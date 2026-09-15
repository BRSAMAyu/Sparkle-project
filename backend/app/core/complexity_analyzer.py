from __future__ import annotations

"""
ComplexityAnalyzer — 纯规则引擎，< 3ms 执行时间，零 LLM 调用。

根据用户消息文本的多维信号，评估任务复杂度，并给出相对于 agent 默认 tier 的
调整量（tier_delta）。负值 = 可降级，正值 = 需升级。

Active dependency: app.core.llm_router uses this module for complexity-aware
model tier adjustment. Keep it lightweight and deterministic.
"""

import re
from dataclasses import dataclass
from enum import StrEnum


class ComplexityLevel(StrEnum):
    TRIVIAL = "trivial"       # 你好、谢谢、嗯
    SIMPLE = "simple"         # 短问句、简单查询
    MODERATE = "moderate"     # 标准知识问答
    COMPLEX = "complex"       # 多步推理、分析
    EXPERT = "expert"         # 深度分析、证明


@dataclass
class ComplexityAssessment:
    level: ComplexityLevel
    confidence: float
    signals: list[str]
    suggested_tier_delta: int  # -2, -1, 0, +1, +2（相对 agent 默认 tier 的调整）


# ============================================
# 信号正则（预编译，保证 < 3ms）
# ============================================

_GREETING_PATTERN = re.compile(
    r"^(你好|您好|hi|hello|hey|嗯|哦|好的|谢谢|感谢|👍|ok|okay|好|哈哈|lol|嘿|哎)[!！。.~～\s]*$",
    re.IGNORECASE,
)
_CONFIRMATION_PATTERN = re.compile(
    r"^(明白了?|懂了|好的?|收到|知道了|了解|没问题|是的?|对的?|不是|不对)[!！。.~～\s]*$",
    re.IGNORECASE,
)
_QUESTION_PATTERN = re.compile(r"[?？]")
_MATH_FORMULA_PATTERN = re.compile(r"[\d\+\-\*/=\^√∫∑∏≤≥≠±]|(\b(sin|cos|tan|log|lim|dx|dy)\b)", re.IGNORECASE)
_CODE_BLOCK_PATTERN = re.compile(r"```|`[^`]+`|\bdef\b|\bclass\b|\bfunction\b|\bconst\b|\bimport\b")
_SCIENCE_TERMS_PATTERN = re.compile(
    r"(分子|原子|电磁|量子|DNA|RNA|细胞|酶|基因|化合物|反应方程|热力学|电路|电场|磁场|"
    r"derivative|integral|theorem|hypothesis|molecule|atom|enzyme|circuit)",
    re.IGNORECASE,
)
_DEPTH_INDICATORS = re.compile(
    r"(为什么|原理|证明|推导|本质|深入|详细分析|比较|区别|联系|如何理解|机制|"
    r"why|prove|derive|mechanism|compare|difference|explain in depth)",
    re.IGNORECASE,
)
_MULTI_STEP_INDICATORS = re.compile(
    r"(步骤|流程|第一步|首先.*然后|分析.*并|"
    r"step by step|first.*then|analyze and)",
    re.IGNORECASE,
)


def assess(message: str) -> ComplexityAssessment:
    """
    评估消息复杂度，返回 ComplexityAssessment。

    执行时间 < 3ms (p99)。
    """
    text = str(message or "").strip()
    if not text:
        return ComplexityAssessment(
            level=ComplexityLevel.TRIVIAL,
            confidence=1.0,
            signals=["empty_message"],
            suggested_tier_delta=-2,
        )

    signals: list[str] = []
    score = 0  # 复杂度得分，映射到 ComplexityLevel

    # ---- 快速匹配：问候/确认 ----
    if _GREETING_PATTERN.match(text) or _CONFIRMATION_PATTERN.match(text):
        signals.append("greeting_or_confirmation")
        return ComplexityAssessment(
            level=ComplexityLevel.TRIVIAL,
            confidence=0.95,
            signals=signals,
            suggested_tier_delta=-2,
        )

    char_len = len(text)

    # ---- 长度信号（汉字平均1字=1 char，英文平均1词=5 chars）----
    if char_len < 5:
        score += 0
        signals.append(f"len<5({char_len})")
    elif char_len < 20:
        score += 1
        signals.append(f"len<20({char_len})")
    elif char_len < 80:
        score += 2
        signals.append(f"len<80({char_len})")
    elif char_len < 200:
        score += 3
        signals.append(f"len<200({char_len})")
    elif char_len < 500:
        score += 4
        signals.append(f"len<500({char_len})")
    else:
        score += 5
        signals.append(f"len>500({char_len})")

    # ---- 问句数量 ----
    question_count = len(_QUESTION_PATTERN.findall(text))
    if question_count >= 2:
        score += 1
        signals.append(f"multi_questions({question_count})")

    # ---- 领域专业性 ----
    if _MATH_FORMULA_PATTERN.search(text):
        score += 1
        signals.append("math_formula")
    if _CODE_BLOCK_PATTERN.search(text):
        score += 1
        signals.append("code_block")
    if _SCIENCE_TERMS_PATTERN.search(text):
        score += 1
        signals.append("science_terms")

    # ---- 深度指示词 ----
    if _DEPTH_INDICATORS.search(text):
        score += 1
        signals.append("depth_indicator")
    if _MULTI_STEP_INDICATORS.search(text):
        score += 1
        signals.append("multi_step")

    # ---- 映射 score → ComplexityLevel ----
    if score <= 1:
        level = ComplexityLevel.TRIVIAL
        delta = -2
        confidence = 0.85
    elif score <= 2:
        level = ComplexityLevel.SIMPLE
        delta = -1
        confidence = 0.80
    elif score <= 4:
        level = ComplexityLevel.MODERATE
        delta = 0
        confidence = 0.75
    elif score <= 6:
        level = ComplexityLevel.COMPLEX
        delta = +1
        confidence = 0.75
    else:
        level = ComplexityLevel.EXPERT
        delta = +1  # 最多升一级，不强制用 REASONING（agent policy 会限制）
        confidence = 0.70

    return ComplexityAssessment(
        level=level,
        confidence=confidence,
        signals=signals,
        suggested_tier_delta=delta,
    )
