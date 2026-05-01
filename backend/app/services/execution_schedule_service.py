"""Scheduling service for recurring or conditional OpenClaw executions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.models.execution_schedule import ExecutionSchedule, ExecutionScheduleTriggerType
from app.services.openclaw.url_guard import SSRFBlocked, validate_external_url


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class ExecutionScheduleDispatchResult:
    schedule_id: str
    intent_id: str | None
    status: str
    detail: str | None = None


class ExecutionScheduleService:
    """Persist and dispatch scheduled execution templates."""

    def __init__(self, db: AsyncSession, redis=None):
        self._db = db
        self._redis = redis

    async def list_schedules(self, *, user_id: UUID) -> list[ExecutionSchedule]:
        result = await self._db.execute(
            select(ExecutionSchedule)
            .where(
                ExecutionSchedule.user_id == user_id,
                ExecutionSchedule.deleted_at.is_(None),
            )
            .order_by(ExecutionSchedule.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_schedule(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        intent_template: dict[str, Any],
        trigger_type: str,
        trigger_config: dict[str, Any],
        is_active: bool = True,
    ) -> ExecutionSchedule:
        normalized_trigger = self._parse_trigger_type(trigger_type)
        normalized_template = self._normalize_intent_template(intent_template=intent_template, task_id=task_id)
        normalized_trigger_config = self._normalize_trigger_config(
            trigger_type=normalized_trigger,
            trigger_config=trigger_config,
        )
        schedule = ExecutionSchedule(
            user_id=user_id,
            task_id=task_id,
            intent_template=normalized_template,
            trigger_type=normalized_trigger,
            trigger_config=normalized_trigger_config,
            is_active=bool(is_active),
            next_run_at=(
                self._compute_next_run_at(
                    trigger_type=normalized_trigger,
                    trigger_config=normalized_trigger_config,
                    from_time=_utcnow(),
                )
                if is_active
                else None
            ),
        )
        self._db.add(schedule)
        await self._db.commit()
        await self._db.refresh(schedule)
        return schedule

    async def pause_schedule(self, *, schedule_id: UUID, user_id: UUID) -> ExecutionSchedule:
        schedule = await self._get_user_schedule(schedule_id=schedule_id, user_id=user_id)
        schedule.is_active = False
        schedule.next_run_at = None
        self._db.add(schedule)
        await self._db.commit()
        await self._db.refresh(schedule)
        return schedule

    async def resume_schedule(self, *, schedule_id: UUID, user_id: UUID) -> ExecutionSchedule:
        schedule = await self._get_user_schedule(schedule_id=schedule_id, user_id=user_id)
        schedule.is_active = True
        schedule.next_run_at = self._compute_next_run_at(
            trigger_type=schedule.trigger_type,
            trigger_config=schedule.trigger_config or {},
            from_time=_utcnow(),
        )
        self._db.add(schedule)
        await self._db.commit()
        await self._db.refresh(schedule)
        return schedule

    async def delete_schedule(self, *, schedule_id: UUID, user_id: UUID) -> None:
        schedule = await self._get_user_schedule(schedule_id=schedule_id, user_id=user_id)
        schedule.soft_delete()
        self._db.add(schedule)
        await self._db.commit()

    async def tick_due_schedules(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or _utcnow()
        result = await self._db.execute(
            select(ExecutionSchedule)
            .where(
                ExecutionSchedule.deleted_at.is_(None),
                ExecutionSchedule.is_active.is_(True),
                ExecutionSchedule.next_run_at.is_not(None),
                ExecutionSchedule.next_run_at <= current,
            )
            .order_by(ExecutionSchedule.next_run_at.asc())
        )
        schedules = list(result.scalars().all())
        dispatched: list[ExecutionScheduleDispatchResult] = []
        for schedule in schedules:
            outcome = await self._dispatch_schedule(schedule=schedule, current=current)
            dispatched.append(outcome)
        return {
            "checked_at": current.isoformat(),
            "due_count": len(schedules),
            "dispatched_count": sum(1 for item in dispatched if item.intent_id),
            "items": [item.__dict__ for item in dispatched],
        }

    async def trigger_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_event = str(event_type or "").strip()
        if not normalized_event:
            raise ValueError("event_type is required")

        result = await self._db.execute(
            select(ExecutionSchedule)
            .where(
                ExecutionSchedule.deleted_at.is_(None),
                ExecutionSchedule.is_active.is_(True),
                ExecutionSchedule.trigger_type == ExecutionScheduleTriggerType.EVENT,
            )
            .order_by(ExecutionSchedule.created_at.asc())
        )
        schedules = [
            item
            for item in result.scalars().all()
            if str((item.trigger_config or {}).get("event_type") or "").strip() == normalized_event
        ]
        dispatched: list[ExecutionScheduleDispatchResult] = []
        for schedule in schedules:
            dispatched.append(await self._dispatch_schedule(schedule=schedule, current=_utcnow(), event_payload=payload))
        return {
            "event_type": normalized_event,
            "matched_count": len(schedules),
            "dispatched_count": sum(1 for item in dispatched if item.intent_id),
            "items": [item.__dict__ for item in dispatched],
        }

    async def _dispatch_schedule(
        self,
        *,
        schedule: ExecutionSchedule,
        current: datetime,
        event_payload: dict[str, Any] | None = None,
    ) -> ExecutionScheduleDispatchResult:
        from app.services.execution_service import ExecutionService

        if schedule.trigger_type == ExecutionScheduleTriggerType.CONDITION:
            matched = await self._condition_matches(schedule.trigger_config or {})
            schedule.next_run_at = current + timedelta(
                minutes=max(5, int((schedule.trigger_config or {}).get("interval_minutes") or 5))
            )
            self._db.add(schedule)
            await self._db.commit()
            if not matched:
                return ExecutionScheduleDispatchResult(
                    schedule_id=str(schedule.id),
                    intent_id=None,
                    status="skipped",
                    detail="condition_not_met",
                )

        template = dict(schedule.intent_template or {})
        service = ExecutionService(self._db, redis=self._redis)
        try:
            intent = await service.handoff_to_openclaw(
                task_id=schedule.task_id,
                user_id=schedule.user_id,
                goal=str(template.get("goal") or "").strip() or None,
                instructions=list(template.get("instructions") or []),
                policy=dict(template.get("policy") or {}),
                success_criteria=dict(template.get("success_criteria") or {}),
                result_contract=dict(template.get("result_contract") or {}),
                template_id=str(template.get("template_id") or "").strip() or None,
                preferred_node_id=str(template.get("preferred_node_id") or "").strip() or None,
            )
        except Exception as exc:
            logger.warning("Execution schedule {} dispatch failed: {}", schedule.id, exc)
            schedule.last_run_at = current
            schedule.next_run_at = self._compute_next_run_at(
                trigger_type=schedule.trigger_type,
                trigger_config=schedule.trigger_config or {},
                from_time=current,
            )
            self._db.add(schedule)
            await self._db.commit()
            return ExecutionScheduleDispatchResult(
                schedule_id=str(schedule.id),
                intent_id=None,
                status="failed",
                detail=str(exc),
            )

        schedule.last_run_at = current
        schedule.next_run_at = self._compute_next_run_at(
            trigger_type=schedule.trigger_type,
            trigger_config=schedule.trigger_config or {},
            from_time=current,
        )
        self._db.add(schedule)
        await self._db.commit()
        await event_bus.publish(
            "EXECUTION_SCHEDULED_COMPLETED",
            {
                "event_type": "EXECUTION_SCHEDULED_COMPLETED",
                "schedule_id": str(schedule.id),
                "user_id": str(schedule.user_id),
                "task_id": str(schedule.task_id),
                "execution_intent_id": str(intent.id),
                "trigger_type": schedule.trigger_type.value if schedule.trigger_type else None,
                "event_payload": event_payload or {},
                "timestamp": current.isoformat(),
            },
        )
        return ExecutionScheduleDispatchResult(
            schedule_id=str(schedule.id),
            intent_id=str(intent.id),
            status=intent.status.value if intent.status else "unknown",
        )

    async def _condition_matches(self, trigger_config: dict[str, Any]) -> bool:
        check_url = str(trigger_config.get("check_url") or "").strip()
        condition = str(trigger_config.get("condition") or "").strip()
        if not check_url or not condition:
            return False
        try:
            safe_url = validate_external_url(check_url)
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)) as client:
                response = await client.get(safe_url)
                response.raise_for_status()
        except SSRFBlocked as exc:
            logger.warning("Scheduled condition check blocked for {}: {}", check_url, exc)
            return False
        except Exception as exc:
            logger.warning("Scheduled condition check failed for {}: {}", check_url, exc)
            return False
        body = response.text
        if condition.startswith("contains(") and condition.endswith(")"):
            expected = condition[len("contains("):-1].strip().strip("'\"")
            return expected in body
        if condition.startswith("equals(") and condition.endswith(")"):
            expected = condition[len("equals("):-1].strip().strip("'\"")
            return body.strip() == expected
        return False

    async def _get_user_schedule(self, *, schedule_id: UUID, user_id: UUID) -> ExecutionSchedule:
        schedule = await self._db.get(ExecutionSchedule, schedule_id)
        if not schedule or schedule.user_id != user_id or schedule.deleted_at is not None:
            raise ValueError("Execution schedule not found")
        return schedule

    @staticmethod
    def _parse_trigger_type(value: str) -> ExecutionScheduleTriggerType:
        normalized = str(value or "").strip().lower()
        mapping = {
            "cron": ExecutionScheduleTriggerType.CRON,
            "event": ExecutionScheduleTriggerType.EVENT,
            "condition": ExecutionScheduleTriggerType.CONDITION,
        }
        if normalized not in mapping:
            raise ValueError("Unsupported trigger_type")
        return mapping[normalized]

    @staticmethod
    def _normalize_intent_template(*, intent_template: dict[str, Any], task_id: UUID) -> dict[str, Any]:
        template = dict(intent_template or {})
        template["task_id"] = str(task_id)
        template["instructions"] = list(template.get("instructions") or [])
        template["policy"] = dict(template.get("policy") or {})
        template["success_criteria"] = dict(template.get("success_criteria") or {})
        template["result_contract"] = dict(template.get("result_contract") or {})
        return template

    def _normalize_trigger_config(
        self,
        *,
        trigger_type: ExecutionScheduleTriggerType,
        trigger_config: dict[str, Any],
    ) -> dict[str, Any]:
        config = dict(trigger_config or {})
        if trigger_type == ExecutionScheduleTriggerType.CRON:
            cron = str(config.get("cron") or "").strip()
            if not cron:
                raise ValueError("cron trigger requires trigger_config.cron")
            config["cron"] = cron
        elif trigger_type == ExecutionScheduleTriggerType.EVENT:
            event_type = str(config.get("event_type") or "").strip()
            if not event_type:
                raise ValueError("event trigger requires trigger_config.event_type")
            config["event_type"] = event_type
        else:
            check_url = str(config.get("check_url") or "").strip()
            condition = str(config.get("condition") or "").strip()
            if not check_url or not condition:
                raise ValueError("condition trigger requires check_url and condition")
            try:
                config["check_url"] = validate_external_url(check_url)
            except SSRFBlocked as exc:
                raise ValueError("condition trigger check_url is not allowed") from exc
            config["condition"] = condition
            config["interval_minutes"] = max(5, int(config.get("interval_minutes") or 5))
        return config

    def _compute_next_run_at(
        self,
        *,
        trigger_type: ExecutionScheduleTriggerType,
        trigger_config: dict[str, Any],
        from_time: datetime,
    ) -> datetime | None:
        if trigger_type == ExecutionScheduleTriggerType.EVENT:
            return None
        if trigger_type == ExecutionScheduleTriggerType.CONDITION:
            return from_time + timedelta(minutes=max(5, int(trigger_config.get("interval_minutes") or 5)))
        return self._next_cron_datetime(str(trigger_config.get("cron") or ""), from_time=from_time)

    @staticmethod
    def _next_cron_datetime(cron: str, *, from_time: datetime) -> datetime:
        fields = cron.split()
        if len(fields) != 5:
            raise ValueError("cron expression must contain 5 fields")
        minute_field, hour_field, _day, _month, weekday_field = fields
        candidate = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(60 * 24 * 8):
            if not ExecutionScheduleService._cron_field_matches(candidate.minute, minute_field):
                candidate += timedelta(minutes=1)
                continue
            if not ExecutionScheduleService._cron_field_matches(candidate.hour, hour_field):
                candidate += timedelta(minutes=1)
                continue
            weekday = (candidate.weekday() + 1) % 7
            if not ExecutionScheduleService._cron_field_matches(weekday, weekday_field):
                candidate += timedelta(minutes=1)
                continue
            return candidate
        raise ValueError("Unable to compute next cron execution within 8 days")

    @staticmethod
    def _cron_field_matches(value: int, field: str) -> bool:
        normalized = str(field or "*").strip()
        if normalized == "*":
            return True
        for part in normalized.split(","):
            item = part.strip()
            if not item:
                continue
            if item.isdigit() and int(item) == value:
                return True
        return False
