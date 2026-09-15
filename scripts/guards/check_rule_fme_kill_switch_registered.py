#!/usr/bin/env python3
"""Rule guard: FME kill switches must remain registered.

Background — Phase-0 of the First-Minute Experience track introduces two
tri-state kill switches (`goal_first_minute`, `task_card_protocol_v2`) that
gate the Entry Wire and Execution Wire respectively. Per CLAUDE.md the
governance contract is:

  • A kill switch is registered iff there is both a KillSwitchBinding entry
    and a settings attribute that the binding points at.
  • Removing either side silently disables the safety mechanism — the
    feature would still ship but lose its `off` rollback.

This guard verifies the contract; if a future refactor accidentally removes
a binding or its settings attribute, CI fails before the change merges.

Exits 0 when both switches are healthy, non-zero otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = REPO_ROOT / "backend" / "app" / "services" / "fme_kill_switch_service.py"
SETTINGS_PATH = REPO_ROOT / "backend" / "app" / "config" / "settings.py"

REQUIRED_FEATURES = {
    "goal_first_minute": "FME_GOAL_FIRST_MINUTE_MODE",
    "task_card_protocol_v2": "FME_TASK_CARD_PROTOCOL_MODE",
}


def fail(msg: str) -> None:
    print(f"[RG-FME] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not SERVICE_PATH.is_file():
        fail(f"missing kill switch service file: {SERVICE_PATH}")
    if not SETTINGS_PATH.is_file():
        fail(f"missing settings file: {SETTINGS_PATH}")

    service_src = SERVICE_PATH.read_text(encoding="utf-8")
    settings_src = SETTINGS_PATH.read_text(encoding="utf-8")

    for feature, settings_attr in REQUIRED_FEATURES.items():
        # Binding must mention the feature name as a key in FEATURE_BINDINGS.
        if not re.search(rf'"{re.escape(feature)}"\s*:', service_src):
            fail(
                f"feature {feature!r} not registered in "
                "FmeKillSwitchService.FEATURE_BINDINGS"
            )
        # Binding must point at the matching settings attribute.
        if settings_attr not in service_src:
            fail(
                f"settings_attr {settings_attr!r} missing from binding for "
                f"feature {feature!r}"
            )
        # Settings file must declare the attribute with a default tri-state.
        if not re.search(
            rf"\b{re.escape(settings_attr)}\s*:\s*str\s*=\s*\"(off|shadow|live)\"",
            settings_src,
        ):
            fail(
                f"settings attribute {settings_attr!r} missing or has invalid "
                "default (must be one of off/shadow/live)"
            )

    print("[RG-FME] OK — both FME kill switches registered with valid defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
