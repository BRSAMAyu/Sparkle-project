#!/usr/bin/env python3
"""S22-PROMPT guard — Stage 22 prompt render coverage ratchet.

Scans ``backend/app/orchestration/prompts.py`` for the audited render-marker set
and validates it against the frozen baseline
``docs/product/stage22_prompt_coverage_baseline.md``.

Read-only discipline (fixes the read-time-rewrite anti-pattern): the default
guard run NEVER writes — a single guard sweep used to rewrite the baseline's
``audited_at`` timestamp and dirty the worktree. The baseline is refreshed only
via the explicit ``--write`` flag, and that write follows the DL-SPEC ratchet
pattern (``scripts/guards/check_dl_spec_ratchet.py``): coverage may only go UP;
a write that would lower ``covered_fields``/``coverage_ratio`` is REFUSED unless
``--allow-drop`` is also passed.

CLI:
  python3 scripts/check_prompt_render_coverage.py            # read-only guard run
  python3 scripts/check_prompt_render_coverage.py --write    # explicit baseline refresh
  python3 scripts/check_prompt_render_coverage.py --min-ratio 0.85

Exit 0 pass / 1 fail (or refused write). Never touches any other file.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS = REPO_ROOT / "backend/app/orchestration/prompts.py"
OUTPUT_PATH = REPO_ROOT / "docs/product/stage22_prompt_coverage_baseline.md"

AUDIT_FIELDS: dict[str, str] = {
    "error_summary": "近期痛点中的错题摘要",
    "recent_errors": "近期痛点中的错题样本",
    "recent_mastery_changes": "近期进展中的掌握度变化",
    "active_tasks": "待办任务 / next_actions",
    "active_goals": "当前目标",
    "episodic_memories": "近期相关记忆",
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
    if field == "active_goals" and "【当前目标】" in prompt_text:
        return "rendered"
    if field == "episodic_memories" and "【近期相关记忆】" in prompt_text:
        return "rendered"
    if field == "community_context":
        return "conditional"
    if field == "knowledge_summary":
        return "partial"
    return "missing"


def _build_markdown(results: list[tuple[str, str]], audited_at: float | str) -> str:
    covered = sum(1 for _field, status in results if status in {"rendered", "conditional", "partial"})
    total = len(results)
    ratio = covered / total if total else 1.0

    lines = [
        "# Stage 22 Prompt Coverage Baseline",
        "",
        f"- audited_at: {audited_at}",
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


def _content_signature(text: str) -> list[str]:
    """Baseline content ignoring the audited_at line (the only line a legitimate
    refresh may change; everything else is the frozen ratchet state)."""
    return [ln for ln in text.splitlines() if not ln.startswith("- audited_at:")]


def _parse_counts(text: str) -> tuple[int, int, float] | None:
    """(audited_fields, covered_fields, coverage_ratio) from a baseline, or None."""
    m_total = re.search(r"- audited_fields:\s*(\d+)", text)
    m_covered = re.search(r"- covered_fields:\s*(\d+)", text)
    m_ratio = re.search(r"- coverage_ratio:\s*([0-9.]+)", text)
    if not (m_total and m_covered and m_ratio):
        return None
    return int(m_total.group(1)), int(m_covered.group(1)), float(m_ratio.group(1))


def scan_results() -> list[tuple[str, str]]:
    prompt_text = PROMPTS.read_text(encoding="utf-8")
    return [(field, _status_for(field, prompt_text)) for field in AUDIT_FIELDS]


def summarize(results: list[tuple[str, str]]) -> tuple[int, int, float]:
    covered = sum(1 for _f, s in results if s in {"rendered", "conditional", "partial"})
    total = len(results)
    return covered, total, (covered / total if total else 1.0)


def run_guard(min_ratio: float) -> int:
    if not OUTPUT_PATH.exists():
        print(
            f"[s22-prompt] FAIL — baseline missing: {OUTPUT_PATH.relative_to(REPO_ROOT)}\n"
            "Action: first audit then freeze baseline explicitly via:\n"
            "  python3 scripts/check_prompt_render_coverage.py --write"
        )
        return 1
    results = scan_results()
    covered, total, ratio = summarize(results)
    expected = _content_signature(_build_markdown(results, audited_at="<ignored>"))
    actual = _content_signature(OUTPUT_PATH.read_text(encoding="utf-8"))
    print(f"[s22-prompt] live: covered={covered} total={total} ratio={ratio:.3f} (min-ratio={min_ratio})")
    for field, status in results:
        print(f"  {field}\t{status}")

    failures: list[str] = []
    if expected != actual:
        exp_map = dict(results)
        base_map = {
            m.group(1): "missing" if m.group(0).startswith("- ❌") else "covered"
            for m in re.finditer(r"- (?:✅|🔄|🟡|❌) `(\w+)`[^\n]*", "\n".join(actual))
        }
        for field in AUDIT_FIELDS:
            live_status = exp_map[field]
            base_status = base_map.get(field, "absent-from-baseline")
            live_bucket = "missing" if live_status == "missing" else "covered"
            if live_bucket != base_status:
                failures.append(f"{field}: baseline={base_status} live={live_bucket} ({live_status})")
        if not failures:
            failures.append("baseline metadata (counts/ratio) drifted from live field statuses")
    if ratio < min_ratio:
        failures.append(f"coverage_ratio {ratio:.3f} < min-ratio {min_ratio}")

    if failures:
        print(
            f"[s22-prompt] FAIL — {len(failures)} drift(s) between baseline and live prompts.py; "
            "read-only guard, baseline was NOT modified."
        )
        for f in failures:
            print(f"  {f}")
        print(
            "\nAction: after auditing the change, refresh baseline explicitly via:\n"
            "  python3 scripts/check_prompt_render_coverage.py --write"
        )
        return 1
    print(
        f"[s22-prompt] PASS — baseline holds: {covered}/{total} covered, "
        f"ratio={ratio:.3f} (read-only run, worktree untouched)"
    )
    return 0


def update_baseline(allow_drop: bool) -> int:
    results = scan_results()
    covered, total, ratio = summarize(results)
    old = _parse_counts(OUTPUT_PATH.read_text(encoding="utf-8")) if OUTPUT_PATH.exists() else None
    if old is not None:
        old_total, old_covered, old_ratio = old
        if (covered < old_covered or ratio < old_ratio) and not allow_drop:
            print(
                f"[s22-prompt] REFUSED — --write would LOWER coverage "
                f"(covered {old_covered} -> {covered}, ratio {old_ratio:.3f} -> {ratio:.3f}). "
                "Baselines only go up (DL-SPEC ratchet discipline). Fix prompts.py to render the "
                "dropped field, or pass --allow-drop if the drop is a deliberate, audited decision."
            )
            return 1
    _build_and_write(results)
    arrow = f"{old_covered if old else '?'} -> " if old else ""
    print(f"[s22-prompt] baseline updated: {arrow}covered={covered}/{total} ratio={ratio:.3f}")
    return 0


def _build_and_write(results: list[tuple[str, str]]) -> None:
    audited_at = time.time()
    OUTPUT_PATH.write_text(_build_markdown(results, audited_at), encoding="utf-8")
    print(f"[s22-prompt] wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="explicitly refresh the baseline markdown (default run is read-only validation)",
    )
    parser.add_argument(
        "--allow-drop",
        action="store_true",
        help="with --write, permit lowering coverage (deliberate debt increase; should never be needed)",
    )
    parser.add_argument("--min-ratio", type=float, default=0.85)
    args = parser.parse_args()

    if args.write:
        return update_baseline(args.allow_drop)
    return run_guard(args.min_ratio)


if __name__ == "__main__":
    raise SystemExit(main())
