from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from pydantic import Field

from app.aurora.common import AuroraSchemaBase

GROWTH_SIGNAL_CONTRACT_VERSION = "ws-g1.2026-04-19.v1"
GROWTH_SIGNAL_SOURCE = "achievement_sampler"
MAX_RECENT_ACHIEVEMENTS = 5
MAX_EVIDENCE_ITEMS = 4
MAX_LABEL_LENGTH = 72
MAX_EVIDENCE_TEXT_LENGTH = 128


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "__dict__"):
        return {str(key): item for key, item in vars(value).items() if not str(key).startswith("_")}
    return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _compact_text(value: Any, *, limit: int) -> str:
    text = _strip(value)
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _extract_recent_achievement_fields(item: Any) -> tuple[str, str]:
    payload = _as_dict(item)
    achievement_id = _compact_text(
        payload.get("achievement_id") or payload.get("id") or payload.get("slug") or payload.get("code"),
        limit=MAX_LABEL_LENGTH,
    )
    achievement_label = _compact_text(
        payload.get("achievement_name") or payload.get("name") or payload.get("title") or achievement_id,
        limit=MAX_LABEL_LENGTH,
    )
    return achievement_id, achievement_label


def _classify_growth_phase(*, streak_days: int, achievement_count: int, cold_start: bool) -> str:
    if cold_start:
        return "cold_start"
    if streak_days >= 14 or achievement_count >= 10:
        return "surging"
    if streak_days >= 7 or achievement_count >= 3:
        return "building"
    if streak_days > 0 or achievement_count > 0:
        return "steady"
    return "cold_start"


def _score_momentum(*, streak_days: int, achievement_count: int, cold_start: bool) -> float:
    if cold_start:
        return 0.0
    streak_component = min(1.0, max(0.0, streak_days / 14.0))
    achievement_component = min(1.0, max(0.0, achievement_count / 10.0))
    return round(min(1.0, streak_component * 0.6 + achievement_component * 0.4), 4)


class GrowthSignalEvidence(AuroraSchemaBase):
    kind: str
    text: str
    weight: float = 1.0


class GrowthSignalContract(AuroraSchemaBase):
    contract_version: str = GROWTH_SIGNAL_CONTRACT_VERSION
    source: str = GROWTH_SIGNAL_SOURCE
    user_id: UUID
    sampled_at: datetime
    cold_start: bool = False
    fallback_reason: str | None = None
    streak_days: int = 0
    achievement_count: int = 0
    recent_achievement_ids: list[str] = Field(default_factory=list)
    recent_achievement_labels: list[str] = Field(default_factory=list)
    growth_phase: str = "cold_start"
    momentum_score: float = 0.0
    evidence: list[GrowthSignalEvidence] = Field(default_factory=list)
    limits: dict[str, int] = Field(
        default_factory=lambda: {
            "max_recent_achievements": MAX_RECENT_ACHIEVEMENTS,
            "max_evidence_items": MAX_EVIDENCE_ITEMS,
        }
    )

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def summary_payload(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "source": self.source,
            "growth_phase": self.growth_phase,
            "cold_start": self.cold_start,
            "streak_days": self.streak_days,
            "achievement_count": self.achievement_count,
            "momentum_score": self.momentum_score,
            "fallback_reason": self.fallback_reason,
        }

    @classmethod
    def build_cold_start(
        cls,
        *,
        user_id: UUID,
        sampled_at: datetime | None = None,
        fallback_reason: str = "no_achievement_data",
    ) -> GrowthSignalContract:
        sampled_at = sampled_at or _utcnow()
        evidence = [
            GrowthSignalEvidence(
                kind="fallback",
                text=_compact_text(fallback_reason or "no_achievement_data", limit=MAX_EVIDENCE_TEXT_LENGTH),
                weight=0.0,
            )
        ]
        return cls(
            user_id=user_id,
            sampled_at=sampled_at,
            cold_start=True,
            fallback_reason=fallback_reason,
            growth_phase="cold_start",
            momentum_score=0.0,
            evidence=evidence,
        )

    @classmethod
    def from_service_data(
        cls,
        *,
        user_id: UUID,
        streak_stats: Any | None,
        user_achievements: Any | None,
        sampled_at: datetime | None = None,
        fallback_reason: str | None = None,
    ) -> GrowthSignalContract:
        sampled_at = sampled_at or _utcnow()
        streak_payload = _as_dict(streak_stats)
        achievements = _as_list(user_achievements)

        streak_days = 0
        for key in ("current_streak", "streak_days", "streak"):
            candidate = streak_payload.get(key)
            if candidate is None:
                continue
            try:
                streak_days = max(0, int(candidate))
                break
            except (TypeError, ValueError):
                continue

        recent_achievements = achievements[:MAX_RECENT_ACHIEVEMENTS]
        recent_achievement_ids: list[str] = []
        recent_achievement_labels: list[str] = []
        for item in recent_achievements:
            achievement_id, achievement_label = _extract_recent_achievement_fields(item)
            if achievement_id:
                recent_achievement_ids.append(achievement_id)
            if achievement_label:
                recent_achievement_labels.append(achievement_label)

        achievement_count = len(achievements)
        cold_start = streak_days <= 0 and achievement_count <= 0 and not recent_achievement_ids and not recent_achievement_labels
        growth_phase = _classify_growth_phase(
            streak_days=streak_days,
            achievement_count=achievement_count,
            cold_start=cold_start,
        )
        momentum_score = _score_momentum(
            streak_days=streak_days,
            achievement_count=achievement_count,
            cold_start=cold_start,
        )

        evidence: list[GrowthSignalEvidence] = []
        if cold_start:
            evidence.append(
                GrowthSignalEvidence(
                    kind="fallback",
                    text=_compact_text(fallback_reason or "no_achievement_data", limit=MAX_EVIDENCE_TEXT_LENGTH),
                    weight=0.0,
                )
            )
        else:
            if streak_days > 0:
                evidence.append(
                    GrowthSignalEvidence(
                        kind="streak",
                        text=_compact_text(f"连续打卡 {streak_days} 天", limit=MAX_EVIDENCE_TEXT_LENGTH),
                        weight=0.55,
                    )
                )
            if achievement_count > 0:
                evidence.append(
                    GrowthSignalEvidence(
                        kind="achievement_count",
                        text=_compact_text(f"累计解锁 {achievement_count} 个成就", limit=MAX_EVIDENCE_TEXT_LENGTH),
                        weight=0.35,
                    )
                )
            if recent_achievement_labels:
                joined = "、".join(recent_achievement_labels[:3])
                evidence.append(
                    GrowthSignalEvidence(
                        kind="recent_achievement",
                        text=_compact_text(f"最近成就：{joined}", limit=MAX_EVIDENCE_TEXT_LENGTH),
                        weight=0.1,
                    )
                )

        if len(evidence) > MAX_EVIDENCE_ITEMS:
            evidence = evidence[:MAX_EVIDENCE_ITEMS]

        if fallback_reason is None and cold_start:
            fallback_reason = "no_achievement_data"

        return cls(
            user_id=user_id,
            sampled_at=sampled_at,
            cold_start=cold_start,
            fallback_reason=fallback_reason,
            streak_days=streak_days,
            achievement_count=achievement_count,
            recent_achievement_ids=recent_achievement_ids,
            recent_achievement_labels=recent_achievement_labels,
            growth_phase=growth_phase,
            momentum_score=momentum_score,
            evidence=evidence,
        )
