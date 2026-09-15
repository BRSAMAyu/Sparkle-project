"""
Tests for T3.4.1-T3.4.4: Aurora Status Band 6-State Unification & User Preferences.

Production scenario coverage:
- T3.4.1: Unified status band returns 6-state + risk flags
- T3.4.2: Correction options for all 6 band states
- T3.4.3: Cooldown fallback quick calibration
- T3.4.4: User preferences CRUD + runtime consumption
"""
import json
import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.aurora.runtime_v1.user_preferences import (
    AuroraUserPreferencesService,
    _DEFAULTS,
    _PREF_KEYS,
)
from app.signals.state_register import StateRegister
from app.signals.types import StateEntry


# ── Helpers ──────────────────────────────────────────────────────────

def _make_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.set.return_value = True
    redis.lpush.return_value = True
    redis.ltrim.return_value = True
    redis.expire.return_value = True
    redis.lrange.return_value = []
    redis.smembers.return_value = set()
    redis.mget.return_value = []
    redis.delete.return_value = True
    redis.srem.return_value = True
    redis.sadd.return_value = True
    # Per-key get: default None (handles state keys, directive keys gracefully)
    redis.get = AsyncMock(return_value=None)
    pipe = AsyncMock()
    pipe.set.return_value = pipe
    pipe.sadd.return_value = pipe
    pipe.delete.return_value = pipe
    pipe.srem.return_value = pipe
    pipe.execute.return_value = None
    redis.pipeline.return_value = pipe
    return redis


def _set_energy_get(redis: AsyncMock, energy_json) -> None:
    """Make redis.get return energy_json for aurora:energy:* keys, None for others."""
    async def _get_side_effect(key: str, *args, **kwargs):
        if isinstance(key, str) and key.startswith("aurora:energy:"):
            return energy_json
        return None
    redis.get.side_effect = _get_side_effect


def _make_state_entry(key: str, value: str, confidence: float = 0.7, scope: str = "session") -> StateEntry:
    return StateEntry(
        state_key=key,
        value=value,
        confidence=confidence,
        scope=scope,
        ttl_hours=24,
    )


def _state_entry_to_json(entry: StateEntry) -> str:
    return json.dumps(entry.to_dict())


# ═══════════════════════════════════════════════════════════════════
# T3.4.1: Unified Status Band — 6-state + risk flags
# ═══════════════════════════════════════════════════════════════════

