from __future__ import annotations

import importlib
import sys
import types
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.protobuf.struct_pb2 import Struct

from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.service import AuroraRuntimeTurnPlan
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.schemas import ExecutablePlan, RouteDecision, ToolCallSpec
from app.orchestration.statechart_engine import WorkflowState

STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"


class _RunLedgerStub:
    def __init__(self, *args, **kwargs):
        pass

    async def record_event(self, *args, **kwargs) -> None:
        return None

    def to_metadata_payload(self) -> dict[str, object]:
        return {}


class _ChatSignalCollectorStub:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def collect_signals(self, *args, **kwargs) -> None:
        return None


class _MemoryRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl
        return True

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def eval(self, script: str, numkeys: int, key: str, *args):
        if "del" in script:
            request_id = args[0]
            if self.values.get(key) == request_id:
                self.values.pop(key, None)
                self.ttls.pop(key, None)
                return 1
            return 0

        request_id = args[0]
        ttl = int(args[1])
        if self.values.get(key) == request_id:
            self.ttls[key] = ttl
            return 1
        return 0

    async def delete(self, *keys: str):
        removed = 0
        for key in keys:
            if key in self.values:
                removed += 1
                self.values.pop(key, None)
                self.ttls.pop(key, None)
        return removed

    async def keys(self, pattern: str):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.values if key.startswith(prefix)]

    async def ttl(self, key: str):
        return self.ttls.get(key, -1)

    async def expire(self, key: str, ttl: int):
        if key in self.values:
            self.ttls[key] = ttl
            return True
        return False

    async def incrby(self, key: str, value: int):
        current = int(self.values.get(key, "0"))
        current += value
        self.values[key] = str(current)
        return current

    async def ping(self):
        return True


async def _passthrough_route(route_decision: RouteDecision, **kwargs) -> RouteDecision:
    return route_decision


async def _emit_noop(*args, **kwargs) -> None:
    return None


def _make_struct(data: dict[str, object]) -> Struct:
    message = Struct()
    message.update(data)
    return message


def _make_request(*, message: str = "帮我整理今天的学习重点") -> agent_service_pb2.ChatRequest:
    return agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
        user_id=str(uuid.uuid4()),
        message=message,
    )


async def _collect(
    orchestrator,
    request: agent_service_pb2.ChatRequest,
) -> list[agent_service_pb2.ChatResponse]:
    return [response async for response in orchestrator.process_stream(request)]


async def _drain_queue(
    queue,
) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
    while not queue.empty():
        item = await queue.get()
        yield item
        queue.task_done()


