"""Spine tests — test_research_and_bridge.py."""

from __future__ import annotations
from tests.unit.spine._helpers import FakeRedis, FakeRedisWithHset


import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    AuroraAgenda,
    AuroraAgendaItem,
    AuroraControlSignal,
    CausalTrace,
    DirectiveApplicationAudit,
    ExecutionDirective,
    OutcomeRecord,
    PolicyDecision,
    StateEntry,
    UserVisibleReceipt,
    _uid,
)
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.policy_engine import PolicyEngine
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.spine_metrics import SpineMetricsCollector, METRIC_DEFINITIONS
from app.orchestration.prompts import build_system_prompt
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.causal_trace_store import CausalTraceStore
from app.signals.material_signal import MaterialSignalDetector
from app.signals.mistake_signal import MistakeSignalDetector
from app.signals.exam_rescue_detector import ExamRescueDetector, FirstMinuteSnapshot
from app.signals.stale_state_guard import StaleStateGuard, TimeContext, TimeDeltaPacket
from app.signals.state_packet_builder import ActionableStatePacketBuilder
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.self_model import SparkleSelfModelService, SelfModelClaim, StrategyOutcome
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.community_signal import CommunitySignalDetector
from app.signals.signal_ranker import SignalRanker
from app.signals.state_register import StateRegister
from app.signals.exam_sprint_policy import ExamSprintPolicyService
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.policy_analytics import PolicyAnalytics
from app.signals.policy_experiments import PolicyExperimentManager
from app.signals.learning_base import LearningBase
from app.signals.growth_chronicle import GrowthChronicleService, ChronicleEntry
from app.signals.relationship_model import RelationshipModelService
from app.signals.skill_extraction import SkillExtractionService
from app.signals.goal_type_adapter import GoalTypeAdapter
from app.signals.timeline_card_renderer import TimelineCardRenderer
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.goal_world_graph import GoalWorldGraphService
from app.signals.multi_goal_arbitration import MultiGoalArbitrator
from app.signals.directive_quota import DirectiveQuotaService
from app.signals.aurora_core_session import AuroraCoreSessionService, SessionClosure, StatePatch, PolicyChange
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.community_loops import CommunityLoopManager
from app.signals.recall_notification import RecallNotificationBuilder, RecallMessage

# ═══════════════════════════════════════════════════════════════════════


def test_p4_4_skill_card_creation():
    """SkillCard v2 holds evidence grade, effectiveness, prerequisites."""
    from app.signals.marketplace import SkillCard

    card = SkillCard(
        name="Exam Sprint Survival Mode",
        description="Activate emergency survival path for last-3-day exam prep",
        goal_type="exam",
        domain="exam_sprint",
        author_id="user_1",
        trigger_condition="deadline_days <= 3 AND baseline == near_zero",
        action_template="Build minimal pass path with top-3 most tested topics",
        expected_outcome="User passes exam focusing only on high-yield content",
        evidence_grade=3,
        evidence_summary="Effective in 85% of 40 zero-baseline episodes",
        episode_count=40,
        success_rate=0.85,
        status="active",
        prerequisites=[],
    )
    assert card.card_id.startswith("sk")
    assert card.evidence_grade == 3
    assert card.version == 1
    assert card.effectiveness_decay == 1.0

    d = card.to_dict()
    assert d["name"] == "Exam Sprint Survival Mode"
    assert d["evidence_grade"] == 3
    assert d["status"] == "active"

    restored = SkillCard.from_dict(d)
    assert restored.evidence_grade == 3


def test_p4_4_marketplace_iron_law_evidence_floor():
    """ML-1: Cards with evidence grade < 2 are blocked from listing."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Weak Skill", author_id="u1",
        evidence_grade=1, status="active",
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    blocking = [v for v in violations if v.severity == "blocking"]
    assert any(v.law_id == "ML-1" for v in blocking)

    check = MarketplaceIronLaws.is_listable(card)
    assert not check["listable"]


def test_p4_4_marketplace_iron_law_adoption_floor():
    """ML-2: Cards with < 5 adoptions get warning (not blocking)."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="New Skill", author_id="u1",
        evidence_grade=3, adoption_count=2, status="active",
    )
    check = MarketplaceIronLaws.is_listable(card)
    assert check["listable"]  # Warning, not blocking
    assert any(w["law_id"] == "ML-2" for w in check["warnings"])


def test_p4_4_marketplace_iron_law_deprecated_blocked():
    """ML-4: Deprecated/retired cards are blocked."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Old Skill", author_id="u1",
        evidence_grade=3, adoption_count=10, status="deprecated",
    )
    check = MarketplaceIronLaws.is_listable(card)
    assert not check["listable"]
    assert any(v["law_id"] == "ML-4" for v in check["blocking_violations"])


def test_p4_4_marketplace_iron_law_provenance():
    """ML-5: Cards without author_id are blocked."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Anonymous Skill",
        evidence_grade=3, adoption_count=10, status="active",
    )
    check = MarketplaceIronLaws.is_listable(card)
    assert not check["listable"]
    assert any(v["law_id"] == "ML-5" for v in check["blocking_violations"])


def test_p4_4_marketplace_iron_law_evidence_backed_claims():
    """ML-6: Unsubstantiated claim words blocked."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Revolutionary Method",
        description="A revolutionary approach to guaranteed success",
        author_id="u1",
        evidence_grade=2, adoption_count=10, status="active",
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    assert any(v.law_id == "ML-6" for v in violations)


def test_p4_4_marketplace_iron_law_rating_integrity():
    """ML-7: Rating without enough reviews gets warning."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Suspiciously Rated", author_id="u1",
        evidence_grade=3, adoption_count=10, status="active",
        rating=5.0, review_count=1,  # Only 1 review
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    assert any(v.law_id == "ML-7" for v in violations)


