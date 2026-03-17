"""
ChatOrchestrator — Modular orchestration engine for Sparkle AI.

This module is the central coordinator composed from specialized mixins:
  - ContextBuilderMixin: User/session context assembly
  - RoutingEngineMixin: Intent routing and dual-core decisions
  - ValidationEngineMixin: Request/plan validation gates
  - SessionStateMixin: Session state, feedback, and version management
  - ExecutionEngineMixin: Tool execution, planning, multi-agent workflows
  - ResponseBuilderMixin: Final response composition
  - PersistenceLayerMixin: DB persistence and feedback recording
  - ObservabilityMixin: Tracing, logging, and metrics streaming
"""
import asyncio
import contextlib
import hashlib
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from google.protobuf import struct_pb2  # noqa: F401 — kept for backward compat
from google.protobuf.json_format import MessageToDict  # noqa: F401
from loguru import logger
from opentelemetry import trace
from sqlalchemy import and_, asc, desc, func, select  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.standard_workflow import create_standard_chat_graph
from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.config import settings
from app.core.business_metrics import (  # noqa: F401
    COLLABORATION_LATENCY,
    COLLABORATION_SUCCESS,
    CONTEXT_FOCUS_DECISION_TOTAL,
    EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL,
    HITL_REQUESTED,
)
from app.core.metrics import (
    ACTIVE_SESSIONS,
    ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL,  # noqa: F401
    REQUEST_COUNT,
    REQUEST_LATENCY,  # noqa: F401
    RESPONSE_FALLBACK_GENERATED_TOTAL,  # noqa: F401
    ROUTING_SUMMARY_CONTEXT_TOTAL,  # noqa: F401
    SESSION_FEEDBACK_APPLIED_TOTAL,  # noqa: F401
    SESSION_FEEDBACK_CONFIDENCE_BUCKET,  # noqa: F401
    SESSION_FEEDBACK_DETECTED_TOTAL,  # noqa: F401
    SESSION_FEEDBACK_IGNORED_TOTAL,  # noqa: F401
    SESSION_FEEDBACK_VISIBLE_HINT_TOTAL,  # noqa: F401
    TOKEN_USAGE,  # noqa: F401
)
from app.core.pending_actions import pending_actions_store  # noqa: F401
from app.core.task_manager import task_manager  # noqa: F401
from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType  # noqa: F401
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, ChatSession, MessageRole  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.cognitive import CognitiveFragment  # noqa: F401
from app.models.galaxy import KnowledgeNode  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.task import TaskStatus as ModelTaskStatus  # noqa: F401
from app.models.task_feedback import TaskFeedback  # noqa: F401

# Phase 3: Circuit Breaker, Observability, Shadow Mode
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
from app.orchestration.composer import ResponseComposer
from app.orchestration.context_focus import (  # noqa: F401
    FocusedContextAssembler,
    infer_route_intent_from_chat_mode,
)
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router  # noqa: F401
from app.orchestration.executor import ToolExecutor
from app.orchestration.goal_quality_evaluator import goal_quality_evaluator  # noqa: F401
from app.orchestration.grounding_validator import GroundingValidator
from app.orchestration.lang_graph_planner import LangGraphPlanner

# Multi-Agent Mode Support
from app.orchestration.chat_modes import (
    CHAT_MODE_STANDARD,
    is_expert_chat_mode,
    normalize_chat_mode,
)
from app.orchestration.expert_strategy import ExpertStrategyV1
from app.orchestration.mode_workflow_config import get_mode_strategy, get_workflow_config  # noqa: F401
from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter, execute_multi_agent_workflow  # noqa: F401
from app.orchestration.agent_memory import AgentMemoryService  # noqa: F401
from app.orchestration.agent_scoring import AgentScoringService  # noqa: F401
from app.orchestration.orchestration_trace import OrchestrationTrace
from app.orchestration.persona_aware_planner import PersonaAwarePlanner  # noqa: F401
from app.orchestration.observability_logger import observability_logger
from app.orchestration.plan_review_service import ReviewDecision, plan_review_service  # noqa: F401
from app.orchestration.session_feedback import (
    SESSION_FEEDBACK_TTL_SECONDS,  # noqa: F401
    SessionAdaptationContext,  # noqa: F401
    SessionFeedbackSignal,
    analyze_conversation_rhythm,  # noqa: F401
    apply_session_feedback_visible_prefix,  # noqa: F401
    build_conversation_rhythm_instruction,
    build_session_adaptation_context,  # noqa: F401
    build_session_feedback_instruction,
    detect_session_feedback_signal,  # noqa: F401
)

# Phase 1 & Phase 2: Full-Loop Closed System with LangGraph Planner
from app.orchestration.route_adapter import to_route_decision  # noqa: F401
from app.orchestration.schemas import (
    ExecutablePlan,  # noqa: F401
    RouteDecision,  # noqa: F401
    StateSnapshot,  # noqa: F401
)
from app.orchestration.state_manager import SessionStateManager
from app.orchestration.state_snapshot import StateSnapshotManager
from app.orchestration.statechart_engine import WorkflowState

# Phase 4: Sufficiency Checking
from app.orchestration.sufficiency_checker import SufficiencyStatus, sufficiency_checker  # noqa: F401
from app.orchestration.token_tracker import TokenTracker

