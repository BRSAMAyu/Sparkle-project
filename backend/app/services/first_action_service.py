"""J-04 · First Meaningful Action —— 六环串通的粘合层（Goal→Context→Aurora→
Proposal→confirm→Task 持久化）.

设计纪律（「先侦察复用，不重建真源」）：
- **Goal 环**（J-02 已交付）：onboarding ``POST /profile/onboarding`` 写
  ``memory_goals``（MemoryService.create_goal，metadata.goal_type 携带 persona
  类型）——本服务只读该真源，不建第二 goal 存储。
- **Context 环**：从 ``memory_goals`` + ``user_preferences_center``（onboarding
  显式偏好真源）+ tasks 账本计数采集，全部真实行读取，source_refs 用 C-01/X-01
  封闭 scheme（goal:// / profile:// / user_state://）。
- **Aurora 环**（A-03/X-01/A-线已交付）：LLM 推导 Smallest Useful Step 内容，
  结构与词表经 ``ActionPlanContract``（X-01）校验；execution_mode 由 Aurora
  分配策略 ``decide_allocation``（mode 权威，学习守卫生效）裁决，LLM 建议
  只做因子输入、不是结论。
- **Proposal 环**（X-03 已交付）：``ActionCommandService.create_proposal`` 统一
  command path（task.create_batch），``trace_id="first_action"`` 标记链路面，
  授权/幂等/diff/expiry 全部沿用 X-03，零新建生命周期。
- **confirm→Task 环**（X-03 已交付）：approve → task_commands → TaskService.create，
  V3 列（desired_outcome / completion_evidence / execution_mode …）随单次 commit
  原子落库。

诚实性（卡面 acceptance「提案生成失败诚实处理」）：Aurora 推导失败（LLM 不可
用/输出不合法/契约违例）→ ``FirstActionGenerationError``（retryable），**不写
任何 proposal 行、不静默降级为模板动作、不假装成功**。错误经 API 映射为
503 结构化错误（error + retryable），重试即重新走全链。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import ProposalSource, ProposalStatus
from app.core.action_plan import (
    USEFUL_STEP_REASONS,
    ActionPlanContract,
    CompletionEvidenceSpec,
    SmallestUsefulStep,
)
from app.models.action_proposal import ActionProposal
from app.models.memory import MemoryGoal
from app.models.task import CognitiveOwnership, Task, TaskStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.task import TaskCreate
from app.services.action_allocation_policy import AllocationDecision, AllocationFactors, decide_allocation
from app.services.action_command_service import ActionCommandService

#: first-action 链路面标记（X-03 trace_id 列，索引；读侧据此查询链路状态）
FIRST_ACTION_TRACE_ID = "first_action"

#: 编辑面可改字段（封闭集合；扩展 = 契约变更）
EDITABLE_FIRST_ACTION_FIELDS: frozenset[str] = frozenset({"title", "estimated_minutes"})

#: llm_chat 注入面：messages → 原始文本（生产默认走 GENERATION/FAST tier，
#: 与 onboarding preview 同一路；测试注入脚本实现）
LlmChat = Callable[[list[dict[str, str]]], Awaitable[str]]

_LLM_TIMEOUT_SECONDS = 12.0

_VALID_EVIDENCE_KINDS = {"artifact", "file", "code", "quiz_result", "user_confirmation", "self_report", "system_event"}


class FirstActionError(Exception):
    """first-action 链路错误基类（API 层据此映射诚实错误码）."""


class NoActiveGoalError(FirstActionError):
    """用户没有 active goal——没有目标就没有 first action（诚实 422）."""

    def __init__(self) -> None:
        super().__init__("no active goal for first action")


class FirstActionGenerationError(FirstActionError):
    """Aurora 推导失败：显式、可重试；绝不静默降级."""

    def __init__(self, *, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        self.retryable = True
        super().__init__(f"first action generation failed ({reason}): {detail}")


# ---------------------------------------------------------------------------
# 环2 · Context（真实行读取，非调用方编造）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FirstActionContext:
    """first action 的上下文快照（Goal 真源 + onboarding 显式偏好 + 账本计数）."""

    user_id: UUID
    goal_id: UUID
    goal_title: str
    goal_type: str
    knowledge_level: str | None
    learning_style: str | None
    study_minutes: int | None
    open_task_count: int

    @property
    def source_refs(self) -> tuple[str, ...]:
        """C-01/X-01 封闭 scheme（goal:// user_state:// profile://）."""
        return (
            f"goal://{self.goal_id}",
            "user_state://onboarding",
            f"profile://{self.user_id}",
        )

    def prompt_bits(self) -> list[str]:
        """推导 prompt 的上下文行（真实数据流证据：goal 原文必须在内）。"""
        bits = [f"目标（用户原话）：{self.goal_title}"]
        if self.goal_type:
            bits.append(f"目标类型：{self.goal_type}")
        if self.knowledge_level:
            bits.append(f"当前基础：{self.knowledge_level}")
        if self.learning_style:
            bits.append(f"偏好风格：{self.learning_style}")
        if self.study_minutes:
            bits.append(f"每天可投入：约 {self.study_minutes} 分钟")
        if self.open_task_count:
            bits.append(f"账本中未完成任务数：{self.open_task_count}")
        return bits


