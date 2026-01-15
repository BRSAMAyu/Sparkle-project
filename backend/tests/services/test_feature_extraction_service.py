"""
Unit Tests for Feature Extraction Service

Tests coverage:
- Learning rhythm detection (deviation, interruption frequency)
- Understanding friction detection (translation density, escalating granularity)
- Energy state detection (late night, short sessions)
- Task risk detection (consecutive failures, procrastination)
- Edge cases and boundary conditions
"""

import pytest
from app.services.feature_extraction_service import (
    feature_extraction_service,
    FeatureExtractionService,
    LearningRhythm,
    UnderstandingFriction,
    EnergyState,
    TaskRisk,
    FeatureExtractResult,
)


def test_extract_learning_rhythm_normal_session():
    """Test learning rhythm extraction for normal session"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 24,
            "interruptions": 2,
            "completion": 0.96,
        },
        "comprehension": {},
        "time": {},
    }

    result = service.extract(envelope)

    # Normal session: no deviation (24/25 = 96% > 70%)
    assert result.rhythm.deviating_from_plan is False
    # Interruption frequency: 2 / 24 * 60 = 5 per hour
    assert result.rhythm.interruption_frequency == 5


def test_extract_learning_rhythm_deviation():
    """Test deviation detection"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 15,  # 60% < 70% threshold
            "interruptions": 8,
            "completion": 0.60,
        },
        "comprehension": {},
        "time": {},
    }

    result = service.extract(envelope)

    assert result.rhythm.deviating_from_plan is True
    # 8 / 15 * 60 = 32 interruptions per hour
    assert result.rhythm.interruption_frequency == 32


def test_extract_learning_rhythm_zero_planned():
    """Test edge case: zero planned minutes"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 0,
            "actual_min": 10,
            "interruptions": 3,
            "completion": 0.0,
        },
        "comprehension": {},
        "time": {},
    }

    result = service.extract(envelope)

    # No planned time => no deviation can be detected
    assert result.rhythm.deviating_from_plan is False
    # Interruption frequency still calculated
    assert result.rhythm.interruption_frequency == 18  # 3 / 10 * 60


def test_extract_understanding_friction_low():
    """Test low comprehension friction"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {},
        "comprehension": {
            "translation_requests": 5,
            "translation_granularity": "word",
            "unknown_terms_saved": 2,
        },
        "time": {},
    }

    result = service.extract(envelope)

    # 5 / 30 * 10 = 1.67 ≈ 1 (rounded down)
    assert result.friction.translation_density == 1
    assert result.friction.escalating_granularity is False


def test_extract_understanding_friction_high():
    """Test high comprehension friction"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {},
        "comprehension": {
            "translation_requests": 15,  # High density
            "translation_granularity": "sentence",  # Escalated
            "unknown_terms_saved": 8,
        },
        "time": {},
    }

    result = service.extract(envelope)

    # 15 / 30 * 10 = 5
    assert result.friction.translation_density == 5
    assert result.friction.escalating_granularity is True


def test_extract_understanding_friction_page_level():
    """Test page-level granularity detection"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {},
        "comprehension": {
            "translation_requests": 3,
            "translation_granularity": "page",
            "unknown_terms_saved": 0,
        },
        "time": {},
    }

    result = service.extract(envelope)

    assert result.friction.escalating_granularity is True


def test_extract_energy_state_normal():
    """Test normal energy state (daytime, good session length)"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 25,
            "interruptions": 1,
            "completion": 1.0,
        },
        "comprehension": {},
        "time": {
            "local_hour": 15,  # 3 PM
            "day_of_week": "monday",
        },
    }

    result = service.extract(envelope)

    assert result.energy.late_night_fatigue is False
    assert result.energy.short_session_trend is False


def test_extract_energy_state_late_night():
    """Test late night fatigue detection"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 20,
            "interruptions": 5,
            "completion": 0.80,
        },
        "comprehension": {},
        "time": {
            "local_hour": 23,  # 11 PM
            "day_of_week": "friday",
        },
    }

    result = service.extract(envelope)

    assert result.energy.late_night_fatigue is True


