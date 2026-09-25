"""V3-FIX-70 · 记忆「变安静」闭环：deny 冷却窗（同位复活修复）.

wt404 Q-04 红队实锤（DYNAMIC_ISSUES V3-FIX-70①，P3）：用户 deny 旧偏好后，
下一探针同位（position 0）复活注入（D-08 memory_not_quieter 类独立复现——
一次 deny 仅 confidence 0.9→0.8，不改排序、不改 surfaced 面）。

修复（对齐 D-08 既有 deny 链路，勿重建）：denied 在偏好行 evidence_refs 落
确定性标记（写侧，与 episodic 的 snapshot 分支同构）；context_pack 读侧按
标记做同 key 冷却窗（72h，对齐 D-08 PROBE_DAYS=0/3/7 的事件后首探针 Day3）
——冷却窗内该偏好不进 prompt 偏好面；窗口过期后以已衰减置信度自然回流。
结构化面（resolved/conflict resolver）与 storage 不动，抑制事实经 pack
metadata ``preference_deny_quiet`` 保持可见（不静默）。

②隐式漂移吸收（行为反证在场而旧偏好仍锚定）＝产品决策（何种行为信号、
  什么阈值算作 drift 证据），本卡如实 DEFERRED——见 DYNAMIC_ISSUES 登记。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.memory import MemoryPreference
from app.models.user import User
from app.services.memory_service import (
    MEMORY_REFERENCE_DENIED_MARKER_TYPE,
    PREFERENCE_DENY_QUIET_WINDOW_HOURS,
    MemoryService,
    latest_preference_denial,
    preference_in_deny_quiet_window,
)

PREF_KEY = "study_time_preference"
DENIED_VALUE = "晚上学习"


# ---------------------------------------------------------------------------
# 纯函数面：标记读取 + 冷却窗判定
# ---------------------------------------------------------------------------


def _row(refs: list[dict]) -> MemoryPreference:
    return MemoryPreference(
        user_id=UUID(int=1),
        pref_key=PREF_KEY,
        pref_value={"value": DENIED_VALUE},
        version=1,
        confidence=0.9,
        evidence_score=0.8,
        evidence_refs=refs,
    )


def test_latest_denial_marker_scan() -> None:
    assert latest_preference_denial(_row([])) is None
    assert latest_preference_denial(_row([{"type": "user_state", "id": "e1"}])) is None
    marker = {"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE, "denied_at": "2026-09-25T10:00:00"}
    assert latest_preference_denial(_row([marker])) == marker
    # 多次 deny 取最新（字符串 ISO 序 = 时序）
    newer = {"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE, "denied_at": "2026-09-26T08:00:00"}
    assert latest_preference_denial(_row([marker, newer])) == newer
    # 形态异常 fail-soft
    assert latest_preference_denial(_row(["garbage", {"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE}])) is None
    row = _row([marker])
    row.evidence_refs = "not-a-list"
    assert latest_preference_denial(row) is None


def test_quiet_window_semantics() -> None:
    fresh = _row([{"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE, "denied_at": "2026-09-25T10:00:00"}])
    assert preference_in_deny_quiet_window(fresh, now=datetime(2026, 9, 25, 11, 0, 0))
    # 72h 窗口边界：窗口内安静、过期回流
    assert preference_in_deny_quiet_window(fresh, now=datetime(2026, 9, 28, 9, 59, 0))
    assert not preference_in_deny_quiet_window(fresh, now=datetime(2026, 9, 28, 10, 0, 1))
    # 无标记永不安静；坏时间戳 fail-soft
    assert not preference_in_deny_quiet_window(_row([]), now=datetime(2026, 9, 25, 11, 0, 0))
    bad = _row([{"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE, "denied_at": "not-a-date"}])
    assert not preference_in_deny_quiet_window(bad, now=datetime(2026, 9, 25, 11, 0, 0))
    assert PREFERENCE_DENY_QUIET_WINDOW_HOURS == 72.0


# ---------------------------------------------------------------------------
# 服务链：deny 落标记（accepted/ignore 不落）
# ---------------------------------------------------------------------------


async def _seed_user_and_pref(db_session) -> tuple[UUID, MemoryPreference]:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    service = MemoryService(db_session)
    row = await service.upsert_preference(
        user_id=user_id,
        pref_key=PREF_KEY,
        pref_value={"value": DENIED_VALUE},
        evidence_refs=[{"type": "user_state", "id": "evt_1", "schema_version": "fix70.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert row is not None
    return user_id, row


@pytest.mark.asyncio
async def test_denied_outcome_stamps_marker(db_session) -> None:
    user_id, row = await _seed_user_and_pref(db_session)
    service = MemoryService(db_session)
    assert latest_preference_denial(row) is None, "upsert 不落 deny 标记"

    result = await service.record_memory_reference_outcome(
        kind="preference",
        memory_id=row.id,
        user_id=user_id,
        outcome="denied",
        reason="现在不做数学了",
    )
    assert result is not None
    assert result["correction_count"] == 1
    refreshed = await service.get_preference_record(user_id, row.id) if hasattr(
        service, "get_preference_record"
    ) else None
    if refreshed is None:
        from sqlalchemy import select

        refreshed = (
            (await db_session.execute(select(MemoryPreference).where(MemoryPreference.id == row.id)))
            .scalars()
            .one()
        )
    marker = latest_preference_denial(refreshed)
    assert marker is not None, "denied 必须落确定性标记"
    assert marker.get("reason") == "现在不做数学了"
    assert any(ref.get("type") == "user_state" for ref in refreshed.evidence_refs), "既有 evidence_refs 保留"
    assert preference_in_deny_quiet_window(refreshed)


@pytest.mark.asyncio
async def test_accepted_outcome_does_not_stamp_marker(db_session) -> None:
    user_id, row = await _seed_user_and_pref(db_session)
    service = MemoryService(db_session)
    await service.record_memory_reference_outcome(
        kind="preference", memory_id=row.id, user_id=user_id, outcome="accepted"
    )
    from sqlalchemy import select

    refreshed = (
        (await db_session.execute(select(MemoryPreference).where(MemoryPreference.id == row.id)))
        .scalars()
        .one()
    )
    assert latest_preference_denial(refreshed) is None, "accepted 不得触发冷却窗"


# ---------------------------------------------------------------------------
# 集成面：deny 后 pack 偏好面零同位复活 + 抑制事实可见
# ---------------------------------------------------------------------------


async def _build_pack(db_session, user_id: UUID):
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 600, "goals": 300, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    return await builder.build(user_id, intent="chat", query_text="这道题看不懂，怎么办")


@pytest.mark.asyncio
async def test_pack_surfaces_pref_before_deny(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    user_id, _row = await _seed_user_and_pref(db_session)
    pack = await _build_pack(db_session, user_id)
    assert pack.preferences.get(PREF_KEY) == {"value": DENIED_VALUE}, "deny 前（基线）偏好正常在场"
    assert "preference_deny_quiet" not in pack.metadata


@pytest.mark.asyncio
async def test_deny_quiets_pref_in_prompt_face(db_session, monkeypatch) -> None:
    """契约锁（wt404 实锤的修复后形态）：deny 一次 → 同 key 不再进 prompt
    偏好面（同位复活被冷却窗截断）；结构化面与抑制事实保持可见。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    user_id, row = await _seed_user_and_pref(db_session)
    service = MemoryService(db_session)
    before = await _build_pack(db_session, user_id)
    assert before.preferences.get(PREF_KEY) == {"value": DENIED_VALUE}

    await service.record_memory_reference_outcome(
        kind="preference", memory_id=row.id, user_id=user_id, outcome="denied", reason="不做数学了"
    )
    after = await _build_pack(db_session, user_id)
    assert PREF_KEY not in after.preferences, "deny 后偏好不得再进 prompt 偏好面（同位复活截断）"
    # 抑制事实可见（不静默）：pack metadata 记录 quieted key
    quiet_meta = after.metadata.get("preference_deny_quiet") or {}
    assert PREF_KEY in (quiet_meta.get("quieted_keys") or [])
    # 行仍在（storage/结构化面零删除）
    from sqlalchemy import select

    live = (
        (await db_session.execute(select(MemoryPreference).where(MemoryPreference.id == row.id)))
        .scalars()
        .one()
    )
    assert live.deleted_at is None


