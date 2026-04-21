from __future__ import annotations

from pathlib import Path

from app.services.source_state_encoder import (
    RULE_AH_DIMENSION_REGISTRY,
    SOURCE_STATE_ALLOWED_VALUES,
    SOURCE_STATE_DIMENSION_ORDER,
)


def test_rule_ah_dimension_registry_covers_all_whitelisted_dimensions() -> None:
    assert tuple(RULE_AH_DIMENSION_REGISTRY.keys()) == SOURCE_STATE_DIMENSION_ORDER


def test_rule_ah_dimension_registry_allowed_values_match_encoder_contract() -> None:
    for name, entry in RULE_AH_DIMENSION_REGISTRY.items():
        assert entry.allowed_values == SOURCE_STATE_ALLOWED_VALUES[name]
        assert entry.sqam_evidence


def test_rule_ah_dimension_registry_markdown_contains_all_dimensions() -> None:
    path = Path("/Users/brsama/code/GitHub/Sparkle-project/docs/aurora/rule_ah_dimension_registry.md")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for name in SOURCE_STATE_DIMENSION_ORDER:
        assert f"`{name}`" in text
