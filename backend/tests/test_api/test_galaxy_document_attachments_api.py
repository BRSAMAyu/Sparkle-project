from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user_id, get_db
from app.api.v1.galaxy import router
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_move_document_primary_node_updates_relationships_and_publishes_event(db_session, test_user):
    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="os-notes.pdf",
        mime_type="application/pdf",
        file_size=2048,
        bucket="test",
        object_key="os-notes.pdf",
        status="ready",
    )
    db_session.add(stored_file)
    await db_session.flush()

    from_node = KnowledgeNode(
        name="Operating Systems",
        source_type="document_import",
        source_file_id=stored_file.id,
        chunk_refs=[0, 1],
    )
    to_node = KnowledgeNode(name="Computer Architecture", source_type="user_created")
    db_session.add_all([from_node, to_node])
    await db_session.flush()
    db_session.add_all(
        [
            DocumentChunk(
                file_id=stored_file.id,
                user_id=test_user.id,
                chunk_index=0,
                content="process scheduling",
            ),
            DocumentChunk(
                file_id=stored_file.id,
                user_id=test_user.id,
                chunk_index=1,
                content="memory hierarchy",
            ),
        ]
    )
    await db_session.commit()

    async def override_user_id():
        return str(test_user.id)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_id] = override_user_id
    try:
        with patch("app.services.galaxy_service.event_bus.publish", new=AsyncMock()) as publish:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                move_response = await client.post(
                    f"/api/v1/galaxy/documents/{stored_file.id}/move",
                    json={
                        "from_node_id": str(from_node.id),
                        "to_node_id": str(to_node.id),
                    },
                )
                from_docs_response = await client.get(f"/api/v1/galaxy/nodes/{from_node.id}/documents")
                to_docs_response = await client.get(f"/api/v1/galaxy/nodes/{to_node.id}/documents")
                doc_nodes_response = await client.get(f"/api/v1/galaxy/documents/{stored_file.id}/nodes")
    finally:
        app.dependency_overrides = {}

    assert move_response.status_code == 200
    assert move_response.json()["to_node_id"] == str(to_node.id)
    assert from_docs_response.status_code == 200
    assert from_docs_response.json() == []
    assert to_docs_response.status_code == 200
    assert to_docs_response.json()[0]["file_id"] == str(stored_file.id)
    assert to_docs_response.json()[0]["is_primary"] is True
    assert to_docs_response.json()[0]["chunk_count"] == 2
    assert doc_nodes_response.status_code == 200
    assert doc_nodes_response.json()[0]["node_id"] == str(to_node.id)
    assert doc_nodes_response.json()[0]["chunk_refs"] == [0, 1]

    await db_session.refresh(from_node)
    await db_session.refresh(to_node)
    link = await db_session.scalar(
        select(KnowledgeNodeDocument).where(
            KnowledgeNodeDocument.user_id == test_user.id,
            KnowledgeNodeDocument.node_id == to_node.id,
            KnowledgeNodeDocument.file_id == stored_file.id,
        )
    )
    assert from_node.source_file_id is None
    assert from_node.chunk_refs is None
    assert to_node.source_file_id == stored_file.id
    assert to_node.chunk_refs == [0, 1]
    assert link is not None
    assert link.is_primary is True

    publish.assert_awaited_once()
    event_type, payload = publish.await_args.args
    assert event_type == "galaxy.document_attachment.changed"
    assert payload["action"] == "moved"
    assert payload["from_node_id"] == str(from_node.id)
    assert payload["to_node_id"] == str(to_node.id)


@pytest.mark.asyncio
async def test_attach_and_detach_document_from_node(db_session, test_user):
    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="algorithms.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key="algorithms.pdf",
        status="ready",
    )
    node = KnowledgeNode(name="Algorithms")
    db_session.add_all([stored_file, node])
    await db_session.commit()

    async def override_user_id():
        return str(test_user.id)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_id] = override_user_id
    try:
        with patch("app.services.galaxy_service.event_bus.publish", new=AsyncMock()) as publish:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                attach_response = await client.post(
                    f"/api/v1/galaxy/nodes/{node.id}/documents",
                    json={"file_id": str(stored_file.id), "is_primary": False},
                )
                list_response = await client.get(f"/api/v1/galaxy/documents/{stored_file.id}/nodes")
                detach_response = await client.delete(
                    f"/api/v1/galaxy/nodes/{node.id}/documents/{stored_file.id}",
                )
                after_detach_response = await client.get(f"/api/v1/galaxy/nodes/{node.id}/documents")
    finally:
        app.dependency_overrides = {}

    assert attach_response.status_code == 200
    assert attach_response.json()["is_primary"] is False
    assert list_response.status_code == 200
    assert list_response.json()[0]["node_id"] == str(node.id)
    assert detach_response.status_code == 200
    assert detach_response.json()["action"] == "detached"
    assert after_detach_response.status_code == 200
    assert after_detach_response.json() == []
    assert publish.await_count == 2
