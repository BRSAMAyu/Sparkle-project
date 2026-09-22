"""NBP-1（NORTHSTAR-LOOP2）：WS/gRPC 主链路记忆写账断裂修复回归。

验收现场（v3-output/NORTHSTAR-LOOP2/REPORT.md NBP-1 + evidence/probe-rest-memory-write.json）：
同一句 B1 明示事实，REST ``POST /api/v1/chat`` 写 3 条 declared facts（due_at 正确），
WS ``/ws/chat``（gateway → gRPC StreamChat）写 0 条（判卷后即时查 + 10 分钟后复查均 0，
排除异步延迟）。

根因（修复前，三处叠加）：
1. 澄清/确认类快交互短路轮（sufficiency / phase-A preflight / goal-quality，
   ``_emit_fast_interaction``）只发协议帧——不持久化、不建 finalize 任务，整轮
   零记忆写账触发器。B1 Day0 onboarding（"请帮我建立目标…"信息不足 → 澄清门）
   正是这类轮；
2. 主路径唯一带用户原文的 fallback（``_write_turn_end_episodic_memory`` 尾部
   enqueue_from_chat_turn）被双重架空：摘要非空即跳过 + 仅 Step14 主路径建
   finalize 任务可达；
3. 全 persist 路径的触发器 ``enqueue_from_session(user_message=None)`` 依赖
   ``_load_latest_user_turn`` 从 Postgres 回捞 user 行——而 WS 链路的 user 行
   由网关 Redis persister 异步落库，一次性后台任务稳输竞态（missing_user_turn
   → return None，无重试）。

修复（单一事实源纪律）：WS 收尾统一直调与 REST api/v1/chat.py 同款
``enqueue_from_chat_turn`` 面——``_persist_assistant_message`` 新增 user_message
入参（调用方在手原文时直传），快交互出口新增 turn_capture；移除被架空的旧
fallback（同时消除与持久化点并发的 semantic_key check-then-insert 双写竞争）。

红线断言：REST 面行为零变化（无 user_message 的旧调用方仍走
enqueue_from_session）；WS 协议帧形状不变；抽取面零 LLM。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.orchestration.validation_engine import ValidationEngineMixin
from app.services import commitment_parser as commitment_parser_module
from app.services import memory_inferred_write_lane as lane_module
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

# B1 验收原句（NORTHSTAR-LOOP2 evidence/steps/B1_onboarding-diagnostic-chat.json）。
B1_ONBOARDING_MESSAGE = (
    "你好，我要开始备考：离散数学期末考试在 7 天后（闭卷，100 分卷）。"
    "我的情况：自评当前掌握度大约 42/100；最薄弱的章是图论（CH4）；"
    "一个具体的困惑：我总是分不清欧拉回路和哈密顿回路的判定条件，考试肯定考。"
    "我每天只能投入 165 分钟。请帮我建立目标并给我冲刺计划。"
)

FROZEN_NOW = datetime(2026, 9, 21, 12, 0, 0)


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch):
    monkeypatch.setattr(commitment_parser_module, "_utcnow", lambda: FROZEN_NOW)
    monkeypatch.setattr(lane_module, "_utcnow", lambda: FROZEN_NOW)


def _patch_lane_enqueue(monkeypatch) -> MagicMock:
    """把捕获面 enqueue_from_chat_turn 换成同步探针（返回 AsyncMock 形状的 MagicMock）。"""
    probe = MagicMock(return_value=None)
    monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_chat_turn", probe)
    return probe


def _patch_lane_enqueue_session(monkeypatch) -> MagicMock:
    probe = MagicMock(return_value=None)
    monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_session", probe)
    return probe


# ============ 断点①：快交互短路轮必须带记忆捕获 ============


class MinimalValidationOrchestrator(ValidationEngineMixin):
    def __init__(self):
        self.redis = MagicMock()


@pytest.fixture
def validation_orchestrator():
    return MinimalValidationOrchestrator()


class TestEmitFastInteractionTurnCapture:
    @pytest.mark.asyncio
    async def test_short_circuit_turn_enqueues_declared_fact_capture(self, validation_orchestrator, monkeypatch):
        """红→绿：澄清短路轮发出 STOP 帧的同时必须触发 declared-fact 捕获面。"""
        probe = _patch_lane_enqueue(monkeypatch)
        stream_callback = AsyncMock()
        user_id, session_id, request_id = str(uuid4()), str(uuid4()), "req-nbp1"

        await validation_orchestrator._emit_fast_interaction(
            stream_callback=stream_callback,
            text="您期望本次期末考试达到多少分？",
            details="clarify",
            turn_capture={
                "user_id": user_id,
                "session_id": session_id,
                "user_message": B1_ONBOARDING_MESSAGE,
                "request_id": request_id,
            },
        )

        assert probe.called, "快交互短路轮必须调用 REST 同款 enqueue_from_chat_turn 面"
        kwargs = probe.call_args.kwargs
        assert kwargs["user_id"] == UUID(user_id)
        assert kwargs["session_id"] == UUID(session_id)
        assert kwargs["user_message"] == B1_ONBOARDING_MESSAGE, "必须携带用户原文（抽取面输入）"
        assert kwargs["assistant_message"] == "您期望本次期末考试达到多少分？"
        assert kwargs["user_message_id"] == request_id

    @pytest.mark.asyncio
    async def test_wire_frames_shape_unchanged(self, validation_orchestrator, monkeypatch):
        """红线：WS 流式协议帧形状不变（status_update + full_text/STOP 两帧）。"""
        _patch_lane_enqueue(monkeypatch)
        stream_callback = AsyncMock()

        await validation_orchestrator._emit_fast_interaction(
            stream_callback=stream_callback,
            text="确认一下方向",
            details="thinking",
            metadata={"requires_confirmation": "true"},
        )

        assert stream_callback.await_count == 2
        first, second = stream_callback.await_args_list
        assert first.args[0].status_update.state == agent_service_pb2.AgentStatus.THINKING
        assert second.args[0].full_text == "确认一下方向"
        assert second.args[0].finish_reason == agent_service_pb2.STOP

    @pytest.mark.asyncio
    async def test_no_turn_capture_keeps_legacy_behavior(self, validation_orchestrator, monkeypatch):
        """红线：未接线的旧调用方（无 turn_capture）零行为变化。"""
        probe = _patch_lane_enqueue(monkeypatch)
        stream_callback = AsyncMock()

        await validation_orchestrator._emit_fast_interaction(
            stream_callback=stream_callback,
            text="hello",
            details="thinking",
        )

        assert not probe.called
        assert stream_callback.await_count == 2

    @pytest.mark.asyncio
    async def test_invalid_turn_capture_never_breaks_reply(self, validation_orchestrator, monkeypatch):
        """红线：turn_capture 形状非法时捕获静默跳过，回复主链路不受影响。"""
        probe = _patch_lane_enqueue(monkeypatch)
        stream_callback = AsyncMock()

        await validation_orchestrator._emit_fast_interaction(
            stream_callback=stream_callback,
            text="hello",
            details="thinking",
            turn_capture={"user_id": "not-a-uuid", "session_id": "also-bad"},
        )

        assert not probe.called
        assert stream_callback.await_count == 2


# ============ 断点③：persist 收尾必须直用用户原文（不再赌 DB 回捞） ============


class MinimalPersistenceOrchestrator(PersistenceLayerMixin):
    def __init__(self):
        self.redis = MagicMock()

    _coerce_session_uuid = ChatOrchestrator._coerce_session_uuid


@pytest.fixture
def persistence_orchestrator():
    return MinimalPersistenceOrchestrator()


def _stub_persist_session(monkeypatch) -> tuple[MagicMock, ChatMessage | None]:
    """独立持久化 session 的桩：捕获 add 的 ChatMessage 并在 flush 时回填 id。"""
    holder: list[ChatMessage] = []

    persist_session = MagicMock()
    persist_session.add = MagicMock(side_effect=holder.append)

    async def _flush():
        for msg in holder:
            if msg.id is None:
                msg.id = uuid4()

    persist_session.flush = _flush
    persist_session.commit = AsyncMock()

    class _SessionCtx:
        async def __aenter__(self):
            return persist_session

        async def __aexit__(self, *args):
            return False

    import app.db.session as dbs

    monkeypatch.setattr(dbs, "AsyncSessionLocal", lambda: _SessionCtx())
    return persist_session, (holder[0] if holder else None)


class TestPersistAssistantMessageTurnCapture:
    @pytest.mark.asyncio
    async def test_user_message_routes_to_chat_turn_surface(self, persistence_orchestrator, monkeypatch):
        probe = _patch_lane_enqueue(monkeypatch)
        session_probe = _patch_lane_enqueue_session(monkeypatch)
        _stub_persist_session(monkeypatch)

        await persistence_orchestrator._persist_assistant_message(
            active_db=MagicMock(),
            user_id=str(uuid4()),
            session_id=str(uuid4()),
            full_response="已收到你的备考信息。",
            user_message=B1_ONBOARDING_MESSAGE,
        )

        assert probe.called, "调用方在手用户原文时必须直调 enqueue_from_chat_turn（不赌 DB 回捞）"
        kwargs = probe.call_args.kwargs
        assert kwargs["user_message"] == B1_ONBOARDING_MESSAGE
        assert kwargs["assistant_message"] == "已收到你的备考信息。"
        assert kwargs["user_message_id"], "evidence_token 必须是落库 assistant 行 id（非空）"
        assert not session_probe.called, "直传原文时不得再走 enqueue_from_session 双触发"

    @pytest.mark.asyncio
    async def test_legacy_callers_keep_session_surface(self, persistence_orchestrator, monkeypatch):
        """红线：无 user_message 的旧调用方保持 enqueue_from_session 行为零变化。"""
        probe = _patch_lane_enqueue(monkeypatch)
        session_probe = _patch_lane_enqueue_session(monkeypatch)
        _stub_persist_session(monkeypatch)

        await persistence_orchestrator._persist_assistant_message(
            active_db=MagicMock(),
            user_id=str(uuid4()),
            session_id=str(uuid4()),
            full_response="回复",
        )

        assert session_probe.called
        assert not probe.called


# ============ 断点②：旧 finalize fallback 移除后不得双触发 ============


class TestNoDoubleCaptureFromFinalize:
    @pytest.mark.asyncio
    async def test_empty_summary_finalize_no_longer_enqueues(self, monkeypatch):
        """普通 chat turn（无任务完成摘要）的 finalize 收尾不再 enqueue——
        写账已上移到 persist/快交互出口，避免并发双写竞争。"""
        probe = _patch_lane_enqueue(monkeypatch)

        fake_self = MagicMock()
        fake_self._build_task_completion_memory_summary = AsyncMock(return_value="")

        await ChatOrchestrator._write_turn_end_episodic_memory(
            fake_self,
            active_db=MagicMock(),
            user_id=str(uuid4()),
            session_id=str(uuid4()),
            request_id="req-x",
            user_message=B1_ONBOARDING_MESSAGE,
            assistant_message="回复",
            event_kind="task_completed",
        )

        assert not probe.called, "finalize 空摘要分支不得再 enqueue（单一触发点纪律）"


# ============ 链路级：WS 收尾携带原文 → declared facts 真实入库 ============


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


async def _lane_episodic_rows(db_session, user_id) -> list[EpisodicMemory]:
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


class TestWsTurnChainWritesDeclaredFacts:
    """链路级红测试：模拟 gRPC 流式轮次收尾（persist 钩子捕获到的调用形状）
    → 同一捕获面 process_chat_turn → declared facts 入库（含 exam due_at）。"""

    @pytest.mark.asyncio
    async def test_persist_hook_shape_writes_three_declared_facts(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        session_id = uuid4()

        captured: dict = {}

        def _capture_enqueue(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_chat_turn", _capture_enqueue)
        _stub_persist_session(monkeypatch)

        orchestrator = persistence_orchestrator_fixture()
        await orchestrator._persist_assistant_message(
            active_db=MagicMock(),
            user_id=str(user.id),
            session_id=str(session_id),
            full_response="我先按【离散数学】冲刺来处理。",
            user_message=B1_ONBOARDING_MESSAGE,
        )

        assert captured, "persist 收尾必须触发捕获面"
        # 用捕获到的真实调用形状驱动同一捕获面（替代后台 task 的确定性等价执行）。
        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=captured["user_id"],
            session_id=captured["session_id"],
            user_message=captured["user_message"],
            assistant_message=captured["assistant_message"],
            user_message_id=captured["user_message_id"],
            assistant_message_id=captured.get("assistant_message_id"),
        )

        rows = await _lane_episodic_rows(db_session, user.id)
        assert len(rows) >= 3, f"B1 同句经 WS 收尾形状必须写 ≥3 条 declared facts，实际 {len(rows)}"
        exam_rows = [row for row in rows if "期末考试" in (row.summary or "")]
        assert exam_rows, "考试句必须入库"
        assert exam_rows[0].due_at is not None, "exam commitment 必须带 due_at"
        assert exam_rows[0].due_at == datetime(2026, 9, 28, 18, 0, 0), "due_at=7 天后 18:00（与 REST 臂一致）"
        assert any("薄弱" in (row.summary or "") for row in rows), "弱点句必须入库"
        assert any("165" in (row.summary or "") for row in rows), "时间约束句必须入库"

    @pytest.mark.asyncio
    async def test_fast_interaction_capture_shape_writes_declared_facts(self, db_session, monkeypatch):
        """短路轮形状：澄清快交互携带的用户原文经同一捕获面真实入库。"""
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        session_id = uuid4()
        request_id = f"req-{uuid4().hex[:8]}"

        captured: dict = {}

        def _capture_enqueue(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_chat_turn", _capture_enqueue)

        orchestrator = MinimalValidationOrchestrator()
        await orchestrator._emit_fast_interaction(
            stream_callback=AsyncMock(),
            text="您期望本次期末考试达到多少分？",
            details="clarify",
            turn_capture={
                "user_id": str(user.id),
                "session_id": str(session_id),
                "user_message": B1_ONBOARDING_MESSAGE,
                "request_id": request_id,
            },
        )

        service = MemoryInferredWriteLaneService(db_session)
        await service.process_chat_turn(
            user_id=captured["user_id"],
            session_id=captured["session_id"],
            user_message=captured["user_message"],
            assistant_message=captured["assistant_message"],
            user_message_id=captured["user_message_id"],
            assistant_message_id=None,
        )

        rows = await _lane_episodic_rows(db_session, user.id)
        assert len(rows) >= 3, f"短路轮（B1 同句）必须写 ≥3 条 declared facts，实际 {len(rows)}"
        assert all(str(row.id) for row in rows)


def persistence_orchestrator_fixture() -> MinimalPersistenceOrchestrator:
    return MinimalPersistenceOrchestrator()
