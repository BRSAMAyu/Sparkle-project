from __future__ import annotations

"""
LLM 安全包装器 - 为现有 LLM 服务提供无缝安全集成

功能:
1. 自动输入净化 (提示注入、XSS、敏感信息)
2. 配额检查与成本控制
3. 输出验证与过滤
4. 监控指标收集
5. 异常处理与降级

R2-08-02 收敛契约（fail-closed 转发面）:
- 包装器只暴露两类 LLM 调用面：
  1. 安全包装方法（完整管线：输入筛查→配额→监控→输出验证→用量记账）
     chat / chat_with_tools / stream_chat
  2. 显式审计旁路方法（配额[可识别身份时]+监控+用量记账；深度筛查由内层
     LLMService 的 secure_messages/sanitize_text_for_llm/wrap_user_message
     自有 hygiene 层承担，避免双重改写语义漂移）
     reason / reason_json / chat_json / continue_with_tool_results /
     chat_stream_with_tools / generate_push_content
- `__getattr__` 不再无界转发：仅放行内层路由元属性
  （chat_model/reason_model/model_key/default_model），其余属性一律
  AttributeError。新增旁路必须在文件内显式实现方法并登记审计论证。
- 旁路豁免论证：continue_with_tool_results 的输入是前序安全调用产出的
  工具结果与对话历史（用户原始输入已在上游被筛查）；reason*/chat_json/
  generate_push_content 为系统内部结构化推理/文案生成，无终端用户身份可
  绑定配额——两者均保留监控与全局成本记账，配额在可识别身份时强制生效。

创建时间: 2026-01-03
R2-08-02 收敛: 2026-09-18
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, cast

from app.core.llm_monitoring import (
    LLM_CALLS_TOTAL,
    LLM_LATENCY_SECONDS,
    TASK_FAILURES,
    LLMMonitor,
)
from app.core.llm_output_validator import LLMOutputValidator
from app.core.llm_quota import LLMCostGuard
from app.core.llm_safety import LLMSafetyService, SafetyCheckResult

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_input_filter: bool = True      # 输入过滤
    enable_quota_check: bool = True       # 配额检查
    enable_output_validation: bool = True # 输出验证
    enable_monitoring: bool = True        # 监控
    strict_mode: bool = True              # 严格模式
    auto_sanitize: bool = True            # 自动净化


def _stringify(value: Any) -> str:
    """把常见消息载荷收敛成可估算 token 的文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        content = value.get("content", "")
        return content if isinstance(content, str) else json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, (list, tuple)):
        return " ".join(filter(None, (_stringify(item) for item in value)))
    return ""


