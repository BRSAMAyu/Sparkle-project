"""A-06 · Receipt 四动作服务链路测试（GJ08: Correction → memory scope → adaptation）。

验收面：每个动作在既有权威真源上**真实生效**（sqlite 行级断言），
跨用户 id 与缺失 id 一律 404（无存在性泄漏），词表外动作 422/ValueError，
终态冲突 409（ConflictError），M-07 撤销链 epoch bump + 缓存 DEL。
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryPreference
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.services.aurora_receipt_service import AuroraReceiptService
from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline
from app.services.memory_provenance_service import (
    MemoryProvenanceConflictError,
    MemoryProvenanceNotFoundError,
)

# ---------------------------------------------------------------------------
# Hermetic fixtures（FakeRedis + outbox 表 + 外部副作用打桩）
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted: list[str] = []

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value
        return True

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key)
                deleted += 1
            self.deleted.append(key)
        return deleted


_OUTBOX_DDL = [
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id CHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        sequence_number INTEGER NOT NULL,
        payload JSON NOT NULL,
        metadata JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
]


@pytest.fixture(name="receipt_env")
async def receipt_env_fixture(db_session, monkeypatch):
    """Feature flags + outbox 表 + hermetic redis + 外部副作用打桩."""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())
    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService.record_user_correction",
        AsyncMock(),
    )
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    fake = FakeRedis()
    monkeypatch.setattr(MemoryInvalidationPipeline, "_resolve_redis", lambda self: fake)
    yield fake


async def _make_user(db_session: AsyncSession) -> User:
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


async def _insert_episodic(
    db_session: AsyncSession,
    user: User,
    summary: str,
    *,
    confidence: float = 0.8,
    lane: str = "user_confirmed",
) -> EpisodicMemory:
    record = EpisodicMemory(
        user_id=user.id,
        summary=summary,
        source_type="chat",
        source_lane=lane,
        occurred_at=datetime.now(UTC).replace(tzinfo=None),
        evidence_refs=[{"type": "event", "id": f"evt_{uuid4().hex[:8]}"}],
        confidence=confidence,
        evidence_score=confidence,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


async def _get_memory(db_session: AsyncSession, kind: str, memory_id: UUID):
    model = {"episodic": EpisodicMemory, "preference": MemoryPreference}[kind]
    result = await db_session.execute(select(model).where(model.id == memory_id))
    return result.scalar_one_or_none()


async def _memory_epoch(db_session: AsyncSession, user_id: UUID) -> int:
    result = await db_session.execute(
        select(UserMemorySettings).where(UserMemorySettings.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    return int(row.memory_epoch) if row is not None else 0


# ---------------------------------------------------------------------------
# 四动作真实生效（GJ08 链路）
# ---------------------------------------------------------------------------


async def test_not_relevant_records_denied_outcome_and_decays_confidence(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "用户偏好先做样例再写代码", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)

    result = await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="not_relevant",
        response_id="resp_1",
    )

    assert result["status"] == "ok"
    assert result["memory_reference_outcome"]["memory_reference_outcome"] == "denied"
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed is not None
    assert float(refreshed.confidence or 0) < 0.8  # 飞轮负样本：引用层降置信
    corrections = (
        (await db_session.execute(select(MemoryCorrection).where(MemoryCorrection.memory_id == record.id)))
        .scalars()
        .all()
    )
    assert any(entry.action == "memory_reference_denied" for entry in corrections)


async def test_wrong_lower_confidence_without_content(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "用户每周三下午没课", confidence=0.7)
    service = AuroraReceiptService(db_session, receipt_env)

    result = await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="wrong",
    )

    assert result["mode"] == "lower_confidence"
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert float(refreshed.confidence or 0) < 0.7
    assert int(refreshed.correction_count or 0) >= 1


async def test_wrong_with_content_supersedes_episodic(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "用户在准备期末考", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)

    result = await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="wrong",
        corrected_content="其实在准备考研复试",
    )

    assert result["mode"] == "supersede"
    old = await _get_memory(db_session, "episodic", record.id)
    assert old.superseded_by_id is not None  # M-01 法则：更正 = supersede，不是覆写
    replacement = await _get_memory(db_session, "episodic", old.superseded_by_id)
    assert replacement is not None
    assert "考研复试" in str(replacement.summary)


async def test_change_scope_pauses_recall(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "用户喜欢简洁解释", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)

    result = await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="change_scope",
    )

    assert result["status"] == "ok"
    assert result["changed"] is True
    assert result["paused"] is True
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed.archived_at is not None  # 暂停召回（可恢复，不是删除）
    assert refreshed.revoked_at is None


async def test_delete_revokes_with_invalidation_chain(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "用户住在上海", confidence=0.9)
    service = AuroraReceiptService(db_session, receipt_env)
    epoch_before = await _memory_epoch(db_session, user.id)

    result = await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="delete",
    )

    assert result["status"] == "ok"
    assert result["revoked"] is True
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed.revoked_at is not None
    epoch_after = await _memory_epoch(db_session, user.id)
    assert epoch_after > epoch_before  # M-07：撤销链 epoch bump
    assert receipt_env.deleted, "derived cache DEL expected after revoke"


# ---------------------------------------------------------------------------
# 隔离 / 词表 / 幂等守卫（不弱化既有安全面）
# ---------------------------------------------------------------------------


async def test_cross_user_id_is_indistinguishable_from_missing(db_session, receipt_env):
    owner = await _make_user(db_session)
    attacker = await _make_user(db_session)
    record = await _insert_episodic(db_session, owner, "owner 的私密记忆", confidence=0.9)
    service = AuroraReceiptService(db_session, receipt_env)

    for action in ("not_relevant", "wrong", "change_scope", "delete"):
        with pytest.raises(MemoryProvenanceNotFoundError):
            await service.respond(
                user_id=attacker.id,
                memory_type="episodic",
                memory_id=record.id,
                action=action,
            )
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed.revoked_at is None and refreshed.archived_at is None


async def test_missing_memory_id_is_not_found(db_session, receipt_env):
    user = await _make_user(db_session)
    service = AuroraReceiptService(db_session, receipt_env)
    for action in ("not_relevant", "wrong", "change_scope", "delete"):
        with pytest.raises(MemoryProvenanceNotFoundError):
            await service.respond(
                user_id=user.id,
                memory_type="episodic",
                memory_id=uuid4(),
                action=action,
            )


async def test_action_out_of_vocabulary_is_rejected(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "正常记忆", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)
    with pytest.raises(ValueError):
        await service.respond(
            user_id=user.id,
            memory_type="episodic",
            memory_id=record.id,
            action="wipe_all",
        )
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed.revoked_at is None


async def test_kind_out_of_vocabulary_is_rejected(db_session, receipt_env):
    user = await _make_user(db_session)
    service = AuroraReceiptService(db_session, receipt_env)
    with pytest.raises(ValueError):
        await service.respond(
            user_id=user.id,
            memory_type="document",
            memory_id=uuid4(),
            action="delete",
        )


async def test_scope_action_on_terminal_memory_conflicts(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "将被删除的记忆", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)
    await service.respond(user_id=user.id, memory_type="episodic", memory_id=record.id, action="delete")
    with pytest.raises(MemoryProvenanceConflictError):
        await service.respond(user_id=user.id, memory_type="episodic", memory_id=record.id, action="change_scope")


async def test_double_delete_is_idempotent_and_honest(db_session, receipt_env):
    """M-07 幂等守卫：重复 delete 不复活不双计；第二次仍诚实回 ok（终态幂等）。"""
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "只删一次", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)
    first = await service.respond(user_id=user.id, memory_type="episodic", memory_id=record.id, action="delete")
    second = await service.respond(user_id=user.id, memory_type="episodic", memory_id=record.id, action="delete")
    assert first["revoked"] is True
    assert second["status"] == "ok"
    refreshed = await _get_memory(db_session, "episodic", record.id)
    assert refreshed.revoked_at is not None


async def test_audit_reason_carries_receipt_marker(db_session, receipt_env):
    user = await _make_user(db_session)
    record = await _insert_episodic(db_session, user, "审计面记忆", confidence=0.8)
    service = AuroraReceiptService(db_session, receipt_env)
    await service.respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=record.id,
        action="not_relevant",
        reason="与本轮无关",
    )
    corrections = (
        (
            await db_session.execute(
                select(MemoryCorrection).where(
                    MemoryCorrection.memory_id == record.id,
                    MemoryCorrection.action == "memory_reference_denied",
                )
            )
        )
        .scalars()
        .all()
    )
    assert corrections, "expected memory_reference_denied audit row"
    assert any("aurora_receipt:not_relevant" in (entry.reason or "") for entry in corrections)


# ---------------------------------------------------------------------------
# preference 域（版本链 supersede）
# ---------------------------------------------------------------------------


async def test_preference_wrong_supersede_via_version_chain(db_session, receipt_env):
    user = await _make_user(db_session)
    preference = MemoryPreference(
        user_id=user.id,
        pref_key="response_style",  # PREFERENCE_KEYS 既有成员
        pref_value={"value": "先给结论"},
        version=1,
        evidence_score=0.5,
        confidence=0.8,
        evidence_refs=[{"type": "event", "id": f"evt_{uuid4().hex[:8]}"}],
    )
    db_session.add(preference)
    await db_session.commit()
    await db_session.refresh(preference)

    service = AuroraReceiptService(db_session, receipt_env)
    result = await service.respond(
        user_id=user.id,
        memory_type="preference",
        memory_id=preference.id,
        action="wrong",
        corrected_content="先给例子再给结论",
    )
    assert result["mode"] == "supersede"
    refreshed = await _get_memory(db_session, "preference", preference.id)
    assert refreshed is not None
    assert refreshed.replaced_by_id is not None  # 版本链：旧版本指向新版本
    successor = await _get_memory(db_session, "preference", refreshed.replaced_by_id)
    assert successor is not None
    value = successor.pref_value or {}
    assert (value.get("value") if isinstance(value, dict) else None) == "先给例子再给结论"
