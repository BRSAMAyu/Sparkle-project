"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

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

from app.core.time_utils import utcnow as _utcnow
from typing import Any

from google.protobuf.json_format import MessageToDict
from loguru import logger
from opentelemetry import trace
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.standard_workflow import create_standard_chat_graph
from app.aurora.runtime_v1 import AURORA_RUNTIME_MODE_SURFACES, AuroraRuntimeV1Service
from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.config import settings
from app.core.business_metrics import (
    COLLABORATION_SUCCESS,
)
from app.core.execution_router import ExecutionRouter
from app.core.metrics import (
    ACTIVE_SESSIONS,
    REQUEST_COUNT,
)
from app.core.safe_error_messages import build_safe_chat_error
from app.core.unified_intent_router import UnifiedIntentRouter
from app.gen.agent.v1 import agent_service_pb2
from app.models.plan import Plan
from app.models.task import Task, TaskStatus as ModelTaskStatus
from app.orchestration.agent_activity import emit_agent_activity, emit_routing_preview
from app.orchestration.capability_selection_policy import CapabilitySelectionPolicy

# Multi-Agent Mode Support
from app.orchestration.chat_modes import (
    CHAT_MODE_STANDARD,
    extract_expert_id,
    is_expert_chat_mode,
    normalize_chat_mode,
    parse_team_spec,
)

# Phase 3: Circuit Breaker, Observability, Shadow Mode
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
from app.orchestration.composer import ResponseComposer

# ---------------------------------------------------------------------------
# Mixin imports
# ---------------------------------------------------------------------------
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.context_focus import (
    KNOWLEDGE_ACTION_KEYWORDS,
    PLAN_ACTION_KEYWORDS,
    TASK_ACTION_KEYWORDS,
    infer_route_intent_from_chat_mode,
)
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.dual_core_router import dual_core_router
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.executor import ToolExecutor
from app.orchestration.experience_actuator import ExperienceActuator
from app.orchestration.experience_packets import attach_goal_realization_context
from app.orchestration.expert_strategy import ExpertStrategyV1
from app.orchestration.graph_rag import (
    GraphRAGRetriever,
    filter_graph_rag_result,
    format_graph_rag_document_context,
)
from app.orchestration.grounding_validator import GroundingValidator
from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.orchestration.memory_helpers import (
    build_aurora_modeling_memory_summary,
    build_error_memory_summary,
    extract_completion_state_from_response_data,
)
from app.orchestration.memory_helpers import (
    build_aurora_runtime_metadata as _build_aurora_runtime_metadata,
)
from app.orchestration.memory_helpers import (
    extract_struggle_score as _extract_struggle_score,
)
from app.orchestration.memory_helpers import (
    first_memory_value as _first_memory_value,
)
from app.orchestration.memory_helpers import (
    memory_dict as _memory_dict,
)
from app.orchestration.memory_helpers import (
    memory_json_dict as _memory_json_dict,
)
from app.orchestration.memory_helpers import (
    memory_text as _memory_text,
)
from app.orchestration.memory_helpers import (
    safe_float as _safe_float,
)
from app.orchestration.memory_helpers import (
    should_record_stressed_session_mood as _should_record_stressed,
)
from app.orchestration.memory_helpers import (
    wake_policy_energy as _wake_policy_energy,
)
from app.orchestration.observability_logger import observability_logger
from app.orchestration.observability_mixin import ObservabilityMixin
from app.orchestration.orchestration_trace import OrchestrationTrace
from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.orchestration.plan_review_service import plan_review_service
from app.orchestration.planning_workflow import EXAM_SPRINT_FAST_TRACK_FLAG, PlanningWorkflowManager
from app.orchestration.response_builder import ResponseBuilderMixin

# Phase 1 & Phase 2: Full-Loop Closed System with LangGraph Planner
from app.orchestration.routing_engine import RoutingEngineMixin
from app.orchestration.run_ledger import RunLedgerRecorder
from app.orchestration.schemas import (
    ExecutablePlan,
    RouteDecision,
    StateSnapshot,
)
from app.orchestration.session_feedback import (
    SessionFeedbackSignal,
    build_conversation_rhythm_instruction,
    build_session_feedback_instruction,
)
from app.orchestration.session_state_mixin import SessionStateMixin
from app.orchestration.soul_compiler import attach_shadow_soul_runtime
from app.orchestration.state_manager import SessionStateManager
from app.orchestration.state_snapshot import StateSnapshotManager
from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter
from app.orchestration.statechart_engine import WorkflowState

# Phase 4: Sufficiency Checking
from app.orchestration.sufficiency_checker import sufficiency_checker
from app.orchestration.token_tracker import TokenTracker

# Phase 5: Plan Execution Validation
from app.orchestration.validation_engine import ValidationEngineMixin
from app.orchestration.validator import RequestValidator
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService
from app.services.chat_signal_collector import ChatSignalCollector
from app.services.checkpoint_nudge_service import CheckpointDebriefService
from app.services.custom_expert_service import CustomExpertService, is_custom_expert_id
from app.services.execution_preference_service import ExecutionPreferenceService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import llm_service
from app.services.memory_service import MemoryService
from app.services.shadow_prediction_service import shadow_prediction_service

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


