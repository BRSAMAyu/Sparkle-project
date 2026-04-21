from __future__ import annotations

from pathlib import Path


def test_foresight_hint_is_not_referenced_by_router_entrypoints() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    targets = [
        backend_root / "app" / "api" / "v1" / "router.py",
        backend_root / "app" / "orchestration" / "dual_core_router.py",
        backend_root / "app" / "orchestration" / "request_router.py",
        backend_root / "app" / "agents" / "graph" / "nodes" / "router.py",
    ]
    for path in targets:
        source = path.read_text(encoding="utf-8")
        assert "foresight_hint" not in source, f"Unexpected foresight reference in {path}"


def test_attractor_and_deviation_tokens_are_absent_from_router_tree() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    for path in (backend_root / "app" / "routing").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "attractors" not in source, f"Unexpected attractor reference in {path}"
        assert "deviations" not in source, f"Unexpected deviation reference in {path}"
