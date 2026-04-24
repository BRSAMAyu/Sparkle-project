#!/usr/bin/env python3
"""SGW v2 Meta Loop: continuous improvement cycle.

Runs SGW orchestrator in a subprocess, evaluates results, adjusts parameters,
and repeats. Supports random exploration injection and convergence detection.

Usage:
    python -m sgw_v2.meta.meta_loop \\
        --db-path ./sgw_runs.db \\
        --persona-library ./persona_library.json \\
        --adversarial-playbook ./adversarial_playbook.json \\
        --max-iterations 100 \\
        --exploration-every-n 5

The loop:
  1. Run SGW with current config (subprocess)
  2. Diagnose failures
  3. Plan parameter changes
  4. Evaluate (compare before/after with significance test)
  5. Adopt or rollback
  6. Inject random exploration every N iterations
  7. Repeat until convergence or max_iterations
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Ensure sgw_v2 is importable
META_DIR = Path(__file__).resolve().parent
SGW_V2_DIR = META_DIR.parent
SCRIPTS_DIR = SGW_V2_DIR.parent
SGW_DIR = SCRIPTS_DIR / "sgw"

for p in [str(SCRIPTS_DIR), str(SGW_V2_DIR), str(SGW_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sgw_v2.storage.db import RunDB
from sgw_v2.meta.meta_orchestrator import MetaOrchestrator
from sgw_v2.rl.environment import PolicyZoo


RL_MODES = ("off", "shadow", "rl")
RL_RECIPES: dict[str, dict[str, Any]] = {
    "default": {},
    "compliance_focus": {
        "soft_violation_threshold": 0.90,
        "soft_violation_rate_limit": 0.03,
        "audit_sample_rate": 0.40,
    },
    "authenticity_focus": {
        "authenticity_sample_rate": 0.40,
        "audit_sample_rate": 0.30,
    },
    "fast_iteration": {
        "wall_clock_hours": 0.05,
        "min_sessions": 2,
        "min_turns": 10,
        "turn_target": 6,
        "adversarial_sessions": 1,
    },
    "stress_test": {
        "adversarial_sessions": 12,
        "soft_violation_threshold": 0.80,
        "soft_violation_rate_limit": 0.10,
    },
}


def _load_config(db: RunDB) -> dict[str, Any]:
    """Load the most recent run's config, or return defaults."""
    run_id = db.latest_run_id()
    if run_id:
        run_data = db.get_run(run_id)
        if run_data:
            return json.loads(run_data.get("scenario_config", "{}"))
    return {
        "wall_clock_hours": 0.5,
        "min_sessions": 20,
        "min_turns": 200,
        "turn_target": 12,
        "adversarial_sessions": 4,
        "soft_violation_threshold": 0.85,
        "soft_violation_rate_limit": 0.05,
        "audit_sample_rate": 0.25,
        "authenticity_sample_rate": 0.20,
    }


