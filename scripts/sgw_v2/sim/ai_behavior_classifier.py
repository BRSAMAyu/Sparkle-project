"""AI behavior classifier — rule-based, no LLM calls.

Priority-ordered pattern matching. ~80%+ accuracy on typical Sparkle AI responses.
Falls back to NEUTRAL when no pattern matches, which is safe for state machine.
"""
from __future__ import annotations

import re
from enum import Enum


class AIBehaviorClass(str, Enum):
    GIVE_ADVICE = "give_advice"
    ASK_QUESTION = "ask_question"
    ENCOURAGE = "encourage"
    CONFIRM = "confirm"
    MISUNDERSTAND = "misunderstand"
    REFUSE = "refuse"
    DIVERGE = "diverge"
    NEUTRAL = "neutral"


# Priority-ordered patterns (first match wins)
_PATTERNS: list[tuple[AIBehaviorClass, list[str]]] = [
    (AIBehaviorClass.REFUSE, [
        "我不能", "无法提供", "不好意思，这个", "抱歉，这个", "我没办法",
        "不应该", "不建议你",
    ]),
    (AIBehaviorClass.ASK_QUESTION, [
        # Ends with question mark
    ]),
    (AIBehaviorClass.GIVE_ADVICE, [
        "你可以试试", "建议你", "我建议", "推荐你", "试试看",
        "第一步", "第二步", "第三步", "以下是", "可以这样做",
        "方法一", "方法二", "具体做法", "一个方法是", "你可以",
        "制定一个", "帮你规划", "帮你安排", "可以这样",
        "复习计划", "学习计划", "时间表",
    ]),
    (AIBehaviorClass.ENCOURAGE, [
        "很棒", "做得好", "加油", "你很", "不错哦",
        "继续努力", "相信自己", "很有潜力", "你已经", "很厉害",
        "一定能", "一定可以", "没问题", "进步很大",
    ]),
    (AIBehaviorClass.CONFIRM, [
        "好的，", "我理解", "总结一下", "所以你", "你的意思是",
        "明白了", "了解了", "也就是说",
    ]),
    (AIBehaviorClass.MISUNDERSTAND, [
        "你是说", "不好意思我可能理解错了", "如果我没理解错",
    ]),
    (AIBehaviorClass.DIVERGE, [
        "顺便说", "对了，", "说到这个", "想起",
    ]),
]


def classify_ai_response(text: str) -> AIBehaviorClass:
    """Classify an AI response into a behavior class.

    Rules applied in priority order:
    1. Check for refusal patterns
    2. Check for question mark ending (ask_question)
    3. Check for advice patterns
    4. Check for encouragement patterns
    5. Check for confirmation patterns
    6. Check for misunderstanding patterns
    7. Check for divergence patterns
    8. Default: NEUTRAL
    """
    if not text or not text.strip():
        return AIBehaviorClass.NEUTRAL

    stripped = text.strip()

    # 1. Pattern-based matching (skip ASK_QUESTION which is handled separately)
    for behavior, patterns in _PATTERNS:
        if behavior == AIBehaviorClass.ASK_QUESTION:
            continue  # Handled below
        if any(p in stripped for p in patterns):
            return behavior

    # 2. Question detection: ends with ？ or ? OR contains question patterns
    if stripped.endswith("？") or stripped.endswith("?"):
        return AIBehaviorClass.ASK_QUESTION

    # Also check for mid-text questions (common in Chinese AI responses)
    question_patterns = ["怎么样？", "对吗？", "可以吗？", "要不要", "愿不愿意",
                         "有没有", "是什么", "为什么", "怎么", "哪些", "哪个",
                         "多少", "几", "什么时候", "吗？", "呢？"]
    if any(p in stripped for p in question_patterns):
        return AIBehaviorClass.ASK_QUESTION

    # 3. Long response without any pattern → likely advice or neutral
    if len(stripped) > 200:
        # Very long responses usually contain some advice
        return AIBehaviorClass.GIVE_ADVICE

    # 4. Default
    return AIBehaviorClass.NEUTRAL


def classify_confidence(text: str, result: AIBehaviorClass) -> float:
    """Estimate confidence of classification. Used for state machine fallback."""
    if result == AIBehaviorClass.NEUTRAL:
        return 0.3  # Low confidence for default

    # Count how many patterns matched (rough proxy)
    matched = sum(1 for behavior, patterns in _PATTERNS
                  if behavior == result
                  for p in patterns if p in text)

    if matched >= 2:
        return 0.9
    elif matched == 1:
        return 0.7
    elif result == AIBehaviorClass.ASK_QUESTION:
        return 0.85  # Question mark is a strong signal
    else:
        return 0.5
