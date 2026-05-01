from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.core.metrics import SOURCE_STATE_ENCODER_LATENCY
from app.state_aggregator.schema import ActiveSkillsSummaryValue, SufficiencySummaryValue

SOURCE_STATE_DIMENSION_ORDER = (
    "tool_category",
    "sufficiency_level",
    "conflict_outcome",
    "skill_domain",
    "achievement_tier",
    "calendar_pressure",
    "cohort_segment",
)
SOURCE_STATE_MAX_COMBINATIONS = 128
SOURCE_STATE_DIMENSION_PRIORITY = (
    "tool_category",
    "sufficiency_level",
    "calendar_pressure",
    "cohort_segment",
    "skill_domain",
    "achievement_tier",
    "conflict_outcome",
)
SOURCE_STATE_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "tool_category": ("chat", "plan", "task", "reflection", "general"),
    "sufficiency_level": ("low", "medium", "high"),
    "conflict_outcome": ("clear", "pending", "resolved"),
    "skill_domain": ("none", "plan", "focus", "reflection", "mixed"),
    "achievement_tier": ("none", "emerging", "active", "advanced"),
    "calendar_pressure": ("none", "low", "medium", "high"),
    "cohort_segment": (
        "general",
        "exam_beginner",
        "exam_intermediate",
        "exam_advanced",
        "habit_beginner",
        "habit_intermediate",
        "habit_advanced",
        "project_beginner",
        "project_intermediate",
        "project_advanced",
    ),
}
SOURCE_STATE_DEFAULT_VALUES = {
    "tool_category": "general",
    "sufficiency_level": "medium",
    "conflict_outcome": "clear",
    "skill_domain": "none",
    "achievement_tier": "none",
    "calendar_pressure": "none",
    "cohort_segment": "general",
}


@dataclass(frozen=True)
class SourceStateDimensionRegistryEntry:
    name: str
    source: str
    value_type: str
    allowed_values: tuple[str, ...]
    ttl: str
    sqam_evidence: str


RULE_AH_DIMENSION_REGISTRY: dict[str, SourceStateDimensionRegistryEntry] = {
    "tool_category": SourceStateDimensionRegistryEntry(
        name="tool_category",
        source="routing_input.intent",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["tool_category"],
        ttl="turn",
        sqam_evidence="ID1/ST1 via deterministic intent mapping; DP1/SM1 via Stage 23 tests and telemetry",
    ),
    "sufficiency_level": SourceStateDimensionRegistryEntry(
        name="sufficiency_level",
        source="task/context sufficiency summaries",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["sufficiency_level"],
        ttl="turn",
        sqam_evidence="ID1/ST1 via threshold mapping; DP1/SM1 via outcome backfill and encoder tests",
    ),
    "conflict_outcome": SourceStateDimensionRegistryEntry(
        name="conflict_outcome",
        source="context_data.unresolved_conflicts + conflict metadata",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["conflict_outcome"],
        ttl="session",
        sqam_evidence="ID1/ST1 via explicit status mapping; DP1/SM1 via deterministic fallback coverage",
    ),
    "skill_domain": SourceStateDimensionRegistryEntry(
        name="skill_domain",
        source="active_skills_summary / selected skill names",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["skill_domain"],
        ttl="turn",
        sqam_evidence="ID1/ST1 via stable name heuristics; DP1/SM1 via router integration tests",
    ),
    "achievement_tier": SourceStateDimensionRegistryEntry(
        name="achievement_tier",
        source="achievement_summary.total_achievement_score + recent_unlocks",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["achievement_tier"],
        ttl="day",
        sqam_evidence="ID1/ST1 via score thresholds; DP1/SM1 via Stage 22 achievement wire baseline",
    ),
    "calendar_pressure": SourceStateDimensionRegistryEntry(
        name="calendar_pressure",
        source="calendar_context.workload_density + exam_urgency + deadlines",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["calendar_pressure"],
        ttl="day",
        sqam_evidence="ID1/ST1 via calendar thresholds; DP1/SM1 via Stage 22 calendar wire baseline",
    ),
    "cohort_segment": SourceStateDimensionRegistryEntry(
        name="cohort_segment",
        source="user_profile.goal_type + knowledge_level",
        value_type="enum",
        allowed_values=SOURCE_STATE_ALLOWED_VALUES["cohort_segment"],
        ttl="week",
        sqam_evidence="ID1/ST1 via normalized cohort mapping; DP1/SM1 via error_replan cohort fallback tests",
    ),
}


