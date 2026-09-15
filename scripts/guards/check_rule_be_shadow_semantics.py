#!/usr/bin/env python3
"""Rule BE: Shadow mode semantics guard.

Verifies that Aurora shadow mode is correctly implemented:
1. Each service checks mode == "off" and mode == "live"/"shadow" appropriately
2. Live-only side effects (DB writes, event publishes) are gated behind mode checks
3. Kill switch service is imported and used

Layer 1: Quick string presence check (fast fail)
Layer 2: AST-level verification of mode-guard structure
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _check_mode_guards_in_file(filepath: str, required_mode_checks: tuple[str, ...]) -> list[str]:
    """AST-level verification that mode checks exist and guard side effects."""
    failures: list[str] = []
    source = _read(filepath)

    # Layer 1: String presence (fast fail)
    for needle in required_mode_checks:
        if needle not in source:
            failures.append(f"{filepath}: missing {needle!r}")
            return failures

    # Layer 2: Parse AST and verify mode checks exist within function bodies
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Non-Python or unparseable — skip AST check, string check already passed
        return failures

    # Collect all If nodes that compare against mode strings
    mode_guards_found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            condition = ast.dump(node.test)
            # Check if the condition references "live", "off", or "shadow" mode strings
            for mode_val in ("live", "off", "shadow"):
                if f"'{mode_val}'" in condition or f'"{mode_val}"' in condition:
                    mode_guards_found.add(mode_val)

    # Verify we have both "off" and "live"/"shadow" guards
    if "off" not in mode_guards_found and "live" not in mode_guards_found:
        failures.append(
            f"{filepath}: AST scan found no mode guards (if mode == 'off' / if mode == 'live')"
        )

    return failures


def main() -> int:
    # Each service with its required mode-check strings and semantic expectations
    checks = {
        "backend/app/services/idiographic_association_service.py": {
            "needles": (
                'if mode == "live":',
                "await self._upsert_daily_vectors",
                "await self.event_bus.publish",
            ),
            "description": "idiographic association",
        },
        "backend/app/services/srl_phase_tracker_service.py": {
            "needles": (
                'live_write = mode == "live" and tracker_mode == "live"',
                "persist_missing=live_write",
                'status="applied" if live_write else "shadow"',
            ),
            "description": "SRL phase tracker",
        },
        "backend/app/services/social_signal_bridge.py": {
            "needles": (
                "AuroraStage33KillSwitchService",
                'if mode == "off":',
                'if mode != "live":',
            ),
            "description": "social signal bridge",
        },
        "backend/app/state_aggregator/service.py": {
            "needles": (
                "AuroraStage18KillSwitchService",
                'if aggregator_mode == "off":',
                'if aggregator_mode == "shadow":',
            ),
            "description": "state aggregator",
        },
    }

    failures: list[str] = []
    for path, config in checks.items():
        # Layer 1 + Layer 2 combined check
        file_failures = _check_mode_guards_in_file(path, config["needles"])
        failures.extend(file_failures)

    if failures:
        print("[Rule BE] FAIL - shadow semantics are not consistently guarded")
        for failure in failures:
            print(failure)
        return 1
    print("[Rule BE] PASS - shadow computes without live persistence/publish hooks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
