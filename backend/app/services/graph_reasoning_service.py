"""
Graph Reasoning Service (Neuro-Symbolic AI)
基于 NetworkX 的动态学习路径生成引擎

Features:
- Redis 缓存图结构，避免每次请求全量加载
- 循环检测预处理
- 个性化学习路径生成
"""
from __future__ import annotations

import pickle
from typing import Any, TypedDict
from uuid import UUID

import networkx as nx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus


class LearningPathNode(TypedDict):
    """学习路径节点类型"""
    id: str
    name: str
    status: str  # mastered, unlocked, locked
    is_target: bool


class LearningPathError(TypedDict):
    """学习路径错误类型"""
    error: str
    error_code: str
    message: str
    details: dict[str, Any] | None


class GraphReasoningService:
    """图推理服务，负责学习路径生成和图结构管理"""

    # Redis 缓存配置
    CACHE_KEY = "galaxy:graph_structure:v2"
    CACHE_TTL = 300  # 5分钟

    def __init__(self, db: AsyncSession):
        self.db = db
        self.G: nx.DiGraph | None = None

    async def _load_graph(self) -> None:
        """
        从缓存或数据库加载图结构到 NetworkX

        加载顺序:
        1. 检查内存缓存 (self.G)
        2. 尝试从 Redis 获取序列化的图
        3. 从数据库加载并缓存到 Redis
        """
        if self.G is not None:
            return

        # 1. 尝试从 Redis 获取序列化的图
        try:
            cached = await cache_service.get(self.CACHE_KEY)
            if cached:
                # cache_service.get() 返回的是 JSON 反序列化后的对象
                # 对于 pickle 序列化的 bytes，需要直接从 redis 获取
                if cache_service.redis:
                    raw_cached = await cache_service.redis.get(self.CACHE_KEY)
                    if raw_cached:
                        self.G = pickle.loads(raw_cached)
                        logger.info(
                            f"Graph loaded from Redis cache: {self.G.number_of_nodes()} nodes, "
                            f"{self.G.number_of_edges()} edges"
                        )
                        return
        except Exception as e:
            logger.warning(f"Failed to load graph from Redis cache: {e}")

        # 2. 从数据库加载
        self.G = nx.DiGraph()

        # 加载所有节点
        nodes_result = await self.db.execute(select(KnowledgeNode))
        nodes = nodes_result.scalars().all()
        for node in nodes:
            self.G.add_node(node.id, name=node.name, description=node.description)

        # 兼容历史数据里大小写不一致的 prerequisite 关系类型。
        edges_result = await self.db.execute(
            select(NodeRelation).where(func.lower(NodeRelation.relation_type) == "prerequisite")
        )
        edges = edges_result.scalars().all()

        edge_list = [(edge.source_node_id, edge.target_node_id) for edge in edges]
        self.G.add_edges_from(edge_list)

        logger.info(
            f"Graph loaded from database: {self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges"
        )

        # 3. 缓存到 Redis
        try:
            if cache_service.redis:
                serialized = pickle.dumps(self.G, protocol=5)
                await cache_service.redis.set(
                    self.CACHE_KEY,
                    serialized,
                    ex=self.CACHE_TTL
                )
                logger.debug(f"Graph cached to Redis with TTL={self.CACHE_TTL}s")
        except Exception as e:
            logger.warning(f"Failed to cache graph to Redis: {e}")

    async def invalidate_cache(self) -> None:
        """
        清除图缓存，在节点/边变更时调用

        使用场景:
        - 创建/删除知识节点
        - 创建/删除节点关系
        - 图结构发生变更
        """
        try:
            if cache_service.redis:
                await cache_service.redis.delete(self.CACHE_KEY)
                logger.info("Graph cache invalidated in Redis")
        except Exception as e:
            logger.warning(f"Failed to invalidate graph cache: {e}")

        # 强制下次重新加载
        self.G = None

    async def generate_learning_path(
        self, user_id: UUID, target_node_id: UUID
    ) -> list[dict[str, Any]]:
        """
        生成个性化学习路径

        Algorithm:
        1. 获取目标节点的所有祖先 (Ancestors)
        2. 构建子图
        3. 循环检测预处理
        4. 拓扑排序
        5. 标记节点状态（mastered/unlocked/locked）

        Returns:
            成功: list[LearningPathNode]
            失败: list[LearningPathError] (单元素列表)
        """
        await self._load_graph()

        if not self.G.has_node(target_node_id):
            logger.warning(f"Target node {target_node_id} not found in graph")
            return [{
                "error": "target_not_found",
                "error_code": "TARGET_NOT_FOUND",
                "message": f"目标节点 {target_node_id} 不存在于知识图谱中",
                "details": {"target_node_id": str(target_node_id)}
            }]

        # 1. 获取所有前置依赖 (Ancestors)
        try:
            ancestors = nx.ancestors(self.G, target_node_id)
        except Exception as e:
            logger.error(f"Error finding ancestors: {e}")
            return [{
                "error": "graph_error",
                "error_code": "GRAPH_ERROR",
                "message": "图结构查询失败",
                "details": {"exception": str(e)}
            }]

        # 包含目标节点本身
        subgraph_nodes = ancestors | {target_node_id}

        # 2. 提取子图
        subgraph = self.G.subgraph(subgraph_nodes)

        # 3. 循环检测预处理 - 在拓扑排序前检测
        if not nx.is_directed_acyclic_graph(subgraph):
            cycles = list(nx.simple_cycles(subgraph))
            cycle_count = len(cycles)
            # 只记录前3个循环，避免日志过大
            logger.error(
                f"Cycle detected in prerequisite graph! "
                f"Total cycles: {cycle_count}, Examples: {cycles[:3]}"
            )
            return [{
                "error": "cyclic_dependency",
                "error_code": "CYCLIC_DEPENDENCY",
                "message": "检测到循环依赖，知识图谱结构异常，请联系管理员修复",
                "details": {
                    "cycle_count": cycle_count,
                    "sample_cycles": [[str(n) for n in c] for c in cycles[:3]]
                }
            }]

        # 4. 拓扑排序 (Topological Sort) - 线性化 DAG
        try:
            path_nodes_ids = list(nx.topological_sort(subgraph))
        except nx.NetworkXUnfeasible as e:
            # 理论上不应该到达这里（因为已经做了循环检测），但作为保险
            logger.error(f"Unexpected topological sort failure: {e}")
            return [{
                "error": "topological_sort_failed",
                "error_code": "TOPOLOGICAL_SORT_FAILED",
                "message": "学习路径排序失败",
                "details": {"exception": str(e)}
            }]

        # 5. 获取用户已掌握的节点 (Mastered Nodes)
        mastered_ids = await self._get_user_mastered_ids(user_id)

        # 6. 构建最终路径 (Formatting with status)
        final_path: list[dict[str, Any]] = []
        for node_id in path_nodes_ids:
            node_data = self.G.nodes[node_id]
            is_mastered = node_id in mastered_ids

            status = "mastered" if is_mastered else "locked"
            # 解锁逻辑：如果该节点的所有前置都已掌握，则为 "unlocked"
            if not is_mastered:
                predecessors = list(self.G.predecessors(node_id))
                if all(p in mastered_ids for p in predecessors):
                    status = "unlocked"

            final_path.append({
                "id": str(node_id),
                "name": node_data.get("name", "Unknown"),
                "status": status,  # mastered, unlocked, locked
                "is_target": node_id == target_node_id,
            })

        return final_path

    async def _get_user_mastered_ids(self, user_id: UUID) -> set[UUID]:
        """获取用户掌握度 > 80 的节点 ID"""
        result = await self.db.execute(
            select(UserNodeStatus.node_id).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.mastery_score >= 80,  # Threshold for mastery
            )
        )
        return set(result.scalars().all())

    def get_node_edge_count(self, node_id: UUID) -> int:
        """获取节点的边数（入度+出度）"""
        if not self.G or not self.G.has_node(node_id):
            return 0
        in_degree = self.G.in_degree(node_id)
        out_degree = self.G.out_degree(node_id)
        return in_degree + out_degree

    def get_node_description(self, node_id: UUID) -> str:
        """获取节点描述"""
        if not self.G or not self.G.has_node(node_id):
            return ""
        node_data = self.G.nodes[node_id]
        return node_data.get("description", "")
