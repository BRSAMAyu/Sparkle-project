"""S-02 Community Context Privacy Boundary —— 群上下文隐私红线守卫测试.

红线：群聊/小队的 AI prompt/tool 上下文**绝不能自动带入**私人 Memory/Profile；
唯一入口是 shared context allowlist（用户主动分享进群的 Goal/Action/Artifact，
真源 = 既有 SharedResource 群分享行，不重建真源）。

判据（卡面验收 headless 口径）：

1. 红线负向：未分享的私人 memory/profile 作为群 prompt 组装候选输入 → 断言
   被拒绝且归因明确（``group_context:not_in_allowlist`` 等）；同时证明既有
   私人 permission 面（M-03 prefilter，llm_context purpose）对 surface=group
   无感知 —— 同一批候选私人路径全放行，只有本卡群边界拦下（无守卫修前红）。
2. allowlist 正向：主动分享（PLAN/TASK/KNOWLEDGE_NODE 载体 → goal/action/
   artifact 三类）后正确进入群 prompt 上下文，payload 形状冻结、零私人字段。
3. revoke/离群：撤销分享（软删）或分享者退群后，下一次组装不再包含（时序：
   build → 有效 → 变更 → rebuild → 消失；陈旧 ctx 仍被逐候选归因拦截）。
4. 跨用户隔离：A 的私库对 B 的群上下文零泄漏；非成员 fail-closed；伪造
   owner 借道他人 share 行 → ``owner_mismatch``。

非目标（登记不修）：群 AI 面尚未存在（全仓无 group prompt 组装点），本卡交付
该面必须经过的唯一边界 + 复用纪律；不新增分享 UX、不动既有 share API。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.community import Group, GroupMember, GroupRole, GroupType, SharedResource, SharedResourceType
from app.models.goal import Goal
from app.models.memory import EpisodicMemory, MemoryPreference
from app.models.user import User
from app.services.collaboration_service import CollaborationService
from app.services.community_context_boundary import (
    GROUP_CONTEXT_BOUNDARY_VERSION,
    GROUP_CONTEXT_FILTER_DIMENSIONS,
    GROUP_CONTEXT_REJECTION_REASONS,
    SHARED_CONTEXT_KINDS,
    GroupContextBoundaryService,
    GroupContextCandidate,
    GroupContextFilterDimension,
    GroupPromptAccessContext,
    GroupSharedEntry,
    SharedContextKind,
    filter_group_prompt_candidates,
    group_tool_context_permits,
)
from app.services.memory_retrieval_prefilter import RetrievalContext, prefilter_candidates

NOW = datetime(2026, 9, 25, 12, 0, 0)


# ---------------------------------------------------------------------------
# seeds
# ---------------------------------------------------------------------------


async def _seed_user(db, tag: str) -> User:
    user = User(
        username=f"gcb_{tag}_{uuid4().hex[:8]}",
        email=f"gcb_{tag}_{uuid4().hex[:8]}@example.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_group(db, owner: User, *members: User) -> Group:
    group = Group(name=f"privacy-boundary-{uuid4().hex[:6]}", type=GroupType.SQUAD, is_public=True)
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    for m in members:
        db.add(GroupMember(group_id=group.id, user_id=m.id, role=GroupRole.MEMBER))
    await db.flush()
    return group


async def _seed_private_memory(db, user: User) -> tuple[EpisodicMemory, MemoryPreference, Goal]:
    """用户私人 episodic memory + 偏好 + 私人目标（真实 ORM 行，进库）。"""
    episodic = EpisodicMemory(
        user_id=user.id,
        summary="我最近失眠很严重，凌晨三点才睡得着",
        source_type="chat_turn",
        occurred_at=NOW,
    )
    pref = MemoryPreference(
        user_id=user.id,
        pref_key="study_time_preference",
        pref_value="深夜学习",
        version=1,
    )
    private_goal = Goal(user_id=user.id, title="考研上岸计划（私密）", goal_type="exam")
    db.add_all([episodic, pref, private_goal])
    await db.flush()
    return episodic, pref, private_goal


def _candidate(kind: str, item_id, owner) -> GroupContextCandidate:
    return GroupContextCandidate(item_kind=kind, item_id=str(item_id), owner_user_id=str(owner.id))


# ---------------------------------------------------------------------------
# 1. 红线负向：未分享私库不得进入群 prompt 组装输入
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unshared_private_memory_and_profile_rejected_from_group_prompt_input(db_session):
    """红线：A 的未分享私人 memory/profile 出现在群 prompt 组装输入 → 拒绝。

    两层归因：memory/profile 本就在群上下文词表外（goal/action/artifact 之外
    永不进入，``unknown_item_type``）；词表内的私人 goal 未显式分享同样被拒
    （``not_in_allowlist``）。

    修前红证据：该守卫模块不存在（全仓无 group 面 allowlist/过滤）——
    私人 llm_context 检索面可以原样产出这些候选且无任何层拦截（见下一用例）。
    """
    alice = await _seed_user(db_session, "alice")
    group = await _seed_group(db_session, alice)
    episodic, pref, private_goal = await _seed_private_memory(db_session, alice)

    ctx = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, alice.id)

    candidates = [
        _candidate("memory", episodic.id, alice),  # 未分享私人情景记忆
        _candidate("profile", pref.id, alice),  # 未分享私人偏好
        _candidate("preference", pref.id, alice),  # 词表外变体同样不允许
        _candidate("goal", private_goal.id, alice),  # 词表内但未分享的私人目标
    ]
    result = filter_group_prompt_candidates(candidates, ctx)

    assert result.allowed == []
    reasons = {r.reason for r in result.rejections}
    # memory/profile 类：群上下文只收 goal/action/artifact
    assert "group_context:unknown_item_type" in reasons
    # 词表内的私人 goal：未分享 → allowlist 之外
    assert "group_context:not_in_allowlist" in reasons
    assert all(r.detail for r in result.rejections)


@pytest.mark.asyncio
async def test_private_llm_context_path_is_surface_blind_group_boundary_is_the_gate(db_session):
    """自动带入路径实证：同一批私人候选，私人 permission 面（M-03）按
    llm_context 全放行（它对 surface=group 无感知，这是私人私聊面的正确
    行为），唯有群边界拒绝 —— 群组装不得走私人 permission 面，必须过本卡
    边界。修前：群边界不存在 → 私人路径产出即无守卫（红）。"""
    alice = await _seed_user(db_session, "carol")
    group = await _seed_group(db_session, alice)
    episodic, pref, _private_goal = await _seed_private_memory(db_session, alice)

    # 私人面：A 自己的 llm_context 检索 —— 私聊正确行为：放行
    private_ctx = RetrievalContext(user_id=str(alice.id), purpose="llm_context", now=NOW)
    m03 = prefilter_candidates([episodic, pref], private_ctx)
    assert m03.allowed_count == 2, "私人私聊面放行本人记忆是既有契约（不被本卡弱化）"

    # 群面：同样这批内容作为群 prompt 候选 —— 必须全拒
    group_ctx = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, alice.id)
    result = filter_group_prompt_candidates(
        [
            _candidate("memory", episodic.id, alice),
            _candidate("profile", pref.id, alice),
        ],
        group_ctx,
    )
    assert result.allowed == []
    assert {r.reason for r in result.rejections} == {"group_context:unknown_item_type"}


# ---------------------------------------------------------------------------
# 2. allowlist 正向：主动分享的项正确进入
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowlisted_shares_enter_group_prompt_context(db_session):
    alice = await _seed_user(db_session, "dave")
    bob = await _seed_user(db_session, "bob")
    group = await _seed_group(db_session, alice, bob)

    goal_id, action_id, artifact_id = uuid4(), uuid4(), uuid4()
    # 载体即既有分享真源：PLAN→goal / TASK→action / KNOWLEDGE_NODE→artifact
    for rtype, rid in (
        (SharedResourceType.PLAN, goal_id),
        (SharedResourceType.TASK, action_id),
        (SharedResourceType.KNOWLEDGE_NODE, artifact_id),
    ):
        await CollaborationService.share_resource(
            db_session, alice.id, rtype, rid, target_group_id=group.id, comment="一起加油"
        )
    await db_session.flush()

    ctx = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    entries = {e.kind: e for e in ctx.allowlist}
    assert set(entries) == {"goal", "action", "artifact"}
    assert entries["goal"].item_id == str(goal_id)
    assert entries["action"].item_id == str(action_id)
    assert entries["artifact"].item_id == str(artifact_id)
    assert all(e.owner_user_id == str(alice.id) for e in ctx.allowlist)

    payload = await GroupContextBoundaryService.resolve_prompt_context(db_session, group.id, bob.id)
    assert payload["schema_version"] == GROUP_CONTEXT_BOUNDARY_VERSION
    assert payload["entry_count"] == 3
    assert len(payload["entries"]) == 3
    for entry in payload["entries"]:
        # 冻结形状：只允许这七个键 —— 零私人 memory/profile 字段
        assert set(entry) == {
            "share_id",
            "kind",
            "item_id",
            "permission",
            "comment",
            "shared_by",
            "shared_at",
        }

    # 逐候选正向：类型化候选（owner=分享者）全放行
    result = filter_group_prompt_candidates(
        [
            _candidate("goal", goal_id, alice),
            _candidate("action", action_id, alice),
            _candidate("artifact", artifact_id, alice),
        ],
        ctx,
    )
    assert result.allowed_count == 3
    assert result.rejections == []

    # tool 面（Aurora group tool context）布尔判定
    assert group_tool_context_permits(ctx, item_kind="action", item_id=str(action_id), owner_user_id=str(alice.id))
    assert not group_tool_context_permits(ctx, item_kind="action", item_id=str(uuid4()), owner_user_id=str(alice.id))


@pytest.mark.asyncio
async def test_out_of_vocabulary_share_types_never_enter_group_prompt(db_session):
    """分享到群的认知碎片/种子等不在群 prompt 词表（goal/action/artifact 之外）：
    群资源 UI 可见是既有功能，但 AI 上下文不收。"""
    alice = await _seed_user(db_session, "eve")
    group = await _seed_group(db_session, alice)
    await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.COGNITIVE_FRAGMENT, uuid4(), target_group_id=group.id
    )
    await db_session.flush()

    ctx = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, alice.id)
    assert ctx.allowlist == set()
    payload = await GroupContextBoundaryService.resolve_prompt_context(db_session, group.id, alice.id)
    assert payload["entry_count"] == 0


# ---------------------------------------------------------------------------
# 3. revoke / 离群失效（时序）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoked_share_excluded_from_next_group_prompt_assembly(db_session):
    alice = await _seed_user(db_session, "frank")
    bob = await _seed_user(db_session, "gail")
    group = await _seed_group(db_session, alice, bob)
    action_id = uuid4()
    share = await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.TASK, action_id, target_group_id=group.id
    )
    await db_session.flush()

    before = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    assert before.allowlist and any(e.item_id == str(action_id) for e in before.allowlist)

    await GroupContextBoundaryService.revoke_share(db_session, share.id, revoked_by=alice.id)
    await db_session.flush()

    # 下一次组装（revoke 后重建快照）：消失
    after = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    assert not any(e.item_id == str(action_id) for e in after.allowlist)
    # 失效条目带精确原因（区别于「从未分享」的 not_in_allowlist）
    assert {i.reason for i in after.invalid_entries} == {"group_context:share_revoked"}
    # 滤芯层对含失效条目的上下文做生命周期维精确归因
    stale = filter_group_prompt_candidates([_candidate("action", action_id, alice)], after)
    assert stale.allowed == []
    assert {r.reason for r in stale.rejections} == {"group_context:share_revoked"}
    assert {r.dimension for r in stale.rejections} == {"lifecycle"}

    payload = await GroupContextBoundaryService.resolve_prompt_context(db_session, group.id, bob.id)
    assert payload["entry_count"] == 0


@pytest.mark.asyncio
async def test_sharer_leaving_group_invalidates_next_group_prompt_assembly(db_session):
    alice = await _seed_user(db_session, "henry")
    bob = await _seed_user(db_session, "iris")
    group = await _seed_group(db_session, alice, bob)
    goal_id = uuid4()
    await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.PLAN, goal_id, target_group_id=group.id
    )
    await db_session.flush()

    before = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    assert any(e.kind == "goal" for e in before.allowlist)

    # alice 退群（软删成员行，社群既有惯例）
    member_row = (
        await db_session.execute(
            select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == alice.id)
        )
    ).scalar_one()
    member_row.soft_delete()
    await db_session.flush()

    after = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    assert not any(e.kind == "goal" for e in after.allowlist)
    assert {i.reason for i in after.invalid_entries} == {"group_context:sharer_left_group"}

    # 滤芯层：分享者离群后候选 → sharer_left_group 精确归因（不与 revoked 混淆）
    stale = filter_group_prompt_candidates([_candidate("goal", goal_id, alice)], after)
    assert {r.reason for r in stale.rejections} == {"group_context:sharer_left_group"}
    assert {r.dimension for r in stale.rejections} == {"lifecycle"}


@pytest.mark.asyncio
async def test_requester_leaving_group_fails_closed(db_session):
    alice = await _seed_user(db_session, "jack")
    bob = await _seed_user(db_session, "kate")
    group = await _seed_group(db_session, alice, bob)
    await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.TASK, uuid4(), target_group_id=group.id
    )
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == bob.id)
        )
    ).scalar_one()
    row.soft_delete()
    await db_session.flush()

    from app.services.community_context_boundary import GroupContextPermissionError

    with pytest.raises(GroupContextPermissionError):
        await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, bob.id)
    with pytest.raises(GroupContextPermissionError):
        await GroupContextBoundaryService.resolve_prompt_context(db_session, group.id, bob.id)


# ---------------------------------------------------------------------------
# 4. 跨用户隔离：A 私库对 B 群上下文零泄漏
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_user_zero_leakage(db_session):
    alice = await _seed_user(db_session, "lara")
    bob = await _seed_user(db_session, "mallory")
    group = await _seed_group(db_session, alice, bob)

    # A 的私库（真实入库，B 的群组装不得触碰）
    episodic, pref, a_private_goal = await _seed_private_memory(db_session, alice)
    # A 只分享了一个 action
    action_id = uuid4()
    await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.TASK, action_id, target_group_id=group.id
    )
    await db_session.flush()

    payload = await GroupContextBoundaryService.resolve_prompt_context(db_session, group.id, bob.id)
    serialized = repr(payload)
    assert str(episodic.id) not in serialized
    assert str(pref.id) not in serialized
    assert str(a_private_goal.id) not in serialized
    assert "失眠" not in serialized and "深夜学习" not in serialized and "考研" not in serialized
    assert payload["entry_count"] == 1  # 只有显式分享的 action

    # B 的私库也不进 A 的组装（对称）：B 的未分享私人 memory 候选 → 全拒
    b_episodic, _b_pref, _b_goal = await _seed_private_memory(db_session, bob)
    ctx_a = await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, alice.id)
    leak = filter_group_prompt_candidates([_candidate("memory", b_episodic.id, bob)], ctx_a)
    assert leak.allowed == []
    assert {r.reason for r in leak.rejections} == {"group_context:unknown_item_type"}

    # A 的另一个未分享私人 goal（词表内）对 B 的组装同样不可见
    leak_goal = filter_group_prompt_candidates([_candidate("goal", a_private_goal.id, alice)], ctx_a)
    assert leak_goal.allowed == []
    assert {r.reason for r in leak_goal.rejections} == {"group_context:not_in_allowlist"}

    # 伪造：B 把自己的 id 填进 A 的 share 行（owner 与 share 行不符）→ owner_mismatch
    forged = filter_group_prompt_candidates(
        [GroupContextCandidate(item_kind="action", item_id=str(action_id), owner_user_id=str(bob.id))],
        ctx_a,
    )
    assert forged.allowed == []
    assert {r.reason for r in forged.rejections} == {"group_context:owner_mismatch"}

    # 非成员 C：fail-closed
    carol = await _seed_user(db_session, "carol_outside")
    from app.services.community_context_boundary import GroupContextPermissionError

    with pytest.raises(GroupContextPermissionError):
        await GroupContextBoundaryService.build_prompt_access_context(db_session, group.id, carol.id)


@pytest.mark.asyncio
async def test_revoke_authorization_requires_sharer_or_group_admin(db_session):
    alice = await _seed_user(db_session, "nancy")
    bob = await _seed_user(db_session, "oliver")
    carol = await _seed_user(db_session, "paula")
    group = await _seed_group(db_session, alice, bob, carol)  # alice=OWNER, bob/carol=MEMBER
    share = await CollaborationService.share_resource(
        db_session, alice.id, SharedResourceType.TASK, uuid4(), target_group_id=group.id
    )
    await db_session.flush()

    from app.services.community_context_boundary import GroupContextPermissionError

    # 无关成员不能撤别人的分享
    with pytest.raises(GroupContextPermissionError):
        await GroupContextBoundaryService.revoke_share(db_session, share.id, revoked_by=bob.id)
    # 分享者本人可撤
    await GroupContextBoundaryService.revoke_share(db_session, share.id, revoked_by=alice.id)
    await db_session.flush()
    row = await db_session.get(SharedResource, share.id)
    assert row.deleted_at is not None


# ---------------------------------------------------------------------------
# 5. 词汇/形状冻结（守卫演化纪律）
# ---------------------------------------------------------------------------


def test_reason_codes_frozen():
    assert (
        frozenset(
            {
                "group_context:no_group_surface",
                "group_context:requester_not_member",
                "group_context:unknown_item_type",
                "group_context:not_in_allowlist",
                "group_context:owner_mismatch",
                "group_context:share_revoked",
                "group_context:sharer_left_group",
            }
        )
        == GROUP_CONTEXT_REJECTION_REASONS
    )


def test_filter_dimensions_order_pinned():
    assert GROUP_CONTEXT_FILTER_DIMENSIONS == (
        GroupContextFilterDimension.IDENTITY,
        GroupContextFilterDimension.TYPE,
        GroupContextFilterDimension.SHARE,
        GroupContextFilterDimension.LIFECYCLE,
    )


def test_shared_context_kinds_frozen():
    assert frozenset({"goal", "action", "artifact"}) == SHARED_CONTEXT_KINDS
    assert SharedContextKind("goal")
    assert SharedContextKind("action")
    assert SharedContextKind("artifact")


def test_no_group_surface_fails_closed():
    """不给群权限上下文 = 无放行依据（私人路径对象不得蒙混进群组装）。"""
    candidate = GroupContextCandidate(item_kind="action", item_id=str(uuid4()), owner_user_id=str(uuid4()))
    result = filter_group_prompt_candidates([candidate], None)
    assert result.allowed == []
    assert {r.reason for r in result.rejections} == {"group_context:no_group_surface"}


def test_requester_not_member_rejected_before_share_lookup():
    member = str(uuid4())
    outsider = str(uuid4())
    entry = GroupSharedEntry(
        kind="action",
        item_id=str(uuid4()),
        owner_user_id=member,
        share_id=str(uuid4()),
        permission="view",
        comment="",
        shared_at=None,
    )
    ctx = GroupPromptAccessContext(
        group_id=str(uuid4()),
        requester_id=outsider,
        active_member_ids=frozenset({member}),
        allowlist=frozenset({entry}),
    )
    candidate = GroupContextCandidate(item_kind="action", item_id=entry.item_id, owner_user_id=member)
    result = filter_group_prompt_candidates([candidate], ctx)
    assert result.allowed == []
    assert {r.reason for r in result.rejections} == {"group_context:requester_not_member"}


def test_stale_share_with_expired_timestamp_still_governed_by_revoke_only():
    """shared_at 只是元数据：时效不在这里判（TTL 属 memory 面 M-03），
    群边界唯一的失效开关是 revoke/离群 —— 旧分享不因时间自动过期。"""
    member = str(uuid4())
    entry = GroupSharedEntry(
        kind="goal",
        item_id=str(uuid4()),
        owner_user_id=member,
        share_id=str(uuid4()),
        permission="view",
        comment="",
        shared_at=(NOW - timedelta(days=365)).isoformat(),
    )
    ctx = GroupPromptAccessContext(
        group_id=str(uuid4()),
        requester_id=member,
        active_member_ids=frozenset({member}),
        allowlist=frozenset({entry}),
    )
    candidate = GroupContextCandidate(item_kind="goal", item_id=entry.item_id, owner_user_id=member)
    result = filter_group_prompt_candidates([candidate], ctx)
    assert result.allowed_count == 1


def test_metric_payload_shape_parity_with_m03():
    member = str(uuid4())
    entry = GroupSharedEntry(
        kind="action",
        item_id=str(uuid4()),
        owner_user_id=member,
        share_id=str(uuid4()),
        permission="view",
        comment="",
        shared_at=None,
    )
    ctx = GroupPromptAccessContext(
        group_id=str(uuid4()),
        requester_id=member,
        active_member_ids=frozenset({member}),
        allowlist=frozenset({entry}),
    )
    hit = GroupContextCandidate(item_kind="action", item_id=entry.item_id, owner_user_id=member)
    miss = GroupContextCandidate(item_kind="action", item_id=str(uuid4()), owner_user_id=member)
    result = filter_group_prompt_candidates([hit, miss], ctx)
    payload = result.to_metric_payload()
    assert set(payload) == {"version", "input_count", "allowed_count", "dimension_counts", "reason_counts"}
    assert payload["input_count"] == 2
    assert payload["allowed_count"] == 1
    assert payload["reason_counts"] == {"group_context:not_in_allowlist": 1}
    # Rejection 形状与 M-03 同源（record_id/dimension/reason/detail）
    rejection = result.rejections[0]
    assert set(rejection.__dict__) == {"record_id", "dimension", "reason", "detail"}
