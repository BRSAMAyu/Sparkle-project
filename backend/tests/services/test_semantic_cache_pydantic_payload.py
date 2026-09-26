"""V3-FIX-240（T-semantic-cache-pydantic-payload）红测：galaxy hybrid_search 型
Pydantic 载荷的语义缓存写路径死亡实录。

台账行（v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-240）：retrieval_service.py:239
经 get_with_lock 把返回 ``list[SearchResultItem]`` 的 ``_execute_hybrid_search``
当 factory 传入，``set()`` 的 ``json.dumps`` 对 Pydantic 模型抛 TypeError、被
except 吞成 error 日志（返回 False，无指标无告警）——语义缓存对该调用方零命中、
每次全量检索（pydantic 2.12.5 下 wt517 实锤复现，见本文件机制实锤测试）。

本套件锁定台账行内"序列化保形三选一"的裁决（① 写侧归一 + 命中侧重水化，
兼收 ② 的写失败可观测）：

1. 命中实录：Pydantic 载荷第一次调用（未命中→工厂执行→写缓存）后，第二次
   调用必须命中缓存（工厂不再执行、total_hits 计数增长），修前 0 命中
   （工厂 await_count==2）；
2. 真保形：命中形态与未命中形态**同型同值**——命中侧不是裸 ``list[dict]``
   （那会把两形态真分裂写进调用方：search_agent 与
   galaxy_service.build_evidence_pack 对 ``item.node.id`` 的属性访问会在
   缓存命中时 AttributeError），而是经骨架重水化回 ``list[SearchResultItem]``；
3. 不掩盖：真异型载荷（不可序列化对象）写失败必须可观测（写失败指标按
   reason 计数），不允许静默吞成一行 error 日志。
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.sector import SectorCode
from app.schemas.galaxy import NodeBase, SearchResultItem, UserStatusInfo
from app.services.semantic_cache_service import SemanticCacheService


class _UnconfiguredEmbedding:
    """打桩 embedding 服务：避免 set() 触发真实 API 调用（对齐 V3-FIX-225 测试口径）。"""

    @staticmethod
    def is_configured() -> bool:
        return False


@pytest.fixture
def mock_redis():
    mock = MagicMock()

    mock.get = AsyncMock()
    mock.setex = AsyncMock()
    mock.hincrby = AsyncMock()
    mock.exists = AsyncMock(return_value=True)  # 统计键视为已初始化
    mock.hset = AsyncMock()
    mock.delete = AsyncMock()
    mock.sadd = AsyncMock()
    mock.smembers = AsyncMock(return_value=set())
    mock.scard = AsyncMock(return_value=0)

    mock_lock = MagicMock()
    mock_lock.__aenter__ = AsyncMock(return_value=True)
    mock_lock.__aexit__ = AsyncMock(return_value=None)
    mock.lock.return_value = mock_lock
    return mock


@pytest.fixture
def no_embedding(monkeypatch):
    import app.services.semantic_cache_service as sc_mod

    monkeypatch.setattr(sc_mod, "embedding_service", _UnconfiguredEmbedding)


def _wire_store(mock_redis) -> dict:
    """把 mock redis 的 get/setex 接到真实字符串存储上（JSON 往返不经手软）。"""
    store: dict = {}

    async def _get(key, *args, **kwargs):
        return store.get(key)

    async def _setex(key, ttl, value, *args, **kwargs):
        store.setdefault(key, value)

    mock_redis.get = AsyncMock(side_effect=_get)
    mock_redis.setex = AsyncMock(side_effect=_setex)
    return store


def _make_item(name: str, *, with_status: bool = False) -> SearchResultItem:
    status = None
    if with_status:
        status = UserStatusInfo(
            mastery_score=87.5,
            total_study_minutes=120,
            study_count=9,
            is_unlocked=True,
            is_collapsed=False,
            is_favorite=True,
            first_unlock_at=datetime(2026, 9, 1, 12, 30, 0),
            last_study_at=datetime(2026, 9, 20, 8, 0, 0),
            next_review_at=datetime(2026, 10, 1, 9, 15, 0),
            decay_paused=False,
            status="brilliant",
            brightness=0.925,
        )
    return SearchResultItem(
        node=NodeBase(
            id=uuid4(),
            name=name,
            name_en=name,
            description=f"{name}的描述",
            importance_level=4,
            sector_code=SectorCode.LIFE,
            sector_weights={"LIFE": 6, "WISDOM": 2},
            is_seed=True,
            tags=["生物"],
            keywords=["细胞", name],
            global_spark_count=3,
        ),
        similarity=0.87,
        user_status=status,
    )


# ------------------------------------------------------------------ #
# 机制实锤（wt517 复现，修前修后恒真——只证明死亡机理，非红测断言）
# ------------------------------------------------------------------ #


def test_raw_json_dumps_on_search_result_item_raises_type_error():
    """wt517 实锤机理：json.dumps 对 pydantic 2.12.5 模型抛 TypeError——
    这就是 hybrid_search 载荷在 set() 里被吞掉的原始死因。"""
    payload = {"data": [_make_item("细胞学说")]}
    with pytest.raises(TypeError):
        json.dumps(payload)


# ------------------------------------------------------------------ #
# 红测 1：hybrid_search 载荷缓存命中实录（修前 0 命中）
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_hybrid_search_payload_second_call_hits_cache(mock_redis, no_embedding):
    """galaxy hybrid_search 同款载荷（list[SearchResultItem]）过 get_with_lock：
    第一次未命中（工厂执行），第二次必须命中（工厂不再执行、total_hits 增长）。
    修前：set() 静默死亡 → 第二次仍全量检索（await_count==2、0 命中）。"""
    _wire_store(mock_redis)
    service = SemanticCacheService(redis_client=mock_redis)

    payload = [_make_item("细胞学说"), _make_item("神经元", with_status=True)]
    factory = AsyncMock(return_value=payload)

    await service.get_with_lock("突变与自然选择", factory, user_id="u1", similarity_threshold=1.0)
    assert factory.await_count == 1

    await service.get_with_lock("突变与自然选择", factory, user_id="u1", similarity_threshold=1.0)

    assert factory.await_count == 1, (
        f"第二次调用必须命中缓存（工厂 await_count 应为 1，实际 {factory.await_count}）——"
        "写路径对 Pydantic 载荷静默死亡（json.dumps TypeError 被 set() 吞掉），"
        "语义缓存对该调用方零命中、每次全量检索"
    )
    hit_stat_calls = [call for call in mock_redis.hincrby.await_args_list if call.args[1:2] == ("total_hits",)]
    assert hit_stat_calls, "第二次调用必须产生 total_hits 计数（修前实录：0 命中）"


# ------------------------------------------------------------------ #
# 红测 2：真保形——命中形态与未命中形态同型同值（list[SearchResultItem]）
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_hit_form_is_same_typed_models_as_miss_form(mock_redis, no_embedding):
    """命中侧不得以裸 dict 形态穿透到调用方（两形态真分裂）：命中形态必须是
    list[SearchResultItem] 且与工厂产物同值——含 UUID/枚举/datetime 字段往返。"""
    _wire_store(mock_redis)
    service = SemanticCacheService(redis_client=mock_redis)

    payload = [_make_item("细胞学说"), _make_item("神经元", with_status=True)]
    factory = AsyncMock(return_value=payload)

    miss_form = await service.get_with_lock("自然选择", factory, user_id="u1", similarity_threshold=1.0)
    hit_form = await service.get_with_lock("自然选择", factory, user_id="u1", similarity_threshold=1.0)

    assert isinstance(hit_form, list), f"命中形态必须是 list，实际 {type(hit_form).__name__}"
    assert all(isinstance(item, SearchResultItem) for item in hit_form), (
        "命中形态必须是 list[SearchResultItem]——裸 list[dict] 会让 "
        "search_agent/build_evidence_pack 的 item.node 属性访问在缓存命中时 AttributeError"
    )
    assert hit_form == miss_form, "命中形态必须与未命中形态同值（真保形，非 JSON 近似）"
    typed_status = hit_form[1].user_status
    assert (
        typed_status is not None and typed_status.status.value == "brilliant"
    ), "嵌套枚举必须重水化为原枚举（而非裸 str）"
    assert hit_form[1].node.id == miss_form[1].node.id


# ------------------------------------------------------------------ #
# 红测 3：复合容器里的模型也要保形（dict 载荷嵌模型）
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_dict_payload_containing_models_round_trips(mock_redis, no_embedding):
    """dict 载荷内嵌 Pydantic 模型（写侧归一须递归）：第二次调用命中且同型同值。"""
    _wire_store(mock_redis)
    service = SemanticCacheService(redis_client=mock_redis)

    item = _make_item("突触可塑性")
    payload = {"total": 1, "items": [item], "note": "文本原样"}
    factory = AsyncMock(return_value=payload)

    miss_form = await service.get_with_lock("突触", factory, user_id="u1", similarity_threshold=1.0)
    hit_form = await service.get_with_lock("突触", factory, user_id="u1", similarity_threshold=1.0)

    assert factory.await_count == 1, f"复合容器载荷同样不允许写路径死亡（await_count 实际 {factory.await_count}）"
    assert hit_form["items"] == miss_form["items"]
    assert isinstance(hit_form["items"][0], SearchResultItem)
    assert hit_form == miss_form


# ------------------------------------------------------------------ #
# 红测 4：序列化保形契约（wt517 json.dumps→loads 契约测试的扩展）
# ------------------------------------------------------------------ #


def test_normalized_payload_survives_real_json_round_trip():
    """写侧归一产物必须经真实 json.dumps→json.loads 往返，再经骨架重水化
    与原载荷同型同值（保形契约的纯函数面）。"""
    from app.services.semantic_cache_service import _normalize_for_cache, _rehydrate_from_skeleton

    item = _make_item("自然选择", with_status=True)
    payload = [_make_item("细胞学说"), item]

    normalized, skeleton = _normalize_for_cache(payload)
    assert skeleton is not None, "含模型载荷必须产出重水化骨架"

    round_tripped = json.loads(json.dumps({"data": normalized}))["data"]
    restored = _rehydrate_from_skeleton(round_tripped, skeleton)

    assert restored == payload, "归一→JSON 往返→重水化必须与原载荷同型同值"
    assert all(isinstance(i, SearchResultItem) for i in restored)


def test_plain_payload_stays_byte_identical():
    """纯 JSON 原生载荷不产出骨架、存储形态与旧格式一致（向后兼容）。"""
    from app.services.semantic_cache_service import _normalize_for_cache

    payload = {"nodes": [{"id": "n1"}], "nums": [1, 2.5, None, True]}
    normalized, skeleton = _normalize_for_cache(payload)
    assert skeleton is None
    assert normalized == payload


# ------------------------------------------------------------------ #
# 红测 5：不掩盖——真异型载荷写失败必须可观测
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_unserializable_payload_failure_is_observable(mock_redis, no_embedding):
    """骨架归一救不了真异型（如 object()）：写失败必须返回 False **且**在
    SEMANTIC_CACHE_WRITE_FAILURE_TOTAL 上留痕，不允许静默吞掉。"""
    service = SemanticCacheService(redis_client=mock_redis)

    import app.core.metrics as metrics_mod

    counter = getattr(metrics_mod, "SEMANTIC_CACHE_WRITE_FAILURE_TOTAL", None)
    assert counter is not None, "V3-FIX-240：写失败必须有显式指标（现状被 except 静默吞掉）"

    before = counter.labels(reason="serialization")._value.get()
    ok = await service.set("异型查询", {"blob": object()}, user_id="u1")
    after = counter.labels(reason="serialization")._value.get()

    assert ok is False, "写失败必须如实返回 False"
    assert after == before + 1, "序列化写失败必须落指标（修前仅一行 error 日志，无指标无告警）"
