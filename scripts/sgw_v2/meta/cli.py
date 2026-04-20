"""SGW v2 Meta-orchestrator CLI.

Usage:
    python -m sgw_v2.meta.cli --db-path <path> diagnose [--run-id <id>]
    python -m sgw_v2.meta.cli --db-path <path> plan [--run-id <id>]
    python -m sgw_v2.meta.cli --db-path <path> iterate [--run-id <id>]
    python -m sgw_v2.meta.cli --db-path <path> history
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure sgw_v2 is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sgw_v2.storage.db import RunDB
from sgw_v2.meta.diagnostic_agent import DiagnosticAgent
from sgw_v2.meta.experiment_planner import ExperimentPlanner
from sgw_v2.meta.meta_orchestrator import MetaOrchestrator


def cmd_diagnose(args: argparse.Namespace) -> int:
    db = RunDB(Path(args.db_path))
    run_id = args.run_id or db.latest_run_id()
    if not run_id:
        print("No runs found in database.")
        return 1

    agent = DiagnosticAgent(db)
    hypotheses = agent.diagnose(run_id)

    if not hypotheses:
        print(f"Run {run_id}: No issues detected.")
        return 0

    print(f"Run {run_id}: {len(hypotheses)} hypotheses")
    for h in hypotheses:
        print(f"  [{h.severity}] {h.hypothesis_id}: {h.description}")
        for e in h.evidence:
            print(f"    evidence: {e}")
        print(f"    action: {h.suggested_action}")
        print(f"    confidence: {h.confidence}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    db = RunDB(Path(args.db_path))
    run_id = args.run_id or db.latest_run_id()
    if not run_id:
        print("No runs found in database.")
        return 1

    # Load current config from the run
    run_data = db.get_run(run_id)
    if not run_data:
        print(f"Run {run_id} not found.")
        return 1
    config = json.loads(run_data.get("scenario_config", "{}"))

    agent = DiagnosticAgent(db)
    planner = ExperimentPlanner(config)
    hypotheses = agent.diagnose(run_id)

    if not hypotheses:
        print("No issues to plan for.")
        return 0

    plan = planner.plan(hypotheses, run_id)
    if not plan:
        print("Issues detected but no auto-adjustable parameters.")
        for h in hypotheses:
            print(f"  [{h.severity}] {h.hypothesis_id}: {h.suggested_action}")
        return 0

    print(f"Plan: {plan.plan_id} (priority: {plan.priority})")
    for pc in plan.parameter_changes:
        print(f"  {pc.parameter}: {pc.current_value} -> {pc.proposed_value}")
        print(f"    reason: {pc.rationale}")
    print(f"  Expected: {plan.expected_outcome}")
    return 0


def cmd_iterate(args: argparse.Namespace) -> int:
    db = RunDB(Path(args.db_path))
    run_id = args.run_id or db.latest_run_id()
    if not run_id:
        print("No runs found in database.")
        return 1

    run_data = db.get_run(run_id)
    config = json.loads(run_data.get("scenario_config", "{}"))

    meta = MetaOrchestrator(db, config)
    result = meta.run_iteration(run_id)

    if result is None:
        print("No iteration produced.")
        return 0

    print(f"Iteration {result.iteration_number}: {result.outcome}")
    print(f"  Hypotheses: {result.hypotheses_count}")
    print(f"  Changes: {result.changes_applied}")
    if result.outcome == "neutral":
        print("  System healthy, no changes needed.")
    else:
        print(f"  New config: {json.dumps(meta.current_config, indent=2)}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    db = RunDB(Path(args.db_path))
    run_data = db.get_run(db.latest_run_id() or "")
    config = json.loads(run_data.get("scenario_config", "{}")) if run_data else {}

    meta = MetaOrchestrator(db, config)
    history = meta.get_iteration_history()

    if not history:
        print("No iterations recorded.")
        return 0

    for record in history:
        print(f"Iteration {record['iteration_number']}: {record['outcome']}")
        print(f"  Run: {record['run_id']}")
        if record.get('plan_id'):
            print(f"  Plan: {record['plan_id']}")
        print(f"  Changes: {record.get('changes_applied', 0)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SGW v2 meta-orchestrator")
    parser.add_argument("--db-path", required=True, help="Path to sgw_runs.db")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("--run-id", default=None)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--run-id", default=None)

    iterate_parser = subparsers.add_parser("iterate")
    iterate_parser.add_argument("--run-id", default=None)

    subparsers.add_parser("history")

    args = parser.parse_args()

    commands = {
        "diagnose": cmd_diagnose,
        "plan": cmd_plan,
        "iterate": cmd_iterate,
        "history": cmd_history,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
