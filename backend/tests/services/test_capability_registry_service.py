from app.services.capability_registry_service import CapabilityRegistryService


def test_capability_registry_service_builds_structured_body_map():
    payload = CapabilityRegistryService().build_registry()

    assert payload["summary"]["model_count"] > 0
    assert payload["summary"]["agent_count"] > 0
    assert payload["summary"]["tool_count"] > 0
    assert any(item["id"] == "chat_orchestrator" for item in payload["subsystems"])
    assert any(item["id"] == "system" for item in payload["configuration_layers"])
    assert any(item["key"] for item in payload["models"])
    assert any(item["id"] == "orchestrator" for item in payload["agents"])
