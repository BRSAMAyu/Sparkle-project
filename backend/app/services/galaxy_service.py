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
from uuid import UUID

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service, cached
from app.core.event_bus import KnowledgeNodeUpdated, event_bus
from app.gen.sparkle.rag.v1 import evidence_pb2
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.galaxy import UserNodeStatus
from app.schemas.galaxy import (
    GalaxyGraphResponse,
    NodeRelationInfo,
    NodeWithStatus,
    SearchResultItem,
    SparkResult,
)
from app.services.embedding_service import embedding_service
from app.services.expansion_service import ExpansionService, validate_knowledge_node_name
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.galaxy.ontology_generator import relation_type_to_wire_name
from app.services.galaxy.ontology_generator import OntologyExtractionResult, OntologyGenerator
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.galaxy.structure_service import GraphStructureService
from app.services.node_sector_service import NodeSectorService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GalaxyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.structure = GraphStructureService(db)
        self.retrieval = KnowledgeRetrievalService(db)
        self.stats = GalaxyStatsService(db)
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
        event_outbox_exists = (
            await self.db.execute(text("SELECT to_regclass('event_outbox')"))
        ).scalar_one_or_none()
        if event_outbox_exists:
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

        legacy_outbox_exists = (
            await self.db.execute(text("SELECT to_regclass('outbox_events')"))
        ).scalar_one_or_none()
        if legacy_outbox_exists:
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

        # 6. Assemble with Flutter-compatible fields
        return GalaxyGraphResponse(
            nodes=[
                NodeWithStatus.from_models(node, status, recent_error_count=error_counts.get(node.id, 0))
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
                for nid in (linked_ids or []):
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

    async def update_node_mastery(
        self,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
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

        update_time = _to_utc_naive(version) or _utcnow()
        bkt_mastery_prob = max(0.0, min(float(new_mastery) / 100.0, 1.0))

        try:
            # === ATOMIC UPDATE WITH OPTIMISTIC LOCKING ===
            # If revision is provided, use atomic conditional UPDATE to prevent race conditions
            if revision is not None:
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
                result = await self.db.execute(atomic_update, {
                    "user_id": user_id,
                    "node_id": node_id,
                    "mastery": new_mastery,
                    "bkt_mastery_prob": bkt_mastery_prob,
                    "expected_revision": revision,
                    "updated_at": update_time,
                })
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
                # === FALLBACK: UPSERT WITHOUT OPTIMISTIC LOCKING (legacy path) ===
                # Get current state first (for audit log and conflict detection via timestamp)
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
                        updated_at = EXCLUDED.updated_at,
                        last_study_at = EXCLUDED.updated_at,
                        is_unlocked = true,
                        revision = EXCLUDED.revision
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

            # === COMMON: Update Global Stats, Audit Log, Outbox ===
            # A. Update Global Stats (Collaborative Sparking)
            is_new_spark = old_mastery == 0 and new_mastery > 0
            if is_new_spark:
                global_update = text("""
                    UPDATE knowledge_nodes
                    SET global_spark_count = global_spark_count + 1
                    WHERE id = :node_id
                """)
                await self.db.execute(global_update, {"node_id": node_id})

            # B. Audit Log
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
                    "new_mastery": new_mastery,
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
                "old_mastery": int(old_mastery),
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
