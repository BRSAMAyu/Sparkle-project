"""GOV-012: Research mode isolation layer.

Ensures that research/analytics queries operate within strict table and PII
boundaries so that user-identifiable data never leaves the production context
without explicit anonymization.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Table allow-lists
# ---------------------------------------------------------------------------

# Tables that contain user auth or PII — never exposed to research mode.
_PII_TABLES: frozenset[str] = frozenset(
    {
        "users",
        "user_profiles",
        "user_settings",
        "user_auth_tokens",
        "user_sessions",
        "user_credentials",
        "refresh_tokens",
        "password_resets",
        "device_registrations",
        "push_tokens",
    }
)

DEFAULT_PRODUCTION_TABLES: frozenset[str] = frozenset(
    {
        # Knowledge & learning
        "knowledge_nodes",
        "knowledge_edges",
        "error_records",
        "error_tags",
        "mastery_records",
        # Planning & execution
        "plans",
        "plan_reviews",
        "tasks",
        "task_dependencies",
        "task_feedback",
        # Growth & achievement
        "achievements",
        "achievement_unlocks",
        "achievement_contracts",
        "achievement_sprints",
        "photon_transactions",
        "visual_elements",
        # Cognitive & memory
        "cognitive_patterns",
        "cognitive_capsules",
        "memory_entries",
        "memory_embeddings",
        # Community
        "communities",
        "community_members",
        "community_posts",
        "community_comments",
        # Calendar & focus
        "calendar_events",
        "focus_sessions",
        "breathing_sessions",
        # Simulation & theater
        "simulations",
        "predictions",
        # General
        "chat_messages",
        "chat_sessions",
        "seed_library_items",
        "notes",
        "tags",
        "notifications",
        "reports",
    }
)

DEFAULT_RESEARCH_TABLES: frozenset[str] = frozenset(
    {
        "knowledge_nodes",
        "error_records",
        "plans",
        "tasks",
        "achievements",
        "cognitive_patterns",
        "mastery_records",
        "focus_sessions",
    }
)

# Fields that are considered PII and must be stripped in research mode.
_PII_FIELD_NAMES: frozenset[str] = frozenset(
    {"email", "phone", "name", "avatar_url", "nickname", "real_name", "id_number", "bank_card"}
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResearchContext:
    """Encapsulates the isolation boundary for a query session."""

    is_research: bool
    anonymized: bool
    allowed_tables: frozenset[str]
    study_id: str | None = None


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------


class ResearchIsolationGuard:
    """Validates and enforces research-mode data access policies."""

    def validate_query(self, context: ResearchContext, table_name: str) -> bool:
        """Return *True* if *table_name* is accessible under *context*."""
        if table_name in _PII_TABLES:
            logger.warning("research-isolation: blocked PII table access ({})", table_name)
            return False

        if not context.is_research:
            # Production context: allow everything except _PII_TABLES (checked above).
            return True

        if table_name not in context.allowed_tables:
            logger.warning(
                "research-isolation: table '{}' not in research allow-list (study={})",
                table_name,
                context.study_id,
            )
            return False

        return True

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def anonymize_user_id(user_id: str, study_id: str) -> str:
        """Deterministic, one-way pseudonym: first 12 hex chars of SHA-256."""
        raw = f"{user_id}:{study_id}".encode()
        return hashlib.sha256(raw).hexdigest()[:12]

    @staticmethod
    def filter_pii_fields(data: dict[str, Any], context: ResearchContext) -> dict[str, Any]:
        """Strip PII keys from *data* when running in research mode."""
        if not context.is_research or not context.anonymized:
            return data

        return {k: v for k, v in data.items() if k not in _PII_FIELD_NAMES}

    # -- context factories ---------------------------------------------------

    @staticmethod
    def create_research_context(
        study_id: str,
        anonymize: bool = True,
        extra_tables: frozenset[str] | None = None,
    ) -> ResearchContext:
        tables = DEFAULT_RESEARCH_TABLES | (extra_tables or frozenset())
        ctx = ResearchContext(
            is_research=True,
            anonymized=anonymize,
            allowed_tables=tables,
            study_id=study_id,
        )
        logger.info("research-isolation: created research context (study={}, tables={})", study_id, len(tables))
        return ctx

    @staticmethod
    def create_production_context() -> ResearchContext:
        return ResearchContext(
            is_research=False,
            anonymized=False,
            allowed_tables=DEFAULT_PRODUCTION_TABLES,
        )
