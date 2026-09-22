"""D-REDEEM · 兑换码付费闭环（参赛演示级）——红→绿测试面。

覆盖：
1. 判级扩展（core/entitlement.entitlement_effective）：到期降级、NULL=永久、
   未知值宁降不升（存量语义零破坏回归）。
2. rd01_20260922 迁移 sqlite 隔离基座重放 + 可逆（主库只读纪律）。
3. 生成面：格式/唯一性/明文不落库。
4. 核销面：成功升级（带到期）、并发同码恰一次（防双花）、过期、上限、
   叠加顺延、永久 pro 保护。
5. 红线：明文不进日志；budget 派生随到期降级（fail-safe 同向）。
6. API 面：user 核销路由 + admin 生成路由的鉴权挂载与业务状态映射。
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.budget_matrix import derive_default_run_budget_if_enabled
from app.core.entitlement import (
    ENTITLEMENT_PRO,
    entitlement_effective,
    entitlement_effective_grants_pro,
)
from app.core.time_utils import utcnow
from app.db.session import Base
from app.models.redeem_code import RedeemCode
from app.models.user import User
from app.services import redeem_service
from app.services.redeem_service import (
    REDEEM_EXHAUSTED,
    REDEEM_EXPIRED,
    REDEEM_INVALID,
    REDEEM_OK,
    generate_redeem_code,
    hash_redeem_code,
    normalize_redeem_code,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "rd01_20260922_redeem_codes.py"

# ---------------------------------------------------------------------------
# 基础设施：隔离 sqlite（文件库支持并发面；内存库支持单会话面）
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'rd_test.db'}",
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
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_batch(db: AsyncSession, *, count: int = 1, max_uses: int = 1, **kwargs) -> list[str]:
    batch = await redeem_service.generate_batch(db, count=count, max_uses=max_uses, **kwargs)
    await db.commit()
    return batch.codes


# ---------------------------------------------------------------------------
# 1. 判级扩展：到期降级 / NULL=永久 / 宁降不升（存量语义零破坏）
# ---------------------------------------------------------------------------


def test_entitlement_effective_null_expiry_is_permanent_pro():
    assert entitlement_effective("pro", None) == "pro"
    assert entitlement_effective("pro") == "pro"


def test_entitlement_effective_expired_pro_degrades_to_free():
    now = utcnow()
    assert entitlement_effective("pro", now - timedelta(seconds=1), now=now) == "free"
    # 边界：恰好到期时刻 → 已失效（宁降不升）
    assert entitlement_effective("pro", now, now=now) == "free"
    assert entitlement_effective("pro", now + timedelta(days=30), now=now) == "pro"


def test_entitlement_effective_unknown_values_stay_free():
    now = utcnow()
    for raw in ("premium", "", None, "PRO ", "free"):
        assert entitlement_effective(raw, now + timedelta(days=1), now=now) == (
            "pro" if raw == "PRO " else "free"
        )
    assert entitlement_effective_grants_pro("pro", utcnow() + timedelta(days=1)) is True


def test_legacy_sites_unchanged_without_expiry():
    """存量 read 面（无 expiry 列时代）行为回归：entitlement_grants_pro 语义不变。"""
    from app.core.entitlement import entitlement_grants_pro

    assert entitlement_grants_pro("pro") is True
    assert entitlement_grants_pro("free") is False
    assert entitlement_grants_pro(None) is False


# ---------------------------------------------------------------------------
# 2. 迁移：sqlite 隔离重放 + 可逆 + 链契约
# ---------------------------------------------------------------------------


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("rd01_20260922", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rd01_migration_replay_and_reversibility(tmp_path):
    module = _load_migration_module()
    assert module.down_revision == "x07_20260921"  # 迁移链契约：单父挂当前 head

    engine = create_engine(f"sqlite:///{tmp_path / 'rd_mig.db'}")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id CHAR(36) PRIMARY KEY, entitlement VARCHAR(32) NOT NULL DEFAULT 'free')"))
        conn.execute(text("INSERT INTO users (id, entitlement) VALUES ('u-1', 'free'), ('u-2', 'free')"))

        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
        conn.commit()

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "redeem_codes" in tables
    rd_cols = {c["name"] for c in inspector.get_columns("redeem_codes")}
    assert {"code_hash", "tier", "duration_days", "max_uses", "used_count", "used_by", "used_at", "created_by", "batch_id", "expires_at"} <= rd_cols
    users_cols = {c["name"] for c in inspector.get_columns("users")}
    assert "entitlement_expires_at" in users_cols
    # 存量行新列 NULL = 永久（语义零变化）
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT entitlement_expires_at FROM users ORDER BY id")).all()
    assert rows == [(None,), (None,)]

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.downgrade()
        conn.commit()
    assert "redeem_codes" not in inspect(engine).get_table_names()
    assert "entitlement_expires_at" not in {c["name"] for c in inspect(engine).get_columns("users")}


# ---------------------------------------------------------------------------
# 3. 生成面
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_batch_format_and_hash_only(db):
    codes = await _make_batch(db, count=5, duration_days=30, created_by=None)
    assert len(codes) == 5
    assert len(set(codes)) == 5
    for code in codes:
        assert code.startswith("SPARK-")
        assert len(code) == 20  # SPARK-XXXX-XXXX-XXXX（含连字符）
        assert len(code.replace("-", "")) == 17  # 归一化长度 = 5 前缀 + 12 随机位
        assert normalize_redeem_code(code) == code.replace("-", "")
    rows = (await db.execute(select(RedeemCode))).scalars().all()
    assert len(rows) == 5
    for row in rows:
        assert len(row.code_hash) == 64
        for code in codes:  # 明文（全量/片段）不落库
            assert code not in (row.code_hash or "")
            assert row.code_prefix is None or code[:14] not in (row.code_prefix or "")


def test_generate_redeem_code_is_csprng_shaped():
    codes = {generate_redeem_code() for _ in range(200)}
    assert len(codes) == 200
    sample = next(iter(codes))
    body = sample.replace("SPARK-", "").replace("-", "")
    assert all(ch in redeem_service.CODE_ALPHABET for ch in body)


# ---------------------------------------------------------------------------
# 4. 核销面
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redeem_success_upgrades_entitlement_with_expiry(db):
    user = await _make_user(db)
    (code,) = await _make_batch(db, count=1, duration_days=30)
    before = utcnow()

    outcome = await redeem_service.redeem(db, user_id=user.id, code=code)
    await db.commit()

    assert outcome.status == REDEEM_OK
    assert outcome.tier == "pro"
    assert outcome.entitlement_expires_at is not None
    # before 取在核销前，实际基线 now ≥ before → delta 可微超 30d（秒级容差）
    delta = outcome.entitlement_expires_at - before
    assert timedelta(days=29, hours=23) < delta <= timedelta(days=30, minutes=5)
    await db.refresh(user)
    assert user.entitlement == "pro"
    assert user.entitlement_expires_at == outcome.entitlement_expires_at


@pytest.mark.asyncio
async def test_redeem_same_code_twice_single_use_is_exhausted(db):
    user = await _make_user(db)
    (code,) = await _make_batch(db, count=1, max_uses=1)

    first = await redeem_service.redeem(db, user_id=user.id, code=code)
    await db.commit()
    second = await redeem_service.redeem(db, user_id=user.id, code=code)
    await db.commit()

    assert first.status == REDEEM_OK
    assert second.status == REDEEM_EXHAUSTED
    await db.refresh(user)
    assert user.entitlement_expires_at == first.entitlement_expires_at  # 未二次叠加


@pytest.mark.asyncio
async def test_redeem_concurrent_same_code_exactly_one_success(db_engine, tmp_path):
    """红线并发测试：N 个并发核销同一 1 次码，恰一次成功（防双花）。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        (code,) = await _make_batch(setup, count=1, max_uses=1)

    async def attempt() -> str:
        async with maker() as session:
            outcome = await redeem_service.redeem(session, user_id=user.id, code=code)
            await session.commit()
            return outcome.status

    statuses = await asyncio.gather(*(attempt() for _ in range(8)))

    assert statuses.count(REDEEM_OK) == 1
    assert statuses.count(REDEEM_EXHAUSTED) == 7
    async with maker() as verify:
        row = (
            await verify.execute(select(RedeemCode))
        ).scalars().one()
        assert row.used_count == 1
        assert row.used_by is not None


