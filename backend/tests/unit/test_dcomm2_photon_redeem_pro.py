"""D-COMM-2 · 光子→Pro 7 天有界兑换（「学出会员」）——红→绿测试面。

覆盖（任务卡红线逐条）：
1. 正常兑换：光子减 / entitlement='pro' + expires_at 落 / 专有 redeem_pro 流水双写；
2. transfer_in 不计入可兑换基数（转账后兑换拒绝——封小号互转刷会员）；
3. 余额不足拒（基数够但混桶余额不够）；
4. 月顶：同月二次拒（状态收敛=幂等），上月流水不影响当月额度；
5. 并发双请求：N 并发同用户恰一次成功（模式同 D-REDEEM §0 条件 UPDATE 族）；
6. entitlement 叠加语义：有效期顺延 / 永久 pro 绝不降级；
7. 免费闭环抽查：零光子新用户核心查询面零变化、兑换失败不碰余额。
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.time_utils import utcnow
from app.db.session import Base, get_db
from app.api.deps import get_current_user
from app.models.shop import PhotonTransactionHistory, PhotonTransactionType as DBTxType
from app.models.user import User
from app.services import photon_redeem_service
from app.services.photon_redeem_service import (
    REDEEM_PRO_INSUFFICIENT_BALANCE,
    REDEEM_PRO_INSUFFICIENT_BASE,
    REDEEM_PRO_MONTHLY_CAP,
    REDEEM_PRO_OK,
    get_redeemable_base,
    redeem_pro,
)
from app.services.photon_service import PhotonService, PhotonTransactionType

# 校准防再改：COST 读 settings 部署值（2026-09-22 校准 3000→1500），
# 下次校准只改 settings，本测试族零改动。
COST = settings.PHOTON_REDEEM_PRO_COST
DAYS = 7


# ---------------------------------------------------------------------------
# 基础设施：隔离 sqlite（文件库支持并发面；会话面照 D-REDEEM 同款）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'dcomm2_test.db'}",
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


async def _make_user(db: AsyncSession, *, entitlement: str = "free", expires_at=None) -> User:
    user = User(
        username=f"u-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        entitlement=entitlement,
        entitlement_expires_at=expires_at,
        photon_balance=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _user_state(db: AsyncSession, user: User) -> tuple[int, str, object]:
    """列选择直读（绕开 ORM 身份图缓存；core UPDATE 不经实例同步）。"""
    row = (
        await db.execute(
            select(User.photon_balance, User.entitlement, User.entitlement_expires_at).where(
                User.id == user.id
            )
        )
    ).one()
    return int(row[0]), str(row[1]), row[2]


async def _grant_ledger(
    db: AsyncSession,
    user: User,
    amount: int,
    tx_type: str = PhotonTransactionType.GRANT_ACHIEVEMENT,
) -> None:
    """按生产发放面同款入账（record_history=True → 审计流水 + 余额）。"""
    await PhotonService(db).grant_photons(
        user_id=str(user.id),
        amount=amount,
        source=f"test:{tx_type}",
        transaction_type=tx_type,
        record_history=True,
    )


async def _drain_balance(db: AsyncSession, user: User, amount: int) -> None:
    """把混桶余额抽干但不减基数（商城购买不在可兑换支出词表内）。"""
    await PhotonService(db).deduct_photons(
        user_id=str(user.id),
        amount=amount,
        reason="shop:purchase",
        transaction_type="purchase",
        record_history=True,
    )


# ---------------------------------------------------------------------------
# 1. 正常兑换：扣减 / 授予 / 双写流水 / 专有类型不落 admin_adjustment 兜底
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_redeem_pro_success_deducts_and_grants_pro(db):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()

    assert outcome.status == REDEEM_PRO_OK
    assert outcome.cost_photons == COST
    assert outcome.pro_days == DAYS
    assert outcome.balance_after == 0
    assert outcome.entitlement_expires_at is not None
    assert abs((outcome.entitlement_expires_at - (utcnow() + timedelta(days=DAYS))).total_seconds()) < 60

    balance, entitlement, _ = await _user_state(db, user)
    assert (balance, entitlement) == (0, "pro")

    tx_rows = (
        await db.execute(
            select(PhotonTransactionHistory).where(PhotonTransactionHistory.user_id == user.id)
        )
    ).scalars().all()
    redeem_rows = [t for t in tx_rows if t.transaction_type == "redeem_pro"]
    assert len(redeem_rows) == 1  # 双写流水恰一条
    assert redeem_rows[0].amount == -COST
    assert redeem_rows[0].balance_after == 0
    assert DBTxType("redeem_pro") == DBTxType.REDEEM_PRO  # 专有枚举成员，非兜底误标


@pytest.mark.asyncio
async def test_base_is_net_of_contract_failure_stake(db, monkeypatch):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST, tx_type=PhotonTransactionType.GRANT_CONTRACT)
    await PhotonService(db).deduct_photons(
        user_id=str(user.id),
        amount=500,
        reason="contract:failed",
        transaction_type=PhotonTransactionType.DEDUCT_CONTRACT,
        record_history=True,
    )
    assert await get_redeemable_base(db, user_id=str(user.id)) == COST - 500

    # 校准无关：兑换价设为当前净值（COST-500），验证「基数扣减失败押金后恰可兑」
    monkeypatch.setattr(settings, "PHOTON_REDEEM_PRO_COST", COST - 500)
    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == REDEEM_PRO_OK


# ---------------------------------------------------------------------------
# 2. transfer_in 不计入基数（红线：封小号互转刷会员）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_transfer_in_excluded_from_redeemable_base(db):
    alice = await _make_user(db)
    bob = await _make_user(db)
    await _grant_ledger(db, alice, COST)

    await PhotonService(db).transfer_photons(
        from_user_id=str(alice.id), to_user_id=str(bob.id), amount=COST, reason="test"
    )
    await db.commit()

    # bob 混桶余额够，但 transfer_in 不在收入词表 → 基数 0 → 拒
    bob_balance = (
        (await db.execute(select(User.photon_balance).where(User.id == bob.id)))
        .scalar_one()
    )
    assert bob_balance == COST
    assert await get_redeemable_base(db, user_id=str(bob.id)) == 0

    outcome = await redeem_pro(db, user_id=str(bob.id))
    assert outcome.status == REDEEM_PRO_INSUFFICIENT_BASE  # 拒绝路径无任何写入

    # 转出方 alice：基数留存（设计口径 transfer_out 不返还基数）但余额已转空
    assert await get_redeemable_base(db, user_id=str(alice.id)) == COST
    outcome_alice = await redeem_pro(db, user_id=str(alice.id))
    assert outcome_alice.status == REDEEM_PRO_INSUFFICIENT_BALANCE


@pytest.mark.asyncio
async def test_balance_shortfall_rejected_even_with_base(db):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)
    await _drain_balance(db, user, COST)  # 商城花掉：余额 0、基数仍 COST

    outcome = await redeem_pro(db, user_id=str(user.id))
    assert outcome.status == REDEEM_PRO_INSUFFICIENT_BALANCE
    balance, _, _ = await _user_state(db, user)
    assert balance == 0  # 拒绝零副作用


# ---------------------------------------------------------------------------
# 3. 月顶与幂等（重复请求同结果、状态收敛）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_monthly_cap_blocks_second_redeem_and_converges(db):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST * 2)

    first = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert first.status == REDEEM_PRO_OK
    snapshot = await _user_state(db, user)

    second = await redeem_pro(db, user_id=str(user.id))
    third = await redeem_pro(db, user_id=str(user.id))
    assert second.status == REDEEM_PRO_MONTHLY_CAP
    assert third.status == REDEEM_PRO_MONTHLY_CAP  # 重复请求同结果

    assert await _user_state(db, user) == snapshot  # 状态收敛不双扣


@pytest.mark.asyncio
async def test_last_month_redemption_does_not_count_into_current_month(db):
    user = await _make_user(db)
    await _grant_ledger(db, user, COST)

    # 直接落一条上月兑换流水（免 freezegun：月顶窗口只看当月）
    last_month = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
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
    await _grant_ledger(db, user, COST)  # 补回余额（上月扣过）
    await db.commit()

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == REDEEM_PRO_OK


# ---------------------------------------------------------------------------
# 4. 并发红线：N 并发同用户恰一次成功（模式同 D-REDEEM §0）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_redeem_exactly_one_success(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        await PhotonService(setup).grant_photons(
            user_id=str(user.id),
            amount=COST * 8,
            source="test:bulk",
            transaction_type=PhotonTransactionType.GRANT_CONTRACT,
            record_history=True,
        )

    async def attempt() -> str:
        async with maker() as session:
            outcome = await redeem_pro(session, user_id=str(user.id))
            if outcome.status == REDEEM_PRO_OK:
                await session.commit()
            return outcome.status

    statuses = await asyncio.gather(*(attempt() for _ in range(8)))

    assert statuses.count(REDEEM_PRO_OK) == 1
    assert statuses.count(REDEEM_PRO_MONTHLY_CAP) == 7

    async with maker() as verify:
        row = (await verify.execute(select(User).where(User.id == user.id))).scalar_one()
        assert row.photon_balance == COST * 8 - COST  # 恰扣一次
        assert row.entitlement == "pro"
        assert abs(
            (row.entitlement_expires_at - (utcnow() + timedelta(days=DAYS))).total_seconds()
        ) < 60  # 只授予一次，未叠加双倍

        redeem_rows = (
            await verify.execute(
                select(PhotonTransactionHistory).where(
                    PhotonTransactionHistory.transaction_type == "redeem_pro"
                )
            )
        ).scalars().all()
        assert len(redeem_rows) == 1


# ---------------------------------------------------------------------------
# 5. entitlement 叠加语义（复用 D-REDEEM 核销核的继承面）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_redeem_stacks_on_active_pro_expiry(db):
    future = utcnow() + timedelta(days=3)
    user = await _make_user(db, entitlement="pro", expires_at=future)
    await _grant_ledger(db, user, COST)

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == REDEEM_PRO_OK
    assert abs((outcome.entitlement_expires_at - (future + timedelta(days=DAYS))).total_seconds()) < 60


@pytest.mark.asyncio
async def test_redeem_never_downgrades_permanent_pro(db):
    user = await _make_user(db, entitlement="pro", expires_at=None)
    await _grant_ledger(db, user, COST)

    outcome = await redeem_pro(db, user_id=str(user.id))
    await db.commit()
    assert outcome.status == REDEEM_PRO_OK
    assert outcome.entitlement_expires_at is None  # 永久 pro 保持 NULL
    balance, _, expires_at = await _user_state(db, user)
    assert expires_at is None
    assert balance == 0  # 光子仍照扣（权益未降级 ≠ 免费）


# ---------------------------------------------------------------------------
# 6. API 面：路由挂载 + 终态映射 + 免费闭环抽查（零光子新用户零阻断）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def api_harness(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _build(current_user: User) -> TestClient:
        from app.api.v1.photons import router as photons_router

        app = FastAPI()
        app.include_router(photons_router, prefix="/photons")

        async def _override_db():
            # 与生产 get_db 同事务语义：成功提交、异常回滚
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


@pytest.mark.asyncio
async def test_api_redeem_pro_status_mapping(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        await PhotonService(setup).grant_photons(
            user_id=str(user.id),
            amount=COST,
            source="test:api",
            transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
            record_history=True,
        )

    client = await api_harness(user)

    ok = client.post("/photons/redeem-pro")
    assert ok.status_code == 200, ok.text
    payload = ok.json()
    assert payload["status"] == "ok"
    assert payload["data"]["cost_photons"] == COST
    assert payload["data"]["pro_days"] == DAYS
    assert payload["data"]["entitlement"] == "pro"
    assert payload["data"]["entitlement_expires_at"] is not None

    capped = client.post("/photons/redeem-pro")  # 幂等：同月重复请求同结果
    assert capped.status_code == 409
    assert capped.json()["detail"]["status"] == REDEEM_PRO_MONTHLY_CAP


@pytest.mark.asyncio
async def test_api_zero_photon_new_user_free_loop_unchanged(db_engine, api_harness):
    """免费闭环抽查：零光子新用户核心面零变化，兑换失败不碰余额。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)

    client = await api_harness(user)

    balance = client.get("/photons/balance")
    assert balance.status_code == 200
    assert balance.json()["data"]["balance"] == 0

    history = client.get("/photons/transactions")
    assert history.status_code == 200
    assert history.json()["data"] == []

    denied = client.post("/photons/redeem-pro")
    assert denied.status_code == 409
    assert denied.json()["detail"]["status"] == REDEEM_PRO_INSUFFICIENT_BASE

    after = client.get("/photons/balance")
    assert after.json()["data"]["balance"] == 0
    async with maker() as verify:
        row = (await verify.execute(select(User).where(User.id == user.id))).scalar_one()
        assert row.entitlement == "free"  # 未被送任何权益（宁降不升 fail-safe 同向）
