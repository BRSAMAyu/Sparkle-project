import json
import asyncio
import time
from typing import AsyncGenerator, List, Dict, Optional, Any
from loguru import logger
from datetime import datetime
import uuid

from google.protobuf.json_format import MessageToDict

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import llm_service
from app.services.knowledge_service import KnowledgeService
from app.services.galaxy_service import GalaxyService
from app.services.user_service import UserService
from app.services.focus_service import focus_service
from app.models.task import Task, TaskStatus as ModelTaskStatus
from app.models.plan import Plan
from sqlalchemy import select, and_, desc, asc
from app.orchestration.prompts import build_system_prompt
from app.orchestration.executor import ToolExecutor
from app.orchestration.state_manager import SessionStateManager, FSMState
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.validator import RequestValidator, ValidationResult
from app.orchestration.composer import ResponseComposer
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.token_tracker import TokenTracker
from app.gen.agent.v1 import agent_service_pb2
from app.config import settings
from app.core.metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, TOKEN_USAGE, TOOL_EXECUTION_COUNT, ACTIVE_SESSIONS
)
from app.core.business_metrics import COLLABORATION_SUCCESS, COLLABORATION_LATENCY
from app.orchestration.statechart_engine import WorkflowState, StateGraph
from app.agents.standard_workflow import create_standard_chat_graph
from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.core.task_manager import task_manager
from app.core.celery_app import schedule_long_task

# FSM States
STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"


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

    def __init__(self, db_session: Optional[AsyncSession] = None, redis_client=None):
        if redis_client is None:
            logger.error("ChatOrchestrator requires Redis, but no redis_client was provided")
            raise ValueError("Redis client is required for ChatOrchestrator")
        self.db_session = db_session
        self.redis = redis_client

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

        # Ensure tools are registered
        self._ensure_tools_registered()

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

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Build comprehensive user context from UserService

        Returns:
            Dict containing user context and analytics
        """
        try:
            # Pass redis_client to UserService for caching
            user_service = UserService(db_session, self.redis)

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
                user_context_data = {
                    "preferences": cognitive_context.preferences,
                    # Add other fields if needed by legacy prompt
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
                
                return {
                    "user_context": user_context_data, # Legacy field
                    "analytics_summary": cognitive_context.engagement_metrics,
                    "preferences": cognitive_context.preferences,
                    "next_actions": cognitive_context.active_tasks,
                    "active_plans": active_plans,
                    "focus_stats": cognitive_context.focus_stats,
                    
                    # New field for full context injection
                    "cognitive_context": cognitive_context.model_dump(exclude={'user_id', 'timestamp'})
                }
            
            # Fallback to legacy logic if new orchestrator returns None (shouldn't happen)
            logger.warning(f"ContextOrchestrator returned None for {user_id}, falling back to legacy")
            
            # ... Legacy Logic ...
            user_context = await user_service.get_context(uuid.UUID(user_id))
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
                }

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            # Fallback
            return {
                "user_context": None,
                "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5}
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
        start_time = time.time()
        ACTIVE_SESSIONS.inc()
        request_id = request.request_id
        session_id = request.session_id
        user_id = request.user_id
        
        # Use provided session or instance session
        active_db = db_session or self.db_session
        
        # Step 0: Request Validation (with quota check)
        if self.validator:
            validation_result = await self.validator.validate_chat_request(request)
            if not validation_result.is_valid:
                logger.error(f"Validation failed: {validation_result.error_message}")
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{uuid.uuid4()}",
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
        cached_response = await self._check_idempotency(session_id, request_id)
        if cached_response:
            logger.info(f"Cache hit for session {session_id}, request {request_id}")
            # Return cached response
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                full_text=cached_response.get("full_text", ""),
                finish_reason=agent_service_pb2.STOP
            )
            return

        # Step 2: Acquire Distributed Lock
        lock_acquired = await self._acquire_session_lock(session_id, request_id)
        if not lock_acquired:
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
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

            user_message = ""
            if request.HasField("message"):
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

            user_context_payload = None
            conversation_context = None
            if active_db and user_id:
                local_context = await self._build_user_context(user_id, active_db)
                # P0: Merge contexts - prioritize gRPC context (more recent) over local context
                user_context_payload = self._merge_user_contexts(local_context, grpc_context)
                logger.info(f"Merged user context: {user_context_payload is not None}")
            elif grpc_context:
                # If no DB session but have gRPC context, use it
                user_context_payload = grpc_context
                logger.info("Using gRPC context without local DB context")

            self._log_context_injection(user_id, user_context_payload)

            if self.context_pruner:
                conversation_context = await self._build_conversation_context(session_id, user_id)

            # Prepare initial state
            state = WorkflowState()
            state.append_message("user", user_message)
            
            # Get tools
            tools = await self._get_tools_schema()
            
            # Prepare queue for streaming
            queue = asyncio.Queue()
            
            async def stream_callback(resp: agent_service_pb2.ChatResponse):
                # Augment response with IDs
                if not resp.response_id:
                    resp.response_id = f"resp_{uuid.uuid4()}"
                resp.created_at = int(datetime.now().timestamp())
                resp.request_id = request_id
                await queue.put(resp)

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
                "file_ids": list(request.file_ids),
                "include_references": bool(request.include_references),
            })

            # Launch Graph Execution in Background (Managed)
            logger.info("🚀 Launching StateGraph Execution")
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
                
                final_response_data = {
                    "message": full_response,
                    "tool_results": [] 
                }
                await self._cache_response(session_id, request_id, final_response_data)
                
                # Yield final full_text if not already streamed complete?
                # Actually, standard_workflow streams delta. Client might need full_text signal.
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{uuid.uuid4()}",
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
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
                response_id=f"resp_{uuid.uuid4()}",
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
