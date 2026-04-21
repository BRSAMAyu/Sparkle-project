#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


FORBIDDEN_TOKENS = ("openai", "anthropic", "llm_", "chat_completion", "responses.create")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "backend" / "app" / "services" / "scene_consolidation_service.py"
    source = target.read_text(encoding="utf-8").lower()
    violations = [token for token in FORBIDDEN_TOKENS if token in source]
    if violations:
        print(f"Scene service contains forbidden LLM tokens: {', '.join(violations)}", file=sys.stderr)
        return 1
    print("Scene no-LLM import check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
