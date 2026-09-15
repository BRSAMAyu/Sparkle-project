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

import os
from dataclasses import dataclass
from typing import Any, Literal, cast

from loguru import logger

# Fields that are considered sensitive / PII and require explicit justification
SENSITIVE_FIELDS: set[str] = {
    "access_token",
    "address",
    "api_key",
    "email",
    "avatar_url",
    "device_id",
    "full_name",
    "ip_address",
    "location_lat",
    "location_lng",
    "password_hash",
    "phone",
    "raw_content",
    "refresh_token",
    "sensitive_tags",
    "token",
}

DataMinimizationMode = Literal["audit", "enforce"]
VALID_DATA_MINIMIZATION_MODES: set[str] = {"audit", "enforce"}
PRODUCTION_ENVIRONMENTS: set[str] = {"prod", "production"}


def _scope(*fields: str) -> set[str]:
    return set(fields)


# Allowed fields per target model scope — anything outside is stripped on store
TARGET_MODEL_SCOPES: dict[str, set[str]] = {
    "sprint_pack": _scope(
        "id",
        "user_id",
        "sprint_id",
        "pack_id",
        "mastery",
        "status",
        "started_at",
        "expires_at",
    ),
    "chronicle": _scope(
        "id",
        "user_id",
        "entry_type",
        "narrative",
        "timestamp",
        "confidence",
        "evidence_refs",
    ),
    "achievement": _scope(
        "id",
        "user_id",
        "achievement_id",
        "progress",
        "progress_value",
        "progress_target",
        "unlocked_at",
        "context_snapshot",
    ),
    "growth_chronicle": _scope(
        "id",
        "user_id",
        "entry_count",
        "confirmed_count",
        "payload",
        "last_saved_at",
        "metadata",
    ),
    "user_profile": _scope(
        "id",
        "user_id",
        "profile_version",
        "learning_preferences",
        "goal_preferences",
        "evidence_refs",
        "last_updated_at",
    ),
    "skill_entry": _scope(
        "id",
        "user_id",
        "skill_id",
        "name",
        "description",
        "version",
        "active",
        "contraindications",
        "evidence_refs",
        "updated_at",
    ),
    "policy_decision": _scope(
        "id",
        "user_id",
        "decision_id",
        "policy_id",
        "surface",
        "action",
        "reason",
        "confidence",
        "decided_at",
        "outcome",
    ),
    "causal_trace": _scope(
        "id",
        "user_id",
        "trace_id",
        "policy_decision_id",
        "event_type",
        "causal_factors",
        "confidence",
        "created_at",
    ),
    "cohort_aggregate": _scope(
        "id",
        "cohort_id",
        "metric_name",
        "metric_value",
        "sample_size",
        "privacy_floor",
        "generated_at",
    ),
    "return_case_file": _scope(
        "id",
        "user_id",
        "case_id",
        "case_type",
        "status",
        "summary",
        "outcome",
        "evidence_refs",
        "created_at",
        "updated_at",
    ),
    "relationship_model": _scope(
        "id",
        "user_id",
        "subject_user_id_hash",
        "relationship_type",
        "status",
        "strength",
        "evidence_refs",
        "updated_at",
    ),
    "knowledge_node": _scope(
        "id",
        "user_id",
        "node_id",
        "name",
        "description",
        "subject_id",
        "status",
        "source_type",
        "source_file_id",
        "chunk_refs",
        "mastery_score",
        "bkt_mastery_prob",
        "last_study_at",
        "revision",
    ),
    "source_asset": _scope(
        "id",
        "user_id",
        "asset_id",
        "file_id",
        "source_type",
        "title",
        "status",
        "checksum",
        "metadata",
        "created_at",
    ),
    "recall_opportunity": _scope(
        "id",
        "user_id",
        "opportunity_id",
        "source_type",
        "recall_score",
        "value_reason",
        "deadline_pressure_label",
        "scheduled_for",
        "created_at",
    ),
    "intervention_episode": _scope(
        "id",
        "user_id",
        "request_id",
        "episode_id",
        "requested_level",
        "final_level",
        "status",
        "reason",
        "content",
        "decision_trace",
        "evidence_refs",
        "outcome",
        "occurred_at",
    ),
    "memory_preference": _scope(
        "id",
        "user_id",
        "pref_key",
        "pref_value",
        "version",
        "confidence",
        "evidence_score",
        "evidence_refs",
        "last_consumed_at",
    ),
    "episodic_memory": _scope(
        "id",
        "user_id",
        "summary",
        "source_type",
        "source_id",
        "source_lane",
        "subject_type",
        "occurred_at",
        "importance_score",
        "confidence",
        "evidence_refs",
        "tags",
    ),
    "memory_goal": _scope(
        "id",
        "user_id",
        "title",
        "status",
        "target_date",
        "linked_task_id",
        "linked_plan_id",
        "evidence_refs",
    ),
    "user_learning_profile": _scope(
        "id",
        "user_id",
        "preferred_difficulty",
        "preferred_duration_minutes",
        "preferred_time_of_day",
        "subject_distribution",
        "learning_vector",
        "cluster_id",
        "last_updated_at",
    ),
    "cohort_recommendation": _scope(
        "id",
        "user_id",
        "recommendation_type",
        "cached_recommendations",
        "generated_at",
        "expires_at",
        "hit_count",
    ),
    "strategy_state": _scope(
        "id",
        "user_id",
        "strategy_id",
        "belief",
        "confidence",
        "evidence_refs",
        "counter_evidence",
        "updated_at",
    ),
    "aurora_state_snapshot": _scope(
        "id",
        "user_id",
        "surface",
        "conversation_id",
        "runtime_session_id",
        "snapshot_version",
        "snapshot_at",
        "user_model_snapshot",
        "informational_tensions",
        "activity_profile",
        "metadata",
    ),
    "goal_world_graph": _scope(
        "id",
        "graph_id",
        "user_id",
        "goal_id",
        "goal_type",
        "coverage",
        "payload",
        "last_saved_at",
        "metadata",
    ),
    "counterfactual_report": _scope(
        "id",
        "user_id",
        "context_signature",
        "context_hash",
        "policy_a",
        "policy_b",
        "estimate",
        "confidence",
        "evidence_grade",
        "generated_at",
        "promotion_status",
        "iron_law_compliance",
    ),
    "safe_experiment_episode": _scope(
        "id",
        "user_id",
        "experiment_id",
        "variant",
        "status",
        "outcome",
        "guardrail_result",
        "started_at",
        "ended_at",
    ),
    "community_interaction": _scope(
        "id",
        "user_id",
        "group_id",
        "sender_id",
        "resource_type",
        "resource_id",
        "knowledge_node_id",
        "message_type",
        "status",
        "metadata",
        "created_at",
    ),
    "document_asset": _scope(
        "id",
        "user_id",
        "file_id",
        "node_id",
        "chunk_id",
        "source_type",
        "content_hash",
        "embedding_ref",
        "feedback_type",
        "score",
        "metadata",
        "created_at",
    ),
    "error_record": _scope(
        "id",
        "user_id",
        "error_id",
        "task_id",
        "knowledge_node_id",
        "error_type",
        "summary",
        "status",
        "evidence_refs",
        "linked_knowledge_node_ids",
        "created_at",
    ),
    "learning_state": _scope(
        "id",
        "user_id",
        "node_id",
        "task_id",
        "subject_id",
        "study_minutes",
        "mastery_score",
        "progress",
        "status",
        "source_type",
        "revision",
        "created_at",
        "updated_at",
    ),
    "skill_marketplace_adoption": _scope(
        "id",
        "user_id",
        "skill_id",
        "pack_id",
        "version",
        "status",
        "adopted_at",
        "source",
        "evidence_refs",
    ),
    "task_state": _scope(
        "id",
        "user_id",
        "task_id",
        "plan_id",
        "title",
        "status",
        "priority",
        "knowledge_node_id",
        "progress",
        "due_date",
        "started_at",
        "completed_at",
        "updated_at",
    ),
    "visual_reward": _scope(
        "id",
        "user_id",
        "achievement_id",
        "element_id",
        "title_id",
        "skin_id",
        "status",
        "unlocked_at",
        "metadata",
    ),
}

