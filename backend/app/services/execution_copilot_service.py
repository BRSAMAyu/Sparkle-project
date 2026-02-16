from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.learning_event_service import LearningEventService
from app.services.plan_state_service import PlanStateService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExecutionCopilotService:
    """Builds a lightweight execution cockpit for today's plan progress."""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.plan_state_service = PlanStateService(db, redis)

    async def build_copilot(self, *, user_id: UUID, plan_id: UUID, limit: int = 3) -> dict[str, Any]:
        plan = await self._get_plan(user_id=user_id, plan_id=plan_id)
        if not plan:
            return {
                "plan_id": str(plan_id),
                "today_actions": [],
                "blockers": ["plan_not_found"],
                "repair_suggestions": ["请先创建或切换到有效计划后再试。"],
                "execution_copilot_hint": "未找到计划，无法生成执行驾驶舱。",
            }

        tasks = await self._get_plan_tasks(plan_id=plan_id)
        today_actions = self._build_today_actions(tasks=tasks, limit=limit)
        blockers = self._detect_blockers(tasks=tasks)
        repair_suggestions = self._build_repair_suggestions(blockers=blockers, tasks=tasks)
        await LearningEventService(redis_client=self.redis).emit(
            event_type="checkpoint_due",
            user_id=str(user_id),
            workflow_id=str(plan_id),
            task_type="execution_copilot",
            data={
                "today_actions_count": len(today_actions),
                "blockers": blockers,
                "repair_suggestions": repair_suggestions,
            },
        )

        return {
            "plan_id": str(plan_id),
            "plan_name": plan.name,
            "today_actions": today_actions,
            "blockers": blockers,
            "repair_suggestions": repair_suggestions,
            "execution_copilot_hint": self._build_hint(today_actions=today_actions, blockers=blockers),
            "generated_at": _utcnow().isoformat(),
        }

    async def record_checkpoint_event(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        status: str,
        task_id: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized = str(status or "").strip().lower()
        if normalized not in {"done", "skipped"}:
            return {"success": False, "message": "invalid_status"}
        event_type = "checkpoint_done" if normalized == "done" else "checkpoint_skipped"
        payload = {
            "task_id": str(task_id or ""),
            "note": str(note or ""),
            "status": normalized,
        }
        await LearningEventService(redis_client=self.redis).emit(
            event_type=event_type,
            user_id=str(user_id),
            workflow_id=str(plan_id),
            task_type="execution_copilot",
            data=payload,
        )
        return {"success": True, "event_type": event_type}

    async def _get_plan(self, *, user_id: UUID, plan_id: UUID) -> Plan | None:
        result = await self.db.execute(
            select(Plan).where(
                and_(
                    Plan.id == plan_id,
                    Plan.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_plan_tasks(self, *, plan_id: UUID) -> list[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.plan_id == plan_id)
            .order_by(Task.priority.desc(), Task.due_date.asc().nullslast(), Task.created_at.asc())
        )
        return list(result.scalars().all())

    def _build_today_actions(self, *, tasks: list[Task], limit: int) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for task in tasks:
            if task.status in {TaskStatus.COMPLETED, TaskStatus.ABANDONED}:
                continue
            actions.append(
                {
                    "task_id": str(task.id),
                    "title": task.title,
                    "estimated_minutes": int(task.estimated_minutes or 0),
                    "priority": int(task.priority or 0),
                    "status": task.status.value,
                }
            )
            if len(actions) >= max(1, min(limit, 6)):
                break
        return actions

    def _detect_blockers(self, *, tasks: list[Task]) -> list[str]:
        blockers: list[str] = []
        today = date.today()
        in_progress_count = sum(1 for task in tasks if task.status == TaskStatus.IN_PROGRESS)
        overdue_count = sum(
            1
            for task in tasks
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.ABANDONED}
            and task.due_date is not None
            and task.due_date < today
        )
        no_acceptance_count = sum(
            1
            for task in tasks
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.ABANDONED}
            and not bool((task.guide_content or "").strip())
        )
        if in_progress_count >= 3:
            blockers.append("parallel_in_progress_overload")
        if overdue_count > 0:
            blockers.append("overdue_tasks_present")
        if no_acceptance_count >= 2:
            blockers.append("missing_task_guidance")
        return blockers

    def _build_repair_suggestions(self, *, blockers: list[str], tasks: list[Task]) -> list[str]:
        suggestions: list[str] = []
        if "parallel_in_progress_overload" in blockers:
            suggestions.append("先收敛并行任务：只保留 1-2 个进行中任务，其他回到待办。")
        if "overdue_tasks_present" in blockers:
            suggestions.append("优先处理已逾期任务，必要时重设截止日期并缩小任务粒度。")
        if "missing_task_guidance" in blockers:
            suggestions.append("为关键任务补齐验收标准和完成定义，减少执行歧义。")
        if not suggestions and tasks:
            suggestions.append("按优先级执行今日前三步，完成后再开启下一任务。")
        if not suggestions:
            suggestions.append("当前暂无可执行任务，请先创建今日任务。")
        return suggestions[:3]

    @staticmethod
    def _build_hint(*, today_actions: list[dict[str, Any]], blockers: list[str]) -> str:
        if not today_actions:
            return "今日暂无可执行动作，建议先明确一个最小行动任务。"
        if blockers:
            return f"已识别 {len(blockers)} 个执行阻塞点，建议先完成第一步并处理阻塞。"
        return f"今日建议先执行前 {min(3, len(today_actions))} 步，完成后再滚动更新计划。"
