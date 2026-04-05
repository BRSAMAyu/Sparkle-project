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
from app.services.experience_phase_evaluator import ExperiencePhaseEvaluator


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
                "weak_spots": [{"node_name": "熵增方向判断", "mastery": 39}],
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


@pytest.mark.asyncio
async def test_phase5_thermodynamics_orchestrator_journey_derives_scores_from_runtime_outputs(
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

    async def _fake_openclaw_chat_control(**kwargs) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        del kwargs
        if False:
            yield agent_service_pb2.ChatResponse()

    async def _fake_attach_shadow_soul_runtime(
        *,
        target_context,
        redis_client,
        user_id,
        user_context,
        plan_context,
        effective_companion_state,
        relationship_profile,
        recent_revisions,
    ):
        del redis_client, user_id, user_context, plan_context, effective_companion_state, relationship_profile, recent_revisions
        target_context.setdefault(
            "effective_companion_state",
            {
                "warmth_calibration": 0.64,
                "candor_calibration": 0.62,
                "relationship_stage": "building",
            },
        )
        target_context.setdefault(
            "companion_state_recent_revisions",
            [{"change_summary": "ground in user materials first", "evidence": {"measurable_effect": True}}],
        )
        return SimpleNamespace(
            debug={
                "compiler_version": "test-shadow",
                "constitution_version": "test-constitution",
                "identity_kernel_version": "test-kernel",
                "dual_core_source": "test",
                "dual_core_mode": "balanced",
            }
        )

    monkeypatch.setattr(circuit_breaker_module.CircuitBreaker, "initialize", _breaker_initialize)
    monkeypatch.setattr(orchestrator_module, "attach_shadow_soul_runtime", _fake_attach_shadow_soul_runtime)

    user = User(
        username="phase5_orchestrator_user",
        email="phase5_orchestrator_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="热力学 14 天冲刺",
        type=PlanType.SPRINT,
        description="用真实材料查漏补缺",
        plan_stage=PlanStage.DAILY,
        target_date=(__import__("datetime").datetime.utcnow().date() + timedelta(days=14)),
        daily_available_minutes=90,
        total_estimated_hours=18,
        subject="热力学",
        mastery_level=0.41,
        progress=0.28,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)

    intervention = InterventionRecord(
        user_id=user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(plan)
    await db_session.refresh(intervention)

    fake_file = SimpleNamespace(
        id=uuid.uuid4(),
        file_name="thermo-notes.pdf",
        mime_type="application/pdf",
    )
    fake_result = SimpleNamespace(
        file_name="thermo-notes.pdf",
        score=0.94,
        chunk=SimpleNamespace(
            id=uuid.uuid4(),
            file_id=fake_file.id,
            section_title="Entropy",
            page_numbers=[12],
            content="判断熵增方向时，先确定系统边界，再看不可逆过程是否主导。",
        ),
    )

    async def _fake_resolve_scoped_files(db, *, user_id, requested_file_ids):
        del db, user_id, requested_file_ids
        return [fake_file]

    async def _fake_document_vector_search(self, *, user_id, query, file_ids, vector_query, limit, threshold):
        del self, user_id, query, file_ids, vector_query, limit, threshold
        return [fake_result]

    monkeypatch.setattr(
        "app.orchestration.experience_actuator._resolve_scoped_files",
        _fake_resolve_scoped_files,
    )
    monkeypatch.setattr(
        "app.orchestration.experience_actuator.KnowledgeRetrievalService.document_vector_search",
        _fake_document_vector_search,
    )

    redis_client = _MemoryRedis()
    orchestrator = orchestrator_module.ChatOrchestrator(db_session=db_session, redis_client=redis_client)
    orchestrator.token_tracker = None
    orchestrator._validate_request = AsyncMock(return_value=None)
    orchestrator._check_idempotency_response = AsyncMock(return_value=None)
    orchestrator._acquire_session_lock = AsyncMock(return_value=True)
    orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
    orchestrator._resolve_active_tools = MagicMock(return_value=[])
    orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(return_value=None)
    orchestrator._stream_openclaw_chat_control = _fake_openclaw_chat_control
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

    async def _fake_build_full_context(*, request, active_db, user_id, session_id, user_message, request_id, tracer):
        del request, active_db, user_id, session_id, request_id, tracer
        payload = _turn_user_context(user_message)
        payload.setdefault(
            "user_strategy_state",
            {
                "difficulty_level": 4,
                "session_mode": "guided",
                "explanation_style": "conceptual",
                "retrieval_emphasis": "balanced",
                "push_vs_support": 0.52,
                "intervention_intensity": "medium",
            },
        )
        if "这样轻一点" in user_message:
            payload["active_interventions"] = [{"intervention_id": str(intervention.id), "source": "runtime_context"}]
        dual_core_mode = "execution_first" if ("too much" in user_message.lower() or "这样轻一点" in user_message) else "balanced"
        brief = await SituationBriefBuilder().build(
            user_context_payload=payload,
            plan_context=_base_plan_context(plan),
            focused_memory={},
            context_briefing_note=str(payload.get("context_briefing_note") or ""),
            visible_update_context={},
            dual_core_snapshot={"decision": {"mode": dual_core_mode}},
            session_feedback_signal={},
            progress_snapshot=payload.get("progress_snapshot") if isinstance(payload.get("progress_snapshot"), dict) else {},
            adaptation_records=[],
        ).to_dict()
        payload["situation_brief"] = brief
        payload["residual_decision_context"] = brief["decision_context"]
        return (
            {},
            plan.id,
            False,
            payload,
            {"messages": []},
            _base_plan_context(plan),
        )

    async def _fake_apply_context_focus_overlay(**kwargs):
        payload = kwargs["user_context_payload"]
        state = kwargs["state"]
        if isinstance(payload, dict):
            if isinstance(payload.get("context_focus"), dict):
                state.context_data["context_focus"] = deepcopy(payload["context_focus"])
            note = str(payload.get("context_briefing_note") or "").strip()
            if note:
                state.context_data["context_briefing_note"] = note
            if isinstance(payload.get("progress_snapshot"), dict):
                state.context_data["progress_snapshot"] = deepcopy(payload["progress_snapshot"])
        return payload

    async def _fake_apply_dual_core_routing(*, route_decision, state, user_context_payload, **kwargs):
        del kwargs
        message = str((user_context_payload or {}).get("current_query") or "")
        mode = "execution_first" if "too much" in message.lower() else "balanced"
        state.context_data["dual_core_decision"] = {
            "mode": mode,
            "reason": "test dual-core routing",
        }
        state.context_data["dual_core_prompt_instruction"] = (
            "优先降低负荷，再推进下一步。"
            if mode == "execution_first"
            else "优先校准理解，再给最小下一步。"
        )
        return route_decision

    async def _fake_route_and_classify(*, user_message, **kwargs):
        del kwargs
        if "怎么选" in user_message or "choose" in user_message.lower():
            intent = "decision"
        elif "笔记" in user_message:
            intent = "knowledge"
        else:
            intent = "chat"
        return (
            RouteDecision(execution_mode="direct", reason=f"test_intent:{intent}", risk_level="low", confidence=0.86),
            SimpleNamespace(
                primary_intent=SimpleNamespace(value=intent),
                confidence=0.86,
                context_signals={},
            ),
        )

    async def _fake_plan_and_validate(**kwargs):
        return (
            kwargs["route_decision"],
            ExecutablePlan(
                rationale="test orchestrator plan",
                confidence=0.86,
                collaboration_mode="single",
                tool_calls=[],
            ),
            None,
            False,
        )

    captures: list[dict[str, object]] = []

    async def _fake_execute_graph(*, state, user_id, queue, result_holder):
        del user_id, queue
        user_context = deepcopy(state.context_data.get("user_context") or {})
        prompt_context_focus = deepcopy(state.context_data.get("context_focus") or {})
        if isinstance(prompt_context_focus, dict):
            prompt_context_focus.setdefault("section_weights", {})
        prompt = build_system_prompt(
            user_context,
            conversation_history=state.context_data.get("conversation_context"),
            prompt_version=str(state.context_data.get("prompt_version") or "v1"),
            plan_context=state.context_data.get("plan_context"),
            session_feedback_instruction=str(state.context_data.get("session_feedback_instruction") or ""),
            dual_core_instruction=str(state.context_data.get("dual_core_prompt_instruction") or ""),
            context_focus=prompt_context_focus,
            context_briefing_note=str(state.context_data.get("context_briefing_note") or ""),
            chat_mode=str(state.context_data.get("chat_mode") or "standard"),
        )
        decision_context = user_context.get("residual_decision_context") or {}
        grounding = user_context.get("user_material_grounding") or {}
        results = grounding.get("results") or []
        snippet = str(results[0].get("snippet") or "").strip() if results else ""
        experience_mode = str(decision_context.get("experience_mode") or "").strip()
        if experience_mode == "explain":
            response = (
                f"先用你的笔记校准：{snippet} "
                "所以这题先定系统边界，再看不可逆过程是不是主导项。"
            )
        elif experience_mode == "stabilize":
            response = "先不扩展内容。把任务压到 5 分钟：只打开热力学笔记第 12 页，圈出系统边界。"
        elif experience_mode == "decide":
            response = "先别急着二选一。你真正该看的标准是：哪条路更能修复当前最关键的误解、哪条更能在这周稳住节奏。"
        elif experience_mode == "reframe":
            response = "先别把这件事解释成“你就是不行”。证据更像是：你已经能重新启动，只是现在还在一个脆弱窗口里。"
        else:
            response = "下一步最稳：按“先定系统边界，再看不可逆过程”做 1 道判断题，做完再回来告诉我哪里还卡。"

        final_state = state.clone()
        final_state.append_message("assistant", response)
        final_state.context_data["generation_model_key"] = "test-model"
        final_state.context_data["conversation_context"] = state.context_data.get("conversation_context")
        final_state.context_data["user_context"] = user_context
        if isinstance(user_context.get("situation_brief"), dict):
            final_state.context_data["situation_brief"] = user_context["situation_brief"]
        if isinstance(user_context.get("user_strategy_state"), dict):
            final_state.context_data["user_strategy_state"] = user_context["user_strategy_state"]
        captures.append(
            {
                "user_message": str(user_context.get("current_query") or ""),
                "prompt": prompt,
                "user_context": user_context,
                "response": response,
            }
        )
        result_holder["final_state"] = final_state
        if False:
            yield agent_service_pb2.ChatResponse()

    orchestrator._build_full_context = AsyncMock(side_effect=_fake_build_full_context)
    orchestrator._attach_active_intervention_state = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._hydrate_companion_runtime_context = AsyncMock(return_value={})
    orchestrator._attach_user_strategy_state = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._attach_situation_brief = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._apply_context_focus_overlay = AsyncMock(side_effect=_fake_apply_context_focus_overlay)
    orchestrator._apply_dual_core_routing = AsyncMock(side_effect=_fake_apply_dual_core_routing)
    orchestrator._route_and_classify = AsyncMock(side_effect=_fake_route_and_classify)
    orchestrator._plan_and_validate = AsyncMock(side_effect=_fake_plan_and_validate)
    orchestrator._execute_graph = _fake_execute_graph

    session_id = f"phase5-orchestrator-{uuid.uuid4()}"
    followup_session_id = f"phase5-orchestrator-followup-{uuid.uuid4()}"
    history: list[agent_service_pb2.ChatMessage] = []
    turn_messages = [
        "用我上传的热力学笔记解释熵增方向判断。",
        "This is too much and I still cannot start.",
        "这样轻一点我就能开始了，下一步怎么做最稳？",
        "I started the lighter step yesterday. How should I choose between proof review and past-paper drills next?",
        "我是不是根本就不是能学好热力学的那种人？",
    ]
    turn_session_ids = [
        session_id,
        session_id,
        session_id,
        followup_session_id,
        followup_session_id,
    ]
    final_responses: list[agent_service_pb2.ChatResponse] = []

    for index, message in enumerate(turn_messages):
        request = _make_request(
            user_id=str(user.id),
            session_id=turn_session_ids[index],
            message=message,
            history=history,
            file_ids=[str(fake_file.id)] if index == 0 else [],
        )
        responses = await _collect(orchestrator, request, db_session)
        final_response = responses[-1]
        final_responses.append(final_response)
        history.extend(
            [
                agent_service_pb2.ChatMessage(role="user", content=message),
                agent_service_pb2.ChatMessage(role="assistant", content=final_response.full_text),
            ]
        )

    await db_session.refresh(intervention)

    turn1_capture, turn2_capture, turn3_capture, turn4_capture, turn5_capture = captures
    turn1_decision = json.loads(final_responses[0].metadata["residual_decision_context"])
    turn2_decision = json.loads(final_responses[1].metadata["residual_decision_context"])
    turn3_decision = json.loads(final_responses[2].metadata["residual_decision_context"])
    turn4_decision = json.loads(final_responses[3].metadata["residual_decision_context"])
    turn5_decision = json.loads(final_responses[4].metadata["residual_decision_context"])
    turn3_runtime = (turn3_capture["user_context"] or {}).get("experience_phase_runtime") or {}
    current_runtime = {
        "effective_companion_state": deepcopy(turn5_capture["user_context"].get("effective_companion_state") or {}),
        "recent_revisions": deepcopy(turn5_capture["user_context"].get("companion_state_recent_revisions") or []),
    }
    previous_runtime = {
        "effective_companion_state": deepcopy(turn1_capture["user_context"].get("effective_companion_state") or {}),
        "recent_revisions": deepcopy(turn1_capture["user_context"].get("companion_state_recent_revisions") or []),
    }

    assert "## 当前决策策略 [L1 引导]" in str(turn1_capture["prompt"])
    assert "## 用户材料依据 [L1 证据]" in str(turn1_capture["prompt"])
    assert "先确定系统边界" in str(turn1_capture["prompt"])
    assert turn1_decision["primary_residual"] == "R_e"
    assert turn1_decision["loop_type"] == "truth_seeking"
    assert turn1_decision["experience_mode"] == "explain"
    assert turn1_capture["user_context"]["user_material_grounding"]["status"] == "grounded"
    assert "先定系统边界" in final_responses[0].full_text

    assert turn2_decision["primary_residual"] == "R_c"
    assert turn2_decision["experience_mode"] == "stabilize"
    assert "load_shedding" in str(turn2_capture["prompt"])
    assert "5 分钟" in final_responses[1].full_text

    assert turn3_decision["primary_residual"] == "R_c"
    assert turn3_decision["experience_mode"] == "mobilize"
    assert turn3_runtime["auto_feedback_binding"]["bound"] is True
    assert intervention.acceptance_status == InterventionAcceptanceStatus.ACTED
    assert "下一步最稳" in final_responses[2].full_text

    assert turn4_decision["primary_residual"] == "R_n"
    assert turn4_decision["experience_mode"] == "decide"
    assert "真正该看的标准" in final_responses[3].full_text
    assert final_responses[3].metadata["session_id"] == followup_session_id
    assert "继续当前节奏" in final_responses[3].metadata["continuity_banner"]

    assert turn5_decision["primary_residual"] == "R_i"
    assert turn5_decision["experience_mode"] == "reframe"
    assert "你已经能重新启动" in final_responses[4].full_text

    turns = [
        {
            "expected_residual": "R_e",
            "expected_loop_type": "truth_seeking",
            "expected_mode": "explain",
            "expected_grounding": "user_materials",
            "decision_context": turn1_capture["user_context"]["residual_decision_context"],
            "auto_strategy_adjustments": (
                (turn1_capture["user_context"].get("experience_phase_runtime") or {}).get("auto_strategy_adjustments", [])
            ),
            "user_material_grounding": turn1_capture["user_context"]["user_material_grounding"],
            "user_signal": "clearer" if "先定系统边界" in final_responses[0].full_text else "unclear",
            "freedom_preservation": 0.9,
        },
        {
            "expected_residual": "R_c",
            "expected_loop_type": "truth_seeking",
            "expected_mode": "stabilize",
            "decision_context": turn2_capture["user_context"]["residual_decision_context"],
            "auto_strategy_adjustments": (
                (turn2_capture["user_context"].get("experience_phase_runtime") or {}).get("auto_strategy_adjustments", [])
            ),
            "user_signal": "accepted" if "这样轻一点我就能开始了" in turn_messages[2] else "still_stuck",
            "freedom_preservation": 0.9,
        },
        {
            "expected_residual": "R_c",
            "expected_loop_type": "truth_seeking",
            "expected_mode": "mobilize",
            "decision_context": turn3_capture["user_context"]["residual_decision_context"],
            "active_interventions": turn3_capture["user_context"].get("active_interventions", []),
            "auto_feedback_binding": turn3_runtime.get("auto_feedback_binding", {}),
            "user_signal": "started" if turn3_runtime.get("auto_feedback_binding", {}).get("bound") else "hesitant",
            "freedom_preservation": 0.91,
        },
        {
            "expected_residual": "R_n",
            "expected_loop_type": "normative",
            "expected_mode": "decide",
            "decision_context": turn4_capture["user_context"]["residual_decision_context"],
            "user_signal": "criteria_clearer" if "标准" in final_responses[3].full_text else "unclear",
            "freedom_preservation": 0.94,
        },
        {
            "expected_residual": "R_i",
            "expected_loop_type": "identity_repair",
            "expected_mode": "reframe",
            "decision_context": turn5_capture["user_context"]["residual_decision_context"],
            "user_signal": "more_grounded" if "证据更像是" in final_responses[4].full_text else "self_negating",
            "freedom_preservation": 0.95,
        },
    ]
    report = ExperiencePhaseEvaluator().evaluate(
        scenario_id="thermo_phase5_orchestrator_journey",
        turns=turns,
        outcomes={
            "misconception_reduction": (
                1.0
                if turn1_capture["user_context"]["user_material_grounding"]["status"] == "grounded"
                and "先定系统边界" in final_responses[0].full_text
                else 0.0
            ),
            "task_execution": (
                1.0
                if turn3_runtime.get("auto_feedback_binding", {}).get("bound")
                and "下一步最稳" in final_responses[2].full_text
                else 0.0
            ),
            "consistency": (
                1.0
                if [
                    turn1_decision["experience_mode"],
                    turn2_decision["experience_mode"],
                    turn3_decision["experience_mode"],
                    turn4_decision["experience_mode"],
                    turn5_decision["experience_mode"],
                ]
                == ["explain", "stabilize", "mobilize", "decide", "reframe"]
                else 0.0
            ),
            "real_world_performance": (
                0.9
                if intervention.acceptance_status == InterventionAcceptanceStatus.ACTED
                and turn1_capture["user_context"]["user_material_grounding"]["status"] == "grounded"
                and turn4_decision["primary_residual"] == "R_n"
                and turn5_decision["primary_residual"] == "R_i"
                else 0.25
            ),
        },
        current_runtime=current_runtime,
        previous_runtime=previous_runtime,
        drift_outcomes={
            "residual_resolution": (
                1.0
                if [
                    turn1_decision["primary_residual"],
                    turn2_decision["primary_residual"],
                    turn3_decision["primary_residual"],
                    turn4_decision["primary_residual"],
                    turn5_decision["primary_residual"],
                ]
                == ["R_e", "R_c", "R_c", "R_n", "R_i"]
                else 0.5
            ),
            "leap_support": (
                1.0
                if turn3_runtime.get("auto_feedback_binding", {}).get("bound")
                and "下一步最稳" in final_responses[2].full_text
                else 0.5
            ),
            "freedom_preservation": round(mean(turn["freedom_preservation"] for turn in turns), 4),
            "felt_understanding": (
                1.0
                if all(
                    turn["user_signal"]
                    in {"clearer", "accepted", "started", "criteria_clearer", "more_grounded"}
                    for turn in turns
                )
                else 0.5
            ),
        },
    )

    assert report.overall_scores["outcome_average"] >= 0.9
    assert report.overall_scores["experience_average"] >= 0.72
    assert report.overall_scores["intelligence_average"] >= 0.9
    assert report.intelligence_scorecard["grounded_evidence_use"].score == 1.0
    assert report.experience_scorecard["real_change"].score >= 0.6
    assert report.experience_scorecard["continuity_and_trust"].score >= 0.5
    assert report.supporting_metrics["turn_count"] == 5
    assert report.recommendation == "accept"
