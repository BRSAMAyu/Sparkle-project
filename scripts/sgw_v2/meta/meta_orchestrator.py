"""Meta-orchestrator: the outer loop that drives iterative SGW improvement.

Cycle: Run -> Diagnose -> Plan -> Execute (next run) -> Compare -> Repeat

This module provides:
- MetaOrchestrator: orchestrates the full improvement cycle
- IterationResult: tracks the outcome of each iteration
- SQLite persistence for experiments and iterations
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..storage.db import RunDB
from .diagnostic_agent import DiagnosticAgent
from .experiment_planner import ExperimentPlanner, ExperimentPlan


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


@dataclass
class IterationResult:
    """Outcome of a single iteration in the meta-orchestration loop."""
    iteration_id: str
    run_id: str
    iteration_number: int
    plan_id: str | None
    hypotheses_count: int
    changes_applied: int
    outcome: str                   # "improved" | "regressed" | "neutral" | "error"
    summary_before: dict[str, Any]
    summary_after: dict[str, Any]
    created_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration_id": self.iteration_id,
            "run_id": self.run_id,
            "iteration_number": self.iteration_number,
            "plan_id": self.plan_id,
            "hypotheses_count": self.hypotheses_count,
            "changes_applied": self.changes_applied,
            "outcome": self.outcome,
            "summary_before": self.summary_before,
            "summary_after": self.summary_after,
            "created_at": self.created_at,
        }


# SQL for experiments and iterations tables (Phase 4)
_PHASE4_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id   TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    plan_id         TEXT NOT NULL,
    hypothesis_ids  TEXT NOT NULL DEFAULT '[]',
    parameter_changes TEXT NOT NULL DEFAULT '[]',
    expected_outcome TEXT,
    priority        TEXT NOT NULL DEFAULT 'normal',
    status          TEXT NOT NULL DEFAULT 'proposed',
    result_run_id   TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS iterations (
    iteration_id    TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    iteration_number INTEGER NOT NULL,
    plan_id         TEXT,
    hypotheses_count INTEGER NOT NULL DEFAULT 0,
    changes_applied INTEGER NOT NULL DEFAULT 0,
    outcome         TEXT NOT NULL DEFAULT 'pending',
    summary_before  TEXT NOT NULL DEFAULT '{}',
    summary_after   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiments_run ON experiments(run_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_iterations_run ON iterations(run_id);
"""


