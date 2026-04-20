from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import timezone, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import (
    MEMORY_INFERRED_EXTRACT_TOTAL,
    MEMORY_INFERRED_REVOKE_TOTAL,
    MEMORY_INFERRED_WRITE_TOTAL,
)
from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class InferredEpisodicCandidate:
    candidate_text: str
    confidence: float
    evidence_token: str
    decay_policy: str
    source_lane: str
    semantic_key: str
    evidence_refs: list[dict[str, str]]


class MemoryInferredWriteLaneService:
    DRY_RUN_KEY_PREFIX = "inference_cache:memory_inferred_dry_run:"
    SOURCE_LANE = "inferred_extraction"

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def enqueue_from_chat_turn(
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_message: str,
        user_message_id: str | None,
        assistant_message_id: str | None,
    ) -> None:
        if not (
            settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED
            or settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED
        ):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(
            MemoryInferredWriteLaneService._run_background(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
            )
        )

    @staticmethod
    def enqueue_from_session(
        *,
        user_id: UUID,
        session_id: UUID,
        assistant_message_id: str,
        assistant_message: str,
    ) -> None:
        if not (
            settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED
            or settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED
        ):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(
            MemoryInferredWriteLaneService._run_background(
                user_id=user_id,
                session_id=session_id,
                user_message=None,
                assistant_message=assistant_message,
                user_message_id=None,
                assistant_message_id=assistant_message_id,
            )
        )

    @staticmethod
    async def _run_background(
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str | None,
        assistant_message: str,
        user_message_id: str | None,
        assistant_message_id: str | None,
    ) -> None:
        try:
            async with AsyncSessionLocal() as db:
                service = MemoryInferredWriteLaneService(db)
                await service.process_chat_turn(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id,
                )
        except Exception as exc:
            logger.warning("Stage16 inferred write lane background task failed: {}", exc)

    async def process_chat_turn(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str | None,
        assistant_message: str,
        user_message_id: str | None,
        assistant_message_id: str | None,
    ) -> InferredEpisodicCandidate | None:
        del assistant_message_id

        resolved_user_message = (user_message or "").strip()
        resolved_user_message_id = user_message_id
        if not resolved_user_message:
            resolved_user_message, resolved_user_message_id = await self._load_latest_user_turn(
                user_id=user_id,
                session_id=session_id,
            )

        if not resolved_user_message or not resolved_user_message_id:
            MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="missing_user_turn").inc()
            return None

        candidate = self.extract_candidate(
            user_message=resolved_user_message,
            assistant_message=assistant_message,
            evidence_token=resolved_user_message_id,
        )
        if candidate is None:
            MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="no_candidate").inc()
            return None

        MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="candidate").inc()
        await self._record_dry_run(user_id=user_id, session_id=session_id, candidate=candidate)

        if not settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="disabled").inc()
            return candidate

        if candidate.confidence < settings.MEMORY_INFERRED_MIN_CONFIDENCE:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="below_threshold").inc()
            return candidate

        if await self._is_user_disabled(user_id):
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="user_disabled").inc()
            return candidate

        if await self._is_duplicate(user_id=user_id, candidate=candidate):
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="duplicate").inc()
            return candidate

        if await self._has_blocking_conflict(user_id=user_id, candidate=candidate):
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="explicit_conflict").inc()
            return candidate

        memory_service = MemoryService(self.db)
        record = await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=candidate.candidate_text,
            source_type="chat",
            source_id=str(session_id),
            source_lane=candidate.source_lane,
            occurred_at=_utcnow(),
            importance_score=candidate.confidence,
            confidence=candidate.confidence,
            tags=[
                "stage16:auto_memory",
                f"decay:{candidate.decay_policy}",
            ],
            evidence_refs=candidate.evidence_refs,
            evidence_token=candidate.evidence_token,
            decay_policy=candidate.decay_policy,
            semantic_key=candidate.semantic_key,
            emit_system_update=False,
        )
        if record is None:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="blocked").inc()
            return candidate

        MEMORY_INFERRED_WRITE_TOTAL.labels(status="written").inc()
        return candidate

    def extract_candidate(
        self,
        *,
        user_message: str,
        assistant_message: str,
        evidence_token: str,
    ) -> InferredEpisodicCandidate | None:
        sentence = self._pick_candidate_sentence(user_message)
        if not sentence:
            return None
        temporal = self._has_temporal_anchor(sentence)
        actionish = self._has_action_signal(sentence)
        confidence = 0.88
        if temporal:
            confidence += 0.04
        if actionish:
            confidence += 0.04
        if assistant_message:
            confidence += 0.01
        confidence = min(confidence, 0.97)
        decay_policy = "7d" if temporal else "30d"
        semantic_key = hashlib.sha1(self._normalize_semantic(sentence).encode("utf-8")).hexdigest()
        return InferredEpisodicCandidate(
            candidate_text=sentence,
            confidence=round(confidence, 2),
            evidence_token=evidence_token,
            decay_policy=decay_policy,
            source_lane=self.SOURCE_LANE,
            semantic_key=semantic_key,
            evidence_refs=[
                {
                    "type": "chat_turn",
                    "id": evidence_token,
                    "schema_version": "stage16.rule_y.v1",
                }
            ],
        )

    async def _load_latest_user_turn(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> tuple[str, str | None]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        message = result.scalar_one_or_none()
        if message is None:
            return "", None
        return str(message.content or ""), str(message.id)

    async def _record_dry_run(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        candidate: InferredEpisodicCandidate,
    ) -> None:
        if not settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED:
            return
        redis_client = cache_service.redis
        if redis_client is None:
            return
        key = f"{self.DRY_RUN_KEY_PREFIX}{user_id}:{candidate.evidence_token}"
        payload = {
            "session_id": str(session_id),
            "candidate_text": candidate.candidate_text,
            "confidence": candidate.confidence,
            "evidence_token": candidate.evidence_token,
            "decay_policy": candidate.decay_policy,
            "source_lane": candidate.source_lane,
        }
        try:
            await redis_client.setex(key, 86400 * 7, json.dumps(payload, ensure_ascii=False))
            MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="dry_run", status="recorded").inc()
        except Exception as exc:
            logger.debug("Stage16 inferred dry-run record skipped: {}", exc)

    async def _is_user_disabled(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id,
                UserMemorySettings.deleted_at.is_(None),
            )
        )
        settings_record = result.scalar_one_or_none()
        if settings_record is None:
            return False
        if not settings_record.enabled or not settings_record.allow_episodic:
            return True
        return not getattr(settings_record, "allow_inferred_episodic", True)

    async def _is_duplicate(
        self,
        *,
        user_id: UUID,
        candidate: InferredEpisodicCandidate,
    ) -> bool:
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.source_lane == self.SOURCE_LANE,
                EpisodicMemory.revoked_at.is_(None),
                (
                    (EpisodicMemory.evidence_token == candidate.evidence_token)
                    | (EpisodicMemory.semantic_key == candidate.semantic_key)
                ),
            )
        )
        return result.scalar_one_or_none() is not None

    async def _has_blocking_conflict(
        self,
        *,
        user_id: UUID,
        candidate: InferredEpisodicCandidate,
    ) -> bool:
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.semantic_key == candidate.semantic_key,
                EpisodicMemory.source_lane != self.SOURCE_LANE,
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _pick_candidate_sentence(user_message: str) -> str | None:
        sentences = re.split(r"[。！？!?\n]+", user_message)
        for raw in sentences:
            sentence = raw.strip(" ，,；;")
            if not sentence:
                continue
            if len(sentence) < 8 or len(sentence) > 120:
                continue
            if not MemoryInferredWriteLaneService._looks_like_safe_context(sentence):
                continue
            return sentence
        return None

    @staticmethod
    def _looks_like_safe_context(sentence: str) -> bool:
        banned = (
            "性格",
            "人格",
            "天生",
            "永远",
            "一辈子",
            "很笨",
            "很懒",
            "我就是",
            "是不是有病",
        )
        if any(token in sentence for token in banned):
            return False
        if "我" not in sentence and "最近" not in sentence:
            return False
        return (
            MemoryInferredWriteLaneService._has_temporal_anchor(sentence)
            or MemoryInferredWriteLaneService._has_action_signal(sentence)
        )

    @staticmethod
    def _has_temporal_anchor(sentence: str) -> bool:
        temporal_tokens = ("最近", "今天", "这周", "本周", "明天", "今晚", "这两天", "刚刚", "现在")
        return any(token in sentence for token in temporal_tokens)

    @staticmethod
    def _has_action_signal(sentence: str) -> bool:
        action_tokens = ("准备", "打算", "要", "需要", "复习", "整理", "练", "学", "赶", "考试", "ddl", "任务")
        return any(token in sentence for token in action_tokens)

    @staticmethod
    def _normalize_semantic(value: str) -> str:
        normalized = re.sub(r"\s+", "", value.strip().lower())
        normalized = re.sub(r"[，,。！？!?；;:：]", "", normalized)
        return normalized


async def revoke_inferred_lane(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    reason: str | None = None,
) -> int:
    service = MemoryService(db)
    revoked = await service.revoke_inferred_memories(user_id=user_id, reason=reason)
    MEMORY_INFERRED_REVOKE_TOTAL.labels(scope="user" if user_id else "global").inc(revoked)
    return revoked
