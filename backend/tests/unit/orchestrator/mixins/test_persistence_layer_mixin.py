"""
Unit tests for PersistenceLayerMixin.

Tests the persistence and side-effect helpers for the orchestrator.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uuid

from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.orchestration.orchestrator import ChatOrchestrator


# Create a minimal class that includes the mixin
class MinimalOrchestrator(PersistenceLayerMixin):
    """Minimal orchestrator with PersistenceLayerMixin for testing."""
    def __init__(self):
        self.redis = MagicMock()

    # 对齐真实契约：ChatOrchestrator._coerce_session_uuid 是 @staticmethod（对齐
    # ContextBuilderMixin 超签）。类访问后裸赋值会退化为普通函数、实例调用多绑
    # self——包 staticmethod 保持原语义。
    _coerce_session_uuid = staticmethod(ChatOrchestrator._coerce_session_uuid)


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


@pytest.mark.asyncio
async def test_persist_assistant_message_returns_early_for_no_db(orchestrator):
    """Test _persist_assistant_message returns early when no db session."""
    # Should not raise exception
    await orchestrator._persist_assistant_message(
        active_db=None,
        user_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        full_response="Test response",
    )


@pytest.mark.asyncio
async def test_persist_assistant_message_returns_early_for_empty_response(orchestrator):
    """Test _persist_assistant_message returns early for empty response."""
    mock_db = MagicMock()

    await orchestrator._persist_assistant_message(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        full_response="",
    )

    # Should not add any message
    assert not mock_db.add.called


@pytest.mark.asyncio
async def test_persist_assistant_message_saves_to_database(orchestrator, monkeypatch):
    """9050650f 语义：assistant 消息经独立 session 自持提交（共享流 session 可能
    被本轮更早的异常毒化，聊天持久化不能陪葬）；断言独立 session 的
    add/flush/commit 而非共享 session。"""
    mock_db = MagicMock()
    mock_db.is_active = True
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    persist_session = MagicMock()
    persist_session.add = MagicMock()
    persist_session.flush = AsyncMock()
    persist_session.commit = AsyncMock()

    class _SessionCtx:
        async def __aenter__(self):
            return persist_session

        async def __aexit__(self, *args):
            return False

    import app.db.session as dbs

    monkeypatch.setattr(dbs, "AsyncSessionLocal", lambda: _SessionCtx())

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    full_response = "This is a test response"

    await orchestrator._persist_assistant_message(
        active_db=mock_db,
        user_id=user_id,
        session_id=session_id,
        full_response=full_response,
    )

    # 独立 session 收到消息并自持提交；共享 session 不再被写入
    assert persist_session.add.called
    assert persist_session.flush.called
    assert persist_session.commit.called
    assert not mock_db.add.called

    # Verify the message object
    added_message = persist_session.add.call_args[0][0]
    assert added_message.content == full_response
    assert str(added_message.user_id) == user_id


@pytest.mark.asyncio
async def test_record_decision_returns_early_for_no_db(orchestrator):
    """Test _record_decision returns early when no db session."""
    # Should not raise exception
    await orchestrator._record_decision(
        active_db=None,
        user_id=str(uuid.uuid4()),
        user_context_payload=None,
        llm_profile_meta={},
        full_response="Test",
    )


@pytest.mark.asyncio
async def test_record_decision_handles_inactive_db(orchestrator):
    """Test _record_decision handles inactive database session."""
    mock_db = MagicMock()
    mock_db.is_active = False

    # Should not raise exception
    await orchestrator._record_decision(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        user_context_payload=None,
        llm_profile_meta={},
        full_response="Test",
    )


@pytest.mark.asyncio
async def test_load_recent_execution_feedback_with_no_db(orchestrator):
    """Test _load_recent_execution_feedback returns None when no db."""
    result = await orchestrator._load_recent_execution_feedback(
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_load_recent_execution_feedback_returns_structure(orchestrator):
    """Test _load_recent_execution_feedback returns None without a plan id."""
    mock_db = MagicMock()

    result = await orchestrator._load_recent_execution_feedback(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        plan_id=None,
    )

    assert result is None


def test_coerce_session_uuid_with_uuid_string(orchestrator):
    """Test _coerce_session_uuid handles UUID strings."""
    test_uuid = uuid.uuid4()
    result = orchestrator._coerce_session_uuid(str(test_uuid))

    assert result == test_uuid


def test_coerce_session_uuid_with_uuid_object(orchestrator):
    """Test _coerce_session_uuid handles UUID objects."""
    test_uuid = uuid.uuid4()
    result = orchestrator._coerce_session_uuid(test_uuid)

    assert result == test_uuid


def test_coerce_session_uuid_with_invalid_string(orchestrator):
    """Test _coerce_session_uuid handles invalid UUID strings."""
    # Should not raise exception
    result = orchestrator._coerce_session_uuid("not-a-uuid")

    # Should return a valid UUID
    assert isinstance(result, uuid.UUID)


# ---------------------------------------------------------------------------
# V3-FIX-264 点位2（wt543）：_notify_pending_milestone_proposals metadata 红转绿守卫
# ---------------------------------------------------------------------------


def _milestone_action(**preview_overrides) -> dict:
    """milestone_task_proposal 待确认动作（preview_data 宽松形状）。

    缺 proposal_id/milestone_id/reasoning/proposed_tasks——pending_actions_store
    的 preview_data 是任意 dict（生产方契约外形状），正是修前 protobuf 赋值炸点。
    """
    preview: dict = {"suggested_count": 4, "plan_id": "plan-9"}
    preview.update(preview_overrides)
    return {
        "tool_name": "milestone_task_proposal",
        "action_id": "act-123",
        "preview_data": preview,
    }


async def test_notify_milestone_proposal_sends_protobuf_safe_metadata(orchestrator, monkeypatch):
    """metadata（proto map<string,string>）缺键 None / int 直传必须不再炸通知。

    修前实录（台账 V3-FIX-263）：ChatResponse(metadata={...}) 构造期 TypeError
    （None/int 不是 str），被方法体外层 `except Exception` 吞成 warning——
    stream_callback 从未被调用，里程碑通知静默丢失。
    """
    action = _milestone_action()
    monkeypatch.setattr(
        "app.core.pending_actions.pending_actions_store.get_all_by_user",
        AsyncMock(return_value=[action]),
    )
    callback = AsyncMock()

    await orchestrator._notify_pending_milestone_proposals("user-1", callback)

    callback.assert_awaited_once()
    resp = callback.await_args.args[0]
    md = dict(resp.metadata)
    assert md["widget_event"] == "milestone_proposal"
    assert md["proposal_id"] == ""  # 缺键 → 规范缺席值，通知不吞
    assert md["action_id"] == "act-123"
    assert md["plan_id"] == "plan-9"
    assert md["milestone_id"] == ""
    assert md["task_count"] == "4"  # int → str
    assert md["reasoning"] == ""
    assert json.loads(md["tasks"]) == []


async def test_notify_milestone_proposal_full_preview_keys_roundtrip(orchestrator, monkeypatch):
    """preview_data 键齐全（含 int suggested_count）时全链路可达且值保持。"""
    action = _milestone_action(
        proposal_id="prop-1",
        milestone_id="ms-2",
        reasoning="因为连续达标",
        proposed_tasks=[{"title": "任务A"}, {"title": "任务B"}],
    )
    monkeypatch.setattr(
        "app.core.pending_actions.pending_actions_store.get_all_by_user",
        AsyncMock(return_value=[action]),
    )
    callback = AsyncMock()

    await orchestrator._notify_pending_milestone_proposals("user-2", callback)

    callback.assert_awaited_once()
    resp = callback.await_args.args[0]
    md = dict(resp.metadata)
    assert md["proposal_id"] == "prop-1"
    assert md["milestone_id"] == "ms-2"
    assert md["task_count"] == "4"
    assert md["reasoning"] == "因为连续达标"
    assert json.loads(md["tasks"]) == [{"title": "任务A"}, {"title": "任务B"}]
    assert "4 个新任务" in resp.delta


async def test_notify_milestone_proposal_none_values_do_not_drop_notification(orchestrator, monkeypatch):
    """preview_data 值显式 None（如 plan_id=None）时通知仍发出，缺省空串。"""
    action = _milestone_action(
        suggested_count=None, plan_id=None, proposal_id=None, reasoning=None,
    )
    monkeypatch.setattr(
        "app.core.pending_actions.pending_actions_store.get_all_by_user",
        AsyncMock(return_value=[action]),
    )
    callback = AsyncMock()

    await orchestrator._notify_pending_milestone_proposals("user-3", callback)

    callback.assert_awaited_once()
    md = dict(callback.await_args.args[0].metadata)
    assert md["task_count"] == "0"
    assert md["plan_id"] == ""
    assert md["proposal_id"] == ""
    assert md["reasoning"] == ""
