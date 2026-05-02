from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

try:
    from prometheus_client import Counter, Gauge, Histogram
except Exception:  # pragma: no cover - prometheus is optional in local scripts
    Counter = Gauge = Histogram = None  # type: ignore[assignment]


SYSTEM_BENCHMARK_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000b03")
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[3] / "docs" / "benchmarks"
SIMULATION_LAB_PATH = Path(__file__).resolve().parents[1] / "signals" / "simulation_lab.py"
HIGH_RISK_LEVEL = "high"
MEDIUM_RISK_LEVEL = "medium"
TREND_BLOCK_THRESHOLD = 0.10

if Counter is not None:
    SIMULATION_BENCHMARK_RUNS = Counter(
        "sparkle_simulation_benchmark_runs_total",
        "Total SparkleGoalBench benchmark runs",
        ["suite", "status"],
    )
    SIMULATION_BENCHMARK_PASS_RATE = Gauge(
        "sparkle_simulation_benchmark_pass_rate",
        "Latest SparkleGoalBench pass rate",
        ["suite"],
    )
    SIMULATION_BENCHMARK_LATENCY_SECONDS = Histogram(
        "sparkle_simulation_benchmark_latency_seconds",
        "Estimated SparkleGoalBench scenario latency",
        ["suite"],
    )
else:
    SIMULATION_BENCHMARK_RUNS = None
    SIMULATION_BENCHMARK_PASS_RATE = None
    SIMULATION_BENCHMARK_LATENCY_SECONDS = None


def _load_simulation_lab() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_sparkle_goalbench_simulation_lab", SIMULATION_LAB_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load simulation lab from {SIMULATION_LAB_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_simulation_lab = _load_simulation_lab()
ScenarioSimulator = _simulation_lab.ScenarioSimulator
SparkleGoalBench = _simulation_lab.SparkleGoalBench
TestScenario = _simulation_lab.TestScenario


@dataclass(frozen=True)
class BenchmarkReport:
    run_id: str
    suite_name: str
    status: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    gate: dict[str, Any]
    suite_breakdown: dict[str, Any]
    reports: list[dict[str, Any]]
    cost_estimate: dict[str, float]
    latency_estimate: dict[str, float]
    generated_at: str
    commit: str
    markdown_path: str | None = None
    simulation_run_id: str | None = None

    @property
    def exit_code(self) -> int:
        return 1 if self.status == "blocked" else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_name": self.suite_name,
            "status": self.status,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "gate": self.gate,
            "suite_breakdown": self.suite_breakdown,
            "reports": self.reports,
            "cost_estimate": self.cost_estimate,
            "latency_estimate": self.latency_estimate,
            "generated_at": self.generated_at,
            "commit": self.commit,
            "markdown_path": self.markdown_path,
            "simulation_run_id": self.simulation_run_id,
        }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _current_commit() -> str:
    env_sha = os.getenv("GITHUB_SHA") or os.getenv("COMMIT_SHA")
    if env_sha:
        return env_sha[:12]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[3],
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _build_suite_selection(suite_name: str) -> dict[str, list[TestScenario]]:
    suites = SparkleGoalBench.build_full_suite()
    normalized = (suite_name or "full").strip()
    lookup = {name.lower(): name for name in suites}
    domain_lookup = {
        "exam": "ExamSprintBench",
        "exam_sprint": "ExamSprintBench",
        "project": "ProjectDeliveryBench",
        "project_delivery": "ProjectDeliveryBench",
        "job": "JobSearchBench",
        "job_search": "JobSearchBench",
        "multi": "MultiGoalLifeBench",
        "multi_goal": "MultiGoalLifeBench",
        "life": "MultiGoalLifeBench",
    }

    lowered = normalized.lower()
    if lowered in {"full", "all", "sparkle_goal_bench"}:
        return suites
    if lowered in lookup:
        key = lookup[lowered]
        return {key: suites[key]}
    if lowered in domain_lookup:
        key = domain_lookup[lowered]
        return {key: suites[key]}
    raise ValueError(f"Unknown benchmark suite '{suite_name}'. Expected full or one of: {', '.join(suites)}")


