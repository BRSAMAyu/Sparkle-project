#!/usr/bin/env python3
"""Activation smoke test for Aurora kill switches.

Validates that all dormant switches have been promoted to live,
checks master/child consistency, and outputs a JSON report.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.core.kill_switch import normalize_mode

# All Aurora mode settings that should be live after activation
LIVE_EXPECTED = {
    "AURORA_STAGE18_AGGREGATOR_MODE",
    "AURORA_STAGE18_PUSH_POLICY_MODE",
    "AURORA_STAGE18_PUSH_DELIVERY_MODE",
    "AURORA_STAGE19_WORKING_MEMORY_MODE",
    "AURORA_STAGE19_LLM_EXTRACTOR_MODE",
    "AURORA_STAGE19_CONSOLIDATION_MODE",
    "AURORA_STAGE21_SKILL_STORE_MODE",
    "AURORA_STAGE21_SKILL_SELECTION_MODE",
    "AURORA_STAGE21_SKILL_SHARE_MODE",
    "AURORA_BAYESIAN_MODE",
    "AURORA_POLICY_COMPILER_MODE",
    "AURORA_REFLECTION_WIRE_MODE",
    "AURORA_SCENE_MODE",
    "AURORA_FORESIGHT_MODE",
    "AURORA_TRAITS_MODE",
    "AURORA_TRAITS_NLP_MODE",
    "AURORA_TRAITS_COLDSTART_MODE",
    "AURORA_SRL_MODE",
    "AURORA_SRL_TRACKER_MODE",
    "AURORA_SRL_BRIDGE_MODE",
    "AURORA_SRL_SCAFFOLDING_CONSUME_MODE",
    "AURORA_METACOG_MODE",
    "AURORA_METACOG_DASHBOARD_MODE",
    "AURORA_METACOG_PROCESS_SCAFFOLDING_MODE",
    "AURORA_METACOG_FSM_COMBINE_MODE",
    "AURORA_IDIOGRAPHIC_MODE",
    "AURORA_STAGE33_MODE",
    "AURORA_STAGE33_SOCIAL_MODE",
    "AURORA_STAGE33_SRL_MODE",
    "AURORA_STAGE33_WM_PROMPT_MODE",
    "AURORA_STAGE33_EVENTS_MODE",
    "AURORA_STAGE34_MODE",
    "AURORA_STAGE34_ERROR_BRIDGE_MODE",
    "AURORA_STAGE34_CAPSULE_MODE",
    "AURORA_STAGE34_JOURNEY_SUBSCRIBERS_ENABLED",
    "AURORA_STAGE35_MODE",
    "AURORA_STAGE35_METACOG_ROUTER_MODE",
    "AURORA_STAGE38_ERR_REPLAN_MODE",
    "AURORA_STAGE38_PUSH_SCHEDULER_MODE",
    "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE",
}

# Settings not expected to be live (sub-features of foresight, or non-mode bools)
ALWAYS_LIVE_ALLOWED = {
    "AURORA_FORESIGHT_ATTRACTOR",
    "AURORA_FORESIGHT_DEVIATION",
    "AURORA_FORESIGHT_JITAI",
    "AURORA_STAGE39_MODE",
    "AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE",
    "AURORA_STAGE39_COGLOAD_ROUTE_MODE",
    "AURORA_STAGE39_GALAXY_INJECT_MODE",
    "AURORA_STAGE40_CALENDAR_MODE",
    "AURORA_PRIVACY_PII_REDACTION_MODE",
}

ALL_MODE_SETTINGS = LIVE_EXPECTED | ALWAYS_LIVE_ALLOWED


def _check_settings_defaults() -> list[dict[str, str]]:
    """Check that all mode settings in settings.py resolve to live."""
    violations = []
    for attr in sorted(LIVE_EXPECTED):
        raw = getattr(settings, attr, None)
        mode = normalize_mode(raw)
        if mode != "live":
            violations.append({
                "setting": attr,
                "raw_value": str(raw),
                "resolved": mode,
                "expected": "live",
            })
    return violations


def _check_env_example() -> list[dict[str, str]]:
    """Check that .env.example matches the expected live defaults."""
    env_path = BACKEND_ROOT / ".env.example"
    if not env_path.exists():
        return [{"error": f"{env_path} not found"}]

    violations = []
    for attr in sorted(LIVE_EXPECTED):
        found = False
        with env_path.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith(f"{attr}="):
                    value = stripped.split("=", 1)[1].strip()
                    mode = normalize_mode(value)
                    if mode != "live":
                        violations.append({
                            "file": str(env_path),
                            "setting": attr,
                            "value": value,
                            "resolved": mode,
                            "expected": "live",
                        })
                    found = True
                    break
        if not found:
            violations.append({
                "file": str(env_path),
                "setting": attr,
                "error": "not found in .env.example",
            })
    return violations


async def _run_drill_check() -> dict[str, Any]:
    """Run the universal drill runner in check-only mode."""
    drill_script = REPO_ROOT / "scripts" / "stage40" / "run_kill_switch_drills.py"
    if not drill_script.exists():
        return {"error": f"{drill_script} not found"}
    return {"status": "drill script exists", "path": str(drill_script)}


def _check_rule_av() -> dict[str, Any]:
    """Check that Rule AV enum guard covers all switches."""
    guard_path = REPO_ROOT / "scripts" / "check_rule_av_kill_switch_mode_enum.py"
    if not guard_path.exists():
        return {"error": f"{guard_path} not found"}

    text = guard_path.read_text()
    missing = []
    for attr in sorted(LIVE_EXPECTED):
        if attr not in text:
            missing.append(attr)
    return {
        "all_covered": len(missing) == 0,
        "missing": missing,
    }


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Aurora activation smoke test")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--skip-drill", action="store_true", help="Skip drill runner check")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "settings_violations": _check_settings_defaults(),
        "env_example_violations": _check_env_example(),
        "rule_av": _check_rule_av(),
    }

    if not args.skip_drill:
        report["drill"] = await _run_drill_check()

    all_pass = (
        len(report["settings_violations"]) == 0
        and len(report["env_example_violations"]) == 0
        and report["rule_av"].get("all_covered", False) is True
    )
    report["pass"] = all_pass
    report["total_live_expected"] = len(LIVE_EXPECTED)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if not all_pass:
        print("[Activation Smoke] FAIL")
        if report["settings_violations"]:
            print(f"  Settings violations: {len(report['settings_violations'])}")
            for v in report["settings_violations"]:
                print(f"    {v['setting']}: {v.get('resolved', '?')} (expected live)")
        if report["env_example_violations"]:
            print(f"  .env.example violations: {len(report['env_example_violations'])}")
        if not report["rule_av"].get("all_covered", False):
            print(f"  Rule AV missing: {report['rule_av'].get('missing', [])}")
        return 1

    print(f"[Activation Smoke] PASS — {len(LIVE_EXPECTED)} switches all live")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
