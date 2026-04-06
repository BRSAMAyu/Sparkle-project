from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _strip(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class UnderstandingBenchmarkScenario:
    scenario_id: str
    title: str
    benchmark_family: str
    comparison_focus: str
    expected_signal_ids: tuple[str, ...]
    expected_prediction_ids: tuple[str, ...]
    expected_unknown_ids: tuple[str, ...]
    expected_clarification_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "benchmark_family": self.benchmark_family,
            "comparison_focus": self.comparison_focus,
            "expected_signal_ids": list(self.expected_signal_ids),
            "expected_prediction_ids": list(self.expected_prediction_ids),
            "expected_unknown_ids": list(self.expected_unknown_ids),
            "expected_clarification_hint": self.expected_clarification_hint,
        }


@dataclass(frozen=True)
class UnderstandingBenchmarkRun:
    scenario_id: str
    variant: str
    artifact: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "variant": self.variant,
            "artifact": dict(self.artifact),
        }


class UnderstandingBenchmarkHarness:
    """Fixture-driven understanding benchmark harness for Stage 2 insight quality."""

    @staticmethod
    def load_scenarios(path: str | Path) -> list[UnderstandingBenchmarkScenario]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        scenarios: list[UnderstandingBenchmarkScenario] = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            scenarios.append(
                UnderstandingBenchmarkScenario(
                    scenario_id=_strip(item.get("scenario_id")),
                    title=_strip(item.get("title")),
                    benchmark_family=_strip(item.get("benchmark_family")),
                    comparison_focus=_strip(item.get("comparison_focus")),
                    expected_signal_ids=tuple(_strip(v) for v in item.get("expected_signal_ids", []) if _strip(v)),
                    expected_prediction_ids=tuple(_strip(v) for v in item.get("expected_prediction_ids", []) if _strip(v)),
                    expected_unknown_ids=tuple(_strip(v) for v in item.get("expected_unknown_ids", []) if _strip(v)),
                    expected_clarification_hint=_strip(item.get("expected_clarification_hint")),
                )
            )
        return scenarios

    def build_raw_model_comparison_prompt(self, scenario: UnderstandingBenchmarkScenario) -> str:
        return (
            "You are evaluating whether a generic frontier model understands a user as well as Sparkle's insight system.\n"
            "Do not assume hidden memory. Only use the visible dossier and say what you would ask or infer first.\n\n"
            f"Scenario: {scenario.title}\n"
            f"Family: {scenario.benchmark_family}\n"
            f"Comparison focus: {scenario.comparison_focus}\n"
            f"Expected key signals: {', '.join(scenario.expected_signal_ids) or 'none'}\n"
            f"Expected prediction surfaces: {', '.join(scenario.expected_prediction_ids) or 'none'}\n"
            f"Expected unknowns to surface: {', '.join(scenario.expected_unknown_ids) or 'none'}\n"
        )

    def build_human_review_payload(self, scenario: UnderstandingBenchmarkScenario) -> dict[str, Any]:
        return {
            "scenario_id": scenario.scenario_id,
            "date_run": "",
            "evaluator": "founder_or_mentor",
            "overall_verdict": "pending_review",
            "segments": [
                {
                    "segment_id": f"{scenario.scenario_id}:segment-1",
                    "turn_or_segment": scenario.title,
                    "sparkle_hypothesis": scenario.comparison_focus,
                    "real_problem": "",
                    "evidence_used": list(scenario.expected_signal_ids),
                    "visible_adaptation": "",
                    "timing_assessment": "",
                    "trust_signal": "",
                    "should_have_done_differently": "",
                    "issue_tags": [],
                }
            ],
        }
