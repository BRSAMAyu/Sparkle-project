"""
Aurora proactive pipeline — deterministic event classifier (P-01).

把 Sparkle V3 的主动式触发做成 **event → filter → Aurora**，而不是定时轮询
问 LLM（PROACTIVE_SYSTEM.md §2 Trigger Pipeline）。本模块是管线的第一段：

1. **ProactiveTrigger** — PROACTIVE_SYSTEM.md 冻结的七类触发
   （deadline / overdue / slot missed / user active / upstream completed /
   goal stalled / run awaiting）。
2. **白名单分类器** — ``classify_event`` 是纯函数：输入一条 EventBus 事件
   dict（``event_type`` + 载荷），输出至多一个触发分类。白名单里的每个事件
   名在仓内都有真实 producer（R2 F4 审计后：两个死名 ``chat.message.sent``
   （全仓无发出点）与 ``task.status_changed``（registry ``producers=()``，
   observed_unregistered）已移出白名单），**零新事件名**；
   ``app/core/event_registry.py`` 零改动。
3. 白名单之外的事件一律忽略（返回 ``None``）——主动式管线不消费未登记的
   事件形状，也绝不发明事件名。

**可达性登记（R2 P1-2，如实申报）**——本管线订阅 Python 侧
``sparkle_events`` stream，按「该事件名是否会到达本流」分两档：

- **reachable（本流可达）**：``task.started`` / ``task.completed`` /
  ``task.abandoned``（task_service 发布）、``focus.session.completed``
  （focus_service）、``plan.health.alerted``（plan_health_signal_service）、
  ``run.status_changed``（execution_run_producer，仅 EXECUTING 步进，分类器
  显式忽略）。
- **reachable-via-bridge（producer 真实、暂不经本流）**：
  ``task.created`` / ``galaxy.study.recorded``（gateway 产，走
  ``cqrs:stream:*``）、``run.awaiting_user``（agent_run_service 写
  ``event_outbox`` → 网关 RabbitMQ exchange；Python stream 无发布点）。
  分类器按词表形状兼容预留，等 outbox→Redis 桥（follow-up 卡）落地即生效。

分类是**载荷驱动且确定性**的：同一事件输入永远得到同一分类，全程零 I/O、
零 LLM。任何"是否值得提醒"的判断都不在本模块发生（那是抑制链与下游
Aurora 决策的事）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Mapping

__all__ = [
    "ProactiveTrigger",
    "TriggerClassification",
    "classify_event",
    "WHITELISTED_EVENT_NAMES",
    "DEADLINE_SOON_WINDOW",
]


class ProactiveTrigger(StrEnum):
    """PROACTIVE_SYSTEM.md §2 的七类触发（v3/02_core_systems 冻结表述）。"""

    DEADLINE = "deadline"  # deadline approaching
    OVERDUE = "overdue"  # task overdue
    SLOT_MISSED = "slot_missed"  # planned slot missed
    USER_ACTIVE = "user_active"  # user active
    UPSTREAM_COMPLETED = "upstream_completed"  # upstream completed
    GOAL_STALLED = "goal_stalled"  # goal stalled
    RUN_AWAITING = "run_awaiting"  # run awaiting user


#: deadline "approaching" 窗口（日期粒度）：Task.due_date 是 Date 列，序列化
#: 进载荷的 ``due_at`` 为日期级 ISO 串——due 日落在 [今日, 今日+2日] 内算
#: "临近"。纯分类参数（无 I/O），测试可直接钉住。
DEADLINE_SOON_DAYS = 2


@dataclass(frozen=True, slots=True)
class TriggerClassification:
    """一条事件被分类出的触发（含新颖性去重键与 correlation 线索）。"""

    trigger: ProactiveTrigger
    #: 新颖性去重键（同用户 + 同 trigger + 同 subject 只提醒一次）。
    #: 取事件里最具体的因果对象 id（task/plan/run/session），缺失时为 ""。
    subject_key: str
    #: 供决策记录 / metrics 使用的线索字段（全部来自载荷，不新造）。
    correlation: Mapping[str, str]


def _clean_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _parse_datetime(value: Any) -> datetime | None:
    """naive-UTC 解析（DB 惯例，与 event_registry.normalize_occurred_at 一致）。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = _clean_str(value)
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is not None:
        from datetime import UTC

        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _run_to_status(payload: Mapping[str, Any]) -> str:
    """``run.status_changed`` 的 schema 扩展落点（execution_run_producer 约定：
    ``payload["run"]["to_status"]``；扁平 ``to_status`` 兼容）。"""
    run_block = payload.get("run")
    if isinstance(run_block, Mapping):
        return _clean_str(run_block.get("to_status")).upper()
    return _clean_str(payload.get("to_status")).upper()


