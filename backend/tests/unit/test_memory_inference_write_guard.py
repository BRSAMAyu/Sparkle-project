"""M-01 写守卫：Inference 不覆盖 fact（红→绿基线测试）。

覆盖三条铁律的存储级保障：
1. memory_preferences 版本链上，推断写（ai_inferred）不得接管显式事实头
   （不新增版本、不设 replaced_by_id、find_preference 仍返回显式值）；
2. 显式用户写可正常取代推断头（用户纠错优先，不回归）；
3. 推断写可正常演替推断头（合法的推断演化不回归）。

另覆盖：episodic 写路径的 epistemic_class 派生、epoch bump 数据结构。
"""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.memory import EpisodicMemory, MemoryPreference
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_epistemic_contract import (
    EpistemicClass,
    MemoryRecordStatus,
    classify_episodic_class,
    derive_status,
)
from app.services.memory_service import MemoryService


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


@pytest.mark.asyncio
async def test_inferred_preference_write_cannot_supersede_explicit_fact(db_session, monkeypatch):
    """推断写不覆盖 fact：显式头必须保持版本链头地位。"""
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    explicit = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "user_state", "id": "settings_ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert explicit is not None

    blocked = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.3},
        evidence_refs=[{"type": "ai_inferred", "id": "seed-1"}],
        confidence=0.6,
        source_type="ai_inferred",
    )

    # 守卫：推断写被拒绝（None），版本链头仍是显式事实。
    assert blocked is None

    head = await service.find_preference(user.id, "depth_preference")
    assert head is not None
    assert head.id == explicit.id
    assert head.version == 1
    assert head.replaced_by_id is None
    assert head.pref_value == {"value": 0.8}

    # 整链上不存在任何推断版本（fact 域未被污染）。
    result = await db_session.execute(
        select(MemoryPreference).where(MemoryPreference.user_id == user.id)
    )
    all_records = list(result.scalars().all())
    assert len(all_records) == 1
    assert all(
        ref.get("type") != "ai_inferred" for ref in all_records[0].evidence_refs
    )


@pytest.mark.asyncio
async def test_inferred_preference_write_blocked_via_evidence_refs_only(db_session, monkeypatch):
    """source_type 未标注但 evidence_refs 含 ai_inferred —— 同样按推断写拦截。"""
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )

    blocked = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.3},
        evidence_refs=[{"type": "user_state", "id": "ui"}, {"type": "ai_inferred", "id": "seed-9"}],
        confidence=0.6,
        source_type=None,
    )
    assert blocked is None

    head = await service.find_preference(user.id, "depth_preference")
    assert head.version == 1
    assert head.pref_value == {"value": 0.8}


@pytest.mark.asyncio
async def test_explicit_write_still_supersedes_inferred_head(db_session, monkeypatch):
    """用户纠错优先：显式写可正常接管推断头（不回归）。"""
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    inferred = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.3},
        evidence_refs=[{"type": "ai_inferred", "id": "seed-1"}],
        confidence=0.6,
        source_type="ai_inferred",
    )
    assert inferred is not None

    explicit = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.9},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.95,
        source_type="user_state",
    )
    assert explicit is not None
    assert explicit.version == 2

    refreshed = await db_session.execute(
        select(MemoryPreference).where(MemoryPreference.id == inferred.id)
    )
    inferred_row = refreshed.scalar_one()
    assert inferred_row.replaced_by_id == explicit.id
    assert derive_status(inferred_row) == MemoryRecordStatus.SUPERSEDED.value


@pytest.mark.asyncio
async def test_inferred_write_still_evolves_inferred_head(db_session, monkeypatch):
    """推断演化不回归：推断头可被新的推断写演替。"""
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    first = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.3},
        evidence_refs=[{"type": "ai_inferred", "id": "seed-1"}],
        confidence=0.6,
        source_type="ai_inferred",
    )
    second = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.4},
        evidence_refs=[{"type": "ai_inferred", "id": "seed-2"}],
        confidence=0.7,
        source_type="ai_inferred",
    )
    assert second is not None
    assert second.version == 2

    refreshed = await db_session.execute(
        select(MemoryPreference).where(MemoryPreference.id == first.id)
    )
    assert refreshed.scalar_one().replaced_by_id == second.id


@pytest.mark.asyncio
async def test_first_write_inferred_allowed_on_empty_chain(db_session, monkeypatch):
    """空链首写不受守卫影响（无 fact 可覆盖）。"""
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    record = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.5},
        evidence_refs=[{"type": "ai_inferred", "id": "seed-1"}],
        confidence=0.6,
        source_type="ai_inferred",
    )
    assert record is not None
    assert record.version == 1


