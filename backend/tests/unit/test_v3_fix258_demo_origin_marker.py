"""V3-FIX-258（wt533 B-02 审计 F1）：demo 产出落库 origin 标记 + 记忆推断读侧过滤。

缺陷（台账 258）：demo 激活（settings.DEMO_MODE 显式或 API key 缺失自动激活，
llm_service ``:411-413/:458-460``）后，3 条脚本回复 DEMO_MOCK_RESPONSES（含捏造
学习分析如「掌握度降至 65%」）与通用演示回复经 ChatOrchestrator / REST 照常落库
——ChatMessage 无持久标记（唯一标记是瞬态 OTel span ``llm.demo_mode``），
model_name 落「配置了但从未运行的模型名」；且 ``_persist_assistant_message`` 把
同一 mock 文本交 MemoryInferredWriteLaneService——假分析喂记忆推断产伪事实记忆。

修法（数据级 origin 标记）：ChatMessage.origin（llm|demo，server_default 'llm'）；
写侧两个 choke point（orchestrator ``_persist_assistant_message``、REST
``save_chat_message``）按 ``llm_service.demo_mode`` 置标记（demo_mode 置位时
llm_service 一切回复均为 provider 调用前的脚本短路，故落库时刻的 demo_mode 是
该行文本来源的充分判据）；记忆推断 ``process_chat_turn`` 入口单点过滤——demo 轮
整轮跳过（台账裁决「demo 轮不进记忆 lane」），全部生产调用方（persist 收尾、
快交互 turn_capture、REST save_chat_message、enqueue_from_session DB 回捞）都汇入
该入口。

红→绿实录口径：①修前落库行无 origin 可查（MessageOrigin ImportError /
AttributeError）；②修前 demo 轮带 mock 文本进记忆推断真实写出 episodic 行。
正控用例（非 demo 轮照常写出）修前后恒绿，钉「过滤不得误伤真实轮」。

注：MessageOrigin 在测试体内延迟导入——修前 app.models.chat 尚无该枚举，
模块级导入会让整文件收集失败、掩盖逐测红绿实录。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.services import memory_inferred_write_lane as lane_module
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.llm_service import DEMO_MOCK_RESPONSES, llm_service, llm_service_impl
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

# B1 onboarding 原句形状（带明示备考事实，正控下必产 ≥3 条 declared facts）。
_DECLARED_FACT_USER_MESSAGE = "我要开始备考：离散数学期末考试在 7 天后。我每天只能投入 165 分钟，" "最薄弱的章是图论。"


def _demo_assistant_text() -> str:
    """取一条真实演示脚本回复（含捏造学习分析的 DEMO_MOCK_RESPONSES 值）。"""
    return next(iter(DEMO_MOCK_RESPONSES.values()))


def _set_demo_mode(monkeypatch, enabled: bool) -> None:
    """翻内层 LLMService.demo_mode（生产中唯一翻转点），经 LLMSecurityWrapper
    的 V3-FIX-258 只读转发面被读侧判据观察到（fail-closed 契约内元属性）。"""
    monkeypatch.setattr(llm_service_impl, "demo_mode", enabled)
    # 转发面回归：wrapper 读侧必须与内层一致（wrapper 自身被 patch 污染时此断言会暴露）。
    assert bool(getattr(llm_service, "demo_mode", False)) is enabled


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


async def _inferred_rows(db_session, user_id) -> list[EpisodicMemory]:
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


# ============ 写侧 choke point ①：orchestrator _persist_assistant_message ============


class _PersistOrchestrator(PersistenceLayerMixin):
    def __init__(self):
        self.redis = MagicMock()

    # 注意：显式 staticmethod 转发（NBP-1 旧套件直接类体赋值在
    # _coerce_session_uuid 转 staticmethod 后已 stale，勿复制该模式）。
    @staticmethod
    def _coerce_session_uuid(session_id):
        return ChatOrchestrator._coerce_session_uuid(session_id)


def _stub_persist_session(monkeypatch) -> list[ChatMessage]:
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
    return holder


def _patch_lane_enqueues(monkeypatch) -> tuple[MagicMock, MagicMock]:
    chat_turn_probe = MagicMock(return_value=None)
    session_probe = MagicMock(return_value=None)
    monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_chat_turn", chat_turn_probe)
    monkeypatch.setattr(MemoryInferredWriteLaneService, "enqueue_from_session", session_probe)
    return chat_turn_probe, session_probe


class TestPersistAssistantMessageOrigin:
    @pytest.mark.asyncio
    async def test_demo_turn_persists_origin_demo(self, monkeypatch):
        """红→绿：demo 轮落库行必须带 origin=demo 持久标记（修前无 origin 可查）。"""
        _set_demo_mode(monkeypatch, True)
        _patch_lane_enqueues(monkeypatch)
        holder = _stub_persist_session(monkeypatch)
        from app.models.chat import MessageOrigin

        orchestrator = _PersistOrchestrator()
        await orchestrator._persist_assistant_message(
            active_db=MagicMock(),
            user_id=str(uuid4()),
            session_id=str(uuid4()),
            full_response=_demo_assistant_text(),
            user_message=_DECLARED_FACT_USER_MESSAGE,
        )

        assert holder, "demo 轮 assistant 行必须照常落库（标记而非丢弃）"
        assert (
            holder[0].origin == MessageOrigin.DEMO
        ), "demo 脚本回复落库必须带 origin=demo（此前唯一标记是瞬态 OTel span）"

    @pytest.mark.asyncio
    async def test_real_turn_persists_origin_llm(self, monkeypatch):
        """正控：真实模型轮落库 origin=llm（标记不得误伤常规管线）。"""
        _set_demo_mode(monkeypatch, False)
        _patch_lane_enqueues(monkeypatch)
        holder = _stub_persist_session(monkeypatch)
        from app.models.chat import MessageOrigin

        orchestrator = _PersistOrchestrator()
        await orchestrator._persist_assistant_message(
            active_db=MagicMock(),
            user_id=str(uuid4()),
            session_id=str(uuid4()),
            full_response="这是一个真实模型回复。",
            user_message=_DECLARED_FACT_USER_MESSAGE,
        )

        assert holder and holder[0].origin == MessageOrigin.LLM


# ============ 写侧 choke point ②：REST api/v1/chat.py save_chat_message ============


class TestRestSaveChatMessageOrigin:
    @pytest.mark.asyncio
    async def test_demo_turn_rest_assistant_row_marked_user_row_default(self, db_session, monkeypatch):
        """红→绿：REST 落库 assistant 行带 origin=demo；user 行保持默认（demo
        轮的用户原文是真实输入，非脚本产出）。"""
        from app.api.v1.chat import save_chat_message
        from app.models.chat import MessageOrigin

        _set_demo_mode(monkeypatch, True)
        user = await _create_user(db_session)
        session_id = uuid4()

        await save_chat_message(
            db=db_session,
            user_id=user.id,
            session_id=session_id,
            user_message=_DECLARED_FACT_USER_MESSAGE,
            assistant_message=_demo_assistant_text(),
            tool_results=[],
        )

        rows = (
            (
                await db_session.execute(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user.id,
                        ChatMessage.session_id == session_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        by_role = {row.role: row for row in rows}
        assert by_role[MessageRole.ASSISTANT].origin == MessageOrigin.DEMO
        assert by_role[MessageRole.USER].origin == MessageOrigin.LLM

    @pytest.mark.asyncio
    async def test_real_turn_rest_rows_default_llm(self, db_session, monkeypatch):
        """正控：REST 真实轮 assistant 行 origin=llm。"""
        from app.api.v1.chat import save_chat_message
        from app.models.chat import MessageOrigin

        _set_demo_mode(monkeypatch, False)
        user = await _create_user(db_session)
        session_id = uuid4()

        await save_chat_message(
            db=db_session,
            user_id=user.id,
            session_id=session_id,
            user_message=_DECLARED_FACT_USER_MESSAGE,
            assistant_message="真实回复。",
            tool_results=[],
        )

        rows = (
            (
                await db_session.execute(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user.id,
                        ChatMessage.session_id == session_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        by_role = {row.role: row for row in rows}
        assert by_role[MessageRole.ASSISTANT].origin == MessageOrigin.LLM


# ============ 读侧：记忆推断入口 demo 轮整轮跳过 ============


class TestMemoryLaneDemoTurnFilter:
    @pytest.mark.asyncio
    async def test_demo_turn_writes_zero_memory_rows(self, db_session, monkeypatch):
        """红→绿：demo 轮（assistant 文本=演示脚本）整轮不进记忆推断——
        修前实录：同一轮经 process_chat_turn 真实写出 episodic 行（假分析
        喂推断的污染链实证）。"""
        _set_demo_mode(monkeypatch, True)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        service = MemoryInferredWriteLaneService(db_session)
        result = await service.process_chat_turn(
            user_id=user.id,
            session_id=uuid4(),
            user_message=_DECLARED_FACT_USER_MESSAGE,
            assistant_message=_demo_assistant_text(),
            user_message_id=f"req-{uuid4().hex[:8]}",
            assistant_message_id=None,
        )

        assert result is None, "demo 轮必须整轮跳过（不产候选不入库）"
        rows = await _inferred_rows(db_session, user.id)
        assert rows == [], f"demo 轮不得写任何推断记忆行，实际 {len(rows)} 行"

    @pytest.mark.asyncio
    async def test_non_demo_turn_still_writes_memory_rows(self, db_session, monkeypatch):
        """正控（修前后恒绿）：真实轮照常写出 declared facts——过滤不得误伤。"""
        _set_demo_mode(monkeypatch, False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
        monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
        monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))

        user = await _create_user(db_session)
        service = MemoryInferredWriteLaneService(db_session)
        result = await service.process_chat_turn(
            user_id=user.id,
            session_id=uuid4(),
            user_message=_DECLARED_FACT_USER_MESSAGE,
            assistant_message="真实模型回复。",
            user_message_id=f"req-{uuid4().hex[:8]}",
            assistant_message_id=None,
        )

        rows = await _inferred_rows(db_session, user.id)
        assert len(rows) >= 1, "非 demo 轮的明示事实必须照常入库（过滤不得误伤）"
        assert any("165" in (row.summary or "") for row in rows), "时间约束句必须入库"
        assert result is not None or rows, "正控轮必须有产出"

    @pytest.mark.asyncio
    async def test_demo_mode_ignores_flag_change_midflight_is_out_of_scope(self, monkeypatch):
        """口径钉子：guard 读的是 process_chat_turn 时刻的 llm_service.demo_mode
        （演示模式翻转仅发生在显式 switch_specific_model，分钟级窗口内的
        mid-turn 翻转误标是已记录的可接受边缘，不做逐轮快照接线）。"""
        from app.services.llm_service import llm_service as svc

        _set_demo_mode(monkeypatch, True)
        assert bool(getattr(svc, "demo_mode", False)) is True
        _set_demo_mode(monkeypatch, False)
        assert bool(getattr(svc, "demo_mode", False)) is False
        # 防过修守卫：guard 实现必须读 llm_service 单例，而非新造全局状态。
        source = __import__("inspect").getsource(lane_module.MemoryInferredWriteLaneService.process_chat_turn)
        assert "demo_mode" in source, "process_chat_turn 必须含 demo_mode 判据"
