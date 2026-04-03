from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card_protocol import (
    BindingMode,
    Card,
    CardAdoptionRecord,
    CardCreatedBy,
    CardEdge,
    CardLifecycleStatus,
    CardShareRecord,
    CardSnapshot,
    CardSourceType,
    CardType,
    CardVisibility,
    EdgeType,
    ImportMode,
    SharePermission,
    ShareScope,
)
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import PlanPriority, PlanStage, PlanType
from app.models.task import TaskType
from app.models.user import User
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.card_edge_service import CardEdgeService
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine, TimeWindow
from app.services.card_service import CardService
from app.services.plan_service import PlanService
from app.services.task_service import TaskService


@dataclass
class SnapshotImportResult:
    root_card: Card
    created_cards: list[Card]
    imported_root_plan_id: UUID | None = None
    imported_root_task_id: UUID | None = None


def _utcnow() -> datetime:
    return datetime.utcnow()


def _parse_uuid(value: Any) -> UUID | None:
    if value in (None, "", "null"):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _coerce_plan_type(value: Any) -> PlanType:
    raw = str(value or "").strip().lower()
    return PlanType.SPRINT if raw == "sprint" else PlanType.GROWTH


def _coerce_plan_stage(value: Any) -> PlanStage:
    raw = str(value or "").strip().lower()
    for stage in PlanStage:
        if stage.value == raw:
            return stage
    return PlanStage.DAILY


def _coerce_plan_priority(value: Any) -> PlanPriority:
    raw = str(value or "").strip().lower()
    for priority in PlanPriority:
        if priority.value == raw:
            return priority
    return PlanPriority.NORMAL


