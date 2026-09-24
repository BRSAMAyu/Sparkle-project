from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp(value: Any, *, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, parsed))


def _positive_float(value: Any, *, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, parsed)


def _event_timestamp(event: dict[str, Any]) -> datetime:
    raw = event.get("timestamp") or event.get("triggered_at")
    if raw:
        try:
            parsed = datetime.fromisoformat(str(raw))
            if parsed.tzinfo is not None:
                return parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return _utcnow()


def _scope(event: dict[str, Any]) -> dict[str, Any]:
    raw_metadata = event.get("source_metadata")
    metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
    return {
        "event_type": event.get("event_type"),
        "task_id": event.get("task_id"),
        "plan_id": event.get("plan_id"),
        "route_history_decision_id": event.get("route_history_decision_id") or metadata.get("route_history_decision_id"),
        "routing_outcome_signal_id": event.get("routing_outcome_signal_id") or metadata.get("routing_outcome_signal_id"),
        "routing_trace_id": event.get("routing_trace_id") or metadata.get("routing_trace_id"),
    }


def _evidence(
    event: dict[str, Any],
    *,
    target: EvidenceTarget,
    direction: EvidenceDirection,
    strength: float,
    confidence: float,
    text: str,
    metadata: dict[str, Any] | None = None,
    ttl_seconds: int = 7 * 24 * 3600,
) -> UnifiedEvidence:
    return UnifiedEvidence(
        source_type=EvidenceSourceType.OUTCOME,
        target_latent_variable=target,
        direction=direction,
        strength=_clamp(strength),
        confidence=_clamp(confidence),
        evidence_text=text,
        timestamp=_event_timestamp(event),
        ttl_seconds=ttl_seconds,
        scope=_scope(event),
        metadata={"adapter": "outcome_evidence_adapter.v1", **(metadata or {})},
    )


def build_task_outcome_evidence(event: dict[str, Any], *, completed: bool) -> list[UnifiedEvidence]:
    """Convert task completion/abandonment events into shadow-safe belief evidence."""
    completion_rate = _clamp(event.get("completion_rate"), default=1.0 if completed else 0.0)
    estimated = _positive_float(event.get("estimated_minutes"))
    actual = _positive_float(event.get("actual_minutes") or event.get("time_spent"))
    difficulty = _clamp((float(event.get("difficulty") or 3.0) - 1.0) / 4.0, default=0.5)
    duration_ratio = actual / estimated if estimated > 0 and actual > 0 else None
    task_id = str(event.get("task_id") or "unknown_task")

    evidence: list[UnifiedEvidence] = [
        _evidence(
            event,
            target=EvidenceTarget.TASK_COMPLETION_STATE,
            direction=EvidenceDirection.OBSERVE,
            strength=completion_rate if completed else 0.0,
            confidence=0.92,
            text=f"Task outcome observed for {task_id}: {'completed' if completed else 'abandoned'}",
            metadata={"completed": completed, "completion_rate": completion_rate},
        )
    ]

    if completed:
        execution_strength = min(1.0, 0.45 + 0.45 * completion_rate + 0.10 * difficulty)
        evidence.append(
            _evidence(
                event,
                target=EvidenceTarget.EXECUTION_CAPACITY,
                direction=EvidenceDirection.INCREASE,
                strength=execution_strength,
                confidence=0.74,
                text=f"Task {task_id} was completed; execution capacity evidence.",
                metadata={"completion_rate": completion_rate, "difficulty_normalized": difficulty},
            )
        )
        evidence.append(
            _evidence(
                event,
                target=EvidenceTarget.TASK_AVERSION,
                direction=EvidenceDirection.DECREASE,
                strength=max(0.55, completion_rate),
                confidence=0.62,
                text=f"Task {task_id} completion lowers immediate task aversion hypothesis.",
                metadata={"completion_rate": completion_rate},
            )
        )
        if duration_ratio is not None and duration_ratio >= 1.5:
            evidence.append(
                _evidence(
                    event,
                    target=EvidenceTarget.COGNITIVE_LOAD,
                    direction=EvidenceDirection.INCREASE,
                    strength=min(1.0, 0.45 + (duration_ratio - 1.0) * 0.25),
                    confidence=0.56,
                    text=f"Task {task_id} took longer than expected; possible load evidence.",
                    metadata={"duration_ratio": round(duration_ratio, 3)},
                )
            )
    else:
        reason = str(event.get("reason") or event.get("feedback") or "").lower()
        aversion_strength = 0.78
        load_strength = 0.62
        emotional_strength = 0.0
        if any(marker in reason for marker in ("too_difficult", "难", "hard", "overwhel", "卡", "stuck")):
            aversion_strength = 0.86
            load_strength = 0.78
        if any(marker in reason for marker in ("累", "焦虑", "崩溃", "烦", "anxious", "tired", "frustrat")):
            emotional_strength = 0.76

        evidence.extend(
            [
                _evidence(
                    event,
                    target=EvidenceTarget.TASK_AVERSION,
                    direction=EvidenceDirection.INCREASE,
                    strength=aversion_strength,
                    confidence=0.76,
                    text=f"Task {task_id} was abandoned; task aversion evidence.",
                    metadata={"reason": reason},
                ),
                _evidence(
                    event,
                    target=EvidenceTarget.EXECUTION_CAPACITY,
                    direction=EvidenceDirection.DECREASE,
                    strength=0.72,
                    confidence=0.66,
                    text=f"Task {task_id} was abandoned; reduced execution capacity evidence.",
                    metadata={"reason": reason},
                ),
                _evidence(
                    event,
                    target=EvidenceTarget.COGNITIVE_LOAD,
                    direction=EvidenceDirection.INCREASE,
                    strength=load_strength,
                    confidence=0.62,
                    text=f"Task {task_id} was abandoned; possible cognitive load evidence.",
                    metadata={"reason": reason},
                ),
            ]
        )
        if emotional_strength > 0.0:
            evidence.append(
                _evidence(
                    event,
                    target=EvidenceTarget.EMOTIONAL_BLOCK,
                    direction=EvidenceDirection.INCREASE,
                    strength=emotional_strength,
                    confidence=0.64,
                    text=f"Task {task_id} abandonment reason suggests emotional block.",
                    metadata={"reason": reason},
                )
            )
    return evidence