def test_p4_4_marketplace_iron_law_high_risk_domain():
    """ML-10: High-risk domains require safety review."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Mental Health Coach", author_id="u1",
        domain="mental_health",
        evidence_grade=3, adoption_count=10, status="active",
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    blocking = [v for v in violations if v.severity == "blocking"]
    assert any(v.law_id == "ML-10" for v in blocking)


def test_p4_4_marketplace_iron_law_prerequisites():
    """ML-8: Prerequisite skills must exist and be active."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    card = SkillCard(
        name="Advanced Skill", author_id="u1",
        evidence_grade=3, status="active",
        prerequisites=["sk_basic_1", "sk_missing"],
    )

    # Only basic_1 exists and is active
    basic = SkillCard(
        card_id="sk_basic_1", name="Basic", author_id="u1",
        evidence_grade=3, status="active",
    )
    active_cards = {"sk_basic_1": basic}

    violations = MarketplaceIronLaws.validate_prerequisites(card, active_cards)
    assert len(violations) == 1
    assert violations[0].asset_id == card.card_id
    assert "sk_missing" in violations[0].description


def test_p4_4_marketplace_iron_law_staleness():
    """ML-3: Cards not validated in 90+ days get warning."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws
    from datetime import datetime, timezone, timedelta

    stale_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    card = SkillCard(
        name="Stale Skill", author_id="u1",
        evidence_grade=3, adoption_count=10, status="active",
        last_validated_at=stale_date,
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    assert any(v.law_id == "ML-3" for v in violations)


def test_p4_4_domain_pack_review():
    """DomainPackReview holds user review with production usage flag."""
    from app.signals.marketplace import DomainPackReview

    review = DomainPackReview(
        asset_id="sk_test",
        user_id="u1",
        rating=4.0,
        title="Good but needs refinement",
        body="Worked well for my exam prep but needed adjustment for CS topics.",
        used_in_production=True,
        outcome_summary="Passed exam with 78%",
    )
    assert review.review_id.startswith("rev")
    assert review.rating == 4.0
    assert review.used_in_production

    d = review.to_dict()
    assert d["title"] == "Good but needs refinement"


def test_p4_4_registry_register_and_list():
    """MarketplaceRegistry registers cards and lists by filters."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()

    card1 = SkillCard(
        name="Exam Sprint", author_id="u1", goal_type="exam",
        domain="exam_sprint", evidence_grade=3, adoption_count=10,
        status="active", episode_count=50, success_rate=0.8,
    )
    card2 = SkillCard(
        name="Project Planner", author_id="u1", goal_type="project",
        domain="project_delivery", evidence_grade=2, adoption_count=5,
        status="active", episode_count=20, success_rate=0.6,
    )
    card3 = SkillCard(
        name="Draft Skill", author_id="u1", goal_type="exam",
        evidence_grade=3, adoption_count=10, status="draft",
    )

    r1 = registry.register_card(card1)
    assert r1["registered"]

    r2 = registry.register_card(card2)
    assert r2["registered"]

    registry.register_card(card3)

    # List active only
    active = registry.list_cards()
    assert len(active) == 2

    # Filter by goal_type
    exam = registry.list_cards(goal_type="exam")
    assert len(exam) == 1

    # Include drafts
    all_cards = registry.list_cards(include_drafts=True)
    assert len(all_cards) == 3

    # Filter by evidence grade
    high_grade = registry.list_cards(min_evidence_grade=3)
    assert len(high_grade) == 1


def test_p4_4_registry_recommendable():
    """list_recommendable ranks by iron law compliance, evidence, success, rating."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()

    best = SkillCard(
        name="Best Skill", author_id="u1", goal_type="exam",
        evidence_grade=4, adoption_count=20, status="active",
        success_rate=0.9, rating=4.5, review_count=10,
    )
    ok = SkillCard(
        name="OK Skill", author_id="u1", goal_type="exam",
        evidence_grade=3, adoption_count=6, status="active",
        success_rate=0.7, rating=3.5, review_count=5,
    )

    registry.register_card(best)
    registry.register_card(ok)

    results = registry.list_recommendable(goal_type="exam")
    assert len(results) == 2
    assert results[0]["recommendable"]
    assert results[0]["card"]["name"] == "Best Skill"


def test_p4_4_registry_reviews():
    """MarketplaceRegistry aggregates reviews and recalculates ratings."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard, DomainPackReview

    registry = MarketplaceRegistry()
    card = SkillCard(
        name="Reviewable Skill", author_id="u1",
        evidence_grade=3, adoption_count=10, status="active",
    )
    registry.register_card(card)

    r1 = registry.add_review(DomainPackReview(
        asset_id=card.card_id, user_id="u1", rating=4.0, title="Good",
        body="Works well", used_in_production=True,
    ))
    assert r1["added"]

    r2 = registry.add_review(DomainPackReview(
        asset_id=card.card_id, user_id="u2", rating=5.0, title="Great",
        body="Excellent", used_in_production=True,
    ))
    assert r2["added"]

    # Duplicate user blocked
    r3 = registry.add_review(DomainPackReview(
        asset_id=card.card_id, user_id="u1", rating=3.0, title="Again",
        body="Testing",
    ))
    assert not r3["added"]
    assert r3["reason"] == "duplicate_user"

    # Rating recalculated
    updated_card = registry.get_card(card.card_id)
    assert updated_card.review_count == 2
    assert updated_card.rating == 4.5  # (4+5)/2

    summary = registry.get_review_summary(card.card_id)
    assert summary["review_count"] == 2
    assert summary["production_review_count"] == 2
    assert not summary["rating_display_allowed"]  # 2 < 3 min