def _install_import_stubs() -> None:
    if "app.agents.standard_workflow" not in sys.modules:
        standard_workflow = types.ModuleType("app.agents.standard_workflow")
        standard_workflow.create_standard_chat_graph = lambda: MagicMock()
        sys.modules["app.agents.standard_workflow"] = standard_workflow

    if "app.services.llm_service" not in sys.modules:
        llm_module = types.ModuleType("app.services.llm_service")

        class _LLMServiceStub:
            async def continue_with_tool_results(self, *args, **kwargs):
                return types.SimpleNamespace(content="tool continuation")

        llm_module.LLMService = _LLMServiceStub
        llm_module.llm_service = _LLMServiceStub()
        llm_module.get_llm_service = lambda *args, **kwargs: llm_module.llm_service
        llm_module.get_configured_llm_service = lambda *args, **kwargs: llm_module.llm_service
        llm_module.get_configured_llm_service_for_tier = lambda *args, **kwargs: llm_module.llm_service
        llm_module.get_llm_service_for_specific_model = lambda *args, **kwargs: llm_module.llm_service
        llm_module.get_llm_service_for_task = lambda *args, **kwargs: llm_module.llm_service
        sys.modules["app.services.llm_service"] = llm_module

    if "app.orchestration.lang_graph_planner" not in sys.modules:
        planner_module = types.ModuleType("app.orchestration.lang_graph_planner")

        class _LangGraphPlannerStub:
            def __init__(self, redis_client):
                self.redis_client = redis_client
                self.circuit_breaker = None

            async def plan(self, *args, **kwargs):
                return types.SimpleNamespace(
                    plan_id="stub-plan",
                    tool_calls=[],
                    confidence=0.5,
                    rationale="stub",
                    collaboration_mode="single",
                    agents_involved=[],
                )

            def build_fallback_plan(self, *args, **kwargs):
                return types.SimpleNamespace(
                    plan_id="fallback-plan",
                    tool_calls=[],
                    confidence=0.4,
                    rationale="fallback",
                    collaboration_mode="single",
                    agents_involved=[],
                )

            @staticmethod
            def get_plan_summary(plan) -> str:
                return str(getattr(plan, "plan_id", "stub-plan"))

            def pop_rendered_plan_artifact(self, session_id=None):
                del session_id
                return None

        planner_module.LangGraphPlanner = _LangGraphPlannerStub
        sys.modules["app.orchestration.lang_graph_planner"] = planner_module

    if "app.orchestration.grounding_validator" not in sys.modules:
        validator_module = types.ModuleType("app.orchestration.grounding_validator")

        class _GroundingValidatorStub:
            def __init__(self, redis_client):
                self.redis_client = redis_client

            def refresh_allowlist(self):
                return None

            async def validate_plan(self, *args, **kwargs):
                return types.SimpleNamespace(is_valid=True, warnings=[])

            async def preflight_check(self, *args, **kwargs):
                return {"is_ready": True, "blocked_by": []}

        validator_module.GroundingValidator = _GroundingValidatorStub
        sys.modules["app.orchestration.grounding_validator"] = validator_module

    if "app.orchestration.state_snapshot" not in sys.modules:
        snapshot_module = types.ModuleType("app.orchestration.state_snapshot")

        class _StateSnapshotManagerStub:
            def __init__(self, redis_client):
                self.redis_client = redis_client

            async def create_snapshot(self, *args, **kwargs):
                return types.SimpleNamespace(snapshot_id="snapshot-1")

        snapshot_module.StateSnapshotManager = _StateSnapshotManagerStub
        sys.modules["app.orchestration.state_snapshot"] = snapshot_module

    if "app.orchestration.multi_agent_adapter" not in sys.modules:
        adapter_module = types.ModuleType("app.orchestration.multi_agent_adapter")

        class _MultiAgentWorkflowAdapterStub:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator

        adapter_module.MultiAgentWorkflowAdapter = _MultiAgentWorkflowAdapterStub
        adapter_module.execute_multi_agent_workflow = _emit_noop
        sys.modules["app.orchestration.multi_agent_adapter"] = adapter_module

    if "app.orchestration.version_conflict_service" not in sys.modules:
        version_conflict_module = types.ModuleType("app.orchestration.version_conflict_service")

        class _VersionConflictServiceStub:
            def __init__(self, redis, planner):
                self.redis = redis
                self.planner = planner

            async def check_all_conflicts(self, *args, **kwargs):
                return types.SimpleNamespace(has_conflict=False)

        version_conflict_module.VersionConflictService = _VersionConflictServiceStub
        sys.modules["app.orchestration.version_conflict_service"] = version_conflict_module

    if "app.orchestration.plan_review_service" not in sys.modules:
        review_module = types.ModuleType("app.orchestration.plan_review_service")

        class _ReviewDecision:
            APPROVED = types.SimpleNamespace(value="approved")
            REJECTED = types.SimpleNamespace(value="rejected")
            REQUIRES_CONFIRMATION = types.SimpleNamespace(value="requires_confirmation")
            NEEDS_MODIFICATION = types.SimpleNamespace(value="needs_modification")

        class _PlanReviewServiceStub:
            def set_redis(self, redis_client) -> None:
                self.redis = redis_client

            async def review_plan(self, *args, **kwargs):
                return types.SimpleNamespace(
                    decision="approved",
                    confidence=0.9,
                    alignment_score=0.9,
                    alignment_summary="stub review",
                    reasoning_summary="",
                    reasoning_details=[],
                    reasoning_source="stub",
                    user_facing_reason="",
                    review_id="review-1",
                    plan_id="plan-1",
                    to_dict=lambda: {"decision": "approved", "confidence": 0.9},
                )

            async def store_review_result(self, *args, **kwargs):
                return "review-action-1"

        review_module.ReviewDecision = _ReviewDecision
        review_module.plan_review_service = _PlanReviewServiceStub()
        sys.modules["app.orchestration.plan_review_service"] = review_module

    if "app.services.focus_service" not in sys.modules:
        focus_module = types.ModuleType("app.services.focus_service")
        focus_module.focus_service = types.SimpleNamespace()
        sys.modules["app.services.focus_service"] = focus_module

    if "app.services.user_service" not in sys.modules:
        user_module = types.ModuleType("app.services.user_service")
        user_module.UserService = type("UserService", (), {})
        sys.modules["app.services.user_service"] = user_module

    if "app.services.plan_progress_service" not in sys.modules:
        progress_module = types.ModuleType("app.services.plan_progress_service")
        progress_module.PlanHealthReport = type("PlanHealthReport", (), {})
        progress_module.PlanProgressService = type("PlanProgressService", (), {})
        sys.modules["app.services.plan_progress_service"] = progress_module

    if "app.services.progress_narrative_service" not in sys.modules:
        narrative_module = types.ModuleType("app.services.progress_narrative_service")
        narrative_module.ProgressNarrativeService = type("ProgressNarrativeService", (), {})
        sys.modules["app.services.progress_narrative_service"] = narrative_module

    if "app.services.plan_execution_record_service" not in sys.modules:
        record_module = types.ModuleType("app.services.plan_execution_record_service")
        record_module.PlanExecutionRecordService = type("PlanExecutionRecordService", (), {})
        sys.modules["app.services.plan_execution_record_service"] = record_module

    if "app.services.plan_execution_validator" not in sys.modules:
        plan_validator_module = types.ModuleType("app.services.plan_execution_validator")
        plan_validator_module.PlanExecutionValidator = type("PlanExecutionValidator", (), {})
        sys.modules["app.services.plan_execution_validator"] = plan_validator_module

    if "app.services.custom_expert_service" not in sys.modules:
        custom_expert_module = types.ModuleType("app.services.custom_expert_service")

        class _CustomExpertServiceStub:
            def __init__(self, db_session):
                self.db_session = db_session

            async def load_runtime_profiles(self, *args, **kwargs):
                return {}

        custom_expert_module.CustomExpertService = _CustomExpertServiceStub
        custom_expert_module.is_custom_expert_id = lambda expert_id: False
        sys.modules["app.services.custom_expert_service"] = custom_expert_module

    if "app.services.perceptible_intelligence_service" not in sys.modules:
        insight_module = types.ModuleType("app.services.perceptible_intelligence_service")
        insight_module.PerceptibleInsightService = type("PerceptibleInsightService", (), {})
        insight_module.ProgressComparisonService = type("ProgressComparisonService", (), {})
        sys.modules["app.services.perceptible_intelligence_service"] = insight_module

    if "app.services.self_evolution_service" not in sys.modules:
        evolution_module = types.ModuleType("app.services.self_evolution_service")
        evolution_module.UnderstandingDepthService = type("UnderstandingDepthService", (), {})
        sys.modules["app.services.self_evolution_service"] = evolution_module

    if "app.visualization.execution_tracer" not in sys.modules:
        tracer_module = types.ModuleType("app.visualization.execution_tracer")

        class _ExecutionTracer:
            def __init__(self, *args, **kwargs):
                pass

            async def record_event(self, *args, **kwargs) -> None:
                return None

        tracer_module.ExecutionTracer = _ExecutionTracer
        sys.modules["app.visualization.execution_tracer"] = tracer_module

    if "app.visualization.realtime_visualizer" not in sys.modules:
        visualizer_module = types.ModuleType("app.visualization.realtime_visualizer")
        visualizer_module.visualizer = types.SimpleNamespace(on_graph_event=_emit_noop)
        sys.modules["app.visualization.realtime_visualizer"] = visualizer_module


