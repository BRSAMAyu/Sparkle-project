"""WT378-08 复核修复（wt379 轮2）：edit 链事务边界——旧提案不得先于替代提案被销毁.

轮1猎缺 + 轮2独立复核 CONFIRMED 的机制：``edit_first_action_proposal`` 曾按
「①reject（``_terminal_user_action`` 内部 commit，旧提案立即持久化为 REJECTED）
→ ②collect_first_action_context（可抛 NoActiveGoalError）→ ③create_proposal
（可失败）」执行。②/③ 任一失败时旧提案已被不可逆销毁且无替代提案——用户的
first-action 从「有待确认提案」退化为「空」，API 返回 422/5xx 但状态已损毁。

修复契约（先门控+重建、成功后才拒绝旧提案；拒绝失败可补偿）：
- goal 非 active 门控（NoActiveGoalError）在任何写之前——422 时旧提案仍 PENDING；
- create_proposal 失败时旧提案仍 PENDING；
- reject 失败时补偿 cancel 新提案（回到「旧 PENDING」可重试态）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import ProposalStatus
from app.models.action_proposal import ActionProposal
from app.models.memory import MemoryGoal
from app.services.action_command_service import ActionCommandService
from tests.unit.test_action_command_service import _OUTBOX_DDL, _make_user


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


_EDIT_SPEC = {
    "tasks": [
        {
            "title": "写下第一期选题",
            "type": "learning",
            "estimated_minutes": 20,
            "success_criteria": "第一期选题草稿",
        }
    ]
}


async def _seed_pending_first_action_proposal(db_session: AsyncSession, user) -> ActionProposal:
    service = ActionCommandService(db_session)
    created = await service.create_proposal(
        user_id=user.id,
        command_type="task.create_batch",
        payload=_EDIT_SPEC,
        source="aurora",
        idempotency_key=f"first_action:seed:{user.id}",
        summary="第一步：写下第一期选题",
        trace_id="first_action",
    )
    return created.proposal


async def _seed_active_goal(db_session: AsyncSession, user) -> MemoryGoal:
    goal = MemoryGoal(
        user_id=user.id,
        title="持续产出播客",
        status="active",
        source_type="user_state",
        metadata_payload={"goal_type": "creator"},
    )
    db_session.add(goal)
    await db_session.commit()
    return goal


async def _old_proposal(db_session: AsyncSession, proposal_id) -> ActionProposal:
    return (await db_session.execute(select(ActionProposal).where(ActionProposal.id == proposal_id))).scalars().one()


@pytest.mark.asyncio
async def test_edit_with_inactive_goal_keeps_old_proposal_pending(db_session: AsyncSession, outbox_tables) -> None:
    """goal 在提案存活期间被 retract：edit 报 NoActiveGoalError，旧提案必须仍 PENDING。

    修前顺序缺陷：reject（含 commit）先执行 → 旧提案已 REJECTED，随后 collect
    才抛 NoActiveGoalError——422 响应背后旧提案已不可逆损毁。
    """
    from app.services.first_action_service import NoActiveGoalError, edit_first_action_proposal

    user = await _make_user(db_session)
    await _seed_active_goal(db_session, user)
    old = await _seed_pending_first_action_proposal(db_session, user)

    goal = (await db_session.execute(select(MemoryGoal).where(MemoryGoal.user_id == user.id))).scalars().one()
    goal.status = "retracted"
    goal.retracted_at = goal.created_at
    await db_session.commit()

    with pytest.raises(NoActiveGoalError):
        await edit_first_action_proposal(
            db_session,
            user_id=user.id,
            proposal_id=old.id,
            edited_fields={"title": "列出 5 个身边可聊的人选"},
        )

    old_after = await _old_proposal(db_session, old.id)
    assert (
        old_after.status is ProposalStatus.PENDING
    ), f"edit 失败（goal 非 active）后旧提案被损毁为 {old_after.status}——非原子销毁仍存在"


@pytest.mark.asyncio
async def test_edit_with_create_failure_keeps_old_proposal_pending(
    db_session: AsyncSession, outbox_tables, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_proposal 失败（任意 DB 错误）：旧提案必须仍 PENDING，可重试。"""
    from app.services import first_action_service

    user = await _make_user(db_session)
    await _seed_active_goal(db_session, user)
    old = await _seed_pending_first_action_proposal(db_session, user)

    async def _broken_create(self, **_kwargs):
        raise RuntimeError("db error during re-propose (probe)")

    monkeypatch.setattr(ActionCommandService, "create_proposal", _broken_create)

    with pytest.raises(RuntimeError):
        await first_action_service.edit_first_action_proposal(
            db_session,
            user_id=user.id,
            proposal_id=old.id,
            edited_fields={"title": "缩小第一步"},
        )

    old_after = await _old_proposal(db_session, old.id)
    assert (
        old_after.status is ProposalStatus.PENDING
    ), f"create_proposal 失败后旧提案被损毁为 {old_after.status}——非原子销毁仍存在"
