from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.plan import Plan, PlanType
from app.models.recommendation import UserItemInteraction
from app.models.user import SearchVisibility, User, UserStatus
from app.schemas.community import GroupTypeEnum
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService
from app.core.profile_context import (
    ActivePattern,
    CognitiveSummary,
    KnowledgeSummary,
    ProfileContext,
)


def _make_user(
    *,
    username: str,
    searchable_by: SearchVisibility = SearchVisibility.EVERYONE,
    flame_level: int = 5,
    last_login_hours_ago: int = 4,
) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
        status=UserStatus.ONLINE,
        searchable_by=searchable_by,
        flame_level=flame_level,
        last_login_at=datetime.utcnow() - timedelta(hours=last_login_hours_ago),
    )


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


def _profile_context(
    *,
    subjects: list[str],
    depth: float,
    curiosity: float,
    focus: int,
    learning_style: str = "balanced",
    feedback_style: str = "balanced",
    mastery: float = 0.5,
    pattern_name: str = "steady learner",
    pattern_type: str = "execution",
    risk_signals: list[str] | None = None,
) -> ProfileContext:
    return ProfileContext(
        preferences={
            "depth_preference": depth,
            "curiosity_preference": curiosity,
            "focus_duration_preference": focus,
            "learning_style": learning_style,
            "feedback_style": feedback_style,
        },
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=mastery,
            active_learning_subjects=subjects,
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[
                ActivePattern(
                    pattern_name=pattern_name,
                    pattern_type=pattern_type,
                    confidence=0.85,
                    policy_signals=[],
                )
            ],
            dominant_pattern_type=pattern_type,
            risk_signals=risk_signals or [],
        ),
    )


