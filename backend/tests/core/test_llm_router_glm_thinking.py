"""
GLM 车道 thinking 控制 + max_tokens 留量单测（V3-FIX-04，mock 传输，零真实请求）。

红绿契约（依据 v3-output/B-05/SUPPLEMENT_KEY_ROTATED.md 的 B-05b 直连实测）：
- coding 端点（/api/coding/paas/v4）是唯一支持 `thinking:{"type":"disabled"}` 真关闭思考
  的通道；标准端点（/api/paas/v4）对该参数返 HTTP 400 code 1210（"该模型始终思考"）。
- 引擎原状：clear_thinking 只是客户端侧概念，extra_body 里的 `clear_thinking` 被智谱
  静默忽略——"no_thinking" 车道实际都在思考。
- 思考吃掉 completion 预算 84-88%：显式 max_tokens=1024 可被思考清空 → 空回复
  （finish=length）。

覆盖面：
1. 线上 payload 形态（AsyncOpenAI + httpx.MockTransport 捕获请求 JSON）：
   - coding 端点 + clear_thinking=True → body 含 thinking:{"type":"disabled"}
   - 标准端点 + clear_thinking=True → body 不含 thinking 参数（发了会 400）
   - clear_thinking=False（思考车道）→ body 不含 thinking 参数（默认思考保持开启）
2. max_tokens 留量保护（glm_effective_max_tokens 纯函数 + llm_service 装配点）
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.agent_profiles import AgentRole
from app.core.llm_router import (
    LLMRouter,
    ModelProvider,
    glm_effective_max_tokens,
    is_zhipu_coding_endpoint,
    llm_router,
)
from app.services.llm_service import LLMService

ZHIPU_CODING_URL = "https://open.bigmodel.cn/api/coding/paas/v4"
ZHIPU_STANDARD_URL = "https://open.bigmodel.cn/api/paas/v4"


@pytest.fixture
def router() -> LLMRouter:
    """Fresh LLMRouter (isolated health state)."""
    return LLMRouter()


def _capture_handler(captured: dict):
    """httpx.MockTransport handler: capture request JSON, return a valid completion."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]},
        )

    return handler


async def _capture_wire_body(base_url: str, extra_body: dict, **create_kwargs) -> dict:
    """按引擎真实路径（get_openai_client_kwargs → SDK create）捕获线上 JSON payload。"""
    captured: dict = {}
    client = AsyncOpenAI(
        api_key="test-key",
        base_url=base_url,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(_capture_handler(captured))),
    )
    await client.chat.completions.create(
        model="glm-test",
        messages=[{"role": "user", "content": "hi"}],
        extra_body=extra_body,
        **create_kwargs,
    )
    await client.close()
    return captured["body"]


# ---------------------------------------------------------------------------
# 1. 线上 payload：thinking 参数按 base_url 分流
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coding_lane_clear_thinking_sends_thinking_disabled(router: LLMRouter):
    """coding 端点 + clear_thinking=True 的 zhipu 候选 → 线上 payload 含 thinking disabled（核心红测）。"""
    selection = router.select_specific_model("glm_4_7_no_thinking", agent_role=AgentRole.ROUTER)

    assert selection.config.provider == ModelProvider.ZHIPU
    assert selection.config.clear_thinking is True
    assert is_zhipu_coding_endpoint(selection.config.base_url), "候选必须指向 coding 端点"

    kwargs = llm_router.get_openai_client_kwargs(selection)
    body = await _capture_wire_body(selection.config.base_url, kwargs.get("extra_body") or {})

    assert body["thinking"] == {"type": "disabled"}


@pytest.mark.asyncio
async def test_standard_endpoint_lane_omits_thinking_param(router: LLMRouter):
    """标准端点 + clear_thinking=True → 不发 thinking 参数（标准端点对该参数返 400 code 1210）。"""
    selection = router.select_specific_model("glm_4_7_flash_no_thinking", agent_role=AgentRole.ROUTER)

    assert selection.config.provider == ModelProvider.ZHIPU
    assert selection.config.clear_thinking is True
    assert not is_zhipu_coding_endpoint(selection.config.base_url), "候选必须指向标准端点"

    kwargs = llm_router.get_openai_client_kwargs(selection)
    body = await _capture_wire_body(selection.config.base_url, kwargs.get("extra_body") or {})

    assert "thinking" not in body


