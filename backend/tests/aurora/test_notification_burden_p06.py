"""P-06: 统一通知负担解析器（Notification Burden / Quiet / Low-stimulation 终局）。

三处散装开关（用户 quiet hours 在 NotificationPreferences 表、daily cap 在
explicit["daily_cap"]、低刺激在 A-07 aurora_stimulation_mode）收束到**一个
解析点** ``NotificationSettingsResolver``——它只消费既有真源（零新表零新键），
输出一个 ``EffectiveNotificationPolicy``，供 nudge/wake/pipeline 各出口一致消费。

断言面：
1. 缺省行为零漂移（平台基线 quiet + env cap + standard）；
2. 用户 quiet 窗口覆盖平台默认（服务端权威）；
3. 低刺激档默认更保守：quiet 窗口加宽（允许集 = 两窗交集语义）、cap 只在
   用户未显式设置时下调；
4. mute 语义复用 P-03 真源（勿重建）；
5. 读失败 fail-closed（宁可少发不可误发，与 P-01/W378-03 同哲学）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.suppression import in_quiet_window
from app.aurora.runtime_v1.notification_settings import (
    EffectiveNotificationPolicy,
    NotificationSettingsResolver,
    NotificationSettingsUnavailable,
    widen_quiet_window,
)
from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user_preferences import UserPreferencesCenter


@pytest.fixture(autouse=True)
def _no_platform_quiet_by_default(monkeypatch: pytest.MonkeyPatch):
    """平台基线 quiet 默认关（与 P-01 管线测试同一时钟无关性约定）；
    用户显式 quiet 窗口不依赖该旋钮，专属测试逐例注入。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)


def _utc(y: int, mo: int, d: int, h: int, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=UTC).replace(tzinfo=None)


async def _set_explicit(db_session, user_id, updates: dict) -> None:
    """get-or-create explicit 行并合并键（resolve 读路径会自动建行，须幂等）。"""
    from sqlalchemy import select

    row = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
    ).scalar_one_or_none()
    if row is None:
        row = UserPreferencesCenter(user_id=user_id, explicit=dict(updates))
    else:
        merged = dict(row.explicit or {})
        merged.update(updates)
        row.explicit = merged
    db_session.add(row)
    await db_session.commit()


# ── 纯函数：窗口加宽（低刺激 → 更保守） ────────────────────────────────────────


def test_widen_quiet_window_extends_both_ends():
    assert widen_quiet_window(("22:00", "08:00"), 60) == ("21:00", "09:00")


def test_widen_quiet_window_wraps_midnight():
    assert widen_quiet_window(("00:30", "06:00"), 60) == ("23:30", "07:00")


def test_in_quiet_window_public_helper_matches_suppression_semantics():
    # 22:00–08:00 Asia/Shanghai；13:30 UTC = 21:30 本地 → 窗外；15:30 UTC = 23:30 本地 → 窗内。
    assert in_quiet_window(_utc(2026, 9, 25, 13, 30), ("22:00", "08:00"), "Asia/Shanghai") is False
    assert in_quiet_window(_utc(2026, 9, 25, 15, 30), ("22:00", "08:00"), "Asia/Shanghai") is True


# ── resolve：缺省行为零漂移 + 服务端权威 ──────────────────────────────────────


async def test_resolver_defaults_keep_current_behavior(db_session, test_user) -> None:
    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)

    assert isinstance(policy, EffectiveNotificationPolicy)
    assert policy.stimulation_mode == "auto"
    assert policy.stimulation.level == "standard"
    assert policy.allow_proactive_push is True
    assert policy.proactive_suppress_hours == 24
    # 平台基线：旋钮关闭 → 无 quiet（与 P-01 现状一致，不凭空收紧）。
    assert policy.quiet_window is None
    assert policy.base_quiet_window is None
    # cap：用户未显式设置 → env 旋钮（3）。
    assert policy.daily_cap == 3
    assert policy.daily_cap_source == "default"


