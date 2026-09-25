"""G-05（wt395）恢复面回归：CRDT 快照持久化必须在 decode_responses=True 共享客户端形态下可用。

缺陷背景（多端恢复面断裂）：cache_service 的共享 Redis 客户端是
``decode_responses=True``；Yjs 快照是二进制。redis-py 在 **响应解析层**就对
GET 结果做 utf-8 解码，二进制快照直接 UnicodeDecodeError——
``CRDTPersistenceManager.restore()`` 里的 ``str`` 兜底根本执行不到。
触发面：引擎重启/会话 TTL 驱逐后第一台重连设备
``SyncCollaborativeGalaxy → restore()`` 必失败（servicer 捕获后 success=False），
即"断线重连/多端恢复"场景下协作星图不可恢复。

本测试用 fakeredis 复刻生产客户端形态（decoded 共享客户端 + binary 客户端），
钉死 persist→restore 往返对二进制安全；若二进制客户端缺失则显式失败（不静默跳过）。
"""

from __future__ import annotations

import fakeredis.aioredis
import pytest
import y_py as Y

import app.services.galaxy.crdt_persistence as crdt_persistence
from app.services.galaxy.crdt_persistence import CRDTPersistenceManager


def _make_doc(node_key: str) -> Y.YDoc:
    doc = Y.YDoc()
    galaxy_map = doc.get_map("galaxy")
    with doc.begin_transaction() as txn:
        galaxy_map.set(txn, node_key, Y.YMap({"mastery": 42, "from": "g05-test"}))
    return doc


@pytest.mark.asyncio
async def test_crdt_snapshot_roundtrip_is_binary_safe(monkeypatch):
    """persist→restore 往返：共享 decoded 客户端形态下二进制快照必须可恢复。"""
    decoded_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    binary_client = fakeredis.aioredis.FakeRedis(decode_responses=False)

    async def fake_binary_redis(fallback):
        assert fallback is decoded_client, "回退参数应为调用方共享客户端"
        return binary_client

    monkeypatch.setattr(crdt_persistence, "_get_binary_redis", fake_binary_redis)

    manager = CRDTPersistenceManager(decoded_client, None)  # type: ignore[arg-type]
    await manager.persist_snapshot("g05-roundtrip-galaxy", _make_doc("node_a"))

    # 断线重连后的新端：内存无会话 → restore() 从 Redis 快照恢复
    restored = await manager.restore("g05-roundtrip-galaxy")
    assert "node_a" in restored.get_map("galaxy")


@pytest.mark.asyncio
async def test_crdt_restore_without_binary_client_fails_loudly(monkeypatch):
    """二进制客户端不可用且共享客户端在场：快照读取不得静默成功成乱码路径。

    修复后 restore() 的读取永远走 _get_binary_redis；注入 None（构建失败回退
    共享 decoded 客户端）时，对二进制快照要么成功（不可能——decoded 解码失败）
    要么抛出明确异常，绝不返回半恢复文档冒充成功。
    """
    decoded_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    binary_client = fakeredis.aioredis.FakeRedis(decode_responses=False)

    manager = CRDTPersistenceManager(decoded_client, None)  # type: ignore[arg-type]
    # 先用二进制客户端写一份真实快照（绕过被测方法, 直接落键）
    update_data = Y.encode_state_as_update(_make_doc("node_b"))
    await binary_client.set("crdt:snapshot:g05-no-binary", update_data, ex=86400)

    async def broken_binary(fallback):
        return None  # 二进制客户端构建失败且无回退

    monkeypatch.setattr(crdt_persistence, "_get_binary_redis", broken_binary)

    with pytest.raises((RuntimeError, UnicodeDecodeError)):
        await manager.restore("g05-no-binary")
