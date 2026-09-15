from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.i18n import I18n

MAX_PAIN_POINTS = 3
MAX_WINS = 3
MAX_SIGNAL_TEXT_LENGTH = 96
MAX_SUMMARY_LENGTH = 220


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return list(value) if isinstance(value, tuple) else []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int) -> str:
    text = " ".join(_strip(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _extract_cognitive_context(user_context: dict[str, Any]) -> dict[str, Any]:
    payload = user_context.get("cognitive_context") if isinstance(user_context, dict) else None
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _extract_profile_context(user_context: dict[str, Any]) -> dict[str, Any]:
    profile_context = _as_dict(user_context.get("profile_context"))
    if not profile_context:
        return {}
    return profile_context


def _format_error_summary(error_summary: dict[str, Any]) -> str:
    parts: list[str] = []
    total_errors = error_summary.get("total_errors")
    if total_errors is not None:
        try:
            parts.append(I18n.t("learning_state.error_summary", locale="zh", count=int(total_errors)))
        except Exception:
            parts.append(I18n.t("learning_state.error_summary", locale="zh", count=total_errors))
    need_review = error_summary.get("need_review_count") or error_summary.get("due_for_review")
    if need_review is not None:
        try:
            parts.append(I18n.t("learning_state.error_summary_review", locale="zh", count=int(need_review)))
        except Exception:
            parts.append(I18n.t("learning_state.error_summary_review", locale="zh", count=need_review))
    subject_distribution = error_summary.get("subject_distribution")
    if isinstance(subject_distribution, dict) and subject_distribution:
        ranked = sorted(
            (
                (str(subject).strip(), int(count))
                for subject, count in subject_distribution.items()
                if str(subject).strip()
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if ranked:
            parts.append(I18n.t("learning_state.error_high_freq_subject", locale="zh", subject=ranked[0][0]))
    return "；".join(parts)


def _collect_recent_pain_points(user_context: dict[str, Any]) -> tuple[list[str], list[str]]:
    cognitive_context = _extract_cognitive_context(user_context)
    summary = user_context.get("error_summary")
    if not isinstance(summary, dict):
        summary = cognitive_context.get("error_summary")
    recent_errors = user_context.get("recent_errors")
    if not isinstance(recent_errors, list):
        recent_errors = cognitive_context.get("recent_errors")

    pain_points: list[str] = []
    source_signals: list[str] = []
    if isinstance(summary, dict) and summary:
        summary_line = _format_error_summary(summary)
        if summary_line:
            pain_points.append(summary_line)
            source_signals.append("error_summary")

    for item in recent_errors or []:
        if not isinstance(item, dict):
            continue
        preview = _strip(item.get("question_preview") or item.get("title"))
        subject = _strip(item.get("subject"))
        error_type = _strip(item.get("error_type"))
        detail = " / ".join(part for part in (subject, error_type) if part)
        pain_points.append(f"{preview or I18n.t('learning_state.pain_point_recent', locale='zh')}{f'（{detail}）' if detail else ''}")
        source_signals.append("recent_errors")
        if len(pain_points) >= MAX_PAIN_POINTS:
            break
    return pain_points[:MAX_PAIN_POINTS], list(dict.fromkeys(source_signals))


def _collect_recent_wins(user_context: dict[str, Any]) -> tuple[list[str], list[str]]:
    cognitive_context = _extract_cognitive_context(user_context)
    mastery_changes = user_context.get("recent_mastery_changes")
    if not isinstance(mastery_changes, list):
        mastery_changes = cognitive_context.get("recent_mastery_changes")
    if not isinstance(mastery_changes, list):
        profile_context = _extract_profile_context(user_context)
        mastery_changes = _as_dict(profile_context.get("knowledge_summary")).get("recent_mastery_changes")

    wins: list[str] = []
    source_signals: list[str] = []
    for item in mastery_changes or []:
        if not isinstance(item, dict):
            continue
        node_name = _strip(item.get("node_name") or item.get("node_id"))
        if not node_name:
            continue
        old_mastery = item.get("old_mastery")
        new_mastery = item.get("new_mastery")
        if old_mastery is None or new_mastery is None:
            wins.append(I18n.t("learning_state.win_progress", locale="zh", node=node_name))
        else:
            try:
                wins.append(
                    I18n.t("learning_state.win_mastery", locale="zh", node=node_name, old=float(old_mastery), new=float(new_mastery))
                )
            except Exception:
                wins.append(f"{node_name} {old_mastery} -> {new_mastery}")
        source_signals.append("recent_mastery_changes")
        if len(wins) >= MAX_WINS:
            break
    return wins[:MAX_WINS], list(dict.fromkeys(source_signals))


@dataclass
class LearningStateFragment:
    status: str
    available: bool
    summary: str
    signals: list[dict[str, str]] = field(default_factory=list)
    recent_pain_points: list[str] = field(default_factory=list)
    recent_wins: list[str] = field(default_factory=list)
    source_signals: list[str] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "available": self.available,
            "summary": self.summary,
            "signals": list(self.signals),
            "recent_pain_points": list(self.recent_pain_points),
            "recent_wins": list(self.recent_wins),
            "source_signals": list(self.source_signals),
            "budget": dict(self.budget),
        }


def build_learning_state_fragment(*, user_context: dict[str, Any] | None) -> LearningStateFragment:
    context = _as_dict(user_context)
    pain_points, pain_sources = _collect_recent_pain_points(context)
    recent_wins, win_sources = _collect_recent_wins(context)

    signals: list[dict[str, str]] = []
    truncated = len(pain_points) > MAX_PAIN_POINTS or len(recent_wins) > MAX_WINS
    for item in pain_points[:MAX_PAIN_POINTS]:
        compacted = _compact_text(item, limit=MAX_SIGNAL_TEXT_LENGTH)
        if compacted != _strip(item):
            truncated = True
        signals.append({"kind": "pain", "text": compacted})
    for item in recent_wins[:MAX_WINS]:
        compacted = _compact_text(item, limit=MAX_SIGNAL_TEXT_LENGTH)
        if compacted != _strip(item):
            truncated = True
        signals.append({"kind": "win", "text": compacted})

    source_signals = list(dict.fromkeys([*pain_sources, *win_sources]))
    summary = ""
    if signals:
        summary_parts: list[str] = []
        if pain_points:
            summary_parts.append(_compact_text(pain_points[0], limit=MAX_SIGNAL_TEXT_LENGTH))
        if recent_wins:
            summary_parts.append(_compact_text(recent_wins[0], limit=MAX_SIGNAL_TEXT_LENGTH))
        for item in pain_points[1:3]:
            summary_parts.append(_compact_text(item, limit=MAX_SIGNAL_TEXT_LENGTH))
        for item in recent_wins[1:3]:
            summary_parts.append(_compact_text(item, limit=MAX_SIGNAL_TEXT_LENGTH))
        summary_raw = "；".join(part for part in summary_parts if _strip(part))
        compact_summary = _compact_text(summary_raw, limit=MAX_SUMMARY_LENGTH)
        if compact_summary != summary_raw:
            truncated = True
        summary = compact_summary
    else:
        summary = I18n.t("learning_state.cold_start", locale="zh")

    budget = {
        "max_pain_points": MAX_PAIN_POINTS,
        "max_wins": MAX_WINS,
        "max_signal_text_length": MAX_SIGNAL_TEXT_LENGTH,
        "max_summary_length": MAX_SUMMARY_LENGTH,
        "source_count": len(source_signals),
        "truncated": truncated,
    }
    return LearningStateFragment(
        status="active" if signals else "cold_start",
        available=bool(signals),
        summary=summary,
        signals=signals,
        recent_pain_points=pain_points,
        recent_wins=recent_wins,
        source_signals=source_signals,
        budget=budget,
    )
