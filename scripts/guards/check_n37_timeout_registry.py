#!/usr/bin/env python3
r"""N37 timeout registry guard — every network timeout must cite ApiTimeouts.

A-SPEC6 面2 差距③ (v3-output/A-SPEC6/REPORT.md OF-G5) found Dio timeouts
hard-coded as bare `Duration(...)` literals at four self-standing sites
(global ApiClient, auth-retry Dio, the three statistics providers, plus a
dead 30/30/30 block in ApiConstants) with no single source of truth. The
TIMEOUT-SOURCE card (wt258) consolidated them into
`mobile/lib/core/network/api_timeouts.dart` (`ApiTimeouts`, value-preserving)
and instituted the N37 registration regime.

This guard ratchets TWO dimensions (baseline frozen at the post-consolidation
tree; counts may only go down):

- dim 1 `dioTimeoutArgLiterals`: bare `Duration(...)` literals passed to Dio
  timeout named arguments (`connectTimeout:` / `receiveTimeout:` /
  `sendTimeout:`) anywhere in `mobile/lib/**` — covers both `BaseOptions(...)`
  constructions and per-request `Options(...)` overrides. The ONLY legal home
  for such literals is `core/network/api_timeouts.dart` (exempted: it is the
  registered registry). A NEW site fails with the registration instruction.

- dim 2 `networkLayerTimeoutLiterals`: bare `Duration(...)` literals in
  timeout context (`.timeout(const Duration(...))` future guards or
  `timeout:` named arguments) inside `mobile/lib/core/network/*.dart`
  (registry file exempted). New network-layer timeout logic must reference
  or register in ApiTimeouts — not grow fresh literals.

- dim 3 `nullTimeoutOverrideLiterals` (WT273 audit, freezes the dio-compose
  trap): `(connectTimeout|receiveTimeout|sendTimeout): null` anywhere in
  `mobile/lib/**`. dio 5.9.0 `Options.compose` merges per-request overrides
  as `perRequest ?? baseOptions.<slot>` — an explicit `null` SILENTLY FALLS
  BACK to the global default, so `null` is an invalid way to express "turn
  this timeout off" (the galaxy SSE precedent: a null exemption masked as a
  fix until A11Y-BATCH2 proved it inert). The only legal "off" is
  `ApiTimeouts.sseReceiveTimeout` (Duration.zero — dio skips the receive
  watchdog for zero values). Baseline frozen at zero; any re-introduction fails.

- dim 4 `unboundedHttpPackageCalls` (WT273 audit): `package:http` verb calls
  (`http.get(`/`http.post(`/... under the conventional `as http` alias)
  whose enclosing statement carries NO `.timeout(` — the dart http package
  has NO default timeout, so such a call pends forever on a stalled
  connection (found live on three share-card download faces + the chaos
  admin dialog; all fixed by citing registered ApiTimeouts constants).
  Statement window = from the call's opening paren, tracking paren depth,
  to the first `;` at depth 0 (2000-char defensive cap). Baseline frozen at
  zero: every future http-package call site must carry an explicit,
  registry-cited `.timeout(...)`.

Not in scope (registered in the api_timeouts.dart header table instead,
migration on touch): feature-layer functional timeouts — gRPC per-call
`timeout:`, ws heartbeat/reconnect backoff tables, chat stream total-cap and
first-event guards, sync ACK waits, health-probe futures outside core/network.

Generated files (`*.g.dart`, `app_localizations*`) are excluded: they are
regenerated from the proto/arb sources of truth (never hand-edited).
Commented-out lines are ignored (same `_code_text` discipline as the N9
guard family).

Baseline: `n37_timeout_registry_baseline.json` — frozen at {} / {} measured
at the post-consolidation tree of HEAD 04904b54 (TIMEOUT-SOURCE card wt258,
2026-09); both dimensions start at zero, so ANY new bare literal fails.
After a legitimate cleanup that LOWERS a count, refresh via
`--update-baseline` and commit the JSON diff; never raise.

CLI:
  python3 scripts/guards/check_n37_timeout_registry.py                # guard run
  python3 scripts/guards/check_n37_timeout_registry.py --update-baseline
  python3 scripts/guards/check_n37_timeout_registry.py --self-test    # fixture test (<2s)

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
REGISTRY_REL = "mobile/lib/core/network/api_timeouts.dart"
BASELINE_PATH = Path(__file__).resolve().parent / "n37_timeout_registry_baseline.json"

# --- dim 1: bare Duration literals on Dio timeout named args -----------------

_DIO_TIMEOUT_ARG = re.compile(
    r"\b(connectTimeout|receiveTimeout|sendTimeout)\s*:\s*"
    r"(?:const\s+)?Duration\s*\("
)

# --- dim 2: bare timeout-context Duration literals in core/network ----------

_TIMEOUT_CONTEXT = re.compile(
    r"(?:\.timeout\s*\(\s*(?:const\s+)?Duration\s*\()"
    r"|(?:\btimeout:\s*(?:const\s+)?Duration\s*\()"
)

# --- dim 3: explicit null overrides on Dio timeout named args (dio-compose
#     fallback trap: null silently reverts to the global default) ------------

_NULL_TIMEOUT_OVERRIDE = re.compile(
    r"\b(connectTimeout|receiveTimeout|sendTimeout)\s*:\s*null\b"
)

# --- dim 4: package:http verb calls with no .timeout( in their statement ----

_HTTP_PACKAGE_CALL = re.compile(
    r"\bhttp\.(?:get|post|put|delete|patch|head|read|readBytes)\s*\("
)

_HTTP_WINDOW_CAP = 2000  # defensive cap for pathological unterminated windows

_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*|///)")

_GENERATED = ("*.g.dart", "app_localizations")


def _is_generated(p: Path) -> bool:
    return p.name.endswith(".g.dart") or p.name.startswith("app_localizations")


def _code_text(text: str) -> str:
    """Drop comment-only lines so commented-out code cannot trip the scanner."""
    return "\n".join(ln for ln in text.splitlines() if not _COMMENT_RE.match(ln))


def _scan(mobile_lib: Path, pattern: re.Pattern[str], root_label: str,
          allowed_rel: set[str], files: list[Path]) -> dict[str, int]:
    """file -> hit count for `pattern`, skipping generated/allowed files."""
    out: dict[str, int] = {}
    for p in sorted(files):
        rel = root_label + p.relative_to(mobile_lib).as_posix()
        if _is_generated(p) or rel in allowed_rel:
            continue
        n = len(pattern.findall(_code_text(p.read_text(encoding="utf-8"))))
        if n:
            out[rel] = n
    return out


def scan_dio_timeout_args(mobile_lib: Path) -> dict[str, int]:
    """dim 1: bare Duration literals on Dio timeout named args, mobile/lib."""
    files = [p for p in mobile_lib.rglob("*.dart")]
    return _scan(mobile_lib, _DIO_TIMEOUT_ARG, "mobile/lib/", {REGISTRY_REL}, files)


def scan_network_layer(mobile_lib: Path) -> dict[str, int]:
    """dim 2: bare timeout-context Duration literals in core/network."""
    files = list((mobile_lib / "core" / "network").glob("*.dart"))
    return _scan(mobile_lib, _TIMEOUT_CONTEXT, "mobile/lib/", {REGISTRY_REL}, files)


def _count_unbounded_http(text: str) -> int:
    """dim 4 core: http-package calls lacking `.timeout(` in their statement.

    Statement window: from the call's opening paren, tracking paren depth,
    to the first `;` at depth 0 (capped at _HTTP_WINDOW_CAP chars).
    """
    hits = 0
    for m in _HTTP_PACKAGE_CALL.finditer(text):
        depth = 0
        j = m.end() - 1  # index of the call's opening paren
        end = min(len(text), j + _HTTP_WINDOW_CAP)
        while j < end:
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == ";" and depth <= 0:
                break
            j += 1
        if ".timeout" not in text[m.start():j]:
            hits += 1
    return hits


def scan_null_overrides(mobile_lib: Path) -> dict[str, int]:
    """dim 3: explicit null overrides on Dio timeout named args, mobile/lib."""
    files = [p for p in mobile_lib.rglob("*.dart")]
    return _scan(mobile_lib, _NULL_TIMEOUT_OVERRIDE, "mobile/lib/", {REGISTRY_REL}, files)


def scan_unbounded_http_calls(mobile_lib: Path) -> dict[str, int]:
    """dim 4: package:http verb calls without a statement-level .timeout(."""
    out: dict[str, int] = {}
    for p in sorted(mobile_lib.rglob("*.dart")):
        rel = "mobile/lib/" + p.relative_to(mobile_lib).as_posix()
        if _is_generated(p):
            continue
        n = _count_unbounded_http(_code_text(p.read_text(encoding="utf-8")))
        if n:
            out[rel] = n
    return out


def check(baseline: dict, dio_args: dict[str, int], net_layer: dict[str, int],
          null_overrides: dict[str, int] | None = None,
          unbounded_http: dict[str, int] | None = None) -> list[str]:
    violations: list[str] = []
    null_overrides = null_overrides or {}
    unbounded_http = unbounded_http or {}
    for file, n in sorted(dio_args.items()):
        b = baseline.get("dioTimeoutArgLiterals", {}).get(file)
        if b is None:
            violations.append(
                f"{file}: bare Dio timeout literal x{n} — register in "
                "core/network/api_timeouts.dart (ApiTimeouts, N37: 命名 "
                "<face><Slot>Timeout + 更新登记表) and reference the constant"
            )
        elif n > b:
            violations.append(f"{file}: dioTimeoutArgLiterals {n} > baseline {b}")
    for file, n in sorted(net_layer.items()):
        b = baseline.get("networkLayerTimeoutLiterals", {}).get(file)
        if b is None:
            violations.append(
                f"{file}: bare timeout-context Duration literal x{n} in "
                "core/network — cite ApiTimeouts or register a new constant "
                "(N37 登记制)"
            )
        elif n > b:
            violations.append(f"{file}: networkLayerTimeoutLiterals {n} > baseline {b}")
    for file, n in sorted(null_overrides.items()):
        violations.append(
            f"{file}: null timeout override x{n} — dio Options.compose merges "
            "`perRequest ?? baseOptions`: explicit null SILENTLY FALLS BACK to "
            "the global default (galaxy SSE precedent, judged inert by "
            "A11Y-BATCH2). To turn a request-level timeout OFF use "
            "ApiTimeouts.sseReceiveTimeout (Duration.zero); to change a value "
            "register a constant in api_timeouts.dart. Never write `: null`."
        )
    for file, n in sorted(unbounded_http.items()):
        violations.append(
            f"{file}: package:http call without .timeout( x{n} — the dart "
            "http package has NO default timeout, so the future pends forever "
            "on a stalled connection (WT273 audit defect class). Add "
            "`.timeout(<ApiTimeouts constant>)` — register the face in "
            "core/network/api_timeouts.dart first (N37 登记制)."
        )
    return violations


def _write_baseline(path: Path, dio_args: dict, net_layer: dict,
                    null_overrides: dict, unbounded_http: dict) -> None:
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_n37_timeout_registry.py "
            "(SPEC N37 弱网参数登记制, TIMEOUT-SOURCE card wt258 @ HEAD 04904b54; "
            "dims 3-4 added by WT273 audit). dioTimeoutArgLiterals = bare "
            "Duration literals on Dio connect/receive/sendTimeout named args "
            "outside core/network/api_timeouts.dart; networkLayerTimeoutLiterals "
            "= bare timeout-context Duration literals in core/network outside "
            "the registry; nullTimeoutOverrideLiterals = `connect/receive/"
            "sendTimeout: null` anywhere (dio Options.compose silently falls "
            "back to the global default — the A11Y-BATCH2 inert-exemption "
            "trap); unboundedHttpPackageCalls = package:http verb calls with "
            "no statement-level .timeout( (dart http has no default timeout). "
            "Registered at ZERO: any NEW hit violates; counts may only go "
            "down via --update-baseline after a legitimate cleanup. Never raise."
        ),
        "dioTimeoutArgLiterals": dio_args,
        "networkLayerTimeoutLiterals": net_layer,
        "nullTimeoutOverrideLiterals": null_overrides,
        "unboundedHttpPackageCalls": unbounded_http,
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
        lib = tmp / "lib"
        (lib / "core" / "network").mkdir(parents=True)
        (lib / "features" / "x").mkdir(parents=True)

        registry = lib / "core" / "network" / "api_timeouts.dart"
        registry.write_text(
            "class ApiTimeouts {\n"
            "  static const Duration defaultConnectTimeout = Duration(seconds: 10);\n"
            "  static const Duration? sseReceiveTimeout = null;\n"
            "}\n",
            encoding="utf-8",
        )

        # clean site: references the registry constants
        (lib / "features" / "x" / "clean.dart").write_text(
            "BaseOptions(connectTimeout: ApiTimeouts.defaultConnectTimeout, "
            "receiveTimeout: ApiTimeouts.defaultReceiveTimeout)\n"
            "Options(receiveTimeout: ApiTimeouts.sseReceiveTimeout)\n"
            "// receiveTimeout: const Duration(seconds: 30) <- comment ignored\n"
            "final r = await http.get(Uri.parse('https://x'))\n"
            "    .timeout(const Duration(seconds: 3));  // statement-bounded\n"
            "// http.post(Uri.parse('https://y'));  <- comment ignored\n",
            encoding="utf-8",
        )
        # violating sites
        (lib / "features" / "x" / "dirty.dart").write_text(
            "BaseOptions(connectTimeout: const Duration(seconds: 10))\n"
            "Options(sendTimeout: Duration(minutes: 1))\n"
            "Options(receiveTimeout: null)  // dio-compose fallback trap\n"
            "await http.post(Uri.parse('https://x'), body: 'x');\n"
            "final big = await http.get(Uri.parse('https://y/z'));\n",
            encoding="utf-8",
        )
        (lib / "core" / "network" / "dirty_net.dart").write_text(
            "channel.ready.timeout(const Duration(seconds: 10));\n"
            "await f(timeout: Duration(seconds: 5));\n"
            "// .timeout(const Duration(seconds: 1)) <- comment ignored\n"
            "final expiry = DateTime.now().add(const Duration(seconds: 30));  // not timeout context\n",
            encoding="utf-8",
        )

        dio_args = scan_dio_timeout_args(lib)
        net_layer = scan_network_layer(lib)
        null_overrides = scan_null_overrides(lib)
        unbounded_http = scan_unbounded_http_calls(lib)
        want_dio = {"mobile/lib/features/x/dirty.dart": 2}
        want_net = {"mobile/lib/core/network/dirty_net.dart": 2}
        want_null = {"mobile/lib/features/x/dirty.dart": 1}
        want_http = {"mobile/lib/features/x/dirty.dart": 2}
        if dio_args != want_dio:
            failures.append(f"dim1 scan mismatch: {dio_args} != {want_dio}")
        if net_layer != want_net:
            failures.append(f"dim2 scan mismatch: {net_layer} != {want_net}")
        if null_overrides != want_null:
            failures.append(f"dim3 scan mismatch: {null_overrides} != {want_null}")
        if unbounded_http != want_http:
            failures.append(f"dim4 scan mismatch: {unbounded_http} != {want_http}")

        empty = {
            "dioTimeoutArgLiterals": {},
            "networkLayerTimeoutLiterals": {},
            "nullTimeoutOverrideLiterals": {},
            "unboundedHttpPackageCalls": {},
        }
        v = check(empty, dio_args, net_layer, null_overrides, unbounded_http)
        if len(v) != 4:
            failures.append(f"expected 4 violations vs empty baseline, got {len(v)}: {v}")

        # ratchet: lower passes, raise fails
        base_raised = {
            "dioTimeoutArgLiterals": {"mobile/lib/features/x/dirty.dart": 3},
            "networkLayerTimeoutLiterals": {"mobile/lib/core/network/dirty_net.dart": 1},
        }
        v = check(base_raised, dio_args, net_layer)
        if len(v) != 1 or "networkLayerTimeoutLiterals 2 > baseline 1" not in v[0]:
            failures.append(f"ratchet raise case mismatch: {v}")

    if failures:
        print("[n37-timeout-registry] SELF-TEST FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print("[n37-timeout-registry] SELF-TEST PASS "
          "(dio-arg ratchet + network-layer ratchet + null-override trap + "
          "unbounded-http-package statement window: clean/dirty/comment/"
          "registry-exempt/expiry-buffer/lower/raise cases)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite baseline JSON from current counts (only after a cleanup LOWERED counts)",
    )
    parser.add_argument("--self-test", action="store_true", help="run fixture self-test in a temp dir")
    parser.add_argument("--baseline", type=Path, help="override baseline path (self-tests / fixtures only)")
    parser.add_argument("--mobile-lib", type=Path, help="override mobile/lib root (self-tests / fixtures only)")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    mobile_lib = args.mobile_lib or MOBILE_LIB
    baseline_path = args.baseline or BASELINE_PATH

    dio_args = scan_dio_timeout_args(mobile_lib)
    net_layer = scan_network_layer(mobile_lib)
    null_overrides = scan_null_overrides(mobile_lib)
    unbounded_http = scan_unbounded_http_calls(mobile_lib)

    if args.update_baseline:
        old = None
        if baseline_path.exists():
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
        _write_baseline(baseline_path, dio_args, net_layer, null_overrides,
                        unbounded_http)
        old_dio = sum(old.get("dioTimeoutArgLiterals", {}).values()) if old else None
        old_net = sum(old.get("networkLayerTimeoutLiterals", {}).values()) if old else None
        old_null = sum(old.get("nullTimeoutOverrideLiterals", {}).values()) if old else None
        old_http = sum(old.get("unboundedHttpPackageCalls", {}).values()) if old else None
        print(
            f"[n37-timeout-registry] baseline updated: "
            f"dioTimeoutArgLiterals {old_dio} -> {sum(dio_args.values())}; "
            f"networkLayerTimeoutLiterals {old_net} -> {sum(net_layer.values())}; "
            f"nullTimeoutOverrideLiterals {old_null} -> {sum(null_overrides.values())}; "
            f"unboundedHttpPackageCalls {old_http} -> {sum(unbounded_http.values())}"
        )
        return 0

    if not baseline_path.exists():
        print(f"[n37-timeout-registry] FAIL — baseline missing: {baseline_path}")
        print("  Register it from measured values: python3 scripts/guards/check_n37_timeout_registry.py --update-baseline")
        return 1
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    violations = check(baseline, dio_args, net_layer, null_overrides, unbounded_http)

    if violations:
        print(
            f"[n37-timeout-registry] FAIL — {len(violations)} N37 violation(s); "
            "network timeouts have a single source of truth: "
            "core/network/api_timeouts.dart (ApiTimeouts). Register new faces "
            "there (命名 <face><Slot>Timeout + 更新文件头登记表) and reference "
            "the constants — never write bare Duration literals on "
            "connect/receive/sendTimeout args or as .timeout()/timeout: values "
            "in core/network."
        )
        for v in violations:
            print(f"  {v}")
        print(
            "\nAction: cite ApiTimeouts constants (e.g. "
            "ApiTimeouts.defaultConnectTimeout). If a cleanup batch "
            "legitimately LOWERED counts, refresh via:"
        )
        print("  python3 scripts/guards/check_n37_timeout_registry.py --update-baseline")
        return 1

    base_dio = sum(baseline.get("dioTimeoutArgLiterals", {}).values())
    base_net = sum(baseline.get("networkLayerTimeoutLiterals", {}).values())
    base_null = sum(baseline.get("nullTimeoutOverrideLiterals", {}).values())
    base_http = sum(baseline.get("unboundedHttpPackageCalls", {}).values())
    print(
        f"[n37-timeout-registry] PASS — ratchet holds: "
        f"dioTimeoutArgLiterals {sum(dio_args.values())}/{base_dio}, "
        f"networkLayerTimeoutLiterals {sum(net_layer.values())}/{base_net}, "
        f"nullTimeoutOverrideLiterals {sum(null_overrides.values())}/{base_null}, "
        f"unboundedHttpPackageCalls {sum(unbounded_http.values())}/{base_http} "
        f"(single source: {REGISTRY_REL})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