async def test_platform_default_quiet_follows_knob(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", True)
    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.quiet_window == ("22:00", "08:00")
    assert policy.quiet_source == "platform_default"


async def test_user_quiet_window_overrides_platform(db_session, test_user) -> None:
    db_session.add(
        NotificationPreferences(
            user_id=test_user.id,
            quiet_hours_enabled=True,
            quiet_hours_start="23:30",
            quiet_hours_end="07:30",
        )
    )
    await db_session.commit()

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.quiet_source == "user"
    assert policy.base_quiet_window == ("23:30", "07:30")
    assert policy.quiet_window == ("23:30", "07:30")
    # 窗口判定走用户时区/窗口：00:30 本地（16:30 UTC）在窗内。
    assert in_quiet_window(_utc(2026, 9, 25, 16, 30), policy.quiet_window, policy.timezone) is True


async def test_user_daily_cap_overrides_env_knob(db_session, test_user) -> None:
    await _set_explicit(db_session, test_user.id, {"daily_cap": 5})

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.daily_cap == 5
    assert policy.daily_cap_source == "user"


# ── 低刺激：默认更保守（quiet 交集语义 + cap 下调仅限未显式设置） ─────────────


async def test_low_stimulation_widens_user_quiet_window(db_session, test_user) -> None:
    db_session.add(
        NotificationPreferences(
            user_id=test_user.id,
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
    )
    await db_session.commit()

    standard = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    await _set_explicit(db_session, test_user.id, {"aurora_stimulation_mode": "low"})
    low = await NotificationSettingsResolver(db_session).resolve(test_user.id)

    # 交集语义：允许时刻 = 标准窗允许 ∩ 加宽窗允许；加宽窗 ⊇ 原窗。
    assert standard.quiet_window == ("22:00", "08:00")
    assert low.quiet_window == ("21:00", "09:00")

    # 21:30 本地（13:30 UTC）：标准档允许、低刺激档抑制。
    probe = _utc(2026, 9, 25, 13, 30)
    assert in_quiet_window(probe, standard.quiet_window, low.timezone) is False
    assert in_quiet_window(probe, low.quiet_window, low.timezone) is True
    # 08:30 本地（00:30 UTC）：标准档窗外、低刺激档抑制。
    probe2 = _utc(2026, 9, 25, 0, 30)
    assert in_quiet_window(probe2, standard.quiet_window, low.timezone) is False
    assert in_quiet_window(probe2, low.quiet_window, low.timezone) is True


async def test_low_stimulation_widens_platform_baseline_when_user_unset(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", True)
    await _set_explicit(db_session, test_user.id, {"aurora_stimulation_mode": "low"})

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    # 用户未开 quiet：生效窗 = 平台基线窗，低刺激档在其上加宽（交集语义）。
    assert policy.base_quiet_window == ("22:00", "08:00")
    assert policy.quiet_window == ("21:00", "09:00")
    assert policy.quiet_source == "platform_default"


async def test_low_stimulation_without_any_quiet_keeps_behavior(db_session, test_user, monkeypatch) -> None:
    """用户未开 quiet 且平台旋钮关闭 → 低刺激档不凭空造窗（时钟无关，零漂移）。"""
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    await _set_explicit(db_session, test_user.id, {"aurora_stimulation_mode": "low"})

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.base_quiet_window is None
    assert policy.quiet_window is None
    assert policy.quiet_source == "none"
    # cap 下调仍然生效（更保守的另一半）。
    assert policy.daily_cap == 2


async def test_low_stimulation_lowers_cap_only_when_user_unset(db_session, test_user) -> None:
    await _set_explicit(db_session, test_user.id, {"aurora_stimulation_mode": "low"})

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.daily_cap == 2, "用户未显式设置 cap 时，低刺激档默认更保守（3→2）"

    # 用户显式设置优先：显式 cap 不被低刺激档压低（A-07 显式覆盖原则）。
    await _set_explicit(db_session, test_user.id, {"daily_cap": 5})
    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.daily_cap == 5


async def test_low_stimulation_policy_carries_a07_budget(db_session, test_user) -> None:
    await _set_explicit(db_session, test_user.id, {"aurora_stimulation_mode": "low"})

    policy = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    assert policy.stimulation.level == "low"
    assert policy.allow_proactive_push is False
    assert policy.proactive_suppress_hours == 72


# ── evaluate_burden：quiet → cap 的确定性闸门 ─────────────────────────────────


async def test_evaluate_burden_suppresses_in_quiet_hours(db_session, test_user) -> None:
    db_session.add(
        NotificationPreferences(
            user_id=test_user.id,
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
    )
    await db_session.commit()

    decision = await NotificationSettingsResolver(db_session).evaluate_burden(
        test_user.id, now=_utc(2026, 9, 25, 15, 30)
    )  # 23:30 本地
    assert decision.allowed is False
    assert decision.reason == "quiet_hours"

    decision = await NotificationSettingsResolver(db_session).evaluate_burden(
        test_user.id, now=_utc(2026, 9, 25, 6, 0)
    )  # 14:00 本地
    assert decision.allowed is True
    assert decision.reason is None


async def test_evaluate_burden_enforces_daily_cap_from_notification_ledger(db_session, test_user) -> None:
    await _set_explicit(db_session, test_user.id, {"daily_cap": 2})
    resolver = NotificationSettingsResolver(db_session)
    now = _utc(2026, 9, 25, 6, 0)

    for i in range(2):
        decision = await resolver.evaluate_burden(test_user.id, now=now)
        assert decision.allowed is True, f"第 {i + 1} 条应放行"
        db_session.add(
            Notification(
                user_id=test_user.id,
                title="t",
                content="c",
                type="comeback_nudge",
                created_at=now,
            )
        )
        await db_session.commit()

    decision = await resolver.evaluate_burden(test_user.id, now=now)
    assert decision.allowed is False
    assert decision.reason == "daily_cap"
    assert decision.details["count"] == 2
    assert decision.details["cap"] == 2


async def test_daily_count_rolls_over_at_local_midnight(db_session, test_user) -> None:
    resolver = NotificationSettingsResolver(db_session)
    # 上海本地 9/25 的 23:59 与 9/26 的 00:01（UTC 15:59 / 16:01）。
    late = _utc(2026, 9, 25, 15, 59)
    early = _utc(2026, 9, 25, 16, 1)
    db_session.add(Notification(user_id=test_user.id, title="t", content="c", type="x", created_at=late))
    await db_session.commit()

    assert await resolver.daily_count(test_user.id, now=late) == 1
    assert await resolver.daily_count(test_user.id, now=early) == 0


# ── mute：复用 P-03 真源，勿重建 ──────────────────────────────────────────────


async def test_suggestion_suppressed_reuses_p03_truth(db_session, test_user) -> None:
    from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

    resolver = NotificationSettingsResolver(db_session)
    assert await resolver.suggestion_suppressed(test_user.id, "comeback_nudge") is None

    await ProactiveSuggestionFeedbackService(db_session).record_mute(test_user.id, "comeback_nudge")
    suppressed = await resolver.suggestion_suppressed(test_user.id, "comeback_nudge")
    assert suppressed is not None
    assert suppressed["reason"] == "muted"

    # 其他类型不受牵连（类型隔离，P-03 既有语义）。
    assert await resolver.suggestion_suppressed(test_user.id, "deadline_nudge") is None


# ── fail-closed：读失败宁可少发 ───────────────────────────────────────────────


async def test_resolver_fails_closed_on_db_error(db_session, test_user) -> None:
    class _Broken:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("db down")

    resolver = NotificationSettingsResolver(_Broken())  # type: ignore[arg-type]
    with pytest.raises(NotificationSettingsUnavailable):
        await resolver.resolve(test_user.id)
    with pytest.raises(NotificationSettingsUnavailable):
        await resolver.evaluate_burden(test_user.id)


# ── 新用户隔离：不串号 ────────────────────────────────────────────────────────


async def test_resolver_settings_are_per_user(db_session, test_user) -> None:
    other = uuid4()
    await _set_explicit(db_session, other, {"aurora_stimulation_mode": "low", "daily_cap": 1})

    mine = await NotificationSettingsResolver(db_session).resolve(test_user.id)
    theirs = await NotificationSettingsResolver(db_session).resolve(other)
    assert mine.stimulation_mode == "auto" and mine.daily_cap == 3
    assert theirs.stimulation_mode == "low" and theirs.daily_cap == 1


# ── P-01 事件管线接通统一设置（settings_provider hook） ───────────────────────


async def test_pipeline_consumes_unified_settings(db_session, test_user) -> None:
    """管线抑制链消费 per-user cap：第 cap+1 个事件同日被 daily_cap 抑制。"""
    from contextlib import asynccontextmanager

    from app.aurora.proactive.pipeline import ProactiveEventPipeline
    from app.aurora.runtime_v1.notification_settings import make_db_settings_provider

    await _set_explicit(db_session, test_user.id, {"daily_cap": 1})

    @asynccontextmanager
    async def _borrow_session():
        yield db_session

    def session_factory():
        return _borrow_session()

    pipeline = ProactiveEventPipeline(
        redis=_PipelineFakeRedis(),
        shadow=False,
        settings_provider=make_db_settings_provider(session_factory),
        deliver=_counting_deliver,
    )

    first = await pipeline.handle_event(
        {"event_type": "plan.health.alerted", "user_id": str(test_user.id), "plan_id": "p1"}
    )
    second = await pipeline.handle_event(
        {"event_type": "plan.health.alerted", "user_id": str(test_user.id), "plan_id": "p2"}
    )

    assert first is not None and first.decision == "notify"
    assert second is not None and second.decision == "suppressed"
    assert second.reason == "daily_cap"
    assert _DELIVERED_COUNT["n"] == 1


_DELIVERED_COUNT = {"n": 0}


async def _counting_deliver(user_id, classification, event_name) -> bool:
    _DELIVERED_COUNT["n"] += 1
    return True


class _PipelineFakeRedis:
    """管线状态 store 最小 fake（async get/set，语义同 tests 里既有 FakeRedis）。"""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.data[key] = value
        return True
