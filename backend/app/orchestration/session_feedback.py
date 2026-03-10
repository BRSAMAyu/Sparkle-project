from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


SESSION_FEEDBACK_TTL_SECONDS = 6 * 60 * 60

_SIGNAL_PRIORITY = {
    "mismatch": 5,
    "simplify": 4,
    "expand": 3,
    "approval": 2,
    "topic_shift": 1,
}

_SIGNAL_THRESHOLDS = {
    "mismatch": 0.75,
    "simplify": 0.75,
    "expand": 0.70,
    "approval": 0.70,
}

_VISIBLE_PREFIXES = {
    "simplify": "我换成更简洁的版本：",
    "expand": "我改用更展开的方式说明：",
    "mismatch": "我直接按你要的方向重答：",
}

_MISMATCH_PHRASES = (
    "不是这个意思",
    "不对",
    "不是我想要的",
    "答非所问",
    "你理解错了",
    "不是这个问题",
)
_SIMPLIFY_PHRASES = (
    "简单点说",
    "简单一点",
    "说简单点",
    "太难了",
    "听不懂",
    "说短一点",
    "短一点",
    "太复杂了",
    "看不懂",
    "讲简单点",
)
_EXPAND_PHRASES = (
    "详细点",
    "详细一点",
    "展开说说",
    "展开讲讲",
    "举个例子",
    "多讲一点",
    "再详细说说",
    "具体一点",
    "说细一点",
)
_APPROVAL_PHRASES = (
    "明白了",
    "可以",
    "懂了",
    "知道了",
    "收到",
    "ok",
    "好的",
)
_TOPIC_SHIFT_MARKERS = (
    "换个问题",
    "另外",
    "顺便",
    "我还有个问题",
    "再问一个",
    "另一个问题",
    "顺带问",
    "话说",
)
_QUESTION_STARTERS = (
    "怎么",
    "为什么",
    "请问",
    "帮我",
    "如何",
    "能不能",
    "有没有",
)
_CONTEXT_MARKERS = (
    "继续",
    "刚才",
    "上面",
    "这个",
    "那个",
    "前面",
    "上一条",
    "再详细",
    "更简单",
    "展开",
    "例子",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize(text: str | None) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _find_trigger(text: str, phrases: tuple[str, ...]) -> str | None:
    for phrase in phrases:
        if phrase in text:
            return phrase
    return None


def _confidence_bucket(confidence: float) -> str:
    if confidence >= 0.9:
        return "0.90_1.00"
    if confidence >= 0.75:
        return "0.75_0.89"
    if confidence >= 0.6:
        return "0.60_0.74"
    return "0.00_0.59"


@dataclass
class SessionFeedbackSignal:
    signal_type: str
    confidence: float
    trigger_text: str
    applies_adaptation: bool
    visible_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "confidence": round(float(self.confidence), 4),
            "trigger_text": self.trigger_text,
            "applies_adaptation": self.applies_adaptation,
            "visible_hint": self.visible_hint,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> SessionFeedbackSignal | None:
        if not isinstance(payload, dict):
            return None
        signal_type = str(payload.get("signal_type") or "").strip()
        if not signal_type:
            return None
        return cls(
            signal_type=signal_type,
            confidence=float(payload.get("confidence") or 0.0),
            trigger_text=str(payload.get("trigger_text") or ""),
            applies_adaptation=bool(payload.get("applies_adaptation")),
            visible_hint=str(payload.get("visible_hint") or "") or None,
        )

    @property
    def priority(self) -> int:
        return _SIGNAL_PRIORITY.get(self.signal_type, 0)

    @property
    def confidence_bucket(self) -> str:
        return _confidence_bucket(self.confidence)


@dataclass
class SessionAdaptationContext:
    active_signal: dict[str, Any] | None = None
    recent_signals: list[dict[str, Any]] = field(default_factory=list)
    applied_strategy: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_signal": self.active_signal,
            "recent_signals": list(self.recent_signals),
            "applied_strategy": self.applied_strategy,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> SessionAdaptationContext:
        if not isinstance(payload, dict):
            return cls()
        recent_signals = payload.get("recent_signals")
        return cls(
            active_signal=payload.get("active_signal") if isinstance(payload.get("active_signal"), dict) else None,
            recent_signals=list(recent_signals) if isinstance(recent_signals, list) else [],
            applied_strategy=str(payload.get("applied_strategy") or "") or None,
            expires_at=str(payload.get("expires_at") or "") or None,
        )


def detect_session_feedback_signal(
    *,
    user_message: str,
    previous_assistant_message: str,
    previous_user_message: str | None = None,
) -> SessionFeedbackSignal | None:
    message = _normalize(user_message)
    previous_assistant = _normalize(previous_assistant_message)
    previous_user = _normalize(previous_user_message)

    if not message or not previous_assistant:
        return None

    mismatch = _find_trigger(message, _MISMATCH_PHRASES)
    if mismatch:
        return _build_signal("mismatch", 0.95, mismatch)

    simplify = _find_trigger(message, _SIMPLIFY_PHRASES)
    if simplify:
        confidence = 0.82 if simplify == "太难了" else 0.9
        return _build_signal("simplify", confidence, simplify)

    expand = _find_trigger(message, _EXPAND_PHRASES)
    if expand:
        confidence = 0.86 if expand == "举个例子" else 0.88
        return _build_signal("expand", confidence, expand)

    approval = _find_approval_trigger(message)
    if approval:
        return _build_signal("approval", 0.78, approval)

    if _looks_like_topic_shift(message, previous_assistant, previous_user):
        return _build_signal("topic_shift", 0.62, "topic_shift")

    return None


def _find_approval_trigger(message: str) -> str | None:
    approval = _find_trigger(message, _APPROVAL_PHRASES)
    if not approval:
        return None
    # Avoid treating long replies that merely contain "可以/好的" as approval.
    if approval in {"可以", "好的"} and len(message) > 8:
        return None
    return approval


def _looks_like_topic_shift(message: str, previous_assistant: str, previous_user: str) -> bool:
    if any(marker in message for marker in _CONTEXT_MARKERS):
        return False
    if any(phrase in message for phrase in _MISMATCH_PHRASES + _SIMPLIFY_PHRASES + _EXPAND_PHRASES):
        return False
    if _find_approval_trigger(message):
        return False
    if any(marker in message for marker in _TOPIC_SHIFT_MARKERS):
        return True
    if len(message) < 8:
        return False
    if not any(starter in message for starter in _QUESTION_STARTERS) and "？" not in message and "?" not in message:
        return False
    if previous_user and message == previous_user:
        return False
    return True


def _build_signal(signal_type: str, confidence: float, trigger_text: str) -> SessionFeedbackSignal:
    threshold = _SIGNAL_THRESHOLDS.get(signal_type)
    applies = signal_type in _VISIBLE_PREFIXES and threshold is not None and confidence >= threshold
    return SessionFeedbackSignal(
        signal_type=signal_type,
        confidence=confidence,
        trigger_text=trigger_text,
        applies_adaptation=applies,
        visible_hint=_VISIBLE_PREFIXES.get(signal_type) if applies else None,
    )


def build_session_feedback_instruction(signal: SessionFeedbackSignal | dict[str, Any] | None) -> str:
    parsed = signal if isinstance(signal, SessionFeedbackSignal) else SessionFeedbackSignal.from_dict(signal)
    if not parsed or not parsed.applies_adaptation:
        return ""

    prefix = parsed.visible_hint or _VISIBLE_PREFIXES.get(parsed.signal_type, "")
    if parsed.signal_type == "simplify":
        return (
            "用户刚刚明确表示上一轮内容太难、太长或不够易懂。\n"
            f"你必须在回答开头先用这句极短提示：{prefix}\n"
            "随后严格执行：\n"
            "- 控制在 3 个要点以内\n"
            "- 优先短句，不堆术语\n"
            "- 最多给 1 个例子\n"
            "- 先结论，再补关键说明"
        )
    if parsed.signal_type == "expand":
        return (
            "用户刚刚明确要求更详细、更展开的解释。\n"
            f"你必须在回答开头先用这句极短提示：{prefix}\n"
            "随后严格执行：\n"
            "- 使用分步骤解释\n"
            "- 至少补 1 个例子或类比\n"
            "- 明确前提、因果和结论\n"
            "- 不要只给简短结论"
        )
    if parsed.signal_type == "mismatch":
        return (
            "用户刚刚明确表示上一轮答偏了方向。\n"
            f"你必须在回答开头先用这句极短提示：{prefix}\n"
            "随后严格执行：\n"
            "- 不要为上一轮辩护\n"
            "- 直接按用户当前诉求重答\n"
            "- 第一段先校正方向，再给新答案\n"
            "- 回答要面向当前问题，而不是复述旧答案"
        )
    return ""


def apply_session_feedback_visible_prefix(
    response: str,
    signal: SessionFeedbackSignal | dict[str, Any] | None,
) -> tuple[str, bool]:
    parsed = signal if isinstance(signal, SessionFeedbackSignal) else SessionFeedbackSignal.from_dict(signal)
    if not parsed or not parsed.applies_adaptation:
        return response, False

    prefix = parsed.visible_hint or _VISIBLE_PREFIXES.get(parsed.signal_type)
    if not prefix:
        return response, False

    normalized_response = str(response or "").lstrip()
    normalized_prefix = prefix.rstrip("：:")
    if normalized_response.startswith(prefix) or normalized_response.startswith(normalized_prefix):
        return response, True

    if not normalized_response:
        return prefix, True

    return f"{prefix}\n{response}", True


def build_session_adaptation_context(
    *,
    signal: SessionFeedbackSignal,
    existing_context: SessionAdaptationContext | None = None,
) -> SessionAdaptationContext:
    existing = existing_context or SessionAdaptationContext()
    recent_signals = [signal.to_dict()]
    for entry in existing.recent_signals:
        if isinstance(entry, dict) and entry != signal.to_dict():
            recent_signals.append(entry)
        if len(recent_signals) >= 3:
            break

    expires_at = (_utcnow() + timedelta(seconds=SESSION_FEEDBACK_TTL_SECONDS)).isoformat()
    return SessionAdaptationContext(
        active_signal=signal.to_dict() if signal.applies_adaptation else None,
        recent_signals=recent_signals[:3],
        applied_strategy=signal.signal_type if signal.applies_adaptation else None,
        expires_at=expires_at,
    )
