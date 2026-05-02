"""
Tests for FV-21: Recall ML triggers + value_reason

Covers:
1. 4 new recall triggers (long_silence, context_window_optimal, material_decay, cohort_pattern_alert)
2. RecallRanker ML scoring (decision tree + logistic regression + blend)
3. Integration: triggers produce value_reason, effort_estimate, deadline_pressure
4. RecallNotificationBuilder support for new trigger types
5. Edge cases and boundary conditions
"""

from __future__ import annotations

import math

import pytest

from app.services.ml.recall_ranker import RecallFeatures, RecallRanker
from app.signals.recall_notification import RecallNotificationBuilder
from app.signals.recall_opportunity import RecallOpportunityDetector


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def detector() -> RecallOpportunityDetector:
    return RecallOpportunityDetector()


@pytest.fixture
def detector_with_ranker() -> RecallOpportunityDetector:
    ranker = RecallRanker()
    return RecallOpportunityDetector(ranker=ranker)


@pytest.fixture
def ranker() -> RecallRanker:
    return RecallRanker()


@pytest.fixture
def notification_builder() -> RecallNotificationBuilder:
    return RecallNotificationBuilder()


# ═══════════════════════════════════════════════════════════════════════
# 1. RecallRanker Tests
# ═══════════════════════════════════════════════════════════════════════

class TestRecallRanker:
    """Test ML-based recall scoring."""

    def test_basic_score_range(self, ranker: RecallRanker):
        """Score is always in [0.0, 1.0]."""
        features = RecallFeatures()
        score = ranker.score(features)
        assert 0.0 <= score <= 1.0

    def test_crisis_override(self, ranker: RecallRanker):
        """Near-deadline + low fatigue → high score."""
        features = RecallFeatures(
            deadline_proximity=0.9,
            fatigue_state=0.2,
            goal_value=0.8,
        )
        score = ranker.score(features)
        assert score > 0.8

    def test_fatigue_penalty(self, ranker: RecallRanker):
        """Critical fatigue heavily reduces score."""
        good_features = RecallFeatures(
            goal_value=0.8,
            deadline_proximity=0.5,
            fatigue_state=0.1,
        )
        fatigued_features = RecallFeatures(
            goal_value=0.8,
            deadline_proximity=0.5,
            fatigue_state=0.9,
        )
        good_score = ranker.score(good_features)
        fatigued_score = ranker.score(fatigued_features)
        assert good_score > fatigued_score
        assert fatigued_score < 0.5  # Heavy penalty

    def test_high_decay_high_goal(self, ranker: RecallRanker):
        """High knowledge decay + high goal value → elevated score."""
        features = RecallFeatures(
            decay_factor=0.8,
            goal_value=0.8,
        )
        score = ranker.score(features)
        assert score > 0.6

    def test_low_everything(self, ranker: RecallRanker):
        """Low values across the board → baseline-ish score."""
        features = RecallFeatures(
            goal_value=0.1,
            decay_factor=0.1,
            user_response_rate=0.1,
            deadline_proximity=0.0,
        )
        score = ranker.score(features)
        assert score < 0.6

    def test_score_trigger_convenience(self, ranker: RecallRanker):
        """score_trigger() convenience method works."""
        score = ranker.score_trigger(
            "undigested_material",
            goal_value=0.7,
            decay_factor=0.5,
        )
        assert 0.0 <= score <= 1.0

    def test_features_to_vector(self):
        """Feature vector has 8 dimensions."""
        features = RecallFeatures()
        vec = features.to_vector()
        assert len(vec) == 8
        assert all(isinstance(v, float) for v in vec)

    def test_ab_test_arms(self, ranker: RecallRanker):
        """A/B test arms produce different scores."""
        features = RecallFeatures(goal_value=0.6)
        default = ranker.get_ab_test_arm_score(features, "default")
        aggressive = ranker.get_ab_test_arm_score(features, "aggressive")
        conservative = ranker.get_ab_test_arm_score(features, "conservative")
        dt_only = ranker.get_ab_test_arm_score(features, "dt_only")
        lr_only = ranker.get_ab_test_arm_score(features, "lr_only")

        assert aggressive > default
        assert conservative < default
        assert 0.0 <= dt_only <= 1.0
        assert 0.0 <= lr_only <= 1.0

    def test_model_version(self, ranker: RecallRanker):
        """Model version is set."""
        assert ranker.MODEL_VERSION.startswith("v")

    @pytest.mark.asyncio
    async def test_get_model_version_default(self, ranker: RecallRanker):
        """get_model_version returns default without Redis."""
        version = await ranker.get_model_version()
        assert version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_get_user_response_rate_no_redis(self, ranker: RecallRanker):
        """get_user_response_rate returns 0.5 default without Redis."""
        rate = await ranker.get_user_response_rate("u1", "test")
        assert rate == 0.5

    @pytest.mark.asyncio
    async def test_record_training_example_no_redis(self, ranker: RecallRanker):
        """record_training_example is a no-op without Redis."""
        features = RecallFeatures()
        # Should not raise
        await ranker.record_training_example("u1", "test", features, True)


