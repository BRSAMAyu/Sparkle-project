"""Phase-0 evaluation-grade episode logger.

Vision mapping: P4-EVID-001..010 (Evaluation-Grade Episode Logging).

What this is for
----------------
The existing [app.signals.types.CausalTrace] captures the spine path
(events → signals → state → policy → directive → audit → receipt). For
P4 research-grade analysis we additionally need to capture:

  • context_signature   — a stable hash of the relevant signal set, so
                          two episodes with identical context can be
                          compared even if their trace_ids differ.
  • candidate_policies  — the set of policies the engine considered, so
                          counterfactual analysis can ask "what if it
                          had picked policy B instead?".
  • selection_reason    — why the chosen policy beat the alternatives,
                          stored as a structured rationale (not free text).
  • expected_outcome    — what the engine predicted at decision time.
  • actual_outcome      — what was actually measured later, written
                          asynchronously by the outcome recorder.

This module is intentionally additive — it does not modify CausalTrace
or any existing spine type. Episode rows are keyed by trace_id so a
downstream join is trivial.

The logger is a no-op until at least one writer registers a sink. The
default writer is [InMemoryEpisodeSink] for tests; production wires
[RedisEpisodeSink] from the bootstrap layer (Phase-0 leaves that wire
documented but unconnected, since the bootstrap files are part of the
protected registry surface).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CandidatePolicy:
    """One policy considered at decision time.

    `expected_outcome` is the engine's prior estimate (typically a
    StrategyBelief mean or a heuristic score). `was_selected` lets the
    log record say "we considered five, chose this one" without forcing
    the reader to re-run the policy engine.
    """

    policy_id: str
    expected_outcome: float
    was_selected: bool = False
    rationale: str = ""


@dataclass
class EvaluationEpisode:
    """One decision episode, joinable to CausalTrace via trace_id."""

    trace_id: str
    user_id: str
    context_signature: str
    candidate_policies: list[CandidatePolicy] = field(default_factory=list)
    selection_reason: str = ""
    selected_policy_id: str | None = None
    expected_outcome: float | None = None
    actual_outcome: float | None = None
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)
    # Anything the caller wants tagged for slicing later (e.g. "exam_rescue").
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "context_signature": self.context_signature,
            "candidate_policies": [asdict(p) for p in self.candidate_policies],
            "selection_reason": self.selection_reason,
            "selected_policy_id": self.selected_policy_id,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def compute_context_signature(signals: Iterable[Any]) -> str:
    """Deterministic hash over a (state_key, claim, scope) projection of signals.

    Stable under signal re-ordering — counterfactual analysis often slices
    by signature to find "same situation, different decision" pairs.
    """
    projection: list[tuple[str, str, str]] = []
    for sig in signals:
        state_key = str(getattr(sig, "state_key", "") or "")
        claim = str(getattr(sig, "claim", "") or "")
        scope = str(getattr(sig, "scope", "") or "")
        projection.append((state_key, claim, scope))
    projection.sort()
    payload = json.dumps(projection, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class EpisodeSink(Protocol):
    """Anything that can persist an EvaluationEpisode."""

    async def write(self, episode: EvaluationEpisode) -> None: ...

    async def update_outcome(self, trace_id: str, actual_outcome: float) -> None: ...


class InMemoryEpisodeSink:
    """Default sink used in tests and as a safe no-op.

    Holds the most recent N episodes in memory so test code can assert on
    them without standing up Redis. The cap matches CausalTraceStore's
    _MAX_USER_TRACES so behavior is comparable.
    """

    def __init__(self, capacity: int = 50) -> None:
        self._episodes: dict[str, EvaluationEpisode] = {}
        self._order: list[str] = []
        self._capacity = capacity

    async def write(self, episode: EvaluationEpisode) -> None:
        if episode.trace_id in self._episodes:
            self._order.remove(episode.trace_id)
        self._episodes[episode.trace_id] = episode
        self._order.append(episode.trace_id)
        if len(self._order) > self._capacity:
            stale = self._order.pop(0)
            self._episodes.pop(stale, None)

    async def update_outcome(self, trace_id: str, actual_outcome: float) -> None:
        ep = self._episodes.get(trace_id)
        if ep is None:
            return
        ep.actual_outcome = actual_outcome
        ep.updated_at = _utcnow()

    # ── test helpers ────────────────────────────────────────────────

    def latest(self) -> EvaluationEpisode | None:
        if not self._order:
            return None
        return self._episodes[self._order[-1]]

    def by_trace_id(self, trace_id: str) -> EvaluationEpisode | None:
        return self._episodes.get(trace_id)

    def all(self) -> list[EvaluationEpisode]:
        return [self._episodes[t] for t in self._order]


class EpisodeLogger:
    """Logs decision episodes; no-op until a sink is attached.

    Intentionally a thin façade so the spine doesn't need to know whether
    we're persisting to Redis, Postgres, or an in-process buffer.
    """

    def __init__(self, sink: EpisodeSink | None = None) -> None:
        self._sink = sink

    def attach_sink(self, sink: EpisodeSink) -> None:
        self._sink = sink

    async def log_decision(
        self,
        *,
        trace_id: str,
        user_id: str,
        signals: Iterable[Any],
        candidates: list[CandidatePolicy],
        selection_reason: str,
        expected_outcome: float | None = None,
        tags: list[str] | None = None,
    ) -> EvaluationEpisode:
        selected = next((c for c in candidates if c.was_selected), None)
        episode = EvaluationEpisode(
            trace_id=trace_id,
            user_id=user_id,
            context_signature=compute_context_signature(signals),
            candidate_policies=list(candidates),
            selection_reason=selection_reason,
            selected_policy_id=(selected.policy_id if selected else None),
            expected_outcome=expected_outcome
            if expected_outcome is not None
            else (selected.expected_outcome if selected else None),
            tags=list(tags or []),
        )
        if self._sink is not None:
            await self._sink.write(episode)
        return episode

    async def record_outcome(self, trace_id: str, actual_outcome: float) -> None:
        if self._sink is None:
            return
        await self._sink.update_outcome(trace_id, actual_outcome)


# Module-level singleton — Phase-0 starts with the in-memory sink so any
# spine code that begins emitting episodes immediately has somewhere to
# write. Production swaps this out via [attach_sink] from the bootstrap
# layer once the Redis writer is wired.
episode_logger = EpisodeLogger(sink=InMemoryEpisodeSink())
