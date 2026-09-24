"""X-09 · Agent Failure Semantics —— 失败/取消/未知结局的确定性分类与重试策略.

契约真源（v3/02_core_systems/AGENT_RUNTIME.md §5 Recovery / §6 Cancellation +
v3/07_tasks/cards/X-09.md 工作项 1/5）：

    三族（failure 细分为 retryable/permanent）：
    - RETRYABLE_FAILURE —— 暂态执行失败（超时/网络/暂时异常），且失败调用
      **无可疑 side effect**（账本已随事务回滚）→ 指数退避重试；
    - PERMANENT_FAILURE —— 确定性失败（权限/参数/未知工具/幂等冲突/预算超限），
      重试不能改变结局 → 直接终态（死信）；
    - USER_CANCELLED —— 用户语义取消 → CANCELLED(user_cancelled)；
    - UNKNOWN_OUTCOME —— 进程崩溃/中断落进 side-effect 调用中间，效果无法
      核实（账本残留 in_progress/interrupted）→ 绝不自动重驱动，绝不假装
      成功或失败（false success=0 的机制根源）。

设计（对齐 run_state_machine.py 的 core 层风格）：

- 本模块 stdlib-only + 仅 import ``app.core.run_state_machine``（同为 stdlib-only），
  零 IO、可被任意层无环引用；
- :func:`classify_execution_failure` 是**纯函数**：输入只有结构化信号
  （failure_kind / tool_effect / side_effect_state / 账本状态），**同类输入恒同
  输出**——不含时间、随机数、LLM 判断（acceptance「三族分类器确定性」）；
- 归因词表 :data:`FAILURE_ATTRIBUTIONS` 封闭（run.error_category 的取值域），
  与 frozen :data:`terminal_reason_vocabulary` 的映射表
  :data:`FAILURE_KIND_TO_TERMINAL` 一并 sha256 冻结（变异必红锚点）；
- 重试策略 :func:`retry_backoff_delay` / :func:`retry_decision` 同为纯函数：
  指数退避（base·2^(attempt-1)，封顶 max_delay，无抖动——确定性优先），
  超过 :data:`DEFAULT_MAX_RETRY_ATTEMPTS` 即死信（run 落明确终态，不再重试）。

与既有真源的关系（不重建）：

- run 终态/迁移边零改动：全部落 X-05 封闭迁移图既有边；terminal_reason 只用
  既有词（无新词；``UNKNOWN_OUTCOME`` 的中断归因复用 ``worker_restart_orphan``，
  精确成因记录在 transition details / error_category，见 REPORT 声明）；
- ExecutionIntent 协议状态机零改动；X-06 账本状态词表由 X-09 增补
  ``interrupted``（agent_tool_call.py 内应用层词表，非 event 词表）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from app.core.run_state_machine import RunStatus, is_terminal_run_status

__all__ = [
    "FAILURE_SEMANTICS_VERSION",
    "FailureFamily",
    "FailureKind",
    "FAILURE_ATTRIBUTIONS",
    "SIDE_EFFECT_STATES",
    "FailureClassification",
    "classify_execution_failure",
    "FAILURE_KIND_TO_TERMINAL",
    "FAILURE_TABLE_SHA256",
    "terminal_for_failure_kind",
    "retry_backoff_delay",
    "retry_decision",
    "is_legal_failure_terminal",
    "DEFAULT_RETRY_BASE_DELAY_SECONDS",
    "DEFAULT_RETRY_MAX_DELAY_SECONDS",
    "DEFAULT_MAX_RETRY_ATTEMPTS",
]

#: 失败语义契约版本（扩 failure_kind / 归因词 / 映射表需 bump 并过两位 reviewer）。
#: ``failure_semantics.v1``（X-09）：三族分类器 + 18 个结构化 failure_kind +
#: 指数退避重试策略。
FAILURE_SEMANTICS_VERSION = "failure_semantics.v1"


class FailureFamily(StrEnum):
    """失败三族（failure 细分 retryable/permanent；AGENT_RUNTIME §5/§6）."""

    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    USER_CANCELLED = "user_cancelled"
    UNKNOWN_OUTCOME = "unknown_outcome"


#: 归因封闭词表（run.error_category / 审计 details 的取值域；卡面工作项 1）。
FAILURE_ATTRIBUTIONS: frozenset[str] = frozenset(f.value for f in FailureFamily)


class FailureKind(StrEnum):
    """结构化失败信号封闭词表（executor/恢复路径可确定性产出的全部成因）.

    分类器的**唯一**成因输入——错误字符串归并到此词表是调用方的确定性映射
    （如 executor 的 TimeoutError → tool_timeout），分类器不再做字符串猜测。
    """

    # --- 用户语义 ---
    USER_CANCELLED = "user_cancelled"
    # --- 确定性失败（重试无意义）---
    BUDGET_EXCEEDED = "budget_exceeded"
    PERMISSION_DENIED = "permission_denied"
    NOT_IN_ALLOWED_TOOLS = "not_in_allowed_tools"
    UNKNOWN_TOOL = "unknown_tool"
    VALIDATION_ERROR = "validation_error"
    CONFIRMATION_REQUIRED = "confirmation_required"
    IDEMPOTENCY_KEY_REQUIRED = "idempotency_key_required"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    IDEMPOTENCY_ARGS_MISMATCH = "idempotency_args_mismatch"
    # --- 暂态失败（无残留 side effect 时可重试）---
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_EXCEPTION = "tool_exception"
    TOOL_REPORTED_FAILURE = "tool_reported_failure"
    NETWORK_UNREACHABLE = "network_unreachable"
    # --- 中断/未知（side effect 无法核实）---
    IDEMPOTENCY_INTERRUPTED = "idempotency_interrupted"  # 账本行 interrupted（前次调用结局未知）
    WORKER_CRASH_ORPHAN = "worker_crash_orphan"  # 恢复路径发现 in-flight 孤儿
    # --- 系统/队列超时（run 级时间裁决，非工具失败）---
    WAIT_EXPIRED = "wait_expired"
    QUEUE_STALE = "queue_stale"


#: side effect 状态封闭词表（分类输入；账本证据的确定性归并）：
#: - ``none``：失败调用的账本行随事务回滚（无任何持久效果残留）；
#: - ``unknown``：账本行残留（in_progress 提前落库/已判 interrupted）——效果
#:   可能已部分发生，不可核实；
#: - ``confirmed``：账本行已收敛 succeeded（效果确认已发生）。
SIDE_EFFECT_STATES: frozenset[str] = frozenset({"none", "unknown", "confirmed"})


@dataclass(frozen=True)
class FailureClassification:
    """一次失败的确定性裁决（纯数据）.

    - ``run_terminal_status`` / ``terminal_reason``：run 状态机合法终态映射
      （全部为 X-05 既有边/既有 reason 词）；
    - ``error_category``：归因（:data:`FAILURE_ATTRIBUTIONS`）；
    - ``retryable``：本次失败是否允许自动重试（attempt < max 时）；
    - ``retry_delay_seconds``：下一次重试的退避时长（不可重试为 None）；
    - ``side_effect_state``：失败调用的 side effect 证据（审计透传）。
    """

    failure_kind: str
    family: FailureFamily
    run_terminal_status: RunStatus
    terminal_reason: str | None
    error_category: str
    retryable: bool
    side_effect_state: str | None = None
    retry_delay_seconds: float | None = None
    retry_requires_new_key: bool = False  # unknown 族：重试必须换新幂等键（防重复 side effect）


#: failure_kind → (run 终态, terminal_reason) 基表（无 side effect 修正前的缺省）。
#: 全部为 X-05 封闭图**既有**边（ACTIVE → 目标终态）与既有 terminal_reason 词。
_FAILURE_KIND_BASE_TABLE: dict[FailureKind, tuple[RunStatus, str]] = {
    FailureKind.USER_CANCELLED: (RunStatus.CANCELLED, "user_cancelled"),
    FailureKind.BUDGET_EXCEEDED: (RunStatus.BUDGET_EXCEEDED, "budget_exceeded"),
    FailureKind.PERMISSION_DENIED: (RunStatus.FAILED, "rejected"),
    FailureKind.NOT_IN_ALLOWED_TOOLS: (RunStatus.FAILED, "rejected"),
    FailureKind.UNKNOWN_TOOL: (RunStatus.FAILED, "failed"),
    FailureKind.VALIDATION_ERROR: (RunStatus.FAILED, "failed"),
    FailureKind.CONFIRMATION_REQUIRED: (RunStatus.FAILED, "rejected"),
    FailureKind.IDEMPOTENCY_KEY_REQUIRED: (RunStatus.FAILED, "rejected"),
    FailureKind.IDEMPOTENCY_CONFLICT: (RunStatus.FAILED, "failed"),
    FailureKind.IDEMPOTENCY_ARGS_MISMATCH: (RunStatus.FAILED, "failed"),
    FailureKind.IDEMPOTENCY_INTERRUPTED: (RunStatus.UNKNOWN_OUTCOME, "worker_restart_orphan"),
    FailureKind.WORKER_CRASH_ORPHAN: (RunStatus.UNKNOWN_OUTCOME, "worker_restart_orphan"),
    FailureKind.TOOL_TIMEOUT: (RunStatus.FAILED, "failed"),
    FailureKind.TOOL_EXCEPTION: (RunStatus.FAILED, "failed"),
    FailureKind.TOOL_REPORTED_FAILURE: (RunStatus.FAILED, "failed"),
    FailureKind.NETWORK_UNREACHABLE: (RunStatus.FAILED, "failed"),
    FailureKind.WAIT_EXPIRED: (RunStatus.TIMED_OUT, "wait_expired"),
    FailureKind.QUEUE_STALE: (RunStatus.CANCELLED, "queue_stale"),
}

#: 不可重试族（确定性成因；PERMANENT/USER_CANCELLED/UNKNOWN/WAIT/QUEUE）。
_NON_RETRYABLE_KINDS: frozenset[FailureKind] = frozenset(
    {
        FailureKind.USER_CANCELLED,
        FailureKind.BUDGET_EXCEEDED,
        FailureKind.PERMISSION_DENIED,
        FailureKind.NOT_IN_ALLOWED_TOOLS,
        FailureKind.UNKNOWN_TOOL,
        FailureKind.VALIDATION_ERROR,
        FailureKind.CONFIRMATION_REQUIRED,
        FailureKind.IDEMPOTENCY_KEY_REQUIRED,
        FailureKind.IDEMPOTENCY_CONFLICT,
        FailureKind.IDEMPOTENCY_ARGS_MISMATCH,
        FailureKind.IDEMPOTENCY_INTERRUPTED,
        FailureKind.WORKER_CRASH_ORPHAN,
        FailureKind.WAIT_EXPIRED,
        FailureKind.QUEUE_STALE,
    }
)

#: 暂态族（side_effect_state=none 时 RETRYABLE；unknown 时升格 UNKNOWN_OUTCOME）.
_TRANSIENT_KINDS: frozenset[FailureKind] = frozenset(
    {
        FailureKind.TOOL_TIMEOUT,
        FailureKind.TOOL_EXCEPTION,
        FailureKind.TOOL_REPORTED_FAILURE,
        FailureKind.NETWORK_UNREACHABLE,
    }
)

#: 对外只读映射（测试冻结用；与内部表同源）。
FAILURE_KIND_TO_TERMINAL: dict[str, tuple[str, str | None]] = {
    kind.value: (status.value, reason) for kind, (status, reason) in _FAILURE_KIND_BASE_TABLE.items()
}


def _table_sha256() -> str:
    canon = ";".join(
        f"{kind.value}>{status.value}|{reason or ''}|{'R' if kind in _TRANSIENT_KINDS else 'P'}"
        for kind, (status, reason) in sorted(_FAILURE_KIND_BASE_TABLE.items(), key=lambda kv: kv[0].value)
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


#: 分类表确定性指纹（冻结测试锚点：改任何映射必红）。
FAILURE_TABLE_SHA256: str = _table_sha256()


def terminal_for_failure_kind(failure_kind: str | FailureKind) -> tuple[RunStatus, str | None]:
    """failure_kind → (合法终态, 既有 terminal_reason)（确定性查表）."""
    kind = FailureKind(failure_kind)
    status, reason = _FAILURE_KIND_BASE_TABLE[kind]
    return status, reason


def classify_execution_failure(
    *,
    failure_kind: str | FailureKind,
    error_type: str | None = None,
    tool_effect: str | None = None,
    side_effect_state: str | None = None,
) -> FailureClassification:
    """三族确定性分类器（纯函数；同类输入恒同输出）.

    Args:
        failure_kind: 结构化成因（:class:`FailureKind` 封闭词表）。
        error_type: 审计透传的错误类型串（**不参与分类**——分类只看结构化信号，
            防止错误文案变化改变终态语义）。
        tool_effect: 失败工具的效果类别（"read"/"write"/None）。
        side_effect_state: 账本证据（"none"/"unknown"/"confirmed"；None 视为
            "none"——无账本上下文时按最保守的**可重试**处理是错的吗？不：
            read 工具与无账本场景无 side effect 可疑性，none 正确；write 工具
            在无证据时由调用方负责传 unknown——fail-closed 在 executor 侧
            （账本不可读即拒绝执行），分类器信任结构化输入）。

    Raises:
        ValueError: failure_kind / side_effect_state 越词表（封闭词表 fail-fast，
            未知成因不允许静默归并——那是非确定性的入口）。
    """
    try:
        kind = FailureKind(failure_kind)
    except ValueError:
        raise ValueError(
            f"unknown failure_kind {failure_kind!r} (closed vocabulary: {sorted(k.value for k in FailureKind)})"
        ) from None

    effect = str(tool_effect).strip().lower() if tool_effect else None
    if effect not in (None, "read", "write"):
        raise ValueError(f"unknown tool_effect {tool_effect!r} (allowed: read, write, None)")
    state = side_effect_state if side_effect_state is not None else "none"
    if state not in SIDE_EFFECT_STATES:
        raise ValueError(f"unknown side_effect_state {side_effect_state!r} (allowed: {sorted(SIDE_EFFECT_STATES)})")

    base_status, base_reason = _FAILURE_KIND_BASE_TABLE[kind]

    # 用户取消：唯一 USER_CANCELLED 族（取消不是失败，run 归因恒 user_cancelled）。
    if kind is FailureKind.USER_CANCELLED:
        return FailureClassification(
            failure_kind=kind.value,
            family=FailureFamily.USER_CANCELLED,
            run_terminal_status=base_status,
            terminal_reason=base_reason,
            error_category=FailureFamily.USER_CANCELLED.value,
            retryable=False,
            side_effect_state=state,
        )

    # 未知结局族：账本证据 unknown 的 side-effect 调用 + 中断/孤儿信号。
    # 语义：效果不可核实 → 绝不自动重试（retry_requires_new_key=True：换新键
    # 是显式的人类/系统决策，防 duplicate side effect）。
    if kind in (FailureKind.IDEMPOTENCY_INTERRUPTED, FailureKind.WORKER_CRASH_ORPHAN):
        return FailureClassification(
            failure_kind=kind.value,
            family=FailureFamily.UNKNOWN_OUTCOME,
            run_terminal_status=RunStatus.UNKNOWN_OUTCOME,
            terminal_reason="worker_restart_orphan",
            error_category=FailureFamily.UNKNOWN_OUTCOME.value,
            retryable=False,
            side_effect_state=state,
            retry_requires_new_key=True,
        )

    # 暂态族：side effect 证据决定 retryable vs unknown。
    if kind in _TRANSIENT_KINDS:
        if state == "unknown":
            # 崩溃/超时落进 side-effect 调用中间（账本残留）——同一不可核实语义。
            return FailureClassification(
                failure_kind=kind.value,
                family=FailureFamily.UNKNOWN_OUTCOME,
                run_terminal_status=RunStatus.UNKNOWN_OUTCOME,
                terminal_reason="worker_restart_orphan",
                error_category=FailureFamily.UNKNOWN_OUTCOME.value,
                retryable=False,
                side_effect_state=state,
                retry_requires_new_key=True,
            )
        # none / confirmed：无残留（或效果已确认落地）→ 可重试（read 重放无害；
        # write 重试由上层换新键执行——本分类器只裁家族，键策略见 retry_decision）。
        return FailureClassification(
            failure_kind=kind.value,
            family=FailureFamily.RETRYABLE_FAILURE,
            run_terminal_status=base_status,
            terminal_reason=base_reason,
            error_category=FailureFamily.RETRYABLE_FAILURE.value,
            retryable=True,
            side_effect_state=state,
        )

    # 确定性失败族（PERMANENT）：重试不能改变结局 → 死信终态。
    return FailureClassification(
        failure_kind=kind.value,
        family=FailureFamily.PERMANENT_FAILURE,
        run_terminal_status=base_status,
        terminal_reason=base_reason,
        error_category=FailureFamily.PERMANENT_FAILURE.value,
        retryable=False,
        side_effect_state=state,
    )


# ---------------------------------------------------------------------------
# 重试策略（指数退避 + 上限 + 死信终态；纯函数，无抖动——确定性优先）
# ---------------------------------------------------------------------------

#: 退避基线（首次重试延迟；attempt 从 1 起）。
DEFAULT_RETRY_BASE_DELAY_SECONDS = 0.5
#: 退避封顶（防长尾卡死执行循环）。
DEFAULT_RETRY_MAX_DELAY_SECONDS = 8.0
#: 自动重试上限（attempt > max 即死信：run 落明确终态 FAILED，不再重试）。
DEFAULT_MAX_RETRY_ATTEMPTS = 2


def retry_backoff_delay(
    attempt: int,
    *,
    base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
    max_delay_seconds: float = DEFAULT_RETRY_MAX_DELAY_SECONDS,
) -> float:
    """指数退避：``min(max_delay, base · 2^(attempt-1))``（attempt ≥ 1）.

    无抖动、无时钟依赖——同一 attempt 恒同延迟（确定性契约；重试风暴抑制
    由 attempt 上限 + 上游并发约束承担）。
    """
    if attempt < 1:
        raise ValueError(f"attempt must be >= 1, got {attempt}")
    if base_delay_seconds < 0 or max_delay_seconds < 0:
        raise ValueError("delays must be non-negative")
    delay = float(base_delay_seconds) * (2 ** (int(attempt) - 1))
    return cast("float", (round(min(delay, float(max_delay_seconds)), 6)))


def retry_decision(
    classification: FailureClassification,
    *,
    attempt: int,
    max_attempts: int = DEFAULT_MAX_RETRY_ATTEMPTS,
    base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
    max_delay_seconds: float = DEFAULT_RETRY_MAX_DELAY_SECONDS,
) -> tuple[bool, float | None]:
    """重试裁决：``(should_retry, delay_seconds)``.

    - 只有 RETRYABLE 族且 ``1 ≤ attempt ≤ max_attempts`` 才重试；
    - 超过上限 → ``(False, None)``：死信（调用方落明确终态，details 记
      ``retries_exhausted=True``——非无限执行、非静默截断）；
    - UNKNOWN 族恒 ``(False, None)``（自动重试被禁止；重试须换新幂等键的
      显式决策，见 ``classification.retry_requires_new_key``）。
    """
    if not classification.retryable:
        return False, None
    if not (1 <= int(attempt) <= int(max_attempts)):
        return False, None  # 死信：重试预算耗尽
    return True, retry_backoff_delay(
        attempt, base_delay_seconds=base_delay_seconds, max_delay_seconds=max_delay_seconds
    )


def is_legal_failure_terminal(status: RunStatus | str) -> bool:
    """分类器产出的 run 终态合法性复查（必须落在 X-05 终态集内）。"""
    return is_terminal_run_status(status)
