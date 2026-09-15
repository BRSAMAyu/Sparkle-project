from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.simulation_run import SimulationRun
from app.services import simulation_runner
from app.services.simulation_runner import run_benchmark_suite


@pytest.mark.asyncio
async def test_run_benchmark_suite_persists_report(db_session, tmp_path):
    report = await run_benchmark_suite(
        "full",
        session=db_session,
        reports_dir=tmp_path,
        commit="testcommit",
    )

    assert report.status == "passed"
    assert report.total == 24
    assert report.passed == 24
    assert report.simulation_run_id is not None
    assert report.markdown_path is not None
    assert Path(report.markdown_path).exists()

    simulation_runs = SimulationRun.__table__
    result = await db_session.execute(
        select(simulation_runs.c.state, simulation_runs.c.payload)
        .where(simulation_runs.c.scenario_key == "goalbench:full")
    )
    state, payload = result.one()
    assert state == "passed"
    assert payload["pass_rate"] == 1.0
    assert payload["total"] == 24


@pytest.mark.asyncio
async def test_run_benchmark_suite_blocks_high_risk_failures(monkeypatch, tmp_path):
    def fake_run_selected_suites(suites):
        high_risk = next(
            scenario
            for scenarios in suites.values()
            for scenario in scenarios
            if scenario.risk_level == "high"
        )
        return {
            "total": 1,
            "passed": 0,
            "failed": 1,
            "pass_rate": 0.0,
            "reports": [
                {
                    "scenario_id": high_risk.scenario_id,
                    "passed": False,
                    "violations": ["spine_integrity: forced regression"],
                    "cost_estimate": {"estimated_turns": 1.0},
                    "latency_estimate": {"estimated_seconds": 2.0},
                }
            ],
            "suite_breakdown": {"ExamSprintBench": {"total": 1, "passed": 0, "pass_rate": 0.0}},
        }

    monkeypatch.setattr(simulation_runner, "_run_selected_suites", fake_run_selected_suites)

    report = await run_benchmark_suite(
        "full",
        write_report=True,
        reports_dir=tmp_path,
        commit="blockedcommit",
    )

    assert report.status == "blocked"
    assert report.exit_code == 1
    assert report.gate["high_risk_failures"]
    assert Path(report.markdown_path or "").exists()


def test_simulation_benchmark_cli_skip_db(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "backend")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.scripts.run_simulation_benchmark",
            "--suite=full",
            "--skip-db",
            "--reports-dir",
            str(tmp_path),
            "--commit",
            "clicommit",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert '"status": "passed"' in result.stdout
    assert list(tmp_path.glob("*_clicommit.md"))
