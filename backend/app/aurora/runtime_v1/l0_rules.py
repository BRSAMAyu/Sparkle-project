"""
L0 Rule-Aware Aurora — pure deterministic rules, no LLM.

Evaluates deadline_pressure and quiet_hours at each turn start,
feeding results into the Spine StateRegister.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger

from app.signals.state_register import StateRegister
from app.signals.types import ActionableSignal, _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class L0RuleEngine:
    """Deterministic rule evaluations for L0 Aurora level."""

    def __init__(self, redis_client: Any):
        self.register = StateRegister(redis_client)

    async def evaluate_deadline_pressure(
        self,
        user_id: UUID | str,
        *,
        upcoming_deadlines: list[dict[str, Any]],
    ) -> ActionableSignal | None:
        """Check upcoming deadlines and generate deadline_pressure signal if urgent.

        Args:
            upcoming_deadlines: list of {"title": str, "deadline_at": datetime|str, "type": str}
        """
        now = _utcnow()
        nearest_hours: float | None = None
        nearest_title = ""

        for dl in upcoming_deadlines:
            dl_at = self._coerce_datetime(dl.get("deadline_at"))
            if dl_at is None:
                continue
            hours_until = max(0, (dl_at - now).total_seconds() / 3600)
            if nearest_hours is None or hours_until < nearest_hours:
                nearest_hours = hours_until
                nearest_title = str(dl.get("title") or "deadline")

        if nearest_hours is None or nearest_hours > 72:
            return None

        if nearest_hours <= 6:
            confidence = 0.92
            priority = "high"
        elif nearest_hours <= 24:
            confidence = 0.82
            priority = "high"
        elif nearest_hours <= 48:
            confidence = 0.72
            priority = "medium"
        else:
            confidence = 0.58
            priority = "medium"

        signal = ActionableSignal(
            signal_id=_uid("l0"),
            source_event_ids=[f"l0_deadline:{user_id}"],
            source_system="aurora_l0.deadline",
            state_key="deadline_pressure",
            claim="upcoming_deadline_approaching",
            confidence=confidence,
            scope="day",
            ttl_hours=int(nearest_hours) + 1,
            evidence_summary=f"Deadline '{nearest_title}' in {nearest_hours:.1f} hours.",
            possible_effects=["adjust_plan_density", "prioritize_review", "suggest_focus_session"],
            priority=priority,
        )

        try:
            await self.register.upsert_from_signal(str(user_id), signal)
        except Exception as exc:
            logger.warning("L0 deadline_pressure upsert failed: {}", exc)

        return signal

    async def evaluate_quiet_hours(
        self,
        user_id: UUID | str,
        *,
        quiet_start: str = "22:00",
        quiet_end: str = "08:00",
    ) -> bool:
        """Check if current time is within quiet hours.

        Returns True if quiet hours are active. Does NOT generate a signal —
        quiet hours is a suppression rule, not a state.
        """
        now = _utcnow()
        current_minutes = now.hour * 60 + now.minute
        start_minutes = self._parse_hhmm(quiet_start)
        end_minutes = self._parse_hhmm(quiet_end)

        if start_minutes > end_minutes:
            # Spans midnight (e.g., 22:00 → 08:00)
            return current_minutes >= start_minutes or current_minutes < end_minutes
        return start_minutes <= current_minutes < end_minutes

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                return value.astimezone(UTC).replace(tzinfo=None)
            return value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_hhmm(value: str) -> int:
        """Parse 'HH:MM' string to minutes since midnight."""
        parts = str(value).strip().split(":")
        if len(parts) != 2:
            return 0
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, TypeError):
            return 0
