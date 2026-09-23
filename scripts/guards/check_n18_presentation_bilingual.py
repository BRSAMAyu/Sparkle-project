#!/usr/bin/env python3
r"""N18 presentation bilingual-inline guard — ratchet the `zh ? '…' : '…` escape channel.

A-SPEC3 (v3-output/A-SPEC3/REPORT.md N18, top7 #4) found that while SPEC §6.5
makes the arb files the single entry point for UI copy, presentation code kept
growing inline bilingual ternaries (`zh ? '中文' : 'English'`), which bypass
arb review, l10n coverage accounting and translator workflows entirely.

This guard ratchets ONE dimension (SPEC v1.3 N18 机检落地):

- dim `bilingualInlineTernary`: occurrences in
  `mobile/lib/features/*/presentation/**` of a zh-conditioned ternary whose
  BOTH branches are quoted string literals. Recognized condition shapes
  (measured in-repo @835e91d7):
    `zh ? '…' : '…'`                        (local `final zh = …languageCode == 'zh'`)
    `_isZh ? '…' : '…'` / `isZh ? '…' : '…'` (extension/getter bool)
    `languageCode == 'zh' ? '…' : '…'`      (inline comparison)
  A NEW file with any hit fails; per-file counts may only go down.
  Known blind spot (registered): branches held in variables
  (`languageCode == 'zh' ? zh : en`) are not string-literal pairs and are not
  counted; no such hit exists in presentation @835e91d7.

Out of scope by card decision: data/mock layers (outside the presentation
scan root) and core/ (whole-lib inventory 222+31=253 is A-SPEC3's grep
caliber; this guard freezes the presentation root first). Explicitly
registered domain aggregate files may be whitelisted in the baseline JSON
with a reason; the whitelist starts empty.

Baseline: `n18_presentation_bilingual_baseline.json`, registered from
measured values at HEAD 835e91d7 (L10N-ZH card wt236, 2026-09-23): 152 hits
across 26 presentation files (regex caliber, multiline-inclusive; the A-SPEC3
report's per-file "31" for goal_detail_l10n.dart is the single-line grep
caliber of the same 34 ternaries). Counts may only go down (ratchet); after
a cleanup batch lowers them run `--update-baseline` and commit the JSON diff.

CLI:
  python3 scripts/guards/check_n18_presentation_bilingual.py                # guard run
  python3 scripts/guards/check_n18_presentation_bilingual.py --update-baseline
  python3 scripts/guards/check_n18_presentation_bilingual.py --self-test    # fixture test (<2s)

Read-only scanner: never modifies scanned sources. Exit 0 pass / 1 violations.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MOBILE_LIB = REPO_ROOT / "mobile" / "lib"
FEATURES = MOBILE_LIB / "features"
BASELINE_PATH = Path(__file__).resolve().parent / "n18_presentation_bilingual_baseline.json"

# --- bilingual inline ternary scan -------------------------------------------

# zh-condition shapes measured in-repo; case-sensitive (lowercase zh family).
_COND = r"(?:\bzh|\b_isZh|\bisZh|languageCode\s*==\s*'zh')"
# Single-quoted Dart literal (no newline, backslash escapes allowed).
_STR = r"'(?:[^'\\\n]|\\.)*'"
_BILINGUAL_TERNARY = re.compile(_COND + r"\s*\?\s*" + _STR + r"\s*:\s*" + _STR)

_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*|///)")


def _code_text(text: str) -> str:
    """Drop comment-only lines so commented-out code cannot trip the scanner."""
    return "\n".join(ln for ln in text.splitlines() if not _COMMENT_RE.match(ln))


def scan_presentation(features_dir: Path) -> dict[str, int]:
    """presentation file -> bilingual inline ternary hit count."""
    out: dict[str, int] = {}
    for p in sorted(features_dir.rglob("*.dart")):
        rel = "mobile/lib/features/" + p.relative_to(features_dir).as_posix()
        if "/presentation/" not in rel:
            continue
        if p.name.endswith(".g.dart") or p.name.endswith(".freezed.dart"):
            continue
        code = _code_text(p.read_text(encoding="utf-8"))
        n = len(_BILINGUAL_TERNARY.findall(code))
        if n:
            out[rel] = n
    return out


def check(
    baseline: dict,
    current: dict[str, int],
) -> list[str]:
    violations: list[str] = []
    whitelist = {w["file"] for w in baseline.get("whitelist", [])}
    base_files = baseline.get("files", {})
    for file, n in sorted(current.items()):
        if file in whitelist:
            continue
        b = base_files.get(file)
        if b is None:
            violations.append(
                f"{file}: NEW presentation file carries {n} inline bilingual "
                "ternary/ies `zh ? '…' : '…'` (baseline: none — copy's single "
                "entry point is the arb files, SPEC §6.5 / v1.3 N18)"
            )
        elif n > b:
            violations.append(f"{file}: bilingual ternary count {n} > baseline {b} (+{n - b})")
    return violations


def _write_baseline(path: Path, current: dict[str, int], whitelist: list[dict]) -> None:
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_n18_presentation_bilingual.py "
            "(SPEC v1.3 N18: presentation inline bilingual ternary `zh ? '…' : '…'`). "
            "First registered from measured values at HEAD 835e91d7 (L10N-ZH card "
            "wt236, 2026-09-23): 152 hits / 26 files, regex caliber "
            "multiline-inclusive over the features/*/presentation root; the same "
            "card then migrated goal_detail_l10n.dart (34 ternaries) to arb and "
            "re-froze lower via --update-baseline. Only lower via --update-baseline "
            "after a cleanup batch; never raise. "
            "data/mock layers and core/ are outside the presentation scan root."
        ),
        "files": current,
        "whitelist": whitelist,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --- self-test (fixtures only; never touches the real tree/baseline) --------

def _self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        features = tmp / "features"
        pres = features / "sample" / "presentation"
        pres.mkdir(parents=True)
        (features / "sample" / "data").mkdir(parents=True)

        pres.joinpath("sample_screen.dart").write_text(
            "\n".join(
                [
                    "final zh = Localizations.localeOf(context).languageCode == 'zh';",
                    "// label: zh ? '注释里的命中' : 'commented hit'  <- must not count",
                    "label: zh ? '确认' : 'Confirm',",
                    "title: _isZh",
                    "    ? '目标详情'",
                    "    : 'Goal detail',",
                    "sep: Localizations.localeOf(context).languageCode == 'zh' ? '、' : ', ',",
                    "ignored: cond ? 'same lang' : 'also fine',",  # cond not zh-shaped
                    "vars: languageCode == 'zh' ? zh : en,",  # blind spot: no literals
                ]
            ),
            encoding="utf-8",
        )
        # data layer is outside the presentation scan root
        features.joinpath("sample/data/mock_repo.dart").write_text(
            "final x = zh ? '数据层双语' : 'data bilingual';\n", encoding="utf-8"
        )

        current = scan_presentation(features)
        want = {"mobile/lib/features/sample/presentation/sample_screen.dart": 3}
        if current != want:
            failures.append(f"scan mismatch: {current} != {want}")

        base = {
            "files": want,
            "whitelist": [],
        }
        if check(base, current):
            failures.append("clean baseline should pass")

        # violation: count raised + brand-new presentation file
        raised = dict(want)
        raised["mobile/lib/features/sample/presentation/sample_screen.dart"] = 5
        new_file = dict(want)
        new_file["mobile/lib/features/sample/presentation/other_screen.dart"] = 1
        v = check(base, raised) + check(base, new_file)
        if len(v) != 2:
            failures.append(f"expected 2 violations, got {len(v)}: {v}")

        # whitelist honors a registered domain aggregate file
        wl_base = {
            "files": {},
            "whitelist": [
                {
                    "file": "mobile/lib/features/sample/presentation/sample_screen.dart",
                    "reason": "registered aggregate, cleanup batch scheduled",
                }
            ],
        }
        if check(wl_base, current):
            failures.append("whitelisted file should not violate")

        # cleanup: file deleted / count lowered -> passes against frozen baseline
        pres.joinpath("sample_screen.dart").unlink()
        if check(base, scan_presentation(features)):
            failures.append("lowered/deleted counts should pass (ratchet only-down)")

    if failures:
        print("[n18-presentation-bilingual] SELF-TEST FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print(
        "[n18-presentation-bilingual] SELF-TEST PASS "
        "(scan zh/_isZh/languageCode== shapes + multiline; comment/data-layer/"
        "variable-branch exclusions; ratchet raise/new-file/whitelist/cleanup cases)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite baseline JSON from current counts (only after a cleanup batch LOWERED counts)",
    )
    parser.add_argument("--self-test", action="store_true", help="run fixture self-test in a temp dir")
    parser.add_argument("--baseline", type=Path, help="override baseline path (self-tests / fixtures only)")
    parser.add_argument("--features-dir", type=Path, help="override mobile/lib/features root (self-tests / fixtures only)")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    features_dir = args.features_dir or FEATURES
    baseline_path = args.baseline or BASELINE_PATH

    current = scan_presentation(features_dir)
    total = sum(current.values())

    if args.update_baseline:
        old = None
        if baseline_path.exists():
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
        whitelist = old.get("whitelist", []) if old else []
        _write_baseline(baseline_path, current, whitelist)
        old_total = sum(old.get("files", {}).values()) if old else None
        old_files = len(old.get("files", {})) if old else None
        print(
            f"[n18-presentation-bilingual] baseline updated: "
            f"{old_total} hits / {old_files} files -> {total} hits / {len(current)} files"
        )
        return 0

    if not baseline_path.exists():
        print(f"[n18-presentation-bilingual] FAIL — baseline missing: {baseline_path}")
        print(
            "  Register it from measured values: "
            "python3 scripts/guards/check_n18_presentation_bilingual.py --update-baseline"
        )
        return 1
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    violations = check(baseline, current)

    if violations:
        print(
            f"[n18-presentation-bilingual] FAIL — {len(violations)} N18 violation(s); "
            "presentation copy's single entry point is the arb files (SPEC §6.5, v1.3 N18): "
            "add zh/en keys and regenerate instead of inlining `zh ? '中文' : 'English'`"
        )
        for v in violations:
            print(f"  {v}")
        print(
            "\nAction: move the copy to mobile/lib/l10n/app_zh.arb + app_en.arb, run "
            "`cd mobile && flutter gen-l10n`, consume via l10n.<key>. If a cleanup batch "
            "legitimately LOWERED counts, refresh via:"
        )
        print("  python3 scripts/guards/check_n18_presentation_bilingual.py --update-baseline")
        return 1

    base_total = sum(baseline.get("files", {}).values())
    base_files = len(baseline.get("files", {}))
    print(
        f"[n18-presentation-bilingual] PASS — ratchet holds: "
        f"inline bilingual ternaries {total}/{base_total} "
        f"({len(current)}/{base_files} presentation files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
