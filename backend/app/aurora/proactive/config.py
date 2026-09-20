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
