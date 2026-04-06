"""
Metadata registry for inferred preferences.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InferredFieldMeta:
    source: str
    explanation_template: str
    adjustable: bool = False
    related_fields: list[str] = field(default_factory=list)


INFERRED_META: dict[str, InferredFieldMeta] = {
    "achievement_motivation_response": InferredFieldMeta(
        source="achievement_signals",
        explanation_template="Recent achievement unlocks suggest you respond best to {value} reinforcement.",
        adjustable=True,
        related_fields=["achievement_reward_sensitivity", "achievement_pace_style"],
    ),
    "achievement_pace_style": InferredFieldMeta(
        source="achievement_signals",
        explanation_template="Your recent achievement pattern looks more {value} in pace.",
        adjustable=True,
        related_fields=["achievement_peak_hours"],
    ),
    "achievement_peak_hours": InferredFieldMeta(
        source="achievement_signals",
        explanation_template="Recent achievements tend to unlock around {hours_text}.",
        adjustable=False,
        related_fields=["peak_focus_hours"],
    ),
    "achievement_reward_sensitivity": InferredFieldMeta(
        source="achievement_signals",
        explanation_template="Recent achievement rarity and sharing behavior suggest a {value} reward sensitivity.",
        adjustable=True,
        related_fields=["achievement_motivation_response"],
    ),
    "avg_question_complexity": InferredFieldMeta(
        source="chat_behavior",
        explanation_template="Recent conversations suggest an average question complexity of {value:.2f}.",
        adjustable=False,
    ),
    "chat_active_hours": InferredFieldMeta(
        source="chat_behavior",
        explanation_template="Your recent chat activity is concentrated around {hours_text}.",
        adjustable=False,
    ),
    "checkin_regularity": InferredFieldMeta(
        source="streak_stats",
        explanation_template="Across your full account history, you have checked in on about {value_pct:.0f}% of days.",
        adjustable=False,
    ),
    "community_engagement_level": InferredFieldMeta(
        source="community",
        explanation_template="Based on recent community activity, your engagement level is {value}.",
        adjustable=False,
    ),
    "consecutive_ignores": InferredFieldMeta(
        source="push_feedback",
        explanation_template="You recently ignored {value} pushes in a row, so push pressure has been reduced.",
        adjustable=False,
    ),
    "content_contribution_rate": InferredFieldMeta(
        source="community",
        explanation_template="About {value_pct:.0f}% of your community activity is contribution-oriented.",
        adjustable=False,
    ),
    "curiosity_push_receptivity": InferredFieldMeta(
        source="push_feedback",
        explanation_template="Curiosity pushes have been performing at a {value} receptivity level recently.",
        adjustable=True,
    ),
    "depth_preference_signal": InferredFieldMeta(
        source="chat_behavior",
        explanation_template="You tend to stay on the same topic for several turns, so the system inferred a preference for deeper explanations.",
        adjustable=True,
    ),
    "error_correction_rate": InferredFieldMeta(
        source="error_book",
        explanation_template="Your recent error correction rate is about {value_pct:.0f}%.",
        adjustable=False,
    ),
    "error_density_score": InferredFieldMeta(
        source="error_book",
        explanation_template="Your 14-day error density score is {value:.2f}; when it is high, the system slows the learning pace.",
        adjustable=False,
    ),
    "difficulty_feedback_ratio": InferredFieldMeta(
        source="task_feedback",
        explanation_template="Recent task difficulty feedback is distributed as {dict_text}.",
        adjustable=False,
    ),
    "focus_completion_rate": InferredFieldMeta(
        source="focus_sessions",
        explanation_template="Your recent focus-session completion rate is about {value_pct:.0f}%.",
        adjustable=False,
    ),
    "inactive_push_hours": InferredFieldMeta(
        source="push_feedback",
        explanation_template="Pushes are often ignored around {hours_text}, so those hours are treated as quieter windows.",
        adjustable=True,
    ),
    "knowledge_expansion_satisfaction": InferredFieldMeta(
        source="galaxy_feedback",
        explanation_template="Your recent knowledge-expansion satisfaction is about {value_pct:.0f}%.",
        adjustable=False,
    ),
    "motivation_type": InferredFieldMeta(
        source="streak_stats",
        explanation_template="Your recent check-in pattern looks more like a {value} motivation style.",
        adjustable=False,
    ),
    "peak_focus_hours": InferredFieldMeta(
        source="focus_sessions",
        explanation_template="Your strongest focus hours recently are {hours_text}.",
        adjustable=False,
    ),
    "preferred_focus_duration": InferredFieldMeta(
        source="focus_sessions",
        explanation_template="Based on completed focus sessions in the last 14 days, your median focus duration is {value} minutes.",
        adjustable=True,
    ),
    "preferred_expansion_depth": InferredFieldMeta(
        source="galaxy_feedback",
        explanation_template="Based on your recent knowledge-expansion ratings, the system inferred a {value} expansion depth preference.",
        adjustable=True,
    ),
    "push_receptivity": InferredFieldMeta(
        source="push_feedback",
        explanation_template="Over the last 7 days, you ignored about {ignore_rate_pct:.0f}% of pushes, so push frequency was reduced.",
        adjustable=True,
        related_fields=["consecutive_ignores", "inactive_push_hours"],
    ),
    "push_receptivity_last_updated": InferredFieldMeta(
        source="push_feedback",
        explanation_template="Push receptivity was last recalculated at {value}.",
        adjustable=False,
    ),
    "recurring_error_tags": InferredFieldMeta(
        source="error_book",
        explanation_template="These recurring error patterns were detected recently: {list_text}.",
        adjustable=False,
    ),
    "response_satisfaction_rate": InferredFieldMeta(
        source="chat_behavior",
        explanation_template="Recent chat behavior suggests a response satisfaction rate of about {value_pct:.0f}%.",
        adjustable=False,
    ),
    "review_accuracy": InferredFieldMeta(
        source="learning_assets",
        explanation_template="Your active learning assets currently show about {value_pct:.0f}% review accuracy.",
        adjustable=False,
    ),
    "review_engagement": InferredFieldMeta(
        source="learning_assets",
        explanation_template="About {value_pct:.0f}% of your active learning assets have review activity.",
        adjustable=False,
    ),
    "social_learning_preference": InferredFieldMeta(
        source="community",
        explanation_template="Your recent community behavior suggests a {value_pct:.0f}% leaning toward social learning.",
        adjustable=True,
    ),
    "streak_consistency": InferredFieldMeta(
        source="streak_stats",
        explanation_template="Your current streak consistency is about {value_pct:.0f}% relative to your best streak.",
        adjustable=False,
    ),
    "task_difficulty_accuracy": InferredFieldMeta(
        source="task_feedback",
        explanation_template="Recent tasks show a median estimate drift of {value_pct:.0f}%.",
        adjustable=False,
    ),
    "task_reflection_depth": InferredFieldMeta(
        source="task_feedback",
        explanation_template="Your recent task reflections look {value} in depth.",
        adjustable=True,
    ),
    "vocabulary_retention_style": InferredFieldMeta(
        source="learning_assets",
        explanation_template="Your current vocabulary retention style looks {value}.",
        adjustable=False,
    ),
}


def build_inferred_explanation(key: str, value: Any, related_values: dict[str, Any] | None = None) -> str:
    meta = INFERRED_META.get(key)
    if meta is None:
        return f"System inferred {key} from recent behavior signals."

    related_values = related_values or {}
    context = {
        "value": value,
        "value_pct": _safe_percent(value),
        "ignore_rate_pct": _safe_percent(1 - float(value)) if isinstance(value, (int, float)) else 0.0,
        "hours_text": _format_hours(related_values.get(key, value)),
        "list_text": _format_list(value),
        "dict_text": _format_dict(value),
    }
    try:
        return meta.explanation_template.format(**context)
    except Exception:
        return f"System inferred {key} from recent behavior signals."


def _format_hours(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "recent active hours"
    hours: list[str] = []
    for raw in value:
        try:
            hour = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23:
            hours.append(f"{hour:02d}:00")
    return ", ".join(hours) if hours else "recent active hours"


def _format_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(str(item) for item in value[:5])


def _safe_percent(value: Any) -> float:
    if not isinstance(value, (int, float)):
        return 0.0
    return float(value) * 100.0


def _format_dict(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    parts: list[str] = []
    for key, raw in list(value.items())[:5]:
        if isinstance(raw, (int, float)):
            parts.append(f"{key} {float(raw) * 100:.0f}%")
        else:
            parts.append(f"{key} {raw}")
    return ", ".join(parts) if parts else "none"
