from __future__ import annotations

import importlib
import json
import sys
import types
import uuid
from collections.abc import AsyncGenerator
from copy import deepcopy
from datetime import timedelta
from statistics import mean
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.gen.agent.v1 import agent_service_pb2
from app.models.base import Base
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.user import User
from app.orchestration.prompts import build_system_prompt
from app.orchestration.schemas import ExecutablePlan, RouteDecision
from app.orchestration.statechart_engine import WorkflowState
from app.orchestration.situation_brief import SituationBriefBuilder

class _RunLedgerStub:
    def __init__(self, *args, **kwargs):
        self.events: list[dict[str, object]] = []

    async def record_event(self, *args, **kwargs) -> None:
        self.events.append({"args": args, "kwargs": kwargs})

    def to_metadata_payload(self) -> dict[str, object]:
        return {
            "event_count": len(self.events),
        }


class _ChatSignalCollectorStub:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def collect_signals(self, *args, **kwargs) -> None:
        return None


class _MemoryRedis:
    def __init__(self) -> None:
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
        del numkeys
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

    async def zadd(self, key: str, mapping: dict[str, float]):
        self.values.setdefault(key, {})
        bucket = self.values[key]
        if not isinstance(bucket, dict):
            bucket = {}
            self.values[key] = bucket
        bucket.update(mapping)
        return len(mapping)

    async def zrange(self, key: str, start: int, end: int, *, withscores: bool = False):
        bucket = self.values.get(key, {})
        if not isinstance(bucket, dict):
            return []
        items = sorted(bucket.items(), key=lambda item: item[1])
        if end == -1:
            sliced = items[start:]
        else:
            sliced = items[start : end + 1]
        if withscores:
            return sliced
        return [member for member, _score in sliced]

    async def zcard(self, key: str):
        bucket = self.values.get(key, {})
        return len(bucket) if isinstance(bucket, dict) else 0

    async def ping(self):
        return True


async def _emit_noop(*args, **kwargs) -> None:
    return None


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

        class _PlanProgressServiceStub:
            def __init__(self, *args, **kwargs):
                pass

        progress_module.PlanProgressService = _PlanProgressServiceStub
        sys.modules["app.services.plan_progress_service"] = progress_module

    if "app.services.progress_narrative_service" not in sys.modules:
        narrative_module = types.ModuleType("app.services.progress_narrative_service")

        class _ProgressNarrativeServiceStub:
            def __init__(self, *args, **kwargs):
                pass

            async def maybe_get_lightweight_snapshot(self, *args, **kwargs):
                return None

        narrative_module.ProgressNarrativeService = _ProgressNarrativeServiceStub
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


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _base_plan_context(plan: Plan) -> dict[str, str]:
    return {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "plan_title": plan.name,
        "goal": "掌握热力学第二章",
        "plan_stage": "冲刺阶段",
    }


