"""sqrejoin_20260923 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
sqrejoin_20260923_group_member_rejoin_unique 的 upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证 group_members 退队-重加入唯一键收口的 schema 变更：

- upgrade 预检通过（全列唯一约束下不可能有重复对）后，
  删除全列唯一约束 uq_group_member（软删行占键 → 退出即永久无法回归的根因），
  建活跃行部分唯一索引 uq_group_member_active
  （WHERE deleted_at IS NULL，与模型/全仓 not_deleted_filter 口径同域）；
- upgrade 后语义钉死：同组同用户第二行**活跃**行 INSERT 违约；活跃行 + 同键
  软删历史行共存合法（重加入的数据前提）；
- downgrade 还原全列唯一约束、删部分索引，round-trip 幂等可重入
  （还原前提：无同键多行，见迁移 docstring）；
- 预检 fail-loudly：schema 漂移（同键多行）时拒绝执行，不静默归并用户统计。

迁移语义（为什么是部分索引、为什么预检拒绝手术）见迁移文件 docstring 与
v3-output/SQUAD-REJOIN/REPORT.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "sqrejoin_20260923_group_member_rejoin_unique.py"

OLD_CONSTRAINT = "uq_group_member"
INDEX_NAME = "uq_group_member_active"

G1 = "11111111-1111-1111-1111-111111111111"
U1 = "22222222-2222-2222-2222-222222222222"
M1 = "33333333-3333-3333-3333-333333333333"
M2 = "44444444-4444-4444-4444-444444444444"

# 迁移前 schema：group_members（与生产同构的列集 + 命名全列唯一约束）。
BASE_DDL = f"""
CREATE TABLE group_members (
    id VARCHAR(36) PRIMARY KEY,
    group_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    role VARCHAR(32) NOT NULL,
    is_muted BOOLEAN NOT NULL,
    mute_until TIMESTAMP,
    warn_count INTEGER NOT NULL,
    notifications_enabled BOOLEAN NOT NULL,
    flame_contribution INTEGER NOT NULL,
    tasks_completed INTEGER NOT NULL,
    checkin_streak INTEGER NOT NULL,
    last_checkin_date TIMESTAMP,
    joined_at TIMESTAMP NOT NULL,
    last_active_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    CONSTRAINT {OLD_CONSTRAINT} UNIQUE (group_id, user_id)
)
"""


def _insert_member(conn, *, member_id: str, group: str, user: str, deleted: str | None) -> None:
    conn.exec_driver_sql(
        "INSERT INTO group_members "
        "(id, group_id, user_id, role, is_muted, warn_count, notifications_enabled, "
        " flame_contribution, tasks_completed, checkin_streak, joined_at, last_active_at, "
        " created_at, updated_at, deleted_at) "
        "VALUES (?, ?, ?, 'MEMBER', 0, 0, 1, 7, 0, 0, '2026-09-01 10:00:00', "
        "'2026-09-01 10:00:00', '2026-09-01 10:00:00', '2026-09-01 10:00:00', ?)",
        (member_id, group, user, deleted),
    )


def _load_upgrade_downgrade():
    spec = importlib.util.spec_from_file_location("sqrejoin_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.upgrade, module.downgrade


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'squad_rejoin_migration.db'}")

    def run_migration(op_fn) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DDL 亦在事务内），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    # 迁移前基座：带全列唯一约束的表 + 一个活跃成员行
    with engine.begin() as conn:
        conn.exec_driver_sql(BASE_DDL)
        _insert_member(conn, member_id=M1, group=G1, user=U1, deleted=None)

    yield engine, run_migration
    engine.dispose()


def _unique_index_names(engine) -> set[str]:
    inspector = inspect(engine)
    return {idx["name"] for idx in inspector.get_indexes("group_members") if idx.get("unique")}


def _unique_constraint_names(engine) -> set[str]:
    inspector = inspect(engine)
    return {uc["name"] for uc in inspector.get_unique_constraints("group_members") if uc.get("name")}


# ===========================================================================
# 1. upgrade：删全列唯一约束 → 建活跃行部分唯一索引（预检通过路径）
# ===========================================================================


def test_upgrade_drops_full_constraint_and_creates_partial_index(migration_env):
    engine, run_migration = migration_env
    upgrade, _ = _load_upgrade_downgrade()

    assert OLD_CONSTRAINT in _unique_constraint_names(engine)
    assert INDEX_NAME not in _unique_index_names(engine)

    run_migration(upgrade)

    assert OLD_CONSTRAINT not in _unique_constraint_names(engine), "全列唯一约束必须删除（软删行不再占键）"
    assert INDEX_NAME in _unique_index_names(engine), "活跃行部分唯一索引必须存在"


# ===========================================================================
# 2. upgrade 后语义：第二活跃行违约；活跃+软删历史行共存合法
# ===========================================================================


def test_post_upgrade_active_duplicate_rejected_and_rejoin_pair_allowed(migration_env):
    engine, run_migration = migration_env
    upgrade, _ = _load_upgrade_downgrade()
    run_migration(upgrade)

    with engine.begin() as conn:
        # 同键第二活跃行：违约（部分唯一索引仲裁并发首 join / 复活竞态）
        with pytest.raises(Exception):  # noqa: B017 —— sqlite 原生 IntegrityError 包装
            _insert_member(conn, member_id=M2, group=G1, user=U1, deleted=None)

    with engine.begin() as conn:
        # 重加入数据前提：活跃行 + 同键软删历史行共存合法（复活语义下行数恒 1，
        # 此处钉的是索引谓词不误伤软删历史行——外部工具可能留下的形态）
        _insert_member(conn, member_id=M2, group=G1, user=U1, deleted="2026-09-20 10:00:00")
        count = conn.execute(
            text("SELECT COUNT(*) FROM group_members WHERE group_id = :g AND user_id = :u"),
            {"g": G1, "u": U1},
        ).scalar()
        assert count == 2, "活跃行 + 软删历史行必须共存（谓词只管活跃行）"


# ===========================================================================
# 3. round-trip：downgrade 还原约束（无同键多行前提成立）、再 upgrade 可重入
# ===========================================================================


def test_round_trip_downgrade_restores_constraint_and_upgrade_reentrant(migration_env):
    engine, run_migration = migration_env
    upgrade, downgrade = _load_upgrade_downgrade()

    run_migration(upgrade)
    run_migration(downgrade)

    assert OLD_CONSTRAINT in _unique_constraint_names(engine)
    assert INDEX_NAME not in _unique_index_names(engine)
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM group_members")).scalar()
        assert count == 1, "round-trip 存量行存活"

    run_migration(upgrade)
    assert INDEX_NAME in _unique_index_names(engine)


# ===========================================================================
# 4. 预检 fail-loudly：schema 漂移（同键多行）时拒绝执行，不静默归并用户统计
# ===========================================================================


def test_upgrade_fails_loudly_on_schema_drift_duplicates(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'drift.db'}")
    # 漂移基座：无约束的裸表 + 同键两活跃行（模拟约束曾被人为移除的库）
    with engine.begin() as conn:
        conn.exec_driver_sql(
            BASE_DDL.replace(f",\n    CONSTRAINT {OLD_CONSTRAINT} UNIQUE (group_id, user_id)", "")
        )
        _insert_member(conn, member_id=M1, group=G1, user=U1, deleted=None)
        _insert_member(conn, member_id=M2, group=G1, user=U1, deleted=None)

    upgrade, _ = _load_upgrade_downgrade()
    with pytest.raises(RuntimeError, match="重复对"):
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                upgrade()
    engine.dispose()
