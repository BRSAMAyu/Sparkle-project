from dataclasses import dataclass


@dataclass(frozen=True)
class RagStrategy:
    name: str
    enable_hyde: bool
    enable_graph: bool
    enable_multi_hop: bool
    use_reranker: bool
    short_query_max_len: int
    trigger_keywords: list[str]
    document_context_similarity_threshold: float
    document_context_weak_evidence_margin: float
    document_context_keyword_overlap_weight: float
    mastery_boost_factor: float = 0.5
    retrieval_mode: str = "hybrid_rrf"


DEFAULT_STRATEGY = RagStrategy(
    name="default",
    enable_hyde=True,
    enable_graph=False,
    enable_multi_hop=False,
    use_reranker=True,
    short_query_max_len=10,
    trigger_keywords=[],
    document_context_similarity_threshold=0.72,
    document_context_weak_evidence_margin=0.08,
    document_context_keyword_overlap_weight=0.0,
)

STRATEGIES: dict[str, RagStrategy] = {
    "hybrid": RagStrategy(
        name="hybrid",
        enable_hyde=True,
        enable_graph=False,
        enable_multi_hop=False,
        use_reranker=False,
        short_query_max_len=10,
        trigger_keywords=[
            "算法",
            "公式",
            "定义",
            "证明",
            "algorithm",
            "formula",
            "definition",
            "theorem",
        ],
        document_context_similarity_threshold=0.72,
        document_context_weak_evidence_margin=0.08,
        document_context_keyword_overlap_weight=0.0,
    ),
    "analytical": RagStrategy(
        name="analytical",
        enable_hyde=True,
        enable_graph=True,
        enable_multi_hop=True,
        use_reranker=True,
        short_query_max_len=10,
        trigger_keywords=[
            "分析",
            "总结",
            "规划",
            "对比",
            "比较",
            "关系",
            "关联",
            "联系",
            "为什么",
            "如何",
            "compare",
            "comparison",
            "relationship",
            "relate",
            "related",
            "interact",
            "interaction",
            "how does",
        ],
        document_context_similarity_threshold=0.72,
        document_context_weak_evidence_margin=0.08,
        document_context_keyword_overlap_weight=0.0,
    ),
}

ANALYTICAL_STRATEGY = STRATEGIES["analytical"]
