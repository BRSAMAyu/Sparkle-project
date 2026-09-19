"""d05_20260919 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
d05_20260919_add_intervention_lifecycle_events.upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证表结构、``uq_intervention_lifecycle_once``
唯一约束（幂等语义的存储层机制）与可回滚性。
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
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "d05_20260919_add_intervention_lifecycle_events.py"

EXPECTED_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "decision_id",
    "event_type",
    "intervention_type",
    "execution_mode",
    "goal_type",
    "friction_tag",
    "linkage",
    "outcome_source",
    "outcome_ref",
    "outcome_polarity",
    "outcome_truth_class",
    "detail",
    "dedupe_subkey",
    "occurred_at",
}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'd05_test.db'}")

    def run_migration(op_fn: Callable[[], None]) -> None:
        """把迁移模块的 upgrade/downgrade 绑到 sqlite 连接上隔离执行。"""
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            conn.commit()

    yield run_migration, engine
    engine.dispose()


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("d05_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_creates_table_with_idempotency_unique_constraint(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    inspector = inspect(engine)
    assert inspector.has_table("intervention_lifecycle_events")
    columns = {col["name"] for col in inspector.get_columns("intervention_lifecycle_events")}
    assert columns == EXPECTED_COLUMNS

    constraints = {
        uc["name"]: uc["column_names"]
        for uc in inspector.get_unique_constraints("intervention_lifecycle_events")
    }
    assert constraints.get("uq_intervention_lifecycle_once") == [
        "decision_id",
        "event_type",
        "dedupe_subkey",
    ]

    index_names = {ix["name"] for ix in inspector.get_indexes("intervention_lifecycle_events")}
    assert {
        "ix_intervention_lifecycle_user",
        "ix_intervention_lifecycle_decision",
        "ix_intervention_lifecycle_event_type",
        "ix_intervention_lifecycle_occurred",
        "ix_intervention_lifecycle_user_intervention",
    } <= index_names


def test_unique_constraint_actually_blocks_double_count(migration_env):
    """「同一 intervention 不双计」的存储层本体：同 (decision_id, event_type,
    dedupe_subkey) 第二行必须被唯一约束拒绝。"""
    from sqlalchemy import text

    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    insert_sql = text(
        "INSERT INTO intervention_lifecycle_events "
        "(id, user_id, decision_id, event_type, intervention_type, goal_type, friction_tag,"
        " dedupe_subkey, occurred_at, created_at) "
        "VALUES (:id, :user_id, :decision_id, :event_type, 'rescope', 'exam',"
        " 'knowledge_bottleneck', :dedupe_subkey, '2026-09-19 10:00:00', '2026-09-19 10:00:00')"
    )
    row = {
        "id": "11111111-1111-4111-8111-111111111111",
        "user_id": "22222222-2222-4222-8222-222222222222",
        "decision_id": "aurora_" + "a" * 32,
        "event_type": "exposed",
        "dedupe_subkey": "",
    }
    with engine.begin() as conn:
        conn.execute(insert_sql, row)
        with pytest.raises(Exception, match="UNIQUE|constraint"):
            conn.execute(insert_sql, row)
        # 不同 dedupe_subkey（不同 outcome）不成重复
        conn.execute(
            insert_sql,
            {
                **row,
                "id": "33333333-3333-4333-8333-333333333333",
                "event_type": "outcome_observed",
                "dedupe_subkey": "outc_1",
            },
        )


def test_downgrade_drops_table_cleanly(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)
    run_migration(module.downgrade)
    assert not inspect(engine).has_table("intervention_lifecycle_events")
