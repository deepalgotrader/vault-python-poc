#!/usr/bin/env python3
"""
reader.py — Read a dictionary secret from Vault KV v2.

Usage:
  export VAULT_ADDR=http://127.0.0.1:8200
  export VAULT_TOKEN=root
  python reader.py --path=api-credentials           # print whole dict (ids only by default)
  python reader.py --path=api-credentials --id=myuser
  python reader.py --path=api-credentials --reveal   # print secrets too (be careful!)
"""

import argparse
import os
import sys

try:
    import hvac
except ImportError as exc:
    raise SystemExit("Missing dependency: hvac. Install via 'pip install hvac python-dotenv'") from exc

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # optional


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
    parser = argparse.ArgumentParser(description="Read a dictionary secret from Vault KV v2.")
    parser.add_argument("--path", default="api-credentials", help="Path under KV v2.")
    parser.add_argument("--id", help="Optional id to print only that entry.")
    parser.add_argument("--reveal", action="store_true",
                        help="Print secrets in clear text (use with caution).")
    args = parser.parse_args()

    vault_addr, token = get_env()
    client = hvac.Client(url=vault_addr, token=token)
    if not client.is_authenticated():
        sys.stderr.write("Error: failed to authenticate with Vault; check VAULT_TOKEN.\n")
        sys.exit(1)

    kv = client.secrets.kv.v2
    try:
        read = kv.read_secret_version(path=args.path)
    except hvac.exceptions.InvalidPath:
        print(f"(empty) No secret at path '{args.path}'.")
        return

    data = read["data"]["data"] or {}
    version = read["data"]["metadata"]["version"]

    if args.id:
        entry = data.get(args.id)
        if entry is None:
            print(f"id='{args.id}' not found at '{args.path}' (version {version}).")
            return
        if args.reveal:
            print({"id": args.id, **entry})
        else:
            print({"id": args.id, "api_secret": "***"})
        return

    # Print summary of all IDs
    ids = sorted(list(data.keys()))
    print(f"Path '{args.path}' (version {version}) contains {len(ids)} id(s):")
    if args.reveal:
        # Danger: prints secrets!
        for i in ids:
            print({ "id": i, **data[i] })
    else:
        for i in ids:
            print({ "id": i, "api_secret": "***" })


if __name__ == "__main__":
    main()
