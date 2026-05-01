from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionTriggerType,
    OccurrenceStatus,
    TaskOccurrence,
)
from app.services.card_edge_service import CardEdgeService
from app.services.card_service import CardService
from app.services.intervention_record_service import InterventionRecordService
from app.services.task_occurrence_service import TaskOccurrenceService


@dataclass
class TimeWindow:
    start: str
    end: str


@dataclass
class RecurrenceRule:
    pattern: Literal["once", "daily", "weekly", "monthly", "custom"] = "once"
    days_of_week: list[int] | None = None
    day_of_month: int | None = None
    time_window: TimeWindow | None = None
    flexible: bool = True
    max_deferrals: int = 3
    end_condition: Literal["date", "count", "phase_end", "never"] = "phase_end"
    end_value: str | int | None = None
    interval_days: int | None = None


class TemporalEngine:
    """Manage recurrence rules and concrete TaskOccurrence generation."""

    DEFAULT_PHASE_WINDOW_DAYS = 28

    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)
        self.occurrence_service = TaskOccurrenceService(db, event_bus)
        self.intervention_service = InterventionRecordService(db, event_bus)

    async def set_task_recurrence(
        self,
        *,
        task_card_id: UUID,
        rule: RecurrenceRule,
        user_id: UUID,
    ) -> Card:
        task_card = await self._get_owned_task(task_card_id, user_id)
        temporal = dict((task_card.metadata_ or {}).get("temporal") or {})
        recurrence_payload = self._rule_to_payload(rule)
        temporal["recurrence"] = recurrence_payload
        metadata_patch = {
            "temporal": temporal,
            "recurrence_rule": recurrence_payload,
        }
        if rule.time_window:
            metadata_patch["scheduling_policy"] = {
                "time_window": asdict(rule.time_window),
                "flexible": rule.flexible,
            }
        updated = await self.card_service.update_card(
            task_card_id,
            metadata=metadata_patch,
        )
        if updated is None:
            raise ValueError("Task card not found")
        return updated

    async def generate_occurrences(
        self,
        *,
        task_card_id: UUID,
        phase_card_id: UUID,
        from_date: date,
        to_date: date,
    ) -> list[TaskOccurrence]:
        if to_date < from_date:
            raise ValueError("to_date must be on or after from_date")

        task_card = await self.card_service.get_card(task_card_id)
        if not task_card or task_card.card_type != CardType.TASK:
            raise ValueError("Task card not found")

        phase_card = await self.card_service.get_card(phase_card_id)
        if not phase_card or phase_card.card_type != CardType.PHASE:
            raise ValueError("Phase card not found")

        plan_card = await self._get_phase_parent_plan(phase_card_id)
        if not plan_card:
            raise ValueError("Phase must belong to a plan")

        rule = self._read_rule(task_card)
        target_dates = self._expand_dates(task_card, rule, from_date, to_date, phase_card=phase_card)
        if not target_dates:
            return []

        existing_stmt = select(TaskOccurrence).where(
            TaskOccurrence.series_card_id == task_card_id,
            TaskOccurrence.phase_card_id == phase_card_id,
            TaskOccurrence.scheduled_for.in_(target_dates),
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_dates = {
            occurrence.scheduled_for
            for occurrence in existing_result.scalars().all()
            if occurrence.scheduled_for is not None
        }

        created: list[TaskOccurrence] = []
        rule_hash = self._rule_hash(rule)
        for scheduled_day in target_dates:
            if scheduled_day in existing_dates:
                continue
            window_start, window_end = self._build_window(scheduled_day, rule.time_window)
            occurrence = await self.occurrence_service.create_occurrence(
                series_card_id=task_card_id,
                plan_card_id=plan_card.id,
                phase_card_id=phase_card_id,
                scheduled_for=scheduled_day,
                window_start=window_start,
                window_end=window_end,
                status=OccurrenceStatus.PLANNED,
                generated_by_rule_hash=rule_hash,
            )
            created.append(occurrence)
        return created

    async def defer_occurrence(
        self,
        *,
        occurrence_id: UUID,
        user_id: UUID,
        new_date: date | None = None,
    ) -> TaskOccurrence:
        occurrence = await self.occurrence_service.get_occurrence(occurrence_id)
        if not occurrence:
            raise ValueError("Occurrence not found")

        task_card = await self.card_service.get_card(occurrence.series_card_id)
        if not task_card or task_card.holder_id != user_id:
            raise ValueError("Occurrence not found")

        rule = self._read_rule(task_card)
        target_date = new_date or self._auto_reschedule_date(occurrence, rule)
        updated = await self.occurrence_service.defer(
            occurrence_id,
            new_date=target_date,
        )
        if updated is None:
            raise ValueError("Occurrence not found")

        if updated.deferral_count >= rule.max_deferrals:
            await self.intervention_service.create_record(
                user_id=user_id,
                trigger_type=InterventionTriggerType.STALL_PATTERN,
                delivery_strategy=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.IN_APP,
                plan_card_id=updated.plan_card_id,
                phase_card_id=updated.phase_card_id,
                task_occurrence_id=updated.id,
                diagnosis_payload={
                    "reason": "occurrence_deferral_limit_reached",
                    "deferral_count": updated.deferral_count,
                    "max_deferrals": rule.max_deferrals,
                    "scheduled_for": updated.scheduled_for.isoformat()
                    if updated.scheduled_for
                    else None,
                },
                outcome_window_days=3,
            )
        return updated

    async def regenerate_phase_schedule(
        self,
        *,
        phase_card_id: UUID,
        from_date: date | None = None,
    ) -> dict[str, Any]:
        phase_card = await self.card_service.get_card(phase_card_id)
        if not phase_card or phase_card.card_type != CardType.PHASE:
            raise ValueError("Phase not found")

        range_start, range_end = self._resolve_phase_window(phase_card, from_date=from_date)
        tasks = await self._get_phase_tasks(phase_card_id)
        task_ids = [task.id for task in tasks]
        if not task_ids:
            return {"cancelled_count": 0, "generated_count": 0}

        cancel_stmt = select(TaskOccurrence).where(
            TaskOccurrence.phase_card_id == phase_card_id,
            TaskOccurrence.series_card_id.in_(task_ids),
            TaskOccurrence.occurrence_status.in_(
                [
                    OccurrenceStatus.PLANNED,
                    OccurrenceStatus.READY,
                    OccurrenceStatus.DEFERRED,
                ]
            ),
            TaskOccurrence.scheduled_for >= range_start,
        )
        cancel_result = await self.db.execute(cancel_stmt)
        cancelled_count = 0
        for occurrence in cancel_result.scalars().all():
            await self.occurrence_service.cancel(occurrence.id)
            occurrence.plan_card_id = None
            occurrence.phase_card_id = None
            cancelled_count += 1

        generated_count = 0
        for task in tasks:
            generated = await self.generate_occurrences(
                task_card_id=task.id,
                phase_card_id=phase_card_id,
                from_date=range_start,
                to_date=range_end,
            )
            generated_count += len(generated)

        return {
            "cancelled_count": cancelled_count,
            "generated_count": generated_count,
            "from_date": range_start.isoformat(),
            "to_date": range_end.isoformat(),
        }

    def _read_rule(self, task_card: Card) -> RecurrenceRule:
        metadata = dict(task_card.metadata_ or {})
        temporal = dict(metadata.get("temporal") or {})
        recurrence = temporal.get("recurrence") or metadata.get("recurrence_rule") or {}
        time_window_payload = recurrence.get("time_window") or (metadata.get("scheduling_policy") or {}).get("time_window")
        time_window = None
        if time_window_payload and time_window_payload.get("start") and time_window_payload.get("end"):
            time_window = TimeWindow(
                start=str(time_window_payload["start"]),
                end=str(time_window_payload["end"]),
            )
        return RecurrenceRule(
            pattern=str(recurrence.get("pattern") or "once"),
            days_of_week=list(recurrence.get("days_of_week") or []) or None,
            day_of_month=recurrence.get("day_of_month"),
            time_window=time_window,
            flexible=bool(recurrence.get("flexible", True)),
            max_deferrals=int(recurrence.get("max_deferrals") or 3),
            end_condition=str(recurrence.get("end_condition") or "phase_end"),
            end_value=recurrence.get("end_value"),
            interval_days=recurrence.get("interval_days"),
        )

    def _rule_to_payload(self, rule: RecurrenceRule) -> dict[str, Any]:
        payload = asdict(rule)
        if rule.time_window is not None:
            payload["time_window"] = asdict(rule.time_window)
        return payload

    def _rule_hash(self, rule: RecurrenceRule) -> str:
        normalized = json.dumps(self._rule_to_payload(rule), sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _expand_dates(
        self,
        task_card: Card,
        rule: RecurrenceRule,
        from_date: date,
        to_date: date,
        *,
        phase_card: Card,
    ) -> list[date]:
        pattern = rule.pattern.lower()
        if pattern == "once":
            due_payload = (task_card.metadata_ or {}).get("due_date")
            target = self._coerce_date(due_payload) or from_date
            return [target] if from_date <= target <= to_date else []

        results: list[date] = []
        current = from_date
        limit = int(rule.end_value) if rule.end_condition == "count" and rule.end_value is not None else None
        hard_end = self._coerce_date(rule.end_value) if rule.end_condition == "date" else None
        phase_end = self._coerce_date((phase_card.metadata_ or {}).get("estimated_end"))
        effective_end = min(
            [candidate for candidate in [to_date, hard_end, phase_end] if candidate is not None]
        ) if any(candidate is not None for candidate in [to_date, hard_end, phase_end]) else to_date

        while current <= effective_end:
            if pattern == "daily":
                results.append(current)
            elif pattern == "weekly":
                valid_days = set(rule.days_of_week or [current.isoweekday()])
                if current.isoweekday() in valid_days:
                    results.append(current)
            elif pattern == "monthly":
                target_dom = rule.day_of_month or from_date.day
                last_day = calendar.monthrange(current.year, current.month)[1]
                effective_dom = min(target_dom, last_day)
                if current.day == effective_dom:
                    results.append(current)
            elif pattern == "custom":
                interval = max(1, int(rule.interval_days or 2))
                delta = (current - from_date).days
                if delta % interval == 0:
                    results.append(current)

            if limit is not None and len(results) >= limit:
                break
            current += timedelta(days=1)

        return results

    def _build_window(
        self,
        scheduled_day: date,
        window: TimeWindow | None,
    ) -> tuple[datetime | None, datetime | None]:
        if window is None:
            return None, None
        start_time = self._parse_clock(window.start)
        end_time = self._parse_clock(window.end)
        return (
            datetime.combine(scheduled_day, start_time),
            datetime.combine(scheduled_day, end_time),
        )

    def _parse_clock(self, value: str) -> time:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.time()

    def _coerce_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    async def _get_owned_task(self, task_card_id: UUID, user_id: UUID) -> Card:
        task_card = await self.card_service.get_card(task_card_id)
        if not task_card or task_card.card_type != CardType.TASK or task_card.holder_id != user_id:
            raise ValueError("Task card not found")
        return task_card

    async def _get_phase_parent_plan(self, phase_card_id: UUID) -> Card | None:
        parents = await self.edge_service.get_parents(
            phase_card_id,
            edge_type=None,
            active_only=True,
        )
        for _, parent in parents:
            if parent.card_type == CardType.PLAN:
                return parent
        return None

    async def _get_phase_tasks(self, phase_card_id: UUID) -> list[Card]:
        children = await self.edge_service.get_children(
            phase_card_id,
            active_only=True,
        )
        return [child for _, child in children if child.card_type == CardType.TASK]

    def _resolve_phase_window(
        self,
        phase_card: Card,
        *,
        from_date: date | None = None,
    ) -> tuple[date, date]:
        metadata = dict(phase_card.metadata_ or {})
        start = from_date or self._coerce_date(metadata.get("estimated_start")) or date.today()
        end = self._coerce_date(metadata.get("estimated_end")) or (start + timedelta(days=self.DEFAULT_PHASE_WINDOW_DAYS))
        if end < start:
            end = start
        return start, end

    def _auto_reschedule_date(self, occurrence: TaskOccurrence, rule: RecurrenceRule) -> date:
        current = occurrence.scheduled_for or date.today()
        if rule.pattern == "weekly":
            return current + timedelta(days=7)
        if rule.pattern == "monthly":
            return current + timedelta(days=30)
        if rule.pattern == "custom":
            return current + timedelta(days=max(1, int(rule.interval_days or 2)))
        return current + timedelta(days=1)
