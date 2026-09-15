#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _load_service_templates(service_path: Path) -> dict[str, dict[str, str]]:
    module = ast.parse(service_path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TEMPLATE_REGISTRY":
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "TEMPLATE_REGISTRY":
                return ast.literal_eval(node.value)
    raise RuntimeError("TEMPLATE_REGISTRY not found in jitai_trigger_service.py")


def _load_doc_template_ids(doc_path: Path) -> set[str]:
    template_ids: set[str] = set()
    pattern = re.compile(r"\|\s*`([^`]+)`\s*\|")
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            template_ids.add(match.group(1))
    return template_ids


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    service_path = repo_root / "backend" / "app" / "services" / "jitai_trigger_service.py"
    doc_path = repo_root / "docs" / "aurora" / "stage27_jitai_templates.md"

    templates = _load_service_templates(service_path)
    template_ids = {item["template_id"] for item in templates.values()}
    if len(template_ids) < 10:
        print(f"Expected at least 10 registered JITAI templates, found {len(template_ids)}.", file=sys.stderr)
        return 1

    doc_template_ids = _load_doc_template_ids(doc_path)
    missing = sorted(template_ids - doc_template_ids)
    if missing:
        print("Template registry doc is missing JITAI templates:", file=sys.stderr)
        for template_id in missing:
            print(f"  - {template_id}", file=sys.stderr)
        return 1

    print("JITAI template registry check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
