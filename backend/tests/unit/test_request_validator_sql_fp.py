"""V3-FIX-77（wt456）——SQL 校验器英文词误判拒答红绿测试。

Q-06 分层 bench 实锤（v3-output/WT406-Q06-PERF/raw-bench.jsonl L2-30/L3-43
r1+r2，error_code=2 "Message contains potentially malicious content"，引擎日志
"Detected potential SQL injection"）：历史规则 `_contains_malicious_content` 以
`select `/`insert `/`update ` 等子串命中 + `\\bkw\\b.*?from\\b` 跨任意距离匹配
——英文学习材料普通词序即触发、校验失败直接拒答：

- L2-30（SQL 教学/审查请求，学习域合法内容）：
  "review this SQL: SELECT * FROM orders WHERE user_id IN (SELECT id FROM
   users WHERE vip=1) — 列出性能与正确性风险并排序"
- L3-43（记忆再巩固英文教材，跨句 `update `→`from`）：
  "...interference during this window can update or weaken the memory...
   Derive three concrete feedback-timing rules for a flashcard app from this
   material..."

修后判据（结构信号校验替代「关键词+from」，误判面消歧）：
- 两条 bench 原句与常见英语词序不再拒答；
- 真实注入载荷（恒真条件/注释截断/union select/高危 DDL/引号堆叠/盲注函数）
  仍全部拒绝——安全语义不回退。
"""

from __future__ import annotations

import pytest

from app.orchestration.validator import RequestValidator

# Q-06 bench L2-30 原句（SQL 教学/审查请求）
BENCH_L2_30_TEXT = (
    "review this SQL: SELECT * FROM orders WHERE user_id IN "
    "(SELECT id FROM users WHERE vip=1) — 列出性能与正确性风险并排序"
)

# Q-06 bench L3-43 原句（英文学习材料，跨句 update→from）
BENCH_L3_43_TEXT = (
    "[Study material] Memory reconsolidation: A retrieved memory enters a "
    "labile state and must re-consolidate; interference during this window "
    "can update or weaken the memory. This explains why incorrectly recalled "
    "facts get strengthened if feedback is delayed. In education, immediate "
    "corrective feedback after retrieval exploits reconsolidation. "
    "Hypercorrection: high-confidence errors, once corrected, are better "
    "remembered than low-confidence errors — but only with prompt feedback. "
    "Spacing feedback 10 minutes after retrieval shows mixed results. "
    "[Question] Derive three concrete feedback-timing rules for a flashcard "
    "app from this material, mark each rule's evidence strength, and identify "
    "which claim rests on the thinnest evidence"
)


@pytest.fixture()
def validator() -> RequestValidator:
    return RequestValidator(enable_quota_check=False)


@pytest.mark.parametrize(
    "message",
    [
        BENCH_L2_30_TEXT,
        BENCH_L3_43_TEXT,
        # 常见英语词序（学习/日常语境中的关键词词族）
        "Please update or weaken the memory model in your notes.",
        "Select all completed tasks from the list and summarize them.",
        "Delete duplicate cards from the deck, then update the schedule.",
        "What does the SQL UPDATE statement do? Give examples from real apps.",
        'The professor asked us to explain "union" and "insert" as plain words.',
    ],
)
def test_english_learning_word_orders_not_rejected(validator: RequestValidator, message: str):
    """学习域合法内容（含 SQL 教学）不得被 SQL 校验器误判拒答。"""
    result = validator.validate_message(message)
    assert result.is_valid, f"误判拒答: {message!r} -> {result.error_message!r}"


@pytest.mark.parametrize(
    "payload",
    [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin' OR 1=1 --",
        "UNION SELECT password FROM admin_accounts",
        "x UNION ALL SELECT credit_card FROM payments",
        "admin'--",
        "'); DROP TABLE sessions; --",
        "1 OR 1=1",
        "id=7 AND 2=2",
        "nothing'; DELETE FROM audit_log WHERE '1'='1",
        "EXEC xp_cmdshell 'dir'",
        "WAITFOR DELAY '0:0:10'; SELECT 1",
        "(SELECT SLEEP(10))",
    ],
)
def test_injection_payloads_still_rejected(validator: RequestValidator, payload: str):
    """真实注入载荷（结构信号面）必须仍被拒绝——安全语义不回退。"""
    result = validator.validate_message(payload)
    assert not result.is_valid, f"漏报载荷: {payload!r}"
    assert result.error_message is not None
