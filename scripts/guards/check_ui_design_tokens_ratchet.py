#!/usr/bin/env python3
"""UI design-token ratchet guard — block NEW hardcoded colors / font sizes.

Ratchet pattern (round2 review 07 §3.4, batch 0): scan `mobile/lib/features/**`
for hardcoded `Color(0x…)` literals and numeric-literal `fontSize:` usages
(`fontSize: 13`; token usages like `fontSize: DS.fontSizeSm` are NOT counted).
Counts are pinned per-file against a frozen baseline
(`ui_design_tokens_baseline.json`, generated at ca86bda8):

- a file exceeding its baseline count, or a NEW file with any violation, fails;
- counts may only go down (ratchet). To lower the baseline after a burn batch,
  run with `--update-baseline` and commit the JSON diff.

Exit 0 on pass, 1 on violations found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "mobile" / "lib" / "features"
BASELINE_PATH = Path(__file__).resolve().parent / "ui_design_tokens_baseline.json"

_COLOR_RE = re.compile(r"Color\(0x")
_FONTSIZE_RE = re.compile(r"fontSize:\s*[0-9]")

# token-style font size (already design-system) — kept for documentation only;
# the numeric-literal regex above already excludes these.


def _code_lines(text: str) -> list[str]:
    """Drop comment-only lines so comments cannot trip the counter."""
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        out.append(line)
    return out


def count_file(path: Path) -> dict[str, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"color": 0, "fontSize": 0}
    color = sum(len(_COLOR_RE.findall(line)) for line in _code_lines(text))
    fontSize = sum(len(_FONTSIZE_RE.findall(line)) for line in _code_lines(text))
    return {"color": color, "fontSize": fontSize}


def scan_all() -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for path in sorted(SCAN_ROOT.rglob("*.dart")):
        rel = "mobile/lib/features/" + path.relative_to(SCAN_ROOT).as_posix()
        c = count_file(path)
        if c["color"] or c["fontSize"]:
            counts[rel] = c
    return counts


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    return {
        "color": sum(c["color"] for c in counts.values()),
        "fontSize": sum(c["fontSize"] for c in counts.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the baseline JSON from current counts (use after a burn batch lowers counts)",
    )
    args = parser.parse_args()

    if not SCAN_ROOT.exists():
        print(f"[ui-tokens-ratchet] SKIP — {SCAN_ROOT} not found")
        return 0

    current = scan_all()
    current_totals = totals(current)

    if args.update_baseline:
        old_totals = None
        if BASELINE_PATH.exists():
            old = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
            old_totals = totals(old.get("files", {}))
        payload = {
            "comment": (
                "Frozen ratchet baseline for check_ui_design_tokens_ratchet.py. "
                "Only lower via --update-baseline after removing hardcoded tokens; "
                "never raise. Generated at ca86bda8."
            ),
            "files": current,
        }
        BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        arrow = f"{old_totals} -> " if old_totals else ""
        print(f"[ui-tokens-ratchet] baseline updated: {arrow}{current_totals} "
              f"({len(current)} files)")
        return 0

    if not BASELINE_PATH.exists():
        print(f"[ui-tokens-ratchet] FAIL — baseline missing: {BASELINE_PATH}")
        return 1
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8")).get("files", {})
    baseline_totals = totals(baseline)

    violations: list[str] = []
    for rel, c in sorted(current.items()):
        b = baseline.get(rel)
        if b is None:
            violations.append(f"NEW FILE {rel}: color={c['color']} fontSize={c['fontSize']} (baseline: none)")
            continue
        if c["color"] > b.get("color", 0):
            violations.append(
                f"{rel}: color {c['color']} > baseline {b.get('color', 0)} (+{c['color'] - b.get('color', 0)})"
            )
        if c["fontSize"] > b.get("fontSize", 0):
            violations.append(
                f"{rel}: fontSize {c['fontSize']} > baseline {b.get('fontSize', 0)} "
                f"(+{c['fontSize'] - b.get('fontSize', 0)})"
            )

    if violations:
        print(f"[ui-tokens-ratchet] FAIL — {len(violations)} ratchet violation(s); "
              f"hardcoded UI tokens may only decrease")
        for v in violations:
            print(f"  {v}")
        print("\nAction: use core/design tokens (see docs/engineering + mobile/lib/core/design/). "
              "If a burn batch legitimately LOWERED counts, refresh baseline via:")
        print("  python3 scripts/guards/check_ui_design_tokens_ratchet.py --update-baseline")
        return 1

    print(
        f"[ui-tokens-ratchet] PASS — ratchet holds at "
        f"color={current_totals['color']}/{baseline_totals['color']}, "
        f"fontSize={current_totals['fontSize']}/{baseline_totals['fontSize']} "
        f"({len(current)} files with hardcoded tokens)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
