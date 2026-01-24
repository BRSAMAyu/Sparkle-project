from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class ConflictNote:
    type: str
    key: str
    reason: str
    winners: List[str]
    suppressed: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "key": self.key,
            "reason": self.reason,
            "winners": self.winners,
            "suppressed": self.suppressed,
        }


def _tokenize(text: str) -> List[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")]


def _similar_summary(a: str, b: str) -> bool:
    if not a or not b:
        return False
    a_norm = " ".join(_tokenize(a))
    b_norm = " ".join(_tokenize(b))
    if not a_norm or not b_norm:
        return False
    prefix_len = 40
    if a_norm[:prefix_len] == b_norm[:prefix_len]:
        return True
    a_tokens = set(a_norm.split())
    b_tokens = set(b_norm.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / float(min(len(a_tokens), len(b_tokens)))
    return overlap >= 0.8


def _goal_overlap(a: Optional[date], b: Optional[date]) -> bool:
    if a is None or b is None:
        return True
    return a == b


def _pick_preference_winner(records: List[MemoryPreference]) -> Tuple[MemoryPreference, str]:
    records_sorted = sorted(
        records,
        key=lambda item: (
            item.evidence_score or 0.0,
            item.updated_at or datetime.min,
            item.confidence or 0.0,
        ),
        reverse=True,
    )
    if len(records_sorted) == 1:
        return records_sorted[0], "single"

    top = records_sorted[0]
    second = records_sorted[1]
    if (top.evidence_score or 0.0) != (second.evidence_score or 0.0):
        return top, "evidence_score"
    if (top.updated_at or datetime.min) != (second.updated_at or datetime.min):
        return top, "updated_at"
    if (top.confidence or 0.0) != (second.confidence or 0.0):
        return top, "confidence"
    return top, "tie_break_latest"


class MemoryConflictResolver:
    def resolve_preferences(
        self,
        prefs: Dict[str, Any],
        pref_history: Iterable[MemoryPreference],
    ) -> Tuple[Dict[str, Any], List[MemoryPreference], List[Dict[str, Any]]]:
        history = list(pref_history)
        if not history:
            return prefs, [], []

        by_key: Dict[str, List[MemoryPreference]] = {}
        for record in history:
            by_key.setdefault(record.pref_key, []).append(record)

        resolved: Dict[str, Any] = {}
        winners: List[MemoryPreference] = []
        conflicts: List[ConflictNote] = []

        for key, records in by_key.items():
            winner, reason = _pick_preference_winner(records)
            winners.append(winner)
            resolved[key] = winner.pref_value

            if len(records) > 1:
                suppressed = [str(item.id) for item in records if item.id != winner.id]
                conflicts.append(
                    ConflictNote(
                        type="preference",
                        key=key,
                        reason=reason,
                        winners=[str(winner.id)],
                        suppressed=suppressed,
                    )
                )

        return resolved, winners, [note.to_dict() for note in conflicts]

    def resolve_goals(
        self,
        goals: Iterable[MemoryGoal],
    ) -> Tuple[List[MemoryGoal], List[Dict[str, Any]]]:
        items = list(goals)
        if len(items) <= 1:
            return items, []

        by_title: Dict[str, List[MemoryGoal]] = {}
        for goal in items:
            key = (goal.title or "").strip().lower()
            by_title.setdefault(key, []).append(goal)

        kept: List[MemoryGoal] = []
        suppressed_ids: set[str] = set()
        conflicts: List[ConflictNote] = []

        for key, group in by_title.items():
            if len(group) == 1:
                kept.append(group[0])
                continue

            overlapping = []
            for goal in group:
                if any(_goal_overlap(goal.target_date, other.target_date) for other in group if other != goal):
                    overlapping.append(goal)

            if len(overlapping) <= 1:
                kept.extend(group)
                continue

            overlapping.sort(
                key=lambda item: (
                    item.evidence_score or 0.0,
                    item.updated_at or datetime.min,
                ),
                reverse=True,
            )
            winner = overlapping[0]
            kept.append(winner)
            suppressed = [item for item in overlapping[1:]]
            suppressed_ids.update(str(item.id) for item in suppressed)
            conflicts.append(
                ConflictNote(
                    type="goal",
                    key=key,
                    reason="duplicate_title_overlap",
                    winners=[str(winner.id)],
                    suppressed=[str(item.id) for item in suppressed],
                )
            )

        kept = [goal for goal in kept if str(goal.id) not in suppressed_ids]
        return kept, [note.to_dict() for note in conflicts]

    def resolve_episodic(
        self,
        episodes: Iterable[EpisodicMemory],
    ) -> Tuple[List[EpisodicMemory], List[Dict[str, Any]]]:
        items = list(episodes)
        if len(items) <= 1:
            return items, []

        items.sort(
            key=lambda item: (
                item.evidence_score or 0.0,
                item.occurred_at or datetime.min,
            ),
            reverse=True,
        )
        kept: List[EpisodicMemory] = []
        conflicts: List[ConflictNote] = []

        for episode in items:
            match = None
            for existing in kept:
                if _similar_summary(episode.summary, existing.summary):
                    match = existing
                    break

            if match is None:
                kept.append(episode)
                continue

            conflicts.append(
                ConflictNote(
                    type="episodic",
                    key=str(match.id),
                    reason="similar_summary",
                    winners=[str(match.id)],
                    suppressed=[str(episode.id)],
                )
            )

        return kept, [note.to_dict() for note in conflicts]

    def resolve_cross_type(
        self,
        goals: Iterable[MemoryGoal],
        episodes: Iterable[EpisodicMemory],
    ) -> Tuple[List[MemoryGoal], List[EpisodicMemory], List[Dict[str, Any]]]:
        goals_list = list(goals)
        episodes_list = list(episodes)
        conflicts: List[ConflictNote] = []
        suppressed_episodic: set[str] = set()
        suppressed_goals: set[str] = set()

        for goal in goals_list:
            title = (goal.title or "").strip().lower()
            if not title:
                continue
            for episode in episodes_list:
                if episode.summary and title in episode.summary.lower():
                    goal_score = goal.evidence_score or 0.0
                    episode_score = episode.evidence_score or 0.0
                    if episode_score > goal_score:
                        suppressed_goals.add(str(goal.id))
                        winner = str(episode.id)
                        suppressed = str(goal.id)
                    else:
                        suppressed_episodic.add(str(episode.id))
                        winner = str(goal.id)
                        suppressed = str(episode.id)
                    conflicts.append(
                        ConflictNote(
                            type="cross_type",
                            key=title,
                            reason="goal_in_episodic",
                            winners=[winner],
                            suppressed=[suppressed],
                        )
                    )

        resolved_goals = [goal for goal in goals_list if str(goal.id) not in suppressed_goals]
        resolved_episodes = [
            episode for episode in episodes_list if str(episode.id) not in suppressed_episodic
        ]
        return resolved_goals, resolved_episodes, [note.to_dict() for note in conflicts]
