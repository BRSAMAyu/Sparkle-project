"""BATCH-CAP（PROD-LOG2 ②-2）· MiniMax 车道故障级联 + 队列饱和丢任务修复面.

覆盖卡面四类验收（模拟双 worker 竞争，不真起双 worker 压测）：
- 信号量超时源头可诊断：wait_for 到点的空 str TimeoutError 统一转带池快照
  的消息（实测 22 条空消息 error 的源头）；
- 双 worker 竞争语义：池满时新 waiter 快速失败（MINIMAX fast-fail），持槽
  释放后 waiter 被唤醒（不丢唤醒、不永久卡死）；
- fallback 分类：TimeoutError 类型先行 → 可重试 TIMEOUT（空 str 不再被误判
  Non-retryable 直接抛出，45s 排队白等后连 fallback 都不进）；
- 队列饱和可观测：饱和开始 ERROR / 周期性 ERROR 汇总 / 恢复 INFO，丢弃
  可观测为速率与时长而非逐条 WARNING。
"""

from __future__ import annotations

import asyncio

import pytest
from loguru import logger as loguru_logger

from app.config import settings
from app.core import queue_backpressure as qbp
from app.services.llm import concurrency as llm_concurrency_module
from app.services.llm.concurrency import (
    PROVIDER_CONFIGS,
    ConcurrencyConfig,
    LLMConcurrencyManager,
    ProviderType,
)
from app.services.llm.fallback import LLMModelFallbackManager, LLMSelection


def _fresh_manager(limit: int, timeout: float) -> LLMConcurrencyManager:
    """构造独立 MINIMAX 配置的 manager（不依赖 settings/redis 的自适应面）。"""
    original = llm_concurrency_module.PROVIDER_CONFIGS
    llm_concurrency_module.PROVIDER_CONFIGS = {
        ProviderType.MINIMAX: ConcurrencyConfig(
            max_concurrent=limit,
            min_concurrent=1,
            queue_timeout=timeout,
        ),
    }
    try:
        return LLMConcurrencyManager()
    finally:
        llm_concurrency_module.PROVIDER_CONFIGS = original


# ---------------------------------------------------------------------------
# 1. 信号量超时源头可诊断 + 配置对齐
# ---------------------------------------------------------------------------


class TestSemaphoreTimeoutDiagnostics:
    async def test_timeout_message_nonempty_with_pool_snapshot(self):
        """池满 + 等待到点 → TimeoutError 消息非空且含 provider/池水位。"""
        manager = _fresh_manager(limit=1, timeout=0.05)
        async with manager.acquire("minimax", timeout=30.0):
            with pytest.raises(TimeoutError) as exc_info:
                async with manager.acquire("minimax", timeout=0.05):
                    pass
        message = str(exc_info.value)
        assert message.strip(), "timeout message must not be empty (PROD-LOG2 empty-message disease)"
        assert "minimax" in message
        assert "limit=1" in message

    async def test_wait_for_expiry_path_also_diagnostic(self):
        """持槽者永不释放 → wait_for 到点路径同样产出带快照的消息（原空 str 源头）。"""
        manager = _fresh_manager(limit=1, timeout=30.0)
        async with manager.acquire("minimax", timeout=30.0):
            with pytest.raises(TimeoutError) as exc_info:
                async with manager.acquire("minimax", timeout=0.05):
                    pass
        message = str(exc_info.value)
        assert message.strip()
        assert "minimax" in message

    async def test_minimax_config_aligned_to_settings(self):
        """MINIMAX 池超时/上限对齐 settings（45s 固定值 → settings 化 fast-fail）。"""
        config = PROVIDER_CONFIGS[ProviderType.MINIMAX]
        assert config.queue_timeout == settings.MINIMAX_QUEUE_TIMEOUT_SECONDS
        assert config.max_concurrent == settings.MINIMAX_MAX_CONCURRENCY
        assert settings.MINIMAX_QUEUE_TIMEOUT_SECONDS < 45.0

    def test_minimax_route_string_maps_to_minimax_pool(self):
        """minimax_m3_batch 路由名必须落 MINIMAX 池（provider 隔离回归钉）。"""
        manager = LLMConcurrencyManager()
        assert manager._get_provider_type("minimax_m3_batch") is ProviderType.MINIMAX


# ---------------------------------------------------------------------------
# 2. 双 worker 竞争（进程内模拟：N 并发任务抢同一池）
# ---------------------------------------------------------------------------