@pytest_asyncio.fixture
async def recommendation_feedback_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None, "contexts": {}}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    async def _fake_profile_context(self, user_id):
        return state["contexts"][str(user_id)]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(ProfileContextService, "get_profile_context", _fake_profile_context)

    yield app, state

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_friend_feedback_updates_tuning_and_changes_recommendation_score(
    recommendation_feedback_app,
    db_session,
):
    app, state = recommendation_feedback_app
    current = _make_user(username="current_feedback")
    candidate = _make_user(username="candidate_similarity", flame_level=7, last_login_hours_ago=1)
    await _commit_all(db_session, current, candidate)

    state["current_user"] = current
    state["contexts"] = {
        str(current.id): _profile_context(
            subjects=["英语", "写作"],
            depth=0.45,
            curiosity=0.55,
            focus=20,
            mastery=0.38,
            pattern_name="delay pattern",
            pattern_type="execution",
            risk_signals=["risk.execution_delay"],
        ),
        str(candidate.id): _profile_context(
            subjects=["英语", "写作"],
            depth=0.72,
            curiosity=0.58,
            focus=36,
            mastery=0.71,
            pattern_name="steady finisher",
            pattern_type="planning",
            risk_signals=[],
        ),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        before = await client.get(
            "/community/friends/recommendations",
            params={"strategy": "compatibility", "target": "friend", "limit": 5},
        )
        assert before.status_code == 200
        before_payload = before.json()
        before_breakdown = before_payload[0]["score_breakdown"]
        before_score = before_payload[0]["match_score"]

        feedback = await client.post(
            "/community/friends/recommendations/feedback",
            json={
                "target_user_id": str(candidate.id),
                "strategy": "compatibility",
                "target": "friend",
                "action": "view",
                "source": "friends_tab",
                "score": before_score,
                "overall_score": 2,
                "relevance_score": 2,
                "similarity_score": 1,
                "selected_issues": ["不够相似"],
                "free_text": "这个人跟我不够相似，最好更契合一点。",
            },
        )
        assert feedback.status_code == 200

        after = await client.get(
            "/community/friends/recommendations",
            params={"strategy": "compatibility", "target": "friend", "limit": 5},
        )
        assert after.status_code == 200
        after_payload = after.json()
        after_breakdown = after_payload[0]["score_breakdown"]

        insights = await client.get(
            "/community/recommendations/feedback/insights",
            params={"item_type": "friend"},
        )
        assert insights.status_code == 200

    pref_service = PreferenceService(db_session)
    prefs = await pref_service.get_preferences(current.id)
    tuning = prefs.explicit["recommendation_feedback_tuning"]["friend"]

    assert after_breakdown["subject_overlap"] > before_breakdown["subject_overlap"]
    assert after_payload[0]["match_score"] >= before_score
    assert tuning["feature_weights"]["subject_overlap"] > 1.0
    assert tuning["strategy_bias"]["compatibility"] > 1.0

    insight_payload = insights.json()
    assert insight_payload[0]["recent_feedback_count"] == 1
    assert insight_payload[0]["average_scores"]["similarity_score"] == 1.0
    assert "too_dissimilar" in insight_payload[0]["top_negative_signals"]
    assert insight_payload[0]["global_adjustments"]["subject_overlap"] >= 1.0


@pytest.mark.asyncio
async def test_group_feedback_prompts_and_insights_form_closed_loop(
    recommendation_feedback_app,
    db_session,
):
    app, state = recommendation_feedback_app
    current = _make_user(username="group_feedback_user")
    owner = _make_user(username="group_owner")
    group = Group(
        name="刷题社群",
        description="一起刷题",
        type=GroupType.SQUAD,
        focus_tags=["算法", "刷题"],
        total_flame_power=1800,
        today_checkin_count=6,
        is_public=True,
        max_members=30,
    )
    await _commit_all(db_session, current, owner, group)

    plan = Plan(
        user_id=current.id,
        name="算法计划",
        type=PlanType.GROWTH,
        subject="算法",
    )
    await _commit_all(
        db_session,
        GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
        plan,
    )

    state["current_user"] = current
    state["contexts"] = {str(current.id): _profile_context(subjects=["算法"], depth=0.5, curiosity=0.5, focus=25)}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        raw_feedback = await client.post(
            "/community/groups/recommendations/feedback",
            json={
                "group_id": str(group.id),
                "action": "view",
                "source": "discover",
                "reason_types": ["tag_overlap"],
            },
        )
        assert raw_feedback.status_code == 200

    interaction = (
        await db_session.execute(
            select(UserItemInteraction).where(
                UserItemInteraction.user_id == current.id,
                UserItemInteraction.item_id == group.id,
            )
        )
    ).scalar_one()
    interaction.created_at = datetime.utcnow() - timedelta(hours=2)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        prompts = await client.get(
            "/community/recommendations/feedback/prompts",
            params={"item_type": "group"},
        )
        assert prompts.status_code == 200
        prompt_payload = prompts.json()
        assert prompt_payload
        prompt_id = prompt_payload[0]["prompt_id"]
        assert prompt_payload[0]["group"]["name"] == "刷题社群"
        assert prompt_payload[0]["stage"] == "immediate"

        structured_feedback = await client.post(
            "/community/groups/recommendations/feedback",
            json={
                "group_id": str(group.id),
                "action": "view",
                "source": "discover",
                "reason_types": ["tag_overlap"],
                "prompt_id": prompt_id,
                "overall_score": 2,
                "interest_match_score": 1,
                "activity_score": 3,
                "selected_issues": ["标签不准"],
                "free_text": "这个社群兴趣不匹配，标签不准。",
            },
        )
        assert structured_feedback.status_code == 200

        prompts_after = await client.get(
            "/community/recommendations/feedback/prompts",
            params={"item_type": "group"},
        )
        insights = await client.get(
            "/community/recommendations/feedback/insights",
            params={"item_type": "group"},
        )

    assert prompts_after.status_code == 200
    assert prompts_after.json() == []
    assert insights.status_code == 200

    pref_service = PreferenceService(db_session)
    prefs = await pref_service.get_preferences(current.id)
    tuning = prefs.explicit["recommendation_feedback_tuning"]["group"]

    insight_payload = insights.json()
    assert insight_payload[0]["recent_feedback_count"] == 1
    assert insight_payload[0]["average_scores"]["interest_match_score"] == 1.0
    assert "want_more_tag_match" in insight_payload[0]["top_negative_signals"]
    assert tuning["feature_weights"]["tag_score"] > 1.0
    assert insight_payload[0]["user_tuning"]["feature_weights"]["tag_score"] > 1.0
    assert insight_payload[0]["global_adjustments"]["tag_score"] >= 1.0
    assert prompt_payload[0]["group"]["type"] == GroupTypeEnum.SQUAD.value
