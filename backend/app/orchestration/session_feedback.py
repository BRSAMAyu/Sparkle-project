from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from datetime import datetime, timedelta, UTC
from typing import Any
from app.core.i18n import I18n


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
    "simplify": "session_feedback.visible_prefix_simplify",
    "expand": "session_feedback.visible_prefix_expand",
    "mismatch": "session_feedback.visible_prefix_mismatch",
}

_TRANSITION_HINT_POOLS = {
    "simplify": ("session_feedback.transition_simplify_1", "session_feedback.transition_simplify_2"),
    "expand": ("session_feedback.transition_expand_1", "session_feedback.transition_expand_2"),
    "mismatch": ("session_feedback.transition_mismatch_1", "session_feedback.transition_mismatch_2"),
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
    transition_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "confidence": round(float(self.confidence), 4),
            "trigger_text": self.trigger_text,
            "applies_adaptation": self.applies_adaptation,
            "visible_hint": self.visible_hint,
            "transition_hint": self.transition_hint,
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
            transition_hint=str(payload.get("transition_hint") or "") or None,
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
    conversation_rhythm: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_signal": self.active_signal,
            "recent_signals": list(self.recent_signals),
            "applied_strategy": self.applied_strategy,
            "expires_at": self.expires_at,
            "conversation_rhythm": self.conversation_rhythm,
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
            conversation_rhythm=payload.get("conversation_rhythm") if isinstance(payload.get("conversation_rhythm"), dict) else None,
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
    visible_hint = I18n.t(_VISIBLE_PREFIXES[signal_type], locale="zh") if applies and signal_type in _VISIBLE_PREFIXES else None
    transition_pool = _TRANSITION_HINT_POOLS.get(signal_type, ("",))
    transition_hint = I18n.t(transition_pool[0], locale="zh") if applies and transition_pool[0] else None
    return SessionFeedbackSignal(
        signal_type=signal_type,
        confidence=confidence,
        trigger_text=trigger_text,
        applies_adaptation=applies,
        visible_hint=visible_hint,
        transition_hint=transition_hint,
    )


def _extract_user_messages(conversation_messages: list[dict[str, Any]] | None) -> list[str]:
    items = conversation_messages if isinstance(conversation_messages, list) else []
    results: list[str] = []
    for message in items:
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").lower() != "user":
            continue
        content = str(message.get("content") or "").strip()
        if content:
            results.append(content)
    return results


def _keyword_set(text: str) -> set[str]:
    normalized = _normalize(text)
    tokens = {
        token
        for token in normalized.replace("？", " ").replace("?", " ").replace("，", " ").replace(",", " ").split()
        if len(token) >= 2
    }
    if tokens:
        return tokens
    condensed = normalized.replace("？", "").replace("?", "").replace("，", "").replace(",", "")
    return {
        condensed[idx:idx + 4]
        for idx in range(max(0, len(condensed) - 3))
        if len(condensed[idx:idx + 4].strip()) == 4
    }


def _question_like(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return False
    if "？" in normalized or "?" in normalized:
        return True
    return any(normalized.startswith(prefix) for prefix in _QUESTION_STARTERS)


def _shared_question_focus(a: str, b: str) -> int:
    normalized_a = _normalize(a).replace("？", "").replace("?", "")
    normalized_b = _normalize(b).replace("？", "").replace("?", "")
    if not normalized_a or not normalized_b:
        return 0
    match = SequenceMatcher(None, normalized_a, normalized_b).find_longest_match(
        0,
        len(normalized_a),
        0,
        len(normalized_b),
    )
    return int(match.size)


def analyze_conversation_rhythm(
    *,
    user_message: str | None = None,
    conversation_messages: list[dict[str, Any]] | None = None,
    previous_user_messages: list[str] | None = None,
    current_user_message: str | None = None,
    previous_signal_type: str | None = None,
) -> dict[str, Any] | None:
    # Backward-compatible entrypoint: older callers/tests passed
    # previous_user_messages/current_user_message instead of the newer
    # conversation_messages/user_message pair.
    history = list(previous_user_messages or []) if previous_user_messages is not None else _extract_user_messages(conversation_messages)
    current_message = str(current_user_message if current_user_message is not None else user_message or "").strip()
    series = [*history[-4:], current_message]
    series = [item for item in series if item]
    if len(series) < 3:
        return None

    lengths = [len(item.strip()) for item in series[-3:]]
    trend = "stable"
    signal_type = ""
    guidance = ""
    recent_three = series[-3:]
    if (
        len(recent_three) == 3
        and all(_question_like(item) for item in recent_three)
        and (
            str(previous_signal_type or "").strip() == "expand"
            or min(
                _shared_question_focus(recent_three[-1], recent_three[0]),
                _shared_question_focus(recent_three[-1], recent_three[1]),
            ) >= 4
        )
    ):
        signal_type = "stalled_followup"
        guidance = I18n.t("session_feedback.stalled_followup_guidance", locale="zh")
    elif lengths[0] >= lengths[1] >= lengths[2] and lengths[0] - lengths[2] >= 6:
        trend = "shrinking"
        signal_type = "patience_drop"
        guidance = I18n.t("session_feedback.patience_drop_guidance", locale="zh")
    elif lengths[0] < lengths[1] < lengths[2]:
        trend = "expanding"
        signal_type = "deepening_focus"
        guidance = I18n.t("session_feedback.deepening_focus_guidance", locale="zh")

    if not signal_type:
        return None
    return {
        "mode": signal_type,
        "reason": guidance,
        "signal_type": signal_type,
        "trend": trend,
        "recent_lengths": lengths,
        "guidance": guidance,
    }


def build_session_feedback_instruction(signal: SessionFeedbackSignal | dict[str, Any] | None) -> str:
    parsed = signal if isinstance(signal, SessionFeedbackSignal) else SessionFeedbackSignal.from_dict(signal)
    if not parsed or not parsed.applies_adaptation:
        return ""

    prefix_key = _VISIBLE_PREFIXES.get(parsed.signal_type, "")
    prefix = parsed.visible_hint or I18n.t(prefix_key, locale="zh") if prefix_key else ""
    transition_hint = parsed.transition_hint or ""
    if parsed.signal_type == "simplify":
        return (
            "用户刚刚明确表示上一轮内容太难、太长或不够易懂。\n"
            f"优先在回答开头自然使用这句过渡语：{transition_hint or prefix}\n"
            f"如果你没有自然使用过渡语，系统会在最终输出兜底补上：{prefix}\n"
            "随后严格执行：\n"
            "- 控制在 3 个要点以内\n"
            "- 优先短句，不堆术语\n"
            "- 最多给 1 个例子\n"
            "- 先结论，再补关键说明"
        )
    if parsed.signal_type == "expand":
        return (
            "用户刚刚明确要求更详细、更展开的解释。\n"
            f"优先在回答开头自然使用这句过渡语：{transition_hint or prefix}\n"
            f"如果你没有自然使用过渡语，系统会在最终输出兜底补上：{prefix}\n"
            "随后严格执行：\n"
            "- 使用分步骤解释\n"
            "- 至少补 1 个例子或类比\n"
            "- 明确前提、因果和结论\n"
            "- 不要只给简短结论"
        )
    if parsed.signal_type == "mismatch":
        return (
            "用户刚刚明确表示上一轮答偏了方向。\n"
            f"优先在回答开头自然使用这句过渡语：{transition_hint or prefix}\n"
            f"如果你没有自然使用过渡语，系统会在最终输出兜底补上：{prefix}\n"
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

    prefix_key = _VISIBLE_PREFIXES.get(parsed.signal_type, "")
    prefix = parsed.visible_hint or I18n.t(prefix_key, locale="zh") if prefix_key else ""
    if not prefix:
        return response, False

    normalized_response = str(response or "").lstrip()
    transition_hint = str(parsed.transition_hint or "").strip()
    normalized_prefix = prefix.rstrip("：:")
    normalized_transition_hint = transition_hint.rstrip("：:").strip()
    if (
        normalized_response.startswith(prefix)
        or normalized_response.startswith(normalized_prefix)
        or (normalized_transition_hint and normalized_response.startswith(normalized_transition_hint))
    ):
        return response, True

    if not normalized_response:
        return prefix, True

    return f"{prefix}\n{response}", True


def build_conversation_rhythm_instruction(rhythm: dict[str, Any] | None) -> str:
    if not isinstance(rhythm, dict):
        return ""
    signal_type = str(rhythm.get("signal_type") or rhythm.get("mode") or "").strip()
    guidance = str(rhythm.get("guidance") or rhythm.get("reason") or "").strip()
    if signal_type == "deepening_focus" and "允许更展开" not in guidance:
        guidance = (
            guidance + I18n.t("session_feedback.rhythm_deepening_focus", locale="zh")
            if guidance
            else I18n.t("session_feedback.deepening_focus_guidance", locale="zh")
        )
    if not guidance and signal_type == "patience_drop":
        guidance = I18n.t("session_feedback.rhythm_patience_drop", locale="zh")
    if not guidance and signal_type == "stalled_followup":
        guidance = I18n.t("session_feedback.rhythm_stalled_followup", locale="zh")
    if not guidance or not signal_type:
        return ""
    return (
        f"会话节奏信号：{signal_type}\n"
        f"{guidance}"
    )


def build_session_adaptation_context(
    *,
    signal: SessionFeedbackSignal | None,
    existing_context: SessionAdaptationContext | None = None,
    conversation_rhythm: dict[str, Any] | None = None,
) -> SessionAdaptationContext:
    existing = existing_context or SessionAdaptationContext()
    recent_signals: list[dict[str, Any]] = []
    if signal is not None:
        recent_signals.append(signal.to_dict())
        for entry in existing.recent_signals:
            if isinstance(entry, dict) and entry != signal.to_dict():
                recent_signals.append(entry)
            if len(recent_signals) >= 3:
                break
    else:
        recent_signals = list(existing.recent_signals)[:3]

    expires_at = (_utcnow() + timedelta(seconds=SESSION_FEEDBACK_TTL_SECONDS)).isoformat()
    return SessionAdaptationContext(
        active_signal=signal.to_dict() if signal and signal.applies_adaptation else None,
        recent_signals=recent_signals[:3],
        applied_strategy=signal.signal_type if signal and signal.applies_adaptation else existing.applied_strategy,
        expires_at=expires_at,
        conversation_rhythm=conversation_rhythm or existing.conversation_rhythm,
    )
