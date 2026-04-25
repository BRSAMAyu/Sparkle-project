from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.error_book import ErrorRecord
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import (
    PostExamReviewRequest,
    PostExamReviewResponse,
    ReviewPlanSelection,
    ReviewTopicSelection,
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
from app.services.notification_service import NotificationService
from app.services.plan_service import PlanService
from app.services.plan_state_service import PlanStateService
from app.services.profile_write_service import ProfileWriteService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExamSprintReviewService:
    REVIEW_ARCHIVE_KEY = "exam_sprint_growth_archive"
    LAST_REVIEW_KEY = "exam_sprint_last_review"
    MASTERY_COVERAGE_THRESHOLD = 60.0
    ERROR_REPAIR_THRESHOLD = 0.8
    MAX_ARCHIVE_ENTRIES = 10

    def __init__(self, db: AsyncSession, redis_client=None) -> None:
        self.db = db
        self.redis = redis_client or cache_service.redis

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
        await self._persist_growth_archive(
            user_id=user_id,
            review_id=review_id,
            plan=archived_plan,
            request=request,
            summary=final_summary,
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
            narrative_highlights.append(
                f"错题修复率达到 {round(error_recovery.repair_rate * 100)}%。"
            )

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
            plan for plan in candidates
            if self._is_review_due(plan) and not self._build_invitation_status(plan).completed_at
        ]
        if due_pending:
            return due_pending[0]

        if require_due:
            raise ValueError("考试结束满 24 小时后才能进入复盘")
        return candidates[0]

    async def _load_plan_tasks(self, plan_id: UUID) -> list[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.plan_id == plan_id, Task.deleted_at.is_(None))
            .order_by(Task.created_at.asc())
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
        result = await self.db.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user_id)
        )
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
                await engine.process_event(str(user_id), AchievementEvent.SPRINT_PERFECT, completion_rate=completion_rate)
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
            "sparkle_helped": request.sparkle_helped,
            "helpful_features": [item.value for item in request.helpful_features],
            "underprepared_topics": [self._serialize_topic(item) for item in request.underprepared_topics],
            "prepared_but_not_tested_topics": [
                self._serialize_plan_selection(item) for item in request.prepared_but_not_tested_topics
            ],
            "summary": summary.model_dump(mode="json"),
        }
        entries.append(archive_entry)
        entries = entries[-self.MAX_ARCHIVE_ENTRIES :]

        latest_review = {
            "review_id": review_id,
            "subject": plan.subject,
            "exam_date": plan.target_date.isoformat() if plan.target_date else None,
            "self_rating": request.self_rating,
            "sparkle_helped": request.sparkle_helped,
            "helpful_features": [item.value for item in request.helpful_features],
            "underprepared_topics": [item.node_name for item in request.underprepared_topics],
            "prepared_but_not_tested_topics": [item.label for item in request.prepared_but_not_tested_topics],
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

    def _is_review_due(self, plan: Plan) -> bool:
        if plan.target_date is None:
            return False
        return self._today() >= (plan.target_date + timedelta(days=1))

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
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
