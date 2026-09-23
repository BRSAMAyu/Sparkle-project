"""DIST-SEMAPHORE · 跨进程 MiniMax 账户级 RPM 预算闸（Redis 固定窗口）.

覆盖卡面四类验收（多"进程"=共享 FakeServer 的多个 gate/redis 实例，不真起多进程压测）：
- 全局预算恰 N/分钟窗口：N 个预算、超量并发 claimant → 恰 N 个取得，其余
  TimeoutError（窗口计数回落到 N，DECR 回滚不吞预算）；
- TTL 防死锁：窗口 key 恒带 TTL（无信号量持有者可悬空占坑；EXPIRE 丢失可自愈
  重武装）；窗口滚动后旧窗口耗尽不传染新窗口；
- 诚实降级：Redis 缺席/出错 → 放行回本地池 + 限频告警，不阻断；
- 非 minimax provider 零变化：预算启用下 zhipu 路径不触 Redis、行为与此前一致。
"""

from __future__ import annotations

import asyncio

import fakeredis
import pytest
from loguru import logger as loguru_logger

from app.config import settings
from app.core.cache import cache_service
from app.services.llm import concurrency as llm_concurrency_module
from app.services.llm import minimax_rpm_gate as gate_module
from app.services.llm.concurrency import ConcurrencyConfig, LLMConcurrencyManager, ProviderType
from app.services.llm.minimax_rpm_gate import MinimaxRpmGate, get_minimax_rpm_gate


