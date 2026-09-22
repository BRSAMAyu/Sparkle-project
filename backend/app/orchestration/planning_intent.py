from __future__ import annotations

import re
from typing import Any

_MESSAGE_PLAN_PATTERN = re.compile(
    r"\b(plan|study plan|schedule|sprint plan)\b|计划|规划|冲刺计划|复习计划|时间安排",
    re.IGNORECASE,
)

# BP-3B：用户明示纠正/指错信号（你说错了/不对/纠正/其实是…）。
# 该信号在判定序上优先于规划词汇（复习/总结等）——用户在指出错误时，
# 消息里的规划词面不应把纠正请求劫持进规划澄清快速通道。
# 「不对」用负向断言排除「对不对」（求确认而非指错）。
_CORRECTION_SIGNAL_PATTERN = re.compile(
    r"你说错了|你说错|说错了|你错了|你搞错了|搞错了|(?<!对)不对|纠正|更正|其实是",
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


def has_correction_signal(user_message: str | None) -> bool:
    """用户明示纠正/指错信号检测（BP-3B 判定序原语）。

    「你说错了/不对/纠正/其实是」等信号表示用户在指出一个错误并要求修正，
    优先级高于消息中的规划词汇（复习/总结/计划等词面）。
    """
    message = _strip(user_message)
    return bool(message and _CORRECTION_SIGNAL_PATTERN.search(message))


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

    # BP-3B 判定序：纠正信号优先于消息词面的规划回退——用户在指错/求纠正时，
    # 复习/计划等规划词面不得把该回合误判为规划回合（结构性信号不受影响）。
    message = _strip(user_message)
    if message and not has_correction_signal(message) and _MESSAGE_PLAN_PATTERN.search(message):
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
