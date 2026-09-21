"""X-08 · GJ03/GJ05/GJ06 → 可查询 outcome + WVPL 可计数 + 失败保留（真实 DB）.

验收对应（卡面 acceptance，逐条红测）：
- **GJ03**（Existing user → Today → action → outcome）：Human 完成带 artifact
  证据 → D-02 账本可查询（truth=ACTUAL、极性 POSITIVE）→ WVPL loop 可计数
  （三腿齐：goal-linked action + actual 证据 + study_record state update）；
- **GJ05**（Human action → evidence → Galaxy）：完成管线 spark_node 落
  study_record / node 状态（Galaxy 吸收痕迹），账本侧同因合并为单一 outcome
  （回声不双计）；
- **GJ06**（Agent action → approval → run → receipt）：SUCCEEDED run receipt
  物化 → 完成升 ACTUAL + agent_run:// 独立证据；PARTIAL/FAILED receipt 保留
  为证据但**永不升 actual**（失败/部分完成不点亮）；
- **失败保留**：ABANDONED 任务以 polarity=NEGATIVE 可查询（不静默丢弃），
  WVPL loop 恒为 0、truth_coverage 分母不含失败行（结构性不可点亮）；
- **接线**：TaskService.complete/abandon 广播 outcome.recorded（极性正确，
  content-free payload）。

说明：Redis 事件总线为外部传输设施，测试中以记录桩替换（仅传输层；
被测行为 = 映射与账本查询，全部走真实 DB 与真实服务）。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.task import TaskStatus
from app.services.north_star_wvpl_service import NorthStarWvplService
from app.services.outcome_capture_service import OUTCOME_RECORDED_EVENT
from app.services.outcome_ledger_service import OutcomeLedgerService
from app.services.task_service import TaskService
from tests.golden.north_star_wvpl_fixture import (
    file_evidence as _file_evidence,
)
from tests.golden.north_star_wvpl_fixture import (
    make_goal_plan as _make_goal_plan,
)
from tests.golden.north_star_wvpl_fixture import (
    make_user as _make_user,
)
from tests.golden.north_star_wvpl_fixture import (
    task as _task,
)

pytestmark = pytest.mark.asyncio


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _RecordingBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type, payload, stream="sparkle_events"):
        self.published.append((event_type, payload))
        return "msg-id"


@pytest.fixture()
def recording_bus(monkeypatch):
    """记录桩：替换 capture 模块的可靠发布器 + EventBus 单例的 publish.

    只替换**传输层**（本环境 Redis 需鉴权不可用，重试退避会拖垮测试）；
    被测行为 = TaskService / capture 服务 / 账本 / WVPL 的真实 DB 流程。
    """
    from app.core.event_bus import event_bus
    from app.services import outcome_capture_service

    bus = _RecordingBus()
    monkeypatch.setattr(outcome_capture_service, "event_bus_reliable", bus)

    async def _record_publish(event_type, payload, stream="sparkle_events"):
        bus.published.append((event_type, dict(payload)))
        return "msg-id"

    monkeypatch.setattr(event_bus, "publish", _record_publish)
    return bus


async def _new_in_progress_task(db_session, user, plan_id=None, title="X-08 验收任务"):
    task = _task(user.id, plan_id=plan_id)
    task.status = TaskStatus.IN_PROGRESS
    task.title = title
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


def _find_task_entry(entries, task_id):
    for entry in entries:
        if entry.source.value == "task_completion" and entry.source_id == str(task_id):
            return entry
    return None


# ---------------------------------------------------------------------------
# GJ03：action → outcome 可查询 + WVPL 可计数
# ---------------------------------------------------------------------------


async def test_gj03_completion_produces_queryable_outcome_and_wvpl_loop(db_session, recording_bus):
    user = await _make_user(db_session, uid=8101)
    goal, plan = await _make_goal_plan(db_session, user, gid=8101, pid=8101)
    task = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="GJ03 证据任务")
    await _file_evidence(db_session, user, task, fid=8101)

    completed = await TaskService.complete(db_session, task, 25)
    assert completed.status == TaskStatus.COMPLETED

    # 账本可查询：truth=ACTUAL（document:// 证据解析）、极性 POSITIVE
    ledger = OutcomeLedgerService(db_session)
    page = await ledger.query(user_id=user.id, truth_class="actual")
    entry = _find_task_entry(page.items, task.id)
    assert entry is not None, "GJ03 outcome must be queryable from the ledger"
    assert entry.truth_class.value == "actual"
    assert entry.polarity.value == "positive"
    assert entry.correlation.get("plan_id") == str(plan.id)
    declared_verified = [e for e in entry.evidence if e.source == "declared_ref" and e.verified]
    assert declared_verified, "artifact 证据必须已解析（verified）"

    # 计数不双计：回声 study_record 并入 task 证据，不产生第二个 outcome
    counts = await ledger.count_by_source(user_id=user.id)
    assert counts["task_completion"] == 1
    assert counts["study_record"] == 0

    # WVPL 可计数：goal-linked + actual + state update 三腿 → loop ≥ 1
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_naive_now(), generated_at=_naive_now())
    assert fact["north_star"]["loops_total"] >= 1
    assert fact["north_star"]["wvpl_users"] >= 1
    loop_task_ids = {sample["task_id"] for sample in fact["loops"]["samples"]}
    assert str(task.id) in loop_task_ids
    # 事件面：task.completed 走同一事件路径；outcome.recorded 已广播（polarity positive）
    recorded_types = {e for e, _ in recording_bus.published}
    assert "task.completed" in recorded_types
    assert OUTCOME_RECORDED_EVENT in recorded_types
    payload = [p for e, p in recording_bus.published if e == OUTCOME_RECORDED_EVENT][-1]
    assert payload["polarity"] == "positive"
    assert payload["outcome_id"] == entry.outcome_id


# ---------------------------------------------------------------------------
# GJ05：Human action → evidence → Galaxy 吸收（study_record / node 状态）
# ---------------------------------------------------------------------------


async def test_gj05_human_evidence_flows_to_galaxy_state(db_session, recording_bus):
    user = await _make_user(db_session, uid=8102)
    task = await _new_in_progress_task(db_session, user, title="GJ05 星图任务")

    await TaskService.complete(db_session, task, 20)

    # Galaxy 吸收：spark_node 落 study_record（state update 腿）+ 节点状态行
    study_rows = (
        await db_session.execute(select(StudyRecord).where(StudyRecord.task_id == task.id))
    ).scalars().all()
    assert study_rows, "完成管线必须经 spark_node 写入 study_record（Galaxy 状态链）"
    node_status = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user.id))
    ).scalars().all()
    assert node_status, "Galaxy 节点状态必须被点亮/更新"

    # 账本侧同因合并：回声是 task outcome 的证据，不是独立 outcome（不双写真源）
    ledger = OutcomeLedgerService(db_session)
    page = await ledger.query(user_id=user.id)
    entry = _find_task_entry(page.items, task.id)
    assert entry is not None
    echo_evidence = [e for e in entry.evidence if e.source == "study_record"]
    assert echo_evidence and all(e.role.value == "pipeline_echo" for e in echo_evidence)
    standalone = await ledger.count_by_source(user_id=user.id)
    assert standalone["study_record"] == 0


# ---------------------------------------------------------------------------
# GJ06：Agent run receipt → outcome（SUCCEEDED 升 actual；PARTIAL/FAILED 不升）
# ---------------------------------------------------------------------------


async def _add_terminal_run(db_session, user, task, status: RunStatus) -> AgentRun:
    run = AgentRun(
        user_id=user.id,
        task_id=task.id,
        objective="X-08 GJ06 receipt run",
        allowed_tools=[],
        permissions={},
        budget={},
        completion_condition={},
        status=status,
        heartbeat_at=_naive_now(),
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


async def test_gj06_succeeded_receipt_materializes_actual_outcome(db_session, recording_bus):
    user = await _make_user(db_session, uid=8103)
    task = await _new_in_progress_task(db_session, user, title="GJ06 agent 任务")
    run = await _add_terminal_run(db_session, user, task, RunStatus.SUCCEEDED)

    await TaskService.complete(db_session, task, None, evidence_source="agent")

    page = await OutcomeLedgerService(db_session).query(user_id=user.id)
    entry = _find_task_entry(page.items, task.id)
    assert entry is not None
    # receipt 物化（无 focus/quiz/document）→ ACTUAL：tool receipt 映射生效
    assert entry.truth_class.value == "actual"
    receipts = [e for e in entry.evidence if e.source == "agent_run_receipt"]
    assert receipts and receipts[0].ref == f"agent_run://{run.id}"
    assert receipts[0].verified is True
    assert receipts[0].role.value == "independent"


async def test_gj06_partial_and_failed_receipts_preserved_but_never_light(db_session, recording_bus):
    user = await _make_user(db_session, uid=8104)
    # P2 收口（G-02 顺手解）：任务挂 goal-linked plan，使「三腿」中前两条腿
    # （goal-link + spark state update）成立——此时若 PARTIAL/FAILED receipt 被
    # 错误升 actual，loops 就会点亮；loops_total == 0 的断言因此非空洞。
    _goal, plan = await _make_goal_plan(db_session, user, gid=8104, pid=8104)
    partial_task = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="GJ06 partial 任务")
    failed_task = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="GJ06 failed 任务")
    await _add_terminal_run(db_session, user, partial_task, RunStatus.PARTIAL)
    await _add_terminal_run(db_session, user, failed_task, RunStatus.FAILED)

    await TaskService.complete(db_session, partial_task, None, evidence_source="agent")
    await TaskService.complete(db_session, failed_task, None, evidence_source="agent")

    ledger = OutcomeLedgerService(db_session)
    page = await ledger.query(user_id=user.id)
    for task in (partial_task, failed_task):
        entry = _find_task_entry(page.items, task.id)
        assert entry is not None, "partial/failed receipt 的 outcome 必须保留可查询"
        # 失败不点亮：PARTIAL/FAILED receipt 永不升 actual
        assert entry.truth_class.value == "self_reported"
        assert entry.polarity.value == "positive"  # 任务本身完成了（点击），但无独立证明
        receipts = [e for e in entry.evidence if e.source == "agent_run_receipt"]
        assert receipts, "receipt 保留为证据（可见、可审计）"
        assert receipts[0].role.value == "pipeline_echo"  # 不作独立工作证明

    # P2 收口：PARTIAL/FAILED receipt 结构性不进 WVPL loops（goal-linked 且
    # completed_at 存在的前提下仍恒为 0——点亮只由 actual 面驱动）
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_naive_now(), generated_at=_naive_now())
    assert fact["north_star"]["loops_total"] == 0, "partial/failed receipt 不得点亮任何 loop"
    loop_task_ids = {sample["task_id"] for sample in fact["loops"]["samples"]}
    assert str(partial_task.id) not in loop_task_ids
    assert str(failed_task.id) not in loop_task_ids


# ---------------------------------------------------------------------------
# 失败保留 + 结构性不可点亮（卡面 work 3 / acceptance 2）
# ---------------------------------------------------------------------------


async def test_abandoned_outcome_preserved_queryable_and_never_counts(db_session, recording_bus):
    user = await _make_user(db_session, uid=8105)
    goal, plan = await _make_goal_plan(db_session, user, gid=8105, pid=8105)
    task = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="将被放弃的任务")

    abandoned = await TaskService.abandon(db_session, task, reason="太难了")
    assert abandoned.status == TaskStatus.ABANDONED
    assert abandoned.completed_at is not None  # abandon 语义：终态时刻落在 completed_at

    # 失败 outcome 可查询：polarity=NEGATIVE 定向检索命中
    ledger = OutcomeLedgerService(db_session)
    negatives = await ledger.query(user_id=user.id, polarity="negative")
    entry = _find_task_entry(negatives.items, task.id)
    assert entry is not None, "失败 outcome 必须保留在账本中（不得静默丢弃）"
    assert entry.polarity.value == "negative"
    assert entry.truth_class.value == "actual"  # quiz_failed 同款：真实但负向的事实

    # 结构性不可点亮：goal-linked + completed_at 存在，但 WVPL loop 恒为 0
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_naive_now(), generated_at=_naive_now())
    assert fact["north_star"]["loops_total"] == 0
    # truth_coverage 维持「完成 ≠ 点击」语义：失败行不进分布分母
    coverage = await ledger.truth_coverage(user_id=user.id)
    assert coverage["total"] == 0

    # 事件面：abandon 广播的 outcome.recorded 携带 negative 极性
    payloads = [p for e, p in recording_bus.published if e == OUTCOME_RECORDED_EVENT]
    assert payloads and payloads[-1]["polarity"] == "negative"


async def test_mixed_terminal_tasks_wvpl_counts_only_completions(db_session, recording_bus):
    user = await _make_user(db_session, uid=8106)
    goal, plan = await _make_goal_plan(db_session, user, gid=8106, pid=8106)
    done = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="完成 + focus 覆盖")
    aborted = await _new_in_progress_task(db_session, user, plan_id=plan.id, title="放弃")
    await TaskService.abandon(db_session, aborted, reason="no time")
    # 完成：无 document 证据，但真实投入 ≥ 覆盖率门槛（30min×0.5 → 15min）
    from datetime import timedelta

    done.started_at = _naive_now() - timedelta(minutes=40)
    from app.models.focus import FocusSession, FocusStatus

    db_session.add(
        FocusSession(
            user_id=user.id,
            task_id=done.id,
            start_time=done.started_at,
            end_time=_naive_now() - timedelta(minutes=5),
            duration_minutes=20,
            status=FocusStatus.COMPLETED,
        )
    )
    await db_session.commit()
    await TaskService.complete(db_session, done, None)

    ledger = OutcomeLedgerService(db_session)
    counts = await ledger.count_by_source(user_id=user.id)
    assert counts["task_completion"] == 2  # 完成 + 放弃（失败保留）
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_naive_now(), generated_at=_naive_now())
    assert fact["north_star"]["loops_total"] == 1  # 只有完成行可成 loop（放弃行不可点亮）
    loop_task_ids = {sample["task_id"] for sample in fact["loops"]["samples"]}
    assert loop_task_ids == {str(done.id)}
    coverage = await ledger.truth_coverage(user_id=user.id)
    assert coverage["total"] == 1  # 真相分布分母只含完成面
