from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import STATE_ESTIMATOR_LATENCY, STATE_ESTIMATOR_RUNS
from app.core.telemetry_boundary import (
    STATE_ESTIMATOR_MIN_INTERVAL_SECONDS,
    TELEMETRY_DERIVED_LOAD_CAP,
    TELEMETRY_DERIVED_STRAIN_CAP,
)
from app.models.event import TrackingEvent
from app.models.user_state import UserStateSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


#: V3-FIX-14: one lock per user so the debounce check-then-act below is a
#: single critical section (check freshness -> compute -> commit). Without
#: it, two concurrent telemetry-triggered calls both pass the freshness
#: check and both mint a snapshot. Process-local scope: cross-process
#: duplicates remain theoretically possible but are bounded harm (both
#: writers apply the same cap/debounce bounds; reads take the latest row),
#: matching the V3-FIX-11 receipt's hazard assessment.
_DEBOUNCE_LOCKS: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass
class StateWindow:
    start: datetime
    end: datetime


class StateEstimatorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_state(
        self,
        user_id: UUID,
        timezone_name: str | None,
        *,
        force: bool = False,
    ) -> UserStateSnapshot:
        """Recompute the user's state snapshot from recent telemetry.

        V3-FIX-11 T1 (D-01 R2 F4 "request-arms-the-estimator"): every
        telemetry ingest endpoint call and every cognitive stream worker event
        used to synchronously mint a fresh snapshot here, and the raw
        event-volume term saturated cognitive_load at ~50 events/24h. Two
        bounds now apply:

        - debounce: telemetry-triggered recomputes for the same user are
          rate-limited to one per STATE_ESTIMATOR_MIN_INTERVAL_SECONDS; inside
          the window the latest existing snapshot is returned unchanged, so no
          single telemetry request can synchronously move user state.
        - cap: the telemetry-derived portion of cognitive_load is capped by
          TELEMETRY_DERIVED_LOAD_CAP (see _compute_state).

        ``force=True`` bypasses the debounce for server-side schedulers
        (nightly review etc.) that own their cadence.

        V3-FIX-14: the freshness check and the snapshot write run inside a
        per-user lock (``_DEBOUNCE_LOCKS``), so concurrent telemetry-triggered
        calls serialize: the second caller re-checks freshness after the
        first one committed and gets the existing snapshot instead of minting
        a duplicate. ``force`` still skips the freshness *check*, but its
        write is serialized against the same lock.
        """
        async with _DEBOUNCE_LOCKS[user_id]:
            if not force:
                latest = await self.get_latest_snapshot(user_id)
                if latest is not None and (_utcnow() - latest.snapshot_at) < timedelta(
                    seconds=STATE_ESTIMATOR_MIN_INTERVAL_SECONDS
                ):
                    STATE_ESTIMATOR_RUNS.labels(result="debounced").inc()
                    return latest

            start_time = _utcnow()
            window = self._default_window()
            events = await self._fetch_recent_events(user_id, window)
            snapshot = self._compute_state(user_id, events, window, timezone_name)
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            STATE_ESTIMATOR_RUNS.labels(result="success").inc()
            STATE_ESTIMATOR_LATENCY.observe((_utcnow() - start_time).total_seconds())
            return snapshot

    async def get_latest_snapshot(self, user_id: UUID) -> UserStateSnapshot | None:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .order_by(desc(UserStateSnapshot.snapshot_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_id(self, user_id: UUID, snapshot_id: str) -> UserStateSnapshot | None:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .where(UserStateSnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    def _default_window(self) -> StateWindow:
        end = _utcnow()
        start = end - timedelta(hours=24)
        return StateWindow(start=start, end=end)

    async def _fetch_recent_events(self, user_id: UUID, window: StateWindow) -> list[TrackingEvent]:
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
        events: list[TrackingEvent],
        window: StateWindow,
        timezone_name: str | None,
    ) -> UserStateSnapshot:
        total_events = len(events)
        wrong_events = 0
        focus_start_at: datetime | None = None
        focus_end_at: datetime | None = None
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
            if _utcnow() - focus_start_at < timedelta(hours=2):
                focus_mode = True

        wrong_ratio = wrong_events / max(1, total_events)
        # V3-FIX-11 T1: BOTH terms below are computed from client telemetry
        # (wrong-event counts and raw volume are client-asserted rows in
        # tracking_events), so the combined telemetry-derived load is capped
        # by TELEMETRY_DERIVED_LOAD_CAP: semantically empty noise (heartbeat /
        # screen_view floods, ~50 events/24h) can no longer saturate
        # cognitive_load to 1.0 and drive interruptibility to 0. Direction is
        # preserved (more struggle -> higher load), only the ceiling is
        # bounded. Server-authoritative signals (event_registry domain, D-01)
        # may later add on top of this cap.
        telemetry_load = (wrong_events * 0.15) + (total_events * 0.02)
        cognitive_load = min(min(1.0, telemetry_load), TELEMETRY_DERIVED_LOAD_CAP)
        # V3-FIX-14: strain_index is likewise 100% client-telemetry-derived
        # (wrong-event counts are client-asserted rows) and is consumed on a
        # decision-adjacent surface (plan_context prompt injection), so the
        # forged quiz_wrong flood must not saturate it either. The estimator
        # is the only writer of the column, so this producer-side cap bounds
        # every reader (events API readback, chat prior_outputs, evidence
        # health). Direction preserved, only the ceiling is bounded.
        strain_index = min(
            min(1.0, wrong_ratio + (0.2 if wrong_events >= 3 else 0.0)),
            TELEMETRY_DERIVED_STRAIN_CAP,
        )
        interruptibility = max(0.0, 1.0 - cognitive_load - (0.2 if focus_mode else 0.0))

        tz = None
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
            except Exception:
                tz = None
        now_local = _utcnow().astimezone(tz) if tz else _utcnow()
        time_context = {
            "hour": now_local.hour,
            "weekday": now_local.weekday(),
        }

        derived_event_ids = [event.event_id for event in events[:20]]

        return UserStateSnapshot(
            user_id=user_id,
            snapshot_at=_utcnow(),
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
