"""
Tests for GAP-P4-12: STAB-011 non-exam crisis mode.

Verifies that CrisisModeFSM supports all goal types with
appropriate trigger conditions, policy constraints, and status labels.
"""

import pytest

from app.signals.crisis_mode_fsm import (
    CrisisModeFSM,
    CrisisSignals,
    CrisisState,
)


# ── Exam (baseline, unchanged) ──────────────────────────────────


class TestExamCrisisMode:
    """Verify exam crisis mode still works after generalization."""

    def test_exam_crisis_trigger(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            knowledge_gap="major",
            goal_type="exam",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_exam_no_trigger_without_pressure(self):
        signals = CrisisSignals(
            deadline_pressure="high",
            knowledge_gap="major",
            goal_type="exam",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)

    def test_exam_transition_to_crisis(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            knowledge_gap="major",
            goal_type="exam",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.state == CrisisState.CRISIS
        assert "考试" in snapshot.status_band_label or "危机" in snapshot.status_band_label

    def test_exam_policy_constraints(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            knowledge_gap="major",
            goal_type="exam",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.policy_constraints["max_task_duration_min"] == 15


# ── Project ──────────────────────────────────────────────────────


class TestProjectCrisisMode:
    """Project: deadline_pressure=critical + scope_bloat, or deadline_passed + high stress."""

    def test_project_crisis_deadline_and_scope_bloat(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="project",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_project_crisis_passed_deadline_high_stress(self):
        signals = CrisisSignals(
            deadline_passed=True,
            stress="high",
            goal_type="project",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_project_no_crisis_without_scope_bloat(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=False,
            goal_type="project",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)

    def test_project_crisis_label(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="project",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert "项目" in snapshot.status_band_label
        assert snapshot.policy_constraints.get("mvp_only") is True
        assert snapshot.policy_constraints.get("freeze_scope") is True

    def test_project_crisis_explanation(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="project",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert "MVP" in snapshot.status_band_explanation


# ── Job Search ───────────────────────────────────────────────────


class TestJobSearchCrisisMode:
    """Job search: interview_imminent + (knowledge_gap or high stress)."""

    def test_job_search_crisis_interview_and_gap(self):
        signals = CrisisSignals(
            interview_imminent=True,
            knowledge_gap="major",
            goal_type="job_search",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_job_search_crisis_interview_and_stress(self):
        signals = CrisisSignals(
            interview_imminent=True,
            stress="high",
            goal_type="job_search",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_job_search_crisis_interview_moderate_gap(self):
        signals = CrisisSignals(
            interview_imminent=True,
            knowledge_gap="moderate",
            goal_type="job_search",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_job_search_no_crisis_without_interview(self):
        signals = CrisisSignals(
            interview_imminent=False,
            stress="high",
            goal_type="job_search",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)

    def test_job_search_crisis_label(self):
        signals = CrisisSignals(
            interview_imminent=True,
            knowledge_gap="major",
            goal_type="job_search",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert "面试" in snapshot.status_band_label
        assert "面试" in snapshot.status_band_explanation

    def test_job_search_policy_constraints(self):
        signals = CrisisSignals(
            interview_imminent=True,
            knowledge_gap="major",
            goal_type="job_search",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.policy_constraints.get("focus_top_companies") is True


# ── Fitness ──────────────────────────────────────────────────────


class TestFitnessCrisisMode:
    """Fitness: injury_risk or skip_streak >= 5."""

    def test_fitness_crisis_injury_risk(self):
        signals = CrisisSignals(
            injury_risk=True,
            goal_type="fitness",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_fitness_crisis_skip_streak(self):
        signals = CrisisSignals(
            skip_streak=5,
            goal_type="fitness",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_fitness_no_crisis_below_threshold(self):
        signals = CrisisSignals(
            skip_streak=4,
            goal_type="fitness",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)

    def test_fitness_crisis_label(self):
        signals = CrisisSignals(
            injury_risk=True,
            goal_type="fitness",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert "恢复" in snapshot.status_band_label or "保护" in snapshot.status_band_label

    def test_fitness_policy_constraints(self):
        signals = CrisisSignals(
            injury_risk=True,
            goal_type="fitness",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.policy_constraints.get("reduce_intensity") is True
        assert snapshot.policy_constraints.get("focus_recovery") is True


# ── Startup ──────────────────────────────────────────────────────


class TestStartupCrisisMode:
    """Startup: deadline_pressure=critical + (scope_bloat or high stress)."""

    def test_startup_crisis_deadline_and_scope_bloat(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="startup",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_startup_crisis_deadline_and_stress(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            stress="high",
            goal_type="startup",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_startup_no_crisis_low_pressure(self):
        signals = CrisisSignals(
            deadline_pressure="high",
            scope_bloat=True,
            goal_type="startup",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)

    def test_startup_crisis_label(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="startup",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert "MVP" in snapshot.status_band_label or "冲刺" in snapshot.status_band_label
        assert snapshot.policy_constraints.get("mvp_only") is True


# ── General ──────────────────────────────────────────────────────


class TestGeneralCrisisMode:
    """General: deadline_pressure=critical + (fatigue high/critical or stress=high)."""

    def test_general_crisis_deadline_and_fatigue(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            fatigue="high",
            goal_type="general",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_general_crisis_deadline_and_stress(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            stress="high",
            goal_type="general",
        )
        assert CrisisModeFSM.is_crisis_trigger(signals)

    def test_general_no_crisis_without_deadline(self):
        signals = CrisisSignals(
            deadline_pressure="high",
            stress="high",
            goal_type="general",
        )
        assert not CrisisModeFSM.is_crisis_trigger(signals)


# ── Recovery transitions ────────────────────────────────────────


class TestRecoveryTransitions:
    """Recovery works for all goal types."""

    def test_project_recovery_on_deadline_passed(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="project",
        )
        crisis = CrisisModeFSM.transition(signals=signals)
        assert crisis.state == CrisisState.CRISIS

        recovery_signals = CrisisSignals(
            deadline_passed=True,
            goal_type="project",
        )
        recovery = CrisisModeFSM.transition(
            current_state=crisis.state,
            signals=recovery_signals,
        )
        assert recovery.state == CrisisState.RECOVERY
        assert "项目" in recovery.status_band_explanation

    def test_fitness_recovery_on_user_declared(self):
        signals = CrisisSignals(
            injury_risk=True,
            goal_type="fitness",
        )
        crisis = CrisisModeFSM.transition(signals=signals)
        assert crisis.state == CrisisState.CRISIS

        recovery_signals = CrisisSignals(
            user_declared_recovered=True,
            goal_type="fitness",
        )
        recovery = CrisisModeFSM.transition(
            current_state=crisis.state,
            signals=recovery_signals,
        )
        assert recovery.state == CrisisState.RECOVERY

    def test_job_search_warning_state(self):
        signals = CrisisSignals(
            deadline_pressure="critical",
            goal_type="job_search",
        )
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.state == CrisisState.WARNING
        assert "面试" in snapshot.status_band_label or "预警" in snapshot.status_band_label

    def test_normal_state_no_trigger(self):
        signals = CrisisSignals(goal_type="project")
        snapshot = CrisisModeFSM.transition(signals=signals)
        assert snapshot.state == CrisisState.NORMAL
        assert snapshot.policy_constraints == {}


# ── Serialization round-trip ─────────────────────────────────────


class TestSerialization:
    """CrisisSignals from_dict/to_dict preserves goal-type fields."""

    def test_round_trip_project(self):
        original = CrisisSignals(
            deadline_pressure="critical",
            scope_bloat=True,
            goal_type="project",
        )
        restored = CrisisSignals.from_dict(original.to_dict())
        assert restored.goal_type == "project"
        assert restored.scope_bloat is True
        assert restored.deadline_pressure == "critical"

    def test_round_trip_fitness(self):
        original = CrisisSignals(
            injury_risk=True,
            skip_streak=7,
            goal_type="fitness",
        )
        restored = CrisisSignals.from_dict(original.to_dict())
        assert restored.goal_type == "fitness"
        assert restored.injury_risk is True
        assert restored.skip_streak == 7

    def test_from_dict_defaults(self):
        restored = CrisisSignals.from_dict(None)
        assert restored.goal_type == "exam"
        assert restored.scope_bloat is False
        assert restored.skip_streak == 0
