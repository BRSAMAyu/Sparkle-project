"""X-05 · Unified Agent Run 持久化状态机 —— 封闭词表与迁移图（纯函数，无 IO）.

契约真源（对应 v3/02_core_systems/AGENT_RUNTIME.md §2 Run State Machine）：

    QUEUED → RUNNING → AWAITING_USER / AWAITING_APPROVAL → EXECUTING → SUCCEEDED
    terminal: FAILED / CANCELLED / TIMED_OUT / PARTIAL / UNKNOWN_OUTCOME

设计（对齐 X-02 action_allocation_policy 的 core 层架构）：

- 本模块 stdlib-only、零 IO、零 import app.*，可被任意层（service/api/worker/
  gateway 测试）无环引用；
- 状态词表与迁移图为**封闭集**，被 backend/tests/unit/test_run_state_machine.py
  双冻结（精确集 + sha256）；扩词表/扩迁移边需 bump ``RUN_STATE_MACHINE_VERSION``
  并过两位 reviewer（X-02 冻结声明同款）；
- 非法迁移抛 :class:`IllegalRunTransitionError`（ValueError 子类，API 层沿用
  tasks.py:999 的 ValueError→409 先例映射）；
- 附带 intent→run 投影映射（:data:`INTENT_STATUS_TO_RUN_STATUS`，供
  run_projection_consumer 使用）：ExecutionIntent 的 11 态执行器协议词表投影到
  用户可见 run 状态机。run 状态机是**用户可见长任务脊柱**，intent 是**执行器
  协议**——两个词表各自封闭，映射是全函数（每个 intent 状态都有 run 侧落点）。

与既有真源的关系（不重建）：
- ExecutionIntent 状态迁移逻辑零改动（execution_service 不动）；
- 本状态机只约束 ``agent_runs.status`` 这一新增聚合（X-05 迁移 x05_20260919）。

Wait 语义：AWAITING_USER 与 AWAITING_APPROVAL 共用事件名 ``run.awaiting_user``
（payload ``wait.kind ∈ {user_step, approval}``，与 dev DB 2026-09-17 探针行的
payload 形状一致）；resume 统一 ``run.user_resumed``。其余状态迁移统一走
``run.status_changed``（D-01 扩词表先例，task.status_changed 同族）。
"""

from __future__ import annotations

import hashlib
from enum import StrEnum

__all__ = [
    "RUN_STATE_MACHINE_VERSION",
    "RunStatus",
    "RunWaitKind",
    "RunEventName",
    "TERMINAL_RUN_STATUSES",
    "ACTIVE_RUN_STATUSES",
    "ALLOWED_RUN_TRANSITIONS",
    "RUN_TRANSITIONS_SHA256",
    "IllegalRunTransitionError",
    "RunStateError",
    "InvalidResumeTargetError",
    "RESUMABLE_RUN_STATUSES",
    "is_terminal_run_status",
    "assert_transition_legal",
    "event_name_for_transition",
    "INTENT_STATUS_TO_RUN_STATUS",
    "run_status_for_intent_status",
    "terminal_reason_vocabulary",
]

#: 状态机契约版本。扩词表/扩迁移边必须 bump 并过两位 reviewer（冻结声明）。
#: ``agent_run.v2``（X-06）：终态词表 + ``budget_exceeded`` 归因 + 5 条活跃态
#: →BUDGET_EXCEEDED 边（run budget 四维超限的明确终态；事件复用
#: ``run.status_changed``，D-01 36 词表零改动——X-06 卡面红线）。
RUN_STATE_MACHINE_VERSION = "agent_run.v2"


class RunStatus(StrEnum):
    """用户可见长任务 run 状态（封闭词表，AGENT_RUNTIME.md §2）。"""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    AWAITING_USER = "AWAITING_USER"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    # --- terminal（封闭：无出边） ---
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class RunWaitKind(StrEnum):
    """等待子类（AWAITING_* 态的 payload 参数化，探针 payload 先例）。"""

    USER_STEP = "user_step"
    APPROVAL = "approval"