TARGET_MODEL_ALIASES: dict[str, str] = {
    "achievements": "achievement",
    "aurora_decision_telemetry": "policy_decision",
    "counterfactual_evaluation_reports": "counterfactual_report",
    "behavioral_outcome": "intervention_episode",
    "behavioral_outcomes": "intervention_episode",
    "document_chunk": "document_asset",
    "document_chunks": "document_asset",
    "document_retrieval_feedback": "document_asset",
    "error_records": "error_record",
    "expansion_feedback": "learning_state",
    "growth_chronicle_snapshot": "growth_chronicle",
    "growth_chronicle_snapshots": "growth_chronicle",
    "goal_world_graph_snapshot": "goal_world_graph",
    "goal_world_graph_snapshots": "goal_world_graph",
    "group_message": "community_interaction",
    "group_messages": "community_interaction",
    "intervention_request": "intervention_episode",
    "intervention_requests": "intervention_episode",
    "intervention_record": "intervention_episode",
    "intervention_records": "intervention_episode",
    "intervention_audit_log": "intervention_episode",
    "intervention_audit_logs": "intervention_episode",
    "intervention_feedback": "intervention_episode",
    "intervention_outcome": "intervention_episode",
    "intervention_outcomes": "intervention_episode",
    "intervention_strategy_outcome": "intervention_episode",
    "intervention_strategy_outcomes": "intervention_episode",
    "knowledge_nodes": "knowledge_node",
    "knowledge_node_document": "source_asset",
    "knowledge_node_documents": "source_asset",
    "learning_asset": "source_asset",
    "learning_assets": "source_asset",
    "asset_suggestion_log": "source_asset",
    "asset_suggestion_logs": "source_asset",
    "memory_preferences": "memory_preference",
    "memory_goals": "memory_goal",
    "node_expansion_queue": "learning_state",
    "node_relation": "knowledge_node",
    "node_relations": "knowledge_node",
    "pack_adoption_history": "skill_marketplace_adoption",
    "passive_signal": "intervention_episode",
    "passive_signals": "intervention_episode",
    "plan_state": "task_state",
    "plan_states": "task_state",
    "episodic_memories": "episodic_memory",
    "policy_decisions": "policy_decision",
    "recommendation_cache": "cohort_recommendation",
    "return_case": "return_case_file",
    "safe_experiment_episodes": "safe_experiment_episode",
    "shared_resource": "community_interaction",
    "shared_resources": "community_interaction",
    "skill_share_moderation_queue": "skill_entry",
    "study_record": "learning_state",
    "study_records": "learning_state",
    "stored_file": "source_asset",
    "stored_files": "source_asset",
    "task": "task_state",
    "tasks": "task_state",
    "user_achievement": "achievement",
    "user_achievements": "achievement",
    "user_galaxy_skin": "visual_reward",
    "user_galaxy_skins": "visual_reward",
    "user_item_interaction": "cohort_recommendation",
    "user_item_interactions": "cohort_recommendation",
    "user_learning_profiles": "user_learning_profile",
    "user_node_status": "knowledge_node",
    "user_profile_snapshot": "user_profile",
    "user_profiles": "user_profile",
    "user_skill_adoption": "skill_marketplace_adoption",
    "user_skill_adoptions": "skill_marketplace_adoption",
    "user_skills": "skill_entry",
    "user_title": "visual_reward",
    "user_titles": "visual_reward",
    "user_visual_element": "visual_reward",
    "user_visual_elements": "visual_reward",
}


