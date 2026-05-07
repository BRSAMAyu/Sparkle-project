"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

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

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus not available, metrics disabled")

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.composer import ResponseComposer
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
from app.orchestration.executor import ToolExecutor
from app.orchestration.experience_actuator import ExperienceActuator
from app.orchestration.prompts import build_system_prompt
from app.orchestration.situation_brief import SituationBriefBuilder
from app.orchestration.soul_compiler import DEFAULT_COMPANION_STATE, attach_shadow_soul_runtime
from app.orchestration.state_manager import SessionStateManager
from app.orchestration.token_tracker import TokenTracker
from app.orchestration.validator import RequestValidator
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.services.companion_state_service import CompanionStateService
from app.services.galaxy_service import GalaxyService
from app.services.graph_knowledge_service import GraphKnowledgeService
from app.services.intervention_feedback_binding_service import InterventionFeedbackBindingService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import llm_service
from app.services.user_service import UserService
from app.services.user_strategy_state_service import UserStrategyStateService

TRACER = trace.get_tracer(__name__)

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


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


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
    """消息 ID 追踪器 - 防止并发重复处理，支持 TTL 清理"""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.processed_messages: dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = asyncio.Lock()

    def _cleanup_expired(self, now: float) -> int:
        cutoff = now - self.ttl_seconds
        expired = [message_id for message_id, ts in self.processed_messages.items() if ts < cutoff]
        for message_id in expired:
            self.processed_messages.pop(message_id, None)
        return len(expired)

    def _cleanup_overflow(self) -> int:
        if len(self.processed_messages) <= self.max_size:
            return 0
        sorted_items = sorted(self.processed_messages.items(), key=lambda item: item[1])
        remove_count = len(self.processed_messages) - self.max_size // 2
        for message_id, _ in sorted_items[:remove_count]:
            self.processed_messages.pop(message_id, None)
        return remove_count

    async def is_processed(self, message_id: str) -> bool:
        """检查消息是否已处理"""
        async with self.lock:
            self._cleanup_expired(time.time())
            return message_id in self.processed_messages

    async def mark_processed(self, message_id: str):
        """标记消息为已处理"""
        async with self.lock:
            now = time.time()
            expired = self._cleanup_expired(now)
            if expired:
                logger.debug(f"Message tracker TTL cleanup: removed {expired} expired messages")

            overflow = self._cleanup_overflow()
            if overflow:
                logger.warning(f"Message tracker cleanup: removed {overflow} old messages")

            self.processed_messages[message_id] = now

    async def cleanup(self, message_id: str):
        """清理指定消息（用于测试或手动干预）"""
        async with self.lock:
            self.processed_messages.pop(message_id, None)


