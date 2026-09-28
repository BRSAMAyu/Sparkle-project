"""V4-F03 · 真实状态驱动的反馈呈现适配器（backend 事件面）集成守卫。

验收对照（卡 V4-F03，B05 §3/§6 契约）：
- **验收 1（正）**：committed 权威回执 → ``kind=state_confirmed``/``committed``
  成功呈现事件，身份内容寻址（同回执重放恒同 event_id——消费方去重键）；
- **验收 1（反）**：无 committed 回执（PENDING / 状态谎报无 receipt / receipt
  本体缺失 / 用户取消拒绝）→ 零成功事件，可观测拒绝；
- **验收 2**：反馈语义与状态语义严格分层——subject 封闭路由（memory ≠ 任务
  成功文案）、证据登记 = ``evidence.registered``、全文案表禁词扫描（精通/已掌握
  无处可拼）；
- **验收 3**：expired → ``terminal_failed`` + ``error_state=expired``，模态恒
  中性（无 audio/haptic），``kind`` 永非 ``state_confirmed``；
- **C-1 闭合**：``project_terminal_reason``/``project_error_state`` 接生产路径，
  ``ACTION_INVALID_COMMAND`` fail-loud 从生产面可触发；
- **C-2 闭合**：mark_seen 挂点不再丢弃降级结果（可观测 warning）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.action_command import (
    ACTION_ERROR_CODES,
    ActionCommandError,
    ProposalStatus,
)
from app.core.experience_copy import (
    COMMITTED_COPY_KEY_BY_SUBJECT,
    ERROR_STATE_COPY_KEY,
    EXPERIENCE_COPY_TABLE,
    KIND_COPY_KEY,
    SUCCESS_FACE_SUBJECT_TYPES,
    copy_key_for_committed_subject,
)
from app.core.experience_event import (
    ExperienceProjectionRefused,
    derive_experience_event_id,
)
from app.models.action_proposal import ActionProposal
from app.services.experience_presentation_adapter import (
    REFUSED_NO_AUTHORITATIVE_RECEIPT,
    REFUSED_NOT_TERMINAL,
    REFUSED_SUBJECT_UNANCHORABLE,
    REFUSED_SUBJECT_VERSION_MISSING,
    REFUSED_USER_ACTION_SKIP,
    ExperiencePresentationAdapter,
    project_action_error_by_id_safe,
    project_action_error_safe,
    project_action_receipt_safe,
)

_FORBIDDEN_MASTERY_MARKERS = ("精通", "已掌握", "掌握度", "mastery", "mastered")
_TASK_SUCCESS_MARKERS = ("任务已",)


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "event-id"


def _make_proposal(db, user_id, **overrides) -> ActionProposal:
    now = datetime.now(UTC).replace(tzinfo=None)
    defaults: dict = {
        "id": uuid4(),
        "user_id": user_id,
        "status": ProposalStatus.PENDING,
        "command_type": "task.update_status",
        "source": "task",
        "subject_type": "task",
        "subject_id": uuid4(),
        "subject_version_token": "2026-09-28T00:00:00",
        "payload": {"task_id": str(uuid4())},
        "authorization": {"mode": "confirmation"},
        "expires_at": now + timedelta(minutes=30),
    }
    defaults.update(overrides)
    proposal = ActionProposal(**defaults)
    db.add(proposal)
    return proposal


def _committed_receipt(proposal: ActionProposal, *, version_after: str = "v-after") -> dict:
    return {
        "receipt_id": str(uuid4()),
        "proposal_id": str(proposal.id),
        "protocol_version": "action_command.v1",
        "status": ProposalStatus.COMMITTED.value,
        "command_type": proposal.command_type,
        "subject": {
            "type": proposal.subject_type,
            "id": str(proposal.subject_id) if proposal.subject_id else None,
            "version_token_before": proposal.subject_version_token,
            "version_token_after": version_after,
        },
        "effects": [],
        "confirmed_by": "user",
        "committed_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
    }


# ---------------------------------------------------------------------------
# 验收 1（正）：committed 回执 → 成功呈现事件 + 内容寻址身份
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_committed_receipt_projects_success_event(db_session, test_user):
    proposal = _make_proposal(
        db_session,
        test_user.id,
        status=ProposalStatus.COMMITTED,
        terminal_reason="committed",
    )
    proposal.receipt = _committed_receipt(proposal)
    await db_session.flush()
    adapter = ExperiencePresentationAdapter(db_session, FakeEventBus())
    result = await adapter.project_action_receipt(proposal)

    assert result.projected is True
    assert result.kind == "state_confirmed"
    assert result.commit_state == "committed"
    assert result.receipt_ref == f"action_command://{proposal.id}"
    event = result.event
    assert event["presentation"]["copy_key"] == "task.committed"
    assert event["presentation"]["modalities"] == ["visual", "audio", "haptic"]
    # version 锚定：优先 receipt.subject.version_token_after
    assert event["subject"]["version_token"] == "v-after"


@pytest.mark.asyncio
async def test_receipt_identity_is_content_addressed_and_replay_stable(db_session, test_user):
    """同权威回执重放恒同 event_id/dedupe_key（消费方按 id 去重即重播抑制）。"""
    proposal = _make_proposal(
        db_session,
        test_user.id,
        status=ProposalStatus.COMMITTED,
        terminal_reason="committed",
    )
    proposal.receipt = _committed_receipt(proposal)
    adapter = ExperiencePresentationAdapter(db_session, FakeEventBus())

    first = await adapter.project_action_receipt(proposal, issued_at=datetime(2026, 9, 28))
    second = await adapter.replay_action_receipt(proposal, issued_at=datetime(2030, 1, 1))

    assert first.projected and second.projected
    assert first.event_id == second.event_id
    assert first.dedupe_key == second.dedupe_key
    assert first.event_id == derive_experience_event_id(first.dedupe_key)


# ---------------------------------------------------------------------------
# 验收 1（反）：无 committed 回执不能触发成功
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_proposal_projects_nothing(db_session, test_user):
    proposal = _make_proposal(db_session, test_user.id)  # PENDING、无终态
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
    assert result.projected is False
    assert result.reason == REFUSED_NOT_TERMINAL
    assert result.event is None


@pytest.mark.asyncio
async def test_committed_status_without_receipt_body_is_refused(db_session, test_user):
    """状态谎报 COMMITTED 但 receipt 本体缺失 → 拒绝（I2：成功必须可溯源）。"""
    proposal = _make_proposal(db_session, test_user.id, status=ProposalStatus.COMMITTED, terminal_reason="committed")
    proposal.receipt = None
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
    assert result.projected is False
    assert result.reason == REFUSED_NO_AUTHORITATIVE_RECEIPT


@pytest.mark.asyncio
async def test_receipt_body_without_committed_status_is_refused(db_session, test_user):
    proposal = _make_proposal(db_session, test_user.id, status=ProposalStatus.COMMITTED, terminal_reason="committed")
    receipt = _committed_receipt(proposal)
    receipt["status"] = "PENDING"  # 回执体不自洽
    proposal.receipt = receipt
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
    assert result.projected is False
    assert result.reason == REFUSED_NO_AUTHORITATIVE_RECEIPT


@pytest.mark.asyncio
async def test_user_cancelled_and_rejected_produce_no_event(db_session, test_user):
    for reason in ("user_cancelled", "user_rejected"):
        proposal = _make_proposal(db_session, test_user.id, status=ProposalStatus.CANCELLED, terminal_reason=reason)
        result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
        assert result.projected is False
        assert result.reason == REFUSED_USER_ACTION_SKIP


@pytest.mark.asyncio
async def test_missing_version_chain_is_refused_not_guessed(db_session, test_user):
    """version 全链缺失 → 拒绝（去重身份无锚，不猜版本）。"""
    proposal = _make_proposal(
        db_session,
        test_user.id,
        status=ProposalStatus.COMMITTED,
        terminal_reason="committed",
        subject_version_token=None,
    )
    receipt = _committed_receipt(proposal)
    receipt["subject"]["version_token_before"] = None
    receipt["subject"]["version_token_after"] = None
    proposal.receipt = receipt
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
    assert result.projected is False
    assert result.reason == REFUSED_SUBJECT_VERSION_MISSING


@pytest.mark.asyncio
async def test_subjectless_command_is_refused(db_session, test_user):
    """create 型命令（无 subject）：不产对象级呈现事件，不造泛化成功。"""
    proposal = _make_proposal(
        db_session,
        test_user.id,
        command_type="task.create_batch",
        subject_type=None,
        subject_id=None,
        status=ProposalStatus.COMMITTED,
        terminal_reason="committed",
    )
    proposal.receipt = _committed_receipt(proposal)
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)
    assert result.projected is False
    assert result.reason == REFUSED_SUBJECT_UNANCHORABLE


# ---------------------------------------------------------------------------
# 验收 3：过期 = 错误面（terminal_failed），永不成功视觉
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_terminal_projects_failure_never_success(db_session, test_user):
    proposal = _make_proposal(db_session, test_user.id, status=ProposalStatus.EXPIRED, terminal_reason="expired")
    result = await ExperiencePresentationAdapter(db_session).project_action_receipt(proposal)

    assert result.projected is True
    assert result.kind == "terminal_failed"
    assert result.commit_state == "error"
    event = result.event
    assert event["error_state"] == "expired"
    assert event["presentation"]["copy_key"] == "err.expired"
    # 错误面模态恒中性：无 audio/haptic，不借成功声/触
    assert event["presentation"]["modalities"] == ["visual"]
    assert event["kind"] != "state_confirmed"


# ---------------------------------------------------------------------------
# C-1 闭合：project_error_state 生产路径 + ACTION_INVALID_COMMAND fail-loud
# ---------------------------------------------------------------------------


class _FakeInvalidCommandError(ActionCommandError):
    error_code = ACTION_ERROR_CODES["INVALID_COMMAND"]


@pytest.mark.asyncio
async def test_invalid_command_error_is_fail_loud_on_production_path(db_session, test_user):
    proposal = _make_proposal(db_session, test_user.id)
    adapter = ExperiencePresentationAdapter(db_session)
    with pytest.raises(ExperienceProjectionRefused):
        await adapter.project_action_error(proposal, _FakeInvalidCommandError("bad command"))


@pytest.mark.asyncio
async def test_version_conflict_error_projects_failure_event(db_session, test_user):
    proposal = _make_proposal(db_session, test_user.id)
    error = ActionCommandError("version drifted")
    error.error_code = ACTION_ERROR_CODES["VERSION_CONFLICT"]
    result = await ExperiencePresentationAdapter(db_session).project_action_error(proposal, error)

    assert result.projected is True
    assert result.kind == "terminal_failed"
    assert result.event["error_state"] == "version_conflict"
    assert result.event["presentation"]["copy_key"] == "err.version_conflict"
    assert result.event["presentation"]["modalities"] == ["visual"]


@pytest.mark.asyncio
async def test_safe_hooks_never_raise_and_observe_refusal(db_session, test_user):
    """韧性壳：Refused/异常 → None + 留痕，宿主链路（commit/HTTP）不被拖垮。"""
    proposal = _make_proposal(db_session, test_user.id)  # PENDING → not_terminal 拒绝
    ok = await project_action_receipt_safe(db_session, None, proposal)
    assert ok is not None and ok.projected is False

    with pytest.raises(ExperienceProjectionRefused):
        await ExperiencePresentationAdapter(db_session).project_action_error(proposal, _FakeInvalidCommandError("bad"))
    swallowed = await project_action_error_safe(db_session, None, proposal, _FakeInvalidCommandError("bad"))
    assert swallowed is None  # fail-loud 被壳转为可观测留痕

    missing = await project_action_error_by_id_safe(
        db_session, None, proposal_id=uuid4(), user_id=test_user.id, error=ActionCommandError("x")
    )
    assert missing is None  # 行不存在 → 可观测跳过


# ---------------------------------------------------------------------------
# 验收 2：反馈语义与状态语义严格分层
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_registration_routes_to_registered_copy_never_mastery(db_session, test_user):
    """证据登记（outcome:// 回执 + progress_delta）→ evidence.registered。"""
    adapter = ExperiencePresentationAdapter(db_session)
    result = await adapter.project_feedback_receipt(
        kind="progress_delta",
        receipt_ref=f"outcome://{uuid4()}",
        subject_type="task",
        subject_id=str(uuid4()),
        version_token="v1",
    )
    assert result.projected is True
    assert result.event["presentation"]["copy_key"] == "evidence.registered"
    assert result.event["presentation"]["modalities"] == ["visual"]


