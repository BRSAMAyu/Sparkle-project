import asyncio
import inspect
import json
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from loguru import logger
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent_profiles import AgentRole, TaskType
from app.core.llm_router import LLMSelection, llm_router
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service
from app.services.llm.base import LLMProvider
from app.services.llm.providers import OpenAICompatibleProvider
from app.services.llm.fallback import FallbackReason, llm_fallback_manager
from app.services.llm.concurrency import llm_concurrency

# ==========================================
# 🎭 演示模式预设响应 (Demo Mock Responses)
# ==========================================
# 用于竞赛演示，确保关键流程 100% 成功且秒回
# 要启用: 在 .env 中设置 DEMO_MODE=true
#
# 💡 使用说明:
# 1. 在演示脚本中输入的文字必须与下面的 key 完全一致
# 2. 可以按需添加更多关键词和响应
# ==========================================

DEMO_MOCK_RESPONSES: dict[str, str] = {
    "帮我制定高数复习计划": """好的！基于你的学习情况，我为你制定了一个高效的高数复习计划。

📚 **高数冲刺复习计划**

根据艾宾浩斯遗忘曲线和你的知识星图分析，我发现你在以下几个知识点需要重点复习：

1. **极限与连续** - 掌握度较低，建议优先复习
2. **导数的应用** - 需要强化，特别是最值问题
3. **积分计算** - 基础还不错，做题巩固即可

我已为你生成以下任务卡片：

```json
{
  "actions": [
    {
      "type": "create_task",
      "data": {
        "title": "极限与连续重难点复习",
        "type": "learning",
        "estimated_minutes": 45,
        "priority": "high"
      }
    },
    {
      "type": "create_task",
      "data": {
        "title": "导数应用专题练习",
        "type": "training",
        "estimated_minutes": 30,
        "priority": "medium"
      }
    },
    {
      "type": "create_task",
      "data": {
        "title": "积分计算刷题",
        "type": "training",
        "estimated_minutes": 25,
        "priority": "normal"
      }
    }
  ]
}
```

建议按照上述顺序学习，先攻克弱项，再巩固强项。加油！🔥""",

    "我今天要学什么": """早上好！让我看看你的学习状态...

📊 **今日学习建议**

根据你的知识星图和遗忘曲线分析：

🔴 **需要复习** (掌握度下降):
- 线性代数：矩阵运算 (距上次学习已过 5 天)
- 高数：积分技巧 (掌握度降至 65%)

🟡 **今日推荐学习**:
- 概率论：条件概率 (按计划应今日学习)

💡 我建议你今天先花 20 分钟复习线代矩阵运算，然后再学习新内容。

需要我帮你创建今日学习任务吗？""",

    "这道题怎么做": """好的，让我来帮你分析这道题！

📝 **解题思路**

首先，我们需要识别题目的关键信息和考查的知识点。

一般来说，解题可以分为以下步骤：
1. **审题** - 明确已知条件和所求
2. **建模** - 建立数学模型或找到适用的公式
3. **计算** - 按步骤规范计算
4. **验证** - 检查结果是否合理

如果你能把具体的题目发给我，我可以给你更详细的解答和分析哦！

💡 小提示：遇到不会的题目，先尝试自己思考 5 分钟，这样学习效果更好！""",
}

@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"

@dataclass
class StreamChunk:
    type: str  # "text" | "tool_call_chunk" | "tool_call_end" | "usage"
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    arguments: str | None = None # For tool_call_chunk
    full_arguments: dict | None = None # For tool_call_end
    # Token usage fields
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

tracer = trace.get_tracer(__name__)

