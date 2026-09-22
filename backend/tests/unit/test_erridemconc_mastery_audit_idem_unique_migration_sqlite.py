"""erridemconc_20260922 迁移在本地 sqlite 基座上的隔离重放（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
erridemconc_20260922_mastery_audit_idem_unique 的 upgrade/downgrade 单独跑在
临时 sqlite 文件库上，验证 mastery_audit_log 幂等键唯一部分索引的 schema 变更：

- upgrade 收敛索引管辖域（edi:/erv:）内的存量重复三元组，保留最早一行
  （首个生效证据；后来者是并发双写落账的重复扣分污染）；
- 管辖域外的存量行（NULL request_id、裸 task_id、obs=/oc= 复合段、
  gRPC 客户端自由 request_id）一概不动——部分索引谓词外零影响；
- upgrade 后唯一部分索引存在且生效：同键二次 INSERT 违约、
  ON CONFLICT DO NOTHING RETURNING 丢行（写侧生产契约）；
- downgrade 后索引移除、存量行存活，round-trip 幂等可重入。

迁移语义（为什么是部分索引而不是全列唯一）见迁移文件 docstring 与
v3-output/ERR-IDEM-CONCUR/REPORT.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "erridemconc_20260922_mastery_audit_idem_unique.py"

INDEX_NAME = "uq_mastery_audit_log_idem_key"

# 迁移前 schema：c8e4f2a3b1d5 建的 mastery_audit_log 裸表（无唯一索引）
BASE_DDL = """
CREATE TABLE mastery_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    old_mastery INTEGER NOT NULL,
    new_mastery INTEGER NOT NULL,
    reason VARCHAR(100) NOT NULL,
    request_id VARCHAR(100),
    revision INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

U = "11111111-1111-1111-1111-111111111111"
N = "22222222-2222-2222-2222-222222222222"


def _insert_audit(conn, request_id, old=50, new=42, user=U, node=N):
    conn.exec_driver_sql(
        "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
        "VALUES (?, ?, ?, ?, 'error_diagnosis:concept_confusion', ?, 1)",
        (node, user, old, new, request_id),
    )


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'erridem_conc_migration.db'}")

    # 迁移前基座：c8e4f2a3b1d5 裸表 + 存量行（含索引管辖域内的重复对）
    with engine.begin() as conn:
        conn.exec_driver_sql(BASE_DDL)
        # 管辖域内：edi: 重复三元组（旧 50->42 生效在前，42->34 双扣污染在后）
        _insert_audit(conn, "edi:aaaa00000000000000000000000000:d90c7fa3:" + "2" * 32, 50, 42)
        _insert_audit(conn, "edi:aaaa00000000000000000000000000:d90c7fa3:" + "2" * 32, 42, 34)
        # 管辖域内：erv: 重复三元组
        _insert_audit(conn, "erv:bbbb00000000000000000000000000:d90c7fa3:remembered:" + "2" * 32, 42, 46)
        _insert_audit(conn, "erv:bbbb00000000000000000000000000:d90c7fa3:remembered:" + "2" * 32, 46, 50)
        # 管辖域内：唯一行（必须存活）
        _insert_audit(conn, "edi:cccc00000000000000000000000000:ab12cd34:" + "3" * 32, 50, 42)
        # 管辖域外：一律不动
        _insert_audit(conn, None, 40, 44, user=U, node=N)                                    # NULL
        _insert_audit(conn, "77777777-7777-7777-7777-777777777777", 60, 64)                  # 裸 task_id
        _insert_audit(conn, "obs=60;conf=0.8;oc=" + "4" * 32, 64, 68)                        # obs= 复合段
        _insert_audit(conn, "client-free-string", 68, 72)                                    # gRPC 自由串
        # 管辖域外：已存在的重复三元组（演示库实测 3 组旧格式 double-write）
        _insert_audit(conn, "99999999-9999-9999-9999-999999999999", 70, 74)                  # 裸 task_id 重复对
        _insert_audit(conn, "99999999-9999-9999-9999-999999999999", 74, 78)

    def run_migration(op_fn) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DDL 亦在事务内），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("erridemconc_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _index_names(engine) -> set[str]:
    insp = inspect(engine)
    return {idx["name"] for idx in insp.get_indexes("mastery_audit_log")}


def _scoped_rows(engine):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT old_mastery, new_mastery FROM mastery_audit_log "
                "WHERE request_id LIKE 'edi:%' OR request_id LIKE 'erv:%' ORDER BY id"
            )
        ).fetchall()


