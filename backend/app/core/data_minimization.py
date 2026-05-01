"""
Core: governance
Phase: sense
Stage: Signal-to-Action Spine GOV-013 Data Minimization Auditor

Ruling: Collect only what is needed, store only what serves the target model's
scope. This auditor inspects field collections against known sensitive fields,
produces minimization reports, and strips extraneous data before persistence.

No-action signal is noise; no-audit directive is hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

# Fields that are considered sensitive / PII and require explicit justification
SENSITIVE_FIELDS: set[str] = {
    "email",
    "phone",
    "password_hash",
    "avatar_url",
    "device_id",
    "ip_address",
    "location_lat",
    "location_lng",
}

# Allowed fields per target model scope — anything outside is stripped on store
TARGET_MODEL_SCOPES: dict[str, set[str]] = {
    "sprint_pack": {"mastery", "status"},
    "chronicle": {"entry_type", "narrative", "timestamp"},
    "achievement": {"achievement_id", "unlocked_at"},
}


@dataclass
class MinimizationReport:
    """Audit report for a module's data collection practices."""

    module: str
    fields: list[str]
    sensitive_count: int
    recommendation: str


class DataMinimizationAuditor:
    """GOV-013: Audits data collection and enforces field minimization."""

    def audit_data_collection(
        self,
        module_name: str,
        fields_collected: list[str],
    ) -> MinimizationReport:
        """Audit a module's collected fields against sensitive-field registry.

        Args:
            module_name: Name of the module collecting data.
            fields_collected: List of field names being collected.

        Returns:
            A MinimizationReport with sensitivity count and recommendation.
        """
        collected_set = set(fields_collected)
        sensitive_found = collected_set & SENSITIVE_FIELDS
        sensitive_count = len(sensitive_found)

        if sensitive_count == 0:
            recommendation = "No sensitive fields detected. Collection is acceptable."
        elif sensitive_count <= 2:
            recommendation = (
                f"Review necessity of sensitive fields: {sorted(sensitive_found)}. "
                "Consider whether each field directly serves the module's purpose."
            )
        else:
            recommendation = (
                f"High sensitivity ({sensitive_count} fields): {sorted(sensitive_found)}. "
                "Strongly reduce collection to only strictly necessary fields. "
                "Consider anonymization or aggregation alternatives."
            )

        logger.info(
            "GOV-013: audit module={} fields={} sensitive_count={}",
            module_name, len(fields_collected), sensitive_count,
        )

        return MinimizationReport(
            module=module_name,
            fields=list(fields_collected),
            sensitive_count=sensitive_count,
            recommendation=recommendation,
        )

    def check_before_store(
        self,
        user_id: str,
        target_model: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Strip fields not in the target model's allowed scope before storage.

        If the target_model has no registered scope, all fields are passed
        through with a warning log (fail-open for unrecognized models to avoid
        data loss during migration).

        Args:
            user_id: The user whose data is being stored.
            target_model: Key in TARGET_MODEL_SCOPES (e.g. "sprint_pack").
            data: The raw data dict to be persisted.

        Returns:
            A filtered dict containing only scope-allowed fields.
        """
        allowed = TARGET_MODEL_SCOPES.get(target_model)

        if allowed is None:
            logger.warning(
                "GOV-013: unknown target_model={} for user={} — passing through "
                "all fields (fail-open). Register scope to enforce minimization.",
                target_model, user_id,
            )
            return dict(data)

        filtered = {k: v for k, v in data.items() if k in allowed}
        stripped_keys = set(data.keys()) - allowed

        if stripped_keys:
            logger.info(
                "GOV-013: stripped fields from store user={} model={} "
                "stripped={} retained={}",
                user_id, target_model, sorted(stripped_keys), sorted(filtered.keys()),
            )

        return filtered