def _due_date_of(payload: Mapping[str, Any]) -> date | None:
    """提取载荷的到期日（date 粒度）。兼容 datetime ISO 串与纯 date 串。"""
    for key in ("due_at", "deadline_at", "deadline"):
        raw = payload.get(key)
        if isinstance(raw, date) and not isinstance(raw, datetime):
            return raw
        parsed = _parse_datetime(raw)
        if parsed is not None:
            return parsed.date()
    return None


def _subject(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = _clean_str(payload.get(key))
        if text:
            return text
    return ""


def _classify_by_name(event_name: str, payload: Mapping[str, Any], now: datetime) -> TriggerClassification | None:
    """白名单映射表。每个名字的 producer 见模块 docstring 与 REPORT。"""

    if event_name == "task.started":
        # task_service.publish("task.started")（due_at 序列化自 Task.due_date，
        # 日期粒度）。带且临期 → deadline，否则视为用户活跃。
        due = _due_date_of(payload)
        if due is not None and now.date() <= due <= now.date() + timedelta(days=DEADLINE_SOON_DAYS):
            return TriggerClassification(
                ProactiveTrigger.DEADLINE,
                _subject(payload, "task_id", "task"),
                {"task_id": _subject(payload, "task_id")},
            )
        return TriggerClassification(
            ProactiveTrigger.USER_ACTIVE,
            _subject(payload, "task_id", "task"),
            {"task_id": _subject(payload, "task_id")},
        )

    if event_name == "task.created":
        # gateway EventTaskCreated（cqrs:stream:task，本流暂不经桥）；仅当载荷
        # 声明了临期到期日才是 deadline 触发（新建任务本身不是提醒理由）。
        due = _due_date_of(payload)
        if due is not None and now.date() <= due <= now.date() + timedelta(days=DEADLINE_SOON_DAYS):
            return TriggerClassification(
                ProactiveTrigger.DEADLINE,
                _subject(payload, "task_id", "task"),
                {"task_id": _subject(payload, "task_id")},
            )
        return None

    if event_name == "task.abandoned":
        # 到期日已过（日期粒度）的放弃 → overdue；其余放弃 → goal_stalled
        # （bus 上最接近"目标停滞"的确定性事实；plan 健康走 plan.health.alerted）。
        due = _due_date_of(payload)
        task_id = _subject(payload, "task_id", "task")
        if due is not None and due < now.date():
            return TriggerClassification(ProactiveTrigger.OVERDUE, task_id, {"task_id": task_id})
        return TriggerClassification(ProactiveTrigger.GOAL_STALLED, task_id, {"task_id": task_id})

    if event_name == "task.status_changed":
        # R2 F4：registry 自记 producers=()（observed_unregistered，仓内无
        # producer，唯一引用是 CommandEffects 的 kind 字符串）——死名，已移出
        # 白名单，永不消费（防御分支保留以明示语义）。
        return None

    if event_name == "focus.session.completed":
        # focus_service：completed=False 即计划时段未完成 → slot missed；
        # 正常完成是用户活跃。
        completed = payload.get("completed")
        session_id = _subject(payload, "session_id", "session")
        if completed is False:
            return TriggerClassification(ProactiveTrigger.SLOT_MISSED, session_id, {"session_id": session_id})
        if completed is True:
            return TriggerClassification(
                ProactiveTrigger.USER_ACTIVE,
                session_id,
                {"session_id": session_id, "task_id": _subject(payload, "task_id")},
            )
        return None

    if event_name == "plan.health.alerted":
        # plan_health_signal_service：计划健康告警 → goal stalled 的直接事实。
        plan_id = _subject(payload, "plan_id", "plan")
        return TriggerClassification(ProactiveTrigger.GOAL_STALLED, plan_id, {"plan_id": plan_id})

    if event_name == "task.completed":
        task_id = _subject(payload, "task_id", "task")
        return TriggerClassification(ProactiveTrigger.UPSTREAM_COMPLETED, task_id, {"task_id": task_id})

    if event_name == "run.status_changed":
        to_status = _run_to_status(payload)
        run_id = _subject(payload, "run_id", "execution_intent_id")
        if to_status in _AWAITING_STATUSES:
            return TriggerClassification(ProactiveTrigger.RUN_AWAITING, run_id, {"run_id": run_id})
        if to_status in {"SUCCEEDED"}:
            return TriggerClassification(ProactiveTrigger.UPSTREAM_COMPLETED, run_id, {"run_id": run_id})
        # 步进/排队/失败迁移不是主动式触发（EXECUTING 步进高频，绝不能提醒）。
        return None

    if event_name == "run.awaiting_user":
        run_id = _subject(payload, "run_id", "execution_intent_id")
        return TriggerClassification(ProactiveTrigger.RUN_AWAITING, run_id, {"run_id": run_id})

    if event_name == "galaxy.study.recorded":
        # gateway 产出的用户活跃事实（cqrs:stream:galaxy；本流暂不经桥，
        # reachable-via-bridge 档）。
        return TriggerClassification(ProactiveTrigger.USER_ACTIVE, "", {})

    return None


_AWAITING_STATUSES = frozenset({"AWAITING_USER", "AWAITING_APPROVAL"})


def classify_event(event: Mapping[str, Any], *, now: datetime | None = None) -> TriggerClassification | None:
    """把一条 EventBus 事件确定性分类为至多一个主动式触发。

    Args:
        event: 事件 dict（至少含 ``event_type``；载荷字段平铺在 dict 上，
            与 ``EventBus._process_stream_message`` 解析后的形状一致）。
        now: naive-UTC 参考时刻（deadline/overdue 判定用）；缺省当前时刻。

    Returns:
        ``TriggerClassification`` 或 ``None``（白名单之外 / 非触发形状）。
    """
    event_name = _clean_str(event.get("event_type"))
    if not event_name or event_name not in WHITELISTED_EVENT_NAMES:
        return None
    if now is None:
        from datetime import UTC

        now = datetime.now(UTC).replace(tzinfo=None)
    elif now.tzinfo is not None:
        from datetime import UTC

        now = now.astimezone(UTC).replace(tzinfo=None)
    return _classify_by_name(event_name, event, now)


def _build_whitelist() -> frozenset[str]:
    """白名单 = 39 冻结词表 ∩ 有真实 producer 的主动式相关名 ∪ 既有旧名。

    R2 F4/P2 审计后（逐个 grep 发出点）：
    - 移除死名 ``chat.message.sent``（Go 仅类型定义，全仓无发出点）与
      ``task.status_changed``（registry ``producers=()``、
      observed_unregistered）——见模块 docstring 可达性登记。
    - 保留 producer 真实但暂不经本流的名字（``task.created`` /
      ``galaxy.study.recorded`` / ``run.awaiting_user``，reachable-via-bridge）。
    本函数在 import 期执行一次，纯内存。
    """
    registry_names = {
        # 39 冻结词表内、被本管线消费的名字（零扩展）。字面量直写以保持本
        # 模块 stdlib-only、无 registry 导入环；契约测试钉死词表，若词表
        # 变更此处需同步（消费方不扩展词表）。
        "task.created",
        "task.started",
        "task.completed",
        "task.abandoned",
        "run.status_changed",
        "run.awaiting_user",
        "galaxy.study.recorded",
        # 既有 sparkle_events 旧名（非 39 词表、但仓内已有 producer 与
        # 消费者先例；属于"既有事件流"，不新造）。
        "focus.session.completed",
        "plan.health.alerted",
    }
    return frozenset(registry_names)


WHITELISTED_EVENT_NAMES: frozenset[str] = _build_whitelist()