def _scenario_index(suites: dict[str, list[TestScenario]]) -> dict[str, tuple[str, TestScenario]]:
    indexed: dict[str, tuple[str, TestScenario]] = {}
    for suite_name, scenarios in suites.items():
        for scenario in scenarios:
            indexed[scenario.scenario_id] = (suite_name, scenario)
    return indexed


def _run_selected_suites(suites: dict[str, list[TestScenario]]) -> dict[str, Any]:
    all_scenarios = [scenario for scenarios in suites.values() for scenario in scenarios]
    aggregate = ScenarioSimulator.run_suite(all_scenarios)
    aggregate["suite_breakdown"] = {
        name: ScenarioSimulator.run_suite(scenarios)
        for name, scenarios in suites.items()
    }
    return aggregate


def _enrich_reports(result: dict[str, Any], suites: dict[str, list[TestScenario]]) -> list[dict[str, Any]]:
    indexed = _scenario_index(suites)
    enriched: list[dict[str, Any]] = []
    for raw in result.get("reports", []):
        suite_name, scenario = indexed.get(str(raw.get("scenario_id")), ("unknown", TestScenario()))
        enriched.append(
            {
                **raw,
                "suite": suite_name,
                "scenario_name": scenario.name,
                "domain": scenario.domain,
                "category": scenario.category,
                "risk_level": scenario.risk_level,
                "expected_properties": list(scenario.expected_properties),
            }
        )
    return enriched


def _estimate_totals(reports: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    estimated_turns = sum(float(report.get("cost_estimate", {}).get("estimated_turns", 0)) for report in reports)
    estimated_seconds = sum(float(report.get("latency_estimate", {}).get("estimated_seconds", 0)) for report in reports)
    return (
        {"estimated_turns": round(estimated_turns, 2)},
        {"estimated_seconds": round(estimated_seconds, 2)},
    )


async def _previous_pass_rate(session: AsyncSession, suite_name: str) -> float | None:
    from app.models.simulation_run import SimulationRun

    simulation_runs = SimulationRun.__table__
    result = await session.execute(
        select(simulation_runs.c.payload)
        .where(
            simulation_runs.c.scenario_key == f"goalbench:{suite_name}",
            simulation_runs.c.deleted_at.is_(None),
        )
        .order_by(desc(simulation_runs.c.completed_at), desc(simulation_runs.c.created_at))
        .limit(1)
    )
    payload = result.scalar_one_or_none()
    if not isinstance(payload, dict):
        return None
    pass_rate = payload.get("pass_rate")
    try:
        return float(pass_rate)
    except (TypeError, ValueError):
        return None


def _build_gate_decision(
    *,
    reports: list[dict[str, Any]],
    pass_rate: float,
    previous_pass_rate: float | None,
) -> dict[str, Any]:
    failed = [report for report in reports if not report.get("passed")]
    high_risk_failures = [report for report in failed if report.get("risk_level") == HIGH_RISK_LEVEL]
    medium_risk_failures = [report for report in failed if report.get("risk_level") == MEDIUM_RISK_LEVEL]
    low_risk_failures = [
        report for report in failed
        if report.get("risk_level") not in {HIGH_RISK_LEVEL, MEDIUM_RISK_LEVEL}
    ]
    trend_delta = None if previous_pass_rate is None else round(previous_pass_rate - pass_rate, 4)
    trend_blocked = trend_delta is not None and trend_delta > TREND_BLOCK_THRESHOLD

    blockers: list[str] = []
    warnings: list[str] = []
    if high_risk_failures:
        blockers.append(f"{len(high_risk_failures)} high-risk scenario(s) failed")
    if trend_blocked:
        blockers.append(f"pass rate degraded by {trend_delta:.1%} from previous run")
    if medium_risk_failures:
        warnings.append(f"{len(medium_risk_failures)} medium-risk scenario(s) failed")
    if low_risk_failures:
        warnings.append(f"{len(low_risk_failures)} low-risk scenario(s) failed")

    status = "blocked" if blockers else ("warning" if warnings else "passed")
    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "previous_pass_rate": previous_pass_rate,
        "trend_delta": trend_delta,
        "high_risk_failures": [report["scenario_name"] for report in high_risk_failures],
        "medium_risk_failures": [report["scenario_name"] for report in medium_risk_failures],
        "low_risk_failures": [report["scenario_name"] for report in low_risk_failures],
    }


