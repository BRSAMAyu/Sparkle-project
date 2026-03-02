from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
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
                "checkpoint_summary": self._empty_checkpoint_summary(),
                "risk_level": "high",
                "adoptable_actions": [],
            }

        tasks = await self._get_plan_tasks(plan_id=plan_id)
        today_actions = self._build_today_actions(tasks=tasks, limit=limit)
        blockers = self._detect_blockers(tasks=tasks)
        repair_suggestions = self._build_repair_suggestions(blockers=blockers, tasks=tasks)
        checkpoint_summary = await self._build_checkpoint_summary(plan_id=plan_id, days=14)
        risk_level = self._assess_risk_level(
            blockers=blockers,
            checkpoint_summary=checkpoint_summary,
            tasks=tasks,
            today_actions=today_actions,
        )
        adoptable_actions = self._build_adoptable_actions(
            today_actions=today_actions,
            blockers=blockers,
            repair_suggestions=repair_suggestions,
            risk_level=risk_level,
        )
        await LearningEventService(redis_client=self.redis).emit(
            event_type="checkpoint_due",
            user_id=str(user_id),
            workflow_id=str(plan_id),
            task_type="execution_copilot",
            data={
                "today_actions_count": len(today_actions),
                "blockers": blockers,
                "repair_suggestions": repair_suggestions,
                "risk_level": risk_level,
            },
        )

        return {
            "plan_id": str(plan_id),
            "plan_name": plan.name,
            "today_actions": today_actions,
            "blockers": blockers,
            "repair_suggestions": repair_suggestions,
            "execution_copilot_hint": self._build_hint(today_actions=today_actions, blockers=blockers),
            "checkpoint_summary": checkpoint_summary,
            "risk_level": risk_level,
            "adoptable_actions": adoptable_actions,
            "generated_at": _utcnow().isoformat(),
        }

    async def build_timeline(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        days: int = 7,
    ) -> dict[str, Any]:
        plan = await self._get_plan(user_id=user_id, plan_id=plan_id)
        if not plan:
            return {
                "plan_id": str(plan_id),
                "timeline_days": max(1, min(int(days), 30)),
                "timeline": [],
                "checkpoint_summary": self._empty_checkpoint_summary(),
                "top_blockers": [],
            }

        timeline_days = max(1, min(int(days), 30))
        events = await self._list_checkpoint_events(plan_id=plan_id, days=timeline_days)
        timeline_rows = self._build_timeline_rows(events=events, days=timeline_days)
        summary = self._summarize_checkpoint_events(events=events)
        top_blockers = self._top_blockers(events=events)
        return {
            "plan_id": str(plan_id),
            "plan_name": plan.name,
            "timeline_days": timeline_days,
            "timeline": timeline_rows,
            "checkpoint_summary": summary,
            "top_blockers": top_blockers,
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

    async def _list_checkpoint_events(self, *, plan_id: UUID, days: int) -> list[dict[str, Any]]:
        since = _utcnow() - timedelta(days=max(1, days))
        events = await LearningEventService(redis_client=self.redis).list_events_since(
            since=since,
            limit=10000,
            event_types={"checkpoint_due", "checkpoint_done", "checkpoint_skipped"},
        )
        plan_id_text = str(plan_id)
        return [row for row in events if str(row.get("workflow_id", "")) == plan_id_text]

    async def _build_checkpoint_summary(self, *, plan_id: UUID, days: int) -> dict[str, Any]:
        events = await self._list_checkpoint_events(plan_id=plan_id, days=days)
        return self._summarize_checkpoint_events(events=events)

    @staticmethod
    def _summarize_checkpoint_events(*, events: list[dict[str, Any]]) -> dict[str, Any]:
        due = 0
        done = 0
        skipped = 0
        latest_status = "none"
        latest_timestamp = ""
        for row in events:
            event_type = str(row.get("event_type", ""))
            if event_type == "checkpoint_due":
                due += 1
            elif event_type == "checkpoint_done":
                done += 1
                ts = str(row.get("timestamp", ""))
                if ts >= latest_timestamp:
                    latest_timestamp = ts
                    latest_status = "done"
            elif event_type == "checkpoint_skipped":
                skipped += 1
                ts = str(row.get("timestamp", ""))
                if ts >= latest_timestamp:
                    latest_timestamp = ts
                    latest_status = "skipped"

        completion_denominator = max(1, done + skipped)
        due_denominator = max(1, due)
        done_rate = float(done) / completion_denominator
        skip_rate = float(skipped) / completion_denominator
        due_completion_rate = float(done) / due_denominator
        return {
            "due": due,
            "done": done,
            "skipped": skipped,
            "done_rate": round(done_rate, 4),
            "skip_rate": round(skip_rate, 4),
            "due_completion_rate": round(due_completion_rate, 4),
            "last_status": latest_status,
        }

    @classmethod
    def _empty_checkpoint_summary(cls) -> dict[str, Any]:
        return {
            "due": 0,
            "done": 0,
            "skipped": 0,
            "done_rate": 0.0,
            "skip_rate": 0.0,
            "due_completion_rate": 0.0,
            "last_status": "none",
        }

    @classmethod
    def _build_timeline_rows(cls, *, events: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
        day_stats: dict[str, dict[str, Any]] = {}
        for idx in range(days):
            day = (date.today() - timedelta(days=days - idx - 1)).isoformat()
            day_stats[day] = {
                "date": day,
                "due": 0,
                "done": 0,
                "skipped": 0,
                "blockers": Counter(),
            }

        for row in events:
            timestamp = str(row.get("timestamp", ""))
            if "T" not in timestamp:
                continue
            day = timestamp.split("T", 1)[0]
            if day not in day_stats:
                continue
            slot = day_stats[day]
            event_type = str(row.get("event_type", ""))
            if event_type == "checkpoint_due":
                slot["due"] += 1
                payload = row.get("data") if isinstance(row.get("data"), dict) else {}
                blockers = payload.get("blockers") if isinstance(payload.get("blockers"), list) else []
                for blocker in blockers:
                    blocker_key = str(blocker).strip()
                    if blocker_key:
                        slot["blockers"][blocker_key] += 1
            elif event_type == "checkpoint_done":
                slot["done"] += 1
            elif event_type == "checkpoint_skipped":
                slot["skipped"] += 1

        rows: list[dict[str, Any]] = []
        for day in sorted(day_stats):
            slot = day_stats[day]
            done = int(slot["done"])
            skipped = int(slot["skipped"])
            due = int(slot["due"])
            denom = max(1, done + skipped)
            top_blocker = ""
            blocker_counter = slot["blockers"]
            if blocker_counter:
                top_blocker = blocker_counter.most_common(1)[0][0]
            rows.append(
                {
                    "date": day,
                    "due": due,
                    "done": done,
                    "skipped": skipped,
                    "done_rate": round(float(done) / denom, 4),
                    "skip_rate": round(float(skipped) / denom, 4),
                    "due_completion_rate": round(float(done) / max(1, due), 4),
                    "top_blocker": top_blocker,
                }
            )
        return rows

    @staticmethod
    def _top_blockers(*, events: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for row in events:
            if str(row.get("event_type", "")) != "checkpoint_due":
                continue
            payload = row.get("data") if isinstance(row.get("data"), dict) else {}
            blockers = payload.get("blockers") if isinstance(payload.get("blockers"), list) else []
            for blocker in blockers:
                blocker_key = str(blocker).strip()
                if blocker_key:
                    counter[blocker_key] += 1
        return [{"blocker": key, "count": count} for key, count in counter.most_common(max(1, limit))]

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

    def _build_adoptable_actions(
        self,
        *,
        today_actions: list[dict[str, Any]],
        blockers: list[str],
        repair_suggestions: list[str],
        risk_level: str,
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for item in today_actions[:3]:
            actions.append(
                {
                    "action_type": "execute_task",
                    "task_id": str(item.get("task_id", "")),
                    "title": str(item.get("title", "")),
                    "estimated_minutes": int(item.get("estimated_minutes", 0) or 0),
                }
            )
        if "overdue_tasks_present" in blockers:
            actions.append(
                {
                    "action_type": "handle_overdue",
                    "title": "先清理逾期任务",
                    "instruction": "优先处理逾期任务并重设其截止时间。",
                }
            )
        if risk_level in {"medium", "high"} and repair_suggestions:
            actions.append(
                {
                    "action_type": "apply_repair",
                    "title": "执行纠偏动作",
                    "instruction": repair_suggestions[0],
                }
            )
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in actions:
            key = f"{item.get('action_type')}::{item.get('task_id', '')}::{item.get('title', '')}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= 4:
                break
        return deduped

    def _assess_risk_level(
        self,
        *,
        blockers: list[str],
        checkpoint_summary: dict[str, Any],
        tasks: list[Task],
        today_actions: list[dict[str, Any]],
    ) -> str:
        if not today_actions:
            return "high"
        if "overdue_tasks_present" in blockers and "parallel_in_progress_overload" in blockers:
            return "high"
        if "missing_task_guidance" in blockers and "overdue_tasks_present" in blockers:
            return "high"

        pending_count = sum(
            1 for task in tasks if task.status not in {TaskStatus.COMPLETED, TaskStatus.ABANDONED}
        )
        done_rate = float(checkpoint_summary.get("done_rate", 0.0) or 0.0)
        skip_rate = float(checkpoint_summary.get("skip_rate", 0.0) or 0.0)
        if pending_count >= 8 and done_rate < 0.4:
            return "high"
        if skip_rate >= 0.6:
            return "high"
        if blockers or done_rate < 0.55:
            return "medium"
        return "low"

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
