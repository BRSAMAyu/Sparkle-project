"""Track whether AI interventions produce measurable learning outcomes."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import InterventionOutcomeRecorded, InterventionRecorded, event_bus
from app.models.base import _utcnow
from app.models.intervention_outcome import InterventionOutcome


def _coerce_uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _isoformat(value) -> str:
    return value.isoformat() if value is not None else ""


async def _publish_event(event) -> None:
    payload = event.to_dict() if hasattr(event, "to_dict") else event.__dict__.copy()
    await event_bus.publish(payload["event_type"], payload)


class InterventionOutcomeTracker:
    """
    追踪AI干预行为的效果。

    核心职责：
    1. record_intervention(): 干预发生时记录
    2. check_outcome(): 72h后检查是否有效
    3. get_effectiveness_summary(): 返回干预有效率统计

    不要直接调用adaptive_replanner，通过事件总线订阅触发。
    """

    async def record_intervention(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        intervention_type: str,
        trigger_reason: str,
        target_concept: str | None = None,
        target_node_id: str | None = None,
        plan_id: str | None = None,
        mastery_before: float | None = None,
    ) -> str:
        """记录一次AI干预"""
        now = _utcnow()
        outcome = InterventionOutcome(
            user_id=_coerce_uuid(user_id),
            intervention_type=intervention_type,
            trigger_reason=trigger_reason,
            target_concept=target_concept,
            target_node_id=_coerce_uuid(target_node_id),
            plan_id=_coerce_uuid(plan_id),
            mastery_before=mastery_before,
            triggered_at=now,
            follow_up_at=now + timedelta(hours=72),
            outcome_status="pending",
        )
        db.add(outcome)
        await db.commit()

        await _publish_event(
            InterventionRecorded(
                user_id=str(outcome.user_id),
                intervention_id=str(outcome.id),
                intervention_type=intervention_type,
                triggered_at=_isoformat(outcome.triggered_at),
            )
        )
        return str(outcome.id)

    async def check_outcome(
        self,
        db: AsyncSession,
        *,
        intervention_id: str,
        galaxy_service,
    ) -> dict | None:
        """
        检查干预效果。通常在TaskCompleted事件触发时调用。
        对比 mastery_before vs 当前mastery，判断是否改善。
        """
        intervention_uuid = _coerce_uuid(intervention_id)
        if intervention_uuid is None:
            return None

        result = await db.execute(
            select(InterventionOutcome)
            .where(
                InterventionOutcome.id == intervention_uuid,
                InterventionOutcome.outcome_status == "pending",
            )
            .with_for_update()
        )
        outcome = result.scalar_one_or_none()
        if not outcome:
            return None

        mastery_after = None
        if outcome.target_node_id:
            mastery_after = await galaxy_service.get_node_mastery(
                db,
                user_id=str(outcome.user_id),
                node_id=str(outcome.target_node_id),
            )

        if mastery_after is not None and outcome.mastery_before is not None:
            delta = mastery_after - outcome.mastery_before
            effective = delta > 5
            status = "improved" if effective else ("no_change" if delta >= -5 else "degraded")
        else:
            effective = None
            status = "not_checked"

        checked_at = _utcnow()
        update_result = await db.execute(
            update(InterventionOutcome)
            .where(
                InterventionOutcome.id == intervention_uuid,
                InterventionOutcome.outcome_status == "pending",
            )
            .values(
                mastery_after=mastery_after,
                effective=effective,
                outcome_status=status,
                outcome_checked_at=checked_at,
            )
        )
        if update_result.rowcount == 0:
            await db.rollback()
            return None

        await db.commit()

        await _publish_event(
            InterventionOutcomeRecorded(
                user_id=str(outcome.user_id),
                intervention_id=str(outcome.id),
                effective=effective,
                status=status,
                checked_at=_isoformat(checked_at),
            )
        )
        return {"intervention_id": str(outcome.id), "effective": effective, "status": status}

    async def get_effectiveness_summary(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        days: int = 30,
    ) -> dict:
        """
        返回：
        {
          "total_interventions": 12,
          "checked": 8,
          "effective_rate": 0.75,
          "by_type": {"replan": 0.8, "push_nudge": 0.6}
        }
        """
        since = _utcnow() - timedelta(days=days)
        result = await db.execute(
            select(InterventionOutcome).where(
                InterventionOutcome.user_id == _coerce_uuid(user_id),
                InterventionOutcome.triggered_at >= since,
            )
        )
        outcomes = list(result.scalars().all())
        checked = [outcome for outcome in outcomes if outcome.effective is not None]
        effective_count = sum(1 for outcome in checked if outcome.effective is True)

        by_type_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for outcome in checked:
            intervention_type = outcome.intervention_type or "unknown"
            by_type_counts[intervention_type][1] += 1
            if outcome.effective is True:
                by_type_counts[intervention_type][0] += 1

        return {
            "total_interventions": len(outcomes),
            "checked": len(checked),
            "effective_rate": effective_count / len(checked) if checked else 0.0,
            "by_type": {
                intervention_type: counts[0] / counts[1]
                for intervention_type, counts in by_type_counts.items()
                if counts[1] > 0
            },
        }

    async def check_pending_outcomes(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        galaxy_service,
    ) -> list[dict]:
        """由Celery定时任务调用，检查所有 follow_up_at <= now() 的待检干预"""
        now = _utcnow()
        result = await db.execute(
            select(InterventionOutcome.id)
            .where(
                InterventionOutcome.user_id == _coerce_uuid(user_id),
                InterventionOutcome.outcome_status == "pending",
                InterventionOutcome.follow_up_at <= now,
            )
            .order_by(InterventionOutcome.follow_up_at.asc())
        )
        intervention_ids = [str(intervention_id) for intervention_id in result.scalars().all()]

        checked: list[dict] = []
        for pending_id in intervention_ids:
            outcome = await self.check_outcome(db, intervention_id=pending_id, galaxy_service=galaxy_service)
            if outcome is not None:
                checked.append(outcome)
        return checked
