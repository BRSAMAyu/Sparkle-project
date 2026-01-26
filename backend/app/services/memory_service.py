from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory, MemoryCorrection
from app.config import settings
from app.core.business_metrics import MEMORY_WRITE_TOTAL, MEMORY_RETRACTION_TOTAL, MEMORY_CORRECTION_TOTAL
from app.core.memory_constants import PREFERENCE_KEYS
from app.services.evidence_scoring import compute_score
from app.services.evidence_health_service import EvidenceHealthService
from app.services.memory_policy_evaluator import MemoryPolicyEvaluator
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.system_update_service import SystemUpdateService, build_system_update
from loguru import logger


ALLOWED_EVIDENCE_TYPES = {
    "event",
    "user_state",
    "error",
    "concept",
    "strategy",
    "task",
    "summary",
}

INACTIVE_GOAL_STATUSES = {"completed", "archived", "cancelled"}
CONFIDENCE_DECREMENT = 0.1
SUMMARY_MAX_LEN = 48


def _truncate_summary(value: str) -> str:
    if not value:
        return ""
    if len(value) <= SUMMARY_MAX_LEN:
        return value
    return f"{value[:SUMMARY_MAX_LEN - 1]}…"


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_preference(
        self,
        user_id: UUID,
        pref_key: str,
        pref_value: Dict[str, Any],
        evidence_refs: Iterable[Any],
        confidence: Optional[float] = None,
        source_type: Optional[str] = None,
    ) -> Optional[MemoryPreference]:
        if pref_key not in PREFERENCE_KEYS:
            raise ValueError(f"Unsupported pref_key: {pref_key}")
        if not await self._allow_write(
            user_id=user_id,
            kind="preference",
            pref_key=pref_key,
            source_type=source_type,
        ):
            MEMORY_WRITE_TOTAL.labels(type="preference", status="blocked").inc()
            return None
        normalized_refs = _normalize_evidence_refs(evidence_refs, require_non_empty=True)

        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.pref_key == pref_key,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        version = 1 if latest is None else latest.version + 1

        evidence_score = compute_score(normalized_refs, evidence_missing=False)
        record = MemoryPreference(
            user_id=user_id,
            pref_key=pref_key,
            pref_value=pref_value,
            version=version,
            replaced_by_id=None,
            confidence=confidence,
            evidence_refs=normalized_refs,
            evidence_score=evidence_score,
            correction_count=0,
        )
        self.db.add(record)
        await self.db.flush()

        if latest is not None:
            latest.replaced_by_id = record.id
            latest.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_WRITE_TOTAL.labels(type="preference", status="ok").inc()
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_preference_updated",
                category="memory",
                title=f"更新了偏好：{pref_key}",
                description="已记录你的最新学习偏好",
                priority="low",
                metadata={
                    "pref_key": pref_key,
                    "version": record.version,
                },
            ),
        )
        return record

    async def create_goal(
        self,
        user_id: UUID,
        title: str,
        status: str = "active",
        target_date: Optional[date] = None,
        expires_at: Optional[datetime] = None,
        linked_task_id: Optional[UUID] = None,
        linked_plan_id: Optional[UUID] = None,
        evidence_refs: Optional[Iterable[Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_type: Optional[str] = None,
    ) -> Optional[MemoryGoal]:
        if not await self._allow_write(
            user_id=user_id,
            kind="goal",
            source_type=source_type,
        ):
            MEMORY_WRITE_TOTAL.labels(type="goal", status="blocked").inc()
            return None
        normalized_refs = _normalize_evidence_refs(evidence_refs or [], require_non_empty=False)
        evidence_score = compute_score(normalized_refs, evidence_missing=False)
        record = MemoryGoal(
            user_id=user_id,
            title=title,
            status=status,
            target_date=target_date,
            expires_at=expires_at,
            linked_task_id=linked_task_id,
            linked_plan_id=linked_plan_id,
            evidence_refs=normalized_refs,
            metadata_payload=metadata,
            evidence_score=evidence_score,
            correction_count=0,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_WRITE_TOTAL.labels(type="goal", status="ok").inc()
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_goal_created",
                category="goal",
                title=f"记录了目标：{_truncate_summary(title)}",
                description="学习目标已保存",
                priority="medium",
                metadata={
                    "goal_id": str(record.id),
                    "status": record.status,
                },
            ),
        )
        return record

    async def update_goal(
        self,
        user_id: UUID,
        goal_id: UUID,
        **updates: Any,
    ) -> Optional[MemoryGoal]:
        result = await self.db.execute(
            select(MemoryGoal).where(
                MemoryGoal.user_id == user_id,
                MemoryGoal.id == goal_id,
                MemoryGoal.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        if "evidence_refs" in updates:
            updates["evidence_refs"] = _normalize_evidence_refs(
                updates["evidence_refs"] or [],
                require_non_empty=False,
            )

        if "evidence_refs" in updates or "evidence_missing" in updates:
            evidence_missing = updates.get("evidence_missing", record.evidence_missing)
            evidence_refs = updates.get("evidence_refs", record.evidence_refs)
            updates["evidence_score"] = compute_score(evidence_refs, evidence_missing=evidence_missing)

        if "metadata" in updates:
            updates["metadata_payload"] = updates.pop("metadata")

        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)

        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_WRITE_TOTAL.labels(type="episodic", status="ok").inc()
        return record

    async def list_active_goals(self, user_id: UUID, now: Optional[datetime] = None) -> List[MemoryGoal]:
        now = now or datetime.utcnow()
        result = await self.db.execute(
            select(MemoryGoal).where(
                MemoryGoal.user_id == user_id,
                MemoryGoal.deleted_at.is_(None),
                MemoryGoal.retracted_at.is_(None),
                ~MemoryGoal.status.in_(INACTIVE_GOAL_STATUSES),
                (MemoryGoal.expires_at.is_(None) | (MemoryGoal.expires_at > now)),
            )
        )
        return list(result.scalars().all())

    async def list_preferences(self, user_id: UUID) -> Dict[str, Any]:
        records = await self.list_preference_records(user_id)
        latest_by_key: Dict[str, Any] = {}
        for record in records:
            latest_by_key[record.pref_key] = record.pref_value
        return latest_by_key

    async def list_preference_records(self, user_id: UUID) -> List[MemoryPreference]:
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
        )
        latest_by_key: Dict[str, MemoryPreference] = {}
        for record in result.scalars().all():
            if record.pref_key not in latest_by_key:
                latest_by_key[record.pref_key] = record
        return list(latest_by_key.values())

    async def list_preference_history(self, user_id: UUID) -> List[MemoryPreference]:
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
        )
        return list(result.scalars().all())

    async def list_recent_episodic(
        self,
        user_id: UUID,
        limit: int = 10,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[EpisodicMemory]:
        stmt = select(EpisodicMemory).where(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.retracted_at.is_(None),
        )
        if start:
            stmt = stmt.where(EpisodicMemory.occurred_at >= start)
        if end:
            stmt = stmt.where(EpisodicMemory.occurred_at <= end)
        stmt = stmt.order_by(EpisodicMemory.occurred_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_episodic_memory(
        self,
        user_id: UUID,
        summary: str,
        source_type: str,
        source_id: Optional[str],
        occurred_at: datetime,
        importance_score: Optional[float],
        tags: Optional[List[str]],
        evidence_refs: Iterable[Any],
        embedding: Optional[List[float]] = None,
    ) -> Optional[EpisodicMemory]:
        if not await self._allow_write(
            user_id=user_id,
            kind="episodic",
            source_type=source_type,
        ):
            MEMORY_WRITE_TOTAL.labels(type="episodic", status="blocked").inc()
            return None
        normalized_refs = _normalize_evidence_refs(evidence_refs, require_non_empty=True)
        # TODO: enforce per-session rate limits (1-2 memories) once session tracking is available.
        evidence_score = compute_score(normalized_refs, evidence_missing=False)
        evidence_snapshot = None
        if settings.ENABLE_EVIDENCE_SNAPSHOT_ON_WRITE and await self._advanced_features_enabled(user_id):
            resolver = EvidenceHealthService(self.db)
            resolved = await resolver.resolve_evidence_refs(normalized_refs, user_id)
            evidence_snapshot = EvidenceHealthService.build_snapshot(resolved)
        record = EpisodicMemory(
            user_id=user_id,
            summary=summary,
            source_type=source_type,
            source_id=source_id,
            occurred_at=occurred_at,
            importance_score=importance_score,
            tags=tags,
            evidence_refs=normalized_refs,
            evidence_snapshot=evidence_snapshot,
            embedding=embedding,
            evidence_score=evidence_score,
            correction_count=0,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_created",
                category="memory",
                title=f"记住了：{_truncate_summary(summary)}",
                description="已写入长期记忆",
                priority="low",
                metadata={
                    "memory_id": str(record.id),
                    "source_type": source_type,
                },
            ),
        )
        return record

    async def retract_memory(
        self,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None,
    ) -> bool:
        if not settings.ENABLE_MEMORY_RETRACTION:
            raise ValueError("Memory retraction is disabled by feature flag")

        model = {
            "preference": MemoryPreference,
            "goal": MemoryGoal,
            "episodic": EpisodicMemory,
        }.get(kind)
        if model is None:
            raise ValueError(f"Unsupported memory kind: {kind}")

        result = await self.db.execute(
            select(model).where(
                model.id == memory_id,
                model.user_id == user_id,
                model.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False

        self._apply_retraction(record, reason)

        await self.db.commit()
        MEMORY_RETRACTION_TOTAL.labels(type=kind).inc()
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_retracted",
                category="memory",
                title="移除了记忆",
                description="已按你的请求删除记录",
                priority="medium",
                metadata={
                    "memory_type": kind,
                    "memory_id": str(memory_id),
                },
            ),
        )
        return True

    async def apply_correction(
        self,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        action: str,
        reason: Optional[str] = None,
    ) -> Optional[Any]:
        if not settings.ENABLE_MEMORY_CORRECTION:
            raise ValueError("Memory correction is disabled by feature flag")

        model = {
            "preference": MemoryPreference,
            "goal": MemoryGoal,
            "episodic": EpisodicMemory,
        }.get(kind)
        if model is None:
            raise ValueError(f"Unsupported memory kind: {kind}")

        result = await self.db.execute(
            select(model).where(
                model.id == memory_id,
                model.user_id == user_id,
                model.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        if action in {"reject", "no_longer_applicable"}:
            if not settings.ENABLE_MEMORY_RETRACTION:
                raise ValueError("Memory retraction is disabled by feature flag")
            reason_label = reason or action
            self._apply_retraction(record, reason_label)
            MEMORY_RETRACTION_TOTAL.labels(type=kind).inc()
        elif action == "lower_confidence":
            if hasattr(record, "confidence"):
                current = record.confidence or 0.0
                record.confidence = max(0.0, current - CONFIDENCE_DECREMENT)
            else:
                current_score = record.evidence_score or 0.0
                record.evidence_score = max(0.0, current_score - CONFIDENCE_DECREMENT)
            record.updated_at = datetime.utcnow()
        else:
            raise ValueError(f"Unsupported correction action: {action}")

        record.correction_count = (record.correction_count or 0) + 1
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type=kind,
                memory_id=record.id,
                action=action,
                reason=reason,
            )
        )

        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_CORRECTION_TOTAL.labels(type=kind, action=action).inc()
        logger.info(
            "Memory correction applied user_id={user_id} memory_id={memory_id} action={action}",
            user_id=user_id,
            memory_id=record.id,
            action=action,
        )
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_corrected",
                category="memory",
                title="收到纠错反馈",
                description="系统会调整你的画像与记忆",
                priority="medium",
                metadata={
                    "memory_type": kind,
                    "memory_id": str(record.id),
                    "action": action,
                },
            ),
        )
        return record

    def _apply_retraction(self, record: Any, reason: Optional[str]) -> None:
        updated_refs = []
        for ref in record.evidence_refs or []:
            ref_copy = dict(ref)
            ref_copy["user_deleted"] = True
            if reason and "retraction_reason" not in ref_copy:
                ref_copy["retraction_reason"] = reason
            updated_refs.append(ref_copy)

        record.evidence_refs = updated_refs
        record.retracted_at = datetime.utcnow()
        record.updated_at = datetime.utcnow()

        if isinstance(record, EpisodicMemory):
            snapshot = record.evidence_snapshot or {}
            snapshot["retraction_reason"] = reason
            snapshot["evidence_refs"] = updated_refs
            record.evidence_snapshot = snapshot

    async def _allow_write(
        self,
        user_id: UUID,
        kind: str,
        pref_key: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> bool:
        if not settings.ENABLE_USER_MEMORY_CONTROLS:
            return True
        evaluator = MemoryPolicyEvaluator(self.db)
        decision = await evaluator.evaluate(
            user_id=user_id,
            kind=kind,
            pref_key=pref_key,
            source_type=source_type,
        )
        if not decision.allowed:
            logger.info(
                "Memory write blocked user_id={user_id} kind={kind} reason={reason}",
                user_id=user_id,
                kind=kind,
                reason=decision.reason,
            )
        return decision.allowed

    async def _advanced_features_enabled(self, user_id: UUID) -> bool:
        if not settings.ENABLE_LTM_ROLLOUT:
            return True
        rollout = LtmRolloutService(self.db)
        return await rollout.is_enabled(user_id)


def _normalize_evidence_refs(
    evidence_refs: Iterable[Any],
    require_non_empty: bool,
) -> List[Dict[str, Any]]:
    refs = list(evidence_refs or [])
    if require_non_empty and not refs:
        raise ValueError("evidence_refs must be non-empty")

    normalized: List[Dict[str, Any]] = []
    for item in refs:
        if isinstance(item, dict):
            ref_type = item.get("type")
            ref_id = item.get("id")
            schema_version = item.get("schema_version")
            user_deleted = item.get("user_deleted", False)
        else:
            ref_type = getattr(item, "type", None)
            ref_id = getattr(item, "id", None)
            schema_version = getattr(item, "schema_version", None)
            user_deleted = getattr(item, "user_deleted", False)

        if not ref_type or not ref_id:
            raise ValueError("evidence_refs items must include type and id")
        if ref_type not in ALLOWED_EVIDENCE_TYPES:
            raise ValueError(f"Unsupported evidence_ref type: {ref_type}")

        normalized.append(
            {
                "type": ref_type,
                "id": ref_id,
                "schema_version": schema_version,
                "user_deleted": bool(user_deleted),
            }
        )

    return normalized
