"""LLM 工厂函数路由状态隔离回归（wt299-p1-pair P1-1）。

背景（wt294 P1-1 交接）：LLMService 单例上存在可变路由状态
（`_current_selection/_provider/chat_model/_extra_body`），`switch_model_for_task /
switch_to_specific_model` 会原地改写它们。`_state_lock` 只串行化单次变更本身，
防不住「切换后到下次切换前」的跨请求串读——A 请求把共享实例切到 batch 模型后，
B 请求（未要求切换）经 `chat()` L682 `model or self.chat_model` 与 L771
`cascade_selection or self._current_selection` 读到的就是 A 的模型。

实锤调用面（本卡核对，wt294「生产无单例调用方」结论已过时）：
- `get_configured_llm_service(role, task_type)`（带 task_type 时）在按角色缓存
  的共享实例上原地 `switch_model_for_task` —— standard_workflow 主聊天路径、
  aurora decision_loop/chat_adapter、graph_rag、bottleneck_analyzer、
  multi_agent_adapter 共 10+ 调用点；
- `get_llm_service_for_specific_model(model_key, role)` 在同一共享实例上原地
  `switch_to_specific_model` —— standard_workflow 自定义专家、predictive、
  capsule、node_sector、cognitive、planning_benchmark 共 7 调用点。

修法：两个工厂改为返回**独立实例**（与已安全的 `get_llm_service_for_task` /
`get_configured_llm_service_for_tier` 同型），对外签名与返回类型不变；
角色缓存不再被任何工厂函数变更。`switch_*` 方法保留（multi_intent_service
等在自建实例上的用法合法），仅补注调用约束。

本文件全程注入 FakeRouter + StubProvider（零网络、零真实路由注册依赖），
chat 级断言直接捕获每请求实际使用的 model 名。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import app.services.llm_service as llm_service_module
from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import (
    LLMService,
    get_configured_llm_service,
    get_llm_service,
    get_llm_service_for_specific_model,
)

DEFAULT_KEY = "fake_default"
BATCH_KEY = "fake_batch"
DEEP_KEY = "fake_deep"


class _FakeConfig:
    """LLMSelection.config 的最小投影（_selection_matches_current 会逐字段比较）。"""

    def __init__(self, model_key: str):
        self.provider = SimpleNamespace(value="fake")
        self.model_name = model_key
        self.base_url = f"https://{model_key}.fake"
        self.temperature = 0.7
        self.clear_thinking = False


def _fake_selection(model_key: str, role: AgentRole, task_type: TaskType | None = None):
    return SimpleNamespace(
        model_key=model_key,
        config=_FakeConfig(model_key),
        agent_role=role,
        task_type=task_type,
        reason="fake",
        is_fallback=False,
    )


class FakeRouter:
    """确定性路由：默认档 fake_default；指定 key 原样返回；DEEP_REASONING → fake_deep。"""

    def __init__(self):
        self.specific_calls: list[str] = []

    def select_model(self, agent_role, task_type=None, avoid_providers=None,
                     reasoning_mode=None, force_tier=None, user_message=None, allow_max=False):
        role = agent_role if isinstance(agent_role, AgentRole) else AgentRole.GENERATION
        if task_type == TaskType.DEEP_REASONING:
            return _fake_selection(DEEP_KEY, role, task_type)
        return _fake_selection(DEFAULT_KEY, role, task_type)

    def select_specific_model(self, model_key, agent_role=AgentRole.GENERATION, task_type=None):
        role = agent_role if isinstance(agent_role, AgentRole) else AgentRole.GENERATION
        self.specific_calls.append(model_key)
        return _fake_selection(model_key, role, task_type)

    def get_openai_client_kwargs(self, selection):
        return {
            "api_key": f"key-{selection.model_key}",
            "base_url": selection.config.base_url,
            "model": selection.config.model_name,
        }

    # chat() 健康上报面（_report_call_outcome → report_model_*）
    def report_model_success(self, *args, **kwargs):
        return None

    def report_model_failure(self, *args, **kwargs):
        return None

    def resolve_model_key(self, *args, **kwargs):
        return None


class StubProvider:
    """记录构造与 chat 所用 model 的假 provider（替代 OpenAICompatibleProvider）。"""

    constructed: list[str] = []

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.has_api_key = bool(api_key)
        StubProvider.constructed.append(base_url)
        self.chat_calls: list[str] = []

    async def chat(self, messages, model=None, temperature=None, **kwargs):
        self.chat_calls.append(model)
        return f"reply-from:{model}"


@pytest.fixture()
def isolated_factory_env(monkeypatch):
    """注入 FakeRouter/StubProvider 并隔离角色缓存与 stub 状态。"""
    router = FakeRouter()
    StubProvider.constructed = []
    monkeypatch.setattr(llm_service_module, "llm_router", router)
    monkeypatch.setattr(llm_service_module, "OpenAICompatibleProvider", StubProvider)
    saved_cache = dict(llm_service_module._llm_service_cache)
    llm_service_module._llm_service_cache.clear()
    yield router
    llm_service_module._llm_service_cache.clear()
    llm_service_module._llm_service_cache.update(saved_cache)


def _default_service() -> LLMService:
    """直接构造（不走工厂）的默认档实例，作为「请求 B」的基准。"""
    return LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)


async def _chat_capture_model(service: LLMService) -> str:
    """走真实 chat() 主链，返回本次请求实际使用的 model 名。"""
    with patch.object(llm_service_module, "refresh_llm_safety_mode", async_noop), patch.object(
        llm_service_module, "is_llm_within_budget", async_true
    ), patch.object(
        llm_service_module.circuit_breaker_service, "check", async_noop
    ), patch.object(
        llm_service_module.circuit_breaker_service, "record_success", async_noop
    ), patch.object(
        llm_service_module.llm_fallback_manager,
        "execute_with_fallback",
        lambda selection, call, operation_type, require_tools=False: call(selection),
    ):
        reply = await service.chat([{"role": "user", "content": "hi"}])
    assert reply.startswith("reply-from:")
    return reply.removeprefix("reply-from:")


async def async_noop(*args, **kwargs):
    return None


async def async_true(*args, **kwargs):
    return True


class TestSpecificModelFactoryIsolation:
    @pytest.mark.asyncio
    async def test_specific_model_factory_returns_isolated_instance(self, isolated_factory_env):
        """P1-1 复现：specific-model 工厂不得改写按角色缓存的共享实例。

        修前：工厂在共享实例上原地 switch → 第二个「什么都没要求」的请求
        get_llm_service(role) 读到 batch 模型（跨请求串模型）。
        """
        svc_batch = await get_llm_service_for_specific_model(BATCH_KEY, AgentRole.GENERATION)
        assert svc_batch.model_key == BATCH_KEY

        # 请求 B：普通角色服务，未做任何切换请求
        plain = get_llm_service(AgentRole.GENERATION)
        assert plain is not svc_batch, "工厂不得返回被改写的共享缓存实例"
        assert plain.model_key != BATCH_KEY, "共享角色实例的路由状态被串改"
        assert plain.chat_model != BATCH_KEY
        assert plain.model_key == DEFAULT_KEY

        # 工厂返回值本身行为正确
        assert await _chat_capture_model(svc_batch) == BATCH_KEY

    @pytest.mark.asyncio
    async def test_concurrent_specific_model_requests_each_get_own_model(self, isolated_factory_env):
        """P1-1 复现（并发形态）：两个并发 specific-model 请求各得各的模型。

        修前两者拿到同一个共享实例，后完成的 switch 覆盖先完成的——
        两请求的 chat 实际都用 model_b。
        """
        svc_a, svc_b = await asyncio.gather(
            get_llm_service_for_specific_model("model_a", AgentRole.GENERATION),
            get_llm_service_for_specific_model("model_b", AgentRole.GENERATION),
        )
        assert svc_a.model_key == "model_a"
        assert svc_b.model_key == "model_b"
        assert svc_a is not svc_b

        used_a, used_b = await asyncio.gather(
            _chat_capture_model(svc_a), _chat_capture_model(svc_b)
        )
        assert used_a == "model_a", f"请求 A 实际用了 {used_a}（串模型）"
        assert used_b == "model_b", f"请求 B 实际用了 {used_b}（串模型）"


class TestConfiguredFactoryIsolation:
    @pytest.mark.asyncio
    async def test_configured_factory_with_task_type_does_not_mutate_shared_cache(
        self, isolated_factory_env
    ):
        """P1-1 复现：get_configured_llm_service(role, task_type) 不得改写共享实例。"""
        svc_deep = await get_configured_llm_service(AgentRole.GENERATION, TaskType.DEEP_REASONING)
        assert svc_deep.model_key == DEEP_KEY

        plain = get_llm_service(AgentRole.GENERATION)
        assert plain is not svc_deep
        assert plain.model_key == DEFAULT_KEY, "共享角色实例的路由状态被串改"
        assert await _chat_capture_model(plain) == DEFAULT_KEY
        assert await _chat_capture_model(svc_deep) == DEEP_KEY

    @pytest.mark.asyncio
    async def test_configured_factory_without_task_type_still_returns_cached_shared(
        self, isolated_factory_env
    ):
        """兼容面：不带 task_type 时维持原语义（返回按角色缓存的共享实例）。"""
        svc1 = get_llm_service(AgentRole.GENERATION)
        svc2 = await get_configured_llm_service(AgentRole.GENERATION)
        assert svc2 is svc1


class TestSharedInstanceUntouchedByFix:
    @pytest.mark.asyncio
    async def test_role_cache_survives_mixed_factory_traffic(self, isolated_factory_env):
        """混合流量压力：切换型工厂反复调用后，角色缓存实例始终停在初始选择。"""
        for key in ("model_x", "model_y", "model_z"):
            await get_llm_service_for_specific_model(key, AgentRole.GENERATION)
        await get_configured_llm_service(AgentRole.GENERATION, TaskType.DEEP_REASONING)

        plain = get_llm_service(AgentRole.GENERATION)
        assert plain.model_key == DEFAULT_KEY
        assert await _chat_capture_model(plain) == DEFAULT_KEY
