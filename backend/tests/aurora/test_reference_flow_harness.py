from __future__ import annotations

import pytest

import app.aurora as aurora_pkg
from pydantic import ValidationError

from .reference_flow_harness import AuroraReferenceFlowHarness


def test_reference_flow_harness_builds_gate0_fixtures() -> None:
    harness = AuroraReferenceFlowHarness()

    day3_case = harness.build_day3_study_resistance_case()
    crisis_case = harness.build_crisis_recovery_case()
    partner_case = harness.build_partner_concern_case()

    assert day3_case.snapshot.snapshot_hash == "ss_day3_reference"
    assert crisis_case.trigger_point == "pre-tool-selection"
    assert partner_case.trigger_point == "pre-node-routing"
    assert day3_case.policy_version.id == "aurora_policy@v1.0"
    assert len(day3_case.expected_output_classes) == 6
    assert day3_case.expected_object_sequence == (
        "SignalSnapshot",
        "InsightClaim",
        "TransitionDecisionRecord",
        "ProbeOutcome",
    )
    assert crisis_case.expected_object_sequence[-2:] == ("WindowState", "FocusContract")
    assert partner_case.expected_object_sequence[1:3] == ("InsightClaim", "ProbeOutcome")
    assert crisis_case.expected_output_classes[-2:] == ("ux_intent", "aurora_presence")


def test_reference_flow_harness_produces_placeholder_decision_and_claim() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_day3_study_resistance_case()

    decision = harness.build_decision_stub(case)
    claim = harness.build_claim_stub(case)

    assert decision.input_snapshot_ref == case.snapshot.snapshot_hash
    assert decision.rollback_anchor["prev_focus_contract_version"] == case.focus_contract.version
    assert claim.status.value == "open"


def test_aurora_root_package_exports_schema_and_helpers() -> None:
    assert aurora_pkg.AuroraPolicyVersion.__name__ == "AuroraPolicyVersion"
    assert aurora_pkg.SignalSnapshot.__name__ == "SignalSnapshot"
    assert "AuroraPolicyVersion" in aurora_pkg.__all__
    assert "enum_values" in aurora_pkg.__all__


def test_gate0_schema_models_are_frozen() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_day3_study_resistance_case()

    with pytest.raises(ValidationError):
        case.focus_contract.active_node = "mutated_node"