@pytest.fixture
def orchestrator_factory(monkeypatch):
    _install_import_stubs()
    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    circuit_breaker_module = importlib.import_module("app.orchestration.circuit_breaker")

    class _GraphStub:
        async def invoke(self, state):
            return state

    monkeypatch.setattr(orchestrator_module, "create_standard_chat_graph", lambda: _GraphStub())
    monkeypatch.setattr(orchestrator_module, "RunLedgerRecorder", _RunLedgerStub)
    monkeypatch.setattr(orchestrator_module, "ChatSignalCollector", _ChatSignalCollectorStub)

    async def _breaker_initialize(self) -> None:
        return None

    monkeypatch.setattr(circuit_breaker_module.CircuitBreaker, "initialize", _breaker_initialize)

    def _factory():
        redis_client = _MemoryRedis()

        orchestrator = orchestrator_module.ChatOrchestrator(db_session=None, redis_client=redis_client)
        state_updates: list[tuple[str, str]] = []
        real_update_state = orchestrator._update_state

        async def tracked_update_state(session_id: str, state: str, details: str = "", **kwargs):
            state_updates.append((state, details))
            return await real_update_state(session_id, state, details, **kwargs)

        orchestrator._update_state = tracked_update_state
        orchestrator._validate_request = AsyncMock(return_value=None)
        orchestrator._check_idempotency_response = AsyncMock(return_value=None)
        orchestrator._acquire_session_lock = AsyncMock(return_value=True)
        orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
        orchestrator._resolve_active_tools = MagicMock(return_value=[])
        orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(return_value=None)
        orchestrator._build_full_context = AsyncMock(return_value=({}, None, False, {}, {"messages": []}, None))
        orchestrator._detect_session_feedback = AsyncMock(return_value=(None, None, None))
        orchestrator._apply_cohort_to_session_feedback_signal = MagicMock(side_effect=lambda signal, cohort: signal)
        orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(return_value=None)
        orchestrator._maybe_enqueue_understanding_depth = AsyncMock(return_value=None)
        orchestrator._drain_system_updates = AsyncMock(
            return_value=(
                [],
                [],
                [],
                [],
                None,
                None,
                {
                    "proactive_opening_message": "",
                    "pending_observation": "",
                    "post_adaptation_question": "",
                },
            )
        )
        orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
        orchestrator._check_goal_quality = AsyncMock(return_value=False)
        orchestrator._load_context_versions = AsyncMock(return_value={})
        orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, _emit_noop))
        orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
        orchestrator._apply_context_focus_overlay = AsyncMock(
            side_effect=lambda **kwargs: kwargs["user_context_payload"]
        )
        orchestrator._apply_dual_core_routing = AsyncMock(side_effect=_passthrough_route)
        orchestrator._emit_roundtable_preview = AsyncMock(return_value=None)
        orchestrator._emit_orchestration_trace = AsyncMock(return_value=None)
        orchestrator._cache_response = AsyncMock(return_value=True)
        orchestrator._cleanup = AsyncMock(return_value=None)
        orchestrator._track_task = MagicMock()
        orchestrator._persist_assistant_message = AsyncMock(return_value=None)
        orchestrator._record_decision = AsyncMock(return_value=None)
        orchestrator.grounding_validator.validate_plan = AsyncMock(
            return_value=types.SimpleNamespace(
                is_valid=True,
                warnings=[],
                failure_reason="",
            )
        )
        orchestrator.observability.log_route_decision = AsyncMock(return_value=None)
        orchestrator.observability.log_circuit_state_change = AsyncMock(return_value=None)
        orchestrator.observability.log_collaboration_start = AsyncMock(return_value=None)
        orchestrator.observability.log_collaboration_end = AsyncMock(return_value=None)
        orchestrator.observability.log_langgraph_plan = AsyncMock(return_value=None)
        orchestrator.observability.log_validation_failed = AsyncMock(return_value=None)
        orchestrator.observability.log_phase_a_decision = AsyncMock(return_value=None)
        orchestrator.shadow_predictor.predict_and_record = AsyncMock(return_value=None)

        return orchestrator, redis_client, state_updates

    return _factory


