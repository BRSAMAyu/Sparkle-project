from app.orchestration.plan_quality_contract import (
    PLAN_MODE_FULL,
    PLAN_MODE_NEXT_STEP_ONLY,
    PLAN_MODE_PROVISIONAL,
    SECTION_GOAL_FRAME,
    SECTION_NEXT_ACTION,
    build_contract_payload,
    build_plan_quality_contract,
)


def test_plan_quality_contract_classifies_modes_from_readiness() -> None:
    contract = build_plan_quality_contract()

    assert contract.classify_mode(readiness_action="proceed") == PLAN_MODE_FULL
    assert contract.classify_mode(readiness_action="provisional") == PLAN_MODE_PROVISIONAL
    assert contract.classify_mode(readiness_action="ask") == PLAN_MODE_NEXT_STEP_ONLY


def test_plan_quality_contract_reports_missing_sections() -> None:
    contract = build_plan_quality_contract()
    coverage = contract.evaluate_coverage(
        mode=PLAN_MODE_FULL,
        payload={
            SECTION_GOAL_FRAME: {"goal": "Pass exam"},
            SECTION_NEXT_ACTION: {"step": "Review chapter 1"},
        },
    )

    assert SECTION_GOAL_FRAME in coverage.present_sections
    assert SECTION_NEXT_ACTION in coverage.present_sections
    assert "assumptions" in coverage.missing_sections


def test_build_contract_payload_uses_brief_and_strategy() -> None:
    payload = build_contract_payload(
        mode=PLAN_MODE_PROVISIONAL,
        situation_brief={
            "vision": {"primary_goal": "Pass thermo exam"},
            "decision_context": {
                "planning_readiness": "medium",
                "planning_readiness_action": "provisional",
                "planning_blocking_unknowns": ["real_capacity"],
                "strategic_clarification_questions": ["How many focused minutes can you really do per day?"],
            },
            "insight_state": {},
        },
        planning_strategy={
            "plan_horizon": "14_days",
            "plan_depth": "standard",
            "pacing_profile": "steady",
            "fallback_policy": "downgrade_to_provisional",
            "required_plan_sections": ["goal_frame", "assumptions"],
        },
    )

    assert payload["goal_frame"]["goal"] == "Pass thermo exam"
    assert payload["readiness_fit"]["mode"] == PLAN_MODE_PROVISIONAL
    assert payload["fallback_uncertainty"]["blocking_unknowns"] == ["real_capacity"]
