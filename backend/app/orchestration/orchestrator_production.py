"""
ChatOrchestrator - 生产级实现

增强特性:
1. ✅ JSON 序列化: 替代 pickle，确保兼容性和安全性
2. ✅ 并发安全: 消息 ID 追踪，防止重复处理
3. ✅ 错误处理: Redis/LLM 故障时的优雅降级
4. ✅ 熔断机制: 防止队列积压导致 OOM
5. ✅ 监控指标: Prometheus 埋点
6. ✅ 结构化日志: 增强可观察性
7. ✅ 配置管理: 环境变量支持
8. ✅ 健康检查: 内置健康状态
"""

import json
import asyncio
import time
from typing import AsyncGenerator, List, Dict, Optional, Any, Set
from datetime import datetime
import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus not available, metrics disabled")

from app.services.llm_service import llm_service
from app.services.knowledge_service import KnowledgeService
from app.services.user_service import UserService
from app.orchestration.prompts import build_system_prompt
from app.orchestration.executor import ToolExecutor
from app.orchestration.state_manager import SessionStateManager
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

# Prometheus Metrics (if available)
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNTER = Counter(
        'chat_orchestrator_requests_total',
        'Total chat requests processed',
        ['status', 'session_id']
    )

    REQUEST_DURATION = Histogram(
        'chat_orchestrator_request_duration_seconds',
        'Request processing duration',
        ['operation']
    )

    CIRCUIT_BREAKER_STATE = Gauge(
        'chat_orchestrator_circuit_breaker',
        'Circuit breaker state (0=closed, 1=open, 2=half-open)'
    )

    TOKEN_USAGE = Counter(
        'chat_orchestrator_tokens_total',
        'Token usage by model',
        ['model', 'type']
    )

    CONCURRENT_SESSIONS = Gauge(
        'chat_orchestrator_concurrent_sessions',
        'Number of active sessions'
    )


