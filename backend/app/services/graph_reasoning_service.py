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
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus


class LearningPathNode(TypedDict):
    """学习路径节点类型"""
    id: str
    name: str
    status: str  # mastered, unlocked, locked
    is_target: bool
    is_optional: bool
    relation_type: str | None
    source_type: str | None


class LearningPathError(TypedDict):
    """学习路径错误类型"""
    error: str
    error_code: str
    message: str
    details: dict[str, Any] | None


class GraphReasoningService:
    """图推理服务，负责学习路径生成和图结构管理"""

    # Redis 缓存配置
    CACHE_KEY = "galaxy:graph_structure:v3"
    CACHE_TTL = 300  # 5分钟
    SUPPORT_RELATION_TYPES = {"related", "application", "evolution", "composition"}

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
            self.G.add_node(
                node.id,
                name=node.name,
                description=node.description,
                source_type=node.source_type,
            )

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
        self,
        user_id: UUID,
        target_node_id: UUID,
        *,
        include_related_suggestions: bool = False,
        selected_related_node_ids: list[UUID] | None = None,
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
        mastery_map = await self._get_user_mastery_map(user_id)
        mastered_ids = {node_id for node_id, mastery in mastery_map.items() if mastery >= 80}

        # 6. 构建最终路径 (Formatting with status)
        final_path: list[dict[str, Any]] = []
        for node_id in path_nodes_ids:
            final_path.append(
                self._build_path_node_payload(
                    node_id=node_id,
                    mastered_ids=mastered_ids,
                    is_target=node_id == target_node_id,
                )
            )

        related_nodes = await self._build_related_nodes(
            user_id=user_id,
            target_node_id=target_node_id,
            backbone_node_ids=path_nodes_ids,
            mastered_ids=mastered_ids,
            include_related_suggestions=include_related_suggestions,
            selected_related_node_ids=selected_related_node_ids or [],
        )
        if related_nodes:
            final_path.extend(related_nodes)

        return final_path

    async def build_diagnostic_snapshot(
        self,
        user_id: UUID,
        *,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Build a read-only graph diagnostic view of the user's weakest nodes."""
        await self._load_graph()

        stmt = (
            select(UserNodeStatus, KnowledgeNode.name)
            .join(KnowledgeNode, KnowledgeNode.id == UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user_id)
            .where(UserNodeStatus.is_unlocked.is_(True))
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        if not rows:
            return {
                "status": "empty",
                "summary": "当前还没有足够的星图掌握度数据来判断哪里最弱。",
                "weak_nodes": [],
                "at_risk_nodes": [],
                "recommended_next_review": [],
                "graph_basis": {
                    "source": "graph_reasoning_service",
                    "mode": "read_only_diagnostic",
                },
            }

        ranked: list[dict[str, Any]] = []
        for status, node_name in rows:
            node_id = str(status.node_id)
            mastery = float(status.mastery_score or 0.0)
            predecessors = []
            successors = []
            if self.G is not None and self.G.has_node(status.node_id):
                predecessors = list(self.G.predecessors(status.node_id))[:3]
                successors = list(self.G.successors(status.node_id))[:3]
            predecessor_names = [
                str(self.G.nodes[item].get("name") or item)
                for item in predecessors
                if self.G is not None and self.G.has_node(item)
            ]
            successor_names = [
                str(self.G.nodes[item].get("name") or item)
                for item in successors
                if self.G is not None and self.G.has_node(item)
            ]
            if mastery < 45:
                status_label = "weak"
                why = "掌握度已经落到明显偏低区间，优先复习更划算。"
            elif mastery < 65:
                status_label = "at_risk"
                why = "还没掉到最弱，但已经接近会拖慢后续路径的风险区。"
            elif mastery < 80:
                status_label = "learning"
                why = "还在学习区间，需要再巩固一次才能更稳。"
            else:
                status_label = "strong"
                why = "当前掌握度相对稳定。"

            ranked.append(
                {
                    "node_id": node_id,
                    "node_name": str(node_name or node_id),
                    "mastery": round(mastery, 1),
                    "status": status_label,
                    "why": why,
                    "prerequisite_names": predecessor_names,
                    "downstream_names": successor_names,
                    "route": f"/galaxy/node/{node_id}",
                    "prompt": f"带我看看「{node_name}」为什么会成为当前薄弱点。",
                }
            )

        ranked.sort(key=lambda item: (float(item["mastery"]), item["node_name"]))
        weak_nodes = [item for item in ranked if item["status"] == "weak"][:limit]
        at_risk_nodes = [item for item in ranked if item["status"] == "at_risk"][:limit]
        recommended = (weak_nodes or at_risk_nodes or ranked[:limit])[:limit]

        summary = "当前最该先补的，是这些掌握度最低且会影响后续路径的知识点。"
        if weak_nodes:
            summary = f"当前最弱的点有 {len(weak_nodes)} 个，最该先补的是「{weak_nodes[0]['node_name']}」。"
        elif at_risk_nodes:
            summary = f"当前没有明显掉到底的薄弱点，但「{at_risk_nodes[0]['node_name']}」已经进入风险区。"

        return {
            "status": "ok",
            "summary": summary,
            "weak_nodes": weak_nodes,
            "at_risk_nodes": at_risk_nodes,
            "recommended_next_review": recommended,
            "graph_basis": {
                "source": "graph_reasoning_service",
                "mode": "read_only_diagnostic",
                "thresholds": {
                    "weak_below": 45,
                    "at_risk_below": 65,
                    "strong_at_or_above": 80,
                },
            },
        }

    async def _get_user_mastery_map(self, user_id: UUID) -> dict[UUID, float]:
        """获取用户节点掌握度映射"""
        result = await self.db.execute(
            select(UserNodeStatus.node_id, UserNodeStatus.mastery_score).where(UserNodeStatus.user_id == user_id)
        )
        return {node_id: float(mastery or 0) for node_id, mastery in result.all()}

    def _build_path_node_payload(
        self,
        *,
        node_id: UUID,
        mastered_ids: set[UUID],
        is_target: bool,
        is_optional: bool = False,
        relation_type: str | None = None,
    ) -> dict[str, Any]:
        node_data = self.G.nodes[node_id]
        is_mastered = node_id in mastered_ids

        status = "mastered" if is_mastered else "locked"
        if not is_mastered:
            predecessors = list(self.G.predecessors(node_id))
            if all(p in mastered_ids for p in predecessors):
                status = "unlocked"

        return {
            "id": str(node_id),
            "name": node_data.get("name", "Unknown"),
            "status": status,
            "is_target": is_target,
            "is_optional": is_optional,
            "relation_type": relation_type,
            "source_type": node_data.get("source_type"),
        }

    async def _build_related_nodes(
        self,
        *,
        user_id: UUID,
        target_node_id: UUID,
        backbone_node_ids: list[UUID],
        mastered_ids: set[UUID],
        include_related_suggestions: bool,
        selected_related_node_ids: list[UUID],
    ) -> list[dict[str, Any]]:
        if not include_related_suggestions and not selected_related_node_ids:
            return []

        selected_set = set(selected_related_node_ids)
        suggested_candidates: list[tuple[UUID, str | None]] = []
        if include_related_suggestions:
            suggested_candidates = await self._suggest_related_candidates(
                target_node_id=target_node_id,
                backbone_node_ids=backbone_node_ids,
                mastered_ids=mastered_ids,
            )

        suggested_map = {node_id: relation_type for node_id, relation_type in suggested_candidates}
        ordered_related_ids: list[UUID] = []

        for node_id in selected_related_node_ids:
            if node_id not in ordered_related_ids:
                ordered_related_ids.append(node_id)

        for node_id, _ in suggested_candidates:
            if node_id not in ordered_related_ids:
                ordered_related_ids.append(node_id)

        related_nodes: list[dict[str, Any]] = []
        for node_id in ordered_related_ids:
            if node_id in backbone_node_ids or not self.G.has_node(node_id):
                continue

            relation_type = suggested_map.get(node_id)
            if relation_type is None:
                relation_type = await self._lookup_support_relation_type(node_id, backbone_node_ids)

            related_nodes.append(
                self._build_path_node_payload(
                    node_id=node_id,
                    mastered_ids=mastered_ids,
                    is_target=False,
                    is_optional=True,
                    relation_type=relation_type,
                )
            )

        return related_nodes

    async def _suggest_related_candidates(
        self,
        *,
        target_node_id: UUID,
        backbone_node_ids: list[UUID],
        mastered_ids: set[UUID],
        limit: int = 4,
    ) -> list[tuple[UUID, str | None]]:
        focus_node_ids = list(dict.fromkeys([target_node_id, *backbone_node_ids[-2:]]))
        result = await self.db.execute(
            select(NodeRelation, KnowledgeNode)
            .join(
                KnowledgeNode,
                or_(
                    and_(
                        NodeRelation.source_node_id.in_(focus_node_ids),
                        NodeRelation.target_node_id == KnowledgeNode.id,
                    ),
                    and_(
                        NodeRelation.target_node_id.in_(focus_node_ids),
                        NodeRelation.source_node_id == KnowledgeNode.id,
                    ),
                ),
            )
            .where(func.lower(NodeRelation.relation_type).in_(self.SUPPORT_RELATION_TYPES))
        )

        candidate_scores: dict[UUID, tuple[float, str | None]] = {}
        for relation, node in result.all():
            if node.id in mastered_ids or node.id in backbone_node_ids:
                continue

            relation_type = (relation.relation_type or "").lower() or None
            score = float(relation.strength or 0.5)
            score += {
                "application": 1.4,
                "evolution": 1.2,
                "related": 1.0,
                "composition": 0.8,
            }.get(relation_type or "", 0.0)
            if node.parent_id in focus_node_ids:
                score += 0.4
            if (node.source_type or "").lower() in {"llm_expanded", "llm_generated"}:
                score += 0.5

            existing = candidate_scores.get(node.id)
            if existing is None or score > existing[0]:
                candidate_scores[node.id] = (score, relation_type)

        ranked = sorted(candidate_scores.items(), key=lambda item: item[1][0], reverse=True)
        return [(node_id, relation_type) for node_id, (_, relation_type) in ranked[:limit]]

    async def _lookup_support_relation_type(
        self,
        node_id: UUID,
        backbone_node_ids: list[UUID],
    ) -> str | None:
        result = await self.db.execute(
            select(NodeRelation.relation_type)
            .where(
                or_(
                    and_(
                        NodeRelation.source_node_id.in_(backbone_node_ids),
                        NodeRelation.target_node_id == node_id,
                    ),
                    and_(
                        NodeRelation.target_node_id.in_(backbone_node_ids),
                        NodeRelation.source_node_id == node_id,
                    ),
                )
            )
            .order_by(NodeRelation.strength.desc())
            .limit(1)
        )
        relation_type = result.scalar_one_or_none()
        return relation_type.lower() if relation_type else None

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
