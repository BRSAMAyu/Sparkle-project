from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.documents import _require_citation_chunk_belongs_to_file, _require_citation_feedback_access
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.document_chunks import DocumentChunk
from app.models.document_feedback import DocumentRetrievalFeedback
from app.models.file_storage import StoredFile
from app.models.group_files import GroupFile
from app.models.user import User
from app.orchestration.graph_rag import GraphRAGRetriever
from app.services.document_service import document_service


async def _create_file_with_chunk(db_session, *, owner_id: uuid.UUID, visibility: str = "private") -> tuple[StoredFile, DocumentChunk]:
    stored_file = StoredFile(
        user_id=owner_id,
        file_name="lecture-notes.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"{uuid.uuid4()}/lecture-notes.pdf",
        status="processed",
        visibility=visibility,
        retention_policy="standard",
    )
    db_session.add(stored_file)
    await db_session.flush()

    chunk = DocumentChunk(
        file_id=stored_file.id,
        user_id=owner_id,
        chunk_index=0,
        page_numbers=[4],
        section_title="Virtual Memory",
        content="Virtual memory maps pages to frames and isolates processes.",
    )
    db_session.add(chunk)
    await db_session.flush()
    return stored_file, chunk


@pytest.mark.asyncio
async def test_five_explicit_negative_feedbacks_demote_document_quality(db_session, test_user: User) -> None:
    stored_file, chunk = await _create_file_with_chunk(db_session, owner_id=test_user.id)

    for _ in range(5):
        await document_service.persist_feedback_event(
            db_session,
            {
                "user_id": str(test_user.id),
                "file_id": str(stored_file.id),
                "chunk_id": str(chunk.id),
                "query_type": "knowledge_query",
                "rating": -1,
                "feedback_source": "explicit",
                "conversation_id": "conv-negative",
                "context": {"reason": "not_relevant"},
            },
        )
    await db_session.commit()
    await db_session.refresh(stored_file)

    adjustment = await document_service.get_document_quality_adjustment(db_session, str(stored_file.id))

    assert stored_file.document_quality_score == pytest.approx(-5 / 7, rel=1e-6)
    assert adjustment == pytest.approx(-1 / 7, rel=1e-6)


@pytest.mark.asyncio
async def test_implicit_negative_feedback_is_persisted_from_next_turn(db_session, test_user: User) -> None:
    stored_file, chunk = await _create_file_with_chunk(db_session, owner_id=test_user.id)

    await document_service.register_turn_citations(
        user_id=str(test_user.id),
        conversation_id="conv-implicit-negative",
        query="explain virtual memory",
        query_type="knowledge_query",
        citations=[
            {
                "chunk_id": str(chunk.id),
                "file_id": str(stored_file.id),
                "title": "lecture-notes.pdf",
                "page_number": 4,
                "chunk_index": 0,
                "section_title": "Virtual Memory",
                "content_preview": "Virtual memory maps pages to frames.",
            }
        ],
    )

    emitted = await document_service.capture_implicit_feedback_from_message(
        user_id=str(test_user.id),
        conversation_id="conv-implicit-negative",
        user_message="That is not relevant. Can you explain it differently?",
        db=db_session,
    )
    await db_session.commit()

    records = (
        await db_session.execute(
            select(DocumentRetrievalFeedback).where(
                DocumentRetrievalFeedback.file_id == stored_file.id,
                DocumentRetrievalFeedback.feedback_source == "implicit_negative",
            )
        )
    ).scalars().all()

    assert len(emitted) == 1
    assert len(records) == 1
    assert records[0].feedback_score == -1
    assert records[0].context["reason"] == "user_requested_different_explanation"


@pytest.mark.asyncio
async def test_implicit_positive_feedback_is_persisted_from_follow_up(db_session, test_user: User) -> None:
    stored_file, chunk = await _create_file_with_chunk(db_session, owner_id=test_user.id)

    await document_service.register_turn_citations(
        user_id=str(test_user.id),
        conversation_id="conv-implicit-positive",
        query="explain virtual memory",
        query_type="knowledge_query",
        citations=[
            {
                "chunk_id": str(chunk.id),
                "file_id": str(stored_file.id),
                "title": "lecture-notes.pdf",
                "page_number": 4,
                "chunk_index": 0,
                "section_title": "Virtual Memory",
                "content_preview": "Virtual memory maps pages to frames and isolates processes.",
            }
        ],
    )

    emitted = await document_service.capture_implicit_feedback_from_message(
        user_id=str(test_user.id),
        conversation_id="conv-implicit-positive",
        user_message="Can you go deeper on the virtual memory mapping part?",
        db=db_session,
    )
    await db_session.commit()

    records = (
        await db_session.execute(
            select(DocumentRetrievalFeedback).where(
                DocumentRetrievalFeedback.file_id == stored_file.id,
                DocumentRetrievalFeedback.feedback_source == "implicit_positive",
            )
        )
    ).scalars().all()

    assert len(emitted) == 1
    assert len(records) == 1
    assert records[0].feedback_score == 1
    assert records[0].context["reason"] == "user_asked_follow_up_about_cited_content"