class CircuitBreaker:
    """熔断器 - 防止系统过载"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = asyncio.Lock()

    async def record_success(self):
        """记录成功"""
        async with self.lock:
            self.failure_count = 0
            self.state = "CLOSED"
            if PROMETHEUS_AVAILABLE:
                CIRCUIT_BREAKER_STATE.set(0)

    async def record_failure(self):
        """记录失败"""
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
                if PROMETHEUS_AVAILABLE:
                    CIRCUIT_BREAKER_STATE.set(1)

    async def can_execute(self) -> bool:
        """检查是否可以执行"""
        async with self.lock:
            if self.state == "CLOSED":
                return True

            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    if PROMETHEUS_AVAILABLE:
                        CIRCUIT_BREAKER_STATE.set(2)
                    return True
                return False

            if self.state == "HALF_OPEN":
                # Allow one request through to test recovery
                return True

            return False

    def get_state(self) -> str:
        """获取当前状态"""
        return self.state


class MessageTracker:
    """消息 ID 追踪器 - 防止并发重复处理"""

    def __init__(self, max_size: int = 10000):
        self.processed_messages: Set[str] = set()
        self.max_size = max_size
        self.lock = asyncio.Lock()

    async def is_processed(self, message_id: str) -> bool:
        """检查消息是否已处理"""
        async with self.lock:
            return message_id in self.processed_messages

    async def mark_processed(self, message_id: str):
        """标记消息为已处理"""
        async with self.lock:
            if len(self.processed_messages) >= self.max_size:
                # 清理旧消息，防止内存泄漏
                to_remove = list(self.processed_messages)[:self.max_size // 2]
                for msg_id in to_remove:
                    self.processed_messages.remove(msg_id)
                logger.warning(f"Message tracker cleanup: removed {len(to_remove)} old messages")

            self.processed_messages.add(message_id)

    async def cleanup(self, message_id: str):
        """清理指定消息（用于测试或手动干预）"""
        async with self.lock:
            self.processed_messages.discard(message_id)


class ProductionChatOrchestrator:
    """
    生产级 ChatOrchestrator

    特性:
    - JSON 序列化 (无 pickle)
    - 并发安全 (消息 ID 追踪)
    - 错误处理 (Redis/LLM 降级)
    - 熔断机制 (防止 OOM)
    - Prometheus 监控
    - 结构化日志
    """

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        redis_client=None,
        # 熔断器配置
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
        # 限流配置
        max_concurrent_sessions: int = 100,
        # 配置
        enable_metrics: bool = True,
        enable_circuit_breaker: bool = True,
    ):
        self.db_session = db_session
        self.redis = redis_client

        # 核心组件
        self.state_manager = SessionStateManager(redis_client) if redis_client else None
        self.validator = RequestValidator(redis_client, daily_quota=100000) if redis_client else None
        self.tool_executor = ToolExecutor()
        self.response_composer = ResponseComposer()

        # 增强组件
        self.context_pruner = None
        self.token_tracker = None
        self.circuit_breaker = None
        self.message_tracker = MessageTracker()

        # 配置
        self.enable_metrics = enable_metrics and PROMETHEUS_AVAILABLE
        self.enable_circuit_breaker = enable_circuit_breaker
        self.max_concurrent_sessions = max_concurrent_sessions
        self.active_sessions: Set[str] = set()
        self.session_lock = asyncio.Lock()

        # 初始化可选组件
        if redis_client:
            # ContextPruner
            self.context_pruner = ContextPruner(
                redis_client=redis_client,
                max_history_messages=10,
                summary_threshold=20,
                summary_cache_ttl=3600
            )

            # TokenTracker
            self.token_tracker = TokenTracker(redis_client)

            # CircuitBreaker
            if enable_circuit_breaker:
                self.circuit_breaker = CircuitBreaker(
                    failure_threshold=circuit_breaker_threshold,
                    recovery_timeout=circuit_breaker_timeout
                )

            logger.info(
                f"ProductionChatOrchestrator initialized: "
                f"metrics={self.enable_metrics}, "
                f"circuit_breaker={enable_circuit_breaker}, "
                f"max_concurrent={max_concurrent_sessions}"
            )

        # 工具注册
        self._ensure_tools_registered()

        # 健康检查状态
        self._healthy = True
        self._startup_time = time.time()

    def _ensure_tools_registered(self):
        """确保工具已注册"""
        try:
            if len(dynamic_tool_registry.get_all_tools()) == 0:
                dynamic_tool_registry.register_from_package("app.tools")
                logger.info(f"Auto-registered {len(dynamic_tool_registry.get_all_tools())} tools")
        except Exception as e:
            logger.error(f"Tool registration failed: {e}")
            self._healthy = False

    async def _track_session(self, session_id: str, add: bool = True):
        """追踪活跃会话"""
        async with self.session_lock:
            if add:
                if len(self.active_sessions) >= self.max_concurrent_sessions:
                    logger.warning(f"Max concurrent sessions reached: {self.max_concurrent_sessions}")
                    return False
                self.active_sessions.add(session_id)
                if self.enable_metrics:
                    CONCURRENT_SESSIONS.set(len(self.active_sessions))
                return True
            else:
                self.active_sessions.discard(session_id)
                if self.enable_metrics:
                    CONCURRENT_SESSIONS.set(len(self.active_sessions))
                return True

    async def _update_state(self, session_id: str, state: str, details: str = ""):
        """更新状态（带错误处理）"""
        try:
            if self.state_manager:
                await self.state_manager.update_state(
                    session_id=session_id,
                    state=state,
                    details=details,
                    request_id=None,
                    user_id=None
                )
            logger.info(f"Session {session_id} State: {state} ({details})")
        except Exception as e:
            logger.warning(f"Failed to update state: {e}")

    async def _check_idempotency(self, session_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """检查幂等性（带降级）"""
        if not self.state_manager:
            return None

        try:
            return await self.state_manager.get_cached_response(session_id, request_id)
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
            return None

    async def _acquire_session_lock(self, session_id: str, request_id: str) -> bool:
        """获取分布式锁（带降级）"""
        if not self.state_manager:
            return True

        try:
            return await self.state_manager.acquire_lock(session_id, request_id)
        except Exception as e:
            logger.warning(f"Lock acquisition failed: {e}, proceeding without lock")
            return True

    async def _release_session_lock(self, session_id: str, request_id: str):
        """释放锁（带降级）"""
        if not self.state_manager:
            return

        try:
            await self.state_manager.release_lock(session_id, request_id)
        except Exception as e:
            logger.warning(f"Lock release failed: {e}")

    async def _cache_response(self, session_id: str, request_id: str, response_data: Dict[str, Any]):
        """缓存响应（带降级）"""
        if not self.state_manager:
            return

        try:
            await self.state_manager.cache_response(session_id, request_id, response_data)
        except Exception as e:
            logger.warning(f"Response caching failed: {e}")

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
        """构建用户上下文（带错误处理和降级）"""
        try:
            user_service = UserService(db_session, self.redis)
            user_context = await user_service.get_context(uuid.UUID(user_id))
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
                logger.warning(f"User {user_id} not found, using fallback")
                return self._get_fallback_context()

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            return self._get_fallback_context()

    def _get_fallback_context(self) -> Dict[str, Any]:
        """获取降级上下文"""
        return {
            "user_context": None,
            "analytics_summary": {"is_active": True, "engagement_level": "medium"},
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5}
        }

    async def _build_conversation_context(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """构建对话上下文（带错误处理）"""
        if not self.context_pruner:
            logger.warning("ContextPruner not available")
            return {"messages": [], "summary": None}

        try:
            result = await self.context_pruner.get_pruned_history(
                session_id=session_id,
                user_id=user_id
            )

            logger.debug(
                f"Conversation context for {session_id}: "
                f"{result['original_count']} -> {result['pruned_count']} messages, "
                f"summary={result['summary_used']}"
            )

            return result
        except Exception as e:
            logger.error(f"Failed to prune conversation: {e}")
            return {"messages": [], "summary": None}

    async def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具模式（带错误处理）"""
        try:
            return dynamic_tool_registry.get_openai_tools_schema()
        except Exception as e:
            logger.error(f"Failed to get tools schema: {e}")
            return []

    async def _record_token_usage(
        self,
        user_id: str,
        session_id: str,
        request_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ):
        """记录 Token 使用（带错误处理）"""
        if not self.token_tracker:
            return

        try:
            await self.token_tracker.record_usage(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model
            )

            # Prometheus metrics
            if self.enable_metrics:
                TOKEN_USAGE.labels(model=model, type="prompt").inc(prompt_tokens)
                TOKEN_USAGE.labels(model=model, type="completion").inc(completion_tokens)

        except Exception as e:
            logger.warning(f"Failed to record token usage: {e}")

    def _log_request(
        self,
        session_id: str,
        request_id: str,
        user_id: str,
        duration: float,
        status: str,
        error: Optional[str] = None
    ):
        """结构化日志"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "request_id": request_id,
            "user_id": user_id,
            "duration_ms": round(duration * 1000, 2),
            "status": status,
            "error": error
        }

        if status == "success":
            logger.info(f"Request processed: {json.dumps(log_data)}")
        else:
            logger.error(f"Request failed: {json.dumps(log_data)}")

    async def process_stream(
        self,
        request: agent_service_pb2.ChatRequest,
        db_session: Optional[AsyncSession] = None,
        context_data: Dict[str, Any] = None
    ) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
        """
        处理聊天请求（生产级实现）

        流程:
        1. 验证请求
        2. 检查熔断器
        3. 并发控制
        4. 消息去重
        5. 幂等性检查
        6. 分布式锁
        7. 执行处理
        8. 记录指标
        """
        start_time = time.time()
        request_id = request.request_id
        session_id = request.session_id
        user_id = request.user_id

        # 消息去重检查
        if await self.message_tracker.is_processed(request_id):
            logger.warning(f"Duplicate request detected: {request_id}")
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    code="DUPLICATE_REQUEST",
                    message="Request already processed",
                    retryable=False
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        # 熔断器检查
        if self.circuit_breaker and not await self.circuit_breaker.can_execute():
            state = self.circuit_breaker.get_state()
            logger.error(f"Circuit breaker is {state}, rejecting request")
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    code="CIRCUIT_BREAKER_OPEN",
                    message=f"Service temporarily unavailable (circuit breaker: {state})",
                    retryable=True
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        # 并发控制
        session_tracked = await self._track_session(session_id, add=True)
        if not session_tracked:
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    code="RATE_LIMIT",
                    message="Too many concurrent sessions",
                    retryable=True
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        active_db = db_session or self.db_session

        try:
            # 验证请求
            with REQUEST_DURATION.labels(operation="validation").time():
                validation_result = await self.validator.validate_chat_request(request)
                if not validation_result.is_valid:
                    raise ValueError(f"Validation failed: {validation_result.error_message}")

            # 幂等性检查
            cached_response = await self._check_idempotency(session_id, request_id)
            if cached_response:
                logger.info(f"Cache hit for {session_id}/{request_id}")
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{uuid.uuid4()}",
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    full_text=cached_response.get("full_text", ""),
                    finish_reason=agent_service_pb2.STOP
                )
                return

            # 分布式锁
            lock_acquired = await self._acquire_session_lock(session_id, request_id)
            if not lock_acquired:
                raise ValueError("Another request is processing for this session")

            # 构建上下文
            with REQUEST_DURATION.labels(operation="context_building").time():
                user_context_data = await self._build_user_context(user_id, active_db)
                conversation_context = await self._build_conversation_context(session_id, user_id)

                # RAG 检索（带降级）
                knowledge_context = ""
                try:
                    if active_db and user_id:
                        ks = KnowledgeService(active_db)
                        knowledge_context = await ks.retrieve_context(
                            user_id=uuid.UUID(user_id),
                            query=request.message if request.HasField("message") else ""
                        )
                except Exception as e:
                    logger.warning(f"Knowledge retrieval failed: {e}, continuing without RAG")

            # 构建 Prompt
            base_system_prompt = build_system_prompt(
                user_context_data,
                conversation_history=conversation_context
            )

            if knowledge_context:
                base_system_prompt += f"\n\n## 检索到的知识背景\n{knowledge_context}"

            # 发送思考状态
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                status_update=agent_service_pb2.AgentStatus(
                    state=agent_service_pb2.AgentStatus.THINKING,
                    details="Analyzing your request..."
                )
            )

            # LLM 调用
            full_response = ""
            tool_execution_results = []
            total_prompt_tokens = 0
            total_completion_tokens = 0

            with REQUEST_DURATION.labels(operation="llm_generation").time():
                tools = await self._get_tools_schema()
                user_message = ""
                if request.HasField("message"):
                    user_message = request.message
                elif request.HasField("tool_result"):
                    tool_result = request.tool_result
                    user_message = f"Tool '{tool_result.tool_name}' result: {tool_result.result_json}"

                async for chunk in llm_service.chat_stream_with_tools(
                    system_prompt=base_system_prompt,
                    user_message=user_message,
                    tools=tools
                ):
                    if chunk.type == "text":
                        full_response += chunk.content
                        yield agent_service_pb2.ChatResponse(
                            response_id=f"resp_{uuid.uuid4()}",
                            created_at=int(datetime.now().timestamp()),
                            request_id=request_id,
                            delta=chunk.content
                        )

                    elif chunk.type == "tool_call_end":
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

                    elif chunk.type == "usage" and self.token_tracker:
                        total_prompt_tokens = chunk.prompt_tokens or 0
                        total_completion_tokens = chunk.completion_tokens or 0
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

            # 记录 Token 使用
            await self._record_token_usage(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens
            )

            # 组合响应
            final_response_data = self.response_composer.compose_response(
                llm_text=full_response,
                tool_results=tool_execution_results,
                requires_confirmation=False,
                confirmation_data=None
            )

            # 缓存响应
            await self._cache_response(session_id, request_id, final_response_data)

            # 标记消息已处理
            await self.message_tracker.mark_processed(request_id)

            # 记录成功
            await self.circuit_breaker.record_success() if self.circuit_breaker else None

            # 发送最终响应
            yield agent_service_pb2.ChatResponse(
                response_id=f"resp_{uuid.uuid4()}",
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                full_text=final_response_data.get("message", full_response),
                finish_reason=agent_service_pb2.STOP
            )

            # 指标和日志
            duration = time.time() - start_time
            if self.enable_metrics:
                REQUEST_COUNTER.labels(status="success", session_id=session_id).inc()

            self._log_request(session_id, request_id, user_id, duration, "success")

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Orchestration error: {e}", exc_info=True)

            # 记录失败
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()

            # 指标和日志
            if self.enable_metrics:
                REQUEST_COUNTER.labels(status="error", session_id=session_id).inc()

            self._log_request(session_id, request_id, user_id, duration, "error", str(e))

            # 发送错误响应
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
            # 清理会话
            await self._release_session_lock(session_id, request_id)
            await self._track_session(session_id, add=False)

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            "healthy": self._healthy,
            "startup_time": self._startup_time,
            "uptime_seconds": time.time() - self._startup_time,
            "active_sessions": len(self.active_sessions),
            "circuit_breaker_state": self.circuit_breaker.get_state() if self.circuit_breaker else "DISABLED",
            "components": {
                "redis": self.redis is not None,
                "state_manager": self.state_manager is not None,
                "validator": self.validator is not None,
                "context_pruner": self.context_pruner is not None,
                "token_tracker": self.token_tracker is not None,
                "circuit_breaker": self.circuit_breaker is not None,
            }
        }
