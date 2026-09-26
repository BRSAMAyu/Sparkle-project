"""V3-FIX-255（T-semantic-cache-lock-fallback-threshold）: LockError 降级路径阈值同源。

get_with_lock 的主路径（首次查询 + 锁内双重检查）把调用方传入的
``similarity_threshold`` 收敛为 ``effective_threshold``（None → 1.0）后显式传给
``get()``；但 LockError 降级路径调 ``get()`` 时**未传**该参数，落到 get() 签名
默认 0.95——生产调用方（galaxy/retrieval_service.py:243 传
``settings.SEMANTIC_CACHE_SIM_THRESHOLD=0.9``）下降级面比主路径**更严**。
现配置下方向保守安全（降级只会多走工厂，绝不取脏数据），但同一方法内两个
get() 口径必须同源一致，不许 get() 默认值成为第二权威。

本套件以桩测钉死契约：一次 get_with_lock 调用内所有 get() 收到的 threshold
必须同值且等于主路径同源 effective_threshold（调用方传入值 / 未传时 1.0），
而非 get() 签名默认 0.95。
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import LockError

from app.services.semantic_cache_service import SemanticCacheService


class _UnconfiguredEmbedding:
    """打桩 embedding 服务：避免语义检索面触发真实 API（对齐邻域测试口径）。"""

    @staticmethod
    def is_configured() -> bool:
        return False


_GET_SIG = inspect.signature(SemanticCacheService.get)


def _threshold_received(args: tuple, kwargs: dict) -> float:
    """还原一次 get() 调用实际生效的 similarity_threshold（含签名默认）。"""
    if len(args) >= 3:
        return float(args[2])
    if "similarity_threshold" in kwargs:
        return float(kwargs["similarity_threshold"])
    return float(_GET_SIG.parameters["similarity_threshold"].default)


@pytest.fixture
def mock_redis():
    mock = MagicMock()

    mock.get = AsyncMock(return_value=None)  # 全程 miss（降级路径同样未命中）
    mock.setex = AsyncMock()
    mock.hincrby = AsyncMock()
    mock.exists = AsyncMock(return_value=True)
    mock.hset = AsyncMock()
    mock.delete = AsyncMock()
    mock.sadd = AsyncMock()
    mock.smembers = AsyncMock(return_value=set())
    mock.scard = AsyncMock(return_value=0)

    # 锁在 acquire（__aenter__）时抛 LockError——驱动 get_with_lock 的降级路径
    mock_lock = MagicMock()
    mock_lock.__aenter__ = AsyncMock(side_effect=LockError("Unable to acquire lock"))
    mock_lock.__aexit__ = AsyncMock(return_value=None)
    mock.lock.return_value = mock_lock
    return mock


@pytest.fixture
def no_embedding(monkeypatch):
    import app.services.semantic_cache_service as sc_mod

    monkeypatch.setattr(sc_mod, "embedding_service", _UnconfiguredEmbedding)


def _spy_get(service: SemanticCacheService, captured: list):
    original_get = service.get

    async def spy(*args, **kwargs):
        captured.append((args, kwargs))
        return await original_get(*args, **kwargs)

    return spy


@pytest.mark.asyncio
async def test_lockerror_fallback_get_receives_caller_threshold(mock_redis, no_embedding, monkeypatch):
    """降级路径 get() 收到的 threshold 必须与主路径同源（调用方传入 0.9）。

    修前：主路径 get() 收到 0.9，降级路径 get() 未传参收到签名默认 0.95——
    降级面比主路径更严（红）。修后：两路同收 0.9（绿）。
    """
    service = SemanticCacheService(redis_client=mock_redis)
    captured: list = []
    monkeypatch.setattr(service, "get", _spy_get(service, captured))

    factory_payload = {"origin": "factory"}
    factory = AsyncMock(return_value=factory_payload)

    result = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=0.9)

    # 降级路径终态：未命中走工厂，工厂原返回值透传
    assert result is factory_payload, "LockError 降级路径必须透传工厂结果（行为面不因本修改变）"
    assert factory.await_count == 1

    # 一次 get_with_lock 内恰两次 get()：主路径一次 + LockError 降级一次
    assert len(captured) == 2, f"期望主路径+降级各一次 get()，实际 {len(captured)} 次"

    main_threshold = _threshold_received(*captured[0])
    fallback_threshold = _threshold_received(*captured[1])

    assert main_threshold == pytest.approx(0.9), "主路径 get() 必须收到调用方传入的 0.9（回归守卫）"
    assert fallback_threshold == pytest.approx(main_threshold), (
        f"降级路径 get() 必须与主路径同源同值（{main_threshold}），"
        f"实际 {fallback_threshold}——get() 签名默认 0.95 不许成为第二权威"
    )
    assert fallback_threshold == pytest.approx(0.9), (
        f"降级路径 get() 收到 threshold={fallback_threshold}（期望 0.9，"
        "修前落到 get() 默认 0.95 使降级面比主路径更严）"
    )


@pytest.mark.asyncio
async def test_lockerror_fallback_get_follows_param_source_when_unset(mock_redis, no_embedding, monkeypatch):
    """调用方未传 threshold 时，降级路径随主路径同源收敛 1.0，而非 0.95。

    钉「同源」而非「同值 0.9」：effective_threshold 的来源是 get_with_lock 的
    similarity_threshold 形参（None → 1.0），修法不许引入第二权威（如把 0.9
    硬编码进降级路径）。
    """
    service = SemanticCacheService(redis_client=mock_redis)
    captured: list = []
    monkeypatch.setattr(service, "get", _spy_get(service, captured))

    factory = AsyncMock(return_value={"origin": "factory"})

    result = await service.get_with_lock("q", factory, user_id="u1")

    assert result == {"origin": "factory"}
    assert len(captured) == 2

    main_threshold = _threshold_received(*captured[0])
    fallback_threshold = _threshold_received(*captured[1])

    assert main_threshold == pytest.approx(1.0), "未传参时主路径 effective_threshold 收敛 1.0（既有行为）"
    assert fallback_threshold == pytest.approx(
        main_threshold
    ), f"未传参时降级路径必须随主路径同源收敛 1.0，实际 {fallback_threshold}"
