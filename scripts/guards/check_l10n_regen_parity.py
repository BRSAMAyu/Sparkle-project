#!/usr/bin/env python3
"""l10n regen parity guard — detect gen-l10n artifacts drifted from their arb sources.

Background (L10N-REGEN, 2026-09): two mobile cards independently reported
~130-line format drift between locally regenerated dart artifacts and the
checked-in ones, because workers hand-appended getters instead of running
`flutter gen-l10n`. The format baseline was reset in a1572cfa (CP-01-MOBILE);
this guard keeps the semantic half of that debt from returning.

What it checks (pure stdlib, no Flutter SDK needed):
  1. The three dart artifacts exist.
  2. Abstract-class members in app_localizations.dart exactly equal the
     template arb (app_zh.arb) message keys — catches "arb edited without
     regen" and "getter hand-appended without arb key".
  3. zh/en subclasses implement every member (no missing, no extra).

What it intentionally does NOT check:
  - Byte-level format identity (requires `flutter gen-l10n`; recommended as a
    CI step: `flutter gen-l10n && git diff --exit-code -- mobile/lib/l10n`).
  - zh/en arb key parity — untranslated fallback is legal gen-l10n behavior;
    a warning is printed instead.

Exit 0 on pass, 1 on violations.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

L10N_DIR = Path("mobile/lib/l10n")
TEMPLATE_ARB = "app_zh.arb"
ARBS = ("app_zh.arb", "app_en.arb")
DARTS = ("app_localizations.dart", "app_localizations_zh.dart", "app_localizations_en.dart")

MEMBER_RE = re.compile(r"^\s String (?:get (\w+)|(\w+)\()", re.MULTILINE)


def arb_keys(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k for k in data if not k.startswith("@")}


def class_members(text: str, marker: str) -> set[str]:
    """Extract String getter/method names declared directly in a class body."""
    start = text.index(marker)
    body = text[start:]
    nxt = re.search(r"\nclass ", body[1:])
    if nxt:
        body = body[: nxt.start() + 1]
    return {a or b for a, b in MEMBER_RE.findall(body)}


def main() -> int:
    failures: list[str] = []

    for name in ARBS + DARTS:
        if not (L10N_DIR / name).exists():
            failures.append(f"missing artifact: {L10N_DIR / name}")
    if failures:
        print("L10N-REGEN-PARITY FAIL:")
        print("\n".join(f"  - {f}" for f in failures))
        return 1

    template = arb_keys(L10N_DIR / TEMPLATE_ARB)
    abstract = class_members(
        (L10N_DIR / "app_localizations.dart").read_text(encoding="utf-8"),
        "abstract class AppLocalizations",
    )

    missing_in_class = sorted(template - abstract)
    extra_in_class = sorted(abstract - template)
    if missing_in_class:
        failures.append(
            f"{len(missing_in_class)} template arb key(s) absent from abstract class "
            f"(arb edited without gen-l10n?): {missing_in_class[:8]}"
        )
    if extra_in_class:
        failures.append(
            f"{len(extra_in_class)} abstract member(s) without template arb key "
            f"(getter hand-appended without arb?): {extra_in_class[:8]}"
        )

    for dart, cls in (
        ("app_localizations_zh.dart", "AppLocalizationsZh"),
        ("app_localizations_en.dart", "AppLocalizationsEn"),
    ):
        impl = class_members((L10N_DIR / dart).read_text(encoding="utf-8"), cls)
        gap = sorted(abstract - impl)
        extra = sorted(impl - abstract)
        if gap:
            failures.append(f"{cls} missing {len(gap)} member(s): {gap[:8]}")
        if extra:
            failures.append(f"{cls} has {len(extra)} member(s) not in abstract class: {extra[:8]}")

    # Non-fatal: report template keys untranslated in other locales.
    for arb in ARBS:
        if arb == TEMPLATE_ARB:
            continue
        keys = arb_keys(L10N_DIR / arb)
        untranslated = sorted(template - keys)
        if untranslated:
            print(
                f"WARN: {arb} missing {len(untranslated)} translation(s) "
                f"(falls back to template at runtime): {untranslated[:8]}"
            )

    if failures:
        print("L10N-REGEN-PARITY FAIL:")
        print("\n".join(f"  - {f}" for f in failures))
        print("Fix: cd mobile && flutter gen-l10n, then commit the regenerated artifacts.")
        return 1

    print(
        f"L10N-REGEN-PARITY OK: {len(template)} template keys == abstract members; "
        "zh/en subclasses complete."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
