"""C-07 红绿测试：Context Cache 版本键 / Memory Epoch / Policy Version 正确性。

灵魂红线：缓存不允许继续使用删除/纠正前的信息。四个 stale 面：

- Face A：``ContextBuilderMixin._user_context_cache``（进程内 120s TTL）——
  版本化组合键 + 写入/纠偏指令轮整轮绕缓存 + 版本解析失败 fail-closed；
- Face B：``user:context:snapshot:{uid}``（Redis 300s）——CognitiveContext
  钉 memory_epoch + 读侧门比对（0 = fail-closed）+ M-07 DEL 模板扩展；
- Face C：``MemorySettingsService.update_settings`` 读权限门字段变化 →
  同事务 epoch bump + 提交后派生缓存 DEL；
- Face D：graphrag 文本 cache 读路径在写入/纠偏指令轮 bypass。

验收锚点（任务卡）：
1. 删除/纠正后 0 stale reuse（变异：拆失效 → 必红）；
2. 跨 user 0 collision（键首段 user 维度）；
3. cache hit metrics 保留 + 命中路径性能不显著退化（版本读 << 重建）。
"""

from __future__ import annotations

import asyncio
import inspect
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.context_manager import CognitiveContext, ContextOrchestrator
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.orchestration.capability_lane import MEMORY_CLASS_INSTRUCTION, classify_memory_class_message
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.graph_rag import graphrag_text_cache_bypass
from app.services.context_cache_key import (
    CONTEXT_CACHE_SCHEMA_VERSION,
    ContextCacheVersionError,
    ContextCacheVersions,
    context_cache_key,
    resolve_context_cache_versions,
)
from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline
from app.services.memory_service import MemoryService
from app.services.memory_settings_service import READ_GATE_FIELDS, MemorySettingsService

# ---------------------------------------------------------------------------
# Hermetic FakeRedis（绝不碰本机 dev Redis）
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


# ---------------------------------------------------------------------------
# 共享夹具
# ---------------------------------------------------------------------------


class _CacheHarness(ContextBuilderMixin):
    """只挂 Face A 所需属性的最小 mixin 宿主（无 ChatOrchestrator 依赖）。"""

    def __init__(self, redis_client=None):
        self.redis = redis_client


async def _create_user(db_session) -> User:
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


async def _create_settings_row(db_session, user: User, *, memory_epoch: int = 1) -> UserMemorySettings:
    row = UserMemorySettings(user_id=user.id, memory_epoch=memory_epoch)
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


def _versions(user_id: str, **overrides) -> ContextCacheVersions:
    base: dict = {
        "user_id": user_id,
        "memory_epoch": 1,
        "preference_version": 0,
        "policy_version": "polpatch_none",
        "knowledge_version": "know_v1",
    }
    base.update(overrides)
    return ContextCacheVersions(**base)


# ---------------------------------------------------------------------------
# 1. 组合键：user 维度 + 任一版本变化 → 键变
# ---------------------------------------------------------------------------


def test_cache_key_user_dimension_is_structural():
    """跨 user 0 collision：同版本组、不同用户 → 键必然不同，且 user 打头。"""
    key_a = _versions("aaaaaaaa-1111-2222-3333-444444444444").cache_key()
    key_b = _versions("bbbbbbbb-1111-2222-3333-444444444444").cache_key()
    assert key_a.startswith("aaaaaaaa-1111-2222-3333-444444444444|")
    assert key_b.startswith("bbbbbbbb-1111-2222-3333-444444444444|")
    assert key_a != key_b


def test_cache_key_changes_on_any_version_component():
    user = "aaaaaaaa-1111-2222-3333-444444444444"
    baseline = context_cache_key(_versions(user))
    variants = (
        context_cache_key(_versions(user, memory_epoch=2)),
        context_cache_key(_versions(user, preference_version=1)),
        context_cache_key(_versions(user, policy_version="polpatch_abc")),
        context_cache_key(_versions(user, knowledge_version="know_v2")),
        context_cache_key(_versions(user, knowledge_version=None)),
        context_cache_key(_versions(user, schema_version=CONTEXT_CACHE_SCHEMA_VERSION + ".next")),
    )
    assert all(v != baseline for v in variants)
    assert len(set(variants)) == len(variants)