def test_p4_4_registry_adoption_tracking():
    """MarketplaceRegistry tracks adoptions and outcomes."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()
    card = SkillCard(
        name="Adopted Skill", author_id="u1",
        evidence_grade=3, status="active",
    )
    registry.register_card(card)

    rec1 = registry.record_adoption("u1", card.card_id, "skill_card")
    assert rec1.record_id.startswith("adopt")

    rec2 = registry.record_adoption("u2", card.card_id, "skill_card")
    rec3 = registry.record_adoption("u3", card.card_id, "skill_card")

    reg = registry.record_adoption_outcome(rec1.record_id, "success", "Great")
    assert reg["updated"]

    registry.record_adoption_outcome(rec2.record_id, "failure", "Not suitable")
    registry.record_adoption_outcome(rec3.record_id, "success", "Perfect")

    stats = registry.get_adoption_stats(card.card_id)
    assert stats["total_adoptions"] == 3
    assert stats["successful"] == 2
    assert stats["failed"] == 1
    assert stats["success_rate"] == pytest.approx(0.667, abs=0.01)

    updated_card = registry.get_card(card.card_id)
    assert updated_card.adoption_count == 3


def test_p4_4_registry_update_effectiveness():
    """update_effectiveness tracks decay, triggers review if success drops."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()
    card = SkillCard(
        name="Decaying Skill", author_id="u1",
        evidence_grade=3, adoption_count=10, status="active",
        success_rate=0.9, effectiveness_decay=1.0,
    )
    registry.register_card(card)

    # Mild drop — OK
    result = registry.update_effectiveness(card.card_id, 0.85)
    assert result["updated"]
    assert result["effectiveness_decay"] == 1.0  # No decay trigger

    # Severe drop (>20%) → decay triggered
    result = registry.update_effectiveness(card.card_id, 0.60)
    assert result["effectiveness_decay"] == 0.8  # -0.2
    assert result["status"] == "active"  # Still above 0.5

    # Repeated severe drops → under review
    result = registry.update_effectiveness(card.card_id, 0.40)
    assert result["effectiveness_decay"] == pytest.approx(0.6, abs=0.01)
    result = registry.update_effectiveness(card.card_id, 0.20)
    assert result["effectiveness_decay"] == pytest.approx(0.4, abs=0.01)
    assert result["status"] == "under_review"


