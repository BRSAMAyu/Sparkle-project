from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.core.user_insight_state import UserInsightState
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.calendar_event import CalendarEvent
from app.models.capsule_favorite import CapsuleFavorite
from app.models.cognitive import BehaviorPattern
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.memory import MemoryCorrection
from app.models.task import Task, TaskStatus, TaskType
from app.models.tool_history import UserToolHistory
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.profile_context_service import ProfileContextService
from app.services.profile_truth_compiler import ProfileTruthCompiler


@pytest.mark.asyncio
async def test_profile_context_service_compiles_canonical_user_insight_state_with_expanded_signal_families(
    db_session,
    test_user,
):
    partner = User(
        username="partner_user",
        email="partner@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(partner)
    await db_session.flush()

    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            version=1,
            explicit={
                "learning_style": "structured",
                "learning_goal_type": "exam",
            },
            inferred={
                "motivation_type": "streak_driven",
                "achievement_peak_hours": [19, 20],
                "achievement_motivation_response": "progress_praise",
                "achievement_pace_style": "steady",
                "achievement_reward_sensitivity": "high",
                "peak_focus_hours": [18, 19],
                "inactive_push_hours": [9],
                "exam_urgency": {"days_left": 12, "urgency": "high"},
            },
        )
    )

    base_day = datetime(2026, 4, 6, 18, 0)
    db_session.add_all(
        [
            CalendarEvent(
                user_id=test_user.id,
                title="Weekly seminar",
                start_time=base_day,
                end_time=base_day + timedelta(hours=1),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Weekly seminar 2",
                start_time=base_day - timedelta(days=7),
                end_time=base_day - timedelta(days=7) + timedelta(hours=1),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Lab block",
                start_time=datetime(2026, 4, 6, 12, 0),
                end_time=datetime(2026, 4, 6, 14, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Class",
                start_time=datetime(2026, 4, 6, 9, 0),
                end_time=datetime(2026, 4, 6, 10, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Review block",
                start_time=datetime(2026, 4, 7, 16, 0),
                end_time=datetime(2026, 4, 7, 18, 0),
                source="manual",
                reminder_minutes=[],
            ),
            CalendarEvent(
                user_id=test_user.id,
                title="Problem set",
                start_time=datetime(2026, 4, 7, 19, 0),
                end_time=datetime(2026, 4, 7, 20, 0),
                source="manual",
                reminder_minutes=[],
            ),
        ]
    )

    db_session.add_all(
        [
            UserToolHistory(user_id=test_user.id, tool_name="search_knowledge", success=True, execution_time_ms=900),
            UserToolHistory(user_id=test_user.id, tool_name="search_knowledge", success=True, execution_time_ms=1100),
            UserToolHistory(user_id=test_user.id, tool_name="search_knowledge", success=True, execution_time_ms=1000),
            UserToolHistory(user_id=test_user.id, tool_name="browser_agent", success=False, execution_time_ms=2500),
        ]
    )

    db_session.add_all(
        [
            Task(
                user_id=test_user.id,
                title="Thermo warmup",
                type=TaskType.LEARNING,
                tags=[],
                estimated_minutes=25,
                difficulty=2,
                energy_cost=2,
                status=TaskStatus.COMPLETED,
                started_at=datetime(2026, 4, 5, 19, 0),
                completed_at=datetime(2026, 4, 5, 19, 25),
                due_date=datetime(2026, 4, 8).date(),
                priority=2,
            ),
            Task(
                user_id=test_user.id,
                title="Entropy review",
                type=TaskType.LEARNING,
                tags=[],
                estimated_minutes=40,
                difficulty=3,
                energy_cost=3,
                status=TaskStatus.IN_PROGRESS,
                started_at=datetime(2026, 4, 6, 18, 30),
                due_date=datetime(2026, 4, 9).date(),
                priority=3,
            ),
        ]
    )

    capsule_a = CuriosityCapsule(
        user_id=test_user.id,
        title="Thermo deep dive",
        content="content",
        related_subject="Thermodynamics",
        depth_level=DepthLevel.DEEP,
        share_count=2,
    )
    capsule_b = CuriosityCapsule(
        user_id=test_user.id,
        title="Physics proof sketch",
        content="content",
        related_subject="Physics",
        depth_level=DepthLevel.DEEP,
        share_count=1,
    )
    db_session.add_all([capsule_a, capsule_b])
    await db_session.flush()
    db_session.add_all(
        [
            CapsuleFavorite(user_id=test_user.id, capsule_id=capsule_a.id, note="revisit"),
            CapsuleFavorite(user_id=test_user.id, capsule_id=capsule_b.id, note="important"),
        ]
    )
    db_session.add(
        BehaviorPattern(
            user_id=test_user.id,
            pattern_name="The Perfectionism-Avoidance Loop",
            pattern_type="cognitive",
            confidence_score=0.96,
            description="English placeholder",
            solution_text="English placeholder",
        )
    )

    partnership = AccountabilityPartnership(
        initiator_id=test_user.id,
        partner_id=partner.id,
        initiator_goal="Exam prep",
        partner_goal="Support exam prep",
        check_in_days=1,
        slot_type=AccountabilitySlotType.CORE,
        status=AccountabilityStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db_session.add(partnership)
    await db_session.flush()
    db_session.add_all(
        [
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=test_user.id,
                content="Checked in",
                mood=4,
                minutes=35,
            ),
            AccountabilityCheckin(
                partnership_id=partnership.id,
                user_id=test_user.id,
                content="Stayed consistent",
                mood=4,
                minutes=40,
            ),
        ]
    )

    await db_session.commit()

    context = await ProfileContextService(db_session, redis=None).get_profile_context(test_user.id)
    state = context.user_insight_state

    assert state is not None
    families = {item.family for item in state.signal_evidence}
    assert {"achievement", "calendar", "workflow", "content", "community"}.issubset(families)
    assert {"motivation", "cognitive"}.issubset(families)
    assert state.inferred_work_style["motivation_type"] == "streak_driven"
    assert state.inferred_work_style["achievement_pace_style"] == "steady"
    assert state.inferred_work_style["preferred_tools"][0] == "search_knowledge"
    assert state.stable_preferences["content_depth_preference"] == "deep"
    assert state.inferred_work_style["accountability_support"] == "active"
    assert state.temporal_patterns["anti_patterns"][0]["pattern_name"] == "完美主义回避循环"
    assert state.temporal_patterns["cognitive_tendencies"][0]["pattern_name"] == "完美主义回避循环"
    assert state.temporal_patterns["calendar"]["recurring_windows"]
    assert state.multi_span_analysis["short_span"]["overload_pressure"] in {"low", "medium", "high"}
    assert state.multi_span_analysis["medium_span"]["task_start_completion_drift"]["label"] in {
        "moderate_drift",
        "high_drift",
        "completion_keeps_up",
    }
    assert state.prediction_summaries["planning_readiness"]["level"] in {"low", "medium", "high"}
    assert state.prediction_summaries["planning_readiness"]["recommended_action"] in {
        "ask",
        "provisional",
        "proceed",
    }
    assert state.prediction_summaries["schedule_fit"]["level"] in {"low", "medium", "high"}
    assert state.prediction_summaries["likely_task_failure_modes"]["modes"]
    assert any(goal["type"] == "exam_window" for goal in state.goals)


@pytest.mark.asyncio
async def test_profile_truth_compiler_projects_canonical_user_insight_state_without_losing_phase_a_logic() -> None:
    canonical = UserInsightState(
        stable_preferences={"learning_style": "structured"},
        current_state={"overall_mastery": 0.55, "active_subjects": ["Physics"]},
        constraints=[
            {
                "id": "cognitive:Perfectionism Paralysis",
                "label": "Perfectionism Paralysis",
                "type": "behavioral",
                "origin": "cognitive_summary",
                "policy_signals": ["task.difficulty.start_easy"],
            }
        ],
        active_bottlenecks=[{"id": "knowledge:entropy", "label": "Entropy", "type": "knowledge_gap"}],
        confidence_metadata={"cognitive:Perfectionism Paralysis": 0.83},
        freshness_metadata={"preferences": "high"},
    )
    profile_context = ProfileContext(
        preferences={},
        preference_version=0,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.55,
            weak_spots=[],
            recent_mastery_changes=[],
            active_learning_subjects=["Physics"],
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[],
            dominant_pattern_type=None,
            risk_signals=[],
        ),
        user_insight_state=canonical,
    )

    state = await ProfileTruthCompiler().compile(
        profile_context=profile_context,
        user_strategy_state={"session_mode": "recovery"},
        turn_signals={"wants_push": True, "requested_difficulty": "hard"},
    )

    assert state.stable_traits["learning_style"] == "structured"
    assert state.current_state["strategy_mode"] == "recovery"
    assert state.active_constraints[0]["id"] == "cognitive:Perfectionism Paralysis"


@pytest.mark.asyncio
async def test_profile_context_service_user_correction_removes_signal_influence_from_analysis_and_prediction(
    db_session,
    test_user,
):
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            version=1,
            explicit={"learning_goal_type": "exam"},
            inferred={"peak_focus_hours": [19, 20]},
        )
    )
    db_session.add(
        MemoryCorrection(
            user_id=test_user.id,
            memory_type="insight_signal",
            memory_id=test_user.id,
            action="wrong",
            reason='{"target_id": "peak_focus_hours", "reason": "No longer true"}',
        )
    )
    await db_session.commit()

    context = await ProfileContextService(db_session, redis=None).get_profile_context(test_user.id)
    state = context.user_insight_state

    assert state is not None
    assert "peak_focus_hours" not in state.inferred_work_style
    assert state.multi_span_analysis["short_span"]["focus_alignment"] == "unclear"
    assert state.prediction_summaries["schedule_fit"]["level"] == "low"
