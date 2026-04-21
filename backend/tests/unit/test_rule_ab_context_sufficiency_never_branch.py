from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from check_rule_ab_aggregator_integrity import scan_router_reads


def test_context_sufficiency_real_router_path_has_no_ab102_violation() -> None:
    path = REPO_ROOT / "backend/app/orchestration/routing_engine.py"
    violations = scan_router_reads([path], REPO_ROOT)
    assert not [item for item in violations if item.startswith("AB102")]


def test_context_sufficiency_prompt_caveat_usage_stays_allowed(tmp_path) -> None:
    path = tmp_path / "backend/app/orchestration/routing_engine.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "context_summary = user_state.context_sufficiency_summary\n"
        "if context_summary is not None:\n"
        "    caveat = render_context_caveat(context_summary)\n",
        encoding="utf-8",
    )
    assert scan_router_reads([path], tmp_path) == []


def test_context_sufficiency_direct_router_branch_is_rejected(tmp_path) -> None:
    path = tmp_path / "backend/app/orchestration/routing_engine.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "if user_state.context_sufficiency_summary:\n"
        "    route = 'clarify'\n",
        encoding="utf-8",
    )
    violations = scan_router_reads([path], tmp_path)
    assert any(item.startswith("AB102") for item in violations)
