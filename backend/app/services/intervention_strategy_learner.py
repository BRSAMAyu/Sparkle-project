"""Learns which intervention strategies work for each user and trigger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome


@dataclass
class ResponseProfile:
    user_id: UUID
    total_samples: int
    preferred_strategy: DeliveryStrategy | None
    preferred_channel: DeliveryChannel | None
    acted_rate_by_strategy: dict[str, float]
    effective_rate_by_strategy: dict[str, float]


class InterventionStrategyLearner:
    """Persists intervention outcomes and recommends the best next tone."""

    MIN_PERSONALIZED_SAMPLES = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_outcome(
        self,
        *,
        user_id: UUID,
        intervention_id: UUID,
        outcome_status: InterventionOutcomeStatus,
        context_snapshot: dict[str, Any] | None = None,
    ) -> InterventionStrategyOutcome | None:
        record = await self.db.get(InterventionRecord, intervention_id)
        if record is None or record.user_id != user_id or record.trigger_type is None:
            return None

        existing_stmt = select(InterventionStrategyOutcome).where(
            InterventionStrategyOutcome.intervention_id == intervention_id,
            InterventionStrategyOutcome.not_deleted_filter(),
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()

        payload = self._build_context_snapshot(record, context_snapshot)
        if existing:
            existing.acceptance_status = record.acceptance_status
            existing.outcome = outcome_status
            existing.time_to_action_seconds = self._compute_time_to_action_seconds(record)
            existing.context_snapshot = payload
            await self.db.flush()
            return existing

        strategy_outcome = InterventionStrategyOutcome(
            user_id=user_id,
            intervention_id=intervention_id,
            trigger_type=record.trigger_type,
            delivery_tone=record.delivery_strategy,
            delivery_channel=record.delivery_channel,
            acceptance_status=record.acceptance_status,
            outcome=outcome_status,
            time_to_action_seconds=self._compute_time_to_action_seconds(record),
            context_snapshot=payload,
        )
        self.db.add(strategy_outcome)
        await self.db.flush()
        return strategy_outcome

    async def get_best_strategy(
        self,
        user_id: UUID,
        trigger_type: InterventionTriggerType,
    ) -> DeliveryStrategy | None:
        outcomes = await self._load_outcomes(user_id=user_id, trigger_type=trigger_type)
        if len(outcomes) < self.MIN_PERSONALIZED_SAMPLES:
            return None

        best_strategy: DeliveryStrategy | None = None
        best_score: tuple[float, float, float, int] | None = None
        for strategy, group in self._group_by_strategy(outcomes).items():
            total = len(group)
            acted = sum(1 for item in group if item.acceptance_status == InterventionAcceptanceStatus.ACTED)
            effective = sum(1 for item in group if item.outcome == InterventionOutcomeStatus.EFFECTIVE)
            with_time = [item.time_to_action_seconds for item in group if item.time_to_action_seconds is not None]
            avg_time = sum(with_time) / len(with_time) if with_time else float("inf")
            score = (
                acted / total if total else 0.0,
                effective / total if total else 0.0,
                -avg_time,
                total,
            )
            if best_score is None or score > best_score:
                best_strategy = strategy
                best_score = score
        return best_strategy

    async def get_user_response_profile(self, user_id: UUID) -> ResponseProfile:
        stmt = select(InterventionStrategyOutcome).where(
            InterventionStrategyOutcome.user_id == user_id,
            InterventionStrategyOutcome.not_deleted_filter(),
        )
        outcomes = list((await self.db.execute(stmt)).scalars().all())

        acted_rate_by_strategy: dict[str, float] = {}
        effective_rate_by_strategy: dict[str, float] = {}
        preferred_strategy: DeliveryStrategy | None = None
        preferred_channel: DeliveryChannel | None = None

        if outcomes:
            grouped = self._group_by_strategy(outcomes)
            ranked: list[tuple[DeliveryStrategy, float, int]] = []
            for strategy, group in grouped.items():
                total = len(group)
                acted = sum(1 for item in group if item.acceptance_status == InterventionAcceptanceStatus.ACTED)
                effective = sum(1 for item in group if item.outcome == InterventionOutcomeStatus.EFFECTIVE)
                acted_rate = acted / total if total else 0.0
                effective_rate = effective / total if total else 0.0
                acted_rate_by_strategy[strategy.value] = acted_rate
                effective_rate_by_strategy[strategy.value] = effective_rate
                ranked.append((strategy, acted_rate + effective_rate, total))

            ranked.sort(key=lambda item: (item[1], item[2]), reverse=True)
            preferred_strategy = ranked[0][0]

            if preferred_strategy is not None:
                channel_counts: dict[DeliveryChannel, int] = {}
                for item in grouped.get(preferred_strategy, []):
                    channel_counts[item.delivery_channel] = channel_counts.get(item.delivery_channel, 0) + 1
                if channel_counts:
                    preferred_channel = max(channel_counts.items(), key=lambda item: item[1])[0]

        return ResponseProfile(
            user_id=user_id,
            total_samples=len(outcomes),
            preferred_strategy=preferred_strategy,
            preferred_channel=preferred_channel,
            acted_rate_by_strategy=acted_rate_by_strategy,
            effective_rate_by_strategy=effective_rate_by_strategy,
        )

    async def _load_outcomes(
        self,
        *,
        user_id: UUID,
        trigger_type: InterventionTriggerType,
    ) -> list[InterventionStrategyOutcome]:
        stmt = select(InterventionStrategyOutcome).where(
            InterventionStrategyOutcome.user_id == user_id,
            InterventionStrategyOutcome.trigger_type == trigger_type,
            InterventionStrategyOutcome.not_deleted_filter(),
        )
        return list((await self.db.execute(stmt)).scalars().all())

    @staticmethod
    def _group_by_strategy(
        outcomes: list[InterventionStrategyOutcome],
    ) -> dict[DeliveryStrategy, list[InterventionStrategyOutcome]]:
        grouped: dict[DeliveryStrategy, list[InterventionStrategyOutcome]] = {}
        for outcome in outcomes:
            grouped.setdefault(outcome.delivery_tone, []).append(outcome)
        return grouped

    @staticmethod
    def _build_context_snapshot(
        record: InterventionRecord,
        override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if override:
            return dict(override)

        evidence = dict(record.evidence_payload or {})
        diagnosis = dict(record.diagnosis_payload or {})
        improvement = dict(evidence.get("improvement") or {})
        context = dict(diagnosis.get("context") or {})
        return {
            "trigger_type": record.trigger_type.value if record.trigger_type else None,
            "delivery_channel": record.delivery_channel.value if record.delivery_channel else None,
            "delivery_strategy": record.delivery_strategy.value if record.delivery_strategy else None,
            "plan_health_recovered": improvement.get("plan_health_recovered"),
            "mastery_improved": improvement.get("mastery_improved"),
            "parameter_strategy_effective": improvement.get("parameter_strategy_effective"),
            "completed_count": context.get("completed_count"),
            "evaluation_method": evidence.get("evaluation_method"),
        }

    @staticmethod
    def _compute_time_to_action_seconds(record: InterventionRecord) -> int | None:
        if record.acceptance_status != InterventionAcceptanceStatus.ACTED:
            return None

        acted_at = dict(record.action_payload or {}).get("acted_at")
        if not acted_at or not record.created_at:
            return None

        try:
            acted_time = datetime.fromisoformat(str(acted_at).replace("Z", "+00:00"))
        except ValueError:
            return None

        if acted_time.tzinfo is not None:
            acted_time = acted_time.replace(tzinfo=None)

        created_at = record.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)

        return max(0, int((acted_time - created_at).total_seconds()))
