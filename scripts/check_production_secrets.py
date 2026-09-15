#!/usr/bin/env python3
"""Pre-deployment secret validation.

Checks that production environment secrets are present and that tracked files do
not contain provider-shaped credentials. The output intentionally names only
files/variables, never secret values.

Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "backend" / ".env"

PLACEHOLDER_PREFIXES = ("your_", "replace_with", "changeme", "placeholder", "example_", "dummy_")
PLACEHOLDER_VALUES = {
    "",
    "dev",
    "test",
    "password",
    "postgres",
    "redis",
    "secret",
    "minioadmin",
    "your-secret-key",
    "your_api_key_here",
}

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
    "XIAOMI_MIMO_API_KEY",
    "ZHIPU_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "SILICONFLOW_API_KEY",
    "HUNYUAN_API_KEY",
]

_LINE_PATTERN = re.compile(r"^([A-Z_]+)=(.*)$")
_TRACKED_ENV_PATTERN = re.compile(r"(^|/)\.env($|\.)")
_ALLOWED_TRACKED_ENV_SUFFIXES = (".example", ".local.example", ".deploy.example")
_PROVIDER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI-compatible key", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
)
_NAMED_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "Zhipu API key",
        re.compile(r"(?im)^\s*ZHIPU_API_KEY\s*=\s*['\"]?([0-9a-f]{32}\.[A-Za-z0-9_-]{8,})['\"]?\s*$"),
    ),
    (
        "XunFei API key",
        re.compile(r"(?im)^\s*XUNFEI_API_KEY\s*=\s*['\"]?([0-9a-f]{32})['\"]?\s*$"),
    ),
    (
        "XunFei API secret",
        re.compile(r"(?im)^\s*XUNFEI_API_SECRET\s*=\s*['\"]?([A-Za-z0-9+/=_-]{24,})['\"]?\s*$"),
    ),
)


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return normalized in PLACEHOLDER_VALUES or any(normalized.startswith(p) for p in PLACEHOLDER_PREFIXES)


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


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [REPO_ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def _is_allowed_tracked_env(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return rel.endswith(_ALLOWED_TRACKED_ENV_SUFFIXES)


def _scan_tracked_files() -> list[str]:
    findings: list[str] = []
    for path in _tracked_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not path.exists() or path.is_dir():
            continue

        if _TRACKED_ENV_PATTERN.search(rel) and not _is_allowed_tracked_env(path):
            findings.append(f"{rel}: runtime .env file is tracked")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for name, pattern in _PROVIDER_PATTERNS:
            if pattern.search(content):
                findings.append(f"{rel}: provider-shaped credential found ({name})")

        for name, pattern in _NAMED_SECRET_PATTERNS:
            match = pattern.search(content)
            if match and not _is_placeholder(match.group(1)):
                findings.append(f"{rel}: provider-shaped credential found ({name})")

    return findings


def _validate_env_file() -> list[str]:
    env = _load_env(ENV_PATH)
    if not env:
        print(f"[Secrets] SKIP — {ENV_PATH} not found (development mode)")
        return []

    violations: list[str] = []

    for name in CRITICAL_SECRETS:
        val = env.get(name, "")
        if _is_placeholder(val):
            violations.append(f"{name} is empty or placeholder")

    has_llm = any(env.get(k, "") and not _is_placeholder(env[k]) for k in LLM_KEY_NAMES)
    if not has_llm:
        violations.append("No LLM API key configured (need one of: " + ", ".join(LLM_KEY_NAMES) + ")")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate production secrets without printing secret values.")
    parser.add_argument(
        "--env-only",
        action="store_true",
        help="only validate backend/.env and skip tracked-file scanning",
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="only scan tracked files and skip backend/.env validation",
    )
    args = parser.parse_args(argv)

    violations: list[str] = []
    if not args.tracked_only:
        violations.extend(_validate_env_file())
    if not args.env_only:
        violations.extend(_scan_tracked_files())

    if violations:
        print("[Secrets] FAIL — secret validation issues detected:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("[Secrets] PASS — production secrets and tracked files validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
