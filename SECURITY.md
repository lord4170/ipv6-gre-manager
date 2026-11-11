# Security Policy

## Supported version

Security fixes should target the latest published version of IPv6 GRE Tunnel Manager.

## Reporting a vulnerability

Do not publish import links, passwords, tunnel configuration, server credentials, or exploitable details in a public issue.

If GitHub private vulnerability reporting is enabled for this repository, use it. Otherwise, contact the repository owner through a private channel.

## Operational guidance

- Keep each encrypted import link's password separate from the link.
- Treat possession of both the link and password as permission to import the encoded tunnel configuration.
- Do not store live tunnel credentials or generated import links in the Git repository.
- Review installer changes before running them as root.
