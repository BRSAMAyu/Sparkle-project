#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.task_reflection_service import TaskReflectionService


REGISTRY_PATH = REPO_ROOT / "docs/aurora/rule_aj_reflection_triggers.md"
EXPECTED = {
    "too_difficult": "AURORA_REFLECTION_TRIGGER_TOO_DIFFICULT",
    "unclear": "AURORA_REFLECTION_TRIGGER_UNCLEAR",
    "abandoned": "AURORA_REFLECTION_TRIGGER_ABANDONED",
    "intervention_ineffective": "AURORA_REFLECTION_TRIGGER_INTERVENTION_INEFFECTIVE",
    "plan_stall": "AURORA_REFLECTION_TRIGGER_PLAN_STALL",
    "overload": "AURORA_REFLECTION_TRIGGER_OVERLOAD",
}


def main() -> int:
    if not REGISTRY_PATH.exists():
        print("missing trigger registry doc")
        return 1
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8")
    missing: list[str] = []
    for category, env_name in EXPECTED.items():
        if category not in TaskReflectionService.ELIGIBLE_CATEGORIES:
            missing.append(f"category missing from ELIGIBLE_CATEGORIES: {category}")
        if category not in TaskReflectionService.PROMPT_TEMPLATES:
            missing.append(f"prompt template missing: {category}")
        if category not in TaskReflectionService.TRIGGER_PROMPT_VERSIONS:
            missing.append(f"prompt version missing: {category}")
        if category not in registry_text or env_name not in registry_text:
            missing.append(f"registry doc missing mapping: {category} -> {env_name}")
    if missing:
        print("Reflection trigger registry drift detected:")
        for item in missing:
            print(f"- {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