def _turn_user_context(user_message: str) -> dict[str, object]:
    lowered = user_message.lower()
    if "choose" in lowered or "怎么选" in user_message:
        return {
            "current_query": user_message,
            "active_goals": [{"title": "14 天内稳住热力学第二章"}],
            "context_focus": {"focus_mode": "decision_focus", "route_intent": "decision"},
            "profile_context": {
                "cognitive_summary": {
                    "active_patterns": [{"pattern_name": "过度比较", "pattern_type": "planning", "confidence": 0.74}]
                }
            },
            "context_briefing_note": "用户已经恢复一点行动，现在需要规范性判断支持，而不是替他做决定。",
            "progress_snapshot": {"highlights": ["用户已经重新启动，但接下来要选对方向。"]},
        }
    if "not the kind" in lowered or "我是不是" in user_message:
        return {
            "current_query": user_message,
            "active_goals": [{"title": "14 天内稳住热力学第二章"}],
            "context_focus": {"focus_mode": "identity_focus", "route_intent": "chat"},
            "profile_context": {
                "cognitive_summary": {
                    "active_patterns": [{"pattern_name": "自我否定循环", "pattern_type": "identity", "confidence": 0.86}]
                }
            },
            "focused_memory": {
                "evidence": {
                    "supporting_items": ["昨天已经完成了 5 分钟微启动", "上周开始能连续推进热力学第二章"],
                }
            },
            "context_briefing_note": "用户处在身份脆弱时刻，需要用连续证据修复自我模型。",
            "progress_snapshot": {"highlights": ["用户已经能重新启动，但自我解释开始滑向否定。"]},
        }
    if "too much" in lowered:
        return {
            "current_query": user_message,
            "active_goals": [{"title": "14 天内稳住热力学第二章"}],
            "context_focus": {"focus_mode": "general_focus", "route_intent": "chat"},
            "profile_context": {
                "cognitive_summary": {
                    "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.83}]
                }
            },
            "context_briefing_note": "User is overloaded and struggling to start.",
            "progress_snapshot": {"attention_areas": ["Load is too high this week."]},
        }
    if "这样轻一点" in user_message:
        return {
            "current_query": user_message,
            "active_goals": [{"title": "14 天内稳住热力学第二章"}],
            "context_focus": {"focus_mode": "general_focus", "route_intent": "chat"},
            "profile_context": {
                "cognitive_summary": {
                    "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.81}]
                }
            },
            "context_briefing_note": "用户开始恢复行动，Sparkle 需要保留连续性并轻推下一步。",
            "progress_snapshot": {"highlights": ["用户已经能重新启动。"]},
        }
    return {
        "current_query": user_message,
        "active_goals": [{"title": "14 天内稳住热力学第二章"}],
        "learning_gaps_summary": "熵增方向判断和可逆/不可逆过程仍然容易混淆。",
        "context_focus": {"focus_mode": "knowledge_focus", "route_intent": "knowledge"},
        "profile_context": {
            "knowledge_summary": {
                "weak_spots": [{"node_id": "thermo-entropy-direction", "node_name": "熵增方向判断", "mastery": 39}],
            },
            "cognitive_summary": {
                "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.81}]
            },
        },
        "context_briefing_note": "用户想先用自己的资料修复热力学概念误解。",
    }


def _make_request(
    *,
    user_id: str,
    session_id: str,
    message: str,
    history: list[agent_service_pb2.ChatMessage],
    file_ids: list[str] | None = None,
) -> agent_service_pb2.ChatRequest:
    request = agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=session_id,
        user_id=user_id,
        message=message,
        file_ids=list(file_ids or []),
    )
    request.history.extend(history)
    return request


async def _collect(
    orchestrator,
    request: agent_service_pb2.ChatRequest,
    db_session: AsyncSession,
) -> list[agent_service_pb2.ChatResponse]:
    return [response async for response in orchestrator.process_stream(request, db_session=db_session)]


