"""a05_20260919 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）。

不连主仓 PostgreSQL：用 alembic Operations/MigrationContext 把
a05_20260919_add_aurora_policy_patches.upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证表结构、``uq_policy_patch_once`` 唯一约束（内容寻址
幂等的存储层机制）、索引与可回滚性（D-05 迁移测试同款）。
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
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "a05_20260919_add_aurora_policy_patches.py"

EXPECTED_COLUMNS = {
    "id",
    "created_at",
    "updated_at",
    "deleted_at",
    "user_id",
    "patch_id",
    "surface",
    "payload",
    "scope_goal_type",
    "scope_friction_tag",
    "state",
    "provenance",
    "evidence_refs",
    "evidence_tier",
    "evidence_verified_at",
    "user_confirmed",
    "confirmed_at",
    "activated_at",
    "expires_at",
    "revoked_at",
    "revoke_reason",
    "transition_history",
}


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'a05_test.db'}")

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
    spec = importlib.util.spec_from_file_location("a05_20260919", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain_links_to_d05(migration_env):
    """迁移挂接点：down_revision = d05_20260919（链单头延续，D-05 R2 教训）。"""
    module = _load_migration_module()
    assert module.revision == "a05_20260919"
    assert module.down_revision == "d05_20260919"


def test_upgrade_creates_table_with_idempotency_unique_constraint(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)

    inspector = inspect(engine)
    assert inspector.has_table("aurora_policy_patches")
    columns = {col["name"] for col in inspector.get_columns("aurora_policy_patches")}
    assert columns == EXPECTED_COLUMNS

    constraints = {uc["name"]: uc["column_names"] for uc in inspector.get_unique_constraints("aurora_policy_patches")}
    assert constraints.get("uq_policy_patch_once") == ["patch_id"]

    index_names = {ix["name"] for ix in inspector.get_indexes("aurora_policy_patches")}
    assert {
        "ix_aurora_policy_patches_user",
        "ix_aurora_policy_patches_state",
        "ix_aurora_policy_patches_expires",
    } <= index_names


def test_downgrade_drops_table_cleanly(migration_env):
    run_migration, engine = migration_env
    module = _load_migration_module()
    run_migration(module.upgrade)
    run_migration(module.downgrade)
    assert not inspect(engine).has_table("aurora_policy_patches")
