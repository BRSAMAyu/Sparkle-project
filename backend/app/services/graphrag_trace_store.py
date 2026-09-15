from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.config import settings
from app.core.cache import cache_service

if TYPE_CHECKING:
    from app.orchestration.graph_rag import RetrievalTrace


TRACE_KEY_PREFIX = "graphrag:trace:"
LATEST_KEY_PREFIX = "graphrag:trace:latest:"


def _trace_key(trace_id: str) -> str:
    return f"{TRACE_KEY_PREFIX}{trace_id}"


def _latest_key(user_id: str) -> str:
    return f"{LATEST_KEY_PREFIX}{user_id}"


def _serialize_trace(trace: RetrievalTrace) -> dict[str, Any]:
    query = trace.query or ""
    truncated_query = query[: settings.GRAPHRAG_TRACE_QUERY_MAX_CHARS]
    redacted_query = _redact_query(truncated_query)

    payload: dict[str, Any] = {
        "trace_id": trace.trace_id,
        "timestamp": trace.timestamp.isoformat(),
        "query_hash": _hash_query(query),
        "nodes_retrieved": trace.nodes_retrieved,
        "node_sources": trace.node_sources,
        "relationships": trace.relationships,
        "vector_search_results": trace.vector_search_results,
        "graph_search_results": trace.graph_search_results,
        "user_interest_nodes": trace.user_interest_nodes,
        "timing": trace.timing,
    }

    if settings.ENABLE_GRAPHRAG_TRACE_PII:
        payload["query"] = truncated_query
    else:
        payload["query_redacted"] = redacted_query

    return payload


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _redact_query(query: str) -> str:
    redacted = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[redacted_email]",
        query,
    )
    redacted = re.sub(
        r"\+?\d[\d\s().-]{7,}\d",
        "[redacted_phone]",
        redacted,
    )
    return redacted


async def cache_trace(trace: RetrievalTrace, user_id: str | None) -> None:
    if not cache_service.redis:
        return
    if not settings.ENABLE_GRAPHRAG_MONITOR_API:
        return

    payload = _serialize_trace(trace)
    raw = json.dumps(payload, ensure_ascii=True)
    if len(raw.encode("utf-8")) > settings.GRAPHRAG_TRACE_MAX_BYTES:
        logger.warning("GraphRAG trace too large to cache trace_id=%s", trace.trace_id)
        return

    trace_key = _trace_key(trace.trace_id)
    await cache_service.redis.setex(trace_key, settings.GRAPHRAG_TRACE_TTL_SECONDS, raw)

    if user_id:
        await cache_service.redis.setex(
            _latest_key(user_id),
            settings.GRAPHRAG_TRACE_TTL_SECONDS,
            trace.trace_id
        )


async def get_trace(trace_id: str) -> dict[str, Any] | None:
    if not cache_service.redis:
        return None
    raw = await cache_service.redis.get(_trace_key(trace_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def get_latest_trace(user_id: str) -> dict[str, Any] | None:
    if not cache_service.redis:
        return None
    trace_id = await cache_service.redis.get(_latest_key(user_id))
    if not trace_id:
        return None
    return await get_trace(trace_id)
