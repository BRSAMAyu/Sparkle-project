"""R2 P0 契约测试：LLMSecurityWrapper 与裸 LLMService 签名一致性。

背景（R2 审查报告 03-r2-critical-services.md §2）：
- wrapper 单例的 chat 族曾是 user_id-first 签名，与全仓 messages-first 约定错位，
  导致 13 个生产调用点 100% TypeError；旧测试用 ``(*args, **kwargs)`` 裸 mock 掩盖了
  错位（mock-oracle）。
- 本文件用真实 wrapper + 真实参数绑定（含 ``inspect.signature`` 断言与
  bare-signature 内层服务全链调用）锁定契约，防止复发。

契约（R2 §2.3）：
- chat / stream_chat: ``messages`` 首参, ``temperature`` 默认 None（非 0.7——
  否则显式 0.7 会击穿 E2 的 selection 配置优先级）, ``user_id`` 为可选 kwarg。
- chat_with_tools: ``system_prompt, user_message, tools`` 前三参,
  ``conversation_history``/``model`` 可选, ``user_id`` 可选 kwarg。
- generate_embeddings: ``texts`` 首参, ``user_id`` 可选 kwarg。
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.core.llm_security_wrapper import LLMSecurityWrapper, SecurityConfig
from app.services.llm_service import LLMService, llm_service as wrapper_singleton

# =============================================================================
# bare-signature 内层服务桩（签名逐参复制自 LLMService，用于真实参数绑定）
# =============================================================================


@dataclass
class _ToolResponse:
    content: str = "tool ok"
    tool_calls: list = field(default_factory=list)


class BareSignatureInner:
    """与裸 LLMService 对外签名一致的桩；多余 kwarg 会直接 TypeError。"""

    def __init__(self) -> None:
        self.chat_calls: list[dict[str, Any]] = []
        self.tools_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []
        self.embed_calls: list[dict[str, Any]] = []

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        *,
        task_type: Any = None,
        **kwargs: Any,
    ) -> str:
        self.chat_calls.append(
            {"messages": messages, "model": model, "temperature": temperature, "kwargs": kwargs}
        )
        return "bare-ok"

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        user_context: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        self.stream_calls.append(
            {"messages": messages, "model": model, "temperature": temperature, "kwargs": kwargs}
        )
        for chunk in ("a", "b"):
            yield chunk

    async def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        conversation_history: list[dict] | None = None,
    ) -> _ToolResponse:
        # 注意：裸服务不接受 model kwarg —— wrapper 若继续转发 model= 会在此 TypeError
        self.tools_calls.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "tools": tools,
                "conversation_history": conversation_history,
            }
        )
        return _ToolResponse()

    async def generate_embeddings(self, texts: list[str], model: str | None = None):
        self.embed_calls.append({"texts": texts, "model": model})
        return [[0.1] for _ in texts]


def _make_wrapper(inner: BareSignatureInner | None = None) -> tuple[LLMSecurityWrapper, BareSignatureInner]:
    inner = inner or BareSignatureInner()
    config = SecurityConfig(
        strict_mode=False,
        enable_quota_check=False,
        enable_monitoring=False,
    )
    return LLMSecurityWrapper(llm_service=inner, redis_client=None, config=config), inner


_MESSAGES = [{"role": "user", "content": "你好"}]


# =============================================================================
# P0：单例签名契约（真实导入的生产单例）
# =============================================================================


class TestSingletonSignatureContract:
    def test_singleton_is_security_wrapper(self):
        assert isinstance(wrapper_singleton, LLMSecurityWrapper)

    def test_chat_first_positional_is_messages(self):
        params = list(inspect.signature(wrapper_singleton.chat).parameters)  # 绑定方法，无 self
        assert params[0] == "messages", f"wrapper.chat 首参必须是 messages，实际: {params}"

    def test_stream_chat_first_positional_is_messages(self):
        params = list(inspect.signature(wrapper_singleton.stream_chat).parameters)
        assert params[0] == "messages", f"wrapper.stream_chat 首参必须是 messages，实际: {params}"

    def test_chat_temperature_default_is_none_not_0_7(self):
        # E2 语义：0.7 默认会以显式值击穿 selection 配置优先级
        for name in ("chat", "stream_chat"):
            default = inspect.signature(getattr(wrapper_singleton, name)).parameters["temperature"].default
            assert default is None, f"wrapper.{name}.temperature 默认必须是 None，实际: {default!r}"
        # 裸服务侧同样保持 E2 语义
        bare_default = inspect.signature(LLMService.chat).parameters["temperature"].default
        assert bare_default is None

    def test_chat_user_id_is_keyword_only_optional(self):
        param = inspect.signature(wrapper_singleton.chat).parameters["user_id"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY
        assert param.default is None

    def test_chat_with_tools_param_order(self):
        params = list(inspect.signature(wrapper_singleton.chat_with_tools).parameters)
        assert params[0:3] == ["system_prompt", "user_message", "tools"]

    def test_generate_embeddings_first_param_is_texts(self):
        params = list(inspect.signature(wrapper_singleton.generate_embeddings).parameters)
        assert params[0] == "texts"

    def test_bare_service_chat_signature_alignment(self):
        """wrapper 与裸服务的公共参数面必须一致（messages/model/temperature + **kwargs）。"""
        bare = inspect.signature(LLMService.chat).parameters
        wrapped = inspect.signature(wrapper_singleton.chat).parameters
        for name in ("messages", "model", "temperature"):
            assert name in wrapped and name in bare
        assert wrapped["messages"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert bare["messages"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


# =============================================================================
# P0：13 个真坏调用点形状逐一对真实单例签名做参数绑定（防 mock-oracle 复发）
# =============================================================================


class TestProductionCallSiteShapesBind:
    """调用形状逐一取自 R2 报告 §2.2 Group A/A'（file:line）。"""

    def setup_method(self):
        self.chat_sig = inspect.signature(wrapper_singleton.chat)  # 绑定方法，无 self
        self.tools_sig = inspect.signature(wrapper_singleton.chat_with_tools)

    def test_a1_llm_fallback_utils_safe_llm_call_shape(self):
        # services/llm_fallback_utils.py:88 chat(messages, **kwargs)
        self.chat_sig.bind(_MESSAGES, temperature=0.5, user_id="u1")

    def test_a2_llm_dispatcher_shape(self):
        # services/llm_dispatcher.py:98 chat(messages, model=model_id)
        self.chat_sig.bind(_MESSAGES, model="free-fast")

    def test_a3_graph_rag_745_shape(self):
        # orchestration/graph_rag.py:745 chat(messages, temperature=0.0)
        self.chat_sig.bind(_MESSAGES, temperature=0.0)

    def test_a4_graph_rag_1665_shape(self):
        # orchestration/graph_rag.py:1665 chat(messages)
        self.chat_sig.bind(_MESSAGES)

    def test_a5_cognitive_271_shape(self):
        # services/cognitive_service.py:271 chat(messages, temperature=0.7)
        self.chat_sig.bind(_MESSAGES, temperature=0.7)

    def test_a6_cognitive_516_shape(self):
        # services/cognitive_service.py:516 chat(messages, temperature=0.5)
        self.chat_sig.bind(_MESSAGES, temperature=0.5)

    def test_a7_document_service_96_shape(self):
        # services/document_service.py:96 chat([...], temperature=0.2)
        self.chat_sig.bind(_MESSAGES, temperature=0.2)

    def test_a8_translation_364_shape(self):
        # services/translation_service.py:364 chat(messages=..., model=...)
        self.chat_sig.bind(messages=_MESSAGES, model="model-x")

    def test_a9_enhanced_orchestrator_433_shape(self):
        # agents/enhanced_orchestrator.py:433 chat(messages=..., model="qwen-plus")
        self.chat_sig.bind(messages=_MESSAGES, model="qwen-plus")

    def test_a10_orchestrator_agent_158_shape(self):
        # agents/orchestrator_agent.py:158 —— 修复后以 messages= 传参（原 prompt= 无签名可绑）
        self.chat_sig.bind(messages=_MESSAGES, model="qwen-plus")

    def test_a11_a12_chat_v1_endpoints_shape(self):
        # api/v1/chat.py:253/:466 chat_with_tools(system_prompt=, user_message=, tools=, conversation_history=)
        self.tools_sig.bind(
            system_prompt="sp", user_message="um", tools=[], conversation_history=[{"role": "user", "content": "h"}]
        )

    def test_a13_error_handler_61_shape(self):
        # orchestration/error_handler.py:61 chat_with_tools(system_prompt=, user_message=, tools=)
        self.tools_sig.bind(system_prompt="sp", user_message="um", tools=[])


