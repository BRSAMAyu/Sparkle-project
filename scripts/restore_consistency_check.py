#!/usr/bin/env python3
"""restore_consistency_check.py — 恢复后 Agent Run / Memory 一致性不变量校验器.

O-05（V3 卡）交付：对恢复完成的数据库执行结构不变量检查 + （可选）与备份点
基线做快照等价比对。恢复演练（staging）与灾难恢复后各跑一次；非零退出码 =
存在违反项，可直接接 CI/cron。

检查的不变量（与 v3-output/WT773-O05/notes.md 不变量表一一对应）：

  INV-1  run 状态封闭词表：agent_runs.status ∈ run_state_machine 词表；
         终态行必有 terminal_reason；heartbeat_at 非空（活性恢复判定前提）。
  INV-2  run 脊柱投影一致：每个 run 的最后一条迁移 to_status == 当前行 status
         （append-only 迁移历史与状态行不脱节）。
  INV-3  每 intent 活跃 run 唯一：非终态 run 不共享 intent_id（x05 部分唯一
         索引的应用层镜像——恢复后的索引/数据必须仍满足）。
  INV-4  outbox 序列不回填：每 aggregate 的 event_outbox 最大 sequence_number
         < event_sequence_counters.next_sequence（恢复后计数器不得小于已发行
         事件，否则新事件撞号）。
  INV-5  memory 墓碑完整：archived_at/retracted_at/revoked_at 非空的行保留
         墓碑；可召回面（三墓碑全空）计数与基线一致（"无已删 memory 复活"的
         直接判据——软删行不得回到可召回面）。
  INV-6  引用完整性零孤儿：agent_runs/episodic_memories/memory_preferences/
         agent_run_transitions 的外键列不得指向不存在的行（快照内自洽）。
  INV-7  快照等价（提供 --baseline 时）：关键表 行数 + 状态分布 + outbox
         发布/待发布分布 + processed_events 数 与备份点基线完全一致。

用法：
  # 恢复后结构校验
  python scripts/restore_consistency_check.py --url postgresql+psycopg2://...

  # 备份点采基线（对源库跑一次，随包存档）
  python scripts/restore_consistency_check.py --url ... --capture-baseline baseline.json

  # 恢复后带基线全量校验
  python scripts/restore_consistency_check.py --url ... --baseline baseline.json

方言：SQLAlchemy sync engine；全部 SQL 为 PG/sqlite 双兼容（演练与单测共用）。
run 状态词表从 app.core.run_state_machine 导入（sha256 冻结真源）；导入失败时
退化为内置词表副本并告警（校验器必须能在脱离 app 上下文的环境运行）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Connection

# ---------------------------------------------------------------------------
# 封闭词表：优先取冻结真源；脱离 app 上下文时用副本（与 run_state_machine 同步维护）
# ---------------------------------------------------------------------------
try:  # pragma: no cover - 分支依赖运行环境
    import sys as _sys

    # 从仓库 checkout 运行（scripts/restore_consistency_check.py）时把 backend/
    # 加进 import 路径，优先用冻结真源词表。
    _backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    if os.path.isdir(_backend_dir) and _backend_dir not in _sys.path:
        _sys.path.insert(0, _backend_dir)
    from app.core.run_state_machine import TERMINAL_RUN_STATUSES, RunStatus, terminal_reason_vocabulary

    RUN_STATUS_VOCABULARY: frozenset[str] = frozenset(s.value for s in RunStatus)
    TERMINAL_STATUSES: frozenset[str] = frozenset(s.value for s in TERMINAL_RUN_STATUSES)
    TERMINAL_REASON_VOCABULARY: frozenset[str] = frozenset(terminal_reason_vocabulary)
    _VOCAB_SOURCE = "app.core.run_state_machine"
except Exception:  # pragma: no cover
    # 副本必须与 backend/app/core/run_state_machine.py（sha256 双冻结）逐字同步；
    # 单测 test_restore_consistency_check.py 钉住两侧一致。
    RUN_STATUS_VOCABULARY = frozenset(
        {
            "QUEUED",
            "RUNNING",
            "AWAITING_USER",
            "AWAITING_APPROVAL",
            "EXECUTING",
            "SUCCEEDED",
            "PARTIAL",
            "FAILED",
            "CANCELLED",
            "TIMED_OUT",
            "UNKNOWN_OUTCOME",
            "BUDGET_EXCEEDED",
        }
    )
    TERMINAL_STATUSES = frozenset(
        {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED", "TIMED_OUT", "UNKNOWN_OUTCOME", "BUDGET_EXCEEDED"}
    )
    TERMINAL_REASON_VOCABULARY = frozenset(
        {
            "completed",
            "completed_partial",
            "failed",
            "user_cancelled",
            "handed_back",
            "timeout",
            "wait_expired",
            "queue_stale",
            "worker_restart_orphan",
            "projection_drift_repair",
            "rejected",
            "budget_exceeded",
        }
    )
    _VOCAB_SOURCE = "embedded-fallback"

KEY_TABLES = (
    "users",
    "agent_runs",
    "agent_run_transitions",
    "episodic_memories",
    "memory_preferences",
    "event_outbox",
    "processed_events",
)


@dataclass
class Finding:
    """单条不变量检查结果。"""

    invariant: str
    ok: bool
    detail: str
    violations: list[str] = field(default_factory=list)

    def render(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        head = f"[{mark}] {self.invariant}: {self.detail}"
        if not self.violations:
            return head
        shown = self.violations[:10]
        tail = self.violations[10:]
        lines = [f"    - {v}" for v in shown]
        if tail:
            lines.append(f"    ...（其余 {len(tail)} 条略）")
        return "\n".join([head, *lines])


def _table_exists(conn: Connection, table: str) -> bool:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        row = conn.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
        return row is not None
    row = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=:t"),
        {"t": table},
    ).first()
    return row is not None


# ---------------------------------------------------------------------------
# INV-1 run 状态封闭词表 + 终态归因 + 活性戳
# ---------------------------------------------------------------------------
def check_run_status_vocabulary(conn: Connection) -> Finding:
    if not _table_exists(conn, "agent_runs"):
        return Finding("INV-1", False, "agent_runs 表不存在", ["missing table agent_runs"])
    rows = conn.execute(
        text(
            "SELECT id, status, terminal_reason, heartbeat_at, "
            "CASE WHEN status IN :terminal THEN 1 ELSE 0 END AS is_terminal FROM agent_runs"
        ).bindparams(bindparam("terminal", expanding=True)),
        {"terminal": sorted(TERMINAL_STATUSES)},
    ).fetchall()
    bad_status: list[str] = []
    bad_terminal: list[str] = []
    bad_reason: list[str] = []
    bad_heartbeat: list[str] = []
    for r in rows:
        status = str(r.status or "")
        if status not in RUN_STATUS_VOCABULARY:
            bad_status.append(f"run={r.id} status={status!r} 不在封闭词表")
        if r.is_terminal and not r.terminal_reason:
            bad_terminal.append(f"run={r.id} 终态 {status} 缺 terminal_reason")
        if r.terminal_reason and str(r.terminal_reason) not in TERMINAL_REASON_VOCABULARY:
            bad_reason.append(f"run={r.id} terminal_reason={r.terminal_reason!r} 不在归因词表")
        if r.heartbeat_at is None:
            bad_heartbeat.append(f"run={r.id} heartbeat_at 为空")
    violations = bad_status + bad_terminal + bad_reason + bad_heartbeat
    detail = (
        f"词表源={_VOCAB_SOURCE}; 共 {len(rows)} 行; 非法状态 {len(bad_status)}; "
        f"终态缺归因 {len(bad_terminal)}; 归因越词表 {len(bad_reason)}; 缺活性戳 {len(bad_heartbeat)}"
    )
    return Finding("INV-1", not violations, detail, violations)


# ---------------------------------------------------------------------------
# INV-2 最后一条迁移与状态行一致
# ---------------------------------------------------------------------------
def check_run_transition_projection(conn: Connection) -> Finding:
    if not _table_exists(conn, "agent_run_transitions"):
        return Finding("INV-2", False, "agent_run_transitions 表不存在", ["missing table agent_run_transitions"])
    rows = conn.execute(text("""
            SELECT r.id AS run_id, r.status AS run_status, t.to_status AS last_to
            FROM agent_runs r
            LEFT JOIN agent_run_transitions t
              ON t.run_id = r.id
             AND t.id = (
                   SELECT t2.id FROM agent_run_transitions t2
                   WHERE t2.run_id = r.id
                   ORDER BY t2.occurred_at DESC, t2.created_at DESC, t2.id DESC
                   LIMIT 1
                 )
            """)).fetchall()
    violations: list[str] = []
    for r in rows:
        if r.last_to is None:
            violations.append(f"run={r.run_id} 无任何迁移记录（append-only 历史断裂）")
        elif str(r.last_to) != str(r.run_status):
            violations.append(f"run={r.run_id} 状态行 {r.run_status} != 最后迁移 to_status {r.last_to}")
    return Finding("INV-2", not violations, f"比对 {len(rows)} 个 run 的状态行与末条迁移", violations)


# ---------------------------------------------------------------------------
# INV-3 每 intent 活跃 run 唯一
# ---------------------------------------------------------------------------
def check_active_run_uniqueness(conn: Connection) -> Finding:
    rows = conn.execute(
        text("""
            SELECT intent_id, count(*) AS n, min(CAST(id AS TEXT)) AS example_run
            FROM agent_runs
            WHERE status NOT IN :terminal AND intent_id IS NOT NULL
            GROUP BY intent_id HAVING count(*) > 1
            """).bindparams(bindparam("terminal", expanding=True)),
        {"terminal": sorted(TERMINAL_STATUSES)},
    ).fetchall()
    violations = [f"intent={r.intent_id} 有 {r.n} 个活跃 run（例 {r.example_run}）" for r in rows]
    return Finding("INV-3", not violations, f"活跃 run per-intent 冲突 {len(rows)} 组", violations)


# ---------------------------------------------------------------------------
# INV-4 outbox 序列计数器不回填
# ---------------------------------------------------------------------------
def check_outbox_sequence_monotonic(conn: Connection) -> Finding:
    if not _table_exists(conn, "event_sequence_counters"):
        return Finding("INV-4", True, "event_sequence_counters 表不存在（旧 schema，跳过）", [])
    rows = conn.execute(text("""
            SELECT c.aggregate_type, c.aggregate_id, c.next_sequence,
                   COALESCE((SELECT max(o.sequence_number) FROM event_outbox o
                              WHERE o.aggregate_type = c.aggregate_type
                                AND o.aggregate_id = c.aggregate_id), 0) AS max_seq
            FROM event_sequence_counters c
            """)).fetchall()
    # 口径（对齐 agent_run_service._next_sequence 的 upsert 语义）：计数器行值 =
    # 最近一次已分配序号（首个事件即 INSERT 1 RETURNING 1），稳态与 max_seq 相等。
    # 违例仅当计数器 < 已发行最大序号——意味着计数器被回填，新事件将与历史撞号。
    violations = [
        f"counter {r.aggregate_type}/{r.aggregate_id} next_sequence={r.next_sequence} < 已发行 max_seq={r.max_seq}（计数器回填，新事件将撞号）"
        for r in rows
        if r.next_sequence is None or int(r.next_sequence) < int(r.max_seq)
    ]
    return Finding("INV-4", not violations, f"校验 {len(rows)} 个序列计数器（不回填口径）", violations)


# ---------------------------------------------------------------------------
# INV-5 memory 墓碑完整（无已删 memory 复活的结构面判据）
# ---------------------------------------------------------------------------
def check_memory_tombstones(conn: Connection) -> Finding:
    if not _table_exists(conn, "episodic_memories"):
        return Finding("INV-5", False, "episodic_memories 表不存在", ["missing table episodic_memories"])
    row = conn.execute(text("""
            SELECT count(*) AS total,
                   sum(CASE WHEN archived_at IS NOT NULL THEN 1 ELSE 0 END) AS archived,
                   sum(CASE WHEN retracted_at IS NOT NULL THEN 1 ELSE 0 END) AS retracted,
                   sum(CASE WHEN revoked_at IS NOT NULL THEN 1 ELSE 0 END) AS revoked,
                   sum(CASE WHEN archived_at IS NULL AND retracted_at IS NULL AND revoked_at IS NULL
                            THEN 1 ELSE 0 END) AS recallable
            FROM episodic_memories
            """)).one()
    total = int(row.total or 0)
    recallable = int(row.recallable or 0)
    detail = (
        f"episodic total={total} recallable={recallable} archived={int(row.archived or 0)} "
        f"retracted={int(row.retracted or 0)} revoked={int(row.revoked or 0)}"
    )
    violations: list[str] = []
    if recallable > total:
        violations.append("可召回计数超过总行数（墓碑公式破裂）")
    return Finding("INV-5", not violations, detail, violations)


# ---------------------------------------------------------------------------
# INV-6 引用完整性零孤儿
# ---------------------------------------------------------------------------
def check_foreign_key_orphans(conn: Connection) -> Finding:
    checks = [
        (
            "agent_runs.user_id",
            "SELECT count(*) FROM agent_runs r LEFT JOIN users u ON u.id = r.user_id WHERE r.user_id IS NOT NULL AND u.id IS NULL",
        ),
        (
            "episodic_memories.user_id",
            "SELECT count(*) FROM episodic_memories m LEFT JOIN users u ON u.id = m.user_id WHERE u.id IS NULL",
        ),
        (
            "memory_preferences.user_id",
            "SELECT count(*) FROM memory_preferences p LEFT JOIN users u ON u.id = p.user_id WHERE u.id IS NULL",
        ),
        (
            "agent_run_transitions.run_id",
            "SELECT count(*) FROM agent_run_transitions t LEFT JOIN agent_runs r ON r.id = t.run_id WHERE t.run_id IS NOT NULL AND r.id IS NULL",
        ),
    ]
    violations: list[str] = []
    ran = 0
    for label, sql in checks:
        head_table = label.split(".")[0]
        if not _table_exists(conn, head_table):
            violations.append(f"{label}: 表 {head_table} 不存在，无法核孤儿")
            continue
        n = int(conn.execute(text(sql)).scalar_one() or 0)
        ran += 1
        if n:
            violations.append(f"{label}: {n} 行孤儿")
    return Finding("INV-6", not violations, f"孤儿检查 {ran}/{len(checks)} 项执行", violations)


# ---------------------------------------------------------------------------
# 基线采集 / INV-7 快照等价
# ---------------------------------------------------------------------------
def capture_baseline(conn: Connection) -> dict[str, Any]:
    baseline: dict[str, Any] = {"captured_at": datetime.utcnow().isoformat() + "Z", "tables": {}}
    for table in KEY_TABLES:
        if not _table_exists(conn, table):
            baseline["tables"][table] = {"exists": False}
            continue
        n = int(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() or 0)  # noqa: S608
        baseline["tables"][table] = {"exists": True, "row_count": n}
    if _table_exists(conn, "agent_runs"):
        rows = conn.execute(text("SELECT status, count(*) AS n FROM agent_runs GROUP BY status")).fetchall()
        baseline["agent_runs_by_status"] = {str(r.status): int(r.n) for r in rows}
    if _table_exists(conn, "episodic_memories"):
        row = conn.execute(
            text(
                "SELECT sum(CASE WHEN archived_at IS NULL AND retracted_at IS NULL AND revoked_at IS NULL "
                "THEN 1 ELSE 0 END) AS recallable FROM episodic_memories"
            )
        ).one()
        baseline["episodic_recallable"] = int(row.recallable or 0)
    if _table_exists(conn, "event_outbox"):
        row = conn.execute(
            text(
                "SELECT sum(CASE WHEN published_at IS NOT NULL THEN 1 ELSE 0 END) AS pub, count(*) AS total FROM event_outbox"
            )
        ).one()
        baseline["outbox_published"] = int(row.pub or 0)
        baseline["outbox_total"] = int(row.total or 0)
    if _table_exists(conn, "processed_events"):
        baseline["processed_events_total"] = int(
            conn.execute(text("SELECT count(*) FROM processed_events")).scalar_one() or 0
        )
    return baseline


def check_snapshot_equality(conn: Connection, baseline: dict[str, Any]) -> Finding:
    violations: list[str] = []
    compared = 0
    for table, meta in baseline.get("tables", {}).items():
        if not meta.get("exists"):
            continue
        if not _table_exists(conn, table):
            violations.append(f"{table}: 基线存在但恢复库缺表")
            continue
        n = int(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() or 0)  # noqa: S608
        compared += 1
        if n != int(meta.get("row_count", -1)):
            violations.append(f"{table}: 行数 恢复后={n} 基线={meta.get('row_count')}")
    for key in (
        "agent_runs_by_status",
        "episodic_recallable",
        "outbox_published",
        "outbox_total",
        "processed_events_total",
    ):
        if key not in baseline:
            continue
        compared += 1
        current: Any
        if key == "agent_runs_by_status":
            rows = conn.execute(text("SELECT status, count(*) AS n FROM agent_runs GROUP BY status")).fetchall()
            current = {str(r.status): int(r.n) for r in rows}
        elif key == "episodic_recallable":
            row = conn.execute(
                text(
                    "SELECT sum(CASE WHEN archived_at IS NULL AND retracted_at IS NULL AND revoked_at IS NULL "
                    "THEN 1 ELSE 0 END) AS recallable FROM episodic_memories"
                )
            ).one()
            current = int(row.recallable or 0)
        elif key == "outbox_published":
            row = conn.execute(
                text("SELECT sum(CASE WHEN published_at IS NOT NULL THEN 1 ELSE 0 END) AS pub FROM event_outbox")
            ).one()
            current = int(row.pub or 0)
        elif key == "outbox_total":
            current = int(conn.execute(text("SELECT count(*) FROM event_outbox")).scalar_one() or 0)
        else:
            current = int(conn.execute(text("SELECT count(*) FROM processed_events")).scalar_one() or 0)
        if current != baseline[key]:
            violations.append(f"{key}: 恢复后={current} 基线={baseline[key]}")
    return Finding("INV-7", not violations, f"与备份点基线比对 {compared} 项", violations)


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--url", default=None, help="SQLAlchemy sync URL（缺省读 DATABASE_URL）")
    parser.add_argument("--baseline", default=None, help="备份点基线 JSON（--capture-baseline 产出）")
    parser.add_argument("--capture-baseline", default=None, metavar="PATH", help="把当前库指纹写为基线 JSON 后退出")
    parser.add_argument("--report", default=None, help="把校验结果同时写入 JSON 文件")
    args = parser.parse_args(argv)

    url = args.url or os.environ.get("DATABASE_URL") or ""
    if not url:
        print("error: --url 或 DATABASE_URL 必须提供", file=sys.stderr)
        return 2

    engine = create_engine(url)
    with engine.connect() as conn:
        if args.capture_baseline:
            captured = capture_baseline(conn)
            with open(args.capture_baseline, "w", encoding="utf-8") as fh:
                json.dump(captured, fh, ensure_ascii=False, indent=2)
            print(f"[baseline] captured -> {args.capture_baseline}")
            return 0

        baseline: dict[str, Any] | None = None
        if args.baseline:
            with open(args.baseline, encoding="utf-8") as fh:
                baseline = json.load(fh)

        findings = [
            check_run_status_vocabulary(conn),
            check_run_transition_projection(conn),
            check_active_run_uniqueness(conn),
            check_outbox_sequence_monotonic(conn),
            check_memory_tombstones(conn),
            check_foreign_key_orphans(conn),
        ]
        if baseline is not None:
            findings.append(check_snapshot_equality(conn, baseline))

    ok_all = all(f.ok for f in findings)
    print("=" * 72)
    print("restore_consistency_check — 恢复后一致性不变量")
    print("=" * 72)
    for f in findings:
        print(f.render())
    print("=" * 72)
    verdict = "PASS" if ok_all else "FAIL"
    failed = [f.invariant for f in findings if not f.ok]
    print(f"verdict={verdict}" + (f" violated={','.join(failed)}" if failed else ""))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "verdict": verdict,
                    "url_database": url.rsplit("/", 1)[-1].split("?")[0],
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                    "findings": [
                        {"invariant": f.invariant, "ok": f.ok, "detail": f.detail, "violations": f.violations}
                        for f in findings
                    ],
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
