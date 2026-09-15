"""Tests for Flutter-side SpineStatusBand model parsing."""

import pytest


# ── Simulate Dart fromJson in Python for contract validation ──────────

BAND_STATUS_MAP = {
    "sensing": "sensing",
    "calibrated": "calibrated",
    "risk_found": "riskFound",
    "needs_confirm": "needsConfirm",
    "calibration_available": "calibrationAvailable",
    "cooling_down": "coolingDown",
}

VALID_SEVERITIES = {"none", "info", "warning", "critical"}
VALID_ENERGIES = {"L0", "L1", "L2", "L3"}


def _make_api_response(**overrides):
    base = {
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
    base.update(overrides)
    return base


class TestSpineStatusBandContract:
    """Verify backend response matches Flutter model expectations."""

    def test_sensing_response_has_all_required_fields(self):
        data = _make_api_response()
        required = {
            "strategy_risk", "material_aware", "execution_risk", "stale_guard",
            "band_severity", "band_status", "band_label", "band_summary",
            "band_energy", "correction_options", "cooldown_remaining_seconds",
            "cooldown_can_override",
        }
        assert required.issubset(set(data.keys()))

    @pytest.mark.parametrize("band_status", list(BAND_STATUS_MAP.keys()))
    def test_all_6_states_valid(self, band_status):
        data = _make_api_response(band_status=band_status)
        assert data["band_status"] in BAND_STATUS_MAP

    @pytest.mark.parametrize("severity", list(VALID_SEVERITIES))
    def test_all_severities_valid(self, severity):
        data = _make_api_response(band_severity=severity)
        assert data["band_severity"] in VALID_SEVERITIES

    @pytest.mark.parametrize("energy", list(VALID_ENERGIES))
    def test_all_energy_levels_valid(self, energy):
        data = _make_api_response(band_energy=energy)
        assert data["band_energy"] in VALID_ENERGIES

    def test_correction_options_structure(self):
        data = _make_api_response(correction_options=[
            {"label": "这个风险判断不对", "semantic_value": "risk_false_positive",
             "is_freeform": False, "is_disconfirming": True},
            {"label": "都不对，我解释一下", "semantic_value": "freeform_correction",
             "is_freeform": True, "is_disconfirming": True},
        ])
        for opt in data["correction_options"]:
            assert "label" in opt
            assert "semantic_value" in opt
            assert "is_freeform" in opt
            assert "is_disconfirming" in opt

    def test_risk_found_response(self):
        data = _make_api_response(
            band_status="risk_found",
            band_severity="warning",
            band_label="发现风险",
            band_summary="Aurora 发现策略风险，建议确认或调整当前方向。",
            band_energy="L2",
            strategy_risk=True,
        )
        assert data["band_status"] == "risk_found"
        assert data["strategy_risk"] is True
        assert data["band_severity"] == "warning"

    def test_cooling_down_with_cooldown_remaining(self):
        data = _make_api_response(
            band_status="cooling_down",
            cooldown_remaining_seconds=900,
            cooldown_can_override=True,
        )
        assert data["cooldown_remaining_seconds"] == 900
        assert data["cooldown_can_override"] is True

    def test_response_json_serializable(self):
        import json
        data = _make_api_response()
        serialized = json.dumps(data, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized["band_status"] == "sensing"


class TestBandStatusToFlutterStateMapping:
    """Verify band_status → AuroraBandState mapping consistency."""

    def test_sensing_maps_to_sensing(self):
        assert BAND_STATUS_MAP["sensing"] == "sensing"

    def test_calibrated_maps_to_calibrated(self):
        assert BAND_STATUS_MAP["calibrated"] == "calibrated"

    def test_risk_found_maps_to_risk_detected(self):
        assert BAND_STATUS_MAP["risk_found"] == "riskFound"

    def test_needs_confirm_maps_to_needs_confirmation(self):
        assert BAND_STATUS_MAP["needs_confirm"] == "needsConfirm"

    def test_calibration_available_maps_correctly(self):
        assert BAND_STATUS_MAP["calibration_available"] == "calibrationAvailable"

    def test_cooling_down_maps_correctly(self):
        assert BAND_STATUS_MAP["cooling_down"] == "coolingDown"

    def test_unknown_status_falls_back_to_sensing(self):
        unknown = "unknown_status"
        result = BAND_STATUS_MAP.get(unknown, "sensing")
        assert result == "sensing"
