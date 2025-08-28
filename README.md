# Python Vault Proof‑of‑Concept

This repository contains a small proof‑of‑concept (PoC) that demonstrates how
to use [HashiCorp Vault](https://www.vaultproject.io/) from Python.  It is
designed to run locally on a Windows Subsystem for Linux (WSL) environment and
shows how one program can write data into Vault while another program reads
the data back.

The PoC uses the **Key/Value (KV) secrets engine**.  When you store data in
Vault, the server automatically encrypts it before writing it to the
back‑end storage.  This means the application does not need to implement its
own encryption; Vault handles it. The KV secrets engine supports versioning of secrets 
so that you can keep multiple versions and retrieve old values if necessary.

## About HashiCorp Vault

HashiCorp Vault is a tool for **centralised secrets management**.  It allows
teams to store, access and manage sensitive information such as API keys,
passwords, database credentials and encryption keys in a secure manner.  The
Vault website notes that most enterprises have credentials distributed across
their infrastructure, making it hard to know who has access to what.
Vault addresses this problem by storing secrets centrally and tightly
controlling access to them.

Key features of Vault include:

* **Arbitrary key/value storage:** Vault can store arbitrary key/value
  secrets.  Data is encrypted before it is stored, so gaining access to the
  underlying storage does not expose the plaintext.

* **Encryption as a service:** The **transit secrets engine** handles
  cryptographic functions on data in transit.  Vault does not store the data
  passed to the transit engine; instead it encrypts or decrypts data on the
  fly.  This relieves application developers from implementing encryption and
  decryption, and it can also sign data, generate hashes/HMACs and act as a
  source of random bytes.

* **Dynamic secrets and short‑lived credentials:** Vault can generate secrets
  on demand.  A dynamic secret is created when read and destroyed when its
  lease expires.  This reduces the exposure of long‑lived credentials and
  simplifies rotation.

* **Revocation and audit logging:** Secrets can be revoked before their TTL
  expires, and Vault keeps a detailed audit log of every request and response
  so that you can trace access to secrets.

* **Multiple authentication methods:** Before a client can interact with
  Vault it must authenticate against one of the available **auth methods**
  (for example LDAP, GitHub, Kubernetes or AppRole).  Authentication yields
  a token whose attached policies limit what the client can do.  The
  `approle` auth method is designed for machines and services and allows
  applications to obtain a token by presenting a **role ID** and **secret
  ID**.

## Project Structure

```bash
vault-python-poc/
├── README.md           – this document
├── requirements.txt    – Python dependencies (hvac, python‑dotenv)
├── writer.py           – program that writes data into Vault
└── reader.py           – program that reads data from Vault
└── setup_python.sh     – script to setup python venv
└── setup_vault.sh      – script to setup vault
└── uninstall_vault.sh  – script to uninstall vault
```

### `writer.py`

The **writer** script connects to Vault using the `hvac` library and writes
arbitrary data to a KV secret path.  You specify the secret path via the
`--path` argument and pass the message as a positional argument.  The script
authenticates to Vault using the `VAULT_ADDR` and `VAULT_TOKEN` environment
variables.  In dev mode Vault automatically mounts a KV version 2 secrets
engine at the `secret/` path; version 2 supports secret versioning and
metadata.

### `reader.py`

The **reader** script reads the secret from Vault at the given path and
prints the stored message.  Like the writer, it uses `VAULT_ADDR` and
`VAULT_TOKEN` to authenticate and interacts with the KV version 2 API to
retrieve the latest version of the secret.  Vault decrypts the data on the
server side before returning it to the client, so your application sees
plaintext even though the data is encrypted at rest.

## Running the PoC on WSL

The following steps assume you are using Ubuntu on WSL.  They should be
adapted as necessary for other distributions.  All commands are run inside
WSL.

### 1. Setup Vault

HashiCorp provides pre‑compiled binaries for Linux.  At the time of writing,
you can install Vault on Ubuntu using the official repository:

```sh
chmod +x setup_vault.sh
./setup_vault.sh
```

### 2. Install Python dependencies

Create a virtual environment (optional but recommended) and install the
dependencies listed in `requirements.txt`:

```sh
chmod +x setup_python.sh
./setup_python.sh
```

### 3. Write a secret

Use `writer.py` to store a message.  The `--path` argument specifies where
under the `secret/` mount the data is saved.  For example:

```sh
python3 writer.py --path registered-users --id 0 --api-secret 123456
```

You should see confirmation that the secret was written successfully.

### 4. Read the secret

Run `reader.py` with the same path to retrieve the message:

```sh
python3 reader.py --path registered-users
```

The script prints `Retrieved message from Vault: Hello from Vault!`

## How it works

1. **Authentication:** Both scripts use the `hvac` client to connect to the
   Vault server specified by `VAULT_ADDR`.  They authenticate using the token
   in `VAULT_TOKEN`.  Before a client can interact with Vault it must
   authenticate against an auth method to obtain a token; the policies attached
   to the token restrict what operations the client can perform.

2. **Key/Value secrets engine:** The scripts interact with the KV version 2
   secrets engine mounted at `secret/`.  This engine stores arbitrary
   key/value secrets.  Version 2 supports retaining multiple versions of a
   secret and allows you to retrieve or destroy specific versions.

3. **Encryption at rest:** Vault encrypts data before storing it in its
   back‑end.  You do not see the encryption keys or algorithms; the server
   decrypts the secret when you read it.

## Moving towards a production architecture

Running Vault in dev mode with a root token is sufficient for experimentation
but **not** suitable for production.  When moving to a real deployment (for
example, on a Virtual Private Server running a Django web application), you
should consider the following:

* **Persistent storage and high availability:** Run Vault using a supported
  storage backend such as the integrated **raft** storage, Consul or a cloud
  storage service.  Avoid dev mode, which is in‑memory only.  Configure
  **replication** and **TLS encryption** for secure communication.

* **Authentication with AppRole:** Use the AppRole auth method for
  applications and services.  AppRole allows machines to authenticate using
  a Role ID and Secret ID and obtain a token scoped by policies.  It is
  designed for automated workflows.  Configure a
  policy granting your Django application permission to write secrets at a
  specific path and create an AppRole bound to that policy.  Use a separate
  AppRole with read‑only permissions for background workers or batch
  processes.  To enable AppRole and create a role via the CLI:

  ```sh
  # enable the AppRole auth method
  vault auth enable approle
  # define a policy that allows writing to secret/data/my‑app/*
  echo 'path "secret/data/my‑app/*" { capabilities = ["create", "update"] }' | \
    vault policy write my‑app-policy -
  # create the AppRole and attach the policy
  vault write auth/approle/role/my‑app token_type=batch policies="my‑app-policy" \
      secret_id_ttl=24h token_ttl=1h token_max_ttl=4h
  # obtain the role_id and a secret_id
  vault read auth/approle/role/my‑app/role-id
  vault write -f auth/approle/role/my‑app/secret-id
  ```

* **Django integration:** In your Django settings you can use the `hvac`
  library to fetch configuration values or secrets at startup.  Alternatively,
  run a small **Vault Agent** process on the VPS that authenticates via
  AppRole and writes secrets to a `.env` file for Django to load.  Vault
  provides a [transit secrets engine] that acts as "encryption as a service"
  and can be used to encrypt sensitive fields before writing them to your
  database.

* **Least privilege:** Grant each application the minimum set of capabilities
  it needs.  Use separate policies and tokens for reading and writing.  This
  limits the blast radius if a token is compromised.

* **Audit logs and monitoring:** Enable audit logging so that every request
  and response is recorded for forensic purposes.  Vault supports writing
  logs to files or external systems.  Monitor seal/unseal status and health
  endpoints.

By following these practices you can integrate Vault into a production
environment with a Django web application that writes secrets into Vault and
another service or job that reads them.  The proof‑of‑concept in this
repository provides a minimal working example to get you started.


A concise and descriptive name for the Git repository is **`vault-python-poc`**.
It reflects that the project demonstrates a Python‑based proof‑of‑concept for
HashiCorp Vault.
