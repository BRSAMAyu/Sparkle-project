#!/usr/bin/env python3
"""i18n coverage guard — detect presentation-layer Dart files missing locale awareness.

Strategy: a presentation file (screen / widget) that contains Chinese UI strings
MUST import i18n infrastructure (context_l10n, i18n_service, or AppLocalizations).
If a file has Chinese string literals but no i18n imports, it gets flagged.

This prevents NEW files from being created without i18n support, while trusting
that files already wired to the i18n system handle their strings properly
(defaults, fallbacks, structured metadata, etc.).

Exit 0 on pass, 1 on violations found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

MOBILE_LIB = Path("mobile/lib")

# Only scan presentation-layer directories
SCAN_DIRS: list[str] = [
    "/presentation/screens/",
    "/presentation/widgets/",
    "/core/design/widgets/",
]

# Files exempt from scanning (legacy — reviewed in prior i18n rounds, to be
# addressed incrementally; the guard's primary purpose is blocking NEW files)
EXEMPT_FILES: set[str] = {
    "entity_card_payloads.dart",
    "simulation_copy.dart",
    "execution_copy.dart",
    "tool_registry.dart",
    "poster_studio_screen.dart",
    # core/design/widgets — existing shared widgets, Chinese-first with review backlog
    "app_feedback.dart",
    "engagement_heatmap.dart",
    "flame_indicator.dart",
    "loading_indicator.dart",
    "sparkle_avatar.dart",
    # core/statistics — dashboard widgets, data labels
    "statistics_line_chart.dart",
    "statistics_pie_chart.dart",
    "statistics_empty_state.dart",
    "statistics_overview_cards.dart",
    # features — existing screens/widgets, prior i18n rounds covered primary paths
    "partner_visibility_banner.dart",
    "group_recommendation_card.dart",
    "memory_evidence_badge.dart",
    "pending_commitments_section.dart",
    "openclaw_primitives.dart",
    "tool_host_screen.dart",
    "tool_shell.dart",
}

# CJK
_CJK_RE = re.compile(r'[一-鿿]')

# File is i18n-aware if it imports any of these
_I18N_IMPORT_RE = re.compile(
    r"import\s+['\"].*context_l10n|"
    r"import\s+['\"].*i18n_service|"
    r"import\s+['\"].*app_localizations|"
    r"import\s+['\"].*l10n/"
)

# String literal containing Chinese
_STRING_CHINESE_RE = re.compile(r"""(?:[rb]?['"])([^'"]*[一-鿿][^'"]*)(?:['\"])""")


def _should_scan(path: Path) -> bool:
    path_str = path.as_posix()
    for d in SCAN_DIRS:
        if d in path_str:
            return True
    return False


def _is_exempt(path: Path) -> bool:
    return path.name in EXEMPT_FILES


def _file_has_i18n_imports(text: str) -> bool:
    """Check if the file imports any i18n infrastructure."""
    return bool(_I18N_IMPORT_RE.search(text))


def _file_has_chinese_ui_strings(text: str) -> bool:
    """Check if the file has Chinese characters inside string literals."""
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*') or stripped.startswith('///'):
            continue
        if 'static const' in line:
            continue
        if 'import ' in line and stripped.startswith('import'):
            continue
        if _CJK_RE.search(line) and _STRING_CHINESE_RE.search(line):
            return True
    return False


def scan_all(*, repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    mobile_lib = repo_root / MOBILE_LIB
    if not mobile_lib.exists():
        print(f"[i18n-coverage] SKIP — {MOBILE_LIB} not found")
        return []

    violations: list[str] = []
    dart_files = sorted(mobile_lib.rglob("*.dart"))

    for path in dart_files:
        if not _should_scan(path):
            continue
        if _is_exempt(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if not _file_has_chinese_ui_strings(text):
            continue

        if _file_has_i18n_imports(text):
            continue

        rel = path.relative_to(repo_root).as_posix()
        violations.append(rel)

    return violations


def main() -> int:
    violations = scan_all()
    if violations:
        print(f"[i18n-coverage] FAIL — {len(violations)} file(s) missing i18n imports")
        for v in violations:
            print(f"  {v}")
        print("\nAction: add one of these imports to each file:")
        print("  import 'package:sparkle/core/extensions/context_l10n.dart';")
        print("  import 'package:sparkle/core/services/i18n_service.dart';")
        return 1
    print("[i18n-coverage] PASS — all presentation files with Chinese strings import i18n infrastructure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
