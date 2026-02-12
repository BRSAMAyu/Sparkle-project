from app.core.agent_profiles import get_public_agent_catalog, get_public_mode_catalog


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
