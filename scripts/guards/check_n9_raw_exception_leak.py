#!/usr/bin/env python3
r"""N9 raw-exception leak guard — block the arb `{error}` escape channel (SPEC v1.2 N9).

A-SPEC2 (v3-output/A-SPEC2/REPORT.md §0/#2) found that SPEC v1.1 N4 only
banned raw-exception INTERPOLATION inside Dart code (`'$_loadError'`), while
new code started passing raw `Object error` as an **arb placeholder
argument** (`squadLoadFailed(error)` -> zh template 「加载失败：{error}」).
Error-copy became the legal front door for bare exceptions and the existing
guard pattern was blind to it.

This guard ratchets BOTH dimensions (per SPEC v1.2 N9 机检双维):

- dim 1 `arbErrorPlaceholder`: every template entry in `mobile/lib/l10n/*.arb`
  containing the exact `{error}` placeholder token is pinned per (file, key)
  in the baseline. A NEW entry carrying `{error}`, or an existing entry whose
  count goes UP, fails. Cleanup batches lower counts via `--update-baseline`.

- dim 2 `rawExceptionArg`: call sites in `mobile/lib/**` that pass a raw
  catch variable (named error/err/ex/e/exception/failure) or its
  `.toString()` result as an l10n call argument
  (`context.l10n.xxxFailed(error)` / `l10n.xxxFailed(e.toString())`),
  detected via balanced-paren argument inspection of `\bl10n.\w+(` calls.
  NEW files with any hit fail; per-file per-kind counts may only go down.

Generated files (`*.g.dart`, `app_localizations*`) are excluded: they are
regenerated from the arb source of truth (never hand-edited).

Baseline: `n9_raw_exception_leak_baseline.json`, registered from measured
values at HEAD a025e82a (GUARDS card wt227, 2026-09-23). Counts may only go
down (ratchet); after a cleanup batch lowers them run `--update-baseline` and
commit the JSON diff.

CLI:
  python3 scripts/guards/check_n9_raw_exception_leak.py                # guard run
  python3 scripts/guards/check_n9_raw_exception_leak.py --update-baseline
  python3 scripts/guards/check_n9_raw_exception_leak.py --self-test    # fixture test (<2s)

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
ARB_DIR = MOBILE_LIB / "l10n"
BASELINE_PATH = Path(__file__).resolve().parent / "n9_raw_exception_leak_baseline.json"

# --- dim 1: arb {error} placeholder ratchet ---------------------------------

# Exact placeholder token, not {errorType}/{errorCount}/{errors} etc.
_ARB_ERROR_TOKEN = re.compile(r"\{error\}")

# --- dim 2: raw-exception l10n argument scan --------------------------------

# Receiver: `l10n.` (covers `context.l10n.x(`, local `final l10n = ...` aliases,
# `I18nService.instance.l10n.x(`). Direct `AppLocalizations.of(context)!.x(`
# call form does not occur in this repo (measured @a025e82a).
_L10N_CALL = re.compile(r"\bl10n\.(\w+)\s*\(")

# Catch-variable names observed in this repo (78x `catch (error)`,
# 16x `catch (error, stackTrace)`, plus `(e)`). A new exotic name would be a
# renaming evasion; ratchet intent follows SPEC N9's `(<catch 变量>)` notation.
_CATCH_NAME = r"(?:error|err|ex|e|exception|failure)"
_BARE_CATCH_ARG = re.compile(r"(?:\(|,)\s*" + _CATCH_NAME + r"\s*(?=[,)])")
_CATCH_TOSTRING = re.compile(r"\b" + _CATCH_NAME + r"\s*\.\s*toString\s*\(\s*\)")

_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*|///)")
_KINDS = ("bareCatchVar", "catchVarToString")


def _code_text(text: str) -> str:
    """Drop comment-only lines so commented-out code cannot trip the scanner."""
    return "\n".join(ln for ln in text.splitlines() if not _COMMENT_RE.match(ln))


def _balanced_arg(text: str, open_paren: int) -> str:
    """Return the argument region of a call whose `(` sits at open_paren."""
    depth = 0
    for i in range(open_paren, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren : i + 1]
    return text[open_paren : open_paren + 200]  # unbalanced (truncated file)


def scan_arb(arb_dir: Path) -> dict[str, dict[str, int]]:
    """file -> {template key: {error} occurrence count} for keys carrying it."""
    out: dict[str, dict[str, int]] = {}
    for p in sorted(arb_dir.glob("*.arb")):
        data = json.loads(p.read_text(encoding="utf-8"))
        hits = {
            key: len(_ARB_ERROR_TOKEN.findall(val))
            for key, val in data.items()
            if not key.startswith("@") and isinstance(val, str)
            if _ARB_ERROR_TOKEN.search(val)
        }
        if hits:
            out["mobile/lib/l10n/" + p.name] = hits
    return out


def scan_call_sites(mobile_lib: Path) -> dict[str, dict[str, int]]:
    """file -> {kind: hit count} for raw-exception l10n arguments."""
    out: dict[str, dict[str, int]] = {}
    for p in sorted(mobile_lib.rglob("*.dart")):
        if p.name.endswith(".g.dart") or p.name.startswith("app_localizations"):
            continue
        code = _code_text(p.read_text(encoding="utf-8"))
        counts = {"bareCatchVar": 0, "catchVarToString": 0}
        for m in _L10N_CALL.finditer(code):
            arg = _balanced_arg(code, m.end() - 1)
            if _BARE_CATCH_ARG.search(arg):
                counts["bareCatchVar"] += 1
            if _CATCH_TOSTRING.search(arg):
                counts["catchVarToString"] += 1
        if any(counts.values()):
            out["mobile/lib/" + p.relative_to(mobile_lib).as_posix()] = counts
    return out


def _totals_arb(arb: dict[str, dict[str, int]]) -> tuple[int, int]:
    entries = sum(len(v) for v in arb.values())
    occ = sum(n for v in arb.values() for n in v.values())
    return entries, occ


def _totals_calls(calls: dict[str, dict[str, int]]) -> dict[str, int]:
    return {k: sum(c.get(k, 0) for c in calls.values()) for k in _KINDS}


def check(
    baseline: dict,
    arb: dict[str, dict[str, int]],
    calls: dict[str, dict[str, int]],
) -> list[str]:
    violations: list[str] = []
    base_arb = baseline.get("arb", {})
    for file, hits in sorted(arb.items()):
        base_file = base_arb.get(file, {})
        for key, n in hits.items():
            b = base_file.get(key)
            if b is None:
                violations.append(f"{file}: NEW arb entry `{key}` carries {{error}} x{n}")
            elif n > b:
                violations.append(f"{file}: `{key}` {{error}} count {n} > baseline {b}")
    base_calls = baseline.get("callSites", {})
    for file, counts in sorted(calls.items()):
        b = base_calls.get(file)
        if b is None:
            summary = ", ".join(f"{k}={counts[k]}" for k in _KINDS if counts.get(k))
            violations.append(
                f"NEW FILE {file}: raw-exception l10n args ({summary}) "
                "(baseline: none — error copy must be human-phrased, exception detail goes to logs)"
            )
            continue
        for kind in _KINDS:
            now, base = counts.get(kind, 0), b.get(kind, 0)
            if now > base:
                violations.append(f"{file}: {kind} {now} > baseline {base} (+{now - base})")
    return violations


def _write_baseline(path: Path, arb: dict, calls: dict) -> None:
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_n9_raw_exception_leak.py "
            "(SPEC v1.2 N9: arb {error} placeholder + raw-exception l10n call args). "
            "Registered from measured values at HEAD a025e82a (GUARDS card wt227, 2026-09-23). "
            "Only lower via --update-baseline after a cleanup batch; never raise. "
            "arb edits additionally follow the §6.5-4 serial arb window discipline."
        ),
        "arb": arb,
        "callSites": calls,
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
        arb_dir = tmp / "l10n"
        lib = tmp / "lib"
        arb_dir.mkdir()
        (lib / "features").mkdir(parents=True)

        arb_payload = {"okKey": "好了", "planCreateFailed": "创建计划失败: {error}"}
        (arb_dir / "app_zh.arb").write_text(json.dumps(arb_payload, ensure_ascii=False), encoding="utf-8")
        dart = [
            "void f() {",
            "  // l10n.xFailed(error)  <- commented-out hits must not count",
            "  _show(context.l10n.planCreateFailed(error));",
            "  _show(context.l10n.detail(e.toString()));",
            "  _show(context.l10n.reviewCount(error.reviewCount));  // model field: legal",
            "  _show(context.l10n.multi(",
            "      scope, err));  // non-first arg position",
            "}",
        ]
        (lib / "features" / "sample_screen.dart").write_text("\n".join(dart), encoding="utf-8")

        arb = scan_arb(arb_dir)
        calls = scan_call_sites(lib)

        if arb != {"mobile/lib/l10n/app_zh.arb": {"planCreateFailed": 1}}:
            failures.append(f"arb scan mismatch: {arb}")
        want = {"mobile/lib/features/sample_screen.dart": {"bareCatchVar": 2, "catchVarToString": 1}}
        if calls != want:
            failures.append(f"call-site scan mismatch: {calls} != {want}")

        base = {
            "arb": {"mobile/lib/l10n/app_zh.arb": {"planCreateFailed": 1}},
            "callSites": want,
        }
        if check(base, arb, calls):
            failures.append("clean baseline should pass")

        # violation: arb count raised + new arb key + call-site raise + new file
        arb2 = {"mobile/lib/l10n/app_zh.arb": {"planCreateFailed": 2, "newFailed": 1}}
        calls2 = {
            "mobile/lib/features/sample_screen.dart": {"bareCatchVar": 4, "catchVarToString": 1},
            "mobile/lib/features/other_screen.dart": {"bareCatchVar": 1, "catchVarToString": 0},
        }
        v = check(base, arb2, calls2)
        if len(v) != 4:
            failures.append(f"expected 4 violations, got {len(v)}: {v}")

        # cleanup: {error} removed from template -> passes against frozen baseline
        (arb_dir / "app_zh.arb").write_text(
            json.dumps({"okKey": "好了", "planCreateFailed": "创建计划失败，你的数据没有丢"}, ensure_ascii=False),
            encoding="utf-8",
        )
        if check(base, scan_arb(arb_dir), calls):
            failures.append("lowered counts should pass (ratchet only-down)")

    if failures:
        print("[n9-raw-exception-leak] SELF-TEST FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print("[n9-raw-exception-leak] SELF-TEST PASS "
          "(arb ratchet + call-face ratchet: catch/clean/lower/new-file/comment cases)")
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
    parser.add_argument("--arb-dir", type=Path, help="override arb dir (self-tests / fixtures only)")
    parser.add_argument("--mobile-lib", type=Path, help="override mobile/lib root (self-tests / fixtures only)")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    arb_dir = args.arb_dir or ARB_DIR
    mobile_lib = args.mobile_lib or MOBILE_LIB
    baseline_path = args.baseline or BASELINE_PATH

    arb = scan_arb(arb_dir)
    calls = scan_call_sites(mobile_lib)
    arb_entries, arb_occ = _totals_arb(arb)
    call_totals = _totals_calls(calls)

    if args.update_baseline:
        old = None
        if baseline_path.exists():
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
        _write_baseline(baseline_path, arb, calls)
        old_calls = _totals_calls(old.get("callSites", {})) if old else None
        old_arb = _totals_arb(old.get("arb", {})) if old else None
        arrow = (
            f"arb {old_arb} -> ({arb_entries}, {arb_occ}); calls {old_calls} -> {call_totals}"
            if old
            else f"arb ({arb_entries}, {arb_occ}); calls {call_totals}"
        )
        print(f"[n9-raw-exception-leak] baseline updated: {arrow}")
        return 0

    if not baseline_path.exists():
        print(f"[n9-raw-exception-leak] FAIL — baseline missing: {baseline_path}")
        print("  Register it from measured values: python3 scripts/guards/check_n9_raw_exception_leak.py --update-baseline")
        return 1
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    violations = check(baseline, arb, calls)

    if violations:
        print(
            f"[n9-raw-exception-leak] FAIL — {len(violations)} N9 violation(s); "
            "error copy must be human-phrased (what happened + impact + retry), "
            "exception detail goes to logs — never into arb {error} templates or l10n args (SPEC v1.2 N9)"
        )
        for v in violations:
            print(f"  {v}")
        print(
            "\nAction: phrase the error template in human language and log the raw object "
            "(debugPrint/report). If a cleanup batch legitimately LOWERED counts, refresh via:"
        )
        print("  python3 scripts/guards/check_n9_raw_exception_leak.py --update-baseline")
        return 1

    base_arb_entries, base_arb_occ = _totals_arb(baseline.get("arb", {}))
    base_calls = _totals_calls(baseline.get("callSites", {}))
    print(
        f"[n9-raw-exception-leak] PASS — ratchet holds: "
        f"arb {{error}} entries {arb_entries}/{base_arb_entries} "
        f"(occurrences {arb_occ}/{base_arb_occ}), "
        f"call sites bareCatchVar={call_totals['bareCatchVar']}/{base_calls['bareCatchVar']}, "
        f"catchVarToString={call_totals['catchVarToString']}/{base_calls['catchVarToString']} "
        f"({len(arb)} arb files, {len(calls)} files with call sites)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
