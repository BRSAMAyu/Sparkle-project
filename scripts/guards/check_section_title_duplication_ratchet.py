#!/usr/bin/env python3
"""Section-title duplication ratchet guard — A-wt283 同屏双标题去重的防回归臂.

Machine-check arm of the A-line 同屏双标题统一 (card wt283-dedup-section-titles):

  dim id     clause  pattern / method
  ---------  ------  ------------------------------------------------------
  dualTitle  wt283   同一 dart 文件内，某 l10n key 已作分区标题
                     （`title: context.l10n.<key>`，ExpandableSection /
                     _SectionCard 等分区件通用形态），同 key 又在文件内
                     再次出现（典型：子卡内部标题行 Text(context.l10n.<key>)）
                     ——即「段落标题 + 卡内标题同串双现」反模式。

裁决基线（A-wt283）：段落标题保留（分区件单源播报），卡内标题移除；
卡内仅保留图标并入首行内容。 accountability_detail_screen 三对双标题
（待执行策略/近期反思/前瞻提示）已按此收敛，本守卫冻结收敛后存量。

Ratchet discipline (same family as UI-TOKENS / TYPO-RHYTHM / UX-COMP):
per-file counts frozen in `section_title_duplication_baseline.json` — a file
exceeding its baseline count, or a NEW file with any violation, fails.
Counts may only go down; after a burn batch lowers counts run
`--update-baseline` and commit the JSON diff.

Known limit: only the dominant `context.l10n.<key>` access style is scanned;
files that alias l10n through a local variable escape detection (accepted for
an S-card guard — the anti-pattern's recurrence surface is the direct style).

Read-only scanner: never modifies scanned sources. Exit 0 pass / 1 violations.
"""
from __future__ import annotations

import argparse
import io
import json
import contextlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = (
    Path(__file__).resolve().parent / "section_title_duplication_baseline.json"
)

FEATURES_REL = "mobile/lib/features"

GENERATED_SUFFIXES = (".g.dart", ".freezed.dart")

_TITLE_USE_RE = re.compile(r"title:\s*context\.l10n\.([A-Za-z0-9_]+)\b")
_ANY_USE_RE = re.compile(r"\bcontext\.l10n\.([A-Za-z0-9_]+)\b")


def _code_lines(text: str) -> list[str]:
    """Drop comment-only lines so comments cannot trip the counters."""
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        out.append(line)
    return out


def _dart_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        p
        for p in sorted(root.rglob("*.dart"))
        if not p.name.endswith(GENERATED_SUFFIXES)
    ]


def count_file(path: Path) -> dict[str, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"dualTitle": 0}
    lines = _code_lines(text)
    joined = "\n".join(lines)
    title_keys = set(_TITLE_USE_RE.findall(joined))
    if not title_keys:
        return {"dualTitle": 0}
    used_keys = _ANY_USE_RE.findall(joined)
    dual = sum(1 for k in title_keys if used_keys.count(k) >= 2)
    return {"dualTitle": dual}


def scan(repo_root: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for path in _dart_files(repo_root / FEATURES_REL):
        c = count_file(path)
        if c["dualTitle"]:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
            counts[rel] = c
    return counts


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    return {"dualTitle": sum(c.get("dualTitle", 0) for c in counts.values())}


def update_baseline(repo_root: Path) -> int:
    current = scan(repo_root)
    current_totals = totals(current)
    old_totals = None
    if BASELINE_PATH.exists():
        old = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        old_totals = totals(old.get("files", {}))
        raised = [d for d in current_totals if current_totals[d] > old_totals[d]]
        if raised:
            detail = ", ".join(
                f"{d}: {old_totals[d]} -> {current_totals[d]}" for d in raised
            )
            print(
                f"[dup-title-ratchet] REFUSED — --update-baseline would RAISE "
                f"totals ({detail}). Baselines only go down. Fix the code."
            )
            return 1
        arrow = f"{old_totals} -> "
    else:
        arrow = ""
    payload = {
        "comment": (
            "Frozen ratchet baseline for "
            "check_section_title_duplication_ratchet.py (A-wt283 同屏双标题"
            "去重：段落标题由分区件单源，卡内标题移除；冻结收敛后存量). "
            "Only lower via --update-baseline after a burn batch lowers "
            "counts; never raise."
        ),
        "files": current,
    }
    BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"[dup-title-ratchet] baseline updated: {arrow}{current_totals} "
        f"({len(current)} files)"
    )
    return 0


