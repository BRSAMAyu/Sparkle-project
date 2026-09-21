"""X-08 · Outcome Capture —— 「无论 Human/Agent/Hybrid 完成，统一产生 Outcome」.

定位（stream=ACTION, gate=V3-3, locks: outcome-ledger + task-core）：
- **本模块不建真源、不双写**：outcome 的真相面是 D-02 Outcome Ledger 读模型
  （五源：tasks / study_records / focus_sessions / expansion_feedback /
  behavioral_outcomes，查询时点重算）。本模块只做两件事：
  1. **映射**：把任务终态（COMPLETED / ABANDONED）映射为确定的 outcome 身份
     （``derive_outcome_id`` 幂等 id）+ 极性（POSITIVE / NEGATIVE）+ correlation
     ——纯函数、零 IO、零 LLM（DATA_FLYWHEEL §5 禁止假象的确定性面）；
  2. **广播**：以 D-01 封闭词表里的 ``outcome.recorded`` 事件（此前 status=reserved、
     producer 记为「v3: outcome evidence adapter」——本模块即该 adapter）把
     「outcome 已捕获」的事实发布到事件总线。Goal/Milestone/Experience/Galaxy
     的状态更新**不**由本模块执行：Goal.progress 走 TaskEventConsumer 消费
     ``task.completed``/``task.abandoned``（既有单一事件路径），Galaxy 掌握度走
     spark/mastery outbox（G-01/G-02），Experience 走 behavioral_outcomes 消费面
     （M-06）——各真源只有各自的单一写入者，本模块零状态写入（卡面 work 2
     「更新 Goal/Milestone/Experience/Galaxy 通过事件，不双写多个真源」）。

- **partial/failed 必须保留（卡面 work 3）**：ABANDONED 任务捕获为
  ``polarity=NEGATIVE`` 的 outcome（不静默丢弃、可查询可审计）；X-05 run 的
  PARTIAL 终态 receipt 映射为 ``polarity=NEUTRAL``（``build_run_receipt_outcome``
  词表 = ``RUN_RECEIPT_OUTCOME_POLARITY``）。极性为负/中立的 outcome **结构性
  不可点亮**：WVPL loop 谓词独立要求 ``status=COMPLETED`` + ``TruthClass.ACTUAL``
  （D-06），Goal.progress 只数 COMPLETED——「失败不点亮成果」由消费端谓词
  与账本极性共同保证，而非靠调用方记得过滤。

- **payload 内容纪律（M-07 同款）**：事件 payload 只含 ids / 极性 / 引用，
  不含结果本体与用户内容（audit-without-exposure）。真相分级（truth_class）
  是账本查询时点重算值，**不**进事件——事件只宣布「捕获了什么身份、什么极性」，
  消费方需要真相面时查账本（单一真源）。

- **已知限制（如实声明）**：``derive_outcome_id`` 产 ``outc_<hash>`` 非 Canonical
  UUID，不能填 D-01 ``CorrelationIds.outcome_id``（EventContractError，D-02 已
  记录的同款限制）；本模块在事件 payload 的 ``outcome_id`` 字段携带可读 id，
  correlation 只携带 canonical UUID（task_id/plan_id/node_id）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.event_bus import event_bus_reliable
from app.core.event_registry import require_registered_event
from app.core.outcome_ledger import (
    OUTCOME_LEDGER_SCHEMA_VERSION,
    RUN_RECEIPT_OUTCOME_POLARITY,
    OutcomePolarity,
    OutcomeSource,
    derive_outcome_id,
    outcome_key,
)
from app.models.task import Task, TaskStatus

OUTCOME_CAPTURE_SCHEMA_VERSION = "outcome.capture.v1"

#: 事件名（D-01 封闭词表；本模块是其 producer，registry 状态 reserved → live）
OUTCOME_RECORDED_EVENT = "outcome.recorded"

#: run receipt 事件面的 outcome 来源标签（仅事件 payload 身份用，**不是**账本第六源；
#: 账本源封闭集仍为 OutcomeSource 五源——receipt 的账本面是 task_completion 条目
#: 上附着的 agent_run:// 证据，见 outcome_ledger_service._task_run_receipts）
RUN_RECEIPT_EVENT_SOURCE = "run_receipt"


@dataclass(frozen=True)
class OutcomeCapture:
    """一次 outcome 捕获的确定映射（可测试的纯值对象）。"""

    outcome_id: str  # outc_<sha256[:32]>（与账本幂等 id 同源）
    outcome_key: str  # <source>:<source_id>（账本去重键）
    source: str  # OutcomeSource value / run_receipt（事件面标签）
    source_id: str
    user_id: str
    polarity: OutcomePolarity
    source_ref: str  # task://… / agent_run://…
    occurred_at: datetime
    correlation: dict[str, str]  # canonical UUID 值：task_id/plan_id/node_id/run_id
    schema_version: str = OUTCOME_CAPTURE_SCHEMA_VERSION


def build_task_outcome_capture(task: Task) -> OutcomeCapture:
    """任务终态 → outcome 捕获（纯函数）。

    - COMPLETED → POSITIVE（真相分级留给账本查询时点重算）；
    - ABANDONED → NEGATIVE（X-08：失败 outcome 保留，绝不静默丢弃、绝不点亮）。
    """
    status = task.status if isinstance(task.status, TaskStatus) else TaskStatus(str(task.status))
    if status == TaskStatus.ABANDONED:
        polarity = OutcomePolarity.NEGATIVE
    elif status == TaskStatus.COMPLETED:
        polarity = OutcomePolarity.POSITIVE
    else:  # 非终态任务不是 outcome（调用方契约错误；显式拒绝而非猜测）
        raise ValueError(f"task {task.id} is not terminal (status={status}); no outcome to capture")

    outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task.id)
    correlation: dict[str, str] = {"task_id": str(task.id)}
    if task.plan_id:
        correlation["plan_id"] = str(task.plan_id)
    if task.knowledge_node_id:
        correlation["node_id"] = str(task.knowledge_node_id)
    return OutcomeCapture(
        outcome_id=outcome_id,
        outcome_key=outcome_key(OutcomeSource.TASK_COMPLETION, task.id),
        source=OutcomeSource.TASK_COMPLETION.value,
        source_id=str(task.id),
        user_id=str(task.user_id),
        polarity=polarity,
        source_ref=f"task://{task.id}",
        occurred_at=task.completed_at or task.created_at,
        correlation=correlation,
    )


def _run_receipt_outcome_id(run_id: str) -> str:
    """run receipt 的事件面幂等 id（与 ``derive_outcome_id`` 同派生风格）。

    身份 seed 用 ``run_receipt`` 标签 + capture schema 版本——**不**经过
    ``derive_outcome_id``（其 source 参封闭为 OutcomeSource 五源，账本不收
    第六源）；receipt 的账本面是 task_completion 条目上的 agent_run:// 证据。
    """
    seed = json.dumps(
        {"schema": OUTCOME_CAPTURE_SCHEMA_VERSION, "source": RUN_RECEIPT_EVENT_SOURCE, "source_id": run_id},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "outc_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def build_run_receipt_outcome(run: Any) -> OutcomeCapture:
    """X-05 终态 run receipt → outcome 捕获映射（纯函数）。

    极性词表 = ``RUN_RECEIPT_OUTCOME_POLARITY``（封闭）：SUCCEEDED → POSITIVE；
    PARTIAL/CANCELLED → NEUTRAL（保留、可查询、不点亮也不记负）；
    FAILED/TIMED_OUT/BUDGET_EXCEEDED/UNKNOWN_OUTCOME → NEGATIVE。
    身份 hash 用 ``run_receipt`` 标签（仅事件面；账本不收第六源）。
    """
    status_value = str(getattr(run, "status", "") or "")
    if status_value not in RUN_RECEIPT_OUTCOME_POLARITY:
        raise ValueError(f"run {getattr(run, 'id', '?')} is not terminal (status={status_value!r})")
    run_id = str(run.id)
    outcome_id = _run_receipt_outcome_id(run_id)
    correlation: dict[str, str] = {"run_id": run_id}
    task_id = getattr(run, "task_id", None)
    if task_id:
        correlation["task_id"] = str(task_id)
    return OutcomeCapture(
        outcome_id=outcome_id,
        outcome_key=f"{RUN_RECEIPT_EVENT_SOURCE}:{run_id}",
        source=RUN_RECEIPT_EVENT_SOURCE,
        source_id=run_id,
        user_id=str(run.user_id),
        polarity=RUN_RECEIPT_OUTCOME_POLARITY[status_value],
        source_ref=f"agent_run://{run_id}",
        occurred_at=getattr(run, "completed_at", None) or getattr(run, "created_at", None),
        correlation=correlation,
    )


def build_outcome_recorded_payload(capture: OutcomeCapture) -> dict[str, Any]:
    """事件 payload（content-free：ids / 极性 / 引用，无结果本体）。"""
    require_registered_event(OUTCOME_RECORDED_EVENT)  # D-01 封闭词表门（显式失败优于静默漂移）
    return {
        "event_type": OUTCOME_RECORDED_EVENT,
        "schema": capture.schema_version,
        "outcome_ledger_schema": OUTCOME_LEDGER_SCHEMA_VERSION,
        "outcome_id": capture.outcome_id,
        "outcome_key": capture.outcome_key,
        "source": capture.source,
        "source_id": capture.source_id,
        "source_ref": capture.source_ref,
        "polarity": capture.polarity.value,
        "user_id": capture.user_id,
        "occurred_at": capture.occurred_at.isoformat(timespec="seconds") if capture.occurred_at else None,
        **{f"correlation_{key}": value for key, value in capture.correlation.items()},
    }


async def emit_outcome_recorded(capture: OutcomeCapture) -> str | None:
    """发布 outcome.recorded 到事件总线（fire-and-forget 事实广播）。

    总线不可达时返回 None 并告警（与 task.* 事件同款 best-effort 语义——
    事件是广播加速，不是真源；账本读模型重放查询恒可重建事实面）。
    """
    payload = build_outcome_recorded_payload(capture)
    try:
        return await event_bus_reliable.publish(OUTCOME_RECORDED_EVENT, payload)
    except Exception as exc:  # noqa: BLE001 — 广播失败不阻断业务流（可观测降级）
        logger.warning("outcome.recorded publish failed for {}: {}", capture.outcome_key, exc)
        return None


async def capture_task_outcome(task: Task) -> OutcomeCapture | None:
    """映射 + 广播一步完成（终态任务接线点共用；非终态返回 None）。"""
    try:
        capture = build_task_outcome_capture(task)
    except ValueError as exc:
        logger.debug("outcome capture skipped: {}", exc)
        return None
    await emit_outcome_recorded(capture)
    return capture


__all__ = [
    "OUTCOME_CAPTURE_SCHEMA_VERSION",
    "OUTCOME_RECORDED_EVENT",
    "RUN_RECEIPT_EVENT_SOURCE",
    "OutcomeCapture",
    "build_outcome_recorded_payload",
    "build_run_receipt_outcome",
    "build_task_outcome_capture",
    "capture_task_outcome",
    "emit_outcome_recorded",
]
