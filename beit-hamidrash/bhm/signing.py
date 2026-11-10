"""יחידת החיתום: מפתחות Ed25519, חתימה ואימות של נתונים.

Every user, node and authority has an Ed25519 key pair. Everything that
travels between computers (events, bundle manifests) is signed over its
canonical JSON form, so a single changed byte breaks the signature.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical(obj) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


class Identity:
    """A signing identity (private key). The public key is its id."""

    def __init__(self, key: Ed25519PrivateKey):
        self._key = key

    @classmethod
    def generate(cls) -> "Identity":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load(cls, path: Path) -> "Identity":
        return cls(serialization.load_pem_private_key(Path(path).read_bytes(), password=None))

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = self._key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption())
        path.write_bytes(pem)
        path.chmod(0o600)

    @property
    def pubkey(self) -> str:
        raw = self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return b64(raw)

    def sign(self, data: bytes) -> str:
        return b64(self._key.sign(data))


def verify(pubkey: str, data: bytes, signature: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(unb64(pubkey)).verify(unb64(signature), data)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def fingerprint(pubkey: str) -> str:
    """Short human-readable id for a key, e.g. for display next to a name."""
    return sha256_hex(unb64(pubkey))[:16]