@pytest.mark.asyncio
async def test_process_stream_direct_flow_reaches_done(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()
    captured_modes: list[str] = []

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, queue, result_holder, **kwargs):
        async for item in _drain_queue(queue):
            yield item
        await orchestrator._update_state(request.session_id, STATE_THINKING, "Understanding request")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="理解问题中",
            )
        )
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Drafting final answer")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details="组织回答中",
            )
        )
        yield agent_service_pb2.ChatResponse(delta="先帮你梳理重点。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, route_decision, session_id, **kwargs):
        captured_modes.append(route_decision.execution_mode)
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="先帮你梳理重点。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "先帮你梳理重点。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert captured_modes == ["direct"]
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_DONE]
    assert any(
        response.HasField("status_update") and response.status_update.state == agent_service_pb2.AgentStatus.THINKING
        for response in responses
    )
    assert any(
        response.HasField("status_update") and response.status_update.state == agent_service_pb2.AgentStatus.GENERATING
        for response in responses
    )
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "先帮你梳理重点。"
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_planning_bypass_injects_aurora_sidecar_prompt(orchestrator_factory):
    orchestrator, _, _state_updates = orchestrator_factory()
    user_id = str(uuid.uuid4())
    session_id = f"planning-detour-{uuid.uuid4()}"
    request = agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=session_id,
        user_id=user_id,
        message="等等，先帮我查一下这个任务完成没有",
    )
    captured_prompt = ""
    captured_sidecar: dict[str, object] = {}

    await orchestrator.planning_workflow_manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=session_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="soft_return_topic",
            chat_directive={
                "intent": "recover_planning_naturally",
                "brief": "Answer the current task first, then recover planning naturally.",
            },
        )
    )

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, state, queue, result_holder, **kwargs):
        nonlocal captured_prompt, captured_sidecar
        async for item in _drain_queue(queue):
            yield item
        user_context = state.context_data.get("user_context") or {}
        captured_sidecar = dict(user_context.get("aurora_planning_sidecar") or {})
        assert "aurora_planning_sidecar_prompt" not in user_context
        from app.orchestration.prompts import build_system_prompt

        captured_prompt = build_system_prompt(
            user_context,
            conversation_history=state.context_data.get("conversation_context") or {"messages": []},
        )
        yield agent_service_pb2.ChatResponse(delta="这个任务目前看起来还没完成。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="这个任务目前看起来还没完成。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "这个任务目前看起来还没完成。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)

    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert captured_sidecar["source"] == "aurora_decision_loop"
    assert (captured_sidecar.get("decision") or {}).get("action") == "soft_return_topic"
    assert "Aurora action: soft_return_topic" in captured_prompt
    assert "Directive brief: Answer the current task first, then recover planning naturally." in captured_prompt
    assert "AURORA PLANNING SIDECAR" in captured_prompt


@pytest.mark.asyncio
async def test_process_stream_planning_sidecar_does_not_reask_resolved_information(orchestrator_factory):
    orchestrator, _, _state_updates = orchestrator_factory()
    user_id = str(uuid.uuid4())
    session_id = f"planning-resolved-{uuid.uuid4()}"
    request = agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=session_id,
        user_id=user_id,
        message="先帮我查一下这个任务完成没有",
    )
    captured_sidecar: dict[str, object] = {}

    await orchestrator.planning_workflow_manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=session_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    await orchestrator.planning_workflow_manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=session_id,
        message="考传输层、网络层和应用层，我是零基础",
        context={},
    )
    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="soft_return_topic",
            chat_directive={
                "intent": "recover_missing_planning_slot",
                "brief": "Handle the detour first, then softly recover the one missing planning field only if it still matters.",
            },
        )
    )

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, state, queue, result_holder, **kwargs):
        nonlocal captured_sidecar
        async for item in _drain_queue(queue):
            yield item
        user_context = state.context_data.get("user_context") or {}
        captured_sidecar = dict(user_context.get("aurora_planning_sidecar") or {})
        yield agent_service_pb2.ChatResponse(delta="我看一下任务状态。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="我看一下任务状态。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "我看一下任务状态。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)

    assert responses[-1].finish_reason == agent_service_pb2.STOP
    scaffold = dict(captured_sidecar.get("scaffold") or {})
    assert (scaffold.get("top_tension") or {}).get("domain") == "time_available"
    assert "当前基础: 完全没学过" in list(scaffold.get("resolved_facts") or [])
    assert all(item.get("domain") != "knowledge_baseline" for item in list(scaffold.get("open_tensions") or []))


@pytest.mark.parametrize(
    ("action", "directive", "expected_prompt_line"),
    [
        (
            "wait",
            {"intent": "handle_current_need_only", "brief": "Stay on the current task and do not recover planning yet."},
            "本轮先处理当前需求，不要主动把话题拉回规划；只在用户自己回到规划时继续。",
        ),
        (
            "drop_thread",
            {"intent": "drop_stale_followup", "brief": "Do not bring the earlier planning clarification back in this reply."},
            "把先前那条规划追问放下，本轮不要带回，也不要补问刚才那块信息。",
        ),
    ],
)
@pytest.mark.asyncio
async def test_process_stream_planning_sidecar_supports_wait_and_drop_thread_actions(
    orchestrator_factory,
    action: str,
    directive: dict[str, str],
    expected_prompt_line: str,
):
    orchestrator, _, _state_updates = orchestrator_factory()
    user_id = str(uuid.uuid4())
    session_id = f"planning-action-{uuid.uuid4()}"
    request = agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=session_id,
        user_id=user_id,
        message="先帮我查一下这个任务完成没有",
    )
    captured_prompt = ""
    captured_sidecar: dict[str, object] = {}

    await orchestrator.planning_workflow_manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=session_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action=action,
            chat_directive=directive,
        )
    )

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, state, queue, result_holder, **kwargs):
        nonlocal captured_prompt, captured_sidecar
        async for item in _drain_queue(queue):
            yield item
        user_context = state.context_data.get("user_context") or {}
        captured_sidecar = dict(user_context.get("aurora_planning_sidecar") or {})
        from app.orchestration.prompts import build_system_prompt

        captured_prompt = build_system_prompt(
            user_context,
            conversation_history=state.context_data.get("conversation_context") or {"messages": []},
        )
        yield agent_service_pb2.ChatResponse(delta="我看一下任务状态。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="我看一下任务状态。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "我看一下任务状态。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)

    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert (captured_sidecar.get("decision") or {}).get("action") == action
    assert expected_prompt_line in captured_prompt


@pytest.mark.asyncio
async def test_process_stream_without_planning_session_leaves_stream_context_unchanged(orchestrator_factory):
    orchestrator, _, _state_updates = orchestrator_factory()
    request = _make_request(message="帮我解释一下 TCP 三次握手")
    captured_user_context: dict[str, object] = {}

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="knowledge_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, state, queue, result_holder, **kwargs):
        nonlocal captured_user_context
        async for item in _drain_queue(queue):
            yield item
        captured_user_context = dict(state.context_data.get("user_context") or {})
        yield agent_service_pb2.ChatResponse(delta="TCP 三次握手用于确认双方收发能力。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="TCP 三次握手用于确认双方收发能力。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "TCP 三次握手用于确认双方收发能力。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)

    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert "aurora_planning_sidecar_prompt" not in captured_user_context
    assert "aurora_planning_sidecar" not in captured_user_context


@pytest.mark.asyncio
async def test_process_stream_onboarding_modeling_enters_aurora_runtime_path(orchestrator_factory, monkeypatch):
    orchestrator, redis_client, state_updates = orchestrator_factory()
    request = _make_request(message="我最近特别想把学习和作息一起稳下来。")
    request.extra_context.CopyFrom(_make_struct({"mode": "onboarding_modeling"}))

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    monkeypatch.setattr(orchestrator_module.settings, "ENABLE_AURORA_RUNTIME_V1", True, raising=False)

    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="emit_message",
            surface_complete=False,
            modeling_complete=False,
            chat_directive={"intent": "continue_modeling"},
        )
    )
    orchestrator.aurora_runtime_v1.chat_adapter.render = AsyncMock(
        return_value=[
            "谢谢你先把这部分告诉我。",
            "我会先围着你的节奏和目标把线索补齐。",
            "如果只先补一个关键空缺，你现在最想先稳住的是作息还是学习推进？",
        ]
    )
    orchestrator._route_and_classify = AsyncMock(side_effect=AssertionError("aurora path should bypass router"))
    orchestrator._plan_and_validate = AsyncMock(side_effect=AssertionError("aurora path should bypass planner"))

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    finish_reasons = [response.finish_reason for response in responses if response.finish_reason]

    assert orchestrator.aurora_runtime_v1.decision_loop.decide.call_count == 1
    assert finish_reasons == [
        agent_service_pb2.CONTINUE,
        agent_service_pb2.CONTINUE,
        agent_service_pb2.STOP,
    ]
    assert responses[-1].metadata["aurora_surface"] == "aurora_modeling"
    assert responses[-1].metadata["aurora_runtime_enabled"] == "true"
    assert responses[-1].metadata["surface_complete"] == "false"
    assert responses[-1].metadata["modeling_complete"] == "false"
    assert any(key.startswith("aurora:runtime:") for key in redis_client.values)
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_explicit_aurora_modeling_surface_uses_modeling_contract(
    orchestrator_factory,
    monkeypatch,
):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="就这些，差不多了。")
    request.extra_context.CopyFrom(
        _make_struct(
            {
                "aurora_surface": "aurora_modeling",
                "aurora_runtime_enabled": True,
            }
        )
    )

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    monkeypatch.setattr(orchestrator_module.settings, "ENABLE_AURORA_RUNTIME_V1", True, raising=False)
    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="emit_message",
            surface_complete=True,
            modeling_complete=True,
            chat_directive={"intent": "close_modeling"},
        )
    )
    orchestrator.aurora_runtime_v1.chat_adapter.render = AsyncMock(
        return_value=[
            "我大概已经抓到你的轮廓了，先把目前这些线索收住。",
            "接下来我会带着这些理解继续陪你往下走；如果你想补充，随时都可以接着说。",
        ]
    )

    orchestrator._route_and_classify = AsyncMock(side_effect=AssertionError("aurora path should bypass router"))
    orchestrator._plan_and_validate = AsyncMock(side_effect=AssertionError("aurora path should bypass planner"))

    responses = await _collect(orchestrator, request)
    final_response = responses[-1]
    text_frames = [response.full_text for response in responses if response.full_text]
    generic_fallback_frames = {
        "我先接住你刚刚补进来的信息。",
        "这轮我会按这个方向继续往下走；如果你想改重点，也可以直接打断我。",
    }

    assert [response.finish_reason for response in responses if response.finish_reason] == [
        agent_service_pb2.CONTINUE,
        agent_service_pb2.STOP,
    ]
    assert final_response.metadata["aurora_surface"] == "aurora_modeling"
    assert final_response.metadata["aurora_runtime_enabled"] == "true"
    assert final_response.metadata["surface_complete"] == "true"
    assert final_response.metadata["modeling_complete"] == "true"
    assert not generic_fallback_frames.intersection(text_frames)
    assert text_frames == [
        "我大概已经抓到你的轮廓了，先把目前这些线索收住。",
        "接下来我会带着这些理解继续陪你往下走；如果你想补充，随时都可以接着说。",
    ]
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]