@pytest.mark.asyncio
async def test_redeem_max_uses_cap_then_exhausted(db):
    user = await _make_user(db)
    (code,) = await _make_batch(db, count=1, max_uses=3, duration_days=7)

    results = []
    for _ in range(4):
        outcome = await redeem_service.redeem(db, user_id=user.id, code=code)
        await db.commit()
        results.append(outcome.status)

    assert results == [REDEEM_OK, REDEEM_OK, REDEEM_OK, REDEEM_EXHAUSTED]
    row = (await db.execute(select(RedeemCode))).scalars().one()
    assert row.used_count == row.max_uses


@pytest.mark.asyncio
async def test_redeem_expired_code_rejected(db):
    user = await _make_user(db)
    batch = await redeem_service.generate_batch(
        db, count=1, duration_days=30, expires_in_days=1
    )
    row = (await db.execute(select(RedeemCode))).scalars().one()
    # 直接把码置为已过期（避免测试等待一天）
    row.expires_at = utcnow() - timedelta(minutes=1)
    await db.commit()

    outcome = await redeem_service.redeem(db, user_id=user.id, code=batch.codes[0])
    await db.commit()

    assert outcome.status == REDEEM_EXPIRED
    await db.refresh(user)
    assert user.entitlement == "free"
    assert user.entitlement_expires_at is None


