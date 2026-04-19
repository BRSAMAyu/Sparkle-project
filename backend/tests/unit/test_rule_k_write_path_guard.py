from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_guard_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "check_rule_k_write_paths.py"
    spec = importlib.util.spec_from_file_location("check_rule_k_write_paths", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_file(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_rule_k_guard_accepts_safe_session_strategy_usage(tmp_path: Path) -> None:
    module = _load_guard_module()
    target = _write_file(
        tmp_path,
        "backend/app/orchestration/experience_actuator.py",
        """
from app.services.user_strategy_state_service import UserStrategyStateService

async def apply_safe_control(service, user_id, session_id):
    return await service.apply_adjustment(
        user_id,
        {"session_mode": "recovery"},
        layer=UserStrategyStateService.SESSION_LAYER,
        reason="safe",
        evidence={"source": "test"},
        confidence=0.8,
        session_id=session_id,
    )
""".strip(),
    )

    violations = module.scan_paths([target], tmp_path)
    assert violations == []


def test_rule_k_guard_blocks_preference_service_in_control_path(tmp_path: Path) -> None:
    module = _load_guard_module()
    target = _write_file(
        tmp_path,
        "backend/app/orchestration/routing_engine.py",
        """
from app.services.personalization.preference_service import PreferenceService

async def bad_write(db, user_id):
    service = PreferenceService(db)
    await service.update_inferred_raw(user_id, {"foo": "bar"})
""".strip(),
    )

    violations = module.scan_paths([target], tmp_path)
    assert [item.rule_id for item in violations] == ["RK002", "RK002", "RK002"]


def test_rule_k_guard_blocks_plan_state_writes_in_control_path(tmp_path: Path) -> None:
    module = _load_guard_module()
    target = _write_file(
        tmp_path,
        "backend/app/aurora/runtime_guard.py",
        """
async def bad_write(plan_state_service, user_id, plan_id):
    await plan_state_service.upsert_plan_state(user_id, plan_id, {"facts": {"foo": "bar"}})
""".strip(),
    )

    violations = module.scan_paths([target], tmp_path)
    assert len(violations) == 1
    assert violations[0].rule_id == "RK004"


def test_rule_k_guard_ignores_non_controlled_paths(tmp_path: Path) -> None:
    module = _load_guard_module()
    target = _write_file(
        tmp_path,
        "backend/app/orchestration/adaptive_replanner.py",
        """
async def allowed_here(plan_state_service, user_id, plan_id):
    await plan_state_service.upsert_plan_state(user_id, plan_id, {"facts": {"adaptive_adjustments": {}}})
""".strip(),
    )

    paths = module.resolve_scan_paths(tmp_path, [str(target)])
    assert paths == []
