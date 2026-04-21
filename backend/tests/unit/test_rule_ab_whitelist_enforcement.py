from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from check_rule_ab_aggregator_integrity import scan_aggregator_read_only, scan_router_reads


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_rule_ab_blocks_forbidden_aggregator_write_calls(tmp_path) -> None:
    path = _write(tmp_path / "backend/app/state_aggregator/bad.py", "session.save(snapshot)\n")
    violations = scan_aggregator_read_only([path], tmp_path)
    assert any(item.startswith("AB001") for item in violations)


def test_rule_ab_blocks_inline_sql_write_tokens(tmp_path) -> None:
    path = _write(tmp_path / "backend/app/state_aggregator/bad_sql.py", 'query = "UPDATE snapshots SET x = 1"\n')
    violations = scan_aggregator_read_only([path], tmp_path)
    assert any(item.startswith("AB003") for item in violations)


def test_rule_ab_allows_task_sufficiency_summary_router_read(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/orchestration/routing_engine.py",
        "value = user_state.task_sufficiency_summary\n",
    )
    assert scan_router_reads([path], tmp_path) == []


def test_rule_ab_allows_active_skills_summary_get_read(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/routing/skill_router.py",
        'value = user_state.get("active_skills_summary")\n',
    )
    assert scan_router_reads([path], tmp_path) == []


def test_rule_ab_blocks_non_whitelisted_router_field_reads(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/orchestration/routing_engine.py",
        "value = user_state.achievement_summary\n",
    )
    violations = scan_router_reads([path], tmp_path)
    assert any(item.startswith("AB101") for item in violations)


def test_rule_ab_blocks_future_fields_by_default(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/routing/future_router.py",
        "value = user_state.future_stage30_signal\n",
    )
    violations = scan_router_reads([path], tmp_path)
    assert any("future_stage30_signal" in item for item in violations)


def test_rule_ab_blocks_context_sufficiency_branch_conditions(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/orchestration/routing_engine.py",
        "if user_state.context_sufficiency_summary:\n    mode = 'branch'\n",
    )
    violations = scan_router_reads([path], tmp_path)
    assert any(item.startswith("AB102") for item in violations)


def test_rule_ab_ignores_safe_scalar_reads(tmp_path) -> None:
    path = _write(
        tmp_path / "backend/app/orchestration/routing_engine.py",
        "identifier = user_state.user_id\nversion = user_state.schema_version\n",
    )
    assert scan_router_reads([path], tmp_path) == []