@pytest.mark.asyncio
async def test_process_stream_legacy_modeling_surface_is_canonicalized(orchestrator_factory, monkeypatch):
    orchestrator, _, _state_updates = orchestrator_factory()
    request = _make_request(message="我最近想把目标和作息一起稳下来。")
    request.extra_context.CopyFrom(_make_struct({"aurora_surface": "modeling"}))

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    monkeypatch.setattr(orchestrator_module.settings, "ENABLE_AURORA_RUNTIME_V1", True, raising=False)
    orchestrator.aurora_runtime_v1.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="emit_message",
            surface_complete=False,
            modeling_complete=False,
            chat_directive={"intent": "continue_modeling"},
        )
    )
    orchestrator.aurora_runtime_v1.chat_adapter.render = AsyncMock(
        return_value=[
            "我会先把目标和节奏这两块放在一起看。",
            "现在最值得补齐的是：你这次具体想稳住哪个结果？",
        ]
    )
    orchestrator._route_and_classify = AsyncMock(side_effect=AssertionError("aurora path should bypass router"))
    orchestrator._plan_and_validate = AsyncMock(side_effect=AssertionError("aurora path should bypass planner"))

    responses = await _collect(orchestrator, request)
    text_frames = [response.full_text for response in responses if response.full_text]

    assert responses[-1].metadata["aurora_surface"] == "aurora_modeling"
    assert responses[-1].metadata["modeling_complete"] == "false"
    assert "我先接住你刚刚补进来的信息。" not in text_frames
    assert any("目标" in frame or "节奏" in frame for frame in text_frames)


