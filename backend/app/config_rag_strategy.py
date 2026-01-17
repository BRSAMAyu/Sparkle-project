from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RagStrategy:
    name: str
    enable_hyde: bool
    enable_graph: bool
    use_reranker: bool
    short_query_max_len: int
    trigger_keywords: List[str]


DEFAULT_STRATEGY = RagStrategy(
    name="default",
    enable_hyde=False,
    enable_graph=False,
    use_reranker=True,
    short_query_max_len=10,
    trigger_keywords=[],
)

STRATEGIES: Dict[str, RagStrategy] = {
    "analytical": RagStrategy(
        name="analytical",
        enable_hyde=True,
        enable_graph=True,
        use_reranker=True,
        short_query_max_len=10,
        trigger_keywords=["分析", "总结", "规划", "对比", "为什么"],
    ),
}