def test_p4_4_registry_block_invalid_card():
    """MarketplaceRegistry rejects cards that fail iron laws."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()
    bad_card = SkillCard(
        name="Unproven", evidence_grade=1, status="active",
    )
    result = registry.register_card(bad_card)
    assert not result["registered"]
    assert "blocking_violations" in result


def test_p4_4_adoption_record():
    """AdoptionRecord captures user→asset adoption with context."""
    from app.signals.marketplace import AdoptionRecord

    rec = AdoptionRecord(
        user_id="u1", asset_id="sk_test", asset_type="skill_card",
        context_signature={"deadline_days": 5},
    )
    assert rec.record_id.startswith("adopt")
    assert rec.outcome == "pending"

    rec2 = AdoptionRecord(
        user_id="u2", asset_id="sk_test", asset_type="skill_card",
        outcome="success", outcome_detail="Achieved goal",
    )
    assert rec2.outcome == "success"


def test_p4_4_registry_empty_review_summary():
    """get_review_summary handles assets with no reviews."""
    from app.signals.marketplace import MarketplaceRegistry

    registry = MarketplaceRegistry()
    summary = registry.get_review_summary("nonexistent")
    assert summary["review_count"] == 0
    assert summary["rating"] is None


def test_p4_4_iron_law_all_nine_blocking_reasons():
    """Comprehensive: card with multiple violations aggregated correctly."""
    from app.signals.marketplace import SkillCard, MarketplaceIronLaws

    # A card violating as many laws as possible
    card = SkillCard(
        name="Terrible Card", description="guaranteed magic results",
        evidence_grade=0, adoption_count=0, status="deprecated",
        domain="medical", rating=5.0, review_count=1,
        # No author_id = provenance violation
    )
    violations = MarketplaceIronLaws.validate_listing(card)
    law_ids = {v.law_id for v in violations}
    # Should hit: ML-1 (evidence), ML-4 (deprecated), ML-5 (no author),
    # ML-6 (banned words), ML-10 (high-risk domain)
    assert "ML-1" in law_ids
    assert "ML-4" in law_ids
    assert "ML-5" in law_ids
    assert "ML-6" in law_ids
    assert "ML-10" in law_ids


def test_p4_4_registry_to_dict():
    """MarketplaceRegistry.to_dict provides aggregate stats."""
    from app.signals.marketplace import MarketplaceRegistry, SkillCard

    registry = MarketplaceRegistry()
    registry.register_card(SkillCard(
        name="Skill A", author_id="u1", evidence_grade=3,
        adoption_count=10, status="active",
    ))
    registry.register_card(SkillCard(
        name="Skill B", author_id="u2", evidence_grade=3,
        adoption_count=5, status="active",
    ))

    d = registry.to_dict()
    assert d["total_cards"] == 2
    assert d["active_cards"] == 2
    assert len(d["cards"]) == 2


# ═══════════════════════════════════════════════════════════════════════
# P4-5: Privacy-Preserving Community Intelligence v2
# ═══════════════════════════════════════════════════════════════════════


def test_p4_5_temporal_privacy_budget_creation():
    """TemporalPrivacyBudget enforces per-window query caps."""
    from app.signals.privacy_community_intelligence import TemporalPrivacyBudget

    budget = TemporalPrivacyBudget(user_id="u1")
    assert budget.can_query()["allowed"]
    assert budget.hourly_count == 0


def test_p4_5_temporal_privacy_budget_hourly_cap():
    """TemporalPrivacyBudget blocks queries after hourly cap exhausted."""
    from app.signals.privacy_community_intelligence import TemporalPrivacyBudget

    budget = TemporalPrivacyBudget(
        user_id="u1", max_hourly_queries=3,
        max_daily_queries=100, max_weekly_queries=500,
    )
    for _ in range(3):
        result = budget.record_query()
        assert result["recorded"]

    # 4th query blocked
    result = budget.record_query()
    assert not result["recorded"]
    assert budget.exhausted


def test_p4_5_temporal_privacy_budget_daily_cap():
    """TemporalPrivacyBudget blocks queries after daily cap."""
    from app.signals.privacy_community_intelligence import TemporalPrivacyBudget

    budget = TemporalPrivacyBudget(
        user_id="u1", max_hourly_queries=100,
        max_daily_queries=2, max_weekly_queries=500,
    )
    budget.record_query()
    budget.record_query()
    assert not budget.record_query()["recorded"]
    assert budget.exhausted


def test_p4_5_temporal_privacy_budget_renew():
    """TemporalPrivacyBudget can be renewed at window boundary."""
    from app.signals.privacy_community_intelligence import TemporalPrivacyBudget

    budget = TemporalPrivacyBudget(
        user_id="u1", max_hourly_queries=1,
        max_daily_queries=100, max_weekly_queries=500,
    )
    budget.record_query()
    assert budget.exhausted

    renewed = budget.try_renew(current_window_start="2026-04-28T00:00:00")
    assert renewed
    assert not budget.exhausted
    assert budget.hourly_count == 0


def test_p4_5_cohort_drift_detection_growing():
    """CohortDriftDetector detects growing cohort."""
    from app.signals.privacy_community_intelligence import CohortDriftDetector

    report = CohortDriftDetector.compute_drift(initial_size=10, current_size=25)
    assert report.drift_detected
    assert report.direction == "growing"
    assert report.requires_requery


def test_p4_5_cohort_drift_detection_shrinking():
    """CohortDriftDetector detects shrinking cohort."""
    from app.signals.privacy_community_intelligence import CohortDriftDetector

    report = CohortDriftDetector.compute_drift(initial_size=100, current_size=60)
    assert report.drift_detected
    assert report.direction == "shrinking"


def test_p4_5_cohort_drift_detection_stable():
    """CohortDriftDetector treats small changes as stable."""
    from app.signals.privacy_community_intelligence import CohortDriftDetector

    report = CohortDriftDetector.compute_drift(initial_size=100, current_size=105)
    assert not report.drift_detected
    assert report.direction == "stable"
    assert not report.requires_requery


def test_p4_5_cohort_drift_criteria_shift():
    """Criteria changes trigger drift regardless of size change."""
    from app.signals.privacy_community_intelligence import CohortDriftDetector

    report = CohortDriftDetector.compute_drift(
        initial_size=100, current_size=100,
        initial_criteria={"goal_type": "exam"},
        current_criteria={"goal_type": "project"},
    )
    assert report.drift_detected
    assert report.direction == "shifting"


def test_p4_5_drift_should_refresh():
    """should_refresh returns refresh decision with priority."""
    from app.signals.privacy_community_intelligence import (
        CohortDriftDetector, CohortDriftReport,
    )

    shrinking = CohortDriftReport(
        cohort_id="c1", initial_member_count=100,
        current_member_count=70, drift_detected=True, direction="shrinking",
    )
    decision = CohortDriftDetector.should_refresh(shrinking)
    assert decision["refresh"]
    assert decision["priority"] == "high"

    stable = CohortDriftReport(
        cohort_id="c2", initial_member_count=100,
        current_member_count=95, drift_detected=False, direction="stable",
    )
    decision = CohortDriftDetector.should_refresh(stable)
    assert not decision["refresh"]


def test_p4_5_federated_insight_creation():
    """FederatedInsight carries audit trail data."""
    from app.signals.privacy_community_intelligence import FederatedInsight

    insight = FederatedInsight(
        insight_type="cross_cohort_trend",
        description="Exam sprint users who adopt survival mode show 40% better outcomes",
        contributing_cohort_ids=["coh_1", "coh_2"],
        confidence=0.7,
        privacy_cost=0.3,
    )
    assert insight.insight_id.startswith("fi")
    assert insight.requires_human_review
    assert insight.status == "candidate"

    d = insight.to_dict()
    assert d["insight_type"] == "cross_cohort_trend"
    assert d["confidence"] == 0.7


def test_p4_5_secure_aggregation_federated_average():
    """SecureAggregationEngine computes weighted average across cohorts."""
    from app.signals.privacy_community_intelligence import (
        SecureAggregationEngine, AnonymizedCohortStat,
    )

    stat1 = AnonymizedCohortStat(
        stat_id="s1", stat_name="completion_rate",
        cohort_size=50, value=0.75, noise_std=0.05, is_reliable=True,
        confidence_interval=(0.70, 0.80),
    )
    stat2 = AnonymizedCohortStat(
        stat_id="s2", stat_name="completion_rate",
        cohort_size=100, value=0.85, noise_std=0.03, is_reliable=True,
        confidence_interval=(0.82, 0.88),
    )
    stat3 = AnonymizedCohortStat(
        stat_id="s3", stat_name="completion_rate",
        cohort_size=3, value=0.90, noise_std=0.10, is_reliable=False,
        confidence_interval=(0.0, 0.0),
    )

    result = SecureAggregationEngine.federated_average([stat1, stat2, stat3])
    assert result["computed"]
    assert result["cohorts_contributing"] == 2  # stat3 excluded
    assert result["total_members"] == 150
    assert result["value"] > 0


def test_p4_5_secure_aggregation_insufficient_cohorts():
    """Federated average requires minimum reliable cohorts."""
    from app.signals.privacy_community_intelligence import (
        SecureAggregationEngine, AnonymizedCohortStat,
    )

    stat = AnonymizedCohortStat(
        stat_id="s1", stat_name="completion_rate",
        cohort_size=20, value=0.75, noise_std=0.05, is_reliable=True,
        confidence_interval=(0.70, 0.80),
    )
    result = SecureAggregationEngine.federated_average([stat], min_reliable_cohorts=2)
    assert not result["computed"]
    assert result["value"] is None


def test_p4_5_secure_aggregation_audit_trail():
    """Audit trail shows which cohorts contributed to an insight."""
    from app.signals.privacy_community_intelligence import (
        SecureAggregationEngine, FederatedInsight, PrivacyPreservingCohort,
    )

    cohorts = {
        "coh_1": PrivacyPreservingCohort(
            cohort_id="coh_1", cohort_criteria={"goal_type": "exam"},
            member_count=50,
        ),
        "coh_2": PrivacyPreservingCohort(
            cohort_id="coh_2", cohort_criteria={"goal_type": "project"},
            member_count=30,
        ),
    }

    insight = FederatedInsight(
        insight_type="cross_cohort_trend",
        description="Cross-domain strategy transfer detected",
        contributing_cohort_ids=["coh_1", "coh_2"],
        confidence=0.8, privacy_cost=0.5,
    )

    trail = SecureAggregationEngine.audit_trail(insight, cohorts)
    assert trail["cohorts_audited"] == 2
    assert trail["verifiable"]
    assert len(trail["entries"]) == 2


def test_p4_5_privacy_preserving_rank():
    """Privacy-preserving rank suppresses items below privacy floor."""
    from app.signals.privacy_community_intelligence import SecureAggregationEngine

    items = [
        {"name": "A", "value": 0.9, "cohort_size": 50},
        {"name": "B", "value": 0.8, "cohort_size": 3},   # Below floor
        {"name": "C", "value": 0.7, "cohort_size": 30},
        {"name": "D", "value": 0.95, "cohort_size": 2},  # Below floor
    ]
    ranked = SecureAggregationEngine.privacy_preserving_rank(items, score_key="value")
    # A and C get ranked
    visible = [r for r in ranked if r.get("rank_reason") != "below_privacy_floor"]
    suppressed = [r for r in ranked if r.get("rank_reason") == "below_privacy_floor"]
    assert len(visible) == 2
    assert len(suppressed) == 2
    assert visible[0]["name"] == "A"  # 0.9 > 0.7


def test_p4_5_anonymized_stat_small_cohort():
    """compute_anonymized_stat returns unreliable for small cohorts."""
    from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine

    engine = PrivacyPreservingCommunityEngine()
    stat = engine.compute_anonymized_stat("test_stat", [1.0, 2.0, 3.0])  # n=3 < 5
    assert not stat.is_reliable
    assert stat.cohort_size == 3


def test_p4_5_community_engine_cohort_tier_auto():
    """PrivacyPreservingCohort auto-determines privacy tier."""
    from app.signals.privacy_community_intelligence import (
        PrivacyPreservingCommunityEngine,
    )

    engine = PrivacyPreservingCommunityEngine()

    tiny = engine.create_cohort({"goal_type": "exam"}, member_count=3)
    assert tiny.privacy_tier == "suppressed"

    small = engine.create_cohort({"goal_type": "exam"}, member_count=10)
    assert small.privacy_tier == "trend_only"

    large = engine.create_cohort({"goal_type": "exam"}, member_count=50)
    assert large.privacy_tier == "anonymous_aggregate"


# ═══════════════════════════════════════════════════════════════════════
# P4-6: Autonomous Quality Guard v2
# ═══════════════════════════════════════════════════════════════════════


def test_p4_6_latency_guard_normal():
    """LatencyGuard passes when all latencies are within thresholds."""
    from app.signals.spine_quality_guard import LatencyGuard

    normal = [50.0, 60.0, 55.0, 70.0, 65.0, 80.0, 58.0, 62.0, 75.0, 68.0]
    check = LatencyGuard.check_latency("signal_detection", normal)
    assert check.passed
    assert check.score > 0.9


def test_p4_6_latency_guard_warning():
    """LatencyGuard warns when p95 exceeds warning threshold."""
    from app.signals.spine_quality_guard import LatencyGuard

    slow = [100.0, 200.0, 300.0, 400.0, 600.0, 800.0, 1000.0, 50.0, 60.0, 70.0]
    check = LatencyGuard.check_latency("signal_detection", slow)
    # p95 might be high enough to trigger warning or critical
    assert check.category == "latency"
    # Should have at least one violation
    details = check.details
    assert details["sample_count"] == 10
    assert isinstance(details["p50_ms"], float)
    assert isinstance(details["p95_ms"], float)


def test_p4_6_latency_guard_critical():
    """LatencyGuard marks critical when p95 is very high."""
    from app.signals.spine_quality_guard import LatencyGuard

    terrible = [5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0, 5000.0, 6000.0, 7000.0, 8000.0]
    check = LatencyGuard.check_latency("policy_evaluation", terrible)
    assert not check.passed
    assert check.score < 0.5


def test_p4_6_latency_guard_empty():
    """LatencyGuard handles empty latency list."""
    from app.signals.spine_quality_guard import LatencyGuard

    check = LatencyGuard.check_latency("signal_detection", [])
    assert check.passed
    assert check.score == 1.0


def test_p4_6_eventbus_health_check():
    """EventBusHealthCheck evaluates stream health."""
    from app.signals.spine_quality_guard import EventBusHealth, EventBusHealthCheck

    healthy = EventBusHealth(
        stream_name="spine_events", consumer_group="spine_consumers",
        pending_messages=10, lag_seconds=5.0,
        consumer_count=3, active_consumers=3, status="healthy",
    )
    check = EventBusHealthCheck.check_stream_health(healthy)
    assert check.passed

    dead = EventBusHealth(
        stream_name="spine_events", status="dead",
    )
    check = EventBusHealthCheck.check_stream_health(dead)
    assert not check.passed
    assert check.score == 0.0


def test_p4_6_eventbus_lag_detection():
    """EventBusHealthCheck detects severe lag."""
    from app.signals.spine_quality_guard import EventBusHealth, EventBusHealthCheck

    laggy = EventBusHealth(
        stream_name="spine_events", consumer_group="spine_consumers",
        pending_messages=2000, lag_seconds=400.0,
        consumer_count=3, active_consumers=2, status="degraded",
    )
    check = EventBusHealthCheck.check_stream_health(laggy)
    assert not check.passed
    assert check.score < 0.6


def test_p4_6_iron_law_compliance_monitor():
    """IronLawComplianceMonitor checks individual iron laws."""
    from app.signals.spine_quality_guard import IronLawComplianceMonitor

    # Clean
    check = IronLawComplianceMonitor.check_iron_law(
        "no_orphan_signal", violations_detected=0, total_checked=100,
    )
    assert check.passed
    assert check.score == 1.0

    # Violated
    check = IronLawComplianceMonitor.check_iron_law(
        "every_directive_audited", violations_detected=5, total_checked=100,
    )
    assert not check.passed
    assert check.score < 1.0


def test_p4_6_iron_law_empty_check():
    """Iron law check with zero total passes gracefully."""
    from app.signals.spine_quality_guard import IronLawComplianceMonitor

    check = IronLawComplianceMonitor.check_iron_law(
        "no_orphan_signal", violations_detected=0, total_checked=0,
    )
    assert check.passed
    assert check.score == 1.0


def test_p4_6_iron_law_comprehensive_check():
    """Comprehensive iron law check produces a QualityReport."""
    from app.signals.spine_quality_guard import IronLawComplianceMonitor

    violations = {
        "no_orphan_signal": {"violations": 0, "total": 100},
        "every_directive_audited": {"violations": 2, "total": 100},
    }
    report = IronLawComplianceMonitor.comprehensive_iron_law_check(violations)
    assert len(report.checks) == 2
    assert report.overall_score < 1.0  # One violation


def test_p4_6_self_healing_action_creation():
    """SelfHealingAction tracks corrective actions."""
    from app.signals.spine_quality_guard import SelfHealingAction

    action = SelfHealingAction(
        action_type="throttle", target="signal_detector",
        reason="High latency", severity="medium",
    )
    assert action.action_id.startswith("sha")
    assert action.reversible
    assert not action.executed

    d = action.to_dict()
    assert d["action_type"] == "throttle"


def test_p4_6_self_healing_controller_decide():
    """SelfHealingController escalates: alert→throttle→degrade→circuit_break."""
    from app.signals.spine_quality_guard import SelfHealingController

    controller = SelfHealingController()

    # Degraded → alert
    action = controller.decide_action(
        health_status="degraded", check_name="latency", target="signal_detector",
    )
    assert action is not None
    assert action.action_type == "alert"

    # At risk → throttle
    action = controller.decide_action(
        health_status="at_risk", check_name="chain_breaks", target="policy_engine",
    )
    assert action.action_type == "throttle"

    # Critical → circuit break
    action = controller.decide_action(
        health_status="critical", check_name="eventbus", target="event_bus",
    )
    assert action.action_type == "circuit_break"


def test_p4_6_self_healing_controller_execute():
    """SelfHealingController executes and tracks actions."""
    from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

    controller = SelfHealingController()
    action = SelfHealingAction(
        action_type="circuit_break", target="spine_pipeline",
        reason="critical failure", severity="critical",
    )
    result = controller.execute_action(action)
    assert result["executed"]
    assert controller.is_circuit_broken("spine_pipeline")


def test_p4_6_self_healing_controller_throttle():
    """Throttle action reduces throughput level."""
    from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

    controller = SelfHealingController()
    assert controller.get_throttle_level("signal_detector") == 1.0

    action = SelfHealingAction(
        action_type="throttle", target="signal_detector",
        reason="high load", severity="medium",
    )
    controller.execute_action(action)
    assert controller.get_throttle_level("signal_detector") < 0.8


def test_p4_6_self_healing_controller_revert():
    """SelfHealingController can revert reversible actions."""
    from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

    controller = SelfHealingController()
    action = SelfHealingAction(
        action_type="circuit_break", target="spine_pipeline",
        reason="test", severity="critical",
    )
    controller.execute_action(action)
    assert controller.is_circuit_broken("spine_pipeline")

    result = controller.revert_action(action.action_id)
    assert result["reverted"]
    assert not controller.is_circuit_broken("spine_pipeline")


def test_p4_6_promotion_gate_all_pass():
    """PromotionGate allows promotion when all checks pass."""
    from app.signals.spine_quality_guard import PromotionGate

    result = PromotionGate.evaluate(
        benchmark_result={"pass_rate": 1.0},
        quality_health="healthy",
        iron_law_violations=0,
    )
    assert result["promotion_allowed"]
    assert result["recommendation"] == "safe_to_promote"


def test_p4_6_promotion_gate_blocks_on_benchmark():
    """PromotionGate blocks when benchmarks don't pass."""
    from app.signals.spine_quality_guard import PromotionGate

    result = PromotionGate.evaluate(
        benchmark_result={"pass_rate": 0.75},
        quality_health="healthy",
        iron_law_violations=0,
    )
    assert not result["promotion_allowed"]
    assert "benchmark_regression" in result["recommendation"]


