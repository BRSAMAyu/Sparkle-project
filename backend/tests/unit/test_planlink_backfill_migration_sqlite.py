"""planlink_20260922 回填迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
planlink_20260922_backfill_manual_task_plan 的 upgrade/downgrade 单独跑在临时
sqlite 文件库上，验证 PLAN-LINK 存量回填的从严条件与精确可逆：

- 唯一 active SPRINT 计划 + 计划期内 + NULL plan_id 的手动任务 → 回填；
- 计划期外（计划开始前 / target_date 已过）→ 不回填；
- 多个 active SPRINT 计划并存（归属歧义）→ 不回填（宁缺勿错）；
- 仅 goal plan（无 SPRINT）→ 不回填（goal 回落只在运行时默认关联生效）；
- 软删任务 → 不回填；
- intake 等原生带 plan_id 的任务 upgrade 前后原样存活；
- downgrade 按 guide_json['plan_link_backfill'] 标记**精确还原**回填行，
  原生任务不被触碰（按窗口反推会误伤 intake 行——本迁移的立卡理由）；
- 重复执行 upgrade 幂等（行内标记去重 + plan_id IS NULL 守卫）。
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "planlink_20260922_backfill_manual_task_plan.py"
MARKER_KEY = "plan_link_backfill"

NOW = datetime(2026, 9, 22, 12, 0, 0)


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'planlink_test.db'}")

    # 最小 plans/tasks 基座：只含迁移 SQL 触碰的列（语义等价，非全量 schema）
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE plans (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                type VARCHAR(16) NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at DATETIME,
                created_at DATETIME NOT NULL,
                target_date DATE
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE tasks (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                plan_id VARCHAR(36),
                deleted_at DATETIME,
                created_at DATETIME NOT NULL,
                guide_json TEXT
            )
        """)

    def run_migration(op_fn: Callable[[], None]) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DML 非隐式提交），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("planlink_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _seed_plan(
    engine,
    plan_id: str,
    user_id: str,
    *,
    type_: str = "SPRINT",
    is_active: int = 1,
    created_at: datetime | None = None,
    target_date: date | None = None,
    deleted_at=None,
) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO plans (id, user_id, type, is_active, deleted_at, created_at, target_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                plan_id,
                user_id,
                type_,
                is_active,
                deleted_at.isoformat() if deleted_at else None,
                (created_at or NOW - timedelta(days=7)).isoformat(),
                target_date.isoformat() if target_date else None,
            ),
        )


def _seed_task(
    engine,
    task_id: str,
    user_id: str,
    *,
    plan_id=None,
    created_at: datetime | None = None,
    deleted_at=None,
    guide_json: dict | None = None,
) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO tasks (id, user_id, plan_id, deleted_at, created_at, guide_json) " "VALUES (?, ?, ?, ?, ?, ?)",
            (
                task_id,
                user_id,
                plan_id,
                deleted_at.isoformat() if deleted_at else None,
                (created_at or NOW - timedelta(days=2)).isoformat(),
                json.dumps(guide_json) if guide_json is not None else None,
            ),
        )


