#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash install.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="$SCRIPT_DIR/ipv6-gre-manager"
SOURCE_HELPER="$SCRIPT_DIR/gre-link-crypto.py"
TARGET_SCRIPT="/usr/local/sbin/ipv6-gre-manager"
TARGET_HELPER="/usr/local/libexec/ipv6-gre-manager/gre-link-crypto.py"
UNIT_FILE="/etc/systemd/system/ipv6-gre@.service"

if [[ ! -f "$SOURCE_SCRIPT" || ! -f "$SOURCE_HELPER" ]]; then
  echo "Required manager files are missing beside install.sh" >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify operating system." >&2
  exit 1
fi
# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This release is designed for Ubuntu. Detected: ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found." >&2
  exit 1
fi

echo "Installing dependencies on ${PRETTY_NAME:-Ubuntu}..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y iproute2 iputils-ping iperf3 python3 openssl ca-certificates

install -D -m 0755 "$SOURCE_SCRIPT" "$TARGET_SCRIPT"
install -D -m 0755 "$SOURCE_HELPER" "$TARGET_HELPER"
install -d -m 0700 /etc/ipv6-gre-manager/tunnels
install -d -m 0700 /var/lib/ipv6-gre-manager/exports

cat > "$UNIT_FILE" <<'UNIT'
[Unit]
Description=IPv6 GRE tunnel %i
Documentation=man:ip-link(8)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/ipv6-gre-manager apply %i
ExecStop=/usr/local/sbin/ipv6-gre-manager down %i
TimeoutStartSec=30

[Install]
WantedBy=multi-user.target
UNIT

chmod 0644 "$UNIT_FILE"
systemctl daemon-reload

# Load the GRE-over-IPv6 kernel module when available; it may also be built into the kernel.
modprobe ip6_gre >/dev/null 2>&1 || true

echo
echo "Installation completed."
echo "Run: sudo ipv6-gre-manager"
echo "The same installer and manager are used on the Foreign and Iran servers."
echo "Encrypted import links use AES-256-CBC with PBKDF2 and HMAC-SHA256."
