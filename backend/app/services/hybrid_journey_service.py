"""J-06 · Hybrid Flagship Journey ——「AI 降摩擦但不偷走目标」四段链装配层.

产品意图（v3/07_tasks/cards/J-06.md + HUMAN_AGENT_HYBRID.md §4）：做一个
可泛化的 Hybrid 样板旅程——科研/比赛/作品集通用的「材料 → 判断 → 交付」：

    段1 Agent prep  → 段2 Human judgment → 段3 Agent execute/check → 段4 Outcome

**不重建真源**（卡面 Forbidden #1；先侦察复用的装配纪律，J-04/J-05 同款）：
- 旅程脊柱 / handoff / 幂等 resume = X-05/X-07 ``AgentRunService``
  （steps 计划、awaiting、完成戳、owner 纪律零复制）；
- Agent prep 的材料检索 = 真实注册工具 ``retrieve_user_material`` 经 X-06
  ``ToolExecutor`` 完整执行链（权限判定 + 账本行 + 真实检索）——零 mock、
  零预录：引用全部指向真实 ``document_chunks`` 行；
- goal / task 锚点 = J-04 ``collect_first_action_context`` 与 tasks 读侧
  （不建第二 goal/task 存储）；
- 引用格式解析 = C-04 ``citation_markers`` 既有确定性解析（不重写）；
- Outcome 段 = X-08 既有 outcome 捕获函数 + G-02 既有吸收器消费者
  （本层零图谱写）；任务完成走 ``TaskService`` 既有路径（单一事件源）。

**卡魂（AI 不偷走目标）的机制化**：段2（judgment）owner=human——
- 服务层**没有**任何默认选择路径：空选择 → ``JudgmentRequiredError``；
- agent 路径完成 human 步被 X-07 owner 纪律结构性拒绝（本层不提供绕过）；
- 判断面显式携带「为什么需要你决定」（why_human + l10n 键）：材料取舍与
  聚焦方向是 goal-defining 的价值判断，属于用户（HUMAN_AGENT_HYBRID §1/§3）。

**每段产物可溯源（work 3）**：每段一行 ``HybridJourneyArtifact``，统一携带
``citations``（citation_id/scheme/ref/source_ref 指向真实 chunk 行）与
C-01 对齐 ``source_refs``；草稿必须带 [S#] 且引用落在用户选择集内——
确定性 check（零 LLM）失败即诚实失败（不落产物、run 不假装完成）。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.citation_markers import parse_cited_markers
from app.core.run_steps import awaiting_step_projection, find_step
from app.models.agent_run import AgentRun
from app.models.agent_tool_call import AgentToolCall
from app.models.document_chunks import DocumentChunk
from app.models.hybrid_journey import HybridJourneyArtifact
from app.models.memory import MemoryGoal
from app.models.task import Task, TaskStatus
from app.orchestration.executor import ToolExecutor
from app.services.agent_run_service import (
    AgentRunService,
    MissingIdempotencyKeyError,
    TransitionActor,
)
from app.services.first_action_service import collect_first_action_context
from app.services.outcome_capture_service import (
    build_run_receipt_outcome,
    emit_outcome_recorded,
)

HYBRID_JOURNEY_SCHEMA_VERSION = "hybrid_journey.v1"

#: X-03 trace_id 面标记（run 聚合上的链路面；GET /runs 可按 trace 检索）。
HYBRID_JOURNEY_TRACE_ID = "hybrid_journey"

#: prep 段执行的真实工具（X-06 注册表成员；run allowed_tools 白名单封闭）。
PREP_TOOL_NAME = "retrieve_user_material"

#: 单次旅程引用候选上限（工具 limit 词表 1..6 内取 4——判断面可读）。
PREP_CITATION_LIMIT = 4

#: 判断段 awaiting 戳引用上限以内（≤16）：候选 source_refs 全量内嵌。
_JUDGMENT_STAMP_REF_LIMIT = 16

#: LlmChat 注入面（J-04 同形）：messages → 原始文本；生产默认真实模型。
LlmChat = Callable[[list[dict[str, str]]], Awaitable[str]]

_LLM_TIMEOUT_SECONDS = 12.0


# ---------------------------------------------------------------------------
# 错误面（API 层据此映射诚实错误码）
# ---------------------------------------------------------------------------


class HybridJourneyError(Exception):
    """旅程链路错误基类."""


class NoActiveGoalError(HybridJourneyError):
    """没有 active goal——没有方向就没有旅程（诚实 422，J-04 同语义）."""


class NoTaskAnchorError(HybridJourneyError):
    """没有可交付的在飞任务——旅程的 outcome 必须落到真实任务上（诚实 422）."""


class NoMaterialError(HybridJourneyError):
    """真实材料检索零命中——旅程不编造引用（诚实 422）."""


class HybridJourneyStateError(HybridJourneyError):
    """旅程状态与请求动作不匹配（409；过期/取消后的迟到动作被明确拒绝）."""


class JudgmentRequiredError(HybridJourneyError):
    """卡魂：判断段没有用户决定——服务层结构性拒绝代决（422 judgment_required）。"""

    def __init__(self) -> None:
        super().__init__("judgment_required: the user must choose; Sparkle cannot decide on their behalf")


class JudgmentUnknownSourceError(HybridJourneyError):
    """选择引用了 prep 候选之外的材料（422；编造来源不合法）."""


class JourneyGenerationError(HybridJourneyError):
    """Aurora 起草失败（LLM 不可用/超时）——显式可重试，不静默降级."""

    def __init__(self, detail: str = "") -> None:
        self.retryable = True
        super().__init__(f"journey generation failed: {detail}")


class JourneyCheckError(HybridJourneyError):
    """确定性引用 check 失败（无引用/越集引用）——不落产物，可重试."""

    def __init__(self, *, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.retryable = True
        super().__init__(f"journey check failed ({reason}): {detail}")


# ---------------------------------------------------------------------------
# 四段链步骤计划（X-07 契约形态；「轮到谁」的持久标注）
# ---------------------------------------------------------------------------

JOURNEY_STEPS: list[dict[str, Any]] = [
    {
        "step_id": "prep",
        "ordinal": 1,
        "label": "Agent 准备材料",
        "owner": "agent",
        "completion_condition": {"kind": "agent_output", "description": "真实材料检索候选引用集就绪"},
    },
    {
        "step_id": "judgment",
        "ordinal": 2,
        "label": "你来研判",
        "owner": "human",
        "completion_condition": {"kind": "user_edit", "description": "用户选择材料并给出聚焦方向"},
    },
    {
        "step_id": "execute_check",
        "ordinal": 3,
        "label": "Agent 起草并核对",
        "owner": "agent",
        "completion_condition": {"kind": "agent_output", "description": "带引用草稿通过确定性 check"},
    },
    {
        "step_id": "outcome",
        "ordinal": 4,
        "label": "确认交付",
        "owner": "hybrid",
        "completion_condition": {"kind": "user_confirmation", "description": "用户确认产出后任务完成并记录 outcome"},
    },
]

_JUDGMENT_WHY_HUMAN_KEY = "hybridJourneyJudgmentWhyHuman"

#: 判断归属说明（receipt 单一说明句制，J-05 同形；客户端 l10n 键并行提供）。
_JUDGMENT_WHY_HUMAN = (
    "选哪些材料、把综述聚焦到哪里，定义的是你自己的研究判断——"
    "这一步必须由你决定：Sparkle 只负责准备和核对，不替你选。"
)

_OUTCOME_CONFIRM_REASON = "以上是按你的选择起草并核对的产出；确认它真实可用，任务才会完成并记入你的成长图谱。"


def _judgment_brief(citations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "why_human_key": _JUDGMENT_WHY_HUMAN_KEY,
        "why_human": _JUDGMENT_WHY_HUMAN,
        "options": citations,
        "requires": ["selected_refs (至少一个；必须出自候选)", "focus_note (可选)"],
    }


# ---------------------------------------------------------------------------
# citation 结构（封闭形状；每段产物可溯源的统一面）
# ---------------------------------------------------------------------------


def _citation_from_result(index: int, item: dict[str, Any]) -> dict[str, Any]:
    """真实检索结果行 → 统一 citation 结构（ref 指向真实 chunk 行）。"""
    chunk_ref = str(item.get("chunk_id") or "").strip()
    return {
        "citation_id": f"S{index}",
        "scheme": "document_chunk",
        "ref": chunk_ref,
        "source_ref": f"document_chunk://{chunk_ref}",
        "file_id": str(item.get("file_id") or ""),
        "file_name": str(item.get("file_name") or ""),
        "chunk_index": item.get("chunk_index"),
        "page_numbers": list(item.get("page_numbers") or []),
        "score": item.get("score"),
        "snippet": str(item.get("snippet") or ""),
    }


def _ref_of(scheme: str, ref: str) -> dict[str, str]:
    return {"scheme": scheme, "ref": str(ref)}


def _source_refs_from_citations(citations: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [_ref_of("document_chunk", str(c["ref"])) for c in citations]


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


@dataclass(frozen=True)
class _JourneyAnchor:
    """旅程锚点投影（goal/task 真源读侧；缺真源如实为 None）。"""

    goal_id: UUID | None
    goal_title: str
    task_id: UUID | None
    task_title: str


async def _resolve_anchor(db: AsyncSession, *, user_id: UUID, task_id: UUID | None) -> _JourneyAnchor:
    """goal = J-04 真源读侧；task = 指定行或最近触碰的在飞任务（stuck_journey 同判据）。"""
    context = await collect_first_action_context(db, user_id=user_id)
    if context is None:
        raise NoActiveGoalError()

    task: Task | None = None
    if task_id is not None:
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id, Task.not_deleted_filter())
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NoTaskAnchorError()
    else:
        in_flight = (
            TaskStatus.IN_PROGRESS,
            TaskStatus.PAUSED,
            TaskStatus.STUCK,
            TaskStatus.RESTORE,
            TaskStatus.PENDING,
        )
        result = await db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status.in_(list(in_flight)),
                Task.not_deleted_filter(),
            )
            .order_by(Task.updated_at.desc())
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NoTaskAnchorError()

    return _JourneyAnchor(
        goal_id=context.goal_id,
        goal_title=context.goal_title,
        task_id=task.id,
        task_title=str(task.title or "").strip(),
    )


async def _anchor_from_run(db: AsyncSession, run: AgentRun) -> _JourneyAnchor:
    """从 run 聚合 + 既有真源读侧重建锚点投影（状态回放/各段返回共用）。"""
    task_title = ""
    if run.task_id is not None:
        task_row = await db.get(Task, run.task_id)
        if task_row is not None:
            task_title = str(task_row.title or "")
    goal_id: UUID | None = None
    goal_title = ""
    prep = await _latest_stage_artifact(db, run.id, stage="prep")
    for ref in (prep.source_refs if prep is not None else []) or []:
        if isinstance(ref, dict) and ref.get("scheme") == "goal" and _is_uuid(str(ref.get("ref"))):
            goal_id = UUID(str(ref["ref"]))
            break
    if goal_id is not None:
        goal_row = await db.get(MemoryGoal, goal_id)
        if goal_row is not None:
            goal_title = str(goal_row.title or "")
    else:
        context = await collect_first_action_context(db, user_id=run.user_id)
        if context is not None:
            goal_id, goal_title = context.goal_id, context.goal_title
    return _JourneyAnchor(
        goal_id=goal_id,
        goal_title=goal_title,
        task_id=run.task_id,
        task_title=task_title,
    )


async def _latest_stage_artifact(db: AsyncSession, run_id: UUID, *, stage: str) -> HybridJourneyArtifact | None:
    result = await db.execute(
        select(HybridJourneyArtifact)
        .where(
            HybridJourneyArtifact.run_id == run_id,
            HybridJourneyArtifact.stage == stage,
            HybridJourneyArtifact.not_deleted_filter(),
        )
        .order_by(HybridJourneyArtifact.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _run_artifacts(db: AsyncSession, run_id: UUID) -> list[HybridJourneyArtifact]:
    result = await db.execute(
        select(HybridJourneyArtifact)
        .where(
            HybridJourneyArtifact.run_id == run_id,
            HybridJourneyArtifact.not_deleted_filter(),
        )
        .order_by(HybridJourneyArtifact.created_at.asc())
    )
    return list(result.scalars().all())


def _journey_payload(
    *,
    anchor: _JourneyAnchor,
    run: AgentRun,
    artifacts: list[HybridJourneyArtifact],
    receipt: dict[str, Any],
    citations: list[dict[str, Any]] | None = None,
    judgment_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": HYBRID_JOURNEY_SCHEMA_VERSION,
        "run": run.to_dict(),
        "goal": (None if anchor.goal_id is None else {"goal_id": str(anchor.goal_id), "title": anchor.goal_title}),
        "task": (None if anchor.task_id is None else {"id": str(anchor.task_id), "title": anchor.task_title}),
        "artifacts": [artifact.projection() for artifact in artifacts],
        "receipt": receipt,
    }
    if citations is not None:
        payload["citations"] = citations
    if judgment_brief is not None:
        payload["judgment_brief"] = judgment_brief
    return payload


def _awaiting_of(run: AgentRun) -> dict[str, Any] | None:
    return awaiting_step_projection(
        run_status=run.status.value if run.status else None,
        wait_kind=run.wait_kind,
        terminal_reason=run.terminal_reason,
        wait_expires_at=run.wait_expires_at,
        steps=run.steps,
    )


async def _replay_payload(db: AsyncSession, run: AgentRun) -> dict[str, Any]:
    """幂等回放面（重复启动 / 状态读面共用；全部真源读侧重建）。"""
    anchor = await _anchor_from_run(db, run)
    artifacts = await _run_artifacts(db, run.id)
    prep = next((a for a in artifacts if a.stage == "prep"), None)
    citations = list(prep.citations) if prep is not None else None
    brief = None
    awaiting = _awaiting_of(run)
    if awaiting is not None and awaiting.get("step_id") == "judgment":
        brief = _judgment_brief(citations or [])
    return _journey_payload(
        anchor=anchor,
        run=run,
        artifacts=artifacts,
        citations=citations,
        judgment_brief=brief,
        receipt={
            "receipt_type": "hybrid_journey_state",
            "decision_reason": "旅程状态回放（幂等）。",
        },
    )


# ---------------------------------------------------------------------------
# 段1+2 启动：prep（真实工具）→ judgment awaiting（轮到用户）
# ---------------------------------------------------------------------------


async def start_hybrid_journey(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    task_id: UUID | str | None = None,
    idempotency_key: str | None = None,
    session_id: str | None = None,
    tool_executor: ToolExecutor | None = None,
) -> dict[str, Any]:
    """启动四段旅程：真实锚点 → run（X-07 计划）→ prep（真实工具检索）→
    判断面 awaiting。幂等：同 task 的重复启动收敛到同一 run（已过 prep
    则原样回放状态，不重复检索、不重复落产物）。
    """
    user_uuid = UUID(str(user_id))
    anchor = await _resolve_anchor(db, user_id=user_uuid, task_id=UUID(str(task_id)) if task_id else None)

    service = AgentRunService(db)
    key = (str(idempotency_key).strip() if idempotency_key else None) or f"hybrid_journey:{anchor.task_id}"
    created = await service.create_run(
        user_id=user_uuid,
        objective=f"Hybrid 旅程：{anchor.goal_title[:60]} —— 材料研判与带引用交付",
        kind="system",
        trace_id=HYBRID_JOURNEY_TRACE_ID,
        task_id=anchor.task_id,
        context_refs=[f"goal://{anchor.goal_id}", f"task://{anchor.task_id}"],
        allowed_tools=[PREP_TOOL_NAME],
        completion_condition={"kind": "user_confirmation", "description": "用户确认带引用交付"},
        risk_class="low",
        steps=JOURNEY_STEPS,
        idempotency_key=key,
        session_id=session_id,
        source="server_service",
    )
    run = created.run
    if not created.created:
        # 幂等重放：已存在的 run 按当前状态回放（判断等待中原样返回）。
        return await _replay_payload(db, run)

    # QUEUED → RUNNING（用户启动；prep 即执行）
    run = (
        await service.transition(
            run.id,
            "RUNNING",
            user_id=user_uuid,
            actor=TransitionActor.USER,
            current_stage="prep",
            source="server_service",
        )
    ).run

    # ---- 段1 prep：真实注册工具经 X-06 完整执行链（权限 + 账本 + 真实检索）----
    executor = tool_executor or ToolExecutor()
    tool_result = await executor.execute_tool_call(
        PREP_TOOL_NAME,
        {"query": anchor.goal_title[:120], "limit": PREP_CITATION_LIMIT},
        str(user_uuid),
        db,
        tool_call_id=f"j06_prep_{run.id}",
        runtime_context={"run_id": str(run.id)},
        idempotency_key=f"hybrid_journey:prep:{run.id}",
    )
    if not tool_result.success:
        logger.warning("hybrid journey prep tool failed run={} err={}", run.id, tool_result.error_message)
        raise HybridJourneyStateError(f"prep tool failed: {tool_result.error_message or 'unknown'}")
    data = dict(tool_result.data or {})
    results = [item for item in (data.get("results") or []) if isinstance(item, dict) and item.get("chunk_id")]
    if not results:
        # 诚实失败：真实材料检索零命中 → 不建旅程产物、不编造引用。
        raise NoMaterialError()

    citations = [_citation_from_result(index, item) for index, item in enumerate(results, start=1)]
    ledger_row = (
        (
            await db.execute(
                select(AgentToolCall).where(
                    AgentToolCall.user_id == user_uuid,
                    AgentToolCall.tool_name == PREP_TOOL_NAME,
                    AgentToolCall.idempotency_key == f"hybrid_journey:prep:{run.id}",
                )
            )
        )
        .scalars()
        .first()
    )
    prep_source_refs = [
        _ref_of("goal", str(anchor.goal_id)),
        _ref_of("task", str(anchor.task_id)),
        _ref_of("tool_call", str(ledger_row.id)) if ledger_row is not None else _ref_of("run", str(run.id)),
    ]
    prep_artifact = HybridJourneyArtifact(
        user_id=user_uuid,
        run_id=run.id,
        task_id=anchor.task_id,
        stage="prep",
        artifact_kind="citations",
        citations=citations,
        source_refs=prep_source_refs + [_ref_of("document", c["file_id"]) for c in citations if c.get("file_id")],
        payload={
            "query": data.get("query"),
            "retrieval_mode": data.get("retrieval_mode"),
            "scoped_file_count": data.get("scoped_file_count"),
            "tool_call_ref": f"tool_call://{ledger_row.id}" if ledger_row is not None else None,
            "goal_title": anchor.goal_title,
            "task_title": anchor.task_title,
        },
        schema_version=HYBRID_JOURNEY_SCHEMA_VERSION,
    )
    db.add(prep_artifact)
    await db.flush()

    run = (
        await service.complete_agent_step(
            run.id,
            step_id="prep",
            artifact_refs=[_ref_of("tool_call", str(ledger_row.id))] if ledger_row is not None else None,
        )
    ).run

    # ---- 段2 judgment：轮到用户（显式说明为什么必须你决定）----
    run = (
        await service.await_user_step(
            run.id,
            step_id="judgment",
            prompt=_JUDGMENT_WHY_HUMAN,
            artifact_refs=_source_refs_from_citations(citations)[:_JUDGMENT_STAMP_REF_LIMIT],
            actor=TransitionActor.SYSTEM.value,
            source="server_service",
        )
    ).run
    await db.commit()

    return _journey_payload(
        anchor=anchor,
        run=run,
        artifacts=[prep_artifact],
        citations=citations,
        judgment_brief=_judgment_brief(citations),
        receipt={
            "receipt_type": "hybrid_journey_started",
            "decision_reason": ("已从你的材料中检索出候选引用；选哪些、聚焦什么，由你决定。"),
            "prep_tool": PREP_TOOL_NAME,
        },
    )


# ---------------------------------------------------------------------------
# 段2 提交判断（空选择结构性拒绝）→ 段3 execute/check → 段4 awaiting outcome
# ---------------------------------------------------------------------------


async def submit_judgment(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    run_id: UUID | str,
    selected_refs: list[str],
    focus_note: str | None = None,
    idempotency_key: str,
    llm_chat: LlmChat | None = None,
) -> dict[str, Any]:
    """用户判断：从候选中选择真实材料引用（AI 不代决——空选择 422）。

    幂等语义：判断步已完成时（同 key 重放 / check 失败后的重试），不重复
    resume、不重复落判断戳，直接继续完成剩余 agent 段。
    """
    user_uuid = UUID(str(user_id))
    key = str(idempotency_key or "").strip()
    if not key:
        raise MissingIdempotencyKeyError("submit_judgment requires an idempotency_key")

    service = AgentRunService(db)
    run = await service.get_run(run_id, user_id=user_uuid)
    if run.trace_id != HYBRID_JOURNEY_TRACE_ID:
        raise HybridJourneyStateError(f"run {run.id} is not a hybrid journey")

    prep = await _latest_stage_artifact(db, run.id, stage="prep")
    if prep is None:
        raise HybridJourneyStateError("journey has no prep artifact; judgment surface unavailable")
    prepared = {str(c.get("source_ref")): c for c in (prep.citations or [])}

    # ---- 卡魂：判断必须来自用户；服务层没有默认选择路径 ----
    refs = [str(ref or "").strip() for ref in (selected_refs or [])]
    refs = [ref for ref in refs if ref]
    if not refs:
        raise JudgmentRequiredError()
    unknown = [ref for ref in refs if ref not in prepared]
    if unknown:
        raise JudgmentUnknownSourceError(f"selected refs not in prepared candidates: {unknown[:3]}")
    # 真实行复核：候选引用必须仍指向活着的 chunk（材料被删 → 诚实拒绝）。
    chunk_ids = [UUID(prepared[ref]["ref"]) for ref in refs]
    rows = (
        (
            await db.execute(
                select(DocumentChunk).where(
                    DocumentChunk.id.in_(chunk_ids),  # type: ignore[attr-defined]
                    DocumentChunk.user_id == user_uuid,
                    DocumentChunk.not_deleted_filter(),
                )
            )
        )
        .scalars()
        .all()
    )
    alive_refs = {f"document_chunk://{row.id}" for row in rows}
    missing = [ref for ref in refs if ref not in alive_refs]
    if missing:
        raise JudgmentUnknownSourceError(f"selected materials no longer exist: {missing[:3]}")

    chosen = [prepared[ref] for ref in refs]
    judgment_step = find_step(run.steps, "judgment")
    replay = bool(judgment_step is not None and judgment_step.get("completion"))
    if not replay:
        awaiting = _awaiting_of(run)
        if awaiting is None or awaiting.get("step_id") != "judgment":
            raise HybridJourneyStateError(f"run {run.id} is not awaiting the judgment step (status={run.status.value})")
        await service.complete_user_step(
            run.id,
            step_id="judgment",
            user_id=user_uuid,
            idempotency_key=key,
            action="decide",
            artifact_refs=_source_refs_from_citations(chosen),
            note=(focus_note or "")[:200] or None,
            current_stage="execute_check",
        )
        db.add(
            HybridJourneyArtifact(
                user_id=user_uuid,
                run_id=run.id,
                task_id=run.task_id,
                stage="judgment",
                artifact_kind="selection",
                citations=chosen,
                source_refs=[_ref_of("run", str(run.id))],
                payload={
                    "selected_refs": refs,
                    "focus_note": (focus_note or "")[:200] or None,
                    "decided_by": "user",
                },
                schema_version=HYBRID_JOURNEY_SCHEMA_VERSION,
            )
        )
        await db.flush()

    # ---- 段3 execute/check：按用户选择起草（LLM 注入面）+ 确定性引用核对 ----
    run = await service.get_run(run.id, user_id=user_uuid)
    outline, cited_ids, chosen = await _execute_and_check(
        run=run, chosen=chosen, focus_note=focus_note, llm_chat=llm_chat
    )
    goal_ref = next(
        (
            _ref_of("goal", str(ref["ref"]))
            for ref in (prep.source_refs or [])
            if isinstance(ref, dict) and ref.get("scheme") == "goal"
        ),
        _ref_of("run", str(run.id)),
    )
    outline_artifact = HybridJourneyArtifact(
        user_id=user_uuid,
        run_id=run.id,
        task_id=run.task_id,
        stage="execute_check",
        artifact_kind="checked_outline",
        citations=chosen,
        source_refs=[_ref_of("run", str(run.id)), goal_ref],
        payload={
            "outline_markdown": outline,
            "focus_note": (focus_note or "")[:200] or None,
            "check": {"passed": True, "cited_ids": cited_ids, "invalid_cited": []},
        },
        schema_version=HYBRID_JOURNEY_SCHEMA_VERSION,
    )
    db.add(outline_artifact)
    await db.flush()
    run = (
        await service.complete_agent_step(
            run.id,
            step_id="execute_check",
            artifact_refs=[
                _ref_of("journey_artifact", str(outline_artifact.id)),
                *_source_refs_from_citations(chosen),
            ],
        )
    ).run

    # ---- 段4 awaiting outcome：产出备好，等用户确认交付（hybrid 所有权）----
    run = (
        await service.await_user_step(
            run.id,
            step_id="outcome",
            prompt=_OUTCOME_CONFIRM_REASON,
            artifact_refs=[_ref_of("journey_artifact", str(outline_artifact.id))],
            actor=TransitionActor.SYSTEM.value,
            source="server_service",
        )
    ).run
    await db.commit()

    anchor = await _anchor_from_run(db, run)
    return _journey_payload(
        anchor=anchor,
        run=run,
        artifacts=await _run_artifacts(db, run.id),
        receipt={
            "receipt_type": "hybrid_journey_judged",
            "decision_reason": (
                "已按你的选择起草并逐条核对引用；确认产出后，任务才会完成。"
                + ("（幂等重放：继续完成剩余步骤）" if replay else "")
            ),
            "judgment_replay": replay,
        },
    )


_DRAFT_SYSTEM_PROMPT = (
    "你是 Sparkle 的 Aurora。基于用户从自己材料中**亲自选定**的片段，起草一份"
    "研究综述大纲（markdown）。规则：材料支撑的表述必须在句末标注来源编号"
    "（如 ……[S1]）；材料未覆盖的部分不要标注编号，也不要编造来源；"
    "严格只输出大纲正文，不要解释。"
)


async def _execute_and_check(
    *,
    run: AgentRun,
    chosen: list[dict[str, Any]],
    focus_note: str | None,
    llm_chat: LlmChat | None,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """起草 + 确定性 check（check 零 LLM）。失败路径不落任何产物。"""
    material_lines = [
        f"[{c['citation_id']}]（{c.get('file_name') or '材料'}"
        f"{'，p.' + '、'.join(str(p) for p in c.get('page_numbers') or []) if c.get('page_numbers') else ''}）"
        f"{c['snippet']}"
        for c in chosen
    ]
    focus = f"用户指定的聚焦方向：{focus_note}" if focus_note else ""
    messages = [
        {"role": "system", "content": _DRAFT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "\n".join(
                [
                    f"目标：{str(run.objective or '').strip()}",
                    focus,
                    "已选材料片段（只可引用这些来源）：",
                    *material_lines,
                ]
            ),
        },
    ]
    chat = llm_chat if llm_chat is not None else _default_llm_chat
    try:
        raw = await asyncio.wait_for(chat(messages), timeout=_LLM_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        raise JourneyGenerationError("llm timeout") from exc
    except Exception as exc:  # noqa: BLE001 — 下游错误统一转诚实生成失败
        raise JourneyGenerationError(str(exc)[:300]) from exc
    outline = (raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)) or ""
    if not outline.strip():
        raise JourneyGenerationError("empty draft")

    # 确定性 check（C-04 解析器复用）：引用必须落在用户选择集内，且至少一条。
    cited = parse_cited_markers(outline)
    valid_ids = {c["citation_id"] for c in chosen}
    invalid = sorted({marker for marker in cited if marker not in valid_ids})
    if not cited:
        raise JourneyCheckError(reason="uncited_draft", detail="draft cites none of the chosen materials")
    if invalid:
        raise JourneyCheckError(
            reason="unresolved_citations",
            detail=f"citations outside user-selected sources: {invalid}",
        )
    return outline.strip(), sorted(set(cited)), chosen


# ---------------------------------------------------------------------------
# 段4 确认交付：任务完成（既有路径）→ run SUCCEEDED → receipt outcome
# ---------------------------------------------------------------------------


async def confirm_outcome(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    run_id: UUID | str,
    idempotency_key: str,
    note: str | None = None,
) -> dict[str, Any]:
    """用户确认交付（段4）：完成戳 + resume → 任务经既有 TaskService 完成
    （X-08 outcome 捕获随之发生）→ run SUCCEEDED（result_ref 指向产物行）
    → run receipt outcome 广播（X-08 既有函数；G-02 既有消费者吸收，
    同因 receipt 只补溯源——不重复点亮）。
    """
    user_uuid = UUID(str(user_id))
    key = str(idempotency_key or "").strip()
    if not key:
        raise MissingIdempotencyKeyError("confirm_outcome requires an idempotency_key")

    service = AgentRunService(db)
    run = await service.get_run(run_id, user_id=user_uuid)
    if run.trace_id != HYBRID_JOURNEY_TRACE_ID:
        raise HybridJourneyStateError(f"run {run.id} is not a hybrid journey")

    outcome_step = find_step(run.steps, "outcome")
    if outcome_step is not None and outcome_step.get("completion"):
        # 幂等重放：交付已确认过——原样回放终态（不二次完成任务/不二次 outcome）。
        return await _confirmed_replay(db, run)

    awaiting = _awaiting_of(run)
    if awaiting is None or awaiting.get("step_id") != "outcome":
        raise HybridJourneyStateError(f"run {run.id} is not awaiting outcome confirmation (status={run.status.value})")
    outline_artifact = await _latest_stage_artifact(db, run.id, stage="execute_check")
    if outline_artifact is None:
        raise HybridJourneyStateError("journey has no checked outline; outcome cannot be confirmed")
    if run.task_id is None:
        raise HybridJourneyStateError("journey run has no task anchor")

    await service.complete_user_step(
        run.id,
        step_id="outcome",
        user_id=user_uuid,
        idempotency_key=key,
        action="confirm",
        artifact_refs=[_ref_of("journey_artifact", str(outline_artifact.id))],
        note=(note or "")[:200] or None,
        current_stage="outcome",
    )

    # 任务完成走既有 TaskService 路径（plan 进度/spark/outcome 捕获单一事件源）。
    from app.services.task_service import TaskService

    task = await db.get(Task, run.task_id)
    if task is None:
        raise HybridJourneyStateError("journey task anchor no longer exists")
    if task.status not in (TaskStatus.COMPLETED, TaskStatus.ABANDONED):
        task = await TaskService.complete_task(
            db,
            run.task_id,
            user_uuid,
            None,
            note=(note or "")[:200] or None,
            evidence=[
                {
                    "evidence_kind": "artifact",
                    "ref": f"run://{run.id}",
                    "description": "Hybrid 旅程带引用交付（用户研判 + Agent 起草核对）",
                }
            ],
            evidence_source="user",
        )

    # run 终态（合法边 RUNNING→SUCCEEDED；result_ref 经 transition 合法写入）。
    run = await service.get_run(run.id, user_id=user_uuid)
    outcome_artifact = HybridJourneyArtifact(
        user_id=user_uuid,
        run_id=run.id,
        task_id=run.task_id,
        stage="outcome",
        artifact_kind="delivery_receipt",
        citations=list(outline_artifact.citations or []),
        source_refs=[_ref_of("run", str(run.id)), _ref_of("task", str(run.task_id))],
        payload={
            "task_id": str(run.task_id),
            "task_status": str(getattr(task.status, "value", task.status)),
            "checked_outline_artifact": str(outline_artifact.id),
        },
        schema_version=HYBRID_JOURNEY_SCHEMA_VERSION,
    )
    db.add(outcome_artifact)
    await db.flush()

    run = (
        await service.transition(
            run.id,
            "SUCCEEDED",
            user_id=user_uuid,
            actor=TransitionActor.SYSTEM,
            reason="completed",
            current_stage="outcome",
            result_ref={"scheme": "journey_artifact", "ref": str(outcome_artifact.id)},
            source="server_service",
        )
    ).run

    # X-08 既有 receipt 函数：SUCCEEDED run 的 outcome 捕获广播（best-effort）。
    receipt_capture = build_run_receipt_outcome(run)
    await emit_outcome_recorded(receipt_capture)
    await db.commit()

    anchor = await _anchor_from_run(db, run)
    return _journey_payload(
        anchor=anchor,
        run=run,
        artifacts=await _run_artifacts(db, run.id),
        receipt={
            "receipt_type": "hybrid_journey_completed",
            "decision_reason": (
                "你已确认交付：任务完成并记入 outcome；图谱点亮由既有 G-02 消费者幂等吸收（不重复点亮）。"
            ),
            "outcome_id": receipt_capture.outcome_id,
            "polarity": receipt_capture.polarity.value,
        },
    )


async def _confirmed_replay(db: AsyncSession, run: AgentRun) -> dict[str, Any]:
    payload = await _replay_payload(db, run)
    payload["receipt"] = {
        "receipt_type": "hybrid_journey_completed",
        "decision_reason": "交付已确认过（幂等回放）；不重复完成任务、不重复产出 outcome。",
    }
    return payload


# ---------------------------------------------------------------------------
# 状态读面（重开 App 持久化回放）
# ---------------------------------------------------------------------------


async def get_hybrid_journey_state(db: AsyncSession, *, user_id: UUID | str, run_id: UUID | str) -> dict[str, Any]:
    user_uuid = UUID(str(user_id))
    run = await AgentRunService(db).get_run(run_id, user_id=user_uuid)
    if run.trace_id != HYBRID_JOURNEY_TRACE_ID:
        raise HybridJourneyStateError(f"run {run.id} is not a hybrid journey")
    return await _replay_payload(db, run)


# ---------------------------------------------------------------------------
# 生产默认 LLM（J-04 同路：GENERATION/FAST tier）
# ---------------------------------------------------------------------------


async def _default_llm_chat(messages: list[dict[str, str]]) -> str:
    from app.core.agent_profiles import AgentRole, ModelTier, TaskType
    from app.services.llm_service import get_configured_llm_service_for_tier

    llm = await get_configured_llm_service_for_tier(
        AgentRole.GENERATION,
        ModelTier.FAST,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="fast",
    )
    raw = await asyncio.wait_for(llm.chat(messages, temperature=0.2), timeout=_LLM_TIMEOUT_SECONDS)
    return raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)


__all__ = [
    "HYBRID_JOURNEY_SCHEMA_VERSION",
    "HYBRID_JOURNEY_TRACE_ID",
    "JOURNEY_STEPS",
    "HybridJourneyError",
    "HybridJourneyStateError",
    "JourneyCheckError",
    "JourneyGenerationError",
    "JudgmentRequiredError",
    "JudgmentUnknownSourceError",
    "NoActiveGoalError",
    "NoMaterialError",
    "NoTaskAnchorError",
    "confirm_outcome",
    "get_hybrid_journey_state",
    "start_hybrid_journey",
    "submit_judgment",
]
