"""memory-governance-mvp: 情景记忆用户侧治理（读侧来源标注/分页 + 写侧纠正/删除/确认）。

覆盖：
- GET  /api/v1/memory/episodic      offset 分页 + tags + source_annotation（哪轮对话/哪个模块+写入时间）
- POST /api/v1/memory/episodic/{id}/correction  wrong/outdated/delete/confirm
- 纠正后列表与召回查询（MemoryService.list_recent_episodic，即 context_builder 召回入口）
  均排除 revoked/retracted 行
- 跨用户隔离与鉴权
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.api.v1.memory import router
from app.config import settings
from app.models.memory import MemoryCorrection
from app.models.user import User
from app.services.memory_service import MemoryService

app = FastAPI()
app.include_router(router, prefix="/api/v1")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def enable_memory_panel(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)


async def _make_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _install_overrides(db_session, user):
    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user


@pytest.mark.asyncio
async def test_episodic_list_pagination_tags_and_source_annotation(db_session, enable_memory_panel):
    user = await _make_user(db_session)
    service = MemoryService(db_session)
    for i in range(5):
        await service.create_episodic_memory(
            user_id=user.id,
            summary=f"对话记忆 {i}",
            source_type="chat",
            source_id=f"msg_{i}",
            occurred_at=_utcnow(),
            importance_score=0.5,
            tags=["数学", f"chapter_{i}"],
            evidence_refs=[{"type": "chat_turn", "id": f"turn_{i}"}, {"type": "event", "id": f"evt_{i}"}],
            confidence=0.6,
        )

    _install_overrides(db_session, user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        page1 = await ac.get("/api/v1/memory/episodic", params={"limit": 2, "offset": 0})
        assert page1.status_code == 200
        body1 = page1.json()
        assert body1["total"] == 5
        assert body1["offset"] == 0
        assert body1["limit"] == 2
        assert body1["has_more"] is True
        assert len(body1["items"]) == 2

        page2 = await ac.get("/api/v1/memory/episodic", params={"limit": 2, "offset": 2})
        assert page2.status_code == 200
        body2 = page2.json()
        assert len(body2["items"]) == 2
        assert body2["has_more"] is True

        page3 = await ac.get("/api/v1/memory/episodic", params={"limit": 2, "offset": 4})
        body3 = page3.json()
        assert len(body3["items"]) == 1
        assert body3["has_more"] is False

        seen_ids = {item["id"] for item in body1["items"] + body2["items"] + body3["items"]}
        assert len(seen_ids) == 5

        first = body1["items"][0]
        assert first["tags"] == ["数学", f"chapter_4"]
        assert first["confidence"] == pytest.approx(0.6)
        annotation = first["source_annotation"]
        assert annotation["turn_id"] == "turn_4"
        assert annotation["label"]
        assert annotation["written_at"] is not None

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_correction_delete_soft_revokes_and_recall_excludes(db_session, enable_memory_panel):
    user = await _make_user(db_session)
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="用户明天要考微积分",
        source_type="chat",
        source_id="msg_del",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["微积分"],
        evidence_refs=[{"type": "chat_turn", "id": "turn_del"}],
        confidence=0.5,
    )

    _install_overrides(db_session, user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/memory/episodic/{record.id}/correction",
            json={"action": "delete", "reason": "不想被记住"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "corrected"
        assert payload["action"] == "delete"
        assert payload["item"]["revoked_at"] is not None
        assert payload["item"]["correction_count"] == 1

        listed = await ac.get("/api/v1/memory/episodic")
        assert listed.status_code == 200
        assert listed.json()["items"] == []
        assert listed.json()["total"] == 0

    await db_session.refresh(record)
    assert record.revoked_at is not None

    corrections = (
        (
            await db_session.execute(
                select(MemoryCorrection).where(
                    MemoryCorrection.user_id == user.id,
                    MemoryCorrection.memory_id == record.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert [c.action for c in corrections] == ["delete"]

    # 召回路径（context_builder 召回入口即 list_recent_episodic）必须排除 revoked。
    recall_rows = await MemoryService(db_session).list_recent_episodic(user.id, limit=10)
    assert recall_rows == []

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_correction_wrong_outdated_and_confirm(db_session, enable_memory_panel):
    user = await _make_user(db_session)
    service = MemoryService(db_session)
    wrong_item = await service.create_episodic_memory(
        user_id=user.id,
        summary="记错的条目",
        source_type="chat",
        source_id="msg_w",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=None,
        evidence_refs=[{"type": "chat_turn", "id": "turn_w"}],
        confidence=0.5,
    )
    confirm_item = await service.create_episodic_memory(
        user_id=user.id,
        summary="正确的条目",
        source_type="analysis",
        source_id="an_c",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["英语"],
        evidence_refs=[{"type": "event", "id": "evt_c"}],
        confidence=0.4,
    )

    _install_overrides(db_session, user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/memory/episodic/{wrong_item.id}/correction",
            json={"action": "wrong", "reason": "记错了"},
        )
        assert resp.status_code == 200
        item = resp.json()["item"]
        assert item["correction_count"] == 1
        assert item["confidence"] == pytest.approx(0.5)  # reject 只撤回，不动 confidence
        # 记错 → 撤回：列表与召回都不再出现
        listed = await ac.get("/api/v1/memory/episodic")
        assert all(entry["id"] != str(wrong_item.id) for entry in listed.json()["items"])

        resp = await ac.post(
            f"/api/v1/memory/episodic/{confirm_item.id}/correction",
            json={"action": "confirm"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "confirmed"
        assert body["item"]["confidence"] == pytest.approx(0.45)
        # 确认不是纠错：correction_count 不增
        assert body["item"]["correction_count"] == 0

    actions = (
        (
            await db_session.execute(
                select(MemoryCorrection).where(
                    MemoryCorrection.user_id == user.id,
                    MemoryCorrection.memory_id == confirm_item.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert [c.action for c in actions] == ["confirm"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_correction_validates_action_and_owner(db_session, enable_memory_panel):
    owner = await _make_user(db_session)
    stranger = await _make_user(db_session)
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=owner.id,
        summary="只有主人能治理",
        source_type="chat",
        source_id="msg_x",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=None,
        evidence_refs=[{"type": "chat_turn", "id": "turn_x"}],
        confidence=0.5,
    )

    _install_overrides(db_session, stranger)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 跨用户治理 → 404（不泄露资源存在性）
        resp = await ac.post(
            f"/api/v1/memory/episodic/{record.id}/correction",
            json={"action": "delete"},
        )
        assert resp.status_code == 404

    _install_overrides(db_session, owner)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 非法 action → 422
        resp = await ac.post(
            f"/api/v1/memory/episodic/{record.id}/correction",
            json={"action": "nuke"},
        )
        assert resp.status_code == 422

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_correction_requires_auth(enable_memory_panel):
    # 不注入 get_current_user 覆盖：携带无效凭证（无 Authorization 头）必须被拒。
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/memory/episodic/{uuid4()}/correction",
            json={"action": "delete"},
        )
        assert resp.status_code in (401, 403)

        resp = await ac.get("/api/v1/memory/episodic")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_correction_respects_feature_flag(db_session, monkeypatch, enable_memory_panel):
    user = await _make_user(db_session)
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="flag 关闭时不可纠",
        source_type="chat",
        source_id="msg_f",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=None,
        evidence_refs=[{"type": "chat_turn", "id": "turn_f"}],
        confidence=0.5,
    )
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", False, raising=False)

    _install_overrides(db_session, user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/memory/episodic/{record.id}/correction",
            json={"action": "delete"},
        )
        assert resp.status_code == 403

    app.dependency_overrides = {}
