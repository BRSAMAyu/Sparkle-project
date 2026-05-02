"""
GraphRAG 检索器

结合向量检索和图检索，提供增强的知识检索能力
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from typing import Any

from loguru import logger
from redis.commands.search.query import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config_rag_strategy import DEFAULT_STRATEGY
from app.core.age_client import get_age_client
from app.core.agent_profiles import AgentRole, TaskType
from app.core.cache import cache_service
from app.core.cost_controller import is_rag_within_budget, record_rag_cost
from app.core.metrics import CACHE_HIT_COUNT, RAG_RETRIEVAL_LATENCY, RETRIEVAL_TIMEOUT_TOTAL
from app.core.redis_search_client import redis_search_client
from app.services.embedding_service import embedding_service
from app.services.galaxy.rag_router import RagRouter
from app.services.graphrag_trace_store import cache_trace
from app.services.group_file_service import GroupFileService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import get_configured_llm_service, llm_service
from app.services.rerank_service import rerank_service

_REDISEARCH_SPECIAL_CHARS = re.compile(r'([,\.<>{}\[\]"\'`:;!@#$%^&*()\-+=~|/\\])')
_QUERY_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass
class RetrievalTrace:
    """检索追踪信息 - 用于可视化"""

    trace_id: str
    query: str
    timestamp: datetime

    # 节点信息
    nodes_retrieved: list[dict[str, Any]]  # 被检索的节点列表
    node_sources: dict[str, str]  # node_id -> source_method (vector/graph/user_interest)

    # 关系信息
    relationships: list[dict[str, Any]]  # 图检索中的关系

    # 检索方法详情
    vector_search_results: list[dict[str, Any]]
    graph_search_results: list[dict[str, Any]]
    user_interest_nodes: list[str]

    # 性能指标
    timing: dict[str, float] = field(default_factory=dict)


@dataclass
class GraphRAGResult:
    """GraphRAG 检索结果"""

    query: str
    entities: list[str]
    vector_results: list[dict[str, Any]]
    graph_results: list[dict[str, Any]]
    fused_context: str
    metadata: dict[str, Any]

    # 新增：检索追踪信息
    trace: RetrievalTrace | None = None


@dataclass(frozen=True)
class FilteredChunk:
    """Post-retrieval chunk that is safe to inject."""

    raw: Any
    content: str
    source_file_id: str | None
    chunk_id: str | None
    filename: str | None
    chunk_index: int | None
    page_number: int | None
    relevance_score: float
    cosine_similarity: float
    keyword_overlap: float
    evidence_strength: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk(self) -> Any:
        return getattr(self.raw, "chunk", self.raw)

    @property
    def file_name(self) -> str:
        return self.filename or str(getattr(self.raw, "file_name", "") or "")

    @property
    def score(self) -> float:
        return self.relevance_score


@dataclass(frozen=True)
class FilteredRAGResult:
    """Post-retrieval RAG filter result."""

    chunks: list[FilteredChunk]
    total_retrieved: int
    total_passed: int
    fallback_triggered: bool


@dataclass(frozen=True)
class HyDEPreparation:
    """Resolved pre-retrieval vector query state."""

    vector_query: str
    source: str
    raw_similarity: float | None = None
    used_hyde: bool = False
    skip_reason: str | None = None


_FILTER_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)


def _clamp_relevance_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _coerce_relevance_score(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _tokenize_for_overlap(text: str) -> set[str]:
    tokens = set()
    for token in _FILTER_TOKEN_RE.findall((text or "").lower()):
        if len(token) >= 2 or "\u4e00" <= token <= "\u9fff":
            tokens.add(token)
    return tokens


def _keyword_overlap_score(query: str, content: str) -> float:
    query_tokens = _tokenize_for_overlap(query)
    if not query_tokens:
        return 0.0
    content_tokens = _tokenize_for_overlap(content)
    if not content_tokens:
        return 0.0
    return len(query_tokens & content_tokens) / len(query_tokens)


def _first_page_number(page_numbers: Any) -> int | None:
    if isinstance(page_numbers, str):
        stripped = page_numbers.strip()
        if stripped.startswith("["):
            try:
                page_numbers = json.loads(stripped)
            except json.JSONDecodeError:
                page_numbers = stripped
        else:
            page_numbers = stripped
    if isinstance(page_numbers, list) and page_numbers:
        try:
            return int(page_numbers[0])
        except (TypeError, ValueError):
            return None
    try:
        return int(page_numbers)
    except (TypeError, ValueError):
        return None


def _extract_chunk_metadata(item: Any) -> tuple[Any, str, dict[str, Any]]:
    if isinstance(item, dict):
        chunk = item.get("chunk") or item
        content = str(
            item.get("content") or item.get("text") or item.get("description") or getattr(chunk, "content", "") or ""
        )
        return chunk, content, item

    chunk = getattr(item, "chunk", item)
    content = str(
        getattr(chunk, "content", "") or getattr(item, "content", "") or getattr(item, "description", "") or ""
    )
    return chunk, content, {}


def _extract_retrieval_score(item: Any, metadata: dict[str, Any]) -> float:
    for source in (item, metadata):
        if isinstance(source, dict):
            for key in ("relevance_score", "similarity", "score"):
                if key in source:
                    score = _coerce_relevance_score(source.get(key))
                    if score is not None:
                        return score
        else:
            for key in ("relevance_score", "similarity", "score"):
                if hasattr(source, key):
                    score = _coerce_relevance_score(getattr(source, key))
                    if score is not None:
                        return score
    return 0.0


def _normalize_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _extract_source_node_id(item: Any, metadata: dict[str, Any] | None = None) -> uuid.UUID | None:
    """Resolve the galaxy node a retrieved chunk came from, if present."""
    metadata = metadata or {}
    sources = [metadata, item]
    chunk = item.get("chunk") if isinstance(item, dict) else getattr(item, "chunk", None)
    if chunk is not None:
        sources.append(chunk)

    for source in sources:
        if isinstance(source, dict):
            for key in ("source_node_id", "node_id", "knowledge_node_id"):
                node_id = _normalize_uuid(source.get(key))
                if node_id is not None:
                    return node_id
        elif source is not None:
            for key in ("source_node_id", "node_id", "knowledge_node_id"):
                node_id = _normalize_uuid(getattr(source, key, None))
                if node_id is not None:
                    return node_id

    source_type = str(item.get("source_type") if isinstance(item, dict) else getattr(item, "source_type", ""))
    if source_type == "node_description":
        parent_id = item.get("parent_id") if isinstance(item, dict) else getattr(item, "parent_id", None)
        return _normalize_uuid(parent_id)

    return None


def _build_filtered_chunk(
    *,
    item: Any,
    query: str,
    threshold: float,
    weak_evidence_margin: float,
    keyword_overlap_weight: float,
) -> FilteredChunk | None:
    chunk, content, metadata = _extract_chunk_metadata(item)
    if not content.strip():
        return None

    cosine_similarity = _extract_retrieval_score(item, metadata)
    keyword_overlap = _keyword_overlap_score(query, content) if keyword_overlap_weight > 0 else 0.0
    relevance_score = _clamp_relevance_score(cosine_similarity + keyword_overlap * keyword_overlap_weight)
    if relevance_score < threshold:
        return None

    page_numbers = metadata.get("page_numbers", getattr(chunk, "page_numbers", None))
    page_number = _first_page_number(page_numbers)
    if page_number is None:
        page_number = _first_page_number(metadata.get("page_number", getattr(chunk, "page_number", None)))

    source_file_id = getattr(chunk, "file_id", None) or metadata.get("source_file_id") or metadata.get("file_id")
    chunk_id = getattr(chunk, "id", None) or metadata.get("chunk_id") or metadata.get("id")
    filename = getattr(item, "file_name", None) or metadata.get("filename") or metadata.get("file_name")
    chunk_index = getattr(chunk, "chunk_index", None)
    if chunk_index is None:
        chunk_index = metadata.get("chunk_index")

    evidence_strength = (
        "weak_evidence" if relevance_score < threshold + max(0.0, weak_evidence_margin) else "strong_evidence"
    )
    citation_metadata = {
        "source_file_id": str(source_file_id) if source_file_id is not None else None,
        "chunk_id": str(chunk_id) if chunk_id is not None else None,
        "source_node_id": str(source_node_id) if (source_node_id := _extract_source_node_id(item, metadata)) else None,
        "filename": str(filename) if filename is not None else None,
        "chunk_index": chunk_index,
        "page_number": page_number,
        "section_title": metadata.get("section_title", getattr(chunk, "section_title", None)),
        "relevance_score": relevance_score,
        "cosine_similarity": cosine_similarity,
        "keyword_overlap": keyword_overlap,
        "evidence_strength": evidence_strength,
        "retrieved_for_concepts": list(metadata.get("retrieved_for_concepts") or []),
    }

    return FilteredChunk(
        raw=item,
        content=content,
        source_file_id=citation_metadata["source_file_id"],
        chunk_id=citation_metadata["chunk_id"],
        filename=citation_metadata["filename"],
        chunk_index=chunk_index,
        page_number=page_number,
        relevance_score=relevance_score,
        cosine_similarity=cosine_similarity,
        keyword_overlap=keyword_overlap,
        evidence_strength=evidence_strength,
        metadata=citation_metadata,
    )


def filter_retrieved_chunks(
    *,
    query: str,
    chunks: list[Any],
    threshold: float | None = None,
    weak_evidence_margin: float | None = None,
    keyword_overlap_weight: float | None = None,
) -> FilteredRAGResult:
    """
    Filter retrieved chunks before prompt injection.

    The retrieval layer already returns a cosine-derived score for each result.
    This pass applies the current-query threshold, optionally blends in keyword
    overlap, and preserves citation metadata for downstream rendering.
    """
    effective_threshold = _clamp_relevance_score(
        threshold
        if threshold is not None
        else getattr(
            settings,
            "DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD",
            DEFAULT_STRATEGY.document_context_similarity_threshold,
        )
    )
    effective_margin = max(
        0.0,
        float(
            weak_evidence_margin
            if weak_evidence_margin is not None
            else getattr(
                settings,
                "DOCUMENT_CONTEXT_WEAK_EVIDENCE_MARGIN",
                DEFAULT_STRATEGY.document_context_weak_evidence_margin,
            )
        ),
    )
    effective_keyword_weight = _clamp_relevance_score(
        keyword_overlap_weight
        if keyword_overlap_weight is not None
        else getattr(
            settings,
            "DOCUMENT_CONTEXT_KEYWORD_OVERLAP_WEIGHT",
            DEFAULT_STRATEGY.document_context_keyword_overlap_weight,
        )
    )

    filtered = [
        filtered_chunk
        for item in chunks
        if (
            filtered_chunk := _build_filtered_chunk(
                item=item,
                query=query,
                threshold=effective_threshold,
                weak_evidence_margin=effective_margin,
                keyword_overlap_weight=effective_keyword_weight,
            )
        )
        is not None
    ]
    filtered.sort(key=lambda chunk: chunk.relevance_score, reverse=True)

    return FilteredRAGResult(
        chunks=filtered,
        total_retrieved=len(chunks),
        total_passed=len(filtered),
        fallback_triggered=not filtered,
    )


def filter_graph_rag_result(
    result: GraphRAGResult,
    *,
    threshold: float | None = None,
    weak_evidence_margin: float | None = None,
    keyword_overlap_weight: float | None = None,
) -> FilteredRAGResult:
    """Filter vector chunks from GraphRAGResult while leaving graph context untouched."""
    return filter_retrieved_chunks(
        query=result.query,
        chunks=result.vector_results,
        threshold=threshold,
        weak_evidence_margin=weak_evidence_margin,
        keyword_overlap_weight=keyword_overlap_weight,
    )


NO_RELEVANT_STUDY_MATERIALS_SENTINEL = (
    "[Study Materials — Referenced Documents]\n\n"
    "No relevant study materials found for this query. Do not claim that uploaded notes, PDFs, slides, or other "
    "study materials support the answer; answer from general knowledge and be transparent if the user asks for "
    "document-specific citations."
)


def _trim_context_snippet(content: str, max_chars: int = 520) -> str:
    snippet = re.sub(r"\s+", " ", str(content or "")).strip()
    if len(snippet) <= max_chars:
        return snippet
    return snippet[: max_chars - 3].rstrip() + "..."


def _filtered_chunk_label(chunk: FilteredChunk) -> str:
    raw = chunk.raw if isinstance(chunk.raw, dict) else {}
    source_name = chunk.file_name or str(raw.get("parent_name") or raw.get("name") or "").strip() or "Study material"
    parts = [source_name]

    section_title = str(
        raw.get("section_title")
        or chunk.metadata.get("section_title")
        or getattr(chunk.chunk, "section_title", "")
        or ""
    ).strip()
    if section_title:
        parts.append(section_title)
    if chunk.page_number is not None:
        parts.append(f"Page {chunk.page_number}")
    elif chunk.chunk_index is not None:
        parts.append(f"Chunk {chunk.chunk_index}")

    return " · ".join(parts)


def format_filtered_study_materials_context(chunks: list[FilteredChunk]) -> str:
    """Render CRAG-filtered chunks as a stable prompt block with citations."""
    if not chunks:
        return NO_RELEVANT_STUDY_MATERIALS_SENTINEL

    lines = ["[Study Materials — Referenced Documents]"]
    for index, chunk in enumerate(chunks, start=1):
        snippet = _trim_context_snippet(chunk.content)
        evidence_tag = " weak_evidence" if chunk.evidence_strength == "weak_evidence" else ""
        lines.extend(
            [
                "",
                f"[{index}] {_filtered_chunk_label(chunk)}{evidence_tag}",
                f'"{snippet}"',
                f"(relevance: {chunk.relevance_score:.2f})",
            ]
        )
    return "\n".join(lines)


def _format_multi_hop_chunk_label(chunk: dict[str, Any]) -> str:
    source_name = str(chunk.get("source_name") or "Study material").strip()
    parts = [source_name]
    section_title = str(chunk.get("section_title") or "").strip()
    if section_title:
        parts.append(section_title)

    page_number = chunk.get("page_number")
    chunk_index = chunk.get("chunk_index")
    if page_number is not None:
        parts.append(f"Page {page_number}")
    elif chunk_index is not None:
        parts.append(f"Chunk {chunk_index}")
    return " · ".join(parts)


def _format_multi_hop_connection(connection: dict[str, Any]) -> str:
    edges = list(connection.get("edges") or [])
    if not edges:
        return str(connection.get("summary") or "").strip()

    segments = []
    for edge in edges:
        source_name = str(edge.get("source_name") or "").strip()
        target_name = str(edge.get("target_name") or "").strip()
        relation_type = str(edge.get("relation_type") or "related").strip().lower()
        if not source_name or not target_name:
            continue
        segments.append(f"{source_name} —[{relation_type}]→ {target_name}")
    return " · ".join(segments)


def format_graph_rag_document_context(result: GraphRAGResult, chunks: list[FilteredChunk]) -> str:
    """Render structured multi-hop synthesis blocks when available."""
    multi_hop = result.metadata.get("multi_hop") if isinstance(result.metadata, dict) else None
    prebuilt = str(multi_hop.get("structured_context") or "").strip() if isinstance(multi_hop, dict) else ""
    if prebuilt:
        return prebuilt
    concept_blocks = list(multi_hop.get("concept_blocks") or []) if isinstance(multi_hop, dict) else []
    if not concept_blocks or not any(list(block.get("chunks") or []) for block in concept_blocks):
        if chunks:
            return format_filtered_study_materials_context(chunks)
        if result.vector_results:
            lines = ["[Knowledge Results]"]
            for index, item in enumerate(result.vector_results[:4], start=1):
                name = str(item.get("name") or f"Result {index}").strip()
                description = _trim_context_snippet(str(item.get("description") or ""))
                lines.append("")
                lines.append(f"[{index}] {name}")
                if description:
                    lines.append(f"\"{description}\"")
            return "\n".join(lines)
        return format_filtered_study_materials_context(chunks)

    lines = ["[Study Materials — Multi-Hop Synthesis]"]
    for index, concept_block in enumerate(concept_blocks, start=1):
        concept = str(concept_block.get("concept") or f"Concept {index}").strip()
        chunk_items = list(concept_block.get("chunks") or [])
        if not chunk_items:
            continue

        lines.append("")
        lines.append(f"[Concept {index}: {concept}]")
        for chunk in chunk_items:
            evidence_tag = " weak_evidence" if chunk.get("evidence_strength") == "weak_evidence" else ""
            lines.append(f"{_format_multi_hop_chunk_label(chunk)}{evidence_tag}")
            lines.append(f"\"{_trim_context_snippet(str(chunk.get('snippet') or ''))}\"")
            try:
                lines.append(f"(relevance: {float(chunk.get('relevance_score') or 0.0):.2f})")
            except (TypeError, ValueError):
                pass

    connections = list(multi_hop.get("graph_connections") or []) if isinstance(multi_hop, dict) else []
    if connections:
        lines.append("")
        lines.append("[Knowledge Graph Connections]")
        for connection in connections:
            from_concept = str(connection.get("from_concept") or "").strip()
            to_concept = str(connection.get("to_concept") or "").strip()
            connection_title = f"{from_concept} ↔ {to_concept}".strip(" ↔")
            if connection_title:
                lines.append(connection_title)
            formatted_connection = _format_multi_hop_connection(connection)
            if formatted_connection:
                lines.append(formatted_connection)

    return "\n".join(lines)


class GraphRAGRetriever:
    """GraphRAG 检索器"""

    MULTI_HOP_RELATION_TYPES = {"prerequisite", "related", "application", "composition", "evolution"}
    MULTI_HOP_TRIGGER_KEYWORDS = {
        "compare",
        "comparison",
        "relationship",
        "relate",
        "related",
        "interact",
        "interaction",
        "connect",
        "connection",
        "between",
        "vs",
        "关系",
        "关联",
        "联系",
        "对比",
        "比较",
    }
    MULTI_HOP_QUERY_PATTERNS = (
        r"\bhow does\b.+\brelate to\b",
        r"\bhow do\b.+\brelate to\b",
        r"\brelationship\b",
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\binteract(?:s|ion)?\b",
        r"\bconnect(?:s|ion)?\b",
        r"\bbetween\b.+\band\b",
        r"\bvs\.?\b",
        r"关系",
        r"关联",
        r"联系",
        r"对比",
        r"比较",
        r"如何.*(关联|联系|影响|作用)",
    )

    def __init__(self, knowledge_service: KnowledgeService):
        self.age_client = get_age_client()
        self.knowledge_service = knowledge_service
        self.max_depth = 2
        self.min_strength = 0.3

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def _build_cache_key(
        self,
        query: str,
        user_id: str,
        knowledge_version: str | None,
        route_intent: str | None = None,
        feedback_version: str | None = None,
        group_scope: list[str] | None = None,
    ) -> str:
        normalized_query = self._normalize_query(query)
        normalized_intent = self._normalize_query(str(route_intent or "chat"))
        parts = [normalized_query, user_id, normalized_intent, "v4-multi-hop-hybrid-rrf-hyde-intent"]
        if knowledge_version:
            parts.append(knowledge_version)
        if feedback_version:
            parts.append(f"feedback:{feedback_version}")
        if group_scope:
            parts.append(f"group:{','.join(sorted(str(item) for item in group_scope))}")
        else:
            parts.append("group:personal")
        raw = ":".join(parts)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"graphrag:cache:{digest}"

    @staticmethod
    def _dedupe_ordered(items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            cleaned = " ".join(str(item or "").split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            ordered.append(cleaned)
        return ordered

    def _is_multi_hop_query(self, query: str) -> bool:
        normalized = self._normalize_query(query)
        if not normalized:
            return False
        if any(keyword in normalized for keyword in self.MULTI_HOP_TRIGGER_KEYWORDS):
            return True
        return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in self.MULTI_HOP_QUERY_PATTERNS)

    async def extract_concepts_for_synthesis(self, query: str, max_concepts: int = 3) -> list[str]:
        """Extract 2-3 synthesis concepts for multi-hop retrieval."""
        system_prompt = """You extract study concepts for multi-hop retrieval.
