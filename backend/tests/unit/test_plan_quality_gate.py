from app.orchestration.plan_quality_gate import PlanQualityGate
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec


def _plan(*tool_names: str) -> ExecutablePlan:
    return ExecutablePlan(
        schema_version="5.0",
        plan_id="plan-1",
        snapshot_id="snap-1",
        context_version="v1",
        source="langgraph",
        confidence=0.9,
        rationale="Generated plan",
        tool_calls=[
            ToolCallSpec(
                id=f"call-{idx}",
                name=name,
                params={"estimated_minutes": 20},
                timeout_ms=10000,
            )
            for idx, name in enumerate(tool_names, start=1)
        ],
    )


def test_plan_quality_gate_asks_more_when_phase_a_requires_clarification() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan"),
        user_message="Help me do better at school",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "ask",
                    "planning_readiness": "low",
                    "strategic_clarification_questions": ["Which subject matters most right now?"],
                },
                "planning_strategy": {
                    "plan_mode": "next_step_only",
                    "required_plan_sections": ["goal_frame", "withhold_reason", "next_action", "unlock_question"],
                    "fallback_policy": "ask_more",
                    "adaptation_trigger": "if_the_missing_fact_is_provided",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nFocus on one school bottleneck first.\n"
                    "Why a Full Plan Is Withheld\nThere is not enough information yet.\n"
                    "Next Action Within 24 Hours\nOpen your grade portal and pick one course.\n"
                    "Unlock Question\nWhich subject matters most right now?"
                )
            },
        },
    )

    assert report.decision == "ask_more"


def test_plan_quality_gate_downgrades_when_grounding_is_required_but_missing() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan"),
        user_message="Make me a plan from my uploaded notes",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "proceed",
                    "planning_readiness": "high",
                },
                "planning_strategy": {
                    "plan_mode": "full",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "workload_model",
                        "sequence",
                        "grounding_basis",
                        "next_action",
                        "adaptation_trigger",
                        "failure_guard",
                    ],
                    "grounding_mode": "mandatory",
                    "fallback_policy": "use_materials_or_downgrade",
                    "adaptation_trigger": "if_material_gap_persists",
                },
            },
            "user_material_grounding": {"status": "no_hits", "results": []},
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nBuild a plan from my uploaded notes.\n"
                    "Key Assumptions\nAssume I can study daily.\n"
                    "Readiness Fit\nThis is a full plan.\n"
                    "Workload Model\nStudy 60 minutes daily.\n"
                    "Sequence and Rationale\n1. Review topic order.\n"
                    "Grounding Basis\nUse the notes I uploaded.\n"
                    "Next Action Within 24 Hours\nOpen the notes and review chapter 1.\n"
                    "Adaptation Trigger\nIf I fall behind, cut scope.\n"
                    "Failure Guard\nReduce to one chapter."
                )
            },
        },
    )

    assert report.decision == "downgrade_to_provisional"
    assert report.grounding_score < 0.5


def test_plan_quality_gate_approves_well_formed_grounded_full_plan() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan"),
        user_message="Build my 14-day thermo plan",
        user_context={
            "situation_brief": {
                "vision": {"primary_goal": "Pass thermo exam"},
                "decision_context": {
                    "planning_readiness_action": "proceed",
                    "planning_readiness": "high",
                },
                "planning_strategy": {
                    "plan_mode": "full",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "workload_model",
                        "sequence",
                        "grounding_basis",
                        "next_action",
                        "adaptation_trigger",
                        "failure_guard",
                    ],
                    "grounding_mode": "mandatory",
                    "fallback_policy": "revise",
                    "adaptation_trigger": "if_daily_checkpoint_slips",
                    "pacing_profile": "steady",
                    "assumption_basis": ["use_attached_materials", "respect_current_capacity"],
                },
            },
            "user_material_grounding": {"status": "grounded", "results": [{"file_name": "notes.pdf"}]},
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nPass thermo exam by the deadline.\n"
                    "Key Assumptions\nAssume I can study 90 minutes daily.\n"
                    "Readiness Fit\nThis is a full plan.\n"
                    "Workload Model\nUse one 90-minute session per day.\n"
                    "Sequence and Rationale\nDay 1 review reversible vs irreversible processes.\n"
                    "Grounding Basis\nUse notes.pdf to focus on the weakest topics.\n"
                    "Next Action Within 24 Hours\nOpen notes.pdf and review the first weak topic.\n"
                    "Adaptation Trigger\nIf the daily checkpoint slips, cut the next day to one core task.\n"
                    "Failure Guard\nReduce the plan to the highest-yield problems first."
                )
            },
        },
    )

    assert report.decision == "approve"
    assert report.overall_score >= 0.8


