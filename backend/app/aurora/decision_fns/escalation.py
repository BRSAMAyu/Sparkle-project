"""WS-B.2 mid-flight escalation detection (Agent H).

Three approved triggers only:
  1. explicit planning request
  2. 2+ structural-topic turns
  3. frustration / blockage signal

This module is intentionally disjoint from the WS-B.1 routing seam
(_classify_routing_mode in backbone.py) and must not be merged into it.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import SignalSnapshot


@dataclass(frozen=True)
class EscalationVerdict:
    """Whether mid-flight escalation should fire and why."""

    should_escalate: bool
    trigger: str | None
    confidence: float
    reason: str


# ---------------------------------------------------------------------------
# Trigger 1 — explicit planning request
# Markers chosen to be disjoint from _PLANNING_MARKERS in backbone.py so
# that WS-B.1 does NOT classify these as WORKFLOW, leaving room for WS-B.2
# escalation to promote direct → workflow.
# ---------------------------------------------------------------------------
_EXPLICIT_PLANNING_ESCALATION_MARKERS: tuple[str, ...] = (
    "别直答",
    "别直接给答案",
    "能执行的方案",
    "跟着做的方案",
    "一步步跟着做",
    "做成方案",
    "别只是回答",
    "别光讲道理",
)

# ---------------------------------------------------------------------------
# Trigger 3 — frustration / blockage signal (text fallback)
# ---------------------------------------------------------------------------
_FRUSTRATION_BLOCKAGE_TEXT_MARKERS: tuple[str, ...] = (
    "做不下去了",
    "帮不到我",
    "完全帮不到",
    "完全没用",
    "一点用都没有",
    "一点帮助都没有",
)


def detect_escalation(snapshot: SignalSnapshot) -> EscalationVerdict:
    """Detect mid-flight escalation from the three approved triggers.

    Priority order: explicit planning > structural turns > frustration.
    Returns on the first matching trigger.
    """
    message = str(snapshot.core_signals.get("user_message") or "").strip().lower()
    enhanced = snapshot.enhanced_signals or {}
    optional = snapshot.optional_signals or {}

    # --- Trigger 1: explicit planning request ---
    for marker in _EXPLICIT_PLANNING_ESCALATION_MARKERS:
        if marker in message:
            return EscalationVerdict(
                should_escalate=True,
                trigger="explicit_planning_request",
                confidence=1.0,
                reason=f"escalation:explicit_planning_request:{marker}",
            )

    # --- Trigger 2: 2+ structural-topic turns ---
    structural_turns = optional.get("structural_topic_turns")
    if isinstance(structural_turns, (int, float)) and int(structural_turns) >= 2:
        return EscalationVerdict(
            should_escalate=True,
            trigger="structural_topic_turns",
            confidence=0.9,
            reason=f"escalation:structural_topic_turns:{int(structural_turns)}",
        )

    # --- Trigger 3: frustration / blockage signal ---
    # 3a: enhanced_signal takes precedence (set by upstream cognitive analysis)
    if enhanced.get("frustration_signal") is True:
        return EscalationVerdict(
            should_escalate=True,
            trigger="frustration_blockage",
            confidence=0.85,
            reason="escalation:frustration_blockage:enhanced_signal",
        )

    # 3b: text-based fallback
    for marker in _FRUSTRATION_BLOCKAGE_TEXT_MARKERS:
        if marker in message:
            return EscalationVerdict(
                should_escalate=True,
                trigger="frustration_blockage",
                confidence=0.8,
                reason=f"escalation:frustration_blockage:text:{marker}",
            )

    return EscalationVerdict(
        should_escalate=False,
        trigger=None,
        confidence=0.0,
        reason="no_escalation_trigger",
    )
