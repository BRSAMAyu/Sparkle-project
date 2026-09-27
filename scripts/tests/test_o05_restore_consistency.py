#!/usr/bin/env python3
"""O-05 · restore_consistency_check 单测（V3-FIX-504/505 修复面）.

Run:  backend/.venv/bin/python -m unittest scripts.tests.test_o05_restore_consistency -v
（或直接：backend/.venv/bin/python scripts/tests/test_o05_restore_consistency.py）

钉两层：
1. 校验器不变量在 sqlite 内存库上的 PASS / FAIL 双路径（红证：坏数据必须被
   抓住；绿证：合法快照必须通过）；
2. backup/restore 脚本契约：--clean --if-exists 转储、ON_ERROR_STOP、
   redis CONFIG dir 感知、MinIO 无容器内 tar 依赖、config 覆盖面
   （V3-FIX-504/505 回归钉——脚本回退到旧通路即红）。

零真实库连接、零 DATABASE_URL 依赖（sqlite 内存库；不触碰演示库）。
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_CHECKER_PATH = _SCRIPTS_DIR / "restore_consistency_check.py"

try:
    import sqlalchemy  # noqa: F401

    _HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover
    _HAS_SQLALCHEMY = False

_spec = importlib.util.spec_from_file_location("restore_consistency_check", _CHECKER_PATH)
assert _spec is not None and _spec.loader is not None, "无法加载 restore_consistency_check 模块"
checker = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("restore_consistency_check", checker)
_spec.loader.exec_module(checker)


# ---------------------------------------------------------------------------
# sqlite 内存库 schema（与生产列形状对齐的最小子集；sqlite 无 uuid/JSONB 用 TEXT）
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE users (id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT);
CREATE TABLE agent_runs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    intent_id TEXT,
    kind TEXT,
    status TEXT,
    terminal_reason TEXT,
    wait_kind TEXT,
    heartbeat_at TEXT,
    attempt INTEGER DEFAULT 1
);
CREATE TABLE agent_run_transitions (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    from_status TEXT,
    to_status TEXT,
    event_name TEXT,
    actor TEXT,
    occurred_at TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE event_sequence_counters (
    aggregate_type TEXT,
    aggregate_id TEXT,
    next_sequence INTEGER,
    PRIMARY KEY (aggregate_type, aggregate_id)
);
CREATE TABLE event_outbox (
    id TEXT PRIMARY KEY,
    aggregate_type TEXT,
    aggregate_id TEXT,
    event_type TEXT,
    sequence_number INTEGER,
    payload TEXT,
    metadata TEXT,
    created_at TEXT,
    published_at TEXT
);
CREATE TABLE processed_events (
    event_id TEXT,
    consumer_group TEXT,
    processed_at TEXT,
    PRIMARY KEY (event_id, consumer_group)
);
CREATE TABLE episodic_memories (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    summary TEXT,
    archived_at TEXT,
    retracted_at TEXT,
    revoked_at TEXT
);
CREATE TABLE memory_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    pref_key TEXT,
    archived_at TEXT,
    retracted_at TEXT
);
"""

_U1 = "11111111-1111-4111-8111-111111111111"

_RUN1_TRANSITIONS = [
    ("t1", None, "QUEUED", "run.created", "00:01"),
    ("t2", "QUEUED", "RUNNING", "run.status_changed", "00:02"),
    ("t3", "RUNNING", "EXECUTING", "run.status_changed", "00:03"),
    ("t4", "EXECUTING", "SUCCEEDED", "run.status_changed", "00:04"),
]