class DataMinimizationViolation(RuntimeError):
    """Raised when enforce mode sees data for an unregistered target model."""

    def __init__(
        self,
        *,
        user_id: str,
        target_model: str,
        fields: list[str],
        mode: DataMinimizationMode,
    ) -> None:
        self.user_id = user_id
        self.target_model = target_model
        self.fields = fields
        self.mode = mode
        # Unknown targets have no approved retention scope. A caller that catches
        # this can persist the audit facts and degrade to an empty prompt payload.
        self.audit_record = {
            "event": "data_minimization_violation",
            "user_id": user_id,
            "target_model": target_model,
            "fields": fields,
            "mode": mode,
            "fallback_data": {},
        }
        super().__init__(
            f"GOV-013 data minimization violation: target_model={target_model!r} "
            f"is not registered for user={user_id!r}"
        )


def resolve_data_minimization_mode(
    configured_mode: str | None = None,
    *,
    environment: str | None = None,
) -> DataMinimizationMode:
    """Resolve audit/enforce behavior from explicit config or environment.

    Production defaults to enforce. Non-production defaults to audit to support
    migration discovery without silently changing local fixtures.
    """
    raw_mode = (
        (configured_mode or os.getenv("SPARKLE_DATA_MINIMIZATION_MODE", ""))
        .strip()
        .lower()
    )
    if raw_mode:
        if raw_mode not in VALID_DATA_MINIMIZATION_MODES:
            raise ValueError(
                "SPARKLE_DATA_MINIMIZATION_MODE must be one of: "
                f"{', '.join(sorted(VALID_DATA_MINIMIZATION_MODES))}"
            )
        return cast(DataMinimizationMode, raw_mode)

    raw_environment = (
        environment
        or os.getenv("ENVIRONMENT")
        or os.getenv("APP_ENV")
        or os.getenv("SPARKLE_ENV")
        or "development"
    )
    normalized_environment = raw_environment.strip().lower()
    if normalized_environment in PRODUCTION_ENVIRONMENTS:
        return "enforce"
    return "audit"


