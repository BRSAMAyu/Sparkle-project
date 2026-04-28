from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Mapping

from loguru import logger

from app.aurora.runtime_v1.control_surface import AuroraHardBounds, ControlSurfaceService, HarnessUpdateRejectedError
from app.aurora.runtime_v1.dashboard import (
    REQUIRED_MODELING_DOMAINS,
    DashboardReadout,
    canonicalize_runtime_domain,
)
from app.aurora.runtime_v1.state import AuroraTeachingStrategy
from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import get_configured_llm_service

ALLOWED_ACTIONS = {
    "emit_message",
    "wait",
    "schedule_wake",
    "update_harness",
    "update_state",
    "soft_return_topic",
    "drop_thread",
}

FORBIDDEN_MODELING_DOMAINS = {
    "clinical_diagnosis",
    "personality_pathology",
    "unconscious_interpretation",
    "inferred_social_identity",
    "trauma_attribution",
    "mental_disorder",
    "stable_trait_label",
    "gender_identity",
    "sexual_orientation",
    "race_inference",
    "ethnicity_inference",
    "religion_inference",
    "class_inference",
    "diagnosis",
    "pathology",
    "personality_disorder",
}
ALLOWED_DOMAIN_GUARD_TERMS = {
    "diagnose_stuck_point",
    "diagnose_breakpoint",
    "diagnostic",
    "mistake_diagnosis",
    "root_cause_intervention",
    "checkpoint_repair",
    "error_analysis",
}

STRATEGY_FIELDS = (
    "concept_first",
    "problem_first",
    "worked_example_first",
    "retrieval_practice",
    "interleaving",
    "spaced_review",
    "error_analysis_required",
    "drop_low_roi_topics",
    "new_topic_allowed",
)
HIGH_URGENCY_SPRINT_MODES = {"seven_day_survival", "last_24h_cram"}
HIGH_URGENCY_TRIAGE_LEVELS = {"high", "emergency"}
STANDARD_LAYER_RESPONSE_TYPES = {
    "task_help",
    "plan_discussion",
    "emotional_support",
    "diagnostic",
    "calibration",
    "general_chat",
}
STANDARD_LAYER_MAX_RESPONSE_LENGTHS = {"brief", "normal", "extended"}
TASK_HELP_INTENTS = {
    "teach_with_example",
    "assign_questions",
    "handle_current_task_first",
    "continue_current_task",
    "diagnose_stuck_point",
    "task_help",
}
DIAGNOSTIC_INTENTS = {
    "diagnostic",
    "diagnose_breakpoint",
    "diagnose_stuck_point",
    "error_analysis",
    "checkpoint_repair",
    "root_cause_intervention",
}
CALIBRATION_INTENTS = {
    "calibration",
    "calibration_check",
    "assumption_check",
    "confirm_assumption",
}
TASK_HELP_STAGE_TOKENS = {
    "task_card",
    "current_task",
    "current_task_card",
    "practice",
    "execution",
    "doing",
    "solving",
    "drill",
    "repair",
}
FAILURE_STATE_TOKENS = {
    "failed",
    "failure",
    "timed_out",
    "timeout",
    "stuck",
    "derailed",
    "overwhelmed",
    "frustrated",
    "blocked",
}
STUCK_TASK_STAGE_TOKENS = {"stuck", "blocked"}
STANDARD_LAYER_RESPONSE_TYPE_ALIASES = {
    "task": "task_help",
    "task_support": "task_help",
    "taskhelp": "task_help",
    "plan": "plan_discussion",
    "planning": "plan_discussion",
    "emotion_support": "emotional_support",
    "support": "emotional_support",
    "diagnose": "diagnostic",
    "diag": "diagnostic",
    "recalibration": "calibration",
    "calibrate": "calibration",
    "chat": "general_chat",
}
STANDARD_LAYER_MAX_LENGTH_ALIASES = {
    "short": "brief",
    "medium": "normal",
    "long": "extended",
}
STANDARD_LAYER_TOKEN_ALIASES = {
    "one_worked_example": "worked_example",
    "worked_example_first": "worked_example",
    "worked_example": "worked_example",
    "three_practice_questions": "three_practice_questions",
    "practice_questions": "three_practice_questions",
    "completion_check": "completion_check",
    "emotional_acknowledgement": "emotional_acknowledgment",
    "emotional_acknowledgment": "emotional_acknowledgment",
    "one_concrete_next_step": "one_concrete_next_step",
    "concrete_next_step": "one_concrete_next_step",
    "full_week_replan": "full_week_replan",
    "long_motivational_speech": "long_motivational_speech",
    "long_motivation_speech": "long_motivational_speech",
    "plan_delta": "plan_delta_or_tradeoff",
    "plan_tradeoff": "plan_delta_or_tradeoff",
    "plan_delta_or_tradeoff": "plan_delta_or_tradeoff",
    "one_decision_or_question": "one_decision_or_question",
    "mistake_diagnosis": "mistake_diagnosis",
    "one_targeted_fix": "one_targeted_fix",
    "blame": "blame_or_shame",
    "blame_or_shame": "blame_or_shame",
    "explicit_uncertainty": "explicit_uncertainty",
    "calibration_question": "calibration_question_or_assumption_check",
    "assumption_check": "calibration_question_or_assumption_check",
    "calibration_question_or_assumption_check": "calibration_question_or_assumption_check",
    "overconfident_claim": "overconfident_claims",
    "overconfident_claims": "overconfident_claims",
    "high_pressure_task_load": "high_pressure_task_load",
    "direct_answer": "direct_answer_or_acknowledgment",
    "answer_or_acknowledgment": "direct_answer_or_acknowledgment",
    "direct_answer_or_acknowledgment": "direct_answer_or_acknowledgment",
    "unsolicited_three_practice_questions": "unsolicited_three_practice_questions",
    "safety_margin": "safety_margin",
    "safety_buffer": "safety_margin",
    "deep_learn": "deep_learn_allowed",
    "deep_learn_allowed": "deep_learn_allowed",
}
STANDARD_LAYER_TOKEN_DESCRIPTIONS = {
    "worked_example": "Include one concise worked example before asking the user to continue.",
    "three_practice_questions": "Include exactly three short practice questions or drills.",
    "completion_check": "End with a concrete check step so the user can reply with answers or status.",
    "emotional_acknowledgment": "Explicitly acknowledge the user's frustration, setback, or emotional load.",
    "one_concrete_next_step": "Give one immediate, concrete next action the user can take now.",
    "full_week_replan": "Do not drift into a full-week or multi-day replanning pass.",
    "long_motivational_speech": "Do not add a long encouragement speech or morale monologue.",
    "plan_delta_or_tradeoff": "Name the specific plan adjustment, tradeoff, or constraint that matters now.",
    "one_decision_or_question": "Close with one concrete decision, option, or missing-variable question.",
    "mistake_diagnosis": "Identify the likely breakpoint, error pattern, or misunderstanding.",
    "one_targeted_fix": "Offer one targeted repair step tied to the diagnosed mistake.",
    "blame_or_shame": "Do not blame, shame, or moralize the user's difficulty.",
    "explicit_uncertainty": "State uncertainty or calibration status explicitly instead of sounding overconfident.",
    "calibration_question_or_assumption_check": "Ask one calibration question or assumption-check to reduce uncertainty.",
    "overconfident_claims": "Do not present uncertain assumptions as settled facts.",
    "high_pressure_task_load": "Do not pile on a heavy new workload while calibration is unresolved.",
    "direct_answer_or_acknowledgment": "Give a direct answer or brief acknowledgment that matches the user's turn.",
    "unsolicited_three_practice_questions": "Do not inject a three-question drill unless the turn is task-help oriented.",
    "safety_margin": "Emphasize pass-first buffers, conservative scope, and fallback room instead of risky overload.",
    "deep_learn_allowed": "Allow deeper conceptual learning or stretch practice after the core pass line is protected.",
}
SLEEP_GUARD_MUST_NOT_INCLUDE = ("full_week_replan", "three_practice_questions")
SLEEP_GUARD_RULE = (
    "睡眠守卫激活：当前为深夜时段。不要增加任务密度，不要追加新内容，回复要简短，鼓励用户设置好第二天的计划后休息。"
)
STRATEGY_RECALIBRATION_RULE = (
    "当前策略已失效（连续 3 轮相同策略），必须切换到不同的 response_type 和不同的教学策略。"
    "优先选择 concept_first 或 worked_example_first。"
)

