from __future__ import annotations

from uuid import UUID

from app.config import settings
from app.core.cache import cache_service
from app.services.llm_extractor_service import LlmExtractorService
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.working_memory.schema import WorkingMemoryEntry
from app.working_memory.service import WorkingMemoryService


class WorkingMemoryPipelineService:
    def __init__(self, db) -> None:
        self.db = db
        self.working_memory = WorkingMemoryService(cache_service.redis)
        self.llm_extractor = LlmExtractorService()
        self.consolidation = WorkingMemoryConsolidationService(db, cache_service.redis)

    async def process_chat_turn(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_message: str,
        evidence_token: str,
        rule_candidate: InferredEpisodicCandidate | None,
    ) -> list[WorkingMemoryEntry]:
        accepted_entries: list[WorkingMemoryEntry] = []
        llm_candidates: list[InferredEpisodicCandidate] = []

        if settings.SPARKLE_LLM_EXTRACTOR_ENABLED or settings.SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED:
            llm_candidates = await self.llm_extractor.dry_run_extract(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                evidence_token=evidence_token,
            )

        if not settings.SPARKLE_WORKING_MEMORY_ENABLED:
            return accepted_entries

        for candidate in [item for item in [rule_candidate, *llm_candidates] if item is not None]:
            entry = await self.working_memory.upsert_entry(
                user_id=str(user_id),
                session_id=str(session_id),
                text=candidate.candidate_text,
                semantic_key=candidate.semantic_key,
                salience_score=max(candidate.confidence, 0.2),
                subject_type=candidate.subject_type,
                confidence=candidate.confidence,
                evidence_token=candidate.evidence_token,
                occurred_at=candidate.occurred_at,
                source_turn_id=candidate.evidence_token,
                due_at=candidate.due_at,
                source_lane=candidate.source_lane,
            )
            accepted_entries.append(entry)

        if self.consolidation.is_explicit_rejection(user_message):
            rejected = await self.consolidation.handle_possible_rejection(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
            )
            if rejected is not None:
                accepted_entries.append(rejected)

        explicit_confirmation = self.consolidation.is_explicit_confirmation(user_message)
        if explicit_confirmation and accepted_entries:
            newest = accepted_entries[0]
            confirmed = await self.working_memory.mark_correct(
                user_id=str(user_id),
                session_id=str(session_id),
                entry_id=newest.entry_id,
            )
            if confirmed is not None:
                accepted_entries[0] = confirmed

        consolidated = await self.consolidation.maybe_consolidate_recent_entries(
            user_id=user_id,
            session_id=session_id,
            explicit_confirmation=explicit_confirmation,
        )
        accepted_entries.extend(consolidated)
        return accepted_entries
