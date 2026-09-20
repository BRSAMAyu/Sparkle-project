"""G-01: Evidence-aware mastery model tests.

Acceptance contract under test:
1. Same 30 minutes with different outcomes -> different mastery.
2. No evidence -> mastery does not rise (time-only capped at LEGACY_TIME_MASTERY_CAP).
3. Self-report is never equivalent to quiz evidence of the same value.
4. Legacy data keeps the `legacy_estimate` flag; first real evidence clears it.
5. Formula transparency: every fusion step exposes prior/gain/posterior.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.galaxy import MasteryEvidenceInfo, NodeWithStatus
from app.services.galaxy.mastery_evidence import (
    DECAY_FLOOR,
    EVIDENCE_WEIGHTS,
    LEGACY_PRIOR_VARIANCE,
    LEGACY_TIME_MASTERY_CAP,
    MasteryBelief,
    MasteryEvidenceType,
    EvidenceHistoryEntry,
    EvidenceObservation,
    apply_evidence_decay,
    capped_legacy_mastery,
    classify_audit_reason,
    encode_evidence_reason,
    encode_observation_payload,
    fuse_mastery,
    legacy_time_delta,
    parse_observation_payload,
    recompute_evidence_state,
)
from app.services.galaxy.stats_service import GalaxyStatsService, _mastery_evidence_info


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Soul test 1: same 30 minutes, different outcomes -> different mastery
# ---------------------------------------------------------------------------


class TestSameTimeDifferentOutcome:
    def test_legacy_formula_blind_to_outcome(self):
        """Documents the OLD defect: legacy delta only sees minutes."""
        minutes = 30
        delta = legacy_time_delta(minutes, 3)
        # regardless of outcome, the delta is a constant
        assert delta == pytest.approx(6.0)

    def test_quiz_pass_vs_fail_same_minutes_diverge(self):
        """NEW model: identical 30min session, quiz 85 vs quiz 25 -> different mastery."""
        start = 0.0
        passed = fuse_mastery(start, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.QUIZ, 85, 0.9)])
        failed = fuse_mastery(start, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.QUIZ, 25, 0.9)])
        assert passed.mean > 70
        assert failed.mean < 30
        assert passed.mean != failed.mean

    def test_task_outcome_quality_diverges(self):
        """Same time, task completed well vs abandoned halfway."""
        good = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.TASK_OUTCOME, 80, 0.8)])
        poor = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.TASK_OUTCOME, 20, 0.8)])
        assert good.mean > poor.mean

    def test_time_only_yields_no_mastery_even_after_many_sessions(self):
        """Repeated time-only sessions can never cross the legacy cap."""
        mastery = 0.0
        for _ in range(100):
            mastery = capped_legacy_mastery(mastery, legacy_time_delta(30, 5))
        assert mastery == pytest.approx(LEGACY_TIME_MASTERY_CAP)
        assert mastery < 80  # can never reach "mastered" without evidence


# ---------------------------------------------------------------------------
# Soul test 2: no evidence -> no mastery
# ---------------------------------------------------------------------------


class TestNoEvidenceNoMastery:
    def test_empty_ledger_is_legacy_estimate(self):
        belief = recompute_evidence_state(42.0, [])
        assert belief.is_legacy_estimate is True
        assert belief.mean == pytest.approx(42.0)  # legacy value preserved, not deleted
        assert belief.evidence_count == 0

    def test_time_and_selfreport_do_not_clear_legacy_flag(self):
        now = _utcnow_naive()
        belief = recompute_evidence_state(
            42.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.TIME_ON_TASK, 30, 1.0, now),
                EvidenceHistoryEntry(MasteryEvidenceType.SELF_REPORT, 90, 0.9, now),
            ],
        )
        assert belief.is_legacy_estimate is True

    def test_time_on_task_does_not_move_posterior(self):
        belief = fuse_mastery(20.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.TIME_ON_TASK, 95, 1.0)])
        assert belief.mean == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Soul test 3: self-report != quiz at the same value
# ---------------------------------------------------------------------------


class TestSelfReportSeparateChannel:
    def test_same_value_not_equivalent(self):
        quiz = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.QUIZ, 80, 0.9)])
        report = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.SELF_REPORT, 80, 0.9)])
        assert quiz.mean == pytest.approx(76.92, abs=0.5)
        assert report.mean == pytest.approx(0.0)  # self-report fused nothing
        assert report.self_report_count == 1
        assert quiz.evidence_count == 1

    def test_self_report_recorded_but_flag_stays(self):
        belief = fuse_mastery(30.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.SELF_REPORT, 95, 1.0)])
        assert belief.is_legacy_estimate is True
        assert belief.self_report_count == 1

    def test_chat_signal_weaker_than_quiz(self):
        """Conversation signals move the posterior less than quiz at same value."""
        quiz = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.QUIZ, 80, 0.9)])
        chat = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.CHAT_SIGNAL, 80, 0.9)])
        assert quiz.mean > chat.mean > 0
        assert EVIDENCE_WEIGHTS[MasteryEvidenceType.QUIZ] > EVIDENCE_WEIGHTS[MasteryEvidenceType.CHAT_SIGNAL]


# ---------------------------------------------------------------------------
# Legacy flag lifecycle
# ---------------------------------------------------------------------------


class TestLegacyFlagLifecycle:
    def test_first_quiz_clears_legacy_flag(self):
        now = _utcnow_naive()
        before = recompute_evidence_state(38.0, [])
        after = recompute_evidence_state(38.0, [EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 70, 0.9, now)])
        assert before.is_legacy_estimate is True
        assert after.is_legacy_estimate is False

    def test_quiz_grade_reasons_from_other_flows_clear_flag(self):
        """Error-book / exam-sprint audit rows already represent quiz evidence."""
        assert classify_audit_reason("error_diagnosis") is MasteryEvidenceType.QUIZ
        assert classify_audit_reason("exam_sprint_diagnostic") is MasteryEvidenceType.QUIZ
        assert classify_audit_reason("post_exam_review_weak_node") is MasteryEvidenceType.QUIZ
        assert classify_audit_reason("error_review") is MasteryEvidenceType.QUIZ

    def test_non_evidence_reasons_do_not_classify(self):
        assert classify_audit_reason("focus_session") is None
        assert classify_audit_reason("offline_sync") is None
        assert classify_audit_reason("manual_update") is None
        assert classify_audit_reason("task_complete") is None

    def test_legacy_value_not_deleted_by_fusion(self):
        """Legacy mastery is the prior, not discarded."""
        belief = recompute_evidence_state(50.0, [EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 50, 0.9, _utcnow_naive())])
        assert 40 < belief.mean < 60  # pulled toward agreement, still anchored


# ---------------------------------------------------------------------------
# Decay (testable parameters)
# ---------------------------------------------------------------------------


class TestDecay:
    def test_zero_days_no_decay(self):
        mean, variance = apply_evidence_decay(70.0, 0.05, 0)
        assert mean == pytest.approx(70.0)
        assert variance == pytest.approx(0.05)

    def test_one_half_life_decays_toward_floor(self):
        mean, _ = apply_evidence_decay(70.0, 0.05, 14.0)
        # stability stretches half-life: 1 + (70/100)*2 = 2.4 -> 33.6 days
        effective_half_life = 14.0 * (1 + (70.0 / 100.0) * 2.0)
        assert DECAY_FLOOR < mean < 70.0
        assert mean == pytest.approx(
            DECAY_FLOOR + (70.0 - DECAY_FLOOR) * math.exp(-math.log(2) * 14 / effective_half_life)
        )

    def test_high_mastery_decays_slower(self):
        high, _ = apply_evidence_decay(90.0, 0.05, 30)
        low, _ = apply_evidence_decay(30.0, 0.05, 30)
        # 90 has longer half-life, so decays proportionally less
        assert (high - 90.0) / 90.0 > (low - 30.0) / 30.0

    def test_variance_relaxes_toward_max(self):
        _, variance = apply_evidence_decay(70.0, 0.05, 60)
        assert variance > 0.05
        assert variance <= 0.25

    def test_replay_applies_inter_event_decay(self):
        """Old evidence counts less: replay decays the posterior over gaps."""
        now = _utcnow_naive()
        fresh = recompute_evidence_state(0.0, [EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, now)])
        stale = recompute_evidence_state(
            0.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, now - timedelta(days=90)),
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 0, 0.9, now),
            ],
        )
        assert stale.mean < fresh.mean


# ---------------------------------------------------------------------------
# Transparency
# ---------------------------------------------------------------------------


class TestTransparency:
    def test_trace_exposes_prior_observation_and_posterior(self):
        belief = fuse_mastery(10.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.QUIZ, 60, 0.8)])
        assert len(belief.trace) == 1
        step = belief.trace[0]
        assert step.evidence_type == "quiz"
        assert step.prior_mean == pytest.approx(10.0)
        assert step.observed_value == pytest.approx(60.0)
        assert 0 < step.kalman_gain < 1
        assert step.posterior_mean == pytest.approx(belief.mean)
        # manual recomputation of the published formula
        expected_gain = step.prior_variance / (step.prior_variance + step.observation_variance)
        assert step.kalman_gain == pytest.approx(expected_gain, abs=1e-5)

    def test_posterior_variance_never_exceeds_bounds(self):
        belief = fuse_mastery(0.0, LEGACY_PRIOR_VARIANCE, [EvidenceObservation(MasteryEvidenceType.MATERIAL_REF, 100, 1.0)])
        assert 0.01 <= belief.variance <= 0.25

    def test_evidence_value_validation(self):
        with pytest.raises(ValueError):
            EvidenceObservation(MasteryEvidenceType.QUIZ, 120, 0.9)
        with pytest.raises(ValueError):
            EvidenceObservation(MasteryEvidenceType.QUIZ, 50, 1.5)


# ---------------------------------------------------------------------------
# Audit-log codec
# ---------------------------------------------------------------------------


class TestCodec:
    def test_reason_roundtrip(self):
        assert encode_evidence_reason(MasteryEvidenceType.QUIZ) == "evidence:quiz"
        assert classify_audit_reason("evidence:task_outcome") is MasteryEvidenceType.TASK_OUTCOME
        assert classify_audit_reason("evidence:bogus") is None

    def test_observation_payload_roundtrip(self):
        payload = encode_observation_payload(82.34, 0.9)
        assert len(payload) <= 100
        assert parse_observation_payload(payload) == (82.34, 0.9)
        assert parse_observation_payload("some-task-uuid") is None
        assert parse_observation_payload(None) is None


# ---------------------------------------------------------------------------
# Spark integration (mock-based, no DB)
# ---------------------------------------------------------------------------


def _make_service_with_ledger(rows: list[tuple]) -> tuple[GalaxyStatsService, AsyncMock]:
    mock_db = AsyncMock()
    ledger_result = MagicMock()
    ledger_result.fetchall = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=ledger_result)
    return GalaxyStatsService(mock_db), mock_db


class TestSparkEvidenceIntegration:
    @pytest.mark.asyncio
    async def test_prior_belief_replays_ledger(self):
        now = _utcnow_naive()
        service, _ = _make_service_with_ledger(
            [("evidence:quiz", "obs=80;conf=0.9", now), ("task_complete", None, now)]
        )
        belief = await service._load_prior_belief(uuid4(), uuid4(), 40.0)
        assert belief.is_legacy_estimate is False
        assert belief.evidence_count == 1
        assert belief.mean > 40  # pulled toward the observed 80

    @pytest.mark.asyncio
    async def test_prior_belief_payload_less_quiz_rows_count_as_presence(self):
        now = _utcnow_naive()
        service, _ = _make_service_with_ledger([("error_diagnosis", None, now)])
        belief = await service._load_prior_belief(uuid4(), uuid4(), 40.0)
        assert belief.is_legacy_estimate is False  # quiz evidence exists
        assert belief.evidence_count == 0  # but nothing was re-fused

    @pytest.mark.asyncio
    async def test_spark_outcome_path_fuses_and_writes_evidence_row(self):
        node_id, user_id = uuid4(), uuid4()
        mock_node = MagicMock()
        mock_node.id = node_id
        mock_node.name = "N"
        mock_node.importance_level = 3
        mock_node.subject = None
        mock_status = MagicMock()
        mock_status.mastery_score = 0
        mock_status.is_unlocked = False
        mock_status.total_study_minutes = 0
        mock_status.study_count = 0

        service, mock_db = _make_service_with_ledger([])
        mock_db.get = AsyncMock(return_value=mock_node)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        with (
            patch("app.services.galaxy.stats_service.ExpansionService") as mock_expansion_cls,
            patch("app.services.galaxy.stats_service.cache_service") as mock_cache,
            patch("app.services.galaxy.stats_service.event_bus") as mock_bus,
            patch.object(GalaxyStatsService, "_get_or_create_status", new_callable=AsyncMock) as mock_status_factory,
            patch("app.services.galaxy.stats_service.achievement_engine", create=True),
        ):
            mock_expansion = AsyncMock()
            mock_expansion.queue_expansion = AsyncMock(return_value=False)
            mock_expansion_cls.return_value = mock_expansion
            mock_cache.delete_pattern = AsyncMock()
            mock_bus.publish = AsyncMock()
            mock_status_factory.return_value = mock_status

            # streaming service disabled
            with patch(
                "app.services.galaxy.streaming_service.get_galaxy_streaming_service",
                return_value=None,
            ):
                result = await service.spark_node(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=30,
                    trigger_expansion=False,
                    outcome=EvidenceObservation(MasteryEvidenceType.QUIZ, 85, 0.9),
                )

            assert result.updated_status.mastery_score > 70  # evidence-driven, not +5
            # evidence audit row written with encoded reason/payload
            executed_params = [call.args[1] for call in mock_db.execute.call_args_list if len(call.args) == 2]
            assert any(p.get("reason") == "evidence:quiz" for p in executed_params)
            assert any(str(p.get("request_id", "")).startswith("obs=85") for p in executed_params)

    @pytest.mark.asyncio
    async def test_spark_time_only_path_capped(self):
        node_id, user_id = uuid4(), uuid4()
        mock_node = MagicMock()
        mock_node.id = node_id
        mock_node.name = "N"
        mock_node.importance_level = 3
        mock_node.subject = None
        mock_status = MagicMock()
        mock_status.mastery_score = 39  # just below cap
        mock_status.is_unlocked = True
        mock_status.total_study_minutes = 0
        mock_status.study_count = 1

        service, _ = _make_service_with_ledger([])
        service.db.get = AsyncMock(return_value=mock_node)
        service.db.commit = AsyncMock()
        service.db.add = MagicMock()

        with (
            patch("app.services.galaxy.stats_service.ExpansionService") as mock_expansion_cls,
            patch("app.services.galaxy.stats_service.cache_service") as mock_cache,
            patch("app.services.galaxy.stats_service.event_bus") as mock_bus,
            patch.object(GalaxyStatsService, "_get_or_create_status", new_callable=AsyncMock) as mock_status_factory,
        ):
            mock_expansion = AsyncMock()
            mock_expansion.queue_expansion = AsyncMock(return_value=False)
            mock_expansion_cls.return_value = mock_expansion
            mock_cache.delete_pattern = AsyncMock()
            mock_bus.publish = AsyncMock()
            mock_status_factory.return_value = mock_status
            with patch(
                "app.services.galaxy.streaming_service.get_galaxy_streaming_service",
                return_value=None,
            ):
                result = await service.spark_node(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=120,
                    trigger_expansion=False,
                )

            # 39 + legacy delta (10) would be 49 under the old formula; capped at 40
            assert result.updated_status.mastery_score == pytest.approx(LEGACY_TIME_MASTERY_CAP)
            assert result.updated_status.mastery_evidence.is_legacy_estimate is True


class TestEvidenceInfoPayload:
    def test_mastery_evidence_info_flag_clears_with_fresh_outcome(self):
        prior = MasteryBelief(mean=30.0)
        info = _mastery_evidence_info(prior, EvidenceObservation(MasteryEvidenceType.QUIZ, 80, 0.9))
        assert isinstance(info, MasteryEvidenceInfo)
        assert info.is_legacy_estimate is False
        assert info.evidence_count == 1
        assert info.breakdown == {"quiz": 1}

    def test_mastery_evidence_info_stays_legacy_without_outcome(self):
        info = _mastery_evidence_info(MasteryBelief(mean=30.0), None)
        assert info.is_legacy_estimate is True

    def test_from_models_accepts_evidence_count(self):
        node = MagicMock()
        node.id = uuid4()
        node.name = "Test Node"
        node.name_en = None
        node.description = ""
        node.importance_level = 3
        node.subject_id = None
        node.parent_node_id = None
        node.position_x = 0
        node.position_y = 0
        node.position_angle = 0
        node.position_radius = 0
        node.is_seed = False
        node.deleted_at = None
        node.sector_weights = None
        node.keywords = None
        node.parent_id = None
        node.parent = MagicMock()
        node.parent.name = None
        status = MagicMock()
        status.mastery_score = 42
        status.total_study_minutes = 30
        status.study_count = 2
        status.is_unlocked = True
        status.is_collapsed = False
        status.is_favorite = False
        status.first_unlock_at = None
        status.last_study_at = None
        status.bkt_last_updated_at = None
        status.updated_at = None
        status.next_review_at = None
        status.decay_paused = False
        status.learning_path_snapshot = None

        legacy_view = NodeWithStatus.from_models(node, status, evidence_count=0)
        assert legacy_view.user_status.mastery_evidence.is_legacy_estimate is True

        evidenced_view = NodeWithStatus.from_models(node, status, evidence_count=3)
        assert evidenced_view.user_status.mastery_evidence.is_legacy_estimate is False
        assert evidenced_view.user_status.mastery_evidence.evidence_count == 3

        unknown_view = NodeWithStatus.from_models(node, status)
        assert unknown_view.user_status.mastery_evidence is None
