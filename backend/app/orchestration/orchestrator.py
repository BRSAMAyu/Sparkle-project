import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict
from loguru import logger
from opentelemetry import trace
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.standard_workflow import create_standard_chat_graph
from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.config import settings
from app.core.business_metrics import COLLABORATION_LATENCY, COLLABORATION_SUCCESS, HITL_REQUESTED
from app.core.metrics import (
    ACTIVE_SESSIONS,
    ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    RESPONSE_FALLBACK_GENERATED_TOTAL,
    ROUTING_SUMMARY_CONTEXT_TOTAL,
    TOKEN_USAGE,
)
from app.core.pending_actions import pending_actions_store
from app.core.task_manager import task_manager
from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan
from app.models.cognitive import CognitiveFragment
from app.models.galaxy import KnowledgeNode
from app.models.task import Task
from app.models.task import TaskStatus as ModelTaskStatus
from app.models.task_feedback import TaskFeedback

# Phase 3: Circuit Breaker, Observability, Shadow Mode
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
from app.orchestration.composer import ResponseComposer
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router
from app.orchestration.executor import ToolExecutor
from app.orchestration.goal_quality_evaluator import goal_quality_evaluator
from app.orchestration.grounding_validator import GroundingValidator
from app.orchestration.lang_graph_planner import LangGraphPlanner

# Multi-Agent Mode Support
from app.orchestration.chat_modes import (
    CHAT_MODE_STANDARD,
    is_expert_chat_mode,
    normalize_chat_mode,
)
from app.orchestration.expert_strategy import ExpertStrategyV1
from app.orchestration.mode_workflow_config import get_workflow_config
from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter, execute_multi_agent_workflow
from app.orchestration.observability_logger import observability_logger
from app.orchestration.plan_review_service import ReviewDecision, plan_review_service

# Phase 1 & Phase 2: Full-Loop Closed System with LangGraph Planner
from app.orchestration.route_adapter import to_route_decision
from app.orchestration.schemas import (
    ExecutablePlan,
    RouteDecision,
    StateSnapshot,
)
from app.orchestration.state_manager import SessionStateManager
from app.orchestration.state_snapshot import StateSnapshotManager
from app.orchestration.statechart_engine import WorkflowState

# Phase 4: Sufficiency Checking
from app.orchestration.sufficiency_checker import SufficiencyStatus, sufficiency_checker
from app.orchestration.token_tracker import TokenTracker

# Phase 5: Plan Execution Validation
from app.orchestration.tool_result_extractor import ToolResultExtractor
from app.orchestration.transparency_data_generator import StepType, TransparencyDataGenerator
from app.orchestration.ux_envelope import ux_envelope_builder
from app.orchestration.validator import RequestValidator
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.services.focus_service import focus_service
from app.services.llm_service import llm_service
from app.services.plan_progress_service import PlanProgressService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.services.plan_execution_record_service import PlanExecutionRecordService
from app.services.plan_execution_validator import PlanExecutionValidator
from app.services.shadow_prediction_service import shadow_prediction_service
from app.services.system_update_service import SystemUpdateService
from app.services.user_service import UserService

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


