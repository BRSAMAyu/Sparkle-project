"""X-05 · run 状态机契约测试（封闭词表/迁移图冻结；非法迁移拒绝）.

双冻结（D-01 同法）：状态词表精确集 + 迁移图 sha256 指纹。扩词表/扩迁移边
必须 bump RUN_STATE_MACHINE_VERSION 并过两位 reviewer（X-02 冻结声明同款）。
"""

from __future__ import annotations

import hashlib
from itertools import pairwise

import pytest

from app.core.run_state_machine import (
    ACTIVE_RUN_STATUSES,
    ALLOWED_RUN_TRANSITIONS,
    INTENT_STATUS_TO_RUN_STATUS,
    TERMINAL_RUN_STATUSES,
    IllegalRunTransitionError,
    RunStatus,
    assert_transition_legal,
    event_name_for_transition,
    is_terminal_run_status,
    run_status_for_intent_status,
)

# 迁移图指纹：X-05 契约冻结时采集（agent_run.v1 = 3d9815d0f3b89bae）；
# X-06（agent_run.v2）扩词表 BUDGET_EXCEEDED + 5 条活跃态→BUDGET_EXCEEDED 边
# + 归因 budget_exceeded——本卡两位 reviewer 的显式契约变更。任何进一步变更
# （加边/删边/改词表）都会破坏此断言——这是刻意的：改契约必须显式。
_FROZEN_TRANSITIONS_SHA256 = "87423d3c179aac83"


