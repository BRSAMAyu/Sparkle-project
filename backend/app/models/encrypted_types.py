"""
SQLAlchemy type decorators for transparent field-level encryption.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt_value, encrypt_value


class EncryptedString(TypeDecorator):
    """Transparently encrypt/decrypt a String column at rest.

    Uses Fernet (AES-256-GCM) authenticated encryption.
    The column stores the Fernet token (base64, ~170-230 bytes for typical values).

    Usage:
        email = Column(EncryptedString(255), nullable=False)
    """

    impl = String
    cache_ok = True

    def __init__(self, length=None, **kwargs):
        # Encrypted values are larger; store at least 500 chars
        effective_length = length or 255
        super().__init__(length=effective_length, **kwargs)

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return decrypt_value(value)
