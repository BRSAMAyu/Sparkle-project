from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.models.plan import Plan
from app.models.subject import Subject
from app.models.task import Task
from app.models.task_document import TaskDocument
from app.models.task_resources import TaskKnowledgeLink, TaskResourceLink


class TaskDocumentService:
    """Task-document linking and suggestion helpers."""

    @staticmethod
    async def list_task_documents(
        db: AsyncSession,
        *,
        task_id: UUID,
        user_id: UUID,
    ) -> list[tuple[TaskDocument, StoredFile]]:
        result = await db.execute(
            select(TaskDocument, StoredFile)
            .join(StoredFile, StoredFile.id == TaskDocument.file_id)
            .join(Task, Task.id == TaskDocument.task_id)
            .where(TaskDocument.task_id == task_id)
            .where(Task.user_id == user_id)
            .where(TaskDocument.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
            .order_by(TaskDocument.created_at.asc(), StoredFile.file_name.asc())
        )
        return list(result.all())

    @staticmethod
    async def attach_document(
        db: AsyncSession,
        *,
        task: Task,
        file_id: UUID,
        linked_by: str = "user",
    ) -> TaskDocument:
        file_record = await TaskDocumentService._get_owned_file(db, user_id=task.user_id, file_id=file_id)
        existing = await db.scalar(
            select(TaskDocument)
            .where(TaskDocument.task_id == task.id)
            .where(TaskDocument.file_id == file_record.id)
        )

        if existing is not None:
            if existing.linked_by != "user" or linked_by == "user":
                existing.linked_by = linked_by
            existing.restore()
            await db.flush()
            return existing

        link = TaskDocument(
            task_id=task.id,
            file_id=file_record.id,
            linked_by=linked_by,
        )
        db.add(link)
        await db.flush()
        return link

    @staticmethod
    async def detach_document(
        db: AsyncSession,
        *,
        task_id: UUID,
        file_id: UUID,
        user_id: UUID,
    ) -> bool:
        link = await db.scalar(
            select(TaskDocument)
            .join(Task, Task.id == TaskDocument.task_id)
            .where(TaskDocument.task_id == task_id)
            .where(TaskDocument.file_id == file_id)
            .where(Task.user_id == user_id)
            .where(TaskDocument.deleted_at.is_(None))
        )
        if link is None:
            return False
        link.soft_delete()
        await db.flush()
        return True

    @staticmethod
    async def auto_link_from_task_context(
        db: AsyncSession,
        *,
        task: Task,
        linked_by: str = "ai",
    ) -> list[TaskDocument]:
        node_ids = await TaskDocumentService._resolve_task_node_ids(db, task=task)
        return await TaskDocumentService.auto_link_from_nodes(
            db,
            task=task,
            node_ids=node_ids,
            linked_by=linked_by,
        )

    @staticmethod
    async def auto_link_from_nodes(
        db: AsyncSession,
        *,
        task: Task,
        node_ids: Iterable[UUID],
        linked_by: str = "ai",
    ) -> list[TaskDocument]:
        unique_node_ids = list(dict.fromkeys(node_ids))
        if not unique_node_ids:
            return []

        file_rows = (
            await db.execute(
                select(KnowledgeNodeDocument.file_id)
                .where(KnowledgeNodeDocument.user_id == task.user_id)
                .where(KnowledgeNodeDocument.node_id.in_(unique_node_ids))
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
                .order_by(KnowledgeNodeDocument.is_primary.desc(), KnowledgeNodeDocument.created_at.asc())
            )
        ).all()

        links: list[TaskDocument] = []
        seen_file_ids: set[UUID] = set()
        for (file_id,) in file_rows:
            if file_id in seen_file_ids:
                continue
            seen_file_ids.add(file_id)
            links.append(
                await TaskDocumentService.attach_document(
                    db,
                    task=task,
                    file_id=file_id,
                    linked_by=linked_by,
                )
            )
        return links

    @staticmethod
    async def ensure_focus_documents(
        db: AsyncSession,
        *,
        task: Task,
    ) -> list[TaskDocument]:
        existing = (
            await db.execute(
                select(TaskDocument)
                .where(TaskDocument.task_id == task.id)
                .where(TaskDocument.deleted_at.is_(None))
                .order_by(TaskDocument.created_at.asc())
            )
        ).scalars().all()
        if existing:
            return existing
        return await TaskDocumentService.auto_link_from_task_context(db, task=task, linked_by="ai")

    @staticmethod
    async def resolve_focus_file_ids(
        db: AsyncSession,
        *,
        task: Task,
        include_legacy_resources: bool = True,
    ) -> list[UUID]:
        file_ids: list[UUID] = []

        doc_rows = (
            await db.execute(
                select(TaskDocument.file_id)
                .where(TaskDocument.task_id == task.id)
                .where(TaskDocument.deleted_at.is_(None))
                .order_by(TaskDocument.created_at.asc())
            )
        ).all()
        for (file_id,) in doc_rows:
            if file_id not in file_ids:
                file_ids.append(file_id)

        if include_legacy_resources:
            resource_rows = (
                await db.execute(
                    select(TaskResourceLink.resource_id)
                    .where(TaskResourceLink.task_id == task.id)
                    .where(TaskResourceLink.resource_type == "file")
                    .where(TaskResourceLink.resource_id.is_not(None))
                    .where(TaskResourceLink.deleted_at.is_(None))
                    .order_by(TaskResourceLink.order_index.asc(), TaskResourceLink.created_at.asc())
                )
            ).all()
            for (file_id,) in resource_rows:
                if file_id and file_id not in file_ids:
                    file_ids.append(file_id)

        return file_ids

    @staticmethod
    async def suggest_documents_for_task(
        db: AsyncSession,
        *,
        task: Task,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        already_linked = {
            file_id
            for (file_id,) in (
                await db.execute(
                    select(TaskDocument.file_id)
                    .where(TaskDocument.task_id == task.id)
                    .where(TaskDocument.deleted_at.is_(None))
                )
            ).all()
        }

        node_ids = await TaskDocumentService._resolve_task_node_ids(db, task=task)
        suggestions: list[dict[str, Any]] = []
        seen_file_ids: set[UUID] = set(already_linked)

        if node_ids:
            rows = (
                await db.execute(
                    select(KnowledgeNodeDocument, StoredFile, KnowledgeNode)
                    .join(StoredFile, StoredFile.id == KnowledgeNodeDocument.file_id)
                    .join(KnowledgeNode, KnowledgeNode.id == KnowledgeNodeDocument.node_id)
                    .where(KnowledgeNodeDocument.user_id == task.user_id)
                    .where(KnowledgeNodeDocument.node_id.in_(node_ids))
                    .where(KnowledgeNodeDocument.deleted_at.is_(None))
                    .where(StoredFile.deleted_at.is_(None))
                    .order_by(KnowledgeNodeDocument.is_primary.desc(), StoredFile.updated_at.desc())
                )
            ).all()
            for _link, file_record, node in rows:
                if file_record.id in seen_file_ids:
                    continue
                seen_file_ids.add(file_record.id)
                suggestions.append(
                    {
                        "file_id": file_record.id,
                        "file_name": file_record.file_name,
                        "reason": f"Attached to {node.name}",
                        "source": "knowledge_node",
                        "node_id": node.id,
                        "node_name": node.name,
                        "linked_by": "ai",
                        "status": file_record.status,
                    }
                )
                if len(suggestions) >= limit:
                    return suggestions

        subject_name = await TaskDocumentService._resolve_task_subject(db, task=task)
        if not subject_name:
            return suggestions

        subject_rows = (
            await db.execute(
                select(KnowledgeNodeDocument, StoredFile, KnowledgeNode, Subject)
                .join(StoredFile, StoredFile.id == KnowledgeNodeDocument.file_id)
                .join(KnowledgeNode, KnowledgeNode.id == KnowledgeNodeDocument.node_id)
                .outerjoin(Subject, Subject.id == KnowledgeNode.subject_id)
                .where(KnowledgeNodeDocument.user_id == task.user_id)
                .where(KnowledgeNodeDocument.deleted_at.is_(None))
                .where(StoredFile.deleted_at.is_(None))
                .where(
                    and_(
                        Subject.name.is_not(None),
                        func.lower(Subject.name) == subject_name.lower(),
                    )
                    | and_(
                        Subject.category.is_not(None),
                        func.lower(Subject.category) == subject_name.lower(),
                    )
                )
                .order_by(KnowledgeNodeDocument.is_primary.desc(), StoredFile.updated_at.desc())
            )
        ).all()
        for _link, file_record, node, _subject in subject_rows:
            if file_record.id in seen_file_ids:
                continue
            seen_file_ids.add(file_record.id)
            suggestions.append(
                {
                    "file_id": file_record.id,
                    "file_name": file_record.file_name,
                    "reason": f"Matches the {subject_name} study materials attached to {node.name}",
                    "source": "subject",
                    "node_id": node.id,
                    "node_name": node.name,
                    "linked_by": "ai",
                    "status": file_record.status,
                }
            )
            if len(suggestions) >= limit:
                break

        return suggestions

    @staticmethod
    async def _get_owned_file(db: AsyncSession, *, user_id: UUID, file_id: UUID) -> StoredFile:
        file_record = await db.scalar(
            select(StoredFile)
            .where(StoredFile.id == file_id)
            .where(StoredFile.user_id == user_id)
            .where(StoredFile.deleted_at.is_(None))
        )
        if file_record is None:
            raise LookupError("Document not found")
        return file_record

    @staticmethod
    async def _resolve_task_subject(db: AsyncSession, *, task: Task) -> str | None:
        guide_json = getattr(task, "guide_json", None)
        if isinstance(guide_json, dict):
            for key in ("subject", "course", "topic"):
                value = str(guide_json.get(key) or "").strip()
                if value:
                    return value

        if task.plan_id:
            subject = await db.scalar(select(Plan.subject).where(Plan.id == task.plan_id))
            value = str(subject or "").strip()
            if value:
                return value

        return None

    @staticmethod
    async def _resolve_task_node_ids(db: AsyncSession, *, task: Task) -> list[UUID]:
        node_ids: list[UUID] = []

        def add_node_id(value: object) -> None:
            if value is None:
                return
            try:
                node_id = value if isinstance(value, UUID) else UUID(str(value))
            except (TypeError, ValueError):
                return
            if node_id not in node_ids:
                node_ids.append(node_id)

        add_node_id(getattr(task, "knowledge_node_id", None))

        for (node_id,) in (
            await db.execute(
                select(TaskKnowledgeLink.knowledge_node_id)
                .where(TaskKnowledgeLink.task_id == task.id)
                .order_by(TaskKnowledgeLink.is_primary.desc(), TaskKnowledgeLink.order_index.asc())
            )
        ).all():
            add_node_id(node_id)

        for payload in (getattr(task, "guide_json", None), getattr(task, "tags", None)):
            for node_id in TaskDocumentService._extract_node_ids(payload):
                add_node_id(node_id)

        return node_ids

    @staticmethod
    def _extract_node_ids(payload: object) -> list[UUID]:
        values: list[object] = []
        if isinstance(payload, dict):
            for key in (
                "galaxy_node_ids",
                "knowledge_node_ids",
                "knowledge_nodes",
                "node_ids",
                "knowledge_node_id",
                "node_id",
            ):
                value = payload.get(key)
                if isinstance(value, list):
                    values.extend(value)
                elif value is not None:
                    values.append(value)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    values.extend(TaskDocumentService._extract_node_ids(item))
                else:
                    values.append(item)

        node_ids: list[UUID] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("id") or value.get("node_id") or value.get("knowledge_node_id")
            try:
                node_id = value if isinstance(value, UUID) else UUID(str(value))
            except (TypeError, ValueError):
                continue
            if node_id not in node_ids:
                node_ids.append(node_id)
        return node_ids


task_document_service = TaskDocumentService()
