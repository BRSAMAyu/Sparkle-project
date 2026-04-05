from app.services.capability_registry_service import CapabilityRegistryService


def test_capability_registry_service_builds_structured_body_map():
    payload = CapabilityRegistryService().build_registry()

    assert payload["schema_version"] == "phase_d.v1"
    assert payload["summary"]["model_count"] > 0
    assert payload["summary"]["agent_count"] > 0
    assert payload["summary"]["tool_count"] > 0
    assert payload["summary"]["canonical_capability_count"] > 0
    assert any(item["id"] == "chat_orchestrator" for item in payload["subsystems"])
    assert any(item["id"] == "system" for item in payload["configuration_layers"])
    assert any(item["key"] for item in payload["models"])
    assert any(item["id"] == "orchestrator" for item in payload["agents"])
    assert any(item["capability_kind"] == "model" for item in payload["canonical_capabilities"])
    assert any(item["capability_kind"] == "agent" for item in payload["canonical_capabilities"])
    assert any(item["capability_kind"] == "tool" for item in payload["canonical_capabilities"])
    assert any(item["capability_id"] == "path:specialist_expert_path" for item in payload["canonical_capabilities"])


def test_capability_registry_service_canonical_entries_declare_rights_and_preconditions():
    payload = CapabilityRegistryService().build_registry()

    capability = next(item for item in payload["canonical_capabilities"] if item["capability_id"] == "knob:model_tier_selection")
    assert capability["rights_model"] == "bounded_registry_only"
    assert capability["reversible"] is False
    assert capability["required_preconditions"]
    assert capability["when_not_to_use"]


def test_capability_registry_service_recommends_bounded_runtime_body_use():
    payload = CapabilityRegistryService().recommend_runtime_capabilities(
        route_intent="knowledge",
        experience_mode="explain",
        grounding_priority=["user_materials"],
        active_plan="Thermo sprint",
    )

    assert payload["primary_subsystem"]["id"] == "galaxy"
    assert "user_materials" in payload["evidence_sources"]
    assert payload["bounded_knob_decisions"][0]["allowed"] is True
    assert payload["rights_note"]
