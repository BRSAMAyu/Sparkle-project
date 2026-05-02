#!/usr/bin/env python3
"""i18n coverage guard — scan mobile/lib presentation layer for hardcoded Chinese UI strings.

Only scans user-visible presentation files (screens, widgets, core design widgets).
Detects lines where a Chinese string literal appears WITHOUT a locale-gating
pattern on the same line (isChinese, zh ?, .l10n, AppLocalizations).

Exit 0 on pass, 1 on violations found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

MOBILE_LIB = Path("mobile/lib")

# Only scan presentation-layer directories (user-visible UI)
SCAN_ONLY_SUB_PATHS: list[str] = [
    "/presentation/screens/",
    "/presentation/widgets/",
    "/core/design/widgets/",
]

# Specific files exempt
EXEMPT_FILE_PATTERNS: list[str] = [
    "entity_card_payloads.dart",     # Data mapping, not UI
    "simulation_copy.dart",           # Generated copy text
    "execution_copy.dart",            # Generated copy text
    "tool_registry.dart",             # Tool configuration
]

# CJK Unified Ideographs
_CJK_RE = re.compile(r'[一-鿿]')

# ── Locale-gating patterns (same-line) ─────────────────────────────────────

_LOCALE_GATE_PATTERNS = [
    r'\bisChinese\b',
    r'\bzh\s*\?\s*',
    r'\.l10n\.',
    r'AppLocalizations',
    r'\blocale\b',
    r'\blang\s*==\s*',
    r'\bDateFormat\b',
    r'\bcontext\.tr\b',
    r'I18nService',
    r'\?\?\s*[\'\"][^\'\"]*[一-鿿]',   # null-coalescing fallback: l10n?.key ?? '中文'
    r'\?\s*[\'\"][^\'\"]*[一-鿿]',     # ternary true branch: cond ? '中文...' : '...'
]

_GATE_RE = re.compile('|'.join(_LOCALE_GATE_PATTERNS))

_STRING_CHINESE_RE = re.compile(r'''(?:r?['"])([^'\"]*[一-鿿][^'\"]*)(?:['\"])''')


def _should_scan(path: Path) -> bool:
    """Only scan files under recognized presentation directories."""
    path_str = path.as_posix()
    for scan_path in SCAN_ONLY_SUB_PATHS:
        if scan_path in path_str:
            return True
    return False


def _is_exempt_file(path: Path) -> bool:
    name = path.name
    for pattern in EXEMPT_FILE_PATTERNS:
        if pattern in name:
            return True
    return False


def _line_is_comment(line: str) -> bool:
    stripped = line.lstrip()
    return (stripped.startswith('//') or stripped.startswith('*')
            or stripped.startswith('/*') or stripped.startswith('///'))


def scan_file(path: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    for lineno, line in enumerate(text.splitlines(), start=1):
        if _line_is_comment(line):
            continue
        if not _CJK_RE.search(line):
            continue
        if _GATE_RE.search(line):
            continue
        if 'static const' in line:
            continue
        if 'import ' in line and line.strip().startswith('import'):
            continue
        if _STRING_CHINESE_RE.search(line):
            violations.append((lineno, line.strip()))

    return violations


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
        if _is_exempt_file(path):
            continue

        file_violations = scan_file(path)
        rel = path.relative_to(repo_root).as_posix()
        for lineno, line_text in file_violations:
            violations.append(f"{rel}:{lineno}: {line_text}")

    return violations


def main() -> int:
    violations = scan_all()
    if violations:
        print(f"[i18n-coverage] FAIL — {len(violations)} hardcoded Chinese string(s) found")
        for v in violations:
            print(f"  {v}")
        return 1
    print("[i18n-coverage] PASS — no hardcoded Chinese UI strings found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
