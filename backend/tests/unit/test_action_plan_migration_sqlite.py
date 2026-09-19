"""x01_20260919 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
x01_20260919_add_action_plan_v3_columns.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证：
- 8 个 V3 新列全部落上 tasks 表（nullable，旧行全兼容）；
- execution_mode 是**复用**的既有列——upgrade/downgrade 都不得触碰它
  （禁止出现第二 execution_mode 列 / 重复真源）；
- 旧记录（无 V3 字段）在 upgrade 后原样存活且新列全 NULL；
- downgrade 把 8 个新列全部移除，回到旧 schema。
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
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "x01_20260919_add_action_plan_v3_columns.py"

# V3 契约新增列（execution_mode 复用既有列，不在此列）
ACTION_PLAN_V3_COLUMNS = {
    "action_schema_version",
    "desired_outcome",
    "smallest_useful_step",
    "completion_evidence",
    "cognitive_ownership",
    "source_refs",
    "risk_class",
    "reversible",
}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'x01_test.db'}")

    # 最小 tasks 基座：模拟迁移前的旧 schema（含将被复用的 execution_mode 列）
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE tasks (
                id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                execution_mode VARCHAR(20) NULL
            )
            """
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
    spec = importlib.util.spec_from_file_location("x01_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_x01_chains_from_current_single_head():
    module = _load_migration_module()
    # 返修 F3：合入窗口实况 ent01→e05(E-05)→m01a(M-01) 单头，x01 挂 m01a 恢复单头
    assert module.down_revision == "m01a_20260919", "必须挂在当前唯一 head（m01a）之后，禁止复活双头"


def test_x01_upgrade_adds_all_v3_columns_and_downgrade_removes_them(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    run_migration(module.upgrade)

    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("tasks")}
    missing = ACTION_PLAN_V3_COLUMNS - set(columns)
    assert not missing, f"V3 列缺失: {sorted(missing)}"
    for name in ACTION_PLAN_V3_COLUMNS:
        assert columns[name]["nullable"], f"{name} 必须 nullable（旧记录全兼容）"
        assert columns[name].get("default") is None, f"{name} 不得带 server default（NULL=legacy 语义）"

    # execution_mode 复用：不新增第二列
    assert "execution_mode" in columns

    run_migration(module.downgrade)
    columns_after = {col["name"] for col in inspect(engine).get_columns("tasks")}
    dropped = ACTION_PLAN_V3_COLUMNS & columns_after
    assert not dropped, f"downgrade 未清除: {sorted(dropped)}"
    assert "execution_mode" in columns_after, "downgrade 不得动既有 execution_mode 列"


def test_x01_legacy_rows_survive_upgrade_untouched(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO tasks (id, title, execution_mode) VALUES ('legacy-1', '旧任务', NULL)"
        )

    run_migration(module.upgrade)

    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT * FROM tasks WHERE id = 'legacy-1'").mappings().one()
    assert row["title"] == "旧任务"
    for name in ACTION_PLAN_V3_COLUMNS:
        assert row[name] is None, f"旧记录的 {name} 应保持 NULL"
