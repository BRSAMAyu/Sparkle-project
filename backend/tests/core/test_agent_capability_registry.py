from app.core.agent_capability_registry import get_capability_catalog


REQUIRED_MODE_FIELDS = {
    "id",
    "label",
    "description",
    "entry_chat_mode",
    "enabled",
    "rank",
    "tags",
}

REQUIRED_EXPERT_FIELDS = {
    "id",
    "display_name",
    "description",
    "tags",
    "entry_chat_mode",
    "recommended_scenarios",
    "enabled",
    "rank",
}


def test_capability_catalog_shape() -> None:
    catalog = get_capability_catalog()
    assert "modes" in catalog
    assert "experts" in catalog
    assert "total_experts" in catalog

    modes = catalog["modes"]
    experts = catalog["experts"]

    assert isinstance(modes, list)
    assert isinstance(experts, list)
    assert catalog["total_experts"] == len(experts)

    for mode in modes:
        assert REQUIRED_MODE_FIELDS.issubset(mode.keys())

    for expert in experts:
        assert REQUIRED_EXPERT_FIELDS.issubset(expert.keys())
        assert expert["entry_chat_mode"].startswith("expert::")


def test_capability_catalog_contains_core_modes() -> None:
    mode_ids = {item["id"] for item in get_capability_catalog()["modes"]}
    assert "standard" in mode_ids
    assert "expert_auto" in mode_ids