@pytest.mark.asyncio
async def test_resolve_versions_reads_real_sources(db_session):
    """接入既有权威源：epoch/pref 版本从真实行读出，空 patch 集 = polpatch_none。"""
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user, memory_epoch=5)

    from app.models.user_preferences import UserPreferencesCenter

    db_session.add(UserPreferencesCenter(user_id=user.id, version=3))
    await db_session.commit()

    versions = await resolve_context_cache_versions(db_session, user.id)
    assert versions.memory_epoch == 5
    assert versions.preference_version == 3
    assert versions.policy_version == "polpatch_none"
    assert versions.schema_version == CONTEXT_CACHE_SCHEMA_VERSION
    # knowledge_version 在无 redis 的 sqlite 环境走 DB 聚合：合法串或 None 皆可，但不得抛
    assert versions.knowledge_version is None or isinstance(versions.knowledge_version, str)


@pytest.mark.asyncio
async def test_resolve_versions_fail_closed_on_epoch_error(db_session, monkeypatch):
    """epoch 读失败必须 fail-closed 抛错（消费方绕缓存重建），不得静默降级。"""
    user = await _create_user(db_session)
    monkeypatch.setattr(MemoryService, "get_memory_epoch", AsyncMock(side_effect=RuntimeError("db down")))
    with pytest.raises(ContextCacheVersionError):
        await resolve_context_cache_versions(db_session, user.id)


# ---------------------------------------------------------------------------
# 2. Face A：进程内 context cache 版本键 + write-intent bypass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_face_a_write_intent_bypasses_cache(db_session):
    """写入/纠偏指令轮 → (None, write_intent_bypass)：旧文本 cache 不可用。"""
    user = await _create_user(db_session)
    harness = _CacheHarness()

    key, outcome = await harness._context_cache_resolve_key(user.id, db_session, "帮我记一下我的复习方式是刷题")
    assert key is None
    assert outcome == "write_intent_bypass"

    # 普通读轮（含记忆检索问答）不受影响
    key2, outcome2 = await harness._context_cache_resolve_key(user.id, db_session, "我的复习方式是什么")
    assert outcome2 == "ok"
    assert key2 is not None and key2.startswith(str(user.id))


@pytest.mark.asyncio
async def test_face_a_version_error_fail_closed(db_session, monkeypatch):
    """版本解析失败 → (None, version_error_bypass)：宁可重建，不可无版本命中。"""
    user = await _create_user(db_session)
    harness = _CacheHarness()
    monkeypatch.setattr(
        "app.orchestration.context_builder.resolve_context_cache_versions",
        AsyncMock(side_effect=ContextCacheVersionError("boom")),
    )
    key, outcome = await harness._context_cache_resolve_key(user.id, db_session, "今天天气怎么样")
    assert key is None
    assert outcome == "version_error_bypass"


@pytest.mark.asyncio
async def test_face_a_lookup_hit_miss_and_isolation():
    """命中返回深拷贝；不同键互不可见；过期条目惰性淘汰。"""
    harness = _CacheHarness()
    key = _versions("aaaaaaaa-1111-2222-3333-444444444444").cache_key()
    other_key = _versions("bbbbbbbb-1111-2222-3333-444444444444").cache_key()

    assert harness._context_cache_lookup(key) is None  # miss
    harness._context_cache_store(key, {"marker": "A", "episodic_memories": [{"summary": "secret"}]})

    payload = harness._context_cache_lookup(key)
    assert payload == {"marker": "A", "episodic_memories": [{"summary": "secret"}]}
    # 深拷贝隔离：改返回值不影响缓存内条目
    payload["episodic_memories"][0]["summary"] = "mutated"
    assert harness._context_cache_lookup(key)["episodic_memories"][0]["summary"] == "secret"
    # 跨键（跨 user）隔离
    assert harness._context_cache_lookup(other_key) is None

    # TTL 过期 → miss + 惰性清理
    stamp = harness._user_context_cache[key][0]
    harness._user_context_cache[key] = (
        stamp - (harness._USER_CONTEXT_CACHE_TTL_SECONDS + 1),
        harness._user_context_cache[key][1],
    )
    assert harness._context_cache_lookup(key) is None
    assert key not in harness._user_context_cache


