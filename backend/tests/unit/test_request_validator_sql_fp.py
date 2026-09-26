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

V3-FIX-164（wt475）——恒真式语境约束双向 bench。

FIX-77 修法引入的恒真式正则 `\\b(?:or|and)\\s+['\\"]?\\d+['\\"]?\\s*=\\s*['\\"]?\\d+\\b`
把数学真值问句判为注入（wt468 审查轮 7A 探针实录红，与 FIX-77 原病症同症状
换形态）：

- "Is 1 = 1 and 2 = 2 always true?"
- "Which is true: 2 = 2 or 3 = 3?"

均 `_contains_malicious_content()=True` → /ws/chat 主链 validate_message 硬拒
（non-retryable）。修后判据（恒真式需携带 SQL 载荷语境）：
- 数学等式/比较/真值问答（中英双语）全部放行；
- 恒真式注入（引号包裹比较/引号逃逸/语句分隔符堆叠/WHERE 列赋值延续）
  与裸符号布尔片段（`1 OR 1=1`）仍全部拒绝——恶意面不放宽。
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


# ---------------------------------------------------------------------------
# V3-FIX-164（wt475）：恒真式语境约束双向 bench
# ---------------------------------------------------------------------------

# wt468 审查轮 7A 探针实录红原句（FIX-77 恒真式正则误拒的数学学习内容）
PROBE_WT468_CASE_1 = "Is 1 = 1 and 2 = 2 always true?"
PROBE_WT468_CASE_2 = "Which is true: 2 = 2 or 3 = 3?"

# 良性面（英文）：数学等式/比较/真值问答——学习域合法核心内容，必须放行
BENIGN_MATH_EN = [
    PROBE_WT468_CASE_1,
    PROBE_WT468_CASE_2,
    "Is 5 = 5 a true statement?",
    "If x = 2 and y = 3, what is x + y?",
    "Solve: 3x = 12 and 2y = 10.",
    "Is a = a always true for any number a?",
    "True or false: 7 = 7?",
    "Does 0.999... = 1? Explain why.",
    "In the equation 4 = 4, both sides are equal.",
    "Explain why n = n is called the reflexive property of equality.",
]

# 良性面（中文）：同域中文词序（含混用英文 and/or 的常见形态，裸字母判断
# 对 CJK 不可靠，须验证词字排除逻辑）
BENIGN_MATH_ZH = [
    "1 = 1 和 2 = 2 永远成立吗？",
    "2 = 2 还是 3 = 3 是对的？",
    "请证明 a = a 是自反律。",
    "如果 x = 2 且 y = 3，那么 x + y 等于多少？",
    "判断题：5 = 5 是否正确？",
    "等式 4 = 4 两边相等，这说明什么性质？",
    "已知 1 = 1 and 2 = 2，请判断这个命题的真假。",
    "为什么老师说 n = n 对任何数都成立？",
    "1 = 2 这个等式错在哪里？请指出。",
    "比较 3 = 3 与 2 = 3，哪个是真命题？",
]

# 恶意面：经典恒真式注入族（含 FIX-77 既有 13 载荷全部保留）——必须拦截
INJECTION_TAUTOLOGY_PAYLOADS = [
    # --- FIX-77 既有载荷（不许回退）---
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
    # --- V3-FIX-164 新增恒真式载荷（语境信号各形态）---
    '" OR "1"="1',
    "1 OR 1=1 --",
    "' OR 1='1",
    'admin" AND 1=1',
    "1=1 OR 1=1",
    "OR 1=1",
]


@pytest.mark.parametrize("message", BENIGN_MATH_EN + BENIGN_MATH_ZH)
def test_math_truth_questions_not_rejected(validator: RequestValidator, message: str):
    """数学等式/比较/真值问答（中英双语）不得被恒真式校验误判拒答。"""
    result = validator.validate_message(message)
    assert result.is_valid, f"数学学习内容误判拒答: {message!r} -> {result.error_message!r}"


@pytest.mark.parametrize("payload", INJECTION_TAUTOLOGY_PAYLOADS)
def test_tautology_injection_payloads_still_rejected(validator: RequestValidator, payload: str):
    """恒真式注入载荷（含裸符号布尔片段）必须仍被拒绝——恶意面不放宽。"""
    result = validator.validate_message(payload)
    assert not result.is_valid, f"漏报恒真式载荷: {payload!r}"
    assert result.error_message is not None
