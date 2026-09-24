"""
增强的知识服务 - 支持双写和 GraphRAG

在原有 KnowledgeService 基础上增加图数据库支持
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.age_client import get_age_client
from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.graph_models import KnowledgeVertex
from app.services.expansion_service import ExpansionService
from app.services.knowledge_service import KnowledgeService
from app.services.node_sector_service import dominant_sector_from_weights


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GraphKnowledgeService:
    """
    增强的知识服务

    特性:
    - 双写: Postgres + AGE
    - GraphRAG 检索
    - 缓存优化
    """

    # 监控探针超时（秒）：探针必须快速失败，不能拖垮监控端点
    GRAPH_PROBE_TIMEOUT_SECONDS: float = 5.0

    def __init__(self, db: AsyncSession):
        self.db = db
        self.age_client = get_age_client()
        self.vector_service = KnowledgeService(db)
        self.redis = cache_service.redis

    async def check_graph_connection(self) -> bool:
        """
        图数据库（Apache AGE）连接探针

        轻量 Cypher ``RETURN 1`` 真往返（带超时）。任何异常/超时都归一化为 False，
        保证监控端点在图库不可达时仍能产出结构化 degraded/unhealthy 报告而非 500。
        """
        try:
            await asyncio.wait_for(
                self.age_client.execute_cypher("RETURN 1 AS result"),
                timeout=self.GRAPH_PROBE_TIMEOUT_SECONDS,
            )
            return True
        except Exception as e:
            logger.warning(f"AGE 连接探针失败: {e}")
            return False

    async def check_vector_connection(self) -> bool:
        """
        向量库（pgvector）连接探针

        对 embedding 向量列做真实 SQL 往返（IS NOT NULL 计数）：
        pgvector 扩展缺失 / 向量类型不可用时该查询会直接失败，据此判定向量库不可用。
        """
        try:
            embedded = await self.db.scalar(
                select(func.count()).select_from(KnowledgeNode).where(KnowledgeNode.embedding.isnot(None))
            )
            logger.debug(f"pgvector 探针通过，已嵌入节点数: {embedded}")
            return True
        except Exception as e:
            logger.warning(f"pgvector 连接探针失败: {e}")
            return False

    async def get_graph_statistics(self) -> dict[str, Any]:
        """
        图数据库真实计数统计（Apache AGE 全图扫描聚合）

        消费契约：graph_monitor 端点逐字段 ``.get`` 读取，字段名勿改——
        total_nodes / total_relations / node_types / relation_types

        Raises:
            Exception: AGE 总量计数失败时向上抛出（端点侧有兜底分支）；
                       类型分布查询失败则降级为空分布，不拖垮整体统计。
        """
        total_rows = await self.age_client.execute_cypher("MATCH (n) RETURN {total_nodes: count(n)} AS result")
        total_nodes = int(total_rows[0]["total_nodes"]) if total_rows else 0

        relation_total_rows = await self.age_client.execute_cypher(
            "MATCH ()-[r]->() RETURN {total_relations: count(r)} AS result"
        )
        total_relations = int(relation_total_rows[0]["total_relations"]) if relation_total_rows else 0

        return {
            "total_nodes": total_nodes,
            "total_relations": total_relations,
            "node_types": await self._graph_type_distribution(
                "MATCH (n) RETURN {type_name: labels(n)[0], type_count: count(*)} AS result"
            ),
            "relation_types": await self._graph_type_distribution(
                "MATCH ()-[r]->() RETURN {type_name: type(r), type_count: count(*)} AS result"
            ),
        }

    async def _graph_type_distribution(self, cypher: str) -> dict[str, int]:
        """
        图元素类型分布（节点 label / 关系 type → 计数）

        AGE 分组聚合形态存在版本差异，查询失败时降级为空分布而非整体失败。
        """
        try:
            rows = await self.age_client.execute_cypher(cypher)
        except Exception as e:
            logger.warning(f"图类型分布查询失败（降级为空分布）: {e}")
            return {}

        distribution: dict[str, int] = {}
        for row in rows:
            type_name = row.get("type_name")
            if isinstance(type_name, str) and type_name:
                distribution[type_name] = int(row.get("type_count") or 0)
        return distribution

    async def get_detailed_statistics(self) -> dict[str, Any]:
        """
        详细统计：AGE 图侧真实计数 + Postgres 双写侧对照 + 同步积压

        供 /monitor/graph/statistics 端点消费；AGE 与 PG 的差值即同步滞后规模。
        """
        stats = await self.get_graph_statistics()
        stats["graph_name"] = self.age_client.config.graph_name

        pg_nodes = await self.db.scalar(select(func.count()).select_from(KnowledgeNode))
        pg_relations = await self.db.scalar(select(func.count()).select_from(NodeRelation))
        stats["pg_total_nodes"] = int(pg_nodes or 0)
        stats["pg_total_relations"] = int(pg_relations or 0)

        stats["sync_stream_length"] = 0
        if self.redis:
            try:
                stats["sync_stream_length"] = int(await self.redis.xlen("stream:graph_sync"))  # type: ignore[misc]  # redis-py 桩 ResponseT 联合含同步 int 分支
            except Exception as e:
                logger.warning(f"读取同步流长度失败: {e}")

        return stats

    async def create_knowledge_node(
        self,
        name: str,
        description: str,
        sector_code: str = "VOID",
        importance_level: int = 1,
        keywords: list[str] = None,
        source_type: str = "user_created",
        source_task_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> KnowledgeNode:
        """
        创建知识节点（双写）

        Returns:
            PostgreSQL 节点对象
        """
        if keywords is None:
            keywords = []

        expansion_service = ExpansionService(self.db)
        node, _ = await expansion_service.upsert_node_from_candidate(
            user_id=user_id or uuid.uuid4(),
            candidate={
                "name": name,
                "description": description,
                "importance_level": importance_level,
                "keywords": keywords,
                "sector_weights": {sector_code: 100},
            },
            source_type=source_type,
            generate_embedding=False,
            unlock_for_user=user_id is not None,
            commit=False,
            invalidate_caches=user_id is not None,
        )
        node.source_task_id = source_task_id
        node.sector_classification_model = "graph_knowledge_service"
        node.sector_classified_at = node.sector_classified_at or _utcnow()
        self.db.add(node)
        await self.db.flush()

        # 2. 异步写入 AGE（通过 Redis 队列）
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "node_created",
                    "data": json.dumps(
                        {
                            "id": str(node.id),
                            "name": node.name,
                            "description": node.description,
                            "sector": node.dominant_sector_code,
                            "importance": node.importance_level,
                            "keywords": ",".join(node.keywords),
                            "source_type": node.source_type,
                            "created_at": node.created_at.isoformat(),
                        }
                    ),
                },
            )
            logger.debug(f"节点 {node.id} 已加入同步队列")

        await self.db.commit()
        return node

    async def create_node_relation(
        self,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        relation_type: str,
        strength: float = 0.5,
        created_by: str = "user",
    ) -> NodeRelation:
        """
        创建节点关系（双写）

        Returns:
            PostgreSQL 关系对象
        """
        # 1. 写入 Postgres
        relation = NodeRelation(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            strength=strength,
            created_by=created_by,
            created_at=_utcnow(),
        )

        self.db.add(relation)
        await self.db.flush()

        # 2. 异步写入 AGE
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "relation_created",
                    "data": json.dumps(
                        {
                            "source": str(source_node_id),
                            "target": str(target_node_id),
                            "type": relation_type,
                            "strength": strength,
                            "created_by": created_by,
                        }
                    ),
                },
            )
            logger.debug(f"关系已加入同步队列: {source_node_id} → {target_node_id}")

        return relation

    async def update_node_status(
        self,
        user_id: uuid.UUID,
        node_id: uuid.UUID,
        study_minutes: int = 0,
        is_favorite: bool = False,
        mastery_delta: float = 0.0,
    ):
        """
        更新用户节点状态（同步到图）
        """
        # 调用原有服务
        await self.vector_service.update_node_status(
            user_id=user_id,
            node_id=node_id,
            study_minutes=study_minutes,
            is_favorite=is_favorite,
            mastery_delta=mastery_delta,
        )

        # 同步到图数据库
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "user_status_updated",
                    "data": json.dumps(
                        {
                            "user_id": str(user_id),
                            "node_id": str(node_id),
                            "study_minutes": study_minutes,
                            "is_favorite": is_favorite,
                            "mastery_delta": mastery_delta,
                            "timestamp": _utcnow().isoformat(),
                        }
                    ),
                },
            )

    async def graph_rag_search(
        self,
        query: str,
        # wt297: 监控端点以 user_id=None 做无主测试查询（调用契约即 Optional）。
        user_id: uuid.UUID | None = None,
        depth: int = 2,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        GraphRAG 检索（增强版）

        Returns:
            {
                "context": "融合后的上下文",
                "vector_results": [...],
                "graph_results": [...],
                "metadata": {...}
            }
        """
        from app.orchestration.graph_rag import GraphRAGRetriever

        retriever = GraphRAGRetriever(self.vector_service)
        result = await retriever.retrieve(query, str(user_id), depth)

        return {
            "context": result.fused_context,
            "vector_results": result.vector_results,
            "graph_results": result.graph_results,
            "metadata": result.metadata,
        }

    async def get_learning_path(self, user_id: uuid.UUID, target_node_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        获取用户学习路径

        Returns:
            路径上的节点列表
        """
        # 获取用户当前水平
        user_nodes = await self.vector_service.get_user_nodes(user_id)
        if not user_nodes:
            return []

        # 找到用户最擅长的节点作为起点
        best_node = max(user_nodes, key=lambda x: x.mastery_score)
        start_name = best_node.node_name

        # 获取目标节点名称
        target_node = await self.db.get(KnowledgeNode, target_node_id)
        if not target_node:
            return []

        # 使用 GraphRAG 查找路径
        from app.orchestration.graph_rag import GraphRAGRetriever

        retriever = GraphRAGRetriever(self.vector_service)

        path = await retriever.find_learning_path(start_name, target_node.name, user_id=str(user_id))
        return path

    async def get_related_knowledge(
        self,
        node_id: uuid.UUID,
        limit: int = 10,
        user_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取相关知识（用于知识拓展）

        Args:
            node_id: 起始节点 ID
            limit: 返回数量
            user_id: 调用方用户 ID — 必传以启用 GraphRAG 跨租户隔离 (R5-P0-6)。

        Returns:
            相关知识列表
        """
        node = await self.db.get(KnowledgeNode, node_id)
        if not node:
            return []

        from app.orchestration.graph_rag import GraphRAGRetriever

        retriever = GraphRAGRetriever(self.vector_service)

        related = await retriever.find_related_concepts(node.name, limit, user_id=str(user_id) if user_id else None)
        return related

    async def get_user_interest_graph(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        获取用户兴趣图谱

        Returns:
            用户兴趣相关的知识网络
        """
        try:
            cypher = """
            MATCH (u:User {id: $user_id})-[r]->(k:KnowledgeNode)
            WHERE type(r) IN ["INTERESTED_IN", "STUDIED"]
            OPTIONAL MATCH (k)-[related]-(other)
            WHERE related IS NULL OR type(related) IN ["RELATED", "PREREQUISITE"]
            RETURN {
                core: k.name,
                sector: k.sector,
                related: collect(DISTINCT other.name),
                relation_types: collect(DISTINCT type(related))
            } as result
            """

            results = await self.age_client.execute_cypher(cypher, {"user_id": str(user_id)})

            return {"user_id": str(user_id), "interests": results}

        except Exception as e:
            logger.warning(f"获取兴趣图谱失败: {e}")
            return {"error": str(e)}

    async def sync_all_to_age(self):
        """
        全量同步（一次性任务）

        用于初始迁移或数据修复
        """
        logger.info("开始全量同步到 AGE...")

        # 同步节点
        offset = 0
        batch_size = 100

        while True:
            result = await self.db.execute(select(KnowledgeNode).limit(batch_size).offset(offset))
            nodes = result.scalars().all()

            if not nodes:
                break

            for node in nodes:
                await self._sync_node_to_age(node)

            offset += batch_size
            logger.info(f"已同步 {offset} 个节点...")

        # 同步关系
        offset = 0
        while True:
            result = await self.db.execute(select(NodeRelation).limit(batch_size).offset(offset))
            relations = result.scalars().all()

            if not relations:
                break

            for rel in relations:
                await self._sync_relation_to_age(rel)

            offset += batch_size
            logger.info(f"已同步 {offset} 条关系...")

        logger.info("全量同步完成")

    async def _sync_node_to_age(self, node: KnowledgeNode):
        """同步单个节点到 AGE"""
        try:
            vertex = KnowledgeVertex(
                id=str(node.id),
                name=node.name,
                description=node.description or "",
                importance=node.importance_level or 1,
                sector=dominant_sector_from_weights(node.sector_weights or {}).value,
                keywords=node.keywords or [],
                source_type=node.source_type or "seed",
                created_at=node.created_at,
            )

            await self.age_client.add_vertex("KnowledgeNode", vertex.to_dict())
        except Exception as e:
            logger.warning(f"同步节点到 AGE 失败 {node.id}: {e}")

    async def _sync_relation_to_age(self, rel: NodeRelation):
        """同步单个关系到 AGE"""
        try:
            await self.age_client.add_edge(
                from_label="KnowledgeNode",
                from_props={"id": str(rel.source_node_id)},
                to_label="KnowledgeNode",
                to_props={"id": str(rel.target_node_id)},
                edge_label=rel.relation_type.upper(),
                edge_props={"strength": str(rel.strength), "created_by": rel.created_by or "seed"},
            )
        except Exception as e:
            logger.warning(f"同步关系到 AGE 失败 {rel.id}: {e}")
