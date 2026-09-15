from __future__ import annotations

import json
from pathlib import Path

from app.orchestration.ai_strategy_ontology import build_inventory_fixture, model_facing_terms


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "semantic_control_vocabulary_inventory.json"


def test_semantic_control_inventory_fixture_matches_canonical_inventory() -> None:
    fixture = json.loads(_fixture_path().read_text(encoding="utf-8"))
    assert fixture == build_inventory_fixture()


def test_all_model_facing_terms_are_present_in_inventory_fixture() -> None:
    fixture = json.loads(_fixture_path().read_text(encoding="utf-8"))
    terms_in_fixture = {item["term"] for item in fixture}
    for term in model_facing_terms():
        if term == "session_mode":
            assert term in terms_in_fixture
        elif term in {"primary_residual", "loop_type", "confidence_label", "planning_readiness", "planning_readiness_action"}:
            assert term in terms_in_fixture
        else:
            assert term in terms_in_fixture