class LLMService:
    """
    LLM 服务 - 支持工具调用和动态模型选择

    新功能：
    - 根据 AgentRole 和 TaskType 动态选择模型
    - 兼容原有的 LLM_PROVIDER 环境变量配置
    - 自动降级策略
    - 可观测的模型选择日志

    向后兼容：
    - 保留原有的 chat/reason 模型划分
    - 无需修改现有调用代码
    """

    def __init__(
        self,
        agent_role: AgentRole | str | Any = AgentRole.GENERATION,
        enable_dynamic_routing: bool = True,
    ):
        """
        Args:
            agent_role: 当前服务代表的Agent角色（用于模型选择）
            enable_dynamic_routing: 是否启用动态路由（默认True）
                                 设为False则使用原有LLM_PROVIDER逻辑
        """
        self.agent_role = self._normalize_agent_role(agent_role)
        self.enable_dynamic_routing = enable_dynamic_routing
        self.demo_mode = bool(getattr(settings, 'DEMO_MODE', False))

        # 并发安全保护
        self._state_lock = asyncio.Lock()

        # 当前选中的模型配置
        self._current_selection: LLMSelection | None = None
        self._provider: LLMProvider | None = None

        # 向后兼容：保留原有的模型名称
        self.chat_model: str = ""
        self.reason_model: str = ""

        # GLM 特有参数
        self._extra_body: dict[str, Any] | None = None

        if enable_dynamic_routing:
            # 使用新的 LLMRouter
            self._init_with_router()
        else:
            # 使用原有的 LLM_PROVIDER 逻辑
            self._init_legacy()

    def _init_with_router(self):
        """使用 LLMRouter 初始化（推荐方式）"""
        selection = llm_router.select_model(self.agent_role)
        self._current_selection = selection

        kwargs = llm_router.get_openai_client_kwargs(selection)
        self._provider = OpenAICompatibleProvider(
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"]
        )

        self.chat_model = kwargs["model"]
        self.reason_model = kwargs["model"]  # 默认用同一个，可按需切换
        self._extra_body = kwargs.get("extra_body")  # 保存 GLM 特有参数
        if not kwargs.get("api_key"):
            self.demo_mode = True

        logger.info(
            f"[LLMRouter] {self.agent_role.value} → {kwargs['model']} "
            f"({selection.reason})"
        )
        if self._extra_body:
            logger.info(f"[LLMRouter] GLM extra_body: {self._extra_body}")

    def _init_legacy(self):
        """使用原有的 LLM_PROVIDER 环境变量初始化（向后兼容）"""
        provider_type = settings.LLM_PROVIDER.lower()

        if provider_type == "xiaomi":
            api_key = settings.XIAOMI_MIMO_API_KEY
            base_url = settings.XIAOMI_MIMO_BASE_URL
            self.chat_model = settings.XIAOMI_CHAT_MODEL
            self.reason_model = settings.XIAOMI_CHAT_MODEL
        elif provider_type == "deepseek":
            api_key = settings.DEEPSEEK_API_KEY
            base_url = settings.DEEPSEEK_BASE_URL
            self.chat_model = settings.DEEPSEEK_CHAT_MODEL
            self.reason_model = settings.DEEPSEEK_REASON_MODEL
        elif provider_type == "zhipu":
            api_key = settings.ZHIPU_API_KEY
            base_url = settings.ZHIPU_BASE_URL
            self.chat_model = settings.ZHIPU_CHAT_MODEL
            self.reason_model = settings.ZHIPU_TOOLS_MODEL
        else:
            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_API_BASE_URL
            self.chat_model = settings.LLM_MODEL_NAME
            self.reason_model = settings.LLM_REASON_MODEL_NAME or settings.LLM_MODEL_NAME

        self._provider = OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url
        )
        if not api_key:
            self.demo_mode = True

        logger.info(f"[Legacy] LLMService initialized with provider={provider_type}")

    async def _get_state_snapshot(self) -> dict[str, Any]:
        """
        获取状态快照（线程安全）

        Returns:
            Dict with provider, chat_model, reason_model, extra_body, current_selection
        """
        async with self._state_lock:
            return {
                "provider": self._provider,
                "chat_model": self.chat_model,
                "reason_model": self.reason_model,
                "extra_body": self._extra_body,
                "current_selection": self._current_selection,
            }

    @property
    def provider(self) -> LLMProvider:
        """获取当前provider（向后兼容）"""
        if self._provider is None:
            self._init_with_router()
        return self._provider

    @property
    def default_model(self) -> str:
        """获取默认模型（向后兼容）"""
        return self.chat_model

    async def switch_model_for_task(self, task_type: TaskType):
        """
        根据任务类型动态切换模型（线程安全）

        Args:
            task_type: 任务类型（如 TaskType.DEEP_REASONING）
        """
        if not self.enable_dynamic_routing:
            logger.warning("Dynamic routing is disabled, cannot switch model")
            return

        # 保护状态变更
        async with self._state_lock:
            selection = llm_router.select_model(self.agent_role, task_type)
            kwargs = llm_router.get_openai_client_kwargs(selection)

            self._provider = OpenAICompatibleProvider(
                api_key=kwargs["api_key"],
                base_url=kwargs["base_url"]
            )
            self.chat_model = kwargs["model"]
            self.reason_model = kwargs["model"]
            self._current_selection = selection
            self._extra_body = kwargs.get("extra_body")

            logger.info(
                f"[LLMRouter] Switched to {kwargs['model']} for task={task_type.value}"
            )

    def get_current_selection(self) -> LLMSelection | None:
        """获取当前的模型选择（用于观测）"""
        return self._current_selection

    @staticmethod
    def _normalize_agent_role(agent_role: AgentRole | str | Any) -> AgentRole:
        if isinstance(agent_role, AgentRole):
            return agent_role
        if isinstance(agent_role, str):
            role_value = agent_role.lower()
            role_aliases = {
                "math": AgentRole.MATH_AGENT,
                "code": AgentRole.CODE_AGENT,
                "writing": AgentRole.WRITING_AGENT,
                "science": AgentRole.SCIENCE_AGENT,
                "search": AgentRole.SEARCH_AGENT,
            }
            if role_value in role_aliases:
                return role_aliases[role_value]
            try:
                return AgentRole(role_value)
            except ValueError:
                return AgentRole.GENERATION
        role_value = getattr(agent_role, "value", None)
        if role_value:
            role_value = str(role_value).lower()
            role_aliases = {
                "math": AgentRole.MATH_AGENT,
                "code": AgentRole.CODE_AGENT,
                "writing": AgentRole.WRITING_AGENT,
                "science": AgentRole.SCIENCE_AGENT,
                "search": AgentRole.SEARCH_AGENT,
            }
            if role_value in role_aliases:
                return role_aliases[role_value]
            try:
                return AgentRole(role_value)
            except ValueError:
                return AgentRole.GENERATION
        return AgentRole.GENERATION

    def _check_demo_match(self, messages: list[dict[str, str]]) -> str | None:
        """
        检查是否匹配演示关键词

        Returns:
            匹配的预设响应，如果不匹配则返回 None
        """
        if not self.demo_mode:
            return None

        # 获取最后一条用户消息
        user_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_content = msg.get("content", "").strip()
                break

        if not user_content:
            return None

        # 精确匹配
        if user_content in DEMO_MOCK_RESPONSES:
            logger.info(f"⚡ [DEMO MODE] Exact match for: {user_content}")
            return DEMO_MOCK_RESPONSES[user_content]

        # 模糊匹配 (包含关键词)
        for key, response in DEMO_MOCK_RESPONSES.items():
            if key in user_content or user_content in key:
                logger.info(f"⚡ [DEMO MODE] Fuzzy match for: {user_content} -> {key}")
                return response
        logger.info("⚡ [DEMO MODE] No match found, returning generic response")
        return (
            "已收到你的请求。当前处于演示模式，我先给出一个可执行的通用建议：\n"
            "1) 先列出目标与截止时间；2) 拆分为每日/每周可完成的小步骤；"
            "3) 设定复盘节点并记录问题；4) 适当安排巩固与练习。\n"
            "如果你愿意，可以提供更多上下文（目标、时间、基础），我会给出更细的计划。"
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Send a chat request to the LLM with automatic fallback support.
        """
        model = model or self.chat_model
        with tracer.start_as_current_span("llm_chat") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature)

            # 🎭 Demo Mode 拦截
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                # 模拟思考延迟
                await asyncio.sleep(1.0)
                return mock_response

            if not self.provider:
                raise HTTPException(
                    status_code=501,
                    detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
                )

            logger.debug(f"Sending chat request to model: {model}")

            # 使用回退管理器执行请求
            async def _call_with_selection(selection: LLMSelection) -> str:
                # 获取 provider 名称用于并发控制
                provider_name = selection.config.provider.value

                # 💡 核心修复：为回退后的模型创建对应的 Provider 实例
                # 否则回退到 DeepSeek 时会继续使用 Zhipu 的 base_url
                current_provider = self.provider
                if selection != self._current_selection:
                    kwargs = llm_router.get_openai_client_kwargs(selection)
                    current_provider = OpenAICompatibleProvider(
                        api_key=kwargs["api_key"],
                        base_url=kwargs["base_url"]
                    )

                try:
                    async with llm_concurrency.acquire(provider_name):
                        response = await current_provider.chat(
                            messages,
                            model=selection.config.model_name,
                            temperature=selection.config.temperature,
                            **kwargs if 'kwargs' in locals() else {}
                        )
                        return response
                except Exception as e:
                    # 让回退管理器判断是否需要重试
                    reason = llm_fallback_manager._detect_fallback_reason(e)
                    if reason:
                        logger.warning(
                            f"[LLM] Request to {selection.config.model_name} failed: "
                            f"reason={reason.value}, will attempt fallback"
                        )
                    raise e

            try:
                # 检查熔断器
                await circuit_breaker_service.check("primary_llm")

                # 使用回退管理器执行
                if self._current_selection:
                    response = await llm_fallback_manager.execute_with_fallback(
                        self._current_selection,
                        _call_with_selection,
                        operation_type="chat",
                    )

                    # 记录成功
                    await circuit_breaker_service.record_success("primary_llm")
                    return response
                else:
                    # 没有当前选择，直接调用
                    response = await _call_with_selection(
                        type('obj', (object,), {'config': type('obj', (object,), {
                            'model_name': model,
                            'provider': type('obj', (object,), {'value': self._get_provider_name_from_url(), 'temperature': temperature})
                        })})
                    )
                    await circuit_breaker_service.record_success("primary_llm")
                    return response

            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)")
            except Exception as e:
                await circuit_breaker_service.record_failure("primary_llm")
                logger.error(f"LLM Chat Error: {e}")
                raise e

    def _get_provider_name_from_url(self) -> str:
        """从 provider 获取提供商名称"""
        if hasattr(self.provider, 'base_url'):
            url_lower = self.provider.base_url.lower()
            if "bigmodel" in url_lower or "zhipu" in url_lower:
                return "zhipu"
            elif "deepseek" in url_lower:
                return "deepseek"
            elif "xiaomi" in url_lower or "mimo" in url_lower:
                return "xiaomi"
            elif "dashscope" in url_lower or "aliyun" in url_lower:
                return "dashscope"
        return "default"

    async def reason(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs
    ) -> str:
        """
        Send a deep reasoning request to the LLM.
        """
        model = model or self.reason_model
        with tracer.start_as_current_span("llm_reason") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature)
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                await asyncio.sleep(1.0)
                return mock_response

            if not self.provider:
                raise HTTPException(
                    status_code=501,
                    detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
                )

            try:
                await circuit_breaker_service.check("primary_llm")
                response = await self.provider.chat(messages, model=model, temperature=temperature, **kwargs)
                await circuit_breaker_service.record_success("primary_llm")
                return response
            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)")
            except Exception as e:
                await circuit_breaker_service.record_failure("primary_llm")
                logger.error(f"LLM Reason Error (Circuit Breaker recording): {e}")
                raise e

    async def reason_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs
    ) -> Any:
        """
        Request JSON output from the LLM using reasoning model.
        """
        raw = await self.reason(messages, model=model, temperature=temperature, **kwargs)
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        def _extract_json_block(text: str) -> str | None:
            for start, end in (("{", "}"), ("[", "]")):
                if start in text and end in text:
                    return text[text.find(start):text.rfind(end) + 1]
            return None

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_json_block(cleaned)
            if extracted:
                return json.loads(extracted)
            logger.warning("Failed to parse JSON from LLM reasoning response, returning empty result")
            return {}

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Any:
        """
        Request JSON output from the LLM and parse it safely.
        """
        raw = await self.chat(messages, model=model, temperature=temperature, **kwargs)
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        def _extract_json_block(text: str) -> str | None:
            for start, end in (("{", "}"), ("[", "]")):
                if start in text and end in text:
                    return text[text.find(start):text.rfind(end) + 1]
            return None

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_json_block(cleaned)
            if extracted:
                return json.loads(extracted)
            logger.warning("Failed to parse JSON from LLM response, returning empty result")
            return {}

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        user_context: dict[str, Any] | None = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from the LLM with automatic fallback support.
        """
        with tracer.start_as_current_span("llm_stream_chat") as span:
            # 🎭 Demo Mode 拦截 - 流式返回预设响应
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                # 模拟流式输出，每次输出几个字符
                chunk_size = 10
                for i in range(0, len(mock_response), chunk_size):
                    chunk = mock_response[i:i + chunk_size]
                    yield chunk
                    # 模拟打字效果的延迟
                    await asyncio.sleep(0.03)
                return

            if self.demo_mode and not self.provider:
                span.set_attribute("llm.demo_mode", True)
                fallback = "（演示模式）当前未配置可用的 LLM 服务，请稍后再试。"
                chunk_size = 10
                for i in range(0, len(fallback), chunk_size):
                    yield fallback[i:i + chunk_size]
                    await asyncio.sleep(0.03)
                return

            if not self.provider:
                raise HTTPException(
                    status_code=501,
                    detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
                )

            import time as _time
            model = model or self.chat_model
            temperature = self._resolve_temperature(user_context, temperature)
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature)

            # Performance logging
            start_time = _time.perf_counter()
            first_chunk_time = None
            chunk_count = 0
            logger.info(f"[LLM] stream_chat START: model={model}, clear_thinking={self._extra_body}")

            # 定义流式调用函数
            async def _stream_with_selection(selection: LLMSelection) -> AsyncGenerator[str, None]:
                # 获取 provider 名称用于并发控制
                provider_name = selection.config.provider.value

                # 💡 核心修复：为回退后的模型创建对应的 Provider 实例
                current_provider = self.provider
                if selection != self._current_selection:
                    kwargs = llm_router.get_openai_client_kwargs(selection)
                    current_provider = OpenAICompatibleProvider(
                        api_key=kwargs["api_key"],
                        base_url=kwargs["base_url"]
                    )

                try:
                    async with llm_concurrency.acquire(provider_name):
                        async for chunk in current_provider.stream_chat(
                            messages,
                            model=selection.config.model_name,
                            temperature=selection.config.temperature,
                            **kwargs if 'kwargs' in locals() else {}
                        ):
                            yield chunk
                except Exception as e:
                    logger.error(f"[LLM] Stream processing failed for model {selection.config.model_name}: {e}")
                    raise e

            try:
                await circuit_breaker_service.check("primary_llm")

                # 流式回退处理（只在首次连接前）
                if self._current_selection:
                    # 使用回退管理器的流式方法
                    last_error = None
                    tried_models = set()

                    # 尝试原始模型
                    for attempt in range(llm_fallback_manager.max_fallback_attempts):
                        selection = self._current_selection

                        # 如果不是第一次尝试，获取回退候选
                        if attempt > 0:
                            candidates = llm_fallback_manager._get_fallback_candidates(
                                self._current_selection,
                                tried_models,
                            )
                            if not candidates:
                                break
                            selection = candidates[0]
                            tried_models.add(selection.config.model_name)
                            logger.info(f"[LLM] Fallback attempt {attempt}: trying {selection.config.model_name}")

                        try:
                            async for chunk in _stream_with_selection(selection):
                                chunk_count += 1
                                if first_chunk_time is None:
                                    first_chunk_time = _time.perf_counter()
                                    ttfc = (first_chunk_time - start_time) * 1000
                                    logger.info(f"[LLM] stream_chat FIRST_CHUNK: model={selection.config.model_name}, ttfc={ttfc:.0f}ms")
                                yield chunk

                            # 成功完成流式传输
                            await circuit_breaker_service.record_success("primary_llm")

                            # 记录回退成功
                            if attempt > 0:
                                logger.success(
                                    f"[LLM] Stream fallback SUCCESS: "
                                    f"final_model={selection.config.model_name}"
                                )
                            return  # 退出函数

                        except Exception as e:
                            last_error = e
                            reason = llm_fallback_manager._detect_fallback_reason(e)
                            if reason:
                                logger.warning(
                                    f"[LLM] Stream attempt {attempt + 1} failed: "
                                    f"model={selection.config.model_name}, reason={reason.value}"
                                )
                                model_key = llm_fallback_manager._get_model_key_from_selection(selection)
                                await llm_fallback_manager.health_tracker.record_failure(model_key, reason)
                                tried_models.add(model_key)
                                # 短暂延迟后重试
                                await asyncio.sleep(llm_fallback_manager._calculate_backoff_delay(attempt))
                            else:
                                # 非回退类型错误，直接抛出
                                raise e

                    # 所有尝试都失败
                    await circuit_breaker_service.record_failure("primary_llm")
                    if last_error:
                        raise last_error
                    raise HTTPException(status_code=503, detail="All LLM models unavailable")

                else:
                    # 没有当前选择，直接调用
                    async for chunk in self.provider.stream_chat(messages, model=model, temperature=temperature, **kwargs):
                        chunk_count += 1
                        if first_chunk_time is None:
                            first_chunk_time = _time.perf_counter()
                            ttfc = (first_chunk_time - start_time) * 1000
                            logger.info(f"[LLM] stream_chat FIRST_CHUNK: model={model}, ttfc={ttfc:.0f}ms")
                        yield chunk
                    await circuit_breaker_service.record_success("primary_llm")

            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)")
            except Exception as e:
                await circuit_breaker_service.record_failure("primary_llm")
                logger.error(f"LLM Stream Chat Error: {e}")
                raise e
            finally:
                elapsed = (_time.perf_counter() - start_time) * 1000
                logger.info(f"[LLM] stream_chat END: model={model}, elapsed={elapsed:.0f}ms, chunks={chunk_count}")

    async def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        conversation_history: list[dict] | None = None
    ) -> LLMResponse:
        """
        带工具调用的聊天
        """
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_chat_with_tools") as span:
                span.set_attribute("llm.model", self.default_model)

                # 构建 API 请求参数
                request_params = {
                    "model": self.default_model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.7,
                }

                # 添加 GLM 特有参数
                if self._extra_body:
                    request_params["extra_body"] = self._extra_body

                response = await self.provider.client.chat.completions.create(**request_params)

                choice = response.choices[0]
                message = choice.message

                if response.usage:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)

                tool_calls_dicts = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls_dicts.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        })

                return LLMResponse(
                    content=message.content or "",
                    tool_calls=tool_calls_dicts,
                    finish_reason=choice.finish_reason
                )
        else:
            raise NotImplementedError("Current LLM provider does not support tool calling directly.")

    async def continue_with_tool_results(
        self,
        conversation_history: list[dict],
        tool_results: list[dict]
    ) -> LLMResponse:
        """
        将工具执行结果反馈给 LLM，获取最终回复
        """
        messages = conversation_history[:]
        fallback_tool_call_ids: list[str] = []
        for msg in reversed(messages):
            if msg.get("role") != "assistant":
                continue
            tool_calls = msg.get("tool_calls") or []
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if isinstance(tc, dict) and tc.get("id"):
                        fallback_tool_call_ids.append(tc["id"])
            if fallback_tool_call_ids:
                break

        for idx, result in enumerate(tool_results):
            tool_message = {
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False)
            }
            tool_call_id = (
                (result.get("tool_call_id") if isinstance(result, dict) else None)
                or (result.get("id") if isinstance(result, dict) else None)
                or (fallback_tool_call_ids[idx] if idx < len(fallback_tool_call_ids) else None)
            )
            if tool_call_id:
                tool_message["tool_call_id"] = tool_call_id
            messages.append(tool_message)

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_continue_after_tools") as span:
                span.set_attribute("llm.model", self.default_model)

                # 构建 API 请求参数
                request_params = {
                    "model": self.default_model,
                    "messages": messages,
                    "temperature": 0.7,
                }

                # 添加 GLM 特有参数
                if self._extra_body:
                    request_params["extra_body"] = self._extra_body

                response = await self.provider.client.chat.completions.create(**request_params)
                choice = response.choices[0]
                message = choice.message

                if response.usage:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)

                return LLMResponse(
                    content=message.content or "",
                    tool_calls=None,
                    finish_reason=choice.finish_reason
                )
        else:
            raise NotImplementedError("Current LLM provider does not support tool calling directly.")

    async def chat_stream_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        user_context: dict[str, Any] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天（支持工具调用）
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        temperature = self._resolve_temperature(user_context, temperature)

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_chat_stream_with_tools") as span:
                span.set_attribute("llm.model", self.default_model)
                span.set_attribute("llm.temperature", temperature)

                # 构建 API 请求参数
                request_params = {
                    "model": self.default_model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True,
                    "temperature": temperature,
                    "stream_options": {"include_usage": True}
                }

                # 添加 GLM 特有参数
                if self._extra_body:
                    request_params["extra_body"] = self._extra_body

                stream = await self.provider.client.chat.completions.create(**request_params)

                collected_tool_call_chunks = {}
                usage_data = None

                async for chunk in stream:
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage_data = chunk.usage

                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield StreamChunk(type="text", content=delta.content)

                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                tool_call_id = tc_chunk.id
                                if tool_call_id not in collected_tool_call_chunks:
                                    collected_tool_call_chunks[tool_call_id] = {"name": "", "args_str": ""}
                                if tc_chunk.function.name:
                                    collected_tool_call_chunks[tool_call_id]["name"] = tc_chunk.function.name
                                    yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, tool_name=tc_chunk.function.name)
                                if tc_chunk.function.arguments:
                                    collected_tool_call_chunks[tool_call_id]["args_str"] += tc_chunk.function.arguments
                                    yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, arguments=tc_chunk.function.arguments)

                for tool_call_id, data in collected_tool_call_chunks.items():
                    if data["name"] and data["args_str"]:
                        try:
                            full_arguments = json.loads(data["args_str"])
                            yield StreamChunk(
                                type="tool_call_end",
                                tool_call_id=tool_call_id,
                                tool_name=data["name"],
                                full_arguments=full_arguments
                            )
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode tool arguments for {tool_call_id}: {data['args_str']}")

                if usage_data:
                    span.set_attribute("llm.usage.prompt_tokens", usage_data.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", usage_data.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", usage_data.total_tokens)
                    yield StreamChunk(
                        type="usage",
                        prompt_tokens=usage_data.prompt_tokens,
                        completion_tokens=usage_data.completion_tokens,
                        total_tokens=usage_data.total_tokens
                    )
        else:
            raise NotImplementedError("Current LLM provider does not support streamed tool calling directly.")

    @staticmethod
    def _resolve_temperature(user_context: dict[str, Any] | None, default: float) -> float:
        if not user_context or not isinstance(user_context, dict):
            return default
        llm_profile = user_context.get("llm_profile", {}) or {}
        if not isinstance(llm_profile, dict):
            return default
        try:
            return float(llm_profile.get("temperature", default))
        except (TypeError, ValueError):
            return default

    def is_thinking_mode(self) -> bool:
        """
        检查当前模型是否启用了思考模式 (clear_thinking=False)

        Returns:
            True 如果使用思考模式，False 否则
        """
        return self._extra_body is not None and self._extra_body.get("clear_thinking") is False

    async def generate_push_content(
        self,
        user_nickname: str,
        persona: str,
        trigger_type: str,
        context_data: dict,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
    ) -> dict[str, str]:
        """
        Generate "irresistible" push notification content based on persona.
        """
        if depth_preference > 0.7:
            detail_instruction = "Provide detailed context and concrete next steps."
        elif depth_preference < 0.3:
            detail_instruction = "Keep it extremely brief, one sentence if possible."
        else:
            detail_instruction = "Use moderate detail, 2-3 sentences."

        exploration_instruction = ""
        if curiosity_preference > 0.6:
            exploration_instruction = "Add one related fun fact or curiosity hook."

        persona_prompts = {
            "coach": f"Role: Strict Study Coach. Tone: Urgent, disciplined. {detail_instruction}",
            "anime": f"Role: Cute Anime Assistant. Tone: Sweet, encouraging, use emoticons. {detail_instruction}",
            "mentor": f"Role: Wise Mentor. Tone: Insightful, patient. {detail_instruction}",
            "friend": f"Role: Friendly Study Buddy. Tone: Casual, supportive. {detail_instruction}",
        }
        selected_persona_prompt = persona_prompts.get(persona, persona_prompts["coach"])
        if exploration_instruction:
            selected_persona_prompt = f"{selected_persona_prompt} {exploration_instruction}"

        trigger_desc = ""
        if trigger_type == "memory":
            nodes = ", ".join(context_data.get("nodes", []))
            trigger_desc = f"User is forgetting: {nodes}."
        elif trigger_type == "sprint":
            trigger_desc = f"Deadline approaching for plan '{context_data.get('plan_name')}'."
        elif trigger_type == "inactivity":
            trigger_desc = "User hasn't studied for over 24 hours."

        system_prompt = f"You are Sparkle, an AI Learning Assistant. {selected_persona_prompt} Context: {trigger_desc}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate push notification now."}
        ]

        try:
            with tracer.start_as_current_span("llm_generate_push") as span:
                span.set_attribute("llm.persona", persona)
                span.set_attribute("llm.trigger", trigger_type)

                response_text = await self.chat(messages, temperature=0.8)
                cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                content = json.loads(cleaned_text)
                return content
        except Exception as e:
            logger.error(f"Failed to generate push content: {e}")
            return {"title": "学习提醒", "body": f"{user_nickname}，该复习了。"}

