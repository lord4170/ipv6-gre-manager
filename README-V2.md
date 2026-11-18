# IPv6 GRE Tunnel Manager v2 (Hub-and-Spoke)

**All terminal menus, prompts, status messages, and errors are English/ASCII only.**

This version is developed on the separate `v2-iran-first` branch. It does not replace v1 or modify its configuration.

## Architecture

The outside server is the central **Hub**. Each Iran server is an independent **Spoke**. One Hub can manage multiple Iran peers. Every peer receives its own interface, GRE key, tunnel ID, and non-overlapping IPv4 /30 subnet.

## Install

Run on both Ubuntu servers:

```bash
curl -fsSL https://raw.githubusercontent.com/lord4170/ipv6-gre-manager/v2-iran-first/bootstrap-v2.sh | sudo bash
sudo gre-manager
```

## Workflow

1. On the outside server, choose **Create Iran peer**.
2. Enter a peer name and the Iran server's public IPv6 address; select the Hub's locally assigned global IPv6 address.
3. The manager locks the central registry, rejects duplicate Iran IPv6 endpoints, checks local IPv4 addresses/routes and registered allocations, then allocates a free /30 subnet and unique GRE key.
4. The Hub creates its tunnel and systemd unit, then prints a peer-specific transfer link.
5. On the Iran server, choose **Import Hub link**, paste the link, select the matching local IPv6 address, and optionally set an interface name.
6. The Spoke creates its matching endpoint and enables it at boot.

Menu options list local tunnel state and RX/TX counters, ping a selected peer, remove one local tunnel, and display the Hub registry.

## Allocation and safety

- Registry: `/etc/gre-manager/registry.json`; local configs: `/etc/gre-manager/tunnels/`.
- Registry writes use an exclusive file lock and atomic replacement.
- Pool: `10.250.0.0/16`, allocated as independent /30 networks.
- Each peer gets a unique GRE key and Linux interface name.
- The allocator checks current IPv4 addresses/routes plus existing registry allocations.
- Before allocation, the Hub also scans common persistent network and script configuration paths (Netplan, systemd-networkd, ifupdown, NetworkManager, GRE Manager, and local admin scripts) for IPv4 reservations. Runtime kernel addresses and routes are checked as well.
- The Hub displays the suggested free /30 and asks for confirmation. The operator can instead enter a custom canonical /30 network; it is checked against all discovered and registered networks before acceptance.
- On import, the Iran Spoke independently checks the received /30 against its own active addresses/routes and common saved network configuration. If it conflicts, import is refused and a new Hub link with a different subnet is required.
- Existing interfaces are never overwritten. Existing v1 files and unrelated GRE tunnels are not removed.
- No default route, NAT, firewall, or IP forwarding changes are made.
- Each local endpoint has its own systemd unit and is restored after reboot.
- Removing a Hub endpoint does not remotely delete the Iran endpoint; remove it separately on that peer.

## Transfer link security

The link contains Base64URL-encoded JSON and a truncated SHA-256 checksum. **It is not encrypted.** The checksum detects accidental corruption only; it is not a signature. Anyone with the link can decode endpoint addresses and the GRE key. Keep it confidential.

## Requirements

Ubuntu with systemd, Python 3, iproute2, IPv6 connectivity, and root access. The installer installs iproute2, iputils-ping, and Python 3. IPv6 GRE uses IP protocol 47, not a TCP/UDP port; allow protocol 47 in provider and host firewalls.

## Validation status

Syntax and shell checks do not prove provider-level connectivity. End-to-end tunnel connectivity must be tested between real VPS endpoints.
