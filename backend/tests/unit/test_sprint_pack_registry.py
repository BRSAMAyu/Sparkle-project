"""Unit tests for Sprint Pack registry subject detection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.sprint_packs.sprint_pack_loader import load_pack
from app.sprint_packs.sprint_pack_registry import SprintPackRegistry


def test_registry_detects_subjects_from_alias_and_pack_metadata() -> None:
    registry = SprintPackRegistry()

    assert registry.match_subject("操作系统") is not None
    assert registry.match_subject("帮我备考操作系统期末") is not None
    assert registry.match_subject("算法设计") is not None
    assert registry.list_available_subjects()


def test_load_pack_uses_registry_for_free_form_subject_text() -> None:
    pack = load_pack("帮我备考操作系统")

    assert pack is not None
    assert pack["id"] == "operating_systems@v1"
