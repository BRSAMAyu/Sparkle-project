from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.user import User
from app.services.source_lifecycle import source_lifecycle_service
from app.services.task_document_service import TaskDocumentService


async def _source(db_session, user_id):
    stored_file = StoredFile(
        user_id=user_id,
        file_name="lecture.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"{uuid4()}/lecture.pdf",
        status="processed",
        visibility="private",
        retention_policy="standard",
    )
    db_session.add(stored_file)
    await db_session.flush()
    chunk = DocumentChunk(
        file_id=stored_file.id,
        user_id=user_id,
        chunk_index=0,
        content="Lifecycle-managed source chunk.",
    )
    db_session.add(chunk)
    await db_session.flush()
    return stored_file, chunk


@pytest.mark.asyncio
async def test_archive_and_restore_toggle_source_retrieval_eligibility(db_session, test_user: User, monkeypatch) -> None:
    stored_file, _chunk = await _source(db_session, test_user.id)
    monkeypatch.setattr(source_lifecycle_service, "invalidate_source_retrieval", AsyncMock(return_value=2))
    monkeypatch.setattr(source_lifecycle_service, "reindex_source_retrieval", AsyncMock(return_value=1))

    archived = await source_lifecycle_service.archive(db_session, source=stored_file, reason="test_archive")
    await db_session.flush()

    assert archived.status == SourceLifecycleStatus.ARCHIVED
    assert stored_file.lifecycle_status == SourceLifecycleStatus.ARCHIVED.value
    assert stored_file.archived_at is not None
    assert stored_file.archive_review_due_at is not None
    assert not source_lifecycle_service.should_include_in_retrieval(stored_file)

    restored = await source_lifecycle_service.restore(db_session, source=stored_file, reason="test_restore")
    await db_session.flush()

    assert restored.status == SourceLifecycleStatus.ACTIVE
    assert stored_file.lifecycle_status == SourceLifecycleStatus.ACTIVE.value
    assert stored_file.archived_at is None
    assert stored_file.archive_review_due_at is None
    assert source_lifecycle_service.should_include_in_retrieval(stored_file)


@pytest.mark.asyncio
async def test_archived_sources_are_hidden_from_task_document_context(db_session, test_user: User, monkeypatch) -> None:
    stored_file, _chunk = await _source(db_session, test_user.id)
    task = Task(
        user_id=test_user.id,
        title="Read lecture",
        type=TaskType.LEARNING,
        estimated_minutes=20,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.flush()
    db_session.add(TaskDocument(task_id=task.id, file_id=stored_file.id, linked_by="user"))
    await db_session.flush()

    before = await TaskDocumentService.list_task_documents(db_session, task_id=task.id, user_id=test_user.id)
    assert len(before) == 1

    monkeypatch.setattr(source_lifecycle_service, "invalidate_source_retrieval", AsyncMock(return_value=0))
    await source_lifecycle_service.archive(db_session, source=stored_file)
    await db_session.flush()

    after = await TaskDocumentService.list_task_documents(db_session, task_id=task.id, user_id=test_user.id)
    assert after == []


@pytest.mark.asyncio
async def test_delete_erases_object_metadata_and_soft_deletes_chunks(db_session, test_user: User, monkeypatch) -> None:
    stored_file, chunk = await _source(db_session, test_user.id)
    monkeypatch.setattr(source_lifecycle_service, "invalidate_source_retrieval", AsyncMock(return_value=4))

    result = await source_lifecycle_service.delete(db_session, source=stored_file, erase_object=False)
    await db_session.flush()
    await db_session.refresh(chunk)

    assert result.invalidated_keys == 4
    assert stored_file.lifecycle_status == SourceLifecycleStatus.REVOKED.value
    assert stored_file.deleted_at is not None
    assert stored_file.erased_at is not None
    assert stored_file.erasure_receipt.startswith("source-erased:")
    assert chunk.deleted_at is not None