@pytest.mark.asyncio
async def test_process_stream_aurora_wait_turn_emits_terminal_frame_and_caches_response(
    orchestrator_factory,
    monkeypatch,
):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="我先不继续这个话题。")
    request.extra_context.CopyFrom(_make_struct({"aurora_surface": "aurora_modeling"}))

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    monkeypatch.setattr(orchestrator_module.settings, "ENABLE_AURORA_RUNTIME_V1", True, raising=False)
    orchestrator.aurora_runtime_v1.plan_turn = AsyncMock(
        return_value=AuroraRuntimeTurnPlan(
            surface="aurora_modeling",
            messages=[],
            surface_complete=False,
            modeling_complete=False,
        )
    )
    orchestrator._route_and_classify = AsyncMock(side_effect=AssertionError("aurora path should bypass router"))
    orchestrator._plan_and_validate = AsyncMock(side_effect=AssertionError("aurora path should bypass planner"))

    responses = await _collect(orchestrator, request)
    terminal_frames = [response for response in responses if response.finish_reason]

    assert len(terminal_frames) == 1
    assert terminal_frames[0].finish_reason == agent_service_pb2.STOP
    assert terminal_frames[0].full_text == ""
    assert terminal_frames[0].metadata["aurora_surface"] == "aurora_modeling"
    assert terminal_frames[0].metadata["aurora_runtime_enabled"] == "true"
    assert terminal_frames[0].metadata["surface_complete"] == "false"
    assert terminal_frames[0].metadata["modeling_complete"] == "false"
    orchestrator._persist_assistant_message.assert_not_awaited()
    orchestrator._cache_response.assert_awaited_once()
    cached_payload = orchestrator._cache_response.await_args.args[2]
    assert cached_payload["message"] == ""
    assert cached_payload["metadata"]["aurora_surface"] == "aurora_modeling"
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]