def _seed_valid_snapshot(db: sqlite3.Connection) -> None:
    """合法快照种子：与 v3-output/WT773-O05 演练种子同构（真词表）。"""
    db.execute("INSERT INTO users (id) VALUES (?)", (_U1,))
    # run1: SUCCEEDED 终态带归因；迁移链与状态行一致
    db.execute(
        "INSERT INTO agent_runs (id, user_id, kind, status, terminal_reason, heartbeat_at) VALUES (?,?,?,?,?,?)",
        ("r1", _U1, "execution", "SUCCEEDED", "completed", "2026-09-27T00:00:00"),
    )
    for tid, src, dst, event, at in _RUN1_TRANSITIONS:
        db.execute(
            "INSERT INTO agent_run_transitions (id, run_id, from_status, to_status, event_name, actor, occurred_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (tid, "r1", src, dst, event, "system", f"2026-09-27T{at}:00"),
        )
    # run2: RUNNING 活跃态（无终态归因要求），同 intent 唯一
    db.execute(
        "INSERT INTO agent_runs (id, user_id, kind, status, heartbeat_at) VALUES (?,?,?,?,?)",
        ("r2", _U1, "execution", "RUNNING", "2026-09-27T00:00:00"),
    )
    db.execute(
        "INSERT INTO agent_run_transitions (id, run_id, from_status, to_status, event_name, actor, occurred_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("t5", "r2", None, "QUEUED", "run.created", "system", "2026-09-27T00:01:00"),
    )
    db.execute(
        "INSERT INTO agent_run_transitions (id, run_id, from_status, to_status, event_name, actor, occurred_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("t6", "r2", "QUEUED", "RUNNING", "run.status_changed", "system", "2026-09-27T00:02:00"),
    )
    # outbox：已发布 1 + 待发布 1；计数器领先已发行最大序号
    db.execute(
        "INSERT INTO event_outbox (id, aggregate_type, aggregate_id, event_type, sequence_number, payload, created_at, published_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        ("o1", "agent_run", "r1", "run.created", 1, "{}", "2026-09-27T00:00:00", "2026-09-27T00:00:30"),
    )
    db.execute(
        "INSERT INTO event_outbox (id, aggregate_type, aggregate_id, event_type, sequence_number, payload, created_at, published_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        ("o2", "agent_run", "r2", "run.created", 1, "{}", "2026-09-27T00:00:00", None),
    )
    for agg in ("r1", "r2"):
        db.execute(
            "INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence) VALUES (?,?,?)",
            ("agent_run", agg, 2),
        )
    # memory：1 可召回 + archived/retracted 墓碑各 1（"无已删 memory 复活"判据面）
    db.execute("INSERT INTO episodic_memories (id, user_id, summary) VALUES (?,?,?)", ("m1", _U1, "active"))
    db.execute(
        "INSERT INTO episodic_memories (id, user_id, summary, archived_at) VALUES (?,?,?,?)",
        ("m2", _U1, "archived", "2026-09-26T00:00:00"),
    )
    db.execute(
        "INSERT INTO episodic_memories (id, user_id, summary, retracted_at) VALUES (?,?,?,?)",
        ("m3", _U1, "retracted", "2026-09-25T00:00:00"),
    )
    db.execute("INSERT INTO memory_preferences (id, user_id, pref_key) VALUES (?,?,?)", ("p1", _U1, "study_time"))
    db.execute(
        "INSERT INTO processed_events (event_id, consumer_group, processed_at) VALUES (?,?,?)",
        ("evt_x", "gj03", "2026-09-27T00:00:00"),
    )
    db.commit()


@unittest.skipUnless(_HAS_SQLALCHEMY, "sqlalchemy 不可用（非 backend venv）")
class InvariantGreenPathTest(unittest.TestCase):
    """绿路径：合法快照必须全过。"""

    def setUp(self) -> None:
        self.raw = sqlite3.connect(":memory:")
        self.raw.executescript(_DDL)
        _seed_valid_snapshot(self.raw)
        engine = sqlalchemy.create_engine("sqlite://", creator=lambda: self.raw)
        self.conn = engine.connect()
        self.addCleanup(self.raw.close)  # 先注册：cleanup LIFO → 连接先关、裸库后关
        self.addCleanup(self.conn.close)

    def test_all_structural_invariants_pass(self) -> None:
        for check in (
            checker.check_run_status_vocabulary,
            checker.check_run_transition_projection,
            checker.check_active_run_uniqueness,
            checker.check_outbox_sequence_monotonic,
            checker.check_memory_tombstones,
            checker.check_foreign_key_orphans,
        ):
            finding = check(self.conn)
            self.assertTrue(finding.ok, f"{finding.invariant} 应 PASS: {finding.violations}")

    def test_baseline_roundtrip_passes(self) -> None:
        baseline = checker.capture_baseline(self.conn)
        self.assertEqual(baseline["episodic_recallable"], 1)
        self.assertEqual(baseline["outbox_published"], 1)
        self.assertEqual(baseline["outbox_total"], 2)
        self.assertEqual(baseline["processed_events_total"], 1)
        finding = checker.check_snapshot_equality(self.conn, baseline)
        self.assertTrue(finding.ok, finding.violations)


