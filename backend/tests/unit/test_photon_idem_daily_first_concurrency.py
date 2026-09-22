"""PHOTON-IDEM · 每日首胜发放毫秒窗口并发双发收口 —— 写侧唯一索引仲裁行为测试.

PHOTON-STREAM 的同日幂等是读侧先查重（``PhotonService._find_existing_transaction``，
check-then-insert）：Redis 缓存失守 + DB 兜底双路径并发时，两个请求在「彼此都还没
写流水」的毫秒窗口内都读到「未发放」→ 双发双计「可兑换基数」。本卡收口 =

- ``photon_transaction_history`` 上的唯一部分索引（迁移 photidem_20260923，只管辖
  ``daily_first:`` 幂等键域）；
- 写侧流水 INSERT ``ON CONFLICT DO NOTHING RETURNING``
  （``PhotonService._insert_daily_first_transaction_arbitrated``）→ 冲突败者与
  读侧门命中同结局（零发放、``deduplicated=True``），发放金额语义零变化。

harness 与 ERR-IDEM-CONCUR（``test_error_mastery_concurrency``）同款：

- 多个独立 session（sqlite 文件库、多条连接）模拟真实并发请求，各自持独立事务；
- 真实 ``PhotonService.grant_photons`` 写入路径（不 stub 流水 INSERT），冲突检测
  直接对着真实部分唯一索引仲裁；
- ``asyncio.Barrier`` 把毫秒窗口放大成确定性交错点：所有协程都通过读侧门
  （_find_existing_transaction）之后才同时放行写入——这正是修复前双发的窗口；
- 断言全部写成交错无关（谁先落账都行）：恰好一方生效、恰好一行流水、余额只加一次。

红线：读侧快路径保留（串行重放不触达写侧）、次日键不被索引吞、域外取值域
（裸 achievement_id 等）不受索引约束。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.shop import PhotonTransactionHistory
from app.models.shop import PhotonTransactionType as DBTxType
from app.models.user import User
from app.services.photon_service import PhotonService, PhotonTransactionType

TEST_DATABASE_URL = "sqlite+aiosqlite://"

DAILY_FIRST_AMOUNT = 30

# 与迁移 photidem_20260923 同构的唯一部分索引 DDL（谓词与迁移严格一致）。
# ORM 建模不含该索引（迁移是唯一入口），测试台需手动补建。
DAILY_FIRST_IDEM_UNIQUE_INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_photon_tx_daily_first_idem
ON photon_transaction_history(user_id, related_item_id)
WHERE related_item_id LIKE 'daily_first:%'
"""


class _ConcurrentRig:
    """多 session（多条连接）+ 共享 schema 的并发测试台。"""

    def __init__(self, engine):
        self.engine = engine

    def session_factory(self):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        return async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def rig(tmp_path):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        f"{TEST_DATABASE_URL}//{tmp_path / 'photon_idem.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(DAILY_FIRST_IDEM_UNIQUE_INDEX_DDL))

    yield _ConcurrentRig(engine)
    await engine.dispose()


async def _seed_user(rig, *, balance: int = 0) -> str:
    factory = rig.session_factory()
    async with factory() as session:
        user = User(
            username=f"photidem_{uuid4().hex[:8]}",
            email="photidem@example.com",
            hashed_password="x",
            photon_balance=balance,
        )
        session.add(user)
        await session.commit()
        return str(user.id)


def _install_gate_barrier(service: PhotonService, barrier: asyncio.Barrier) -> None:
    """毫秒窗口放大器：每个协程**第一次**通过读侧门后在 barrier 处等齐，再同时放行。

    修复前语义下这就是双发窗口（双方都读到「未发放」）；修复后写入侧由
    唯一部分索引仲裁出唯一胜者。注意必须单次拦截：竞态败者在写侧仲裁分支
    会再次调用 _find_existing_transaction 重查胜者行（生产语义），那一次
    不允许再进 barrier——否则败者在已收场的 barrier 上永久等待。
    """
    original_gate = service._find_existing_transaction
    gate_armed = True

    async def _gated(*args, **kwargs):
        nonlocal gate_armed
        seen = await original_gate(*args, **kwargs)
        if gate_armed:
            gate_armed = False
            await barrier.wait()
        return seen

    service._find_existing_transaction = _gated


