from app.orchestration.capability_requirement_compiler import CapabilityRequirementCompiler


def test_requirement_compiler_forces_grounding_when_user_materials_are_attached() -> None:
    payload = CapabilityRequirementCompiler().compile(
        user_context_payload={
            "current_query": "Use my uploaded notes to explain this.",
            "attached_materials": [{"file_id": "file-1"}],
            "user_strategy_state": {"retrieval_emphasis": "balanced"},
        },
        plan_context={},
        decision_context={"experience_mode": "explain", "grounding_priority": ["user_materials"]},
        insight_state={},
        planning_strategy={"plan_depth": "light"},
        route_intent="knowledge",
    )

    assert payload["grounding_required"] == "mandatory"
    assert payload["material_dependency"] == "mandatory"
    assert "ungrounded_generalization" in payload["forbidden_paths"]


def test_requirement_compiler_avoids_specialist_and_deep_paths_for_overload() -> None:
    payload = CapabilityRequirementCompiler().compile(
        user_context_payload={
            "current_query": "This is too much and I still cannot start.",
            "user_strategy_state": {"session_mode": "guided"},
        },
        plan_context={},
        decision_context={"experience_mode": "stabilize"},
        insight_state={"readiness_level": "low"},
        planning_strategy={"plan_depth": "deep"},
        route_intent="chat",
    )

    assert payload["planning_depth_required"] == "light"
    assert payload["cost_band"] == "low"
    assert payload["specialization_required"] is False
    assert "deep_planning" in payload["forbidden_paths"]


def test_requirement_compiler_marks_specialist_for_error_diagnosis() -> None:
    payload = CapabilityRequirementCompiler().compile(
        user_context_payload={"current_query": "Help me debug the root cause of this calculus error."},
        plan_context={},
        decision_context={"experience_mode": "explain"},
        insight_state={"readiness_level": "high"},
        planning_strategy={"plan_depth": "targeted"},
        route_intent="error_diagnosis",
    )

    assert payload["specialization_required"] is True
    assert payload["cost_band"] == "medium"


def test_requirement_compiler_treats_boolean_material_attachment_as_grounding_signal() -> None:
    payload = CapabilityRequirementCompiler().compile(
        user_context_payload={
            "current_query": "Use the file I attached to explain where I went wrong.",
            "materials_attached": True,
        },
        plan_context={},
        decision_context={"experience_mode": "explain"},
        insight_state={},
        planning_strategy={"plan_depth": "light"},
        route_intent="knowledge",
    )

    assert payload["grounding_required"] == "mandatory"
    assert payload["material_dependency"] == "mandatory"


def test_requirement_compiler_marks_translation_specialist_when_specialist_lane_is_live() -> None:
    payload = CapabilityRequirementCompiler().compile(
        user_context_payload={
            "current_query": "Translate this short paragraph into Chinese and keep the tone natural.",
            "specialist_translation_available": True,
        },
        plan_context={},
        decision_context={"experience_mode": "explain"},
        insight_state={"readiness_level": "not_applicable"},
        planning_strategy={"plan_depth": "light"},
        route_intent="translation",
    )

    assert payload["specialization_required"] is True
    assert payload["cost_band"] == "low"
