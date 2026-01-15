"""
Signal Generation Service
Generates decision-ready signals from objective features

This service converts feature extraction results into actionable signals
with confidence scores and explainable reasons.
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from loguru import logger

from app.services.feature_extraction_service import FeatureExtractResult


@dataclass
class Signal:
    """Decision-ready signal with confidence score"""
    type: str  # Signal type identifier
    confidence: float  # 0.0-1.0
    reason: str  # Explainable reason in Chinese
    metadata: Dict[str, Any]  # Additional context

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class Signals:
    """Complete signal generation result"""
    version: str  # "sig_v1"
    signals: List[Signal]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "signals": [s.to_dict() for s in self.signals],
        }


class SignalGenerationService:
    """
    Generate actionable signals from features

    Design principle: "Decision, not measurement"
    - Input: FeatureExtractResult (objective metrics)
    - Output: Signals (decision-ready with confidence scores)
    - Contains decision logic based on features
    """

    VERSION = "sig_v1"

    # Minimum confidence threshold for signals to be actionable
    CONFIDENCE_THRESHOLD = 0.65

    def generate(self, features: FeatureExtractResult) -> Signals:
        """
        Generate signals from feature extraction result.

        Args:
            features: FeatureExtractResult with objective metrics

        Returns:
            Signals with decision-ready signals filtered by confidence threshold
        """
        signals = []

        # Signal 1: Risk dropout soon
        # Triggered when: procrastination detected AND deviating from plan
        if features.risk.procrastination_detected and features.rhythm.deviating_from_plan:
            signals.append(Signal(
                type="risk_dropout_soon",
                confidence=0.75,
                reason="连续多次中断且未完成计划专注时长",
                metadata={
                    "interruptions": features.rhythm.interruption_frequency,
                    "deviation": features.rhythm.deviating_from_plan,
                }
            ))

        # Signal 2: Needs break
        # Triggered when: late night fatigue AND high interruption frequency
        if features.energy.late_night_fatigue and features.rhythm.interruption_frequency > 4:
            signals.append(Signal(
                type="needs_break",
                confidence=0.80,
                reason="深夜学习且频繁中断，精力可能不足",
                metadata={
                    "late_night": features.energy.late_night_fatigue,
                    "interruption_freq": features.rhythm.interruption_frequency,
                }
            ))

        # Signal 3: Topic stuck (comprehension friction)
        # Triggered when: escalating granularity AND high translation density
        if features.friction.escalating_granularity and features.friction.translation_density > 3:
            signals.append(Signal(
                type="topic_stuck",
                confidence=0.70,
                reason="翻译请求从词汇升级为整句，理解遇到阻塞",
                metadata={
                    "translation_density": features.friction.translation_density,
                    "escalating": features.friction.escalating_granularity,
                }
            ))

        # Signal 4: Best next action window
        # Triggered when: deviating from plan BUT NOT late night fatigue
        if features.rhythm.deviating_from_plan and not features.energy.late_night_fatigue:
            signals.append(Signal(
                type="best_next_action_window",
                confidence=0.60,
                reason="偏离计划但精力状态尚可，适合重新规划",
                metadata={
                    "deviation": features.rhythm.deviating_from_plan,
                    "good_energy": not features.energy.late_night_fatigue,
                }
            ))

        # Signal 5: Short session pattern
        # Triggered when: short session trend AND procrastination detected
        if features.energy.short_session_trend and features.risk.procrastination_detected:
            signals.append(Signal(
                type="session_too_short",
                confidence=0.68,
                reason="多次短时段学习且频繁中断，可能需要调整学习计划",
                metadata={
                    "short_session": features.energy.short_session_trend,
                    "procrastination": features.risk.procrastination_detected,
                }
            ))

        # Signal 6: Consecutive failures risk
        # Triggered when: consecutive failures detected (future: from database)
        if features.risk.consecutive_failures:
            signals.append(Signal(
                type="consecutive_failures",
                confidence=0.85,
                reason="连续多次未完成任务，建议调整任务难度或拆分任务",
                metadata={
                    "consecutive_failures": features.risk.consecutive_failures,
                }
            ))

        # Signal 7: High comprehension friction
        # Triggered when: high translation density alone (even without escalation)
        if features.friction.translation_density > 5:
            signals.append(Signal(
                type="high_comprehension_friction",
                confidence=0.72,
                reason="翻译请求密度过高，内容理解难度较大",
                metadata={
                    "translation_density": features.friction.translation_density,
                }
            ))

        # Filter by confidence threshold
        filtered_signals = [s for s in signals if s.confidence >= self.CONFIDENCE_THRESHOLD]

        logger.debug(
            f"Signal generation completed: "
            f"generated={len(signals)}, filtered={len(filtered_signals)}, "
            f"threshold={self.CONFIDENCE_THRESHOLD}"
        )

        # Log each generated signal
        for signal in filtered_signals:
            logger.debug(
                f"Signal: type={signal.type}, confidence={signal.confidence:.2f}, "
                f"reason={signal.reason}"
            )

        return Signals(version=self.VERSION, signals=filtered_signals)

    def generate_from_dict(self, features_dict: Dict[str, Any]) -> Signals:
        """
        Generate signals from feature dictionary.

        Args:
            features_dict: Dictionary representation of FeatureExtractResult

        Returns:
            Signals with decision-ready signals
        """
        # Reconstruct FeatureExtractResult from dict
        from app.services.feature_extraction_service import (
            LearningRhythm,
            UnderstandingFriction,
            EnergyState,
            TaskRisk,
            FeatureExtractResult,
        )

        rhythm_data = features_dict.get("rhythm", {})
        friction_data = features_dict.get("friction", {})
        energy_data = features_dict.get("energy", {})
        risk_data = features_dict.get("risk", {})

        rhythm = LearningRhythm(
            deviating_from_plan=rhythm_data.get("deviating_from_plan", False),
            interruption_frequency=rhythm_data.get("interruption_frequency", 0),
        )

        friction = UnderstandingFriction(
            translation_density=friction_data.get("translation_density", 0),
            escalating_granularity=friction_data.get("escalating_granularity", False),
        )

        energy = EnergyState(
            late_night_fatigue=energy_data.get("late_night_fatigue", False),
            short_session_trend=energy_data.get("short_session_trend", False),
        )

        risk = TaskRisk(
            consecutive_failures=risk_data.get("consecutive_failures", False),
            procrastination_detected=risk_data.get("procrastination_detected", False),
        )

        features = FeatureExtractResult(
            version=features_dict.get("version", "fer_v1"),
            rhythm=rhythm,
            friction=friction,
            energy=energy,
            risk=risk,
        )

        return self.generate(features)


# Singleton instance
signal_generation_service = SignalGenerationService()
