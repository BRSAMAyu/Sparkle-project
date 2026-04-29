from __future__ import annotations

import pytest

from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.card_protocol.consistency_validator import CardProtocolConsistencyValidator
from app.services.card_protocol.legacy_adapter import PlanAdapter, TaskAdapter


async def _make_plan_and_task(db_session, user_id):
    plan = Plan(
        user_id=user_id,
        name="Consistency Plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()
    task = Task(
        user_id=user_id,
        plan_id=plan.id,
        title="Consistency Task",
        type=TaskType.LEARNING,
        estimated_minutes=25,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=0,
        order_index=1000,
    )
    db_session.add(task)
    await db_session.commit()
    return plan, task


@pytest.mark.asyncio
async def test_card_protocol_consistency_validator_reports_missing_projections(db_session, test_user):
    await _make_plan_and_task(db_session, test_user.id)

    issues = await CardProtocolConsistencyValidator(db_session).validate()

    codes = {issue.code for issue in issues}
    assert "missing_plan_card" in codes
    assert "missing_task_card" in codes


@pytest.mark.asyncio
async def test_card_protocol_consistency_validator_accepts_legacy_adapter_projection(db_session, test_user):
    plan, task = await _make_plan_and_task(db_session, test_user.id)
    await PlanAdapter(db_session).plan_to_card(plan)
    await TaskAdapter(db_session).task_to_card(task)
    await db_session.commit()

    issues = await CardProtocolConsistencyValidator(db_session).validate()

    assert issues == []
