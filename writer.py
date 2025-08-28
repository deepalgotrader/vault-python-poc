"""
writer.py
==========

This script demonstrates how to write a secret into a HashiCorp Vault key/value
store from Python. It uses the `hvac` library to communicate with Vault over
its HTTP API.  Vault encrypts secrets at rest【247159539390981†L568-L617】, so the
application does not need to handle cryptography itself.

Usage
-----

Run the script with a secret path and the message to store.  The path is
relative to the mount point of the KV secrets engine (the default mount in
development mode is ``secret/``).  For example, to store a message at
``secret/data/my‑secret`` you would use the following command:

.. code-block:: shell

    export VAULT_ADDR=http://127.0.0.1:8200
    export VAULT_TOKEN=root
    python writer.py --path=my‑secret "Hello from Vault"

The script requires the ``VAULT_ADDR`` and ``VAULT_TOKEN`` environment
variables to be set.  ``VAULT_ADDR`` specifies the base URL of your Vault
server and ``VAULT_TOKEN`` must contain a token with permission to write
secrets.  In development mode Vault prints a root token when it starts.

"""

import argparse
import os
import sys

try:
    import hvac
except ImportError as exc:  # pragma: no cover - imported at runtime
    raise SystemExit(
        "Missing dependency: hvac. Install requirements via 'pip install -r requirements.txt'"
    ) from exc

try:
    from dotenv import load_dotenv
except ImportError:
    # python‑dotenv is optional; if not installed the script will still work as long as
    # VAULT_ADDR and VAULT_TOKEN are set in the environment.
    load_dotenv = None  # type: ignore


def main() -> None:
    """Entry point for the writer script."""
    parser = argparse.ArgumentParser(description="Store a secret in HashiCorp Vault.")
    parser.add_argument(
        "message", help="The message to store in Vault"
    )
    parser.add_argument(
        "--path",
        default="my-secret",
        help=(
            "The relative path under the KV secrets engine where the message will be stored."
            " Defaults to 'my-secret'."
        ),
    )
    args = parser.parse_args()

    # Load environment variables from .env if python‑dotenv is available
    if load_dotenv is not None:
        load_dotenv()

    vault_addr = os.getenv("VAULT_ADDR")
    token = os.getenv("VAULT_TOKEN")
    if not vault_addr or not token:
        sys.stderr.write(
            "Error: VAULT_ADDR and VAULT_TOKEN must be set in the environment or in a .env file.\n"
        )
        sys.exit(1)

    # Initialise the HVAC client
    client = hvac.Client(url=vault_addr, token=token)
    if not client.is_authenticated():
        sys.stderr.write(
            "Error: failed to authenticate with Vault; check your VAULT_TOKEN.\n"
        )
        sys.exit(1)

    # Use the KV version 2 secrets engine.  In development mode the 'secret' mount
    # is enabled by default.  If you run Vault with a different mount point or
    # version you may need to adjust this call.  Version 2 supports versioning and
    # metadata.
    kv = client.secrets.kv.v2
    path = args.path
    secret_data = {"message": args.message}
    try:
        kv.create_or_update_secret(path=path, secret=secret_data)
    except hvac.exceptions.VaultError as err:
        sys.stderr.write(f"Failed to write secret: {err}\n")
        sys.exit(1)

    print(f"Secret written successfully to path: {path}")


if __name__ == "__main__":
    main()
