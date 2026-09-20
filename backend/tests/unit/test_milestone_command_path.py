"""X-03 R2 P2-1 返修 · milestone 入口全链接线权威 command path 的集成测试.

返修前缺陷（REPORT §1 本卡动机）：``MilestoneHandler.confirm_proposal`` 走
pending_actions 的 get→create×N→delete——非原子，双确认竞窗内**重复建任务**，
且新权威路径是「建好但无人走的路」（R2 全仓 grep 零真实调用方）。

返修后全链（本测试钉住的链路）：
    task 完成 → task_state_sync → MilestoneHandler.on_milestone_achieved
    → ActionCommandService.create_proposal(task.create_batch, source=system)
    → **action_proposals 行落账** → 用户 confirm_proposal
    → ActionCommandService.approve（恰一次 commit + receipt）
    → TaskService.create×N（领域写）。

双确认/崩溃重放由协议恰一次语义根治：重复确认重放 already_committed，
任务数不翻倍。
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select, text

from app.models.action_proposal import ActionProposal, ActionProposalTransition
from app.models.task import Task
from app.models.user import User
from app.services.action_command_service import ActionCommandService
from app.services.milestone_handler import MilestoneHandler
from tests.unit.test_action_command_service import (
    _OUTBOX_DDL,
    _committed_transitions,
    _make_user,
)


async def _outbox_count(db_session, event_type: str) -> int:
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM event_outbox WHERE event_type = :t"), {"t": event_type}
    )
    return int(result.scalar_one())


async def _achieve_milestone(db_session, user: User, plan_id) -> str | None:
    """真实入口：任务完成后的里程碑触发（LLM 故障 → 规则模板回退，零真实 LLM）."""
    handler = MilestoneHandler(db_session)
    with patch(
        "app.services.milestone_handler.get_llm_service_for_task",
        side_effect=RuntimeError("llm unavailable in test"),
    ):
        return await handler.on_milestone_achieved(
            user_id=user.id,
            plan_id=plan_id,
            milestone={"id": "ms-25pct-completion", "title": "25% 完成"},
            pending_task_count=0,
            current_plan_context={"title": "考研数学一轮", "task_index": {"completed": 10}},
        )


async def test_milestone_entry_lands_authoritative_proposal(db_session):
    """里程碑触发 → action_proposals 行落账（source=system，task.create_batch）."""
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()

    user = await _make_user(db_session)
    plan_id = uuid4()

    action_id = await _achieve_milestone(db_session, user, plan_id)
    assert action_id, "milestone should produce a proposal"

    service = ActionCommandService(db_session)
    proposal = await service.get_proposal(action_id, user_id=user.id)
    assert proposal.command_type == "task.create_batch"
    assert proposal.source == "system"
    assert proposal.status.value == "PENDING"
    assert proposal.idempotency_key == f"milestone:ms-25pct-completion:{plan_id}"
    assert proposal.diff["after"]["count"] == 3  # 规则模板 3 任务
    assert proposal.risk_class == "low"
    assert proposal.reversible == "false"
    # 确认卡数据面可渲染
    assert proposal.summary and "推荐" in proposal.summary


async def test_milestone_retrigger_idempotent_single_proposal(db_session):
    """同 (milestone, plan) 重复触发 → 恰一条 proposal（幂等键收敛）."""
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()

    user = await _make_user(db_session)
    plan_id = uuid4()

    first = await _achieve_milestone(db_session, user, plan_id)
    second = await _achieve_milestone(db_session, user, plan_id)
    assert first == second

    rows = list(
        (await db_session.execute(select(ActionProposal).where(ActionProposal.user_id == user.id))).scalars().all()
    )
    assert len(rows) == 1
    assert await _outbox_count(db_session, "action.proposed") == 1


async def test_milestone_confirm_double_confirm_exactly_once(db_session):
    """返修核心断言：双确认恰一次建任务（V2 缺陷根治）+ receipt 权威 + 审计恰一行."""
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()

    user = await _make_user(db_session)
    plan_id = uuid4()
    handler = MilestoneHandler(db_session)

    action_id = await _achieve_milestone(db_session, user, plan_id)
    assert action_id

    # 第一次确认：3 个任务建成
    first = await handler.confirm_proposal(action_id, str(user.id))
    assert first["success"] is True
    assert first["tasks_created"] == 3
    assert len(first["tasks"]) == 3
    assert all(t["id"] for t in first["tasks"])

    # 双确认（原缺陷：竞窗内重复建任务）：重放，任务数不翻倍
    second = await handler.confirm_proposal(action_id, str(user.id))
    assert second["success"] is True
    assert second["tasks_created"] == 3
    assert second["tasks"] == first["tasks"]

    # 领域恰一次：3 个任务（不是 6），plan 归属正确
    tasks = list(
        (await db_session.execute(select(Task).where(Task.user_id == user.id).order_by(Task.created_at.asc())))
        .scalars()
        .all()
    )
    assert len(tasks) == 3
    assert {t.plan_id for t in tasks} == {plan_id}

    # proposal 终态 + receipt + 恰一行 COMMITTED 审计 + 恰一条 action.accepted
    service = ActionCommandService(db_session)
    proposal = await service.get_proposal(action_id, user_id=user.id)
    assert proposal.status.value == "COMMITTED"
    receipt = await service.get_receipt(action_id, user_id=user.id)
    assert receipt["effects"][0]["kind"] == "task.created_batch"
    assert receipt["effects"][0]["count"] == 3
    assert len(await _committed_transitions(db_session, action_id)) == 1
    assert await _outbox_count(db_session, "action.accepted") == 1

    # 审计轨迹完整（PENDING → COMMITTED）
    transitions = list(
        (
            await db_session.execute(
                select(ActionProposalTransition)
                .where(ActionProposalTransition.proposal_id == proposal.id)
                .order_by(ActionProposalTransition.occurred_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [t.to_status for t in transitions] == ["PENDING", "COMMITTED"]


async def test_milestone_confirm_unknown_proposal_legacy_shape(db_session):
    """不存在的 proposal → 旧契约错误形态（success=False）."""
    handler = MilestoneHandler(db_session)
    result = await handler.confirm_proposal(str(uuid4()), str(uuid4()))
    assert result["success"] is False
    assert "not found" in result["error"].lower()
