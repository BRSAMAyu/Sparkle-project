from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.orchestration.capability_requirement_compiler import CapabilityRequirementCompiler
from app.orchestration.capability_selection_policy import CapabilitySelectionPolicy
from app.services.capability_registry_service import CapabilityRegistryService


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _bounded(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 4)


@dataclass(frozen=True)
class CapabilitySelectionScenarioResult:
    scenario_id: str
    mode: str
    retrieval_score: float
    specialist_score: float
    cost_score: float
    coherence_score: float
    notes: list[str]
    selection_summary: dict[str, Any]
    blocked_capabilities: list[str]

    @property
    def overall_score(self) -> float:
        return _bounded(mean([self.retrieval_score, self.specialist_score, self.cost_score, self.coherence_score]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "mode": self.mode,
            "retrieval_score": self.retrieval_score,
            "specialist_score": self.specialist_score,
            "cost_score": self.cost_score,
            "coherence_score": self.coherence_score,
            "overall_score": self.overall_score,
            "notes": list(self.notes),
            "selection_summary": dict(self.selection_summary),
            "blocked_capabilities": list(self.blocked_capabilities),
        }


class CapabilitySelectionEvaluator:
    """Fixture-driven Phase D evaluator based on the D0 baseline scenarios."""

    _STRICT_RUNTIME_BLOCKS = {
        "phase_d_materials_mandatory_grounding": ["path:user_material_grounding"],
        "phase_d_specialist_escalation_required": ["path:specialist_expert_path"],
        "phase_d_cost_sensitive_fast_enough": [
            "model:xiaomi_chat",
            "model:dashscope_fast",
            "model:glm_4_7_flash_no_thinking",
        ],
    }

    def __init__(
        self,
        *,
        fixture_path: Path | None = None,
    ) -> None:
        self.fixture_path = fixture_path or Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase_d_body_awareness_baseline_scenarios.json"

    def load_scenarios(self) -> list[dict[str, Any]]:
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict)]

    def evaluate(self, *, mode: str = "regression_guided") -> dict[str, Any]:
        normalized_mode = _strip(mode) or "regression_guided"
        if normalized_mode not in {"regression_guided", "strict_runtime"}:
            raise ValueError(f"Unsupported evaluation mode: {mode}")

        registry = CapabilityRegistryService().build_registry()
        policy = CapabilitySelectionPolicy()
        compiler = CapabilityRequirementCompiler()

        scenario_results: list[CapabilitySelectionScenarioResult] = []
        grounding_wins = 0
        specialist_true_positives = 0
        specialist_false_positives = 0
        cost_disciplined = 0

        for scenario in self.load_scenarios():
            scenario_id = _strip(scenario.get("scenario_id"))
            expected_needs = _as_dict(scenario.get("expected_capability_needs"))
            current_context = self._build_current_context(scenario=scenario, mode=normalized_mode)
            requirements = compiler.compile(
                user_context_payload=current_context,
                plan_context={},
                decision_context={
                    "experience_mode": _strip(current_context.get("experience_mode")),
                    "grounding_priority": (
                        ["user_materials"]
                        if _strip(current_context.get("retrieval_emphasis")) == "user_materials"
                        else []
                    ),
                },
                insight_state={
                    "readiness_level": _strip(current_context.get("planning_readiness")),
                },
                planning_strategy={
                    "plan_depth": _strip(current_context.get("planning_depth")),
                },
                route_intent=_strip(scenario.get("route_intent")),
            )
            if normalized_mode == "regression_guided":
                requirements = self._apply_guided_expectations(
                    requirements=requirements,
                    expected_needs=expected_needs,
                    current_context=current_context,
                )

            body_map = policy.build_body_map(
                registry=registry,
                route_intent=_strip(scenario.get("route_intent")),
                capability_requirements=requirements,
            )
            blocked_capabilities = self._blocked_capabilities_for_scenario(
                scenario_id=scenario_id,
                mode=normalized_mode,
            )
            if blocked_capabilities:
                body_map = policy.apply_availability_overrides(
                    body_map=body_map,
                    blocked_capability_ids=blocked_capabilities,
                )

            selection = policy.select(
                body_map=body_map,
                capability_requirements=requirements,
                route_intent=_strip(scenario.get("route_intent")),
                current_context=current_context,
                mode_strategy={"strategy_mode": _strip(current_context.get("session_mode"))},
            )
            summary = selection.get("summary") if isinstance(selection.get("summary"), dict) else {}
            notes: list[str] = []

            retrieval_score = self._score_retrieval(
                summary=summary,
                expected_needs=expected_needs,
                selection=selection,
                notes=notes,
            )
            if retrieval_score >= 0.8:
                grounding_wins += 1

            specialist_score, expected_specialist, actual_specialist = self._score_specialist(
                summary=summary,
                expected_needs=expected_needs,
                selection=selection,
                notes=notes,
            )
            if expected_specialist and actual_specialist:
                specialist_true_positives += 1
            if not expected_specialist and actual_specialist:
                specialist_false_positives += 1

            cost_score = self._score_cost(
                summary=summary,
                expected_needs=expected_needs,
                selection=selection,
                notes=notes,
            )
            if cost_score >= 1.0:
                cost_disciplined += 1

            rationale = selection.get("selection_rationale") if isinstance(selection.get("selection_rationale"), list) else []
            fallback_plan = selection.get("fallback_plan") if isinstance(selection.get("fallback_plan"), list) else []
            coherence_score = 1.0 if rationale and selection.get("audit_notes") else 0.6
            if normalized_mode == "strict_runtime" and blocked_capabilities and not fallback_plan:
                coherence_score = min(coherence_score, 0.4)
                notes.append("missing explicit fallback plan under blocked-organ simulation")
            if not rationale:
                notes.append("missing selection rationale")

            scenario_results.append(
                CapabilitySelectionScenarioResult(
                    scenario_id=scenario_id,
                    mode=normalized_mode,
                    retrieval_score=_bounded(retrieval_score),
                    specialist_score=_bounded(specialist_score),
                    cost_score=_bounded(cost_score),
                    coherence_score=_bounded(coherence_score),
                    notes=notes,
                    selection_summary=summary,
                    blocked_capabilities=blocked_capabilities,
                )
            )

        overall = _bounded(mean([result.overall_score for result in scenario_results])) if scenario_results else 0.0
        return {
            "fixture_path": str(self.fixture_path),
            "mode": normalized_mode,
            "scenario_count": len(scenario_results),
            "selection_correctness": overall,
            "grounding_win_rate": _bounded(grounding_wins / len(scenario_results)) if scenario_results else 0.0,
            "specialist_escalation_precision": _bounded(
                specialist_true_positives / max(1, specialist_true_positives + specialist_false_positives)
            ),
            "unnecessary_escalation_rate": _bounded(specialist_false_positives / max(1, len(scenario_results))),
            "cost_discipline": _bounded(cost_disciplined / len(scenario_results)) if scenario_results else 0.0,
            "user_facing_coherence": _bounded(mean([result.coherence_score for result in scenario_results]))
            if scenario_results
            else 0.0,
            "scenario_error_cases": [result.scenario_id for result in scenario_results if result.overall_score < 0.6],
            "status": "pass" if overall >= 0.75 else "needs_iteration",
            "scenario_results": [result.to_dict() for result in scenario_results],
        }

    def _build_current_context(self, *, scenario: dict[str, Any], mode: str) -> dict[str, Any]:
        current_context = _as_dict(scenario.get("current_context"))
        expected_needs = _as_dict(scenario.get("expected_capability_needs"))
        current_context = {
            **current_context,
            "current_query": _strip(current_context.get("current_query")) or _strip(scenario.get("user_request")),
        }
        if bool(current_context.get("materials_attached")) and not current_context.get("attached_materials"):
            current_context = {
                **current_context,
                "attached_materials": [{"source": "phase_d_fixture"}],
            }
        if mode == "regression_guided" and expected_needs.get("preferred_specialists"):
            current_context = {
                **current_context,
                "preferred_specialists": list(expected_needs.get("preferred_specialists") or []),
            }
        return current_context

    def _apply_guided_expectations(
        self,
        *,
        requirements: dict[str, Any],
        expected_needs: dict[str, Any],
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        requirements = dict(requirements)
        if expected_needs.get("grounding_required") == "mandatory":
            requirements["grounding_required"] = "mandatory"
        if expected_needs.get("specialist_needed") is True:
            requirements["specialization_required"] = True
        if expected_needs.get("cost_posture") == "low":
            requirements["cost_band"] = "low"
        elif expected_needs.get("cost_posture") == "medium":
            requirements["cost_band"] = "medium"
        if current_context.get("preferred_specialists"):
            requirements["specialization_required"] = True
        return requirements

    def _blocked_capabilities_for_scenario(self, *, scenario_id: str, mode: str) -> list[str]:
        if mode != "strict_runtime":
            return []
        return list(self._STRICT_RUNTIME_BLOCKS.get(scenario_id, []))

    def _score_retrieval(
        self,
        *,
        summary: dict[str, Any],
        expected_needs: dict[str, Any],
        selection: dict[str, Any],
        notes: list[str],
    ) -> float:
        expected_grounding = _strip(expected_needs.get("grounding_required")).lower()
        retrieval_mode = _strip(summary.get("retrieval_mode"))
        fallback_plan = selection.get("fallback_plan") if isinstance(selection.get("fallback_plan"), list) else []

        if expected_grounding == "mandatory":
            if retrieval_mode == "user_materials_first":
                return 1.0
            if retrieval_mode == "user_materials_tool_only":
                return 0.85
            if retrieval_mode == "light_query_knowledge" and fallback_plan:
                notes.append("grounding degraded to knowledge fallback")
                return 0.45
            notes.append("mandatory grounding not satisfied")
            return 0.1
        if retrieval_mode == "light_query_knowledge":
            return 0.8
        if retrieval_mode == "no_retrieval":
            notes.append("retrieval path stayed minimal")
            return 0.4
        return 0.6

    def _score_specialist(
        self,
        *,
        summary: dict[str, Any],
        expected_needs: dict[str, Any],
        selection: dict[str, Any],
        notes: list[str],
    ) -> tuple[float, bool, bool]:
        expected_specialist = bool(expected_needs.get("specialist_needed"))
        specialist_strategy = _strip(summary.get("specialist_strategy"))
        actual_specialist = specialist_strategy in {"specialist_required", "fallback_specialist"}
        fallback_plan = selection.get("fallback_plan") if isinstance(selection.get("fallback_plan"), list) else []

        if expected_specialist and actual_specialist:
            return 1.0, expected_specialist, actual_specialist
        if expected_specialist and specialist_strategy == "simple_path" and fallback_plan:
            notes.append("specialist requirement degraded to simple path")
            return 0.4, expected_specialist, actual_specialist
        if expected_specialist and not actual_specialist:
            notes.append("missed specialist escalation")
            return 0.0, expected_specialist, actual_specialist
        if not expected_specialist and actual_specialist:
            notes.append("unnecessary specialist escalation")
            return 0.0, expected_specialist, actual_specialist
        return 1.0, expected_specialist, actual_specialist

    def _score_cost(
        self,
        *,
        summary: dict[str, Any],
        expected_needs: dict[str, Any],
        selection: dict[str, Any],
        notes: list[str],
    ) -> float:
        expected_cost = _strip(expected_needs.get("cost_posture")).lower()
        preferred_tier = _strip(summary.get("preferred_model_tier")).lower()
        fallback_plan = selection.get("fallback_plan") if isinstance(selection.get("fallback_plan"), list) else []

        if expected_cost == "low":
            if preferred_tier in {"fast", "standard"}:
                return 1.0
            if fallback_plan:
                notes.append("cost band fallback crossed into a more expensive tier")
                return 0.5
            return 0.0
        if expected_cost == "medium":
            if preferred_tier in {"standard", "plus"}:
                return 1.0
            if preferred_tier in {"fast", "pro"}:
                return 0.7
            return 0.0
        return 0.8 if preferred_tier else 0.0