@unittest.skipUnless(_HAS_SQLALCHEMY, "sqlalchemy 不可用（非 backend venv）")
class InvariantRedPathTest(unittest.TestCase):
    """红路径：恢复缺陷的典型形状必须被对应不变量抓住。"""

    def setUp(self) -> None:
        self.raw = sqlite3.connect(":memory:")
        self.raw.executescript(_DDL)
        _seed_valid_snapshot(self.raw)
        engine = sqlalchemy.create_engine("sqlite://", creator=lambda: self.raw)
        self.conn = engine.connect()
        self.addCleanup(self.raw.close)  # 先注册：cleanup LIFO → 连接先关、裸库后关
        self.addCleanup(self.conn.close)

    def test_illegal_status_vocabulary_red(self) -> None:
        # 旧词表残留（COMPLETED 不是封闭词表成员）
        self.raw.execute("UPDATE agent_runs SET status='COMPLETED' WHERE id='r1'")
        self.raw.commit()
        finding = checker.check_run_status_vocabulary(self.conn)
        self.assertFalse(finding.ok)
        self.assertTrue(any("COMPLETED" in v for v in finding.violations))

    def test_terminal_without_reason_red(self) -> None:
        self.raw.execute("UPDATE agent_runs SET terminal_reason=NULL WHERE id='r1'")
        self.raw.commit()
        finding = checker.check_run_status_vocabulary(self.conn)
        self.assertFalse(finding.ok)
        self.assertTrue(any("terminal_reason" in v for v in finding.violations))

    def test_status_projection_drift_red(self) -> None:
        # 备份后状态推进残留：状态行与 append-only 迁移链末条脱节
        self.raw.execute("UPDATE agent_runs SET status='EXECUTING' WHERE id='r1'")
        self.raw.commit()
        finding = checker.check_run_transition_projection(self.conn)
        self.assertFalse(finding.ok)
        self.assertTrue(any("r1" in v for v in finding.violations))

    def test_counter_rollback_red(self) -> None:
        # 计数器回填：计数器低于已发行最大序号，新事件将与历史撞号
        # （upsert 语义：计数器行值 = 最近已分配序号；与 max_seq 相等是稳态）
        self.raw.execute(
            "INSERT INTO event_outbox (id, aggregate_type, aggregate_id, event_type, sequence_number, payload, created_at, published_at)"
            " VALUES ('o3', 'agent_run', 'r1', 'run.status_changed', 2, '{}', '2026-09-27T00:05:00', NULL)"
        )
        self.raw.execute("UPDATE event_sequence_counters SET next_sequence=1 WHERE aggregate_id='r1'")
        self.raw.commit()
        finding = checker.check_outbox_sequence_monotonic(self.conn)
        self.assertFalse(finding.ok)
        self.assertTrue(any("next_sequence=1" in v for v in finding.violations))

    def test_counter_steady_state_equal_passes(self) -> None:
        # 稳态：计数器 == 已发行 max_seq（live 写入路径的常态，不得误报）
        self.raw.execute(
            "INSERT INTO event_outbox (id, aggregate_type, aggregate_id, event_type, sequence_number, payload, created_at, published_at)"
            " VALUES ('o3', 'agent_run', 'r1', 'run.status_changed', 2, '{}', '2026-09-27T00:05:00', NULL)"
        )
        self.raw.execute("UPDATE event_sequence_counters SET next_sequence=2 WHERE aggregate_id='r1'")
        self.raw.commit()
        finding = checker.check_outbox_sequence_monotonic(self.conn)
        self.assertTrue(finding.ok, finding.violations)

    def test_tombstone_resurrection_red(self) -> None:
        # "已删 memory 复活"形状：墓碑被清 → 可召回面计数偏离基线
        baseline = checker.capture_baseline(self.conn)
        self.raw.execute("UPDATE episodic_memories SET archived_at=NULL WHERE id='m2'")
        self.raw.commit()
        finding = checker.check_snapshot_equality(self.conn, baseline)
        self.assertFalse(finding.ok)
        self.assertTrue(any("episodic_recallable" in v for v in finding.violations))

    def test_ghost_rows_red(self) -> None:
        # 备份后新增行残留（合并恢复的 ghost 形状）
        baseline = checker.capture_baseline(self.conn)
        self.raw.execute(
            "INSERT INTO episodic_memories (id, user_id, summary) VALUES ('m-ghost', ?, 'drift')",
            (_U1,),
        )
        self.raw.commit()
        finding = checker.check_snapshot_equality(self.conn, baseline)
        self.assertFalse(finding.ok)
        self.assertTrue(any("episodic_memories" in v for v in finding.violations))

    def test_active_run_duplication_red(self) -> None:
        # 同 intent 出现第二个非终态 run（部分唯一索引失守形状）
        self.raw.execute("UPDATE agent_runs SET intent_id='i1' WHERE id='r2'")
        self.raw.execute(
            "INSERT INTO agent_runs (id, user_id, kind, status, intent_id, heartbeat_at) VALUES (?,?,?,?,?,?)",
            ("r3", _U1, "execution", "RUNNING", "i1", "2026-09-27T00:00:00"),
        )
        self.raw.commit()
        finding = checker.check_active_run_uniqueness(self.conn)
        self.assertFalse(finding.ok)

    def test_orphan_transitions_red(self) -> None:
        self.raw.execute(
            "INSERT INTO agent_run_transitions (id, run_id, from_status, to_status, event_name, actor, occurred_at)"
            " VALUES ('t-orphan', 'no-such-run', NULL, 'QUEUED', 'run.created', 'system', '2026-09-27T00:00:00')"
        )
        self.raw.commit()
        finding = checker.check_foreign_key_orphans(self.conn)
        self.assertFalse(finding.ok)
        self.assertTrue(any("agent_run_transitions.run_id" in v for v in finding.violations))


