"""X-09 · Failure Semantics 契约测试 —— 三族分类器确定性 + 重试策略.

覆盖卡面验收（变异必红锚点）：

- **确定性**：同类输入恒同输出（重复调用 100 次逐字段一致；无时间/随机数
  /LLM 参与）；
- **三族 → run 合法终态映射**：全部落 X-05 既有终态 + 既有 terminal_reason
  词（词表零扩展的回归钉）；
- **冻结**：18 个 failure_kind 的映射表 sha256（改任何映射必红）；
- **side effect 证据升格**：同 kind 下 unknown → UNKNOWN_OUTCOME（不重试）、
  none → RETRYABLE——账本证据是唯一分流依据；
- **重试策略**：指数退避（base·2^(n-1) 封顶）、attempt 上限、死信（不可
  重试族恒 False）；
- **变异锚点**：每族至少一条具体映射断言（改分类表 → 必红）。
"""

from __future__ import annotations

import pytest

from app.core.failure_semantics import (
    DEFAULT_MAX_RETRY_ATTEMPTS,
    FAILURE_ATTRIBUTIONS,
    FAILURE_KIND_TO_TERMINAL,
    FAILURE_SEMANTICS_VERSION,
    FAILURE_TABLE_SHA256,
    FailureFamily,
    FailureKind,
    classify_execution_failure,
    retry_backoff_delay,
    retry_decision,
    terminal_for_failure_kind,
)
from app.core.run_state_machine import RunStatus, is_terminal_run_status, terminal_reason_vocabulary

# ---------------------------------------------------------------------------
# 1. 词表与映射表冻结（变异必红）
# ---------------------------------------------------------------------------


class TestVocabularyFreeze:
    def test_failure_kinds_are_frozen(self):
        assert sorted(k.value for k in FailureKind) == sorted(
            [
                "user_cancelled",
                "budget_exceeded",
                "permission_denied",
                "not_in_allowed_tools",
                "unknown_tool",
                "validation_error",
                "confirmation_required",
                "idempotency_key_required",
                "idempotency_conflict",
                "idempotency_args_mismatch",
                "tool_timeout",
                "tool_exception",
                "tool_reported_failure",
                "network_unreachable",
                "idempotency_interrupted",
                "worker_crash_orphan",
                "wait_expired",
                "queue_stale",
            ]
        )

    def test_families_are_four(self):
        assert sorted(f.value for f in FailureFamily) == [
            "permanent_failure",
            "retryable_failure",
            "unknown_outcome",
            "user_cancelled",
        ]
        assert frozenset(f.value for f in FailureFamily) == FAILURE_ATTRIBUTIONS

    def test_mapping_table_sha256_frozen(self):
        """改任何 failure_kind → (终态, reason) 映射必红（冻结锚点）."""
        assert FAILURE_TABLE_SHA256 == "f392949f856f42cab89b4c335711afb30111a4471a425673b52f42d5998ab8c9"

    def test_terminal_reasons_all_in_x05_vocabulary(self):
        """X-09 零新 terminal_reason 词（红线：不扩 X-05 冻结词表）."""
        for kind, (_status, reason) in FAILURE_KIND_TO_TERMINAL.items():
            if reason is not None:
                assert reason in terminal_reason_vocabulary, f"{kind} -> {reason} not in X-05 vocabulary"

    def test_every_kind_has_full_mapping(self):
        assert set(FAILURE_KIND_TO_TERMINAL) == {k.value for k in FailureKind}
        for kind in FailureKind:
            status, _reason = terminal_for_failure_kind(kind)
            assert is_terminal_run_status(status)


# ---------------------------------------------------------------------------
# 2. 三族分类（确定性表；变异锚点逐条钉死）
# ---------------------------------------------------------------------------


