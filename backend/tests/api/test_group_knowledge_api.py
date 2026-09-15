from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.file_storage import StoredFile
from app.models.group_files import GroupFile, GroupFileTrustLevel
from app.models.user import User


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


@pytest_asyncio.fixture
async def community_knowledge_app(db_session):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    yield app, state

    app.dependency_overrides = {}


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


@pytest.mark.asyncio
async def test_owner_can_promote_member_upload_into_official_knowledge_base(
    community_knowledge_app,
    db_session,
):
    app, state = community_knowledge_app
    owner = _make_user(username="owner")
    member = _make_user(username="member")
    await _commit_all(db_session, owner, member)

    group = Group(name="CET-6 Study Group", type=GroupType.SQUAD, max_members=20)
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER),
        ]
    )

    stored_file = StoredFile(
        user_id=member.id,
        file_name="cet6-official-outline.pdf",
        mime_type="application/pdf",
        file_size=2048,
        bucket="test",
        object_key=f"cet6-{uuid4()}",
        status="ready",
        visibility="group",
        retention_policy="keep",
    )
    db_session.add(stored_file)
    await db_session.flush()
    db_session.add(
        GroupFile(
            group_id=group.id,
            file_id=stored_file.id,
            shared_by_id=member.id,
            category="mock-exam",
            tags=["cet6", "writing"],
            trust_level=GroupFileTrustLevel.MEMBER,
            is_knowledge_base=False,
            view_role=GroupRole.MEMBER,
            download_role=GroupRole.MEMBER,
            manage_role=GroupRole.ADMIN,
        )
    )
    await db_session.commit()

    state["current_user"] = owner
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        promote_response = await client.post(
            f"/community/groups/{group.id}/knowledge-base/documents",
            json={
                "file_id": str(stored_file.id),
                "category": "official-materials",
                "tags": ["cet6", "official", "listening"],
            },
        )

        knowledge_base_response = await client.get(f"/community/groups/{group.id}/knowledge-base")
        galaxy_response = await client.get(f"/community/groups/{group.id}/galaxy")

    assert promote_response.status_code == 200
    promoted = promote_response.json()
    assert promoted["trust_level"] == "official"
    assert promoted["knowledge_base"] is True
    assert promoted["category"] == "official-materials"
    assert promoted["retrieval_boost"] >= 1.5

    assert knowledge_base_response.status_code == 200
    knowledge_base = knowledge_base_response.json()
    assert knowledge_base["stats"]["total_documents"] == 1
    assert knowledge_base["stats"]["official_count"] == 1
    assert knowledge_base["documents"][0]["trust_level"] == "official"
    assert knowledge_base["collaborative_galaxy_id"] is not None

    assert galaxy_response.status_code == 200
    galaxy = galaxy_response.json()
    assert galaxy["group_id"] == str(group.id)
    assert galaxy["galaxy_id"] == knowledge_base["collaborative_galaxy_id"]
    assert galaxy["stats"]["document_nodes"] == 1
    assert any(
        node["node_type"] == "document"
        and node["file_id"] == str(stored_file.id)
        and node["trust_level"] == "official"
        for node in galaxy["nodes"]
    )


@pytest.mark.asyncio
async def test_member_cannot_add_official_knowledge_base_document(
    community_knowledge_app,
    db_session,
):
    app, state = community_knowledge_app
    owner = _make_user(username="owner")
    member = _make_user(username="member")
    await _commit_all(db_session, owner, member)

    group = Group(name="CET-6 Study Group", type=GroupType.SQUAD, max_members=20)
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER),
        ]
    )
    stored_file = StoredFile(
        user_id=member.id,
        file_name="peer-notes.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"cet6-member-{uuid4()}",
        status="ready",
        visibility="private",
        retention_policy="keep",
    )
    db_session.add(stored_file)
    await db_session.commit()

    state["current_user"] = member
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/community/groups/{group.id}/knowledge-base/documents",
            json={"file_id": str(stored_file.id)},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "需要群管理员或群主权限"