def _run_sgw_subprocess(
    *,
    persona_library: Path,
    adversarial_playbook: Path,
    output_dir: Path,
    shared_db_path: Path,
    config: dict[str, Any],
) -> int:
    """Run the SGW orchestrator as a subprocess. Returns exit code.

    Critical design notes
    ---------------------
    * ``--db-path`` is passed explicitly so the orchestrator writes its run
      records into the *same* SQLite file that meta_loop reads.  Without this,
      ``db.latest_run_id()`` always returns None and the RL loop never adapts.
    * Dynamic RL parameters (soft_violation_threshold, audit_sample_rate, etc.)
      are injected as environment variables because the orchestrator reads them
      from the environment, not from CLI flags.  Passing them here ensures that
      every policy-adjusted parameter actually takes effect in the next run.
    * The subprocess timeout is derived from wall_clock_hours so long runs are
      not killed prematurely (adds a 10-minute safety buffer).
    """
    report_path = output_dir / "report.md"
    checkpoint_path = output_dir / "checkpoint.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(SGW_DIR / "sgw_orchestrator.py"),
        "--persona-library", str(persona_library),
        "--adversarial-playbook", str(adversarial_playbook),
        "--report-path", str(report_path),
        "--checkpoint-path", str(checkpoint_path),
        "--db-path", str(shared_db_path),         # FIX: share a single DB
        "--wall-clock-hours", str(config.get("wall_clock_hours", 0.5)),
        "--min-sessions", str(config.get("min_sessions", 20)),
        "--min-turns", str(config.get("min_turns", 200)),
        "--turn-target", str(config.get("turn_target", 12)),
        "--adversarial-sessions", str(config.get("adversarial_sessions", 4)),
    ]

    # FIX: inject RL-adjustable parameters as env vars so they actually reach
    # the orchestrator's OrchestratorConfig (which reads from os.getenv).
    env_overrides: dict[str, str] = {}
    _ENV_MAP = {
        "soft_violation_threshold": "SGW_SOFT_VIOLATION_THRESHOLD",
        "audit_sample_rate":        "SGW_AUDIT_SAMPLE_RATE",
        "authenticity_sample_rate": "SGW_AUTHENTICITY_SAMPLE_RATE",
        "expression_validation_retries": "SGW_EXPRESSION_VALIDATION_RETRIES",
        "max_history_pairs":        "SGW_MAX_HISTORY_PAIRS",
        "session_turn_slice":       "SGW_SESSION_TURN_SLICE",
        "claude_timeout_seconds":   "SGW_CLAUDE_TIMEOUT_SECONDS",
        "claude_failure_backoff_seconds": "SGW_CLAUDE_FAILURE_BACKOFF_SECONDS",
    }
    for config_key, env_key in _ENV_MAP.items():
        if config_key in config:
            env_overrides[env_key] = str(config[config_key])

    subprocess_env = {**os.environ, **env_overrides}

    wall_hours = config.get("wall_clock_hours", 0.5)
    timeout_seconds = int(wall_hours * 3600) + 600  # +10 min safety buffer

    print(f"[meta-loop] Launching SGW subprocess (timeout={timeout_seconds}s)...")
    print(f"[meta-loop]   cmd: {' '.join(cmd[:6])}...")
    if env_overrides:
        print(f"[meta-loop]   env overrides: {json.dumps(env_overrides)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=subprocess_env,
    )

    if result.returncode != 0:
        print(f"[meta-loop] SGW exited with code {result.returncode}")
        if result.stderr:
            print(f"[meta-loop] stderr: {result.stderr[-500:]}")

    return result.returncode


