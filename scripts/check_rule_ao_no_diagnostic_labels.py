#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.metacognition_guard import scan_many  # noqa: E402
from app.services.metacognition_registry import render_guard_samples  # noqa: E402

DOC_TARGETS = (REPO_ROOT / "docs/aurora/stage30_process_scaffolding_templates.md",)
CODE_TARGETS = (
    REPO_ROOT / "backend/app/services/metacognition_registry.py",
    REPO_ROOT / "backend/app/services/metacognition_service.py",
)


def _doc_texts() -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for path in DOC_TARGETS:
        texts.append(
            (str(path.relative_to(REPO_ROOT)), path.read_text(encoding="utf-8"))
        )
    return texts


def _code_string_literals(path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    items: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if value:
                items.append(
                    (
                        f"{path.relative_to(REPO_ROOT)}:{getattr(node, 'lineno', '?')}",
                        value,
                    )
                )
    return items


def main() -> int:
    violations: list[str] = []

    for label, text in _doc_texts():
        matches = scan_many((text,), source=label)
        violations.extend(
            f"AO001 {label}:{match.pattern_id}:{match.matched_text}"
            for match in matches
        )

    for path in CODE_TARGETS:
        for label, text in _code_string_literals(path):
            matches = scan_many((text,), source=label)
            violations.extend(
                f"AO002 {label}:{match.pattern_id}:{match.matched_text}"
                for match in matches
            )

    runtime_matches = scan_many(render_guard_samples(), source="runtime_render")
    violations.extend(
        f"AO003 runtime_render:{match.pattern_id}:{match.matched_text}"
        for match in runtime_matches
    )

    if violations:
        print("[Rule AO] FAIL")
        for violation in violations:
            print(violation)
        return 1

    print(
        "[Rule AO] PASS - no diagnostic labels in Stage 30 docs, template registry, or rendered samples"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
