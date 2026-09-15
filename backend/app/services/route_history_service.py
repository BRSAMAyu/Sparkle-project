from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
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
    def from_record(cls, record: RoutingDecisionLog) -> RouteHistoryDecisionView:
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

    async def record_task_abandonment(
        self,
        *,
        decision_id: UUID,
        outcome_signal_id: str,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        """Record a task abandonment as a concrete negative routing outcome."""
        return await self._record_outcome(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id,
            outcome="user_correction",
            legacy_outcome_type="task_abandoned",
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

    async def record_task_completion_for_event(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        plan_id: UUID | None = None,
        route_history_decision_id: UUID | str | None = None,
        routing_outcome_signal_id: UUID | str | None = None,
        routing_trace_id: str | None = None,
        outcome_signal_id: str | None = None,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        decision_id = await self._resolve_task_event_decision_id(
            user_id=user_id,
            task_id=task_id,
            plan_id=plan_id,
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
            collected_at=collected_at,
            outcome_kind="task_completion",
        )
        if decision_id is None:
            return None
        return await self.record_task_completion(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id or f"task.completed:{task_id}",
            collected_at=collected_at,
        )

    async def record_task_abandonment_for_event(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        plan_id: UUID | None = None,
        route_history_decision_id: UUID | str | None = None,
        routing_outcome_signal_id: UUID | str | None = None,
        routing_trace_id: str | None = None,
        outcome_signal_id: str | None = None,
        collected_at: datetime | None = None,
    ) -> RoutingDecisionLog | None:
        decision_id = await self._resolve_task_event_decision_id(
            user_id=user_id,
            task_id=task_id,
            plan_id=plan_id,
            route_history_decision_id=route_history_decision_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
            routing_trace_id=routing_trace_id,
            collected_at=collected_at,
            outcome_kind="task_abandonment",
        )
        if decision_id is None:
            return None
        return await self.record_task_abandonment(
            decision_id=decision_id,
            outcome_signal_id=outcome_signal_id or f"task.abandoned:{task_id}",
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
        await self._sync_self_model(record=record, outcome=outcome, outcome_signal_id=outcome_signal_id)
        latency = max(0.0, (outcome_at - record.decided_at).total_seconds())
        ROUTING_OUTCOME_BACKFILL_LATENCY.labels(outcome=outcome).observe(latency)
        await self._update_learner(record, outcome=outcome)
        return record

    async def _resolve_task_event_decision_id(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        plan_id: UUID | None,
        route_history_decision_id: UUID | str | None,
        routing_outcome_signal_id: UUID | str | None,
        routing_trace_id: str | None,
        collected_at: datetime | None,
        outcome_kind: str,
    ) -> UUID | None:
        normalized_user_id = self._require_user_id(user_id)
        explicit = self._coerce_uuid(route_history_decision_id)
        if explicit is not None:
            record = await self._load_decision_for_user(normalized_user_id, explicit)
            if record is not None and record.outcome is None:
                return explicit
            if record is not None:
                logger.debug("Route history decision {} already has outcome {}; skipping", explicit, record.outcome)
                return None

        signal_decision_id = await self._decision_id_from_passive_signal(
            user_id=normalized_user_id,
            routing_outcome_signal_id=routing_outcome_signal_id,
        )
        if signal_decision_id is not None:
            return signal_decision_id

        return await self._find_recent_unresolved_task_decision(
            user_id=normalized_user_id,
            task_id=task_id,
            plan_id=plan_id,
            routing_trace_id=routing_trace_id,
            collected_at=collected_at or _utcnow(),
            outcome_kind=outcome_kind,
        )

    async def _decision_id_from_passive_signal(
        self,
        *,
        user_id: UUID,
        routing_outcome_signal_id: UUID | str | None,
    ) -> UUID | None:
        signal_uuid = self._coerce_uuid(routing_outcome_signal_id)
        if signal_uuid is None:
            return None
        try:
            from app.models.intervention_adaptive import PassiveSignal

            signal = (
                await self.db.execute(
                    select(PassiveSignal).where(
                        PassiveSignal.id == signal_uuid,
                        PassiveSignal.user_id == user_id,
                        PassiveSignal.signal_type == "routing_decision",
                    )
                )
            ).scalar_one_or_none()
            if signal is None:
                return None
            context = dict(signal.context or {})
            decision_id = self._coerce_uuid(context.get("route_history_decision_id"))
            if decision_id is None:
                return None
            record = await self._load_decision_for_user(user_id, decision_id)
            if record is not None and record.outcome is None:
                return decision_id
        except Exception as exc:
            logger.debug("Failed to resolve passive routing signal {}: {}", routing_outcome_signal_id, exc)
        return None

    async def _find_recent_unresolved_task_decision(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        plan_id: UUID | None,
        routing_trace_id: str | None,
        collected_at: datetime,
        outcome_kind: str,
    ) -> UUID | None:
        lookback_start = collected_at - timedelta(hours=8)
        rows = list(
            (
                await self.db.execute(
                    select(RoutingDecisionLog)
                    .where(
                        RoutingDecisionLog.user_id == user_id,
                        RoutingDecisionLog.outcome.is_(None),
                        RoutingDecisionLog.decided_at <= collected_at,
                        RoutingDecisionLog.decided_at >= lookback_start,
                    )
                    .order_by(RoutingDecisionLog.decided_at.desc())
                    .limit(30)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return None

        scored: list[tuple[float, RoutingDecisionLog]] = []
        for row in rows:
            score = self._score_task_outcome_candidate(
                row=row,
                task_id=task_id,
                plan_id=plan_id,
                routing_trace_id=routing_trace_id,
                collected_at=collected_at,
                outcome_kind=outcome_kind,
            )
            if score > 0:
                scored.append((score, row))
        if not scored:
            return None

        scored.sort(key=lambda item: (item[0], item[1].decided_at), reverse=True)
        best_score, best = scored[0]
        if best_score < 20.0:
            logger.debug(
                "Route history task outcome fallback skipped for task {}: weak best score {}",
                task_id,
                best_score,
            )
            return None
        if len(scored) > 1:
            second_score = scored[1][0]
            if best_score - second_score < 2.0 and best_score < 60.0:
                logger.debug(
                    "Route history task outcome fallback ambiguous for task {}: best={} second={}",
                    task_id,
                    best_score,
                    second_score,
                )
                return None
        return UUID(str(best.decision_id))

    @classmethod
    def _score_task_outcome_candidate(
        cls,
        *,
        row: RoutingDecisionLog,
        task_id: UUID,
        plan_id: UUID | None,
        routing_trace_id: str | None,
        collected_at: datetime,
        outcome_kind: str,
    ) -> float:
        payload = dict(row.decision_payload or {})
        source_state = dict(row.source_state_v2 or {})
        haystack = cls._json_text({"payload": payload, "source_state": source_state})
        score = 0.0

        if routing_trace_id and routing_trace_id in haystack:
            score += 100.0
        if str(task_id) in haystack:
            score += 80.0
        if plan_id is not None and str(plan_id) in haystack:
            score += 35.0

        minutes_old = max(0.0, (collected_at - row.decided_at).total_seconds() / 60.0)
        if minutes_old <= 90:
            score += max(0.0, 18.0 - (minutes_old / 10.0))
        elif score < 35.0:
            return 0.0

        mode = str(payload.get("mode") or row.decision_type or "").strip()
        route_execution_mode = str(payload.get("route_execution_mode") or "").strip()
        if outcome_kind == "task_completion":
            if mode == "execution_first":
                score += 8.0
            elif mode == "balanced":
                score += 5.0
            elif mode == "cognitive_first":
                score += 3.0
            if route_execution_mode in {"direct", "langgraph", "hybrid"}:
                score += 4.0
        else:
            if mode == "execution_first":
                score += 9.0
            elif mode == "balanced":
                score += 6.0
            elif mode == "cognitive_first":
                score += 4.0
        return score

    @staticmethod
    def _json_text(value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except TypeError:
            return str(value)

    @staticmethod
    def _coerce_uuid(value: UUID | str | None) -> UUID | None:
        if isinstance(value, UUID):
            return value
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return UUID(raw)
        except (TypeError, ValueError, AttributeError):
            return None

    async def _sync_self_model(
        self,
        *,
        record: RoutingDecisionLog,
        outcome: str,
        outcome_signal_id: str,
    ) -> None:
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService

            service = SparkleSelfModelService(cache_service.redis)
            signal_id = f"route_history:{outcome}:{record.decision_id}:{outcome_signal_id}"
            if outcome == "user_correction":
                await service.record_user_correction(
                    user_id=str(record.user_id),
                    signal_id=signal_id,
                    reason=f"route_history:{outcome_signal_id}",
                    source="route_history",
                )
            elif outcome == "timeout":
                await service.record_task_outcome(
                    user_id=str(record.user_id),
                    signal_id=signal_id,
                    completed=False,
                    timed_out=True,
                    source="route_history",
                    reason="strategy_timeout",
                )
            elif outcome == "task_completion":
                await service.record_task_outcome(
                    user_id=str(record.user_id),
                    signal_id=signal_id,
                    completed=True,
                    timed_out=False,
                    source="route_history",
                    reason="strategy_completed",
                )
        except Exception as exc:
            logger.warning("Failed to sync Aurora self model from route history {}: {}", record.decision_id, exc)

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
