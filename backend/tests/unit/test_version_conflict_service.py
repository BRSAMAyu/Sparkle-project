from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.orchestration.schemas import ExecutablePlan, StateSnapshot, ToolCallSpec
from app.orchestration.version_conflict_service import VersionConflictResult, VersionConflictService


def _build_plan(plan_id: str | None = None) -> ExecutablePlan:
    pid = plan_id or str(uuid.uuid4())
    return ExecutablePlan(
        plan_id=pid,
        context_version=f"{pid}:v1",
        plan_version=1,
        confidence=0.85,
        tool_calls=[ToolCallSpec(id="tc1", name="create_task", params={"title": "A"})],
        fallback_strategy={"on_version_conflict": "replan"},
    )


@pytest.mark.asyncio
async def test_check_all_conflicts_no_conflict():
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    snapshot = StateSnapshot(context_versions={"tasks": "v1"})
    result = await service.check_all_conflicts(
        plan=plan,
        snapshot=snapshot,
        current_context_versions={"tasks": "v1"},
        user_id=uuid.uuid4(),
    )
    assert result.has_conflict is False


@pytest.mark.asyncio
async def test_check_all_conflicts_context_only():
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    snapshot = StateSnapshot(context_versions={"tasks": "v1"})
    result = await service.check_all_conflicts(
        plan=plan,
        snapshot=snapshot,
        current_context_versions={"tasks": "v2"},
        user_id=uuid.uuid4(),
    )
    assert result.has_conflict is True
    assert result.conflict_type == "context_version"
    assert "tasks" in result.conflicted_domains


@pytest.mark.asyncio
async def test_check_all_conflicts_plan_version_only():
    class PlanStateServiceStub:
        async def get_plan_state(self, user_id, plan_id):
            return SimpleNamespace(version=2, current_phase="p1", completed_milestones=[], active_task_count=0, feedback_log=[], constraints={})

    service = VersionConflictService(redis=None, plan_state_service=PlanStateServiceStub(), planner=None)
    plan = _build_plan()
    snapshot = StateSnapshot(context_versions={"tasks": "v1"})
    result = await service.check_all_conflicts(
        plan=plan,
        snapshot=snapshot,
        current_context_versions={"tasks": "v1"},
        user_id=uuid.uuid4(),
    )
    assert result.has_conflict is True
    assert result.conflict_type == "plan_version"


@pytest.mark.asyncio
async def test_check_all_conflicts_both():
    class PlanStateServiceStub:
        async def get_plan_state(self, user_id, plan_id):
            return SimpleNamespace(version=2, current_phase="p1", completed_milestones=[], active_task_count=0, feedback_log=[], constraints={})

    service = VersionConflictService(redis=None, plan_state_service=PlanStateServiceStub(), planner=None)
    plan = _build_plan()
    snapshot = StateSnapshot(context_versions={"tasks": "v1"})
    result = await service.check_all_conflicts(
        plan=plan,
        snapshot=snapshot,
        current_context_versions={"tasks": "v2"},
        user_id=uuid.uuid4(),
    )
    assert result.has_conflict is True
    assert result.conflict_type == "both"


@pytest.mark.asyncio
async def test_resolve_conflict_proceed():
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    conflict = VersionConflictResult(has_conflict=True, recommendation="proceed")
    result = await service.resolve_conflict(
        conflict_result=conflict,
        original_plan=plan,
        user_id=uuid.uuid4(),
        session_id="s1",
        user_message="msg",
        plan_id=uuid.uuid4(),
    )
    assert result.success is True
    assert result.new_plan is plan


@pytest.mark.asyncio
async def test_resolve_conflict_discard():
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    conflict = VersionConflictResult(has_conflict=True, recommendation="discard")
    result = await service.resolve_conflict(
        conflict_result=conflict,
        original_plan=plan,
        user_id=uuid.uuid4(),
        session_id="s1",
        user_message="msg",
        plan_id=uuid.uuid4(),
    )
    assert result.success is False
    assert result.requires_hitl is False


@pytest.mark.asyncio
async def test_resolve_conflict_replan_success(monkeypatch):
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    new_plan = _build_plan()
    conflict = VersionConflictResult(has_conflict=True, recommendation="replan")

    async def mock_can_replan(user_id, plan_id):
        return (True, "ok", 0)

    async def mock_record_replan_attempt(user_id, plan_id):
        return None

    monkeypatch.setattr(service, "can_replan", mock_can_replan)
    monkeypatch.setattr(service, "record_replan_attempt", mock_record_replan_attempt)

    async def replan_callback():
        return new_plan

    result = await service.resolve_conflict(
        conflict_result=conflict,
        original_plan=plan,
        user_id=uuid.uuid4(),
        session_id="s1",
        user_message="msg",
        plan_id=uuid.uuid4(),
        replan_callback=replan_callback,
    )
    assert result.success is True
    assert result.new_plan is new_plan


@pytest.mark.asyncio
async def test_resolve_conflict_hitl():
    service = VersionConflictService(redis=None, plan_state_service=None, planner=None)
    plan = _build_plan()
    conflict = VersionConflictResult(has_conflict=True, recommendation="hitl", replan_confidence=0.5)
    result = await service.resolve_conflict(
        conflict_result=conflict,
        original_plan=plan,
        user_id=uuid.uuid4(),
        session_id="s1",
        user_message="msg",
        plan_id=uuid.uuid4(),
    )
    assert result.success is False
    assert result.requires_hitl is True
