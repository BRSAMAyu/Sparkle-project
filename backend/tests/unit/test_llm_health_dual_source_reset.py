"""V3-FIX-81（wt456b）——模型健康双源不同步无复位出口红绿测试。

Q-06 chaos S3a 实锤（v3-output/WT406-Q06-PERF/chaos_results.json）：故障演练
清 redis `llm:*` 三相状态后，生成仍持续避开目标模型（3s 完成 mock 链）——
llm_router 内存健康态与 redis tracker 并行生效，**只清一个源不复位另一个**，
「已恢复的 provider」被残留内存态跳过；重启引擎才恢复（18.7-58.2s 真实慢
TTFT 对照）。运维排障同踩此坑，且不存在同时清双源的管理面出口。

修后判据（只补同步/复位出口，不改判定语义）：
- 内存面：router 三相状态机可显式复位到 healthy（未注册 key 无操作）；
  复位后状态机既有语义不变（再连续失败仍会照常转 unhealthy）；
- redis 面：tracker 三族键（llm:fail / llm:last_fail / llm:circuit）可按 key
  或全量清除；熔断打开态清除后 is_healthy 恢复；
- 双源单出口：管理面一次调用同时清内存+redis（消除「清一源漏一源」陷阱）；
  复位后 `_preflight_all_unhealthy` 不再误判全不健康，fallback 链可正常发起
  上游尝试（与 wt448 V3-FIX-78 预检协同，判定逻辑零改动）。
"""

from __future__ import annotations

from typing import Any

import fakeredis
import pytest

import app.api.v1.llm_health_admin as llm_health_admin
from app.core.llm_router import llm_router
from app.services.llm import fallback as fallback_module
from app.services.llm.fallback import FallbackReason, ModelHealthTracker

# ---------------------------------------------------------------------------
# 隔离脚手架：单例健康态逐例保存/恢复（对齐 wt444 隔离审计纪律）
# ---------------------------------------------------------------------------

_MEMORY_TEST_KEYS = ("primary_standard", "secondary_standard")


def _test_cfg(model_key: str):  # noqa: ANN001, ANN202
    from app.core.agent_profiles import ModelTier  # noqa: PLC0415
    from app.core.llm_router import ModelConfig, ModelProvider  # noqa: PLC0415

    return ModelConfig(
        model_name=f"test-{model_key}",
        provider=ModelProvider.DASHSCOPE,
        api_key="k",
        base_url="https://test",
        tier=ModelTier.STANDARD,
    )


@pytest.fixture()
def isolated_router_health(monkeypatch):
    """注册测试模型键 + 保存/恢复单例健康态（llm_router 为全局单例）。"""
    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {key: _test_cfg(key) for key in _MEMORY_TEST_KEYS},
    )
    saved = dict(llm_router._model_health)
    yield llm_router
    llm_router._model_health.clear()
    llm_router._model_health.update(saved)


