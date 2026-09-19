"""X-05B · EXECUTING 执行面 producer 钩子（execution 轨道步进 → run 事件）.

X-05 合入时 EXECUTING 态骨架完整（状态机边、投影、API 全在），但 execution
轨道没有步进 producer——OpenClaw 执行步进（启动/用工具/产出/收尾）只进
task monitor，不进 EventBus，用户在 agent_runs 上看不到执行进度（双验收裁
ACCEPT 的裁剪项，FIX-28）。本模块补上这根线：

- **零新事件名**：只复用 D-01 冻结词表的 ``run.status_changed``（与
  execution.status_changed 同一漏斗协议——flat payload + event_type 键，
  EventBus 既有 publish 路径）。schema 扩展字段（``milestone`` / ``run``
  块）允许，事件名不扩；
- **最小侵入**：独立函数 :func:`publish_execution_step_event`，永不抛出
  （可见性发布不得削弱 execution_service 既有守卫/执行链），调用点只有
  ``execution_service._handle_gateway_stream_event`` 的四个步进分支；
- **幂等**：正确性锚在消费侧（X-05 投影幂等语义——同 intent+attempt+step
  重投恰一次：transition 的 FOR UPDATE+复查吸收重复 to_status，
  record_step 的绝对序号单调吸收重复 step）。本模块的进程内 once-set 只是
  **流量消减器**（tool/assistant 流每帧都会触发回调，不消减会逐帧刷总线），
  进程重启后重复发布由消费侧幂等吸收，非正确性机制；
- **步进词表封闭**：里程碑 → 绝对序号（UI「正在执行 2/4」）：
  ``execution_started=1 / tool_in_use=2 / producing_output=3 / finishing=4``。
  终态不在此发（终态归 intent 状态漏斗 execution.status_changed，单一真源）。

消费侧：``run_projection_consumer.RunProjectionConsumer``（同组消费
``run.status_changed`` → ``AgentRunService.project_execution_step``）。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.core.event_bus import event_bus
from app.core.run_state_machine import RunEventName, RunStatus

if TYPE_CHECKING:  # 仅类型引用，避免运行时服务层互依
    from app.models.execution_intent import ExecutionIntent

__all__ = [
    "RUN_EVENT_STREAM",
    "EXECUTION_MILESTONE_STEPS",
    "EXECUTION_MILESTONE_STEPS_TOTAL",
    "EXECUTION_MILESTONE_STAGES",
    "publish_execution_step_event",
]

#: run 步进事件的发布流（与 execution.status_changed 同流同协议）。
RUN_EVENT_STREAM = "sparkle_events"

#: 步进里程碑 → 绝对序号（封闭词表；扩词需同步消费侧 UI 语义与 steps_total）。
EXECUTION_MILESTONE_STEPS: dict[str, int] = {
    "execution_started": 1,
    "tool_in_use": 2,
    "producing_output": 3,
    "finishing": 4,
}

#: 里程碑 → current_stage 标签（run.current_stage 上限 64 字符）。
EXECUTION_MILESTONE_STAGES: dict[str, str] = {
    "execution_started": "openclaw_start",
    "tool_in_use": "openclaw_tool",
    "producing_output": "openclaw_output",
    "finishing": "openclaw_finish",
}

EXECUTION_MILESTONE_STEPS_TOTAL = len(EXECUTION_MILESTONE_STEPS)

#: 进程内 once-set 的 TTL / 容量上限（intent 默认 timeout 300s，取 30 分钟
#: 覆盖长任务；超量先扫过期再整体让位——防长活进程无界增长）。
_DEDUP_TTL_SECONDS = 30 * 60
_DEDUP_MAX_ENTRIES = 8192

_recently_published: dict[tuple[str, str], float] = {}


def _utcnow_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _should_publish(intent_key: str, milestone: str) -> bool:
    """进程内 once-set（流量消减，非正确性机制；见模块 docstring）。"""
    now = time.monotonic()
    key = (intent_key, milestone)
    if len(_recently_published) > _DEDUP_MAX_ENTRIES:
        expired = [k for k, ts in _recently_published.items() if now - ts > _DEDUP_TTL_SECONDS]
        if expired:
            for k in expired:
                _recently_published.pop(k, None)
        else:
            _recently_published.clear()
    last = _recently_published.get(key)
    if last is not None and now - last <= _DEDUP_TTL_SECONDS:
        return False
    _recently_published[key] = now
    return True


async def publish_execution_step_event(intent: "ExecutionIntent", milestone: str) -> None:
    """在执行步进点发布 ``run.status_changed``（EXECUTING 可见步进）。

    永不抛出：发布失败仅记 warning（EventBus.publish 自带重试与 publish 侧
    DLQ 落档），执行链与既有守卫零影响。payload 扩展字段（``milestone``、
    ``run.to_status``、``run.step``）是 run.status_changed 的 schema 扩展，
    非新事件名。
    """
    ordinal = EXECUTION_MILESTONE_STEPS.get(milestone)
    if ordinal is None:
        logger.debug("execution run producer skipped unknown milestone {}", milestone)
        return
    try:
        intent_key = str(intent.id)
        if not _should_publish(intent_key, milestone):
            return
        payload: dict[str, Any] = {
            "event_type": RunEventName.STATUS_CHANGED.value,
            "user_id": str(intent.user_id),
            "execution_intent_id": intent_key,
            "task_id": str(intent.task_id),
            "milestone": milestone,
            "run": {
                # 步进期 run 落点统一 EXECUTING；终态不在此发（intent 状态漏斗
                # 单一真源）。消费侧只允许 QUEUED/RUNNING 源落此态（防迟到
                # 步进覆盖 AWAITING_* 等待态）。
                "to_status": RunStatus.EXECUTING.value,
                "step": {
                    "ordinal": ordinal,
                    "stage": EXECUTION_MILESTONE_STAGES.get(milestone),
                    "steps_total": EXECUTION_MILESTONE_STEPS_TOTAL,
                },
            },
            "timestamp": _utcnow_iso(),
        }
        await event_bus.publish(
            RunEventName.STATUS_CHANGED.value,
            payload,
            stream=RUN_EVENT_STREAM,
        )
    except Exception as exc:  # noqa: BLE001 — 可见性钩子永不削弱执行链
        logger.warning("execution run step publish failed intent_id={} milestone={} error={!r}", intent.id, milestone, exc)
