from app.config_rag_strategy import DEFAULT_STRATEGY, STRATEGIES, RagStrategy


class RagRouter:
    def __init__(self):
        self.default_strategy = DEFAULT_STRATEGY
        self.strategies = STRATEGIES

    def select(self, query: str) -> RagStrategy:
        try:
            cleaned = (query or "").strip()
            if not cleaned:
                return self.default_strategy

            if len(cleaned) < self.default_strategy.short_query_max_len:
                return RagStrategy(
                    name="short_query",
                    enable_hyde=False,
                    enable_graph=False,
                    use_reranker=False,
                    short_query_max_len=self.default_strategy.short_query_max_len,
                    trigger_keywords=[],
                )

            for strategy in self.strategies.values():
                if any(keyword in cleaned for keyword in strategy.trigger_keywords):
                    return strategy
        except Exception:
            return self.default_strategy

        return self.default_strategy
