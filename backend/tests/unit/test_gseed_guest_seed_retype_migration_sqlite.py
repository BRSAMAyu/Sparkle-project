"""gseed_20260923 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
gseed_20260923_guest_seed_out_of_redeem_base 的 upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证访客种子流水改型的数据回填语义（MINT-FIX，
D-MONETIZE 审计 §1.5-R3）：

- upgrade 只改写三键联合锁定的误标行（transaction_type='grant_achievement'
  AND source='guest_seed:welcome_bonus' AND related_item_id='guest_welcome'）
  为专有类型 guest_seed——出「可兑换基数」收入词表；
- 域外行零影响：普通成就发放（grant_achievement + 裸 achievement_id）、
  其他 source 的 guest 域行、daily_first/combo/purchase 形态一概不动；
- round-trip：downgrade 精确还原误标形态，upgrade 幂等可重入。

迁移语义与影响申报见迁移文件 docstring 与 v3-output/MINT-FIX/REPORT.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "gseed_20260923_guest_seed_out_of_redeem_base.py"

# 迁移前 schema：photon_transaction_history 裸表（与现网一致，transaction_type
# 为 VARCHAR(50) 非 PG 原生枚举——新类型值零 DDL）。
BASE_DDL = """
CREATE TABLE photon_transaction_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    source VARCHAR(255),
    related_item_id VARCHAR(50),
    extra_data JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
)
"""

U1 = "11111111-1111-1111-1111-111111111111"
U2 = "22222222-2222-2222-2222-222222222222"


def _insert_tx(
    conn,
    *,
    tx_id: str,
    user: str,
    tx_type: str,
    source: str,
    related: str | None,
    amount: int = 1000,
) -> None:
    conn.exec_driver_sql(
        "INSERT INTO photon_transaction_history "
        "(id, user_id, transaction_type, amount, balance_before, balance_after, "
        "source, related_item_id, extra_data, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, '2026-09-20 10:00:00', '2026-09-20 10:00:00')",
        (tx_id, user, tx_type, amount, 0, amount, source, related),
    )


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'gseed_migration.db'}")

    # 迁移前基座：改写域内误标行 + 域外各形态对照行
    with engine.begin() as conn:
        conn.exec_driver_sql(BASE_DDL)
        # 域内：访客种子误标行（grant_achievement + 种子 source + guest_welcome）
        _insert_tx(conn, tx_id="a" * 36, user=U1, tx_type="grant_achievement",
                   source="guest_seed:welcome_bonus", related="guest_welcome")
        _insert_tx(conn, tx_id="b" * 36, user=U2, tx_type="grant_achievement",
                   source="guest_seed:welcome_bonus", related="guest_welcome")
        # 域外：普通成就发放（同类型，但 source/related 域外）——不得被误伤
        _insert_tx(conn, tx_id="c" * 36, user=U1, tx_type="grant_achievement",
                   source="achievement:streak_7", related="streak_7", amount=50)
        # 域外：种子 source 但类型已改（幂等重放形态）——upgrade 对其零命中
        _insert_tx(conn, tx_id="d" * 36, user=U2, tx_type="guest_seed",
                   source="guest_seed:welcome_bonus", related="guest_welcome")
        # 域外：guest_welcome 键但 source 不同（防御未来其他 guest 域写入方）
        _insert_tx(conn, tx_id="e" * 36, user=U1, tx_type="grant_achievement",
                   source="guest_other:bonus", related="guest_welcome", amount=20)
        # 域外：日常收入形态（首胜）
        _insert_tx(conn, tx_id="f" * 36, user=U1, tx_type="grant_daily_first",
                   source="daily_first", related="daily_first:2026-09-23", amount=30)

    def run_migration(op_fn) -> None:
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("gseed_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _type_of(engine, tx_id: str) -> str:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT transaction_type FROM photon_transaction_history "
                "WHERE id = :tid"
            ),
            {"tid": tx_id},
        ).scalar_one()


def test_upgrade_retypes_only_seed_rows(migration_env):
    engine, run_migration, load = migration_env
    upgrade, _ = load()
    run_migration(upgrade)

    # 域内：误标行 → guest_seed
    assert _type_of(engine, "a" * 36) == "guest_seed"
    assert _type_of(engine, "b" * 36) == "guest_seed"
    # 域外：逐行原样
    assert _type_of(engine, "c" * 36) == "grant_achievement"
    assert _type_of(engine, "d" * 36) == "guest_seed"  # 已改型行不动
    assert _type_of(engine, "e" * 36) == "grant_achievement"
    assert _type_of(engine, "f" * 36) == "grant_daily_first"


def test_upgrade_is_idempotent(migration_env):
    engine, run_migration, load = migration_env
    upgrade, _ = load()
    run_migration(upgrade)
    run_migration(upgrade)  # 二次执行零行命中、零异常
    assert _type_of(engine, "a" * 36) == "guest_seed"
    assert _type_of(engine, "c" * 36) == "grant_achievement"


def test_round_trip_restores_legacy_shape(migration_env):
    engine, run_migration, load = migration_env
    upgrade, downgrade = load()
    run_migration(upgrade)
    run_migration(downgrade)

    assert _type_of(engine, "a" * 36) == "grant_achievement"
    assert _type_of(engine, "b" * 36) == "grant_achievement"
    assert _type_of(engine, "c" * 36) == "grant_achievement"
    # down 改写域同样只锁三键：已改型行还原，域外行不受影响
    assert _type_of(engine, "d" * 36) == "grant_achievement"
    assert _type_of(engine, "e" * 36) == "grant_achievement"
    assert _type_of(engine, "f" * 36) == "grant_daily_first"
