from __future__ import annotations

import uuid
from dataclasses import dataclass
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
DECISION_CHAIN_KEYS = (
    "parent_decision_id",
    "previous_decision_id",
    "related_decision_id",
    "route_decision_id",
    "decision_id",
    "next_decision_id",
    "child_decision_id",
)


@dataclass(frozen=True)
class RouteHistoryDecisionView:
    decision_id: str
    user_id: str
    decided_at: datetime
    decision_type: str
    decision_payload: dict[str, Any]
    input_aggregator_snapshot_id: str
    source_state_v2: dict[str, str]
    source_state_v2_key: str | None
    skills_injected: tuple[str, ...]
    idiographic_associations_injected: tuple[dict[str, Any], ...]
    outcome: str | None
    outcome_timestamp: datetime | None
    outcome_signal_id: str | None

    @classmethod
    def from_record(cls, record: RoutingDecisionLog) -> "RouteHistoryDecisionView":
        return cls(
            decision_id=str(record.decision_id),
            user_id=str(record.user_id),
            decided_at=record.decided_at,
            decision_type=str(record.decision_type or ""),
            decision_payload=dict(record.decision_payload or {}),
            input_aggregator_snapshot_id=str(record.input_aggregator_snapshot_id or ""),
            source_state_v2=dict(record.source_state_v2 or {}),
            source_state_v2_key=str(record.source_state_v2_key or "").strip() or None,
            skills_injected=tuple(str(item) for item in (record.skills_injected or [])),
            idiographic_associations_injected=tuple(
                item
                for item in (record.idiographic_associations_injected or [])
                if isinstance(item, dict)
            ),
            outcome=str(record.outcome or "").strip() or None,
            outcome_timestamp=record.outcome_timestamp,
            outcome_signal_id=str(record.outcome_signal_id or "").strip() or None,
        )


class RouteHistoryService:
    """Stage 20/25 route history collector with user-isolated read APIs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def read_recent_decisions(
        self,
        user_id: UUID,
        limit: int = 20,
        since: datetime | None = None,
        outcome_filter: str | None = None,
    ) -> list[RouteHistoryDecisionView]:
        normalized_user_id = self._require_user_id(user_id)
        clamped_limit = max(1, min(int(limit or 20), 100))

        stmt = select(RoutingDecisionLog).where(RoutingDecisionLog.user_id == normalized_user_id)
        if since is not None:
            stmt = stmt.where(RoutingDecisionLog.decided_at >= since)
        normalized_outcome = str(outcome_filter or "").strip()
        if normalized_outcome:
            stmt = stmt.where(RoutingDecisionLog.outcome == normalized_outcome)
        stmt = stmt.order_by(RoutingDecisionLog.decided_at.desc()).limit(clamped_limit)

        rows = (await self.db.execute(stmt)).scalars().all()
        return [RouteHistoryDecisionView.from_record(row) for row in rows]

    async def read_decision_chain(
        self,
        user_id: UUID,
        decision_id: UUID,
        depth: int = 3,
    ) -> list[RouteHistoryDecisionView]:
        normalized_user_id = self._require_user_id(user_id)
        record = await self._load_decision_for_user(normalized_user_id, decision_id)
        if record is None:
            return []

        clamped_depth = max(1, min(int(depth or 3), 10))
        visited: set[str] = {str(record.decision_id)}
        chain: list[RoutingDecisionLog] = [record]
        frontier: list[RoutingDecisionLog] = [record]

        for _ in range(clamped_depth):
            if not frontier:
                break
            next_frontier: list[RoutingDecisionLog] = []
            for current in frontier:
                neighbors = await self._load_related_decisions(
                    user_id=normalized_user_id,
                    anchor=current,
                )
                for neighbor in neighbors:
                    neighbor_id = str(neighbor.decision_id)
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    chain.append(neighbor)
                    next_frontier.append(neighbor)
            frontier = next_frontier

        chain.sort(key=lambda item: (item.decided_at, str(item.decision_id)))
        return [RouteHistoryDecisionView.from_record(row) for row in chain]

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
        idiographic_associations_injected: list[dict[str, Any]] | None = None,
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
            idiographic_associations_injected=[
                item
                for item in (idiographic_associations_injected or [])
                if isinstance(item, dict)
            ]
            or None,
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

    async def _load_decision_for_user(
        self,
        user_id: UUID,
        decision_id: UUID,
    ) -> RoutingDecisionLog | None:
        result = await self.db.execute(
            select(RoutingDecisionLog).where(
                RoutingDecisionLog.user_id == user_id,
                RoutingDecisionLog.decision_id == decision_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_related_decisions(
        self,
        *,
        user_id: UUID,
        anchor: RoutingDecisionLog,
    ) -> list[RoutingDecisionLog]:
        anchor_id = str(anchor.decision_id)
        payload = dict(anchor.decision_payload or {})
        candidate_ids = {
            str(payload.get(key) or "").strip()
            for key in DECISION_CHAIN_KEYS
            if str(payload.get(key) or "").strip()
        }
        stmt = (
            select(RoutingDecisionLog)
            .where(
                RoutingDecisionLog.user_id == user_id,
            )
            .order_by(RoutingDecisionLog.decided_at.desc())
            .limit(50)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        related: list[RoutingDecisionLog] = []
        for row in rows:
            row_id = str(row.decision_id)
            row_payload = dict(row.decision_payload or {})
            row_refs = {
                str(row_payload.get(key) or "").strip()
                for key in DECISION_CHAIN_KEYS
                if str(row_payload.get(key) or "").strip()
            }
            if row_id in candidate_ids:
                related.append(row)
                continue
            if anchor_id in row_refs:
                related.append(row)
                continue
            if anchor.outcome_signal_id and row.outcome_signal_id == anchor.outcome_signal_id:
                related.append(row)
        return related[:10]

    async def _update_learner(self, record: RoutingDecisionLog, *, outcome: str) -> None:
        route_execution_mode = str((record.decision_payload or {}).get("route_execution_mode") or "").strip()
        source_key = str(record.source_state_v2_key or "").strip()
        if not route_execution_mode or not source_key:
            return
        learner = PersistentBayesianLearner(cache_service.redis, user_id=str(record.user_id))
        await learner.update_for_state(source_key, route_execution_mode, outcome in SUCCESS_OUTCOMES)
        await learner.drain_pending_saves()

    @staticmethod
    def _looks_like_uuid(value: str) -> bool:
        try:
            UUID(value)
        except (TypeError, ValueError, AttributeError):
            return False
        return True

    @staticmethod
    def _require_user_id(user_id: UUID | None) -> UUID:
        if user_id is None:
            raise ValueError("RouteHistoryService read APIs require a non-empty user_id")
        if isinstance(user_id, UUID):
            return user_id
        normalized = str(user_id or "").strip()
        if not normalized:
            raise ValueError("RouteHistoryService read APIs require a non-empty user_id")
        try:
            return UUID(normalized)
        except ValueError as exc:
            raise ValueError("RouteHistoryService read APIs require a valid user_id") from exc
