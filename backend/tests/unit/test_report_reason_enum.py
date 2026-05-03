"""Regression test for ISSUE-20260503-2102-I3: ReportReason enum cross-layer sync.

Validates that:
1. Backend ReportReasonEnum has both hate_speech and inappropriate
2. The two previously missing cross-layer values are present
"""

import pytest
from app.schemas.community import ReportReasonEnum


class TestReportReasonEnumCrossLayer:

    def test_backend_has_all_seven_values(self):
        """After fix, backend should have 7 values covering both Flutter's
        hate_speech and backend's original inappropriate."""
        values = set(ReportReasonEnum.__members__.keys())
        assert len(values) == 7, f"Expected 7, got {len(values)}: {values}"

    def test_backend_accepts_hate_speech(self):
        """Flutter sends hate_speech — backend must accept it (was 422 before fix)."""
        assert ReportReasonEnum.HATE_SPEECH == "hate_speech"
        assert ReportReasonEnum("hate_speech") == ReportReasonEnum.HATE_SPEECH

    def test_backend_keeps_inappropriate(self):
        """Backend's original inappropriate must still work."""
        assert ReportReasonEnum.INAPPROPRIATE == "inappropriate"
        assert ReportReasonEnum("inappropriate") == ReportReasonEnum.INAPPROPRIATE

    def test_original_five_unchanged(self):
        """Core 5 values that were already consistent across layers."""
        for val in ("spam", "harassment", "violence", "misinformation", "other"):
            assert val in ReportReasonEnum.__members__.values()
