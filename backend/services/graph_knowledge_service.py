"""
增强的知识服务 - 支持双写和 GraphRAG

在原有 KnowledgeService 基础上增加图数据库支持
"""

import asyncio
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.age_client import get_age_client
from app.models.knowledge import KnowledgeNode, NodeRelation
from app.models.graph_models import KnowledgeVertex, RelationEdge
from app.services.knowledge_service import KnowledgeService
from app.core.cache import cache_service


class GraphKnowledgeService:
    """
    增强的知识服务

    特性:
    - 双写: Postgres + AGE
    - GraphRAG 检索
    - 缓存优化
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.age_client = get_age_client()
        self.vector_service = KnowledgeService(db)
        self.redis = cache_service.redis

    async def create_knowledge_node(
        self,
        name: str,
        description: str,
        sector_code: str = "VOID",
        importance_level: int = 1,
        keywords: List[str] = None,
        source_type: str = "user_created",
        source_task_id: Optional[uuid.UUID] = None
    ) -> KnowledgeNode:
        """
        创建知识节点（双写）

        Returns:
            PostgreSQL 节点对象
        """
        if keywords is None:
            keywords = []

        # 1. 写入 Postgres
        node = KnowledgeNode(
            id=uuid.uuid4(),
            name=name,
            description=description,
            sector_code=sector_code,
            importance_level=importance_level,
            keywords=keywords,
            source_type=source_type,
            source_task_id=source_task_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(node)
        await self.db.flush()

        # 2. 异步写入 AGE（通过 Redis 队列）
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "node_created",
                    "data": json.dumps({
                        "id": str(node.id),
                        "name": node.name,
                        "description": node.description,
                        "sector": node.sector_code,
                        "importance": node.importance_level,
                        "keywords": ",".join(node.keywords),
                        "source_type": node.source_type,
                        "created_at": node.created_at.isoformat()
                    })
                }
            )
            logger.debug(f"节点 {node.id} 已加入同步队列")

        return node

    async def create_node_relation(
        self,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        relation_type: str,
        strength: float = 0.5,
        created_by: str = "user"
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
            created_at=datetime.utcnow()
        )

        self.db.add(relation)
        await self.db.flush()

        # 2. 异步写入 AGE
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "relation_created",
                    "data": json.dumps({
                        "source": str(source_node_id),
                        "target": str(target_node_id),
                        "type": relation_type,
                        "strength": strength,
                        "created_by": created_by
                    })
                }
            )
            logger.debug(f"关系已加入同步队列: {source_node_id} → {target_node_id}")

        return relation

    async def update_node_status(
        self,
        user_id: uuid.UUID,
        node_id: uuid.UUID,
        study_minutes: int = 0,
        is_favorite: bool = False,
        mastery_delta: float = 0.0
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
            mastery_delta=mastery_delta
        )

        # 同步到图数据库
        if self.redis:
            await self.redis.xadd(
                "stream:graph_sync",
                {
                    "type": "user_status_updated",
                    "data": json.dumps({
                        "user_id": str(user_id),
                        "node_id": str(node_id),
                        "study_minutes": study_minutes,
                        "is_favorite": is_favorite,
                        "mastery_delta": mastery_delta,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
            )

    async def graph_rag_search(
        self,
        query: str,
        user_id: uuid.UUID,
        depth: int = 2,
        top_k: int = 5
    ) -> Dict[str, Any]:
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
            "metadata": result.metadata
        }

    async def get_learning_path(
        self,
        user_id: uuid.UUID,
        target_node_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
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

        path = await retriever.find_learning_path(start_name, target_node.name)
        return path

    async def get_related_knowledge(
        self,
        node_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取相关知识（用于知识拓展）

        Returns:
            相关知识列表
        """
        node = await self.db.get(KnowledgeNode, node_id)
        if not node:
            return []

        from app.orchestration.graph_rag import GraphRAGRetriever
        retriever = GraphRAGRetriever(self.vector_service)

        related = await retriever.find_related_concepts(node.name, limit)
        return related

    async def get_user_interest_graph(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        获取用户兴趣图谱

        Returns:
            用户兴趣相关的知识网络
        """
        try:
            cypher = """
            MATCH (u:User {id: $user_id})-[r:INTERESTED_IN|STUDIED]->(k:KnowledgeNode)
            OPTIONAL MATCH (k)-[related:RELATED|PREREQUISITE]-(other)
            RETURN
                k.name as core,
                k.sector as sector,
                collect(DISTINCT other.name) as related,
                collect(DISTINCT type(related)) as relation_types
            """

            results = await self.age_client.execute_cypher(
                cypher,
                {"user_id": str(user_id)}
            )

            return {
                "user_id": str(user_id),
                "interests": results
            }

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
            result = await self.db.execute(
                select(KnowledgeNode)
                .limit(batch_size)
                .offset(offset)
            )
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
            result = await self.db.execute(
                select(NodeRelation)
                .limit(batch_size)
                .offset(offset)
            )
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
                sector=node.sector_code or "VOID",
                keywords=node.keywords or [],
                source_type=node.source_type or "seed",
                created_at=node.created_at
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
                edge_props={
                    "strength": str(rel.strength),
                    "created_by": rel.created_by or "seed"
                }
            )
        except Exception as e:
            logger.warning(f"同步关系到 AGE 失败 {rel.id}: {e}")