@pytest.mark.asyncio
async def test_episodic_write_derives_epistemic_class_from_lane(db_session, monkeypatch):
    """episodic 写路径落 epistemic_class（R2-F1 收紧后语义）：
    - direct_capture + user_registered（用户陈述）→ FACT
    - direct_capture + chat_turn（机器写事件）→ OBSERVATION
    - inferred lane → HYPOTHESIS
    """
    user = await _create_user(db_session)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())

    service = MemoryService(db_session)
    fact_record = await service.create_episodic_memory(
        user_id=user.id,
        summary="用户注册时陈述：我每周三下午有空",
        source_type="user_registered",
        source_id="seed-1",
        occurred_at=datetime(2026, 9, 19, 10, 0, 0),
        importance_score=0.8,
        tags=["seed"],
        evidence_refs=[{"type": "user_state", "id": "seed-1"}],
        source_lane="direct_capture",
        semantic_key="seed-availability",
    )
    assert fact_record is not None
    assert fact_record.epistemic_class == EpistemicClass.FACT.value

    observation_record = await service.create_episodic_memory(
        user_id=user.id,
        summary="completed 操作系统 - 死锁处理机制",
        source_type="chat_turn",
        source_id="session-1",
        occurred_at=datetime(2026, 9, 19, 10, 5, 0),
        importance_score=0.5,
        tags=["completion"],
        evidence_refs=[{"type": "chat_turn", "id": "turn-1"}],
        source_lane="direct_capture",
        semantic_key="completion-os-deadlock",
    )
    assert observation_record is not None
    assert observation_record.epistemic_class == EpistemicClass.OBSERVATION.value

    hypothesis_record = await service.create_episodic_memory(
        user_id=user.id,
        summary="用户偏好晚间复习",
        source_type="chat",
        source_id="session-1",
        occurred_at=datetime(2026, 9, 19, 10, 10, 0),
        importance_score=0.5,
        tags=["inferred"],
        evidence_refs=[{"type": "chat_turn", "id": "turn-2"}],
        source_lane="inferred_extraction",
        semantic_key="pref-evening",
    )
    assert hypothesis_record is not None
    assert hypothesis_record.epistemic_class == EpistemicClass.HYPOTHESIS.value

    assert derive_status(fact_record) == MemoryRecordStatus.ACTIVE.value
    assert classify_episodic_class("direct_capture", source_type="user_registered") == EpistemicClass.FACT.value
    assert classify_episodic_class("direct_capture", source_type="chat_turn") == (
        EpistemicClass.OBSERVATION.value
    )
    assert classify_episodic_class("inferred_extraction") == EpistemicClass.HYPOTHESIS.value
    assert classify_episodic_class(None) == EpistemicClass.HYPOTHESIS.value


@pytest.mark.asyncio
async def test_memory_epoch_bump_creates_settings_and_audits(db_session):
    """epoch 数据结构：懒建设置行、单调递增、MemoryCorrection 留痕。"""
    from app.models.memory import MemoryCorrection

    user = await _create_user(db_session)
    service = MemoryService(db_session)

    epoch_before = await service.get_memory_epoch(user.id)
    assert epoch_before == 1  # 无设置行时默认 epoch=1

    new_epoch = await service.bump_memory_epoch(user.id, reason="user_bulk_delete")
    assert new_epoch == 2

    settings_row = (
        await db_session.execute(select(UserMemorySettings).where(UserMemorySettings.user_id == user.id))
    ).scalar_one()
    assert settings_row.memory_epoch == 2
    assert settings_row.memory_epoch_reason == "user_bulk_delete"
    assert settings_row.memory_epoch_bumped_at is not None

    again = await service.bump_memory_epoch(user.id, reason="sensitive_delete")
    assert again == 3

    corrections = (
        await db_session.execute(
            select(MemoryCorrection).where(
                MemoryCorrection.user_id == user.id,
                MemoryCorrection.action == "epoch_bump",
            )
        )
    ).scalars().all()
    assert len(corrections) == 2

    assert await service.get_memory_epoch(user.id) == 3


@pytest.mark.asyncio
async def test_memory_epoch_concurrent_bumps_no_lost_increment(tmp_path):
    """R2-F3：并发 bump 不丢增量。

    三个独立连接（真实文件 sqlite，非共享内存库）同时对同一用户首 bump：
    - 懒建并发撞 unique(user_id) 的 IntegrityError 必须先 rollback 再原子
      自增重试（不得把 session 留在 aborted 态）；
    - 每次成功 bump 各得一个不同的返回值（2/3/4 之一），终值必为 4，
      审计行数必为 3 —— 无论语句如何交错。
    旧实现（SELECT→python+1→commit）在交错下会返回两个 2、终值 2。
    """
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base
    from app.models.memory import MemoryCorrection

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'epoch_concurrency.db'}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[
                    Base.metadata.tables["users"],
                    Base.metadata.tables["user_memory_settings"],
                    Base.metadata.tables["memory_corrections"],
                ],
            )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()

        async def bump_once() -> int:
            async with session_factory() as session:
                return await MemoryService(session).bump_memory_epoch(user_id, reason="concurrent_delete")

        results = await asyncio.gather(bump_once(), bump_once(), bump_once())
        assert sorted(results) == [2, 3, 4]

        async with session_factory() as session:
            final_epoch = await MemoryService(session).get_memory_epoch(user_id)
            audit_rows = (
                await session.execute(
                    select(MemoryCorrection).where(
                        MemoryCorrection.user_id == user_id,
                        MemoryCorrection.action == "epoch_bump",
                    )
                )
            ).scalars().all()
        assert final_epoch == 4
        assert len(audit_rows) == 3
    finally:
        await engine.dispose()
