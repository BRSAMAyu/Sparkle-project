"""G-05（wt395）恢复风暴回归：``@cached`` 必须合并同 key 的 in-flight 请求（singleflight）。

缺陷背景：``cached`` 装饰器 get→miss→compute→set 之间无合并——断线重连风暴下
N 台设备同时冷缓存取图，各自完整重算（G-05 本地实证：16 并发冷缓存取 5000 节点
图 p50=10.3s ≈ 单发 ×16 的纯 CPU 排队）。修复后首个请求计算、其余共享同一
Future，风暴尾部回到"一次计算 + 等待"量级（G-05 复跑实证见
v3-output/WT395-G05-GALAXY/summary_scale_perf.md）。

契约：
1. 并发 miss → 被装饰函数只执行一次，全部调用方拿到同一结果;
2. 异常不缓存：首个调用失败传播给同批等待者，in-flight 标记清除，下次调用重算;
3. 不同 key 互不合并。
sqlite 口径（cache_service 无 redis 时走进程内本地缓存, 不依赖外部服务）。
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.cache import cached


@pytest.mark.asyncio
async def test_concurrent_miss_computes_once_and_shares_result():
    calls = {"n": 0}

    @cached(ttl=60, namespace="g05_test")
    async def slow_compute(user_id: str) -> dict:
        calls["n"] += 1
        await asyncio.sleep(0.05)  # 模拟重算窗口
        return {"nodes": 5000, "computed_by": calls["n"]}

    results = await asyncio.gather(*[slow_compute("u-1") for _ in range(16)])

    assert calls["n"] == 1, f"16 并发同 key 冷启动必须只算一次, 实际执行 {calls['n']} 次"
    assert all(r["nodes"] == 5000 for r in results)
    assert len({id(r) for r in results}) == 1, "同批等待者必须共享同一结果对象"


@pytest.mark.asyncio
async def test_exception_propagates_to_waiters_and_does_not_stick():
    calls = {"n": 0}

    @cached(ttl=60, namespace="g05_test")
    async def failing_compute(user_id: str) -> dict:
        calls["n"] += 1
        await asyncio.sleep(0.02)
        raise RuntimeError("boom")

    results = await asyncio.gather(*[failing_compute("u-2") for _ in range(8)], return_exceptions=True)
    assert all(isinstance(r, RuntimeError) for r in results), "同批等待者必须收到同一异常"
    assert calls["n"] == 1

    # 异常不缓存: 下一次调用重算（依旧失败, 但证明没有吞异常/粘住失败态）
    with pytest.raises(RuntimeError):
        await failing_compute("u-2")
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_different_keys_do_not_coalesce():
    calls = {"n": 0}

    @cached(ttl=60, namespace="g05_test")
    async def keyed_compute(user_id: str) -> dict:
        calls["n"] += 1
        await asyncio.sleep(0.03)
        return {"user": user_id}

    results = await asyncio.gather(
        *[keyed_compute(f"u-{i}") for i in range(8)],
        keyed_compute("u-0"),  # 与第 0 个同 key → 合并
    )
    assert calls["n"] == 8, "8 个不同 key 各算一次; 同 key 的重复调用合并"
    assert results[-1]["user"] == "u-0"
