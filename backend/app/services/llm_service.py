"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from loguru import logger
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import routing_audit
from app.core.adaptive_routing import adaptive_routing_engine
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.cost_controller import is_llm_within_budget, record_llm_cost
from app.core.exceptions import LLMServiceError
from app.core.llm_monitoring import LLMMonitor
from app.core.llm_router import LLMSelection, ModelProvider, glm_effective_max_tokens, llm_router
from app.core.llm_secure_io import (
    refresh_llm_safety_mode,
    sanitize_llm_output,
    sanitize_text_for_llm,
    sanitize_tool_payload,
    secure_messages,
    wrap_tool_result,
    wrap_user_message,
)
from app.core.metrics import (
    LLM_PROVIDER_TTFT,
    LLM_PUSH_CONTENT_PARSE_FAILURE_TOTAL,
    LLM_ROUTER_CALL_LATENCY_SECONDS,
)
from app.core.trace_spine import current_recorder, current_trace_id, emit_span
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service
from app.services.llm.base import LLMProvider
from app.services.llm.concurrency import llm_concurrency
from app.services.llm.fallback import llm_fallback_manager
from app.services.llm.providers import OpenAICompatibleProvider

# ---------------------------------------------------------------------------
# M-2 stream variance guards (see round2/m2-stream-variance.md):
# The old code applied a single 120s/300s `stream_timeout` to the whole
# provider stream, so a provider TTFT tail (58s observed) plus SDK retries
# could hold a chat silently for 2 minutes before the fallback manager ever
# switched models. We now split the budget:
#   - FIRST_CHUNK_*: deadline for the *first* content chunk; expiry raises an
#     LLMServiceError whose message contains "timeout" so the existing
#     fallback manager classifies it as FallbackReason.TIMEOUT and switches
#     models instead of hanging.
#   - OVERALL_*: after the first chunk arrives the deadline is rescheduled to
#     now + OVERALL, keeping the original generous budget for chunk gaps /
#     long generations (reasoning models keep their larger budgets).
# Module-level so tests can shrink the windows.
# ---------------------------------------------------------------------------
LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS = 45
LLM_STREAM_FIRST_CHUNK_TIMEOUT_REASONING_SECONDS = 90
LLM_STREAM_OVERALL_TIMEOUT_SECONDS = 120
LLM_STREAM_OVERALL_TIMEOUT_REASONING_SECONDS = 300


