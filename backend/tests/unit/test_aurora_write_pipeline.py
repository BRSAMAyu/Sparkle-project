from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

import app.aurora.runtime_v1.write_pipeline as write_pipeline_module
from app.aurora.runtime_v1.write_pipeline import (
    AURORA_CLAIM_KEY_TEMPLATE,
    AURORA_CLAIM_TTL_SECONDS,
    EXAM_SPRINT_KEY_TEMPLATE,
    INFERENCE_PIPELINE_KEY,
    TEMPORARY_STATE_KEY_TEMPLATE,
    TEMPORARY_STATE_TTL_SECONDS,
    InferenceClaim,
    InferenceWritePipeline,
    get_claim,
    submit_claim,
)
from app.models.user import User
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService
from app.services.personalization.preference_service import PreferenceService


class _ClockedRedis:
    def __init__(self, *, now: datetime | None = None) -> None:
        self.now = (now or datetime(2026, 4, 25, 8, 0, tzinfo=UTC)).replace(tzinfo=None)
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self._expires_at: dict[str, datetime] = {}

    def advance(self, *, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)

    def _prune(self, key: str) -> None:
        expires_at = self._expires_at.get(key)
        if expires_at is not None and self.now >= expires_at:
            self.kv.pop(key, None)
            self.ttl.pop(key, None)
            self._expires_at.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._prune(key)
        return self.kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.kv[key] = value
        self.ttl[key] = ttl
        self._expires_at[key] = self.now + timedelta(seconds=ttl)

    async def expire(self, key: str, ttl: int) -> None:
        if key not in self.kv:
            return
        self.ttl[key] = ttl
        self._expires_at[key] = self.now + timedelta(seconds=ttl)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.kv.pop(key, None)
            self.ttl.pop(key, None)
            self._expires_at.pop(key, None)


async def _create_user(db_session, *, user_id=None):
    user_id = user_id or uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    return user_id


@pytest.mark.asyncio
async def test_submit_claim_writes_and_reads_domain_claim_with_24h_ttl() -> None:
    redis = _ClockedRedis()

    await submit_claim(
        InferenceClaim(
            user_id="user-1",
            domain="baseline",
            value="零基础",
            confidence=0.62,
            evidence_type="modeling_turn",
        ),
        redis=redis,
    )
    await submit_claim(
        InferenceClaim(
            user_id="user-1",
            domain="baseline",
            value="零基础",
            confidence=0.84,
            evidence_type="modeling_turn",
        ),
        redis=redis,
    )

    key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id="user-1", domain="baseline")
    assert redis.ttl[key] == AURORA_CLAIM_TTL_SECONDS

    stored = await get_claim("baseline", user_id="user-1", redis=redis)
    assert stored is not None
    assert stored.domain == "baseline"
    assert stored.value == "零基础"
    assert stored.confidence == 0.84


@pytest.mark.asyncio
async def test_temporary_state_uses_24h_ttl_and_auto_expires(db_session) -> None:
    redis = _ClockedRedis()
    pipeline = InferenceWritePipeline(db_session, redis)

    claim = await pipeline.ingest_claim(
        user_id="temporary-user",
        claim="今天很累",
        claim_type="temporary_state",
        scope="long_term",
        confidence=0.94,
        evidence=["用户刚刚明确说今天状态很差。"],
    )

    key = TEMPORARY_STATE_KEY_TEMPLATE.format(user_id="temporary-user", claim_id=claim.id)
    assert redis.ttl[key] == TEMPORARY_STATE_TTL_SECONDS
    assert (await pipeline.get_temporary_state(user_id="temporary-user", claim_id=claim.id)) is not None

    redis.advance(seconds=TEMPORARY_STATE_TTL_SECONDS + 1)
    assert await pipeline.get_temporary_state(user_id="temporary-user", claim_id=claim.id) is None


@pytest.mark.asyncio
async def test_exam_sprint_claim_uses_exam_deadline_ttl(db_session, monkeypatch) -> None:
    redis = _ClockedRedis(now=datetime(2026, 4, 25, 10, 0, 0))
    pipeline = InferenceWritePipeline(db_session, redis)
    exam_ends_at = datetime(2026, 4, 28, 10, 0, 0)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: redis.now)

    claim = await pipeline.ingest_claim(
        user_id="exam-user",
        claim="TCP 是当前冲刺期的薄弱点",
        claim_type="exam_sprint",
        scope="exam_sprint",
        confidence=0.82,
        evidence=[
            "最近三次 TCP 题目都出现关键错误。",
            "模拟卷中 TCP 题整组失分。",
        ],
        planning_session_id="planning-1",
        exam_ends_at=exam_ends_at,
        plan_id="plan-1",
    )

    key = EXAM_SPRINT_KEY_TEMPLATE.format(user_id="exam-user", planning_session_id="planning-1")
    assert redis.ttl[key] == int((exam_ends_at - redis.now).total_seconds())
    assert claim.status == "confirmed"
    assert claim.expires_at == exam_ends_at.isoformat()

    stored = await pipeline.get_exam_sprint_claims(user_id="exam-user", planning_session_id="planning-1")
    assert [item.claim for item in stored] == ["TCP 是当前冲刺期的薄弱点"]


