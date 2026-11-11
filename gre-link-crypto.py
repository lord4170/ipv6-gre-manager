#!/usr/bin/env python3
"""Create and consume authenticated, encrypted IPv6 GRE import links.

Format: gre1://import/<base64url(AES-256-CBC ciphertext || HMAC-SHA256)>
Encryption: OpenSSL enc AES-256-CBC + PBKDF2-HMAC-SHA256.
Authentication: encrypt-then-MAC with an independently derived HMAC key.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile

PREFIX = "gre1://import/"
ITERATIONS = 250000
MAGIC = b"Salted__"
CONFIG_KEYS = (
    "VERSION", "NAME", "ROLE", "LOCAL_IPV6", "REMOTE_IPV6",
    "LOCAL_IPV4", "REMOTE_IPV4", "PREFIX", "TTL", "MTU",
)


class LinkError(Exception):
    pass


def _openssl(args, password):
    try:
        proc = subprocess.run(
            ["openssl"] + args,
            input=password + b"\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise LinkError("OpenSSL is required to encrypt or decrypt import links.") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise LinkError(detail or "OpenSSL encryption/decryption failed.")
    return proc.stdout


def _encrypt_bytes(plaintext, password):
    with tempfile.TemporaryDirectory(prefix="ipv6-gre-link-") as workdir:
        os.chmod(workdir, 0o700)
        source = os.path.join(workdir, "plain")
        target = os.path.join(workdir, "cipher")
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(plaintext)
        try:
            proc = subprocess.run(
                [
                    "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
                    "-iter", str(ITERATIONS), "-md", "sha256", "-pass", "stdin",
                    "-in", source, "-out", target,
                ],
                input=password + b"\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            raise LinkError("OpenSSL is required to encrypt or decrypt import links.") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise LinkError(detail or "OpenSSL encryption failed.")
        with open(target, "rb") as stream:
            encrypted = stream.read()
    if not encrypted.startswith(MAGIC) or len(encrypted) < 32:
        raise LinkError("OpenSSL returned an unexpected encrypted payload.")
    return encrypted


def _decrypt_bytes(encrypted, password):
    with tempfile.TemporaryDirectory(prefix="ipv6-gre-link-") as workdir:
        os.chmod(workdir, 0o700)
        source = os.path.join(workdir, "cipher")
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(encrypted)
        return _openssl(
            [
                "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter",
                str(ITERATIONS), "-md", "sha256", "-pass", "stdin", "-in", source,
            ],
            password,
        )


def _mac_key(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password, b"IPv6GRE-MAC-v1" + salt, ITERATIONS, dklen=32
    )


def encrypt_for_role(target_role, args):
    if target_role not in ("foreign", "iran"):
        raise LinkError("Target role must be 'foreign' or 'iran'.")
    name, local_v6, remote_v6, local_v4, remote_v4, prefix, ttl, mtu = args
    payload = {
        "VERSION": "1",
        "NAME": name,
        "ROLE": target_role,
        "LOCAL_IPV6": local_v6,
        "REMOTE_IPV6": remote_v6,
        "LOCAL_IPV4": local_v4,
        "REMOTE_IPV4": remote_v4,
        "PREFIX": prefix,
        "TTL": ttl,
        "MTU": mtu,
    }
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    password = secrets.token_urlsafe(24).encode("ascii")
    encrypted = _encrypt_bytes(plaintext, password)
    salt = encrypted[8:16]
    tag = hmac.new(
        _mac_key(password, salt), b"IPv6GRE-LINK-v1\x00" + encrypted, hashlib.sha256
    ).digest()
    token = PREFIX + base64.urlsafe_b64encode(encrypted + tag).decode("ascii").rstrip("=")
    result = {"link": token, "password": password.decode("ascii")}
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")


def encrypt(args):
    # Backward-compatible command: Foreign -> Iran.
    encrypt_for_role("iran", args)


def decrypt():
    token = sys.stdin.readline().rstrip("\r\n")
    password_text = sys.stdin.readline().rstrip("\r\n")
    if not token.startswith(PREFIX):
        raise LinkError("Invalid import link. Expected a gre1://import/ link.")
    if not password_text:
        raise LinkError("The decryption password is empty.")
    encoded = token[len(PREFIX):]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
        raise LinkError("The import link contains invalid characters.")
    try:
        raw = base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))
    except Exception as exc:
        raise LinkError("The import link is not valid Base64URL data.") from exc
    if len(raw) < 8 + 8 + 16 + 32 or not raw.startswith(MAGIC):
        raise LinkError("The import link is incomplete or has an unsupported format.")
    encrypted, supplied_tag = raw[:-32], raw[-32:]
    salt = encrypted[8:16]
    password = password_text.encode("utf-8")
    expected_tag = hmac.new(
        _mac_key(password, salt), b"IPv6GRE-LINK-v1\x00" + encrypted, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise LinkError("Authentication failed. The password is incorrect or the link was modified.")
    plaintext = _decrypt_bytes(encrypted, password)
    try:
        payload = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        raise LinkError("The decrypted configuration is not valid JSON.") from exc
    if not isinstance(payload, dict) or set(payload.keys()) != set(CONFIG_KEYS):
        raise LinkError("The decrypted configuration has an unexpected structure.")
    for key in CONFIG_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value or "\n" in value or "\r" in value or "=" in value:
            raise LinkError("The decrypted configuration contains an invalid field: " + key)
    if payload["VERSION"] != "1" or payload["ROLE"] not in ("iran", "foreign"):
        raise LinkError("Unsupported configuration version or server role.")
    for key in CONFIG_KEYS:
        sys.stdout.write(key + "=" + payload[key] + "\n")


def main():
    if len(sys.argv) < 2:
        raise LinkError("Usage: gre-link-crypto.py encrypt ... | encrypt-target ROLE ... | decrypt")
    mode = sys.argv[1]
    if mode == "encrypt":
        if len(sys.argv) != 10:
            raise LinkError("Encrypt expects 8 configuration arguments.")
        encrypt(sys.argv[2:])
    elif mode == "encrypt-target":
        if len(sys.argv) != 11:
            raise LinkError("Encrypt-target expects a role and 8 configuration arguments.")
        encrypt_for_role(sys.argv[2], sys.argv[3:])
    elif mode == "decrypt":
        if len(sys.argv) != 2:
            raise LinkError("Decrypt does not accept command-line arguments.")
        decrypt()
    else:
        raise LinkError("Unknown operation.")


if __name__ == "__main__":
    try:
        main()
    except LinkError as exc:
        sys.stderr.write("[ERROR] " + str(exc) + "\n")
        sys.exit(1)
    except Exception:
        sys.stderr.write("[ERROR] Unexpected failure while processing the import link.\n")
        sys.exit(1)
