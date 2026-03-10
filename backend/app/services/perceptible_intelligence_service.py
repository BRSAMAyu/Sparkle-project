from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import time
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL,
    PHASE4_OPERATION_DURATION_SECONDS,
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
from app.models.task_feedback import TaskFeedback
from app.services.plan_progress_service import PlanProgressService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.services.self_evolution_service import StrategyCalibrationService
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
    evidence_window: str
    trigger_count: int
    scenario_match_score: float
    evidence_source: str = "behavior_pattern"


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
        started_at = time.perf_counter()
        sources = [
            await self._build_mastery_comparison(user_id=user_id, period_days=period_days),
            await self._build_task_duration_comparison(user_id=user_id, plan_id=plan_id, period_days=period_days),
            await self._build_plan_progress_comparison(user_id=user_id, plan_id=plan_id, period_days=period_days),
        ]
        candidates = [item for item in sources if isinstance(item, dict)]
        if not candidates:
            PROGRESS_COMPARISON_SKIPPED_TOTAL.labels(reason="no_comparable_evidence").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="build_best_comparison").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None
        candidate = max(candidates, key=lambda item: float(item.get("score") or 0.0))
        PROGRESS_COMPARISON_GENERATED_TOTAL.labels(source=str(candidate.get("source") or "unknown")).inc()
        PHASE4_OPERATION_DURATION_SECONDS.labels(operation="build_best_comparison").observe(
            max(time.perf_counter() - started_at, 0.0)
        )
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
            select(
                StudyRecord.node_id,
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0),
                func.count(StudyRecord.id),
            ).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= current_start,
                StudyRecord.created_at < now,
            ).group_by(StudyRecord.node_id)
        )
        previous_rows = await self.db.execute(
            select(
                StudyRecord.node_id,
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0),
                func.count(StudyRecord.id),
            ).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= previous_start,
                StudyRecord.created_at < current_start,
            ).group_by(StudyRecord.node_id)
        )
        current = {
            str(node_id): {"delta": float(delta or 0.0), "count": int(count or 0)}
            for node_id, delta, count in current_rows.all()
            if node_id is not None
        }
        previous = {
            str(node_id): {"delta": float(delta or 0.0), "count": int(count or 0)}
            for node_id, delta, count in previous_rows.all()
            if node_id is not None
        }
        domain_candidates = set(current.keys()) & set(previous.keys())
        best: dict[str, Any] | None = None
        for node_key in domain_candidates:
            current_delta = current[node_key]["delta"]
            previous_delta = previous[node_key]["delta"]
            sample_size = current[node_key]["count"] + previous[node_key]["count"]
            diff = abs(current_delta - previous_delta)
            if sample_size < 2 or diff < 3:
                continue
            candidate = {
                "source": "mastery",
                "before_label": "上一周期同知识点掌握提升",
                "before_value": f"{previous_delta:.1f}",
                "after_label": "最近7天同知识点掌握提升",
                "after_value": f"{current_delta:.1f}",
                "delta_text": (
                    f"同一个知识点最近 7 天掌握提升 {current_delta:.1f}，"
                    f"相比上一周期的 {previous_delta:.1f} 更{'高' if current_delta >= previous_delta else '稳'}。"
                ),
                "why_it_matters": "这是同知识点的前后对比，能更真实反映你的吸收效率变化。",
                "evidence_summary": (
                    f"同域依据：知识点 {node_key} 在两个连续 {period_days} 天窗口内均有学习记录，"
                    f"共 {sample_size} 条记录。"
                ),
                "domain_key": node_key,
                "period_range": f"{previous_start.date().isoformat()} ~ {now.date().isoformat()}",
                "score": diff,
            }
            if best is None or float(candidate["score"]) > float(best["score"]):
                best = candidate
        if best is None:
            PROGRESS_COMPARISON_SKIPPED_TOTAL.labels(reason="mastery_domain_mismatch").inc()
            return None
        return best

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

        def task_domain_key(task: Task) -> str:
            if task.plan_id:
                return f"plan:{task.plan_id}"
            normalized_title = str(task.title or "").strip().lower()
            return f"type:{task.type.value if task.type else 'unknown'}|title:{normalized_title}"

        current_groups: dict[str, list[Task]] = {}
        previous_groups: dict[str, list[Task]] = {}
        for task in current:
            current_groups.setdefault(task_domain_key(task), []).append(task)
        for task in previous:
            previous_groups.setdefault(task_domain_key(task), []).append(task)

        best: dict[str, Any] | None = None
        for domain_key in set(current_groups.keys()) & set(previous_groups.keys()):
            current_items = current_groups[domain_key]
            previous_items = previous_groups[domain_key]
            sample_size = len(current_items) + len(previous_items)
            if sample_size < 3:
                continue
            current_avg = sum(int(item.actual_minutes or 0) for item in current_items) / max(len(current_items), 1)
            previous_avg = sum(int(item.actual_minutes or 0) for item in previous_items) / max(len(previous_items), 1)
            diff = abs(current_avg - previous_avg)
            if diff < 5:
                continue
            improved = current_avg < previous_avg
            candidate = {
                "source": "task_duration",
                "before_label": "上一周期同类任务平均时长",
                "before_value": f"{previous_avg:.0f} 分钟",
                "after_label": "最近7天同类任务平均时长",
                "after_value": f"{current_avg:.0f} 分钟",
                "delta_text": (
                    f"同一类任务的平均完成时长从 {previous_avg:.0f} 分钟变成 {current_avg:.0f} 分钟。"
                ),
                "why_it_matters": (
                    "这说明你在同类任务上的推进节奏变得更顺手。"
                    if improved
                    else "这说明同类任务最近开始变重，值得及时调轻节奏。"
                ),
                "evidence_summary": (
                    f"同域依据：比较对象为 {domain_key}，两个连续 {period_days} 天窗口共 {sample_size} 个已完成任务。"
                ),
                "domain_key": domain_key,
                "period_range": f"{previous_start.date().isoformat()} ~ {now.date().isoformat()}",
                "score": diff,
            }
            if best is None or float(candidate["score"]) > float(best["score"]):
                best = candidate
        if best is None:
            PROGRESS_COMPARISON_SKIPPED_TOTAL.labels(reason="task_domain_mismatch").inc()
            return None
        return best

    async def _build_plan_progress_comparison(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None,
        period_days: int,
    ) -> dict[str, Any] | None:
        if plan_id is None:
            return None
        now = _utcnow()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)
        plan = await self.db.get(Plan, plan_id)
        if plan is None or plan.user_id != user_id:
            return None
        total_result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
            )
        )
        total_tasks = int(total_result.scalar() or 0)
        if total_tasks < 2:
            PROGRESS_COMPARISON_SKIPPED_TOTAL.labels(reason="plan_sample_too_small").inc()
            return None
        current_completed = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= current_start,
                Task.completed_at < now,
            )
        )
        previous_completed = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= previous_start,
                Task.completed_at < current_start,
            )
        )
        current_count = int(current_completed.scalar() or 0)
        previous_count = int(previous_completed.scalar() or 0)
        current_rate = current_count / total_tasks
        previous_rate = previous_count / total_tasks
        diff = abs(current_rate - previous_rate)
        if diff < 0.1:
            return None
        return {
            "source": "plan_progress",
            "before_label": "上一周期同计划推进率",
            "before_value": f"{previous_rate:.0%}",
            "after_label": "最近7天同计划推进率",
            "after_value": f"{current_rate:.0%}",
            "delta_text": f"同一个计划最近 7 天的推进率从 {previous_rate:.0%} 变成了 {current_rate:.0%}。",
            "why_it_matters": "这反映的是同一计划前后节奏变化，而不是不同计划之间的混合平均。",
            "evidence_summary": (
                f"同域依据：计划「{plan.name}」共有 {total_tasks} 个任务，比较两个连续 {period_days} 天窗口的完成占比。"
            ),
            "domain_key": str(plan_id),
            "period_range": f"{previous_start.date().isoformat()} ~ {now.date().isoformat()}",
            "score": diff * 100,
        }


