"""
Unit Tests for Signal Generation Service

Tests coverage:
- Signal type generation from features
- Confidence scoring
- Confidence threshold filtering
- Multiple signals from same features
- Edge cases and boundary conditions
"""

import pytest
from app.services.signal_generation_service import (
    signal_generation_service,
    SignalGenerationService,
    Signal,
    Signals,
)
from app.services.feature_extraction_service import (
    FeatureExtractResult,
    LearningRhythm,
    UnderstandingFriction,
    EnergyState,
    TaskRisk,
)


def test_generate_no_signals():
    """Test feature set that generates no signals"""
    service = SignalGenerationService()

    # Perfect session: no issues
    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=2,
        ),
        friction=UnderstandingFriction(
            translation_density=1,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    assert result.version == "sig_v1"
    assert len(result.signals) == 0


def test_generate_risk_dropout_soon():
    """Test risk_dropout_soon signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=True,  # Trigger condition 1
            interruption_frequency=8,
        ),
        friction=UnderstandingFriction(
            translation_density=2,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=True,  # Trigger condition 2
        ),
    )

    result = service.generate(features)

    assert len(result.signals) > 0
    signal = next((s for s in result.signals if s.type == "risk_dropout_soon"), None)
    assert signal is not None
    assert signal.confidence == 0.75
    assert "连续多次中断" in signal.reason
    assert "interruptions" in signal.metadata


def test_generate_needs_break():
    """Test needs_break signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=6,  # > 4 threshold
        ),
        friction=UnderstandingFriction(
            translation_density=2,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=True,  # Trigger condition 1
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    signal = next((s for s in result.signals if s.type == "needs_break"), None)
    assert signal is not None
    assert signal.confidence == 0.80
    assert "深夜学习" in signal.reason
    assert "频繁中断" in signal.reason


def test_generate_topic_stuck():
    """Test topic_stuck signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=3,
        ),
        friction=UnderstandingFriction(
            translation_density=5,  # > 3 threshold
            escalating_granularity=True,  # Both conditions met
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    signal = next((s for s in result.signals if s.type == "topic_stuck"), None)
    assert signal is not None
    assert signal.confidence == 0.70
    assert "翻译请求" in signal.reason
    assert "理解遇到阻塞" in signal.reason
    assert signal.metadata["translation_density"] == 5


def test_generate_best_next_action_window():
    """Test best_next_action_window signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=True,  # Condition 1
            interruption_frequency=4,
        ),
        friction=UnderstandingFriction(
            translation_density=2,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,  # Condition 2: NOT late night
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    signal = next(
        (s for s in result.signals if s.type == "best_next_action_window"), None
    )
    assert signal is not None
    assert signal.confidence == 0.60
    assert "偏离计划" in signal.reason
    assert "精力状态尚可" in signal.reason


def test_generate_session_too_short():
    """Test session_too_short signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=3,
        ),
        friction=UnderstandingFriction(
            translation_density=1,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=True,  # Condition 1
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=True,  # Condition 2
        ),
    )

    result = service.generate(features)

    signal = next((s for s in result.signals if s.type == "session_too_short"), None)
    assert signal is not None
    assert signal.confidence == 0.68
    assert "短时段学习" in signal.reason


def test_generate_high_comprehension_friction():
    """Test high_comprehension_friction signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=2,
        ),
        friction=UnderstandingFriction(
            translation_density=8,  # > 5 threshold (even without escalation)
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    signal = next(
        (s for s in result.signals if s.type == "high_comprehension_friction"), None
    )
    assert signal is not None
    assert signal.confidence == 0.72
    assert "翻译请求密度过高" in signal.reason


def test_generate_consecutive_failures():
    """Test consecutive_failures signal generation"""
    service = SignalGenerationService()

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=False,
            interruption_frequency=2,
        ),
        friction=UnderstandingFriction(
            translation_density=1,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=True,  # Trigger condition
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    signal = next((s for s in result.signals if s.type == "consecutive_failures"), None)
    assert signal is not None
    assert signal.confidence == 0.85
    assert "连续多次未完成任务" in signal.reason


def test_generate_multiple_signals():
    """Test multiple signals generated from same features"""
    service = SignalGenerationService()

    # Feature set that triggers multiple conditions
    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=True,
            interruption_frequency=7,
        ),
        friction=UnderstandingFriction(
            translation_density=6,
            escalating_granularity=True,
        ),
        energy=EnergyState(
            late_night_fatigue=True,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=True,
        ),
    )

    result = service.generate(features)

    # Should generate multiple signals
    assert len(result.signals) >= 3

    # Check for expected signals
    signal_types = [s.type for s in result.signals]
    assert "risk_dropout_soon" in signal_types
    assert "needs_break" in signal_types
    assert "topic_stuck" in signal_types


