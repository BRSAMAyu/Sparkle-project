from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
from app.core.time_utils import ensure_naive_utc
from app.db.session import AsyncSessionLocal, _get_engine_kwargs, _sanitize_asyncpg_url
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user_memory_settings import UserMemorySettings
from app.services.commitment_parser import parse_commitment_due_at, resolve_weekday_anchor
from app.services.conflict_resolver_service import ConflictCandidate, ConflictResolverService
from app.services.memory_service import MemoryService
from app.services.scene_consolidation_service import SceneConsolidationService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# MR-1 修复：显式记忆口令集合（与 WorkingMemoryConsolidationService 的确认短语
# 保持同语义）。带这些口令的句子即使被规则启发式判为无候选，也必须捕获，
# 否则"帮我记住 X"这一产品承诺在主聊天路径整链失活（实测 A1 0/3）。
EXPLICIT_MEMORY_COMMAND_PHRASES = (
    "帮我记住这个",
    "帮我记住",
    "记住这个",
    "记下来",
    "把这个记住",
    "就记这个",
    "记一下这个",
)


def _strip_memory_command_phrases(text: str) -> str:
    """剥离显式记忆口令；按长度降序替换，避免"帮我记住这个"被拆成"帮我"+"这个"。"""
    cleaned = text
    for phrase in sorted(EXPLICIT_MEMORY_COMMAND_PHRASES, key=len, reverse=True):
        cleaned = cleaned.replace(phrase, "，")
    return cleaned