@pytest.mark.asyncio
async def test_group_citation_feedback_requires_group_view_permission(db_session, test_user: User) -> None:
    viewer = User(
        username=f"viewer-{uuid.uuid4()}",
        email=f"viewer-{uuid.uuid4()}@example.com",
        hashed_password="hashed",
    )
    db_session.add(viewer)
    await db_session.flush()

    group = Group(
        name="OS Study Squad",
        type=GroupType.SQUAD,
        focus_tags=["os"],
    )
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=test_user.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=viewer.id, role=GroupRole.MEMBER),
        ]
    )

    stored_file, _ = await _create_file_with_chunk(db_session, owner_id=test_user.id, visibility="group")
    group_file = GroupFile(
        group_id=group.id,
        file_id=stored_file.id,
        shared_by_id=test_user.id,
        view_role=GroupRole.ADMIN,
        download_role=GroupRole.ADMIN,
        manage_role=GroupRole.ADMIN,
    )
    db_session.add(group_file)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await _require_citation_feedback_access(db_session, record=stored_file, user_id=viewer.id)
    assert exc.value.status_code == 403

    group_file.view_role = GroupRole.MEMBER
    db_session.add(group_file)
    await db_session.flush()

    await _require_citation_feedback_access(db_session, record=stored_file, user_id=viewer.id)


@pytest.mark.asyncio
async def test_citation_feedback_chunk_must_belong_to_file(db_session, test_user: User) -> None:
    first_file, _ = await _create_file_with_chunk(db_session, owner_id=test_user.id)
    _, other_chunk = await _create_file_with_chunk(db_session, owner_id=test_user.id)

    with pytest.raises(HTTPException) as exc:
        await _require_citation_chunk_belongs_to_file(
            db_session,
            file_id=first_file.id,
            chunk_id=str(other_chunk.id),
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as invalid_exc:
        await _require_citation_chunk_belongs_to_file(
            db_session,
            file_id=first_file.id,
            chunk_id="not-a-uuid",
        )
    assert invalid_exc.value.status_code == 400


@pytest.mark.asyncio
async def test_rerank_by_mastery_applies_document_quality_demotions(db_session, test_user: User) -> None:
    noisy_file, noisy_chunk = await _create_file_with_chunk(db_session, owner_id=test_user.id)
    neutral_file, _ = await _create_file_with_chunk(db_session, owner_id=test_user.id)

    for _ in range(5):
        await document_service.persist_feedback_event(
            db_session,
            {
                "user_id": str(test_user.id),
                "file_id": str(noisy_file.id),
                "chunk_id": str(noisy_chunk.id),
                "query_type": "knowledge_query",
                "rating": -1,
                "feedback_source": "explicit",
                "conversation_id": "conv-rerank",
                "context": {"reason": "noisy"},
            },
        )
    await db_session.commit()

    knowledge_service = AsyncMock()
    knowledge_service.db = db_session
    knowledge_service.galaxy_service = None
    retriever = GraphRAGRetriever(knowledge_service)

    reranked = await retriever.rerank_by_mastery(
        [
            {
                "id": "noisy",
                "chunk_id": str(noisy_chunk.id),
                "file_id": str(noisy_file.id),
                "name": "Noisy notes",
                "description": "irrelevant chunk",
                "similarity": 0.8,
            },
            {
                "id": "neutral",
                "file_id": str(neutral_file.id),
                "name": "Clean notes",
                "description": "relevant chunk",
                "similarity": 0.8,
            },
        ],
        user_id=str(test_user.id),
        db=db_session,
    )

    assert reranked[0]["id"] == "neutral"
    assert reranked[1]["id"] == "noisy"
    assert reranked[1]["document_quality_adjustment"] == pytest.approx(-1 / 7, rel=1e-6)
    assert reranked[1]["boosted_rank_score"] < reranked[0]["boosted_rank_score"]
