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
    assert score.dimensions["behavior_compliance"].score >= 0.7
    assert score.dimensions["response_shape_compliance"].score >= 0.6
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
    assert score.dimensions["behavior_compliance"].score < 0.6
    assert score.dimensions["trustworthiness"].score < 0.5


def test_semantic_doctrine_variant_beats_raw_baseline_on_thermodynamics_behavior_compliance() -> None:
    evaluator = PlanningBenchmarkEvaluator()
    scenario = PlanningBenchmarkScenario(
        scenario_id="thermo_recovery_case",
        title="Thermodynamics recovery",
        user_goal="Stabilize thermodynamics chapter two without overload",
        deadline="2026-04-21",
        materials=["chapter2_notes.pdf", "mistakes.csv"],
        baseline_state="The user is overloaded, confuses entropy direction, and needs lighter grounded recovery planning.",
        constraints=["Use the user's own materials", "Keep pressure low", "Name assumptions when the horizon is provisional"],
        recent_failures=["Generic full plans caused overload", "The assistant pushed too hard before grounding"],
        phase_a_readiness_action="provisional",
        phase_a_readiness_level="medium",
        planning_blocking_unknowns=["Exact daily capacity is unclear"],
        expected_plan_mode="provisional",
    )
    raw_run = PlanningBenchmarkRun(
        scenario_id=scenario.scenario_id,
        variant="raw_baseline",
        model_key="dashscope_chat",
        prompt="",
        output_text=(
            "Week 1: relearn all of thermodynamics chapter 2 in depth.\n"
            "Week 2: push harder with two timed sets every day.\n"
            "Ignore uncertainty and follow the schedule strictly."
        ),
    )
    semantic_run = PlanningBenchmarkRun(
        scenario_id=scenario.scenario_id,
        variant="semantic_doctrine",
        model_key="dashscope_chat",
        prompt="",
        output_text=(
            "Provisional plan for now:\n"
            "Goal and horizon: stabilize thermodynamics chapter 2 before 2026-04-21 without overload.\n"
            "Assumptions: I am assuming you can manage one lighter 35-minute block on most days.\n"
            "Grounding basis: use chapter2_notes.pdf and mistakes.csv to choose the weakest entropy-direction examples first.\n"
            "Scope and horizon: for the next three days, focus only on entropy direction and reversible vs irreversible process judgments.\n"
            "Next action within 24 hours: open mistakes.csv, pick the weakest two entropy-direction errors, and rebuild them with chapter2_notes.pdf.\n"
            "If this still feels heavy, cut the block to 15 minutes and keep only one example."
        ),
    )

    raw_score = evaluator.evaluate_run(scenario=scenario, run=raw_run)
    semantic_score = evaluator.evaluate_run(scenario=scenario, run=semantic_run)

    assert raw_score.dimensions["behavior_compliance"].score < semantic_score.dimensions["behavior_compliance"].score
    assert raw_score.dimensions["behavior_compliance"].score < 0.6
    assert semantic_score.dimensions["behavior_compliance"].score >= 0.7
