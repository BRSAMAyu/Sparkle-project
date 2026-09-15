from datetime import timedelta

from app.core.time_utils import utcnow
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
        situation_brief={
            **common,
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        },
    )
    provisional = compiler.compile(
        situation_brief={
            **common,
            "decision_context": {"planning_readiness_action": "provisional", "planning_readiness": "medium"},
        },
    )
    ask = compiler.compile(
        situation_brief={
            **common,
            "decision_context": {"planning_readiness_action": "ask", "planning_readiness": "low"},
        },
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


def test_planning_strategy_compiler_flags_impossible_deadline_capacity() -> None:
    compiler = PlanningStrategyCompiler()
    target_date = (utcnow().date() + timedelta(days=3)).isoformat()

    strategy = compiler.compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam", "target_date": target_date},
            "current_state": {"snapshot": "Need a plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        },
        plan_context={"daily_available_minutes": 45},
        planning_constraints={"route_intent": "create_plan"},
    )

    assert strategy.workload_fit == "impossible"
    assert "impossible_schedule_risk" in strategy.feasibility_flags
    assert strategy.fallback_policy == "shrink_scope_then_retry"
    assert strategy.checkpoint_cadence == "daily"
    assert strategy.first_review_after_days == 1


def test_planning_strategy_compiler_consumes_dual_core_cognitive_mode() -> None:
    strategy = PlanningStrategyCompiler().compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        },
        planning_constraints={"dual_core_mode": "cognitive_first"},
    )

    assert strategy.dual_core_mode == "cognitive_first"
    assert strategy.plan_depth == "light"
    assert strategy.scaffold_level == "high"
    assert strategy.pacing_profile == "light"
    assert strategy.planning_bias_constraints["max_first_step_minutes"] == 5
    assert strategy.first_step_hint == "start_with_one_micro-step_within_5_minutes"


def test_planning_strategy_compiler_consumes_dual_core_execution_mode() -> None:
    strategy = PlanningStrategyCompiler().compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        },
        planning_constraints={"dual_core_mode": "execution_first"},
    )

    assert strategy.dual_core_mode == "execution_first"
    assert strategy.pacing_profile == "push"
    assert strategy.planning_bias_constraints["direct_execution"] is True
    assert strategy.planning_bias_constraints["avoid_over_explaining"] is True


def test_planning_strategy_compiler_applies_cognitive_load_type_biases() -> None:
    strategy = PlanningStrategyCompiler().compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
        },
        planning_constraints={
            "dual_core_mode": "balanced",
            "dominant_cognitive_load_type": "extraneous",
        },
    )

    assert strategy.planning_bias_constraints["simplify_explanation"] is True
    assert strategy.planning_bias_constraints["reduce_card_count"] is True
    assert "cognitive_load_extraneous_simplify_system_output" in strategy.assumption_basis


def test_planning_strategy_compiler_applies_mi_tension_for_low_readiness_stage() -> None:
    strategy = PlanningStrategyCompiler().compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Avoiding the plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "medium"},
        },
        planning_constraints={
            "dual_core_mode": "cognitive_first",
            "stage_of_change": "contemplation",
            "active_probe_target": "task_aversion",
        },
    )

    assert strategy.mi_tension_level == "develop_discrepancy"
    assert strategy.planning_bias_constraints["avoid_validating_avoidance"] is True
    assert strategy.planning_bias_constraints["ask_discrepancy_question"] is True
    assert strategy.planning_bias_constraints["active_probe_target"] == "task_aversion"