class TestDualWorkerContention:
    async def test_waiters_wake_on_release_no_loss(self):
        """4 个并发任务抢 2 槽：分批成功、无超时、无唤醒丢失。"""
        manager = _fresh_manager(limit=2, timeout=5.0)
        done: list[int] = []

        async def worker(idx: int):
            async with manager.acquire("minimax", timeout=5.0):
                await asyncio.sleep(0.05)
                done.append(idx)

        await asyncio.gather(*(worker(i) for i in range(4)))
        assert sorted(done) == [0, 1, 2, 3]
        state = manager.get_provider_runtime_state("minimax")
        assert state["active"] == 0

    async def test_saturated_pool_fails_fast(self):
        """持槽者挂住 + 队列饱和 → waiter 快速失败（不再挂 45s），消息可诊断。"""
        manager = _fresh_manager(limit=1, timeout=0.05)
        async with manager.acquire("minimax", timeout=30.0):
            state = manager.get_provider_runtime_state("minimax")
            assert state["active"] == 1
            with pytest.raises(TimeoutError):
                async with manager.acquire("minimax", timeout=0.05):
                    pass
        # 槽释放后可复用（泄漏回归钉）
        async with manager.acquire("minimax", timeout=1.0):
            state = manager.get_provider_runtime_state("minimax")
            assert state["active"] == 1

    async def test_release_wakes_blocked_waiter(self):
        """持槽释放精确唤醒一个阻塞 waiter（condition notify 面回归）。"""
        manager = _fresh_manager(limit=1, timeout=5.0)
        acquired = asyncio.Event()

        async def holder():
            async with manager.acquire("minimax", timeout=5.0):
                acquired.set()
                await asyncio.sleep(0.1)

        async def waiter():
            await acquired.wait()
            async with manager.acquire("minimax", timeout=5.0):
                pass

        await asyncio.gather(holder(), waiter())
        state = manager.get_provider_runtime_state("minimax")
        assert state["active"] == 0


# ---------------------------------------------------------------------------
# 3. fallback：TimeoutError 类型先行 → 可重试 TIMEOUT
# ---------------------------------------------------------------------------


class _EmptyStrError(Exception):
    def __str__(self) -> str:  # pragma: no cover - trivially empty
        return ""


def _make_manager_with_candidate(monkeypatch) -> LLMModelFallbackManager:
    """fallback manager：健康面全绿（不依赖 redis/router）。"""
    manager = LLMModelFallbackManager(max_fallback_attempts=3)

    async def _healthy(model_key: str) -> bool:
        return True

    monkeypatch.setattr(manager.health_tracker, "is_healthy", _healthy)
    return manager


class TestFallbackTimeoutClassification:
    def test_bare_timeout_error_classified_retryable(self):
        """空 str 的 TimeoutError() 必须归类 TIMEOUT（原误判 Non-retryable 的病灶）。"""
        manager = LLMModelFallbackManager()
        assert manager._detect_fallback_reason(TimeoutError()) == "timeout"

    def test_descriptive_timeout_error_classified_retryable(self):
        manager = LLMModelFallbackManager()
        reason = manager._detect_fallback_reason(TimeoutError("LLM API minimax is busy: no free concurrency slot"))
        assert reason == "timeout"

    async def test_semaphore_timeout_now_falls_back(self, monkeypatch):
        """端到端：首选抛信号量 TimeoutError → 切候选成功（不再直接抛出）。"""
        manager = _make_manager_with_candidate(monkeypatch)
        selection = LLMSelection(
            model_key="minimax_m3_batch",
            config=SimpleNamespaceConfig(),
            agent_role=None,
            task_type=None,
            reason="test",
        )
        fallback_selection = LLMSelection(
            model_key="glm_4_7_no_thinking",
            config=SimpleNamespaceConfig(),
            agent_role=None,
            task_type=None,
            reason="test-fallback",
        )
        candidates = [fallback_selection]
        manager._get_fallback_candidates = lambda *a, **kw: candidates  # type: ignore[method-assign]

        calls: list[str] = []

        async def call_fn(sel):
            calls.append(sel.model_key)
            if sel.model_key == "minimax_m3_batch":
                raise TimeoutError()  # 空 str：原路径直接 Non-retryable 抛出
            return "ok"

        result = await manager.execute_with_fallback(selection, call_fn)
        assert result == "ok"
        assert calls == ["minimax_m3_batch", "glm_4_7_no_thinking"]

    async def test_non_retryable_empty_error_logs_type_name(self, monkeypatch):
        """str(e) 为空的 Non-retryable 异常：日志兜底出类型名（不产出空消息）。"""
        manager = _make_manager_with_candidate(monkeypatch)
        selection = LLMSelection(
            model_key="minimax_m3_batch",
            config=SimpleNamespaceConfig(),
            agent_role=None,
            task_type=None,
            reason="test",
        )

        lines: list[str] = []
        sink_id = loguru_logger.add(lines.append, level="ERROR", format="{message}")
        try:
            with pytest.raises(_EmptyStrError):
                await manager.execute_with_fallback(selection, _raise_empty_error)
        finally:
            loguru_logger.remove(sink_id)

        target = [line for line in lines if "Non-retryable error" in line]
        assert target, f"expected non-retryable error log, got: {lines!r}"
        # 原病灶形态是行尾悬空冒号（"Non-retryable error: "）——必须消失
        assert all("_EmptyStrError" in line and not line.rstrip().endswith(":") for line in target)