@pytest.mark.asyncio
async def test_redeem_invalid_code_rejected(db):
    user = await _make_user(db)
    outcome = await redeem_service.redeem(db, user_id=user.id, code="SPARK-0000-0000-0000")
    await db.commit()
    assert outcome.status == REDEEM_INVALID

    short = await redeem_service.redeem(db, user_id=user.id, code="SPARK")
    assert short.status == REDEEM_INVALID


@pytest.mark.asyncio
async def test_redeem_stacks_on_active_pro_and_restarts_after_expiry(db):
    now = utcnow()
    active = await _make_user(db, entitlement="pro", expires_at=now + timedelta(days=10))
    (c1,) = await _make_batch(db, count=1, duration_days=30)
    out1 = await redeem_service.redeem(db, user_id=active.id, code=c1)
    await db.commit()
    assert out1.entitlement_expires_at is not None
    assert timedelta(days=39) <= out1.entitlement_expires_at - now <= timedelta(days=41)

    expired = await _make_user(db, entitlement="pro", expires_at=now - timedelta(days=5))
    (c2,) = await _make_batch(db, count=1, duration_days=30)
    out2 = await redeem_service.redeem(db, user_id=expired.id, code=c2)
    await db.commit()
    assert out2.entitlement_expires_at is not None
    assert timedelta(days=29) <= out2.entitlement_expires_at - now <= timedelta(days=31)


@pytest.mark.asyncio
async def test_redeem_never_downgrades_permanent_pro_to_dated(db):
    """红线：既有永久 pro（手工授予）核销后仍保持 NULL 到期，不得被降为有期。"""
    user = await _make_user(db, entitlement="pro", expires_at=None)
    (code,) = await _make_batch(db, count=1, duration_days=30)

    outcome = await redeem_service.redeem(db, user_id=user.id, code=code)
    await db.commit()

    assert outcome.status == REDEEM_OK
    await db.refresh(user)
    assert user.entitlement == "pro"
    assert user.entitlement_expires_at is None


# ---------------------------------------------------------------------------
# 5. 红线：明文不进日志；budget 派生随到期降级
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plaintext_never_enters_logs_or_hash_column(db, caplog):
    user = await _make_user(db)
    (code,) = await _make_batch(db, count=1, duration_days=30)

    with caplog.at_level(logging.DEBUG):
        await redeem_service.redeem(db, user_id=user.id, code=code)
        await db.commit()

    assert code not in caplog.text
    assert normalize_redeem_code(code) not in caplog.text
    row = (await db.execute(select(RedeemCode))).scalars().one()
    assert row.code_hash == hash_redeem_code(normalize_redeem_code(code))
    assert code not in row.code_hash


