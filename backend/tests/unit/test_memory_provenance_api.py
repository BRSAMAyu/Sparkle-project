"""M-08 Memory Provenance/Scope user API — red/green acceptance suite.

验收锚点（任务卡 + MEMORY_AURORA_UI.md）：
1. 跨用户隔离：双用户数据集下，A 对 B 的任何路径（detail/source/scope/
   update/revoke、receipt 枚举、pack 枚举）一律 404，list 零泄露；
   服务层查询带 user_id 过滤（变异测试物理删除该过滤 → 本套必红）。
2. source 不存在时诚实 unknown（source_known=False +「来源不明」，
   不猜测、不静默空串）。
3. 修改/删除触发 epoch/invalidation（M-07 既有链）：epoch bump +
   memory.invalidated 事件（content-free）+ derived 缓存 DEL；
   软删后检索面（list_recent_episodic）与 API 面默认不可见、不复活。
4. revoke 语义完整：检索 / API / 派生缓存 三面不可见。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.api.deps import get_current_user, get_db
from app.api.v1.memory_provenance import router
from app.config import settings
from app.models.context_pack import ContextPackRun
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.services.memory_invalidation_pipeline import (
    PROFILE_CONTEXT_KEY_TEMPLATE,
    MemoryInvalidationPipeline,
)
from app.services.memory_service import MemoryService

app = FastAPI()
app.include_router(router, prefix="/api/v1")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Hermetic fixtures（FakeRedis + outbox 表 + 外部副作用打桩）
# ---------------------------------------------------------------------------


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value
        return True

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key)
                deleted += 1
        return deleted


_OUTBOX_DDL = [
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id CHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        sequence_number INTEGER NOT NULL,
        payload JSON NOT NULL,
        metadata JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
]


@pytest.fixture(name="provenance_env")
async def provenance_env_fixture(db_session, monkeypatch):
    """Feature flags + outbox tables + hermetic redis + 外部副作用打桩."""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", True, raising=False)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())
    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService.record_user_correction",
        AsyncMock(),
    )
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()

    fake_redis = FakeRedis()
    monkeypatch.setattr(MemoryInvalidationPipeline, "_resolve_redis", lambda self: fake_redis)
    yield fake_redis


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


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _insert_episodic(
    db_session,
    user: User,
    summary: str,
    *,
    lane: str = "direct_capture",
    source_type: str = "chat",
    epistemic_class: str | None = None,
    evidence_refs: list | None = None,
) -> EpisodicMemory:
    record = EpisodicMemory(
        user_id=user.id,
        summary=summary,
        source_type=source_type,
        source_lane=lane,
        occurred_at=_utcnow(),
        evidence_refs=evidence_refs or [{"type": "event", "id": f"evt_{uuid4().hex[:8]}"}],
        epistemic_class=epistemic_class,
        confidence=0.7,
        evidence_score=0.5,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


async def _seed_two_user_dataset(db_session):
    """A/B 双用户数据集：A 覆盖四个 bucket + 各 kind；B 提供枚举靶."""
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)

    a_fact = await _insert_episodic(db_session, user_a, "用户确认自己每周三晚上有固定课程", lane="user_confirmed")
    a_observation = await _insert_episodic(
        db_session,
        user_a,
        "用户在错题本中反复练习链表章节",
        lane="direct_capture",
        source_type="error_book",
        epistemic_class="OBSERVATION",
    )
    a_hypothesis = await _insert_episodic(db_session, user_a, "用户可能偏好晚上学习", lane="inferred_extraction")
    a_experience = await _insert_episodic(
        db_session,
        user_a,
        "在考试焦虑场景下，拆分任务的小步干预曾经有效",
        lane="direct_capture",
        source_type="analysis",
        epistemic_class="EXPERIENCE",
    )
    a_unknown_source = await _insert_episodic(
        db_session,
        user_a,
        "来源缺失的旧记录",
        lane="",
        source_type="",
        epistemic_class=None,
    )

    pref_service = MemoryService(db_session)
    a_pref_explicit = await pref_service.upsert_preference(
        user_id=user_a.id,
        pref_key="depth_preference",
        pref_value={"value": 0.6},
        evidence_refs=[{"type": "user_state", "id": "settings"}],
        source_type="user_state",
    )
    a_pref_inferred = await pref_service.upsert_preference(
        user_id=user_a.id,
        pref_key="response_style",
        pref_value={"value": "concise"},
        evidence_refs=[{"type": "ai_inferred", "id": "inf_1"}],
        source_type="ai_inferred",
    )
    from app.models.memory import MemoryGoal

    a_goal = MemoryGoal(
        user_id=user_a.id,
        title="期末前完成数据结构复习",
        status="active",
        evidence_refs=[{"type": "event", "id": "goal_evt"}],
    )
    db_session.add(a_goal)
    await db_session.commit()
    await db_session.refresh(a_goal)

    b_episodic = await _insert_episodic(db_session, user_b, "B 用户的私有记忆内容")
    b_pref = await pref_service.upsert_preference(
        user_id=user_b.id,
        pref_key="depth_preference",
        pref_value={"value": 0.9},
        evidence_refs=[{"type": "user_state", "id": "b_settings"}],
        source_type="user_state",
    )
    b_run = ContextPackRun(
        user_id=user_b.id,
        intent="chat",
        budgets={},
        token_usage={},
        memory_counts={},
    )
    db_session.add(b_run)
    a_run = ContextPackRun(
        user_id=user_a.id,
        intent="chat",
        budgets={},
        token_usage={},
        memory_counts={},
    )
    db_session.add(a_run)
    await db_session.commit()
    await db_session.refresh(a_run)
    await db_session.refresh(b_run)

    return {
        "a": user_a,
        "b": user_b,
        "a_fact": a_fact,
        "a_observation": a_observation,
        "a_hypothesis": a_hypothesis,
        "a_experience": a_experience,
        "a_unknown": a_unknown_source,
        "a_pref_explicit": a_pref_explicit,
        "a_pref_inferred": a_pref_inferred,
        "a_goal": a_goal,
        "b_episodic": b_episodic,
        "b_pref": b_pref,
        "a_run": a_run,
        "b_run": b_run,
    }


async def _epoch_of(db_session, user: User) -> int:
    result = await db_session.execute(select(UserMemorySettings).where(UserMemorySettings.user_id == user.id))
    row = result.scalar_one_or_none()
    return int(row.memory_epoch) if row is not None else 1


async def _invalidation_events(db_session, user: User) -> list[dict]:
    result = await db_session.execute(
        text(
            "SELECT payload FROM event_outbox "
            "WHERE aggregate_type = 'user_memory' AND aggregate_id = :uid "
            "AND event_type = 'memory.invalidated' ORDER BY sequence_number"
        ),
        {"uid": str(user.id)},
    )
    return [json.loads(row[0]) for row in result.all()]


# ---------------------------------------------------------------------------
# 1. list / detail：bucket 分组 + 用户语言 metadata + 跨用户零泄露
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_groups_by_u03_buckets_with_user_language_metadata(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])

    async with _client() as ac:
        resp = await ac.get("/api/v1/memory/provenance/items")
    assert resp.status_code == 200
    body = resp.json()
    by_id = {item["id"]: item for item in body["items"]}

    # 四组语义（M-01 epistemic class → U-03 bucket）
    assert by_id[str(data["a_fact"].id)]["bucket"] == "told"
    assert by_id[str(data["a_observation"].id)]["bucket"] == "observed"
    assert by_id[str(data["a_hypothesis"].id)]["bucket"] == "uncertain"
    assert by_id[str(data["a_experience"].id)]["bucket"] == "effective"
    assert by_id[str(data["a_pref_inferred"].id)]["bucket"] == "uncertain"
    assert by_id[str(data["a_pref_explicit"].id)]["bucket"] == "told"
    assert by_id[str(data["a_goal"].id)]["bucket"] == "told"
    # 来源缺失的旧行保守落 HYPOTHESIS → uncertain（M-01 派生规则）
    assert by_id[str(data["a_unknown"].id)]["bucket"] == "uncertain"
    assert body["bucket_counts"] == {
        "told": 3,
        "observed": 1,
        "uncertain": 3,
        "effective": 1,
    }

    # 用户语言 metadata：来源标签 + 置信层级（tier，不是内部参数）
    fact_item = by_id[str(data["a_fact"].id)]
    assert fact_item["source_known"] is True
    assert fact_item["source_label"] == "你告诉我的"
    assert fact_item["confidence_tier_label"] == "已确认"
    hypothesis_item = by_id[str(data["a_hypothesis"].id)]
    assert hypothesis_item["source_label"] == "系统从你的对话与行为中推断"
    assert hypothesis_item["confidence_tier_label"] in {"较有把握", "初步推断"}
    experience_item = by_id[str(data["a_experience"].id)]
    assert experience_item["source_label"] == "从对你的帮助效果中总结"
    observation_item = by_id[str(data["a_observation"].id)]
    assert observation_item["source_label"] == "来自错题本"

    # 跨用户零泄露（list 面）
    serialized = json.dumps(body, ensure_ascii=False)
    assert str(data["b_episodic"].id) not in serialized
    assert "B 用户的私有记忆内容" not in serialized
    assert str(data["b_pref"].id) not in serialized


@pytest.mark.asyncio
async def test_bucket_filter_and_detail(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])

    async with _client() as ac:
        effective = await ac.get("/api/v1/memory/provenance/items", params={"bucket": "effective"})
        assert effective.status_code == 200
        assert len(effective.json()["items"]) == 1
        assert effective.json()["items"][0]["id"] == str(data["a_experience"].id)

        detail = await ac.get(f"/api/v1/memory/provenance/items/episodic/{data['a_fact'].id}")
        assert detail.status_code == 200
        assert detail.json()["ref"] == f"memory://episodic/{data['a_fact'].id}"
        assert detail.json()["actions"] == ["update", "revoke", "view_source", "pause"]

        bad_bucket = await ac.get("/api/v1/memory/provenance/items", params={"bucket": "nope"})
        assert bad_bucket.status_code == 422
        bad_kind = await ac.get("/api/v1/memory/provenance/items", params={"kind": "scene"})
        assert bad_kind.status_code == 422


# ---------------------------------------------------------------------------
# 2. 跨用户隔离：ID 枚举 / Receipt 枚举 / pack 枚举全 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_user_isolation_all_paths_404(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])
    b_episodic_id = data["b_episodic"].id
    b_pref_id = data["b_pref"].id

    async with _client() as ac:
        # detail / source / scope 读路径
        for kind, mid in (("episodic", b_episodic_id), ("preference", b_pref_id)):
            for suffix in ("", "/source", "/scope"):
                resp = await ac.get(f"/api/v1/memory/provenance/items/{kind}/{mid}{suffix}")
                assert resp.status_code == 404, (kind, suffix, resp.status_code)

        # update / revoke / scope 写路径
        resp = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{b_episodic_id}/update",
            json={"content": "越权改写"},
        )
        assert resp.status_code == 404
        resp = await ac.post(f"/api/v1/memory/provenance/items/episodic/{b_episodic_id}/revoke", json={})
        assert resp.status_code == 404
        resp = await ac.put(
            f"/api/v1/memory/provenance/items/episodic/{b_episodic_id}/scope",
            json={"action": "pause"},
        )
        assert resp.status_code == 404

        # receipt 枚举：B 的 memory_ref
        resp = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={"memory_ref": f"memory://episodic/{b_episodic_id}"},
        )
        assert resp.status_code == 404
        # pack 枚举：B 的 pack_id（即使 memory_ref 是 A 自己的）
        resp = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={
                "memory_ref": f"memory://episodic/{data['a_fact'].id}",
                "pack_id": str(data["b_run"].id),
            },
        )
        assert resp.status_code == 404
        # 非法 ref scheme / kind → 422（不静默）
        resp = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={"memory_ref": f"plan://{data['a_fact'].id}"},
        )
        assert resp.status_code == 422
        resp = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={"memory_ref": "memory://galaxy/not-a-uuid"},
        )
        assert resp.status_code == 422

    # B 的数据未被 A 的任何调用改动（写路径全被 404 挡下）
    await db_session.refresh(data["b_episodic"])
    assert data["b_episodic"].revoked_at is None
    assert data["b_episodic"].summary == "B 用户的私有记忆内容"


# ---------------------------------------------------------------------------
# 3. source 诚实 unknown（不猜测、不静默空）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_honest_unknown(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])

    async with _client() as ac:
        resp = await ac.get(f"/api/v1/memory/provenance/items/episodic/{data['a_unknown'].id}/source")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_known"] is False
    assert body["source_label"] == "来源不明"
    assert body["source_lane_hint"] is None
    # 何时/证据概况仍然如实返回
    assert body["written_at"] is not None
    assert body["evidence_count"] == 1

    # list 面同样不猜测
    async with _client() as ac:
        listed = await ac.get("/api/v1/memory/provenance/items", params={"kind": "episodic"})
    by_id = {item["id"]: item for item in listed.json()["items"]}
    assert by_id[str(data["a_unknown"].id)]["source_known"] is False
    assert by_id[str(data["a_unknown"].id)]["source_label"] == "来源不明"


# ---------------------------------------------------------------------------
# 4. 修改/删除触发 epoch + invalidation（M-07 链）+ 三面不可见
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_triggers_epoch_event_cache_del_and_three_face_invisible(db_session, provenance_env: FakeRedis):
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    target = data["a_hypothesis"]

    profile_key = PROFILE_CONTEXT_KEY_TEMPLATE.format(user_id=user.id)
    provenance_env.store[profile_key] = "stale-derived-profile"
    epoch_before = await _epoch_of(db_session, user)

    async with _client() as ac:
        resp = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{target.id}/revoke",
            json={"reason": "不对"},
        )
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True
    assert resp.json()["status"] == "revoked"

    # (a) epoch bump
    assert await _epoch_of(db_session, user) > epoch_before
    # (b) memory.invalidated 事件（content-free：无 summary 正文）
    events = await _invalidation_events(db_session, user)
    assert events, "memory.invalidated event must be written"
    matched = [e for e in events if str(target.id) in e.get("memory_ids", [])]
    assert matched, "event must carry the revoked memory id"
    assert "不对" not in json.dumps(events, ensure_ascii=False) or all(
        "summary" not in e for e in events
    ), "event payload must stay content-free"
    assert all("summary" not in e and "content" not in e for e in events)
    # (c) derived 缓存 DEL（M-07 链第三面）
    assert profile_key not in provenance_env.store

    # 三面不可见：
    # 1) 检索面（context_builder 召回入口）
    retrieval = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    assert all(str(row.id) != str(target.id) for row in retrieval)
    # 2) API 面（默认列表）
    async with _client() as ac:
        listed = await ac.get("/api/v1/memory/provenance/items", params={"kind": "episodic"})
    assert str(target.id) not in {item["id"] for item in listed.json()["items"]}
    # 3) 幂等重复 revoke 不再产生副作用（M-07 契约）
    epoch_after_revoke = await _epoch_of(db_session, user)
    async with _client() as ac:
        again = await ac.post(f"/api/v1/memory/provenance/items/episodic/{target.id}/revoke", json={})
    assert again.status_code == 200
    assert await _epoch_of(db_session, user) == epoch_after_revoke


@pytest.mark.asyncio
async def test_update_episodic_supersedes_with_invalidation(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    target = data["a_hypothesis"]
    epoch_before = await _epoch_of(db_session, user)

    async with _client() as ac:
        resp = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{target.id}/update",
            json={"content": "用户明确表示自己只在周末晚上学习", "reason": "说错了"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["superseded_id"] == str(target.id)
    assert body["status"] == "active"
    # 新记录是用户陈述（M-01 law：correction produces supersede，非覆写）
    assert body["bucket"] == "told"
    assert body["source_label"] == "你告诉我的"

    # 旧记录被取代 + 检索面不可见（M-03 召回路径：prefilter 状态机排除 superseded）
    await db_session.refresh(target)
    assert target.superseded_by_id is not None
    from app.services.memory_retrieval_prefilter import (
        PURPOSE_LLM_CONTEXT,
        apply_memory_prefilter,
        build_retrieval_context,
    )

    retrieval_ctx = await build_retrieval_context(db_session, user_id=user.id, purpose=PURPOSE_LLM_CONTEXT)
    recalled = apply_memory_prefilter(
        await MemoryService(db_session).list_recent_episodic(user.id, limit=50), retrieval_ctx
    )
    assert all(str(row.id) != str(target.id) for row in recalled)
    # 新记录以用户陈述身份进入召回
    assert any(str(row.id) == body["id"] for row in recalled)

    # epoch + 事件（SUPERSEDE）
    assert await _epoch_of(db_session, user) > epoch_before
    events = await _invalidation_events(db_session, user)
    matched = [e for e in events if str(target.id) in e.get("memory_ids", [])]
    assert matched and matched[-1]["action"] == "supersede"


@pytest.mark.asyncio
async def test_update_goal_and_preference_trigger_invalidation(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    epoch_before = await _epoch_of(db_session, user)

    async with _client() as ac:
        goal_resp = await ac.post(
            f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/update",
            json={"title": "期末前完成数据结构与算法复习（修订）"},
        )
        assert goal_resp.status_code == 200
        assert goal_resp.json()["title"].endswith("（修订）")

        events = await _invalidation_events(db_session, user)
        goal_events = [e for e in events if str(data["a_goal"].id) in e.get("memory_ids", [])]
        assert goal_events, "goal edit must write memory.invalidated"
        assert goal_events[-1]["action"] == "user_update"

        pref_resp = await ac.post(
            f"/api/v1/memory/provenance/items/preference/{data['a_pref_explicit'].id}/update",
            json={"pref_value": {"value": 0.8}},
        )
        assert pref_resp.status_code == 200
        assert pref_resp.json()["pref_key"] == "depth_preference"

    assert await _epoch_of(db_session, user) > epoch_before
    # 旧 preference 版本被链头取代（不覆写）
    await db_session.refresh(data["a_pref_explicit"])
    assert data["a_pref_explicit"].replaced_by_id is not None


@pytest.mark.asyncio
async def test_scope_pause_resume_hides_from_retrieval_and_api(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    target = data["a_observation"]
    epoch_before = await _epoch_of(db_session, user)

    async with _client() as ac:
        paused = await ac.put(
            f"/api/v1/memory/provenance/items/episodic/{target.id}/scope",
            json={"action": "pause", "reason": "暂时不用"},
        )
        assert paused.status_code == 200
        assert paused.json()["paused"] is True
        assert paused.json()["changed"] is True
        assert paused.json()["memory_epoch"] > epoch_before

    # 检索面：archived 不进召回
    retrieval = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    assert all(str(row.id) != str(target.id) for row in retrieval)
    # API 面默认隐藏，include_inactive 可见（诚实呈现 paused 状态）
    async with _client() as ac:
        listed = await ac.get("/api/v1/memory/provenance/items", params={"kind": "episodic"})
        assert str(target.id) not in {i["id"] for i in listed.json()["items"]}
        listed_all = await ac.get(
            "/api/v1/memory/provenance/items", params={"kind": "episodic", "include_inactive": "true"}
        )
        entry = next(i for i in listed_all.json()["items"] if i["id"] == str(target.id))
        assert entry["status"] == "archived"
        # P1-1 后的动作栏：paused 记录的 revoke 是真实操作（删除意图胜出暂停）
        assert entry["actions"] == ["view_source", "resume", "revoke"]

        # 幂等：重复 pause 不再 bump epoch
        epoch_now = await _epoch_of(db_session, user)
        again = await ac.put(
            f"/api/v1/memory/provenance/items/episodic/{target.id}/scope",
            json={"action": "pause"},
        )
        assert again.status_code == 200 and again.json()["changed"] is False
        assert await _epoch_of(db_session, user) == epoch_now

        resumed = await ac.put(
            f"/api/v1/memory/provenance/items/episodic/{target.id}/scope",
            json={"action": "resume"},
        )
        assert resumed.status_code == 200
        assert resumed.json()["paused"] is False

    retrieval = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    assert any(str(row.id) == str(target.id) for row in retrieval)


async def _make_plan(db_session, user):
    from app.models.plan import Plan, PlanType

    plan = Plan(user_id=user.id, name=f"计划 {uuid4().hex[:6]}", type=PlanType.SPRINT)
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


async def _make_task(db_session, user, plan=None):
    from app.models.task import Task, TaskType

    task = Task(
        user_id=user.id,
        title=f"任务 {uuid4().hex[:6]}",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        plan_id=plan.id if plan else None,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_goal_scope_linkage(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])
    a_plan = await _make_plan(db_session, data["a"])
    a_task = await _make_task(db_session, data["a"], plan=a_plan)

    async with _client() as ac:
        # 仅此 Goal：goal 域的 scope 绑定到 plan/task（既有列，不造新存储）
        linked = await ac.put(
            f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/scope",
            json={"action": "link_plan", "plan_id": str(a_plan.id)},
        )
        assert linked.status_code == 200
        assert linked.json()["scope"].get("plan_id") == str(a_plan.id)

        linked_task = await ac.put(
            f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/scope",
            json={"action": "link_task", "task_id": str(a_task.id)},
        )
        assert linked_task.status_code == 200
        assert linked_task.json()["scope"].get("task_id") == str(a_task.id)

        # episodic 不支持 link_plan → 422（诚实拒绝，不静默伪装成功）
        rejected = await ac.put(
            f"/api/v1/memory/provenance/items/episodic/{data['a_fact'].id}/scope",
            json={"action": "link_plan", "plan_id": str(a_plan.id)},
        )
        assert rejected.status_code == 422


@pytest.mark.asyncio
async def test_goal_scope_linkage_validates_target_ownership(db_session, provenance_env):
    """P2-3：link_plan/link_task 目标必须归属本人——跨用户与不存在的 id 一律 404，
    与全卡隔离法则同形（此前跨用户 200 落库、随机 UUID 在 PG 上 FK 500）。"""
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])
    b_plan = await _make_plan(db_session, data["b"])
    b_task = await _make_task(db_session, data["b"])
    missing_id = uuid4()

    async with _client() as ac:
        base = f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/scope"
        # 跨用户目标（真实存在但不属于 A）→ 404，且不落库
        cross_plan = await ac.put(base, json={"action": "link_plan", "plan_id": str(b_plan.id)})
        assert cross_plan.status_code == 404
        cross_task = await ac.put(base, json={"action": "link_task", "task_id": str(b_task.id)})
        assert cross_task.status_code == 404
        # 不存在的 UUID → 404（PG 上此前是未捕获 FK IntegrityError → 500）
        missing_plan = await ac.put(base, json={"action": "link_plan", "plan_id": str(missing_id)})
        assert missing_plan.status_code == 404
        missing_task = await ac.put(base, json={"action": "link_task", "task_id": str(missing_id)})
        assert missing_task.status_code == 404

    await db_session.refresh(data["a_goal"])
    assert data["a_goal"].linked_plan_id is None
    assert data["a_goal"].linked_task_id is None


# ---------------------------------------------------------------------------
# 5. Why-this by memory_use_receipt（M-05 回执结构消费）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_why_this_translates_receipt_with_honest_unknown(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])
    target = data["a_hypothesis"]

    async with _client() as ac:
        resp = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={
                "memory_ref": f"memory://episodic/{target.id}",
                "version": "memory_use_selfcheck.v1",
                "pack_id": str(data["a_run"].id),
                "why_included": ["rank_policy", "semantic_gate"],
                "internal_only": [
                    {"id": str(target.id), "section": "episodic", "reason": "selfcheck:irrelevant_to_query"},
                    {"id": str(target.id), "section": "episodic", "reason": "selfcheck:not_a_real_reason"},
                ],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["memory"]["id"] == str(target.id)
    assert body["memory"]["still_in_use"] is True
    assert body["run"]["pack_id"] == str(data["a_run"].id)
    assert body["run"]["intent"] == "chat"

    labels = {entry["reason"]: entry for entry in body["why_included"]}
    assert labels["rank_policy"]["known"] is True
    assert labels["rank_policy"]["label"] == "按与当轮内容的相关度排序选中"
    assert labels["semantic_gate"]["known"] is True

    internal = body["usage_decision"]["internal_only"]
    known_entry = next(e for e in internal if e["reason"] == "selfcheck:irrelevant_to_query")
    assert known_entry["reason_known"] is True
    assert known_entry["reason_label"] == "与当轮话题无关，未直接说出来"
    unknown_entry = next(e for e in internal if e["reason"] == "selfcheck:not_a_real_reason")
    # 诚实 unknown：词表外 reason 不猜测
    assert unknown_entry["reason_known"] is False
    assert unknown_entry["reason_label"] is None

    # 来源元数据（何时/何源/置信层级）随回执一并返回
    assert body["source"]["source_label"] == "系统从你的对话与行为中推断"
    assert body["source"]["confidence_tier"] in {"likely", "tentative"}
    # U-03 纠正回路端点指向真实 mutation 面
    assert body["correction"]["revoke"].endswith(f"/items/episodic/{target.id}/revoke")


@pytest.mark.asyncio
async def test_why_this_flags_stale_receipt_and_revoked_memory(db_session, provenance_env):
    data = await _seed_two_user_dataset(db_session)
    _install_overrides(db_session, data["a"])

    async with _client() as ac:
        stale = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={
                "memory_ref": f"memory://episodic/{data['a_fact'].id}",
                "version": "memory_use_selfcheck.v0",
            },
        )
        assert stale.status_code == 200
        assert stale.json()["usage_decision"]["receipt_version_known"] is False

        revoked = await ac.post(f"/api/v1/memory/provenance/items/episodic/{data['a_hypothesis'].id}/revoke", json={})
        assert revoked.status_code == 200
        after = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={"memory_ref": f"memory://episodic/{data['a_hypothesis'].id}"},
        )
        assert after.status_code == 200
        assert after.json()["memory"]["status_now"] == "revoked"
        assert after.json()["memory"]["still_in_use"] is False


# ---------------------------------------------------------------------------
# 6. R2 返修回归（P1-1 / P2-2 / P2-4 / P2-5 / P3）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["episodic", "preference", "goal"])
async def test_pause_then_revoke_deletes_for_real_all_kinds(db_session, provenance_env, kind):
    """P1-1：pause 后 revoke 必须真实生效——终态化 + resume 拒绝复活 + 召回不可见。

    修复前：M-07 幂等守卫把 ARCHIVED 当终态静默吞掉删除意图，API 谎报
    revoked=true，随后一次 resume 即把「已删除」记录完整送回召回。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    target = {"episodic": data["a_observation"], "preference": data["a_pref_explicit"], "goal": data["a_goal"]}[kind]
    base = f"/api/v1/memory/provenance/items/{kind}/{target.id}"

    async with _client() as ac:
        paused = await ac.put(f"{base}/scope", json={"action": "pause"})
        assert paused.status_code == 200 and paused.json()["paused"] is True
        epoch_paused = await _epoch_of(db_session, user)
        events_paused = len(await _invalidation_events(db_session, user))

        # 删除意图胜出暂停：revoke 真实终态化（非静默 no-op）
        revoked = await ac.post(f"{base}/revoke", json={"reason": "删除"})
        assert revoked.status_code == 200
        body = revoked.json()
        assert body["revoked"] is True
        assert body["status"] in {"revoked", "retracted"}

    # 全链真实触发：epoch bump + memory.invalidated 事件（修复前增量为 0）
    assert await _epoch_of(db_session, user) > epoch_paused
    events = await _invalidation_events(db_session, user)
    assert len(events) > events_paused
    assert any(str(target.id) in e.get("memory_ids", []) for e in events[events_paused:])

    # 终态真实落位（修复前 revoked_at/retracted_at 均为 None）
    await db_session.refresh(target)
    terminal = {"episodic": "revoked_at", "preference": "retracted_at", "goal": "retracted_at"}[kind]
    assert getattr(target, terminal) is not None
    assert target.archived_at is None

    async with _client() as ac:
        # resume 不得复活「已删除」的记录（修复前 resume 成功且记录回归召回）
        resumed = await ac.put(f"{base}/scope", json={"action": "resume"})
        assert resumed.status_code == 409

        listed = await ac.get("/api/v1/memory/provenance/items", params={"kind": kind})
        assert str(target.id) not in {i["id"] for i in listed.json()["items"]}

    if kind == "episodic":
        retrieval = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
        assert all(str(row.id) != str(target.id) for row in retrieval)


