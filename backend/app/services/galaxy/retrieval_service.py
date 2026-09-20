from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger
from redis.commands.search.query import Query
from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.cache import cache_service
from app.core.metrics import RAG_RETRIEVAL_LATENCY, RETRIEVAL_ERROR_TOTAL, RETRIEVAL_TIMEOUT_TOTAL
from app.core.redis_search_client import redis_search_client
from app.db.extensions import is_vector_extension_available
from app.models.community import GroupMember
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.group_files import GroupFile
from app.schemas.galaxy import NodeBase, SearchResultItem, UserStatusInfo
from app.services.context_retrieval_pipeline import (
    KnowledgeAccessContext,
    run_hard_filter_pipeline_async,
)
from app.services.embedding_service import EmbeddingNotConfiguredError, embedding_service
from app.services.rerank_service import rerank_service

try:
    from app.services.group_file_service import GroupFileService
except ImportError:
    GroupFileService = None

try:
    from app.services.semantic_cache_service import semantic_cache_service
except ImportError:
    # Handle circular import or missing dependency during tests
    semantic_cache_service = None

_PGVECTOR_RUNTIME_ENABLED = True

# E-05 D2（R2）：知识数据版本的 Redis 缓存键（TTL=KNOWLEDGE_VERSION_CACHE_TTL_SECONDS=30s）。
# 删除/归档/撤销来源时必须同步失效（SourceLifecycleService.invalidate_source_retrieval），
# 否则 TTL 窗口内的检索仍以旧 knowledge_version 组语义缓存键——exact 与语义相似
# 两条命中路径都会继续命中已删内容的缓存条目（违反"删除即时不可见"）。
KNOWLEDGE_VERSION_CACHE_KEY = "knowledge:version:v1"

# E-05: 词法检索的 token 提取——拉丁字母/数字词（>=2 字符）+ 连续 CJK 段整体
# （长段追加二元组提升召回）。无 zhparser 的 PG 上用 ILIKE 子串匹配。
_LEX_WORD_RE = re.compile(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]+")
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+$")

def extract_lexical_tokens(query: str, *, max_tokens: int = 8) -> list[str]:
    """把查询拆成词法检索 token（去重、保序、截断）。"""
    tokens: list[str] = []
    for match in _LEX_WORD_RE.findall(query or ""):
        token = match.lower()
        if token not in tokens:
            tokens.append(token)
        if len(match) >= 3 and _CJK_RUN_RE.fullmatch(match):
            for i in range(len(match) - 1):
                bigram = match[i : i + 2]
                if bigram not in tokens:
                    tokens.append(bigram)
    return tokens[:max_tokens]

class KnowledgeRetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    # E-05: embedding 版本隔离                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _embedding_version_filter(column):
        """检索只允许命中当前 embedding 版本（或过渡期未标记 NULL）的向量。

        任何标记了**其他**模型的向量无条件排除——跨模型余弦距离没有意义，
        混用会让相似度静默变成垃圾。EMBEDDING_STRICT_VERSION_FILTER=True 时
        连 NULL（来源未知）也排除（重建完成后推荐）。
        """
        current = embedding_service.current_embedding_version()
        if settings.EMBEDDING_STRICT_VERSION_FILTER:
            return column == current
        return or_(column == current, column.is_(None))

    @staticmethod
    def _is_vector_runtime_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = (
            "vector.so",
            "pgvector",
            'type "vector" does not exist',
            "could not load library",
            "operator does not exist: vector",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _disable_vector_runtime(reason: str) -> None:
        global _PGVECTOR_RUNTIME_ENABLED
        if _PGVECTOR_RUNTIME_ENABLED:
            logger.warning(f"Disabling retrieval pgvector runtime fallback: {reason}")
        _PGVECTOR_RUNTIME_ENABLED = False

    async def _vector_runtime_available(self) -> bool:
        if not _PGVECTOR_RUNTIME_ENABLED:
            return False
        available = await is_vector_extension_available(self.db)
        if not available:
            self._disable_vector_runtime("pgvector extension unavailable")
        return available

    @staticmethod
    def _mark_degraded(exec_meta: dict | None) -> None:
        """E-05 D3：向缓存层标记"本次结果为降级产物"（词法降级等）。"""
        if exec_meta is not None:
            exec_meta["degraded"] = True

    async def _keyword_fallback(
        self,
        user_id_uuid: UUID,
        query_str: str,
        subject_id: int | None,
        limit: int,
    ) -> list[SearchResultItem]:
        try:
            keyword_nodes = await self.keyword_search(
                user_id=user_id_uuid,
                query=query_str,
                subject_id=subject_id,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"Keyword fallback search failed: {e}")
            RETRIEVAL_ERROR_TOTAL.labels(source="keyword_fallback", stage="retrieve").inc()
            return []

        if not keyword_nodes:
            return []

        return await self._build_results_from_nodes(keyword_nodes[:limit], user_id_uuid)

    async def _get_knowledge_version(self) -> str | None:
        if not cache_service.redis:
            return await self._compute_knowledge_version()

        cached = await cache_service.get(KNOWLEDGE_VERSION_CACHE_KEY)
        if cached:
            return cached

        version = await self._compute_knowledge_version()
        if version:
            await cache_service.set(KNOWLEDGE_VERSION_CACHE_KEY, version, ttl=settings.KNOWLEDGE_VERSION_CACHE_TTL_SECONDS)
        return version

    async def _compute_knowledge_version(self) -> str | None:
        """知识图谱数据版本：驱动语义缓存的失效隔离。

        E-05 修复：旧实现只用 max(updated_at)。删除**非最新**行不改变
        max(updated_at) → 删除文档/节点后语义缓存可能继续命中陈旧结果
        （delete isolation 漏洞）。加入行数计数后，任何写入或删除都会改变
        版本串，旧缓存条目（exact 与 semantic 命中路径都以版本为键）立即
        无法命中，等 TTL 自然过期。
        """
        try:
            node_max_stmt = select(func.max(KnowledgeNode.updated_at), func.count(KnowledgeNode.id))
            chunk_max_stmt = select(func.max(DocumentChunk.updated_at), func.count(DocumentChunk.id))

            node_result = await self.db.execute(node_max_stmt)
            chunk_result = await self.db.execute(chunk_max_stmt)

            node_max, node_count = node_result.one()
            chunk_max, chunk_count = chunk_result.one()

            candidates = [dt for dt in (node_max, chunk_max) if dt]
            if not candidates and node_count == 0 and chunk_count == 0:
                return "tsms:0"

            latest = max(candidates) if candidates else None
            ts_ms = int(latest.timestamp() * 1000) if latest else 0
            return f"tsms:{ts_ms}:n{int(node_count)}:c{int(chunk_count)}"
        except Exception:
            return None

    async def hybrid_search(
        self,
        user_id: UUID,
        query: str,
        vector_query: str | None = None,
        subject_id: int | None = None,
        limit: int = 5,
        threshold: float = 0.6,
        use_reranker: bool = True
    ) -> list[SearchResultItem]:
        """
        RAG v2.0 Hybrid Search with Cache Stampede Protection.
        """
        if not semantic_cache_service:
            return await self._execute_hybrid_search(user_id, query, vector_query, subject_id, limit, threshold, use_reranker)

        knowledge_version = await self._get_knowledge_version()

        # E-05 D3：降级标记通道——_execute_hybrid_search 在向量侧故障降级词法时
        # 置 degraded=True，语义缓存层据此拒绝把降级结果固化（否则瞬时故障的
        # 词法答案会被缓存 1h，供应商恢复后同查询继续命中降级答案）
        exec_meta: dict = {}
        # Use get_with_lock to prevent redundant heavy retrieval tasks
        return await semantic_cache_service.get_with_lock(
            query=query,
            factory_func=self._execute_hybrid_search,
            user_id=str(user_id), # Optional: could be global if knowledge is shared
            similarity_threshold=settings.SEMANTIC_CACHE_SIM_THRESHOLD,
            knowledge_version=knowledge_version,
            embedding_version=embedding_service.current_embedding_version(),
            factory_meta=exec_meta,
            # factory_func arguments
            user_id_uuid=user_id,
            query_str=query,
            vector_query=vector_query,
            subject_id=subject_id,
            limit=limit,
            threshold=threshold,
            use_reranker=use_reranker
        )

    async def _execute_hybrid_search(
        self,
        user_id_uuid: UUID,
        query_str: str,
        vector_query: str | None = None,
        subject_id: int | None = None,
        limit: int = 5,
        threshold: float = 0.6,
        use_reranker: bool = True,
        exec_meta: dict | None = None,
    ) -> list[SearchResultItem]:
        """
        Internal implementation of hybrid search.

        exec_meta（E-05 D3）：由缓存层（get_with_lock）注入的降级标记通道；
        向量侧因 embedding 故障降级词法检索时置 ``degraded=True``，调用方
        （语义缓存）据此拒绝缓存本次结果。直调时不传则不标记。
        """
        # 2. Prepare Queries
        start_time = time.time()
        actual_vector_text = vector_query if vector_query else query_str
        try:
            query_embedding = await embedding_service.get_embedding(actual_vector_text, text_type="query")
        except EmbeddingNotConfiguredError as e:
            # E-05: 无 key = 明确关闭向量侧，降级词法检索（显式记录，非静默）
            logger.warning(f"Embedding provider not configured; hybrid search degrades to lexical-only: {e}")
            RETRIEVAL_ERROR_TOTAL.labels(source="redis_hybrid", stage="embedding").inc()
            self._mark_degraded(exec_meta)
            return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)
        except Exception as e:
            logger.warning(f"Embedding generation failed for hybrid search: {e}")
            RETRIEVAL_ERROR_TOTAL.labels(source="redis_hybrid", stage="embedding").inc()
            self._mark_degraded(exec_meta)
            return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)

        # 3. Parallel Retrieval
        vector_limit = limit * 10
        keyword_limit = limit * 10

        cleaned_query = " ".join([w for w in query_str.split() if len(w) > 1]) or "*"

        bm25_q = (
            Query(cleaned_query)
            .paging(0, keyword_limit)
            # C-03: 身份字段必须随候选返回——RRF 融合后的权限硬筛（rerank 前）
            # 依赖 source_type / user_id / group_id / lifecycle_status 判定归属
            # （缺失即 fail-closed 砍除，见 context_retrieval_pipeline）。
            .return_fields(
                "id",
                "parent_id",
                "content",
                "parent_name",
                "importance",
                "source_type",
                "user_id",
                "group_id",
                "lifecycle_status",
            )
            .dialect(2)
        )

        vector_task = redis_search_client.hybrid_search(
            text_query="*",
            vector=query_embedding,
            top_k=vector_limit
        )
        keyword_task = redis_search_client.search(bm25_q)

        try:
            vector_res, keyword_res = await asyncio.gather(
                asyncio.wait_for(vector_task, timeout=settings.REDIS_HYBRID_TIMEOUT_SECONDS),
                asyncio.wait_for(keyword_task, timeout=settings.REDIS_HYBRID_TIMEOUT_SECONDS),
            )
            RAG_RETRIEVAL_LATENCY.labels(source="redis_hybrid", stage="retrieve").observe(time.time() - start_time)
        except TimeoutError:
            logger.warning("Redis hybrid search timed out, fallback_enabled=%s", settings.ENABLE_REDIS_HYBRID_FALLBACK)
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="redis_hybrid", stage="retrieve").inc()
            if settings.ENABLE_REDIS_HYBRID_FALLBACK:
                return await self._pgvector_fallback(user_id_uuid, query_str, subject_id, limit, threshold, use_reranker)
            raise
        except Exception as e:
            logger.warning(f"Redis hybrid search failed: {e}, fallback_enabled={settings.ENABLE_REDIS_HYBRID_FALLBACK}")
            RETRIEVAL_ERROR_TOTAL.labels(source="redis_hybrid", stage="retrieve").inc()
            if settings.ENABLE_REDIS_HYBRID_FALLBACK:
                return await self._pgvector_fallback(user_id_uuid, query_str, subject_id, limit, threshold, use_reranker)
            raise

        vec_docs = vector_res.docs if vector_res else []
        kw_docs = keyword_res.docs if keyword_res else []

        if not vec_docs and not kw_docs and settings.ENABLE_REDIS_HYBRID_FALLBACK:
            return await self._pgvector_fallback(user_id_uuid, query_str, subject_id, limit, threshold, use_reranker)

        # 4. RRF Fusion
        fused_results = rerank_service.reciprocal_rank_fusion([vec_docs, kw_docs])
        candidates = [item for item, score in fused_results]

        # 5. C-03 硬过滤 → rerank（顺序铁律：权限滤芯在远程 rerank 模型之前）
        # Redis RAG 索引是跨用户共享索引（vector="*" 全库 KNN + 无用户谓词的
        # BM25），融合候选天然含他人 personal chunk——此前直接把全部候选正文送
        # 远程 rerank 模型（内容外泄 + 预算浪费）。现在合法候选才进 rerank；
        # 砍除归因/延迟/token 计量随 pipeline 报告结构化落日志（C-03 滤芯）。
        # 本路径无群组解析上下文（调用方未请求群组 scope）→ group chunk
        # fail-closed 砍除（knowledge:group_inaccessible），与既有装配面行为
        # 一致（group chunk 的 parent_id=file_id 本就不在 KnowledgeNode 装配集）。
        knowledge_ctx = KnowledgeAccessContext(user_id=str(user_id_uuid))
        rerank_start = time.time()

        async def _rerank_legal(legal: list[Any]) -> list[Any]:
            if not (use_reranker and legal):
                return legal[:limit]
            try:
                return await asyncio.wait_for(
                    rerank_service.rerank(query_str, legal, top_k=limit),
                    timeout=settings.RERANK_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning("Rerank timed out, returning fused candidates.")
                RETRIEVAL_TIMEOUT_TOTAL.labels(source="redis_hybrid", stage="rerank").inc()
                return legal[:limit]
            except Exception as e:
                logger.warning(f"Rerank failed, returning fused candidates: {e}")
                RETRIEVAL_ERROR_TOTAL.labels(source="redis_hybrid", stage="rerank").inc()
                return legal[:limit]

        pipeline_result = await run_hard_filter_pipeline_async(
            knowledge_candidates=candidates,
            knowledge_ctx=knowledge_ctx,
            rerank_fn=_rerank_legal,
        )
        final_chunks = list(pipeline_result.ranked)
        RAG_RETRIEVAL_LATENCY.labels(source="redis_hybrid", stage="rerank").observe(time.time() - rerank_start)

        # 6. Fetch Nodes from DB (Optimized with Status Join to avoid N+1)
        parent_ids = list({chunk.parent_id for chunk in final_chunks})
        if not parent_ids:
            return []

        stmt = (
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id_uuid)
            )
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(KnowledgeNode.id.in_(parent_ids))
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        nodes_map = {str(node.id): (node, status) for node, status in rows}

        # 7. Assemble Result
        search_results = []
        seen_parents = set()

        for chunk in final_chunks:
            pid = chunk.parent_id
            if pid not in nodes_map or pid in seen_parents:
                continue

            seen_parents.add(pid)
            node, user_status = nodes_map[pid]
            search_results.append(self._format_search_result(node, user_status, 1.0))

        return search_results

    async def _build_results_from_nodes(
        self,
        nodes: list[KnowledgeNode],
        user_id_uuid: UUID,
    ) -> list[SearchResultItem]:
        if not nodes:
            return []

        node_ids = list({node.id for node in nodes})
        stmt = (
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id_uuid)
            )
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(KnowledgeNode.id.in_(node_ids))
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        nodes_map = {node.id: (node, status) for node, status in rows}

        search_results = []
        for node in nodes:
            entry = nodes_map.get(node.id)
            if not entry:
                continue
            search_results.append(self._format_search_result(entry[0], entry[1], 1.0))
        return search_results

    async def _pgvector_fallback(
        self,
        user_id_uuid: UUID,
        query_str: str,
        subject_id: int | None,
        limit: int,
        threshold: float,
        use_reranker: bool,
    ) -> list[SearchResultItem]:
        if not await self._vector_runtime_available():
            logger.info("Skipping pgvector fallback because vector runtime is unavailable")
            return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)

        fallback_start = time.time()
        candidate_limit = max(limit * 5, limit)

        try:
            candidates = await self.semantic_search_nodes(
                query=query_str,
                subject_id=subject_id,
                limit=candidate_limit,
                threshold=threshold,
            )
        except Exception as e:
            if self._is_vector_runtime_error(e):
                self._disable_vector_runtime(str(e))
                return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)
            logger.warning(f"pgvector fallback search failed: {e}")
            RETRIEVAL_ERROR_TOTAL.labels(source="pgvector_fallback", stage="retrieve").inc()
            return []

        RAG_RETRIEVAL_LATENCY.labels(source="pgvector_fallback", stage="retrieve").observe(
            time.time() - fallback_start
        )

        if not candidates:
            logger.info("pgvector fallback returned no candidates, trying keyword fallback")
            return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)

        rerank_start = time.time()
        if use_reranker:
            try:
                reranked = await asyncio.wait_for(
                    rerank_service.rerank(query_str, candidates, top_k=limit),
                    timeout=settings.RERANK_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning("pgvector rerank timed out, returning original candidates.")
                RETRIEVAL_TIMEOUT_TOTAL.labels(source="pgvector_fallback", stage="rerank").inc()
                reranked = candidates[:limit]
            except Exception as e:
                logger.warning(f"pgvector rerank failed: {e}")
                RETRIEVAL_ERROR_TOTAL.labels(source="pgvector_fallback", stage="rerank").inc()
                reranked = candidates[:limit]
        else:
            reranked = candidates[:limit]

        RAG_RETRIEVAL_LATENCY.labels(source="pgvector_fallback", stage="rerank").observe(
            time.time() - rerank_start
        )

        results = await self._build_results_from_nodes(reranked, user_id_uuid)
        if results:
            return results

        logger.info("pgvector fallback produced no assembled results, trying keyword fallback")
        return await self._keyword_fallback(user_id_uuid, query_str, subject_id, limit)

    async def document_vector_search(
        self,
        user_id: UUID,
        query: str,
        file_ids: list[UUID],
        vector_query: str | None = None,
        limit: int = 5,
        threshold: float = 0.6,
        include_group_documents: bool = False,
        group_ids: list[UUID | str] | None = None,
    ) -> list[DocumentChunkResult]:
        """
        Vector search over document chunks with forced file scope.
        """
        if not query or not file_ids:
            return []
        if not await self._vector_runtime_available():
            return []

        actual_vector_text = vector_query if vector_query else query
        query_embedding = await embedding_service.get_embedding(actual_vector_text, text_type="query")
        accessible_group_ids: list[UUID] = []
        if include_group_documents and GroupFileService is not None:
            accessible_group_ids = await GroupFileService.list_accessible_group_ids(
                self.db,
                user_id,
                requested_group_ids=group_ids,
            )

        stmt = (
            select(
                DocumentChunk,
                StoredFile.file_name,
                GroupFile.group_id,
                GroupFile.shared_by_id,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .outerjoin(
                GroupFile,
                and_(
                    GroupFile.file_id == DocumentChunk.file_id,
                    GroupFile.not_deleted_filter(),
                    GroupFile.group_id.in_(accessible_group_ids) if accessible_group_ids else false(),
                ),
            )
            .outerjoin(
                GroupMember,
                and_(
                    GroupMember.group_id == GroupFile.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter(),
                ),
            )
            .where(
                or_(
                    DocumentChunk.user_id == user_id,
                    GroupMember.id.isnot(None),
                )
            )
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.deleted_at.is_(None))
            .where(StoredFile.lifecycle_status == SourceLifecycleStatus.ACTIVE.value)
            .where(DocumentChunk.embedding.isnot(None))
            # E-05: 只检索当前 embedding 版本的向量（不同模型的向量混在同一
            # 余弦空间无意义）；过渡期容忍未标记 NULL。
            .where(self._embedding_version_filter(DocumentChunk.embedding_model))
            .order_by("distance")
            .limit(limit * 5)
        )

        try:
            result = await self.db.execute(stmt)
        except Exception as exc:
            if not self._is_vector_runtime_error(exc):
                raise
            self._disable_vector_runtime(str(exc))
            return []
        rows = result.all()

        results: list[DocumentChunkResult] = []
        seen: set[tuple[str, str]] = set()
        for chunk, file_name, group_id, shared_by_id, distance in rows:
            if distance is None:
                continue
            if distance <= threshold:
                score = max(0.0, 1.0 - float(distance))
                dedupe_key = (str(chunk.id), str(group_id or "personal"))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                results.append(
                    DocumentChunkResult(
                        chunk=chunk,
                        file_name=file_name,
                        score=score,
                        group_id=group_id,
                        shared_by_user_id=shared_by_id,
                    )
                )

        return results[:limit]

    async def document_lexical_search(
        self,
        user_id: UUID,
        query: str,
        file_ids: list[UUID],
        limit: int = 5,
        include_group_documents: bool = False,
        group_ids: list[UUID | str] | None = None,
    ) -> list[DocumentChunkResult]:
        """E-05: 纯词法（稀疏）检索 document_chunks，与向量检索同权限边界。

        - 用户隔离：与 document_vector_search 完全一致（本人 chunk 或其可访问
          群组共享 chunk），wrong-user=0 由 SQL 谓词保证；
        - 生命周期：只检索 ACTIVE 且未软删的来源；
        - 不依赖 embedding（无 key 时仍然可用，作为向量能力的词法降级路径）。
        """
        tokens = extract_lexical_tokens(query)
        if not query or not file_ids or not tokens:
            return []

        accessible_group_ids: list[UUID] = []
        if include_group_documents and GroupFileService is not None:
            accessible_group_ids = await GroupFileService.list_accessible_group_ids(
                self.db,
                user_id,
                requested_group_ids=group_ids,
            )

        escaped = [token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for token in tokens]
        match_conditions = [
            or_(
                DocumentChunk.content.ilike(f"%{token}%"),
                DocumentChunk.section_title.ilike(f"%{token}%"),
            )
            for token in escaped
        ]
        lex_score = sum(
            case(
                (
                    or_(
                        DocumentChunk.content.ilike(f"%{token}%"),
                        DocumentChunk.section_title.ilike(f"%{token}%"),
                    ),
                    1,
                ),
                else_=0,
            )
            for token in escaped
        )

        stmt = (
            select(
                DocumentChunk,
                StoredFile.file_name,
                GroupFile.group_id,
                GroupFile.shared_by_id,
                lex_score.label("lex_score"),
            )
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .outerjoin(
                GroupFile,
                and_(
                    GroupFile.file_id == DocumentChunk.file_id,
                    GroupFile.not_deleted_filter(),
                    GroupFile.group_id.in_(accessible_group_ids) if accessible_group_ids else false(),
                ),
            )
            .outerjoin(
                GroupMember,
                and_(
                    GroupMember.group_id == GroupFile.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter(),
                ),
            )
            .where(
                or_(
                    DocumentChunk.user_id == user_id,
                    GroupMember.id.isnot(None),
                )
            )
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.deleted_at.is_(None))
            .where(StoredFile.lifecycle_status == SourceLifecycleStatus.ACTIVE.value)
            .where(or_(*match_conditions))
            .order_by(lex_score.desc(), DocumentChunk.chunk_index.asc())
            .limit(limit * 10)
        )
        result = await self.db.execute(stmt)

        rows = result.all()
        lexical_results_out: list[DocumentChunkResult] = []
        for chunk, file_name, group_id, shared_by_id, score in rows:
            lexical_results_out.append(
                DocumentChunkResult(
                    chunk=chunk,
                    file_name=file_name,
                    score=float(int(score or 0)) / max(1, len(tokens)),
                    group_id=group_id,
                    shared_by_user_id=shared_by_id,
                )
            )
        return lexical_results_out[:limit]

    async def document_hybrid_search(
        self,
        user_id: UUID,
        query: str,
        file_ids: list[UUID],
        vector_query: str | None = None,
        limit: int = 5,
        threshold: float = 0.4,
        use_reranker: bool = True,
        include_group_documents: bool = False,
        group_ids: list[UUID | str] | None = None,
        exec_meta: dict[str, Any] | None = None,
    ) -> list[DocumentChunkResult]:
        """E-05: hybrid lexical + vector 检索（RRF 融合，可选 rerank）。

        - 并行跑 document_vector_search 与 document_lexical_search；
        - 向量侧失败（含未配置 key）时降级为纯词法——显式记日志，绝不静默
          使用占位向量；
        - 融合用 reciprocal_rank_fusion（与 Redis hybrid 链路同一实现），
          可选 rerank（超时/失败回退融合序）。

        exec_meta（FIX-16 ④ D8）：实际执行模式回填通道。调用方（工具层）
        据此报告 ``retrieval_mode``——不再按「key 是否配置」预写 hybrid：
        供应商故障期（key 在、调用败）或向量运行时熔断期实际执行的是词法，
        payload 必须如实反映。词表：
          hybrid_lexical_vector ｜ lexical_only_embedding_disabled ｜
          lexical_only_vector_degraded ｜ lexical_only_vector_disabled ｜
          vector_only_lexical_degraded ｜ retrieval_unavailable
        """
        start_time = time.time()
        candidate_limit = max(limit * 5, limit)

        def _report_mode(mode: str) -> None:
            if exec_meta is not None:
                exec_meta["retrieval_mode"] = mode

        vector_task = self.document_vector_search(
            user_id=user_id,
            query=query,
            file_ids=file_ids,
            vector_query=vector_query,
            limit=candidate_limit,
            threshold=threshold,
            include_group_documents=include_group_documents,
            group_ids=group_ids,
        )
        lexical_task = self.document_lexical_search(
            user_id=user_id,
            query=query,
            file_ids=file_ids,
            limit=candidate_limit,
            include_group_documents=include_group_documents,
            group_ids=group_ids,
        )

        vector_results, lexical_results = await asyncio.gather(
            vector_task, lexical_task, return_exceptions=True
        )  # type: ignore[assignment]

        vector_side_failed = False
        lexical_side_failed = False
        if isinstance(vector_results, BaseException):
            if isinstance(vector_results, EmbeddingNotConfiguredError):
                logger.warning(
                    "Hybrid document search: embedding provider not configured; "
                    "degrading to lexical-only retrieval (vector side explicitly disabled)"
                )
                _report_mode("lexical_only_embedding_disabled")
            else:
                logger.warning(f"Hybrid document search vector side failed: {vector_results}")
                RETRIEVAL_ERROR_TOTAL.labels(source="pg_hybrid", stage="retrieve").inc()
                _report_mode("lexical_only_vector_degraded")
            vector_side_failed = True
            vector_results = []
        if isinstance(lexical_results, BaseException):
            logger.warning(f"Hybrid document search lexical side failed: {lexical_results}")
            RETRIEVAL_ERROR_TOTAL.labels(source="pg_hybrid", stage="retrieve").inc()
            lexical_side_failed = True
            lexical_results = []

        if vector_side_failed and lexical_side_failed:
            _report_mode("retrieval_unavailable")
        elif lexical_side_failed:
            _report_mode("vector_only_lexical_degraded")

        if not vector_results and not lexical_results:
            return []

        # D8：向量侧「空结果但无异常」需区分「熔断/关闭」与「正常零命中」——
        # 前者实际执行的是纯词法，模式不得谎报 hybrid。
        if not vector_side_failed and not vector_results and not await self._vector_runtime_available():
            _report_mode("lexical_only_vector_disabled")
        elif not vector_side_failed and not lexical_side_failed:
            _report_mode("hybrid_lexical_vector")

        fused_results = rerank_service.reciprocal_rank_fusion([vector_results, lexical_results])
        candidates = [item for item, _score in fused_results]

        rerank_start = time.time()
        if use_reranker and candidates:
            try:
                final_chunks = await asyncio.wait_for(
                    rerank_service.rerank(query, candidates, top_k=limit),
                    timeout=settings.RERANK_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning("Hybrid document rerank timed out, returning fused candidates.")
                RETRIEVAL_TIMEOUT_TOTAL.labels(source="pg_hybrid", stage="rerank").inc()
                final_chunks = candidates[:limit]
            except Exception as e:
                logger.warning(f"Hybrid document rerank failed, returning fused candidates: {e}")
                RETRIEVAL_ERROR_TOTAL.labels(source="pg_hybrid", stage="rerank").inc()
                final_chunks = candidates[:limit]
        else:
            final_chunks = candidates[:limit]
        RAG_RETRIEVAL_LATENCY.labels(source="pg_hybrid", stage="rerank").observe(time.time() - rerank_start)
        RAG_RETRIEVAL_LATENCY.labels(source="pg_hybrid", stage="retrieve").observe(time.time() - start_time)

        return final_chunks

    async def semantic_search_nodes(
        self,
        query: str,
        subject_id: int | None = None,
        limit: int = 10,
        threshold: float = 0.3
    ) -> list[KnowledgeNode]:
        """Internal semantic search that returns KnowledgeNode models."""
        ranked_nodes = await self.semantic_search_ranked_nodes(
            query=query,
            subject_id=subject_id,
            limit=limit,
            threshold=threshold,
        )
        return [node for node, _score in ranked_nodes]

    async def semantic_search_ranked_nodes(
        self,
        query: str,
        subject_id: int | None = None,
        limit: int = 10,
        threshold: float = 0.6,
    ) -> list[tuple[KnowledgeNode, float]]:
        """Internal semantic search that returns nodes with normalized scores.
        threshold is cosine DISTANCE (0=identical, 1=opposite).
        Default 0.6 ≈ similarity>0.4, suitable for Chinese DashScope embeddings.
        """
        if not await self._vector_runtime_available():
            return []

        query_embedding = await embedding_service.get_embedding(query, text_type="query")

        search_query = (
            select(
                KnowledgeNode,
                KnowledgeNode.embedding.cosine_distance(query_embedding).label('distance')
            )
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(KnowledgeNode.embedding.isnot(None))
            .where(or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"))
            # E-05: 版本隔离——不同 embedding 模型的节点向量不参与当前查询
            .where(self._embedding_version_filter(KnowledgeNode.embedding_model))
        )

        if subject_id:
            search_query = search_query.where(KnowledgeNode.subject_id == subject_id)

        search_query = (
            search_query
            .order_by('distance')
            .limit(limit)
        )

        try:
            result = await self.db.execute(search_query)
        except Exception as exc:
            if not self._is_vector_runtime_error(exc):
                raise
            self._disable_vector_runtime(str(exc))
            return []
        matches = result.all()

        ranked_matches: list[tuple[KnowledgeNode, float]] = []
        for node, distance in matches:
            if distance is None or distance > threshold:
                continue
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            ranked_matches.append((node, score))

        return ranked_matches

    async def keyword_search(
        self,
        user_id: UUID,
        query: str,
        subject_id: int | None = None,
        limit: int = 20
    ) -> list[KnowledgeNode]:
        """Keyword search for nodes (Sparse Retrieval).

        R6-P0-7: previously accepted ``user_id`` but ignored it. Now the query
        is restricted to nodes the user can access — either seed/system nodes
        (``is_seed=True`` or ``source_type='seed'``) or nodes the user has a
        ``UserNodeStatus`` row for. This matches what callers expect when they
        pass ``user_id``.
        """
        from sqlalchemy import func

        # Optimized JSONB search using @> operator for exact tags match
        # and jsonb_path_exists for partial match inside array if needed (requires PG 12+)
        # Here we use a hybrid approach:
        # 1. ILIKE for Name/Description
        # 2. @> for exact keyword match (using GIN index)
        # 3. jsonb_path_exists for partial keyword match
        # Escape LIKE wildcards and regex metacharacters to prevent injection
        # Both ILIKE patterns and jsonb_path_exists regex are vulnerable
        escaped_query = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        # For regex injection in jsonb_path_exists, also escape regex special chars
        import re
        regex_safe_query = re.escape(query)

        # R6-P0-7: tenant isolation — node must be seed OR user has UserNodeStatus
        user_status_exists = (
            select(UserNodeStatus.node_id)
            .where(
                UserNodeStatus.node_id == KnowledgeNode.id,
                UserNodeStatus.user_id == user_id,
            )
            .exists()
        )

        stmt = (
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent)
            )
            .where(
                or_(
                    KnowledgeNode.name.ilike(f"%{escaped_query}%"),
                    KnowledgeNode.description.ilike(f"%{escaped_query}%"),
                    KnowledgeNode.keywords.contains([query]),
                    func.jsonb_path_exists(
                        KnowledgeNode.keywords,
                        f'$[*] ? (@ like_regex "{regex_safe_query}" flag "i")'
                    )
                )
            )
            .where(or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"))
            .where(
                or_(
                    KnowledgeNode.is_seed.is_(True),
                    KnowledgeNode.source_type == "seed",
                    user_status_exists,
                )
            )
        )

        if subject_id:
            stmt = stmt.where(KnowledgeNode.subject_id == subject_id)

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # --- Helpers ---
    async def get_user_node_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus | None:
        """Public alias for _get_user_status."""
        return await self._get_user_status(user_id, node_id)

    async def _get_user_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus | None:
        stmt = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == node_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _format_search_result(self, node: KnowledgeNode, status: UserNodeStatus | None, score: float) -> SearchResultItem:
        node_base = NodeBase.from_model(node)

        user_status_info = None
        if status:
            # Note: We duplicate logic from StatsService for formatting to avoid circular deps
            # Ideally this formatting logic belongs to a Schema Mapper
            brightness = 0.3 + (status.mastery_score / 100.0) * 0.7
            if not status.is_unlocked: brightness = 0.2

            from app.schemas.galaxy import NodeStatus
            visual_status = NodeStatus.UNLIT
            if status.is_unlocked:
                if status.mastery_score >= 80: visual_status = NodeStatus.BRILLIANT
                elif status.mastery_score > 0: visual_status = NodeStatus.GLIMMER
            else:
                visual_status = NodeStatus.LOCKED

            user_status_info = UserStatusInfo(
                mastery_score=status.mastery_score,
                total_study_minutes=status.total_study_minutes,
                study_count=status.study_count,
                is_unlocked=status.is_unlocked,
                is_collapsed=status.is_collapsed,
                is_favorite=status.is_favorite,
                first_unlock_at=status.first_unlock_at,
                last_study_at=status.last_study_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                status=visual_status,
                brightness=brightness
            )

        return SearchResultItem(
            node=node_base,
            similarity=score,
            user_status=user_status_info
        )


@dataclass
class DocumentChunkResult:
    chunk: DocumentChunk
    file_name: str
    score: float
    group_id: UUID | None = None
    shared_by_user_id: UUID | None = None
    trust_level: str | None = None

    @property
    def id(self) -> str:
        """RRF 融合按 id 去重（rerank_service.reciprocal_rank_fusion 契约）。"""
        return str(self.chunk.id)

    @property
    def content(self) -> str:
        """rerank 契约：候选需暴露 content 供重排序器读取。"""
        return self.chunk.content or ""