def build_task_feedback_evidence(event: dict[str, Any]) -> list[UnifiedEvidence]:
    """Convert explicit task feedback into evidence without treating it as an outcome label."""
    category = str(event.get("category") or event.get("feedback_category") or "").strip().lower()
    text = str(event.get("feedback_text") or event.get("feedback") or category or "task feedback").strip()
    if not category and not text:
        return []

    evidence: list[UnifiedEvidence] = []
    if category in {"too_difficult", "hard", "confusing"} or any(
        marker in text.lower() for marker in ("太难", "不懂", "卡住", "confusing", "too hard")
    ):
        evidence.extend(
            [
                _evidence(
                    event,
                    target=EvidenceTarget.COGNITIVE_LOAD,
                    direction=EvidenceDirection.INCREASE,
                    strength=0.78,
                    confidence=0.82,
                    text=text,
                    metadata={"feedback_category": category},
                ),
                _evidence(
                    event,
                    target=EvidenceTarget.TASK_AVERSION,
                    direction=EvidenceDirection.INCREASE,
                    strength=0.68,
                    confidence=0.72,
                    text=text,
                    metadata={"feedback_category": category},
                ),
            ]
        )
    if category in {"too_long", "boring"} or any(marker in text.lower() for marker in ("太长", "无聊", "boring")):
        evidence.append(
            _evidence(
                event,
                target=EvidenceTarget.TASK_AVERSION,
                direction=EvidenceDirection.INCREASE,
                strength=0.64,
                confidence=0.70,
                text=text,
                metadata={"feedback_category": category},
            )
        )
    if category in {"too_easy", "easy"} or any(marker in text.lower() for marker in ("太简单", "轻松", "too easy")):
        evidence.append(
            _evidence(
                event,
                target=EvidenceTarget.EXECUTION_CAPACITY,
                direction=EvidenceDirection.INCREASE,
                strength=0.76,
                confidence=0.70,
                text=text,
                metadata={"feedback_category": category},
            )
        )
    return evidence


# S-04 采纳强度按反馈词表封闭取值：peer 反馈是被采纳的**用户侧社会证据**，
# 永不自动产生（必须资源主人显式采纳），因此置信档低于服务器行为观察
# （outcome 0.92 / feedback 0.82），与「声明不构成证明」的账本哲学同口径。
_PEER_FEEDBACK_STRENGTH: dict[str, float] = {
    "helpful": 0.62,
    "insightful": 0.70,
    "applied": 0.78,
}


def build_peer_feedback_evidence(event: dict[str, Any]) -> list[UnifiedEvidence]:
    """Convert an *user-adopted* peer feedback into shadow-safe belief evidence.

    S-04：同伴反馈只有被资源主人显式采纳后才经本适配器进入信念链；
    反馈/ack 本身**永不**自动成为 mastery 或证据（GALAXY mastery 不动，
    仅 UnifiedEvidence 信念面 + Goal 轨迹回执）。
    事件字段：feedback_id / shared_resource_id / verdict / goal_id /
    sharer_id(=资源主人) / feedback_giver_id / comment。
    """
    verdict = str(event.get("verdict") or "").strip().lower()
    if verdict not in _PEER_FEEDBACK_STRENGTH:
        return []
    strength = _PEER_FEEDBACK_STRENGTH[verdict]
    feedback_id = str(event.get("feedback_id") or "unknown_feedback")
    giver_alias = str(event.get("feedback_giver_alias") or "").strip()
    text = str(event.get("comment") or "").strip() or (
        f"Peer feedback ({verdict}) adopted for shared artifact {event.get('shared_resource_id')}"
    )

    metadata = {
        "adopted_from": "community_feedback",
        "feedback_id": feedback_id,
        "shared_resource_id": str(event.get("shared_resource_id") or "") or None,
        "goal_id": str(event.get("goal_id") or "") or None,
        "verdict": verdict,
        "peer_alias": giver_alias or None,
        # 诚实标注：这是用户采纳的社会证据（self_reported 档），不是服务器
        # 行为观察——下游消费方按 outcome_ledger 的 TruthClass 哲学对待。
        "truth_class": "self_reported",
    }
    return [
        _evidence(
            event,
            target=EvidenceTarget.EXECUTION_CAPACITY,
            direction=EvidenceDirection.INCREASE,
            strength=strength,
            confidence=0.58,
            text=text,
            metadata=metadata,
            ttl_seconds=14 * 24 * 3600,
        )
    ]
