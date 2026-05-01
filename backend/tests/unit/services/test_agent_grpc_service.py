from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import grpc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "app" / "gen" / "agent" / "v1"))

from app.core.metrics import SESSION_ID_FALLBACK_TOTAL
from app.gen.agent.v1 import agent_service_pb2
from app.services.agent_grpc_service import AgentServiceImpl


class _DummySession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _DummySessionContext:
    def __init__(self, session: _DummySession) -> None:
        self._session = session

    async def __aenter__(self) -> _DummySession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _DummySessionFactory:
    def __init__(self) -> None:
        self.last_session: _DummySession | None = None

    def __call__(self) -> _DummySessionContext:
        session = _DummySession()
        self.last_session = session
        return _DummySessionContext(session)


class _FakeContext:
    def __init__(self, metadata: list[tuple[str, str]] | None = None) -> None:
        self._metadata = metadata or []
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    def invocation_metadata(self):
        return self._metadata

    def set_code(self, code: grpc.StatusCode) -> None:
        self.code = code

    def set_details(self, details: str) -> None:
        self.details = details


class _BrokenMetadataContext(_FakeContext):
    def invocation_metadata(self):
        raise RuntimeError("metadata unavailable")


class _RaisingOrchestrator:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.redis = None

    async def process_stream(self, *args, **kwargs):
        if False:
            yield None
        raise self.exc


class _StreamingOrchestrator:
    def __init__(self, responses: list[agent_service_pb2.ChatResponse]) -> None:
        self.responses = responses
        self.redis = None

    async def process_stream(self, *args, **kwargs):
        for response in self.responses:
            yield response


@pytest.mark.asyncio
async def test_stream_chat_errors_set_grpc_internal_and_error_finish_reason():
    session_factory = _DummySessionFactory()
    service = AgentServiceImpl(
        orchestrator=_RaisingOrchestrator(RuntimeError("boom")),
        db_session_factory=session_factory,
    )
    context = _FakeContext()
    request = agent_service_pb2.ChatRequest(
        user_id=str(uuid.uuid4()),
        session_id="session-1",
        request_id="req-1",
        message="hello",
    )

    responses = [response async for response in service.StreamChat(request, context)]

    assert len(responses) == 1
    assert responses[0].finish_reason == agent_service_pb2.ERROR
    assert responses[0].error.error_code == agent_service_pb2.ERROR_CODE_INTERNAL
    assert context.code == grpc.StatusCode.INTERNAL
    assert context.details == "系统暂时不可用，请稍后重试。"
    assert session_factory.last_session is not None
    assert session_factory.last_session.rolled_back is True


@pytest.mark.asyncio
async def test_stream_chat_timeout_sets_deadline_exceeded():
    session_factory = _DummySessionFactory()
    service = AgentServiceImpl(
        orchestrator=_RaisingOrchestrator(asyncio.TimeoutError()),
        db_session_factory=session_factory,
    )
    context = _FakeContext()
    request = agent_service_pb2.ChatRequest(
        user_id=str(uuid.uuid4()),
        session_id="session-2",
        request_id="req-2",
        message="hello",
    )

    responses = [response async for response in service.StreamChat(request, context)]

    assert len(responses) == 1
    assert responses[0].finish_reason == agent_service_pb2.ERROR
    assert responses[0].error.error_code == agent_service_pb2.ERROR_CODE_TIMEOUT
    assert context.code == grpc.StatusCode.DEADLINE_EXCEEDED
    assert context.details == "系统处理超时，请稍后重试。"


@pytest.mark.asyncio
async def test_stream_chat_error_path_uses_safe_defaults_before_metadata_load():
    session_factory = _DummySessionFactory()
    service = AgentServiceImpl(
        orchestrator=_RaisingOrchestrator(RuntimeError("should not be reached")),
        db_session_factory=session_factory,
    )
    context = _BrokenMetadataContext()
    request = agent_service_pb2.ChatRequest(
        user_id=str(uuid.uuid4()),
        session_id="session-3",
        request_id="req-3",
        message="hello",
    )

    responses = [response async for response in service.StreamChat(request, context)]

    assert len(responses) == 1
    assert responses[0].trace_id == "req-3"
    assert responses[0].workflow_id == "standard_chat"
    assert responses[0].prompt_version == "v1"
    assert responses[0].finish_reason == agent_service_pb2.ERROR
    assert context.code == grpc.StatusCode.INTERNAL


@pytest.mark.asyncio
async def test_stream_chat_reuses_request_session_when_response_omits_session_id():
    session_factory = _DummySessionFactory()
    service = AgentServiceImpl(
        orchestrator=_StreamingOrchestrator(
            [
                agent_service_pb2.ChatResponse(
                    response_id="response-1",
                    delta="hello",
                )
            ]
        ),
        db_session_factory=session_factory,
    )
    request = agent_service_pb2.ChatRequest(
        user_id=str(uuid.uuid4()),
        session_id="session-propagated",
        request_id="req-propagated",
        message="hello",
    )

    responses = [response async for response in service.StreamChat(request, _FakeContext())]

    assert [response.session_id for response in responses] == ["session-propagated"]


@pytest.mark.asyncio
async def test_stream_chat_empty_request_session_generates_single_fallback_and_metric():
    metric = SESSION_ID_FALLBACK_TOTAL.labels(source="grpc_stream_chat")
    before = metric._value.get()
    session_factory = _DummySessionFactory()
    service = AgentServiceImpl(
        orchestrator=_StreamingOrchestrator(
            [
                agent_service_pb2.ChatResponse(response_id="response-1", delta="hello"),
                agent_service_pb2.ChatResponse(response_id="response-2", full_text="done"),
            ]
        ),
        db_session_factory=session_factory,
    )
    request = agent_service_pb2.ChatRequest(
        user_id=str(uuid.uuid4()),
        request_id="req-fallback",
        message="hello",
    )

    responses = [response async for response in service.StreamChat(request, _FakeContext())]

    assert len(responses) == 2
    assert responses[0].session_id
    assert responses[0].session_id == responses[1].session_id
    assert request.session_id == responses[0].session_id
    assert uuid.UUID(responses[0].session_id)
    assert metric._value.get() == before + 1
