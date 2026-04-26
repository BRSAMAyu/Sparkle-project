from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.services.galaxy_service import GalaxyService


@pytest.mark.asyncio
async def test_get_node_source_documents_returns_uploaded_file_and_previews(db_session, test_user):
    cache_service._local_cache.clear()

    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="lecture-notes.pdf",
        mime_type="application/pdf",
        file_size=2048,
        bucket="test",
        object_key="uploads/lecture-notes.pdf",
        status="processed",
    )
    db_session.add(stored_file)
    await db_session.flush()

    chunks = [
        DocumentChunk(
            file_id=stored_file.id,
            user_id=test_user.id,
            chunk_index=index,
            content=f"Sentence one for chunk {index}. Sentence two for chunk {index}. Sentence three for chunk {index}.",
        )
        for index in range(4)
    ]
    node = KnowledgeNode(
        name="Vector Spaces",
        importance_level=3,
        source_type="document_import",
        source_file_id=stored_file.id,
        chunk_refs=[1, 2, 3],
    )
    db_session.add_all([*chunks, node])
    await db_session.commit()

    service = GalaxyService(db_session)

    documents = await service.get_node_source_documents(test_user.id, node.id)
    stats = await service.get_node_knowledge_stats(test_user.id, node.id)

    assert len(documents) == 1
    assert documents[0].file_id == stored_file.id
    assert documents[0].filename == "lecture-notes.pdf"
    assert documents[0].file_type == "application/pdf"
    assert documents[0].upload_date == stored_file.created_at
    assert documents[0].chunk_count == 3
    assert len(documents[0].preview_chunks) == 3
    assert documents[0].preview_chunks[0].startswith("Sentence one for chunk 1.")
    assert stats.total_documents == 1
    assert stats.total_chunks == 3
    assert stats.has_personal_uploads is True
    assert stats.last_material_added == stored_file.created_at


@pytest.mark.asyncio
async def test_get_node_document_chunks_paginates_attached_chunks(db_session, test_user):
    cache_service._local_cache.clear()

    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="networks.pdf",
        mime_type="application/pdf",
        file_size=4096,
        bucket="test",
        object_key="uploads/networks.pdf",
        status="processed",
    )
    db_session.add(stored_file)
    await db_session.flush()

    chunks = [
        DocumentChunk(
            file_id=stored_file.id,
            user_id=test_user.id,
            chunk_index=index,
            page_numbers=[index + 1],
            section_title=f"Section {index}",
            content=f"Chunk {index} content. More context.",
        )
        for index in range(5)
    ]
    node = KnowledgeNode(
        name="TCP Congestion Control",
        importance_level=3,
        source_type="document_import",
        source_file_id=stored_file.id,
        chunk_refs=[1, 3, 4],
    )
    db_session.add_all([*chunks, node])
    await db_session.commit()

    result = await GalaxyService(db_session).get_node_document_chunks(
        user_id=test_user.id,
        node_id=node.id,
        page=1,
        page_size=2,
    )

    assert result.total == 3
    assert result.total_pages == 2
    assert result.has_next is True
    assert [chunk.chunk_index for chunk in result.chunks] == [1, 3]
    assert result.chunks[0].filename == "networks.pdf"
    assert result.chunks[0].page_numbers == [2]


@pytest.mark.asyncio
async def test_get_node_source_documents_reads_attachment_table(db_session, test_user):
    cache_service._local_cache.clear()

    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="linear-algebra.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key="uploads/linear-algebra.pdf",
        status="processed",
    )
    node = KnowledgeNode(
        name="Eigenvalues",
        importance_level=3,
        source_type="document_import",
    )
    db_session.add_all([stored_file, node])
    await db_session.flush()

    db_session.add(
        KnowledgeNodeDocument(
            user_id=test_user.id,
            node_id=node.id,
            file_id=stored_file.id,
            is_primary=True,
        )
    )
    db_session.add_all(
        [
            DocumentChunk(
                file_id=stored_file.id,
                user_id=test_user.id,
                chunk_index=0,
                content="Eigenvalues measure stretch along invariant directions. They are roots of the characteristic polynomial.",
            ),
            DocumentChunk(
                file_id=stored_file.id,
                user_id=test_user.id,
                chunk_index=1,
                content="Diagonalization uses eigenvectors as a basis when enough independent eigenvectors exist.",
            ),
        ]
    )
    await db_session.commit()

    documents = await GalaxyService(db_session).get_node_source_documents(test_user.id, node.id)

    assert len(documents) == 1
    assert documents[0].file_id == stored_file.id
    assert documents[0].filename == "linear-algebra.pdf"
    assert documents[0].chunk_count == 2