# ═══════════════════════════════════════════════════════════════════════
# 2. New Trigger: long_silence
# ═══════════════════════════════════════════════════════════════════════

class TestLongSilenceTrigger:
    """Test long_silence trigger detection."""

    def test_triggers_after_72h(self, detector: RecallOpportunityDetector):
        """72h silence with active goal → triggers."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=80.0,
            has_active_goal=True,
        )
        assert trigger is not None
        assert trigger.trigger_type == "long_silence"
        assert trigger.value_reason != ""
        assert trigger.effort_estimate != ""
        assert trigger.deadline_pressure != ""

    def test_no_trigger_under_72h(self, detector: RecallOpportunityDetector):
        """Under 72h → no trigger."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=50.0,
            has_active_goal=True,
        )
        assert trigger is None

    def test_no_trigger_exam_period(self, detector: RecallOpportunityDetector):
        """Exam period → skip, use pre_exam_silence instead."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=100.0,
            has_active_goal=True,
            is_exam_period=True,
        )
        assert trigger is None

    def test_no_trigger_no_active_goal(self, detector: RecallOpportunityDetector):
        """No active goal → don't disturb."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=100.0,
            has_active_goal=False,
        )
        assert trigger is None

    def test_high_urgency_after_7_days(self, detector: RecallOpportunityDetector):
        """Over 7 days silence → high urgency."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=200.0,
            has_active_goal=True,
        )
        assert trigger is not None
        assert trigger.urgency == "high"

    def test_medium_urgency_under_7_days(self, detector: RecallOpportunityDetector):
        """Under 7 days silence → medium urgency."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=80.0,
            has_active_goal=True,
        )
        assert trigger is not None
        assert trigger.urgency == "medium"

    def test_silence_days_in_context(self, detector: RecallOpportunityDetector):
        """Context contains silence_days."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=96.0,
            has_active_goal=True,
        )
        assert trigger is not None
        assert trigger.context["silence_days"] == 4.0


# ═══════════════════════════════════════════════════════════════════════
# 3. New Trigger: context_window_optimal
# ═══════════════════════════════════════════════════════════════════════

class TestContextWindowOptimalTrigger:
    """Test context_window_optimal trigger detection."""

    def test_triggers_in_optimal_window(self, detector: RecallOpportunityDetector):
        """Within optimal interval window → triggers."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=23.0,  # ~1x interval
            mastery_level=0.5,
            optimal_interval_hours=24.0,
        )
        assert trigger is not None
        assert trigger.trigger_type == "context_window_optimal"
        assert trigger.value_reason != ""
        assert trigger.effort_estimate != ""
        assert trigger.deadline_pressure != ""

    def test_no_trigger_too_early(self, detector: RecallOpportunityDetector):
        """Review too early → no trigger."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=10.0,
            mastery_level=0.5,
            optimal_interval_hours=24.0,
        )
        assert trigger is None

    def test_no_trigger_too_late(self, detector: RecallOpportunityDetector):
        """Review too late → no trigger."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=50.0,
            mastery_level=0.5,
            optimal_interval_hours=24.0,
        )
        assert trigger is None

    def test_no_trigger_mastered(self, detector: RecallOpportunityDetector):
        """Already mastered → no trigger."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=23.0,
            mastery_level=0.95,
            optimal_interval_hours=24.0,
        )
        assert trigger is None

    def test_no_trigger_fatigued(self, detector: RecallOpportunityDetector):
        """Critical fatigue → no trigger."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=23.0,
            mastery_level=0.5,
            optimal_interval_hours=24.0,
            current_fatigue=0.8,
        )
        assert trigger is None

    def test_decay_factor_in_context(self, detector: RecallOpportunityDetector):
        """Context contains computed decay_factor."""
        trigger = detector.check_context_window_optimal(
            user_id="u1",
            last_review_hours=24.0,
            mastery_level=0.6,
            optimal_interval_hours=24.0,
        )
        assert trigger is not None
        assert "decay_factor" in trigger.context


