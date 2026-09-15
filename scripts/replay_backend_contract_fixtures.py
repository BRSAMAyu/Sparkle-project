#!/usr/bin/env python3
"""Replay fixed backend contract fixtures and verify structural outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _bootstrap_imports() -> None:
    backend_dir = _repo_root() / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def run_fixture_file(path: Path) -> list[str]:
    _bootstrap_imports()

    from app.core.unified_intent_router import UnifiedIntentRouter, UnifiedIntentType
    from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput

    cases = json.loads(path.read_text(encoding="utf-8"))
    router = UnifiedIntentRouter()
    dual_core_router = DualCoreRouter()
    failures: list[str] = []

    for case in cases:
        kind = case["kind"]
        name = case["name"]
        if kind == "intent_routing":
            intent = UnifiedIntentType(case["intent"])
            mode = router._determine_execution_mode(
                message=case["message"],
                intent=intent,
                confidence=float(case["confidence"]),
            )
            risk = router._assess_risk_level(message=case["message"], intent=intent)
            expected = case["expect"]
            if mode != expected["mode"] or risk != expected["risk"]:
                failures.append(
                    f"{name}: expected mode={expected['mode']} risk={expected['risk']}, got mode={mode} risk={risk}"
                )
        elif kind == "dual_core_routing":
            routing_input = DualCoreRoutingInput(**case["input"])
            decision = dual_core_router.route(routing_input)
            expected = case["expect"]
            if decision.mode != expected["mode"]:
                failures.append(f"{name}: expected mode={expected['mode']}, got {decision.mode}")
                continue
            ux_mode = expected.get("ux_mode")
            if ux_mode and decision.ux_mode != ux_mode:
                failures.append(f"{name}: expected ux_mode={ux_mode}, got {decision.ux_mode}")
            contains = expected.get("contains_reason")
            if contains and contains not in decision.reason:
                failures.append(f"{name}: expected reason to contain {contains!r}, got {decision.reason!r}")
            contains_adjustment = expected.get("contains_adjustment")
            if contains_adjustment and not any(
                contains_adjustment in item for item in decision.cognitive_adjustments
            ):
                failures.append(
                    f"{name}: expected cognitive adjustment to contain {contains_adjustment!r}, "
                    f"got {decision.cognitive_adjustments!r}"
                )
            contains_constraint = expected.get("contains_constraint")
            if contains_constraint and not any(
                contains_constraint in item for item in decision.execution_constraints
            ):
                failures.append(
                    f"{name}: expected execution constraint to contain {contains_constraint!r}, "
                    f"got {decision.execution_constraints!r}"
                )
            prompt_contains = expected.get("prompt_contains")
            if prompt_contains and prompt_contains not in decision.prompt_instruction:
                failures.append(
                    f"{name}: expected prompt instruction to contain {prompt_contains!r}, "
                    f"got {decision.prompt_instruction!r}"
                )
        else:
            failures.append(f"{name}: unsupported fixture kind {kind!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay backend contract fixtures")
    parser.add_argument(
        "--fixture",
        default="backend/tests/fixtures/contract_replay_cases.json",
        help="Fixture JSON file to replay",
    )
    args = parser.parse_args()

    fixture_path = _repo_root() / args.fixture
    failures = run_fixture_file(fixture_path)
    if failures:
        print("❌ Backend fixture replay failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("✅ Backend fixture replay passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
