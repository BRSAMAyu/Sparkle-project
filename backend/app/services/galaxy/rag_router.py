from dataclasses import replace

from app.config import settings
from app.config_rag_strategy import DEFAULT_STRATEGY, STRATEGIES, RagStrategy


class RagRouter:
    KNOWLEDGE_ROUTE_INTENTS = frozenset({"knowledge", "knowledge_query"})

    def __init__(self):
        self.default_strategy = DEFAULT_STRATEGY
        self.strategies = STRATEGIES

    @classmethod
    def _normalize_route_intent(cls, route_intent: str | None) -> str:
        return str(route_intent or "").strip().lower()

    def select(self, query: str, route_intent: str | None = None) -> RagStrategy:
        strategy = self.default_strategy
        try:
            cleaned = (query or "").strip()
            if not cleaned:
                strategy = self.default_strategy
            elif len(cleaned) < self.default_strategy.short_query_max_len:
                strategy = RagStrategy(
                    name="short_query",
                    enable_hyde=self.default_strategy.enable_hyde,
                    enable_graph=False,
                    enable_multi_hop=False,
                    use_reranker=False,
                    short_query_max_len=self.default_strategy.short_query_max_len,
                    trigger_keywords=[],
                    document_context_similarity_threshold=(
                        self.default_strategy.document_context_similarity_threshold
                    ),
                    document_context_weak_evidence_margin=(
                        self.default_strategy.document_context_weak_evidence_margin
                    ),
                    document_context_keyword_overlap_weight=(
                        self.default_strategy.document_context_keyword_overlap_weight
                    ),
                    retrieval_mode=self.default_strategy.retrieval_mode,
                )
            else:
                for candidate in self.strategies.values():
                    if any(keyword in cleaned for keyword in candidate.trigger_keywords):
                        strategy = candidate
                        break
                else:
                    strategy = self.default_strategy
        except Exception:
            strategy = self.default_strategy

        normalized_intent = self._normalize_route_intent(route_intent)
        hyde_allowed = (
            bool(getattr(settings, "ENABLE_HYDE", False))
            and strategy.enable_hyde
            and normalized_intent in self.KNOWLEDGE_ROUTE_INTENTS
        )
        return replace(strategy, enable_hyde=hyde_allowed)