@pytest.mark.asyncio
async def test_auto_captured_goal_source_not_told_confirmed(db_session, provenance_env):
    """P2-2：系统捕获的 goal（计划审批 source_type="event"）不得标「你告诉我的/已确认」。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)

    # 以 plan_review_service._capture 同参复演（R2 PROBE2）
    auto_goal = await MemoryService(db_session).create_goal(
        user_id=user.id,
        title="考研英语冲刺计划",
        status="active",
        evidence_refs=[{"type": "event", "id": "action_1", "schema_version": "event.v1"}],
        metadata={"plan_type": "sprint", "subject": "english"},
        source_type="event",
    )
    assert auto_goal is not None and auto_goal.source_type == "event"
    # 对照组：用户公共创建路径（source_type=None → 创建动作本身即用户陈述）
    user_goal = await MemoryService(db_session).create_goal(user_id=user.id, title="我自己定的目标", status="active")
    assert user_goal is not None and user_goal.source_type is None

    from app.services.memory_provenance_service import MemoryProvenanceService

    service = MemoryProvenanceService(db_session)
    auto_payload = service._item_payload("goal", auto_goal)
    user_payload = service._item_payload("goal", user_goal)

    # 自动捕获：观察桶 + 系统写入标签 + 置信降档（推断/捕获永不报已确认）
    assert auto_payload["bucket"] == "observed"
    assert auto_payload["source_known"] is True
    assert auto_payload["source_label"] == "系统写入"
    assert auto_payload["confidence_tier"] in {"likely", "tentative"}
    assert auto_payload["confidence_tier"] != "confirmed"
    # 用户创建：told + 已确认（既有语义不变）
    assert user_payload["bucket"] == "told"
    assert user_payload["source_label"] == "你告诉我的"
    assert user_payload["confidence_tier"] == "confirmed"


@pytest.mark.asyncio
async def test_supersede_crash_window_retry_converges_single_active(db_session, provenance_env):
    """P2-4（PROBE7 复演）：create 腿已提交、supersede 腿崩溃 → 用户重试必须收敛，
    不允许两条 user_confirmed active 分叉进入召回。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    old = data["a_hypothesis"]

    # 模拟崩溃窗口：只有 create 腿提交（锚点与 update_item 的 create 腿完全同构）
    orphan = await MemoryService(db_session).create_episodic_memory(
        user_id=user.id,
        summary="崩溃窗口留下的替代记录",
        source_type="user_created",
        source_id=str(old.id),
        occurred_at=old.occurred_at,
        importance_score=None,
        tags=None,
        evidence_refs=[{"type": "user_state", "id": f"user_edit:{old.id}"}],
        source_lane="user_confirmed",
        epistemic_class="FACT",
        emit_system_update=False,
    )
    assert orphan is not None

    # 用户重试编辑（修复前：再建一条替代 → 两条 active 分叉）
    async with _client() as ac:
        resp = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{old.id}/update",
            json={"content": "用户明确表示自己只在周末晚上学习"},
        )
    assert resp.status_code == 200
    replacement_id = resp.json()["id"]

    await db_session.refresh(old)
    await db_session.refresh(orphan)
    # 收敛：旧记录与孤儿都指向新替代；锚定族恰一条 active
    assert str(old.superseded_by_id) == replacement_id
    assert str(orphan.superseded_by_id) == replacement_id
    from app.services.memory_epistemic_contract import MemoryRecordStatus, derive_status

    anchored = [old, orphan]
    result = await db_session.execute(
        select(EpisodicMemory).where(
            EpisodicMemory.user_id == user.id,
            EpisodicMemory.source_type == "user_created",
            EpisodicMemory.source_id == str(old.id),
        )
    )
    anchored.extend(result.scalars().all())
    active_rows = [row for row in anchored if derive_status(row, now=_utcnow()) == MemoryRecordStatus.ACTIVE.value]
    assert len(active_rows) == 1 and str(active_rows[0].id) == replacement_id
    # 检索面只见新替代（旧内容 + 崩溃孤儿都不可见）
    retrieval = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    ids = {str(row.id) for row in retrieval}
    assert str(old.id) not in ids and orphan.id not in ids
    assert replacement_id in ids


