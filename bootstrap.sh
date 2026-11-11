#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Usage:
#   curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/bootstrap.sh \
#     | sudo bash -s -- OWNER/REPO [BRANCH_OR_TAG]

REPOSITORY="lord4170/ipv6-gre-manager"
REF="${1:-main}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[ERROR] Run this installer as root (use sudo)." >&2
  exit 1
fi

if [[ ! "$REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  cat >&2 <<'USAGE'
Usage:
  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/bootstrap.sh \
    | sudo bash -s -- OWNER/REPO [BRANCH_OR_TAG]
USAGE
  exit 2
fi

if [[ ! "$REF" =~ ^[A-Za-z0-9._/-]+$ || "$REF" == *".."* ]]; then
  echo "[ERROR] Invalid branch or tag name." >&2
  exit 2
fi

if [[ ! -r /etc/os-release ]]; then
  echo "[ERROR] Cannot identify operating system." >&2
  exit 1
fi
# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "[ERROR] Ubuntu is required. Detected: ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
  echo "[INFO] Installing curl and CA certificates..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y curl ca-certificates
fi

TMP_DIR="$(mktemp -d -t ipv6-gre-manager.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

ARCHIVE_URL="https://codeload.github.com/${REPOSITORY}/tar.gz/${REF}"
ARCHIVE_PATH="$TMP_DIR/source.tar.gz"
SOURCE_DIR="$TMP_DIR/source"
mkdir -p "$SOURCE_DIR"

echo "[INFO] Downloading ${REPOSITORY} (${REF})..."
if command -v curl >/dev/null 2>&1; then
  curl --fail --location --silent --show-error --retry 3 \
    "$ARCHIVE_URL" --output "$ARCHIVE_PATH"
else
  wget -qO "$ARCHIVE_PATH" "$ARCHIVE_URL"
fi

tar -xzf "$ARCHIVE_PATH" --strip-components=1 -C "$SOURCE_DIR"

if [[ ! -f "$SOURCE_DIR/install.sh" ||
      ! -f "$SOURCE_DIR/ipv6-gre-manager" ||
      ! -f "$SOURCE_DIR/gre-link-crypto.py" ]]; then
  echo "[ERROR] The downloaded repository does not contain the required files." >&2
  exit 1
fi

echo "[INFO] Starting IPv6 GRE Tunnel Manager installation..."
bash "$SOURCE_DIR/install.sh"
