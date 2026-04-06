from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.planning_benchmark_service import PlanningBenchmarkHarness, RAW_BASELINE_MODEL_KEYS


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "planning_benchmark_scenarios.json"


def test_planning_benchmark_harness_loads_phase_b_scenarios() -> None:
    harness = PlanningBenchmarkHarness()
    scenarios = harness.load_scenarios(_fixture_path())

    assert len(scenarios) == 8
    assert {item.expected_plan_mode for item in scenarios} == {"full", "provisional", "next_step_only"}
    assert all(item.phase_a_readiness_action for item in scenarios)


def test_planning_benchmark_harness_builds_mixed_provider_prompts() -> None:
    harness = PlanningBenchmarkHarness()
    scenario = harness.load_scenarios(_fixture_path())[0]

    raw_prompt = harness.build_raw_model_prompt(scenario)
    sparkle_prompt = harness.build_sparkle_phase_b_prompt(scenario)
    semantic_prompt = harness.build_semantic_doctrine_prompt(scenario)

    assert "Goal:" in raw_prompt
    assert "Compiled planning strategy" in sparkle_prompt
    assert "Semantic doctrine" in semantic_prompt
    assert "behavioral contract" in semantic_prompt
    assert "controlled regression evidence" in raw_prompt
    assert "controlled regression evidence" in sparkle_prompt
    assert "controlled regression evidence" in semantic_prompt


def test_planning_benchmark_harness_uses_phase_a_inputs_not_expected_mode_for_strategy() -> None:
    harness = PlanningBenchmarkHarness()
    scenario = harness.load_scenarios(_fixture_path())[0]
    scenario = scenario.__class__(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        user_goal=scenario.user_goal,
        deadline=scenario.deadline,
        materials=scenario.materials,
        baseline_state=scenario.baseline_state,
        constraints=scenario.constraints,
        recent_failures=scenario.recent_failures,
        phase_a_readiness_action="ask",
        phase_a_readiness_level="low",
        planning_blocking_unknowns=["Exact target is unclear"],
        expected_plan_mode="full",
        notes=scenario.notes,
    )

    sparkle_prompt = harness.build_sparkle_phase_b_prompt(scenario)

    assert "mode=next_step_only" in sparkle_prompt


@pytest.mark.asyncio
async def test_planning_benchmark_harness_fails_fast_when_model_missing() -> None:
    harness = PlanningBenchmarkHarness()
    scenario = harness.load_scenarios(_fixture_path())[0]

    with pytest.raises(RuntimeError):
        await harness.run_prompt_variant(
            scenario=scenario,
            variant="raw_baseline",
            model_key="does_not_exist",
        )


@pytest.mark.asyncio
async def test_planning_benchmark_harness_runs_mixed_baselines_with_mocked_llm() -> None:
    harness = PlanningBenchmarkHarness()
    scenario = harness.load_scenarios(_fixture_path())[0]

    with patch.object(harness, "require_model_configured") as require_configured:
        with patch("app.services.planning_benchmark_service.get_llm_service_for_specific_model") as get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value="A grounded plan")
            get_llm.return_value = mock_llm

            runs = []
            for model_key in RAW_BASELINE_MODEL_KEYS:
                runs.append(
                    await harness.run_prompt_variant(
                        scenario=scenario,
                        variant="raw_baseline",
                        model_key=model_key,
                    )
                )

    assert require_configured.call_count == 2
    assert [run.model_key for run in runs] == list(RAW_BASELINE_MODEL_KEYS)
    assert all(run.output_text == "A grounded plan" for run in runs)
