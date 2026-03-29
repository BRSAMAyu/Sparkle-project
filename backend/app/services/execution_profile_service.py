"""Read-only execution profile aggregation service."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus
from app.models.execution_record import ExecutionRecord
from app.models.task import Task


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_succeeded_status():
    return cast(ExecutionIntent.status, String) == ExecutionIntentStatus.SUCCEEDED.value


class ExecutionProfileService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_execution_profile(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        since = _utcnow() - timedelta(days=days)
        base_filter = (
            (ExecutionIntent.user_id == user_id)
            & (ExecutionIntent.created_at >= since)
            & (ExecutionIntent.deleted_at.is_(None))
        )

        total_stmt = select(
            func.count(ExecutionIntent.id).label("total"),
            func.sum(case((_is_succeeded_status(), 1), else_=0)).label(
                "succeeded",
            ),
        ).where(base_filter)
        total_row = (await self._db.execute(total_stmt)).one()
        total_executions = int(total_row.total or 0)
        success_rate = round((float(total_row.succeeded or 0) / total_executions), 2) if total_executions else 0.0

        by_type_stmt = (
            select(
                ExecutionIntent.target_env,
                func.count(ExecutionIntent.id).label("total"),
                func.sum(case((_is_succeeded_status(), 1), else_=0)).label(
                    "succeeded",
                ),
            )
            .where(base_filter)
            .group_by(ExecutionIntent.target_env)
        )
        by_type: dict[str, Any] = {}
        for row in (await self._db.execute(by_type_stmt)).all():
            key = row.target_env.value if row.target_env else "general"
            total = int(row.total or 0)
            by_type[key] = {
                "total": total,
                "succeeded": int(row.succeeded or 0),
                "success_rate": round((float(row.succeeded or 0) / total), 2) if total else 0.0,
            }

        trust_stmt = (
            select(ExecutionIntent.trust_level, func.count(ExecutionIntent.id).label("cnt"))
            .where(base_filter)
            .group_by(ExecutionIntent.trust_level)
        )
        trust_distribution = {
            row.trust_level.value if row.trust_level else "unknown": int(row.cnt or 0)
            for row in (await self._db.execute(trust_stmt)).all()
        }

        approval_stmt = (
            select(ExecutionRecord.approval_requested)
            .join(ExecutionIntent, ExecutionRecord.execution_intent_id == ExecutionIntent.id)
            .where(base_filter)
        )
        approval_request_count = sum(
            int(row.approval_requested or 0) for row in (await self._db.execute(approval_stmt)).all()
        )

        template_stmt = (
            select(ExecutionIntent.policy["template_metadata"]["template_id"].astext.label("template_id"))
            .where(base_filter)
        )
        template_counter = Counter(
            row.template_id for row in (await self._db.execute(template_stmt)).all() if row.template_id
        )

        time_saved_stmt = (
            select(
                Task.estimated_minutes,
                ExecutionRecord.duration_ms,
            )
            .join(ExecutionIntent, ExecutionIntent.task_id == Task.id)
            .join(ExecutionRecord, ExecutionRecord.execution_intent_id == ExecutionIntent.id)
            .where(
                base_filter,
                _is_succeeded_status(),
            )
        )
        estimated_time_saved_minutes = 0.0
        for row in (await self._db.execute(time_saved_stmt)).all():
            estimated_minutes = float(row.estimated_minutes or 0)
            actual_minutes = max(float(row.duration_ms or 0) / 60000.0, 0.0)
            estimated_time_saved_minutes += max(estimated_minutes - actual_minutes, 0.0)

        return {
            "days": days,
            "total_executions": total_executions,
            "success_rate": success_rate,
            "by_type": by_type,
            "trust_distribution": trust_distribution,
            "approval_request_count": approval_request_count,
            "top_templates": template_counter.most_common(5),
            "estimated_time_saved_minutes": round(estimated_time_saved_minutes, 1),
            "delegation_trend": (
                "increasing" if success_rate >= 0.7 else "stable" if success_rate >= 0.4 else "decreasing"
            ),
        }

    async def get_execution_profile_for_all_users(
        self,
        *,
        days: int = 30,
    ) -> dict[str, Any]:
        since = _utcnow() - timedelta(days=days)
        base_filter = (
            (ExecutionIntent.created_at >= since)
            & (ExecutionIntent.deleted_at.is_(None))
        )

        total_stmt = select(
            func.count(ExecutionIntent.id).label("total"),
            func.sum(case((_is_succeeded_status(), 1), else_=0)).label(
                "succeeded",
            ),
        ).where(base_filter)
        total_row = (await self._db.execute(total_stmt)).one()
        total_executions = int(total_row.total or 0)
        success_rate = round((float(total_row.succeeded or 0) / total_executions), 2) if total_executions else 0.0

        by_type_stmt = (
            select(
                ExecutionIntent.target_env,
                func.count(ExecutionIntent.id).label("total"),
                func.sum(case((_is_succeeded_status(), 1), else_=0)).label(
                    "succeeded",
                ),
            )
            .where(base_filter)
            .group_by(ExecutionIntent.target_env)
        )
        by_type: dict[str, Any] = {}
        for row in (await self._db.execute(by_type_stmt)).all():
            key = row.target_env.value if row.target_env else "general"
            total = int(row.total or 0)
            by_type[key] = {
                "total": total,
                "succeeded": int(row.succeeded or 0),
                "success_rate": round((float(row.succeeded or 0) / total), 2) if total else 0.0,
            }

        trust_stmt = (
            select(ExecutionIntent.trust_level, func.count(ExecutionIntent.id).label("cnt"))
            .where(base_filter)
            .group_by(ExecutionIntent.trust_level)
        )
        trust_distribution = {
            row.trust_level.value if row.trust_level else "unknown": int(row.cnt or 0)
            for row in (await self._db.execute(trust_stmt)).all()
        }

        approval_stmt = (
            select(ExecutionRecord.approval_requested)
            .join(ExecutionIntent, ExecutionRecord.execution_intent_id == ExecutionIntent.id)
            .where(base_filter)
        )
        approval_request_count = sum(
            int(row.approval_requested or 0) for row in (await self._db.execute(approval_stmt)).all()
        )

        template_stmt = (
            select(ExecutionIntent.policy["template_metadata"]["template_id"].astext.label("template_id"))
            .where(base_filter)
        )
        template_counter = Counter(
            row.template_id for row in (await self._db.execute(template_stmt)).all() if row.template_id
        )

        time_saved_stmt = (
            select(
                Task.estimated_minutes,
                ExecutionRecord.duration_ms,
            )
            .join(ExecutionIntent, ExecutionIntent.task_id == Task.id)
            .join(ExecutionRecord, ExecutionRecord.execution_intent_id == ExecutionIntent.id)
            .where(
                base_filter,
                _is_succeeded_status(),
            )
        )
        estimated_time_saved_minutes = 0.0
        for row in (await self._db.execute(time_saved_stmt)).all():
            estimated_minutes = float(row.estimated_minutes or 0)
            actual_minutes = max(float(row.duration_ms or 0) / 60000.0, 0.0)
            estimated_time_saved_minutes += max(estimated_minutes - actual_minutes, 0.0)

        return {
            "days": days,
            "total_executions": total_executions,
            "success_rate": success_rate,
            "by_type": by_type,
            "trust_distribution": trust_distribution,
            "approval_request_count": approval_request_count,
            "top_templates": template_counter.most_common(10),
            "estimated_time_saved_minutes": round(estimated_time_saved_minutes, 1),
            "delegation_trend": (
                "increasing" if success_rate >= 0.7 else "stable" if success_rate >= 0.4 else "decreasing"
            ),
        }
