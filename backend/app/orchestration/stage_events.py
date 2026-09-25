"""E-03 实时 Stage Events——canonical 阶段词表与帧构造的单一真源.

设计约束（与卡片对齐）：
- 不新增 proto 枚举/字段：stage 事件沿用既有 ``status_update``（AgentStatus）
  + ``metadata["ux_progress"]`` 通道，网关已按 ``jsonMetadataKeys`` 透传解码，
  mobile 已解析 headline/detail——本模块只把「阶段语义」标准化，不重建通道。
- 不暴露 chain-of-thought：帧只携带阶段枚举 + 可展示摘要（headline/detail），
  构造面没有任何 reasoning 字段可传入。
- stage 与 trace 匹配：每个 stage 帧携带 ``ledger_event_id``（RunLedger 事件 id）
  与 ``trace_id``，客户端/测试可 1:1 回查 RunLedger timeline 的 workflow_stage。

词表（UX stage → run_ledger workflow_stage → AgentStatus.State）：
  intake    → orchestration → THINKING    服务可知后的首帧确认（快路径 intake/深路径 handoff）
  context   → context       → THINKING    会话/用户/画像上下文整合段
  retrieval → retrieval     → SEARCHING   文档 RAG / 记忆检索段
  decision  → routing       → THINKING    路由决策（含 E-02 双核调度）完成
  tool      → tool          → EXECUTING_TOOL DAG/工具执行段
  waiting   → waiting       → IDLE        等待用户动作（确认门/补充信息），is_blocked=True
"""

from __future__ import annotations

import json
from typing import Any

from app.gen.agent.v1 import agent_service_pb2

CANONICAL_STAGES: frozenset[str] = frozenset(
    {"intake", "handoff", "context", "retrieval", "decision", "tool", "waiting"}
)

# UX stage → RunLedger workflow_stage（「stage 与 trace 匹配」的映射真源）。
# orchestration/context/routing 复用既有 ledger 阶段；retrieval/tool/waiting
# 是 E-03 新登记的真实阶段（此前检索/工具/等待在 timeline 中不可区分）。
STAGE_TO_LEDGER_STAGE: dict[str, str] = {
    "intake": "orchestration",
    "handoff": "orchestration",
    "context": "context",
    "retrieval": "retrieval",
    "decision": "routing",
    "tool": "tool",
    "waiting": "waiting",
}

# UX stage → 既有 proto AgentStatus.State（对齐网关 deriveUXProgress 的兜底词表，
# 不新增枚举；waiting 固定 is_blocked=True）。
STAGE_TO_AGENT_STATE: dict[str, agent_service_pb2.AgentStatus.State] = {
    "intake": agent_service_pb2.AgentStatus.THINKING,
    "handoff": agent_service_pb2.AgentStatus.THINKING,
    "context": agent_service_pb2.AgentStatus.THINKING,
    "decision": agent_service_pb2.AgentStatus.THINKING,
    "retrieval": agent_service_pb2.AgentStatus.SEARCHING,
    "tool": agent_service_pb2.AgentStatus.EXECUTING_TOOL,
    "waiting": agent_service_pb2.AgentStatus.IDLE,
}

_STAGE_EVENT_METADATA_KEY = "stage_event"


def build_stage_frame(
    stage: str,
    *,
    headline: str,
    detail: str = "",
    trace_id: str = "",
    ledger_event_id: str = "",
    is_blocked: bool | None = None,
    current_agent_name: str = "Sparkle AI",
) -> agent_service_pb2.ChatResponse:
    """构造一个 canonical stage 帧（status_update + ux_progress 载荷）。

    安全不变式：本函数没有任何入参能携带 reasoning/CoT 原文——阶段帧只含
    枚举 + 可展示摘要 + trace 关联 id。
    """
    if stage not in CANONICAL_STAGES:
        raise ValueError(f"Unknown stage: {stage!r} (canonical: {sorted(CANONICAL_STAGES)})")
    blocked = True if stage == "waiting" else bool(is_blocked or False)
    payload: dict[str, Any] = {
        "stage": stage,
        "headline": headline,
        "detail": detail,
        "is_blocked": blocked,
    }
    if ledger_event_id:
        payload["ledger_event_id"] = ledger_event_id
    if trace_id:
        payload["trace_id"] = trace_id
    return agent_service_pb2.ChatResponse(
        status_update=agent_service_pb2.AgentStatus(
            state=STAGE_TO_AGENT_STATE[stage],
            details=headline,
            current_agent_name=current_agent_name,
        ),
        metadata={
            "ux_progress": json.dumps(payload, ensure_ascii=False),
            _STAGE_EVENT_METADATA_KEY: "true",
        },
    )


async def record_stage_event(
    run_ledger: Any,
    stage: str,
    *,
    headline: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """在 RunLedger 登记一个 stage 边界事件，返回事件字典（含 event_id）。

    run_ledger 为空（如极早期失败路径）时静默返回 None——stage 帧仍可下发，
    只是失去 trace 关联。事件类型固定 ``stage_<name>``，workflow_stage 取
    STAGE_TO_LEDGER_STAGE 映射，保证「stage 与 trace 匹配」可测。
    """
    if run_ledger is None:
        return None
    try:
        event: dict[str, Any] | None = await run_ledger.record_event(
            event_type=f"stage_{stage}",
            label=headline,
            workflow_stage=STAGE_TO_LEDGER_STAGE[stage],
            metadata=dict(metadata or {}),
            emit_snapshot=False,
        )
        return event
    except Exception:  # noqa: BLE001 — stage 事件失败绝不阻断主链
        from loguru import logger

        logger.debug(f"Failed to record stage event: {stage}")
        return None


async def emit_stage_event(
    *,
    stream_callback: Any,
    run_ledger: Any,
    stage: str,
    headline: str,
    detail: str = "",
    trace_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> agent_service_pb2.ChatResponse | None:
    """登记 ledger 事件 + 下发 stage 帧（失败静默，绝不阻断主链）。"""
    if stream_callback is None:
        return None
    try:
        event = await record_stage_event(run_ledger, stage, headline=headline, metadata=metadata)
        frame = build_stage_frame(
            stage,
            headline=headline,
            detail=detail,
            trace_id=trace_id,
            ledger_event_id=str((event or {}).get("event_id") or ""),
        )
        await stream_callback(frame)
        return frame
    except Exception:  # noqa: BLE001 — stage 事件失败绝不阻断主链
        from loguru import logger

        logger.debug(f"Failed to emit stage event: {stage}")
        return None
