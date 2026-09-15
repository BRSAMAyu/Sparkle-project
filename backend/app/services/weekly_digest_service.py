from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactStatus, ArtifactType, Card, CardType, PlanningArtifact
from app.models.cognitive import BehaviorPattern
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.analytics.weekly_stats_service import WeeklyStatsService
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.notification_push_service import NotificationPushService
from app.services.perceptible_intelligence_service import WeeklyLearningReportService
from app.services.planning_artifact_service import PlanningArtifactService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WeeklyDigestService:
    """Generate and deliver the user-facing weekly growth digest."""

    DIGEST_DEDUP_TTL_DAYS = 8
    DELIVERY_DEDUP_TTL_DAYS = 3

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.stats_service = WeeklyStatsService(db)
        self.growth_dashboard_service = GrowthDashboardService(db)
        self.weekly_report_service = WeeklyLearningReportService(db, redis)
        self.artifact_service = PlanningArtifactService(db)
        self.notification_service = NotificationPushService(db)

    async def generate_for_user(
        self,
        *,
        user_id: UUID,
        end_date: datetime | None = None,
        deliver: bool = True,
    ) -> dict[str, Any] | None:
        if await self._already_generated(user_id):
            return None

        end = end_date or _utcnow()
        start = end - timedelta(days=7)
        user = await self._get_user(user_id)
        growth_snapshot = await self.growth_dashboard_service.build_snapshot(user_id, user=user)
        weekly_report = await self.weekly_report_service.build_weekly_report(user_id=user_id)
        stats = await self.stats_service.get_weekly_summary(str(user_id), start, end)
        patterns = await self._recent_patterns(user_id)
        upcoming = await self._upcoming_tasks(user_id)

        digest = self._build_digest_payload(
            user=user,
            weekly_report=weekly_report,
            stats=stats,
            growth_snapshot=growth_snapshot,
            patterns=patterns,
            upcoming=upcoming,
            start=start,
            end=end,
        )
        if not digest:
            return None

        artifact: PlanningArtifact | None = None
        plan_card = await self._resolve_active_plan_card(user_id)
        if plan_card is not None:
            artifact = await self._store_artifact(plan_card.id, digest)
            digest["artifact_id"] = str(artifact.id) if artifact else None
            await self.db.commit()
        elif not deliver:
            logger.warning(f"Weekly digest skipped for {user_id}: no active plan card for deferred delivery")
            return None

        if deliver:
            await self._deliver_and_mark_artifact(
                user_id=user_id,
                digest=digest,
                artifact=artifact,
            )
            await self._mark_delivered(user_id)
        await self._mark_generated(user_id)
        return digest

    async def generate_for_active_users(self, *, limit: int = 200, deliver: bool = True) -> dict[str, int]:
        user_ids = await self._active_user_ids(limit=limit)
        generated = 0
        skipped = 0
        for user_id in user_ids:
            try:
                digest = await self.generate_for_user(user_id=user_id, deliver=deliver)
                if digest:
                    generated += 1
                else:
                    skipped += 1
            except Exception as exc:
                skipped += 1
                logger.warning(f"Failed to generate weekly digest for {user_id}: {exc}")
        return {"active_users": len(user_ids), "generated": generated, "skipped": skipped}

    async def deliver_for_active_users(self, *, limit: int = 200) -> dict[str, int]:
        user_ids = await self._active_user_ids(limit=limit)
        delivered = 0
        skipped = 0
        for user_id in user_ids:
            try:
                digest = await self.deliver_pending_for_user(user_id=user_id)
                if digest:
                    delivered += 1
                else:
                    skipped += 1
            except Exception as exc:
                skipped += 1
                logger.warning(f"Failed to deliver weekly digest for {user_id}: {exc}")
        return {"active_users": len(user_ids), "delivered": delivered, "skipped": skipped}

    async def deliver_pending_for_user(self, *, user_id: UUID) -> dict[str, Any] | None:
        if await self._already_delivered(user_id):
            return None

        artifact = await self._latest_pending_digest_artifact(user_id)
        if artifact is None:
            return await self.generate_for_user(user_id=user_id, deliver=True)

        digest = artifact.payload if isinstance(artifact.payload, dict) else {}
        if digest.get("digest_kind") != "weekly_growth_digest":
            return None
        if not str(digest.get("summary") or "").strip():
            return None

        await self._deliver_and_mark_artifact(
            user_id=user_id,
            digest=digest,
            artifact=artifact,
        )
        await self._mark_delivered(user_id)
        return digest

    def _build_digest_payload(
        self,
        *,
        user: User,
        weekly_report: dict[str, Any] | None,
        stats: dict[str, Any],
        growth_snapshot: dict[str, Any],
        patterns: list[BehaviorPattern],
        upcoming: list[dict[str, Any]],
        start: datetime,
        end: datetime,
    ) -> dict[str, Any] | None:
        growth_status = growth_snapshot.get("growth_status") if isinstance(growth_snapshot, dict) else {}
        growth_signal = growth_snapshot.get("growth_signal") if isinstance(growth_snapshot, dict) else {}
        plan_progress = growth_snapshot.get("active_plan_progress") if isinstance(growth_snapshot, dict) else {}
        report_items = (weekly_report or {}).get("top_learning_items") or []

        what_you_did = [
            f"完成了 {int(stats.get('tasks_completed') or 0)} 个任务",
            f"累计专注 {int(stats.get('focus_duration_minutes') or 0)} 分钟",
            f"活跃了 {int(stats.get('active_days') or 0)} 天",
        ]
        what_moved: list[str] = []
        if isinstance(growth_signal, dict) and growth_signal.get("summary"):
            what_moved.append(str(growth_signal["summary"]))
        if float(stats.get("mastery_gain") or 0.0) > 0:
            what_moved.append(
                f"累计掌握度提升约 {float(stats.get('mastery_gain') or 0.0):.1f}，覆盖 {int(stats.get('nodes_learned') or 0)} 个知识点。"
            )

        system_noticed: list[str] = []
        if patterns:
            top = patterns[0]
            system_noticed.append(
                f"你最近更容易出现「{top.pattern_name}」模式，我会继续按这个规律调整建议。"
            )
        if isinstance(weekly_report, dict) and weekly_report.get("one_key_adjustment"):
            system_noticed.append(str(weekly_report["one_key_adjustment"]))

        whats_coming = [
            item["title"]
            for item in upcoming
            if str(item.get("title") or "").strip()
        ][:3]

        display_name = str(user.nickname or user.full_name or user.username or "你").strip()
        headline = str((growth_status or {}).get("headline") or f"{display_name}，这是你本周的成长摘要").strip()
        summary = str((weekly_report or {}).get("weekly_summary") or "").strip()
        if not summary and what_moved:
            summary = what_moved[0]
        if not summary and report_items:
            summary = str(report_items[0].get("text") or "").strip()
        if not summary:
            return None

        return {
            "digest_kind": "weekly_growth_digest",
            "headline": headline,
            "summary": summary,
            "user_name": display_name,
            "period_start": start.date().isoformat(),
            "period_end": end.date().isoformat(),
            "what_you_did": what_you_did,
            "what_moved": what_moved[:3],
            "system_noticed": system_noticed[:2],
            "whats_coming": whats_coming,
            "growth_signal": growth_signal,
            "active_plan_progress": plan_progress,
            "weekly_report": weekly_report or {},
            "delivery_scheduled_for": self._delivery_datetime().isoformat(),
            "generated_at": _utcnow().isoformat(),
        }

    async def _deliver_digest(self, *, user_id: UUID, digest: dict[str, Any]) -> None:
        data = {
            "destination_route": "/home",
            "digest_kind": digest.get("digest_kind"),
            "generated_at": digest.get("generated_at"),
            "delivery_scheduled_for": digest.get("delivery_scheduled_for"),
            "summary": digest.get("summary"),
            "whats_coming": digest.get("whats_coming"),
            "artifact_id": digest.get("artifact_id"),
        }
        await self.notification_service.create_and_push(
            user_id=user_id,
            title=str(digest.get("headline") or "本周成长摘要"),
            content=str(digest.get("summary") or "本周的关键变化已经整理好了。"),
            notification_type="weekly_digest",
            data=data,
            priority="high",
        )

    async def _deliver_and_mark_artifact(
        self,
        *,
        user_id: UUID,
        digest: dict[str, Any],
        artifact: PlanningArtifact | None,
    ) -> None:
        await self._deliver_digest(user_id=user_id, digest=digest)
        delivered_at = _utcnow().isoformat()
        digest["delivered_at"] = delivered_at
        if artifact is not None:
            artifact.payload = {**(artifact.payload or {}), **digest}
            await self.db.commit()

    async def _store_artifact(self, plan_card_id: UUID, digest: dict[str, Any]):
        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.REFLECTION_REPORT,
            payload=digest,
            created_by_agent="weekly_digest_service",
        )
        await self.artifact_service.propose_artifact(artifact.id)
        return await self.artifact_service.auto_approve_artifact(artifact.id)

    async def _resolve_active_plan_card(self, user_id: UUID) -> Card | None:
        plan = await self._active_plan(user_id)
        if not plan:
            return None
        stmt = select(Card).where(
            Card.card_type == CardType.PLAN,
            Card.owner_id == user_id,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan.id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _active_plan(self, user_id: UUID) -> Plan | None:
        stmt = (
            select(Plan)
            .where(Plan.user_id == user_id, Plan.is_active.is_(True))
            .order_by(desc(Plan.is_primary), Plan.target_date, desc(Plan.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _recent_patterns(self, user_id: UUID) -> list[BehaviorPattern]:
        cutoff = _utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(BehaviorPattern)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.is_archived.is_(False),
                or_(
                    BehaviorPattern.last_observed_at.is_(None),
                    BehaviorPattern.last_observed_at >= cutoff,
                ),
            )
            .order_by(desc(BehaviorPattern.confidence_score), desc(BehaviorPattern.frequency))
            .limit(2)
        )
        return list(result.scalars().all())

    async def _upcoming_tasks(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
            )
            .order_by(desc(Task.priority), Task.due_date, Task.created_at)
            .limit(3)
        )
        return [
            {
                "id": str(task.id),
                "title": task.title,
                "estimated_minutes": int(task.estimated_minutes or 0),
            }
            for task in result.scalars().all()
        ]

    async def _active_user_ids(self, *, limit: int) -> list[UUID]:
        return await self.weekly_report_service._active_user_ids(limit=limit)

    async def _latest_pending_digest_artifact(self, user_id: UUID) -> PlanningArtifact | None:
        result = await self.db.execute(
            select(PlanningArtifact)
            .join(Card, Card.id == PlanningArtifact.plan_card_id)
            .where(
                Card.owner_id == user_id,
                PlanningArtifact.artifact_type == ArtifactType.REFLECTION_REPORT,
                PlanningArtifact.status == ArtifactStatus.APPROVED,
                PlanningArtifact.created_by_agent == "weekly_digest_service",
                PlanningArtifact.created_at >= self._generation_window_start(),
                PlanningArtifact.not_deleted_filter(),
            )
            .order_by(desc(PlanningArtifact.created_at), desc(PlanningArtifact.version))
        )
        for artifact in result.scalars().all():
            payload = artifact.payload if isinstance(artifact.payload, dict) else {}
            if payload.get("digest_kind") != "weekly_growth_digest":
                continue
            if payload.get("delivered_at"):
                continue
            return artifact
        return None

    async def _already_generated(self, user_id: UUID) -> bool:
        if not self.redis:
            return False
        try:
            return bool(await self.redis.exists(self._digest_key(user_id)))
        except Exception as exc:
            logger.warning(f"Failed to check weekly digest dedupe key: {exc}")
            return False

    async def _mark_generated(self, user_id: UUID) -> None:
        if not self.redis:
            return
        try:
            await self.redis.setex(
                self._digest_key(user_id),
                int(timedelta(days=self.DIGEST_DEDUP_TTL_DAYS).total_seconds()),
                "1",
            )
        except Exception as exc:
            logger.warning(f"Failed to persist weekly digest dedupe key: {exc}")

    async def _already_delivered(self, user_id: UUID) -> bool:
        if not self.redis:
            return False
        try:
            return bool(await self.redis.exists(self._delivery_key(user_id)))
        except Exception as exc:
            logger.warning(f"Failed to check weekly digest delivery key: {exc}")
            return False

    async def _mark_delivered(self, user_id: UUID) -> None:
        if not self.redis:
            return
        try:
            await self.redis.setex(
                self._delivery_key(user_id),
                int(timedelta(days=self.DELIVERY_DEDUP_TTL_DAYS).total_seconds()),
                "1",
            )
        except Exception as exc:
            logger.warning(f"Failed to persist weekly digest delivery key: {exc}")

    def _digest_key(self, user_id: UUID) -> str:
        monday = self._cycle_monday().isoformat()
        return f"weekly_growth_digest:{user_id}:{monday}"

    def _delivery_key(self, user_id: UUID) -> str:
        monday = self._cycle_monday().isoformat()
        return f"weekly_growth_digest:delivered:{user_id}:{monday}"

    def _cycle_monday(self, ref: datetime | None = None):
        anchor = (ref or _utcnow()).date()
        if anchor.weekday() == 6:
            return anchor + timedelta(days=1)
        return anchor - timedelta(days=anchor.weekday())

    def _generation_window_start(self, ref: datetime | None = None) -> datetime:
        sunday = self._cycle_monday(ref) - timedelta(days=1)
        return datetime.combine(sunday, datetime.min.time())

    def _delivery_datetime(self, ref: datetime | None = None) -> datetime:
        monday = self._cycle_monday(ref)
        return datetime.combine(monday, datetime.min.time()).replace(hour=8)
