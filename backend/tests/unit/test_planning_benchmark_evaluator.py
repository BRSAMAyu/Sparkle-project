from app.services.planning_benchmark_evaluator import PlanningBenchmarkEvaluator
from app.services.planning_benchmark_service import PlanningBenchmarkRun, PlanningBenchmarkScenario


def test_evaluator_rewards_grounded_phase_b_style_output() -> None:
    evaluator = PlanningBenchmarkEvaluator()
    scenario = PlanningBenchmarkScenario(
        scenario_id="materials_case",
        title="Materials case",
        user_goal="Build a grounded recovery plan",
        deadline="2026-04-21",
        materials=["chapter3_notes.pdf", "error_book_export.csv"],
        baseline_state="Weak spots are known but pacing needs to stay realistic.",
        constraints=["Must reuse uploaded materials", "Non-expert friendly pacing"],
        recent_failures=["Used generic advice instead of personal materials"],
        phase_a_readiness_action="proceed",
        phase_a_readiness_level="high",
        planning_blocking_unknowns=["Need to prioritize weak nodes"],
        expected_plan_mode="full",
    )
    run = PlanningBenchmarkRun(
        scenario_id=scenario.scenario_id,
        variant="sparkle_phase_b",
        model_key="dashscope_chat",
        prompt="",
        output_text=(
            "Goal and deadline: build a grounded recovery plan by 2026-04-21.\n"
            "Assumptions: I am assuming you can sustain one 60-minute session daily.\n"
            "Grounding basis: use chapter3_notes.pdf and error_book_export.csv to pick weak nodes.\n"
            "Sequence:\n"
            "1. Today review the error clusters from error_book_export.csv.\n"
            "2. Day 1 rebuild chapter 3 from chapter3_notes.pdf.\n"
            "3. Day 2 solve one checkpoint set.\n"
            "If you fall behind, cut scope to the weakest two nodes first."
        ),
    )

    score = evaluator.evaluate_run(scenario=scenario, run=run)

    assert score.overall_score >= 0.74
    assert score.dimensions["grounding_quality"].score >= 0.8
    assert score.dimensions["next_action_usefulness"].score >= 0.6


def test_evaluator_penalizes_fake_full_plan_when_clarification_is_needed() -> None:
    evaluator = PlanningBenchmarkEvaluator()
    scenario = PlanningBenchmarkScenario(
        scenario_id="clarify_case",
        title="Clarify first",
        user_goal="Do better at school soon",
        deadline="",
        materials=[],
        baseline_state="No clear subject, no deadline, no baseline.",
        constraints=["Do not fake a full plan", "Ask only the highest-value question first"],
        recent_failures=["Accepted generic advice but never followed through"],
        phase_a_readiness_action="ask",
        phase_a_readiness_level="low",
        planning_blocking_unknowns=["Subject is unknown", "Deadline is unknown"],
        expected_plan_mode="next_step_only",
    )
    run = PlanningBenchmarkRun(
        scenario_id=scenario.scenario_id,
        variant="raw_baseline",
        model_key="dashscope_chat",
        prompt="",
        output_text=(
            "Week 1: study every subject for two hours each day.\n"
            "Week 2: continue revising all topics.\n"
            "Week 3: take practice tests and push harder."
        ),
    )

    score = evaluator.evaluate_run(scenario=scenario, run=run)

    assert score.inferred_mode == "full"
    assert score.overall_score < 0.6
    assert score.dimensions["trustworthiness"].score < 0.5
