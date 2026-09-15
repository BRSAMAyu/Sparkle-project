"""
Field-Level Encryption for sensitive PII at rest.

Uses AES-256-GCM (via Fernet) for authenticated encryption of database columns.
The encryption key is loaded from FIELD_ENCRYPTION_KEY env var, falling back to
a derivation from SECRET_KEY.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from an arbitrary secret string."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def get_fernet_key() -> bytes:
    """Return the Fernet encryption key.

    Prefers FIELD_ENCRYPTION_KEY env var; falls back to SECRET_KEY derivation.
    """
    from app.config import settings

    raw = os.getenv("FIELD_ENCRYPTION_KEY", "")
    if raw:
        return raw.encode() if len(raw) == 44 and raw.endswith("=") else _derive_fernet_key(raw)

    return _derive_fernet_key(settings.SECRET_KEY or "sparkle-field-encryption-fallback")


def encrypt_value(plaintext: str | None) -> str | None:
    """Encrypt a string value for database storage.

    Returns None if input is None/empty.
    The result is a base64 Fernet token string.
    """
    if not plaintext:
        return None
    f = Fernet(get_fernet_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a Fernet token back to the original string.

    Returns None if input is None/empty.
    If the ciphertext is not a valid Fernet token (legacy plaintext),
    returns it unchanged to support gradual migration.
    """
    if not ciphertext:
        return None
    try:
        f = Fernet(get_fernet_key())
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Not a Fernet token — may be legacy plaintext during migration
        return ciphertext
