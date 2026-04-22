#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from sgw_v2.storage.db import RunDB, compute_config_hash


FAST_CONFIG = {
    "wall_clock_hours": 0.001,
    "min_sessions": 1,
    "min_turns": 1,
    "turn_target": 1,
    "adversarial_sessions": 1,
    "soft_violation_threshold": 0.85,
    "soft_violation_rate_limit": 0.05,
    "audit_sample_rate": 0.25,
    "authenticity_sample_rate": 0.20,
}


@dataclass
class PhaseResult:
    phase: str
    command: list[str]
    status: str
    return_code: int | None
    duration_seconds: float
    notes: list[str]
    db_snapshot: dict[str, Any]
    stdout_path: str | None = None
    stderr_path: str | None = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Stage40 SGW dogfood matrix.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "artifacts" / "stage40" / "sgw")
    parser.add_argument("--off-db", type=Path, default=Path("/tmp/stage40_off.db"))
    parser.add_argument("--shadow-db", type=Path, default=Path("/tmp/stage40_shadow.db"))
    parser.add_argument("--rl-db", type=Path, default=Path("/tmp/stage40_rl.db"))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser.parse_args()


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def _seed_bootstrap_run(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    db = RunDB(db_path)
    run_id = db.create_run(
        scenario_id="stage40_bootstrap",
        config_hash=compute_config_hash(FAST_CONFIG),
        git_sha=_git_sha(),
        scenario_config=FAST_CONFIG,
        prompt_hashes={},
        model_versions={},
    )
    db.finish_run(
        run_id,
        status="bootstrap",
        summary={"bootstrap": True, "note": "Stage40 fast config seed"},
    )
    db.close()


def _meta_loop_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{SCRIPTS_ROOT}{os.pathsep}{current}" if current else str(SCRIPTS_ROOT)
    return env


def _meta_loop_help() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "sgw_v2.meta.meta_loop", "--help"],
        cwd=REPO_ROOT,
        env=_meta_loop_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    return (result.stdout or "") + (result.stderr or "")


def _db_snapshot(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"exists": False}

    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        counts: dict[str, int] = {}
        for table in ("runs", "sessions", "turns", "audits", "violations", "experiments", "iterations", "rl_trajectories"):
            if table in tables:
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

        snapshot: dict[str, Any] = {
            "exists": True,
            "tables": sorted(tables),
            "counts": counts,
            "non_bootstrap_runs": int(
                conn.execute("SELECT COUNT(*) FROM runs WHERE scenario_id != 'stage40_bootstrap'").fetchone()[0]
            )
            if "runs" in tables
            else 0,
        }

        if "runs" in tables:
            snapshot["run_rows"] = [
                {
                    "run_id": row[0],
                    "scenario_id": row[1],
                    "status": row[2],
                }
                for row in conn.execute(
                    "SELECT run_id, scenario_id, status FROM runs ORDER BY started_at"
                ).fetchall()
            ]

        if "rl_trajectories" in tables:
            snapshot["action_source_counts"] = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT action_source, COUNT(*) FROM rl_trajectories GROUP BY action_source"
                ).fetchall()
            }

        return snapshot
    finally:
        conn.close()


