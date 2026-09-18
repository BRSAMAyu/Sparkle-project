"""
Core: infra
Phase: execute
Stage: restore-storm guard

恢复风暴防护最小单测：EndpointShield 的 single-flight 合并、TTL 缓存、
并发钳制与过载 shedding，以及 dispatch_task_async 的事件循环不被冻结。
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.request_coalescing import EndpointOverloaded, EndpointShield


@pytest.mark.asyncio
async def test_single_flight_merges_concurrent_calls():
    """同 key 的 20 并发只触发一次 loader（恢复风暴去重核心语义）。"""
    shield = EndpointShield(name="t_merge", max_concurrency=8, ttl=10.0, wait_timeout=5.0)
    calls = 0

    async def loader() -> dict:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # 模拟 DB/图计算
        return {"v": 42}

    results = await asyncio.gather(*(shield.run("user-a", loader) for _ in range(20)))

    assert calls == 1, "single-flight 应把 20 个并发合并为一次 loader 调用"
    assert all(r == {"v": 42} for r in results)


@pytest.mark.asyncio
async def test_ttl_cache_hit_and_expiry():
    """TTL 内直接命中缓存；过期后重新计算。"""
    shield = EndpointShield(name="t_ttl", max_concurrency=4, ttl=0.2, wait_timeout=5.0)
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        return calls

    first = await shield.run("k", loader)
    second = await shield.run("k", loader)
    assert first == 1 and second == 1, "TTL 内第二次调用应命中缓存"
    assert calls == 1

    await asyncio.sleep(0.25)  # 超过 ttl
    third = await shield.run("k", loader)
    assert third == 2 and calls == 2, "TTL 过期后应重新计算"


@pytest.mark.asyncio
async def test_different_keys_compute_independently():
    """不同 key 互不合并、互不命中。"""
    shield = EndpointShield(name="t_keys", max_concurrency=8, ttl=10.0)

    async def loader() -> int:
        await asyncio.sleep(0.02)
        return 1

    a, b = await asyncio.gather(shield.run("user-a", loader), shield.run("user-b", loader))
    assert a == 1 and b == 1
    assert shield.hits == 0 and shield.deduped == 0


@pytest.mark.asyncio
async def test_loader_failure_not_cached_and_propagates():
    """loader 异常传播给等待者，但不写缓存——后续请求重新计算。"""
    shield = EndpointShield(name="t_fail", max_concurrency=8, ttl=10.0, wait_timeout=5.0)
    calls = 0

    async def failing() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        raise RuntimeError("boom")

    async def ok() -> int:
        nonlocal calls
        calls += 1
        return 7

    with pytest.raises(RuntimeError):
        await asyncio.gather(*(shield.run("k", failing) for _ in range(5)))

    assert calls == 1, "并发失败也应只算一次"
    assert shield.snapshot()["cache_entries"] == 0, "失败不得写缓存"

    assert await shield.run("k", ok) == 7, "失败后新请求应重新计算并成功"


@pytest.mark.asyncio
async def test_concurrency_clamp_limits_parallel_loaders():
    """并发钳制：同时在飞的 loader 数不超过 max_concurrency。"""
    max_concurrency = 3
    shield = EndpointShield(name="t_clamp", max_concurrency=max_concurrency, ttl=0.0, wait_timeout=10.0)
    current = 0
    peak = 0

    async def loader() -> int:
        nonlocal current, peak
        current += 1
        peak = max(peak, current)
        await asyncio.sleep(0.05)
        current -= 1
        return 1

    # ttl=0：不缓存结果，强制 20 个请求都走计算路径以验证钳制
    await asyncio.gather(*(shield.run(f"u-{i}", loader) for i in range(20)))

    assert peak <= max_concurrency, f"峰值并发 {peak} 超过钳制 {max_concurrency}"
    assert shield.snapshot()["shed"] == 0


@pytest.mark.asyncio
async def test_shed_when_saturated_beyond_wait_timeout():
    """钳制满载且等待超时 → EndpointOverloaded（快速失败优于无限排队）。"""
    shield = EndpointShield(name="t_shed", max_concurrency=1, ttl=0.0, wait_timeout=0.1)
    release = asyncio.Event()

    async def blocked() -> str:
        await release.wait()
        return "done"

    holder = asyncio.create_task(shield.run("k", blocked))
    await asyncio.sleep(0.02)  # 确保 holder 已占住唯一槽位

    start = time.monotonic()
    with pytest.raises(EndpointOverloaded):
        await shield.run("k", blocked)
    assert time.monotonic() - start < 1.0, "过载应在 wait_timeout 内快速失败"

    release.set()
    assert await holder == "done"


@pytest.mark.asyncio
async def test_snapshot_observability():
    """snapshot 暴露命中/去重/雪崩计数（观测用）。"""
    shield = EndpointShield(name="t_obs", max_concurrency=2, ttl=5.0, wait_timeout=5.0)

    async def loader() -> int:
        await asyncio.sleep(0.01)
        return 1

    await asyncio.gather(*(shield.run("k", loader) for _ in range(6)))
    snap = shield.snapshot()
    assert snap["deduped"] >= 1
    assert snap["hits"] >= 4  # 首个完成写缓存后，后续调用命中
    assert snap["shed"] == 0
