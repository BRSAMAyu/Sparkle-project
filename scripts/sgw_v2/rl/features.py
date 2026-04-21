"""RL data collection layer: trajectory storage, feature extraction, failure library.

Phase 1 of the SGW RL upgrade. Provides:
- rl_trajectories table: per-turn RL signal storage
- failure_library table: persistent failure pattern catalog
- FeatureExtractor: converts RunDB data into StateVectors for policy input
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..storage.db import RunDB
from .spec import (
    StateVector, PopulationStats, RunContext, FailureSignal,
    IterationOutcome, compute_config_hash, state_from_summary,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


# ── Schema ─────────────────────────────────────────────────


_TRAJECTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS rl_trajectories (
    traj_id         TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    iteration_id    TEXT,
    session_id      TEXT REFERENCES sessions(session_id),
    turn_id         TEXT REFERENCES turns(turn_id),

    -- State features
    state_vector    TEXT NOT NULL DEFAULT '[]',    -- JSON: feature vector φ(s_t)
    config_snapshot TEXT,                          -- JSON: config at this point

    -- Action
    action_taken    TEXT NOT NULL DEFAULT '{}',    -- JSON: {param: value}
    action_source   TEXT NOT NULL DEFAULT 'rule',  -- "rule" | "bandit" | "contextual" | "explore"

    -- Reward
    reward_raw      REAL,
    reward_normalized REAL,
    reward_components TEXT,                        -- JSON: per-dimension rewards

    -- Outcome
    outcome         TEXT NOT NULL DEFAULT 'pending',  -- IterationOutcome value

    -- Context for attribution
    persona_id      TEXT,
    behavior_class  TEXT,
    audit_scores    TEXT,                          -- JSON: audit dimension scores

    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traj_run ON rl_trajectories(run_id);
CREATE INDEX IF NOT EXISTS idx_traj_iteration ON rl_trajectories(iteration_id);
CREATE INDEX IF NOT EXISTS idx_traj_outcome ON rl_trajectories(outcome);
CREATE INDEX IF NOT EXISTS idx_traj_action_source ON rl_trajectories(action_source);
"""

_FAILURE_LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS failure_library (
    pattern_id      TEXT PRIMARY KEY,
    pattern_hash    TEXT NOT NULL,                 -- dedup key
    category        TEXT NOT NULL,                 -- "compliance" | "authenticity" | "attribution" | "performance"
    severity        TEXT NOT NULL DEFAULT 'major',

    -- Pattern description
    description     TEXT NOT NULL,
    evidence_template TEXT NOT NULL,               -- JSON: evidence pattern to match

    -- Occurrence tracking
    first_seen_run  TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    last_seen_run   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,

    -- Resolution
    status          TEXT NOT NULL DEFAULT 'active', -- "active" | "mitigated" | "resolved"
    resolution      TEXT,                           -- how it was fixed
    resolved_at     TEXT,

    UNIQUE(pattern_hash)
);

