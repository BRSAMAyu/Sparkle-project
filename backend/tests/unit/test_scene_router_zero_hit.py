from __future__ import annotations

from pathlib import Path


def test_recent_scenes_is_not_referenced_by_routing_engine() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    source = (backend_root / "app" / "orchestration" / "routing_engine.py").read_text(encoding="utf-8")

    assert "recent_scenes" not in source


def test_recent_scenes_is_not_referenced_by_router_modules() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    for path in (backend_root / "app" / "routing").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "recent_scenes" not in source, f"Router module unexpectedly consumes recent_scenes: {path}"
