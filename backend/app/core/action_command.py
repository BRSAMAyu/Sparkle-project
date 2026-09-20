"""X-03 · Action Proposal/Command 协议契约（真源：闭词汇 + 冻结结构）.

ACTION_AND_INTERVENTION_ENGINE.md §3 的协议化：

    proposal → approve(confirmation) → validate(version + permission)
            → commit(effects) → authoritative receipt

本模块只定义**封闭词表与结构**（C-01 decision_context / X-01 action_plan 同款
纪律）：状态、来源、命令类型、终态归因、授权 reason codes、错误码。写入权威在
``app/services/action_command_service.py``（单一 command path），命令执行器在
``app/services/action_commands/``（路由到既有领域服务，不重建写路径）。

词表冻结：新增 CommandType / terminal reason / authorization reason code 是契约
变更，需在测试 ``test_action_command_service.py`` 的冻结断言中同步 bump。

stdlib-only，无 I/O——任意层可 import，无循环风险。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "ACTION_COMMAND_PROTOCOL_VERSION",
    "ACTION_PROPOSAL_AGGREGATE_TYPE",
    "ProposalStatus",
    "ProposalSource",
    "ActionCommandType",
    "TerminalReason",
    "AuthorizationMode",
    "AuthorizationReason",
    "ACTION_ERROR_CODES",
    "ActionCommandError",
    "ProposalNotFoundError",
    "VersionConflictError",
    "AuthorizationDeniedError",
    "ProposalNotPendingError",
    "ProposalExpiredError",
    "CommandValidationError",
    "TERMINAL_PROPOSAL_STATUSES",
    "PROPOSAL_STATUS_VALUES",
    "ACTION_COMMAND_TYPE_VALUES",
    "TERMINAL_REASON_VOCABULARY",
    "AUTHORIZATION_REASON_VOCABULARY",
    "version_token",
    "build_diff",
    "DEFAULT_PROPOSAL_TTL_SECONDS",
    "MAX_PROPOSAL_TTL_SECONDS",
]

ACTION_COMMAND_PROTOCOL_VERSION = "action_command.v1"

ACTION_PROPOSAL_AGGREGATE_TYPE = "action_proposal"

#: 事件名（D-01 封闭词表，36 名不动）：action.proposed / action.accepted /
#: action.rejected 为 X-03 落地 producer（reserved → live，X-05 run.* 同款先例）。
EVENT_ACTION_PROPOSED = "action.proposed"
EVENT_ACTION_ACCEPTED = "action.accepted"
EVENT_ACTION_REJECTED = "action.rejected"


class ProposalStatus(StrEnum):
    """Proposal 生命周期状态（封闭词表）。

    PENDING 是唯一非终态。终态封闭：COMMITTED / CANCELLED / EXPIRED / REJECTED
    均无出边（X-05 run 状态机同款终态封闭纪律；approve-after-cancel 等一律 409）。
    """

    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


TERMINAL_PROPOSAL_STATUSES: frozenset[ProposalStatus] = frozenset(
    {
        ProposalStatus.COMMITTED,
        ProposalStatus.CANCELLED,
        ProposalStatus.EXPIRED,
        ProposalStatus.REJECTED,
    }
)

PROPOSAL_STATUS_VALUES: tuple[str, ...] = tuple(s.value for s in ProposalStatus)


class ProposalSource(StrEnum):
    """Proposal 的产生入口（「所有入口走同一路径」的入口标记，仅观测用）."""

    CHAT = "chat"
    TASK = "task"
    AURORA = "aurora"
    SYSTEM = "system"
    API = "api"


class ActionCommandType(StrEnum):
    """Proposal 到 commit 时执行的命令域（封闭词表）.

    X-03 首发任务域三类——覆盖「有 subject + 版本冲突面」（update_status /
    update_fields）与「无 subject」（create_batch，milestone 式推荐建任务）。
    新命令域 = 契约变更：在此登记 + 处理器注册 + 冻结测试 bump。
    """

    TASK_UPDATE_STATUS = "task.update_status"
    TASK_UPDATE_FIELDS = "task.update_fields"
    TASK_CREATE_BATCH = "task.create_batch"


ACTION_COMMAND_TYPE_VALUES: tuple[str, ...] = tuple(t.value for t in ActionCommandType)


class TerminalReason(StrEnum):
    """终态归因（封闭词表；与 X-05 run terminal_reason 风格对齐）.

    - ``user_cancelled``：用户显式取消（X-05 同名归因——非复活语义）；
    - ``user_rejected``：用户在确认卡上选择拒绝（区别于取消）；
    - ``expired``：过期作废（懒转 + sweep，状态显式持久化）；
    - ``committed``：正常落账（receipt 权威）。
    """

    COMMITTED = "committed"
    USER_CANCELLED = "user_cancelled"
    USER_REJECTED = "user_rejected"
    EXPIRED = "expired"


TERMINAL_REASON_VOCABULARY: frozenset[str] = frozenset(r.value for r in TerminalReason)


class AuthorizationMode(StrEnum):
    """授权模式（ACTION §3：proposal ≠ 执行）."""

    AUTO = "auto"  # 用户已授予的低风险自动权限（仅 risk=low 且可逆且无人工审批标记）
    CONFIRMATION = "confirmation"  # 其余一切写操作：proposal → confirmation → …


class AuthorizationReason(StrEnum):
    """授权决策 reason codes（封闭词表，确定性规则输出，非 LLM）."""

    RISK_LOW_REVERSIBLE_AUTO_GRANT = "risk_low_reversible_auto_grant"
    AUTO_FORBIDDEN_RISK_NOT_LOW = "auto_forbidden_risk_not_low"
    AUTO_FORBIDDEN_IRREVERSIBLE = "auto_forbidden_irreversible"
    AUTO_FORBIDDEN_HUMAN_APPROVAL_REQUIRED = "auto_forbidden_human_approval_required"
    AUTO_FORBIDDEN_GRANT_ABSENT = "auto_forbidden_grant_absent"
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation"
    USER_CONFIRMATION_PRESENT = "user_confirmation_present"
    DENIED_NO_CONFIRMATION = "denied_no_confirmation"


AUTHORIZATION_REASON_VOCABULARY: frozenset[str] = frozenset(r.value for r in AuthorizationReason)


#: 明确错误码（网关/客户端可编程处理；runs.py 先例：错误码进 detail 结构）
ACTION_ERROR_CODES = {
    "VERSION_CONFLICT": "ACTION_VERSION_CONFLICT",
    "UNAUTHORIZED": "ACTION_UNAUTHORIZED",
    "NOT_PENDING": "ACTION_NOT_PENDING",
    "EXPIRED": "ACTION_EXPIRED",
    "NOT_FOUND": "ACTION_NOT_FOUND",
    "INVALID_COMMAND": "ACTION_INVALID_COMMAND",
}


# --- 错误层级（ValueError 族 → API 400/409/410/403/404 house 映射） -------------


class ActionCommandError(ValueError):
    """基类：携带稳定 error_code，API 层映射 HTTP 状态。"""

    error_code: str = ACTION_ERROR_CODES["INVALID_COMMAND"]
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details: dict[str, Any] = dict(details or {})

    def to_payload(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": str(self),
            "details": self.details,
        }


class ProposalNotFoundError(ActionCommandError):
    error_code = ACTION_ERROR_CODES["NOT_FOUND"]
    http_status = 404


class VersionConflictError(ActionCommandError):
    """乐观并发拒绝：subject 版本 token 与 proposal 捕获时不一致——不覆盖.

    proposal 保持 PENDING（不自动作废），客户端取 fresh diff 后重提或取消。
    """

    error_code = ACTION_ERROR_CODES["VERSION_CONFLICT"]
    http_status = 409


class AuthorizationDeniedError(ActionCommandError):
    """未授权不执行：permission decision 前置于 commit（软件强制，非提示词）."""

    error_code = ACTION_ERROR_CODES["UNAUTHORIZED"]
    http_status = 403


class ProposalNotPendingError(ActionCommandError):
    """终态封闭：对非 PENDING proposal 的 approve/cancel/reject 一律拒绝."""

    error_code = ACTION_ERROR_CODES["NOT_PENDING"]
    http_status = 409


class ProposalExpiredError(ActionCommandError):
    """过期作废：approve 时懒转 EXPIRED（显式持久状态）后抛出."""

    error_code = ACTION_ERROR_CODES["EXPIRED"]
    http_status = 410


class CommandValidationError(ActionCommandError):
    """payload/命令前置校验失败（确定性预筛，非 LLM）."""

    error_code = ACTION_ERROR_CODES["INVALID_COMMAND"]
    http_status = 422


# --- 结构 ---------------------------------------------------------------------


def version_token(updated_at: datetime | None) -> str | None:
    """subject 行的版本 token（updated_at ISO 字符串；None = 无 subject/新建）.

    BaseModel.updated_at 带 onupdate —— 任何 ORM 写都会 bump，天然乐观并发令牌。
    """
    if updated_at is None:
        return None
    return updated_at.replace(tzinfo=None).isoformat(timespec="microseconds")


def build_diff(
    *,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any]:
    """可渲染前后对照（UI 确认卡数据面）.

    结构：``{"before": …, "after": …, "changed_fields": […]}``；
    ``changed_fields`` 由键差集推导（确定性，非自由文本）。before 为 None 表示
    创建型命令（无前态）。
    """
    before = dict(before) if before is not None else None
    after = dict(after) if after is not None else None
    if before is None or after is None:
        changed = sorted(after.keys()) if after is not None else []
    else:
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    return {"before": before, "after": after, "changed_fields": changed}


@dataclass(frozen=True)
class PreparedCommand:
    """命令处理器 prepare() 的产出（proposal 落库前的确定性预筛结果）."""

    command_type: str
    subject_type: str | None
    subject_id: str | None
    subject_version_token: str | None
    payload: dict[str, Any]
    diff: dict[str, Any]
    summary: str
    risk_class: str | None = None
    reversible: bool | None = None


@dataclass(frozen=True)
class CommandEffects:
    """命令处理器 execute() 的产出（receipt 的 effects 块）."""

    effects: list[dict[str, Any]] = field(default_factory=list)
    subject_after: dict[str, Any] | None = None
    subject_version_token_after: str | None = None


# --- TTL 契约（与 V2 pending_actions 30 分钟默认对齐） --------------------------

DEFAULT_PROPOSAL_TTL_SECONDS = 30 * 60
MAX_PROPOSAL_TTL_SECONDS = 24 * 3600
