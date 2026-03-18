"""
GraphRAG 检索器

结合向量检索和图检索，提供增强的知识检索能力
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from app.config import settings
from app.core.age_client import get_age_client
from app.core.cache import cache_service
from app.core.metrics import CACHE_HIT_COUNT, RAG_RETRIEVAL_LATENCY, RETRIEVAL_TIMEOUT_TOTAL
from app.services.graphrag_trace_store import cache_trace
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import llm_service


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


class GraphRAGRetriever:
    """GraphRAG 检索器"""

    def __init__(self, knowledge_service: KnowledgeService):
        self.age_client = get_age_client()
        self.knowledge_service = knowledge_service
        self.max_depth = 2
        self.min_strength = 0.3

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def _build_cache_key(self, query: str, user_id: str, knowledge_version: str | None) -> str:
        normalized_query = self._normalize_query(query)
        parts = [normalized_query, user_id, "v1"]
        if knowledge_version:
            parts.append(knowledge_version)
        raw = ":".join(parts)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"graphrag:cache:{digest}"

    async def _get_cached_result(
        self,
        cache_key: str
    ) -> GraphRAGResult | None:
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
                trace=None
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
            "metadata": result.metadata
        }
        await cache_service.set(cache_key, payload, ttl=settings.GRAPHRAG_CACHE_TTL_SECONDS)

    async def _retrieve_fastpath(
        self,
        query: str,
        user_id: str,
        depth: int
    ) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], str, list[dict[str, Any]], list[str], dict[str, float], list[dict[str, Any]]]:
        import time
        timing: dict[str, float] = {}
        start_time = time.time()

        timeout = settings.GRAPHRAG_FASTPATH_TIMEOUT_SECONDS
        try:
            t0 = time.time()
            entities_task = self.extract_entities(query)
            vector_task = self.vector_search(query, top_k=5)
            interests_task = self.get_user_interests(user_id)
            entities, vector_results, user_interests = await asyncio.wait_for(
                asyncio.gather(entities_task, vector_task, interests_task),
                timeout=timeout
            )
            parallel_duration = time.time() - t0
            timing["parallel_stage"] = parallel_duration
            timing["entity_extraction"] = parallel_duration
            timing["vector_search"] = parallel_duration
            timing["user_interests"] = parallel_duration
        except TimeoutError:
            logger.warning("GraphRAG fastpath timeout in parallel stage, falling back to sequential")
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="parallel").inc()
            return await self._retrieve_sequential(query, user_id, depth)

        t0 = time.time()
        try:
            graph_results, relationships = await asyncio.wait_for(
                self.graph_search(entities, depth),
                timeout=timeout
            )
        except TimeoutError:
            logger.warning("GraphRAG fastpath graph search timeout")
            RETRIEVAL_TIMEOUT_TOTAL.labels(source="graphrag", stage="graph_search").inc()
            graph_results, relationships = [], []
        timing["graph_search"] = time.time() - t0

        t0 = time.time()
        fused_context, unique_results = self.fuse_results(
            vector_results, graph_results, user_interests
        )
        timing["fusion"] = time.time() - t0
        timing["total"] = time.time() - start_time

        return entities, vector_results, graph_results, fused_context, unique_results, user_interests, timing, relationships

    async def _retrieve_sequential(
        self,
        query: str,
        user_id: str,
        depth: int
    ) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], str, list[dict[str, Any]], list[str], dict[str, float], list[dict[str, Any]]]:
        import time
        timing: dict[str, float] = {}
        start_time = time.time()

        # 1. 实体识别
        t0 = time.time()
        entities = await self.extract_entities(query)
        timing["entity_extraction"] = time.time() - t0

        # 2. 向量检索 (语义相似)
        t0 = time.time()
        vector_results = await self.vector_search(query, top_k=5)
        timing["vector_search"] = time.time() - t0

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
        fused_context, unique_results = self.fuse_results(
            vector_results, graph_results, user_interests
        )
        timing["fusion"] = time.time() - t0
        timing["total"] = time.time() - start_time

        return entities, vector_results, graph_results, fused_context, unique_results, user_interests, timing, relationships

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
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await llm_service.chat(messages)

            # 清理响应
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1].strip()
            if response.startswith('json'):
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

    async def vector_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        向量检索（语义相似）

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            检索结果
        """
        try:
            # 使用现有的知识服务进行向量检索
            results = await self.knowledge_service.semantic_search(
                query=query,
                top_k=top_k,
                min_similarity=0.3
            )

            # 格式化结果
            formatted = []
            for result in results:
                formatted.append({
                    "id": str(result.id),
                    "name": result.name,
                    "description": result.description,
                    "similarity": result.similarity,
                    "source": "vector"
                })

            logger.debug(f"向量检索: {len(formatted)} 条结果")
            return formatted

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    async def graph_search(self, entities: list[str], depth: int = 2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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

        for entity in entities:
            try:
                # 查找实体及其关联知识
                cypher = f"""
                MATCH (start:KnowledgeNode {{name: $entity}})
                -[r*1..{depth}]-(related)
                WHERE ALL(edge IN r WHERE edge.strength > $min_strength)
                RETURN {{
                    start_id: start.id,
                    start_name: start.name,
                    id: related.id,
                    name: related.name,
                    description: related.description,
                    relation_type: type(r[0]),
                    strength: r[0].strength,
                    sector: related.sector
                }} as result
                ORDER BY r[0].strength DESC
                LIMIT 10
                """

                result = await self.age_client.execute_cypher(
                    cypher,
                    {"entity": entity, "min_strength": self.min_strength}
                )

                # 添加元数据并收集关系
                for item in result:
                    item["source"] = "graph"
                    item["query_entity"] = entity

                    # 收集关系信息（用于可视化）
                    relationships.append({
                        "from_id": item.get("start_id"),
                        "from_name": item.get("start_name", entity),
                        "to_id": item.get("id"),
                        "to_name": item.get("name"),
                        "relation_type": item.get("relation_type"),
                        "strength": item.get("strength")
                    })

                results.extend(result)

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
            MATCH (u:User {id: $user_id})-[r:INTERESTED_IN|STUDIED]->(k:KnowledgeNode)
            WHERE r.strength > 0.3
            RETURN DISTINCT {name: k.name} as result
            ORDER BY r.strength DESC
            LIMIT 10
            """

            results = await self.age_client.execute_cypher(
                cypher,
                {"user_id": user_id}
            )

            return [r["name"] for r in results]

        except Exception as e:
            logger.warning(f"获取用户兴趣失败: {e}")
            return []

    def fuse_results(self, vector_results: list[dict], graph_results: list[dict],
                     user_interests: list[str]) -> tuple[str, list[dict]]:
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

    async def retrieve(self, query: str, user_id: str, depth: int = 2, enable_trace: bool = True) -> GraphRAGResult:
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
        cache_key = None
        if settings.ENABLE_GRAPHRAG_FASTPATH:
            knowledge_version = None
            try:
                knowledge_version = await self.knowledge_service.get_knowledge_version()
            except Exception as e:
                logger.warning(f"Failed to resolve knowledge version for cache key: {e}")
            cache_key = self._build_cache_key(query, user_id, knowledge_version=knowledge_version)
            cached = await self._get_cached_result(cache_key)
            if cached:
                CACHE_HIT_COUNT.labels(cache_name="graphrag", result="hit").inc()
                return cached
            CACHE_HIT_COUNT.labels(cache_name="graphrag", result="miss").inc()

        if settings.ENABLE_GRAPHRAG_FASTPATH:
            (
                entities,
                vector_results,
                graph_results,
                fused_context,
                unique_results,
                user_interests,
                timing,
                relationships
            ) = await self._retrieve_fastpath(query, user_id, depth)
        else:
            (
                entities,
                vector_results,
                graph_results,
                fused_context,
                unique_results,
                user_interests,
                timing,
                relationships
            ) = await self._retrieve_sequential(query, user_id, depth)

        # 6. 构建元数据
        metadata = {
            "vector_count": len(vector_results),
            "graph_count": len(graph_results),
            "fusion_count": len(unique_results),
            "entities": entities,
            "user_interests": user_interests,
            "query": query,
            "timing": timing
        }

        # 7. 构建检索追踪信息（用于前端可视化）
        trace = None
        if enable_trace:
            # 构建节点来源映射
            node_sources = {}
            for node in vector_results:
                node_sources[node["id"]] = "vector"
            for node in graph_results:
                node_sources[node["id"]] = "graph"

            trace = RetrievalTrace(
                trace_id=str(uuid.uuid4()),
                query=query,
                timestamp=datetime.now(),
                nodes_retrieved=unique_results,
                node_sources=node_sources,
                relationships=relationships,
                vector_search_results=vector_results,
                graph_search_results=graph_results,
                user_interest_nodes=user_interests,
                timing=timing
            )

            await cache_trace(trace, user_id)

        result = GraphRAGResult(
            query=query,
            entities=entities,
            vector_results=vector_results,
            graph_results=graph_results,
            fused_context=fused_context,
            metadata=metadata,
            trace=trace
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
            MATCH path = shortestPath(
                (start:KnowledgeNode {name: $start})-[*1..5]-(end:KnowledgeNode {name: $target})
            )
            UNWIND nodes(path) as node
            RETURN {
                name: node.name,
                description: node.description,
                importance: node.importance
            } as result
            """

            results = await self.age_client.execute_cypher(
                cypher,
                {"start": start_node, "target": target_node}
            )

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
            MATCH (c:KnowledgeNode {name: $concept})-[r:RELATED|PREREQUISITE|APPLIES_TO]-(related)
            WHERE r.strength > 0.3
            RETURN {
                name: related.name,
                description: related.description,
                relation: type(r),
                strength: r.strength
            } as result
            ORDER BY r.strength DESC
            LIMIT $limit
            """

            results = await self.age_client.execute_cypher(
                cypher,
                {"concept": concept, "limit": limit}
            )

            return results

        except Exception as e:
            logger.warning(f"查找相关概念失败: {e}")
            return []