class TestClassifierDeterminism:
    def test_same_input_always_same_output(self):
        """确定性契约：100 次重复调用逐字段一致（无时钟/随机/LLM）."""
        base = classify_execution_failure(failure_kind="tool_timeout", tool_effect="write", side_effect_state="unknown")
        for _ in range(100):
            again = classify_execution_failure(
                failure_kind="tool_timeout", tool_effect="write", side_effect_state="unknown"
            )
            assert again == base

    @pytest.mark.parametrize(
        "kind,effect,state,expected_family,expected_status,expected_reason",
        [
            # --- 用户取消族 ---
            ("user_cancelled", None, "none", "user_cancelled", "CANCELLED", "user_cancelled"),
            # --- 确定性失败族（变异锚点：改表必红）---
            ("budget_exceeded", None, "none", "permanent_failure", "BUDGET_EXCEEDED", "budget_exceeded"),
            ("permission_denied", "write", "none", "permanent_failure", "FAILED", "rejected"),
            ("not_in_allowed_tools", "write", "none", "permanent_failure", "FAILED", "rejected"),
            ("unknown_tool", None, "none", "permanent_failure", "FAILED", "failed"),
            ("validation_error", "read", "none", "permanent_failure", "FAILED", "failed"),
            ("confirmation_required", "write", "none", "permanent_failure", "FAILED", "rejected"),
            ("idempotency_key_required", "write", "none", "permanent_failure", "FAILED", "rejected"),
            ("idempotency_conflict", "write", "none", "permanent_failure", "FAILED", "failed"),
            ("idempotency_args_mismatch", "write", "none", "permanent_failure", "FAILED", "failed"),
            # --- 暂态族（side effect 证据分流）---
            ("tool_timeout", "read", "none", "retryable_failure", "FAILED", "failed"),
            ("tool_timeout", "read", "confirmed", "retryable_failure", "FAILED", "failed"),
            ("tool_exception", "write", "none", "retryable_failure", "FAILED", "failed"),
            ("tool_reported_failure", "read", "none", "retryable_failure", "FAILED", "failed"),
            ("network_unreachable", "read", "none", "retryable_failure", "FAILED", "failed"),
            # --- 未知结局族（账本证据/中断信号 → 绝不自动重试）---
            ("tool_timeout", "write", "unknown", "unknown_outcome", "UNKNOWN_OUTCOME", "worker_restart_orphan"),
            ("tool_exception", "write", "unknown", "unknown_outcome", "UNKNOWN_OUTCOME", "worker_restart_orphan"),
            (
                "tool_reported_failure",
                "write",
                "unknown",
                "unknown_outcome",
                "UNKNOWN_OUTCOME",
                "worker_restart_orphan",
            ),
            (
                "idempotency_interrupted",
                "write",
                "unknown",
                "unknown_outcome",
                "UNKNOWN_OUTCOME",
                "worker_restart_orphan",
            ),
            ("worker_crash_orphan", "write", "unknown", "unknown_outcome", "UNKNOWN_OUTCOME", "worker_restart_orphan"),
            # --- 系统/队列时间裁决 ---
            ("wait_expired", None, "none", "permanent_failure", "TIMED_OUT", "wait_expired"),
            ("queue_stale", None, "none", "permanent_failure", "CANCELLED", "queue_stale"),
        ],
    )
    def test_classification_table(self, kind, effect, state, expected_family, expected_status, expected_reason):
        c = classify_execution_failure(failure_kind=kind, tool_effect=effect, side_effect_state=state)
        assert c.family.value == expected_family
        assert c.run_terminal_status is RunStatus(expected_status)
        assert c.terminal_reason == expected_reason
        assert c.error_category == expected_family  # 归因 = 族名（封闭词表）
        assert c.failure_kind == kind

    def test_unknown_family_never_auto_retries(self):
        """UNKNOWN 族：retryable=False 且 retry_requires_new_key=True（换新键是
        显式决策——duplicate side effect=0 的分类器根基）."""
        for kind in ("idempotency_interrupted", "worker_crash_orphan"):
            c = classify_execution_failure(failure_kind=kind, tool_effect="write", side_effect_state="unknown")
            assert c.family is FailureFamily.UNKNOWN_OUTCOME
            assert c.retryable is False
            assert c.retry_requires_new_key is True

    def test_side_effect_state_is_the_only_transient_split(self):
        """同 kind 同 effect：state unknown vs none 恒分两族（证据驱动升格）."""
        none_c = classify_execution_failure(
            failure_kind="tool_exception", tool_effect="write", side_effect_state="none"
        )
        unknown_c = classify_execution_failure(
            failure_kind="tool_exception", tool_effect="write", side_effect_state="unknown"
        )
        assert none_c.family is FailureFamily.RETRYABLE_FAILURE and none_c.retryable
        assert unknown_c.family is FailureFamily.UNKNOWN_OUTCOME and not unknown_c.retryable

    def test_fail_closed_on_unknown_kind(self):
        with pytest.raises(ValueError, match="closed vocabulary"):
            classify_execution_failure(failure_kind="someone_elses_bug")

    def test_fail_closed_on_unknown_side_effect_state(self):
        with pytest.raises(ValueError, match="side_effect_state"):
            classify_execution_failure(failure_kind="tool_timeout", side_effect_state="maybe")

    def test_error_type_does_not_change_classification(self):
        """error_type 只审计不分类（错误文案变化不得改变终态语义）."""
        a = classify_execution_failure(failure_kind="tool_timeout", error_type="TimeoutError")
        b = classify_execution_failure(failure_kind="tool_timeout", error_type="weird provider message 500")
        assert a == b


