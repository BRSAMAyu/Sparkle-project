"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

知识星图核心服务 (Galaxy Service) - Facade Pattern
Refactored to delegate to specialized services:
- GraphStructureService: CRUD, Relations
- KnowledgeRetrievalService: Search, Embedding
- GalaxyStatsService: Spark, Stats, Prediction
"""

from __future__ import annotations

import json
from datetime import timezone, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from loguru import logger
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service, cached
from app.core.event_bus import KnowledgeNodeUpdated, MasteryUpdatedFromError, event_bus
from app.gen.sparkle.rag.v1 import evidence_pb2
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.schemas.galaxy import (
    GalaxyContributionNode,
    GalaxyGraphResponse,
    NodeRelationInfo,
    NodeWithStatus,
    SearchResultItem,
    SparkResult,
    UserGalaxyContribution,
)
from app.services.embedding_service import embedding_service
from app.services.expansion_service import ExpansionService, validate_knowledge_node_name
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.galaxy.ontology_generator import relation_type_to_wire_name
from app.services.galaxy.ontology_generator import OntologyExtractionResult, OntologyGenerator
from app.services.galaxy.review_urgency_service import ReviewUrgencyService
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.galaxy.structure_service import GraphStructureService
from app.services.node_sector_service import NodeSectorService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


SPRINT_NODE_UUID_NAMESPACE = uuid5(NAMESPACE_URL, "sparkle:sprint-pack-node")
SPRINT_NODE_ID_ALIASES = {
    "cn.tcp_flow": "cn.tcp_flow_control",
}


class GalaxyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.structure = GraphStructureService(db)
        self.retrieval = KnowledgeRetrievalService(db)
        self.stats = GalaxyStatsService(db)
        self.review_urgency = ReviewUrgencyService()
        self.ontology_generator = OntologyGenerator()

        # Subscribe to error.created events
        # Note: In a real production app, subscription should be handled in a startup event or a separate worker
        # to avoid re-subscribing on every request if GalaxyService is transient.
        # Assuming GalaxyService is scoped or we rely on external worker.
        # For this task, we'll implement the handler method that can be registered.

    async def _write_mastery_outbox_event(
        self,
        *,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        """Write mastery updates into the active CQRS outbox schema.

        Prefer the current `event_outbox` table used by gateway/CQRS. Fall back to
        the legacy `outbox_events` table only if that older schema is what's available.
        """
        if await self._table_exists("event_outbox"):
            seq_result = await self.db.execute(
                text("""
                    INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                    VALUES (:aggregate_type, :aggregate_id, 1)
                    ON CONFLICT (aggregate_type, aggregate_id)
                    DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                    RETURNING next_sequence
                """),
                {
                    "aggregate_type": "galaxy_node_mastery",
                    "aggregate_id": aggregate_id,
                },
            )
            sequence_number = seq_result.scalar_one()

            await self.db.execute(
                text("""
                    INSERT INTO event_outbox
                    (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                    VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
                """),
                {
                    "aggregate_type": "galaxy_node_mastery",
                    "aggregate_id": aggregate_id,
                    "event_type": event_type,
                    "sequence_number": sequence_number,
                    "payload": json.dumps(payload),
                    "metadata": json.dumps({"service": "galaxy_service"}),
                },
            )
            return

        if await self._table_exists("outbox_events"):
            await self.db.execute(
                text("""
                    INSERT INTO outbox_events (topic, payload, status, created_at, updated_at)
                    VALUES (:topic, :payload, 'pending', :created_at, :created_at)
                """),
                {
                    "topic": event_type,
                    "payload": json.dumps(payload),
                    "created_at": _utcnow(),
                },
            )
            return

        logger.warning("No compatible outbox table found; skipping mastery outbox event write")

    async def _table_exists(self, table_name: str) -> bool:
        connection = await self.db.connection()
        return await connection.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table_name))

    async def handle_error_created(self, event_data: dict):
        """
        Handle error.created event: reduce mastery for related nodes.
        """
        try:
            user_id = UUID(event_data["user_id"])
            linked_node_ids = [UUID(nid) for nid in event_data.get("linked_node_ids", [])]

            if not linked_node_ids:
                return

            logger.info(f"Processing error event for user {user_id}, linked nodes: {linked_node_ids}")

            for node_id in linked_node_ids:
                # 1. Get current status
                query = text("SELECT mastery_score FROM user_node_status WHERE user_id = :uid AND node_id = :nid")
                res = await self.db.execute(query, {"uid": user_id, "nid": node_id})
                current = res.scalar_one_or_none()

                current_score = current if current is not None else 0

                # 2. Penalty Logic (Simple: -10%)
                # Ensure it doesn't go below 0
                new_score = max(0, int(current_score * 0.9))

                if new_score != current_score:
                    # 3. Update Mastery using existing method (handles Outbox + Audit)
                    await self.update_node_mastery(
                        user_id=user_id, node_id=node_id, new_mastery=new_score, reason="error_penalty"
                    )

                    # 4. Publish galaxy.node.updated (Specific for frontend realtime update)
                    # update_node_mastery already publishes galaxy.node.mastery_updated via Outbox
                    # We can also publish a realtime event via Redis directly if needed for immediate websocket
                    realtime_event = KnowledgeNodeUpdated(
                        user_id=str(user_id), node_id=str(node_id), new_mastery=new_score
                    )
                    await event_bus.publish("galaxy.node.updated", realtime_event.to_dict())
                    logger.info(f"Reduced mastery for node {node_id} to {new_score}")

        except Exception as e:
            logger.error(f"Failed to handle error_created event: {e}")

    async def update_mastery_from_error(
        self,
        db: AsyncSession | None = None,
        *,
        user_id: str,
        knowledge_node_id: str | None,
        knowledge_node_name: str | None,
        error_type: str,
        error_count: int,
    ) -> dict | None:
        """
        根据错题分析更新知识节点掌握度。

        掌握度更新公式：
        - 轻度错误（careless）：mastery -= 3
        - 中度错误（comprehension_failure）：mastery -= 8
        - 重度错误（repeated >= 3次）：mastery -= 15
        - 最低下限：10（不设为0，避免过度惩罚）

        返回：{"node_id": ..., "old_mastery": ..., "new_mastery": ..., "delta": ...}
        如果节点不存在：返回 None（不报错）
        """
        active_db = db or self.db
        coerced_user_id = self._coerce_uuid(user_id)
        coerced_node_id = self._coerce_uuid(knowledge_node_id)
        node_name = str(knowledge_node_name or "").strip()

        row = None
        if coerced_node_id is not None:
            result = await active_db.execute(
                select(KnowledgeNode, UserNodeStatus)
                .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
                .where(UserNodeStatus.user_id == coerced_user_id)
                .where(KnowledgeNode.id == coerced_node_id)
                .limit(1)
            )
            row = result.first()

        if row is None and node_name:
            result = await active_db.execute(
                select(KnowledgeNode, UserNodeStatus)
                .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
                .where(UserNodeStatus.user_id == coerced_user_id)
                .where(func.lower(KnowledgeNode.name).like(f"%{node_name.lower()}%"))
                .order_by(KnowledgeNode.name)
                .limit(1)
            )
            row = result.first()

        if row is None:
            return None

        node, status = row
        old_mastery = float(status.mastery_score or 0.0)
        requested_delta = self._error_mastery_delta(error_type=error_type, error_count=error_count)
        new_mastery = max(10.0, old_mastery + requested_delta)
        actual_delta = new_mastery - old_mastery
        update_time = _utcnow()

        status.mastery_score = new_mastery
        status.bkt_mastery_prob = max(0.0, min(new_mastery / 100.0, 1.0))
        status.bkt_last_updated_at = update_time
        status.updated_at = update_time
        status.last_interacted_at = update_time
        status.is_unlocked = True
        await active_db.flush()

        event = MasteryUpdatedFromError(
            user_id=str(user_id),
            node_id=str(node.id),
            node_name=str(node.name or ""),
            old_mastery=old_mastery,
            new_mastery=new_mastery,
            delta=actual_delta,
            error_type=str(error_type or "").strip().lower(),
            triggered_at=update_time.isoformat(),
        )
        await event_bus.publish(event.event_type, event.to_dict())

        return {
            "node_id": str(node.id),
            "node_name": str(node.name or ""),
            "old_mastery": old_mastery,
            "new_mastery": new_mastery,
            "delta": actual_delta,
        }

    @staticmethod
    def _coerce_uuid(value: object) -> object:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return value

    async def get_sprint_mastery_summary(
        self,
        *,
        user_id: str | UUID,
        pack_node_ids: list[str],
    ) -> dict[str, object]:
        """Return user mastery for Sprint Pack node ids when Galaxy has matching nodes."""
        wanted_ids: list[str] = []
        for node_id in pack_node_ids:
            normalized = str(node_id or "").strip()
            if normalized and normalized not in wanted_ids:
                wanted_ids.append(normalized)
        if not wanted_ids:
            return {"mastery_snapshot": {}, "strongest_nodes": [], "persistent_weak_nodes": []}

        wanted_by_key = {self._pack_node_match_key(node_id): node_id for node_id in wanted_ids}
        user_uuid = self._coerce_uuid(user_id)
        result = await self.db.execute(
            select(KnowledgeNode, UserNodeStatus)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_uuid)
        )

        mastery_snapshot: dict[str, float] = {}
        for node, status in result.all():
            candidate_keys = self._sprint_pack_candidate_keys(node, status)
            matched_id = self._match_sprint_pack_node_id(candidate_keys, wanted_by_key)
            if not matched_id:
                continue
            mastery = float(status.mastery_score or 0.0)
            if mastery > 1.0:
                mastery = mastery / 100.0
            mastery_snapshot[matched_id] = max(0.0, min(mastery, 1.0))

        strongest_nodes = [node_id for node_id, mastery in mastery_snapshot.items() if mastery > 0.7]
        persistent_weak_nodes = [node_id for node_id, mastery in mastery_snapshot.items() if mastery < 0.4]
        return {
            "mastery_snapshot": mastery_snapshot,
            "strongest_nodes": strongest_nodes,
            "persistent_weak_nodes": persistent_weak_nodes,
        }

    @staticmethod
    def _pack_node_match_key(value: object) -> str:
        return "".join(ch for ch in str(value or "").lower() if ch.isalnum())

    def _sprint_pack_candidate_keys(self, node: KnowledgeNode, status: UserNodeStatus) -> set[str]:
        raw_candidates: list[object] = [node.id, node.name, node.name_en]
        keywords = node.keywords
        if isinstance(keywords, dict):
            raw_candidates.extend([*keywords.keys(), *keywords.values()])
        elif isinstance(keywords, list):
            raw_candidates.extend(keywords)

        snapshot = status.learning_path_snapshot if isinstance(status.learning_path_snapshot, dict) else {}
        for key in (
            "sprint_pack_node_id",
            "sprint_pack_id",
            "pack_node_id",
            "external_node_id",
            "node_slug",
            "slug",
        ):
            raw_candidates.append(snapshot.get(key))
        for key in ("sprint_pack_node_ids", "pack_node_ids", "related_pack_nodes"):
            value = snapshot.get(key)
            if isinstance(value, list):
                raw_candidates.extend(value)

        return {key for item in raw_candidates if (key := self._pack_node_match_key(item))}

    @staticmethod
    def _match_sprint_pack_node_id(candidate_keys: set[str], wanted_by_key: dict[str, str]) -> str | None:
        for key, node_id in wanted_by_key.items():
            if key in candidate_keys:
                return node_id
        for candidate in candidate_keys:
            if len(candidate) < 4:
                continue
            for key, node_id in wanted_by_key.items():
                if candidate in key or key in candidate:
                    return node_id
        return None

    @staticmethod
    def _error_mastery_delta(*, error_type: str, error_count: int) -> float:
        normalized_type = str(error_type or "").strip().lower()
        if error_count >= 3 or normalized_type == "repeated_mistake":
            return -15.0
        if normalized_type in {"careless_error", "careless_mistake", "reading_careless", "calculation_error"}:
            return -3.0
        return -8.0

    # --- Delegated to GraphStructureService ---

    async def create_node(
        self,
        user_id: UUID,
        title: str,
        summary: str,
        subject_id: int | None = None,
        tags: list[str] = None,
        parent_node_id: UUID | None = None,
        *,
        name_en: str | None = None,
        importance_level: int = 3,
        relation_type: str = "related",
        relation_strength: float = 0.7,
        sector_weights: dict[str, int] | None = None,
    ) -> KnowledgeNode:
        """
        Create a new knowledge node.
        Async pipeline:
        1. Write basic info to DB (Fast)
        2. Spawn background task for Embedding & Deduplication (Slow)
        """
        # 1. Fast Write
        if tags is None:
            tags = []
        validate_knowledge_node_name(title)
        expansion_service = ExpansionService(self.db)
        node, _ = await expansion_service.upsert_node_from_candidate(
            user_id=user_id,
            candidate={
                "name": title,
                "name_en": name_en,
                "description": summary,
                "importance_level": importance_level,
                "relation_to_trigger": relation_type,
                "relation_strength": relation_strength,
                "keywords": tags,
                "sector_weights": sector_weights or {},
            },
            parent_node_id=parent_node_id,
            subject_id=subject_id,
            source_type="user_created",
            generate_embedding=False,
            unlock_for_user=True,
            commit=True,
            invalidate_caches=True,
        )

        # 2. Async Background Processing (Managed)
        from app.core.task_manager import task_manager

        # from app.core.celery_app import schedule_long_task

        # 方案1: 使用 TaskManager (快速任务, < 10秒)
        await task_manager.spawn(
            self._process_node_background(node.id, title, summary), task_name="node_embedding", user_id=str(user_id)
        )

        # 方案2: 使用 Celery (长时任务, 需要持久化) - 可选
        # schedule_long_task(
        #     "generate_node_embedding",
        #     args=(str(node.id), title, summary, str(user_id)),
        #     queue="high_priority"
        # )

        return node

    async def create_edge(self, user_id: UUID, source_id: UUID, target_id: UUID, relation_type: str) -> NodeRelation:
        return await self.structure.create_edge(user_id, source_id, target_id, relation_type)

    async def get_goal_context_nodes(
        self,
        *,
        user_id: UUID,
        plan_ids: list[UUID],
        limit: int = 5,
    ) -> list[dict[str, object]]:
        if not plan_ids:
            return []

        task_rows = (
            await self.db.execute(
                select(Task.knowledge_node_id, Task.priority, Task.status)
                .where(Task.user_id == user_id)
                .where(Task.plan_id.in_(plan_ids))
                .where(Task.knowledge_node_id.is_not(None))
                .order_by(Task.priority.desc(), Task.updated_at.desc())
                .limit(12)
            )
        ).all()

        seed_node_ids: list[UUID] = []
        for node_id, _priority, status in task_rows:
            if node_id is None:
                continue
            if status not in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED}:
                continue
            if node_id not in seed_node_ids:
                seed_node_ids.append(node_id)
            if len(seed_node_ids) >= limit:
                break

        if not seed_node_ids:
            status_rows = (
                await self.db.execute(
                    select(UserNodeStatus.node_id)
                    .where(UserNodeStatus.user_id == user_id)
                    .where(UserNodeStatus.is_unlocked.is_(True))
                    .order_by(UserNodeStatus.updated_at.desc())
                    .limit(limit)
                )
            ).all()
            seed_node_ids = [node_id for node_id, in status_rows if node_id is not None]

        if not seed_node_ids:
            return []

        candidate_scores: dict[UUID, float] = {}
        candidate_roles: dict[UUID, str] = {}
        for node_id in seed_node_ids:
            candidate_scores[node_id] = candidate_scores.get(node_id, 0.0) + 2.0
            candidate_roles[node_id] = "goal_anchor"

        relation_rows = (
            await self.db.execute(
                select(
                    NodeRelation.source_node_id,
                    NodeRelation.target_node_id,
                    NodeRelation.relation_type,
                )
                .where(NodeRelation.source_node_id.in_(seed_node_ids) | NodeRelation.target_node_id.in_(seed_node_ids))
                .limit(32)
            )
        ).all()
        for source_id, target_id, _relation_type in relation_rows:
            neighbor_id = target_id if source_id in seed_node_ids else source_id
            if neighbor_id is None:
                continue
            candidate_scores[neighbor_id] = candidate_scores.get(neighbor_id, 0.0) + 1.0
            candidate_roles.setdefault(neighbor_id, "related")

        candidate_ids = list(candidate_scores.keys())
        rows = (
            await self.db.execute(
                select(KnowledgeNode, UserNodeStatus.mastery_score, UserNodeStatus.is_unlocked)
                .join(
                    UserNodeStatus,
                    (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id),
                )
                .where(KnowledgeNode.id.in_(candidate_ids))
            )
        ).all()
        if not rows:
            return []

        node_payloads: dict[UUID, dict[str, object]] = {}
        for node, mastery_score, is_unlocked in rows:
            if not bool(is_unlocked):
                continue
            description = str(node.description or "").strip()
            if len(description) > 96:
                description = description[:95].rstrip() + "..."
            node_payloads[node.id] = {
                "node_id": str(node.id),
                "name": str(node.name or "").strip(),
                "description": description,
                "mastery_score": round(float(mastery_score or 0.0), 1),
                "role": candidate_roles.get(node.id, "related"),
                "relevance_score": round(float(candidate_scores.get(node.id, 0.0)), 2),
            }

        ordered_ids = sorted(
            node_payloads.keys(),
            key=lambda node_id: (
                candidate_scores.get(node_id, 0.0),
                float(node_payloads[node_id].get("mastery_score") or 0.0),
            ),
            reverse=True,
        )
        return [node_payloads[node_id] for node_id in ordered_ids[:limit]]

    async def auto_generate_ontology(self, document_text: str, subject: str | None = None) -> OntologyExtractionResult:
        return await self.ontology_generator.generate(document_text=document_text, subject=subject)

    async def create_nodes_from_document(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        file_name: str,
        document_text: str,
        subject_id: int | None = None,
        subject: str | None = None,
    ) -> dict[str, object]:
        ontology = await self.auto_generate_ontology(document_text, subject)
        expansion_service = ExpansionService(self.db)
        root_node, _ = await expansion_service.upsert_node_from_candidate(
            user_id=user_id,
            candidate={
                "name": file_name[:255],
                "description": f"Imported from {file_name}",
                "importance_level": 3,
                "keywords": ["document_import", "ontology:root", *(["subject:" + subject] if subject else [])],
            },
            subject_id=subject_id,
            source_type="document_import",
            generate_embedding=False,
            unlock_for_user=True,
            commit=False,
            invalidate_caches=False,
            allow_existing_match=False,
            node_updates={
                "source_file_id": file_id,
                "status": "draft",
            },
        )

        created_nodes: list[KnowledgeNode] = []
        created_relations: list[NodeRelation] = []
        node_by_name: dict[str, KnowledgeNode] = {}

        for candidate in ontology.nodes:
            child, _ = await expansion_service.upsert_node_from_candidate(
                user_id=user_id,
                candidate={
                    "name": candidate.name[:255],
                    "description": candidate.summary,
                    "keywords": [
                        *list(dict.fromkeys([*candidate.keywords[:8], f"node_type:{candidate.node_type.lower()}"])),
                    ],
                    "importance_level": candidate.importance_level,
                    "relation_to_trigger": "parent_child",
                    "relation_strength": 0.65,
                },
                trigger_node_id=root_node.id,
                parent_node_id=root_node.id,
                subject_id=subject_id,
                source_type="document_import",
                generate_embedding=False,
                unlock_for_user=True,
                commit=False,
                invalidate_caches=False,
                allow_existing_match=False,
                node_updates={
                    "source_file_id": file_id,
                    "status": "draft",
                },
            )
            parent_relation = await self.db.scalar(
                select(NodeRelation).where(
                    NodeRelation.source_node_id == root_node.id,
                    NodeRelation.target_node_id == child.id,
                )
            )
            if parent_relation:
                created_relations.append(parent_relation)
            node_by_name[candidate.name] = child
            created_nodes.append(child)

        for relation in ontology.relations:
            source = node_by_name.get(relation.source_name)
            target = node_by_name.get(relation.target_name)
            if not source or not target:
                continue
            edge = NodeRelation(
                source_node_id=source.id,
                target_node_id=target.id,
                relation_type=relation_type_to_wire_name(relation.relation_type),
                strength=relation.strength,
                created_by="ontology_generator",
            )
            self.db.add(edge)
            created_relations.append(edge)

        await self.db.commit()
        await expansion_service._invalidate_after_graph_mutation(user_id)
        return {
            "root_node": root_node,
            "created_nodes": created_nodes,
            "created_relations": created_relations,
            "ontology": ontology.to_dict(),
        }

    async def get_node_neighbors(self, node_id: UUID, limit: int = 5) -> list[KnowledgeNode]:
        """Get connected neighbor nodes (Graph RAG support)"""
        return await self.structure.get_node_neighbors(node_id, limit)

    async def update_node_positions(self, updates: list[dict]) -> int:
        """Batch update node positions"""
        return await self.structure.update_node_positions(updates)

    async def get_nodes_in_bounds(self, min_x: float, max_x: float, min_y: float, max_y: float) -> list[KnowledgeNode]:
        """Get nodes within viewport"""
        return await self.structure.get_nodes_in_bounds(min_x, max_x, min_y, max_y)

    @cached(
        ttl=600,
        key_builder=lambda self, user_id, sector_code=None, include_locked=True, zoom_level=1.0: f"{user_id}:{sector_code}:{include_locked}:{zoom_level < 0.5}",
    )
    async def get_galaxy_graph(
        self, user_id: UUID, sector_code: str | None = None, include_locked: bool = True, zoom_level: float = 1.0
    ) -> GalaxyGraphResponse:
        # 1. Get Structure
        nodes_with_status, relations = await self.structure.get_graph_view(
            user_id, sector_code, include_locked, zoom_level
        )
        await NodeSectorService(self.db).ensure_backfill_for_user(
            user_id=user_id,
            candidate_nodes=[node for node, _ in nodes_with_status],
        )

        # 2. Get Stats (Parallelizable if needed, but fast enough)
        user_stats = await self.stats.calculate_user_stats(user_id)

        # 3. Build edge list (Flutter expects 'edges' field)
        edge_list = [
            NodeRelationInfo(
                source_node_id=rel.source_node_id,
                target_node_id=rel.target_node_id,
                relation_type=rel.relation_type,
                strength=rel.strength,
            )
            for rel in relations
        ]

        # 4. Calculate user flame intensity from stats
        user_flame_intensity = 0.0
        if user_stats.total_nodes > 0:
            user_flame_intensity = min(1.0, user_stats.unlocked_count / max(1, user_stats.total_nodes))

        # 5. Fetch recent error counts per node (single batch query, last 14 days)
        error_counts = await self._get_recent_error_counts_by_node(user_id, days=14)
        review_signals = self.review_urgency.score_graph_nodes(
            nodes_with_status,
            recent_error_counts=error_counts,
        )

        # 6. Assemble with Flutter-compatible fields
        return GalaxyGraphResponse(
            nodes=[
                NodeWithStatus.from_models(
                    node,
                    status,
                    recent_error_count=error_counts.get(node.id, 0),
                    review_signal=review_signals.get(node.id),
                )
                for node, status in nodes_with_status
            ],
            relations=edge_list,
            edges=edge_list,  # Flutter expects this field name
            user_stats=user_stats,
            user_flame_intensity=user_flame_intensity,  # Flutter expects 0.0-1.0
        )

    async def _get_recent_error_counts_by_node(self, user_id: UUID, days: int = 14) -> dict[UUID, int]:
        """Return {node_id: error_count} for errors in the last `days` days (single query)."""
        from datetime import timedelta

        try:
            from app.models.error_book import ErrorRecord

            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            result = await self.db.execute(
                select(ErrorRecord.linked_knowledge_node_ids)
                .where(ErrorRecord.user_id == user_id)
                .where(ErrorRecord.is_deleted.is_(False))
                .where(ErrorRecord.created_at >= cutoff)
            )
            counts: dict[UUID, int] = {}
            for (linked_ids,) in result.all():
                for nid in linked_ids or []:
                    try:
                        key = UUID(str(nid)) if not isinstance(nid, UUID) else nid
                        counts[key] = counts.get(key, 0) + 1
                    except (ValueError, AttributeError):
                        pass
            return counts
        except Exception as exc:
            logger.debug("GalaxyService: could not load error counts: {}", exc)
            return {}

    async def get_galaxy_graph_viewport(
        self,
        user_id: UUID,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        limit: int = 800,
    ) -> GalaxyGraphResponse:
        nodes_with_status, relations = await self.structure.get_graph_viewport(
            user_id=user_id,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            limit=limit,
        )
        if not nodes_with_status:
            fallback_nodes, fallback_relations = await self.structure.get_graph_view(
                user_id=user_id,
                sector_code=None,
                include_locked=True,
                zoom_level=1.0,
            )
            mapped_nodes = [NodeWithStatus.from_models(node, status) for node, status in fallback_nodes]
            filtered_nodes = [
                node for node in mapped_nodes if min_x <= node.position_x <= max_x and min_y <= node.position_y <= max_y
            ][:limit]
            filtered_ids = {node.id for node in filtered_nodes}
            relations = [
                rel
                for rel in fallback_relations
                if rel.source_node_id in filtered_ids and rel.target_node_id in filtered_ids
            ]
            user_stats = await self.stats.calculate_user_stats(user_id)
            return GalaxyGraphResponse(
                nodes=filtered_nodes,
                relations=[
                    NodeRelationInfo(
                        source_node_id=rel.source_node_id,
                        target_node_id=rel.target_node_id,
                        relation_type=rel.relation_type,
                        strength=rel.strength,
                    )
                    for rel in relations
                ],
                user_stats=user_stats,
            )
        user_stats = await self.stats.calculate_user_stats(user_id)
        return GalaxyGraphResponse(
            nodes=[NodeWithStatus.from_models(node, status) for node, status in nodes_with_status],
            relations=[
                NodeRelationInfo(
                    source_node_id=rel.source_node_id,
                    target_node_id=rel.target_node_id,
                    relation_type=rel.relation_type,
                    strength=rel.strength,
                )
                for rel in relations
            ],
            user_stats=user_stats,
        )

    # --- Delegated to KnowledgeRetrievalService ---

    async def keyword_search(
        self, user_id: UUID, query: str, subject_id: int | None = None, limit: int = 20
    ) -> list[KnowledgeNode]:
        return await self.retrieval.keyword_search(user_id, query, subject_id, limit)

    async def hybrid_search(
        self,
        user_id: UUID,
        query: str,
        vector_query: str | None = None,
        subject_id: int | None = None,
        limit: int = 5,
        threshold: float = 0.3,
        use_reranker: bool = True,
    ) -> list[SearchResultItem]:
        return await self.retrieval.hybrid_search(
            user_id, query, vector_query, subject_id, limit, threshold, use_reranker
        )

    async def semantic_search(
        self, user_id: UUID, query: str, subject_id: int | None = None, limit: int = 10, threshold: float = 0.3
    ) -> list[SearchResultItem]:
        ranked_nodes = await self.retrieval.semantic_search_ranked_nodes(
            query=query,
            subject_id=subject_id,
            limit=limit,
            threshold=threshold,
        )

        results = []
        for node, score in ranked_nodes:
            status = await self.retrieval.get_user_node_status(user_id, node.id)
            results.append(self.retrieval._format_search_result(node, status, score))

        return results

    async def record_expansion_feedback(
        self,
        user_id: UUID,
        trigger_node_id: UUID,
        expansion_queue_id: UUID | None,
        rating: int | None,
        implicit_score: float | None,
        feedback_type: str,
        prompt_version: str | None,
        metadata: dict | None,
    ) -> UUID:
        expansion_service = ExpansionService(self.db)
        return await expansion_service.record_feedback(
            user_id=user_id,
            trigger_node_id=trigger_node_id,
            expansion_queue_id=expansion_queue_id,
            rating=rating,
            implicit_score=implicit_score,
            feedback_type=feedback_type,
            prompt_version=prompt_version,
            metadata=metadata,
        )

    async def semantic_search_nodes(
        self, query: str, subject_id: int | None = None, limit: int = 10, threshold: float = 0.3
    ) -> list[KnowledgeNode]:
        return await self.retrieval.semantic_search_nodes(query, subject_id, limit, threshold)

    def build_evidence_pack(
        self,
        results: list[SearchResultItem],
        request_id: str,
        trace_id: str,
        query: str,
        strategy_name: str,
    ) -> evidence_pb2.EvidencePack:
        nodes = []
        for result in results:
            node = result.node
            snippet = (node.description or node.name or "")[:400]
            metadata = {
                "name": node.name or "",
                "sector_code": str(node.sector_code),
                "parent_name": node.parent_name or "",
                "strategy": strategy_name,
            }
            nodes.append(
                evidence_pb2.EvidenceNode(
                    node_id=str(node.id),
                    source_id=str(node.id),
                    snippet=snippet,
                    score=float(result.similarity),
                    source_uri=f"galaxy://node/{node.id}",
                    source_type="hybrid",
                    metadata=metadata,
                )
            )

        pack = evidence_pb2.EvidencePack(
            request_id=request_id,
            trace_id=trace_id,
            nodes=nodes,
            metadata={
                "query": query,
                "strategy": strategy_name,
            },
        )
        return pack

    async def auto_classify_task(self, task_title: str, task_description: str | None = None) -> UUID | None:
        # Logic was in galaxy_service.py, moving here or to retrieval
        search_text = f"{task_title} {task_description or ''}"
        nodes = await self.retrieval.semantic_search_nodes(search_text, limit=1)
        if nodes:
            return nodes[0].id

        # Fallback keyword
        nodes_kw = await self.retrieval.keyword_search(
            UUID("00000000-0000-0000-0000-000000000000"), task_title.split()[0], limit=1
        )
        if nodes_kw:
            return nodes_kw[0].id

        return None

    # --- Delegated to GalaxyStatsService ---

    async def spark_node(
        self,
        user_id: UUID,
        node_id: UUID,
        study_minutes: int,
        task_id: UUID | None = None,
        trigger_expansion: bool = True,
    ) -> SparkResult:
        return await self.stats.spark_node(user_id, node_id, study_minutes, task_id, trigger_expansion)

    async def predict_next_node(self, user_id: UUID) -> NodeWithStatus | None:
        return await self.stats.predict_next_node(user_id)

    async def get_heatmap_data(self, user_id: UUID) -> list[dict]:
        """Get forget curve heatmap data"""
        return await self.stats.get_heatmap_data(user_id)

    async def auto_link_nodes(self, node_id: UUID) -> int:
        """Run auto-link worker logic for a node"""
        # Note: In Facade we access ExpansionService via stats service or structure?
        # Actually ExpansionService is initialized in GalaxyService directly usually or via Stats
        # Looking at __init__, it's not there.
        # But StatsService has it.
        return await self.stats.expansion_service.auto_link_nodes(node_id)

    @staticmethod
    def sprint_node_uuid(external_node_id: str) -> UUID:
        """Stable internal UUID for Sprint Pack node IDs such as `cn.tcp_flow_control`."""
        return uuid5(SPRINT_NODE_UUID_NAMESPACE, str(external_node_id or "").strip())

    @staticmethod
    def _mastery_ratio(value: object) -> float:
        try:
            mastery = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if mastery > 1.0:
            mastery = mastery / 100.0
        return max(0.0, min(mastery, 1.0))

    @staticmethod
    def _bkt_probability_from_mastery(value: object) -> float:
        try:
            mastery = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if mastery <= 1.0:
            return max(0.0, min(mastery, 1.0))
        return max(0.0, min(mastery / 100.0, 1.0))

    @staticmethod
    def _coerce_uuid_or_none(value: object) -> UUID | None:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _canonical_sprint_node_id(node_id: object) -> str:
        raw = str(node_id or "").strip()
        return SPRINT_NODE_ID_ALIASES.get(raw, raw)

    def _lookup_sprint_node_metadata(self, external_node_id: str) -> dict[str, object]:
        external_node_id = self._canonical_sprint_node_id(external_node_id)
        try:
            from app.sprint_packs.sprint_pack_registry import PACKS_DIR

            for path in sorted(PACKS_DIR.glob("*_v1.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                for node in list(payload.get("knowledge_nodes") or []):
                    if str(node.get("node_id") or "").strip() == external_node_id:
                        return {
                            "pack_id": payload.get("id") or path.stem,
                            "subject": payload.get("subject"),
                            "node": node,
                        }
        except Exception as exc:
            logger.debug("GalaxyService: failed to resolve sprint node metadata for {}: {}", external_node_id, exc)
        return {"node": {"node_id": external_node_id, "label": external_node_id}}

    async def _resolve_mastery_node_id(self, node_id: UUID | str, *, create_missing: bool) -> UUID:
        uuid_value = self._coerce_uuid_or_none(node_id)
        if uuid_value is not None:
            return uuid_value

        external_node_id = self._canonical_sprint_node_id(node_id)
        if not external_node_id:
            raise ValueError("node_id is required")

        resolved_id = self.sprint_node_uuid(external_node_id)
        if not create_missing:
            return resolved_id

        existing = await self.db.get(KnowledgeNode, resolved_id)
        if existing is not None:
            return resolved_id

        metadata = self._lookup_sprint_node_metadata(external_node_id)
        node_meta = metadata.get("node") if isinstance(metadata.get("node"), dict) else {}
        node_label = str(node_meta.get("label") or external_node_id).strip()
        subject = str(metadata.get("subject") or "").strip()
        description = str(node_meta.get("recommended_action") or "").strip()
        keywords = [
            "sprint_pack_node",
            external_node_id,
            *(str(item).strip() for item in list(node_meta.get("common_mistakes") or []) if str(item).strip()),
        ]
        knowledge_node = KnowledgeNode(
            id=resolved_id,
            name=node_label[:255] or external_node_id,
            description=description or f"Sprint Pack node: {external_node_id}",
            keywords=list(dict.fromkeys(keywords)),
            importance_level=max(1, min(5, int(round(float(node_meta.get("exam_weight") or 0.6) * 5)))),
            is_seed=True,
            source_type="sprint_pack",
            dominant_sector_code="TECH" if external_node_id.startswith(("cn.", "os.", "ds.")) else "VOID",
            sector_weights={"TECH": 100} if external_node_id.startswith(("cn.", "os.", "ds.")) else {"VOID": 100},
            sector_classification_status="completed",
            sector_classification_model="sprint_pack",
            sector_classified_at=_utcnow(),
            position_x=None,
            position_y=None,
            status="published",
        )
        if subject:
            knowledge_node.keywords = list(dict.fromkeys([*knowledge_node.keywords, subject]))
        self.db.add(knowledge_node)
        await self.db.flush()
        return resolved_id

    async def get_sprint_mastery_summary(self, user_id: UUID, node_ids: list[str]) -> dict[str, float]:
        """Return normalized 0-1 mastery for the requested Sprint Pack node IDs."""
        ordered_ids = [str(node_id or "").strip() for node_id in node_ids if str(node_id or "").strip()]
        if not ordered_ids:
            return {}

        unique_ids = list(dict.fromkeys(ordered_ids))
        internal_by_external = {
            external_id: await self._resolve_mastery_node_id(external_id, create_missing=False)
            for external_id in unique_ids
        }
        result = {external_id: 0.0 for external_id in unique_ids}

        rows = (
            await self.db.execute(
                select(UserNodeStatus.node_id, UserNodeStatus.mastery_score).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id.in_(list(internal_by_external.values())),
                )
            )
        ).all()
        mastery_by_node_id = {node_uuid: self._mastery_ratio(mastery_score) for node_uuid, mastery_score in rows}
        for external_id, internal_id in internal_by_external.items():
            result[external_id] = mastery_by_node_id.get(internal_id, 0.0)
        return result

    @staticmethod
    def _latest_datetime(*values: datetime | None) -> datetime | None:
        datetimes = [value for value in values if isinstance(value, datetime)]
        if not datetimes:
            return None
        return max(datetimes)

    @staticmethod
    def _compact_node_label(label: object) -> str:
        text_value = str(label or "").strip()
        for separator in ("（", "(", "：", ":"):
            if separator in text_value:
                text_value = text_value.split(separator, 1)[0].strip()
        return text_value

    @staticmethod
    def _error_text_haystack(error: ErrorRecord) -> str:
        latest_analysis = getattr(error, "latest_analysis", None)
        try:
            latest_analysis_text = json.dumps(latest_analysis or {}, ensure_ascii=False)
        except TypeError:
            latest_analysis_text = str(latest_analysis or "")
        return "\n".join(
            str(item or "")
            for item in (
                getattr(error, "question_text", None),
                getattr(error, "user_answer", None),
                getattr(error, "correct_answer", None),
                getattr(error, "ai_analysis_summary", None),
                latest_analysis_text,
            )
        ).lower()

    def _error_matches_history_node(
        self,
        error: ErrorRecord,
        *,
        resolved_node_id: UUID | None,
        requested_node_id: str,
        canonical_node_id: str,
        node_label: str | None,
    ) -> bool:
        if resolved_node_id is not None:
            primary_id = self._coerce_uuid_or_none(getattr(error, "affected_node_id", None))
            linked_ids = {
                node_id
                for node_id in (
                    self._coerce_uuid_or_none(value)
                    for value in (getattr(error, "linked_knowledge_node_ids", None) or [])
                )
                if node_id is not None
            }
            if primary_id == resolved_node_id or resolved_node_id in linked_ids:
                return True

        haystack = self._error_text_haystack(error)
        needles = {
            requested_node_id,
            canonical_node_id,
            str(node_label or ""),
            self._compact_node_label(node_label),
            self._compact_node_label(node_label).replace(" ", ""),
        }
        return any(needle and needle.lower() in haystack for needle in needles)

    @staticmethod
    def _error_analysis_summary(error: ErrorRecord) -> str | None:
        if error.ai_analysis_summary:
            return str(error.ai_analysis_summary)
        latest_analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        for key in ("root_cause", "error_type_label", "study_suggestion", "correct_approach"):
            value = latest_analysis.get(key)
            if value:
                return str(value)
        return None

    async def get_node_history(
        self,
        *,
        user_id: UUID,
        node_id: str,
        pack_id: str | None = None,
        related_errors_limit: int = 2,
    ) -> dict[str, object]:
        """Return a user's personal study/error history for a Galaxy or Sprint Pack node."""
        del pack_id  # Reserved for future pack-specific disambiguation.
        requested_node_id = str(node_id or "").strip()
        if not requested_node_id:
            raise ValueError("node_id is required")

        uuid_value = self._coerce_uuid_or_none(requested_node_id)
        canonical_node_id = requested_node_id if uuid_value is not None else self._canonical_sprint_node_id(node_id)
        resolved_node_id = uuid_value or await self._resolve_mastery_node_id(canonical_node_id, create_missing=False)

        node = await self.db.get(KnowledgeNode, resolved_node_id) if resolved_node_id is not None else None
        metadata = self._lookup_sprint_node_metadata(canonical_node_id)
        node_meta = metadata.get("node") if isinstance(metadata.get("node"), dict) else {}
        node_label = (
            str(getattr(node, "name", "") or "").strip()
            or str(node_meta.get("label") or "").strip()
            or requested_node_id
        )

        status = None
        study_record_count = 0
        latest_study_record_at = None
        if resolved_node_id is not None:
            status = await self.db.get(UserNodeStatus, (user_id, resolved_node_id))
            study_result = await self.db.execute(
                select(func.count(StudyRecord.id), func.max(StudyRecord.created_at)).where(
                    StudyRecord.user_id == user_id,
                    StudyRecord.node_id == resolved_node_id,
                )
            )
            study_record_count, latest_study_record_at = study_result.one()

        mastery = self._mastery_ratio(getattr(status, "mastery_score", 0.0) if status else 0.0)
        study_count = max(
            int(getattr(status, "study_count", 0) or 0) if status else 0,
            int(study_record_count or 0),
        )
        last_studied_at = self._latest_datetime(
            getattr(status, "last_study_at", None) if status else None,
            latest_study_record_at,
            getattr(status, "last_interacted_at", None) if status and study_count > 0 else None,
        )

        error_limit = max(1, min(int(related_errors_limit or 2), 10))
        error_scan_result = await self.db.execute(
            select(ErrorRecord)
            .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
            .order_by(ErrorRecord.created_at.desc())
            .limit(max(50, error_limit * 10))
        )
        related_errors = []
        for error in error_scan_result.scalars().all():
            if not self._error_matches_history_node(
                error,
                resolved_node_id=resolved_node_id,
                requested_node_id=requested_node_id,
                canonical_node_id=canonical_node_id,
                node_label=node_label,
            ):
                continue
            related_errors.append(
                {
                    "id": error.id,
                    "question_text": error.question_text,
                    "question_image_url": error.question_image_url,
                    "subject_code": error.subject_code,
                    "chapter": error.chapter,
                    "mastery_level": float(error.mastery_level or 0.0),
                    "review_count": int(error.review_count or 0),
                    "analysis_summary": self._error_analysis_summary(error),
                    "affected_node_id": error.affected_node_id,
                    "linked_knowledge_node_ids": [str(value) for value in (error.linked_knowledge_node_ids or [])],
                    "created_at": error.created_at,
                    "last_reviewed_at": error.last_reviewed_at,
                }
            )
            if len(related_errors) >= error_limit:
                break

        return {
            "node_id": requested_node_id,
            "resolved_node_id": resolved_node_id,
            "node_label": node_label,
            "mastery": mastery,
            "last_studied_at": last_studied_at,
            "study_count": study_count,
            "related_errors": related_errors,
        }

    @staticmethod
    def _is_first_activation_reason(reason: str) -> bool:
        normalized = str(reason or "").strip().lower()
        return normalized in {
            "task_complete",
            "sprint_task_completed",
            "focus_session",
        }

    @staticmethod
    def _is_error_repair_reason(reason: str) -> bool:
        normalized = str(reason or "").strip().lower()
        return normalized.startswith("error_review") or normalized in {
            "post_exam_review_weak_node",
        }

    @staticmethod
    def _is_conversation_update_reason(reason: str) -> bool:
        normalized = str(reason or "").strip().lower()
        if normalized in {"knowledge_service_increment"}:
            return True
        return any(
            token in normalized
            for token in ("conversation", "chat", "dialog", "dialogue", "writeback", "correction", "user_correction")
        )

    async def get_user_contribution_stats(self, user_id: UUID) -> UserGalaxyContribution:
        """Aggregate contribution stats from mastery history audit records."""
        if not await self._table_exists("mastery_audit_log"):
            return UserGalaxyContribution()

        rows = (
            await self.db.execute(
                text("""
                    SELECT
                        mal.node_id,
                        COALESCE(kn.name, '未命名节点') AS node_name,
                        COALESCE(mal.old_mastery, 0) AS old_mastery,
                        COALESCE(mal.new_mastery, 0) AS new_mastery,
                        COALESCE(mal.reason, '') AS reason,
                        mal.created_at
                    FROM mastery_audit_log AS mal
                    LEFT JOIN knowledge_nodes AS kn
                        ON kn.id = mal.node_id
                    WHERE mal.user_id = :user_id
                      AND COALESCE(mal.new_mastery, 0) > COALESCE(mal.old_mastery, 0)
                    ORDER BY mal.created_at DESC, mal.id DESC
                """),
                {"user_id": str(user_id)},
            )
        ).mappings()

        first_activated: dict[str, GalaxyContributionNode] = {}
        error_repaired: dict[str, GalaxyContributionNode] = {}
        conversation_updated: dict[str, GalaxyContributionNode] = {}

        for row in rows:
            node_id = row["node_id"]
            if node_id is None:
                continue

            reason = str(row["reason"] or "")
            old_mastery = float(row["old_mastery"] or 0.0)
            new_mastery = float(row["new_mastery"] or 0.0)
            node_key = str(node_id)
            item = GalaxyContributionNode(
                node_id=node_id,
                node_name=str(row["node_name"] or "未命名节点"),
                reason=reason or None,
                mastery_delta=int(round(new_mastery - old_mastery)),
                updated_at=row["created_at"],
            )

            if (
                old_mastery <= 0
                and new_mastery > 0
                and self._is_first_activation_reason(reason)
                and node_key not in first_activated
            ):
                first_activated[node_key] = item

            if self._is_error_repair_reason(reason) and node_key not in error_repaired:
                error_repaired[node_key] = item

            if self._is_conversation_update_reason(reason) and node_key not in conversation_updated:
                conversation_updated[node_key] = item

        return UserGalaxyContribution(
            first_activation_count=len(first_activated),
            error_repaired_count=len(error_repaired),
            conversation_updated_count=len(conversation_updated),
            first_activated_nodes=list(first_activated.values()),
            error_repaired_nodes=list(error_repaired.values()),
            conversation_updated_nodes=list(conversation_updated.values()),
        )

    async def update_node_mastery(
        self,
        user_id: UUID,
        node_id: UUID | str,
        new_mastery: float,
        reason: str,
        version: datetime | None = None,
        request_id: str | None = None,
        revision: int | None = None,
    ):
        """
        Update node mastery with Outbox pattern and atomic revision checking to prevent race conditions.

        Race condition fix (C1): Uses atomic UPDATE with WHERE revision = expected_revision
        and RETURNING clause to detect conflicts in a single database operation.
        """

        def _to_utc_naive(dt: datetime | None) -> datetime | None:
            if dt is None:
                return None
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt

        node_id = await self._resolve_mastery_node_id(node_id, create_missing=True)
        new_mastery = max(0.0, min(float(new_mastery), 100.0))
        update_time = _to_utc_naive(version) or _utcnow()
        bkt_mastery_prob = self._bkt_probability_from_mastery(new_mastery)
        dialect_name = self.db.bind.dialect.name if self.db.bind is not None else ""

        try:
            # === ATOMIC UPDATE WITH OPTIMISTIC LOCKING ===
            # If revision is provided, use atomic conditional UPDATE to prevent race conditions
            if revision is not None:
                if dialect_name == "postgresql":
                    # Atomic update: lock the expected revision row, then update and return the pre-update mastery.
                    atomic_update = text("""
                        WITH current AS (
                            SELECT mastery_score
                            FROM user_node_status
                            WHERE user_id = :user_id
                              AND node_id = :node_id
                              AND revision = :expected_revision
                            FOR UPDATE
                        ),
                        updated AS (
                            UPDATE user_node_status AS status
                            SET mastery_score = :mastery,
                                bkt_mastery_prob = :bkt_mastery_prob,
                                bkt_last_updated_at = :updated_at,
                                updated_at = :updated_at,
                                last_study_at = :updated_at,
                                last_interacted_at = :updated_at,
                                is_unlocked = true,
                                revision = status.revision + 1
                            FROM current
                            WHERE status.user_id = :user_id
                              AND status.node_id = :node_id
                              AND status.revision = :expected_revision
                            RETURNING status.revision AS new_revision
                        )
                        SELECT current.mastery_score AS old_mastery, updated.new_revision
                        FROM current, updated
                    """)
                    result = await self.db.execute(
                        atomic_update,
                        {
                            "user_id": user_id,
                            "node_id": node_id,
                            "mastery": new_mastery,
                            "bkt_mastery_prob": bkt_mastery_prob,
                            "expected_revision": revision,
                            "updated_at": update_time,
                        },
                    )
                    row = result.fetchone()

                    if not row:
                        # Revision mismatch - concurrent update occurred
                        # Fetch current revision for conflict response
                        current_query = text("""
                            SELECT revision FROM user_node_status
                            WHERE user_id = :user_id AND node_id = :node_id
                        """)
                        current_result = await self.db.execute(current_query, {"user_id": user_id, "node_id": node_id})
                        current_row = current_result.fetchone()
                        current_revision = current_row[0] if current_row else 0

                        logger.warning(
                            f"Atomic update conflict for node {node_id}. Expected revision {revision}, current is {current_revision}"
                        )
                        await self.db.rollback()
                        return {"success": False, "reason": "conflict", "current_revision": current_revision}

                    old_mastery = row[0] if row else 0
                    new_revision = row[1]
                else:
                    status = await self.db.get(UserNodeStatus, (user_id, node_id))
                    current_revision = int(status.revision or 0) if status else 0
                    if status is None or current_revision != revision:
                        logger.warning(
                            f"Mastery update conflict for node {node_id}. Expected revision {revision}, current is {current_revision}"
                        )
                        await self.db.rollback()
                        return {"success": False, "reason": "conflict", "current_revision": current_revision}
                    old_mastery = float(status.mastery_score or 0.0)
                    new_revision = current_revision + 1
                    status.mastery_score = new_mastery
                    status.bkt_mastery_prob = bkt_mastery_prob
                    status.bkt_last_updated_at = update_time
                    status.updated_at = update_time
                    status.last_study_at = update_time
                    status.last_interacted_at = update_time
                    status.is_unlocked = True
                    status.revision = new_revision
                    await self.db.flush()

            else:
                # === FALLBACK: UPSERT WITHOUT OPTIMISTIC LOCKING (legacy path) ===
                # Get current state first (for audit log and conflict detection via timestamp)
                if dialect_name != "postgresql":
                    status = await self.db.get(UserNodeStatus, (user_id, node_id))
                    if status:
                        old_mastery = float(status.mastery_score or 0.0)
                        current_updated_at = _to_utc_naive(status.updated_at)
                        current_revision = int(status.revision or 0)
                        if version and current_updated_at and _to_utc_naive(version) <= current_updated_at:
                            logger.warning(
                                f"Ignoring stale update (Time) for node {node_id}. Incoming version {version} <= current {current_updated_at}"
                            )
                            return {"success": False, "reason": "stale_update", "current_revision": current_revision}
                        new_revision = current_revision + 1
                        status.mastery_score = new_mastery
                        status.bkt_mastery_prob = bkt_mastery_prob
                        status.bkt_last_updated_at = update_time
                        status.updated_at = update_time
                        status.last_study_at = update_time
                        status.last_interacted_at = update_time
                        status.is_unlocked = True
                        status.revision = new_revision
                    else:
                        old_mastery = 0.0
                        new_revision = 1
                        self.db.add(
                            UserNodeStatus(
                                user_id=user_id,
                                node_id=node_id,
                                mastery_score=new_mastery,
                                bkt_mastery_prob=bkt_mastery_prob,
                                bkt_last_updated_at=update_time,
                                updated_at=update_time,
                                last_study_at=update_time,
                                last_interacted_at=update_time,
                                is_unlocked=True,
                                revision=new_revision,
                                first_unlock_at=update_time,
                            )
                        )
                    await self.db.flush()
                else:
                    query_current = text("""
                        SELECT mastery_score, updated_at, revision
                        FROM user_node_status
                        WHERE user_id = :user_id AND node_id = :node_id
                    """)
                    result = await self.db.execute(query_current, {"user_id": user_id, "node_id": node_id})
                    current = result.fetchone()

                    if current:
                        old_mastery = current[0]
                        current_updated_at = _to_utc_naive(current[1])
                        current_revision = current[2] or 0

                        # Fallback to Physical Clock conflict detection (Legacy)
                        if version and current_updated_at and _to_utc_naive(version) <= current_updated_at:
                            logger.warning(
                                f"Ignoring stale update (Time) for node {node_id}. Incoming version {version} <= current {current_updated_at}"
                            )
                            return {"success": False, "reason": "stale_update", "current_revision": current_revision}
                    else:
                        old_mastery = 0
                        current_revision = 0

                    new_revision = current_revision + 1
                    # UPSERT pattern for non-revision cases
                    # Use atomic revision increment to prevent TOCTOU race
                    upsert_query = text("""
                        INSERT INTO user_node_status (
                            user_id,
                            node_id,
                            mastery_score,
                            bkt_mastery_prob,
                            bkt_last_updated_at,
                            updated_at,
                            last_study_at,
                            is_unlocked,
                            revision,
                            total_minutes,
                            total_study_minutes,
                            last_interacted_at,
                            created_at,
                            study_count,
                            is_collapsed,
                            is_favorite,
                            decay_paused
                        )
                        VALUES (
                            :user_id,
                            :node_id,
                            :mastery,
                            :bkt_mastery_prob,
                            :updated_at,
                            :updated_at,
                            :updated_at,
                            true,
                            :revision,
                            0,
                            0,
                            :updated_at,
                            :updated_at,
                            0,
                            false,
                            false,
                            false
                        )
                        ON CONFLICT (user_id, node_id) DO UPDATE SET
                            mastery_score = EXCLUDED.mastery_score,
                            bkt_mastery_prob = EXCLUDED.bkt_mastery_prob,
                            bkt_last_updated_at = EXCLUDED.bkt_last_updated_at,
                            updated_at = EXCLUDED.updated_at,
                            last_study_at = EXCLUDED.updated_at,
                            last_interacted_at = EXCLUDED.updated_at,
                            is_unlocked = true,
                            revision = user_node_status.revision + 1
                    """)

                    await self.db.execute(
                        upsert_query,
                        {
                            "user_id": user_id,
                            "node_id": node_id,
                            "mastery": new_mastery,
                            "bkt_mastery_prob": bkt_mastery_prob,
                            "updated_at": update_time,
                            "revision": new_revision,
                        },
                    )
                    # Re-read the actual revision after atomic increment
                    rev_result = await self.db.execute(
                        text("SELECT revision FROM user_node_status WHERE user_id = :user_id AND node_id = :node_id"),
                        {"user_id": user_id, "node_id": node_id},
                    )
                    rev_row = rev_result.fetchone()
                    if rev_row:
                        new_revision = rev_row[0]

            # === COMMON: Update Global Stats, Audit Log, Outbox ===
            # A. Update Global Stats (Collaborative Sparking)
            is_new_spark = old_mastery == 0 and new_mastery > 0
            if is_new_spark:
                node = await self.db.get(KnowledgeNode, node_id)
                if node is not None:
                    node.global_spark_count = int(node.global_spark_count or 0) + 1

            # B. Audit Log
            if await self._table_exists("mastery_audit_log"):
                audit_query = text("""
                    INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision)
                    VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision)
                """)
                await self.db.execute(
                    audit_query,
                    {
                        "node_id": node_id,
                        "user_id": user_id,
                        "old_mastery": int(old_mastery),
                        "new_mastery": int(round(new_mastery)),
                        "reason": reason,
                        "request_id": request_id,
                        "revision": new_revision,
                    },
                )

            # 4. Invalidate Semantic Cache (User specific)
            from app.services.semantic_cache_service import semantic_cache_service

            if semantic_cache_service:
                # We invalidate all cache for this user since we don't know which queries
                # might be affected by this specific node's mastery change.
                # In a more advanced version, we could use tags or query-to-node mapping.
                # await semantic_cache_service.invalidate_user_cache(str(user_id))
                pass  # Pattern for broad invalidation if needed, or rely on TTL.
                # Actually, mastery score might not change the retrieved nodes, just their status.
                # Since status is re-fetched in hybrid_search, we might not need to invalidate nodes cache!

            # 5. Add to Outbox
            await self._write_mastery_outbox_event(
                aggregate_id=user_id,
                event_type="galaxy.node.mastery_updated",
                payload={
                    "user_id": str(user_id),
                    "node_id": str(node_id),
                    "mastery_score": new_mastery,
                    "revision": new_revision,
                    "timestamp": _utcnow().isoformat(),
                },
            )

            await self.db.flush()

            await self.db.commit()
            await cache_service.delete_pattern(f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*")

            if new_mastery >= 80:
                await self._process_mastery_achievement_after_commit(
                    user_id=user_id,
                    node_id=node_id,
                    new_mastery=new_mastery,
                )

            return {
                "success": True,
                "old_mastery": float(old_mastery or 0.0),
                "new_mastery": new_mastery,
                "current_revision": new_revision,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update node mastery: {e}")
            raise e

    async def _process_mastery_achievement_after_commit(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
    ) -> None:
        """Process mastery achievements after the primary transaction is durable."""
        try:
            from app.db.session import AsyncSessionLocal
            from app.services.achievement_engine import AchievementEngine, AchievementEvent

            async with AsyncSessionLocal() as achievement_db:
                achievement_engine = AchievementEngine(achievement_db)
                await achievement_engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.NODE_MASTERED,
                    node_id=str(node_id),
                    mastery_score=new_mastery,
                )
        except Exception as e:
            logger.warning(f"Achievement processing failed after mastery commit: {e}")

    # --- Async Background Processing ---

    async def _process_node_background(self, node_id: UUID, title: str, summary: str):
        """
        Background Worker for Node Processing:
        1. Generate Embedding
        2. Deduplication Check (Notify if duplicate)
        """
        logger.info(f"Starting background processing for node {node_id}")

        # We need a new session for background task as the original request session might be closed
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            try:
                # 1. Generate Embedding
                text = f"{title}\n{summary}"
                embedding = await embedding_service.get_embedding(text)

                # Update Node
                node = await session.get(KnowledgeNode, node_id)
                if node:
                    node.embedding = embedding
                    session.add(node)
                    await session.commit()
                    logger.info(f"Generated embedding for node {node_id}")

                    # 2. Check Deduplication (Post-creation check)
                    # Find similar nodes (excluding self)
                    retrieval = KnowledgeRetrievalService(session)
                    similar = await retrieval.semantic_search_nodes(title, limit=2, threshold=0.1)

                    for sim in similar:
                        if sim.id != node_id:
                            logger.warning(f"Potential duplicate found for {node_id}: {sim.id} ({sim.name})")
                            # TRACKED(TD-006): Create Notification for user to merge
                            # notification_service.create_system_notification(...)
                            break

            except Exception as e:
                logger.error(f"Background processing failed for node {node_id}: {e}")
