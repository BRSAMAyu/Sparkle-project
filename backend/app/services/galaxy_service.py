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
import math
import re
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from loguru import logger
from sqlalchemy import and_, delete, func, inspect, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, undefer

from app.config import settings
from app.core.cache import cache_service, cached
from app.core.event_bus import event_bus
from app.gen.sparkle.rag.v1 import evidence_pb2
from app.models.document_chunks import DocumentChunk
from app.models.error_book import ErrorRecord
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument, NodeRelation, StudyRecord, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.schemas.galaxy import (
    DraftGalaxyNode,
    GalaxyContributionNode,
    GalaxyGraphResponse,
    NodeChunksResponse,
    NodeDocumentRef,
    NodeKnowledgeStats,
    NodeRelationInfo,
    NodeSourceChunk,
    NodeWithStatus,
    ReviewDocumentNodesResponse,
    ReviewNodeDecision,
    ReviewNodeResult,
    SearchResultItem,
    SparkResult,
    SuggestedDocumentNode,
    SuggestedNodeSimilarity,
    UserGalaxyContribution,
)
from app.services.embedding_service import embedding_service
from app.services.expansion_service import ExpansionService, validate_knowledge_node_name
from app.services.galaxy.ontology_generator import (
    OntologyExtractionResult,
    OntologyGenerator,
    relation_type_to_wire_name,
)
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.galaxy.review_urgency_service import ReviewUrgencyService
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.galaxy.structure_service import GraphStructureService
from app.services.node_sector_service import NodeSectorService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
        [DEPRECATED] Do NOT call — mastery is owned by ErrorBookMasterySyncService.
        Calling this will cause double mastery deductions.
        """
        logger.warning(
            "Blocked deprecated GalaxyService.handle_error_created call; "
            "mastery updates are owned by ErrorBookMasterySyncService"
        )
        return None

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
        [DEPRECATED] Do NOT call — mastery is owned by ErrorBookMasterySyncService.
        Calling this will cause double mastery deductions.
        """
        logger.warning(
            "Blocked deprecated GalaxyService.update_mastery_from_error call; "
            "mastery updates are owned by ErrorBookMasterySyncService"
        )
        return None

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

    async def get_sprint_mastery_rollup(
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

        self.db.add(
            KnowledgeNodeDocument(
                user_id=user_id,
                node_id=root_node.id,
                file_id=file_id,
                is_primary=True,
            )
        )
        for child in created_nodes:
            self.db.add(
                KnowledgeNodeDocument(
                    user_id=user_id,
                    node_id=child.id,
                    file_id=file_id,
                    is_primary=False,
                )
            )

        await self.db.commit()
        await expansion_service._invalidate_after_graph_mutation(user_id)
        return {
            "root_node": root_node,
            "created_nodes": created_nodes,
            "created_relations": created_relations,
            "ontology": ontology.to_dict(),
        }

    async def attach_document_to_node(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        file_id: UUID,
        is_primary: bool = False,
    ) -> dict[str, object]:
        node = await self._get_existing_node(node_id)
        file_record = await self._get_owned_file(user_id, file_id)

        link = await self._upsert_document_link(
            user_id=user_id,
            node=node,
            file_record=file_record,
            is_primary=is_primary,
        )
        await self.db.commit()
        await self._invalidate_document_attachment_cache(user_id)
        await self._publish_document_attachment_event(
            action="attached",
            user_id=user_id,
            node_id=node_id,
            file_id=file_id,
            is_primary=bool(link.is_primary),
            chunk_refs=node.chunk_refs,
        )
        return await self._document_link_payload(link=link, file_record=file_record, node=node)

    async def detach_document_from_node(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        file_id: UUID,
    ) -> dict[str, object]:
        node = await self._get_existing_node(node_id)
        file_record = await self._get_owned_file(user_id, file_id)
        link = await self._get_document_link(user_id=user_id, node_id=node_id, file_id=file_id)
        had_legacy_link = node.source_file_id == file_id

        if not link and not had_legacy_link:
            raise LookupError("Document attachment not found")

        was_primary = bool(link.is_primary) if link else bool(had_legacy_link)
        if link:
            await self.db.execute(delete(KnowledgeNodeDocument).where(KnowledgeNodeDocument.id == link.id))
        if had_legacy_link:
            node.source_file_id = None
            node.chunk_refs = None

        await self.db.commit()
        await self._invalidate_document_attachment_cache(user_id)
        await self._publish_document_attachment_event(
            action="detached",
            user_id=user_id,
            node_id=node_id,
            file_id=file_id,
            is_primary=was_primary,
            chunk_refs=None,
        )
        return {
            "status": "success",
            "action": "detached",
            "node_id": str(node_id),
            "file_id": str(file_record.id),
            "was_primary": was_primary,
        }

    async def move_document_primary_node(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        from_node_id: UUID,
        to_node_id: UUID,
    ) -> dict[str, object]:
        if from_node_id == to_node_id:
            raise ValueError("from_node_id and to_node_id must be different")

        file_record = await self._get_owned_file(user_id, file_id)
        from_node = await self._get_existing_node(from_node_id)
        to_node = await self._get_existing_node(to_node_id)
        from_link = await self._get_document_link(user_id=user_id, node_id=from_node_id, file_id=file_id)
        had_legacy_link = from_node.source_file_id == file_id

        if not from_link and not had_legacy_link:
            raise LookupError("Source document attachment not found")

        moved_chunk_refs = from_node.chunk_refs if had_legacy_link else None

        if from_link:
            await self.db.execute(delete(KnowledgeNodeDocument).where(KnowledgeNodeDocument.id == from_link.id))
        if had_legacy_link:
            from_node.source_file_id = None
            from_node.chunk_refs = None

        to_link = await self._upsert_document_link(
            user_id=user_id,
            node=to_node,
            file_record=file_record,
            is_primary=True,
        )
        if moved_chunk_refs is not None and not to_node.chunk_refs:
            to_node.chunk_refs = moved_chunk_refs

        await self.db.commit()
        await self._invalidate_document_attachment_cache(user_id)
        await self._publish_document_attachment_event(
            action="moved",
            user_id=user_id,
            node_id=to_node_id,
            file_id=file_id,
            is_primary=True,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            chunk_refs=to_node.chunk_refs,
        )
        return {
            "status": "success",
            "action": "moved",
            "file_id": str(file_record.id),
            "from_node_id": str(from_node_id),
            "to_node_id": str(to_node_id),
            "attachment": await self._document_link_payload(link=to_link, file_record=file_record, node=to_node),
        }

    async def list_node_documents(self, *, user_id: UUID, node_id: UUID) -> list[dict[str, object]]:
        node = await self._get_existing_node(node_id)
        chunk_counts = (
            select(DocumentChunk.file_id, func.count(DocumentChunk.id).label("chunk_count"))
            .where(DocumentChunk.user_id == user_id)
            .group_by(DocumentChunk.file_id)
            .subquery()
        )
        rows = (
            await self.db.execute(
                select(KnowledgeNodeDocument, StoredFile, chunk_counts.c.chunk_count)
                .join(StoredFile, StoredFile.id == KnowledgeNodeDocument.file_id)
                .outerjoin(chunk_counts, chunk_counts.c.file_id == KnowledgeNodeDocument.file_id)
                .where(KnowledgeNodeDocument.user_id == user_id)
                .where(KnowledgeNodeDocument.node_id == node_id)
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
                .where(StoredFile.deleted_at.is_(None))
                .order_by(KnowledgeNodeDocument.is_primary.desc(), StoredFile.file_name.asc())
            )
        ).all()

        payloads: list[dict[str, object]] = []
        seen_file_ids: set[UUID] = set()
        for link, file_record, chunk_count in rows:
            seen_file_ids.add(file_record.id)
            payloads.append(
                await self._document_link_payload(
                    link=link,
                    file_record=file_record,
                    node=node,
                    chunk_count=int(chunk_count or 0),
                )
            )

        if node.source_file_id and node.source_file_id not in seen_file_ids:
            legacy_file = await self._get_owned_file_or_none(user_id, node.source_file_id)
            if legacy_file:
                payloads.append(
                    await self._document_link_payload(
                        link=None,
                        file_record=legacy_file,
                        node=node,
                        is_primary=True,
                    )
                )

        return payloads

    async def list_document_nodes(self, *, user_id: UUID, file_id: UUID) -> list[dict[str, object]]:
        await self._get_owned_file(user_id, file_id)
        rows = (
            await self.db.execute(
                select(KnowledgeNodeDocument, KnowledgeNode)
                .join(KnowledgeNode, KnowledgeNode.id == KnowledgeNodeDocument.node_id)
                .where(KnowledgeNodeDocument.user_id == user_id)
                .where(KnowledgeNodeDocument.file_id == file_id)
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
                .where(KnowledgeNode.deleted_at.is_(None))
                .order_by(KnowledgeNodeDocument.is_primary.desc(), KnowledgeNode.name.asc())
            )
        ).all()

        payloads: list[dict[str, object]] = []
        seen_node_ids: set[UUID] = set()
        for link, node in rows:
            seen_node_ids.add(node.id)
            payloads.append(self._node_link_payload(link=link, node=node))

        legacy_nodes = (
            await self.db.execute(
                select(KnowledgeNode)
                .where(KnowledgeNode.source_file_id == file_id)
                .where(KnowledgeNode.deleted_at.is_(None))
                .order_by(KnowledgeNode.name.asc())
            )
        ).scalars().all()
        for node in legacy_nodes:
            if node.id in seen_node_ids:
                continue
            payloads.append(self._node_link_payload(link=None, node=node, is_primary=True))

        return payloads

    async def summarize_study_materials_for_planning(
        self,
        *,
        user_id: UUID,
        topic_hints: list[str] | None = None,
        preferred_file_ids: list[UUID | str] | None = None,
        limit_documents: int = 8,
    ) -> dict[str, Any]:
        """Return a planning-oriented summary of uploaded study materials.

        This is an internal integration surface for the planning pipeline. It keeps
        the existing Galaxy document API intact while exposing richer context:
        uploaded filenames, node attachments, section structure, and per-node
        mastery so plans can anchor tasks to actual study materials.
        """
        preferred_ids = {
            file_id
            for raw_file_id in list(preferred_file_ids or [])
            if (file_id := self._coerce_uuid_or_none(raw_file_id)) is not None
        }
        cleaned_topic_hints = [
            hint
            for raw_hint in list(topic_hints or [])
            if (hint := str(raw_hint or "").strip())
        ]

        explicit_rows = (
            await self.db.execute(
                select(KnowledgeNodeDocument, KnowledgeNode, StoredFile, UserNodeStatus)
                .join(KnowledgeNode, KnowledgeNode.id == KnowledgeNodeDocument.node_id)
                .join(StoredFile, StoredFile.id == KnowledgeNodeDocument.file_id)
                .outerjoin(
                    UserNodeStatus,
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.node_id == KnowledgeNode.id,
                    ),
                )
                .where(KnowledgeNodeDocument.user_id == user_id)
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
                .where(KnowledgeNode.deleted_at.is_(None))
                .where(StoredFile.deleted_at.is_(None))
            )
        ).all()

        attachment_index: dict[tuple[UUID, UUID], dict[str, Any]] = {}
        file_records: dict[UUID, StoredFile] = {}
        node_records: dict[UUID, KnowledgeNode] = {}

        for link, node, file_record, status in explicit_rows:
            file_records[file_record.id] = file_record
            node_records[node.id] = node
            attachment_index[(node.id, file_record.id)] = {
                "node": node,
                "file": file_record,
                "mastery_score": float(getattr(status, "mastery_score", 0.0) or 0.0),
                "is_primary": bool(link.is_primary),
                "is_legacy": False,
            }

        legacy_rows = (
            await self.db.execute(
                select(KnowledgeNode, StoredFile, UserNodeStatus)
                .join(StoredFile, StoredFile.id == KnowledgeNode.source_file_id)
                .outerjoin(
                    UserNodeStatus,
                    and_(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.node_id == KnowledgeNode.id,
                    ),
                )
                .where(StoredFile.user_id == user_id)
                .where(KnowledgeNode.source_file_id.is_not(None))
                .where(KnowledgeNode.deleted_at.is_(None))
                .where(StoredFile.deleted_at.is_(None))
            )
        ).all()
        for node, file_record, status in legacy_rows:
            file_records[file_record.id] = file_record
            node_records[node.id] = node
            attachment_index.setdefault(
                (node.id, file_record.id),
                {
                    "node": node,
                    "file": file_record,
                    "mastery_score": float(getattr(status, "mastery_score", 0.0) or 0.0),
                    "is_primary": True,
                    "is_legacy": True,
                },
            )

        if not file_records:
            return {
                "documents": [],
                "available_materials": [],
                "matched_documents_count": 0,
                "has_materials": False,
                "topic_hints": cleaned_topic_hints,
            }

        file_ids = list(file_records.keys())
        chunk_rows = (
            await self.db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.user_id == user_id)
                .where(DocumentChunk.file_id.in_(file_ids))
                .where(DocumentChunk.deleted_at.is_(None))
                .order_by(DocumentChunk.file_id.asc(), DocumentChunk.chunk_index.asc())
            )
        ).scalars().all()

        chunks_by_file: dict[UUID, list[DocumentChunk]] = {}
        for chunk in chunk_rows:
            chunks_by_file.setdefault(chunk.file_id, []).append(chunk)

        documents: list[dict[str, Any]] = []
        matched_documents_count = 0
        for file_id, file_record in file_records.items():
            file_chunks = list(chunks_by_file.get(file_id) or [])
            section_rollups = self._build_planning_section_rollups(file_chunks)
            document_attachments: list[dict[str, Any]] = []

            for (node_id, attachment_file_id), attachment in attachment_index.items():
                if attachment_file_id != file_id:
                    continue
                node = attachment["node"]
                node_chunks = self._resolve_node_file_chunks(node=node, file_id=file_id, file_chunks=file_chunks)
                section_titles = self._ordered_unique(
                    [
                        str(chunk.section_title or "").strip()
                        for chunk in node_chunks
                        if str(chunk.section_title or "").strip()
                    ],
                    limit=6,
                )
                attachment_read_minutes = self._estimate_read_minutes(node_chunks)
                document_attachments.append(
                    {
                        "node_id": str(node_id),
                        "node_name": str(node.name or ""),
                        "mastery_score": float(attachment.get("mastery_score") or 0.0),
                        "is_primary": bool(attachment.get("is_primary")),
                        "section_titles": section_titles,
                        "estimated_read_minutes": attachment_read_minutes,
                        "chunk_count": len(node_chunks),
                    }
                )

            query_match_score = self._planning_document_query_score(
                file_name=str(file_record.file_name or ""),
                section_rollups=section_rollups,
                attachments=document_attachments,
                topic_hints=cleaned_topic_hints,
                preferred=bool(file_id in preferred_ids),
            )
            if query_match_score > 0:
                matched_documents_count += 1

            documents.append(
                {
                    "file_id": str(file_record.id),
                    "file_name": str(file_record.file_name or ""),
                    "mime_type": str(file_record.mime_type or ""),
                    "upload_date": file_record.created_at.isoformat() if file_record.created_at else None,
                    "document_quality_score": float(file_record.document_quality_score or 0.0),
                    "estimated_read_minutes": self._estimate_read_minutes(file_chunks),
                    "section_titles": [item["section_title"] for item in section_rollups],
                    "sections": section_rollups,
                    "node_attachments": sorted(
                        document_attachments,
                        key=lambda item: (
                            not bool(item.get("is_primary")),
                            float(item.get("mastery_score") or 0.0),
                            str(item.get("node_name") or ""),
                        ),
                    ),
                    "query_match_score": query_match_score,
                    "preferred": bool(file_id in preferred_ids),
                }
            )

        if matched_documents_count == 0 and len(documents) == 1:
            documents[0]["query_match_score"] = max(float(documents[0].get("query_match_score") or 0.0), 0.25)
            matched_documents_count = 1

        documents.sort(
            key=lambda item: (
                float(item.get("query_match_score") or 0.0),
                1.0 if bool(item.get("preferred")) else 0.0,
                item.get("upload_date") or "",
            ),
            reverse=True,
        )
        if limit_documents > 0:
            documents = documents[:limit_documents]

        return {
            "documents": documents,
            "available_materials": [str(item.get("file_name") or "") for item in documents if str(item.get("file_name") or "").strip()],
            "matched_documents_count": matched_documents_count,
            "has_materials": bool(documents),
            "topic_hints": cleaned_topic_hints,
        }

    @staticmethod
    def _ordered_unique(items: list[str], *, limit: int | None = None) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
            if limit is not None and len(ordered) >= limit:
                break
        return ordered

    @staticmethod
    def _estimate_read_minutes(chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0

        latin_words = 0
        cjk_chars = 0
        for chunk in chunks:
            text = str(getattr(chunk, "content", "") or "")
            latin_words += len(re.findall(r"[A-Za-z0-9_]+", text))
            cjk_chars += len(re.findall(r"[\u4e00-\u9fff]", text))

        reading_units = latin_words + int(cjk_chars * 0.8)
        estimated = math.ceil(reading_units / 180) if reading_units else 0
        return max(estimated, 5 if reading_units else 0)

    def _build_planning_section_rollups(self, chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
        grouped: dict[str, list[DocumentChunk]] = {}
        for chunk in chunks:
            section_title = str(chunk.section_title or "").strip() or "General"
            grouped.setdefault(section_title, []).append(chunk)

        rollups: list[dict[str, Any]] = []
        for section_title, section_chunks in grouped.items():
            pages = sorted(
                {
                    int(page)
                    for section_chunk in section_chunks
                    for page in list(section_chunk.page_numbers or [])
                    if isinstance(page, int | float)
                }
            )
            rollups.append(
                {
                    "section_title": section_title,
                    "chunk_count": len(section_chunks),
                    "page_numbers": pages,
                    "estimated_read_minutes": self._estimate_read_minutes(section_chunks),
                }
            )

        rollups.sort(key=lambda item: (item["section_title"] == "General", item["section_title"].lower()))
        return rollups

    def _resolve_node_file_chunks(
        self,
        *,
        node: KnowledgeNode,
        file_id: UUID,
        file_chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        chunk_id_refs, chunk_index_refs, _, has_refs = self._parse_chunk_refs(node.chunk_refs)
        if has_refs:
            matched = [
                chunk
                for chunk in file_chunks
                if (chunk_id_refs and chunk.id in chunk_id_refs)
                or (chunk_index_refs and int(chunk.chunk_index or 0) in chunk_index_refs)
            ]
            if matched:
                return matched

        node_tokens = self._planning_match_keys(
            [node.name, node.description, *(list(node.keywords or []) if isinstance(node.keywords, list) else [])]
        )
        if not node_tokens:
            return []

        matched_by_title = [
            chunk
            for chunk in file_chunks
            if self._planning_text_matches(str(chunk.section_title or ""), node_tokens)
        ]
        if matched_by_title:
            return matched_by_title
        return []

    def _planning_document_query_score(
        self,
        *,
        file_name: str,
        section_rollups: list[dict[str, Any]],
        attachments: list[dict[str, Any]],
        topic_hints: list[str],
        preferred: bool,
    ) -> float:
        score = 0.5 if preferred else 0.0
        query_tokens = self._planning_match_keys(topic_hints)
        if not query_tokens:
            return score

        if self._planning_text_matches(file_name, query_tokens):
            score += 2.0

        for attachment in attachments:
            node_name = str(attachment.get("node_name") or "")
            if self._planning_text_matches(node_name, query_tokens):
                score += 3.0
            for section_title in list(attachment.get("section_titles") or []):
                if self._planning_text_matches(str(section_title or ""), query_tokens):
                    score += 1.5
                    break

        for section in section_rollups:
            if self._planning_text_matches(str(section.get("section_title") or ""), query_tokens):
                score += 1.0

        return round(score, 3)

    @staticmethod
    def _planning_match_keys(values: list[Any]) -> list[str]:
        keys: list[str] = []
        for raw_value in values:
            text = str(raw_value or "").strip().lower()
            if not text:
                continue
            parts = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text)
            candidates = [text, *parts]
            for candidate in candidates:
                cleaned = candidate.strip("_ ").lower()
                if len(cleaned) < 2 or cleaned in keys:
                    continue
                keys.append(cleaned)
        return keys

    def _planning_text_matches(self, text: str, query_tokens: list[str]) -> bool:
        haystack = str(text or "").strip().lower()
        if not haystack or not query_tokens:
            return False
        haystack_tokens = self._planning_match_keys([haystack])
        for token in query_tokens:
            if token in haystack:
                return True
            if any(token == hay_token or token in hay_token or hay_token in token for hay_token in haystack_tokens):
                return True
        return False

    async def _upsert_document_link(
        self,
        *,
        user_id: UUID,
        node: KnowledgeNode,
        file_record: StoredFile,
        is_primary: bool,
    ) -> KnowledgeNodeDocument:
        if is_primary:
            await self._clear_primary_document_links(user_id=user_id, file_id=file_record.id)

        link = await self._get_document_link(user_id=user_id, node_id=node.id, file_id=file_record.id)
        if not link:
            link = KnowledgeNodeDocument(
                user_id=user_id,
                node_id=node.id,
                file_id=file_record.id,
                is_primary=is_primary,
            )
            self.db.add(link)
        else:
            link.is_primary = is_primary

        if is_primary:
            node.source_file_id = file_record.id

        await self.db.flush()
        return link

    async def _clear_primary_document_links(self, *, user_id: UUID, file_id: UUID) -> None:
        existing = (
            await self.db.execute(
                select(KnowledgeNodeDocument)
                .where(KnowledgeNodeDocument.user_id == user_id)
                .where(KnowledgeNodeDocument.file_id == file_id)
                .where(KnowledgeNodeDocument.is_primary.is_(True))
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
            )
        ).scalars().all()
        for link in existing:
            link.is_primary = False

    async def _get_document_link(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        file_id: UUID,
    ) -> KnowledgeNodeDocument | None:
        return await self.db.scalar(
            select(KnowledgeNodeDocument)
            .where(KnowledgeNodeDocument.user_id == user_id)
            .where(KnowledgeNodeDocument.node_id == node_id)
            .where(KnowledgeNodeDocument.file_id == file_id)
            .where(KnowledgeNodeDocument.deleted_at.is_(None))
        )

    async def _get_existing_node(self, node_id: UUID) -> KnowledgeNode:
        node = await self.db.get(KnowledgeNode, node_id)
        if not node or node.deleted_at is not None:
            raise LookupError("Knowledge node not found")
        return node

    async def _get_owned_file(self, user_id: UUID, file_id: UUID) -> StoredFile:
        file_record = await self._get_owned_file_or_none(user_id, file_id)
        if not file_record:
            raise LookupError("Document not found")
        return file_record

    async def _get_owned_file_or_none(self, user_id: UUID, file_id: UUID) -> StoredFile | None:
        return await self.db.scalar(
            select(StoredFile)
            .where(StoredFile.id == file_id)
            .where(StoredFile.user_id == user_id)
            .where(StoredFile.deleted_at.is_(None))
        )

    async def _document_link_payload(
        self,
        *,
        link: KnowledgeNodeDocument | None,
        file_record: StoredFile,
        node: KnowledgeNode,
        chunk_count: int | None = None,
        is_primary: bool | None = None,
    ) -> dict[str, object]:
        if chunk_count is None:
            chunk_count = int(
                await self.db.scalar(
                    select(func.count(DocumentChunk.id))
                    .where(DocumentChunk.file_id == file_record.id)
                    .where(DocumentChunk.user_id == file_record.user_id)
                )
                or 0
            )
        primary = bool(link.is_primary) if link else bool(is_primary)
        attached_at = link.created_at if link else node.created_at
        updated_at = link.updated_at if link else node.updated_at
        return {
            "file_id": str(file_record.id),
            "node_id": str(node.id),
            "file_name": file_record.file_name,
            "mime_type": file_record.mime_type,
            "file_size": int(file_record.file_size or 0),
            "status": file_record.status,
            "visibility": file_record.visibility,
            "is_primary": primary,
            "chunk_count": chunk_count,
            "attached_at": attached_at.isoformat() if attached_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    def _node_link_payload(
        self,
        *,
        link: KnowledgeNodeDocument | None,
        node: KnowledgeNode,
        is_primary: bool | None = None,
    ) -> dict[str, object]:
        primary = bool(link.is_primary) if link else bool(is_primary)
        attached_at = link.created_at if link else node.created_at
        updated_at = link.updated_at if link else node.updated_at
        return {
            "node_id": str(node.id),
            "file_id": str(link.file_id) if link else str(node.source_file_id),
            "name": node.name,
            "description": node.description,
            "source_type": node.source_type or "seed",
            "status": node.status or "published",
            "is_primary": primary,
            "chunk_refs": node.chunk_refs,
            "attached_at": attached_at.isoformat() if attached_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    async def _invalidate_document_attachment_cache(self, user_id: UUID) -> None:
        await cache_service.delete_pattern(f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*")
        await cache_service.delete_pattern(f"galaxy:node_source_documents:v1:{user_id}:*")
        await cache_service.delete_pattern(f"galaxy:node_knowledge_stats:v1:{user_id}:*")

    async def _publish_document_attachment_event(
        self,
        *,
        action: str,
        user_id: UUID,
        node_id: UUID,
        file_id: UUID,
        is_primary: bool,
        chunk_refs: object | None,
        from_node_id: UUID | None = None,
        to_node_id: UUID | None = None,
    ) -> None:
        payload = {
            "event_type": "galaxy.document_attachment.changed",
            "action": action,
            "user_id": str(user_id),
            "file_id": str(file_id),
            "node_id": str(node_id),
            "from_node_id": str(from_node_id) if from_node_id else None,
            "to_node_id": str(to_node_id) if to_node_id else None,
            "is_primary": is_primary,
            "chunk_refs": json.loads(json.dumps(chunk_refs, default=str)) if chunk_refs is not None else None,
            "timestamp": _utcnow().isoformat(),
        }
        try:
            await event_bus.publish("galaxy.document_attachment.changed", payload)
        except Exception as exc:
            logger.warning(
                "Failed to publish document attachment event action={} user_id={} file_id={} node_id={}: {}",
                action,
                user_id,
                file_id,
                node_id,
                exc,
            )

    async def get_suggested_nodes_for_document(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> list[SuggestedDocumentNode]:
        draft_nodes = await self._get_user_draft_nodes(user_id=user_id, file_id=file_id)
        return await self._build_suggested_node_payloads(draft_nodes)

    async def get_draft_nodes(
        self,
        *,
        user_id: UUID,
    ) -> list[DraftGalaxyNode]:
        result = await self.db.execute(
            select(KnowledgeNode, StoredFile.file_name)
            .options(undefer(KnowledgeNode.embedding))
            .join(UserNodeStatus, and_(UserNodeStatus.node_id == KnowledgeNode.id, UserNodeStatus.user_id == user_id))
            .outerjoin(StoredFile, StoredFile.id == KnowledgeNode.source_file_id)
            .where(KnowledgeNode.status == "draft")
            .order_by(KnowledgeNode.created_at.desc())
        )
        rows = result.all()
        suggestions = await self._build_suggested_node_payloads([node for node, _file_name in rows])
        suggestion_by_id = {item.node_id: item for item in suggestions}

        drafts: list[DraftGalaxyNode] = []
        for node, file_name in rows:
            suggestion = suggestion_by_id[node.id]
            drafts.append(
                DraftGalaxyNode(
                    node_id=suggestion.node_id,
                    name=suggestion.name,
                    description=suggestion.description,
                    confidence_score=suggestion.confidence_score,
                    similarity_to_existing=suggestion.similarity_to_existing,
                    source_file_id=node.source_file_id,
                    source_file_name=file_name,
                    created_at=node.created_at,
                )
            )
        return drafts

    async def review_document_nodes(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        decisions: list[ReviewNodeDecision],
    ) -> ReviewDocumentNodesResponse:
        if not decisions:
            return ReviewDocumentNodesResponse(file_id=file_id)

        results: list[ReviewNodeResult] = []
        approved_count = 0
        rejected_count = 0
        merged_count = 0

        try:
            for decision in decisions:
                node = await self._get_user_draft_node(user_id=user_id, node_id=decision.node_id, file_id=file_id)
                if decision.action == "approve":
                    self._apply_review_edits(node, decision)
                    node.status = "published"
                    node.updated_at = _utcnow()
                    self.db.add(node)
                    approved_count += 1
                    results.append(ReviewNodeResult(node_id=node.id, action="approve", status="published"))
                    continue

                if decision.action == "reject":
                    await self._delete_draft_node(node)
                    rejected_count += 1
                    results.append(ReviewNodeResult(node_id=node.id, action="reject", status="rejected"))
                    continue

                if decision.action == "merge":
                    if decision.merge_into_node_id is None:
                        raise ValueError("merge_into_node_id is required for merge decisions")
                    target = await self._get_merge_target(decision.merge_into_node_id)
                    self._apply_review_edits(node, decision)
                    await self._merge_draft_node_into_target(
                        user_id=user_id,
                        draft_node=node,
                        target_node=target,
                    )
                    merged_count += 1
                    results.append(
                        ReviewNodeResult(
                            node_id=node.id,
                            action="merge",
                            status="merged",
                            merge_into_node_id=target.id,
                        )
                    )
                    continue

                raise ValueError(f"Unsupported review action: {decision.action}")

            await self.db.commit()
            await NodeSectorService(self.db).invalidate_user_graph_cache(user_id)
            return ReviewDocumentNodesResponse(
                file_id=file_id,
                approved_count=approved_count,
                rejected_count=rejected_count,
                merged_count=merged_count,
                results=results,
            )
        except Exception:
            await self.db.rollback()
            raise

    async def approve_all_document_nodes(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> ReviewDocumentNodesResponse:
        draft_nodes = await self._get_user_draft_nodes(user_id=user_id, file_id=file_id)
        for node in draft_nodes:
            node.status = "published"
            node.updated_at = _utcnow()
            self.db.add(node)

        await self.db.commit()
        await NodeSectorService(self.db).invalidate_user_graph_cache(user_id)
        return ReviewDocumentNodesResponse(
            file_id=file_id,
            approved_count=len(draft_nodes),
            results=[ReviewNodeResult(node_id=node.id, action="approve", status="published") for node in draft_nodes],
        )

    async def _get_user_draft_nodes(self, *, user_id: UUID, file_id: UUID) -> list[KnowledgeNode]:
        result = await self.db.execute(
            select(KnowledgeNode)
            .options(undefer(KnowledgeNode.embedding))
            .join(UserNodeStatus, and_(UserNodeStatus.node_id == KnowledgeNode.id, UserNodeStatus.user_id == user_id))
            .where(KnowledgeNode.source_file_id == file_id)
            .where(KnowledgeNode.status == "draft")
            .order_by(KnowledgeNode.created_at.asc())
        )
        return list(result.scalars().all())

    async def _get_user_draft_node(self, *, user_id: UUID, node_id: UUID, file_id: UUID) -> KnowledgeNode:
        result = await self.db.execute(
            select(KnowledgeNode)
            .options(undefer(KnowledgeNode.embedding))
            .join(UserNodeStatus, and_(UserNodeStatus.node_id == KnowledgeNode.id, UserNodeStatus.user_id == user_id))
            .where(KnowledgeNode.id == node_id)
            .where(KnowledgeNode.source_file_id == file_id)
            .where(KnowledgeNode.status == "draft")
        )
        node = result.scalar_one_or_none()
        if node is None:
            raise ValueError(f"Draft node {node_id} not found for document {file_id}")
        return node

    async def _get_merge_target(self, node_id: UUID) -> KnowledgeNode:
        result = await self.db.execute(
            select(KnowledgeNode)
            .options(undefer(KnowledgeNode.embedding))
            .where(KnowledgeNode.id == node_id)
            .where(or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"))
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise ValueError(f"Merge target {node_id} not found or is not published")
        return target

    async def _build_suggested_node_payloads(self, draft_nodes: list[KnowledgeNode]) -> list[SuggestedDocumentNode]:
        if not draft_nodes:
            return []

        result = await self.db.execute(
            select(KnowledgeNode)
            .options(undefer(KnowledgeNode.embedding))
            .where(or_(KnowledgeNode.status.is_(None), KnowledgeNode.status == "published"))
            .where(KnowledgeNode.embedding.isnot(None))
        )
        existing_nodes = list(result.scalars().all())

        payloads: list[SuggestedDocumentNode] = []
        for node in draft_nodes:
            node_embedding = self._embedding_to_list(node.embedding)
            scored: list[tuple[KnowledgeNode, float]] = []
            if node_embedding:
                for existing in existing_nodes:
                    if existing.id == node.id:
                        continue
                    similarity = self._cosine_similarity(node_embedding, self._embedding_to_list(existing.embedding))
                    if similarity is not None:
                        scored.append((existing, similarity))

            scored.sort(key=lambda item: item[1], reverse=True)
            top_matches = [
                SuggestedNodeSimilarity(
                    node_id=existing.id,
                    name=existing.name,
                    similarity=round(max(0.0, min(1.0, similarity)), 4),
                )
                for existing, similarity in scored[:3]
            ]
            max_similarity = top_matches[0].similarity if top_matches else 0.0
            payloads.append(
                SuggestedDocumentNode(
                    node_id=node.id,
                    name=node.name,
                    description=node.description,
                    confidence_score=round(max(0.0, min(1.0, 1.0 - max_similarity)), 4),
                    similarity_to_existing=top_matches,
                )
            )
        return payloads

    @staticmethod
    def _embedding_to_list(value: object) -> list[float]:
        if value is None:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []
        try:
            return [float(item) for item in value]  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
        if not left or not right:
            return None
        length = min(len(left), len(right))
        dot = sum(left[index] * right[index] for index in range(length))
        left_norm = math.sqrt(sum(left[index] * left[index] for index in range(length)))
        right_norm = math.sqrt(sum(right[index] * right[index] for index in range(length)))
        if left_norm == 0.0 or right_norm == 0.0:
            return None
        return dot / (left_norm * right_norm)

    @staticmethod
    def _apply_review_edits(node: KnowledgeNode, decision: ReviewNodeDecision) -> None:
        if decision.edited_name is not None:
            validate_knowledge_node_name(decision.edited_name)
            node.name = decision.edited_name
        if decision.edited_description is not None:
            node.description = decision.edited_description

    async def _delete_draft_node(self, node: KnowledgeNode) -> None:
        if node.status != "draft":
            raise ValueError(f"Only draft nodes can be removed during review (node status: {node.status})")
        await self.db.execute(
            delete(NodeRelation).where(
                or_(NodeRelation.source_node_id == node.id, NodeRelation.target_node_id == node.id)
            )
        )
        await self.db.execute(delete(KnowledgeNodeDocument).where(KnowledgeNodeDocument.node_id == node.id))
        await self.db.execute(delete(UserNodeStatus).where(UserNodeStatus.node_id == node.id))
        await self.db.delete(node)

    async def _merge_draft_node_into_target(
        self,
        *,
        user_id: UUID,
        draft_node: KnowledgeNode,
        target_node: KnowledgeNode,
    ) -> None:
        if draft_node.id == target_node.id:
            raise ValueError("Cannot merge a draft node into itself")

        target_node.chunk_refs = self._merge_chunk_refs(target_node.chunk_refs, draft_node.chunk_refs)
        if target_node.source_file_id is None:
            target_node.source_file_id = draft_node.source_file_id
        target_node.updated_at = _utcnow()
        self.db.add(target_node)

        draft_status = await self.db.get(UserNodeStatus, (user_id, draft_node.id))
        target_status = await self.db.get(UserNodeStatus, (user_id, target_node.id))
        if target_status is None:
            target_status = UserNodeStatus(
                user_id=user_id,
                node_id=target_node.id,
                is_unlocked=bool(getattr(draft_status, "is_unlocked", True)),
                mastery_score=float(getattr(draft_status, "mastery_score", 0.0) or 0.0),
                bkt_mastery_prob=float(getattr(draft_status, "bkt_mastery_prob", 0.0) or 0.0),
                first_unlock_at=getattr(draft_status, "first_unlock_at", None) or _utcnow(),
            )
            self.db.add(target_status)
        else:
            target_status.is_unlocked = True
            target_status.updated_at = _utcnow()

        await self._transfer_document_links_for_merge(user_id, draft_node.id, target_node.id)
        await self._rewire_relations_for_merge(draft_node.id, target_node.id)
        await self._delete_draft_node(draft_node)

    @staticmethod
    def _merge_chunk_refs(existing: object, incoming: object) -> object:
        if incoming in (None, [], {}):
            return existing
        if existing in (None, [], {}):
            return incoming

        def as_list(value: object) -> list[object]:
            if isinstance(value, list):
                return value
            return [value]

        if isinstance(existing, dict) or isinstance(incoming, dict):
            merged: dict[str, object] = {}
            existing_items = (
                existing.items() if isinstance(existing, dict) else [(item, True) for item in as_list(existing)]
            )
            incoming_items = (
                incoming.items() if isinstance(incoming, dict) else [(item, True) for item in as_list(incoming)]
            )
            merged.update({str(key): value for key, value in existing_items})
            merged.update({str(key): value for key, value in incoming_items})
            return merged

        merged_list: list[object] = []
        for item in [*as_list(existing), *as_list(incoming)]:
            if item not in merged_list:
                merged_list.append(item)
        return merged_list

    async def _rewire_relations_for_merge(self, draft_node_id: UUID, target_node_id: UUID) -> None:
        result = await self.db.execute(
            select(NodeRelation).where(
                or_(NodeRelation.source_node_id == draft_node_id, NodeRelation.target_node_id == draft_node_id)
            )
        )
        for relation in result.scalars().all():
            new_source_id = target_node_id if relation.source_node_id == draft_node_id else relation.source_node_id
            new_target_id = target_node_id if relation.target_node_id == draft_node_id else relation.target_node_id
            if new_source_id == new_target_id:
                await self.db.delete(relation)
                continue
            duplicate = await self.db.scalar(
                select(NodeRelation).where(
                    NodeRelation.id != relation.id,
                    NodeRelation.source_node_id == new_source_id,
                    NodeRelation.target_node_id == new_target_id,
                    NodeRelation.relation_type == relation.relation_type,
                )
            )
            if duplicate:
                duplicate.strength = max(float(duplicate.strength or 0.0), float(relation.strength or 0.0))
                await self.db.delete(relation)
                continue
            relation.source_node_id = new_source_id
            relation.target_node_id = new_target_id
            self.db.add(relation)

    async def _transfer_document_links_for_merge(
        self, user_id: UUID, draft_node_id: UUID, target_node_id: UUID
    ) -> None:
        result = await self.db.execute(
            select(KnowledgeNodeDocument).where(
                KnowledgeNodeDocument.user_id == user_id,
                KnowledgeNodeDocument.node_id == draft_node_id,
                KnowledgeNodeDocument.deleted_at.is_(None),
            )
        )
        for link in result.scalars().all():
            duplicate = await self.db.scalar(
                select(KnowledgeNodeDocument).where(
                    KnowledgeNodeDocument.user_id == user_id,
                    KnowledgeNodeDocument.node_id == target_node_id,
                    KnowledgeNodeDocument.file_id == link.file_id,
                    KnowledgeNodeDocument.deleted_at.is_(None),
                )
            )
            if duplicate:
                duplicate.is_primary = bool(duplicate.is_primary or link.is_primary)
                await self.db.delete(link)
                continue
            link.node_id = target_node_id
            self.db.add(link)

    async def get_node_source_documents(self, user_id: UUID, node_id: UUID) -> list[NodeDocumentRef]:
        """Return source-document provenance for a node, cached separately from mastery detail."""
        cache_key = f"galaxy:node_source_documents:v1:{user_id}:{node_id}"
        cached_docs = await cache_service.get(cache_key)
        if cached_docs is not None:
            return [NodeDocumentRef.model_validate(item) for item in cached_docs]

        docs = await self._load_node_source_documents(user_id=user_id, node_id=node_id)
        await cache_service.set(
            cache_key,
            [doc.model_dump(mode="json") for doc in docs],
            ttl=1800,
        )
        return docs

    async def get_node_knowledge_stats(self, user_id: UUID, node_id: UUID) -> NodeKnowledgeStats:
        """Return document-level knowledge stats using a shorter, independent cache."""
        cache_key = f"galaxy:node_knowledge_stats:v1:{user_id}:{node_id}"
        cached_stats = await cache_service.get(cache_key)
        if cached_stats is not None:
            return NodeKnowledgeStats.model_validate(cached_stats)

        source_documents = await self.get_node_source_documents(user_id=user_id, node_id=node_id)
        upload_dates = [doc.upload_date for doc in source_documents if doc.upload_date is not None]
        stats = NodeKnowledgeStats(
            total_documents=len(source_documents),
            total_chunks=sum(doc.chunk_count for doc in source_documents),
            has_personal_uploads=bool(source_documents),
            last_material_added=max(upload_dates) if upload_dates else None,
        )
        await cache_service.set(cache_key, stats.model_dump(mode="json"), ttl=300)
        return stats

    async def get_node_document_chunks(
        self,
        *,
        user_id: UUID,
        node_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> NodeChunksResponse:
        """Return paginated source chunks attached to a Galaxy node."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        node = await self.db.get(KnowledgeNode, node_id)
        if not node:
            return NodeChunksResponse(node_id=node_id, page=page, page_size=page_size)

        chunk_id_refs, chunk_index_refs, chunk_scores, has_refs = self._parse_chunk_refs(node.chunk_refs)
        file_ids = await self._get_node_source_file_ids(user_id=user_id, node=node)
        if not file_ids:
            return NodeChunksResponse(node_id=node_id, page=page, page_size=page_size)

        conditions = []
        if has_refs:
            if chunk_id_refs:
                conditions.append(DocumentChunk.id.in_(chunk_id_refs))
            if chunk_index_refs:
                conditions.append(DocumentChunk.chunk_index.in_(chunk_index_refs))
            if not conditions:
                return NodeChunksResponse(node_id=node_id, page=page, page_size=page_size)

        count_stmt = (
            select(func.count(DocumentChunk.id))
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .where(DocumentChunk.user_id == user_id)
            .where(StoredFile.user_id == user_id)
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
        )
        if conditions:
            count_stmt = count_stmt.where(or_(*conditions))
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        stmt = (
            select(DocumentChunk, StoredFile)
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .where(DocumentChunk.user_id == user_id)
            .where(StoredFile.user_id == user_id)
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
            .order_by(DocumentChunk.chunk_index.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if conditions:
            stmt = stmt.where(or_(*conditions))

        result = await self.db.execute(stmt)
        chunks = [
            self._serialize_node_source_chunk(chunk=chunk, file_record=file_record)
            for chunk, file_record in result.all()
        ]
        if chunk_scores:
            chunks.sort(key=lambda item: chunk_scores.get(str(item.chunk_id), 0.0), reverse=True)

        total_pages = (total + page_size - 1) // page_size if total else 0
        return NodeChunksResponse(
            node_id=node_id,
            chunks=chunks,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1 and total_pages > 0,
        )

    async def _load_node_source_documents(self, *, user_id: UUID, node_id: UUID) -> list[NodeDocumentRef]:
        node = await self.db.get(KnowledgeNode, node_id)
        if not node:
            return []

        file_ids = await self._get_node_source_file_ids(user_id=user_id, node=node)
        if not file_ids:
            return []

        chunk_id_refs, chunk_index_refs, chunk_scores, has_refs = self._parse_chunk_refs(node.chunk_refs)
        conditions = []
        if has_refs:
            if chunk_id_refs:
                conditions.append(DocumentChunk.id.in_(chunk_id_refs))
            if chunk_index_refs:
                conditions.append(DocumentChunk.chunk_index.in_(chunk_index_refs))
            if not conditions:
                return []

        stmt = (
            select(DocumentChunk, StoredFile)
            .join(StoredFile, StoredFile.id == DocumentChunk.file_id)
            .where(DocumentChunk.user_id == user_id)
            .where(StoredFile.user_id == user_id)
            .where(DocumentChunk.file_id.in_(file_ids))
            .where(DocumentChunk.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
            .order_by(DocumentChunk.chunk_index.asc())
        )
        if conditions:
            stmt = stmt.where(or_(*conditions))

        result = await self.db.execute(stmt)
        rows = result.all()
        if not rows:
            return []

        chunks_by_file: dict[UUID, list[DocumentChunk]] = {}
        files_by_id: dict[UUID, StoredFile] = {}
        for chunk, file_record in rows:
            chunks_by_file.setdefault(file_record.id, []).append(chunk)
            files_by_id[file_record.id] = file_record

        documents: list[NodeDocumentRef] = []
        for file_id, chunks in chunks_by_file.items():
            if chunk_scores:
                ranked_chunks = sorted(chunks, key=lambda chunk: chunk_scores.get(str(chunk.id), 0.0), reverse=True)
            else:
                ranked_chunks = sorted(chunks, key=lambda chunk: int(chunk.chunk_index or 0))
            file_record = files_by_id[file_id]
            documents.append(
                NodeDocumentRef(
                    file_id=file_id,
                    filename=str(file_record.file_name or ""),
                    file_type=file_record.mime_type,
                    upload_date=file_record.created_at,
                    chunk_count=len(chunks),
                    preview_chunks=[self._preview_text(chunk.content) for chunk in ranked_chunks[:3]],
                )
            )

        documents.sort(key=lambda doc: doc.upload_date or datetime.min, reverse=True)
        return documents

    async def _get_node_source_file_ids(self, *, user_id: UUID, node: KnowledgeNode) -> list[UUID]:
        result = await self.db.execute(
            select(KnowledgeNodeDocument.file_id)
            .where(KnowledgeNodeDocument.user_id == user_id)
            .where(KnowledgeNodeDocument.node_id == node.id)
            .where(KnowledgeNodeDocument.deleted_at.is_(None))
            .order_by(KnowledgeNodeDocument.is_primary.desc(), KnowledgeNodeDocument.created_at.desc())
        )
        file_ids = list(dict.fromkeys(result.scalars().all()))
        if node.source_file_id and node.source_file_id not in file_ids:
            file_ids.insert(0, node.source_file_id)
        return file_ids

    @staticmethod
    def _parse_chunk_refs(chunk_refs: object) -> tuple[set[UUID], set[int], dict[str, float], bool]:
        chunk_ids: set[UUID] = set()
        chunk_indices: set[int] = set()
        chunk_scores: dict[str, float] = {}

        def parse_one(raw_ref: object, raw_score: object = None) -> None:
            ref = raw_ref
            score = raw_score
            if isinstance(raw_ref, dict):
                ref = raw_ref.get("chunk_id") or raw_ref.get("id") or raw_ref.get("chunk_index") or raw_ref.get("index")
                score = raw_ref.get("score") or raw_ref.get("relevance") or raw_ref.get("weight")
            if ref is None:
                return
            if isinstance(ref, int):
                chunk_indices.add(ref)
                return
            ref_text = str(ref).strip()
            if not ref_text:
                return
            if ref_text.isdigit():
                chunk_indices.add(int(ref_text))
                return
            try:
                chunk_id = UUID(ref_text)
            except ValueError:
                return
            chunk_ids.add(chunk_id)
            try:
                chunk_scores[str(chunk_id)] = float(score)
            except (TypeError, ValueError):
                pass

        if isinstance(chunk_refs, list):
            for item in chunk_refs:
                parse_one(item)
        elif isinstance(chunk_refs, dict):
            for key, value in chunk_refs.items():
                parse_one(key, value)

        return chunk_ids, chunk_indices, chunk_scores, bool(chunk_refs)

    @staticmethod
    def _preview_text(content: str | None, *, max_sentences: int = 3, max_chars: int = 480) -> str:
        text = " ".join(str(content or "").split())
        if not text:
            return ""

        sentence_endings = {".", "!", "?", "。", "！", "？"}
        sentences: list[str] = []
        start = 0
        for index, char in enumerate(text):
            if char in sentence_endings:
                sentence = text[start : index + 1].strip()
                if sentence:
                    sentences.append(sentence)
                start = index + 1
                if len(sentences) >= max_sentences:
                    break
        if not sentences:
            preview = text
        else:
            preview = " ".join(sentences)

        if len(preview) > max_chars:
            preview = preview[: max_chars - 1].rstrip() + "…"
        return preview

    def _serialize_node_source_chunk(self, *, chunk: DocumentChunk, file_record: StoredFile) -> NodeSourceChunk:
        return NodeSourceChunk(
            chunk_id=chunk.id,
            file_id=file_record.id,
            filename=str(file_record.file_name or ""),
            file_type=file_record.mime_type,
            chunk_index=int(chunk.chunk_index or 0),
            content=str(chunk.content or ""),
            preview=self._preview_text(chunk.content),
            page_numbers=list(chunk.page_numbers or []),
            section_title=chunk.section_title,
            quality_score=float(chunk.quality_score) if chunk.quality_score is not None else None,
            created_at=chunk.created_at,
        )

    async def get_node_neighbors(self, node_id: UUID, limit: int = 5) -> list[KnowledgeNode]:
        """Get connected neighbor nodes (Graph RAG support)"""
        return await self.structure.get_node_neighbors(node_id, limit)

    async def get_user_node_mastery_scores(
        self,
        user_id: UUID | str,
        node_ids: list[UUID | str],
    ) -> dict[UUID, float]:
        """Return mastery scores for a user's linked knowledge nodes."""
        user_uuid = self._coerce_uuid_or_none(user_id)
        normalized_node_ids = [
            node_uuid for node_id in node_ids if (node_uuid := self._coerce_uuid_or_none(node_id)) is not None
        ]
        if user_uuid is None or not normalized_node_ids:
            return {}

        stmt = select(UserNodeStatus.node_id, UserNodeStatus.mastery_score).where(
            UserNodeStatus.user_id == user_uuid,
            UserNodeStatus.node_id.in_(normalized_node_ids),
        )
        result = await self.db.execute(stmt)
        return {node_id: float(mastery_score or 0.0) for node_id, mastery_score in result.all()}

    async def find_relation_bridge(
        self,
        source_node_ids: list[UUID | str],
        target_node_ids: list[UUID | str],
        *,
        relation_types: set[str] | None = None,
    ) -> dict[str, object] | None:
        """Find the strongest direct or one-bridge connection between two node sets."""
        source_ids = [
            node_uuid for node_id in source_node_ids if (node_uuid := self._coerce_uuid_or_none(node_id)) is not None
        ]
        target_ids = [
            node_uuid for node_id in target_node_ids if (node_uuid := self._coerce_uuid_or_none(node_id)) is not None
        ]
        if not source_ids or not target_ids:
            return None

        allowed_relation_types = {str(item).strip().lower() for item in (relation_types or set()) if str(item).strip()}
        if not allowed_relation_types:
            allowed_relation_types = {"prerequisite", "related", "application", "composition", "evolution"}

        relation_weight = {
            "application": 1.4,
            "prerequisite": 1.3,
            "related": 1.0,
            "composition": 0.9,
            "evolution": 0.8,
        }

        source_set = set(source_ids)
        target_set = set(target_ids)
        seed_ids = list(source_set | target_set)
        source_node = aliased(KnowledgeNode)
        target_node = aliased(KnowledgeNode)

        async def _load_edges(node_ids: list[UUID]) -> list[dict[str, object]]:
            if not node_ids:
                return []
            stmt = (
                select(
                    NodeRelation.source_node_id,
                    NodeRelation.target_node_id,
                    NodeRelation.relation_type,
                    NodeRelation.strength,
                    source_node.name,
                    target_node.name,
                )
                .join(source_node, source_node.id == NodeRelation.source_node_id)
                .join(target_node, target_node.id == NodeRelation.target_node_id)
                .where(
                    func.lower(NodeRelation.relation_type).in_(allowed_relation_types),
                    or_(
                        NodeRelation.source_node_id.in_(node_ids),
                        NodeRelation.target_node_id.in_(node_ids),
                    ),
                )
            )
            result = await self.db.execute(stmt)
            edges: list[dict[str, object]] = []
            for source_id, target_id, relation_type, strength, source_name, target_name in result.all():
                normalized_type = str(relation_type or "").strip().lower() or "related"
                edges.append(
                    {
                        "source_node_id": source_id,
                        "target_node_id": target_id,
                        "relation_type": normalized_type,
                        "strength": float(strength or 0.0),
                        "source_name": str(source_name or ""),
                        "target_name": str(target_name or ""),
                    }
                )
            return edges

        first_hop_edges = await _load_edges(seed_ids)
        if not first_hop_edges:
            return None

        seen_keys: set[tuple[UUID, UUID, str]] = set()

        def _dedupe(edges: list[dict[str, object]]) -> list[dict[str, object]]:
            deduped: list[dict[str, object]] = []
            for edge in edges:
                key = (
                    edge["source_node_id"],
                    edge["target_node_id"],
                    str(edge["relation_type"]),
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped.append(edge)
            return deduped

        first_hop_edges = _dedupe(first_hop_edges)

        best_path: dict[str, object] | None = None

        def _score(edge: dict[str, object]) -> float:
            relation_type = str(edge.get("relation_type") or "related")
            return float(edge.get("strength") or 0.0) * relation_weight.get(relation_type, 1.0)

        def _set_best(candidate: dict[str, object]) -> None:
            nonlocal best_path
            if best_path is None or float(candidate.get("score") or 0.0) > float(best_path.get("score") or 0.0):
                best_path = candidate

        for edge in first_hop_edges:
            source_id = edge["source_node_id"]
            target_id = edge["target_node_id"]
            if (source_id in source_set and target_id in target_set) or (source_id in target_set and target_id in source_set):
                _set_best(
                    {
                        "path_type": "direct",
                        "score": _score(edge),
                        "path_nodes": [edge["source_name"], edge["target_name"]],
                        "path_node_ids": [str(source_id), str(target_id)],
                        "relation_chain": [edge["relation_type"]],
                        "edges": [edge],
                    }
                )

        bridge_ids = {
            edge["target_node_id"] if edge["source_node_id"] in source_set | target_set else edge["source_node_id"]
            for edge in first_hop_edges
        }
        bridge_ids = {bridge_id for bridge_id in bridge_ids if bridge_id not in source_set and bridge_id not in target_set}
        second_hop_edges = _dedupe(await _load_edges(list(bridge_ids)))
        all_edges = first_hop_edges + second_hop_edges

        edges_by_bridge: dict[UUID, list[dict[str, object]]] = {}
        for edge in all_edges:
            for node_id in (edge["source_node_id"], edge["target_node_id"]):
                if node_id in bridge_ids:
                    edges_by_bridge.setdefault(node_id, []).append(edge)

        for bridge_id, bridge_edges in edges_by_bridge.items():
            from_source = [
                edge
                for edge in bridge_edges
                if (
                    edge["source_node_id"] in source_set and edge["target_node_id"] == bridge_id
                ) or (
                    edge["target_node_id"] in source_set and edge["source_node_id"] == bridge_id
                )
            ]
            to_target = [
                edge
                for edge in bridge_edges
                if (
                    edge["source_node_id"] in target_set and edge["target_node_id"] == bridge_id
                ) or (
                    edge["target_node_id"] in target_set and edge["source_node_id"] == bridge_id
                )
            ]
            if not from_source or not to_target:
                continue

            for left_edge in from_source:
                for right_edge in to_target:
                    bridge_name = (
                        left_edge["source_name"]
                        if left_edge["source_node_id"] == bridge_id
                        else left_edge["target_name"]
                    )
                    path_node_ids = [
                        str(
                            left_edge["source_node_id"]
                            if left_edge["source_node_id"] in source_set
                            else left_edge["target_node_id"]
                        ),
                        str(bridge_id),
                        str(
                            right_edge["source_node_id"]
                            if right_edge["source_node_id"] in target_set
                            else right_edge["target_node_id"]
                        ),
                    ]
                    path_nodes = [
                        left_edge["source_name"]
                        if left_edge["source_node_id"] in source_set
                        else left_edge["target_name"],
                        bridge_name,
                        right_edge["source_name"]
                        if right_edge["source_node_id"] in target_set
                        else right_edge["target_name"],
                    ]
                    _set_best(
                        {
                            "path_type": "bridge",
                            "score": _score(left_edge) + _score(right_edge),
                            "path_nodes": path_nodes,
                            "path_node_ids": path_node_ids,
                            "relation_chain": [
                                left_edge["relation_type"],
                                right_edge["relation_type"],
                            ],
                            "edges": [left_edge, right_edge],
                        }
                    )

        return best_path

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

            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
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

    async def get_sprint_mastery_summary(self, user_id: UUID | str, node_ids: list[str]) -> dict[str, float]:
        """Return normalized 0-1 mastery for the requested Sprint Pack node IDs."""
        states = await self.get_sprint_mastery_states(user_id, node_ids)
        return {
            external_id: self._mastery_ratio(state.get("mastery_score", 0.0)) for external_id, state in states.items()
        }

    async def get_sprint_mastery_states(
        self,
        user_id: UUID | str,
        node_ids: list[str],
    ) -> dict[str, dict[str, float | int | None]]:
        """Return 0-100 mastery and revision for requested Sprint Pack node IDs."""
        ordered_ids = [str(node_id or "").strip() for node_id in node_ids if str(node_id or "").strip()]
        if not ordered_ids:
            return {}

        unique_ids = list(dict.fromkeys(ordered_ids))
        internal_by_external = {
            external_id: await self._resolve_mastery_node_id(external_id, create_missing=False)
            for external_id in unique_ids
        }
        result: dict[str, dict[str, float | int | None]] = {
            external_id: {"mastery_score": 0.0, "revision": None} for external_id in unique_ids
        }

        rows = (
            await self.db.execute(
                select(UserNodeStatus.node_id, UserNodeStatus.mastery_score, UserNodeStatus.revision).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id.in_(list(internal_by_external.values())),
                )
            )
        ).all()
        state_by_node_id = {
            node_uuid: {
                "mastery_score": self._mastery_score_percent(mastery_score),
                "revision": int(revision or 0),
            }
            for node_uuid, mastery_score, revision in rows
        }
        for external_id, internal_id in internal_by_external.items():
            result[external_id] = state_by_node_id.get(internal_id, result[external_id])
        return result

    @staticmethod
    def _mastery_score_percent(value: object) -> float:
        try:
            mastery = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if 0.0 < mastery <= 1.0:
            mastery *= 100.0
        return max(0.0, min(mastery, 100.0))

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
                return dt.astimezone(UTC).replace(tzinfo=None)
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