def test_confidence_threshold_filtering():
    """Test that signals below threshold are filtered"""
    service = SignalGenerationService()

    # Modify threshold temporarily
    original_threshold = service.CONFIDENCE_THRESHOLD
    service.CONFIDENCE_THRESHOLD = 0.75

    features = FeatureExtractResult(
        version="fer_v1",
        rhythm=LearningRhythm(
            deviating_from_plan=True,
            interruption_frequency=3,
        ),
        friction=UnderstandingFriction(
            translation_density=1,
            escalating_granularity=False,
        ),
        energy=EnergyState(
            late_night_fatigue=False,
            short_session_trend=False,
        ),
        risk=TaskRisk(
            consecutive_failures=False,
            procrastination_detected=False,
        ),
    )

    result = service.generate(features)

    # best_next_action_window has confidence 0.60, should be filtered
    signal = next(
        (s for s in result.signals if s.type == "best_next_action_window"), None
    )
    assert signal is None

    # Restore threshold
    service.CONFIDENCE_THRESHOLD = original_threshold


def test_signal_to_dict():
    """Test Signal to_dict serialization"""
    signal = Signal(
        type="test_signal",
        confidence=0.85,
        reason="测试原因",
        metadata={"key": "value"},
    )

    signal_dict = signal.to_dict()

    assert signal_dict["type"] == "test_signal"
    assert signal_dict["confidence"] == 0.85
    assert signal_dict["reason"] == "测试原因"
    assert signal_dict["metadata"]["key"] == "value"


def test_signals_to_dict():
    """Test Signals to_dict serialization"""
    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(
                type="needs_break",
                confidence=0.80,
                reason="测试",
                metadata={},
            ),
            Signal(
                type="topic_stuck",
                confidence=0.70,
                reason="测试2",
                metadata={"density": 5},
            ),
        ],
    )

    signals_dict = signals.to_dict()

    assert signals_dict["version"] == "sig_v1"
    assert len(signals_dict["signals"]) == 2
    assert signals_dict["signals"][0]["type"] == "needs_break"
    assert signals_dict["signals"][1]["type"] == "topic_stuck"


def test_generate_from_dict():
    """Test generate_from_dict convenience method"""
    service = SignalGenerationService()

    features_dict = {
        "version": "fer_v1",
        "rhythm": {
            "deviating_from_plan": True,
            "interruption_frequency": 8,
        },
        "friction": {
            "translation_density": 2,
            "escalating_granularity": False,
        },
        "energy": {
            "late_night_fatigue": False,
            "short_session_trend": False,
        },
        "risk": {
            "consecutive_failures": False,
            "procrastination_detected": True,
        },
    }

    result = service.generate_from_dict(features_dict)

    assert result.version == "sig_v1"
    assert len(result.signals) > 0


def test_singleton_instance():
    """Test singleton instance is available"""
    from app.services.signal_generation_service import signal_generation_service

    assert signal_generation_service is not None
    assert isinstance(signal_generation_service, SignalGenerationService)
