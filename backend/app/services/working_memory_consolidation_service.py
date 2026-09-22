from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.cache import cache_service
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate, MemoryInferredWriteLaneService
from app.services.memory_service import MemoryService
from app.working_memory.schema import WorkingMemoryEntry
from app.working_memory.service import WorkingMemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WorkingMemoryConsolidationService:
    STRONG_CONFIRM_PHRASES = (
        "记住这个",
        "记下来",
        "帮我记住",
        "把这个记住",
        "就记这个",
        "记一下这个",
    )
    # M2: 拒绝判定分级——记忆显式短语可单独命中；宽泛否定短语必须与记忆语境
    # 词共现，避免"不对，这道题应该…"这类普通纠正被误判为撤回记忆。
    STRONG_REJECTION_PHRASES = (
        "别记这个",
        "记错了",
        "别记了",
    )
    WEAK_REJECTION_PHRASES = (
        "不对",
        "不是这样",
    )
    REJECTION_MEMORY_CONTEXT_TOKENS = (
        "记",
        "记忆",
        "撤回",
        "删掉",
        "删了",
    )
    CONFIRMATION_ANCHOR_WINDOW = timedelta(minutes=10)
    REJECTION_ANCHOR_WINDOW = timedelta(minutes=10)

    def __init__(self, db, redis_client=None, *, now_fn=_utcnow):
        self.db = db
        self.working_memory = WorkingMemoryService(redis_client or cache_service.redis, now_fn=now_fn)
        self.kill_switches = AuroraStage19KillSwitchService()
        self._now_fn = now_fn

    @classmethod
    def is_explicit_confirmation(cls, user_message: str) -> bool:
        normalized = user_message.strip()
        return any(phrase in normalized for phrase in cls.STRONG_CONFIRM_PHRASES)

    @classmethod
    def is_explicit_rejection(cls, user_message: str) -> bool:
        normalized = user_message.strip()
        if any(phrase in normalized for phrase in cls.STRONG_REJECTION_PHRASES):
            return True
        if not any(token in normalized for token in cls.REJECTION_MEMORY_CONTEXT_TOKENS):
            return False
        return any(phrase in normalized for phrase in cls.WEAK_REJECTION_PHRASES)

    def should_consolidate(self, entry: WorkingMemoryEntry, *, explicit_confirmation: bool, now: datetime) -> bool:
        if entry.rejected or entry.consolidated_to_l1_id is not None:
            return False
        if entry.subject_type == "commitment" and entry.due_at is not None:
            return True
        if explicit_confirmation and now - entry.last_seen_at <= self.CONFIRMATION_ANCHOR_WINDOW:
            return True
        time_span_seconds = max(0.0, (entry.last_seen_at - entry.first_seen_at).total_seconds())
        return entry.mention_count >= 3 and time_span_seconds >= 60

    async def promote_entry_now(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        entry: WorkingMemoryEntry,
        declared_fact: bool = False,
    ) -> WorkingMemoryEntry | None:
        """明示事实（declared_fact）即时固化：不等重复提及/口令确认。

        单次用户自我陈述（考试/截止、弱点、目标、约束）若只停留 session 级
        工作记忆，会随会话消亡——Day1 追问即失忆（NORTHSTAR-LOOP1 BP-2）。
        走既有固化链（``_consolidate_entry`` → L1 门禁/去重/冲突裁决全保留）；
        consolidation kill-switch 关闭时不提升；重复提升经 semantic_key 去重
        返回 None，无副作用。
        """
        if not await self.kill_switches.is_live("consolidation_enabled"):
            return None
        return await self._consolidate_entry(
            user_id=user_id, session_id=session_id, entry=entry, declared_fact=declared_fact
        )

    async def maybe_consolidate_recent_entries(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        explicit_confirmation: bool = False,
    ) -> list[WorkingMemoryEntry]:
        if not await self.kill_switches.is_live("consolidation_enabled"):
            return []
        now = self._now_fn()
        entries = await self.working_memory.list_entries(
            user_id=str(user_id),
            session_id=str(session_id),
            limit=None,
            include_rejected=True,
        )
        accepted: list[WorkingMemoryEntry] = []
        for entry in entries:
            if not self.should_consolidate(entry, explicit_confirmation=explicit_confirmation, now=now):
                continue
            updated = await self._consolidate_entry(user_id=user_id, session_id=session_id, entry=entry)
            if updated is not None:
                accepted.append(updated)
        return accepted

    async def handle_possible_rejection(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
    ) -> WorkingMemoryEntry | None:
        if not self.is_explicit_rejection(user_message):
            return None
        now = self._now_fn()
        entries = await self.working_memory.list_entries(
            user_id=str(user_id),
            session_id=str(session_id),
            limit=None,
            include_rejected=True,
        )
        # M2: 只允许撤回"时间邻近"的已固化条目，并在候选中取最近活跃的
        # （list_entries 按 salience 排序，直接取首个会误撤无关重要记忆）。
        candidates = [
            entry
            for entry in entries
            if entry.consolidated_to_l1_id
            and not entry.rejected
            and now - entry.last_seen_at <= self.REJECTION_ANCHOR_WINDOW
        ]
        if not candidates:
            return None
        target = max(candidates, key=lambda entry: entry.last_seen_at)
        memory_service = MemoryService(self.db)
        await memory_service.retract_memory(
            kind="episodic",
            memory_id=UUID(str(target.consolidated_to_l1_id)),
            user_id=user_id,
            reason="working_memory_rejected",
        )
        return await self.working_memory.mark_rejected(
            user_id=str(user_id),
            session_id=str(session_id),
            entry_id=target.entry_id,
        )

    async def _consolidate_entry(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        entry: WorkingMemoryEntry,
        declared_fact: bool = False,
    ) -> WorkingMemoryEntry | None:
        lane = MemoryInferredWriteLaneService(self.db)
        candidate = InferredEpisodicCandidate(
            candidate_text=entry.text,
            subject_type=entry.subject_type,
            confidence=entry.confidence,
            evidence_token=entry.evidence_token,
            decay_policy="due_at+7d" if entry.subject_type == "commitment" and entry.due_at else "30d",
            source_lane=MemoryInferredWriteLaneService.SOURCE_LANE,
            semantic_key=entry.semantic_key,
            evidence_refs=[
                {
                    "type": "chat_turn",
                    "id": entry.evidence_token,
                    "schema_version": "stage19.rule_y.v1",
                }
            ],
            occurred_at=entry.occurred_at,
            due_at=entry.due_at,
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=None,
            # MEM-AMNESIA：明示事实标记必须随重建候选透传——否则 L1 去重会退回
            # 「一轮一条」的 evidence_token OR 语义，把同轮其余明示事实误判为
            # 重复（实测 weakness/constraint 两句被吞）。
            declared_fact=declared_fact,
        )
        record = await lane.write_candidate_to_l1(
            user_id=user_id,
            session_id=session_id,
            candidate=candidate,
            force_write=True,
        )
        if record is None:
            return None
        updated = await self.working_memory.mark_consolidated(
            user_id=str(user_id),
            session_id=str(session_id),
            entry_id=entry.entry_id,
            l1_memory_id=str(record.id),
        )
        if updated is None:
            return replace(entry, consolidated_to_l1_id=str(record.id))
        return updated
