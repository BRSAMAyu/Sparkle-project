"""Regression test for ISSUE-20260503-0432-L2.

Verifies that the AV guard uses dynamic discovery instead of hardcoded lists,
covering all kill switch services and Aurora mode settings.
"""
import re
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AV_SCRIPT = REPO_ROOT / "scripts" / "check_rule_av_kill_switch_mode_enum.py"
SERVICES_DIR = REPO_ROOT / "backend" / "app" / "services"
SETTINGS_PATH = REPO_ROOT / "backend" / "app" / "config" / "settings.py"


def test_guard_uses_dynamic_service_discovery():
    """AV guard must discover services via glob, not a hardcoded list."""
    source = AV_SCRIPT.read_text()
    assert "SERVICE_PATHS" not in source or "SERVICE_PATHS" not in source.split("def main")[0], (
        "SERVICE_PATHS hardcoded list should not exist in the guard"
    )
    assert "glob" in source or "_discover_service" in source, (
        "Guard should use dynamic discovery for services"
    )


def test_guard_uses_dynamic_mode_settings():
    """AV guard must discover mode settings by parsing settings.py, not from a hardcoded set."""
    source = AV_SCRIPT.read_text()
    assert "_discover_mode_settings" in source, (
        "Guard should have a _discover_mode_settings function"
    )


def test_all_service_files_covered():
    """Every aurora_*kill_switch*.py on disk must be found by the guard."""
    # Import the module's discovery function
    import importlib.util

    spec = importlib.util.spec_from_file_location("av_guard", AV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    discovered = mod._discover_service_paths()
    actual = sorted(SERVICES_DIR.glob("aurora_*kill_switch*.py"))

    discovered_names = {p.name for p in discovered}
    actual_names = {p.name for p in actual}

    assert discovered_names == actual_names, (
        f"Guard discovers {len(discovered_names)} services, "
        f"but filesystem has {len(actual_names)}. "
        f"Missing: {actual_names - discovered_names}"
    )


def test_all_mode_settings_covered():
    """Every AURORA_* mode setting in settings.py with a tri-state value must be found."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("av_guard", AV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    discovered = mod._discover_mode_settings()

    # Parse settings.py independently
    text = SETTINGS_PATH.read_text()
    pattern = re.compile(
        r"^\s*(?P<name>[A-Z0-9_]+):\s*str\s*=\s*(?:\(\s*)?\"(?P<value>[^\"]+)\"",
        re.MULTILINE,
    )
    matches = {m.group("name"): m.group("value") for m in pattern.finditer(text)}
    expected = {
        name for name, value in matches.items()
        if name.startswith("AURORA_") and value in {"off", "shadow", "live", "auto"}
    }

    assert discovered == expected, (
        f"Guard discovers {len(discovered)} mode settings, "
        f"but settings.py has {len(expected)}. "
        f"Missing: {expected - discovered}"
    )


def test_dual_core_router_covered():
    """The E1-added dual_core_router kill switch must be covered."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("av_guard", AV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    discovered = mod._discover_service_paths()
    names = [p.name for p in discovered]
    assert "aurora_dual_core_router_kill_switch_service.py" in names

    mode_settings = mod._discover_mode_settings()
    assert "AURORA_DUAL_CORE_ROUTER_MODE" in mode_settings


def test_stage37_llm_safety_covered():
    """Stage 37 (LLM Safety) kill switch must be covered."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("av_guard", AV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    discovered = mod._discover_service_paths()
    names = [p.name for p in discovered]
    assert "aurora_stage37_llm_safety_kill_switch_service.py" in names

    mode_settings = mod._discover_mode_settings()
    assert "AURORA_STAGE37_LLM_SAFETY_MODE" in mode_settings


def test_stage39_covered():
    """Stage 39 kill switch service and modes must be covered."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("av_guard", AV_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    discovered = mod._discover_service_paths()
    names = [p.name for p in discovered]
    assert "aurora_stage39_kill_switch_service.py" in names

    mode_settings = mod._discover_mode_settings()
    assert "AURORA_STAGE39_MODE" in mode_settings
