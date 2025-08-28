#!/usr/bin/env python3
"""
writer.py — Append/merge into a dictionary secret on Vault KV v2.

Usage:
  export VAULT_ADDR=http://127.0.0.1:8200
  export VAULT_TOKEN=root
  python writer.py --path=api-credentials --id=myuser --api-key ABC --api-secret XYZ
  # add --overwrite to replace an existing id
"""

import argparse
import os
import sys
import time

try:
    import hvac
except ImportError as exc:
    raise SystemExit("Missing dependency: hvac. Install via 'pip install hvac python-dotenv'") from exc

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # optional

MAX_RETRIES = 5
RETRY_SLEEP_S = 0.25  # backoff base


def get_env() -> tuple[str, str]:
    if load_dotenv is not None:
        load_dotenv()
    addr = os.getenv("VAULT_ADDR")
    token = os.getenv("VAULT_TOKEN")
    if not addr or not token:
        sys.stderr.write("Error: VAULT_ADDR and VAULT_TOKEN must be set.\n")
        sys.exit(1)
    return addr, token


def main() -> None:
    parser = argparse.ArgumentParser(description="Append/merge credentials into a Vault KV v2 dictionary.")
    parser.add_argument("--path", default="api-credentials",
                        help="Relative path under KV v2 (default: api-credentials).")
    parser.add_argument("--id", required=True, help="Logical ID (dictionary key).")
    parser.add_argument("--api-secret", required=True, help="API secret (will NOT be printed).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Allow overwriting an existing id entry.")
    args = parser.parse_args()

    vault_addr, token = get_env()
    client = hvac.Client(url=vault_addr, token=token)
    if not client.is_authenticated():
        sys.stderr.write("Error: failed to authenticate with Vault; check VAULT_TOKEN.\n")
        sys.exit(1)

    kv = client.secrets.kv.v2
    path = args.path
    entry_id = args.id

    # Retry loop to handle CAS conflicts (simultaneous writers)
    for attempt in range(1, MAX_RETRIES + 1):
        # 1) Read current secret and version
        current_data = {}
        current_version = 0
        try:
            read = kv.read_secret_version(path=path)
            current_data = read["data"]["data"] or {}
            current_version = read["data"]["metadata"]["version"]
        except hvac.exceptions.InvalidPath:
            # Secret doesn't exist yet -> treat as empty dict, version stays 0
            current_data = {}
            current_version = 0

        # 2) Check overwrite policy
        if not args.overwrite and entry_id in current_data:
            sys.stderr.write(
                f"Refused: id '{entry_id}' already exists. Use --overwrite to replace it.\n"
            )
            sys.exit(2)

        # 3) Merge new entry
        new_data = dict(current_data)  # shallow copy
        new_data[entry_id] = {
            "api_secret": args.api_secret,
        }

        # 4) Write back with CAS to avoid lost updates
        try:
            # CAS rule for KV v2:
            # - If secret exists, set cas=<current_version>
            # - If it doesn't exist, cas=0 to create only if missing
            kv.create_or_update_secret(path=path, secret=new_data, cas=current_version)
            print(f"Upsert OK: id='{entry_id}' written at '{path}' (version CAS={current_version}).")
            return
        except hvac.exceptions.VaultError as err:
            msg = " ".join(err.errors) if hasattr(err, "errors") and err.errors else str(err)
            # Typical CAS conflict phrase:
            cas_conflict = "check-and-set parameter did not match" in msg.lower()
            if cas_conflict and attempt < MAX_RETRIES:
                # backoff and retry
                time.sleep(RETRY_SLEEP_S * attempt)
                continue
            # Other errors or retries exhausted
            sys.stderr.write(f"Failed to write (attempt {attempt}/{MAX_RETRIES}): {msg}\n")
            sys.exit(3)


if __name__ == "__main__":
    main()