def test_p4_6_promotion_gate_blocks_on_health():
    """PromotionGate blocks when quality health is critical."""
    from app.signals.spine_quality_guard import PromotionGate

    result = PromotionGate.evaluate(
        benchmark_result={"pass_rate": 1.0},
        quality_health="critical",
        iron_law_violations=0,
    )
    assert not result["promotion_allowed"]
    assert "quality_health" in result["recommendation"]


def test_p4_6_promotion_gate_blocks_on_iron_law():
    """PromotionGate blocks on iron law violations."""
    from app.signals.spine_quality_guard import PromotionGate

    result = PromotionGate.evaluate(
        benchmark_result={"pass_rate": 1.0},
        quality_health="healthy",
        iron_law_violations=3,
    )
    assert not result["promotion_allowed"]
    assert "iron_law_compliance" in result["recommendation"]


def test_p4_6_self_healing_controller_to_dict():
    """SelfHealingController.to_dict provides snapshot."""
    from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

    controller = SelfHealingController()
    action = SelfHealingAction(
        action_type="alert", target="test", reason="test", severity="low",
    )
    controller.execute_action(action)

    d = controller.to_dict()
    assert d["total_actions"] == 1
    assert len(d["recent_actions"]) == 1
    assert d["active_circuit_breaks"] == []