async def _run_first_win(
    rig,
    user_id: str,
    day: str,
    barrier: asyncio.Barrier,
) -> dict:
    """一个真实请求：独立 session 内跑一次每日首胜发放面 + 请求边界提交。"""
    factory = rig.session_factory()
    async with factory() as session:
        service = PhotonService(session)
        _install_gate_barrier(service, barrier)
        result = await service.grant_photons(
            user_id=user_id,
            amount=DAILY_FIRST_AMOUNT,
            source="daily_first",
            transaction_type=PhotonTransactionType.GRANT_DAILY_FIRST,
            related_item_id=f"daily_first:{day}",
            record_history=True,
            manage_transaction=False,
        )
        # 生产语义：get_db 在请求边界提交（manage_transaction=False 只 flush）
        await session.commit()
        return result


async def _tx_rows(rig, user_id: str, day: str | None = None) -> list[PhotonTransactionHistory]:
    factory = rig.session_factory()
    async with factory() as session:
        stmt = select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == user_id
        )
        if day is not None:
            stmt = stmt.where(PhotonTransactionHistory.related_item_id == f"daily_first:{day}")
        stmt = stmt.order_by(PhotonTransactionHistory.created_at)
        return list((await session.execute(stmt)).scalars().all())


async def _final_balance(rig, user_id: str) -> int:
    factory = rig.session_factory()
    async with factory() as session:
        result = await session.execute(select(User.photon_balance).where(User.id == user_id))
        return int(result.scalar_one())


# ===========================================================================
# 1. 并发同日首胜（毫秒窗口）→ 恰好一发（修复前红：余额 60、流水 ×2）
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_same_day_first_win_grants_exactly_once(rig):
    user_id = await _seed_user(rig, balance=0)
    day = "2026-09-23"
    barrier = asyncio.Barrier(2)  # 所有协程共享同一交错点

    results = await asyncio.gather(*[
        _run_first_win(rig, user_id, day, barrier)
        for _ in range(2)
    ])

    effective = [r for r in results if not r["deduplicated"]]
    deduped = [r for r in results if r["deduplicated"]]
    assert len(effective) == 1, f"并发同日首胜必须恰好生效一次，实际 {len(effective)} 次"
    assert len(deduped) == 1, "败者必须拿到 deduplicated=True 的读侧门同款结局"

    rows = await _tx_rows(rig, user_id, day)
    assert len(rows) == 1, f"同键流水必须恰好一行，实际 {len(rows)}"
    assert rows[0].transaction_type == DBTxType.GRANT_DAILY_FIRST
    assert rows[0].amount == DAILY_FIRST_AMOUNT
    assert (rows[0].balance_before, rows[0].balance_after) == (0, DAILY_FIRST_AMOUNT)

    assert await _final_balance(rig, user_id) == DAILY_FIRST_AMOUNT, "余额只允许加一次"


# ===========================================================================
# 2. 8 并发放大（照 ERR-IDEM-CONCUR 并发模式）→ 仍然恰好一发
# ===========================================================================


@pytest.mark.asyncio
async def test_eight_way_concurrent_first_win_still_exactly_once(rig):
    user_id = await _seed_user(rig, balance=0)
    day = "2026-09-23"
    barrier = asyncio.Barrier(8)  # 所有协程共享同一交错点

    results = await asyncio.gather(*[
        _run_first_win(rig, user_id, day, barrier)
        for _ in range(8)
    ])

    effective = [r for r in results if not r["deduplicated"]]
    assert len(effective) == 1, f"8 并发同键必须恰好生效一次，实际 {len(effective)} 次"
    assert len(await _tx_rows(rig, user_id, day)) == 1
    assert await _final_balance(rig, user_id) == DAILY_FIRST_AMOUNT
    # 基数诚实性：审计流水重放口径下同键只可能贡献一份收入
    assert sum(r.amount for r in await _tx_rows(rig, user_id)) == DAILY_FIRST_AMOUNT


# ===========================================================================
# 3. 竞态败者结局 == 读侧门命中（同形返回：零发放 + 胜者账目）
# ===========================================================================


