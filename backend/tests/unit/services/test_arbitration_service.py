"""Tests for ArbitrationService pure logic: EscalationRulesEngine."""
import pytest

from app.services.arbitration_service import (
    ArbitrationPriority,
    EscalationReason,
    EscalationRulesEngine,
)


class TestShouldEscalate:
    """Table-driven tests for EscalationRulesEngine.should_escalate."""

    @pytest.mark.parametrize(
        "original,secondary,confidence,appeals,sensitive,expected_escalate,expected_reason",
        [
            # Sensitive content always escalates
            (0.9, 0.9, 0.99, 1, True, True, EscalationReason.SENSITIVE_CONTENT),
            # Repeat appeal
            (0.5, 0.5, 0.8, 2, False, True, EscalationReason.REPEAT_APPEAL),
            (0.5, 0.5, 0.8, 5, False, True, EscalationReason.REPEAT_APPEAL),
            # Low confidence
            (0.5, 0.5, 0.3, 1, False, True, EscalationReason.LOW_CONFIDENCE),
            (0.5, 0.5, 0.59, 1, False, True, EscalationReason.LOW_CONFIDENCE),
            # Score discrepancy
            (0.2, 0.7, 0.8, 1, False, True, EscalationReason.SCORE_DISCREPANCY),
            (0.5, 0.76, 0.9, 1, False, True, EscalationReason.SCORE_DISCREPANCY),
            # No escalation needed
            (0.5, 0.6, 0.8, 1, False, False, None),
            (0.5, None, 0.9, 1, False, False, None),
            # Boundary: confidence exactly at threshold does NOT escalate
            (0.5, 0.5, 0.6, 1, False, False, None),
            # Boundary: discrepancy exactly at threshold DOES escalate
            (0.0, 0.25, 0.8, 1, False, True, EscalationReason.SCORE_DISCREPANCY),
        ],
    )
    def test_escalation_logic(
        self, original, secondary, confidence, appeals, sensitive, expected_escalate, expected_reason
    ):
        should, reason = EscalationRulesEngine.should_escalate(
            original_score=original,
            secondary_score=secondary,
            confidence=confidence,
            appeal_count=appeals,
            is_sensitive=sensitive,
        )
        assert should == expected_escalate
        assert reason == expected_reason

    def test_sensitive_takes_precedence_over_low_confidence(self):
        should, reason = EscalationRulesEngine.should_escalate(
            original_score=0.5, secondary_score=0.5, confidence=0.1, appeal_count=1, is_sensitive=True
        )
        assert should is True
        assert reason == EscalationReason.SENSITIVE_CONTENT

    def test_repeat_appeal_takes_precedence_over_low_confidence(self):
        should, reason = EscalationRulesEngine.should_escalate(
            original_score=0.5, secondary_score=0.5, confidence=0.1, appeal_count=5, is_sensitive=False
        )
        assert should is True
        assert reason == EscalationReason.REPEAT_APPEAL


class TestCalculatePriority:
    """Table-driven tests for EscalationRulesEngine.calculate_priority."""

    @pytest.mark.parametrize(
        "reason,tier,wait_hours,expected",
        [
            # Sensitive = urgent
            (EscalationReason.SENSITIVE_CONTENT, "free", 0, ArbitrationPriority.URGENT),
            # Policy violation = urgent
            (EscalationReason.POLICY_VIOLATION, "free", 0, ArbitrationPriority.URGENT),
            # System error = high
            (EscalationReason.SYSTEM_ERROR, "free", 0, ArbitrationPriority.HIGH),
            # Score discrepancy = normal
            (EscalationReason.SCORE_DISCREPANCY, "free", 0, ArbitrationPriority.NORMAL),
            # Low confidence = normal
            (EscalationReason.LOW_CONFIDENCE, "free", 0, ArbitrationPriority.NORMAL),
            # Pro user upgrades normal → high
            (EscalationReason.SCORE_DISCREPANCY, "pro", 0, ArbitrationPriority.HIGH),
            # Enterprise user upgrades normal → high
            (EscalationReason.LOW_CONFIDENCE, "enterprise", 0, ArbitrationPriority.HIGH),
            # Pro + system error = urgent (high → urgent)
            (EscalationReason.SYSTEM_ERROR, "pro", 0, ArbitrationPriority.URGENT),
            # Long wait upgrades normal → high
            (EscalationReason.SCORE_DISCREPANCY, "free", 25, ArbitrationPriority.HIGH),
            # Pro + long wait upgrades normal → urgent (normal→high via pro, high→urgent via wait)
            (EscalationReason.SCORE_DISCREPANCY, "pro", 25, ArbitrationPriority.URGENT),
        ],
    )
    def test_priority_calculation(self, reason, tier, wait_hours, expected):
        result = EscalationRulesEngine.calculate_priority(
            escalation_reason=reason, user_tier=tier, waiting_hours=wait_hours
        )
        assert result == expected

    def test_free_tier_does_not_upgrade(self):
        result = EscalationRulesEngine.calculate_priority(
            escalation_reason=EscalationReason.REPEAT_APPEAL, user_tier="free", waiting_hours=0
        )
        assert result == ArbitrationPriority.NORMAL

    def test_urgent_stays_urgent_with_all_upgrades(self):
        result = EscalationRulesEngine.calculate_priority(
            escalation_reason=EscalationReason.SENSITIVE_CONTENT, user_tier="enterprise", waiting_hours=48
        )
        assert result == ArbitrationPriority.URGENT
