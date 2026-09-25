"""wt380 Tier 塌缩三因修复守卫（E-08 基准发现）。

E-08 实证（主仓 v3-output/WT372-E08-BENCH）：85/85 条带 token 生成行全部落
dashscope_fast，pro 车道/deep 档无一到达 standard/plus/max——L1/L2/L3 tier
差异在当前构建不存在。三因红测：

① extra_context.user_tier 死键：Struct 键经不同序列化路径存在 camelCase
   （userTier）形态，_resolve_request_user_tier 只读 snake_case → tier 信号
   丢失。契约：两形态都必须正确解析。
② 自适应重排启发式越权：samples>=8 的持久化启发式把显式 deep/pro 意图的
   E-02 偏好链头稳定翻到 cheap/fast 模型（bench 窗口该日志 90 次）。契约：
   启发式只作用于无明确信号的默认流量；显式 deep 意图或 pro 档位不被降档。
③ 多代理 fan-out 丢信号：ChatOrchestrator 全图经 BackgroundTaskManager.spawn
   的长驻 queue worker 创建任务，内层任务运行在 worker 创建时刻的上下文快照
   里——请求级 tier ContextVar 不随请求传播（E-08 实证子代理 pro->fast
   clamp 与主请求档位无关）。契约：spawn 的内层协程继承 spawn 调用方的
   contextvars（与 asyncio.create_task 原生语义一致）。
"""

from __future__ import annotations

import asyncio

import pytest

from app.config import settings
from app.core.adaptive_routing import adaptive_routing_engine
from app.core.agent_profiles import AgentRole
from app.core.llm_router import (
    LLMRouter,
    get_request_user_tier,
    llm_router,
    reset_request_user_tier,
    set_request_user_tier,
)
from app.core.task_manager import BackgroundTaskManager

# E-07 同款确定性池：清空 .env 泄漏的 *_API_KEY/LLM_TIER_*，路由器池与
# 无 key 环境一致，断言不随主仓 shell 漂移。
DEEP_CHAIN_HEAD = "dashscope_standard_thinking"  # deep 偏好链首位（E-02 权威）
CHEAP_RIVAL = "dashscope_chat"  # PLUS 层 non-thinking 便宜模型（启发式宠儿）


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    from app.config import settings as _s

    for k in [k for k in vars(_s) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]:
        monkeypatch.setattr(_s, k, "")


@pytest.fixture(autouse=True)
def _isolate_adaptive_state():
    """隔离自适应滑窗与路由器健康态，防跨测试污染（E-07 同款）。"""
    from app.core import routing_audit

    saved_stats = dict(adaptive_routing_engine._stats)
    saved_health = dict(llm_router._model_health)
    adaptive_routing_engine._stats.clear()
    llm_router._model_health.clear()
    routing_audit.clear()
    yield
    adaptive_routing_engine._stats.clear()
    adaptive_routing_engine._stats.update(saved_stats)
    llm_router._model_health.clear()
    llm_router._model_health.update(saved_health)
    routing_audit.clear()


@pytest.fixture(autouse=True)
def _clean_user_tier():
    token = set_request_user_tier(None)
    yield
    reset_request_user_tier(token)


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter()


def _seed_heuristic_favors_cheap_rival() -> None:
    """喂满 MIN_SAMPLES：便宜快的 rival 高分，deep 链头慢模型低分。

    这正是 E-08 bench 窗口的积累形态：flash 车道大量成功样本把启发式
    评分拉满，深档链头被稳定翻掉。
    """
    for _ in range(10):
        adaptive_routing_engine.record_outcome(CHEAP_RIVAL, latency_ms=100.0, success=True, cost_per_1k=0.0001)
        adaptive_routing_engine.record_outcome(DEEP_CHAIN_HEAD, latency_ms=9000.0, success=True, cost_per_1k=0.001)


# ---------------------------------------------------------------------------
# ① extra_context.user_tier：camelCase / snake_case 两形态都可达
# ---------------------------------------------------------------------------


def test_resolve_request_user_tier_accepts_snake_case_key(router: LLMRouter):
    """snake_case 直填（Python 客户端/网关 structpb.NewStruct）——存量契约不回退。"""
    from app.gen.agent.v1 import agent_service_pb2
    from app.services.agent_grpc_service import AgentServiceImpl

    req = agent_service_pb2.ChatRequest(extra_context={"user_tier": "pro"})
    assert AgentServiceImpl._resolve_request_user_tier(req) == "pro"


