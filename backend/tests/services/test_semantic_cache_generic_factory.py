"""V3-FIX-225（T-semantic-cache-generic-factory）: get_with_lock 泛型工厂契约。

此前签名声明 ``factory_func``（完全无注解）且返回写死 ``dict[str, Any] | None``，
但工厂是泛型调用面：galaxy/retrieval_service.py:239 把返回
``list[SearchResultItem]`` 的 ``_execute_hybrid_search`` 直接当 factory 传入，
未命中路径原样透传工厂返回值——异型被静态谎称 dict（mypy 在调用点报
Incompatible return value）。本套件锁定两层诚实契约：

1. 签名泛型化：factory_func 必须标注 ``Callable[..., Awaitable[T]]``、返回
   注解必须随工厂泛型（TypeVar），异型不再被写死为 dict；
2. 序列化保形证据（命中/未命中两形态）：JSON 稳定形态（dict / list[dict]）
   经真实 json.dumps → json.loads 往返后同型同值——命中路径与未命中路径对
   同一调用点给出同一形态。

保形契约以「JSON 稳定形态」为界：tuple 等往返变型与不可 JSON 序列化载荷
（如 Pydantic 模型——缓存写入会静默失败，见台账 V3-FIX-240）不在本层保形
范围内。
"""

from __future__ import annotations

import typing
from collections.abc import Awaitable
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.semantic_cache_service import SemanticCacheService


class _UnconfiguredEmbedding:
    """打桩 embedding 服务：避免 set() 触发真实 API 调用（对齐 D3 测试口径）。"""

    @staticmethod
    def is_configured() -> bool:
        return False


@pytest.fixture
def mock_redis():
    mock = MagicMock()

    # Async methods need AsyncMock
    mock.get = AsyncMock()
    mock.setex = AsyncMock()
    mock.hincrby = AsyncMock()
    mock.exists = AsyncMock(return_value=True)  # 统计键视为已初始化
    mock.hset = AsyncMock()
    mock.delete = AsyncMock()
    mock.sadd = AsyncMock()
    mock.smembers = AsyncMock(return_value=set())
    mock.scard = AsyncMock(return_value=0)

    # Mock redis lock（async context manager）
    mock_lock = MagicMock()
    mock_lock.__aenter__ = AsyncMock(return_value=True)
    mock_lock.__aexit__ = AsyncMock(return_value=None)
    mock.lock.return_value = mock_lock
    return mock


@pytest.fixture
def no_embedding(monkeypatch):
    import app.services.semantic_cache_service as sc_mod

    monkeypatch.setattr(sc_mod, "embedding_service", _UnconfiguredEmbedding)


# ------------------------------------------------------------------ #
# 红测面：签名诚实性（泛型化前本套件红）
# ------------------------------------------------------------------ #


def test_get_with_lock_signature_is_generic_over_factory_return():
    """工厂可返回异型时，静态契约不得写死 dict——签名必须随工厂泛型。"""
    hints = typing.get_type_hints(SemanticCacheService.get_with_lock)

    # factory_func 此前完全无注解（隐式 Any），泛型契约无从谈起
    assert "factory_func" in hints, "get_with_lock.factory_func 必须有显式类型注解"
    assert typing.get_origin(hints["factory_func"]) is not None, "factory_func 必须标注为泛型 Callable"
    param_args = typing.get_args(hints["factory_func"])
    returnables = [typing.get_origin(a) for a in param_args if a is not Ellipsis]
    assert (
        Awaitable in returnables
    ), f"factory_func 必须是 Callable[..., Awaitable[...]]，实际 {hints['factory_func']!r}"

    # 返回注解必须随工厂泛型（TypeVar），而非写死的 dict[str, Any] | None
    assert isinstance(hints["return"], typing.TypeVar), (
        f"get_with_lock 返回注解必须随工厂泛型（TypeVar），实际 {hints['return']!r}——"
        "工厂返回 list 等异型时该注解是在说谎（未命中路径原样透传工厂返回值）"
    )


# ------------------------------------------------------------------ #
# 实测错配：异型返回值的运行时形态（未命中路径透传）
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_miss_returns_factory_list_untouched(mock_redis, no_embedding):
    """未命中路径：工厂原返回值（list）不被包装、不改型地透传。"""
    service = SemanticCacheService(redis_client=mock_redis)
    mock_redis.get = AsyncMock(return_value=None)  # 全程 miss

    payload = [{"node": {"id": "n1"}, "similarity": 0.9}]
    factory = AsyncMock(return_value=payload)

    result = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=1.0)

    assert result is payload, "未命中路径必须原样透传工厂返回值（零拷贝）"
    assert isinstance(result, list)


# ------------------------------------------------------------------ #
# 序列化保形证据：命中/未命中两形态同型同值（真实 JSON 往返）
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_two_forms_share_shape_for_list_payload(mock_redis, no_embedding):
    """galaxy 型 list 载荷：第一次调用（未命中，工厂产物）与第二次调用
    （命中，json.loads 反序列化产物）同型同值——两形态不分裂。"""
    store: dict = {}

    async def _get(key, *args, **kwargs):
        return store.get(key)

    async def _setex(key, ttl, value, *args, **kwargs):
        store.setdefault(key, value)

    mock_redis.get = AsyncMock(side_effect=_get)
    mock_redis.setex = AsyncMock(side_effect=_setex)

    service = SemanticCacheService(redis_client=mock_redis)
    payload = [{"node": {"id": "n1", "name": "细胞"}, "similarity": 0.9}]
    factory = AsyncMock(return_value=payload)

    miss_form = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=1.0)
    assert isinstance(miss_form, list) and miss_form == payload
    assert store, "JSON 可序列化载荷必须真实写入缓存（保形前提）"

    hit_form = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=1.0)

    assert factory.await_count == 1, "第二次调用必须命中缓存，工厂不得再执行"
    assert isinstance(hit_form, list), f"命中形态必须是 list，实际 {type(hit_form).__name__}——两形态分裂"
    assert hit_form == payload


@pytest.mark.asyncio
async def test_two_forms_share_shape_for_dict_payload(mock_redis, no_embedding):
    """dict 载荷（get_cached_result 的 ``{"nodes": [...]}`` 形态）：两形态保形。"""
    store: dict = {}

    async def _get(key, *args, **kwargs):
        return store.get(key)

    async def _setex(key, ttl, value, *args, **kwargs):
        store.setdefault(key, value)

    mock_redis.get = AsyncMock(side_effect=_get)
    mock_redis.setex = AsyncMock(side_effect=_setex)

    service = SemanticCacheService(redis_client=mock_redis)
    payload = {"nodes": [{"id": "n1", "name": "神经元"}]}
    factory = AsyncMock(return_value=payload)

    miss_form = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=1.0)
    assert isinstance(miss_form, dict) and miss_form == payload

    hit_form = await service.get_with_lock("q", factory, user_id="u1", similarity_threshold=1.0)

    assert factory.await_count == 1
    assert isinstance(hit_form, dict), f"命中形态必须是 dict，实际 {type(hit_form).__name__}"
    assert hit_form == payload
    assert hit_form["nodes"] == payload["nodes"]
