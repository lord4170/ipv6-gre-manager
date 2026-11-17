#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "$(id -u)" -ne 0 ]]; then echo "[ERROR] Run as root: sudo bash install-v2.sh" >&2; exit 1; fi
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/gre-manager-v2.py"
TARGET="/usr/local/sbin/gre-manager"
[[ -f "$SOURCE" ]] || { echo "[ERROR] gre-manager-v2.py missing." >&2; exit 1; }
. /etc/os-release
[[ "$ID" == ubuntu ]] || { echo "[ERROR] Ubuntu required; detected $PRETTY_NAME." >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y iproute2 iputils-ping python3 ca-certificates
install -D -m 0755 "$SOURCE" "$TARGET"
python3 -m py_compile "$TARGET"
"$TARGET" --version
echo "[OK] Installed. Run: sudo gre-manager"
echo "[INFO] Existing v1 manager and its data are not modified."
