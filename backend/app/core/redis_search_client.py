from __future__ import annotations

import struct
from typing import Any

from loguru import logger
from redis.asyncio import Redis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.services.rag_indexing_service import RAG_INDEX_PREFIXES


class RedisSearchClient:
    """
    Wrapper for Redis Search (RediSearch)
    Handles Vector Search + Hybrid Search
    """

    def __init__(self, redis_url: str = settings.REDIS_URL, password: str | None = settings.REDIS_PASSWORD):
        resolved_password, _ = resolve_redis_password(redis_url, password)
        # Note: Redis 7.x with ACL requires username='default' when password is set
        self.redis = Redis.from_url(redis_url, username="default", password=resolved_password, decode_responses=True)
        self.index_name = "idx:knowledge"

    @staticmethod
    def _is_missing_index_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        return "no such index" in lowered or "unknown index name" in lowered

    @staticmethod
    def _is_search_module_unavailable(exc: Exception) -> bool:
        lowered = str(exc).lower()
        return "unknown command" in lowered or "module" in lowered and "not found" in lowered

    def _build_index_schema(self):
        return (
            TextField("$.content", as_name="content", weight=1.0),
            TextField("$.keywords", as_name="keywords", weight=2.0),
            TagField("$.parent_id", as_name="parent_id"),
            TagField("$.source_type", as_name="source_type"),
            TagField("$.user_id", as_name="user_id"),
            TagField("$.group_id", as_name="group_id"),
            TagField("$.shared_by_user_id", as_name="shared_by_user_id"),
            TagField("$.trust_level", as_name="trust_level"),
            TagField("$.document_scope", as_name="document_scope"),
            TextField("$.parent_name", as_name="parent_name"),
            NumericField("$.subject_id", as_name="subject_id"),
            NumericField("$.importance", as_name="importance"),
            VectorField(
                "$.vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": settings.EMBEDDING_DIM,
                    "DISTANCE_METRIC": "COSINE",
                    "M": 16,
                    "EF_CONSTRUCTION": 200,
                },
                as_name="vector",
            ),
        )

    async def ensure_index(self) -> bool:
        try:
            await self.redis.ft(self.index_name).info()
            return True
        except Exception as exc:
            if not self._is_missing_index_error(exc):
                if self._is_search_module_unavailable(exc):
                    logger.warning(f"Redis search module unavailable while checking index {self.index_name}: {exc}")
                else:
                    logger.warning(f"Failed to inspect Redis search index {self.index_name}: {exc}")
                return False

        try:
            await self.redis.ft(self.index_name).create_index(
                self._build_index_schema(),
                definition=IndexDefinition(prefix=RAG_INDEX_PREFIXES, index_type=IndexType.JSON),
            )
            logger.info(f"Created missing Redis search index {self.index_name}")
            return True
        except Exception as exc:
            lowered = str(exc).lower()
            if "index already exists" in lowered:
                return True
            if self._is_search_module_unavailable(exc):
                logger.warning(f"Redis search module unavailable while creating index {self.index_name}: {exc}")
            else:
                logger.warning(f"Failed to create Redis search index {self.index_name}: {exc}")
            return False

    async def search(self, query: Query, query_params: dict[str, Any] | None = None):
        """Execute a search query"""
        try:
            return await self.redis.ft(self.index_name).search(query, query_params)
        except Exception as e:
            if self._is_missing_index_error(e):
                logger.warning(f"Redis search index {self.index_name} missing, attempting initialization")
                if await self.ensure_index():
                    try:
                        return await self.redis.ft(self.index_name).search(query, query_params)
                    except Exception as retry_exc:
                        logger.warning(f"Redis search retry failed after index initialization: {retry_exc}")
                        return None
                return None
            if self._is_search_module_unavailable(e):
                logger.warning(f"Redis search module unavailable: {e}")
                return None
            logger.error(f"Redis search failed: {e}")
            return None

    async def hybrid_search(self, text_query: str, vector: list[float], top_k: int = 10, vector_field: str = "vector"):
        """
        Perform Hybrid Search (Text Filter + Vector Similarity)
        Syntax: (<text_query>) => [KNN <k> @vector $vec_param AS vector_score]
        """
        # 1. Prepare Vector Blob
        # Convert list of floats to binary string (Little Endian Float32)
        vector_blob = struct.pack(f"{len(vector)}f", *vector)

        # 2. Construct Query
        # If text_query is empty, use wildcard
        actual_text = text_query if text_query.strip() else "*"

        # RediSearch Query Syntax for Hybrid
        # We want to pre-filter by text, then run KNN on the result.
        # Format: "text_query=>[KNN k @vector $vec AS score]"
        q_str = f"({actual_text})=>[KNN {top_k} @{vector_field} $vec AS vector_score]"

        q = (
            Query(q_str)
            .sort_by("vector_score")
            .paging(0, top_k)
            .return_fields(
                "id",
                "parent_id",
                "content",
                "vector_score",
                "parent_name",
                "importance",
                "source_type",
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
            )
            .dialect(2)
        )

        params = {"vec": vector_blob}

        return await self.search(q, params)

    async def close(self):
        await self.redis.close()


# Global Instance
redis_search_client = RedisSearchClient()
