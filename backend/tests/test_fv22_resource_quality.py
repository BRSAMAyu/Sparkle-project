"""
FV-22: 社群资源质量评分 + cohort 阈值上调
==========================================

Tests:
1. CommunityResourceScorer.compute_quality_score — formula correctness
2. Auto-hide threshold (< 0.3)
3. flag_misleading — immediate penalty
4. COHORT_AGGREGATION_MIN_K = 5
5. update_resource_quality — DB persistence
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.models.community import Group, GroupMember, GroupRole, GroupType, SharedResource
from app.models.user import User
from app.services.community_service import (
    COHORT_AGGREGATION_MIN_K,
    CommunityResourceScorer,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Unit Tests: compute_quality_score
# =============================================================================


class TestComputeQualityScore:
    """Pure function tests for the quality scoring formula."""

    def test_all_zeros(self):
        score = CommunityResourceScorer.compute_quality_score(
            adoption_count=0,
            outcome_effectiveness=0.0,
            negative_feedback_rate=0.0,
            scope_match=0.0,
        )
        assert score == 0.0

    def test_max_adoption_only(self):
        score = CommunityResourceScorer.compute_quality_score(
            adoption_count=100,
            outcome_effectiveness=0.0,
            negative_feedback_rate=0.0,
            scope_match=0.0,
        )
        assert 0.29 < score <= 0.3

    def test_max_outcome_only(self):
        score = CommunityResourceScorer.compute_quality_score(
            adoption_count=0,
            outcome_effectiveness=1.0,
            negative_feedback_rate=0.0,
            scope_match=0.0,
        )
        assert 0.29 < score <= 0.3

    def test_negative_feedback_penalty(self):
        base = CommunityResourceScorer.compute_quality_score(
            adoption_count=10,
            outcome_effectiveness=0.5,
            negative_feedback_rate=0.0,
            scope_match=0.5,
        )
        penalized = CommunityResourceScorer.compute_quality_score(
            adoption_count=10,
            outcome_effectiveness=0.5,
            negative_feedback_rate=0.5,
            scope_match=0.5,
        )
        assert penalized < base

    def test_high_negative_feedback_can_go_negative_clamped(self):
        score = CommunityResourceScorer.compute_quality_score(
            adoption_count=0,
            outcome_effectiveness=0.0,
            negative_feedback_rate=1.0,
            scope_match=0.0,
        )
        assert score == 0.0  # Clamped to 0

    def test_perfect_score(self):
        score = CommunityResourceScorer.compute_quality_score(
            adoption_count=100,
            outcome_effectiveness=1.0,
            negative_feedback_rate=0.0,
            scope_match=1.0,
        )
        # W_ADOPTION(0.3) + W_OUTCOME(0.3) + W_SCOPE(0.15) = 0.75
        assert score == 0.75

    def test_scope_match_contribution(self):
        no_scope = CommunityResourceScorer.compute_quality_score(
            adoption_count=10,
            outcome_effectiveness=0.5,
            negative_feedback_rate=0.0,
            scope_match=0.0,
        )
        with_scope = CommunityResourceScorer.compute_quality_score(
            adoption_count=10,
            outcome_effectiveness=0.5,
            negative_feedback_rate=0.0,
            scope_match=1.0,
        )
        assert with_scope > no_scope

    def test_score_bounded_zero_one(self):
        for neg in [0.0, 0.5, 1.0]:
            for outcome in [0.0, 0.5, 1.0]:
                score = CommunityResourceScorer.compute_quality_score(
                    adoption_count=5,
                    outcome_effectiveness=outcome,
                    negative_feedback_rate=neg,
                    scope_match=0.5,
                )
                assert 0.0 <= score <= 1.0


class TestShouldHide:
    def test_below_threshold_hidden(self):
        assert CommunityResourceScorer.should_hide(0.29) is True

    def test_at_threshold_not_hidden(self):
        assert CommunityResourceScorer.should_hide(0.3) is False

    def test_above_threshold_not_hidden(self):
        assert CommunityResourceScorer.should_hide(0.5) is False

    def test_zero_hidden(self):
        assert CommunityResourceScorer.should_hide(0.0) is True


class TestCohortThreshold:
    def test_min_k_is_five(self):
        assert COHORT_AGGREGATION_MIN_K == 5


# =============================================================================
# Integration Tests: DB persistence
# =============================================================================


@pytest.fixture
async def setup_shared_resource(db_session):
    """Create a user, group, and shared resource for testing."""
    user = User(
        username=f"scorer_{uuid4().hex[:8]}",
        nickname="Scorer Tester",
        email=f"scorer_{uuid4().hex[:8]}@example.com",
        hashed_password="hash",
    )
    db_session.add(user)
    await db_session.flush()

    group = Group(
        name="Quality Test Group",
        type=GroupType.SQUAD,
        max_members=20,
    )
    db_session.add(group)
    await db_session.flush()

    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=GroupRole.OWNER,
    )
    db_session.add(member)

    resource = SharedResource(
        group_id=group.id,
        shared_by=user.id,
        permission="view",
        view_count=10,
        save_count=2,
        adoption_count=0,
        negative_feedback_count=0,
        quality_score=0.0,
        quality_hidden=False,
    )
    db_session.add(resource)
    await db_session.flush()

    return user, group, resource


class TestUpdateResourceQuality:
    @pytest.mark.asyncio
    async def test_update_sets_score(self, db_session, setup_shared_resource):
        user, group, resource = setup_shared_resource
        score = await CommunityResourceScorer.update_resource_quality(db_session, resource.id)
        assert score is not None
        assert score > 0.0

        await db_session.refresh(resource)
        assert resource.quality_score == score

    @pytest.mark.asyncio
    async def test_nonexistent_returns_none(self, db_session):
        score = await CommunityResourceScorer.update_resource_quality(db_session, uuid4())
        assert score is None

    @pytest.mark.asyncio
    async def test_high_negative_feedback_auto_hides(self, db_session, setup_shared_resource):
        user, group, resource = setup_shared_resource
        resource.negative_feedback_count = 8
        resource.view_count = 10
        resource.save_count = 0
        resource.adoption_count = 0
        await db_session.flush()

        score = await CommunityResourceScorer.update_resource_quality(db_session, resource.id)
        assert CommunityResourceScorer.should_hide(score)

        await db_session.refresh(resource)
        assert resource.quality_hidden is True


class TestFlagMisleading:
    @pytest.mark.asyncio
    async def test_flag_increments_neg_count(self, db_session, setup_shared_resource):
        user, group, resource = setup_shared_resource
        original_neg = resource.negative_feedback_count

        new_score = await CommunityResourceScorer.flag_misleading(db_session, resource.id, user.id)
        assert new_score is not None

        await db_session.refresh(resource)
        assert resource.negative_feedback_count == original_neg + 1

    @pytest.mark.asyncio
    async def test_flag_applies_extra_penalty(self, db_session, setup_shared_resource):
        user, group, resource = setup_shared_resource
        # Set up a resource with decent stats
        resource.adoption_count = 5
        resource.view_count = 20
        resource.save_count = 5
        resource.negative_feedback_count = 0
        await db_session.flush()

        base_score = await CommunityResourceScorer.update_resource_quality(db_session, resource.id)
        flagged_score = await CommunityResourceScorer.flag_misleading(db_session, resource.id, user.id)

        assert flagged_score < base_score

    @pytest.mark.asyncio
    async def test_flag_nonexistent_returns_none(self, db_session):
        result = await CommunityResourceScorer.flag_misleading(db_session, uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_repeated_flags_can_hide(self, db_session, setup_shared_resource):
        user, group, resource = setup_shared_resource
        resource.adoption_count = 0
        resource.view_count = 5
        resource.save_count = 0
        await db_session.flush()

        for _ in range(4):
            await CommunityResourceScorer.flag_misleading(db_session, resource.id, user.id)

        await db_session.refresh(resource)
        assert resource.quality_hidden is True
