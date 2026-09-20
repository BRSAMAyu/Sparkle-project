"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    MEMORY_CORRECTION_TOTAL,
    MEMORY_RETRACTION_TOTAL,
    MEMORY_STORAGE_GATE_TOTAL,
    MEMORY_WRITE_TOTAL,
)
from app.core.memory_constants import PREFERENCE_KEYS
from app.core.time_utils import ensure_naive_utc, utcnow
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryGoal, MemoryPreference
from app.models.user_memory_settings import UserMemorySettings
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.evidence_health_service import EvidenceHealthService
from app.services.evidence_scoring import compute_score
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_epistemic_contract import (
    MemoryRecordStatus,
    Provenance,
    classify_episodic_class,
    derive_status,
    inferred_may_supersede,
    preference_write_provenance,
)
from app.services.memory_evolution_service import MemoryEvolutionService
from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline, MemoryMutationAction
from app.services.memory_policy_evaluator import MemoryPolicyEvaluator
from app.services.policy_compiler_service import PolicyCompilerService
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
# memory-governance-mvp: 用户"这就是对的"确认路径的置信度增益（与 DECREMENT 对称的小步长）。
CONFIDENCE_CONFIRM_INCREMENT = 0.05
MEMORY_REFERENCE_OUTCOMES = {"accepted", "corrected", "ignored", "denied"}
SUMMARY_MAX_LEN = 48
SESSION_MOOD_TTL_SECONDS = 7 * 24 * 60 * 60
SESSION_MOOD_LAST_KEY_TEMPLATE = "memory:session_mood:{user_id}:last"
SESSION_MOOD_SESSION_KEY_TEMPLATE = "memory:session_mood:{user_id}:{session_id}"
RECENT_CALIBRATION_RECEIPTS_KEY_TEMPLATE = "aurora:recent_corrections:{user_id}"
LAST_CALIBRATION_RECEIPT_KEY_TEMPLATE = "aurora:last_calibration_receipt:{user_id}"
RECENT_CALIBRATION_RECEIPTS_TTL_SECONDS = 7 * 24 * 60 * 60
NON_CRITICAL_SERVICE_ERRORS = (
    AttributeError,
    ImportError,
    RuntimeError,
    TypeError,
    ValueError,
    SQLAlchemyError,
)


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

        # Memory V3 (M-01) 写守卫：Inference 不覆盖 fact。
        # memory_preferences 是 FACT/CONFIRMED_PREFERENCE 域；推断写
        # （source_type=ai_inferred 或 evidence 含 ai_inferred）不得接管
        # 显式事实链头（不新增版本、不设 replaced_by_id）。推断值仍写
        # user_preferences live 表（那边已有 explicit-override 保护）。
        if latest is not None:
            head_provenance = preference_write_provenance(
                source_type=None,
                evidence_refs=latest.evidence_refs,
            )
            incoming_provenance = preference_write_provenance(
                source_type=source_type,
                evidence_refs=normalized_refs,
            )
            if not inferred_may_supersede(head_provenance, incoming_provenance):
                MEMORY_WRITE_TOTAL.labels(type="preference", status="blocked_inferred_over_fact").inc()
                logger.info(
                    "Blocked inferred preference write over explicit fact user_id={user_id} pref_key={pref_key}",
                    user_id=user_id,
                    pref_key=pref_key,
                )
                return None

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
            # V3-FIX-35（精确化 M-07 的 updated_at bump）：
            # supersede 仍触碰旧行 updated_at（缓存失效/审计语义保留），但链头
            # 与被取代行共享同一转换时刻——旧行绝不比链头"更新"。修复前旧行
            # 被 bump 到晚于链头创建时刻的 utcnow()，任何按 updated_at 排序的
            # 消费面（如 _pick_preference_winner 的旧实现）都会让被取代值反杀
            # 链头（M-09 评测 20 case 红的根因之一）。
            supersede_at = utcnow()
            latest.replaced_by_id = record.id
            latest.updated_at = supersede_at
            if (record.updated_at or supersede_at) < supersede_at:
                record.updated_at = supersede_at
            # Memory V3 (M-07)：supersede（用户纠正产生新链头）→ epoch bump +
            # invalidation 事件 + derived 缓存失效，与版本推进同事务原子生效。
            # 行锁持有期间无中间提交，C2 的 FOR UPDATE 保护不被破坏。
            await MemoryInvalidationPipeline(self.db, self.redis).apply_in_txn(
                user_id=user_id,
                action=MemoryMutationAction.SUPERSEDE,
                kind="preference",
                memory_ids=[record.id],
                reason_code="preference_supersede",
            )

        await self.db.commit()
        # M-07 R1-C2-3：DEL 后置到 commit 之后（apply_in_txn 不再内部 DEL）。
        if latest is not None:
            await MemoryInvalidationPipeline(self.db, self.redis).invalidate_derived_caches(
                user_id=user_id, kinds={"preference"}
            )
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
        except NON_CRITICAL_SERVICE_ERRORS as exc:
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
        except (AttributeError, ImportError, RuntimeError) as exc:
            logger.debug("Unable to resolve Redis for session mood memory: {}", exc)
            return None

    def _calibration_receipt_redis(self):
        if self.redis is not None:
            return self.redis
        try:
            from app.core.cache import cache_service

            return cache_service.redis
        except (AttributeError, ImportError, RuntimeError) as exc:
            logger.debug("Unable to resolve Redis for calibration receipt memory: {}", exc)
            return None

    async def record_calibration_receipt(
        self,
        *,
        user_id: UUID | str,
        receipt: dict[str, Any],
    ) -> dict[str, Any] | None:
        redis = self._calibration_receipt_redis()
        if redis is None or not isinstance(receipt, dict) or not receipt:
            return None

        payload = {
            **receipt,
            "user_id": str(user_id),
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        recent_key = RECENT_CALIBRATION_RECEIPTS_KEY_TEMPLATE.format(user_id=user_id)
        last_key = LAST_CALIBRATION_RECEIPT_KEY_TEMPLATE.format(user_id=user_id)
        await redis.lpush(recent_key, encoded)
        await redis.ltrim(recent_key, 0, 9)
        await redis.expire(recent_key, RECENT_CALIBRATION_RECEIPTS_TTL_SECONDS)
        await redis.setex(last_key, RECENT_CALIBRATION_RECEIPTS_TTL_SECONDS, encoded)
        return payload

    async def list_recent_calibration_receipts(
        self,
        user_id: UUID | str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        redis = self._calibration_receipt_redis()
        if redis is None:
            return []

        safe_limit = max(1, min(int(limit or 3), 10))
        raw_items = await redis.lrange(
            RECENT_CALIBRATION_RECEIPTS_KEY_TEMPLATE.format(user_id=user_id),
            0,
            safe_limit - 1,
        )
        receipts: list[dict[str, Any]] = []
        for raw in raw_items or []:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                receipts.append(payload)
        return receipts

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
            # M-08 R2 P2-2：写入方真实来源落库（此前参数被静默丢弃——计划审批
            # 自动捕获 goal 被溯源面错标「你告诉我的」）。None = 用户公共创建路径。
            source_type=source_type,
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
            select(MemoryGoal)
            .where(
                MemoryGoal.user_id == user_id,
                MemoryGoal.id == goal_id,
                MemoryGoal.deleted_at.is_(None),
            )
            .with_for_update()
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

        # Memory V3 (M-08)：goal 字段编辑是 M-07 统一失效契约覆盖的
        # 「有效内容变更」——标题/状态变化会流入后续 prompt/投影，必须在
        # 同事务内 bump epoch + 写 memory.invalidated（旧派生缓存不复活）。
        # 记录保持 active（无版本链、非拒绝族），故 action=USER_UPDATE。
        record.updated_at = utcnow()
        record.correction_count = (record.correction_count or 0) + 1
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="goal",
                memory_id=record.id,
                action="user_update",
                reason=(str(updates.get("title") or "") or "user_update")[:500],
            )
        )
        goal_pipeline = MemoryInvalidationPipeline(self.db, self.redis)
        await goal_pipeline.apply_in_txn(
            user_id=user_id,
            action=MemoryMutationAction.USER_UPDATE,
            kind="goal",
            memory_ids=[record.id],
            reason_code="user_update",
        )
        await self.db.commit()
        await goal_pipeline.invalidate_derived_caches(user_id=user_id, kinds={"goal"})
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
        except NON_CRITICAL_SERVICE_ERRORS as exc:
            logger.warning(f"Failed to track goal evolution: {exc}")
        return record

    async def list_active_goals(self, user_id: UUID, now: datetime | None = None) -> list[MemoryGoal]:
        now = now or utcnow()
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
        now = utcnow()
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
        offset: int = 0,
    ) -> list[EpisodicMemory]:
        stmt = select(EpisodicMemory).where(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.archived_at.is_(None),
            EpisodicMemory.retracted_at.is_(None),
            EpisodicMemory.revoked_at.is_(None),
            # M-08 R2 P2-5：superseded 行与 revoked/archived 同为召回排除态。
            # 用户改写「说错的内容」后，旧内容不再喂 state_aggregator /
            # router_context_reader / aurora signal_aggregator 等非预筛决策面
            # （主 LLM 面另有 M-03 prefilter 兜底，此处补齐其余读者）。
            EpisodicMemory.superseded_by_id.is_(None),
        )
        if start:
            stmt = stmt.where(EpisodicMemory.occurred_at >= start)
        if end:
            stmt = stmt.where(EpisodicMemory.occurred_at <= end)
        if subject_types:
            stmt = stmt.where(EpisodicMemory.subject_type.in_(list(subject_types)))
        stmt = stmt.order_by(EpisodicMemory.occurred_at.desc()).limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_episodic(
        self,
        user_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        subject_types: Iterable[str] | None = None,
    ) -> int:
        """memory-governance-mvp: total count feeding the episodic list pagination."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                # M-08 R2 P2-5：与 list_recent_episodic 同款排除态——列表分页
                # total 与行集保持一致（superseded 行不再计入）。
                EpisodicMemory.superseded_by_id.is_(None),
            )
        )
        if start:
            stmt = stmt.where(EpisodicMemory.occurred_at >= start)
        if end:
            stmt = stmt.where(EpisodicMemory.occurred_at <= end)
        if subject_types:
            stmt = stmt.where(EpisodicMemory.subject_type.in_(list(subject_types)))
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

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
        epistemic_class: str | None = None,
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
            epistemic_class=epistemic_class,
        )
        # Memory V3 (M-02): Personalized Storage Gate —— 五分类
        # （store/current_state/event/ignore/confirm）。评估入口自身永不抛
        # 异常（内部全量兜底，异常降级 ignore+log），veto 时跳过落库直接
        # 返回 None，聊天主链零感知。
        try:
            from app.services.memory_storage_gate import (
                MemoryStorageGate,
                apply_decision_to_record,
                candidate_from_record,
            )

            gate_decision = await MemoryStorageGate().evaluate(candidate_from_record(record))
        except Exception as exc:  # noqa: BLE001 —— 韧性红线：gate 永不阻断写路径调用方
            logger.warning("Storage gate raised unexpectedly, degrading to ignore: {}", exc)
            from app.services.memory_storage_gate import StorageGateDecision, StorageGateVerdict

            gate_decision = StorageGateDecision(
                verdict=StorageGateVerdict.IGNORE.value,
                layer="error_degraded",
                reason="ERR.entrypoint",
            )
            apply_decision_to_record = None
        MEMORY_STORAGE_GATE_TOTAL.labels(verdict=gate_decision.verdict, layer=gate_decision.layer).inc()
        if gate_decision.verdict in {"ignore", "current_state"}:
            logger.info(
                "Storage gate vetoed episodic write user_id={} verdict={} reason={} detail={}",
                user_id,
                gate_decision.verdict,
                gate_decision.reason,
                gate_decision.detail,
            )
            MEMORY_WRITE_TOTAL.labels(type="episodic", status="gate_filtered").inc()
            return None
        apply_decision_to_record(record, gate_decision)
        # confirm 档：挂起等用户确认（既有四动作治理 API 出口），不推送
        # "记住了"系统通知。
        if gate_decision.verdict == "confirm":
            emit_system_update = False
        self.db.add(record)
        try:
            await self.db.commit()
            await self.db.refresh(record)
        except (SQLAlchemyError, RuntimeError) as exc:
            # M3: pgvector 运行时缺失可能以裸 RuntimeError 抛出（如 "vector.so unavailable"），
            # 是否可降级仍由 _is_vector_runtime_error 判定，非向量错误照常上抛。
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
                    epistemic_class=epistemic_class,
                )
                # 重建记录会丢失 gate 注解（tags/decay/confidence），重放一次
                # 决策应用（apply 幂等：min() 封顶 + tag 去重 + 空值守卫）。
                apply_decision_to_record(record, gate_decision)
                self.db.add(record)
                try:
                    await self.db.commit()
                    await self.db.refresh(record)
                except (SQLAlchemyError, RuntimeError) as retry_exc:
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
            except NON_CRITICAL_SERVICE_ERRORS as exc:
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
        epistemic_class: str | None = None,
    ) -> EpisodicMemory:
        # naive-UTC is the DB canonical form; aware inputs (e.g. LLM-extracted
        # ISO timestamps) make asyncpg raise DataError against TIMESTAMP columns
        occurred_at = ensure_naive_utc(occurred_at)
        due_at = ensure_naive_utc(due_at)
        resolved_at = ensure_naive_utc(resolved_at)
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
            # Memory V3 (M-01)：显式传入优先（OBSERVATION/EXPERIENCE 未来写方），
            # 否则按 lane+source_type 保守派生（R2-F1：FACT 仅限用户陈述——
            # user_confirmed lane 或 direct_capture+USER_STATEMENT_SOURCE_TYPES；
            # direct_capture 机器写行落 OBSERVATION；其余 lane 落 HYPOTHESIS）。
            epistemic_class=classify_episodic_class(
                source_lane, explicit_class=epistemic_class, source_type=source_type
            ),
        )

    async def list_pending_commitments(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> list[EpisodicMemory]:
        reference_time = now or utcnow()
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
        record.resolved_at = resolved_at or utcnow()
        record.updated_at = utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        try:
            await PolicyCompilerService(self.db).revoke_for_commitment(
                commitment_id=record.id,
                user_id=user_id,
            )
        except NON_CRITICAL_SERVICE_ERRORS as exc:
            logger.warning(f"Failed to revoke accountability policies for commitment {record.id}: {exc}")
        return record

    async def retract_memory(
        self,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        reason: str | None = None,
        reason_code: str | None = None,
    ) -> bool:
        """用户/系统撤回入口。

        M-08 R2 P3-8：``reason_code``（事件 actor 归因）可选传入——用户主权
        面传 ``"user_revoke"``，系统侧调用方（working_memory_consolidation 等）
        保持默认 ``revoke``，两者在 ``memory.invalidated`` 载荷上不再同形。
        """
        if not settings.ENABLE_MEMORY_RETRACTION:
            raise ValueError("Memory retraction is disabled by feature flag")

        model = {
            "preference": MemoryPreference,
            "goal": MemoryGoal,
            "episodic": EpisodicMemory,
        }.get(kind)
        if model is None:
            raise ValueError(f"Unsupported memory kind: {kind}")

        # M-07：行锁 + 终态复查 —— 双设备并发/重试/重复删除收敛为单次生效。
        result = await self.db.execute(
            select(model)
            .where(
                model.id == memory_id,
                model.user_id == user_id,
                model.deleted_at.is_(None),
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        if derive_status(record, now=utcnow()) != MemoryRecordStatus.ACTIVE.value:
            # 已处于终态（撤回/撤销/归档/过期…）：幂等成功，零重复副作用。
            return True

        self._apply_retraction(record, reason)
        record.correction_count = (record.correction_count or 0) + 1
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type=kind,
                memory_id=record.id,
                action="retract",
                reason=reason,
            )
        )
        if kind == "preference":
            # 链头删除 → live 视图同事务摘键，否则 ProfileContext 复活已删偏好。
            await self._remove_live_preference_key_in_txn(user_id=user_id, record=record)

        # Memory V3 (M-01→M-07)：状态变更、审计、epoch bump、invalidation 事件
        # 同事务原子落地（不再是 best-effort）。
        pipeline = MemoryInvalidationPipeline(self.db, self.redis)
        await pipeline.apply_in_txn(
            user_id=user_id,
            action=MemoryMutationAction.REVOKE,
            kind=kind,
            memory_ids=[record.id],
            reason_code=reason_code,
        )
        await self.db.commit()
        # M-07 R1-C2-3：DEL 后置到 commit 之后（apply_in_txn 不再内部 DEL）。
        await pipeline.invalidate_derived_caches(user_id=user_id, kinds={kind})
        await self.db.refresh(record)
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
        # M-07 R1-C2-2：与三个单记录入口同款守卫 —— SELECT ... FOR UPDATE +
        # 行锁内逐行 derive_status 终态复查。并发语义：PG 上两个重叠的批量
        # 撤销批次（admin kill-switch 重试/双触发）在本查询的行锁上串行化；
        # 先提交批次置 revoked_at/superseded_by_id 后，后到批次在 READ
        # COMMITTED 的锁内重读时被 SQL 预过滤 + 以下复查双重排除 → 每用户
        # 恰一次 epoch bump / 一条聚合事件（不再有双 bump 双事件路径）。
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.source_lane == "inferred_extraction",
                EpisodicMemory.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if user_id is not None:
            stmt = stmt.where(EpisodicMemory.user_id == user_id)
        if subject_types:
            stmt = stmt.where(EpisodicMemory.subject_type.in_(list(subject_types)))

        result = await self.db.execute(stmt)
        records = [
            record
            for record in result.scalars().all()
            # 行锁内终态复查（对齐 derive_status）：superseded 等终态行不再
            # 二次触碰；全部行已终态时零副作用返回。
            if derive_status(record, now=utcnow()) == MemoryRecordStatus.ACTIVE.value
        ]
        if not records:
            return 0

        pipeline = MemoryInvalidationPipeline(self.db, self.redis)
        ids_by_user: dict[UUID, list[UUID]] = {}
        for record in records:
            self._apply_retraction(record, reason or "admin_kill_switch")
            ids_by_user.setdefault(record.user_id, []).append(record.id)

        # Memory V3 (M-01→M-07)：批量撤销与单条同契约 —— 每受影响用户恰一次
        # epoch bump + 一条聚合 invalidation 事件（memory_ids 全量），同事务。
        for affected_user_id, memory_ids in ids_by_user.items():
            await pipeline.apply_in_txn(
                user_id=affected_user_id,
                action=MemoryMutationAction.BULK_REVOKE,
                kind="episodic",
                memory_ids=memory_ids,
                reason_code="revoke_inferred_bulk",
            )
        await self.db.commit()
        # M-07 R1-C2-3：DEL 后置到 commit 之后（apply_in_txn 不再内部 DEL）。
        for affected_user_id in ids_by_user:
            await pipeline.invalidate_derived_caches(user_id=affected_user_id, kinds={"episodic"})
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
            select(model)
            .where(
                model.id == memory_id,
                model.user_id == user_id,
                model.deleted_at.is_(None),
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        if action in {"reject", "no_longer_applicable"}:
            if not settings.ENABLE_MEMORY_RETRACTION:
                raise ValueError("Memory retraction is disabled by feature flag")
            # M-07 幂等守卫：重复纠错（双设备/重试）零重复副作用。
            if derive_status(record, now=utcnow()) != MemoryRecordStatus.ACTIVE.value:
                return record
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
            record.updated_at = utcnow()
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

        if action in {"reject", "no_longer_applicable"}:
            if kind == "preference":
                await self._remove_live_preference_key_in_txn(user_id=user_id, record=record)
            # Memory V3 (M-01→M-07)：撤回类纠错的 epoch bump + invalidation
            # 事件 + derived 失效与状态变更、审计同事务原子生效。
            await MemoryInvalidationPipeline(self.db, self.redis).apply_in_txn(
                user_id=user_id,
                action=MemoryMutationAction.CORRECTION,
                kind=kind,
                memory_ids=[record.id],
                reason_code=action,
            )

        await self.db.commit()
        # M-07 R1-C2-3：DEL 后置到 commit 之后（apply_in_txn 不再内部 DEL）。
        if action in {"reject", "no_longer_applicable"}:
            await MemoryInvalidationPipeline(self.db, self.redis).invalidate_derived_caches(
                user_id=user_id, kinds={kind}
            )
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
        except NON_CRITICAL_SERVICE_ERRORS as exc:
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

    async def revoke_episodic_memory(
        self,
        *,
        user_id: UUID,
        memory_id: UUID,
        reason: str | None = None,
        reason_code: str | None = None,
    ) -> EpisodicMemory | None:
        """memory-governance-mvp: 用户"删除"路径 —— 软删（revoked_at）。

        与 apply_correction 的 reject（按 lane 决定 revoked/retracted）不同，
        显式删除对任意 lane 一律落 revoked_at；召回查询
        （list_recent_episodic / context_builder 召回）均已排除 revoked 行。

        M-08 R2 P3-8：事件 reason_code 默认 ``user_revoke``（与 pref/goal 用户
        撤回面对齐——此前此处硬编码 ``user_delete`` 而另两 kind 走裸 ``revoke``，
        前瞻消费方无法统一判 actor）。
        """
        if not settings.ENABLE_MEMORY_CORRECTION:
            raise ValueError("Memory correction is disabled by feature flag")

        # M-07：行锁 + 终态复查 —— 用户"删除"的幂等/并发收敛点。
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.id == memory_id,
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if derive_status(record, now=utcnow()) != MemoryRecordStatus.ACTIVE.value:
            # 重复删除（双设备/重试）：幂等返回当前记录，零重复副作用。
            return record

        now = utcnow()
        updated_refs = []
        for ref in record.evidence_refs or []:
            ref_copy = dict(ref)
            ref_copy["user_deleted"] = True
            if reason and "retraction_reason" not in ref_copy:
                ref_copy["retraction_reason"] = reason
            updated_refs.append(ref_copy)
        record.evidence_refs = updated_refs
        record.revoked_at = now
        record.updated_at = now
        record.correction_count = (record.correction_count or 0) + 1

        snapshot = record.evidence_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {"history": snapshot}
        snapshot["revocation_reason"] = reason or "user_deleted"
        snapshot["evidence_refs"] = updated_refs
        record.evidence_snapshot = snapshot

        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="episodic",
                memory_id=record.id,
                action="delete",
                reason=reason,
            )
        )
        # Memory V3 (M-01→M-07)：用户删除 → epoch bump + invalidation 事件 +
        # derived 缓存失效，与 revoked 状态变更同事务原子生效（硬保证）。
        await MemoryInvalidationPipeline(self.db, self.redis).apply_in_txn(
            user_id=user_id,
            action=MemoryMutationAction.REVOKE,
            kind="episodic",
            memory_ids=[record.id],
            reason_code=reason_code or "user_revoke",
        )
        await self.db.commit()
        # M-07 R1-C2-3：DEL 后置到 commit 之后（apply_in_txn 不再内部 DEL）。
        await MemoryInvalidationPipeline(self.db, self.redis).invalidate_derived_caches(
            user_id=user_id, kinds={"episodic"}
        )
        await self.db.refresh(record)
        MEMORY_RETRACTION_TOTAL.labels(type="episodic").inc()
        MEMORY_CORRECTION_TOTAL.labels(type="episodic", action="delete").inc()
        logger.info(
            "Episodic memory revoked by user user_id={user_id} memory_id={memory_id}",
            user_id=user_id,
            memory_id=record.id,
        )
        return record

    async def confirm_episodic_memory(
        self,
        *,
        user_id: UUID,
        memory_id: UUID,
    ) -> EpisodicMemory | None:
        """memory-governance-mvp: "这就是对的"确认路径 —— confidence 提升。

        确认不是纠错：不增 correction_count，但写 MemoryCorrection(action="confirm")
        留痕（审计/数据飞轮正样本）。
        """
        if not settings.ENABLE_MEMORY_CORRECTION:
            raise ValueError("Memory correction is disabled by feature flag")

        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.id == memory_id,
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        record.confidence = min(1.0, float(record.confidence or 0.0) + CONFIDENCE_CONFIRM_INCREMENT)
        if hasattr(record, "evidence_score"):
            record.evidence_score = min(1.0, float(record.evidence_score or 0.0) + CONFIDENCE_CONFIRM_INCREMENT)
        record.updated_at = utcnow()
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="episodic",
                memory_id=record.id,
                action="confirm",
                reason=None,
            )
        )
        await self.db.commit()
        await self.db.refresh(record)
        MEMORY_CORRECTION_TOTAL.labels(type="episodic", action="confirm").inc()
        logger.info(
            "Episodic memory confirmed by user user_id={user_id} memory_id={memory_id}",
            user_id=user_id,
            memory_id=record.id,
        )
        return record

    async def record_memory_reference_outcome(
        self,
        *,
        kind: str,
        memory_id: UUID,
        user_id: UUID,
        outcome: str,
        response_id: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        """Record how a memory reference landed without changing the storage schema.

        Outcomes are stored as trace rows and folded back into confidence so future
        prompt selection can become quieter after denial/correction.
        """
        normalized_outcome = str(outcome or "").strip().lower()
        if normalized_outcome not in MEMORY_REFERENCE_OUTCOMES:
            raise ValueError(f"Unsupported memory reference outcome: {outcome}")

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

        now = utcnow()
        if hasattr(record, "last_consumed_at"):
            record.last_consumed_at = now

        if normalized_outcome == "accepted":
            if hasattr(record, "confidence") and record.confidence is not None:
                record.confidence = min(1.0, float(record.confidence or 0.0) + 0.03)
            if hasattr(record, "evidence_score"):
                record.evidence_score = min(1.0, float(record.evidence_score or 0.0) + 0.02)
        elif normalized_outcome in {"corrected", "denied"}:
            if hasattr(record, "confidence") and record.confidence is not None:
                record.confidence = max(0.0, float(record.confidence or 0.0) - CONFIDENCE_DECREMENT)
            if hasattr(record, "evidence_score"):
                record.evidence_score = max(0.0, float(record.evidence_score or 0.0) - CONFIDENCE_DECREMENT)
            record.correction_count = (record.correction_count or 0) + 1
            if normalized_outcome == "denied" and isinstance(record, EpisodicMemory):
                snapshot = record.evidence_snapshot or {}
                if not isinstance(snapshot, dict):
                    snapshot = {"history": snapshot}
                snapshot["reference_denied_at"] = now.isoformat()
                snapshot["reference_denial_reason"] = reason or "memory_reference_denied"
                record.evidence_snapshot = snapshot
        record.updated_at = now

        trace_reason = reason or normalized_outcome
        if response_id:
            trace_reason = f"{trace_reason}; response_id={response_id}"
        correction_entry = MemoryCorrection(
            user_id=user_id,
            memory_type=kind,
            memory_id=record.id,
            action=f"memory_reference_{normalized_outcome}",
            reason=trace_reason,
        )
        self.db.add(correction_entry)
        await self.db.commit()
        await self.db.refresh(record)

        return {
            "memory_reference_outcome": normalized_outcome,
            "memory_type": kind,
            "memory_id": str(record.id),
            "response_id": response_id,
            "confidence": getattr(record, "confidence", None),
            "evidence_score": getattr(record, "evidence_score", None),
            "correction_count": getattr(record, "correction_count", None),
        }

    def _apply_retraction(self, record: Any, reason: str | None) -> None:
        updated_refs = []
        for ref in record.evidence_refs or []:
            ref_copy = dict(ref)
            ref_copy["user_deleted"] = True
            if reason and "retraction_reason" not in ref_copy:
                ref_copy["retraction_reason"] = reason
            updated_refs.append(ref_copy)

        record.evidence_refs = updated_refs
        now = utcnow()
        if isinstance(record, EpisodicMemory) and getattr(record, "source_lane", "") == "inferred_extraction":
            record.revoked_at = now
        else:
            record.retracted_at = now
        record.updated_at = utcnow()

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

    # ------------------------------------------------------------------
    # Memory V3 (M-01): memory_epoch contract
    # ------------------------------------------------------------------

    async def get_memory_epoch(self, user_id: UUID | str) -> int:
        """Current memory epoch for the user (1 when never bumped).

        M-07 (context compiler cache) and C-07 (user-facing control) capture
        this value when compiling memory context and re-check to detect
        stale caches after destructive memory changes (MEMORY_V3.md §6).
        """
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        settings_row = result.scalar_one_or_none()
        if settings_row is None:
            return 1
        return int(settings_row.memory_epoch or 1)

    async def bump_memory_epoch(self, user_id: UUID | str, reason: str | None = None) -> int:
        """Bump the per-user memory epoch (monotonic) and audit it.

        R2-F3：并发安全。自增走单条原子 ``UPDATE ... SET memory_epoch =
        memory_epoch + 1 ... RETURNING``（行级锁 + 数据库端自增，两个并发
        bump 各得各的返回值，终值必为 +2）；懒建设置行撞 unique(user_id)
        时先 rollback（清 aborted 事务态，避免同 session 后续 bump 全部
        PendingRollbackError 被吞）再走原子自增重试。每次成功 bump 写一条
        MemoryCorrection(action="epoch_bump") 审计（锚定 settings 行 id）。
        """
        now = utcnow()
        trimmed_reason = (reason or "memory_epoch_bump")[:200]

        async def _atomic_increment() -> int | None:
            result = await self.db.execute(
                update(UserMemorySettings)
                .where(
                    UserMemorySettings.user_id == user_id,
                    UserMemorySettings.deleted_at.is_(None),
                )
                .values(
                    memory_epoch=UserMemorySettings.memory_epoch + 1,
                    memory_epoch_bumped_at=now,
                    memory_epoch_reason=trimmed_reason,
                    updated_at=now,
                )
                .returning(UserMemorySettings.id, UserMemorySettings.memory_epoch)
            )
            row = result.one_or_none()
            if row is None:
                return None
            self.db.add(
                MemoryCorrection(
                    user_id=user_id,
                    memory_type="memory_epoch",
                    memory_id=row.id,
                    action="epoch_bump",
                    reason=trimmed_reason,
                )
            )
            return int(row.memory_epoch)

        new_epoch = await _atomic_increment()
        if new_epoch is not None:
            await self.db.commit()
            return new_epoch

        # 懒建首行（首个 bump：1 -> 2）。并发首撞 unique(user_id) 时：
        # rollback 清 aborted 态 -> 对方已提交的行走原子自增重试。
        settings_row = UserMemorySettings(
            user_id=user_id,
            memory_epoch=2,
            memory_epoch_bumped_at=now,
            memory_epoch_reason=trimmed_reason,
        )
        self.db.add(settings_row)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            retried = await _atomic_increment()
            if retried is None:
                # 行存在但不可自增（如被软删）——显式失败而非静默丢 bump。
                raise SQLAlchemyError(f"memory settings row for user {user_id} exists but is not bumpable")
            await self.db.commit()
            return retried
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type="memory_epoch",
                memory_id=settings_row.id,
                action="epoch_bump",
                reason=trimmed_reason,
            )
        )
        await self.db.commit()
        return int(settings_row.memory_epoch)

    async def _remove_live_preference_key_in_txn(
        self,
        *,
        user_id: UUID,
        record: MemoryPreference,
    ) -> bool:
        """链头删除 → live ``user_preferences`` 视图同事务摘键（M-07）。

        ProfileContext/UserInsightCompiler 的偏好真源是 live 表
        (``UserPreferencesCenter``)；只撤 memory_preferences 链而不摘 live
        键会让已删除偏好在每次编译中复活（derived 复活通道）。仅当被撤
        行仍是该 pref_key 的当前活跃链头时摘键（删除历史版本不误伤新值），
        摘键递增 preference_version → prefs-center / profile_context 的
        version 门自动失效。

        M-07 R1-C1：链头判定必须对齐 ``derive_status`` 终态语义 ——
        ``replaced_by_id`` 置位的行是 SUPERSEDED 终态（版本链的历史环节），
        不是活跃链头。supersede 链（设值 → 改值 → 删链头）下漏掉该过滤
        会让 head-check 命中被顶替的旧版本，live 键不摘除、已删值复活。
        """
        head_result = await self.db.execute(
            select(MemoryPreference.id)
            .where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.pref_key == record.pref_key,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
                # 契约对齐：replaced_by_id 置位 = SUPERSEDED 终态（等价于
                # episodic 侧 superseded_by_id 的语义），不作为活跃链头。
                MemoryPreference.replaced_by_id.is_(None),
                MemoryPreference.id != record.id,
            )
            .order_by(MemoryPreference.version.desc())
            .limit(1)
        )
        newer_head_id = head_result.scalar_one_or_none()
        if newer_head_id is not None:
            return False  # 已有更新活跃版本承载 live 值

        from app.models.user_preferences import UserPreferencesCenter

        live_result = await self.db.execute(
            select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
        )
        live = live_result.scalar_one_or_none()
        if live is None:
            return False

        provenance = preference_write_provenance(source_type=None, evidence_refs=record.evidence_refs)
        bucket_name = "inferred" if provenance == Provenance.INFERRED.value else "explicit"
        bucket = dict(getattr(live, bucket_name) or {})
        if record.pref_key not in bucket:
            return False
        bucket.pop(record.pref_key, None)
        setattr(live, bucket_name, bucket)
        live.version = (live.version or 0) + 1
        live.updated_at = utcnow()
        return True


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