# ==========================================
# 全局单例 - 向后兼容
# ==========================================

# 默认单例（使用新的动态路由）
llm_service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

# 创建专用角色的服务实例（按需使用）
def get_llm_service(agent_role: AgentRole | str) -> LLMService:
    """
    获取指定角色的LLM服务实例

    Args:
        agent_role: Agent角色（如 "galaxy_guide", "exam_oracle" 等）

    Example:
        # 在 galaxy_guide 节点中使用
        galaxy_llm = get_llm_service("galaxy_guide")
        response = await galaxy_llm.chat(messages)
    """
    return LLMService(agent_role=agent_role, enable_dynamic_routing=True)


async def get_configured_llm_service(
    agent_role: AgentRole | str,
    task_type: TaskType | None = None,
) -> LLMService:
    """
    获取已按角色/任务完成模型路由的 LLM 服务实例。

    该 helper 用于避免调用方只切换了 prompt / workflow，
    但底层仍落到全局 generation 模型。
    """
    service = get_llm_service(agent_role)
    if task_type is not None:
        await service.switch_model_for_task(task_type)
    return service


def get_llm_service_for_task(task_type: TaskType) -> LLMService:
    """
    获取适合特定任务的LLM服务实例

    Args:
        task_type: 任务类型（如 TaskType.DEEP_REASONING）

    Example:
        # 深度推理任务使用更强的模型
        reason_llm = get_llm_service_for_task(TaskType.DEEP_REASONING)
        response = await reason_llm.chat(messages)
    """
    from app.core.llm_router import select_model_for_task
    selection = select_model_for_task(task_type)
    return LLMService(agent_role=selection.agent_role, enable_dynamic_routing=True)