def _coerce_task_priority(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class CardSnapshotService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)

    async def create_snapshot(
        self,
        *,
        card_id: UUID,
        include_children: bool = True,
        max_depth: int = 3,
    ) -> CardSnapshot:
        root = await self.card_service.get_card(card_id)
        if not root:
            raise ValueError("Card not found")

        owner = await self.db.get(User, root.owner_id)
        nodes, containment_edges = await self._collect_tree(
            root=root,
            include_children=include_children,
            max_depth=max_depth,
        )
        node_ids = list(nodes.keys())
        all_edges = await self._collect_internal_edges(node_ids)

        refs_by_id: dict[UUID, str] = {}
        cards_payload: list[dict[str, Any]] = []
        for index, card in enumerate(nodes.values()):
            ref = f"$ref:{index}"
            refs_by_id[card.id] = ref
            cards_payload.append(
                {
                    "ref": ref,
                    "source_card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "lifecycle_status": card.lifecycle_status.value,
                    "visibility": card.visibility.value,
                    "source_type": card.source_type.value,
                    "tags": list(card.tags or []),
                    "metadata": dict(card.metadata_ or {}),
                }
            )

        edges_payload: list[dict[str, Any]] = []
        for edge in all_edges:
            if edge.from_card_id not in refs_by_id or edge.to_card_id not in refs_by_id:
                continue
            edges_payload.append(
                {
                    "from": refs_by_id[edge.from_card_id],
                    "to": refs_by_id[edge.to_card_id],
                    "type": edge.edge_type.value,
                    "binding_mode": edge.binding_mode.value,
                    "order_index": edge.order_index,
                    "weight": edge.weight,
                    "metadata": dict(edge.metadata_ or {}),
                }
            )

        payload = {
            "schema_version": "1.0",
            "snapshot_at": _utcnow().isoformat(),
            "source": {
                "owner_display_name": (
                    owner.nickname or owner.full_name or owner.username if owner else None
                ),
                "owner_id_hash": _sha256_text(str(root.owner_id)),
                "card_id_hash": _sha256_text(str(root.id)),
                "root_card_type": root.card_type.value,
            },
            "root_ref": refs_by_id[root.id],
            "cards": cards_payload,
            "edges": edges_payload,
            "tree": {
                "containment_edges": [
                    {
                        "from": refs_by_id[from_id],
                        "to": refs_by_id[to_id],
                        "order_index": order_index,
                    }
                    for from_id, to_id, order_index in containment_edges
                    if from_id in refs_by_id and to_id in refs_by_id
                ]
            },
        }

        snapshot = CardSnapshot(
            root_card_id=root.id,
            source_owner_id=root.owner_id,
            source_card_type=root.card_type,
            schema_version="1.0",
            payload=payload,
            metadata_={
                "include_children": include_children,
                "max_depth": max_depth,
                "node_count": len(cards_payload),
                "edge_count": len(edges_payload),
            },
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def import_snapshot(
        self,
        *,
        snapshot: CardSnapshot | dict[str, Any],
        user_id: UUID,
        import_mode: ImportMode,
        modifications: dict[str, Any] | None = None,
    ) -> SnapshotImportResult:
        snapshot_record = snapshot if isinstance(snapshot, CardSnapshot) else None
        payload = snapshot.payload if isinstance(snapshot, CardSnapshot) else snapshot
        cards = list(payload.get("cards") or [])
        if not cards:
            raise ValueError("Snapshot payload contains no cards")

        root_ref = str(payload.get("root_ref") or cards[0].get("ref"))
        cards_by_ref = {str(item["ref"]): item for item in cards if item.get("ref")}
        root_node = cards_by_ref.get(root_ref)
        if not root_node:
            raise ValueError("Snapshot root card is missing")

        if root_node.get("card_type") == CardType.PLAN.value:
            return await self._import_plan_snapshot(
                snapshot_record=snapshot_record,
                payload=payload,
                user_id=user_id,
                import_mode=import_mode,
                modifications=modifications or {},
            )
        if root_node.get("card_type") == CardType.TASK.value:
            return await self._import_task_snapshot(
                snapshot_record=snapshot_record,
                payload=payload,
                user_id=user_id,
                import_mode=import_mode,
                modifications=modifications or {},
            )
        return await self._import_generic_snapshot(
            snapshot_record=snapshot_record,
            payload=payload,
            user_id=user_id,
            import_mode=import_mode,
            modifications=modifications or {},
        )

    async def _collect_tree(
        self,
        *,
        root: Card,
        include_children: bool,
        max_depth: int,
    ) -> tuple[dict[UUID, Card], list[tuple[UUID, UUID, int | None]]]:
        seen: dict[UUID, Card] = {root.id: root}
        containment_edges: list[tuple[UUID, UUID, int | None]] = []

        async def walk(card: Card, depth: int) -> None:
            if not include_children or depth >= max_depth:
                return
            children = await self.edge_service.get_children(
                card.id,
                edge_type=EdgeType.CONTAINS,
                active_only=True,
            )
            for edge, child in children:
                seen[child.id] = child
                containment_edges.append((card.id, child.id, edge.order_index))
                await walk(child, depth + 1)

        await walk(root, 0)

        # Pull in directly referenced in-graph cards so plan snapshots keep
        # attached knowledge/support cards needed for adoption.
        referenced_edges = await self._collect_outgoing_noncontainment_edges(list(seen.keys()))
        for edge in referenced_edges:
            if edge.to_card_id in seen:
                continue
            referenced = await self.card_service.get_card(edge.to_card_id)
            if referenced and referenced.owner_id == root.owner_id:
                seen[referenced.id] = referenced

        return seen, containment_edges

    async def _collect_outgoing_noncontainment_edges(self, node_ids: list[UUID]) -> list[CardEdge]:
        if not node_ids:
            return []
        stmt = select(CardEdge).where(
            CardEdge.from_card_id.in_(node_ids),
            CardEdge.edge_type != EdgeType.CONTAINS,
            CardEdge.active.is_(True),
            CardEdge.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _collect_internal_edges(self, node_ids: list[UUID]) -> list[CardEdge]:
        if not node_ids:
            return []
        stmt = select(CardEdge).where(
            CardEdge.from_card_id.in_(node_ids),
            CardEdge.to_card_id.in_(node_ids),
            CardEdge.active.is_(True),
            CardEdge.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _import_generic_snapshot(
        self,
        *,
        snapshot_record: CardSnapshot | None,
        payload: dict[str, Any],
        user_id: UUID,
        import_mode: ImportMode,
        modifications: dict[str, Any],
    ) -> SnapshotImportResult:
        cards_by_ref = {str(item["ref"]): item for item in payload.get("cards") or [] if item.get("ref")}
        root_ref = str(payload.get("root_ref") or "")
        ordered_refs = [str(item["ref"]) for item in payload.get("cards") or [] if item.get("ref")]
        ref_to_card: dict[str, Card] = {}
        created_cards: list[Card] = []

        for ref in ordered_refs:
            node = cards_by_ref[ref]
            metadata = dict(node.get("metadata") or {})
            if ref == root_ref:
                metadata.update(modifications.get("metadata") or {})
                if modifications.get("name"):
                    metadata["name"] = modifications["name"]
                if modifications.get("title"):
                    metadata["title"] = modifications["title"]
            source_card_id = _parse_uuid(node.get("source_card_id"))
            card = await self.card_service.create_card(
                card_type=CardType(node["card_type"]),
                owner_id=user_id,
                holder_id=user_id,
                metadata=metadata,
                tags=list(modifications.get("tags") or node.get("tags") or []),
                source_type=(
                    CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED
                ),
                origin_card_id=source_card_id,
                origin_snapshot_id=snapshot_record.id if snapshot_record else None,
                created_by=CardCreatedBy.SYSTEM,
                visibility=CardVisibility.PRIVATE,
                lifecycle_status=CardLifecycleStatus(node.get("lifecycle_status") or CardLifecycleStatus.DRAFT.value),
            )
            ref_to_card[ref] = card
            created_cards.append(card)

        for edge_payload in payload.get("edges") or []:
            from_card = ref_to_card.get(str(edge_payload.get("from")))
            to_card = ref_to_card.get(str(edge_payload.get("to")))
            if not from_card or not to_card:
                continue
            await self.edge_service.create_edge(
                from_card_id=from_card.id,
                to_card_id=to_card.id,
                edge_type=EdgeType(edge_payload.get("type") or EdgeType.REFERENCES.value),
                binding_mode=BindingMode(edge_payload.get("binding_mode") or BindingMode.REFERENCE.value),
                order_index=edge_payload.get("order_index"),
                weight=edge_payload.get("weight"),
                metadata=dict(edge_payload.get("metadata") or {}),
            )

        root_card = ref_to_card[root_ref]
        source_root_id = _parse_uuid(cards_by_ref[root_ref].get("source_card_id"))
        if source_root_id:
            await self.edge_service.create_edge(
                from_card_id=root_card.id,
                to_card_id=source_root_id,
                edge_type=EdgeType.ADOPTED_FROM if import_mode == ImportMode.ADOPT else EdgeType.FORKED_FROM,
                binding_mode=BindingMode.SNAPSHOT,
                metadata={"source": "card_snapshot_import"},
            )
        await self.db.flush()
        return SnapshotImportResult(root_card=root_card, created_cards=created_cards)

    async def _import_task_snapshot(
        self,
        *,
        snapshot_record: CardSnapshot | None,
        payload: dict[str, Any],
        user_id: UUID,
        import_mode: ImportMode,
        modifications: dict[str, Any],
    ) -> SnapshotImportResult:
        cards_by_ref = {str(item["ref"]): item for item in payload.get("cards") or [] if item.get("ref")}
        root_ref = str(payload.get("root_ref") or "")
        root_node = cards_by_ref[root_ref]
        metadata = dict(root_node.get("metadata") or {})

        task = await TaskService.create(
            self.db,
            TaskCreate(
                title=str(modifications.get("title") or metadata.get("title") or "Imported Task"),
                type=coerce_task_type(metadata.get("task_kind"), default=TaskType.LEARNING) or TaskType.LEARNING,
                plan_id=None,
                tags=list(modifications.get("tags") or root_node.get("tags") or []),
                estimated_minutes=metadata.get("effort_minutes_default"),
                difficulty=metadata.get("difficulty"),
                energy_cost=metadata.get("energy_cost") or 1,
                guide_content=metadata.get("description"),
                priority=_coerce_task_priority(metadata.get("priority")),
                due_date=_parse_date(metadata.get("due_date")),
            ),
            user_id,
        )
        root_card = await self._find_task_card(task.id, user_id)
        if root_card is None:
            raise ValueError("Imported task card projection is missing")

        source_card_id = _parse_uuid(root_node.get("source_card_id"))
        merged_root_metadata = dict(root_card.metadata_ or {})
        merged_root_metadata.update(metadata)
        merged_root_metadata.update(modifications.get("metadata") or {})
        merged_root_metadata["legacy_task_id"] = str(task.id)
        root_card.metadata_ = merged_root_metadata
        root_card.tags = list(modifications.get("tags") or root_node.get("tags") or [])
        root_card.source_type = CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED
        root_card.origin_card_id = source_card_id
        root_card.origin_snapshot_id = snapshot_record.id if snapshot_record else None
        root_card.updated_by = CardCreatedBy.SYSTEM
        root_card.version += 1

        created_cards = [root_card]
        created_cards.extend(
            await self._import_auxiliary_cards(
                payload=payload,
                user_id=user_id,
                import_mode=import_mode,
                snapshot_record=snapshot_record,
                ref_to_card={root_ref: root_card},
                skip_refs={root_ref},
            )
        )
        ref_to_card = {root_ref: root_card}
        for card in created_cards[1:]:
            ref = next(
                (str(item["ref"]) for item in payload.get("cards") or [] if _parse_uuid(item.get("source_card_id")) == card.origin_card_id),
                None,
            )
            if ref:
                ref_to_card[ref] = card

        await self._recreate_noncontainment_edges(
            payload=payload,
            ref_to_card=ref_to_card,
            import_mode=import_mode,
        )
        await self._apply_task_temporal_from_metadata(root_card, user_id)
        return SnapshotImportResult(
            root_card=root_card,
            created_cards=created_cards,
            imported_root_task_id=task.id,
        )

    async def _import_plan_snapshot(
        self,
        *,
        snapshot_record: CardSnapshot | None,
        payload: dict[str, Any],
        user_id: UUID,
        import_mode: ImportMode,
        modifications: dict[str, Any],
    ) -> SnapshotImportResult:
        cards_by_ref = {str(item["ref"]): item for item in payload.get("cards") or [] if item.get("ref")}
        root_ref = str(payload.get("root_ref") or "")
        root_node = cards_by_ref[root_ref]
        root_metadata = dict(root_node.get("metadata") or {})

        new_plan = await PlanService.create(
            self.db,
            PlanCreate(
                name=str(modifications.get("name") or root_metadata.get("name") or "Imported Plan"),
                type=_coerce_plan_type(root_metadata.get("plan_kind")),
                description=modifications.get("description") or root_metadata.get("description"),
                subject=root_metadata.get("subject"),
                target_date=_parse_date(root_metadata.get("target_date")),
                daily_available_minutes=int(root_metadata.get("daily_available_minutes") or 60),
                total_estimated_hours=root_metadata.get("total_estimated_hours"),
                priority=_coerce_plan_priority(root_metadata.get("priority")),
                plan_stage=_coerce_plan_stage(root_metadata.get("legacy_plan_stage")),
            ),
            user_id,
            skip_quota_check=True,
        )
        root_card = await self._find_plan_card(new_plan.id, user_id)
        if root_card is None:
            raise ValueError("Imported plan card projection is missing")

        source_root_card_id = _parse_uuid(root_node.get("source_card_id"))
        plan_meta = dict(root_card.metadata_ or {})
        plan_meta.update(root_metadata)
        plan_meta.update(modifications.get("metadata") or {})
        plan_meta["legacy_plan_id"] = str(new_plan.id)
        root_card.metadata_ = plan_meta
        root_card.tags = list(modifications.get("tags") or root_node.get("tags") or [])
        root_card.source_type = CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED
        root_card.origin_card_id = source_root_card_id
        root_card.origin_snapshot_id = snapshot_record.id if snapshot_record else None
        root_card.updated_by = CardCreatedBy.SYSTEM
        root_card.version += 1
        new_plan.source = "community_shared"
        new_plan.source_metadata = {
            "import_mode": import_mode.value.lower(),
            "origin_card_id": str(source_root_card_id) if source_root_card_id else None,
            "origin_snapshot_id": str(snapshot_record.id) if snapshot_record else None,
        }
        self.db.add(new_plan)

        phase_service = PhaseService(self.db, self.event_bus)
        temporal_engine = TemporalEngine(self.db, self.event_bus)
        card_ops = CardOperationsService(self.db, self.event_bus)

        created_cards: list[Card] = [root_card]
        ref_to_card: dict[str, Card] = {root_ref: root_card}

        containment_order = self._build_child_order_map(payload)
        phase_refs = [
            child_ref
            for child_ref in containment_order.get(root_ref, [])
            if cards_by_ref.get(child_ref, {}).get("card_type") == CardType.PHASE.value
        ]

        current_phase_source_id = str(root_metadata.get("current_phase_card_id") or "")
        current_phase_ref: str | None = None
        if current_phase_source_id:
            current_phase_ref = next(
                (
                    ref
                    for ref, item in cards_by_ref.items()
                    if str(item.get("source_card_id") or "") == current_phase_source_id
                ),
                None,
            )

        for index, phase_ref in enumerate(phase_refs, start=1):
            node = cards_by_ref[phase_ref]
            metadata = dict(node.get("metadata") or {})
            phase_card = await phase_service.create_phase(
                plan_card_id=root_card.id,
                name=str(metadata.get("title") or metadata.get("name") or f"Phase {index}"),
                phase_index=int(metadata.get("phase_index") or index),
                user_id=user_id,
                estimated_start=_parse_date(metadata.get("estimated_start")),
                estimated_end=_parse_date(metadata.get("estimated_end")),
                entry_criteria=list(metadata.get("entry_criteria") or []),
                exit_criteria=list(metadata.get("exit_criteria") or []),
                feedback_gate_required=bool(metadata.get("feedback_gate_required", True)),
                phase_weight=float(metadata.get("phase_weight") or 1.0),
                objective=metadata.get("objective"),
            )
            phase_meta = dict(phase_card.metadata_ or {})
            phase_meta.update(metadata)
            phase_meta["legacy_plan_id"] = str(new_plan.id)
            phase_meta.pop("synthetic_phase", None)
            phase_meta.pop("synthetic_replaced_by", None)
            phase_card.metadata_ = phase_meta
            phase_card.source_type = CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED
            phase_card.origin_card_id = _parse_uuid(node.get("source_card_id"))
            phase_card.origin_snapshot_id = snapshot_record.id if snapshot_record else None
            phase_card.updated_by = CardCreatedBy.SYSTEM
            phase_card.version += 1
            ref_to_card[phase_ref] = phase_card
            created_cards.append(phase_card)

        # Import auxiliary cards first so task references can attach to them.
        auxiliary_cards = await self._import_auxiliary_cards(
            payload=payload,
            user_id=user_id,
            import_mode=import_mode,
            snapshot_record=snapshot_record,
            ref_to_card=ref_to_card,
            skip_refs={root_ref, *phase_refs},
        )
        created_cards.extend(auxiliary_cards)

        for phase_ref in phase_refs:
            phase_card = ref_to_card[phase_ref]
            task_refs = [
                child_ref
                for child_ref in containment_order.get(phase_ref, [])
                if cards_by_ref.get(child_ref, {}).get("card_type") == CardType.TASK.value
            ]
            for task_ref in task_refs:
                node = cards_by_ref[task_ref]
                metadata = dict(node.get("metadata") or {})
                task = await TaskService.create(
                    self.db,
                    TaskCreate(
                        title=str(metadata.get("title") or "Imported Task"),
                        type=coerce_task_type(metadata.get("task_kind"), default=TaskType.LEARNING)
                        or TaskType.LEARNING,
                        plan_id=new_plan.id,
                        tags=list(node.get("tags") or []),
                        estimated_minutes=metadata.get("effort_minutes_default"),
                        difficulty=metadata.get("difficulty"),
                        energy_cost=metadata.get("energy_cost") or 1,
                        guide_content=metadata.get("description"),
                        priority=_coerce_task_priority(metadata.get("priority")),
                        due_date=_parse_date(metadata.get("due_date")),
                    ),
                    user_id,
                )
                task_card = await self._find_task_card(task.id, user_id)
                if task_card is None:
                    raise ValueError("Imported task card projection is missing")
                await card_ops.move_card(
                    card_id=task_card.id,
                    new_parent_card_id=phase_card.id,
                    user_id=user_id,
                )
                task_meta = dict(task_card.metadata_ or {})
                task_meta.update(metadata)
                task_meta["legacy_task_id"] = str(task.id)
                task_meta["legacy_plan_id"] = str(new_plan.id)
                task_card.metadata_ = task_meta
                task_card.tags = list(node.get("tags") or [])
                task_card.source_type = (
                    CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED
                )
                task_card.origin_card_id = _parse_uuid(node.get("source_card_id"))
                task_card.origin_snapshot_id = snapshot_record.id if snapshot_record else None
                task_card.updated_by = CardCreatedBy.SYSTEM
                task_card.version += 1
                ref_to_card[task_ref] = task_card
                created_cards.append(task_card)
                await self._apply_task_temporal_from_metadata(task_card, user_id)

        await self._recreate_noncontainment_edges(
            payload=payload,
            ref_to_card=ref_to_card,
            import_mode=import_mode,
        )

        active_phase_ref = current_phase_ref or (phase_refs[0] if phase_refs else None)
        if active_phase_ref and active_phase_ref in ref_to_card:
            await phase_service.activate_phase(
                phase_card_id=ref_to_card[active_phase_ref].id,
                user_id=user_id,
            )
        elif phase_refs:
            await phase_service.activate_phase(
                phase_card_id=ref_to_card[phase_refs[0]].id,
                user_id=user_id,
            )

        if phase_refs:
            final_plan_meta = dict(root_card.metadata_ or {})
            final_active_phase_ref = active_phase_ref if active_phase_ref in ref_to_card else phase_refs[0]
            final_plan_meta["current_phase_card_id"] = str(ref_to_card[final_active_phase_ref].id)
            final_plan_meta["legacy_plan_id"] = str(new_plan.id)
            root_card.metadata_ = final_plan_meta
            root_card.updated_by = CardCreatedBy.SYSTEM
            root_card.version += 1

        if source_root_card_id:
            await self.edge_service.create_edge(
                from_card_id=root_card.id,
                to_card_id=source_root_card_id,
                edge_type=EdgeType.ADOPTED_FROM if import_mode == ImportMode.ADOPT else EdgeType.FORKED_FROM,
                binding_mode=BindingMode.SNAPSHOT,
                metadata={"source": "card_snapshot_import"},
            )

        if phase_refs:
            await temporal_engine.regenerate_phase_schedule(
                phase_card_id=ref_to_card[phase_refs[0]].id,
                from_date=_parse_date(root_metadata.get("target_date")),
            )

        return SnapshotImportResult(
            root_card=root_card,
            created_cards=created_cards,
            imported_root_plan_id=new_plan.id,
        )

    async def _import_auxiliary_cards(
        self,
        *,
        payload: dict[str, Any],
        user_id: UUID,
        import_mode: ImportMode,
        snapshot_record: CardSnapshot | None,
        ref_to_card: dict[str, Card],
        skip_refs: set[str],
    ) -> list[Card]:
        cards_by_ref = {str(item["ref"]): item for item in payload.get("cards") or [] if item.get("ref")}
        created_cards: list[Card] = []
        for ref, node in cards_by_ref.items():
            if ref in skip_refs or ref in ref_to_card:
                continue
            card_type = CardType(node["card_type"])
            if card_type in {CardType.PHASE, CardType.TASK, CardType.PLAN}:
                continue
            metadata = dict(node.get("metadata") or {})
            source_card_id = _parse_uuid(node.get("source_card_id"))

            if card_type == CardType.KNOWLEDGE and metadata.get("knowledge_node_id"):
                cloned = await self._clone_knowledge_node_card(
                    source_knowledge_node_id=_parse_uuid(metadata.get("knowledge_node_id")),
                    user_id=user_id,
                    metadata=metadata,
                    tags=list(node.get("tags") or []),
                    import_mode=import_mode,
                    snapshot_record=snapshot_record,
                    source_card_id=source_card_id,
                )
                ref_to_card[ref] = cloned
                created_cards.append(cloned)
                continue

            card = await self.card_service.create_card(
                card_type=card_type,
                owner_id=user_id,
                holder_id=user_id,
                metadata=metadata,
                tags=list(node.get("tags") or []),
                source_type=CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED,
                origin_card_id=source_card_id,
                origin_snapshot_id=snapshot_record.id if snapshot_record else None,
                created_by=CardCreatedBy.SYSTEM,
                visibility=CardVisibility.PRIVATE,
                lifecycle_status=CardLifecycleStatus(node.get("lifecycle_status") or CardLifecycleStatus.ACTIVE.value),
            )
            ref_to_card[ref] = card
            created_cards.append(card)
        return created_cards

    async def _clone_knowledge_node_card(
        self,
        *,
        source_knowledge_node_id: UUID | None,
        user_id: UUID,
        metadata: dict[str, Any],
        tags: list[str],
        import_mode: ImportMode,
        snapshot_record: CardSnapshot | None,
        source_card_id: UUID | None,
    ) -> Card:
        if source_knowledge_node_id is None:
            return await self.card_service.create_card(
                card_type=CardType.KNOWLEDGE,
                owner_id=user_id,
                holder_id=user_id,
                metadata=metadata,
                tags=tags,
                source_type=CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED,
                origin_card_id=source_card_id,
                origin_snapshot_id=snapshot_record.id if snapshot_record else None,
                created_by=CardCreatedBy.SYSTEM,
                visibility=CardVisibility.PRIVATE,
                lifecycle_status=CardLifecycleStatus.ACTIVE,
            )

        original = await self.db.get(KnowledgeNode, source_knowledge_node_id)
        if original is None:
            return await self.card_service.create_card(
                card_type=CardType.KNOWLEDGE,
                owner_id=user_id,
                holder_id=user_id,
                metadata=metadata,
                tags=tags,
                source_type=CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED,
                origin_card_id=source_card_id,
                origin_snapshot_id=snapshot_record.id if snapshot_record else None,
                created_by=CardCreatedBy.SYSTEM,
                visibility=CardVisibility.PRIVATE,
                lifecycle_status=CardLifecycleStatus.ACTIVE,
            )

        node = KnowledgeNode(
            subject_id=original.subject_id,
            parent_id=None,
            name=original.name,
            name_en=original.name_en,
            description=original.description,
            keywords=list(original.keywords or []),
            importance_level=original.importance_level,
            is_seed=False,
            source_type="community_adopted",
            source_task_id=None,
            source_file_id=None,
            chunk_refs=None,
            status=original.status or "published",
            sector_weights=dict(original.sector_weights or {}),
            dominant_sector_code=original.dominant_sector_code or "VOID",
            sector_classification_status=original.sector_classification_status or "pending",
            sector_classification_model="card_snapshot_import",
            sector_classified_at=_utcnow(),
            global_spark_count=0,
        )
        self.db.add(node)
        await self.db.flush()
        self.db.add(
            UserNodeStatus(
                user_id=user_id,
                node_id=node.id,
                mastery_score=0,
                bkt_mastery_prob=0.0,
                total_minutes=0,
                total_study_minutes=0,
                study_count=0,
                is_unlocked=True,
                is_collapsed=False,
                is_favorite=False,
            )
        )
        card_metadata = dict(metadata)
        card_metadata["knowledge_node_id"] = str(node.id)
        return await self.card_service.create_card(
            card_type=CardType.KNOWLEDGE,
            owner_id=user_id,
            holder_id=user_id,
            metadata=card_metadata,
            tags=tags,
            source_type=CardSourceType.ADOPTED if import_mode == ImportMode.ADOPT else CardSourceType.FORKED,
            origin_card_id=source_card_id,
            origin_snapshot_id=snapshot_record.id if snapshot_record else None,
            created_by=CardCreatedBy.SYSTEM,
            visibility=CardVisibility.PRIVATE,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
        )

    async def _recreate_noncontainment_edges(
        self,
        *,
        payload: dict[str, Any],
        ref_to_card: dict[str, Card],
        import_mode: ImportMode,
    ) -> None:
        for edge_payload in payload.get("edges") or []:
            edge_type = str(edge_payload.get("type") or "")
            if edge_type == EdgeType.CONTAINS.value:
                continue
            if edge_type in {EdgeType.ADOPTED_FROM.value, EdgeType.FORKED_FROM.value}:
                continue
            from_card = ref_to_card.get(str(edge_payload.get("from")))
            to_card = ref_to_card.get(str(edge_payload.get("to")))
            if not from_card or not to_card:
                continue
            await self.edge_service.create_edge(
                from_card_id=from_card.id,
                to_card_id=to_card.id,
                edge_type=EdgeType(edge_type),
                binding_mode=BindingMode(edge_payload.get("binding_mode") or BindingMode.REFERENCE.value),
                order_index=edge_payload.get("order_index"),
                weight=edge_payload.get("weight"),
                metadata=dict(edge_payload.get("metadata") or {}),
            )

    async def _apply_task_temporal_from_metadata(self, task_card: Card, user_id: UUID) -> None:
        metadata = dict(task_card.metadata_ or {})
        recurrence = metadata.get("temporal", {}).get("recurrence") or metadata.get("recurrence_rule")
        if not isinstance(recurrence, dict):
            return
        rule = RecurrenceRule(
            pattern=str(recurrence.get("pattern") or "once"),
            days_of_week=list(recurrence.get("days_of_week") or []) or None,
            day_of_month=recurrence.get("day_of_month"),
            time_window=(
                TimeWindow(
                    start=str((recurrence.get("time_window") or {}).get("start")),
                    end=str((recurrence.get("time_window") or {}).get("end")),
                )
                if isinstance(recurrence.get("time_window"), dict)
                else None
            ),
            flexible=bool(recurrence.get("flexible", True)),
            max_deferrals=int(recurrence.get("max_deferrals") or 3),
            end_condition=str(recurrence.get("end_condition") or "phase_end"),
            end_value=recurrence.get("end_value"),
            interval_days=recurrence.get("interval_days"),
        )
        await TemporalEngine(self.db, self.event_bus).set_task_recurrence(
            task_card_id=task_card.id,
            rule=rule,
            user_id=user_id,
        )

    def _build_child_order_map(self, payload: dict[str, Any]) -> dict[str, list[str]]:
        order_map: dict[str, list[tuple[int, str]]] = {}
        for edge in payload.get("tree", {}).get("containment_edges") or []:
            from_ref = str(edge.get("from"))
            to_ref = str(edge.get("to"))
            order_index = edge.get("order_index")
            normalized_order = int(order_index) if order_index is not None else 0
            order_map.setdefault(from_ref, []).append((normalized_order, to_ref))
        return {
            key: [child for _, child in sorted(values, key=lambda item: item[0])]
            for key, values in order_map.items()
        }

    async def _find_plan_card(self, legacy_plan_id: UUID, user_id: UUID) -> Card | None:
        stmt = select(Card).where(
            Card.owner_id == user_id,
            Card.card_type == CardType.PLAN,
            Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_task_card(self, legacy_task_id: UUID, user_id: UUID) -> Card | None:
        stmt = select(Card).where(
            Card.owner_id == user_id,
            Card.card_type == CardType.TASK,
            Card.metadata_["legacy_task_id"].as_string() == str(legacy_task_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class ShareService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.snapshot_service = CardSnapshotService(db, event_bus)

    async def share_card(
        self,
        *,
        card_id: UUID,
        user_id: UUID,
        scope: ShareScope,
        target_id: UUID | None = None,
        permission: SharePermission = SharePermission.ADOPT,
        message: str | None = None,
        include_children: bool = True,
        max_depth: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> CardShareRecord:
        card = await self.snapshot_service.card_service.get_card(card_id)
        if not card or card.owner_id != user_id:
            raise ValueError("Card not found")
        snapshot = await self.snapshot_service.create_snapshot(
            card_id=card_id,
            include_children=include_children,
            max_depth=max_depth,
        )
        share = CardShareRecord(
            snapshot_id=snapshot.id,
            root_card_id=card.id,
            shared_by_user_id=user_id,
            target_user_id=target_id if scope == ShareScope.USER else None,
            group_id=target_id if scope == ShareScope.GROUP else None,
            scope=scope,
            permission=permission,
            message=message,
            metadata_=metadata or {},
        )
        self.db.add(share)
        await self.db.flush()
        if self.event_bus:
            await self.event_bus.publish(
                "card.shared",
                {
                    "event_type": "card.shared",
                    "share_record_id": str(share.id),
                    "root_card_id": str(card.id),
                    "scope": share.scope.value,
                    "permission": share.permission.value,
                },
            )
        return share

    async def get_share_record(self, share_record_id: UUID) -> CardShareRecord | None:
        stmt = (
            select(CardShareRecord)
            .options(selectinload(CardShareRecord.snapshot))
            .where(
                CardShareRecord.id == share_record_id,
                CardShareRecord.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def adopt_shared_card(
        self,
        *,
        share_record_id: UUID,
        user_id: UUID,
        import_mode: ImportMode = ImportMode.ADOPT,
        modifications: dict[str, Any] | None = None,
    ) -> SnapshotImportResult:
        share = await self.get_share_record(share_record_id)
        if share is None:
            raise ValueError("Share record not found")
        await self._assert_share_access(share, user_id)
        if share.snapshot is None:
            raise ValueError("Share snapshot is missing")

        share.view_count = int(share.view_count or 0) + 1
        share.adoption_count = int(share.adoption_count or 0) + 1
        result = await self.snapshot_service.import_snapshot(
            snapshot=share.snapshot,
            user_id=user_id,
            import_mode=import_mode,
            modifications=modifications or {},
        )

        adoption = CardAdoptionRecord(
            share_record_id=share.id,
            adopter_user_id=user_id,
            adopted_root_card_id=result.root_card.id,
            import_mode=import_mode,
            attribution_payload={
                "share_record_id": str(share.id),
                "snapshot_id": str(share.snapshot_id),
                "shared_by_user_id": str(share.shared_by_user_id),
                "permission": share.permission.value,
            },
        )
        self.db.add(adoption)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "card.adopted",
                {
                    "event_type": "card.adopted",
                    "share_record_id": str(share.id),
                    "adopter_user_id": str(user_id),
                    "import_mode": import_mode.value,
                    "root_card_id": str(result.root_card.id),
                    "legacy_plan_id": str(result.imported_root_plan_id) if result.imported_root_plan_id else None,
                    "legacy_task_id": str(result.imported_root_task_id) if result.imported_root_task_id else None,
                },
            )
        return result

    async def resolve_card_from_legacy_resource(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        owner_id: UUID,
    ) -> Card | None:
        normalized = resource_type.lower()
        if normalized == "plan":
            stmt = select(Card).where(
                Card.owner_id == owner_id,
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(resource_id),
                Card.not_deleted_filter(),
            )
        elif normalized == "task":
            stmt = select(Card).where(
                Card.owner_id == owner_id,
                Card.card_type == CardType.TASK,
                Card.metadata_["legacy_task_id"].as_string() == str(resource_id),
                Card.not_deleted_filter(),
            )
        else:
            return None
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _assert_share_access(self, share: CardShareRecord, user_id: UUID) -> None:
        if share.target_user_id and str(share.target_user_id) != str(user_id):
            raise ValueError("No access to this share")
        if share.shared_by_user_id == user_id:
            return
        if share.scope == ShareScope.GROUP and share.group_id:
            from app.models.community import GroupMember

            result = await self.db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == share.group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter(),
                )
            )
            if result.scalar_one_or_none() is None:
                raise ValueError("No access to this group share")
