from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user_id, get_db
from app.api.v1.galaxy import router
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus

app = FastAPI()
app.include_router(router, prefix="/api/v1")


def _node(*, name: str, file_id=None, status: str = "published", embedding=None, chunk_refs=None) -> KnowledgeNode:
    return KnowledgeNode(
        id=uuid4(),
        name=name,
        description=f"{name} description",
        importance_level=2,
        source_type="document_import" if file_id else "seed",
        source_file_id=file_id,
        chunk_refs=chunk_refs,
        status=status,
        embedding=embedding,
        dominant_sector_code="VOID",
        sector_classification_status="completed",
    )


@pytest.mark.asyncio
async def test_document_review_api_approves_rejects_and_merges(db_session, test_user):
    file_id = uuid4()
    existing = _node(name="Process Scheduling", embedding=[1.0, 0.0, 0.0], chunk_refs=[100])
    approve_node = _node(name="Virtual Memory", file_id=file_id, status="draft", embedding=[0.0, 1.0, 0.0])
    reject_node = _node(name="Duplicate Appendix", file_id=file_id, status="draft", embedding=[0.0, 0.0, 1.0])
    merge_node = _node(
        name="CPU Scheduling",
        file_id=file_id,
        status="draft",
        embedding=[0.98, 0.02, 0.0],
        chunk_refs=[7, 8],
    )
    db_session.add_all([existing, approve_node, reject_node, merge_node])
    await db_session.flush()
    db_session.add_all(
        [
            UserNodeStatus(user_id=test_user.id, node_id=approve_node.id, is_unlocked=True),
            UserNodeStatus(user_id=test_user.id, node_id=reject_node.id, is_unlocked=True),
            UserNodeStatus(user_id=test_user.id, node_id=merge_node.id, is_unlocked=True),
            NodeRelation(source_node_id=merge_node.id, target_node_id=approve_node.id, relation_type="related", strength=0.7),
        ]
    )
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            suggestions_resp = await ac.get(f"/api/v1/galaxy/documents/{file_id}/suggested-nodes")
            assert suggestions_resp.status_code == 200
            suggestions = suggestions_resp.json()["suggested_nodes"]
            assert {item["node_id"] for item in suggestions} == {
                str(approve_node.id),
                str(reject_node.id),
                str(merge_node.id),
            }
            merge_suggestion = next(item for item in suggestions if item["node_id"] == str(merge_node.id))
            assert merge_suggestion["similarity_to_existing"][0]["node_id"] == str(existing.id)
            assert merge_suggestion["confidence_score"] < 0.1

            review_resp = await ac.post(
                f"/api/v1/galaxy/documents/{file_id}/review-nodes",
                json={
                    "decisions": [
                        {
                            "node_id": str(approve_node.id),
                            "action": "approve",
                            "edited_name": "Virtual Memory Management",
                        },
                        {"node_id": str(reject_node.id), "action": "reject"},
                        {
                            "node_id": str(merge_node.id),
                            "action": "merge",
                            "merge_into_node_id": str(existing.id),
                        },
                    ]
                },
            )
            assert review_resp.status_code == 200
            assert review_resp.json()["approved_count"] == 1
            assert review_resp.json()["rejected_count"] == 1
            assert review_resp.json()["merged_count"] == 1

            graph_resp = await ac.get("/api/v1/galaxy/graph")
            assert graph_resp.status_code == 200
            graph_names = {node["name"] for node in graph_resp.json()["nodes"]}
            assert "Virtual Memory Management" in graph_names
            assert "Duplicate Appendix" not in graph_names
            assert "CPU Scheduling" not in graph_names
            assert "Process Scheduling" in graph_names

    finally:
        app.dependency_overrides = {}

    await db_session.refresh(existing)
    assert existing.chunk_refs == [100, 7, 8]
    assert await db_session.get(KnowledgeNode, reject_node.id) is None
    assert await db_session.get(KnowledgeNode, merge_node.id) is None
