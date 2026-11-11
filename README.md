# IPv6 GRE Tunnel Manager

**A standalone IPv6 GRE tunnel manager for Ubuntu servers.**

Create and manage point-to-point IPv4 links over IPv6 GRE between one Foreign server and multiple Iran servers. The same program runs independently on both sides; configuration is exchanged through password-protected encrypted links.

> **Current version:** `1.0.3`  
> **Platform:** Ubuntu 18.04+ (systemd)  
> **License:** No license file is included yet. All rights remain with the copyright holder unless a license is added.

## Features

- One shared manager for both **Foreign** and **Iran** server roles
- Automatic detection of local IPv4 and IPv6 addresses
- Multiple Iran-side tunnels connected to one Foreign server
- Automatic `/30` IPv4 allocation from `10.250.0.0/16` on the Foreign server
- Copy/paste encrypted import links; no configuration file transfer or central SSH controller required
- Password-protected configuration links using AES-256-CBC, PBKDF2-HMAC-SHA256, and HMAC-SHA256
- Create, import, apply, stop, restart, and delete tunnels without rebooting
- Edit existing tunnels in place, including IPv6 endpoints, tunnel IPv4 addresses, prefix, TTL, and MTU
- Bidirectional encrypted peer-update links for edits initiated from either side
- Optional per-tunnel `systemd` startup after reboot
- Tunnel status, packet counters, ping checks, and `iperf3` bandwidth tests
- No default-route changes, NAT rules, or IP-forwarding changes
- Legacy configuration-file import retained for backward compatibility

## How it works

```text
                   IPv6 GRE
    +------------------------------------+
    |                                    |
+------------------+             +------------------+
|  FOREIGN SERVER  |             |   IRAN SERVER    |
|                  |             |                  |
|  gre1            |=============|  gre1            |
|  10.250.0.1/30   |             |  10.250.0.2/30   |
+------------------+             +------------------+

          One Foreign server can manage
              multiple Iran peers.
```

The GRE transport uses the servers' **public IPv6 addresses**. The tunnel provides a private point-to-point IPv4 connection. It does not route all server traffic and does not change the default route.

## Requirements

- Ubuntu 18.04 or newer
- Root access (`sudo`)
- A systemd-based installation
- Kernel support for IPv6 GRE (`ip6_gre`)
- Public IPv6 connectivity between the two servers
- IPv6 GRE (IP protocol number `47`) permitted by the host and provider firewalls

The installer installs these packages through APT:

- `iproute2`
- `iputils-ping`
- `iperf3`
- `python3`
- `openssl`
- `ca-certificates`

## Quick install

The repository must be **public** for this no-token installation method.


```bash
curl -fsSL https://raw.githubusercontent.com/lord4170/ipv6-gre-manager/main/bootstrap.sh | sudo bash -s -- lord4170/ipv6-gre-manager
```

To install a specific tagged release instead of the latest `main` branch:

```bash
curl -fsSL https://raw.githubusercontent.com/lord4170/ipv6-gre-manager/main/bootstrap.sh | sudo bash -s -- lord4170/ipv6-gre-manager v1.0.3
```

The command can be run from any directory on either server. The same command installs the manager on both the Foreign and Iran servers.

### Manual installation

Download or clone the repository, then run:

```bash
sudo bash install.sh
sudo ipv6-gre-manager
```

## First-time setup

### 1. Foreign server

1. Run `sudo ipv6-gre-manager`.
2. Select **Foreign Server**.
3. Choose **Create New Tunnel**.
4. Enter the Iran server's public IPv6 address.
5. Review the detected local IPv6 address, suggested MTU, tunnel name, and allocated private IPv4 pair.
6. Confirm creation.
7. Copy the generated encrypted import link and its password.

### 2. Iran server