@pytest.fixture()
def fake_redis_tracker(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    tracker = ModelHealthTracker()
    monkeypatch.setattr(fallback_module.cache_service, "redis", fake, raising=False)
    yield tracker, fake
    monkeypatch.setattr(fallback_module.cache_service, "redis", None, raising=False)


# ---------------------------------------------------------------------------
# 内存面：router 三相状态机复位出口
# ---------------------------------------------------------------------------


def test_memory_unhealthy_reset_to_healthy(isolated_router_health):
    key = "primary_standard"
    for _ in range(5):
        llm_router.report_model_failure(key)
    assert not llm_router._is_model_healthy(key)

    reset_keys = llm_router.reset_model_health(key)

    assert reset_keys == [key]
    assert llm_router._is_model_healthy(key)
    assert llm_router._health_rank(key) == 0


def test_memory_reset_keeps_state_machine_semantics(isolated_router_health):
    """复位不改判定语义：复位后再连续失败仍照常转 unhealthy。"""
    key = "primary_standard"
    for _ in range(5):
        llm_router.report_model_failure(key)
    llm_router.reset_model_health(key)
    assert llm_router._is_model_healthy(key)

    for _ in range(5):
        llm_router.report_model_failure(key)
    assert not llm_router._is_model_healthy(key)


def test_memory_reset_single_key_scoped(isolated_router_health):
    for key in ("primary_standard", "secondary_standard"):
        for _ in range(5):
            llm_router.report_model_failure(key)

    llm_router.reset_model_health("primary_standard")

    assert llm_router._is_model_healthy("primary_standard")
    assert not llm_router._is_model_healthy("secondary_standard")


def test_memory_reset_all_and_unregistered_noop(isolated_router_health):
    for key in ("primary_standard", "secondary_standard"):
        for _ in range(5):
            llm_router.report_model_failure(key)

    assert llm_router.reset_model_health("not_a_registered_key") == []
    reset_keys = llm_router.reset_model_health(None)

    assert set(reset_keys) == {"primary_standard", "secondary_standard"}
    assert llm_router._is_model_healthy("primary_standard")
    assert llm_router._is_model_healthy("secondary_standard")


# ---------------------------------------------------------------------------
# redis 面：tracker 三族键复位出口
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_circuit_open_reset_restores_health(fake_redis_tracker):
    tracker, fake = fake_redis_tracker
    key = "primary_standard"
    for _ in range(tracker.failure_threshold):
        await tracker.record_failure(key, FallbackReason.UNKNOWN_ERROR)
    assert not await tracker.is_healthy(key)

    cleared = await tracker.reset_health(key)

    assert cleared >= 2  # llm:fail + llm:circuit（last_fail 亦应有）
    assert await tracker.is_healthy(key)
    assert await fake.get(f"{tracker.FAILURE_COUNT_PREFIX}{key}") is None
    assert await fake.get(f"{tracker.CIRCUIT_OPEN_PREFIX}{key}") is None


@pytest.mark.asyncio
async def test_redis_reset_all_scopes_and_noop(fake_redis_tracker):
    tracker, _fake = fake_redis_tracker
    for key in ("primary_standard", "secondary_standard"):
        for _ in range(tracker.failure_threshold):
            await tracker.record_failure(key, FallbackReason.UNKNOWN_ERROR)

    assert await tracker.reset_health("not_registered_anywhere") == 0
    cleared = await tracker.reset_health(None)

    assert cleared >= 6
    assert await tracker.is_healthy("primary_standard")
    assert await tracker.is_healthy("secondary_standard")


# ---------------------------------------------------------------------------
# 双源单出口：管理面一次调用同时清内存+redis（FIX-81 核心）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dual_source_single_reset_exit(monkeypatch, isolated_router_health):
    """陷阱场景复现：内存不健康 + redis 熔断开；只清 redis（排障惯性操作）
    后 fallback 预检仍判不可试（内存残留）；管理面单出口一次清双源后恢复。"""
    key = "primary_standard"
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    tracker = ModelHealthTracker()
    monkeypatch.setattr(fallback_module.cache_service, "redis", fake, raising=False)
    monkeypatch.setattr(llm_health_admin, "llm_fallback_manager", fallback_module.LLMModelFallbackManager(health_tracker=tracker))
    try:
        for _ in range(5):
            llm_router.report_model_failure(key)
        for _ in range(tracker.failure_threshold):
            await tracker.record_failure(key, FallbackReason.UNKNOWN_ERROR)

        # 陷阱操作：只清 redis —— 内存残留仍把 provider 挡在门外
        await tracker.reset_health(key)
        selection = _selection_for(key)
        manager = llm_health_admin.llm_fallback_manager
        assert not await manager._model_tryable(selection.model_key)

        # 重新弄脏 redis 面，让单出口在「双源皆脏」现场执行
        for _ in range(tracker.failure_threshold):
            await tracker.record_failure(key, FallbackReason.UNKNOWN_ERROR)

        # 管理面单出口：一次调用双源复位
        result: dict[str, Any] = await llm_health_admin.reset_llm_health_sources(model_key=key)

        assert key in result["memory_reset_keys"]
        assert result["redis_cleared_keys"] >= 2
        assert await manager._model_tryable(key)
    finally:
        monkeypatch.setattr(fallback_module.cache_service, "redis", None, raising=False)


def _selection_for(model_key: str):  # noqa: ANN001, ANN202
    from app.core.agent_profiles import AgentRole, ModelTier  # noqa: PLC0415
    from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider  # noqa: PLC0415

    config = ModelConfig(
        model_name="test-model",
        provider=ModelProvider.DASHSCOPE,
        api_key="k",
        base_url="https://test",
        tier=ModelTier.STANDARD,
    )
    return LLMSelection(
        model_key=model_key,
        config=config,
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="test",
    )