def test_resolve_request_user_tier_accepts_camel_case_key():
    """camelCase 键（protojson/MessageToDict 往返产物）当前是死键——必红修复。"""
    from app.gen.agent.v1 import agent_service_pb2
    from app.services.agent_grpc_service import AgentServiceImpl

    req = agent_service_pb2.ChatRequest(extra_context={"userTier": "pro"})
    assert AgentServiceImpl._resolve_request_user_tier(req) == "pro"


def test_resolve_request_user_tier_camel_case_free_still_overrides_to_free():
    """camelCase 形态的 free 覆盖同样生效（钳制语义不能被绕过）。"""
    from app.gen.agent.v1 import agent_service_pb2
    from app.services.agent_grpc_service import AgentServiceImpl

    req = agent_service_pb2.ChatRequest(
        user_profile=agent_service_pb2.UserProfile(is_pro=True),
        extra_context={"userTier": "free"},
    )
    assert AgentServiceImpl._resolve_request_user_tier(req) == "free"


# ---------------------------------------------------------------------------
# ② 显式 deep/pro 意图不被 samples 启发式降档
# ---------------------------------------------------------------------------


def test_explicit_deep_with_pro_tier_not_demoted_by_adaptive_reorder(router: LLMRouter):
    """pro 档 + 显式 deep：E-02 deep 偏好链头必须保位（当前被翻到 cheap rival——红）。"""
    _seed_heuristic_favors_cheap_rival()
    token = set_request_user_tier("pro")
    try:
        assert get_request_user_tier() == "pro"
        selection = router.select_model(AgentRole.GENERATION, reasoning_mode="deep")
        assert selection.model_key == DEEP_CHAIN_HEAD, (
            f"显式 deep+pro 被启发式降档到 {selection.model_key}" f"（tier={selection.config.tier.value}）——Tier 塌缩②"
        )
    finally:
        reset_request_user_tier(token)


def test_explicit_deep_without_tier_signal_not_demoted_by_adaptive_reorder(router: LLMRouter):
    """未标注档位 + 显式 deep：深推理偏好链同样不许被启发式翻头。"""
    _seed_heuristic_favors_cheap_rival()
    selection = router.select_model(AgentRole.GENERATION, reasoning_mode="deep")
    assert selection.model_key == DEEP_CHAIN_HEAD, f"显式 deep 被启发式降档到 {selection.model_key}——Tier 塌缩②"


def test_default_traffic_still_allows_adaptive_reorder(router: LLMRouter):
    """对照：无明确信号的默认流量（balanced/未标注）启发式仍然生效——防过修。"""
    _seed_heuristic_favors_cheap_rival()
    selection = router.select_model(AgentRole.GENERATION)
    assert selection.model_key == CHEAP_RIVAL, "默认流量必须保留 E-07 自适应重排语义"


# ---------------------------------------------------------------------------
# ③ task_manager.spawn 跨队列边界继承请求 contextvars
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_manager_spawn_preserves_request_tier_contextvar():
    """spawn 内层协程必须继承 spawn 调用方的 tier ContextVar。

    先用无 tier 上下文 prime 出长驻 worker（复刻生产：worker 创建于某个
    更早/无关请求），再在 pro 上下文里 spawn——内层读到的是 pro 而不是
    worker 快照。当前实现读到 None（worker 上下文）——红。
    """
    tm = BackgroundTaskManager()

    async def _prime() -> None:
        return None

    prime_handle = await tm.spawn(_prime(), task_name="wt380-prime")
    await asyncio.wait_for(prime_handle, timeout=2.0)

    token = set_request_user_tier("pro")
    seen: dict[str, str | None] = {}

    async def _probe() -> None:
        seen["tier"] = get_request_user_tier()

    try:
        handle = await tm.spawn(_probe(), task_name="wt380-probe")
        await asyncio.wait_for(handle, timeout=2.0)
    finally:
        reset_request_user_tier(token)

    assert seen["tier"] == "pro", (
        f"spawn 内层读到 tier={seen['tier']!r}（期望 pro）——"
        "queue worker 上下文快照吞掉请求级 ContextVar，多代理 fan-out 丢信号"
    )


# ---------------------------------------------------------------------------
# settings 面干净收尾（未新增 settings 键，防呆断言）
# ---------------------------------------------------------------------------


def test_no_new_settings_keys_introduced():
    """本卡零新增配置：三因修复全部走代码内聚语义，不引入开关漂移面。"""
    assert not any("WT380" in name for name in vars(settings))