# ---------------------------------------------------------------------------
# 3. 重试策略（指数退避 + 上限 + 死信）
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    def test_exponential_backoff(self):
        assert retry_backoff_delay(1) == 0.5
        assert retry_backoff_delay(2) == 1.0
        assert retry_backoff_delay(3) == 2.0
        assert retry_backoff_delay(4) == 4.0

    def test_backoff_capped(self):
        assert retry_backoff_delay(5) == 8.0
        assert retry_backoff_delay(50) == 8.0  # 封顶

    def test_backoff_is_deterministic(self):
        for attempt in range(1, 10):
            assert retry_backoff_delay(attempt) == retry_backoff_delay(attempt)

    def test_backoff_rejects_invalid_attempt(self):
        with pytest.raises(ValueError):
            retry_backoff_delay(0)

    def test_retryable_within_budget(self):
        c = classify_execution_failure(failure_kind="tool_timeout", tool_effect="read", side_effect_state="none")
        for attempt in range(1, DEFAULT_MAX_RETRY_ATTEMPTS + 1):
            should, delay = retry_decision(c, attempt=attempt)
            assert should and delay == retry_backoff_delay(attempt)

    def test_dead_letter_after_max_attempts(self):
        """attempt > max → (False, None)：死信，run 层落明确终态（非无限执行）."""
        c = classify_execution_failure(failure_kind="tool_timeout", tool_effect="read", side_effect_state="none")
        should, delay = retry_decision(c, attempt=DEFAULT_MAX_RETRY_ATTEMPTS + 1)
        assert should is False and delay is None

    @pytest.mark.parametrize(
        "kind,effect,state",
        [
            ("user_cancelled", None, "none"),
            ("budget_exceeded", None, "none"),
            ("permission_denied", "write", "none"),
            ("validation_error", "read", "none"),
            ("idempotency_interrupted", "write", "unknown"),
            ("worker_crash_orphan", "write", "unknown"),
            ("tool_timeout", "write", "unknown"),  # unknown 族：即使 attempt=1 也不重试
        ],
    )
    def test_non_retryable_families_never_retry(self, kind, effect, state):
        c = classify_execution_failure(failure_kind=kind, tool_effect=effect, side_effect_state=state)
        should, delay = retry_decision(c, attempt=1)
        assert should is False and delay is None


def test_version_stamp():
    assert FAILURE_SEMANTICS_VERSION == "failure_semantics.v1"