@pytest.mark.asyncio
async def test_supersede_lost_race_converges_rival(db_session, provenance_env, monkeypatch):
    """P2-4（并发分叉半）：首读见 ACTIVE、行锁重读前 rival 已取胜的竞态——
    本腿的新替代必须收敛 rival，绝不允许双 active 并存。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    old = data["a_hypothesis"]

    rival = await MemoryService(db_session).create_episodic_memory(
        user_id=user.id,
        summary="并发竞态的先到替代",
        source_type="user_created",
        source_id=str(old.id),
        occurred_at=old.occurred_at,
        importance_score=None,
        tags=None,
        evidence_refs=[{"type": "user_state", "id": f"user_edit:{old.id}"}],
        source_lane="user_confirmed",
        epistemic_class="FACT",
        emit_system_update=False,
    )
    assert rival is not None

    from app.services.memory_provenance_service import MemoryProvenanceService

    original_get = MemoryProvenanceService._get_record
    locked_reads = {"count": 0}

    async def racing_get(self, uid, kind, mid, *, for_update=False):
        record = await original_get(self, uid, kind, mid, for_update=for_update)
        if for_update and str(mid) == str(old.id):
            locked_reads["count"] += 1
            if locked_reads["count"] == 1:
                # 恰在行锁重读前，rival 的 supersede 腿先行提交（竞态注入）
                record.superseded_by_id = rival.id
                record.updated_at = _utcnow()
                await self.db.commit()
                await self.db.refresh(record)
        return record

    monkeypatch.setattr(MemoryProvenanceService, "_get_record", racing_get)

    service = MemoryProvenanceService(db_session)
    result = await service.update_item(user.id, "episodic", old.id, content="重试方最新的改写内容", reason="竞态重试")
    new_id = result["id"]

    await db_session.refresh(rival)
    await db_session.refresh(old)
    # 链收敛：old→rival→new；rival 被 newest-intent 收敛，非双 active
    assert str(old.superseded_by_id) == str(rival.id)
    assert str(rival.superseded_by_id) == new_id
    from app.services.memory_epistemic_contract import MemoryRecordStatus, derive_status

    assert derive_status(rival, now=_utcnow()) == MemoryRecordStatus.SUPERSEDED.value
    rows = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    active_anchored = [
        row
        for row in rows
        if str(row.id) in {str(old.id), str(rival.id), new_id}
        and derive_status(row, now=_utcnow()) == MemoryRecordStatus.ACTIVE.value
    ]
    assert [str(row.id) for row in active_anchored] == [new_id]


@pytest.mark.asyncio
async def test_superseded_excluded_from_recall_and_three_consumer_faces(db_session, provenance_env):
    """P2-5：supersede 后旧内容不得继续喂三个非预筛决策面（最长 7 天窗口）。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)

    # 社交面消费的 subject_type：person_mention
    old = await _insert_episodic(
        db_session,
        user,
        "用户和小明每周三一起自习",
        lane="direct_capture",
        source_type="chat",
    )
    old.subject_type = "person_mention"
    await db_session.commit()

    async with _client() as ac:
        resp = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{old.id}/update",
            json={"content": "用户和小明改为每周五一起自习", "reason": "时间说错了"},
        )
    assert resp.status_code == 200
    new_id = resp.json()["id"]

    # 1) 检索面（三消费者的共同数据入口）
    rows = await MemoryService(db_session).list_recent_episodic(user.id, limit=50)
    summaries = [row.summary for row in rows]
    assert "用户和小明每周三一起自习" not in summaries
    assert "用户和小明改为每周五一起自习" in summaries

    # 2) state_aggregator：RecentPersonMentions 用户状态字段
    from app.state_aggregator.service import StateAggregatorService

    envelope = await StateAggregatorService(db_session)._build_recent_person_mentions(user.id, now=_utcnow())
    mention_summaries = [m.summary for m in envelope.value.mentions]
    assert "用户和小明每周三一起自习" not in mention_summaries
    assert "用户和小明改为每周五一起自习" in mention_summaries

    # 3) 双核路由社交快照
    from app.routing.router_context_reader import RouterContextReader

    snapshot = await RouterContextReader(db_session).fetch(user.id)
    router_summaries = [m.summary for m in snapshot.recent_person_mentions]
    assert "用户和小明每周三一起自习" not in router_summaries
    assert "用户和小明改为每周五一起自习" in router_summaries

    # 4) Aurora 信号
    from app.aurora.signal_aggregator import _collect_memory

    payload = await _collect_memory(MemoryService(db_session), user.id, {})
    episodic_ids = [str(item.get("id")) for item in payload.get("recent_episodic", [])]
    assert str(old.id) not in episodic_ids
    assert new_id in episodic_ids


