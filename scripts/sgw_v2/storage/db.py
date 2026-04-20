"""SGW v2 storage layer: SQLite-backed run persistence with run_id and config_hash."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def compute_config_hash(config: dict) -> str:
    """Deterministic SHA-256 of a config dict. Sorts keys for reproducibility."""
    canonical = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def compute_prompt_hashes(prompt_dir: Path) -> dict[str, str]:
    """Hash all .md files in the prompts directory."""
    hashes: dict[str, str] = {}
    for f in sorted(prompt_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        hashes[f.name] = hashlib.sha256(content.encode()).hexdigest()[:16]
    return hashes


def compute_file_hash(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()[:16]


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT PRIMARY KEY,
    scenario_id     TEXT NOT NULL DEFAULT 'stage_16_rule_y',
    config_hash     TEXT NOT NULL,
    git_sha         TEXT NOT NULL DEFAULT 'unknown',
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    scenario_config TEXT NOT NULL DEFAULT '{}',
    prompt_hashes   TEXT NOT NULL DEFAULT '{}',
    model_versions  TEXT NOT NULL DEFAULT '{}',
    summary         TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    task_id         TEXT NOT NULL,
    role            TEXT NOT NULL,
    seed_persona_id TEXT,
    persona_sample  TEXT,
    arc_id          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    target_turns    INTEGER NOT NULL DEFAULT 12,
    turns_completed INTEGER NOT NULL DEFAULT 0,
    detected_memory_ids TEXT,
    revoke_scheduled INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    turn_id         TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    turn_index      INTEGER NOT NULL,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    user_message    TEXT NOT NULL DEFAULT '',
    ai_response     TEXT NOT NULL DEFAULT '',
    turn_decision   TEXT,
    state_machine_state TEXT,
    ai_behavior_class TEXT,
    latency_ms      INTEGER,
    model_used      TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audits (
    audit_id        TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    session_id      TEXT REFERENCES sessions(session_id),
    target_id       TEXT NOT NULL,
    audit_type      TEXT NOT NULL DEFAULT 'compliance',
    status          TEXT NOT NULL DEFAULT 'pending',
    scores          TEXT,
    overall         REAL,
    is_violation    INTEGER,
    reason          TEXT,
    audit_model     TEXT NOT NULL DEFAULT '',
    audit_provider  TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS violations (
    violation_id    TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    session_id      TEXT REFERENCES sessions(session_id),
    turn_id         TEXT REFERENCES turns(turn_id),
    code            TEXT NOT NULL,
    severity        TEXT NOT NULL,
    context         TEXT,
    created_at      TEXT NOT NULL
);

-- Phase 1 indexes
CREATE INDEX IF NOT EXISTS idx_sessions_run ON sessions(run_id);
CREATE INDEX IF NOT EXISTS idx_sessions_run_status ON sessions(run_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_persona ON sessions(seed_persona_id);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_session_turn ON turns(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_turns_run ON turns(run_id);
CREATE INDEX IF NOT EXISTS idx_turns_behavior ON turns(ai_behavior_class);
CREATE INDEX IF NOT EXISTS idx_audits_run ON audits(run_id);
CREATE INDEX IF NOT EXISTS idx_audits_run_type ON audits(run_id, audit_type);
CREATE INDEX IF NOT EXISTS idx_audits_type ON audits(audit_type);
CREATE INDEX IF NOT EXISTS idx_audits_target ON audits(target_id);
CREATE INDEX IF NOT EXISTS idx_violations_run ON violations(run_id);
CREATE INDEX IF NOT EXISTS idx_violations_code ON violations(code);
"""


