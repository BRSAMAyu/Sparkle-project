from __future__ import annotations

import pytest

from app.config import settings
from app.core.kill_switch import KillSwitchBinding, is_enabled_mode, is_live_mode, normalize_mode, resolve_settings_mode


def test_kill_switch_core_normalize_mode_accepts_legacy_aliases() -> None:
    assert normalize_mode(True) == "live"
    assert normalize_mode(False) == "off"
    assert normalize_mode("live_canary") == "live"


def test_kill_switch_core_enabled_and_live_helpers_match_tri_state() -> None:
    assert is_enabled_mode("shadow") is True
    assert is_enabled_mode("off") is False
    assert is_live_mode("live") is True
    assert is_live_mode("shadow") is False


def test_kill_switch_core_legacy_bool_backfills_default_mode(monkeypatch) -> None:
    """V3-FIX-21 后 legacy bool 的唯一合法面：仅在未声明 tri-state 设置时兜底。

    曾在此断言「settings_attr="off" + legacy True → live」的劫持语义即本卡修掉的
    缺陷（显式 off 被默认 True 的 legacy bool 静默劫持回 live）；判据唯一化后
    tri-state 设置在场时 legacy bool 不再参与解析。
    """
    binding = KillSwitchBinding(
        stage="18",
        feature="push_policy",
        redis_key="push_policy_mode",
        settings_attr=None,
        legacy_bool_attr="SPARKLE_PUSH_POLICY_ENABLED",
    )
    monkeypatch.setattr("app.core.kill_switch.settings.SPARKLE_PUSH_POLICY_ENABLED", True)
    assert resolve_settings_mode(binding) == "live"

    monkeypatch.setattr("app.core.kill_switch.settings.SPARKLE_PUSH_POLICY_ENABLED", False)
    assert resolve_settings_mode(binding) == "off"


def test_kill_switch_core_explicit_off_not_hijacked_by_legacy_bool(monkeypatch) -> None:
    """V3-FIX-21 红证：tri-state 设置在场即为唯一判据。

    显式 ``AURORA_STAGE18_AGGREGATOR_MODE="off"``（解析落在 fallback）不得被
    默认 True 的 legacy bool ``SPARKLE_AGGREGATOR_ENABLED`` 静默劫持回 "live"——
    否则真实部署下 governance_off 原因码不可达（FIX-09/F1 发现，R1 代码级核实）。
    """
    binding = KillSwitchBinding(
        stage="18",
        feature="aggregator",
        redis_key="aggregator_mode",
        settings_attr="AURORA_STAGE18_AGGREGATOR_MODE",
        legacy_bool_attr="SPARKLE_AGGREGATOR_ENABLED",
    )
    monkeypatch.setattr("app.core.kill_switch.settings.AURORA_STAGE18_AGGREGATOR_MODE", "off")
    # 显式钉回默认 True，实录劫持面（生产默认即触发）
    monkeypatch.setattr("app.core.kill_switch.settings.SPARKLE_AGGREGATOR_ENABLED", True)

    assert resolve_settings_mode(binding) == "off"


@pytest.mark.parametrize(
    ("module_name", "service_cls", "binding_key"),
    [
        ("app.services.aurora_stage18_kill_switch_service", "AuroraStage18KillSwitchService", "aggregator_enabled"),
        ("app.services.aurora_stage18_kill_switch_service", "AuroraStage18KillSwitchService", "push_policy_enabled"),
        ("app.services.aurora_stage18_kill_switch_service", "AuroraStage18KillSwitchService", "push_delivery_enabled"),
        ("app.services.aurora_stage19_kill_switch_service", "AuroraStage19KillSwitchService", "working_memory_enabled"),
        ("app.services.aurora_stage19_kill_switch_service", "AuroraStage19KillSwitchService", "llm_extractor_enabled"),
        ("app.services.aurora_stage19_kill_switch_service", "AuroraStage19KillSwitchService", "consolidation_enabled"),
        ("app.services.aurora_stage20_kill_switch_service", "AuroraStage20KillSwitchService", "sufficiency_judge"),
        ("app.services.aurora_stage20_kill_switch_service", "AuroraStage20KillSwitchService", "conflict_resolver"),
        ("app.services.aurora_stage21_kill_switch_service", "AuroraStage21KillSwitchService", "skill_store_enabled"),
        (
            "app.services.aurora_stage21_kill_switch_service",
            "AuroraStage21KillSwitchService",
            "skill_selection_enabled",
        ),
        ("app.services.aurora_stage21_kill_switch_service", "AuroraStage21KillSwitchService", "skill_share_enabled"),
    ],
)
def test_kill_switch_core_family_off_survives_legacy_bool_true(
    monkeypatch, module_name, service_cls, binding_key
) -> None:
    """V3-FIX-21 同族回归锁：全部 legacy_bool_attr 绑定下，显式 "off" + legacy bool
    强制 True 仍必须解析为 "off"（tri-state 设置在场时不被劫持/旁路）。"""
    import importlib

    binding = getattr(importlib.import_module(module_name), service_cls).BINDINGS[binding_key]
    assert binding.settings_attr is not None
    assert binding.legacy_bool_attr is not None

    monkeypatch.setattr(settings, binding.settings_attr, "off", raising=False)
    monkeypatch.setattr(settings, binding.legacy_bool_attr, True, raising=False)

    assert resolve_settings_mode(binding) == "off"