# ═══════════════════════════════════════════════════════════════════════
# 4. New Trigger: material_decay
# ═══════════════════════════════════════════════════════════════════════

class TestMaterialDecayTrigger:
    """Test material_decay trigger detection."""

    def test_triggers_on_decay(self, detector: RecallOpportunityDetector):
        """Declining mastery + old enough → triggers."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=7.0,
            mastery_delta=-0.15,
            relevance_to_goal=0.7,
        )
        assert trigger is not None
        assert trigger.trigger_type == "material_decay"
        assert trigger.value_reason != ""
        assert trigger.effort_estimate != ""
        assert trigger.deadline_pressure != ""

    def test_no_trigger_too_recent(self, detector: RecallOpportunityDetector):
        """Under 3 days → no trigger."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=2.0,
            mastery_delta=-0.2,
            relevance_to_goal=0.7,
        )
        assert trigger is None

    def test_no_trigger_stable_mastery(self, detector: RecallOpportunityDetector):
        """Mastery is stable or growing → no trigger."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=7.0,
            mastery_delta=0.05,
            relevance_to_goal=0.7,
        )
        assert trigger is None

    def test_no_trigger_already_recalled(self, detector: RecallOpportunityDetector):
        """Already recalled → no trigger."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=7.0,
            mastery_delta=-0.15,
            relevance_to_goal=0.7,
            has_been_recalled=True,
        )
        assert trigger is None

    def test_no_trigger_slow_decay(self, detector: RecallOpportunityDetector):
        """Decay rate too slow → no trigger."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=7.0,
            mastery_delta=-0.01,
            relevance_to_goal=0.7,
        )
        assert trigger is None

    def test_medium_urgency_high_decay(self, detector: RecallOpportunityDetector):
        """High decay rate → medium urgency."""
        trigger = detector.check_material_decay(
            user_id="u1",
            material_id="m1",
            days_since_diagnosis=10.0,
            mastery_delta=-0.5,
            relevance_to_goal=0.8,
        )
        assert trigger is not None
        assert trigger.urgency == "medium"


# ═══════════════════════════════════════════════════════════════════════
# 5. New Trigger: cohort_pattern_alert
# ═══════════════════════════════════════════════════════════════════════

class TestCohortPatternAlertTrigger:
    """Test cohort_pattern_alert trigger detection."""

    def test_triggers_when_behind_cohort(self, detector: RecallOpportunityDetector):
        """User below cohort average + active cohort → triggers."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.7,
            user_relative_position="below",
        )
        assert trigger is not None
        assert trigger.trigger_type == "cohort_pattern_alert"
        assert trigger.value_reason != ""
        assert trigger.effort_estimate != ""
        assert trigger.deadline_pressure != ""

    def test_no_trigger_low_cohort_activity(self, detector: RecallOpportunityDetector):
        """Cohort not active enough → no trigger."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.3,
            user_relative_position="below",
        )
        assert trigger is None

    def test_no_trigger_user_above_average(self, detector: RecallOpportunityDetector):
        """User is above average → no trigger."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.7,
            user_relative_position="above",
        )
        assert trigger is None

    def test_no_trigger_user_at_average(self, detector: RecallOpportunityDetector):
        """User is at average → no trigger."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.7,
            user_relative_position="average",
        )
        assert trigger is None

    def test_always_low_urgency(self, detector: RecallOpportunityDetector):
        """Cohort alerts are always low urgency (gentle nudge)."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.8,
            user_relative_position="below",
        )
        assert trigger is not None
        assert trigger.urgency == "low"

    def test_with_deadline(self, detector: RecallOpportunityDetector):
        """Deadline proximity is considered in ML scoring."""
        trigger = detector.check_cohort_pattern_alert(
            user_id="u1",
            cohort_activity_rate=0.7,
            user_relative_position="below",
            days_until_deadline=3.0,
        )
        assert trigger is not None


