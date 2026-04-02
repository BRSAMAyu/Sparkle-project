from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.execution_engine import ExecutionEngineMixin


class _Adapter:
    async def execute_mode_workflow(self, **kwargs):
        yield agent_service_pb2.ChatResponse(delta="团队模式已执行")


class _Observability:
    async def log_collaboration_start(self, **kwargs):
        return None

    async def log_collaboration_end(self, **kwargs):
        return None


class _Engine(ExecutionEngineMixin):
    def __init__(self):
        self.multi_agent_adapter = _Adapter()
        self.observability = _Observability()

    async def _update_state(self, *args, **kwargs):
        return None

    async def _persist_assistant_message(self, **kwargs):
        return None

    async def _record_decision(self, **kwargs):
        return None

    def _extract_llm_profile_meta(self, user_context_payload):
        return {}


@pytest.mark.asyncio
async def test_handle_multi_agent_mode_preserves_stable_workflow_id(monkeypatch):
    engine = _Engine()
    monkeypatch.setattr("app.orchestration.execution_engine.settings.ENABLE_MODE_WORKFLOW_V2", True)

    responses = []
    async for response in engine._handle_multi_agent_mode(
        chat_mode='team::{"agents":["deep_analyst","exam_oracle"]}',
        user_message="一起分析这个问题",
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        response_id=str(uuid4()),
        request_id=str(uuid4()),
        trace_id=str(uuid4()),
        start_time=0.0,
        user_context_payload=None,
        conversation_context=None,
        plan_context=None,
        active_db=None,
        workflow_id="expert_team_workflow",
        prompt_version="v1",
        stream_callback=lambda _: None,
        result_holder={},
    ):
        responses.append(response)

    assert responses
    assert all(response.workflow_id == "expert_team_workflow" for response in responses)
    assert all('team::' not in response.workflow_id for response in responses)
