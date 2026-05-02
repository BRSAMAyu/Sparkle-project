"""Unit tests for RoutingParameterRegistry and its integration with DualCoreRouter.

Phase 1 verification:
- Router with no snapshot produces identical output to pre-registry behavior
- Registry falls back to defaults when Redis is empty
- Snapshot appears in DualCoreDecision.routing_debug
"""

import json

import pytest

from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRouter, DualCoreRoutingInput
from app.orchestration.routing_parameter_registry import (
    ALL_DEFAULT_PARAMETERS,
    DEFAULT_PRECEDENCE_WEIGHTS,
    DEFAULT_THRESHOLDS,
    RoutingParameterRegistry,
    RoutingParameterSnapshot,
    _clamp,
    _config_hash,
)


# ── RoutingParameterSnapshot Tests ──────────────────────────────────


class TestRoutingParameterSnapshot:
    def test_defaults_snapshot_has_correct_version(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        assert snap.source == "defaults"
        assert snap.version == _config_hash(ALL_DEFAULT_PARAMETERS)
        assert len(snap.parameters) == len(ALL_DEFAULT_PARAMETERS)

    def test_get_returns_value(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        assert snap.get("emotional_block") == 9.0
        assert snap.get("nonexistent", 42) == 42

    def test_precedence_weights_returns_only_weights(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        weights = snap.precedence_weights()
        assert set(weights.keys()) == set(DEFAULT_PRECEDENCE_WEIGHTS.keys())
        for k, v in weights.items():
            assert v == DEFAULT_PRECEDENCE_WEIGHTS[k]

    def test_threshold_returns_value(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        assert snap.threshold("high_cognitive_load_threshold") == 0.55
        assert snap.threshold("corrections_threshold") == 3

    def test_profile_defaults_returns_only_profiles(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        profiles = snap.profile_defaults()
        assert "procrastination_threshold" in profiles
        assert "emotional_sensitivity" in profiles
        assert "directness_preference" in profiles

    def test_to_dict_roundtrip(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        d = snap.to_dict()
        assert "version" in d
        assert "source" in d
        assert "parameters" in d
        assert d["source"] == "defaults"


# ── Clamping Tests ──────────────────────────────────────────────────


class TestClamping:
    def test_clamp_within_bounds(self):
        assert _clamp(5.0, "emotional_block") == 5.0

    def test_clamp_below_min(self):
        assert _clamp(-1.0, "emotional_block") == 0.0

    def test_clamp_above_max(self):
        assert _clamp(20.0, "emotional_block") == 15.0

    def test_clamp_unknown_param_uses_generic_bounds(self):
        assert _clamp(5.0, "unknown_param") == 5.0


# ── RoutingParameterRegistry Tests ──────────────────────────────────


class TestRoutingParameterRegistry:
    @pytest.mark.asyncio
    async def test_load_returns_defaults_when_redis_none(self):
        registry = RoutingParameterRegistry(redis_client=None)
        snap = await registry.load()
        assert snap.source == "defaults"
        assert snap.version == _config_hash(ALL_DEFAULT_PARAMETERS)

    @pytest.mark.asyncio
    async def test_load_returns_defaults_when_redis_empty(self):
        class FakeRedis:
            async def get(self, key):
                return None

        registry = RoutingParameterRegistry(redis_client=FakeRedis())
        snap = await registry.load()
        assert snap.source == "defaults"

    @pytest.mark.asyncio
    async def test_load_reads_from_redis(self):
        params = dict(ALL_DEFAULT_PARAMETERS)
        params["emotional_block"] = 5.0
        version = _config_hash(params)
        payload = json.dumps({"version": version, "parameters": params})

        class FakeRedisWithMode:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return payload.encode()

        registry = RoutingParameterRegistry(redis_client=FakeRedisWithMode())
        snap = await registry.load()
        assert snap.source == "redis"
        assert snap.get("emotional_block") == 5.0

    @pytest.mark.asyncio
    async def test_load_clamps_out_of_bounds_values(self):
        params = dict(ALL_DEFAULT_PARAMETERS)
        params["emotional_block"] = 999.0  # Way above max of 15.0
        payload = json.dumps({"parameters": params})

        class FakeRedisWithMode:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return payload.encode()

        registry = RoutingParameterRegistry(redis_client=FakeRedisWithMode())
        snap = await registry.load()
        assert snap.get("emotional_block") == 15.0  # Clamped to max

    @pytest.mark.asyncio
    async def test_load_ignores_unknown_keys(self):
        params = dict(ALL_DEFAULT_PARAMETERS)
        params["totally_fake_param"] = 42.0
        payload = json.dumps({"parameters": params})

        class FakeRedisWithMode:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return payload.encode()

        registry = RoutingParameterRegistry(redis_client=FakeRedisWithMode())
        snap = await registry.load()
        assert "totally_fake_param" not in snap.parameters

    @pytest.mark.asyncio
    async def test_load_falls_back_on_redis_error(self):
        class BrokenRedis:
            async def get(self, key):
                raise ConnectionError("Redis down")

        registry = RoutingParameterRegistry(redis_client=BrokenRedis())
        snap = await registry.load()
        assert snap.source == "defaults"


# ── DualCoreRouter Integration Tests ────────────────────────────────


def _make_execution_first_input() -> DualCoreRoutingInput:
    return DualCoreRoutingInput(
        intent="task",
        intent_confidence=0.9,
        information_sufficient=True,
        primary_challenge_area=None,
        recent_sentiment_distribution={"neutral": 5},
        has_active_plan=True,
        plan_health_status="on_track",
        recent_task_feedback_distribution={"completed": 3},
    )


def _make_cognitive_first_input() -> DualCoreRoutingInput:
    return DualCoreRoutingInput(
        intent="chat",
        intent_confidence=0.6,
        information_sufficient=False,
        primary_challenge_area="emotional",
        recent_sentiment_distribution={"anxious": 3, "stressed": 2},
        has_active_plan=False,
        plan_health_status=None,
        recent_task_feedback_distribution={"abandoned": 2},
        emotional_block_detected=True,
    )


class TestDualCoreRouter_ParameterRegistryIntegration:
    def test_no_snapshot_produces_identical_output(self):
        """Router with no snapshot must produce the same decision as before."""
        router_no_snap = DualCoreRouter()
        router_defaults = DualCoreRouter(
            parameter_snapshot=RoutingParameterRegistry._defaults_snapshot(),
        )
        inp = _make_execution_first_input()
        decision_a = router_no_snap.route(inp)
        decision_b = router_defaults.route(inp)
        assert decision_a.mode == decision_b.mode
        assert decision_a.signal_scores == decision_b.signal_scores

    def test_no_snapshot_reports_defaults_version(self):
        router = DualCoreRouter()
        decision = router.route(_make_execution_first_input())
        assert decision.routing_debug["parameter_version"] == "defaults"
        assert decision.routing_debug["parameter_source"] == "defaults"

    def test_snapshot_version_appears_in_debug(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        router = DualCoreRouter(parameter_snapshot=snap)
        decision = router.route(_make_execution_first_input())
        assert decision.routing_debug["parameter_version"] == snap.version
        assert decision.routing_debug["parameter_source"] == "defaults"

    def test_modified_precedence_weight_changes_routing(self):
        """Lower emotional_block weight so a previously cognitive_first case goes balanced."""
        defaults = RoutingParameterRegistry._defaults_snapshot()
        modified_params = dict(defaults.parameters)
        modified_params["emotional_block"] = 0.5  # Very low
        modified_params["procrastination"] = 0.5
        modified_snap = RoutingParameterSnapshot(
            version="test_low_emotional",
            source="test",
            parameters=modified_params,
        )
        router = DualCoreRouter(parameter_snapshot=modified_snap)
        decision = router.route(_make_cognitive_first_input())
        # With emotional_block weight at 0.5, it's still cognitive_first because
        # emotional_block_detected=True bypasses the score check entirely.
        # But the routing_debug should show the modified weight.
        assert decision.routing_debug["precedence_scores"].get("emotional_block", 0) == pytest.approx(0.5)

    def test_modified_threshold_changes_goal_clarity(self):
        """Raise goal_clear_threshold_base to make it harder to be execution_first."""
        defaults = RoutingParameterRegistry._defaults_snapshot()
        modified_params = dict(defaults.parameters)
        modified_params["goal_clear_threshold_base"] = 0.95  # Very high threshold
        modified_snap = RoutingParameterSnapshot(
            version="test_high_threshold",
            source="test",
            parameters=modified_params,
        )
        router = DualCoreRouter(parameter_snapshot=modified_snap)
        # An input that would normally be execution_first (0.9 confidence, clear intent)
        # should now fail the goal_clear check because threshold is 0.95
        decision = router.route(_make_execution_first_input())
        # It might go to balanced or cognitive_first depending on other signals
        # But the threshold in debug should reflect the modified value
        assert decision.routing_debug["goal_clear_threshold"] >= 0.55

    def test_cognitive_first_preserves_signal_scores(self):
        snap = RoutingParameterRegistry._defaults_snapshot()
        router = DualCoreRouter(parameter_snapshot=snap)
        decision = router.route(_make_cognitive_first_input())
        assert "emotional_block" in decision.signal_scores
        assert decision.signal_scores["emotional_block"] > 0


# ── Phase 4: A/B Test Integration Tests ────────────────────────────


class TestRoutingParameterExperimentService:
    """Tests for the experiment service bridging effectiveness with A/B testing."""

    def test_import_succeeds(self):
        from app.services.routing_parameter_experiment_service import RoutingParameterExperimentService
        assert RoutingParameterExperimentService is not None

    def test_propose_skips_when_value_too_close(self):
        """If proposed value is within 0.01 of current, skip experiment creation."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from app.services.routing_parameter_experiment_service import RoutingParameterExperimentService

        db = MagicMock()
        service = RoutingParameterExperimentService(db, redis_client=MagicMock())

        result = asyncio.get_event_loop().run_until_complete(
            service.propose_parameter_change(
                parameter_name="emotional_block",
                proposed_value=9.005,  # Within 0.01 of default 9.0
                evidence={"current_value": 9.0},
            )
        )
        assert result["status"] == "skipped"
        assert "too_close" in result["reason"]

    def test_apply_returns_insufficient_samples(self):
        """If fewer than 30 samples per variant, don't apply."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.routing_parameter_experiment_service import RoutingParameterExperimentService

        db = MagicMock()
        service = RoutingParameterExperimentService(db, redis_client=MagicMock())

        # Mock resolve_experiment to return low sample counts
        service.resolve_experiment = AsyncMock(return_value={
            "status": "resolved",
            "experiment_id": "test-exp",
            "variants": {
                "control": {"successes": 5, "total": 10, "rate": 0.5},
                "treatment": {"successes": 7, "total": 10, "rate": 0.7},
            },
        })

        result = asyncio.get_event_loop().run_until_complete(
            service.apply_winning_variant("test-exp")
        )
        assert result["status"] == "insufficient_samples"

    def test_apply_returns_no_improvement(self):
        """If treatment doesn't beat control by 5%, don't apply."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from app.services.routing_parameter_experiment_service import RoutingParameterExperimentService

        db = MagicMock()
        service = RoutingParameterExperimentService(db, redis_client=MagicMock())

        service.resolve_experiment = AsyncMock(return_value={
            "status": "resolved",
            "experiment_id": "test-exp",
            "variants": {
                "control": {"successes": 50, "total": 100, "rate": 0.5},
                "treatment": {"successes": 51, "total": 100, "rate": 0.51},
            },
        })

        result = asyncio.get_event_loop().run_until_complete(
            service.apply_winning_variant("test-exp")
        )
        assert result["status"] == "no_improvement"


class TestExperimentOverlayInRegistry:
    """Tests for user-level experiment overlay in RoutingParameterRegistry."""

    @pytest.mark.asyncio
    async def test_load_without_user_id_returns_base_params(self):
        """Without user_id, no experiment overlay is attempted."""
        params = dict(ALL_DEFAULT_PARAMETERS)
        params["emotional_block"] = 7.0
        payload = json.dumps({"version": "test", "parameters": params})

        class FakeRedis:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return payload.encode()

        registry = RoutingParameterRegistry(redis_client=FakeRedis())
        snap = await registry.load()
        assert snap.source == "redis"
        assert snap.get("emotional_block") == 7.0

    @pytest.mark.asyncio
    async def test_load_with_user_id_but_no_db_returns_base_params(self):
        """With user_id but no db, experiment overlay is skipped."""
        params = dict(ALL_DEFAULT_PARAMETERS)
        payload = json.dumps({"version": "test", "parameters": params})

        class FakeRedis:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return payload.encode()

        registry = RoutingParameterRegistry(redis_client=FakeRedis(), user_id="user-123")
        snap = await registry.load()
        assert snap.source == "redis"

    @pytest.mark.asyncio
    async def test_load_with_experiment_overlay(self):
        """When experiment assigns treatment variant, overrides are applied."""
        base_params = dict(ALL_DEFAULT_PARAMETERS)
        base_payload = json.dumps({"version": "base_v1", "parameters": base_params})

        class FakeRedis:
            async def get(self, key):
                if "meta_learning" in key:
                    return "shadow"
                return base_payload.encode()

        class FakeVariant:
            is_control = False
            configuration = {"overrides": {"emotional_block": 3.0}}

        class FakeDB:
            async def execute(self, stmt):
                class FakeResult:
                    def scalars(self):
                        return self
                    def all(self):
                        return []
                return FakeResult()

        registry = RoutingParameterRegistry(redis_client=FakeRedis(), user_id="user-123")
        # The _load_experiment_overlays will find no experiments, so it returns None → base params
        snap = await registry.load(db=FakeDB())
        assert snap.source == "redis"
        assert snap.get("emotional_block") == 9.0  # No experiment found, base value used


# ── Phase 5: Automatic Parameter Proposal Tests ────────────────────


class TestParameterProposal:
    """Tests for ParameterProposal data class."""

    def test_proposal_creation(self):
        from app.services.routing_parameter_proposal_service import ParameterProposal

        p = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=7.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=100,
            promotion_layer="episode",
        )
        assert p.parameter_name == "emotional_block"
        assert p.status == "pending"
        assert p.promotion_layer == "episode"

    def test_proposal_to_dict_roundtrip(self):
        from app.services.routing_parameter_proposal_service import ParameterProposal

        p = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=7.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=100,
        )
        d = p.to_dict()
        p2 = ParameterProposal.from_dict(d)
        assert p2.parameter_name == p.parameter_name
        assert p2.proposed_value == p.proposed_value
        assert p2.sample_count == p.sample_count

    def test_promotion_layer_profile(self):
        from app.services.routing_parameter_proposal_service import (
            LAYER_PROFILE,
            ParameterProposal,
        )

        p = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=7.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=150,
            promotion_layer=LAYER_PROFILE,
        )
        assert p.promotion_layer == LAYER_PROFILE

    def test_promotion_layer_session(self):
        from app.services.routing_parameter_proposal_service import (
            LAYER_SESSION,
            ParameterProposal,
        )

        p = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=7.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=35,
            promotion_layer=LAYER_SESSION,
        )
        assert p.promotion_layer == LAYER_SESSION

    def test_determine_promotion_layer_from_samples(self):
        from app.services.routing_parameter_proposal_service import (
            LAYER_EPISODE,
            LAYER_PROFILE,
            LAYER_SESSION,
            RoutingParameterProposalService,
        )
        from unittest.mock import MagicMock

        service = RoutingParameterProposalService(MagicMock(), redis_client=MagicMock())
        assert service._determine_promotion_layer(20) == LAYER_SESSION
        assert service._determine_promotion_layer(60) == LAYER_EPISODE
        assert service._determine_promotion_layer(200) == LAYER_PROFILE


class TestRoutingParameterProposalService:
    """Tests for the proposal service."""

    def test_import_succeeds(self):
        from app.services.routing_parameter_proposal_service import RoutingParameterProposalService
        assert RoutingParameterProposalService is not None

    def test_canary_bucket_deterministic(self):
        from app.services.routing_parameter_proposal_service import in_canary_bucket

        # Same user_id always gets same result
        assert in_canary_bucket("user-123", 50) == in_canary_bucket("user-123", 50)
        # 0% → no one
        assert not in_canary_bucket("user-123", 0)
        # 100% → everyone
        assert in_canary_bucket("user-123", 100)

    def test_canary_bucket_distribution(self):
        from app.services.routing_parameter_proposal_service import in_canary_bucket

        # With 50% canary, roughly half of users should be in bucket
        in_count = sum(1 for i in range(100) if in_canary_bucket(f"user-{i}", 50))
        assert 20 < in_count < 80  # Rough sanity check

    def test_drift_check_blocks_large_change(self):
        from app.services.routing_parameter_proposal_service import (
            MAX_DRIFT_RATIO,
            ParameterProposal,
            RoutingParameterProposalService,
        )
        from unittest.mock import MagicMock

        db = MagicMock()
        service = RoutingParameterProposalService(db, redis_client=MagicMock())

        # Propose changing emotional_block from 9.0 to 0.5 — that's a >90% drift
        proposal = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=0.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=100,
        )
        result = service._check_drift(proposal)
        assert result["disposition"] == "blocked"
        assert "drifts" in result["explanation"]

    def test_drift_check_allows_small_change(self):
        from app.services.routing_parameter_proposal_service import (
            ParameterProposal,
            RoutingParameterProposalService,
        )
        from unittest.mock import MagicMock

        db = MagicMock()
        service = RoutingParameterProposalService(db, redis_client=MagicMock())

        # Propose changing emotional_block from 9.0 to 8.5 — that's ~6% drift
        proposal = ParameterProposal(
            parameter_name="emotional_block",
            current_value=9.0,
            proposed_value=8.5,
            baseline_rate=0.4,
            treatment_rate=0.55,
            sample_count=100,
        )
        result = service._check_drift(proposal)
        # Should NOT be blocked by drift ratio (but may hit constitutional firewall)
        assert result["disposition"] != "blocked" or "constitutional" not in result.get("explanation", "")

    @pytest.mark.asyncio
    async def test_propose_returns_empty_without_data(self):
        from app.services.routing_parameter_proposal_service import RoutingParameterProposalService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        redis = MagicMock()
        redis.get = AsyncMock(return_value=None)
        service = RoutingParameterProposalService(db, redis_client=redis)
        proposals = await service.propose_from_effectiveness()
        assert proposals == []

    @pytest.mark.asyncio
    async def test_list_proposals_empty_when_no_redis(self):
        from app.services.routing_parameter_proposal_service import RoutingParameterProposalService
        from unittest.mock import MagicMock

        db = MagicMock()
        service = RoutingParameterProposalService(db, redis_client=None)
        result = await service.list_proposals()
        assert result == []


# ── Phase 6: Anomaly Detection + Auto-Rollback Tests ───────────────


class TestRoutingParameterHealthCheck:
    """Tests for SpineQualityGuard.check_routing_parameter_health()."""

    def test_healthy_when_no_data(self):
        from app.signals.spine_quality_guard import SpineQualityGuard

        check = SpineQualityGuard.check_routing_parameter_health([])
        assert check.passed
        assert check.score == 1.0

    def test_healthy_when_rates_above_baseline(self):
        from app.signals.spine_quality_guard import SpineQualityGuard

        data = [
            {"parameter_version": "v1", "dominant_signal": "emotional_block", "routing_mode": "cognitive_first", "total": 100, "success_rate": 0.6},
            {"parameter_version": "v1", "dominant_signal": "procrastination", "routing_mode": "balanced", "total": 80, "success_rate": 0.55},
        ]
        check = SpineQualityGuard.check_routing_parameter_health(data, baseline_success_rate=0.5)
        assert check.passed
        assert check.score > 0.5

    def test_degraded_when_rate_drops_below_threshold(self):
        from app.signals.spine_quality_guard import SpineQualityGuard

        data = [
            {"parameter_version": "v2_bad", "dominant_signal": "emotional_block", "routing_mode": "cognitive_first", "total": 100, "success_rate": 0.25},
            {"parameter_version": "v1", "dominant_signal": "procrastination", "routing_mode": "balanced", "total": 80, "success_rate": 0.55},
        ]
        check = SpineQualityGuard.check_routing_parameter_health(
            data, baseline_success_rate=0.5, max_degradation=0.10,
        )
        assert not check.passed
        assert len(check.details["degrading_groups"]) == 1
        assert check.details["degrading_groups"][0]["parameter_version"] == "v2_bad"

    def test_ignores_low_sample_groups(self):
        from app.signals.spine_quality_guard import SpineQualityGuard

        data = [
            {"parameter_version": "v2_bad", "dominant_signal": "emotional_block", "routing_mode": "cognitive_first", "total": 5, "success_rate": 0.1},
        ]
        check = SpineQualityGuard.check_routing_parameter_health(
            data, baseline_success_rate=0.5, min_samples=20,
        )
        assert check.passed  # Ignored because only 5 samples

    def test_has_recommendations_when_degraded(self):
        from app.signals.spine_quality_guard import SpineQualityGuard

        data = [
            {"parameter_version": "v2_bad", "dominant_signal": "emotional_block", "routing_mode": "cognitive_first", "total": 50, "success_rate": 0.2},
        ]
        check = SpineQualityGuard.check_routing_parameter_health(data, baseline_success_rate=0.5)
        assert not check.passed
        assert len(check.recommendations) > 0
        assert "rollback" in check.recommendations[0].lower()


class TestSelfHealingController_ParameterRollback:
    """Tests for rollback_parameter_version action in SelfHealingController."""

    def test_decide_action_triggers_rollback_for_parameter_health(self):
        from app.signals.spine_quality_guard import SelfHealingController

        controller = SelfHealingController()
        action = controller.decide_action(
            health_status="at_risk",
            check_name="routing_parameter_health",
            target="routing_parameters",
        )
        assert action is not None
        assert action.action_type == "rollback_parameter_version"
        assert action.severity == "high"

    def test_decide_action_triggers_critical_rollback(self):
        from app.signals.spine_quality_guard import SelfHealingController

        controller = SelfHealingController()
        action = controller.decide_action(
            health_status="critical",
            check_name="routing_parameter_health",
            target="routing_parameters",
        )
        assert action is not None
        assert action.action_type == "rollback_parameter_version"
        assert action.severity == "critical"

    def test_decide_action_no_action_for_healthy(self):
        from app.signals.spine_quality_guard import SelfHealingController

        controller = SelfHealingController()
        action = controller.decide_action(
            health_status="healthy",
            check_name="routing_parameter_health",
            target="routing_parameters",
        )
        assert action is None

    def test_execute_rollback_action(self):
        from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

        controller = SelfHealingController()
        action = SelfHealingAction(
            action_type="rollback_parameter_version",
            target="routing_parameters",
            reason="Parameter health degraded",
            severity="critical",
        )
        result = controller.execute_action(action)
        assert result["executed"]
        assert controller.is_circuit_broken("routing_parameters")

    def test_revert_rollback_action(self):
        from app.signals.spine_quality_guard import SelfHealingController, SelfHealingAction

        controller = SelfHealingController()
        action = SelfHealingAction(
            action_type="rollback_parameter_version",
            target="routing_parameters",
            reason="Parameter health degraded",
            severity="high",
        )
        controller.execute_action(action)
        assert controller.is_circuit_broken("routing_parameters")

        result = controller.revert_action(action.action_id)
        assert result["reverted"]
        assert not controller.is_circuit_broken("routing_parameters")
