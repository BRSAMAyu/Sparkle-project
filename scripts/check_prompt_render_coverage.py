#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = REPO_ROOT / "backend/app/orchestration/prompts.py"
OUTPUT_PATH = REPO_ROOT / "docs/product/stage22_prompt_coverage_baseline.md"

AUDIT_FIELDS: dict[str, str] = {
    "error_summary": "近期痛点中的错题摘要",
    "recent_errors": "近期痛点中的错题样本",
    "recent_mastery_changes": "近期进展中的掌握度变化",
    "active_tasks": "待办任务 / next_actions",
    "preferences": "学习偏好",
    "social_context": "社交上下文渲染器",
    "profile_context": "通过知识/画像快照间接可见",
    "community_context": "仅在社区摘要链路命中时可见",
    "knowledge_summary": "知识薄弱点 / 画像摘要",
    "focus_stats": "专注统计",
    "engagement_metrics": "行为分析摘要",
}


def _status_for(field: str, prompt_text: str) -> str:
    mark_pattern = re.compile(rf'_mark_rendered\("{re.escape(field)}"\)')
    if mark_pattern.search(prompt_text):
        return "rendered"
    if field == "profile_context" and "【画像快照】" in prompt_text:
        return "rendered"
    if field == "community_context":
        return "conditional"
    if field == "knowledge_summary":
        return "partial"
    return "missing"


def _build_markdown(results: list[tuple[str, str]]) -> str:
    covered = sum(1 for _field, status in results if status in {"rendered", "conditional", "partial"})
    total = len(results)
    ratio = covered / total if total else 1.0

    lines = [
        "# Stage 22 Prompt Coverage Baseline",
        "",
        f"- audited_at: {OUTPUT_PATH.stat().st_mtime if OUTPUT_PATH.exists() else 'fresh-run'}",
        f"- audited_fields: {total}",
        f"- covered_fields: {covered}",
        f"- coverage_ratio: {ratio:.3f}",
        f"- baseline_interpretation: {'PASS' if ratio >= 0.70 else 'ESCALATE'}",
        "",
        "## Covered",
        "",
    ]
    for field, status in results:
        if status in {"rendered", "conditional", "partial"}:
            emoji = "✅" if status == "rendered" else ("🔄" if status == "conditional" else "🟡")
            lines.append(f"- {emoji} `{field}` — {AUDIT_FIELDS[field]} ({status})")

    lines.extend(["", "## Gaps", ""])
    missing = False
    for field, status in results:
        if status == "missing":
            missing = True
            lines.append(f"- ❌ `{field}` — {AUDIT_FIELDS[field]}")
    if not missing:
        lines.append("- None in the Stage 22 audited set.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    prompt_text = PROMPTS.read_text(encoding="utf-8")
    results = [(field, _status_for(field, prompt_text)) for field in AUDIT_FIELDS]
    covered = sum(1 for _field, status in results if status in {"rendered", "conditional", "partial"})
    ratio = covered / len(results)
    print(f"covered={covered} total={len(results)} ratio={ratio:.3f}")
    for field, status in results:
        print(f"{field}\t{status}")

    if args.write:
        OUTPUT_PATH.write_text(_build_markdown(results), encoding="utf-8")
        print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