def canonical_target_model(target_model: str) -> str:
    """Normalize table/class aliases to a registered target-model scope key."""
    normalized = target_model.strip()
    return TARGET_MODEL_ALIASES.get(normalized, normalized)


@dataclass
class MinimizationReport:
    """Audit report for a module's data collection practices."""

    module: str
    fields: list[str]
    sensitive_count: int
    recommendation: str


class DataMinimizationAuditor:
    """GOV-013: Audits data collection and enforces field minimization."""

    def __init__(
        self,
        mode: DataMinimizationMode | str | None = None,
        *,
        environment: str | None = None,
    ) -> None:
        self.mode = resolve_data_minimization_mode(mode, environment=environment)

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
            module_name,
            len(fields_collected),
            sensitive_count,
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

        In audit mode, unknown target models are passed through with an audit
        warning for migration discovery. In enforce mode, unknown target models
        raise DataMinimizationViolation so callers can write the audit record
        and degrade the prompt/persistence path instead of storing unscoped data.

        Args:
            user_id: The user whose data is being stored.
            target_model: Key in TARGET_MODEL_SCOPES (e.g. "sprint_pack").
            data: The raw data dict to be persisted.

        Returns:
            A filtered dict containing only scope-allowed fields.
        """
        canonical_model = canonical_target_model(target_model)
        allowed = TARGET_MODEL_SCOPES.get(canonical_model)

        if allowed is None:
            field_names = sorted(data.keys())
            if self.mode == "enforce":
                logger.error(
                    "GOV-013: unknown target_model={} canonical={} user={} "
                    "mode=enforce fields={} — blocking store",
                    target_model,
                    canonical_model,
                    user_id,
                    field_names,
                )
                raise DataMinimizationViolation(
                    user_id=user_id,
                    target_model=target_model,
                    fields=field_names,
                    mode=self.mode,
                )
            logger.warning(
                "GOV-013: unknown target_model={} canonical={} user={} mode=audit "
                "— passing through fields for migration discovery. Register scope "
                "before enabling enforce.",
                target_model,
                canonical_model,
                user_id,
            )
            return dict(data)

        filtered = {k: v for k, v in data.items() if k in allowed}
        stripped_keys = set(data.keys()) - allowed

        if stripped_keys:
            logger.info(
                "GOV-013: stripped fields from store user={} model={} canonical={} mode={} "
                "stripped={} retained={}",
                user_id,
                target_model,
                canonical_model,
                self.mode,
                sorted(stripped_keys),
                sorted(filtered.keys()),
            )

        return filtered
