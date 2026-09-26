"""V3-FIX-78 / V3-FIX-79（wt448）——Q-06 波动注入实锤的弹性双缺陷红绿测试。

注入面复用 wt406 scripts/devtools/q06_provider_chaos.py 的口径（上游客户端层
全 provider 429 / 全部排队），此处以单测等价面复现其两个不合格场景：

V3-FIX-78（P1）全断供重试风暴无快速失败：
  chaos S2 实锤：全部 provider 429 时引擎内 fallback/重试链无总预算，
  record_failure 连续计数至 86、探针烧满 180s 客户端超时且多数无 error 帧。
  修后判据：
  - 全候选不健康（router 内存三相状态机或 redis tracker 任一判不健康）→
    LLMProvidersExhaustedError 快速失败，不打上游、毫秒级返回；
  - fallback 链总时延预算（LLM_FALLBACK_TOTAL_BUDGET_SECONDS）到点后拒绝
    发起新的上游尝试；
  - 候选全扫失败也以 LLMProvidersExhaustedError 收场（可被 build_safe_chat_error
    映射为 ERROR_CODE_UNAVAILABLE 诚实文案），不再把原始 429 一路静默上抛。

V3-FIX-79（P2）过载无背压：
  chaos S5 实锤：上游 5s 延迟 × 30 并发，22/30 静默烧满 150s 客户端超时
  （TTFT max 143.8s），排队期间用户只有 stage 帧。
  修后判据：
  - 并发池排队深度超 admission cap（LLM_POOL_MAX_WAITING）→ LLMOverloadedError
    快速拒绝（429 语义优先于超时），等槽者不再无限堆积；
  - LLMOverloadedError 映射为 ERROR_CODE_RATE_LIMITED 繁忙文案（用户可感知的
    诚实降级提示）。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.llm.concurrency import (
    PROVIDER_CONFIGS,
    ConcurrencyConfig,
    LLMConcurrencyManager,
    ProviderRuntimeState,
    ProviderType,
)
from app.services.llm.fallback import FallbackReason, LLMModelFallbackManager, ModelHealthTracker

# ---------------------------------------------------------------------------
# 测试替身：全部 provider 一律 429（对齐 q06_provider_chaos.py 的 429_all 模式）
# ---------------------------------------------------------------------------


class _All429Provider:
    """所有调用一律抛 429（chaos S2 total-outage 注入等价物）；记录每次上游尝试。"""

    calls: list[dict] = []

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 60.0):
        self.api_key = api_key
        self.base_url = base_url

    async def chat(self, messages, model, temperature=0.7, **kwargs):
        _All429Provider.calls.append({"base_url": self.base_url, "model": model})
        raise Exception("429 Too Many Requests (throttling)")

    async def stream_chat(self, messages, model, temperature=0.7, **kwargs):  # type: ignore[no-untyped-def]
        _All429Provider.calls.append({"base_url": self.base_url, "model": model})
        raise Exception("429 Too Many Requests (throttling)")
        yield ""  # pragma: no cover —— 使本函数成为 async generator


# ---------------------------------------------------------------------------
# 公共脚手架
# ---------------------------------------------------------------------------

_MODELS: dict[str, tuple[str, ModelTier]] = {
    "primary_standard": ("https://primary.test", ModelTier.STANDARD),
    "secondary_standard": ("https://secondary.test", ModelTier.STANDARD),
    "tertiary_plus": ("https://tertiary.test", ModelTier.PLUS),
}


def _cfg(model_key: str) -> ModelConfig:
    base_url, tier = _MODELS[model_key]
    return ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name=model_key,
        base_url=base_url,
        api_key="key",
        tier=tier,
    )


def _selection(model_key: str) -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=_cfg(model_key),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="test",
    )


@pytest.fixture
def outage_router(monkeypatch):
    """注册三模型 tier 映射 + 全 429 provider + 熔断器 no-op + 健康态复位。"""
    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {
            **{key: _cfg(key) for key in _MODELS},
            # llm_service 模块级单例构建时 select_model 需要 "default" 兜底键
            "default": _cfg("secondary_standard"),
        },
    )
    monkeypatch.setattr(
        llm_router,
        "_tier_mapping",
        {
            ModelTier.PLUS: ["tertiary_plus"],
            ModelTier.STANDARD: ["primary_standard", "secondary_standard"],
        },
    )
    monkeypatch.setattr("app.services.llm_service.OpenAICompatibleProvider", _All429Provider)

    async def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.check", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_success", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_failure", _noop)

    _All429Provider.calls = []
    # 内存健康态复位（跨用例隔离；llm_router 是全局单例）
    monkeypatch.setattr(llm_router, "_model_health", {})
    yield _All429Provider
    _All429Provider.calls = []


class _UnhealthyStubTracker(ModelHealthTracker):
    """redis tracker 判「全不健康」的桩（等价 chaos 现场 redis llm:circuit 全开）。"""

    async def is_healthy(self, model_key: str) -> bool:  # noqa: ARG002
        return False

    async def record_failure(self, model_key: str, reason: FallbackReason) -> None:
        return None


# ---------------------------------------------------------------------------
# V3-FIX-78：全断供快速失败
# ---------------------------------------------------------------------------


def _pollute_router_unhealthy(threshold: int = 5) -> None:
    """把三个模型在 router 内存三相状态机里全部推到 unhealthy（86 连败稳态的等价面）。"""
    for key in _MODELS:
        for _ in range(threshold):
            llm_router.report_model_failure(key)


@pytest.mark.asyncio
async def test_stream_total_outage_all_unhealthy_fails_fast_without_upstream_calls(outage_router):
    """全候选不健康 → 流式链毫秒级 LLMProvidersExhaustedError，零上游尝试。

    红证：现状 execute_stream_with_fallback 对 original_selection 不做健康预检，
    每次调用都打一次上游（S2 每请求重复该面 → 86 连败/180s 静默）。
    """
    manager = LLMModelFallbackManager(health_tracker=_UnhealthyStubTracker())
    _pollute_router_unhealthy()

    t0 = time.perf_counter()
    with pytest.raises(Exception) as exc_info:
        async for _ in manager.execute_stream_with_fallback(
            _selection("primary_standard"),
            _stream_fn_calls_counter(),
            operation_type="stream_chat",
        ):
            pass
    elapsed = time.perf_counter() - t0

    assert outage_router.calls == [], f"全候选不健康时不应打上游，实际: {outage_router.calls}"
    assert elapsed < 2.0, f"应快速失败，实际耗时 {elapsed:.2f}s"
    assert type(exc_info.value).__name__ == "LLMProvidersExhaustedError"


@pytest.mark.asyncio
async def test_chat_total_outage_all_unhealthy_fails_fast_without_upstream_calls(outage_router):
    """同上，非流式 execute_with_fallback 路径。"""
    manager = LLMModelFallbackManager(health_tracker=_UnhealthyStubTracker())
    _pollute_router_unhealthy()

    with pytest.raises(Exception) as exc_info:
        await manager.execute_with_fallback(
            _selection("primary_standard"),
            _call_fn_calls_counter(),
            operation_type="chat",
        )

    assert outage_router.calls == [], f"全候选不健康时不应打上游，实际: {outage_router.calls}"
    assert type(exc_info.value).__name__ == "LLMProvidersExhaustedError"


@pytest.mark.asyncio
async def test_stream_outage_sweep_exhaustion_raises_typed_error(outage_router):
    """健康态干净、但每次上游尝试都 429：链扫完候选后以 LLMProvidersExhaustedError 收场。

    红证：现状把原始 429 异常直接上抛（build_safe_chat_error 落入泛化内部分支），
    且上游尝试面不受总预算约束。
    """
    manager = LLMModelFallbackManager(health_tracker=_AlwaysHealthyTracker())

    with pytest.raises(Exception) as exc_info:
        async for _ in manager.execute_stream_with_fallback(
            _selection("primary_standard"),
            _stream_fn_calls_counter(),
            operation_type="stream_chat",
        ):
            pass

    assert type(exc_info.value).__name__ == "LLMProvidersExhaustedError"
    # 每个模型至多一次上游尝试（S2 的 86 连败倍增面被钳住）
    tried_models = [c["model"] for c in outage_router.calls]
    assert len(tried_models) <= len(_MODELS), f"候选扫描应每模型至多一次，实际 {tried_models}"


@pytest.mark.asyncio
async def test_chat_outage_sweep_exhaustion_raises_typed_error(outage_router, monkeypatch):
    """非流式同判据；且总时延预算到点后不再发起新尝试。"""
    monkeypatch.setattr(settings, "LLM_FALLBACK_TOTAL_BUDGET_SECONDS", 0.2)
    manager = LLMModelFallbackManager(health_tracker=_AlwaysHealthyTracker())

    async def _slow_call_fn(selection: LLMSelection) -> str:
        # 模拟每次尝试 0.15s 后 429（三次候选 ≈ 0.45s > 预算 0.2s）
        await asyncio.sleep(0.15)
        outage_router.calls.append({"base_url": selection.config.base_url, "model": selection.model_key})
        raise Exception("429 Too Many Requests (throttling)")

    t0 = time.perf_counter()
    with pytest.raises(Exception) as exc_info:
        await manager.execute_with_fallback(_selection("primary_standard"), _slow_call_fn, operation_type="chat")
    elapsed = time.perf_counter() - t0

    assert type(exc_info.value).__name__ == "LLMProvidersExhaustedError"
    # 预算 0.2s + 单次尝试 0.15s：最多 2 次尝试就应收场（红证现状会扫满 3 候选）
    assert len(outage_router.calls) <= 2, f"预算到点应拒绝新尝试，实际尝试 {len(outage_router.calls)} 次"
    assert elapsed < 1.0, f"应快速收场，实际 {elapsed:.2f}s"


def _stream_fn_calls_counter():
    async def _stream_fn(selection: LLMSelection):  # type: ignore[no-untyped-def]
        _All429Provider.calls.append({"base_url": selection.config.base_url, "model": selection.model_key})
        raise Exception("429 Too Many Requests (throttling)")
        yield ""  # pragma: no cover

    return _stream_fn


def _call_fn_calls_counter():
    async def _call_fn(selection: LLMSelection) -> str:
        _All429Provider.calls.append({"base_url": selection.config.base_url, "model": selection.model_key})
        raise Exception("429 Too Many Requests (throttling)")

    return _call_fn


class _AlwaysHealthyTracker(ModelHealthTracker):
    """恒健康 tracker——扫描面不受本机 redis（sparkle_redis 可能在位）计数影响。

    显式恒健康（而非依赖 cache_service.redis is None 的缺省路径）：本机若起着
    sparkle_redis，tracker 会真实计数，阈值翻转让候选扫描面不确定。
    """

    async def is_healthy(self, model_key: str) -> bool:  # noqa: ARG002
        return True

    async def record_failure(self, model_key: str, reason: FallbackReason) -> None:  # noqa: ARG002
        return None


# ---------------------------------------------------------------------------
# V3-FIX-79：过载背压（admission cap → 快速拒绝）
# ---------------------------------------------------------------------------


def _fresh_manager(monkeypatch, *, max_concurrent: int, queue_timeout: float, max_waiting: int):
    monkeypatch.setattr(settings, "LLM_POOL_MAX_WAITING", max_waiting)
    config = ConcurrencyConfig(max_concurrent=max_concurrent, queue_timeout=queue_timeout)
    monkeypatch.setitem(PROVIDER_CONFIGS, ProviderType.ZHIPU, config)
    manager = LLMConcurrencyManager()
    # 只保留被测 provider 的运行态（隔离其他 provider 的自适应状态）
    manager._runtime = {
        ProviderType.ZHIPU: ProviderRuntimeState(config=config, current_limit=max_concurrent)
    }
    return manager


@pytest.mark.asyncio
async def test_pool_admission_cap_rejects_excess_waiters_fast(monkeypatch):
    """排队超 cap → LLMOverloadedError 毫秒级拒绝；429 语义优先于等满 queue_timeout。

    红证：现状无 admission cap，30 并发全量入队等满 30s（S5：22/30 烧满 150s）。
    """
    manager = _fresh_manager(
        monkeypatch, max_concurrent=1, queue_timeout=30.0, max_waiting=2
    )

    async def _holder():
        async with manager.acquire("zhipu"):
            await asyncio.sleep(0.5)  # 占住唯一槽位片刻，制造排队面

    holder_task = asyncio.create_task(_holder())
    await asyncio.sleep(0.05)  # 让 holder 占住唯一槽位

    async def _waiter(i: int) -> str:
        try:
            async with manager.acquire("zhipu"):
                return "acquired"
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__

    t0 = time.perf_counter()
    results = await asyncio.wait_for(
        asyncio.gather(*[_waiter(i) for i in range(5)]),
        timeout=10.0,
    )
    elapsed = time.perf_counter() - t0
    await holder_task

    overloaded = [r for r in results if r == "LLMOverloadedError"]
    acquired = [r for r in results if r == "acquired"]
    assert overloaded, f"超 cap 的排队者应被 LLMOverloadedError 快速拒绝，实际 {results}"
    assert acquired, f"cap 内的排队者应正常等槽成功，实际 {results}"
    # 拒绝远快于 queue_timeout(30s)：holder 0.5s 释放 + 排队者随后快速拿到槽位
    assert elapsed < 5.0, f"拒绝应远快于 queue_timeout，实际 {elapsed:.2f}s"
    state = manager._runtime[ProviderType.ZHIPU]
    assert state.waiting <= 2, f"排队深度不得超过 cap，实际 {state.waiting}"


@pytest.mark.asyncio
async def test_pool_admission_cap_not_triggered_under_capacity(monkeypatch):
    """未超 cap 时正常获取槽位（背压不误伤正常并发）。"""
    manager = _fresh_manager(
        monkeypatch, max_concurrent=2, queue_timeout=5.0, max_waiting=4
    )

    async def _worker() -> str:
        async with manager.acquire("zhipu"):
            await asyncio.sleep(0.05)
            return "ok"

    results = await asyncio.gather(*[_worker() for _ in range(4)])
    assert results == ["ok"] * 4


# ---------------------------------------------------------------------------
# 用户可见语义：typed error → 诚实错误帧字段
# ---------------------------------------------------------------------------


def test_build_safe_chat_error_maps_providers_exhausted():
    """FIX-78：全断供 typed error → ERROR_CODE_UNAVAILABLE + 诚实文案（非泛化内部错误）。"""
    from app.core.exceptions import LLMProvidersExhaustedError  # noqa: PLC0415
    from app.core.safe_error_messages import build_safe_chat_error  # noqa: PLC0415
    from app.gen.agent.v1 import agent_service_pb2  # noqa: PLC0415

    message, error_code, retryable = build_safe_chat_error(
        LLMProvidersExhaustedError("all providers exhausted")
    )
    assert error_code == agent_service_pb2.ERROR_CODE_UNAVAILABLE
    assert retryable is True
    assert message and "稍后" in message


def test_build_safe_chat_error_maps_overloaded():
    """FIX-79：过载 typed error → ERROR_CODE_RATE_LIMITED + 繁忙文案（429 语义）。"""
    from app.core.exceptions import LLMOverloadedError  # noqa: PLC0415
    from app.core.safe_error_messages import build_safe_chat_error  # noqa: PLC0415
    from app.gen.agent.v1 import agent_service_pb2  # noqa: PLC0415

    message, error_code, retryable = build_safe_chat_error(
        LLMOverloadedError("engine busy: queue full")
    )
    assert error_code == agent_service_pb2.ERROR_CODE_RATE_LIMITED
    assert retryable is True
    assert message and "繁忙" in message


def test_generation_fast_fail_helper_scope():
    """generation 链只对两个 typed error 快速失败放行；其余异常保持既有 rescue/模板语义。"""
    from app.agents.standard_workflow import _should_fast_fail_generation  # noqa: PLC0415
    from app.core.exceptions import (  # noqa: PLC0415
        LLMOverloadedError,
        LLMProvidersExhaustedError,
        LLMServiceError,
    )

    assert _should_fast_fail_generation(LLMProvidersExhaustedError("x")) is True
    assert _should_fast_fail_generation(LLMOverloadedError("x")) is True
    assert _should_fast_fail_generation(ValueError("x")) is False
    assert _should_fast_fail_generation(LLMServiceError("x")) is False
    assert _should_fast_fail_generation(TimeoutError()) is False
    # 单个 provider 失败（可 fallback 换道）不触发整轮快速失败
    assert _should_fast_fail_generation(Exception("429 Too Many Requests")) is False


def test_settings_defaults_registered():
    """新设置项存在且默认值与卡片语义一致（预算>0、cap 有界）。"""
    assert getattr(settings, "LLM_FALLBACK_TOTAL_BUDGET_SECONDS", 0) > 0
    assert getattr(settings, "LLM_POOL_MAX_WAITING", 0) > 0


def test_no_healthy_candidates_message_is_typed():
    """既有「无健康候选」路径升级为 typed error（保持可被安全错误映射消费）。"""
    from app.core.exceptions import LLMProvidersExhaustedError  # noqa: PLC0415

    err = LLMProvidersExhaustedError("No healthy fallback models available after 2 attempts")
    assert "No healthy fallback models" in str(err)
    assert err.status_code == 503


# ---------------------------------------------------------------------------
# V3-FIX-78/79 集成验证补丁（wt460）：statechart 节点错误包装不得吞掉 typed error
#
# 真栈 chaos 复跑实锤（wt460，engine :50062 + mock :9099）：S2 全断供下
# generation_node 快速放行的 LLMProvidersExhaustedError 在 statechart_engine.invoke
# 的节点错误包装处被替换为 RuntimeError("Graph ... aborted due to node error(s)...")
# —— orchestrator 的 build_safe_chat_error 收到的是 RuntimeError，落入泛化
# ERROR_CODE_INTERNAL「系统暂时不可用」分支，wt448 声明的 ERROR_CODE_UNAVAILABLE
# 「AI 服务暂时全部不可用」专属文案在真实栈上不出现（单测直测 build_safe_chat_error
# 测不到该包装面）。LLMOverloadedError 同型。修后判据：两个 typed fast-fail 异常
# 原样穿透 statechart 边界；其余节点错误维持既有 RuntimeError 包装语义不变。
# ---------------------------------------------------------------------------


def _graph_whose_node_raises(exc: Exception):
    from app.orchestration.statechart_engine import StateGraph

    async def _boom(_state):  # noqa: ANN202
        raise exc

    graph = StateGraph("WT460TypedErrorProbe")
    graph.add_node("generation", _boom)
    graph.set_entry_point("generation")
    graph.add_edge("generation", "__end__")
    return graph


def _fresh_workflow_state():
    from app.orchestration.statechart_engine import WorkflowState

    return WorkflowState()


@pytest.mark.asyncio
async def test_statechart_preserves_providers_exhausted_typed_error():
    """FIX-78：LLMProvidersExhaustedError 原样穿透 statechart（不得包装成 RuntimeError）。"""
    from app.core.exceptions import LLMProvidersExhaustedError  # noqa: PLC0415

    graph = _graph_whose_node_raises(LLMProvidersExhaustedError("all candidates unhealthy; failing fast"))
    with pytest.raises(LLMProvidersExhaustedError):
        await graph.invoke(_fresh_workflow_state())


@pytest.mark.asyncio
async def test_statechart_preserves_overloaded_typed_error():
    """FIX-79：LLMOverloadedError 原样穿透 statechart（不得包装成 RuntimeError）。"""
    from app.core.exceptions import LLMOverloadedError  # noqa: PLC0415

    graph = _graph_whose_node_raises(LLMOverloadedError("queue depth 21 exceeds admission cap 20"))
    with pytest.raises(LLMOverloadedError):
        await graph.invoke(_fresh_workflow_state())


@pytest.mark.asyncio
async def test_statechart_still_wraps_generic_node_errors():
    """回归锁：其余节点错误维持既有 RuntimeError 包装语义（修复不扩面）。"""
    graph = _graph_whose_node_raises(ValueError("boom"))
    with pytest.raises(RuntimeError):
        await graph.invoke(_fresh_workflow_state())