CREATE INDEX IF NOT EXISTS idx_failure_category ON failure_library(category);
CREATE INDEX IF NOT EXISTS idx_failure_status ON failure_library(status);
CREATE INDEX IF NOT EXISTS idx_failure_hash ON failure_library(pattern_hash);
"""


# ── Feature Extraction ────────────────────────────────────


class FeatureExtractor:
    """Extracts StateVectors and trajectory records from RunDB data."""

    def __init__(self, run_db: RunDB):
        self.run_db = run_db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.run_db.conn.executescript(_TRAJECTORY_SCHEMA)
        self.run_db.conn.executescript(_FAILURE_LIBRARY_SCHEMA)
        self.run_db.conn.commit()

    def extract_state(
        self,
        run_id: str,
        iteration_number: int = 0,
        active_hypotheses: list[str] | None = None,
        last_outcome: IterationOutcome = IterationOutcome.NEUTRAL,
    ) -> StateVector | None:
        """Build StateVector from current run summary."""
        summary = self.run_db.run_summary(run_id)
        if not summary:
            return None

        run_data = self.run_db.get_run(run_id)
        scenario_id = run_data.get("scenario_id", "") if run_data else ""
        config_hash = run_data.get("config_hash", "") if run_data else ""

        return state_from_summary(
            summary=summary,
            scenario_id=scenario_id,
            config_hash=config_hash,
            iteration_number=iteration_number,
            active_hypotheses=active_hypotheses,
            last_outcome=last_outcome,
        )

    def record_trajectory(
        self,
        *,
        run_id: str,
        iteration_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        state_vector: list[float] | None = None,
        config_snapshot: dict[str, Any] | None = None,
        action_taken: dict[str, Any] | None = None,
        action_source: str = "rule",
        reward_raw: float | None = None,
        reward_normalized: float | None = None,
        reward_components: dict[str, float] | None = None,
        outcome: str = "pending",
        persona_id: str | None = None,
        behavior_class: str | None = None,
        audit_scores: dict[str, float] | None = None,
    ) -> str:
        """Record a trajectory step."""
        traj_id = f"traj_{uuid.uuid4().hex[:12]}"
        self.run_db.conn.execute(
            """INSERT INTO rl_trajectories
               (traj_id, run_id, iteration_id, session_id, turn_id,
                state_vector, config_snapshot, action_taken, action_source,
                reward_raw, reward_normalized, reward_components, outcome,
                persona_id, behavior_class, audit_scores, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                traj_id, run_id, iteration_id, session_id, turn_id,
                json.dumps(state_vector or [], ensure_ascii=False),
                json.dumps(config_snapshot, ensure_ascii=False) if config_snapshot else None,
                json.dumps(action_taken or {}, ensure_ascii=False),
                action_source,
                reward_raw, reward_normalized,
                json.dumps(reward_components, ensure_ascii=False) if reward_components else None,
                outcome,
                persona_id, behavior_class,
                json.dumps(audit_scores, ensure_ascii=False) if audit_scores else None,
                _utcnow_iso(),
            ),
        )
        self.run_db.conn.commit()
        return traj_id

    def update_trajectory_outcome(self, traj_id: str, outcome: str,
                                   reward_raw: float, reward_normalized: float,
                                   reward_components: dict[str, float]) -> None:
        """Update trajectory with final outcome and reward."""
        self.run_db.conn.execute(
            """UPDATE rl_trajectories SET outcome = ?, reward_raw = ?,
               reward_normalized = ?, reward_components = ? WHERE traj_id = ?""",
            (
                outcome, reward_raw, reward_normalized,
                json.dumps(reward_components, ensure_ascii=False), traj_id,
            ),
        )
        self.run_db.conn.commit()

    def get_iteration_trajectories(self, iteration_id: str) -> list[dict[str, Any]]:
        """Get all trajectory records for a specific iteration."""
        rows = self.run_db.conn.execute(
            "SELECT * FROM rl_trajectories WHERE iteration_id = ? ORDER BY created_at",
            (iteration_id,),
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute(
            "SELECT * FROM rl_trajectories LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def get_recent_configs(self, limit: int = 10) -> list[str]:
        """Get recent config hashes for Guardrail 1 (novelty check)."""
        rows = self.run_db.conn.execute(
            """SELECT DISTINCT config_snapshot FROM rl_trajectories
               WHERE config_snapshot IS NOT NULL ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        hashes = []
        for row in rows:
            try:
                config = json.loads(row[0])
                hashes.append(compute_config_hash(config))
            except (json.JSONDecodeError, TypeError):
                pass
        return hashes

    # ── Failure Library ──────────────────────────────────

    def record_failure_pattern(
        self,
        *,
        category: str,
        severity: str,
        description: str,
        evidence: dict[str, Any],
        run_id: str,
    ) -> str | None:
        """Record or increment a failure pattern. Returns pattern_id or None if duplicate."""
        pattern_hash = hashlib.sha256(
            json.dumps({"category": category, "description": description[:100]}, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Check if already seen
        existing = self.run_db.conn.execute(
            "SELECT pattern_id, occurrence_count FROM failure_library WHERE pattern_hash = ?",
            (pattern_hash,),
        ).fetchone()

        if existing:
            # Increment occurrence
            self.run_db.conn.execute(
                """UPDATE failure_library SET occurrence_count = ?, last_seen_run = ?, last_seen_at = ?
                   WHERE pattern_hash = ?""",
                (existing[1] + 1, run_id, _utcnow_iso(), pattern_hash),
            )
            self.run_db.conn.commit()
            return existing[0]

        pattern_id = f"fp_{uuid.uuid4().hex[:12]}"
        self.run_db.conn.execute(
            """INSERT INTO failure_library
               (pattern_id, pattern_hash, category, severity, description,
                evidence_template, first_seen_run, occurrence_count, last_seen_run, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                pattern_id, pattern_hash, category, severity, description,
                json.dumps(evidence, ensure_ascii=False),
                run_id, run_id, _utcnow_iso(),
            ),
        )
        self.run_db.conn.commit()
        return pattern_id

    def get_active_failures(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get all active (unresolved) failure patterns."""
        if category:
            rows = self.run_db.conn.execute(
                "SELECT * FROM failure_library WHERE status = 'active' AND category = ? ORDER BY occurrence_count DESC",
                (category,),
            ).fetchall()
        else:
            rows = self.run_db.conn.execute(
                "SELECT * FROM failure_library WHERE status = 'active' ORDER BY occurrence_count DESC",
            ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute(
            "SELECT * FROM failure_library LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def resolve_failure(self, pattern_id: str, resolution: str) -> None:
        """Mark a failure pattern as resolved."""
        self.run_db.conn.execute(
            """UPDATE failure_library SET status = 'resolved', resolution = ?, resolved_at = ?
               WHERE pattern_id = ?""",
            (resolution, _utcnow_iso(), pattern_id),
        )
        self.run_db.conn.commit()