LLMFactory = Callable[[], Any | Awaitable[Any]]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class AuroraDecision:
    action: str = "wait"
    surface_complete: bool = False
    modeling_complete: bool = False
    state_updates: dict[str, Any] = field(default_factory=dict)
    harness_updates: dict[str, Any] = field(default_factory=dict)
    wake_schedule: dict[str, Any] | None = None
    chat_directive: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> AuroraDecision:
        if not isinstance(payload, Mapping):
            return cls(metadata={"fallback_reason": "non_mapping_decision"})
        return cls(
            action=str(payload.get("action") or "wait"),
            surface_complete=bool(payload.get("surface_complete")),
            modeling_complete=bool(payload.get("modeling_complete")),
            state_updates=dict(payload.get("state_updates") or {}),
            harness_updates=dict(payload.get("harness_updates") or {}),
            wake_schedule=(
                dict(payload.get("wake_schedule")) if isinstance(payload.get("wake_schedule"), Mapping) else None
            ),
            chat_directive=dict(payload.get("chat_directive") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "surface_complete": self.surface_complete,
            "modeling_complete": self.modeling_complete,
            "state_updates": self.state_updates,
            "harness_updates": self.harness_updates,
            "wake_schedule": self.wake_schedule,
            "chat_directive": self.chat_directive,
            "metadata": self.metadata,
        }


def _normalize_standard_layer_token(value: Any) -> str | None:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if not text:
        return None
    return STANDARD_LAYER_TOKEN_ALIASES.get(text, text)


def _normalize_standard_layer_token_list(value: Any) -> list[str]:
    items = value if isinstance(value, (list, tuple, set)) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = _normalize_standard_layer_token(item)
        if token and token not in seen:
            seen.add(token)
            normalized.append(token)
    return normalized


def _normalize_standard_layer_response_type(value: Any) -> str | None:
    token = _normalize_standard_layer_token(value)
    if not token:
        return None
    canonical = STANDARD_LAYER_RESPONSE_TYPE_ALIASES.get(token, token)
    return canonical if canonical in STANDARD_LAYER_RESPONSE_TYPES else None


def _normalize_standard_layer_length(value: Any) -> str | None:
    token = _normalize_standard_layer_token(value)
    if not token:
        return None
    canonical = STANDARD_LAYER_MAX_LENGTH_ALIASES.get(token, token)
    return canonical if canonical in STANDARD_LAYER_MAX_RESPONSE_LENGTHS else None


def describe_standard_layer_tokens(tokens: list[str] | None = None) -> dict[str, str]:
    if not tokens:
        return {}
    descriptions: dict[str, str] = {}
    for token in tokens:
        canonical = _normalize_standard_layer_token(token)
        if canonical and canonical in STANDARD_LAYER_TOKEN_DESCRIPTIONS:
            descriptions[canonical] = STANDARD_LAYER_TOKEN_DESCRIPTIONS[canonical]
    return descriptions


def _normalize_marker(value: Any) -> str | None:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or None


def _sleep_guard_context(readout: DashboardReadout) -> dict[str, Any]:
    request_context = readout.request_extra_context if isinstance(readout.request_extra_context, Mapping) else {}
    if request_context.get("sleep_guard_active") is not True:
        return {"active": False, "hint": ""}
    return {
        "active": True,
        "hint": str(request_context.get("sleep_guard_hint") or "").strip(),
    }


def _is_stressed_new_session_check_in(readout: DashboardReadout) -> bool:
    request_context = readout.request_extra_context if isinstance(readout.request_extra_context, Mapping) else {}
    if str(request_context.get("last_session_mood") or "").strip().lower() != "stressed":
        return False
    summary = readout.conversation_summary if isinstance(readout.conversation_summary, Mapping) else {}
    message_count = _safe_int(summary.get("message_count"))
    return message_count is None or message_count <= 1


def _strategy_recalibration_context(readout: DashboardReadout) -> dict[str, Any]:
    request_context = readout.request_extra_context if isinstance(readout.request_extra_context, Mapping) else {}
    if request_context.get("strategy_recalibration_needed") is not True:
        return {"active": False, "stuck_domain": ""}
    stuck_domain = (
        canonicalize_runtime_domain(request_context.get("stuck_domain"))
        or str(request_context.get("stuck_domain") or "").strip()
    )
    return {
        "active": True,
        "stuck_domain": stuck_domain,
    }


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_nonnegative_int(*values: Any) -> int | None:
    for value in values:
        parsed = _safe_int(value)
        if parsed is not None and parsed >= 0:
            return parsed
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
        return None
    return bool(value)


def _achievement_signal_state(readout: DashboardReadout) -> dict[str, Any]:
    signals = readout.achievement_signals if isinstance(readout.achievement_signals, Mapping) else {}
    active_streaks = signals.get("active_streaks")
    current_streak_days = _first_nonnegative_int(
        signals.get("current_streak_days"),
        signals.get("current_streak"),
        signals.get("streak_days"),
        signals.get("streak"),
    )
    gap_since_last_study_days = _first_nonnegative_int(
        signals.get("gap_since_last_study_days"),
        signals.get("days_since_last_study"),
        signals.get("study_gap_days"),
        signals.get("inactive_days"),
    )
    streak_active = _coerce_bool(signals.get("streak_active"))
    if streak_active is None:
        streak_active = (bool(active_streaks) if isinstance(active_streaks, list) else False) or bool(
            current_streak_days and current_streak_days > 0
        )
    recently_unlocked = _coerce_bool(signals.get("recently_unlocked"))
    if recently_unlocked is None:
        recent_unlocks = signals.get("recent_unlocks")
        recently_unlocked = bool(recent_unlocks) if isinstance(recent_unlocks, list) else False
    return {
        "momentum": _safe_float(signals.get("momentum")),
        "current_streak_days": current_streak_days,
        "gap_since_last_study_days": gap_since_last_study_days,
        "recently_unlocked": recently_unlocked,
        "streak_active": streak_active,
    }


def _achievement_recent_unlock_scene(readout: DashboardReadout) -> bool:
    state = _achievement_signal_state(readout)
    momentum = state.get("momentum")
    return momentum is not None and momentum > 0.7 and state["recently_unlocked"] is True


def _achievement_stalled_scene(readout: DashboardReadout) -> bool:
    state = _achievement_signal_state(readout)
    momentum = state.get("momentum")
    return momentum is not None and momentum < 0.2 and state["streak_active"] is False


def _achievement_high_streak_scene(readout: DashboardReadout) -> bool:
    state = _achievement_signal_state(readout)
    current_streak_days = state.get("current_streak_days")
    return current_streak_days is not None and current_streak_days >= 5


def _achievement_reentry_gap_scene(readout: DashboardReadout) -> bool:
    state = _achievement_signal_state(readout)
    gap_since_last_study_days = state.get("gap_since_last_study_days")
    return gap_since_last_study_days is not None and gap_since_last_study_days >= 3


def _achievement_signal_rules(readout: DashboardReadout) -> list[str]:
    state = _achievement_signal_state(readout)
    momentum = state.get("momentum")
    current_streak_days = state.get("current_streak_days")
    gap_since_last_study_days = state.get("gap_since_last_study_days")
    rules: list[str] = []
    if current_streak_days is not None and current_streak_days >= 5:
        rules.append(
            "Achievement streak rule: current_streak_days >= 5; set "
            "harness_updates.strategy.retrieval_practice = true to consolidate the current streak state, "
            "and allow direct_answer_or_acknowledgment in chat_directive.standard_layer_contract.must_include "
            "so Aurora can briefly confirm the user's momentum before the next challenge."
        )
    if gap_since_last_study_days is not None and gap_since_last_study_days >= 3:
        rules.append(
            "Achievement re-entry rule: gap_since_last_study_days >= 3; 减压 by lowering "
            "harness_updates.task_density_hint by 0.1 from the dashboard value, prefer "
            "response_type=emotional_support, and include one_concrete_next_step in the first response."
        )
    if momentum is not None and momentum > 0.7 and state["recently_unlocked"] is True:
        rules.append(
            "Achievement rule: momentum > 0.7 AND recently_unlocked == true; add "
            "direct_answer_or_acknowledgment to chat_directive.standard_layer_contract.must_include, "
            "briefly confirm progress, and do not add a new burden."
        )
    if momentum is not None and momentum < 0.2 and state["streak_active"] is False:
        rules.append(
            "Achievement rule: momentum < 0.2 AND streak_active == false; prefer response_type "
            "emotional_support, and add three_practice_questions to "
            "chat_directive.standard_layer_contract.must_not_include."
        )
    if state["streak_active"] is True:
        rules.append(
            "Achievement rule: streak_active == true; the response may briefly mention 连续打卡, but only as a side "
            "acknowledgment and never as a shift away from the user's current focus."
        )
    return rules


def _effective_strategy_flags(decision: AuroraDecision, readout: DashboardReadout) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for candidate in (
        readout.activity_profile.get("strategy"),
        decision.harness_updates.get("strategy"),
    ):
        if not isinstance(candidate, Mapping):
            continue
        for field in STRATEGY_FIELDS:
            if field in candidate:
                merged[field] = bool(candidate[field])
    return merged


def _intent_token(decision: AuroraDecision) -> str | None:
    directive = decision.chat_directive if isinstance(decision.chat_directive, Mapping) else {}
    return _normalize_marker(directive.get("intent"))


def _deep_pattern_alerts(readout: DashboardReadout) -> list[dict[str, Any]]:
    cold_start = readout.cold_start_context if isinstance(readout.cold_start_context, Mapping) else {}
    alerts = cold_start.get("deep_pattern_alerts")
    if not isinstance(alerts, list):
        return []
    return [dict(alert) for alert in alerts if isinstance(alert, Mapping) and alert.get("recurring") is True]


def _has_deep_pattern_alerts(readout: DashboardReadout) -> bool:
    return bool(_deep_pattern_alerts(readout))


def _task_stage_tokens(readout: DashboardReadout) -> set[str]:
    tokens: set[str] = set()
    for value in (
        readout.task_state.get("stage"),
        readout.task_state.get("status"),
        readout.task_state.get("mode"),
        readout.checkpoint_state.get("last_status"),
        readout.checkpoint_state.get("status"),
    ):
        token = _normalize_marker(value)
        if token:
            tokens.add(token)
    return tokens


def _iter_text_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, Mapping):
        for nested in value.values():
            values.extend(_iter_text_values(nested))
        return values
    if isinstance(value, (list, tuple, set)):
        for item in value:
            values.extend(_iter_text_values(item))
        return values
    if value in (None, "", [], {}):
        return values
    values.append(str(value))
    return values


