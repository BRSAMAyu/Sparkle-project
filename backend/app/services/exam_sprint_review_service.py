from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import (
    LearningPortfolioResponse,
    NodeQualityAlert,
    PackQualityReport,
    PortfolioSprintEntry,
    PostExamReviewRequest,
    PostExamReviewResponse,
    ReviewPlanSelection,
    ReviewTopicSelection,
    SprintCompletionCheckResponse,
    SprintCompletionSummary,
    SprintCoverageStats,
    SprintDailyStudyPoint,
    SprintErrorRecoveryStats,
    SprintInvitationStatus,
    SprintMasteryDelta,
    SprintScoreStats,
    SprintSummaryResponse,
    SprintTaskStats,
)
from app.schemas.notification import NotificationCreate
from app.services.achievement_engine import AchievementEngine, AchievementEvent
from app.services.galaxy_service import GalaxyService
from app.services.notification_service import NotificationService
from app.services.plan_service import PlanService
from app.services.plan_state_service import PlanStateService
from app.services.profile_write_service import ProfileWriteService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.sprint_packs.sprint_pack_loader import load_pack


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExamSprintReviewService:
    REVIEW_ARCHIVE_KEY = "exam_sprint_growth_archive"
    LAST_REVIEW_KEY = "exam_sprint_last_review"
    PACK_QUALITY_ALERTS_REDIS_PREFIX = "aurora:pack_quality_alerts:"
    PACK_QUALITY_REPORT_TTL_SECONDS = 45 * 24 * 3600
    MASTERY_COVERAGE_THRESHOLD = 60.0
    ERROR_REPAIR_THRESHOLD = 0.8
    MAX_ARCHIVE_ENTRIES = 10
    MASTERY_PENALTY_RATIO = 0.2
    PACK_QUALITY_MIN_EVIDENCE_COUNT = 50
    PACK_QUALITY_EXPECTED_MASTERY_BY_DIFFICULTY: dict[int, float] = {
        1: 0.8,
        2: 0.65,
        3: 0.5,
        4: 0.35,
        5: 0.2,
    }
    PACK_QUALITY_ALERT_GAP_THRESHOLD = 0.3
    CHALLENGE_KEYWORD_NODE_RULES: tuple[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], ...] = (
        (
            ("tcp状态机", "tcp 状态机", "状态机", "状态转换", "状态变化", "time_wait", "time wait", "syn_sent"),
            (
                ("cn.tcp_state", "TCP 状态机"),
                ("cn.tcp_three_way", "TCP 三次握手"),
                ("cn.tcp_four_way", "TCP 四次挥手"),
            ),
        ),
        (
            ("三次握手", "syn", "syn_ack", "syn ack"),
            (("cn.tcp_three_way", "TCP 三次握手"),),
        ),
        (
            ("四次挥手", "time_wait", "time wait", "2msl"),
            (("cn.tcp_four_way", "TCP 四次挥手"),),
        ),
        (
            ("拥塞控制", "慢启动", "拥塞避免", "快重传", "快恢复", "ssthresh", "cwnd"),
            (("cn.tcp_congestion_control", "TCP 拥塞控制"),),
        ),
        (
            ("流量控制", "滑动窗口", "rwnd"),
            (("cn.tcp_flow_control", "TCP 流量控制"),),
        ),
        (
            ("可靠传输", "确认号", "ack", "重传", "序号"),
            (("cn.tcp_reliable_transport", "TCP 可靠传输机制"),),
        ),
        (
            ("tcp", "传输层"),
            (
                ("cn.tcp_basics", "TCP 基础"),
                ("cn.tcp_three_way", "TCP 三次握手"),
                ("cn.tcp_four_way", "TCP 四次挥手"),
                ("cn.tcp_reliable_transport", "TCP 可靠传输机制"),
                ("cn.tcp_congestion_control", "TCP 拥塞控制"),
            ),
        ),
    )

    def __init__(self, db: AsyncSession, redis_client=None) -> None:
        self.db = db
        self.redis = redis_client or cache_service.redis

    async def analyze_pack_node_effectiveness(self, pack_id: str) -> list[NodeQualityAlert]:
        """Return pack-node difficulty alerts from aggregated Galaxy mastery outcomes."""
        pack = self._load_pack_by_pack_id(pack_id)
        stats = await self._collect_pack_node_effectiveness_stats(pack)

        alerts: list[NodeQualityAlert] = []
        for item in stats:
            current_difficulty = int(item["current_difficulty"])
            evidence_count = int(item["evidence_count"])
            average_post_sprint_mastery = float(item["average_post_sprint_mastery"])
            expected_mastery = float(item["expected_mastery"])
            if evidence_count < self.PACK_QUALITY_MIN_EVIDENCE_COUNT:
                continue
            if current_difficulty >= 5:
                continue
            if average_post_sprint_mastery > expected_mastery - self.PACK_QUALITY_ALERT_GAP_THRESHOLD:
                continue
            alerts.append(
                NodeQualityAlert(
                    node_id=str(item["node_id"]),
                    node_label=str(item["node_label"]),
                    current_difficulty=current_difficulty,
                    suggested_difficulty=min(current_difficulty + 1, 5),
                    average_post_sprint_mastery=round(average_post_sprint_mastery, 4),
                    expected_mastery=round(expected_mastery, 4),
                    evidence_count=evidence_count,
                )
            )
        return alerts

    async def build_pack_quality_report(
        self,
        pack_id: str,
        *,
        alerts: list[NodeQualityAlert] | None = None,
    ) -> PackQualityReport:
        """Build a full pack quality report from cached or live mastery statistics."""
        pack = self._load_pack_by_pack_id(pack_id)
        stats = await self._collect_pack_node_effectiveness_stats(pack)
        pack_nodes = list(pack.get("knowledge_nodes") or [])

        if alerts is None:
            alerts = await self.analyze_pack_node_effectiveness(pack_id)

        insufficient_data_nodes = sum(
            1 for item in stats if int(item["evidence_count"]) < self.PACK_QUALITY_MIN_EVIDENCE_COUNT
        )
        return PackQualityReport(
            pack_id=str(pack.get("id") or pack_id),
            pack_name=str(pack.get("name") or pack.get("title") or pack.get("id") or pack_id),
            total_nodes=len(pack_nodes),
            nodes_analyzed=len(stats),
            alerts=alerts,
            insufficient_data_nodes=insufficient_data_nodes,
        )

    async def submit_post_exam_review(
        self,
        *,
        user_id: UUID,
        request: PostExamReviewRequest,
    ) -> PostExamReviewResponse:
        plan = await self._resolve_target_plan(
            user_id=user_id,
            plan_id=request.plan_id,
            require_due=True,
            prefer_active=True,
        )
        plan_id = plan.id
        now = _utcnow()
        initial_summary = await self._build_summary(user_id=user_id, plan=plan)
        archived_plan = await PlanService.archive(
            db=self.db,
            plan_id=plan_id,
            user_id=user_id,
            redis_client=self.redis,
        )
        if archived_plan is None:
            raise LookupError("未找到对应的冲刺计划")

        await PlanStateService(self.db, self.redis).upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={
                "status": PlanStateStatus.ARCHIVED.value,
                "archived_at": now,
            },
            bump_version=False,
        )

        review_id = str(uuid4())
        completion_rate = max(float(plan.progress or 0.0), float(initial_summary.task_stats.completion_rate))
        unlocked = await self._trigger_sprint_achievements(
            user_id=user_id,
            plan=archived_plan,
            completion_rate=completion_rate,
        )

        metadata = self._as_dict(archived_plan.source_metadata)
        review_state = self._as_dict(metadata.get("post_exam_review"))
        review_state.update(
            {
                "completed_at": now.isoformat(),
                "review_id": review_id,
                "self_rating": request.self_rating,
                "sparkle_helped": request.sparkle_helped,
                "helpful_features": [item.value for item in request.helpful_features],
                "underprepared_topics": [self._serialize_topic(item) for item in request.underprepared_topics],
                "prepared_but_not_tested_topics": [
                    self._serialize_plan_selection(item) for item in request.prepared_but_not_tested_topics
                ],
            }
        )
        metadata["post_exam_review"] = review_state
        archived_plan.source_metadata = metadata
        self.db.add(archived_plan)
        await self.db.commit()
        await self.db.refresh(archived_plan)

        final_summary = await self._build_summary(user_id=user_id, plan=archived_plan)
        persistent_weak_nodes = self._identify_persistent_weak_nodes(plan=archived_plan, request=request)
        await self._apply_persistent_weak_node_mastery_adjustments(
            user_id=user_id,
            request=request,
            persistent_weak_nodes=persistent_weak_nodes,
        )
        await self._persist_growth_archive(
            user_id=user_id,
            review_id=review_id,
            plan=archived_plan,
            request=request,
            summary=final_summary,
            persistent_weak_nodes=persistent_weak_nodes,
        )

        return PostExamReviewResponse(
            review_id=review_id,
            plan_id=plan_id,
            archived_in_growth_profile=True,
            helpful_features=list(request.helpful_features),
            summary=final_summary,
            unlocked_achievements=unlocked,
        )

    async def get_sprint_summary(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None = None,
    ) -> SprintSummaryResponse:
        plan = await self._resolve_target_plan(
            user_id=user_id,
            plan_id=plan_id,
            require_due=False,
            prefer_active=False,
        )
        return await self._build_summary(user_id=user_id, plan=plan)

    async def check_sprint_completion(
        self,
        *,
        plan_id: UUID,
        user_id: UUID | None = None,
    ) -> SprintCompletionCheckResponse:
        if user_id is not None:
            plan = await PlanService.get_by_id(self.db, plan_id, user_id)
        else:
            result = await self.db.execute(
                select(Plan).where(
                    Plan.id == plan_id,
                    Plan.deleted_at.is_(None),
                )
            )
            plan = result.scalar_one_or_none()

        if plan is None or plan.type != PlanType.SPRINT:
            raise LookupError("未找到对应的冲刺计划")

        tasks = await self._load_plan_tasks(plan.id)
        if not self._has_completed_seven_day_sprint(tasks):
            return SprintCompletionCheckResponse(completed=False)

        summary = await self._build_summary(user_id=plan.user_id, plan=plan)
        return SprintCompletionCheckResponse(
            completed=True,
            summary=self._build_completion_summary(plan=plan, summary=summary),
        )

    async def get_portfolio(self, *, user_id: UUID) -> LearningPortfolioResponse:
        """Return all sprint entries for the user's learning portfolio."""
        explicit = await self._get_explicit_preferences(user_id)
        archive_payload = self._as_dict(explicit.get(self.REVIEW_ARCHIVE_KEY))
        archived_entries = list(archive_payload.get("entries") or [])

        entries: list[PortfolioSprintEntry] = []
        completed_plan_ids: set[str] = set()
        for archived_entry in reversed(archived_entries):
            portfolio_entry = self._portfolio_entry_from_archive(archived_entry)
            if portfolio_entry is None:
                continue
            entries.append(portfolio_entry)
            completed_plan_ids.add(str(portfolio_entry.plan_id))

        result = await self.db.execute(
            select(Plan)
            .where(
                Plan.user_id == user_id,
                Plan.type == PlanType.SPRINT,
                Plan.deleted_at.is_(None),
            )
            .order_by(Plan.created_at.desc())
        )
        plans = result.scalars().all()

        for plan in plans:
            if str(plan.id) in completed_plan_ids:
                continue
            entries.append(self._portfolio_entry_from_plan(plan))

        entries.sort(key=self._portfolio_sort_key, reverse=True)

        total_mastered = sum(e.mastered_nodes_count for e in entries)
        active_count = sum(1 for e in entries if e.status == "active")
        completed_count = sum(1 for e in entries if e.status == "completed")
        planned_count = sum(1 for e in entries if e.status == "planned")

        return LearningPortfolioResponse(
            entries=entries,
            total_mastered_nodes=total_mastered,
            active_count=active_count,
            completed_count=completed_count,
            planned_count=planned_count,
        )

    def _portfolio_entry_from_archive(self, entry: dict[str, Any]) -> PortfolioSprintEntry | None:
        plan_id = self._parse_uuid(entry.get("plan_id"))
        if plan_id is None:
            return None

        summary = self._as_dict(entry.get("summary"))
        coverage = self._as_dict(summary.get("high_frequency_coverage"))
        task_stats = self._as_dict(summary.get("task_stats"))
        score_stats = self._as_dict(summary.get("score_stats"))
        top_improvement = self._as_dict(summary.get("top_improvement"))
        strongest_area = self._first_non_empty(
            top_improvement.get("node_name"),
            entry.get("strongest_area"),
        )
        weakest_points = self._archive_weakest_points(entry)
        proud_nodes = self._archive_proud_nodes(summary=summary, strongest_area=strongest_area)

        return PortfolioSprintEntry(
            plan_id=plan_id,
            plan_name=str(entry.get("plan_name") or summary.get("plan_name") or "考试冲刺"),
            subject=self._first_non_empty(entry.get("subject"), summary.get("subject")),
            sprint_mode=self._archive_sprint_mode(entry=entry, summary=summary),
            status="completed",
            mastered_nodes_count=self._safe_int(coverage.get("covered_topics_after")),
            started_at=self._first_non_empty(summary.get("started_at"), entry.get("started_at")),
            completed_at=self._first_non_empty(
                entry.get("reviewed_at"),
                self._as_dict(summary.get("invitation_status")).get("completed_at"),
            ),
            target_date=self._parse_date(entry.get("exam_date")),
            progress=self._portfolio_progress(task_stats.get("completion_rate"), fallback=1.0),
            strongest_area=strongest_area,
            growth_area=weakest_points[0] if weakest_points else None,
            self_rating=self._safe_int_or_none(entry.get("self_rating")),
            result_rating=self._safe_int_or_none(entry.get("result_rating")),
            result_description=self._strip(entry.get("result_description")),
            headline=self._strip(summary.get("headline")),
            current_score=self._safe_float_or_none(score_stats.get("current_score")),
            weakest_points=weakest_points,
            proud_nodes=proud_nodes,
        )

    def _portfolio_entry_from_plan(self, plan: Plan) -> PortfolioSprintEntry:
        metadata = self._as_dict(plan.source_metadata)
        review_state = self._as_dict(metadata.get("post_exam_review"))
        status = "active" if plan.is_active else "planned"
        mastered = int(round(max(float(plan.mastery_level or 0.0), 0.0) * 100))
        days_total = self._plan_days_total(plan)
        progress = self._portfolio_progress(plan.progress, fallback=0.0)
        proud_nodes = []
        weakest_points = []
        weak_chapters = metadata.get("exam_sprint_intake")
        if isinstance(weak_chapters, dict):
            weakest_points = [self._strip(item) for item in weak_chapters.get("weak_chapters") or [] if self._strip(item)]

        if days_total and progress > 0:
            proud_nodes = [f"已推进 {max(1, round(progress * days_total))} / {days_total} 天"]

        return PortfolioSprintEntry(
            plan_id=plan.id,
            plan_name=plan.name,
            subject=plan.subject,
            sprint_mode=self._plan_sprint_mode(plan),
            status=status,
            mastered_nodes_count=mastered,
            started_at=plan.created_at.isoformat() if plan.created_at else None,
            completed_at=self._strip(review_state.get("completed_at")),
            target_date=plan.target_date,
            progress=progress,
            strongest_area=None,
            growth_area=weakest_points[0] if weakest_points else None,
            self_rating=self._safe_int_or_none(review_state.get("self_rating")),
            result_rating=None,
            result_description=None,
            headline=self._portfolio_headline_for_plan(plan=plan, status=status, days_total=days_total),
            current_score=None,
            weakest_points=weakest_points,
            proud_nodes=proud_nodes,
        )

    def _portfolio_sort_key(self, entry: PortfolioSprintEntry) -> tuple[int, str]:
        priority = {
            "active": 3,
            "planned": 2,
            "completed": 1,
        }.get(entry.status, 0)
        timestamp = self._first_non_empty(
            entry.completed_at,
            entry.started_at,
            entry.target_date.isoformat() if entry.target_date else None,
        )
        return priority, timestamp or ""

    def _portfolio_progress(self, value: Any, *, fallback: float) -> float:
        numeric = self._safe_float_or_none(value)
        if numeric is None:
            return fallback
        return min(max(numeric, 0.0), 1.0)

    def _plan_sprint_mode(self, plan: Plan) -> str | None:
        metadata = self._as_dict(plan.source_metadata)
        intake = self._as_dict(metadata.get("exam_sprint_intake"))
        explicit_mode = self._first_non_empty(
            intake.get("sprint_mode"),
            metadata.get("sprint_mode"),
        )
        if explicit_mode:
            return explicit_mode
        if metadata.get("last_24h_mode") is True:
            return "last_24h_cram"
        return self._infer_sprint_mode_from_window(
            started_at=plan.created_at.isoformat() if plan.created_at else None,
            target_date=plan.target_date.isoformat() if plan.target_date else None,
        )

    def _archive_sprint_mode(self, *, entry: dict[str, Any], summary: dict[str, Any]) -> str | None:
        explicit_mode = self._first_non_empty(
            entry.get("sprint_mode"),
            summary.get("sprint_mode"),
        )
        if explicit_mode:
            return explicit_mode
        return self._infer_sprint_mode_from_window(
            started_at=self._first_non_empty(summary.get("started_at"), entry.get("started_at")),
            target_date=self._first_non_empty(entry.get("exam_date"), summary.get("exam_date")),
        )

    def _infer_sprint_mode_from_window(self, *, started_at: str | None, target_date: str | None) -> str | None:
        start_dt = self._parse_datetime(started_at)
        target = self._parse_date(target_date)
        if start_dt is None or target is None:
            return None
        total_days = (target - start_dt.date()).days + 1
        if total_days <= 1:
            return "last_24h_cram"
        if total_days <= 7:
            return "seven_day_survival"
        if total_days <= 14:
            return "fourteen_day_build_and_retrieve"
        return "standard_exam_sprint"

    def _portfolio_headline_for_plan(self, *, plan: Plan, status: str, days_total: int | None) -> str:
        if status == "planned":
            if days_total is not None and days_total > 0:
                return f"计划已创建，预计用 {days_total} 天完成这次冲刺。"
            return "计划已创建，等待你开始第一天冲刺。"

        if days_total is not None and days_total > 0:
            completed_days = max(1, round(self._portfolio_progress(plan.progress, fallback=0.0) * days_total))
            remaining_days = max(days_total - completed_days, 0)
            return f"进行到第 {completed_days} 天，还剩 {remaining_days} 天。"

        return "冲刺正在进行中。"

    def _plan_days_total(self, plan: Plan) -> int | None:
        if plan.created_at is None or plan.target_date is None:
            return None
        return max((plan.target_date - plan.created_at.date()).days + 1, 1)

    def _archive_weakest_points(self, entry: dict[str, Any]) -> list[str]:
        points: list[str] = []
        for item in entry.get("persistent_weak_nodes") or []:
            if isinstance(item, dict):
                label = self._strip(item.get("node_name"))
                if label:
                    points.append(label)
        for item in entry.get("underprepared_topics") or []:
            if isinstance(item, dict):
                label = self._first_non_empty(item.get("node_name"), item.get("label"))
                if label:
                    points.append(label)
        return self._unique_strs(points)

    def _archive_proud_nodes(self, *, summary: dict[str, Any], strongest_area: str | None) -> list[str]:
        proud_nodes: list[str] = []
        if strongest_area:
            proud_nodes.append(strongest_area)
        for item in summary.get("mastery_changes") or []:
            if not isinstance(item, dict):
                continue
            label = self._strip(item.get("node_name"))
            if label:
                proud_nodes.append(label)
        return self._unique_strs(proud_nodes)

    def _unique_strs(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []
        for raw in values:
            value = self._strip(raw)
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            results.append(value)
        return results

    def _parse_uuid(self, value: Any) -> UUID | None:
        raw = self._strip(value)
        if not raw:
            return None
        try:
            return UUID(raw)
        except (TypeError, ValueError):
            return None

    def _parse_date(self, value: Any) -> date | None:
        raw = self._strip(value)
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        raw = self._strip(value)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _first_non_empty(self, *values: Any) -> str | None:
        for value in values:
            text = self._strip(value)
            if text:
                return text
        return None

    def _safe_float_or_none(self, value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int_or_none(self, value: Any) -> int | None:
        numeric = self._safe_int(value)
        return numeric if numeric > 0 else None

    async def scan_due_review_invitations(self, *, limit: int = 200) -> dict[str, int]:
        result = await self.db.execute(
            select(Plan)
            .where(
                Plan.type == PlanType.SPRINT,
                Plan.is_active.is_(True),
                Plan.target_date.isnot(None),
                Plan.deleted_at.is_(None),
            )
            .order_by(Plan.created_at.asc())
            .limit(limit)
        )
        invited = 0
        skipped = 0
        for plan in result.scalars().all():
            if not self._is_review_due(plan):
                skipped += 1
                continue

            metadata = self._as_dict(plan.source_metadata)
            review_state = self._as_dict(metadata.get("post_exam_review"))
            if review_state.get("invited_at") or review_state.get("completed_at"):
                skipped += 1
                continue

            notification = await NotificationService.create(
                self.db,
                plan.user_id,
                NotificationCreate(
                    title="考试结束了！",
                    content="想花 3 分钟做一个快速复盘吗？",
                    type="exam_sprint_review",
                    data={
                        "plan_id": str(plan.id),
                        "entrypoint": "/exam-sprint/post-exam-review",
                        "subject": plan.subject,
                    },
                ),
                push_via_websocket=False,
            )
            review_state.update(
                {
                    "invited_at": _utcnow().isoformat(),
                    "notification_id": str(notification.id),
                }
            )
            metadata["post_exam_review"] = review_state
            plan.source_metadata = metadata
            self.db.add(plan)
            await self.db.commit()

            await SystemUpdateService(self.redis).enqueue(
                plan.user_id,
                build_system_update(
                    update_type="exam_sprint_post_exam_review_invite",
                    category="journey",
                    title="考试结束了！",
                    description="想花 3 分钟做一个快速复盘吗？",
                    priority="medium",
                    metadata={
                        "plan_id": str(plan.id),
                        "entrypoint": "/exam-sprint/post-exam-review",
                        "subject": plan.subject,
                    },
                ),
            )
            invited += 1

        return {"invited": invited, "skipped": skipped}

    async def _build_summary(
        self,
        *,
        user_id: UUID,
        plan: Plan,
    ) -> SprintSummaryResponse:
        explicit = await self._get_explicit_preferences(user_id)
        cold_start = self._as_dict(explicit.get("cold_start_context"))
        tasks = await self._load_plan_tasks(plan.id)
        task_stats = self._build_task_stats(tasks)
        mastery_changes, score_stats, top_improvement, coverage_stats = await self._build_mastery_summary(
            user_id=user_id,
            cold_start=cold_start,
        )
        error_recovery = await self._build_error_recovery(
            user_id=user_id,
            subject=plan.subject,
            start_at=plan.created_at,
            exam_date=plan.target_date,
        )
        daily_study_trend = await self._build_daily_study_trend(
            user_id=user_id,
            plan_id=plan.id,
            start_at=plan.created_at,
            exam_date=plan.target_date,
        )

        end_date = plan.target_date or _utcnow().date()
        days_used = max(1, (end_date - plan.created_at.date()).days + 1)
        headline = self._build_headline(days_used=days_used, task_stats=task_stats, top_improvement=top_improvement)
        invitation_status = self._build_invitation_status(plan)

        narrative_highlights = [
            f"你用了 {days_used} 天，完成了 {task_stats.completed} / {task_stats.total} 项任务。",
        ]
        if top_improvement is not None:
            narrative_highlights.append(
                f"{top_improvement.node_name} 从 {round(top_improvement.before_mastery)} 分提升到 {round(top_improvement.after_mastery)} 分。"
            )
        if coverage_stats.total_topics > 0:
            narrative_highlights.append(
                f"高频考点覆盖率从 {round(coverage_stats.baseline_rate * 100)}% 提升到 {round(coverage_stats.current_rate * 100)}%。"
            )
        elif error_recovery.total_errors > 0:
            narrative_highlights.append(f"错题修复率达到 {round(error_recovery.repair_rate * 100)}%。")

        return SprintSummaryResponse(
            plan_id=plan.id,
            plan_name=plan.name,
            subject=plan.subject,
            exam_date=plan.target_date,
            started_at=plan.created_at.isoformat(),
            days_used=days_used,
            headline=headline,
            task_stats=task_stats,
            score_stats=score_stats,
            mastery_changes=mastery_changes,
            top_improvement=top_improvement,
            high_frequency_coverage=coverage_stats,
            error_recovery=error_recovery,
            daily_study_trend=daily_study_trend,
            narrative_highlights=narrative_highlights,
            invitation_status=invitation_status,
        )

    async def _resolve_target_plan(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None,
        require_due: bool,
        prefer_active: bool,
    ) -> Plan:
        if plan_id is not None:
            plan = await PlanService.get_by_id(self.db, plan_id, user_id)
            if plan is None or plan.type != PlanType.SPRINT:
                raise LookupError("未找到对应的冲刺计划")
            if require_due and not self._is_review_due(plan):
                raise ValueError("考试结束满 24 小时后才能进入复盘")
            return plan

        result = await self.db.execute(
            select(Plan)
            .where(
                Plan.user_id == user_id,
                Plan.type == PlanType.SPRINT,
                Plan.deleted_at.is_(None),
            )
            .order_by(Plan.created_at.desc())
        )
        plans = result.scalars().all()
        if not plans:
            raise LookupError("当前没有可复盘的冲刺计划")

        candidates = list(plans)
        if prefer_active:
            active_due = [plan for plan in candidates if plan.is_active and self._is_review_due(plan)]
            if active_due:
                return active_due[0]

        due_pending = [
            plan
            for plan in candidates
            if self._is_review_due(plan) and not self._build_invitation_status(plan).completed_at
        ]
        if due_pending:
            return due_pending[0]

        if require_due:
            raise ValueError("考试结束满 24 小时后才能进入复盘")
        return candidates[0]

    async def _load_plan_tasks(self, plan_id: UUID) -> list[Task]:
        result = await self.db.execute(
            select(Task).where(Task.plan_id == plan_id, Task.deleted_at.is_(None)).order_by(Task.created_at.asc())
        )
        return result.scalars().all()

    def _build_task_stats(self, tasks: list[Task]) -> SprintTaskStats:
        total = len(tasks)
        completed = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
        completion_rate = (completed / total) if total else 0.0
        return SprintTaskStats(total=total, completed=completed, completion_rate=round(completion_rate, 4))

    async def _build_mastery_summary(
        self,
        *,
        user_id: UUID,
        cold_start: dict[str, Any],
    ) -> tuple[list[SprintMasteryDelta], SprintScoreStats, SprintMasteryDelta | None, SprintCoverageStats]:
        raw_snapshot = cold_start.get("diagnostic_node_mastery_snapshot")
        baseline_snapshot = list(raw_snapshot) if isinstance(raw_snapshot, list) else []
        node_ids: list[UUID] = []
        baseline_by_id: dict[UUID, dict[str, Any]] = {}
        for item in baseline_snapshot:
            if not isinstance(item, dict):
                continue
            raw_node_id = item.get("node_id")
            if not raw_node_id:
                continue
            try:
                node_id = UUID(str(raw_node_id))
            except (TypeError, ValueError):
                continue
            node_ids.append(node_id)
            baseline_by_id[node_id] = item

        current_status_rows: list[UserNodeStatus] = []
        if node_ids:
            result = await self.db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id.in_(node_ids),
                )
            )
            current_status_rows = result.scalars().all()
        current_by_id = {row.node_id: float(row.mastery_score or 0.0) for row in current_status_rows}

        mastery_changes: list[SprintMasteryDelta] = []
        for node_id in node_ids:
            baseline = baseline_by_id.get(node_id) or {}
            before = float(baseline.get("mastery") or 0.0)
            after = float(current_by_id.get(node_id, before))
            mastery_changes.append(
                SprintMasteryDelta(
                    node_id=node_id,
                    node_name=str(baseline.get("node_name") or node_id),
                    before_mastery=round(before, 1),
                    after_mastery=round(after, 1),
                    delta=round(after - before, 1),
                )
            )

        mastery_changes.sort(key=lambda item: (item.delta, item.after_mastery), reverse=True)
        top_improvement = mastery_changes[0] if mastery_changes else None

        baseline_score = self._safe_float(cold_start.get("diagnostic_estimated_score"))
        baseline_source = "diagnostic" if baseline_score is not None else None
        if baseline_score is None:
            baseline_score = self._safe_float(cold_start.get("estimated_score_now"))
            baseline_source = "intake" if baseline_score is not None else None

        current_score = None
        if mastery_changes:
            current_score = round(
                sum(item.after_mastery for item in mastery_changes) / len(mastery_changes),
                1,
            )
        else:
            current_score = await self._current_average_mastery(user_id)

        score_delta = None
        if baseline_score is not None and current_score is not None:
            score_delta = round(current_score - baseline_score, 1)

        covered_before = sum(1 for item in mastery_changes if item.before_mastery >= self.MASTERY_COVERAGE_THRESHOLD)
        covered_after = sum(1 for item in mastery_changes if item.after_mastery >= self.MASTERY_COVERAGE_THRESHOLD)
        total_topics = len(mastery_changes)
        baseline_rate = (covered_before / total_topics) if total_topics else 0.0
        current_rate = (covered_after / total_topics) if total_topics else 0.0

        return (
            mastery_changes,
            SprintScoreStats(
                baseline_score=baseline_score,
                current_score=current_score,
                delta=score_delta,
                baseline_source=baseline_source,
            ),
            top_improvement,
            SprintCoverageStats(
                baseline_rate=round(baseline_rate, 4),
                current_rate=round(current_rate, 4),
                delta_rate=round(current_rate - baseline_rate, 4),
                total_topics=total_topics,
                covered_topics_before=covered_before,
                covered_topics_after=covered_after,
            ),
        )

    async def _current_average_mastery(self, user_id: UUID) -> float | None:
        result = await self.db.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_id))
        rows = result.scalars().all()
        if not rows:
            return None
        return round(sum(float(row.mastery_score or 0.0) for row in rows) / len(rows), 1)

    async def _build_error_recovery(
        self,
        *,
        user_id: UUID,
        subject: str | None,
        start_at: datetime,
        exam_date: date | None,
    ) -> SprintErrorRecoveryStats:
        end_at = self._window_end(start_at=start_at, exam_date=exam_date)
        result = await self.db.execute(
            select(ErrorRecord).where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted.is_(False),
                ErrorRecord.created_at >= start_at,
                ErrorRecord.created_at <= end_at,
            )
        )
        records = result.scalars().all()
        if subject:
            matched = [record for record in records if str(record.subject_code or "").strip() == str(subject).strip()]
            if matched:
                records = matched
        repaired = sum(1 for record in records if float(record.mastery_level or 0.0) >= self.ERROR_REPAIR_THRESHOLD)
        total = len(records)
        rate = (repaired / total) if total else 0.0
        return SprintErrorRecoveryStats(
            total_errors=total,
            repaired_errors=repaired,
            repair_rate=round(rate, 4),
        )

    async def _build_daily_study_trend(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        start_at: datetime,
        exam_date: date | None,
    ) -> list[SprintDailyStudyPoint]:
        end_at = self._window_end(start_at=start_at, exam_date=exam_date)
        totals: dict[date, int] = defaultdict(int)

        result = await self.db.execute(
            select(StudyRecord).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= start_at,
                StudyRecord.created_at <= end_at,
            )
        )
        study_records = result.scalars().all()
        for record in study_records:
            record_date = record.created_at.date()
            totals[record_date] += max(int(record.study_minutes or 0), 0)

        if not totals:
            task_result = await self.db.execute(
                select(Task).where(
                    Task.plan_id == plan_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at.isnot(None),
                    Task.completed_at >= start_at,
                    Task.completed_at <= end_at,
                )
            )
            for task in task_result.scalars().all():
                task_date = task.completed_at.date() if task.completed_at else start_at.date()
                totals[task_date] += max(int(task.actual_minutes or task.estimated_minutes or 0), 0)

        current_date = start_at.date()
        final_date = end_at.date()
        points: list[SprintDailyStudyPoint] = []
        while current_date <= final_date:
            points.append(SprintDailyStudyPoint(date=current_date, minutes=int(totals.get(current_date, 0))))
            current_date += timedelta(days=1)
        return points

    async def _trigger_sprint_achievements(
        self,
        *,
        user_id: UUID,
        plan: Plan,
        completion_rate: float,
    ) -> list[dict[str, Any]]:
        if completion_rate < 0.8:
            return []

        engine = AchievementEngine(self.db)
        unlocked: list[dict[str, Any]] = []
        unlocked.extend(
            await engine.process_event(str(user_id), AchievementEvent.SPRINT_COMPLETED, completion_rate=completion_rate)
        )
        if completion_rate >= 1.0:
            unlocked.extend(
                await engine.process_event(
                    str(user_id), AchievementEvent.SPRINT_PERFECT, completion_rate=completion_rate
                )
            )
            if plan.target_date:
                days_ahead = max((plan.target_date - _utcnow().date()).days, 0)
                if days_ahead > 0:
                    unlocked.extend(
                        await engine.process_event(
                            str(user_id),
                            AchievementEvent.SPRINT_AHEAD,
                            completion_rate=completion_rate,
                            days_ahead=days_ahead,
                        )
                    )
        unlocked.extend(
            await engine.process_event(str(user_id), AchievementEvent.SPRINT_STREAK, completion_rate=completion_rate)
        )
        return unlocked

    async def _persist_growth_archive(
        self,
        *,
        user_id: UUID,
        review_id: str,
        plan: Plan,
        request: PostExamReviewRequest,
        summary: SprintSummaryResponse,
        persistent_weak_nodes: list[dict[str, Any]],
    ) -> None:
        explicit = await self._get_explicit_preferences(user_id)
        archive_payload = self._as_dict(explicit.get(self.REVIEW_ARCHIVE_KEY))
        entries = list(archive_payload.get("entries") or [])
        entries = [entry for entry in entries if entry.get("review_id") != review_id]
        now = _utcnow().isoformat()
        archive_entry = {
            "review_id": review_id,
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "subject": plan.subject,
            "exam_date": plan.target_date.isoformat() if plan.target_date else None,
            "reviewed_at": now,
            "self_rating": request.self_rating,
            "result_rating": request.result_rating,
            "result_description": request.result_description,
            "biggest_challenge": request.biggest_challenge,
            "strategy_feedback": request.strategy_feedback,
            "self_advice": request.self_advice,
            "sparkle_helped": request.sparkle_helped,
            "helpful_features": [item.value for item in request.helpful_features],
            "underprepared_topics": [self._serialize_topic(item) for item in request.underprepared_topics],
            "prepared_but_not_tested_topics": [
                self._serialize_plan_selection(item) for item in request.prepared_but_not_tested_topics
            ],
            "persistent_weak_nodes": persistent_weak_nodes,
            "summary": summary.model_dump(mode="json"),
        }
        entries.append(archive_entry)
        entries = entries[-self.MAX_ARCHIVE_ENTRIES :]

        latest_review = {
            "review_id": review_id,
            "subject": plan.subject,
            "exam_date": plan.target_date.isoformat() if plan.target_date else None,
            "self_rating": request.self_rating,
            "result_rating": request.result_rating,
            "biggest_challenge": request.biggest_challenge,
            "sparkle_helped": request.sparkle_helped,
            "helpful_features": [item.value for item in request.helpful_features],
            "underprepared_topics": [item.node_name for item in request.underprepared_topics],
            "prepared_but_not_tested_topics": [item.label for item in request.prepared_but_not_tested_topics],
            "persistent_weak_nodes": persistent_weak_nodes,
            "headline": summary.headline,
            "top_improvement": summary.top_improvement.model_dump(mode="json") if summary.top_improvement else None,
            "reviewed_at": now,
        }

        await ProfileWriteService(self.db, self.redis).set_explicit_preferences(
            user_id=user_id,
            updates={
                self.REVIEW_ARCHIVE_KEY: {
                    "entries": entries,
                    "updated_at": now,
                },
                self.LAST_REVIEW_KEY: latest_review,
            },
            evidence_refs_by_key={
                self.REVIEW_ARCHIVE_KEY: [{"type": "system", "id": "exam_sprint_post_exam_review"}],
                self.LAST_REVIEW_KEY: [{"type": "system", "id": "exam_sprint_post_exam_review"}],
            },
            confidence_by_key={
                self.REVIEW_ARCHIVE_KEY: 0.95,
                self.LAST_REVIEW_KEY: 0.95,
            },
            source_type="system",
            source="exam_sprint_post_exam_review",
        )

    def _identify_persistent_weak_nodes(
        self,
        *,
        plan: Plan,
        request: PostExamReviewRequest,
    ) -> list[dict[str, Any]]:
        weak_nodes: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_node(
            *,
            node_id: str | None,
            node_name: str,
            source: str,
            evidence: str | None = None,
        ) -> None:
            name = str(node_name or "").strip()
            normalized_id = str(node_id or "").strip()
            dedupe_key = normalized_id or self._match_key(name)
            if not dedupe_key or dedupe_key in seen:
                return
            seen.add(dedupe_key)
            weak_nodes.append(
                {
                    "node_id": normalized_id or None,
                    "node_name": name or normalized_id,
                    "source": source,
                    "evidence": evidence,
                }
            )

        challenge = str(request.biggest_challenge or "").strip()
        challenge_key = self._match_key(challenge)
        if challenge_key:
            for keywords, nodes in self.CHALLENGE_KEYWORD_NODE_RULES:
                is_broad_tcp_rule = set(keywords) == {"tcp", "传输层"}
                if is_broad_tcp_rule and weak_nodes:
                    continue
                if any(self._match_key(keyword) in challenge_key for keyword in keywords):
                    for node_id, node_name in nodes:
                        add_node(
                            node_id=node_id,
                            node_name=node_name,
                            source="biggest_challenge_keyword",
                            evidence=challenge,
                        )

            for node in self._match_pack_nodes_from_text(subject=plan.subject, text=challenge):
                add_node(
                    node_id=str(node.get("node_id") or ""),
                    node_name=str(node.get("label") or node.get("node_id") or ""),
                    source="biggest_challenge_pack_match",
                    evidence=challenge,
                )

        for topic in request.underprepared_topics:
            add_node(
                node_id=str(topic.node_id) if topic.node_id else None,
                node_name=topic.node_name,
                source="underprepared_topic",
                evidence=topic.node_name,
            )

        return weak_nodes

    def _match_pack_nodes_from_text(self, *, subject: str | None, text: str) -> list[dict[str, Any]]:
        pack = load_pack(subject or "")
        if not pack:
            return []
        text_key = self._match_key(text)
        if not text_key:
            return []

        matches: list[dict[str, Any]] = []
        for node in list(pack.get("knowledge_nodes") or []):
            node_id = str(node.get("node_id") or "")
            label = str(node.get("label") or "")
            candidates = [
                node_id,
                label,
                label.replace("（", " ").replace("）", " "),
                node_id.rsplit(".", 1)[-1].replace("_", " "),
            ]
            if any(candidate and self._match_key(candidate) in text_key for candidate in candidates):
                matches.append(dict(node))
        return matches

    def build_pack_quality_alerts_cache_key(self, pack_id: str) -> str:
        normalized_pack_id = str(pack_id or "").strip()
        return f"{self.PACK_QUALITY_ALERTS_REDIS_PREFIX}{normalized_pack_id}"

    def _load_pack_by_pack_id(self, pack_id: str) -> dict[str, Any]:
        raw_pack_id = str(pack_id or "").strip()
        if not raw_pack_id:
            raise ValueError("pack_id is required")

        subject = raw_pack_id
        version = "v1"
        if "@" in raw_pack_id:
            subject, version = raw_pack_id.split("@", 1)

        pack = load_pack(subject, version)
        if pack is None:
            raise LookupError("未找到对应的 Sprint Pack")
        return pack

    async def _collect_pack_node_effectiveness_stats(self, pack: dict[str, Any]) -> list[dict[str, Any]]:
        pack_nodes = list(pack.get("knowledge_nodes") or [])
        if not pack_nodes:
            return []

        node_meta_by_uuid: dict[UUID, dict[str, Any]] = {}
        for item in pack_nodes:
            raw_node_id = str(item.get("node_id") or "").strip()
            if not raw_node_id:
                continue
            canonical_node_id = GalaxyService._canonical_sprint_node_id(raw_node_id)
            node_uuid = GalaxyService.sprint_node_uuid(canonical_node_id)
            node_meta_by_uuid[node_uuid] = {
                "node_id": canonical_node_id,
                "node_label": str(item.get("label") or canonical_node_id),
                "current_difficulty": max(1, min(self._as_int(item.get("difficulty"), fallback=3), 5)),
            }

        if not node_meta_by_uuid:
            return []

        result = await self.db.execute(
            select(
                UserNodeStatus.node_id,
                func.avg(UserNodeStatus.mastery_score),
                func.count(UserNodeStatus.user_id),
            )
            .where(UserNodeStatus.node_id.in_(list(node_meta_by_uuid.keys())))
            .group_by(UserNodeStatus.node_id)
        )
        aggregate_rows = {
            node_id: {
                "average_mastery": self._mastery_ratio(average_mastery),
                "evidence_count": int(evidence_count or 0),
            }
            for node_id, average_mastery, evidence_count in result.all()
        }

        stats: list[dict[str, Any]] = []
        for node_uuid, node_meta in node_meta_by_uuid.items():
            aggregate = aggregate_rows.get(node_uuid, {})
            current_difficulty = int(node_meta["current_difficulty"])
            stats.append(
                {
                    "node_id": str(node_meta["node_id"]),
                    "node_label": str(node_meta["node_label"]),
                    "current_difficulty": current_difficulty,
                    "average_post_sprint_mastery": float(aggregate.get("average_mastery", 0.0)),
                    "expected_mastery": self._expected_mastery_for_difficulty(current_difficulty),
                    "evidence_count": int(aggregate.get("evidence_count", 0)),
                }
            )
        return stats

    async def _apply_persistent_weak_node_mastery_adjustments(
        self,
        *,
        user_id: UUID,
        request: PostExamReviewRequest,
        persistent_weak_nodes: list[dict[str, Any]],
    ) -> None:
        if not persistent_weak_nodes:
            return
        rating = request.result_rating or max(1, min(5, round(float(request.self_rating or 0) / 2)))
        has_keyword_match = any(
            str(node.get("source") or "").startswith("biggest_challenge") for node in persistent_weak_nodes
        )
        if rating > 2 and not has_keyword_match:
            return

        rows = await self._load_user_galaxy_node_statuses(user_id)
        if not rows:
            return

        matched_rows: dict[UUID, tuple[KnowledgeNode, UserNodeStatus]] = {}
        for weak_node in persistent_weak_nodes:
            for node, status in rows:
                if self._weak_node_matches_galaxy_node(weak_node, node):
                    matched_rows[node.id] = (node, status)

        if not matched_rows:
            return

        galaxy_service = GalaxyService(self.db)
        for node, status in matched_rows.values():
            current_mastery = float(status.mastery_score or 0.0)
            new_mastery = self._penalized_mastery(current_mastery)
            if new_mastery == current_mastery:
                continue
            try:
                await galaxy_service.update_node_mastery(
                    user_id=user_id,
                    node_id=node.id,
                    new_mastery=new_mastery,
                    reason="post_exam_review_weak_node",
                )
            except Exception as exc:
                logger.warning(
                    "post-exam mastery adjustment failed user_id={} node_id={} error={}",
                    user_id,
                    node.id,
                    exc,
                )

    async def _load_user_galaxy_node_statuses(
        self,
        user_id: UUID,
    ) -> list[tuple[KnowledgeNode, UserNodeStatus]]:
        result = await self.db.execute(
            select(KnowledgeNode, UserNodeStatus)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_id)
        )
        return list(result.all())

    def _weak_node_matches_galaxy_node(self, weak_node: dict[str, Any], node: KnowledgeNode) -> bool:
        terms = self._weak_node_match_terms(weak_node)
        if not terms:
            return False
        node_terms = self._galaxy_node_match_terms(node)
        if not node_terms:
            return False

        for term in terms:
            if term in node_terms:
                return True
            if len(term) >= 4 and any(term in node_term for node_term in node_terms):
                return True
        return False

    def _weak_node_match_terms(self, weak_node: dict[str, Any]) -> set[str]:
        values: list[Any] = [
            weak_node.get("node_id"),
            weak_node.get("node_name"),
            weak_node.get("label"),
            weak_node.get("title"),
        ]
        node_id = str(weak_node.get("node_id") or "").strip()
        if node_id:
            values.append(node_id.rsplit(".", 1)[-1].replace("_", " "))
        return {self._match_key(value) for value in values if self._match_key(value)}

    def _galaxy_node_match_terms(self, node: KnowledgeNode) -> set[str]:
        values: list[Any] = [node.name, node.name_en, node.description]
        keywords = node.keywords or []
        if isinstance(keywords, dict):
            values.extend(keywords.keys())
            values.extend(keywords.values())
        elif isinstance(keywords, list | tuple | set):
            values.extend(keywords)
        return {self._match_key(value) for value in values if self._match_key(value)}

    def _penalized_mastery(self, current_mastery: float) -> float:
        penalty = self.MASTERY_PENALTY_RATIO if current_mastery <= 1.0 else self.MASTERY_PENALTY_RATIO * 100
        new_mastery = max(0.0, current_mastery - penalty)
        return round(new_mastery, 4 if current_mastery <= 1.0 else 1)

    @staticmethod
    def _mastery_ratio(value: Any) -> float:
        try:
            mastery = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if mastery > 1.0:
            mastery = mastery / 100.0
        return max(0.0, min(mastery, 1.0))

    def _expected_mastery_for_difficulty(self, difficulty: int) -> float:
        normalized_difficulty = max(1, min(int(difficulty or 3), 5))
        return float(self.PACK_QUALITY_EXPECTED_MASTERY_BY_DIFFICULTY.get(normalized_difficulty, 0.5))

    @staticmethod
    def _match_key(value: Any) -> str:
        return "".join(str(value or "").lower().split())

    async def _get_explicit_preferences(self, user_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id)
        )
        explicit = result.scalar_one_or_none() or {}
        return explicit if isinstance(explicit, dict) else {}

    def _build_headline(
        self,
        *,
        days_used: int,
        task_stats: SprintTaskStats,
        top_improvement: SprintMasteryDelta | None,
    ) -> str:
        if top_improvement is not None:
            return (
                f"你用了 {days_used} 天，完成了 {task_stats.completed} 项任务，"
                f"{top_improvement.node_name} 从 {round(top_improvement.before_mastery)} 分提升到 "
                f"{round(top_improvement.after_mastery)} 分。"
            )
        return f"你用了 {days_used} 天，完成了 {task_stats.completed} 项任务。"

    def _build_invitation_status(self, plan: Plan) -> SprintInvitationStatus:
        metadata = self._as_dict(plan.source_metadata)
        review_state = self._as_dict(metadata.get("post_exam_review"))
        return SprintInvitationStatus(
            eligible=self._is_review_due(plan),
            invited_at=review_state.get("invited_at"),
            notification_id=review_state.get("notification_id"),
            completed_at=review_state.get("completed_at"),
            review_id=review_state.get("review_id"),
        )

    def _has_completed_seven_day_sprint(self, tasks: list[Task]) -> bool:
        if not tasks:
            return False

        grouped_days: set[int] = set()
        for task in tasks:
            grouped_days.add(self._task_day_index(task))
            if self._task_status(task) != TaskStatus.COMPLETED.value:
                return False

        return set(range(1, 8)).issubset(grouped_days)

    def _build_completion_summary(
        self,
        *,
        plan: Plan,
        summary: SprintSummaryResponse,
    ) -> SprintCompletionSummary:
        mastery_changes = list(summary.mastery_changes)
        mastered_nodes_count = summary.high_frequency_coverage.covered_topics_after
        if mastered_nodes_count == 0 and mastery_changes:
            mastered_nodes_count = sum(
                1 for item in mastery_changes if item.after_mastery >= self.MASTERY_COVERAGE_THRESHOLD
            )

        strongest_area = self._strongest_area(summary=summary, plan=plan)
        growth_area = self._growth_area(summary=summary, strongest_area=strongest_area)

        return SprintCompletionSummary(
            mastered_nodes_count=mastered_nodes_count,
            repaired_errors_count=summary.error_recovery.repaired_errors,
            completed_tasks_count=summary.task_stats.completed,
            strongest_area=strongest_area,
            growth_area=growth_area,
        )

    def _strongest_area(self, *, summary: SprintSummaryResponse, plan: Plan) -> str:
        if summary.mastery_changes:
            strongest = max(
                summary.mastery_changes,
                key=lambda item: (item.after_mastery, item.delta, item.node_name),
            )
            return strongest.node_name
        if summary.top_improvement is not None:
            return summary.top_improvement.node_name
        return str(plan.subject or plan.name or "核心知识点")

    def _growth_area(self, *, summary: SprintSummaryResponse, strongest_area: str) -> str:
        if summary.mastery_changes:
            growth_candidates = [item for item in summary.mastery_changes if item.node_name != strongest_area]
            if not growth_candidates:
                growth_candidates = list(summary.mastery_changes)
            weakest = min(
                growth_candidates,
                key=lambda item: (item.after_mastery, item.delta, item.node_name),
            )
            return weakest.node_name
        return "下一轮综合应用"

    def _is_review_due(self, plan: Plan) -> bool:
        if plan.target_date is None:
            return False
        return self._today() >= (plan.target_date + timedelta(days=1))

    def _task_day_index(self, task: Task) -> int:
        order_index = int(task.order_index or 0)
        if order_index >= 1000:
            return max(order_index // 1000, 1)

        for tag in list(task.tags or []):
            tag_text = str(tag or "").strip().lower()
            if not tag_text.startswith("day:"):
                continue
            day = self._as_int(tag_text.split(":", maxsplit=1)[1])
            if day > 0:
                return day
        return 1

    @staticmethod
    def _task_status(task: Task) -> str:
        return str(getattr(task.status, "value", task.status) or TaskStatus.PENDING.value)

    @staticmethod
    def _window_end(*, start_at: datetime, exam_date: date | None) -> datetime:
        if exam_date is None:
            return _utcnow()
        return datetime.combine(max(exam_date, start_at.date()), time.max)

    @staticmethod
    def _today() -> date:
        return _utcnow().date()

    @staticmethod
    def _serialize_topic(item: ReviewTopicSelection) -> dict[str, Any]:
        return {
            "node_id": str(item.node_id) if item.node_id else None,
            "node_name": item.node_name,
        }

    @staticmethod
    def _serialize_plan_selection(item: ReviewPlanSelection) -> dict[str, Any]:
        return {
            "task_id": str(item.task_id) if item.task_id else None,
            "label": item.label,
        }

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            return round(float(value), 1)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _strip(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _as_int(value: Any, *, fallback: int = 0) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return fallback
        return fallback

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