class LLMSecurityWrapper:
    """
    LLM 安全包装器 - 为现有 LLM 服务提供统一安全层

    使用示例:
        # 初始化
        security_wrapper = LLMSecurityWrapper(
            llm_service=your_llm_service,
            redis_client=redis,
            config=SecurityConfig()
        )

        # 使用包装后的方法 (自动应用安全层)
        response = await security_wrapper.chat(
            messages=[{"role": "user", "content": user_input}],
            user_id="user_123",
        )
    """

    #: 仅这两类路由元属性允许经 __getattr__ 透传到内层服务（只读，无调用面）。
    #: default_model 供 persistence_layer 等读取路由模型名做元数据记录。
    _FORWARDABLE_META_ATTRS = frozenset(
        {
            "chat_model",
            "reason_model",
            "model_key",
            "default_model",
            "agent_role",
            "get_current_selection",
            "is_thinking_mode",
        }
    )

    def __init__(
        self,
        llm_service: Any,
        redis_client: Any,
        config: SecurityConfig | None = None
    ):
        """
        初始化安全包装器

        Args:
            llm_service: 原始 LLM 服务实例
            redis_client: Redis 客户端 (用于配额)
            config: 安全配置
        """
        self.llm_service = llm_service
        self.config = config or SecurityConfig()

        # 初始化各安全模块
        self.safety_service = LLMSafetyService(enable_deep_analysis=self.config.strict_mode)
        self.cost_guard = LLMCostGuard(redis_client) if self.config.enable_quota_check else None
        self.output_validator = LLMOutputValidator(strict_mode=self.config.strict_mode)
        self.monitor = LLMMonitor() if self.config.enable_monitoring else None

        logger.info(f"LLMSecurityWrapper initialized (strict_mode={self.config.strict_mode})")

    def __getattr__(self, name: str) -> Any:
        """fail-closed：不再无界转发（R2-08-02）。

        仅放行 `_FORWARDABLE_META_ATTRS` 中的只读路由元属性（含
        default_model，persistence_layer 记录 model_name 元数据所需）；其余
        属性一律 AttributeError，杜绝新增调用点静默绕过配额/筛查/监控。
        """
        if name.startswith("__"):
            raise AttributeError(name)
        if name in self._FORWARDABLE_META_ATTRS:
            inner = self.__dict__.get("llm_service")
            if inner is None:
                raise AttributeError(name)
            return getattr(inner, name)
        raise AttributeError(
            f"{type(self).__name__} blocks forwarded attribute {name!r} (R2-08-02 fail-closed). "
            "Use the secured surface (chat/chat_with_tools/stream_chat) or an audited bypass "
            "(reason/reason_json/chat_json/continue_with_tool_results/"
            "chat_stream_with_tools/generate_push_content). "
            "New bypasses must be implemented and audited explicitly in llm_security_wrapper.py."
        )

    # =============================================================================
    # 安全基元（配额 / 监控 / 记账）
    # =============================================================================

    @staticmethod
    def _resolve_user_id(**kwargs: Any) -> str | None:
        """从调用参数解析用户身份（与 LLMService._resolve_user_id 同语义）。"""
        user_id = kwargs.get("user_id")
        if user_id:
            return str(user_id)
        user_context = kwargs.get("user_context")
        if isinstance(user_context, dict):
            candidate = user_context.get("user_id") or user_context.get("uid")
            if candidate:
                return str(candidate)
        return None

    def _extract_input_text(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        parts = [_stringify(value) for value in args]
        parts.extend(_stringify(value) for value in kwargs.values())
        return " ".join(filter(None, parts))

    @staticmethod
    def _result_text(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(result, (dict, list)):
            try:
                return json.dumps(result, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(result)
        return ""

    async def _enforce_quota(self, endpoint: str, user_id: str | None, input_text: str) -> None:
        """配额预检：身份可识别时强制；配额设施自身故障时 fail-open（不阻断主链路）。"""
        if not user_id or not self.config.enable_quota_check or self.cost_guard is None:
            return
        try:
            estimated_tokens = self.cost_guard.estimate_tokens(input_text)
            quota_result = await self.cost_guard.check_quota(user_id, estimated_tokens, check_only=True)
        except Exception as exc:
            logger.warning(
                "LLM quota check failed open (endpoint=%s, user=%s): %s",
                endpoint,
                user_id,
                exc,
            )
            return
        if not quota_result.allowed:
            if self.monitor:
                self.monitor.record_quota_exceeded(user_id, quota_result.current_usage, quota_result.limit)
            raise QuotaExceededError(quota_result.message)
        if self.monitor:
            self.monitor.update_quota_metrics(
                user_id,
                quota_result.current_usage,
                quota_result.limit,
            )

    def _record_call_metrics(
        self,
        endpoint: str,
        model: str | None,
        status: str,
        latency_seconds: float,
        input_text: str,
        output_text: str,
    ) -> None:
        """监控记账（尽力而为，不向调用方抛错）。"""
        if not self.monitor:
            return
        try:
            # F-2 修复：LLM_CALLS_TOTAL/LLM_LATENCY_SECONDS 是 llm_monitoring 的模块级
            # 指标，并非 LLMMonitor 实例属性——原先经 self.monitor.X 访问触发
            # AttributeError 且被下方 except 静默吞掉，导致整个监控记账成为 no-op。
            LLM_CALLS_TOTAL.labels(
                model=model or "unknown",
                status=status,
                endpoint=endpoint,
            ).inc()
            LLM_LATENCY_SECONDS.labels(
                model=model or "unknown",
                endpoint=endpoint,
            ).observe(latency_seconds)
            if self.cost_guard and (input_text or output_text):
                self.monitor.estimate_and_record_cost(
                    model=model or "unknown",
                    input_tokens=self.cost_guard.estimate_tokens(input_text),
                    output_tokens=self.cost_guard.estimate_tokens(output_text),
                    endpoint=endpoint,
                )
        except Exception as exc:
            logger.warning("LLM monitor recording failed (ignored): %s", exc)

    def _record_call_failure(self, endpoint: str, model: str | None, exc: Exception) -> None:
        if not self.monitor:
            return
        try:
            # F-2 修复：TASK_FAILURES 同为模块级指标（属性名漂移曾令本记账静默失效）
            TASK_FAILURES.labels(
                task_type=endpoint,
                error_type=type(exc).__name__,
            ).inc()
        except Exception as recording_error:
            logger.warning("LLM monitor failure recording failed (ignored): %s", recording_error)

    async def _record_usage(self, user_id: str | None, model: str | None, output_text: str) -> None:
        """按实际产出补记用量（配额预检为 check_only，不扣减）。"""
        if not user_id or not output_text or not self.config.enable_quota_check or self.cost_guard is None:
            return
        try:
            actual_tokens = self.cost_guard.estimate_tokens(output_text)
            await self.cost_guard.record_usage(user_id, actual_tokens, model or "unknown")
        except Exception as exc:
            logger.warning("LLM usage recording failed (ignored): %s", exc)

    async def _run_audited(
        self,
        endpoint: str,
        func: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        """审计旁路统一执行体：配额（可识别身份时）→ 调用 → 监控/用量记账。"""
        user_id = self._resolve_user_id(**kwargs)
        model = kwargs.get("model")
        input_text = self._extract_input_text(args, kwargs)
        await self._enforce_quota(endpoint, user_id, input_text)

        start = time.monotonic()
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            self._record_call_failure(endpoint, model, exc)
            self._record_call_metrics(endpoint, model, "error", time.monotonic() - start, input_text, "")
            raise
        output_text = self._result_text(result)
        elapsed = time.monotonic() - start
        self._record_call_metrics(endpoint, model, "success", elapsed, input_text, output_text)
        await self._record_usage(user_id, model, output_text)
        return result

    # =============================================================================
    # 主要安全接口（完整管线）
    # =============================================================================

    async def chat(
        self,
        messages: list[dict[str, str]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        *,
        task_type: Any | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        安全的聊天接口（签名与内层 LLMService.chat 对齐）

        Args:
            messages: 对话消息
            model: 模型名称
            temperature: 温度参数（None = 由动态路由决定）
            task_type: 级联路由任务类型
            user_id: 用户ID（提供时启用配额与用量记账）

        Returns:
            str: 安全的响应内容
        """
        if messages is None:
            raise ValueError("chat() requires messages")

        # 1. 输入安全检查
        if self.config.enable_input_filter:
            safe_messages, check_result = await self._filter_messages(user_id or "anonymous", messages)
            if not check_result.is_safe and not self.config.auto_sanitize:
                raise SecurityViolationError(
                    f"输入不安全: {check_result.violations}",
                    risk_score=check_result.risk_score
                )
        else:
            safe_messages = messages

        # 2. 配额检查
        input_text = " ".join([msg.get("content", "") for msg in safe_messages])
        await self._enforce_quota("chat", user_id, input_text)

        # 3. 调用原始 LLM 服务 (带监控)
        start = time.monotonic()
        try:
            response = await self.llm_service.chat(
                safe_messages,
                model=model,
                temperature=temperature,
                task_type=task_type,
                user_id=user_id,
                **kwargs,
            )
        except Exception as exc:
            self._record_call_failure("chat", model, exc)
            self._record_call_metrics("chat", model, "error", time.monotonic() - start, input_text, "")
            raise

        elapsed = time.monotonic() - start
        # 4. 输出验证
        if self.config.enable_output_validation:
            validation_result = self.output_validator.validate(
                response,
                context={"user_id": user_id or "anonymous", "type": "chat"}
            )

            if not validation_result.is_valid:
                if self.monitor:
                    for violation in validation_result.violations:
                        if "敏感信息" in violation:
                            self.monitor.record_sensitive_leak(user_id or "anonymous", violation)
                        elif "XSS" in violation:
                            self.monitor.record_xss_attempt(user_id or "anonymous", violation)

                if validation_result.action == "block":
                    raise SecurityViolationError(
                        f"输出被阻断: {validation_result.violations}",
                        risk_score=1.0
                    )

                response = validation_result.sanitized_text

        # 5. 监控与用量记账
        self._record_call_metrics("chat", model, "success", elapsed, input_text, response)
        await self._record_usage(user_id, model, response)

        return cast("str", (response))

    async def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        conversation_history: list[dict] | None = None,
        *,
        user_id: str | None = None,
        # 兼容 kwarg：裸服务不接受 model，历史调用点传过 model= —— 显式接受并忽略
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        安全的带工具调用的聊天（签名与内层 LLMService.chat_with_tools 对齐）

        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            tools: 工具列表
            conversation_history: 对话历史
            user_id: 用户ID（提供时启用配额与用量记账）

        Returns:
            LLMResponse: 响应对象
        """
        # 1. 过滤系统提示和用户消息（sanitize_input 返回 SafetyCheckResult，非元组）
        if self.config.enable_input_filter:
            system_check = self.safety_service.sanitize_input(system_prompt, user_id or "anonymous")
            safe_system = system_check.sanitized_text if system_check.sanitized_text is not None else system_prompt
            user_check = self.safety_service.sanitize_input(user_message, user_id or "anonymous")
            safe_user_msg = user_check.sanitized_text if user_check.sanitized_text is not None else user_message

            if not user_check.is_safe and not self.config.auto_sanitize:
                raise SecurityViolationError(
                    f"用户消息不安全: {user_check.violations}",
                    risk_score=user_check.risk_score
                )

            # 过滤对话历史
            safe_history = None
            if conversation_history:
                safe_history = []
                for msg in conversation_history:
                    content_check = self.safety_service.sanitize_input(
                        msg.get("content", ""),
                        user_id or "anonymous"
                    )
                    safe_history.append({
                        "role": msg.get("role", "user"),
                        "content": content_check.sanitized_text if content_check.sanitized_text is not None else msg.get("content", "")
                    })
        else:
            safe_system = system_prompt
            safe_user_msg = user_message
            safe_history = conversation_history

        # 2. 配额检查
        total_text = f"{safe_system} {safe_user_msg}"
        if safe_history:
            total_text += " " + " ".join([msg.get("content", "") for msg in safe_history])
        await self._enforce_quota("chat_with_tools", user_id, total_text)

        # 3. 调用原始服务
        start = time.monotonic()
        try:
            response = await self.llm_service.chat_with_tools(
                system_prompt=safe_system,
                user_message=safe_user_msg,
                tools=tools,
                conversation_history=safe_history,
            )
        except Exception as exc:
            self._record_call_failure("chat_with_tools", None, exc)
            self._record_call_metrics("chat_with_tools", None, "error", time.monotonic() - start, total_text, "")
            raise

        elapsed = time.monotonic() - start
        output_text = ""
        if hasattr(response, 'content'):
            output_text = response.content if isinstance(response.content, str) else str(response.content)
        # 4. 输出验证
        if self.config.enable_output_validation and hasattr(response, 'content'):
            validation_result = self.output_validator.validate(
                response.content,
                context={"user_id": user_id or "anonymous", "type": "chat_with_tools"}
            )

            if not validation_result.is_valid:
                if self.monitor:
                    for violation in validation_result.violations:
                        if "敏感信息" in violation:
                            self.monitor.record_sensitive_leak(user_id or "anonymous", violation)

                if validation_result.action == "block":
                    raise SecurityViolationError(
                        f"输出被阻断: {validation_result.violations}",
                        risk_score=1.0
                    )

                response.content = validation_result.sanitized_text

        # 5. 监控与用量记账
        self._record_call_metrics("chat_with_tools", None, "success", elapsed, total_text, output_text)
        await self._record_usage(user_id, None, output_text)

        return response

    async def generate_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
        *,
        user_id: str | None = None,
    ) -> list[list[float]]:
        """
        安全的 Embedding 生成（texts-first，与裸 LLMService 对齐）。

        输入过滤 → 配额 → 内层调用 → 用量记账；user_id 缺省视为内部/批量调用，
        跳过配额但保留监控。
        """
        if self.config.enable_input_filter:
            safe_texts: list[str] = []
            for text in texts:
                result = self.safety_service.sanitize_input(text, user_id or "anonymous")
                safe_texts.append(result.sanitized_text if result.sanitized_text is not None else text)
        else:
            safe_texts = list(texts)

        input_text = " ".join(safe_texts)
        await self._enforce_quota("generate_embeddings", user_id, input_text)

        start = time.monotonic()
        try:
            embeddings = await self.llm_service.generate_embeddings(safe_texts, model=model)
        except Exception as exc:
            self._record_call_failure("generate_embeddings", model, exc)
            self._record_call_metrics(
                "generate_embeddings", model, "error", time.monotonic() - start, input_text, ""
            )
            raise

        self._record_call_metrics(
            "generate_embeddings", model, "success", time.monotonic() - start, input_text, ""
        )
        await self._record_usage(user_id, model or "embedding", "")
        return cast("list[list[float]]", (embeddings))

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        *,
        user_id: str | None = None,
        user_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        安全的流式聊天（签名与内层 LLMService.stream_chat 对齐）
        """
        if self.config.enable_input_filter:
            safe_messages, check_result = await self._filter_messages(user_id or "anonymous", messages)
            if not check_result.is_safe and not self.config.auto_sanitize:
                raise SecurityViolationError(
                    f"输入不安全: {check_result.violations}",
                    risk_score=check_result.risk_score
                )
        else:
            safe_messages = messages

        input_text = " ".join([msg.get("content", "") for msg in safe_messages])
        await self._enforce_quota(
            "stream_chat",
            self._resolve_user_id(user_id=user_id, user_context=user_context),
            input_text,
        )

        full_response = ""
        start = time.monotonic()
        # temperature 未显式指定时不向内层注入 None（内层默认/selection 决定，E2 语义）
        stream_kwargs: dict[str, Any] = dict(kwargs)
        if temperature is not None:
            stream_kwargs["temperature"] = temperature
        try:
            async for chunk in self.llm_service.stream_chat(
                safe_messages,
                model=model,
                user_context=user_context,
                **stream_kwargs,
            ):
                full_response += chunk
                yield chunk
        except Exception as exc:
            self._record_call_failure("stream_chat", model, exc)
            self._record_call_metrics("stream_chat", model, "error", time.monotonic() - start, input_text, full_response)
            raise

        elapsed = time.monotonic() - start
        # 完整响应验证
        if self.config.enable_output_validation:
            validation_result = self.output_validator.validate(
                full_response,
                context={"user_id": user_id or "anonymous", "type": "stream_chat"}
            )

            if not validation_result.is_valid:
                if self.monitor:
                    for violation in validation_result.violations:
                        if "敏感信息" in violation:
                            self.monitor.record_sensitive_leak(user_id or "anonymous", violation)

                # 流式响应无法回滚,只能记录警告
                logger.warning(
                    f"流式响应验证失败 - User: {user_id}, "
                    f"Violations: {validation_result.violations}"
                )

        self._record_call_metrics("stream_chat", model, "success", elapsed, input_text, full_response)
        await self._record_usage(
            self._resolve_user_id(user_id=user_id, user_context=user_context),
            model,
            full_response,
        )

    # =============================================================================
    # 显式审计旁路（配额[可识别身份时] + 监控 + 用量记账）
    # =============================================================================

    async def reason(self, *args: Any, **kwargs: Any) -> str:
        """审计旁路：推理模型调用。豁免论证见模块 docstring。"""
        return cast("str", (await self._run_audited("reason", self.llm_service.reason, args, kwargs)))

    async def reason_json(self, *args: Any, **kwargs: Any) -> Any | None:
        """审计旁路：推理模型 JSON 结构化输出。豁免论证见模块 docstring。"""
        return await self._run_audited("reason_json", self.llm_service.reason_json, args, kwargs)

    async def chat_json(self, *args: Any, **kwargs: Any) -> Any | None:
        """审计旁路：聊天模型 JSON 结构化输出。豁免论证见模块 docstring。"""
        return await self._run_audited("chat_json", self.llm_service.chat_json, args, kwargs)

    async def continue_with_tool_results(self, *args: Any, **kwargs: Any) -> Any:
        """审计旁路：工具结果回传续写。输入为前序安全调用产物，豁免论证见模块 docstring。"""
        return await self._run_audited(
            "continue_with_tool_results", self.llm_service.continue_with_tool_results, args, kwargs
        )

    async def generate_push_content(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        """审计旁路：系统内部推送文案生成，无终端用户身份。豁免论证见模块 docstring。"""
        return cast("dict[str, str]", (await self._run_audited(
            "generate_push_content", self.llm_service.generate_push_content, args, kwargs
        )))

    async def chat_stream_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        conversation_history: list[dict[str, Any]] | None = None,
        user_context: dict[str, Any] | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        """审计旁路：REST 流式工具聊天（chat.py SSE 主路径）。

        user_context 可解析身份时强制配额；内层已有 secure_messages/sanitize
        hygiene 层，此处不再双重改写输入；全程监控与用量记账。
        """
        user_id = self._resolve_user_id(user_context=user_context, **kwargs)
        model = kwargs.get("model")
        input_text = self._extract_input_text((), {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "conversation_history": conversation_history,
        })
        await self._enforce_quota("chat_stream_with_tools", user_id, input_text)

        collected_output: list[str] = []
        start = time.monotonic()
        try:
            async for chunk in self.llm_service.chat_stream_with_tools(
                system_prompt=system_prompt,
                user_message=user_message,
                tools=tools,
                conversation_history=conversation_history,
                user_context=user_context,
                temperature=temperature,
                **kwargs,
            ):
                content = getattr(chunk, "content", None)
                if isinstance(content, str) and getattr(chunk, "type", None) == "text":
                    collected_output.append(content)
                yield chunk
        except Exception as exc:
            self._record_call_failure("chat_stream_with_tools", model, exc)
            self._record_call_metrics(
                "chat_stream_with_tools", model, "error",
                time.monotonic() - start, input_text, "".join(collected_output),
            )
            raise

        output_text = "".join(collected_output)
        self._record_call_metrics(
            "chat_stream_with_tools", model, "success",
            time.monotonic() - start, input_text, output_text,
        )
        await self._record_usage(user_id, model, output_text)

    # =============================================================================
    # 内部辅助方法
    # =============================================================================

    async def _filter_messages(
        self,
        user_id: str,
        messages: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], SafetyCheckResult]:
        """过滤消息列表"""
        safe_messages = []
        total_violations = []
        max_risk = 0.0
        all_safe = True

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if not content:
                safe_messages.append(msg)
                continue

            # 过滤内容
            check_result = self.safety_service.sanitize_input(content, user_id)

            # 记录安全事件
            if not check_result.is_safe and self.monitor:
                for violation in check_result.violations:
                    if "提示注入" in violation:
                        self.monitor.record_injection_attempt(
                            user_id,
                            violation,
                            check_result.risk_score
                        )
                    elif "XSS" in violation:
                        self.monitor.record_xss_attempt(user_id, violation)

            # 累积结果
            safe_messages.append({
                "role": role,
                "content": check_result.sanitized_text
            })
            total_violations.extend(check_result.violations)
            max_risk = max(max_risk, check_result.risk_score)
            all_safe = all_safe and check_result.is_safe

        combined_result = SafetyCheckResult(
            is_safe=all_safe,
            sanitized_text=" ".join([msg["content"] for msg in safe_messages]),
            violations=total_violations,
            risk_score=max_risk
        )

        return safe_messages, combined_result


# =============================================================================
# 异常类
# =============================================================================

class SecurityViolationError(Exception):
    """安全违规异常"""
    def __init__(self, message: str, risk_score: float):
        self.risk_score = risk_score
        super().__init__(message)


class QuotaExceededError(Exception):
    """配额超限异常"""
    pass
