"""Meta-orchestrator: the outer loop that drives iterative SGW improvement.

Cycle: Run -> Diagnose -> Plan -> Execute (next run) -> Compare -> Repeat

This module provides:
- MetaOrchestrator: orchestrates the full improvement cycle
- IterationResult: tracks the outcome of each iteration
- SQLite persistence for experiments and iterations
"""
from __future__ import annotations

import json
import math
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
    pre_change_config TEXT,
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
        """Create Phase 4 tables if they don't exist, and migrate older schemas."""
        self.run_db.conn.executescript(_PHASE4_SCHEMA)
        # Migration: add pre_change_config column if missing
        try:
            self.run_db.conn.execute("ALTER TABLE iterations ADD COLUMN pre_change_config TEXT")
        except Exception:  # noqa: BLE001
            pass  # Column already exists
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

        # Step 4: Record iteration with pre-change config snapshot
        pre_change_config = dict(self.current_config)
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

        self._save_iteration(iteration, pre_change_config=pre_change_config)

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

        # Update experiment status based on outcome
        if iteration.plan_id:
            exp_status = "completed" if outcome.startswith("improved") else "rejected"
            self.run_db.conn.execute(
                "UPDATE experiments SET status = ?, updated_at = ? WHERE plan_id = ?",
                (exp_status, _utcnow_iso(), iteration.plan_id),
            )
            self.run_db.conn.commit()

        # If significantly regressed, revert config from saved snapshot
        if outcome.startswith("regressed_sig"):
            self._revert_config(iteration_id)

        return iteration

    def _judge_outcome(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        """Judge outcome with statistical significance testing.

        Returns one of:
        - improved_sig: Significant improvement (auto-adopt)
        - improved_nonsig: Improvement but not significant (adopt cautiously)
        - regressed_sig: Significant regression (auto-rollback)
        - regressed_nonsig: Regression but not significant
        - neutral: No meaningful change
        """
        # Minimum sample size gate
        min_audits = min(
            before.get("audits_total", 0) + before.get("authenticity_total", 0),
            after.get("audits_total", 0) + after.get("authenticity_total", 0),
        )
        if min_audits < 200:
            # Not enough samples for significance — fall back to direction-only
            return self._judge_direction_only(before, after)

        # Two-proportion z-test for soft violation rate
        soft_before_n = before.get("audits_total", 0)
        soft_after_n = after.get("audits_total", 0)
        soft_before_x = before.get("soft_violations", 0)
        soft_after_x = after.get("soft_violations", 0)

        z_soft = self._z_test_two_proportions(soft_before_x, soft_before_n, soft_after_x, soft_after_n)
        # Negative z means after has lower rate (improvement)

        # Two-proportion z-test for authenticity failure rate
        auth_before_n = before.get("authenticity_total", 0)
        auth_after_n = after.get("authenticity_total", 0)
        auth_before_x = before.get("authenticity_failures", 0)
        auth_after_x = after.get("authenticity_failures", 0)

        z_auth = self._z_test_two_proportions(auth_before_x, auth_before_n, auth_after_x, auth_after_n)

        # Hard violations: any increase is always significant
        hard_delta = after.get("hard_violations", 0) - before.get("hard_violations", 0)

        # Compute composite score and significance
        alpha = 1.96  # 95% confidence
        improved_dimensions = 0
        regressed_dimensions = 0
        sig_improved = 0
        sig_regressed = 0

        # Soft violations: z_soft > 0 means after has higher rate (regression)
        if z_soft is not None and abs(z_soft) > 0.01:
            if z_soft > alpha:
                regressed_dimensions += 1
                sig_regressed += 1
            elif z_soft < -alpha:
                improved_dimensions += 1
                sig_improved += 1
            elif z_soft > 0:
                regressed_dimensions += 1
            else:
                improved_dimensions += 1

        # Authenticity failures: z_auth > 0 means after has higher failure rate (regression)
        if z_auth is not None and abs(z_auth) > 0.01:
            if z_auth > alpha:
                regressed_dimensions += 1
                sig_regressed += 1
            elif z_auth < -alpha:
                improved_dimensions += 1
                sig_improved += 1
            elif z_auth > 0:
                regressed_dimensions += 1
            else:
                improved_dimensions += 1

        # Hard violations override
        if hard_delta > 0:
            regressed_dimensions += 2
            sig_regressed += 1

        # One-vote veto: authenticity or hard violations regressing significantly
        # is a deal-breaker regardless of soft violation improvements
        auth_sig_regressed = z_auth is not None and z_auth > alpha
        if auth_sig_regressed or hard_delta > 0:
            return "regressed_sig"

        # Final classification (no veto triggered)
        if sig_regressed > 0 and regressed_dimensions > improved_dimensions:
            return "regressed_sig"
        if sig_improved > 0 and improved_dimensions > regressed_dimensions:
            return "improved_sig"
        if improved_dimensions > regressed_dimensions:
            return "improved_nonsig"
        if regressed_dimensions > improved_dimensions:
            return "regressed_nonsig"
        return "neutral"

    @staticmethod
    def _z_test_two_proportions(x1: int, n1: int, x2: int, n2: int) -> float | None:
        """Two-proportion z-test. Returns z-statistic or None if insufficient data."""
        if n1 < 10 or n2 < 10:
            return None
        p1 = x1 / n1
        p2 = x2 / n2
        p_pool = (x1 + x2) / (n1 + n2)
        if p_pool == 0 or p_pool == 1:
            return 0.0
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se < 1e-10:
            return 0.0
        return (p2 - p1) / se

    def _judge_direction_only(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        """Fallback judge when sample size is insufficient for significance testing."""
        score = 0

        delta_soft = before.get("soft_violation_rate", 0) - after.get("soft_violation_rate", 0)
        if delta_soft > 0.02:
            score += 2
        elif delta_soft < -0.02:
            score -= 2

        delta_auth = after.get("authenticity_mean", 0) - before.get("authenticity_mean", 0)
        if delta_auth > 0.03:
            score += 2
        elif delta_auth < -0.03:
            score -= 2

        if after.get("hard_violations", 0) > before.get("hard_violations", 0):
            score -= 3

        if score >= 2:
            return "improved_nonsig"
        elif score <= -2:
            return "regressed_nonsig"
        return "neutral"

    def _revert_config(self, iteration_id: str) -> None:
        """Revert config to pre-iteration state by reading saved snapshot."""
        row = self.run_db.conn.execute(
            "SELECT pre_change_config FROM iterations WHERE iteration_id = ?",
            (iteration_id,),
        ).fetchone()
        if row and row[0]:
            saved = json.loads(row[0])
            self.current_config = saved
            self.planner = ExperimentPlanner(saved)
            print(f"[meta] Reverted config to pre-change state ({len(saved)} params)")
        else:
            print(f"[meta] WARNING: no pre_change_config found for iteration {iteration_id}")

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

    def _save_iteration(self, iteration: IterationResult, *, pre_change_config: dict[str, Any] | None = None) -> None:
        self.run_db.conn.execute(
            """INSERT OR REPLACE INTO iterations
               (iteration_id, run_id, iteration_number, plan_id, hypotheses_count,
                changes_applied, outcome, summary_before, summary_after, pre_change_config, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                json.dumps(pre_change_config, ensure_ascii=False) if pre_change_config else None,
                iteration.created_at,
            ),
        )
        self.run_db.conn.commit()

    def get_latest_pending_iteration(self) -> dict[str, Any] | None:
        """Return the newest pending iteration awaiting comparison with a future run."""
        row = self.run_db.conn.execute(
            "SELECT * FROM iterations WHERE outcome = 'pending' ORDER BY iteration_number DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM iterations LIMIT 0").description]
        return dict(zip(cols, row))

    def set_iteration_outcome(
        self,
        iteration_id: str,
        *,
        outcome: str,
        summary_after: dict[str, Any] | None = None,
    ) -> None:
        """Finalize an iteration outcome without triggering evaluation logic."""
        self.run_db.conn.execute(
            "UPDATE iterations SET outcome = ?, summary_after = ? WHERE iteration_id = ?",
            (
                outcome,
                json.dumps(summary_after or {}, ensure_ascii=False),
                iteration_id,
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

    # ── DPO Cycle ───────────────────────────────────────

    def run_dpo_cycle(
        self,
        run_id: str,
        *,
        min_pairs: int = 50,
        dpo_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute full DPO cycle: evaluate responses → extract pairs → train.

        Returns a summary dict with keys:
          - pairs_created, pairs_trained, model_trained, response_quality_mean,
            best_val_loss, training_time_seconds
        """
        from ..rl.response_evaluator import ResponseEvaluator
        from ..rl.preference_extractor import PreferenceExtractor
        from ..rl.dpo_trainer import DPOTrainer, DPOTrainingConfig
        from ..rl.dpo_policy import DPOPolicy
        import json

        result: dict[str, Any] = {
            "run_id": run_id,
            "pairs_created": 0,
            "pairs_trained": 0,
            "model_trained": False,
            "response_quality_mean": 0.0,
        }

        # Step 1: Evaluate responses for all turns in all sessions
        evaluator = ResponseEvaluator()
        extractor = PreferenceExtractor(evaluator=evaluator)

        sessions = self._get_sessions_for_run(run_id)
        if not sessions:
            return result

        turns_by_session: dict[str, list[dict[str, Any]]] = {}
        all_qualities: list[float] = []
        for sess in sessions:
            sid = sess["session_id"]
            turns = self._get_turns_for_session(sid)
            turns_by_session[sid] = turns
            for turn in turns:
                q = evaluator.evaluate(turn)
                all_qualities.append(q.overall_score)

        if all_qualities:
            result["response_quality_mean"] = round(
                sum(all_qualities) / len(all_qualities), 4
            )

        # Step 2: Extract preference pairs
        extraction = extractor.extract_from_run(run_id, sessions, turns_by_session)
        result["pairs_created"] = extraction.pairs_created
        result["sessions_scanned"] = extraction.sessions_scanned
        result["turns_evaluated"] = extraction.turns_evaluated

        if extraction.pairs:
            extractor.persist_pairs(extraction.pairs, self.run_db)

        # Step 3: Train DPO model if enough pairs
        untrained_pairs = self.run_db.get_preference_pairs(untrained_only=True, min_margin=0.15)
        if len(untrained_pairs) < min_pairs:
            result["pairs_trained"] = 0
            return result

        cfg = DPOTrainingConfig(**(dpo_config or {}))
        trainer = DPOTrainer(cfg)
        training_result = trainer.train(untrained_pairs)

        result["pairs_trained"] = training_result.n_pairs_trained
        result["best_val_loss"] = training_result.best_val_loss
        result["training_time_seconds"] = training_result.training_time_seconds
        result["converged"] = training_result.converged

        if training_result.n_pairs_trained > 0:
            result["model_trained"] = True

            # Save model
            model_path = self.run_db.db_path.parent / "policy" / "dpo_model.npz"
            training_result.model.save(model_path)

            # Mark pairs as trained
            pair_ids = [p.get("pair_id", "") for p in untrained_pairs]
            self.run_db.mark_pairs_trained(pair_ids)

        return result

    def update_dpo_policy(
        self, policy_router: Any
    ) -> bool:
        """Load trained DPO model into a PolicyRouter. Returns True on success."""
        from ..rl.dpo_policy import DPOPolicy

        model_path = self.run_db.db_path.parent / "policy" / "dpo_model.npz"
        if not model_path.exists():
            return False

        dpo = DPOPolicy()
        if dpo.load_model(model_path):
            policy_router.dpo = dpo
            return True
        return False

    def _get_sessions_for_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.run_db.conn.execute(
            "SELECT * FROM sessions WHERE run_id = ? AND status = 'completed'",
            (run_id,),
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM sessions LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]

    def _get_turns_for_session(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.run_db.conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index",
            (session_id,),
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM turns LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]
