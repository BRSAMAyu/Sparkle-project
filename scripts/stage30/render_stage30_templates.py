#!/usr/bin/env python3
"""Render docs/aurora/stage30_process_scaffolding_templates.md from the code registry.

原 v1 文档为未跟踪产物已丢失；本脚本从 `metacognition_registry` 代码注册表再生成，
保证文档与代码不漂移（Rule AO 依赖该文档存在且不含诊断性标签用语）。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.metacognition_registry import (  # noqa: E402
    DASHBOARD_LANGUAGE_TEMPLATES,
    PROCESS_SCAFFOLDING_TEMPLATES,
)

OUTPUT = REPO_ROOT / "docs/aurora/stage30_process_scaffolding_templates.md"


def _table(templates: tuple, title: str) -> list[str]:
    lines = [f"## {title}", "", "| template_id | dim | direction | i18n key |", "| --- | --- | --- | --- |"]
    for item in templates:
        lines.append(f"| `{item.template_id}` | {item.dim} | {item.direction} | `{item.template}` |")
    lines.append("")
    return lines


def main() -> int:
    lines = [
        "# Stage 30 · 过程脚手架与仪表盘语言模板注册表",
        "",
        "> 由 `scripts/stage30/render_stage30_templates.py` 从 `backend/app/services/metacognition_registry.py` 自动生成，勿手改。",
        "",
    ]
    lines.extend(_table(PROCESS_SCAFFOLDING_TEMPLATES, "过程脚手架模板（process_scaffolding）"))
    lines.extend(_table(DASHBOARD_LANGUAGE_TEMPLATES, "仪表盘语言模板（dashboard_language）"))
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
