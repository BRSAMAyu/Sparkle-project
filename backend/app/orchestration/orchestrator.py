import json
import asyncio
import time
from typing import AsyncGenerator, List, Dict, Optional, Any
from loguru import logger
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import llm_service
from app.services.knowledge_service import KnowledgeService
from app.services.galaxy_service import GalaxyService
from app.services.user_service import UserService
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
from app.orchestration.statechart_engine import WorkflowState, StateGraph
from app.agents.standard_workflow import create_standard_chat_graph
from app.checkpoint.redis_checkpointer import RedisCheckpointer

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
    if any(keyword in tool_lower for keyword in ['task', 'plan', 'create', 'update', 'batch', 'orchestrate']):
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
        self.db_session = db_session
        self.redis = redis_client

        # Initialize components
        self.state_manager = SessionStateManager(redis_client) if redis_client else None
        self.validator = RequestValidator(redis_client, daily_quota=100000) if redis_client else None
        self.tool_executor = ToolExecutor()
        self.response_composer = ResponseComposer()

        # Initialize ContextPruner (P0 feature)
        self.context_pruner = None
        self.token_tracker = None
        if redis_client:
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
        if redis_client:  # Only log if initialized
            logger.info("ChatOrchestrator initialized with all components")

        # Ensure tools are registered
        self._ensure_tools_registered()

        # Initialize State Graph
        self.graph = create_standard_chat_graph()
        
        # Connect Checkpointer
        if redis_client:
            self.graph.checkpointer = RedisCheckpointer(redis_client)

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

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Build comprehensive user context from UserService

        Returns:
            Dict containing user context and analytics
        """
        try:
            # Pass redis_client to UserService for caching
            user_service = UserService(db_session, self.redis)

            # Get user context for LLM (with Redis caching)
            user_context = await user_service.get_context(uuid.UUID(user_id))

            # Get analytics summary (with Redis caching)
            analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

            if user_context:
                return {
                    "user_context": user_context,
                    "analytics_summary": analytics,
                    "preferences": {
                        "depth_preference": user_context.preferences.get("depth_preference", 0.5),
                        "curiosity_preference": user_context.preferences.get("curiosity_preference", 0.5),
                    }
                }
            else:
                # Fallback to basic context
                logger.warning(f"User {user_id} not found, using fallback context")
                return {
                    "user_context": None,
                    "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                    "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5}
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
                "tools_schema": tools
            })

            # Launch Graph Execution in Background
            logger.info("🚀 Launching StateGraph Execution")
            graph_task = asyncio.create_task(self.graph.invoke(state))
            
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

        except Exception as e:
            REQUEST_COUNT.labels(module="orchestration", method="process_stream", status="error").inc()
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

                    # Record usage (async)
                    asyncio.create_task(
                        self.token_tracker.record_usage(
                            user_id=user_id,
                            session_id=session_id,
                            request_id=request_id,
                            prompt_tokens=total_prompt_tokens,
                            completion_tokens=total_completion_tokens,
                            model="gpt-4",
                            cost=estimated_cost
                        )
                    )

                    logger.info(
                        f"Token usage recorded for user {user_id}: "
                        f"{total_prompt_tokens} + {total_completion_tokens} = "
                        f"{total_prompt_tokens + total_completion_tokens} tokens, "
                        f"est. cost: ${estimated_cost:.6f}"
                    )

                except Exception as e:
                    logger.error(f"Failed to record token usage: {e}")
