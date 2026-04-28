#!/usr/bin/env python3
"""Pre-deployment secret validation.

Checks that no placeholder values remain in the production .env file.
Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "backend" / ".env"

PLACEHOLDER_PREFIXES = ("your_", "replace_with", "changeme")

CRITICAL_SECRETS = [
    "SECRET_KEY",
    "JWT_SECRET",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "INTERNAL_API_KEY",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
]

LLM_KEY_NAMES = [
    "LLM_API_KEY",
    "ZHIPU_API_KEY",
    "DEEPSEEK_API_KEY",
]

_LINE_PATTERN = re.compile(r"^([A-Z_]+)=(.*)$")


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        m = _LINE_PATTERN.match(line.strip())
        if m:
            val = m.group(2).strip()
            # Strip surrounding quotes
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            env[m.group(1)] = val
    return env


def main() -> int:
    env = _load_env(ENV_PATH)
    if not env:
        print(f"[Secrets] SKIP — {ENV_PATH} not found (development mode)")
        return 0

    violations: list[str] = []

    for name in CRITICAL_SECRETS:
        val = env.get(name, "")
        if not val or any(val.startswith(p) for p in PLACEHOLDER_PREFIXES):
            violations.append(f"{name} is empty or placeholder: {val!r}")

    has_llm = any(
        env.get(k, "") and not any(env[k].startswith(p) for p in PLACEHOLDER_PREFIXES)
        for k in LLM_KEY_NAMES
    )
    if not has_llm:
        violations.append("No LLM API key configured (need one of: " + ", ".join(LLM_KEY_NAMES) + ")")

    if violations:
        print("[Secrets] FAIL — placeholder secrets detected:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print(f"[Secrets] PASS — {len(CRITICAL_SECRETS)} critical secrets + LLM key validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