# ═══════════════════════════════════════════════════════════════════════
# P4-7: Research Mode — Continuous Improvement Loop
# ═══════════════════════════════════════════════════════════════════════


def test_p4_7_research_proposal_creation():
    """ResearchProposal captures a hypothesis-driven improvement proposal."""
    from app.signals.research_mode import ResearchProposal

    prop = ResearchProposal(
        title="Improve Deadline Detection",
        description="Current deadline detection misses implicit deadlines in messages",
        source="quality_guard",
        hypothesis="Adding implicit deadline NLP will improve crisis mode detection",
        target_metric="crisis_detection_rate",
        expected_effect_size=0.25,
        risk_level="low",
        domain="exam_sprint",
        proposed_policies=["implicit_deadline_nlp"],
    )
    assert prop.proposal_id.startswith("rp")
    assert prop.status == "draft"
    assert prop.evidence_grade == 0

    d = prop.to_dict()
    assert d["title"] == "Improve Deadline Detection"
    assert d["risk_level"] == "low"


def test_p4_7_research_conclusion_creation():
    """ResearchConclusion integrates all evidence for a final decision."""
    from app.signals.research_mode import ResearchConclusion

    conclusion = ResearchConclusion(
        proposal_id="rp_test",
        experiment_id="exp_test",
        title="Deadline Detection — Concluded",
        summary="NLP-based deadline detection improved crisis detection by 30%",
        evidence_grade=4,
        effect_size=0.30,
        confidence_interval=(0.15, 0.45),
        statistical_significance=True,
        practical_significance=True,
        action="promote",
        recommendations=["Deploy to production", "Monitor for regression"],
    )
    assert conclusion.conclusion_id.startswith("rc")
    assert conclusion.action == "promote"
    assert conclusion.statistical_significance

    d = conclusion.to_dict()
    assert d["evidence_grade"] == 4
    assert d["effect_size"] == 0.30


