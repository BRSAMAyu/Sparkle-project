from __future__ import annotations

from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    EVIDENCE_MISSING_CURRENT,
    MEMORY_JOB_RUNS_TOTAL,
    REPAIR_SUCCESS_TOTAL,
)
from app.models.ltm_daily_snapshot import LtmDailySnapshot
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.models.user import User
from app.services.analytics.behavior_pattern_decay_service import BehaviorPatternDecayService
from app.services.evidence_health_service import EvidenceHealthService
from app.services.evidence_scoring import compute_score
from app.services.ltm_health_snapshot import LtmHealthSnapshotService
from app.services.system_update_service import SystemUpdateService, build_system_update

_JOB_STATUS: dict[str, dict[str, Any]] = {}
_JOB_HISTORY: dict[str, list[dict[str, Any]]] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MemoryJobsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def get_status(cls) -> dict[str, dict[str, Any]]:
        return dict(_JOB_STATUS)

    @classmethod
    def get_history(cls) -> dict[str, list[dict[str, Any]]]:
        return {job: list(entries) for job, entries in _JOB_HISTORY.items()}

    async def run_evidence_health_job(self, limit_per_type: int = 200) -> dict[str, Any]:
        if not settings.ENABLE_EVIDENCE_HEALTH_JOB:
            return self._record_status("evidence_health", "disabled", {"reason": "flag_off"})

        logger.info("Memory evidence health job started limit_per_type={limit}", limit=limit_per_type)
        try:
            users = await self._get_active_users()
            totals = {"preferences": 0, "goals": 0, "episodic": 0}
            missing_totals = {"preferences": 0, "goals": 0, "episodic": 0}
            service = EvidenceHealthService(self.db)
            for user in users:
                summary = await service.run_health_check(user.id, limit=limit_per_type)
                checked = summary.get("checked", {})
                missing = summary.get("missing", {})
                checked_total = sum(checked.values())
                missing_total = sum(missing.values())

                for key in totals:
                    totals[key] += checked.get(key, 0)
                    missing_totals[key] += missing.get(key, 0)

                if checked_total > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="memory_health_report",
                            category="memory",
                            title="记忆健康检查完成",
                            description=f"已核对 {checked_total} 条记忆记录，整体状态已更新。",
                            priority="low",
                            metadata={
                                "checked": checked,
                                "missing": missing,
                            },
                        ),
                    )
                if missing_total > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="memory_evidence_missing",
                            category="memory",
                            title="发现需要补全的记忆证据",
                            description=f"有 {missing_total} 条记忆证据暂时缺失，已记录并安排修复。",
                            priority="low",
                            metadata={
                                "missing": missing,
                            },
                        ),
                    )

            await self._update_missing_gauges()
            MEMORY_JOB_RUNS_TOTAL.labels(job="evidence_health", status="ok").inc()
            summary = {"users": len(users), "counts": totals, "missing": missing_totals}
            logger.info("Memory evidence health job completed users={users} counts={counts}", **summary)
            return self._record_status("evidence_health", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="evidence_health", status="error").inc()
            logger.error("Memory evidence health job failed: {error}", error=exc)
            return self._record_status("evidence_health", "error", {"error": str(exc)})

    async def run_decay_job(self, user_id: UUID | None = None, window_days: int = 14) -> dict[str, Any]:
        logger.info("Memory decay job started user_id={user_id} window_days={window}", user_id=user_id, window=window_days)
        try:
            users = await self._get_active_users(user_id)
            behavior_summary: dict[UUID, dict[str, int]] = {}
            if settings.ENABLE_BEHAVIOR_DECAY:
                decay_service = BehaviorPatternDecayService(self.db)
                for user in users:
                    behavior_summary[user.id] = await decay_service.apply_decay(
                        user.id,
                        window_days=window_days,
                    )

            episodic_summary: dict[UUID, int] = {}
            if settings.ENABLE_MEMORY_DECAY:
                episodic_summary = await self._apply_episodic_decay(users, window_days)
            governance_summary: dict[UUID, dict[str, int]] = {}
            if settings.ENABLE_MEMORY_GOVERNANCE:
                governance_summary = await self._apply_consumption_governance(users)

            for user in users:
                behavior = behavior_summary.get(user.id, {})
                behavior_updated = behavior.get("updated", 0)
                behavior_archived = behavior.get("archived", 0)
                behavior_decayed = max(0, behavior_updated - behavior_archived)
                if behavior_decayed > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="behavior_pattern_decayed",
                            category="cognitive",
                            title="行为模式已做轻微调整",
                            description=f"我们对 {behavior_decayed} 个行为模式做了轻微调整，让画像更贴近你。",
                            priority="low",
                            metadata={"count": behavior_decayed},
                        ),
                    )
                if behavior_archived > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="behavior_pattern_archived",
                            category="cognitive",
                            title="行为模式已归档",
                            description=f"已将 {behavior_archived} 个低置信度模式归档，减少不必要的干扰。",
                            priority="medium",
                            metadata={"count": behavior_archived},
                        ),
                    )
                episodic_updated = episodic_summary.get(user.id, 0)
                if episodic_updated > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="memory_decay_applied",
                            category="memory",
                            title="记忆重要性已自动调整",
                            description=f"随时间推移，有 {episodic_updated} 条记忆的重要性已自动调整。",
                            priority="low",
                            metadata={"count": episodic_updated},
                        ),
                    )
                governance = governance_summary.get(user.id, {})
                decayed = int(governance.get("decayed", 0) or 0)
                archived = int(governance.get("archived", 0) or 0)
                if decayed > 0 or archived > 0:
                    await SystemUpdateService().enqueue(
                        user.id,
                        build_system_update(
                            update_type="memory_governance_cleanup",
                            category="memory",
                            title="画像记录已做新鲜度治理",
                            description=f"本轮衰减了 {decayed} 条长期未消费记录，归档了 {archived} 条不再活跃的画像记录。",
                            priority="low",
                            metadata={
                                "decayed": decayed,
                                "archived": archived,
                            },
                        ),
                    )

            MEMORY_JOB_RUNS_TOTAL.labels(job="decay", status="ok").inc()
            summary = {
                "users": len(users),
                "behavior_patterns": sum(item.get("updated", 0) for item in behavior_summary.values()),
                "behavior_archived": sum(item.get("archived", 0) for item in behavior_summary.values()),
                "episodic": sum(episodic_summary.values()),
                "memory_governance_decayed": sum(item.get("decayed", 0) for item in governance_summary.values()),
                "memory_governance_archived": sum(item.get("archived", 0) for item in governance_summary.values()),
            }
            logger.info("Memory decay job completed {summary}", summary=summary)
            return self._record_status("decay", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="decay", status="error").inc()
            logger.error("Memory decay job failed: {error}", error=exc)
            return self._record_status("decay", "error", {"error": str(exc)})

    async def run_repair_job(self, limit: int = 200) -> dict[str, Any]:
        logger.info("Memory repair job started limit={limit}", limit=limit)
        try:
            repaired = 0
            repaired_by_user: dict[UUID, int] = {}
            service = EvidenceHealthService(self.db)
            for model, _kind in (
                (MemoryPreference, "preference"),
                (MemoryGoal, "goal"),
                (EpisodicMemory, "episodic"),
            ):
                items = await self._get_missing(model, limit)
                for item in items:
                    result = await service.check_memory_item(item, item.user_id)
                    if not result["missing"]:
                        item.evidence_missing = False
                        item.evidence_checked_at = _utcnow()
                        item.evidence_score = compute_score(
                            item.evidence_refs or [],
                            evidence_missing=False,
                        )
                        if isinstance(item, EpisodicMemory):
                            item.evidence_snapshot = result["snapshot"]
                        repaired += 1
                        repaired_by_user[item.user_id] = repaired_by_user.get(item.user_id, 0) + 1
                        REPAIR_SUCCESS_TOTAL.inc()

            await self.db.commit()
            await self._update_missing_gauges()
            for user_id, count in repaired_by_user.items():
                if count <= 0:
                    continue
                await SystemUpdateService().enqueue(
                    user_id,
                    build_system_update(
                        update_type="memory_evidence_repaired",
                        category="memory",
                        title="记忆证据已修复",
                        description=f"已修复 {count} 条记忆证据，系统稳定性已提升。",
                        priority="low",
                        metadata={"count": count},
                    ),
                )
            MEMORY_JOB_RUNS_TOTAL.labels(job="repair", status="ok").inc()
            summary = {"repaired": repaired}
            logger.info("Memory repair job completed repaired={repaired}", repaired=repaired)
            return self._record_status("repair", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="repair", status="error").inc()
            logger.error("Memory repair job failed: {error}", error=exc)
            return self._record_status("repair", "error", {"error": str(exc)})

    async def run_daily_summary_job(self) -> dict[str, Any]:
        if not settings.ENABLE_MEMORY_DAILY_SUMMARY:
            return self._record_status("daily_summary", "disabled", {"reason": "flag_off"})

        logger.info("Memory daily summary job started")
        try:
            service = LtmHealthSnapshotService(self.db)
            snapshot = await service.compute_snapshot()
            today = _utcnow().date()
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
                record.updated_at = _utcnow()

            await self.db.commit()
            MEMORY_JOB_RUNS_TOTAL.labels(job="daily_summary", status="ok").inc()
            summary = {"snapshot_date": today.isoformat()}
            logger.info("Memory daily summary job completed date={date}", date=today)
            return self._record_status("daily_summary", "ok", summary)
        except Exception as exc:
            MEMORY_JOB_RUNS_TOTAL.labels(job="daily_summary", status="error").inc()
            logger.error("Memory daily summary job failed: {error}", error=exc)
            return self._record_status("daily_summary", "error", {"error": str(exc)})

    async def _get_active_users(self, user_id: UUID | None = None) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True))
        if user_id is not None:
            stmt = stmt.where(User.id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_missing(self, model, limit: int) -> list[Any]:
        conditions = [model.evidence_missing.is_(True), model.deleted_at.is_(None)]
        if hasattr(model, "archived_at"):
            conditions.append(model.archived_at.is_(None))
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        result = await self.db.execute(
            select(model)
            .where(*conditions)
            .order_by(model.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _apply_episodic_decay(self, users: list[User], window_days: int) -> dict[UUID, int]:
        if not users:
            return {}
        cutoff = _utcnow() - timedelta(days=window_days)
        recent_guard = _utcnow() - timedelta(hours=24)
        updated_by_user: dict[UUID, int] = {}
        updated_any = False
        for user in users:
            result = await self.db.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user.id,
                    EpisodicMemory.deleted_at.is_(None),
                    EpisodicMemory.archived_at.is_(None),
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
                record.updated_at = _utcnow()
                updated += 1
            if updated > 0:
                updated_by_user[user.id] = updated
                updated_any = True
        if updated_any:
            await self.db.commit()
        return updated_by_user

    async def _update_missing_gauges(self) -> None:
        for model, kind in (
            (MemoryPreference, "preference"),
            (MemoryGoal, "goal"),
            (EpisodicMemory, "episodic"),
        ):
            conditions = [model.evidence_missing.is_(True), model.deleted_at.is_(None)]
            if hasattr(model, "archived_at"):
                conditions.append(model.archived_at.is_(None))
            if hasattr(model, "retracted_at"):
                conditions.append(model.retracted_at.is_(None))
            result = await self.db.execute(select(func.count(model.id)).where(*conditions))
            count = result.scalar() or 0
            EVIDENCE_MISSING_CURRENT.labels(type=kind).set(count)

    async def _apply_consumption_governance(self, users: list[User]) -> dict[UUID, dict[str, int]]:
        if not users:
            return {}

        now = _utcnow()
        sixty_days_ago = now - timedelta(days=60)
        ninety_days_ago = now - timedelta(days=90)
        summary: dict[UUID, dict[str, int]] = {}
        any_updates = False

        async def _process_model(model, *, score_fields: tuple[str, ...]) -> None:
            nonlocal any_updates
            for user in users:
                result = await self.db.execute(
                    select(model).where(
                        model.user_id == user.id,
                        model.deleted_at.is_(None),
                        model.archived_at.is_(None),
                        model.retracted_at.is_(None),
                    )
                )
                records = result.scalars().all()
                decayed = 0
                archived = 0
                for record in records:
                    last_consumed_at = getattr(record, "last_consumed_at", None) or record.updated_at or record.created_at
                    if not last_consumed_at:
                        continue
                    current_scores = [float(getattr(record, field) or 0.0) for field in score_fields if getattr(record, field, None) is not None]
                    current_signal = max(current_scores) if current_scores else 0.0
                    if last_consumed_at <= ninety_days_ago and current_signal < 0.3:
                        record.archived_at = now
                        archived += 1
                        any_updates = True
                        continue
                    if last_consumed_at <= sixty_days_ago:
                        changed = False
                        for field in score_fields:
                            value = getattr(record, field, None)
                            if value is None:
                                continue
                            setattr(record, field, max(0.0, float(value or 0.0) * 0.9))
                            changed = True
                        if changed:
                            decayed += 1
                            any_updates = True
                if decayed or archived:
                    bucket = summary.setdefault(user.id, {"decayed": 0, "archived": 0})
                    bucket["decayed"] += decayed
                    bucket["archived"] += archived

        await _process_model(MemoryPreference, score_fields=("confidence", "evidence_score"))
        await _process_model(MemoryGoal, score_fields=("evidence_score",))
        await _process_model(EpisodicMemory, score_fields=("importance_score", "evidence_score"))
        if any_updates:
            await self.db.commit()
        return summary

    def _record_status(self, job: str, status: str, detail: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "job": job,
            "status": status,
            "detail": detail,
            "updated_at": _utcnow(),
        }
        _JOB_STATUS[job] = payload
        history = _JOB_HISTORY.setdefault(job, [])
        history.append(payload)
        if len(history) > 200:
            history.pop(0)
        return payload
