from __future__ import annotations

from uuid import UUID

from loguru import logger

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.llm_extractor_service import LlmExtractorService
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.working_memory.schema import WorkingMemoryEntry
from app.working_memory.service import WorkingMemoryService


class WorkingMemoryPipelineService:
    def __init__(self, db) -> None:
        self.db = db
        self.working_memory = WorkingMemoryService(cache_service.redis)
        self.kill_switches = AuroraStage19KillSwitchService()
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
        declared_candidates: list[InferredEpisodicCandidate] | None = None,
    ) -> list[WorkingMemoryEntry]:
        accepted_entries: list[WorkingMemoryEntry] = []
        llm_candidates: list[InferredEpisodicCandidate] = []
        wm_mode = await self.kill_switches.get_feature_mode("working_memory_enabled")
        llm_mode = await self.kill_switches.get_feature_mode("llm_extractor_enabled")

        if wm_mode != "off":
            # NBP-6（2026-09-22）：明示事实快速道必须先于 LLM 抽取调用执行。
            # 此前全部候选（含明示事实）都排在 dry_run_extract 的真实 LLM 往返
            # 之后——主路径每轮一次 llm_service.chat_json（fallback 链含
            # 45s/90s 首块超时），供应商拥塞时整条写账带内滞留 30-90s，用户
            # 「刚说完→立刻看今日面板/记忆账本」读到空投影（NORTHSTAR-LOOP3
            # NBP-6 实证：抽取 15:27:38 → L1 落库 15:28:29，带内 51.2s；30s
            # 探针差 1.6s 扑空）。明示事实抽取是确定性正则
            # （extract_declared_fact_candidates，零 LLM），与 LLM 抽取输出
            # 零依赖；其 upsert+promote 只耗 Redis+DB 写，提前执行后投影
            # 延迟与 LLM 健康度解耦（亚秒级）。LLM 抽取面（规则/LLM 候选
            # 补强腿）照旧在其后运行，抽取质量零变化。
            for candidate in declared_candidates or []:
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
                # MEM-AMNESIA（2026-09-22）：明示事实不等「mention_count>=3 才固化」
                # ——Day0 单次声明的科目/截止/弱点/目标若只停留 session 级工作记忆，
                # 会随会话消亡，Day1 追问即失忆（NORTHSTAR-LOOP1 BP-2/GP-07）。
                # 即时提升走既有固化链（同一 L1 门禁/去重/冲突裁决），幂等由
                # semantic_key/evidence_token 去重兜底；重复提升返回 None 无副作用。
                if getattr(candidate, "declared_fact", False):
                    promoted = await self.consolidation.promote_entry_now(
                        user_id=user_id,
                        session_id=session_id,
                        entry=entry,
                        declared_fact=True,
                    )
                    if promoted is not None:
                        accepted_entries[-1] = promoted

        if llm_mode in {"shadow", "live"} or settings.SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED:
            # LLM 抽取失败（超时/熔断 503/网络）不得炸整轮 pipeline：规则候选与
            # 显式口令 fallback 不依赖 LLM，必须照常走完（mr1 零条入库根因）。
            try:
                llm_candidates = await self.llm_extractor.dry_run_extract(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    evidence_token=evidence_token,
                )
            except Exception as exc:
                logger.warning("LLM extractor failed, falling back to rule candidates only: {}", exc)
                llm_candidates = []

        if wm_mode == "off":
            return accepted_entries

        effective_candidates = [item for item in [rule_candidate] if item is not None]
        if llm_mode == "live":
            effective_candidates.extend(llm_candidates)

        for candidate in effective_candidates:
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
