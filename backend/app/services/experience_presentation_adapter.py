"""V4-F03 · 真实状态驱动的反馈呈现适配器（backend 事件面）。

卡 V4-F03：「接既有业务 receipt 到 ExperienceEvent，统一视觉/声/触入口；加入
事件去重、replay 抑制、当前对象 version 校验。」本模块是 backend 侧适配面：
把**既有权威回执**（X-03 action_command 回执/终态行）确定性投影为
``experience_event.v1``（D01 投影器），供移动端统一呈现入口消费。

与既有权威的关系（不造第二权威）：

- **投影器零复制**：commit 投影唯一真源 = D01 ``project_terminal_reason`` /
  ``project_error_state``（``app/core/experience_event.py``；契约 §6 全函数 +
  ``ACTION_INVALID_COMMAND`` fail-loud）。D01 二审挑战 **C-1**（两投影函数无
  生产调用方）由本模块接生产挂点闭合：``approve`` 成功路径 / 过期清扫 /
  approve 错误面（API 层）。
- **copy 语义分层**：``app/core/experience_copy.py``（本卡冻结文案表，契约
  §3 R1-C5 owner 落点）——成功面孔 subject 封闭集（task/goal/plan）之外的
  committed 投影**结构性**拿不到成功模态与任务成功文案（记忆保存 ≠ 任务修改
  完成；证据登记 ≠ 精通：全表无精通类键）。
- **幂等身份（去重/replay 抑制键）**：``event_id``/``dedupe_key`` 内容寻址
  （receipt_ref+kind+version_token，D01 派生）；同权威回执重放恒同 id——重播
  抑制由消费方按 event_id 去重（B05 §3「同 event_id 重播不重复触觉/音效」）。
- **I2 成功必须可溯源**：``kind=state_confirmed`` 投影前双查——proposal.status
  确为 COMMITTED **且** receipt 本体真实存在（receipt_id + status=committed）；
  缺任一 → 可观测拒绝 ``no_authoritative_receipt``，不产成功事件（卡验收 1）。
- **version 校验（当前对象 version 锚定）**：事件 ``subject.version_token`` 只
  取权威回执链（receipt.subject.version_token_after → before → proposal 期
  token）；全链缺失 → 拒绝投影（``subject_version_missing``）——去重身份无锚
  即拒绝，不猜版本、不以空值冒充（回执 input_versions 纪律同源）。
- **发布走既有 EventBus**（D01 同主题 ``experience.event_projected``，非新
  总线）；发布失败只留痕（韧性壳），投影结果恒可重放。生产挂点默认
  ``event_bus=None``（与生产 mark_seen 调用方形态一致：投影成立、发布随
  consumer 形态注入——D01 二审 §3 同款判定）。

生产挂点（全部韧性壳、additive、零宿主语义变更）：
- ``ActionCommandService.approve`` 成功落账后 → ``project_action_receipt_safe``
- ``ActionCommandService.expire_stale_proposals`` 每条过期转场 → 同上（expired 面）
- API ``approve_proposal`` 错误面（ActionCommandError）→ ``project_action_error_safe``
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import ActionCommandError, ProposalStatus
from app.core.experience_copy import (
    EVIDENCE_REGISTERED_COPY_KEY,
    KIND_COPY_KEY,
    SUCCESS_FACE_SUBJECT_TYPES,
    copy_key_for_committed_subject,
    copy_key_for_error_state,
)
from app.core.experience_event import (
    EXPERIENCE_EVENT_SCHEMA_VERSION,
    SUBJECT_TYPE_VOCABULARY,
    ExperienceCommitState,
    ExperienceEvent,
    ExperienceEventKind,
    ExperienceEventValidationError,
    ExperiencePresentation,
    ExperienceProjectionRefused,
    ExperienceSubject,
    project_error_state,
    project_terminal_reason,
)
from app.models.action_proposal import ActionProposal
from app.services.experience_event_service import EXPERIENCE_EVENT_TOPIC

EXPERIENCE_PRESENTATION_ADAPTER_VERSION = "experience-presenter.f03.v1"

#: 拒绝原因词表（可观测降级面，封闭；D01 二审挑战 C-2：降级必可观测，不静默）。
REFUSED_NOT_TERMINAL = "not_terminal_no_receipt"
REFUSED_USER_ACTION_SKIP = "user_action_terminal_skip"
REFUSED_NO_AUTHORITATIVE_RECEIPT = "no_authoritative_receipt"
REFUSED_SUBJECT_VERSION_MISSING = "subject_version_missing"
REFUSED_SUBJECT_UNANCHORABLE = "subject_unanchorable"

#: committed + 成功面孔 subject 的呈现模态（视觉/声/触统一入口；庆祝类唯一入口）。
_SUCCESS_MODALITIES: tuple[str, ...] = ("visual", "audio", "haptic")
#: 非 success face committed / 失败面模态（中性呈现：无庆祝音/触）。
_INFO_MODALITIES: tuple[str, ...] = ("visual",)


@dataclass(frozen=True)
class ExperiencePresentationResult:
    """一次呈现投影的结果（三态可观测：投影 / 拒绝 / fail-loud 上抛）。"""

    projected: bool
    reason: str
    event_id: str = ""
    dedupe_key: str = ""
    kind: str = ""
    commit_state: str = ""
    receipt_ref: str | None = None
    event: dict[str, Any] | None = None
    published: bool = False


def _refused(reason: str, *, proposal: ActionProposal | None = None) -> ExperiencePresentationResult:
    logger.info(
        "ExperiencePresentation: not projected (reason={}, proposal={})",
        reason,
        getattr(proposal, "id", "-") if proposal is not None else "-",
    )
    return ExperiencePresentationResult(projected=False, reason=reason)


def _receipt_ref_for(proposal: ActionProposal) -> str:
    return f"action_command://{proposal.id}"


def _receipt_subject_token(proposal: ActionProposal) -> str | None:
    """权威回执链取版本位（after → before → proposal 期 token；全链缺失返回 None）。"""
    receipt = proposal.receipt if isinstance(proposal.receipt, dict) else {}
    subject = receipt.get("subject") if isinstance(receipt.get("subject"), dict) else {}
    for candidate in (
        subject.get("version_token_after"),
        subject.get("version_token_before"),
        proposal.subject_version_token,
    ):
        token = str(candidate).strip() if candidate is not None else ""
        if token:
            return token
    return None


def _normalized_subject_type(proposal: ActionProposal) -> str | None:
    """proposal.subject_type → 封闭词表值；空/词表外返回 None（调用方拒绝）。"""
    raw = str(proposal.subject_type or "").strip().lower()
    return raw if raw in SUBJECT_TYPE_VOCABULARY else None


def _authoritative_receipt_ok(proposal: ActionProposal) -> bool:
    """I2 第二门（本适配面）：receipt 本体真实存在且自洽（committed 面专用）。"""
    status = getattr(proposal.status, "value", str(proposal.status))
    if status != ProposalStatus.COMMITTED.value:
        return False
    receipt = proposal.receipt
    if not isinstance(receipt, dict):
        return False
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    receipt_status = str(receipt.get("status") or "").strip()
    return bool(receipt_id) and receipt_status == ProposalStatus.COMMITTED.value


class ExperiencePresentationAdapter:
    """既有业务回执 → experience_event.v1 投影适配器（统一呈现入口的服务面）。"""

    def __init__(self, db: AsyncSession | None, event_bus: Any | None = None):
        self._db = db
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # X-03 权威回执面（C-1：project_terminal_reason / project_error_state
    # 的生产调用方；commit_state 唯一真源 = X-03 终态/错误码）
    # ------------------------------------------------------------------

    async def project_action_receipt(
        self,
        proposal: ActionProposal,
        *,
        issued_at: datetime | None = None,
        publish: bool = True,
    ) -> ExperiencePresentationResult:
        """把 X-03 proposal 的终态/回执投影成呈现事件（幂等、可重放）。

        - ``committed`` → ``kind=state_confirmed``（I2 双门：status + receipt 本体）；
        - ``expired`` → ``kind=terminal_failed`` + ``error_state=expired``；
        - ``user_cancelled``/``user_rejected`` → 不产事件（契约 §6：用户亲自
          取消/拒绝即时可知，补发属呈现噪音）；
        - 终态前/词表外 → 拒绝或 fail-loud（词表外终态 = 上游漂移）。
        """
        if not proposal.terminal_reason:
            return _refused(REFUSED_NOT_TERMINAL, proposal=proposal)
        subject_type = _normalized_subject_type(proposal)
        if subject_type is None:
            # 词表外/缺失 subject：无可锚对象域，不产对象级呈现事件（如实拒绝，
            # 不造泛化成功——create 型命令属此面，见 limitations）。
            return _refused(REFUSED_SUBJECT_UNANCHORABLE, proposal=proposal)
        projection = project_terminal_reason(proposal.terminal_reason)  # 词表外 fail-loud 上抛
        if projection is None:
            return _refused(REFUSED_USER_ACTION_SKIP, proposal=proposal)

        commit_state, error_state = projection
        if commit_state == ExperienceCommitState.COMMITTED:
            if not _authoritative_receipt_ok(proposal):
                # I2：无 committed 权威回执 → 绝不触发成功类呈现（卡验收 1 反例面）。
                return _refused(REFUSED_NO_AUTHORITATIVE_RECEIPT, proposal=proposal)
            kind = ExperienceEventKind.STATE_CONFIRMED.value
            copy_key = copy_key_for_committed_subject(subject_type)
        else:
            kind = ExperienceEventKind.TERMINAL_FAILED.value
            copy_key = copy_key_for_error_state(error_state.value)

        return await self._project(
            proposal=proposal,
            kind=kind,
            commit_state=commit_state.value,
            error_state=error_state.value if error_state is not None else None,
            copy_key=copy_key,
            issued_at=issued_at,
            publish=publish,
        )

    async def project_action_error(
        self,
        proposal: ActionProposal,
        error: ActionCommandError,
        *,
        issued_at: datetime | None = None,
        publish: bool = True,
    ) -> ExperiencePresentationResult:
        """X-03 命令错误面 → ``kind=terminal_failed``（``project_error_state`` 生产路径）。

        ``ACTION_INVALID_COMMAND`` → :class:`ExperienceProjectionRefused` 上抛
        （契约 §6 断言：该码不产权威回执，出现即上游漂移，fail-loud）。
        """
        error_state = project_error_state(error.error_code)
        return await self._project(
            proposal=proposal,
            kind=ExperienceEventKind.TERMINAL_FAILED.value,
            commit_state=ExperienceCommitState.ERROR.value,
            error_state=error_state.value,
            copy_key=copy_key_for_error_state(error_state.value),
            issued_at=issued_at,
            publish=publish,
        )

    # ------------------------------------------------------------------
    # 通用回执面（证据登记等既有权威回执的最小投影入口；语义分层由
    # experience_copy 封闭路由结构性保证）
    # ------------------------------------------------------------------

    async def project_feedback_receipt(
        self,
        *,
        kind: str,
        receipt_ref: str,
        subject_type: str,
        subject_id: str,
        version_token: str,
        issued_at: datetime | None = None,
        publish: bool = True,
    ) -> ExperiencePresentationResult:
        """非 X-03 域既有回执（证据登记/进度等）的统一投影入口。

        ``copy_key`` 与模态由封闭路由按 kind/subject/ref-scheme 决定（调用方
        **不可**指定成功文案）：证据登记（``outcome://`` ref + progress_delta）
        恒得 ``evidence.registered``（「证据已登记」，全表无精通词）；成功模态
        仅对 SUCCESS_FACE_SUBJECT_TYPES 的 committed 投影开放。
        """
        subject_type = str(subject_type).strip().lower()
        if subject_type not in SUBJECT_TYPE_VOCABULARY:
            raise ExperienceEventValidationError(f"subject_type {subject_type!r} outside closed vocabulary")
        success_face = kind == ExperienceEventKind.STATE_CONFIRMED.value and subject_type in SUCCESS_FACE_SUBJECT_TYPES
        try:
            event = ExperienceEvent.project(
                kind=kind,
                commit_state=ExperienceCommitState.COMMITTED.value,
                receipt_ref=receipt_ref,
                subject=ExperienceSubject(
                    type=subject_type,
                    id=subject_id,
                    version_token=version_token,
                ),
                presentation=ExperiencePresentation(
                    modalities=_SUCCESS_MODALITIES if success_face else _INFO_MODALITIES,
                    copy_key=_copy_key_for_receipt(kind=kind, receipt_ref=receipt_ref, subject_type=subject_type),
                ),
                issued_at=issued_at or datetime.utcnow(),
                expires_at=None,
            )
        except ExperienceEventValidationError:
            raise
        published = await self._publish(event) if publish else False
        return ExperiencePresentationResult(
            projected=True,
            reason="",
            event_id=event.event_id,
            dedupe_key=event.dedupe_key,
            kind=kind,
            commit_state=ExperienceCommitState.COMMITTED.value,
            receipt_ref=receipt_ref,
            event=event.to_dict(),
            published=published,
        )

    async def replay_action_receipt(
        self,
        proposal: ActionProposal,
        *,
        issued_at: datetime | None = None,
    ) -> ExperiencePresentationResult:
        """丢事件重放：按权威回执重算（确定性——恒同 event_id/dedupe_key）。"""
        return await self.project_action_receipt(proposal, issued_at=issued_at, publish=True)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _project(
        self,
        *,
        proposal: ActionProposal,
        kind: str,
        commit_state: str,
        error_state: str | None,
        copy_key: str,
        issued_at: datetime | None,
        publish: bool,
    ) -> ExperiencePresentationResult:
        subject_type = _normalized_subject_type(proposal)
        if subject_type is None:
            # 词表外/缺失 subject：无可锚对象域，不产对象级呈现事件（如实拒绝，
            # 不造泛化成功——create 型命令属此面，见 limitations）。
            return _refused(REFUSED_SUBJECT_UNANCHORABLE, proposal=proposal)
        version_token = _receipt_subject_token(proposal)
        if version_token is None:
            # version 全链缺失：去重身份无锚 → 拒绝投影（不猜版本、不冒充）。
            return _refused(REFUSED_SUBJECT_VERSION_MISSING, proposal=proposal)
        subject_id = str(proposal.subject_id) if proposal.subject_id else ""
        if not subject_id:
            return _refused(REFUSED_SUBJECT_UNANCHORABLE, proposal=proposal)
        success_face = subject_type in SUCCESS_FACE_SUBJECT_TYPES and error_state is None
        receipt_ref = _receipt_ref_for(proposal)
        try:
            event = ExperienceEvent.project(
                kind=kind,
                commit_state=commit_state,
                receipt_ref=receipt_ref,
                error_state=error_state,
                subject=ExperienceSubject(
                    type=subject_type,
                    id=subject_id,
                    version_token=version_token,
                ),
                presentation=ExperiencePresentation(
                    modalities=_SUCCESS_MODALITIES if success_face else _INFO_MODALITIES,
                    copy_key=copy_key,
                ),
                issued_at=issued_at or datetime.utcnow(),
                expires_at=None,
            )
        except ExperienceEventValidationError:
            raise
        published = await self._publish(event) if publish else False
        return ExperiencePresentationResult(
            projected=True,
            reason="",
            event_id=event.event_id,
            dedupe_key=event.dedupe_key,
            kind=kind,
            commit_state=commit_state,
            receipt_ref=receipt_ref,
            event=event.to_dict(),
            published=published,
        )

    async def _publish(self, event: ExperienceEvent) -> bool:
        """既有总线发布（韧性壳：失败只留痕，投影恒可重放；无 bus 则跳过）。"""
        if self._event_bus is None:
            return False
        try:
            await self._event_bus.publish(
                EXPERIENCE_EVENT_TOPIC,
                {
                    "schema_version": EXPERIENCE_EVENT_SCHEMA_VERSION,
                    "adapter_version": EXPERIENCE_PRESENTATION_ADAPTER_VERSION,
                    "event_id": event.event_id,
                    "dedupe_key": event.dedupe_key,
                    "event": event.to_dict(),
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001 — 发布失败不拖垮宿主链路
            logger.warning("ExperiencePresentation: publish failed (event_id={}): {}", event.event_id, exc)
            return False


def _copy_key_for_receipt(*, kind: str, receipt_ref: str, subject_type: str) -> str:
    """通用回执面的封闭 copy 路由（调用方不可指定成功文案）。

    - ``state_confirmed`` → committed 路由（按 subject，成功面孔之外即域内文案）；
    - ``progress_delta`` + ``outcome://`` ref → ``evidence.registered``（证据登记，
      D-02 分级语义：登记 ≠ 精通）；其余 progress → ``progress.delta``；
    - 其余 kind → KIND_COPY_KEY。
    """
    if kind == ExperienceEventKind.STATE_CONFIRMED.value:
        return copy_key_for_committed_subject(subject_type)
    if kind == ExperienceEventKind.PROGRESS_DELTA.value:
        scheme = receipt_ref.split("://", 1)[0]
        if scheme == "outcome":
            return EVIDENCE_REGISTERED_COPY_KEY
        return KIND_COPY_KEY[ExperienceEventKind.PROGRESS_DELTA.value]
    key = KIND_COPY_KEY.get(kind)
    if key is None:
        raise ExperienceEventValidationError(f"kind {kind!r} has no copy route (closed router)")
    return key


# ---------------------------------------------------------------------------
# 韧性壳挂点（FIX-507/D01 判例同款：呈现投影永不拖垮宿主链路）
# ---------------------------------------------------------------------------


async def project_action_receipt_safe(
    db: AsyncSession | None,
    event_bus: Any | None,
    proposal: ActionProposal,
    *,
    publish: bool = False,
) -> ExperiencePresentationResult | None:
    """``approve`` 成功路径 / 过期清扫的挂点（任何异常只 warning，不拖垮 commit）。"""
    try:
        return await ExperiencePresentationAdapter(db, event_bus).project_action_receipt(proposal, publish=publish)
    except ExperienceProjectionRefused as exc:
        logger.warning(
            "ExperiencePresentation: projection refused (proposal={}): {}",
            getattr(proposal, "id", "-"),
            exc,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — 韧性壳
        logger.warning(
            "ExperiencePresentation: projection failed (proposal={}): {}",
            getattr(proposal, "id", "-"),
            exc,
        )
        return None


async def project_action_error_safe(
    db: AsyncSession | None,
    event_bus: Any | None,
    proposal: ActionProposal,
    error: ActionCommandError,
    *,
    publish: bool = False,
) -> ExperiencePresentationResult | None:
    """approve 错误面挂点（API 层 ActionCommandError → terminal_failed 呈现）。

    ``ACTION_INVALID_COMMAND`` fail-loud 同样被韧性壳转为可观测 warning——
    呈现挂点永不拖垮宿主请求，但漂移必留痕（不静默吞）。
    """
    try:
        return await ExperiencePresentationAdapter(db, event_bus).project_action_error(proposal, error, publish=publish)
    except ExperienceProjectionRefused as exc:
        logger.warning(
            "ExperiencePresentation: error projection refused (proposal={}, code={}): {}",
            getattr(proposal, "id", "-"),
            getattr(error, "error_code", "-"),
            exc,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — 韧性壳
        logger.warning(
            "ExperiencePresentation: error projection failed (proposal={}): {}",
            getattr(proposal, "id", "-"),
            exc,
        )
        return None


async def project_action_error_by_id_safe(
    db: AsyncSession | None,
    event_bus: Any | None,
    *,
    proposal_id: Any,
    user_id: Any,
    error: ActionCommandError,
    publish: bool = False,
) -> ExperiencePresentationResult | None:
    """API 错误面挂点：按 proposal_id 取行后投影 terminal_failed。

    行不存在/查询失败 → 可观测跳过（NOT_FOUND 类错误本就无对象可呈现）；
    其余语义同 :func:`project_action_error_safe`。
    """
    import uuid as _uuid

    from sqlalchemy import select

    try:
        row = (
            await db.execute(  # type: ignore[union-attr]
                select(ActionProposal).where(
                    ActionProposal.id == _uuid.UUID(str(proposal_id)),
                    ActionProposal.user_id == _uuid.UUID(str(user_id)),
                    ActionProposal.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 — 韧性壳
        logger.warning("ExperiencePresentation: error projection lookup failed (proposal={}): {}", proposal_id, exc)
        return None
    if row is None:
        return None
    return await project_action_error_safe(db, event_bus, row, error, publish=publish)


__all__ = [
    "EXPERIENCE_PRESENTATION_ADAPTER_VERSION",
    "ExperiencePresentationAdapter",
    "ExperiencePresentationResult",
    "project_action_error_by_id_safe",
    "project_action_error_safe",
    "project_action_receipt_safe",
]