class RunEventName(StrEnum):
    """run 聚合的事件名（D-01 注册词表的 run 子集 + X-05 唯一新增名）。

    - created / awaiting_user / user_resumed / step_completed：D-01 已注册
      （X-05 起 status=live，producer=app/services/agent_run_service.py）；
    - status_changed：X-05 新增（D-01 扩词表先例，task.status_changed 同族），
      覆盖其余全部状态迁移——语义时刻用专名，其余统一 status_changed，
      避免为 started/succeeded/failed/… 各扩一名。
    """

    CREATED = "run.created"
    STATUS_CHANGED = "run.status_changed"
    AWAITING_USER = "run.awaiting_user"
    USER_RESUMED = "run.user_resumed"
    STEP_COMPLETED = "run.step_completed"


#: 终态集（封闭：任何出边非法）。
TERMINAL_RUN_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.PARTIAL,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.TIMED_OUT,
        RunStatus.UNKNOWN_OUTCOME,
        RunStatus.BUDGET_EXCEEDED,
    }
)

#: 活动态集。
ACTIVE_RUN_STATUSES: frozenset[RunStatus] = frozenset(set(RunStatus) - TERMINAL_RUN_STATUSES)


class RunStateError(ValueError):
    """run 状态机契约错误的基类（ValueError 子类 → API 层 409 映射先例）。"""


class IllegalRunTransitionError(RunStateError):
    """非法状态迁移（不在封闭迁移图内；终态出边同样落此）。"""


class InvalidResumeTargetError(RunStateError):
    """resume 的目标状态不在服务端白名单内（R2 F4）。

    ``resume`` 是**用户恢复等待中 run** 的语义操作，目标只允许落回执行态
    （:data:`RESUMABLE_RUN_STATUSES`）；终态/等待态/未知串一律拒绝——
    客户端不得借 resume 注入 ``AWAITING_USER → SUCCEEDED`` 之类的伪造迁移。
    """


#: resume 语义合法目标子集（服务端白名单，客户端 to_status 只能从这里取值）。
#: RUNNING/EXECUTING 即 AGENT_RUNTIME.md §2 的两个执行落点；终态不可达。
RESUMABLE_RUN_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.RUNNING,
        RunStatus.EXECUTING,
    }
)


#: 封闭迁移图。无自环：同态重复迁移由 service 层的 FOR UPDATE+复查幂等吸收
#:（M-07 同法），不作为合法迁移边。
#:
#: QUEUED 无 →SUCCEEDED/PARTIAL：从未启动的 run 不可能成功/部分完成
#: （恢复路径给 QUEUED stale 的落点是 CANCELLED）。
#: AWAITING_* 互通（USER↔APPROVAL）非法：等待类型变更没有业务语义。
#: X-06：全部活跃态 →BUDGET_EXCEEDED（预算是外部资源裁决，非执行成败声明，
#: 故 QUEUED 也可达——排队的 run 同样消耗时间预算）。
ALLOWED_RUN_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.EXECUTING,
            RunStatus.AWAITING_USER,
            RunStatus.AWAITING_APPROVAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
            RunStatus.UNKNOWN_OUTCOME,
            RunStatus.BUDGET_EXCEEDED,
        }
    ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.EXECUTING,
            RunStatus.AWAITING_USER,
            RunStatus.AWAITING_APPROVAL,
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
            RunStatus.UNKNOWN_OUTCOME,
            RunStatus.BUDGET_EXCEEDED,
        }
    ),
    RunStatus.EXECUTING: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.AWAITING_USER,
            RunStatus.AWAITING_APPROVAL,
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
            RunStatus.UNKNOWN_OUTCOME,
            RunStatus.BUDGET_EXCEEDED,
        }
    ),
    RunStatus.AWAITING_USER: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.EXECUTING,
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
            RunStatus.UNKNOWN_OUTCOME,
            RunStatus.BUDGET_EXCEEDED,
        }
    ),
    RunStatus.AWAITING_APPROVAL: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.EXECUTING,
            RunStatus.SUCCEEDED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMED_OUT,
            RunStatus.UNKNOWN_OUTCOME,
            RunStatus.BUDGET_EXCEEDED,
        }
    ),
    # terminal：封闭（无出边）。
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.PARTIAL: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
    RunStatus.TIMED_OUT: frozenset(),
    RunStatus.UNKNOWN_OUTCOME: frozenset(),
    RunStatus.BUDGET_EXCEEDED: frozenset(),
}


