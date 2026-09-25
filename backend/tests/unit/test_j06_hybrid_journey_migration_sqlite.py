"""j06_20260925 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
j06_20260925_add_hybrid_journey_artifacts.upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证表结构、索引与可回滚性（j05/d03 同款 harness）。
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
    BACKEND_ROOT / "alembic" / "versions" / "j06_20260925_add_hybrid_journey_artifacts.py"
)

EXPECTED_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "run_id",
    "task_id",
    "stage",
    "artifact_kind",
    "citations",
    "source_refs",
    "payload",
    "schema_version",
}

EXPECTED_INDEXES = {"idx_hybrid_journey_artifact_run", "idx_hybrid_journey_artifact_user"}

#: 单头断言：j06_20260925 的 down_revision 必须是 j05_20260925（链不裂头）。
EXPECTED_DOWN_REVISION = "j05_20260925"


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'j06_test.db'}")
    with engine.begin() as conn:
        # 外键目标最小基座（重放只验表结构，不写数据）。
        conn.exec_driver_sql(
            "CREATE TABLE users ("
            "id VARCHAR(36) PRIMARY KEY, "
            "created_at TIMESTAMP, updated_at TIMESTAMP)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE agent_runs ("
            "id VARCHAR(36) PRIMARY KEY, "
            "created_at TIMESTAMP, updated_at TIMESTAMP)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE tasks ("
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
    spec = importlib.util.spec_from_file_location("j06_20260925", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_head_chained_to_j05():
    module = _load_migration_module()
    assert module.revision == "j06_20260925"
    assert module.down_revision == EXPECTED_DOWN_REVISION


def test_upgrade_creates_expected_schema(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    inspector = inspect(engine)
    assert "hybrid_journey_artifacts" in inspector.get_table_names()
    assert {
        col["name"] for col in inspector.get_columns("hybrid_journey_artifacts")
    } >= EXPECTED_COLUMNS
    assert {
        idx["name"] for idx in inspector.get_indexes("hybrid_journey_artifacts")
    } >= EXPECTED_INDEXES


def test_upgrade_is_idempotent(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    run_migration(module.upgrade)  # 二次执行不炸（has_table 幂等守卫）
    assert "hybrid_journey_artifacts" in inspect(engine).get_table_names()


def test_downgrade_drops_table(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    run_migration(module.downgrade)
    assert "hybrid_journey_artifacts" not in inspect(engine).get_table_names()
