from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class ConflictNote:
    type: str
    key: str
    reason: str
    winners: list[str]
    suppressed: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "key": self.key,
            "reason": self.reason,
            "winners": self.winners,
            "suppressed": self.suppressed,
        }


def _tokenize(text: str) -> list[str]:
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


def _goal_overlap(a: date | None, b: date | None) -> bool:
    if a is None or b is None:
        return True
    return a == b


def _rank_preferences(records: list[MemoryPreference]) -> list[MemoryPreference]:
    """Legacy ranking axes: (evidence_score, updated_at, confidence)."""
    return sorted(
        records,
        key=lambda item: (
            item.evidence_score or 0.0,
            item.updated_at or datetime.min,
            item.confidence or 0.0,
        ),
        reverse=True,
    )


def _pick_preference_winner(records: list[MemoryPreference]) -> tuple[MemoryPreference, str]:
    """V3-FIX-35: the M-01/M-07 supersede chain owns winner selection.

    A row with ``replaced_by_id`` set is SUPERSEDED — its value was explicitly
    replaced by a newer chain head and must never compete for the win, no
    matter how its (evidence_score, updated_at, confidence) compare. Before
    this fix the ranking axes ran over the full version history, so
    (a) M-07's supersede-time ``updated_at`` bump on the OLD row and
    (b) an old row having accumulated more evidence refs both resurrected
    superseded values into ``pack.preferences`` (the M-09 "反杀" bug).

    Resolution law:
    - rows with ``replaced_by_id`` set are excluded from candidacy;
    - the winner is the best-ranked CHAIN HEAD (``replaced_by_id`` is None);
    - whenever superseded rows were suppressed, the reason is
      ``supersede_chain_head`` (the chain structure, not the ranking axes,
      decided the outcome — honest attribution for the conflicts face);
    - parallel unchained rows (no supersede ever recorded) keep the legacy
      ranking semantics unchanged;
    - a headless group (every row claims a successor — legacy anomaly with a
      dangling chain) falls back to ranking ALL rows rather than returning
      nothing: resolution must stay deterministic on damaged data.
    """
    superseded = [item for item in records if item.replaced_by_id is not None]
    heads = [item for item in records if item.replaced_by_id is None]
    if len(records) == 1:
        return records[0], "single"

    pool = heads if heads else records
    ranked = _rank_preferences(pool)
    winner = ranked[0]
    if superseded and heads:
        return winner, "supersede_chain_head"
    # No chain structure in play — legacy attribution over the ranking axes.
    # (ranked has >= 2 entries here: pool == records and len(records) >= 2.)
    second = ranked[1]
    if (winner.evidence_score or 0.0) != (second.evidence_score or 0.0):
        return winner, "evidence_score"
    if (winner.updated_at or datetime.min) != (second.updated_at or datetime.min):
        return winner, "updated_at"
    if (winner.confidence or 0.0) != (second.confidence or 0.0):
        return winner, "confidence"
    return winner, "tie_break_latest"


class MemoryConflictResolver:
    def resolve_preferences(
        self,
        prefs: dict[str, Any],
        pref_history: Iterable[MemoryPreference],
    ) -> tuple[dict[str, Any], list[MemoryPreference], list[dict[str, Any]]]:
        history = list(pref_history)
        if not history:
            return prefs, [], []

        by_key: dict[str, list[MemoryPreference]] = {}
        for record in history:
            by_key.setdefault(record.pref_key, []).append(record)

        resolved: dict[str, Any] = {}
        winners: list[MemoryPreference] = []
        conflicts: list[ConflictNote] = []

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
    ) -> tuple[list[MemoryGoal], list[dict[str, Any]]]:
        items = list(goals)
        if len(items) <= 1:
            return items, []

        by_title: dict[str, list[MemoryGoal]] = {}
        for goal in items:
            key = (goal.title or "").strip().lower()
            by_title.setdefault(key, []).append(goal)

        kept: list[MemoryGoal] = []
        suppressed_ids: set[str] = set()
        conflicts: list[ConflictNote] = []

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
            suppressed = list(overlapping[1:])
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
    ) -> tuple[list[EpisodicMemory], list[dict[str, Any]]]:
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
        kept: list[EpisodicMemory] = []
        conflicts: list[ConflictNote] = []

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
    ) -> tuple[list[MemoryGoal], list[EpisodicMemory], list[dict[str, Any]]]:
        goals_list = list(goals)
        episodes_list = list(episodes)
        conflicts: list[ConflictNote] = []
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