def _unwrap_pref(value: Any) -> Any:
    """偏好中心存储形态归一（set_explicit_preference 写入 {"value": x} 包裹）."""
    if isinstance(value, dict):
        if "value" in value:
            return value["value"]
        if "minutes" in value:
            return value["minutes"]
    return value


async def collect_first_action_context(db: AsyncSession, *, user_id: UUID | str) -> FirstActionContext | None:
    """环1→2：读 onboarding goal 真源 + 显式偏好 + 账本计数；无 active goal → None."""
    user_uuid = UUID(str(user_id))
    goal = (
        (
            await db.execute(
                select(MemoryGoal)
                .where(
                    MemoryGoal.user_id == user_uuid,
                    MemoryGoal.status == "active",
                    MemoryGoal.deleted_at.is_(None),
                    MemoryGoal.archived_at.is_(None),
                    MemoryGoal.retracted_at.is_(None),
                )
                .order_by(MemoryGoal.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if goal is None:
        return None

    prefs_row = (
        await db.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_uuid))
    ).scalar_one_or_none()
    explicit = dict(getattr(prefs_row, "explicit", None) or {}) if prefs_row is not None else {}

    open_tasks = int(
        (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == user_uuid,
                    Task.deleted_at.is_(None),
                    Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.ABANDONED]),
                )
            )
        ).scalar()
        or 0
    )

    metadata = dict(goal.metadata_payload or {})
    knowledge_level = _unwrap_pref(explicit.get("knowledge_level"))
    learning_style = _unwrap_pref(explicit.get("learning_style"))
    study_minutes = _unwrap_pref(explicit.get("study_time_preference"))
    return FirstActionContext(
        user_id=user_uuid,
        goal_id=goal.id,
        goal_title=str(goal.title or "").strip(),
        goal_type=str(metadata.get("goal_type") or "").strip(),
        knowledge_level=str(knowledge_level).strip() or None if knowledge_level is not None else None,
        learning_style=str(learning_style).strip() or None if learning_style is not None else None,
        study_minutes=int(study_minutes) if study_minutes is not None else None,
        open_task_count=open_tasks,
    )


# ---------------------------------------------------------------------------
# 环3 · Aurora（LLM 推导 + 契约校验 + mode 权威裁决）
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "你是 Sparkle 的 Aurora。用户刚写下第一个真实目标，你要给出一个「最小有用第一步」"
    "（Smallest Useful Step）：当天就能完成、产出真实可见、推进目标本身。"
    "严格只输出 JSON（不要 markdown、不要解释），字段："
    '{"step_title": "<=30字，这一步做什么", '
    '"smallest_step": "<=60字，具体动作（从哪、打开什么、写下什么）", '
    '"desired_outcome": "<=60字，完成后手里多出什么（产出）", '
    '"evidence_kind": "artifact|file|code|quiz_result|user_confirmation|self_report|system_event", '
    '"useful_because": ["produces_artifact|reduces_uncertainty|builds_capability|unblocks_dependency|enables_decision|advances_goal 中至少一个"], '
    '"suggested_mode": "human|agent|hybrid（仅建议，系统会按分配策略裁决）", '
    '"estimated_minutes": 5~120 的整数}'
)