# Phase 5: Plan Execution Validation
from app.orchestration.tool_result_extractor import ToolResultExtractor  # noqa: F401
from app.orchestration.transparency_data_generator import StepType, TransparencyDataGenerator  # noqa: F401
from app.orchestration.ux_envelope import ux_envelope_builder  # noqa: F401
from app.orchestration.validator import RequestValidator
from app.routing.tool_preference_router import ToolPreferenceRouter  # noqa: F401
from app.services.chat_signal_collector import ChatSignalCollector
from app.services.focus_service import focus_service  # noqa: F401
from app.services.llm_service import llm_service  # noqa: F401
from app.services.plan_progress_service import PlanProgressService  # noqa: F401
from app.services.progress_narrative_service import ProgressNarrativeService  # noqa: F401
from app.services.plan_execution_record_service import PlanExecutionRecordService  # noqa: F401
from app.services.plan_execution_validator import PlanExecutionValidator  # noqa: F401
from app.services.perceptible_intelligence_service import (  # noqa: F401
    PerceptibleInsightService,
    ProgressComparisonService,
)
from app.services.self_evolution_service import UnderstandingDepthService  # noqa: F401
from app.services.shadow_prediction_service import shadow_prediction_service
from app.services.system_update_service import SystemUpdateService, build_system_update  # noqa: F401
from app.services.user_service import UserService  # noqa: F401

# ---------------------------------------------------------------------------
# Mixin imports
# ---------------------------------------------------------------------------
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.routing_engine import RoutingEngineMixin
from app.orchestration.validation_engine import ValidationEngineMixin
from app.orchestration.session_state_mixin import SessionStateMixin
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.response_builder import ResponseBuilderMixin
from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.orchestration.observability_mixin import ObservabilityMixin

# ---------------------------------------------------------------------------
# Constants (exported for backward compatibility)
# ---------------------------------------------------------------------------

# FSM States
STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"

CONTEXT_VERSION_KEY_PREFIX = "user:context:versions:"
CONTEXT_VERSION_TTL_SECONDS = 6 * 60 * 60
REALTIME_VERSION_DOMAINS = ("tasks", "plans", "focus", "progress", "prefs")
SESSION_FEEDBACK_KEY_PREFIX = "session:feedback:"


# ---------------------------------------------------------------------------
# Standalone helpers (exported for backward compatibility)
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_agent_type_for_tool(tool_name: str) -> int:
    """
    Map tool names to AgentType enum for multi-agent visualization.

    Returns:
        AgentType enum value (int)
    """
    tool_lower = tool_name.lower()

    # Knowledge-related tools -> KNOWLEDGE agent
    if any(keyword in tool_lower for keyword in ['knowledge', 'query', 'search', 'retrieve', 'vector', 'graphrag']):
        return agent_service_pb2.KNOWLEDGE

    # Math/calculation tools -> MATH agent
    if any(keyword in tool_lower for keyword in ['math', 'calculate', 'wolfram', 'compute', 'formula', 'equation']):
        return agent_service_pb2.MATH

    # Code/system tools -> CODE agent
    if any(keyword in tool_lower for keyword in ['code', 'execute', 'run', 'system', 'debug', 'compile']):
        return agent_service_pb2.CODE

    # Data analysis tools -> DATA_ANALYSIS agent
    if any(keyword in tool_lower for keyword in ['data', 'analyze', 'statistic', 'chart', 'plot', 'visualize', 'pandas', 'numpy']):
        return agent_service_pb2.DATA_ANALYSIS

    # Translation tools -> TRANSLATION agent
    if any(keyword in tool_lower for keyword in ['translate', 'language', 'localize', 'i18n']):
        return agent_service_pb2.TRANSLATION

    # Image tools -> IMAGE agent
    if any(keyword in tool_lower for keyword in ['image', 'photo', 'picture', 'draw', 'generate_image', 'edit_image']):
        return agent_service_pb2.IMAGE

    # Audio tools -> AUDIO agent
    if any(keyword in tool_lower for keyword in ['audio', 'sound', 'music', 'speech', 'voice', 'tts', 'stt']):
        return agent_service_pb2.AUDIO

    # Writing/content tools -> WRITING agent
    if any(keyword in tool_lower for keyword in ['write', 'summarize', 'compose', 'draft', 'edit_text']):
        return agent_service_pb2.WRITING

    # Reasoning/logic tools -> REASONING agent
    if any(keyword in tool_lower for keyword in ['reason', 'logic', 'solve', 'deduce', 'infer', 'prove']):
        return agent_service_pb2.REASONING

    # Task/orchestration tools -> ORCHESTRATOR
    if any(keyword in tool_lower for keyword in ['task', 'plan', 'create', 'update', 'batch', 'orchestrate', 'focus', 'pomodoro']):
        return agent_service_pb2.ORCHESTRATOR

    # Default to ORCHESTRATOR
    return agent_service_pb2.ORCHESTRATOR


# ---------------------------------------------------------------------------
# ChatOrchestrator — composed from mixins
# ---------------------------------------------------------------------------