def test_plan_quality_gate_rejects_full_plan_without_rendered_artifact() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan"),
        user_message="Build my thermo plan",
        user_context={
            "situation_brief": {
                "vision": {"primary_goal": "Pass thermo exam"},
                "decision_context": {
                    "planning_readiness_action": "proceed",
                    "planning_readiness": "high",
                },
                "planning_strategy": {
                    "plan_mode": "full",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "workload_model",
                        "sequence",
                        "grounding_basis",
                        "next_action",
                        "adaptation_trigger",
                        "failure_guard",
                    ],
                    "grounding_mode": "mandatory",
                    "fallback_policy": "revise",
                    "adaptation_trigger": "if_daily_checkpoint_slips",
                },
            },
            "user_material_grounding": {"status": "grounded", "results": [{"file_name": "notes.pdf"}]},
        },
    )

    assert report.decision != "approve"
    assert any(issue.code == "missing_plan_artifact" for issue in report.issues)


def test_plan_quality_gate_rejects_when_rendered_full_plan_omits_grounding_section() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan"),
        user_message="Build a grounded thermo plan",
        user_context={
            "situation_brief": {
                "vision": {"primary_goal": "Pass thermo exam"},
                "decision_context": {
                    "planning_readiness_action": "proceed",
                    "planning_readiness": "high",
                },
                "planning_strategy": {
                    "plan_mode": "full",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "workload_model",
                        "sequence",
                        "grounding_basis",
                        "next_action",
                        "adaptation_trigger",
                        "failure_guard",
                    ],
                    "grounding_mode": "mandatory",
                    "fallback_policy": "revise",
                    "adaptation_trigger": "if_daily_checkpoint_slips",
                },
            },
            "user_material_grounding": {"status": "grounded", "results": [{"file_name": "notes.pdf"}]},
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nPass thermo exam.\n"
                    "Key Assumptions\nAssume I can study 90 minutes daily.\n"
                    "Readiness Fit\nThis is a full plan.\n"
                    "Workload Model\nUse one 90-minute session per day.\n"
                    "Sequence and Rationale\nDay 1 review reversible vs irreversible processes.\n"
                    "Next Action Within 24 Hours\nOpen notes.pdf and review the first weak topic.\n"
                    "Adaptation Trigger\nIf the daily checkpoint slips, cut the next day to one core task.\n"
                    "Failure Guard\nReduce the plan to the highest-yield problems first."
                )
            },
        },
    )

    assert report.decision != "approve"
    assert any(issue.code == "missing_section:grounding_basis" for issue in report.issues)


def test_plan_quality_gate_flags_missing_validated_learning_alignment() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan"),
        user_message="Build a safer restart plan",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "proceed",
                    "planning_readiness": "high",
                },
                "planning_strategy": {
                    "plan_mode": "full",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "workload_model",
                        "sequence",
                        "grounding_basis",
                        "next_action",
                        "adaptation_trigger",
                        "failure_guard",
                    ],
                    "grounding_mode": "general_knowledge",
                    "scaffold_level": "medium",
                    "first_step_hint": "Start by outlining the full workload.",
                },
                "outcome_learning": {
                    "planning_bias_constraints": {
                        "lighter_first_step": True,
                        "grounding_mode": "mandatory",
                        "scaffold_level": "high",
                    },
                    "plan_generation_hints_from_outcomes": ["Default to a lighter first step."],
                },
            },
            "user_material_grounding": {"status": "grounded", "results": [{"file_name": "notes.pdf"}]},
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nRecover the plan safely.\n"
                    "Key Assumptions\nAssume I can study 2 hours immediately.\n"
                    "Readiness Fit\nThis is a full plan.\n"
                    "Workload Model\nUse one 120-minute session.\n"
                    "Sequence and Rationale\nStart with the full backlog.\n"
                    "Grounding Basis\nUse notes.pdf.\n"
                    "Next Action Within 24 Hours\nWork through the full backlog outline.\n"
                    "Adaptation Trigger\nIf it slips, try again tomorrow.\n"
                    "Failure Guard\nKeep pushing."
                )
            },
        },
    )

    assert report.outcome_learning_score < 0.5
    assert any(issue.code == "missed_validated_grounding_requirement" for issue in report.issues)


def test_plan_quality_gate_accepts_provisional_plan_with_rendered_sections() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan"),
        user_message="Help me recover momentum",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "provisional",
                    "planning_readiness": "medium",
                },
                "planning_strategy": {
                    "plan_mode": "provisional",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "scope_and_horizon",
                        "next_action",
                        "fallback_uncertainty",
                    ],
                    "grounding_mode": "preferred",
                    "fallback_policy": "downgrade_to_provisional",
                    "adaptation_trigger": "if_today_fails",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nRecover enough momentum to study again.\n"
                    "Key Assumptions\nAssume energy is low today.\n"
                    "Readiness Fit\nThis is a provisional plan.\n"
                    "Narrowed Scope and Horizon\nOnly cover the next 48 hours.\n"
                    "Next Action Within 24 Hours\nSet a 15-minute study block for tonight.\n"
                    "Fallback Path and Uncertainty\nIf that block fails, reduce to five minutes tomorrow."
                )
            },
        },
    )

    assert report.decision == "downgrade_to_provisional"
    assert report.artifact_coverage["missing_sections"] == []