@pytest.mark.asyncio
async def test_race_loser_outcome_matches_read_gate_hit(rig):
    user_id = await _seed_user(rig, balance=0)
    barrier = asyncio.Barrier(2)  # 所有协程共享同一交错点

    results = await asyncio.gather(*[
        _run_first_win(rig, user_id, "2026-09-23", barrier)
        for _ in range(2)
    ])
    winner = next(r for r in results if not r["deduplicated"])
    loser = next(r for r in results if r["deduplicated"])

    rows = await _tx_rows(rig, user_id, "2026-09-23")
    assert len(rows) == 1
    winner_row = rows[0]

    # 败者返回胜者的账目快照（与读侧门命中 _find_existing_transaction 同构）
    assert loser["deduplicated"] is True
    assert loser["old_balance"] == winner_row.balance_before
    assert loser["new_balance"] == winner_row.balance_after
    assert loser["amount"] == DAILY_FIRST_AMOUNT
    assert loser["source"] == "daily_first"
    assert winner["deduplicated"] is False
    assert (winner["old_balance"], winner["new_balance"]) == (0, DAILY_FIRST_AMOUNT)


# ===========================================================================
# 4. 串行重复（已提交后重放）→ 读侧快路径仍然生效（保留不回归）
# ===========================================================================


@pytest.mark.asyncio
async def test_sequential_replay_still_uses_read_fast_path(rig):
    user_id = await _seed_user(rig, balance=0)
    day = "2026-09-23"

    first = await _run_first_win(rig, user_id, day, asyncio.Barrier(1))
    assert first["deduplicated"] is False

    # 串行重放：读侧门直接命中，绝不触达写侧仲裁 INSERT（快路径保留）
    factory = rig.session_factory()
    async with factory() as session:
        service = PhotonService(session)
        service._insert_daily_first_transaction_arbitrated = AsyncMock(
            side_effect=AssertionError("串行重放不得触达写侧仲裁")
        )
        replay = await service.grant_photons(
            user_id=user_id,
            amount=DAILY_FIRST_AMOUNT,
            source="daily_first",
            transaction_type=PhotonTransactionType.GRANT_DAILY_FIRST,
            related_item_id=f"daily_first:{day}",
            record_history=True,
        )
        service._insert_daily_first_transaction_arbitrated.assert_not_awaited()
        await session.commit()

    assert replay["deduplicated"] is True
    assert len(await _tx_rows(rig, user_id, day)) == 1
    assert await _final_balance(rig, user_id) == DAILY_FIRST_AMOUNT


# ===========================================================================
# 5. 红线：次日键自然变化 → 唯一索引绝不吞次日首胜（D-COMM-2 警告面）
# ===========================================================================


@pytest.mark.asyncio
async def test_next_day_first_win_not_blocked_by_index(rig):
    user_id = await _seed_user(rig, balance=0)

    day1 = await _run_first_win(rig, user_id, "2026-09-23", asyncio.Barrier(1))
    day2 = await _run_first_win(rig, user_id, "2026-09-24", asyncio.Barrier(1))

    assert day1["deduplicated"] is False and day2["deduplicated"] is False
    rows = await _tx_rows(rig, user_id)
    assert [r.related_item_id for r in rows] == [
        "daily_first:2026-09-23",
        "daily_first:2026-09-24",
    ]
    assert await _final_balance(rig, user_id) == DAILY_FIRST_AMOUNT * 2


# ===========================================================================
# 6. 域外取值域不受索引约束：同键裸 achievement_id 重复写不违约（部分索引不越界）
# ===========================================================================


@pytest.mark.asyncio
async def test_out_of_domain_keys_not_constrained_by_index(rig):
    """裸 achievement_id（域外）即使读侧门失守也不该被索引误伤——
    索引只管辖 daily_first: 域；域外重复本就存在合法场景（重试补发等）。"""
    user_id = await _seed_user(rig, balance=0)

    async def _grant_bare_key():
        factory = rig.session_factory()
        async with factory() as session:
            service = PhotonService(session)
            # 读侧门失守模拟（返回 None = 域外无去重语义的既有写入方形态）
            service._find_existing_transaction = AsyncMock(return_value=None)
            result = await service.grant_photons(
                user_id=user_id,
                amount=10,
                source="achievement:ach_001",
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
                related_item_id="ach_001",
                record_history=True,
                manage_transaction=False,
            )
            await session.commit()
            return result

    await _grant_bare_key()
    await _grant_bare_key()  # 不违约（域外不在部分索引谓词内）

    factory = rig.session_factory()
    async with factory() as session:
        count = len(
            list(
                (
                    await session.execute(
                        select(PhotonTransactionHistory.id).where(
                            PhotonTransactionHistory.user_id == user_id,
                            PhotonTransactionHistory.related_item_id == "ach_001",
                        )
                    )
                ).scalars()
            )
        )
    assert count == 2, "域外同键重复写必须不受索引约束"
