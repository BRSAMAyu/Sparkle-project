"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, UTC
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import MEMORY_CORRECTION_TOTAL, MEMORY_RETRACTION_TOTAL, MEMORY_WRITE_TOTAL
from app.core.memory_constants import PREFERENCE_KEYS
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryGoal, MemoryPreference
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.evidence_health_service import EvidenceHealthService
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.evidence_scoring import compute_score
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_evolution_service import MemoryEvolutionService
from app.services.memory_policy_evaluator import MemoryPolicyEvaluator
from app.services.system_update_service import SystemUpdateService, build_system_update

ALLOWED_EVIDENCE_TYPES = {
    "ai_inferred",
    "chat_turn",
    "event",
    "user_state",
    "error",
    "practice_outcome",
    "concept",
    "strategy",
    "task",
    "summary",
}

INACTIVE_GOAL_STATUSES = {"completed", "archived", "cancelled"}
CONFIDENCE_DECREMENT = 0.1
SUMMARY_MAX_LEN = 48
SESSION_MOOD_TTL_SECONDS = 7 * 24 * 60 * 60
SESSION_MOOD_LAST_KEY_TEMPLATE = "memory:session_mood:{user_id}:last"
SESSION_MOOD_SESSION_KEY_TEMPLATE = "memory:session_mood:{user_id}:{session_id}"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _truncate_summary(value: str) -> str:
    if not value:
        return ""
    if len(value) <= SUMMARY_MAX_LEN:
        return value
    return f"{value[:SUMMARY_MAX_LEN - 1]}…"


