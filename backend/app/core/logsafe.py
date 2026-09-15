"""
Log-safe helpers for redacting PII before it reaches structured logs.

Mirrors the Go log-safe package at backend/gateway/internal/logsafe/.
"""

from __future__ import annotations

import hashlib


def user_id_hash(user_id: str) -> str:
    """
    Return a stable, non-reversible 12-char hex token for a user ID.

    Uses SHA-256 and takes the first 12 hex characters, matching the Go
    log-safe UserIDHash() convention so cross-layer log correlation stays
    possible without exposing raw identifiers.
    """
    normalized = user_id.strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def email_mask(email: str) -> str:
    """Return a partially-masked email safe for logging.

    'alice@example.com' → 'a***e@example.com'
    'a@b.com'           → '***@b.com'
    """
    email = (email or "").strip()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "***"
    else:
        masked_local = local[0] + "*" * max(len(local) - 2, 1) + local[-1]
    return f"{masked_local}@{domain}"


def username_hash(username: str) -> str:
    """Return a stable 12-char hex token for a username, matching user_id_hash."""
    return user_id_hash(username)


def pii_lookup_hash(value: str) -> str:
    """Return a SHA-256 hex digest for deterministic PII lookup.

    Used to search by encrypted fields: hash the plaintext input,
    query by the hash column, then decrypt the stored value.
    """
    if not value or not value.strip():
        return ""
    return hashlib.sha256(value.strip().encode()).hexdigest()
