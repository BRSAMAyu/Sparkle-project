"""AI response quality evaluator — rule-based + optional LLM scoring.

Evaluates AI responses on 6 quality dimensions. The rule-based evaluator
reuses patterns from ai_behavior_classifier.py for fast scoring without
external LLM calls. An optional LLM path provides deeper qualitative scores.
"""
from __future__ import annotations

from typing import Any

from ..sim.ai_behavior_classifier import AIBehaviorClass, classify_ai_response


# ── Quality Dimensions ──────────────────────────────────────

class QualityDim:
    HELPFULNESS = "helpfulness"
    SPECIFICITY = "specificity"
    ENGAGEMENT = "engagement"
    COHERENCE = "coherence"
    SAFETY = "safety"
    CONCISENESS = "conciseness"

DIMENSIONS = [
    QualityDim.HELPFULNESS,
    QualityDim.SPECIFICITY,
    QualityDim.ENGAGEMENT,
    QualityDim.COHERENCE,
    QualityDim.SAFETY,
    QualityDim.CONCISENESS,
]

DIMENSION_WEIGHTS = {
    QualityDim.HELPFULNESS: 0.30,
    QualityDim.SPECIFICITY: 0.22,
    QualityDim.ENGAGEMENT: 0.18,
    QualityDim.COHERENCE: 0.15,
    QualityDim.SAFETY: 0.10,
    QualityDim.CONCISENESS: 0.05,
}


# ── ResponseQuality ─────────────────────────────────────────

class ResponseQuality:
    """Quality assessment of a single AI response."""

    __slots__ = (
        "turn_id", "overall_score", "dimension_scores",
        "flags", "ai_behavior", "response_len",
    )

    def __init__(
        self,
        turn_id: str,
        overall_score: float = 0.0,
        dimension_scores: dict[str, float] | None = None,
        flags: list[str] | None = None,
        ai_behavior: str = "",
        response_len: int = 0,
    ):
        self.turn_id = turn_id
        self.overall_score = overall_score
        self.dimension_scores = dimension_scores or {}
        self.flags = flags or []
        self.ai_behavior = ai_behavior
        self.response_len = response_len

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "flags": self.flags,
            "ai_behavior": self.ai_behavior,
        }

    @property
    def is_low_quality(self) -> bool:
        return self.overall_score < 0.40

    @property
    def is_high_quality(self) -> bool:
        return self.overall_score >= 0.70


# ── Keyword heuristics (reuse patterns from ai_behavior_classifier) ──

_HELPFUL_KEYWORDS = [
    "你可以", "建议你", "我建议", "推荐", "试试看", "第一步", "方法一",
    "具体做法", "可以这样", "复习计划", "学习计划", "帮你规划",
    "制定一个", "以下是", "帮你安排", "时间表",
]

_SPECIFIC_KEYWORDS = [
    "例如", "比如", "具体", "步骤", "分钟", "小时", "天",
    "第一", "第二", "第三", "首先", "然后", "最后",
]

_ENGAGEMENT_KEYWORDS = [
    "你觉得", "怎么样", "试试", "要不要", "一起",
]

_SAFETY_PATTERNS = [
    "我不能", "无法提供", "不好意思", "抱歉", "我没办法", "不应该",
]

_CONFUSION_PATTERNS = [
    "不太确定", "可能理解错了", "不太清楚",
]

_SHORT_ACK_PATTERNS = [
    "好的", "嗯嗯", "谢谢", "知道了", "明白了", "了解了",
]


def _score_helpfulness(response: str, _user_message: str, _turn_index: int) -> float:
    text = response.strip()
    if len(text) < 20:
        return 0.1
    score = 0.3  # base
    if any(kw in text for kw in _HELPFUL_KEYWORDS):
        score += 0.35
    # Bonus for actionable structure
    if any(kw in text for kw in ["第一步", "第1", "1.", "①"]):
        score += 0.20
    if len(text) > 100:
        score += 0.10
    return min(1.0, score)


def _score_specificity(response: str, _user_message: str, _turn_index: int) -> float:
    text = response.strip()
    if len(text) < 15:
        return 0.0
    score = 0.15
    specific_count = sum(1 for kw in _SPECIFIC_KEYWORDS if kw in text)
    score += min(0.5, specific_count * 0.12)
    # Numeric mentions indicate specificity
    import re
    numbers = len(re.findall(r'\d+', text))
    score += min(0.25, numbers * 0.05)
    # Penalize only-generic responses
    if len(text) > 30 and specific_count == 0 and numbers == 0:
        score = max(0.0, score - 0.15)
    return min(1.0, score)


