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
