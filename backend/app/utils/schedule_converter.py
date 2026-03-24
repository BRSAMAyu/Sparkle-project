"""
周日程表转换工具

将前端 168 格（7天×24小时）的周日程表数据转换为后端推送系统使用的活跃分钟列表。

前端格式（schedule_preferences.grid）:
- 168 个字符串元素，每个代表一个小时槽
- 索引 = hour * 7 + day_of_week (周一=0, 周日=6)
- 值: "busy"（忙碌，不推送）, "fragmented"（碎片时间，可推送）, "relax"（放松，可推送）

后端格式（active_hours）:
- 列表包含 0-1439 的分钟数（一天中的分钟）
- 当前时间对应的分钟数在此列表中则允许推送

作者: Claude Code
创建时间: 2026-03-16
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger


def weekly_grid_to_active_hours(
    grid: list[str],
    timezone: str = "Asia/Shanghai",
) -> list[int]:
    """
    将 168 格周日程表转换为当前时刻是否活跃的判断。

    注意：这个函数返回的是一个布尔值，表示"当前时刻"是否允许推送。
    由于推送系统使用的是分钟列表格式，我们需要返回当前小时对应的分钟范围。

    Args:
        grid: 168 个元素的列表，每个元素是 "busy"/"fragmented"/"relax"
        timezone: 用户时区

    Returns:
        包含当前允许推送的分钟数的列表（当前小时内允许推送的分钟）
    """
    if not grid or len(grid) != 168:
        logger.warning(f"Invalid grid length: {len(grid) if grid else 0}, expected 168")
        # 返回默认的活跃分钟（8:00-22:00）
        return list(range(480, 1321))

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")

    now = datetime.now(tz)

    # 计算当前是一周中的第几天和第几小时
    # Python weekday: 周一=0, 周日=6
    # 我们的前端格式: 周一=0, 周日=6 (与 Python 一致)
    current_dow = now.weekday()
    current_hour = now.hour

    # 计算在 168 格中的索引: hour * 7 + day_of_week
    index = current_hour * 7 + current_dow

    if index >= len(grid):
        logger.warning(f"Index {index} out of bounds for grid length {len(grid)}")
        return list(range(480, 1321))

    slot_status = grid[index]

    # 'fragmented' 和 'relax' 允许推送，'busy' 拒绝
    if slot_status in ("fragmented", "relax"):
        # 返回当前小时内的所有分钟
        start_minute = current_hour * 60
        return list(range(start_minute, start_minute + 60))
    else:
        # 当前是 busy 时间，返回空列表
        return []


def weekly_grid_to_full_active_hours(
    grid: list[str],
    timezone: str = "Asia/Shanghai",
) -> list[int]:
    """
    将完整的 168 格周日程表转换为今日所有活跃分钟列表。

    这个函数遍历今天的 24 个小时槽，返回所有允许推送的分钟。

    Args:
        grid: 168 个元素的列表
        timezone: 用户时区

    Returns:
        今日所有允许推送的分钟列表
    """
    if not grid or len(grid) != 168:
        logger.warning(f"Invalid grid length: {len(grid) if grid else 0}, expected 168")
        return list(range(480, 1321))

    active_minutes: list[int] = []

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")

    now = datetime.now(tz)
    current_dow = now.weekday()

    # 遍历今天的 24 个小时槽
    for hour in range(24):
        index = hour * 7 + current_dow
        if index < len(grid):
            slot_status = grid[index]
            if slot_status in ("fragmented", "relax"):
                start_minute = hour * 60
                active_minutes.extend(range(start_minute, start_minute + 60))

    return active_minutes


def weekly_grid_to_weekly_active_hours(
    grid: list[str],
    timezone: str = "Asia/Shanghai",
) -> list[int]:
    """
    将完整的 168 格周日程表转换为本周所有活跃分钟列表（基于当前时间）。

    这个函数返回当前时刻是否活跃。用于推送系统的实时判断。

    Args:
        grid: 168 个元素的列表
        timezone: 用户时区

    Returns:
        如果当前时刻允许推送，返回包含当前分钟的列表；否则返回空列表
    """
    if not grid or len(grid) != 168:
        logger.warning(f"Invalid grid length: {len(grid) if grid else 0}, expected 168")
        # 默认 8:00-22:00 允许
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        current_minute = now.hour * 60 + now.minute
        if 480 <= current_minute <= 1320:
            return [current_minute]
        return []

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")

    now = datetime.now(tz)
    current_dow = now.weekday()
    current_hour = now.hour
    current_minute = now.hour * 60 + now.minute

    index = current_hour * 7 + current_dow

    if index >= len(grid):
        return [current_minute] if 480 <= current_minute <= 1320 else []

    slot_status = grid[index]

    if slot_status in ("fragmented", "relax"):
        return [current_minute]
    else:
        return []


def is_currently_active(
    grid: list[str] | None,
    timezone: str = "Asia/Shanghai",
) -> bool:
    """
    简化接口：检查当前时刻是否允许推送。

    Args:
        grid: 168 个元素的列表，如果为 None 则使用默认行为
        timezone: 用户时区

    Returns:
        True 如果当前允许推送，False 否则
    """
    if grid is None or len(grid) != 168:
        # 默认行为：8:00-22:00 允许推送
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        current_minute = now.hour * 60 + now.minute
        return 480 <= current_minute <= 1320

    active = weekly_grid_to_weekly_active_hours(grid, timezone)
    return len(active) > 0


def parse_schedule_preferences(
    schedule_preferences: dict[str, Any] | None,
    timezone: str = "Asia/Shanghai",
) -> list[int]:
    """
    从 schedule_preferences 字典中解析并转换为活跃分钟列表。

    这是主要的入口函数，处理各种输入格式。

    Args:
        schedule_preferences: 用户的日程偏好设置，可能包含 'grid' 字段
        timezone: 用户时区

    Returns:
        当前允许推送的分钟列表
    """
    if not schedule_preferences:
        return list(range(480, 1321))  # 默认 8:00-22:00

    grid = schedule_preferences.get("grid")
    if grid and isinstance(grid, list):
        return weekly_grid_to_weekly_active_hours(grid, timezone)

    # 如果没有 grid，返回默认值
    return list(range(480, 1321))