def _task(engine, task_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT plan_id, guide_json FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert row is not None, f"task {task_id} missing"
    guide = json.loads(row[1]) if row[1] else {}
    return {"plan_id": row[0], "guide_json": guide}


def test_backfills_null_plan_task_in_unique_sprint_window(migration_env):
    """唯一 active SPRINT + 窗口内的 NULL plan 手动任务 → 回填 + 打标记。"""
    engine, run_migration, load = migration_env
    upgrade, downgrade = load()

    _seed_plan(
        engine, "plan-A", "user-1", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(engine, "task-manual", "user-1", created_at=NOW - timedelta(days=2))

    run_migration(upgrade)

    task = _task(engine, "task-manual")
    assert task["plan_id"] == "plan-A"
    assert task["guide_json"][MARKER_KEY]["plan_id"] == "plan-A"
    assert task["guide_json"][MARKER_KEY]["migration"] == "planlink_20260922"

    # downgrade 精确还原：清 plan_id + 剥标记
    run_migration(downgrade)
    task = _task(engine, "task-manual")
    assert task["plan_id"] is None
    assert MARKER_KEY not in task["guide_json"]


def test_skips_out_of_window_and_ambiguous_and_deleted(migration_env):
    """窗口外 / 多冲刺计划歧义 / 软删 / 非唯一域 → 全部不回填。"""
    engine, run_migration, load = migration_env
    upgrade, _ = load()

    # user-2：计划开始前的任务（窗口外）
    _seed_plan(
        engine, "plan-B", "user-2", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(engine, "task-before-plan", "user-2", created_at=NOW - timedelta(days=9))

    # user-3：两个 active SPRINT 计划（歧义）
    _seed_plan(
        engine, "plan-C1", "user-3", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_plan(
        engine, "plan-C2", "user-3", created_at=NOW - timedelta(days=6), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(engine, "task-ambiguous", "user-3", created_at=NOW - timedelta(days=2))

    # user-4：目标日期已过的 active 计划（窗口外——过期计划不吸收 target 之后的任务）
    _seed_plan(
        engine, "plan-D", "user-4", created_at=NOW - timedelta(days=30), target_date=NOW.date() - timedelta(days=1)
    )
    _seed_task(engine, "task-after-target", "user-4", created_at=NOW)

    # user-5：只有 goal plan（无 SPRINT）→ 迁移侧不回填
    _seed_plan(engine, "plan-E", "user-5", type_="GROWTH", created_at=NOW - timedelta(days=7))
    _seed_task(engine, "task-goal-only", "user-5", created_at=NOW - timedelta(days=2))

    # user-6：唯一 active SPRINT，但任务已软删
    _seed_plan(
        engine, "plan-F", "user-6", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(engine, "task-deleted", "user-6", created_at=NOW - timedelta(days=2), deleted_at=NOW - timedelta(days=1))

    run_migration(upgrade)

    for task_id in ("task-before-plan", "task-ambiguous", "task-after-target", "task-goal-only", "task-deleted"):
        task = _task(engine, task_id)
        assert task["plan_id"] is None, f"{task_id} 不应被回填"
        assert MARKER_KEY not in task["guide_json"], f"{task_id} 不应带回填标记"


def test_native_plan_tasks_survive_roundtrip_untouched(migration_env):
    """intake 等原生带 plan_id 的任务：upgrade/downgrade 全程原样存活。"""
    engine, run_migration, load = migration_env
    upgrade, downgrade = load()

    _seed_plan(
        engine, "plan-G", "user-7", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(
        engine,
        "task-intake-native",
        "user-7",
        plan_id="plan-G",
        created_at=NOW - timedelta(days=2),
        guide_json={"day_number": 3, "sprint_mode": "exam"},
    )

    run_migration(upgrade)
    task = _task(engine, "task-intake-native")
    assert task["plan_id"] == "plan-G"
    assert MARKER_KEY not in task["guide_json"]  # 原生任务不打标记

    run_migration(downgrade)
    task = _task(engine, "task-intake-native")
    assert task["plan_id"] == "plan-G"  # downgrade 不误伤
    assert task["guide_json"]["day_number"] == 3  # 业务键原样


def test_upgrade_is_idempotent_and_zero_new_tables(migration_env):
    """重复 upgrade 幂等；零 schema 变更（纯数据回填，不建平行真源）。"""
    engine, run_migration, load = migration_env
    upgrade, _ = load()

    _seed_plan(
        engine, "plan-H", "user-8", created_at=NOW - timedelta(days=7), target_date=NOW.date() + timedelta(days=7)
    )
    _seed_task(engine, "task-idem", "user-8", created_at=NOW - timedelta(days=2))

    before = set(inspect(engine).get_table_names())
    run_migration(upgrade)
    after_upgrade = set(inspect(engine).get_table_names())
    assert after_upgrade == before  # 零新表

    # 二次执行：不重复写标记、不报错
    run_migration(upgrade)
    task = _task(engine, "task-idem")
    assert task["plan_id"] == "plan-H"
    assert len(task["guide_json"].get(MARKER_KEY, {})) == 3  # 单份标记（plan_id/migration/backfilled_at）
