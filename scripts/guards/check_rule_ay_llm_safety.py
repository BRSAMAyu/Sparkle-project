#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


IGNORE_RE = re.compile(r"#\s*rule-ay:\s*ignore\s+(.+)", re.IGNORECASE)
FORBIDDEN_PATTERNS = (
    (re.compile(r"\b(?:openai\.OpenAI|AsyncOpenAI|anthropic\.Anthropic)\("), "AY001 raw vendor client construction"),
    (re.compile(r"chat\.completions\.create\("), "AY002 raw chat completion call"),
    (re.compile(r"\.(?:a?completion)\("), "AY003 raw completion helper call"),
)
ALLOWED_FILES = {
    "backend/app/core/llm_client.py",
    "backend/app/services/llm/providers.py",
    "backend/app/services/llm_service.py",
}
EXCLUDED_FILES = {"backend/app/core/llm_secure_io.py"}


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "tests" not in path.parts and "_deprecated" not in path.parts
    )


def scan_rule_ay(*, repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    backend_app = repo_root / "backend" / "app"
    exceptions_doc = repo_root / "docs" / "aurora" / "rule_ay_exceptions.md"
    exceptions_text = exceptions_doc.read_text(encoding="utf-8") if exceptions_doc.exists() else ""

    violations: list[str] = []
    for path in _iter_python_files(backend_app):
        rel = path.relative_to(repo_root).as_posix()
        if rel in EXCLUDED_FILES or rel in ALLOWED_FILES:
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            ignore_here = IGNORE_RE.search(line)
            ignore_prev = IGNORE_RE.search(lines[lineno - 2]) if lineno > 1 else None
            ignore_match = ignore_here or ignore_prev

            for pattern, code in FORBIDDEN_PATTERNS:
                if not pattern.search(line):
                    continue
                if ignore_match:
                    marker = f"{rel}:{lineno}"
                    if marker not in exceptions_text:
                        violations.append(f"AY004 {marker} ignore is missing from docs/aurora/rule_ay_exceptions.md")
                    break
                violations.append(f"{code} {rel}:{lineno} must use SecureLLMClient.get or an approved wrapper")
                break

    return violations


def main() -> int:
    violations = scan_rule_ay()
    if violations:
        print("[Rule AY] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule AY] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
