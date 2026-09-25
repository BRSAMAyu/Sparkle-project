"""j05_20260925 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
j05_20260925_add_stuck_journey_corrections.upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证表结构、索引与可回滚性（d03 同款 harness）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "j05_20260925_add_stuck_journey_corrections.py"
)

EXPECTED_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "surface",
    "friction_type",
    "intervention_key",
    "task_id",
    "goal_id",
    "reason_text",
    "context_snapshot",
    "schema_version",
    "corrected_at",
}

EXPECTED_INDEXES = {"idx_stuck_journey_corr_user", "idx_stuck_journey_corr_ftype"}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'j05_test.db'}")
    with engine.begin() as conn:
        # users 最小基座（外键目标；重放只验表结构，不写数据）。
        conn.exec_driver_sql(
            "CREATE TABLE users ("
            "id VARCHAR(36) PRIMARY KEY, "
            "created_at TIMESTAMP, updated_at TIMESTAMP)"
        )

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("j05_20260925", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_creates_expected_schema(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    inspector = inspect(engine)
    assert "stuck_journey_corrections" in inspector.get_table_names()
    assert EXPECTED_COLUMNS <= {
        col["name"] for col in inspector.get_columns("stuck_journey_corrections")
    }
    assert EXPECTED_INDEXES <= {
        idx["name"] for idx in inspector.get_indexes("stuck_journey_corrections")
    }


def test_upgrade_is_idempotent(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    run_migration(module.upgrade)  # 二次执行不炸（has_table 幂等守卫）
    assert "stuck_journey_corrections" in inspect(engine).get_table_names()


def test_downgrade_drops_table(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    run_migration(module.downgrade)
    assert "stuck_journey_corrections" not in inspect(engine).get_table_names()
