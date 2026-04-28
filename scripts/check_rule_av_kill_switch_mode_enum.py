#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "backend" / "app" / "config" / "settings.py"
METRICS_PATH = REPO_ROOT / "backend" / "app" / "core" / "metrics.py"
SERVICE_PATHS = [
    REPO_ROOT / "backend/app/services/aurora_stage18_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage19_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage21_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage23_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage24_policy_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage25_reflection_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage26_scene_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage27_foresight_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage28_traits_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage29_srl_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage30_metacognition_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage31_idiographic_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage33_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage34_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage35_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage40_calendar_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_doc_context_kill_switch_service.py",
    REPO_ROOT / "backend/app/services/aurora_stage38_kill_switch_service.py",
]
MODE_SETTINGS = {
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
    "AURORA_FORESIGHT_ATTRACTOR",
    "AURORA_FORESIGHT_DEVIATION",
    "AURORA_FORESIGHT_JITAI",
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
    "AURORA_STAGE40_CALENDAR_MODE",
    "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE",
}
MODE_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Z0-9_]+):\s*str\s*=\s*(?:\(\s*)?\"(?P<value>[^\"]+)\"",
    re.MULTILINE,
)
ALLOWED = {"off", "shadow", "live"}


def main() -> int:
    violations: list[str] = []
    settings_text = SETTINGS_PATH.read_text(encoding="utf-8")
    settings_map = {match.group("name"): match.group("value") for match in MODE_PATTERN.finditer(settings_text)}

    missing_settings = sorted(MODE_SETTINGS - set(settings_map))
    if missing_settings:
        violations.extend(f"missing mode setting: {name}" for name in missing_settings)

    invalid = {
        name: value
        for name, value in settings_map.items()
        if name in MODE_SETTINGS and value not in ALLOWED
    }
    if invalid:
        for name, value in sorted(invalid.items()):
            violations.append(f"invalid mode enum {name}={value!r}")

    metrics_text = METRICS_PATH.read_text(encoding="utf-8")
    if "sparkle_kill_switch_mode" not in metrics_text:
        violations.append("sparkle_kill_switch_mode metric missing")

    for path in SERVICE_PATHS:
        if not path.exists():
            violations.append(f"missing kill switch service: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if "app.core.kill_switch" not in text:
            violations.append(f"service does not use shared kill_switch helper: {path.relative_to(REPO_ROOT)}")

    if violations:
        print("[Rule AV] FAIL")
        for item in violations:
            print(item)
        return 1

    print(f"[Rule AV] PASS - validated {len(MODE_SETTINGS)} mode settings and {len(SERVICE_PATHS)} kill switch services")
    return 0


if __name__ == "__main__":
    sys.exit(main())
