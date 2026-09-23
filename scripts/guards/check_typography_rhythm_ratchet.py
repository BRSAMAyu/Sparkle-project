#!/usr/bin/env python3
"""Typography rhythm ratchet guard — N41 sub-12 floor + N42 weight cap (A-SPEC7 v1.7).

Machine-check arm of the typography-rhythm clauses proposed by
`v3-output/A-SPEC7/REPORT.md` §4 and executed by the TYPE-RHYTHM card:

  dim id        clause  pattern / method
  ------------  ------  ----------------------------------------------------
  sub12FontSize N41     numeric-literal `fontSize: N` with N < 12 in
                        `mobile/lib/features/**` (ratchet; registered stock
                        frozen — sub-12 禁新增, 白名单外只降不升; 微标签豁免走
                        N45 登记制, 迁移归 §3.1 数值迁移批)
  fontWeightW800 N42    `FontWeight.w800` in `mobile/lib/**` (ratchet pinned
                        at 0 by the TYPE-RHYTHM card — non-standard weight,
                        w700 is the role-table cap; 禁新增/存量清零)
  fontWeightW900 N42    `FontWeight.w900` in `mobile/lib/**` (ratchet; N42
                        存量 6 处登记只降不升, 触碰即迁)

Ratchet discipline (same family as UI-TOKENS / DL-SPEC / UX-COMP): per-file
counts frozen in `typography_rhythm_baseline.json` — a file exceeding its
baseline count, or a NEW file with any violation, fails. Counts may only go
down; after a burn batch lowers counts run `--update-baseline` and commit the
JSON diff.

Baseline provenance: A-SPEC7 REPORT §2.1b registers sub-12 存量 238 处
(11×122、10×101、9×9、8×6, mixed-scope manual count). This scanner's own
machine-countable features-scope figure at freeze time is lower (comment-line
filtered, decimals split out); the JSON baseline is the enforcement source of
truth, and the registered 238 remains the ledger number (N45).

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
BASELINE_PATH = Path(__file__).resolve().parent / "typography_rhythm_baseline.json"

FEATURES_REL = "mobile/lib/features"
MOBILE_LIB_REL = "mobile/lib"

GENERATED_SUFFIXES = (".g.dart", ".freezed.dart")

_FONTSIZE_RE = re.compile(r"fontSize:\s*(\d+(?:\.\d+)?)")
_W800_RE = re.compile(r"\bFontWeight\.w800\b")
_W900_RE = re.compile(r"\bFontWeight\.w900\b")

SUB12_FLOOR = 12.0


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
        return {"sub12FontSize": 0, "fontWeightW800": 0, "fontWeightW900": 0}
    lines = _code_lines(text)
    sub12 = sum(
        1
        for ln in lines
        for m in _FONTSIZE_RE.finditer(ln)
        if float(m.group(1)) < SUB12_FLOOR
    )
    return {
        "sub12FontSize": sub12,
        "fontWeightW800": sum(len(_W800_RE.findall(ln)) for ln in lines),
        "fontWeightW900": sum(len(_W900_RE.findall(ln)) for ln in lines),
    }


def scan(repo_root: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}

    def absorb(path: Path, dims: tuple[str, ...]) -> None:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        c = count_file(path)
        picked = {d: c[d] for d in dims if c[d]}
        if not picked:
            return
        merged = counts.setdefault(rel, {})
        for d, n in picked.items():
            merged[d] = max(merged.get(d, 0), n)

    # features files get the full dimension set; the wider mobile/lib walk
    # only contributes the weight dims (merge, never overwrite).
    for path in _dart_files(repo_root / FEATURES_REL):
        absorb(path, ("sub12FontSize", "fontWeightW800", "fontWeightW900"))
    features_seen = set(counts)
    for path in _dart_files(repo_root / MOBILE_LIB_REL):
        absorb(path, ("fontWeightW800", "fontWeightW900"))
    assert set(counts) >= features_seen  # merge-only invariant
    return counts


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    return {
        "sub12FontSize": sum(c.get("sub12FontSize", 0) for c in counts.values()),
        "fontWeightW800": sum(c.get("fontWeightW800", 0) for c in counts.values()),
        "fontWeightW900": sum(c.get("fontWeightW900", 0) for c in counts.values()),
    }


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
            print(f"[typo-rhythm-ratchet] REFUSED — --update-baseline would RAISE totals ({detail}). "
                  "Baselines only go down. Fix the code.")
            return 1
        arrow = f"{old_totals} -> "
    else:
        arrow = ""
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_typography_rhythm_ratchet.py "
            "(A-SPEC7 N41 sub-12 floor + N42 weight cap; frozen by the "
            "TYPE-RHYTHM card). Only lower via --update-baseline after a burn "
            "batch lowers counts; never raise."
        ),
        "files": current,
    }
    BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[typo-rhythm-ratchet] baseline updated: {arrow}{current_totals} "
          f"({len(current)} files)")
    return 0


def run_guard(repo_root: Path, baseline_path: Path) -> int:
    if not baseline_path.exists():
        print(f"[typo-rhythm-ratchet] FAIL — baseline missing: {baseline_path}")
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
        print(f"[typo-rhythm-ratchet] FAIL — {len(violations)} ratchet violation(s); "
              "typography debt may only decrease (A-SPEC7 N41/N42)")
        for v in violations:
            print(f"  {v}")
        print("\nAction: consume SparkleTypography roles (context.typo.* / textTheme; "
              "floor = caption/labelMedium 12, weight cap = w700). If a burn batch "
              "legitimately LOWERED counts, refresh baseline via:")
        print("  python3 scripts/guards/check_typography_rhythm_ratchet.py --update-baseline")
        return 1

    ct = totals(current)
    bt = totals(baseline)
    print(
        "[typo-rhythm-ratchet] PASS — ratchet holds: "
        f"sub12FontSize={ct['sub12FontSize']}/{bt['sub12FontSize']}, "
        f"fontWeightW800={ct['fontWeightW800']}/{bt['fontWeightW800']}, "
        f"fontWeightW900={ct['fontWeightW900']}/{bt['fontWeightW900']} "
        f"({len(current)} files with debt)"
    )
    return 0


def self_test() -> int:
    """End-to-end fixture tests proving every dimension trips and ratchets."""
    failures: list[str] = []

    def make_fixture() -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="typo-rhythm-selftest-"))
        (tmp / "mobile/lib/features/demo/presentation").mkdir(parents=True)
        (tmp / "mobile/lib/core/design").mkdir(parents=True)
        return tmp

    # Case 1 — clean fixture matching baseline: PASS.
    tmp = make_fixture()
    try:
        f = tmp / "mobile/lib/features/demo/presentation/ok_screen.dart"
        f.write_text(
            "final a = TextStyle(fontSize: 12);\n"
            "// fontSize: 9 in comment must not count\n"
            "final b = FontWeight.w700;\n",
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
        if "comment" in buf.getvalue() and "fontSize: 9" in buf.getvalue():
            failures.append("case1 comment line should not count")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 2 — new file stacking violations: FAIL, each dim named.
    tmp = make_fixture()
    try:
        bp = tmp / "baseline.json"
        bp.write_text(json.dumps({"files": {}}), encoding="utf-8")
        (tmp / "mobile/lib/features/demo/presentation/bad_screen.dart").write_text(
            "final a = TextStyle(fontSize: 11.5);\n"
            "final b = TextStyle(fontSize: 10);\n"
            "final c = FontWeight.w800;\n"
            "final d = FontWeight.w900;\n",
            encoding="utf-8",
        )
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1:
            failures.append("case2 stacked-violation file should FAIL")
        for needle in ("sub12FontSize", "fontWeightW800", "fontWeightW900"):
            if needle not in buf.getvalue():
                failures.append(f"case2 should flag {needle}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Case 3 — pinned file raising a count: FAIL; lowering: PASS.
    tmp = make_fixture()
    try:
        pinned = "mobile/lib/features/demo/presentation/legacy_screen.dart"
        f = tmp / pinned
        f.write_text("final a = TextStyle(fontSize: 11);\n", encoding="utf-8")
        bp = tmp / "baseline.json"
        bp.write_text(
            json.dumps({"files": {pinned: {"sub12FontSize": 1}}}), encoding="utf-8"
        )
        import contextlib
        import io

        f.write_text(
            "final a = TextStyle(fontSize: 11);\n"
            "final b = TextStyle(fontSize: 9);\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "sub12FontSize 2 > baseline 1" not in buf.getvalue():
            failures.append("case3a pinned-file raise should FAIL")

        f.write_text("final a = TextStyle(fontSize: 14);\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 0:
            failures.append("case3b lowered pinned file should PASS")

        # weight dim in core (mobile-lib scope) is covered too
        core = tmp / "mobile/lib/core/design/poster.dart"
        core.write_text("final c = FontWeight.w800;\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_guard(tmp, bp)
        if code != 1 or "fontWeightW800" not in buf.getvalue():
            failures.append("case3c core-scope w800 should FAIL")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"[typo-rhythm-ratchet] SELF-TEST FAIL — {len(failures)} case(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[typo-rhythm-ratchet] SELF-TEST PASS — clean PASS, stacked violations, "
          "ratchet raise/lower, core-scope weights all behave")
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
