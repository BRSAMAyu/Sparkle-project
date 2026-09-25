from __future__ import annotations

from app.aurora.runtime_v1.stimulation_policy import (
    LOW_STIMULATION_NUDGE_SUPPRESS_HOURS,
    DEFAULT_NUDGE_SUPPRESS_HOURS,
    STIMULATION_LOW,
    STIMULATION_STANDARD,
    apply_policy_to_nudge,
    resolve_stimulation_policy,
)
from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService


# ── explicit setting overrides everything (both directions) ───────────────────


def test_explicit_low_mode_attenuates_proactive_surface():
    policy = resolve_stimulation_policy("low")

    assert policy.level == STIMULATION_LOW
    # 主动建议频率衰减：不主动推送 + 重复抑制窗口拉长。
    assert policy.allow_proactive_push is False
    assert policy.proactive_suppress_hours == LOW_STIMULATION_NUDGE_SUPPRESS_HOURS
    assert policy.quiet_title is True
    assert policy.payload_tag == STIMULATION_LOW


def test_explicit_standard_mode_overrides_any_auto_judgement():
    # 显式 standard = 永不衰减：即使未来接入偏高信号也不得降档。
    policy = resolve_stimulation_policy("standard")

    assert policy.level == STIMULATION_STANDARD
    assert policy.allow_proactive_push is True
    assert policy.proactive_suppress_hours == DEFAULT_NUDGE_SUPPRESS_HOURS
    assert policy.quiet_title is False


def test_auto_mode_keeps_current_behavior():
    # auto（默认档）当前无引擎侧信号源 → standard，行为与历史完全一致。
    for raw in (None, "", "auto"):
        policy = resolve_stimulation_policy(raw)
        assert policy.level == STIMULATION_STANDARD
        assert policy.allow_proactive_push is True

    # 大小写/空白容错。
    assert resolve_stimulation_policy(" LOW ").level == STIMULATION_LOW
    assert resolve_stimulation_policy("Standard").level == STIMULATION_STANDARD


def test_unknown_mode_falls_back_to_standard():
    assert resolve_stimulation_policy("mystery").level == STIMULATION_STANDARD


# ── nudge copy transform: no diagnosis, factual quiet title ──────────────────


def test_low_stimulation_quiets_nudge_title_only():
    title, content = apply_policy_to_nudge(
        resolve_stimulation_policy("low"),
        title="好久不见，我一直在等你",
        content="你已经 6 天没来了，我保留着上次的进度。",
    )
    # 去敦促/等待压力，改中性事实性表述；正文保持引擎事实性消息。
    assert title == "你的学习计划状态"
    assert content == "你已经 6 天没来了，我保留着上次的进度。"


def test_standard_stimulation_keeps_nudge_copy_unchanged():
    title, content = apply_policy_to_nudge(
        resolve_stimulation_policy("standard"),
        title="好久不见，我一直在等你",
        content="正文不动",
    )
    assert title == "好久不见，我一直在等你"
    assert content == "正文不动"


# ── preference persistence (explicit channel) ─────────────────────────────────


async def test_stimulation_mode_persists_via_preferences_service(db_session):
    from uuid import uuid4

    from app.models.user import User

    user = User(
        id=uuid4(),
        username=f"stim_{uuid4().hex[:8]}",
        email=f"stim_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    service = AuroraUserPreferencesService(db_session)

    defaults = await service.get(user.id)
    assert defaults["aurora_stimulation_mode"] == "auto"

    updated = await service.update(
        user.id, {"aurora_stimulation_mode": "low"}
    )
    assert updated["aurora_stimulation_mode"] == "low"
    assert (await service.get(user.id))["aurora_stimulation_mode"] == "low"

    # 非法值被拒绝，保持既有值（显式设置不允许被静默改写为未知档）。
    invalid = await service.update(
        user.id, {"aurora_stimulation_mode": "diagnose_me"}
    )
    assert invalid["aurora_stimulation_mode"] == "low"
