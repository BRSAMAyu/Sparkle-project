#!/usr/bin/env python3
"""Render docs/aurora/stage27_jitai_templates.md from the JITAI TEMPLATE_REGISTRY.

原 v1 文档为未跟踪产物已丢失；本脚本从 `jitai_trigger_service.py` 的注册表再生成，
保证文档与代码不漂移（Rule S27-JITAI 校验两侧 template_id 一致）。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE = REPO_ROOT / "backend/app/services/jitai_trigger_service.py"
OUTPUT = REPO_ROOT / "docs/aurora/stage27_jitai_templates.md"


def _load_registry() -> dict[str, dict[str, str]]:
    module = ast.parse(SERVICE.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "TEMPLATE_REGISTRY":
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TEMPLATE_REGISTRY" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("TEMPLATE_REGISTRY not found")


def main() -> int:
    registry = _load_registry()
    lines = [
        "# Stage 27 · JITAI 触发模板登记（jitai template registry）",
        "",
        "> 由 `scripts/stage27/render_jitai_templates.py` 从 `backend/app/services/jitai_trigger_service.py` 的 `TEMPLATE_REGISTRY` 自动生成，勿手改。",
        "",
        "| template_id | registry key | 触发语（zh） |",
        "| --- | --- | --- |",
    ]
    for key, item in registry.items():
        lines.append(f"| `{item['template_id']}` | `{key}` | {item['message']} |")
    lines.append("")
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(registry)} templates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
