"""
Aurora proactive pipeline — deterministic suppression chain (P-01).

确定性**抑制链**（PROACTIVE_SYSTEM.md §3 Suppression 的确定性子集）：

    state_unavailable → quiet_hours → mute → daily_cap → cooldown
      → recent_rejection → novelty

其中 ``state_unavailable`` 是 fail-closed 总闸（R2 P1-1）：抑制状态读不到
时整条链全抑制——宁可少发不可误发。

硬约束（本卡灵魂）：
- **零 LLM**：本模块及其调用方在抑制判定路径上没有任何模型调用；全部判定
  是对 ``SuppressionSnapshot``（由调用方注入的状态快照）的纯函数运算。
- **确定性**：同一 (trigger, subject, snapshot) 输入永远得到同一裁决。
- **可审计**：每个否决都带稳定的 ``reason``（与 metrics label 同名）与
  命中的 ``step``，首个命中即短路（顺序固定，见 ``SUPPRESSION_STEPS``）。

I/O（Redis/DB 读取）发生在 :mod:`app.aurora.proactive.state` 的快照构建里，
不在本模块——因此抑制逻辑可以脱离基础设施单独穷举测试。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.aurora.proactive.triggers import ProactiveTrigger

__all__ = [
    "SuppressionSnapshot",
    "SuppressionDecision",
    "evaluate_suppression",
    "SUPPRESSION_STEPS",
    "DEFAULT_DAILY_CAP",
    "DEFAULT_COOLDOWN_MINUTES",
    "DEFAULT_QUIET_START",
    "DEFAULT_QUIET_END",
    "DEFAULT_REJECTION_THRESHOLD",
    "REJECTION_WINDOW_DAYS",
    "NOVELTY_TTL",
]


# --- Tunables（与 wake_policy / PushService 既有量级一致；纯常量） -----------

DEFAULT_DAILY_CAP = 3
DEFAULT_COOLDOWN_MINUTES = 240
DEFAULT_QUIET_START = "22:00"
DEFAULT_QUIET_END = "08:00"
DEFAULT_REJECTION_THRESHOLD = 2
REJECTION_WINDOW_DAYS = 14
NOVELTY_TTL = timedelta(hours=48)

#: 固定短路顺序（metrics reason 与 step 同名，审计直读）。
#: ``state_unavailable`` 永远排第一：抑制状态读不到（Redis 故障/未配置）时
#: **宁可少发不可误发**——按全抑制处理（R2 P1-1 fail-closed 契约）。
SUPPRESSION_STEPS: tuple[str, ...] = (
    "state_unavailable",
    "quiet_hours",
    "mute",
    "daily_cap",
    "cooldown",
    "recent_rejection",
    "novelty",
)


@dataclass(frozen=True, slots=True)
class SuppressionSnapshot:
    """抑制链的输入状态快照（由 state 层构建，或测试直接构造）。

    所有计数字段都已由 state 层做过窗口修剪（日界滚动 / 14d 拒绝窗 /
    48h 新颖性 TTL）——本纯函数不做任何 I/O 与时间窗计算之外的逻辑。
    """

    #: naive-UTC 判定时刻。
    now: datetime
    #: 抑制状态不可用（store 读失败 / Redis 未配置）——fail-closed 总闸：
    #: 置 True 时整条链直接全抑制，reason=state_unavailable（R2 P1-1）。
    state_unavailable: bool = False
    #: quiet hours 本地窗口 ("HH:MM", "HH:MM")；``None`` = 未启用。
    quiet_window: tuple[str, str] | None = (DEFAULT_QUIET_START, DEFAULT_QUIET_END)
    #: IANA 时区名（quiet hours 的本地化判定）；无效名回退 UTC。
    timezone: str = "Asia/Shanghai"
    #: Aurora control-surface 级"主动触达"总闸（proactive_follow_up disabled）。
    proactive_action_disabled: bool = False
    #: 用户显式 mute 的 trigger 名集合（如 {"deadline"}）。
    muted_triggers: frozenset[str] = frozenset()
    #: 今日（用户本地日）已通知数。
    daily_count: int = 0
    daily_cap: int = DEFAULT_DAILY_CAP
    #: 同 trigger 上次通知时刻（naive-UTC）；缺 trigger = 从未通知。
    last_notify_at: Mapping[str, datetime] = field(default_factory=dict)
    #: 同 trigger 最小间隔（分钟）。
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES
    #: 拒绝窗内（14d）各 trigger 被用户拒绝/负反馈次数。
    recent_rejections: Mapping[str, int] = field(default_factory=dict)
    #: 超过该次数即抑制该 trigger。
    rejection_threshold: int = DEFAULT_REJECTION_THRESHOLD
    #: 新颖性窗口内已通知过的 "(trigger):(subject)" 集合。
    seen_subject_keys: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class SuppressionDecision:
    """一步裁决：允许或被第几个抑制器以何原因短路。"""

    allowed: bool
    #: 否决原因（与 SUPPRESSION_STEPS 同名）；允许时为 None。
    reason: str | None = None
    #: 命中的抑制步骤名；允许时为 None。
    step: str | None = None
    #: 供审计的细节（如剩余秒数/当前计数），不含用户内容。
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def suppressed(self) -> bool:
        return not self.allowed


def _local_minutes(now: datetime, timezone_name: str) -> tuple[int, str]:
    """把 naive-UTC 时刻换算到本地日的分钟数；无效时区回退 UTC（确定性）。"""
    effective_tz = timezone_name
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        tz = ZoneInfo("UTC")
        effective_tz = "UTC"
    local = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return local.hour * 60 + local.minute, effective_tz


def _minutes_of(hhmm: str) -> int | None:
    parts = str(hhmm or "").split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def in_quiet_window(now: datetime, window: tuple[str, str], timezone_name: str) -> bool:
    """quiet 窗口判定（公开助手；P-06 统一设置解析复用同一实现）。"""
    current, _ = _local_minutes(now, timezone_name)
    start = _minutes_of(window[0])
    end = _minutes_of(window[1])
    if start is None or end is None:
        return False
    if start <= end:
        return start <= current <= end
    # 跨午夜窗口（22:00–08:00）。
    return current >= start or current <= end


# 兼容别名：既有内部调用点保持不变。
_in_quiet_window = in_quiet_window


def _cooldown_remaining(now: datetime, last: datetime | None, cooldown_minutes: int) -> int:
    if last is None or cooldown_minutes <= 0:
        return 0
    if last.tzinfo is not None:
        from datetime import UTC

        last = last.astimezone(UTC).replace(tzinfo=None)
    remaining = int(((last + timedelta(minutes=cooldown_minutes)) - now).total_seconds())
    return max(0, remaining)


def evaluate_suppression(
    *,
    trigger: ProactiveTrigger,
    subject_key: str,
    snapshot: SuppressionSnapshot,
) -> SuppressionDecision:
    """确定性抑制链。首个命中即短路返回；全通过返回 allowed。"""
    trigger_name = str(trigger.value)

    # 0. state unavailable —— 抑制状态读不到：fail-closed 全抑制（宁可少发
    #    不可误发；与 pipeline 侧「抑制而非误发」注释对齐）。
    if snapshot.state_unavailable:
        return SuppressionDecision(False, "state_unavailable", "state_unavailable")

    # 1. quiet hours —— 本地静默窗内一律不触达。
    if snapshot.quiet_window is not None and _in_quiet_window(
        snapshot.now, snapshot.quiet_window, snapshot.timezone
    ):
        return SuppressionDecision(False, "quiet_hours", "quiet_hours")

    # 2. mute —— control-surface 总闸或 trigger 级显式静音。
    if snapshot.proactive_action_disabled:
        return SuppressionDecision(False, "mute", "mute", {"mute_scope": "proactive_follow_up"})
    if trigger_name in snapshot.muted_triggers:
        return SuppressionDecision(False, "mute", "mute", {"mute_scope": trigger_name})

    # 3. daily cap —— 用户本地日计数达到上限。
    if snapshot.daily_cap > 0 and snapshot.daily_count >= snapshot.daily_cap:
        return SuppressionDecision(
            False, "daily_cap", "daily_cap", {"count": snapshot.daily_count, "cap": snapshot.daily_cap}
        )

    # 4. cooldown —— 同 trigger 最小通知间隔。
    remaining = _cooldown_remaining(
        snapshot.now, snapshot.last_notify_at.get(trigger_name), snapshot.cooldown_minutes
    )
    if remaining > 0:
        return SuppressionDecision(
            False, "cooldown", "cooldown", {"remaining_seconds": remaining, "trigger": trigger_name}
        )

    # 5. recent rejection —— 拒绝窗内该 trigger 负反馈达到阈值即降频为 0。
    if snapshot.rejection_threshold > 0:
        rejections = int(snapshot.recent_rejections.get(trigger_name) or 0)
        if rejections >= snapshot.rejection_threshold:
            return SuppressionDecision(
                False,
                "recent_rejection",
                "recent_rejection",
                {"rejections": rejections, "threshold": snapshot.rejection_threshold, "trigger": trigger_name},
            )

    # 6. novelty —— 同 (trigger, subject) 在新颖性窗口内已提醒过。
    if subject_key:
        dedup_key = f"{trigger_name}:{subject_key}"
        if dedup_key in snapshot.seen_subject_keys:
            return SuppressionDecision(False, "novelty", "novelty", {"dedup_key": dedup_key})

    return SuppressionDecision(True)
