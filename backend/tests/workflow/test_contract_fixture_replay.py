from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.replay_backend_contract_fixtures import run_fixture_file


def test_backend_contract_fixture_replay_is_green():
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "contract_replay_cases.json"

    failures = run_fixture_file(fixture_path)

    assert failures == []
