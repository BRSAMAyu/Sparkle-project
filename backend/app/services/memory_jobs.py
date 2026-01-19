from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    MEMORY_JOB_RUNS_TOTAL,
    EVIDENCE_MISSING_CURRENT,
    REPAIR_SUCCESS_TOTAL,
)
from app.models.user import User
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory
from app.models.ltm_daily_snapshot import LtmDailySnapshot
from app.services.analytics.behavior_pattern_decay_service import BehaviorPatternDecayService
from app.services.evidence_health_service import EvidenceHealthService
from app.services.evidence_scoring import compute_score
from app.services.ltm_health_snapshot import LtmHealthSnapshotService
from loguru import logger


_JOB_STATUS: Dict[str, Dict[str, Any]] = {}
_JOB_HISTORY: Dict[str, list[Dict[str, Any]]] = {}


class MemoryJobsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def get_status(cls) -> Dict[str, Dict[str, Any]]:
        return dict(_JOB_STATUS)

    @classmethod
    def get_history(cls) -> Dict[str, list[Dict[str, Any]]]:
        return {job: list(entries) for job, entries in _JOB_HISTORY.items()}

    async def run_evidence_health_job(self, limit_per_type: int = 200) -> Dict[str, Any]:
        if not settings.ENABLE_EVIDENCE_HEALTH_JOB:
            return self._record_status("evidence_health", "disabled", {"reason": "flag_off"})

        logger.info("Memory evidence health job started limit_per_type={limit}", limit=limit_per_type)
        try:
            users = await self._get_active_users()
            totals = {"preferences": 0, "goals": 0, "episodic": 0}
            service = EvidenceHealthService(self.db)
            for user in users:
                counts = await service.run_health_check(user.id, limit=limit_per_type)
                for key in totals:
                    totals[key] += counts.get(key, 0)

            await self._update_missing_gauges()
            MEMORY_JOB_RUNS_TOTAL.labels(job="evidence_health", status="ok").inc()
            summary = {"users": len(users), "counts": totals}
            logger.info("Memory evidence health job completed users={users} counts={counts}", **summary)
            return self._record_status("evidence_health", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="evidence_health", status="error").inc()
            logger.error("Memory evidence health job failed: {error}", error=exc)
            return self._record_status("evidence_health", "error", {"error": str(exc)})

    async def run_decay_job(self, user_id: Optional[UUID] = None, window_days: int = 30) -> Dict[str, Any]:
        logger.info("Memory decay job started user_id={user_id} window_days={window}", user_id=user_id, window=window_days)
        try:
            users = await self._get_active_users(user_id)
            behavior_updated = 0
            if settings.ENABLE_BEHAVIOR_DECAY:
                decay_service = BehaviorPatternDecayService(self.db)
                for user in users:
                    behavior_updated += await decay_service.apply_decay(user.id, window_days=window_days)

            episodic_updated = 0
            if settings.ENABLE_MEMORY_DECAY:
                episodic_updated = await self._apply_episodic_decay(users, window_days)

            MEMORY_JOB_RUNS_TOTAL.labels(job="decay", status="ok").inc()
            summary = {
                "users": len(users),
                "behavior_patterns": behavior_updated,
                "episodic": episodic_updated,
            }
            logger.info("Memory decay job completed {summary}", summary=summary)
            return self._record_status("decay", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="decay", status="error").inc()
            logger.error("Memory decay job failed: {error}", error=exc)
            return self._record_status("decay", "error", {"error": str(exc)})

    async def run_repair_job(self, limit: int = 200) -> Dict[str, Any]:
        logger.info("Memory repair job started limit={limit}", limit=limit)
        try:
            repaired = 0
            service = EvidenceHealthService(self.db)
            for model, kind in (
                (MemoryPreference, "preference"),
                (MemoryGoal, "goal"),
                (EpisodicMemory, "episodic"),
            ):
                items = await self._get_missing(model, limit)
                for item in items:
                    result = await service.check_memory_item(item, item.user_id)
                    if not result["missing"]:
                        item.evidence_missing = False
                        item.evidence_checked_at = datetime.utcnow()
                        item.evidence_score = compute_score(
                            item.evidence_refs or [],
                            evidence_missing=False,
                        )
                        if isinstance(item, EpisodicMemory):
                            item.evidence_snapshot = result["snapshot"]
                        repaired += 1
                        REPAIR_SUCCESS_TOTAL.inc()

            await self.db.commit()
            await self._update_missing_gauges()
            MEMORY_JOB_RUNS_TOTAL.labels(job="repair", status="ok").inc()
            summary = {"repaired": repaired}
            logger.info("Memory repair job completed repaired={repaired}", repaired=repaired)
            return self._record_status("repair", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="repair", status="error").inc()
            logger.error("Memory repair job failed: {error}", error=exc)
            return self._record_status("repair", "error", {"error": str(exc)})

    async def run_daily_summary_job(self) -> Dict[str, Any]:
        if not settings.ENABLE_MEMORY_DAILY_SUMMARY:
            return self._record_status("daily_summary", "disabled", {"reason": "flag_off"})

        logger.info("Memory daily summary job started")
        try:
            service = LtmHealthSnapshotService(self.db)
            snapshot = await service.compute_snapshot()
            today = datetime.utcnow().date()
            result = await self.db.execute(
                select(LtmDailySnapshot).where(
                    LtmDailySnapshot.snapshot_date == today,
                    LtmDailySnapshot.deleted_at.is_(None),
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = LtmDailySnapshot(snapshot_date=today, payload=snapshot)
                self.db.add(record)
            else:
                record.payload = snapshot
                record.updated_at = datetime.utcnow()

            await self.db.commit()
            MEMORY_JOB_RUNS_TOTAL.labels(job="daily_summary", status="ok").inc()
            summary = {"snapshot_date": today.isoformat()}
            logger.info("Memory daily summary job completed date={date}", date=today)
            return self._record_status("daily_summary", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="daily_summary", status="error").inc()
            logger.error("Memory daily summary job failed: {error}", error=exc)
            return self._record_status("daily_summary", "error", {"error": str(exc)})

    async def _get_active_users(self, user_id: Optional[UUID] = None) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True))
        if user_id is not None:
            stmt = stmt.where(User.id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_missing(self, model, limit: int) -> list[Any]:
        conditions = [model.evidence_missing.is_(True), model.deleted_at.is_(None)]
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        result = await self.db.execute(
            select(model)
            .where(*conditions)
            .order_by(model.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _apply_episodic_decay(self, users: list[User], window_days: int) -> int:
        if not users:
            return 0
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent_guard = datetime.utcnow() - timedelta(hours=24)
        user_ids = [user.id for user in users]
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id.in_(user_ids),
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.occurred_at <= cutoff,
                EpisodicMemory.updated_at <= recent_guard,
                EpisodicMemory.importance_score.isnot(None),
            )
        )
        records = result.scalars().all()
        updated = 0
        for record in records:
            record.importance_score = max(0.0, float(record.importance_score or 0.0) * 0.98)
            record.updated_at = datetime.utcnow()
            updated += 1
        if updated:
            await self.db.commit()
        return updated

    async def _update_missing_gauges(self) -> None:
        for model, kind in (
            (MemoryPreference, "preference"),
            (MemoryGoal, "goal"),
            (EpisodicMemory, "episodic"),
        ):
            conditions = [model.evidence_missing.is_(True), model.deleted_at.is_(None)]
            if hasattr(model, "retracted_at"):
                conditions.append(model.retracted_at.is_(None))
            result = await self.db.execute(select(func.count(model.id)).where(*conditions))
            count = result.scalar() or 0
            EVIDENCE_MISSING_CURRENT.labels(type=kind).set(count)

    def _record_status(self, job: str, status: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "job": job,
            "status": status,
            "detail": detail,
            "updated_at": datetime.utcnow(),
        }
        _JOB_STATUS[job] = payload
        history = _JOB_HISTORY.setdefault(job, [])
        history.append(payload)
        if len(history) > 200:
            history.pop(0)
        return payload
