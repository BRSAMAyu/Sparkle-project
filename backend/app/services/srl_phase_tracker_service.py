from __future__ import annotations

import asyncio
import math
import os
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.metrics import (
    SRL_DLQ_SIZE,
    SRL_EVENT_CONSUMED_TOTAL,
    SRL_EVENT_LAG_P95,
    SRL_PHASE_TRANSITION_TOTAL,
    SRL_PHASE_UNKNOWN_RATE,
    SRL_TRACKER_LOCK_CONTENTION_TOTAL,
)
from app.db.session import AsyncSessionLocal
from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage29_srl_kill_switch_service import (
    AuroraStage29SRLKillSwitchService,
)
from app.services.srl_phase_traits import derive_coldstart_phase_from_traits
from app.services.srl_phase_types import (
    INACTIVE_TIMEOUT_HOURS,
    SRLPhase,
    SRLPhaseState,
    get_transition_rule,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SRLPhaseTrackerService:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "srl_phase_tracker"
    CACHE_PREFIX = "aurora:stage29:srl:state:"
    CACHE_TTL_SECONDS = 60 * 60 * 24
    MAX_EVIDENCE_IDS = 12
    FORCE_RESET_CONFIDENCE_CAP = 0.8
    EVIDENCE_ID_PATTERN = re.compile(r"^[a-zA-Z_]+:[A-Za-z0-9\-:.]+$")

    def __init__(
        self,
        db: AsyncSession | None = None,
        *,
        event_bus: EventBus | None = None,
        redis=None,
        now_factory=_utcnow,
    ) -> None:
        self.db = db
        self.event_bus = event_bus
        self.redis = redis or cache_service.redis
        self.now_factory = now_factory
        self.kill_switch = AuroraStage29SRLKillSwitchService()
        self.consumer_name = f"srl-phase-{os.getpid()}"
        self._running = False
        self._subscribed = False
        self._local_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._recent_lag_samples: list[float] = []

    async def start(self) -> None:
        if self.event_bus is None:
            raise RuntimeError("event_bus is required to start SRLPhaseTrackerService")

        await self.event_bus.connect()
        if self._running:
            return
        self._running = True

        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self.handle_event,
                    )
                    self._subscribed = True
                    logger.info(
                        "SRLPhaseTrackerService subscribed to {}", self.STREAM_NAME
                    )
                await asyncio.sleep(1)
            except Exception as exc:
                self._subscribed = False
                logger.error("SRLPhaseTrackerService loop error: {}", exc)
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def handle_event(self, event: dict[str, Any]) -> SRLPhaseState | None:
        event_type = str(event.get("event_type") or "").strip()
        if event_type.startswith("srl.") and event_type != "srl.phase.transition":
            return None
        if event_type != "srl.phase.transition":
            return None
        return await self.handle_transition_event(event)

    async def handle_transition_event(
        self, event: dict[str, Any]
    ) -> SRLPhaseState | None:
        mode = await self.kill_switch.get_mode()
        tracker_mode = await self.kill_switch.get_tracker_mode()
        if mode == "off" or tracker_mode == "off":
            return None
        live_write = mode == "live" and tracker_mode == "live"

        event_type = str(event.get("event_type") or "").strip()
        if event_type.startswith("srl.") and event_type != "srl.phase.transition":
            return None

        user_id = self._normalize_user_id(event.get("user_id"))
        trigger_event_type = str(event.get("trigger_event_type") or "").strip()
        if not trigger_event_type:
            raise ValueError("trigger_event_type is required")

        evidence_id = str(
            event.get("evidence_id") or self._default_evidence_id(trigger_event_type)
        ).strip()
        if not self._is_valid_evidence_id(evidence_id):
            raise ValueError(f"invalid evidence_id: {evidence_id}")
        metadata = dict(event.get("metadata") or {})
        published_at = self._coerce_datetime(event.get("published_at"))

        async with self._user_lock(str(user_id)):
            async with self._distributed_lock(str(user_id)):
                async with self._session_scope() as (db, owns_session):
                    current_state = await self._get_current_phase_for_transition(
                        db,
                        user_id,
                        persist_missing=live_write,
                    )
                    current_state = self._apply_inactivity_if_needed(current_state)

                    rule = get_transition_rule(
                        current_state.current_phase, trigger_event_type
                    )
                    if rule is None:
                        SRL_EVENT_CONSUMED_TOTAL.labels(
                            trigger_event_type=trigger_event_type,
                            status="ignored",
                        ).inc()
                        return current_state

                    if not rule.allowed:
                        SRL_EVENT_CONSUMED_TOTAL.labels(
                            trigger_event_type=trigger_event_type,
                            status="rejected",
                        ).inc()
                        return current_state

                    next_state = self._transition_state(
                        current_state=current_state,
                        next_phase=rule.to_phase,
                        evidence_id=evidence_id,
                        metadata=metadata,
                    )
                    if live_write:
                        await self._persist_state(db, next_state)
                        if owns_session:
                            await db.commit()

                    self._record_transition_metrics(current_state, next_state)
                    self._record_lag_metrics(published_at)
                    SRL_EVENT_CONSUMED_TOTAL.labels(
                        trigger_event_type=trigger_event_type,
                        status="applied" if live_write else "shadow",
                    ).inc()
                    return next_state

    async def get_current_phase(self, user_id: UUID | str) -> SRLPhaseState:
        normalized_user_id = self._normalize_user_id(user_id)
        write_mode = await self._tracker_write_mode()
        if write_mode == "off":
            return self._default_state(normalized_user_id)
        async with self._session_scope() as (db, owns_session):
            state = await self._get_current_phase_for_transition(
                db,
                normalized_user_id,
                persist_missing=write_mode == "live",
            )
            state = self._apply_inactivity_if_needed(state)
            if write_mode == "live":
                await self._persist_state(db, state)
                if owns_session:
                    await db.commit()
                await self._persist_cache(state)
            return state

    async def force_reset(
        self,
        user_id: UUID | str,
        phase: SRLPhase | str,
        justification: str,
    ) -> SRLPhaseState:
        normalized_user_id = self._normalize_user_id(user_id)
        next_phase = (
            phase
            if isinstance(phase, SRLPhase)
            else SRLPhase(str(phase).strip().upper())
        )
        cleaned_justification = str(justification or "").strip()
        if not cleaned_justification:
            raise ValueError("justification is required")
        write_mode = await self._tracker_write_mode()
        if write_mode == "off":
            return self._default_state(normalized_user_id)
        evidence_id = self._force_reset_evidence_id(cleaned_justification)
        async with self._user_lock(str(normalized_user_id)):
            async with self._distributed_lock(str(normalized_user_id)):
                async with self._session_scope() as (db, owns_session):
                    current_state = await self._get_current_phase_for_transition(
                        db,
                        normalized_user_id,
                        persist_missing=write_mode == "live",
                    )
                    decided_at = self.now_factory()
                    forced_state = SRLPhaseState(
                        user_id=normalized_user_id,
                        current_phase=next_phase,
                        previous_phase=current_state.current_phase,
                        phase_started_at=decided_at,
                        transition_evidence_ids=self._append_evidence_ids(
                            current_state.transition_evidence_ids,
                            evidence_id,
                        ),
                        confidence=self.FORCE_RESET_CONFIDENCE_CAP,
                        source="default",
                        updated_at=decided_at,
                    )
                    if write_mode == "live":
                        await self._persist_state(db, forced_state)
                        await self._write_force_reset_audit(
                            db,
                            user_id=normalized_user_id,
                            previous_phase=current_state.current_phase,
                            next_phase=next_phase,
                            justification=cleaned_justification,
                            confidence=forced_state.confidence,
                            decided_at=decided_at,
                        )
                        if owns_session:
                            await db.commit()
                    self._record_transition_metrics(current_state, forced_state)
                    return forced_state

    async def collect_runtime_metrics(self) -> dict[str, Any]:
        if self.event_bus is None:
            return {"lag_p95": 0.0, "dlq_size": 0}

        lag_info = await self.event_bus.get_consumer_lag(
            stream=self.STREAM_NAME, group_name=self.GROUP_NAME
        )
        lag_values = [
            float(group.get("lag_time_seconds") or 0.0)
            for group in lag_info.get("groups", [])
            if group.get("name") == self.GROUP_NAME
        ]
        lag_p95 = self._p95(lag_values)
        SRL_EVENT_LAG_P95.set(lag_p95)
        await self.kill_switch.record_event_lag_p95(lag_p95, now=self.now_factory())

        dlq_stats = await self.event_bus.get_dlq_stats(stream=self.STREAM_NAME)
        dlq_size = int(dlq_stats.get("message_count") or 0)
        SRL_DLQ_SIZE.set(dlq_size)
        return {"lag_p95": lag_p95, "dlq_size": dlq_size}

    @asynccontextmanager
    async def _session_scope(self):
        if self.db is not None:
            yield self.db, False
            return
        async with AsyncSessionLocal() as db:
            yield db, True

    @asynccontextmanager
    async def _user_lock(self, user_id: str):
        lock = self._local_locks[user_id]
        async with lock:
            yield

    @asynccontextmanager
    async def _distributed_lock(self, user_id: str):
        lock_context = None
        try:
            lock_context = cache_service.distributed_lock(
                f"srl-phase:{user_id}", expire=10
            )
            await lock_context.__aenter__()
        except Exception:
            SRL_TRACKER_LOCK_CONTENTION_TOTAL.labels(mode="fallback").inc()
            yield
            return
        try:
            yield
        finally:
            if lock_context is not None:
                await lock_context.__aexit__(None, None, None)

    async def _get_current_phase_internal(
        self, db: AsyncSession, user_id: UUID
    ) -> SRLPhaseState:
        return await self._get_current_phase_for_transition(
            db,
            user_id,
            persist_missing=True,
        )

    async def _tracker_write_mode(self) -> str:
        mode = await self.kill_switch.get_mode()
        tracker_mode = await self.kill_switch.get_tracker_mode()
        if mode == "off" or tracker_mode == "off":
            return "off"
        return "live" if mode == "live" and tracker_mode == "live" else "shadow"

    async def _get_current_phase_for_transition(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        persist_missing: bool,
    ) -> SRLPhaseState:
        cached = await self._load_cached_state(user_id)
        if cached is not None:
            return cached

        record = await self._get_state_record(db, user_id)
        if record is not None:
            state = self._state_from_record(record)
            if persist_missing:
                await self._persist_cache(state)
            return state

        traits_prior = await self._load_traits_prior(db, user_id)
        coldstart_state = derive_coldstart_phase_from_traits(
            user_id=user_id, traits_prior=traits_prior
        )
        if persist_missing:
            await self._persist_state(db, coldstart_state)
            await self._persist_cache(coldstart_state)
        return coldstart_state

    async def _get_state_record(
        self, db: AsyncSession, user_id: UUID
    ) -> SRLPhaseStateRecord | None:
        result = await db.execute(
            select(SRLPhaseStateRecord).where(SRLPhaseStateRecord.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _load_traits_prior(
        self, db: AsyncSession, user_id: UUID
    ) -> dict[str, Any]:
        result = await db.execute(
            select(UserPreferencesCenter.traits_prior).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        traits_prior = result.scalar_one_or_none()
        return dict(traits_prior or {})

    def _default_state(self, user_id: UUID) -> SRLPhaseState:
        now = self.now_factory()
        return SRLPhaseState(
            user_id=user_id,
            current_phase=SRLPhase.UNKNOWN,
            previous_phase=None,
            phase_started_at=now,
            transition_evidence_ids=(),
            confidence=0.0,
            source="default",
            updated_at=now,
        )

    async def _load_cached_state(self, user_id: UUID) -> SRLPhaseState | None:
        payload = await cache_service.get(self._cache_key(user_id))
        if not isinstance(payload, dict):
            return None
        try:
            return SRLPhaseState.model_validate(payload)
        except Exception:
            return None

    async def _persist_cache(self, state: SRLPhaseState) -> None:
        await cache_service.set(
            self._cache_key(state.user_id),
            state.model_dump(mode="json"),
            ttl=self.CACHE_TTL_SECONDS,
        )

    async def _persist_state(self, db: AsyncSession, state: SRLPhaseState) -> None:
        record = await self._get_state_record(db, state.user_id)
        if record is None:
            record = SRLPhaseStateRecord(
                user_id=state.user_id,
                current_phase=state.current_phase.value,
                phase_started_at=state.phase_started_at,
                previous_phase=(
                    state.previous_phase.value if state.previous_phase else None
                ),
                transition_evidence_ids=list(state.transition_evidence_ids),
                confidence=state.confidence,
                source=state.source,
                updated_at=state.updated_at,
            )
            db.add(record)
        else:
            record.current_phase = state.current_phase.value
            record.phase_started_at = state.phase_started_at
            record.previous_phase = (
                state.previous_phase.value if state.previous_phase else None
            )
            record.transition_evidence_ids = list(state.transition_evidence_ids)
            record.confidence = state.confidence
            record.source = state.source
            record.updated_at = state.updated_at
        await db.flush()
        await self._persist_cache(state)

    def _transition_state(
        self,
        *,
        current_state: SRLPhaseState,
        next_phase: SRLPhase,
        evidence_id: str,
        metadata: dict[str, Any],
    ) -> SRLPhaseState:
        now = self.now_factory()
        previous_phase = current_state.current_phase
        phase_started_at = current_state.phase_started_at
        if next_phase != current_state.current_phase:
            phase_started_at = now

        evidence_ids = self._append_evidence_ids(
            current_state.transition_evidence_ids, evidence_id
        )
        if metadata.get("plan_id"):
            evidence_ids = self._append_evidence_ids(
                evidence_ids, f"plan:{metadata['plan_id']}"
            )

        return SRLPhaseState(
            user_id=current_state.user_id,
            current_phase=next_phase,
            previous_phase=previous_phase,
            phase_started_at=phase_started_at,
            transition_evidence_ids=evidence_ids,
            confidence=self._confidence_for_transition(
                next_phase=next_phase, same_phase=next_phase == previous_phase
            ),
            source="event_triggered",
            updated_at=now,
        )

    def _apply_inactivity_if_needed(self, state: SRLPhaseState) -> SRLPhaseState:
        timeout = timedelta(hours=INACTIVE_TIMEOUT_HOURS)
        if self.now_factory() - state.updated_at <= timeout:
            return state
        now = self.now_factory()
        return SRLPhaseState(
            user_id=state.user_id,
            current_phase=SRLPhase.UNKNOWN,
            previous_phase=state.current_phase,
            phase_started_at=now,
            transition_evidence_ids=self._append_evidence_ids(
                state.transition_evidence_ids, "inactive_timeout"
            ),
            confidence=0.0,
            source="default",
            updated_at=now,
        )

    def _record_transition_metrics(
        self, previous: SRLPhaseState, current: SRLPhaseState
    ) -> None:
        SRL_PHASE_TRANSITION_TOTAL.labels(
            from_phase=previous.current_phase.value,
            to_phase=current.current_phase.value,
            source=current.source,
        ).inc()
        SRL_PHASE_UNKNOWN_RATE.set(
            1.0 if current.current_phase == SRLPhase.UNKNOWN else 0.0
        )

    def _record_lag_metrics(self, published_at: datetime | None) -> None:
        if published_at is None:
            return
        lag_seconds = max(0.0, (self.now_factory() - published_at).total_seconds())
        self._recent_lag_samples.append(lag_seconds)
        self._recent_lag_samples = self._recent_lag_samples[-100:]
        lag_p95 = self._p95(self._recent_lag_samples)
        SRL_EVENT_LAG_P95.set(lag_p95)

    def _append_evidence_ids(self, existing: list[str], evidence_id: str) -> list[str]:
        normalized = [item for item in existing if str(item).strip()]
        if evidence_id and evidence_id not in normalized:
            normalized.append(evidence_id)
        return normalized[-self.MAX_EVIDENCE_IDS :]

    async def _write_force_reset_audit(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        previous_phase: SRLPhase,
        next_phase: SRLPhase,
        justification: str,
        confidence: float,
        decided_at: datetime,
    ) -> None:
        db.add(
            RoutingDecisionLog(
                created_at=decided_at,
                updated_at=decided_at,
                user_id=user_id,
                decided_at=decided_at,
                input_aggregator_snapshot_id="aurora_stage29_srl_force_reset",
                decision_type="aurora_srl_force_reset",
                decision_payload={
                    "previous_phase": previous_phase.value,
                    "next_phase": next_phase.value,
                    "justification": justification,
                    "confidence": round(float(confidence), 4),
                    "rule": "AR",
                },
                source_state_v2={
                    "component": "srl_phase_tracker",
                    "mode": "manual_override",
                },
                source_state_v2_key="aurora.stage29.srl.force_reset",
            )
        )

    def _confidence_for_transition(
        self, *, next_phase: SRLPhase, same_phase: bool
    ) -> float:
        if next_phase == SRLPhase.UNKNOWN:
            return 0.0
        if same_phase:
            return 0.72
        return {
            SRLPhase.FORETHOUGHT: 0.78,
            SRLPhase.PERFORMANCE: 0.84,
            SRLPhase.SELF_REFLECTION: 0.8,
            SRLPhase.UNKNOWN: 0.0,
        }[next_phase]

    @staticmethod
    def _state_from_record(record: SRLPhaseStateRecord) -> SRLPhaseState:
        return SRLPhaseState(
            user_id=record.user_id,
            current_phase=SRLPhase(record.current_phase),
            phase_started_at=record.phase_started_at,
            previous_phase=(
                SRLPhase(record.previous_phase) if record.previous_phase else None
            ),
            transition_evidence_ids=list(record.transition_evidence_ids or []),
            confidence=float(record.confidence or 0.0),
            source=record.source,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _normalize_user_id(user_id: UUID | str | None) -> UUID:
        if user_id is None or not str(user_id).strip():
            raise ValueError("user_id is required")
        if isinstance(user_id, UUID):
            return user_id
        return UUID(str(user_id).strip())

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
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    @classmethod
    def _default_evidence_id(cls, trigger_event_type: str) -> str:
        prefix = (
            re.sub(r"[^A-Za-z_]+", "_", str(trigger_event_type or "").strip()).strip(
                "_"
            )
            or "event"
        )
        return f"{prefix}:{_utcnow().isoformat()}"

    @classmethod
    def _force_reset_evidence_id(cls, justification: str) -> str:
        suffix = (
            re.sub(r"[^A-Za-z0-9\-:.]+", "_", str(justification or "").strip()).strip(
                "_"
            )
            or "manual"
        )
        return f"force_reset:{suffix}"

    @classmethod
    def _is_valid_evidence_id(cls, evidence_id: str) -> bool:
        normalized = str(evidence_id or "").strip()
        if not normalized:
            return False
        if cls.EVIDENCE_ID_PATTERN.match(normalized):
            return True
        try:
            UUID(normalized)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _p95(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(float(item) for item in values)
        index = max(0, math.ceil(len(ordered) * 0.95) - 1)
        return round(ordered[index], 4)

    @classmethod
    def _cache_key(cls, user_id: UUID) -> str:
        return f"{cls.CACHE_PREFIX}{user_id}"