def _transitions_sha256() -> str:
    """迁移图的确定性指纹（冻结测试双冻结用）。"""
    canon = ";".join(
        f"{src.value}>" + ",".join(sorted(dst.value for dst in dsts))
        for src, dsts in sorted(ALLOWED_RUN_TRANSITIONS.items(), key=lambda kv: kv[0].value)
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


RUN_TRANSITIONS_SHA256: str = _transitions_sha256()


def is_terminal_run_status(status: RunStatus | str) -> bool:
    try:
        return RunStatus(status) in TERMINAL_RUN_STATUSES
    except ValueError:
        return False


def assert_transition_legal(source: RunStatus | str, target: RunStatus | str) -> RunStatus:
    """断言迁移在封闭图内；非法抛 IllegalRunTransitionError（含终态出边）。"""
    try:
        src = RunStatus(source)
    except ValueError:
        raise IllegalRunTransitionError(f"unknown run status {source!r}") from None
    try:
        dst = RunStatus(target)
    except ValueError:
        raise IllegalRunTransitionError(f"unknown run status {target!r}") from None
    if dst not in ALLOWED_RUN_TRANSITIONS[src]:
        if src in TERMINAL_RUN_STATUSES:
            raise IllegalRunTransitionError(f"run status {src.value} is terminal; transition to {dst.value} rejected")
        raise IllegalRunTransitionError(
            f"illegal run transition {src.value} -> {dst.value} "
            f"(allowed: {sorted(s.value for s in ALLOWED_RUN_TRANSITIONS[src]) or 'none'})"
        )
    return dst


def event_name_for_transition(source: RunStatus | None, target: RunStatus) -> RunEventName:
    """语义时刻用 D-01 专名，其余迁移统一 run.status_changed（封闭映射）。"""
    if source is None:
        return RunEventName.CREATED
    if target in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL):
        return RunEventName.AWAITING_USER
    if source in (RunStatus.AWAITING_USER, RunStatus.AWAITING_APPROVAL) and target in (
        RunStatus.RUNNING,
        RunStatus.EXECUTING,
    ):
        return RunEventName.USER_RESUMED
    return RunEventName.STATUS_CHANGED


#: terminal_reason 封闭词表（终态归因，供审计/恢复读取；扩词需 bump 版本）。
#: X-06 v2 新增 ``budget_exceeded``（BUDGET_EXCEEDED 终态唯一归因）。
terminal_reason_vocabulary: frozenset[str] = frozenset(
    {
        "completed",
        "completed_partial",
        "failed",
        "user_cancelled",
        "handed_back",
        "timeout",
        "wait_expired",
        "queue_stale",
        "worker_restart_orphan",
        "projection_drift_repair",
        "rejected",
        "budget_exceeded",
    }
)

# ---------------------------------------------------------------------------
# ExecutionIntent → Run 投影映射（run_projection_consumer 消费；全函数）
# ---------------------------------------------------------------------------

INTENT_STATUS_TO_RUN_STATUS: dict[str, RunStatus] = {
    # intent 执行器协议态 → 用户可见 run 态
    "draft": RunStatus.QUEUED,
    "ready": RunStatus.QUEUED,
    "queued": RunStatus.QUEUED,
    "dispatched": RunStatus.RUNNING,
    "running": RunStatus.RUNNING,
    "waiting_approval": RunStatus.AWAITING_APPROVAL,
    "succeeded": RunStatus.SUCCEEDED,
    "partial": RunStatus.PARTIAL,
    "failed": RunStatus.FAILED,
    "canceled": RunStatus.CANCELLED,
    "timed_out": RunStatus.TIMED_OUT,
    # handed_back：任务交还用户执行——run 侧终态 CANCELLED（reason=handed_back）
    "handed_back": RunStatus.CANCELLED,
}


def run_status_for_intent_status(intent_status: str) -> RunStatus:
    """intent 状态 → run 状态（全函数：未知值抛 RunStateError）。"""
    try:
        return INTENT_STATUS_TO_RUN_STATUS[str(intent_status).strip().lower()]
    except KeyError:
        raise RunStateError(f"unmapped execution intent status {intent_status!r}") from None
