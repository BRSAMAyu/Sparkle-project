from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    PERCEPTIBLE_INSIGHT_CANDIDATE_TOTAL,
    PERCEPTIBLE_INSIGHT_SENT_TOTAL,
    PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL,
    PROGRESS_COMPARISON_GENERATED_TOTAL,
    PROGRESS_COMPARISON_SKIPPED_TOTAL,
    WEEKLY_LEARNING_REPORT_GENERATED_TOTAL,
    WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL,
)
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import StudyRecord
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.plan_progress_service import PlanProgressService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class InsightCandidate:
    scenario: str
    pattern: BehaviorPattern | None
    title: str
    description: str
    evidence_summary: str
    recommended_action: dict[str, Any] | None
    confidence: float
    pattern_type: str


class ProgressComparisonService:
    """Build comparable progress narratives from same-domain evidence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_best_comparison(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None = None,
        period_days: int = 7,
    ) -> dict[str, Any] | None:
        sources = [
            await self._build_mastery_comparison(user_id=user_id, period_days=period_days),
            await self._build_task_duration_comparison(user_id=user_id, plan_id=plan_id, period_days=period_days),
            await self._build_plan_progress_comparison(user_id=user_id),
        ]
        candidates = [item for item in sources if isinstance(item, dict)]
        if not candidates:
            PROGRESS_COMPARISON_SKIPPED_TOTAL.labels(reason="no_comparable_evidence").inc()
            return None
        candidate = max(candidates, key=lambda item: float(item.get("score") or 0.0))
        PROGRESS_COMPARISON_GENERATED_TOTAL.labels(source=str(candidate.get("source") or "unknown")).inc()
        return {k: v for k, v in candidate.items() if k != "score"}

    async def _build_mastery_comparison(
        self,
        *,
        user_id: UUID,
        period_days: int,
    ) -> dict[str, Any] | None:
        now = _utcnow()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)

        current_rows = await self.db.execute(
            select(StudyRecord).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= current_start,
                StudyRecord.created_at < now,
                StudyRecord.mastery_delta > 0,
            )
        )
        previous_rows = await self.db.execute(
            select(StudyRecord).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= previous_start,
                StudyRecord.created_at < current_start,
                StudyRecord.mastery_delta > 0,
            )
        )
        current = list(current_rows.scalars().all())
        previous = list(previous_rows.scalars().all())
        current_delta = sum(float(item.mastery_delta or 0.0) for item in current)
        previous_delta = sum(float(item.mastery_delta or 0.0) for item in previous)
        if current_delta <= 0 and previous_delta <= 0:
            return None
        if abs(current_delta - previous_delta) < 5:
            return None
        return {
            "source": "mastery",
            "before_label": "上一周期掌握度提升",
            "before_value": f"{previous_delta:.1f}",
            "after_label": "最近7天掌握度提升",
            "after_value": f"{current_delta:.1f}",
            "delta_text": (
                f"最近 7 天你的掌握度提升约 {current_delta:.1f}，"
                f"相比上一周期{'更快' if current_delta >= previous_delta else '更稳'}。"
            ),
            "why_it_matters": "这说明你最近的学习吸收效率出现了可感知变化。",
            "score": abs(current_delta - previous_delta),
        }

    async def _build_task_duration_comparison(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None,
        period_days: int,
    ) -> dict[str, Any] | None:
        now = _utcnow()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)
        stmt = select(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.actual_minutes.is_not(None),
            Task.completed_at.is_not(None),
        )
        if plan_id:
            stmt = stmt.where(Task.plan_id == plan_id)
        current_rows = await self.db.execute(
            stmt.where(Task.completed_at >= current_start, Task.completed_at < now)
        )
        previous_rows = await self.db.execute(
            stmt.where(Task.completed_at >= previous_start, Task.completed_at < current_start)
        )
        current = list(current_rows.scalars().all())
        previous = list(previous_rows.scalars().all())
        if not current or not previous:
            return None
        current_avg = sum(int(item.actual_minutes or 0) for item in current) / max(len(current), 1)
        previous_avg = sum(int(item.actual_minutes or 0) for item in previous) / max(len(previous), 1)
        if abs(current_avg - previous_avg) < 5:
            return None
        improved = current_avg < previous_avg
        return {
            "source": "task_duration",
            "before_label": "上一周期平均完成时长",
            "before_value": f"{previous_avg:.0f} 分钟",
            "after_label": "最近7天平均完成时长",
            "after_value": f"{current_avg:.0f} 分钟",
            "delta_text": (
                f"同类任务的平均完成时长从 {previous_avg:.0f} 分钟变成 {current_avg:.0f} 分钟。"
            ),
            "why_it_matters": "这意味着你处理同类任务的节奏在变得更顺手。" if improved else "这说明当前节奏开始变重，值得及时调轻任务负担。",
            "score": abs(current_avg - previous_avg),
        }

    async def _build_plan_progress_comparison(self, *, user_id: UUID) -> dict[str, Any] | None:
        current_rows = await self.db.execute(
            select(Plan).where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
        )
        current_plans = list(current_rows.scalars().all())
        if not current_plans:
            return None
        current_avg = sum(float(plan.progress or 0.0) for plan in current_plans) / max(len(current_plans), 1)
        previous_rows = await self.db.execute(
            select(Plan).where(
                Plan.user_id == user_id,
                Plan.updated_at < (_utcnow() - timedelta(days=7)),
            )
        )
        previous_plans = list(previous_rows.scalars().all())
        if not previous_plans:
            return None
        previous_avg = sum(float(plan.progress or 0.0) for plan in previous_plans) / max(len(previous_plans), 1)
        if abs(current_avg - previous_avg) < 0.1:
            return None
        return {
            "source": "plan_progress",
            "before_label": "之前计划平均进度",
            "before_value": f"{previous_avg:.0%}",
            "after_label": "当前计划平均进度",
            "after_value": f"{current_avg:.0%}",
            "delta_text": f"你的活跃计划平均进度从 {previous_avg:.0%} 走到了 {current_avg:.0%}。",
            "why_it_matters": "这能直接反映出计划推进是否开始更贴合你的真实节奏。",
            "score": abs(current_avg - previous_avg) * 100,
        }


class PerceptibleInsightService:
    """Turn behavioral patterns into user-visible insights with cooldown."""

    COOLDOWN_HOURS = 72
    RECENT_PATTERN_DAYS = 21

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.system_updates = SystemUpdateService(redis)
        self.progress_service = PlanProgressService(db, redis)

    async def maybe_enqueue_session_insight(
        self,
        *,
        user_id: UUID | str,
        user_message: str,
        context_focus: dict[str, Any] | None = None,
        plan_id: UUID | str | None = None,
        progress_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not (settings.ENABLE_PERCEPTIBLE_INTELLIGENCE and settings.ENABLE_PROACTIVE_INSIGHTS):
            return None
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        scenario = self._detect_scenario(user_message=user_message, context_focus=context_focus)
        PERCEPTIBLE_INSIGHT_CANDIDATE_TOTAL.labels(scenario=scenario).inc()

        candidate = await self._build_candidate(
            user_id=user_uuid,
            scenario=scenario,
            plan_id=plan_id,
            progress_snapshot=progress_snapshot,
        )
        if candidate is None:
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="no_candidate").inc()
            return None
        if await self._on_cooldown(user_uuid, scenario, candidate.pattern.id if candidate.pattern else None):
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="cooldown").inc()
            return None
        payload = build_system_update(
            update_type="perceptible_insight",
            category="evolution",
            title=candidate.title,
            description=candidate.description,
            priority="medium",
            metadata={
                "evolution_kind": "proactive_insight",
                "headline": candidate.title,
                "insight_text": candidate.description,
                "evidence_summary": candidate.evidence_summary,
                "recommended_action": candidate.recommended_action,
                "confidence": round(candidate.confidence, 2),
                "cooldown_until": (
                    _utcnow() + timedelta(hours=self.COOLDOWN_HOURS)
                ).isoformat(),
                "pattern_type": candidate.pattern_type,
                "pattern_id": str(candidate.pattern.id) if candidate.pattern else "",
                "scenario": scenario,
            },
        )
        await self.system_updates.enqueue(user_uuid, payload)
        await self._mark_sent(user_uuid, scenario, candidate.pattern.id if candidate.pattern else None)
        PERCEPTIBLE_INSIGHT_SENT_TOTAL.labels(pattern_type=candidate.pattern_type or "unknown").inc()
        return payload

    async def _build_candidate(
        self,
        *,
        user_id: UUID,
        scenario: str,
        plan_id: UUID | str | None,
        progress_snapshot: dict[str, Any] | None,
    ) -> InsightCandidate | None:
        patterns = await self._eligible_patterns(user_id)
        for pattern in patterns:
            if self._pattern_matches_scenario(pattern, scenario):
                return self._pattern_candidate(pattern=pattern, scenario=scenario)

        if scenario == "plan_adjustment" and plan_id:
            try:
                report = await self.progress_service.evaluate_progress(
                    user_id=user_id,
                    plan_id=plan_id if isinstance(plan_id, UUID) else UUID(str(plan_id)),
                )
            except Exception as exc:
                logger.warning(f"Failed to evaluate plan progress for insight: {exc}")
                report = None
            if report and report.requires_adjustment:
                reasons = "、".join(report.reasons[:2]) or "最近执行摩擦增加"
                return InsightCandidate(
                    scenario=scenario,
                    pattern=None,
                    title="我发现这个计划最近开始有点顶住你了",
                    description="从最近的执行节奏看，这个计划已经不像一开始那样顺手，值得现在就调轻一点。",
                    evidence_summary=f"触发依据：{reasons}；当前建议动作：{report.recommended_action}",
                    recommended_action={
                        "label": "帮我调整计划",
                        "type": "prompt",
                        "payload": {"prompt": "根据我最近的执行情况，帮我把这个计划调轻一点"},
                        "style": "primary",
                        "reason_key": "plan_adjustment",
                    },
                    confidence=0.82,
                    pattern_type="progress",
                )

        if isinstance(progress_snapshot, dict):
            highlights = [str(item).strip() for item in (progress_snapshot.get("attention_areas") or []) if str(item).strip()]
            if highlights:
                return InsightCandidate(
                    scenario=scenario,
                    pattern=None,
                    title="我从你最近的节奏里看到一个值得提前处理的点",
                    description=highlights[0],
                    evidence_summary="这条提醒来自你最近 7 天的进度快照，而不是单次对话印象。",
                    recommended_action={
                        "label": "结合这个提醒调整一下",
                        "type": "prompt",
                        "payload": {"prompt": "根据你刚才的提醒，帮我给出一个更稳的下一步安排"},
                        "style": "primary",
                        "reason_key": "snapshot_adjustment",
                    },
                    confidence=0.76,
                    pattern_type="progress_snapshot",
                )
        return None

    async def _eligible_patterns(self, user_id: UUID) -> list[BehaviorPattern]:
        cutoff = _utcnow() - timedelta(days=self.RECENT_PATTERN_DAYS)
        result = await self.db.execute(
            select(BehaviorPattern)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.confidence_score >= 0.8,
                BehaviorPattern.frequency >= 3,
                BehaviorPattern.is_archived.is_(False),
                or_(
                    BehaviorPattern.last_observed_at.is_(None),
                    BehaviorPattern.last_observed_at >= cutoff,
                ),
            )
            .order_by(BehaviorPattern.confidence_score.desc(), BehaviorPattern.frequency.desc())
            .limit(10)
        )
        return list(result.scalars().all())

    def _detect_scenario(self, *, user_message: str, context_focus: dict[str, Any] | None) -> str:
        text = str(user_message or "").strip().lower()
        focus_mode = str((context_focus or {}).get("focus_mode") or "").strip().lower()
        now_hour = datetime.now().hour
        if any(token in text for token in ("计划", "安排", "复习", "调整")) or focus_mode == "plan_focus":
            return "plan_adjustment"
        if any(token in text for token in ("拖延", "不想做", "开始不了", "拖着", "拖到")):
            return "procrastination"
        if any(token in text for token in ("来不及", "做不完", "超时", "总是拖很久", "太久")):
            return "repeated_timeout"
        if any(token in text for token in ("晚上", "夜里", "熬夜", "十点", "十一点")) or now_hour >= 22 or now_hour < 6:
            return "late_night"
        return "general"

    def _pattern_matches_scenario(self, pattern: BehaviorPattern, scenario: str) -> bool:
        haystack = " ".join(
            [
                str(pattern.pattern_name or ""),
                str(pattern.description or ""),
                str(pattern.solution_text or ""),
                str(pattern.pattern_type or ""),
            ]
        ).lower()
        keyword_map = {
            "late_night": ("晚", "夜", "熬夜", "睡", "深夜"),
            "plan_adjustment": ("计划", "安排", "节奏", "复习"),
            "procrastination": ("拖延", "启动", "开始", "抗拒"),
            "repeated_timeout": ("超时", "时间", "拖长", "来不及", "做不完"),
            "general": (),
        }
        keywords = keyword_map.get(scenario, ())
        if not keywords:
            return True
        return any(keyword in haystack for keyword in keywords)

    def _pattern_candidate(self, *, pattern: BehaviorPattern, scenario: str) -> InsightCandidate:
        action_prompt = {
            "late_night": "根据我最近晚间学习的状态，帮我把明天的任务安排到更容易完成的时段",
            "plan_adjustment": "根据我最近的执行阻力，帮我调整这周计划",
            "procrastination": "结合我最近容易拖延的模式，帮我把下一步拆得更容易开始",
            "repeated_timeout": "按我最近总超时的情况，帮我把任务时间预算重排一下",
            "general": "根据你刚识别到的模式，给我一个更适合我的下一步建议",
        }
        title_map = {
            "late_night": "我注意到你最近晚一点开始时，完成率会明显掉下来",
            "plan_adjustment": "我发现你最近不是不努力，而是当前安排开始顶住你了",
            "procrastination": "我看到你最近卡住的点更像“启动困难”，不是能力不够",
            "repeated_timeout": "我发现你最近不是做得慢，而是时间预算经常低估",
            "general": f"我从最近几次互动里更确定了一个模式：{pattern.pattern_name}",
        }
        description = str(pattern.description or pattern.solution_text or pattern.pattern_name or "").strip()
        evidence = (
            f"依据：这个模式最近已重复出现 {int(pattern.frequency or 0)} 次，"
            f"当前置信度约 {float(pattern.confidence_score or 0.0):.0%}。"
        )
        return InsightCandidate(
            scenario=scenario,
            pattern=pattern,
            title=title_map.get(scenario, title_map["general"]),
            description=description or "我已经把这个模式纳入后续建议依据。",
            evidence_summary=evidence,
            recommended_action={
                "label": "按这个思路帮我调整",
                "type": "prompt",
                "payload": {"prompt": action_prompt.get(scenario, action_prompt["general"])},
                "style": "primary",
                "reason_key": scenario,
            },
            confidence=float(pattern.confidence_score or 0.0),
            pattern_type=str(pattern.pattern_type or "unknown"),
        )

    async def _on_cooldown(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> bool:
        if not self.redis:
            return False
        key = self._cooldown_key(user_id, scenario, pattern_id)
        try:
            return bool(await self.redis.exists(key))
        except Exception as exc:
            logger.warning(f"Failed to read perceptible insight cooldown: {exc}")
            return False

    async def _mark_sent(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> None:
        if not self.redis:
            return
        key = self._cooldown_key(user_id, scenario, pattern_id)
        try:
            await self.redis.setex(key, int(timedelta(hours=self.COOLDOWN_HOURS).total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to persist perceptible insight cooldown: {exc}")

    def _cooldown_key(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> str:
        pattern_part = str(pattern_id) if pattern_id else "progress"
        return f"perceptible_insight:{user_id}:{scenario}:{pattern_part}"


class WeeklyLearningReportService:
    """Aggregate weekly learnings into a single user-visible report."""

    REPORT_DEDUP_TTL = timedelta(days=8)

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.system_updates = SystemUpdateService(redis)
        self.progress_service = ProgressNarrativeService(db, redis)
        self.comparison_service = ProgressComparisonService(db)

    async def build_weekly_report(self, *, user_id: UUID) -> dict[str, Any] | None:
        snapshot = await self.progress_service.build_snapshot(str(user_id), period_label="最近7天", period_days=7)
        recent_patterns = await self._recent_patterns(user_id)
        recent_updates = await self._recent_evolution_updates(user_id)
        comparison = await self.comparison_service.build_best_comparison(user_id=user_id)

        top_learnings: list[str] = []
        for message in snapshot.highlights:
            if message and message not in top_learnings:
                top_learnings.append(message)
        for pattern in recent_patterns:
            learning = f"我更确定了一个模式：{pattern.pattern_name}"
            if learning not in top_learnings:
                top_learnings.append(learning)
        for item in recent_updates:
            if item and item not in top_learnings:
                top_learnings.append(item)
        if comparison and comparison.get("delta_text"):
            top_learnings.append(str(comparison["delta_text"]))
        top_learnings = top_learnings[:3]

        if not top_learnings:
            WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL.labels(reason="no_meaningful_change").inc()
            return None

        summary = top_learnings[0]
        one_key_adjustment = self._one_key_adjustment(snapshot=snapshot, patterns=recent_patterns)
        return {
            "headline": "这周我更了解你了一点",
            "weekly_summary": summary,
            "top_learnings": top_learnings,
            "one_key_adjustment": one_key_adjustment,
            "comparison_highlight": comparison["delta_text"] if comparison else "",
            "comparison": comparison,
            "period_range": self._period_range_label(),
            "progress_snapshot": snapshot.to_dict(),
        }

    async def enqueue_weekly_report(self, *, user_id: UUID) -> bool:
        if not (settings.ENABLE_PERCEPTIBLE_INTELLIGENCE and settings.ENABLE_WEEKLY_LEARNING_REPORT):
            return False
        if await self._report_already_generated(user_id):
            WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL.labels(reason="deduped").inc()
            return False
        report = await self.build_weekly_report(user_id=user_id)
        if report is None:
            return False
        payload = build_system_update(
            update_type="weekly_learning_report",
            category="evolution",
            title=report["headline"],
            description=report["weekly_summary"],
            priority="medium",
            metadata={
                "evolution_kind": "weekly_learning_report",
                **report,
            },
        )
        await self.system_updates.enqueue(user_id, payload)
        await self._mark_report_generated(user_id)
        WEEKLY_LEARNING_REPORT_GENERATED_TOTAL.inc()
        return True

    async def enqueue_reports_for_active_users(self, *, limit: int = 200) -> dict[str, int]:
        user_ids = await self._active_user_ids(limit=limit)
        generated = 0
        skipped = 0
        for user_id in user_ids:
            try:
                created = await self.enqueue_weekly_report(user_id=user_id)
                if created:
                    generated += 1
                else:
                    skipped += 1
            except Exception as exc:
                skipped += 1
                logger.warning(f"Failed to generate weekly learning report for {user_id}: {exc}")
        return {"active_users": len(user_ids), "generated": generated, "skipped": skipped}

    async def _recent_patterns(self, user_id: UUID) -> list[BehaviorPattern]:
        cutoff = _utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(BehaviorPattern)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.is_archived.is_(False),
                BehaviorPattern.confidence_score >= 0.7,
                or_(
                    BehaviorPattern.last_observed_at.is_(None),
                    BehaviorPattern.last_observed_at >= cutoff,
                ),
            )
            .order_by(BehaviorPattern.confidence_score.desc(), BehaviorPattern.frequency.desc())
            .limit(3)
        )
        return list(result.scalars().all())

    async def _recent_evolution_updates(self, user_id: UUID) -> list[str]:
        updates = await self.system_updates.list_updates(user_id, limit=80)
        if not updates:
            return []
        cutoff_ts = int((_utcnow() - timedelta(days=7)).timestamp())
        messages: list[str] = []
        for update in updates:
            if int(update.get("created_at") or 0) < cutoff_ts:
                continue
            metadata = update.get("metadata") if isinstance(update, dict) else None
            if not isinstance(metadata, dict):
                continue
            kind = str(metadata.get("evolution_kind") or "").strip()
            if kind == "adaptation_record":
                record = metadata.get("adaptation_record")
                if isinstance(record, dict) and record.get("user_facing_message"):
                    messages.append(str(record["user_facing_message"]).strip())
            elif kind == "preference_learning":
                record = metadata.get("preference_learning")
                if isinstance(record, dict) and record.get("user_facing_message"):
                    messages.append(str(record["user_facing_message"]).strip())
        deduped: list[str] = []
        for item in messages:
            if item and item not in deduped:
                deduped.append(item)
        return deduped[:3]

    def _one_key_adjustment(self, *, snapshot: Any, patterns: list[BehaviorPattern]) -> str:
        if patterns:
            top = patterns[0]
            if top.solution_text:
                return str(top.solution_text).strip()
        attention = getattr(snapshot, "attention_areas", None) or []
        if attention:
            return str(attention[0]).strip()
        growth = getattr(snapshot, "growth_areas", None) or []
        if growth:
            return f"下周继续把重心放在「{growth[0]}」上。"
        return "下一周我会继续沿着你更容易进入状态的节奏给建议。"

    def _period_range_label(self) -> str:
        end = _utcnow().date()
        start = end - timedelta(days=7)
        return f"{start.isoformat()} ~ {end.isoformat()}"

    async def _active_user_ids(self, *, limit: int) -> list[UUID]:
        cutoff = _utcnow() - timedelta(days=14)
        user_ids: list[UUID] = []
        seen: set[UUID] = set()
        queries = [
            select(Task.user_id).where(
                or_(
                    Task.created_at >= cutoff,
                    Task.completed_at >= cutoff,
                )
            ),
            select(StudyRecord.user_id).where(StudyRecord.created_at >= cutoff),
            select(BehaviorPattern.user_id).where(
                or_(
                    BehaviorPattern.last_observed_at >= cutoff,
                    BehaviorPattern.created_at >= cutoff,
                )
            ),
        ]
        for stmt in queries:
            result = await self.db.execute(stmt.limit(limit))
            for raw_user_id in result.scalars().all():
                if raw_user_id in seen or raw_user_id is None:
                    continue
                seen.add(raw_user_id)
                user_ids.append(raw_user_id)
                if len(user_ids) >= limit:
                    return user_ids
        if not user_ids:
            fallback = await self.db.execute(
                select(User.id).where(User.is_active.is_(True)).limit(min(limit, 20))
            )
            for raw_user_id in fallback.scalars().all():
                if raw_user_id not in seen:
                    user_ids.append(raw_user_id)
        return user_ids[:limit]

    async def _report_already_generated(self, user_id: UUID) -> bool:
        if not self.redis:
            return False
        key = self._report_key(user_id)
        try:
            return bool(await self.redis.exists(key))
        except Exception as exc:
            logger.warning(f"Failed to read weekly report dedupe key: {exc}")
            return False

    async def _mark_report_generated(self, user_id: UUID) -> None:
        if not self.redis:
            return
        key = self._report_key(user_id)
        try:
            await self.redis.setex(key, int(self.REPORT_DEDUP_TTL.total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to persist weekly report dedupe key: {exc}")

    def _report_key(self, user_id: UUID) -> str:
        monday = (_utcnow().date() - timedelta(days=_utcnow().weekday())).isoformat()
        return f"weekly_learning_report:{user_id}:{monday}"
