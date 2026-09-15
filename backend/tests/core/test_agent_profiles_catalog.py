from app.core.agent_profiles import AgentRole, get_public_agent_catalog, get_public_mode_catalog
from app.core.llm_router import llm_router


def test_public_agent_catalog_has_required_fields():
    catalog = get_public_agent_catalog()
    assert len(catalog) > 0
    for item in catalog:
        assert item["id"]
        assert item["display_name"]
        assert "entry_chat_mode" in item
        assert item["entry_chat_mode"].startswith("expert::")
        assert isinstance(item["tags"], list)
        assert isinstance(item["enabled"], bool)


def test_public_mode_catalog_contains_expert_auto():
    modes = get_public_mode_catalog()
    ids = {item["id"] for item in modes}
    assert "expert_auto" in ids


def test_llm_router_describes_agent_routing_candidates():
    routing = llm_router.describe_agent_routing(AgentRole.GALAXY_GUIDE)
    assert routing["selected_model_key"]
    assert routing["selected_model_key"] in routing["candidate_models"]
    assert len(routing["candidate_models"]) >= 2