class EmbeddedVocabularySyncTest(unittest.TestCase):
    """embedded fallback 词表必须与冻结真源逐字一致。"""

    def test_vocabulary_matches_frozen_source(self) -> None:
        try:
            backend_dir = str(_SCRIPTS_DIR.parent / "backend")
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            from app.core.run_state_machine import RunStatus, terminal_reason_vocabulary
        except Exception:  # pragma: no cover
            self.skipTest("app.core.run_state_machine 不可导入（非 checkout 布局）")
        self.assertEqual(checker.RUN_STATUS_VOCABULARY, frozenset(s.value for s in RunStatus))
        self.assertEqual(checker.TERMINAL_REASON_VOCABULARY, frozenset(terminal_reason_vocabulary))
        self.assertNotIn("COMPLETED", checker.RUN_STATUS_VOCABULARY)
        self.assertIn("SUCCEEDED", checker.TERMINAL_STATUSES)


class ScriptContractTest(unittest.TestCase):
    """V3-FIX-504/505 修复面回归钉：脚本回退旧通路即红。"""

    def test_backup_script_contract(self) -> None:
        backup = (_SCRIPTS_DIR / "backup_prod_data.sh").read_text(encoding="utf-8")
        self.assertIn("--clean --if-exists", backup, "pg_dump 必须带 --clean --if-exists（快照语义）")
        self.assertIn("minio-data.tar.gz", backup, "MinIO 归档产物名保持稳定（restore 兼容）")
        self.assertIsNone(
            re.search(r'docker exec "\$\{MINIO_CONTAINER\}".*tar -C', backup),
            "MinIO 官方镜像无 tar——禁止容器内 tar 通路（V3-FIX-504）",
        )
        self.assertIn("config/env", backup, "config 覆盖面：.env 必须随包（chmod 600）")
        self.assertIn("alembic_head", backup, "manifest 必须带 alembic 版本戳")

    def test_restore_script_contract(self) -> None:
        restore = (_SCRIPTS_DIR / "restore_prod_data.sh").read_text(encoding="utf-8")
        self.assertIn("ON_ERROR_STOP=1", restore, "restore 必须开 ON_ERROR_STOP（假成功禁令）")
        self.assertIn("pg_terminate_backend", restore, "恢复前必须排空目标库连接")
        self.assertIn("CONFIG GET dir", restore, "redis 恢复必须按服务器 CONFIG dir 落盘（V3-FIX-505）")
        self.assertGreaterEqual(restore.count("docker restart"), 2, "redis 与 minio 恢复后都必须重启生效")
        self.assertIn("STRICT_SCHEMA", restore, "schema 代差校验开关必须在位")


if __name__ == "__main__":
    unittest.main()