# ═══════════════════════════════════════════════════════════════════════
# 6. Integration: ML scoring in triggers
# ═══════════════════════════════════════════════════════════════════════

class TestMLScoringIntegration:
    """Test that triggers use ML scoring when ranker is provided."""

    def test_original_triggers_have_value_reason(self, detector: RecallOpportunityDetector):
        """All original 4 triggers produce value_reason."""
        # 1. undigested_material
        t1 = detector.check_undigested_material(
            user_id="u1", uploaded_files_count=3, diagnosed_files_count=1,
            hours_since_upload=2.0,
        )
        assert t1 is not None
        assert t1.value_reason != ""
        assert t1.effort_estimate != ""
        assert t1.deadline_pressure != ""

        # 2. task_not_started
        t2 = detector.check_task_not_started(
            user_id="u1", task_id="t1", hours_since_assignment=3.0,
            has_started=False,
        )
        assert t2 is not None
        assert t2.value_reason != ""

        # 3. task_missed
        t3 = detector.check_task_missed(
            user_id="u1", task_id="t1", deadline_hours=-3.0,
            is_completed=False,
        )
        assert t3 is not None
        assert t3.value_reason != ""

        # 4. pre_exam_silence
        t4 = detector.check_pre_exam_silence(
            user_id="u1", exam_deadline_days=1.5,
            hours_since_last_activity=5.0,
        )
        assert t4 is not None
        assert t4.value_reason != ""

    def test_detector_with_ranker_produces_scores(self, detector_with_ranker: RecallOpportunityDetector):
        """With ranker, scores differ from rule-only."""
        t = detector_with_ranker.check_undigested_material(
            user_id="u1", uploaded_files_count=3, diagnosed_files_count=1,
            hours_since_upload=2.0,
        )
        assert t is not None
        assert t.recall_score > 0.0

    def test_detector_without_ranker_still_works(self, detector: RecallOpportunityDetector):
        """Without ranker, detector still works (neutral ML score)."""
        t = detector.check_undigested_material(
            user_id="u1", uploaded_files_count=3, diagnosed_files_count=1,
            hours_since_upload=2.0,
        )
        assert t is not None
        assert 0.0 <= t.recall_score <= 1.0

    def test_to_actionable_signal_new_trigger(self, detector: RecallOpportunityDetector):
        """New triggers convert to ActionableSignal correctly."""
        trigger = detector.check_long_silence(
            user_id="u1",
            hours_since_last_activity=100.0,
            has_active_goal=True,
        )
        assert trigger is not None
        signal = detector.to_actionable_signal(trigger)
        assert signal.state_key == "recall_needed"
        assert signal.claim == "long_silence"
        assert signal.source_system == "recall_opportunity"

    def test_cooldown_for_new_triggers(self, detector: RecallOpportunityDetector):
        """All 8 trigger types have cooldown values."""
        trigger_types = [
            "undigested_material", "task_not_started", "task_missed", "pre_exam_silence",
            "long_silence", "context_window_optimal", "material_decay", "cohort_pattern_alert",
        ]
        for tt in trigger_types:
            cd = detector.get_cooldown_seconds(tt)
            assert cd > 0, f"No cooldown for {tt}"


# ═══════════════════════════════════════════════════════════════════════
# 7. Notification Builder support for new triggers
# ═══════════════════════════════════════════════════════════════════════

