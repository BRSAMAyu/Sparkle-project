from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "guards"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from check_metacog_hint_user_scope import scan_user_scope


def test_metacog_hint_user_scope_guard_passes_on_repo() -> None:
    assert scan_user_scope() == []
