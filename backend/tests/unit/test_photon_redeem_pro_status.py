"""PHOTON-STATUS · 兑换前状态快照（GET /photons/redeem-pro/status）——红→绿测试面。

任务卡红线逐条：
1. **同源一致性**（红线）：同一用户 ``status.redeemable_base`` == 后续兑换响应
   揭示值——status 复用 ``get_redeemable_base``/``_count_redeems_in_month``
   同一函数，绝无第二套算法；服务端隔离层（service 函数与 HTTP 面分别断言）；
2. **诚实区分**：``redeemable_base`` 与 ``balance`` 并列——transfer_in 场景
   balance > base（转账不可兑），商城消费场景 base > balance（学得未花光）；
3. **月顶状态翻转**：兑换前 ``monthly_cap_used=false`` → 兑换后 ``true`` +
   当月兑换时间 + ``next_window_at`` = 下月 UTC 月初；
4. **常量面**：cost/days/cap 随 settings 回显（【待产品校准】面可调）；
5. **只读承诺**：status 调用零状态变更（余额/流水/权益三不动）；
6. **API 面**：响应契约 + 零光子新用户诚实零值 + 网关同路径形状（catch-all 直透）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_current_user
from app.config import settings
from app.core.time_utils import utcnow
from app.db.session import Base, get_db
from app.models.shop import PhotonTransactionHistory
from app.models.user import User
from app.services import photon_redeem_service
from app.services.photon_redeem_service import (
    get_redeem_status,
    redeem_pro,
)
from app.services.photon_service import PhotonService, PhotonTransactionType

from app.config.settings import settings

# 引用 settings 常量（防再校准改测试惯例，见 PHOTON-CALIBRATION）
COST = settings.PHOTON_REDEEM_PRO_COST
DAYS = 7


# ---------------------------------------------------------------------------
# 基础设施：隔离 sqlite（照 D-COMM-2 测试面同款）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'photon_status_test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


async def _make_user(db: AsyncSession) -> User:
    user = User(
        username=f"u-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        entitlement="free",
        photon_balance=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _grant_ledger(
    db: AsyncSession,
    user: User,
    amount: int,
    tx_type: str = PhotonTransactionType.GRANT_ACHIEVEMENT,
) -> None:
    """生产发放面同款入账（审计流水 + 余额）。"""
    await PhotonService(db).grant_photons(
        user_id=str(user.id),
        amount=amount,
        source=f"test:{tx_type}",
        transaction_type=tx_type,
        record_history=True,
    )


async def _ledger_row_count(db: AsyncSession, user: User) -> int:
    return int(
        (
            await db.execute(
                select(func.count(PhotonTransactionHistory.id)).where(
                    PhotonTransactionHistory.user_id == user.id
                )
            )
        ).scalar_one()
    )


# ---------------------------------------------------------------------------
# 1. 同源一致性（红线）：status.redeemable_base == 后续兑换响应揭示值
# ---------------------------------------------------------------------------
async def test_status_base_equals_redeem_outcome_reveal(db):
    """service 层同源：快照基数与兑换终态揭示的基数同值同源。"""
    user = await _make_user(db)
    await _grant_ledger(db, user, COST + 2200)

    snapshot = await get_redeem_status(db, user_id=str(user.id))
    assert snapshot.redeemable_base == COST + 2200

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == "ok"
    # 红线断言：status 预示值 == 兑换响应揭示值（同一重放函数，绝无第二套算法）
    assert snapshot.redeemable_base == outcome.redeemable_base


async def test_status_base_transfer_income_excluded_same_as_redeem(db):
    """transfer_in 计入余额不计入基数：status 的两数区分与兑换拒绝面同源一致。"""
    alice = await _make_user(db)
    bob = await _make_user(db)
    await _grant_ledger(db, alice, COST)
    await PhotonService(db).transfer_photons(
        from_user_id=str(alice.id), to_user_id=str(bob.id), amount=COST, reason="test"
    )
    await db.commit()

    snapshot = await get_redeem_status(db, user_id=str(bob.id))
    assert snapshot.balance == COST  # 混桶余额含转账
    assert snapshot.redeemable_base == 0  # 重放口径排除 transfer_in
    assert snapshot.can_redeem is False

    outcome = await redeem_pro(db, user_id=str(bob.id))
    assert outcome.status == "insufficient_base"  # 兑换路径同判：基数不足


async def test_api_status_base_equals_redeem_response_reveal(db_engine, api_harness):
    """HTTP 面同源：GET status 的基数 == 随后 POST redeem 响应揭示的基数。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        await _grant_ledger(setup, user, 5200)

    client = await api_harness(user)

    status_payload = client.get("/photons/redeem-pro/status").json()["data"]
    assert status_payload["redeemable_base"] == 5200

    redeem_payload = client.post("/photons/redeem-pro").json()
    assert redeem_payload["status"] == "ok"
    assert redeem_payload["data"]["redeemable_base"] == status_payload["redeemable_base"]
    # 余额同源：兑换响应 balance_after == status 快照 balance − cost
    assert (
        redeem_payload["data"]["balance_after"]
        == status_payload["balance"] - status_payload["cost_photons"]
    )


