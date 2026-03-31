"""
知识拓展服务 (Expansion Service)
使用 LLM 自动拓展知识星图
"""
from __future__ import annotations
import asyncio
import json
import re
from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.cache import cache_service
from app.core.llm_client import llm_client
from app.db.session import AsyncSessionLocal
from app.models.galaxy import ExpansionFeedback, KnowledgeNode, NodeExpansionQueue, NodeRelation, UserNodeStatus
from app.models.subject import Subject
from app.schemas.galaxy import SectorCode
from app.services.embedding_service import embedding_service
from app.services.galaxy_feedback_signal_processor import GalaxyFeedbackSignalProcessor
from app.services.node_sector_service import (
    NodeSectorService,
    build_sector_visuals,
    dominant_sector_from_weights,
    normalize_sector_weights,
    parse_sector_code,
    resolve_sector_weights,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


_INVALID_NODE_NAME_PREFIXES = (
    "j0",
    "j1",
    "j2",
    "j3",
    "j4",
    "j5",
    "j6",
    "j7",
    "j8",
    "j9",
    "decay-node-",
    "test-",
    "debug-",
    "tmp-",
    "测试主题",
)
_INVALID_NODE_NAME_FRAGMENTS = (
    "sparkle rag",
    "系统错误码",
    "cs101 课程说明",
)


def is_valid_knowledge_node_name(name: str) -> bool:
    normalized = name.strip()
    if not normalized:
        return False

    lowered = normalized.lower()
    if lowered in {"null", "none", "n/a", "unknown", "undefined"}:
        return False

    if lowered.startswith(_INVALID_NODE_NAME_PREFIXES):
        return False
    if any(fragment in lowered for fragment in _INVALID_NODE_NAME_FRAGMENTS):
        return False
    if re.match(r"^J\d", normalized) or re.match(r"^[a-zA-Z]\d{2,}", normalized):
        return False
    if len(normalized) > 36:
        return False
    if "�" in normalized:
        return False
    if not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", normalized):
        return False
    if re.match(r"^[?？·•\-_=\s]+$", normalized):
        return False
    return True


def validate_knowledge_node_name(name: str) -> None:
    if not is_valid_knowledge_node_name(name):
        raise ValueError(f"Invalid knowledge node name: {name!r}")


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
        trigger_task_id: UUID | None,
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
        cooldown_time = _utcnow() - timedelta(hours=self.EXPANSION_COOLDOWN_HOURS)

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
                "sector": (parse_sector_code(getattr(node.subject, "sector_code", None)) or SectorCode.VOID).value
                if node.subject
                else (parse_sector_code(getattr(node, "dominant_sector_code", None)) or SectorCode.VOID).value,
                "sector_weights": resolve_sector_weights(node),
            },
            "neighbor_nodes": [
                {"name": n.name, "relation": rel}
                for n, rel in neighbors
            ],
            "already_learned": [n.name for n in learned_nodes],
        }

        return json.dumps(context, ensure_ascii=False)

    async def _get_neighbor_nodes(self, node_id: UUID, limit: int = 10) -> list[tuple[KnowledgeNode, str]]:
        """获取节点的邻居节点"""

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

    async def _get_user_learned_nodes(self, user_id: UUID, limit: int = 50) -> list[KnowledgeNode]:
        """获取用户已学习的节点"""
        query = (
            select(KnowledgeNode)
            .join(UserNodeStatus)
            .where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.is_unlocked
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def process_expansion(self, queue_id: UUID) -> list[KnowledgeNode]:
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
            response = await self._request_expansion_json(
                prompt,
                model_name=model_name,
                temperature=0.7,
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
            queue_item.processed_at = _utcnow()
            await self.db.commit()

            return new_nodes

        except Exception as e:
            queue_item.status = 'failed'
            queue_item.error_message = str(e)
            await self.db.commit()
            raise

    async def preview_expansion_candidates(
        self,
        trigger_node_id: UUID,
        user_id: UUID,
        *,
        count: int = 3,
    ) -> tuple[list[dict], str]:
        context = await self._build_expansion_context(trigger_node_id, user_id)
        prompt_version = await self._select_prompt_version(trigger_node_id)
        requested_count = max(1, min(3, count))
        try:
            prompt = self._build_expansion_prompt(
                context,
                prompt_version=prompt_version,
                count=requested_count,
                preview_only=True,
            )
            model_name = settings.DEEPSEEK_CHAT_MODEL if settings.LLM_PROVIDER == "deepseek" else settings.LLM_MODEL_NAME
            response = await self._request_expansion_json(
                prompt,
                model_name=model_name,
                temperature=0.65,
            )
            expanded_data = self._parse_expansion_response(response)
            candidates = self._normalize_candidates(expanded_data, count=requested_count)
        except Exception as exc:
            logger.warning("Expansion candidate preview fell back to deterministic suggestions: {}", exc)
            candidates = self._fallback_candidates(context, count=requested_count)
        return candidates, prompt_version

    async def apply_expansion_candidates(
        self,
        trigger_node_id: UUID,
        user_id: UUID,
        *,
        candidates: list[dict],
    ) -> list[KnowledgeNode]:
        normalized = self._normalize_candidates(
            {"expanded_nodes": candidates},
            count=min(len(candidates), self.MAX_EXPANDED_NODES_PER_REQUEST),
        )
        return await self._create_expanded_nodes(
            {"expanded_nodes": normalized},
            trigger_node_id=trigger_node_id,
            user_id=user_id,
        )

    async def upsert_node_from_candidate(
        self,
        *,
        user_id: UUID,
        candidate: dict,
        trigger_node_id: UUID | None = None,
        parent_node_id: UUID | None = None,
        subject_id: int | None = None,
        source_type: str = "llm_expanded",
        generate_embedding: bool = True,
        unlock_for_user: bool = True,
        commit: bool = True,
        invalidate_caches: bool = True,
        allow_existing_match: bool = True,
        node_updates: dict | None = None,
    ) -> tuple[KnowledgeNode, bool]:
        context_node_id = trigger_node_id or parent_node_id
        context_node = await self._get_context_node(context_node_id) if context_node_id else None
        resolved_subject = await self._get_subject(subject_id or getattr(context_node, "subject_id", None))
        fallback_sector = (
            parse_sector_code(getattr(context_node, "dominant_sector_code", None))
            or parse_sector_code(getattr(resolved_subject, "sector_code", None))
            or SectorCode.VOID
        )
        normalized = self._normalize_candidate_item(candidate, index=0, fallback_sector=fallback_sector)
        if not normalized:
            raise ValueError("Invalid knowledge node candidate")
        existing = await self._find_existing_node(normalized["name"]) if allow_existing_match else None
        visual_data, classification_model = await self._resolve_visual_data(
            normalized,
            context_node=context_node,
            subject=resolved_subject,
            fallback_sector=fallback_sector,
        )

        if existing:
            node = existing
            created = False
            self._heal_existing_node(
                existing,
                normalized,
                visual_data=visual_data,
                classification_model=classification_model,
                parent_node_id=parent_node_id,
            )
        else:
            node = KnowledgeNode(
                subject_id=subject_id or getattr(context_node, "subject_id", None),
                parent_id=parent_node_id,
                name=normalized["name"],
                name_en=normalized.get("name_en"),
                description=normalized.get("description"),
                importance_level=normalized.get("importance_level", 3),
                is_seed=False,
                source_type=source_type,
                keywords=normalized.get("keywords", []),
                sector_weights=visual_data.sector_weights,
                dominant_sector_code=visual_data.dominant_sector_code.value,
                sector_classification_status="completed",
                sector_classification_model=classification_model,
                sector_classified_at=_utcnow(),
                position_x=visual_data.position_x,
                position_y=visual_data.position_y,
            )
            if generate_embedding and node.description:
                embedding_text = f"{node.name} {node.description}"
                node.embedding = await embedding_service.get_embedding(embedding_text)
            self.db.add(node)
            await self.db.flush()
            created = True

        self._apply_node_updates(node, node_updates)

        if unlock_for_user:
            await self._ensure_user_node_status(user_id, node.id)

        if context_node_id and node.id != context_node_id:
            await self._ensure_relation(
                context_node_id,
                node.id,
                normalized,
            )

        if commit:
            await self.db.commit()
            if invalidate_caches:
                await self._invalidate_after_graph_mutation(user_id)

        return node, created

    def _apply_node_updates(self, node: KnowledgeNode, updates: dict | None) -> None:
        if not updates:
            return
        for field, value in updates.items():
            setattr(node, field, value)
        self.db.add(node)

    def _build_expansion_prompt(
        self,
        context_json: str,
        prompt_version: str | None = None,
        *,
        count: int = 3,
        preview_only: bool = False,
    ) -> str:
        """构建拓展 Prompt"""
        context = json.loads(context_json)

        prompt_version = prompt_version or "v1"
        base_prompt = f"""你是一个知识图谱拓展专家。用户正在学习"{context['trigger_node']['name']}"这个知识点。

## 当前知识点信息
- 名称：{context['trigger_node']['name']}
- 描述：{context['trigger_node']['description']}
- 所属领域：{context['trigger_node']['sector']}
- 星域归属：{json.dumps(context['trigger_node'].get('sector_weights') or {}, ensure_ascii=False)}

## 相邻知识点
{chr(10).join([f"- {n['name']} ({n['relation']})" for n in context['neighbor_nodes']]) if context['neighbor_nodes'] else "暂无"}

## 用户已学习的知识点
{', '.join(context['already_learned'][:20]) if context['already_learned'] else "暂无"}

## 任务
请推荐 {count} 个与"{context['trigger_node']['name']}"相关的、用户可能感兴趣的知识点。

要求：
1. 不要推荐用户已学习的知识点
2. 推荐的知识点应该是渐进式的，从简单到复杂
3. 包含理论深化和实际应用两个方向
4. 每个知识点需要说明与触发知识点的关系
5. 节点名称必须可读，禁止乱码、占位词、null、N/A
6. 每个候选节点必须足够具体，适合直接显示给用户选择
7. 如果 preview_only 为真，请只输出候选项，不要解释

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
      "keywords": ["关键词1", "关键词2"],
      "sector_weights": {{
        "COSMOS": 0,
        "TECH": 0,
        "ART": 0,
        "CIVILIZATION": 0,
        "LIFE": 0,
        "WISDOM": 0,
        "VOID": 0
      }}
    }}
  ]
}}
```

relation_to_trigger 可选值: prerequisite (前置知识), related (相关), application (应用), evolution (进阶)
sector_weights 必须返回整数百分比，总和必须为 100，可多星域归属，不要默认全放进 VOID。
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
    ) -> list[KnowledgeNode]:
        """创建拓展的知识节点"""
        new_nodes = []

        for item in expanded_data.get('expanded_nodes', [])[:self.MAX_EXPANDED_NODES_PER_REQUEST]:
            if settings.EXPANSION_SEMANTIC_DEDUP_ENABLED:
                dedup_candidate = await self._find_semantic_duplicate(item)
                if dedup_candidate:
                    await self._ensure_user_node_status(user_id, dedup_candidate.id)
                    await self._ensure_relation(trigger_node_id, dedup_candidate.id, item)
                    continue

            node, created = await self.upsert_node_from_candidate(
                user_id=user_id,
                candidate=item,
                trigger_node_id=trigger_node_id,
                parent_node_id=trigger_node_id,
                source_type="llm_expanded",
                generate_embedding=True,
                unlock_for_user=True,
                commit=False,
                invalidate_caches=False,
            )
            if created:
                new_nodes.append(node)

        await self.db.commit()
        await self._invalidate_after_graph_mutation(user_id)
        return new_nodes

    async def _find_semantic_duplicate(self, item: dict) -> KnowledgeNode | None:
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
        expansion_queue_id: UUID | None,
        rating: int | None,
        implicit_score: float | None,
        feedback_type: str,
        prompt_version: str | None,
        metadata: dict | None
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
        asyncio.create_task(_refresh_galaxy_feedback_signals(user_id))
        return feedback.id

    async def _find_existing_node(self, name: str) -> KnowledgeNode | None:
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

        if existing_relation:
            return existing_relation

        relation = NodeRelation(
            source_node_id=source_id,
            target_node_id=target_id,
            relation_type=item.get('relation_to_trigger', 'related'),
            strength=item.get('relation_strength', 0.7),
        )
        self.db.add(relation)
        await self.db.flush()
        return relation

    async def _ensure_user_node_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        result = await self.db.execute(
            select(UserNodeStatus).where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == node_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if not existing.is_unlocked:
                existing.is_unlocked = True
                existing.first_unlock_at = existing.first_unlock_at or _utcnow()
                self.db.add(existing)
            return existing

        status = UserNodeStatus(
            user_id=user_id,
            node_id=node_id,
            is_unlocked=True,
            mastery_score=0,
            bkt_mastery_prob=0.0,
            first_unlock_at=_utcnow(),
        )
        self.db.add(status)
        await self.db.flush()
        return status

    async def _get_context_node(self, node_id: UUID | None) -> KnowledgeNode | None:
        if node_id is None:
            return None
        result = await self.db.execute(
            select(KnowledgeNode)
            .options(
                selectinload(KnowledgeNode.subject),
                selectinload(KnowledgeNode.parent),
            )
            .where(KnowledgeNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def _get_subject(self, subject_id: int | None) -> Subject | None:
        if subject_id is None:
            return None
        return await self.db.get(Subject, subject_id)

    async def _resolve_visual_data(
        self,
        item: dict,
        *,
        context_node: KnowledgeNode | None,
        subject: Subject | None,
        fallback_sector: SectorCode,
    ):
        sector_weights = normalize_sector_weights(
            item.get("sector_weights"),
            fallback_sector=fallback_sector,
        )
        dominant_sector = dominant_sector_from_weights(sector_weights)
        should_classify = (
            not item.get("sector_weights_provided")
            or dominant_sector == SectorCode.VOID
        )
        if should_classify:
            try:
                visual_data = await NodeSectorService(self.db).classify_payload(
                    name=item["name"],
                    name_en=item.get("name_en"),
                    description=item.get("description"),
                    keywords=item.get("keywords", []),
                    importance_level=item.get("importance_level", 3),
                    parent_name=getattr(context_node, "name", None),
                    subject_name=getattr(subject, "name", None),
                    subject_sector_hint=getattr(subject, "sector_code", None),
                    neighbors=(
                        [{"name": context_node.name, "relation": "trigger"}]
                        if context_node is not None
                        else []
                    ),
                    fallback_sector=fallback_sector,
                    stable_seed=item.get("candidate_id") or item["name"],
                )
                return visual_data, "expansion_sector_classifier"
            except Exception as exc:
                logger.warning("Expansion sector enrichment fallback triggered for {}: {}", item["name"], exc)

        return (
            build_sector_visuals(
                item.get("candidate_id") or item["name"],
                importance_level=item.get("importance_level", 3),
                sector_weights=sector_weights,
            ),
            "expansion_llm" if item.get("sector_weights_provided") else "expansion_fallback",
        )

    def _heal_existing_node(
        self,
        node: KnowledgeNode,
        item: dict,
        *,
        visual_data,
        classification_model: str,
        parent_node_id: UUID | None,
    ) -> None:
        if not node.description and item.get("description"):
            node.description = item["description"]
        if not node.name_en and item.get("name_en"):
            node.name_en = item["name_en"]
        if int(node.importance_level or 0) <= 0:
            node.importance_level = item.get("importance_level", 3)
        merged_keywords = list(dict.fromkeys([*(node.keywords or []), *(item.get("keywords") or [])]))
        if merged_keywords != list(node.keywords or []):
            node.keywords = merged_keywords[:10]
        if not node.parent_id and parent_node_id:
            node.parent_id = parent_node_id
        if (
            not node.sector_weights
            or str(getattr(node, "dominant_sector_code", "VOID") or "VOID") == SectorCode.VOID.value
            or str(getattr(node, "sector_classification_status", "pending") or "pending") in {"pending", "failed"}
        ):
            node.sector_weights = visual_data.sector_weights
            node.dominant_sector_code = visual_data.dominant_sector_code.value
            node.sector_classification_status = "completed"
            node.sector_classification_model = classification_model
            node.sector_classified_at = _utcnow()
            node.position_x = visual_data.position_x
            node.position_y = visual_data.position_y
        self.db.add(node)

    async def _invalidate_after_graph_mutation(self, user_id: UUID) -> None:
        await NodeSectorService(self.db).invalidate_user_graph_cache(user_id)
        from app.services.graph_reasoning_service import GraphReasoningService

        await GraphReasoningService(self.db).invalidate_cache()

    def _normalize_candidates(self, expanded_data: dict, *, count: int) -> list[dict]:
        normalized: list[dict] = []
        for index, raw_item in enumerate(expanded_data.get("expanded_nodes", [])[:count]):
            item = self._normalize_candidate_item(raw_item, index=index, fallback_sector=SectorCode.VOID)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_candidate_item(
        self,
        raw_item: dict | None,
        *,
        index: int,
        fallback_sector: SectorCode,
    ) -> dict | None:
        if not isinstance(raw_item, dict):
            return None
        name = self._sanitize_text(raw_item.get("name"))
        if not name:
            return None
        if not is_valid_knowledge_node_name(name):
            return None
        relation = self._normalize_relation_type(raw_item.get("relation_to_trigger"))
        description = self._sanitize_text(raw_item.get("description")) or f"围绕{name}补充一个更完整的学习节点。"
        keywords = [
            keyword
            for keyword in (
                self._sanitize_text(item) for item in (raw_item.get("keywords") or [])
            )
            if keyword
        ][:6]
        raw_sector_weights = raw_item.get("sector_weights")
        return {
            "candidate_id": self._sanitize_text(raw_item.get("candidate_id"))
            or f"{name}_{index + 1}",
            "name": name,
            "name_en": self._sanitize_text(raw_item.get("name_en")),
            "description": description[:120],
            "importance_level": max(1, min(5, int(raw_item.get("importance_level") or 3))),
            "relation_to_trigger": relation,
            "relation_strength": max(0.0, min(1.0, float(raw_item.get("relation_strength") or 0.7))),
            "keywords": keywords,
            "sector_weights": normalize_sector_weights(
                raw_sector_weights,
                fallback_sector=fallback_sector,
            ),
            "sector_weights_provided": bool(raw_sector_weights),
        }

    def _sanitize_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {"null", "none", "n/a", "unknown", "undefined"}:
            return None
        if "�" in text:
            return None
        if not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", text):
            return None
        if len(text) > 40:
            text = text[:40].rstrip()
        return text

    def _normalize_relation_type(self, raw: object) -> str:
        relation = str(raw or "related").strip().lower()
        mapping = {
            "prerequisite": "prerequisite",
            "related": "related",
            "application": "application",
            "evolution": "evolution",
            "parent_child": "parent_child",
            "contains": "contains",
            "derived": "evolution",
            "similar": "related",
        }
        return mapping.get(relation, "related")

    def _fallback_candidates(self, context_json: str, *, count: int) -> list[dict]:
        context = json.loads(context_json)
        trigger = self._sanitize_text(context.get("trigger_node", {}).get("name")) or "当前主题"
        neighbor_names = [
            self._sanitize_text(item.get("name"))
            for item in context.get("neighbor_nodes", [])
            if isinstance(item, dict)
        ]
        neighbor_names = [item for item in neighbor_names if item]

        templates = [
            {
                "candidate_id": f"{trigger}_foundation",
                "name": neighbor_names[0] if neighbor_names else f"{trigger}基础框架",
                "description": f"补齐 {trigger} 的核心基础脉络，避免后续学习只停留在表层概念。",
                "importance_level": 3,
                "relation_to_trigger": "prerequisite",
                "relation_strength": 0.82,
                "keywords": [trigger, "基础", "框架"],
                "sector_weights": dict(context.get("trigger_node", {}).get("sector_weights") or {"VOID": 100}),
            },
            {
                "candidate_id": f"{trigger}_application",
                "name": f"{trigger}应用场景",
                "description": f"围绕 {trigger} 增加一个更贴近真实任务或问题解决的应用节点。",
                "importance_level": 3,
                "relation_to_trigger": "application",
                "relation_strength": 0.75,
                "keywords": [trigger, "应用", "实践"],
                "sector_weights": dict(context.get("trigger_node", {}).get("sector_weights") or {"VOID": 100}),
            },
            {
                "candidate_id": f"{trigger}_advanced",
                "name": f"{trigger}进阶专题",
                "description": f"把 {trigger} 向更系统化、更深入的方向延展，形成下一步学习入口。",
                "importance_level": 4,
                "relation_to_trigger": "evolution",
                "relation_strength": 0.7,
                "keywords": [trigger, "进阶", "专题"],
                "sector_weights": dict(context.get("trigger_node", {}).get("sector_weights") or {"VOID": 100}),
            },
        ]
        return templates[:count]

    async def _request_expansion_json(
        self,
        prompt: str,
        *,
        model_name: str,
        temperature: float,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        try:
            return await llm_client.chat_completion(
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                model=model_name,
            )
        except Exception as exc:
            logger.warning("Expansion LLM json mode failed, falling back to plain text parsing: {}", exc)
            return await llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                model=model_name,
            )

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


async def _refresh_galaxy_feedback_signals(user_id: UUID) -> None:
    try:
        async with AsyncSessionLocal() as db:
            processor = GalaxyFeedbackSignalProcessor(db, cache_service.redis)
            await processor.process_feedback(user_id)
    except Exception as exc:
        logger.warning("Failed to refresh galaxy feedback signals for {}: {}", user_id, exc)