class ChatOrchestrator(
    ContextBuilderMixin,
    RoutingEngineMixin,
    ValidationEngineMixin,
    SessionStateMixin,
    ExecutionEngineMixin,
    ResponseBuilderMixin,
    PersistenceLayerMixin,
    ObservabilityMixin,
):
    """
    Enhanced ChatOrchestrator with production-ready features:
    1. Redis-based session state persistence
    2. Dynamic tool registry
    3. User context integration
    4. Request validation
    5. Idempotency support
    6. Response composition
    """

    def __init__(self, db_session: AsyncSession | None = None, redis_client=None, user_id: str | None = None):
        if redis_client is None:
            logger.error("ChatOrchestrator requires Redis, but no redis_client was provided")
            raise ValueError("redis_client is required for ChatOrchestrator")
        self.db_session = db_session
        self.redis = redis_client
        self.redis_client = redis_client
        self.user_id = user_id
        self._bg_tasks: set[asyncio.Task] = set()

        # Initialize components
        self.state_manager = SessionStateManager(redis_client)
        self.validator = RequestValidator(redis_client, daily_quota=100000)
        self.tool_executor = ToolExecutor()
        self.response_composer = ResponseComposer()
        self.dual_core_router = dual_core_router

        # Initialize ContextPruner (P0 feature)
        self.context_pruner = None
        self.token_tracker = None
        self.context_pruner = ContextPruner(
            redis_client=redis_client,
            max_history_messages=10,      # 保留最近10轮对话
            summary_threshold=20,         # 超过20轮触发总结
            summary_cache_ttl=3600        # 总结缓存1小时
        )

        # Initialize TokenTracker (P1 feature)
        self.token_tracker = TokenTracker(redis_client)

        logger.info("ChatOrchestrator initialized with ContextPruner and TokenTracker")

        # Initialize tool registry (auto-discover tools)
        logger.info("ChatOrchestrator initialized with all components")

        # Initialize State Graph
        self.graph = create_standard_chat_graph()

        # Connect Checkpointer
        self.graph.checkpointer = RedisCheckpointer(redis_client)

        # Connect Visualizer and Tracer
        from app.visualization.execution_tracer import ExecutionTracer
        from app.visualization.realtime_visualizer import visualizer

        self.tracer = ExecutionTracer(redis_client)

        self.graph.on_event = self._chain_event_handlers(
            visualizer.on_graph_event,
            self.tracer.record_event
        )

        # Phase 1: Initialize new components
        self.grounding_validator = GroundingValidator(redis_client)

        # Unified Intent Router (Fix #1): 统一功能入口路由
        self.unified_router = UnifiedIntentRouter(
            redis_client=redis_client,
            llm_service=llm_service,
            context_window_size=5
        )
        logger.info("ChatOrchestrator initialized with GroundingValidator and UnifiedIntentRouter")

        # Phase 2: Initialize LangGraph Planner and Snapshot Manager
        self.lang_graph_planner = LangGraphPlanner(redis_client)
        self.snapshot_manager = StateSnapshotManager(redis_client)
        logger.info("ChatOrchestrator initialized with LangGraphPlanner and StateSnapshotManager")

        # Phase 3: Initialize Circuit Breaker
        self.langgraph_breaker = CircuitBreaker(
            name="langgraph_planner",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_ms=60000,
                failure_rate_threshold=0.5
            ),
            redis_client=redis_client
        )
        circuit_breaker_registry.register(self.langgraph_breaker)
        self._track_task(asyncio.create_task(self.langgraph_breaker.initialize()))

        # Phase 3: Observability
        self.observability = observability_logger
        self.observability.redis = redis_client

        # Phase 3: Shadow Mode
        self.shadow_predictor = shadow_prediction_service
        self.shadow_predictor.redis = redis_client

        # Plan Review Service
        plan_review_service.set_redis(redis_client)

        # Phase 3: Version Conflict Service (P1 enhancement)
        from app.orchestration.version_conflict_service import VersionConflictService
        self.version_conflict_service = VersionConflictService(
            redis=redis_client,
            planner=self.lang_graph_planner,
        )

        logger.info("ChatOrchestrator initialized with Phase 3 components: CircuitBreaker, Observability, ShadowMode, PlanReview, VersionConflict")

        # Ensure tools are registered
        self._ensure_tools_registered()
        self.multi_agent_adapter = MultiAgentWorkflowAdapter(self)

    def _coerce_session_uuid(self, session_id: str) -> uuid.UUID:
        raw = str(session_id).strip()
        try:
            return uuid.UUID(raw)
        except Exception:
            return uuid.uuid5(uuid.NAMESPACE_URL, f"sparkle-session:{raw}")

    @staticmethod
    def _experiment_cohort_for_user(user_id: str | None) -> str | None:
        raw = str(user_id or "").strip()
        if not raw:
            return None
        bucket = int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16) % 3
        return ("A", "B", "C")[bucket]

    @staticmethod
    def _apply_cohort_to_session_feedback_signal(
        signal: SessionFeedbackSignal | None,
        experiment_cohort: str | None,
    ) -> SessionFeedbackSignal | None:
        if signal is None or str(experiment_cohort or "") != "B":
            return signal
        stronger_hints = {
            "simplify": "好，我直接说最关键的：",
            "expand": "我按更完整的脉络展开说：",
            "mismatch": "我先对准你真正要问的点：",
        }
        stronger_hint = stronger_hints.get(signal.signal_type)
        if not stronger_hint:
            return signal
        return SessionFeedbackSignal(
            signal_type=signal.signal_type,
            confidence=signal.confidence,
            trigger_text=signal.trigger_text,
            applies_adaptation=signal.applies_adaptation,
            visible_hint=signal.visible_hint,
            transition_hint=stronger_hint,
        )

    def _track_task(self, task: asyncio.Task) -> None:
        """Track background tasks for graceful shutdown."""
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def shutdown(self) -> None:
        """Cancel background tasks started by the orchestrator."""
        for task in list(self._bg_tasks):
            task.cancel()
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()

    def _chain_event_handlers(self, *handlers):
        """Chain multiple event handlers"""
        async def chained(event):
            for handler in handlers:
                await handler(event)
        return chained

    def _ensure_tools_registered(self):
        """Ensure tools are registered in the registry"""
        try:
            # Check if tools are already registered
            if len(dynamic_tool_registry.get_all_tools()) == 0:
                # Auto-discover tools from app.tools package
                dynamic_tool_registry.register_from_package("app.tools")
                logger.info(f"Auto-registered {len(dynamic_tool_registry.get_all_tools())} tools")

            # Fix 3: 刷新 validator allowlist（与工具注册联动）
            if self.grounding_validator:
                self.grounding_validator.refresh_allowlist()
                logger.info("GroundingValidator allowlist refreshed after tool registration")
        except Exception as e:
            logger.warning(f"Tool registration failed: {e}")

    # -----------------------------------------------------------------------
    # process_stream — main entry point (delegates to mixin methods)
    # -----------------------------------------------------------------------

    async def process_stream(
        self,
        request: agent_service_pb2.ChatRequest,
        db_session: AsyncSession | None = None,
        context_data: dict[str, Any] | None = None
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """Coordinator: orchestrate chat request through validation, routing,
        planning, execution, and response composition."""
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("orchestrator.process_stream") as span:
            span.set_attribute("session_id", request.session_id)
            span.set_attribute("user_id", request.user_id)
            span.set_attribute("request_id", request.request_id)
            trace_id = format(span.get_span_context().trace_id, "032x")

            start_time = time.time()
            ACTIVE_SESSIONS.inc()
            request_id = request.request_id
            session_id = request.session_id
            user_id = request.user_id
            response_id = str(uuid.uuid4())
            workflow_id = (context_data or {}).get("workflow_id", "standard_chat")
            prompt_version = (context_data or {}).get("prompt_version", "v1")
            active_db = db_session or self.db_session

            # Step 1: Validation & idempotency (early exits)
            with tracer.start_as_current_span("orchestrator.validate_request"):
                if validation_error := await self._validate_request(request, response_id=response_id, request_id=request_id):
                    yield validation_error
                    return
            with tracer.start_as_current_span("orchestrator.check_idempotency"):
                if cached_resp := await self._check_idempotency_response(session_id=session_id, request_id=request_id, response_id=response_id):
                    yield cached_resp
                    return

            lock_acquired = False
            lock_renewal_task: asyncio.Task | None = None
            lock_renewal_stop: asyncio.Event | None = None
            total_prompt_tokens = 0
            total_completion_tokens = 0
            transparency_generator: TransparencyDataGenerator | None = None
            emit_transparency_event = None

            try:
                # Step 2: Distributed lock
                with tracer.start_as_current_span("redis.acquire_lock"):
                    lock_acquired = await self._acquire_session_lock(session_id, request_id)
                if not lock_acquired:
                    yield agent_service_pb2.ChatResponse(
                        response_id=response_id, created_at=int(datetime.now().timestamp()), request_id=request_id,
                        error=agent_service_pb2.Error(message="会话正在处理另一个请求，请稍候", retryable=True, error_code=agent_service_pb2.ERROR_CODE_CONFLICT),
                        finish_reason=agent_service_pb2.ERROR,
                    )
                    return
                lock_renewal_task, lock_renewal_stop = await self.state_manager.start_lock_renewal(session_id, request_id, interval=10.0)

                # Step 3: Initialize state & extract message
                await self._update_state(session_id, STATE_INIT, f"Request {request_id}")
                chat_mode = normalize_chat_mode(request.chat_mode or CHAT_MODE_STANDARD)
                user_message = request.message or ""

                # Step 4: Build full context
                grpc_context, plan_id, plan_switched, user_context_payload, conversation_context, plan_context = \
                    await self._build_full_context(request=request, active_db=active_db, user_id=user_id, session_id=session_id, user_message=user_message, request_id=request_id, tracer=tracer)
                conversation_context = self._merge_request_history_into_conversation_context(
                    conversation_context,
                    list(request.history),
                )

                session_feedback_signal = None
                session_adaptation_context = None
                conversation_rhythm = None
                if not request.HasField("tool_result"):
                    session_feedback_signal, session_adaptation_context, conversation_rhythm = await self._detect_session_feedback(
                        session_id=session_id,
                        user_message=user_message,
                        conversation_context=conversation_context,
                    )
                session_feedback_signal = self._apply_cohort_to_session_feedback_signal(
                    session_feedback_signal,
                    (user_context_payload or {}).get("experiment_cohort") if isinstance(user_context_payload, dict) else None,
                )

                expert_routing_decision = None
                if settings.ENABLE_EXPERT_STRATEGY_V1 and is_expert_chat_mode(chat_mode):
                    user_preferences = (user_context_payload or {}).get("preferences", {})
                    expert_routing_decision = ExpertStrategyV1.route(
                        message=user_message,
                        chat_mode=chat_mode,
                        user_preferences=user_preferences if isinstance(user_preferences, dict) else {},
                    )
                    for expert_id in expert_routing_decision.selected_experts:
                        await self.observability.log_expert_selected(
                            user_id=user_id,
                            session_id=session_id,
                            expert_id=expert_id,
                            strategy=expert_routing_decision.routing_strategy,
                            entry_source=expert_routing_decision.expert_entry_source,
                            workflow_id=workflow_id,
                        )
                        await self.observability.log_expert_invoked(
                            user_id=user_id,
                            session_id=session_id,
                            expert_id=expert_id,
                            workflow_id=workflow_id,
                        )
                    if expert_routing_decision.fallback_reason:
                        await self.observability.log_expert_fallback(
                            user_id=user_id,
                            session_id=session_id,
                            reason=expert_routing_decision.fallback_reason,
                            from_mode=chat_mode,
                            workflow_id=workflow_id,
                        )

                state = WorkflowState()
                if user_message:
                    state.append_message("user", user_message)
                if session_feedback_signal is not None:
                    state.context_data["session_feedback_signal"] = session_feedback_signal.to_dict()
                    session_feedback_instruction = build_session_feedback_instruction(session_feedback_signal)
                    rhythm_instruction = build_conversation_rhythm_instruction(conversation_rhythm)
                    combined_instruction = "\n\n".join(
                        part for part in (session_feedback_instruction, rhythm_instruction) if part
                    )
                    if combined_instruction:
                        state.context_data["session_feedback_instruction"] = combined_instruction
                elif conversation_rhythm is not None:
                    rhythm_instruction = build_conversation_rhythm_instruction(conversation_rhythm)
                    if rhythm_instruction:
                        state.context_data["session_feedback_instruction"] = rhythm_instruction
                if session_adaptation_context is not None:
                    state.context_data["session_adaptation"] = session_adaptation_context.to_dict()
                if conversation_rhythm is not None:
                    state.context_data["conversation_rhythm"] = conversation_rhythm
                queue: asyncio.Queue = asyncio.Queue()

                async def stream_callback(resp: agent_service_pb2.ChatResponse):
                    resp.response_id = response_id
                    resp.created_at = int(datetime.now().timestamp())
                    resp.request_id = request_id
                    resp.workflow_id = resp.workflow_id or workflow_id
                    resp.prompt_version = resp.prompt_version or prompt_version
                    resp.trace_id = resp.trace_id or trace_id
                    await queue.put(resp)

                # Step 4.5: Proactively emit unread evolution/system updates at session start
                await self._maybe_enqueue_perceptible_insight(
                    active_db=active_db,
                    user_id=user_id,
                    user_message=user_message,
                    user_context_payload=user_context_payload,
                    plan_id=plan_id,
                    session_feedback_signal=session_feedback_signal.to_dict() if session_feedback_signal else None,
                    session_id=session_id,
                )
                await self._maybe_enqueue_understanding_depth(
                    active_db=active_db,
                    user_id=user_id,
                )
                (
                    update_responses,
                    adaptation_records,
                    preference_learnings,
                    evolution_highlights,
                    progress_snapshot,
                    understanding_depth_update,
                ) = await self._drain_system_updates(user_id)
                if adaptation_records:
                    state.context_data["adaptation_records"] = adaptation_records
                if preference_learnings:
                    state.context_data["preference_learnings"] = preference_learnings
                if evolution_highlights:
                    state.context_data["evolution_highlights"] = evolution_highlights
                if progress_snapshot:
                    state.context_data["progress_snapshot"] = progress_snapshot
                if isinstance(understanding_depth_update, dict):
                    state.context_data["understanding_depth_update"] = understanding_depth_update
                    if isinstance(user_context_payload, dict):
                        user_context_payload["understanding_depth_hint"] = {
                            "natural_hint": str(understanding_depth_update.get("natural_hint") or "").strip(),
                            "description": str(understanding_depth_update.get("description") or "").strip(),
                            "level": (
                                (understanding_depth_update.get("understanding_depth") or {}).get("level")
                                if isinstance(understanding_depth_update.get("understanding_depth"), dict)
                                else None
                            ),
                        }
                for update_resp in update_responses:
                    yield update_resp

                # Step 5: Sufficiency check (may short-circuit)
                with tracer.start_as_current_span("orchestrator.sufficiency_check"):
                    sufficiency_handled, intent_type = await self._check_sufficiency(
                        request=request,
                        user_message=user_message,
                        user_id=user_id,
                        plan_id=plan_id,
                        conversation_context=conversation_context,
                        stream_callback=stream_callback,
                        queue=queue,
                    )
                    if sufficiency_handled:
                        async for queued in self._drain_queue(queue):
                            yield queued
                        return
                with tracer.start_as_current_span("orchestrator.goal_quality_check"):
                    if await self._check_goal_quality(
                        intent_type=intent_type,
                        user_message=user_message,
                        user_id=user_id,
                        plan_id=plan_id,
                        active_db=active_db,
                        conversation_context=conversation_context,
                        stream_callback=stream_callback,
                        state=state,
                    ):
                        async for queued in self._drain_queue(queue):
                            yield queued
                        return

                if chat_mode != CHAT_MODE_STANDARD and not settings.ENABLE_UNIFIED_GRAPH_ROUTING:
                    user_context_payload = await self._apply_context_focus_overlay(
                        active_db=active_db,
                        user_id=user_id,
                        user_message=user_message,
                        route_intent=infer_route_intent_from_chat_mode(chat_mode),
                        plan_id=plan_id,
                        plan_context=plan_context,
                        user_context_payload=user_context_payload,
                        state=state,
                        session_feedback_signal=(
                            session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                        ),
                    )

                # Step 6: Prepare runtime context (transparency, tools)
                transparency_generator, emit_transparency_event = await self._prepare_runtime_context(
                    state,
                    request_id,
                    response_id,
                    list(request.active_tools),
                    stream_callback,
                    tracer,
                )

                if request.HasField("tool_result"):
                    async for queued in self._drain_queue(queue):
                        yield queued
                    async for continued_response in self._continue_after_tool_result(
                        request=request,
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        user_context_payload=user_context_payload,
                        conversation_context=conversation_context,
                    ):
                        yield continued_response
                    await self._update_state(session_id, STATE_DONE, "Tool result continuation completed")
                    REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                    COLLABORATION_SUCCESS.labels(workflow_type="standard_chat", agents_used="orchestrator", outcome="success").inc()
                    return

                # Step 7: Notifications
                await self._notify_pending_milestone_proposals(user_id, stream_callback)
                if plan_switched and plan_id:
                    await stream_callback(agent_service_pb2.ChatResponse(metadata={"plan_switched": "true", "switched_to_plan_id": str(plan_id), "session_id": session_id}))

                # Step 8: Inject dependencies into state
                self._inject_state_dependencies(
                    state, active_db=active_db, user_id=user_id, session_id=session_id, stream_callback=stream_callback,
                    tools_schema=state.context_data.get("tools_schema", []), transparency_generator=transparency_generator,
                    emit_transparency_event=emit_transparency_event, user_context_payload=user_context_payload,
                    conversation_context=conversation_context, plan_context=plan_context,
                    file_ids=list(request.file_ids), include_references=bool(request.include_references),
                    workflow_id=workflow_id, prompt_version=prompt_version,
                )
                state.context_data["chat_mode"] = chat_mode
                orchestration_trace = OrchestrationTrace(trace_id=trace_id or request_id or str(uuid.uuid4()))
                self._sync_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    user_context_payload=user_context_payload,
                )
                if expert_routing_decision:
                    state.context_data["expert_routing_metadata"] = expert_routing_decision.to_metadata()
                    state.context_data["selected_experts"] = list(expert_routing_decision.selected_experts)
                    state.context_data["expert_policy_id"] = expert_routing_decision.policy_id

                # Step 9: Non-standard mode fallback only when unified graph routing is explicitly disabled.
                if chat_mode != CHAT_MODE_STANDARD and not settings.ENABLE_UNIFIED_GRAPH_ROUTING:
                    mode_result: dict[str, Any] = {}
                    async for resp in self._handle_multi_agent_mode(
                        chat_mode=chat_mode,
                        user_message=user_message,
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        request_id=request_id,
                        trace_id=trace_id,
                        start_time=start_time,
                        user_context_payload=user_context_payload,
                        conversation_context=conversation_context,
                        plan_context=plan_context,
                        active_db=active_db,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        stream_callback=stream_callback,
                        session_feedback_signal=(
                            session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                        ),
                        session_adaptation_context=(
                            session_adaptation_context.to_dict() if session_adaptation_context is not None else None
                        ),
                        result_holder=mode_result,
                    ):
                        yield resp
                    final_response_data = mode_result.get("final_response_data")
                    if isinstance(final_response_data, dict):
                        with tracer.start_as_current_span("orchestrator.cache_mode_response"):
                            await self._cache_response(session_id, request_id, final_response_data)
                        followup_updates, _, _, _, _, _ = await self._drain_system_updates(user_id)
                        for update_resp in followup_updates:
                            yield update_resp
                    return

                # Step 10: Route with unified orchestration brain for all modes
                route_started_at = time.perf_counter()
                route_decision, unified_routing_result = await self._route_and_classify(
                    user_message=user_message, user_id=user_id, session_id=session_id,
                    grpc_context=grpc_context, conversation_context=conversation_context, state=state,
                )
                orchestration_trace.add_step(
                    step_id="route",
                    label="路由决策",
                    decision=f"进入{self._execution_mode_label(route_decision.execution_mode)}模式",
                    reason=(
                        f"根据你的问题复杂度与上下文信号，当前更适合 {self._execution_mode_label(route_decision.execution_mode)}。"
                    ),
                    confidence=route_decision.confidence,
                    metadata={
                        "execution_mode": route_decision.execution_mode,
                        "risk_level": route_decision.risk_level,
                        "route_reason": route_decision.reason,
                        "intent": (
                            unified_routing_result.primary_intent.value
                            if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                            else None
                        ),
                    },
                    duration_ms=self._roundtrip_ms(route_started_at),
                )
                self._sync_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    user_context_payload=user_context_payload,
                )

                if chat_mode == CHAT_MODE_STANDARD and unified_routing_result:
                    mode_suggestion = self._suggest_mode_switch(
                        intent=unified_routing_result.primary_intent,
                        confidence=unified_routing_result.confidence,
                        context_signals=unified_routing_result.context_signals,
                    )
                    if mode_suggestion:
                        state.context_data["mode_suggestion"] = mode_suggestion
                        if isinstance(user_context_payload, dict):
                            user_context_payload["mode_suggestion"] = mode_suggestion
                        if not state.context_data.get("mode_suggestion_sent"):
                            try:
                                await stream_callback(
                                    agent_service_pb2.ChatResponse(
                                        metadata={
                                            "event_type": "mode_suggestion",
                                            "suggestion": json.dumps(mode_suggestion, ensure_ascii=False),
                                            "session_id": session_id,
                                        }
                                    )
                                )
                                state.context_data["mode_suggestion_sent"] = True
                            except Exception as exc:
                                logger.debug(f"Failed to emit mode suggestion: {exc}")

                mode_strategy_started_at = time.perf_counter()
                route_decision, mode_strategy_metadata = self._apply_mode_strategy_override(
                    chat_mode=chat_mode,
                    route_decision=route_decision,
                    user_message=user_message,
                )
                if mode_strategy_metadata:
                    state.context_data["mode_strategy"] = mode_strategy_metadata
                    if isinstance(user_context_payload, dict):
                        user_context_payload["mode_strategy"] = mode_strategy_metadata
                    orchestration_trace.add_step(
                        step_id="mode_strategy",
                        label="模式策略",
                        decision=(
                            f"{chat_mode} 模式要求 {', '.join(mode_strategy_metadata.get('required_agents') or mode_strategy_metadata.get('preferred_agents') or ['系统自动选择'])} 协作"
                        ),
                        reason=(
                            f"当前模式会优先使用 {mode_strategy_metadata.get('collaboration_mode', 'auto')} 协同，"
                            f"并按既定输出结构组织结果。"
                        ),
                        metadata={
                            **mode_strategy_metadata,
                            "chat_mode": chat_mode,
                            "session_id": session_id,
                        },
                        duration_ms=self._roundtrip_ms(mode_strategy_started_at),
                    )
                    self._sync_orchestration_trace(
                        state=state,
                        orchestration_trace=orchestration_trace,
                        user_context_payload=user_context_payload,
                    )
                    route_decision.reason = (
                        f"{route_decision.reason} | unified_mode:{chat_mode}"
                        if route_decision.reason
                        else f"unified_mode:{chat_mode}"
                    )

                dual_core_started_at = time.perf_counter()
                route_decision = await self._apply_dual_core_routing(
                    route_decision=route_decision,
                    state=state,
                    active_db=active_db,
                    user_id=user_id,
                    plan_id=plan_id,
                    user_context_payload=user_context_payload,
                    plan_context=plan_context,
                    unified_routing_result=unified_routing_result,
                    information_sufficient=bool((state.context_data.get("goal_quality") or {}).get("passed", True)),
                    stream_callback=stream_callback,
                )
                dual_core_decision = state.context_data.get("dual_core_decision") or {}
                orchestration_trace.add_step(
                    step_id="dual_core",
                    label="双核调度",
                    decision=f"{self._dual_core_mode_label(str(dual_core_decision.get('mode') or 'balanced'))}",
                    reason=str(
                        dual_core_decision.get("reason")
                        or "系统判断当前需要同时兼顾理解用户状态与推进执行。"
                    ),
                    metadata={
                        "mode": dual_core_decision.get("mode"),
                        "cognitive_adjustments": dual_core_decision.get("cognitive_adjustments", []),
                        "execution_constraints": dual_core_decision.get("execution_constraints", []),
                        "session_id": session_id,
                    },
                    duration_ms=self._roundtrip_ms(dual_core_started_at),
                )
                self._sync_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    user_context_payload=user_context_payload,
                )

                user_context_payload = await self._apply_context_focus_overlay(
                    active_db=active_db,
                    user_id=user_id,
                    user_message=user_message,
                    route_intent=(
                        unified_routing_result.primary_intent.value
                        if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                        else intent_type
                    ),
                    plan_id=plan_id,
                    plan_context=plan_context,
                    user_context_payload=user_context_payload,
                    state=state,
                    session_feedback_signal=(
                        session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                    ),
                )

                # Step 11: Plan & validate (langgraph/hybrid mode)
                route_decision, executable_plan, snapshot, should_return = await self._plan_and_validate(
                    route_decision=route_decision, user_message=user_message, user_id=user_id, session_id=session_id,
                    active_db=active_db, plan_id=plan_id, conversation_context=conversation_context,
                    plan_context=plan_context,
                    stream_callback=stream_callback, state=state, user_context_payload=user_context_payload,
                    orchestration_trace=orchestration_trace,
                )
                await self._emit_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    stream_callback=stream_callback,
                )
                if should_return:
                    return

                # Step 12: Log route decision
                route_intent = (
                    unified_routing_result.primary_intent.value
                    if unified_routing_result
                    else self._extract_route_intent(route_decision.reason)
                )
                plan_meta = state.context_data.get("plan_metadata", {})
                await self.observability.log_route_decision(
                    user_id=user_id, session_id=session_id, message=user_message,
                    decision={"execution_mode": route_decision.execution_mode, "risk_level": route_decision.risk_level,
                              "reason": route_decision.reason, "intent": route_intent,
                              "confidence": route_decision.confidence,
                              "routing_layer": plan_meta.get("routing_layer", "unknown"),
                              "adaptive_notes": plan_meta.get("adaptive_notes", ""),
                              "summary_used_for_routing": plan_meta.get("summary_used_for_routing", "false")},
                )

                # Step 13: Execute graph
                result_holder: dict[str, Any] = {}
                with tracer.start_as_current_span("agent_graph.invoke"):
                    async for item in self._execute_graph(state=state, user_id=user_id, queue=queue, result_holder=result_holder):
                        yield item

                # Step 14: Build & yield final response
                final_state = result_holder.get("final_state")
                if final_state is not None:
                    total_prompt_tokens = result_holder.get("total_prompt_tokens", 0)
                    total_completion_tokens = result_holder.get("total_completion_tokens", 0)
                    with tracer.start_as_current_span("orchestrator.build_final_response"):
                        final_response, final_response_data = await self._build_final_response(
                            final_state=final_state, executable_plan=executable_plan, active_db=active_db,
                            user_id=user_id, session_id=session_id, response_id=response_id, request_id=request_id,
                            trace_id=trace_id, workflow_id=workflow_id, prompt_version=prompt_version,
                            route_decision=route_decision, plan_switched=plan_switched, plan_id=plan_id,
                            user_context_payload=user_context_payload,
                        )
                    with tracer.start_as_current_span("orchestrator.cache_response"):
                        await self._cache_response(session_id, request_id, final_response_data)
                    try:
                        turn_index = 1
                        if isinstance(conversation_context, dict):
                            messages = conversation_context.get("messages")
                            if isinstance(messages, list):
                                user_count = sum(
                                    1 for msg in messages
                                    if isinstance(msg, dict) and msg.get("role") == "user"
                                )
                                turn_index = user_count
                                if user_message and (not messages or messages[-1].get("role") != "user"):
                                    turn_index += 1
                        collector = ChatSignalCollector(self.redis)
                        task = asyncio.create_task(
                            collector.collect_signals(
                                user_id=uuid.UUID(str(user_id)),
                                user_message=user_message,
                                ai_response=str(final_response_data.get("message") or ""),
                                conversation_id=session_id,
                                turn_index=turn_index,
                                timestamp=_utcnow(),
                            )
                        )
                        self._track_task(task)
                    except Exception as exc:
                        logger.warning("Failed to schedule chat signal collection: %s", exc)
                    if executable_plan and executable_plan.collaboration_mode != "single":
                        await self.observability.log_collaboration_end(
                            user_id=user_id,
                            session_id=session_id,
                            agents=executable_plan.agents_involved,
                            mode=executable_plan.collaboration_mode,
                            tool_calls_count=len(executable_plan.tool_calls or []),
                            latency_ms=(time.time() - start_time) * 1000.0,
                        )
                    if transparency_generator is not None and emit_transparency_event is not None:
                        await emit_transparency_event(transparency_generator.get_complete_event())
                    followup_updates, _, _, _, _, _ = await self._drain_system_updates(user_id)
                    for update_resp in followup_updates:
                        yield update_resp
                    yield final_response

                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                COLLABORATION_SUCCESS.labels(workflow_type="standard_chat", agents_used="orchestrator", outcome="success").inc()

            except Exception as e:
                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="error").inc()
                COLLABORATION_SUCCESS.labels(workflow_type="standard_chat", agents_used="orchestrator", outcome="error").inc()
                logger.error(f"Orchestration Error: {e}", exc_info=True)
                await self._update_state(session_id, STATE_FAILED, str(e))
                if transparency_generator is not None and emit_transparency_event is not None:
                    await emit_transparency_event(transparency_generator.get_complete_event())
                yield agent_service_pb2.ChatResponse(
                    response_id=response_id, created_at=int(datetime.now().timestamp()), request_id=request_id,
                    error=agent_service_pb2.Error(message=str(e), retryable=True, error_code=agent_service_pb2.ERROR_CODE_INTERNAL),
                    finish_reason=agent_service_pb2.ERROR,
                    session_id=session_id,
                )

            finally:
                await self._cleanup(
                    lock_acquired=lock_acquired, lock_renewal_task=lock_renewal_task, lock_renewal_stop=lock_renewal_stop,
                    session_id=session_id, request_id=request_id, start_time=start_time, user_id=user_id,
                    total_prompt_tokens=total_prompt_tokens, total_completion_tokens=total_completion_tokens,
                )


# Backwards-compatible alias for benchmarks/tests
Orchestrator = ChatOrchestrator