@pytest.mark.asyncio
async def test_face_a_delete_orphans_cached_entry_zero_stale(db_session):
    """headline：删除记忆 → epoch bump → 键变 → 旧键不可达（0 stale reuse）。"""
    from app.models.memory import EpisodicMemory

    user = await _create_user(db_session)
    memory = EpisodicMemory(
        user_id=user.id,
        summary="USER_SECRET_MEMORY_TEXT",
        source_type="chat",
        source_lane="user_confirmed",
        subject_type="study_habit",
        occurred_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    db_session.add(memory)
    await db_session.commit()
    await db_session.refresh(memory)

    harness = _CacheHarness()
    versions_before = await resolve_context_cache_versions(db_session, user.id)
    key_before = versions_before.cache_key()
    harness._context_cache_store(key_before, {"episodic_memories": [{"summary": "USER_SECRET_MEMORY_TEXT"}]})
    assert harness._context_cache_lookup(key_before) is not None

    # 用户删除（M-07 统一管线：软删 + epoch bump 同事务）
    deleted = await MemoryService(db_session).revoke_episodic_memory(
        user_id=user.id, memory_id=memory.id, reason="user delete"
    )
    assert deleted is not None

    versions_after = await resolve_context_cache_versions(db_session, user.id)
    key_after = versions_after.cache_key()
    assert versions_after.memory_epoch > versions_before.memory_epoch
    assert key_after != key_before

    # 旧键成为孤儿：即便 TTL 未到，装配流程在当前键下只会 miss → 重建
    assert harness._context_cache_lookup(key_after) is None
    # 模拟 _build_full_context 决策流：当前键 miss → 从真源重建 → 无被删文本
    fresh = harness._context_cache_lookup(key_after)
    if fresh is None:
        fresh = {"episodic_memories": []}  # 真源重建：被删行已 revoked 不再入装配
    assert "USER_SECRET_MEMORY_TEXT" not in str(fresh)


@pytest.mark.asyncio
async def test_face_a_lru_capacity_bounds_entries():
    harness = _CacheHarness()
    harness._USER_CONTEXT_CACHE_MAX_ENTRIES = 4  # type: ignore[misc]
    for i in range(6):
        harness._context_cache_store(_versions(f"user-{i}").cache_key(), {"i": i})
        await asyncio.sleep(0)  # 保证 monotonic 时间戳可区分
    assert len(harness._user_context_cache) <= 4
    assert harness._context_cache_lookup(_versions("user-5").cache_key()) == {"i": 5}


# ---------------------------------------------------------------------------
# 3. Face B：Redis 聚合快照 epoch 读侧门
# ---------------------------------------------------------------------------


def test_cognitive_context_memory_epoch_default_zero():
    """旧快照（无 memory_epoch 字段）反序列化 → 0 → 读侧门必判 mismatch。"""
    ctx = CognitiveContext(user_id="u", timestamp=datetime.now(UTC))
    assert ctx.memory_epoch == 0


def test_face_b_derived_cache_keys_include_context_snapshot():
    uid = uuid4()
    keys = MemoryInvalidationPipeline.derived_cache_keys(user_id=uid, kinds=set())
    assert f"user:context:snapshot:{uid}" in keys
    assert f"user:profile_context:{uid}" in keys
    assert f"user:inline_snapshot:{uid}" in keys


@pytest.mark.asyncio
async def test_face_b_snapshot_epoch_gate_rejects_stale(db_session, monkeypatch):
    """epoch 不一致（删除后）→ 拒绝命中快照 → 走重建路径（0 stale）。"""
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user, memory_epoch=1)
    orchestrator = ContextOrchestrator(db_session, FakeRedis())

    stale_snapshot = CognitiveContext(
        user_id=str(user.id),
        timestamp=datetime.now(UTC),
        memory_epoch=1,
        preference_version=3,
        past_session_memory=[{"summary": "STALE_DELETED_TEXT"}],
    )
    monkeypatch.setattr(orchestrator, "_get_cached_context", AsyncMock(return_value=stale_snapshot))
    monkeypatch.setattr(orchestrator, "_get_memory_epoch", AsyncMock(return_value=2))  # 删除后 bump → 2
    # 偏好版本钉成一致：本测只允许 epoch 门独立拦住 stale 命中
    # （否则 pref 门会掩盖 epoch 门失效——变异实验 M-2 依赖此隔离）
    monkeypatch.setattr(orchestrator, "_get_preference_version", AsyncMock(return_value=3))

    # 重建主干：把全部子抓取器替换为空载荷哨兵（真源重建语义 = 空记忆文本）
    monkeypatch.setattr(orchestrator, "_get_recent_achievement_progress_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(orchestrator, "_get_spine_model_claims", AsyncMock(return_value=[]))
    monkeypatch.setattr(orchestrator, "_get_past_session_memory", AsyncMock(return_value=[]))
    for name, ret in (
        ("_get_profile_context", None),
        ("_get_error_profile", {"summary": {}, "recent": []}),
        ("_get_task_profile", {"tasks": [], "focus": {}}),
        ("_get_user_metrics", {}),
        ("_get_community_profile", {}),
        ("_get_social_context_v1", {}),
        ("_get_achievement_context", {}),
        ("_get_calendar_context", {}),
        ("_get_capsule_preferences", {}),
    ):
        monkeypatch.setattr(orchestrator, name, AsyncMock(return_value=ret))

    result = await orchestrator.get_user_context(str(user.id))
    # 重建出的新快照 epoch = 当前 epoch（2），且不带旧快照的 stale 文本
    assert result.memory_epoch == 2
    assert result.past_session_memory == []
    assert result is not stale_snapshot


@pytest.mark.asyncio
async def test_face_b_snapshot_hit_when_epochs_match(db_session, monkeypatch):
    """epoch + pref 版本均一致 → 命中缓存（hit 路径保留）。"""
    user = await _create_user(db_session)
    orchestrator = ContextOrchestrator(db_session, FakeRedis())

    cached = CognitiveContext(
        user_id=str(user.id),
        timestamp=datetime.now(UTC),
        memory_epoch=7,
        preference_version=3,
    )
    monkeypatch.setattr(orchestrator, "_get_cached_context", AsyncMock(return_value=cached))
    monkeypatch.setattr(orchestrator, "_get_memory_epoch", AsyncMock(return_value=7))
    monkeypatch.setattr(orchestrator, "_get_preference_version", AsyncMock(return_value=3))
    monkeypatch.setattr(orchestrator, "_get_past_session_memory", AsyncMock(return_value=[]))

    result = await orchestrator.get_user_context(str(user.id))
    assert result is cached


@pytest.mark.asyncio
async def test_face_b_epoch_read_failure_fails_closed(db_session, monkeypatch):
    """epoch 读失败 → 0 → 与已钉快照必不一致 → 重建（fail-closed）。"""
    user = await _create_user(db_session)
    orchestrator = ContextOrchestrator(db_session, FakeRedis())
    cached = CognitiveContext(user_id=str(user.id), timestamp=datetime.now(UTC), memory_epoch=7)
    monkeypatch.setattr(orchestrator, "_get_cached_context", AsyncMock(return_value=cached))
    monkeypatch.setattr(orchestrator, "_get_memory_epoch", AsyncMock(return_value=0))

    rebuild_entered = {"v": False}

    def _boom(*args, **kwargs):
        rebuild_entered["v"] = True
        raise RuntimeError("rebuild path entered (expected)")  # 主干第一处 DB 读即抛

    monkeypatch.setattr(orchestrator, "_get_recent_achievement_progress_events", AsyncMock(side_effect=_boom))
    with pytest.raises(RuntimeError):
        await orchestrator.get_user_context(str(user.id))
    assert rebuild_entered["v"] is True


# ---------------------------------------------------------------------------
# 4. Face C：读权限门字段变化 → epoch bump + 派生缓存 DEL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_face_c_permission_flip_bumps_epoch_and_dels(db_session):
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user)
    fake_redis = FakeRedis()
    uid = str(user.id)
    fake_redis.store.update(
        {
            f"user:profile_context:{uid}": "old",
            f"user:context:snapshot:{uid}": "old",
            f"aurora:self_model:{uid}": "old",
        }
    )

    service = MemorySettingsService(db_session, fake_redis)
    record = await service.update_settings(user.id, {"allow_episodic": False})

    assert record.allow_episodic is False
    epoch = await MemoryService(db_session).get_memory_epoch(user.id)
    assert epoch == 2  # 恰一次 bump
    # 派生缓存全部被 DEL
    assert f"user:profile_context:{uid}" not in fake_redis.store
    assert f"user:context:snapshot:{uid}" not in fake_redis.store
    assert f"aurora:self_model:{uid}" not in fake_redis.store
    # 审计：epoch_bump 行存在
    from sqlalchemy import select

    from app.models.memory import MemoryCorrection

    rows = (
        (await db_session.execute(select(MemoryCorrection).where(MemoryCorrection.user_id == user.id))).scalars().all()
    )
    assert any(r.action == "epoch_bump" for r in rows)