Return ONLY a valid JSON array of 2 or 3 concise concept strings.
Prefer explicit technical concepts, not full questions or verbs.

Example:
Query: "how does the OS scheduler relate to process states?"
Return: ["OS scheduler", "process states"]"""
        user_prompt = f"""Extract the 2 or 3 key concepts from this study question: {query}

Return ONLY a JSON array of concept strings."""
        try:
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            response = await llm_service.chat(messages, temperature=0.0)
            cleaned_response = str(response or "").strip()
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response.split("```")[1].strip()
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:].strip()

            parsed = json.loads(cleaned_response)
            if isinstance(parsed, list):
                concepts = self._dedupe_ordered([str(item) for item in parsed])
                if len(concepts) >= 2:
                    return concepts[:max_concepts]
        except Exception as exc:
            logger.warning(f"Multi-hop concept extraction failed: {exc}")

        entity_fallback = self._dedupe_ordered(await self.extract_entities(query))
        if len(entity_fallback) >= 2:
            return entity_fallback[:max_concepts]
        return self._heuristic_concept_split(query, max_concepts=max_concepts)

    def _heuristic_concept_split(self, query: str, max_concepts: int = 3) -> list[str]:
        normalized = re.sub(r"\s+", " ", str(query or "")).strip()
        normalized = normalized.rstrip("?.，,")
        split_patterns = [
            r"\brelate(?:s|d)? to\b",
            r"\brelated to\b",
            r"\bcompare(?:d)? with\b",
            r"\bcompare\b",
            r"\binteract(?:s|ion)? with\b",
            r"\bbetween\b",
            r"\band\b",
            r"\bvs\.?\b",
            r"与",
            r"和",
            r"以及",
            r"对比",
            r"比较",
            r"关系",
            r"关联",
            r"联系",
        ]
        parts = [normalized]
        for pattern in split_patterns:
            if len(parts) >= 2:
                break
            parts = [segment.rstrip("?.，,:：").strip() for segment in re.split(pattern, normalized, flags=re.IGNORECASE) if segment.strip()]

        cleaned_parts = []
        for part in parts:
            part = re.sub(r"^(how does|how do|what is the relationship between|explain|how)\s+", "", part, flags=re.IGNORECASE)
            part = re.sub(r"^(请解释|请说明|解释|说明|如何理解)\s*", "", part)
            if part:
                cleaned_parts.append(part)
        concepts = self._dedupe_ordered(cleaned_parts)
        return concepts[:max_concepts]

    async def _build_multi_hop_metadata(
        self,
        *,
        query: str,
        user_id: str,
        concepts: list[str],
        concept_results: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        concept_blocks: list[dict[str, Any]] = []
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            user_uuid = None

        for concept in concepts:
            raw_results = list(concept_results.get(concept) or [])
            filtered = filter_retrieved_chunks(query=concept, chunks=raw_results)
            chunk_payloads: list[dict[str, Any]] = []
            source_node_ids: list[str] = []
            for filtered_chunk in filtered.chunks[:2]:
                source_node_id = str(filtered_chunk.metadata.get("source_node_id") or "").strip()
                if source_node_id:
                    source_node_ids.append(source_node_id)
                chunk_payloads.append(
                    {
                        "source_name": filtered_chunk.file_name or "Study material",
                        "section_title": filtered_chunk.metadata.get("section_title"),
                        "page_number": filtered_chunk.page_number,
                        "chunk_index": filtered_chunk.chunk_index,
                        "snippet": filtered_chunk.content,
                        "relevance_score": filtered_chunk.relevance_score,
                        "evidence_strength": filtered_chunk.evidence_strength,
                    }
                )

            if not source_node_ids and user_uuid is not None:
                try:
                    node = await self.knowledge_service.find_node_by_name(user_uuid, concept)
                except Exception:
                    node = None
                if node is not None:
                    source_node_ids.append(str(node.id))

            concept_blocks.append(
                {
                    "concept": concept,
                    "chunks": chunk_payloads,
                    "source_node_ids": self._dedupe_ordered(source_node_ids),
                }
            )

        graph_connections: list[dict[str, Any]] = []
        galaxy_service = getattr(self.knowledge_service, "galaxy_service", None)
        if galaxy_service is not None:
            for left_block, right_block in combinations(concept_blocks, 2):
                left_ids = list(left_block.get("source_node_ids") or [])
                right_ids = list(right_block.get("source_node_ids") or [])
                if not left_ids or not right_ids:
                    continue
                try:
                    bridge = await galaxy_service.find_relation_bridge(
                        left_ids,
                        right_ids,
                        relation_types=self.MULTI_HOP_RELATION_TYPES,
                    )
                except Exception as exc:
                    logger.warning(f"Multi-hop graph linking failed: {exc}")
                    bridge = None
                if bridge is None or not isinstance(bridge, dict):
                    continue
                graph_connections.append(
                    {
                        **bridge,
                        "from_concept": left_block.get("concept"),
                        "to_concept": right_block.get("concept"),
                    }
                )

        return {
            "enabled": True,
            "query": query,
            "concepts": concepts,
            "concept_blocks": concept_blocks,
            "graph_connections": graph_connections,
        }

    def _merge_multi_hop_vector_results(
        self,
        *,
        base_results: list[dict[str, Any]],
        concept_results: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        ordered_candidates: list[tuple[str | None, dict[str, Any]]] = []
        for concept, results in concept_results.items():
            for result in results:
                ordered_candidates.append((concept, result))
        for result in base_results:
            ordered_candidates.append((None, result))

        merged: dict[str, dict[str, Any]] = {}
        ordered_keys: list[str] = []
        for concept, result in ordered_candidates:
            item = dict(result)
            item_id = str(item.get("id") or item.get("parent_id") or "")
            if not item_id:
                continue
            if item_id not in merged:
                merged[item_id] = item
                merged[item_id]["retrieved_for_concepts"] = []
                ordered_keys.append(item_id)

            concept_list = merged[item_id].setdefault("retrieved_for_concepts", [])
            if concept and concept not in concept_list:
                concept_list.append(concept)

            existing_similarity = _extract_retrieval_score(merged[item_id], merged[item_id])
            incoming_similarity = _extract_retrieval_score(item, item)
            if incoming_similarity > existing_similarity:
                preserved_concepts = list(merged[item_id].get("retrieved_for_concepts") or [])
                merged[item_id] = item
                merged[item_id]["retrieved_for_concepts"] = preserved_concepts

        return [merged[item_id] for item_id in ordered_keys]

    async def _retrieve_multi_hop(
        self,
        query: str,
        user_id: str,
        depth: int,
        allowed_group_ids: set[str] | None = None,
        *,
        strategy: Any | None = None,
        trace: RetrievalTrace | None = None,
    ) -> tuple[
        list[str],
        list[dict[str, Any]],
        list[dict[str, Any]],
        str,
        list[dict[str, Any]],
        list[str],
        dict[str, float],
        list[dict[str, Any]],
        dict[str, Any],
        HyDEPreparation,
    ]:
        import time

        timing: dict[str, float] = {}
        start_time = time.time()

        hyde_prep = await self._prepare_vector_query(query=query, user_id=user_id, strategy=strategy, trace=trace)
        vector_query = hyde_prep.vector_query

        t0 = time.time()
        concepts_task = self.extract_concepts_for_synthesis(query)
        entities_task = self.extract_entities(query)
        base_vector_task = self._vector_search_scoped(
            vector_query,
            top_k=5,
            user_id=user_id,
            allowed_group_ids=allowed_group_ids,
        )
        interests_task = self.get_user_interests(user_id)
        concepts, entities, base_vector_results, user_interests = await asyncio.gather(
            concepts_task,
            entities_task,
            base_vector_task,
            interests_task,
        )
        timing["parallel_stage"] = time.time() - t0

        concept_list = self._dedupe_ordered(concepts or entities)[:3]
        if len(concept_list) < 2:
            concept_list = self._heuristic_concept_split(query, max_concepts=3)
        if len(concept_list) < 2:
            concept_list = self._dedupe_ordered((concepts or []) + (entities or []))[:3]

        t0 = time.time()
        concept_search_results = await asyncio.gather(
            *(
                self._vector_search_scoped(
                    concept,
                    top_k=3,
                    user_id=user_id,
                    allowed_group_ids=allowed_group_ids,
                )
                for concept in concept_list
            )
        ) if concept_list else []
        timing["concept_vector_search"] = time.time() - t0
        concept_results = {
            concept: list(results)
            for concept, results in zip(concept_list, concept_search_results, strict=False)
        }

        t0 = time.time()
        graph_results, relationships = await self.graph_search(concept_list or entities, depth)
        timing["graph_search"] = time.time() - t0

        t0 = time.time()
        merged_vector_results = self._merge_multi_hop_vector_results(
            base_results=base_vector_results,
            concept_results=concept_results,
        )
        vector_results = await self.rerank_by_mastery(
            merged_vector_results,
            user_id,
            db=getattr(self.knowledge_service, "db", None),
        )
        timing["mastery_rerank"] = time.time() - t0

        t0 = time.time()
        multi_hop_metadata = await self._build_multi_hop_metadata(
            query=query,
            user_id=user_id,
            concepts=concept_list,
            concept_results=concept_results,
        )
        timing["multi_hop_linking"] = time.time() - t0

        t0 = time.time()
        fused_context, unique_results = self.fuse_results(vector_results, graph_results, user_interests)
        timing["fusion"] = time.time() - t0
        timing["total"] = time.time() - start_time

        return (
            entities,
            vector_results,
            graph_results,
            fused_context,
            unique_results,
            user_interests,
            timing,
            relationships,
            multi_hop_metadata,
            hyde_prep,
        )

    @staticmethod
    def _escape_redisearch_token(token: str) -> str:
        return _REDISEARCH_SPECIAL_CHARS.sub(r"\\\1", token)

    def _build_bm25_query(self, query: str) -> str:
        """Build an OR-style BM25 query over indexed chunk text fields."""
        tokens = [
            self._escape_redisearch_token(token.lower())
            for token in _QUERY_TOKEN_RE.findall(query or "")
            if token.strip()
        ]
        if not tokens:
            return "*"

        clauses: list[str] = []
        for token in tokens[:12]:
            clauses.append(token)
            if len(token) >= 4:
                clauses.append(f"%{token}%")

        term_query = "|".join(dict.fromkeys(clauses))
        return f"(@content:({term_query}) | @keywords:({term_query}) | @parent_name:({term_query}))"

    @staticmethod
    def _redis_doc_field(doc: Any, field: str, default: Any = "") -> Any:
        if isinstance(doc, dict):
            return doc.get(field, default)
        return getattr(doc, field, default)

    def _format_redis_chunk_result(
        self,
        doc: Any,
        *,
        source_method: str,
        rank: int,
        rrf_score: float | None = None,
    ) -> dict[str, Any]:
        chunk_id = str(self._redis_doc_field(doc, "id", "") or getattr(doc, "id", ""))
        parent_id = str(self._redis_doc_field(doc, "parent_id", "") or "")
        parent_name = str(self._redis_doc_field(doc, "parent_name", "") or "Knowledge Chunk")
        content = str(self._redis_doc_field(doc, "content", "") or "")

        vector_score_raw = self._redis_doc_field(doc, "vector_score", None)
        similarity = rrf_score or 0.0
        if vector_score_raw is not None:
            try:
                similarity = max(0.0, 1.0 - float(vector_score_raw))
            except (TypeError, ValueError):
                pass

        result = {
            "id": chunk_id or parent_id,
            "name": parent_name,
            "description": content,
            "similarity": similarity,
            "source": "vector",
            "retrieval_method": "hybrid_rrf",
            "retrieval_sources": [source_method],
            "rank": rank,
        }
        for field in (
            "source_type",
            "source_node_id",
            "node_id",
            "file_id",
            "chunk_id",
            "user_id",
            "group_id",
            "shared_by_user_id",
            "trust_level",
            "document_scope",
            "chunk_index",
            "page_numbers",
            "section_title",
            "quality_score",
        ):
            value = self._redis_doc_field(doc, field, None)
            if value is not None and value != "":
                result[field] = value
        if result.get("source_type") == "node_description" and not result.get("source_node_id"):
            result["source_node_id"] = str(result.get("node_id") or parent_id)
        if result.get("source_type") == "document_chunk" and parent_name:
            result["file_name"] = parent_name
        if parent_id:
            result["parent_id"] = parent_id
        if rrf_score is not None:
            result["rrf_score"] = rrf_score
        if vector_score_raw is not None:
            result["vector_score"] = vector_score_raw
        return result

    def _rrf_fuse(
        self,
        ranked_lists: list[list[dict[str, Any]]],
        *,
        top_k: int,
        k: int = 60,
    ) -> list[dict[str, Any]]:
        scores: dict[str, float] = {}
        items: dict[str, dict[str, Any]] = {}

        for ranked in ranked_lists:
            for rank, item in enumerate(ranked):
                item_id = str(item.get("id") or item.get("parent_id") or "")
                if not item_id:
                    continue
                if item_id not in items:
                    items[item_id] = dict(item)
                    items[item_id]["retrieval_sources"] = list(item.get("retrieval_sources") or [])
                else:
                    existing_sources = set(items[item_id].get("retrieval_sources") or [])
                    existing_sources.update(item.get("retrieval_sources") or [])
                    items[item_id]["retrieval_sources"] = sorted(existing_sources)

                scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)

        fused: list[dict[str, Any]] = []
        for rank, (item_id, score) in enumerate(
            sorted(scores.items(), key=lambda pair: pair[1], reverse=True), start=1
        ):
            item = items[item_id]
            item["rrf_score"] = score
            normalized_score = min(1.0, score * (k + 1))
            item["similarity"] = normalized_score
            item["relevance_score"] = normalized_score
            item["rank"] = rank
            fused.append(item)
            if len(fused) >= top_k:
                break

        return fused

    async def _rerank_hybrid_results(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not getattr(settings, "ENABLE_GRAPHRAG_RERANKER", False) or not candidates:
            return candidates[:top_k]

        try:
            timeout = getattr(settings, "RERANK_TIMEOUT_SECONDS", 2.5)
            reranked = await asyncio.wait_for(
                rerank_service.rerank(
                    query,
                    candidates,
                    top_k=top_k,
                    instruct="Prioritize chunks that directly answer technical study questions, exact definitions, formulas, and named algorithms.",
                ),
                timeout=timeout,
            )
            return reranked[:top_k]
        except TimeoutError:
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="rerank").inc()
            logger.warning("GraphRAG hybrid rerank timed out; returning RRF order")
            return candidates[:top_k]
        except Exception as e:
            logger.warning(f"GraphRAG hybrid rerank failed; returning RRF order: {e}")
            return candidates[:top_k]

    async def rerank_by_mastery(
        self,
        results: list[dict[str, Any]],
        user_id: str,
        *,
        boost_factor: float | None = None,
        db: Any | None = None,
    ) -> list[dict[str, Any]]:
        if not results:
            return []

        effective_boost = float(
            boost_factor
            if boost_factor is not None
            else getattr(settings, "MASTERY_BOOST_FACTOR", DEFAULT_STRATEGY.mastery_boost_factor)
        )
        linked_node_ids = [node_id for item in results if (node_id := _extract_source_node_id(item, item)) is not None]
        mastery_scores: dict[uuid.UUID, float] = {}
        if linked_node_ids:
            try:
                galaxy_service = getattr(self.knowledge_service, "galaxy_service", None)
                if galaxy_service is not None:
                    mastery_scores = await galaxy_service.get_user_node_mastery_scores(
                        user_id=user_id,
                        node_ids=list(dict.fromkeys(linked_node_ids)),
                    )
            except Exception as exc:
                logger.warning(f"GraphRAG mastery rerank lookup failed: {exc}")

        # Batch-fetch document quality multipliers if feedback loop is enabled
        quality_multipliers: dict[str, float] = {}
        feedback_loop_enabled = getattr(settings, "ENABLE_DOCUMENT_FEEDBACK_LOOP", True)
        if feedback_loop_enabled and isinstance(db, AsyncSession):
            try:
                from app.services.document_service import document_service

                file_ids: list[str] = list(
                    dict.fromkeys(
                        str(item.get("file_id") or item.get("source_file_id") or "")
                        for item in results
                        if (item.get("file_id") or item.get("source_file_id"))
                    )
                )
                for fid in file_ids:
                    quality_multipliers[fid] = await document_service.get_document_quality_multiplier(db, fid)
            except Exception as exc:
                logger.warning(f"GraphRAG quality multiplier batch fetch failed: {exc}")

        ranked: list[tuple[int, dict[str, Any]]] = []
        for index, item in enumerate(results):
            ranked_item = dict(item)
            source_node_id = _extract_source_node_id(ranked_item, ranked_item)
            retrieval_score = _extract_retrieval_score(ranked_item, ranked_item)
            mastery_score: float | None = None
            if source_node_id is None:
                mastery_gap = 0.5
            else:
                mastery_score = max(0.0, min(100.0, float(mastery_scores.get(source_node_id, 0.0))))
                mastery_gap = 1.0 - (mastery_score / 100.0)

            boosted_rank_score = retrieval_score * (1.0 + (mastery_gap * effective_boost))

            # Apply document quality multiplier (only when feedback loop is active and DB was provided)
            if feedback_loop_enabled and quality_multipliers:
                fid = str(ranked_item.get("file_id") or ranked_item.get("source_file_id") or "")
                quality_multiplier = quality_multipliers.get(fid, 1.0)
                boosted_rank_score = boosted_rank_score * quality_multiplier
                ranked_item["document_quality_adjustment"] = quality_multiplier - 1.0
                ranked_item["quality_multiplier"] = quality_multiplier

            ranked_item["retrieval_score"] = retrieval_score
            ranked_item["mastery_gap"] = mastery_gap
            ranked_item["mastery_boost_factor"] = effective_boost
            ranked_item["boosted_rank_score"] = boosted_rank_score
            if source_node_id is not None:
                ranked_item["source_node_id"] = str(source_node_id)
                ranked_item["mastery_score"] = mastery_score
            ranked.append((index, ranked_item))

        ranked.sort(key=lambda pair: (pair[1]["boosted_rank_score"], -pair[0]), reverse=True)
        for rank, (_, item) in enumerate(ranked, start=1):
            item["mastery_rank"] = rank
        return [item for _, item in ranked]

    async def _get_cached_result(self, cache_key: str) -> GraphRAGResult | None:
        cached = await cache_service.get(cache_key)
        if not cached:
            return None
        try:
            return GraphRAGResult(
                query=cached["query"],
                entities=cached.get("entities", []),
                vector_results=cached.get("vector_results", []),
                graph_results=cached.get("graph_results", []),
                fused_context=cached.get("fused_context", ""),
                metadata=cached.get("metadata", {}),
                trace=None,
            )
        except Exception:
            return None

    async def _store_cache(self, cache_key: str, result: GraphRAGResult) -> None:
        payload = {
            "query": result.query,
            "entities": result.entities,
            "vector_results": result.vector_results,
            "graph_results": result.graph_results,
            "fused_context": result.fused_context,
            "metadata": result.metadata,
        }
        await cache_service.set(cache_key, payload, ttl=settings.GRAPHRAG_CACHE_TTL_SECONDS)

    # ------------------------------------------------------------------ #
    # HyDE — Hypothetical Document Embeddings                            #
    # ------------------------------------------------------------------ #

    async def _probe_query_chunk_similarity(
        self,
        query: str,
        *,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> float | None:
        """Check whether the raw query already lands close to a document chunk."""
        try:
            query_embedding = await embedding_service.get_embedding(query, text_type="query")
        except Exception as exc:
            logger.debug(f"HyDE precision probe embedding failed: {exc}")
            return None

        try:
            dense_res = await redis_search_client.hybrid_search(text_query="*", vector=query_embedding, top_k=top_k)
        except Exception as exc:
            logger.debug(f"HyDE precision probe search failed: {exc}")
            return None

        for doc in list(getattr(dense_res, "docs", []) or []):
            if not self._redis_doc_matches_user(doc, user_id):
                continue
            if str(self._redis_doc_field(doc, "source_type", "") or "") != "document_chunk":
                continue
            vector_score_raw = self._redis_doc_field(doc, "vector_score", None)
            if vector_score_raw is None:
                continue
            try:
                return max(0.0, min(1.0, 1.0 - float(vector_score_raw)))
            except (TypeError, ValueError):
                continue
        return None

    async def _expand_query_with_hyde(
        self,
        query: str,
        subject_hint: str | None = None,
        timeout_s: float | None = None,
        trace: RetrievalTrace | None = None,
    ) -> str:
        """
        HyDE pre-retrieval expansion: generate a short hypothetical textbook
        passage that would answer *query*, then return it as the embedding
        query.  Falls back to the original query on any error or timeout.
        """
        import time

        effective_timeout = timeout_s if timeout_s is not None else getattr(settings, "HYDE_TIMEOUT_SECONDS", 2.0)
        max_tokens = getattr(settings, "HYDE_MAX_TOKENS", 80)

        hint_clause = f"\nSubject hint: {subject_hint}" if subject_hint else ""
        messages = [
            {
                "role": "system",
                "content": (
                    "Write a concise textbook-style passage that would directly answer a student's study question. "
                    "Use precise technical vocabulary and concrete concepts. No preamble."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {query}{hint_clause}\n"
                    "Return 2-4 sentences as if from an ideal textbook passage."
                ),
            },
        ]

        t0 = time.time()
        try:
            hyde_llm = await get_configured_llm_service(AgentRole.RETRIEVAL, TaskType.QUICK_QUERY)
            passage = await asyncio.wait_for(
                hyde_llm.chat(messages, max_tokens=max_tokens, temperature=0.2),
                timeout=effective_timeout,
            )
            elapsed = time.time() - t0
            passage = (passage or "").strip()
            if not passage:
                logger.debug("HyDE expansion returned empty passage; using original query")
                return query
            logger.debug(
                f"HyDE expansion ({elapsed:.2f}s): '{query[:60]}' → '{passage[:80]}'"
            )
            if trace is not None:
                trace.timing["hyde_expansion"] = elapsed
            return passage
        except TimeoutError:
            elapsed = time.time() - t0
            logger.debug(f"HyDE expansion timed out after {elapsed:.2f}s; using original query")
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="hyde").inc()
            return query
        except Exception as exc:
            elapsed = time.time() - t0
            logger.debug(f"HyDE expansion failed after {elapsed:.2f}s: {exc}; using original query")
            return query

    async def _prepare_vector_query(
        self,
        *,
        query: str,
        user_id: str,
        strategy: RagRouter | Any | None = None,
        trace: RetrievalTrace | None = None,
    ) -> HyDEPreparation:
        if not getattr(strategy, "enable_hyde", False):
            return HyDEPreparation(vector_query=query, source="raw", skip_reason="hyde_disabled")

        probe_started = asyncio.get_running_loop().time()
        raw_similarity = await self._probe_query_chunk_similarity(query, user_id=user_id)
        probe_elapsed = asyncio.get_running_loop().time() - probe_started
        if trace is not None:
            trace.timing["hyde_probe"] = probe_elapsed

        skip_threshold = float(getattr(settings, "HYDE_SKIP_THRESHOLD", 0.85) or 0.85)
        if raw_similarity is not None and raw_similarity >= skip_threshold:
            logger.debug(
                "Skipping HyDE for precise knowledge query: similarity={:.3f}, threshold={:.3f}",
                raw_similarity,
                skip_threshold,
            )
            return HyDEPreparation(
                vector_query=query,
                source="raw",
                raw_similarity=raw_similarity,
                skip_reason="already_precise",
            )

        expanded_query = await self._expand_query_with_hyde(
            query,
            timeout_s=getattr(settings, "HYDE_TIMEOUT_SECONDS", 2.0),
            trace=trace,
        )
        used_hyde = bool(expanded_query.strip() and expanded_query.strip() != query.strip())
        return HyDEPreparation(
            vector_query=expanded_query if used_hyde else query,
            source="hyde" if used_hyde else "raw",
            raw_similarity=raw_similarity,
            used_hyde=used_hyde,
            skip_reason=None if used_hyde else "hyde_fallback",
        )

    async def _retrieve_fastpath(
        self,
        query: str,
        user_id: str,
        depth: int,
        allowed_group_ids: set[str] | None = None,
        *,
        strategy: Any | None = None,
        trace: RetrievalTrace | None = None,
    ) -> tuple[
        list[str],
        list[dict[str, Any]],
        list[dict[str, Any]],
        str,
        list[dict[str, Any]],
        list[str],
        dict[str, float],
        list[dict[str, Any]],
        HyDEPreparation,
    ]:
        import time

        timing: dict[str, float] = {}
        start_time = time.time()

        hyde_prep = await self._prepare_vector_query(query=query, user_id=user_id, strategy=strategy, trace=trace)
        vector_query = hyde_prep.vector_query

        timeout = settings.GRAPHRAG_FASTPATH_TIMEOUT_SECONDS
        try:
            t0 = time.time()
            entities_task = self.extract_entities(query)
            vector_task = self._vector_search_scoped(
                vector_query,
                top_k=5,
                user_id=user_id,
                allowed_group_ids=allowed_group_ids,
            )
            interests_task = self.get_user_interests(user_id)
            entities, vector_results, user_interests = await asyncio.wait_for(
                asyncio.gather(entities_task, vector_task, interests_task), timeout=timeout
            )
            parallel_duration = time.time() - t0
            timing["parallel_stage"] = parallel_duration
            timing["entity_extraction"] = parallel_duration
            timing["vector_search"] = parallel_duration
            timing["user_interests"] = parallel_duration
        except TimeoutError:
            logger.warning("GraphRAG fastpath timeout in parallel stage, falling back to sequential")
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="parallel").inc()
            return await self._retrieve_sequential(
                query,
                user_id,
                depth,
                allowed_group_ids=allowed_group_ids,
                strategy=strategy,
                trace=trace,
            )

        t0 = time.time()
        try:
            graph_results, relationships = await asyncio.wait_for(self.graph_search(entities, depth), timeout=timeout)
        except TimeoutError:
            logger.warning("GraphRAG fastpath graph search timeout")
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="graph_search").inc()
            graph_results, relationships = [], []
        timing["graph_search"] = time.time() - t0

        t0 = time.time()
        vector_results = await self.rerank_by_mastery(
            vector_results,
            user_id,
            db=getattr(self.knowledge_service, "db", None),
        )
        timing["mastery_rerank"] = time.time() - t0

        t0 = time.time()
        fused_context, unique_results = self.fuse_results(vector_results, graph_results, user_interests)
        timing["fusion"] = time.time() - t0
        timing["total"] = time.time() - start_time

        return (
            entities,
            vector_results,
            graph_results,
            fused_context,
            unique_results,
            user_interests,
            timing,
            relationships,
            hyde_prep,
        )

    async def _retrieve_sequential(
        self,
        query: str,
        user_id: str,
        depth: int,
        allowed_group_ids: set[str] | None = None,
        *,
        strategy: Any | None = None,
        trace: RetrievalTrace | None = None,
    ) -> tuple[
        list[str],
        list[dict[str, Any]],
        list[dict[str, Any]],
        str,
        list[dict[str, Any]],
        list[str],
        dict[str, float],
        list[dict[str, Any]],
        HyDEPreparation,
    ]:
        import time

        timing: dict[str, float] = {}
        start_time = time.time()

        hyde_prep = await self._prepare_vector_query(query=query, user_id=user_id, strategy=strategy, trace=trace)
        vector_query = hyde_prep.vector_query

        # 1. 实体识别
        t0 = time.time()
        entities = await self.extract_entities(query)
        timing["entity_extraction"] = time.time() - t0

        # 2. 向量检索 (语义相似)
        t0 = time.time()
        vector_results = await self._vector_search_scoped(
            vector_query,
            top_k=5,
            user_id=user_id,
            allowed_group_ids=allowed_group_ids,
        )
        timing["vector_search"] = time.time() - t0

        t0 = time.time()
        vector_results = await self.rerank_by_mastery(
            vector_results,
            user_id,
            db=getattr(self.knowledge_service, "db", None),
        )
        timing["mastery_rerank"] = time.time() - t0

        # 3. 图检索 (结构关联)
        t0 = time.time()
        graph_results, relationships = await self.graph_search(entities, depth)
        timing["graph_search"] = time.time() - t0

        # 4. 用户个性化
        t0 = time.time()
        user_interests = await self.get_user_interests(user_id)
        timing["user_interests"] = time.time() - t0

        # 5. 融合与去重
        t0 = time.time()
        fused_context, unique_results = self.fuse_results(vector_results, graph_results, user_interests)
        timing["fusion"] = time.time() - t0
        timing["total"] = time.time() - start_time

        return (
            entities,
            vector_results,
            graph_results,
            fused_context,
            unique_results,
            user_interests,
            timing,
            relationships,
            hyde_prep,
        )

    async def extract_entities(self, query: str) -> list[str]:
        """
        使用 LLM 从查询中提取实体

        Args:
            query: 用户查询

        Returns:
            实体名称列表
        """
        system_prompt = """You are a knowledge entity extractor. Extract knowledge entity names from user queries.
