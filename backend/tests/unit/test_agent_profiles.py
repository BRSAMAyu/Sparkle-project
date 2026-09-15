from app.core.agent_profiles import AgentProfileRegistry, AgentRole, AgentProfile, ModelTier


def test_get_model_config_supports_free_and_specialist_tiers() -> None:
    profile = AgentProfile(
        role=AgentRole.GENERATION,
        display_name="生成",
        description="test",
        model_tier=ModelTier.FREE_REASONING,
    )
    available_models = {
        "free_model": {"name": "free"},
        "free_fast_model": {"name": "free-fast"},
        "free_reasoning_model": {"name": "free-reasoning"},
        "specialist_model": {"name": "specialist"},
    }

    assert profile.get_model_config(available_models) == {"name": "free-reasoning"}

    profile.model_tier = ModelTier.SPECIALIST
    assert profile.get_model_config(available_models) == {"name": "specialist"}


def test_agent_profile_registry_does_not_mutate_global_defaults() -> None:
    registry = AgentProfileRegistry()
    original_title = registry.get_profile(AgentRole.GENERATION).display_name

    registry.update_profile(AgentRole.GENERATION, {"display_name": "局部修改"})

    assert registry.get_profile(AgentRole.GENERATION).display_name == "局部修改"
    fresh_registry = AgentProfileRegistry()
    assert fresh_registry.get_profile(AgentRole.GENERATION).display_name == original_title
