"""intakeidx_20260922 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
intakeidx_20260922_add_plans_sprint_goal_unique.upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证：

- 存量收敛：同目标活跃双计划（LOOP1 时代产物）保留最新（created_at DESC,
  id DESC），旧者仅置 is_active=false（不删行、不改内容）；
- 谓词边界：inactive 行、软删行、GROWTH 同键行、subject/target_date 为 NULL
  的行一律不收敛、不参与唯一性（可继续共存）；
- 索引生效：upgrade 后同目标第二个活跃 sprint 行 INSERT 被拒
  （UNIQUE constraint failed），inactive 形态不受限；
- 可升可降：downgrade 移除索引后同目标双活跃行可再次共存；
- 只读纪律：本测试全程不触碰真实 DB。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "intakeidx_20260922_add_plans_sprint_goal_unique.py"

_USER = "11111111-1111-1111-1111-111111111111"
_USER2 = "22222222-2222-2222-2222-222222222222"


def _insert_plan(
    conn,
    plan_id: str,
    *,
    user_id: str = _USER,
    type_: str = "SPRINT",
    subject: str | None = "计算机网络",
    target_date: str | None = "2026-05-02",
    is_active: int = 1,
    deleted_at: str | None = None,
    created_at: str = "2026-09-19 00:00:00",
) -> None:
    conn.exec_driver_sql(
        "INSERT INTO plans (id, user_id, name, type, subject, target_date, is_active, deleted_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            plan_id,
            user_id,
            f"plan-{plan_id}",
            type_,
            subject,
            target_date,
            is_active,
            deleted_at,
            created_at,
            created_at,
        ),
    )


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'intakeidx_test.db'}")

    # 最小 plans 基座：参与约束/收敛所需的列（模拟基线之后的 plans 形态）
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE plans (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(16) NOT NULL,
                subject VARCHAR(100),
                target_date VARCHAR(10),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                deleted_at DATETIME,
                created_at DATETIME,
                updated_at DATETIME
            )
            """)
        # LOOP1 时代同目标活跃双计划：保留最新（plan-new），旧者收敛
        _insert_plan(conn, "plan-old", created_at="2026-09-19 00:00:00")
        _insert_plan(conn, "plan-new", created_at="2026-09-20 00:00:00")
        # 谓词边界：以下各行不得被收敛，也不参与唯一性
        _insert_plan(conn, "plan-inactive", is_active=0)
        _insert_plan(conn, "plan-deleted", deleted_at="2026-09-21 00:00:00")
        _insert_plan(conn, "plan-growth", type_="GROWTH")
        _insert_plan(conn, "plan-nosub", subject=None)
        _insert_plan(conn, "plan-nodate", target_date=None)
        _insert_plan(conn, "plan-other-user", user_id=_USER2)

    def run_migration(op_fn: Callable[[], None]) -> None:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()
            # Operations.context 只安装 op 代理不提交；SQLAlchemy 2.0 的
            # pysqlite 全事务模式下 DDL/DML 都在未决事务里，需显式提交
            conn.commit()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("intakeidx_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _is_active(engine, plan_id: str) -> int:
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT is_active FROM plans WHERE id = ?", (plan_id,)).fetchone()
    assert row is not None, f"plan {plan_id} missing"
    return int(row[0])


def _index_sql(engine) -> str:
    with engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_plans_user_sprint_goal_active'"
        ).fetchone()
    return row[0] if row else ""


def test_intakeidx_migration_converges_and_enforces_goal_uniqueness(migration_env):
    engine, run_migration, load = migration_env
    upgrade, downgrade = load()

    run_migration(upgrade)

    # 索引落上且为部分唯一索引（谓词原样保留）
    index_sql = _index_sql(engine)
    assert "UNIQUE INDEX uq_plans_user_sprint_goal_active" in index_sql
    assert "type = 'SPRINT'" in index_sql and "deleted_at IS NULL" in index_sql

    # 存量收敛：保留最新，旧者仅置 is_active=false（行仍在、内容未动）
    assert _is_active(engine, "plan-new") == 1
    assert _is_active(engine, "plan-old") == 0

    # 谓词边界行原样存活
    assert _is_active(engine, "plan-inactive") == 0
    assert _is_active(engine, "plan-deleted") == 1
    assert _is_active(engine, "plan-growth") == 1
    assert _is_active(engine, "plan-nosub") == 1
    assert _is_active(engine, "plan-nodate") == 1
    assert _is_active(engine, "plan-other-user") == 1

    # 索引生效：同目标第二个活跃 sprint 行被 DB 拒绝
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            _insert_plan(conn, "plan-dup", created_at="2026-09-21 00:00:00")

    # inactive 形态不受限：软删/停用后的同目标行可共存
    with engine.begin() as conn:
        _insert_plan(conn, "plan-dup-inactive", is_active=0, created_at="2026-09-21 00:00:00")
        _insert_plan(conn, "plan-dup-deleted", deleted_at="2026-09-22 00:00:00", created_at="2026-09-21 00:00:00")

    # downgrade：索引移除后同目标双活跃行可再次共存（数据收敛不自动回滚）
    run_migration(downgrade)
    assert _index_sql(engine) == ""
    with engine.begin() as conn:
        _insert_plan(conn, "plan-dup", created_at="2026-09-21 00:00:00")
    assert _is_active(engine, "plan-dup") == 1


def test_intakeidx_migration_noop_on_clean_data_and_still_indexed(migration_env):
    """无存量违反时收敛为零操作（幂等安全），索引照常落上。"""
    engine, run_migration, load = migration_env
    upgrade, _ = load()

    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM plans WHERE id = 'plan-old'")  # 消掉唯一违反组

    run_migration(upgrade)

    assert "UNIQUE INDEX uq_plans_user_sprint_goal_active" in _index_sql(engine)
    assert _is_active(engine, "plan-new") == 1  # 干净数据收敛零改动
    # 不同目标（不同 subject）正常插入不受影响
    with engine.begin() as conn:
        _insert_plan(conn, "plan-clean-dup", subject="高等数学", created_at="2026-09-21 00:00:00")
    assert _is_active(engine, "plan-clean-dup") == 1
    # 同目标重复仍被 DB 拒绝
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            _insert_plan(conn, "plan-clean-dup2", created_at="2026-09-21 00:00:00")