async def _ensure_benchmark_user(session: AsyncSession) -> uuid.UUID:
    from app.models.user import User

    users = User.__table__
    result = await session.execute(select(users.c.id).where(users.c.id == SYSTEM_BENCHMARK_USER_ID).limit(1))
    existing_user_id = result.scalar_one_or_none()
    if existing_user_id is not None:
        return SYSTEM_BENCHMARK_USER_ID

    now = _utcnow()
    await session.execute(
        users.insert().values(
            id=SYSTEM_BENCHMARK_USER_ID,
            username="system_simulation_benchmark",
            email="simulation-benchmark@sparkle.local",
            hashed_password="system-managed",
            password_login_enabled=False,
            email_verified=True,
            avatar_status="APPROVED",
            flame_level=1,
            flame_brightness=0.5,
            depth_preference=0.5,
            curiosity_preference=0.5,
            is_active=False,
            is_superuser=False,
            status="OFFLINE",
            registration_source="system",
            photon_balance=0,
            searchable_by="nobody",
            created_at=now,
            updated_at=now,
        )
    )
    return SYSTEM_BENCHMARK_USER_ID


async def _persist_report(session: AsyncSession, report: BenchmarkReport) -> str:
    from app.models.simulation_run import SimulationRun

    user_id = await _ensure_benchmark_user(session)
    simulation_runs = SimulationRun.__table__
    record_id = uuid.uuid4()
    now = _utcnow()
    await session.execute(
        simulation_runs.insert().values(
            id=record_id,
            session_id=f"goalbench:{report.suite_name}:{report.run_id}",
            user_id=user_id,
            scenario_key=f"goalbench:{report.suite_name}",
            topic=f"SparkleGoalBench {report.suite_name}",
            state=report.status,
            payload=report.to_dict(),
            insight_summary=(
                f"{report.passed}/{report.total} scenarios passed; gate={report.status}; "
                f"blockers={len(report.gate.get('blockers', []))}"
            ),
            last_active_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    await session.commit()
    return str(record_id)


def _render_markdown(report: BenchmarkReport, reports_dir: Path) -> str:
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_part = datetime.now(UTC).strftime("%Y-%m-%d")
    safe_commit = "".join(ch for ch in report.commit if ch.isalnum() or ch in {"-", "_"}) or "unknown"
    path = reports_dir / f"{date_part}_{safe_commit}.md"
    failed = [item for item in report.reports if not item.get("passed")]
    lines = [
        f"# SparkleGoalBench Benchmark Report · {report.suite_name}",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Commit: `{report.commit}`",
        f"- Generated at: `{report.generated_at}`",
        f"- Gate status: **{report.status.upper()}**",
        f"- Pass rate: **{report.pass_rate:.1%}** ({report.passed}/{report.total})",
        f"- Estimated cost: {json.dumps(report.cost_estimate, ensure_ascii=False)}",
        f"- Estimated latency: {json.dumps(report.latency_estimate, ensure_ascii=False)}",
        "",
        "## Gate Decision",
        "",
        f"- Blockers: {', '.join(report.gate.get('blockers') or ['none'])}",
        f"- Warnings: {', '.join(report.gate.get('warnings') or ['none'])}",
        f"- Previous pass rate: {report.gate.get('previous_pass_rate')}",
        f"- Trend delta: {report.gate.get('trend_delta')}",
        "",
        "## Suite Breakdown",
        "",
        "| Suite | Passed | Total | Pass Rate | Recommendation |",
        "|---|---:|---:|---:|---|",
    ]
    for suite_name, suite_result in report.suite_breakdown.items():
        lines.append(
            f"| {suite_name} | {suite_result.get('passed', 0)} | {suite_result.get('total', 0)} | "
            f"{float(suite_result.get('pass_rate', 0)):.1%} | {suite_result.get('recommendation', 'unknown')} |"
        )

    lines.extend(["", "## Regressions", ""])
    if failed:
        lines.extend(["| Scenario | Suite | Risk | Violations |", "|---|---|---|---|"])
        for item in failed:
            violations = "; ".join(str(v) for v in item.get("violations", [])) or "unknown"
            lines.append(
                f"| {item.get('scenario_name')} | {item.get('suite')} | {item.get('risk_level')} | {violations} |"
            )
    else:
        lines.append("No scenario regressions detected.")

    lines.extend(["", "## Raw Summary", "", "```json", json.dumps(report.to_dict(), indent=2, ensure_ascii=False), "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _record_metrics(report: BenchmarkReport) -> None:
    if SIMULATION_BENCHMARK_RUNS is not None:
        SIMULATION_BENCHMARK_RUNS.labels(report.suite_name, report.status).inc()
    if SIMULATION_BENCHMARK_PASS_RATE is not None:
        SIMULATION_BENCHMARK_PASS_RATE.labels(report.suite_name).set(report.pass_rate)
    if SIMULATION_BENCHMARK_LATENCY_SECONDS is not None:
        SIMULATION_BENCHMARK_LATENCY_SECONDS.labels(report.suite_name).observe(
            report.latency_estimate.get("estimated_seconds", 0)
        )


async def run_benchmark_suite(
    suite_name: str = "full",
    *,
    session: AsyncSession | None = None,
    write_report: bool = True,
    reports_dir: Path | str | None = None,
    commit: str | None = None,
) -> BenchmarkReport:
    selected_suites = _build_suite_selection(suite_name)
    canonical_suite_name = "full" if len(selected_suites) > 1 else next(iter(selected_suites))
    result = _run_selected_suites(selected_suites)
    enriched_reports = _enrich_reports(result, selected_suites)
    cost_estimate, latency_estimate = _estimate_totals(enriched_reports)
    previous_pass_rate = await _previous_pass_rate(session, canonical_suite_name) if session is not None else None
    pass_rate = float(result.get("pass_rate", 0))
    gate = _build_gate_decision(
        reports=enriched_reports,
        pass_rate=pass_rate,
        previous_pass_rate=previous_pass_rate,
    )

    report = BenchmarkReport(
        run_id=uuid.uuid4().hex[:12],
        suite_name=canonical_suite_name,
        status=gate["status"],
        total=int(result.get("total", 0)),
        passed=int(result.get("passed", 0)),
        failed=int(result.get("failed", 0)),
        pass_rate=pass_rate,
        gate=gate,
        suite_breakdown=dict(result.get("suite_breakdown", {})),
        reports=enriched_reports,
        cost_estimate=cost_estimate,
        latency_estimate=latency_estimate,
        generated_at=_iso_now(),
        commit=commit or _current_commit(),
    )

    markdown_path = None
    if write_report:
        markdown_path = _render_markdown(report, Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR)
        report = BenchmarkReport(**{**report.to_dict(), "markdown_path": markdown_path})

    simulation_run_id = None
    if session is not None:
        simulation_run_id = await _persist_report(session, report)
        report = BenchmarkReport(**{**report.to_dict(), "simulation_run_id": simulation_run_id})

    _record_metrics(report)
    return report
