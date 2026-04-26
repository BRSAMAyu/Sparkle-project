from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user, get_current_user_id, get_db
from app.api.v1.community import router as community_router
from app.api.v1.galaxy import router as galaxy_router
from app.models.community import Friendship, FriendshipStatus, Group, GroupMember, GroupRole, GroupType, MessageType, PrivateMessage
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.group_files import GroupFile
from app.models.notification import Notification
from app.models.user import User
from app.services.group_file_service import GroupFileService
from app.services.notification_service import NotificationService


def _make_user(*, username: str) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
    )


async def _commit_all(db_session, *objects) -> None:
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


@pytest_asyncio.fixture
async def community_file_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")
    app.include_router(galaxy_router, prefix="/api/v1")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    def _override_get_current_user_id():
        return str(state["current_user"].id)

    async def _fake_enqueue_processing(db, *, stored_file, effective_user_id):
        del db
        node = KnowledgeNode(
            name=f"Draft {stored_file.file_name}",
            description="Auto suggested from copied document",
            source_type="document_import",
            source_file_id=stored_file.id,
            status="draft",
        )
        db_session.add(node)
        await db_session.flush()
        db_session.add(UserNodeStatus(user_id=effective_user_id, node_id=node.id))
        await db_session.flush()
        return f"job-{stored_file.id}"

    monkeypatch.setattr(GroupFileService, "_enqueue_processing", _fake_enqueue_processing)
    monkeypatch.setattr(
        "app.services.group_file_service.document_upload_storage.copy_object",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.api.v1.community.manager.broadcast",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.api.v1.community.manager.send_personal_message",
        AsyncMock(),
    )
    monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock())

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_user_id] = _override_get_current_user_id

    yield app, state

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_group_share_list_copy_flow_surfaces_library_state_and_galaxy_suggestions(
    community_file_app,
    db_session,
):
    app, state = community_file_app
    owner = _make_user(username="owner")
    member = _make_user(username="member")
    await _commit_all(db_session, owner, member)

    group = Group(name="Sparkle Docs", type=GroupType.SQUAD, max_members=10)
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER),
        ]
    )
    source_file = StoredFile(
        user_id=owner.id,
        file_name="networking-notes.pdf",
        mime_type="application/pdf",
        file_size=4096,
        bucket="test",
        object_key=f"owner-{uuid4()}",
        status="processed",
        visibility="group",
        retention_policy="standard",
    )
    db_session.add(source_file)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        state["current_user"] = owner
        share_response = await client.post(
            f"/community/groups/{group.id}/files",
            json={
                "file_id": str(source_file.id),
                "category": "notes",
                "description": "Week 1 networking review",
            },
        )
        assert share_response.status_code == 200
        assert share_response.json()["description"] == "Week 1 networking review"

        state["current_user"] = member
        before_list = await client.get(
            f"/community/groups/{group.id}/files",
            params={"category": "notes", "page": 1},
        )
        assert before_list.status_code == 200
        before_payload = before_list.json()
        assert len(before_payload) == 1
        assert before_payload[0]["download_count"] == 0
        assert before_payload[0]["is_in_my_library"] is False
        assert before_payload[0]["uploader_name"] == owner.nickname

        copy_response = await client.post(
            f"/community/groups/{group.id}/files/{source_file.id}/copy-to-library",
        )
        assert copy_response.status_code == 200
        copy_payload = copy_response.json()
        copied_file_id = copy_payload["file_id"]
        assert copy_payload["already_in_library"] is False
        assert copy_payload["job_id"] == f"job-{copied_file_id}"
        assert copy_payload["suggested_nodes_route"].endswith(f"/{copied_file_id}/suggested-nodes")

        after_list = await client.get(
            f"/community/groups/{group.id}/files",
            params={"sort_by": "downloads", "page": 1},
        )
        assert after_list.status_code == 200
        after_payload = after_list.json()
        assert after_payload[0]["download_count"] == 1
        assert after_payload[0]["is_in_my_library"] is True

        suggestions_response = await client.get(
            f"/api/v1/galaxy/documents/{copied_file_id}/suggested-nodes",
        )
        assert suggestions_response.status_code == 200
        suggestions_payload = suggestions_response.json()
        assert suggestions_payload["file_id"] == copied_file_id
        assert len(suggestions_payload["suggested_nodes"]) == 1
        assert suggestions_payload["suggested_nodes"][0]["name"] == "Draft networking-notes.pdf"

    copied_file = await db_session.get(StoredFile, copied_file_id)
    assert copied_file is not None
    assert copied_file.user_id == member.id
    assert copied_file.visibility == "private"
    assert copied_file.source_file_id == source_file.id

    notification = await db_session.scalar(
        select(Notification).where(
            Notification.user_id == owner.id,
            Notification.type == "document_copied",
        )
    )
    assert notification is not None

    group_file = await db_session.scalar(
        select(GroupFile).where(GroupFile.group_id == group.id, GroupFile.file_id == source_file.id)
    )
    assert group_file is not None
    assert group_file.download_count == 1


@pytest.mark.asyncio
async def test_direct_share_file_creates_private_copy_and_message(
    community_file_app,
    db_session,
):
    app, state = community_file_app
    owner = _make_user(username="owner")
    friend = _make_user(username="friend")
    await _commit_all(db_session, owner, friend)

    friendship = Friendship(
        user_id=min(owner.id, friend.id, key=str),
        friend_id=max(owner.id, friend.id, key=str),
        initiated_by=owner.id,
        status=FriendshipStatus.ACCEPTED,
    )
    shared_file = StoredFile(
        user_id=owner.id,
        file_name="friends-only.pdf",
        mime_type="application/pdf",
        file_size=2048,
        bucket="test",
        object_key=f"friends-{uuid4()}",
        status="processed",
        visibility="friends",
        retention_policy="standard",
    )
    db_session.add_all([friendship, shared_file])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        state["current_user"] = owner
        response = await client.post(
            f"/community/users/{friend.id}/share-file",
            json={"file_id": str(shared_file.id)},
        )

    assert response.status_code == 200
    payload = response.json()
    copied_file_id = payload["file_id"]
    assert payload["already_in_library"] is False
    assert payload["job_id"] == f"job-{copied_file_id}"

    copied_file = await db_session.get(StoredFile, copied_file_id)
    assert copied_file is not None
    assert copied_file.user_id == friend.id
    assert copied_file.visibility == "private"
    assert copied_file.source_file_id == shared_file.id

    message = await db_session.scalar(
        select(PrivateMessage).where(
            PrivateMessage.sender_id == owner.id,
            PrivateMessage.receiver_id == friend.id,
        )
    )
    assert message is not None
    assert message.message_type == MessageType.FILE_SHARE
    assert message.content_data["shared_copy_file_id"] == str(copied_file_id)
