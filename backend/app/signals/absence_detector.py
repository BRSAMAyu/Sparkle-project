"""
Core: execution
Phase: sense
Stage: Signal-to-Action Spine P1-7 MAGIC-004 Automatic Absence Detection

Proactive absence detection — detects when users are away and generates
signals for the spine pipeline, enabling timely nudges and plan adjustments.

Absence levels:
- idle: 15-60 min (still connected, no activity)
- short: 60 min - 6h (likely stepped away)
- prolonged: 6-48h (missed session)
- extended: 48h+ (disengaged)

Uses Redis keys:
- spine:last_chat_turn_at:{user_id}  (written by _record_chat_turn_heartbeat)
- spine:absence_cooldown:{user_id}:{level}  (per-level cooldown)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


@dataclass
class AbsenceSnapshot:
    user_id: str
    absence_level: str  # "idle" | "short" | "prolonged" | "extended"
    elapsed_minutes: float
    last_interaction_at: str | None
    has_active_goal: bool
    has_active_task: bool
    deadline_days: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "absence_level": self.absence_level,
            "elapsed_minutes": self.elapsed_minutes,
            "last_interaction_at": self.last_interaction_at,
            "has_active_goal": self.has_active_goal,
            "has_active_task": self.has_active_task,
            "deadline_days": self.deadline_days,
        }


# ── Thresholds (minutes) ────────────────────────────────────────────

_THRESHOLDS: list[tuple[str, int]] = [
    ("extended", 2880),   # 48h
    ("prolonged", 360),   # 6h
    ("short", 60),        # 1h
    ("idle", 15),         # 15 min
]

_COOLDOWN_SECONDS: dict[str, int] = {
    "idle": 1800,         # 30 min — don't re-signal idle frequently
    "short": 7200,        # 2h
    "prolonged": 86400,   # 24h
    "extended": 172800,   # 48h
}

_EFFECTS: dict[str, list[str]] = {
    "idle": [
        "record_idle_state",
        "skip_nudge",
    ],
    "short": [
        "queue_gentle_recall",
        "check_task_status",
    ],
    "prolonged": [
        "schedule_recall_nudge",
        "adjust_plan_pacing",
        "notify_accountability_partner",
    ],
    "extended": [
        "send_reengagement_message",
        "pause_plan_gracefully",
        "notify_accountability_partner",
    ],
}


def classify(elapsed_minutes: float) -> str:
    """Map elapsed minutes to absence level."""
    for level, threshold in _THRESHOLDS:
        if elapsed_minutes >= threshold:
            return level
    return "present"


class AbsenceDetector:
    """Proactive absence detection for MAGIC-004.

    Scans Redis heartbeat keys to find users who have been away,
    respects per-level cooldowns, and produces ActionableSignals.
    """

    async def scan_absent_users(
        self,
        redis: Any,
        *,
        min_level: str = "short",
    ) -> list[AbsenceSnapshot]:
        """Scan all users with heartbeat keys and return those absent >= min_level.

        Args:
            redis: Async Redis client.
            min_level: Minimum absence level to include (idle/short/prolonged/extended).

        Returns:
            List of AbsenceSnapshot for absent users past cooldown.
        """
        min_order = _level_order(min_level)
        now = datetime.now(UTC)
        results: list[AbsenceSnapshot] = []

        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match="spine:last_chat_turn_at:*",
                count=100,
            )
            if not keys:
                if cursor == 0:
                    break
                continue

            pipe = redis.pipeline()
            for key in keys:
                pipe.get(key)
            values = await pipe.execute()

            for key, raw_val in zip(keys, values):
                if raw_val is None:
                    continue
                val = raw_val.decode() if isinstance(raw_val, bytes) else raw_val
                user_id = key.decode().split(":")[-1] if isinstance(key, bytes) else str(key).split(":")[-1]

                try:
                    prev_dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                    elapsed_min = (now - prev_dt).total_seconds() / 60
                except (ValueError, TypeError):
                    continue

                level = classify(elapsed_min)
                if _level_order(level) < min_order:
                    continue

                on_cooldown = await self._check_cooldown(redis, user_id, level)
                if on_cooldown:
                    continue

                has_active_task = await self._has_active_task(redis, user_id)

                results.append(AbsenceSnapshot(
                    user_id=user_id,
                    absence_level=level,
                    elapsed_minutes=elapsed_min,
                    last_interaction_at=val,
                    has_active_goal=True,
                    has_active_task=has_active_task,
                ))

            if cursor == 0:
                break

        return results

    async def check_user(
        self,
        user_id: str,
        redis: Any,
    ) -> AbsenceSnapshot | None:
        """Check absence state for a single user.

        Returns AbsenceSnapshot if absent, None if present or on cooldown.
        """
        key = f"spine:last_chat_turn_at:{user_id}"
        raw_val = await redis.get(key)
        if raw_val is None:
            return None

        val = raw_val.decode() if isinstance(raw_val, bytes) else raw_val
        now = datetime.now(UTC)

        try:
            prev_dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            elapsed_min = (now - prev_dt).total_seconds() / 60
        except (ValueError, TypeError):
            return None

        level = classify(elapsed_min)
        if level == "present":
            return None

        on_cooldown = await self._check_cooldown(redis, user_id, level)
        if on_cooldown:
            return None

        has_active_task = await self._has_active_task(redis, user_id)

        return AbsenceSnapshot(
            user_id=user_id,
            absence_level=level,
            elapsed_minutes=elapsed_min,
            last_interaction_at=val,
            has_active_goal=True,
            has_active_task=has_active_task,
        )

    def to_actionable_signal(self, snapshot: AbsenceSnapshot) -> ActionableSignal:
        """Convert absence snapshot to an ActionableSignal."""
        level = snapshot.absence_level

        claim_map: dict[str, str] = {
            "idle": "user_idle",
            "short": "user_short_absence",
            "prolonged": "user_prolonged_absence",
            "extended": "user_extended_absence",
        }

        evidence = (
            f"User {snapshot.user_id} absent for "
            f"{snapshot.elapsed_minutes:.0f} minutes (level={level})."
        )

        return ActionableSignal(
            signal_id=_uid("abs"),
            source_event_ids=[f"absence_scan_{level}"],
            source_system="absence_detector",
            state_key="engagement_pattern",
            claim=claim_map.get(level, "user_absent"),
            confidence=_confidence(level, snapshot),
            scope="current_sprint",
            ttl_hours=_ttl(level),
            evidence_summary=evidence,
            possible_effects=_EFFECTS.get(level, ["record_absence"]),
            priority="high" if level in ("prolonged", "extended") else "medium",
        )

    async def mark_cooldown(self, redis: Any, user_id: str, level: str) -> None:
        """Set cooldown so the same absence level isn't re-signaled."""
        cooldown = _COOLDOWN_SECONDS.get(level, 3600)
        key = f"spine:absence_cooldown:{user_id}:{level}"
        await redis.set(key, "1", ex=cooldown)

    # ── Private ────────────────────────────────────────────────────

    async def _check_cooldown(self, redis: Any, user_id: str, level: str) -> bool:
        """Return True if this level is on cooldown for the user."""
        key = f"spine:absence_cooldown:{user_id}:{level}"
        val = await redis.exists(key)
        return bool(val)

    async def _has_active_task(self, redis: Any, user_id: str) -> bool:
        """Check if user has an active task."""
        key = f"spine:session_active:{user_id}"
        return bool(await redis.exists(key))


def _level_order(level: str) -> int:
    return {"present": 0, "idle": 1, "short": 2, "prolonged": 3, "extended": 4}.get(level, 0)


def _confidence(level: str, snapshot: AbsenceSnapshot) -> float:
    base = {"idle": 0.70, "short": 0.80, "prolonged": 0.88, "extended": 0.92}.get(level, 0.70)
    if snapshot.has_active_task:
        base = min(base + 0.05, 0.95)
    return base


def _ttl(level: str) -> int:
    return {"idle": 4, "short": 12, "prolonged": 48, "extended": 72}.get(level, 12)
