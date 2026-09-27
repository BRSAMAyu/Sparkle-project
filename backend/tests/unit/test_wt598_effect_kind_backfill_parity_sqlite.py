"""wt598_20260927 迁移在本地 sqlite 基座上的隔离重放 + 回填口径一致性（主库只读纪律）.

不连主库 PostgreSQL：用 alembic Operations/MigrationContext 把
wt598_20260927_mastery_audit_effect_kind 的 upgrade/downgrade 单独跑在
临时 sqlite 文件库上，钉住 V3-FIX-299 的两件事：

- **回填口径 = wt594 普查口径**（裁决材料 §1.1，live 394 行形状分布按比例
  复刻：12 payload 证据 / 100 exam-sprint set-point / 282 投影行）：
  ``reason LIKE 'evidence:%'`` → evidence；``exam_sprint_diagnostic`` /
  ``post_exam_review_weak_node`` → set_point；其余（task_complete、
  sprint_task_completed:*、错题本带后缀、offline_sync、客户端自由串）→
  projection；
- **回填口径 = 写点定性单点映射**（``mastery_evidence.classify_effect_kind``）：
  对覆盖全部写点词形的代表串逐条比对 SQL 回填结果与 Python 映射——同一
  账本不同时点重算不同（破坏幂等）的漂移风险在此钉死；
- upgrade/downgrade round-trip 可重入；已有非 NULL kind 的行不被回填覆写。

迁移语义背景见迁移文件 docstring 与 v3-output/WT594-SHADOW/adjudication.md。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from app.services.galaxy.mastery_evidence import classify_effect_kind

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "wt598_20260927_mastery_audit_effect_kind.py"

# 迁移前 schema：wt539_20260926 时点的 mastery_audit_log（无 effect_kind）
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


def _insert_audit(conn, reason: str, request_id: str | None = None, node: str = N) -> None:
    conn.exec_driver_sql(
        "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
        "VALUES (?, ?, 40, 42, ?, ?, 1)",
        (node, U, reason, request_id),
    )


def _seed_census_shape(conn) -> None:
    """按 wt594 普查（live 394 行 / 12 evidence + 100 set_point + 282 投影）
    的形状分布复刻存量账本。"""
    for _ in range(12):  # payload 证据行（全部 evidence:task_outcome，absorber 写）
        _insert_audit(conn, "evidence:task_outcome", "obs=60;conf=0.6")
    for _ in range(100):  # exam-sprint 绝对 set-point 行（咽喉写）
        _insert_audit(conn, "exam_sprint_diagnostic")
    # 282 投影行构成：task_complete 225 + sprint_task_completed 35 + 错题本 21 + probe 1
    for _ in range(225):
        _insert_audit(conn, "task_complete", "33333333-3333-3333-3333-333333333333")
    for _ in range(35):
        _insert_audit(conn, "sprint_task_completed:00000000-0000-0000-0000-000000000001")
    for reason in ("error_review:remembered", "error_diagnosis:knowledge_gap", "error_review:forgotten"):
        for _ in range(7):
            _insert_audit(conn, reason)
    _insert_audit(conn, "probe_inval_test")


@pytest.fixture(name="migration_env")
def _migration_env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'wt598_effect_kind_migration.db'}")

    with engine.begin() as conn:
        conn.exec_driver_sql(BASE_DDL)
        _seed_census_shape(conn)

    def run_migration(op_fn) -> None:
        # begin()：SQLAlchemy 2.x 无 commit 不落盘（DDL 亦在事务内），迁移必须在事务内执行
        with engine.begin() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                op_fn()

    def load_upgrade_downgrade():
        spec = importlib.util.spec_from_file_location("wt598_effect_kind_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.upgrade, module.downgrade

    yield engine, run_migration, load_upgrade_downgrade
    engine.dispose()


def _kind_counts(conn) -> dict[str, int]:
    rows = conn.execute(text("SELECT effect_kind, COUNT(*) FROM mastery_audit_log GROUP BY effect_kind")).all()
    return {str(kind): int(n) for kind, n in rows}


def _kinds_by_reason(conn, reason: str) -> list[str]:
    rows = conn.execute(
        text("SELECT effect_kind FROM mastery_audit_log WHERE reason = :r"),
        {"r": reason},
    ).all()
    return [str(row[0]) for row in rows]


def test_upgrade_backfills_census_shape_and_is_idempotent(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)

    with engine.connect() as conn:
        counts = _kind_counts(conn)
        assert counts.get("evidence") == 12, "普查：12 条 payload 证据行 → evidence"
        assert counts.get("set_point") == 100, "普查：100 条 exam-sprint 行 → set_point"
        assert counts.get("projection") == 282, "普查：282 条投影行（task_complete/sprint/错题本/probe）"
        assert sum(counts.values()) == 394
        assert None not in counts, "回填后不得残留 NULL kind"

    # 防御面：回填只管 NULL——显式 kind 不被覆写，回填语句可重入
    # （ADD COLUMN 的单次执行由 alembic 保证，与 erridemconc 同纪律）。
    spec = importlib.util.spec_from_file_location("wt598_effect_kind_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision, effect_kind) "
            "VALUES (?, ?, 40, 42, 'exam_sprint_diagnostic', NULL, 1, 'evidence')",
            (N, U),
        )
        conn.exec_driver_sql(
            "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
            "VALUES (?, ?, 40, 42, 'exam_sprint_diagnostic', NULL, 1)",
            (N, U),
        )
        for sql in (module.BACKFILL_EVIDENCE_SQL, module.BACKFILL_SET_POINT_SQL, module.BACKFILL_PROJECTION_SQL):
            conn.exec_driver_sql(sql)
    with engine.connect() as conn:
        counts_after = _kind_counts(conn)
        assert counts_after.get("evidence") == 13, "显式 kind 的行不被回填覆写"
        assert counts_after.get("set_point") == 101, "新增 NULL 行由可重入回填收敛"


def test_backfill_matches_single_point_write_side_mapping(migration_env):
    """回填 SQL 与写点定性单点映射（classify_effect_kind）逐词形同口径。"""
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    # 覆盖全部写点词形 + 伪造面
    reason_shapes = [
        "evidence:task_outcome",
        "evidence:quiz",
        "exam_sprint_diagnostic",
        "post_exam_review_weak_node",
        "task_complete",
        "sprint_task_completed:00000000-0000-0000-0000-000000000001",
        "error_diagnosis:knowledge_gap",
        "error_review:remembered",
        "offline_sync",
        "manual_update",
        "focus_session",
        "knowledge_service_increment",
        "community_knowledge_share_bonus",
        "aurora_completion_check_correct",
        "client-forged-free-string",
        "evidence-forged-free-string",
    ]
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM mastery_audit_log")
        for reason in reason_shapes:
            _insert_audit(conn, reason)

    run_migration(upgrade)

    with engine.connect() as conn:
        for reason in reason_shapes:
            expected = classify_effect_kind(reason).value
            actuals = set(_kinds_by_reason(conn, reason))
            assert actuals == {expected}, f"reason={reason!r}: SQL 回填 {actuals} ≠ 写点映射 {expected!r}"


def test_downgrade_round_trip_reentrant(migration_env):
    engine, run_migration, load_upgrade_downgrade = migration_env
    upgrade, downgrade = load_upgrade_downgrade()

    run_migration(upgrade)
    run_migration(downgrade)

    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(mastery_audit_log)").fetchall()}
        assert "effect_kind" not in columns
        assert int(conn.execute(text("SELECT COUNT(*) FROM mastery_audit_log")).scalar_one()) == 394, "存量行不丢"

    run_migration(upgrade)
    with engine.connect() as conn:
        counts = _kind_counts(conn)
        assert counts.get("evidence") == 12 and counts.get("set_point") == 100 and counts.get("projection") == 282
