from app.orchestration.capability_selection_policy import CapabilitySelectionPolicy
from app.services.capability_registry_service import CapabilityRegistryService


def _build_body_map(*, route_intent: str, requirements: dict[str, object]) -> dict[str, object]:
    registry = CapabilityRegistryService().build_registry()
    return CapabilitySelectionPolicy().build_body_map(
        registry=registry,
        route_intent=route_intent,
        capability_requirements=requirements,
    )


def test_selector_prefers_live_user_material_grounding_path() -> None:
    requirements = {
        "grounding_required": "mandatory",
        "specialization_required": False,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="knowledge", requirements=requirements)

    selection = CapabilitySelectionPolicy().select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="knowledge",
        current_context={},
        mode_strategy={},
    )

    assert selection["summary"]["retrieval_mode"] == "user_materials_first"
    assert selection["tool_selection"]["selected_capability_id"] == "path:user_material_grounding"
    assert selection["selected_capabilities"][0]["capability_id"] == "path:user_material_grounding"


def test_selector_falls_back_to_retrieve_user_material_when_primary_path_is_blocked() -> None:
    policy = CapabilitySelectionPolicy()
    requirements = {
        "grounding_required": "mandatory",
        "specialization_required": False,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="knowledge", requirements=requirements)
    body_map = policy.apply_availability_overrides(
        body_map=body_map,
        blocked_capability_ids=["path:user_material_grounding"],
    )

    selection = policy.select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="knowledge",
        current_context={},
        mode_strategy={},
    )

    assert selection["summary"]["retrieval_mode"] == "user_materials_tool_only"
    assert selection["tool_selection"]["selected_capability_id"] == "tool:retrieve_user_material"
    assert selection["fallback_plan"][0]["preferred_capability_id"] == "path:user_material_grounding"
    assert selection["fallback_plan"][0]["fallback_capability_id"] == "tool:retrieve_user_material"


def test_selector_chooses_no_retrieval_when_mandatory_grounding_cannot_be_satisfied() -> None:
    policy = CapabilitySelectionPolicy()
    requirements = {
        "grounding_required": "mandatory",
        "specialization_required": False,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="knowledge", requirements=requirements)
    body_map = policy.apply_availability_overrides(
        body_map=body_map,
        blocked_capability_ids=["path:user_material_grounding", "tool:retrieve_user_material"],
    )

    selection = policy.select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="knowledge",
        current_context={},
        mode_strategy={},
    )

    assert selection["summary"]["retrieval_mode"] == "no_retrieval"
    assert selection["tool_selection"]["selected_capability_id"] == "path:no_retrieval"
    assert selection["degraded_selection_notes"]
    assert any(item["capability_id"] == "path:no_retrieval" for item in selection["selected_capabilities"])


def test_selector_falls_back_to_compatible_specialist_when_preferred_agent_is_blocked() -> None:
    policy = CapabilitySelectionPolicy()
    requirements = {
        "grounding_required": "helpful",
        "specialization_required": True,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="error_diagnosis", requirements=requirements)
    body_map = policy.apply_availability_overrides(
        body_map=body_map,
        blocked_capability_ids=["agent:math_agent"],
    )

    selection = policy.select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="error_diagnosis",
        current_context={"preferred_specialists": ["math_agent"]},
        mode_strategy={},
    )

    assert selection["summary"]["specialist_strategy"] == "fallback_specialist"
    assert selection["specialist_selection"]["selected_experts"]
    assert "math_agent" not in selection["specialist_selection"]["selected_experts"]
    assert selection["fallback_plan"][0]["decision_class"] == "specialist"


def test_selector_respects_live_model_availability_and_records_cost_fallback() -> None:
    policy = CapabilitySelectionPolicy()
    requirements = {
        "grounding_required": "optional",
        "specialization_required": False,
        "cost_band": "low",
    }
    body_map = _build_body_map(route_intent="chat", requirements=requirements)
    body_map = policy.apply_availability_overrides(
        body_map=body_map,
        blocked_capability_ids=[
            "model:xiaomi_chat",
            "model:dashscope_fast",
            "model:deepseek_fast",
            "model:glm_4_7_flash_no_thinking",
            "model:xiaomi_standard_thinking",
            "model:deepseek_chat",
            "model:dashscope_standard_thinking",
            "model:default",
        ],
    )

    selection = policy.select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="chat",
        current_context={},
        mode_strategy={},
    )

    assert selection["summary"]["selected_model_capability_id"].startswith("model:")
    assert selection["summary"]["preferred_model_tier"] in {"plus", "pro", "max"}
    assert selection["fallback_plan"][-1]["decision_class"] == "model_tier"
    assert selection["fallback_plan"][-1]["fallback_capability_id"] == selection["summary"]["selected_model_capability_id"]


def test_selector_records_in_band_model_fallback_when_fast_model_is_blocked() -> None:
    policy = CapabilitySelectionPolicy()
    requirements = {
        "grounding_required": "optional",
        "specialization_required": False,
        "cost_band": "low",
    }
    body_map = _build_body_map(route_intent="chat", requirements=requirements)
    body_map = policy.apply_availability_overrides(
        body_map=body_map,
        blocked_capability_ids=[
            "model:xiaomi_chat",
            "model:dashscope_fast",
            "model:deepseek_fast",
            "model:glm_4_7_flash_no_thinking",
        ],
    )

    selection = policy.select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="chat",
        current_context={},
        mode_strategy={},
    )

    assert selection["summary"]["preferred_model_tier"] == "standard"
    model_fallbacks = [item for item in selection["fallback_plan"] if item["decision_class"] == "model_tier"]
    assert model_fallbacks
    assert model_fallbacks[-1]["reason"] == "higher_priority_in_band_model_unavailable"
    assert model_fallbacks[-1]["fallback_capability_id"] == selection["summary"]["selected_model_capability_id"]
    assert model_fallbacks[-1]["requirement_satisfaction"] == "full"


def test_selector_does_not_activate_surfaces_for_core_planning_turns() -> None:
    requirements = {
        "grounding_required": "required_from_profile",
        "specialization_required": False,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="plan", requirements=requirements)

    selection = CapabilitySelectionPolicy().select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="plan",
        current_context={},
        mode_strategy={},
    )

    selected_ids = {item["capability_id"] for item in selection["selected_capabilities"]}
    assert "surface:community" not in selected_ids
    assert "surface:achievements" not in selected_ids
    assert "surface:visual_bgm" not in selected_ids


def test_selector_reports_only_canonical_capability_ids() -> None:
    requirements = {
        "grounding_required": "mandatory",
        "specialization_required": True,
        "cost_band": "medium",
    }
    body_map = _build_body_map(route_intent="error_diagnosis", requirements=requirements)

    selection = CapabilitySelectionPolicy().select(
        body_map=body_map,
        capability_requirements=requirements,
        route_intent="error_diagnosis",
        current_context={"preferred_specialists": ["error_analyst"]},
        mode_strategy={},
    )

    capabilities_by_id = body_map["capabilities_by_id"]
    for item in selection["selected_capabilities"] + selection["rejected_capabilities"]:
        assert item["capability_id"] in capabilities_by_id
