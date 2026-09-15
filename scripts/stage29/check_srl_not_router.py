#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend" / "app"
TARGETS = (
    BACKEND_ROOT / "orchestration" / "routing_engine.py",
    BACKEND_ROOT / "orchestration" / "dual_core_router.py",
    BACKEND_ROOT / "orchestration" / "prompts.py",
)


def main() -> int:
    required_tokens = {
        BACKEND_ROOT / "orchestration" / "routing_engine.py": ("srl_phase_hint", 'stage33_modes.get("srl")'),
        BACKEND_ROOT / "orchestration" / "dual_core_router.py": ("srl_phase_hint", "explicit_srl_signal"),
        BACKEND_ROOT / "orchestration" / "prompts.py": ("学习自调节阶段", "AURORA_STAGE33_SRL_MODE"),
    }
    forbidden_tokens = ("srl_phase_tracker_service", "SRLPhaseTrackerService")

    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        for token in required_tokens[path]:
            if token not in text:
                raise AssertionError(f"Missing gated SRL consumption token {token}: {path}")
        for token in forbidden_tokens:
            if token in text:
                raise AssertionError(f"Router unexpectedly imports tracker dependency {token}: {path}")
    print("PASS SRL router gated-consumption check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
