"""
TaskOccurrenceService — Concrete execution instance management.

TaskOccurrence is NOT a card. Provenance lives on the occurrence record itself
via series_card_id, plan_card_id, phase_card_id, and generated_by_rule_hash.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.card_protocol import (
    OccurrenceStatus,
    TaskOccurrence,
)


class TaskOccurrenceService:
    """Service for TaskOccurrence CRUD and scheduling."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_occurrence(
        self,
        *,
        series_card_id: uuid.UUID,
        plan_card_id: uuid.UUID | None = None,
        phase_card_id: uuid.UUID | None = None,
        scheduled_for: date | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        status: OccurrenceStatus = OccurrenceStatus.PLANNED,
        generated_by_rule_hash: str = "",
    ) -> TaskOccurrence:
        occ = TaskOccurrence(
            series_card_id=series_card_id,
            plan_card_id=plan_card_id,
            phase_card_id=phase_card_id,
            scheduled_for=scheduled_for,
            window_start=window_start,
            window_end=window_end,
            occurrence_status=status,
            generated_by_rule_hash=generated_by_rule_hash,
        )
        self.db.add(occ)
        await self.db.flush()
        return occ

    async def create_batch(
        self,
        occurrences: list[dict],
    ) -> list[TaskOccurrence]:
        """Create multiple occurrences in bulk (for scheduling)."""
        objs = []
        for occ_data in occurrences:
            occ = TaskOccurrence(**occ_data)
            self.db.add(occ)
            objs.append(occ)
        await self.db.flush()
        return objs

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_occurrence(self, occurrence_id: uuid.UUID) -> TaskOccurrence | None:
        stmt = select(TaskOccurrence).where(TaskOccurrence.id == occurrence_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_occurrences_for_date(
        self,
        user_id: uuid.UUID,
        target_date: date,
        status: OccurrenceStatus | None = None,
    ) -> list[TaskOccurrence]:
        """Get all occurrences for a user on a specific date."""
        from app.models.card_protocol import Card

        stmt = (
            select(TaskOccurrence)
            .join(Card, Card.id == TaskOccurrence.series_card_id)
            .where(
                Card.holder_id == user_id,
                TaskOccurrence.scheduled_for == target_date,
                Card.not_deleted_filter(),
            )
        )
        if status:
            stmt = stmt.where(TaskOccurrence.occurrence_status == status)
        stmt = stmt.order_by(TaskOccurrence.window_start)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_upcoming(
        self,
        series_card_id: uuid.UUID,
        limit: int = 14,
    ) -> list[TaskOccurrence]:
        """Get upcoming occurrences for a task series."""
        stmt = (
            select(TaskOccurrence)
            .where(
                TaskOccurrence.series_card_id == series_card_id,
                TaskOccurrence.scheduled_for >= date.today(),
                TaskOccurrence.occurrence_status.in_([
                    OccurrenceStatus.PLANNED,
                    OccurrenceStatus.READY,
                ]),
            )
            .order_by(TaskOccurrence.scheduled_for)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    async def mark_ready(self, occurrence_id: uuid.UUID) -> TaskOccurrence | None:
        return await self._transition(occurrence_id, OccurrenceStatus.READY)

    async def start(self, occurrence_id: uuid.UUID) -> TaskOccurrence | None:
        return await self._transition(occurrence_id, OccurrenceStatus.IN_PROGRESS)

    async def complete(
        self,
        occurrence_id: uuid.UUID,
        *,
        actual_minutes: int | None = None,
        completion_quality: int | None = None,
        feedback_payload: dict | None = None,
    ) -> TaskOccurrence | None:
        occ = await self.get_occurrence(occurrence_id)
        if not occ:
            return None
        old_status = occ.occurrence_status
        occ.occurrence_status = OccurrenceStatus.COMPLETED
        occ.actual_minutes = actual_minutes
        occ.completion_quality = completion_quality
        occ.feedback_payload = feedback_payload
        occ.completed_at = datetime.utcnow()
        await self.db.flush()

        if self.event_bus:
            await self._publish_status_changed(occ, old_status=old_status)
            await self.event_bus.publish(
                "occurrence.completed",
                {
                    "occurrence_id": str(occ.id),
                    "series_card_id": str(occ.series_card_id),
                    "actual_minutes": actual_minutes,
                    "completion_quality": completion_quality,
                },
            )
        return occ

    async def miss(self, occurrence_id: uuid.UUID) -> TaskOccurrence | None:
        return await self._transition(occurrence_id, OccurrenceStatus.MISSED)

    async def defer(self, occurrence_id: uuid.UUID, *, new_date: date | None = None) -> TaskOccurrence | None:
        occ = await self.get_occurrence(occurrence_id)
        if not occ:
            return None
        old_status = occ.occurrence_status
        occ.occurrence_status = OccurrenceStatus.DEFERRED
        occ.deferral_count += 1
        if new_date:
            occ.scheduled_for = new_date
        await self.db.flush()

        if self.event_bus:
            await self._publish_status_changed(
                occ,
                old_status=old_status,
                extra_payload={
                    "deferral_count": occ.deferral_count,
                    "scheduled_for": occ.scheduled_for.isoformat() if occ.scheduled_for else None,
                },
            )
        return occ

    async def cancel(self, occurrence_id: uuid.UUID) -> TaskOccurrence | None:
        return await self._transition(occurrence_id, OccurrenceStatus.CANCELLED)

    async def _transition(self, occurrence_id: uuid.UUID, target: OccurrenceStatus) -> TaskOccurrence | None:
        occ = await self.get_occurrence(occurrence_id)
        if not occ:
            return None
        old_status = occ.occurrence_status
        if old_status == target:
            return occ
        occ.occurrence_status = target
        await self.db.flush()

        if self.event_bus:
            await self._publish_status_changed(occ, old_status=old_status)
        return occ

    async def _publish_status_changed(
        self,
        occurrence: TaskOccurrence,
        *,
        old_status: OccurrenceStatus,
        extra_payload: dict | None = None,
    ) -> None:
        if not self.event_bus:
            return

        payload = {
            "occurrence_id": str(occurrence.id),
            "series_card_id": str(occurrence.series_card_id),
            "old_status": old_status.value,
            "new_status": occurrence.occurrence_status.value,
        }
        if extra_payload:
            payload.update(extra_payload)

        await self.event_bus.publish("occurrence.status_changed", payload)

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def auto_transition_ready(self, reference_date: date | None = None) -> int:
        """Transition PLANNED occurrences to READY when within execution window.

        Returns count of transitions.
        """
        ref = reference_date or date.today()
        now = datetime.utcnow()

        stmt = (
            update(TaskOccurrence)
            .where(
                TaskOccurrence.occurrence_status == OccurrenceStatus.PLANNED,
                TaskOccurrence.scheduled_for <= ref,
                TaskOccurrence.window_start <= now,
            )
            .values(occurrence_status=OccurrenceStatus.READY)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def auto_mark_missed(self, reference_date: date | None = None) -> int:
        """Mark PLANNED/READY occurrences as MISSED when past their window.

        Returns count of transitions.
        """
        reference_date or date.today()
        now = datetime.utcnow()

        stmt = (
            update(TaskOccurrence)
            .where(
                TaskOccurrence.occurrence_status.in_([
                    OccurrenceStatus.PLANNED,
                    OccurrenceStatus.READY,
                ]),
                TaskOccurrence.window_end < now,
            )
            .values(occurrence_status=OccurrenceStatus.MISSED)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_completion_stats(
        self,
        series_card_id: uuid.UUID,
        days: int = 30,
    ) -> dict:
        """Get completion statistics for a task series over N days."""
        cutoff = date.today() - timedelta(days=days)

        stmt = (
            select(
                TaskOccurrence.occurrence_status,
                func.count(TaskOccurrence.id),
                func.avg(TaskOccurrence.actual_minutes),
                func.avg(TaskOccurrence.completion_quality),
            )
            .where(
                TaskOccurrence.series_card_id == series_card_id,
                TaskOccurrence.scheduled_for >= cutoff,
            )
            .group_by(TaskOccurrence.occurrence_status)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        stats = {}
        for status, count, avg_min, avg_quality in rows:
            stats[status.value] = {
                "count": count,
                "avg_actual_minutes": float(avg_min) if avg_min else None,
                "avg_quality": float(avg_quality) if avg_quality else None,
            }
        return stats
