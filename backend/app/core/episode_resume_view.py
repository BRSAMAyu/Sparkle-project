"""V4-I01 · EpisodeResumeView ``episode_resume_view.v1`` —— 目标 Episode 接续读模型契约。

冻结来源（V4-B05 合同 §5 + §4 why_now 字段位；卡 V4-I01，locks: episode-view）：
- **它是读模型，绝非另一份主任务**：原 goal/task/run 状态始终优先
  （ARCHITECTURE_DELTA §新契约最小面 2 原文）。本模块零写路径、零新表、
  零模型调用——全部字段都是既有权威行的**读面投影**。
- **数据源只接既有权威**（B05 §1 映射表，复用不复制）：
    - goal/task/run 行：``goals``/``tasks``/``agent_runs``（X-05 run 唯一持久真源）；
    - ``last_valid_outcome.truth_class``：D-02 ``TruthClass`` **全 5 值 1:1**
      （demo 行透传不排除，R1-C4 修订；呈现端对 demo 显式标注，永不进成功面）；
    - ``pending_human_step`` 词表：X-01 ``CognitiveOwnership`` + ``ExecutionMode``，
      import 不复制；步描述取 ActionPlan ``smallest_useful_step``（经统一读侧门）；
    - ``version_token``：复用 X-03 ``action_command.version_token``（updated_at 令牌）；
    - ``freshness.memory_epoch_at_compute``：C-07/M-07 memory epoch 契约；
    - ``why_now``：``action_plan.v1.1`` 字段位（B05 §4）的投影——**v1 行 = null**，
      不臆测回填；子结构校验失败走字段级降级（仅 why_now 置 null + WARN，
      §4.1），不影响视图其余字段；过期 why-now 不得当作当前原因复用（§4）。
- **expires_at 过期语义**（§5 + §9 反例）：过期视图只允许「说明不确定性」，
  不允许静默续跑旧授权、不强行接续、后台任务不复活。本模块把「过期」做成
  可判定的纯函数（:func:`resume_view_stale_reason`），消费方据此退回明确校准。
- **无历史不造分数**（MASTER_DESIGN §6）：视图字段集封闭，不存在
  进度/精通/「练了 N 分钟」类字段；``last_valid_outcome=null`` 就是 null。

本模块为核心契约层：封闭词表 + 纯函数装配 + 结构冻结检查，零 IO（与
``run_steps.py`` 同风格；IO 聚合在 ``app/services/episode_resume_service.py``）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES
from app.core.outcome_ledger import TruthClass

EPISODE_RESUME_VIEW_SCHEMA_VERSION = "episode_resume_view.v1"

#: ``freshness.context_receipt_ref`` 的封闭 scheme（B05 §5：绑定本轮
#: ContextSelectionReceipt；receipt 本体契约归 V4-B05 §2 / 后续实现卡，本卡只绑 ref）。
CONTEXT_SELECTION_REF_SCHEME = "context_selection"

#: step_ref 允许的封闭 scheme（B05 §5：``task|subtask scheme``，其余一律拒）。
STEP_REF_SCHEMES: frozenset[str] = frozenset({"task", "subtask"})

#: ``why_now.confidence_band`` 封闭词表（B05 §4 R1-C2 修订冻结四值；审慎标签，
#: 不向用户显示虚构精度百分比）。
WHY_NOW_CONFIDENCE_BANDS: frozenset[str] = frozenset({"high", "medium", "low", "unknown"})

#: D-02 ``TruthClass`` 全 5 值 1:1 复用（R1-C4：demo 透传不排除，fail-closed 不吞合法账本行）。
TRUTH_CLASS_VALUES: frozenset[str] = frozenset(member.value for member in TruthClass)

#: 聚合器的类型化降级词表（封闭；扩展需过 reviewer）。每个值都是「退回明确校准」
#: 的机器可读出口——视图不出，消费方拿到原因，不拿半真视图。
RESUME_DEGRADE_REASONS: frozenset[str] = frozenset(
    {
        "object_not_found",  # task/goal/plan 行不存在或已软删——已删对象不复活
        "cross_object_access",  # 行存在但属主非当前用户（I3：拒绝 + 安全遥测日志）
        "goal_unresolved",  # task 无可达 goal 权威（无 plan / plan 无 goal_id）
        "goal_changed_requires_calibration",  # goal 终态或计划绑定 goal 不一致——旧计划不强推
        "context_receipt_missing",  # 无本轮 ContextSelectionReceipt ref（§2：resume view 返回之前必有 receipt）
    }
)

#: 视图冻结字段集（B05 §5 全字段 + ``why_now`` 字段位投影，见模块 docstring 增量声明）。
#: why_now 为必选=false 的追加位：缺省恒以 null 补位（v1 行语义，§4.1），旧客户端
#: 忽略未知可选字段（§8 双读纪律）。结构检查据此钉死，消费方不得依赖其他键。
RESUME_VIEW_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "goal_ref",
        "task_ref",
        "run_ref",
        "last_valid_outcome",
        "last_confirmed_step",
        "pending_human_step",
        "why_now",
        "expires_at",
        "freshness",
    }
)

_WHY_NOW_MAX_STATEMENT = 200


def _ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


def _iso(value: datetime | None) -> str | None:
    """naive-UTC 规范时刻 → ISO 串（秒精度；None 透传）。"""
    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# why_now（action_plan.v1.1 字段位的读面投影，B05 §4 / §4.1）
# ---------------------------------------------------------------------------


def normalize_why_now(raw: Any, *, now: datetime) -> tuple[dict[str, Any] | None, str | None]:
    """why_now 子结构读侧门（§4.1 字段级降级的判定函数）。

    返回 ``(payload, degrade_reason)``：
    - raw 为 None（v1 行无该字段位）→ ``(None, None)``——**正常态，非降级**
      （v1 行 = why_now null，不臆测回填）；
    - 子结构任一校验失败 → ``(None, "<原因>")``——字段级降级：调用方仅将
      why_now 置 null 并 WARN（带 task_id 与原因），视图其余字段不受影响；
    - ``expires_at`` 非空且 ≤ now → ``(None, "why_now_expired")``——过期
      why-now 不得当作当前原因复用（§4：过期后呈现「当时的原因」属呈现层
      历史面，不进本视图的当前位）。

    payload 形状（封闭）::

        {"statement": str(≤200), "basis_refs": [closed-scheme ref, ≥1],
         "expires_at": iso|None, "confidence_band": high|medium|low|unknown}
    """
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        return None, "why_now_not_object"
    unknown = set(raw) - {"statement", "basis_refs", "expires_at", "confidence_band"}
    if unknown:
        return None, f"why_now_unknown_keys:{sorted(unknown)!r}"
    statement = raw.get("statement")
    if not isinstance(statement, str) or not statement.strip() or len(statement) > _WHY_NOW_MAX_STATEMENT:
        return None, "why_now_statement_invalid"
    basis_refs_raw = raw.get("basis_refs")
    if not isinstance(basis_refs_raw, (list, tuple)) or not basis_refs_raw:
        # 无依据的 why-now = 伪依据（§4：同 USEFUL_STEP_REASONS 空集=伪步骤纪律）
        return None, "why_now_basis_refs_empty"
    basis_refs: list[str] = []
    for ref in basis_refs_raw:
        if not isinstance(ref, str) or _ref_scheme(ref) not in ACTION_SOURCE_REF_SCHEMES:
            return None, f"why_now_basis_ref_unknown_scheme:{ref!r}"
        basis_refs.append(ref)
    band = raw.get("confidence_band")
    if band not in WHY_NOW_CONFIDENCE_BANDS:
        return None, f"why_now_confidence_band_invalid:{band!r}"
    expires_raw = raw.get("expires_at")
    expires_at: datetime | None = None
    if expires_raw is not None:
        if not isinstance(expires_raw, datetime):
            return None, "why_now_expires_at_invalid"
        expires_at = expires_raw.replace(tzinfo=None)
        if expires_at <= now.replace(tzinfo=None):
            return None, "why_now_expired"
    return (
        {
            "statement": statement,
            "basis_refs": list(basis_refs),
            "expires_at": _iso(expires_at),
            "confidence_band": band,
        },
        None,
    )


# ---------------------------------------------------------------------------
# 视图装配（纯函数；输入为已解析的权威值，零 IO）
# ---------------------------------------------------------------------------


def assemble_resume_view(
    *,
    goal_id: str,
    task_id: str,
    run_id: str | None,
    last_outcome: dict[str, Any] | None,
    last_step: dict[str, Any] | None,
    pending_step: dict[str, Any] | None,
    why_now: dict[str, Any] | None,
    computed_at: datetime,
    expires_at: datetime,
    context_receipt_ref: str,
    memory_epoch: int,
) -> dict[str, Any]:
    """从已解析权威值装配 ``episode_resume_view.v1`` payload（封闭结构）。

    任何部件形状不合法（scheme 越界 / truth_class 越界 / ref 缺 scheme）抛
    ``ValueError``——聚合器输入错误必须 fail-loud，不得静默投影成半真视图
    （对齐 B05 §0 封闭词表纪律）。
    """
    if not goal_id:
        raise ValueError(f"goal_ref requires non-empty goal id, got {goal_id!r}")
    if not task_id:
        raise ValueError(f"task_ref requires non-empty task id, got {task_id!r}")
    if _ref_scheme(context_receipt_ref) != CONTEXT_SELECTION_REF_SCHEME:
        raise ValueError(
            f"context_receipt_ref scheme must be {CONTEXT_SELECTION_REF_SCHEME!r}, got {context_receipt_ref!r}"
        )
    if not isinstance(memory_epoch, int) or isinstance(memory_epoch, bool) or memory_epoch < 0:
        raise ValueError(f"memory_epoch must be non-negative int, got {memory_epoch!r}")
    if expires_at.replace(tzinfo=None) <= computed_at.replace(tzinfo=None):
        raise ValueError("expires_at must be after computed_at")

    outcome_payload: dict[str, Any] | None = None
    if last_outcome is not None:
        outcome_id = str(last_outcome.get("outcome_id") or "")
        truth_class = last_outcome.get("truth_class")
        if not outcome_id:
            raise ValueError("last_outcome.outcome_id must be non-empty")
        if truth_class not in TRUTH_CLASS_VALUES:
            # R1-C4：全 5 值 1:1（含 demo 透传）；词表外值拒绝，不静默吞
            raise ValueError(f"last_outcome.truth_class {truth_class!r} out of TruthClass vocabulary")
        outcome_payload = {
            "outcome_ref": f"outcome://{outcome_id}",
            "truth_class": truth_class,
            "recorded_at": _iso(last_outcome.get("recorded_at")),
        }

    step_payload: dict[str, Any] | None = None
    if last_step is not None:
        step_ref = str(last_step.get("step_ref") or "")
        scheme, _, ref_id = step_ref.partition("://")
        if scheme not in STEP_REF_SCHEMES or not ref_id:
            raise ValueError(
                f"last_step.step_ref must be <scheme>://<non-empty id> with scheme in {sorted(STEP_REF_SCHEMES)}, got {step_ref!r}"
            )
        description = str(last_step.get("description") or "")
        if not description:
            raise ValueError("last_step.description must be non-empty")
        version_token = last_step.get("version_token")
        if version_token is not None and not isinstance(version_token, str):
            raise ValueError(f"last_step.version_token must be str|None, got {version_token!r}")
        step_payload = {
            "step_ref": step_ref,
            "description": description,
            "confirmed_at": _iso(last_step.get("confirmed_at")),
            "version_token": version_token,
        }

    pending_payload: dict[str, Any] | None = None
    if pending_step is not None:
        pending_description = str(pending_step.get("description") or "")
        if not pending_description:
            raise ValueError("pending_step.description must be non-empty")
        pending_payload = {
            "description": pending_description,
            "cognitive_ownership": pending_step.get("cognitive_ownership"),
            "execution_mode": pending_step.get("execution_mode"),
        }

    return {
        "schema_version": EPISODE_RESUME_VIEW_SCHEMA_VERSION,
        "goal_ref": f"goal://{goal_id}",
        "task_ref": f"task://{task_id}",
        "run_ref": f"run://{run_id}" if run_id else None,
        "last_valid_outcome": outcome_payload,
        "last_confirmed_step": step_payload,
        "pending_human_step": pending_payload,
        "why_now": why_now,
        "expires_at": _iso(expires_at),
        "freshness": {
            "context_receipt_ref": context_receipt_ref,
            "computed_at": _iso(computed_at),
            "memory_epoch_at_compute": int(memory_epoch),
        },
    }


def validate_resume_view_shape(payload: Any) -> tuple[str, ...]:
    """冻结结构检查：键集恰为 :data:`RESUME_VIEW_FIELDS`、版本常量、freshness 三键。

    供服务层防御与契约测试共用；结构漂移在此 fail（封闭结构 + 测试钉死纪律）。
    """
    violations: list[str] = []
    if not isinstance(payload, dict):
        return (f"resume view payload must be dict, got {type(payload).__name__}",)
    missing = RESUME_VIEW_FIELDS - set(payload)
    extra = set(payload) - RESUME_VIEW_FIELDS
    if missing:
        violations.append(f"missing fields: {sorted(missing)}")
    if extra:
        violations.append(f"unknown fields: {sorted(extra)}")
    if payload.get("schema_version") != EPISODE_RESUME_VIEW_SCHEMA_VERSION:
        violations.append(f"schema_version must be {EPISODE_RESUME_VIEW_SCHEMA_VERSION!r}")
    freshness = payload.get("freshness")
    if freshness is not None:
        if not isinstance(freshness, dict):
            violations.append("freshness must be dict")
        else:
            freshness_keys = {"context_receipt_ref", "computed_at", "memory_epoch_at_compute"}
            if set(freshness) != freshness_keys:
                violations.append(f"freshness keys must be exactly {sorted(freshness_keys)}")
    return tuple(violations)


# ---------------------------------------------------------------------------
# 过期 / 陈旧判定（expires_at 过期语义的可判定出口；§5 + §9 反例钉死）
# ---------------------------------------------------------------------------


def resume_view_stale_reason(
    view: dict[str, Any],
    *,
    now: datetime,
    current_memory_epoch: int | None = None,
) -> str | None:
    """视图陈旧判定：返回 None = 仍新鲜；否则给出封闭原因串。

    - ``"expires_at_passed"``——视图过期：消费方只允许呈现不确定性说明、退回
      明确校准；**不得**静默接续、不得复活后台任务（§9：过期 EpisodeResumeView
      自动接续 = 反例）。
    - ``"memory_epoch_changed"``——C-07：删除/纠正/权限收紧 bump epoch 后，
      计算时钉住的 epoch 已变 → 视图 stale，必须重算（§5 freshness 语义）。
    """
    if not isinstance(view, dict):
        return "expires_at_passed"
    expires_raw = view.get("expires_at")
    if isinstance(expires_raw, str):
        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            return "expires_at_passed"
        if now.replace(tzinfo=None) >= expires_at:
            return "expires_at_passed"
    elif expires_raw is None:
        return "expires_at_passed"
    epoch_at_compute = (view.get("freshness") or {}).get("memory_epoch_at_compute")
    if current_memory_epoch is not None and epoch_at_compute is not None:
        try:
            if int(epoch_at_compute) != int(current_memory_epoch):
                return "memory_epoch_changed"
        except (TypeError, ValueError):
            return "memory_epoch_changed"
    return None


__all__ = [
    "CONTEXT_SELECTION_REF_SCHEME",
    "EPISODE_RESUME_VIEW_SCHEMA_VERSION",
    "RESUME_DEGRADE_REASONS",
    "RESUME_VIEW_FIELDS",
    "STEP_REF_SCHEMES",
    "TRUTH_CLASS_VALUES",
    "WHY_NOW_CONFIDENCE_BANDS",
    "assemble_resume_view",
    "normalize_why_now",
    "resume_view_stale_reason",
    "validate_resume_view_shape",
]