class _FakeClock:
    """可控时钟（只替换 gate 模块可见的 time.time，模拟窗口滚动）。"""

    def __init__(self, start: float = 1_000_000.0):
        self.now = start

    def time(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """每个用例独立：清 gate 单例、隔离 cache_service.redis、可控时钟。"""
    monkeypatch.setattr(gate_module, "_singleton", None)
    monkeypatch.setattr(cache_service, "redis", None)
    clock = _FakeClock()
    monkeypatch.setattr(gate_module, "time", clock)
    yield clock
    monkeypatch.setattr(gate_module, "_singleton", None)


def _shared_redis_pair():
    """模拟两个"进程"：独立连接、共享同一 FakeServer 存储。"""
    server = fakeredis.FakeServer()
    r1 = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    r2 = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    return server, r1, r2


def _window_keys_pattern(prefix: str) -> str:
    return f"{prefix}:*"


# ---------------------------------------------------------------------------
# 1. 全局预算恰 N/分钟窗口（跨"进程"多实例）
# ---------------------------------------------------------------------------


class TestGlobalBudgetExactlyN:
    async def test_multiple_gate_instances_share_budget_exactly_n_per_window(self):
        """双"进程"（两个 gate 实例 × 独立 redis 连接）并发取令牌：恰 N 个成功。"""
        server, r1, r2 = _shared_redis_pair()
        gate_a = MinimaxRpmGate(3, key_prefix="test:rpm", redis_getter=lambda: r1)
        gate_b = MinimaxRpmGate(3, key_prefix="test:rpm", redis_getter=lambda: r2)

        claimants = [gate_a] * 6 + [gate_b] * 6

        async def _claim(gate: MinimaxRpmGate):
            try:
                await gate.acquire(timeout=0.3)
                return "ok"
            except TimeoutError:
                return "timeout"

        results = await asyncio.gather(*[_claim(g) for g in claimants])
        assert results.count("ok") == 3, f"预算恰 3，实得 {results.count('ok')}"
        assert results.count("timeout") == 9
        # 窗口计数回落到 N（超发方 DECR 回滚，不吞预算）
        keys = [k async for k in r1.scan_iter(_window_keys_pattern("test:rpm"))]
        assert len(keys) == 1
        assert int(await r1.get(keys[0])) == 3
        # 双实例合计观测一致
        assert gate_a.total_acquired + gate_b.total_acquired == 3

    async def test_budget_refreshes_after_window_rolls(self, _isolated_env):
        """窗口滚动即 refill：旧窗口耗尽不传染新窗口（每分钟 N 发起口径）。"""
        clock = _isolated_env
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        gate = MinimaxRpmGate(2, key_prefix="test:roll")

        await gate.acquire(timeout=0.1)
        await gate.acquire(timeout=0.1)
        with pytest.raises(TimeoutError):
            await gate.acquire(timeout=0.05)

        clock.now += 61.0  # 滚动到下一分钟窗口
        await gate.acquire(timeout=0.1)
        await gate.acquire(timeout=0.1)
        with pytest.raises(TimeoutError):
            await gate.acquire(timeout=0.05)
        assert gate.total_acquired == 4

    async def test_timeout_message_nonempty_with_budget_snapshot(self):
        """等预算超时 → 非空 TimeoutError（含 budget/窗口用量，对齐 BATCH-CAP 空消息修复）。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        gate = MinimaxRpmGate(1, key_prefix="test:msg")
        await gate.acquire(timeout=0.1)
        with pytest.raises(TimeoutError) as exc_info:
            await gate.acquire(timeout=0.05)
        msg = str(exc_info.value)
        assert msg.strip(), "消息不得为空（空消息是 BATCH-CAP 实测故障面）"
        assert "RPM budget" in msg
        assert "budget=1/min" in msg
        assert "window_used>=1" in msg
        assert gate.total_rejected_timeout == 1


# ---------------------------------------------------------------------------
# 2. TTL 防死锁（无持有者悬空占坑 + EXPIRE 自愈）
# ---------------------------------------------------------------------------


class TestTtlCrashSafety:
    async def test_window_key_always_carries_ttl(self):
        """窗口 key 恒带 TTL（≤2×窗口长度）：孤儿状态必然到期自动回收。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        gate = MinimaxRpmGate(5, key_prefix="test:ttl")
        await gate.acquire(timeout=0.1)
        keys = [k async for k in fake.scan_iter(_window_keys_pattern("test:ttl"))]
        assert len(keys) == 1
        ttl = await fake.ttl(keys[0])
        assert 0 < ttl <= 120

    async def test_lost_expire_self_heals_on_next_acquire(self):
        """EXPIRE 丢失自愈：模拟 INCR/EXPIRE 分离的崩溃残留 → 下次 acquire 重新武装 TTL。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        gate = MinimaxRpmGate(5, key_prefix="test:heal")
        await gate.acquire(timeout=0.1)
        keys = [k async for k in fake.scan_iter(_window_keys_pattern("test:heal"))]
        await fake.persist(keys[0])  # 人为制造"无 TTL 孤儿 key"（最坏崩溃残留形态）
        assert await fake.ttl(keys[0]) == -1
        await gate.acquire(timeout=0.1)  # 同窗口再次取得 → pipeline EXPIRE 重武装
        assert await fake.ttl(keys[0]) > 0

    async def test_crashed_claimant_cannot_squat_next_window(self, _isolated_env):
        """崩溃"进程"已消费的发起配额不阻塞后续窗口（消费即花费、无释放悬空面）。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        gate = MinimaxRpmGate(1, key_prefix="test:crash")
        await gate.acquire(timeout=0.1)  # 模拟该进程此刻崩溃：无任何释放动作
        _isolated_env.now += 61.0
        await gate.acquire(timeout=0.1)  # 新窗口不受旧窗口"持有者"影响
        assert gate.total_acquired == 2

    async def test_budget_zero_or_negative_rejected_by_gate_constructor(self):
        """预算必须 >0（0 = 禁用语义归 get_minimax_rpm_gate，不放陷阱实例）。"""
        with pytest.raises(ValueError):
            MinimaxRpmGate(0)
        with pytest.raises(ValueError):
            MinimaxRpmGate(-5)


# ---------------------------------------------------------------------------
# 3. 诚实降级（Redis 缺席/出错不阻断）
# ---------------------------------------------------------------------------


class TestHonestDegradation:
    async def test_redis_absent_falls_back_to_local_pool(self):
        """cache_service.redis is None → 放行（本地池把关）+ 降级计数。"""
        gate = MinimaxRpmGate(1, key_prefix="test:degrade")
        await gate.acquire(timeout=0.1)  # 不抛即放行
        await gate.acquire(timeout=0.1)
        assert gate.total_degraded == 2
        assert gate.total_acquired == 0

    async def test_redis_error_falls_back_and_warns_with_cooldown(self):
        """Redis 命令出错 → 降级放行 + 限频告警（冷却窗口内只一条）。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake

        class _ExplodingClient:
            def __getattr__(self, name):
                raise ConnectionError("redis down")

        cache_service.redis = _ExplodingClient()
        gate = MinimaxRpmGate(1, key_prefix="test:err")
        lines: list[str] = []
        sink_id = loguru_logger.add(lines.append, level="WARNING", format="{message}")
        try:
            await gate.acquire(timeout=0.1)
            await gate.acquire(timeout=0.1)
        finally:
            loguru_logger.remove(sink_id)
        assert gate.total_degraded == 2
        assert len(lines) == 1, f"冷却窗口内应限频为 1 条告警，实得 {len(lines)}"
        assert "NOT enforced" in lines[0]

    async def test_recovery_after_redis_returns(self):
        """Redis 恢复后自动回到分布式预算（降级不粘滞）。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        gate = MinimaxRpmGate(1, key_prefix="test:recover")

        class _Down:
            def __getattr__(self, name):
                raise ConnectionError("down")

        cache_service.redis = _Down()
        await gate.acquire(timeout=0.1)
        assert gate.total_degraded == 1

        cache_service.redis = fake
        await gate.acquire(timeout=0.1)
        with pytest.raises(TimeoutError):
            await gate.acquire(timeout=0.05)
        assert gate.total_acquired == 1  # 预算恢复执行：第 2 次被拒（等 0.05s 超时）
        assert gate.total_rejected_timeout == 1


# ---------------------------------------------------------------------------
# 4. 非 minimax provider 零变化 + 挂钩语义
# ---------------------------------------------------------------------------


def _fresh_manager(minimax_limit: int = 8) -> LLMConcurrencyManager:
    original = llm_concurrency_module.PROVIDER_CONFIGS
    llm_concurrency_module.PROVIDER_CONFIGS = {
        ProviderType.ZHIPU: ConcurrencyConfig(max_concurrent=2, queue_timeout=30.0),
        ProviderType.MINIMAX: ConcurrencyConfig(
            max_concurrent=minimax_limit,
            min_concurrent=1,
            queue_timeout=5.0,
        ),
    }
    try:
        return LLMConcurrencyManager()
    finally:
        llm_concurrency_module.PROVIDER_CONFIGS = original


class TestHookSemantics:
    async def test_non_minimax_provider_never_touches_redis(self):
        """预算启用下 zhipu 路径零 Redis 接触、行为与此前一致（其他 provider 零变化）。"""
        server, _, _ = _shared_redis_pair()
        fake = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
        cache_service.redis = fake
        manager = _fresh_manager()
        async with manager.acquire("zhipu", timeout=1.0):
            keys = [k async for k in fake.scan_iter("*")]
            assert keys == [], "非 MINIMAX provider 不得触达 RPM 桶"

    async def test_minimax_acquire_goes_through_gate_then_local_pool(self, monkeypatch):
        """MINIMAX acquire：先过 RPM 桶（Redis 留痕）再过本地池（第二道防线）。"""
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 10)
        server, _, _ = _shared_redis_pair()
        fake = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
        cache_service.redis = fake
        manager = _fresh_manager(minimax_limit=8)
        async with manager.acquire("minimax", timeout=1.0):
            keys = [k async for k in fake.scan_iter(_window_keys_pattern(gate_module._KEY_PREFIX))]
            assert len(keys) == 1, "MINIMAX acquire 应在 Redis 留 RPM 桶痕"

    async def test_gate_disabled_by_default_zero_behavior_change(self):
        """默认 MINIMAX_RPM_BUDGET=0：gate 为 None，Redis 不留痕（回滚位兼容）。"""
        assert settings.MINIMAX_RPM_BUDGET == 0
        assert get_minimax_rpm_gate() is None
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        manager = _fresh_manager()
        async with manager.acquire("minimax", timeout=1.0):
            keys = [k async for k in fake.scan_iter("*")]
            assert keys == [], "禁用位下不得有任何 Redis 痕"

    async def test_remaining_budget_handed_to_local_pool(self, monkeypatch):
        """gate 通过后把剩余等待预算交给本地池：总等待 ≤ queue_timeout（不放宽 fast-fail）。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 10)
        manager = _fresh_manager()
        captured: list[float] = []
        original = manager._acquire_slot

        async def _spy(provider_type, timeout):
            captured.append(timeout)
            await original(provider_type, timeout)

        monkeypatch.setattr(manager, "_acquire_slot", _spy)
        async with manager.acquire("minimax", timeout=5.0):
            pass
        assert captured, "本地池必须仍被调用（第二道防线保留）"
        assert 0 < captured[0] <= 5.0

    async def test_gate_budget_exhausted_times_out_with_rpm_message(self, monkeypatch):
        """端到端：预算 1、本地池 8 槽 → 第 2 个 acquire 在 gate 处超时，消息指 RPM 而非槽。"""
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache_service.redis = fake
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 1)
        manager = _fresh_manager(minimax_limit=8)
        async with manager.acquire("minimax", timeout=1.0):
            with pytest.raises(TimeoutError) as exc_info:
                await manager.acquire("minimax", timeout=0.1).__aenter__()
            assert "RPM budget" in str(exc_info.value)

    async def test_singleton_respects_budget_changes(self, monkeypatch):
        """get_minimax_rpm_gate：0 → None；>0 → 实例；改值 → 重建（env+重启即生效/回滚）。"""
        assert get_minimax_rpm_gate() is None
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 20)
        gate = get_minimax_rpm_gate()
        assert gate is not None and gate.budget == 20
        assert get_minimax_rpm_gate() is gate  # 同预算复用单例
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 200)
        gate2 = get_minimax_rpm_gate()
        assert gate2 is not gate and gate2.budget == 200
        monkeypatch.setattr(settings, "MINIMAX_RPM_BUDGET", 0)
        assert get_minimax_rpm_gate() is None


# ---------------------------------------------------------------------------
# 5. settings 面
# ---------------------------------------------------------------------------


class TestSettings:
    def test_default_budget_is_zero_rollback_position(self):
        from app.config import Settings

        fresh = Settings(MINIMAX_RPM_BUDGET=0)
        assert fresh.MINIMAX_RPM_BUDGET == 0

    def test_negative_budget_clamped_to_zero(self):
        from app.config import Settings

        fresh = Settings(MINIMAX_RPM_BUDGET=-3)
        assert fresh.MINIMAX_RPM_BUDGET == 0

    def test_positive_budget_round_trips(self):
        from app.config import Settings

        fresh = Settings(MINIMAX_RPM_BUDGET=20)
        assert fresh.MINIMAX_RPM_BUDGET == 20
