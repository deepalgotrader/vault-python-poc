#!/usr/bin/env bash
set -euo pipefail

echo "[uninstall] Searching for Vault binary..."

VAULT_PATH="$(command -v vault || true)"

if [[ -z "$VAULT_PATH" ]]; then
  echo "[info] Vault is not in PATH. Nothing to remove."
  exit 0
fi

echo "[info] Vault binary found at: $VAULT_PATH"

# Detect if installed via apt
if dpkg -s vault >/dev/null 2>&1; then
  echo "[info] Vault appears installed via APT package manager."
  read -rp "Do you want to remove it with apt? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    sudo apt remove --purge -y vault
    sudo apt autoremove -y
    echo "[ok] Vault removed via apt."
    exit 0
  else
    echo "[skip] Skipping apt removal."
  fi
fi

# If it’s just a binary in /usr/local/bin or elsewhere
if [[ -f "$VAULT_PATH" ]]; then
  read -rp "Do you want to delete $VAULT_PATH ? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    sudo rm -f "$VAULT_PATH"
    echo "[ok] Removed Vault binary at $VAULT_PATH"
  else
    echo "[skip] Not removed."
  fi
fi

# Optional cleanup of local config and token
if [[ -d "$HOME/.vault" || -f "$HOME/.vault-token" ]]; then
  read -rp "Remove user config (~/.vault* ) ? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.vault" "$HOME/.vault-token"
    echo "[ok] Removed user Vault config and token."
  fi
fi

echo "[done] Vault uninstallation finished."
