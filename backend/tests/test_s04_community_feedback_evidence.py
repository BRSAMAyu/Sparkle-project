"""S-04 · Community Artifact Feedback → Outcome/Evidence 定向测试。

覆盖（v3/07_tasks/cards/S-04.md 验收 + Forbidden）：
1. 反馈/ack **不自动成为 mastery**（Galaxy mastery / Goal.mastery 不动）；
2. 主人显式采纳 → Goal.metadata 轨迹回执 + services/evidence 证据构建；
3. 撤回传播：共享软删 → 活跃反馈标 retracted + Goal 派生回执标 retracted；
4. check-in 可选关联 Goal（GJ16 从 check-in 回到 Goal trajectory 的回链）；
5. goal_router 的 community_evidence 轨迹投影（含撤回态）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.community import (
    Group,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    MessageType,
    SharedResource,
    SharedResourceFeedback,
    SharedResourceType,
)
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskType
from app.models.user import User
from app.schemas.community import CheckinRequest, FeedbackVerdict
from app.services.community_feedback_service import SharedResourceFeedbackService
from app.services.community_service import CheckinService
from app.api.v1.experience.goal_router import _community_evidence_payload


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _make_user(db, name: str) -> User:
    user = User(
        username=f"s04_{name}_{uuid4().hex[:8]}",
        nickname=f"用户{name}",
        email=f"s04_{name}_{uuid4().hex[:8]}@example.com",
        hashed_password="hash",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_group_with_member(db, owner: User, member: User) -> Group:
    group = Group(name="S-04 测试群", type=GroupType.SQUAD)
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    db.add(GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER))
    await db.flush()
    return group


async def _make_shared_task(db, owner: User, group: Group, *, with_goal: bool = True) -> tuple[SharedResource, Goal | None]:
    goal: Goal | None = None
    plan: Plan | None = None
    if with_goal:
        goal = Goal(user_id=owner.id, title="S-04 目标：完成作品集", status="active", mastery=0.2, progress=0.1)
        db.add(goal)
        await db.flush()
        plan = Plan(user_id=owner.id, goal_id=goal.id, name="作品集计划", type=PlanType.SPRINT)
        db.add(plan)
        await db.flush()
        goal.plan_id = plan.id
        db.add(goal)
        await db.flush()
    task = Task(
        user_id=owner.id,
        plan_id=plan.id if plan is not None else None,
        title="作品集第一章",
        type=TaskType.LEARNING,
        estimated_minutes=45,
    )
    db.add(task)
    await db.flush()
    shared = SharedResource(
        group_id=group.id,
        shared_by=owner.id,
        task_id=task.id,
        plan_id=plan.id if plan is not None else None,
        permission="view",
    )
    db.add(shared)
    await db.flush()
    return shared, goal


@pytest.fixture(name="two_users")
async def two_users_fixture(db_session):
    owner = await _make_user(db_session, "owner")
    peer = await _make_user(db_session, "peer")
    await db_session.commit()
    return owner, peer


# =============================================================================
# 1. 反馈不自动成为 mastery（Forbidden 守卫）
# =============================================================================


@pytest.mark.asyncio
async def test_give_feedback_persists_without_any_mastery_change(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    shared, goal = await _make_shared_task(db_session, owner, group)
    await db_session.commit()

    feedback = await SharedResourceFeedbackService.give_feedback(
        db_session,
        resource_id=shared.id,
        user=peer,
        verdict=FeedbackVerdict.HELPFUL,
        comment="第一章结构很清楚",
    )
    await db_session.commit()

    assert feedback.verdict == "helpful"
    assert feedback.adopted_at is None  # 未采纳
    assert feedback.retracted_at is None

    # 守卫：反馈后 Galaxy mastery 面与 Goal mastery/progress 全部不动。
    refreshed_goal = await db_session.get(Goal, goal.id)
    assert refreshed_goal.mastery == 0.2
    assert refreshed_goal.progress == 0.1
    assert refreshed_goal.metadata_payload is None  # 无任何证据回执写入


@pytest.mark.asyncio
async def test_feedback_upsert_and_self_feedback_guard(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    shared, _ = await _make_shared_task(db_session, owner, group, with_goal=False)
    await db_session.commit()

    first = await SharedResourceFeedbackService.give_feedback(
        db_session, resource_id=shared.id, user=peer, verdict=FeedbackVerdict.HELPFUL, comment=None
    )
    second = await SharedResourceFeedbackService.give_feedback(
        db_session, resource_id=shared.id, user=peer, verdict=FeedbackVerdict.INSIGHTFUL, comment="有启发"
    )
    assert first.id == second.id  # 一人一资源一条：upsert
    assert second.verdict == "insightful"

    with pytest.raises(ValueError, match="不能给自己的共享成果反馈"):
        await SharedResourceFeedbackService.give_feedback(
            db_session, resource_id=shared.id, user=owner, verdict=FeedbackVerdict.HELPFUL, comment=None
        )


# =============================================================================
# 2. 显式采纳 → Goal 轨迹回执 + 证据构建（不改 mastery）
# =============================================================================


@pytest.mark.asyncio
async def test_adopt_feedback_writes_goal_receipt_and_resolves_goal_via_plan(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    shared, goal = await _make_shared_task(db_session, owner, group)
    await SharedResourceFeedbackService.give_feedback(
        db_session, resource_id=shared.id, user=peer, verdict=FeedbackVerdict.APPLIED, comment="照做后真的顺了"
    )
    await db_session.commit()

    result = await SharedResourceFeedbackService.adopt_feedback(
        db_session,
        resource_id=shared.id,
        feedback_id=await _feedback_id(db_session, shared.id),
        owner=owner,
    )
    await db_session.commit()

    assert result["already_adopted"] is False
    resolved_goal: Goal = result["goal"]
    assert resolved_goal.id == goal.id  # 经 plan→goal 链解析

    receipts = (resolved_goal.metadata_payload or {}).get("community_evidence")
    assert len(receipts) == 1
    assert receipts[0]["kind"] == "peer_feedback"
    assert receipts[0]["verdict"] == "applied"
    assert receipts[0]["status"] == "adopted"
    assert receipts[0]["shared_resource_id"] == str(shared.id)

    # 采纳后 Goal mastery/progress 仍不动（采纳 ≠ mastery）
    refreshed = await db_session.get(Goal, goal.id)
    assert refreshed.mastery == 0.2
    assert refreshed.progress == 0.1


async def _feedback_id(db, resource_id) -> object:
    from sqlalchemy import select as _select

    result = await db.execute(
        _select(SharedResourceFeedback.id).where(SharedResourceFeedback.shared_resource_id == resource_id)
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_adopt_is_idempotent_and_owner_only(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    shared, _ = await _make_shared_task(db_session, owner, group)
    await SharedResourceFeedbackService.give_feedback(
        db_session, resource_id=shared.id, user=peer, verdict=FeedbackVerdict.HELPFUL, comment=None
    )
    await db_session.commit()
    feedback_id = await _feedback_id(db_session, shared.id)

    first = await SharedResourceFeedbackService.adopt_feedback(
        db_session, resource_id=shared.id, feedback_id=feedback_id, owner=owner
    )
    second = await SharedResourceFeedbackService.adopt_feedback(
        db_session, resource_id=shared.id, feedback_id=feedback_id, owner=owner
    )
    assert first["already_adopted"] is False
    assert second["already_adopted"] is True  # 幂等：不重复注入证据

    with pytest.raises(PermissionError):
        await SharedResourceFeedbackService.adopt_feedback(
            db_session, resource_id=shared.id, feedback_id=feedback_id, owner=peer
        )


# =============================================================================
# 3. 撤回传播：共享软删 + 反馈标撤回 + Goal 回执标 retracted
# =============================================================================


@pytest.mark.asyncio
async def test_retract_propagates_to_feedback_and_goal_receipt(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    shared, goal = await _make_shared_task(db_session, owner, group)
    await SharedResourceFeedbackService.give_feedback(
        db_session, resource_id=shared.id, user=peer, verdict=FeedbackVerdict.HELPFUL, comment=None
    )
    await db_session.commit()
    feedback_id = await _feedback_id(db_session, shared.id)
    await SharedResourceFeedbackService.adopt_feedback(
        db_session, resource_id=shared.id, feedback_id=feedback_id, owner=owner
    )
    await db_session.commit()

    # 非主人撤回被拒（活跃共享上验证 owner-only 守卫）
    with pytest.raises(PermissionError):
        await SharedResourceFeedbackService.retract_share(db_session, resource_id=shared.id, owner=peer)

    result = await SharedResourceFeedbackService.retract_share(db_session, resource_id=shared.id, owner=owner)
    await db_session.commit()

    assert result["retracted_feedback_count"] == 1
    assert result["updated_goal_receipt_count"] == 1

    # 共享本体软删（读面过滤）
    refreshed_shared = await db_session.get(SharedResource, shared.id)
    assert refreshed_shared.deleted_at is not None

    # 派生引用①：反馈行标 retracted，且随共享不可达而不可再采纳
    refreshed_feedback = await db_session.get(SharedResourceFeedback, feedback_id)
    assert refreshed_feedback.retracted_at is not None
    with pytest.raises(ValueError, match="共享资源不存在"):
        await SharedResourceFeedbackService.adopt_feedback(
            db_session, resource_id=shared.id, feedback_id=feedback_id, owner=owner
        )

    # 派生引用②：Goal 轨迹回执标 retracted（不静默消失，审计可查）
    refreshed_goal = await db_session.get(Goal, goal.id)
    receipts = (refreshed_goal.metadata_payload or {}).get("community_evidence")
    assert receipts[0]["status"] == "retracted"
    assert receipts[0]["retracted_at"] is not None

    # 幂等：二次撤回按不存在处理（软删后读面不可达）
    with pytest.raises(ValueError, match="共享资源不存在"):
        await SharedResourceFeedbackService.retract_share(db_session, resource_id=shared.id, owner=owner)


# =============================================================================
# 4. check-in 关联 Goal（GJ16 回链）
# =============================================================================


@pytest.mark.asyncio
async def test_checkin_with_goal_link_writes_content_data_and_response(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    goal = Goal(user_id=owner.id, title="GJ16 目标", status="active")
    db_session.add(goal)
    await db_session.commit()

    result = await CheckinService.checkin(
        db_session,
        owner.id,
        CheckinRequest(group_id=group.id, today_duration_minutes=60, goal_id=goal.id, message="今天推进了"),
    )
    assert result["goal_id"] == str(goal.id)
    assert result["goal_title"] == "GJ16 目标"

    message_result = await db_session.execute(
        select(GroupMessage).where(
            GroupMessage.group_id == group.id, GroupMessage.message_type == MessageType.CHECKIN
        )
    )
    message = message_result.scalar_one()
    assert message.content_data["goal_id"] == str(goal.id)
    assert message.content_data["goal_title"] == "GJ16 目标"


@pytest.mark.asyncio
async def test_checkin_with_foreign_goal_rejected(db_session, two_users):
    owner, peer = two_users
    group = await _make_group_with_member(db_session, owner, peer)
    foreign_goal = Goal(user_id=peer.id, title="别人的目标", status="active")
    db_session.add(foreign_goal)
    await db_session.commit()

    with pytest.raises(ValueError, match="不属于当前用户"):
        await CheckinService.checkin(
            db_session,
            owner.id,
            CheckinRequest(group_id=group.id, today_duration_minutes=30, goal_id=foreign_goal.id),
        )


# =============================================================================
# 5. goal_router community_evidence 轨迹投影
# =============================================================================


@pytest.mark.asyncio
async def test_community_evidence_projection_active_and_rejected(db_session, two_users):
    owner, _ = two_users
    goal = Goal(user_id=owner.id, title="轨迹目标", status="active")
    db_session.add(goal)
    await db_session.commit()

    goal.metadata_payload = {
        "community_evidence": [
            {
                "kind": "peer_feedback",
                "feedback_id": str(uuid4()),
                "shared_resource_id": str(uuid4()),
                "verdict": "helpful",
                "peer_alias": "同伴A",
                "adopted_at": "2026-09-24T10:00:00",
                "status": "adopted",
            },
            {
                "kind": "peer_feedback",
                "feedback_id": str(uuid4()),
                "shared_resource_id": str(uuid4()),
                "verdict": "applied",
                "peer_alias": "同伴B",
                "adopted_at": "2026-09-23T10:00:00",
                "status": "retracted",
                "retracted_at": "2026-09-24T11:00:00",
            },
            "corrupted-entry",  # 非 dict 条目诚实丢弃
        ]
    }
    receipts = _community_evidence_payload(goal)
    assert [r.status for r in receipts] == ["adopted", "retracted"]
    assert receipts[1].retracted_at == "2026-09-24T11:00:00"

    assert _community_evidence_payload(None) == []


# =============================================================================
# 6. 证据适配器（services/evidence 既有链）
# =============================================================================


def test_peer_feedback_evidence_adapter_builds_self_reported_belief_evidence():
    from app.services.evidence import build_peer_feedback_evidence
    from app.services.evidence.unified_evidence import EvidenceDirection, EvidenceSourceType, EvidenceTarget

    items = build_peer_feedback_evidence(
        {
            "feedback_id": "fb-1",
            "shared_resource_id": "sr-1",
            "goal_id": "g-1",
            "verdict": "insightful",
            "comment": "这个角度没想过",
            "feedback_giver_alias": "同伴A",
        }
    )
    assert len(items) == 1
    evidence = items[0]
    assert evidence.source_type == EvidenceSourceType.OUTCOME
    assert evidence.target_latent_variable == EvidenceTarget.EXECUTION_CAPACITY
    assert evidence.direction == EvidenceDirection.INCREASE
    assert evidence.metadata["adopted_from"] == "community_feedback"
    assert evidence.metadata["truth_class"] == "self_reported"  # 诚实档位：社会证据非服务器观察
    assert evidence.metadata["goal_id"] == "g-1"

    assert build_peer_feedback_evidence({"verdict": "unknown-verdict"}) == []
