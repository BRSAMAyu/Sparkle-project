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


# ---------------------------------------------------------------------------
# EI-06：readiness 报告不得引用不存在的 settings 键，缺键不得静默回退
# ---------------------------------------------------------------------------


def test_catalog_settings_keys_all_exist_in_settings_model() -> None:
    """FEATURE_CATALOG 引用的每个 settings 键都必须真实存在于 Settings 模型。"""
    from app.config.settings import Settings

    model_keys = set(Settings.model_fields)
    unknown = {
        feature_key: catalog["settings_key"]
        for feature_key, catalog in KillSwitchReadinessService.FEATURE_CATALOG.items()
        if catalog["settings_key"] not in model_keys
    }

    assert not unknown, (
        "readiness 目录引用了不存在的 settings 键（报告会静默回退到预期值）："
        f"{unknown}"
    )


@pytest.mark.asyncio
async def test_full_catalog_against_settings_defaults_resolves_every_mode() -> None:
    """用 Settings 全量默认值驱动报告：任何条目都不应落在 unknown。"""
    from app.config.settings import Settings

    defaults = SimpleNamespace(
        **{name: f.default for name, f in Settings.model_fields.items()}
    )

    report = await KillSwitchReadinessService().get_readiness_report(defaults)

    unresolved = sorted(
        feature_key for feature_key, readiness in report.items() if readiness.current_mode == "unknown"
    )
    assert report.keys() == KillSwitchReadinessService.FEATURE_CATALOG.keys()
    assert not unresolved, f"以下条目无法从 Settings 默认值解析出模式: {unresolved}"


@pytest.mark.asyncio
async def test_missing_settings_key_reports_unknown_not_silent_live() -> None:
    """缺键时必须显式 unknown 并阻塞升级判定，而非回退成 catalog 的预期 'live'。"""
    settings = SimpleNamespace()  # 什么都不给

    report = await KillSwitchReadinessService().get_readiness_report(settings)

    stage24 = report["stage24_policy"]
    assert stage24.current_mode == "unknown"
    assert stage24.ready_for_promotion is False
    assert stage24.blocking_reasons, "unknown 模式必须产生 blocking reason 提示运维"
    assert any("AURORA_POLICY_COMPILER_MODE" in reason for reason in stage24.blocking_reasons)