def run_guard(repo_root: Path, baseline_path: Path) -> int:
    if not baseline_path.exists():
        print(f"[dup-title-ratchet] FAIL — baseline missing: {baseline_path}")
        return 1
    current = scan(repo_root)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")).get("files", {})

    violations: list[str] = []
    for rel, c in sorted(current.items()):
        b = baseline.get(rel)
        if b is None:
            violations.append(
                f"NEW FILE {rel}: dualTitle={c['dualTitle']} (baseline: none)"
            )
            continue
        if c["dualTitle"] > b.get("dualTitle", 0):
            violations.append(
                f"{rel}: dualTitle {c['dualTitle']} > baseline "
                f"{b.get('dualTitle', 0)} (+{c['dualTitle'] - b.get('dualTitle', 0)})"
            )

    if violations:
        print(
            f"[dup-title-ratchet] FAIL — {len(violations)} ratchet violation(s); "
            "同屏双标题（段落标题 + 卡内同串标题）存量只降不升 (A-wt283)"
        )
        for v in violations:
            print(f"  {v}")
        print(
            "\nAction: 段落标题由分区组件（ExpandableSection/_SectionCard 等）"
            "单源播报，移除卡内重复标题（图标并入首行内容）。若 burn 批次合法"
            "降低了计数，刷新基线："
        )
        print(
            "  python3 scripts/guards/"
            "check_section_title_duplication_ratchet.py --update-baseline"
        )
        return 1

    ct = totals(current)
    bt = totals(baseline)
    print(
        "[dup-title-ratchet] PASS — ratchet holds: "
        f"dualTitle={ct['dualTitle']}/{bt['dualTitle']} "
        f"({len(current)} files with stock)"
    )
    return 0


def self_test() -> int:
    """End-to-end fixture tests proving the dimension trips and ratchets."""
    failures: list[str] = []

    def make_fixture() -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="dup-title-selftest-"))
        (tmp / "mobile/lib/features/demo/presentation").mkdir(parents=True)
        return tmp

    def write_screen(tmp: Path, name: str, body: str) -> Path:
        f = tmp / "mobile/lib/features/demo/presentation" / name
        f.write_text(body, encoding="utf-8")
        return f

    clean = (
        "Widget b(BuildContext c) => ExpandableSection(\n"
        "  title: c.l10n.x,\n"  # non-l10n-direct style, ignored
        ");\n"
        "Widget w(BuildContext context) => Column(children: [\n"
        "  // Text(context.l10n.sectionA) — comment must not count\n"
        "  Text(context.l10n.body),\n"
        "]);\n"
        "Widget s(BuildContext context) => ExpandableSection(\n"
        "  title: context.l10n.sectionA,\n"
        "  child: Text(context.l10n.body),\n"
        ");\n"
    )

    dirty = (
        "Widget s(BuildContext context) => ExpandableSection(\n"
        "  title: context.l10n.sectionA,\n"
        "  child: Row(children: [Icon(Icons.x), Text(context.l10n.sectionA)]),\n"
        ");\n"
    )

    # Case 1 — clean fixture + matching (empty) baseline: PASS.
    tmp = make_fixture()
    try:
        write_screen(tmp, "ok_screen.dart", clean)
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append(f"case1 clean should PASS, got {code}: {buf.getvalue()}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 2 — dual-title NEW file: FAIL.
    tmp = make_fixture()
    try:
        write_screen(tmp, "bad_screen.dart", dirty)
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "bad_screen.dart" not in buf.getvalue():
            failures.append(f"case2 dual-title NEW file should FAIL: {buf.getvalue()}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 3 — ratchet only-down: baseline 2 with stock 2 passes;
    # baseline 1 with stock 2 fails. (update-baseline raise-refusal is not
    # fixture-tested: it writes the module-level repo baseline path, so it
    # must never run against fixtures.)
    tmp = make_fixture()
    try:
        write_screen(
            tmp,
            "ratchet_screen.dart",
            dirty
            + "Widget t(BuildContext context) => SectionCard(\n"
            "  title: context.l10n.sectionB,\n"
            "  child: Text(context.l10n.sectionB),\n"
            ");\n",
        )
        bp = tmp / "baseline.json"
        rel = "mobile/lib/features/demo/presentation/ratchet_screen.dart"
        bp.write_text(
            json.dumps({"files": {rel: {"dualTitle": 2}}}), encoding="utf-8"
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append(f"case3a stock==baseline should PASS: {buf.getvalue()}")
        bp.write_text(json.dumps({"files": {rel: {"dualTitle": 1}}}), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1:
            failures.append(f"case3b stock>baseline should FAIL: {buf.getvalue()}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"[dup-title-ratchet] SELF-TEST FAIL — {len(failures)} case(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(
        "[dup-title-ratchet] SELF-TEST PASS — clean PASS, dual-title FAIL, "
        "ratchet only-down all behave"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite baseline JSON from current counts (only after a batch LOWERED counts)",
    )
    parser.add_argument("--self-test", action="store_true", help="run end-to-end fixture tests")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.update_baseline:
        return update_baseline(REPO_ROOT)
    return run_guard(REPO_ROOT, BASELINE_PATH)


if __name__ == "__main__":
    sys.exit(main())
