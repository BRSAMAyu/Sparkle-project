from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

_gen_pkg = types.ModuleType("app.gen")
_sparkle_pkg = types.ModuleType("app.gen.sparkle")
_rag_pkg = types.ModuleType("app.gen.sparkle.rag")
_rag_v1_pkg = types.ModuleType("app.gen.sparkle.rag.v1")
_gen_pkg.__path__ = []
_sparkle_pkg.__path__ = []
_rag_pkg.__path__ = []
_rag_v1_pkg.evidence_pb2 = types.SimpleNamespace()
sys.modules.setdefault("app.gen", _gen_pkg)
sys.modules.setdefault("app.gen.sparkle", _sparkle_pkg)
sys.modules.setdefault("app.gen.sparkle.rag", _rag_pkg)
sys.modules.setdefault("app.gen.sparkle.rag.v1", _rag_v1_pkg)

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, KnowledgeNodeDocument
from app.models.task import Task, TaskType
from app.models.task_document import TaskDocument
from app.models.user import User


@pytest.fixture
def tasks_client(db_session):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_create_task_auto_links_documents_from_confirmed_node(tasks_client, db_session):
    client, state = tasks_client

    user = User(username="task_doc_user", email="task_doc_user@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    stored_file = StoredFile(
        user_id=user.id,
        file_name="OS.pdf",
        mime_type="application/pdf",
        file_size=4096,
        bucket="test",
        object_key="os.pdf",
        status="ready",
    )
    node = KnowledgeNode(name="Process Scheduling")
    db_session.add_all([stored_file, node])
    await db_session.flush()
    db_session.add(
        KnowledgeNodeDocument(
            user_id=user.id,
            node_id=node.id,
            file_id=stored_file.id,
            is_primary=True,
        )
    )
    await db_session.commit()
    await db_session.refresh(user)
    state["current_user"] = user

    with (
        patch("app.services.task_service._sync_task_card_projection", new=AsyncMock()),
        patch("app.services.intelligent_task_service.IntelligentTaskService.get_task_nudges", new=AsyncMock(return_value=[])),
    ):
        response = client.post(
            "/tasks",
            json={
                "title": "Study Chapter 3 of OS textbook",
                "type": "LEARNING",
                "estimated_minutes": 45,
                "difficulty": 3,
                "knowledge_node_id": str(node.id),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["linked_documents"][0]["file_name"] == "OS.pdf"
    assert payload["linked_documents"][0]["linked_by"] == "ai"

    task_id = payload["data"]["id"]
    link = await db_session.scalar(select(TaskDocument).where(TaskDocument.task_id == task_id))
    assert link is not None
    assert link.file_id == stored_file.id


@pytest.mark.asyncio
async def test_task_document_attach_and_detach_endpoints(tasks_client, db_session):
    client, state = tasks_client

    user = User(username="manual_doc_user", email="manual_doc_user@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        title="Read chapter summary",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=20,
        difficulty=1,
        energy_cost=1,
    )
    stored_file = StoredFile(
        user_id=user.id,
        file_name="chapter3-notes.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key="chapter3-notes.pdf",
        status="ready",
    )
    db_session.add_all([task, stored_file])
    await db_session.commit()
    await db_session.refresh(user)
    state["current_user"] = user

    attach_response = client.post(
        f"/tasks/{task.id}/documents",
        json={"file_id": str(stored_file.id), "linked_by": "user"},
    )
    list_response = client.get(f"/tasks/{task.id}/documents")
    detach_response = client.request(
        "DELETE",
        f"/tasks/{task.id}/documents",
        json={"file_id": str(stored_file.id)},
    )
    after_detach = client.get(f"/tasks/{task.id}/documents")

    assert attach_response.status_code == 200
    assert attach_response.json()["data"]["file_name"] == "chapter3-notes.pdf"
    assert attach_response.json()["data"]["linked_by"] == "user"
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1
    assert detach_response.status_code == 200
    assert detach_response.json()["success"] is True
    assert after_detach.status_code == 200
    assert after_detach.json()["data"] == []