def test_budget_derivation_degrades_to_free_after_expiry():
    """run 预算派生（O-07）随到期降级：过期 pro → free 档派生值（宁降不升）。"""
    now = utcnow()
    assert (
        derive_default_run_budget_if_enabled(
            entitlement_effective("pro", now - timedelta(days=1), now=now)
        )
        == derive_default_run_budget_if_enabled("free")
    )
    assert (
        derive_default_run_budget_if_enabled(
            entitlement_effective("pro", now + timedelta(days=1), now=now)
        )
        == derive_default_run_budget_if_enabled("pro")
    )


# ---------------------------------------------------------------------------
# 6. API 面：鉴权挂载 + 业务状态映射
# ---------------------------------------------------------------------------


@pytest.fixture
def api_harness(db_engine):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    def _build(current_user):
        from app.api.deps import get_current_active_superuser, get_current_active_user, get_db
        from app.api.v1.redeem import router as redeem_router

        app = FastAPI()
        app.include_router(redeem_router)

        async def _override_db():
            # 与生产 get_db 同事务语义：成功提交、异常回滚（核销必须真实落库）
            async with maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_active_user] = lambda: current_user
        app.dependency_overrides[get_current_active_superuser] = lambda: current_user
        return TestClient(app)

    return _build


@pytest.mark.asyncio
async def test_api_user_redeem_status_mapping(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        user = await _make_user(setup)
        codes = await _make_batch(setup, count=2, duration_days=30)

    client = api_harness(user)

    ok = client.post("/billing/redeem", json={"code": codes[0]})
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["status"] == "ok"
    assert payload["tier"] == "pro"
    assert payload["entitlement_expires_at"] is not None

    exhausted = client.post("/billing/redeem", json={"code": codes[0]})
    assert exhausted.status_code == 409
    assert exhausted.json()["detail"]["status"] == REDEEM_EXHAUSTED

    invalid = client.post("/billing/redeem", json={"code": "SPARK-0000-0000-0000"})
    assert invalid.status_code == 404
    assert invalid.json()["detail"]["status"] == REDEEM_INVALID

    async with maker() as verify:
        row = (await verify.execute(select(User))).scalars().one()
        assert row.entitlement == "pro"


@pytest.mark.asyncio
async def test_api_admin_route_mounts_superuser_guard(db_engine, api_harness):
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as setup:
        admin = await _make_user(setup)
        admin.is_superuser = True
        await setup.commit()

    client = api_harness(admin)
    created = client.post(
        "/billing/redeem-codes",
        json={"tier": "pro", "duration_days": 30, "count": 3, "max_uses": 1, "batch_id": "demo-batch-1"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["batch_id"] == "demo-batch-1"
    assert len(body["codes"]) == 3

    # batch_id 幂等防覆盖：同 batch_id 再生成 → 409
    duplicate = client.post(
        "/billing/redeem-codes",
        json={"tier": "pro", "duration_days": 30, "count": 3, "batch_id": "demo-batch-1"},
    )
    assert duplicate.status_code == 409

    # 静态断言：admin 面确实挂在 superuser 依赖上（鉴权面不弱化）
    from app.api.deps import get_current_active_superuser
    from app.api.v1.redeem import router as redeem_router

    route = next(r for r in redeem_router.routes if getattr(r, "path", "").endswith("/redeem-codes"))
    dep_calls = [d.call for d in route.dependant.dependencies]
    assert get_current_active_superuser in dep_calls

    # 生成的码可直接被 user 面核销（闭环）
    (code,) = body["codes"][:1]
    async with maker() as setup2:
        user = await _make_user(setup2)
    user_client = api_harness(user)
    ok = user_client.post("/billing/redeem", json={"code": code})
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"
