"""x07_20260921 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
x07_20260921_add_agent_run_steps.upgrade/downgrade 单独跑在临时 sqlite
文件库上，验证：

- ``steps`` JSON 列落上 ``agent_runs`` 表（NOT NULL + server default '[]'，
  旧行全兼容——X-05 既有 run 行不迁移即可读）；
- 旧记录在 upgrade 后原样存活且 steps 缺省 '[]'；
- downgrade 移除该列，回到 X-05 schema；
- 零新表：X-07 唯一 schema 变更就是这一列（不建平行真源）。
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
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "x07_20260921_add_agent_run_steps.py"


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'x07_test.db'}")

    # 最小 agent_runs 基座：模拟 X-05 迁移后的 schema（无 steps 列）
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE agent_runs (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                objective TEXT NOT NULL,
                status VARCHAR(24) NOT NULL,
                steps_done INTEGER NOT NULL DEFAULT 0
            )
            """)
        conn.exec_driver_sql(
            "INSERT INTO agent_runs (id, user_id, objective, status) "
            "VALUES ('run-legacy', 'user-1', '旧 run 行', 'SUCCEEDED')"
        )

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("x07_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def test_x07_migration_adds_steps_column_and_survives_legacy_rows(migration_env):
    engine, run_migration, load = migration_env
    upgrade, downgrade = load()

    run_migration(upgrade)

    inspector = inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("agent_runs")}
    assert "steps" in columns
    assert columns["steps"]["nullable"] is False

    # 旧行原样存活 + steps 缺省 '[]'（JSON 序列化形态）
    with engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT id, objective, status, steps FROM agent_runs WHERE id = 'run-legacy'"
        ).fetchone()
    assert row is not None
    assert row[1] == "旧 run 行"
    assert row[2] == "SUCCEEDED"
    assert row[3] in ("[]", "", None) or row[3] == b"[]"

    # downgrade 回到 X-05 schema（列移除）
    run_migration(downgrade)
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("agent_runs")}
    assert "steps" not in columns


def test_x07_migration_is_the_only_schema_change(migration_env):
    """零新表：步骤计划挂在既有 run 聚合内（不建平行真源）。"""
    engine, run_migration, load = migration_env
    upgrade, _ = load()

    before = set(inspect(engine).get_table_names())
    run_migration(upgrade)
    after = set(inspect(engine).get_table_names())
    assert after == before
    assert "agent_run_steps" not in after  # 平行真源出现即失败