def _extract_json(raw: str) -> Any:
    """宽容 JSON 提取（LLMService._parse_json_payload 同法：剥围栏/思维链）。"""
    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    if cleaned.startswith("<think>"):
        end_idx = cleaned.find("</think>")
        cleaned = cleaned[end_idx + len("</think>") :].strip() if end_idx >= 0 else cleaned[len("</think>") :].strip()

    def _block(text: str) -> str | None:
        start_idx = text.find("{")
        last_close = text.rfind("}")
        if 0 <= start_idx < last_close:
            return text[start_idx : last_close + 1]
        return None

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        block = _block(cleaned)
        if block:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass
    return None


async def derive_first_action(context: FirstActionContext, *, llm_chat: LlmChat) -> dict[str, Any]:
    """Aurora 推导：真实 goal 上下文 → 结构化 Smallest Useful Step（词表校验）.

    任何失败路径都抛 ``FirstActionGenerationError``（retryable=True）——不降级、
    不模板化、不假装成功。
    """
    if not context.goal_title:
        raise FirstActionGenerationError(reason="empty_goal", detail="goal title is empty")
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(context.prompt_bits())},
    ]
    try:
        raw = await llm_chat(messages)
    except Exception as exc:  # noqa: BLE001 — 下游错误统一转为诚实生成失败
        raise FirstActionGenerationError(reason="aurora_unavailable", detail=str(exc)[:300]) from exc

    payload = _extract_json(raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False))
    if not isinstance(payload, dict):
        raise FirstActionGenerationError(reason="aurora_unparseable", detail=str(raw)[:300])

    derived: dict[str, Any] = {}
    for key in ("step_title", "smallest_step", "desired_outcome"):
        value = str(payload.get(key) or "").strip()
        if not value:
            raise FirstActionGenerationError(reason="missing_field", detail=key)
        derived[key] = value[:255]

    evidence_kind = str(payload.get("evidence_kind") or "").strip()
    if evidence_kind not in _VALID_EVIDENCE_KINDS:
        raise FirstActionGenerationError(
            reason="invalid_evidence_kind",
            detail=f"{evidence_kind!r} not in X-01 evidence vocabulary",
        )
    derived["evidence_kind"] = evidence_kind

    reasons_raw = payload.get("useful_because")
    reasons = [str(item).strip() for item in reasons_raw] if isinstance(reasons_raw, list) else []
    reasons = [item for item in reasons if item in USEFUL_STEP_REASONS]
    if not reasons:
        # X-01：空判据 = 伪步骤，契约层拒绝——诚实报错而非补默认
        raise FirstActionGenerationError(
            reason="no_useful_reason",
            detail="useful_because empty or out of vocabulary (伪步骤不合法)",
        )
    derived["useful_because"] = reasons

    mode_suggestion = str(payload.get("suggested_mode") or "").strip().lower()
    derived["suggested_mode"] = mode_suggestion if mode_suggestion in {"human", "agent", "hybrid"} else None

    minutes_raw = payload.get("estimated_minutes")
    try:
        minutes = int(minutes_raw) if minutes_raw is not None else None
    except (TypeError, ValueError):
        minutes = None
    if minutes is not None and not 1 <= minutes <= 600:
        minutes = None
    derived["estimated_minutes"] = minutes
    return derived


def resolve_execution_mode(context: FirstActionContext, derived: dict[str, Any]) -> AllocationDecision:
    """mode 权威 = Aurora 分配策略：LLM 建议只是因子，学习守卫拦全自动."""
    ownership = CognitiveOwnership.USER_CORE.value
    if derived.get("suggested_mode") == "agent" and not (
        set(derived["useful_because"]) & {"builds_capability", "enables_decision"}
    ):
        # LLM 认为可委托且该步不带能力/决策属性 → 机械步骤，允许进入委托判定
        ownership = CognitiveOwnership.DELEGATED.value
    factors = AllocationFactors(
        task_type="LEARNING",
        task_summary=derived["smallest_step"][:300],
        learning_goal=True,
        cognitive_ownership=ownership,
        reversible=True,
        risk_class="low",
        time_pressure="relaxed" if (context.study_minutes or 0) >= 30 else "tight",
    )
    return decide_allocation(factors)


