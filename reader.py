"""
reader.py
==========

This script reads a secret from a HashiCorp Vault key/value store.  It uses
the `hvac` library to communicate with the Vault HTTP API.  You must provide
the path of the secret to retrieve.  The script assumes the secret was stored
as a key called ``message`` in a KV version 2 engine.

The data stored in Vault is encrypted at rest【247159539390981†L568-L617】.  When you
retrieve the secret using the API the Vault server decrypts it on the fly
before returning the plaintext to the client, so your application never
handles encryption or decryption keys itself.

Usage
-----

.. code-block:: shell

    export VAULT_ADDR=http://127.0.0.1:8200
    export VAULT_TOKEN=root
    python reader.py --path=my‑secret

The script requires the ``VAULT_ADDR`` and ``VAULT_TOKEN`` environment variables.
See ``writer.py`` for details.

"""

import argparse
import os
import sys

try:
    import hvac
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: hvac. Install requirements via 'pip install -r requirements.txt'"
    ) from exc

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


def main() -> None:
    """Entry point for the reader script."""
    parser = argparse.ArgumentParser(description="Read a secret from HashiCorp Vault.")
    parser.add_argument(
        "--path",
        default="my-secret",
        help=(
            "The relative path under the KV secrets engine where the message is stored."
            " Defaults to 'my-secret'."
        ),
    )
    args = parser.parse_args()

    # Load environment variables from .env if available
    if load_dotenv is not None:
        load_dotenv()

    vault_addr = os.getenv("VAULT_ADDR")
    token = os.getenv("VAULT_TOKEN")
    if not vault_addr or not token:
        sys.stderr.write(
            "Error: VAULT_ADDR and VAULT_TOKEN must be set in the environment or in a .env file.\n"
        )
        sys.exit(1)

    client = hvac.Client(url=vault_addr, token=token)
    if not client.is_authenticated():
        sys.stderr.write(
            "Error: failed to authenticate with Vault; check your VAULT_TOKEN.\n"
        )
        sys.exit(1)

    kv = client.secrets.kv.v2
    path = args.path
    try:
        result = kv.read_secret_version(path=path)
    except hvac.exceptions.InvalidPath:
        sys.stderr.write(f"No secret found at path: {path}\n")
        sys.exit(1)
    except hvac.exceptions.VaultError as err:
        sys.stderr.write(f"Failed to read secret: {err}\n")
        sys.exit(1)

    # Extract the 'message' field from the secret
    secret_data = result["data"]["data"]
    message = secret_data.get("message")
    print(f"Retrieved message from Vault: {message}")


if __name__ == "__main__":
    main()
