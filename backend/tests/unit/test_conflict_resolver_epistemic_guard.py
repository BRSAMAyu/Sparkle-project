"""M-01 写守卫（conflict 域）：自动冲突裁决不得让推断记录压掉显式记录。

apply_live_decision 是对既有行做 retraction 的变更点；守卫必须落在变更点
（defense in depth），而不仅依赖 resolve() 的 lane 算术 —— 该方法是公开 API，
M-04 接线 Context 后将有更多调用方。用户仲裁（arbitrate_unresolved_conflict）
是显式人类动作，不经过本守卫，保持最高权限。
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services.conflict_resolver_service import ConflictCandidate, ConflictResolverService, ResolutionDecision


async def _create_user(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _add_episodic(db_session, *, user_id, lane, confidence, semantic_key, summary):
    record = EpisodicMemory(
        user_id=user_id,
        summary=summary,
        source_type="chat",
        source_id="session-1",
        source_lane=lane,
        subject_type="self",
        occurred_at=datetime(2026, 9, 19, 10, 0, 0),
        confidence=confidence,
        evidence_refs=[{"type": "chat_turn", "id": f"turn-{lane}"}],
        evidence_token=f"turn-{lane}",
        semantic_key=semantic_key,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.mark.asyncio
async def test_apply_live_decision_refuses_inferred_winner_over_explicit_loser(db_session):
    """推断 winner 的 accept 决策不得 retract/supersede 显式 lane 的 loser。"""
    user = await _create_user(db_session)
    explicit_record = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="direct_capture",
        confidence=0.7,
        semantic_key="guard-key-1",
        summary="用户明确说的事实",
    )
    new_record = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="inferred_extraction",
        confidence=0.95,
        semantic_key="guard-key-1",
        summary="系统推断的矛盾候选",
    )

    service = ConflictResolverService(db_session)
    # 构造一个"越权"决策：winner 是推断 lane，loser 是显式记录。
    # 正常 resolve() 算术不会产出这种决策（这正是守卫存在的意义：
    # apply_live_decision 是公开变更点，不能信任所有调用方）。
    decision = ResolutionDecision(
        action="accept",
        reason="candidate_overrides_lower_priority",
        winner_lane="inferred_extraction",
        loser_record_ids=(explicit_record.id,),
        loser_lanes=("direct_capture",),
        evidence_tokens=("turn-x",),
        conflict_key="guard-key-1",
    )
    await service.apply_live_decision(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="系统推断的矛盾候选",
            source_lane="inferred_extraction",
            confidence=0.95,
            occurred_at=datetime(2026, 9, 19, 11, 0, 0),
            evidence_token="turn-x",
            semantic_key="guard-key-1",
        ),
        decision=decision,
        new_record=new_record,
    )

    await db_session.refresh(explicit_record)
    # 守卫生效：显式事实未被撤回、未被 supersede。
    assert explicit_record.retracted_at is None
    assert explicit_record.superseded_by_id is None


@pytest.mark.asyncio
async def test_apply_live_decision_allows_higher_lane_winner_to_supersede_lower(db_session):
    """合法路径不回归：显式 winner 正常 supersede 推断 loser，并落 supersede 链。"""
    user = await _create_user(db_session)
    inferred_record = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="inferred_extraction",
        confidence=0.9,
        semantic_key="guard-key-2",
        summary="旧的推断",
    )
    new_record = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="direct_capture",
        confidence=0.9,
        semantic_key="guard-key-2",
        summary="用户更正后的事实",
    )

    service = ConflictResolverService(db_session)
    decision = ResolutionDecision(
        action="accept",
        reason="candidate_overrides_lower_priority",
        winner_lane="direct_capture",
        loser_record_ids=(inferred_record.id,),
        loser_lanes=("inferred_extraction",),
        evidence_tokens=("turn-y",),
        conflict_key="guard-key-2",
    )
    await service.apply_live_decision(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="用户更正后的事实",
            source_lane="direct_capture",
            confidence=0.9,
            occurred_at=datetime(2026, 9, 19, 11, 0, 0),
            evidence_token="turn-y",
            semantic_key="guard-key-2",
        ),
        decision=decision,
        new_record=new_record,
    )

    await db_session.refresh(inferred_record)
    assert inferred_record.retracted_at is not None
    # supersede 链：败者指向胜者（与 memory_preferences.replaced_by_id 对称）。
    assert inferred_record.superseded_by_id == new_record.id


@pytest.mark.asyncio
async def test_apply_live_decision_same_lane_supersede_allowed(db_session):
    """同 lane（推断 vs 推断）的裁决不受守卫影响。"""
    user = await _create_user(db_session)
    older = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="inferred_extraction",
        confidence=0.7,
        semantic_key="guard-key-3",
        summary="旧推断",
    )
    newer = await _add_episodic(
        db_session,
        user_id=user.id,
        lane="inferred_extraction",
        confidence=0.9,
        semantic_key="guard-key-3",
        summary="新推断",
    )

    service = ConflictResolverService(db_session)
    decision = ResolutionDecision(
        action="accept",
        reason="candidate_overrides_lower_priority",
        winner_lane="inferred_extraction",
        loser_record_ids=(older.id,),
        loser_lanes=("inferred_extraction",),
        evidence_tokens=("turn-z",),
        conflict_key="guard-key-3",
    )
    await service.apply_live_decision(
        candidate=ConflictCandidate(
            user_id=user.id,
            summary="新推断",
            source_lane="inferred_extraction",
            confidence=0.9,
            occurred_at=datetime(2026, 9, 19, 11, 0, 0),
            evidence_token="turn-z",
            semantic_key="guard-key-3",
        ),
        decision=decision,
        new_record=newer,
    )

    await db_session.refresh(older)
    assert older.retracted_at is not None
    assert older.superseded_by_id == newer.id