def test_plan_quality_gate_scores_next_step_only_from_rendered_action_and_question() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan(),
        user_message="I want to do better at school soon",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "ask",
                    "planning_readiness": "low",
                },
                "planning_strategy": {
                    "plan_mode": "next_step_only",
                    "required_plan_sections": ["goal_frame", "withhold_reason", "next_action", "unlock_question"],
                    "fallback_policy": "ask_more",
                    "adaptation_trigger": "if_new_details_arrive",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nIdentify the biggest school bottleneck.\n"
                    "Why a Full Plan Is Withheld\nThere is not enough information yet.\n"
                    "Next Action Within 24 Hours\nOpen your grade portal and identify one risky course.\n"
                    "Unlock Question\nWhat exact assignment or exam in that course worries you most?"
                )
            },
        },
    )

    assert report.decision == "ask_more"
    assert report.next_action_score >= 0.9
    assert report.adaptation_score >= 0.8


def test_plan_quality_gate_flags_over_scoped_clarify_response() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan"),
        user_message="Help me do better at school",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "ask",
                    "planning_readiness": "low",
                    "experience_mode": "clarify",
                },
                "planning_strategy": {
                    "plan_mode": "next_step_only",
                    "required_plan_sections": ["goal_frame", "withhold_reason", "next_action", "unlock_question"],
                    "fallback_policy": "ask_more",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nImprove school performance.\n"
                    "Why a Full Plan Is Withheld\nDetails are still missing.\n"
                    "Next Action Within 24 Hours\nReview every class and build a two-week plan.\n"
                    "Unlock Question\nWhich subject matters most right now?\n"
                    "Extra Question\nHow many hours do you have this week?"
                )
            },
        },
    )

    assert report.decision == "ask_more"
    assert any(issue.code == "clarify_over_scoped" for issue in report.issues)


def test_plan_quality_gate_flags_missing_assumptions_for_provisional_plan() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan"),
        user_message="Help me recover momentum",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "provisional",
                    "planning_readiness": "medium",
                },
                "planning_strategy": {
                    "plan_mode": "provisional",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "scope_and_horizon",
                        "next_action",
                        "fallback_uncertainty",
                    ],
                    "grounding_mode": "preferred",
                    "fallback_policy": "downgrade_to_provisional",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nRecover enough momentum to study again.\n"
                    "Readiness Fit\nThis is a provisional plan.\n"
                    "Narrowed Scope and Horizon\nOnly cover the next 48 hours.\n"
                    "Next Action Within 24 Hours\nSet a 15-minute study block for tonight.\n"
                    "Fallback Path and Uncertainty\nIf that block fails, reduce to five minutes tomorrow."
                )
            },
        },
    )

    assert any(issue.code == "missing_explicit_assumptions" for issue in report.issues)


def test_plan_quality_gate_flags_high_pressure_stabilize_plan() -> None:
    gate = PlanQualityGate()
    report = gate.evaluate(
        plan=_plan("create_plan", "generate_tasks_for_plan", "generate_tasks_for_plan", "generate_tasks_for_plan"),
        user_message="I am overwhelmed and need a restart plan",
        user_context={
            "situation_brief": {
                "decision_context": {
                    "planning_readiness_action": "provisional",
                    "planning_readiness": "medium",
                    "experience_mode": "stabilize",
                },
                "planning_strategy": {
                    "plan_mode": "provisional",
                    "required_plan_sections": [
                        "goal_frame",
                        "assumptions",
                        "readiness_fit",
                        "scope_and_horizon",
                        "next_action",
                        "fallback_uncertainty",
                    ],
                    "grounding_mode": "preferred",
                    "pacing_profile": "light",
                    "fallback_policy": "shrink_scope_then_retry",
                },
            },
            "rendered_plan_artifact": {
                "text": (
                    "Goal Frame\nRestart studying immediately.\n"
                    "Key Assumptions\nAssume energy is low today.\n"
                    "Readiness Fit\nThis is a provisional plan.\n"
                    "Narrowed Scope and Horizon\nOnly cover the next 24 hours.\n"
                    "Next Action Within 24 Hours\nPush harder tonight and complete four dense study blocks.\n"
                    "Fallback Path and Uncertainty\nIf this is too much, cut to one block tomorrow."
                )
            },
        },
    )

    assert any(issue.code == "stabilize_pressure_too_high" for issue in report.issues)
