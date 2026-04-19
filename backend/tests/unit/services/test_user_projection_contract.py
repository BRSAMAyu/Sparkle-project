from __future__ import annotations

from app.core.user_insight_state import InsightSignalEvidence, UserInsightState
from app.profile.projection_contract import UserProjectionContract


def _sample_state() -> UserInsightState:
    return UserInsightState(
        goals=[{"id": "goal:1", "type": "exam_window", "label": "期末冲刺"}],
        recent_pain_points=[{"id": "pain:1", "label": "错题压力偏高"}],
        recent_wins=[{"id": "win:1", "label": "热机效率提升"}],
        active_bottlenecks=[{"id": "b:1", "label": "熵增方向"}],
        readiness={"predicted_level": "medium"},
        multi_span_analysis={"short_span": {"overload_pressure": "medium"}},
        prediction_summaries={"planning_readiness": {"level": "medium"}},
        calibration_summary={"calibration_posture": "mixed"},
        confidence_metadata={"error_summary": 0.92},
        freshness_metadata={"error_summary": "high"},
        uncertainty_markers=[{"id": "uncertainty:capacity", "description": "Capacity unclear"}],
        signal_evidence=[
            InsightSignalEvidence(
                signal_id="error_summary",
                family="error",
                label="Errors",
                source="error_book",
                value={"total_errors": 6},
                confidence=0.92,
                freshness="high",
            ),
            InsightSignalEvidence(
                signal_id="achievement_motivation_response",
                family="achievement",
                label="Motivation response",
                source="prefs",
                value="progress_praise",
                confidence=0.8,
                freshness="medium",
            ),
        ],
    )


def test_user_projection_contract_captures_m1_source_inventory() -> None:
    contract = UserProjectionContract.from_compiled_state(state=_sample_state(), merged_preferences={})

    assert contract.m1_sources.module_name == "M1"
    assert contract.m1_sources.source_of_truth == "L0"
    assert contract.m1_sources.signal_count == 2
    assert {"achievement", "error"} == set(contract.m1_sources.source_families)


def test_user_projection_contract_captures_m2_canonical_state() -> None:
    state = _sample_state()
    contract = UserProjectionContract.from_compiled_state(state=state, merged_preferences={})

    assert contract.m2_canonical.module_name == "M2"
    assert contract.canonical_state.goals[0]["label"] == "期末冲刺"
    assert contract.m2_canonical.recent_pain_point_count == 1
    assert contract.m2_canonical.active_bottleneck_count == 1


def test_user_projection_contract_captures_m3_inference_surface() -> None:
    contract = UserProjectionContract.from_compiled_state(state=_sample_state(), merged_preferences={})

    assert contract.m3_inference.module_name == "M3"
    assert contract.m3_inference.multi_span_analysis["short_span"]["overload_pressure"] == "medium"
    assert contract.m3_inference.prediction_summaries["planning_readiness"]["level"] == "medium"
    assert contract.m3_inference.readiness["predicted_level"] == "medium"


def test_user_projection_contract_captures_m4_calibration_surface() -> None:
    contract = UserProjectionContract.from_compiled_state(state=_sample_state(), merged_preferences={})

    assert contract.m4_calibration.module_name == "M4"
    assert contract.m4_calibration.calibration_summary["calibration_posture"] == "mixed"
    assert contract.m4_calibration.confidence_metadata["error_summary"] == 0.92
    assert contract.m4_calibration.uncertainty_markers[0]["id"] == "uncertainty:capacity"


def test_user_projection_contract_captures_m5_transparency_surface() -> None:
    contract = UserProjectionContract.from_compiled_state(
        state=_sample_state(),
        merged_preferences={"insight_scope_overrides": {}},
    )

    assert contract.m5_transparency.module_name == "M5"
    assert contract.m5_transparency.transparency_payload["claims"][0]["id"] in {
        "achievement_motivation_response",
        "error_summary",
    }
    assert "wrong" in contract.m5_transparency.available_controls
