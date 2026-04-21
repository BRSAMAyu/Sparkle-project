from __future__ import annotations

from pathlib import Path


FORBIDDEN = ("foresight_hint", "deviations", "attractors")


def test_rule_al_router_engine_has_no_foresight_tokens() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    source = (backend_root / "app" / "orchestration" / "routing_engine.py").read_text(encoding="utf-8")

    for token in FORBIDDEN:
        assert token not in source


def test_rule_al_router_modules_have_no_foresight_tokens() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    targets = list((backend_root / "app" / "routing").glob("*.py"))
    targets.extend((backend_root / "app" / "core").glob("*router*.py"))
    for path in targets:
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            assert token not in source, f"Router module unexpectedly consumes {token}: {path}"
