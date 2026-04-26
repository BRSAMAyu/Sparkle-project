from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.business_metrics import (
    MEMORY_INFERRED_EXTRACT_TOTAL,
    MEMORY_INFERRED_REVOKE_TOTAL,
    MEMORY_INFERRED_WRITE_TOTAL,
)
from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal, _get_engine_kwargs, _sanitize_asyncpg_url
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user_memory_settings import UserMemorySettings
from app.services.commitment_parser import parse_commitment_due_at
from app.services.conflict_resolver_service import ConflictCandidate, ConflictResolverService
from app.services.memory_service import MemoryService
from app.services.scene_consolidation_service import SceneConsolidationService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class InferredEpisodicCandidate:
    candidate_text: str
    subject_type: str
    confidence: float
    evidence_token: str
    decay_policy: str
    source_lane: str
    semantic_key: str
    evidence_refs: list[dict[str, str]]
    occurred_at: datetime
    due_at: datetime | None
    mentioned_entity_hash: str | None
    mentioned_entity_owner_user_id: UUID | None


def _build_inferred_write_session_factory():
    db_url, sslmode, sslrootcert = _sanitize_asyncpg_url(
        AsyncSessionLocal.kw["bind"].url.render_as_string(hide_password=False)
    )
    if db_url.startswith("sqlite"):
        return AsyncSessionLocal

    engine = create_async_engine(
        db_url,
        **_get_engine_kwargs(db_url, sslmode, sslrootcert) | {"pool_size": 5, "max_overflow": 0},
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


INFERRED_WRITE_SESSION_FACTORY = _build_inferred_write_session_factory()


class MemoryInferredWriteLaneService:
    DRY_RUN_KEY_PREFIX = "inference_cache:memory_inferred_dry_run:"
    SOURCE_LANE = "inferred_extraction"
    _rate_limit_state: dict[str, list[datetime]] = {}
    _degraded_queue: list[dict[str, object]] = []

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
        if not (settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED or settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED):
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
        if not (settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED or settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED):
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
            async with INFERRED_WRITE_SESSION_FACTORY() as db:
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
            user_id=user_id,
            user_message=resolved_user_message,
            assistant_message=assistant_message,
            evidence_token=resolved_user_message_id,
        )
        if candidate is None:
            MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="no_candidate").inc()
        else:
            MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="candidate").inc()
            await self._record_dry_run(user_id=user_id, session_id=session_id, candidate=candidate)

        from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService

        if await AuroraStage19KillSwitchService().is_enabled("working_memory_enabled"):
            from app.services.working_memory_pipeline_service import WorkingMemoryPipelineService

            pipeline = WorkingMemoryPipelineService(self.db)
            await pipeline.process_chat_turn(
                user_id=user_id,
                session_id=session_id,
                user_message=resolved_user_message,
                assistant_message=assistant_message,
                evidence_token=resolved_user_message_id,
                rule_candidate=candidate,
            )
            return candidate

        if candidate is None:
            return None

        record = await self.write_candidate_to_l1(
            user_id=user_id,
            session_id=session_id,
            candidate=candidate,
        )
        if record is None:
            return candidate

        MEMORY_INFERRED_WRITE_TOTAL.labels(status="written").inc()
        return candidate

    def extract_candidate(
        self,
        *,
        user_id: UUID,
        user_message: str,
        assistant_message: str,
        evidence_token: str,
    ) -> InferredEpisodicCandidate | None:
        sentence = self._pick_candidate_sentence(user_message)
        if not sentence:
            return None
        subject_type, entity_name = self._classify_subject_type(sentence)
        if subject_type is None:
            return None

        due_at = parse_commitment_due_at(sentence) if subject_type == "commitment" else None
        if subject_type == "commitment" and due_at is None:
            return None

        occurred_at, temporal_kind = self._resolve_occurred_at(sentence)
        temporal = temporal_kind is not None
        actionish = self._has_action_signal(sentence)
        confidence = 0.72
        if temporal:
            confidence += 0.08
        if actionish:
            confidence += 0.06
        if assistant_message:
            confidence += 0.01
        if temporal_kind in {"tomorrow", "this_week", "weekend", "tonight"}:
            confidence += 0.03
        if actionish and any(
            token in sentence
            for token in ("今天", "明天", "今晚", "周末", "下周", "这周", "本周", "下午", "晚上", "早上")
        ):
            confidence += 0.03
        confidence = min(confidence, 0.9)
        if subject_type == "commitment" and due_at is not None:
            confidence = min(0.95, confidence + 0.03)
        decay_policy = "due_at+7d" if subject_type == "commitment" else ("7d" if temporal else "30d")
        mentioned_entity_hash = None
        mentioned_entity_owner_user_id = None
        semantic_key_source = self._normalize_semantic(sentence)
        candidate_text = sentence
        if subject_type in {"person_mention", "relationship"}:
            if not entity_name:
                return None
            mentioned_entity_hash = self._build_mentioned_entity_hash(user_id=user_id, person_name=entity_name)
            mentioned_entity_owner_user_id = user_id
            semantic_key_source = f"{subject_type}:{mentioned_entity_hash}"
            candidate_text = (
                "你提到过一位学习相关人物" if subject_type == "person_mention" else "你提到过一段与他人的关系动态"
            )
        semantic_key = hashlib.sha1(semantic_key_source.encode("utf-8")).hexdigest()
        return InferredEpisodicCandidate(
            candidate_text=candidate_text,
            subject_type=subject_type,
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
            occurred_at=occurred_at,
            due_at=due_at,
            mentioned_entity_hash=mentioned_entity_hash,
            mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
        )

    @classmethod
    def _within_rate_limit(cls, user_id: UUID) -> bool:
        now = _utcnow()
        key = str(user_id)
        history = [stamp for stamp in cls._rate_limit_state.get(key, []) if (now - stamp).total_seconds() < 60]
        if len(history) >= 10:
            cls._rate_limit_state[key] = history
            return False
        history.append(now)
        cls._rate_limit_state[key] = history
        return True

    @classmethod
    def _enqueue_degraded_candidate(
        cls,
        *,
        user_id: UUID,
        session_id: UUID,
        candidate: InferredEpisodicCandidate,
    ) -> None:
        cls._degraded_queue.append(
            {
                "user_id": str(user_id),
                "session_id": str(session_id),
                "candidate": candidate.candidate_text,
                "subject_type": candidate.subject_type,
                "queued_at": _utcnow().isoformat(),
            }
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
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                (
                    (EpisodicMemory.evidence_token == candidate.evidence_token)
                    | (EpisodicMemory.semantic_key == candidate.semantic_key)
                ),
            )
        )
        return result.scalar_one_or_none() is not None

    async def write_candidate_to_l1(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        candidate: InferredEpisodicCandidate,
        force_write: bool = False,
        bypass_min_confidence: bool = False,
        source_type: str = "chat",
        extra_tags: list[str] | None = None,
    ) -> EpisodicMemory | None:
        from app.services.rule_y_adapter import RuleYAdapter

        validated_candidate = RuleYAdapter.validate(candidate)
        if validated_candidate is None:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="rule_y_rejected").inc()
            return None
        candidate = validated_candidate

        if not self._within_rate_limit(user_id):
            self._enqueue_degraded_candidate(user_id=user_id, session_id=session_id, candidate=candidate)
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="rate_limited").inc()
            return None

        if not force_write and not settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="disabled").inc()
            return None

        if not bypass_min_confidence and candidate.confidence < settings.MEMORY_INFERRED_MIN_CONFIDENCE:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="below_threshold").inc()
            return None

        if await self._is_user_disabled(user_id):
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="user_disabled").inc()
            return None

        if await self._is_duplicate(user_id=user_id, candidate=candidate):
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="duplicate").inc()
            return None

        resolution = await self._resolve_conflict(user_id=user_id, candidate=candidate)
        if resolution is not None and resolution.action in {"reject", "surface_to_user"}:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="explicit_conflict").inc()
            return None

        memory_service = MemoryService(self.db)
        record = await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=candidate.candidate_text,
            source_type=source_type,
            source_id=str(session_id),
            source_lane=self.SOURCE_LANE,
            occurred_at=candidate.occurred_at,
            importance_score=candidate.confidence,
            confidence=candidate.confidence,
            tags=[
                "stage16:auto_memory",
                f"decay:{candidate.decay_policy}",
                *(extra_tags or []),
            ],
            evidence_refs=candidate.evidence_refs,
            evidence_token=candidate.evidence_token,
            decay_policy=candidate.decay_policy,
            semantic_key=candidate.semantic_key,
            subject_type=candidate.subject_type,
            due_at=candidate.due_at,
            mentioned_entity_hash=candidate.mentioned_entity_hash,
            mentioned_entity_owner_user_id=candidate.mentioned_entity_owner_user_id,
            emit_system_update=False,
        )
        if record is None:
            MEMORY_INFERRED_WRITE_TOTAL.labels(status="blocked").inc()
            return None
        if resolution is not None and resolution.action == "accept" and resolution.loser_record_ids:
            await ConflictResolverService(self.db).apply_live_decision(
                candidate=self._to_conflict_candidate(user_id=user_id, session_id=session_id, candidate=candidate),
                decision=resolution,
                new_record=record,
            )
        try:
            await SceneConsolidationService(self.db).consolidate_memory(record)
        except Exception as exc:
            logger.warning(f"Stage26 scene consolidation skipped for memory {record.id}: {exc}")
        return record

    async def _resolve_conflict(
        self,
        *,
        user_id: UUID,
        candidate: InferredEpisodicCandidate,
    ):
        resolver = ConflictResolverService(self.db)
        existing_records = await resolver.load_conflicting_records(
            user_id=user_id,
            semantic_key=candidate.semantic_key,
        )
        if not existing_records:
            return None

        conflict_candidate = self._to_conflict_candidate(
            user_id=user_id,
            session_id=None,
            candidate=candidate,
        )
        decision = resolver.resolve(candidate=conflict_candidate, existing_records=existing_records)

        if settings.SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE:
            legacy_blocked = await self._legacy_has_blocking_conflict(user_id=user_id, candidate=candidate)
            await resolver.record_shadow_comparison(
                user_id=user_id,
                legacy_blocked=legacy_blocked,
                decision=decision,
            )
            if legacy_blocked:
                return decision.__class__(
                    action="reject",
                    reason="legacy_blocked_shadow_mode",
                    winner_record_id=decision.winner_record_id,
                    winner_lane=decision.winner_lane,
                    loser_record_ids=decision.loser_record_ids,
                    loser_lanes=decision.loser_lanes,
                    evidence_tokens=decision.evidence_tokens,
                    conflict_key=decision.conflict_key,
                    metadata={
                        **decision.metadata,
                        "shadow_resolver_action": decision.action,
                    },
                )
            return None

        if decision.action in {"reject", "surface_to_user"}:
            await resolver.apply_live_decision(candidate=conflict_candidate, decision=decision)
        return decision

    async def _legacy_has_blocking_conflict(
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
    def _to_conflict_candidate(
        *,
        user_id: UUID,
        session_id: UUID | None,
        candidate: InferredEpisodicCandidate,
    ) -> ConflictCandidate:
        return ConflictCandidate(
            user_id=user_id,
            summary=candidate.candidate_text,
            source_lane=candidate.source_lane,
            confidence=candidate.confidence,
            occurred_at=candidate.occurred_at,
            evidence_token=candidate.evidence_token,
            semantic_key=candidate.semantic_key,
            subject_type=candidate.subject_type,
            due_at=candidate.due_at,
            evidence_refs=tuple(candidate.evidence_refs),
            mentioned_entity_hash=candidate.mentioned_entity_hash,
            mentioned_entity_owner_user_id=candidate.mentioned_entity_owner_user_id,
            source_id=str(session_id) if session_id is not None else None,
        )

    @staticmethod
    def _pick_candidate_sentence(user_message: str) -> str | None:
        sentences = re.split(r"[。！？!?\n]+", user_message)
        best_sentence: str | None = None
        best_score = -1.0
        for raw in sentences:
            sentence = raw.strip(" ，,；;")
            if not sentence:
                continue
            if (len(sentence) < 8 and not MemoryInferredWriteLaneService._looks_like_learning_context(sentence)) or len(
                sentence
            ) > 180:
                continue
            if not MemoryInferredWriteLaneService._looks_like_safe_context(sentence):
                continue
            score = 0.0
            if "我" in sentence:
                score += 2.0
            if MemoryInferredWriteLaneService._has_temporal_anchor(sentence):
                score += 2.0
            if MemoryInferredWriteLaneService._has_action_signal(sentence):
                score += 1.5
            if MemoryInferredWriteLaneService._has_learning_difficulty_signal(sentence):
                score += 1.8
            if MemoryInferredWriteLaneService._looks_like_learning_context(sentence):
                score += 1.0
            if any(token in sentence for token in ("明天", "今晚", "周末", "下周", "这周", "今天")):
                score += 1.0
            score += min(len(sentence), 80) / 80.0
            if score > best_score:
                best_score = score
                best_sentence = sentence
        return best_sentence

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
        if (
            "我" not in sentence
            and "最近" not in sentence
            and not MemoryInferredWriteLaneService._looks_like_social_context(sentence)
            and not MemoryInferredWriteLaneService._looks_like_learning_context(sentence)
        ):
            return False
        return (
            MemoryInferredWriteLaneService._has_temporal_anchor(sentence)
            or MemoryInferredWriteLaneService._has_action_signal(sentence)
            or MemoryInferredWriteLaneService._looks_like_social_context(sentence)
            or MemoryInferredWriteLaneService._has_learning_difficulty_signal(sentence)
        )

    @staticmethod
    def _has_temporal_anchor(sentence: str) -> bool:
        temporal_tokens = (
            "最近",
            "今天",
            "这周",
            "本周",
            "明天",
            "今晚",
            "这两天",
            "刚刚",
            "现在",
            "周末",
            "下周",
            "月底",
            "早上",
            "下午",
            "晚上",
        )
        return any(token in sentence for token in temporal_tokens) or bool(
            re.search(r"\d{1,2}月\d{1,2}[日号]?", sentence)
        )

    @staticmethod
    def _has_action_signal(sentence: str) -> bool:
        action_tokens = (
            "准备",
            "打算",
            "要",
            "需要",
            "复习",
            "整理",
            "练",
            "学",
            "赶",
            "考",
            "考试",
            "ddl",
            "任务",
            "完成",
            "补完",
            "刷题",
            "背",
            "预习",
        )
        return any(token in sentence for token in action_tokens)

    @staticmethod
    def _looks_like_social_context(sentence: str) -> bool:
        social_tokens = ("他", "她", "朋友", "同学", "老师", "妈妈", "爸爸", "老张", "小李", "关系", "相处")
        return any(token in sentence for token in social_tokens)

    @staticmethod
    def _looks_like_learning_context(sentence: str) -> bool:
        learning_tokens = (
            "高数",
            "数学",
            "线代",
            "概率论",
            "英语",
            "TCP",
            "计网",
            "计算机网络",
            "操作系统",
            "OS",
            "数据结构",
            "算法",
            "图论",
            "物理",
            "化学",
            "考研",
            "教资",
            "论文",
            "实验",
            "错题",
            "真题",
            "笔记",
            "复习",
            "背单词",
        )
        if not any(token in sentence for token in learning_tokens):
            return False
        return (
            MemoryInferredWriteLaneService._has_temporal_anchor(sentence)
            or MemoryInferredWriteLaneService._has_action_signal(sentence)
            or MemoryInferredWriteLaneService._has_learning_difficulty_signal(sentence)
        )

    @staticmethod
    def _has_learning_difficulty_signal(sentence: str) -> bool:
        learning_tokens = (
            "高数",
            "数学",
            "线代",
            "概率论",
            "英语",
            "TCP",
            "计网",
            "计算机网络",
            "操作系统",
            "数据结构",
            "算法",
            "图论",
            "物理",
            "化学",
        )
        difficulty_tokens = (
            "很难",
            "太难",
            "有点难",
            "不会",
            "不懂",
            "卡住",
            "薄弱",
            "搞不懂",
            "看不懂",
            "学不会",
            "吃力",
        )
        return any(token in sentence for token in learning_tokens) and any(
            token in sentence for token in difficulty_tokens
        )

    @classmethod
    def _classify_subject_type(cls, sentence: str) -> tuple[str | None, str | None]:
        if cls._looks_like_commitment(sentence):
            return "commitment", None
        relationship_name = cls._extract_relationship_name(sentence)
        if relationship_name is not None:
            return "relationship", relationship_name
        mention_name = cls._extract_mentioned_person_name(sentence)
        if mention_name is not None:
            return "person_mention", mention_name
        if cls._looks_like_safe_context(sentence):
            return "self", None
        return None, None

    @staticmethod
    def _looks_like_commitment(sentence: str) -> bool:
        future_markers = ("我会", "我要", "我打算", "我计划", "我准备", "我想", "本周要", "这周要", "明天要", "今天要")
        return any(token in sentence for token in future_markers)

    @staticmethod
    def _extract_relationship_name(sentence: str) -> str | None:
        if "关系" not in sentence and "相处" not in sentence:
            return None
        match = re.search(r"(?:我和|跟|和|与)([^，。！？\s]{1,6})(?:的)?(?:关系|相处)", sentence)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_mentioned_person_name(sentence: str) -> str | None:
        match = re.search(r"(?:和|跟)([^，。！？\s]{1,6})(?:一起|约好|说|在|要)", sentence)
        if match:
            return match.group(1)
        kinship_tokens = (
            "我妈",
            "我爸",
            "妈妈",
            "爸爸",
            "老师",
            "同学",
            "朋友",
            "室友",
            "同事",
            "老张",
            "小李",
            "她",
            "他",
        )
        for token in kinship_tokens:
            if token in sentence:
                return token
        return None

    @staticmethod
    def _build_mentioned_entity_hash(*, user_id: UUID, person_name: str) -> str:
        # Stage 17 deliberately salts with `user_id:null` because the mentioned
        # party is not resolved to a registered Sparkle user. This preserves the
        # Rule Z no-cross-user-join boundary; a future explicit user-to-user
        # mention system would need a separate governed upgrade path.
        key = f"{user_id}:null".encode("utf-8")
        msg = MemoryInferredWriteLaneService._normalize_semantic(person_name).encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    @staticmethod
    def _normalize_semantic(value: str) -> str:
        normalized = re.sub(r"\s+", "", value.strip().lower())
        normalized = re.sub(r"[，,。！？!?；;:：]", "", normalized)
        return normalized

    @staticmethod
    def _resolve_occurred_at(sentence: str) -> tuple[datetime, str | None]:
        now = _utcnow()
        lowered = sentence.lower()
        if "明天晚上" in lowered or "明晚" in lowered:
            base = now + timedelta(days=1)
            return base.replace(hour=20, minute=0, second=0, microsecond=0), "tomorrow_evening"
        if "明天下午" in lowered:
            base = now + timedelta(days=1)
            return base.replace(hour=15, minute=0, second=0, microsecond=0), "tomorrow_afternoon"
        if "明天早上" in lowered:
            base = now + timedelta(days=1)
            return base.replace(hour=9, minute=0, second=0, microsecond=0), "tomorrow_morning"
        if "明天" in lowered:
            base = now + timedelta(days=1)
            return base.replace(hour=9, minute=0, second=0, microsecond=0), "tomorrow"
        if "今晚" in lowered:
            return now.replace(hour=20, minute=0, second=0, microsecond=0), "tonight"
        if "今天晚上" in lowered or "晚上" in lowered:
            return now.replace(hour=20, minute=0, second=0, microsecond=0), "today_evening"
        if "今天下午" in lowered or "下午" in lowered:
            return now.replace(hour=15, minute=0, second=0, microsecond=0), "today_afternoon"
        if "今天早上" in lowered or "早上" in lowered:
            return now.replace(hour=9, minute=0, second=0, microsecond=0), "today_morning"
        if "今天" in lowered or "现在" in lowered:
            return now, "today"
        if "周末" in lowered:
            days_until_saturday = (5 - now.weekday()) % 7
            target = now + timedelta(days=days_until_saturday)
            return target.replace(hour=10, minute=0, second=0, microsecond=0), "weekend"
        if "这周" in lowered or "本周" in lowered:
            target = now + timedelta(days=max(0, 6 - now.weekday()))
            return target.replace(hour=18, minute=0, second=0, microsecond=0), "this_week"
        if "下周" in lowered:
            days_until_next_monday = (7 - now.weekday()) % 7 or 7
            target = now + timedelta(days=days_until_next_monday)
            return target.replace(hour=9, minute=0, second=0, microsecond=0), "next_week"
        return now, None


async def revoke_inferred_lane(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    reason: str | None = None,
    subject_types: list[str] | None = None,
) -> int:
    service = MemoryService(db)
    revoked = await service.revoke_inferred_memories(user_id=user_id, reason=reason, subject_types=subject_types)
    MEMORY_INFERRED_REVOKE_TOTAL.labels(scope="user" if user_id else "global").inc(revoked)
    return revoked