# ---------------------------------------------------------------------------
# 2. 诚实区分：base 与 balance 并列（两方向缝隙都照实呈现）
# ---------------------------------------------------------------------------
async def test_status_base_above_balance_after_shop_spend(db):
    """学得未花光：基数 > 余额（商城消费减余额不减基数）。"""
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)
    await PhotonService(db).deduct_photons(
        user_id=str(user.id),
        amount=500,
        reason="shop:purchase",
        transaction_type="purchase",
        record_history=True,
    )
    await db.commit()

    snapshot = await get_redeem_status(db, user_id=str(user.id))
    assert snapshot.redeemable_base == COST
    assert snapshot.balance == COST - 500
    assert snapshot.redeemable_base > snapshot.balance  # 诚实区分：两数不同


# ---------------------------------------------------------------------------
# 3. 月顶状态翻转 + 月窗边界
# ---------------------------------------------------------------------------
async def test_monthly_cap_flips_after_redeem_with_timestamp_and_next_window(db):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)

    before = await get_redeem_status(db, user_id=str(user.id))
    assert before.monthly_cap_used is False
    assert before.redeems_this_month == 0
    assert before.monthly_cap_redeemed_at is None
    assert before.can_redeem is True

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == "ok"

    after = await get_redeem_status(db, user_id=str(user.id))
    assert after.monthly_cap_used is True  # 状态翻转
    assert after.redeems_this_month == 1
    assert after.monthly_cap_redeemed_at is not None
    assert after.monthly_cap_redeemed_at >= photon_redeem_service._month_start(utcnow())
    assert after.can_redeem is False
    # 时间戳即当月本通道流水时间（同真源交叉验证）
    redeem_row = (
        await db.execute(
            select(PhotonTransactionHistory.created_at).where(
                PhotonTransactionHistory.user_id == user.id,
                PhotonTransactionHistory.transaction_type == "redeem_pro",
            )
        )
    ).scalar_one()
    assert after.monthly_cap_redeemed_at == redeem_row


async def test_next_window_at_is_first_day_of_next_utc_month(db):
    user = await _make_user(db)
    snapshot = await get_redeem_status(db, user_id=str(user.id))

    now = utcnow()
    expected = photon_redeem_service._next_month_start(now)
    assert snapshot.next_window_at == expected
    assert snapshot.next_window_at > now
    # 边界形状：月初 0 点（naive UTC）
    assert snapshot.next_window_at.day == 1
    assert snapshot.next_window_at.hour == 0
    # 与当月窗衔接：next_window_at 恰在当月流水窗（>= month_start）之外的下月
    assert snapshot.next_window_at.month != now.month or snapshot.next_window_at.year > now.year


async def test_last_month_redeem_does_not_flip_current_cap_status(db):
    """上月流水不翻转当月状态（月窗只看当月，与兑换路径同判）。"""
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)
    last_month = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    db.add(
        PhotonTransactionHistory(
            id=str(uuid4()),
            user_id=user.id,
            transaction_type="redeem_pro",
            amount=-COST,
            balance_before=COST,
            balance_after=0,
            source="photon_redeem_pro",
            created_at=last_month,
        )
    )
    await db.commit()

    snapshot = await get_redeem_status(db, user_id=str(user.id))
    assert snapshot.monthly_cap_used is False
    assert snapshot.monthly_cap_redeemed_at is None  # 上月时间不冒充当月
    assert snapshot.can_redeem is True