class PerceptibleInsightService:
    """Turn behavioral patterns into user-visible insights with cooldown."""

    COOLDOWN_HOURS = 72
    RECENT_PATTERN_DAYS = 21
    MIN_SCENARIO_SCORE = 0.55

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
        session_feedback: dict[str, Any] | None = None,
        session_id: str | None = None,
        experiment_cohort: str | None = None,
    ) -> dict[str, Any] | None:
        started_at = time.perf_counter()
        if not (settings.ENABLE_PERCEPTIBLE_INTELLIGENCE and settings.ENABLE_PROACTIVE_INSIGHTS):
            return None
        if not self.redis or not getattr(self.system_updates, "redis", None):
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="redis_unavailable").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        plan_uuid = plan_id if isinstance(plan_id, UUID) else UUID(str(plan_id)) if plan_id else None
        plan_report = None
        if plan_uuid:
            try:
                plan_report = await self.progress_service.evaluate_progress(user_id=user_uuid, plan_id=plan_uuid)
            except Exception as exc:
                logger.warning(f"Failed to evaluate plan progress for insight: {exc}")
        eligible_patterns = await self._eligible_patterns(user_uuid)
        comparison = await ProgressComparisonService(self.db).build_best_comparison(
            user_id=user_uuid,
            plan_id=plan_uuid,
        )
        scenario_scores = self._score_scenarios(
            user_message=user_message,
            context_focus=context_focus,
            progress_snapshot=progress_snapshot,
            session_feedback=session_feedback,
            patterns=eligible_patterns,
            plan_report=plan_report,
        )
        scenario, scenario_score = max(scenario_scores.items(), key=lambda item: item[1])
        min_scenario_score = self.MIN_SCENARIO_SCORE + (0.1 if experiment_cohort == "C" else 0.0)
        PERCEPTIBLE_INSIGHT_CANDIDATE_TOTAL.labels(scenario=scenario).inc()
        if scenario_score < min_scenario_score:
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="scenario_below_threshold").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None

        candidate = await self._build_candidate(
            user_id=user_uuid,
            scenario=scenario,
            scenario_score=scenario_score,
            patterns=eligible_patterns,
            plan_id=plan_uuid,
            progress_snapshot=progress_snapshot,
            plan_report=plan_report,
        )
        if candidate is None:
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="no_candidate").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None
        insight_level = "standard"
        upgraded_candidate = await self._maybe_upgrade_to_first_moment(
            user_id=user_uuid,
            session_id=session_id,
            candidate=candidate,
            comparison=comparison,
            experiment_cohort=experiment_cohort,
        )
        if upgraded_candidate is not None:
            candidate = upgraded_candidate
            insight_level = "first_moment"
        if await self._session_has_sent_insight(session_id):
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="session_limit").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None
        if await self._on_cooldown(user_uuid, scenario, candidate.pattern.id if candidate.pattern else None):
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="cooldown").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
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
                "evidence_window": candidate.evidence_window,
                "trigger_count": candidate.trigger_count,
                "scenario_match_score": round(candidate.scenario_match_score, 2),
                "evidence_source": candidate.evidence_source,
                "confidence_tier": "inferred",
                "insight_level": insight_level,
                "experiment_cohort": str(experiment_cohort or ""),
            },
        )
        enqueued = await self.system_updates.enqueue(user_uuid, payload)
        if not enqueued:
            PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL.labels(reason="delivery_unavailable").inc()
            PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
                max(time.perf_counter() - started_at, 0.0)
            )
            return None
        await self._mark_sent(user_uuid, scenario, candidate.pattern.id if candidate.pattern else None)
        await self._mark_session_sent(session_id)
        if insight_level == "first_moment":
            await self._mark_first_moment_sent(user_uuid)
        PERCEPTIBLE_INSIGHT_SENT_TOTAL.labels(pattern_type=candidate.pattern_type or "unknown").inc()
        EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL.labels(kind="proactive_insight").inc()
        PHASE4_OPERATION_DURATION_SECONDS.labels(operation="maybe_enqueue_session_insight").observe(
            max(time.perf_counter() - started_at, 0.0)
        )
        return payload

    async def _build_candidate(
        self,
        *,
        user_id: UUID,
        scenario: str,
        scenario_score: float,
        patterns: list[BehaviorPattern],
        plan_id: UUID | None,
        progress_snapshot: dict[str, Any] | None,
        plan_report: Any | None,
    ) -> InsightCandidate | None:
        for pattern in patterns:
            if self._pattern_matches_scenario(pattern, scenario):
                return self._pattern_candidate(
                    pattern=pattern,
                    scenario=scenario,
                    scenario_score=scenario_score,
                )

        if scenario == "plan_overload_or_friction" and plan_id and plan_report and plan_report.requires_adjustment:
            reasons = "、".join(self._plan_report_reasons(plan_report)[:2]) or "最近执行摩擦增加"
            return InsightCandidate(
                scenario=scenario,
                pattern=None,
                title="我发现这个计划最近开始有点顶住你了",
                description="从最近的执行节奏看，这个计划已经不像一开始那样顺手，值得现在就调轻一点。",
                evidence_summary=(
                    f"触发模式：计划负载/执行摩擦；证据窗口：最近 21 天；"
                    f"计划告警：{reasons}；当前建议动作与计划调整直接相关。"
                ),
                recommended_action=self._recommended_action(
                    label="帮我调整计划",
                    action_type="switch_plan" if plan_id else "prompt",
                    payload=(
                        {"plan_id": str(plan_id)}
                        if plan_id
                        else {"prompt": "根据我最近的执行情况，帮我把这个计划调轻一点"}
                    ),
                    reason_key="plan_overload_or_friction",
                    fallback_prompt="根据我最近的执行情况，帮我把这个计划调轻一点",
                ),
                confidence=0.82,
                pattern_type="progress",
                evidence_window="最近21天",
                trigger_count=max(len(getattr(plan_report, "reasons", []) or []), 1),
                scenario_match_score=scenario_score,
                evidence_source="plan_progress_report",
            )

        if scenario == "repeated_timeout_pattern" and plan_report:
            timeout_reasons = [reason for reason in self._plan_report_reasons(plan_report) if reason in {"time_overrun", "progress_lag"}]
            if timeout_reasons:
                reasons = "、".join(timeout_reasons[:2]) or "最近执行时长持续超出预期"
                return InsightCandidate(
                    scenario=scenario,
                    pattern=None,
                    title="我发现你最近不是做得慢，而是时间预算经常低估",
                    description="最近几次推进里，耗时和节奏偏差在重复出现，值得先把时间预算调准。",
                    evidence_summary=(
                        f"触发模式：重复超时；证据窗口：最近 21 天；"
                        f"关键依据：{reasons}；建议动作直接对应时间预算重排。"
                    ),
                    recommended_action=self._recommended_action(
                        label="帮我重排时间预算",
                        action_type="prompt",
                        payload={"prompt": "按我最近总超时的情况，帮我把任务时间预算重排一下"},
                        reason_key="repeated_timeout_pattern",
                    ),
                    confidence=0.82,
                    pattern_type="progress",
                    evidence_window="最近21天",
                    trigger_count=len(timeout_reasons),
                    scenario_match_score=scenario_score,
                    evidence_source="plan_progress_report",
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

    def _score_scenarios(
        self,
        *,
        user_message: str,
        context_focus: dict[str, Any] | None,
        progress_snapshot: dict[str, Any] | None,
        session_feedback: dict[str, Any] | None,
        patterns: list[BehaviorPattern],
        plan_report: Any | None,
    ) -> dict[str, float]:
        text = str(user_message or "").strip().lower()
        focus_mode = str((context_focus or {}).get("focus_mode") or "").strip().lower()
        now_hour = datetime.now().hour
        feedback_type = str((session_feedback or {}).get("signal_type") or "").strip().lower()
        attention_areas = [
            str(item).strip().lower()
            for item in ((progress_snapshot or {}).get("attention_areas") or [])
            if str(item).strip()
        ]
        score_map = {
            "late_night_underperformance": 0.0,
            "plan_overload_or_friction": 0.0,
            "procrastination_pattern": 0.0,
            "repeated_timeout_pattern": 0.0,
        }
        if now_hour >= 22 or now_hour < 6:
            score_map["late_night_underperformance"] += 0.35
        if any(token in text for token in ("晚上", "夜里", "熬夜", "十点", "十一点", "半夜")):
            score_map["late_night_underperformance"] += 0.35
        if any(self._pattern_matches_scenario(pattern, "late_night_underperformance") for pattern in patterns):
            score_map["late_night_underperformance"] += 0.2
        if any("晚上" in item or "熬夜" in item or "夜" in item for item in attention_areas):
            score_map["late_night_underperformance"] += 0.1

        if focus_mode == "plan_focus":
            score_map["plan_overload_or_friction"] += 0.3
        if any(token in text for token in ("计划", "安排", "复习", "调整", "这周")):
            score_map["plan_overload_or_friction"] += 0.25
        if plan_report and getattr(plan_report, "requires_adjustment", False):
            score_map["plan_overload_or_friction"] += 0.3
        if any(self._pattern_matches_scenario(pattern, "plan_overload_or_friction") for pattern in patterns):
            score_map["plan_overload_or_friction"] += 0.15

        if any(token in text for token in ("拖延", "不想做", "开始不了", "拖着", "拖到", "提不起劲")):
            score_map["procrastination_pattern"] += 0.45
        if feedback_type in {"mismatch", "simplify"}:
            score_map["procrastination_pattern"] += 0.05
        if any(self._pattern_matches_scenario(pattern, "procrastination_pattern") for pattern in patterns):
            score_map["procrastination_pattern"] += 0.25
        if any("拖延" in item or "开始不了" in item for item in attention_areas):
            score_map["procrastination_pattern"] += 0.15

        if any(token in text for token in ("来不及", "做不完", "超时", "拖很久", "太久", "赶不完")):
            score_map["repeated_timeout_pattern"] += 0.45
        if plan_report and any(reason in {"time_overrun", "progress_lag"} for reason in (getattr(plan_report, "reasons", []) or [])):
            score_map["repeated_timeout_pattern"] += 0.25
        if any(self._pattern_matches_scenario(pattern, "repeated_timeout_pattern") for pattern in patterns):
            score_map["repeated_timeout_pattern"] += 0.2
        if any("超时" in item or "太久" in item or "做不完" in item for item in attention_areas):
            score_map["repeated_timeout_pattern"] += 0.1

        return {key: min(value, 1.0) for key, value in score_map.items()}

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
            "late_night_underperformance": ("晚", "夜", "熬夜", "睡", "深夜"),
            "plan_overload_or_friction": ("计划", "安排", "节奏", "复习", "负载", "摩擦"),
            "procrastination_pattern": ("拖延", "启动", "开始", "抗拒"),
            "repeated_timeout_pattern": ("超时", "时间", "拖长", "来不及", "做不完"),
        }
        keywords = keyword_map.get(scenario, ())
        return any(keyword in haystack for keyword in keywords)

    def _pattern_candidate(self, *, pattern: BehaviorPattern, scenario: str, scenario_score: float) -> InsightCandidate:
        action_prompt = {
            "late_night_underperformance": "根据我最近晚间学习的状态，帮我把明天的任务安排到更容易完成的时段",
            "plan_overload_or_friction": "根据我最近的执行阻力，帮我调整这周计划",
            "procrastination_pattern": "结合我最近容易拖延的模式，帮我把下一步拆得更容易开始",
            "repeated_timeout_pattern": "按我最近总超时的情况，帮我把任务时间预算重排一下",
        }
        title_map = {
            "late_night_underperformance": "我注意到你最近晚一点开始时，完成率会明显掉下来",
            "plan_overload_or_friction": "我发现你最近不是不努力，而是当前安排开始顶住你了",
            "procrastination_pattern": "我看到你最近卡住的点更像“启动困难”，不是能力不够",
            "repeated_timeout_pattern": "我发现你最近不是做得慢，而是时间预算经常低估",
        }
        description = str(pattern.description or pattern.solution_text or pattern.pattern_name or "").strip()
        evidence = (
            f"触发模式：{pattern.pattern_name}；证据窗口：最近 21 天；"
            f"重复次数 {int(pattern.frequency or 0)} 次，当前置信度约 {float(pattern.confidence_score or 0.0):.0%}；"
            f"建议动作与该模式直接相关。"
        )
        return InsightCandidate(
            scenario=scenario,
            pattern=pattern,
            title=title_map.get(scenario, f"我从最近几次互动里更确定了一个模式：{pattern.pattern_name}"),
            description=description or "我已经把这个模式纳入后续建议依据。",
            evidence_summary=evidence,
            recommended_action=self._recommended_action(
                label="按这个思路帮我调整",
                action_type="prompt",
                payload={"prompt": action_prompt.get(scenario, "根据你刚识别到的模式，给我一个更适合我的下一步建议")},
                reason_key=scenario,
            ),
            confidence=float(pattern.confidence_score or 0.0),
            pattern_type=str(pattern.pattern_type or "unknown"),
            evidence_window="最近21天",
            trigger_count=int(pattern.frequency or 0),
            scenario_match_score=scenario_score,
            evidence_source="behavior_pattern",
        )

    async def _maybe_upgrade_to_first_moment(
        self,
        *,
        user_id: UUID,
        session_id: str | None,
        candidate: InsightCandidate,
        comparison: dict[str, Any] | None,
        experiment_cohort: str | None,
    ) -> InsightCandidate | None:
        if await self._has_sent_first_moment(user_id):
            return None
        if comparison is None:
            return None
        feedback_count = await self._complete_task_feedback_count(user_id)
        if feedback_count < 5:
            return None
        active_pattern_count = await self._active_pattern_count(user_id)
        if active_pattern_count < 2:
            return None
        pattern_text = candidate.pattern.pattern_name if candidate.pattern else candidate.title
        comparison_text = str(comparison.get("delta_text") or "").strip()
        if not comparison_text:
            return None
        title = "我现在更确定自己已经开始真正懂你了"
        if experiment_cohort == "B":
            title = "我现在第一次能很明确地说：我真的开始懂你了"
        return InsightCandidate(
            scenario=candidate.scenario,
            pattern=candidate.pattern,
            title=title,
            description=(
                f"我先确认了一个稳定模式：{pattern_text}。"
                f"同时你最近的进展也出现了清晰对比：{comparison_text}"
                "接下来我会按这个节奏给你更贴合的建议。"
            ),
            evidence_summary=(
                f"{candidate.evidence_summary}；"
                f"首次懂你时刻：你已经累计 {feedback_count} 次完整任务反馈，"
                f"有 {active_pattern_count} 个活跃高置信模式，且存在同域成长对比。"
            ),
            recommended_action=candidate.recommended_action,
            confidence=max(candidate.confidence, 0.85),
            pattern_type=candidate.pattern_type,
            evidence_window=candidate.evidence_window,
            trigger_count=candidate.trigger_count,
            scenario_match_score=candidate.scenario_match_score,
            evidence_source="behavior_pattern+comparison",
        )

    async def _complete_task_feedback_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(TaskFeedback.id)).where(TaskFeedback.user_id == user_id)
        )
        return int(result.scalar() or 0)

    async def _active_pattern_count(self, user_id: UUID) -> int:
        cutoff = _utcnow() - timedelta(days=self.RECENT_PATTERN_DAYS)
        result = await self.db.execute(
            select(func.count(BehaviorPattern.id)).where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.confidence_score >= 0.7,
                BehaviorPattern.is_archived.is_(False),
                or_(
                    BehaviorPattern.last_observed_at.is_(None),
                    BehaviorPattern.last_observed_at >= cutoff,
                ),
            )
        )
        return int(result.scalar() or 0)

    async def _has_sent_first_moment(self, user_id: UUID) -> bool:
        if not self.redis:
            return False
        try:
            return bool(await self.redis.exists(f"first_perceptible_moment_sent:{user_id}"))
        except Exception as exc:
            logger.warning(f"Failed to read first perceptible moment flag: {exc}")
            return False

    async def _mark_first_moment_sent(self, user_id: UUID) -> None:
        if not self.redis:
            return
        try:
            await self.redis.setex(
                f"first_perceptible_moment_sent:{user_id}",
                int(timedelta(days=365).total_seconds()),
                "1",
            )
        except Exception as exc:
            logger.warning(f"Failed to persist first perceptible moment flag: {exc}")

    async def _on_cooldown(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> bool:
        if not self.redis:
            return True
        key = self._cooldown_key(user_id, scenario, pattern_id)
        try:
            return bool(await self.redis.exists(key))
        except Exception as exc:
            logger.warning(f"Failed to read perceptible insight cooldown: {exc}")
            return True

    async def _mark_sent(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> None:
        if not self.redis:
            return
        key = self._cooldown_key(user_id, scenario, pattern_id)
        try:
            await self.redis.setex(key, int(timedelta(hours=self.COOLDOWN_HOURS).total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to persist perceptible insight cooldown: {exc}")

    async def _session_has_sent_insight(self, session_id: str | None) -> bool:
        if not self.redis or not session_id:
            return bool(self.redis is None)
        try:
            return bool(await self.redis.exists(f"perceptible_insight:session:{session_id}"))
        except Exception as exc:
            logger.warning(f"Failed to read session perceptible insight flag: {exc}")
            return True

    async def _mark_session_sent(self, session_id: str | None) -> None:
        if not self.redis or not session_id:
            return
        try:
            await self.redis.setex(
                f"perceptible_insight:session:{session_id}",
                int(timedelta(hours=self.COOLDOWN_HOURS).total_seconds()),
                "1",
            )
        except Exception as exc:
            logger.warning(f"Failed to persist session perceptible insight flag: {exc}")

    def _cooldown_key(self, user_id: UUID, scenario: str, pattern_id: UUID | None) -> str:
        pattern_part = str(pattern_id) if pattern_id else "progress"
        return f"perceptible_insight:{user_id}:{scenario}:{pattern_part}"

    def _recommended_action(
        self,
        *,
        label: str,
        action_type: str,
        payload: dict[str, Any],
        reason_key: str,
        fallback_prompt: str | None = None,
    ) -> dict[str, Any]:
        if action_type not in {"prompt", "route", "switch_plan", "open_task", "start_focus"}:
            action_type = "prompt"
        if action_type != "prompt" and not payload:
            action_type = "prompt"
        if action_type == "prompt" and "prompt" not in payload:
            payload = {"prompt": fallback_prompt or label}
        return {
            "label": label,
            "type": action_type,
            "payload": payload,
            "style": "primary",
            "reason_key": reason_key,
        }

    def _plan_report_reasons(self, report: Any) -> list[str]:
        return [str(item).strip() for item in (getattr(report, "reasons", []) or []) if str(item).strip()]


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
        profile_hit_rate = await self._profile_strategy_hit_rate(user_id=user_id, snapshot=snapshot)

        evidence_items = self._build_meaningful_change_items(
            snapshot=snapshot,
            recent_patterns=recent_patterns,
            recent_updates=recent_updates,
            comparison=comparison,
            profile_hit_rate=profile_hit_rate,
        )
        if len(evidence_items) < 2:
            WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL.labels(reason="no_meaningful_change").inc()
            return None

        top_learnings = [item["text"] for item in evidence_items[:3]]
        summary = top_learnings[0]
        one_key_adjustment = self._one_key_adjustment(snapshot=snapshot, patterns=recent_patterns)
        evidence_summary = "；".join(item["evidence"] for item in evidence_items[:2] if item.get("evidence"))
        return {
            "headline": "这周我更了解你了一点",
            "weekly_summary": summary,
            "top_learnings": top_learnings,
            "top_learning_items": evidence_items[:3],
            "one_key_adjustment": one_key_adjustment,
            "comparison_highlight": comparison["delta_text"] if comparison else "",
            "comparison": comparison,
            "period_range": self._period_range_label(),
            "progress_snapshot": snapshot.to_dict(),
            "evidence_summary": evidence_summary,
            "delivery_mode": "deferred_inbox",
            "profile_hit_rate": profile_hit_rate,
        }

    async def enqueue_weekly_report(self, *, user_id: UUID) -> bool:
        if not (settings.ENABLE_PERCEPTIBLE_INTELLIGENCE and settings.ENABLE_WEEKLY_LEARNING_REPORT):
            return False
        if not self.redis or not getattr(self.system_updates, "redis", None):
            WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL.labels(reason="redis_unavailable").inc()
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
        enqueued = await self.system_updates.enqueue(user_id, payload)
        if not enqueued:
            WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL.labels(reason="delivery_unavailable").inc()
            return False
        try:
            calibration = StrategyCalibrationService(self.db, self.redis)
            await calibration.record_profile_hit_rate(
                user_id=user_id,
                hit_rate=((report.get("profile_hit_rate") or {}).get("hit_rate")),
            )
        except Exception as exc:
            logger.warning(f"Failed to record profile hit rate for weekly report: {exc}")
        await self._mark_report_generated(user_id)
        WEEKLY_LEARNING_REPORT_GENERATED_TOTAL.inc()
        EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL.labels(kind="weekly_learning_report").inc()
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

    async def _recent_evolution_updates(self, user_id: UUID) -> list[dict[str, str]]:
        updates = await self.system_updates.list_updates(user_id, limit=80)
        if not updates:
            return []
        cutoff_ts = int((_utcnow() - timedelta(days=7)).timestamp())
        messages: list[dict[str, str]] = []
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
                    messages.append(
                        {
                            "source": "adaptation_record",
                            "text": str(record["user_facing_message"]).strip(),
                            "evidence": "来自过去 7 天内的真实适配记录。",
                            "confidence_tier": "implicit",
                            "evidence_source": "adaptation_record",
                        }
                    )
            elif kind == "preference_learning":
                record = metadata.get("preference_learning")
                if isinstance(record, dict) and record.get("user_facing_message"):
                    messages.append(
                        {
                            "source": "preference_learning",
                            "text": str(record["user_facing_message"]).strip(),
                            "evidence": "来自过去 7 天内新增的偏好学习记录。",
                            "confidence_tier": "implicit",
                            "evidence_source": "preference_learning",
                        }
                    )
            elif kind == "plan_reasoning":
                summary = str(metadata.get("reasoning_summary") or "").strip()
                alignment_summary = str(metadata.get("alignment_summary") or "").strip()
                evidence_summary = str(metadata.get("evidence_summary") or "").strip()
                if summary:
                    messages.append(
                        {
                            "source": "plan_reasoning",
                            "text": alignment_summary or summary,
                            "evidence": evidence_summary or "来自过去 7 天内的画像驱动规划依据。",
                            "confidence_tier": "inferred",
                            "evidence_source": "plan_reasoning",
                        }
                    )
            elif update.get("update_type") == "memory_governance_cleanup":
                archived = int(metadata.get("archived") or 0)
                decayed = int(metadata.get("decayed") or 0)
                messages.append(
                    {
                        "source": "memory_governance_cleanup",
                        "text": f"本周清理了 {archived} 条不再活跃的画像记录，并衰减了 {decayed} 条长期未消费记录。",
                        "evidence": "来自最近 7 天内的画像新鲜度治理任务。",
                        "confidence_tier": "inferred",
                        "evidence_source": "memory_governance_cleanup",
                    }
                )
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in messages:
            key = f"{item.get('source')}::{item.get('text')}"
            if item.get("text") and key not in seen:
                seen.add(key)
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

    def _build_meaningful_change_items(
        self,
        *,
        snapshot: Any,
        recent_patterns: list[BehaviorPattern],
        recent_updates: list[dict[str, str]],
        comparison: dict[str, Any] | None,
        profile_hit_rate: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        comparisons = getattr(snapshot, "comparisons", {}) or {}
        tasks_completed = comparisons.get("tasks_completed") or {}
        task_current = int(tasks_completed.get("current") or 0)
        task_previous = int(tasks_completed.get("previous") or 0)
        if task_current > task_previous:
            items.append(
                {
                    "source": "tasks_completed",
                    "text": f"你最近 7 天完成了 {task_current} 个任务，比上一周期多 {task_current - task_previous} 个。",
                    "evidence": f"任务完成数从 {task_previous} 提升到 {task_current}。",
                    "confidence_tier": "inferred",
                    "evidence_source": "progress_snapshot",
                }
            )

        mastery_delta = comparisons.get("mastery_delta") or {}
        mastery_current = float(mastery_delta.get("current") or 0.0)
        mastery_previous = float(mastery_delta.get("previous") or 0.0)
        if abs(mastery_current - mastery_previous) >= 5:
            items.append(
                {
                    "source": "mastery_delta",
                    "text": f"最近 7 天你的知识掌握提升约 {mastery_current:.1f}，相比上一周期更有进展。",
                    "evidence": f"掌握度提升从 {mastery_previous:.1f} 变为 {mastery_current:.1f}。",
                    "confidence_tier": "inferred",
                    "evidence_source": "progress_snapshot",
                }
            )

        progress = comparisons.get("active_plan_progress") or {}
        progress_current = float(progress.get("current") or 0.0)
        progress_previous = float(progress.get("previous") or 0.0)
        if abs(progress_current - progress_previous) >= 0.1:
            items.append(
                {
                    "source": "plan_progress",
                    "text": f"你最近的计划推进节奏比上一周期更清晰，活跃计划平均进度来到 {progress_current:.0%}。",
                    "evidence": f"活跃计划平均进度从 {progress_previous:.0%} 变为 {progress_current:.0%}。",
                    "confidence_tier": "inferred",
                    "evidence_source": "progress_snapshot",
                }
            )

        for pattern in recent_patterns:
            items.append(
                {
                    "source": "behavior_pattern",
                    "text": f"我更确定了一个模式：{pattern.pattern_name}",
                    "evidence": (
                        f"该模式近 7 天仍在出现，频次 {int(pattern.frequency or 0)} 次，"
                        f"置信度约 {float(pattern.confidence_score or 0.0):.0%}。"
                    ),
                    "confidence_tier": "inferred",
                    "evidence_source": "behavior_pattern",
                }
            )

        for item in recent_updates:
            if item.get("text"):
                items.append(item)

        if comparison and comparison.get("delta_text") and comparison.get("evidence_summary"):
            items.append(
                {
                    "source": "comparison",
                    "text": str(comparison["delta_text"]),
                    "evidence": str(comparison["evidence_summary"]),
                    "confidence_tier": "inferred",
                    "evidence_source": str(comparison.get("source") or "comparison"),
                }
            )

        if profile_hit_rate and profile_hit_rate.get("summary"):
            items.append(
                {
                    "source": "profile_hit_rate",
                    "text": str(profile_hit_rate["summary"]),
                    "evidence": str(profile_hit_rate.get("evidence") or ""),
                    "confidence_tier": "inferred",
                    "evidence_source": "plan_reasoning+feedback",
                }
            )

        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in items:
            key = f"{item.get('source')}::{item.get('text')}"
            if item.get("text") and key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    async def _profile_strategy_hit_rate(
        self,
        *,
        user_id: UUID,
        snapshot: Any,
    ) -> dict[str, Any] | None:
        updates = await self.system_updates.list_updates(user_id, limit=80)
        if not updates:
            return None
        cutoff_ts = int((_utcnow() - timedelta(days=7)).timestamp())
        mapping_items: list[dict[str, Any]] = []
        for update in updates:
            if int(update.get("created_at") or 0) < cutoff_ts:
                continue
            metadata = update.get("metadata") if isinstance(update, dict) else None
            if not isinstance(metadata, dict) or metadata.get("evolution_kind") != "plan_reasoning":
                continue
            for item in metadata.get("persona_strategy_mapping") or []:
                if isinstance(item, dict):
                    mapping_items.append(item)
        if not mapping_items:
            return None

        feedback_rows = await self.db.execute(
            select(TaskFeedback.category, TaskFeedback.completion_quality)
            .where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.created_at >= _utcnow() - timedelta(days=7),
            )
        )
        feedbacks = list(feedback_rows.all())
        counts = {
            "too_difficult": 0,
            "too_long": 0,
            "just_right": 0,
        }
        quality_positive = 0
        for category, quality in feedbacks:
            key = str(category or "").strip().lower()
            if key in counts:
                counts[key] += 1
            if quality is not None and int(quality or 0) >= 4:
                quality_positive += 1

        comparisons = getattr(snapshot, "comparisons", {}) or {}
        progress = comparisons.get("active_plan_progress") or {}
        progress_current = float(progress.get("current") or 0.0)
        progress_previous = float(progress.get("previous") or 0.0)
        task_completed = comparisons.get("tasks_completed") or {}
        tasks_current = int(task_completed.get("current") or 0)
        tasks_previous = int(task_completed.get("previous") or 0)

        matched = 0
        for item in mapping_items:
            constraint = str(item.get("recommended_constraint") or "").strip().lower()
            value = str(item.get("recommended_value") or "").strip().lower()
            if constraint == "task_difficulty" and value == "lower":
                if counts["too_difficult"] == 0 or counts["just_right"] > 0 or quality_positive > 0:
                    matched += 1
            elif constraint == "session_length" and value == "shorter":
                if counts["too_long"] == 0 and tasks_current >= tasks_previous:
                    matched += 1
            elif constraint == "task_granularity" and value == "finer":
                if tasks_current >= tasks_previous or quality_positive > 0:
                    matched += 1
            elif constraint == "concurrency" and value == "lower":
                if progress_current >= progress_previous:
                    matched += 1
            elif constraint == "load_shape" and value == "preserve":
                if counts["just_right"] > 0 or quality_positive > 0:
                    matched += 1

        total = len(mapping_items)
        if total <= 0:
            return None
        hit_rate = round(matched / total, 2)
        return {
            "matched": matched,
            "total": total,
            "hit_rate": hit_rate,
            "summary": f"本周画像驱动的规划建议命中率约为 {hit_rate:.0%}。",
            "evidence": (
                f"过去 7 天共跟踪 {total} 条画像驱动建议，命中 {matched} 条；"
                f"参考了任务反馈、完成质量和活跃计划推进变化。"
            ),
        }
