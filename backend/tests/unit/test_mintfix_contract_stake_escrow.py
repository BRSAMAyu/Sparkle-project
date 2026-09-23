"""MINT-FIX · 契约押金托管闭环——钉死铸币洞（D-MONETIZE 审计 §1.5-R1）

铸币洞三连（任务卡验收面逐条）：
1. 余额 0 创建契约 → 服务层 ValueError（API 面映射 400），零契约零流水零副作用；
2. 完成净得 = stake（托管已预扣，完成发 stake×multiplier 含还本），
   非「无本双倍」——生命周期余额增量与流水重放双面断言；
3. 失败从托管扣（没收创建时已预扣的本金），余额不再变动，
   彻底消灭「余额不足静默豁免」。

配套验收面：
- ``contract_escrow`` 托管流水类型出可兑换审计重放基数（transfer_in 排除先例同型断言）；
- 存量在途契约（托管上线前创建、无 escrow 流水）结算走旧路径，升级瞬间行为不突变；
- 取消路径（DELETE /contracts）在托管语义下 ``photons_lost`` 首次为真；
- 上限钳制（settings.PHOTON_CONTRACT_STAKE_MAX）拒绝超额 stake。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_current_user
from app.config import settings
from app.db.session import Base, get_db
from app.models.achievement import ContractStatus, SparkContract
from app.models.shop import PhotonTransactionHistory
from app.models.user import User
from app.services.achievement_engine import ContractService
from app.services.photon_redeem_service import (
    REDEEMABLE_DEDUCT_TYPES,
    REDEEMABLE_INCOME_TYPES,
    get_redeemable_base,
)
from app.services.photon_service import PhotonService, PhotonTransactionType

STAKE_MAX = settings.PHOTON_CONTRACT_STAKE_MAX


# ---------------------------------------------------------------------------
# 基础设施：隔离 sqlite 文件库 + API 挂载（照 D-COMM-2 同款）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'mintfix_test.db'}",
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


async def _make_user(db: AsyncSession, *, balance: int = 0) -> User:
    user = User(
        username=f"u-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        photon_balance=balance,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _balance(db: AsyncSession, user_id: str) -> int:
    """列选择直读（绕开 ORM 身份图缓存；core UPDATE 不经实例同步，D-COMM-2 同款）。"""
    return int((await db.execute(select(User.photon_balance).where(User.id == user_id))).scalar_one())


async def _rows(db: AsyncSession, user_id: str) -> list[PhotonTransactionHistory]:
    rows = (
        (
            await db.execute(
                select(PhotonTransactionHistory)
                .where(PhotonTransactionHistory.user_id == user_id)
                .order_by(PhotonTransactionHistory.created_at)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def _grant_ledger(db: AsyncSession, user_id: str, amount: int) -> None:
    """按生产发放面同款入账（record_history=True → 审计流水 + 余额）。"""
    await PhotonService(db).grant_photons(
        user_id=user_id,
        amount=amount,
        source="test:seed",
        transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
        record_history=True,
    )


def _settle_window_over(contract: SparkContract, *, complete: bool) -> None:
    """把契约推进到结算窗口：complete=True 达标、False 违约。"""
    contract.end_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    if complete:
        contract.current_days = contract.target_days
        contract.current_minutes = contract.target_study_minutes


# ---------------------------------------------------------------------------
# 1. 创建即托管预扣（原子：契约与 escrow 流水同生同灭）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_contract_escrows_stake(db):
    user = await _make_user(db, balance=200)

    contract = await ContractService(db).create_contract(str(user.id), study_minutes=30, days=7, photon_stake=100)
    await db.commit()

    assert contract.status == ContractStatus.ACTIVE
    assert await _balance(db, str(user.id)) == 100  # 创建即真实预扣

    rows = await _rows(db, str(user.id))
    escrow_rows = [r for r in rows if r.transaction_type == PhotonTransactionType.CONTRACT_ESCROW]
    assert len(escrow_rows) == 1
    row = escrow_rows[0]
    assert row.amount == -100
    assert row.balance_before == 200
    assert row.balance_after == 100
    assert row.related_item_id == str(contract.id)  # 流水对账键：托管挂契约 id


@pytest.mark.asyncio
async def test_create_contract_insufficient_balance_rejected(db):
    """铸币洞第一钉：余额 0 立约 → 拒绝（服务层 ValueError，API 面映射 400）。"""
    user = await _make_user(db, balance=0)
    uid = str(user.id)  # rollback 会过期实例，先取纯值
    service = ContractService(db)

    with pytest.raises(ValueError, match="Insufficient photon balance to stake"):
        await service.create_contract(uid, study_minutes=30, days=7, photon_stake=100)
    await db.rollback()

    # 零副作用：无契约、无流水、余额不动
    contracts = (await db.execute(select(SparkContract).where(SparkContract.user_id == uid))).scalars().all()
    assert contracts == []
    assert await _rows(db, uid) == []
    assert await _balance(db, uid) == 0


@pytest.mark.asyncio
async def test_create_contract_over_cap_rejected(db):
    """上限钳制：stake > settings.PHOTON_CONTRACT_STAKE_MAX → 拒绝。"""
    user = await _make_user(db, balance=10**6)
    uid = str(user.id)
    service = ContractService(db)

    with pytest.raises(ValueError, match="exceeds the maximum allowed"):
        await service.create_contract(uid, study_minutes=30, days=7, photon_stake=STAKE_MAX + 1)
    await db.rollback()

    contracts = (await db.execute(select(SparkContract).where(SparkContract.user_id == uid))).scalars().all()
    assert contracts == []
    assert await _rows(db, uid) == []

    # 边界内（== 上限）且余额充足 → 正常托管
    contract = await service.create_contract(uid, study_minutes=30, days=7, photon_stake=STAKE_MAX)
    assert contract.photon_stake == STAKE_MAX
    assert await _balance(db, uid) == 10**6 - STAKE_MAX


# ---------------------------------------------------------------------------
# 2. 完成：发还本 + 奖励（净得 stake），非无本双倍
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_completed_contract_nets_stake_not_free_double(db):
    """铸币洞第二钉：完成发 stake×2.0（1 份还本），生命周期净得 = stake。"""
    user = await _make_user(db, balance=200)
    service = ContractService(db)
    service._trigger_contract_achievement = AsyncMock()  # 隔离成就域光子
    contract = await service.create_contract(str(user.id), study_minutes=30, days=7, photon_stake=100)
    await db.commit()

    await _settle_window_over_and_refresh(db, contract, complete=True)
    result = await service.check_contract_status(str(user.id))
    await db.commit()

    assert result["status"] == "completed"
    assert result["reward"] == 200  # 完成发放面与既有语义一致（stake × multiplier）

    balance = await _balance(db, str(user.id))
    assert balance == 300  # 200 − 100(托管) + 200(还本+奖励)
    lifecycle_net = balance - 200
    assert lifecycle_net == 100  # 净得 = stake，而非旧洞的 +200 无本双倍

    rows = await _rows(db, str(user.id))
    grants = [r for r in rows if r.transaction_type == PhotonTransactionType.GRANT_CONTRACT]
    assert len(grants) == 1
    assert grants[0].amount == 200
    assert grants[0].related_item_id == str(contract.id)


async def _settle_window_over_and_refresh(db: AsyncSession, contract: SparkContract, *, complete: bool) -> None:
    _settle_window_over(contract, complete=complete)
    await db.commit()
    await db.refresh(contract)


# ---------------------------------------------------------------------------
# 3. 失败：没收托管本金，余额不再变动（不再静默豁免）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_contract_forfeits_escrow_balance_untouched(db):
    """铸币洞第三钉：失败从托管扣（托管已在创建时真实预扣），余额不动。"""
    user = await _make_user(db, balance=200)
    service = ContractService(db)
    service._trigger_contract_achievement = AsyncMock()
    contract = await service.create_contract(str(user.id), study_minutes=30, days=7, photon_stake=100)
    await db.commit()
    escrowed_balance = await _balance(db, str(user.id))
    assert escrowed_balance == 100

    await _settle_window_over_and_refresh(db, contract, complete=False)
    result = await service.check_contract_status(str(user.id))
    await db.commit()

    assert result["status"] == "failed"
    assert result["lost"] == 100
    assert await _balance(db, str(user.id)) == 100  # 失败零余额变动（本金已在创建时扣）

    rows = await _rows(db, str(user.id))
    deducts = [r for r in rows if r.transaction_type == PhotonTransactionType.DEDUCT_CONTRACT]
    assert deducts == []  # 无二次扣款流水——没收发生在托管预扣那一刻


def _legacy_contract(user: User, *, stake: int, complete: bool) -> SparkContract:
    """托管上线前的在途契约形态：ACTIVE、无任何 escrow 流水。"""
    now = datetime.now(UTC).replace(tzinfo=None)
    return SparkContract(
        user_id=user.id,
        target_study_minutes=30,
        target_days=7,
        photon_stake=stake,
        start_date=now - timedelta(days=8),
        end_date=now - timedelta(days=1),  # 已过期 → check 即结算
        status=ContractStatus.ACTIVE,
        current_days=7 if complete else 3,
        current_minutes=210 if complete else 90,
    )


@pytest.mark.asyncio
async def test_legacy_inflight_contract_without_escrow_keeps_old_settlement(db):
    """存量兼容：托管上线前的在途契约（无 escrow 流水）结算走旧路径不突变。

    - 失败：照旧实扣余额 + deduct 流水（旧「静默豁免」只在余额不足时发生，
      属存量事实，不追缴不放大）；
    - 完成：照旧发 stake × multiplier（无本双倍对其已是历史事实，不追缴）。
    """
    user = await _make_user(db, balance=200)

    # —— 失败结算（旧路径）：实扣 50 ——
    failed = _legacy_contract(user, stake=50, complete=False)
    db.add(failed)
    await db.commit()

    service = ContractService(db)
    service._trigger_contract_achievement = AsyncMock()
    result = await service.check_contract_status(str(user.id))
    await db.commit()
    assert result == {"status": "failed", "lost": 50}
    assert await _balance(db, str(user.id)) == 150
    rows = await _rows(db, str(user.id))
    deducts = [r for r in rows if r.transaction_type == PhotonTransactionType.DEDUCT_CONTRACT]
    assert len(deducts) == 1 and deducts[0].amount == -50

    # —— 完成结算（旧路径）：发 2×stake ——
    completed = _legacy_contract(user, stake=40, complete=True)
    db.add(completed)
    await db.commit()

    service2 = ContractService(db)
    service2._trigger_contract_achievement = AsyncMock()
    result = await service2.check_contract_status(str(user.id))
    await db.commit()
    assert result == {"status": "completed", "reward": 80}
    assert await _balance(db, str(user.id)) == 230  # 150 + 80（历史行为原样，无还本语义）


# ---------------------------------------------------------------------------
# 4. 托管流水出可兑换审计基数（transfer_in 排除先例同型）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_escrow_ledger_excluded_from_redeemable_base(db):
    user = await _make_user(db, balance=0)
    await _grant_ledger(db, str(user.id), 500)
    assert await get_redeemable_base(db, user_id=str(user.id)) == 500

    service = ContractService(db)
    service._trigger_contract_achievement = AsyncMock()
    contract = await service.create_contract(str(user.id), study_minutes=30, days=7, photon_stake=100)
    await db.commit()

    # escrow −100 不进基数：自有本金进出 ≠「学出」收入
    assert await get_redeemable_base(db, user_id=str(user.id)) == 500

    await _settle_window_over_and_refresh(db, contract, complete=True)
    await service.check_contract_status(str(user.id))
    await db.commit()

    # 完成发放 grant_contract +200 进基数（与既有收入词表一致）
    assert await get_redeemable_base(db, user_id=str(user.id)) == 700


@pytest.mark.asyncio
async def test_escrow_type_not_in_redeem_word_lists(db):
    """词表级钉死：contract_escrow 不得出现在收入/支出两个词表（防未来误并入）。"""
    assert PhotonTransactionType.CONTRACT_ESCROW not in REDEEMABLE_INCOME_TYPES
    assert PhotonTransactionType.CONTRACT_ESCROW not in REDEEMABLE_DEDUCT_TYPES
    assert PhotonTransactionType.GUEST_SEED not in REDEEMABLE_INCOME_TYPES
    assert PhotonTransactionType.GUEST_SEED not in REDEEMABLE_DEDUCT_TYPES


# ---------------------------------------------------------------------------
# 5. API 面：4xx 明确错误 + 取消路径 photons_lost 首次为真
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def api_harness(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _build(current_user: User) -> TestClient:
        from app.api.v1.achievements import router as achievements_router

        app = FastAPI()
        app.include_router(achievements_router, prefix="/achievements")

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


def _contract_payload(stake: int) -> dict:
    return {"target_study_minutes": 30, "target_days": 7, "photon_stake": stake}


@pytest.mark.asyncio
async def test_api_zero_balance_create_contract_returns_400(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
    client = await api_harness(user)

    resp = client.post(
        "/achievements/contracts",
        json=_contract_payload(100),
        headers={"Idempotency-Key": "mintfix-1"},
    )
    assert resp.status_code == 400
    assert "Insufficient photon balance" in resp.json()["detail"]

    over_cap = client.post(
        "/achievements/contracts",
        json=_contract_payload(STAKE_MAX + 1),
        headers={"Idempotency-Key": "mintfix-2"},
    )
    assert over_cap.status_code == 400
    assert "maximum allowed" in over_cap.json()["detail"]


@pytest.mark.asyncio
async def test_api_create_contract_escrows_and_reports_balance(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup, balance=500)
    client = await api_harness(user)

    ok = client.post(
        "/achievements/contracts",
        json=_contract_payload(100),
        headers={"Idempotency-Key": "mintfix-3"},
    )
    assert ok.status_code == 200, ok.text
    payload = ok.json()
    assert payload["success"] is True
    assert payload["data"]["photon_stake"] == 100

    async with maker() as verify:
        refreshed = await verify.get(User, user.id)
        assert refreshed.photon_balance == 400  # 托管预扣可见


@pytest.mark.asyncio
async def test_api_cancel_contract_forfeits_escrow_without_touching_balance(db_engine, api_harness):
    """取消路径：托管语义下「photons_lost」首次名副其实，且不再碰余额。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup, balance=500)
    client = await api_harness(user)

    created = client.post(
        "/achievements/contracts",
        json=_contract_payload(100),
        headers={"Idempotency-Key": "mintfix-4"},
    )
    assert created.status_code == 200

    cancelled = client.delete("/achievements/contracts", headers={"Idempotency-Key": "mintfix-5"})
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["success"] is True
    assert body["photons_lost"] == 100  # 取消=没收托管本金（此前该字段名不副实：从不实扣）

    async with maker() as verify:
        refreshed = await verify.get(User, user.id)
        assert refreshed.photon_balance == 400  # 500 − 100(托管)，取消零余额变动
        rows = (
            (await verify.execute(select(PhotonTransactionHistory).where(PhotonTransactionHistory.user_id == user.id)))
            .scalars()
            .all()
        )
        assert [r.transaction_type for r in rows] == [
            PhotonTransactionType.CONTRACT_ESCROW
        ]  # 恰一条托管流水，无 deduct 补扣
