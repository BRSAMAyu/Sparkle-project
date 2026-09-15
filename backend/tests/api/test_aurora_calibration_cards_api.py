from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.v1.aurora import router as aurora_router
from app.db.session import get_db
from app.models.memory import MemoryCorrection
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.aurora.runtime_v1.write_pipeline import INFERENCE_PIPELINE_KEY
from app.services.personalization.preference_service import PreferenceService


@pytest.fixture
def aurora_client(db_session):
    app = FastAPI()
    app.include_router(aurora_router)

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_get_calibration_cards_returns_up_to_three_pending_items(
    aurora_client,
    db_session,
):
    client, state = aurora_client
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit={},
            inferred={
                "self_model": {
                    "known_assumptions": [
                        {
                            "id": "needs-confirmation",
                            "title": "你最近两天的可用时间可能被高估了",
                            "statement": "我目前的判断：你最近两天的可用时间可能被高估了。",
                            "confidence": 0.91,
                            "status": "candidate",
                            "needs_confirmation": True,
                            "evidence": [
                                "两张 90 分钟任务卡都超过 130 分钟。",
                            ],
                            "updated_at": "2026-04-25T08:00:00",
                        },
                        {
                            "id": "candidate-short-card",
                            "title": "你更适合短任务卡推进",
                            "status": "candidate",
                            "confidence": 0.74,
                            "needs_confirmation": True,
                            "evidence_summary": "证据：25 分钟任务的完成率明显高于长卡。",
                            "updated_at": "2026-04-25T09:00:00",
                        },
                        {
                            "id": "candidate-tcp",
                            "title": "TCP 这部分的掌握度还不稳定",
                            "status": "candidate",
                            "confidence": 0.71,
                            "needs_confirmation": True,
                            "evidence_summary": "证据：最近三次相关题目正确率波动较大。",
                            "updated_at": "2026-04-24T09:00:00",
                        },
                        {
                            "id": "observed-hidden",
                            "title": "这条观察还不足以升级成候选",
                            "status": "observed",
                            "confidence": 0.66,
                            "needs_confirmation": False,
                            "evidence": [
                                "目前只有一条弱证据。",
                            ],
                            "updated_at": "2026-04-25T10:00:00",
                        },
                        {
                            "id": "trial-hidden",
                            "title": "已经进入试用，不应继续显示",
                            "status": "trial",
                            "confidence": 0.88,
                            "needs_confirmation": False,
                            "trial_started_at": "2026-04-24T10:00:00",
                            "trial_expires_at": "2026-05-01T10:00:00",
                            "updated_at": "2026-04-25T11:00:00",
                        },
                        {
                            "id": "revoked-item",
                            "title": "不应再显示的假设",
                            "confidence": 0.21,
                            "status": "revoked",
                            "needs_confirmation": False,
                            "updated_at": "2026-04-25T12:00:00",
                        },
                    ]
                }
            },
        )
    )
    await db_session.commit()
    state["current_user"] = type("UserStub", (), {"id": user_id})()

    response = client.get("/aurora/calibration-cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["surface"]["state"] == "needs_confirmation"
    assert payload["surface"]["label"] == "Aurora · 需要确认"
    assert [item["id"] for item in payload["items"]] == [
        "needs-confirmation",
        "candidate-short-card",
        "candidate-tcp",
    ]
    assert payload["items"][0]["evidence"][0] == "两张 90 分钟任务卡都超过 130 分钟。"
    assert payload["items"][1]["status"] == "candidate"
    assert payload["items"][2]["confidence_label"] == "71%"


@pytest.mark.asyncio
async def test_respond_calibration_card_updates_self_model_and_logs_feedback(
    aurora_client,
    db_session,
):
    client, state = aurora_client
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            version=1,
            explicit={},
            inferred={
                "self_model": {
                    "known_assumptions": [
                        {
                            "id": "confirm-me",
                            "title": "你现在更适合短任务卡推进",
                            "status": "candidate",
                            "confidence": 0.61,
                            "needs_confirmation": True,
                            "preference_key": "task_card_preference",
                            "preference_value": {"duration": "short"},
                        },
                        {
                            "id": "reject-me",
                            "title": "你每天都能稳定学 90 分钟",
                            "status": "candidate",
                            "confidence": 0.66,
                            "needs_confirmation": True,
                        },
                        {
                            "id": "mute-me",
                            "title": "系统想继续监测这个判断",
                            "status": "candidate",
                            "confidence": 0.49,
                            "needs_confirmation": True,
                        },
                    ]
                }
            },
        )
    )
    await db_session.commit()
    state["current_user"] = type("UserStub", (), {"id": user_id})()

    confirm_response = client.post(
        "/aurora/calibration-cards/confirm-me/respond",
        json={"response": "confirm"},
    )
    reject_response = client.post(
        "/aurora/calibration-cards/reject-me/respond",
        json={
            "response": "incorrect",
            "reason": "最近节奏和以前不一样",
        },
    )
    mute_response = client.post(
        "/aurora/calibration-cards/mute-me/respond",
        json={"response": "mute"},
    )

    assert confirm_response.status_code == 200
    assert reject_response.status_code == 200
    assert mute_response.status_code == 200

    prefs = await PreferenceService(db_session).get_preferences(user_id)
    self_model = prefs.inferred["self_model"]
    assumptions = {item["id"]: item for item in self_model["known_assumptions"]}

    assert assumptions["confirm-me"]["status"] == "trial"
    assert assumptions["confirm-me"]["needs_confirmation"] is False
    assert assumptions["confirm-me"]["confidence"] >= 0.85
    assert assumptions["confirm-me"]["response_history"][-1]["response"] == "confirm"
    assert assumptions["confirm-me"]["trial_started_at"] is not None
    assert assumptions["confirm-me"]["trial_expires_at"] is not None

    assert assumptions["reject-me"]["status"] == "revoked"
    assert assumptions["reject-me"]["needs_confirmation"] is False
    assert assumptions["reject-me"]["confidence"] <= 0.25
    assert assumptions["reject-me"]["response_history"][-1]["response"] == "incorrect"
    assert assumptions["reject-me"]["response_history"][-1]["reason"] == "最近节奏和以前不一样"

    assert assumptions["mute-me"]["status"] == "revoked"
    assert assumptions["mute-me"]["response_history"][-1]["response"] == "mute"

    durable_claims = ((prefs.inferred or {}).get(INFERENCE_PIPELINE_KEY) or {}).get("claims") or {}
    assert durable_claims["confirm-me"]["status"] == "trial"
    assert "reject-me" not in durable_claims
    assert "mute-me" not in durable_claims

    corrections = (
        (await db_session.execute(select(MemoryCorrection).where(MemoryCorrection.user_id == user_id))).scalars().all()
    )
    assert {item.action for item in corrections} == {"confirm", "incorrect", "mute"}