1. Install the same version of the manager.
2. Run `sudo ipv6-gre-manager`.
3. Select **Iran Server**.
4. Choose **Import encrypted configuration / peer update**.
5. Paste the `gre1://import/...` link.
6. Enter the password when prompted.
7. Confirm the imported settings and enable systemd startup if desired.

Share the link and password through separate channels when practical. Anyone who obtains both can import that tunnel configuration.

## Editing a tunnel

1. Open **Manage Tunnels** and select the tunnel.
2. Choose **Edit tunnel settings (update in place)**.
3. Enter the new local or peer IPv6 endpoint, private tunnel IPv4 address, prefix, TTL, or MTU. Press Enter to keep an existing value.
4. The local interface is updated in place and a new encrypted peer-update link is generated.
5. Import that link on the opposite server to apply the matching peer-side update.

Editing can be initiated from either server. The peer must import the new link to complete the update on both ends. Until then, traffic may be interrupted if an endpoint or tunnel IPv4 address changed.

**Public IPv4 note:** IPv6 GRE uses public IPv6 addresses as its transport endpoints. Changing a server's public IPv4 address alone does not require a GRE edit. The editable IPv4 values are the private addresses assigned to the GRE interface.

## Useful commands

```bash
sudo ipv6-gre-manager
sudo ipv6-gre-manager --version
sudo ipv6-gre-manager apply gre1
sudo ipv6-gre-manager down gre1
```

## Firewall and bandwidth testing

- Allow **IPv6 protocol 47 (GRE)** between the two public IPv6 endpoints. GRE is an IP protocol, not a TCP or UDP port.
- For `iperf3`, allow TCP port `5201` on the tunnel interface/address for the duration of the test.
- For a bidirectional bandwidth test, run an `iperf3` server on the peer first.

## Security

- Import links are encrypted and authenticated. A fresh random password is generated for each link.
- The password is not embedded in the link. Keep it separate when sharing.
- Links do not automatically expire. Generate a new link if an old link/password pair may have been exposed.
- Do not commit real tunnel configuration, import links, passwords, private keys, or server credentials to this repository.
- The one-line installer downloads code and runs it as root. Review `bootstrap.sh` and `install.sh` before running them if you want to audit the installation process.
- Use a private repository if you do not want the source code to be public. A private repository requires an authenticated download method; the public one-line command above will not work without authentication.

## Upgrade

Run the quick-install command again on **both ends** using the desired branch or release tag. The installer replaces the program files and refreshes the systemd unit while retaining saved tunnel configurations under:

```text
/etc/ipv6-gre-manager/tunnels/
```

For bidirectional editing, keep both ends on the same manager version.

## Troubleshooting

- **No IPv6 route:** confirm the server has a global IPv6 address and can reach the peer IPv6 endpoint.
- **Tunnel does not come up:** verify IPv6 GRE protocol 47 is permitted by both host and provider firewalls.
- **Ping fails:** confirm the peer imported the matching configuration and that both tunnel interfaces are up.
- **Bandwidth test fails:** ensure `iperf3` is running on the peer and TCP port `5201` is allowed on the tunnel.
- **Startup fails after reboot:** inspect the unit with `systemctl status ipv6-gre@gre1` and logs with `journalctl -u ipv6-gre@gre1`.

## Repository layout

```text
ipv6-gre-manager/
├── README.md
├── CHANGELOG.md
├── SECURITY.md
├── .gitignore
├── bootstrap.sh
├── install.sh
├── ipv6-gre-manager
└── gre-link-crypto.py
```

## Known limitations

- The manager does not configure NAT, enable IP forwarding, or install default routes.
- Deleting a tunnel on one server does not automatically delete its peer configuration. Remove the matching tunnel on the other server as well.
- A peer update is not applied remotely by itself; the encrypted link must be imported on the other server.
- The public IPv4 address is not used as the GRE transport endpoint.

## Feedback

Please report reproducible bugs with the Ubuntu release, kernel version, manager version, and relevant sanitized logs. Never include import links, passwords, credentials, or private server details in a public issue.