def build_first_action_plan(
    context: FirstActionContext,
    derived: dict[str, Any],
    decision: AllocationDecision,
) -> ActionPlanContract:
    """推导结果 + 分配裁决 → X-01 ActionPlanContract（outcome/evidence/mode 三字段）."""
    contract = ActionPlanContract(
        desired_outcome=derived["desired_outcome"],
        smallest_useful_step=SmallestUsefulStep(
            description=derived["smallest_step"],
            useful_because=tuple(derived["useful_because"]),
        ),
        completion_evidence=(
            CompletionEvidenceSpec(
                evidence_kind=derived["evidence_kind"],
                ref=None,
                description=derived["step_title"],
            ),
        ),
        execution_mode=decision.execution_mode,
        cognitive_ownership=CognitiveOwnership(
            decision.recommended_cognitive_ownership or CognitiveOwnership.USER_CORE.value
        ),
        source_refs=context.source_refs,
        risk_class=None,
        reversible=True,
    )
    violations = contract.validate()
    if violations:
        raise FirstActionGenerationError(reason="plan_invalid", detail="; ".join(violations))
    return contract


# ---------------------------------------------------------------------------
# 环4→6 · Proposal（X-03 统一 command path）→ confirm → Task 持久化
# ---------------------------------------------------------------------------


def _proposal_payload(
    context: FirstActionContext, contract: ActionPlanContract, derived: dict[str, Any]
) -> dict[str, Any]:
    """task.create_batch 的 payload（action_plan 块 = ActionPlanIn 形态）。"""
    plan_block = contract.to_dict()
    plan_block.pop("schema_version", None)  # ActionPlanIn 解析时固定 v1
    task_spec: dict[str, Any] = {
        "title": derived["step_title"],
        "type": "learning",
        "estimated_minutes": derived.get("estimated_minutes"),
        "action_plan": plan_block,
        "success_criteria": derived["desired_outcome"],
    }
    return {"tasks": [task_spec]}


async def propose_first_action(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    llm_chat: LlmChat | None = None,
    idempotency_key: str | None = None,
    session_id: str | None = None,
) -> Any:
    """全链：Context → Aurora → X-03 proposal（PENDING，等确认）.

    ``llm_chat=None``（生产）走 GENERATION/FAST tier 真实模型；失败诚实抛错，
    本函数路径上**零 proposal 落库**。
    """
    context = await collect_first_action_context(db, user_id=user_id)
    if context is None:
        raise NoActiveGoalError()
    chat = llm_chat if llm_chat is not None else _default_llm_chat
    derived = await derive_first_action(context, llm_chat=chat)
    decision = resolve_execution_mode(context, derived)
    contract = build_first_action_plan(context, derived, decision)
    payload = _proposal_payload(context, contract, derived)
    result = await ActionCommandService(db).create_proposal(
        user_id=user_id,
        command_type="task.create_batch",
        payload=payload,
        source=ProposalSource.AURORA.value,
        idempotency_key=idempotency_key,
        summary=f"第一步：{derived['step_title']}（目标：{context.goal_title[:40]}）",
        trace_id=FIRST_ACTION_TRACE_ID,
        session_id=session_id,
    )
    logger.info(
        "first action proposed user={} goal={} proposal={} mode={}",
        user_id,
        context.goal_id,
        result.proposal.id,
        contract.execution_mode.value,
    )
    return result