@pytest.mark.asyncio
async def test_long_term_candidate_moves_to_trial_then_auto_confirms(db_session, monkeypatch) -> None:
    user_id = await _create_user(db_session)
    pref_svc = PreferenceService(db_session)
    pipeline = InferenceWritePipeline(db_session, redis=None, pref_service=pref_svc)
    service = AuroraCalibrationCardService(db_session, redis=None)

    observed_at = datetime(2026, 4, 25, 12, 0, 0)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: observed_at)

    claim = await pipeline.ingest_claim(
        user_id=user_id,
        claim="用户更适合 30-45 分钟的短任务卡",
        claim_type="learning_preference",
        scope="long_term",
        confidence=0.78,
        evidence=[
            "25 分钟任务完成率明显高于 60 分钟任务。",
            "长任务中断后通常不会立刻回到原任务。",
        ],
        preference_key="task_card_preference",
        preference_value={"duration": "short"},
    )

    cards = await service.list_cards(user_id=user_id)
    assert [item["id"] for item in cards["items"]] == [claim.id]
    assert cards["items"][0]["status"] == "candidate"

    confirmed_at = observed_at + timedelta(minutes=10)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: confirmed_at)
    response = await service.respond(
        user_id=user_id,
        card_id=claim.id or "",
        response="confirm",
    )
    assert response["card"]["status"] == "trial"
    assert response["card"]["trial_expires_at"] is not None

    prefs = await PreferenceService(db_session).get_preferences(user_id)
    durable_claims = ((prefs.inferred or {}).get(INFERENCE_PIPELINE_KEY) or {}).get("claims") or {}
    assert durable_claims[claim.id]["status"] == "trial"

    auto_confirm_at = confirmed_at + timedelta(days=7, seconds=1)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: auto_confirm_at)
    cards_after_trial = await service.list_cards(user_id=user_id)
    assert cards_after_trial["items"] == []

    refreshed = await PreferenceService(db_session).get_preferences(user_id)
    assumptions = {
        item["id"]: item
        for item in ((refreshed.inferred or {}).get("self_model") or {}).get("known_assumptions", [])
    }
    assert assumptions[claim.id]["status"] == "confirmed"
    assert assumptions[claim.id]["confirmed_at"] == auto_confirm_at.isoformat()

    durable_claims = ((refreshed.inferred or {}).get(INFERENCE_PIPELINE_KEY) or {}).get("claims") or {}
    assert durable_claims[claim.id]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_revoked_claim_is_not_proposed_again(db_session, monkeypatch) -> None:
    user_id = await _create_user(db_session)
    pref_svc = PreferenceService(db_session)
    pipeline = InferenceWritePipeline(db_session, redis=None, pref_service=pref_svc)
    service = AuroraCalibrationCardService(db_session, redis=None)

    first_seen_at = datetime(2026, 4, 25, 15, 0, 0)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: first_seen_at)
    claim = await pipeline.ingest_claim(
        user_id=user_id,
        claim="用户存在明显拖延倾向",
        claim_type="long_term_profile",
        scope="long_term",
        confidence=0.81,
        evidence=[
            "连续三次把当天第一张任务卡推迟到晚上。",
            "计划开始时间稳定晚于承诺时间超过 90 分钟。",
        ],
        preference_key="procrastination_tendency",
        preference_value={"label": "high"},
    )

    rejected_at = first_seen_at + timedelta(minutes=5)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: rejected_at)
    response = await service.respond(
        user_id=user_id,
        card_id=claim.id or "",
        response="incorrect",
        reason="这周是临时有事，不是长期状态。",
    )
    assert response["card"]["status"] == "revoked"

    seen_again_at = rejected_at + timedelta(days=1)
    monkeypatch.setattr(write_pipeline_module, "_utcnow", lambda: seen_again_at)
    reingested = await pipeline.ingest_claim(
        user_id=user_id,
        claim="用户存在明显拖延倾向",
        claim_type="long_term_profile",
        scope="long_term",
        confidence=0.93,
        evidence=[
            "再次观察到任务延迟启动。",
            "又一次在晚间才进入正式学习。",
        ],
        preference_key="procrastination_tendency",
        preference_value={"label": "high"},
    )

    assert reingested.status == "revoked"
    assert reingested.id == claim.id

    cards = await service.list_cards(user_id=user_id)
    assert cards["items"] == []

    prefs = await PreferenceService(db_session).get_preferences(user_id)
    durable_bucket = (prefs.inferred or {}).get(INFERENCE_PIPELINE_KEY) or {}
    revoked_claims = durable_bucket.get("revoked_claims") or {}
    assert revoked_claims[claim.fingerprint]["status"] == "revoked"
