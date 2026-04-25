from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, UserAchievement, UserStreakStats
from app.models.cognitive import BehaviorPattern
from app.models.community import GroupTaskClaim, SharedResource
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class ProgressSnapshot:
    period: str
    highlights: list[str]
    comparisons: dict[str, dict[str, float | int]]
    streak_info: dict[str, int]
    growth_areas: list[str]
    attention_areas: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "highlights": self.highlights,
            "comparisons": self.comparisons,
            "streak_info": self.streak_info,
            "growth_areas": self.growth_areas,
            "attention_areas": self.attention_areas,
            "generated_at": self.generated_at,
        }


@dataclass
class WeeklyGrowthNarrative:
    period: str
    week_start: str
    week_end: str
    body: str
    sentences: list[str]
    data_points: dict[str, Any]
    source_counts: dict[str, int]
    is_placeholder: bool
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "week_start": self.week_start,
            "week_end": self.week_end,
            "body": self.body,
            "sentences": self.sentences,
            "data_points": self.data_points,
            "source_counts": self.source_counts,
            "is_placeholder": self.is_placeholder,
            "generated_at": self.generated_at,
        }


class ProgressNarrativeService:
    """Build cross-period growth snapshots from existing product signals."""

    LAST_SNAPSHOT_KEY = "progress_snapshot:last_generated:"
    ACHIEVEMENT_SIGNAL_KEY = "progress_snapshot:achievement_unlocks:"
    AUTO_INJECT_INTERVAL = timedelta(days=3)
    WEEKLY_NARRATIVE_KEY = "progress_narrative:weekly:"
    WEEKLY_CACHE_GRACE = timedelta(days=2)

    def __init__(self, db: AsyncSession, redis=None, cache=None):
        self.db = db
        self.redis = redis
        self.cache = cache

    async def build_snapshot(
        self,
        user_id: str,
        *,
        period_label: str = "本周",
        period_days: int = 7,
    ) -> ProgressSnapshot:
        now = _utcnow()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)

        task_current = await self._count_completed_tasks(user_id, current_start, now)
        task_previous = await self._count_completed_tasks(user_id, previous_start, current_start)

        mastery_current = await self._study_mastery_delta(user_id, current_start, now)
        mastery_previous = await self._study_mastery_delta(user_id, previous_start, current_start)

        achievements = await self.recent_achievement_story_lines(user_id, current_start, now)
        plan_progress = await self._plan_progress(user_id)
        group_stats = await self._group_contribution(user_id, current_start, now)
        streak = await self._streak_info(user_id)
        patterns = await self._pattern_shift(user_id, current_start, now)

        highlights: list[str] = []
        growth_areas: list[str] = []
        attention_areas: list[str] = []

        task_delta = task_current - task_previous
        if task_current > 0:
            if task_previous > 0:
                highlights.append(f"你这周完成了 {task_current} 个任务，比上周多 {task_delta} 个。")
            else:
                highlights.append(f"你这周完成了 {task_current} 个任务，重新把执行节奏拉起来了。")
            growth_areas.append("任务执行")

        mastery_nodes = mastery_current["nodes"]
        mastery_delta = mastery_current["delta"]
        if mastery_nodes > 0 or mastery_delta > 0:
            highlights.append(f"最近 7 天你在 {mastery_nodes} 个知识点上有推进，累计掌握度提升约 {mastery_delta:.1f}。")
            growth_areas.append("知识掌握")

        if streak["current_streak"] > 0:
            highlights.append(
                f"你已经连续学习 {streak['current_streak']} 天，目前最长记录是 {streak['max_streak']} 天。"
            )
            growth_areas.append("连续性")

        if achievements:
            highlights.append(achievements[0])
            growth_areas.append("成就里程碑")

        if group_stats["completed_claims"] > 0 or group_stats["shared_nodes"] > 0:
            highlights.append(
                f"你在群组里完成了 {group_stats['completed_claims']} 个协作任务，分享了 {group_stats['shared_nodes']} 次知识节点。"
            )
            growth_areas.append("群组贡献")

        if task_current == 0 and plan_progress["active_plan_count"] > 0:
            attention_areas.append("本周活跃计划仍在推进中，但任务完成数偏低。")
        if mastery_previous["delta"] > mastery_delta and mastery_previous["delta"] > 0:
            attention_areas.append("知识掌握推进速度比上一周期慢了一些。")
        if patterns["new_patterns"]:
            attention_areas.append(f"最近出现了新的阻力模式：{patterns['new_patterns'][0]}。")
        if patterns["archived_patterns"]:
            growth_areas.append(f"已弱化的模式：{patterns['archived_patterns'][0]}")

        if not highlights:
            highlights.append("最近几天你的节奏还比较平，先把下一次完成动作稳住最重要。")
        return ProgressSnapshot(
            period=period_label,
            highlights=highlights[:3],
            comparisons={
                "tasks_completed": {"current": task_current, "previous": task_previous},
                "mastery_delta": {"current": round(mastery_delta, 2), "previous": round(mastery_previous["delta"], 2)},
                "group_contributions": {
                    "current": group_stats["completed_claims"] + group_stats["shared_nodes"],
                    "previous": group_stats["previous_contributions"],
                },
                "active_plan_progress": {
                    "current": round(plan_progress["average_progress"], 2),
                    "previous": round(plan_progress["previous_average_progress"], 2),
                },
            },
            streak_info=streak,
            growth_areas=growth_areas[:3],
            attention_areas=attention_areas[:3],
            generated_at=now.isoformat(),
        )

    async def maybe_get_lightweight_snapshot(self, user_id: str) -> dict[str, Any] | None:
        if not await self._should_refresh(user_id):
            return None
        snapshot = await self.build_snapshot(user_id, period_label="最近7天", period_days=7)
        await self._mark_generated(user_id)
        return snapshot.to_dict()

    async def get_weekly_narrative(
        self,
        user_id: str | UUID,
        *,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return the current Monday-based growth story, generating it once per week."""
        generated_at = now or _utcnow()
        week_start, week_end = self._week_bounds(generated_at)
        cache_key = self._weekly_cache_key(user_id, week_start)

        if not force:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, dict):
                return cached

        narrative = await self.build_weekly_narrative(
            user_id,
            week_start=week_start,
            week_end=week_end,
            generated_at=generated_at,
        )
        payload = narrative.to_dict()
        await self._cache_set(cache_key, payload, ttl=self._weekly_cache_ttl(generated_at, week_end))
        return payload

    async def build_weekly_narrative(
        self,
        user_id: str | UUID,
        *,
        week_start: datetime | None = None,
        week_end: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> WeeklyGrowthNarrative:
        now = generated_at or _utcnow()
        start, end = (week_start, week_end) if week_start and week_end else self._week_bounds(now)

        tasks = await self._completed_task_details(user_id, start, end)
        errors = await self._error_record_summary(user_id, start, end)
        reflections = await self._reflection_summary(user_id, start, end)
        mastery = await self._mastery_progress_summary(user_id, start, end)
        achievements = await self.recent_achievement_story_lines(str(user_id), start, end)

        data_points = {
            "tasks_completed": tasks["count"],
            "task_titles": tasks["titles"],
            "task_minutes": tasks["minutes"],
            "achievement_stories": achievements,
            "achievement_count": len(achievements),
            "error_records": errors["count"],
            "error_focus": errors["focus"],
            "error_causes": errors["causes"],
            "reflection_records": reflections["count"],
            "reflection_snippets": reflections["snippets"],
            "mastery_delta": round(float(mastery["delta"]), 2),
            "mastery_nodes": mastery["nodes"],
        }
        source_counts = {
            "task_completions": int(tasks["count"]),
            "error_records": int(errors["count"]),
            "reflection_records": int(reflections["count"]),
            "mastery_changes": int(mastery["record_count"]),
            "achievement_unlocks": len(achievements),
        }

        has_data = any(source_counts.values()) or float(mastery["delta"]) > 0
        if not has_data:
            sentences = [
                "这是你的第一周，先开始吧。",
                "完成一次学习任务、记录一道错题，或者写下一句复盘后，这里就会开始把你的成长线索连起来。",
            ]
            is_placeholder = True
        else:
            sentences = self._compose_weekly_story(tasks, errors, reflections, mastery, achievements)
            is_placeholder = False

        return WeeklyGrowthNarrative(
            period="本周成长故事",
            week_start=start.date().isoformat(),
            week_end=(end - timedelta(days=1)).date().isoformat(),
            body="".join(sentences),
            sentences=sentences,
            data_points=data_points,
            source_counts=source_counts,
            is_placeholder=is_placeholder,
            generated_at=now.isoformat(),
        )

    async def _should_refresh(self, user_id: str) -> bool:
        if not self.redis:
            return True
        key = f"{self.LAST_SNAPSHOT_KEY}{user_id}"
        try:
            raw = await self.redis.get(key)
            if not raw:
                return True
            return (float(raw) + self.AUTO_INJECT_INTERVAL.total_seconds()) <= _utcnow().timestamp()
        except Exception as exc:
            logger.warning(f"Failed to read progress snapshot freshness: {exc}")
            return True

    async def _mark_generated(self, user_id: str) -> None:
        if not self.redis:
            return
        key = f"{self.LAST_SNAPSHOT_KEY}{user_id}"
        try:
            await self.redis.setex(key, int(self.AUTO_INJECT_INTERVAL.total_seconds()), str(_utcnow().timestamp()))
        except Exception as exc:
            logger.warning(f"Failed to persist progress snapshot freshness: {exc}")

    async def record_achievement_unlock_signal(
        self,
        *,
        user_id: str,
        achievement_id: str,
        achievement_name: str,
        unlocked_at: datetime | str | None,
        context_snapshot: dict[str, Any] | None = None,
        is_first: bool = False,
    ) -> None:
        """Keep a lightweight achievement unlock signal for growth-story consumers."""
        if not self.redis:
            return
        payload = {
            "achievement_id": achievement_id,
            "achievement_name": achievement_name,
            "unlocked_at": unlocked_at.isoformat() if isinstance(unlocked_at, datetime) else unlocked_at,
            "context_snapshot": context_snapshot or {},
            "is_first": is_first,
            "recorded_at": _utcnow().isoformat(),
        }
        key = f"{self.ACHIEVEMENT_SIGNAL_KEY}{user_id}"
        try:
            await self.redis.lpush(key, json.dumps(payload, ensure_ascii=False, default=str))
            await self.redis.ltrim(key, 0, 49)
            await self.redis.expire(key, 86400 * 45)
        except Exception as exc:
            logger.warning(f"Failed to persist achievement narrative signal: {exc}")

    async def _count_completed_tasks(self, user_id: str, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= start,
                Task.completed_at < end,
            )
        )
        return int(result.scalar() or 0)

    async def _completed_task_details(
        self,
        user_id: str | UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        count = await self._count_completed_tasks(str(user_id), start, end)
        result = await self.db.execute(
            select(Task.title, Task.actual_minutes, Task.tags, Task.completed_at)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= start,
                Task.completed_at < end,
            )
            .order_by(desc(Task.completed_at))
            .limit(12)
        )
        rows = result.all()
        titles: list[str] = []
        tag_counter: Counter[str] = Counter()
        minutes = 0
        for title, actual_minutes, tags, _completed_at in rows:
            title_text = self._clean_text(title)
            if title_text and title_text not in titles:
                titles.append(title_text)
            minutes += int(actual_minutes or 0)
            if isinstance(tags, list):
                for tag in tags:
                    tag_text = self._clean_text(tag)
                    if tag_text:
                        tag_counter[tag_text] += 1
        return {
            "count": count,
            "titles": titles[:3],
            "tags": [tag for tag, _count in tag_counter.most_common(3)],
            "minutes": minutes,
        }

    async def _study_mastery_delta(self, user_id: str, start: datetime, end: datetime) -> dict[str, float | int]:
        result = await self.db.execute(
            select(
                func.count(func.distinct(StudyRecord.node_id)),
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0),
            ).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= start,
                StudyRecord.created_at < end,
                StudyRecord.mastery_delta > 0,
            )
        )
        nodes, delta = result.one()
        return {"nodes": int(nodes or 0), "delta": float(delta or 0.0)}

    async def _mastery_progress_summary(
        self,
        user_id: str | UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        aggregate = await self._study_mastery_delta(str(user_id), start, end)
        delta_sum = func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0).label("delta")
        record_count = func.count(StudyRecord.id).label("record_count")
        result = await self.db.execute(
            select(
                KnowledgeNode.name,
                delta_sum,
                record_count,
            )
            .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
            .where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= start,
                StudyRecord.created_at < end,
                StudyRecord.mastery_delta > 0,
            )
            .group_by(KnowledgeNode.name)
            .order_by(desc(delta_sum))
            .limit(5)
        )
        rows = result.all()
        return {
            "nodes": [self._clean_text(name) for name, _delta, _record_count in rows if self._clean_text(name)],
            "delta": float(aggregate["delta"]),
            "node_count": int(aggregate["nodes"]),
            "record_count": sum(int(record_count or 0) for _name, _delta, record_count in rows),
        }

    async def _error_record_summary(
        self,
        user_id: str | UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(
                ErrorRecord.subject_code,
                ErrorRecord.chapter,
                ErrorRecord.latest_analysis,
                ErrorRecord.ai_analysis_summary,
            )
            .where(
                ErrorRecord.user_id == self._uuid_or_original(user_id),
                ErrorRecord.created_at >= start,
                ErrorRecord.created_at < end,
                ErrorRecord.is_deleted.is_(False),
            )
            .order_by(desc(ErrorRecord.created_at))
            .limit(20)
        )
        rows = result.all()
        focus_counter: Counter[str] = Counter()
        causes: list[str] = []
        for subject_code, chapter, latest_analysis, ai_analysis_summary in rows:
            focus = self._clean_text(chapter) or self._clean_text(subject_code)
            if focus:
                focus_counter[focus] += 1
            if isinstance(latest_analysis, dict):
                cause = (
                    self._clean_text(latest_analysis.get("root_cause"))
                    or self._clean_text(latest_analysis.get("error_type"))
                    or self._clean_text(latest_analysis.get("diagnosis"))
                )
                if cause and cause not in causes:
                    causes.append(cause)
            summary = self._clean_text(ai_analysis_summary)
            if summary and summary not in causes:
                causes.append(self._shorten(summary, 42))
        return {
            "count": len(rows),
            "focus": [focus for focus, _count in focus_counter.most_common(3)],
            "causes": causes[:3],
        }

    async def _reflection_summary(
        self,
        user_id: str | UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(TaskFeedback.category, TaskFeedback.feedback_text, TaskFeedback.reflection_payload)
            .where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.created_at >= start,
                TaskFeedback.created_at < end,
                TaskFeedback.reflection_payload.is_not(None),
            )
            .order_by(desc(TaskFeedback.created_at))
            .limit(10)
        )
        rows = result.all()
        snippets: list[str] = []
        categories: Counter[str] = Counter()
        for category, feedback_text, reflection_payload in rows:
            category_text = self._clean_text(category)
            if category_text:
                categories[category_text] += 1
            payload = reflection_payload if isinstance(reflection_payload, dict) else {}
            snippet = (
                self._clean_text(payload.get("free_text"))
                or self._clean_text(payload.get("selected_option"))
                or self._clean_text(feedback_text)
            )
            if snippet and snippet not in snippets:
                snippets.append(self._shorten(snippet, 42))
        return {
            "count": len(rows),
            "snippets": snippets[:3],
            "categories": [category for category, _count in categories.most_common(3)],
        }

    async def recent_achievement_story_lines(self, user_id: str, start: datetime, end: datetime) -> list[str]:
        result = await self.db.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, Achievement.id == UserAchievement.achievement_id)
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.is_not(None),
                UserAchievement.unlocked_at >= start,
                UserAchievement.unlocked_at < end,
            )
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(3)
        )
        return [
            self._achievement_story_line(user_achievement, achievement)
            for user_achievement, achievement in result.all()
        ]

    def _achievement_story_line(
        self,
        user_achievement: UserAchievement,
        achievement: Achievement,
    ) -> str:
        snapshot = user_achievement.context_snapshot if isinstance(user_achievement.context_snapshot, dict) else {}
        first_clause = (
            "，这是你第一次做到"
            if bool(user_achievement.is_first_unlocker or snapshot.get("is_first_unlocker"))
            else ""
        )
        context_bits: list[str] = []

        plan = snapshot.get("current_plan") if isinstance(snapshot.get("current_plan"), dict) else {}
        task = snapshot.get("task") if isinstance(snapshot.get("task"), dict) else {}
        plan_name = self._clean_text(plan.get("name"))
        task_title = self._clean_text(task.get("title"))
        days_to_target = plan.get("days_to_target")
        if plan_name and isinstance(days_to_target, int):
            if days_to_target >= 0:
                context_bits.append(f"发生在「{plan_name}」目标日前 {days_to_target} 天")
            else:
                context_bits.append(f"发生在「{plan_name}」目标日后 {abs(days_to_target)} 天")
        elif plan_name:
            context_bits.append(f"当时你正在推进「{plan_name}」")
        if task_title:
            context_bits.append(f"任务是「{task_title}」")

        suffix = f"。{'，'.join(context_bits)}。" if context_bits else "。"
        return f"这周你解锁了「{achievement.name}」{first_clause}{suffix}"

    async def _plan_progress(self, user_id: str) -> dict[str, float | int]:
        current = await self.db.execute(
            select(
                func.count(Plan.id),
                func.coalesce(func.avg(Plan.progress), 0.0),
            ).where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
        )
        count, average = current.one()
        previous = await self.db.execute(
            select(func.coalesce(func.avg(Plan.progress), 0.0)).where(
                Plan.user_id == user_id,
                Plan.updated_at < (_utcnow() - timedelta(days=7)),
            )
        )
        return {
            "active_plan_count": int(count or 0),
            "average_progress": float(average or 0.0),
            "previous_average_progress": float(previous.scalar() or 0.0),
        }

    async def _group_contribution(self, user_id: str, start: datetime, end: datetime) -> dict[str, int]:
        current_claims = await self.db.execute(
            select(func.count(GroupTaskClaim.id)).where(
                GroupTaskClaim.user_id == user_id,
                GroupTaskClaim.is_completed.is_(True),
                GroupTaskClaim.completed_at >= start,
                GroupTaskClaim.completed_at < end,
            )
        )
        current_shares = await self.db.execute(
            select(func.count(SharedResource.id)).where(
                SharedResource.shared_by == user_id,
                SharedResource.knowledge_node_id.is_not(None),
                SharedResource.created_at >= start,
                SharedResource.created_at < end,
            )
        )
        previous_start = start - (end - start)
        prev_claims = await self.db.execute(
            select(func.count(GroupTaskClaim.id)).where(
                GroupTaskClaim.user_id == user_id,
                GroupTaskClaim.is_completed.is_(True),
                GroupTaskClaim.completed_at >= previous_start,
                GroupTaskClaim.completed_at < start,
            )
        )
        prev_shares = await self.db.execute(
            select(func.count(SharedResource.id)).where(
                SharedResource.shared_by == user_id,
                SharedResource.knowledge_node_id.is_not(None),
                SharedResource.created_at >= previous_start,
                SharedResource.created_at < start,
            )
        )
        return {
            "completed_claims": int(current_claims.scalar() or 0),
            "shared_nodes": int(current_shares.scalar() or 0),
            "previous_contributions": int(prev_claims.scalar() or 0) + int(prev_shares.scalar() or 0),
        }

    async def _streak_info(self, user_id: str) -> dict[str, int]:
        result = await self.db.execute(select(UserStreakStats).where(UserStreakStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        if not stats:
            return {"current_streak": 0, "max_streak": 0, "total_checkin_days": 0}
        return {
            "current_streak": int(stats.current_streak or 0),
            "max_streak": int(stats.max_streak or stats.longest_streak or 0),
            "total_checkin_days": int(stats.total_checkin_days or 0),
        }

    async def _pattern_shift(self, user_id: str, start: datetime, end: datetime) -> dict[str, list[str]]:
        new_patterns_result = await self.db.execute(
            select(BehaviorPattern.pattern_name)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.created_at >= start,
                BehaviorPattern.created_at < end,
                BehaviorPattern.is_archived.is_(False),
                BehaviorPattern.confidence_score >= 0.7,
            )
            .limit(3)
        )
        archived_patterns_result = await self.db.execute(
            select(BehaviorPattern.pattern_name)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.updated_at >= start,
                BehaviorPattern.updated_at < end,
                BehaviorPattern.is_archived.is_(True),
            )
            .limit(3)
        )
        return {
            "new_patterns": [str(item) for item in new_patterns_result.scalars().all()],
            "archived_patterns": [str(item) for item in archived_patterns_result.scalars().all()],
        }

    def _compose_weekly_story(
        self,
        tasks: dict[str, Any],
        errors: dict[str, Any],
        reflections: dict[str, Any],
        mastery: dict[str, Any],
        achievements: list[str] | None = None,
    ) -> list[str]:
        sentences: list[str] = []
        achievements = achievements or []
        focus = self._primary_focus(tasks, errors, mastery)
        task_count = int(tasks["count"])
        error_count = int(errors["count"])
        reflection_count = int(reflections["count"])
        mastery_delta = float(mastery["delta"])
        mastery_nodes = list(mastery["nodes"])

        if focus and task_count > 0:
            minutes_text = f"，实际投入了 {tasks['minutes']} 分钟" if int(tasks["minutes"]) > 0 else ""
            sentences.append(f"这周你主要把力气放在{focus}上，完成了 {task_count} 个任务{minutes_text}。")
        elif task_count > 0:
            title = tasks["titles"][0] if tasks["titles"] else "学习任务"
            sentences.append(f"这周你完成了 {task_count} 个任务，最近收尾的是《{title}》。")
        elif focus:
            sentences.append(f"这周的线索集中在{focus}，虽然任务完成数还不多，但方向已经露出来了。")

        if error_count > 0:
            error_focus = self._format_list(errors["focus"]) or "最近练习"
            cause_text = f"，最常见的信号是「{errors['causes'][0]}」" if errors["causes"] else ""
            sentences.append(f"卡点也很具体：{error_focus}留下了 {error_count} 条错题{cause_text}，先把这里拆小就好。")

        if mastery_delta > 0:
            node_text = self._format_list(mastery_nodes) or f"{mastery['node_count']} 个知识点"
            sentences.append(f"好消息是，{node_text}的掌握度累计往前推了 {mastery_delta:.1f}，这就是这周最清楚的突破。")

        if achievements:
            sentences.append(achievements[0])

        if reflection_count > 0:
            snippet = reflections["snippets"][0] if reflections["snippets"] else None
            if snippet:
                sentences.append(
                    f"你还做了 {reflection_count} 次复盘，里面那句「{snippet}」可以留着，下次卡住时直接拿来试。"
                )
            else:
                sentences.append(f"你还做了 {reflection_count} 次复盘，这些小结会帮下周少走一点弯路。")

        if len(sentences) < 3 and task_count > 0:
            title = tasks["titles"][0] if tasks["titles"] else "刚完成的任务"
            sentences.append(f"先记住《{title}》这次推进的节奏：完成后马上补一小句复盘，比攒到周末更有效。")

        if len(sentences) < 3 and error_count == 0 and mastery_delta > 0:
            sentences.append("这周暂时没有新的错题信号，说明你可以把注意力放在巩固和迁移上。")

        if len(sentences) < 3:
            sentences.append("下周继续用一次任务、一次错题、一次复盘来给自己留下清楚的路标。")

        return sentences[:4]

    def _primary_focus(
        self,
        tasks: dict[str, Any],
        errors: dict[str, Any],
        mastery: dict[str, Any],
    ) -> str:
        for candidates in (mastery["nodes"], errors["focus"], tasks["tags"], tasks["titles"]):
            if candidates:
                return self._format_list(candidates[:2])
        return ""

    def _format_list(self, values: list[Any]) -> str:
        cleaned = [self._shorten(self._clean_text(value), 18) for value in values if self._clean_text(value)]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        return "、".join(cleaned[:2])

    def _week_bounds(self, now: datetime) -> tuple[datetime, datetime]:
        week_start_date = now.date() - timedelta(days=now.weekday())
        week_start = datetime.combine(week_start_date, time.min)
        return week_start, week_start + timedelta(days=7)

    def _weekly_cache_key(self, user_id: str | UUID, week_start: datetime) -> str:
        return f"{self.WEEKLY_NARRATIVE_KEY}{user_id}:{week_start.date().isoformat()}"

    def _weekly_cache_ttl(self, now: datetime, week_end: datetime) -> int:
        expires_at = week_end + self.WEEKLY_CACHE_GRACE
        return max(int((expires_at - now).total_seconds()), 3600)

    async def _cache_get(self, key: str) -> Any | None:
        if self.cache is not None:
            try:
                return await self.cache.get(key)
            except Exception as exc:
                logger.warning(f"Failed to read weekly progress narrative cache: {exc}")
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:
            logger.warning(f"Failed to read weekly progress narrative redis key: {exc}")
            return None

    async def _cache_set(self, key: str, value: dict[str, Any], *, ttl: int) -> None:
        if self.cache is not None:
            try:
                await self.cache.set(key, value, ttl=ttl)
                return
            except Exception as exc:
                logger.warning(f"Failed to write weekly progress narrative cache: {exc}")
        if self.redis is None:
            return
        try:
            await self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=True))
        except Exception as exc:
            logger.warning(f"Failed to write weekly progress narrative redis key: {exc}")

    def _uuid_or_original(self, value: str | UUID) -> str | UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return value

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _shorten(self, value: str, limit: int) -> str:
        text = value.strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit]}..."
