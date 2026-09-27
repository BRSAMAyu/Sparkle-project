"""冲刺（exam sprint）day 数学的唯一权威语义 —— V3-FIX-326 裁决落地。

裁决（wt618，2026-09-27）：冲刺 day 数学族（dashboard ``_current_day_index``、
plans API ``_today_day_index``/``_derived_today_day``、daily task selection
``_plan_current_day``）统一为「**创建锚定的 UTC 日期脊柱**」读法：

1. 存储：``plan.created_at`` 是 naive-UTC（wt615 五环锚链 + wt618 live PG
   独立复核：JOURNEY 计划 7917e864 created 21:15:30.064186 == 驱动器
   ``run_id`` 秒级自戳 ``datetime.now(UTC)``）。V3-FIX-314 注释里
   「本地墙上钟存储」的论证被翻案，但其读法（``created_at.date()`` 直取）
   保留——直取的正是 UTC 日历日。
2. 脊柱：sprint day N 锚在「创建 UTC 日历日 + N - 1」。写入链与验收链
   都在 UTC 日期空间：
   - intake 用 ``datetime.now(UTC).date()`` 校验 exam_date 并按 UTC
     days_left 选 7 天包（``exam_sprint_intake_service._today``）；
   - JOURNEY 驱动器 ``exam_date = datetime.now(UTC).date() + 7 天``
     （real_drive.py:1151），CP-04 日门 = 严格递增的驱动器 UTC 日
     （real_drive.py:1858-1865，``day{N}_run_date`` 同为 UTC 日）；
   - ``target_date == exam_date`` 原样透传（日界值，无时刻成分）。
   因此 day:N 模板与 target_date 只在 UTC 日期空间自洽：JOURNEY 计划
   created 09-22 21:15Z + target 09-29 = 7 天脊柱；换算到上海本地日框架
   会得 6 天，与模板自相矛盾——该换算即 day6 门 ``/tasks/today=[]`` 病征
   与 day7 门必失败的根源，裁决予以排除。
3. today：调用方传入用户本地日（V3-FIX-221/233 契约）。上海用户
   08:00–24:00 本地日 == UTC 日（JOURNEY 全部门在 08:00+ 窗跑），公式
   在该窗内与脊柱逐位一致；本地 00:00–08:00 消费窗内，UTC 16–24 点创建
   的计划（live 库 128/975 = 13.1%）读数比本地日框架提前一天——这是
   脊柱 UTC 锚定的既定约定边界（夜间窗提前泄入 = 脊柱按自身钟推进），
   不是 defect；任务侧本地日契约（due_date/completed_at/undated created
   锚、连胜 293 族）不属本族、不受影响、保持不动。

若未来产品裁定冲刺脊柱也吃本地日契约，代价是 day7 式门需驱动器侧
显式供 today 的替代机制——该分支被 V3-FIX-326 明确否决。
"""

from __future__ import annotations

from datetime import date, datetime


def sprint_spine_days(target_date: date | None, created_at: date | datetime | None) -> int | None:
    """冲刺脊柱长度 = ``target_date - created_at 的 UTC 日历日``（天）。

    ``created_at`` 是 naive-UTC 存储列，``.date()`` 直取 UTC 日历日（不按
    用户时区换算——见模块 docstring 第 2 条）。``target_date`` 是日界值
    原样透传。输入缺失或脊柱非正（target 未晚于创建 UTC 日）→ ``None``。
    """
    if target_date is None or created_at is None:
        return None
    created_day = created_at.date() if isinstance(created_at, datetime) else created_at
    spine_days = (target_date - created_day).days
    return spine_days if spine_days > 0 else None


def sprint_days_remaining(target_date: date, today: date) -> int:
    """距考试日剩余天数，下限 0（过期日之后按 0 计，不回负）。"""
    return max((target_date - today).days, 0)


def sprint_current_day(target_date: date | None, created_at: date | datetime | None, today: date) -> int | None:
    """冲刺当前推进到 1-based 第几天；脊柱不可知时 ``None``。

    ``current = spine - days_remaining + 1``，下限 1；**不设上限截断**——
    超期后按日历继续外推是 plans API ``_derived_today_day`` 的文档化意图
    （超期回归者推到日程之外由 highlight 降级接管），dashboard/plans API
    的 ``max_task_day`` 截断在各面上自行叠加。
    """
    if target_date is None:
        return None
    spine_days = sprint_spine_days(target_date, created_at)
    if spine_days is None:
        return None
    return max(spine_days - sprint_days_remaining(target_date, today) + 1, 1)
