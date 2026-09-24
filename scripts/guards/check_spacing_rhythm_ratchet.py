#!/usr/bin/env python3
"""Spacing rhythm ratchet guard — N43 half-step grid erosion registry (A-SPEC7 v1.7).

Machine-check arm of the §3.3 two-tier card-padding revision proposed by
`v3-output/A-SPEC7/REPORT.md` §4 (N43) and executed by the
wt270-ty-cardpadding card:

  dim             clause  pattern / method
  --------------  ------  ----------------------------------------------------
  spacingHalfStep N43     half-step spacing values (2/6/10/14/18 — off the 4pt
                          base grid) in `mobile/lib/**`, counted per CODE LINE as
                            a) spacing-token usages: `spacing2|6|10|14|18`
                               (DS.spacing10, theme.spacing6, ...), plus
                            b) bare numeric literals on lines that also mention
                               `EdgeInsets` (padding/margin context).
                          台账口径 1285 处=18%（A-SPEC7 §2.1b 只数 spacing token）；
                          本守卫机器口径含 EdgeInsets 行裸字面量，故基线数更大，
                          基线 JSON 是棘轮唯一事实源。存量登记只降不升，不做专项
                          清洗（新组件只准取 4 基栅格档 4/8/12/16/20/24/32/40/48/64）。

Ratchet discipline (same family as TYPO-RHYTHM / UI-TOKENS / DL-SPEC): per-file
counts frozen in `spacing_rhythm_baseline.json` — a file exceeding its baseline
count, or a NEW file with any violation, fails. Counts may only go down; after
a burn batch lowers counts run `--update-baseline` and commit the JSON diff.

Inline ignore marker (KNOWN TRAP — read before using): put
`// spacing-rhythm-ratchet:ignore <reason>` at the END of the offending line
itself. Comment-only lines (including a marker on its own line above the
violation) are stripped BEFORE counting, so a leading marker never reaches the
counter and does NOT suppress anything.

Known undercount (accepted, like DL-SPEC's sat<0.15): bare half-step literals
on a CONTINUATION line of a multi-line EdgeInsets constructor are not counted
(the line lacks the word `EdgeInsets`); token-based usages are line-independent
and remain fully covered.

Read-only scanner: never modifies scanned sources. Exit 0 pass / 1 violations.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = Path(__file__).resolve().parent / "spacing_rhythm_baseline.json"

MOBILE_LIB_REL = "mobile/lib"

GENERATED_SUFFIXES = (".g.dart", ".freezed.dart")

# `spacing2|6|10|14|18` token usages (DS.spacing10 / theme.spacing6 / ...).
# \b anchors keep spacing12/spacing16/spacing20/spacing180 out.
_HALF_STEP_TOKEN_RE = re.compile(r"\bspacing(?:2|6|10|14|18)\b")

# Bare half-step literals: 2 / 6 / 10 / 14 / 18 (with optional .0), not part of
# a longer number and not a decimal fragment (0.6, 1.35, 0.18 are protected by
# the lookarounds).
_HALF_STEP_LITERAL_RE = re.compile(r"(?<![\w.])(?:2|6|10|14|18)(?:\.0)?(?![\w.])")

# Bare literals only count on lines that are actually about EdgeInsets.
_EDGEINSETS_RE = re.compile(r"\bEdgeInsets\b")

# Trailing inline ignore marker — must ride the MATCHED line (see module doc).
_IGNORE_RE = re.compile(r"spacing-rhythm-ratchet\s*:\s*ignore\b")

DIM = "spacingHalfStep"


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
        return {DIM: 0}
    n = 0
    for line in _code_lines(text):
        if _IGNORE_RE.search(line):
            continue
        c = len(_HALF_STEP_TOKEN_RE.findall(line))
        if _EDGEINSETS_RE.search(line):
            c += len(_HALF_STEP_LITERAL_RE.findall(line))
        n += c
    return {DIM: n}


def scan(repo_root: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for path in _dart_files(repo_root / MOBILE_LIB_REL):
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        c = count_file(path)
        if c[DIM]:
            counts[rel] = {DIM: c[DIM]}
    return counts


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    return {DIM: sum(c.get(DIM, 0) for c in counts.values())}


def update_baseline(repo_root: Path) -> int:
    current = scan(repo_root)
    current_totals = totals(current)
    old_totals = None
    if BASELINE_PATH.exists():
        old = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        old_totals = totals(old.get("files", {}))
        raised = [d for d in current_totals if current_totals[d] > old_totals[d]]
        if raised:
            detail = ", ".join(f"{d}: {old_totals[d]} -> {current_totals[d]}" for d in raised)
            print(f"[spacing-rhythm-ratchet] REFUSED — --update-baseline would RAISE totals ({detail}). "
                  "Baselines only go down. Fix the code.")
            return 1
        arrow = f"{old_totals} -> "
    else:
        arrow = ""
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_spacing_rhythm_ratchet.py "
            "(A-SPEC7 N43 half-step grid erosion registry + §3.3 card-padding "
            "two-tier revision; frozen by wt270-ty-cardpadding). Machine scope "
            "= spacing tokens 2/6/10/14/18 + bare literals on EdgeInsets "
            "lines, mobile/lib. Only lower via --update-baseline after a burn "
            "batch lowers counts; never raise."
        ),
        "files": current,
    }
    BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[spacing-rhythm-ratchet] baseline updated: {arrow}{current_totals} "
          f"({len(current)} files)")
    return 0


def run_guard(repo_root: Path, baseline_path: Path) -> int:
    if not baseline_path.exists():
        print(f"[spacing-rhythm-ratchet] FAIL — baseline missing: {baseline_path}")
        return 1
    current = scan(repo_root)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")).get("files", {})

    violations: list[str] = []
    for rel, c in sorted(current.items()):
        b = baseline.get(rel)
        if b is None:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
            violations.append(f"NEW FILE {rel}: {summary} (baseline: none)")
            continue
        for d in sorted(c):
            if c[d] > b.get(d, 0):
                violations.append(
                    f"{rel}: {d} {c[d]} > baseline {b.get(d, 0)} (+{c[d] - b.get(d, 0)})"
                )

    if violations:
        print(f"[spacing-rhythm-ratchet] FAIL — {len(violations)} ratchet violation(s); "
              "spacing debt may only decrease (A-SPEC7 N43 §3.3)")
        for v in violations:
            print(f"  {v}")
        print("\nAction: new components must take 4pt-base-grid steps "
              "(4/8/12/16/20/24/32/40/48/64; card inner padding two-tier: "
              "list card DS.cardPaddingList=12 / content card "
              "DS.cardPaddingContent=16). If a burn batch legitimately LOWERED "
              "counts, refresh baseline via:")
        print("  python3 scripts/guards/check_spacing_rhythm_ratchet.py --update-baseline")
        print("Registered-stock exemptions need a TRAILING marker on the matched "
              "line itself: `// spacing-rhythm-ratchet:ignore <reason>` — a "
              "marker on its own comment line is stripped before counting and "
              "does NOT suppress (known trap).")
        return 1

    ct = totals(current)
    bt = totals(baseline)
    print(
        "[spacing-rhythm-ratchet] PASS — ratchet holds: "
        f"{DIM}={ct[DIM]}/{bt[DIM]} "
        f"({len(current)} files with debt)"
    )
    return 0


def self_test() -> int:
    """End-to-end fixture tests proving every dimension trips and ratchets."""
    failures: list[str] = []

    def make_fixture() -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="spacing-rhythm-selftest-"))
        (tmp / MOBILE_LIB_REL).mkdir(parents=True)
        return tmp

    # Case 1 — clean fixture matching empty baseline: PASS; comment lines and
    # on-grid values never count.
    tmp = make_fixture()
    try:
        f = tmp / MOBILE_LIB_REL / "ok_widget.dart"
        f.write_text(
            "final a = EdgeInsets.all(DS.spacing12);\n"
            "// spacing: 10 in comment must not count\n"
            "final b = EdgeInsets.symmetric(horizontal: 16, vertical: 8);\n",
            encoding="utf-8",
        )
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case1 clean fixture should PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 2 — token + EdgeInsets-literal counts trip; new file with debt FAILs.
    tmp = make_fixture()
    try:
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        (tmp / MOBILE_LIB_REL / "bad_widget.dart").write_text(
            "final a = EdgeInsets.all(DS.spacing10);\n"
            "final b = EdgeInsets.symmetric(horizontal: 6, vertical: 14);\n"
            "final c = EdgeInsets.all(18.0);\n"
            "final d = SizedBox(width: theme.spacing6);\n",
            encoding="utf-8",
        )
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1:
            failures.append("case2 stacked-violation file should FAIL")
        # expected count: spacing10(1) + 6(1) + 14(1) + 18.0(1) + spacing6(1) = 5
        if "NEW FILE mobile/lib/bad_widget.dart: spacingHalfStep=5" not in buf.getvalue():
            failures.append("case2 should count exactly 5 (got: "
                            + buf.getvalue().strip().splitlines()[:1].__str__() + ")")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 3 — ratchet: pinned file raising FAILs; lowering PASSes.
    tmp = make_fixture()
    try:
        pinned = MOBILE_LIB_REL + "/legacy_widget.dart"
        f = tmp / pinned
        f.write_text("final a = EdgeInsets.all(10);\n", encoding="utf-8")
        bp = tmp / "baseline.json"
        bp.write_text(
            json.dumps({"files": {pinned: {"spacingHalfStep": 1}}}), encoding="utf-8"
        )
        import contextlib
        import io

        f.write_text(
            "final a = EdgeInsets.all(10);\n"
            "final b = EdgeInsets.all(6);\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "spacingHalfStep 2 > baseline 1" not in buf.getvalue():
            failures.append("case3a pinned-file raise should FAIL")

        f.write_text("final a = EdgeInsets.all(DS.spacing12);\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case3b lowered pinned file should PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 4 — the KNOWN TRAP: a leading comment-line marker does NOT suppress;
    # a trailing marker on the matched line DOES.
    tmp = make_fixture()
    try:
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        f = tmp / MOBILE_LIB_REL / "trap_widget.dart"
        f.write_text(
            "// spacing-rhythm-ratchet:ignore registered stock\n"
            "final a = EdgeInsets.all(10);\n",
            encoding="utf-8",
        )
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "NEW FILE mobile/lib/trap_widget.dart: spacingHalfStep=1" not in buf.getvalue():
            failures.append("case4a leading comment marker must NOT suppress")

        f.write_text(
            "final a = EdgeInsets.all(10); // spacing-rhythm-ratchet:ignore registered stock\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case4b trailing marker on matched line should suppress")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"[spacing-rhythm-ratchet] SELF-TEST FAIL — {len(failures)} case(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[spacing-rhythm-ratchet] SELF-TEST PASS — clean PASS, token+literal "
          "count=5, ratchet raise/lower, leading-vs-trailing ignore trap all behave")
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
