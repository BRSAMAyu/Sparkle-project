from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.services.agent_grpc_service import AgentServiceImpl


@dataclass
class _FeedbackResult:
    success: bool
    already_recorded: bool
    response_id: str


class _DummyContext:
    def __init__(self, metadata: list[tuple[str, str]] | None = None):
        self._metadata = metadata or []
        self.code = None
        self.details = ""

    def invocation_metadata(self):
        return self._metadata

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


class _DummySessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ObservabilityRecorder:
    def __init__(self):
        self.calls: list[dict] = []

    async def log_user_feedback_bound(self, **kwargs):
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_submit_feedback_parses_selected_experts_json(monkeypatch):
    response_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    async def _fake_submit_feedback(self, **kwargs):
        return _FeedbackResult(success=True, already_recorded=False, response_id=kwargs["response_id"])

    monkeypatch.setattr(
        "app.services.response_feedback_service.ResponseFeedbackService.submit_feedback",
        _fake_submit_feedback,
    )

    observability = _ObservabilityRecorder()
    orchestrator = type("_O", (), {"redis": None, "observability": observability})()
    service = AgentServiceImpl(orchestrator=orchestrator, db_session_factory=lambda: _DummySessionContext())

    request = agent_service_pb2.ResponseFeedbackRequest(
        user_id=user_id,
        response_id=response_id,
        feedback_type=agent_service_pb2.FEEDBACK_TYPE_UP,
        workflow_id="expert_auto_workflow",
        meta={
            "selected_experts": '["deep_analyst", "code_agent"]',
            "policy_id": "expert_strategy_v2",
        },
    )

    context = _DummyContext(metadata=[("user-id", user_id)])
    response = await service.SubmitResponseFeedback(request, context)

    assert response.success is True
    assert observability.calls
    assert observability.calls[0]["selected_experts"] == ["deep_analyst", "code_agent"]
    assert observability.calls[0]["policy_id"] == "expert_strategy_v2"
