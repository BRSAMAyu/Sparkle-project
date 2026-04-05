from __future__ import annotations

import re
from typing import Any


_MESSAGE_PLAN_PATTERN = re.compile(
    r"\b(plan|study plan|schedule|sprint plan)\b|计划|规划|冲刺计划|复习计划|时间安排",
    re.IGNORECASE,
)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _has_phase_a_markers(decision_context: dict[str, Any] | None) -> bool:
    if not isinstance(decision_context, dict):
        return False
    if _strip(decision_context.get("planning_readiness_action")):
        return True
    if _strip(decision_context.get("phase_a_guardrail")):
        return True
    questions = decision_context.get("strategic_clarification_questions")
    return isinstance(questions, list) and any(_strip(item) for item in questions)


def detect_planning_like_turn(
    *,
    normalized_intent: str | None,
    route_intent: str | None,
    user_message: str | None,
    decision_context: dict[str, Any] | None,
) -> tuple[bool, str]:
    normalized = _strip(normalized_intent).lower()
    if normalized in {"create_plan", "time_planning"}:
        return True, "normalized_intent"

    route = _strip(route_intent).lower()
    if route in {"plan", "create_plan", "time_planning"} or "plan" in route:
        return True, "route_intent"

    if _has_phase_a_markers(decision_context):
        return True, "decision_context"

    message = _strip(user_message)
    if message and _MESSAGE_PLAN_PATTERN.search(message):
        return True, "message_fallback"

    return False, "none"


def is_planning_like_intent(label: str | None) -> bool:
    return detect_planning_like_turn(
        normalized_intent=label,
        route_intent=label,
        user_message=None,
        decision_context=None,
    )[0]


def is_planning_like_turn(
    normalized_intent: str | None,
    route_intent: str | None,
    user_message: str | None,
    decision_context: dict[str, Any] | None,
) -> bool:
    return detect_planning_like_turn(
        normalized_intent=normalized_intent,
        route_intent=route_intent,
        user_message=user_message,
        decision_context=decision_context,
    )[0]
