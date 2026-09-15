from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config.settings import Settings
from app.services.kill_switch_readiness_service import FeatureReadiness, KillSwitchReadinessService


def test_promoted_settings_defaults() -> None:
    defaults = Settings.model_fields

    assert defaults["AURORA_STAGE39_COGLOAD_ROUTE_MODE"].default == "live"
    assert defaults["AURORA_STAGE39_GALAXY_INJECT_MODE"].default == "live"
    assert defaults["AURORA_BAYESIAN_MODE"].default == "live"
    assert defaults["SPARKLE_MEMORY_INFERRED_WRITE_ENABLED"].default is True


@pytest.mark.asyncio
async def test_readiness_report_tracks_memory_inferred_write_live_default() -> None:
    settings = SimpleNamespace(
        SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=True,
        AURORA_BAYESIAN_MODE="shadow",
    )

    report = await KillSwitchReadinessService().get_readiness_report(settings)

    memory_write = report["memory_inferred_write"]
    assert isinstance(memory_write, FeatureReadiness)
    assert memory_write.current_mode == "live"
    assert memory_write.target_mode == "live"
    assert memory_write.ready_for_promotion is True
    assert memory_write.blocking_reasons == []
    assert memory_write.promotion_criteria


@pytest.mark.asyncio
async def test_readiness_report_tracks_bayesian_shadow_to_live_canary() -> None:
    settings = SimpleNamespace(
        SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False,
        AURORA_BAYESIAN_MODE="shadow",
    )

    report = await KillSwitchReadinessService().get_readiness_report(settings)

    bayesian = report["bayesian_learning"]
    assert bayesian.current_mode == "shadow"
    assert bayesian.target_mode == "live_canary"
    assert bayesian.ready_for_promotion is False
    assert any("outcome" in criterion for criterion in bayesian.promotion_criteria)