def test_extract_energy_state_short_session():
    """Test short session trend detection"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 10,  # < 15 min threshold
            "interruptions": 3,
            "completion": 0.40,
        },
        "comprehension": {},
        "time": {
            "local_hour": 14,
            "day_of_week": "wednesday",
        },
    }

    result = service.extract(envelope)

    assert result.energy.short_session_trend is True


def test_extract_energy_state_zero_actual():
    """Test edge case: zero actual minutes"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 0,
            "interruptions": 0,
            "completion": 0.0,
        },
        "comprehension": {},
        "time": {
            "local_hour": 10,
            "day_of_week": "monday",
        },
    }

    result = service.extract(envelope)

    # Zero minutes => not short session (must be > 0)
    assert result.energy.short_session_trend is False


def test_extract_task_risk_procrastination():
    """Test procrastination detection"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 20,
            "interruptions": 8,  # > 5 threshold
            "completion": 0.80,
        },
        "comprehension": {},
        "time": {},
    }

    result = service.extract(envelope)

    assert result.risk.procrastination_detected is True
    # consecutive_failures always False (TODO: query from DB)
    assert result.risk.consecutive_failures is False


def test_extract_task_risk_no_procrastination():
    """Test normal task completion (no procrastination)"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 25,
            "interruptions": 2,  # <= 5 threshold
            "completion": 1.0,
        },
        "comprehension": {},
        "time": {},
    }

    result = service.extract(envelope)

    assert result.risk.procrastination_detected is False


def test_extract_complete_envelope():
    """Test extraction from complete envelope"""
    service = FeatureExtractionService()

    envelope = {
        "context_version": "ce_v1",
        "window": "last_30min",
        "focus": {
            "planned_min": 25,
            "actual_min": 18,
            "interruptions": 7,
            "completion": 0.72,
        },
        "comprehension": {
            "translation_requests": 12,
            "translation_granularity": "sentence",
            "unknown_terms_saved": 3,
        },
        "time": {
            "local_hour": 22,
            "day_of_week": "thursday",
        },
        "content": {
            "language": "en",
            "domain": "cs",
        },
        "pii_scrubbed": True,
    }

    result = service.extract(envelope)

    # Verify all features
    assert result.version == "fer_v1"

    # Rhythm: deviation + high interruption
    assert result.rhythm.deviating_from_plan is False  # 18/25 = 72% > 70%
    assert result.rhythm.interruption_frequency == 23  # 7/18*60

    # Friction: moderate density + escalation
    assert result.friction.translation_density == 4  # 12/30*10
    assert result.friction.escalating_granularity is True

    # Energy: late night + not short
    assert result.energy.late_night_fatigue is True
    assert result.energy.short_session_trend is False

    # Risk: procrastination detected
    assert result.risk.procrastination_detected is True


def test_extract_to_dict():
    """Test to_dict serialization"""
    service = FeatureExtractionService()

    envelope = {
        "focus": {
            "planned_min": 25,
            "actual_min": 20,
            "interruptions": 3,
            "completion": 0.80,
        },
        "comprehension": {
            "translation_requests": 8,
            "translation_granularity": "word",
            "unknown_terms_saved": 1,
        },
        "time": {
            "local_hour": 15,
            "day_of_week": "monday",
        },
    }

    result = service.extract(envelope)
    result_dict = result.to_dict()

    # Verify structure
    assert "version" in result_dict
    assert "rhythm" in result_dict
    assert "friction" in result_dict
    assert "energy" in result_dict
    assert "risk" in result_dict

    # Verify nested structure
    assert "deviating_from_plan" in result_dict["rhythm"]
    assert "interruption_frequency" in result_dict["rhythm"]
    assert "translation_density" in result_dict["friction"]
    assert "escalating_granularity" in result_dict["friction"]


def test_extract_empty_envelope():
    """Test extraction from minimal envelope"""
    service = FeatureExtractionService()

    envelope = {}

    result = service.extract(envelope)

    # Should handle gracefully with defaults
    assert result.rhythm.deviating_from_plan is False
    assert result.rhythm.interruption_frequency == 0
    assert result.friction.translation_density == 0
    assert result.friction.escalating_granularity is False
    assert result.energy.late_night_fatigue is False
    assert result.energy.short_session_trend is False
    assert result.risk.procrastination_detected is False


def test_singleton_instance():
    """Test singleton instance is available"""
    from app.services.feature_extraction_service import feature_extraction_service

    assert feature_extraction_service is not None
    assert isinstance(feature_extraction_service, FeatureExtractionService)