class SimpleNamespaceConfig:
    """最小 ModelConfig 替身（execute_with_fallback 只读 provider/model_name）。"""

    provider = None
    model_name = "test-model"
    tier = None
    base_url = ""
    clear_thinking = False


async def _raise_empty_error(_selection):
    raise _EmptyStrError()


# ---------------------------------------------------------------------------
# 4. 队列饱和可观测（首条 ERROR / 周期汇总 / 恢复 INFO）
# ---------------------------------------------------------------------------


@pytest.fixture()
def _clean_saturation_state():
    qbp._SATURATION_STATE.clear()
    yield
    qbp._SATURATION_STATE.clear()


class TestQueueSaturationObservability:
    def _capture(self, cap=200):
        def _llen(queue: str) -> int:
            return cap

        return _llen

    @staticmethod
    def _sink(records: list[str]):
        """loguru sink：level 前缀 + message（Message 是 str 子类，format 内插值）。"""
        return loguru_logger.add(
            lambda msg: records.append(str(msg)),
            level="INFO",
            format="{level.name}|{message}",
        )

    async def test_saturation_start_error_then_recovery_info(self, monkeypatch, _clean_saturation_state):
        records: list[str] = []
        sink_id = self._sink(records)
        try:
            monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(200))
            allowed = await qbp.enforce_queue_backpressure("glm_batch")
            assert allowed is False
            assert any("SATURATION START" in r for r in records)

            monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(199))
            allowed = await qbp.enforce_queue_backpressure("glm_batch")
            assert allowed is True
            assert any("SATURATION RECOVERED" in r for r in records)
            assert qbp._SATURATION_STATE == {}
        finally:
            loguru_logger.remove(sink_id)

    async def test_periodic_summary_within_episode(self, monkeypatch, _clean_saturation_state):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_SATURATION_LOG_INTERVAL_SECONDS", 0.05)
        records: list[str] = []
        sink_id = self._sink(records)
        try:
            monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(200))
            await qbp.enforce_queue_backpressure("glm_batch")  # START
            await qbp.enforce_queue_backpressure("glm_batch")  # drop (suppressed)
            await asyncio.sleep(0.06)
            await qbp.enforce_queue_backpressure("glm_batch")  # ONGOING summary
        finally:
            loguru_logger.remove(sink_id)

        starts = [r for r in records if "SATURATION START" in r]
        ongoing = [r for r in records if "SATURATION ONGOING" in r]
        assert len(starts) == 1
        assert len(ongoing) == 1
        assert "drops_in_episode=3" in ongoing[0]

    async def test_every_drop_counts_and_returns_false(self, monkeypatch, _clean_saturation_state):
        monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(200))
        for _ in range(3):
            assert await qbp.enforce_queue_backpressure("glm_batch") is False
        episode = qbp._SATURATION_STATE["glm_batch"]
        assert episode["drops"] == 3

    def test_sync_enforce_shares_episode_semantics(self, monkeypatch, _clean_saturation_state):
        records: list[str] = []
        sink_id = self._sink(records)
        try:
            monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(200))
            assert qbp.enforce_queue_backpressure_sync("glm_batch") is False
            assert any("SATURATION START" in r for r in records)

            monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(10))
            assert qbp.enforce_queue_backpressure_sync("glm_batch") is True
            assert any("SATURATION RECOVERED" in r for r in records)
        finally:
            loguru_logger.remove(sink_id)

    async def test_probe_failure_does_not_end_episode(self, monkeypatch, _clean_saturation_state):
        """探测失败（broker 不可达）≠ 恢复：episode 必须保留。"""
        monkeypatch.setattr(qbp, "_llen_via_celery", self._capture(200))
        assert await qbp.enforce_queue_backpressure("glm_batch") is False
        assert "glm_batch" in qbp._SATURATION_STATE

        def _boom(queue: str) -> int:
            raise ConnectionError("broker down")

        monkeypatch.setattr(qbp, "_llen_via_celery", _boom)
        assert await qbp.enforce_queue_backpressure("glm_batch") is True  # 有界降级放行
        assert "glm_batch" in qbp._SATURATION_STATE  # 但不误报恢复
