from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.core.user_insight_state import InsightSignalEvidence, UserInsightState
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome
from app.models.memory import MemoryCorrection
from app.services.user_insight_calibration_service import UserInsightCalibrationService


@pytest.mark.asyncio
async def test_user_insight_calibration_service_demotes_corrected_signals_and_calibrates_predictions(
    db_session,
    test_user,
) -> None:
    db_session.add(
        MemoryCorrection(
            user_id=test_user.id,
            memory_type="insight_signal",
            memory_id=test_user.id,
            action="wrong",
            reason=json.dumps({"target_id": "peak_focus_hours", "reason": "Not true this term"}),
        )
    )
    db_session.add_all(
        [
            InterventionStrategyOutcome(
                user_id=test_user.id,
                intervention_id=uuid4(),
                trigger_type=InterventionTriggerType.OVERLOAD,
                delivery_tone=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.CHAT,
                acceptance_status=InterventionAcceptanceStatus.ACTED,
                outcome=InterventionOutcomeStatus.EFFECTIVE,
                context_snapshot={"goal_type": "exam"},
            ),
            InterventionStrategyOutcome(
                user_id=test_user.id,
                intervention_id=uuid4(),
                trigger_type=InterventionTriggerType.OVERLOAD,
                delivery_tone=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.CHAT,
                acceptance_status=InterventionAcceptanceStatus.ACTED,
                outcome=InterventionOutcomeStatus.EFFECTIVE,
                context_snapshot={"goal_type": "exam"},
            ),
            InterventionStrategyOutcome(
                user_id=test_user.id,
                intervention_id=uuid4(),
                trigger_type=InterventionTriggerType.OVERLOAD,
                delivery_tone=DeliveryStrategy.DIRECT,
                delivery_channel=DeliveryChannel.CHAT,
                acceptance_status=InterventionAcceptanceStatus.ACCEPTED,
                outcome=InterventionOutcomeStatus.INEFFECTIVE,
                context_snapshot={"goal_type": "exam"},
            ),
        ]
    )
    await db_session.commit()

    state = UserInsightState(
        stable_preferences={"content_depth_preference": "deep"},
        current_state={"calendar_density_level": "high"},
        inferred_work_style={
            "peak_focus_hours": [19, 20],
            "achievement_motivation_response": "progress_praise",
        },
        temporal_patterns={
            "calendar": {"peak_focus_hours": [19, 20], "density_level": "high"},
            "achievement": {"motivation_response": "progress_praise"},
        },
        signal_evidence=[
            InsightSignalEvidence(
                signal_id="peak_focus_hours",
                family="calendar",
                label="Peak focus hours",
                source="preferences",
                value=[19, 20],
                confidence=0.84,
                freshness="medium",
            ),
            InsightSignalEvidence(
                signal_id="achievement_motivation_response",
                family="achievement",
                label="Motivation response",
                source="preferences",
                value="progress_praise",
                confidence=0.78,
                freshness="medium",
            ),
        ],
        confidence_metadata={"peak_focus_hours": 0.84, "achievement_motivation_response": 0.78},
        freshness_metadata={"peak_focus_hours": "medium", "achievement_motivation_response": "medium"},
        evidence_backed_hypotheses=[
            {
                "id": "hypothesis:focus_window",
                "source_signals": ["peak_focus_hours"],
                "status": "provisional",
                "confidence_bound": 0.72,
            }
        ],
        prediction_summaries={
            "overload_risk": {
                "level": "medium",
                "confidence": 0.7,
            }
        },
    )
    profile_context = ProfileContext(
        preferences={"insight_scope_overrides": {"achievement_motivation_response": {"scope": "exam_mode_only"}}},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(),
        cognitive_summary=CognitiveSummary(),
    )

    summary = await UserInsightCalibrationService(db_session).calibrate(
        user_id=test_user.id,
        state=state,
        profile_context=profile_context,
    )

    assert summary["recent_correction_count"] == 1
    assert summary["strategy_outcome_sample_count"] == 3
    assert summary["demoted_signals"][0]["signal_id"] == "peak_focus_hours"
    assert "achievement_motivation_response" in summary["inactive_effective_signals"]
    assert "peak_focus_hours" in summary["inactive_effective_signals"]
    assert state.confidence_metadata["peak_focus_hours"] < 0.84
    assert "peak_focus_hours" not in state.inferred_work_style
    assert "achievement_motivation_response" not in state.inferred_work_style
    assert "peak_focus_hours" not in state.temporal_patterns["calendar"]
    assert "achievement" not in state.temporal_patterns
    assert state.prediction_summaries["overload_risk"]["calibrated_confidence"] < 0.7
    assert state.evidence_backed_hypotheses == []
