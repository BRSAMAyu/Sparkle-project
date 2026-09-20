"""X-03 · Action Proposal 授权层（确定性软件强制，前置 commit）.

ACTION_AND_INTERVENTION_ENGINE.md §3：

    Proposal 不等于执行。用户已授予的低风险自动权限才允许 auto-execute。
    其它写操作：proposal → confirmation → deterministic validation → execute → receipt。

设计边界（卡面红线）：
- **proposal/action 授权层**，不是工具权限（X-06 在途 wt11 动 tools/权限/预算——
  本模块不 import 工具注册表，零耦合）；
- **复用既有 permission 真源**：风险/可逆性取命令域语义导出（X-01 RiskClass 词表，
  ``action_commands/task_commands.py`` 的 per-command 映射）；「需人工审批」取
  X-02 R1 语义的**服务端投影**（``action_command_service._requires_human_approval``，
  R2 P2-3 返修后调用方/客户端零传入面——授权输入不由任何请求方供给）；
- 纯函数、封闭 reason codes、无 I/O 无 LLM——守卫由代码强制，不信任提示词。

两个检查点：
1. :func:`decide_authorization_mode` —— proposal 创建时决定 mode（auto|confirmation），
   记录在 proposal.authorization（UI 据此决定「直接执行」还是「弹确认卡」）；
2. :func:`authorize_commit` —— commit 前强制复核：mode=confirmation 的 proposal
   必须携带有效用户确认（approve 调用即确认行为），否则
   :class:`AuthorizationDeniedError`（未授权不执行）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.action_command import (
    AuthorizationDeniedError,
    AuthorizationMode,
    AuthorizationReason,
)

__all__ = [
    "ActionAuthorizationDecision",
    "decide_authorization_mode",
    "authorize_commit",
    "record_confirmation",
]

_AUTO_ALLOWED_RISK = frozenset({"low", None})  # None = 未分级：按 low 处理（可逆前提下）


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ActionAuthorizationDecision(dict):
    """授权决策的 JSON 可序列化形态（落 proposal.authorization 列）.

    dict 子类：直接 JSONB 落库、直接 API 投影，无需转换层。
    """

    @property
    def mode(self) -> str:
        return str(self.get("mode", AuthorizationMode.CONFIRMATION.value))

    @property
    def allowed(self) -> bool:
        return bool(self.get("allowed", False))

    @property
    def reason_codes(self) -> list[str]:
        return list(self.get("reason_codes", []))


def decide_authorization_mode(
    *,
    risk_class: str | None,
    reversible: bool | None,
    requires_human_approval: bool = False,
    user_auto_grant: bool = False,
) -> ActionAuthorizationDecision:
    """proposal 创建时的 mode 决策（确定性规则，封闭 reason codes）.

    auto 需**同时**满足：
    - 风险为 low（或未分级——未分级不视为高风险，但可逆性必须明确为真）；
    - 可逆（reversible 不为 False；None 时要求显式 risk=low 才放行）；
    - X-02 分配策略未标记 requires_human_approval；
    - 用户已授予低风险自动权限（user_auto_grant；真源=UserSettings.
      low_risk_auto_execute，由 command path 服务端自查，R2 P2-3 返修后非调用方输入）。

    任何一条不满足 → confirmation（proposal → 用户确认 → …）。
    """
    reasons: list[str] = []
    auto = True

    if risk_class is not None and risk_class not in _AUTO_ALLOWED_RISK:
        auto = False
        reasons.append(AuthorizationReason.AUTO_FORBIDDEN_RISK_NOT_LOW.value)
    if reversible is False:
        auto = False
        reasons.append(AuthorizationReason.AUTO_FORBIDDEN_IRREVERSIBLE.value)
    if reversible is None and risk_class is None:
        # 既未分级又未声明可逆性：不可自动
        auto = False
        reasons.append(AuthorizationReason.AUTO_FORBIDDEN_IRREVERSIBLE.value)
    if requires_human_approval:
        auto = False
        reasons.append(AuthorizationReason.AUTO_FORBIDDEN_HUMAN_APPROVAL_REQUIRED.value)
    if not user_auto_grant:
        auto = False
        reasons.append(AuthorizationReason.AUTO_FORBIDDEN_GRANT_ABSENT.value)

    mode = AuthorizationMode.AUTO if auto else AuthorizationMode.CONFIRMATION
    if auto:
        reasons.insert(0, AuthorizationReason.RISK_LOW_REVERSIBLE_AUTO_GRANT.value)
    else:
        reasons.insert(0, AuthorizationReason.AWAITING_USER_CONFIRMATION.value)

    return ActionAuthorizationDecision(
        {
            "mode": mode.value,
            "decided_at": _utcnow().isoformat(timespec="seconds"),
            "reason_codes": reasons,
            "confirmed_by": None,
            "confirmed_at": None,
        }
    )


def authorize_commit(authorization: dict[str, Any] | None) -> ActionAuthorizationDecision:
    """commit 前的强制复核（未授权不执行——软件层守卫）.

    - mode=auto：放行（创建时已过全部 guard）；
    - mode=confirmation：必须存在已记录的用户确认（``confirmed_by`` 非空）；
    - 授权记录缺失：按 confirmation 且无确认处理（保守拒绝，绝不放行）。
    """
    auth = dict(authorization or {})
    mode = str(auth.get("mode", AuthorizationMode.CONFIRMATION.value))

    if mode == AuthorizationMode.AUTO.value:
        return ActionAuthorizationDecision({**auth, "allowed": True, "commit_reason": "auto_mode_granted"})

    confirmed_by = auth.get("confirmed_by")
    if confirmed_by:
        return ActionAuthorizationDecision(
            {**auth, "allowed": True, "commit_reason": AuthorizationReason.USER_CONFIRMATION_PRESENT.value}
        )
    raise AuthorizationDeniedError(
        "commit denied: no valid user confirmation recorded for this proposal",
        details={
            "mode": mode,
            "reason_codes": [AuthorizationReason.DENIED_NO_CONFIRMATION.value],
        },
    )


def record_confirmation(
    authorization: dict[str, Any] | None,
    *,
    confirmed_by: str = "user",
) -> ActionAuthorizationDecision:
    """把 approve 调用记录为该 proposal 的用户确认行为（幂等：重复确认覆盖同一字段）."""
    auth = dict(authorization or {})
    auth.setdefault("mode", AuthorizationMode.CONFIRMATION.value)
    auth["confirmed_by"] = confirmed_by
    auth["confirmed_at"] = _utcnow().isoformat(timespec="milliseconds")
    return ActionAuthorizationDecision(auth)
