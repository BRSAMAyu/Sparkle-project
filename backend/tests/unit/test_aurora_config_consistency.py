from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "scripts/check_aurora_config_consistency.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_aurora_config_consistency", CHECKER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aurora_config_defaults_are_consistent():
    checker = _load_checker()

    assert checker.validate() == []
