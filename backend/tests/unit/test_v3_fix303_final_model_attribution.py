"""V3-FIX-303 · fallback 实际服务模型记账归位 —— service 层红绿锁.

缺陷（wt587 F2 / wt591 存活，二轮复核 v3-output/WT591-VERIFY2/verdicts.md §302）：

三条 LLM 链路（``chat_with_tools`` / ``continue_with_tool_results`` /
``chat_stream_with_tools``）的 token 计数、成本估算与 O-02 trace 全部记在
**调用前**的原选模型（``selection = self._current_selection``）上；fallback
实际服务模型（``session.final_model_key``）全仓仅 1 写 0 读、无外传通道。
wt591 实验：fallback 链首候选 429 → 次候选实际服务，``chat_with_tools``
记账段把 token+cost 全记在 model-a（服务方是 model-b）——成本归因失真。

红测（base 上红）：
1. ``chat_with_tools``：首候选 429 → 次候选 model-b 实际服务，``_record_token_usage``
   与 ``record_llm_cost`` 必须记在 model-b（修前记在 model-a → 红）。
2. ``continue_with_tool_results``：同链路同断言（source=tool_results）。
3. ``chat_stream_with_tools``：首候选 429 → model-b 流式服务，token/cost 记账
   与 O-02 ``llm_call`` span 的 ``model`` 标签都必须是 model-b（修前 model-a）。

恒等对照（修前修后都必须绿——零行为变化守卫）：
4. 无 fallback（首候选直连成功）时，记账恒等于原选模型键。
5. 流式无 fallback 时，记账与 O-02 span ``model`` 恒等于原选模型键。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

import app.services.llm_service as llm_service_module
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.llm.base import LLMProvider
from app.services.llm.fallback import LLMModelFallbackManager
from app.services.llm_service import LLMService

PRIMARY_MODEL_KEY = "wt303_primary_standard"
SECONDARY_MODEL_KEY = "wt303_secondary_standard"
PRIMARY_MODEL_NAME = "wt303-model-a"
SECONDARY_MODEL_NAME = "wt303-model-b"

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "echo_tool",
            "description": "echo",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


def _selection(model_key: str, model_name: str, provider: ModelProvider) -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=ModelConfig(
            provider=provider,
            model_name=model_name,
            base_url=f"https://{model_name}.test/v1",
            api_key=f"sk-{model_name}",
            tier=ModelTier.STANDARD,
        ),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="v3-fix303 test",
    )


def _completion_response(model_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=f"answered-by-{model_name}", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
    )


def _stream_chunks(model_name: str) -> list[SimpleNamespace]:
    """完整 provider 轮：内容帧 + finish_reason 终帧 + usage 帧。"""
    return [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="hi", tool_calls=None), finish_reason=None
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="", tool_calls=None), finish_reason="stop"
                )
            ]
        ),
        SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=13, completion_tokens=5, total_tokens=18),
        ),
    ]


class _AttributionProvider(LLMProvider):
    """model-a（原选）一律 429，model-b 成功——复现 wt591 fallback 链形态。

    ``fail_first=False`` 时 model-a 直连成功（恒等对照组用）。
    fallback 候选会经 ``OpenAICompatibleProvider`` 打桩新建实例，故「实际
    服务方」留痕挂类级共享列表，按测试前置清空。
    """

    served_all: list[str] = []

    def __init__(self, api_key: str = "", base_url: str = "", *, fail_first: bool = True):
        self.fail_first = fail_first
        provider = self

        def _track(model: str) -> None:
            _AttributionProvider.served_all.append(model)

        def _fail_or_pass(model: str) -> bool:
            return model == PRIMARY_MODEL_NAME and provider.fail_first

        async def create(**params: Any) -> Any:
            model = str(params.get("model"))
            _track(model)
            if _fail_or_pass(model):
                raise RuntimeError("429 Too Many Requests (primary saturated)")
            if params.get("stream"):
                async def gen() -> AsyncIterator[Any]:
                    for chunk in _stream_chunks(model):
                        yield chunk

                return gen()
            return _completion_response(model)

        self.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

    async def chat(self, messages, model, temperature: float = 0.7, **kwargs) -> str:
        return ""

    async def stream_chat(self, messages, model, temperature: float = 0.7, **kwargs):  # noqa: ANN201
        yield "unused"


@pytest.fixture()
def attribution_env(monkeypatch: pytest.MonkeyPatch):
    """真实 fallback 管理器 + 双模型注册表 + 记账捕获面。"""
    primary = _selection(PRIMARY_MODEL_KEY, PRIMARY_MODEL_NAME, ModelProvider.ZHIPU)
    secondary = _selection(SECONDARY_MODEL_KEY, SECONDARY_MODEL_NAME, ModelProvider.DASHSCOPE)

    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {PRIMARY_MODEL_KEY: primary.config, SECONDARY_MODEL_KEY: secondary.config},
    )
    # 测试卫生：真实 fallback 链会经 report_model_success/failure 向 router
    # 健康表写 wt303 键（_available_models 由 monkeypatch 还原，_model_health
    # 不会）——用副本隔离，防止向同进程后续测试泄漏健康态。
    monkeypatch.setattr(llm_router, "_model_health", dict(llm_router._model_health))
    monkeypatch.setattr(
        llm_router,
        "_tier_mapping",
        {
            tier: (
                [PRIMARY_MODEL_KEY, SECONDARY_MODEL_KEY]
                if tier is ModelTier.STANDARD
                else []
            )
            for tier in ModelTier
        },
    )

    async def _noop_async(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(llm_service_module, "refresh_llm_safety_mode", _noop_async)
    monkeypatch.setattr(llm_service_module, "_track_daily_user_tokens", _noop_async)

    token_calls: list[tuple[str, str]] = []
    cost_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        llm_service_module,
        "_record_token_usage",
        lambda model, prompt_tokens, completion_tokens, source="chat": token_calls.append(
            (model, source)
        ),
    )

    async def _fake_record_llm_cost(
        model_key: str, prompt_tokens: int, completion_tokens: int, source: str = "chat"
    ) -> float:
        cost_calls.append((model_key, source))
        return 0.0

    monkeypatch.setattr(llm_service_module, "record_llm_cost", _fake_record_llm_cost)

    def _build(fail_first: bool = True) -> LLMService:
        _AttributionProvider.served_all.clear()
        # 真实 fallback 逻辑 + 全新健康态（单例会被进程内历史污染，故换新实例）。
        monkeypatch.setattr(
            llm_service_module, "llm_fallback_manager", LLMModelFallbackManager()
        )
        monkeypatch.setattr(
            llm_service_module, "OpenAICompatibleProvider", _AttributionProvider
        )
        service = LLMService(enable_dynamic_routing=False)
        service.demo_mode = False
        service._current_selection = primary
        service._provider = _AttributionProvider(fail_first=fail_first)
        return service

    return SimpleNamespace(
        build=_build,
        token_calls=token_calls,
        cost_calls=cost_calls,
        served=_AttributionProvider.served_all,
        primary=primary,
        secondary=secondary,
    )


# --- 红测 1：chat_with_tools —— fallback 后记账必须归位 model-b ---------------


@pytest.mark.asyncio
async def test_chat_with_tools_fallback_accounts_serving_model(attribution_env):
    service = attribution_env.build(fail_first=True)

    response = await service.chat_with_tools("sys", "user", tools=_TOOLS)

    assert response.content == f"answered-by-{SECONDARY_MODEL_NAME}"
    # 实际服务方是 model-b（首候选 429 被 fallback 链换道）
    assert attribution_env.served == [PRIMARY_MODEL_NAME, SECONDARY_MODEL_NAME]
    # 记账必须跟随实际服务模型（修前记在 PRIMARY → 红）
    assert attribution_env.token_calls == [(SECONDARY_MODEL_KEY, "chat_with_tools")]
    assert attribution_env.cost_calls == [(SECONDARY_MODEL_KEY, "chat_with_tools")]


# --- 红测 2：continue_with_tool_results —— 同链路同契约 ----------------------


@pytest.mark.asyncio
async def test_continue_with_tool_results_fallback_accounts_serving_model(attribution_env):
    service = attribution_env.build(fail_first=True)
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_303",
                    "type": "function",
                    "function": {"name": "echo_tool", "arguments": "{}"},
                }
            ],
        }
    ]

    response = await service.continue_with_tool_results(
        history, [{"tool_call_id": "call_303", "ok": True}]
    )

    assert response.content == f"answered-by-{SECONDARY_MODEL_NAME}"
    assert attribution_env.served == [PRIMARY_MODEL_NAME, SECONDARY_MODEL_NAME]
    assert attribution_env.token_calls == [(SECONDARY_MODEL_KEY, "tool_results")]
    assert attribution_env.cost_calls == [(SECONDARY_MODEL_KEY, "tool_results")]


# --- 红测 3：chat_stream_with_tools —— 流式记账 + O-02 span 归位 -------------


@pytest.mark.asyncio
async def test_chat_stream_with_tools_fallback_accounts_serving_model(
    attribution_env, monkeypatch: pytest.MonkeyPatch
):
    span_calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(llm_service_module, "current_trace_id", lambda: "wt303-trace")
    monkeypatch.setattr(llm_service_module, "current_recorder", lambda: None)
    monkeypatch.setattr(
        llm_service_module,
        "emit_span",
        lambda name, **kwargs: span_calls.append((name, kwargs.get("tags") or {})),
    )

    service = attribution_env.build(fail_first=True)

    async for _chunk in service.chat_stream_with_tools("sys", "user", tools=_TOOLS):
        pass

    assert attribution_env.served == [PRIMARY_MODEL_NAME, SECONDARY_MODEL_NAME]
    assert attribution_env.token_calls == [(SECONDARY_MODEL_KEY, "stream_chat")]
    assert attribution_env.cost_calls == [(SECONDARY_MODEL_KEY, "stream_chat")]
    # O-02 trace spine：llm_call span 的 model 标签 = 实际服务模型
    llm_call_spans = [tags for name, tags in span_calls if name == "llm_call"]
    assert llm_call_spans, "usage 帧存在时必须发射 llm_call span"
    assert llm_call_spans[0]["model"] == SECONDARY_MODEL_KEY


# --- 恒等对照 4：无 fallback —— 记账恒等于原选模型（零行为变化守卫）-----------


@pytest.mark.asyncio
async def test_chat_with_tools_no_fallback_accounts_original_model(attribution_env):
    service = attribution_env.build(fail_first=False)

    response = await service.chat_with_tools("sys", "user", tools=_TOOLS)

    assert response.content == f"answered-by-{PRIMARY_MODEL_NAME}"
    assert attribution_env.served == [PRIMARY_MODEL_NAME]
    assert attribution_env.token_calls == [(PRIMARY_MODEL_KEY, "chat_with_tools")]
    assert attribution_env.cost_calls == [(PRIMARY_MODEL_KEY, "chat_with_tools")]


# --- 恒等对照 5：流式无 fallback —— 记账与 O-02 span 恒等于原选模型 -----------


@pytest.mark.asyncio
async def test_chat_stream_with_tools_no_fallback_accounts_original_model(
    attribution_env, monkeypatch: pytest.MonkeyPatch
):
    span_calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(llm_service_module, "current_trace_id", lambda: "wt303-trace")
    monkeypatch.setattr(llm_service_module, "current_recorder", lambda: None)
    monkeypatch.setattr(
        llm_service_module,
        "emit_span",
        lambda name, **kwargs: span_calls.append((name, kwargs.get("tags") or {})),
    )

    service = attribution_env.build(fail_first=False)

    async for _chunk in service.chat_stream_with_tools("sys", "user", tools=_TOOLS):
        pass

    assert attribution_env.served == [PRIMARY_MODEL_NAME]
    assert attribution_env.token_calls == [(PRIMARY_MODEL_KEY, "stream_chat")]
    assert attribution_env.cost_calls == [(PRIMARY_MODEL_KEY, "stream_chat")]
    llm_call_spans = [tags for name, tags in span_calls if name == "llm_call"]
    assert llm_call_spans, "usage 帧存在时必须发射 llm_call span"
    assert llm_call_spans[0]["model"] == PRIMARY_MODEL_KEY