def test_copy_table_semantic_layering_is_structural():
    """冻结表的分层保证（结构性，不靠自觉）：

    - memory 域路由 → ``memory.saved``，永不落在任务成功文案；
    - 成功面孔封闭集 = {task, goal, plan}，memory/run/intervention 不在内；
    - 全表禁词扫描：无精通/已掌握类键或文案（证据登记 ≠ 精通，I07 概念预接
      不越锁面）。
    """
    assert COMMITTED_COPY_KEY_BY_SUBJECT["memory"] == "memory.saved"
    assert "memory" not in SUCCESS_FACE_SUBJECT_TYPES
    assert "run" not in SUCCESS_FACE_SUBJECT_TYPES
    assert "intervention" not in SUCCESS_FACE_SUBJECT_TYPES
    assert "task.committed" not in COMMITTED_COPY_KEY_BY_SUBJECT.values() or (
        COMMITTED_COPY_KEY_BY_SUBJECT["task"] == "task.committed"
    )
    # memory 路由的文案不是任务成功文案
    memory_copy = EXPERIENCE_COPY_TABLE[COMMITTED_COPY_KEY_BY_SUBJECT["memory"]]
    assert memory_copy == "记忆已保存"
    assert not any(marker in memory_copy for marker in _TASK_SUCCESS_MARKERS)
    # 证据登记键存在且非精通语义
    evidence_copy = EXPERIENCE_COPY_TABLE["evidence.registered"]
    assert evidence_copy == "证据已登记"
    # 全表禁词
    for key, copy in EXPERIENCE_COPY_TABLE.items():
        for marker in _FORBIDDEN_MASTERY_MARKERS:
            assert marker not in key, key
            assert marker not in copy, (key, copy)


