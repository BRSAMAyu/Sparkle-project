"""
知识拓展服务 (Expansion Service)
使用 LLM 自动拓展知识星图
"""
import json
from uuid import UUID
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, NodeExpansionQueue, NodeRelation, UserNodeStatus, ExpansionFeedback
from app.core.llm_client import llm_client
from app.services.embedding_service import embedding_service
from app.config import settings


class ExpansionService:
    """
    LLM 知识拓展服务

    当用户深入学习某个知识点后，自动拓展相关知识节点，
    实现知识星图的有机生长。
    """

    # 拓展限制
    MAX_EXPANDED_NODES_PER_REQUEST = 5  # 每次最多拓展 5 个节点
    MIN_STUDY_COUNT_FOR_EXPANSION = 2  # 至少学习 2 次才触发拓展
    EXPANSION_COOLDOWN_HOURS = 24  # 同一节点拓展冷却时间
    PROMPT_VERSIONS = ("v1", "v2", "v3")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_expansion(
        self,
        trigger_node_id: UUID,
        trigger_task_id: Optional[UUID],
        user_id: UUID
    ) -> bool:
        """
        将拓展请求加入队列

        Returns:
            bool: 是否成功加入队列
        """
        # 1. 检查是否满足拓展条件
        if not await self._should_expand(trigger_node_id, user_id):
            return False

        # 2. 收集拓展上下文
        context = await self._build_expansion_context(trigger_node_id, user_id)

        prompt_version = await self._select_prompt_version(trigger_node_id)

        # 3. 创建队列任务
        queue_item = NodeExpansionQueue(
            trigger_node_id=trigger_node_id,
            trigger_task_id=trigger_task_id,
            user_id=user_id,
            expansion_context=context,
            status='pending',
            prompt_version=prompt_version
        )

        self.db.add(queue_item)
        await self.db.commit()

        return True

    async def _should_expand(self, node_id: UUID, user_id: UUID) -> bool:
        """检查是否应该触发拓展"""
        # 检查最近是否已拓展过
        cooldown_time = datetime.utcnow() - timedelta(hours=self.EXPANSION_COOLDOWN_HOURS)

        query = select(NodeExpansionQueue).where(
            and_(
                NodeExpansionQueue.trigger_node_id == node_id,
                NodeExpansionQueue.user_id == user_id,
                NodeExpansionQueue.created_at > cooldown_time
            )
        )

        result = await self.db.execute(query)
        recent_expansion = result.scalar_one_or_none()

        return recent_expansion is None

    async def _build_expansion_context(self, node_id: UUID, user_id: UUID) -> str:
        """构建发送给 LLM 的拓展上下文"""
        # 获取触发节点
        node = await self.db.get(KnowledgeNode, node_id)

        # 获取相邻节点
        neighbors = await self._get_neighbor_nodes(node_id)

        # 获取用户已学习的节点 (避免重复推荐)
        learned_nodes = await self._get_user_learned_nodes(user_id)

        context = {
            "trigger_node": {
                "name": node.name,
                "description": node.description or "",
                "sector": node.subject.sector_code if node.subject else "VOID",
            },
            "neighbor_nodes": [
                {"name": n.name, "relation": rel}
                for n, rel in neighbors
            ],
            "already_learned": [n.name for n in learned_nodes],
        }

        return json.dumps(context, ensure_ascii=False)

    async def _get_neighbor_nodes(self, node_id: UUID, limit: int = 10) -> List[Tuple[KnowledgeNode, str]]:
        """获取节点的邻居节点"""
        from app.models.subject import Subject

        query = (
            select(KnowledgeNode, NodeRelation.relation_type)
            .join(
                NodeRelation,
                or_(
                    and_(NodeRelation.source_node_id == node_id, NodeRelation.target_node_id == KnowledgeNode.id),
                    and_(NodeRelation.target_node_id == node_id, NodeRelation.source_node_id == KnowledgeNode.id)
                )
            )
            .where(KnowledgeNode.id != node_id)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.all()

    async def _get_user_learned_nodes(self, user_id: UUID, limit: int = 50) -> List[KnowledgeNode]:
        """获取用户已学习的节点"""
        query = (
            select(KnowledgeNode)
            .join(UserNodeStatus)
            .where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.is_unlocked == True
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def process_expansion(self, queue_id: UUID) -> List[KnowledgeNode]:
        """
        处理拓展请求 (由 Worker 调用)

        Returns:
            List[KnowledgeNode]: 新创建的知识节点
        """
        # 1. 获取队列任务
        queue_item = await self.db.get(NodeExpansionQueue, queue_id)
        if not queue_item or queue_item.status != 'pending':
            return []

        # 2. 标记为处理中
        queue_item.status = 'processing'
        await self.db.commit()

        try:
            # 3. 调用 LLM
            prompt = self._build_expansion_prompt(queue_item.expansion_context, queue_item.prompt_version)
            model_name = settings.DEEPSEEK_CHAT_MODEL if settings.LLM_PROVIDER == "deepseek" else settings.LLM_MODEL_NAME
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                model=model_name
            )
            queue_item.model_name = model_name

            # 4. 解析响应
            expanded_data = self._parse_expansion_response(response)

            # 5. 创建新节点
            new_nodes = await self._create_expanded_nodes(
                expanded_data,
                trigger_node_id=queue_item.trigger_node_id,
                user_id=queue_item.user_id
            )

            # 6. 更新队列状态
            queue_item.status = 'completed'
            queue_item.expanded_nodes = json.dumps([
                {"id": str(n.id), "name": n.name} for n in new_nodes
            ], ensure_ascii=False)
            queue_item.processed_at = datetime.utcnow()
            await self.db.commit()

            return new_nodes

        except Exception as e:
            queue_item.status = 'failed'
            queue_item.error_message = str(e)
            await self.db.commit()
            raise

    def _build_expansion_prompt(self, context_json: str, prompt_version: Optional[str] = None) -> str:
        """构建拓展 Prompt"""
        context = json.loads(context_json)

        prompt_version = prompt_version or "v1"
        base_prompt = f"""你是一个知识图谱拓展专家。用户正在学习"{context['trigger_node']['name']}"这个知识点。

## 当前知识点信息
- 名称：{context['trigger_node']['name']}
- 描述：{context['trigger_node']['description']}
- 所属领域：{context['trigger_node']['sector']}

## 相邻知识点
{chr(10).join([f"- {n['name']} ({n['relation']})" for n in context['neighbor_nodes']]) if context['neighbor_nodes'] else "暂无"}

## 用户已学习的知识点
{', '.join(context['already_learned'][:20]) if context['already_learned'] else "暂无"}

## 任务
请推荐 3-5 个与"{context['trigger_node']['name']}"相关的、用户可能感兴趣的知识点。

要求：
1. 不要推荐用户已学习的知识点
2. 推荐的知识点应该是渐进式的，从简单到复杂
3. 包含理论深化和实际应用两个方向
4. 每个知识点需要说明与触发知识点的关系

## 输出格式 (JSON)
```json
{{
  "expanded_nodes": [
    {{
      "name": "知识点名称",
      "name_en": "English Name",
      "description": "简要描述 (50字以内)",
      "importance_level": 3,
      "relation_to_trigger": "prerequisite",
      "relation_strength": 0.8,
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}
```

relation_to_trigger 可选值: prerequisite (前置知识), related (相关), application (应用), evolution (进阶)
"""
        if prompt_version == "v2":
            return base_prompt + "\n额外要求：避免重复或过度相似的概念，确保每个节点的差异性。"
        if prompt_version == "v3":
            return base_prompt + "\n额外要求：优先推荐高价值概念，并简要标注学习收益（1-2句）。"
        return base_prompt

    def _parse_expansion_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            raise ValueError("Failed to parse LLM response as JSON")

    async def _create_expanded_nodes(
        self,
        expanded_data: dict,
        trigger_node_id: UUID,
        user_id: UUID
    ) -> List[KnowledgeNode]:
        """创建拓展的知识节点"""
        trigger_node = await self.db.get(KnowledgeNode, trigger_node_id)
        new_nodes = []

        for item in expanded_data.get('expanded_nodes', [])[:self.MAX_EXPANDED_NODES_PER_REQUEST]:
            # 检查是否已存在 (通过名称去重)
            existing = await self._find_existing_node(item['name'])
            if existing:
                # 如果已存在，只创建关系
                await self._ensure_relation(trigger_node_id, existing.id, item)
                continue

            # 语义去重
            if settings.EXPANSION_SEMANTIC_DEDUP_ENABLED:
                dedup_candidate = await self._find_semantic_duplicate(item)
                if dedup_candidate:
                    await self._ensure_relation(trigger_node_id, dedup_candidate.id, item)
                    continue

            # 创建新节点
            node = KnowledgeNode(
                subject_id=trigger_node.subject_id,
                parent_id=trigger_node_id,
                name=item['name'],
                name_en=item.get('name_en'),
                description=item.get('description'),
                importance_level=item.get('importance_level', 3),
                is_seed=False,
                source_type='llm_generated',
                keywords=item.get('keywords', [])
            )

            # 生成向量嵌入
            if node.description:
                embedding_text = f"{node.name} {node.description}"
                node.embedding = await embedding_service.get_embedding(embedding_text)

            self.db.add(node)
            await self.db.flush()  # 获取 node.id

            # 创建关系
            relation = NodeRelation(
                source_node_id=trigger_node_id,
                target_node_id=node.id,
                relation_type=item.get('relation_to_trigger', 'related'),
                strength=item.get('relation_strength', 0.7)
            )
            self.db.add(relation)

            new_nodes.append(node)

        await self.db.commit()
        return new_nodes

    async def _find_semantic_duplicate(self, item: dict) -> Optional[KnowledgeNode]:
        """基于向量的语义去重"""
        embedding_text = f"{item.get('name', '')} {item.get('description', '')}".strip()
        if not embedding_text:
            return None

        embedding = await embedding_service.get_embedding(embedding_text)
        distance_label = KnowledgeNode.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(KnowledgeNode, distance_label)
            .where(KnowledgeNode.embedding.isnot(None))
            .order_by(distance_label)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None
        node, distance = row
        if distance is not None and float(distance) <= settings.EXPANSION_SEMANTIC_DEDUP_THRESHOLD:
            return node
        return None

    async def _select_prompt_version(self, trigger_node_id: UUID) -> str:
        """Select prompt version based on feedback stats."""
        if not settings.EXPANSION_AB_TEST_ENABLED:
            return "v1"

        stmt = (
            select(
                ExpansionFeedback.prompt_version,
                func.avg(ExpansionFeedback.rating).label("avg_rating"),
                func.count().label("count")
            )
            .where(ExpansionFeedback.trigger_node_id == trigger_node_id)
            .group_by(ExpansionFeedback.prompt_version)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        if rows:
            best = max(rows, key=lambda r: (r.avg_rating or 0, r.count))
            if best.prompt_version:
                return best.prompt_version

        # Deterministic fallback
        index = int(trigger_node_id.int % len(self.PROMPT_VERSIONS))
        return self.PROMPT_VERSIONS[index]

    async def record_feedback(
        self,
        user_id: UUID,
        trigger_node_id: UUID,
        expansion_queue_id: Optional[UUID],
        rating: Optional[int],
        implicit_score: Optional[float],
        feedback_type: str,
        prompt_version: Optional[str],
        metadata: Optional[dict]
    ) -> UUID:
        """Record feedback for expansion quality."""
        if not prompt_version and expansion_queue_id:
            queue_item = await self.db.get(NodeExpansionQueue, expansion_queue_id)
            if queue_item:
                prompt_version = queue_item.prompt_version

        feedback = ExpansionFeedback(
            expansion_queue_id=expansion_queue_id,
            trigger_node_id=trigger_node_id,
            user_id=user_id,
            rating=rating,
            implicit_score=implicit_score,
            feedback_type=feedback_type,
            prompt_version=prompt_version,
            model_name=settings.DEEPSEEK_CHAT_MODEL if settings.LLM_PROVIDER == "deepseek" else settings.LLM_MODEL_NAME,
            metadata=metadata or {}
        )
        self.db.add(feedback)
        await self.db.commit()
        return feedback.id

    async def _find_existing_node(self, name: str) -> Optional[KnowledgeNode]:
        """查找已存在的节点"""
        query = select(KnowledgeNode).where(KnowledgeNode.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _ensure_relation(self, source_id: UUID, target_id: UUID, item: dict):
        """确保关系存在"""
        query = select(NodeRelation).where(
            and_(
                NodeRelation.source_node_id == source_id,
                NodeRelation.target_node_id == target_id
            )
        )
        result = await self.db.execute(query)
        existing_relation = result.scalar_one_or_none()

        if not existing_relation:
            relation = NodeRelation(
                source_node_id=source_id,
                target_node_id=target_id,
                relation_type=item.get('relation_to_trigger', 'related'),
                strength=item.get('relation_strength', 0.7)
            )
            self.db.add(relation)
            await self.db.commit()

    async def auto_link_nodes(self, node_id: UUID, limit: int = 50) -> int:
        """
        Phase 4.1: Auto-Link Worker Logic.
        Optimized to use JSONB GIN indexes and Exact Match B-Tree indexes.
        Avoids ILIKE '%...%' description scans on the whole table.
        """
        target_node = await self.db.get(KnowledgeNode, node_id)
        if not target_node:
            return 0
            
        links_created = 0
        
        # 1. Incoming Links (Reverse Lookup): 
        # Find other nodes that have 'target_node.name' in their keywords.
        # This uses the GIN index on keywords: keywords @> '["Name"]'
        incoming_query = (
            select(KnowledgeNode)
            .where(
                and_(
                    KnowledgeNode.id != node_id,
                    KnowledgeNode.keywords.contains([target_node.name])
                )
            )
            .limit(limit)
        )
        mentioning_nodes = (await self.db.execute(incoming_query)).scalars().all()
        
        for source in mentioning_nodes:
            # Create link: source -> mentions -> target
            exists = await self._check_link_exists(source.id, target_node.id)
            if not exists:
                link = NodeRelation(
                    source_node_id=source.id,
                    target_node_id=target_node.id,
                    relation_type="mention",
                    strength=0.5, # Higher strength for explicit tag
                    created_by="auto_linker"
                )
                self.db.add(link)
                links_created += 1
        
        # 2. Outgoing Links (Forward Lookup):
        # For each keyword in target_node, find nodes with that EXACT name.
        # This uses the B-Tree index on name.
        if target_node.keywords:
            for keyword in target_node.keywords:
                # Find nodes with exact name match
                candidates_query = select(KnowledgeNode).where(KnowledgeNode.name == keyword)
                candidates = (await self.db.execute(candidates_query)).scalars().all()
                
                for cand in candidates:
                    if cand.id != node_id:
                        exists = await self._check_link_exists(target_node.id, cand.id)
                        if not exists:
                            link = NodeRelation(
                                source_node_id=target_node.id,
                                target_node_id=cand.id,
                                relation_type="mention",
                                strength=0.5,
                                created_by="auto_linker"
                            )
                            self.db.add(link)
                            links_created += 1

        if links_created > 0:
            await self.db.commit()
            
        return links_created

    async def _check_link_exists(self, u: UUID, v: UUID) -> bool:
        stmt = select(NodeRelation).where(
            and_(
                NodeRelation.source_node_id == u,
                NodeRelation.target_node_id == v
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None


# 导入 or_ 函数
from sqlalchemy import or_
