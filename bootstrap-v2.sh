#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
OWNER_REPO="lord4170/ipv6-gre-manager"
REF="${1:-v2-iran-first}"
[[ "$REF" =~ ^[A-Za-z0-9._/-]+$ && "$REF" != *".."* ]] || { echo "[ERROR] Invalid ref." >&2; exit 2; }
[[ "$(id -u)" -eq 0 ]] || { echo "[ERROR] Run with sudo." >&2; exit 1; }
. /etc/os-release
[[ "$ID" == ubuntu ]] || { echo "[ERROR] Ubuntu required." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { apt-get update; apt-get install -y curl ca-certificates; }
TMP_DIR="$(mktemp -d -t gre-manager-v2.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
BASE_URL="https://raw.githubusercontent.com/$OWNER_REPO/$REF"
for file in gre-manager-v2.py install-v2.sh; do
 echo "[INFO] Downloading $file..."
 curl --fail --location --silent --show-error --retry 3 "$BASE_URL/$file" --output "$TMP_DIR/$file"
done
chmod 0755 "$TMP_DIR/install-v2.sh"
bash "$TMP_DIR/install-v2.sh"
echo "Start with: sudo gre-manager"