def _report_call_outcome(
    selection: Any,
    *,
    success: bool,
    latency_ms: float | None = None,
    provider_name: str | None = None,
) -> None:
    """E-07/FIX-23：键型对齐的健康上报 + 真实调用结果回流。

    FIX-23（键型死键）：历史调用面按 ``config.model_name`` 上报健康，而选型按
    ``model_key`` 查 ``_is_model_healthy``——providers 路径的健康态在选型侧永远
    查不到（死键）。统一改为按注册 model_key 上报；只持有 config 的 legacy 路径
    经 ``llm_router.resolve_model_key`` 反查，反查不出则放弃（宁缺毋滥，不造死键）。

    同时把每次真实调用的 (latency, success, cost) 回流给三维自适应反馈环
    （quality/latency/cost），并写入路由审计与 Prometheus 时序指标。
    """
    model_key = getattr(selection, "model_key", None)
    if not model_key:
        model_key = llm_router.resolve_model_key(getattr(selection, "config", None))
    if not model_key:
        return
    if success:
        llm_router.report_model_success(model_key)
    else:
        llm_router.report_model_failure(model_key)

    config = getattr(selection, "config", None)
    provider_label = provider_name or (
        getattr(getattr(config, "provider", None), "value", None) or "unknown"
    )
    if latency_ms is not None:
        latency_ms = max(0.0, float(latency_ms))
        LLM_ROUTER_CALL_LATENCY_SECONDS.labels(
            provider=provider_label, model_key=model_key
        ).observe(latency_ms / 1000.0)
        cost = getattr(config, "cost_per_1k_tokens", None)
        adaptive_routing_engine.record_outcome(
            model_key,
            latency_ms=latency_ms,
            success=success,
            cost_per_1k=float(cost) if cost is not None else None,
        )
    routing_audit.record(
        "outcome",
        {
            "model_key": model_key,
            "provider": provider_label,
            "success": success,
            "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        },
    )

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
    # MIMO 特有字段
    reasoning_content: str | None = None   # 思考链内容
    annotations: list[dict] | None = None  # 联网搜索引用
    web_search_usage: dict | None = None   # 联网搜索用量

@dataclass
class StreamChunk:
    type: str  # "text" | "tool_call_chunk" | "tool_call_end" | "usage" | "reasoning" | "annotation"
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    arguments: str | None = None # For tool_call_chunk
    full_arguments: dict | None = None # For tool_call_end
    # Token usage fields
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    # MIMO 特有字段
    reasoning_content: str | None = None
    annotations: list[dict] | None = None

tracer = trace.get_tracer(__name__)
_llm_monitor = LLMMonitor()


def _record_token_usage(model: str, prompt_tokens: int, completion_tokens: int, source: str = "chat") -> None:
    """Record token usage and estimated cost to Prometheus + LLMMonitor."""
    try:
        _llm_monitor.estimate_and_record_cost(
            model=model, input_tokens=prompt_tokens,
            output_tokens=completion_tokens, endpoint=source,
        )
    except Exception:
        logger.opt(exception=True).warning("_record_token_usage: monitoring failed for model={}", model)


async def _track_daily_user_tokens(user_id: str | None, total_tokens: int) -> None:
    """Track per-user daily token usage in Redis for quota enforcement."""
    if not user_id or total_tokens <= 0:
        return
    try:
        from datetime import UTC, datetime

        from app.core.cache import cache_service
        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        redis_key = f"llm_tokens:{user_id}:{date_key}"
        r = cache_service.redis
        await r.incrby(redis_key, total_tokens)
        # Set 48h TTL on first write (in case key is new)
        ttl = await r.ttl(redis_key)
        if ttl is None or ttl < 0:
            await r.expire(redis_key, 48 * 3600)
    except Exception:
        logger.opt(exception=True).debug("_track_daily_user_tokens: redis failed")


_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*[ \t]*\n?|```")


def _extract_json_payload(text: str) -> str | None:
    """从 LLM 输出中稳健提取 JSON 对象文本（F-2）。

    处理三种常见形态：
    1. markdown fence 包裹（```json ... ```，语言标注大小写/省略均可）
    2. JSON 前后带解释性散文
    3. 纯 JSON

    返回首个花括号平衡的 JSON 对象字符串；无 JSON 时返回 None（空/纯文本）。
    """
    if not text or not text.strip():
        return None
    stripped = _FENCE_PATTERN.sub("", text).strip()
    start = stripped.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(stripped)):
        ch = stripped[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : idx + 1]
    return None


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
        initial_selection: LLMSelection | None = None,
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
        self._provider_error: str | None = None
        self._explicit_model_override = False

        # 向后兼容：保留原有的模型名称
        self.chat_model: str = ""
        self.reason_model: str = ""

        # GLM 特有参数
        self._extra_body: dict[str, Any] | None = None

        if enable_dynamic_routing:
            # 使用新的 LLMRouter
            self._init_with_router(initial_selection)
        else:
            # 使用原有的 LLM_PROVIDER 逻辑
            self._init_legacy()

    def _init_with_router(self, selection: LLMSelection | None = None):
        """使用 LLMRouter 初始化（推荐方式）"""
        selection = selection or llm_router.select_model(self.agent_role)
        self._current_selection = selection

        kwargs = llm_router.get_openai_client_kwargs(selection)
        try:
            self._provider = OpenAICompatibleProvider(
                api_key=kwargs["api_key"],
                base_url=kwargs["base_url"]
            )
            self._provider_error = None
        except Exception as exc:
            self._provider = None
            self._provider_error = str(exc)
            logger.exception("[LLMRouter] Failed to initialize provider")
            return

        self.chat_model = kwargs["model"]
        self.reason_model = kwargs["model"]  # 默认用同一个，可按需切换
        self._extra_body = kwargs.get("extra_body")  # 保存 GLM 特有参数
        self._explicit_model_override = False
        if not kwargs.get("api_key"):
            self.demo_mode = True
            logger.warning("LLM API key not configured, activating demo mode. Set LLM_API_KEY in environment for production.")

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
            base_url = settings.ZHIPU_CODING_BASE_URL
            self.chat_model = settings.ZHIPU_CHAT_MODEL
            self.reason_model = settings.ZHIPU_TOOLS_MODEL
        else:
            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_API_BASE_URL
            self.chat_model = settings.LLM_MODEL_NAME
            self.reason_model = settings.LLM_REASON_MODEL_NAME or settings.LLM_MODEL_NAME

        try:
            self._provider = OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url
            )
            self._provider_error = None
        except Exception as exc:
            self._provider = None
            self._provider_error = str(exc)
            logger.exception(f"[Legacy] Failed to initialize provider={provider_type}")
            return
        if not api_key:
            self.demo_mode = True
            logger.warning("LLM API key not configured, activating demo mode. Set LLM_API_KEY in environment for production.")

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
    def provider(self) -> LLMProvider | None:
        """获取当前provider（向后兼容，缓存结果）"""
        if self._provider is None and self._provider_error is None:
            self._init_with_router()
            # Cache the error state to prevent re-initialization on every access
            if self._provider is None and self._provider_error is None:
                self._provider_error = RuntimeError("Provider initialization returned None")
        return self._provider

    @property
    def default_model(self) -> str:
        """获取默认模型（向后兼容）"""
        return self.chat_model

    @property
    def model_key(self) -> str:
        """获取当前选中的注册模型 key。"""
        return self._current_selection.model_key if self._current_selection else ""

    @property
    def provider_name(self) -> str:
        """获取当前选中模型的 provider 名称。"""
        if self._current_selection is not None:
            return self._current_selection.config.provider.value
        return self._get_provider_name_from_url()

    async def switch_model_for_task(
        self,
        task_type: TaskType,
        avoid_providers: list[ModelProvider] | None = None,
        reasoning_mode: str | None = None,
    ):
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
            selection = llm_router.select_model(
                self.agent_role,
                task_type,
                avoid_providers=avoid_providers,
                reasoning_mode=reasoning_mode,
            )
            kwargs = llm_router.get_openai_client_kwargs(selection)

            self._provider = OpenAICompatibleProvider(
                api_key=kwargs["api_key"],
                base_url=kwargs["base_url"]
            )
            self.chat_model = kwargs["model"]
            self.reason_model = kwargs["model"]
            self._current_selection = selection
            self._extra_body = kwargs.get("extra_body")
            self._explicit_model_override = False

            logger.info(
                f"[LLMRouter] Switched to {kwargs['model']} for task={task_type.value}"
            )

    async def switch_to_specific_model(self, model_key: str):
        """切换到指定模型 key。用于 batch / specialist 等显式路由场景。"""
        if not self.enable_dynamic_routing:
            logger.warning("Dynamic routing is disabled, cannot switch to a specific model")
            return

        async with self._state_lock:
            selection = llm_router.select_specific_model(model_key, agent_role=self.agent_role)
            kwargs = llm_router.get_openai_client_kwargs(selection)

            self._provider = OpenAICompatibleProvider(
                api_key=kwargs["api_key"],
                base_url=kwargs["base_url"]
            )
            self.chat_model = kwargs["model"]
            self.reason_model = kwargs["model"]
            self._current_selection = selection
            self._extra_body = kwargs.get("extra_body")
            self._explicit_model_override = True
            # 显式切换后按新 provider 的 key 状态重估 demo 模式：
            # 否则初始 selection 无 key 时激活的 demo_mode 会被永久带进后续
            # 显式模型调用——glm_batch 任务切换到有 key 的模型仍输出演示文案
            # （wt9 全链实测踩中：minimax_m3_batch 调用被 demo 短路返回通用回复）。
            self.demo_mode = not getattr(self._provider, "has_api_key", True)

            logger.info(f"[LLMRouter] Switched to specific model {model_key} -> {kwargs['model']}")

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

        # 模糊匹配 (包含关键词) - requires minimum length to avoid false matches
        if len(user_content) >= 3:
            for key, response in DEMO_MOCK_RESPONSES.items():
                if len(key) >= 3 and (key in user_content or user_content in key):
                    logger.info(f"⚡ [DEMO MODE] Fuzzy match for: {user_content} -> {key}")
                    return response
        logger.info("⚡ [DEMO MODE] No match found, returning generic response")
        return (
            "已收到你的请求。当前处于演示模式，我先给出一个可执行的通用建议：\n"
            "1) 先列出目标与截止时间；2) 拆分为每日/每周可完成的小步骤；"
            "3) 设定复盘节点并记录问题；4) 适当安排巩固与练习。\n"
            "如果你愿意，可以提供更多上下文（目标、时间、基础），我会给出更细的计划。"
        )

    @staticmethod
    def _resolve_user_id(**kwargs: Any) -> str | None:
        user_id = kwargs.get("user_id")
        if user_id:
            return str(user_id)
        user_context = kwargs.get("user_context")
        if isinstance(user_context, dict):
            candidate = user_context.get("user_id") or user_context.get("uid")
            if candidate:
                return str(candidate)
        return None

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        *,
        task_type: TaskType | None = None,
        **kwargs
    ) -> str:
        """
        Send a chat request to the LLM with automatic fallback support.

        Args:
            task_type: Optional task type for cascade routing. When provided
                       with dynamic routing enabled, selects the appropriate
                       model tier (e.g. ROUTING → FAST, STANDARD_RESPONSE → STANDARD).
            temperature: E2 — None 表示未显式指定，使用路由 selection 的配置值；
                         caller 显式传入的值优先于 selection 配置。
        """
        await refresh_llm_safety_mode()
        kwargs = dict(kwargs)
        user_id = self._resolve_user_id(**kwargs)
        kwargs.pop("user_id", None)
        safe_messages = secure_messages(
            messages,
            user_id=user_id,
            wrap_user_messages=True,
        )
        model = model or self.chat_model

        # Cascade routing: when task_type is provided, select tier-appropriate model
        cascade_selection: LLMSelection | None = None
        if (
            task_type is not None
            and self.enable_dynamic_routing
            and model == self.chat_model
        ):
            try:
                cascade_selection = llm_router.select_model(self.agent_role, task_type)
                model = cascade_selection.config.model_name
            except Exception as exc:
                logger.debug(f"Cascade model selection failed: {exc}")

        with tracer.start_as_current_span("llm_chat") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature if temperature is not None else 0.7)

            # 🎭 Demo Mode 拦截
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                # 模拟思考延迟
                await asyncio.sleep(1.0)
                return mock_response

            # Budget preflight: fail fast if LLM daily budget is exhausted
            if not await is_llm_within_budget():
                logger.warning("LLM daily budget exhausted, returning fallback response")
                raise HTTPException(
                    status_code=429,
                    detail="Daily AI usage limit reached. Your budget will reset tomorrow.",
                )

            if not self.provider:
                raise HTTPException(
                    status_code=501,
                    detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
                )

            logger.debug(f"Sending chat request to model: {model}")

            # 使用回退管理器执行请求
            async def _call_with_selection(selection: LLMSelection) -> str:
                provider_name, current_provider, request_kwargs = self._build_provider_for_selection(selection)

                _outcome_t0 = time.perf_counter()
                try:
                    async with llm_concurrency.acquire(provider_name):
                        async with asyncio.timeout(120):
                            response = await current_provider.chat(
                                safe_messages,
                                model=selection.config.model_name,
                                temperature=(
                                    temperature if temperature is not None else selection.config.temperature
                                ),
                                **request_kwargs
                            )
                        _report_call_outcome(
                            selection,
                            success=True,
                            latency_ms=(time.perf_counter() - _outcome_t0) * 1000.0,
                            provider_name=provider_name,
                        )
                        return sanitize_llm_output(
                            response,
                            context={"user_id": user_id, "type": "chat"},
                        )
                except Exception as e:
                    _report_call_outcome(
                        selection,
                        success=False,
                        latency_ms=(time.perf_counter() - _outcome_t0) * 1000.0,
                        provider_name=provider_name,
                    )
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
                active_selection = cascade_selection or self._current_selection
                if active_selection:
                    response = await llm_fallback_manager.execute_with_fallback(
                        active_selection,
                        _call_with_selection,
                        operation_type="chat",
                    )

                    # 记录成功
                    await circuit_breaker_service.record_success("primary_llm")
                    return response
                else:
                    # No current selection — use legacy provider path
                    logger.warning("No LLM selection available, using legacy provider")
                    response = await _call_with_selection(
                        type('obj', (object,), {'config': type('obj', (object,), {
                            'model_name': model,
                            'temperature': temperature if temperature is not None else 0.7,
                            'provider': type('obj', (object,), {'value': self._get_provider_name_from_url()})
                        })})
                    )
                    await circuit_breaker_service.record_success("primary_llm")
                    return response

            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)") from None
            except Exception as e:
                await circuit_breaker_service.record_failure("primary_llm")
                # BATCH-CAP（PROD-LOG2 ②-2）：str(e) 为空的异常（如 TimeoutError()）
                # 曾产出 23 条不可诊断的 "LLM Chat Error: " —— 兜底出类型名并附
                # traceback（照 wt182 reviewer 先例 + EXC-TRACEBACK 迁移同法）。
                error_detail = str(e).strip() or type(e).__name__
                logger.opt(exception=True).error(f"LLM Chat Error: {error_detail}")
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

    def _selection_matches_current(self, selection: LLMSelection) -> bool:
        current = self._current_selection
        if current is None:
            return False
        return (
            current.model_key == selection.model_key
            and current.config.provider == selection.config.provider
            and current.config.base_url == selection.config.base_url
            and current.config.model_name == selection.config.model_name
            and current.config.clear_thinking == selection.config.clear_thinking
        )

    def _build_provider_for_selection(
        self,
        selection: LLMSelection,
    ) -> tuple[str, OpenAICompatibleProvider | LLMProvider, dict[str, Any]]:
        provider_name = selection.config.provider.value
        client_kwargs = llm_router.get_openai_client_kwargs(selection)
        request_kwargs = {
            key: value
            for key, value in client_kwargs.items()
            if key not in {"api_key", "base_url", "model", "temperature"}
        }

        if self._selection_matches_current(selection):
            current_provider = self.provider
        else:
            current_provider = OpenAICompatibleProvider(
                api_key=client_kwargs["api_key"],
                base_url=client_kwargs["base_url"]
            )

        return provider_name, current_provider, request_kwargs

    async def _create_raw_completion(
        self,
        selection: LLMSelection,
        request_params: dict[str, Any],
    ) -> Any:
        provider_name, current_provider, request_kwargs = self._build_provider_for_selection(selection)
        params = dict(request_params)
        params["model"] = selection.config.model_name
        params.setdefault("temperature", selection.config.temperature)
        for key, value in request_kwargs.items():
            params.setdefault(key, value)

        # V3-FIX-04: GLM 思考车道 max_tokens 留量（caller 显式小预算可被思考清空 → 空回复）
        params["max_tokens"] = glm_effective_max_tokens(
            selection.config.provider,
            selection.config.base_url,
            selection.config.clear_thinking,
            params.get("max_tokens"),
        )

        # 添加 MIMO 特有参数：联网搜索和思考模式
        if selection.config.enable_web_search:
            params.setdefault("tools", [])
            params["tools"].append({"type": "web_search"})
        # TTFT-CFG: 思考控制按 provider 分叉——DashScope 走 enable_thinking（已在
        # get_openai_client_kwargs 注入），不再叠加 GLM 风格 thinking:{}（对其无效）；
        # 其余 provider（GLM/MIMO/DeepSeek）保持现有 thinking:{} 发送不变。
        if (
            selection.config.thinking_mode
            and selection.config.provider is not ModelProvider.DASHSCOPE
        ):
            extra_body = dict(params.get("extra_body") or {})
            extra_body["thinking"] = {"type": selection.config.thinking_mode}
            params["extra_body"] = extra_body

        if not hasattr(current_provider, "client"):
            raise NotImplementedError("Current LLM provider does not expose raw chat completions.")

        async with llm_concurrency.acquire(provider_name):
            return await current_provider.client.chat.completions.create(**params)

    async def _create_raw_completion_with_fallback(
        self,
        selection: LLMSelection,
        request_params: dict[str, Any],
        operation_type: str,
    ) -> Any:
        async def _call(current_selection: LLMSelection) -> Any:
            return await self._create_raw_completion(current_selection, request_params)

        # E-02 能力兼容：带工具 schema 的调用，fallback 候选保持在主聊天能力层，
        # 不得降到 FREE*/GLM_BATCH/SPECIALIST 造成"会说话但不能执行"的假完成。
        return await llm_fallback_manager.execute_with_fallback(
            selection,
            _call,
            operation_type=operation_type,
            require_tools=bool(request_params.get("tools")),
        )

    async def _create_raw_stream(
        self,
        selection: LLMSelection,
        request_params: dict[str, Any],
    ) -> AsyncGenerator[Any, None]:
        provider_name, current_provider, request_kwargs = self._build_provider_for_selection(selection)
        params = dict(request_params)
        params["model"] = selection.config.model_name
        params.setdefault("temperature", selection.config.temperature)
        for key, value in request_kwargs.items():
            params.setdefault(key, value)

        # V3-FIX-04: GLM 思考车道 max_tokens 留量（caller 显式小预算可被思考清空 → 空回复）
        params["max_tokens"] = glm_effective_max_tokens(
            selection.config.provider,
            selection.config.base_url,
            selection.config.clear_thinking,
            params.get("max_tokens"),
        )

        # 添加 MIMO 特有参数：联网搜索和思考模式
        if selection.config.enable_web_search:
            params.setdefault("tools", [])
            params["tools"].append({"type": "web_search"})
        # TTFT-CFG: 思考控制按 provider 分叉——DashScope 走 enable_thinking（已在
        # get_openai_client_kwargs 注入），不再叠加 GLM 风格 thinking:{}（对其无效）；
        # 其余 provider（GLM/MIMO/DeepSeek）保持现有 thinking:{} 发送不变。
        if (
            selection.config.thinking_mode
            and selection.config.provider is not ModelProvider.DASHSCOPE
        ):
            extra_body = dict(params.get("extra_body") or {})
            extra_body["thinking"] = {"type": selection.config.thinking_mode}
            params["extra_body"] = extra_body

        if not hasattr(current_provider, "client"):
            raise NotImplementedError("Current LLM provider does not expose raw chat completions.")

        # M-2 stream variance: this is the raw stream behind
        # chat_stream_with_tools (main chat generation). Same two-stage
        # deadline as stream_chat._stream_with_selection — a bounded window
        # for the first chunk (raising a fallback-eligible "timeout" error
        # instead of hanging), then the generous overall budget.
        model_name = str(params["model"])
        is_deep_reasoning = "reason" in model_name.lower() or "thinking" in model_name.lower()
        overall_timeout = (
            LLM_STREAM_OVERALL_TIMEOUT_REASONING_SECONDS
            if is_deep_reasoning
            else LLM_STREAM_OVERALL_TIMEOUT_SECONDS
        )
        first_chunk_timeout = (
            LLM_STREAM_FIRST_CHUNK_TIMEOUT_REASONING_SECONDS
            if is_deep_reasoning
            else LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS
        )

        try:
            async with llm_concurrency.acquire(provider_name):
                loop = asyncio.get_running_loop()
                ttft_started = time.perf_counter()
                async with asyncio.timeout(first_chunk_timeout) as stream_deadline:
                    got_first_chunk = False
                    stream = await current_provider.client.chat.completions.create(**params)
                    async for chunk in stream:
                        if not got_first_chunk:
                            got_first_chunk = True
                            stream_deadline.reschedule(loop.time() + overall_timeout)
                            # M-2: provider-level TTFT probe for the raw path.
                            LLM_PROVIDER_TTFT.labels(provider=provider_name, model=model_name).observe(
                                time.perf_counter() - ttft_started
                            )
                        yield chunk
        except TimeoutError:
            # asyncio.timeout expiry. The message MUST contain "timeout" so
            # llm_fallback_manager._detect_fallback_reason maps it to
            # FallbackReason.TIMEOUT and switches models.
            logger.warning(
                f"[LLM] Raw stream timeout for model {model_name} "
                f"(first_chunk_timeout={first_chunk_timeout}s, overall={overall_timeout}s), triggering fallback"
            )
            raise LLMServiceError(
                f"LLM stream timeout: model {model_name} exceeded "
                f"first-chunk window ({first_chunk_timeout}s)"
            ) from None

    async def _create_raw_stream_with_fallback(
        self,
        selection: LLMSelection,
        request_params: dict[str, Any],
        operation_type: str,
    ) -> AsyncGenerator[Any, None]:
        async def _stream(current_selection: LLMSelection) -> AsyncGenerator[Any, None]:
            async for chunk in self._create_raw_stream(current_selection, request_params):
                yield chunk

        # E-02 能力兼容：带工具 schema 的流式调用，fallback 候选保持在主聊天能力层。
        async for chunk in llm_fallback_manager.execute_stream_with_fallback(
            selection,
            _stream,
            operation_type=operation_type,
            require_tools=bool(request_params.get("tools")),
        ):
            yield chunk

    async def reason(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        **kwargs
    ) -> str:
        """
        Send a deep reasoning request to the LLM.

        E2: `temperature=None` 表示未显式指定，使用路由 selection 的配置值；
        caller 显式传入的 temperature 优先于 selection 配置。
        """
        await refresh_llm_safety_mode()
        kwargs = dict(kwargs)
        user_id = self._resolve_user_id(**kwargs)
        kwargs.pop("user_id", None)
        safe_messages = secure_messages(
            messages,
            user_id=user_id,
            wrap_user_messages=True,
        )
        requested_model = model
        resolved_model = model or self.reason_model
        with tracer.start_as_current_span("llm_reason") as span:
            span.set_attribute("llm.model", resolved_model)
            span.set_attribute("llm.temperature", temperature if temperature is not None else 0.2)
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
                if self.enable_dynamic_routing and requested_model is None:
                    if self._explicit_model_override and self._current_selection is not None:
                        selection = self._current_selection
                    else:
                        selection = llm_router.select_model(self.agent_role, TaskType.DEEP_REASONING)

                    async def _call_with_selection(current_selection: LLMSelection) -> str:
                        provider_name, current_provider, request_kwargs = self._build_provider_for_selection(current_selection)
                        merged_kwargs = dict(kwargs)
                        for key, value in request_kwargs.items():
                            merged_kwargs.setdefault(key, value)
                        _outcome_t0 = time.perf_counter()
                        try:
                            async with llm_concurrency.acquire(provider_name):
                                async with asyncio.timeout(180):
                                    result = await current_provider.chat(
                                        safe_messages,
                                        model=current_selection.config.model_name,
                                        temperature=(
                                            temperature if temperature is not None else current_selection.config.temperature
                                        ),
                                        **merged_kwargs,
                                    )
                            _report_call_outcome(
                                current_selection,
                                success=True,
                                latency_ms=(time.perf_counter() - _outcome_t0) * 1000.0,
                                provider_name=provider_name,
                            )
                            return result
                        except Exception:
                            _report_call_outcome(
                                current_selection,
                                success=False,
                                latency_ms=(time.perf_counter() - _outcome_t0) * 1000.0,
                                provider_name=provider_name,
                            )
                            raise

                    response = await llm_fallback_manager.execute_with_fallback(
                        selection,
                        _call_with_selection,
                        operation_type="reason",
                    )
                else:
                    async with asyncio.timeout(180):
                        response = await self.provider.chat(
                            safe_messages,
                            model=resolved_model,
                            temperature=temperature if temperature is not None else 0.2,
                            **kwargs,
                        )
                await circuit_breaker_service.record_success("primary_llm")
                return sanitize_llm_output(
                    response,
                    context={"user_id": user_id, "type": "reason"},
                )
            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)") from None
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
    ) -> Any | None:
        """
        Request JSON output from the LLM using reasoning model.
        """
        raw = await self.reason(messages, model=model, temperature=temperature, **kwargs)
        return self._parse_json_payload(raw, response_kind="reasoning")

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Any | None:
        """
        Request JSON output from the LLM and parse it safely.
        """
        raw = await self.chat(messages, model=model, temperature=temperature, **kwargs)
        return self._parse_json_payload(raw, response_kind="chat")

    @staticmethod
    def _parse_json_payload(raw: str, *, response_kind: str) -> Any | None:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        # 思维链剥离：推理模型经 OpenAI 兼容路径（MiniMax-M3 实测）会把 <think>…</think>
        # 内联在 content 头部；思维链文本若含花括号，下方 _extract_json_block 的首个
        # '{' 会锚定到思维链内部导致提取失败。剥掉前缀思维链后再走原提取逻辑。
        if cleaned.startswith("<think>"):
            end_idx = cleaned.find("</think>")
            cleaned = cleaned[end_idx + len("</think>"):].strip() if end_idx >= 0 else cleaned[len("<think>"):].strip()

        def _extract_json_block(text: str) -> str | None:
            for start_ch, end_ch in (("{", "}"), ("[", "]")):
                start_idx = text.find(start_ch)
                if start_idx < 0:
                    continue
                last_close = text.rfind(end_ch)
                if last_close <= start_idx:
                    continue
                # Try progressively shorter substrings from each closing bracket
                for end_idx in range(last_close, start_idx, -1):
                    if text[end_idx] != end_ch:
                        continue
                    candidate = text[start_idx:end_idx + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        continue
            return None

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_json_block(cleaned)
            if extracted:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from LLM {} response", response_kind)
            return None

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
        await refresh_llm_safety_mode()
        user_id = self._resolve_user_id(user_context=user_context, **kwargs)
        safe_messages = secure_messages(
            messages,
            user_id=user_id,
            wrap_user_messages=True,
        )
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

            # Budget preflight: fail fast if LLM daily budget is exhausted
            if not await is_llm_within_budget():
                logger.warning("LLM daily budget exhausted, raising error")
                raise RuntimeError(
                    "LLM_DAILY_BUDGET_EXHAUSTED: Daily AI usage quota exhausted. "
                    "Quota resets at midnight."
                )

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
                provider_name, current_provider, request_kwargs = self._build_provider_for_selection(selection)

                is_deep_reasoning = "reason" in selection.config.model_name.lower() or "thinking" in selection.config.model_name.lower()
                overall_timeout = (
                    LLM_STREAM_OVERALL_TIMEOUT_REASONING_SECONDS
                    if is_deep_reasoning
                    else LLM_STREAM_OVERALL_TIMEOUT_SECONDS
                )
                first_chunk_timeout = (
                    LLM_STREAM_FIRST_CHUNK_TIMEOUT_REASONING_SECONDS
                    if is_deep_reasoning
                    else LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS
                )

                try:
                    async with llm_concurrency.acquire(provider_name):
                        loop = asyncio.get_running_loop()
                        # M-2: two-stage deadline — strict window for the first
                        # content chunk (falls back to another model instead of
                        # hanging), then the generous overall budget for the
                        # remainder of the stream.
                        async with asyncio.timeout(first_chunk_timeout) as stream_deadline:
                            got_first_chunk = False
                            async for chunk in current_provider.stream_chat(
                                safe_messages,
                                model=selection.config.model_name,
                                temperature=selection.config.temperature,
                                **request_kwargs
                            ):
                                if not got_first_chunk:
                                    got_first_chunk = True
                                    stream_deadline.reschedule(loop.time() + overall_timeout)
                                yield chunk
                except TimeoutError:
                    # asyncio.timeout expiry. The message MUST contain "timeout"
                    # so llm_fallback_manager._detect_fallback_reason maps it to
                    # FallbackReason.TIMEOUT and switches models.
                    stage = "first-chunk" if not got_first_chunk else "mid-stream"
                    logger.warning(
                        f"[LLM] Stream timeout ({stage}) for model {selection.config.model_name} "
                        f"(first_chunk_timeout={first_chunk_timeout}s, overall={overall_timeout}s), triggering fallback"
                    )
                    raise LLMServiceError(
                        f"LLM stream timeout: model {selection.config.model_name} exceeded "
                        f"{stage} window (first_chunk={first_chunk_timeout}s, overall={overall_timeout}s)"
                    ) from None
                except Exception as e:
                    logger.error(f"[LLM] Stream processing failed for model {selection.config.model_name}: {e}")
                    raise e

            try:
                await circuit_breaker_service.check("primary_llm")

                # 流式回退处理（只在首次连接前）
                if self._current_selection:
                    async for chunk in llm_fallback_manager.execute_stream_with_fallback(
                        self._current_selection,
                        _stream_with_selection,
                        operation_type="stream_chat",
                    ):
                        chunk_count += 1
                        if first_chunk_time is None:
                            first_chunk_time = _time.perf_counter()
                            ttfc = (first_chunk_time - start_time) * 1000
                            logger.info(f"[LLM] stream_chat FIRST_CHUNK: ttfc={ttfc:.0f}ms")
                        yield chunk
                    await circuit_breaker_service.record_success("primary_llm")
                    return

                else:
                    # 没有当前选择，直接调用
                    async for chunk in self.provider.stream_chat(safe_messages, model=model, temperature=temperature, **kwargs):
                        chunk_count += 1
                        if first_chunk_time is None:
                            first_chunk_time = _time.perf_counter()
                            ttfc = (first_chunk_time - start_time) * 1000
                            logger.info(f"[LLM] stream_chat FIRST_CHUNK: model={model}, ttfc={ttfc:.0f}ms")
                        yield chunk
                    await circuit_breaker_service.record_success("primary_llm")

            except CircuitBreakerOpenException:
                logger.warning("Circuit breaker OPEN for primary_llm. Fast failing.")
                raise HTTPException(status_code=503, detail="LLM Service Temporarily Unavailable (Circuit Open)") from None
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
        await refresh_llm_safety_mode()
        user_id = self._resolve_user_id()
        safe_system_prompt = sanitize_text_for_llm(system_prompt, user_id=user_id)
        safe_user_message = wrap_user_message(sanitize_text_for_llm(user_message, user_id=user_id))

        messages = [{"role": "system", "content": safe_system_prompt}]

        if conversation_history:
            messages.extend(
                secure_messages(
                    conversation_history,
                    user_id=user_id,
                    wrap_user_messages=True,
                    wrap_tool_messages=True,
                )
            )

        if not self._history_ends_with_user_message(conversation_history, user_message):
            messages.append({"role": "user", "content": safe_user_message})

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

                selection = self._current_selection
                if selection:
                    response = await self._create_raw_completion_with_fallback(
                        selection,
                        request_params,
                        operation_type="chat_with_tools",
                    )
                else:
                    response = await self.provider.client.chat.completions.create(**request_params)

                choice = response.choices[0]
                message = choice.message

                if response.usage and selection is not None:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)
                    _record_token_usage(
                        selection.model_key, response.usage.prompt_tokens,
                        response.usage.completion_tokens, source="chat_with_tools",
                    )
                    await record_llm_cost(
                        selection.model_key, response.usage.prompt_tokens,
                        response.usage.completion_tokens, source="chat_with_tools",
                    )
                    await _track_daily_user_tokens(user_id, response.usage.total_tokens or 0)

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
                    content=sanitize_llm_output(
                        message.content or "",
                        context={"user_id": user_id, "type": "chat_with_tools"},
                    ),
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
        await refresh_llm_safety_mode()
        messages = secure_messages(
            conversation_history,
            wrap_user_messages=True,
            wrap_tool_messages=True,
        )
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
            safe_result = sanitize_tool_payload(result)
            tool_message = {
                "role": "tool",
                "content": wrap_tool_result(json.dumps(safe_result, ensure_ascii=False))
            }
            tool_call_id = (
                (safe_result.get("tool_call_id") if isinstance(safe_result, dict) else None)
                or (safe_result.get("id") if isinstance(safe_result, dict) else None)
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

                selection = self._current_selection
                if selection:
                    response = await self._create_raw_completion_with_fallback(
                        selection,
                        request_params,
                        operation_type="continue_with_tool_results",
                    )
                else:
                    response = await self.provider.client.chat.completions.create(**request_params)
                choice = response.choices[0]
                message = choice.message

                if response.usage and selection is not None:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)
                    _record_token_usage(
                        selection.model_key, response.usage.prompt_tokens,
                        response.usage.completion_tokens, source="tool_results",
                    )
                    await record_llm_cost(
                        selection.model_key, response.usage.prompt_tokens,
                        response.usage.completion_tokens, source="tool_results",
                    )

                return LLMResponse(
                    content=sanitize_llm_output(
                        message.content or "",
                        context={"type": "continue_with_tool_results"},
                    ),
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
        conversation_history: list[dict[str, Any]] | None = None,
        user_context: dict[str, Any] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天（支持工具调用）
        """
        await refresh_llm_safety_mode()
        user_id = self._resolve_user_id(user_context=user_context)
        safe_system_prompt = sanitize_text_for_llm(system_prompt)
        safe_user_message = wrap_user_message(sanitize_text_for_llm(user_message))
        messages = [{"role": "system", "content": safe_system_prompt}]
        if conversation_history:
            messages.extend(
                secure_messages(
                    conversation_history,
                    wrap_user_messages=True,
                    wrap_tool_messages=True,
                )
            )
        if not self._history_ends_with_user_message(conversation_history, user_message):
            messages.append({"role": "user", "content": safe_user_message})
        temperature = self._resolve_temperature(user_context, temperature)

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            # O-02 trace spine：trace_id 优先取同 task 绑定的 recorder，否则
            # 回退调用方经 user_context 显式传入（graph worker task 场景）。
            _uc = user_context if isinstance(user_context, dict) else {}
            _spine_trace = current_trace_id() or str(_uc.get("trace_id") or "")
            with tracer.start_as_current_span("llm_chat_stream_with_tools") as span:
                span.set_attribute("llm.model", self.default_model)
                span.set_attribute("llm.temperature", temperature)
                # O-02 trace spine：OTel span 与全链 trace_id 关联。
                if _spine_trace:
                    span.set_attribute("sparkle.trace_id", _spine_trace)

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

                collected_tool_call_chunks = {}
                usage_data = None
                _llm_t0 = time.perf_counter()
                _llm_error: str | None = None

                selection = self._current_selection
                if selection:
                    chunk_stream = self._create_raw_stream_with_fallback(
                        selection,
                        request_params,
                        operation_type="chat_stream_with_tools",
                    )
                else:
                    async def _direct_stream() -> AsyncGenerator[Any, None]:
                        stream = await self.provider.client.chat.completions.create(**request_params)
                        async for item in stream:
                            yield item
                    chunk_stream = _direct_stream()

                try:
                    async for chunk in chunk_stream:
                        if hasattr(chunk, 'usage') and chunk.usage:
                            usage_data = chunk.usage

                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            if delta.content:
                                yield StreamChunk(type="text", content=delta.content)

                            # MIMO 特有：处理思考链内容 (reasoning_content)
                            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                yield StreamChunk(type="reasoning", reasoning_content=delta.reasoning_content)

                            # MIMO 特有：处理联网搜索引用 (annotations)
                            if hasattr(delta, 'annotations') and delta.annotations:
                                yield StreamChunk(type="annotation", annotations=list(delta.annotations))

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
                except Exception as exc:
                    _llm_error = type(exc).__name__
                    raise

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
                    model_name = selection.model_key if selection else "unknown"
                    _record_token_usage(
                        model_name, usage_data.prompt_tokens or 0,
                        usage_data.completion_tokens or 0, source="stream_chat",
                    )
                    _llm_cost_usd = await record_llm_cost(
                        model_name, usage_data.prompt_tokens or 0,
                        usage_data.completion_tokens or 0, source="stream_chat",
                    )
                    await _track_daily_user_tokens(user_id, usage_data.total_tokens or 0)
                    # O-02 trace spine：llm_call span——actual model/token/cost/
                    # latency 与全链 trace_id 关联（正文零记录）。
                    _llm_span_tags = {
                        "model": str(model_name),
                        "prompt_tokens": int(usage_data.prompt_tokens or 0),
                        "completion_tokens": int(usage_data.completion_tokens or 0),
                        "total_tokens": int(usage_data.total_tokens or 0),
                        "cost_usd": round(float(_llm_cost_usd or 0.0), 6),
                    }
                    _spine = current_recorder()
                    if _spine is not None:
                        _spine.span(
                            "llm_call",
                            status="error" if _llm_error else "ok",
                            duration_ms=(time.perf_counter() - _llm_t0) * 1000.0,
                            **_llm_span_tags,
                        )
                    elif _spine_trace:
                        emit_span(
                            "llm_call",
                            trace_id=_spine_trace,
                            status="error" if _llm_error else "ok",
                            duration_ms=(time.perf_counter() - _llm_t0) * 1000.0,
                            tags=_llm_span_tags,
                        )
                    yield StreamChunk(
                        type="usage",
                        prompt_tokens=usage_data.prompt_tokens,
                        completion_tokens=usage_data.completion_tokens,
                        total_tokens=usage_data.total_tokens
                    )
                elif current_trace_id() or _spine_trace:
                    # 无 usage 帧（部分 provider 不回传）仍发射阶段 span，
                    # 保证时间线不断链；token/cost 缺省为 0 诚实降级。
                    emit_span(
                        "llm_call",
                        trace_id=current_trace_id() or _spine_trace,
                        status="error" if _llm_error else "ok",
                        duration_ms=(time.perf_counter() - _llm_t0) * 1000.0,
                        tags={
                            "model": str(selection.model_key if selection else self.default_model),
                            "cost_usd": 0.0,
                        },
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

    @staticmethod
    def _history_ends_with_user_message(
        conversation_history: list[dict[str, Any]] | None,
        user_message: str,
    ) -> bool:
        if not conversation_history:
            return False
        last_message = conversation_history[-1]
        if not isinstance(last_message, dict):
            return False
        return (
            str(last_message.get("role") or "") == "user"
            and str(last_message.get("content") or "").strip() == str(user_message or "").strip()
        )

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
            {"role": "user", "content": "Generate push notification now. Respond with a single JSON object like {\"title\": \"...\", \"body\": \"...\"}."}
        ]
        # F-2：重试时附加"只输出 JSON"修正提示（历史上模型常回 markdown fence/散文/空串，
        # json.loads 直接抛 "Expecting value: line 1 column 1" 后静默降级硬编码文案）
        _JSON_ONLY_CORRECTION = (
            "上一次输出无法解析。请只输出一个 JSON 对象（形如 {\"title\": \"...\", \"body\": \"...\"}），"
            "不要 markdown 代码块，不要任何解释文字，不要输出空内容。"
        )

        def _parse_push_content(raw: str) -> dict[str, str]:
            payload = _extract_json_payload(raw)
            if payload is None:
                raise ValueError("no JSON object found in LLM output")
            content = json.loads(payload)
            if not isinstance(content, dict):
                raise ValueError(f"expected JSON object, got {type(content).__name__}")
            title = str(content.get("title") or "").strip()
            body = str(content.get("body") or "").strip()
            if not title or not body:
                raise ValueError("push content JSON missing non-empty 'title'/'body'")
            return {"title": title, "body": body}

        def _record_parse_failure(stage: str, exc: Exception, raw: str) -> None:
            try:
                LLM_PUSH_CONTENT_PARSE_FAILURE_TOTAL.labels(stage=stage).inc()
            except Exception:
                logger.opt(exception=True).debug("push content parse-failure metric recording failed")
            logger.warning(
                "generate_push_content: JSON parse failed at stage={} ({!r}); output preview={!r}",
                stage,
                exc,
                (raw or "")[:200],
            )

        fallback_content = {"title": "学习提醒", "body": f"{user_nickname}，该复习了。"}
        response_text = ""

        with tracer.start_as_current_span("llm_generate_push") as span:
            span.set_attribute("llm.persona", persona)
            span.set_attribute("llm.trigger", trigger_type)

            for attempt, correction in enumerate((None, _JSON_ONLY_CORRECTION)):
                attempt_messages = messages
                if correction is not None:
                    attempt_messages = [
                        *messages[:-1],
                        {"role": "user", "content": f"{messages[-1]['content']}\n\n{correction}"},
                    ]
                try:
                    response_text = await self.chat(attempt_messages, temperature=0.8)
                except Exception as exc:
                    # 调用层失败（网络/限流等）：允许重试一次，但不计入解析失败指标
                    logger.warning("generate_push_content: LLM call failed at attempt={}: {!r}", attempt, exc)
                    continue
                try:
                    return _parse_push_content(response_text)
                except Exception as exc:
                    stage = "initial" if attempt == 0 else "retry"
                    _record_parse_failure(stage, exc, response_text)
                    if attempt == 0:
                        span.set_attribute("llm.push_parse_retry", True)
                        continue
                    # F-2：保留降级但不再静默——指标 + error 日志（含触发上下文）
                    span.set_attribute("llm.push_fallback", True)
                    logger.error(
                        "generate_push_content: falling back to static copy after retry "
                        "(persona={}, trigger={}, user={}, stages=initial+retry both failed)",
                        persona,
                        trigger_type,
                        user_nickname,
                    )
                    return fallback_content
            span.set_attribute("llm.push_fallback", True)
            logger.error(
                "generate_push_content: falling back to static copy (persona={}, trigger={}, user={}, reason=llm call failures)",
                persona,
                trigger_type,
                user_nickname,
            )
            return fallback_content

# ==========================================
# 全局单例 - 向后兼容
# ==========================================

# 默认单例（使用新的动态路由）
llm_service_impl = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

from app.core.cache import cache_service
from app.core.llm_security_wrapper import LLMSecurityWrapper, SecurityConfig

llm_service = LLMSecurityWrapper(
    llm_service=llm_service_impl,
    redis_client=cache_service.redis,
    config=SecurityConfig()
)

# 创建专用角色的服务实例（按需使用，按角色缓存）
_llm_service_cache: dict[str, LLMService] = {}

def get_llm_service(agent_role: AgentRole | str) -> LLMService:
    """
    获取指定角色的LLM服务实例（缓存，避免重复创建HTTP连接池）

    Args:
        agent_role: Agent角色（如 "galaxy_guide", "exam_oracle" 等）

    Example:
        # 在 galaxy_guide 节点中使用
        galaxy_llm = get_llm_service("galaxy_guide")
        response = await galaxy_llm.chat(messages)
    """
    key = str(agent_role)
    if key not in _llm_service_cache:
        _llm_service_cache[key] = LLMService(agent_role=agent_role, enable_dynamic_routing=True)
    return _llm_service_cache[key]


async def get_configured_llm_service(
    agent_role: AgentRole | str,
    task_type: TaskType | None = None,
    avoid_providers: list[ModelProvider] | None = None,
    reasoning_mode: str | None = None,
) -> LLMService:
    """
    获取已按角色/任务完成模型路由的 LLM 服务实例。

    该 helper 用于避免调用方只切换了 prompt / workflow，
    但底层仍落到全局 generation 模型。
    """
    service = get_llm_service(agent_role)
    if task_type is not None:
        await service.switch_model_for_task(
            task_type,
            avoid_providers=avoid_providers,
            reasoning_mode=reasoning_mode,
        )
    return service


async def get_configured_llm_service_for_tier(
    agent_role: AgentRole | str,
    force_tier: ModelTier,
    task_type: TaskType | None = None,
    reasoning_mode: str | None = None,
) -> LLMService:
    """获取按指定 tier 强制路由后的 LLM 服务实例。"""
    selection = llm_router.select_model(
        agent_role,
        task_type=task_type,
        force_tier=force_tier,
        reasoning_mode=reasoning_mode,
        allow_max=force_tier == ModelTier.MAX,
    )
    return LLMService(
        agent_role=selection.agent_role,
        enable_dynamic_routing=True,
        initial_selection=selection,
    )


def get_llm_service_for_task(
    task_type: TaskType,
    avoid_providers: list[ModelProvider] | None = None,
) -> LLMService:
    """
    获取适合特定任务的LLM服务实例

    Args:
        task_type: 任务类型（如 TaskType.DEEP_REASONING）

    Example:
        # 深度推理任务使用更强的模型
        reason_llm = get_llm_service_for_task(TaskType.DEEP_REASONING)
        response = await reason_llm.chat(messages)
    """
    from app.core.agent_profiles import agent_profile_registry

    role = agent_profile_registry.get_profile_for_task(task_type).role
    selection = llm_router.select_model(
        agent_role=role,
        task_type=task_type,
        avoid_providers=avoid_providers,
    )
    return LLMService(
        agent_role=selection.agent_role,
        enable_dynamic_routing=True,
        initial_selection=selection,
    )


async def get_llm_service_for_specific_model(
    model_key: str,
    agent_role: AgentRole | str = AgentRole.GENERATION,
) -> LLMService:
    """获取并切换到指定 model_key 的 LLM 服务实例。"""
    service = get_llm_service(agent_role)
    await service.switch_to_specific_model(model_key)
    return service


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
    db_gen = None
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
        if db_gen is not None:
            await db_gen.aclose()

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