class MemoryService:
    def __init__(self, db: AsyncSession | None, redis_client=None):
        self.db = db
        self.redis = redis_client

    @staticmethod
    def _is_vector_runtime_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = (
            "vector.so",
            "pgvector",
            'type "vector" does not exist',
            "could not load library",
            "operator does not exist: vector",
        )
        return any(marker in lowered for marker in markers)

    async def upsert_preference(
        self,
        user_id: UUID,
        pref_key: str,
        pref_value: dict[str, Any],
        evidence_refs: Iterable[Any],
        confidence: float | None = None,
        source_type: str | None = None,
    ) -> MemoryPreference | None:
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

        # ✅ Fix C2: Use SELECT FOR UPDATE to acquire row-level lock and prevent race conditions
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.pref_key == pref_key,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.version.desc())
            .limit(1)
            .with_for_update()  # 🔒 Acquires row-level lock until transaction ends
        )
        latest = result.scalar_one_or_none()
        version_result = await self.db.execute(
            select(func.max(MemoryPreference.version)).where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.pref_key == pref_key,
            )
        )
        max_version = version_result.scalar_one_or_none() or 0
        version = max_version + 1

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
            latest.updated_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_WRITE_TOTAL.labels(type="preference", status="ok").inc()

        # Track preference evolution without blocking the main write path.
        try:
            evolution = MemoryEvolutionService(self.db)
            old_snapshot = (
                {
                    **(latest.pref_value or {}),
                    "confidence": latest.confidence or 0.0,
                    "evidence_count": len(latest.evidence_refs or []),
                    "evidence_refs": latest.evidence_refs or [],
                }
                if latest
                else {}
            )
            new_snapshot = {
                **(record.pref_value or {}),
                "confidence": record.confidence or 0.0,
                "evidence_count": len(record.evidence_refs or []),
                "evidence_refs": record.evidence_refs or [],
            }
            change_reason = "user_edit" if source_type == "user_state" else "system_update"
            await evolution.track_memory_change(
                memory_id=str(record.id),
                memory_type="preference",
                old_value=old_snapshot,
                new_value=new_snapshot,
                change_reason=change_reason,
                workflow_id=source_type,
            )
        except Exception as exc:
            logger.warning(f"Failed to track preference evolution: {exc}")

        adaptation_record = self._build_preference_adaptation_record(
            pref_key=pref_key,
            latest=latest,
            record=record,
        )
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="memory_preference_updated",
                category="memory" if adaptation_record is None else "evolution",
                title=f"更新了偏好：{pref_key}",
                description=(
                    "已记录你的最新学习偏好" if adaptation_record is None else adaptation_record.user_facing_message
                ),
                priority="low",
                metadata={
                    "pref_key": pref_key,
                    "version": record.version,
                    **(
                        {
                            "evolution_kind": "preference_learning",
                            "preference_learning": adaptation_record.to_dict(),
                        }
                        if adaptation_record is not None
                        else {}
                    ),
                },
            ),
        )
        return record

    async def upsert_session_mood(
        self,
        user_id: UUID | str,
        session_id: UUID | str,
        mood_score: float,
        mood_label: str,
    ) -> dict[str, Any] | None:
        redis = self._session_mood_redis()
        if redis is None:
            logger.debug("Skipping session mood write because Redis is unavailable")
            return None

        label = str(mood_label or "").strip().lower()
        if not label:
            raise ValueError("mood_label is required")
        try:
            score = float(mood_score)
        except (TypeError, ValueError) as exc:
            raise ValueError("mood_score must be numeric") from exc
        score = max(0.0, min(1.0, score))

        recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        payload = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "mood_score": score,
            "mood_label": label,
            "recorded_at": recorded_at,
        }
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        last_key = SESSION_MOOD_LAST_KEY_TEMPLATE.format(user_id=user_id)
        session_key = SESSION_MOOD_SESSION_KEY_TEMPLATE.format(user_id=user_id, session_id=session_id)
        await redis.setex(last_key, SESSION_MOOD_TTL_SECONDS, encoded)
        await redis.setex(session_key, SESSION_MOOD_TTL_SECONDS, encoded)
        return payload

    async def get_last_session_mood(self, user_id: UUID | str) -> dict[str, Any] | None:
        redis = self._session_mood_redis()
        if redis is None:
            return None
        raw = await redis.get(SESSION_MOOD_LAST_KEY_TEMPLATE.format(user_id=user_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, json.JSONDecodeError):
            logger.debug("Ignoring malformed session mood payload for user {}", user_id)
            return None
        if not isinstance(payload, dict):
            return None
        return dict(payload)

    def _session_mood_redis(self):
        if self.redis is not None:
            return self.redis
        try:
            from app.core.cache import cache_service

            return cache_service.redis
        except Exception as exc:
            logger.debug("Unable to resolve Redis for session mood memory: {}", exc)
            return None

    async def create_goal(
        self,
        user_id: UUID,
        title: str,
        status: str = "active",
        target_date: date | None = None,
        expires_at: datetime | None = None,
        linked_task_id: UUID | None = None,
        linked_plan_id: UUID | None = None,
        evidence_refs: Iterable[Any] | None = None,
        metadata: dict[str, Any] | None = None,
        source_type: str | None = None,
    ) -> MemoryGoal | None:
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

    def _build_preference_adaptation_record(
        self,
        *,
        pref_key: str,
        latest: MemoryPreference | None,
        record: MemoryPreference,
    ) -> AdaptationRecord | None:
        if latest is None:
            return None

        old_value = latest.pref_value or {}
        new_value = record.pref_value or {}
        if old_value == new_value:
            return None

        old_display = self._describe_preference_value(pref_key, old_value)
        new_display = self._describe_preference_value(pref_key, new_value)
        label = pref_key.replace("_", " ")
        return AdaptationRecord(
            what_changed=f"把 {label} 从“{old_display}”更新为“{new_display}”",
            why=f"你最近的反馈和显式设置已经显示出新的 {label} 偏好。",
            expected_effect=f"后续回答和计划会优先按“{new_display}”来组织。",
            user_facing_message=f"我记住了你更喜欢{new_display}的回答方式。",
            source="memory_preference",
        )

    def _describe_preference_value(self, pref_key: str, pref_value: dict[str, Any]) -> str:
        value = pref_value.get("value")
        if pref_key == "depth_preference" and isinstance(value, (int, float)):
            if value >= 0.7:
                return "深入详尽"
            if value <= 0.3:
                return "简洁概览"
            return "适中平衡"
        if pref_key == "curiosity_preference" and isinstance(value, (int, float)):
            if value >= 0.7:
                return "探索扩展"
            if value <= 0.3:
                return "专注聚焦"
            return "适中平衡"
        if pref_key == "session_length_preference" and isinstance(value, (int, float)):
            return f"{int(value)} 分钟节奏"
        if pref_key == "difficulty_preference" and isinstance(value, (int, float)):
            if value >= 0.7:
                return "更有挑战"
            if value <= 0.3:
                return "更轻量"
            return "适中难度"
        return str(value) if value is not None else "新的偏好"

    async def update_goal(
        self,
        user_id: UUID,
        goal_id: UUID,
        **updates: Any,
    ) -> MemoryGoal | None:
        result = await self.db.execute(
            select(MemoryGoal).where(
                MemoryGoal.user_id == user_id,
                MemoryGoal.id == goal_id,
                MemoryGoal.deleted_at.is_(None),
            ).with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        old_snapshot = {
            "title": record.title,
            "status": record.status,
            "target_date": record.target_date.isoformat() if record.target_date else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "metadata": record.metadata_payload or {},
            "confidence": 0.0,
            "evidence_count": len(record.evidence_refs or []),
            "evidence_refs": record.evidence_refs or [],
        }

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
        MEMORY_WRITE_TOTAL.labels(type="goal", status="ok").inc()

        try:
            evolution = MemoryEvolutionService(self.db)
            new_snapshot = {
                "title": record.title,
                "status": record.status,
                "target_date": record.target_date.isoformat() if record.target_date else None,
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                "metadata": record.metadata_payload or {},
                "confidence": 0.0,
                "evidence_count": len(record.evidence_refs or []),
                "evidence_refs": record.evidence_refs or [],
            }
            await evolution.track_memory_change(
                memory_id=str(record.id),
                memory_type="goal",
                old_value=old_snapshot,
                new_value=new_snapshot,
                change_reason="user_edit",
                workflow_id="update_goal",
            )
        except Exception as exc:
            logger.warning(f"Failed to track goal evolution: {exc}")
        return record

    async def list_active_goals(self, user_id: UUID, now: datetime | None = None) -> list[MemoryGoal]:
        now = now or _utcnow()
        result = await self.db.execute(
            select(MemoryGoal).where(
                MemoryGoal.user_id == user_id,
                MemoryGoal.deleted_at.is_(None),
                MemoryGoal.archived_at.is_(None),
                MemoryGoal.retracted_at.is_(None),
                ~MemoryGoal.status.in_(INACTIVE_GOAL_STATUSES),
                (MemoryGoal.expires_at.is_(None) | (MemoryGoal.expires_at > now)),
            )
        )
        return list(result.scalars().all())

    async def list_preferences(self, user_id: UUID) -> dict[str, Any]:
        records = await self.list_preference_records(user_id)
        latest_by_key: dict[str, Any] = {}
        for record in records:
            latest_by_key[record.pref_key] = record.pref_value
        return latest_by_key

    async def get_preference_record(
        self,
        user_id: UUID,
        preference_id: UUID,
    ) -> MemoryPreference | None:
        result = await self.db.execute(
            select(MemoryPreference).where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.id == preference_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_preference(
        self,
        user_id: UUID,
        pref_key: str,
    ) -> MemoryPreference | None:
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.pref_key == pref_key,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_preference(
        self,
        user_id: UUID,
        preference_id: UUID,
        pref_key: str | None = None,
        pref_value: dict[str, Any] | None = None,
        value: dict[str, Any] | None = None,
        confidence: float | None = None,
        evidence_refs: Iterable[Any] | None = None,
    ) -> MemoryPreference | None:
        record = await self.get_preference_record(user_id, preference_id)
        if record is None:
            return None

        resolved_key = pref_key or record.pref_key
        resolved_value = pref_value if pref_value is not None else value
        if resolved_value is None:
            resolved_value = record.pref_value

        refs = (
            evidence_refs
            or record.evidence_refs
            or [{"type": "user_state", "id": "batch_edit", "schema_version": "batch_edit.v1"}]
        )

        return await self.upsert_preference(
            user_id=user_id,
            pref_key=resolved_key,
            pref_value=resolved_value,
            evidence_refs=refs,
            confidence=confidence if confidence is not None else record.confidence,
            source_type="user_state",
        )

    async def delete_preference(
        self,
        user_id: UUID,
        preference_id: UUID,
        reason: str | None = None,
    ) -> bool:
        return await self.retract_memory(
            kind="preference",
            memory_id=preference_id,
            user_id=user_id,
            reason=reason or "batch_delete",
        )

    async def list_preference_records(self, user_id: UUID) -> list[MemoryPreference]:
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
        )
        latest_by_key: dict[str, MemoryPreference] = {}
        for record in result.scalars().all():
            if record.pref_key not in latest_by_key:
                latest_by_key[record.pref_key] = record
        return list(latest_by_key.values())

    async def list_preference_history(self, user_id: UUID) -> list[MemoryPreference]:
        result = await self.db.execute(
            select(MemoryPreference)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
            .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
        )
        return list(result.scalars().all())

    async def list_goals(
        self,
        user_id: UUID,
        status_filter: str | None = None,
        include_expired: bool = False,
        limit: int = 20,
    ) -> list[MemoryGoal]:
        now = _utcnow()
        stmt = select(MemoryGoal).where(
            MemoryGoal.user_id == user_id,
            MemoryGoal.deleted_at.is_(None),
            MemoryGoal.archived_at.is_(None),
            MemoryGoal.retracted_at.is_(None),
        )
        if status_filter:
            stmt = stmt.where(MemoryGoal.status == status_filter)
        if not include_expired:
            stmt = stmt.where(MemoryGoal.expires_at.is_(None) | (MemoryGoal.expires_at > now))
        stmt = stmt.order_by(MemoryGoal.updated_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_episodic(
        self,
        user_id: UUID,
        limit: int = 10,
        start: datetime | None = None,
        end: datetime | None = None,
        subject_types: Iterable[str] | None = None,
    ) -> list[EpisodicMemory]:
        stmt = select(EpisodicMemory).where(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.archived_at.is_(None),
            EpisodicMemory.retracted_at.is_(None),
            EpisodicMemory.revoked_at.is_(None),
        )
        if start:
            stmt = stmt.where(EpisodicMemory.occurred_at >= start)
        if end:
            stmt = stmt.where(EpisodicMemory.occurred_at <= end)
        if subject_types:
            stmt = stmt.where(EpisodicMemory.subject_type.in_(list(subject_types)))
        stmt = stmt.order_by(EpisodicMemory.occurred_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_episodic(
        self,
        user_id: UUID,
        limit: int = 10,
        start: datetime | None = None,
        end: datetime | None = None,
        subject_types: Iterable[str] | None = None,
    ) -> list[EpisodicMemory]:
        """Compatibility alias for callers that use the read-oriented name."""
        return await self.list_recent_episodic(
            user_id=user_id,
            limit=limit,
            start=start,
            end=end,
            subject_types=subject_types,
        )

    async def create_episodic_memory(
        self,
        user_id: UUID,
        summary: str,
        source_type: str,
        source_id: str | None,
        occurred_at: datetime,
        importance_score: float | None,
        tags: list[str] | None,
        evidence_refs: Iterable[Any],
        embedding: list[float] | None = None,
        confidence: float | None = None,
        evidence_token: str | None = None,
        decay_policy: str | None = None,
        source_lane: str = "direct_capture",
        semantic_key: str | None = None,
        subject_type: str = "self",
        due_at: datetime | None = None,
        resolved_at: datetime | None = None,
        mentioned_entity_hash: str | None = None,
        mentioned_entity_owner_user_id: UUID | None = None,
        emit_system_update: bool = True,
    ) -> EpisodicMemory | None:
        if not await self._allow_write(
            user_id=user_id,
            kind="episodic",
            source_type=source_type,
            source_lane=source_lane,
        ):
            MEMORY_WRITE_TOTAL.labels(type="episodic", status="blocked").inc()
            return None
        normalized_refs = _normalize_evidence_refs(evidence_refs, require_non_empty=True)
        # TRACKED(TD-008): enforce per-session rate limits (1-2 memories) once session tracking is available.
        evidence_score = compute_score(normalized_refs, evidence_missing=False)
        evidence_snapshot = None
        if settings.ENABLE_EVIDENCE_SNAPSHOT_ON_WRITE and await self._advanced_features_enabled(user_id):
            resolver = EvidenceHealthService(self.db)
            resolved = await resolver.resolve_evidence_refs(normalized_refs, user_id)
            evidence_snapshot = EvidenceHealthService.build_snapshot(resolved)
        record = self._build_episodic_memory_record(
            user_id=user_id,
            summary=summary,
            source_type=source_type,
            source_id=source_id,
            source_lane=source_lane,
            occurred_at=occurred_at,
            importance_score=importance_score,
            confidence=confidence,
            tags=tags,
            normalized_refs=normalized_refs,
            evidence_snapshot=evidence_snapshot,
            embedding=embedding,
            evidence_score=evidence_score,
            evidence_token=evidence_token,
            decay_policy=decay_policy,
            semantic_key=semantic_key,
            subject_type=subject_type,
            due_at=due_at,
            resolved_at=resolved_at,
            mentioned_entity_hash=mentioned_entity_hash,
            mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
        )
        self.db.add(record)
        try:
            await self.db.commit()
            await self.db.refresh(record)
        except Exception as exc:
            await self.db.rollback()
            if not self._is_vector_runtime_error(exc):
                raise
            if embedding is not None:
                logger.warning(
                    "Retrying episodic memory write without embedding because vector runtime is unavailable: {}",
                    exc,
                )
                record = self._build_episodic_memory_record(
                    user_id=user_id,
                    summary=summary,
                    source_type=source_type,
                    source_id=source_id,
                    source_lane=source_lane,
                    occurred_at=occurred_at,
                    importance_score=importance_score,
                    confidence=confidence,
                    tags=tags,
                    normalized_refs=normalized_refs,
                    evidence_snapshot=evidence_snapshot,
                    embedding=None,
                    evidence_score=evidence_score,
                    evidence_token=evidence_token,
                    decay_policy=decay_policy,
                    semantic_key=semantic_key,
                    subject_type=subject_type,
                    due_at=due_at,
                    resolved_at=resolved_at,
                    mentioned_entity_hash=mentioned_entity_hash,
                    mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
                )
                self.db.add(record)
                try:
                    await self.db.commit()
                    await self.db.refresh(record)
                except Exception as retry_exc:
                    await self.db.rollback()
                    if not self._is_vector_runtime_error(retry_exc):
                        raise
                    logger.warning(f"Skipping episodic memory write because vector runtime is unavailable: {retry_exc}")
                    MEMORY_WRITE_TOTAL.labels(type="episodic", status="degraded").inc()
                    return None
            else:
                logger.warning(f"Skipping episodic memory write because vector runtime is unavailable: {exc}")
                MEMORY_WRITE_TOTAL.labels(type="episodic", status="degraded").inc()
                return None
        if emit_system_update:
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
                        "source_lane": source_lane,
                    },
                ),
            )
        if record.subject_type == "commitment" and record.due_at is not None:
            try:
                await PolicyCompilerService(self.db).compile_for_commitment(record, persist=True)
            except Exception as exc:
                logger.warning(f"Failed to compile accountability policies for commitment {record.id}: {exc}")
        MEMORY_WRITE_TOTAL.labels(type="episodic", status="ok").inc()
        return record

    @staticmethod
    def _build_episodic_memory_record(
        *,
        user_id: UUID,
        summary: str,
        source_type: str,
        source_id: str | None,
        source_lane: str,
        occurred_at: datetime,
        importance_score: float | None,
        confidence: float | None,
        tags: list[str] | None,
        normalized_refs: list[dict[str, Any]],
        evidence_snapshot: dict[str, Any] | None,
        embedding: list[float] | None,
        evidence_score: float,
        evidence_token: str | None,
        decay_policy: str | None,
        semantic_key: str | None,
        subject_type: str,
        due_at: datetime | None,
        resolved_at: datetime | None,
        mentioned_entity_hash: str | None,
        mentioned_entity_owner_user_id: UUID | None,
    ) -> EpisodicMemory:
        return EpisodicMemory(
            user_id=user_id,
            summary=summary,
            source_type=source_type,
            source_id=source_id,
            source_lane=source_lane,
            subject_type=subject_type,
            occurred_at=occurred_at,
            due_at=due_at,
            resolved_at=resolved_at,
            importance_score=importance_score,
            confidence=confidence,
            tags=tags,
            evidence_refs=normalized_refs,
            evidence_snapshot=evidence_snapshot,
            embedding=embedding,
            evidence_score=evidence_score,
            correction_count=0,
            evidence_token=evidence_token,
            decay_policy=decay_policy,
            semantic_key=semantic_key,
            mentioned_entity_hash=mentioned_entity_hash,
            mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
        )

    async def list_pending_commitments(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> list[EpisodicMemory]:
        reference_time = now or _utcnow()
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.subject_type == "commitment",
                EpisodicMemory.due_at.is_not(None),
                EpisodicMemory.due_at <= reference_time,
                EpisodicMemory.resolved_at.is_(None),
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
            .order_by(EpisodicMemory.due_at.asc())
        )
        return list(result.scalars().all())

    async def resolve_commitment(
        self,
        *,
        user_id: UUID,
        memory_id: UUID,
        resolved_at: datetime | None = None,
    ) -> EpisodicMemory | None:
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.id == memory_id,
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.subject_type == "commitment",
                EpisodicMemory.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.resolved_at = resolved_at or _utcnow()
        record.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        try:
            await PolicyCompilerService(self.db).revoke_for_commitment(
                commitment_id=record.id,
                user_id=user_id,
            )
        except Exception as exc:
            logger.warning(f"Failed to revoke accountability policies for commitment {record.id}: {exc}")
        return record

    async def retract_memory(
        self,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        reason: str | None = None,
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

    async def revoke_inferred_memories(
        self,
        *,
        user_id: UUID | None = None,
        reason: str | None = None,
        subject_types: Iterable[str] | None = None,
    ) -> int:
        stmt = select(EpisodicMemory).where(
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.source_lane == "inferred_extraction",
            EpisodicMemory.revoked_at.is_(None),
        )
        if user_id is not None:
            stmt = stmt.where(EpisodicMemory.user_id == user_id)
        if subject_types:
            stmt = stmt.where(EpisodicMemory.subject_type.in_(list(subject_types)))

        result = await self.db.execute(stmt)
        records = list(result.scalars().all())
        if not records:
            return 0

        for record in records:
            self._apply_retraction(record, reason or "admin_kill_switch")

        await self.db.commit()
        return len(records)

    async def apply_correction(
        self,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        action: str,
        reason: str | None = None,
    ) -> Any | None:
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
            record.updated_at = _utcnow()
        else:
            raise ValueError(f"Unsupported correction action: {action}")

        record.correction_count = (record.correction_count or 0) + 1
        correction_entry = MemoryCorrection(
            user_id=user_id,
            memory_type=kind,
            memory_id=record.id,
            action=action,
            reason=reason,
        )
        self.db.add(correction_entry)

        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_CORRECTION_TOTAL.labels(type=kind, action=action).inc()
        logger.info(
            "Memory correction applied user_id={user_id} memory_id={memory_id} action={action}",
            user_id=user_id,
            memory_id=record.id,
            action=action,
        )
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService
            from app.core.cache import cache_service

            await SparkleSelfModelService(cache_service.redis).record_user_correction(
                user_id=str(user_id),
                signal_id=f"memory_correction:{correction_entry.id or record.id}:{action}",
                reason=reason or action,
                source="memory_correction",
            )
        except Exception as exc:
            logger.warning("Failed to update Aurora self model for memory correction {}: {}", record.id, exc)
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

    def _apply_retraction(self, record: Any, reason: str | None) -> None:
        updated_refs = []
        for ref in record.evidence_refs or []:
            ref_copy = dict(ref)
            ref_copy["user_deleted"] = True
            if reason and "retraction_reason" not in ref_copy:
                ref_copy["retraction_reason"] = reason
            updated_refs.append(ref_copy)

        record.evidence_refs = updated_refs
        now = _utcnow()
        if isinstance(record, EpisodicMemory) and getattr(record, "source_lane", "") == "inferred_extraction":
            record.revoked_at = now
        else:
            record.retracted_at = now
        record.updated_at = _utcnow()

        if isinstance(record, EpisodicMemory):
            snapshot = record.evidence_snapshot or {}
            if not isinstance(snapshot, dict):
                snapshot = {"history": snapshot}
            if getattr(record, "source_lane", "") == "inferred_extraction":
                snapshot["revocation_reason"] = reason
            else:
                snapshot["retraction_reason"] = reason
            snapshot["evidence_refs"] = updated_refs
            record.evidence_snapshot = snapshot

    async def _allow_write(
        self,
        user_id: UUID,
        kind: str,
        pref_key: str | None = None,
        source_type: str | None = None,
        source_lane: str | None = None,
    ) -> bool:
        if not settings.ENABLE_USER_MEMORY_CONTROLS:
            return True
        evaluator = MemoryPolicyEvaluator(self.db)
        decision = await evaluator.evaluate(
            user_id=user_id,
            kind=kind,
            pref_key=pref_key,
            source_type=source_type,
            source_lane=source_lane,
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
) -> list[dict[str, Any]]:
    refs = list(evidence_refs or [])
    if require_non_empty and not refs:
        raise ValueError("evidence_refs must be non-empty")

    normalized: list[dict[str, Any]] = []
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
