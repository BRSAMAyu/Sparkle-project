from __future__ import annotations

from datetime import timezone, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanPriority
from app.models.task import Task, TaskStatus
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GrowthDashboardService:
    """Computes the high-signal dashboard payload for Phase 5."""

    LOOKBACK_DAYS = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_snapshot(self, user_id: UUID, *, user: User | None = None) -> dict[str, Any]:
        resolved_user = user or await self._get_user(user_id)
        active_plan = await self._get_active_plan(user_id)
        growth_signal = await self._get_growth_signal(user_id)
        most_important_task = await self._get_most_important_task(user_id)
        weakest_area = await self._get_weakest_area(user_id)
        growth_status = await self._get_growth_status(
            user_id=user_id,
            user=resolved_user,
            active_plan=active_plan,
            growth_signal=growth_signal,
            most_important_task=most_important_task,
            weakest_area=weakest_area,
        )
        active_plan_progress = self._serialize_active_plan(active_plan)
        what_changed_card = self._build_what_changed_card(
            growth_signal=growth_signal,
            growth_status=growth_status,
            weakest_area=weakest_area,
        )
        next_move_card = self._build_next_move_card(
            most_important_task=most_important_task,
            active_plan=active_plan,
            weakest_area=weakest_area,
        )

        return {
            "growth_status": growth_status,
            "most_important_task": most_important_task,
            "growth_signal": growth_signal,
            "active_plan_progress": active_plan_progress,
            "what_changed_card": what_changed_card,
            "next_move_card": next_move_card,
        }

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _get_active_plan(self, user_id: UUID) -> Plan | None:
        stmt = (
            select(Plan)
            .where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
            .order_by(
                desc(Plan.is_primary),
                Plan.target_date,
                desc(Plan.created_at),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_growth_status(
        self,
        *,
        user_id: UUID,
        user: User,
        active_plan: Plan | None,
        growth_signal: dict[str, Any] | None,
        most_important_task: dict[str, Any] | None,
        weakest_area: str | None,
    ) -> dict[str, Any]:
        period_start = _utcnow() - timedelta(days=self.LOOKBACK_DAYS)
        focus_minutes = await self._sum_focus_minutes(user_id, period_start)
        tasks_completed = await self._count_completed_tasks(user_id, period_start)
        streak_days = await self._get_current_streak_days(user_id)
        display_name = str(user.nickname or user.full_name or user.username or "Sparkle").strip()

        signal_label = ""
        signal_delta = 0
        if isinstance(growth_signal, dict):
            signal_label = str(growth_signal.get("topic") or "").strip()
            signal_delta = int(round(float(growth_signal.get("delta_points") or 0.0)))

        focus_hours = round(focus_minutes / 60.0, 1)
        plan_label = str(active_plan.subject or active_plan.name) if active_plan else ""
        if tasks_completed > 0 and signal_label:
            headline = f"{display_name}，上周你完成了 {tasks_completed} 个任务，在「{signal_label}」上也看到了真实进展。"
        elif tasks_completed > 0:
            headline = f"{display_name}，上周你完成了 {tasks_completed} 个任务，学习节奏正在重新站稳。"
        elif signal_delta > 0 and signal_label:
            headline = f"{display_name}，这周你在「{signal_label}」上往前推了 {signal_delta:.0f} 个点。"
        else:
            headline = f"{display_name}，今天我先帮你把真正关键的一步放到前面。"

        subtitle_parts: list[str] = []
        if weakest_area:
            subtitle_parts.append(f"现在最该补的是「{weakest_area}」")
        elif plan_label:
            subtitle_parts.append(f"当前最值得盯住的是「{plan_label}」")

        if most_important_task and most_important_task.get("title"):
            subtitle_parts.append(f"我建议你先做「{most_important_task['title']}」")
        elif active_plan and active_plan.target_date:
            subtitle_parts.append(
                f"当前计划「{active_plan.name}」离目标日还有 {self._days_until(active_plan.target_date)} 天"
            )

        if streak_days > 0:
            subtitle_parts.append(f"你已经连续 {streak_days} 天保持推进")
        elif focus_hours > 0:
            subtitle_parts.append(f"最近 7 天已经积累了 {focus_hours} 小时专注时间")

        subtitle = "。".join(part.rstrip("。") for part in subtitle_parts if part).strip()
        if subtitle:
            subtitle = f"{subtitle}。"
        else:
            subtitle = "先把今天最有杠杆的一步做出来，后面的节奏就会顺很多。"

        return {
            "headline": headline,
            "subtitle": subtitle,
            "user_name": display_name,
            "streak_days": streak_days,
            "focus_hours_week": focus_hours,
            "tasks_completed_week": tasks_completed,
        }

    def _build_what_changed_card(
        self,
        *,
        growth_signal: dict[str, Any] | None,
        growth_status: dict[str, Any] | None,
        weakest_area: str | None,
    ) -> dict[str, Any] | None:
        if not growth_signal and not growth_status:
            return None

        topic = str((growth_signal or {}).get("topic") or weakest_area or "").strip()
        highlights: list[str] = []
        if topic:
            highlights.append(f"最近真正有变化的是「{topic}」而不只是表面忙碌。")
        signal_summary = str((growth_signal or {}).get("summary") or "").strip()
        if signal_summary:
            highlights.append(signal_summary)
        growth_subtitle = str((growth_status or {}).get("subtitle") or "").strip()
        if growth_subtitle:
            highlights.append(growth_subtitle)

        if not highlights:
            return None

        return {
            "headline": str((growth_status or {}).get("headline") or "我注意到你的推进轨迹有了真实变化。").strip(),
            "summary": highlights[0],
            "highlights": highlights[:3],
            "timeframe_label": "最近 7 天",
        }

    def _build_next_move_card(
        self,
        *,
        most_important_task: dict[str, Any] | None,
        active_plan: Plan | None,
        weakest_area: str | None,
    ) -> dict[str, Any] | None:
        if not most_important_task:
            return None

        title = str(most_important_task.get("title") or "").strip()
        if not title:
            return None

        reason = str(most_important_task.get("reason") or "").strip()
        plan_name = str(most_important_task.get("plan_name") or getattr(active_plan, "name", "") or "").strip()
        why_now = (
            f"因为它最直接对应你现在还没补稳的「{weakest_area}」。"
            if weakest_area
            else "因为它是现在风险和收益最平衡的一步。"
        )
        reassurance = "如果今天状态不稳，我们也可以把它再拆小，不需要硬扛。"

        return {
            "headline": f"下一步先做「{title}」",
            "summary": reason or why_now,
            "why_now": why_now,
            "reassurance": reassurance,
            "task_id": str(most_important_task.get('id') or '').strip(),
            "estimated_minutes": int(most_important_task.get("estimated_minutes") or 0),
            "plan_name": plan_name or None,
            "days_to_deadline": most_important_task.get("days_to_deadline"),
        }

    async def _sum_focus_minutes(self, user_id: UUID, start: datetime) -> int:
        stmt = select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.start_time >= start,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def _count_completed_tasks(self, user_id: UUID, start: datetime) -> int:
        stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= start,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def _get_current_streak_days(self, user_id: UUID) -> int:
        cutoff = _utcnow() - timedelta(days=30)
        task_result = await self.db.execute(
            select(Task.completed_at).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= cutoff,
            )
        )
        focus_result = await self.db.execute(
            select(FocusSession.start_time).where(
                FocusSession.user_id == user_id,
                FocusSession.status == FocusStatus.COMPLETED,
                FocusSession.start_time >= cutoff,
            )
        )
        active_days = {
            value.date()
            for value in [*task_result.scalars().all(), *focus_result.scalars().all()]
            if isinstance(value, datetime)
        }
        if not active_days:
            return 0

        cursor = _utcnow().date()
        if cursor not in active_days and (cursor - timedelta(days=1)) in active_days:
            cursor -= timedelta(days=1)

        streak = 0
        while cursor in active_days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    async def _get_growth_signal(self, user_id: UUID) -> dict[str, Any] | None:
        period_start = _utcnow() - timedelta(days=self.LOOKBACK_DAYS)
        stmt = (
            select(
                StudyRecord.node_id,
                KnowledgeNode.name,
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0).label("mastery_delta"),
                func.count(StudyRecord.id).label("review_count"),
                func.coalesce(func.sum(StudyRecord.study_minutes), 0).label("study_minutes"),
            )
            .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
            .where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= period_start,
            )
            .group_by(StudyRecord.node_id, KnowledgeNode.name)
            .order_by(desc("mastery_delta"), desc("review_count"))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row and float(row.mastery_delta or 0.0) > 0:
            mastery_stmt = select(UserNodeStatus.mastery_score).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == row.node_id,
            )
            mastery_result = await self.db.execute(mastery_stmt)
            current_mastery = float(mastery_result.scalar() or 0.0)
            previous_mastery = max(0.0, current_mastery - float(row.mastery_delta or 0.0))
            summary = (
                f"{row.name} 掌握度从 {previous_mastery / 100:.2f} 提升到 {current_mastery / 100:.2f}"
            )
            source = f"{int(row.review_count or 0)} 次学习记录 / {int(row.study_minutes or 0)} 分钟投入"
            return {
                "topic": row.name,
                "headline": f"{row.name}: {previous_mastery / 100:.2f} -> {current_mastery / 100:.2f}",
                "summary": summary,
                "source": source,
                "delta_points": round(float(row.mastery_delta or 0.0), 1),
                "evidence_count": int(row.review_count or 0),
            }

        fallback_tasks = await self._count_completed_tasks(user_id, period_start)
        fallback_focus = await self._sum_focus_minutes(user_id, period_start)
        if fallback_tasks > 0 or fallback_focus > 0:
            return {
                "topic": "执行节奏",
                "headline": "这周的推进证据已经累起来了",
                "summary": f"最近 7 天完成了 {fallback_tasks} 个任务，并积累了 {fallback_focus} 分钟专注时间。",
                "source": "任务完成记录 + 专注会话",
                "delta_points": float(fallback_tasks),
                "evidence_count": fallback_tasks,
            }
        return None

    async def _get_weakest_area(self, user_id: UUID) -> str | None:
        stmt = (
            select(KnowledgeNode.name, UserNodeStatus.mastery_score)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_id)
            .order_by(UserNodeStatus.mastery_score.asc(), KnowledgeNode.name.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        name = str(row.name or "").strip()
        return name or None

    async def _get_most_important_task(self, user_id: UUID) -> dict[str, Any] | None:
        stmt = (
            select(Task, Plan, UserNodeStatus.mastery_score)
            .outerjoin(Plan, Task.plan_id == Plan.id)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == Task.knowledge_node_id,
                ),
            )
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
            )
            .order_by(desc(Task.priority), Task.created_at)
            .limit(25)
        )
        result = await self.db.execute(stmt)
        candidates = result.all()
        if not candidates:
            return None

        best_payload: dict[str, Any] | None = None
        best_score = -1.0
        for task, plan, mastery_score in candidates:
            mastery_gap = self._mastery_gap(task, mastery_score)
            deadline_factor = self._deadline_factor(task, plan)
            plan_factor = self._plan_factor(plan)
            priority_factor = 1.0 + min(max(int(task.priority or 0), 0), 5) * 0.12
            score = plan_factor * priority_factor * max(mastery_gap, 0.25) * max(deadline_factor, 0.5)

            if score <= best_score:
                continue

            due_reference = task.due_date or getattr(plan, "target_date", None)
            best_score = score
            best_payload = {
                "id": str(task.id),
                "title": task.title,
                "estimated_minutes": int(task.estimated_minutes or 0),
                "priority": int(task.priority or 0),
                "type": getattr(task.type, "value", str(task.type or "")),
                "risk_score": round(score, 3),
                "reason": self._task_reason(task, plan, mastery_gap, deadline_factor),
                "plan_name": plan.name if plan else None,
                "days_to_deadline": self._days_until(due_reference) if due_reference else None,
            }
        return best_payload

    def _mastery_gap(self, task: Task, mastery_score: float | None) -> float:
        if mastery_score is not None:
            return max(0.15, (100.0 - float(mastery_score or 0.0)) / 100.0)
        return min(0.8, 0.3 + float(task.difficulty or 1) * 0.1)

    def _deadline_factor(self, task: Task, plan: Plan | None) -> float:
        due_reference = task.due_date or getattr(plan, "target_date", None)
        if due_reference is None:
            return 0.8
        days = self._days_until(due_reference)
        if days <= 0:
            return 1.6
        if days <= 2:
            return 1.4
        if days <= 5:
            return 1.15
        return max(0.75, 1.0 - (days / 30.0))

    def _plan_factor(self, plan: Plan | None) -> float:
        if not plan:
            return 0.9
        priority_weights = {
            PlanPriority.CRITICAL.value: 1.3,
            PlanPriority.HIGH.value: 1.15,
            PlanPriority.NORMAL.value: 1.0,
            PlanPriority.LOW.value: 0.85,
        }
        raw_priority = getattr(plan.priority, "value", plan.priority)
        base = priority_weights.get(str(raw_priority or "").lower(), 1.0)
        if bool(plan.is_primary):
            base += 0.1
        return base

    def _task_reason(
        self,
        task: Task,
        plan: Plan | None,
        mastery_gap: float,
        deadline_factor: float,
    ) -> str:
        if mastery_gap >= 0.6 and deadline_factor >= 1.2:
            return "它同时卡在掌握度缺口和临近截止日上，最值得优先处理。"
        if mastery_gap >= 0.6:
            return "它背后对应的掌握度缺口还比较大，先补上会更稳。"
        if deadline_factor >= 1.2:
            return "它离截止时间更近，先推进能明显降低计划风险。"
        if plan and plan.is_primary:
            return "它属于你当前的主计划，先推进它最容易带来整体进度。"
        return "这是今天风险和收益最平衡的一步，先做它最划算。"

    def _serialize_active_plan(self, plan: Plan | None) -> dict[str, Any] | None:
        if plan is None:
            return None
        return {
            "id": str(plan.id),
            "name": plan.name,
            "type": getattr(plan.type, "value", str(plan.type or "")),
            "phase": getattr(plan.plan_stage, "value", str(plan.plan_stage or "")),
            "progress": float(plan.progress or 0.0),
            "mastery_level": float(plan.mastery_level or 0.0),
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "days_to_deadline": self._days_until(plan.target_date) if plan.target_date else None,
        }

    @staticmethod
    def _days_until(value: date | datetime | None) -> int:
        if value is None:
            return 0
        if isinstance(value, datetime):
            target = value.date()
        else:
            target = value
        return (target - _utcnow().date()).days