def test_p4_7_gap_detector_quality_critical():
    """GapDetector generates proposals from critical quality state."""
    from app.signals.research_mode import GapDetector

    proposals = GapDetector.from_quality_report(
        quality_health="critical",
        quality_score=0.35,
        systemic_issues=["orphan_signals", "chain_breaks"],
        domain="exam_sprint",
    )
    assert len(proposals) >= 1
    critical = proposals[0]
    assert critical.risk_level == "high"
    assert critical.source == "quality_guard"


def test_p4_7_gap_detector_quality_degraded():
    """GapDetector generates uplift proposals from degraded state."""
    from app.signals.research_mode import GapDetector

    proposals = GapDetector.from_quality_report(
        quality_health="degraded",
        quality_score=0.65,
        systemic_issues=["latency_warning"],
        domain="exam_sprint",
    )
    assert len(proposals) >= 1
    assert proposals[0].risk_level == "low"


def test_p4_7_gap_detector_quality_healthy():
    """GapDetector produces no proposals when healthy."""
    from app.signals.research_mode import GapDetector

    proposals = GapDetector.from_quality_report(
        quality_health="healthy",
        quality_score=0.95,
        systemic_issues=[],
    )
    assert len(proposals) == 0


def test_p4_7_gap_detector_counterfactual():
    """GapDetector generates proposals from counterfactual comparison."""
    from app.signals.research_mode import GapDetector

    comp = {
        "best_policy": "survival_mode_v2",
        "effect_size": 0.35,
        "evidence_grade": 4,
        "recommendation": "strong_evidence_for_change",
    }
    prop = GapDetector.from_counterfactual_gap(comp, domain="exam_sprint")
    assert prop is not None
    assert prop.source == "counterfactual"
    assert prop.evidence_grade == 4
    assert "survival_mode_v2" in prop.proposed_policies


def test_p4_7_gap_detector_counterfactual_no_change():
    """GapDetector returns None when counterfactual recommends no change."""
    from app.signals.research_mode import GapDetector

    comp = {"recommendation": "no_change"}
    prop = GapDetector.from_counterfactual_gap(comp)
    assert prop is None


def test_p4_7_gap_detector_benchmark_failure():
    """GapDetector generates proposals from failing scenarios."""
    from app.signals.research_mode import GapDetector

    benchmark = {
        "pass_rate": 0.85,
        "reports": [
            {"passed": False, "scenario_id": "scn_test", "violations": ["spine_integrity"]},
        ],
    }
    proposals = GapDetector.from_benchmark_failure(benchmark, domain="exam_sprint")
    assert len(proposals) == 1
    assert proposals[0].source == "simulation"
    assert "Fix Regression" in proposals[0].title


def test_p4_7_continuous_improvement_loop_ingest():
    """ContinuousImprovementLoop ingests gaps and generates proposals."""
    from app.signals.research_mode import ContinuousImprovementLoop

    loop = ContinuousImprovementLoop()
    proposals = loop.ingest_gaps(
        quality_health="degraded",
        quality_score=0.65,
        systemic_issues=["latency_warning"],
        domain="exam_sprint",
    )
    assert len(proposals) >= 1
    assert len(loop._proposals) >= 1