@pytest.mark.asyncio
async def test_mark_seen_hook_observes_degraded_projection(db_session, test_user):
    """C-2 闭合：mark_seen 挂点不再丢弃投影结果——降级 reason 进可观测面。

    权威回执行被删（I2 双门第二门失败）→ SEEN 转场照常成立、呈现降级
    ``no_authoritative_receipt``，且挂点以稳定前缀 ``experience_presentation.
    degraded`` 留 warning（运维可 grep 计数）。
    """
    from loguru import logger
    from sqlalchemy import delete

    from app.models.card_protocol import (
        DeliveryChannel,
        DeliveryStrategy,
        InterventionTriggerType,
    )
    from app.models.intervention_lifecycle import InterventionLifecycleEvent
    from app.services.intervention_record_service import InterventionRecordService

    service = InterventionRecordService(db_session, FakeEventBus())
    record = await service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        diagnosis_payload={"reasons": ["progress_lag"]},
    )
    await service.mark_delivered(record.id)  # 交付面：正常路径会落 D-05 exposed 行
    await db_session.execute(delete(InterventionLifecycleEvent))  # 删行模拟回执缺失
    await db_session.flush()

    logs: list[str] = []
    sink_id = logger.add(lambda message: logs.append(str(message)), level="WARNING")
    try:
        seen = await service.mark_seen(record.id)
        assert seen is not None and seen.acceptance_status.value == "SEEN"
    finally:
        logger.remove(sink_id)
    assert any(
        "experience_presentation.degraded" in line and "no_authoritative_receipt" in line for line in logs
    ), logs[-5:]