class RunDB:
    """SQLite-backed run storage for SGW v2."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._init_db()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Runs ──────────────────────────────────────────

    def create_run(
        self,
        *,
        scenario_id: str = "stage_16_rule_y",
        config_hash: str,
        git_sha: str,
        scenario_config: dict,
        prompt_hashes: dict[str, str],
        model_versions: dict[str, str],
    ) -> str:
        run_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO runs (run_id, scenario_id, config_hash, git_sha,
               started_at, status, scenario_config, prompt_hashes, model_versions)
               VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)""",
            (
                run_id,
                scenario_id,
                config_hash,
                git_sha,
                _utcnow_iso(),
                json.dumps(scenario_config, ensure_ascii=False),
                json.dumps(prompt_hashes, ensure_ascii=False),
                json.dumps(model_versions, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self.conn.execute("SELECT * FROM runs LIMIT 0").description]
        return dict(zip(cols, row))

    def finish_run(self, run_id: str, *, status: str = "completed", summary: dict | None = None) -> None:
        self.conn.execute(
            "UPDATE runs SET ended_at = ?, status = ?, summary = ? WHERE run_id = ?",
            (_utcnow_iso(), status, json.dumps(summary, ensure_ascii=False) if summary else None, run_id),
        )
        self.conn.commit()

    # ── Sessions ──────────────────────────────────────

    def upsert_session(
        self,
        *,
        session_id: str,
        run_id: str,
        task_id: str,
        role: str,
        seed_persona_id: str | None = None,
        persona_sample: dict | None = None,
        target_turns: int = 12,
        turns_completed: int = 0,
        status: str = "pending",
        detected_memory_ids: list[str] | None = None,
        revoke_scheduled: bool = False,
    ) -> None:
        now = _utcnow_iso()
        self.conn.execute(
            """INSERT INTO sessions
               (session_id, run_id, task_id, role, seed_persona_id, persona_sample,
                status, target_turns, turns_completed, detected_memory_ids,
                revoke_scheduled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 status=excluded.status,
                 turns_completed=excluded.turns_completed,
                 detected_memory_ids=excluded.detected_memory_ids,
                 revoke_scheduled=excluded.revoke_scheduled,
                 updated_at=excluded.updated_at,
                 persona_sample=excluded.persona_sample""",
            (
                session_id,
                run_id,
                task_id,
                role,
                seed_persona_id,
                json.dumps(persona_sample, ensure_ascii=False) if persona_sample else None,
                status,
                target_turns,
                turns_completed,
                json.dumps(detected_memory_ids, ensure_ascii=False) if detected_memory_ids else None,
                int(revoke_scheduled),
                now,
                now,
            ),
        )
        self.conn.commit()

    def complete_session(self, session_id: str) -> None:
        now = _utcnow_iso()
        self.conn.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ?, updated_at = ? WHERE session_id = ?",
            (now, now, session_id),
        )
        self.conn.commit()

    # ── Turns ─────────────────────────────────────────

    def insert_turn(
        self,
        *,
        session_id: str,
        run_id: str,
        turn_index: int,
        user_message: str,
        ai_response: str,
        turn_decision: dict | None = None,
        state_machine_state: str | None = None,
        ai_behavior_class: str | None = None,
        latency_ms: int | None = None,
        model_used: str | None = None,
    ) -> str:
        turn_id = f"{session_id}_{turn_index:04d}"
        self.conn.execute(
            """INSERT OR REPLACE INTO turns
               (turn_id, session_id, turn_index, run_id, user_message, ai_response,
                turn_decision, state_machine_state, ai_behavior_class,
                latency_ms, model_used, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                turn_id,
                session_id,
                turn_index,
                run_id,
                user_message,
                ai_response,
                json.dumps(turn_decision, ensure_ascii=False) if turn_decision else None,
                state_machine_state,
                ai_behavior_class,
                latency_ms,
                model_used,
                _utcnow_iso(),
            ),
        )
        self.conn.commit()
        return turn_id

    def get_session_turns(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index",
            (session_id,),
        ).fetchall()
        cols = [desc[0] for desc in self.conn.execute("SELECT * FROM turns LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]

    # ── Audits ────────────────────────────────────────

    def insert_audit(
        self,
        *,
        audit_id: str,
        run_id: str,
        session_id: str | None = None,
        target_id: str,
        audit_type: str = "compliance",
        scores: dict | None = None,
        overall: float | None = None,
        is_violation: bool | None = None,
        reason: str | None = None,
        audit_model: str = "",
        audit_provider: str = "",
        status: str = "completed",
    ) -> None:
        now = _utcnow_iso()
        self.conn.execute(
            """INSERT INTO audits
               (audit_id, run_id, session_id, target_id, audit_type, status,
                scores, overall, is_violation, reason, audit_model, audit_provider,
                created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                run_id,
                session_id,
                target_id,
                audit_type,
                status,
                json.dumps(scores, ensure_ascii=False) if scores else None,
                overall,
                int(is_violation) if is_violation is not None else None,
                reason,
                audit_model,
                audit_provider,
                now,
                now,
            ),
        )
        self.conn.commit()

    # ── Violations ────────────────────────────────────

    def insert_violation(
        self,
        *,
        run_id: str,
        session_id: str | None = None,
        turn_id: str | None = None,
        code: str,
        severity: str,
        context: dict | None = None,
    ) -> str:
        violation_id = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO violations
               (violation_id, run_id, session_id, turn_id, code, severity, context, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                violation_id,
                run_id,
                session_id,
                turn_id,
                code,
                severity,
                json.dumps(context, ensure_ascii=False) if context else None,
                _utcnow_iso(),
            ),
        )
        self.conn.commit()
        return violation_id

    # ── Query helpers ─────────────────────────────────

    def run_summary(self, run_id: str) -> dict[str, Any]:
        """Generate summary metrics for a run."""
        sessions_total = self.conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        sessions_completed = self.conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE run_id = ? AND status = 'completed'", (run_id,)
        ).fetchone()[0]
        turns_total = self.conn.execute(
            "SELECT COUNT(*) FROM turns WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        audits_total = self.conn.execute(
            "SELECT COUNT(*) FROM audits WHERE run_id = ? AND audit_type = 'compliance'", (run_id,)
        ).fetchone()[0]
        soft_violations = self.conn.execute(
            "SELECT COUNT(*) FROM audits WHERE run_id = ? AND audit_type = 'compliance' AND is_violation = 1",
            (run_id,),
        ).fetchone()[0]
        hard_violations = self.conn.execute(
            "SELECT COUNT(*) FROM violations WHERE run_id = ? AND severity = 'hard'", (run_id,)
        ).fetchone()[0]
        auth_total = self.conn.execute(
            "SELECT COUNT(*) FROM audits WHERE run_id = ? AND audit_type = 'authenticity'", (run_id,)
        ).fetchone()[0]
        auth_failures = self.conn.execute(
            "SELECT COUNT(*) FROM audits WHERE run_id = ? AND audit_type = 'authenticity' AND is_violation = 1",
            (run_id,),
        ).fetchone()[0]
        auth_mean_row = self.conn.execute(
            "SELECT AVG(overall) FROM audits WHERE run_id = ? AND audit_type = 'authenticity' AND overall IS NOT NULL",
            (run_id,),
        ).fetchone()[0]

        soft_rate = soft_violations / audits_total if audits_total > 0 else 0.0
        auth_mean = round(auth_mean_row, 4) if auth_mean_row is not None else 0.0

        return {
            "sessions_total": sessions_total,
            "sessions_completed": sessions_completed,
            "turns_total": turns_total,
            "audits_total": audits_total,
            "soft_violations": soft_violations,
            "soft_violation_rate": round(soft_rate, 4),
            "hard_violations": hard_violations,
            "authenticity_total": auth_total,
            "authenticity_failures": auth_failures,
            "authenticity_mean": auth_mean,
        }

    def compare_runs(self, run_id_a: str, run_id_b: str) -> dict[str, Any]:
        """Compare two runs and return diff of all metrics."""
        summary_a = self.run_summary(run_id_a)
        summary_b = self.run_summary(run_id_b)
        diff = {}
        for key in summary_a:
            diff[key] = {"a": summary_a[key], "b": summary_b[key]}
            if isinstance(summary_a[key], (int, float)):
                diff[key]["delta"] = summary_b[key] - summary_a[key]
        return diff

    def latest_run_id(self) -> str | None:
        row = self.conn.execute(
            "SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    # ── Migration from checkpoint.json ────────────────

    def migrate_checkpoint(self, checkpoint_path: Path) -> str | None:
        """Import existing sgw_checkpoint.json data into SQLite."""
        if not checkpoint_path.exists():
            return None
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        metrics = data.get("metrics", {})

        run_id = self.create_run(
            config_hash="migrated",
            git_sha="migrated",
            scenario_config={"source": "checkpoint_migration"},
            prompt_hashes={},
            model_versions={},
        )

        # Import session tasks
        for task_id, task_data in data.get("session_tasks", {}).items():
            self.upsert_session(
                session_id=task_data.get("session_id", task_id),
                run_id=run_id,
                task_id=task_id,
                role=task_data.get("role", "persona"),
                seed_persona_id=task_data.get("persona_id"),
                target_turns=task_data.get("target_turns", 12),
                turns_completed=task_data.get("turns_completed", 0),
                status=task_data.get("status", "pending"),
                detected_memory_ids=task_data.get("detected_memory_ids"),
                revoke_scheduled=task_data.get("revoke_scheduled", False),
            )

        self.finish_run(
            run_id,
            status="migrated",
            summary={
                "sessions_completed": metrics.get("sessions_completed", 0),
                "turns_completed": metrics.get("turns_completed", 0),
                "soft_violation_rate": metrics.get("audit_soft_violations", 0)
                / max(metrics.get("audit_cases", 1), 1),
                "hard_violations": len(metrics.get("hard_violations", [])),
            },
        )
        return run_id
