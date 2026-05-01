from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.learning.persistent_bayesian_learner import PersistentBayesianLearner

SQAM_INFORMATION_DENSITY_THRESHOLD = 0.70
SQAM_STABILITY_THRESHOLD = 0.95
SQAM_DISCRIMINATIVE_POWER_THRESHOLD = 0.60
SQAM_SAFETY_MARGIN_THRESHOLD = 0.85
SQAM_MIN_TOTAL_OBSERVATIONS = 12
SQAM_MIN_OBSERVED_PAIRS = 4
SQAM_MIN_LABELED_SOURCE_STATES = 3
SQAM_HIGH_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class SQAMFixtureEntry:
    source: str
    target: str
    repeats: int
    success: bool
    was_helpful: bool | None = None
    user_satisfaction: int | None = None

    def effective_outcome(self) -> bool:
        if self.was_helpful is not None:
            return bool(self.was_helpful)
        if self.user_satisfaction is not None:
            return int(self.user_satisfaction) >= 4
        return bool(self.success)


@dataclass(frozen=True)
class SQAMTopDecision:
    source: str
    target: str
    probability: float
    effective_outcome: bool


@dataclass(frozen=True)
class SQAMScorecard:
    information_density: float
    stability: float
    discriminative_power: float
    safety_margin: float
    total_observations: int
    observed_pairs: int
    supported_pairs: int
    labeled_source_states: int
    false_confident_decisions: int
    high_confidence_decisions: int
    top_decisions: tuple[SQAMTopDecision, ...]

    def is_wire_ready(self) -> bool:
        return (
            self.information_density >= SQAM_INFORMATION_DENSITY_THRESHOLD
            and self.stability >= SQAM_STABILITY_THRESHOLD
            and self.discriminative_power >= SQAM_DISCRIMINATIVE_POWER_THRESHOLD
            and self.safety_margin >= SQAM_SAFETY_MARGIN_THRESHOLD
        )


class _MemoryRedis:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self._data[key] = value
        self._ttl[key] = ttl
        return True


def load_sqam_fixture(path: str | Path) -> tuple[SQAMFixtureEntry, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(SQAMFixtureEntry(**entry) for entry in payload["observations"])


async def run_sqam_fixture(entries: tuple[SQAMFixtureEntry, ...], user_id: str = "stage14-scale") -> SQAMScorecard:
    redis = _MemoryRedis()
    learner = PersistentBayesianLearner(redis, user_id=user_id)
    pair_entries: dict[tuple[str, str], SQAMFixtureEntry] = {}

    total_observations = 0
    for entry in entries:
        pair_entries[(entry.source, entry.target)] = entry
        total_observations += entry.repeats
        outcome = entry.effective_outcome()
        for _ in range(entry.repeats):
            await learner.update(entry.source, entry.target, outcome)

    await learner.drain_pending_saves()

    observed_pairs = len(pair_entries)
    if total_observations < SQAM_MIN_TOTAL_OBSERVATIONS or observed_pairs < SQAM_MIN_OBSERVED_PAIRS:
        raise ValueError("SQAM fixture is unmeasurable under Rule W minimums")

    supported_pairs: list[tuple[str, str]] = []
    for (source, target), entry in pair_entries.items():
        observation_count = entry.repeats
        if observation_count >= 3:
            supported_pairs.append((source, target))

    if not supported_pairs:
        raise ValueError("SQAM fixture has no supported pairs for stability")

    supported_pair_count = len(supported_pairs)
    information_density = supported_pair_count / observed_pairs

    max_reload_drift = 0.0
    reloaded = PersistentBayesianLearner(redis, user_id=user_id)
    for source, target in supported_pairs:
        before = await learner.get_probability(source, target)
        after = await reloaded.get_probability(source, target)
        max_reload_drift = max(max_reload_drift, abs(before - after))
    stability = 1.0 - max_reload_drift

    by_source: dict[str, list[SQAMFixtureEntry]] = {}
    for entry in pair_entries.values():
        by_source.setdefault(entry.source, []).append(entry)

    top_decisions: list[SQAMTopDecision] = []
    labeled_source_states = 0
    correct_top1_decisions = 0
    false_confident_decisions = 0
    high_confidence_decisions = 0

    for source, source_entries in by_source.items():
        if len(source_entries) < 2:
            continue

        labeled_entries = [entry for entry in source_entries if entry.was_helpful is not None or entry.user_satisfaction is not None or entry.success is not None]
        if not labeled_entries:
            continue

        labeled_source_states += 1
        ranked: list[tuple[SQAMFixtureEntry, float]] = []
        for entry in source_entries:
            probability = await reloaded.get_probability(entry.source, entry.target)
            ranked.append((entry, probability))
        ranked.sort(key=lambda item: item[1], reverse=True)

        top_entry, top_probability = ranked[0]
        effective_outcome = top_entry.effective_outcome()
        top_decisions.append(
            SQAMTopDecision(
                source=source,
                target=top_entry.target,
                probability=top_probability,
                effective_outcome=effective_outcome,
            )
        )

        if effective_outcome:
            correct_top1_decisions += 1
        if top_probability >= SQAM_HIGH_CONFIDENCE_THRESHOLD:
            high_confidence_decisions += 1
            if not effective_outcome:
                false_confident_decisions += 1

    if labeled_source_states < SQAM_MIN_LABELED_SOURCE_STATES:
        raise ValueError("SQAM fixture has too few labeled source states for DP1")
    if high_confidence_decisions == 0:
        raise ValueError("SQAM fixture has no high-confidence decisions for SM1")

    discriminative_power = correct_top1_decisions / labeled_source_states
    safety_margin = 1.0 - (false_confident_decisions / high_confidence_decisions)

    return SQAMScorecard(
        information_density=information_density,
        stability=stability,
        discriminative_power=discriminative_power,
        safety_margin=safety_margin,
        total_observations=total_observations,
        observed_pairs=observed_pairs,
        supported_pairs=supported_pair_count,
        labeled_source_states=labeled_source_states,
        false_confident_decisions=false_confident_decisions,
        high_confidence_decisions=high_confidence_decisions,
        top_decisions=tuple(top_decisions),
    )