# ==========================================
# 种子内容库集成 (Seed Content Library Integration)
# ==========================================

async def build_prompt_with_seed_examples(
    system_prompt: str,
    user_message: str,
    user_id: str,
    subject: str | None = None,
    db: AsyncSession | None = None,
    count: int = 3,
) -> list[dict[str, str]]:
    """
    使用种子库的 few-shot 示例增强 prompt

    Args:
        system_prompt: 原始系统提示
        user_message: 用户消息
        user_id: 用户ID
        subject: 学科筛选
        db: 数据库会话 (可选)
        count: 需要的示例数量

    Returns:
        增强后的消息列表
    """
    from app.db.session import get_db
    from app.services.seed_library_service import SeedLibraryService

    messages = [{"role": "system", "content": system_prompt}]

    # 尝试获取 few-shot 示例
    if db is None:
        db_gen = get_db()
        db = await db_gen.__anext__()

    try:
        seed_service = SeedLibraryService()
        examples = await seed_service.get_few_shot_examples(
            db=db,
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            subject=subject,
            count=count,
        )

        if examples:
            # 添加 few-shot 示例到消息中
            few_shot_section = "以下是参考示例：\n\n"
            for i, example in enumerate(examples, 1):
                few_shot_section += f"### 示例 {i}\n"
                few_shot_section += f"**问题：** {example.get('input', '')}\n"
                few_shot_section += f"**解答：** {example.get('output', '')}\n"
                if example.get('explanation'):
                    few_shot_section += f"**说明：** {example['explanation']}\n"
                few_shot_section += "\n"

            # 将示例添加到系统提示后
            messages[0]["content"] = f"{system_prompt}\n\n{few_shot_section}"
            logger.debug(f"Added {len(examples)} few-shot examples to prompt")

    except Exception as e:
        logger.warning(f"Failed to fetch few-shot examples: {e}, using original prompt")
    finally:
        # db 是从 get_db() 获取的，不要关闭
        pass

    messages.append({"role": "user", "content": user_message})
    return messages


async def get_reply_template(
    template_key: str,
    user_id: str,
    language: str = "zh",
    db: AsyncSession | None = None,
) -> str | None:
    """
    获取回复模板

    Args:
        template_key: 模板标识
        user_id: 用户ID
        language: 语言
        db: 数据库会话 (可选)

    Returns:
        模板内容或 None
    """
    from app.db.session import get_db
    from app.services.seed_library_service import SeedLibraryService

    if db is None:
        db_gen = get_db()
        db = await db_gen.__anext__()

    try:
        seed_service = SeedLibraryService()
        template = await seed_service.get_reply_template(
            db=db,
            template_key=template_key,
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            language=language,
        )
        return template
    except Exception as e:
        logger.warning(f"Failed to fetch reply template '{template_key}': {e}")
        return None
