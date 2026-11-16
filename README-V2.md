# IPv6 GRE Tunnel Manager v2 (Iran-first)

This preview adds an Iran-initiated workflow in a separate branch. The existing v1 manager and its configuration remain untouched.

## Install on both Ubuntu servers

```bash
curl -fsSL https://raw.githubusercontent.com/lord4170/ipv6-gre-manager/v2-iran-first/bootstrap-v2.sh | sudo bash
sudo gre-manager
```

## Workflow

1. On Iran, select option 1 and enter the outside server's public IPv6. The manager detects the local IPv6 route, selects an unused interface, allocates a free /30 from 10.250.0.0/16, creates a random GRE key, starts the tunnel and prints a transfer link.
2. On the outside server, select option 2, paste the link, and enter a preferred interface name.
3. The outside server creates its matching tunnel and runs a ping test to Iran.

The menu also lists managed tunnels, shows interface counters, runs ping tests, and removes a selected tunnel. Each tunnel has its own systemd unit for reboot persistence.

## Link security

The GRE2 link is Base64URL-encoded JSON with a truncated SHA-256 checksum for accidental corruption detection. It is **not encrypted** and the checksum is **not a digital signature**. Anyone who obtains the link can decode its endpoints, private tunnel IPs, and GRE key. Treat it as confidential.

## Safety boundaries

- IPv6 GRE uses IP protocol 47 (not a TCP/UDP port).
- No default route, NAT, firewall, or IP forwarding changes are made.
- Existing interfaces and v1 files are not intentionally modified.
- Configurations are stored in /etc/gre-manager; the executable is /usr/local/sbin/gre-manager.
- Deleting a tunnel removes it only from that server; remove its peer separately if desired.
- Permit IPv6 GRE (Next Header 47) in provider and host firewalls.

Requirements: Ubuntu with systemd, root access, Python 3, iproute2, and IPv6 reachability between servers.
