"""X-07 · Hybrid Run Steps —— run 内步骤 owner/完成条件契约（stdlib-only 纯函数）.

真源分工（**不建平行真源**）：run 内步骤的持久真源是 ``agent_runs.steps``
（X-05 run 聚合的 JSONB 扩展列，Alembic ``x07_20260921``）；本模块只是该列的
**封闭词表与纯函数契约**（``app/core/action_plan.py`` 对 ``tasks`` V3 列的同款
架构：core 层契约 + 模型列 + 服务层唯一写入权威，X-02/X-05 同款纪律）。

语义真源：``v3/02_core_systems/HUMAN_AGENT_HYBRID.md`` §4——每个 hybrid step
必须有 handoff：``Agent prepares → Human decides/creates → Agent checks →
Outcome``，且「UI 应清楚显示现在轮到谁」。：

- :class:`StepOwner`（AGENT/HUMAN/HYBRID）即「轮到谁」的持久标注；mobile 端
  U-04 ``ProposalTurnOwnership`` 的 wire 词表（"human"/"agent"/"hybrid"）与本
  词表同名对齐——run 投影里的 ``ownership`` 字段让「你做」态可达（解 U-04
  P2：此前 ownership 只能从 authMode 推导，HUMAN 不可达）；
- :class:`StepCompletionKind` 是步骤完成条件 kind 的封闭词表；
- 步骤产物（Agent 准备的 artifacts）以 ``{"scheme", "ref"}`` 引用形式内嵌步骤
  记录（``run.result_ref`` / X-03 proposal receipt / 工具账本等既有机制是
  本体真源，步骤只持引用——C-01 scheme 对齐，不复制本体）；
- 「当前 awaiting step」是**推导态**不是存储态：awaiting = run 处于
  AWAITING_* 且 wait_kind=user_step 时第一个未完成步骤（冷启动/通知重开从
  持久化推导，不依赖内存）；
- 取消/过期零新状态：run 级状态机（``run_state_machine.py``）的
  CANCELLED/TIMED_OUT 封闭图与 wait_expires_at sweep 语义原样覆盖步骤面，
  ``awaiting_step_projection`` 只把终态归因投为步骤可见状态
  （expired/cancelled），供 UI 明确呈现。

本模块 stdlib-only、零 IO、零 import app.*，可被任意层无环引用。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Iterable

__all__ = [
    "RUN_STEPS_CONTRACT_VERSION",
    "StepOwner",
    "StepCompletionKind",
    "StepOwnerVocabulary",
    "StepCompletionKindVocabulary",
    "MAX_RUN_STEPS",
    "MAX_STEP_ARTIFACTS",
    "normalize_run_steps",
    "normalize_artifact_refs",
    "normalize_completion_condition",
    "find_step",
    "first_incomplete_step",
    "completed_steps_count",
    "reconcile_step_counters",
    "awaiting_step_projection",
    "run_steps_wire",
    "step_completion_stamped",
]

#: 契约版本（payload 投影携带；扩词表/扩结构必须 bump 并在冻结测试同步）。
RUN_STEPS_CONTRACT_VERSION = "run_steps.v1"

#: 单 run 步骤数上限（fail-closed 防御性上限；run budget 同风格）。
MAX_RUN_STEPS = 64

#: 单步骤产物引用数上限。
MAX_STEP_ARTIFACTS = 16


class StepOwner(StrEnum):
    """步骤归属（「现在轮到谁」的持久标注；HUMAN_AGENT_HYBRID.md §4）。

    wire 词表与 mobile ``ProposalTurnOwnership``（U-04）同名对齐：
    "human" / "agent" / "hybrid"。
    """

    AGENT = "agent"
    HUMAN = "human"
    HYBRID = "hybrid"


class StepCompletionKind(StrEnum):
    """步骤完成条件 kind（封闭词表；handoff 的完成语义）。

    - ``agent_output``：Agent 产出 artifact 即完成（机械步骤）；
    - ``user_confirmation``：用户确认 Agent 准备的产物（prepare→decide handoff；
      确认动作同时触发 run resume——X-09 幂等键语义，服务端强制）；
    - ``user_edit``：用户编辑/创作内容（decide/create handoff，编辑本体落
      用户输入，引用随 artifacts 持久化）。
    """

    AGENT_OUTPUT = "agent_output"
    USER_CONFIRMATION = "user_confirmation"
    USER_EDIT = "user_edit"


StepOwnerVocabulary: frozenset[str] = frozenset(o.value for o in StepOwner)
StepCompletionKindVocabulary: frozenset[str] = frozenset(k.value for k in StepCompletionKind)


def normalize_artifact_refs(raw: Any) -> list[dict[str, str]]:
    """校验/归一化步骤产物引用列表（fail-closed）。

    canonical 形状：``[{"scheme": <str>, "ref": <str>}, …]``（``run.result_ref``
    与 C-01 source_refs 的 scheme://id 语义；scheme 可为 ``action_proposal``/
    ``tool_call``/``evidence``/``galaxy`` 等既有机制——本体真源留在各机制，
    步骤只持引用）。空/None → []。
    """
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"artifacts must be a list, got {type(raw).__name__}")
    refs: list[dict[str, str]] = []
    for item in raw[:MAX_STEP_ARTIFACTS]:
        if not isinstance(item, dict):
            raise ValueError(f"artifact ref must be a dict, got {type(item).__name__}")
        scheme = str(item.get("scheme") or "").strip()
        ref = str(item.get("ref") or "").strip()
        if not scheme or not ref:
            raise ValueError(f"artifact ref requires non-empty scheme and ref, got {item!r}")
        refs.append({"scheme": scheme[:64], "ref": ref[:255]})
    if len(raw) > MAX_STEP_ARTIFACTS:
        raise ValueError(f"artifacts exceeds {MAX_STEP_ARTIFACTS} refs per step")
    return refs


def normalize_completion_condition(raw: Any) -> dict[str, Any]:
    """校验/归一化步骤完成条件（fail-closed）。

    canonical 形状：``{"kind": <StepCompletionKind>, "description"?: <str>}``。
    """
    if not isinstance(raw, dict):
        raise ValueError(f"completion_condition must be a dict, got {type(raw).__name__}")
    unknown = set(raw) - {"kind", "description"}
    if unknown:
        raise ValueError(f"unknown completion_condition keys {sorted(unknown)} (allowed: kind, description)")
    kind = str(raw.get("kind") or "").strip()
    if kind not in StepCompletionKindVocabulary:
        raise ValueError(f"completion kind {kind!r} out of vocabulary (closed: {sorted(StepCompletionKindVocabulary)})")
    condition: dict[str, Any] = {"kind": kind}
    description = raw.get("description")
    if description:
        condition["description"] = str(description)[:255]
    return condition


def normalize_run_steps(raw: Any) -> list[dict[str, Any]]:
    """校验/归一化 run 步骤计划（fail-closed；写入前唯一入口）。

    canonical 形状（按 ordinal 升序存储）::

        [{"step_id": str(1..64), "ordinal": int(1..1000), "label"?: str(≤64),
          "owner": "agent"|"human"|"hybrid",
          "completion_condition": {"kind": …, "description"?},
          "artifacts"?: [{"scheme","ref"}]}]

    step_id/ordinal 全局唯一；owner 与完成条件 kind 越表即 ValueError。
    """
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"steps must be a list, got {type(raw).__name__}")
    if len(raw) > MAX_RUN_STEPS:
        raise ValueError(f"steps exceeds {MAX_RUN_STEPS} entries per run")

    seen_ids: set[str] = set()
    seen_ordinals: set[int] = set()
    steps: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"step must be a dict, got {type(item).__name__}")
        unknown = set(item) - {"step_id", "ordinal", "label", "owner", "completion_condition", "artifacts"}
        if unknown:
            raise ValueError(f"unknown step keys {sorted(unknown)}")
        step_id = str(item.get("step_id") or "").strip()
        if not step_id or len(step_id) > 64:
            raise ValueError(f"step_id must be a non-empty string ≤64 chars, got {item.get('step_id')!r}")
        if step_id in seen_ids:
            raise ValueError(f"duplicate step_id {step_id!r}")
        seen_ids.add(step_id)
        ordinal_raw = item.get("ordinal")
        if isinstance(ordinal_raw, bool) or not isinstance(ordinal_raw, int) or not 1 <= ordinal_raw <= 1000:
            raise ValueError(f"step {step_id!r} ordinal must be int in [1,1000], got {ordinal_raw!r}")
        if ordinal_raw in seen_ordinals:
            raise ValueError(f"duplicate step ordinal {ordinal_raw}")
        seen_ordinals.add(ordinal_raw)
        owner = str(item.get("owner") or "").strip()
        if owner not in StepOwnerVocabulary:
            raise ValueError(
                f"step {step_id!r} owner {owner!r} out of vocabulary (closed: {sorted(StepOwnerVocabulary)})"
            )
        step: dict[str, Any] = {
            "step_id": step_id,
            "ordinal": ordinal_raw,
            "owner": owner,
            "completion_condition": normalize_completion_condition(item.get("completion_condition")),
        }
        label = str(item.get("label") or "").strip()
        if label:
            step["label"] = label[:64]
        artifacts = item.get("artifacts")
        if artifacts:
            step["artifacts"] = normalize_artifact_refs(artifacts)
        steps.append(step)
    return sorted(steps, key=lambda s: s["ordinal"])


def find_step(steps: Iterable[dict[str, Any]], step_id: str) -> dict[str, Any] | None:
    """按 step_id 查找（steps 已归一化时线性查找；纯读）。"""
    wanted = str(step_id).strip()
    for step in steps or []:
        if step.get("step_id") == wanted:
            return step
    return None


def first_incomplete_step(steps: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """第一个未完成步骤（ordinal 升序；「现在轮到谁」的推导依据）。"""
    for step in steps or []:
        if not step.get("completion"):
            return step
    return None


def completed_steps_count(steps: Iterable[dict[str, Any]] | None) -> int:
    """已完成步骤数（``completion`` 戳计数；纯读）。"""
    return sum(1 for step in steps or [] if step.get("completion"))


def reconcile_step_counters(
    *,
    steps_done: int | None,
    steps_total: int | None,
    steps: Iterable[dict[str, Any]] | None,
) -> tuple[int, int | None]:
    """X-07 P2-1 · 双计数统一——steps 计划 completion 戳为真源的计数派生.

    债项：``steps_done/steps_total``（X-05 单调计数）与 ``steps`` 计划的
    completion 戳（X-07）双计数并存，两处进度可能不同步。本函数是**唯一
    派生逻辑**（读面 ``to_dict`` 与服务层写点共用）：

    - **无计划**（``steps`` 空）：原值透传——X-05 execution 轨道（里程碑
      ``record_step`` 序号语义）零改动；
    - **有计划**：
      - ``steps_done = max(存储值, completed_steps_count(steps))``——计划
        completion 戳是进度的下界真源；``max`` 是**单调兜底**：派生只升不
        降，X-05「steps_done 不得倒退」语义原样保留（先经序号推进、后补
        计划的混合历史行不被拉回）；
      - ``steps_total = len(steps)``——计划只定义一次、长度不变（first-win
        冲突拒绝），故计划长度即步骤总数的真源；显式传入的 ``steps_total``
        （里程碑词表计数）在有计划时被收口，UI 两处进度不再分叉。

    纯函数、零 IO；返回 ``(steps_done, steps_total)`` 派生值，字段名与形状
    由调用方保持不变（移动端 ``agent_run_read_service`` 兼容面零改动）。
    """
    plan = list(steps or [])
    if not plan:
        return int(steps_done or 0), steps_total
    derived_done = max(int(steps_done or 0), completed_steps_count(plan))
    return derived_done, len(plan)


def step_completion_stamped(
    steps: Iterable[dict[str, Any]],
    *,
    step_id: str,
    completed_by: str,
    idempotency_key: str,
    action: str | None = None,
    artifact_refs: list[dict[str, str]] | None = None,
    note: str | None = None,
    completed_at: str,
) -> tuple[list[dict[str, Any]], bool]:
    """在步骤上盖完成戳（纯函数；返回新列表 + 是否实际落戳）。

    幂等语义（卡面灵魂：「用户操作两次不会 resume 两次」）：步骤已带完成戳时
    **无论 key 是否相同一律 no-op**（first-wins：同一步骤的用户操作恰记录
    一次；重放/双击/换 key 重发都收敛到第一次），由调用方据此跳过 resume。
    """
    steps = list(steps or [])
    for index, step in enumerate(steps):
        if step.get("step_id") != str(step_id).strip():
            continue
        if step.get("completion"):
            return steps, False
        stamped = dict(step)
        completion: dict[str, Any] = {
            "by": str(completed_by)[:32],
            "idempotency_key": str(idempotency_key)[:255],
            "completed_at": completed_at,
        }
        if action:
            completion["action"] = str(action)[:32]
        if note:
            completion["note"] = str(note)[:500]
        if artifact_refs:
            completion["artifacts"] = normalize_artifact_refs(artifact_refs)
        stamped["completion"] = completion
        steps[index] = stamped
        return steps, True
    return steps, False


def awaiting_step_projection(
    *,
    run_status: str | None,
    wait_kind: str | None,
    terminal_reason: str | None,
    wait_expires_at: Any,
    steps: Iterable[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """从持久化状态推导「当前 awaiting step」的只读投影（冷启动可推导）。

    返回 None（当前没有等待用户的步骤面）或::

        {"step_id", "ordinal", "label"?, "owner", "ownership", "state",
         "completion_condition", "artifacts"?, "prompt"?, "expires_at"?}

    ``state``（明确取消/过期，acceptance ②）：
    - ``"awaiting"``：run AWAITING_* 且 wait_kind=user_step，等待中；
    - ``"expired"``：run TIMED_OUT(wait_expired)——等待窗口已过，明确过期；
    - ``"cancelled"``：run CANCELLED(user_cancelled)——用户显式取消；
    - 其余（活跃执行态/其他终态）→ None（进度面由 steps 列表呈现）。
    """
    status = str(run_status or "").strip().upper()
    step = first_incomplete_step(steps or [])
    if step is None:
        return None

    state: str | None = None
    if status in ("AWAITING_USER", "AWAITING_APPROVAL") and str(wait_kind or "") == "user_step":
        state = "awaiting"
    elif status == "TIMED_OUT" and str(terminal_reason or "") == "wait_expired":
        state = "expired"
    elif status == "CANCELLED" and str(terminal_reason or "") == "user_cancelled":
        state = "cancelled"
    if state is None:
        return None

    raw_awaiting = step.get("awaiting")
    awaiting: dict[str, Any] = raw_awaiting if isinstance(raw_awaiting, dict) else {}
    projection: dict[str, Any] = {
        "schema_version": RUN_STEPS_CONTRACT_VERSION,
        "step_id": step.get("step_id"),
        "ordinal": step.get("ordinal"),
        "owner": step.get("owner"),
        "ownership": step.get("owner"),  # U-04 wire 词表同名（human/agent/hybrid）
        "state": state,
        "completion_condition": step.get("completion_condition") or {},
    }
    if step.get("label"):
        projection["label"] = step.get("label")
    if awaiting.get("prompt"):
        projection["prompt"] = awaiting.get("prompt")
    artifacts = step.get("artifacts") or awaiting.get("artifacts") or []
    if artifacts:
        projection["artifacts"] = artifacts
    if state == "awaiting" and wait_expires_at is not None:
        projection["expires_at"] = getattr(wait_expires_at, "isoformat", lambda: str(wait_expires_at))()
    return projection


def run_steps_wire(steps: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """``agent_runs.steps`` → 只读 wire 投影（UI/网关透传面）。"""
    wire: list[dict[str, Any]] = []
    for step in steps or []:
        completion = step.get("completion") if isinstance(step.get("completion"), dict) else None
        entry: dict[str, Any] = {
            "step_id": step.get("step_id"),
            "ordinal": step.get("ordinal"),
            "owner": step.get("owner"),
            "ownership": step.get("owner"),
            "completion_condition": step.get("completion_condition") or {},
            "completed": completion is not None,
        }
        if step.get("label"):
            entry["label"] = step.get("label")
        if step.get("artifacts"):
            entry["artifacts"] = step.get("artifacts")
        if step.get("awaiting"):
            entry["awaiting"] = step.get("awaiting")
        if completion:
            entry["completion"] = completion
        wire.append(entry)
    return wire