def canonicalize_source_state(source_state: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    raw = source_state or {}
    for name in SOURCE_STATE_DIMENSION_ORDER:
        entry = RULE_AH_DIMENSION_REGISTRY[name]
        value = str(raw.get(name) or SOURCE_STATE_DEFAULT_VALUES[name]).strip().lower()
        if value not in entry.allowed_values:
            value = SOURCE_STATE_DEFAULT_VALUES[name]
        normalized[name] = value
    return normalized


def encode_source_state_key(source_state: dict[str, str] | None) -> str:
    normalized = canonicalize_source_state(source_state)
    return "|".join(f"{name}={normalized[name]}" for name in SOURCE_STATE_DIMENSION_ORDER)


def estimate_state_space(value_map: dict[str, set[str] | list[str] | tuple[str, ...]]) -> int:
    total = 1
    for name in SOURCE_STATE_DIMENSION_ORDER:
        options = value_map.get(name) or []
        count = max(1, len({str(item) for item in options}))
        total *= count
    return total


def prune_dimension_space_for_budget(
    value_map: dict[str, set[str] | list[str] | tuple[str, ...]],
    max_combinations: int = SOURCE_STATE_MAX_COMBINATIONS,
) -> dict[str, list[str]]:
    pruned = {
        name: sorted({str(item) for item in (value_map.get(name) or [])}) or [SOURCE_STATE_DEFAULT_VALUES[name]]
        for name in SOURCE_STATE_DIMENSION_ORDER
    }
    while estimate_state_space(pruned) > max_combinations:
        trimmed = False
        for name in reversed(SOURCE_STATE_DIMENSION_PRIORITY):
            if len(pruned[name]) <= 1:
                continue
            pruned[name] = [pruned[name][0]]
            trimmed = True
            break
        if not trimmed:
            break
    return pruned


class SourceStateEncoder:
    def build(
        self,
        *,
        routing_input: Any | None,
        task_summary: SufficiencySummaryValue | None,
        context_summary: SufficiencySummaryValue | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        active_skills_summary: ActiveSkillsSummaryValue | None,
        selected_skill_names: list[str] | None = None,
        state_context_data: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        started = time.perf_counter()
        try:
            state = canonicalize_source_state(
                {
                    "tool_category": self._derive_tool_category(routing_input),
                    "sufficiency_level": self._derive_sufficiency_level(task_summary, context_summary),
                    "conflict_outcome": self._derive_conflict_outcome(state_context_data),
                    "skill_domain": self._derive_skill_domain(active_skills_summary, selected_skill_names or []),
                    "achievement_tier": self._derive_achievement_tier(user_context_payload),
                    "calendar_pressure": self._derive_calendar_pressure(user_context_payload),
                    "cohort_segment": self._derive_cohort_segment(plan_context, user_context_payload),
                }
            )
            return state
        finally:
            SOURCE_STATE_ENCODER_LATENCY.observe(max(0.0, time.perf_counter() - started))

    def key_for(self, source_state: dict[str, str] | None) -> str:
        return encode_source_state_key(source_state)

    @staticmethod
    def _derive_tool_category(routing_input: Any | None) -> str:
        intent = str(getattr(routing_input, "intent", "") or "").strip().lower()
        if intent in {"plan", "planning"}:
            return "plan"
        if intent in {"task", "todo", "execution"}:
            return "task"
        if intent in {"reflection", "review"}:
            return "reflection"
        if intent in {"chat", "conversation", "qa"}:
            return "chat"
        return "general"

    @staticmethod
    def _derive_sufficiency_level(
        task_summary: SufficiencySummaryValue | None,
        context_summary: SufficiencySummaryValue | None,
    ) -> str:
        scores = [item.score for item in (task_summary, context_summary) if item is not None]
        if not scores:
            return "medium"
        floor = min(scores)
        if floor < 0.6:
            return "low"
        if floor < 0.8:
            return "medium"
        return "high"

    @staticmethod
    def _derive_conflict_outcome(state_context_data: dict[str, Any] | None) -> str:
        context = state_context_data or {}
        unresolved = context.get("unresolved_conflicts")
        if isinstance(unresolved, list) and unresolved:
            return "pending"
        comparison = context.get("aurora_shadow_comparison")
        if isinstance(comparison, dict) and comparison.get("diverged"):
            return "resolved"
        return "clear"

    @staticmethod
    def _derive_skill_domain(
        active_skills_summary: ActiveSkillsSummaryValue | None,
        selected_skill_names: list[str],
    ) -> str:
        names: list[str] = []
        if active_skills_summary is not None:
            names.extend(item.name for item in active_skills_summary.items)
        names.extend(selected_skill_names)
        if not names:
            return "none"
        matched: set[str] = set()
        for raw in names:
            name = raw.strip().lower()
            if any(token in name for token in ("plan", "规划", "拆解")):
                matched.add("plan")
            elif any(token in name for token in ("focus", "专注", "番茄")):
                matched.add("focus")
            elif any(token in name for token in ("reflect", "复盘", "反思")):
                matched.add("reflection")
        if not matched:
            return "mixed"
        if len(matched) == 1:
            return next(iter(matched))
        return "mixed"

    @staticmethod
    def _derive_achievement_tier(user_context_payload: dict[str, Any] | None) -> str:
        summary = (user_context_payload or {}).get("achievement_summary")
        if not isinstance(summary, dict):
            return "none"
        score = float(summary.get("total_achievement_score") or 0.0)
        recent_unlocks = summary.get("recent_unlocks") or []
        if score <= 0 and not recent_unlocks:
            return "none"
        if score >= 8 or len(recent_unlocks) >= 4:
            return "advanced"
        if score >= 3 or len(recent_unlocks) >= 2:
            return "active"
        return "emerging"

    @staticmethod
    def _derive_calendar_pressure(user_context_payload: dict[str, Any] | None) -> str:
        calendar_context = (user_context_payload or {}).get("calendar_context")
        if not isinstance(calendar_context, dict) or not calendar_context:
            return "none"
        if not any(
            key in calendar_context
            for key in ("workload_density", "upcoming_deadlines", "exam_urgency", "time_blocks_today")
        ):
            return "none"
        workload_density = str(calendar_context.get("workload_density") or "").strip().lower()
        deadlines = calendar_context.get("upcoming_deadlines") or []
        exam_urgency = calendar_context.get("exam_urgency") or {}
        urgent_exam = bool(exam_urgency.get("urgent")) if isinstance(exam_urgency, dict) else False
        if urgent_exam or workload_density == "high" or len(deadlines) >= 3:
            return "high"
        if workload_density == "medium" or len(deadlines) >= 1:
            return "medium"
        return "low"

    @staticmethod
    def _derive_cohort_segment(
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
    ) -> str:
        profile = (plan_context or {}).get("user_profile") if isinstance(plan_context, dict) else None
        if not isinstance(profile, dict):
            profile = (user_context_payload or {}).get("user_profile")
        goal_type = str((profile or {}).get("goal_type") or "general").strip().lower()
        knowledge_level = str((profile or {}).get("knowledge_level") or "intermediate").strip().lower()
        goal_bucket = "general"
        if "exam" in goal_type or "考试" in goal_type:
            goal_bucket = "exam"
        elif any(token in goal_type for token in ("habit", "习惯", "routine")):
            goal_bucket = "habit"
        elif any(token in goal_type for token in ("project", "项目", "deliverable")):
            goal_bucket = "project"

        level_bucket = "intermediate"
        if any(token in knowledge_level for token in ("beginner", "novice", "初")):
            level_bucket = "beginner"
        elif any(token in knowledge_level for token in ("advanced", "expert", "高")):
            level_bucket = "advanced"
        elif any(token in knowledge_level for token in ("intermediate", "mid", "中")):
            level_bucket = "intermediate"

        candidate = f"{goal_bucket}_{level_bucket}" if goal_bucket != "general" else "general"
        return candidate if candidate in SOURCE_STATE_ALLOWED_VALUES["cohort_segment"] else "general"


def build_backfill_source_state(
    *,
    decision_type: str,
    decision_payload: dict[str, Any] | None,
    skills_injected: list[str] | None,
) -> dict[str, str]:
    payload = decision_payload or {}
    route_reason = str(payload.get("route_reason") or "").strip().lower()
    follow_up_question = str(payload.get("follow_up_question") or "").strip()
    tool_category = "general"
    if "plan" in route_reason or decision_type in {"cognitive_first", "execution_first", "balanced"}:
        tool_category = "plan"
    if "chat" in route_reason:
        tool_category = "chat"
    if "task" in route_reason:
        tool_category = "task"
    return canonicalize_source_state(
        {
            "tool_category": tool_category,
            "sufficiency_level": "low" if follow_up_question else "medium",
            "conflict_outcome": "clear",
            "skill_domain": "mixed" if skills_injected else "none",
            "achievement_tier": "none",
            "calendar_pressure": "none",
            "cohort_segment": "general",
        }
    )
