#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "app" / "services" / "skill_extract_service.py"
KEYWORDS = ROOT / "backend" / "app" / "services" / "skill_extract_trigger_keywords.v1.json"


def main() -> int:
    if not TARGET.exists():
        print("[Skill Trigger Purity] PASS - extract service not landed yet")
        return 0

    text = TARGET.read_text(encoding="utf-8")
    violations: list[str] = []
    if "matches_explicit_trigger" not in text:
        violations.append("missing matches_explicit_trigger() rule path")
    if "TRIGGER_KEYWORDS_PATH" not in text:
        violations.append("trigger path is not backed by frozen keyword file")
    if "matches_explicit_trigger" in text and "chat_json" in text.split("matches_explicit_trigger", 1)[1].split("async def", 1)[0]:
        violations.append("explicit trigger matcher may not call LLM")
    if not KEYWORDS.exists():
        violations.append("missing frozen trigger keywords json")

    if violations:
        print("[Skill Trigger Purity] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Skill Trigger Purity] PASS - trigger recognition remains pure-rule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
