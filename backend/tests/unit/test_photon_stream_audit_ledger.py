"""PHOTON-STREAM · 每日首胜 / combo 加成的审计流水补录——红→绿测试面。

D-COMM-2 诚实申报的两个发放侧缝隙，本卡收敛（只补记录，不改发放规则）：
1. 每日首胜发放点补写 ``grant_daily_first`` 审计流水，去重键
   ``related_item_id="daily_first:<当日 ISO 日期>"``——同日幂等、次日不吞；
2. combo 加成补写 ``grant_bonus`` 流水（新枚举成员，杜绝 admin_adjustment
   兜底误标），去重键每事件唯一（uuid4）——连击窗口内合法重复触发永不互吞；
3. 可兑换基数重放含两类新流水（D-COMM-2 词表同步收录 ``grant_bonus``）；
4. 红线钉死：连续两日首胜两天都入流水、两天都计基数（防 D-COMM-2 警告的
   「补流水吞次日首胜」回归）。
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.shop import PhotonTransactionHistory
from app.models.shop import PhotonTransactionType as DBTxType
from app.services import achievement_engine as achievement_engine_module
from app.services.achievement_engine import AchievementEngine
from app.services.photon_redeem_service import (
    REDEEM_PRO_OK,
    get_redeemable_base,
    redeem_pro,
)
from app.services.photon_service import PhotonService, PhotonTransactionType

DAILY_FIRST_AMOUNT = 30


async def _tx_rows(db, user_id) -> list[PhotonTransactionHistory]:
    rows = (
        await db.execute(
            select(PhotonTransactionHistory)
            .where(PhotonTransactionHistory.user_id == user_id)
            .order_by(PhotonTransactionHistory.created_at)
        )
    ).scalars().all()
    return list(rows)


class _FixedDate:
    """替身：钉死 check_daily_first 的「今日」，跨日场景手动推进。"""

    current = date(2026, 9, 22)

    @classmethod
    def today(cls) -> date:
        return cls.current


@pytest.fixture
def fixed_date(monkeypatch):
    monkeypatch.setattr(achievement_engine_module, "date", _FixedDate)
    return _FixedDate


# ---------------------------------------------------------------------------
# 1. 每日首胜：发放即入流水（旧码零流水 → 红；补录后 → 绿）
# ---------------------------------------------------------------------------
async def test_daily_first_writes_audit_row_and_counts_into_base(db_session, test_user, fixed_date):
    engine = AchievementEngine(db_session)

    reward = await engine.check_daily_first(str(test_user.id), db_session)
    await db_session.commit()

    assert reward is not None
    rows = await _tx_rows(db_session, test_user.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.transaction_type == DBTxType.GRANT_DAILY_FIRST  # 专有枚举，非兜底误标
    assert row.amount == DAILY_FIRST_AMOUNT
    assert row.source == "daily_first"
    assert row.related_item_id == f"daily_first:{_FixedDate.current.isoformat()}"
    assert (row.balance_before, row.balance_after) == (0, DAILY_FIRST_AMOUNT)

    balance = await PhotonService(db_session).get_balance(str(test_user.id))
    assert balance == DAILY_FIRST_AMOUNT
    assert await get_redeemable_base(db_session, user_id=str(test_user.id)) == DAILY_FIRST_AMOUNT


# ---------------------------------------------------------------------------
# 2. 红线：连续两日首胜都入流水、基数两天都计（去重键按日区分，绝不吞次日）
# ---------------------------------------------------------------------------
async def test_consecutive_days_first_win_both_ledgered_and_counted(db_session, test_user, fixed_date):
    engine = AchievementEngine(db_session)

    day1 = await engine.check_daily_first(str(test_user.id), db_session)
    await db_session.commit()
    _FixedDate.current = date(2026, 9, 23)
    day2 = await engine.check_daily_first(str(test_user.id), db_session)
    await db_session.commit()

    assert day1 is not None and day2 is not None
    assert day1["date"] != day2["date"]  # 两日均真实发放（次日未被判定为已领）

    rows = [
        r
        for r in await _tx_rows(db_session, test_user.id)
        if r.transaction_type == DBTxType.GRANT_DAILY_FIRST
    ]
    assert len(rows) == 2  # 两日各恰一条流水
    assert {r.related_item_id for r in rows} == {
        "daily_first:2026-09-22",
        "daily_first:2026-09-23",
    }
    assert all(r.amount == DAILY_FIRST_AMOUNT for r in rows)

    balance = await PhotonService(db_session).get_balance(str(test_user.id))
    assert balance == DAILY_FIRST_AMOUNT * 2  # 次日光子未被去重路径吞掉
    assert await get_redeemable_base(db_session, user_id=str(test_user.id)) == DAILY_FIRST_AMOUNT * 2


# ---------------------------------------------------------------------------
# 3. 同日幂等：缓存守门 + DB 去重双保险，同日重复只发一次
# ---------------------------------------------------------------------------
async def test_same_day_repeat_stays_idempotent(db_session, test_user, fixed_date):
    engine = AchievementEngine(db_session)

    first = await engine.check_daily_first(str(test_user.id), db_session)
    await db_session.commit()
    assert first is not None
    second = await engine.check_daily_first(str(test_user.id), db_session)  # 缓存命中 → None
    await db_session.commit()
    assert second is None

    # 缓存失守兜底：同键直打发放面，命中 _find_existing_transaction 去重
    replay = await PhotonService(db_session).grant_photons(
        user_id=str(test_user.id),
        amount=DAILY_FIRST_AMOUNT,
        source="daily_first",
        transaction_type=PhotonTransactionType.GRANT_DAILY_FIRST,
        related_item_id=f"daily_first:{_FixedDate.current.isoformat()}",
        record_history=True,
    )
    await db_session.commit()
    assert replay["deduplicated"] is True

    rows = await _tx_rows(db_session, test_user.id)
    assert len(rows) == 1  # 全天仍只一条流水
    balance = await PhotonService(db_session).get_balance(str(test_user.id))
    assert balance == DAILY_FIRST_AMOUNT


# ---------------------------------------------------------------------------
# 4. combo 加成：入流水 + 专有枚举 + 每事件唯一键（合法重复触发不互吞）
# ---------------------------------------------------------------------------
async def test_combo_bonus_writes_audit_row_with_dedicated_enum(db_session, test_user):
    engine = AchievementEngine(db_session)

    first = await engine._handle_achievement_combo(str(test_user.id), unlock_count=3)
    assert first is not None and first["bonus_photons"] == 30
    await db_session.commit()

    rows = await _tx_rows(db_session, test_user.id)
    assert len(rows) == 1
    row = rows[0]
    assert row.transaction_type == DBTxType.GRANT_BONUS  # 新枚举成员，非 admin_adjustment 兜底
    assert row.amount == 30
    assert row.source == "achievement_combo:3"
    assert row.related_item_id.startswith("achievement_combo:")
    assert (row.balance_before, row.balance_after) == (0, 30)


async def test_combo_bonus_repeated_triggers_never_swallow_each_other(db_session, test_user):
    """连击窗口内第二次达标（combo=3 → combo=6）：键每事件唯一，两次都入流水。"""
    engine = AchievementEngine(db_session)

    await engine._handle_achievement_combo(str(test_user.id), unlock_count=3)  # combo=3 → 30
    await engine._handle_achievement_combo(str(test_user.id), unlock_count=3)  # combo=6 → 60
    await db_session.commit()

    rows = await _tx_rows(db_session, test_user.id)
    assert len(rows) == 2
    assert sorted(r.amount for r in rows) == [30, 60]
    assert len({r.related_item_id for r in rows}) == 2  # 键互不碰撞
    assert await get_redeemable_base(db_session, user_id=str(test_user.id)) == 90


# ---------------------------------------------------------------------------
# 5. 端到端：补录直接转化为可兑换基数（D-COMM-2 词表含两类新收入）
# ---------------------------------------------------------------------------
async def test_redeemable_base_includes_daily_first_and_combo(db_session, test_user, fixed_date, monkeypatch):
    from app.config import settings

    engine = AchievementEngine(db_session)
    await engine.check_daily_first(str(test_user.id), db_session)
    await engine._handle_achievement_combo(str(test_user.id), unlock_count=3)
    await db_session.commit()

    assert await get_redeemable_base(db_session, user_id=str(test_user.id)) == 60

    monkeypatch.setattr(settings, "PHOTON_REDEEM_PRO_COST", 60)
    outcome = await redeem_pro(db_session, user_id=str(test_user.id))
    await db_session.commit()
    assert outcome.status == REDEEM_PRO_OK


# ---------------------------------------------------------------------------
# 6. TOUR 回归钉：去重键必须落得进 related_item_id VARCHAR(50)（PG 真相）。
#    SQLite 不 enforce 列宽——原键 "achievement_combo:"+36 位 uuid4() 共 53 字符
#    在 PG 上每次 combo 发放都 StringDataRightTruncation，毒化事务并连带回滚
#    同批全部光子发放（v3-output/TOUR 活栈实证）。本用例只钉长度真相。
# ---------------------------------------------------------------------------
async def test_combo_related_item_key_fits_varchar50(db_session, test_user, fixed_date):
    from uuid import uuid4

    from app.services.achievement_engine import AchievementEngine

    engine = AchievementEngine(db_session)
    for _ in range(8):
        await engine._handle_achievement_combo(str(test_user.id), unlock_count=3)

    rows = await _tx_rows(db_session, test_user.id)
    assert rows, "combo bonus rows must exist"
    for row in rows:
        # PG 列宽真相：任何字段长度超限都会在 asyncpg 上炸 StringDataRightTruncation
        assert len(row.related_item_id or "") <= 50, row.related_item_id
        assert len(row.source or "") <= 255, row.source
        assert len(row.transaction_type or "") <= 50, row.transaction_type
        assert row.related_item_id.startswith("achievement_combo:")
    # 每事件唯一语义保持：键互不碰撞
    assert len({r.related_item_id for r in rows}) == len(rows)
    probe = f"achievement_combo:{uuid4().hex[:16]}"
    assert len(probe) <= 50
