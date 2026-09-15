from __future__ import annotations

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
    binding = KillSwitchBinding(
        stage="18",
        feature="push_policy",
        redis_key="push_policy_mode",
        settings_attr="AURORA_STAGE18_PUSH_POLICY_MODE",
        legacy_bool_attr="SPARKLE_PUSH_POLICY_ENABLED",
    )
    monkeypatch.setattr("app.core.kill_switch.settings.AURORA_STAGE18_PUSH_POLICY_MODE", "off")
    monkeypatch.setattr("app.core.kill_switch.settings.SPARKLE_PUSH_POLICY_ENABLED", True)

    assert resolve_settings_mode(binding) == "live"