def _score_engagement(response: str, _user_message: str, _turn_index: int) -> float:
    text = response.strip()
    if not text:
        return 0.0
    score = 0.2
    if any(kw in text for kw in _ENGAGEMENT_KEYWORDS):
        score += 0.30
    if text.rstrip().endswith("？") or text.rstrip().endswith("?"):
        score += 0.35
    # Quick acknowledgments are low engagement
    if len(text) < 15 and any(ack in text for ack in _SHORT_ACK_PATTERNS):
        return 0.05
    return min(1.0, score)


def _score_coherence(response: str, _user_message: str, _turn_index: int) -> float:
    text = response.strip()
    if len(text) < 5:
        return 0.0
    score = 0.5
    if len(text) > 20:
        score += 0.25
    if any(p in text for p in _CONFUSION_PATTERNS):
        score -= 0.25
    # Penalize extreme repetition
    if len(text) > 30:
        words = text.split()
        if len(words) > 5:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                score -= 0.30
    return max(0.0, min(1.0, score))


def _score_safety(response: str, _user_message: str, _turn_index: int) -> float:
    """High score = safe. Refusals reduce score slightly but aren't unsafe."""
    text = response.strip()
    if not text:
        return 1.0
    score = 0.9
    if any(p in text for p in _SAFETY_PATTERNS):
        score -= 0.15
    return max(0.3, score)


def _score_conciseness(response: str, _user_message: str, _turn_index: int) -> float:
    text = response.strip()
    length = len(text)
    if length < 10:
        return 0.2
    if 50 <= length <= 500:
        return 0.9
    if length < 50:
        return 0.6
    # > 500 chars: diminishing returns
    if length > 800:
        return 0.3
    # 500-800: acceptable
    return 0.5


_SCORERS = {
    QualityDim.HELPFULNESS: _score_helpfulness,
    QualityDim.SPECIFICITY: _score_specificity,
    QualityDim.ENGAGEMENT: _score_engagement,
    QualityDim.COHERENCE: _score_coherence,
    QualityDim.SAFETY: _score_safety,
    QualityDim.CONCISENESS: _score_conciseness,
}


# ── ResponseEvaluator ───────────────────────────────────────

class ResponseEvaluator:
    """Evaluates AI response quality per turn."""

    def __init__(
        self,
        *,
        enable_llm: bool = False,
        llm_provider: str = "",
        llm_model: str = "",
    ):
        self.enable_llm = enable_llm
        self.llm_provider = llm_provider
        self.llm_model = llm_model

    def evaluate(
        self,
        turn: dict[str, Any],
        *,
        session_context: dict[str, Any] | None = None,
    ) -> ResponseQuality:
        """Score a single turn's AI response."""
        response_text = turn.get("ai_response", "")
        user_message = turn.get("user_message", "")
        turn_index = turn.get("turn_index", 0)
        turn_id = turn.get("turn_id", "")

        dimension_scores = self._rule_based_score(response_text, user_message, turn_index)
        flags = self._compute_flags(response_text, dimension_scores)
        overall = self._composite_score(dimension_scores)
        behavior = classify_ai_response(response_text).value
        response_len = len(response_text)

        return ResponseQuality(
            turn_id=turn_id,
            overall_score=round(overall, 4),
            dimension_scores={k: round(v, 4) for k, v in dimension_scores.items()},
            flags=flags,
            ai_behavior=behavior,
            response_len=response_len,
        )

    def evaluate_session(
        self,
        turns: list[dict[str, Any]],
        *,
        session_context: dict[str, Any] | None = None,
    ) -> list[ResponseQuality]:
        """Score all turns in a session."""
        return [
            self.evaluate(t, session_context=session_context)
            for t in sorted(turns, key=lambda t: t.get("turn_index", 0))
        ]

    def _rule_based_score(
        self, response_text: str, user_message: str, turn_index: int
    ) -> dict[str, float]:
        scores = {}
        for dim, scorer in _SCORERS.items():
            try:
                scores[dim] = scorer(response_text, user_message, turn_index)
            except Exception:
                scores[dim] = 0.0
        return scores

    def _composite_score(self, dimension_scores: dict[str, float]) -> float:
        total = 0.0
        for dim, weight in DIMENSION_WEIGHTS.items():
            total += weight * dimension_scores.get(dim, 0.0)
        return total

    def _compute_flags(
        self, response_text: str, scores: dict[str, float]
    ) -> list[str]:
        flags: list[str] = []
        if len(response_text.strip()) < 10:
            flags.append("empty_response")
        if scores.get(QualityDim.HELPFULNESS, 0) < 0.25:
            flags.append("low_helpfulness")
        if scores.get(QualityDim.COHERENCE, 0) < 0.20:
            flags.append("low_coherence")
        if scores.get(QualityDim.SAFETY, 0) < 0.5:
            flags.append("safety_concern")
        return flags
