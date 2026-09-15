from __future__ import annotations

from pathlib import Path

from app.services.jitai_trigger_service import TEMPLATE_REGISTRY


def test_jitai_templates_stay_within_character_budget() -> None:
    assert len(TEMPLATE_REGISTRY) >= 10
    assert all(len(item["message"]) <= 80 for item in TEMPLATE_REGISTRY.values())


def test_jitai_template_source_has_no_llm_imports() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "jitai_trigger_service.py"
    ).read_text(encoding="utf-8").lower()

    assert "openai" not in source
    assert "anthropic" not in source
    assert "llm_" not in source