@pytest.mark.asyncio
async def test_phase5_orchestrator_cold_start_plan_asks_one_question_instead_of_planning(
    monkeypatch,
    db_session,
):
    _install_import_stubs()
    orchestrator_module = importlib.import_module("app.orchestration.orchestrator")
    circuit_breaker_module = importlib.import_module("app.orchestration.circuit_breaker")

    monkeypatch.setattr(orchestrator_module, "create_standard_chat_graph", lambda: MagicMock())
    monkeypatch.setattr(orchestrator_module, "RunLedgerRecorder", _RunLedgerStub)
    monkeypatch.setattr(orchestrator_module, "ChatSignalCollector", _ChatSignalCollectorStub)

    async def _breaker_initialize(self) -> None:
        return None

    monkeypatch.setattr(circuit_breaker_module.CircuitBreaker, "initialize", _breaker_initialize)

    shadow_module = types.ModuleType("app.services.shadow_prediction_service")
    shadow_module.shadow_prediction_service = SimpleNamespace(
        predict_intent_only=AsyncMock(
            return_value={
                "intent_type": "create_plan",
                "suggested_tools": ["create_plan"],
            }
        )
    )
    sys.modules["app.services.shadow_prediction_service"] = shadow_module

    user = User(
        username="phase5_cold_start_user",
        email="phase5_cold_start_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    redis_client = _MemoryRedis()
    orchestrator = orchestrator_module.ChatOrchestrator(db_session=db_session, redis_client=redis_client)
    orchestrator.token_tracker = None
    orchestrator._validate_request = AsyncMock(return_value=None)
    orchestrator._check_idempotency_response = AsyncMock(return_value=None)
    orchestrator._acquire_session_lock = AsyncMock(return_value=True)
    orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
    orchestrator._resolve_active_tools = MagicMock(return_value=[])
    orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(return_value=None)
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
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, _emit_noop))
    orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
    orchestrator._emit_roundtable_preview = AsyncMock(return_value=None)
    orchestrator._emit_orchestration_trace = AsyncMock(return_value=None)
    orchestrator._suggest_mode_switch = MagicMock(return_value=None)
    orchestrator._cache_response = AsyncMock(return_value=True)
    orchestrator._cleanup = AsyncMock(return_value=None)
    orchestrator._track_task = MagicMock()
    orchestrator._persist_assistant_message = AsyncMock(return_value=None)
    orchestrator._record_decision = AsyncMock(return_value=None)
    orchestrator._validate_plan_execution = AsyncMock(return_value={})
    orchestrator._detect_execution_suggestion = AsyncMock(return_value=None)
    orchestrator._hydrate_evolution_context = AsyncMock(return_value=None)
    orchestrator.grounding_validator.validate_plan = AsyncMock(
        return_value=types.SimpleNamespace(is_valid=True, warnings=[], failure_reason="")
    )
    orchestrator.observability.log_route_decision = AsyncMock(return_value=None)
    orchestrator.observability.log_circuit_state_change = AsyncMock(return_value=None)
    orchestrator.observability.log_collaboration_start = AsyncMock(return_value=None)
    orchestrator.observability.log_collaboration_end = AsyncMock(return_value=None)
    orchestrator.observability.log_langgraph_plan = AsyncMock(return_value=None)
    orchestrator.observability.log_validation_failed = AsyncMock(return_value=None)
    orchestrator.observability.log_phase_a_decision = AsyncMock(return_value=None)
    orchestrator.shadow_predictor.predict_and_record = AsyncMock(return_value=None)

    orchestrator._check_sufficiency = orchestrator_module.ChatOrchestrator._check_sufficiency.__get__(
        orchestrator,
        type(orchestrator),
    )
    orchestrator._compose_fast_interaction_copy = AsyncMock(
        return_value="我先确认一个最关键的问题：你目前对物理这部分的掌握大概在哪个水平？"
    )
    orchestrator._check_goal_quality = AsyncMock(return_value=False)
    orchestrator._build_full_context = AsyncMock(
        return_value=(
            {},
            None,
            False,
            {
                "current_query": "帮我做一个 14 天物理考试冲刺计划",
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
    orchestrator._attach_user_strategy_state = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._route_and_classify = AsyncMock()
    orchestrator._plan_and_validate = AsyncMock()

    request = _make_request(
        user_id=str(user.id),
        session_id=f"phase5-cold-start-{uuid.uuid4()}",
        message="帮我做一个 14 天物理考试冲刺计划",
        history=[],
    )
    responses = await _collect(orchestrator, request, db_session)

    assert orchestrator._plan_and_validate.await_count == 0
    assert orchestrator._route_and_classify.await_count == 0
    assert any(response.metadata.get("clarification_source") == "phase_a" for response in responses)
    assert any(response.metadata.get("phase_a_guardrail") == "ask_before_plan" for response in responses)
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text.count("？") <= 1
    assert "掌握" in responses[-1].full_text or "水平" in responses[-1].full_text
    assert "计划" not in responses[-1].full_text or "先确认" in responses[-1].full_text
