from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.metrics import ROUTING_OUTCOME_BACKFILL_LATENCY
from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
from app.models.aurora_stage20 import RoutingDecisionLog
from app.services.source_state_encoder import build_backfill_source_state, encode_source_state_key


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


SUCCESS_OUTCOMES = {"task_completion", "plan_success"}
CANONICAL_OUTCOMES = {"task_completion", "plan_success", "user_correction", "timeout"}


class RouteHistoryService:
    """Stage 20 write-only route history collector."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_decision(
        self,
        *,
        user_id: UUID,
        input_aggregator_snapshot_id: str,
        decision_type: str,
        decision_payload: dict[str, Any],
        skills_injected: list[UUID] | None = None,
        sufficiency_judgment_id: UUID | None = None,
        decided_at: datetime | None = None,
        decision_id: UUID | None = None,
        source_state_v2: dict[str, str] | None = None,
        source_state_v2_key: str | None = None,
    ) -> UUID:
        now = decided_at or _utcnow()
        resolved_source_state = source_state_v2 or build_backfill_source_state(
            decision_type=decision_type,
            decision_payload=decision_payload,
            skills_injected=[str(item) for item in (skills_injected or [])],
        )
        record = RoutingDecisionLog(
            decision_id=decision_id or uuid.uuid4(),
            created_at=now,
            updated_at=now,
            user_id=user_id,
            decided_at=now,
            input_aggregator_snapshot_id=input_aggregator_snapshot_id,
            sufficiency_judgment_id=sufficiency_judgment_id,
            decision_type=decision_type,
            decision_payload=decision_payload,
            source_state_v2=resolved_source_state,
            source_state_v2_key=source_state_v2_key or encode_source_state_key(resolved_source_state),
            skills_injected=[str(item) for item in (skills_injected or [])],
        )
        self.db.add(record)
        await self.db.commit()
        return UUID(str(record.decision_id))

    async def record_explicit_feedback(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        positive: bool,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="plan_success" if positive else "user_correction",
            legacy_outcome_type="thumbs_up" if positive else "thumbs_down",
            collected_at=collected_at,
        )

    async def record_follow_up_input(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="task_completion",
            legacy_outcome_type="implicit_follow_up",
            collected_at=collected_at,
        )

    async def mark_timeout(
        self,
        *,
        decision_id: UUID,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id="timeout",
            outcome="timeout",
            legacy_outcome_type="timeout",
            collected_at=collected_at,
        )

    async def record_plan_success(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="plan_success",
            legacy_outcome_type="plan_success",
            collected_at=collected_at,
        )

    async def record_task_completion(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="task_completion",
            legacy_outcome_type="task_completion",
            collected_at=collected_at,
        )

    async def record_user_correction(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="user_correction",
            legacy_outcome_type="user_correction",
            collected_at=collected_at,
        )

    async def _record_outcome(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        outcome: str,
        legacy_outcome_type: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        if outcome not in CANONICAL_OUTCOMES:
            raise ValueError(f"Unsupported routing outcome: {outcome}")
        record = await self._load_decision(decision_id)
        if record is None:
            return None
        outcome_at = collected_at or _utcnow()
        record.outcome_signal_id = outcome_signal_id
        record.outcome = outcome
        record.outcome_timestamp = outcome_at
        record.outcome_type = legacy_outcome_type
        record.outcome_collected_at = outcome_at
        record.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        latency = max(0.0, (outcome_at - record.decided_at).total_seconds())
        ROUTING_OUTCOME_BACKFILL_LATENCY.labels(outcome=outcome).observe(latency)
        await self._update_learner(record, outcome=outcome)
        return record

    async def _load_decision(self, decision_id: UUID) -> RoutingDecisionLog | None:
        result = await self.db.execute(
            select(RoutingDecisionLog).where(RoutingDecisionLog.decision_id == decision_id)
        )
        return result.scalar_one_or_none()

    async def _update_learner(self, record: RoutingDecisionLog, *, outcome: str) -> None:
        route_execution_mode = str((record.decision_payload or {}).get("route_execution_mode") or "").strip()
        source_key = str(record.source_state_v2_key or "").strip()
        if not route_execution_mode or not source_key:
            return
        learner = PersistentBayesianLearner(cache_service.redis, user_id=str(record.user_id))
        await learner.update_for_state(source_key, route_execution_mode, outcome in SUCCESS_OUTCOMES)
        await learner.drain_pending_saves()