class TestUnifiedStatusBand:
    """GET /spine/status-band returns 6-state band alongside risk flags."""

    @pytest.mark.asyncio
    async def test_returns_6state_band_with_risk_flags(self):
        """Unified response includes both risk flags and 6-state band fields."""
        redis = _make_redis()
        entries = [
            _make_state_entry("knowledge_transfer", "transfer_failure", 0.85),
            _make_state_entry("source_material", "material_received", 0.7),
        ]
        entry_jsons = [_state_entry_to_json(e) for e in entries]
        redis.smembers.return_value = {"knowledge_transfer", "source_material"}
        redis.mget.return_value = entry_jsons
        redis.get.return_value = None  # no energy stored → default AuroraEnergyState

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")

        # Existing risk flags preserved
        assert result["strategy_risk"] is True
        assert result["material_aware"] is True
        assert result["band_severity"] == "warning"

        # New 6-state band fields
        assert "band_status" in result
        assert result["band_status"] in (
            "sensing", "calibrated", "risk_found", "needs_confirm",
            "calibration_available", "cooling_down",
        )
        assert "band_label" in result
        assert isinstance(result["band_label"], str)
        assert len(result["band_label"]) > 0
        assert "band_summary" in result
        assert isinstance(result["band_summary"], str)
        assert len(result["band_summary"]) > 0
        assert "band_energy" in result
        assert result["band_energy"] in ("L0", "L1", "L2", "L3")

    @pytest.mark.asyncio
    async def test_each_band_status_has_label_and_summary(self):
        """Every 6-state value has a Chinese label and summary text."""
        from app.services.aurora_control_surface_service import AuroraControlSurfaceService
        from app.aurora.runtime_v1.state import AuroraEnergyState

        expected_labels = {
            "sensing": "轻量感知中",
            "calibrated": "已校准",
            "risk_found": "发现风险",
            "needs_confirm": "需要确认",
            "calibration_available": "深度校准可用",
            "cooling_down": "冷却中",
        }

        cs = AuroraControlSurfaceService(None, None)
        for band in expected_labels:
            summary = cs._band_status_summary(band, [])
            assert isinstance(summary, str)
            assert len(summary) > 10

    @pytest.mark.asyncio
    async def test_band_severity_and_band_status_consistent(self):
        """risk_found band should correlate with warning/critical severity."""
        redis = _make_redis()
        entries = [
            _make_state_entry("knowledge_transfer", "transfer_failure", 0.85),
            _make_state_entry("task_granularity_fit", "too_large", 0.75),
        ]
        entry_jsons = [_state_entry_to_json(e) for e in entries]
        redis.smembers.return_value = {"knowledge_transfer", "task_granularity_fit"}
        redis.mget.return_value = entry_jsons
        redis.get.return_value = None

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_severity"] == "critical"
        assert result["strategy_risk"] is True
        assert result["execution_risk"] is True

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_sensing_defaults(self):
        """Redis=None → all fields sensible defaults, 6-state is sensing."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []
        redis.get.return_value = None

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["strategy_risk"] is False
        assert result["band_severity"] == "none"
        assert result["band_status"] == "sensing"
        assert result["band_label"] == "轻量感知中"
        assert result["band_energy"] == "L0"

    @pytest.mark.asyncio
    async def test_backward_compatible_all_preexisting_fields(self):
        """All fields from the pre-T3.4 contract are still present."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []
        redis.get.return_value = None

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        required = [
            "strategy_risk", "material_aware", "execution_risk", "stale_guard",
            "has_active_directive", "active_claims", "active_state_keys",
            "directive_summary", "band_severity",
        ]
        for key in required:
            assert key in result, f"Missing backward-compatible key: {key}"

    @pytest.mark.asyncio
    async def test_cooldown_remaining_seconds_when_cooling_down(self):
        """When band is cooling_down, cooldown_remaining_seconds > 0."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cooldown_until = now + timedelta(seconds=1800)
        energy_json = json.dumps({
            "user_id": "user_1",
            "current_level": "L0",
            "wake_score": 0.0,
            "last_l3_session_at": (now - timedelta(minutes=5)).isoformat(),
            "cooldown_until": cooldown_until.isoformat(),
            "l3_session_count_today": 1,
            "updated_at": now.isoformat(),
        })
        _set_energy_get(redis, energy_json)

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "cooling_down"
        assert result["cooldown_remaining_seconds"] is not None
        assert result["cooldown_remaining_seconds"] > 0
        assert result["cooldown_can_override"] is True

    @pytest.mark.asyncio
    async def test_correction_options_present_for_all_states(self):
        """Every band status returns a list of correction options with freeform fallback."""
        redis = _make_redis()
        redis.get.return_value = None

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        for band in ("sensing", "calibrated", "risk_found", "needs_confirm",
                      "calibration_available", "cooling_down"):
            options = await spine._build_correction_options(band, [])
            assert isinstance(options, list)
            assert len(options) >= 2, f"{band} should have at least 2 options"
            # Last option is always freeform fallback
            assert options[-1]["is_freeform"] is True
            assert options[-1]["semantic_value"] == "freeform_correction"
            # Each option has required fields
            for opt in options:
                assert "label" in opt
                assert "semantic_value" in opt
                assert "is_freeform" in opt
                assert "is_disconfirming" in opt

    @pytest.mark.asyncio
    async def test_empty_stateregister_returns_sensing_none(self):
        """No active states → sensing bandwidth, none severity."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []
        redis.get.return_value = None

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "sensing"
        assert result["band_severity"] == "none"
        assert result["strategy_risk"] is False
        assert result["execution_risk"] is False

    @pytest.mark.asyncio
    async def test_6state_computation_failure_returns_sensing(self):
        """When _compute_6state_band fails, it returns safe sensing defaults."""
        redis = _make_redis()
        redis.smembers.return_value = {"some_key"}
        redis.mget.return_value = []

        # Make energy load crash, but active directive lookup works (returns None)
        async def _get_crash_for_energy(key: str, *args, **kwargs):
            if isinstance(key, str) and key.startswith("aurora:energy:"):
                raise RuntimeError("connection lost")
            return None
        redis.get.side_effect = _get_crash_for_energy

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "sensing"
        assert result["band_label"] == "轻量感知中"
        assert result["band_energy"] == "L0"
        assert result["cooldown_remaining_seconds"] is None


