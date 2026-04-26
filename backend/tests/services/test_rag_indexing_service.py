from uuid import uuid4

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.group_files import GroupFile
from app.services.rag_indexing_service import (
    DOCUMENT_CHUNK_PREFIX,
    GROUP_DOCUMENT_CHUNK_PREFIX,
    RAG_INDEX_PREFIXES,
    SOURCE_DOCUMENT_CHUNK,
    SOURCE_NODE_DESCRIPTION,
    build_document_chunk_document,
    build_group_document_chunk_document,
    build_knowledge_chunk_document,
    document_chunk_key,
    group_document_chunk_key,
)


def test_document_chunk_document_uses_requested_key_and_source_type():
    file_id = uuid4()
    user_id = uuid4()
    chunk_id = uuid4()
    file_record = StoredFile(
        id=file_id,
        user_id=user_id,
        file_name="OS_Textbook.pdf",
        mime_type="application/pdf",
        file_size=1234,
        bucket="files",
        object_key="uploads/os.pdf",
    )
    chunk = DocumentChunk(
        id=chunk_id,
        file_id=file_id,
        user_id=user_id,
        chunk_index=7,
        content="A process scheduler decides which ready process runs next.",
        embedding=[0.1, 0.2, 0.3],
        page_numbers=[42],
        section_title="CPU Scheduling",
        quality_score=0.9,
        pipeline_version="v1",
    )

    doc = build_document_chunk_document(chunk, file_record)

    assert doc["id"] == document_chunk_key(file_id, 7)
    assert doc["id"] == f"sparkle:doc_chunk:{file_id}:7"
    assert doc["source_type"] == SOURCE_DOCUMENT_CHUNK
    assert doc["parent_id"] == str(file_id)
    assert doc["parent_name"] == "OS_Textbook.pdf"
    assert doc["chunk_id"] == str(chunk_id)
    assert doc["vector"] == [0.1, 0.2, 0.3]
    assert "CPU Scheduling" in doc["keywords"]


def test_knowledge_node_document_marks_source_type():
    node_id = uuid4()
    node = KnowledgeNode(
        id=node_id,
        name="Schedulers",
        description="Process scheduling overview",
        keywords=["os", "process"],
        importance_level=4,
        subject_id=3,
    )

    doc = build_knowledge_chunk_document(node, "Round-robin scheduling uses time slices.", [0.4, 0.5], 2)

    assert doc["id"] == f"sparkle:chunk:{node_id}:2"
    assert doc["source_type"] == SOURCE_NODE_DESCRIPTION
    assert doc["parent_id"] == str(node_id)
    assert doc["keywords"] == "Schedulers os process"
    assert doc["vector"] == [0.4, 0.5]


def test_rag_index_prefixes_include_document_chunks():
    assert DOCUMENT_CHUNK_PREFIX in RAG_INDEX_PREFIXES
    assert GROUP_DOCUMENT_CHUNK_PREFIX in RAG_INDEX_PREFIXES


def test_group_document_chunk_document_uses_group_namespace_and_metadata():
    group_id = uuid4()
    file_id = uuid4()
    user_id = uuid4()
    group_file_id = uuid4()
    chunk_id = uuid4()
    file_record = StoredFile(
        id=file_id,
        user_id=user_id,
        file_name="CET6_Vocabulary.pdf",
        mime_type="application/pdf",
        file_size=4321,
        bucket="files",
        object_key="uploads/cet6.pdf",
    )
    group_file = GroupFile(
        id=group_file_id,
        group_id=group_id,
        file_id=file_id,
        shared_by_id=user_id,
    )
    chunk = DocumentChunk(
        id=chunk_id,
        file_id=file_id,
        user_id=user_id,
        chunk_index=2,
        content="abandon: to give up completely.",
        embedding=[0.2, 0.4, 0.6],
        page_numbers=[3],
        section_title="Word List A",
        quality_score=0.95,
        pipeline_version="v1",
    )

    doc = build_group_document_chunk_document(
        chunk,
        file_record,
        group_file,
        trust_level="verified",
    )

    assert doc["id"] == group_document_chunk_key(group_id, file_id, 2)
    assert doc["group_id"] == str(group_id)
    assert doc["shared_by_user_id"] == str(user_id)
    assert doc["trust_level"] == "verified"
    assert doc["document_scope"] == "group"