@pytest.mark.asyncio
async def test_why_this_superseded_carries_replacement_pointer_and_history_visible(db_session, provenance_env):
    """P3-7 + P3-6：superseded 旧 id 的 why-this 带替代指针；M-08 自己写的
    user_update/scope_update 审计在治理历史可见。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)

    async with _client() as ac:
        edited = await ac.post(
            f"/api/v1/memory/provenance/items/episodic/{data['a_hypothesis'].id}/update",
            json={"content": "改写后的内容"},
        )
        assert edited.status_code == 200
        replacement_id = edited.json()["id"]

        # P3-7：旧 id 的回执 → 现行版本指针
        why = await ac.post(
            "/api/v1/memory/provenance/why-this",
            json={"memory_ref": f"memory://episodic/{data['a_hypothesis'].id}"},
        )
        assert why.status_code == 200
        assert why.json()["memory"]["status_now"] == "superseded"
        assert why.json()["memory"]["replaced_by_ref"] == f"memory://episodic/{replacement_id}"

        # P3-6：goal 编辑（user_update）与 link（scope_update）审计在源历史可见
        a_plan = await _make_plan(db_session, user)
        goal_edit = await ac.post(
            f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/update",
            json={"title": "修订后的目标标题"},
        )
        assert goal_edit.status_code == 200
        goal_link = await ac.put(
            f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/scope",
            json={"action": "link_plan", "plan_id": str(a_plan.id)},
        )
        assert goal_link.status_code == 200

        source = await ac.get(f"/api/v1/memory/provenance/items/goal/{data['a_goal'].id}/source")
        assert source.status_code == 200
        actions = {row["action"] for row in source.json()["governance_history"]}
        assert "user_update" in actions
        assert "scope_update" in actions


@pytest.mark.asyncio
async def test_user_revoke_reason_code_uniform_across_kinds(db_session, provenance_env):
    """P3-8：M-08 revoke 面三种 kind 的 memory.invalidated 事件 reason_code 统一
    为 user_revoke（前瞻消费方可统一判 actor——修复前 episodic=user_delete、
    pref/goal=裸 revoke，三者不同形）。"""
    data = await _seed_two_user_dataset(db_session)
    user = data["a"]
    _install_overrides(db_session, user)
    targets = {
        "episodic": data["a_observation"],
        "preference": data["a_pref_explicit"],
        "goal": data["a_goal"],
    }

    for kind, target in targets.items():
        async with _client() as ac:
            resp = await ac.post(f"/api/v1/memory/provenance/items/{kind}/{target.id}/revoke", json={})
        assert resp.status_code == 200

    events = await _invalidation_events(db_session, user)
    reason_codes = set()
    for kind, target in targets.items():
        matched = [
            e
            for e in events
            if str(target.id) in e.get("memory_ids", []) and e.get("action") in {"revoke", "REVOKE", "user_revoke"}
        ]
        assert matched, f"{kind} revoke must write memory.invalidated"
        reason_codes.update(e.get("reason_code") for e in matched if e.get("reason_code"))
    assert reason_codes == {"user_revoke"}