@pytest.mark.asyncio
async def test_quiet_window_expiry_allows_reflow(db_session, monkeypatch) -> None:
    """窗口过期后偏好自然回流（变安静 ≠ 永久沉默）；回流排序吃既有 deny
    衰减（confidence/evidence 已降）。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    user_id, row = await _seed_user_and_pref(db_session)
    service = MemoryService(db_session)
    await service.record_memory_reference_outcome(
        kind="preference", memory_id=row.id, user_id=user_id, outcome="denied"
    )
    # 直接回拨标记时间到窗口外（免真实等待）
    from sqlalchemy import update as sa_update

    old = (datetime.utcnow() - timedelta(hours=PREFERENCE_DENY_QUIET_WINDOW_HOURS + 2)).isoformat()
    await db_session.execute(
        sa_update(MemoryPreference)
        .where(MemoryPreference.id == row.id)
        .values(evidence_refs=[{"type": MEMORY_REFERENCE_DENIED_MARKER_TYPE, "denied_at": old}])
    )
    await db_session.commit()
    pack = await _build_pack(db_session, user_id)
    assert pack.preferences.get(PREF_KEY) == {"value": DENIED_VALUE}, "冷却窗过期后偏好回流"


def test_helper_tolerates_foreign_record_shapes() -> None:
    assert latest_preference_denial(None) is None
    assert latest_preference_denial(SimpleNamespace(evidence_refs=None)) is None
    assert not preference_in_deny_quiet_window(SimpleNamespace(evidence_refs=[]))
