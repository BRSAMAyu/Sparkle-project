"""MEM-AMNESIA：跨会话记忆失忆修复回归（NORTHSTAR-LOOP1 BP-2 验收断点）。

验收现场（v3-output/NORTHSTAR-LOOP1/evidence/B1 + snapshot-memory-episodic-after-day1）：
用户 Day0 在 chat 明示「离散数学期末 7 天后 / 自评 42/100 / 最薄弱图论（CH4）/
每天只能投入 165 分钟」，Day1 新 session 追问 → AI 自述「我这里没有完整记录」；
/memory/episodic 仅 1 条 task_outcome，对话事实零入库。

根因（修复前）：
1. ``parse_commitment_due_at`` 不支持「N 天后」→ 考试句 due_at 永不解析，
   整条放弃（commitment+due_at None 直接丢弃）；
2. 明示事实候选（弱点句）置信 0.79 < MEMORY_INFERRED_MIN_CONFIDENCE(0.9)
   → L1 直写门禁拦截；
3. working-memory live 路径（默认）需 mention_count>=3 且跨度>=60s 才固化
   → 单次声明永远停留在 session 级存储，随会话消亡，跨会话 episodic 零写入。

本文件红绿锁定：用户明示事实（考试/截止、弱点、目标、时间约束）必须产出
可入库候选、走通跨会话 episodic 写入，且幂等（同一事实重复对话不重复入库）。
全程确定性正则，零 LLM、零新增投递点。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services import commitment_parser as commitment_parser_module
from app.services import memory_inferred_write_lane as lane_module
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

# B1 验收原句（NORTHSTAR-LOOP1 evidence/steps/B1_onboarding-diagnostic-chat.json）。
B1_ONBOARDING_MESSAGE = (
    "你好，我要开始备考：离散数学期末考试在 7 天后（闭卷，100 分卷）。"
    "我的情况：自评当前掌握度大约 42/100；最薄弱的章是图论（CH4）；"
    "一个具体的困惑：我总是分不清欧拉回路和哈密顿回路的判定条件，考试肯定考。"
    "我每天只能投入 165 分钟。请帮我建立目标并给我冲刺计划。"
)

# 固定时钟：2026-09-21 是周一（UTC），让「N 天后」的期望值可精确断言。
FROZEN_NOW = datetime(2026, 9, 21, 12, 0, 0)


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch):
    monkeypatch.setattr(commitment_parser_module, "_utcnow", lambda: FROZEN_NOW)
    monkeypatch.setattr(lane_module, "_utcnow", lambda: FROZEN_NOW)


async def _create_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _create_user_turn(db_session, user_id, session_id, content: str) -> ChatMessage:
    message = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=MessageRole.USER,
        content=content,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


async def _lane_episodic_rows(db_session, user_id: uuid4) -> list[EpisodicMemory]:
    return (
        (
            await db_session.execute(
                select(EpisodicMemory).where(
                    EpisodicMemory.user_id == user_id,
                    EpisodicMemory.source_lane == "inferred_extraction",
                    EpisodicMemory.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )


class TestParseCommitmentDueAtDaysAfter:
    """断点①：N 天后/N天以后 必须可解析为 due_at（此前返回 None 整条丢弃）。"""

    def test_seven_days_after_with_spaces(self):
        due = commitment_parser_module.parse_commitment_due_at("离散数学期末考试在 7 天后")
        assert due == datetime(2026, 9, 28, 18, 0, 0)

    def test_three_days_after_compact(self):
        due = commitment_parser_module.parse_commitment_due_at("期末考试3天后")
        assert due == datetime(2026, 9, 24, 18, 0, 0)

    def test_days_after_naive_utc(self):
        due = commitment_parser_module.parse_commitment_due_at("14天后要交论文")
        assert due is not None
        assert due.tzinfo is None
        assert due == datetime(2026, 10, 5, 18, 0, 0)


class TestDeclaredFactCandidateExtraction:
    """断点②：明示事实必须产出置信≥0.9 的候选（此前 0.79 被 L1 门禁拦截）。"""

    def _extract(self, user_message: str) -> list:
        service = MemoryInferredWriteLaneService(db=None)
        return service.extract_declared_fact_candidates(
            user_id=uuid4(),
            user_message=user_message,
            evidence_token="turn_declared",
        )

    def test_b1_onboarding_yields_declared_candidates(self):
        candidates = self._extract(B1_ONBOARDING_MESSAGE)
        assert len(candidates) >= 3, f"Day0 明示事实至少应捕获 考试/弱点/约束 三类，实际 {len(candidates)}"

    def test_exam_fact_is_commitment_with_due_at(self):
        candidates = self._extract(B1_ONBOARDING_MESSAGE)
        exam = [c for c in candidates if c.subject_type == "commitment"]
        assert exam, "期末考试句必须以 commitment 入库"
        assert exam[0].due_at == datetime(2026, 9, 28, 18, 0, 0)
        assert exam[0].decay_policy == "due_at+7d"

    def test_weakness_fact_captured(self):
        candidates = self._extract(B1_ONBOARDING_MESSAGE)
        weakness = [c for c in candidates if "薄弱" in c.candidate_text]
        assert weakness, "「最薄弱的章是图论」必须被捕获（GP-07 纠正保持的原料）"
        assert weakness[0].confidence >= 0.9, "明示事实置信必须越过 L1 直写门槛（0.9）"

    def test_time_constraint_fact_captured(self):
        candidates = self._extract(B1_ONBOARDING_MESSAGE)
        constraint = [c for c in candidates if "165" in c.candidate_text]
        assert constraint, "「每天只能投入 165 分钟」是计划约束，必须被捕获"

    def test_all_candidates_cross_l1_confidence_gate_and_naive_utc(self):
        for candidate in self._extract(B1_ONBOARDING_MESSAGE):
            assert candidate.confidence >= settings.MEMORY_INFERRED_MIN_CONFIDENCE
            assert candidate.occurred_at.tzinfo is None
            if candidate.due_at is not None:
                assert candidate.due_at.tzinfo is None

    def test_idempotent_semantic_keys_for_repeated_declaration(self):
        first = self._extract(B1_ONBOARDING_MESSAGE)
        second = self._extract(B1_ONBOARDING_MESSAGE)
        keys_first = {c.semantic_key for c in first}
        keys_second = {c.semantic_key for c in second}
        assert keys_first == keys_second, "同一事实重复对话必须命中同一 semantic_key（去重依据）"

    def test_plain_chat_produces_no_declared_candidates(self):
        assert self._extract("今天天气真不错，心情很好。") == []

    def test_question_about_past_not_captured(self):
        assert self._extract("我之前跟你说过我哪一章薄弱来着？") == []

    def test_banned_identity_topic_not_captured(self):
        # 人格判定/负面自我标签不得长期化（与显式口令通道同一禁入面）。
        assert self._extract("我这人数学永远学不明白，我就是很笨。") == []


class TestDeclaredFactL1WriteFallbackLane:
    """断点③（fallback 形态，working-memory 关闭时）：明示事实必须写入跨会话 episodic。"""

    @pytest.mark.asyncio
    async def test_process_chat_turn_writes_declared_facts(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的，已整理。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        rows = await _lane_episodic_rows(db_session, user.id)
        assert len(rows) >= 2, f"明示事实至少写入 考试+弱点 两条 episodic，实际 {len(rows)}"
        summaries = " | ".join(row.summary for row in rows)
        assert any("期末考试" in row.summary for row in rows), summaries
        exam_row = next(row for row in rows if "期末考试" in row.summary)
        assert exam_row.due_at is not None, "考试事实必须带 due_at（固化链依赖）"
        assert any("薄弱" in row.summary for row in rows), summaries

    @pytest.mark.asyncio
    async def test_repeated_declaration_does_not_duplicate_rows(self, db_session, monkeypatch):
        """幂等红线：同一事实重复对话不得重复入库。"""
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        for _ in range(2):
            await service.process_chat_turn(
                user_id=user.id,
                session_id=session_id,
                user_message=B1_ONBOARDING_MESSAGE,
                assistant_message="好的。",
                user_message_id=str(turn.id),
                assistant_message_id=None,
            )

        rows = await _lane_episodic_rows(db_session, user.id)
        semantic_keys = [row.semantic_key for row in rows]
        assert len(semantic_keys) == len(set(semantic_keys)), "同一事实重复入库（semantic_key 重复）"

    @pytest.mark.asyncio
    async def test_user_memory_disabled_blocks_declared_facts(self, db_session, monkeypatch):
        """护栏：用户关闭记忆时明示事实也不得落库（与显式口令通道同款）。"""
        from app.models.user_memory_settings import UserMemorySettings

        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        db_session.add(
            UserMemorySettings(
                user_id=user.id,
                enabled=False,
                allow_episodic=False,
            )
        )
        await db_session.commit()
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        rows = await _lane_episodic_rows(db_session, user.id)
        assert len(rows) == 0, "用户关闭记忆时明示事实不得落库"


class TestDeclaredFactL1WriteWorkingMemoryLiveLane:
    """断点③（默认 live 形态）：working-memory 活性路径必须立即固化明示事实。

    此前该路径要 mention_count>=3 才提升 L1，单次声明永远停留 session 级。
    """

    @pytest.mark.asyncio
    async def test_live_pipeline_promotes_declared_facts_to_l1(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_CONSOLIDATION_ENABLED", True, raising=False)
        # 不 mock working_memory kill switch → 走默认 live 路径。

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=session_id,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的，已整理。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )

        rows = await _lane_episodic_rows(db_session, user.id)
        assert len(rows) >= 2, f"live 路径明示事实必须即时固化为跨会话 episodic（不等重复提及），实际 {len(rows)}"
        assert any("期末考试" in row.summary for row in rows)
        assert any("薄弱" in row.summary for row in rows)

    @pytest.mark.asyncio
    async def test_live_pipeline_idempotent_on_second_turn(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_CONSOLIDATION_ENABLED", True, raising=False)

        user = await _create_user(db_session)
        session_id = uuid4()
        turn = await _create_user_turn(db_session, user.id, session_id, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        for _ in range(2):
            await service.process_chat_turn(
                user_id=user.id,
                session_id=session_id,
                user_message=B1_ONBOARDING_MESSAGE,
                assistant_message="好的。",
                user_message_id=str(turn.id),
                assistant_message_id=None,
            )

        rows = await _lane_episodic_rows(db_session, user.id)
        semantic_keys = [row.semantic_key for row in rows]
        assert len(semantic_keys) == len(set(semantic_keys)), "重复轮次后同一事实重复入库"


class TestDeclaredFactRecallInjection:
    """召回腿绿证：写入的明示事实必须能被下一会话的上下文装配读到。

    生产 /ws/chat 的 stage34 注入面（context_builder._attach_stage34_memory_context
    与 context_pack.ContextPackBuilder）都从 list_recent_episodic（按用户跨
    session）拉取——本测试证明明示事实行能走完该装配面进入 prompt 面。
    """

    @pytest.mark.asyncio
    async def test_next_session_context_pack_surfaces_declared_facts(self, db_session, monkeypatch):
        import json

        from app.core.context_budget import ContextBudgetScheduler
        from app.core.context_pack import ContextPackBuilder

        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))
        # 复用 memory_use_selfcheck_wiring 的 pack harness 基线（关掉依赖外部
        # embedding/排序服务的可选面，聚焦注入本身）。
        monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", False, raising=False)
        monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
        monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
        monkeypatch.setattr(settings, "ENABLE_PERSONALIZED_RANKING", False, raising=False)
        monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUSING", False, raising=False)
        monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False, raising=False)
        monkeypatch.setattr(settings, "ENABLE_DECISION_CONTEXT", True, raising=False)

        user = await _create_user(db_session)
        day0_session = uuid4()
        turn = await _create_user_turn(db_session, user.id, day0_session, B1_ONBOARDING_MESSAGE)

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=user.id,
            session_id=day0_session,
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="好的，已整理。",
            user_message_id=str(turn.id),
            assistant_message_id=None,
        )
        await db_session.commit()

        # Day1：全新 session 的追问轮。
        scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
        pack = await ContextPackBuilder(db_session, scheduler=scheduler).build(
            str(user.id),
            intent="chat",
            query_text="我之前说最薄弱的是哪一章来着？",
        )
        surfaced = json.dumps(
            [memory.get("summary") or "" for memory in (pack.episodic_memories or [])],
            ensure_ascii=False,
        )
        # 查询相关的明示事实必须 surface 进 prompt 面（GP-07 场景：追问弱点
        # → 系统记得「图论」）。
        assert "薄弱" in surfaced, f"Day1 上下文未召回弱点明示事实：{surfaced}"
        # 其余明示事实（考试/约束）必须仍在召回候选集中——M-05 selfcheck 按
        # 本轮 query 相关性做 prompt 面降档（反过度 personalized），但记忆
        # 本身可被后续轮次合法召回，而不是从未入库/从未被读。
        from app.services.memory_service import MemoryService

        recalled = await MemoryService(db_session).list_recent_episodic(user.id, limit=12)
        recalled_text = json.dumps([str(row.summary or "") for row in recalled], ensure_ascii=False)
        assert "期末考试" in recalled_text, "考试明示事实不在召回候选集"
        assert "165" in recalled_text, "时间约束明示事实不在召回候选集"