class MetaOrchestrator:
    """Outer loop orchestrator for iterative SGW improvement.

    Usage:
        meta = MetaOrchestrator(run_db, current_config)
        result = meta.run_iteration(latest_run_id)
        if result and result.outcome == "improved":
            # adopt new config
    """

    def __init__(self, run_db: RunDB, current_config: dict[str, Any]):
        self.run_db = run_db
        self.current_config = current_config
        self.diagnostic = DiagnosticAgent(run_db)
        self.planner = ExperimentPlanner(current_config)
        self._ensure_phase4_schema()
        self._iteration_count = self._count_iterations()

    def _ensure_phase4_schema(self) -> None:
        """Create Phase 4 tables if they don't exist."""
        self.run_db.conn.executescript(_PHASE4_SCHEMA)
        self.run_db.conn.commit()

    def _count_iterations(self) -> int:
        row = self.run_db.conn.execute(
            "SELECT COUNT(*) FROM iterations"
        ).fetchone()
        return row[0] if row else 0

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    def run_iteration(self, run_id: str) -> IterationResult | None:
        """Execute one diagnose -> plan cycle for a completed run.

        Returns IterationResult if changes are proposed, None if run is healthy.
        """
        summary_before = self.run_db.run_summary(run_id)
        if not summary_before:
            return None

        # Step 1: Diagnose
        hypotheses = self.diagnostic.diagnose(run_id)
        if not hypotheses:
            # Healthy run, no changes needed
            return IterationResult(
                iteration_id=f"iter_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                iteration_number=self._iteration_count + 1,
                plan_id=None,
                hypotheses_count=0,
                changes_applied=0,
                outcome="neutral",
                summary_before=summary_before,
                summary_after=summary_before,
            )

        # Step 2: Plan
        plan = self.planner.plan(hypotheses, run_id)
        if plan is None:
            # Hypotheses exist but no auto-adjustable parameters
            return IterationResult(
                iteration_id=f"iter_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                iteration_number=self._iteration_count + 1,
                plan_id=None,
                hypotheses_count=len(hypotheses),
                changes_applied=0,
                outcome="neutral",
                summary_before=summary_before,
                summary_after=summary_before,
            )

        # Step 3: Persist experiment
        self._save_experiment(plan)

        # Step 4: Record iteration
        iteration = IterationResult(
            iteration_id=f"iter_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            iteration_number=self._iteration_count + 1,
            plan_id=plan.plan_id,
            hypotheses_count=len(hypotheses),
            changes_applied=len(plan.parameter_changes),
            outcome="pending",
            summary_before=summary_before,
            summary_after={},  # Will be filled after next run
        )

        self._save_iteration(iteration)

        # Step 5: Update config for next run
        new_config = self.planner.apply_plan(plan)
        self.current_config = new_config
        self.planner = ExperimentPlanner(new_config)

        self._iteration_count += 1
        return iteration

    def evaluate_iteration(self, iteration_id: str, new_run_id: str) -> IterationResult | None:
        """Evaluate the outcome of a completed iteration by comparing runs."""
        # Get the iteration
        row = self.run_db.conn.execute(
            "SELECT * FROM iterations WHERE iteration_id = ?", (iteration_id,)
        ).fetchone()
        if not row:
            return None

        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM iterations LIMIT 0").description]
        iter_data = dict(zip(cols, row))
        parent_run_id = iter_data["run_id"]

        summary_before = self.run_db.run_summary(parent_run_id)
        summary_after = self.run_db.run_summary(new_run_id)
        if not summary_before or not summary_after:
            return None

        # Determine outcome
        outcome = self._judge_outcome(summary_before, summary_after)

        iteration = IterationResult(
            iteration_id=iteration_id,
            run_id=parent_run_id,
            iteration_number=iter_data["iteration_number"],
            plan_id=iter_data.get("plan_id"),
            hypotheses_count=iter_data.get("hypotheses_count", 0),
            changes_applied=iter_data.get("changes_applied", 0),
            outcome=outcome,
            summary_before=summary_before,
            summary_after=summary_after,
        )

        # Update in DB
        self.run_db.conn.execute(
            """UPDATE iterations SET outcome = ?, summary_after = ?
               WHERE iteration_id = ?""",
            (
                outcome,
                json.dumps(summary_after, ensure_ascii=False),
                iteration_id,
            ),
        )
        self.run_db.conn.commit()

        # If regressed, revert config
        if outcome == "regressed":
            self._revert_config(summary_before)

        return iteration

    def _judge_outcome(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        """Judge whether the iteration improved, regressed, or was neutral."""
        score = 0

        # Soft violation rate: lower is better
        delta_soft = before.get("soft_violation_rate", 0) - after.get("soft_violation_rate", 0)
        if delta_soft > 0.02:
            score += 2
        elif delta_soft < -0.02:
            score -= 2

        # Authenticity mean: higher is better
        delta_auth = after.get("authenticity_mean", 0) - before.get("authenticity_mean", 0)
        if delta_auth > 0.03:
            score += 2
        elif delta_auth < -0.03:
            score -= 2

        # Hard violations: fewer is better
        if after.get("hard_violations", 0) > before.get("hard_violations", 0):
            score -= 3

        # Session completion: more is better
        delta_sessions = after.get("sessions_completed", 0) - before.get("sessions_completed", 0)
        if delta_sessions > 10:
            score += 1

        if score >= 2:
            return "improved"
        elif score <= -2:
            return "regressed"
        return "neutral"

    def _revert_config(self, previous_summary: dict[str, Any]) -> None:
        """Revert config to pre-iteration state."""
        # Reset planner to current config (which was the pre-change config)
        self.planner = ExperimentPlanner(self.current_config)

    def _save_experiment(self, plan: ExperimentPlan) -> None:
        self.run_db.conn.execute(
            """INSERT OR REPLACE INTO experiments
               (experiment_id, run_id, plan_id, hypothesis_ids, parameter_changes,
                expected_outcome, priority, status, result_run_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan.plan_id,
                plan.parent_run_id,
                plan.plan_id,
                json.dumps(plan.hypotheses, ensure_ascii=False),
                json.dumps([pc.to_dict() for pc in plan.parameter_changes], ensure_ascii=False),
                plan.expected_outcome,
                plan.priority,
                plan.status,
                plan.result_run_id,
                plan.created_at,
                _utcnow_iso(),
            ),
        )
        self.run_db.conn.commit()

    def _save_iteration(self, iteration: IterationResult) -> None:
        self.run_db.conn.execute(
            """INSERT OR REPLACE INTO iterations
               (iteration_id, run_id, iteration_number, plan_id, hypotheses_count,
                changes_applied, outcome, summary_before, summary_after, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                iteration.iteration_id,
                iteration.run_id,
                iteration.iteration_number,
                iteration.plan_id,
                iteration.hypotheses_count,
                iteration.changes_applied,
                iteration.outcome,
                json.dumps(iteration.summary_before, ensure_ascii=False),
                json.dumps(iteration.summary_after, ensure_ascii=False),
                iteration.created_at,
            ),
        )
        self.run_db.conn.commit()

    def get_iteration_history(self) -> list[dict[str, Any]]:
        """Return all iteration records ordered by iteration_number."""
        rows = self.run_db.conn.execute(
            "SELECT * FROM iterations ORDER BY iteration_number"
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM iterations LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]

    def get_proposed_experiments(self) -> list[dict[str, Any]]:
        """Return all experiments with status='proposed'."""
        rows = self.run_db.conn.execute(
            "SELECT * FROM experiments WHERE status = 'proposed' ORDER BY created_at"
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM experiments LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]