@pytest.mark.asyncio
async def test_committed_receipt_publishes_on_existing_topic(db_session, test_user):
    """发布走既有 EventBus 单主题（experience.event_projected），非新总线。"""
    from app.services.experience_event_service import EXPERIENCE_EVENT_TOPIC

    bus = FakeEventBus()
    proposal = _make_proposal(db_session, test_user.id, status=ProposalStatus.COMMITTED, terminal_reason="committed")
    proposal.receipt = _committed_receipt(proposal)
    result = await ExperiencePresentationAdapter(db_session, bus).project_action_receipt(proposal)

    assert result.projected is True and result.published is True
    topics = [name for name, _ in bus.events]
    assert topics and set(topics) == {EXPERIENCE_EVENT_TOPIC}
    payload = bus.events[0][1]
    assert payload["event"]["event_id"] == result.event_id


def test_copy_routers_are_closed_and_pinned():
    """路由封闭：键集逐字面冻结（扩展 = 契约变更，测试先红）。"""
    assert set(COMMITTED_COPY_KEY_BY_SUBJECT) == {"task", "goal", "plan", "memory", "run", "intervention"}
    assert set(ERROR_STATE_COPY_KEY) == {
        "version_conflict",
        "unauthorized",
        "not_pending",
        "expired",
        "not_found",
    }
    assert set(KIND_COPY_KEY) == {
        "state_syncing",
        "resume_available",
        "correction_applied",
        "calibration_notice",
        "progress_delta",
    }
    assert set(EXPERIENCE_COPY_TABLE) == {
        "task.committed",
        "goal.committed",
        "plan.committed",
        "memory.saved",
        "run.completed",
        "intervention.rendered",
        "state.syncing",
        "resume.available",
        "correction.applied",
        "calibration.notice",
        "evidence.registered",
        "progress.delta",
        "err.version_conflict",
        "err.unauthorized",
        "err.not_pending",
        "err.expired",
        "err.not_found",
    }
    with pytest.raises(ValueError):
        copy_key_for_committed_subject("alien")
