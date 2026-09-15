"""
SQLAlchemy event listeners for transparent PII field-level encryption.

Intercepts before_insert, before_update, and refresh events on User and
UserDevice models to encrypt sensitive fields at rest and decrypt on load.
All existing application code continues to work unchanged.

Fields encrypted: google_id, apple_id, wechat_unionid, push_token
Lookup hash columns: google_id_hash, apple_id_hash, wechat_unionid_hash,
                     push_token_hash, username_hash, email_hash
"""

from __future__ import annotations

from sqlalchemy import event

from app.core.crypto import decrypt_value, encrypt_value
from app.core.logsafe import pii_lookup_hash

# Fields that should be encrypted at rest
_ENCRYPTED_FIELDS = {
    "google_id": "google_id_hash",
    "apple_id": "apple_id_hash",
    "wechat_unionid": "wechat_unionid_hash",
    "push_token": "push_token_hash",
}

# Fields that only need hash columns (for future migration)
_HASH_ONLY_FIELDS = {"username": "username_hash", "email": "email_hash"}


def _is_fernet_token(value: str | None) -> bool:
    """Heuristic: Fernet tokens are base64, ~170+ chars, start with gAAA."""
    if not value:
        return False
    return len(value) >= 100 and value.startswith("gAAA")


def _encrypt_fields(target, fields_to_encrypt: dict[str, str]) -> None:
    """Encrypt plaintext fields and populate hash columns."""
    for plain_field, hash_field in fields_to_encrypt.items():
        value = getattr(target, plain_field, None)
        if value is None:
            continue
        if _is_fernet_token(value):
            # Already encrypted — skip
            continue
        # Set hash column for deterministic lookup
        if hash_field:
            setattr(target, hash_field, pii_lookup_hash(value))
        # Encrypt the value
        encrypted = encrypt_value(value)
        if encrypted is not None:
            setattr(target, plain_field, encrypted)


def _decrypt_fields(target, fields_to_decrypt: dict[str, str]) -> None:
    """Decrypt encrypted fields back to plaintext."""
    for plain_field, _hash_field in fields_to_decrypt.items():
        value = getattr(target, plain_field, None)
        if value is None:
            continue
        if _is_fernet_token(value):
            decrypted = decrypt_value(value)
            if decrypted is not None:
                setattr(target, plain_field, decrypted)


def _setup_listeners() -> None:
    """Register SQLAlchemy event listeners for PII encryption."""
    from app.models.user import User, UserDevice
    from app.core.crypto import get_fernet_key

    # Only activate if encryption key is available
    try:
        get_fernet_key()
    except Exception:
        return

    user_fields = {
        "google_id": "google_id_hash",
        "apple_id": "apple_id_hash",
        "wechat_unionid": "wechat_unionid_hash",
    }

    device_fields = {
        "push_token": "push_token_hash",
    }

    # ── User: encrypt social IDs before write ──
    @event.listens_for(User, "before_insert", propagate=True)
    def user_before_insert(_mapper, _connection, target):
        _encrypt_fields(target, user_fields)

    @event.listens_for(User, "before_update", propagate=True)
    def user_before_update(_mapper, _connection, target):
        # Only re-encrypt if the plaintext is new (not already a Fernet token)
        _encrypt_fields(target, user_fields)

    # ── User: decrypt after load ──
    @event.listens_for(User, "load", propagate=True)
    def user_after_load(target, _context):
        _decrypt_fields(target, user_fields)

    @event.listens_for(User, "refresh", propagate=True)
    def user_after_refresh(target, _context, _attribute_names):
        _decrypt_fields(target, user_fields)

    # ── UserDevice: encrypt push_token before write ──
    @event.listens_for(UserDevice, "before_insert", propagate=True)
    def device_before_insert(_mapper, _connection, target):
        _encrypt_fields(target, device_fields)

    @event.listens_for(UserDevice, "before_update", propagate=True)
    def device_before_update(_mapper, _connection, target):
        _encrypt_fields(target, device_fields)

    # ── UserDevice: decrypt after load ──
    @event.listens_for(UserDevice, "load", propagate=True)
    def device_after_load(target, _context):
        _decrypt_fields(target, device_fields)

    @event.listens_for(UserDevice, "refresh", propagate=True)
    def device_after_refresh(target, _context, _attribute_names):
        _decrypt_fields(target, device_fields)


# Install listeners at import time
_setup_listeners()