@pytest.mark.asyncio
async def test_process_stream_feature_flag_off_keeps_legacy_behavior(orchestrator_factory, monkeypatch):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="我最近在摸索自己的节奏。")
    request.extra_context.CopyFrom(_make_struct({"mode": "onboarding_modeling"}))

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    monkeypatch.setattr(orchestrator_module.settings, "ENABLE_AURORA_RUNTIME_V1", False, raising=False)
    orchestrator.aurora_runtime_v1.plan_turn = AsyncMock(side_effect=AssertionError("feature flag off"))
    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (
            kwargs["route_decision"],
            None,
            None,
            False,
        )
    )

    async def execute_graph(*, queue, result_holder, **kwargs):
        async for item in _drain_queue(queue):
            yield item
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Legacy direct response")
        yield agent_service_pb2.ChatResponse(delta="这是旧链路返回。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="这是旧链路返回。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "这是旧链路返回。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)

    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "这是旧链路返回。"
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]


@pytest.mark.asyncio
async def test_process_stream_tool_result_continuation_marks_done(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="")
    request.tool_result.tool_call_id = "tool-1"
    request.tool_result.tool_name = "search_knowledge"
    request.tool_result.result_json = '{"summary":"找到 3 条相关知识"}'

    async def continue_after_tool_result(**kwargs):
        await orchestrator._update_state(request.session_id, STATE_TOOL_CALLING, "Tool result received")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details="处理工具结果",
            )
        )
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Synthesizing tool result")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details="整合工具输出",
            )
        )
        yield agent_service_pb2.ChatResponse(
            full_text="根据工具结果，我已经帮你整理出关键结论。",
            finish_reason=agent_service_pb2.STOP,
        )

    orchestrator._continue_after_tool_result = continue_after_tool_result

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_TOOL_CALLING, STATE_GENERATING, STATE_DONE]
    assert any(
        response.HasField("status_update")
        and response.status_update.state == agent_service_pb2.AgentStatus.EXECUTING_TOOL
        for response in responses
    )
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "根据工具结果，我已经帮你整理出关键结论。"
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_planner_failure_falls_back_to_direct_mode(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="帮我设计一个跨学科长期学习方案")
    captured_modes: list[str] = []

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="langgraph", reason="complex_plan", risk_level="medium"), None)
    )
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(return_value=MagicMock(snapshot_id="snap-1"))
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.lang_graph_planner.plan = AsyncMock(side_effect=RuntimeError("llm timeout"))

    async def execute_graph(*, queue, result_holder, **kwargs):
        async for item in _drain_queue(queue):
            yield item
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Fallback direct response")
        yield agent_service_pb2.ChatResponse(delta="我先用直接模式给你一个稳定版本。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, route_decision, session_id, **kwargs):
        captured_modes.append(route_decision.execution_mode)
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="我先用直接模式给你一个稳定版本。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "我先用直接模式给你一个稳定版本。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert captured_modes == ["direct"]
    assert any("规划失败，使用直接模式" in response.delta for response in responses if response.HasField("delta"))
    orchestrator.langgraph_breaker.on_failure.assert_awaited_once()
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "我先用直接模式给你一个稳定版本。"
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_lock_conflict_returns_retryable_error(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()
    orchestrator._acquire_session_lock = AsyncMock(return_value=False)

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert len(responses) == 1
    assert responses[0].HasField("error")
    assert responses[0].error.error_code == agent_service_pb2.ERROR_CODE_CONFLICT
    assert responses[0].error.retryable is True
    assert state_updates == []
    assert final_state is None


@pytest.mark.asyncio
async def test_process_stream_review_required_drains_queue_before_return(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="帮我制定一个四周复习计划")

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="langgraph", reason="complex_plan", risk_level="medium"), None)
    )
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(return_value=MagicMock(snapshot_id="snap-review"))
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.lang_graph_planner.plan = AsyncMock(
        return_value=ExecutablePlan(
            plan_id="plan-review-1",
            source="langgraph",
            confidence=0.86,
            rationale="review-gated study plan",
            tool_calls=[
                ToolCallSpec(id="step-1", name="search_knowledge", params={"topic": "复习策略"}),
                ToolCallSpec(id="step-2", name="generate_learning_report", params={"scope": "4_weeks"}),
            ],
        )
    )

    review_module = sys.modules["app.orchestration.plan_review_service"]
    review_result = types.SimpleNamespace(
        decision=review_module.ReviewDecision.REQUIRES_CONFIRMATION.value,
        confidence=0.78,
        alignment_score=0.71,
        alignment_summary="计划需要你先确认节奏和投入强度。",
        reasoning_summary="",
        reasoning_details=[],
        reasoning_source="stubbed_review",
        quality_report={},
        user_facing_reason="建议先确认执行节奏。",
        review_id="review-42",
        plan_id="plan-review-1",
        comments=[
            types.SimpleNamespace(
                severity="warning",
                message="每周投入时长尚未确认。",
                suggested_fix="补充你的每周可用时间。",
            )
        ],
        to_dict=lambda: {
            "decision": review_module.ReviewDecision.REQUIRES_CONFIRMATION.value,
            "review_id": "review-42",
            "plan_id": "plan-review-1",
        },
    )
    review_module.plan_review_service.review_plan = AsyncMock(return_value=review_result)
    review_module.plan_review_service.store_review_result = AsyncMock(return_value="review-action-1")

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    review_responses = [response for response in responses if response.metadata.get("requires_review") == "true"]
    assert review_responses, "review-required path should flush queued review response before returning"
    assert review_responses[0].metadata["review_action_id"] == "review-action-1"
    assert review_responses[0].metadata["review_decision"] == review_result.decision
    assert "需要确认计划" in review_responses[0].delta
    assert responses[-1].finish_reason != agent_service_pb2.STOP
    assert len(state_updates) == 1
    assert state_updates[0][0] == STATE_INIT
    assert state_updates[0][1].startswith("Request req-")
    assert final_state is not None
    assert final_state.state == STATE_INIT
    assert orchestrator.langgraph_breaker.on_success.await_count == 0


