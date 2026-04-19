from __future__ import annotations

from app.aurora.decision_fns import (
    RoutingMode,
    build_fallback_decision,
    check_materiality,
    decide_backbone_route,
    dispatch_trigger,
)
from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.observability import AURORA_FALLBACK_TOTAL
from app.aurora.policy_loader import load_policy_version
from app.aurora.schemas import SignalSnapshot

from .reference_flow_harness import AuroraReferenceFlowHarness


def _fallback_counter_total() -> float:
    collected = AURORA_FALLBACK_TOTAL.collect()
    if not collected:
        return 0.0
    return sum(
        sample.value
        for sample in collected[0].samples
        if sample.name == "sparkle_aurora_fallback_total"
    )


def test_policy_loader_loads_v1_fixture() -> None:
    policy = load_policy_version("v1.0")

    assert policy.id == "aurora_policy@v1.0"
    assert policy.version == "v1.0"
    assert len(policy.interaction_model_registry) == 4
    assert policy.materiality_threshold == 0.5


def test_materiality_check_skips_low_impact_message() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_day3_study_resistance_case()

    check = check_materiality(case.snapshot, case.policy_version)

    assert check.should_route is False
    assert check.score < case.policy_version.materiality_threshold


def test_materiality_check_passes_commitment_conflict() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    conflict_snapshot = SignalSnapshot.model_validate(
        {
            **case.snapshot.model_dump(mode="json"),
            "snapshot_hash": "ss_conflict_reference",
            "core_signals": {"commitment_conflict": "需要立刻改期"},
        }
    )

    check = check_materiality(conflict_snapshot, case.policy_version)

    assert check.should_route is True
    assert check.basis.value == "commitment_conflict"


def test_backbone_route_stays_without_strong_signal() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    decision = decide_backbone_route(
        snapshot=case.snapshot,
        policy=case.policy_version,
        current_node=case.focus_contract.active_node,
    )

    assert decision.should_stay is True
    assert decision.route_kind == "stay"
    assert decision.proposed_node is None
    assert decision.routing_mode == RoutingMode.DIRECT


def test_backbone_route_marks_planning_request_as_workflow_mode() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    planning_snapshot = SignalSnapshot.model_validate(
        {
            **case.snapshot.model_dump(mode="json"),
            "snapshot_hash": "ss_stage4_routing_workflow",
            "core_signals": {"user_message": "帮我把这周复习计划拆成每天三步。"},
        }
    )

    decision = decide_backbone_route(
        snapshot=planning_snapshot,
        policy=case.policy_version,
        current_node=case.focus_contract.active_node,
    )

    assert decision.routing_mode == RoutingMode.WORKFLOW
    assert decision.route_kind == "stay"


def test_backbone_route_marks_task_assistant_request_as_task_assistant_mode() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    assistant_snapshot = SignalSnapshot.model_validate(
        {
            **case.snapshot.model_dump(mode="json"),
            "snapshot_hash": "ss_stage4_routing_task_assistant",
            "core_signals": {"user_message": "不用重做计划，我就想把当前这张任务卡顺下来。"},
            "optional_signals": {"task_card_id": "task-card-01"},
        }
    )

    decision = decide_backbone_route(
        snapshot=assistant_snapshot,
        policy=case.policy_version,
        current_node=case.focus_contract.active_node,
    )

    assert decision.routing_mode == RoutingMode.TASK_ASSISTANT
    assert decision.route_kind == "stay"


def test_trigger_dispatch_maps_three_trigger_types() -> None:
    reactive = dispatch_trigger("reactive")
    scheduled = dispatch_trigger("scheduled")
    on_demand = dispatch_trigger("on_demand")

    assert reactive.trigger_point == "pre-node-routing"
    assert scheduled.trigger_point == "pre-tool-selection"
    assert on_demand.trigger_point == "pre-response-formatting"
    assert reactive.priority < scheduled.priority < on_demand.priority


def test_fallback_decision_is_schema_valid_and_inert() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()

    record = build_fallback_decision(
        user_id=case.snapshot.user_id,
        snapshot_ref=None,
        policy_version=None,
        reason="snapshot_corrupted",
        trigger_point="pre-node-routing",
    )

    assert record.decision_type == "no_op"
    assert record.rollback_anchor["policy_version_at_decision"] == "aurora_policy@v1.0"
    assert record.input_snapshot_ref == "aurora_fallback_snapshot"


def test_safe_route_distinguishes_normal_stay_from_fallback() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    engine = AuroraEngine()

    stay_context = AuroraDecisionContext(
        snapshot=case.snapshot,
        trigger_point="pre-node-routing",
        current_node=case.focus_contract.active_node,
        policy_version=case.policy_version,
    )
    fallback_context = AuroraDecisionContext(
        snapshot=None,
        trigger_point="pre-node-routing",
        current_node=case.focus_contract.active_node,
        policy_version=case.policy_version,
    )

    fallback_before = _fallback_counter_total()
    stay_record = engine.safe_route(stay_context)
    fallback_record = engine.safe_route(fallback_context)
    fallback_after = _fallback_counter_total()

    assert stay_record.decision_type == "stay"
    assert stay_record.proposed_transition is None
    assert stay_record.input_snapshot_ref == case.snapshot.snapshot_hash
    assert stay_record.policy_version == case.policy_version.id
    assert stay_record.inference_knobs and stay_record.inference_knobs.get("fallback") is not True
    assert fallback_record.decision_type == "no_op"
    assert fallback_record.policy_version == case.policy_version.id
    assert fallback_record.input_snapshot_ref == "aurora_fallback_snapshot"
    assert fallback_after == fallback_before + 1


def test_safe_route_stay_does_not_increment_fallback_counter() -> None:
    case = AuroraReferenceFlowHarness().build_day3_study_resistance_case()
    engine = AuroraEngine()

    context = AuroraDecisionContext(
        snapshot=case.snapshot,
        trigger_point="pre-node-routing",
        current_node=case.focus_contract.active_node,
        policy_version=case.policy_version,
    )

    fallback_before = _fallback_counter_total()
    record = engine.safe_route(context)
    fallback_after = _fallback_counter_total()

    assert record.decision_type == "stay"
    assert fallback_after == fallback_before