def test_p4_7_continuous_improvement_loop_prioritize():
    """prioritize_proposals ranks by evidence, effect, risk."""
    from app.signals.research_mode import (
        ContinuousImprovementLoop, ResearchProposal,
    )

    loop = ContinuousImprovementLoop()
    loop._proposals["rp_1"] = ResearchProposal(
        proposal_id="rp_1", title="High evidence, low risk",
        evidence_grade=4, expected_effect_size=0.5, risk_level="low",
        status="draft",
    )
    loop._proposals["rp_2"] = ResearchProposal(
        proposal_id="rp_2", title="Low evidence, high risk",
        evidence_grade=1, expected_effect_size=0.1, risk_level="high",
        status="draft",
    )

    ranked = loop.prioritize_proposals()
    assert len(ranked) == 2
    assert ranked[0]["proposal_id"] == "rp_1"
    assert ranked[0]["priority_score"] > ranked[1]["priority_score"]


def test_p4_7_continuous_improvement_loop_top_proposal():
    """get_top_proposal returns highest-priority ready proposal."""
    from app.signals.research_mode import (
        ContinuousImprovementLoop, ResearchProposal,
    )

    loop = ContinuousImprovementLoop()
    loop._proposals["rp_1"] = ResearchProposal(
        proposal_id="rp_1", title="Top", evidence_grade=4,
        expected_effect_size=0.5, risk_level="low", status="draft",
    )

    top = loop.get_top_proposal()
    assert top is not None
    assert top["proposal_id"] == "rp_1"
    assert "proposal" in top


def test_p4_7_continuous_improvement_loop_record_conclusion():
    """record_conclusion updates proposal status and logs."""
    from app.signals.research_mode import (
        ContinuousImprovementLoop, ResearchProposal, ResearchConclusion,
    )

    loop = ContinuousImprovementLoop()
    loop._proposals["rp_1"] = ResearchProposal(
        proposal_id="rp_1", title="Test", evidence_grade=3,
        status="approved",
    )

    conclusion = ResearchConclusion(
        proposal_id="rp_1", experiment_id="exp_1",
        title="Test Complete", summary="Works well",
        evidence_grade=4, effect_size=0.3, action="promote",
    )
    result = loop.record_conclusion(conclusion)
    assert result["recorded"]
    assert loop._proposals["rp_1"].status == "completed"


def test_p4_7_continuous_improvement_loop_measure_improvement():
    """measure_improvement tracks cumulative effect and trajectory."""
    from app.signals.research_mode import (
        ContinuousImprovementLoop, ResearchConclusion,
    )

    loop = ContinuousImprovementLoop()
    loop.record_conclusion(ResearchConclusion(
        proposal_id="rp_1", title="Improvement 1", effect_size=0.2,
        action="promote", concluded_at="2026-04-01T00:00:00",
    ))
    loop.record_conclusion(ResearchConclusion(
        proposal_id="rp_2", title="Improvement 2", effect_size=0.3,
        action="promote", concluded_at="2026-04-15T00:00:00",
    ))

    improvement = loop.measure_improvement()
    assert improvement["promoted_count"] == 2
    assert improvement["cumulative_effect"] == 0.5


def test_p4_7_research_dashboard():
    """ResearchDashboard aggregates all P4 metrics into one view."""
    from app.signals.research_mode import ResearchDashboard

    db = ResearchDashboard(
        active_experiments=3, completed_experiments=12,
        total_episodes_collected=5000, total_users_reached=200,
        quality_health="healthy", quality_score=0.92,
        marketplace_cards=15, marketplace_adoptions=85,
        active_cohorts=8, benchmark_pass_rate=0.96,
        proposals_active=5, proposals_completed=20,
    )
    assert db.dashboard_id.startswith("rdb")

    d = db.to_dict()
    assert d["active_experiments"] == 3
    assert d["quality_health"] == "healthy"
    assert d["benchmark_pass_rate"] == 0.96


def test_p4_7_continuous_improvement_loop_build_dashboard():
    """ContinuousImprovementLoop.build_dashboard integrates all P4 data."""
    from app.signals.research_mode import ContinuousImprovementLoop

    loop = ContinuousImprovementLoop()
    db = loop.build_dashboard(
        experiment_registry={
            "active_experiments": 2, "total_episodes": 1000, "total_users": 50,
        },
        marketplace_registry={
            "total_cards": 10, "total_adoptions": 60,
            "cards": [
                {"status": "active", "effectiveness_decay": 0.9},
                {"status": "active", "effectiveness_decay": 0.8},
            ],
        },
        quality_health="degraded", quality_score=0.7,
        iron_law_violations=2, benchmark_pass_rate=0.88,
        community_stats={
            "active_cohorts": 5, "total_members": 200, "federated_insights": 3,
        },
    )
    assert db.quality_health == "degraded"
    assert db.marketplace_cards == 10
    assert db.average_card_effectiveness == pytest.approx(0.85, abs=0.01)
    assert db.active_cohorts == 5
    assert db.benchmark_pass_rate == 0.88


def test_p4_7_continuous_improvement_loop_to_dict():
    """to_dict provides loop aggregate state."""
    from app.signals.research_mode import (
        ContinuousImprovementLoop, ResearchProposal, ResearchConclusion,
    )

    loop = ContinuousImprovementLoop()
    loop._proposals["rp_1"] = ResearchProposal(
        proposal_id="rp_1", title="Test", status="draft",
    )
    loop._conclusions["rc_1"] = ResearchConclusion(
        proposal_id="rp_1", title="Test", action="promote",
    )

    d = loop.to_dict()
    assert d["total_proposals"] == 1
    assert d["total_conclusions"] == 1
    assert "improvement_summary" in d


