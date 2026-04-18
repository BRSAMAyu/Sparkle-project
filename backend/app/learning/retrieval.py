"""Retrieval seam for DistilledStrategy lookup."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from uuid import UUID

from app.aurora.schemas import DistilledStrategy
from app.learning.strategy_store import InMemoryDistilledStrategyStore, StrategyQuery


def retrieval_enabled() -> bool:
    return os.getenv("SPARKLE_WS7_RETRIEVAL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RetrievalQueryInput:
    text: str
    limit: int = 5


def _tokens(text: str) -> set[str]:
    return {token for token in re.split(r"[\s,.;:，。；：/|]+", text.casefold()) if token}


def retrieve_strategies(
    query: RetrievalQueryInput,
    store: InMemoryDistilledStrategyStore,
) -> list[DistilledStrategy]:
    """Return relevant strategies using simple overlap scoring."""

    if not retrieval_enabled():
        return []
    query_text = query.text.casefold()
    tokens = _tokens(query.text)
    if not tokens:
        return []
    candidates = store.list(StrategyQuery())
    scored: list[tuple[int, DistilledStrategy]] = []
    for strategy in candidates:
        haystack_text = f"{strategy.title} {strategy.description} {strategy.applicability_scope}".casefold()
        haystack_tokens = _tokens(haystack_text)
        overlap = len(tokens & haystack_tokens)
        overlap += sum(1 for token in tokens if token and token in haystack_text)
        if query_text and query_text in haystack_text:
            overlap += 1
        if overlap > 0:
            scored.append((overlap, strategy))
    scored.sort(key=lambda item: (item[0], item[1].evidence_strength, item[1].diversity_score), reverse=True)
    return [strategy for _, strategy in scored[: query.limit]]


def build_distilled_strategy_refs(
    query: RetrievalQueryInput,
    store: InMemoryDistilledStrategyStore,
) -> list[UUID]:
    """Return only strategy ids for SignalSnapshot integration."""

    return [strategy.id for strategy in retrieve_strategies(query, store)]
