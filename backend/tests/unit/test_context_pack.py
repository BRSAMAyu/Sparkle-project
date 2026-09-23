from datetime import timezone, datetime, timedelta
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.core.intent_router import IntentRouter
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_context_pack_budget_trimming(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "x" * 120},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="curiosity_preference",
        pref_value={"value": "y" * 120},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    await memory_service.create_goal(
        user_id=user_id,
        title="Goal A",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Goal B",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_4"}],
    )

    now = _utcnow()
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory A " + ("z" * 120),
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_5"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory B " + ("z" * 120),
        source_type="analysis",
        source_id="src_2",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.4,
        tags=["cognitive"],
        evidence_refs=[{"type": "event", "id": "evt_6"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 5, "goals": 5, "episodic": 5}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert pack.token_usage["preferences"] <= pack.budgets["preferences"]
    assert pack.token_usage["goals"] <= pack.budgets["goals"]
    assert pack.token_usage["episodic"] <= pack.budgets["episodic"]


@pytest.mark.asyncio
async def test_context_pack_intent_budget(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    scheduler = ContextBudgetScheduler(
        budgets={
            "chat": {"preferences": 5, "goals": 5, "episodic": 5},
            "planning": {"preferences": 1, "goals": 2, "episodic": 3},
        }
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="planning")

    assert pack.budgets["goals"] == 3
    assert pack.context_focus is not None
    assert pack.context_focus["focus_mode"] == "plan_focus"
    assert pack.intent == "planning"

    router = IntentRouter()
    assert router.get_intent({"context": {"intent": "planning"}}) == "planning"


@pytest.mark.asyncio
async def test_context_pack_marks_consumed_memory_records(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_consumed"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "depth_preference" in pack.preferences

    refreshed = await db_session.get(MemoryPreference, pref.id)
    assert refreshed is not None
    assert refreshed.last_consumed_at is not None


@pytest.mark.asyncio
async def test_context_pack_keeps_memory_preferences_alongside_profile_domain(db_session):
    """D3 止血回归：profile 域（user_preferences_center）与 memory_preferences
    同 key 时不再先验遮蔽——双源并存进 pack，由 rank/预算竞争，双源键登记 metadata。"""
    from app.models.user_preferences import UserPreferencesCenter
    from app.services.personalization.preference_service import PreferenceService

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.flush()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="error_correction_rate",
        pref_value={"rate": 0.42},
        evidence_refs=[{"type": "event", "id": "evt_d3"}],
    )
    # 生产实证形态（审计案例 A）：同名 key 同时存在于 center.inferred（无置信度列）
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit=PreferenceService.DEFAULT_EXPLICIT.copy(),
            inferred={"error_correction_rate": {"value": 0.9}},
        )
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    # memory_preferences 的证据化记录必须保留在 pack 里，不得被 center 静默吃掉
    assert "error_correction_rate" in pack.preferences
    assert pack.preferences["error_correction_rate"] == {"rate": 0.42}
    # 双源并存要显式可审计，而不是无声遮蔽
    assert pack.metadata.get("preference_dual_source_keys") == ["error_correction_rate"]
    # 预算行为不被破坏
    assert pack.token_usage["preferences"] <= pack.budgets["preferences"]


@pytest.mark.asyncio
async def test_context_pack_no_dual_source_note_without_overlap(db_session):
    """无同 key 冲突时不得产生双源标注（默认 explicit 值也不算 profile 域占有）。"""
    from app.models.user_preferences import UserPreferencesCenter
    from app.services.personalization.preference_service import PreferenceService

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.flush()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_d3b"}],
    )
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit=PreferenceService.DEFAULT_EXPLICIT.copy(),  # depth_preference=0.5 默认值
            inferred={},
        )
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(
        budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 50}}
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "depth_preference" in pack.preferences
    assert "preference_dual_source_keys" not in pack.metadata


# ---------------------------------------------------------------------------
# GAIN-FIX 红旗2 守卫：预算裁剪的内容不得经 evidence_summary 回灌 prompt（M-05）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_summary_never_resurrects_budget_clipped_content(db_session):
    """goals/episodic 被预算整体裁掉时，evidence_summary 不得带回其正文。"""
    memory_service = MemoryService(db_session)
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="绝密目标GAINFIX-91",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_gf1"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="绝密记忆GAINFIX-77 " + ("z" * 120),
        source_type="analysis",
        source_id="src_gf1",
        occurred_at=_utcnow(),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_gf2"}],
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 0, "goals": 0, "episodic": 0}})
    pack = await ContextPackBuilder(db_session, scheduler=scheduler).build(user_id, intent="chat")
    ctx = pack.to_prompt_context()

    assert ctx["active_goals"] == []
    assert ctx["episodic_memories"] == []
    evidence = (ctx["context_pack"]["metadata"] or {}).get("evidence_summary") or {}
    assert [g.get("title") for g in evidence.get("goals") or []] == []
    assert [e.get("summary") for e in evidence.get("episodic") or []] == []

    from app.orchestration.prompts import format_user_context

    prompt = format_user_context(ctx)
    assert "绝密目标GAINFIX-91" not in prompt
    assert "绝密记忆GAINFIX-77" not in prompt
    # 诚实空态：无内容不落节头
    assert "【画像证据摘要】" not in prompt


@pytest.mark.asyncio
async def test_evidence_summary_stays_subset_of_surfaced_faces_under_partial_clip(db_session):
    """部分裁剪：evidence_summary 只保留注入面仍在场的条目（对齐而非杀观测面）。"""
    memory_service = MemoryService(db_session)
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Goal KEEP-1",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_k1"}],
    )
    for index in range(6):
        await memory_service.create_goal(
            user_id=user_id,
            title=f"Goal FILLER-{index} " + ("x" * 60),
            status="active",
            evidence_refs=[{"type": "event", "id": f"evt_f{index}"}],
        )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 0, "goals": 40, "episodic": 0}})
    pack = await ContextPackBuilder(db_session, scheduler=scheduler).build(user_id, intent="chat")
    ctx = pack.to_prompt_context()

    surfaced_ids = {str(g.get("id")) for g in ctx["active_goals"]}
    assert surfaced_ids, "前置：预算应允许部分 goal 在场"
    evidence = (ctx["context_pack"]["metadata"] or {}).get("evidence_summary") or {}
    evidence_ids = {str(g.get("id")) for g in evidence.get("goals") or []}
    assert evidence_ids <= surfaced_ids
