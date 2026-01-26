import json
import asyncio
import time
from typing import AsyncGenerator, List, Dict, Optional, Any
from loguru import logger
from datetime import datetime
import uuid

from google.protobuf.json_format import MessageToDict
from google.protobuf import struct_pb2

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import llm_service
from app.services.system_update_service import SystemUpdateService
from app.services.knowledge_service import KnowledgeService
from app.services.galaxy_service import GalaxyService
from app.services.user_service import UserService
from app.services.focus_service import focus_service
from app.models.task import Task, TaskStatus as ModelTaskStatus
from app.models.plan import Plan
from sqlalchemy import select, and_, desc, asc, func
from app.orchestration.prompts import build_system_prompt
from app.orchestration.executor import ToolExecutor
from app.orchestration.state_manager import SessionStateManager, FSMState
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.validator import RequestValidator, ValidationResult
from app.orchestration.composer import ResponseComposer
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.token_tracker import TokenTracker
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.gen.agent.v1 import agent_service_pb2
from app.config import settings
from app.core.metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, TOKEN_USAGE, TOOL_EXECUTION_COUNT, ACTIVE_SESSIONS
)
from app.core.business_metrics import (
    COLLABORATION_SUCCESS,
    COLLABORATION_LATENCY,
    HITL_REQUESTED
)
from app.core.pending_actions import pending_actions_store
from app.orchestration.statechart_engine import WorkflowState, StateGraph
from app.agents.standard_workflow import create_standard_chat_graph
from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.core.task_manager import task_manager
from app.core.celery_app import schedule_long_task
from app.orchestration.plan_review_service import plan_review_service, ReviewDecision
from opentelemetry import trace

# Phase 1 & Phase 2: Full-Loop Closed System with LangGraph Planner
from app.orchestration.request_router import RequestRouter
from app.orchestration.grounding_validator import GroundingValidator
from app.orchestration.schemas import (
    ExecutablePlan, FeedbackPayload, StateSnapshot,
    VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD,
    MAX_REPLAN_ATTEMPTS,
    REPLAN_RATE_LIMIT_WINDOW,
    REPLAN_MAX_PER_WINDOW,
)
from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.orchestration.state_snapshot import StateSnapshotManager

