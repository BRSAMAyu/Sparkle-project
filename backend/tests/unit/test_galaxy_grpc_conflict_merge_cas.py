"""V3-FIX-295（wt583）: gRPC 冲突合并 retry 无锁 SELECT + 盲写 upsert（TOCTOU）— 红→绿固化钉。

wt576 复核（v3-output/WT576-VERIFY/verdicts.md F4 节）按序注入复现：

    seed: mastery=10, revision=5
    step1 A stale write (revision=3, mastery=30) → conflict
    step2 W atomic write (revision=5, mastery=90) → success   ← 窗口内并发写
    step3 A blind retry (无 version/revision, mastery=30) → success
    FINAL mastery_score = 30.0   （max-wins 要求 90）

本文件用真实 ``GalaxyGrpcServiceImpl.UpdateNodeMastery`` + 真实
``GalaxyService.update_node_mastery``（sqlite 内存库，全 schema）按序注入
同一交错：monkeypatch 包装 ``update_node_mastery``，在无 revision 的合并腿
进入前先提交 W 的高值原子写（等价于"窗口内并发写 90"）。

修复契约（CAS，V3-FIX-295）：冲突后的合并走服务端原子 max-wins
compare-and-set —— stored ≥ incoming 时零写返回（幂等，窗口内更高值不被
覆盖），stored < incoming 时原子写入 incoming；不再存在"读旧值→盲写"窗口。
CAS 谓词在 PG（生产）与 sqlite（测试）两方言都真实生效，故本钉在 sqlite
即可固化行为等价性。

运行（纪律命令口径）::

    cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v \\
        python -m pytest tests/unit/test_galaxy_grpc_conflict_merge_cas.py -q
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.galaxy import UserNodeStatus
from app.services import galaxy_grpc_service as grpc_module
from app.services.galaxy_service import GalaxyService


class _FakeContext:
    def __init__(self, metadata: dict[str, str]):
        self._metadata = tuple(metadata.items())
        self.code = None
        self.details = None

    def invocation_metadata(self):
        return self._metadata

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


@pytest_asyncio.fixture()
async def session_factory():
    """独立 sqlite 内存库（口径同 tests/conftest.py db_session）。

    conftest 已把全部模型注册进 Base.metadata，这里自建引擎建全 schema，
    交给真实 servicer（它自带 ``async with self.db_session_factory()`` 会话
    生命周期）与并发写方注入会话共用。
    """
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_status(factory, *, user_id, node_id, mastery: float, revision: int) -> None:
    async with factory() as db:
        db.add(
            UserNodeStatus(
                user_id=user_id,
                node_id=node_id,
                mastery_score=mastery,
                revision=revision,
                is_unlocked=True,
            )
        )
        await db.commit()


async def _read_final(factory, *, user_id, node_id) -> tuple[float, int]:
    async with factory() as db:
        row = await db.get(UserNodeStatus, (user_id, node_id))
        assert row is not None
        return float(row.mastery_score), int(row.revision)


def _wrap_with_concurrent_writer(
    monkeypatch: pytest.MonkeyPatch,
    session_factory,
    *,
    user_id,
    node_id,
    concurrent_mastery: float,
    concurrent_revision: int,
) -> list[dict[str, Any]]:
    """包装 ``GalaxyService.update_node_mastery``：无 revision 的合并腿进入前，
    先以独立会话原子提交并发写方 W 的高值（revision CAS 路径）。

    这正是 TOCTOU 窗口的按序注入：冲突检出之后、合并写落库之前，另一写方
    提交了更高的 mastery。返回调用记录供断言。
    """
    original = GalaxyService.update_node_mastery
    calls: list[dict[str, Any]] = []

    async def wrapper(
        self, *, user_id, node_id, new_mastery, reason, version=None, request_id=None, revision=None, merge_higher=False
    ):
        calls.append({"revision": revision, "new_mastery": new_mastery, "merge_higher": merge_higher})
        if revision is None:
            # 窗口内并发写方：原子 revision-CAS 提交更高掌握度
            async with session_factory() as wdb:
                wsvc = GalaxyService(wdb)
                await original(
                    wsvc,
                    user_id=user_id,
                    node_id=node_id,
                    new_mastery=concurrent_mastery,
                    reason="concurrent_writer",
                    revision=concurrent_revision,
                )
        return await original(
            self,
            user_id=user_id,
            node_id=node_id,
            new_mastery=new_mastery,
            reason=reason,
            version=version,
            request_id=request_id,
            revision=revision,
            merge_higher=merge_higher,
        )

    monkeypatch.setattr(GalaxyService, "update_node_mastery", wrapper)
    return calls


def _make_request(user_id, node_id, *, mastery: int) -> Any:
    return grpc_module.galaxy_service_pb2.UpdateNodeMasteryRequest(
        user_id=str(user_id),
        node_id=str(node_id),
        mastery=mastery,
        reason="offline_sync",
        revision=3,  # 过期 revision → 冲突
    )


@pytest.mark.asyncio
async def test_conflict_merge_keeps_concurrent_higher_mastery(session_factory):
    """红→绿主钉：冲突→窗口内并发写 90→合并腿 30 —— 最终必须 90 胜出。

    修前（无锁 SELECT + 盲写 upsert）：盲写 30 覆盖 90，最终 30.0（红）。
    修后（服务端原子 CAS）：stored(90) ≥ incoming(30) 零写返回，最终 90.0。
    """
    user_id = uuid4()
    node_id = uuid4()
    await _seed_status(session_factory, user_id=user_id, node_id=node_id, mastery=10.0, revision=5)

    servicer = grpc_module.GalaxyGrpcServiceImpl(db_session_factory=session_factory)
    request = _make_request(user_id, node_id, mastery=30)
    context = _FakeContext({"user-id": str(user_id)})

    monkeypatch = pytest.MonkeyPatch()
    try:
        calls = _wrap_with_concurrent_writer(
            monkeypatch,
            session_factory,
            user_id=user_id,
            node_id=node_id,
            concurrent_mastery=90.0,
            concurrent_revision=5,
        )
        response = await servicer.UpdateNodeMastery(request, context)
    finally:
        monkeypatch.undo()

    assert response.success is True
    assert response.new_mastery == 90, f"max-wins 要求 90 胜出，实际 {response.new_mastery}（盲写回退即红）"
    # CAS 零写：old=new=stored（本腿未写库，报告的是已胜出的现值）
    assert response.old_mastery == 90
    assert response.current_revision == 6

    final_mastery, final_revision = await _read_final(session_factory, user_id=user_id, node_id=node_id)
    assert final_mastery == 90.0, "库内最终值必须保留并发写方的 90"
    assert final_revision == 6, "CAS 零写不得推进 revision（5 → W 写 6 后保持）"

    # 结构断言：冲突后合并腿不得携带 revision（携带则注入位置错位），
    # 且必须走服务端 CAS（merge_higher=True）——这正是 TOCTOU 收口点
    merge_legs = [c for c in calls if c["revision"] is None]
    assert len(merge_legs) == 1
    assert merge_legs[0]["new_mastery"] == 30
    assert merge_legs[0]["merge_higher"] is True


@pytest.mark.asyncio
async def test_conflict_merge_still_writes_when_incoming_higher(session_factory):
    """守门反测：CAS 不得吞掉合法的更高 incoming —— 窗口内无并发写时，合并腿须真实写入。"""
    from unittest.mock import patch

    user_id = uuid4()
    node_id = uuid4()
    await _seed_status(session_factory, user_id=user_id, node_id=node_id, mastery=10.0, revision=5)

    original = GalaxyService.update_node_mastery
    calls: list[dict[str, Any]] = []

    async def passthrough_wrapper(self, **kwargs):
        calls.append({"revision": kwargs.get("revision"), "new_mastery": kwargs.get("new_mastery")})
        return await original(self, **kwargs)

    servicer = grpc_module.GalaxyGrpcServiceImpl(db_session_factory=session_factory)
    request = _make_request(user_id, node_id, mastery=90)
    context = _FakeContext({"user-id": str(user_id)})

    with patch.object(GalaxyService, "update_node_mastery", passthrough_wrapper):
        response = await servicer.UpdateNodeMastery(request, context)

    assert response.success is True
    assert response.new_mastery == 90, "incoming 更高时合并必须真实写入"
    assert response.old_mastery == 10

    final_mastery, final_revision = await _read_final(session_factory, user_id=user_id, node_id=node_id)
    assert final_mastery == 90.0
    assert final_revision == 6


@pytest.mark.asyncio
async def test_conflict_merge_cas_noop_is_idempotent_replay(session_factory):
    """CAS 零写路径即幂等重放：stored(90) ≥ incoming(30) → 库值与 revision 均不动。"""
    user_id = uuid4()
    node_id = uuid4()
    await _seed_status(session_factory, user_id=user_id, node_id=node_id, mastery=90.0, revision=6)

    # 并发写已落库（90/rev6）：直接走合并腿（无 revision）＝ CAS 零写场景
    servicer = grpc_module.GalaxyGrpcServiceImpl(db_session_factory=session_factory)
    request = _make_request(user_id, node_id, mastery=30)
    context = _FakeContext({"user-id": str(user_id)})

    response = await servicer.UpdateNodeMastery(request, context)

    assert response.success is True
    assert response.new_mastery == 90

    final_mastery, final_revision = await _read_final(session_factory, user_id=user_id, node_id=node_id)
    assert final_mastery == 90.0
    assert final_revision == 6, "零写不得推进 revision"
