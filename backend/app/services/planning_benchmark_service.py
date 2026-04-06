from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.agent_profiles import AgentRole
from app.core.llm_router import llm_router
from app.orchestration.ai_strategy_renderer import build_semantic_control
from app.orchestration.plan_quality_contract import build_plan_quality_contract
from app.orchestration.planning_strategy_compiler import PlanningStrategyCompiler
from app.services.llm_service import get_llm_service_for_specific_model

RAW_BASELINE_MODEL_KEYS = ("dashscope_chat", "deepseek_chat")
PLANNING_BENCHMARK_DIMENSIONS = (
    "understanding_fit",
    "behavior_compliance",
    "response_shape_compliance",
    "constraint_realism",
    "plan_sequence_quality",
    "grounding_quality",
    "next_action_usefulness",
    "adaptation_fallback_quality",
    "non_expert_usability",
    "trustworthiness",
    "trust_tone_compliance",
)
BENCHMARK_SECTION_LABELS = {
    "goal_frame": "goal frame",
    "assumptions": "key assumptions",
    "readiness_fit": "readiness fit",
    "workload_model": "workload model",
    "sequence": "sequence and rationale",
    "grounding_basis": "grounding basis",
    "next_action": "next action within 24 hours",
    "adaptation_trigger": "adaptation trigger",
    "failure_guard": "failure guard",
    "scope_and_horizon": "narrowed scope and horizon",
    "fallback_uncertainty": "fallback path and uncertainty",
    "withhold_reason": "why a full plan is withheld",
    "unlock_question": "one unlock question or blocker",
}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _benchmark_prompt_requirements(contract: Any, *, mode: str) -> str:
    sections = contract.get_required_sections(mode)
    return ", ".join(BENCHMARK_SECTION_LABELS.get(section, section) for section in sections)


@dataclass(frozen=True)
class PlanningBenchmarkScenario:
    scenario_id: str
    title: str
    user_goal: str
    deadline: str
    materials: list[str]
    baseline_state: str
    constraints: list[str]
    recent_failures: list[str]
    phase_a_readiness_action: str
    phase_a_readiness_level: str
    planning_blocking_unknowns: list[str]
    expected_plan_mode: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "user_goal": self.user_goal,
            "deadline": self.deadline,
            "materials": list(self.materials),
            "baseline_state": self.baseline_state,
            "constraints": list(self.constraints),
            "recent_failures": list(self.recent_failures),
            "phase_a_readiness_action": self.phase_a_readiness_action,
            "phase_a_readiness_level": self.phase_a_readiness_level,
            "planning_blocking_unknowns": list(self.planning_blocking_unknowns),
            "expected_plan_mode": self.expected_plan_mode,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PlanningBenchmarkRun:
    scenario_id: str
    variant: str
    model_key: str
    prompt: str
    output_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "variant": self.variant,
            "model_key": self.model_key,
            "prompt": self.prompt,
            "output_text": self.output_text,
        }


@dataclass(frozen=True)
class PlanningBenchmarkScorecard:
    scenario_id: str
    variant: str
    model_key: str
    dimensions: dict[str, dict[str, Any]]
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "variant": self.variant,
            "model_key": self.model_key,
            "dimensions": dict(self.dimensions),
            "human_review_required": self.human_review_required,
        }


