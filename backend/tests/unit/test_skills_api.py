from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.skills import router
from app.models.user import User

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_skills_api_crud_extract_and_share_flow(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    async def _fake_extract(self, **_kwargs):
        return {
            "name": "Exam Triage",
            "pattern_template": "Scope first.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": [],
            "rejected": False,
        }

    monkeypatch.setattr("app.api.v1.skills.SkillExtractService._call_llm", _fake_extract)
    monkeypatch.setattr("app.services.skill_extract_service.settings.SPARKLE_SKILL_EXTRACT_ENABLED", True)
    monkeypatch.setattr("app.services.skill_share.service.settings.SPARKLE_SKILL_SHARE_ENABLED", True)

    async def _share_safe(*_args, **_kwargs):
        return []

    monkeypatch.setattr("app.services.skill_share.service.SkillShareService.scan_for_pii", _share_safe)
    monkeypatch.setattr("app.services.skill_share.service.SkillShareService.detect_injection", _share_safe)

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post(
            "/api/v1/skills",
            json={
                "name": "Exam Triage",
                "pattern_template": "Scope first.",
                "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
                "examples": [],
            },
        )
        assert create_resp.status_code == 201
        skill_id = create_resp.json()["id"]

        list_resp = await ac.get("/api/v1/skills")
        assert list_resp.status_code == 200
        assert len(list_resp.json()["items"]) == 1

        extract_resp = await ac.post(
            "/api/v1/skills/drafts/extract",
            json={
                "trigger_type": "explicit_phrase",
                "consent_text": "以后这样做，记住这种方式",
                "user_message": "我快考试了。",
                "assistant_message": "先缩小范围。",
                "seconds_since_response": 20,
            },
        )
        assert extract_resp.status_code == 200
        assert extract_resp.json()["draft"]["name"] == "Exam Triage"

        share_resp = await ac.post(f"/api/v1/skills/{skill_id}/share")
        assert share_resp.status_code == 200
        shared_skill_id = share_resp.json()["shared_skill_id"]

        shared_list_resp = await ac.get("/api/v1/skills/shared")
        assert shared_list_resp.status_code == 200
        assert len(shared_list_resp.json()["items"]) == 1

        fork_resp = await ac.post(f"/api/v1/skills/shared/{shared_skill_id}/fork")
        assert fork_resp.status_code == 201
        assert fork_resp.json()["forked_from_share_id"] == shared_skill_id

    app.dependency_overrides = {}
