from app.core.user_insight_state import UserInsightState
from app.services.insight_prediction_service import InsightPredictionService


def test_insight_prediction_service_bounds_predictions_from_canonical_state() -> None:
    state = UserInsightState(
        goals=[{"id": "goal:1"}],
        recent_pain_points=[{"id": "pain:1"}],
        recent_wins=[{"id": "win:1"}],
        active_bottlenecks=[{"id": "b1"}, {"id": "b2"}, {"id": "b3"}, {"id": "b4"}],
        active_contradictions=[{"id": "c1"}],
        missing_information=["refresh:calendar_density"],
        inferred_work_style={
            "peak_focus_hours": [19, 20],
            "achievement_motivation_response": "progress_praise",
            "achievement_reward_sensitivity": "high",
            "preferred_tools": ["search_knowledge"],
            "accountability_support": "active",
        },
        stable_preferences={"content_depth_preference": "deep", "curiosity_preference": 0.7},
        current_state={
            "calendar_density_level": "high",
            "current_traction": "medium",
            "overload_pressure": "high",
            "task_drift_label": "high_drift",
        },
        temporal_patterns={"calendar": {"density_level": "high", "exam_urgency": {"days_left": 5}}},
        multi_span_analysis={
            "short_span": {"current_traction": "medium", "overload_pressure": "high", "focus_alignment": "supported"},
            "medium_span": {
                "deadline_pressure": "high",
                "task_start_completion_drift": {"label": "high_drift", "completion_ratio": 0.3},
            },
            "confidence_decay": {"stable_signals": ["peak_focus_hours", "achievement_motivation_response"], "stale_signals": []},
        },
    )

    predictions = InsightPredictionService().compile_predictions(state=state)

    assert predictions["overload_risk"]["level"] == "high"
    assert predictions["plan_slippage_risk"]["level"] == "high"
    assert predictions["planning_readiness"]["recommended_action"] in {"ask", "provisional"}
    assert predictions["schedule_fit"]["confidence"] <= 0.86
    assert predictions["likely_task_failure_modes"]["modes"]
