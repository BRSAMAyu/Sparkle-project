"""Multi-scenario parallel runner.

Runs multiple ScenarioSpec instances concurrently with resource isolation.
Each scenario gets its own OrchestratorConfig and RunDB tracking.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .spec import ScenarioSpec, BUILTIN_SCENARIOS


@dataclass
class ScenarioResult:
    """Result of running a single scenario."""
    scenario_id: str
    run_id: str
    acceptance: dict[str, bool]
    passed: bool
    metrics_summary: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "acceptance": self.acceptance,
            "passed": self.passed,
            "metrics_summary": self.metrics_summary,
            "error": self.error,
        }


class ScenarioRunner:
    """Runs ScenarioSpec instances and collects results.

    This is a lightweight coordinator — it doesn't re-implement the
    orchestrator's event loop. Instead, it builds OrchestratorConfig
    from ScenarioSpec and delegates to SGWOrchestrator.
    """

    def __init__(
        self,
        *,
        persona_library_path: Path,
        adversarial_playbook_path: Path,
        output_dir: Path,
        max_concurrent: int = 2,
    ):
        self.persona_library_path = persona_library_path
        self.adversarial_playbook_path = adversarial_playbook_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self.results: list[ScenarioResult] = []

    def build_config(self, spec: ScenarioSpec) -> dict[str, Any]:
        """Build OrchestratorConfig kwargs from ScenarioSpec."""
        report_path = self.output_dir / f"report_{spec.scenario_id}.md"
        checkpoint_path = self.output_dir / f"checkpoint_{spec.scenario_id}.json"

        return {
            "persona_library": self.persona_library_path,
            "adversarial_playbook": self.adversarial_playbook_path,
            "report_path": report_path,
            "checkpoint_path": checkpoint_path,
            "wall_clock_hours": spec.acceptance.min_wall_clock_hours,
            "min_sessions": spec.acceptance.min_sessions,
            "min_turns": spec.acceptance.min_turns,
            "turn_target": spec.arc_config.max_turns_per_session,
            "adversarial_sessions": spec.adversarial_config.session_count if spec.adversarial_config.enabled else 0,
            "llm_provider": spec.llm_provider,
            "api_model": spec.api_model,
            "api_temperature": spec.api_temperature,
            "audit_sample_rate": spec.audit_sample_rate,
            "authenticity_sample_rate": spec.authenticity_sample_rate,
        }

    async def run_scenario(self, spec: ScenarioSpec) -> ScenarioResult:
        """Run a single scenario and return results."""
        from sgw.orchestrator import SGWOrchestrator, OrchestratorConfig

        config_kwargs = self.build_config(spec)
        config = OrchestratorConfig(**config_kwargs)

        try:
            orchestrator = SGWOrchestrator(config)
            exit_code = await orchestrator.run()

            # Collect results
            metrics = orchestrator.metrics
            acceptance = spec.check_acceptance({
                "sessions_completed": metrics.sessions_completed,
                "turns_completed": metrics.turns_completed,
                "soft_violation_rate": metrics.soft_violation_rate(),
                "hard_violations": len(metrics.hard_violations),
                "authenticity_mean": metrics.authenticity_mean(),
            })

            run_summary = {}
            if orchestrator.run_id and orchestrator.run_db:
                run_summary = orchestrator.run_db.run_summary(orchestrator.run_id) or {}

            return ScenarioResult(
                scenario_id=spec.scenario_id,
                run_id=orchestrator.run_id or "unknown",
                acceptance=acceptance,
                passed=all(acceptance.values()),
                metrics_summary=run_summary,
            )
        except Exception as exc:  # noqa: BLE001
            return ScenarioResult(
                scenario_id=spec.scenario_id,
                run_id="error",
                acceptance={},
                passed=False,
                metrics_summary={},
                error=str(exc),
            )

    async def run_multiple(self, specs: list[ScenarioSpec]) -> list[ScenarioResult]:
        """Run multiple scenarios with concurrency limit."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def bounded_run(spec: ScenarioSpec) -> ScenarioResult:
            async with semaphore:
                return await self.run_scenario(spec)

        tasks = [asyncio.create_task(bounded_run(spec)) for spec in specs]
        self.results = await asyncio.gather(*tasks)
        return list(self.results)

    def print_summary(self) -> str:
        """Print a summary of all scenario results."""
        lines = ["# Multi-Scenario Run Summary", ""]
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)

        lines.append(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
        lines.append("")

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"## {result.scenario_id}: {status}")
            if result.error:
                lines.append(f"  Error: {result.error}")
            else:
                for key, ok in result.acceptance.items():
                    lines.append(f"  - {key}: {'PASS' if ok else 'FAIL'}")
            lines.append("")

        summary = "\n".join(lines)
        summary_path = self.output_dir / "multi_scenario_summary.md"
        summary_path.write_text(summary, encoding="utf-8")
        return summary
