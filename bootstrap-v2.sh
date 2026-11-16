#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
OWNER_REPO="lord4170/ipv6-gre-manager"
DEFAULT_REF="v2-iran-first"
REF="${1:-$DEFAULT_REF}"
[[ "$REF" =~ ^[A-Za-z0-9._/-]+$ && "$REF" != *".."* ]] || { echo "[ERROR] Invalid ref." >&2; exit 2; }
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then echo "[ERROR] Run with sudo." >&2; exit 1; fi
[[ -r /etc/os-release ]] || { echo "[ERROR] Cannot identify OS." >&2; exit 1; }
. /etc/os-release
[[ "${ID:-}" == ubuntu ]] || { echo "[ERROR] Ubuntu required." >&2; exit 1; }
if ! command -v curl >/dev/null 2>&1; then
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y curl ca-certificates
fi
TMP_DIR="$(mktemp -d -t gre-manager-v2.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
BASE_URL="https://raw.githubusercontent.com/${OWNER_REPO}/${REF}"
for file in gre-manager-v2.py.gz.b64 install-v2.sh; do
 echo "[INFO] Downloading $file..."
 curl --fail --location --silent --show-error --retry 3 "$BASE_URL/$file" --output "$TMP_DIR/$file"
done
base64 -d "$TMP_DIR/gre-manager-v2.py.gz.b64" | gzip -d > "$TMP_DIR/gre-manager-v2.py"
# Normalize iproute2 tunnel-show syntax for portability.
sed -i 's/ip -6 tunnel show dev /ip -6 tunnel show /g; s/"show", "dev", cfg\["ifname"\]/"show", cfg["ifname"]/g' "$TMP_DIR/gre-manager-v2.py"
chmod 0755 "$TMP_DIR/install-v2.sh"
bash "$TMP_DIR/install-v2.sh"
echo "Start with: sudo gre-manager"