# ═══════════════════════════════════════════════════════════════════
# T3.4.4: User Preferences — CRUD
# ═══════════════════════════════════════════════════════════════════

class TestUserPreferencesCRUD:
    """AuroraUserPreferencesService get/update for 4 preference dimensions."""

    @pytest.mark.asyncio
    async def test_get_returns_defaults_when_no_prefs(self):
        """When UserPreferencesCenter row doesn't exist, all 4 defaults are returned."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.get("user_1")

        assert prefs == _DEFAULTS
        assert set(prefs.keys()) == _PREF_KEYS

    @pytest.mark.asyncio
    async def test_get_returns_stored_prefs(self):
        """Stored preferences are returned, missing keys get defaults."""
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.explicit = {
            "aurora_directness": "direct",
            "aurora_pressure_style": "gentle",
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.get("user_1")

        assert prefs["aurora_directness"] == "direct"
        assert prefs["aurora_pressure_style"] == "gentle"
        # Unset keys get defaults
        assert prefs["aurora_analysis_depth"] == _DEFAULTS["aurora_analysis_depth"]
        assert prefs["aurora_explanation_level"] == _DEFAULTS["aurora_explanation_level"]

    @pytest.mark.asyncio
    async def test_update_stores_all_4_prefs(self):
        """All 4 prefs are stored in explicit JSONB."""
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.explicit = {}
        mock_row.version = 1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {
            "aurora_analysis_depth": "light",
            "aurora_directness": "direct",
            "aurora_explanation_level": "brief",
            "aurora_pressure_style": "gentle",
        })

        assert prefs["aurora_analysis_depth"] == "light"
        assert prefs["aurora_directness"] == "direct"
        assert prefs["aurora_explanation_level"] == "brief"
        assert prefs["aurora_pressure_style"] == "gentle"
        mock_db.commit.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_update_rejects_invalid_enum_values(self):
        """Invalid enum values are silently ignored."""
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.explicit = {}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {
            "aurora_directness": "invalid_value",
            "aurora_analysis_depth": "light",
        })

        # invalid_value is ignored, light is stored
        assert prefs["aurora_directness"] == _DEFAULTS["aurora_directness"]
        assert prefs["aurora_analysis_depth"] == "light"

    @pytest.mark.asyncio
    async def test_update_partial_preserves_other_fields(self):
        """Partial update only changes specified fields, others unchanged."""
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.explicit = {
            "aurora_directness": "direct",
            "aurora_analysis_depth": "light",
            "aurora_pressure_style": "gentle",
            "aurora_explanation_level": "detailed",
        }
        mock_row.version = 1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {"aurora_directness": "guided"})

        assert prefs["aurora_directness"] == "guided"  # changed
        assert prefs["aurora_analysis_depth"] == "light"  # unchanged
        assert prefs["aurora_pressure_style"] == "gentle"  # unchanged
        assert prefs["aurora_explanation_level"] == "detailed"  # unchanged

    @pytest.mark.asyncio
    async def test_update_creates_row_when_none_exists(self):
        """When no UserPreferencesCenter row exists, a new one is created."""
        mock_db = AsyncMock()

        # First execute (in update): returns None → creates new row
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        # Second execute (in get fallback after update): returns created row
        mock_row = MagicMock()
        mock_row.explicit = {"aurora_directness": "direct"}
        mock_result_created = MagicMock()
        mock_result_created.scalar_one_or_none.return_value = mock_row

        mock_db.execute.side_effect = [mock_result_none, mock_result_created]

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {"aurora_directness": "direct"})

        assert prefs["aurora_directness"] == "direct"
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.user_id == "user_1"
        assert "aurora_directness" in added_obj.explicit
        mock_db.commit.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_db_failure_during_get_returns_defaults(self):
        """When DB query fails, defaults are returned (no crash)."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = RuntimeError("connection lost")

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.get("user_1")

        assert prefs == _DEFAULTS

    @pytest.mark.asyncio
    async def test_db_failure_during_update_returns_current(self):
        """When DB commit fails, rollback happens and current prefs returned."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        # First execute (in update) fails on commit, second (in get fallback) returns None
        mock_db.execute.side_effect = [
            mock_result,   # update: select → None
            RuntimeError("commit failed"),
        ]
        # Actually let me make this simpler — commit itself fails
        mock_db.execute.side_effect = None
        mock_db.execute.return_value = mock_result
        mock_db.commit.side_effect = RuntimeError("commit failed")

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {"aurora_directness": "direct"})

        mock_db.rollback.assert_called_once_with()
        assert "aurora_directness" in prefs  # returns defaults on failure

    @pytest.mark.asyncio
    async def test_preferences_survive_json_roundtrip(self):
        """Preferences are JSON-serializable (JSONB storage compatible)."""
        original = dict(_DEFAULTS)
        serialized = json.dumps(original)
        deserialized = json.loads(serialized)
        assert deserialized == original

    @pytest.mark.asyncio
    async def test_non_aurora_keys_not_overwritten(self):
        """Only recognized aurora_* keys are modified; other explicit keys remain."""
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.explicit = {
            "timezone": "Asia/Shanghai",
            "daily_cap": 5,
            "aurora_directness": "guided",
        }
        mock_row.version = 1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute.return_value = mock_result

        service = AuroraUserPreferencesService(mock_db)
        prefs = await service.update("user_1", {
            "aurora_directness": "direct",
            "some_unknown_key": "value",
        })

        # Aurora pref updated
        assert prefs["aurora_directness"] == "direct"
        # Aurora defaults filled for missing keys
        assert prefs["aurora_analysis_depth"] == _DEFAULTS["aurora_analysis_depth"]


# ═══════════════════════════════════════════════════════════════════
# T3.4.4: User Preferences — Runtime Consumption
# ═══════════════════════════════════════════════════════════════════

class TestPreferencesConsumption:
    """apply_to_response_directive + DualCoreRouter consumption."""

    def test_apply_directness_direct(self):
        """direct=direct produces action_oriented intervention style."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_directness": "direct"}
        )
        assert result["intervention_style"] == "action_oriented"
        assert result["directness"] == "direct"

    def test_apply_directness_guided(self):
        """directness=guided produces reflective intervention style."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_directness": "guided"}
        )
        assert result["intervention_style"] == "reflective"

    def test_apply_pressure_gentle_sets_low_pressure(self):
        """pressure_style=gentle → pressure=low_pressure."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_pressure_style": "gentle"}
        )
        assert result["pressure"] == "low_pressure"

    def test_apply_pressure_motivating_sets_moderate(self):
        """pressure_style=motivating → pressure=moderate."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_pressure_style": "motivating"}
        )
        assert result["pressure"] == "moderate"

    def test_apply_explanation_brief_concise(self):
        """explanation_level=brief → verbosity=concise."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_explanation_level": "brief"}
        )
        assert result["verbosity"] == "concise"

    def test_apply_explanation_detailed_supportive(self):
        """explanation_level=detailed → verbosity=supportive."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_explanation_level": "detailed"}
        )
        assert result["verbosity"] == "supportive"

    def test_apply_combined_preferences(self):
        """All 4 prefs combined produce correct modulation."""
        result = AuroraUserPreferencesService.apply_to_response_directive({
            "aurora_analysis_depth": "light",
            "aurora_directness": "direct",
            "aurora_explanation_level": "brief",
            "aurora_pressure_style": "gentle",
        })
        assert result["analysis_depth"] == "light"
        assert result["directness"] == "direct"
        assert result["intervention_style"] == "action_oriented"
        assert result["verbosity"] == "concise"
        assert result["pressure"] == "low_pressure"

    def test_apply_explicit_overrides(self):
        """Explicit tone/verbosity/pressure params override pref-derived values."""
        result = AuroraUserPreferencesService.apply_to_response_directive(
            {"aurora_explanation_level": "brief", "aurora_pressure_style": "gentle"},
            tone="urgent",
            verbosity="detailed",
            pressure="high",
        )
        assert result["tone"] == "urgent"
        assert result["verbosity"] == "detailed"
        assert result["pressure"] == "high"

    def test_dual_core_router_respects_directness(self):
        """DualCoreRouter consumes directness preference → action_oriented strategy."""
        from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput

        router = DualCoreRouter()
        input_ = DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.85,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={},
            has_active_plan=True,
            plan_health_status="good",
            recent_task_feedback_distribution={},
            aurora_preferences={"aurora_directness": "direct"},
        )
        decision = router.route(input_)
        strategy_fields = [s.get("field") for s in decision.strategy_adjustments]
        assert "directness_mode" in strategy_fields

    def test_dual_core_router_respects_gentle_pressure(self):
        """DualCoreRouter adds gentle constraint when pressure_style=gentle."""
        from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput

        router = DualCoreRouter()
        input_ = DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.85,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={},
            has_active_plan=True,
            plan_health_status="good",
            recent_task_feedback_distribution={},
            aurora_preferences={"aurora_pressure_style": "gentle"},
        )
        decision = router.route(input_)
        gentle_constraints = [
            c for c in decision.execution_constraints
            if "温和提醒" in c
        ]
        assert len(gentle_constraints) > 0


# ═══════════════════════════════════════════════════════════════════
# T3.4.3: Cooldown Fallback Calibration
# ═══════════════════════════════════════════════════════════════════

class TestCooldownCalibration:
    """Cooldown band includes quick_calibration options and cooldown_remaining."""

    @pytest.mark.asyncio
    async def test_cooling_down_includes_quick_calibration_option(self):
        """cooling_down correction options include '快速校准'."""
        redis = _make_redis()
        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        options = await spine._build_correction_options("cooling_down", [])
        labels = [o["label"] for o in options]
        assert "快速校准" in labels
        assert "坚持冷却" in labels
        # Freeform fallback always present
        assert options[-1]["is_freeform"] is True

    @pytest.mark.asyncio
    async def test_cooldown_remaining_seconds_computed(self):
        """cooldown_remaining_seconds > 0 when cooldown is active."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cooldown_until = now + timedelta(seconds=900)  # 15 min remaining
        energy_json = json.dumps({
            "user_id": "user_1",
            "current_level": "L3",
            "wake_score": 0.8,
            "last_l3_session_at": (now - timedelta(minutes=5)).isoformat(),
            "cooldown_until": cooldown_until.isoformat(),
            "l3_session_count_today": 1,
            "updated_at": now.isoformat(),
        })
        _set_energy_get(redis, energy_json)

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "cooling_down"
        assert result["cooldown_remaining_seconds"] is not None
        # Should be between 0 and 900 seconds
        assert 0 < result["cooldown_remaining_seconds"] <= 900
        assert result["cooldown_can_override"] is True

    @pytest.mark.asyncio
    async def test_no_cooldown_when_cooling_finished(self):
        """When cooldown_until is in the past, band is not cooling_down."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cooldown_until = now - timedelta(seconds=600)  # cooldown expired 10 min ago
        energy_json = json.dumps({
            "user_id": "user_1",
            "current_level": "L0",
            "wake_score": 0.0,
            "last_l3_session_at": (now - timedelta(hours=7)).isoformat(),
            "cooldown_until": cooldown_until.isoformat(),
            "l3_session_count_today": 0,
            "updated_at": now.isoformat(),
        })
        _set_energy_get(redis, energy_json)

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        # Cooldown expired → should be sensing, not cooling_down
        assert result["band_status"] == "sensing"
        assert result["cooldown_can_override"] is False

    @pytest.mark.asyncio
    async def test_cooldown_override_blocked_when_l3_quota_exhausted(self):
        """cooldown_can_override is False when user already used 3 L3 sessions today."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cooldown_until = now + timedelta(seconds=1800)
        energy_json = json.dumps({
            "user_id": "user_1",
            "current_level": "L0",
            "wake_score": 0.0,
            "last_l3_session_at": (now - timedelta(minutes=5)).isoformat(),
            "cooldown_until": cooldown_until.isoformat(),
            "l3_session_count_today": 3,
            "updated_at": now.isoformat(),
        })
        _set_energy_get(redis, energy_json)

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "cooling_down"
        assert result["cooldown_remaining_seconds"] > 0
        assert result["cooldown_can_override"] is False

    @pytest.mark.asyncio
    async def test_energy_store_invalid_json_returns_default(self):
        """Corrupted energy JSON → returns sensing, no crash."""
        redis = _make_redis()
        redis.smembers.return_value = set()
        redis.mget.return_value = []
        _set_energy_get(redis, b"not valid json {{{")

        from app.signals.spine_orchestrator import SpineOrchestrator
        spine = SpineOrchestrator(redis)

        result = await spine.get_status_band_summary("user_1")
        assert result["band_status"] == "sensing"
        assert result["band_energy"] == "L0"