@pytest.mark.asyncio
async def test_thinking_lane_keeps_default_thinking(router: LLMRouter):
    """clear_thinking=False（保留思考车道）→ 不发 thinking 参数，默认思考行为保持不变。"""
    selection = router.select_specific_model("glm_4_7_thinking", agent_role=AgentRole.ROUTER)

    assert selection.config.provider == ModelProvider.ZHIPU
    assert selection.config.clear_thinking is False

    kwargs = llm_router.get_openai_client_kwargs(selection)
    body = await _capture_wire_body(selection.config.base_url, kwargs.get("extra_body") or {})

    assert "thinking" not in body


# ---------------------------------------------------------------------------
# 2. max_tokens 留量保护
# ---------------------------------------------------------------------------


def test_glm_effective_max_tokens_headroom_on_thinking_lanes():
    """思考仍会进行的车道：请求值上浮保证最坏 88% 思考占比下可见输出 ≥ 配置值的 15%。"""
    # coding 端点 + clear_thinking=True → 思考已关闭，预算原样
    assert glm_effective_max_tokens(ModelProvider.ZHIPU, ZHIPU_CODING_URL, True, 1024) == 1024
    # coding 端点 + clear_thinking=False → 思考仍在：1024 → 1280（ceil(1024*0.15/0.12)）
    assert glm_effective_max_tokens(ModelProvider.ZHIPU, ZHIPU_CODING_URL, False, 1024) == 1280
    # 标准端点（即使 clear_thinking=True 关不掉思考）：同样上浮
    assert glm_effective_max_tokens(ModelProvider.ZHIPU, ZHIPU_STANDARD_URL, True, 1024) == 1280
    # 未显式配置 max_tokens（None）→ 不注入
    assert glm_effective_max_tokens(ModelProvider.ZHIPU, ZHIPU_CODING_URL, True, None) is None
    # 非 zhipu → 原样
    assert glm_effective_max_tokens(ModelProvider.DEEPSEEK, "https://api.deepseek.com", None, 1024) == 1024


def test_get_openai_client_kwargs_applies_max_tokens_headroom(router: LLMRouter):
    """get_openai_client_kwargs 对带 max_tokens 的 zhipu 思考车道应用留量。"""
    selection = router.select_specific_model("glm_4_7_no_thinking", agent_role=AgentRole.ROUTER)
    selection.config.max_tokens = 1024

    kwargs = llm_router.get_openai_client_kwargs(selection)
    # coding 端点 + clear_thinking=True → 思考关闭，预算不膨胀
    assert kwargs["max_tokens"] == 1024

    selection_thinking = router.select_specific_model("glm_4_7_thinking", agent_role=AgentRole.ROUTER)
    selection_thinking.config.max_tokens = 1024
    kwargs_thinking = llm_router.get_openai_client_kwargs(selection_thinking)
    # 思考车道 → 上浮留量
    assert kwargs_thinking["max_tokens"] == 1280


# ---------------------------------------------------------------------------
# 3. llm_service 装配点：caller 显式传入的小 max_tokens 也被保护
# ---------------------------------------------------------------------------


class _FakeRawProvider:
    """暴露 .client 供 _create_raw_completion 走 raw 路径，并捕获最终请求参数。"""

    def __init__(self, captured: dict):
        self.captured = captured
        self.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=self._create)))

    async def _create(self, **params):
        self.captured.update(params)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))], usage=None)


@pytest.mark.asyncio
async def test_raw_completion_glm_max_tokens_headroom_applied(router: LLMRouter, monkeypatch):
    """caller 显式传 max_tokens=1024 给思考车道 → 实际请求值上浮到 1280。"""
    selection = router.select_specific_model("glm_4_7_thinking", agent_role=AgentRole.ROUTER)
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)
    service._current_selection = selection
    captured: dict = {}
    service._provider = _FakeRawProvider(captured)

    await service._create_raw_completion(
        selection,
        {"model": selection.config.model_name, "messages": [], "max_tokens": 1024},
    )

    assert captured["max_tokens"] == 1280
