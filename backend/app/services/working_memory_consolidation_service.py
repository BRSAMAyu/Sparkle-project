from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config import settings
from app.core.cache import cache_service
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
    REJECTION_PHRASES = (
        "不对",
        "不是这样",
        "别记这个",
        "记错了",
        "别记了",
    )
    CONFIRMATION_ANCHOR_WINDOW = timedelta(minutes=10)

    def __init__(self, db, redis_client=None, *, now_fn=_utcnow):
        self.db = db
        self.working_memory = WorkingMemoryService(redis_client or cache_service.redis, now_fn=now_fn)
        self._now_fn = now_fn

    @classmethod
    def is_explicit_confirmation(cls, user_message: str) -> bool:
        normalized = user_message.strip()
        return any(phrase in normalized for phrase in cls.STRONG_CONFIRM_PHRASES)

    @classmethod
    def is_explicit_rejection(cls, user_message: str) -> bool:
        normalized = user_message.strip()
        return any(phrase in normalized for phrase in cls.REJECTION_PHRASES)

    def should_consolidate(self, entry: WorkingMemoryEntry, *, explicit_confirmation: bool, now: datetime) -> bool:
        if entry.rejected or entry.consolidated_to_l1_id is not None:
            return False
        if entry.subject_type == "commitment" and entry.due_at is not None:
            return True
        if explicit_confirmation and now - entry.last_seen_at <= self.CONFIRMATION_ANCHOR_WINDOW:
            return True
        time_span_seconds = max(0.0, (entry.last_seen_at - entry.first_seen_at).total_seconds())
        return entry.mention_count >= 3 and time_span_seconds >= 60

    async def maybe_consolidate_recent_entries(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        explicit_confirmation: bool = False,
    ) -> list[WorkingMemoryEntry]:
        if not settings.SPARKLE_CONSOLIDATION_ENABLED:
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
        entries = await self.working_memory.list_entries(
            user_id=str(user_id),
            session_id=str(session_id),
            limit=None,
            include_rejected=True,
        )
        target = next((entry for entry in entries if entry.consolidated_to_l1_id and not entry.rejected), None)
        if target is None:
            return None
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