def _run_phase(
    *,
    phase: str,
    db_path: Path,
    extra_args: list[str],
    output_dir: Path,
    timeout_seconds: int,
    required_tables: tuple[str, ...] = (),
    min_non_bootstrap_runs: int = 0,
    min_iterations: int = 0,
) -> PhaseResult:
    _seed_bootstrap_run(db_path)

    stdout_path = output_dir / f"{phase}.stdout.log"
    stderr_path = output_dir / f"{phase}.stderr.log"
    cmd = [
        sys.executable,
        "-m",
        "sgw_v2.meta.meta_loop",
        "--db-path",
        str(db_path),
        "--persona-library",
        str(REPO_ROOT / "scripts" / "sgw" / "persona_library.json"),
        "--adversarial-playbook",
        str(REPO_ROOT / "scripts" / "sgw" / "adversarial_playbook.json"),
        *extra_args,
    ]
    started = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=_meta_loop_env(),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout_path.write_text(result.stdout or "", encoding="utf-8")
        stderr_path.write_text(result.stderr or "", encoding="utf-8")
        snapshot = _db_snapshot(db_path)
        status = "pass" if result.returncode == 0 else "failed"
        notes: list[str] = []
        if result.returncode != 0:
            stderr_tail = (result.stderr or "").strip().splitlines()[-5:]
            if stderr_tail:
                notes.append("stderr_tail=" + " | ".join(stderr_tail))
        if result.returncode == 0:
            missing_tables = [
                table for table in required_tables
                if table not in snapshot.get("tables", [])
            ]
            if missing_tables:
                status = "failed_assertion"
                notes.append("missing_tables=" + ",".join(missing_tables))
            if int(snapshot.get("non_bootstrap_runs", 0)) < min_non_bootstrap_runs:
                status = "failed_assertion"
                notes.append(
                    f"non_bootstrap_runs={snapshot.get('non_bootstrap_runs', 0)} < {min_non_bootstrap_runs}"
                )
            if int(snapshot.get("counts", {}).get("iterations", 0)) < min_iterations:
                status = "failed_assertion"
                notes.append(
                    f"iterations={snapshot.get('counts', {}).get('iterations', 0)} < {min_iterations}"
                )
        return PhaseResult(
            phase=phase,
            command=cmd,
            status=status,
            return_code=result.returncode,
            duration_seconds=round(time.time() - started, 2),
            notes=notes,
            db_snapshot=snapshot,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8")
        stderr_path.write_text((exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8")
        return PhaseResult(
            phase=phase,
            command=cmd,
            status="timeout",
            return_code=None,
            duration_seconds=round(time.time() - started, 2),
            notes=[f"timeout after {timeout_seconds}s"],
            db_snapshot=_db_snapshot(db_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )


def _blocked_phase(phase: str, command: list[str], note: str, db_path: Path) -> PhaseResult:
    return PhaseResult(
        phase=phase,
        command=command,
        status="blocked",
        return_code=None,
        duration_seconds=0.0,
        notes=[note],
        db_snapshot=_db_snapshot(db_path),
    )


def _run_rl_scaffolding_probe(output_dir: Path) -> dict[str, Any]:
    stdout_path = output_dir / "rl_scaffolding.stdout.log"
    stderr_path = output_dir / "rl_scaffolding.stderr.log"
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "sgw_v2" / "tests" / "test_rl_scaffolding.py")]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=_meta_loop_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")
    return {
        "command": cmd,
        "status": "pass" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def main() -> int:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    help_output = _meta_loop_help()
    supports_rl_flags = "--rl-mode" in help_output and "--dashboard" in help_output and "--rl-recipe" in help_output

    results: list[PhaseResult] = []
    results.append(
        _run_phase(
            phase="Phase A",
            db_path=args.off_db,
            extra_args=["--max-iterations", "3"],
            output_dir=args.output_dir,
            timeout_seconds=args.timeout_seconds,
            required_tables=("runs", "sessions", "turns", "audits", "iterations"),
            min_non_bootstrap_runs=1,
            min_iterations=3,
        )
    )

    shadow_cmd = [
        sys.executable,
        "-m",
        "sgw_v2.meta.meta_loop",
        "--db-path",
        str(args.shadow_db),
        "--persona-library",
        str(REPO_ROOT / "scripts" / "sgw" / "persona_library.json"),
        "--adversarial-playbook",
        str(REPO_ROOT / "scripts" / "sgw" / "adversarial_playbook.json"),
        "--rl-mode",
        "shadow",
        "--max-iterations",
        "10",
        "--dashboard",
    ]
    rl_cmd = [
        sys.executable,
        "-m",
        "sgw_v2.meta.meta_loop",
        "--db-path",
        str(args.rl_db),
        "--persona-library",
        str(REPO_ROOT / "scripts" / "sgw" / "persona_library.json"),
        "--adversarial-playbook",
        str(REPO_ROOT / "scripts" / "sgw" / "adversarial_playbook.json"),
        "--rl-mode",
        "rl",
        "--rl-recipe",
        "fast_iteration",
        "--max-iterations",
        "5",
        "--dashboard",
    ]

    if supports_rl_flags:
        results.append(
            _run_phase(
                phase="Phase B",
                db_path=args.shadow_db,
                extra_args=["--rl-mode", "shadow", "--max-iterations", "10", "--dashboard"],
                output_dir=args.output_dir,
                timeout_seconds=args.timeout_seconds,
            )
        )
        results.append(
            _run_phase(
                phase="Phase C",
                db_path=args.rl_db,
                extra_args=["--rl-mode", "rl", "--rl-recipe", "fast_iteration", "--max-iterations", "5", "--dashboard"],
                output_dir=args.output_dir,
                timeout_seconds=args.timeout_seconds,
            )
        )
    else:
        results.append(
            _blocked_phase(
                "Phase B",
                shadow_cmd,
                "current meta_loop CLI does not expose --rl-mode/--dashboard",
                args.shadow_db,
            )
        )
        results.append(
            _blocked_phase(
                "Phase C",
                rl_cmd,
                "current meta_loop CLI does not expose --rl-mode/--rl-recipe/--dashboard",
                args.rl_db,
            )
        )

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "supports_rl_flags": supports_rl_flags,
        "meta_loop_help": help_output.strip(),
        "phases": [asdict(item) for item in results],
        "rl_scaffolding_probe": _run_rl_scaffolding_probe(args.output_dir),
    }

    summary_path = args.output_dir / "dogfood_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary_path={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
