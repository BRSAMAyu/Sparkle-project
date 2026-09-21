"""X-08 · Outcome Capture 纯函数面验收（映射词表 + 事件 payload + registry live）.

覆盖（卡面 work 1/3 的确定性面）：
- run receipt 极性词表封闭且覆盖全部 run 终态（PARTIAL → NEUTRAL 保留、不点亮）；
- SUCCEEDED receipt 物化 → classify 升 ACTUAL；PARTIAL/FAILED receipt 永不升 actual；
- 任务终态 → OutcomeCapture 映射（幂等 id、极性、correlation、非终态拒绝）；
- outcome.recorded payload content-free（只含 ids/极性/引用，无结果本体）；
- D-01 registry：outcome.recorded status=live、producer 指向本 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.event_registry import EVENT_REGISTRY, EventStage
from app.core.outcome_ledger import (
    RUN_RECEIPT_OUTCOME_POLARITY,
    RUN_RECEIPT_WORK_MATERIALIZED_STATUSES,
    OutcomePolarity,
    TruthClass,
    classify_task_completion,
    derive_outcome_id,
)
from app.core.run_state_machine import TERMINAL_RUN_STATUSES, RunStatus
from app.models.task import Task, TaskStatus
from app.services.outcome_capture_service import (
    OUTCOME_RECORDED_EVENT,
    build_run_receipt_outcome,
    build_task_outcome_capture,
)


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _terminal_task(*, status: TaskStatus, completed_at: datetime | None = None) -> Task:
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="x08",
        type="LEARNING",
        estimated_minutes=30,
        status=status,
    )
    if completed_at is not None:
        task.completed_at = completed_at
    return task


# ---------------------------------------------------------------------------
# registry / 词表
# ---------------------------------------------------------------------------


def test_registry_outcome_recorded_is_live_with_adapter_producer():
    registered = EVENT_REGISTRY[OUTCOME_RECORDED_EVENT]
    assert registered.status == "live"
    assert registered.stage is EventStage.OUTCOME
    assert any("outcome_capture_service" in producer for producer in registered.producers)


def test_run_receipt_polarity_mapping_covers_all_terminal_statuses():
    # 封闭性：run 终态集与极性映射词表一一对应，词表演进即刻暴露
    assert {status.value for status in TERMINAL_RUN_STATUSES} == set(RUN_RECEIPT_OUTCOME_POLARITY)
    assert RUN_RECEIPT_OUTCOME_POLARITY["SUCCEEDED"] is OutcomePolarity.POSITIVE
    assert RUN_RECEIPT_OUTCOME_POLARITY["PARTIAL"] is OutcomePolarity.NEUTRAL
    assert RUN_RECEIPT_OUTCOME_POLARITY["CANCELLED"] is OutcomePolarity.NEUTRAL
    for failed in ("FAILED", "TIMED_OUT", "BUDGET_EXCEEDED", "UNKNOWN_OUTCOME"):
        assert RUN_RECEIPT_OUTCOME_POLARITY[failed] is OutcomePolarity.NEGATIVE


def test_work_materialized_statuses_is_succeeded_only():
    # 失败不点亮红线：只有 SUCCEEDED receipt 算「工作已物化」
    assert {"SUCCEEDED"} == RUN_RECEIPT_WORK_MATERIALIZED_STATUSES


# ---------------------------------------------------------------------------
# classify：receipt 物化 → ACTUAL（与 quiz 物化面同款）；partial/failed 永不升格
# ---------------------------------------------------------------------------


def _classify_kwargs(**overrides):
    kwargs = {
        "completed_at": _naive_now(),
        "declared_evidence": None,
        "focus_minutes_covered": 0,
        "quiz_materialized": False,
        "verified_evidence_kinds": frozenset(),
        "actual_minutes": 30,
    }
    kwargs.update(overrides)
    return kwargs


def test_classify_without_any_evidence_stays_self_reported():
    assert classify_task_completion(**_classify_kwargs()) is TruthClass.SELF_REPORTED


def test_classify_succeeded_receipt_materializes_actual():
    assert (
        classify_task_completion(**_classify_kwargs(run_receipt_materialized=True)) is TruthClass.ACTUAL
    )


def test_classify_partial_or_failed_receipt_never_upgrades_actual():
    # receipt 物化标记只由 SUCCEEDED 触发（service 层只认 WORK_MATERIALIZED 集合）；
    # 未验证声明 + 无 receipt → self_reported（失败/部分完成不点亮）
    assert classify_task_completion(**_classify_kwargs()) is TruthClass.SELF_REPORTED


# ---------------------------------------------------------------------------
# 任务终态 → OutcomeCapture 映射
# ---------------------------------------------------------------------------


def test_build_task_capture_completed_positive_and_idempotent():
    task = _terminal_task(status=TaskStatus.COMPLETED, completed_at=_naive_now())
    capture = build_task_outcome_capture(task)
    assert capture.source == "task_completion"
    assert capture.polarity is OutcomePolarity.POSITIVE
    assert capture.outcome_id == derive_outcome_id(source="task_completion", source_id=task.id)
    assert capture.outcome_key == f"task_completion:{task.id}"
    assert capture.correlation["task_id"] == str(task.id)
    # 幂等：同一任务重放映射 → 同一 outcome id（与账本幂等 id 同源）
    assert build_task_outcome_capture(task).outcome_id == capture.outcome_id


def test_build_task_capture_abandoned_negative():
    task = _terminal_task(status=TaskStatus.ABANDONED, completed_at=_naive_now())
    capture = build_task_outcome_capture(task)
    assert capture.polarity is OutcomePolarity.NEGATIVE  # 失败保留，不静默丢弃
    assert capture.source_ref == f"task://{task.id}"


def test_build_task_capture_nonterminal_rejected():
    with pytest.raises(ValueError):
        build_task_outcome_capture(_terminal_task(status=TaskStatus.IN_PROGRESS))


# ---------------------------------------------------------------------------
# run receipt → OutcomeCapture 映射（极性词表的消费面）
# ---------------------------------------------------------------------------


def _run(status: RunStatus, *, task_id=None):
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        task_id=task_id,
        status=status,
        completed_at=_naive_now(),
        created_at=_naive_now() - timedelta(minutes=10),
    )


def test_build_run_receipt_outcome_polarities():
    assert build_run_receipt_outcome(_run(RunStatus.SUCCEEDED)).polarity is OutcomePolarity.POSITIVE
    assert build_run_receipt_outcome(_run(RunStatus.PARTIAL)).polarity is OutcomePolarity.NEUTRAL
    assert build_run_receipt_outcome(_run(RunStatus.FAILED)).polarity is OutcomePolarity.NEGATIVE


def test_build_run_receipt_outcome_deterministic_and_correlated():
    run = _run(RunStatus.SUCCEEDED, task_id=uuid4())
    capture = build_run_receipt_outcome(run)
    assert capture.outcome_id == build_run_receipt_outcome(run).outcome_id
    assert capture.source_ref == f"agent_run://{run.id}"
    assert capture.correlation == {"run_id": str(run.id), "task_id": str(run.task_id)}


def test_build_run_receipt_outcome_nonterminal_rejected():
    with pytest.raises(ValueError):
        build_run_receipt_outcome(_run(RunStatus.RUNNING))


# ---------------------------------------------------------------------------
# 事件 payload：content-free 纪律
# ---------------------------------------------------------------------------


@dataclass
class _RecordingBus:
    published: list

    async def publish(self, event_type, payload, stream="sparkle_events"):
        self.published.append((event_type, payload))
        return "msg-id"


async def test_emit_outcome_recorded_payload_is_content_free(monkeypatch):
    from app.services import outcome_capture_service

    bus = _RecordingBus([])
    monkeypatch.setattr(outcome_capture_service, "event_bus_reliable", bus)

    task = _terminal_task(status=TaskStatus.ABANDONED, completed_at=_naive_now())
    task.user_note = "Abandoned: too hard"  # 用户内容绝不进事件（audit-without-exposure）
    capture = build_task_outcome_capture(task)
    await outcome_capture_service.emit_outcome_recorded(capture)

    assert len(bus.published) == 1
    event_type, payload = bus.published[0]
    assert event_type == OUTCOME_RECORDED_EVENT
    assert payload["event_type"] == OUTCOME_RECORDED_EVENT
    assert payload["polarity"] == "negative"
    assert payload["outcome_id"] == capture.outcome_id
    assert payload["source_ref"] == f"task://{task.id}"
    assert payload["correlation_task_id"] == str(task.id)
    # content-free：无结果本体/用户内容字段
    for forbidden in ("user_note", "note", "content", "result", "guide_json", "completion_evidence_record"):
        assert forbidden not in payload
