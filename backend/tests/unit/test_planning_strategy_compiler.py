from app.orchestration.plan_quality_contract import PLAN_MODE_FULL, PLAN_MODE_NEXT_STEP_ONLY, PLAN_MODE_PROVISIONAL
from app.orchestration.planning_strategy_compiler import PlanningStrategyCompiler


def test_planning_strategy_compiler_is_deterministic_for_same_input() -> None:
    compiler = PlanningStrategyCompiler()
    payload = {
        "vision": {"primary_goal": "Pass exam", "target_date": "2026-04-19"},
        "current_state": {"snapshot": "Behind and starting late"},
        "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        "insight_state": {},
    }
    user_context = {"user_material_grounding": {"status": "grounded", "results": [{"file_name": "notes.pdf"}]}}

    first = compiler.compile(situation_brief=payload, user_context_payload=user_context).to_dict()
    second = compiler.compile(situation_brief=payload, user_context_payload=user_context).to_dict()

    comparable_first = {k: v for k, v in first.items() if k != "generated_at"}
    comparable_second = {k: v for k, v in second.items() if k != "generated_at"}
    assert comparable_first == comparable_second


def test_planning_strategy_compiler_differs_by_readiness() -> None:
    compiler = PlanningStrategyCompiler()
    common = {"vision": {"primary_goal": "Pass exam"}, "current_state": {"snapshot": "Need a plan"}}

    full = compiler.compile(
        situation_brief={**common, "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"}},
    )
    provisional = compiler.compile(
        situation_brief={**common, "decision_context": {"planning_readiness_action": "provisional", "planning_readiness": "medium"}},
    )
    ask = compiler.compile(
        situation_brief={**common, "decision_context": {"planning_readiness_action": "ask", "planning_readiness": "low"}},
    )

    assert full.plan_mode == PLAN_MODE_FULL
    assert provisional.plan_mode == PLAN_MODE_PROVISIONAL
    assert ask.plan_mode == PLAN_MODE_NEXT_STEP_ONLY
    assert full.required_plan_sections != ask.required_plan_sections


def test_planning_strategy_compiler_applies_validated_outcome_learning_hints() -> None:
    compiler = PlanningStrategyCompiler()

    strategy = compiler.compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a safer recovery plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
            "outcome_learning": {
                "planning_bias_constraints": {
                    "lighter_first_step": True,
                    "grounding_mode": "mandatory",
                    "scaffold_level": "high",
                },
                "plan_generation_hints_from_outcomes": ["Default to a lighter first step."],
                "known_failure_avoidance_rules": ["Avoid dense first steps when similar conditions recur."],
            },
        },
        user_context_payload={},
    )

    assert strategy.grounding_mode == "mandatory"
    assert strategy.scaffold_level == "high"
    assert strategy.pacing_profile == "light"
    assert "Default to a lighter first step." in strategy.outcome_learning_hints


def test_planning_strategy_compiler_uses_predicted_overload_risk() -> None:
    compiler = PlanningStrategyCompiler()

    strategy = compiler.compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a plan"},
            "decision_context": {
                "planning_readiness_action": "proceed",
                "planning_readiness": "high",
                "predicted_overload_risk": "high",
            },
        },
        user_context_payload={},
    )

    assert strategy.overload_signal is True
    assert strategy.plan_type == "recovery"
    assert strategy.plan_depth == "standard"