@pytest.mark.asyncio
async def test_face_c_non_gate_change_does_not_bump(db_session):
    """capture_level 是写侧档位：变化不触发 epoch bump（失效面不越界）。"""
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user)
    service = MemorySettingsService(db_session, FakeRedis())
    await service.update_settings(user.id, {"capture_level": "high"})
    assert await MemoryService(db_session).get_memory_epoch(user.id) == 1


@pytest.mark.asyncio
async def test_face_c_noop_update_does_not_bump(db_session):
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user)
    service = MemorySettingsService(db_session, FakeRedis())
    await service.update_settings(user.id, {"allow_episodic": True})  # 与现值相同
    assert await MemoryService(db_session).get_memory_epoch(user.id) == 1


def test_face_c_read_gate_fields_cover_policy_evaluator_gates():
    """读权限词表与 MemoryPolicyEvaluator 的读侧 gate 字段对齐。"""
    from app.services.memory_policy_evaluator import MemoryPolicyEvaluator

    src = inspect.getsource(MemoryPolicyEvaluator)
    for field in ("enabled", "allow_preferences", "allow_goals", "allow_episodic", "allow_inferred_episodic"):
        assert field in READ_GATE_FIELDS
        assert field in src


# ---------------------------------------------------------------------------
# 5. Face D：graphrag 文本 cache 写入/纠偏轮 bypass
# ---------------------------------------------------------------------------


