from app.services.capability_registry_service import CapabilityRegistryService


def test_capability_registry_phase_e_knobs_declare_bounded_rights_metadata() -> None:
    payload = CapabilityRegistryService().build_registry()

    knob = next(item for item in payload["system_layer_knobs"] if item["id"] == "tool_surface_selection")

    assert knob["rights_model"] == "bounded_registry_only"
    assert knob["approval_level"] == "bounded_runtime"
    assert knob["constitutional_review_required"] is True
    assert "session" in knob["allowed_target_layers"]


def test_capability_registry_phase_e_blocks_system_change_without_enough_evidence() -> None:
    result = CapabilityRegistryService().evaluate_system_change_request(
        knob_id="agent_mix_selection",
        reason="Use specialists only when needed.",
        reversible=True,
        evidence_strength=0.3,
        target_layer="session",
    )

    assert result["allowed"] is False
    assert "Evidence threshold" in result["reason"]