class PlanningBenchmarkHarness:
    """Fixture-driven planning benchmark harness for Sparkle Phase B."""

    def __init__(self) -> None:
        self.contract = build_plan_quality_contract()
        self.strategy_compiler = PlanningStrategyCompiler(contract=self.contract)

    @staticmethod
    def load_scenarios(path: str | Path) -> list[PlanningBenchmarkScenario]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        scenarios: list[PlanningBenchmarkScenario] = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            scenarios.append(
                PlanningBenchmarkScenario(
                    scenario_id=_strip(item.get("scenario_id")),
                    title=_strip(item.get("title")),
                    user_goal=_strip(item.get("user_goal")),
                    deadline=_strip(item.get("deadline")),
                    materials=[_strip(v) for v in item.get("materials", []) if _strip(v)],
                    baseline_state=_strip(item.get("baseline_state")),
                    constraints=[_strip(v) for v in item.get("constraints", []) if _strip(v)],
                    recent_failures=[_strip(v) for v in item.get("recent_failures", []) if _strip(v)],
                    phase_a_readiness_action=_strip(item.get("phase_a_readiness_action")),
                    phase_a_readiness_level=_strip(item.get("phase_a_readiness_level")),
                    planning_blocking_unknowns=[
                        _strip(v) for v in item.get("planning_blocking_unknowns", []) if _strip(v)
                    ],
                    expected_plan_mode=_strip(item.get("expected_plan_mode")),
                    notes=_strip(item.get("notes")),
                )
            )
        return scenarios

    def build_raw_model_prompt(self, scenario: PlanningBenchmarkScenario) -> str:
        return (
            "You are helping an ordinary user build a study or action plan.\n"
            "Use only the information below. Do not invent hidden data. If uncertainty remains, say so plainly.\n\n"
            f"Goal: {scenario.user_goal}\n"
            f"Deadline: {scenario.deadline}\n"
            f"Current baseline: {scenario.baseline_state}\n"
            f"Constraints: {'; '.join(scenario.constraints) or 'None provided'}\n"
            f"Recent failures: {'; '.join(scenario.recent_failures) or 'None provided'}\n"
            f"Materials available: {'; '.join(scenario.materials) or 'None'}\n\n"
            "Create a plan that is realistic, sequenced, and non-expert friendly."
        )

    def build_sparkle_current_prompt(self, scenario: PlanningBenchmarkScenario) -> str:
        return (
            "You are Sparkle's current planning stack.\n"
            "Turn the dossier into a helpful plan for a non-expert user.\n\n"
            f"Goal: {scenario.user_goal}\n"
            f"Deadline: {scenario.deadline}\n"
            f"Baseline state: {scenario.baseline_state}\n"
            f"Constraints: {'; '.join(scenario.constraints) or 'None'}\n"
            f"Recent failures: {'; '.join(scenario.recent_failures) or 'None'}\n"
            f"Materials: {'; '.join(scenario.materials) or 'None'}"
        )

    def build_sparkle_phase_b_prompt(self, scenario: PlanningBenchmarkScenario) -> str:
        strategy = self.strategy_compiler.compile(
            situation_brief={
                "vision": {
                    "primary_goal": scenario.user_goal,
                    "target_date": scenario.deadline,
                },
                "current_state": {
                    "snapshot": scenario.baseline_state,
                },
                "decision_context": {
                    "planning_readiness_action": scenario.phase_a_readiness_action,
                    "planning_readiness": scenario.phase_a_readiness_level,
                    "planning_blocking_unknowns": list(scenario.planning_blocking_unknowns),
                },
                "insight_state": {},
            },
            user_context_payload={
                "file_ids": ["fixture"] if scenario.materials else [],
                "user_material_grounding": {
                    "status": "grounded" if scenario.materials else "",
                    "results": [{"file_name": name} for name in scenario.materials[:3]],
                },
            },
            plan_context={},
            planning_constraints={},
        ).to_dict()
        section_requirements = _benchmark_prompt_requirements(self.contract, mode=strategy["plan_mode"])
        mode = strategy["plan_mode"]
        mode_instruction = {
            "full": (
                "Return a true full plan. Tighten scope if needed, but do not downgrade away from a full plan unless a hard blocking unknown makes planning impossible."
            ),
            "provisional": (
                "Return a clearly provisional plan with a narrowed horizon, explicit assumptions, and a smaller first move."
            ),
            "next_step_only": (
                "Do not return a multi-day plan. Return exactly one next action and exactly one unlock question or blocker."
            ),
        }.get(mode, "Honor the compiled planning mode exactly.")
        return (
            "You are Sparkle Phase B, a growth-first planning engine.\n"
            "Make planning quality explicit and do not pretend certainty when the dossier is weak.\n"
            "Respond in English.\n\n"
            f"Dossier goal: {scenario.user_goal}\n"
            f"Dossier deadline: {scenario.deadline}\n"
            f"Dossier baseline: {scenario.baseline_state}\n"
            f"Dossier constraints: {'; '.join(scenario.constraints) or 'None'}\n"
            f"Dossier recent failures: {'; '.join(scenario.recent_failures) or 'None'}\n"
            f"Dossier materials: {'; '.join(scenario.materials) or 'None'}\n\n"
            f"Compiled planning strategy: mode={strategy['plan_mode']}, depth={strategy['plan_depth']}, pacing={strategy['pacing_profile']}, grounding={strategy['grounding_mode']}, fallback={strategy['fallback_policy']}.\n"
            "The compiled planning strategy is authoritative for this benchmark.\n"
            f"The response must explicitly cover: {section_requirements}.\n"
            f"{mode_instruction}\n"
            "Use attached materials by name whenever grounding is mandatory."
        )

    def build_semantic_doctrine_prompt(self, scenario: PlanningBenchmarkScenario) -> str:
        strategy = self.strategy_compiler.compile(
            situation_brief={
                "vision": {
                    "primary_goal": scenario.user_goal,
                    "target_date": scenario.deadline,
                },
                "current_state": {
                    "snapshot": scenario.baseline_state,
                },
                "decision_context": {
                    "planning_readiness_action": scenario.phase_a_readiness_action,
                    "planning_readiness": scenario.phase_a_readiness_level,
                    "planning_blocking_unknowns": list(scenario.planning_blocking_unknowns),
                },
                "insight_state": {},
            },
            user_context_payload={
                "file_ids": ["fixture"] if scenario.materials else [],
                "user_material_grounding": {
                    "status": "grounded" if scenario.materials else "",
                    "results": [{"file_name": name} for name in scenario.materials[:3]],
                },
            },
            plan_context={},
            planning_constraints={},
        ).to_dict()
        semantic_control = build_semantic_control(
            decision_context={
                "planning_readiness_action": scenario.phase_a_readiness_action,
                "planning_readiness": scenario.phase_a_readiness_level,
                "planning_blocking_unknowns": list(scenario.planning_blocking_unknowns),
                "experience_mode": "clarify" if scenario.phase_a_readiness_action == "ask" else "",
            },
            planning_strategy=strategy,
            body_awareness_guidance={},
            user_strategy_state={},
            outcome_learning={},
            language="en",
        ).to_dict()
        summary = dict(semantic_control.get("rendered_doctrine_summary") or {})
        doctrine_lines = []
        for key in ("decision_doctrine", "planning_doctrine"):
            doctrine_lines.extend([_strip(item) for item in summary.get(key, []) if _strip(item)])
        return (
            "You are Sparkle's semantic-control planning stack.\n"
            "Treat the doctrine below as behavioral contract, not stylistic suggestion.\n"
            "Respond in English.\n\n"
            f"Dossier goal: {scenario.user_goal}\n"
            f"Dossier deadline: {scenario.deadline}\n"
            f"Dossier baseline: {scenario.baseline_state}\n"
            f"Dossier constraints: {'; '.join(scenario.constraints) or 'None'}\n"
            f"Dossier recent failures: {'; '.join(scenario.recent_failures) or 'None'}\n"
            f"Dossier materials: {'; '.join(scenario.materials) or 'None'}\n\n"
            "Semantic doctrine:\n"
            + "\n".join(f"- {item}" for item in doctrine_lines)
            + "\n\n"
            + "Use the doctrine behaviorally. If grounding is required, explicitly name the materials you used."
        )

    def build_blank_scorecard(self, run: PlanningBenchmarkRun) -> PlanningBenchmarkScorecard:
        excerpt = run.output_text.strip().splitlines()[:3]
        evidence = " ".join(line.strip() for line in excerpt if line.strip())[:240]
        dimensions = {
            dimension: {
                "score": None,
                "notes": "",
                "evidence_excerpt": evidence,
            }
            for dimension in PLANNING_BENCHMARK_DIMENSIONS
        }
        return PlanningBenchmarkScorecard(
            scenario_id=run.scenario_id,
            variant=run.variant,
            model_key=run.model_key,
            dimensions=dimensions,
            human_review_required=True,
        )

    def require_model_configured(self, model_key: str) -> None:
        config = llm_router._available_models.get(model_key)
        if config is None:
            raise RuntimeError(f"Unknown planning benchmark model key: {model_key}")
        if not _strip(getattr(config, "model_name", "")) or not _strip(getattr(config, "api_key", "")):
            raise RuntimeError(f"Planning benchmark requires configured model credentials for {model_key}")

    async def run_prompt_variant(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
        variant: str,
        model_key: str,
    ) -> PlanningBenchmarkRun:
        self.require_model_configured(model_key)
        if variant == "sparkle_current":
            prompt = self.build_sparkle_current_prompt(scenario)
        elif variant == "sparkle_phase_b":
            prompt = self.build_sparkle_phase_b_prompt(scenario)
        elif variant == "semantic_doctrine":
            prompt = self.build_semantic_doctrine_prompt(scenario)
        elif variant == "raw_baseline":
            prompt = self.build_raw_model_prompt(scenario)
        else:
            raise ValueError(f"Unsupported planning benchmark variant: {variant}")

        llm = await get_llm_service_for_specific_model(model_key, agent_role=AgentRole.GENERATION)
        response = await llm.chat(
            [
                {"role": "system", "content": "Return a useful planning answer for the user dossier."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return PlanningBenchmarkRun(
            scenario_id=scenario.scenario_id,
            variant=variant,
            model_key=model_key,
            prompt=prompt,
            output_text=_strip(response),
        )

    async def run_mixed_provider_baselines(
        self,
        *,
        scenario: PlanningBenchmarkScenario,
    ) -> list[PlanningBenchmarkRun]:
        runs: list[PlanningBenchmarkRun] = []
        for model_key in RAW_BASELINE_MODEL_KEYS:
            runs.append(
                await self.run_prompt_variant(
                    scenario=scenario,
                    variant="raw_baseline",
                    model_key=model_key,
                )
            )
        return runs