# ---------------------------------------------------------------------------
# 4. 常量面 + 只读承诺 + 零光子诚实零值
# ---------------------------------------------------------------------------
async def test_status_echoes_settings_constants(db, monkeypatch):
    monkeypatch.setattr(settings, "PHOTON_REDEEM_PRO_COST", 4500)
    monkeypatch.setattr(settings, "PHOTON_REDEEM_PRO_DAYS", 5)
    monkeypatch.setattr(settings, "PHOTON_REDEEM_PRO_MONTHLY_CAP", 2)

    user = await _make_user(db)
    snapshot = await get_redeem_status(db, user_id=str(user.id))
    assert snapshot.cost_photons == 4500
    assert snapshot.pro_days == 5
    assert snapshot.monthly_cap == 2


async def test_status_is_read_only_zero_state_change(db):
    """只读承诺：status 前后余额/流水数/权益三不动。"""
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)
    await db.commit()

    rows_before = await _ledger_row_count(db, user)
    balance_before = user.photon_balance
    entitlement_before = user.entitlement

    await get_redeem_status(db, user_id=str(user.id))
    await db.commit()

    await db.refresh(user)
    assert user.photon_balance == balance_before
    assert user.entitlement == entitlement_before
    assert await _ledger_row_count(db, user) == rows_before


async def test_zero_photon_new_user_honest_zeros(db):
    user = await _make_user(db)
    snapshot = await get_redeem_status(db, user_id=str(user.id))
    assert snapshot.redeemable_base == 0
    assert snapshot.balance == 0
    assert snapshot.monthly_cap_used is False
    assert snapshot.can_redeem is False  # 不送任何许可（宁降不升 fail-safe 同向）


# ---------------------------------------------------------------------------
# 5. API 面：响应契约 + 月顶经 API 翻转
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def api_harness(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _build(current_user: User) -> TestClient:
        from app.api.v1.photons import router as photons_router

        app = FastAPI()
        app.include_router(photons_router, prefix="/photons")

        async def _override_db():
            async with maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = lambda: current_user
        return TestClient(app)

    return _build


async def test_api_status_contract_and_cap_flip(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        await _grant_ledger(setup, user, COST)

    client = await api_harness(user)

    resp = client.get("/photons/redeem-pro/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # 契约键全量（PHOTON-STATUS 卡响应面）
    assert set(data) == {
        "user_id",
        "redeemable_base",
        "balance",
        "cost_photons",
        "pro_days",
        "monthly_cap",
        "redeems_this_month",
        "monthly_cap_used",
        "monthly_cap_redeemed_at",
        "next_window_at",
        "can_redeem",
    }
    assert data["redeemable_base"] == COST
    assert data["balance"] == COST
    assert data["cost_photons"] == COST
    assert data["pro_days"] == DAYS
    assert data["monthly_cap"] == 1
    assert data["monthly_cap_used"] is False
    assert data["monthly_cap_redeemed_at"] is None
    assert data["can_redeem"] is True
    datetime.fromisoformat(data["next_window_at"])  # 可解析时间戳

    # 月顶经 API 翻转：兑换后 status 如实呈现 used + 时间
    assert client.post("/photons/redeem-pro").status_code == 200
    after = client.get("/photons/redeem-pro/status").json()["data"]
    assert after["monthly_cap_used"] is True
    assert after["redeems_this_month"] == 1
    assert after["monthly_cap_redeemed_at"] is not None
    datetime.fromisoformat(after["monthly_cap_redeemed_at"])
    assert after["can_redeem"] is False
    assert after["balance"] == 0  # 兑换后真值刷新


async def test_api_status_new_user_honest_zero_contract(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)

    client = await api_harness(user)
    data = client.get("/photons/redeem-pro/status").json()["data"]
    assert data["redeemable_base"] == 0
    assert data["balance"] == 0
    assert data["monthly_cap_used"] is False
    assert data["can_redeem"] is False