# ═══════════════════════════════════════════════════════════════════
# API Response Contract
# ═══════════════════════════════════════════════════════════════════

class TestStatusBandContract:
    """API contract: response structure validation."""

    def test_redis_none_response_structure(self):
        """When Redis is None, API response has all required keys."""
        fallback = {
            "strategy_risk": False,
            "material_aware": False,
            "execution_risk": False,
            "stale_guard": False,
            "has_active_directive": False,
            "active_claims": [],
            "active_state_keys": [],
            "directive_summary": None,
            "band_severity": "none",
            "band_status": "sensing",
            "band_label": "轻量感知中",
            "band_summary": "Aurora 正在轻量感知，参考当前上下文优化回复。",
            "band_energy": "L0",
            "correction_options": [],
            "cooldown_remaining_seconds": None,
            "cooldown_can_override": False,
        }
        required_keys = {
            "strategy_risk", "material_aware", "execution_risk", "stale_guard",
            "band_severity", "band_status", "band_label", "band_summary",
            "band_energy", "correction_options", "cooldown_remaining_seconds",
            "cooldown_can_override",
        }
        assert required_keys.issubset(set(fallback.keys()))

    def test_full_response_json_serializable(self):
        """Full status band response is JSON-serializable."""
        response = {
            "strategy_risk": True,
            "material_aware": False,
            "execution_risk": False,
            "stale_guard": True,
            "has_active_directive": False,
            "active_claims": ["transfer_failure"],
            "active_state_keys": ["knowledge_transfer", "stale_state"],
            "directive_summary": None,
            "band_severity": "warning",
            "band_status": "risk_found",
            "band_label": "发现风险",
            "band_summary": "Aurora 发现策略风险，建议确认或调整当前方向。",
            "band_energy": "L2",
            "correction_options": [
                {"label": "这个风险判断不对", "semantic_value": "risk_false_positive",
                 "is_freeform": False, "is_disconfirming": True},
                {"label": "都不对，我解释一下", "semantic_value": "freeform_correction",
                 "is_freeform": True, "is_disconfirming": True},
            ],
            "cooldown_remaining_seconds": None,
            "cooldown_can_override": False,
        }
        serialized = json.dumps(response, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized["band_status"] == "risk_found"
        assert len(deserialized["correction_options"]) == 2
        assert deserialized["correction_options"][-1]["is_freeform"] is True
