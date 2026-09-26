"""
Unit tests for PersistenceLayerMixin.

Tests the persistence and side-effect helpers for the orchestrator.
"""
from __future__ import annotations

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