@pytest.mark.asyncio
async def test_process_stream_phase_a_hard_stops_cold_start_plan_before_planning(orchestrator_factory):
    orchestrator, _, _state_updates = orchestrator_factory()
    request = _make_request(message="帮我做一个 14 天物理考试冲刺计划")

    shadow_module = types.ModuleType("app.services.shadow_prediction_service")
    shadow_module.shadow_prediction_service = types.SimpleNamespace(
        predict_intent_only=AsyncMock(
            return_value={
                "intent_type": "create_plan",
                "suggested_tools": ["create_plan"],
            }
        )
    )
    sys.modules["app.services.shadow_prediction_service"] = shadow_module

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    orchestrator._check_sufficiency = orchestrator_module.ChatOrchestrator._check_sufficiency.__get__(
        orchestrator,
        type(orchestrator),
    )
    orchestrator._compose_fast_interaction_copy = AsyncMock(
        return_value="先确认一个关键问题：你目前对这个主题的掌握大概在哪个水平？"
    )
    orchestrator._build_full_context = AsyncMock(
        return_value=(
            {},
            None,
            False,
            {
                "profile_context": {
                    "preferences": {},
                    "preference_version": 0,
                    "knowledge_summary": {
                        "overall_mastery": 0.0,
                        "weak_spots": [],
                        "recent_mastery_changes": [],
                        "active_learning_subjects": [],
                    },
                    "cognitive_summary": {
                        "active_patterns": [],
                        "dominant_pattern_type": None,
                        "risk_signals": [],
                    },
                },
            },
            {"messages": []},
            None,
        )
    )
    orchestrator._route_and_classify = AsyncMock()
    orchestrator._plan_and_validate = AsyncMock()

    responses = await _collect(orchestrator, request)

    assert orchestrator._plan_and_validate.await_count == 0
    assert orchestrator._route_and_classify.await_count == 0
    assert any(response.metadata.get("requires_clarification") == "true" for response in responses)
    assert any(response.metadata.get("clarification_source") == "phase_a" for response in responses)
    assert any(response.metadata.get("phase_a_guardrail") == "ask_before_plan" for response in responses)
    assert responses[-1].full_text.count("？") <= 1
    assert "掌握" in responses[-1].full_text or "水平" in responses[-1].full_text


@pytest.mark.asyncio
async def test_process_stream_phase_a_hard_stop_survives_underclassified_planning_intent(orchestrator_factory):
    orchestrator, _, _state_updates = orchestrator_factory()
    request = _make_request(message="帮我安排一下 14 天物理考试冲刺计划")

    shadow_module = types.ModuleType("app.services.shadow_prediction_service")
    shadow_module.shadow_prediction_service = types.SimpleNamespace(
        predict_intent_only=AsyncMock(
            return_value={
                "intent_type": "knowledge_query",
                "suggested_tools": [],
            }
        )
    )
    sys.modules["app.services.shadow_prediction_service"] = shadow_module

    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    orchestrator._check_sufficiency = orchestrator_module.ChatOrchestrator._check_sufficiency.__get__(
        orchestrator,
        type(orchestrator),
    )
    orchestrator._compose_fast_interaction_copy = AsyncMock(
        return_value="先确认一个关键问题：你目前对这个主题的掌握大概在哪个水平？"
    )
    orchestrator._build_full_context = AsyncMock(
        return_value=(
            {},
            None,
            False,
            {
                "current_query": "帮我安排一下 14 天物理考试冲刺计划",
                "context_focus": {"route_intent": "plan"},
                "profile_context": {
                    "preferences": {},
                    "preference_version": 0,
                    "knowledge_summary": {
                        "overall_mastery": 0.0,
                        "weak_spots": [],
                        "recent_mastery_changes": [],
                        "active_learning_subjects": [],
                    },
                    "cognitive_summary": {
                        "active_patterns": [],
                        "dominant_pattern_type": None,
                        "risk_signals": [],
                    },
                },
            },
            {"messages": []},
            None,
        )
    )
    orchestrator._route_and_classify = AsyncMock()
    orchestrator._plan_and_validate = AsyncMock()

    responses = await _collect(orchestrator, request)

    assert orchestrator._plan_and_validate.await_count == 0
    assert orchestrator._route_and_classify.await_count == 0
    assert any(response.metadata.get("planning_detection_source") == "route_intent" for response in responses)
    orchestrator.observability.log_phase_a_decision.assert_awaited()
