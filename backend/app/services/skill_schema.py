from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal


ActivationConditionKind = Literal["intent_keywords", "tool_category", "time_of_day", "weekday_set"]

ALLOWED_CONDITION_KINDS: tuple[ActivationConditionKind, ...] = (
    "intent_keywords",
    "tool_category",
    "time_of_day",
    "weekday_set",
)


@dataclass(frozen=True)
class ActivationCondition:
    kind: ActivationConditionKind
    value: tuple[str, ...]


@dataclass(frozen=True)
class SkillDraft:
    name: str
    pattern_template: str
    activation_conditions: tuple[ActivationCondition, ...]
    examples: tuple[str, ...]


@dataclass(frozen=True)
class SkillSelectionContext:
    intent: str
    tool_category: str
    current_time: datetime


@dataclass(frozen=True)
class SkillActivationMatch:
    skill_id: str
    name: str
    activation_match_score: float


def normalize_name(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("Skill name is required")
    if len(value) > 40:
        raise ValueError("Skill name exceeds 40 chars")
    return value


def normalize_pattern_template(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("Skill pattern_template is required")
    if len(value.split()) > 200:
        raise ValueError("Skill pattern_template exceeds 200 tokens")
    return value


def normalize_examples(raw_examples: Any) -> tuple[str, ...]:
    if raw_examples is None:
        return ()
    if not isinstance(raw_examples, (list, tuple)):
        raise ValueError("Skill examples must be a list")
    normalized: list[str] = []
    for raw in raw_examples:
        text = str(raw or "").strip()
        if not text:
            continue
        if len(text.split()) > 100:
            raise ValueError("Skill example exceeds 100 tokens")
        normalized.append(text)
    if len(normalized) > 3:
        raise ValueError("Skill examples exceed max count of 3")
    return tuple(normalized)


def normalize_activation_conditions(raw_conditions: Any) -> tuple[ActivationCondition, ...]:
    if not isinstance(raw_conditions, (list, tuple)) or not raw_conditions:
        raise ValueError("Skill activation_conditions must be a non-empty list")

    normalized: list[ActivationCondition] = []
    for item in raw_conditions:
        if not isinstance(item, dict):
            raise ValueError("Skill activation condition must be an object")
        kind = str(item.get("kind") or "").strip()
        if kind not in ALLOWED_CONDITION_KINDS:
            raise ValueError(f"Unsupported activation condition kind: {kind}")

        raw_value = item.get("value")
        if isinstance(raw_value, str):
            values = [raw_value]
        elif isinstance(raw_value, (list, tuple)):
            values = [str(entry or "").strip() for entry in raw_value if str(entry or "").strip()]
        else:
            raise ValueError("Skill activation condition value must be a string or list")

        if not values:
            raise ValueError("Skill activation condition value may not be empty")
        normalized.append(ActivationCondition(kind=kind, value=tuple(values)))

    return tuple(normalized)


def conditions_to_json(conditions: tuple[ActivationCondition, ...]) -> list[dict[str, object]]:
    return [{"kind": item.kind, "value": list(item.value)} for item in conditions]


def draft_to_payload(draft: SkillDraft) -> dict[str, object]:
    return {
        "name": draft.name,
        "pattern_template": draft.pattern_template,
        "activation_conditions": conditions_to_json(draft.activation_conditions),
        "examples": list(draft.examples),
    }


def time_of_day_token(current_time: datetime) -> str:
    current = current_time.astimezone(UTC) if current_time.tzinfo else current_time.replace(tzinfo=UTC)
    hour = current.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def weekday_token(current_time: datetime) -> str:
    current = current_time.astimezone(UTC) if current_time.tzinfo else current_time.replace(tzinfo=UTC)
    return ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[current.weekday()]