def test_face_d_predicate_flags_memory_instruction_only():
    assert graphrag_text_cache_bypass("请记住：我的复习方式是刷题") is True
    assert graphrag_text_cache_bypass("帮我记一下我怕高数挂科") is True
    assert graphrag_text_cache_bypass("别忘了明天要交作业") is True
    # 检索问答 / 普通查询：允许命中（版本键已保证读新鲜）
    assert graphrag_text_cache_bypass("我的复习方式是什么") is False
    assert graphrag_text_cache_bypass("什么是光合作用") is False
    assert graphrag_text_cache_bypass("") is False
    # 词表同源：与 chat 主链同一权威判定
    assert graphrag_text_cache_bypass("记住我的口味") == (
        classify_memory_class_message("记住我的口味") == MEMORY_CLASS_INSTRUCTION
    )


def test_face_d_cache_read_is_gated_before_lookup():
    """AST 级钉桩：retrieve 的缓存读必须在 write-intent 门之下。"""
    from app.orchestration.graph_rag import GraphRAGRetriever

    src = inspect.getsource(GraphRAGRetriever.retrieve)
    gate_pos = src.find("graphrag_text_cache_bypass")
    read_pos = src.find("_get_cached_result")
    assert gate_pos != -1, "write-intent gate missing in retrieve()"
    assert read_pos != -1, "cache read missing in retrieve()"
    assert gate_pos < read_pos, "cache read must be gated after write-intent check"
    # bypass 轮不读缓存（读调用在 else 分支内）
    assert "if _write_intent_turn:" in src
    assert 'result="write_intent_bypass"' in src


# ---------------------------------------------------------------------------
# 6. 命中路径性能：版本读 + 深拷贝 << 全量重建
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hit_path_performance_bounded(db_session):
    user = await _create_user(db_session)
    await _create_settings_row(db_session, user)
    harness = _CacheHarness()
    payload = {"episodic_memories": [{"summary": f"m{i}"} for i in range(50)]}

    key, outcome = await harness._context_cache_resolve_key(user.id, db_session, "普通闲聊一轮")
    assert outcome == "ok"
    harness._context_cache_store(key, payload)

    # 预热后测命中路径（键解析 = 全部版本读 + lookup + deepcopy）
    rounds = 20
    t0 = time.perf_counter()
    for _ in range(rounds):
        k, o = await harness._context_cache_resolve_key(user.id, db_session, "普通闲聊一轮")
        assert o == "ok"
        got = harness._context_cache_lookup(k)
        assert got is not None
    hit_elapsed = (time.perf_counter() - t0) / rounds

    # 重建路径用 200ms 睡眠模拟（真实重建 1-2s 量级）
    t1 = time.perf_counter()
    await asyncio.sleep(0.2)
    rebuild_elapsed = time.perf_counter() - t1

    assert hit_elapsed < 0.05, f"hit path {hit_elapsed * 1000:.1f}ms exceeds 50ms bound"
    assert hit_elapsed < rebuild_elapsed / 4, "hit path must stay well below rebuild cost"