def test_upgrade_dedupes_idem_namespace_keeping_earliest(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    # 迁移前：管辖域内 5 行（两组重复对 + 一行唯一）
    assert len(_scoped_rows(engine)) == 5

    run_migration(upgrade)

    # 重复收敛：每组保留最早一行；被删的是后来者（重复扣分/回升污染）
    rows = _scoped_rows(engine)
    assert [tuple(r) for r in rows] == [(50, 42), (42, 46), (50, 42)], "保留最早、删除后来者"
    assert INDEX_NAME in _index_names(engine)


def test_upgrade_leaves_out_of_scope_rows_untouched(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    run_migration(upgrade)

    with engine.connect() as conn:
        total_scoped = conn.execute(
            text("SELECT COUNT(*) FROM mastery_audit_log WHERE request_id IS NULL")
        ).scalar()
        bare = conn.execute(
            text(
                "SELECT COUNT(*) FROM mastery_audit_log WHERE request_id = '99999999-9999-9999-9999-999999999999'"
            )
        ).scalar()
        others = conn.execute(
            text(
                "SELECT COUNT(*) FROM mastery_audit_log WHERE request_id LIKE 'obs=%' "
                "OR request_id = 'client-free-string'"
            )
        ).scalar()
    # 管辖域外零影响：NULL/复合段行原样；域外既有重复对也不收敛（索引管不着）
    assert total_scoped == 1
    assert bare == 2, "域外重复对不属于本索引管辖，收敛不是本迁移的职责"
    assert others == 2


def test_upgrade_enforces_uniqueness_and_on_conflict_contract(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, _ = load_upgrade_downgrade()

    run_migration(upgrade)

    with engine.begin() as conn:
        # 同键裸 INSERT 违约
        with pytest.raises(Exception):
            _insert_audit(conn, "edi:cccc00000000000000000000000000:ab12cd34:" + "3" * 32, 42, 34)
    # 写侧生产契约：ON CONFLICT DO NOTHING RETURNING 丢行（galaxy_service 同款）
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
                "VALUES (:n, :u, :o, :w, 'r', :q, 1) ON CONFLICT DO NOTHING RETURNING id"
            ),
            {
                "n": N, "u": U, "o": 42, "w": 34,
                "q": "edi:cccc00000000000000000000000000:ab12cd34:" + "3" * 32,
            },
        )
        assert result.scalar_one_or_none() is None, "冲突时 RETURNING 必须无行（写侧据此判定 duplicate）"
    # 非管辖域重复写不受索引约束
    with engine.begin() as conn:
        _insert_audit(conn, "88888888-8888-8888-8888-888888888888", 80, 84)
        _insert_audit(conn, "88888888-8888-8888-8888-888888888888", 84, 88)  # 不违约


def test_round_trip_downgrade_and_reentrant(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)
    assert INDEX_NAME in _index_names(engine)
    scoped_after_upgrade = _scoped_rows(engine)

    run_migration(downgrade)
    assert INDEX_NAME not in _index_names(engine)
    # downgrade 不回填被收敛的污染行；存量数据行原样存活
    assert _scoped_rows(engine) == scoped_after_upgrade

    # 可重入：再次 upgrade 幂等（无重复可删 + IF NOT EXISTS）
    run_migration(upgrade)
    assert INDEX_NAME in _index_names(engine)
    assert _scoped_rows(engine) == scoped_after_upgrade
