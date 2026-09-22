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


# ---------------------------------------------------------------------------
# SHIELD-INVAL · 前缀失效面（写后即时投影的进程内第二层）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_prefix_clears_only_matching_user():
    """按 user 前缀失效：该 user 全部参数变体清空、他 user 缓存原样保留。"""
    shield = EndpointShield(name="t_inval", max_concurrency=4, ttl=10.0, wait_timeout=5.0)
    calls: list[str] = []

    async def loader() -> str:
        calls.append("compute")
        return f"v{len(calls)}"

    # user-a 两个参数变体 + user-b 一个变体，全部落缓存
    await shield.run("user-a::True:1.0", loader)
    await shield.run("user-a::False:1.0", loader)
    await shield.run("user-b::True:1.0", loader)
    assert shield.snapshot()["cache_entries"] == 3

    cleared = shield.invalidate_prefix("user-a:")
    assert cleared == 2, "user-a 的两个变体都应被清除"
    assert shield.snapshot()["cache_entries"] == 1, "user-b 的缓存不得被误伤"

    before = len(calls)
    assert await shield.run("user-b::True:1.0", loader) == "v3"
    assert len(calls) == before, "user-b 仍应命中缓存（零重算）"
    assert await shield.run("user-a::True:1.0", loader) == "v4"
    assert len(calls) == before + 1, "user-a 失效后必须重算"


@pytest.mark.asyncio
async def test_invalidation_during_inflight_not_backfilled():
    """失效发生在飞计算中：其完成后的旧值不得回填缓存（失效不可被撤销）。"""
    shield = EndpointShield(name="t_race", max_concurrency=4, ttl=10.0, wait_timeout=5.0)
    calls = 0
    release = asyncio.Event()

    async def stale_loader() -> dict:
        nonlocal calls
        calls += 1
        await release.wait()  # 模拟慢图计算：失效将发生在其计算窗口内
        return {"mastery": None}  # 写前旧值

    async def fresh_loader() -> dict:
        nonlocal calls
        calls += 1
        return {"mastery": 42}

    inflight = asyncio.create_task(shield.run("user-a:sect", stale_loader))
    await asyncio.sleep(0.02)  # 确保 stale_loader 已在飞
    assert shield.invalidate_prefix("user-a:") == 0  # 尚无已完成条目可清

    release.set()
    stale = await inflight  # 等待者仍拿到旧值（single-flight 语义不变）
    assert stale == {"mastery": None}

    # 旧计算启动早于失效 → 不落缓存；下一请求必须重算出写后新值
    fresh = await shield.run("user-a:sect", fresh_loader)
    assert fresh == {"mastery": 42}
    assert calls == 2, "失效窗口内的在飞旧值不得被缓存复用"
    assert await shield.run("user-a:sect", fresh_loader) == {"mastery": 42}
    assert calls == 2, "失效后新计算的值正常落缓存命中"


@pytest.mark.asyncio
async def test_single_flight_and_clamp_survive_invalidation():
    """风暴防护语义不因失效面受损：失效后并发仍合并为一次计算。"""
    shield = EndpointShield(name="t_storm", max_concurrency=8, ttl=10.0, wait_timeout=5.0)
    calls = 0

    async def loader() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return calls

    await shield.run("user-a", loader)
    shield.invalidate_prefix("user-a")
    calls = 0

    results = await asyncio.gather(*(shield.run("user-a", loader) for _ in range(20)))
    assert calls == 1, "失效后的并发拉取仍应 single-flight 合并"
    assert all(r == 1 for r in results)
    assert shield.snapshot()["shed"] == 0


def test_read_view_invalidation_registry():
    """注册表契约：notify 按域分发、异常兜底、未注册域 no-op、重复注册去重。"""
    from app.core import request_coalescing as rc

    domain = "t_registry_domain"
    rc._READ_VIEW_INVALIDATION_HOOKS.pop(domain, None)  # 隔离：清理可能的残留
    seen: list[str] = []

    def hook(user_id: str) -> int:
        seen.append(user_id)
        return 2

    rc.register_read_view_invalidation_hook(domain, hook)
    rc.register_read_view_invalidation_hook(domain, hook)  # 幂等
    assert rc.notify_read_view_invalidated(domain, "u-1") == 2
    assert seen == ["u-1"], "同一回调重复注册只触发一次"

    def broken(user_id: str) -> int:
        raise RuntimeError("hook bug")

    rc.register_read_view_invalidation_hook(domain, broken)
    assert rc.notify_read_view_invalidated(domain, "u-2") == 2, "回调异常不得传播、不得吞掉其他回调的清理数"
    assert seen == ["u-1", "u-2"]

    assert rc.notify_read_view_invalidated("t_never_registered", "u-1") == 0, "未注册域为 no-op"
    assert rc._READ_VIEW_INVALIDATION_HOOKS.pop(domain, None) is not None