def _transitions_digest() -> str:
    canon = ";".join(
        f"{src.value}>" + ",".join(sorted(dst.value for dst in dsts))
        for src, dsts in sorted(ALLOWED_RUN_TRANSITIONS.items(), key=lambda kv: kv[0].value)
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


class TestClosedVocabulary:
    def test_status_vocabulary_is_exact(self):
        assert {s.value for s in RunStatus} == {
            "QUEUED",
            "RUNNING",
            "AWAITING_USER",
            "AWAITING_APPROVAL",
            "EXECUTING",
            "SUCCEEDED",
            "PARTIAL",
            "FAILED",
            "CANCELLED",
            "TIMED_OUT",
            "UNKNOWN_OUTCOME",
            "BUDGET_EXCEEDED",
        }

    def test_terminal_and_active_partition_the_vocabulary(self):
        assert set(RunStatus) == TERMINAL_RUN_STATUSES | ACTIVE_RUN_STATUSES
        assert not (TERMINAL_RUN_STATUSES & ACTIVE_RUN_STATUSES)

    def test_terminal_set_matches_runtime_doc(self):
        # AGENT_RUNTIME.md §2: 非快乐终态 FAILED/CANCELLED/TIMED_OUT/PARTIAL/
        # UNKNOWN_OUTCOME + 流程终点的 SUCCEEDED（terminal list 行省略了它，
        # 但 QUEUED→RUNNING→…→SUCCEEDED 的终点即无出边终态）。
        # X-06: BUDGET_EXCEEDED 加入终态（budget 四维超限的明确落点）。
        assert {s.value for s in TERMINAL_RUN_STATUSES} == {
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "TIMED_OUT",
            "PARTIAL",
            "UNKNOWN_OUTCOME",
            "BUDGET_EXCEEDED",
        }

    def test_transitions_map_is_frozen(self):
        assert set(ALLOWED_RUN_TRANSITIONS) == set(RunStatus)  # 每个状态都有条目
        assert _transitions_digest() == _FROZEN_TRANSITIONS_SHA256

    def test_no_self_loops(self):
        for src, dsts in ALLOWED_RUN_TRANSITIONS.items():
            assert src not in dsts, f"self-loop {src}"

    def test_all_active_states_reach_budget_exceeded(self):
        # X-06：预算是外部资源裁决（非执行成败声明），全部活跃态可达。
        for src in ACTIVE_RUN_STATUSES:
            assert assert_transition_legal(src, RunStatus.BUDGET_EXCEEDED) is RunStatus.BUDGET_EXCEEDED

    def test_budget_exceeded_is_closed(self):
        for dst in RunStatus:
            with pytest.raises(IllegalRunTransitionError):
                assert_transition_legal(RunStatus.BUDGET_EXCEEDED, dst)


class TestLegality:
    def test_queued_can_start(self):
        assert assert_transition_legal("QUEUED", "RUNNING") is RunStatus.RUNNING

    def test_happy_path_lifecycle_is_legal(self):
        chain = ["QUEUED", "RUNNING", "AWAITING_USER", "RUNNING", "EXECUTING", "SUCCEEDED"]
        for src, dst in pairwise(chain):
            assert_transition_legal(src, dst)

    def test_awaiting_approval_roundtrip_is_legal(self):
        assert_transition_legal("RUNNING", "AWAITING_APPROVAL")
        assert_transition_legal("AWAITING_APPROVAL", "EXECUTING")
        assert_transition_legal("AWAITING_APPROVAL", "RUNNING")

    @pytest.mark.parametrize("src", sorted(TERMINAL_RUN_STATUSES, key=lambda s: s.value))
    @pytest.mark.parametrize(
        "dst",
        sorted(RunStatus, key=lambda s: s.value),
    )
    def test_terminal_is_closed(self, src, dst):
        with pytest.raises(IllegalRunTransitionError):
            assert_transition_legal(src, dst)

    def test_unknown_status_rejected(self):
        with pytest.raises(IllegalRunTransitionError):
            assert_transition_legal("PAUSED", "RUNNING")
        with pytest.raises(IllegalRunTransitionError):
            assert_transition_legal("RUNNING", "PAUSED")

    def test_illegal_edge_examples(self):
        # 终态旁路、等待态互通、从未启动即成功，全部非法。
        for src, dst in [
            ("SUCCEEDED", "RUNNING"),
            ("AWAITING_USER", "AWAITING_APPROVAL"),
            ("AWAITING_APPROVAL", "AWAITING_USER"),
            ("QUEUED", "SUCCEEDED"),
            ("QUEUED", "PARTIAL"),
            ("RUNNING", "RUNNING"),
        ]:
            with pytest.raises(IllegalRunTransitionError):
                assert_transition_legal(src, dst)

    def test_all_active_states_reach_every_terminal_except_queued_success(self):
        # 不变量：活跃态都能到取消/失败（用户总能退出）；QUEUED 不能直达成败。
        for src in ACTIVE_RUN_STATUSES:
            for dst in (RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.UNKNOWN_OUTCOME):
                assert_transition_legal(src, dst)
            assert is_terminal_run_status(src) is False


class TestEventNameMapping:
    def test_create_uses_registered_created_name(self):
        assert event_name_for_transition(None, RunStatus.QUEUED).value == "run.created"

    def test_awaiting_uses_registered_name_for_both_wait_kinds(self):
        assert event_name_for_transition(RunStatus.RUNNING, RunStatus.AWAITING_USER).value == "run.awaiting_user"
        assert event_name_for_transition(RunStatus.RUNNING, RunStatus.AWAITING_APPROVAL).value == "run.awaiting_user"

    def test_resume_uses_registered_name(self):
        assert event_name_for_transition(RunStatus.AWAITING_USER, RunStatus.RUNNING).value == "run.user_resumed"
        assert event_name_for_transition(RunStatus.AWAITING_APPROVAL, RunStatus.EXECUTING).value == "run.user_resumed"

    def test_other_transitions_use_status_changed(self):
        assert event_name_for_transition(RunStatus.QUEUED, RunStatus.RUNNING).value == "run.status_changed"
        assert event_name_for_transition(RunStatus.EXECUTING, RunStatus.SUCCEEDED).value == "run.status_changed"
        assert event_name_for_transition(RunStatus.RUNNING, RunStatus.FAILED).value == "run.status_changed"


class TestIntentProjectionMapping:
    def test_mapping_is_total_over_intent_vocabulary(self):
        # ExecutionIntentStatus 的 11 态全有落点（全函数）。
        intent_values = {
            "draft",
            "ready",
            "queued",
            "dispatched",
            "running",
            "waiting_approval",
            "succeeded",
            "partial",
            "failed",
            "canceled",
            "timed_out",
            "handed_back",
        }
        assert set(INTENT_STATUS_TO_RUN_STATUS) == intent_values

    def test_unknown_intent_status_raises(self):
        from app.core.run_state_machine import RunStateError

        with pytest.raises(RunStateError):
            run_status_for_intent_status("exploded")

    def test_projection_directions(self):
        assert run_status_for_intent_status("queued") is RunStatus.QUEUED
        assert run_status_for_intent_status("dispatched") is RunStatus.RUNNING
        assert run_status_for_intent_status("waiting_approval") is RunStatus.AWAITING_APPROVAL
        assert run_status_for_intent_status("handed_back") is RunStatus.CANCELLED
        assert run_status_for_intent_status("succeeded") is RunStatus.SUCCEEDED
        assert is_terminal_run_status(run_status_for_intent_status("timed_out"))
