#!/usr/bin/env python3
r"""FS-CARRY finally-erase guard — ratchet the `finally` error-carry face.

wt241 (ERR-FINALLY, auth domain) proved the disease: 15 auth-provider
`finally { state = state.copyWith(isLoading: false); }` blocks erased the
error/failure the *catch* had just written, because AuthState.copyWith uses
direct-assignment semantics — an omitted `error:` argument resets the field
to null. The user never saw a single one of those errors. wt241 fixed the
auth face with call-site carry-over (`error: state.error`).

FINALLY-SCAN (wt247) then swept ALL of mobile/lib for the same shape:

- Every `finally` body that mutates provider state was extracted (brace
  balanced) and judged against its state class's copyWith semantics.
- Verdict: **zero live same-disease sites remain**. The two un-carried
  `finally` copyWith faces that exist (chat_provider's isSending reset,
  plan_provider's isLoading fallback) are safe only because ChatState /
  PlanListState use null-merge copyWith (`error: clearError ? null :
  error ?? this.error`) — an omitted error argument KEEPS the old value
  there. Widget-local `setState` finally blocks clear busy markers only
  (structurally immune: direct field assignment has no null-merge trap).
- The precondition (direct-assign copyWith on an error field) is alive in
  10 other state classes (calendar/marketplace/seed_library x3/
  notification_center x2/error_book/visual_elements x2) — all currently
  benign (their catches write the error as the last statement, with no
  trailing finally). They are latent carriers: the next person who adds a
  `finally { state = state.copyWith(isLoading: false); }` there re-creates
  the auth bug silently.

This guard freezes that face. It scans every `finally` block in
`mobile/lib/**` for `state = state.copyWith(...)` calls whose argument
list carries NO error key (`error:` / `failure:` / `errorCode:` /
`errorMessage:` / `clearError:` / `clearFailure:`) — the exact textual
shape of the wt241 disease. Ratchet semantics, N9 family form:

- file -> un-carried finally-copyWith count pinned in the baseline JSON.
  A NEW file with any hit fails; a per-file count going UP fails; counts
  may only go down (via `--update-baseline` after a legitimate cleanup).
- The carry-over form (`error: state.error`) and the explicit-clear form
  (`clearError: true`) both pass — the guard enforces *intent made
  explicit*, not a particular spelling.

Known blind spots (accepted, reviewed at registration): helper-mediated
mutations (`finally { _setHandoffLoading(id, false); }` where the helper
copyWithes) are invisible to a textual finally scan — task_provider's four
finally sites are of this shape and are safe today because their helpers
only touch in-flight sets; full-state reconstruction (`state = FreshState()`)
in a finally is also out of pattern (none exists @1ebcfe09). Both are
review-checkable; the textual face this guard pins is the one the disease
actually wore.

Baseline: `finally_error_carry_baseline.json`, registered from measured
values at HEAD 1ebcfe09 (FINALLY-SCAN card wt247, 2026-09-23):
chat_provider x1 + plan_provider x1, both verified safe (null-merge state
classes, documented in v3-output/FINALLY-SCAN/REPORT.md).

CLI:
  python3 scripts/guards/check_finally_error_carry.py                # guard run
  python3 scripts/guards/check_finally_error_carry.py --update-baseline
  python3 scripts/guards/check_finally_error_carry.py --self-test    # fixture test (<2s)

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
BASELINE_PATH = Path(__file__).resolve().parent / "finally_error_carry_baseline.json"

_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*|///)")

# `finally {` opener (also matches the `} finally {` tail form).
_FINALLY_OPEN = re.compile(r"\bfinally\s*\{")

# Provider-state mutation shape inside a finally body. Receiver is literally
# `state` (StateNotifier/Notifier state field) — the wt241 disease form.
_STATE_COPYWITH = re.compile(r"\bstate\s*=\s*state\s*\.\s*copyWith\s*\(")

# An argument list carries error intent if ANY of these keys appear. The
# carry-over fix (`error: state.error, failure: state.failure`) and the
# explicit-clear fix (`clearError: true`) both satisfy it.
_CARRY_KEY = re.compile(
    r"\b(?:error|failure|errorCode|errorMessage|clearError|clearFailure)\s*:"
)


def _code_text(text: str) -> str:
    """Drop comment-only lines so commented-out code cannot trip the scanner."""
    return "\n".join(ln for ln in text.splitlines() if not _COMMENT_RE.match(ln))


def _balanced_block(text: str, open_brace: int) -> str:
    """Return the brace-balanced region starting at the `{` at open_brace."""
    depth = 0
    for i in range(open_brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace : i + 1]
    return text[open_brace:]  # unbalanced (truncated file)


def _balanced_parens(text: str, open_paren: int) -> str:
    """Return the paren-balanced region starting at the `(` at open_paren."""
    depth = 0
    for i in range(open_paren, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren : i + 1]
    return text[open_paren : open_paren + 400]  # unbalanced (truncated file)


def iter_finally_bodies(code: str):
    """Yield each brace-balanced finally body (comment lines already stripped)."""
    for m in _FINALLY_OPEN.finditer(code):
        open_brace = code.index("{", m.start())
        yield _balanced_block(code, open_brace)


def scan_un_carried_finally_copywith(mobile_lib: Path) -> dict[str, int]:
    """file -> count of finally bodies containing an un-carried state.copyWith."""
    out: dict[str, int] = {}
    for p in sorted(mobile_lib.rglob("*.dart")):
        if p.name.endswith(".g.dart") or p.name.startswith("app_localizations"):
            continue
        code = _code_text(p.read_text(encoding="utf-8"))
        hits = 0
        for body in iter_finally_bodies(code):
            for m in _STATE_COPYWITH.finditer(body):
                args = _balanced_parens(body, body.index("(", m.end() - 1))
                if not _CARRY_KEY.search(args):
                    hits += 1
        if hits:
            out["mobile/lib/" + p.relative_to(mobile_lib).as_posix()] = hits
    return out


def check(baseline: dict, current: dict[str, int]) -> list[str]:
    violations: list[str] = []
    base = baseline.get("finallyErrorCopyWith", {})
    for file, n in sorted(current.items()):
        b = base.get(file)
        if b is None:
            violations.append(
                f"NEW FILE {file}: un-carried finally copyWith x{n} "
                "(wt241 disease shape — a finally copyWith without an error key "
                "erases the error the catch just wrote when the state class's "
                "copyWith is direct-assign. Carry it over (`error: state.error`) "
                "or clear it explicitly (`clearError: true`); pin in baseline "
                "only with a null-merge-state proof in the REPORT."
            )
        elif n > b:
            violations.append(
                f"{file}: un-carried finally copyWith {n} > baseline {b} (+{n - b})"
            )
    return violations


def _write_baseline(path: Path, current: dict[str, int]) -> None:
    payload = {
        "comment": (
            "Frozen ratchet baseline for check_finally_error_carry.py "
            "(wt241 auth finally-erase disease; FINALLY-SCAN wt247 sweep found "
            "zero live sites outside auth — the two pinned faces are safe "
            "because ChatState/PlanListState copyWith are null-merge with "
            "explicit clear flags, see v3-output/FINALLY-SCAN/REPORT.md). "
            "Registered from measured values at HEAD 1ebcfe09. Counts may "
            "only go down; refresh via --update-baseline only after a "
            "cleanup batch, never raise."
        ),
        "finallyErrorCopyWith": current,
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
        lib = tmp / "lib" / "features"
        lib.mkdir(parents=True)

        # 1. the wt241 auth disease shape (multi-line, as written in auth_provider)
        diseased = "\n".join(
            [
                "  } finally {",
                "    state = state.copyWith(",
                "      isLoading: false,",
                "    );",
                "  }",
            ]
        )
        # 2. the wt241 carry-over fix shape -> passes
        carried = "\n".join(
            [
                "  } finally {",
                "    if (mounted) {",
                "      state = state.copyWith(",
                "        isLoading: false,",
                "        error: state.error,",
                "        failure: state.failure,",
                "      );",
                "    }",
                "  }",
            ]
        )
        # 3. explicit-clear intent -> passes
        cleared = "\n".join(
            [
                "  } finally {",
                "    state = state.copyWith(isLoading: false, clearError: true);",
                "  }",
            ]
        )
        # 4. nested finally body + non-error clear flags (chat_provider shape)
        nested = "\n".join(
            [
                "  } finally {",
                "    if (ready && state.isSending) {",
                "      state = state.copyWith(",
                "        isSending: false,",
                "        clearTransparency: true,",
                "      );",
                "    }",
                "  }",
            ]
        )
        # 5. commented-out disease inside finally must not count
        commented = "\n".join(
            [
                "  } finally {",
                "    // state = state.copyWith(isLoading: false);",
                "    _busy = false;",
                "  }",
            ]
        )
        # 6. same copyWith OUTSIDE any finally (success path) must not count
        outside = "\n".join(
            [
                "  Future<void> load() async {",
                "    state = state.copyWith(isLoading: true);",
                "    try {",
                "      await repo.go();",
                "      state = state.copyWith(isLoading: false);",
                "    } catch (e) {",
                "      state = state.copyWith(isLoading: false, error: e.toString());",
                "    }",
                "  }",
            ]
        )
        sample = "\n".join(
            [
                diseased,
                carried,
                cleared,
                nested,
                commented,
                outside,
            ]
        )
        (lib / "sample_provider.dart").write_text(sample, encoding="utf-8")

        current = scan_un_carried_finally_copywith(tmp / "lib")
        # diseased (1) + nested un-carried (1) = 2; carried/cleared/commented/outside = 0
        want = {"mobile/lib/features/sample_provider.dart": 2}
        if current != want:
            failures.append(f"scan mismatch: {current} != {want}")

        base = {"finallyErrorCopyWith": want}
        if check(base, current):
            failures.append("clean pinned baseline should pass")

        # ratchet: count raised + new file both fail
        raised = {"mobile/lib/features/sample_provider.dart": 3}
        v = check(base, raised)
        if len(v) != 1 or "baseline 2" not in v[0]:
            failures.append(f"raise case mismatch: {v}")
        newfile = dict(want)
        newfile["mobile/lib/features/other_provider.dart"] = 1
        v = check(base, newfile)
        if len(v) != 1 or "NEW FILE" not in v[0]:
            failures.append(f"new-file case mismatch: {v}")

        # lowered counts pass (ratchet only-down)
        v = check(base, {"mobile/lib/features/sample_provider.dart": 1})
        if v:
            failures.append(f"lowered case should pass: {v}")

    if failures:
        print("[fs-carry] SELF-TEST FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print(
        "[fs-carry] SELF-TEST PASS "
        "(finally un-carried copyWith ratchet: disease/carry-over/clear-flag/"
        "nested/commented/outside-finally/raise/new-file/lowered cases)"
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
    parser.add_argument("--mobile-lib", type=Path, help="override mobile/lib root (self-tests / fixtures only)")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    mobile_lib = args.mobile_lib or MOBILE_LIB
    baseline_path = args.baseline or BASELINE_PATH

    current = scan_un_carried_finally_copywith(mobile_lib)
    total = sum(current.values())

    if args.update_baseline:
        old = None
        if baseline_path.exists():
            old = json.loads(baseline_path.read_text(encoding="utf-8"))
        _write_baseline(baseline_path, current)
        old_total = sum(old.get("finallyErrorCopyWith", {}).values()) if old else None
        arrow = (
            f"un-carried finally copyWith {old_total} -> {total}"
            if old is not None
            else f"un-carried finally copyWith {total}"
        )
        print(f"[fs-carry] baseline updated: {arrow}")
        return 0

    if not baseline_path.exists():
        print(f"[fs-carry] FAIL — baseline missing: {baseline_path}")
        print(
            "  Register it from measured values: "
            "python3 scripts/guards/check_finally_error_carry.py --update-baseline"
        )
        return 1
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    violations = check(baseline, current)

    if violations:
        print(
            f"[fs-carry] FAIL — {len(violations)} finally-erase violation(s); "
            "a `finally` block copyWithes provider state without an error key. "
            "If the state class's copyWith is direct-assign (AuthState-style), "
            "this erases the error the catch just wrote (wt241 disease). "
            "Carry it over (`error: state.error`), clear it explicitly "
            "(`clearError: true`), or prove null-merge semantics and pin in "
            "the baseline with the proof recorded in the REPORT."
        )
        for v in violations:
            print(f"  {v}")
        return 1

    base_total = sum(baseline.get("finallyErrorCopyWith", {}).values())
    print(
        f"[fs-carry] PASS — ratchet holds: un-carried finally copyWith "
        f"{total}/{base_total} ({len(current)} pinned files; "
        f"carried `error: state.error` and `clearError: true` forms pass)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