def _inject_random_exploration(config: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Inject random parameter perturbation for exploration."""
    new_config = dict(config)

    # Pick 1-2 parameters to perturb
    params = [
        ("soft_violation_threshold", 0.80, 0.95, 0.05),
        ("audit_sample_rate", 0.10, 0.50, 0.05),
        ("authenticity_sample_rate", 0.10, 0.50, 0.05),
        ("turn_target", 8, 16, 1),
    ]

    n_perturb = rng.randint(1, 2)
    chosen = rng.sample(params, min(n_perturb, len(params)))
    for param, lo, hi, step in chosen:
        current = new_config.get(param, (lo + hi) / 2)
        delta = rng.choice([-step, step])
        new_val = round(max(lo, min(hi, current + delta)), 4)
        if new_val != current:
            new_config[param] = new_val
            print(f"[meta-loop] Exploration: {param} {current} -> {new_val}")

    return new_config


def _check_convergence(db: RunDB, window: int = 5) -> bool:
    """Check if the last N iterations show convergence (all neutral)."""
    rows = db.conn.execute(
        "SELECT outcome FROM iterations ORDER BY created_at DESC LIMIT ?",
        (window,),
    ).fetchall()
    if len(rows) < window:
        return False
    outcomes = [row[0] for row in rows]
    # Converged if all recent outcomes are neutral or improved_sig
    non_neutral = [o for o in outcomes if o not in ("neutral", "improved_sig")]
    return len(non_neutral) == 0


def run_meta_loop(
    *,
    db_path: Path,
    persona_library: Path,
    adversarial_playbook: Path,
    max_iterations: int = 100,
    exploration_every_n: int = 5,
    convergence_window: int = 5,
    seed: int = 42,
    rl_mode: str = "rl",
    rl_recipe: str = "default",
    dashboard: bool = False,
) -> int:
    """Run the full meta-orchestration loop.

    rl_mode:
        off    - no meta-iteration adaptation; runs SGW subprocess only.
        shadow - run diagnosis + planning, log decisions, but do not mutate current_config.
        rl     - full loop (default): diagnose, plan, evaluate, adopt, explore.
    rl_recipe:
        Named preset applied on top of the config defaults (see RL_RECIPES).
    dashboard:
        When True, print a single-line dashboard summary per iteration (stdout) for easy parsing.
    """
    if rl_mode not in RL_MODES:
        raise ValueError(f"invalid rl_mode {rl_mode!r}; expected one of {RL_MODES}")
    if rl_recipe not in RL_RECIPES:
        raise ValueError(f"invalid rl_recipe {rl_recipe!r}; expected one of {tuple(RL_RECIPES)}")

    db = RunDB(db_path)
    rng = random.Random(seed)
    output_dir = db_path.parent / "meta_loop_output"
    policy_dir = db_path.parent / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_zoo = PolicyZoo(policy_dir)

    current_config = _load_config(db)
    recipe_overrides = RL_RECIPES[rl_recipe]
    if recipe_overrides:
        current_config = {**current_config, **recipe_overrides}
        print(f"[meta-loop] Applied rl_recipe={rl_recipe}: {json.dumps(recipe_overrides)}")
    print(f"[meta-loop] rl_mode={rl_mode} dashboard={dashboard}")
    print(f"[meta-loop] Starting with config: {json.dumps(current_config, indent=2)}")

    consecutive_neutral = 0

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*60}")
        print(f"[meta-loop] Iteration {iteration}/{max_iterations}")
        print(f"{'='*60}")

        # Step 1: Run SGW with current config.
        # db_path is passed explicitly so the orchestrator writes into the same
        # SQLite file that this loop reads — without it latest_run_id() is always None.
        exit_code = _run_sgw_subprocess(
            persona_library=persona_library,
            adversarial_playbook=adversarial_playbook,
            output_dir=output_dir / f"iter_{iteration}",
            shared_db_path=db_path,
            config=current_config,
        )

        if exit_code != 0:
            print(f"[meta-loop] SGW failed with exit code {exit_code}, skipping diagnosis")
            continue

        # Step 2: Get latest run from DB
        latest_run_id = db.latest_run_id()
        if not latest_run_id:
            print("[meta-loop] No run found in DB after subprocess, skipping")
            continue

        print(f"[meta-loop] Latest run: {latest_run_id[:12]}")

        if rl_mode == "off":
            consecutive_neutral += 1
            if dashboard:
                print(f"[dashboard] iter={iteration} mode=off run={latest_run_id[:12]}")
            continue

        # Step 3: Run meta-iteration (diagnose -> plan)
        meta = MetaOrchestrator(db, current_config)
        result = meta.run_iteration(latest_run_id)

        if result is None:
            print("[meta-loop] No iteration produced, continuing")
            if dashboard:
                print(f"[dashboard] iter={iteration} mode={rl_mode} outcome=none")
            continue

        print(f"[meta-loop] Iteration result: {result.outcome}, hypotheses={result.hypotheses_count}, changes={result.changes_applied}")

        # Step 4: Evaluate if we have a previous run to compare against
        evaluation_outcome = "pending"
        snapshot_id: str | None = None
        if result.plan_id and result.changes_applied > 0:
            evaluation = meta.evaluate_iteration(result.iteration_id, latest_run_id)
            if evaluation:
                evaluation_outcome = evaluation.outcome
                print(f"[meta-loop] Evaluation: {evaluation.outcome}")

                if rl_mode == "shadow":
                    print("[meta-loop] shadow mode: logging decision without adopting")
                    consecutive_neutral += 1
                else:
                    current_config = meta.current_config
                    if evaluation.outcome == "regressed":
                        consecutive_neutral = 0
                        print("[meta-loop] Regressed — keeping original config")
                    elif evaluation.outcome == "improved_sig":
                        consecutive_neutral = 0
                        print("[meta-loop] Significant improvement — adopted new config")
                        # Save a config snapshot on every significant improvement
                        # so the state can be restored via 'cli rollback' if needed.
                        try:
                            snapshot_id = policy_zoo.save_config_snapshot(
                                current_config=current_config,
                                metadata={
                                    "iteration": iteration,
                                    "run_id": latest_run_id,
                                    "outcome": evaluation.outcome,
                                    "rl_mode": rl_mode,
                                    "rl_recipe": rl_recipe,
                                },
                            )
                            print(f"[meta-loop] Config snapshot saved: {snapshot_id}")
                        except Exception as exc:
                            print(f"[meta-loop] Warning: config snapshot failed: {exc}")
                    elif evaluation.outcome == "improved_nonsig":
                        print("[meta-loop] Non-significant improvement — adopting cautiously")
                        consecutive_neutral += 1
                    else:
                        consecutive_neutral += 1
            else:
                consecutive_neutral += 1
        else:
            consecutive_neutral += 1

        if dashboard:
            print(
                f"[dashboard] iter={iteration} mode={rl_mode} "
                f"outcome={result.outcome} eval={evaluation_outcome} "
                f"hypotheses={result.hypotheses_count} changes={result.changes_applied}"
                + (f" snapshot={snapshot_id}" if snapshot_id else "")
            )

        # Step 5: Random exploration injection (rl mode only)
        if rl_mode == "rl" and iteration % exploration_every_n == 0:
            print("[meta-loop] Injecting random exploration...")
            current_config = _inject_random_exploration(current_config, rng)

        # Step 6: Check convergence
        if consecutive_neutral >= convergence_window:
            print(f"[meta-loop] {consecutive_neutral} consecutive neutral iterations, checking convergence...")
            if _check_convergence(db, convergence_window):
                print("[meta-loop] CONVERGED — system stable, exiting loop")
                break

        # Print current config state
        print(f"[meta-loop] Current config: {json.dumps(current_config, indent=2)}")

    print(f"\n[meta-loop] Completed {iteration} iterations")
    print(f"[meta-loop] Final config: {json.dumps(current_config, indent=2)}")

    # Print iteration history
    meta_final = MetaOrchestrator(db, current_config)
    history = meta_final.get_iteration_history()
    print(f"\n[meta-loop] Iteration history ({len(history)} iterations):")
    for record in history:
        print(f"  #{record.get('iteration_number', '?')}: {record.get('outcome', '?')} "
              f"(hypotheses={record.get('hypotheses_count', 0)}, changes={record.get('changes_applied', 0)})")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SGW v2 meta-orchestration loop")
    parser.add_argument("--db-path", required=True, type=Path, help="Path to sgw_runs.db")
    parser.add_argument("--persona-library", required=True, type=Path)
    parser.add_argument("--adversarial-playbook", required=True, type=Path)
    parser.add_argument("--max-iterations", type=int, default=100)
    parser.add_argument("--exploration-every-n", type=int, default=5)
    parser.add_argument("--convergence-window", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--rl-mode",
        choices=list(RL_MODES),
        default="rl",
        help="off=no adaptation, shadow=log-only decisions, rl=full adaptive loop (default)",
    )
    parser.add_argument(
        "--rl-recipe",
        choices=list(RL_RECIPES),
        default="default",
        help="Named parameter preset to seed initial config.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Emit one-line iteration dashboard summaries to stdout.",
    )
    args = parser.parse_args()

    return run_meta_loop(
        db_path=args.db_path,
        persona_library=args.persona_library,
        adversarial_playbook=args.adversarial_playbook,
        max_iterations=args.max_iterations,
        exploration_every_n=args.exploration_every_n,
        convergence_window=args.convergence_window,
        seed=args.seed,
        rl_mode=args.rl_mode,
        rl_recipe=args.rl_recipe,
        dashboard=args.dashboard,
    )


if __name__ == "__main__":
    raise SystemExit(main())