Return ONLY a valid JSON array of strings. No markdown, no explanation, no extra text.

Extract only explicit knowledge points, concepts, or domain names.

Examples:
Query: "学习量子计算需要什么前置知识"
Return: ["量子计算"]

Query: "Python 和 Java 的区别"
Return: ["Python", "Java"]"""

        user_prompt = f"""Extract knowledge entities from this query: {query}

Return ONLY a JSON array of entity names."""

        try:
            # llm_service.chat() expects messages parameter
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            response = await llm_service.chat(messages)

            # 清理响应
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1].strip()
            if response.startswith("json"):
                response = response[4:].strip()

            entities = json.loads(response)
            logger.debug(f"提取实体: {entities}")
            return entities
        except Exception as e:
            logger.warning(f"实体提取失败: {e}")
            # 降级：简单关键词提取
            return await self._simple_extract(query)

    async def _simple_extract(self, query: str) -> list[str]:
        """简单关键词提取（降级）"""
        # 这里可以使用简单的 NLP 或关键词提取
        # 暂时返回空，由后续处理
        return []

    @staticmethod
    def _redis_doc_matches_user(
        doc: Any,
        user_id: str | None,
        allowed_group_ids: set[str] | None = None,
    ) -> bool:
        source_type = str(GraphRAGRetriever._redis_doc_field(doc, "source_type", "") or "")
        if source_type != "document_chunk" or not user_id:
            return True
        lifecycle_status = str(GraphRAGRetriever._redis_doc_field(doc, "lifecycle_status", "active") or "active")
        if lifecycle_status != "active":
            return False
        doc_group_id = str(GraphRAGRetriever._redis_doc_field(doc, "group_id", "") or "").strip()
        if doc_group_id:
            return doc_group_id in (allowed_group_ids or set())
        doc_user_id = str(GraphRAGRetriever._redis_doc_field(doc, "user_id", "") or "")
        return not doc_user_id or doc_user_id == str(user_id)

    async def _redis_dense_search(self, query: str, top_k: int, user_id: str | None = None):
        try:
            query_embedding = await embedding_service.get_embedding(query, text_type="query")
        except Exception as e:
            logger.warning(f"GraphRAG dense embedding failed; using BM25-only Redis search if available: {e}")
            return None

        return await redis_search_client.hybrid_search(
            text_query="*",
            vector=query_embedding,
            top_k=top_k,
        )

    async def _redis_hybrid_search(
        self,
        query: str,
        top_k: int,
        user_id: str | None = None,
        allowed_group_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        candidate_limit = max(top_k * 4, top_k)
        timeout = getattr(settings, "REDIS_HYBRID_TIMEOUT_SECONDS", 2.0)

        bm25_q = (
            Query(self._build_bm25_query(query))
            .paging(0, candidate_limit)
            .return_fields(
                "id",
                "parent_id",
                "content",
                "parent_name",
                "importance",
                "source_type",
                "source_node_id",
                "node_id",
                "file_id",
                "chunk_id",
                "user_id",
                "group_id",
                "shared_by_user_id",
                "trust_level",
                "document_scope",
                "chunk_index",
                "page_numbers",
                "section_title",
                "quality_score",
                "lifecycle_status",
            )
            .with_scores()
            .dialect(2)
        )

        dense_task = self._redis_dense_search(query, candidate_limit, user_id=user_id)
        bm25_task = redis_search_client.search(bm25_q)

        try:
            dense_res, bm25_res = await asyncio.gather(
                asyncio.wait_for(dense_task, timeout=timeout),
                asyncio.wait_for(bm25_task, timeout=timeout),
            )
        except TimeoutError:
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="redis_hybrid").inc()
            logger.warning("GraphRAG Redis hybrid search timed out")
            return []
        except Exception as e:
            logger.warning(f"GraphRAG Redis hybrid search failed: {e}")
            return []

        dense_docs = [
            doc
            for doc in list(getattr(dense_res, "docs", []) or [])
            if self._redis_doc_matches_user(doc, user_id, allowed_group_ids)
        ]
        bm25_docs = [
            doc
            for doc in list(getattr(bm25_res, "docs", []) or [])
            if self._redis_doc_matches_user(doc, user_id, allowed_group_ids)
        ]

        if not dense_docs and not bm25_docs:
            return []

        dense_results = [
            self._format_redis_chunk_result(doc, source_method="dense", rank=rank)
            for rank, doc in enumerate(dense_docs, start=1)
        ]
        bm25_results = [
            self._format_redis_chunk_result(doc, source_method="bm25", rank=rank)
            for rank, doc in enumerate(bm25_docs, start=1)
        ]

        fused = self._rrf_fuse([dense_results, bm25_results], top_k=max(top_k * 2, top_k))
        return await self._rerank_hybrid_results(query, fused, top_k)

    async def _vector_search_scoped(
        self,
        query: str,
        *,
        top_k: int,
        user_id: str | None = None,
        allowed_group_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"top_k": top_k, "user_id": user_id}
        if allowed_group_ids:
            kwargs["allowed_group_ids"] = allowed_group_ids
        return await self.vector_search(query, **kwargs)

    async def vector_search(
        self,
        query: str,
        top_k: int = 5,
        user_id: str | None = None,
        allowed_group_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        混合检索：Redis BM25 + dense vector search, fused by RRF.

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果
        """
        redis_results = await self._redis_hybrid_search(
            query,
            top_k,
            user_id=user_id,
            allowed_group_ids=allowed_group_ids,
        )
        if redis_results:
            logger.debug(f"GraphRAG Redis hybrid 检索: {len(redis_results)} 条结果")
            return redis_results

        try:
            # Fallback: keep the previous DB vector behavior when Redis Search is unavailable.
            results = await self.knowledge_service.semantic_search(query=query, top_k=top_k, min_similarity=0.3)

            # 格式化结果
            formatted = []
            for result in results:
                formatted.append(
                    {
                        "id": str(result.id),
                        "name": result.name,
                        "description": result.description,
                        "similarity": result.similarity,
                        "source": "vector",
                        "source_node_id": str(result.id),
                        "retrieval_method": "pgvector_fallback",
                        "retrieval_sources": ["dense"],
                    }
                )

            logger.debug(f"向量检索: {len(formatted)} 条结果")
            return formatted

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    async def graph_search(
        self, entities: list[str], depth: int = 2
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        图检索（结构关联）

        Args:
            entities: 实体列表
            depth: 搜索深度

        Returns:
            (节点检索结果, 关系列表)
        """
        if not entities:
            return [], []

        results = []
        relationships = []  # 新增：收集关系信息
        seen_result_ids: set[str] = set()
        seen_relationship_keys: set[tuple[str | None, str | None, str | None]] = set()

        for entity in entities:
            try:
                # AGE 对复杂路径列表过滤支持较弱，这里优先使用稳定的一跳关联查询。
                cypher = """
                MATCH (start:KnowledgeNode {name: $entity})
                -[rel]-(related:KnowledgeNode)
                WHERE toFloat(rel.strength) > $min_strength
                RETURN {
                    start_id: start.id,
                    start_name: start.name,
                    id: related.id,
                    name: related.name,
                    description: related.description,
                    relation_type: type(rel),
                    strength: toFloat(rel.strength),
                    sector: related.sector
                } as result
                ORDER BY toFloat(rel.strength) DESC
                LIMIT 10
                """

                result = await self.age_client.execute_cypher(
                    cypher, {"entity": entity, "min_strength": self.min_strength}
                )

                # 添加元数据并收集关系
                for item in result:
                    item_id = str(item.get("id") or "")
                    if item_id and item_id in seen_result_ids:
                        continue
                    if item_id:
                        seen_result_ids.add(item_id)
                    item["source"] = "graph"
                    item["query_entity"] = entity
                    results.append(item)

                    # 收集关系信息（用于可视化）
                    relationship_key = (
                        item.get("start_id"),
                        item.get("id"),
                        item.get("relation_type"),
                    )
                    if relationship_key in seen_relationship_keys:
                        continue
                    seen_relationship_keys.add(relationship_key)
                    relationships.append(
                        {
                            "from_id": item.get("start_id"),
                            "from_name": item.get("start_name", entity),
                            "to_id": item.get("id"),
                            "to_name": item.get("name"),
                            "relation_type": item.get("relation_type"),
                            "strength": item.get("strength"),
                        }
                    )

            except Exception as e:
                logger.warning(f"图检索失败 for {entity}: {e}")

        logger.debug(f"图检索: {len(results)} 条结果, {len(relationships)} 个关系")
        return results, relationships

    async def get_user_interests(self, user_id: str) -> list[str]:
        """
        获取用户兴趣领域

        Args:
            user_id: 用户ID

        Returns:
            用户感兴趣的知识点名称
        """
        try:
            cypher = """
            MATCH (u:User {id: $user_id})-[r]->(k:KnowledgeNode)
            WHERE type(r) IN ["INTERESTED_IN", "STUDIED"]
              AND toFloat(r.strength) > 0.3
            RETURN {name: k.name, strength: toFloat(r.strength)} as result
            ORDER BY toFloat(r.strength) DESC
            LIMIT 20
            """

            results = await self.age_client.execute_cypher(cypher, {"user_id": user_id})

            interests: list[str] = []
            seen: set[str] = set()
            for item in results:
                name = str(item.get("name") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                interests.append(name)
                if len(interests) >= 10:
                    break

            return interests

        except Exception as e:
            logger.warning(f"获取用户兴趣失败: {e}")
            return []

    def fuse_results(
        self, vector_results: list[dict], graph_results: list[dict], user_interests: list[str]
    ) -> tuple[str, list[dict]]:
        """
        融合向量和图结果

        Args:
            vector_results: 向量检索结果
            graph_results: 图检索结果
            user_interests: 用户兴趣

        Returns:
            (融合后的文本上下文, 去重后的结果列表)
        """
        # 基于 ID 去重，优先保留图结果（包含关系信息）
        seen = set()
        fused = []

        # 先添加图结果（包含关系信息）
        for item in graph_results:
            item_id = item.get("id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                fused.append(item)

        # 再添加向量结果
        for item in vector_results:
            item_id = item.get("id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                fused.append(item)

        # 构建上下文文本
        context_parts = []

        for item in fused:
            name = item.get("name", "")
            desc = item.get("description", "")
            source = item.get("source", "")
            relation = item.get("relation_type", "")
            strength = item.get("strength", "")

            part = f"## {name}"
            if relation:
                part += f" ({relation})"
            if strength:
                part += f" [强度: {strength}]"

            part += f"\n{desc}"
            if source == "graph":
                part += "\n[来自图谱]"

            context_parts.append(part)

        # 如果有用户兴趣，添加个性化提示
        if user_interests:
            context_parts.append(f"\n## 用户兴趣领域\n{', '.join(user_interests[:5])}")

        return "\n\n".join(context_parts), fused

    async def _resolve_group_scope(
        self,
        *,
        user_id: str,
        include_group_documents: bool,
        group_ids: list[str] | None,
    ) -> list[str]:
        if not include_group_documents:
            return []
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return []
        try:
            accessible = await GroupFileService.list_accessible_group_ids(
                self.knowledge_service.db,
                user_uuid,
                requested_group_ids=group_ids,
            )
        except Exception as exc:
            logger.warning(f"Failed to resolve GraphRAG group scope for user {user_id}: {exc}")
            return []
        return [str(group_id) for group_id in accessible]

    async def retrieve(
        self,
        query: str,
        user_id: str,
        depth: int = 2,
        enable_trace: bool = True,
        route_intent: str | None = None,
        include_group_documents: bool = False,
        group_ids: list[str] | None = None,
    ) -> GraphRAGResult:
        """
        GraphRAG 主检索流程

        Args:
            query: 用户查询
            user_id: 用户ID
            depth: 图搜索深度
            enable_trace: 是否启用检索追踪（用于可视化）

        Returns:
            GraphRAGResult
        """
        logger.info(f"GraphRAG 检索: query='{query}', user='{user_id}'")

        if not await is_rag_within_budget():
            logger.warning(f"RAG budget exhausted, returning empty result for user {user_id}")
            return GraphRAGResult(
                answer="",
                sources=[],
                trace=None,
                metadata={"budget_exhausted": True},
            )

        strategy = RagRouter().select(query, route_intent=route_intent)
        resolved_group_scope = await self._resolve_group_scope(
            user_id=user_id,
            include_group_documents=include_group_documents,
            group_ids=group_ids,
        )
        allowed_group_ids = set(resolved_group_scope)
        cache_key = None
        if settings.ENABLE_GRAPHRAG_FASTPATH:
            knowledge_version = None
            feedback_version = None
            try:
                knowledge_version = await self.knowledge_service.get_knowledge_version()
            except Exception as e:
                logger.warning(f"Failed to resolve knowledge version for cache key: {e}")
            if getattr(settings, "ENABLE_DOCUMENT_FEEDBACK_LOOP", True):
                try:
                    feedback_version = str(await cache_service.get("document_feedback:cache_version") or "0")
                except Exception as exc:
                    logger.warning(f"Failed to resolve document feedback cache version: {exc}")
                    feedback_version = "0"
            cache_key = self._build_cache_key(
                query,
                user_id,
                knowledge_version=knowledge_version,
                route_intent=route_intent,
                feedback_version=feedback_version,
                group_scope=resolved_group_scope,
            )
            cached = await self._get_cached_result(cache_key)
            if cached:
                CACHE_HIT_COUNT.labels(cache_name="graphrag", result="hit").inc()
                return cached
            CACHE_HIT_COUNT.labels(cache_name="graphrag", result="miss").inc()

        trace = (
            RetrievalTrace(
                trace_id=str(uuid.uuid4()),
                query=query,
                timestamp=datetime.now(),
                nodes_retrieved=[],
                node_sources={},
                relationships=[],
                vector_search_results=[],
                graph_search_results=[],
                user_interest_nodes=[],
                timing={},
            )
            if enable_trace
            else None
        )

        multi_hop_enabled = self._is_multi_hop_query(query)

        if multi_hop_enabled:
            (
                entities,
                vector_results,
                graph_results,
                fused_context,
                unique_results,
                user_interests,
                timing,
                relationships,
                multi_hop_metadata,
                hyde_prep,
            ) = await self._retrieve_multi_hop(
                query,
                user_id,
                depth,
                allowed_group_ids=allowed_group_ids,
                strategy=strategy,
                trace=trace,
            )
        elif settings.ENABLE_GRAPHRAG_FASTPATH:
            (
                entities,
                vector_results,
                graph_results,
                fused_context,
                unique_results,
                user_interests,
                timing,
                relationships,
                hyde_prep,
            ) = await self._retrieve_fastpath(
                query,
                user_id,
                depth,
                allowed_group_ids=allowed_group_ids,
                strategy=strategy,
                trace=trace,
            )
            multi_hop_metadata = None
        else:
            (
                entities,
                vector_results,
                graph_results,
                fused_context,
                unique_results,
                user_interests,
                timing,
                relationships,
                hyde_prep,
            ) = await self._retrieve_sequential(
                query,
                user_id,
                depth,
                allowed_group_ids=allowed_group_ids,
                strategy=strategy,
                trace=trace,
            )
            multi_hop_metadata = None

        if multi_hop_metadata:
            structured_context = format_graph_rag_document_context(
                GraphRAGResult(
                    query=query,
                    entities=entities,
                    vector_results=vector_results,
                    graph_results=graph_results,
                    fused_context=fused_context,
                    metadata={"multi_hop": multi_hop_metadata},
                ),
                [],
            )
            multi_hop_metadata["structured_context"] = structured_context
            fused_context = structured_context

        # 6. 构建元数据
        metadata = {
            "vector_count": len(vector_results),
            "graph_count": len(graph_results),
            "fusion_count": len(unique_results),
            "entities": entities,
            "user_interests": user_interests,
            "query": query,
            "mastery_boost_factor": getattr(settings, "MASTERY_BOOST_FACTOR", DEFAULT_STRATEGY.mastery_boost_factor),
            "route_intent": route_intent,
            "rag_strategy": strategy.name,
            "hyde_enabled": strategy.enable_hyde,
            "hyde_used": hyde_prep.used_hyde,
            "hyde_query_source": hyde_prep.source,
            "hyde_skip_reason": hyde_prep.skip_reason,
            "raw_query_chunk_similarity": hyde_prep.raw_similarity,
            "timing": timing,
            "multi_hop": multi_hop_metadata,
            "group_scope": resolved_group_scope,
        }

        # 7. 构建检索追踪信息（用于前端可视化）
        if enable_trace:
            # 构建节点来源映射
            node_sources = {}
            for node in vector_results:
                node_sources[node["id"]] = "vector"
            for node in graph_results:
                node_sources[node["id"]] = "graph"

            assert trace is not None
            trace.nodes_retrieved = unique_results
            trace.node_sources = node_sources
            trace.relationships = relationships
            trace.vector_search_results = vector_results
            trace.graph_search_results = graph_results
            trace.user_interest_nodes = user_interests
            trace.timing.update(timing)

            await cache_trace(trace, user_id)

        result = GraphRAGResult(
            query=query,
            entities=entities,
            vector_results=vector_results,
            graph_results=graph_results,
            fused_context=fused_context,
            metadata=metadata,
            trace=trace,
        )

        if settings.ENABLE_GRAPHRAG_FASTPATH and cache_key:
            await self._store_cache(cache_key, result)

        try:
            if "total" in timing:
                RAG_RETRIEVAL_LATENCY.labels(source="graphrag", stage="total").observe(timing["total"])
            if "entity_extraction" in timing:
                RAG_RETRIEVAL_LATENCY.labels(source="graphrag", stage="entity_extract").observe(
                    timing["entity_extraction"]
                )
            if "graph_search" in timing:
                RAG_RETRIEVAL_LATENCY.labels(source="graphrag", stage="graph_expand").observe(timing["graph_search"])
            if "vector_search" in timing:
                RAG_RETRIEVAL_LATENCY.labels(source="pgvector", stage="retrieve").observe(timing["vector_search"])
        except Exception:
            pass

        logger.info(
            f"GraphRAG 完成: vector={len(vector_results)}, "
            f"graph={len(graph_results)}, fused={len(unique_results)}, "
            f"total_time={timing['total']:.3f}s"
        )

        try:
            await record_rag_cost(operation="graphrag_retrieve")
        except Exception:
            pass

        return result

    async def find_learning_path(self, start_node: str, target_node: str) -> list[dict[str, Any]]:
        """
        查找学习路径（高级功能）

        Args:
            start_node: 起点（用户当前水平）
            target_node: 终点（目标知识）

        Returns:
            路径上的节点列表
        """
        try:
            cypher = """
            MATCH path =
                (start:KnowledgeNode {name: $start})-[:PREREQUISITE*1..5]->(goal:KnowledgeNode {name: $target})
            UNWIND nodes(path) as node
            RETURN {
                name: node.name,
                description: node.description,
                importance: node.importance
            } as result
            """

            results = await self.age_client.execute_cypher(cypher, {"start": start_node, "target": target_node})

            logger.info(f"找到学习路径: {start_node} → {target_node}, 长度: {len(results)}")
            return results

        except Exception as e:
            logger.warning(f"查找学习路径失败: {e}")
            return []

    async def find_related_concepts(self, concept: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        查找相关概念（用于知识拓展）

        Args:
            concept: 核心概念
            limit: 返回数量

        Returns:
            相关概念列表
        """
        try:
            cypher = """
            MATCH (c:KnowledgeNode {name: $concept})-[r]-(related)
            WHERE type(r) IN ["RELATED", "PREREQUISITE", "APPLIES_TO"]
              AND toFloat(r.strength) > 0.3
            RETURN {
                name: related.name,
                description: related.description,
                relation: type(r),
                strength: r.strength
            } as result
            ORDER BY toFloat(r.strength) DESC
            LIMIT $limit
            """

            results = await self.age_client.execute_cypher(cypher, {"concept": concept, "limit": limit})

            return results

        except Exception as e:
            logger.warning(f"查找相关概念失败: {e}")
            return []
