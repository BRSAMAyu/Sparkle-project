"""G-05（wt395）恢复风暴回归：多端**并发**首连 SyncCollaborativeGalaxy 不得丢单。

缺陷背景（本地 16 并发首连实证 6/16 台设备并入, 10 台更新丢失）：服务重启/
会话驱逐后多台设备同时重连时, 旧实现的"查字典 → miss → restore + 新建 + 入字典"
三步在锁外交错——每个并发请求各自 restore 出空文档、各挂各的会话, 后入字典者
覆盖先入者, 先到设备的 CRDT 更新全部丢失（crdt_snapshots 只剩最后一份局部态）。

修复：get-or-create 原子化（``_get_or_create_collaborative_session``, restore 的
外部 IO 移入 ``_sessions_lock``）——并发首连串行化冷路径, 全部更新并入同一共享
YDoc。热路径（会话已在案）仍是锁内一次字典读。

Redis 面用 fakeredis 复刻生产客户端形态（共享 decode_responses=True + 二进制
客户端 decode_responses=False, 同 test_g05_crdt_restore_binary_safety）。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import fakeredis.aioredis
import pytest
import y_py as Y

import app.services.galaxy.crdt_persistence as crdt_persistence
import app.services.galaxy_grpc_service as grpc_module
from app.services.galaxy.crdt_persistence import CRDTPersistenceManager
from app.services.galaxy_grpc_service import GalaxyGrpcServiceImpl

DEVICES = 16


class _FakeDB:
    """restore() 的 DB 回退面: 永远无快照行; log_operation 的 add/commit 面最小化。"""

    class _Result:
        def scalar_one_or_none(self):
            return None

    async def execute(self, *args, **kwargs):
        return self._Result()

    def add(self, obj):
        return None

    async def commit(self):
        return None


def _client_update(device_idx: int) -> bytes:
    doc = Y.YDoc()
    m = doc.get_map("galaxy")
    with doc.begin_transaction() as txn:
        m.set(txn, f"device_{device_idx}", Y.YMap({"mastery": 60 + device_idx}))
    return Y.encode_state_as_update(doc)


@pytest.fixture()
async def storm_env(monkeypatch):
    binary = fakeredis.aioredis.FakeRedis(decode_responses=False)

    async def fake_binary_redis(fallback):
        # fakeredis 无真实 IO 让渡: 不 sleep(0) 时整个"restore→store"竞态窗口
        # 在单任务内同步走完, 旧代码的丢单缺陷无法复现（红测失真）。
        # sleep(0) 强制一次事件循环让渡, 等价真实 Redis 网络往返的挂起点。
        await asyncio.sleep(0)
        return binary

    monkeypatch.setattr(crdt_persistence, "_get_binary_redis", fake_binary_redis)
    grpc_module._active_collaborative_sessions.clear()
    yield binary
    grpc_module._active_collaborative_sessions.clear()


@pytest.mark.asyncio
async def test_concurrent_first_connect_merges_all_devices(storm_env):
    galaxy_id = f"g05-race-{id(object()):x}"

    @asynccontextmanager
    async def fake_session_factory():
        yield _FakeDB()

    servicer = GalaxyGrpcServiceImpl(db_session_factory=fake_session_factory)
    context = SimpleNamespace(
        invocation_metadata=lambda: (("user-id", "11111111-1111-1111-1111-111111111111"),),
        set_code=lambda code: None,
        set_details=lambda details: None,
    )

    async def sync_one(i: int):
        request = SimpleNamespace(galaxy_id=galaxy_id, partial_update=_client_update(i), user_id="")
        return await servicer.SyncCollaborativeGalaxy(request, context)

    responses = await asyncio.gather(*[sync_one(i) for i in range(DEVICES)])
    assert all(r.success for r in responses), "并发首连不允许任何设备失败"

    # 全部并入后, 第 N+1 台设备重连 restore: 16 台设备的更新都必须在合并态。
    # （模块级 _get_binary_redis 仍被 storm_env monkeypatch 指向 binary 客户端,
    #   与生产同形态：restore 走二进制客户端读快照。）
    mgr = CRDTPersistenceManager(storm_env, None)  # type: ignore[arg-type]
    ydoc = await mgr.restore(galaxy_id)
    restored = set(ydoc.get_map("galaxy").keys())
    assert restored == {
        f"device_{i}" for i in range(DEVICES)
    }, f"恢复风暴丢单: 合并态只含 {len(restored)}/{DEVICES} 台设备 {sorted(restored)}"
