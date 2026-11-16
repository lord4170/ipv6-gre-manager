# IPv6 GRE Tunnel Manager v2 (Iran-first)

**All terminal menus, prompts, status messages, and errors are in English.** The manager uses plain ASCII text in its terminal interface.

This version is developed on a separate branch. It does not replace the existing v1 manager or its configuration.

## Install

Run this command on both Ubuntu servers:

```bash
curl -fsSL https://raw.githubusercontent.com/lord4170/ipv6-gre-manager/v2-iran-first/bootstrap-v2.sh | sudo bash
```

Then launch:

```bash
sudo gre-manager
```

## Menu

1. Create tunnel on the Iran server and generate a transfer link.
2. Import the link on the outside server and create the peer tunnel.
3. List registered tunnels and interface counters.
4. Remove one selected tunnel.
5. Run a ping test and show tunnel statistics.
0. Exit.

## Setup workflow

1. On the Iran server, select option 1 and enter the outside server's public IPv6 address. The manager detects the local IPv6 source, chooses an unused interface name, allocates an unused /30 subnet from 10.250.0.0/16, generates a unique GRE key, creates the tunnel, and displays the transfer link.
2. On the outside server, select option 2, paste the link, and enter a preferred interface name.
3. The outside server validates its local IPv6 address, creates the matching GRE tunnel, and tests connectivity to the Iran tunnel IP.

Each tunnel has its own systemd unit and is restored after reboot.

## Transfer link security

The GRE2 link contains Base64URL-encoded JSON and a truncated SHA-256 checksum. **It is not encrypted.** The checksum only detects accidental corruption; it is not a digital signature. Anyone who obtains the link can decode both IPv6 endpoints, tunnel IP addresses, and the GRE key. Treat the link as confidential.

## Safety

- Uses IPv6 GRE (IP protocol 47); no TCP or UDP port is used.
- Does not change the default route, NAT, firewall rules, or IP forwarding.
- Does not remove or modify existing tunnel interfaces or v1 configuration.
- v2 configuration is stored under /etc/gre-manager/.
- The executable is installed as /usr/local/sbin/gre-manager.
- Removing a tunnel deletes only the selected local endpoint. Remove its peer separately if required.

## Requirements

Ubuntu with systemd, root access, Python 3, iproute2, and IPv6 connectivity between both servers. The installer installs iproute2, iputils-ping, and Python 3 if needed. Allow IPv6 GRE (Next Header 47) in provider and host firewalls.
