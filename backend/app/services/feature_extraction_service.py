"""
Feature Extraction Service
Extracts objective features from ContextEnvelope for signal generation

This service processes compressed context from mobile and extracts
decision-ready features WITHOUT making decisions itself.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger


@dataclass
class LearningRhythm:
    """Learning rhythm metrics"""
    deviating_from_plan: bool
    interruption_frequency: int  # interruptions per hour


@dataclass
class UnderstandingFriction:
    """Comprehension friction metrics"""
    translation_density: int  # translation requests per 10 minutes
    escalating_granularity: bool  # word → sentence → page


@dataclass
class EnergyState:
    """Energy and fatigue metrics"""
    late_night_fatigue: bool  # studying after 22:00
    short_session_trend: bool  # actual < 15 min


@dataclass
class TaskRisk:
    """Task completion risk metrics"""
    consecutive_failures: bool  # multiple incomplete sessions
    procrastination_detected: bool  # high interruption count


@dataclass
class FeatureExtractResult:
    """Complete feature extraction result"""
    version: str  # "fer_v1"
    rhythm: LearningRhythm
    friction: UnderstandingFriction
    energy: EnergyState
    risk: TaskRisk

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "rhythm": {
                "deviating_from_plan": self.rhythm.deviating_from_plan,
                "interruption_frequency": self.rhythm.interruption_frequency,
            },
            "friction": {
                "translation_density": self.friction.translation_density,
                "escalating_granularity": self.friction.escalating_granularity,
            },
            "energy": {
                "late_night_fatigue": self.energy.late_night_fatigue,
                "short_session_trend": self.energy.short_session_trend,
            },
            "risk": {
                "consecutive_failures": self.risk.consecutive_failures,
                "procrastination_detected": self.risk.procrastination_detected,
            },
        }


class FeatureExtractionService:
    """
    Extract objective features from ContextEnvelope

    Design principle: "Measurement, not decision"
    - Input: ContextEnvelope (compressed context from mobile)
    - Output: FeatureExtractResult (objective metrics)
    - NO decision-making logic here (belongs in signal generation)
    """

    VERSION = "fer_v1"

    # Thresholds for feature detection
    DEVIATION_THRESHOLD = 0.7  # 70% completion threshold
    LATE_NIGHT_HOUR = 22  # 22:00 (10 PM)
    SHORT_SESSION_MINUTES = 15
    HIGH_INTERRUPTION_COUNT = 5
    TRANSLATION_DENSITY_THRESHOLD = 3  # requests per 10min

    def extract(self, envelope: Dict[str, Any]) -> FeatureExtractResult:
        """
        Extract features from context envelope

        Args:
            envelope: Context envelope dict with keys:
                - focus: {planned_min, actual_min, interruptions, completion}
                - comprehension: {translation_requests, translation_granularity, unknown_terms_saved}
                - time: {local_hour, day_of_week}
                - content: {language, domain}

        Returns:
            FeatureExtractResult with objective metrics
        """
        focus = envelope.get("focus", {})
        comprehension = envelope.get("comprehension", {})
        time_ctx = envelope.get("time", {})

        # Extract learning rhythm features
        rhythm = self._extract_learning_rhythm(focus)

        # Extract comprehension friction features
        friction = self._extract_understanding_friction(comprehension)

        # Extract energy state features
        energy = self._extract_energy_state(focus, time_ctx)

        # Extract task risk features
        risk = self._extract_task_risk(focus)

        result = FeatureExtractResult(
            version=self.VERSION,
            rhythm=rhythm,
            friction=friction,
            energy=energy,
            risk=risk,
        )

        logger.debug(
            f"Feature extraction completed: "
            f"rhythm.deviating={rhythm.deviating_from_plan}, "
            f"friction.density={friction.translation_density}, "
            f"energy.fatigue={energy.late_night_fatigue}, "
            f"risk.procrastination={risk.procrastination_detected}"
        )

        return result

    def _extract_learning_rhythm(self, focus: Dict[str, Any]) -> LearningRhythm:
        """
        Extract learning rhythm metrics

        Detects:
        - Deviation from plan (actual < planned * 0.7)
        - Interruption frequency (per hour)
        """
        planned_min = focus.get("planned_min", 0)
        actual_min = focus.get("actual_min", 0)
        interruptions = focus.get("interruptions", 0)

        # Deviation detection
        deviating_from_plan = False
        if planned_min > 0:
            deviating_from_plan = actual_min < (planned_min * self.DEVIATION_THRESHOLD)

        # Interruption frequency calculation
        interruption_frequency = 0
        if actual_min > 0:
            interruption_frequency = int((interruptions / actual_min) * 60)

        return LearningRhythm(
            deviating_from_plan=deviating_from_plan,
            interruption_frequency=interruption_frequency,
        )

    def _extract_understanding_friction(
        self, comprehension: Dict[str, Any]
    ) -> UnderstandingFriction:
        """
        Extract comprehension friction metrics

        Detects:
        - Translation density (requests per 10 minutes)
        - Escalating granularity (word → sentence → page)
        """
        translation_requests = comprehension.get("translation_requests", 0)
        translation_granularity = comprehension.get("translation_granularity", "word")

        # Translation density (assuming 30-minute window)
        # Normalize to per-10-minutes
        translation_density = int((translation_requests / 30) * 10)

        # Escalating granularity detection
        escalating_granularity = translation_granularity in ["sentence", "page"]

        return UnderstandingFriction(
            translation_density=translation_density,
            escalating_granularity=escalating_granularity,
        )

    def _extract_energy_state(
        self, focus: Dict[str, Any], time_ctx: Dict[str, Any]
    ) -> EnergyState:
        """
        Extract energy state metrics

        Detects:
        - Late night fatigue (studying after 22:00)
        - Short session trend (actual < 15 minutes)
        """
        local_hour = time_ctx.get("local_hour", 12)
        actual_min = focus.get("actual_min", 0)

        # Late night detection
        late_night_fatigue = local_hour >= self.LATE_NIGHT_HOUR

        # Short session trend
        short_session_trend = actual_min < self.SHORT_SESSION_MINUTES and actual_min > 0

        return EnergyState(
            late_night_fatigue=late_night_fatigue,
            short_session_trend=short_session_trend,
        )

    def _extract_task_risk(self, focus: Dict[str, Any]) -> TaskRisk:
        """
        Extract task risk metrics

        Detects:
        - Consecutive failures (TODO: query from database)
        - Procrastination (high interruption count)
        """
        interruptions = focus.get("interruptions", 0)

        # TODO: Query database for consecutive failures
        # For now, always return False
        consecutive_failures = False

        # Procrastination detection
        procrastination_detected = interruptions > self.HIGH_INTERRUPTION_COUNT

        return TaskRisk(
            consecutive_failures=consecutive_failures,
            procrastination_detected=procrastination_detected,
        )

    def extract_from_proto(self, envelope_proto) -> FeatureExtractResult:
        """
        Extract features from proto message

        Args:
            envelope_proto: ContextEnvelope proto message

        Returns:
            FeatureExtractResult
        """
        # Convert proto to dict
        envelope_dict = {
            "focus": {
                "planned_min": envelope_proto.focus.planned_min,
                "actual_min": envelope_proto.focus.actual_min,
                "interruptions": envelope_proto.focus.interruptions,
                "completion": envelope_proto.focus.completion,
            },
            "comprehension": {
                "translation_requests": envelope_proto.comprehension.translation_requests,
                "translation_granularity": envelope_proto.comprehension.translation_granularity,
                "unknown_terms_saved": envelope_proto.comprehension.unknown_terms_saved,
            },
            "time": {
                "local_hour": envelope_proto.time.local_hour,
                "day_of_week": envelope_proto.time.day_of_week,
            },
            "content": {
                "language": envelope_proto.content.language,
                "domain": envelope_proto.content.domain,
            },
        }

        return self.extract(envelope_dict)


# Singleton instance
feature_extraction_service = FeatureExtractionService()
