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
    "task_help",
}
DIAGNOSTIC_INTENTS = {
    "diagnostic",
    "diagnose_breakpoint",
    "error_analysis",
    "checkpoint_repair",
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
}

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


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


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
    if readout.surface == "aurora_checkpoint":
        return True
    strategy = _effective_strategy_flags(decision, readout)
    if strategy.get("error_analysis_required"):
        return True
    return _intent_token(decision) in DIAGNOSTIC_INTENTS


def _is_task_help_scene(decision: AuroraDecision, readout: DashboardReadout) -> bool:
    task_state = readout.task_state if isinstance(readout.task_state, Mapping) else {}
    if _intent_token(decision) in TASK_HELP_INTENTS:
        return True
    if any(task_state.get(key) for key in ("task_card_id", "current_task_id", "current_task")):
        return True
    if _task_stage_tokens(readout).intersection(TASK_HELP_STAGE_TOKENS):
        return True
    return False


def _infer_standard_layer_response_type(
    decision: AuroraDecision,
    readout: DashboardReadout,
    contract: Mapping[str, Any] | None = None,
) -> str:
    requested = _normalize_standard_layer_response_type((contract or {}).get("response_type"))
    if _is_emotional_support_scene(decision, readout):
        return "emotional_support"
    if _is_calibration_scene(decision, readout):
        return "calibration"
    if _is_diagnostic_scene(decision, readout):
        return "diagnostic"
    if _is_task_help_scene(decision, readout):
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
        return {
            "response_type": response_type,
            "must_include": ["emotional_acknowledgment", "one_concrete_next_step"],
            "must_not_include": ["full_week_replan", "long_motivational_speech", "blame_or_shame"],
            "max_response_length": "normal",
        }
    if response_type == "diagnostic":
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
    must_include = [
        token
        for token in _normalize_standard_layer_token_list(defaults.get("must_include"))
        + _normalize_standard_layer_token_list(contract.get("must_include"))
        if token not in must_not_include
    ]
    deduped_include: list[str] = []
    seen_include: set[str] = set()
    for token in must_include:
        if token not in seen_include:
            seen_include.add(token)
            deduped_include.append(token)
    max_response_length = _normalize_standard_layer_length(contract.get("max_response_length")) or str(
        defaults.get("max_response_length") or "normal"
    )
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
            "When setting informational_tensions, include importance_reasoning explaining why this gap blocks downstream "
            "planning (e.g. 'baseline 缺失会导致任务难度无法个性化'). "
            "Use self_model as Aurora's self-check: when strategy_confidence is low, task_failure_streak is high, or "
            "needs_recalibration is true, prefer shorter and safer next steps, lower task density, and avoid assuming "
            "the user can sustain the previous workload estimate. "
            "motivation domain is optional — ask about it if covered_domains has goal/scope/baseline/time but not motivation. "
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
            "must_include and must_not_include are hard content constraints for the standard chat layer, not style suggestions. "
            "Use concise canonical tokens such as worked_example, three_practice_questions, completion_check, "
            "emotional_acknowledgment, one_concrete_next_step, full_week_replan, and long_motivational_speech."
        )
        wake_instruction = str(wake_policy.get("diagnostic_prompt") or "").strip()
        if wake_instruction:
            system = f"{system} {wake_instruction}"
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
        # Last-24h mode overrides: detected from readout.last_24h_mode or exam_sprint_policy sprint_mode.
        _in_last_24h = bool(
            getattr(readout, "last_24h_mode", False)
            or (isinstance(readout.exam_sprint_policy, Mapping) and readout.exam_sprint_policy.get("sprint_mode") == "last_24h_cram")
            or (isinstance(readout.exam_sprint_policy, Mapping) and readout.exam_sprint_policy.get("last_24h_mode") is True)
        )
        if _in_last_24h:
            user["rules"].append(
                "LAST-24H EXAM MODE is active. "
                "Do NOT probe for new information, open new modeling domains, or increase task density. "
                "The exam is tomorrow — the user needs confidence, stability, and final-pass reinforcement, not new calibration. "
                "Focus exclusively on high-yield review, error-book recall, and short mock items that are already scoped. "
                "response_type must be task_help or emotional_support — never calibration or diagnostic unless the user explicitly asks. "
                "Keep responses short and reassuring. new_topic_allowed is false."
            )
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
        ):
            target_domain = preferred_missing or self._select_missing_domain(readout, exclude_recent=False)

        if target_domain:
            normalized = self._apply_target_domain(normalized, target_domain, readout)
        elif missing_domains and normalized.action in {"emit_message", "soft_return_topic"}:
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
        payload = readout.to_llm_payload()
        surface_state = self._surface_state_from_readout(readout)
        if surface_state:
            payload["surface_state"] = surface_state
        wake_policy = self._wake_policy_from_readout(readout)
        if wake_policy.get("context_budget") == "extended":
            if readout.achievement_signals:
                payload["achievement_signals"] = readout.achievement_signals
            if readout.conversation_summary:
                payload["conversation_summary"] = readout.conversation_summary
        return payload

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
        return merged

    def _strategy_defaults_for_readout(self, readout: DashboardReadout) -> dict[str, bool]:
        defaults = AuroraTeachingStrategy().model_dump(mode="python")
        if readout.surface == "aurora_modeling":
            defaults["concept_first"] = True
        elif readout.surface == "aurora_planning":
            defaults["problem_first"] = True
        elif readout.surface == "aurora_checkpoint":
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

        if self._is_high_exam_urgency(readout):
            defaults["worked_example_first"] = True
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
