"""
Core: signals / safety
Phase: adapt
GOV-016 — Automatic Safety Degradation Mode

When quality guard failures or anomalous patterns are detected,
the system automatically reduces capabilities to protect the user.

Thresholds:
  NORMAL     — quality >= 0.7  AND  errors < 3
  CAUTION    — quality [0.4, 0.7)  OR  errors [3, 5]
  RESTRICTED — quality < 0.4  OR  errors > 5  OR  hallucination flag
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from loguru import logger


class SafetyDegradationLevel(StrEnum):
    NORMAL = "normal"
    CAUTION = "caution"
    RESTRICTED = "restricted"


# Capabilities disabled at each level (cumulative: CAUTION disables its own, RESTRICTED adds more)
_RESTRICTED_CAPS: dict[SafetyDegradationLevel, list[str]] = {
    SafetyDegradationLevel.NORMAL: [],
    SafetyDegradationLevel.CAUTION: [
        "proactive_intervention",
        "new_chapter_suggestion",
        "auto_plan_adjustment",
    ],
    SafetyDegradationLevel.RESTRICTED: [
        "model_write",
        "proactive_intervention",
        "new_chapter_suggestion",
        "auto_plan_adjustment",
        "skill_auto_extraction",
        "community_signal_injection",
    ],
}

_REDIS_KEY_PREFIX = "sparkle:safety_degradation:"
_TTL_SECONDS = 86400  # 24 hours


class SafetyDegradationManager:
    """Evaluates quality signals and degrades system capabilities when needed."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_and_degrade(
        self,
        user_id: str,
        quality_score: float,
        error_count: int,
        anomaly_flags: list[str] | None = None,
    ) -> SafetyDegradationLevel:
        anomaly_flags = anomaly_flags or []
        level = self._classify(quality_score, error_count, anomaly_flags)

        if level != SafetyDegradationLevel.NORMAL:
            reason = self._build_reason(quality_score, error_count, anomaly_flags)
            await self.record_degradation_event(user_id, level, reason)
            logger.warning(
                "safety_degradation uid=%s level=%s reason=%s",
                user_id,
                level.value,
                reason,
            )
        else:
            # Clear any previous degradation when conditions improve
            await self._redis.delete(f"{_REDIS_KEY_PREFIX}{user_id}")

        return level

    async def get_current_level(self, user_id: str) -> SafetyDegradationLevel:
        raw = await self._redis.get(f"{_REDIS_KEY_PREFIX}{user_id}")
        if raw is None:
            return SafetyDegradationLevel.NORMAL
        try:
            data = json.loads(raw)
            return SafetyDegradationLevel(data.get("level", "normal"))
        except (json.JSONDecodeError, ValueError):
            return SafetyDegradationLevel.NORMAL

    async def record_degradation_event(
        self, user_id: str, level: SafetyDegradationLevel, reason: str
    ) -> None:
        payload = json.dumps({
            "level": level.value,
            "reason": reason,
            "restricted_capabilities": _RESTRICTED_CAPS[level],
            "ts": datetime.now(UTC).isoformat(),
        })
        await self._redis.set(
            f"{_REDIS_KEY_PREFIX}{user_id}", payload, ex=_TTL_SECONDS
        )

    @staticmethod
    def get_restricted_capabilities(level: SafetyDegradationLevel) -> list[str]:
        return list(_RESTRICTED_CAPS[level])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(
        quality_score: float, error_count: int, anomaly_flags: list[str]
    ) -> SafetyDegradationLevel:
        if (
            quality_score < 0.4
            or error_count > 5
            or "hallucination" in anomaly_flags
        ):
            return SafetyDegradationLevel.RESTRICTED
        if quality_score < 0.7 or error_count >= 3:
            return SafetyDegradationLevel.CAUTION
        return SafetyDegradationLevel.NORMAL

    @staticmethod
    def _build_reason(
        quality_score: float, error_count: int, anomaly_flags: list[str]
    ) -> str:
        parts: list[str] = []
        if quality_score < 0.4:
            parts.append(f"quality={quality_score:.2f}(<0.4)")
        elif quality_score < 0.7:
            parts.append(f"quality={quality_score:.2f}(<0.7)")
        if error_count > 5:
            parts.append(f"errors={error_count}(>5)")
        elif error_count >= 3:
            parts.append(f"errors={error_count}(>=3)")
        if anomaly_flags:
            parts.append(f"anomalies={anomaly_flags}")
        return "; ".join(parts) or "unknown"