class TestNotificationBuilderNewTriggers:
    """Test that RecallNotificationBuilder supports all 8 trigger types."""

    def test_build_long_silence_message(self, notification_builder: RecallNotificationBuilder):
        msg = notification_builder.build_message(
            "long_silence", "gentle_checkin",
            {"silence_days": 4},
        )
        assert msg is not None
        assert msg.trigger_type == "long_silence"
        assert "4" in msg.body

    def test_build_context_window_message(self, notification_builder: RecallNotificationBuilder):
        msg = notification_builder.build_message(
            "context_window_optimal", "optimal_review", {},
        )
        assert msg is not None
        assert msg.trigger_type == "context_window_optimal"

    def test_build_material_decay_message(self, notification_builder: RecallNotificationBuilder):
        msg = notification_builder.build_message(
            "material_decay", "decay_alert", {},
        )
        assert msg is not None
        assert msg.trigger_type == "material_decay"

    def test_build_cohort_pattern_message(self, notification_builder: RecallNotificationBuilder):
        msg = notification_builder.build_message(
            "cohort_pattern_alert", "peer_nudge", {},
        )
        assert msg is not None
        assert msg.trigger_type == "cohort_pattern_alert"

    def test_reasoning_templates_exist(self, notification_builder: RecallNotificationBuilder):
        """All 8 trigger types have reasoning templates."""
        for tt in ["undigested_material", "task_not_started", "task_missed", "pre_exam_silence",
                    "long_silence", "context_window_optimal", "material_decay", "cohort_pattern_alert"]:
            assert tt in notification_builder.REASONING_TEMPLATES
            assert tt in notification_builder.VALUE_REASON_TEMPLATES
            assert tt in notification_builder.EFFORT_ESTIMATE_TEMPLATES
            assert tt in notification_builder.DEADLINE_PRESSURE_LABELS

    def test_preference_schema_includes_new_triggers(self, notification_builder: RecallNotificationBuilder):
        """User preference schema includes all 8 trigger types."""
        schema = notification_builder.build_user_preference_schema()
        assert len(schema) == 8
        for tt in ["long_silence", "context_window_optimal", "material_decay", "cohort_pattern_alert"]:
            assert tt in schema
            assert "enabled" in schema[tt]

    def test_notification_message_has_value_reason(self, notification_builder: RecallNotificationBuilder):
        """Built messages have value_reason populated."""
        msg = notification_builder.build_message(
            "long_silence", "gentle_checkin",
            {"silence_days": 4},
        )
        assert msg is not None
        assert msg.value_reason != ""
        assert msg.effort_estimate != ""


# ═══════════════════════════════════════════════════════════════════════
# 8. Edge cases
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_score_always_bounded(self, ranker: RecallRanker):
        """Score never exceeds [0.0, 1.0] even with extreme inputs."""
        extreme_high = RecallFeatures(
            goal_value=1.0, decay_factor=1.0, user_response_rate=1.0,
            fatigue_state=0.0, deadline_proximity=1.0, material_relevance=1.0,
            silence_hours=1.0, cohort_response_rate=1.0,
        )
        extreme_low = RecallFeatures(
            goal_value=0.0, decay_factor=0.0, user_response_rate=0.0,
            fatigue_state=1.0, deadline_proximity=0.0, material_relevance=0.0,
            silence_hours=0.0, cohort_response_rate=0.0,
        )
        assert 0.0 <= ranker.score(extreme_high) <= 1.0
        assert 0.0 <= ranker.score(extreme_low) <= 1.0

    def test_trigger_to_dict_has_all_fields(self, detector: RecallOpportunityDetector):
        """to_dict includes all FV-21 fields."""
        trigger = detector.check_long_silence(
            user_id="u1", hours_since_last_activity=100.0, has_active_goal=True,
        )
        assert trigger is not None
        d = trigger.to_dict()
        assert "trigger_type" in d
        assert "value_reason" in d
        assert "effort_estimate" in d
        assert "deadline_pressure" in d
        assert "recall_score" in d

    def test_blend_function(self):
        """_blend produces weighted average."""
        assert abs(RecallOpportunityDetector._blend(0.8, 0.6) - 0.74) < 0.001
        assert abs(RecallOpportunityDetector._blend(0.0, 1.0) - 0.3) < 0.001

    def test_ab_test_default_arm(self, ranker: RecallRanker):
        """Default arm matches score()."""
        features = RecallFeatures(goal_value=0.5)
        assert ranker.get_ab_test_arm_score(features, "default") == ranker.score(features)

    def test_unknown_arm_returns_default(self, ranker: RecallRanker):
        """Unknown arm falls back to default."""
        features = RecallFeatures(goal_value=0.5)
        assert ranker.get_ab_test_arm_score(features, "unknown_arm") == ranker.score(features)