def get_agent_type_for_tool(tool_name: str) -> int:
    """
    Map tool names to AgentType enum for multi-agent visualization.

    Returns:
        AgentType enum value (int)
    """
    tool_lower = tool_name.lower()

    # Knowledge-related tools -> KNOWLEDGE agent
    if any(keyword in tool_lower for keyword in ["knowledge", "query", "search", "retrieve", "vector", "graphrag"]):
        return agent_service_pb2.KNOWLEDGE

    # Math/calculation tools -> MATH agent
    if any(keyword in tool_lower for keyword in ["math", "calculate", "wolfram", "compute", "formula", "equation"]):
        return agent_service_pb2.MATH

    # Code/system tools -> CODE agent
    if any(keyword in tool_lower for keyword in ["code", "execute", "run", "system", "debug", "compile"]):
        return agent_service_pb2.CODE

    # Data analysis tools -> DATA_ANALYSIS agent
    if any(
        keyword in tool_lower
        for keyword in ["data", "analyze", "statistic", "chart", "plot", "visualize", "pandas", "numpy"]
    ):
        return agent_service_pb2.DATA_ANALYSIS

    # Translation tools -> TRANSLATION agent
    if any(keyword in tool_lower for keyword in ["translate", "language", "localize", "i18n"]):
        return agent_service_pb2.TRANSLATION

    # Image tools -> IMAGE agent
    if any(keyword in tool_lower for keyword in ["image", "photo", "picture", "draw", "generate_image", "edit_image"]):
        return agent_service_pb2.IMAGE

    # Audio tools -> AUDIO agent
    if any(keyword in tool_lower for keyword in ["audio", "sound", "music", "speech", "voice", "tts", "stt"]):
        return agent_service_pb2.AUDIO

    # Writing/content tools -> WRITING agent
    if any(keyword in tool_lower for keyword in ["write", "summarize", "compose", "draft", "edit_text"]):
        return agent_service_pb2.WRITING

    # Reasoning/logic tools -> REASONING agent
    if any(keyword in tool_lower for keyword in ["reason", "logic", "solve", "deduce", "infer", "prove"]):
        return agent_service_pb2.REASONING

    # Task/orchestration tools -> ORCHESTRATOR
    if any(
        keyword in tool_lower
        for keyword in ["task", "plan", "create", "update", "batch", "orchestrate", "focus", "pomodoro"]
    ):
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

    _STREAM_QUEUE_MAXSIZE = 512
    _STREAM_QUEUE_PRESSURE_THRESHOLD = 0.75
    _STREAM_QUEUE_CRITICAL_PUT_TIMEOUT_SECONDS = 1.5

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
        self.state_manager = SessionStateManager(redis_client, db_session=db_session)
        self.validator = RequestValidator(
            redis_client,
            daily_quota=getattr(settings, "DAILY_QUOTA", 100000),
            enable_quota_check=bool(getattr(settings, "LLM_QUOTA_ENABLED", False)),
        )
        self.tool_executor = ToolExecutor()
        self.response_composer = ResponseComposer()
        self.dual_core_router = dual_core_router

        # Initialize ContextPruner (P0 feature)
        self.context_pruner = None
        self.token_tracker = None
        self.context_pruner = ContextPruner(
            redis_client=redis_client,
            max_history_messages=10,  # 保留最近10轮对话
            summary_threshold=20,  # 超过20轮触发总结
            summary_cache_ttl=3600,  # 总结缓存1小时
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

        self.graph.on_event = self._chain_event_handlers(visualizer.on_graph_event, self.tracer.record_event)

        # Phase 1: Initialize new components
        self.grounding_validator = GroundingValidator(redis_client)
        self.planning_workflow_manager = PlanningWorkflowManager(redis_client=redis_client)

        # Unified Intent Router (Fix #1): 统一功能入口路由
        self.unified_router = UnifiedIntentRouter(
            redis_client=redis_client, llm_service=llm_service, context_window_size=5
        )
        logger.info("ChatOrchestrator initialized with GroundingValidator and UnifiedIntentRouter")

        # Phase 2: Initialize LangGraph Planner and Snapshot Manager
        # Note: Circuit breaker will be injected after initialization
        self.lang_graph_planner = LangGraphPlanner(redis_client)
        self.snapshot_manager = StateSnapshotManager(redis_client)
        logger.info("ChatOrchestrator initialized with LangGraphPlanner and StateSnapshotManager")

        # Phase 3: Initialize Circuit Breaker
        self.langgraph_breaker = CircuitBreaker(
            name="langgraph_planner",
            config=CircuitBreakerConfig(
                failure_threshold=5, success_threshold=2, timeout_ms=60000, failure_rate_threshold=0.5
            ),
            redis_client=redis_client,
        )
        circuit_breaker_registry.register(self.langgraph_breaker)
        self._track_task(asyncio.create_task(self.langgraph_breaker.initialize()))

        # Inject circuit breaker into LangGraphPlanner
        self.lang_graph_planner.circuit_breaker = self.langgraph_breaker

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

        logger.info(
            "ChatOrchestrator initialized with Phase 3 components: CircuitBreaker, Observability, ShadowMode, PlanReview, VersionConflict"
        )

        # Ensure tools are registered
        self._ensure_tools_registered()
        self.multi_agent_adapter = MultiAgentWorkflowAdapter(self)
        self.aurora_runtime_v1 = AuroraRuntimeV1Service(redis_client)

    async def _attach_aurora_planning_sidecar(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState,
    ) -> str:
        """Attach Aurora planning detour guidance driven by the Aurora decision loop."""
        if not user_message or not isinstance(user_context_payload, dict):
            return ""

        manager = self.planning_workflow_manager
        try:
            session = await manager.get_active_session(session_id)
            if session is None:
                return ""

            extracted_fields = manager._extract_clarifying_fields(user_message)
            if manager.is_message_relevant_to_planning(
                session,
                user_message,
                extracted_fields=extracted_fields,
            ):
                return ""

            try:
                parsed_user_id = uuid.UUID(str(user_id))
            except (TypeError, ValueError):
                logger.debug("Skipping Aurora planning sidecar for non-UUID user_id: {}", user_id)
                return ""

            profile_context = {}
            raw_profile_context = user_context_payload.get("profile_context")
            if isinstance(raw_profile_context, dict):
                profile_context = raw_profile_context
            planning_context = dict(request_extra_context or {})
            planning_context["profile_context"] = profile_context
            if isinstance(user_context_payload.get("calendar_context"), dict):
                planning_context["calendar_context"] = user_context_payload["calendar_context"]
            elif isinstance(user_context_payload.get("cognitive_context"), dict) and isinstance(
                user_context_payload["cognitive_context"].get("calendar_context"), dict
            ):
                planning_context["calendar_context"] = user_context_payload["cognitive_context"]["calendar_context"]

            planning_response = await asyncio.timeout(30)(manager.process_planning_turn)(
                db=active_db,  # type: ignore[arg-type]
                user_id=parsed_user_id,
                chat_session_id=session_id,
                message=user_message,
                context=planning_context,
            )
            if not (planning_response and planning_response.get("bypass_planning")):
                return ""

            planning_runtime_state = await manager.runtime_adapter.load_state(
                user_id=str(parsed_user_id),
                conversation_id=session_id,
                db=active_db,
            )
            if planning_runtime_state is None:
                return ""

            detour_scaffold = manager.runtime_adapter.build_detour_scaffold(planning_runtime_state)
            open_tensions = list(detour_scaffold.get("open_tensions") or [])
            latent_threads = list(detour_scaffold.get("latent_threads") or [])
            if not open_tensions and not latent_threads:
                return ""

            sidecar_request_context = dict(request_extra_context or {})
            sidecar_request_context.update(
                {
                    "surface_complete": False,
                    "modeling_complete": False,
                    "planning_detour_scaffold": detour_scaffold,
                    "informational_tensions": open_tensions,
                    "latent_threads": latent_threads,
                }
            )

            control_surface_reading = await self.aurora_runtime_v1._read_control_surface(
                active_db=active_db,
                user_id=user_id,
            )
            merged_hard_bounds = self._merge_aurora_planning_hard_bounds(
                control_surface_reading.hard_bounds.model_dump(mode="json"),
                detour_scaffold.get("hard_bounds"),
            )
            control_surface_reading = control_surface_reading.model_copy(update={"hard_bounds": merged_hard_bounds})

            activity_profile = self.aurora_runtime_v1._build_activity_profile(
                surface=planning_runtime_state.surface,
                request_extra_context=sidecar_request_context,
            )
            activity_profile.update(planning_runtime_state.activity_profile.to_dict())
            activity_profile.update(self.aurora_runtime_v1._activity_payload(control_surface_reading.adjustable))

            # L1 fast path: skip expensive Aurora LLM decision loop when
            # L1LightAurora determines no escalation is needed.
            _l1 = (request_extra_context or {}).get("aurora_l1")
            if isinstance(_l1, dict) and not bool(_l1.get("should_escalate", True)):
                logger.debug("L1 fast path: skipping Aurora planning sidecar for user={}", user_id)
                return ""

            readout = self.aurora_runtime_v1.dashboard_builder.build(
                surface=planning_runtime_state.surface,
                user_id=user_id,
                conversation_id=session_id,
                request_id=request_id,
                user_message=user_message,
                request_extra_context=sidecar_request_context,
                conversation_context=dict(conversation_context or {}),
                user_context_payload=user_context_payload,
                control_surface_reading=control_surface_reading,
                activity_profile=activity_profile,
                candidate_affordances=self.aurora_runtime_v1.skill_registry.load_candidate_affordances(
                    planning_runtime_state.surface
                ),
            )
            decision = await self.aurora_runtime_v1.decision_loop.decide(readout)

            planning_runtime_state = await manager.runtime_adapter.apply_detour_decision(
                state=planning_runtime_state,
                db=active_db,
                action=decision.action,
                chat_directive=decision.chat_directive,
                harness_updates=decision.harness_updates,
            )
            final_scaffold = manager.runtime_adapter.build_detour_scaffold(planning_runtime_state)
            sidecar_meta = {
                "surface": planning_runtime_state.surface,
                "planning_session_id": planning_runtime_state.planning_session_id or session.planning_session_id,
                "bypass_planning": True,
                "decision": decision.to_payload(),
                "scaffold": final_scaffold,
                "source": "aurora_decision_loop",
            }
            user_context_payload["aurora_planning_sidecar"] = sidecar_meta
            state.context_data["aurora_planning_sidecar"] = dict(sidecar_meta)
            return str(decision.action or "")
        except Exception as exc:
            logger.debug("Aurora planning sidecar attach skipped: {}", exc)
            return ""

    @staticmethod
    def _stringify_response_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
        rendered: dict[str, str] = {}
        for key, value in dict(metadata or {}).items():
            if isinstance(value, bool):
                rendered[str(key)] = str(value).lower()
            elif isinstance(value, (dict, list)):
                rendered[str(key)] = json.dumps(value, ensure_ascii=False, default=str)
            elif value is not None:
                rendered[str(key)] = str(value)
        return rendered

    @staticmethod
    def _is_truthy_metadata_flag(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    @classmethod
    def _extract_fast_track_launch_metadata(
        cls,
        planning_response: dict[str, Any] | None,
    ) -> dict[str, str]:
        response_payload = dict(planning_response or {})
        raw_metadata = dict(response_payload.get("metadata") or {})
        widgets = response_payload.get("widgets")

        plan_id = str(raw_metadata.get("plan_id") or raw_metadata.get("planId") or "").strip()
        recommended_task_id = str(
            raw_metadata.get("recommended_task_id") or raw_metadata.get("recommendedTaskId") or ""
        ).strip()
        first_day_task_ids: list[str] = []

        if isinstance(widgets, list):
            for widget in widgets:
                if not isinstance(widget, dict):
                    continue
                widget_type = str(widget.get("type") or "").strip()
                payload = widget.get("data")
                if not isinstance(payload, dict):
                    continue

                if widget_type == "plan_card" and not plan_id:
                    plan_id = str(payload.get("plan_id") or payload.get("id") or "").strip()

                if widget_type != "task_list":
                    continue

                tasks = payload.get("tasks")
                if not isinstance(tasks, list):
                    continue

                for item in tasks:
                    if not isinstance(item, dict):
                        continue
                    task_id = str(item.get("id") or "").strip()
                    item_plan_id = str(item.get("plan_id") or item.get("planId") or "").strip()
                    if item_plan_id and not plan_id:
                        plan_id = item_plan_id
                    if not task_id:
                        continue
                    if task_id not in first_day_task_ids:
                        first_day_task_ids.append(task_id)
                    if not recommended_task_id:
                        recommended_task_id = task_id

        launch_metadata: dict[str, str] = {}
        if plan_id:
            launch_metadata["plan_id"] = plan_id
            launch_metadata["plan_route"] = f"/plans/{plan_id}"
        if first_day_task_ids:
            launch_metadata["first_day_task_ids_json"] = json.dumps(first_day_task_ids, ensure_ascii=False)
        if recommended_task_id:
            launch_metadata["recommended_task_id"] = recommended_task_id
            launch_metadata["recommended_task_route"] = f"/tasks/{recommended_task_id}"
        return launch_metadata

    @staticmethod
    def _as_plain_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _build_modeling_complete_fast_track_context(
        self,
        *,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        profile_context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Recover deterministic planning prefill when Aurora modeling just closed."""
        manager = self.planning_workflow_manager
        modeling_output = self._as_plain_dict((request_extra_context or {}).get("modeling_output"))
        if not modeling_output:
            profile = self._as_plain_dict(profile_context)
            preferences = self._as_plain_dict(profile.get("preferences"))
            cold_start = self._as_plain_dict(preferences.get("cold_start_context"))
            if cold_start:
                modeling_output = {
                    "activity_profile": self._as_plain_dict(profile.get("activity_profile")),
                    "user_model_snapshot": profile,
                    "cold_start_context": cold_start,
                    "galaxy_baseline": (request_extra_context or {}).get("galaxy_baseline"),
                }
        if not modeling_output:
            return None

        bridge = manager.build_plan_from_modeling_output(modeling_output)
        collected = self._as_plain_dict(bridge.get("collected"))
        if not collected:
            return None

        goal_raw = str(bridge.get("goal_raw") or user_message or "").strip()
        subject = str(collected.get("subject") or collected.get("exam_scope") or goal_raw or "考试科目").strip()
        fast_track_context = manager.build_exam_sprint_fast_track_context(goal_raw or subject) or {
            "intent": "exam_sprint",
            "subject": subject,
            "pack": None,
            "sprint_pack_id": "",
            "pre_filled_scope": str(collected.get("exam_scope") or "").strip(),
            "pre_filled_domain_hints": [],
            "collected": {},
        }

        fast_track_collected = self._as_plain_dict(fast_track_context.get("collected"))
        cold_start = self._as_plain_dict(fast_track_collected.get("cold_start_context"))
        for key, value in collected.items():
            if value in (None, "", [], {}):
                continue
            fast_track_collected[key] = value
            cold_start[key] = value
        fast_track_collected[EXAM_SPRINT_FAST_TRACK_FLAG] = True
        fast_track_collected["from_modeling_complete"] = True
        cold_start[EXAM_SPRINT_FAST_TRACK_FLAG] = True
        cold_start["from_modeling_complete"] = True
        fast_track_collected["cold_start_context"] = cold_start
        fast_track_context["collected"] = fast_track_collected
        if subject:
            fast_track_context["subject"] = subject
        return fast_track_context

    async def _fast_track_exam_sprint(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        stream_callback,
    ) -> bool:
        """Handle cold-start exam sprint planning before generic sufficiency checks."""
        if not user_message:
            return False

        manager = self.planning_workflow_manager
        try:
            active_session = await manager.get_active_session(session_id)
            fast_track_context = None
            from_modeling_complete = self._is_truthy_metadata_flag(
                (request_extra_context or {}).get("from_modeling_complete")
            )
            if active_session is None or not manager.is_fast_track_exam_sprint_session(active_session):
                if not from_modeling_complete:
                    fast_track_context = manager.build_exam_sprint_fast_track_context(user_message)
                else:
                    profile_context = {}
                    if isinstance(user_context_payload, dict) and isinstance(
                        user_context_payload.get("profile_context"), dict
                    ):
                        profile_context = user_context_payload["profile_context"]
                    fast_track_context = self._build_modeling_complete_fast_track_context(
                        user_message=user_message,
                        request_extra_context=request_extra_context,
                        profile_context=profile_context,
                    )
                if not fast_track_context and not from_modeling_complete:
                    return False

            try:
                parsed_user_id = uuid.UUID(str(user_id))
            except (TypeError, ValueError):
                logger.debug("Skipping exam sprint fast-track for non-UUID user_id: {}", user_id)
                return False

            profile_context = {}
            if isinstance(user_context_payload, dict) and isinstance(user_context_payload.get("profile_context"), dict):
                profile_context = user_context_payload["profile_context"]

            planning_context = dict(request_extra_context or {})
            planning_context["profile_context"] = profile_context
            if isinstance(user_context_payload, dict) and isinstance(
                user_context_payload.get("calendar_context"), dict
            ):
                planning_context["calendar_context"] = user_context_payload["calendar_context"]
            elif (
                isinstance(user_context_payload, dict)
                and isinstance(user_context_payload.get("cognitive_context"), dict)
                and isinstance(user_context_payload["cognitive_context"].get("calendar_context"), dict)
            ):
                planning_context["calendar_context"] = user_context_payload["cognitive_context"]["calendar_context"]
            if fast_track_context:
                planning_context["exam_sprint_fast_track"] = fast_track_context

            planning_response = await asyncio.timeout(30)(manager.process_planning_turn)(
                db=active_db,  # type: ignore[arg-type]
                user_id=parsed_user_id,
                chat_session_id=session_id,
                message=user_message,
                context=planning_context,
            )
            if not planning_response or planning_response.get("bypass_planning"):
                return False

            text = str(planning_response.get("message") or "").strip()
            if not text:
                return False

            metadata = self._stringify_response_metadata(planning_response.get("metadata"))
            metadata.update(
                {
                    "planning_fast_track": "exam_sprint",
                    "planning_surface": "aurora_planning",
                    "session_id": session_id,
                }
            )
            metadata.update(self._extract_fast_track_launch_metadata(planning_response))
            widgets = planning_response.get("widgets")
            if widgets:
                metadata["planning_widgets_json"] = json.dumps(widgets, ensure_ascii=False, default=str)

            await stream_callback(
                agent_service_pb2.ChatResponse(
                    full_text=text,
                    finish_reason=agent_service_pb2.STOP,
                    session_id=session_id,
                    metadata=metadata,
                )
            )
            await self._persist_assistant_message(
                active_db=active_db,
                user_id=user_id,
                session_id=session_id,
                full_response=text,
            )
            return True
        except Exception as exc:
            logger.warning("Exam sprint fast-track failed, continuing generic path: {}", exc)
            return False

    @staticmethod
    def _merge_aurora_planning_hard_bounds(
        control_surface_bounds: dict[str, Any] | None,
        scaffold_bounds: dict[str, Any] | None,
    ) -> AuroraHardBounds:
        merged = dict(control_surface_bounds or {})
        overlay = dict(scaffold_bounds or {})

        for field in ("privacy_boundaries", "disabled_actions"):
            values: list[str] = []
            seen: set[str] = set()
            for candidate in list(merged.get(field) or []) + list(overlay.get(field) or []):
                token = str(candidate or "").strip().lower()
                if not token or token in seen:
                    continue
                seen.add(token)
                values.append(token)
            if values:
                merged[field] = values

        dnd_windows: list[dict[str, str]] = []
        seen_windows: set[tuple[str, str]] = set()
        for candidate in list(merged.get("dnd_windows") or []) + list(overlay.get("dnd_windows") or []):
            if not isinstance(candidate, dict):
                continue
            start = str(candidate.get("start") or "").strip()
            end = str(candidate.get("end") or "").strip()
            if not start or not end or (start, end) in seen_windows:
                continue
            seen_windows.add((start, end))
            dnd_windows.append({"start": start, "end": end})
        if dnd_windows:
            merged["dnd_windows"] = dnd_windows

        timezone_name = str(overlay.get("timezone_name") or "").strip()
        if timezone_name:
            merged["timezone_name"] = timezone_name

        return AuroraHardBounds.model_validate(merged)

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        return _safe_float(value)

    @classmethod
    def _extract_struggle_score(cls, payload: Any) -> float | None:
        return _extract_struggle_score(payload)

    @staticmethod
    def _wake_policy_energy(wake_policy: dict[str, Any] | None) -> str:
        return _wake_policy_energy(wake_policy)

    @classmethod
    def _should_record_stressed_session_mood(
        cls,
        *,
        request_extra_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None = None,
        wake_policy: dict[str, Any] | None = None,
    ) -> bool:
        return _should_record_stressed(
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            wake_policy=wake_policy,
        )

    async def _maybe_upsert_session_mood(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        request_extra_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None = None,
        wake_policy: dict[str, Any] | None = None,
    ) -> None:
        if not self._should_record_stressed_session_mood(
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            wake_policy=wake_policy,
        ):
            return
        try:
            await MemoryService(active_db, redis_client=self.redis).upsert_session_mood(
                user_id=user_id,
                session_id=session_id,
                mood_score=0.7,
                mood_label="stressed",
            )
        except Exception as exc:
            logger.warning(
                "Failed to upsert stressed session mood for user {} session {}: {}", user_id, session_id, exc
            )

    @staticmethod
    def _resolve_aurora_runtime_surface(request_extra_context: dict[str, Any]) -> str | None:
        if not getattr(settings, "ENABLE_AURORA_RUNTIME_V1", False):
            return None
        explicit_surface = str(request_extra_context.get("aurora_surface") or "").strip()
        if explicit_surface:
            return AURORA_RUNTIME_MODE_SURFACES.get(explicit_surface, explicit_surface)
        mode = str(request_extra_context.get("mode") or "").strip()
        return AURORA_RUNTIME_MODE_SURFACES.get(mode)

    async def _process_aurora_correction_from_context(
        self,
        *,
        user_id: str,
        session_id: str,
        request_id: str,
        active_db: AsyncSession | None,
        request_extra_context: dict[str, Any],
    ) -> None:
        raw_payload = request_extra_context.get("aurora_correction")
        if not isinstance(raw_payload, dict):
            return
        try:
            from app.aurora.correction_types import AuroraCorrectionPayload
            from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor

            payload = AuroraCorrectionPayload.normalize(
                raw_payload,
                conversation_id=raw_payload.get("conversation_id") or session_id,
                message_id=raw_payload.get("message_id") or request_id,
            )
            request_extra_context["aurora_correction"] = payload.to_dict()

            db_session_factory = None
            if active_db is not None:

                @contextlib.asynccontextmanager
                async def _db_session():
                    yield active_db

                db_session_factory = _db_session

            processor = CorrectionFeedbackProcessor(self.redis, db_session_factory)
            result = await processor.process(
                user_id=user_id,
                semantic_value=payload.semantic_value,
                is_disconfirming=payload.is_disconfirming,
                is_freeform=payload.is_freeform,
                freeform_text=payload.freeform_text,
                telemetry_id=payload.telemetry_id,
                context_source=payload.source,
                correction_payload=payload,
            )
            if result.user_visible_effect:
                effect_key = f"aurora:last_correction_effect:{user_id}"
                await self.redis.set(effect_key, json.dumps(result.user_visible_effect, ensure_ascii=False))
                await self.redis.expire(effect_key, 24 * 3600)
        except Exception:
            logger.warning("Failed to process Aurora correction payload from chat context", exc_info=True)

    @staticmethod
    def _build_aurora_runtime_metadata(
        *,
        surface: str,
        surface_complete: bool,
        modeling_complete: bool,
        modeling_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        return _build_aurora_runtime_metadata(
            surface=surface,
            surface_complete=surface_complete,
            modeling_complete=modeling_complete,
            modeling_snapshot=modeling_snapshot,
        )

    # ── Memory helpers (delegated to memory_helpers module) ────────────

    @staticmethod
    def _memory_dict(value: Any) -> dict[str, Any]:
        return _memory_dict(value)

    @staticmethod
    def _memory_text(value: Any) -> str:
        return _memory_text(value)

    @classmethod
    def _first_memory_value(cls, sources: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
        return _first_memory_value(sources, keys)

    @staticmethod
    def _memory_json_dict(value: Any) -> dict[str, Any]:
        return _memory_json_dict(value)

    @classmethod
    def _build_aurora_modeling_memory_summary(cls, *, modeling_snapshot, request_extra_context, user_context_payload) -> str:
        return build_aurora_modeling_memory_summary(
            modeling_snapshot=modeling_snapshot,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
        )

    @classmethod
    def _extract_completion_state_from_response_data(cls, final_response_data: dict[str, Any] | None) -> str:
        return extract_completion_state_from_response_data(final_response_data)

    async def _find_completed_task_since(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        turn_started_at: datetime | None,
    ) -> Any | None:
        if active_db is None or turn_started_at is None:
            return None
        try:
            result = await active_db.execute(
                select(Task)
                .where(
                    Task.user_id == uuid.UUID(str(user_id)),
                    Task.status == ModelTaskStatus.COMPLETED,
                    Task.completed_at.is_not(None),
                    Task.completed_at >= turn_started_at,
                )
                .order_by(desc(Task.completed_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.debug("Skipping completed-task memory lookup: {}", exc)
            with contextlib.suppress(Exception):
                await active_db.rollback()
            return None

    async def _build_task_completion_memory_summary(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        turn_started_at: datetime | None,
        final_state: WorkflowState | None,
        final_response_data: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
    ) -> str:
        context_data = getattr(final_state, "context_data", {}) or {}
        metadata = self._memory_dict((final_response_data or {}).get("metadata"))
        for key in ("task_completion", "completed_task", "task_completed"):
            candidate = context_data.get(key, metadata.get(key))
            if isinstance(candidate, bool) and candidate:
                task_context = self._derive_task_context_for_execution(
                    task_context=context_data.get("task_context"),
                    plan_context=plan_context,
                    user_context_payload=context_data.get("user_context"),
                )
                topic = self._memory_text((task_context or {}).get("task_description")) or "current task"
                return f"completed {topic}"
            if isinstance(candidate, str) and candidate.strip():
                return f"completed {candidate.strip()}"
            if isinstance(candidate, dict):
                status = str(candidate.get("status") or "").strip().lower()
                completed = candidate.get("completed")
                if completed is True or status in {"completed", "done", "success"}:
                    topic = self._memory_text(
                        candidate.get("topic")
                        or candidate.get("title")
                        or candidate.get("task_title")
                        or candidate.get("name")
                    )
                    return f"completed {topic or 'current task'}"

        completed_task = await self._find_completed_task_since(
            active_db=active_db,
            user_id=user_id,
            turn_started_at=turn_started_at,
        )
        if completed_task is not None:
            topic = self._memory_text(getattr(completed_task, "title", ""))
            return f"completed {topic or str(getattr(completed_task, 'id', 'task'))}"

        completion_state = self._extract_completion_state_from_response_data(final_response_data)
        task_context = self._derive_task_context_for_execution(
            task_context=context_data.get("task_context"),
            plan_context=plan_context,
            user_context_payload=context_data.get("user_context"),
        )
        if completion_state == "done" and task_context and task_context.get("active_task_id"):
            topic = self._memory_text(task_context.get("task_description"))
            return f"completed {topic or task_context.get('active_task_id')}"
        return ""

    @classmethod
    def _build_error_memory_summary(
        cls,
        *,
        request_extra_context: dict[str, Any] | None,
        final_state: WorkflowState | None,
        user_message: str,
        error: Exception | None,
    ) -> str:
        return build_error_memory_summary(
            request_extra_context=request_extra_context,
            final_state=final_state,
            user_message=user_message,
            error=error,
        )

    async def _write_turn_end_episodic_memory(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        request_id: str,
        user_message: str,
        assistant_message: str,
        event_kind: str,
        request_extra_context: dict[str, Any] | None = None,
        user_context_payload: dict[str, Any] | None = None,
        modeling_snapshot: dict[str, Any] | None = None,
        final_state: WorkflowState | None = None,
        final_response_data: dict[str, Any] | None = None,
        plan_context: dict[str, Any] | None = None,
        turn_started_at: datetime | None = None,
        error: Exception | None = None,
    ) -> None:
        if active_db is None:
            return
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return

        summary = ""
        tags: list[str] = ["turn_end", event_kind]
        subject_type = "self"
        importance_score = 0.65

        if event_kind == "aurora_modeling_complete":
            summary = self._build_aurora_modeling_memory_summary(
                modeling_snapshot=modeling_snapshot,
                request_extra_context=request_extra_context,
                user_context_payload=user_context_payload,
            )
            tags.extend(["aurora", "modeling_complete"])
            subject_type = "learning_profile"
            importance_score = 0.86
        elif event_kind == "task_completed":
            summary = await self._build_task_completion_memory_summary(
                active_db=active_db,
                user_id=user_id,
                turn_started_at=turn_started_at,
                final_state=final_state,
                final_response_data=final_response_data,
                plan_context=plan_context,
            )
            tags.append("task_completed")
            subject_type = "task_outcome"
            importance_score = 0.72
        elif event_kind == "error":
            summary = self._build_error_memory_summary(
                request_extra_context=request_extra_context,
                final_state=final_state,
                user_message=user_message,
                error=error,
            )
            tags.append("struggle")
            subject_type = "struggle"
            importance_score = 0.78

        summary = " ".join(str(summary or "").split())
        if not summary:
            return
        if len(summary) > 1800:
            summary = f"{summary[:1799]}…"

        evidence_id = str(request_id or session_id or uuid.uuid4())
        semantic_key = hashlib.sha256(
            f"{user_uuid}:{session_id}:{evidence_id}:{event_kind}:{summary}".encode()
        ).hexdigest()[:64]
        try:
            await MemoryService(active_db).create_episodic_memory(
                user_id=user_uuid,
                summary=summary,
                source_type="chat_turn",
                source_id=evidence_id[:100],
                occurred_at=_utcnow().replace(tzinfo=None),
                importance_score=importance_score,
                confidence=0.78,
                tags=tags,
                evidence_refs=[
                    {
                        "type": "chat_turn",
                        "id": evidence_id,
                        "schema_version": "chat_turn.v1",
                    }
                ],
                source_lane="direct_capture",
                semantic_key=semantic_key,
                subject_type=subject_type,
                emit_system_update=False,
            )
        except Exception as exc:
            logger.warning("Failed to write turn-end episodic memory: {}", exc)

    async def _stream_aurora_runtime_v1(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        surface = self._resolve_aurora_runtime_surface(request_extra_context)
        if surface is None:
            return

        plan = await self.aurora_runtime_v1.plan_turn(
            active_db=active_db,
            user_id=user_id,
            surface=surface,
            conversation_id=session_id,
            request_id=request_id,
            user_message=request.message or "",
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
        )

        modeling_snapshot: dict[str, Any] | None = None
        if plan.modeling_complete:
            profile_context = (
                user_context_payload.get("profile_context") if isinstance(user_context_payload, dict) else None
            )
            modeling_snapshot = {
                "activity_profile": plan.activity_profile,
                "user_model_snapshot": profile_context or {},
                "cold_start_context": ((profile_context or {}).get("preferences", {}).get("cold_start_context")),
                "galaxy_baseline": request_extra_context.get("galaxy_baseline"),
            }

        combined_messages: list[str] = []
        total_messages = len(plan.messages)
        if total_messages == 0:
            terminal_metadata = self._build_aurora_runtime_metadata(
                surface=plan.surface,
                surface_complete=plan.surface_complete,
                modeling_complete=plan.modeling_complete,
                modeling_snapshot=modeling_snapshot,
            )
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                session_id=session_id,
                full_text="",
                finish_reason=agent_service_pb2.STOP,
                metadata=terminal_metadata,
            )
        for index, message in enumerate(plan.messages):
            combined_messages.append(message)
            finish_reason = agent_service_pb2.CONTINUE if index < total_messages - 1 else agent_service_pb2.STOP
            is_terminal = index == total_messages - 1
            metadata = self._build_aurora_runtime_metadata(
                surface=plan.surface,
                surface_complete=plan.surface_complete if is_terminal else False,
                modeling_complete=plan.modeling_complete if is_terminal else False,
                modeling_snapshot=modeling_snapshot if is_terminal else None,
            )
            if total_messages > 1:
                metadata["aurora_message_index"] = str(index)
                metadata["aurora_message_count"] = str(total_messages)
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                session_id=session_id,
                full_text=message,
                finish_reason=finish_reason,
                metadata=metadata,
            )

        combined_text = "\n\n".join(item for item in combined_messages if str(item).strip())
        if combined_text:
            await self._persist_assistant_message(
                active_db=active_db,
                user_id=user_id,
                session_id=session_id,
                full_response=combined_text,
            )
        await self._cache_response(
            session_id,
            request_id,
            {
                "message": combined_text,
                "tool_results": [],
                "metadata": self._build_aurora_runtime_metadata(
                    surface=plan.surface,
                    surface_complete=plan.surface_complete,
                    modeling_complete=plan.modeling_complete,
                ),
            },
        )
        await self._maybe_upsert_session_mood(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            wake_policy=plan.wake_policy,
        )
        if plan.modeling_complete:
            await self._write_turn_end_episodic_memory(
                active_db=active_db,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                user_message=request.message or "",
                assistant_message=combined_text,
                event_kind="aurora_modeling_complete",
                request_extra_context=request_extra_context,
                user_context_payload=user_context_payload,
                modeling_snapshot=modeling_snapshot,
            )

        # Feed Aurora decision back to Spine for attribution tracking
        try:
            from app.signals.spine_aurora_bridge import SpineAuroraBridge
            _bridge = SpineAuroraBridge(self.redis)
            await _bridge.feed_aurora_decision(
                user_id=user_id,
                action=plan.action or "emit_message",
                surface=surface or "",
                chat_directive=plan.chat_directive if hasattr(plan, "chat_directive") else None,
            )
        except Exception:
            logger.warning(
                "feed_aurora_decision failed for user=%s action=%s",
                user_id, plan.action or "emit_message", exc_info=True,
            )

    async def _emit_early_ack_progress(
        self,
        *,
        stream_callback,
        chat_mode: str,
    ) -> None:
        if not getattr(settings, "EARLY_ACK_PROGRESS_ENABLED", True):
            return
        if stream_callback is None:
            return

        normalized_mode = normalize_chat_mode(chat_mode)
        headline = "Message received, preparing response..."
        stage = "intake"
        detail = "Sparkle Flash is handling first-screen interaction."

        if normalized_mode != CHAT_MODE_STANDARD:
            headline = "Message received, initiating collaboration..."
            stage = "handoff"
            detail = "Preparing a quick response before deeper collaboration."

        try:
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.THINKING,
                        details=headline,
                        current_agent_name="Sparkle Flash",
                    ),
                    metadata={
                        "ux_progress": json.dumps(
                            {
                                "stage": stage,
                                "headline": headline,
                                "detail": detail,
                                "is_blocked": False,
                            },
                            ensure_ascii=False,
                        ),
                        "early_ack": "true",
                    },
                )
            )
        except Exception as exc:
            logger.debug(f"Failed to emit early ack progress: {exc}")

    def _coerce_session_uuid(self, session_id: str) -> uuid.UUID:
        raw = str(session_id).strip()
        try:
            return uuid.UUID(raw)
        except Exception:
            logger.debug("Non-standard session_id format, using uuid5 fallback: %s", raw[:50])
            return uuid.uuid5(uuid.NAMESPACE_URL, f"sparkle-session:{raw}")

    @staticmethod
    def _bind_response_session_id(
        response: agent_service_pb2.ChatResponse,
        session_id: str,
        *,
        request_id: str | None = None,
    ) -> agent_service_pb2.ChatResponse:
        if response.session_id:
            return response
        response.session_id = session_id
        if request_id:
            logger.warning(
                "Orchestrator response missing session_id; bound active session_id "
                f"request_id={request_id} session_id={session_id}"
            )
        return response

    def _response_priority(self, resp: agent_service_pb2.ChatResponse) -> str:
        content_kind = resp.WhichOneof("content")
        if resp.finish_reason != agent_service_pb2.NULL or resp.HasField("error"):
            return "critical"
        if content_kind in {"delta", "full_text", "tool_call", "tool_result", "intervention", "citations", "usage"}:
            return "critical"
        metadata = dict(resp.metadata or {})
        event_type = str(metadata.get("event_type") or "").strip().lower()
        if content_kind == "status_update" or event_type in {"transparency", "mode_suggestion"}:
            return "droppable"
        if "ux_progress" in metadata or metadata.get("early_ack") == "true":
            return "droppable"
        return "normal"

    def _evict_oldest_droppable_stream_item(self, queue: asyncio.Queue) -> bool:
        drained_items: list[agent_service_pb2.ChatResponse] = []
        retained_items: list[agent_service_pb2.ChatResponse] = []
        dropped = False

        try:
            while True:
                drained_items.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            pass

        if not drained_items:
            return False

        for item in drained_items:
            if (
                not dropped
                and isinstance(item, agent_service_pb2.ChatResponse)
                and self._response_priority(item) == "droppable"
            ):
                queue.task_done()
                dropped = True
                continue
            retained_items.append(item)

        for item in retained_items:
            queue.put_nowait(item)
            queue.task_done()

        return dropped

    async def _enqueue_stream_response(self, queue: asyncio.Queue, resp: agent_service_pb2.ChatResponse) -> None:
        priority = self._response_priority(resp)
        pressure_ratio = queue.qsize() / max(queue.maxsize or self._STREAM_QUEUE_MAXSIZE, 1)

        if priority == "droppable" and pressure_ratio >= self._STREAM_QUEUE_PRESSURE_THRESHOLD:
            logger.debug(
                "Skipping droppable stream response under queue pressure "
                f"(size={queue.qsize()}, maxsize={queue.maxsize}, priority={priority})"
            )
            return

        try:
            queue.put_nowait(resp)
            return
        except asyncio.QueueFull:
            if priority == "droppable":
                logger.warning(
                    "Response queue full; dropping low-priority stream response "
                    f"(size={queue.qsize()}, maxsize={queue.maxsize})"
                )
                return

        if self._evict_oldest_droppable_stream_item(queue):
            try:
                queue.put_nowait(resp)
                logger.warning(
                    "Evicted low-priority stream response to preserve critical event "
                    f"(finish_reason={resp.finish_reason}, content={resp.WhichOneof('content')})"
                )
                return
            except asyncio.QueueFull:
                pass

        logger.warning(
            "Response queue full while enqueueing critical stream response; applying bounded backpressure "
            f"(finish_reason={resp.finish_reason}, content={resp.WhichOneof('content')}, "
            f"size={queue.qsize()}, maxsize={queue.maxsize})"
        )
        await asyncio.wait_for(
            queue.put(resp),
            timeout=self._STREAM_QUEUE_CRITICAL_PUT_TIMEOUT_SECONDS,
        )

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
        """Track background tasks for graceful shutdown with exception logging."""

        def _on_task_done(t: asyncio.Task) -> None:
            self._bg_tasks.discard(t)
            if t.cancelled():
                return
            if exc := t.exception():
                logger.error(f"Background task {t.get_coro().__name__ if t.get_coro() else t} failed: {exc}", exc_info=exc)

        self._bg_tasks.add(task)
        task.add_done_callback(_on_task_done)

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
            registered = dynamic_tool_registry.ensure_package_registered("app.tools")
            if registered > 0:
                logger.info(f"Auto-registered {len(dynamic_tool_registry.get_all_tools())} tools")

            # Fix 3: 刷新 validator allowlist（与工具注册联动）
            if self.grounding_validator:
                self.grounding_validator.refresh_allowlist()
                logger.info("GroundingValidator allowlist refreshed after tool registration")
        except Exception as e:
            logger.warning(f"Tool registration failed: {e}")

    @staticmethod
    def _infer_bridge_tool_names(user_message: str) -> list[str]:
        message = str(user_message or "").strip().lower()
        if not message:
            return []

        prediction_keywords = (
            "学习规划",
            "学习路径",
            "路径推演",
            "推演一下",
            "帮我推演",
            "推演",
            "两周",
            "两天",
            "what if",
            "what-if",
            "如果我跳过",
            "如果跳过",
            "会怎样",
            "怎么安排",
        )
        simulation_keywords = (
            "帮我模拟",
            "模拟一下",
            "学习场景",
            "演练",
            "学习小组",
            "辩论",
            "角色扮演",
            "苏格拉底",
            "如果我这样学",
        )
        report_keywords = (
            "学习报告",
            "分析报告",
            "学习分析",
            "复盘报告",
            "学习总结",
            "周报",
            "周总结",
            "最近学得怎么样",
            "最近学习表现",
            "生成学习报告",
        )

        negation_markers = (
            "不需要",
            "不要",
            "不用",
            "无需",
            "先别",
            "别",
            "不想",
            "先不",
            "暂时不",
            "先不要",
            "not ",
            "don't ",
            "do not ",
            "no ",
        )

        def _has_positive_keyword(keywords: tuple[str, ...]) -> bool:
            for keyword in keywords:
                start = message.find(keyword)
                while start != -1:
                    prefix = message[max(0, start - 8) : start]
                    if not any(marker in prefix for marker in negation_markers):
                        return True
                    start = message.find(keyword, start + len(keyword))
            return False

        inferred: list[str] = []
        if _has_positive_keyword(prediction_keywords):
            inferred.append("launch_prediction")
        if _has_positive_keyword(simulation_keywords):
            inferred.append("run_quick_simulation")
        report_context = _has_positive_keyword(("报告", "总结", "复盘")) and _has_positive_keyword(
            ("学习", "掌握", "进度", "本周", "这周", "最近")
        )
        if _has_positive_keyword(report_keywords) or report_context:
            inferred.append("generate_learning_report")
        return inferred

    def _resolve_active_tools(self, request: agent_service_pb2.ChatRequest, user_message: str) -> list[str]:
        requested = [tool.strip() for tool in list(request.active_tools) if str(tool).strip()]
        explicit_request = bool(requested)
        for inferred in self._infer_bridge_tool_names(user_message):
            if inferred not in requested:
                requested.append(inferred)
        if not explicit_request:
            route_intent = self._infer_capability_route_intent(
                user_message=user_message,
                chat_mode=getattr(request, "chat_mode", None),
            )
            requested = CapabilitySelectionPolicy().choose_pre_context_tools(
                route_intent=route_intent,
                user_message=user_message,
                requested_tools=requested,
            )
        return requested

    def _infer_capability_route_intent(self, *, user_message: str, chat_mode: str | None) -> str | None:
        route_intent = infer_route_intent_from_chat_mode(chat_mode)
        if route_intent:
            return route_intent

        message = str(user_message or "").strip().lower()
        if not message:
            return None

        def _contains_any(keywords: set[str]) -> bool:
            return any(str(keyword).strip().lower() in message for keyword in keywords if str(keyword).strip())

        if _contains_any(KNOWLEDGE_ACTION_KEYWORDS):
            return "knowledge"
        if _contains_any(PLAN_ACTION_KEYWORDS):
            return "plan"
        if _contains_any(TASK_ACTION_KEYWORDS):
            return "task"
        return None

    @staticmethod
    def _derive_task_context_for_execution(
        *,
        task_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if isinstance(task_context, dict) and task_context:
            return task_context

        if isinstance(plan_context, dict):
            active_task_id = plan_context.get("active_task_id") or plan_context.get("task_id")
            task_description = plan_context.get("task_title") or plan_context.get("title") or ""
            if active_task_id or task_description:
                return {
                    "active_task_id": active_task_id,
                    "task_type": plan_context.get("task_type") or "general",
                    "task_description": task_description,
                }

        if isinstance(user_context_payload, dict):
            next_actions = user_context_payload.get("next_actions")
            if isinstance(next_actions, list):
                for item in next_actions:
                    if not isinstance(item, dict):
                        continue
                    return {
                        "active_task_id": item.get("id") or item.get("task_id"),
                        "task_type": item.get("type") or "general",
                        "task_description": item.get("title") or item.get("content") or "",
                    }
        return None

    async def _detect_execution_suggestion(
        self,
        *,
        user_message: str,
        assistant_response: str,
        task_context: dict[str, Any] | None,
        cognitive_context: dict[str, Any] | None,
        user_id: str,
        session_id: str,
        active_db: AsyncSession | None,
    ) -> dict[str, Any] | None:
        if not settings.OPENCLAW_ENABLED or not task_context or active_db is None:
            return None

        task_id = task_context.get("active_task_id")
        if not task_id:
            return None

        delegation_signals = [
            "帮我查",
            "帮我找",
            "帮我搜",
            "帮我整理",
            "帮我总结",
            "你来做",
            "交给你",
            "自动完成",
            "帮我执行",
            "help me search",
            "look up",
            "find for me",
            "summarize this",
        ]
        message_lower = (user_message or "").lower()
        assistant_lower = (assistant_response or "").lower()
        suggestion_markers = (
            "你可以",
            "建议你",
            "下一步可以",
            "可以先去",
            "you can",
            "you should",
            "next step",
        )
        if not any(signal in message_lower for signal in delegation_signals) and not any(
            marker in assistant_lower for marker in suggestion_markers
        ):
            return None

        delegate_preference = 0.5
        if isinstance(cognitive_context, dict):
            preferences = cognitive_context.get("preferences")
            if isinstance(preferences, dict):
                try:
                    delegate_preference = float(preferences.get("ai_delegate_preference") or 0.5)
                except (TypeError, ValueError):
                    delegate_preference = 0.5

        try:
            preference_service = ExecutionPreferenceService(active_db, self.redis)
            user_uuid = uuid.UUID(str(user_id))
            if await preference_service.should_suppress_delegation_suggestion(
                user_id=user_uuid,
                session_id=session_id,
            ):
                return None
            router = ExecutionRouter(openclaw_enabled=True)
            decision = router.classify(
                task_type=str(task_context.get("task_type") or "general"),
                goal=str(task_context.get("task_description") or user_message or ""),
                has_side_effects=False,
                has_clear_criteria=False,
                task_tags=[],
            )
            if decision.execution_mode.value not in {"agent", "hybrid"}:
                return None
            await preference_service.record_delegation_suggestion_shown(
                user_id=user_uuid,
                session_id=session_id,
            )
            return {
                "type": "execution_suggestion",
                "task_id": str(task_id),
                "execution_mode": decision.execution_mode.value,
                "target_env": decision.target_env.value if decision.target_env else None,
                "reason": decision.reason,
                "suggested_action": "handoff",
                "tone": "detailed_guidance" if delegate_preference < 0.45 else "brief_handoff",
                "delegate_preference": round(delegate_preference, 2),
                "source": "execution_suggestion",
            }
        except Exception as exc:
            logger.debug("Execution suggestion detection failed: {}", exc)
            return None

    async def _hydrate_document_context(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_message: str,
        route_intent: str | None,
        user_context_payload: dict[str, Any] | None,
        state: WorkflowState,
    ) -> dict[str, Any] | None:
        """Run document RAG once and attach the prompt-ready document block."""
        if str(state.context_data.get("document_context") or "").strip():
            return user_context_payload
        if state.context_data.get("use_document_context") is False:
            logger.info("Document context hydration skipped: use_document_context=false")
            return user_context_payload
        if active_db is None or not str(user_message or "").strip():
            return user_context_payload

        decision = state.context_data.get("document_retrieval_decision") or state.context_data.get("retrieval_decision")
        if not isinstance(decision, dict):
            user_context_payload = self._attach_retrieval_decision(
                user_context_payload=user_context_payload,
                state=state,
                user_message=user_message,
                route_intent=route_intent,
            )
            decision = state.context_data.get("document_retrieval_decision") or state.context_data.get(
                "retrieval_decision"
            )
        if not (isinstance(decision, dict) and decision.get("should_retrieve")):
            return user_context_payload
        if not bool(getattr(settings, "ENABLE_DOCUMENT_CONTEXT_INJECTION", True)):
            return user_context_payload
        try:
            injection_mode = (await AuroraDocContextKillSwitchService().get_mode()).strip().lower()
        except Exception:
            logger.warning("AuroraDocContextKillSwitchService.get_mode failed, falling back to settings", exc_info=True)
            injection_mode = (
                str(getattr(settings, "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE", "live") or "live")
                .strip()
                .lower()
            )
        if injection_mode == "off":
            return user_context_payload

        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return user_context_payload

        conversation_settings = state.context_data.get("conversation_settings")
        if not isinstance(conversation_settings, dict):
            conversation_settings = {}
        include_group_documents = bool(
            state.context_data.get("include_group_documents")
            or conversation_settings.get("include_group_documents")
            or state.context_data.get("group_id")
            or conversation_settings.get("group_id")
        )
        raw_group_ids = state.context_data.get("group_ids") or conversation_settings.get("group_ids") or []
        group_ids: list[str] = []
        seen_group_ids: set[str] = set()
        for item in raw_group_ids:
            value = str(item or "").strip()
            if value and value not in seen_group_ids:
                seen_group_ids.add(value)
                group_ids.append(value)
        primary_group_id = str(state.context_data.get("group_id") or conversation_settings.get("group_id") or "").strip()
        if primary_group_id and primary_group_id not in seen_group_ids:
            group_ids.append(primary_group_id)

        mode = str(decision.get("retrieval_mode") or "selective")
        spine_retrieval_directive = state.context_data.get("spine_retrieval_directive")
        if isinstance(spine_retrieval_directive, dict) and str(
            spine_retrieval_directive.get("retrieval_mode") or ""
        ).strip().lower() in {"no_rag", "no_retrieval", "skip"}:
            logger.info("Document context hydration skipped by RetrievalDirective no_rag")
            return user_context_payload
        try:
            knowledge_service = KnowledgeService(active_db)
            retriever = GraphRAGRetriever(knowledge_service)

            # P1-9: depth mapping for deep_source_synthesis + aurora_core_case_file
            if mode == "deep_source_synthesis":
                retrieval_depth = 3
            elif mode == "aurora_core_case_file":
                retrieval_depth = 2
            elif mode == "aggressive":
                retrieval_depth = 2
            else:
                retrieval_depth = 1

            rag_result = await asyncio.wait_for(
                retriever.retrieve(
                    str(user_message or ""),
                    str(user_uuid),
                    depth=retrieval_depth,
                    route_intent=route_intent,
                    include_group_documents=include_group_documents,
                    group_ids=group_ids,
                    retrieval_directive=(
                        spine_retrieval_directive if isinstance(spine_retrieval_directive, dict) else None
                    ),
                ),
                timeout=max(6.0, float(getattr(settings, "GRAPHRAG_FASTPATH_TIMEOUT_SECONDS", 2.5) or 2.5) * 3),
            )
            filtered_rag = filter_graph_rag_result(rag_result)
            document_context = format_graph_rag_document_context(rag_result, filtered_rag.chunks)
            used_chunks = [
                {
                    "chunk_id": c.chunk_id,
                    "source_file_id": c.source_file_id,
                    "filename": c.filename,
                    "page_number": c.page_number,
                    "relevance_score": round(c.relevance_score, 3),
                    "evidence_strength": c.evidence_strength,
                }
                for c in filtered_rag.chunks
                if c.relevance_score >= 0.3
            ]
            used_filenames = {c["filename"] for c in used_chunks}
            all_filenames = {c.filename for c in filtered_rag.chunks}
            excluded_names = sorted(all_filenames - used_filenames)
            excluded_count = filtered_rag.total_retrieved - len(used_chunks)
            context_receipt = {
                "used": used_chunks,
                "used_names": sorted(used_filenames),
                "used_count": len(used_chunks),
                "excluded_names": [
                    f"{name}（相关度过低）" for name in excluded_names
                ],
                "excluded_count": excluded_count,
                "total_retrieved": filtered_rag.total_retrieved,
                "mode": mode,
                "decision_reason": state.context_data.get(
                    "retrieval_decision", {}
                ).get("reason_for_user", ""),
            }
            metadata = {
                "source": "graphrag",
                "mode": mode,
                "total_retrieved": filtered_rag.total_retrieved,
                "total_passed": filtered_rag.total_passed,
                "fallback_triggered": filtered_rag.fallback_triggered,
                "entities": list(rag_result.entities or []),
                "injection_mode": injection_mode,
                "context_receipt": context_receipt,
            }
        except Exception as exc:
            logger.warning(f"GraphRAG document context hydration failed: {exc}")
            return user_context_payload

        state.context_data["document_context"] = document_context
        state.context_data["document_context_retrieval"] = metadata
        state.context_data["document_context_candidate"] = document_context
        state.context_data["document_context_candidate_chunks"] = metadata["total_passed"]
        if isinstance(user_context_payload, dict):
            user_context_payload["document_context"] = document_context
            user_context_payload["document_context_retrieval"] = metadata
        logger.info(
            "Hydrated document context via GraphRAG: mode={} passed={} retrieved={}",
            mode,
            metadata["total_passed"],
            metadata["total_retrieved"],
        )
        return user_context_payload

    # -----------------------------------------------------------------------
    # process_stream — main entry point (delegates to mixin methods)
    # -----------------------------------------------------------------------

    async def process_stream(
        self,
        request: agent_service_pb2.ChatRequest,
        db_session: AsyncSession | None = None,
        context_data: dict[str, Any] | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """Coordinator: orchestrate chat request through validation, routing,
        planning, execution, and response composition."""
        tracer = trace.get_tracer(__name__)

        # NOTE: Do NOT use `with tracer.start_as_current_span(...)` wrapping the
        # entire async generator body. An async generator yields across multiple
        # coroutine contexts; the ContextVar token created by start_as_current_span
        # is tied to the originating context and cannot be detached from a different
        # one (raises "ValueError: Token was created in a different Context").
        # Inner spans on individual await expressions are fine.
        span = tracer.start_span("orchestrator.process_stream")
        span.set_attribute("session_id", request.session_id)
        span.set_attribute("user_id", request.user_id)
        span.set_attribute("request_id", request.request_id)
        trace_id = format(span.get_span_context().trace_id, "032x")

        try:
            start_time = time.time()
            turn_started_at = _utcnow().replace(tzinfo=None)
            ACTIVE_SESSIONS.inc()
            request_id = request.request_id
            session_id = str(request.session_id or "").strip()
            if not session_id:
                session_id = str(uuid.uuid4())
                request.session_id = session_id
                logger.warning(
                    "Generated new orchestrator session_id for first request without a session_id "
                    f"request_id={request_id} session_id={session_id}"
                )
                span.set_attribute("session_id_generated", True)
            span.set_attribute("session_id", session_id)
            user_id = request.user_id
            response_id = str(uuid.uuid4())
            workflow_id = (context_data or {}).get("workflow_id", "standard_chat")
            prompt_version = (context_data or {}).get("prompt_version", "v1")
            active_db = db_session or self.db_session

            # Step 1: Validation & idempotency (early exits)
            if validation_error := await self._validate_request(
                request, response_id=response_id, request_id=request_id
            ):
                yield self._bind_response_session_id(validation_error, session_id, request_id=request_id)
                return
            if cached_resp := await self._check_idempotency_response(
                session_id=session_id, request_id=request_id, response_id=response_id
            ):
                yield self._bind_response_session_id(cached_resp, session_id, request_id=request_id)
                return

            lock_acquired = False
            lock_renewal_task: asyncio.Task | None = None
            lock_renewal_stop: asyncio.Event | None = None
            total_prompt_tokens = 0
            total_completion_tokens = 0
            transparency_generator: TransparencyDataGenerator | None = None
            emit_transparency_event = None
            queue: asyncio.Queue = asyncio.Queue(maxsize=self._STREAM_QUEUE_MAXSIZE)

            try:
                # Step 2: Distributed lock
                lock_acquired = await self._acquire_session_lock(session_id, request_id)
                if not lock_acquired:
                    yield self._bind_response_session_id(
                        agent_service_pb2.ChatResponse(
                            response_id=response_id,
                            created_at=int(datetime.now().timestamp()),
                            request_id=request_id,
                            error=agent_service_pb2.Error(
                                message="Session is busy processing another request, please wait.",
                                retryable=True,
                                error_code=agent_service_pb2.ERROR_CODE_CONFLICT,
                            ),
                            finish_reason=agent_service_pb2.ERROR,
                        ),
                        session_id,
                        request_id=request_id,
                    )
                    return
                lock_renewal_task, lock_renewal_stop = await self.state_manager.start_lock_renewal(
                    session_id, request_id, interval=10.0
                )

                # Step 3: Initialize state & extract message
                await self._update_state(
                    session_id,
                    STATE_INIT,
                    f"Request {request_id}",
                    request_id=request_id,
                    user_id=user_id,
                )
                chat_mode = normalize_chat_mode(request.chat_mode or CHAT_MODE_STANDARD)
                user_message = request.message or ""
                request_extra_context = {}
                if request.HasField("extra_context"):
                    try:
                        request_extra_context = MessageToDict(request.extra_context)
                    except Exception as exc:
                        logger.warning(f"Failed to parse request extra_context in process_stream: {exc}")
                request_document_filter = list(getattr(request, "document_filter", []) or [])
                request_use_document_context = None
                try:
                    if request.HasField("use_document_context"):
                        request_use_document_context = bool(request.use_document_context)
                        request_extra_context["use_document_context"] = request_use_document_context
                except ValueError:
                    request_use_document_context = request_extra_context.get("use_document_context")
                if request_document_filter:
                    request_extra_context["document_filter"] = request_document_filter
                    request_extra_context["selected_document_ids"] = request_document_filter
                await self._process_aurora_correction_from_context(
                    user_id=user_id,
                    session_id=session_id,
                    request_id=request_id,
                    active_db=active_db,
                    request_extra_context=request_extra_context,
                )
                raw_conversation_settings = request_extra_context.get("conversation_settings")
                conversation_settings = dict(raw_conversation_settings) if isinstance(raw_conversation_settings, dict) else {}
                raw_group_ids = (
                    request_extra_context.get("group_ids")
                    or request_extra_context.get("target_group_ids")
                    or conversation_settings.get("group_ids")
                    or []
                )
                group_ids: list[str] = []
                seen_group_ids: set[str] = set()
                for item in raw_group_ids:
                    value = str(item or "").strip()
                    if value and value not in seen_group_ids:
                        seen_group_ids.add(value)
                        group_ids.append(value)
                group_id = str(
                    request_extra_context.get("group_id")
                    or request_extra_context.get("target_group_id")
                    or conversation_settings.get("group_id")
                    or ""
                ).strip()
                if group_id and group_id not in seen_group_ids:
                    group_ids.append(group_id)
                include_group_documents = bool(
                    request_extra_context.get("include_group_documents")
                    or conversation_settings.get("include_group_documents")
                    or group_id
                )
                request_extra_context["conversation_settings"] = {
                    "use_document_context": request_use_document_context,
                    "document_filter": request_document_filter,
                    "group_id": group_id or None,
                    "group_ids": group_ids,
                    "include_group_documents": include_group_documents,
                }
                if group_id:
                    request_extra_context["group_id"] = group_id
                if group_ids:
                    request_extra_context["group_ids"] = group_ids
                request_extra_context["include_group_documents"] = include_group_documents
                resolved_active_tools = self._resolve_active_tools(request, user_message)

                debrief_response = await CheckpointDebriefService(active_db, self.redis).process_turn(
                    user_id=uuid.UUID(str(user_id)),
                    chat_session_id=session_id,
                    user_message=user_message,
                    context=request_extra_context,
                )
                if debrief_response:
                    text = str(debrief_response.get("message") or "")
                    await self._persist_assistant_message(
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        full_response=text,
                    )
                    yield agent_service_pb2.ChatResponse(
                        response_id=response_id,
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        full_text=text,
                        finish_reason=agent_service_pb2.STOP,
                        session_id=session_id,
                        metadata={"debrief_mode": "checkpoint"},
                    )
                    await self._update_state(session_id, STATE_DONE, "Checkpoint debrief completed")
                    return

                if chat_mode == CHAT_MODE_STANDARD and not request.HasField("tool_result"):
                    bridge_responses = await self._maybe_short_circuit_bridge_tool(
                        active_tools=resolved_active_tools,
                        user_message=user_message,
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        active_db=active_db,
                    )
                    if bridge_responses:
                        for bridge_response in bridge_responses:
                            yield self._bind_response_session_id(bridge_response, session_id, request_id=request_id)
                        await self._update_state(session_id, STATE_DONE, "Bridge tool short-circuit completed")
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                        COLLABORATION_SUCCESS.labels(
                            workflow_type="standard_chat", agents_used="orchestrator", outcome="success"
                        ).inc()
                        return

                    saw_openclaw_short_circuit = False
                    async for openclaw_response in self._stream_openclaw_chat_control(
                        active_tools=resolved_active_tools,
                        user_message=user_message,
                        request_extra_context=request_extra_context,
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        active_db=active_db,
                    ):
                        saw_openclaw_short_circuit = True
                        yield self._bind_response_session_id(openclaw_response, session_id, request_id=request_id)
                    if saw_openclaw_short_circuit:
                        await self._update_state(
                            session_id, STATE_DONE, "OpenClaw chat control short-circuit completed"
                        )
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                        COLLABORATION_SUCCESS.labels(
                            workflow_type="standard_chat", agents_used="openclaw", outcome="success"
                        ).inc()
                        return

                # Step 4: Build full context
                (
                    grpc_context,
                    plan_id,
                    plan_switched,
                    user_context_payload,
                    conversation_context,
                    plan_context,
                ) = await self._build_full_context(
                    request=request,
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    request_id=request_id,
                    tracer=tracer,
                )
                conversation_context = self._merge_request_history_into_conversation_context(
                    conversation_context,
                    list(request.history),
                )
                effective_file_ids = (
                    [] if request_use_document_context is False else (request_document_filter or list(request.file_ids))
                )
                if isinstance(user_context_payload, dict):
                    user_context_payload["use_document_context"] = request_use_document_context
                    user_context_payload["document_filter"] = request_document_filter
                    user_context_payload["selected_document_ids"] = request_document_filter
                    user_context_payload["conversation_settings"] = dict(request_extra_context["conversation_settings"])
                initial_document_context_state = {
                    "use_document_context": request_use_document_context,
                    "document_filter": request_document_filter,
                    "selected_document_ids": request_document_filter,
                    "effective_file_ids": effective_file_ids,
                    "conversation_settings": dict(request_extra_context["conversation_settings"]),
                    "group_id": request_extra_context.get("group_id"),
                    "group_ids": list(request_extra_context.get("group_ids") or []),
                    "include_group_documents": bool(request_extra_context.get("include_group_documents")),
                }

                session_feedback_signal = None
                session_adaptation_context = None
                conversation_rhythm = None
                if not request.HasField("tool_result"):
                    (
                        session_feedback_signal,
                        session_adaptation_context,
                        conversation_rhythm,
                    ) = await self._detect_session_feedback(
                        session_id=session_id,
                        user_message=user_message,
                        conversation_context=conversation_context,
                    )
                session_feedback_signal = self._apply_cohort_to_session_feedback_signal(
                    session_feedback_signal,
                    (
                        (user_context_payload or {}).get("experiment_cohort")
                        if isinstance(user_context_payload, dict)
                        else None
                    ),
                )

                # P3: Signal-to-Action Spine — exam rescue & stale state + Aurora bridge
                _spine_context: dict[str, Any] = {}
                if not request.HasField("tool_result") and user_message:
                    try:
                        from app.signals.spine_aurora_bridge import SpineAuroraBridge
                        from app.signals.spine_orchestrator import get_spine_orchestrator
                        _spine = get_spine_orchestrator(self.redis)
                        _spine_bridge = SpineAuroraBridge(self.redis)

                        # First-message exam rescue detection
                        _conv_msgs = (conversation_context or {}).get("messages") or []
                        if len(_conv_msgs) == 0:
                            await _spine.on_first_message(
                                user_id=user_id,
                                message=user_message,
                            )

                        _chat_trace = await _spine.on_chat_turn(
                            user_id=user_id,
                            message=user_message,
                            session_id=session_id,
                            request_id=request_id,
                            context=request_extra_context if isinstance(request_extra_context, dict) else {},
                        )
                        if _chat_trace is not None:
                            request_extra_context["spine_causal_trace_id"] = _chat_trace.trace_id
                        _l1_context = await _spine.get_l1_turn_context(user_id)
                        if _l1_context:
                            request_extra_context["aurora_l1"] = _l1_context

                        # Stale-state guard on user return
                        _analytics = (user_context_payload or {}).get("analytics_summary") or {}
                        _last_active = _analytics.get("last_activity_time") or _analytics.get("last_login")
                        if _last_active:
                            from datetime import datetime as _dt
                            if isinstance(_last_active, str):
                                with contextlib.suppress(ValueError):
                                    _last_active = _dt.fromisoformat(_last_active)
                            if isinstance(_last_active, _dt):
                                _elapsed_min = (_utcnow().replace(tzinfo=None) - _last_active.replace(tzinfo=None)).total_seconds() / 60
                                if _elapsed_min >= 60:
                                    await _spine.on_user_return(
                                        user_id=user_id,
                                        time_context={
                                            "now": _utcnow().isoformat(),
                                            "elapsed_since_last_interaction_min": _elapsed_min,
                                            "active_task_id": None,
                                        },
                                    )

                        # Aurora ↔ Spine bridge: fetch Spine context for Aurora
                        _spine_context = await _spine_bridge.get_context_for_aurora(user_id)
                        if _spine_context:
                            if isinstance(request_extra_context, dict):
                                request_extra_context["spine_signals"] = _spine_context
                            else:
                                request_extra_context = {"spine_signals": _spine_context}

                        # v2.9: Fetch structured directives for prompt/RAG modulation
                        try:
                            _spine_resp_dir = await _spine.get_response_directive(user_id)
                            if _spine_resp_dir:
                                request_extra_context["spine_response_directive"] = _spine_resp_dir.to_dict()
                        except Exception:
                            logger.warning("Redis/spine get_response_directive failed for user=%s", user_id, exc_info=True)
                        try:
                            _spine_ret_dir = await _spine.get_retrieval_directive(user_id)
                            if _spine_ret_dir:
                                request_extra_context["spine_retrieval_directive"] = _spine_ret_dir.to_dict()
                        except Exception:
                            logger.warning("Redis/spine get_retrieval_directive failed for user=%s", user_id, exc_info=True)
                        try:
                            from app.signals.growth_chronicle import GrowthChronicleService
                            _chronicle_svc = GrowthChronicleService(self.redis)
                            _chronicle_entries = await _chronicle_svc.get_chronicle(user_id, limit=3)
                            if _chronicle_entries:
                                request_extra_context["spine_chronicle_summary"] = "\n".join(
                                    f"- {e.title}: {e.narrative}" for e in _chronicle_entries if e.narrative
                                )
                        except Exception:
                            logger.warning(
                                "GrowthChronicleService.get_chronicle failed for user=%s", user_id, exc_info=True,
                            )
                        try:
                            # Track interaction count for fatigue detection
                            _inter_key = f"spine:interaction_count:{user_id}:24h"
                            await self.redis.incr(_inter_key)
                            await self.redis.expire(_inter_key, 24 * 3600)
                            _inter_count_raw = await self.redis.get(_inter_key)
                            _inter_count = int(_inter_count_raw) if _inter_count_raw else 0
                            _fatigue = await _spine.check_fatigue(
                                user_id=user_id,
                                interactions_last_24h=_inter_count,
                            )
                            if _fatigue and _fatigue.get("fatigue_level") not in ("low", "normal"):
                                request_extra_context["spine_fatigue_context"] = _fatigue
                        except Exception:
                            logger.warning(
                                "Spine fatigue check failed for user=%s", user_id, exc_info=True,
                            )
                        try:
                            _spine_ux = await _spine.get_ux_directive(user_id)
                            if _spine_ux:
                                request_extra_context["spine_ux_directive"] = _spine_ux.to_dict()
                        except Exception:
                            logger.warning("Redis/spine get_ux_directive failed for user=%s", user_id, exc_info=True)
                        try:
                            _spine_comm = await _spine.get_community_directive(user_id)
                            if _spine_comm:
                                request_extra_context["spine_community_directive"] = _spine_comm.to_dict()
                        except Exception:
                            logger.warning("Redis/spine get_community_directive failed for user=%s", user_id, exc_info=True)
                        try:
                            _spine_skill = await _spine.get_skill_directive(user_id)
                            if _spine_skill:
                                request_extra_context["spine_skill_directive"] = _spine_skill.to_dict()
                        except Exception:
                            logger.warning("Redis/spine get_skill_directive failed for user=%s", user_id, exc_info=True)
                    except Exception as _spine_err:
                        from app.core.business_metrics import record_spine_degradation

                        record_spine_degradation("chat_turn", _spine_err)
                        logger.warning("Spine signal check degraded: {}", _spine_err)
                        request_extra_context["spine_degraded"] = True

                expert_routing_decision = None
                requested_experts: list[str] = []
                answer_experts: list[str] = []
                team_spec = parse_team_spec(chat_mode)
                if team_spec:
                    requested_experts = [
                        str(item).strip() for item in (team_spec.get("agents") or []) if str(item).strip()
                    ]
                    answer_experts = [
                        str(item).strip()
                        for item in (team_spec.get("final_agents") or team_spec.get("answer_agents") or [])
                        if str(item).strip()
                    ]
                explicit_expert = extract_expert_id(chat_mode)
                if explicit_expert:
                    requested_experts = [explicit_expert]

                custom_expert_profiles: dict[str, dict[str, Any]] = {}
                if active_db is not None and any(
                    is_custom_expert_id(item) for item in [*requested_experts, *answer_experts]
                ):
                    custom_expert_profiles = await CustomExpertService(active_db).load_runtime_profiles(
                        user_id=user_id,
                        expert_ids=[*requested_experts, *answer_experts],
                    )

                if (
                    settings.ENABLE_EXPERT_STRATEGY_V1
                    and is_expert_chat_mode(chat_mode)
                    and not any(is_custom_expert_id(item) for item in requested_experts)
                ):
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
                state.context_data.update(initial_document_context_state)
                state.context_data["session_id"] = session_id
                state.context_data["conversation_id"] = session_id
                state.context_data["request_id"] = request_id
                state.context_data["user_id"] = user_id
                # v2.9/v2.10: Inject spine directives into workflow state
                for _spine_key in ("spine_response_directive", "spine_chronicle_summary",
                                   "spine_fatigue_context", "spine_retrieval_directive",
                                   "spine_ux_directive", "spine_community_directive",
                                   "spine_skill_directive", "spine_causal_trace_id",
                                   "aurora_l1"):
                    _spine_val = (request_extra_context or {}).get(_spine_key)
                    if _spine_val:
                        state.context_data[_spine_key] = _spine_val
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

                await self._attach_aurora_planning_sidecar(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    request_id=request_id,
                    user_message=user_message,
                    request_extra_context=request_extra_context,
                    conversation_context=conversation_context,
                    user_context_payload=user_context_payload,
                    state=state,
                )

                # Bound stream buffering while preserving critical terminal/content events.
                async def stream_callback(resp: agent_service_pb2.ChatResponse):
                    resp.response_id = response_id
                    resp.created_at = int(datetime.now().timestamp())
                    resp.request_id = request_id
                    resp.session_id = resp.session_id or session_id
                    resp.workflow_id = resp.workflow_id or workflow_id
                    resp.prompt_version = resp.prompt_version or prompt_version
                    resp.trace_id = resp.trace_id or trace_id
                    try:
                        await self._enqueue_stream_response(queue, resp)
                    except TimeoutError:
                        logger.error(
                            "Timed out while enqueueing critical stream response "
                            f"(response_id={resp.response_id}, finish_reason={resp.finish_reason}, "
                            f"content={resp.WhichOneof('content')})"
                        )

                run_ledger = RunLedgerRecorder(
                    trace_id=trace_id,
                    session_id=session_id,
                    workflow_id=workflow_id,
                    response_id=response_id,
                    prompt_version=prompt_version,
                    request_id=request_id,
                    redis_client=self.redis,
                    stream_callback=stream_callback,
                )
                state.context_data["run_ledger"] = run_ledger
                await run_ledger.record_event(
                    event_type="run_started",
                    label="运行开始",
                    workflow_stage="orchestration",
                    metadata={
                        "chat_mode": chat_mode,
                        "workflow_id": workflow_id,
                        "prompt_version": prompt_version,
                    },
                    emit_snapshot=False,
                )
                await self._emit_early_ack_progress(
                    stream_callback=stream_callback,
                    chat_mode=chat_mode,
                )

                # v2.10: Emit UXDirective metadata for Flutter status band + receipt display
                # R5-DF4: Use 'spine_ux_warning' to match Flutter websocket_chat_service_v2 listener
                _spine_ux_data = (request_extra_context or {}).get("spine_ux_directive")
                if _spine_ux_data and stream_callback:
                    try:
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                metadata={
                                    "spine_ux_warning": json.dumps(_spine_ux_data, ensure_ascii=False),
                                },
                            )
                        )
                    except Exception as _ux_err:
                        logger.debug(f"Spine UX directive emission skipped: {_ux_err}")

                _spine_trace_id = (request_extra_context or {}).get("spine_causal_trace_id")
                if _spine_trace_id and stream_callback:
                    try:
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                metadata={"spine_causal_trace_id": str(_spine_trace_id)},
                            )
                        )
                    except Exception:
                        logger.debug("stream_callback failed for spine_causal_trace_id, stream may be closed")

                _aurora_l1 = (request_extra_context or {}).get("aurora_l1")
                if _aurora_l1 and stream_callback:
                    try:
                        await stream_callback(
                            agent_service_pb2.ChatResponse(
                                metadata={"aurora_l1": json.dumps(_aurora_l1, ensure_ascii=False)},
                            )
                        )
                    except Exception:
                        logger.debug("stream_callback failed for aurora_l1, stream may be closed")

                # v2.11: Emit growth card metadata for Flutter (divine moment #1 看见坚持)
                if stream_callback:
                    try:
                        _growth_raw = await self.redis.get(f"spine:card:growth:{user_id}:latest")
                        if _growth_raw:
                            _growth_data = json.loads(_growth_raw if isinstance(_growth_raw, str) else _growth_raw.decode())
                            await stream_callback(
                                agent_service_pb2.ChatResponse(
                                    metadata={
                                        "spine_growth_card": json.dumps(_growth_data, ensure_ascii=False),
                                    },
                                ),
                            )
                    except Exception:
                        logger.debug("stream_callback failed for spine_growth_card, stream may be closed")

                # MAGIC-002~006: Emit unified divine moment card metadata for Flutter
                if stream_callback:
                    _divine_card_keys = [
                        ("correction_impact", "spine:card:correction_impact:{user_id}:latest"),
                        ("material_non_use", "spine:card:material_non_use:{user_id}:latest"),
                        ("absence_notice", "spine:card:absence_notice:{user_id}:latest"),
                        ("low_yield_block", "spine:card:low_yield_block:{user_id}:latest"),
                        ("community_strategy", "spine:card:community_hint:{user_id}:latest"),
                    ]
                    for _dm_type, _key_template in _divine_card_keys:
                        try:
                            _raw = await self.redis.get(_key_template.format(user_id=user_id))
                            if _raw:
                                _data = json.loads(_raw if isinstance(_raw, str) else _raw.decode())
                                _data["divine_moment_type"] = _dm_type
                                await stream_callback(
                                    agent_service_pb2.ChatResponse(
                                        metadata={
                                            "spine_divine_moment": json.dumps(_data, ensure_ascii=False),
                                        },
                                    ),
                                )
                        except Exception:
                            logger.debug(
                                "stream_callback failed for spine_divine_moment type=%s", _dm_type,
                            )

                # STAB-012: Emit spine degraded flag when Spine pipeline failed
                if request_extra_context and request_extra_context.get("spine_degraded"):
                    if stream_callback:
                        try:
                            await stream_callback(
                                agent_service_pb2.ChatResponse(
                                    metadata={"spine_degraded": "true"},
                                ),
                            )
                        except Exception:
                            logger.debug("stream_callback failed for spine_degraded, stream may be closed")

                state.context_data["resolved_active_tools"] = list(resolved_active_tools)

                if chat_mode == CHAT_MODE_STANDARD and not request.HasField("tool_result"):
                    fast_track_handled = await self._fast_track_exam_sprint(
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        request_extra_context=request_extra_context,
                        user_context_payload=user_context_payload,
                        stream_callback=stream_callback,
                    )
                    if fast_track_handled:
                        async for queued in self._drain_queue(queue):
                            yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                        await self._update_state(session_id, STATE_DONE, "Exam sprint fast-track completed")
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                        COLLABORATION_SUCCESS.labels(
                            workflow_type="standard_chat", agents_used="orchestrator", outcome="success"
                        ).inc()
                        return

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
                    visible_update_context,
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
                if isinstance(visible_update_context, dict):
                    state.context_data["visible_update_context"] = visible_update_context
                    if isinstance(user_context_payload, dict):
                        for key, value in visible_update_context.items():
                            if isinstance(value, list):
                                if value:
                                    user_context_payload[key] = value
                            elif str(value or "").strip():
                                user_context_payload[key] = str(value).strip()
                        if evolution_highlights:
                            user_context_payload["evolution_highlights"] = evolution_highlights
                for update_resp in update_responses:
                    yield self._bind_response_session_id(update_resp, session_id, request_id=request_id)

                user_context_payload = await self._attach_active_intervention_state(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    user_context_payload=user_context_payload,
                    state=state,
                )

                await self._hydrate_companion_runtime_context(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    plan_id=plan_id,
                    user_context_payload=user_context_payload,
                    state=state,
                )
                soul_runtime_payload = None
                try:
                    soul_runtime_payload = await attach_shadow_soul_runtime(
                        target_context=state.context_data,
                        redis_client=self.redis,
                        user_id=user_id,
                        user_context=user_context_payload,
                        plan_context=plan_context,
                        effective_companion_state=state.context_data.get("effective_companion_state"),
                        relationship_profile=state.context_data.get("relationship_profile"),
                        recent_revisions=state.context_data.get("companion_state_recent_revisions"),
                    )
                except Exception as exc:
                    logger.warning(f"Shadow soul runtime attach failed (non-fatal): {exc}")
                if isinstance(user_context_payload, dict):
                    self._copy_companion_runtime_keys(
                        source_context=state.context_data, target_context=user_context_payload
                    )
                if soul_runtime_payload is not None:
                    await run_ledger.record_event(
                        event_type="soul_runtime_shadow_compiled",
                        label="Soul shadow ready",
                        workflow_stage="orchestration",
                        metadata={
                            "compiler_version": soul_runtime_payload.debug.get("compiler_version"),
                            "constitution_version": soul_runtime_payload.debug.get("constitution_version"),
                            "identity_kernel_version": soul_runtime_payload.debug.get("identity_kernel_version"),
                            "dual_core_source": soul_runtime_payload.debug.get("dual_core_source"),
                            "dual_core_mode": soul_runtime_payload.debug.get("dual_core_mode"),
                        },
                        emit_snapshot=False,
                    )

                # Step 5: Sufficiency check (may short-circuit)
                sufficiency_handled, intent_type = await self._check_sufficiency(
                    request=request,
                    user_message=user_message,
                    user_id=user_id,
                    plan_id=plan_id,
                    session_id=session_id,
                    conversation_context=conversation_context,
                    user_context_payload=user_context_payload,
                    plan_context=plan_context,
                    state=state,
                    active_db=active_db,
                    session_feedback_signal=(
                        session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                    ),
                    stream_callback=stream_callback,
                    queue=queue,
                )
                if sufficiency_handled:
                    async for queued in self._drain_queue(queue):
                        yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                    return
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
                        yield self._bind_response_session_id(queued, session_id, request_id=request_id)
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
                    try:
                        await attach_shadow_soul_runtime(
                            target_context=state.context_data,
                            redis_client=self.redis,
                            user_id=user_id,
                            user_context=user_context_payload,
                            plan_context=plan_context,
                            effective_companion_state=state.context_data.get("effective_companion_state"),
                            relationship_profile=state.context_data.get("relationship_profile"),
                            recent_revisions=state.context_data.get("companion_state_recent_revisions"),
                        )
                    except Exception as exc:
                        logger.warning(f"Shadow soul runtime refresh failed (non-fatal): {exc}")
                    if isinstance(user_context_payload, dict):
                        self._copy_companion_runtime_keys(
                            source_context=state.context_data,
                            target_context=user_context_payload,
                        )
                    user_context_payload = await self._attach_user_strategy_state(
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        plan_id=plan_id,
                        user_context_payload=user_context_payload,
                        state=state,
                    )
                    user_context_payload = await self._attach_situation_brief(
                        active_db=active_db,
                        user_id=user_id,
                        user_context_payload=user_context_payload,
                        plan_context=plan_context,
                        state=state,
                        session_feedback_signal=(
                            session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                        ),
                    )
                    if active_db is not None and isinstance(user_context_payload, dict):
                        await ExperienceActuator(active_db, getattr(self, "redis", None)).apply(
                            user_id=user_id,
                            session_id=session_id,
                            plan_id=plan_id,
                            request_id=request_id,
                            user_message=user_message,
                            file_ids=effective_file_ids,
                            use_document_context=request_use_document_context,
                            user_context_payload=user_context_payload,
                            context_targets=[state.context_data],
                        )
                    user_context_payload = await self._hydrate_document_context(
                        active_db=active_db,
                        user_id=user_id,
                        user_message=user_message,
                        route_intent=infer_route_intent_from_chat_mode(chat_mode),
                        user_context_payload=user_context_payload,
                        state=state,
                    )
                    user_context_payload = attach_goal_realization_context(
                        user_context_payload=user_context_payload,
                        state_context=state.context_data,
                    )

                # Step 6: Prepare runtime context (transparency, tools)
                transparency_generator, emit_transparency_event = await self._prepare_runtime_context(
                    state,
                    request_id,
                    response_id,
                    resolved_active_tools,
                    stream_callback,
                    tracer,
                )

                if request.HasField("tool_result"):
                    async for queued in self._drain_queue(queue):
                        yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                    last_tool_response = None
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
                        last_tool_response = continued_response
                        yield continued_response
                    if last_tool_response is not None and last_tool_response.HasField("error"):
                        await self._update_state(session_id, STATE_FAILED, "Tool result continuation error")
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="error").inc()
                    else:
                        await self._update_state(session_id, STATE_DONE, "Tool result continuation completed")
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                        COLLABORATION_SUCCESS.labels(
                            workflow_type="standard_chat", agents_used="orchestrator", outcome="success"
                        ).inc()
                    return

                aurora_surface = self._resolve_aurora_runtime_surface(request_extra_context)
                if aurora_surface is not None:
                    # L1 fast path: when L1 determines no escalation needed, skip the
                    # expensive Aurora LLM decision loop and fall through to standard chat.
                    _aurora_l1 = (request_extra_context or {}).get("aurora_l1")
                    _l1_should_escalate = True
                    if isinstance(_aurora_l1, dict):
                        _l1_should_escalate = bool(_aurora_l1.get("should_escalate", True))
                    if not _l1_should_escalate:
                        logger.debug(
                            "L1 fast path: skipping Aurora LLM for user={}, band={}",
                            user_id,
                            _aurora_l1.get("status_band_hint", "unknown"),
                        )
                        # Fall through to standard chat — the aurora_l1 metadata was
                        # already forwarded to Flutter at the pre-processing stage.
                    else:
                        await self._update_state(session_id, STATE_GENERATING, f"Aurora runtime v1 ({aurora_surface})")
                        async for queued in self._drain_queue(queue):
                            yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                        async for aurora_response in self._stream_aurora_runtime_v1(
                            request=request,
                            active_db=active_db,
                            user_id=user_id,
                            session_id=session_id,
                            response_id=response_id,
                            request_id=request_id,
                            trace_id=trace_id,
                            workflow_id=workflow_id,
                            prompt_version=prompt_version,
                            request_extra_context=request_extra_context,
                            conversation_context=conversation_context,
                            user_context_payload=user_context_payload,
                        ):
                            yield aurora_response
                        await self._update_state(session_id, STATE_DONE, f"Aurora runtime v1 completed ({aurora_surface})")
                        REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                        COLLABORATION_SUCCESS.labels(
                            workflow_type=workflow_id, agents_used="aurora_runtime_v1", outcome="success"
                        ).inc()
                        return

                # Step 7: Notifications
                await self._notify_pending_milestone_proposals(user_id, stream_callback)
                if plan_switched and plan_id:
                    await stream_callback(
                        agent_service_pb2.ChatResponse(
                            metadata={
                                "plan_switched": "true",
                                "switched_to_plan_id": str(plan_id),
                                "session_id": session_id,
                            }
                        )
                    )

                # Step 8: Inject dependencies into state
                self._inject_state_dependencies(
                    state,
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    tools_schema=state.context_data.get("tools_schema", []),
                    transparency_generator=transparency_generator,
                    emit_transparency_event=emit_transparency_event,
                    user_context_payload=user_context_payload,
                    conversation_context=conversation_context,
                    plan_context=plan_context,
                    file_ids=effective_file_ids,
                    include_references=bool(request.include_references),
                    workflow_id=workflow_id,
                    prompt_version=prompt_version,
                    run_ledger=run_ledger,
                )
                if context_data:
                    state.update(context_data)
                state.context_data["chat_mode"] = chat_mode
                orchestration_trace = OrchestrationTrace(trace_id=trace_id or request_id or str(uuid.uuid4()))
                self._sync_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    user_context_payload=user_context_payload,
                )
                capability_selection_report = state.context_data.get("capability_selection_report")
                capability_specialist = (
                    capability_selection_report.get("specialist_selection")
                    if isinstance(capability_selection_report, dict)
                    else None
                )
                capability_strategy = (
                    str(capability_specialist.get("strategy") or "").strip()
                    if isinstance(capability_specialist, dict)
                    else ""
                )
                capability_experts = (
                    [
                        str(item).strip()
                        for item in capability_specialist.get("selected_experts", [])
                        if str(item).strip()
                    ]
                    if isinstance(capability_specialist, dict)
                    else []
                )

                if requested_experts:
                    state.context_data["selected_experts"] = list(requested_experts)
                    state.context_data["expert_policy_id"] = "custom_team_v1" if team_spec else "explicit_custom_expert"
                elif capability_strategy == "specialist_required" and capability_experts:
                    state.context_data["selected_experts"] = list(capability_experts)
                    state.context_data["expert_policy_id"] = "phase_d_capability_policy_v1"
                    state.context_data["expert_routing_metadata"] = {
                        "selected_experts": json.dumps(capability_experts, ensure_ascii=False),
                        "routing_strategy": "phase_d_capability_policy",
                        "fallback_reason": "",
                        "route_confidence": "0.80",
                        "expert_entry_source": "phase_d",
                        "policy_id": "phase_d_capability_policy_v1",
                        "complexity_score": "0.70",
                        "complexity_tier": "medium",
                    }
                elif expert_routing_decision and capability_strategy != "simple_path":
                    state.context_data["expert_routing_metadata"] = expert_routing_decision.to_metadata()
                    state.context_data["selected_experts"] = list(expert_routing_decision.selected_experts)
                    state.context_data["expert_policy_id"] = expert_routing_decision.policy_id
                if answer_experts:
                    state.context_data["answer_experts"] = list(answer_experts)
                if custom_expert_profiles:
                    state.context_data["_custom_expert_profiles"] = dict(custom_expert_profiles)

                selected_for_preview = []
                if isinstance(state.context_data.get("selected_experts"), list):
                    selected_for_preview = [
                        str(item).strip()
                        for item in state.context_data.get("selected_experts", [])
                        if str(item).strip()
                    ]
                elif expert_routing_decision and expert_routing_decision.selected_experts:
                    selected_for_preview = list(expert_routing_decision.selected_experts)
                if selected_for_preview:
                    routing_preview = await emit_routing_preview(
                        stream_callback,
                        selected_experts=selected_for_preview,
                        complexity_score=(
                            expert_routing_decision.complexity_score if expert_routing_decision else 0.45
                        ),
                        complexity_tier=(
                            expert_routing_decision.complexity_tier if expert_routing_decision else "medium"
                        ),
                        route_confidence=(expert_routing_decision.route_confidence if expert_routing_decision else 0.7),
                        routing_strategy=(
                            expert_routing_decision.routing_strategy if expert_routing_decision else "explicit_team"
                        ),
                    )
                    state.context_data["routing_preview"] = routing_preview
                    for index, expert_id in enumerate(selected_for_preview):
                        await emit_agent_activity(
                            stream_callback,
                            agent_id=expert_id,
                            status="pending",
                            metadata={
                                "phase": "roundtable",
                                "queue_index": index,
                                "collaboration_mode": (state.context_data.get("collaboration_mode") or "expert"),
                            },
                        )

                # Step 9: Non-standard mode fallback only when unified graph routing is explicitly disabled.
                if chat_mode != CHAT_MODE_STANDARD and not settings.ENABLE_UNIFIED_GRAPH_ROUTING:
                    mode_result: dict[str, Any] = {}
                    async for resp in self._handle_multi_agent_mode(
                        state=state,
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
                        yield self._bind_response_session_id(resp, session_id, request_id=request_id)
                    final_response_data = mode_result.get("final_response_data")
                    if isinstance(final_response_data, dict):
                        await self._cache_response(session_id, request_id, final_response_data)
                        followup_updates, _, _, _, _, _, _ = await self._drain_system_updates(user_id)
                        for update_resp in followup_updates:
                            yield self._bind_response_session_id(update_resp, session_id, request_id=request_id)
                    return

                # Step 10: Route with unified orchestration brain for all modes
                route_started_at = time.perf_counter()
                route_decision, unified_routing_result = await self._route_and_classify(
                    user_message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    grpc_context=grpc_context,
                    conversation_context=conversation_context,
                    state=state,
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
                await run_ledger.record_event(
                    event_type="route_selected",
                    label="路由决策",
                    workflow_stage="routing",
                    metadata={
                        "execution_mode": route_decision.execution_mode,
                        "reason": route_decision.reason,
                        "risk_level": route_decision.risk_level,
                        "confidence": route_decision.confidence,
                        "intent": (
                            unified_routing_result.primary_intent.value
                            if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                            else ""
                        ),
                    },
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
                            f"{chat_mode} mode requires {', '.join(mode_strategy_metadata.get('required_agents') or mode_strategy_metadata.get('preferred_agents') or ['auto-selected'])} collaboration"
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
                    session_id=session_id,
                    request_id=request_id,
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
                    reason=str(dual_core_decision.get("reason") or "系统判断当前需要同时兼顾理解用户状态与推进执行。"),
                    metadata={
                        "mode": dual_core_decision.get("mode"),
                        "cognitive_adjustments": dual_core_decision.get("cognitive_adjustments", []),
                        "structured_adjustments": dual_core_decision.get("structured_adjustments", []),
                        "execution_constraints": dual_core_decision.get("execution_constraints", []),
                        "signal_scores": dual_core_decision.get("signal_scores", {}),
                        "routing_trace_id": dual_core_decision.get("routing_trace_id"),
                        "scaffolding_zone": dual_core_decision.get("scaffolding_zone"),
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
                try:
                    await attach_shadow_soul_runtime(
                        target_context=state.context_data,
                        redis_client=self.redis,
                        user_id=user_id,
                        user_context=user_context_payload,
                        plan_context=plan_context,
                        effective_companion_state=state.context_data.get("effective_companion_state"),
                        relationship_profile=state.context_data.get("relationship_profile"),
                        recent_revisions=state.context_data.get("companion_state_recent_revisions"),
                    )
                except Exception as exc:
                    logger.warning(f"Shadow soul runtime refresh failed (non-fatal): {exc}")
                if isinstance(user_context_payload, dict):
                    self._copy_companion_runtime_keys(
                        source_context=state.context_data, target_context=user_context_payload
                    )
                user_context_payload = await self._attach_user_strategy_state(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    plan_id=plan_id,
                    user_context_payload=user_context_payload,
                    state=state,
                )
                user_context_payload = await self._attach_situation_brief(
                    active_db=active_db,
                    user_id=user_id,
                    user_context_payload=user_context_payload,
                    plan_context=plan_context,
                    state=state,
                    session_feedback_signal=(
                        session_feedback_signal.to_dict() if session_feedback_signal is not None else None
                    ),
                )
                if active_db is not None and isinstance(user_context_payload, dict):
                    await ExperienceActuator(active_db, getattr(self, "redis", None)).apply(
                        user_id=user_id,
                        session_id=session_id,
                        plan_id=plan_id,
                        request_id=request_id,
                        user_message=user_message,
                        file_ids=effective_file_ids,
                        use_document_context=request_use_document_context,
                        user_context_payload=user_context_payload,
                        context_targets=[state.context_data],
                    )
                user_context_payload = await self._hydrate_document_context(
                    active_db=active_db,
                    user_id=user_id,
                    user_message=user_message,
                    route_intent=(
                        unified_routing_result.primary_intent.value
                        if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                        else intent_type
                    ),
                    user_context_payload=user_context_payload,
                    state=state,
                )
                user_context_payload = attach_goal_realization_context(
                    user_context_payload=user_context_payload,
                    state_context=state.context_data,
                )

                # Step 11: Plan & validate (langgraph/hybrid mode)
                route_decision, executable_plan, snapshot, should_return = await self._plan_and_validate(
                    route_decision=route_decision,
                    user_message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    active_db=active_db,
                    plan_id=plan_id,
                    conversation_context=conversation_context,
                    plan_context=plan_context,
                    stream_callback=stream_callback,
                    state=state,
                    user_context_payload=user_context_payload,
                    orchestration_trace=orchestration_trace,
                )
                await self._emit_orchestration_trace(
                    state=state,
                    orchestration_trace=orchestration_trace,
                    stream_callback=stream_callback,
                )
                if should_return:
                    async for queued in self._drain_queue(queue):
                        yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                    return

                # Step 12: Log route decision
                route_intent = (
                    unified_routing_result.primary_intent.value
                    if unified_routing_result
                    else self._extract_route_intent(route_decision.reason)
                )
                plan_meta = state.context_data.get("plan_metadata", {})
                await self.observability.log_route_decision(
                    user_id=user_id,
                    session_id=session_id,
                    message=user_message,
                    decision={
                        "execution_mode": route_decision.execution_mode,
                        "risk_level": route_decision.risk_level,
                        "reason": route_decision.reason,
                        "intent": route_intent,
                        "confidence": route_decision.confidence,
                        "routing_layer": plan_meta.get("routing_layer", "unknown"),
                        "adaptive_notes": plan_meta.get("adaptive_notes", ""),
                        "summary_used_for_routing": plan_meta.get("summary_used_for_routing", "false"),
                    },
                )

                # Step 13: Execute graph
                result_holder: dict[str, Any] = {}
                async for item in self._execute_graph(
                    state=state, user_id=user_id, queue=queue, result_holder=result_holder
                ):
                    yield item

                # Step 14: Build & yield final response
                final_state = result_holder.get("final_state")
                if final_state is not None:
                    total_prompt_tokens = result_holder.get("total_prompt_tokens", 0)
                    total_completion_tokens = result_holder.get("total_completion_tokens", 0)
                    final_response, final_response_data = await self._build_final_response(
                        final_state=final_state,
                        executable_plan=executable_plan,
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        response_id=response_id,
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        route_decision=route_decision,
                        plan_switched=plan_switched,
                        plan_id=plan_id,
                        plan_context=plan_context,
                        user_context_payload=user_context_payload,
                        total_prompt_tokens=total_prompt_tokens,
                        total_completion_tokens=total_completion_tokens,
                    )
                    await self._cache_response(session_id, request_id, final_response_data)
                    await self._write_turn_end_episodic_memory(
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        request_id=request_id,
                        user_message=user_message,
                        assistant_message=str(final_response_data.get("message") or ""),
                        event_kind="task_completed",
                        request_extra_context=request_extra_context,
                        user_context_payload=user_context_payload,
                        final_state=final_state,
                        final_response_data=final_response_data,
                        plan_context=plan_context,
                        turn_started_at=turn_started_at,
                    )
                    try:
                        turn_index = 1
                        if isinstance(conversation_context, dict):
                            messages = conversation_context.get("messages")
                            if isinstance(messages, list):
                                user_count = sum(
                                    1 for msg in messages if isinstance(msg, dict) and msg.get("role") == "user"
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

                        # Schedule automatic skill extraction when user uses trigger phrases
                        _assistant_text = str(final_response_data.get("message") or "")
                        if user_message and _assistant_text:
                            try:
                                from app.services.skill_extract_service import SkillExtractService
                                _skill_svc = SkillExtractService()
                                if _skill_svc.matches_explicit_trigger(user_message):

                                    async def _extract_and_persist_skill():
                                        try:
                                            draft = await _skill_svc.generate_draft(
                                                trigger_type="explicit_phrase",
                                                consent_text=user_message,
                                                user_message=user_message,
                                                assistant_message=_assistant_text,
                                                seconds_since_response=0,
                                            )
                                            from app.db.session import AsyncSessionLocal
                                            from app.services.skill_store import SkillStoreService
                                            from app.services.skill_schema import draft_to_payload
                                            async with AsyncSessionLocal() as db:
                                                await SkillStoreService(db).create_skill(
                                                    user_id=user_id,
                                                    payload=draft_to_payload(draft),
                                                )
                                            _skill_svc.record_draft_outcome(accepted=True)
                                            logger.info(
                                                "Skill extracted and persisted: user=%s name=%s",
                                                user_id, draft.name,
                                            )
                                        except ValueError as _ve:
                                            _skill_svc.record_draft_outcome(accepted=False)
                                            logger.debug("Skill extract skipped for user=%s: %s", user_id, _ve)
                                        except Exception as _persist_exc:
                                            _skill_svc.record_draft_outcome(accepted=False)
                                            logger.warning(
                                                "Skill extract persistence failed for user=%s: %s",
                                                user_id, _persist_exc,
                                            )

                                    _skill_task = asyncio.create_task(_extract_and_persist_skill())
                                    self._track_task(_skill_task)
                                    logger.info(
                                        "Skill extract draft scheduled: user={} session={}",
                                        user_id, session_id,
                                    )
                            except Exception as _skill_exc:
                                logger.debug("Skill extract schedule skipped: {}", _skill_exc)
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
                    followup_updates, _, _, _, _, _, _ = await self._drain_system_updates(user_id)
                    for update_resp in followup_updates:
                        yield self._bind_response_session_id(update_resp, session_id, request_id=request_id)
                    completion_note = "Response completed"
                    if final_state.is_finished:
                        completion_note = f"Response completed (graph truncated: max steps reached)"
                    await self._update_state(
                        session_id,
                        STATE_DONE,
                        completion_note,
                        request_id=request_id,
                        user_id=user_id,
                    )
                    await self._maybe_upsert_session_mood(
                        active_db=active_db,
                        user_id=user_id,
                        session_id=session_id,
                        request_extra_context=request_extra_context,
                        conversation_context=conversation_context,
                    )
                    yield self._bind_response_session_id(final_response, session_id, request_id=request_id)

                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                COLLABORATION_SUCCESS.labels(
                    workflow_type="standard_chat", agents_used="orchestrator", outcome="success"
                ).inc()

            except asyncio.CancelledError:
                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="cancelled").inc()
                logger.warning("Orchestration cancelled for session {}", session_id)
                raise
            except Exception as e:
                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="error").inc()
                COLLABORATION_SUCCESS.labels(
                    workflow_type="standard_chat", agents_used="orchestrator", outcome="error"
                ).inc()
                logger.opt(exception=e).error("Orchestration Error")
                await self._update_state(
                    session_id,
                    STATE_FAILED,
                    str(e),
                    request_id=request_id,
                    user_id=user_id,
                )
                await self._write_turn_end_episodic_memory(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    request_id=request_id,
                    user_message=user_message if "user_message" in locals() else "",
                    assistant_message="",
                    event_kind="error",
                    request_extra_context=(request_extra_context if "request_extra_context" in locals() else None),
                    user_context_payload=(user_context_payload if "user_context_payload" in locals() else None),
                    final_state=state if "state" in locals() else None,
                    plan_context=plan_context if "plan_context" in locals() else None,
                    turn_started_at=turn_started_at if "turn_started_at" in locals() else None,
                    error=e,
                )
                if transparency_generator is not None and emit_transparency_event is not None:
                    await emit_transparency_event(transparency_generator.get_complete_event())
                # ✅ Fix C4: Drain queue before yielding error to ensure all queued messages are sent
                async for queued in self._drain_queue(queue):
                    yield self._bind_response_session_id(queued, session_id, request_id=request_id)
                safe_message, error_code, retryable = build_safe_chat_error(e)
                yield agent_service_pb2.ChatResponse(
                    response_id=response_id,
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    error=agent_service_pb2.Error(
                        message=safe_message,
                        retryable=retryable,
                        error_code=error_code,
                    ),
                    finish_reason=agent_service_pb2.ERROR,
                    session_id=session_id,
                )

            finally:
                await self._cleanup(
                    lock_acquired=lock_acquired,
                    lock_renewal_task=lock_renewal_task,
                    lock_renewal_stop=lock_renewal_stop,
                    session_id=session_id,
                    request_id=request_id,
                    start_time=start_time,
                    user_id=user_id,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                    final_state=result_holder.get("final_state") if "result_holder" in locals() else None,
                    chat_mode_hint=chat_mode if "chat_mode" in locals() else None,
                    reasoning_mode_hint=(
                        str((context_data or {}).get("reasoning_mode") or "balanced")
                        if isinstance(context_data, dict)
                        else None
                    ),
                )
        finally:
            ACTIVE_SESSIONS.dec()
            span.end()


# Backwards-compatible alias for benchmarks/tests
Orchestrator = ChatOrchestrator