# Phase 3: Circuit Breaker, Observability, Shadow Mode
from app.orchestration.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
)
# Multi-Agent Mode Support
from app.orchestration.multi_agent_adapter import execute_multi_agent_workflow, CHAT_MODE_STANDARD
from app.orchestration.observability_logger import observability_logger
from app.services.shadow_prediction_service import shadow_prediction_service

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

    def __init__(self, db_session: Optional[AsyncSession] = None, redis_client=None, user_id: Optional[str] = None):
        if redis_client is None:
            logger.error("ChatOrchestrator requires Redis, but no redis_client was provided")
            raise ValueError("redis_client is required for ChatOrchestrator")
        self.db_session = db_session
        self.redis = redis_client
        self.redis_client = redis_client
        self.user_id = user_id

        # Initialize components
        self.state_manager = SessionStateManager(redis_client)
        self.validator = RequestValidator(redis_client, daily_quota=100000)
        self.tool_executor = ToolExecutor()
        self.response_composer = ResponseComposer()

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
        from app.visualization.realtime_visualizer import visualizer
        from app.visualization.execution_tracer import ExecutionTracer

        self.tracer = ExecutionTracer(redis_client)

        self.graph.on_event = self._chain_event_handlers(
            visualizer.on_graph_event,
            self.tracer.record_event
        )

        # Phase 1: Initialize new components
        self.request_router = RequestRouter(redis_client)
        self.grounding_validator = GroundingValidator(redis_client)
        logger.info("ChatOrchestrator initialized with RequestRouter and GroundingValidator")

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

    async def _emit_system_updates(self, user_id: str) -> List[agent_service_pb2.ChatResponse]:
        updates = await SystemUpdateService(self.redis).drain(user_id, limit=20)
        responses: List[agent_service_pb2.ChatResponse] = []
        for update in updates:
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
        return responses
        asyncio.create_task(self.langgraph_breaker.initialize())

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

    def _infer_domain_for_tool(self, tool_name: str) -> Optional[str]:
        tool_lower = tool_name.lower()
        if "task" in tool_lower:
            return "tasks"
        if "plan" in tool_lower or "sprint" in tool_lower:
            return "plans"
        if "focus" in tool_lower or "pomodoro" in tool_lower:
            return "focus"
        if "friend" in tool_lower or "group" in tool_lower or "community" in tool_lower:
            return "community"
        if "knowledge" in tool_lower or "graph" in tool_lower or "galaxy" in tool_lower:
            return "knowledge"
        return None

    def _get_plan_affected_domains(self, plan: ExecutablePlan) -> set:
        domains = set()
        for tool_call in plan.tool_calls:
            domain = self._infer_domain_for_tool(tool_call.name)
            if domain:
                domains.add(domain)
        return domains

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

    async def _check_idempotency(self, session_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if request was already processed
        
        Returns:
            Optional[Dict]: Cached response if duplicate, None otherwise
        """
        if not self.state_manager:
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

    async def _cache_response(self, session_id: str, request_id: str, response_data: Dict[str, Any]):
        """Cache response for idempotency"""
        if self.state_manager:
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

    async def _load_context_versions(self, user_id: str) -> Dict[str, str]:
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

    async def _save_context_versions(self, user_id: str, versions: Dict[str, str]) -> None:
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
        overlay_versions: Dict[str, str],
        db_session: Optional[AsyncSession],
    ) -> None:
        if not overlay_versions or not user_id:
            return

        previous = await self._load_context_versions(user_id)
        healed: List[str] = []

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

    async def _check_replan_rate_limit(self, plan_id: Optional[uuid.UUID]) -> tuple[bool, int]:
        """Check replan rate limit to prevent excessive replanning

        Args:
            plan_id: Plan ID to check rate limit for

        Returns:
            tuple[bool, int]: (is_allowed, current_count)
        """
        if not self.redis or not plan_id:
            return True, 0

        window_key = f"replan:rate:{plan_id}:{int(time.time()) // REPLAN_RATE_LIMIT_WINDOW}"

        try:
            current = await self.redis.incr(window_key)
            await self.redis.expire(window_key, REPLAN_RATE_LIMIT_WINDOW)
            return current <= REPLAN_MAX_PER_WINDOW, current
        except Exception as e:
            logger.warning(f"Failed to check replan rate limit: {e}")
            return True, 0

    def _merge_user_contexts(self, local_context: Dict[str, Any], grpc_context: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _get_task_status_summary(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
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
                    Task.due_date < datetime.utcnow()
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

    async def _get_cognitive_insights(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """获取认知模式摘要，注入 LLM 上下文

        当用户有已识别的行为模式时，LLM 可以在合适时机主动展示认知棱镜。
        """
        try:
            from app.services.cognitive_service import CognitiveService
            from uuid import UUID

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

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
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
            from app.core.context_manager import ContextOrchestrator, CognitiveContext
            
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
                            Plan.is_active == True
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

                return {
                    "user_context": user_context_data, # Legacy field
                    "analytics_summary": cognitive_context.engagement_metrics,
                    "preferences": cognitive_context.preferences,
                    "next_actions": cognitive_context.active_tasks,
                    "active_plans": active_plans,
                    "focus_stats": cognitive_context.focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "task_status_summary": task_status_summary,

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
                        Plan.is_active == True
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
                return {
                    "user_context": user_context_data,
                    "analytics_summary": analytics,
                    "preferences": {
                        "depth_preference": user_context.preferences.get("depth_preference", 0.5),
                        "curiosity_preference": user_context.preferences.get("curiosity_preference", 0.5),
                    },
                    "next_actions": next_actions,
                    "active_plans": active_plans,
                    "focus_stats": focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "task_status_summary": task_status_summary,
                }
            else:
                # Fallback to basic context
                logger.warning(f"User {user_id} not found, using fallback context")
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
            }

    async def _build_conversation_context(self, session_id: str, user_id: str) -> Dict[str, Any]:
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

    def _log_context_injection(self, user_id: str, context: Optional[Dict[str, Any]]) -> None:
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

    async def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools from dynamic registry"""
        try:
            return dynamic_tool_registry.get_openai_tools_schema()
        except Exception as e:
            logger.error(f"Failed to get tools schema: {e}")
            return []

    async def process_stream(
        self,
        request: agent_service_pb2.ChatRequest,
        db_session: Optional[AsyncSession] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Process the incoming chat request with enhanced features
        """
        tracer = trace.get_tracer(__name__)
        
        # Start Root Span
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
            
            # Use provided session or instance session
            active_db = db_session or self.db_session
            
            # Step 0: Request Validation (with quota check)
            with tracer.start_as_current_span("orchestrator.validate_request"):
                if self.validator:
                    validation_result = await self.validator.validate_chat_request(request)
                    if not validation_result.is_valid:
                        logger.error(f"Validation failed: {validation_result.error_message}")
                        yield agent_service_pb2.ChatResponse(
                            response_id=response_id,
                            created_at=int(datetime.now().timestamp()),
                            request_id=request_id,
                            error=agent_service_pb2.Error(
                                code="VALIDATION_ERROR",
                                message=validation_result.error_message,
                                retryable=False
                            ),
                            finish_reason=agent_service_pb2.ERROR
                        )
                        return

            # Step 1: Check Idempotency
            with tracer.start_as_current_span("orchestrator.check_idempotency"):
                cached_response = await self._check_idempotency(session_id, request_id)
                if cached_response:
                    logger.info(f"Cache hit for session {session_id}, request {request_id}")
                    cached_metadata = cached_response.get("metadata") if isinstance(cached_response, dict) else None
                    metadata_map = {}
                    if isinstance(cached_metadata, dict):
                        metadata_map = {str(k): str(v) for k, v in cached_metadata.items()}
                    # Return cached response
                    yield agent_service_pb2.ChatResponse(
                        response_id=response_id,
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        full_text=cached_response.get("full_text") or cached_response.get("message", ""),
                        metadata=metadata_map,
                        finish_reason=agent_service_pb2.STOP
                    )
                    return

            # Step 2: Acquire Distributed Lock
            with tracer.start_as_current_span("redis.acquire_lock"):
                lock_acquired = await self._acquire_session_lock(session_id, request_id)
            
            if not lock_acquired:
                yield agent_service_pb2.ChatResponse(
                    response_id=response_id,
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    error=agent_service_pb2.Error(
                        code="CONFLICT",
                        message="Another request is processing for this session",
                        retryable=True
                    ),
                    finish_reason=agent_service_pb2.ERROR
                )
                return

            total_prompt_tokens = 0
            total_completion_tokens = 0

            try:
                # Step 3: Initialize Workflow State
                await self._update_state(session_id, STATE_INIT, f"Request {request_id}")

                # Step 3.5: Extract chat mode for multi-agent routing
                chat_mode = CHAT_MODE_STANDARD
                if request.chat_mode:
                    chat_mode = request.chat_mode
                    logger.info(f"Chat mode requested: {chat_mode}")

                user_message = ""
                if request.message:
                    user_message = request.message
                elif request.HasField("tool_result"):
                    tool_result = request.tool_result
                    user_message = f"Tool '{tool_result.tool_name}' execution result: {tool_result.result_json}"

                # P0: Build user + conversation context
                # First, try to merge extra_context from gRPC (from Go Gateway)
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

                # Extract plan_id from extra_context for PlanScope
                plan_id = None
                if grpc_context and "plan_id" in grpc_context:
                    try:
                        plan_id = uuid.UUID(grpc_context["plan_id"])
                    except (ValueError, AttributeError):
                        pass

                # P0: Auto-switch plan based on task context if no plan_id provided
                plan_switched = False
                if not plan_id and user_message and active_db:
                    with tracer.start_as_current_span("orchestrator.auto_switch_plan"):
                        try:
                            from app.services.plan_matching_service import PlanMatchingService
                            plan_matching = PlanMatchingService(active_db)

                            # Try to match the message to a plan
                            matched_plan_id = await self.session_state.auto_switch_plan(
                                session_id=session_id,
                                user_id=uuid.UUID(user_id),
                                task_context={
                                    "content": user_message,
                                    "type": grpc_context.get("task_type", "chat"),
                                },
                                db_session=active_db,
                                plan_matching_service=plan_matching
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

                if grpc_context:
                    if "realtime_versions" in grpc_context or "overlay_generated_at" in grpc_context:
                        grpc_context = dict(grpc_context)
                        grpc_context.pop("realtime_versions", None)
                        grpc_context.pop("overlay_generated_at", None)

                user_context_payload = None
                conversation_context = None
                plan_context = None

                with tracer.start_as_current_span("db.build_context"):
                    if active_db and user_id:
                        local_context = await self._build_user_context(user_id, active_db)
                        # P0: Merge contexts - prioritize gRPC context (more recent) over local context
                        user_context_payload = self._merge_user_contexts(local_context, grpc_context)
                        logger.info(f"Merged user context: {user_context_payload is not None}")

                        # PlanScope: Build plan_context if plan_id is provided
                        if plan_id:
                            try:
                                from app.core.plan_context import PlanContextBuilder
                                plan_builder = PlanContextBuilder(active_db, self.redis)
                                plan_context = await plan_builder.build(uuid.UUID(user_id), plan_id)
                                if plan_context:
                                    logger.info(f"Built plan_context for plan_id={plan_id}")
                                    # Include plan_context in user_context_payload
                                    if user_context_payload is None:
                                        user_context_payload = {}
                                    user_context_payload["plan_context"] = plan_context

                                    # P0-2: Check for phase rollback requirement
                                    try:
                                        from app.services.plan_state_service import PlanStateService
                                        plan_state_svc = PlanStateService(active_db, self.redis)
                                        plan_state = await plan_state_svc.get_plan_state(
                                            uuid.UUID(user_id), uuid.UUID(plan_id)
                                        )
                                        if plan_state and plan_state.constraints.get("require_phase_rollback"):
                                            logger.info(f"Phase rollback triggered for plan_id={plan_id}")
                                            # Clear the flag
                                            await plan_state_svc.upsert_plan_state(
                                                user_id=uuid.UUID(user_id),
                                                plan_id=uuid.UUID(plan_id),
                                                patch={"constraints": {"require_phase_rollback": False}},
                                                bump_version=False,
                                            )
                                            # Inject rollback context
                                            plan_context["mode"] = "phase_rollback"
                                            plan_context["rollback_reason"] = "2次连续拒绝，需重新收集信息"
                                            # Get last 2 feedback entries for context
                                            if plan_state.feedback_log:
                                                plan_context["previous_feedback"] = plan_state.feedback_log[-2:]
                                    except Exception as e:
                                        logger.warning(f"Failed to check phase rollback: {e}")
                            except Exception as e:
                                logger.warning(f"Failed to build plan context: {e}")

                        # P4: Tool Preference Routing
                        try:
                            # Convert user_id string to UUID
                            user_uuid = uuid.UUID(user_id)
                            router = ToolPreferenceRouter(active_db, user_uuid, self.redis)
                            preferred_tools = await router.get_preferred_tools(limit=3)
                            if preferred_tools:
                                if user_context_payload is not None:
                                    user_context_payload["preferred_tools"] = preferred_tools
                                logger.info(f"Injected tool preferences for user {user_id}: {preferred_tools}")
                        except Exception as e:
                            logger.warning(f"Failed to get tool preferences: {e}")
                    elif grpc_context:
                        # If no DB session but have gRPC context, use it
                        user_context_payload = grpc_context
                        logger.info("Using gRPC context without local DB context")

                self._log_context_injection(user_id, user_context_payload)

                if self.context_pruner:
                    with tracer.start_as_current_span("db.build_conversation_context"):
                        conversation_context = await self._build_conversation_context(session_id, user_id)

                # Prepare initial state
                state = WorkflowState()
                state.append_message("user", user_message)
                
                # Get tools
                with tracer.start_as_current_span("orchestrator.get_tools"):
                    tools = await self._get_tools_schema()

                # Prepare queue for streaming
                queue = asyncio.Queue()
                
                async def stream_callback(resp: agent_service_pb2.ChatResponse):
                    # Augment response with IDs
                    resp.response_id = response_id
                    resp.created_at = int(datetime.now().timestamp())
                    resp.request_id = request_id
                    resp.workflow_id = resp.workflow_id or workflow_id
                    resp.prompt_version = resp.prompt_version or prompt_version
                    resp.trace_id = resp.trace_id or trace_id
                    await queue.put(resp)

                # Emit initial thinking status
                await stream_callback(agent_service_pb2.ChatResponse(
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.THINKING
                    )
                ))

                # Check and notify pending milestone proposals
                await self._notify_pending_milestone_proposals(user_id, stream_callback)

                # P0: Send plan switch notification if auto-switched
                if plan_switched and plan_id:
                    await stream_callback(agent_service_pb2.ChatResponse(
                        metadata={
                            "plan_switched": "true",
                            "switched_to_plan_id": str(plan_id),
                        }
                    ))
                    logger.info(f"Sent plan switch notification to client: plan_id={plan_id}")

                # Inject Dependencies
                if active_db:
                    state.context_data["db_session"] = active_db
                
                state.context_data.update({
                    "user_id": user_id,
                    "session_id": session_id,
                    "stream_callback": stream_callback,
                    "tools_schema": tools,
                    "redis_client": self.redis,
                    "user_context": user_context_payload,
                    "conversation_context": conversation_context,
                    "plan_context": plan_context,
                    "file_ids": list(request.file_ids),
                    "include_references": bool(request.include_references),
                    "workflow_id": workflow_id,
                    "prompt_version": prompt_version,
                })

                # === Multi-Agent Mode Routing ===
                # Check if a specific chat mode is requested
                if chat_mode != CHAT_MODE_STANDARD:
                    logger.info(f"Routing to multi-agent workflow: {chat_mode}")

                    # Prepare context for multi-agent workflow
                    multi_agent_context = {
                        "user_id": user_id,
                        "session_id": session_id,
                        "user_context": user_context_payload,
                        "conversation_context": conversation_context,
                        "plan_context": plan_context,
                    }

                    try:
                        # Execute multi-agent workflow and stream responses
                        async for response in execute_multi_agent_workflow(
                            orchestrator=self,
                            chat_mode=chat_mode,
                            message=user_message,
                            user_id=user_id,
                            session_id=session_id,
                            context_data=multi_agent_context,
                            stream_callback=stream_callback,
                        ):
                            # Add response metadata
                            response.response_id = response_id
                            response.created_at = int(datetime.now().timestamp())
                            response.request_id = request_id
                            response.trace_id = response.trace_id or trace_id
                            response.workflow_id = f"multi_agent_{chat_mode}"
                            await queue.put(response)

                        # Signal completion
                        await queue.put(agent_service_pb2.ChatResponse(
                            response_id=response_id,
                            created_at=int(datetime.now().timestamp()),
                            request_id=request_id,
                            trace_id=trace_id,
                            workflow_id=f"multi_agent_{chat_mode}",
                            finish_reason=agent_service_pb2.STOP,
                        ))

                        # Update final state
                        await self._update_state(session_id, STATE_DONE, "Multi-agent workflow completed")

                        # Stream all responses from queue
                        while True:
                            item = await queue.get()
                            yield item
                            if item.finish_reason != agent_service_pb2.NULL:
                                break

                        # Log completion
                        REQUEST_COUNT.labels(
                            mode="multi_agent",
                            chat_mode=chat_mode,
                            status="success"
                        ).inc()
                        REQUEST_LATENCY.labels(
                            mode="multi_agent",
                            chat_mode=chat_mode
                        ).observe(time.time() - start_time)

                        return

                    except Exception as e:
                        logger.error(f"Multi-agent workflow error: {e}")
                        yield agent_service_pb2.ChatResponse(
                            response_id=response_id,
                            created_at=int(datetime.now().timestamp()),
                            request_id=request_id,
                            error=agent_service_pb2.Error(
                                code="MULTI_AGENT_ERROR",
                                message=f"多Agent协作模式执行失败: {str(e)}",
                                retryable=True,
                            ),
                            finish_reason=agent_service_pb2.ERROR,
                        )
                        return

                # === Phase 1 & Phase 2: Routing & Validation Setup ===
                # 路由决策
                route_decision = await self.request_router.decide(
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id
                )
                logger.info(
                    f"Route decision: {route_decision.execution_mode} "
                    f"(risk: {route_decision.risk_level}, intent: {route_decision.reason})"
                )

                # 存储路由决策和 plan 元数据到 state
                # 工具执行节点会使用这些信息进行验证
                state.context_data["plan_metadata"] = {
                    "context_version": route_decision.context_version,
                    "execution_mode": route_decision.execution_mode,
                    "risk_level": route_decision.risk_level,
                    "route_reason": route_decision.reason
                }
                state.context_data["grounding_validator"] = self.grounding_validator

                # === Phase 2: LangGraph Planning Mode ===
                # === Phase 3: With Circuit Breaker, Observability, Shadow Mode ===
                executable_plan = None
                snapshot = None

                if route_decision.execution_mode in ["langgraph", "hybrid"]:
                    logger.info(f"Using LangGraph planner for {route_decision.execution_mode} mode")

                    # === Phase 3: Circuit Breaker Check ===
                    allow, reason = await self.langgraph_breaker.allow_request()
                    if not allow:
                        logger.warning(f"LangGraph blocked by circuit breaker: {reason}")
                        await self.observability.log_circuit_state_change(
                            circuit_name="langgraph_planner",
                            old_state="open",
                            new_state="open",
                            reason=reason
                        )
                        # Degrade to direct mode
                        await stream_callback(agent_service_pb2.ChatResponse(
                            delta=f"\n\n⚠️ 智能规划暂时不可用，使用标准模式"
                        ))
                        route_decision.execution_mode = "direct"
                    else:
                        try:
                            # 1. Create State Snapshot
                            snapshot = await self.snapshot_manager.create_snapshot(
                                user_id=user_id,
                                session_id=session_id,
                                db_session=active_db
                            )

                            # 2. Call LangGraph Planner
                            conversation_history = []
                            if conversation_context:
                                conversation_history = conversation_context.get("messages", [])

                            # Phase 4: Pass plan_id for version tracking
                            plan_id_str = str(plan_id) if plan_id else None

                            executable_plan = await self.lang_graph_planner.plan(
                                message=user_message,
                                snapshot=snapshot,
                                user_id=user_id,
                                session_id=session_id,
                                conversation_history=conversation_history,
                                plan_id=plan_id_str,  # Phase 4
                            )

                            # === Phase 3: Log planning observability ===
                            await self.observability.log_langgraph_plan(
                                user_id=user_id,
                                session_id=session_id,
                                plan_id=executable_plan.plan_id,
                                plan_data={
                                    "agents_involved": executable_plan.agents_involved,
                                    "collaboration_mode": executable_plan.collaboration_mode,
                                    "tool_calls_count": len(executable_plan.tool_calls),
                                    "confidence": executable_plan.confidence,
                                    "rationale": executable_plan.rationale
                                }
                            )

                            logger.info(
                                f"LangGraph plan generated: {len(executable_plan.tool_calls)} tool calls, "
                                f"confidence={executable_plan.confidence}, "
                                f"collaboration={executable_plan.collaboration_mode}, "
                                f"agents={executable_plan.agents_involved}"
                            )

                            # 3. Version Conflict Check
                            current_versions = await self._load_context_versions(user_id)
                            version_check = await self.snapshot_manager.compare_versions(
                                snapshot=snapshot,
                                current_versions=current_versions
                            )
                            replan_attempted = False

                            if version_check["has_conflict"]:
                                logger.warning(
                                    f"Version conflict detected: {version_check['conflicted_domains']}"
                                )

                                if executable_plan.fallback_strategy.get("on_version_conflict") == "replan":
                                    # P1: Check replan rate limit
                                    plan_uuid = uuid.UUID(plan_id_str) if plan_id_str else None
                                    user_uuid = uuid.UUID(user_id)

                                    if plan_uuid:
                                        can_replan, limit_reason, attempt_count = await self.version_conflict_service.can_replan(
                                            user_uuid, plan_uuid
                                        )

                                        if not can_replan:
                                            logger.warning(f"Replan rate limited: {limit_reason}")
                                            await stream_callback(agent_service_pb2.ChatResponse(
                                                delta=f"\n\n⚠️ {limit_reason}. 请稍后重试。",
                                                metadata={
                                                    "replan_blocked": "true",
                                                    "reason": limit_reason,
                                                    "attempt_count": str(attempt_count),
                                                }
                                            ))
                                            return

                                        # Record replan attempt
                                        await self.version_conflict_service.record_replan_attempt(user_uuid, plan_uuid)

                                    logger.info("Version conflict -> attempting replan with latest snapshot")
                                    replan_attempted = True
                                    snapshot = await self.snapshot_manager.create_snapshot(
                                        user_id=user_id,
                                        session_id=session_id,
                                        db_session=active_db
                                    )
                                    executable_plan = await self.lang_graph_planner.plan(
                                        message=user_message,
                                        snapshot=snapshot,
                                        user_id=user_id,
                                        session_id=session_id,
                                        conversation_history=conversation_history,
                                        plan_id=plan_id_str,  # Phase 4
                                    )
                                    current_versions = await self._load_context_versions(user_id)
                                    version_check = await self.snapshot_manager.compare_versions(
                                        snapshot=snapshot,
                                        current_versions=current_versions
                                    )

                                conflict_domains = set(version_check.get("conflicted_domains", []))
                                affected_domains = self._get_plan_affected_domains(executable_plan)

                                if affected_domains and conflict_domains.isdisjoint(affected_domains):
                                    logger.info(
                                        "Version conflict outside affected domains, proceeding without replan"
                                    )
                                elif executable_plan.confidence < 0.7 and not replan_attempted:
                                    # Low confidence + conflict → Discard plan
                                    await stream_callback(agent_service_pb2.ChatResponse(
                                        delta=f"\n\n⚠️ 检测到状态变化，计划已过期。请重试。"
                                    ))
                                    # === Phase 3: Log validation failure ===
                                    await self.observability.log_validation_failed(
                                        user_id=user_id,
                                        session_id=session_id,
                                        plan_id=executable_plan.plan_id,
                                        failure_reason="Version conflict with low confidence"
                                    )
                                    await self.langgraph_breaker.on_failure("version_conflict_low_confidence")
                                    return
                                elif version_check["has_conflict"]:
                                    # High confidence + conflict → HITL confirmation
                                    tool_calls_payload = [
                                        {
                                            "id": tc.id,
                                            "name": tc.name,
                                            "params": tc.params
                                        }
                                        for tc in executable_plan.tool_calls
                                    ]
                                    action_id = await pending_actions_store.save(
                                        tool_name="__plan__",
                                        arguments={
                                            "plan_id": executable_plan.plan_id,
                                            "snapshot_id": snapshot.snapshot_id if snapshot else None,
                                            "tool_calls": tool_calls_payload,
                                            "reason": "version_conflict",
                                            "conflicted_domains": list(conflict_domains)
                                        },
                                        user_id=str(user_id),
                                        description="检测到状态变更，是否继续执行该计划？",
                                        preview_data={
                                            "plan_id": executable_plan.plan_id,
                                            "conflicted_domains": list(conflict_domains),
                                            "affected_domains": list(affected_domains),
                                            "tool_calls": tool_calls_payload
                                        }
                                    )
                                    HITL_REQUESTED.labels(reason="version_conflict").inc()
                                    await stream_callback(agent_service_pb2.ChatResponse(
                                        delta=(
                                            "\n\n⚠️ 检测到状态变化，需要确认后继续执行。\n"
                                            f"action_id={action_id}"
                                        ),
                                        metadata={
                                            "requires_hitl": "true",
                                            "action_id": action_id,
                                            "reason": "version_conflict"
                                        }
                                    ))
                                    return

                            # 4. Grounding Validation
                            validation_result = await self.grounding_validator.validate_plan(
                                plan=executable_plan,
                                snapshot=snapshot
                            )

                            if not validation_result.is_valid:
                                await stream_callback(agent_service_pb2.ChatResponse(
                                    delta=f"\n\n⚠️ 计划验证失败: {validation_result.failure_reason}"
                                ))
                                # === Phase 3: Log validation failure ===
                                await self.observability.log_validation_failed(
                                    user_id=user_id,
                                    session_id=session_id,
                                    plan_id=executable_plan.plan_id,
                                    failure_reason=validation_result.failure_reason
                                )
                                await self.langgraph_breaker.on_failure("validation_failed")
                                return

                            # 5. Preflight Check
                            preflight = await self.grounding_validator.preflight_check(
                                plan=executable_plan,
                                user_id=user_id
                            )

                            if not preflight["is_ready"]:
                                await stream_callback(agent_service_pb2.ChatResponse(
                                    delta=f"\n\n⚠️ 服务暂时不可用: {', '.join(preflight['blocked_by'])}"
                                ))
                                await self.langgraph_breaker.on_failure("preflight_blocked")
                                return

                            # === Phase 4: Plan version conflict check before execution ===
                            if plan_id and hasattr(executable_plan, 'plan_version'):
                                from app.services.plan_state_service import PlanStateService
                                from app.services.plan_feedback_service import get_plan_feedback_service

                                plan_state_service = PlanStateService(active_db, self.redis)
                                feedback_service = get_plan_feedback_service(active_db, self.redis)

                                # Check rate limit first
                                rate_allowed, rate_count = await self._check_replan_rate_limit(plan_id)
                                if not rate_allowed:
                                    await stream_callback(agent_service_pb2.ChatResponse(
                                        delta=f"\n\n⚠️ 计划重规划过于频繁，请稍后再试。"
                                    ))
                                    return

                                # Retry loop for version conflict handling
                                version_conflict_logged = False
                                for replan_attempt in range(MAX_REPLAN_ATTEMPTS):
                                    current_state = await plan_state_service.get_plan_state(
                                        uuid.UUID(user_id), uuid.UUID(plan_id)
                                    )

                                    if not current_state or current_state.version == executable_plan.plan_version:
                                        # No conflict or no state, exit loop successfully
                                        break

                                    # Version conflict detected
                                    logger.warning(
                                        f"Plan version conflict (attempt {replan_attempt + 1}/{MAX_REPLAN_ATTEMPTS}): "
                                        f"planned v{executable_plan.plan_version} -> current v{current_state.version}"
                                    )

                                    # Log conflict feedback only once
                                    if not version_conflict_logged:
                                        await feedback_service.append_user_feedback(
                                            user_id=uuid.UUID(user_id),
                                            plan_id=uuid.UUID(plan_id),
                                            content=(
                                                f"Plan version conflict detected: "
                                                f"planned v{executable_plan.plan_version}, "
                                                f"current v{current_state.version}"
                                            ),
                                            decision="supplement",
                                            priority="high"
                                        )
                                        version_conflict_logged = True

                                    # Check if we've exhausted retries
                                    if replan_attempt >= MAX_REPLAN_ATTEMPTS - 1:
                                        # Max retries reached, require HITL
                                        tool_calls_payload = [
                                            {"id": tc.id, "name": tc.name, "params": tc.params}
                                            for tc in executable_plan.tool_calls
                                        ]
                                        action_id = await pending_actions_store.save(
                                            tool_name="__plan_version_conflict__",
                                            arguments={
                                                "plan_id": executable_plan.plan_id,
                                                "planned_version": executable_plan.plan_version,
                                                "current_version": current_state.version,
                                                "tool_calls": tool_calls_payload,
                                            },
                                            user_id=str(user_id),
                                            description=(
                                                f"计划版本持续变更，已重试 {MAX_REPLAN_ATTEMPTS} 次，"
                                                f"是否继续执行？"
                                            ),
                                            preview_data={
                                                "plan_id": executable_plan.plan_id,
                                                "planned_version": executable_plan.plan_version,
                                                "current_version": current_state.version,
                                                "confidence": executable_plan.confidence,
                                                "tool_calls": tool_calls_payload,
                                            }
                                        )
                                        HITL_REQUESTED.labels(reason="plan_version_conflict_max_retries").inc()
                                        await stream_callback(agent_service_pb2.ChatResponse(
                                            delta=(
                                                f"\n\n⚠️ 检测到持续状态变更，已重试 {MAX_REPLAN_ATTEMPTS} 次，"
                                                f"需要确认后继续执行。\naction_id={action_id}"
                                            ),
                                            metadata={
                                                "requires_hitl": "true",
                                                "action_id": action_id,
                                                "reason": "plan_version_conflict_max_retries",
                                            }
                                        ))
                                        return

                                    # Handle conflict based on confidence
                                    if executable_plan.confidence >= VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD:
                                        # High confidence: auto replan
                                        if replan_attempt == 0:
                                            await stream_callback(agent_service_pb2.ChatResponse(
                                                delta=f"\n\n⚠️ 检测到状态变更，正在重新规划..."
                                            ))

                                        # Create new snapshot and replan
                                        new_snapshot = await self.snapshot_manager.create_snapshot(
                                            user_id=user_id,
                                            session_id=session_id,
                                            db_session=active_db
                                        )
                                        executable_plan = await self.lang_graph_planner.replan(
                                            message=user_message,
                                            snapshot=new_snapshot,
                                            user_id=user_id,
                                            session_id=session_id,
                                            previous_plan=executable_plan,
                                            conflict_info={
                                                "has_conflict": True,
                                                "old_version": executable_plan.plan_version,
                                                "new_version": current_state.version,
                                            },
                                            plan_id=plan_id_str,
                                        )
                                        # Continue loop to verify new plan version
                                    else:
                                        # Low confidence: require HITL confirmation (no retry)
                                        tool_calls_payload = [
                                            {"id": tc.id, "name": tc.name, "params": tc.params}
                                            for tc in executable_plan.tool_calls
                                        ]
                                        action_id = await pending_actions_store.save(
                                            tool_name="__plan_version_conflict__",
                                            arguments={
                                                "plan_id": executable_plan.plan_id,
                                                "planned_version": executable_plan.plan_version,
                                                "current_version": current_state.version,
                                                "tool_calls": tool_calls_payload,
                                            },
                                            user_id=str(user_id),
                                            description=(
                                                f"计划版本已变更 (v{executable_plan.plan_version} -> v{current_state.version})，"
                                                f"是否继续执行？"
                                            ),
                                            preview_data={
                                                "plan_id": executable_plan.plan_id,
                                                "planned_version": executable_plan.plan_version,
                                                "current_version": current_state.version,
                                                "confidence": executable_plan.confidence,
                                                "tool_calls": tool_calls_payload,
                                            }
                                        )
                                        HITL_REQUESTED.labels(reason="plan_version_conflict_low_confidence").inc()
                                        await stream_callback(agent_service_pb2.ChatResponse(
                                            delta=(
                                                f"\n\n⚠️ 检测到状态变更，需要确认后继续执行。\n"
                                                f"action_id={action_id}"
                                            ),
                                            metadata={
                                                "requires_hitl": "true",
                                                "action_id": action_id,
                                                "reason": "plan_version_conflict",
                                            }
                                        ))
                                        return

                                # If we get here, version check passed (no conflict or resolved)
                                if version_conflict_logged:
                                    logger.info(f"Plan version conflict resolved for plan {plan_id}")

                            # 6. Plan Review (User Confirmation Loop)
                            if executable_plan and route_decision.execution_mode in ["langgraph", "hybrid"]:
                                review_result = await plan_review_service.review_plan(
                                    plan=executable_plan,
                                    user_message=user_message,
                                    user_context=user_context_payload or {}
                                )

                                # === Phase 4: Write review feedback to PlanScope (时机1: 审查完成后) ===
                                if plan_id:
                                    from app.services.plan_feedback_service import get_plan_feedback_service
                                    feedback_service = get_plan_feedback_service(active_db, self.redis)

                                    # 写入审查结果到 feedback_log
                                    await feedback_service.append_review_feedback(
                                        user_id=uuid.UUID(user_id),
                                        plan_id=uuid.UUID(plan_id),
                                        review_result=review_result,
                                        user_decision=None,  # 尚未确认
                                    )
                                    logger.info(f"Review feedback written for plan {plan_id}")

                                # Check if plan requires user action
                                if review_result.decision in [
                                    ReviewDecision.REJECTED.value,
                                    ReviewDecision.REQUIRES_CONFIRMATION.value,
                                    ReviewDecision.NEEDS_MODIFICATION.value
                                ]:
                                    action_id = await plan_review_service.store_review_result(
                                        review=review_result,
                                        user_id=str(user_id)
                                    )

                                    # Send review result to client
                                    review_metadata = {
                                        "requires_review": "true",
                                        "review_action_id": action_id,
                                        "review_decision": review_result.decision,
                                        "review_id": review_result.review_id,
                                        "plan_id": review_result.plan_id,
                                    }

                                    # Format review message for display
                                    review_delta = self._format_review_message(review_result)

                                    await stream_callback(agent_service_pb2.ChatResponse(
                                        delta=review_delta,
                                        metadata=review_metadata
                                    ))

                                    # Store review result in state for potential re-plan
                                    state.context_data["plan_review"] = review_result.to_dict()
                                    state.context_data["pending_review_action_id"] = action_id

                                    logger.info(
                                        f"Plan {executable_plan.plan_id} requires user review: "
                                        f"{review_result.decision} (action_id={action_id})"
                                    )
                                    return

                                # Auto-approved: continue with execution
                                state.context_data["plan_review"] = review_result.to_dict()
                                logger.info(
                                    f"Plan {executable_plan.plan_id} auto-approved: "
                                    f"confidence={review_result.confidence}"
                                )

                            # 7. Store plan in state for execution
                            state.context_data["executable_plan"] = executable_plan
                            state.context_data["snapshot"] = snapshot

                            # === Phase 3: Record success for circuit breaker (plan accepted) ===
                            await self.langgraph_breaker.on_success()

                            # Log plan summary
                            plan_summary = self.lang_graph_planner.get_plan_summary(executable_plan)
                            logger.info(f"Plan ready for execution: {plan_summary}")

                            # === Phase 3: Log collaboration start if multi-agent ===
                            if executable_plan.collaboration_mode != "single":
                                await self.observability.log_collaboration_start(
                                    user_id=user_id,
                                    session_id=session_id,
                                    agents=executable_plan.agents_involved,
                                    mode=executable_plan.collaboration_mode
                                )

                            # === Phase 3: Shadow Mode Prediction (parallel, non-blocking) ===
                            asyncio.create_task(
                                self.shadow_predictor.predict_and_record(
                                    user_message=user_message,
                                    user_id=user_id,
                                    session_id=session_id,
                                    actual_decision=route_decision,
                                    actual_plan=executable_plan
                                )
                            )

                        except Exception as e:
                            logger.error(f"LangGraph planning error: {e}", exc_info=True)
                            # === Phase 3: Record failure for circuit breaker ===
                            await self.langgraph_breaker.on_failure(str(e))
                            # Fall back to direct mode
                            await stream_callback(agent_service_pb2.ChatResponse(
                                delta=f"\n\n⚠️ 规划失败，使用直接模式: {str(e)}"
                            ))
                            # Reset to direct mode
                            route_decision.execution_mode = "direct"

                # === Phase 3: Log route decision (after potential mode change) ===
                await self.observability.log_route_decision(
                    user_id=user_id,
                    session_id=session_id,
                    message=user_message,
                    decision={
                        "execution_mode": route_decision.execution_mode,
                        "risk_level": route_decision.risk_level,
                        "reason": route_decision.reason,
                        "intent": route_decision.reason.split(":")[0] if ":" in route_decision.reason else "unknown"
                    }
                )

                # ===========================================

                # Launch Graph Execution in Background (Managed)
                logger.info("🚀 Launching StateGraph Execution")
                
                with tracer.start_as_current_span("agent_graph.invoke"):
                    graph_task = await task_manager.spawn(
                        self.graph.invoke(state),
                        task_name="orchestrator_graph",
                        user_id=str(user_id)
                    )
                    
                    # Stream from queue
                    while not graph_task.done() or not queue.empty():
                        try:
                            # Wait for next item with timeout to check task status
                            item = await asyncio.wait_for(queue.get(), timeout=0.1)
                            
                            # Track token usage if present
                            if item.HasField("usage"):
                                total_prompt_tokens = item.usage.prompt_tokens
                                total_completion_tokens = item.usage.completion_tokens
                                # Also track to Prometheus immediately
                                if self.token_tracker:
                                    TOKEN_USAGE.labels(model="gpt-4", type="prompt").inc(total_prompt_tokens)
                                    TOKEN_USAGE.labels(model="gpt-4", type="completion").inc(total_completion_tokens)

                            yield item
                            queue.task_done()
                        except asyncio.TimeoutError:
                            if graph_task.done():
                                break
            
                # Check for exceptions
                if graph_task.done():
                    exc = graph_task.exception()
                    if exc:
                        raise exc
                    
                    # Get final state
                    final_state = graph_task.result()
                    
                    # Get full response from state history
                    full_response = ""
                    # Find the last assistant message
                    for msg in reversed(final_state.messages):
                        if msg["role"] == "assistant":
                            full_response = msg["content"]
                            break
                    
                    # Compose Final Response (Idempotency Cache)
                    # Note: Tool results are already in history, but ResponseComposer might need them separate.
                    # For now, we trust full_response is sufficient or we can extract from context.
                    
                    llm_profile_meta = {}
                    if isinstance(user_context_payload, dict):
                        llm_profile_meta = user_context_payload.get("llm_profile") or {}
                        if not isinstance(llm_profile_meta, dict):
                            llm_profile_meta = {}

                    # Build metadata with plan switch notification
                    response_metadata = {
                        "response_id": response_id,
                        "trace_id": trace_id,
                        "preference_version": (user_context_payload or {}).get("preference_version", 0),
                        "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
                    }

                    # P0: Add plan switch notification to metadata
                    if plan_switched and plan_id:
                        response_metadata["plan_switched"] = True
                        response_metadata["switched_to_plan_id"] = str(plan_id)
                        logger.info(f"Plan switch notification added to response: plan_id={plan_id}")

                    final_response_data = {
                        "message": full_response,
                        "tool_results": [],
                        "metadata": response_metadata,
                    }
                    try:
                        from app.services.decision_record_service import DecisionRecordService

                        decision_service = DecisionRecordService(self.db_session)
                        await decision_service.record_decision(
                            user_id=uuid.UUID(str(user_id)),
                            module="ai",
                            action="generate_response",
                            preference_version=(user_context_payload or {}).get("preference_version", 0),
                            preferences_snapshot={
                                "verbosity": llm_profile_meta.get("verbosity_target"),
                                "temperature": llm_profile_meta.get("temperature"),
                                "tone": llm_profile_meta.get("tone"),
                            },
                            outcome=f"Generated response with {len(full_response)} chars",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record decision: {e}")
                    with tracer.start_as_current_span("orchestrator.cache_response"):
                        await self._cache_response(session_id, request_id, final_response_data)
                    
                    # Yield final full_text if not already streamed complete?
                    # Actually, standard_workflow streams delta. Client might need full_text signal.
                    for update_resp in await self._emit_system_updates(user_id):
                        yield update_resp

                    yield agent_service_pb2.ChatResponse(
                        response_id=response_id,
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        prompt_version=prompt_version,
                        metadata={str(k): str(v) for k, v in final_response_data.get("metadata", {}).items()},
                        full_text=full_response,
                        finish_reason=agent_service_pb2.STOP
                    )

                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="success").inc()
                
                COLLABORATION_SUCCESS.labels(
                    workflow_type="standard_chat",
                    agents_used="orchestrator",
                    outcome="success"
                ).inc()

            except Exception as e:
                REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="error").inc()
                
                COLLABORATION_SUCCESS.labels(
                    workflow_type="standard_chat",
                    agents_used="orchestrator",
                    outcome="error"
                ).inc()
                logger.error(f"Orchestration Error: {e}", exc_info=True)
                await self._update_state(session_id, STATE_FAILED, str(e))
                yield agent_service_pb2.ChatResponse(
                    response_id=response_id,
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    error=agent_service_pb2.Error(
                        code="INTERNAL_ERROR",
                        message=str(e),
                        retryable=True
                    ),
                    finish_reason=agent_service_pb2.ERROR
                )
            
            finally:
                ACTIVE_SESSIONS.dec()
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module="orchestration", method="process_stream").observe(latency)
                COLLABORATION_LATENCY.labels(workflow_type="standard_chat").observe(latency)
                
                # Always release lock
                await self._release_session_lock(session_id, request_id)

                # Record token usage (async, non-blocking)
                if self.token_tracker and total_prompt_tokens > 0:
                    try:
                        # Estimate cost
                        estimated_cost = await self.token_tracker.estimate_cost(
                            prompt_tokens=total_prompt_tokens,
                            completion_tokens=total_completion_tokens,
                            model="gpt-4"
                        )

                        # Record usage (async - managed)
                        await task_manager.spawn(
                            self.token_tracker.record_usage(
                                user_id=user_id,
                                session_id=session_id,
                                request_id=request_id,
                                prompt_tokens=total_prompt_tokens,
                                completion_tokens=total_completion_tokens,
                                model="gpt-4",
                                cost=estimated_cost
                            ),
                            task_name="token_usage_record",
                            user_id=str(user_id)
                        )

                        logger.info(
                            f"Token usage recorded for user {user_id}: "
                            f"{total_prompt_tokens} + {total_completion_tokens} = "
                            f"{total_prompt_tokens + total_completion_tokens} tokens, "
                            f"est. cost: ${estimated_cost:.6f}"
                        )

                    except Exception as e:
                        logger.error(f"Failed to record token usage: {e}")

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
