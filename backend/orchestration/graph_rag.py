"""
GraphRAG 检索器

结合向量检索和图检索，提供增强的知识检索能力
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import json

from app.core.age_client import get_age_client
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import llm_service


@dataclass
class GraphRAGResult:
    """GraphRAG 检索结果"""
    query: str
    entities: List[str]
    vector_results: List[Dict[str, Any]]
    graph_results: List[Dict[str, Any]]
    fused_context: str
    metadata: Dict[str, Any]


class GraphRAGRetriever:
    """GraphRAG 检索器"""

    def __init__(self, knowledge_service: KnowledgeService):
        self.age_client = get_age_client()
        self.knowledge_service = knowledge_service
        self.max_depth = 2
        self.min_strength = 0.3

    async def extract_entities(self, query: str) -> List[str]:
        """
        使用 LLM 从查询中提取实体

        Args:
            query: 用户查询

        Returns:
            实体名称列表
        """
        prompt = f"""
        从以下查询中提取知识实体名称，返回 JSON 数组。
        只提取明确的知识点、概念或领域名称。

        查询: {query}

        示例:
        查询: "学习量子计算需要什么前置知识"
        返回: ["量子计算"]

        查询: "Python 和 Java 的区别"
        返回: ["Python", "Java"]

        返回格式 (JSON):
        """

        try:
            response = await llm_service.chat(prompt)
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

    async def _simple_extract(self, query: str) -> List[str]:
        """简单关键词提取（降级）"""
        # 这里可以使用简单的 NLP 或关键词提取
        # 暂时返回空，由后续处理
        return []

    async def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
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

    async def graph_search(self, entities: List[str], depth: int = 2) -> List[Dict[str, Any]]:
        """
        图检索（结构关联）

        Args:
            entities: 实体列表
            depth: 搜索深度

        Returns:
            检索结果
        """
        if not entities:
            return []

        results = []

        for entity in entities:
            try:
                # 查找实体及其关联知识
                cypher = f"""
                MATCH (start:KnowledgeNode {{name: $entity}})
                -[r*1..{depth}]-(related)
                WHERE ALL(edge IN r WHERE edge.strength > $min_strength)
                RETURN
                    related.id as id,
                    related.name as name,
                    related.description as description,
                    type(r[0]) as relation_type,
                    r[0].strength as strength,
                    related.sector as sector
                ORDER BY r[0].strength DESC
                LIMIT 10
                """

                result = await self.age_client.execute_cypher(
                    cypher,
                    {"entity": entity, "min_strength": self.min_strength}
                )

                # 添加元数据
                for item in result:
                    item["source"] = "graph"
                    item["query_entity"] = entity

                results.extend(result)

            except Exception as e:
                logger.warning(f"图检索失败 for {entity}: {e}")

        logger.debug(f"图检索: {len(results)} 条结果")
        return results

    async def get_user_interests(self, user_id: str) -> List[str]:
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
            RETURN DISTINCT k.name as name
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

    def fuse_results(self, vector_results: List[Dict], graph_results: List[Dict],
                     user_interests: List[str]) -> Tuple[str, List[Dict]]:
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

    async def retrieve(self, query: str, user_id: str, depth: int = 2) -> GraphRAGResult:
        """
        GraphRAG 主检索流程

        Args:
            query: 用户查询
            user_id: 用户ID
            depth: 图搜索深度

        Returns:
            GraphRAGResult
        """
        logger.info(f"GraphRAG 检索: query='{query}', user='{user_id}'")

        # 1. 实体识别
        entities = await self.extract_entities(query)

        # 2. 向量检索 (语义相似)
        vector_results = await self.vector_search(query, top_k=5)

        # 3. 图检索 (结构关联)
        graph_results = await self.graph_search(entities, depth)

        # 4. 用户个性化
        user_interests = await self.get_user_interests(user_id)

        # 5. 融合与去重
        fused_context, unique_results = self.fuse_results(
            vector_results, graph_results, user_interests
        )

        # 6. 构建元数据
        metadata = {
            "vector_count": len(vector_results),
            "graph_count": len(graph_results),
            "fusion_count": len(unique_results),
            "entities": entities,
            "user_interests": user_interests,
            "query": query
        }

        result = GraphRAGResult(
            query=query,
            entities=entities,
            vector_results=vector_results,
            graph_results=graph_results,
            fused_context=fused_context,
            metadata=metadata
        )

        logger.info(
            f"GraphRAG 完成: vector={len(vector_results)}, "
            f"graph={len(graph_results)}, fused={len(unique_results)}"
        )

        return result

    async def find_learning_path(self, start_node: str, target_node: str) -> List[Dict[str, Any]]:
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
            RETURN
                node.name as name,
                node.description as description,
                node.importance as importance
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

    async def find_related_concepts(self, concept: str, limit: int = 10) -> List[Dict[str, Any]]:
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
            RETURN
                related.name as name,
                related.description as description,
                type(r) as relation,
                r.strength as strength
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
