"""x03b_20260920 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

R2 P2-3 返修的 schema 半边：``user_settings.low_risk_auto_execute``（授权门
服务端真源）。用 alembic Operations/MigrationContext 把
x03b_20260920_user_settings_low_risk_auto.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证：
- 新列落上 user_settings（NOT NULL，server_default false）；
- 既有行 upgrade 后存活且取默认 False（保守）；
- downgrade 把列移除，回到旧 schema；
- 迁移链挂 x03_20260919 下游（worktree 单头；P1 双头重挂由 Leader 合入时
  处理——x03 改挂 d05 后 x03b 自动跟随，此处只钉父子关系）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "x03b_20260920_user_settings_low_risk_auto.py"


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'x03b_test.db'}")

    # 最小 user_settings 基座：迁移前的旧 schema（无 low_risk_auto_execute）
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE user_settings (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                transparency_level INTEGER NOT NULL DEFAULT 0
            )
            """)
        conn.execute(text("INSERT INTO user_settings (id, user_id) VALUES ('s-1', 'u-1')"))

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("x03b_20260920", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_x03b_chains_from_x03():
    module = _load_migration_module()
    # x03b 挂 x03 下游（返修不触碰 x03→x05 双头重挂——Leader 合入时改挂 d05，
    # 本迁移作为 x03 的子节点自动跟随，链保持单头）
    assert module.down_revision == "x03_20260919"


def test_x03b_upgrade_adds_column_and_old_rows_default_false(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)
    columns = {c["name"] for c in inspect(engine).get_columns("user_settings")}
    assert "low_risk_auto_execute" in columns

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT user_id, low_risk_auto_execute FROM user_settings")).fetchall()
    assert rows == [("u-1", False)]  # 旧行存活 + 保守默认 False

    # downgrade 对称移除
    run_migration(module.downgrade)
    columns_after = {c["name"] for c in inspect(engine).get_columns("user_settings")}
    assert "low_risk_auto_execute" not in columns_after
