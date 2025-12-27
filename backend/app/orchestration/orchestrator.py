import json
import asyncio
from typing import AsyncGenerator, List, Dict, Optional, Any
from loguru import logger
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm_service import llm_service
from app.services.knowledge_service import KnowledgeService
from app.services.graph_knowledge_service import GraphKnowledgeService
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

# FSM States
STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"


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
        context_data: Dict[str, Any] = None
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        Process the incoming chat request with enhanced features
        """
        request_id = request.request_id
        session_id = request.session_id
        user_id = request.user_id
        
        # Use provided session or instance session
        active_db = db_session or self.db_session
        
        # Step 0: Request Validation (with quota check)
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

        try:
            # Step 3: Initialize State
            await self._update_state(session_id, STATE_INIT, f"Request {request_id}")
            
            # Update state with request info
            if self.state_manager:
                await self.state_manager.update_state(
                    session_id=session_id,
                    state=STATE_INIT,
                    details=f"Processing request {request_id}",
                    request_id=request_id,
                    user_id=user_id
                )

            # Step 4: Input Processing
            user_message = ""
            if request.HasField("message"):
                user_message = request.message
            elif request.HasField("tool_result"):
                tool_result = request.tool_result
                user_message = f"Tool '{tool_result.tool_name}' execution result: {tool_result.result_json}"

            # Step 5: Build User Context
            await self._update_state(session_id, STATE_THINKING, "Building user context...")
            user_context_data = await self._build_user_context(user_id, active_db)

            # Step 6: Build Conversation Context with ContextPruner (NEW!)
            await self._update_state(session_id, STATE_THINKING, "Pruning conversation history...")
            conversation_context = await self._build_conversation_context(session_id, user_id)

            # Step 7: GraphRAG Retrieval (Enhanced with graph database)
            await self._update_state(session_id, STATE_THINKING, "Retrieving relevant knowledge...")
            knowledge_context = ""
            if active_db and user_id:
                try:
                    # Use GraphKnowledgeService for enhanced GraphRAG
                    graph_ks = GraphKnowledgeService(active_db)
                    rag_result = await graph_ks.graph_rag_search(
                        query=user_message,
                        user_id=uuid.UUID(user_id),
                        depth=2,
                        top_k=5
                    )
                    knowledge_context = rag_result.get("context", "")

                    # Log GraphRAG metrics
                    if rag_result.get("metadata"):
                        logger.info(
                            f"GraphRAG results: "
                            f"vector={rag_result['metadata'].get('vector_count', 0)}, "
                            f"graph={rag_result['metadata'].get('graph_count', 0)}, "
                            f"fused={rag_result['metadata'].get('fusion_count', 0)}"
                        )
                except Exception as e:
                    logger.warning(f"GraphRAG retrieval failed: {e}, falling back to vector search")
                    # Fallback to regular KnowledgeService
                    try:
                        ks = KnowledgeService(active_db)
                        knowledge_context = await ks.retrieve_context(
                            user_id=uuid.UUID(user_id),
                            query=user_message
                        )
                    except Exception as e2:
                        logger.error(f"Fallback knowledge retrieval also failed: {e2}")

            # Step 8: Build Prompt with ContextPruner
            await self._update_state(session_id, STATE_THINKING, "Building system prompt...")

            # Use real user context + pruned conversation history
            base_system_prompt = build_system_prompt(
                user_context_data,
                conversation_history=conversation_context  # 传递修剪后的历史
            )

            full_system_prompt = base_system_prompt
            if knowledge_context:
                full_system_prompt += f"\n\n## 检索到的知识背景\n{knowledge_context}"

            # Yield Thinking Status
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details="Analyzing your request and preparing response..."
                )
            )

            # Step 8: LLM Generation with Dynamic Tools
            await self._update_state(session_id, STATE_GENERATING)
            
            # Get tools from dynamic registry (NO MORE HARD-CODING!)
            tools = await self._get_tools_schema()
            
            if not tools:
                logger.warning("No tools available from registry")

            full_response = ""
            tool_execution_results = []
            total_prompt_tokens = 0
            total_completion_tokens = 0

            # Call LLM Service
            async for chunk in llm_service.chat_stream_with_tools(
                system_prompt=full_system_prompt,
                user_message=user_message,
                tools=tools
            ):
                # Map StreamChunk to ChatResponse
                if chunk.type == "text":
                    full_response += chunk.content
                    yield agent_service_pb2.ChatResponse(
                        response_id=f"resp_{uuid.uuid4()}",
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        delta=chunk.content
                    )

                elif chunk.type == "tool_call_end":
                    # Tool call is ready
                    await self._update_state(session_id, STATE_TOOL_CALLING, f"Calling {chunk.tool_name}...")

                    yield agent_service_pb2.ChatResponse(
                        response_id=f"resp_{uuid.uuid4()}",
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        status_update=agent_service_pb2.AgentStatus(
                            state=agent_service_pb2.AgentStatus.TOOL_CALLING,
                            details=f"Executing {chunk.tool_name}..."
                        ),
                        tool_call=agent_service_pb2.ToolCall(
                            id=chunk.tool_call_id,
                            name=chunk.tool_name,
                            arguments=json.dumps(chunk.full_arguments)
                        )
                    )

                # Collect token usage
                elif chunk.type == "usage" and self.token_tracker:
                    total_prompt_tokens = chunk.prompt_tokens or 0
                    total_completion_tokens = chunk.completion_tokens or 0

                    # Send usage info to client
                    yield agent_service_pb2.ChatResponse(
                        response_id=f"resp_{uuid.uuid4()}",
                        created_at=int(datetime.now().timestamp()),
                        request_id=request_id,
                        usage=agent_service_pb2.Usage(
                            prompt_tokens=total_prompt_tokens,
                            completion_tokens=total_completion_tokens,
                            total_tokens=total_prompt_tokens + total_completion_tokens
                        )
                    )

            # Step 9: Compose Final Response
            await self._update_state(session_id, STATE_DONE, "Composing response...")
            
            # Use ResponseComposer to build unified response
            final_response_data = self.response_composer.compose_response(
                llm_text=full_response,
                tool_results=tool_execution_results,
                requires_confirmation=False,
                confirmation_data=None
            )

            # Cache response for idempotency
            await self._cache_response(session_id, request_id, final_response_data)

            # Yield final response
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                full_text=final_response_data.get("message", full_response),
                finish_reason=agent_service_pb2.STOP
            )

        except Exception as e:
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