class ProductionChatOrchestrator:
    """
    Legacy production orchestrator.

    This stack is no longer bridge-safe. The supported runtime is
    ``app.orchestration.orchestrator.ChatOrchestrator``.

    Set ``SPARKLE_ALLOW_LEGACY_PRODUCTION_ORCHESTRATOR=1`` only for
    audited migration work; otherwise construction is blocked so the
    bridge architecture cannot be silently bypassed.
    """

    def __init__(
        self,
        db_session: AsyncSession | None = None,
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
        if os.getenv("SPARKLE_ALLOW_LEGACY_PRODUCTION_ORCHESTRATOR", "").strip().lower() not in {"1", "true", "yes"}:
            raise RuntimeError(
                "ProductionChatOrchestrator is legacy and unsupported. "
                "Use ChatOrchestrator or explicitly set SPARKLE_ALLOW_LEGACY_PRODUCTION_ORCHESTRATOR=1 "
                "for audited migration-only use."
            )
        self.db_session = db_session
        self.redis = redis_client

        # 核心组件
        self.state_manager = SessionStateManager(redis_client) if redis_client else None
        self.validator = (
            RequestValidator(
                redis_client,
                daily_quota=getattr(settings, "DAILY_QUOTA", 100000),
                enable_quota_check=bool(getattr(settings, "LLM_QUOTA_ENABLED", False)),
            )
            if redis_client
            else None
        )
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
        self.active_sessions: set[str] = set()
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
            registered = dynamic_tool_registry.ensure_package_registered("app.tools")
            if registered > 0:
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

    async def _check_idempotency(self, session_id: str, request_id: str) -> dict[str, Any] | None:
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
            logger.warning("Session lock disabled: Redis unavailable")
            return True

        with TRACER.start_as_current_span("redis.acquire_lock") as span:
            try:
                acquired = await self.state_manager.acquire_lock(session_id, request_id)
                span.set_attribute("lock.acquired", acquired)
                return acquired
            except Exception as e:
                span.record_exception(e)
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

    async def _cache_response(self, session_id: str, request_id: str, response_data: dict[str, Any]):
        """缓存响应（带降级）"""
        if not self.state_manager:
            return

        try:
            await self.state_manager.cache_response(session_id, request_id, response_data)
        except Exception as e:
            logger.warning(f"Response caching failed: {e}")

    async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """构建用户上下文（带错误处理和降级）"""
        try:
            user_service = UserService(db_session, self.redis)
            user_context = await user_service.get_context(uuid.UUID(user_id))
            analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

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

            if user_context:
                profile_payload = self._build_profile_payload(
                    user_context_data=user_context.model_dump() if hasattr(user_context, "model_dump") else user_context,
                    preferences=user_context.preferences if hasattr(user_context, "preferences") else None,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                )
                return {
                    "user_context": user_context,
                    "analytics_summary": analytics,
                    "preferences": {
                        "depth_preference": user_context.preferences.get("depth_preference", 0.5),
                        "curiosity_preference": user_context.preferences.get("curiosity_preference", 0.5),
                    },
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "profile": profile_payload,
                }
            else:
                logger.warning(f"User {user_id} not found, using fallback")
                fallback = self._get_fallback_context()
                fallback["preference_version"] = preference_version
                fallback["llm_profile"] = llm_profile_data
                fallback["profile"] = self._build_profile_payload(
                    user_context_data=None,
                    preferences=fallback.get("preferences"),
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                )
                return fallback

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            return self._get_fallback_context()

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

        prefs = preferences if isinstance(preferences, dict) else {}
        llm_profile = llm_profile_data if isinstance(llm_profile_data, dict) else {}

        return {
            "identity": identity,
            "preferences": prefs,
            "llm_profile": llm_profile,
            "preference_version": preference_version,
        }

    def _get_fallback_context(self) -> dict[str, Any]:
        """获取降级上下文"""
        fallback = {
            "user_context": None,
            "analytics_summary": {"is_active": True, "engagement_level": "medium"},
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "preference_version": 0,
            "llm_profile": None,
        }
        fallback["profile"] = self._build_profile_payload(
            user_context_data=None,
            preferences=fallback.get("preferences"),
            llm_profile_data=None,
            preference_version=0,
        )
        return fallback

    async def _build_conversation_context(self, session_id: str, user_id: str) -> dict[str, Any]:
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

    async def _get_tools_schema(self) -> list[dict[str, Any]]:
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
        error: str | None = None
    ):
        """结构化日志"""
        log_data = {
            "timestamp": _utcnow().isoformat(),
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
        db_session: AsyncSession | None = None,
        context_data: dict[str, Any] = None
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
        response_id = str(uuid.uuid4())
        session_id = request.session_id
        user_id = request.user_id
        workflow_id = (context_data or {}).get("workflow_id", "standard_chat")
        prompt_version = (context_data or {}).get("prompt_version", "v1")
        trace_id = format(trace.get_current_span().get_span_context().trace_id, "032x")

        # 消息去重检查
        if await self.message_tracker.is_processed(request_id):
            logger.warning(f"Duplicate request detected: {request_id}")
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message="Request already processed",
                    retryable=False,
                    error_code=agent_service_pb2.ERROR_CODE_CONFLICT,
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        # 熔断器检查
        if self.circuit_breaker and not await self.circuit_breaker.can_execute():
            state = self.circuit_breaker.get_state()
            logger.error(f"Circuit breaker is {state}, rejecting request")
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message=f"Service temporarily unavailable (circuit breaker: {state})",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_UNAVAILABLE,
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        # 并发控制
        session_tracked = await self._track_session(session_id, add=True)
        if not session_tracked:
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message="Too many concurrent sessions",
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_RATE_LIMITED,
                ),
                finish_reason=agent_service_pb2.ERROR
            )
            return

        active_db = db_session or self.db_session

        lock_acquired = False
        lock_renewal_task: asyncio.Task | None = None
        lock_renewal_stop: asyncio.Event | None = None
        try:
            # 验证请求
            with TRACER.start_as_current_span("request.validate"):
                with REQUEST_DURATION.labels(operation="validation").time():
                    validation_result = await self.validator.validate_chat_request(request)
                    if not validation_result.is_valid:
                        raise ValueError(f"Validation failed: {validation_result.error_message}")

            # 幂等性检查
            with TRACER.start_as_current_span("request.idempotency_check"):
                cached_response = await self._check_idempotency(session_id, request_id)
            if cached_response:
                logger.info(f"Cache hit for {session_id}/{request_id}")
                cached_metadata = cached_response.get("metadata") if isinstance(cached_response, dict) else None
                metadata_map = {}
                if isinstance(cached_metadata, dict):
                    metadata_map = {str(k): str(v) for k, v in cached_metadata.items()}
                yield agent_service_pb2.ChatResponse(
                    response_id=response_id,
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    prompt_version=prompt_version,
                    metadata=metadata_map,
                    full_text=cached_response.get("full_text") or cached_response.get("message", ""),
                    finish_reason=agent_service_pb2.STOP
                )
                return

            # 分布式锁
            lock_acquired = await self._acquire_session_lock(session_id, request_id)
            if not lock_acquired:
                raise ValueError("Another request is processing for this session")

            # Start lock renewal for long-running requests
            lock_renewal_task, lock_renewal_stop = await self.state_manager.start_lock_renewal(
                session_id, request_id, interval=10.0
            )

            # 构建上下文
            with TRACER.start_as_current_span("context.build"):
                with REQUEST_DURATION.labels(operation="context_building").time():
                    user_context_data = await self._build_user_context(user_id, active_db)
                    conversation_context = await self._build_conversation_context(session_id, user_id)

                # PlanScope: Extract plan_id and build plan_context
                plan_context = None
                try:
                    from google.protobuf.json_format import MessageToDict
                    if request.HasField("extra_context"):
                        request_context = MessageToDict(request.extra_context)
                        plan_id_str = request_context.get("plan_id") if request_context else None
                        if plan_id_str and active_db:
                            try:
                                from uuid import UUID

                                from app.core.plan_context import PlanContextBuilder
                                plan_id = UUID(plan_id_str)
                                plan_builder = PlanContextBuilder(active_db, self.redis)
                                plan_context = await plan_builder.build_enriched(uuid.UUID(user_id), plan_id)
                                if plan_context:
                                    logger.info(f"Built plan_context for plan_id={plan_id}")
                            except (ValueError, AttributeError) as e:
                                logger.warning(f"Invalid plan_id in extra_context: {e}")
                            except Exception as e:
                                logger.warning(f"Failed to build plan context: {e}")
                except Exception as e:
                    logger.debug(f"Could not extract plan_context from request: {e}")

                # P4: Tool Preference Routing
                preferred_tools_hint = ""
                try:
                    if active_db and user_id:
                        # Convert user_id string to UUID
                        user_uuid = uuid.UUID(user_id)
                        router = ToolPreferenceRouter(active_db, user_uuid, self.redis)
                        preferred_tools = await router.get_preferred_tools(limit=3)
                        if preferred_tools:
                            preferred_tools_hint = f"\n\n## 工具偏好\n根据历史习惯，用户倾向于使用以下工具: {', '.join(preferred_tools)}"
                            logger.info(f"Injected tool preferences for user {user_id}: {preferred_tools}")
                except Exception as e:
                    logger.warning(f"Failed to get tool preferences: {e}")

                # GraphRAG 检索（增强版，带降级）
                knowledge_context = ""
                try:
                    if active_db and user_id:
                        with TRACER.start_as_current_span("rag.graphrag"):
                            # Signal-to-Action Spine: apply RetrievalDirective
                            _retrieval_top_k = 5
                            _retrieval_depth = 2
                            try:
                                from app.signals.spine_orchestrator import get_spine_orchestrator
                                _spine_rag = get_spine_orchestrator(self.redis)
                                _ret_dir = await _spine_rag.get_retrieval_directive(str(user_id))
                                if _ret_dir:
                                    _retrieval_top_k = max(1, min(20, _ret_dir.token_budget // 600))
                                    if _ret_dir.pollution_guard == "strict":
                                        _retrieval_depth = 1
                            except Exception as exc:
                                logger.warning("Spine retrieval directive fetch failed for user={}: {}", user_id, exc)

                            # 使用 GraphKnowledgeService 进行增强的 GraphRAG 检索
                            graph_ks = GraphKnowledgeService(active_db)
                            rag_result = await graph_ks.graph_rag_search(
                                query=request.message if request.HasField("message") else "",
                                user_id=uuid.UUID(user_id),
                                depth=_retrieval_depth,
                                top_k=_retrieval_top_k
                            )
                        knowledge_context = rag_result.get("context", "")

                        # 记录 GraphRAG 指标
                        if rag_result.get("metadata"):
                            logger.info(
                                f"GraphRAG results: "
                                f"vector={rag_result['metadata'].get('vector_count', 0)}, "
                                f"graph={rag_result['metadata'].get('graph_count', 0)}, "
                                f"fused={rag_result['metadata'].get('fusion_count', 0)}"
                            )

                        # Prometheus 指标
                        if PROMETHEUS_AVAILABLE:
                            REQUEST_COUNTER.labels(status="graphrag_success", session_id=session_id).inc()
                except Exception as e:
                    logger.warning(f"GraphRAG retrieval failed: {e}, falling back to vector search")
                    # 降级到普通向量检索
                    try:
                        if active_db and user_id:
                            with TRACER.start_as_current_span("rag.vector_fallback"):
                                ks = KnowledgeService(active_db)
                                knowledge_context = await ks.retrieve_context(
                                    user_id=uuid.UUID(user_id),
                                    query=request.message if request.HasField("message") else ""
                                )
                            if PROMETHEUS_AVAILABLE:
                                REQUEST_COUNTER.labels(status="vector_success", session_id=session_id).inc()
                    except Exception as e2:
                        logger.error(f"Fallback knowledge retrieval also failed: {e2}")
                        if PROMETHEUS_AVAILABLE:
                            REQUEST_COUNTER.labels(status="rag_failed", session_id=session_id).inc()
                        # 降级到关键词检索（避免向量服务依赖）
                        try:
                            if active_db and user_id:
                                with TRACER.start_as_current_span("rag.keyword_fallback"):
                                    galaxy_service = GalaxyService(active_db)
                                    nodes = await galaxy_service.keyword_search(
                                        user_id=uuid.UUID(user_id),
                                        query=request.message if request.HasField("message") else "",
                                        limit=5
                                    )
                                if nodes:
                                    lines = ["Relevant Knowledge Base (Keyword Fallback):"]
                                    for node in nodes:
                                        line = f"- [{node.name}]: {node.description or 'No description'}"
                                        if node.parent_name:
                                            line += f" (Parent: {node.parent_name})"
                                        lines.append(line)
                                    knowledge_context = "\n".join(lines)
                                    if PROMETHEUS_AVAILABLE:
                                        REQUEST_COUNTER.labels(status="keyword_success", session_id=session_id).inc()
                        except Exception as e3:
                            logger.error(f"Keyword fallback failed: {e3}")

            # 构建 Prompt
            if isinstance(user_context_data, dict):
                visible_update_context = (context_data or {}).get("visible_update_context")
                if isinstance(visible_update_context, dict):
                    for key in (
                        "proactive_opening_message",
                        "pending_observation",
                        "post_adaptation_question",
                        "active_intervention_id",
                    ):
                        value = str(visible_update_context.get(key) or "").strip()
                        if value:
                            user_context_data[key] = value
                    active_interventions = visible_update_context.get("active_interventions")
                    if isinstance(active_interventions, list) and active_interventions:
                        user_context_data["active_interventions"] = active_interventions
                if (context_data or {}).get("evolution_highlights"):
                    user_context_data["evolution_highlights"] = list((context_data or {}).get("evolution_highlights") or [])
            companion_state_payload = {
                "effective_companion_state": DEFAULT_COMPANION_STATE.to_dict(),
                "relationship_profile": {},
                "companion_state_recent_revisions": [],
            }
            plan_uuid = None
            if active_db and user_id:
                try:
                    companion_service = CompanionStateService(active_db, self.redis)
                    user_uuid = uuid.UUID(str(user_id))
                    if isinstance(plan_context, dict):
                        raw_plan_id = plan_context.get("plan_id")
                        if raw_plan_id:
                            try:
                                plan_uuid = uuid.UUID(str(raw_plan_id))
                            except (TypeError, ValueError, AttributeError):
                                plan_uuid = None
                    companion_state_payload = {
                        "effective_companion_state": await companion_service.get_effective_state(
                            user_uuid,
                            plan_id=plan_uuid,
                            session_id=session_id,
                        ),
                        "relationship_profile": await companion_service.get_relationship_profile(user_uuid),
                        "companion_state_recent_revisions": await companion_service.get_recent_revisions(
                            user_uuid,
                            plan_id=plan_uuid,
                            session_id=session_id,
                        ),
                    }
                except Exception as exc:
                    logger.warning(f"Failed to hydrate companion runtime context: {exc}")
            if isinstance(user_context_data, dict):
                user_context_data.update(companion_state_payload)
            runtime_context_data = dict(context_data or {})
            runtime_context_data.update(companion_state_payload)
            if active_db and user_id:
                try:
                    binding_service = InterventionFeedbackBindingService(active_db, self.redis)
                    active_interventions = await binding_service.resolve_active_interventions(
                        user_id=uuid.UUID(str(user_id)),
                        session_id=session_id,
                        runtime_active_interventions=(
                            user_context_data.get("active_interventions")
                            if isinstance(user_context_data, dict) and isinstance(user_context_data.get("active_interventions"), list)
                            else None
                        ),
                    )
                    last_feedback_binding = await binding_service.get_last_feedback_binding(session_id)
                    runtime_context_data["active_interventions"] = active_interventions
                    if active_interventions:
                        runtime_context_data["active_intervention_id"] = str(
                            active_interventions[0].get("intervention_id") or ""
                        ).strip()
                    if last_feedback_binding:
                        runtime_context_data["last_feedback_binding"] = last_feedback_binding
                    if isinstance(user_context_data, dict):
                        user_context_data["active_interventions"] = active_interventions
                        if active_interventions:
                            user_context_data["active_intervention_id"] = str(
                                active_interventions[0].get("intervention_id") or ""
                            ).strip()
                        if last_feedback_binding:
                            user_context_data["last_feedback_binding"] = last_feedback_binding
                except Exception as exc:
                    logger.warning(f"Failed to hydrate active intervention state: {exc}")
            if active_db and user_id and isinstance(user_context_data, dict):
                try:
                    strategy_service = UserStrategyStateService(active_db, self.redis)
                    user_strategy_state = await strategy_service.get_effective_state(
                        uuid.UUID(str(user_id)),
                        plan_id=plan_uuid,
                        session_id=session_id,
                    )
                    user_strategy_history = await strategy_service.get_recent_changes(
                        uuid.UUID(str(user_id)),
                        plan_id=plan_uuid,
                        session_id=session_id,
                        limit=6,
                    )
                    user_context_data["user_strategy_state"] = user_strategy_state
                    if user_strategy_history:
                        user_context_data["user_strategy_history"] = user_strategy_history
                    runtime_context_data["user_strategy_state"] = user_strategy_state
                    runtime_context_data["user_strategy_history"] = user_strategy_history
                except Exception as exc:
                    logger.warning(f"Failed to hydrate user strategy state: {exc}")
            if isinstance(user_context_data, dict):
                try:
                    situation_brief = (await SituationBriefBuilder().build(
                        user_context_payload=user_context_data,
                        plan_context=plan_context,
                        focused_memory=user_context_data.get("focused_memory"),
                        context_briefing_note=str(user_context_data.get("context_briefing_note") or "").strip() or None,
                        visible_update_context={},
                        dual_core_snapshot=_as_dict(user_context_data.get("dual_core_snapshot")),
                        session_feedback_signal={},
                        progress_snapshot=_as_dict(user_context_data.get("progress_snapshot")),
                        adaptation_records=[
                            item
                            for item in (user_context_data.get("adaptation_records") or [])
                            if isinstance(item, dict)
                        ],
                    )).to_dict()
                    user_context_data["situation_brief"] = situation_brief
                    runtime_context_data["situation_brief"] = situation_brief
                    decision_context = situation_brief.get("decision_context")
                    if isinstance(decision_context, dict):
                        user_context_data["residual_decision_context"] = decision_context
                        runtime_context_data["residual_decision_context"] = decision_context
                except Exception as exc:
                    logger.warning(f"Failed to build production situation brief: {exc}")
            if active_db and user_id and isinstance(user_context_data, dict):
                try:
                    request_message = request.message if request.WhichOneof("input") == "message" else ""
                    await ExperienceActuator(active_db, self.redis).apply(
                        user_id=user_id,
                        session_id=session_id,
                        plan_id=plan_uuid,
                        request_id=request_id,
                        user_message=request_message,
                        file_ids=list(request.file_ids),
                        user_context_payload=user_context_data,
                        context_targets=[runtime_context_data],
                    )
                except Exception as exc:
                    logger.warning(f"Failed to apply phase 4 experience actions in production runtime: {exc}")
            try:
                await attach_shadow_soul_runtime(
                    target_context=runtime_context_data,
                    redis_client=self.redis,
                    user_id=user_id,
                    user_context=user_context_data,
                    plan_context=plan_context,
                    effective_companion_state=runtime_context_data.get("effective_companion_state"),
                    relationship_profile=runtime_context_data.get("relationship_profile"),
                    recent_revisions=runtime_context_data.get("companion_state_recent_revisions"),
                )
            except Exception as exc:
                logger.warning(f"Shadow soul runtime attach failed (non-fatal): {exc}")
            if isinstance(user_context_data, dict):
                for key in ("soul_runtime_context", "soul_runtime_debug"):
                    if runtime_context_data.get(key) is not None:
                        user_context_data[key] = runtime_context_data[key]
            context_data = runtime_context_data

            # Signal-to-Action Spine: fetch all relevant directives for prompt modulation
            spine_response_directive = None
            _spine_exec_section = ""  # Extra prompt section for ExamSprint phase context
            _spine_receipt_payload = None  # Latest UserVisibleReceipt for response metadata
            _spine_stale_card = None  # StaleStateGuard comeback card
            _spine_chronicle_summary = None  # Growth chronicle narrative
            _spine_fatigue_context = None  # Fatigue/crisis state
            try:
                from app.signals.spine_orchestrator import get_spine_orchestrator
                _spine = get_spine_orchestrator(self.redis)

                # ResponseDirective → tone/length/avoid/acknowledge
                _resp_dir = await _spine.get_response_directive(str(user_id))
                if _resp_dir:
                    spine_response_directive = {
                        "tone": _resp_dir.tone,
                        "length": _resp_dir.length,
                        "avoid": list(_resp_dir.avoid or []),
                        "must_acknowledge": list(_resp_dir.must_acknowledge or []),
                        "include_user_options": _resp_dir.include_user_options,
                    }

                # ExecutionDirective → exam sprint phase constraints injected into prompt
                _exec_dir = await _spine.get_active_directive(str(user_id))
                if _exec_dir:
                    hc = _exec_dir.hard_constraints or {}
                    phase_id = hc.get("exam_sprint_phase_id")
                    if phase_id:
                        days = None
                        raw_days = await self.redis.get(f"spine:exam_sprint:{user_id}:deadline_days")
                        if raw_days:
                            try:
                                days = int(raw_days.decode() if isinstance(raw_days, bytes) else raw_days)
                            except (ValueError, AttributeError):
                                pass
                        phase_label = {
                            "build_path": "建立最小通过路径",
                            "bottleneck_training": "主瓶颈训练",
                            "error_repair": "高频错因修复",
                            "survival": "考前生存策略",
                            "final_review": "最后复盘，不开新坑",
                        }.get(phase_id, phase_id)
                        dur_cap = hc.get("max_task_duration_min", 45)
                        no_new = hc.get("avoid_new_chapter", False)
                        task_type = hc.get("exam_sprint_task_type_bias", "mixed")
                        _spine_exec_section = (
                            f"\n\n## 考试冲刺策略约束"
                            f"\n- 当前阶段：{phase_label}"
                            + (f"（距考试 {days} 天）" if days is not None else "")
                            + f"\n- 单任务时长上限：{dur_cap} 分钟"
                            f"\n- 推荐任务类型：{task_type}"
                            + ("\n- 禁止推进新章节" if no_new else "")
                            + ("\n- 优先高收益复盘内容" if hc.get("prefer_high_yield") else "")
                        )
                    elif _exec_dir.user_visible_reason:
                        _spine_exec_section = (
                            f"\n\n## 当前策略调整\n{_exec_dir.user_visible_reason}"
                        )

                # UserVisibleReceipt → include in streaming metadata so Flutter can render it
                _latest_receipt = await _spine.get_latest_receipt(str(user_id))
                if _latest_receipt:
                    _receipt_actions = list(_latest_receipt.actions or [])
                    _correctable = "correct" in _receipt_actions
                    _correction_options = (
                        ["这个判断不准确", "我不同意这个调整", "继续，先看看效果"]
                        if _correctable else []
                    )
                    _spine_receipt_payload = {
                        "receipt_id": _latest_receipt.receipt_id,
                        "trigger": _latest_receipt.receipt_type,
                        "summary": _latest_receipt.message,
                        "correctable": _correctable,
                        "correction_options": _correction_options,
                    }

                # StaleStateGuard → check if user returned after extended absence
                from app.signals.stale_state_guard import TimeContext
                _last_seen_raw = await self.redis.get(f"spine:last_seen:{user_id}")
                if _last_seen_raw:
                    try:
                        import json as _json
                        _last_ctx = _json.loads(_last_seen_raw)
                        _tc = TimeContext(
                            now=datetime.now(UTC).isoformat(),
                            last_user_interaction_at=_last_ctx.get("last_seen"),
                        )
                        _stale_packet = _spine.stale_guard.check(_tc)
                        if _stale_packet and _stale_packet.elapsed_since_last_seen_min > 60:
                            _stale_card = _spine.stale_guard.build_recovery_card(_stale_packet, _tc)
                            if _stale_card:
                                _spine_stale_card = _stale_card
                    except Exception as exc:
                        logger.debug("Spine stale-state card enrichment skipped for user={}: {}", user_id, exc)

                # Growth chronicle → inject recent narrative for AI awareness
                try:
                    _chronicle_entries = await _spine.growth_chronicle.get_chronicle(
                        str(user_id), limit=3,
                    )
                    if _chronicle_entries:
                        _spine_chronicle_summary = "；".join(
                            f"{e.title}（{e.narrative[:60]}）"
                            for e in _chronicle_entries
                        )
                except Exception as exc:
                    logger.debug("Spine growth chronicle enrichment skipped for user={}: {}", user_id, exc)

                # Fatigue + crisis → inject tone modulation
                try:
                    _fatigue_raw = await self.redis.get(f"spine:fatigue:{user_id}:latest")
                    _crisis_raw = await self.redis.get(f"spine:crisis:{user_id}:latest")
                    if _fatigue_raw or _crisis_raw:
                        _spine_fatigue_context = {}
                        if _fatigue_raw:
                            _spine_fatigue_context["fatigue_level"] = _json.loads(
                                _fatigue_raw if isinstance(_fatigue_raw, str) else _fatigue_raw.decode()
                            ).get("fatigue_level")
                        if _crisis_raw:
                            _spine_fatigue_context["crisis_mode"] = True
                except Exception as exc:
                    logger.debug("Spine fatigue/crisis context enrichment skipped for user={}: {}", user_id, exc)

                # Record current timestamp for next stale check
                import json as _json
                await self.redis.set(
                    f"spine:last_seen:{user_id}",
                    _json.dumps({"last_seen": datetime.now(UTC).isoformat()}),
                    ex=7 * 24 * 3600,
                )
            except Exception as _spine_exc:
                logger.debug("Spine directive fetch skipped: {}", _spine_exc)

            # R5-DF2/DF3: Inject community and skill directives into user_context for prompt rendering
            try:
                from app.signals.spine_orchestrator import get_spine_orchestrator as _SO
                _spine_quick = _SO(self.redis)
                _comm_dir = await _spine_quick.get_community_directive(str(user_id))
                if _comm_dir:
                    user_context_data["spine_community_directive"] = _comm_dir.to_dict()
                _skill_dir = await _spine_quick.get_skill_directive(str(user_id))
                if _skill_dir:
                    user_context_data["spine_skill_directive"] = _skill_dir.to_dict()
            except Exception as exc:
                logger.debug("Spine community/skill directive enrichment skipped for user={}: {}", user_id, exc)

            base_system_prompt = build_system_prompt(
                user_context_data,
                conversation_history=conversation_context,
                plan_context=plan_context,
                session_feedback_instruction=str((context_data or {}).get("session_feedback_instruction") or ""),
                dual_core_instruction=str((context_data or {}).get("dual_core_prompt_instruction") or ""),
                spine_response_directive=spine_response_directive,
                spine_chronicle_summary=_spine_chronicle_summary,
                spine_fatigue_context=_spine_fatigue_context,
            )

            if preferred_tools_hint:
                base_system_prompt += preferred_tools_hint

            if knowledge_context:
                base_system_prompt += f"\n\n## 检索到的知识背景\n{knowledge_context}"

            # Inject ExamSprint phase constraints from ExecutionDirective
            if _spine_exec_section:
                base_system_prompt += _spine_exec_section

            # Inject stale state recovery card as user-facing context
            if _spine_stale_card:
                base_system_prompt += (
                    f"\n\n## 用户返回感知\n"
                    f"用户刚刚回来。{_spine_stale_card.get('message_template', '')} "
                    f"优先用简短消息确认用户当前状态，不要直接继续上次话题。"
                )

            # ------------------------------------------------------------------

            # 发送思考状态
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
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

            with TRACER.start_as_current_span("llm.generate"):
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
                        tools=tools,
                        conversation_history=(conversation_context or {}).get("messages", []),
                        user_context=user_context_data,
                    ):
                        if chunk.type == "text":
                            full_response += chunk.content
                            yield agent_service_pb2.ChatResponse(
                                response_id=response_id,
                                created_at=int(datetime.now().timestamp()),
                                request_id=request_id,
                                delta=chunk.content
                            )

                        elif chunk.type == "tool_call_end":
                            await self._update_state(session_id, STATE_TOOL_CALLING, f"Calling {chunk.tool_name}...")
                            yield agent_service_pb2.ChatResponse(
                                response_id=response_id,
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
                                response_id=response_id,
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
            llm_profile_meta = {}
            if isinstance(user_context_data, dict):
                llm_profile = user_context_data.get("llm_profile")
                if llm_profile:
                    # Handle both dict and JSON string cases
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
                        llm_profile_meta = {}
            response_metadata = {
                "response_id": response_id,
                "trace_id": trace_id,
                "preference_version": (user_context_data or {}).get("preference_version", 0),
                "verbosity_target": llm_profile_meta.get("verbosity_target", "balanced"),
            }
            # Inject spine UserVisibleReceipt for Flutter to render "因为X我调整了Y" card
            if _spine_receipt_payload:
                import json as _json
                response_metadata["spine_receipt"] = _json.dumps(_spine_receipt_payload)
            # Inject stale state card for Flutter recovery UX
            if _spine_stale_card:
                import json as _json
                response_metadata["spine_stale_card"] = _json.dumps(_spine_stale_card)
            final_response_data["metadata"] = response_metadata

            try:
                from app.services.decision_record_service import DecisionRecordService

                if self.db_session is not None:
                    decision_service = DecisionRecordService(self.db_session)
                    await decision_service.record_decision(
                        user_id=uuid.UUID(str(user_id)),
                        module="ai",
                        action="generate_response",
                        preference_version=(user_context_data or {}).get("preference_version", 0),
                        preferences_snapshot={
                            "verbosity": llm_profile_meta.get("verbosity_target"),
                            "temperature": llm_profile_meta.get("temperature"),
                            "tone": llm_profile_meta.get("tone"),
                        },
                        outcome=f"Generated response with {len(full_response)} chars",
                    )
            except Exception as e:
                logger.warning(f"Failed to record decision: {e}")

            # 缓存响应
            await self._cache_response(session_id, request_id, final_response_data)

            # 标记消息已处理
            await self.message_tracker.mark_processed(request_id)

            # 记录成功
            await self.circuit_breaker.record_success() if self.circuit_breaker else None

            # 发送最终响应
            yield agent_service_pb2.ChatResponse(
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                prompt_version=prompt_version,
                metadata={str(k): str(v) for k, v in final_response_data.get("metadata", {}).items()},
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
                response_id=response_id,
                created_at=int(datetime.now().timestamp()),
                request_id=request_id,
                error=agent_service_pb2.Error(
                    message=str(e),
                    retryable=True,
                    error_code=agent_service_pb2.ERROR_CODE_INTERNAL,
                ),
                finish_reason=agent_service_pb2.ERROR
            )

        finally:
            # Stop lock renewal task
            if lock_renewal_task and lock_renewal_stop:
                try:
                    await self.state_manager.stop_lock_renewal(lock_renewal_task, lock_renewal_stop)
                except Exception as e:
                    logger.warning(f"Failed to stop lock renewal: {e}")
            # 清理会话 - only release lock if it was acquired
            if lock_acquired:
                await self._release_session_lock(session_id, request_id)
            await self._track_session(session_id, add=False)

    def get_health_status(self) -> dict[str, Any]:
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
