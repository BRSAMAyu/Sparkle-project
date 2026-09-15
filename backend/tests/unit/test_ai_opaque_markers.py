from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_ai_opaque_markers_exist_on_stage34_models() -> None:
    for rel_path in (
        "backend/app/models/notification_interaction.py",
        "backend/app/models/shop.py",
        "backend/app/models/visual_element.py",
    ):
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "# AI-OPAQUE:" in text
