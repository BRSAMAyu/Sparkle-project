"""cp01confirm_20260922 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
cp01confirm_20260922_add_plan_confirmed_at 的 upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证 CP-01 计划人工确认列的 schema 变更：

- upgrade 后 plans 表新增 confirmed_at 列（nullable，无 NOT NULL 违约风险）；
- 存量行（含已软删行）upgrade 后 confirmed_at 保持 NULL（无推测性回填）；
- downgrade 后列被移除，round-trip 后 schema 还原；
- upgrade→downgrade→upgrade 幂等可重入。

迁移语义（落点裁决）见 PlanService.confirm_plan docstring 与
v3-output/CP01-CONFIRM/REPORT.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "cp01confirm_20260922_add_plan_confirmed_at.py"


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cp01_confirm_test.db'}")

    # 最小 plans 基座：迁移前 schema（无 confirmed_at），含确认语义消费面的关键列
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE plans (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                type VARCHAR(16) NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at DATETIME
            )
        """)
        conn.exec_driver_sql(
            "INSERT INTO plans (id, user_id, type, is_active, deleted_at) "
            "VALUES ('p-1', 'u-1', 'SPRINT', 1, NULL)"
        )
        conn.exec_driver_sql(
            "INSERT INTO plans (id, user_id, type, is_active, deleted_at) "
            "VALUES ('p-2', 'u-1', 'SPRINT', 0, '2026-09-01T00:00:00')"
        )

    def run_migration(op_fn) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DDL 亦在事务内），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("cp01_confirm_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _column_names(engine) -> set[str]:
    inspector = inspect(engine)
    return {col["name"] for col in inspector.get_columns("plans")}


def test_upgrade_adds_confirmed_at_nullable_and_keeps_rows_null(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    assert "confirmed_at" not in _column_names(engine)

    run_migration(upgrade)

    assert "confirmed_at" in _column_names(engine)
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT id, confirmed_at FROM plans ORDER BY id"
        ).fetchall()
    assert [row[0] for row in rows] == ["p-1", "p-2"]
    # 无推测性回填：存量行（含软删行）一律视为未确认
    assert all(row[1] is None for row in rows)


def test_round_trip_downgrade_restores_schema(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)
    assert "confirmed_at" in _column_names(engine)

    run_migration(downgrade)
    assert "confirmed_at" not in _column_names(engine)
    # 数据行在 round-trip 后原样存活
    with engine.begin() as conn:
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM plans").scalar()
    assert count == 2


def test_migration_is_reentrant(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)
    run_migration(downgrade)
    run_migration(upgrade)

    assert "confirmed_at" in _column_names(engine)