# =============================================================================
# P0：全链真实绑定调用（真实 wrapper 代码路径，bare-signature 内层，无 mock）
# =============================================================================


class TestRealBindingFullChain:
    @pytest.mark.asyncio
    async def test_chat_positional_messages_no_type_error(self):
        wrapper, inner = _make_wrapper()
        result = await wrapper.chat(_MESSAGES)
        assert result == "bare-ok"
        assert inner.chat_calls[0]["messages"] == _MESSAGES
        # temperature=None 必须原样透传（不得变成显式 0.7 击穿 E2）
        assert inner.chat_calls[0]["temperature"] is None

    @pytest.mark.asyncio
    async def test_chat_forwards_user_id_kwarg(self):
        wrapper, inner = _make_wrapper()
        await wrapper.chat(_MESSAGES, user_id="u1")
        assert inner.chat_calls[0]["kwargs"].get("user_id") == "u1"

    @pytest.mark.asyncio
    async def test_chat_forwards_explicit_temperature(self):
        wrapper, inner = _make_wrapper()
        await wrapper.chat(_MESSAGES, temperature=0.2)
        assert inner.chat_calls[0]["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_chat_with_tools_inner_receives_no_model_kwarg(self):
        # 裸服务 chat_with_tools 不接受 model —— wrapper 内层调用不得转发 model=
        wrapper, inner = _make_wrapper()
        response = await wrapper.chat_with_tools(
            system_prompt="sp", user_message="um", tools=[{"name": "t"}], model="ignored-by-bare"
        )
        assert response.content == "tool ok"
        call = inner.tools_calls[0]
        assert call["system_prompt"] == "sp"
        assert call["user_message"] == "um"
        assert call["tools"] == [{"name": "t"}]
        assert call["conversation_history"] is None

    @pytest.mark.asyncio
    async def test_chat_with_tools_without_optional_args(self):
        # A13 形状：仅三个必填参数
        wrapper, inner = _make_wrapper()
        await wrapper.chat_with_tools(system_prompt="sp", user_message="um", tools=[])
        assert len(inner.tools_calls) == 1

    @pytest.mark.asyncio
    async def test_chat_with_tools_sanitizes_conversation_history(self):
        # A11/A12 形状：带非空 conversation_history（历史过滤路径曾对
        # SafetyCheckResult 做元组解包必 TypeError）
        wrapper, inner = _make_wrapper()
        history = [
            {"role": "user", "content": "早前消息"},
            {"role": "assistant", "content": "早前回复"},
        ]
        await wrapper.chat_with_tools(
            system_prompt="sp", user_message="um", tools=[], conversation_history=history
        )
        call = inner.tools_calls[0]
        assert [m["role"] for m in call["conversation_history"]] == ["user", "assistant"]
        assert call["conversation_history"][0]["content"] == "早前消息"

    @pytest.mark.asyncio
    async def test_stream_chat_full_chain(self):
        wrapper, inner = _make_wrapper()
        chunks = [chunk async for chunk in wrapper.stream_chat(_MESSAGES)]
        assert chunks == ["a", "b"]
        # wrapper 未显式传 temperature 时不向内层注入 None（内层用自己的默认/E2 语义）
        assert inner.stream_calls[0]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_stream_chat_forwards_explicit_temperature(self):
        wrapper, inner = _make_wrapper()
        _ = [chunk async for chunk in wrapper.stream_chat(_MESSAGES, temperature=0.3)]
        assert inner.stream_calls[0]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_generate_embeddings_full_chain(self):
        wrapper, inner = _make_wrapper()
        vectors = await wrapper.generate_embeddings(["x", "y"])
        assert vectors == [[0.1], [0.1]]
        assert inner.embed_calls[0]["texts"] == ["x", "y"]

    @pytest.mark.asyncio
    async def test_monitor_enabled_original_error_propagates(self):
        """monitor 开启（生产单例默认）时内层失败，原始异常必须透传。

        回归防护：指标 TASK_FAILURES/LLM_CALLS_TOTAL/LLM_LATENCY_SECONDS 是
        llm_monitoring 的模块级对象，wrapper 曾错用 self.monitor.X 访问——
        except 路径自身 AttributeError 吞掉真实错误（运行时实证发现）。
        """
        class _ExplodingInner(BareSignatureInner):
            async def chat(self, messages, model=None, temperature=None, *, task_type=None, **kwargs):
                raise RuntimeError("inner-boom")

        config = SecurityConfig(strict_mode=False, enable_quota_check=False, enable_monitoring=True)
        wrapper = LLMSecurityWrapper(llm_service=_ExplodingInner(), redis_client=None, config=config)
        with pytest.raises(RuntimeError, match="inner-boom"):
            await wrapper.chat(_MESSAGES)


# =============================================================================
# E1 补强：__getattr__ 收敛为 allowlist（安全旁路面关闭，dunder 拒绝保留）
# =============================================================================


class _MetadataInner(BareSignatureInner):
    chat_model = "stub-chat-model"
    reason_model = "stub-reason-model"
    default_model = "stub-default-model"
    agent_role = "generation"
    model_key = "stub-key"

    def get_current_selection(self):
        return None

    def is_thinking_mode(self):
        return False

    async def chat_json(self, prompt, **kwargs):
        return {"ok": True}

    async def reason(self, *args, **kwargs):
        return "reasoned"

    async def reason_json(self, *args, **kwargs):
        return {}

    async def continue_with_tool_results(self, *args, **kwargs):
        return _ToolResponse()

    async def chat_stream_with_tools(self, *args, **kwargs):
        yield "chunk"

    async def generate_push_content(self, *args, **kwargs):
        return "push"


class TestGetattrAllowlist:
    def test_allowlisted_routing_metadata_forwarded(self):
        wrapper, _ = _make_wrapper(_MetadataInner())
        assert wrapper.chat_model == "stub-chat-model"
        assert wrapper.reason_model == "stub-reason-model"
        assert wrapper.default_model == "stub-default-model"
        assert wrapper.agent_role == "generation"
        assert wrapper.model_key == "stub-key"
        assert wrapper.get_current_selection() is None
        assert wrapper.is_thinking_mode() is False

    def test_allowlisted_functional_passthrough_forwarded(self):
        """生产已在用的裸服务方法（Group B 审计清单）仍可经转发触达。"""
        wrapper, _ = _make_wrapper(_MetadataInner())
        assert callable(wrapper.chat_json)
        assert callable(wrapper.reason)
        assert callable(wrapper.reason_json)
        assert callable(wrapper.continue_with_tool_results)
        assert callable(wrapper.chat_stream_with_tools)
        assert callable(wrapper.generate_push_content)

    def test_non_allowlisted_attributes_blocked(self):
        wrapper, _ = _make_wrapper(_MetadataInner())
        for name in ("provider", "providers", "_provider_error", "made_up_future_method", "secure_messages"):
            with pytest.raises(AttributeError, match=name):
                getattr(wrapper, name)

    def test_dunder_forwarding_rejected(self):
        wrapper, _ = _make_wrapper(_MetadataInner())
        with pytest.raises(AttributeError):
            getattr(wrapper, "__deepcopy__")
        # __class__ 是类型属性，正常解析，不受影响
        assert wrapper.__class__ is LLMSecurityWrapper
