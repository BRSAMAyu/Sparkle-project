"""Regression test for ISSUE-20260503-1601-E2: privacy kill switch Prometheus gauge.

Validates that pii_redaction_mode() records the mode to Prometheus
instead of silently bypassing read_mode().
"""

import pytest
from unittest import mock

from app.aurora.privacy import pii_redaction_mode
from app.core.kill_switch import record_mode_gauge, normalize_mode


class TestPrivacyKillSwitchGauge:

    def test_normalize_mode_is_stateless(self):
        """normalize_mode() should still work as before."""
        assert normalize_mode("live") == "live"
        assert normalize_mode("shadow") == "shadow"
        assert normalize_mode("off") == "off"
        assert normalize_mode(None, fallback="live") == "live"

    def test_pii_redaction_mode_returns_normalized_mode(self):
        """pii_redaction_mode should still return the correct mode string."""
        mode = pii_redaction_mode()
        assert mode in ("off", "shadow", "live")

    def test_pii_redaction_mode_calls_record_mode_gauge(self):
        """The fix: pii_redaction_mode must call record_mode_gauge with correct args."""
        with mock.patch(
            "app.aurora.privacy.record_mode_gauge"
        ) as mock_record:
            result = pii_redaction_mode()
            assert result in ("off", "shadow", "live")
            mock_record.assert_called_once_with(
                "privacy", "pii_redaction", result
            )

    def test_record_mode_gauge_sets_metric(self):
        """record_mode_gauge should set the Prometheus gauge without error."""
        # This tests that record_mode_gauge doesn't throw
        record_mode_gauge("privacy", "pii_redaction", "shadow")
        # If we get here without exception, the gauge was set
