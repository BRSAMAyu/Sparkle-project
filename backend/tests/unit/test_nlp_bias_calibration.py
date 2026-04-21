from __future__ import annotations

import pytest

from app.config import settings
from app.services.traits_bias_calibration import CALIBRATION_SAMPLES
from app.services.traits_nlp_observer_service import TraitsNlpObserverService


def test_bias_calibration_has_five_or_more_samples() -> None:
    assert len(CALIBRATION_SAMPLES) >= 5


def test_bias_calibration_covers_multiple_languages() -> None:
    assert len({sample.language for sample in CALIBRATION_SAMPLES}) >= 5


@pytest.mark.asyncio
async def test_bias_calibration_reports_bias_rate_payload(db_session) -> None:
    result = await TraitsNlpObserverService(db_session).validate_bias_calibration()

    assert set(result.keys()) >= {"sample_count", "mismatches", "total_checks", "bias_rate", "passed"}


@pytest.mark.asyncio
async def test_bias_calibration_bias_rate_stays_bounded(db_session) -> None:
    result = await TraitsNlpObserverService(db_session).validate_bias_calibration()
    assert 0.0 <= result["bias_rate"] <= 1.0


@pytest.mark.asyncio
async def test_bias_calibration_uses_threshold_from_settings(db_session) -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 1.0
    result = await TraitsNlpObserverService(db_session).validate_bias_calibration()
    assert result["passed"] is True
