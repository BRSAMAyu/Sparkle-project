from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import TrackingEvent
from app.models.user_state import UserStateSnapshot


@dataclass
class StateWindow:
    start: datetime
    end: datetime


class StateEstimatorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_state(self, user_id: UUID, timezone_name: Optional[str]) -> UserStateSnapshot:
        window = self._default_window()
        events = await self._fetch_recent_events(user_id, window)
        snapshot = self._compute_state(user_id, events, window, timezone_name)
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_snapshot(self, user_id: UUID) -> Optional[UserStateSnapshot]:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .order_by(desc(UserStateSnapshot.snapshot_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_id(self, user_id: UUID, snapshot_id: str) -> Optional[UserStateSnapshot]:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .where(UserStateSnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    def _default_window(self) -> StateWindow:
        end = datetime.utcnow()
        start = end - timedelta(hours=24)
        return StateWindow(start=start, end=end)

    async def _fetch_recent_events(self, user_id: UUID, window: StateWindow) -> List[TrackingEvent]:
        result = await self.db.execute(
            select(TrackingEvent)
            .where(TrackingEvent.user_id == user_id)
            .where(TrackingEvent.received_at >= window.start)
            .order_by(TrackingEvent.received_at.desc())
            .limit(200)
        )
        return list(result.scalars().all())

    def _compute_state(
        self,
        user_id: UUID,
        events: List[TrackingEvent],
        window: StateWindow,
        timezone_name: Optional[str],
    ) -> UserStateSnapshot:
        total_events = len(events)
        wrong_events = 0
        focus_start_at: Optional[datetime] = None
        focus_end_at: Optional[datetime] = None
        sprint_mode = False

        for event in events:
            if event.event_type in {"quiz_wrong", "error_recorded"}:
                wrong_events += 1
            if event.event_type == "question_submit":
                payload = event.payload or {}
                if payload.get("correct") is False:
                    wrong_events += 1
            if event.event_type == "focus_start":
                focus_start_at = event.received_at
            if event.event_type == "focus_end":
                focus_end_at = event.received_at
            payload = event.payload or {}
            if payload.get("sprint_mode") is True:
                sprint_mode = True

        focus_mode = False
        if focus_start_at and (not focus_end_at or focus_end_at < focus_start_at):
            if datetime.utcnow() - focus_start_at < timedelta(hours=2):
                focus_mode = True

        wrong_ratio = wrong_events / max(1, total_events)
        cognitive_load = min(1.0, (wrong_events * 0.15) + (total_events * 0.02))
        strain_index = min(1.0, wrong_ratio + (0.2 if wrong_events >= 3 else 0.0))
        interruptibility = max(0.0, 1.0 - cognitive_load - (0.2 if focus_mode else 0.0))

        tz = None
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
            except Exception:
                tz = None
        now_local = datetime.utcnow().astimezone(tz) if tz else datetime.utcnow()
        time_context = {
            "hour": now_local.hour,
            "weekday": now_local.weekday(),
        }

        derived_event_ids = [event.event_id for event in events[:20]]

        return UserStateSnapshot(
            user_id=user_id,
            snapshot_at=datetime.utcnow(),
            window_start=window.start,
            window_end=window.end,
            cognitive_load=cognitive_load,
            interruptibility=interruptibility,
            strain_index=strain_index,
            focus_mode=focus_mode,
            sprint_mode=sprint_mode,
            knowledge_state=None,
            time_context=time_context,
            derived_event_ids=derived_event_ids,
        )
