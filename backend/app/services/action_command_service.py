"""X-03 · ActionCommandService —— proposal→approve→validate→commit→receipt 唯一权威.

V2 可信写入协议（chat ``/confirm`` 的 pending_actions + idempotency 基建）推广到
V3 Action，**复用不重建**：

- 幂等骨架 = X-05 agent_run_service 同构：``(user_id, idempotency_key)`` 唯一索引
  （重复创建恰一次）+ ``SELECT…FOR UPDATE`` 行锁 + 复查（重复 approve 恰一次
  commit，sqlite 测试下行锁 no-op 由复查+唯一索引兜底）+ ``(proposal_id,
  idempotency_key)`` 审计唯一；
- 事件 = D-01 封闭词表既有名 ``action.proposed`` / ``action.accepted`` /
  ``action.rejected``（36 词表零新增；reserved→live，X-05 run.* 同款先例），
  event_outbox 同事务写入 + ``event_sequence_counters`` 单调序列（M-07 同法）；
- 过期 = V2 pending_actions 30 分钟 TTL 语义，但状态**显式持久化**
  （PENDING→EXPIRED 懒转 + sweep，非读时挥发）。

单一 command path（卡面工作项 1）：所有入口（chat/task/Aurora）经
``create_proposal(source=...)`` 生成 proposal，经 ``approve()`` 落账——
权威逻辑单点在 ``_commit_pending``，入口适配层只是薄参数化。

事务纪律：proposal/receipt/transition/outbox 的写先 stage 进同一 session 事务，
命令处理器 execute() 调用**既有领域服务**（TaskService），其内部 commit 原子
携带全部 staged 写（单次 commit 全落或全不落）；异常一律 rollback。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import (
    ACTION_COMMAND_PROTOCOL_VERSION,
    DEFAULT_PROPOSAL_TTL_SECONDS,
    EVENT_ACTION_ACCEPTED,
    EVENT_ACTION_PROPOSED,
    EVENT_ACTION_REJECTED,
    MAX_PROPOSAL_TTL_SECONDS,
    TERMINAL_PROPOSAL_STATUSES,
    ActionCommandError,
    ProposalExpiredError,
    ProposalNotFoundError,
    ProposalNotPendingError,
    ProposalSource,
    ProposalStatus,
    TerminalReason,
)
from app.core.event_registry import CorrelationIds, EventSource, build_event_metadata
from app.models.action_proposal import ActionProposal, ActionProposalTransition
from app.models.user_settings import UserSettings
from app.services.action_authorization import (
    decide_authorization_mode,
    record_confirmation,
)

# 直接从定义模块导入（而非包再导出）：依赖图对静态守卫（Rule AT）可见，
# 运行时同一对象，语义零变化。
from app.services.action_commands.task_commands import get_command_handler

ACTION_PROPOSAL_AGGREGATE = "action_proposal"
ACTION_COMMAND_SERVICE_NAME = "action_command_service"

_SOURCE_EVENT_SOURCE: dict[str, EventSource] = {
    ProposalSource.CHAT.value: EventSource.SERVER_SERVICE,
    ProposalSource.TASK.value: EventSource.SERVER_SERVICE,
    ProposalSource.AURORA.value: EventSource.SERVER_SERVICE,
    ProposalSource.SYSTEM.value: EventSource.SERVER_SERVICE,
    ProposalSource.API.value: EventSource.SERVER_SERVICE,
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _requires_human_approval(prepared: Any) -> bool:
    """审批标记的**服务端真源**（R2 P2-3 返修）：只认 X-02 服务端语义.

    X-02 ``action_allocation_policy`` rule 层 R1（高风险必须人工审批，
    ``requires_human_approval`` ⟺ ``R1.high_risk_requires_human_approval``）在
    命令风险分级上的确定性投影。任务域当前无 high/critical 命令 → 恒 False；
    高影响命令域接入时，此处替换为完整 ``AllocationDecision`` 权威输出读取。
    调用方（含 API 客户端）无法传入或压低此标记。
    """
    return getattr(prepared, "risk_class", None) in {"high", "critical"}


@dataclass(frozen=True)
class ProposalMutationResult:
    """一次 proposal 操作的结果（applied=False 即幂等 no-op / replay）."""

    proposal: ActionProposal
    applied: bool
    created: bool = False
    event_name: str | None = None
    event_written: bool = False
    already_committed: bool = False  # approve 重放：receipt 原样奉还，不重复写


class ActionCommandService:
    """Action proposal/command 的唯一读写权威（API/入口不直改 proposal 行）."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # create（幂等：同 (user_id, idempotency_key) 重复创建恰一次）
    # ------------------------------------------------------------------

    async def create_proposal(
        self,
        *,
        user_id: UUID | str,
        command_type: str,
        payload: dict[str, Any],
        source: str = ProposalSource.SYSTEM.value,
        idempotency_key: str | None = None,
        ttl_seconds: int | None = None,
        summary: str | None = None,
        execute_if_authorized: bool = False,
        session_id: str | None = None,
        trace_id: str | None = None,
        run_id: UUID | str | None = None,
    ) -> ProposalMutationResult:
        """统一入口：生成 proposal（确定性预筛 + diff + 授权 mode + 过期）.

        ``execute_if_authorized=True`` 且授权 mode=auto 时，同一事务链内直接落账
        （用户已授予的低风险自动权限路径，ACTION §3）；否则 PENDING 等确认。

        授权输入的服务端真源（R2 P2-3 返修，客户端/调用方零自授面）：
        - ``user_auto_grant`` ← ``UserSettings.low_risk_auto_execute``（本方法自查）；
        - ``requires_human_approval`` ← X-02 rule 层 R1 语义在命令风险分级上的
          服务端投影（``_requires_human_approval``）。
        两者均**不是**本方法的参数——任何调用路径都无法传入授权值。
        """
        user_uuid = UUID(str(user_id))
        key = (str(idempotency_key).strip() if idempotency_key else None) or None
        if source not in {s.value for s in ProposalSource}:
            raise ValueError(f"unknown proposal source {source!r} (closed vocabulary)")

        if key is not None:
            existing = await self._find_by_idempotency_key(user_uuid, key)
            if existing is not None:
                return await self._resume_or_replay(existing, execute_if_authorized=execute_if_authorized)

        handler = get_command_handler(command_type)
        prepared = await handler.prepare(self.db, payload=payload, user_id=user_uuid)

        authorization = decide_authorization_mode(
            risk_class=prepared.risk_class,
            reversible=prepared.reversible,
            requires_human_approval=_requires_human_approval(prepared),
            user_auto_grant=await self._user_auto_grant(user_uuid),
        )

        now = _utcnow()
        ttl = DEFAULT_PROPOSAL_TTL_SECONDS if ttl_seconds is None else int(ttl_seconds)
        ttl = max(60, min(ttl, MAX_PROPOSAL_TTL_SECONDS))
        proposal = ActionProposal(
            id=uuid4(),
            user_id=user_uuid,
            status=ProposalStatus.PENDING,
            command_type=prepared.command_type,
            source=source,
            subject_type=prepared.subject_type,
            subject_id=UUID(prepared.subject_id) if prepared.subject_id else None,
            subject_version_token=prepared.subject_version_token,
            payload=prepared.payload,
            diff=prepared.diff,
            authorization=dict(authorization),
            risk_class=prepared.risk_class,
            reversible=("true" if prepared.reversible else "false") if prepared.reversible is not None else None,
            summary=summary or prepared.summary,
            idempotency_key=key,
            expires_at=now + timedelta(seconds=ttl),
            session_id=str(session_id)[:64] if session_id else None,
            trace_id=str(trace_id)[:64] if trace_id else None,
            run_id=UUID(str(run_id)) if run_id else None,
        )
        self.db.add(proposal)
        transition = ActionProposalTransition(
            proposal_id=proposal.id,
            from_status=None,
            to_status=ProposalStatus.PENDING.value,
            event_name=EVENT_ACTION_PROPOSED,
            actor=source,
            idempotency_key=key,
            reason=None,
            details={"command_type": prepared.command_type},
            occurred_at=now,
        )
        self.db.add(transition)
        event_written = await self._write_action_event_in_txn(
            proposal=proposal,
            event_name=EVENT_ACTION_PROPOSED,
            source=_SOURCE_EVENT_SOURCE.get(source, EventSource.SERVER_SERVICE),
            payload=self._proposal_payload(proposal, extra={"ttl_seconds": ttl}),
        )

        try:
            await self.db.commit()
        except IntegrityError:
            # 并发同 key 双创建 → 复查收敛（X-05 create 同法）
            await self.db.rollback()
            if key is not None:
                existing = await self._find_by_idempotency_key(user_uuid, key)
                if existing is not None:
                    return await self._resume_or_replay(existing, execute_if_authorized=execute_if_authorized)
            raise
        await self.db.refresh(proposal)

        # 低风险自动权限路径：授权 mode=auto 且入口请求立即执行 → 同链路落账
        if execute_if_authorized and authorization.mode == "auto":
            return await self.approve(proposal.id, user_id=user_uuid, actor="system", _called_internally=True)

        return ProposalMutationResult(
            proposal=proposal,
            applied=True,
            created=True,
            event_name=EVENT_ACTION_PROPOSED,
            event_written=event_written,
        )

    # ------------------------------------------------------------------
    # approve（确认 → 验证 → 落账 → receipt；重复确认恰一次 commit）
    # ------------------------------------------------------------------

    async def approve(
        self,
        proposal_id: UUID | str,
        *,
        user_id: UUID | str,
        actor: str = "user",
        idempotency_key: str | None = None,
        _called_internally: bool = False,
    ) -> ProposalMutationResult:
        """用户确认（或 auto 路径系统确认）→ commit。

        顺序即守卫（全部在 proposal 行锁内）：
        1. 重放复查：已 COMMITTED → 原样返回 receipt（不重复写）；
        2. 终态封闭：其它终态 → 409；
        3. 过期：懒转 EXPIRED（显式持久状态）→ 410；
        4. 授权：confirmation 模式必须有本次确认行为 → 否则 403（未授权不执行）；
        5. commit：**先 stage** 守卫写（status=COMMITTED + receipt + transition +
           outbox），再调命令处理器 execute()——其内部领域服务 commit 会原子携带
           全部 staged 写。守卫与领域写同一次 commit 落账 = 「重复确认恰一次
           commit」的崩溃安全不变量（crash 后要么都没发生、要么都已发生）；
        6. 富化：execute 返回的实际 effects（如 create 型命令的生成 refs）事后
           补进 receipt——增量步骤，丢失只降级 receipt 详尽度，永不破坏恰一次。
        """
        from app.services.action_authorization import authorize_commit

        key = (str(idempotency_key).strip() if idempotency_key else None) or None
        proposal = await self._lock_proposal(proposal_id, user_id=user_id)
        now = _utcnow()

        current = ProposalStatus(proposal.status)
        if current is ProposalStatus.COMMITTED:
            # 幂等重放：receipt 原样奉还，零新写（重复确认不重复写）
            return ProposalMutationResult(
                proposal=proposal,
                applied=False,
                event_name=EVENT_ACTION_ACCEPTED,
                already_committed=True,
            )
        if current in TERMINAL_PROPOSAL_STATUSES:
            raise ProposalNotPendingError(
                f"proposal is {current.value} (terminal); only PENDING proposals can be approved",
                details={"status": current.value, "terminal_reason": proposal.terminal_reason},
            )

        # 过期：显式持久化 EXPIRED（一次写）再拒绝——状态明确，非读时挥发
        if proposal.expires_at is not None and proposal.expires_at <= now:
            await self._terminalize(
                proposal,
                to_status=ProposalStatus.EXPIRED,
                reason=TerminalReason.EXPIRED.value,
                actor="system",
                occurred_at=now,
                key=key,
            )
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
            await self.db.refresh(proposal)
            raise ProposalExpiredError(
                "proposal has expired and is now void (status=EXPIRED)",
                details={"expires_at": proposal.expires_at.isoformat() if proposal.expires_at else None},
            ) from None

        # 授权前置 + stage 守卫写 + 版本校验（SAVEPOINT 内；冲突只回滚保存点）。
        # 授权记录一并放进保存点：冲突时确认痕迹随守卫写一起撤销，proposal 完整
        # 复位 PENDING。版本漂移 → 保存点回滚，**不**触发全 session rollback——
        # 那会使调用方持有的全部 ORM 对象过期（异步上下文外的惰性加载即
        # MissingGreenlet）；保存点回滚只过期保存点内改动的对象（仅 proposal）。
        receipt_id = str(uuid4())
        handler = get_command_handler(proposal.command_type)
        effects: Any = None
        try:
            async with self.db.begin_nested():
                if not _called_internally or actor == "user":
                    proposal.authorization = dict(record_confirmation(proposal.authorization, confirmed_by=actor))
                decision = authorize_commit(proposal.authorization)  # 未授权 → 403，不执行
                receipt = self._build_receipt(
                    proposal,
                    receipt_id=receipt_id,
                    effects=None,  # 确定性 effects 缺省为 diff 派生；实际 effects 落账后富化
                    actor=actor,
                    now=now,
                )
                proposal.status = ProposalStatus.COMMITTED
                proposal.committed_at = now
                proposal.terminal_reason = TerminalReason.COMMITTED.value
                proposal.receipt = receipt
                proposal.authorization = dict(decision)
                transition = ActionProposalTransition(
                    proposal_id=proposal.id,
                    from_status=ProposalStatus.PENDING.value,
                    to_status=ProposalStatus.COMMITTED.value,
                    event_name=EVENT_ACTION_ACCEPTED,
                    actor=str(actor),
                    idempotency_key=key,
                    reason=TerminalReason.COMMITTED.value,
                    details=None,
                    occurred_at=now,
                )
                self.db.add(transition)
                event_written = await self._write_action_event_in_txn(
                    proposal=proposal,
                    event_name=EVENT_ACTION_ACCEPTED,
                    source=EventSource.SERVER_SERVICE,
                    payload={
                        "schema_version": ACTION_COMMAND_PROTOCOL_VERSION,
                        "proposal_id": str(proposal.id),
                        "command_type": proposal.command_type,
                        "receipt_id": receipt_id,
                    },
                )
                # 版本校验（漂移 → VersionConflictError → 保存点回滚，proposal 复位）
                await handler.validate_subject(self.db, proposal=proposal)
        except ActionCommandError:
            # 保存点已回滚：staged 写撤销、proposal 复位 PENDING（重载后抛出清晰
            # 状态）。外层事务不含任何 pending 写，留给请求级 get_db 统一清理——
            # 不在此处全量 rollback（避免误伤调用方持有的其它 ORM 对象）。
            await self.db.refresh(proposal)
            raise

        # --- 执行（保存点已释放；领域服务内部 commit 原子携带 staged 守卫写） ---
        effects = await handler.execute(self.db, proposal=proposal)

        # --- 富化：实际 effects / subject_after / token 补进 receipt（增量） ---
        if effects is not None and (effects.effects or effects.subject_after is not None):
            enriched = dict(proposal.receipt or {})
            enriched["effects"] = effects.effects
            if effects.subject_after is not None:
                enriched["subject_after"] = effects.subject_after
            if effects.subject_version_token_after is not None:
                enriched["subject"] = {
                    **(enriched.get("subject") or {}),
                    "version_token_after": effects.subject_version_token_after,
                }
            proposal.receipt = enriched
            transition.details = {"effects": effects.effects}
        await self.db.commit()  # 领域服务已 commit 时为 no-op 安全网
        await self.db.refresh(proposal)
        return ProposalMutationResult(
            proposal=proposal,
            applied=True,
            event_name=EVENT_ACTION_ACCEPTED,
            event_written=event_written,
        )

    # ------------------------------------------------------------------
    # cancel / reject（取消传播语义与 X-05 user_cancelled 归因对齐）
    # ------------------------------------------------------------------

    async def cancel(
        self,
        proposal_id: UUID | str,
        *,
        user_id: UUID | str,
        reason: str = TerminalReason.USER_CANCELLED.value,
        idempotency_key: str | None = None,
    ) -> ProposalMutationResult:
        """用户取消：PENDING→CANCELLED（终态封闭；重复取消幂等 no-op）."""
        if reason != TerminalReason.USER_CANCELLED.value:
            raise ValueError(f"cancel reason must be {TerminalReason.USER_CANCELLED.value!r}")
        return await self._terminal_user_action(
            proposal_id,
            user_id=user_id,
            to_status=ProposalStatus.CANCELLED,
            reason=TerminalReason.USER_CANCELLED.value,
            idempotency_key=idempotency_key,
        )

    async def reject(
        self,
        proposal_id: UUID | str,
        *,
        user_id: UUID | str,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProposalMutationResult:
        """用户拒绝（确认卡「不要」）：PENDING→REJECTED，与取消语义区分."""
        return await self._terminal_user_action(
            proposal_id,
            user_id=user_id,
            to_status=ProposalStatus.REJECTED,
            reason=TerminalReason.USER_REJECTED.value,
            idempotency_key=idempotency_key,
        )

    async def _terminal_user_action(
        self,
        proposal_id: UUID | str,
        *,
        user_id: UUID | str,
        to_status: ProposalStatus,
        reason: str,
        idempotency_key: str | None,
    ) -> ProposalMutationResult:
        key = (str(idempotency_key).strip() if idempotency_key else None) or None
        proposal = await self._lock_proposal(proposal_id, user_id=user_id)
        current = ProposalStatus(proposal.status)

        if current is to_status:
            # 幂等 no-op：重复取消/拒绝不写第二行审计
            return ProposalMutationResult(proposal=proposal, applied=False, event_name=EVENT_ACTION_REJECTED)
        if current in TERMINAL_PROPOSAL_STATUSES:
            raise ProposalNotPendingError(
                f"proposal is {current.value} (terminal); cannot move to {to_status.value}",
                details={"status": current.value, "terminal_reason": proposal.terminal_reason},
            )

        await self._terminalize(
            proposal,
            to_status=to_status,
            reason=reason,
            actor="user",
            occurred_at=_utcnow(),
            key=key,
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            await self.db.refresh(proposal)
            return ProposalMutationResult(proposal=proposal, applied=False, event_name=EVENT_ACTION_REJECTED)
        await self.db.refresh(proposal)
        return ProposalMutationResult(
            proposal=proposal, applied=True, event_name=EVENT_ACTION_REJECTED, event_written=True
        )

    # ------------------------------------------------------------------
    # 过期 sweep（显式作废；懒转之外的兜底）
    # ------------------------------------------------------------------

    async def expire_stale_proposals(
        self,
        *,
        user_id: UUID | str | None = None,
        limit: int = 200,
    ) -> int:
        """把已过期仍 PENDING 的 proposal 批量转为 EXPIRED（admin/定时）."""
        now = _utcnow()
        stmt = (
            select(ActionProposal)
            .where(
                ActionProposal.status == ProposalStatus.PENDING.value,
                ActionProposal.deleted_at.is_(None),
                ActionProposal.expires_at <= now,
            )
            .limit(max(1, min(int(limit), 1000)))
        )
        if user_id is not None:
            stmt = stmt.where(ActionProposal.user_id == UUID(str(user_id)))
        rows = list((await self.db.execute(stmt)).scalars().all())
        for proposal in rows:
            await self._terminalize(
                proposal,
                to_status=ProposalStatus.EXPIRED,
                reason=TerminalReason.EXPIRED.value,
                actor="system",
                occurred_at=now,
                key=None,
            )
        if rows:
            await self.db.commit()
        return len(rows)

    # ------------------------------------------------------------------
    # 读（权威查询面：proposal / receipt / 列表）
    # ------------------------------------------------------------------

    async def get_proposal(self, proposal_id: UUID | str, *, user_id: UUID | str) -> ActionProposal:
        proposal = (
            await self.db.execute(
                select(ActionProposal).where(
                    ActionProposal.id == UUID(str(proposal_id)),
                    ActionProposal.user_id == UUID(str(user_id)),
                    ActionProposal.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFoundError(f"action proposal {proposal_id} not found")
        return proposal

    async def get_receipt(self, proposal_id: UUID | str, *, user_id: UUID | str) -> dict[str, Any]:
        """UI 权威回执查询（未落账 → 409 语义错误，不返回半成品）."""
        proposal = await self.get_proposal(proposal_id, user_id=user_id)
        if proposal.status is not ProposalStatus.COMMITTED or not proposal.receipt:
            raise ProposalNotPendingError(
                f"proposal {proposal_id} has no receipt yet (status={proposal.status.value})",
                details={"status": proposal.status.value},
            )
        return dict(proposal.receipt)

    async def find_by_idempotency_key(self, user_id: UUID | str, key: str) -> ActionProposal | None:
        return await self._find_by_idempotency_key(UUID(str(user_id)), key)

    async def list_proposals(
        self,
        *,
        user_id: UUID | str,
        status: str | None = None,
        subject_id: UUID | str | None = None,
        limit: int = 50,
    ) -> list[ActionProposal]:
        stmt = select(ActionProposal).where(
            ActionProposal.user_id == UUID(str(user_id)),
            ActionProposal.deleted_at.is_(None),
        )
        if status is not None:
            stmt = stmt.where(ActionProposal.status == ProposalStatus(status).value)
        if subject_id is not None:
            stmt = stmt.where(ActionProposal.subject_id == UUID(str(subject_id)))
        stmt = stmt.order_by(ActionProposal.created_at.desc()).limit(max(1, min(int(limit), 200)))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_transitions(
        self,
        proposal_id: UUID | str,
        *,
        user_id: UUID | str,
        limit: int = 100,
    ) -> list[ActionProposalTransition]:
        await self.get_proposal(proposal_id, user_id=user_id)
        stmt = (
            select(ActionProposalTransition)
            .where(ActionProposalTransition.proposal_id == UUID(str(proposal_id)))
            .order_by(
                ActionProposalTransition.occurred_at.asc(),
                ActionProposalTransition.created_at.asc(),
            )
            .limit(max(1, min(int(limit), 500)))
        )
        return list((await self.db.execute(stmt)).scalars().all())

    def proposal_projection(self, proposal: ActionProposal) -> dict[str, Any]:
        """API 投影（含过期标志的即时计算，读不写库）."""
        now = _utcnow()
        expired = (
            proposal.status is ProposalStatus.PENDING and proposal.expires_at is not None and proposal.expires_at <= now
        )
        return {
            "proposal_id": str(proposal.id),
            "status": proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
            "command_type": proposal.command_type,
            "source": proposal.source,
            "subject_type": proposal.subject_type,
            "subject_id": str(proposal.subject_id) if proposal.subject_id else None,
            "subject_version_token": proposal.subject_version_token,
            "payload": proposal.payload,
            "diff": proposal.diff,
            "authorization": proposal.authorization,
            "risk_class": proposal.risk_class,
            "reversible": proposal.reversible,
            "summary": proposal.summary,
            "idempotency_key": proposal.idempotency_key,
            "expires_at": proposal.expires_at.isoformat() if proposal.expires_at else None,
            "expired": expired,
            "committed_at": proposal.committed_at.isoformat() if proposal.committed_at else None,
            "terminal_reason": proposal.terminal_reason,
            "receipt": proposal.receipt,
            "session_id": proposal.session_id,
            "trace_id": proposal.trace_id,
            "run_id": str(proposal.run_id) if proposal.run_id else None,
            "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
            "protocol_version": ACTION_COMMAND_PROTOCOL_VERSION,
        }

    # ------------------------------------------------------------------
    # 内部（锁/终态/receipt/事件/幂等查找）
    # ------------------------------------------------------------------

    async def _user_auto_grant(self, user_uuid: UUID) -> bool:
        """用户低风险自动授权的**服务端真源**（R2 P2-3 返修）.

        只读 ``UserSettings.low_risk_auto_execute``（用户显式授予；默认 False 保守，
        FV-02 opt-out 同款先例）。无 settings 行 / 未授予 → False。
        授权值不经过任何调用方参数——客户端自授在本路径上不存在。
        """
        granted = (
            await self.db.execute(
                select(UserSettings.low_risk_auto_execute).where(
                    UserSettings.user_id == user_uuid,
                    UserSettings.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return bool(granted)

    async def _resume_or_replay(
        self, existing: ActionProposal, *, execute_if_authorized: bool
    ) -> ProposalMutationResult:
        """幂等早退分支的活性修复（R2 P3 返修）.

        原缺陷：auto 直通在 create-commit 与 inline approve 之间崩溃后，同 key
        重试在此早退返回 PENDING——安全（不双写）但**永不执行**（活性缺陷）。

        修复：proposal 仍 PENDING、创建时记录的授权 mode=auto、且重试仍携带
        执行意图 → 重入 approve 恢复执行。恰一次不变（approve 重放
        already_committed 零新写），过期/终态守卫原样生效；mode 非 auto 或未
        携带执行意图 → 维持原早退语义（重放响应，零新写）。
        """
        if (
            execute_if_authorized
            and ProposalStatus(existing.status) is ProposalStatus.PENDING
            and str((existing.authorization or {}).get("mode", "")) == "auto"
        ):
            return await self.approve(existing.id, user_id=existing.user_id, actor="system", _called_internally=True)
        return ProposalMutationResult(
            proposal=existing,
            applied=True,
            created=False,
            event_name=EVENT_ACTION_PROPOSED,
            event_written=False,
        )

    async def _lock_proposal(self, proposal_id: UUID | str, *, user_id: UUID | str) -> ActionProposal:
        stmt = (
            select(ActionProposal)
            .where(
                ActionProposal.id == UUID(str(proposal_id)),
                ActionProposal.user_id == UUID(str(user_id)),
                ActionProposal.deleted_at.is_(None),
            )
            .with_for_update()  # PG 行锁；sqlite 测试 no-op，由复查+唯一索引兜底（X-05 同法）
        )
        proposal = (await self.db.execute(stmt)).scalar_one_or_none()
        if proposal is None:
            raise ProposalNotFoundError(f"action proposal {proposal_id} not found")
        return proposal

    async def _terminalize(
        self,
        proposal: ActionProposal,
        *,
        to_status: ProposalStatus,
        reason: str,
        actor: str,
        occurred_at: datetime,
        key: str | None,
    ) -> None:
        from_status = ProposalStatus(proposal.status)
        proposal.status = to_status
        proposal.terminal_reason = reason
        self.db.add(
            ActionProposalTransition(
                proposal_id=proposal.id,
                from_status=from_status.value,
                to_status=to_status.value,
                event_name=EVENT_ACTION_REJECTED,
                actor=actor,
                idempotency_key=key,
                reason=reason,
                details=None,
                occurred_at=occurred_at,
            )
        )
        await self._write_action_event_in_txn(
            proposal=proposal,
            event_name=EVENT_ACTION_REJECTED,
            source=EventSource.SERVER_SERVICE,
            payload=self._proposal_payload(proposal, extra={"terminal_reason": reason}),
        )

    def _build_receipt(
        self,
        proposal: ActionProposal,
        *,
        receipt_id: str,
        effects: Any,
        actor: str,
        now: datetime,
    ) -> dict[str, Any]:
        """权威回执：commit 同事务生成、与 proposal 行同生命周期、UI 可查询.

        ``effects=None`` → 守卫版 receipt（effects 由 execute 落账后富化；其前
        diff 已携带 before/after 对照）。守卫版与领域写同 commit——崩溃安全。
        """
        diff = proposal.diff or {}
        return {
            "receipt_id": receipt_id,
            "proposal_id": str(proposal.id),
            "protocol_version": ACTION_COMMAND_PROTOCOL_VERSION,
            "status": ProposalStatus.COMMITTED.value,
            "command_type": proposal.command_type,
            "subject": {
                "type": proposal.subject_type,
                "id": str(proposal.subject_id) if proposal.subject_id else None,
                "version_token_before": proposal.subject_version_token,
                "version_token_after": getattr(effects, "subject_version_token_after", None),
            },
            "diff": diff,
            "effects": list(effects.effects) if effects is not None else [],
            "subject_after": effects.subject_after if effects is not None else diff.get("after"),
            "authorization": proposal.authorization,
            "confirmed_by": actor,
            "committed_at": now.isoformat(timespec="milliseconds"),
            "idempotency_key": proposal.idempotency_key,
            "source": proposal.source,
        }

    def _proposal_payload(self, proposal: ActionProposal, *, extra: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": ACTION_COMMAND_PROTOCOL_VERSION,
            "proposal_id": str(proposal.id),
            "command_type": proposal.command_type,
            "source": proposal.source,
            "status": proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
            "subject_type": proposal.subject_type,
            "subject_id": str(proposal.subject_id) if proposal.subject_id else None,
            "changed_fields": (proposal.diff or {}).get("changed_fields"),
        }
        payload.update(extra)
        return payload

    async def _find_by_idempotency_key(self, user_uuid: UUID, key: str) -> ActionProposal | None:
        return (
            await self.db.execute(
                select(ActionProposal).where(
                    ActionProposal.user_id == user_uuid,
                    ActionProposal.idempotency_key == key,
                    ActionProposal.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    async def _write_action_event_in_txn(
        self,
        *,
        proposal: ActionProposal,
        event_name: str,
        source: EventSource | str,
        payload: dict[str, Any],
    ) -> bool:
        """event_outbox 同事务写入（X-05 _write_run_event_in_txn 同法；词表既有名）."""
        if not await self._outbox_tables_exist():
            logger.warning("action event skipped: event_outbox unavailable proposal_id={}", proposal.id)
            return False

        sequence_number = await self._next_sequence(ACTION_PROPOSAL_AGGREGATE, proposal.id)
        correlation: dict[str, str] = {"action_id": str(proposal.id)}
        if proposal.subject_id:
            correlation["task_id"] = str(proposal.subject_id)  # 任务域命令的 subject 即 task
        if proposal.session_id:
            correlation["session_id"] = proposal.session_id
        if proposal.run_id:
            correlation["run_id"] = str(proposal.run_id)
        metadata = build_event_metadata(
            user_id=proposal.user_id,
            source=source,
            service=ACTION_COMMAND_SERVICE_NAME,
            event_name=event_name,
            aggregate_type=ACTION_PROPOSAL_AGGREGATE,
            aggregate_id=proposal.id,
            sequence_number=sequence_number,
            correlation=CorrelationIds(**correlation),
            extra={"action_command_protocol_version": ACTION_COMMAND_PROTOCOL_VERSION},
        )
        await self.db.execute(
            text("""
                INSERT INTO event_outbox
                (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
                """),
            {
                "aggregate_type": ACTION_PROPOSAL_AGGREGATE,
                "aggregate_id": str(proposal.id),
                "event_type": event_name,
                "sequence_number": sequence_number,
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
                "metadata": json.dumps(metadata, ensure_ascii=False, default=str),
            },
        )
        return True

    async def _outbox_tables_exist(self) -> bool:
        connection = await self.db.connection()
        return await connection.run_sync(lambda sync_conn: _has_table(sync_conn, "event_outbox"))

    async def _next_sequence(self, aggregate_type: str, aggregate_id: UUID) -> int:
        """单调 per-aggregate 序列（X-05 _next_sequence 同法；sqlite 退化读改写）."""
        try:
            result = await self.db.execute(
                text("""
                    INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                    VALUES (:aggregate_type, :aggregate_id, 1)
                    ON CONFLICT (aggregate_type, aggregate_id)
                    DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                    RETURNING next_sequence
                    """),
                {"aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)},
            )
            return int(result.scalar_one())
        except Exception as exc:  # noqa: BLE001 — sqlite 等方言退化读改写
            logger.debug("action event sequence upsert fallback ({})", exc)
            current_result = await self.db.execute(
                text(
                    "SELECT next_sequence FROM event_sequence_counters "
                    "WHERE aggregate_type = :t AND aggregate_id = :a"
                ),
                {"t": aggregate_type, "a": str(aggregate_id)},
            )
            current = current_result.scalar_one_or_none()
            if current is None:
                await self.db.execute(
                    text(
                        "INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence) "
                        "VALUES (:t, :a, 1)"
                    ),
                    {"t": aggregate_type, "a": str(aggregate_id)},
                )
                return 1
            nxt = int(current) + 1
            await self.db.execute(
                text(
                    "UPDATE event_sequence_counters SET next_sequence = :n "
                    "WHERE aggregate_type = :t AND aggregate_id = :a"
                ),
                {"n": nxt, "t": aggregate_type, "a": str(aggregate_id)},
            )
            return nxt


def _has_table(sync_conn, name: str) -> bool:
    from sqlalchemy import inspect

    try:
        return cast("bool", (inspect(sync_conn).has_table(name)))
    except Exception:  # noqa: BLE001
        return False


#: 入口适配层（薄）：chat/task/Aurora 共用的提案构造 sugar——同一权威路径的入口参数化
async def propose_task_status_change(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    task_id: UUID | str,
    to_status: str,
    source: str = ProposalSource.AURORA.value,
    **kwargs: Any,
) -> ProposalMutationResult:
    """入口适配（chat/Aurora/task UI 共用）：提案任务状态变更."""
    return await ActionCommandService(db).create_proposal(
        user_id=user_id,
        command_type="task.update_status",
        payload={"task_id": str(task_id), "to_status": to_status},
        source=source,
        **kwargs,
    )


async def propose_task_field_changes(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    task_id: UUID | str,
    fields: dict[str, Any],
    source: str = ProposalSource.AURORA.value,
    **kwargs: Any,
) -> ProposalMutationResult:
    """入口适配：提案任务字段修改（白名单内）."""
    return await ActionCommandService(db).create_proposal(
        user_id=user_id,
        command_type="task.update_fields",
        payload={"task_id": str(task_id), "fields": fields},
        source=source,
        **kwargs,
    )
