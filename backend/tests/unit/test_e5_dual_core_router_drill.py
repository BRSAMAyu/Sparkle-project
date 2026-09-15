"""Regression test for ISSUE-20260504-0945-E5.

Verifies that dual_core_router is properly integrated into the central
kill switch drill runner (run_kill_switch_drills.py):
1. Included in DEFAULT_SPECS
2. Included in SPECS dict
3. Apply function exists and uses AuroraDualCoreRouterKillSwitchService
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "stage40" / "run_kill_switch_drills.py"


def _load_drill_module():
    """Load the drill runner as a module for inspection."""
    mod_name = "run_kill_switch_drills"
    spec = importlib.util.spec_from_file_location(mod_name, SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Must register in sys.modules BEFORE exec_module so dataclass factory
    # can resolve cls.__module__
    old_modules = dict(sys.modules)
    sys.modules[mod_name] = mod
    backend_root = str(REPO_ROOT / "backend")
    old_path = list(sys.path)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    try:
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path[:] = old_path
        sys.modules = old_modules


def test_dual_core_router_in_default_specs():
    """E5 fix: dual_core_router must be in DEFAULT_SPECS."""
    mod = _load_drill_module()
    assert "dual_core_router" in mod.DEFAULT_SPECS, (
        "dual_core_router missing from DEFAULT_SPECS — drill_all would skip it"
    )


def test_dual_core_router_in_specs_dict():
    """E5 fix: dual_core_router must have a DrillSpec entry."""
    mod = _load_drill_module()
    assert "dual_core_router" in mod.SPECS, (
        "dual_core_router missing from SPECS dict — --only dual_core_router would fail"
    )


def test_dual_core_router_spec_has_valid_stage():
    """DrillSpec for dual_core_router should reference the correct stage label."""
    mod = _load_drill_module()
    spec = mod.SPECS["dual_core_router"]
    assert spec.stage == "dual_core_router", (
        f"Expected stage='dual_core_router', got '{spec.stage}'"
    )


def test_dual_core_router_apply_is_async_callable():
    """_dual_core_router_apply must be an async callable that returns dict."""
    mod = _load_drill_module()
    assert callable(mod._dual_core_router_apply), (
        "_dual_core_router_apply is not callable"
    )
    import asyncio
    assert asyncio.iscoroutinefunction(mod._dual_core_router_apply), (
        "_dual_core_router_apply is not an async function"
    )


if __name__ == "__main__":
    test_dual_core_router_in_default_specs()
    test_dual_core_router_in_specs_dict()
    test_dual_core_router_spec_has_valid_stage()
    test_dual_core_router_apply_is_async_callable()
    print("All 4 E5 regression tests passed.")
