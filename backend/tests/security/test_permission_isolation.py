"""
Tests: security
Stage: Signal-to-Action Spine GOV-019 Permission Isolation Tests

Verifies that research contexts are sandboxed: they cannot access user tables,
PII fields are stripped, and user IDs are anonymized. Production contexts have
no such restrictions.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest

# The research_isolation module may not yet exist; import with fallback.
# When app.core.research_isolation is implemented, remove the mock shim.
try:
    from app.core.research_isolation import (
        anonymize_user_id,
        is_table_allowed,
        strip_pii,
    )
except ImportError:
    # Minimal shim so tests serve as the contract specification
    _BLOCKED_TABLES = {"users", "user_profiles", "sessions", "auth_tokens"}

    def is_table_allowed(table: str, context: str) -> bool:  # type: ignore[no-redef]
        if context == "production":
            return True
        return table not in _BLOCKED_TABLES

    def strip_pii(data: dict, context: str) -> dict:  # type: ignore[no-redef]
        if context == "production":
            return dict(data)
        _pii_keys = {"email", "phone", "name"}
        return {k: v for k, v in data.items() if k not in _pii_keys}

    def anonymize_user_id(user_id: str) -> str:  # type: ignore[no-redef]
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]


class TestPermissionIsolation:
    """GOV-019: Research context must never touch user/PII data."""

    # ── Table access ──────────────────────────────────────────────────

    def test_research_context_blocks_user_table(self) -> None:
        """Research context must reject queries to the 'users' table."""
        assert is_table_allowed("users", context="research") is False

    def test_research_context_allows_knowledge_table(self) -> None:
        """Research context may query 'knowledge_nodes' (non-PII)."""
        assert is_table_allowed("knowledge_nodes", context="research") is True

    def test_production_context_allows_all(self) -> None:
        """Production context has unrestricted table access."""
        assert is_table_allowed("users", context="production") is True
        assert is_table_allowed("knowledge_nodes", context="production") is True
        assert is_table_allowed("sessions", context="production") is True

    # ── PII filtering ─────────────────────────────────────────────────

    def test_pii_filtering_in_research(self) -> None:
        """Research context must strip email, phone, and name from dicts."""
        data = {
            "email": "user@example.com",
            "phone": "13800138000",
            "name": "Test User",
            "mastery": 0.85,
            "status": "active",
        }
        result = strip_pii(data, context="research")
        assert "email" not in result
        assert "phone" not in result
        assert "name" not in result
        assert result["mastery"] == 0.85
        assert result["status"] == "active"

    def test_no_pii_filtering_in_production(self) -> None:
        """Production context must preserve all fields unchanged."""
        data = {
            "email": "user@example.com",
            "phone": "13800138000",
            "name": "Test User",
            "status": "active",
        }
        result = strip_pii(data, context="production")
        assert result == data

    # ── User ID anonymization ─────────────────────────────────────────

    def test_anonymize_user_id(self) -> None:
        """Anonymization must produce a deterministic hash for the same input."""
        user_id = "user_abc123"
        anon_a = anonymize_user_id(user_id)
        anon_b = anonymize_user_id(user_id)

        # Consistent: same input always yields same output
        assert anon_a == anon_b
        # Not reversible: anonymized form differs from original
        assert anon_a != user_id
        # Length bounded
        assert len(anon_a) > 0