def _motivation_context_text(readout: DashboardReadout) -> str:
    candidate_texts: list[str] = []

    def collect_keyed_values(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                key_text = str(key or "").lower()
                if "motivation" in key_text or key_text in {"reason", "why", "purpose", "pressure"}:
                    candidate_texts.extend(_iter_text_values(nested))
                collect_keyed_values(nested)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect_keyed_values(item)

    for source in (
        readout.request_extra_context,
        readout.cold_start_context,
        readout.profile_context,
        readout.task_state,
        readout.exam_sprint_policy,
    ):
        collect_keyed_values(source)
    candidate_texts.append(str(readout.user_message or ""))
    return " ".join(text for text in candidate_texts if text).lower()


def _motivation_kind(readout: DashboardReadout) -> str | None:
    if "motivation" not in set(readout.covered_domains):
        return None
    text = _motivation_context_text(readout)
    if any(marker in text for marker in ("必须过", "一定要过", "不能挂", "不挂科", "不想挂", "保底", "过线")):
        return "must_pass"
    if any(marker in text for marker in ("想拿高分", "尽量考高分", "考高分", "冲高分", "高分", "拿高分")):
        return "high_score"
    if any(marker in text for marker in ("探索兴趣", "探索", "兴趣", "想了解")):
        return "explore_interest"
    return None


def _failure_streak(readout: DashboardReadout) -> int:
    candidates = (
        readout.self_model.get("task_failure_streak"),
        readout.task_state.get("failure_streak"),
        readout.checkpoint_state.get("failure_streak"),
        readout.checkpoint_state.get("recent_failures"),
    )
    numeric = [_safe_int(value) for value in candidates]
    return max((value for value in numeric if value is not None), default=0)


def _is_emotional_support_scene(decision: AuroraDecision, readout: DashboardReadout) -> bool:
    if _failure_streak(readout) >= 2:
        return True
    if _task_stage_tokens(readout).intersection(FAILURE_STATE_TOKENS):
        return True
    text = str(readout.user_message or "").lower()
    return any(marker in text for marker in ("连续失败", "一直错", "崩了", "学不会", "frustrat", "failed"))


def _is_calibration_scene(decision: AuroraDecision, readout: DashboardReadout) -> bool:
    self_model = readout.self_model if isinstance(readout.self_model, Mapping) else {}
    if bool(self_model.get("needs_recalibration")):
        return True
    confidence = self_model.get("strategy_confidence")
    try:
        if confidence is not None and float(confidence) <= 0.45:
            return True
    except (TypeError, ValueError):
        pass
    return _intent_token(decision) in CALIBRATION_INTENTS


def _is_diagnostic_scene(decision: AuroraDecision, readout: DashboardReadout) -> bool:
    if _has_deep_pattern_alerts(readout):
        return True
    if readout.surface == "aurora_checkpoint":
        return True
    strategy = _effective_strategy_flags(decision, readout)
    if strategy.get("error_analysis_required"):
        return True
    return _intent_token(decision) in DIAGNOSTIC_INTENTS


def _is_task_help_scene(decision: AuroraDecision, readout: DashboardReadout) -> bool:
    task_state = readout.task_state if isinstance(readout.task_state, Mapping) else {}
    if _is_stuck_task_scene(readout):
        return True
    if _intent_token(decision) in TASK_HELP_INTENTS:
        return True
    if any(task_state.get(key) for key in ("task_card_id", "current_task_id", "current_task")):
        return True
    if _task_stage_tokens(readout).intersection(TASK_HELP_STAGE_TOKENS):
        return True
    return False


def _is_stuck_task_scene(readout: DashboardReadout) -> bool:
    task_state = readout.task_state if isinstance(readout.task_state, Mapping) else {}
    stage = _normalize_marker(task_state.get("stage"))
    if stage in STUCK_TASK_STAGE_TOKENS:
        return True
    request_context = readout.request_extra_context if isinstance(readout.request_extra_context, Mapping) else {}
    if isinstance(request_context.get("stuck_event"), Mapping):
        return True
    return _normalize_marker(request_context.get("task_stage")) in STUCK_TASK_STAGE_TOKENS


def _infer_standard_layer_response_type(
    decision: AuroraDecision,
    readout: DashboardReadout,
    contract: Mapping[str, Any] | None = None,
) -> str:
    requested = _normalize_standard_layer_response_type((contract or {}).get("response_type"))
    motivation_kind = _motivation_kind(readout)
    if _has_deep_pattern_alerts(readout):
        return "diagnostic"
    if _is_stressed_new_session_check_in(readout):
        return "emotional_support"
    if _is_stuck_task_scene(readout):
        return "diagnostic"
    if _is_emotional_support_scene(decision, readout):
        return "emotional_support"
    if _achievement_stalled_scene(readout):
        return "emotional_support"
    if _achievement_reentry_gap_scene(readout):
        return "emotional_support"
    if _is_calibration_scene(decision, readout):
        return "calibration"
    if _is_diagnostic_scene(decision, readout):
        return "diagnostic"
    if motivation_kind == "must_pass":
        return "emotional_support"
    if _is_task_help_scene(decision, readout):
        return "task_help"
    if motivation_kind == "high_score":
        return "task_help"
    if readout.surface == "aurora_planning":
        return "plan_discussion"
    return requested or "general_chat"


def _default_standard_layer_contract(
    response_type: str,
    decision: AuroraDecision,
    readout: DashboardReadout,
) -> dict[str, Any]:
    strategy = _effective_strategy_flags(decision, readout)
    motivation_kind = _motivation_kind(readout)
    if response_type == "task_help":
        must_include: list[str] = []
        if strategy.get("worked_example_first") or _is_task_help_scene(decision, readout):
            must_include.append("worked_example")
        if (
            strategy.get("problem_first")
            or strategy.get("retrieval_practice")
            or _is_task_help_scene(decision, readout)
        ):
            must_include.append("three_practice_questions")
        if must_include or strategy.get("error_analysis_required"):
            must_include.append("completion_check")
        if not must_include:
            must_include.append("one_concrete_next_step")
        if motivation_kind == "high_score":
            must_include.append("deep_learn_allowed")
        return {
            "response_type": response_type,
            "must_include": must_include,
            "must_not_include": ["full_week_replan", "long_motivational_speech"],
            "max_response_length": "extended",
        }
    if response_type == "plan_discussion":
        return {
            "response_type": response_type,
            "must_include": ["plan_delta_or_tradeoff", "one_decision_or_question"],
            "must_not_include": ["long_motivational_speech", "unsolicited_three_practice_questions"],
            "max_response_length": "normal",
        }
    if response_type == "emotional_support":
        must_include = ["emotional_acknowledgment", "one_concrete_next_step"]
        if motivation_kind == "must_pass":
            must_include.append("safety_margin")
        return {
            "response_type": response_type,
            "must_include": must_include,
            "must_not_include": ["full_week_replan", "long_motivational_speech", "blame_or_shame"],
            "max_response_length": "normal",
        }
    if response_type == "diagnostic":
        if _is_stuck_task_scene(readout):
            return {
                "response_type": response_type,
                "must_include": ["mistake_diagnosis", "one_targeted_fix"],
                "must_not_include": ["full_week_replan", "long_motivational_speech", "three_practice_questions"],
                "max_response_length": "normal",
            }
        return {
            "response_type": response_type,
            "must_include": ["mistake_diagnosis", "one_targeted_fix"],
            "must_not_include": ["full_week_replan", "long_motivational_speech"],
            "max_response_length": "normal",
        }
    if response_type == "calibration":
        return {
            "response_type": response_type,
            "must_include": ["explicit_uncertainty", "calibration_question_or_assumption_check"],
            "must_not_include": ["overconfident_claims", "high_pressure_task_load", "long_motivational_speech"],
            "max_response_length": "brief",
        }
    return {
        "response_type": "general_chat",
        "must_include": ["direct_answer_or_acknowledgment"],
        "must_not_include": ["full_week_replan", "long_motivational_speech"],
        "max_response_length": "brief",
    }


def build_standard_layer_contract(decision: AuroraDecision, readout: DashboardReadout) -> dict[str, Any]:
    directive = decision.chat_directive if isinstance(decision.chat_directive, Mapping) else {}
    raw_contract = directive.get("standard_layer_contract")
    contract = dict(raw_contract) if isinstance(raw_contract, Mapping) else {}
    response_type = _infer_standard_layer_response_type(decision, readout, contract)
    defaults = _default_standard_layer_contract(response_type, decision, readout)
    must_not_include = _normalize_standard_layer_token_list(defaults.get("must_not_include"))
    must_not_include.extend(
        token
        for token in _normalize_standard_layer_token_list(contract.get("must_not_include"))
        if token not in must_not_include
    )
    if _achievement_stalled_scene(readout) and "three_practice_questions" not in must_not_include:
        must_not_include.append("three_practice_questions")
    if _sleep_guard_context(readout).get("active"):
        must_not_include.extend(token for token in SLEEP_GUARD_MUST_NOT_INCLUDE if token not in must_not_include)
    must_include = [
        token
        for token in _normalize_standard_layer_token_list(defaults.get("must_include"))
        + _normalize_standard_layer_token_list(contract.get("must_include"))
        if token not in must_not_include
    ]
    if _achievement_recent_unlock_scene(readout) and "direct_answer_or_acknowledgment" not in must_not_include:
        must_include.append("direct_answer_or_acknowledgment")
    if _achievement_high_streak_scene(readout) and "direct_answer_or_acknowledgment" not in must_not_include:
        must_include.append("direct_answer_or_acknowledgment")
    deduped_include: list[str] = []
    seen_include: set[str] = set()
    for token in must_include:
        if token not in seen_include:
            seen_include.add(token)
            deduped_include.append(token)
    max_response_length = _normalize_standard_layer_length(contract.get("max_response_length")) or str(
        defaults.get("max_response_length") or "normal"
    )
    if _sleep_guard_context(readout).get("active"):
        max_response_length = "brief"
    return {
        "response_type": response_type,
        "must_include": deduped_include,
        "must_not_include": must_not_include,
        "max_response_length": max_response_length,
    }


class AuroraDecisionLoop:
    """LLM-driven Aurora cognition.

    This class decides what Aurora should do. It must not write final user
    messages; that is the ChatLayerAdapter's job.
    """

    def __init__(
        self,
        *,
        llm_factory: LLMFactory | None = None,
        temperature: float = 0.15,
    ) -> None:
        self.llm_factory = llm_factory or self._default_llm_factory
        self.temperature = temperature

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        messages = self.build_prompt(readout)
        try:
            llm = await self._resolve_llm()
            raw = await llm.chat_json(
                messages,
                temperature=self.temperature,
                max_tokens=self._max_tokens_for_readout(readout),
            )
        except Exception as exc:
            logger.warning("Aurora decision loop fell back after LLM failure: {}", exc)
            return self._fallback_decision(readout, reason="llm_failure")

        decision = AuroraDecision.from_payload(raw)
        return self.validate_decision(decision, readout)

    def build_prompt(self, readout: DashboardReadout) -> list[dict[str, str]]:
        wake_policy = self._wake_policy_from_readout(readout)
        schema = {
            "action": sorted(ALLOWED_ACTIONS),
            "surface_complete": "boolean",
            "modeling_complete": "boolean",
            "state_updates": "object",
            "harness_updates": {
                "type": "object",
                "allowed_fields": [
                    "proactive_intensity",
                    "next_wake_at",
                    "conversation_style",
                    "expression",
                    "agenda_priority",
                    "task_density_hint",
                    "strategy",
                ],
                "strategy": dict.fromkeys(STRATEGY_FIELDS, "boolean"),
            },
            "wake_schedule": "object or null",
            "chat_directive": {
                "intent": "string",
                "target_domain": "string or null",
                "standard_layer_contract": {
                    "response_type": sorted(STANDARD_LAYER_RESPONSE_TYPES),
                    "must_include": "list[str]",
                    "must_not_include": "list[str]",
                    "max_response_length": sorted(STANDARD_LAYER_MAX_RESPONSE_LENGTHS),
                },
            },
            "metadata": {"reasoning_summary": "brief, non-sensitive rationale"},
        }
        system = (
            "You are Aurora's cognitive decision loop for Sparkle. "
            "You are NOT the final chat writer. Decide what should happen next from action-masked dashboard readouts. "
            "Return strict JSON only. "
            "Do not generate final user-facing text or polished dialogue. "
            "Do not make clinical diagnoses, personality/pathology labels, unconscious interpretations, trauma claims, "
            "or inferred social identity guesses. Social roles must come only from explicit user-provided data. "
            "Action semantics are strict: emit_message = send a user-visible response now; wait = no visible response now; "
            "soft_return_topic = gently recover a latent thread after handling the current detour; "
            "drop_thread = abandon an outdated latent thread only when it is no longer worth recovering. "
            "Only ask about domains still missing from the dashboard. Never re-ask a domain that is already covered or "
            "appears in recently_asked_domains. modeling_complete must follow dashboard coverage, not user keywords like "
            "'差不多了' or '就这些'. Optimize for concrete user value: better goal fit, less execution friction, "
            "earlier bottleneck detection. "
            "When covered_domains already has 2 or more domains, confirm the known information in a natural coaching "
            "tone and ask only the single most important remaining gap. "
            "When setting informational_tensions, include importance_reasoning explaining why this gap blocks downstream "
            "planning (e.g. 'baseline 缺失会导致任务难度无法个性化'). "
            "Use self_model as Aurora's self-check: when strategy_confidence is low, task_failure_streak is high, or "
            "needs_recalibration is true, prefer shorter and safer next steps, lower task density, and avoid assuming "
            "the user can sustain the previous workload estimate. "
            "motivation domain is optional — ask about it if covered_domains has goal/scope/baseline/time but not motivation. "
            "When motivation is covered and the value is '必须过', prefer response_type=emotional_support and emphasize safety margin; "
            "when the value is '想拿高分', prefer response_type=task_help and allow deep learn. "
            "Teaching strategy is a first-class decision. Always set harness_updates.strategy with the boolean switches "
            "concept_first, problem_first, worked_example_first, retrieval_practice, interleaving, spaced_review, "
            "and error_analysis_required. Use concept_first when the user needs conceptual scaffolding before more tasks. "
            "Use problem_first when concepts are already mostly understood and practice is the best next move. "
            "Use worked_example_first when confusion is high or exam urgency is high and you need one concrete anchor fast. "
            "Use retrieval_practice for recall checks, mini-tests, or closed-book prompts. Use interleaving for mixed "
            "nearby problem types. Use spaced_review when earlier material should be resurfaced. Use "
            "error_analysis_required when repeated mistakes, transition errors, or misunderstanding patterns should be "
            "diagnosed before more drilling. Default strategy heuristics matter: aurora_modeling should usually lean "
            "concept_first=true; aurora_planning should usually lean problem_first=true; high exam urgency should "
            "usually lean worked_example_first=true unless stronger evidence suggests otherwise. "
            "Always populate chat_directive.standard_layer_contract with all four fields. "
            "Choose response_type from task_help, plan_discussion, emotional_support, diagnostic, calibration, or general_chat. "
            "Scene guidance: active task/card help should usually be task_help; planning turns should usually be "
            "plan_discussion; repeated failure or frustration should usually be emotional_support; checkpoint or "
            "mistake-analysis turns should usually be diagnostic; low-confidence self-model or assumption-check turns "
            "should usually be calibration. "
            "When cold_start_context.deep_pattern_alerts is non-empty, prioritize root-cause diagnosis before normal "
            "task help: set chat_directive.intent exactly to root_cause_intervention, set "
            "chat_directive.standard_layer_contract.response_type to diagnostic, and base the move on "
            "root_cause_hypothesis plus recommended_intervention. "
            "must_include and must_not_include are hard content constraints for the standard chat layer, not style suggestions. "
            "Use concise canonical tokens such as worked_example, three_practice_questions, completion_check, "
            "emotional_acknowledgment, one_concrete_next_step, full_week_replan, and long_motivational_speech. "
            "When the previous Aurora turn asked a completion_check and the user correctly restates the knowledge point, "
            "choose action=emit_message and include state_updates.correct_answer_node=<node_id>. "
            "Use only node_id values from the Sprint Pack, especially cold_start_context.sprint_pack_nodes; omit the field when unsure."
        )
        wake_instruction = str(wake_policy.get("diagnostic_prompt") or "").strip()
        if wake_instruction:
            system = f"{system} {wake_instruction}"
        recalibration = _strategy_recalibration_context(readout)
        if recalibration.get("active"):
            system = f"{system} {STRATEGY_RECALIBRATION_RULE}"
        user = {
            "decision_schema": schema,
            "dashboard_readout": self._slim_readout_for_surface(readout),
            "strategy_defaults": self._strategy_defaults_for_readout(readout),
            "current_strategy": self._normalize_strategy_payload(
                readout.activity_profile.get("strategy"),
                include_defaults=False,
            ),
            "wake_policy": wake_policy,
            "rules": [
                "If the user is detouring and the detour matters more, choose wait or emit_message without forcing topic return.",
                "If dashboard_readout.surface_state.in_detour is true, use latent_thread_recovery_candidates to decide whether a soft_return_topic is warranted.",
                "If a latent thread should be gently recovered, choose soft_return_topic.",
                "If dashboard coverage already closes the core modeling domains, stop asking questions and let modeling_complete become true.",
                "If you need more information, put the missing domain in state_updates.informational_tensions.",
                "Always return harness_updates.strategy with all seven boolean fields, starting from strategy_defaults and overriding them only when current evidence warrants it.",
                "Always return chat_directive.standard_layer_contract with response_type, must_include, must_not_include, and max_response_length.",
                "Treat standard_layer_contract.must_include and must_not_include as structural requirements for the chat layer, not soft preferences.",
                "Never request or infer forbidden psychological or social-identity domains.",
            ],
        }
        if readout.social_signals:
            user["rules"].append(
                "Rule Z social boundary: social_signals are aggregate collaboration hints only. "
                "Do not infer social identity, name or contact third parties, or push social/accountability actions "
                "unless the user explicitly asks for that direction."
            )
        user["rules"].extend(_achievement_signal_rules(readout))
        deep_pattern_alerts = _deep_pattern_alerts(readout)
        if deep_pattern_alerts:
            user["rules"].append(
                "Deep pattern alert rule: cold_start_context.deep_pattern_alerts is non-empty, so prioritize 根因干预. "
                "Set chat_directive.intent='root_cause_intervention', set "
                "chat_directive.standard_layer_contract.response_type='diagnostic', and do not downgrade this turn to "
                "task_help just because a current task exists."
            )
        if recalibration.get("active"):
            stuck_domain = recalibration.get("stuck_domain") or "unknown"
            user["rules"].append(
                f"Strategy recalibration is required for stuck_domain={stuck_domain}; switch away from the repeated response_type and teaching strategy."
            )
        sleep_guard = _sleep_guard_context(readout)
        if sleep_guard.get("active"):
            sleep_guard_rule = SLEEP_GUARD_RULE
            if sleep_guard.get("hint"):
                sleep_guard_rule = f"{sleep_guard_rule} sprint_policy.sleep_guard_hint：{sleep_guard['hint']}"
            user["rules"].append(sleep_guard_rule)
            user["chat_directive_constraints"] = {
                "assistant_tone_constraints": [sleep_guard["hint"]] if sleep_guard.get("hint") else [],
                "must_not_include": list(SLEEP_GUARD_MUST_NOT_INCLUDE),
                "standard_layer_contract_must_not_include": list(SLEEP_GUARD_MUST_NOT_INCLUDE),
                "max_response_length": "brief",
            }
        energy = str(wake_policy.get("energy") or "silent").lower()
        if energy == "moderate":
            user["rules"].append(
                "Moderate wake means a lightweight diagnostic nudge: do not start a full calibration dialogue, and prefer one concise reminder tied to the current bottleneck."
            )
        elif energy == "full" and wake_policy.get("full_allowed"):
            user["rules"].append(
                "Full wake is allowed: Aurora may initiate a more explicit calibration move, widen the context it uses, and structure a short multi-step reset."
            )
        elif wake_policy.get("full_candidate") and not wake_policy.get("full_allowed"):
            user["rules"].append(
                "A full wake candidate is on cooldown, so stay below full-calibration intensity and keep the intervention lighter."
            )
        if _is_stuck_task_scene(readout):
            user["rules"].append(
                "Task stuck rule: when dashboard_readout.task_state.stage is stuck or blocked, set "
                "chat_directive.intent='diagnose_stuck_point' instead of continue_current_task. "
                "Use micro_teaching: first narrow the stuck point with one two-choice diagnosis, then provide only "
                "one targeted fix after the user's answer. standard_layer_contract.must_include must contain "
                "mistake_diagnosis and one_targeted_fix; standard_layer_contract.must_not_include must contain "
                "full_week_replan and three_practice_questions."
            )
        # Last-24h mode overrides: detected from readout.last_24h_mode or exam_sprint_policy sprint_mode.
        _in_last_24h = bool(
            getattr(readout, "last_24h_mode", False)
            or (
                isinstance(readout.exam_sprint_policy, Mapping)
                and readout.exam_sprint_policy.get("sprint_mode") == "last_24h_cram"
            )
            or (
                isinstance(readout.exam_sprint_policy, Mapping)
                and readout.exam_sprint_policy.get("last_24h_mode") is True
            )
        )
        if _in_last_24h:
            user["rules"].append(
                "LAST-24H EXAM MODE is active. "
                "Do NOT probe for new information, open new modeling domains, or increase task density. "
                "The exam is tomorrow — the user needs confidence, stability, and final-pass reinforcement, not new calibration. "
                "Focus exclusively on high-yield review, error-book recall, and short mock items that are already scoped. "
                "response_type must be task_help or emotional_support — never calibration or diagnostic unless the user explicitly asks "
                "or cold_start_context.deep_pattern_alerts is non-empty. "
                "Keep responses short and reassuring. new_topic_allowed is false."
            )
        # F18: Inject Sprint Pack aurora hint into system prompt when available.
        _aurora_hint = (
            readout.cold_start_context.get("sprint_pack_aurora_hint")
            if isinstance(readout.cold_start_context, Mapping)
            else None
        )
        if _aurora_hint:
            system = f"{system} Sprint Pack自适应提示：{_aurora_hint}"
        # Spine signal awareness: if Spine has active directives or risk flags, inform the decision loop
        _spine = readout.spine_signals
        if isinstance(_spine, dict) and _spine:
            _spine_active = _spine.get("active_directive")
            _spine_risks = _spine.get("risk_flags", [])
            _spine_outcomes = _spine.get("recent_outcomes_summary")
            _spine_trust = _spine.get("relationship_trust")
            _spine_rules: list[str] = []
            if _spine_active:
                _spine_rules.append(
                    f"Spine active directive: strategy={_spine_active.get('strategy')}, "
                    f"reason={_spine_active.get('reason')}. "
                    "Honor this directive in your response — adjust tone, content scope, or task suggestions accordingly."
                )
            if _spine_risks:
                _spine_rules.append(
                    f"Spine risk flags detected: {', '.join(_spine_risks)}. "
                    "Consider these risks when calibrating difficulty and pacing."
                )
            if _spine_outcomes:
                _recent_effective = sum(1 for o in _spine_outcomes if o.get("effectiveness") == "effective")
                _recent_total = len(_spine_outcomes)
                if _recent_total >= 3 and _recent_effective / _recent_total < 0.4:
                    _spine_rules.append(
                        "Spine outcome history shows low intervention effectiveness. "
                        "Prefer lighter interventions and avoid repeating recently failed strategies."
                    )
            if _spine_trust is not None and _spine_trust < 0.3:
                _spine_rules.append(
                    "User-AI relationship trust is low. Reduce proactive suggestions, increase user choice, and avoid prescriptive framing."
                )
            if _spine_rules:
                user["rules"].extend(_spine_rules)
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, default=str)},
        ]

    def validate_decision(self, decision: AuroraDecision, readout: DashboardReadout) -> AuroraDecision:
        if decision.action not in ALLOWED_ACTIONS:
            return self._fallback_decision(readout, reason="illegal_action")

        hard_bounds = readout.hard_bounds
        if hard_bounds.is_action_disabled(decision.action):
            return self._fallback_decision(readout, reason="disabled_action")

        if self._contains_forbidden_domain(decision.to_payload()):
            return self._fallback_decision(readout, reason="forbidden_modeling_domain")

        if decision.harness_updates:
            try:
                decision.harness_updates = ControlSurfaceService.validate_harness_update(
                    ControlSurfaceService,
                    decision.harness_updates,
                    hard_bounds=hard_bounds,
                )
            except HarnessUpdateRejectedError as exc:
                decision.harness_updates = self._merge_strategy_harness_updates({}, readout)
                decision.metadata = {
                    **decision.metadata,
                    "harness_update_rejected": True,
                    "harness_update_errors": list(exc.errors),
                }
        agenda_priority = decision.harness_updates.get("agenda_priority")
        if agenda_priority:
            decision.harness_updates["agenda_priority"] = canonicalize_runtime_domain(agenda_priority) or str(
                agenda_priority
            )

        if hard_bounds.is_action_disabled("proactive_follow_up") and decision.action == "schedule_wake":
            return self._fallback_decision(readout, reason="proactive_follow_up_disabled")

        if decision.wake_schedule:
            decision.wake_schedule = self._validate_wake_schedule(decision.wake_schedule, hard_bounds)
            if decision.wake_schedule is None and decision.action == "schedule_wake":
                decision.action = "wait"

        decision = self._stabilize_decision(decision, readout)
        decision = self._revalidate_stabilized_decision(decision, readout)
        if decision.metadata.get("fallback_reason"):
            return decision
        decision.metadata = {
            **decision.metadata,
            "covered_domains": list(readout.covered_domains),
            "missing_domains": list(readout.missing_domains),
            "recently_asked_domains": list(readout.recently_asked_domains),
            "selected_target_domain": self._extract_target_domain(decision),
            "decision_validated_at": _utcnow().isoformat(),
        }
        return decision

    def _validate_wake_schedule(
        self,
        wake_schedule: dict[str, Any],
        hard_bounds: AuroraHardBounds,
    ) -> dict[str, Any] | None:
        if hard_bounds.is_action_disabled("proactive_follow_up"):
            return None
        raw_time = wake_schedule.get("scheduled_at") or wake_schedule.get("next_wake_at")
        when = self._coerce_datetime(raw_time)
        if when is not None and hard_bounds.is_within_dnd(when):
            return None
        return dict(wake_schedule)

    def _contains_forbidden_domain(self, payload: Any) -> bool:
        text = json.dumps(payload, ensure_ascii=False, default=str).lower()
        for allowed in ALLOWED_DOMAIN_GUARD_TERMS:
            text = text.replace(allowed, "")
        return any(token in text for token in FORBIDDEN_MODELING_DOMAINS)

    def _revalidate_stabilized_decision(self, decision: AuroraDecision, readout: DashboardReadout) -> AuroraDecision:
        hard_bounds = readout.hard_bounds

        if self._contains_forbidden_domain(decision.to_payload()):
            return self._fallback_decision(readout, reason="forbidden_modeling_domain")

        blocked_domain = self._find_privacy_blocked_domain(decision, hard_bounds)
        if blocked_domain:
            return self._fallback_decision(readout, reason="privacy_blocked_domain")

        if decision.harness_updates:
            try:
                decision.harness_updates = ControlSurfaceService.validate_harness_update(
                    ControlSurfaceService,
                    decision.harness_updates,
                    hard_bounds=hard_bounds,
                )
            except HarnessUpdateRejectedError as exc:
                decision.harness_updates = self._merge_strategy_harness_updates({}, readout)
                decision.metadata = {
                    **decision.metadata,
                    "harness_update_rejected": True,
                    "harness_update_errors": list(exc.errors),
                }

        agenda_priority = decision.harness_updates.get("agenda_priority")
        if agenda_priority:
            decision.harness_updates["agenda_priority"] = canonicalize_runtime_domain(agenda_priority) or str(
                agenda_priority
            )

        return decision

    def _find_privacy_blocked_domain(
        self,
        decision: AuroraDecision,
        hard_bounds: AuroraHardBounds,
    ) -> str | None:
        for domain in self._iter_decision_domains(decision):
            if hard_bounds.is_privacy_blocked(domain):
                return domain
        return None

    def _iter_decision_domains(self, decision: AuroraDecision) -> list[str]:
        domains: list[str] = []
        seen: set[str] = set()

        def _push(candidate: Any) -> None:
            canonical = canonicalize_runtime_domain(candidate)
            if canonical and canonical not in seen:
                seen.add(canonical)
                domains.append(canonical)

        directive = decision.chat_directive or {}
        _push(directive.get("target_domain"))
        _push(directive.get("question_domain"))
        _push(directive.get("domain"))
        _push(decision.harness_updates.get("agenda_priority"))
        for item in decision.state_updates.get("informational_tensions") or []:
            if isinstance(item, Mapping):
                _push(item.get("domain"))

        return domains

    def _stabilize_decision(self, decision: AuroraDecision, readout: DashboardReadout) -> AuroraDecision:
        normalized = AuroraDecision.from_payload(decision.to_payload())
        normalized.state_updates = self._normalize_state_updates(normalized.state_updates)

        covered_domains = set(readout.covered_domains)
        missing_domains = [domain for domain in readout.missing_domains if domain not in covered_domains]
        preferred_missing = self._select_missing_domain(readout, exclude_recent=True)
        target_domain = self._extract_target_domain(normalized)
        recent_domains = set(readout.recently_asked_domains)
        deep_pattern_active = _has_deep_pattern_alerts(readout)

        if target_domain in covered_domains:
            normalized.metadata = {
                **normalized.metadata,
                "retargeted_from_resolved_domain": target_domain,
            }
            target_domain = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)

        if target_domain in recent_domains:
            next_missing = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)
            if next_missing and next_missing != target_domain:
                normalized.metadata = {
                    **normalized.metadata,
                    "retargeted_from_repeated_domain": target_domain,
                }
                target_domain = next_missing

        if normalized.action == "soft_return_topic":
            candidate = self._select_latent_candidate(readout, exclude_recent=True) or self._select_latent_candidate(
                readout,
                exclude_recent=False,
            )
            if candidate is None:
                normalized.metadata = {
                    **normalized.metadata,
                    "action_rewritten": "soft_return_without_recovery_candidate",
                }
                normalized.action = "emit_message" if missing_domains else "wait"
                target_domain = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)
            else:
                target_domain = candidate["target_domain"]
                normalized.chat_directive = {
                    **normalized.chat_directive,
                    "intent": normalized.chat_directive.get("intent") or "soft_return_topic",
                    "target_domain": target_domain,
                    "thread_id": candidate["thread_id"],
                }

        if normalized.action == "drop_thread":
            normalized = self._stabilize_drop_thread(normalized, readout)
            target_domain = self._extract_target_domain(normalized)

        if (
            normalized.action in {"emit_message", "update_harness", "update_state"}
            and not target_domain
            and missing_domains
            and not deep_pattern_active
        ):
            target_domain = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)

        if target_domain:
            normalized = self._apply_target_domain(normalized, target_domain, readout)
        elif missing_domains and normalized.action in {"emit_message", "soft_return_topic"} and not deep_pattern_active:
            fallback_domain = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)
            if fallback_domain:
                normalized = self._apply_target_domain(normalized, fallback_domain, readout)

        modeling_complete = self._resolve_modeling_complete(readout)
        normalized.modeling_complete = modeling_complete
        if readout.surface == "aurora_modeling":
            normalized.surface_complete = modeling_complete

        if modeling_complete:
            normalized.state_updates = {
                **normalized.state_updates,
                "informational_tensions": [],
            }
            normalized.harness_updates.pop("agenda_priority", None)
            if normalized.action == "soft_return_topic":
                normalized.action = "emit_message"
            target_domain = self._extract_target_domain(normalized)
            if target_domain:
                normalized.chat_directive = {
                    key: value
                    for key, value in normalized.chat_directive.items()
                    if key not in {"target_domain", "domain", "question_domain"}
                }
            normalized.chat_directive = {
                **normalized.chat_directive,
                "intent": normalized.chat_directive.get("intent") or "confirm_modeling_ready",
            }
        if _is_stuck_task_scene(readout):
            normalized.chat_directive = {
                **normalized.chat_directive,
                "intent": "diagnose_stuck_point",
                "micro_teaching_mode": True,
            }
        if _is_stressed_new_session_check_in(readout):
            normalized.action = "emit_message"
            normalized.chat_directive = {
                key: value
                for key, value in normalized.chat_directive.items()
                if key not in {"target_domain", "domain", "question_domain"}
            }
            normalized.chat_directive["intent"] = "empathy_check_in"
        if deep_pattern_active:
            normalized.chat_directive = {
                key: value
                for key, value in normalized.chat_directive.items()
                if key not in {"target_domain", "domain", "question_domain"}
            }
            normalized.chat_directive["intent"] = "root_cause_intervention"
            strategy = dict(normalized.harness_updates.get("strategy") or {})
            strategy.update(
                {
                    "concept_first": True,
                    "problem_first": False,
                    "error_analysis_required": True,
                }
            )
            normalized.harness_updates = {
                **normalized.harness_updates,
                "strategy": strategy,
            }
        normalized.chat_directive = {
            **normalized.chat_directive,
            "standard_layer_contract": build_standard_layer_contract(normalized, readout),
        }
        if not normalized.metadata.get("fallback_reason") and not normalized.metadata.get("harness_update_rejected"):
            normalized.harness_updates = self._merge_strategy_harness_updates(normalized.harness_updates, readout)
        return normalized

    def _stabilize_drop_thread(self, decision: AuroraDecision, readout: DashboardReadout) -> AuroraDecision:
        target_domain = self._extract_target_domain(decision)
        matching = None
        for candidate in readout.latent_thread_recovery_candidates:
            candidate_domain = canonicalize_runtime_domain(candidate.get("target_domain"))
            if target_domain and candidate_domain == target_domain:
                matching = candidate
                break
        if matching is None and readout.latent_thread_recovery_candidates:
            matching = readout.latent_thread_recovery_candidates[0]

        if matching is None:
            decision.metadata = {
                **decision.metadata,
                "action_rewritten": "drop_thread_without_candidate",
            }
            decision.action = "wait"
            return decision

        target_domain = canonicalize_runtime_domain(matching.get("target_domain"))
        decision.chat_directive = {
            **decision.chat_directive,
            "intent": decision.chat_directive.get("intent") or "drop_thread",
            "thread_id": matching.get("thread_id"),
            "target_domain": target_domain,
        }
        latent_thread_updates = list(decision.state_updates.get("latent_threads") or [])
        latent_thread_updates.append(
            {
                "thread_id": matching.get("thread_id"),
                "status": "dropped",
                "target_domain": target_domain,
            }
        )
        decision.state_updates = {
            **decision.state_updates,
            "latent_threads": latent_thread_updates,
        }
        return decision

    def _apply_target_domain(
        self,
        decision: AuroraDecision,
        target_domain: str,
        readout: DashboardReadout,
    ) -> AuroraDecision:
        decision.chat_directive = {
            **decision.chat_directive,
            "target_domain": target_domain,
        }
        if decision.action in {"emit_message", "soft_return_topic", "update_state"} or (
            decision.action == "update_harness" and not decision.metadata.get("harness_update_rejected")
        ):
            decision.harness_updates = {
                **decision.harness_updates,
                "agenda_priority": target_domain,
            }
        decision.state_updates = {
            **decision.state_updates,
            "informational_tensions": self._normalize_informational_tensions(
                decision.state_updates.get("informational_tensions"),
                target_domain=target_domain,
                readout=readout,
            ),
        }
        return decision

    def _normalize_state_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(updates or {})
        tensions = normalized.get("informational_tensions")
        if isinstance(tensions, list):
            normalized["informational_tensions"] = [
                {
                    **dict(item),
                    "domain": canonicalize_runtime_domain(item.get("domain")) or str(item.get("domain") or ""),
                    "status": str(item.get("status") or "open"),
                }
                for item in tensions
                if isinstance(item, Mapping) and canonicalize_runtime_domain(item.get("domain"))
            ]
        correct_node = normalized.get("correct_answer_node")
        if isinstance(correct_node, Mapping):
            correct_node = correct_node.get("node_id") or correct_node.get("id")
        if isinstance(correct_node, str):
            correct_node = correct_node.strip()
            if correct_node:
                normalized["correct_answer_node"] = correct_node
            else:
                normalized.pop("correct_answer_node", None)
        return normalized

    def _normalize_informational_tensions(
        self,
        tensions: Any,
        *,
        target_domain: str | None,
        readout: DashboardReadout,
    ) -> list[dict[str, Any]]:
        covered = set(readout.covered_domains)
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        if isinstance(tensions, list):
            for item in tensions:
                if not isinstance(item, Mapping):
                    continue
                domain = canonicalize_runtime_domain(item.get("domain"))
                status = str(item.get("status") or "open")
                if not domain or domain in covered or status in {"resolved", "dropped"} or domain in seen:
                    continue
                seen.add(domain)
                normalized.append(
                    {
                        **dict(item),
                        "domain": domain,
                        "status": status,
                    }
                )
        if target_domain and target_domain not in covered and target_domain not in seen:
            normalized.insert(
                0,
                {
                    "domain": target_domain,
                    "status": "open",
                    "description": f"需要补齐 {target_domain} 相关线索",
                    "priority": 0.8,
                },
            )
        return normalized

    def _resolve_modeling_complete(self, readout: DashboardReadout) -> bool:
        if readout.surface != "aurora_modeling":
            return False
        covered = set(readout.covered_domains)
        missing = {domain for domain in readout.missing_domains if domain not in covered}
        return set(REQUIRED_MODELING_DOMAINS).issubset(covered) and not missing.intersection(REQUIRED_MODELING_DOMAINS)

    def _slim_readout_for_surface(self, readout: DashboardReadout) -> dict[str, Any]:
        wake_policy = self._wake_policy_from_readout(readout)
        context_budget = str(wake_policy.get("context_budget") or "").strip().lower() or None
        action_hint = self._infer_action_hint(readout)
        payload = readout.to_llm_payload(action=action_hint, context_budget=context_budget)
        surface_state = self._surface_state_from_readout(readout)
        if surface_state:
            payload["surface_state"] = surface_state
        deep_pattern_alerts = _deep_pattern_alerts(readout)
        if deep_pattern_alerts:
            cold_start_context = dict(payload.get("cold_start_context") or {})
            cold_start_context["deep_pattern_alerts"] = deep_pattern_alerts
            payload["cold_start_context"] = cold_start_context
        if context_budget == "compact":
            # G28: compact mode keeps only the highest-signal task/error context.
            compact_payload = {
                key: payload[key] for key in ("user_message", "task_state", "wake_policy") if key in payload
            }
            tensions = readout.informational_tensions
            if isinstance(tensions, list) and tensions:
                compact_payload["informational_tensions"] = tensions[:2]
            return compact_payload
        if context_budget == "extended":
            if readout.achievement_signals:
                payload["achievement_signals"] = readout.achievement_signals
            if readout.conversation_summary:
                payload["conversation_summary"] = readout.conversation_summary
        return payload

    def _infer_action_hint(self, readout: DashboardReadout) -> str | None:
        if readout.surface == "aurora_planning":
            return "update_harness"
        if readout.missing_domains:
            return "emit_message"
        if not readout.informational_tensions:
            return "wait"
        return None

    def _surface_state_from_readout(self, readout: DashboardReadout) -> dict[str, Any]:
        request_context = readout.request_extra_context if isinstance(readout.request_extra_context, Mapping) else {}
        surface_state: dict[str, Any] = {}

        direct_state = request_context.get("surface_state")
        if isinstance(direct_state, Mapping):
            surface_state.update(dict(direct_state))

        detour_scaffold = request_context.get("planning_detour_scaffold")
        if isinstance(detour_scaffold, Mapping):
            scaffold_state = detour_scaffold.get("surface_state")
            if isinstance(scaffold_state, Mapping):
                surface_state.update(dict(scaffold_state))
            if readout.surface == "aurora_planning" and (
                detour_scaffold.get("recent_detours") or detour_scaffold.get("top_latent_thread")
            ):
                surface_state.setdefault("in_detour", True)

        return surface_state

    def _extract_target_domain(self, decision: AuroraDecision) -> str | None:
        directive = decision.chat_directive or {}
        candidates = [
            directive.get("target_domain"),
            directive.get("question_domain"),
            directive.get("domain"),
            decision.harness_updates.get("agenda_priority"),
        ]
        tensions = decision.state_updates.get("informational_tensions")
        if isinstance(tensions, list):
            for item in tensions:
                if isinstance(item, Mapping):
                    candidates.append(item.get("domain"))
        for candidate in candidates:
            canonical = canonicalize_runtime_domain(candidate)
            if canonical:
                return canonical
        return None

    def _select_missing_domain(self, readout: DashboardReadout, *, exclude_recent: bool) -> str | None:
        recent = set(readout.recently_asked_domains) if exclude_recent else set()
        covered = set(readout.covered_domains)
        for domain in readout.missing_domains:
            if domain in covered or domain in recent:
                continue
            return domain
        return None

    def _select_latent_candidate(
        self,
        readout: DashboardReadout,
        *,
        exclude_recent: bool,
    ) -> dict[str, Any] | None:
        recent = set(readout.recently_asked_domains) if exclude_recent else set()
        covered = set(readout.covered_domains)
        for candidate in readout.latent_thread_recovery_candidates:
            domain = canonicalize_runtime_domain(candidate.get("target_domain"))
            if not domain or domain in covered or domain in recent:
                continue
            return dict(candidate)
        return None

    def _merge_strategy_harness_updates(
        self,
        harness_updates: Mapping[str, Any] | None,
        readout: DashboardReadout,
    ) -> dict[str, Any]:
        merged = dict(harness_updates or {})
        current_strategy = self._normalize_strategy_payload(
            readout.activity_profile.get("strategy"),
            include_defaults=False,
        )
        requested_strategy = self._normalize_strategy_payload(merged.get("strategy"), include_defaults=False)
        strategy = {
            **self._strategy_defaults_for_readout(readout),
            **current_strategy,
            **requested_strategy,
        }
        if requested_strategy.get("concept_first") and "problem_first" not in requested_strategy:
            strategy["problem_first"] = False
        if requested_strategy.get("problem_first") and "concept_first" not in requested_strategy:
            strategy["concept_first"] = False
        merged["strategy"] = strategy
        if _achievement_reentry_gap_scene(readout):
            current_density = _safe_float(merged.get("task_density_hint"))
            baseline_density = _safe_float(readout.activity_profile.get("task_density_hint"))
            if baseline_density is None:
                baseline_density = 0.7
            reduced_density = round(max(0.0, min(1.0, baseline_density) - 0.1), 4)
            if current_density is None or current_density > reduced_density:
                merged["task_density_hint"] = reduced_density
        return merged

    def _strategy_defaults_for_readout(self, readout: DashboardReadout) -> dict[str, bool]:
        defaults = AuroraTeachingStrategy().model_dump(mode="python")
        if readout.surface == "aurora_modeling":
            defaults["concept_first"] = True
        elif readout.surface == "aurora_planning":
            defaults["problem_first"] = True
        elif readout.surface == "aurora_checkpoint":
            defaults["error_analysis_required"] = True

        # F20: When checkpoint has sprint_pack_mistakes, force error analysis.
        if readout.checkpoint_state.get("sprint_pack_mistakes"):
            defaults["error_analysis_required"] = True

        retrieval_policy = readout.exam_sprint_policy.get("retrieval_policy")
        if isinstance(retrieval_policy, Mapping):
            if retrieval_policy.get("daily_retrieval_required"):
                defaults["retrieval_practice"] = True
            if retrieval_policy.get("spaced_retrieval"):
                defaults["spaced_review"] = True
            if retrieval_policy.get("new_topic_allowed") is False:
                defaults["new_topic_allowed"] = False

        if readout.exam_sprint_policy.get("drop_low_roi_topics") is True:
            defaults["drop_low_roi_topics"] = True
        if readout.exam_sprint_policy.get("error_analysis_required") is True:
            defaults["error_analysis_required"] = True

        if _has_deep_pattern_alerts(readout):
            defaults["concept_first"] = True
            defaults["problem_first"] = False
            defaults["error_analysis_required"] = True

        if self._is_high_exam_urgency(readout):
            defaults["worked_example_first"] = True
        if _achievement_high_streak_scene(readout):
            defaults["retrieval_practice"] = True
        # Detect last-24h mode via either the explicit boolean flag or sprint_mode value.
        # exam_sprint_policy is built from ExamSprintPolicy.to_dict() which uses sprint_mode,
        # not a separate last_24h_mode key — so both checks are needed.
        _is_last_24h = bool(
            readout.exam_sprint_policy.get("last_24h_mode") is True
            or readout.exam_sprint_policy.get("sprint_mode") == "last_24h_cram"
            or getattr(readout, "last_24h_mode", False)
        )
        if _is_last_24h:
            defaults.update(
                {
                    "worked_example_first": True,
                    "retrieval_practice": True,
                    "spaced_review": True,
                    "error_analysis_required": True,
                    "drop_low_roi_topics": True,
                    "new_topic_allowed": False,
                }
            )

        # G13: Apply confirmed strategy preference from persistent learning style.
        cold_start_context = readout.cold_start_context if isinstance(readout.cold_start_context, Mapping) else {}
        confirmed_preference = cold_start_context.get("confirmed_strategy_preference")
        if isinstance(confirmed_preference, str) and confirmed_preference.strip():
            flag_name = confirmed_preference.strip()
            if flag_name in STRATEGY_FIELDS:
                defaults[flag_name] = True
                # Clear conflicting opposite flags
                if flag_name == "concept_first":
                    defaults.pop("problem_first", None)
                elif flag_name == "problem_first":
                    defaults.pop("concept_first", None)

        return defaults

    def _normalize_strategy_payload(self, value: Any, *, include_defaults: bool) -> dict[str, bool]:
        if not isinstance(value, Mapping):
            return {}
        strategy = AuroraTeachingStrategy.model_validate(dict(value))
        payload = strategy.model_dump(mode="python", exclude_unset=not include_defaults)
        if (
            not include_defaults
            and set(payload.keys()) == set(STRATEGY_FIELDS)
            and not any(bool(flag) for key, flag in payload.items() if key != "new_topic_allowed")
            and payload.get("new_topic_allowed") is True
        ):
            return {}
        return payload

    def _is_high_exam_urgency(self, readout: DashboardReadout) -> bool:
        summary = readout.sprint_policy_summary if isinstance(readout.sprint_policy_summary, Mapping) else {}
        policy = readout.exam_sprint_policy if isinstance(readout.exam_sprint_policy, Mapping) else {}

        triage = str(policy.get("triage_level") or summary.get("triage_level") or "").strip().lower()
        if triage in HIGH_URGENCY_TRIAGE_LEVELS:
            return True

        mode = str(policy.get("sprint_mode") or policy.get("mode") or summary.get("mode") or "").strip().lower()
        if mode in HIGH_URGENCY_SPRINT_MODES:
            return True

        for candidate in (
            summary.get("urgent"),
            policy.get("urgent"),
            (
                (policy.get("exam_urgency") or {}).get("urgent")
                if isinstance(policy.get("exam_urgency"), Mapping)
                else None
            ),
        ):
            if candidate is True:
                return True

        for raw_days in (
            summary.get("days_remaining"),
            summary.get("days_left"),
            policy.get("days_remaining"),
            policy.get("days_left"),
            policy.get("time_constraint_days"),
            (
                (policy.get("exam_urgency") or {}).get("days_left")
                if isinstance(policy.get("exam_urgency"), Mapping)
                else None
            ),
        ):
            days = self._coerce_positive_int(raw_days)
            if days is not None and days <= 7:
                return True
        return False

    def _coerce_positive_int(self, value: Any) -> int | None:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo is None else value.astimezone(UTC).replace(tzinfo=None)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    def _wake_policy_from_readout(self, readout: DashboardReadout) -> dict[str, Any]:
        return dict(readout.wake_policy or {})

    def _max_tokens_for_readout(self, readout: DashboardReadout) -> int:
        wake_policy = self._wake_policy_from_readout(readout)
        return 600 if wake_policy.get("context_budget") == "extended" else 320

    async def _resolve_llm(self) -> Any:
        service_or_awaitable = self.llm_factory()
        if inspect.isawaitable(service_or_awaitable):
            return await service_or_awaitable
        return service_or_awaitable

    async def _default_llm_factory(self) -> Any:
        return await get_configured_llm_service(AgentRole.ORCHESTRATOR, TaskType.QUICK_QUERY)

    def _fallback_decision(self, readout: DashboardReadout, *, reason: str) -> AuroraDecision:
        safe_action = "emit_message" if reason in {"llm_failure", "non_mapping_decision"} else "wait"
        target_domain = self._select_missing_domain(readout, exclude_recent=True) or self._select_missing_domain(
            readout,
            exclude_recent=False,
        )
        modeling_complete = self._resolve_modeling_complete(readout)
        chat_directive = {
            "intent": "confirm_modeling_ready" if modeling_complete else "safe_ack",
            "brief": "Acknowledge briefly and only pursue one safe task-level missing domain if useful.",
            "surface": readout.surface,
        }
        if target_domain and not modeling_complete:
            chat_directive["target_domain"] = target_domain
        fallback = AuroraDecision(
            action=safe_action,
            surface_complete=bool(readout.request_extra_context.get("surface_complete"))
            or bool(readout.surface == "aurora_modeling" and modeling_complete),
            modeling_complete=modeling_complete,
            harness_updates=self._merge_strategy_harness_updates({}, readout),
            chat_directive=chat_directive,
            metadata={
                "reasoning_summary": "Fallback decision preserved safety and continuity.",
                "fallback_reason": reason,
            },
        )
        fallback.chat_directive = {
            **fallback.chat_directive,
            "standard_layer_contract": build_standard_layer_contract(fallback, readout),
        }
        return fallback
