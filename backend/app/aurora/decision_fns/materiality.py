"""Materiality checks for Aurora snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from app.aurora.schemas import AuroraPolicyVersion, DecisionBasis, SignalSnapshot

_STRONG_SIGNAL_KEYWORDS = (
    "commitment_conflict",
    "conflict",
    "deadline",
    "can’t continue",
    "can't continue",
    "not possible",
    "family issue",
    "energy_drop",
    "sharp_drop",
    "gaming_detected",
    "我家里出事了",
    "没法继续",
)


@dataclass(frozen=True)
class MaterialityCheck:
    """Result of deterministic materiality evaluation."""

    should_route: bool
    score: float
    threshold: float
    basis: DecisionBasis
    matched_signals: tuple[str, ...] = field(default_factory=tuple)


def _flatten_signals(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for key, inner in value.items():
            flattened.extend(_flatten_signals(key))
            flattened.extend(_flatten_signals(inner))
        return flattened
    if isinstance(value, (list, tuple, set)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_signals(item))
        return flattened
    return [str(value)]


def _score_from_text(text: str) -> tuple[float, str | None]:
    normalized = text.strip().lower()
    for keyword in _STRONG_SIGNAL_KEYWORDS:
        if keyword.lower() in normalized:
            return 1.0, keyword
    if any(token in normalized for token in ("我今天不想做", "不想", "疲劳", "need help", "help", "pause", "delay")):
        return 0.35, "soft_resistance"
    if normalized:
        return 0.15, None
    return 0.0, None


def _contains_partner_concern(value: Any) -> bool:
    if isinstance(value, dict):
        if "partner_report" in value:
            partner_value = value["partner_report"]
            partner_text = " ".join(_flatten_signals(partner_value)).lower()
            if any(token in partner_text for token in ("medium", "high", "concern", "issue", "urgent", "gaming_detected")):
                return True
        return any(_contains_partner_concern(inner) for inner in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_partner_concern(item) for item in value)
    return False


def check_materiality(snapshot: SignalSnapshot, policy: AuroraPolicyVersion) -> MaterialityCheck:
    """Return a deterministic materiality verdict for a snapshot."""

    texts = list(_flatten_signals(snapshot.core_signals))
    texts.extend(_flatten_signals(snapshot.enhanced_signals))
    texts.extend(_flatten_signals(snapshot.optional_signals))

    score = 0.0
    matched: list[str] = []

    if _contains_partner_concern(snapshot.core_signals) or _contains_partner_concern(snapshot.enhanced_signals):
        score = 1.0
        matched.append("partner_report")

    for text in texts:
        delta, keyword = _score_from_text(text)
        score = max(score, delta)
        if keyword:
            matched.append(keyword)

    threshold = float(policy.materiality_threshold)
    if score >= threshold and not matched:
        matched.append("threshold_crossed")

    basis = DecisionBasis.MIXED
    if matched:
        if any(keyword in matched_item for matched_item in matched for keyword in ("commitment_conflict", "conflict", "deadline")):
            basis = DecisionBasis.COMMITMENT_CONFLICT
        elif any(keyword in matched_item for matched_item in matched for keyword in ("family issue", "energy_drop", "sharp_drop", "我家里出事了", "没法继续")):
            basis = DecisionBasis.ENERGY_DROP
        elif any(keyword in matched_item for matched_item in matched for keyword in ("partner_report", "gaming_detected")):
            basis = DecisionBasis.PARTNER_SIGNAL
        elif any(keyword in matched_item for matched_item in matched for keyword in ("soft_resistance",)):
            basis = DecisionBasis.BEHAVIORAL_SIGNAL

    return MaterialityCheck(
        should_route=score >= threshold,
        score=score,
        threshold=threshold,
        basis=basis,
        matched_signals=tuple(dict.fromkeys(matched)),
    )
