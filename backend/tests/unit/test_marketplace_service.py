from __future__ import annotations

import pytest

from app.models.marketplace import PackAdoptionHistory, UserSkillAdoption  # noqa: F401
from app.models.user import User
from app.signals.marketplace import MarketplacePersistenceService, SkillCard


async def _user(db_session, username: str = "marketplace_user") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _card(card_id: str = "sk_marketplace_test") -> SkillCard:
    return SkillCard(
        card_id=card_id,
        name="Worked example repair",
        description="Use a worked example before a drill when transfer fails.",
        goal_type="exam",
        domain="computer_science",
        author_id="00000000-0000-0000-0000-000000000001",
        trigger_condition="transfer_failure",
        action_template="show worked example then ask for a near-transfer drill",
        expected_outcome="task_started_and_completed",
        evidence_grade=3,
        evidence_summary="12 supported episodes, 9 effective outcomes",
        episode_count=12,
        success_rate=0.75,
        context_signatures=[{"domain": "computer_science", "state_key": "transfer_failure"}],
        status="active",
    )


@pytest.mark.asyncio
async def test_marketplace_rejects_pii_before_listing(db_session) -> None:
    service = MarketplacePersistenceService(db_session)
    card = _card("sk_pii_reject")
    card.description = "Student email is jane@example.com"

    with pytest.raises(ValueError, match="pii_detected"):
        await service.register_skill_card(card)


@pytest.mark.asyncio
async def test_marketplace_adoption_requires_explicit_confirmation(db_session) -> None:
    user = await _user(db_session)
    service = MarketplacePersistenceService(db_session)
    card = await service.register_skill_card(_card())

    with pytest.raises(ValueError, match="explicit_confirmation_required"):
        await service.adopt_asset(
            user_id=user.id,
            asset_id=card.skill_id,
            asset_type="skill",
            confirm=False,
        )

    adoption = await service.adopt_asset(
        user_id=user.id,
        asset_id=card.skill_id,
        asset_type="skill",
        confirm=True,
        trace_id="trace-adopt-1",
    )

    assert adoption.explicit_confirm is True
    assert adoption.status == "active"
    assert adoption.preview_snapshot["requires_explicit_confirm"] is True


@pytest.mark.asyncio
async def test_marketplace_negative_outcome_auto_deprecates_asset(db_session) -> None:
    user = await _user(db_session, "marketplace_negative")
    service = MarketplacePersistenceService(db_session)
    card = await service.register_skill_card(_card("sk_deprecate"))
    adoption = await service.adopt_asset(
        user_id=user.id,
        asset_id=card.skill_id,
        asset_type="skill",
        confirm=True,
    )

    await service.record_impact(
        user_id=user.id,
        adoption_id=adoption.id,
        trace_id="trace-negative-1",
        impact_type="task",
        impact_summary="Task got worse after adoption",
        outcome="negative",
    )
    refreshed = await service.get_skill(card.skill_id)

    assert refreshed is not None
    assert refreshed.status == "deprecated"
    assert refreshed.auto_deprecation_reason == "negative_feedback_rate"
    assert refreshed.negative_feedback_rate == 1.0


@pytest.mark.asyncio
async def test_marketplace_skill_version_rollback(db_session) -> None:
    service = MarketplacePersistenceService(db_session)
    card = _card("sk_rollback")
    await service.register_skill_card(card)
    updated = _card("sk_rollback")
    updated.name = "Updated worked example repair"
    updated.version = 2
    await service.register_skill_card(updated)

    rolled_back = await service.rollback_skill("sk_rollback")

    assert rolled_back.name == "Worked example repair"
    assert rolled_back.version == 1