async def edit_first_action_proposal(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    proposal_id: UUID | str,
    edited_fields: dict[str, Any],
    reason: str | None = None,
    idempotency_key: str | None = None,
) -> Any:
    """编辑面：拒绝旧提案（编辑即 feedback，落 append-only 审计）+ 同链路重提案.

    - 只允许编辑 PENDING 的 first-action proposal（trace 面封闭）；
    - 可改字段封闭（title / estimated_minutes）；合并后过 TaskCreate 全量校验，
      非法值 → CommandValidationError（API 422），不产生半成品；
    - 编辑 delta（edited_fields + 用户理由）作为 user_feedback 持久进旧提案的
      transition + event——「编辑也进入 feedback（不静默丢弃）」。
    """
    illegal = sorted(set(edited_fields) - EDITABLE_FIRST_ACTION_FIELDS)
    if illegal or not edited_fields:
        from app.core.action_command import CommandValidationError

        raise CommandValidationError(
            f"editable fields are {sorted(EDITABLE_FIRST_ACTION_FIELDS)}; got {sorted(edited_fields)}",
            details={"illegal": illegal},
        )

    service = ActionCommandService(db)
    old = await service.get_proposal(proposal_id, user_id=user_id)
    if old.trace_id != FIRST_ACTION_TRACE_ID or old.command_type != "task.create_batch":
        from app.core.action_command import CommandValidationError

        raise CommandValidationError("only first-action create proposals are editable via this surface")
    if ProposalStatus(old.status) is not ProposalStatus.PENDING:
        from app.core.action_command import ProposalNotPendingError

        raise ProposalNotPendingError(
            f"proposal is {old.status} (only PENDING proposals can be edited)",
            details={"status": str(old.status)},
        )

    old_tasks = (old.payload or {}).get("tasks") or []
    old_spec = dict(old_tasks[0]) if old_tasks else {}
    merged_spec = {**old_spec, **edited_fields}
    try:
        TaskCreate(**merged_spec)
    except Exception as exc:  # noqa: BLE001 — pydantic 校验失败统一转显式命令错误
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            from app.core.action_command import CommandValidationError

            raise CommandValidationError(f"invalid edited task spec: {exc.errors()[0].get('msg', 'invalid')}") from exc
        raise

    await service.reject(
        old.id,
        user_id=user_id,
        reason=reason,
        user_feedback={
            "kind": "edit",
            "edited_fields": {key: edited_fields[key] for key in sorted(edited_fields)},
            "reason": (reason or "")[:200] or None,
            "superseded_by": "re-propose",
        },
        idempotency_key=idempotency_key or f"first_action_edit:{old.id}",
    )

    context = await collect_first_action_context(db, user_id=user_id)
    if context is None:
        raise NoActiveGoalError()
    payload = {"tasks": [merged_spec]}
    result = await service.create_proposal(
        user_id=user_id,
        command_type="task.create_batch",
        payload=payload,
        source=ProposalSource.AURORA.value,
        idempotency_key=idempotency_key,
        summary=f"第一步（已按你的编辑调整）：{merged_spec.get('title', '')[:60]}",
        trace_id=FIRST_ACTION_TRACE_ID,
    )
    return result


async def get_first_action_state(db: AsyncSession, *, user_id: UUID | str) -> dict[str, Any]:
    """链路状态读面（重开 App 后的持久化回放：proposal + receipt + 已建任务）."""
    from app.core.action_plan import action_plan_projection

    user_uuid = UUID(str(user_id))
    context = await collect_first_action_context(db, user_id=user_id)
    service = ActionCommandService(db)
    latest = (
        (
            await db.execute(
                select(ActionProposal)
                .where(
                    ActionProposal.user_id == user_uuid,
                    ActionProposal.trace_id == FIRST_ACTION_TRACE_ID,
                    ActionProposal.deleted_at.is_(None),
                )
                .order_by(ActionProposal.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    state: dict[str, Any] = {
        "goal": (
            None
            if context is None
            else {
                "goal_id": str(context.goal_id),
                "title": context.goal_title,
                "goal_type": context.goal_type,
            }
        ),
        "proposal": None,
        "tasks": [],
    }
    if latest is not None:
        projection = service.proposal_projection(latest)
        state["proposal"] = projection
        if ProposalStatus(latest.status) is ProposalStatus.COMMITTED:
            task_ids: list[str] = []
            for effect in (latest.receipt or {}).get("effects") or []:
                refs = effect.get("refs") if isinstance(effect, dict) else None
                for ref in refs or []:
                    if isinstance(ref, str) and ref.startswith("task://"):
                        task_ids.append(ref[len("task://") :])
            if task_ids:
                rows = (
                    (
                        await db.execute(
                            select(Task).where(Task.user_id == user_uuid, Task.id.in_(task_ids))  # type: ignore[attr-defined]
                        )
                    )
                    .scalars()
                    .all()
                )
                state["tasks"] = [
                    {
                        "id": str(task.id),
                        "title": task.title,
                        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                        "action_plan": action_plan_projection(task),
                    }
                    for task in rows
                ]
    return state


# ---------------------------------------------------------------------------
# 生产默认 LLM（与 onboarding preview 同路：GENERATION/FAST tier）
# ---------------------------------------------------------------------------


async def _default_llm_chat(messages: list[dict[str, str]]) -> str:
    import asyncio

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
