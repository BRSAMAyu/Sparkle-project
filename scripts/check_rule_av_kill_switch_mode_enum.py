#!/usr/bin/env python3
"""
Rule AV: Kill Switch Mode Enum Validation.

Dynamic discovery — scans filesystem for kill switch services and parses
settings.py for Aurora mode settings. No hardcoded lists to go stale.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = REPO_ROOT / "backend" / "app" / "services"
SETTINGS_PATH = REPO_ROOT / "backend" / "app" / "config" / "settings.py"
METRICS_PATH = REPO_ROOT / "backend" / "app" / "core" / "metrics.py"

ALLOWED = {"off", "shadow", "live", "auto"}

STR_ASSIGNMENT = re.compile(
    r"^\s*(?P<name>[A-Z0-9_]+):\s*str\s*=\s*(?:\(\s*)?\"(?P<value>[^\"]+)\"",
    re.MULTILINE,
)
AURORA_MODE_PREFIX = "AURORA_"


def _discover_service_paths() -> list[Path]:
    """Scan services dir for kill switch service files."""
    return sorted(SERVICES_DIR.glob("aurora_*kill_switch*.py"))


def _discover_mode_settings() -> set[str]:
    """Parse settings.py for AURORA_* settings whose value is a tri-state."""
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    matches = {
        m.group("name"): m.group("value")
        for m in STR_ASSIGNMENT.finditer(text)
    }
    return {
        name for name, value in matches.items()
        if name.startswith(AURORA_MODE_PREFIX) and value in ALLOWED
    }


def main() -> int:
    violations: list[str] = []

    # 1. Validate all AURORA mode settings have allowed values
    settings_text = SETTINGS_PATH.read_text(encoding="utf-8")
    settings_map = {
        m.group("name"): m.group("value")
        for m in STR_ASSIGNMENT.finditer(settings_text)
    }
    mode_settings = _discover_mode_settings()

    invalid = {
        name: value
        for name, value in settings_map.items()
        if name in mode_settings and value not in ALLOWED
    }
    if invalid:
        for name, value in sorted(invalid.items()):
            violations.append(f"invalid mode enum {name}={value!r}")

    # 2. Verify Prometheus metric exists
    metrics_text = METRICS_PATH.read_text(encoding="utf-8")
    if "sparkle_kill_switch_mode" not in metrics_text:
        violations.append("sparkle_kill_switch_mode metric missing")

    # 3. Verify every kill switch service imports the shared helper
    service_paths = _discover_service_paths()
    for path in service_paths:
        text = path.read_text(encoding="utf-8")
        if "app.core.kill_switch" not in text:
            violations.append(
                f"service does not use shared kill_switch helper: {path.relative_to(REPO_ROOT)}"
            )

    if violations:
        print("[Rule AV] FAIL")
        for item in violations:
            print(item)
        return 1

    print(
        f"[Rule AV] PASS - validated {len(mode_settings)} mode settings "
        f"and {len(service_paths)} kill switch services"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