# 显式口令也不得越过的硬禁止话题（人格判定/负面自我标签等）。
EXPLICIT_COMMAND_HARD_BANNED_TOKENS = (
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

# 学习科目词表（自 _looks_like_learning_context 原词表提取共用；明示事实的
# weakness 判定要求科目词共现以保精度）。
_LEARNING_SUBJECT_TOKENS = (
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

# MEM-AMNESIA（2026-09-22）：用户明示事实捕获面。Day0 onboarding 一句自述
# （考试/截止、弱点、目标、时间约束）是跨会话记忆的核心原料，但通用启发式
# 只把候选句置信打到 0.79（< MEMORY_INFERRED_MIN_CONFIDENCE=0.9），且
# working-memory live 路径要 mention_count>=3 才固化 → 明示事实永远进不了
# 跨会话 episodic（NORTHSTAR-LOOP1 BP-2/GP-07 实锤：「memory 必须比裸 GPT
# 好」在主路径失灵）。明示事实与显式记忆口令同级处理：用户自我陈述的关键
# 备考事实是最高优先捕获信号（置信 0.92 直写档）。确定性正则、零 LLM、
# 不新增投递点；幂等由既有 semantic_key/evidence_token 去重兜底。
# 元组顺序即同句多信号时的优先级：exam（可解析截止日，最强）> weakness >
# goal > constraint。
DECLARED_FACT_EXAM_RE = re.compile(r"期末|期中|考试|小测|测验|模考|deadline|截止")
DECLARED_FACT_WEAKNESS_RE = re.compile(
    r"薄弱|最弱|不扎实|不熟|没掌握|搞不懂|分不清|容易混淆|最容易混淆|最难|困惑|难点|卡在"
)
DECLARED_FACT_GOAL_RE = re.compile(
    r"目标|想考到|要考到|希望考到|冲到|冲\s*\d+\s*分|提到\s*\d+\s*分|达到\s*\d+\s*分|及格|不挂"
)
DECLARED_FACT_TIME_BUDGET_RE = re.compile(r"(每天|每日)[^。！？\n]{0,20}\d+\s*分钟")


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
    # MEM-AMNESIA（2026-09-22）：明示事实标记。True 的候选在 working-memory
    # live 路径跳过「mention_count>=3 才固化」的门槛，单次声明即时写入跨会话
    # episodic（NORTHSTAR-LOOP1 BP-2：Day0 明示 Day1 失忆）。默认 False，
    # 既有构造方零感知。
    declared_fact: bool = False


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
    # M1: 降级候选队列当前无消费者，必须设上限防止进程内存无界增长；
    # 超限丢弃 oldest 并计数（观测点），后续若接定时 flush 消费者可直接复用。
    DEGRADED_QUEUE_MAXLEN = 256
    _degraded_queue: deque[dict[str, object]] = deque(maxlen=DEGRADED_QUEUE_MAXLEN)
    _degraded_queue_dropped_total = 0

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
        # MEM-AMNESIA：明示事实候选与规则候选并行抽取（互补形态——规则候选
        # 只挑最佳一句，明示事实逐句扫描）；写入面共享同一去重/门禁/冲突链。
        declared_candidates = self.extract_declared_fact_candidates(
            user_id=user_id,
            user_message=resolved_user_message,
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
                declared_candidates=declared_candidates,
            )
            return candidate

        # fallback（working-memory 关闭）：明示事实先直写 L1（0.92 越门禁），
        # 规则候选照旧。两者共享 semantic_key 去重，同句不会双写。
        for declared_candidate in declared_candidates:
            declared_record = await self.write_candidate_to_l1(
                user_id=user_id,
                session_id=session_id,
                candidate=declared_candidate,
            )
            if declared_record is not None:
                MEMORY_INFERRED_WRITE_TOTAL.labels(status="written").inc()

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
            # MR-1 修复：规则启发式丢掉的句子若带显式记忆口令，走口令 fallback，
            # 保证"帮我记住 X"这一产品承诺在主聊天路径整链失活（实测 A1 0/3）。
            return self._build_explicit_command_candidate(
                user_message=user_message,
                evidence_token=evidence_token,
            )
        # 显式记忆口令混在候选句里会污染 candidate_text/semantic_key
        # （如"我下周三有期中考试，帮我记住这个"），先剥离再分类。
        cleaned = _strip_memory_command_phrases(sentence)
        cleaned = cleaned.strip(" ，,。：:；;！!？?·「」《》\"'")
        if not cleaned:
            cleaned = sentence
        sentence = cleaned
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
            # 可解析 due_at 的事件承诺是最强入库信号；无"我"主语的短句
            # （"明天上午有英语课/下周四有一场高数小测"）在加性启发式下会停在
            # 0.9 直写门槛之下（固化链 min-confidence 同样被卡），与
            # "中文考试/承诺类短句可靠入库"目标冲突，故托底到门槛、封顶 0.95。
            confidence = min(0.95, max(confidence + 0.03, 0.9))
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
            occurred_at=ensure_naive_utc(occurred_at) or occurred_at,
            due_at=ensure_naive_utc(due_at),
            mentioned_entity_hash=mentioned_entity_hash,
            mentioned_entity_owner_user_id=mentioned_entity_owner_user_id,
        )

    @classmethod
    def _match_declared_fact_kind(cls, sentence: str) -> str | None:
        """返回该句命中的明示事实种类；无命中返回 None。

        exam 类额外要求可解析时间锚（否则信息量不足，留给通用启发式）；
        weakness 类要求科目词共现（防「我比较薄弱」这类无主泛述误捕）。
        """
        if DECLARED_FACT_EXAM_RE.search(sentence) and parse_commitment_due_at(sentence) is not None:
            return "exam"
        if DECLARED_FACT_WEAKNESS_RE.search(sentence) and any(token in sentence for token in _LEARNING_SUBJECT_TOKENS):
            return "weakness"
        if DECLARED_FACT_GOAL_RE.search(sentence):
            return "goal"
        if DECLARED_FACT_TIME_BUDGET_RE.search(sentence):
            return "constraint"
        return None

    def extract_declared_fact_candidates(
        self,
        *,
        user_id: UUID,
        user_message: str,
        evidence_token: str,
    ) -> list[InferredEpisodicCandidate]:
        """逐句扫描用户明示事实（考试/截止、弱点、目标、时间约束）。

        与 ``extract_candidate``（只挑最佳一句）互补：明示事实按句独立成
        候选，覆盖 Day0 onboarding「一句一事实」的多句声明形态。置信固定
        0.92 直写档（与显式记忆口令同级）；同一句多信号只取最高优先一类。
        """
        del user_id  # 保留签名对称；抽取为纯函数，不触库。
        candidates: list[InferredEpisodicCandidate] = []
        seen_keys: set[str] = set()
        for raw_sentence in re.split(r"[。！？!?\n]+", str(user_message or "")):
            sentence = raw_sentence.strip(" ，,；;")
            if len(sentence) < 6 or len(sentence) > 180:
                continue
            # 与显式口令通道同一禁入面：人格判定/负面自我标签不得长期化。
            if any(token in sentence for token in EXPLICIT_COMMAND_HARD_BANNED_TOKENS):
                continue
            kind = self._match_declared_fact_kind(sentence)
            if kind is None:
                continue
            # goal 类排除请求句（「请帮我建立目标」是请求不是已声明的事实）。
            if kind == "goal" and re.search(r"请|帮我|能不能|可不可以|麻烦", sentence):
                continue
            due_at: datetime | None = None
            subject_type = "self"
            decay_policy = "30d"
            if kind == "exam":
                due_at = parse_commitment_due_at(sentence)
                subject_type = "commitment"
                decay_policy = "due_at+7d"
            occurred_at, _temporal_kind = self._resolve_occurred_at(sentence)
            semantic_key = hashlib.sha1(self._normalize_semantic(sentence).encode("utf-8")).hexdigest()
            if semantic_key in seen_keys:
                continue
            seen_keys.add(semantic_key)
            candidates.append(
                InferredEpisodicCandidate(
                    candidate_text=sentence,
                    subject_type=subject_type,
                    confidence=0.92,
                    evidence_token=evidence_token,
                    decay_policy=decay_policy,
                    source_lane=self.SOURCE_LANE,
                    semantic_key=semantic_key,
                    evidence_refs=[
                        {
                            "type": "chat_turn",
                            "id": evidence_token,
                            "schema_version": "stage16.declared_fact.v1",
                        }
                    ],
                    occurred_at=ensure_naive_utc(occurred_at) or occurred_at,
                    due_at=ensure_naive_utc(due_at),
                    mentioned_entity_hash=None,
                    mentioned_entity_owner_user_id=None,
                    declared_fact=True,
                )
            )
        return candidates

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
        if len(cls._degraded_queue) >= cls.DEGRADED_QUEUE_MAXLEN:
            cls._degraded_queue_dropped_total += 1
            if cls._degraded_queue_dropped_total % 50 == 1:
                logger.warning(
                    "Inferred write lane degraded queue full (maxlen={}): dropping oldest, dropped_total={}",
                    cls.DEGRADED_QUEUE_MAXLEN,
                    cls._degraded_queue_dropped_total,
                )
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
        # MEM-AMNESIA：明示事实一轮可产多条候选（考试/弱点/约束各占一句），
        # evidence_token 相同属预期形态——该通道只按 semantic_key 去重（同句
        # 同键，重复对话/重放皆命中）；其余候选维持「一轮一条 OR 同键」的
        # 既有单写语义不变。
        if candidate.declared_fact:
            duplicate_filter = EpisodicMemory.semantic_key == candidate.semantic_key
        else:
            duplicate_filter = (EpisodicMemory.evidence_token == candidate.evidence_token) | (
                EpisodicMemory.semantic_key == candidate.semantic_key
            )
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.source_lane == self.SOURCE_LANE,
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                duplicate_filter,
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
        # M-04: every accept application leaves a resolution record (audit) —
        # including scope-difference "preserve both" (no losers): CONFLICT_
        # RESOLVER.md §5 "所有 resolution 产生记录". Destructive side effects
        # (supersede/epoch/event) remain loser-gated inside apply_live_decision.
        if resolution is not None and resolution.action == "accept":
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
            # M-04: decay policy rides the candidate so time-scope arbitration
            # (today-only vs standing) sees the same signals as the record side.
            decay_policy=candidate.decay_policy,
        )

    @classmethod
    def _has_explicit_memory_command(cls, text: str) -> bool:
        normalized = str(text or "").strip()
        return any(phrase in normalized for phrase in EXPLICIT_MEMORY_COMMAND_PHRASES)

    @classmethod
    def _extract_explicit_command_fact(cls, text: str) -> str | None:
        """从带显式记忆口令的句子里剥离口令，返回要记住的事实文本。"""
        normalized = str(text or "").strip()
        if not normalized or not cls._has_explicit_memory_command(normalized):
            return None
        if any(token in normalized for token in EXPLICIT_COMMAND_HARD_BANNED_TOKENS):
            return None
        fact = _strip_memory_command_phrases(normalized)
        parts = [part.strip(" ，,。：:；;！!？?·「」《》\"'") for part in re.split(r"[，,；;：:]+", fact)]
        parts = [part for part in parts if len(part) >= 4]
        if not parts:
            return None
        return max(parts, key=len)

    def _build_explicit_command_candidate(
        self,
        *,
        user_message: str,
        evidence_token: str,
    ) -> InferredEpisodicCandidate | None:
        fact = self._extract_explicit_command_fact(user_message)
        if not fact or len(fact) < 6 or len(fact) > 180:
            return None
        occurred_at, _temporal_kind = self._resolve_occurred_at(fact)
        semantic_key = hashlib.sha1(self._normalize_semantic(fact).encode("utf-8")).hexdigest()
        # 用户显式口令是最高优先级捕获信号：给最高置信档（必须越过
        # MEMORY_INFERRED_MIN_CONFIDENCE=0.9 的 L1 直写门槛）。
        subject_type = "self"
        decay_policy = "30d"
        due_at: datetime | None = None
        # R28 修复：口令事实本身带可解析时间锚的（"帮我记住，下周三有期中考试"）
        # 升级为 commitment，接通固化链 commitment+due_at 自动固化通道。
        if self._looks_like_commitment(fact):
            due_at = parse_commitment_due_at(fact)
            if due_at is not None:
                subject_type = "commitment"
                decay_policy = "due_at+7d"
        return InferredEpisodicCandidate(
            candidate_text=fact,
            subject_type=subject_type,
            confidence=0.92,
            evidence_token=evidence_token,
            decay_policy=decay_policy,
            source_lane=self.SOURCE_LANE,
            semantic_key=semantic_key,
            evidence_refs=[
                {
                    "type": "chat_turn",
                    "id": evidence_token,
                    "schema_version": "stage16.explicit_command.v1",
                }
            ],
            occurred_at=ensure_naive_utc(occurred_at) or occurred_at,
            due_at=ensure_naive_utc(due_at),
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=None,
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
        if not any(token in sentence for token in _LEARNING_SUBJECT_TOKENS):
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
        if any(token in sentence for token in future_markers):
            return True
        # R28 修复：中文事件式承诺（考试/交作业/上课/小测等）没有"我会/我要"这类
        # 第一人称意图标记，此前全部漏判为 self，due_at 永不解析，固化链的
        # commitment+due_at 自动固化通道也随之失活。仅当句子带可解析的时间锚时
        # 才判为 commitment——否则 extract_candidate 会因 due_at None 整条放弃。
        event_markers = (
            "考试",
            "期中",
            "期末",
            "小测",
            "测验",
            "要交",
            "得交",
            "要考",
            "有课",
            "上课",
            "deadline",
            "截止",
            "截稿",
            "面试",
        )
        # "有英语课/有一节高数课"等"有…课"变体不含连续子串"有课"，用正则兜住。
        if not any(token in sentence for token in event_markers) and not re.search(r"有[^，。！？]{0,4}课", sentence):
            return False
        return parse_commitment_due_at(sentence) is not None

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
        key = f"{user_id}:null".encode()
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
        # R28 修复："下周三/这周五"等星期表达此前落进"下周/这周"兜底分支，
        # occurred_at 会偏到周一/周日；先解析星期锚，让事件日对齐真实日期。
        weekday_anchor = resolve_weekday_anchor(sentence)
        if weekday_anchor is not None:
            target, kind = weekday_anchor
            return target, kind
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