class ChatOrchestrator:
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

    async def _drain_system_updates(
        self,
        user_id: str,
    ) -> tuple[list[agent_service_pb2.ChatResponse], list[dict[str, Any]], list[dict[str, Any]], list[str], dict[str, Any] | None]:
        updates = await SystemUpdateService(getattr(self, "redis", None)).drain(user_id, limit=20)
        responses: list[agent_service_pb2.ChatResponse] = []
        adaptation_records: list[dict[str, Any]] = []
        preference_learnings: list[dict[str, Any]] = []
        evolution_highlights: list[str] = []
        progress_snapshot: dict[str, Any] | None = None
        for update in updates:
            metadata = update.get("metadata") if isinstance(update, dict) else None
            if isinstance(metadata, dict):
                if metadata.get("evolution_kind") == "adaptation_record" and isinstance(metadata.get("adaptation_record"), dict):
                    adaptation_records.append(metadata["adaptation_record"])
                if metadata.get("evolution_kind") == "preference_learning" and isinstance(metadata.get("preference_learning"), dict):
                    preference_learnings.append(metadata["preference_learning"])
                if metadata.get("evolution_kind") == "highlight" and metadata.get("highlight"):
                    evolution_highlights.append(str(metadata["highlight"]).strip())
                if metadata.get("evolution_kind") == "progress_snapshot" and isinstance(metadata.get("progress_snapshot"), dict):
                    progress_snapshot = metadata["progress_snapshot"]
            widget_struct = struct_pb2.Struct()
            widget_struct.update(update)
            responses.append(
                agent_service_pb2.ChatResponse(
                    tool_result=agent_service_pb2.ToolResultPayload(
                        tool_name="system_update",
                        success=True,
                        widget_type="system_update",
                        widget_data=widget_struct,
                        tool_call_id="",
                    )
                )
            )
        if progress_snapshot:
            evolution_highlights = [*evolution_highlights[:2], *(progress_snapshot.get("highlights") or [])[:1]]
        return responses, adaptation_records[:3], preference_learnings[:3], evolution_highlights[:3], progress_snapshot

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

    async def _update_state(self, session_id: str, state: str, details: str = ""):
        """Update FSM State in Redis with persistence"""
        if self.state_manager:
            await self.state_manager.update_state(
                session_id=session_id,
                state=state,
                details=details,
                request_id=None,  # Will be set in process_stream
                user_id=None
            )
        logger.info(f"Session {session_id} State: {state} ({details})")

    async def _check_idempotency(self, session_id: str, request_id: str) -> dict[str, Any] | None:
        """
        Check if request was already processed

        Returns:
            Optional[Dict]: Cached response if duplicate, None otherwise
        """
        if not self.state_manager or not request_id:
            return None

        return await self.state_manager.get_cached_response(session_id, request_id)

    async def _acquire_session_lock(self, session_id: str, request_id: str) -> bool:
        """Acquire distributed lock for session"""
        if not self.state_manager:
            return True

        return await self.state_manager.acquire_lock(session_id, request_id)

    async def _release_session_lock(self, session_id: str, request_id: str):
        """Release distributed lock"""
        if self.state_manager:
            await self.state_manager.release_lock(session_id, request_id)

    async def _cache_response(self, session_id: str, request_id: str, response_data: dict[str, Any]):
        """Cache response for idempotency"""
        if self.state_manager and request_id:
            await self.state_manager.cache_response(session_id, request_id, response_data)

    def _format_review_message(self, review_result) -> str:
        """Format plan review result as user-friendly message"""
        from app.orchestration.plan_review_service import ReviewDecision

        decision = review_result.decision
        comments = review_result.comments

        # Header based on decision
        if decision == ReviewDecision.REJECTED.value:
            header = "🚫 计划未通过审查"
        elif decision == ReviewDecision.NEEDS_MODIFICATION.value:
            header = "⚠️ 计划需要修改"
        elif decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            header = "🔍 需要确认计划"
        else:
            header = "✅ 计划已通过审查"

        lines = [f"\n\n{header}"]

        # Add comments by severity
        critical_comments = [c for c in comments if c.severity == "critical"]
        warning_comments = [c for c in comments if c.severity == "warning"]
        info_comments = [c for c in comments if c.severity == "info"]

        if critical_comments:
            lines.append("\n**严重问题:**")
            for c in critical_comments:
                lines.append(f"- {c.message}")
                if c.suggested_fix:
                    lines.append(f"  建议: {c.suggested_fix}")

        if warning_comments:
            lines.append("\n**警告:**")
            for c in warning_comments[:3]:  # Limit warnings
                lines.append(f"- {c.message}")

        if info_comments and decision != ReviewDecision.REJECTED.value:
            lines.append("\n**建议:**")
            for c in info_comments[:2]:  # Limit info comments
                lines.append(f"- {c.message}")

        # Add confidence indicator
        if review_result.confidence > 0:
            confidence_pct = int(review_result.confidence * 100)
            lines.append(f"\n置信度: {confidence_pct}%")

        # Add footer based on decision
        if decision == ReviewDecision.REJECTED.value:
            lines.append("\n请重新描述您的需求，我将为您重新规划。")
        elif decision == ReviewDecision.NEEDS_MODIFICATION.value:
            lines.append("\n请在下方补充说明修改要求，我将重新规划。")
        elif decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            lines.append("\n请确认是否执行此计划。")

        return "\n".join(lines)

    async def _load_context_versions(self, user_id: str) -> dict[str, str]:
        if not self.redis:
            return {}
        key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
        try:
            raw = await self.redis.get(key)
            if not raw:
                return {}
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Failed to load context versions: {e}")
        return {}

    async def _save_context_versions(self, user_id: str, versions: dict[str, str]) -> None:
        if not self.redis:
            return
        key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
        try:
            payload = json.dumps(versions, ensure_ascii=False)
            await self.redis.setex(key, CONTEXT_VERSION_TTL_SECONDS, payload)
        except Exception as e:
            logger.warning(f"Failed to save context versions: {e}")

    async def _self_heal_versions(
        self,
        user_id: str,
        overlay_versions: dict[str, str],
        db_session: AsyncSession | None,
    ) -> None:
        if not overlay_versions or not user_id:
            return

        previous = await self._load_context_versions(user_id)
        healed: list[str] = []

        for domain in REALTIME_VERSION_DOMAINS:
            new_v = overlay_versions.get(domain)
            if not new_v:
                continue
            old_v = previous.get(domain)
            if old_v == new_v:
                continue

            if domain == "prefs" and db_session:
                user_service = UserService(db_session, self.redis)
                await user_service.invalidate_user_cache(uuid.UUID(user_id))

            previous[domain] = new_v
            healed.append(f"{domain}:{old_v}->{new_v}")

        if healed:
            await self._save_context_versions(user_id, previous)
            logger.info("Context self-heal versions user=%s healed=%s", user_id, healed)

    def _merge_user_contexts(self, local_context: dict[str, Any], grpc_context: dict[str, Any]) -> dict[str, Any]:
        """
        P0: Merge user context from Go Gateway (gRPC) with local context (Python).
        Prioritizes gRPC context as it's more recent (fetched at request time).

        Returns:
            Merged context dict with both sources
        """
        if not grpc_context:
            return local_context

        merged = {}

        # Start with local context as base
        merged.update(local_context)

        # Override with gRPC context (prioritized as more recent)
        if "pending_tasks" in grpc_context:
            merged["next_actions"] = grpc_context["pending_tasks"]  # Normalize field name
        if "active_plans" in grpc_context:
            merged["active_plans"] = grpc_context["active_plans"]
        if "focus_stats" in grpc_context:
            merged["focus_stats"] = grpc_context["focus_stats"]
        if "recent_progress" in grpc_context:
            merged["recent_progress"] = grpc_context["recent_progress"]

        logger.debug(f"Merged context keys: {list(merged.keys())}")
        return merged

    async def _get_task_status_summary(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """Get summary of all tasks for user across all plans."""
        try:
            # Pending count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status == ModelTaskStatus.PENDING
                )
            )
            pending = result.scalar() or 0

            # In progress count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status == ModelTaskStatus.IN_PROGRESS
                )
            )
            in_progress = result.scalar() or 0

            # Overdue count (pending/in_progress and due_date < now)
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date < _utcnow()
                )
            )
            overdue = result.scalar() or 0

            return {
                "pending": pending,
                "in_progress": in_progress,
                "overdue": overdue
            }
        except Exception as e:
            logger.warning(f"Failed to get task status summary: {e}")
            return {"pending": 0, "in_progress": 0, "overdue": 0}

    async def _get_cognitive_insights(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """获取认知模式摘要，注入 LLM 上下文

        当用户有已识别的行为模式时，LLM 可以在合适时机主动展示认知棱镜。
        """
        try:
            from uuid import UUID

            from app.services.cognitive_service import CognitiveService

            cognitive = CognitiveService(db_session)
            patterns = await cognitive.get_user_patterns(UUID(user_id), min_confidence=0.6)

            if patterns:
                # 按类型分组
                by_type = {"cognitive": [], "emotional": [], "execution": []}
                for p in patterns:
                    by_type.setdefault(p.pattern_type, []).append(p.pattern_name)

                return {
                    "has_cognitive_patterns": True,
                    "pattern_count": len(patterns),
                    "recent_patterns": [p.pattern_name for p in patterns[:3]],
                    "patterns_by_type": {k: len(v) for k, v in by_type.items()}
                }
        except Exception as e:
            logger.warning(f"Failed to get cognitive insights for {user_id}: {e}")

        return {"has_cognitive_patterns": False}

    async def _get_recent_sentiment_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(CognitiveFragment.sentiment)
                .where(CognitiveFragment.user_id == uuid.UUID(user_id))
                .where(CognitiveFragment.sentiment.isnot(None))
                .order_by(desc(CognitiveFragment.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                sentiment = str(raw or "").strip().lower()
                if not sentiment:
                    continue
                distribution[sentiment] = distribution.get(sentiment, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent sentiment distribution: {e}")
            return {}

    async def _get_recent_task_feedback_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(TaskFeedback.category)
                .where(TaskFeedback.user_id == uuid.UUID(user_id))
                .where(TaskFeedback.category.isnot(None))
                .order_by(desc(TaskFeedback.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                category = str(raw or "").strip().lower()
                if not category:
                    continue
                distribution[category] = distribution.get(category, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent task feedback distribution: {e}")
            return {}

    @staticmethod
    def _extract_primary_challenge_area(
        plan_context: dict[str, Any] | None,
    ) -> str | None:
        if not isinstance(plan_context, dict):
            return None
        user_profile = plan_context.get("user_profile")
        if not isinstance(user_profile, dict):
            return None
        derived = user_profile.get("derived_insights")
        if not isinstance(derived, dict):
            return None
        value = derived.get("primary_challenge_area")
        return str(value).strip() if value else None

    @staticmethod
    def _extract_session_length_preference(
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
    ) -> int | None:
        facts = (plan_context or {}).get("facts") if isinstance(plan_context, dict) else None
        if isinstance(facts, dict):
            raw = facts.get("session_length_preference")
            if isinstance(raw, (int, float)):
                return int(raw)
        preferences = (user_context_payload or {}).get("preferences") if isinstance(user_context_payload, dict) else None
        if isinstance(preferences, dict):
            raw = preferences.get("focus_duration_preference") or preferences.get("session_length_preference")
            if isinstance(raw, (int, float)):
                return int(raw)
        profile = ((plan_context or {}).get("user_profile") or {}).get("preferences_snapshot") if isinstance(plan_context, dict) else None
        if isinstance(profile, dict):
            raw = profile.get("focus_duration_preference") or profile.get("inferred_session_length")
            if isinstance(raw, (int, float)):
                return int(raw)
        return None

    @staticmethod
    def _extract_difficulty_preference(
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
    ) -> float | None:
        facts = (plan_context or {}).get("facts") if isinstance(plan_context, dict) else None
        if isinstance(facts, dict):
            raw = facts.get("difficulty_preference")
            if isinstance(raw, (int, float)):
                return float(raw)
        profile = ((plan_context or {}).get("user_profile") or {}).get("preferences_snapshot") if isinstance(plan_context, dict) else None
        if isinstance(profile, dict):
            raw = profile.get("inferred_difficulty")
            if isinstance(raw, (int, float)):
                return float(raw)
        preferences = (user_context_payload or {}).get("preferences") if isinstance(user_context_payload, dict) else None
        if isinstance(preferences, dict):
            raw = preferences.get("difficulty_preference")
            if isinstance(raw, (int, float)):
                return float(raw)
        return None

    async def _build_dual_core_input(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        unified_routing_result: Any | None,
        information_sufficient: bool,
    ) -> DualCoreRoutingInput:
        active_plan_id = plan_id
        if active_plan_id is None:
            active_plans = (user_context_payload or {}).get("active_plans")
            if isinstance(active_plans, list) and active_plans:
                raw_plan_id = active_plans[0].get("id") if isinstance(active_plans[0], dict) else None
                with contextlib.suppress(ValueError, TypeError, AttributeError):
                    active_plan_id = uuid.UUID(str(raw_plan_id))

        plan_health_status: str | None = None
        if active_db and active_plan_id:
            try:
                report = await PlanProgressService(active_db, self.redis).evaluate_progress(
                    uuid.UUID(user_id),
                    active_plan_id,
                )
                plan_health_status = report.severity
            except Exception as e:
                logger.warning(f"Failed to evaluate plan health for dual core routing: {e}")

        return DualCoreRoutingInput(
            intent=(
                unified_routing_result.primary_intent.value
                if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
                else "chat"
            ),
            intent_confidence=float(getattr(unified_routing_result, "confidence", 0.5) or 0.5),
            information_sufficient=information_sufficient,
            primary_challenge_area=self._extract_primary_challenge_area(plan_context),
            recent_sentiment_distribution=await self._get_recent_sentiment_distribution(user_id, active_db),
            has_active_plan=bool(active_plan_id),
            plan_health_status=plan_health_status,
            recent_task_feedback_distribution=await self._get_recent_task_feedback_distribution(user_id, active_db),
            session_length_preference=self._extract_session_length_preference(user_context_payload, plan_context),
            difficulty_preference=self._extract_difficulty_preference(user_context_payload, plan_context),
        )

    async def _emit_dual_core_status(self, decision, stream_callback) -> None:
        stage = "planning"
        headline = "我会直接把目标收敛成可执行方案。"
        detail = decision.reason

        if decision.mode == "cognitive_first":
            stage = "understanding"
            headline = "我先处理你当前的阻力，再一起收紧计划。"
        elif decision.mode == "balanced":
            stage = "reviewing"
            headline = "我会一边推进方案，一边兼顾你当前的状态。"

        await stream_callback(
            agent_service_pb2.ChatResponse(
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details=headline,
                    current_agent_name="Sparkle AI",
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
                    )
                },
            )
        )

    async def _apply_dual_core_routing(
        self,
        *,
        route_decision: RouteDecision,
        state: WorkflowState,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        unified_routing_result: Any | None,
        information_sufficient: bool,
        stream_callback,
    ) -> RouteDecision:
        routing_input = await self._build_dual_core_input(
            active_db=active_db,
            user_id=user_id,
            plan_id=plan_id,
            user_context_payload=user_context_payload,
            plan_context=plan_context,
            unified_routing_result=unified_routing_result,
            information_sufficient=information_sufficient,
        )
        decision = self.dual_core_router.route(routing_input)
        state.context_data["dual_core_decision"] = decision.to_dict()
        state.context_data["dual_core_prompt_instruction"] = decision.prompt_instruction
        state.context_data["dual_core_signal_snapshot"] = {
            "intent": routing_input.intent,
            "intent_confidence": routing_input.intent_confidence,
            "primary_challenge_area": routing_input.primary_challenge_area,
            "recent_sentiment_distribution": routing_input.recent_sentiment_distribution,
            "recent_task_feedback_distribution": routing_input.recent_task_feedback_distribution,
            "plan_health_status": routing_input.plan_health_status,
        }

        await self._emit_dual_core_status(decision, stream_callback)

        if decision.mode == "cognitive_first" and route_decision.execution_mode in ["langgraph", "hybrid"]:
            route_decision.execution_mode = "direct"
            route_decision.reason = (
                f"{route_decision.reason} | dual_core:cognitive_first"
                if route_decision.reason
                else "dual_core:cognitive_first"
            )
        elif decision.mode == "execution_first" and route_decision.reason:
            route_decision.reason = f"{route_decision.reason} | dual_core:execution_first"
        elif decision.mode == "balanced" and route_decision.reason:
            route_decision.reason = f"{route_decision.reason} | dual_core:balanced"

        plan_meta = state.context_data.get("plan_metadata", {})
        if isinstance(plan_meta, dict):
            plan_meta["dual_core_mode"] = decision.mode
            plan_meta["dual_core_reason"] = decision.reason
            state.context_data["plan_metadata"] = plan_meta

        return route_decision

    def _build_profile_payload(
        self,
        user_context_data: dict[str, Any] | None,
        preferences: dict[str, Any] | None,
        llm_profile_data: dict[str, Any] | None,
        preference_version: int,
    ) -> dict[str, Any]:
        identity: dict[str, Any] = {}
        if isinstance(user_context_data, dict):
            flame_level = None
            prefs = user_context_data.get("preferences")
            if isinstance(prefs, dict):
                flame_level = prefs.get("flame_level")
            identity = {
                "nickname": user_context_data.get("nickname", "未知"),
                "timezone": user_context_data.get("timezone", "Asia/Shanghai"),
                "language": user_context_data.get("language", "zh-CN"),
                "is_pro": user_context_data.get("is_pro", False),
                "persona_type": user_context_data.get("persona_type"),
                "flame_level": flame_level,
            }

        prefs = preferences
        if not isinstance(prefs, dict) and isinstance(user_context_data, dict):
            prefs = user_context_data.get("preferences")
        if not isinstance(prefs, dict):
            prefs = {}

        llm_profile = llm_profile_data if isinstance(llm_profile_data, dict) else {}

        return {
            "identity": identity,
            "preferences": prefs,
            "llm_profile": llm_profile,
            "preference_version": preference_version,
        }

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """
        Build comprehensive user context from UserService

        Returns:
            Dict containing user context and analytics
        """
        try:
            # Pass redis_client to UserService for caching
            user_service = UserService(db_session, self.redis)
            base_user_context = await user_service.get_context(uuid.UUID(user_id))
            base_user_context_data = base_user_context.model_dump() if base_user_context else None

            # P1: Task Status Summary
            task_status_summary = await self._get_task_status_summary(user_id, db_session)

            llm_profile_data = None
            preference_version = 0
            try:
                from app.services.personalization import get_personalization_engine

                engine = get_personalization_engine(db_session, self.redis)
                llm_profile = await engine.get_llm_profile(uuid.UUID(user_id))
                prefs = await engine.pref_service.get_preferences(uuid.UUID(user_id))
                preference_version = prefs.version
                llm_profile_data = {
                    "system_prompt_additions": llm_profile.system_prompt_additions,
                    "verbosity_target": llm_profile.verbosity_target,
                    "temperature": llm_profile.temperature,
                    "should_ask_clarifying": llm_profile.should_ask_clarifying,
                    "should_provide_examples": llm_profile.should_provide_examples,
                    "exploration_level": llm_profile.exploration_level,
                    "tone": llm_profile.tone,
                }
            except Exception as e:
                logger.warning(f"Failed to build LLM profile: {e}")

            # --- Use ContextOrchestrator (P4) ---
            from app.core.context_manager import ContextOrchestrator

            context_orchestrator = ContextOrchestrator(db_session, self.redis)
            # Fetch aggregated context (cached)
            cognitive_context = await context_orchestrator.get_user_context(user_id)

            # Map CognitiveContext to legacy dict format for backward compatibility
            # In future, we should use CognitiveContext object directly in prompt builder

            user_context_data = None
            if cognitive_context:
                # Use data from new orchestrator
                user_context_data = base_user_context_data or {
                    "user_id": user_id,
                    "nickname": "同学",
                }

                # Fetch active plans manually if not in cognitive context yet
                # Active plans (latest 3)
                plans_stmt = (
                    select(Plan)
                    .where(
                        and_(
                            Plan.user_id == uuid.UUID(user_id),
                            Plan.is_active
                        )
                    )
                    .order_by(desc(Plan.created_at))
                    .limit(3)
                )
                plans_result = await db_session.execute(plans_stmt)
                plans = plans_result.scalars().all()
                active_plans = [
                    {
                        "id": str(plan.id),
                        "title": plan.name,
                        "type": plan.type.value,
                        "target_date": plan.target_date.isoformat() if plan.target_date else None,
                        "progress": plan.progress or 0
                    }
                    for plan in plans
                ]

                # P0: 认知棱镜上下文注入
                cognitive_insights = await self._get_cognitive_insights(user_id, db_session)

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=cognitive_context.preferences,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                )

                return {
                    "user_context": user_context_data, # Legacy field
                    "analytics_summary": cognitive_context.engagement_metrics or {},
                    "preferences": cognitive_context.preferences,
                    "next_actions": cognitive_context.active_tasks,
                    "active_plans": active_plans,
                    "focus_stats": cognitive_context.focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "task_status_summary": task_status_summary,
                    "profile": profile_payload,

                    # New field for full context injection
                    "cognitive_context": cognitive_context.model_dump(exclude={'user_id', 'timestamp'}),

                    # 认知棱镜数据
                    "cognitive_insights": cognitive_insights
                }

            # Fallback to legacy logic if new orchestrator returns None (shouldn't happen)
            logger.warning(f"ContextOrchestrator returned None for {user_id}, falling back to legacy")

            # ... Legacy Logic ...
            user_context = base_user_context
            analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

            if user_context:
                user_context_data = user_context.model_dump()

            # Next actions (top pending tasks)
            tasks_stmt = (
                select(Task)
                .where(
                    and_(
                        Task.user_id == uuid.UUID(user_id),
                        Task.status == ModelTaskStatus.PENDING
                    )
                )
                .order_by(desc(Task.priority), asc(Task.due_date), desc(Task.created_at))
                .limit(3)
            )
            tasks_result = await db_session.execute(tasks_stmt)
            tasks = tasks_result.scalars().all()
            next_actions = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority
                }
                for task in tasks
            ]

            # Active plans (latest 3)
            plans_stmt = (
                select(Plan)
                .where(
                    and_(
                        Plan.user_id == uuid.UUID(user_id),
                        Plan.is_active
                    )
                )
                .order_by(desc(Plan.created_at))
                .limit(3)
            )
            plans_result = await db_session.execute(plans_stmt)
            plans = plans_result.scalars().all()
            active_plans = [
                {
                    "id": str(plan.id),
                    "title": plan.name,
                    "type": plan.type.value,
                    "target_date": plan.target_date.isoformat() if plan.target_date else None,
                    "progress": plan.progress or 0
                }
                for plan in plans
            ]

            # Focus stats (today)
            focus_stats = await focus_service.get_today_stats(db_session, uuid.UUID(user_id))

            if user_context_data:
                # Handle preferences: could be dict (from cognitive_context) or object (from base_user_context)
                preferences_dict = {}
                if "preferences" in user_context_data:
                    prefs = user_context_data["preferences"]
                    if isinstance(prefs, dict):
                        preferences_dict = prefs
                    elif hasattr(prefs, 'model_dump'):
                        preferences_dict = prefs.model_dump()
                    else:
                        logger.warning(f"Unexpected preferences type: {type(prefs)}")
                elif "user_context" in user_context_data and hasattr(user_context_data["user_context"], "preferences"):
                    # Old structure: preferences is on user_context object
                    prefs = user_context_data["user_context"].preferences
                    if hasattr(prefs, "model_dump"):
                        preferences_dict = prefs.model_dump()
                    else:
                        preferences_dict = {"depth_preference": 0.5, "curiosity_preference": 0.5}

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=preferences_dict,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                )

                return {
                    "user_context": user_context_data,
                    "analytics_summary": analytics,
                    "preferences": {
                        "depth_preference": preferences_dict.get("depth_preference", 0.5),
                        "curiosity_preference": preferences_dict.get("curiosity_preference", 0.5),
                    },
                    "next_actions": next_actions,
                    "active_plans": active_plans,
                    "focus_stats": focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "task_status_summary": task_status_summary,
                    "profile": profile_payload,
                }
            else:
                # Fallback to basic context
                logger.warning(f"User {user_id} not found, using fallback context")
                profile_payload = self._build_profile_payload(
                    user_context_data=None,
                    preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                )
                return {
                    "user_context": None,
                    "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                    "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                    "next_actions": next_actions,
                    "active_plans": active_plans,
                    "focus_stats": focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "task_status_summary": task_status_summary,
                    "profile": profile_payload,
                }

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            # Fallback
            return {
                "user_context": None,
                "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                "preference_version": 0,
                "llm_profile": None,
                "profile": self._build_profile_payload(
                    user_context_data=None,
                    preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                    llm_profile_data=None,
                    preference_version=0,
                ),
            }

    async def _build_conversation_context(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Build conversation context with ContextPruner

        Returns:
            Dict containing pruned history and summary
        """
        if not self.context_pruner:
            logger.warning("ContextPruner not initialized, returning empty context")
            return {"messages": [], "summary": None}

        try:
            pruned_result = await self.context_pruner.get_pruned_history(
                session_id=session_id,
                user_id=user_id
            )

            logger.debug(
                f"Conversation context for session {session_id}: "
                f"{pruned_result['original_count']} -> {pruned_result['pruned_count']} messages, "
                f"summary_used={pruned_result['summary_used']}"
            )

            return pruned_result

        except Exception as e:
            logger.error(f"Failed to prune conversation history: {e}")
            return {"messages": [], "summary": None}

    def _log_context_injection(self, user_id: str, context: dict[str, Any] | None) -> None:
        """Log context injection details for observability."""
        if not context or not isinstance(context, dict):
            logger.info("Context injection for user {}: empty", user_id)
            return

        next_actions = context.get("next_actions") or context.get("pending_tasks") or []
        active_plans = context.get("active_plans") or []

        tasks_count = len(next_actions) if isinstance(next_actions, list) else 0
        plans_count = len(active_plans) if isinstance(active_plans, list) else 0

        last_activity = None
        user_ctx = context.get("user_context")
        if isinstance(user_ctx, dict):
            last_activity = user_ctx.get("last_activity_time") or user_ctx.get("last_login")

        if not last_activity and isinstance(context.get("analytics_summary"), dict):
            last_activity = context["analytics_summary"].get("last_login") or context["analytics_summary"].get("last_activity_time")

        logger.info(
            "Context injection for user {}: {} tasks, {} plans, last_activity={}",
            user_id,
            tasks_count,
            plans_count,
            last_activity
        )

    async def _get_tools_schema(self, active_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """Get tools from dynamic registry, optionally filtered by request-scoped allowlist."""
        try:
            requested_tools = [tool_name.strip() for tool_name in (active_tools or []) if tool_name and tool_name.strip()]
            if not requested_tools:
                return dynamic_tool_registry.get_openai_tools_schema()

            tools_by_name = {tool.name: tool for tool in dynamic_tool_registry.get_all_tools()}
            filtered_tools: list[dict[str, Any]] = []
            unknown_tools: list[str] = []
            seen: set[str] = set()
            for tool_name in requested_tools:
                if tool_name in seen:
                    continue
                seen.add(tool_name)
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    unknown_tools.append(tool_name)
                    continue
                filtered_tools.append(tool.to_openai_schema())

            if unknown_tools:
                logger.warning(f"Ignoring unknown active_tools: {unknown_tools}")

            return filtered_tools
        except Exception as e:
            logger.error(f"Failed to get tools schema: {e}")
            return []

    async def _validate_request(
        self,
        request: agent_service_pb2.ChatRequest,
        *,
        response_id: str,
        request_id: str,
    ) -> agent_service_pb2.ChatResponse | None:
        if not self.validator:
            return None
        validation_result = await self.validator.validate_chat_request(request)
        if validation_result.is_valid:
            return None
        logger.error(f"Validation failed: {validation_result.error_message}")
        return agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            error=agent_service_pb2.Error(
                message=validation_result.error_message,
                retryable=False,
                error_code=agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            ),
            finish_reason=agent_service_pb2.ERROR,
        )

    async def _check_idempotency_response(
        self,
        *,
        session_id: str,
        request_id: str,
        response_id: str,
    ) -> agent_service_pb2.ChatResponse | None:
        cached_response = await self._check_idempotency(session_id, request_id)
        if not cached_response:
            return None
        logger.info(f"Cache hit for session {session_id}, request {request_id}")
        cached_metadata = cached_response.get("metadata") if isinstance(cached_response, dict) else None
        metadata_map = {}
        if isinstance(cached_metadata, dict):
            metadata_map = {str(k): str(v) for k, v in cached_metadata.items()}
        return agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            full_text=cached_response.get("full_text") or cached_response.get("message", ""),
            metadata=metadata_map,
            finish_reason=agent_service_pb2.STOP,
        )

    async def _drain_queue(self, queue: asyncio.Queue) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        while not queue.empty():
            item = await queue.get()
            yield item

    async def _check_sufficiency(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        user_message: str,
        user_id: str,
        plan_id: uuid.UUID | None,
        conversation_context: dict[str, Any] | None,
        stream_callback,
        queue: asyncio.Queue,
    ) -> tuple[bool, str]:
        if request.HasField("tool_result"):
            return False, ""
        try:
            prediction = await shadow_prediction_service.predict_intent_only(
                user_message=user_message,
                active_plan_id=str(plan_id) if plan_id else None,
                user_id=user_id,
            )
            intent_type = prediction.get("intent_type", "unknown")
            extracted_entities = {
                "intent_type": intent_type,
                "suggested_tools": prediction.get("suggested_tools", []),
            }
            plan_intents = {"create_plan", "time_planning"}
            check_result = await sufficiency_checker.check(
                intent=intent_type,
                extracted_entities=extracted_entities,
                conversation_context=(conversation_context or {}).get("messages", []),
                user_message=user_message,
                use_llm_fallback=intent_type in plan_intents,
            )

            if check_result.status == SufficiencyStatus.NEED_CLARIFICATION:
                questions = check_result.clarification_questions
                if check_result.clarification_text:
                    questions = [check_result.clarification_text]
                question_text = "\n".join([f"- {q}" for q in questions if q]) if questions else "- 请补充更多关键信息"
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"我需要更多信息来帮您：\n\n{question_text}\n\n请提供以上信息，我将为您处理。",
                    metadata={
                        "requires_clarification": "true",
                        "missing_fields": ",".join(check_result.missing_fields),
                    },
                ))
                await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
                return True, intent_type

            if check_result.status == SufficiencyStatus.NEED_CONFIRMATION:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=check_result.confirmation_message,
                    metadata={"requires_confirmation": "true"},
                ))
                await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
                return True, intent_type
        except Exception as e:
            logger.warning(f"Sufficiency check failed, continuing: {e}")
        return False, intent_type if 'intent_type' in locals() else ""

    async def _check_goal_quality(
        self,
        *,
        intent_type: str,
        user_message: str,
        user_id: str,
        plan_id: uuid.UUID | None,
        active_db: AsyncSession | None,
        conversation_context: dict[str, Any] | None,
        stream_callback,
        state: WorkflowState,
    ) -> bool:
        if intent_type not in {"create_plan", "set_goal"}:
            state.context_data["goal_quality"] = {"passed": True, "skipped": True}
            return False

        if active_db and plan_id:
            try:
                from app.services.plan_state_service import PlanStateService

                plan_state = await PlanStateService(active_db, self.redis).get_plan_state(
                    uuid.UUID(user_id),
                    plan_id,
                )
                goal_quality = ((plan_state.facts or {}).get("goal_quality")) if plan_state else None
                if isinstance(goal_quality, dict) and goal_quality.get("passed") is True:
                    state.context_data["goal_quality"] = goal_quality
                    return False
            except Exception as e:
                logger.warning(f"Failed to load goal quality mark from plan state: {e}")

        evaluation = await goal_quality_evaluator.evaluate(
            user_message=user_message,
            intent=intent_type,
            conversation_context=(conversation_context or {}).get("messages", []),
        )
        state.context_data["goal_quality"] = evaluation.to_dict()

        if not evaluation.passed:
            question_text = "\n".join(
                f"- {question}" for question in evaluation.clarification_questions if question
            ) or "- 请把目标再说具体一点"
            await stream_callback(
                agent_service_pb2.ChatResponse(
                    delta=(
                        "我想先把目标收紧到足够可执行，再开始做计划：\n\n"
                        f"{question_text}\n\n"
                        "你补充这些信息后，我就能给你更靠谱的阶段方案。"
                    ),
                    metadata={
                        "requires_goal_clarification": "true",
                        "goal_quality_scores": json.dumps(evaluation.scores.to_dict(), ensure_ascii=False),
                    },
                )
            )
            await stream_callback(agent_service_pb2.ChatResponse(finish_reason=agent_service_pb2.STOP))
            return True

        if active_db and plan_id:
            try:
                from app.services.plan_state_service import PlanStateService

                await PlanStateService(active_db, self.redis).upsert_plan_state(
                    user_id=uuid.UUID(user_id),
                    plan_id=plan_id,
                    patch={"facts": {"goal_quality": evaluation.to_dict()}},
                    bump_version=False,
                )
            except Exception as e:
                logger.warning(f"Failed to persist goal quality mark: {e}")

        return False

    async def _route_and_classify(
        self,
        *,
        user_message: str,
        user_id: str,
        session_id: str,
        grpc_context: dict[str, Any],
        conversation_context: dict[str, Any] | None,
        state: WorkflowState,
    ) -> tuple[RouteDecision, Any | None]:
        unified_routing_result = None
        has_summary = self._has_conversation_summary(conversation_context)
        if has_summary:
            ROUTING_SUMMARY_CONTEXT_TOTAL.labels(phase="router_input").inc()
        routing_history = self._build_routing_history(conversation_context)
        try:
            unified_routing_result = await self.unified_router.route(
                message=user_message,
                user_id=user_id,
                session_id=session_id,
                payload=grpc_context,
                conversation_history=routing_history,
            )
            logger.info(
                f"Unified routing: {unified_routing_result.primary_intent.value} "
                f"(confidence={unified_routing_result.confidence:.2f}, "
                f"layer={unified_routing_result.routing_layer})"
            )
        except Exception as e:
            logger.warning(f"Unified routing failed: {e}")

        if unified_routing_result:
            state.context_data["unified_intent"] = {
                "primary_intent": unified_routing_result.primary_intent.value,
                "confidence": unified_routing_result.confidence,
                "routing_layer": unified_routing_result.routing_layer,
                "execution_mode": unified_routing_result.execution_mode,
                "risk_level": unified_routing_result.risk_level,
                "context_signals": unified_routing_result.context_signals,
            }
            if unified_routing_result.primary_intent == UnifiedIntentType.COGNITIVE_PRISM:
                state.context_data["special_intent"] = "cognitive_prism"
            elif unified_routing_result.primary_intent == UnifiedIntentType.TRANSLATION:
                state.context_data["special_intent"] = "translation"
            elif unified_routing_result.primary_intent == UnifiedIntentType.SPRINT_PLAN:
                state.context_data["special_intent"] = "sprint_plan"
            route_decision = to_route_decision(unified_routing_result)
        else:
            route_decision = RouteDecision(
                execution_mode="direct",
                reason="unified:fallback",
                risk_level="low",
                confidence=0.5,
                context_version=None,
            )

        route_decision, adaptive_notes = self._apply_adaptive_routing_policy(
            route_decision=route_decision,
            unified_routing_result=unified_routing_result,
            user_message=user_message,
            conversation_context=conversation_context,
        )
        if adaptive_notes:
            state.context_data["adaptive_routing"] = {
                "notes": adaptive_notes,
                "execution_mode": route_decision.execution_mode,
                "risk_level": route_decision.risk_level,
                "reason": route_decision.reason,
            }
        if unified_routing_result and "unified_intent" in state.context_data:
            state.context_data["unified_intent"]["execution_mode"] = route_decision.execution_mode
            state.context_data["unified_intent"]["risk_level"] = route_decision.risk_level

        state.context_data["plan_metadata"] = {
            "context_version": route_decision.context_version,
            "execution_mode": route_decision.execution_mode,
            "risk_level": route_decision.risk_level,
            "confidence": route_decision.confidence,
            "route_reason": route_decision.reason,
            "routing_layer": unified_routing_result.routing_layer if unified_routing_result else "fallback",
            "adaptive_notes": ",".join(adaptive_notes) if adaptive_notes else "",
            "summary_used_for_routing": "true" if has_summary else "false",
        }
        state.context_data["grounding_validator"] = self.grounding_validator
        return route_decision, unified_routing_result

    @staticmethod
    def _build_routing_history(conversation_context: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(conversation_context, dict):
            return []
        messages = conversation_context.get("messages")
        history: list[dict[str, Any]] = [m for m in messages if isinstance(m, dict)] if isinstance(messages, list) else []
        summary = conversation_context.get("summary")
        if isinstance(summary, str) and summary.strip():
            summary_content = summary.strip()
            if len(summary_content) > 600:
                summary_content = summary_content[:600] + "..."
            history = [{"role": "system", "content": f"Summary of prior conversation: {summary_content}"}] + history
        return history

    @staticmethod
    def _normalize_proto_history(history_messages: list[Any]) -> list[dict[str, Any]]:
        normalized_history: list[dict[str, Any]] = []
        for msg in history_messages or []:
            role = str(getattr(msg, "role", "") or "").strip().lower()
            if not role:
                continue

            history_item: dict[str, Any] = {
                "role": role,
                "content": str(getattr(msg, "content", "") or ""),
            }

            name = str(getattr(msg, "name", "") or "").strip()
            if name:
                history_item["name"] = name

            tool_call_id = str(getattr(msg, "tool_call_id", "") or "").strip()
            if tool_call_id:
                history_item["tool_call_id"] = tool_call_id

            metadata = {
                str(k): str(v)
                for k, v in dict(getattr(msg, "metadata", {}) or {}).items()
            }
            if metadata:
                history_item["metadata"] = metadata
                raw_tool_calls = metadata.get("tool_calls")
                if raw_tool_calls:
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        parsed_tool_calls = json.loads(raw_tool_calls)
                        if isinstance(parsed_tool_calls, list):
                            history_item["tool_calls"] = parsed_tool_calls

            normalized_history.append(history_item)

        return normalized_history

    def _merge_request_history_into_conversation_context(
        self,
        conversation_context: dict[str, Any] | None,
        request_history: list[Any],
    ) -> dict[str, Any]:
        proto_history = self._normalize_proto_history(request_history)
        if not proto_history:
            return conversation_context or {"messages": [], "summary": None}

        merged_context = dict(conversation_context or {"messages": [], "summary": None})
        existing_messages = merged_context.get("messages")
        existing_history = [m for m in existing_messages if isinstance(m, dict)] if isinstance(existing_messages, list) else []

        overlap = 0
        max_overlap = min(len(existing_history), len(proto_history))
        for size in range(max_overlap, 0, -1):
            if existing_history[-size:] == proto_history[:size]:
                overlap = size
                break

        merged_context["messages"] = existing_history + proto_history[overlap:]
        return merged_context

    @staticmethod
    def _has_conversation_summary(conversation_context: dict[str, Any] | None) -> bool:
        if not isinstance(conversation_context, dict):
            return False
        summary = conversation_context.get("summary")
        return isinstance(summary, str) and bool(summary.strip())

    @staticmethod
    def _is_complex_user_query(message: str) -> bool:
        if not message:
            return False
        msg_lower = message.lower()
        complex_keywords = {
            "方案", "策略", "权衡", "分阶段", "multi-step", "tradeoff", "design", "architecture",
            "学习计划", "复习计划", "错误诊断", "knowledge graph", "then", "after that", "首先", "然后", "接着",
        }
        if any(keyword in msg_lower for keyword in complex_keywords):
            return True
        sentence_count = (
            message.count("。")
            + message.count(".")
            + message.count("!")
            + message.count("?")
            + message.count("！")
            + message.count("？")
        )
        return len(message) > 90 and sentence_count >= 2

    @staticmethod
    def _is_context_dependent_query(message: str) -> bool:
        if not message:
            return False
        msg_lower = message.lower()
        context_markers = {
            "继续", "接着", "刚才", "上面", "这个", "那个", "如前所述", "继续上次",
            "continue", "as above", "that one", "the previous", "what we discussed",
        }
        return any(marker in msg_lower for marker in context_markers)

    @staticmethod
    def _extract_route_intent(reason: str) -> str:
        if not reason:
            return "unknown"
        reason_lc = str(reason).lower()
        if reason_lc.startswith("unified:"):
            return reason_lc.split(":", 1)[1] or "unknown"
        if reason_lc.startswith("adaptive:"):
            parts = reason_lc.split(":")
            if len(parts) >= 3:
                return parts[-1] or "unknown"
        if ":" in reason_lc:
            return reason_lc.split(":", 1)[0]
        return reason_lc

    def _apply_adaptive_routing_policy(
        self,
        *,
        route_decision: RouteDecision,
        unified_routing_result: Any | None,
        user_message: str,
        conversation_context: dict[str, Any] | None,
    ) -> tuple[RouteDecision, list[str]]:
        notes: list[str] = []
        if not route_decision:
            return route_decision, notes

        confidence = route_decision.confidence if route_decision.confidence is not None else 0.5
        is_complex = self._is_complex_user_query(user_message)
        is_context_dependent = self._is_context_dependent_query(user_message)
        has_summary = bool(isinstance(conversation_context, dict) and str(conversation_context.get("summary") or "").strip())

        inferred_intent = (
            unified_routing_result.primary_intent.value
            if unified_routing_result and hasattr(unified_routing_result, "primary_intent")
            else self._extract_route_intent(route_decision.reason)
        )

        if route_decision.risk_level != "high" and route_decision.execution_mode == "direct":
            if confidence < 0.6 and is_complex:
                from_mode = route_decision.execution_mode
                route_decision.execution_mode = "hybrid"
                if route_decision.risk_level == "low":
                    route_decision.risk_level = "medium"
                route_decision.reason = f"adaptive:low_confidence_complex:{inferred_intent}"
                notes.append("upgraded_to_hybrid_low_confidence_complex")
                ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                    action="upgrade",
                    trigger="low_confidence_complex",
                    from_mode=from_mode,
                    to_mode=route_decision.execution_mode,
                ).inc()
            elif confidence < 0.7 and is_context_dependent and has_summary:
                from_mode = route_decision.execution_mode
                route_decision.execution_mode = "hybrid"
                route_decision.reason = f"adaptive:context_continuity:{inferred_intent}"
                notes.append("upgraded_to_hybrid_context_continuity")
                ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                    action="upgrade",
                    trigger="context_continuity",
                    from_mode=from_mode,
                    to_mode=route_decision.execution_mode,
                ).inc()

        if route_decision.execution_mode == "hybrid" and confidence >= 0.92 and not is_complex and not is_context_dependent:
            from_mode = route_decision.execution_mode
            route_decision.execution_mode = "direct"
            route_decision.reason = f"adaptive:high_confidence_simple:{inferred_intent}"
            notes.append("downgraded_to_direct_high_confidence_simple")
            ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL.labels(
                action="downgrade",
                trigger="high_confidence_simple",
                from_mode=from_mode,
                to_mode=route_decision.execution_mode,
            ).inc()

        return route_decision, notes

    async def _stream_hitl_escalation(
        self,
        *,
        conflict,
        executable_plan: ExecutablePlan,
        snapshot: StateSnapshot | None,
        user_id: str,
        stream_callback,
    ) -> None:
        tool_calls_payload = [{"id": tc.id, "name": tc.name, "params": tc.params} for tc in executable_plan.tool_calls]
        action_id = await pending_actions_store.save(
            tool_name="__plan_version_conflict__",
            arguments={
                "plan_id": executable_plan.plan_id,
                "snapshot_id": snapshot.snapshot_id if snapshot else None,
                "tool_calls": tool_calls_payload,
                "reason": "version_conflict",
                "conflicted_domains": list(conflict.conflicted_domains),
            },
            user_id=user_id,
            description="检测到状态变更，是否继续执行该计划？",
            preview_data={
                "plan_id": executable_plan.plan_id,
                "conflicted_domains": list(conflict.conflicted_domains),
                "affected_domains": list(conflict.affected_domains),
                "tool_calls": tool_calls_payload,
            },
        )
        HITL_REQUESTED.labels(reason="version_conflict").inc()
        await stream_callback(agent_service_pb2.ChatResponse(
            delta=("\n\n⚠️ 检测到状态变化，需要确认后继续执行。\n" f"action_id={action_id}"),
            metadata={"requires_hitl": "true", "action_id": action_id, "reason": "version_conflict"},
        ))

    async def _stream_discard_notice(self, stream_callback) -> None:
        await stream_callback(agent_service_pb2.ChatResponse(
            delta="\n\n⚠️ 检测到状态变化，计划已过期。请重试。",
        ))

    def _extract_llm_profile_meta(self, user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
        llm_profile_meta = {}
        if not isinstance(user_context_payload, dict):
            return llm_profile_meta
        llm_profile = user_context_payload.get("llm_profile")
        if not llm_profile:
            return llm_profile_meta
        if isinstance(llm_profile, str):
            try:
                llm_profile_meta = json.loads(llm_profile)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse llm_profile JSON string: {llm_profile[:100] if llm_profile else 'None'}")
                llm_profile_meta = {}
        elif isinstance(llm_profile, dict):
            llm_profile_meta = llm_profile
        else:
            logger.warning(f"Unexpected llm_profile type: {type(llm_profile)}")
        return llm_profile_meta

    @staticmethod
    def _extract_execution_feedback_from_log_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None

        entry_type = str(entry.get("type", "")).strip()
        if entry_type == "plan_execution_feedback":
            feedback = {
                "slow_tools": entry.get("slow_tools", []) or [],
                "failed_tools": entry.get("failed_tools", []) or [],
                "unreliable_dependencies": entry.get("unreliable_dependencies", []) or [],
                "quality_score": entry.get("quality_score"),
            }
            if any(feedback.get(k) for k in ("slow_tools", "failed_tools", "unreliable_dependencies")) or feedback.get("quality_score") is not None:
                return feedback
            return None

        if entry_type == "plan_execution":
            adjustment = entry.get("applied_adjustment") or {}
            if not isinstance(adjustment, dict):
                return None
            feedback = {
                "slow_tools": adjustment.get("slow_tools", []) or [],
                "failed_tools": adjustment.get("failed_tools", []) or [],
                "unreliable_dependencies": adjustment.get("unreliable_dependencies", []) or [],
                "quality_score": adjustment.get("quality_score"),
            }
            if any(feedback.get(k) for k in ("slow_tools", "failed_tools", "unreliable_dependencies")) or feedback.get("quality_score") is not None:
                return feedback
        return None

    async def _load_recent_execution_feedback(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        plan_id: str | None,
    ) -> dict[str, Any] | None:
        if not active_db or not plan_id:
            return None
        try:
            from app.services.plan_state_service import PlanStateService

            plan_state_service = PlanStateService(active_db, self.redis)
            plan_state = await plan_state_service.get_plan_state(
                uuid.UUID(user_id),
                uuid.UUID(plan_id),
            )
            if not plan_state or not plan_state.feedback_log:
                return None

            for entry in reversed(plan_state.feedback_log):
                feedback = self._extract_execution_feedback_from_log_entry(entry)
                if feedback is not None:
                    return feedback
        except Exception as e:
            logger.warning(f"Failed to load recent execution feedback: {e}")
        return None

    async def _publish_execution_feedback(
        self,
        *,
        active_db: AsyncSession | None,
        executable_plan: ExecutablePlan,
        plan_result: Any,
        validation_result: Any,
        user_id: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        if not active_db:
            return []
        try:
            from app.orchestration.adaptive_replanner import AdaptiveReplanner
            from app.orchestration.step_feedback_collector import StepFeedbackCollector

            collector = StepFeedbackCollector()
            feedback = collector.collect(
                plan=executable_plan,
                plan_result=plan_result,
                validation_result=validation_result,
                user_id=user_id,
                session_id=session_id,
            )
            replanner = AdaptiveReplanner(active_db, redis=self.redis)
            records = await replanner.on_plan_execution_completed(
                user_id=uuid.UUID(user_id),
                plan_id=uuid.UUID(str(executable_plan.plan_id)),
                feedback=feedback,
            )
            return [record.to_dict() if hasattr(record, "to_dict") else record for record in (records or [])]
        except Exception as e:
            logger.warning(f"Failed to publish execution feedback: {e}", exc_info=True)
            return []

    async def _validate_plan_execution(
        self,
        *,
        executable_plan: ExecutablePlan | None,
        active_db: AsyncSession | None,
        final_state: WorkflowState,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        if not executable_plan or not hasattr(executable_plan, "plan_id") or not active_db:
            return None
        try:
            record_service = PlanExecutionRecordService(active_db)
            execution_validator = PlanExecutionValidator(record_service=record_service)
            plan_result = final_state.context_data.get("plan_execution_result")

            if plan_result is not None and hasattr(plan_result, "step_results"):
                adaptation_records: list[dict[str, Any]] = []
                validation_result = await execution_validator.validate_plan_execution(
                    plan=executable_plan,
                    plan_result=plan_result,
                    user_id=uuid.UUID(user_id),
                )
                adaptation_records = await self._publish_execution_feedback(
                    active_db=active_db,
                    executable_plan=executable_plan,
                    plan_result=plan_result,
                    validation_result=validation_result,
                    user_id=user_id,
                    session_id=session_id,
                )
                if adaptation_records:
                    final_state.context_data["adaptation_records"] = adaptation_records
                logger.info(
                    "DAG plan execution validation: plan_id={} status={} score={:.2f} steps={} aborted={}",
                    validation_result.plan_id,
                    validation_result.validation_status,
                    validation_result.quality_score,
                    len(getattr(validation_result, "step_validations", []) or []),
                    getattr(validation_result, "aborted", False),
                )
                return {
                    "validation_status": validation_result.validation_status,
                    "quality_score": validation_result.quality_score,
                    "tools_total": validation_result.tool_summary.get("total", 0),
                    "tools_successful": validation_result.tool_summary.get("successful", 0),
                    "steps_total": len(getattr(validation_result, "step_validations", []) or []),
                    "steps_passed": sum(1 for sv in (getattr(validation_result, "step_validations", []) or []) if sv.passed),
                    "aborted": bool(getattr(validation_result, "aborted", False)),
                }

            tool_extractor = ToolResultExtractor()
            tool_results = tool_extractor.extract_from_messages(final_state.messages)
            if not (tool_results or executable_plan.tool_calls):
                return None

            validation_result = await execution_validator.validate_and_record(
                plan=executable_plan,
                tool_results=tool_results,
                user_id=uuid.UUID(user_id),
            )
            logger.info(
                f"Plan execution validation: plan_id={validation_result.plan_id}, "
                f"validation_status={validation_result.validation_status}, "
                f"score={validation_result.quality_score:.2f}"
            )
            return {
                "validation_status": validation_result.validation_status,
                "quality_score": validation_result.quality_score,
                "tools_total": validation_result.tool_summary.get("total", 0),
                "tools_successful": validation_result.tool_summary.get("successful", 0),
            }
        except Exception as e:
            logger.warning(f"Plan execution validation failed: {e}", exc_info=True)
            return None

    async def _persist_assistant_message(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        full_response: str,
    ) -> None:
        if not active_db or not full_response:
            return
        try:
            assistant_msg = ChatMessage(
                user_id=uuid.UUID(str(user_id)),
                session_id=uuid.UUID(str(session_id)),
                role=MessageRole.ASSISTANT,
                content=full_response,
                model_name=getattr(llm_service, "default_model", None),
            )
            active_db.add(assistant_msg)
            await active_db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist assistant chat message: {e}")
            with contextlib.suppress(Exception):
                await active_db.rollback()

    async def _record_decision(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        user_context_payload: dict[str, Any] | None,
        llm_profile_meta: dict[str, Any],
        full_response: str,
    ) -> None:
        try:
            from app.services.decision_record_service import DecisionRecordService

            if active_db is None or not active_db.is_active:
                return

            def get_val(d, key, default):
                if not isinstance(d, dict):
                    return default
                if key in d:
                    return d[key]
                quoted_key = f'"{key}"'
                if quoted_key in d:
                    return d[quoted_key]
                return default

            pref_snapshot = {
                "verbosity": get_val(llm_profile_meta, "verbosity_target", "balanced"),
                "temperature": get_val(llm_profile_meta, "temperature", 0.7),
                "tone": get_val(llm_profile_meta, "tone", "encouraging"),
            }
            decision_service = DecisionRecordService(active_db)
            await decision_service.record_decision(
                user_id=uuid.UUID(str(user_id)),
                module="ai",
                action="generate_response",
                preference_version=(user_context_payload or {}).get("preference_version", 0),
                preferences_snapshot=pref_snapshot,
                outcome=f"Generated response with {len(full_response)} chars",
            )
        except Exception as e:
            logger.warning(f"Failed to record decision: {e}")
            logger.debug(f"llm_profile_meta type: {type(llm_profile_meta)}, content: {llm_profile_meta}")

    async def _hydrate_evolution_context(
        self,
        *,
        final_state: WorkflowState,
        user_id: str,
    ) -> None:
        try:
            updates = await SystemUpdateService(getattr(self, "redis", None)).list_updates(user_id, limit=20)
            if not updates:
                return
            context_data = final_state.context_data
            adaptation_records = list(context_data.get("adaptation_records") or [])
            preference_learnings = list(context_data.get("preference_learnings") or [])
            evolution_highlights = list(context_data.get("evolution_highlights") or [])
            progress_snapshot = context_data.get("progress_snapshot")
            for update in updates:
                metadata = update.get("metadata") if isinstance(update, dict) else None
                if not isinstance(metadata, dict):
                    continue
                adaptation = metadata.get("adaptation_record")
                if metadata.get("evolution_kind") == "adaptation_record" and isinstance(adaptation, dict):
                    if adaptation not in adaptation_records:
                        adaptation_records.append(adaptation)
                pref = metadata.get("preference_learning")
                if metadata.get("evolution_kind") == "preference_learning" and isinstance(pref, dict):
                    if pref not in preference_learnings:
                        preference_learnings.append(pref)
                if metadata.get("evolution_kind") == "highlight" and metadata.get("highlight"):
                    highlight = str(metadata["highlight"]).strip()
                    if highlight and highlight not in evolution_highlights:
                        evolution_highlights.append(highlight)
                snapshot = metadata.get("progress_snapshot")
                if metadata.get("evolution_kind") == "progress_snapshot" and isinstance(snapshot, dict):
                    progress_snapshot = snapshot
            if progress_snapshot is None and hasattr(self, "db_session_factory"):
                async with self.db_session_factory() as db_session:
                    service = ProgressNarrativeService(db_session, getattr(self, "redis", None))
                    progress_snapshot = await service.maybe_get_lightweight_snapshot(user_id)
            if adaptation_records:
                context_data["adaptation_records"] = adaptation_records[:3]
            if preference_learnings:
                context_data["preference_learnings"] = preference_learnings[:3]
            if evolution_highlights:
                context_data["evolution_highlights"] = evolution_highlights[:3]
            if progress_snapshot:
                context_data["progress_snapshot"] = progress_snapshot
        except Exception as e:
            logger.warning(f"Failed to hydrate evolution context: {e}")

    async def _build_final_response(
        self,
        *,
        final_state: WorkflowState,
        executable_plan: ExecutablePlan | None,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        workflow_id: str,
        prompt_version: str,
        route_decision: RouteDecision,
        plan_switched: bool,
        plan_id: uuid.UUID | None,
        user_context_payload: dict[str, Any] | None,
    ) -> tuple[agent_service_pb2.ChatResponse, dict[str, Any]]:
        full_response = ""
        for msg in reversed(final_state.messages):
            if msg["role"] == "assistant":
                full_response = msg["content"]
                break
        used_fallback_response = False
        if not full_response or not full_response.strip():
            full_response = self._build_nonempty_fallback_response(final_state=final_state, executable_plan=executable_plan)
            used_fallback_response = True
            RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="standard_empty_final").inc()

        llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
        response_metadata = {
            "response_id": response_id,
            "trace_id": trace_id,
            "preference_version": (user_context_payload or {}).get("preference_version", 0),
            "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
        }
        if used_fallback_response:
            response_metadata["response_fallback"] = "generated"
        if route_decision and "sprint" in route_decision.reason.lower():
            response_metadata["switch_to_sprint"] = True
        if plan_switched and plan_id:
            response_metadata["plan_switched"] = True
            response_metadata["switched_to_plan_id"] = str(plan_id)
        expert_metadata = final_state.context_data.get("expert_routing_metadata")
        if isinstance(expert_metadata, dict):
            response_metadata.update(expert_metadata)
        selected_experts = final_state.context_data.get("selected_experts")
        if isinstance(selected_experts, list) and selected_experts:
            response_metadata["selected_experts"] = json.dumps(
                [str(expert) for expert in selected_experts],
                ensure_ascii=False,
            )

        execution_validation = await self._validate_plan_execution(
            executable_plan=executable_plan,
            active_db=active_db,
            final_state=final_state,
            user_id=user_id,
            session_id=session_id,
        )
        if execution_validation:
            response_metadata["execution_validation"] = execution_validation

        await self._hydrate_evolution_context(final_state=final_state, user_id=user_id)
        ux_envelope = ux_envelope_builder.build(
            user_message=self._extract_latest_user_message(final_state.messages),
            full_response=full_response,
            final_state=final_state,
            executable_plan=executable_plan,
            route_decision=route_decision,
            include_references=bool(final_state.context_data.get("include_references")),
            file_ids=list(final_state.context_data.get("file_ids") or []),
            execution_validation=execution_validation,
            conversation_context=final_state.context_data.get("conversation_context"),
            plan_context=final_state.context_data.get("plan_context"),
            user_context_payload=user_context_payload,
        )
        response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))

        await self._persist_assistant_message(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            full_response=full_response,
        )
        await self._record_decision(
            active_db=active_db,
            user_id=user_id,
            user_context_payload=user_context_payload,
            llm_profile_meta=llm_profile_meta,
            full_response=full_response,
        )

        final_response_data = {
            "message": full_response,
            "tool_results": [],
            "metadata": response_metadata,
        }
        final_response = agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            metadata={str(k): str(v) for k, v in response_metadata.items()},
            full_text=full_response,
            finish_reason=agent_service_pb2.STOP,
        )
        return final_response, final_response_data

    @staticmethod
    def _extract_latest_user_message(messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content") or "")
        return ""

    def _build_nonempty_fallback_response(
        self,
        *,
        final_state: WorkflowState,
        executable_plan: ExecutablePlan | None,
    ) -> str:
        plan_result = final_state.context_data.get("plan_execution_result")
        success_count = 0
        failed_count = 0
        failed_tools: list[str] = []
        if plan_result is not None and hasattr(plan_result, "step_results"):
            for step in getattr(plan_result, "step_results", []) or []:
                tool_result = getattr(step, "tool_result", None)
                tool_name = getattr(step, "tool_name", "unknown_tool")
                if getattr(tool_result, "success", False):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_tools.append(str(tool_name))

        if success_count > 0 or failed_count > 0:
            summary_parts = [f"已完成执行：成功 {success_count} 项"]
            if failed_count > 0:
                summary_parts.append(f"失败 {failed_count} 项")
            detail = "，".join(summary_parts)
            if failed_tools:
                failed_preview = "、".join(failed_tools[:3])
                detail += f"。失败工具：{failed_preview}"
            detail += "。如果你希望，我可以基于当前结果继续细化下一步行动。"
            return detail

        if executable_plan and executable_plan.tool_calls:
            tool_names = [tc.name for tc in executable_plan.tool_calls[:3]]
            tool_list = "、".join(tool_names)
            return f"我已生成并执行任务流程（{tool_list}）。当前结果未形成完整文本答案，你可以让我继续输出详细结论或下一步计划。"

        return "我已经完成本轮处理，但结果文本为空。请告诉我你希望我优先输出：结论摘要、执行细节，或下一步行动计划。"

    async def _cleanup(
        self,
        *,
        lock_acquired: bool,
        lock_renewal_task: asyncio.Task | None,
        lock_renewal_stop: asyncio.Event | None,
        session_id: str,
        request_id: str,
        start_time: float,
        user_id: str,
        total_prompt_tokens: int,
        total_completion_tokens: int,
    ) -> None:
        ACTIVE_SESSIONS.dec()
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(module="orchestration", method="process_stream").observe(latency)
        COLLABORATION_LATENCY.labels(workflow_type="standard_chat").observe(latency)

        if lock_renewal_task and lock_renewal_stop:
            try:
                await self.state_manager.stop_lock_renewal(lock_renewal_task, lock_renewal_stop)
            except Exception as e:
                logger.warning(f"Failed to stop lock renewal: {e}")

        if lock_acquired:
            await self._release_session_lock(session_id, request_id)

        if self.token_tracker and total_prompt_tokens > 0:
            try:
                estimated_cost = await self.token_tracker.estimate_cost(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    model="gpt-4",
                )
                await task_manager.spawn(
                    self.token_tracker.record_usage(
                        user_id=user_id,
                        session_id=session_id,
                        request_id=request_id,
                        prompt_tokens=total_prompt_tokens,
                        completion_tokens=total_completion_tokens,
                        model="gpt-4",
                        cost=estimated_cost,
                    ),
                    task_name="token_usage_record",
                    user_id=str(user_id),
                )
                logger.info(
                    f"Token usage recorded for user {user_id}: "
                    f"{total_prompt_tokens} + {total_completion_tokens} = "
                    f"{total_prompt_tokens + total_completion_tokens} tokens, "
                    f"est. cost: ${estimated_cost:.6f}"
                )
            except Exception as e:
                logger.error(f"Failed to record token usage: {e}")

    async def _prepare_runtime_context(
        self,
        state: WorkflowState,
        request_id: str,
        response_id: str,
        active_tools: list[str],
        stream_callback,
        tracer,
    ) -> tuple[TransparencyDataGenerator, "typing.Callable"]:
        """Prepare transparency tracking, tools schema, and initial status.

        Returns (transparency_generator, emit_transparency_event).
        """
        import typing

        transparency_enabled = bool(
            settings.TRANSPARENCY_MODE_ENABLED and settings.TRANSPARENCY_MODE_DEFAULT
        )
        transparency_generator = TransparencyDataGenerator(
            request_id=request_id or response_id,
            enabled=transparency_enabled,
        )

        async def emit_transparency_event(event: dict[str, Any] | None) -> None:
            if not event:
                return
            try:
                await stream_callback(
                    agent_service_pb2.ChatResponse(
                        metadata={
                            "event_type": "transparency",
                            "event_payload": json.dumps(event, ensure_ascii=False),
                        }
                    )
                )
            except Exception as exc:
                logger.debug(f"Failed to emit transparency event: {exc}")

        # Load tools with transparency step
        tools_step = transparency_generator.create_step(
            name="加载工具配置",
            step_type=StepType.PLANNING,
            agent_type="ORCHESTRATOR",
            metadata={"phase": "tools_schema"},
        )
        transparency_generator.start_step(tools_step)
        await emit_transparency_event(transparency_generator.get_step_event())
        with tracer.start_as_current_span("orchestrator.get_tools"):
            tools = await self._get_tools_schema(active_tools=active_tools)
        transparency_generator.complete_step(
            tools_step,
            metadata={"tool_count": len(tools), "requested_tool_count": len(active_tools)},
        )
        await emit_transparency_event(transparency_generator.get_step_event())

        # Emit initial thinking status
        await stream_callback(agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING
            )
        ))

        # Inject tools into state
        state.context_data["tools_schema"] = tools
        state.context_data["active_tools"] = list(active_tools)

        return transparency_generator, emit_transparency_event

    @staticmethod
    def _coerce_tool_result_payload(raw_result_json: str) -> Any:
        if not raw_result_json:
            return {}
        try:
            return json.loads(raw_result_json)
        except json.JSONDecodeError:
            return {"raw_result": raw_result_json}

    @staticmethod
    def _iter_text_chunks(text: str, chunk_size: int = 240) -> list[str]:
        if not text:
            return []
        return [text[idx:idx + chunk_size] for idx in range(0, len(text), chunk_size)]

    async def _continue_after_tool_result(
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
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        tr = request.tool_result
        conversation_history = self._build_routing_history(conversation_context)
        tool_result = {
            "tool_call_id": tr.tool_call_id,
            "tool_name": tr.tool_name,
            "result": self._coerce_tool_result_payload(tr.result_json),
            "success": not tr.is_error,
            "is_error": bool(tr.is_error),
            "error_message": tr.error_message,
        }

        try:
            llm_response = await llm_service.continue_with_tool_results(
                conversation_history=conversation_history,
                tool_results=[tool_result],
            )
        except Exception as exc:
            logger.error(f"Tool result continuation failed: {exc}", exc_info=True)
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                error=agent_service_pb2.Error(
                    message=f"工具结果续跑失败: {exc}",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_INTERNAL,
                ),
                finish_reason=agent_service_pb2.ERROR,
            )
            return

        full_response = (llm_response.content or "").strip()
        if not full_response:
            full_response = "工具执行已完成，但没有生成补充说明。请继续告诉我下一步需要处理什么。"
            RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="tool_result_empty_final").inc()

        yield agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details=f"正在整合工具结果：{tr.tool_name}",
                current_agent_name="Sparkle AI",
            ),
        )

        for chunk in self._iter_text_chunks(full_response):
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                delta=chunk,
            )

        await self._persist_assistant_message(
            active_db=active_db,
            user_id=user_id,
            session_id=session_id,
            full_response=full_response,
        )
        llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
        await self._record_decision(
            active_db=active_db,
            user_id=user_id,
            user_context_payload=user_context_payload,
            llm_profile_meta=llm_profile_meta,
            full_response=full_response,
        )

        response_metadata = {
            "response_id": response_id,
            "trace_id": trace_id,
            "tool_continuation": "true",
            "tool_name": tr.tool_name,
            "tool_error": str(bool(tr.is_error)).lower(),
            "preference_version": (user_context_payload or {}).get("preference_version", 0),
            "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
        }
        ux_envelope = ux_envelope_builder.build(
            user_message=self._extract_latest_user_message(conversation_history),
            full_response=full_response,
            final_state=WorkflowState(messages=conversation_history, context_data={
                "chat_mode": CHAT_MODE_STANDARD,
                "conversation_context": conversation_context,
                "include_references": False,
                "file_ids": [],
            }),
            executable_plan=None,
            route_decision=RouteDecision(
                execution_mode="direct",
                reason="tool_continuation",
                risk_level="low",
            ),
            include_references=False,
            file_ids=[],
            execution_validation=None,
            conversation_context=conversation_context,
            plan_context=None,
            user_context_payload=user_context_payload,
        )
        response_metadata.update(ux_envelope_builder.to_metadata_map(ux_envelope))
        final_response_data = {
            "message": full_response,
            "tool_results": [tool_result],
            "metadata": response_metadata,
        }
        await self._cache_response(session_id, request_id, final_response_data)
        update_responses, _, _, _, _ = await self._drain_system_updates(user_id)
        for update_resp in update_responses:
            yield update_resp

        yield agent_service_pb2.ChatResponse(
            response_id=response_id,
            created_at=int(datetime.now().timestamp()),
            request_id=request_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            metadata={str(k): str(v) for k, v in response_metadata.items()},
            full_text=full_response,
            finish_reason=agent_service_pb2.STOP,
        )

    async def _handle_multi_agent_mode(
        self,
        chat_mode: str,
        user_message: str,
        user_id: str,
        session_id: str,
        response_id: str,
        request_id: str,
        trace_id: str,
        start_time: float,
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        active_db: AsyncSession | None,
        workflow_id: str,
        prompt_version: str,
        stream_callback,
        result_holder: dict[str, Any] | None = None,
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """Handle non-standard chat modes (multi-agent workflows).

        Yields ChatResponse items directly; caller should ``return`` after iteration.
        """
        logger.info(f"Routing to multi-agent workflow: {chat_mode}")
        result_holder = result_holder if result_holder is not None else {}
        multi_agent_context = {
            "user_id": user_id,
            "session_id": session_id,
            "user_context": user_context_payload,
            "conversation_context": conversation_context,
            "plan_context": plan_context,
            "db_session": active_db,
            "prompt_version": prompt_version,
            "workflow_id": workflow_id,
        }
        full_text_parts: list[str] = []
        full_text_override = ""
        metadata_map: dict[str, str] = {}
        had_error = False
        mode_config = get_workflow_config(chat_mode)

        try:
            response_count = 0
            agents = list(mode_config.collaboration_agents) if mode_config else []
            collaboration_mode = mode_config.collaboration_mode if mode_config else "single"
            if agents and collaboration_mode != "single":
                await self.observability.log_collaboration_start(
                    user_id=user_id,
                    session_id=session_id,
                    agents=agents,
                    mode=collaboration_mode,
                )
            if settings.ENABLE_MODE_WORKFLOW_V2:
                response_stream = self.multi_agent_adapter.execute_mode_workflow(
                    chat_mode=chat_mode,
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    context_data=multi_agent_context,
                    stream_callback=stream_callback,
                    result_holder=result_holder,
                )
            else:
                response_stream = execute_multi_agent_workflow(
                    orchestrator=self,
                    chat_mode=chat_mode,
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    context_data=multi_agent_context,
                    stream_callback=stream_callback,
                    result_holder=result_holder,
                )

            async for response in response_stream:
                response.response_id = response_id
                response.created_at = int(datetime.now().timestamp())
                response.request_id = request_id
                response.trace_id = response.trace_id or trace_id
                response.workflow_id = f"multi_agent_{chat_mode}"
                response.prompt_version = response.prompt_version or prompt_version
                response_count += 1
                content_type = response.WhichOneof("content")
                logger.info(
                    f"[Orchestrator] Multi-agent response #{response_count}: "
                    f"type={content_type}, delta_len={len(response.delta) if response.delta else 0}"
                )
                if response.delta:
                    full_text_parts.append(response.delta)
                if response.full_text:
                    full_text_override = response.full_text
                if response.metadata:
                    for k, v in response.metadata.items():
                        metadata_map[str(k)] = str(v)
                if response.finish_reason == agent_service_pb2.ERROR or response.HasField("error"):
                    had_error = True
                yield response

            logger.info(f"[Orchestrator] Multi-agent workflow completed with {response_count} responses")
            await self._update_state(session_id, STATE_DONE, "Multi-agent workflow completed")
            final_text = full_text_override or "".join(full_text_parts)
            if not had_error and (not final_text or not final_text.strip()):
                execution_summary = str(result_holder.get("execution_summary", "")).strip()
                if execution_summary:
                    final_text = (
                        "执行已完成，以下是关键结果摘要：\n"
                        f"{execution_summary}\n\n"
                        "如需我继续，我可以进一步输出完整分析与下一步计划。"
                    )
                    metadata_map["response_fallback"] = "mode_execution_summary"
                    RESPONSE_FALLBACK_GENERATED_TOTAL.labels(source="mode_empty_final").inc()
            if not had_error and final_text:
                await self._persist_assistant_message(
                    active_db=active_db,
                    user_id=user_id,
                    session_id=session_id,
                    full_response=final_text,
                )
                llm_profile_meta = self._extract_llm_profile_meta(user_context_payload)
                await self._record_decision(
                    active_db=active_db,
                    user_id=user_id,
                    user_context_payload=user_context_payload,
                    llm_profile_meta=llm_profile_meta,
                    full_response=final_text,
                )
                response_metadata = {
                    "response_id": response_id,
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "prompt_version": prompt_version,
                    **metadata_map,
                }
                result_holder["final_response_data"] = {
                    "message": final_text,
                    "full_text": final_text,
                    "tool_results": [],
                    "metadata": response_metadata,
                }
            tool_calls_count = int(result_holder.get("tool_calls_count", 0))
            if agents and collaboration_mode != "single":
                await self.observability.log_collaboration_end(
                    user_id=user_id,
                    session_id=session_id,
                    agents=agents,
                    mode=collaboration_mode,
                    tool_calls_count=tool_calls_count,
                    latency_ms=(time.time() - start_time) * 1000.0,
                )

        except Exception as e:
            logger.error(f"Multi-agent workflow error: {e}")
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message=f"多Agent协作模式执行失败: {str(e)}",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_INTERNAL,
                ),
                finish_reason=agent_service_pb2.ERROR,
            )

    def _inject_state_dependencies(
        self,
        state: WorkflowState,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        stream_callback,
        tools_schema: list[dict[str, Any]],
        transparency_generator: TransparencyDataGenerator,
        emit_transparency_event,
        user_context_payload: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        file_ids: list[str],
        include_references: bool,
        workflow_id: str,
        prompt_version: str,
    ) -> None:
        """Inject all runtime dependencies into the workflow state."""
        if active_db:
            state.context_data["db_session"] = active_db
        state.context_data.update({
            "user_id": user_id,
            "session_id": session_id,
            "stream_callback": stream_callback,
            "tools_schema": tools_schema,
            "transparency_generator": transparency_generator,
            "emit_transparency_event": emit_transparency_event,
            "redis_client": self.redis,
            "user_context": user_context_payload,
            "conversation_context": conversation_context,
            "plan_context": plan_context,
            "file_ids": file_ids,
            "include_references": include_references,
            "workflow_id": workflow_id,
            "prompt_version": prompt_version,
        })

    async def _execute_graph(
        self,
        *,
        state: WorkflowState,
        user_id: str,
        queue: asyncio.Queue,
        result_holder: dict[str, Any],
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        logger.info("🚀 Launching StateGraph Execution")
        graph_task = await task_manager.spawn(
            self.graph.invoke(state),
            task_name="orchestrator_graph",
            user_id=str(user_id),
        )

        total_prompt_tokens = 0
        total_completion_tokens = 0

        while not graph_task.done() or not queue.empty():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.1)
                if item.HasField("usage"):
                    total_prompt_tokens = item.usage.prompt_tokens
                    total_completion_tokens = item.usage.completion_tokens
                    if self.token_tracker:
                        TOKEN_USAGE.labels(model="gpt-4", type="prompt").inc(total_prompt_tokens)
                        TOKEN_USAGE.labels(model="gpt-4", type="completion").inc(total_completion_tokens)
                yield item
                queue.task_done()
            except TimeoutError:
                if graph_task.done():
                    break

        if graph_task.done():
            exc = graph_task.exception()
            if exc:
                raise exc
            result_holder["final_state"] = graph_task.result()
            result_holder["total_prompt_tokens"] = total_prompt_tokens
            result_holder["total_completion_tokens"] = total_completion_tokens

    async def _plan_and_validate(
        self,
        *,
        route_decision: RouteDecision,
        user_message: str,
        user_id: str,
        session_id: str,
        active_db: AsyncSession | None,
        plan_id: uuid.UUID | None,
        conversation_context: dict[str, Any] | None,
        stream_callback,
        state: WorkflowState,
        user_context_payload: dict[str, Any] | None,
    ) -> tuple[RouteDecision, ExecutablePlan | None, StateSnapshot | None, bool]:
        executable_plan = None
        snapshot = None

        if route_decision.execution_mode not in ["langgraph", "hybrid"]:
            return route_decision, executable_plan, snapshot, False

        logger.info(f"Using LangGraph planner for {route_decision.execution_mode} mode")
        allow, reason = await self.langgraph_breaker.allow_request()
        if not allow:
            logger.warning(f"LangGraph blocked by circuit breaker: {reason}")
            await self.observability.log_circuit_state_change(
                circuit_name="langgraph_planner",
                old_state="open",
                new_state="open",
                reason=reason,
            )
            await stream_callback(agent_service_pb2.ChatResponse(
                delta="\n\n⚠️ 智能规划暂时不可用，使用标准模式"
            ))
            route_decision.execution_mode = "direct"
            return route_decision, executable_plan, snapshot, False

        try:
            snapshot = await self.snapshot_manager.create_snapshot(
                user_id=user_id,
                session_id=session_id,
                db_session=active_db,
            )
            conversation_history = []
            if conversation_context:
                conversation_history = conversation_context.get("messages", [])
            plan_id_str = str(plan_id) if plan_id else None

            execution_feedback = await self._load_recent_execution_feedback(
                active_db=active_db,
                user_id=user_id,
                plan_id=plan_id_str,
            )
            planning_constraints = {}
            if isinstance(plan_context, dict) and isinstance(plan_context.get("constraints"), dict):
                planning_constraints = dict(plan_context.get("constraints") or {})
            weak_knowledge_node_ids = planning_constraints.get("weak_knowledge_node_ids") or []
            if weak_knowledge_node_ids and active_db:
                resolved_nodes: list[dict[str, Any]] = []
                normalized_ids: list[uuid.UUID] = []
                for node_id in weak_knowledge_node_ids[:5]:
                    with contextlib.suppress(Exception):
                        normalized_ids.append(uuid.UUID(str(node_id)))
                if normalized_ids:
                    nodes_result = await active_db.execute(
                        select(KnowledgeNode).where(KnowledgeNode.id.in_(normalized_ids))
                    )
                    for node in nodes_result.scalars().all():
                        resolved_nodes.append(
                            {
                                "id": str(node.id),
                                "name": node.name,
                                "description": (node.description or "")[:160],
                            }
                        )
                if resolved_nodes:
                    planning_constraints["weak_knowledge_nodes"] = resolved_nodes

            chat_mode = str(state.context_data.get("chat_mode", CHAT_MODE_STANDARD))
            mode_config = get_workflow_config(chat_mode)
            selected_experts = state.context_data.get("selected_experts", [])
            state_overrides: dict[str, Any] = {}
            if isinstance(selected_experts, list) and selected_experts:
                cleaned = [str(expert).strip() for expert in selected_experts if str(expert).strip()]
                if cleaned:
                    state_overrides["next_step"] = cleaned[0]
                    state_overrides["collaboration_agents"] = cleaned
                    state_overrides["collaboration_mode"] = "sequential"
                    state_overrides["collaboration_order"] = [
                        {"agent": expert, "task": user_message} for expert in cleaned
                    ]
                    state_overrides["collaboration_index"] = 0

            executable_plan = await self.lang_graph_planner.plan(
                message=user_message,
                snapshot=snapshot,
                user_id=user_id,
                session_id=session_id,
                conversation_history=conversation_history,
                plan_id=plan_id_str,
                execution_feedback=execution_feedback,
                mode_config=mode_config,
                state_overrides=state_overrides or None,
                planning_constraints=planning_constraints or None,
            )

            await self.observability.log_langgraph_plan(
                user_id=user_id,
                session_id=session_id,
                plan_id=executable_plan.plan_id,
                plan_data={
                    "agents_involved": executable_plan.agents_involved,
                    "collaboration_mode": executable_plan.collaboration_mode,
                    "tool_calls_count": len(executable_plan.tool_calls),
                    "confidence": executable_plan.confidence,
                    "rationale": executable_plan.rationale,
                },
            )

            logger.info(
                f"LangGraph plan generated: {len(executable_plan.tool_calls)} tool calls, "
                f"confidence={executable_plan.confidence}, "
                f"collaboration={executable_plan.collaboration_mode}, "
                f"agents={executable_plan.agents_involved}"
            )

            current_versions = await self._load_context_versions(user_id)
            conflict = await self.version_conflict_service.check_all_conflicts(
                plan=executable_plan,
                snapshot=snapshot,
                current_context_versions=current_versions,
                user_id=uuid.UUID(user_id),
            )
            if conflict.has_conflict:
                logger.warning(
                    "Version conflict detected: type=%s domains=%s",
                    conflict.conflict_type,
                    conflict.conflicted_domains,
                )
                plan_uuid = uuid.UUID(plan_id_str) if plan_id_str else None

                async def _replan_callback():
                    new_snapshot = await self.snapshot_manager.create_snapshot(
                        user_id=user_id,
                        session_id=session_id,
                        db_session=active_db,
                    )
                    nonlocal snapshot
                    snapshot = new_snapshot
                    return await self.lang_graph_planner.replan(
                        message=user_message,
                        snapshot=new_snapshot,
                        user_id=user_id,
                        session_id=session_id,
                        previous_plan=executable_plan,
                        conflict_info=conflict.to_dict(),
                        plan_id=plan_id_str,
                        execution_feedback=execution_feedback,
                    )

                resolution = await self.version_conflict_service.resolve_conflict(
                    conflict_result=conflict,
                    original_plan=executable_plan,
                    user_id=uuid.UUID(user_id),
                    session_id=session_id,
                    user_message=user_message,
                    plan_id=plan_uuid,
                    replan_callback=_replan_callback,
                )
                if resolution.requires_hitl:
                    await self._stream_hitl_escalation(
                        conflict=conflict,
                        executable_plan=executable_plan,
                        snapshot=snapshot,
                        user_id=str(user_id),
                        stream_callback=stream_callback,
                    )
                    return route_decision, executable_plan, snapshot, True
                if resolution.success and resolution.new_plan:
                    executable_plan = resolution.new_plan
                else:
                    await self._stream_discard_notice(stream_callback)
                    await self.observability.log_validation_failed(
                        user_id=user_id,
                        session_id=session_id,
                        plan_id=executable_plan.plan_id,
                        failure_reason="Version conflict discard",
                    )
                    await self.langgraph_breaker.on_failure("version_conflict_discard")
                    return route_decision, executable_plan, snapshot, True

            validation_result = await self.grounding_validator.validate_plan(
                plan=executable_plan,
                snapshot=snapshot,
                db_session=active_db,
                user_id=user_id,
            )
            if not validation_result.is_valid:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 计划验证失败: {validation_result.failure_reason}"
                ))
                await self.observability.log_validation_failed(
                    user_id=user_id,
                    session_id=session_id,
                    plan_id=executable_plan.plan_id,
                    failure_reason=validation_result.failure_reason,
                )
                await self.langgraph_breaker.on_failure("validation_failed")
                return route_decision, executable_plan, snapshot, True
            if validation_result.warnings:
                state.context_data["knowledge_readiness_warnings"] = validation_result.warnings
                for warning in validation_result.warnings[:3]:
                    message = str(warning.get("message") or "").strip()
                    if message and f"knowledge_warning:{message}" not in executable_plan.risk_flags:
                        executable_plan.risk_flags.append(f"knowledge_warning:{message}")
                first_warning = validation_result.warnings[0]
                warning_message = str(first_warning.get("message") or "").strip()
                if warning_message:
                    existing_rationale = (executable_plan.rationale or "").strip()
                    suffix = f" 知识前置提醒：{warning_message}。"
                    if suffix.strip() not in existing_rationale:
                        executable_plan.rationale = f"{existing_rationale}{suffix}".strip()

            preflight = await self.grounding_validator.preflight_check(
                plan=executable_plan,
                user_id=user_id,
            )
            if not preflight["is_ready"]:
                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"\n\n⚠️ 服务暂时不可用: {', '.join(preflight['blocked_by'])}"
                ))
                await self.langgraph_breaker.on_failure("preflight_blocked")
                return route_decision, executable_plan, snapshot, True

            if executable_plan and route_decision.execution_mode in ["langgraph", "hybrid"]:
                review_result = await plan_review_service.review_plan(
                    plan=executable_plan,
                    user_message=user_message,
                    user_context=user_context_payload or {},
                )
                if plan_id:
                    from app.services.plan_feedback_service import get_plan_feedback_service

                    feedback_service = get_plan_feedback_service(active_db, self.redis)
                    await feedback_service.append_review_feedback(
                        user_id=uuid.UUID(user_id),
                        plan_id=uuid.UUID(plan_id),
                        review_result=review_result,
                        user_decision=None,
                    )
                    logger.info(f"Review feedback written for plan {plan_id}")

                if review_result.decision in [
                    ReviewDecision.REJECTED.value,
                    ReviewDecision.REQUIRES_CONFIRMATION.value,
                    ReviewDecision.NEEDS_MODIFICATION.value,
                ]:
                    action_id = await plan_review_service.store_review_result(
                        review=review_result,
                        user_id=str(user_id),
                    )
                    review_data_dict = review_result.to_dict()
                    review_data_dict["action_id"] = action_id
                    review_metadata = {
                        "requires_review": "true",
                        "review_action_id": action_id,
                        "review_decision": review_result.decision,
                        "review_id": review_result.review_id,
                        "plan_id": review_result.plan_id,
                        "review_data": json.dumps(review_data_dict),
                    }
                    review_delta = self._format_review_message(review_result)
                    await stream_callback(agent_service_pb2.ChatResponse(
                        delta=review_delta,
                        metadata=review_metadata,
                    ))
                    state.context_data["plan_review"] = review_result.to_dict()
                    state.context_data["pending_review_action_id"] = action_id
                    logger.info(
                        f"Plan {executable_plan.plan_id} requires user review: "
                        f"{review_result.decision} (action_id={action_id})"
                    )
                    return route_decision, executable_plan, snapshot, True

                state.context_data["plan_review"] = review_result.to_dict()
                logger.info(
                    f"Plan {executable_plan.plan_id} auto-approved: "
                    f"confidence={review_result.confidence}"
                )

            state.context_data["executable_plan"] = executable_plan
            state.context_data["snapshot"] = snapshot
            await self.langgraph_breaker.on_success()

            plan_summary = self.lang_graph_planner.get_plan_summary(executable_plan)
            logger.info(f"Plan ready for execution: {plan_summary}")
            if executable_plan.collaboration_mode != "single":
                await self.observability.log_collaboration_start(
                    user_id=user_id,
                    session_id=session_id,
                    agents=executable_plan.agents_involved,
                    mode=executable_plan.collaboration_mode,
                )

            asyncio.create_task(
                self.shadow_predictor.predict_and_record(
                    user_message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    actual_decision=route_decision,
                    actual_plan=executable_plan,
                )
            )
            return route_decision, executable_plan, snapshot, False
        except Exception as e:
            logger.error(f"LangGraph planning error: {e}", exc_info=True)
            await self.langgraph_breaker.on_failure(str(e))
            await stream_callback(agent_service_pb2.ChatResponse(
                delta=f"\n\n⚠️ 规划失败，使用直接模式: {str(e)}"
            ))
            route_decision.execution_mode = "direct"
            return route_decision, executable_plan, snapshot, False

    async def _build_full_context(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        user_message: str,
        request_id: str,
        tracer,
    ) -> tuple[dict[str, Any], uuid.UUID | None, bool, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        grpc_context = {}
        if request.user_profile and request.user_profile.extra_context:
            try:
                grpc_context = json.loads(request.user_profile.extra_context)
                logger.debug(f"Parsed extra_context from gRPC: {list(grpc_context.keys())}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extra_context JSON: {e}")

        request_context = {}
        if request.HasField("extra_context"):
            try:
                request_context = MessageToDict(request.extra_context)
                if request_context:
                    logger.debug(f"Parsed request extra_context: {list(request_context.keys())}")
            except Exception as e:
                logger.warning(f"Failed to parse request extra_context: {e}")

        if request_context:
            grpc_context = {**grpc_context, **request_context}

        plan_id = None
        if grpc_context and "plan_id" in grpc_context:
            with contextlib.suppress(ValueError, AttributeError):
                plan_id = uuid.UUID(grpc_context["plan_id"])

        plan_switched = False
        if not plan_id and user_message and active_db:
            with tracer.start_as_current_span("orchestrator.auto_switch_plan"):
                try:
                    from app.services.plan_matching_service import PlanMatchingService
                    plan_matching = PlanMatchingService(active_db)
                    matched_plan_id = await self.state_manager.auto_switch_plan(
                        session_id=session_id,
                        user_id=uuid.UUID(user_id),
                        task_context={
                            "content": user_message,
                            "type": grpc_context.get("task_type", "chat"),
                        },
                        db_session=active_db,
                        plan_matching_service=plan_matching,
                    )
                    if matched_plan_id:
                        plan_id = matched_plan_id
                        plan_switched = True
                        logger.info(f"Auto-switched to plan {plan_id} based on message content")
                except Exception as e:
                    logger.warning(f"Auto-switch plan failed: {e}")

        overlay_versions = {}
        if grpc_context:
            versions = grpc_context.get("realtime_versions")
            if isinstance(versions, dict):
                overlay_versions = {str(k): str(v) for k, v in versions.items()}
        if overlay_versions:
            await self._self_heal_versions(user_id, overlay_versions, active_db)

        if grpc_context and ("realtime_versions" in grpc_context or "overlay_generated_at" in grpc_context):
            grpc_context = dict(grpc_context)
            grpc_context.pop("realtime_versions", None)
            grpc_context.pop("overlay_generated_at", None)

        user_context_payload = None
        conversation_context = None
        plan_context = None
        with tracer.start_as_current_span("db.build_context"):
            if active_db and user_id:
                local_context = await self._build_user_context(user_id, active_db)
                user_context_payload = self._merge_user_contexts(local_context, grpc_context)
                logger.info(f"Merged user context: {user_context_payload is not None}")

                if plan_id:
                    try:
                        from app.core.plan_context import PlanContextBuilder
                        from app.services.plan_state_service import PlanStateService

                        plan_builder = PlanContextBuilder(active_db, self.redis)
                        plan_context = await plan_builder.build_enriched(uuid.UUID(user_id), plan_id)
                        if plan_context:
                            logger.info(f"Built plan_context for plan_id={plan_id}")
                            if user_context_payload is None:
                                user_context_payload = {}
                            user_context_payload["plan_context"] = plan_context

                            try:
                                plan_state_svc = PlanStateService(active_db, self.redis)
                                plan_state = await plan_state_svc.get_plan_state(
                                    uuid.UUID(user_id), uuid.UUID(plan_id)
                                )
                                if plan_state and plan_state.constraints.get("require_phase_rollback"):
                                    logger.info(f"Phase rollback triggered for plan_id={plan_id}")
                                    await plan_state_svc.upsert_plan_state(
                                        user_id=uuid.UUID(user_id),
                                        plan_id=uuid.UUID(plan_id),
                                        patch={"constraints": {"require_phase_rollback": False}},
                                        bump_version=False,
                                    )
                                    plan_context["mode"] = "phase_rollback"
                                    plan_context["rollback_reason"] = "2次连续拒绝，需重新收集信息"
                                    if plan_state.feedback_log:
                                        plan_context["previous_feedback"] = plan_state.feedback_log[-2:]
                            except Exception as e:
                                logger.warning(f"Failed to check phase rollback: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to build plan context: {e}")

                try:
                    user_uuid = uuid.UUID(user_id)
                    router = ToolPreferenceRouter(active_db, user_uuid, self.redis)
                    preferred_tools = await router.get_preferred_tools(limit=3)
                    if preferred_tools:
                        if user_context_payload is not None:
                            user_context_payload["preferred_tools"] = preferred_tools
                        logger.info(f"Injected tool preferences for user {user_id}: {preferred_tools}")
                except Exception as e:
                    logger.warning(f"Failed to get tool preferences (non-fatal): {e}")
                    if active_db:
                        await active_db.rollback()
            elif grpc_context:
                user_context_payload = grpc_context
                logger.info("Using gRPC context without local DB context")

        self._log_context_injection(user_id, user_context_payload)
        if self.context_pruner:
            with tracer.start_as_current_span("db.build_conversation_context"):
                conversation_context = await self._build_conversation_context(session_id, user_id)

        if active_db and user_message:
            try:
                user_msg = ChatMessage(
                    user_id=uuid.UUID(str(user_id)),
                    session_id=uuid.UUID(str(session_id)),
                    role=MessageRole.USER,
                    content=user_message,
                    message_id=request_id,
                )
                active_db.add(user_msg)
                await active_db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist user chat message: {e}")
                with contextlib.suppress(Exception):
                    await active_db.rollback()

        return grpc_context, plan_id, plan_switched, user_context_payload, conversation_context, plan_context

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
                update_responses, adaptation_records, preference_learnings, evolution_highlights, progress_snapshot = await self._drain_system_updates(user_id)
                if adaptation_records:
                    state.context_data["adaptation_records"] = adaptation_records
                if preference_learnings:
                    state.context_data["preference_learnings"] = preference_learnings
                if evolution_highlights:
                    state.context_data["evolution_highlights"] = evolution_highlights
                if progress_snapshot:
                    state.context_data["progress_snapshot"] = progress_snapshot
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
                    await stream_callback(agent_service_pb2.ChatResponse(metadata={"plan_switched": "true", "switched_to_plan_id": str(plan_id)}))

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
                if expert_routing_decision:
                    state.context_data["expert_routing_metadata"] = expert_routing_decision.to_metadata()
                    state.context_data["selected_experts"] = list(expert_routing_decision.selected_experts)
                    state.context_data["expert_policy_id"] = expert_routing_decision.policy_id

                # Step 9: Multi-agent mode (early exit)
                if chat_mode != CHAT_MODE_STANDARD and not settings.ENABLE_UNIFIED_GRAPH_ROUTING:
                    mode_result: dict[str, Any] = {}
                    async for resp in self._handle_multi_agent_mode(
                        chat_mode=chat_mode, user_message=user_message, user_id=user_id, session_id=session_id,
                        response_id=response_id, request_id=request_id, trace_id=trace_id, start_time=start_time,
                        user_context_payload=user_context_payload, conversation_context=conversation_context,
                        plan_context=plan_context, active_db=active_db, workflow_id=workflow_id,
                        prompt_version=prompt_version, stream_callback=stream_callback, result_holder=mode_result,
                    ):
                        yield resp
                    final_response_data = mode_result.get("final_response_data")
                    if isinstance(final_response_data, dict):
                        with tracer.start_as_current_span("orchestrator.cache_mode_response"):
                            await self._cache_response(session_id, request_id, final_response_data)
                        followup_updates, _, _, _, _ = await self._drain_system_updates(user_id)
                        for update_resp in followup_updates:
                            yield update_resp
                    return

                # Step 10: Route
                route_decision, unified_routing_result = await self._route_and_classify(
                    user_message=user_message, user_id=user_id, session_id=session_id,
                    grpc_context=grpc_context, conversation_context=conversation_context, state=state,
                )
                if settings.ENABLE_UNIFIED_GRAPH_ROUTING and chat_mode != CHAT_MODE_STANDARD:
                    route_decision.execution_mode = "langgraph"
                    route_decision.reason = (
                        f"{route_decision.reason} | unified_mode:{chat_mode}"
                        if route_decision.reason
                        else f"unified_mode:{chat_mode}"
                    )

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

                # Step 11: Plan & validate (langgraph/hybrid mode)
                route_decision, executable_plan, snapshot, should_return = await self._plan_and_validate(
                    route_decision=route_decision, user_message=user_message, user_id=user_id, session_id=session_id,
                    active_db=active_db, plan_id=plan_id, conversation_context=conversation_context,
                    stream_callback=stream_callback, state=state, user_context_payload=user_context_payload,
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
                    followup_updates, _, _, _, _ = await self._drain_system_updates(user_id)
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
                )

            finally:
                await self._cleanup(
                    lock_acquired=lock_acquired, lock_renewal_task=lock_renewal_task, lock_renewal_stop=lock_renewal_stop,
                    session_id=session_id, request_id=request_id, start_time=start_time, user_id=user_id,
                    total_prompt_tokens=total_prompt_tokens, total_completion_tokens=total_completion_tokens,
                )

    async def _notify_pending_milestone_proposals(
        self,
        user_id: str,
        stream_callback,
    ) -> None:
        """
        Check and send pending milestone proposals to user.
        Called at the start of StreamChat to notify users of pending proposals.
        """
        from app.core.pending_actions import pending_actions_store

        try:
            actions = await pending_actions_store.get_all_by_user(user_id)

            # Find milestone proposals
            milestone_proposals = [
                a for a in actions
                if a.get("tool_name") == "milestone_task_proposal"
            ]

            if not milestone_proposals:
                return

            logger.info(f"Found {len(milestone_proposals)} pending milestone proposal(s) for user {user_id}")

            for proposal_action in milestone_proposals:
                preview = proposal_action.get("preview_data", {})
                if not preview:
                    continue

                await stream_callback(agent_service_pb2.ChatResponse(
                    delta=f"🎉 恭喜达成里程碑！为你推荐 {preview.get('suggested_count', 0)} 个新任务",
                    metadata={
                        "widget_event": "milestone_proposal",
                        "proposal_id": preview.get("proposal_id"),
                        "action_id": proposal_action.get("action_id"),
                        "plan_id": preview.get("plan_id"),
                        "milestone_id": preview.get("milestone_id"),
                        "task_count": preview.get("suggested_count", 0),
                        "reasoning": preview.get("reasoning", ""),
                        "tasks": json.dumps(preview.get("proposed_tasks", [])),
                    }
                ))

        except Exception as e:
            logger.warning(f"Failed to notify milestone proposals: {e}")

# Backwards-compatible alias for benchmarks/tests
Orchestrator = ChatOrchestrator
