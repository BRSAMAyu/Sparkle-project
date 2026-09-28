"""
Aurora proactive pipeline — tuning knobs (P-01).

管线自有旋钮：env 读取一次、默认值与仓库既有量级一致（wake_policy 的
cooldown/daily_limit、PushService 的 quiet hours 同族）。**不新增
``app/config/settings.py`` 字段**（本卡红线：settings 零改动、词表零改动）。

测试通过 monkeypatch 本模块属性覆盖旋钮（pydantic Settings 禁未知字段
setattr，因此不把旋钮挂到 settings 上）。
"""

from __future__ import annotations

import os

__all__ = [
    "PROACTIVE_PIPELINE_SHADOW",
    "PROACTIVE_QUIET_HOURS_ENABLED",
    "PROACTIVE_QUIET_START",
    "PROACTIVE_QUIET_END",
    "PROACTIVE_QUIET_TIMEZONE",
    "PROACTIVE_DAILY_CAP",
    "PROACTIVE_COOLDOWN_MINUTES",
    "PROACTIVE_REJECTION_THRESHOLD",
    "PROACTIVE_UNIFIED_BUDGET_ENABLED",
    "PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS",
]


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


#: shadow 模式总开关（默认开：would-notify 只记录不真发）。
PROACTIVE_PIPELINE_SHADOW = _flag("PROACTIVE_PIPELINE_SHADOW", True)

#: quiet hours（本地静默窗）默认启停与窗口。
PROACTIVE_QUIET_HOURS_ENABLED = _flag("PROACTIVE_QUIET_HOURS_ENABLED", True)
PROACTIVE_QUIET_START = os.getenv("PROACTIVE_QUIET_START", "22:00")
PROACTIVE_QUIET_END = os.getenv("PROACTIVE_QUIET_END", "08:00")
PROACTIVE_QUIET_TIMEZONE = os.getenv("PROACTIVE_QUIET_TIMEZONE", "Asia/Shanghai")

#: 每日上限 / 同类最小间隔（分钟）/ 拒绝窗内阈值。
PROACTIVE_DAILY_CAP = _int("PROACTIVE_DAILY_CAP", 3)
PROACTIVE_COOLDOWN_MINUTES = _int("PROACTIVE_COOLDOWN_MINUTES", 240)
PROACTIVE_REJECTION_THRESHOLD = _int("PROACTIVE_REJECTION_THRESHOLD", 2)

#: V4-P01 统一主动预算闸门（nudges/spine 渠道同一预算 + 跨渠道抑制）。
#: 默认开——闸门是**纯抑制面**（只减少发送、永不增加）。置 false =
#: passthrough 的**全关紧急开关**（一审 C-2a 如实口径）：nudge 渠道既有
#: 的内联 P-03/P-06 检查已被本闸门替代，off 态连这些既有保护一并失效
#: （静音用户可再被打扰），并非「恢复各渠道既有行为」；spine 渠道回到
#: 「仅自身 Redis 冷却」。审计面保留。
PROACTIVE_UNIFIED_BUDGET_ENABLED = _flag("PROACTIVE_UNIFIED_BUDGET_ENABLED", True)

#: 同一 prompt_key 的「一次 effect」去重窗（小时）。仅对带 subject 的提示
#: 生效（无 subject 的提示没有跨渠道同一性，节奏仍归各渠道既有冷却）。
PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS = _int("PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS", 24)
