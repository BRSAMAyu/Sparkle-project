from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.accountability_policy import AccountabilityPolicy
from app.models.memory import EpisodicMemory
from app.services.policy_compiler_service import PolicyCompilerService


def _commitment(
    *,
    tags: list[str] | None = None,
    due_at: datetime | None = None,
    include_due_at: bool = True,
) -> EpisodicMemory:
    return EpisodicMemory(
        id=uuid4(),
        user_id=uuid4(),
        summary="完成这一周的复盘",
        source_type="chat",
        source_id="session-1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=(
            (datetime(2026, 4, 24, 18, 0, 0) if due_at is None else due_at)
            if include_due_at
            else None
        ),
        tags=tags or [],
        evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        evidence_token="turn_1",
    )


@pytest.mark.asyncio
async def test_policy_compiler_builds_stage24_template_library(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)

    rules = await service.compile_for_commitment(_commitment())

    assert [rule.policy_id.split(":")[0] for rule in rules] == list(service.TEMPLATE_IDS)


@pytest.mark.asyncio
async def test_policy_compiler_is_idempotent(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()

    first = await service.compile_for_commitment(commitment)
    second = await service.compile_for_commitment(commitment)

    assert [rule.model_dump(mode="json") for rule in first] == [rule.model_dump(mode="json") for rule in second]


@pytest.mark.asyncio
async def test_policy_compiler_persists_only_accountability_policy_rows(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()

    await service.compile_for_commitment(commitment, persist=True)

    rows = (await db_session.execute(select(AccountabilityPolicy))).scalars().all()
    assert len(rows) == len(service.TEMPLATE_IDS)
    assert {row.commitment_id for row in rows} == {commitment.id}


@pytest.mark.asyncio
async def test_policy_compiler_skips_when_mode_off(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "off")

    rules = await PolicyCompilerService(db_session).compile_for_commitment(_commitment())

    assert rules == []


@pytest.mark.asyncio
async def test_policy_compiler_extracts_partner_consent_from_tags(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    partner_id = uuid4()
    partnership_id = uuid4()
    commitment = _commitment(
        tags=[
            "accountability:partner_consent:true",
            f"accountability:partner_id:{partner_id}",
            f"accountability:partnership_id:{partnership_id}",
        ]
    )

    rules = await PolicyCompilerService(db_session).compile_for_commitment(commitment)
    partner_rule = next(rule for rule in rules if rule.action.type.value == "notify_partner")

    assert partner_rule.context.partner_consent_granted is True
    assert partner_rule.context.partner_id == partner_id
    assert partner_rule.context.partnership_id == partnership_id


@pytest.mark.asyncio
async def test_policy_compiler_does_not_emit_rules_without_due_at(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    commitment = _commitment(include_due_at=False)

    rules = await PolicyCompilerService(db_session).compile_for_commitment(commitment)

    assert rules == []


@pytest.mark.asyncio
async def test_policy_compiler_persists_deterministic_hashes(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()

    await service.compile_for_commitment(commitment, persist=True)
    rows = (await db_session.execute(select(AccountabilityPolicy).order_by(AccountabilityPolicy.policy_id))).scalars().all()

    assert all(len(row.ir_hash) == 64 for row in rows)
    assert rows[0].ir_hash == rows[0].ir_hash.lower()


@pytest.mark.asyncio
async def test_policy_compiler_reconciles_removed_rules(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()

    await service.compile_for_commitment(commitment, persist=True)
    await service.revoke_for_commitment(commitment_id=commitment.id)
    rows = (await db_session.execute(select(AccountabilityPolicy))).scalars().all()

    assert rows
    assert all(row.is_enabled is False for row in rows)


@pytest.mark.asyncio
async def test_policy_compiler_uses_shadow_flag_when_needed(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "shadow")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()
    db_session.add(commitment)
    await db_session.commit()

    await service.compile_for_commitment(commitment, persist=True)
    rows = (await db_session.execute(select(AccountabilityPolicy))).scalars().all()

    assert rows
    assert all(row.is_shadow is True for row in rows)


@pytest.mark.asyncio
async def test_policy_compiler_meets_lightweight_latency_budget(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "live")
    service = PolicyCompilerService(db_session)
    commitment = _commitment()

    started = time.perf_counter()
    for _ in range(25):
        await service.compile_for_commitment(commitment)
    average = (time.perf_counter() - started) / 25

    assert average <= 0.01
