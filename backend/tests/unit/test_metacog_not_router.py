from __future__ import annotations

from pathlib import Path

FORBIDDEN = (
    "metacognition_profile",
    "metacognition_dashboard",
    "metacognition_process_scaffolding",
)


def test_router_modules_do_not_read_metacognition_fields() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    targets = list((backend_root / "app" / "routing").glob("*.py"))
    targets.extend((backend_root / "app" / "core").glob("*router*.py"))
    for path in targets:
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            assert (
                token not in source
            ), f"Router module unexpectedly consumes {token}: {path}"


def test_routing_engine_does_not_reference_metacognition() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    source = (backend_root / "app" / "orchestration" / "routing_engine.py").read_text(
        encoding="utf-8"
    )
    assert "metacognition_profile" not in source
    assert "metacognition_dashboard" not in source
