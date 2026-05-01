from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.achievement import UserStreakStats
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanPriority
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.llm_fallback_utils import safe_llm_json_call
from app.services.plan_progress_service import PlanHealthReport, PlanProgressService
from app.services.progress_narrative_service import ProgressNarrativeService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class DailyContextLineContext:
    target_day: date
    display_name: str
    plan_name: str | None = None
    subject: str | None = None
    days_to_deadline: int | None = None
    yesterday_total: int = 0
    yesterday_completed: int = 0
    completed_yesterday: int = 0
    bottleneck: str | None = None
    streak_days: int = 0
    next_action_title: str | None = None

    @property
    def has_personal_data(self) -> bool:
        return any(
            [
                self.plan_name,
                self.subject,
                self.days_to_deadline is not None,
                self.yesterday_total > 0,
                self.completed_yesterday > 0,
                self.bottleneck,
                self.streak_days > 0,
                self.next_action_title,
            ]
        )


class GrowthDashboardService:
    """Computes the high-signal dashboard payload for Phase 5."""

    LOOKBACK_DAYS = 7
    DAILY_CONTEXT_RECENT_TTL_SECONDS = 86400 * 21
    DAILY_CONTEXT_RECENT_LIMIT = 14

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_snapshot(self, user_id: UUID, *, user: User | None = None) -> dict[str, Any]:
        resolved_user = user or await self._get_user(user_id)
        active_plan = await self._get_active_plan(user_id)
        growth_signal = await self._get_growth_signal(user_id)
        achievement_stories = await ProgressNarrativeService(self.db).recent_achievement_story_lines(
            str(user_id),
            _utcnow() - timedelta(days=self.LOOKBACK_DAYS),
            _utcnow(),
        )
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
        active_plan_health = await self._get_plan_health(user_id, active_plan)
        active_plan_progress = self._serialize_active_plan(active_plan, health=active_plan_health)
        what_changed_card = self._build_what_changed_card(
            growth_signal=growth_signal,
            growth_status=growth_status,
            weakest_area=weakest_area,
            achievement_stories=achievement_stories,
        )
        next_move_card = self._build_next_move_card(
            most_important_task=most_important_task,
            active_plan=active_plan,
            weakest_area=weakest_area,
        )
        active_bottleneck = self._build_active_bottleneck(weakest_area)

        return {
            "growth_status": growth_status,
            "most_important_task": most_important_task,
            "growth_signal": growth_signal,
            "active_plan_progress": active_plan_progress,
            "active_bottleneck": active_bottleneck,
            "what_changed_card": what_changed_card,
            "next_move_card": next_move_card,
        }

    async def get_daily_context_line(
        self,
        user_id: UUID,
        *,
        user: User | None = None,
        target_day: date | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Return one cached, context-aware line for the top of Home."""
        day = target_day or date.today()
        cache_key = self._daily_context_line_cache_key(user_id, day)
        if not force_refresh:
            cached = await cache_service.get(cache_key)
            if isinstance(cached, dict) and str(cached.get("text") or "").strip():
                return cached

        context = await self._build_daily_context_line_context(user_id, user=user, target_day=day)
        recent_lines = await self._get_recent_daily_context_lines(user_id)
        fallback_line = self._rule_daily_context_line(context, recent_lines)
        text = fallback_line
        source = "rule"

        ai_line = await self._generate_daily_context_line_with_ai(context, recent_lines)
        if self._is_valid_context_line(ai_line, context, recent_lines):
            text = self._clean_context_line(ai_line)
            source = "ai"
        elif self._is_recent_duplicate(text, recent_lines):
            text = self._rule_daily_context_line(context, recent_lines, avoid_duplicates=True)

        payload = {
            "text": text,
            "source": source,
            "date": day.isoformat(),
            "generated_at": _utcnow().isoformat(),
            "context": self._daily_context_payload(context),
        }
        await cache_service.set(
            cache_key,
            payload,
            ttl=self._seconds_until_next_day(day),
        )
        await self._remember_daily_context_line(user_id, text, day)
        return payload

    @classmethod
    def _daily_context_line_cache_key(cls, user_id: UUID, target_day: date) -> str:
        return f"growth:daily_context_line:{user_id}:{target_day.isoformat()}"

    @classmethod
    def _daily_context_recent_key(cls, user_id: UUID) -> str:
        return f"growth:daily_context_line:{user_id}:recent"

    async def _build_daily_context_line_context(
        self,
        user_id: UUID,
        *,
        user: User | None,
        target_day: date,
    ) -> DailyContextLineContext:
        resolved_user = user or await self._get_user(user_id)
        active_plan = await self._get_active_plan(user_id)
        most_important_task = await self._get_most_important_task(user_id)
        bottleneck = await self._get_weakest_area(user_id)
        streak_days = await self._get_streak_stats_days(user_id)
        yesterday_stats = await self._get_yesterday_task_completion(user_id, target_day=target_day)
        display_name = str(resolved_user.nickname or resolved_user.full_name or resolved_user.username or "你").strip()

        return DailyContextLineContext(
            target_day=target_day,
            display_name=display_name or "你",
            plan_name=str(active_plan.name).strip() if active_plan and active_plan.name else None,
            subject=str(active_plan.subject).strip() if active_plan and active_plan.subject else None,
            days_to_deadline=(
                self._days_until(active_plan.target_date) if active_plan and active_plan.target_date else None
            ),
            yesterday_total=yesterday_stats["total"],
            yesterday_completed=yesterday_stats["completed"],
            completed_yesterday=yesterday_stats["completed_yesterday"],
            bottleneck=bottleneck,
            streak_days=streak_days,
            next_action_title=str((most_important_task or {}).get("title") or "").strip() or None,
        )

    async def _get_yesterday_task_completion(self, user_id: UUID, *, target_day: date) -> dict[str, int]:
        yesterday = target_day - timedelta(days=1)
        due_stmt = select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label("completed"),
        ).where(
            Task.user_id == user_id,
            Task.due_date == yesterday,
        )
        due_result = await self.db.execute(due_stmt)
        due_row = due_result.one()

        start = datetime.combine(yesterday, datetime.min.time())
        end = start + timedelta(days=1)
        completed_stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= start,
            Task.completed_at < end,
        )
        completed_result = await self.db.execute(completed_stmt)
        return {
            "total": int(due_row.total or 0),
            "completed": int(due_row.completed or 0),
            "completed_yesterday": int(completed_result.scalar() or 0),
        }

    async def _get_streak_stats_days(self, user_id: UUID) -> int:
        result = await self.db.execute(select(UserStreakStats.current_streak).where(UserStreakStats.user_id == user_id))
        value = result.scalar_one_or_none()
        if value is not None:
            return max(0, int(value or 0))
        return await self._get_current_streak_days(user_id)

    async def _generate_daily_context_line_with_ai(
        self,
        context: DailyContextLineContext,
        recent_lines: list[str],
    ) -> str | None:
        if not context.has_personal_data:
            return None

        facts = self._daily_context_payload(context)
        messages = [
            {
                "role": "system",
                "content": (
                    '你是 Sparkle 首页的晨间问候文案生成器。只输出 JSON：{"text":"..."}。'
                    "文案必须是中文 1 句话，像熟悉用户计划状态的朋友，不要鸡汤，不要编造事实。"
                    "如果有真实数据，必须自然引用至少一个给定数据点。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "根据这些事实写今天首页顶部的一句话：\n"
                    f"facts={facts}\n"
                    f"recent_lines={recent_lines[:5]}\n"
                    "要求：不超过 46 个汉字；不要和 recent_lines 重复；不要解释；不要使用列表。"
                ),
            },
        ]
        payload = await safe_llm_json_call(
            messages,
            fallback={},
            timeout=4.0,
            retry_count=0,
            temperature=0.35,
        )
        if not isinstance(payload, dict):
            return None
        text = payload.get("text")
        return str(text).strip() if text is not None else None

    def _rule_daily_context_line(
        self,
        context: DailyContextLineContext,
        recent_lines: list[str] | None = None,
        *,
        avoid_duplicates: bool = False,
    ) -> str:
        recent = recent_lines or []
        candidates = self._rule_daily_context_candidates(context)
        if avoid_duplicates:
            for candidate in candidates:
                cleaned = self._clean_context_line(candidate)
                if not self._is_recent_duplicate(cleaned, recent):
                    return cleaned

        index = context.target_day.toordinal() % max(len(candidates), 1)
        ordered = candidates[index:] + candidates[:index]
        for candidate in ordered:
            cleaned = self._clean_context_line(candidate)
            if not self._is_recent_duplicate(cleaned, recent):
                return cleaned
        return self._clean_context_line(candidates[0])

    def _rule_daily_context_candidates(self, context: DailyContextLineContext) -> list[str]:
        deadline = self._deadline_phrase(context)
        plan_label = context.subject or context.plan_name
        yesterday_label = self._yesterday_phrase(context)
        next_action = context.next_action_title
        bottleneck = context.bottleneck

        candidates: list[str] = []
        if deadline and bottleneck and next_action:
            candidates.append(f"{deadline}，今天先攻「{bottleneck}」，从「{next_action}」接着来。")
        if context.streak_days >= 3 and next_action:
            candidates.append(f"这 {context.streak_days} 天你节奏很稳，今天保持手感，先做「{next_action}」。")
        if yesterday_label and bottleneck:
            candidates.append(f"{yesterday_label}，今天把「{bottleneck}」补稳一点就很好。")
        if deadline and bottleneck:
            candidates.append(f"{deadline}，今天把「{bottleneck}」放到最前面，先稳住关键处。")
        if yesterday_label and next_action:
            candidates.append(f"{yesterday_label}，今天顺着「{next_action}」往前推进一小段。")
        if next_action:
            candidates.append(f"早上好，今天最值得先做的是「{next_action}」，我会陪你把它拆小。")
        if plan_label:
            candidates.append(f"早上好，今天继续推进「{plan_label}」，先做一个能带来确定感的小动作。")
        if context.streak_days > 0:
            candidates.append(f"你已经连续推进 {context.streak_days} 天，今天不用加速，稳稳接住节奏就好。")

        candidates.extend(
            [
                "早上好，今天先从一小步开始，把节奏找回来就很好。",
                "今天不用一口气解决所有事，先完成最清楚的那一步。",
                "早上好，给今天留一个轻量开头，后面的推进会自然很多。",
            ]
        )
        return candidates

    def _deadline_phrase(self, context: DailyContextLineContext) -> str | None:
        days = context.days_to_deadline
        if days is None:
            return None
        target = context.plan_name or context.subject or "目标日"
        if days == 0:
            return f"今天就是「{target}」目标日"
        if days > 0:
            return f"离「{target}」还有 {days} 天"
        return f"「{target}」目标日已经过去 {abs(days)} 天"

    @staticmethod
    def _yesterday_phrase(context: DailyContextLineContext) -> str | None:
        if context.yesterday_total > 0:
            return f"昨天完成了 {context.yesterday_completed}/{context.yesterday_total} 项"
        if context.completed_yesterday > 0:
            return f"昨天完成了 {context.completed_yesterday} 项任务"
        return None

    def _is_valid_context_line(
        self,
        text: str | None,
        context: DailyContextLineContext,
        recent_lines: list[str],
    ) -> bool:
        cleaned = self._clean_context_line(text)
        if not cleaned or self._is_recent_duplicate(cleaned, recent_lines):
            return False
        if len(cleaned) > 96:
            return False
        forbidden = ("作为AI", "作为 AI", "无法", "抱歉", "\n")
        if any(item in cleaned for item in forbidden):
            return False
        if not context.has_personal_data:
            return True
        return any(token and token in cleaned for token in self._context_reference_tokens(context))

    @staticmethod
    def _context_reference_tokens(context: DailyContextLineContext) -> list[str]:
        tokens = [
            context.plan_name,
            context.subject,
            context.bottleneck,
            context.next_action_title,
        ]
        if context.days_to_deadline is not None:
            tokens.extend([str(context.days_to_deadline), f"{context.days_to_deadline} 天"])
        if context.yesterday_total > 0:
            tokens.extend(
                [f"{context.yesterday_completed}/{context.yesterday_total}", str(context.yesterday_completed)]
            )
        if context.completed_yesterday > 0:
            tokens.append(str(context.completed_yesterday))
        if context.streak_days > 0:
            tokens.extend([str(context.streak_days), f"{context.streak_days} 天"])
        return [str(token).strip() for token in tokens if str(token or "").strip()]

    @classmethod
    def _clean_context_line(cls, text: str | None) -> str:
        cleaned = str(text or "").strip().strip("\"'“”‘’")
        cleaned = re.sub(r"\s+", "", cleaned)
        if not cleaned:
            return ""
        match = re.match(r"^(.+?[。！？!?])", cleaned)
        if match:
            cleaned = match.group(1)
        if cleaned[-1] not in "。！？!?":
            cleaned = f"{cleaned}。"
        return cleaned

    @classmethod
    def _is_recent_duplicate(cls, text: str, recent_lines: list[str]) -> bool:
        normalized = cls._normalize_context_line(text)
        return bool(normalized) and any(cls._normalize_context_line(line) == normalized for line in recent_lines)

    @staticmethod
    def _normalize_context_line(text: str) -> str:
        return re.sub(r"[，。！？!?,.\s「」\"'“”‘’]", "", str(text or "").lower())

    async def _get_recent_daily_context_lines(self, user_id: UUID) -> list[str]:
        cached = await cache_service.get(self._daily_context_recent_key(user_id))
        if not isinstance(cached, list):
            return []
        lines: list[str] = []
        for item in cached:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                lines.append(text)
        return lines[: self.DAILY_CONTEXT_RECENT_LIMIT]

    async def _remember_daily_context_line(self, user_id: UUID, text: str, target_day: date) -> None:
        recent = await cache_service.get(self._daily_context_recent_key(user_id))
        items = recent if isinstance(recent, list) else []
        normalized_new = self._normalize_context_line(text)
        next_items = [
            item
            for item in items
            if self._normalize_context_line(str((item or {}).get("text") if isinstance(item, dict) else item))
            != normalized_new
        ]
        next_items.insert(0, {"date": target_day.isoformat(), "text": text})
        await cache_service.set(
            self._daily_context_recent_key(user_id),
            next_items[: self.DAILY_CONTEXT_RECENT_LIMIT],
            ttl=self.DAILY_CONTEXT_RECENT_TTL_SECONDS,
        )

    @staticmethod
    def _daily_context_payload(context: DailyContextLineContext) -> dict[str, Any]:
        return {
            "date": context.target_day.isoformat(),
            "display_name": context.display_name,
            "plan_name": context.plan_name,
            "subject": context.subject,
            "days_to_deadline": context.days_to_deadline,
            "yesterday_total": context.yesterday_total,
            "yesterday_completed": context.yesterday_completed,
            "completed_yesterday": context.completed_yesterday,
            "bottleneck": context.bottleneck,
            "streak_days": context.streak_days,
            "next_action_title": context.next_action_title,
        }

    @staticmethod
    def _seconds_until_next_day(target_day: date) -> int:
        now = datetime.now()
        tomorrow = datetime.combine(target_day + timedelta(days=1), datetime.min.time())
        if tomorrow <= now:
            return 3600
        return max(3600, int((tomorrow - now).total_seconds()))

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
            headline = (
                f"{display_name}，上周你完成了 {tasks_completed} 个任务，在「{signal_label}」上也看到了真实进展。"
            )
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
        achievement_stories: list[str] | None = None,
    ) -> dict[str, Any] | None:
        achievement_stories = [story for story in (achievement_stories or []) if str(story).strip()]
        if not growth_signal and not growth_status and not achievement_stories:
            return None

        topic = str((growth_signal or {}).get("topic") or weakest_area or "").strip()
        highlights: list[str] = []
        highlights.extend(achievement_stories[:1])
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
            "task_id": str(most_important_task.get("id") or "").strip(),
            "estimated_minutes": int(most_important_task.get("estimated_minutes") or 0),
            "plan_name": plan_name or None,
            "days_to_deadline": most_important_task.get("days_to_deadline"),
        }

    @staticmethod
    def _build_active_bottleneck(weakest_area: str | None) -> dict[str, Any] | None:
        topic = str(weakest_area or "").strip()
        if not topic:
            return None
        return {
            "id": f"weakest:{topic}",
            "topic": topic,
            "severity": "high",
            "source": "knowledge_mastery",
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
            summary = f"{row.name} 掌握度从 {previous_mastery / 100:.2f} 提升到 {current_mastery / 100:.2f}"
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

    async def _get_plan_health(self, user_id: UUID, plan: Plan | None) -> PlanHealthReport | None:
        if plan is None:
            return None
        try:
            return await PlanProgressService(self.db).evaluate_progress(user_id, plan.id)
        except (SQLAlchemyError, TypeError, ValueError, AttributeError) as exc:
            logger.warning("Failed to evaluate plan health for user_id={} plan_id={}: {}", user_id, plan.id, exc)
            return None

    def _serialize_active_plan(
        self,
        plan: Plan | None,
        *,
        health: PlanHealthReport | None = None,
    ) -> dict[str, Any] | None:
        if plan is None:
            return None
        health_score = health.health_score if health else None
        return {
            "id": str(plan.id),
            "name": plan.name,
            "type": getattr(plan.type, "value", str(plan.type or "")),
            "phase": getattr(plan.plan_stage, "value", str(plan.plan_stage or "")),
            "progress": float(plan.progress or 0.0),
            "health_score": health_score,
            "health_status": health.severity if health else None,
            "health_reasons": list(health.reasons or []) if health else [],
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
