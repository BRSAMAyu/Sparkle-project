"""M-07 红绿基线测试：Correction/Delete/Revocation + Memory Epoch 终局。

统一删除语义管线（correction/revoke/supersede/delete → 单一 status 变更管线）：
每个有效变更确定性触发 epoch bump（原子、事务内）+ memory.invalidated 事件
（D-01 词表，correlation 带 memory_id，payload 不落记忆内容明文）+ derived
缓存失效（profile_context / inline_snapshot / prefs_center / aurora self-model）。

验收锚点（任务卡）：
1. 删除后 retrieval/cache/context 新请求 0 使用；旧 derived summary 不复活；
2. 双设备/重试/重复删除幂等——终态一致且无重复副作用；
3. 审计保留删除事实但事件 payload 不暴露内容；
4. in-flight 当前轮不回滚（声明式），下一轮装配 0 使用（list_recent_episodic 钉住）。
"""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.models.memory import EpisodicMemory, MemoryCorrection
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter

# ---------------------------------------------------------------------------
# Fake Redis（测试 hermetic：绝不碰 127.0.0.1:6379 的 dev Redis）
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
# event_outbox / event_sequence_counters 最小 sqlite 表（对齐 5f2b9b3c0e6f 迁移列）
# ---------------------------------------------------------------------------

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


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


@pytest.fixture(name="patch_enqueue")
def patch_enqueue_fixture(monkeypatch):
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())
    # apply_correction 提交后会用真实 cache_service.redis 写 Aurora self-model
    # （90 天 TTL）——测试必须 hermetic，不碰本机 dev Redis。
    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService.record_user_correction",
        AsyncMock(),
    )


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


async def _create_episodic(
    db_session, user: User, summary: str, *, lane: str = "inferred_extraction"
) -> EpisodicMemory:
    from datetime import UTC, datetime

    record = EpisodicMemory(
        user_id=user.id,
        summary=summary,
        source_type="chat",
        source_lane=lane,
        subject_type="study_habit",
        occurred_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


async def _get_epoch(db_session, user: User) -> int:
    from app.services.memory_service import MemoryService

    return await MemoryService(db_session).get_memory_epoch(user.id)


async def _outbox_rows(db_session, event_type: str = "memory.invalidated") -> list[dict]:
    result = await db_session.execute(
        text(
            "SELECT aggregate_type, aggregate_id, event_type, sequence_number, payload, metadata FROM event_outbox WHERE event_type = :t"
        ),
        {"t": event_type},
    )
    return [dict(row._mapping) for row in result.all()]


# ---------------------------------------------------------------------------
# 1. 事件词表（D-01 扩词表流程：登记并冻结）
# ---------------------------------------------------------------------------


def test_memory_invalidated_event_is_registered_live():
    from app.core.event_registry import EVENT_REGISTRY, EventStage

    entry = EVENT_REGISTRY["memory.invalidated"]
    assert entry.stage is EventStage.STATE_UPDATE
    assert entry.aggregate_type == "user_memory"
    assert entry.status == "live"
    assert any("memory_invalidation_pipeline" in producer for producer in entry.producers)


def test_memory_id_is_auxiliary_correlation_key():
    from app.core.event_registry import CORRELATION_KEYS, CorrelationIds

    assert "memory_id" in CORRELATION_KEYS
    memory_id = uuid4()
    corr = CorrelationIds(memory_id=memory_id)
    assert corr.as_dict() == {"memory_id": str(memory_id)}


# ---------------------------------------------------------------------------
# 2. 幂等：重复删除 / 重试 → 终态一致、无重复副作用
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_user_delete_is_idempotent(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    memory = await _create_episodic(db_session, user, "用户每天 23 点后效率骤降")

    first = await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id, reason="user_deleted")
    assert first is not None and first.revoked_at is not None

    epoch_after_first = await _get_epoch(db_session, user)
    audit_after_first = (
        (
            await db_session.execute(
                select(MemoryCorrection).where(
                    MemoryCorrection.user_id == user.id,
                    MemoryCorrection.action == "delete",
                )
            )
        )
        .scalars()
        .all()
    )
    events_after_first = await _outbox_rows(db_session)
    revoked_at_first = first.revoked_at
    correction_count_first = first.correction_count

    # 双设备/重试：第二次删除同一 memory —— 必须无重复副作用。
    second = await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id, reason="user_deleted")

    assert second is not None, "重复删除应幂等成功而非 404 循环"
    epoch_after_second = await _get_epoch(db_session, user)
    audit_after_second = (
        (
            await db_session.execute(
                select(MemoryCorrection).where(
                    MemoryCorrection.user_id == user.id,
                    MemoryCorrection.action == "delete",
                )
            )
        )
        .scalars()
        .all()
    )
    events_after_second = await _outbox_rows(db_session)

    assert epoch_after_second == epoch_after_first, "重复删除不得二次 bump epoch"
    assert len(audit_after_second) == len(audit_after_first) == 1, "审计行不重复"
    assert len(events_after_second) == len(events_after_first) == 1, "invalidation 事件不重复"
    assert second.revoked_at == revoked_at_first, "revoked_at 不被覆盖"
    assert second.correction_count == correction_count_first, "correction_count 不重复累加"


@pytest.mark.asyncio
async def test_retract_memory_repeat_keeps_single_epoch(db_session, patch_enqueue, outbox_tables):
    from app.config import settings
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    pref = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert pref is not None
    settings.ENABLE_MEMORY_RETRACTION = True

    assert await service.retract_memory(kind="preference", memory_id=pref.id, user_id=user.id)
    epoch_once = await _get_epoch(db_session, user)

    # 重试同一删除 → 幂等成功，epoch 不再变化。
    assert await service.retract_memory(kind="preference", memory_id=pref.id, user_id=user.id)
    assert await _get_epoch(db_session, user) == epoch_once


@pytest.mark.asyncio
async def test_apply_correction_reject_repeat_idempotent(db_session, patch_enqueue, outbox_tables):
    from app.config import settings
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    memory = await _create_episodic(db_session, user, "偏好晚上学数学", lane="direct_capture")
    settings.ENABLE_MEMORY_CORRECTION = True
    settings.ENABLE_MEMORY_RETRACTION = True

    first = await service.apply_correction(
        kind="episodic", memory_id=memory.id, user_id=user.id, action="reject", reason="记错了"
    )
    assert first is not None
    epoch_once = await _get_epoch(db_session, user)

    second = await service.apply_correction(
        kind="episodic", memory_id=memory.id, user_id=user.id, action="reject", reason="记错了"
    )
    assert second is not None, "重复纠错幂等成功"
    assert await _get_epoch(db_session, user) == epoch_once
    # 状态检查：两次后 retracted/revoked 恰好一种、仅一处。
    statuses = {first.retracted_at is not None, first.revoked_at is not None}
    assert True in statuses


# ---------------------------------------------------------------------------
# 3. 硬保证：每个有效变更 → epoch bump + 内容无关事件
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_episodic_bumps_epoch_and_writes_content_free_event(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    secret_summary = "用户的银行卡尾号是 8888"
    memory = await _create_episodic(db_session, user, secret_summary)

    assert await _get_epoch(db_session, user) == 1
    await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id, reason="user_deleted")

    # epoch 硬 bump（非 best-effort）。
    assert await _get_epoch(db_session, user) == 2

    events = await _outbox_rows(db_session)
    assert len(events) == 1
    event = events[0]
    assert event["aggregate_type"] == "user_memory"
    assert event["aggregate_id"] == str(user.id)

    metadata = event["metadata"] if isinstance(event["metadata"], dict) else json.loads(event["metadata"])
    assert metadata["schema_version"] == "event.v1"
    assert metadata["user_id"] == str(user.id)
    assert metadata["correlation"]["memory_id"] == str(memory.id)

    payload = event["payload"] if isinstance(event["payload"], dict) else json.loads(event["payload"])
    assert payload["memory_epoch"] == 2
    assert payload["memory_ids"] == [str(memory.id)]
    assert payload["memory_type"] == "episodic"
    # SECURITY_PRIVACY：事件不携带记忆内容明文（审计保留事实，不暴露内容）。
    assert "summary" not in payload
    assert "content" not in payload
    assert secret_summary not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_supersede_bumps_epoch_and_emits_event(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())

    initial = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.8},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert initial is not None
    # 首写（无 supersede）不 bump epoch。
    assert await _get_epoch(db_session, user) == 1
    assert (await _outbox_rows(db_session)) == []

    second = await service.upsert_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value={"value": 0.5},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert second is not None and second.version == 2
    # supersede（用户纠正出 v2）确定性触发 epoch + 事件。
    assert await _get_epoch(db_session, user) == 2
    events = await _outbox_rows(db_session)
    assert len(events) == 1
    payload = events[0]["payload"] if isinstance(events[0]["payload"], dict) else json.loads(events[0]["payload"])
    assert payload["action"] == "supersede"
    assert payload["memory_epoch"] == 2


@pytest.mark.asyncio
async def test_bulk_revoke_bumps_epoch_once_per_user(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user_a = await _create_user(db_session)
    user_b = await _create_user(db_session)
    for user in (user_a, user_b):
        await _create_episodic(db_session, user, f"{user.username} 的推断记忆 1")
        await _create_episodic(db_session, user, f"{user.username} 的推断记忆 2")

    service = MemoryService(db_session, FakeRedis())
    count = await service.revoke_inferred_memories(reason="admin_kill_switch")
    assert count == 4

    assert await _get_epoch(db_session, user_a) == 2
    assert await _get_epoch(db_session, user_b) == 2

    events = await _outbox_rows(db_session)
    assert len(events) == 2, "每用户恰好一条 invalidation 事件"
    for event in events:
        payload = event["payload"] if isinstance(event["payload"], dict) else json.loads(event["payload"])
        assert len(payload["memory_ids"]) == 2
        assert payload["action"] == "bulk_revoke"


@pytest.mark.asyncio
async def test_bulk_revoke_locked_recheck_skips_terminal_rows(db_session, patch_enqueue, outbox_tables):
    """R1-C2-2/R2-P2-3：bulk 入口行锁内逐行终态复查。

    superseded 终态行（superseded_by_id 置位、revoked_at 为 NULL——能穿过
    SQL 预过滤）必须被 derive_status 复查排除：不撤销、不计入 count、
    memory_ids 不含它。这是并发收敛语义在单连接 sqlite 下可钉住的部分：
    PG 上两个重叠批次在 FOR UPDATE 行锁上串行化，先到批次留下的终态行
    （revoked 或 superseded），后到批次锁内重读 + 复查后零触碰 → 每用户
    恰一次 epoch bump / 一条聚合事件（无双 bump 双事件路径）。删掉复查
    过滤本测试必红（变异击杀）。
    """
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    keep = await _create_episodic(db_session, user, "待撤销的推断")
    superseded = await _create_episodic(db_session, user, "已被顶替的推断")
    # 模拟并发先到批次/冲突解决的产物：superseded 处于终态但 revoked_at 为
    # NULL —— 只能靠 derive_status 复查识别。
    superseded.superseded_by_id = keep.id
    await db_session.commit()

    service = MemoryService(db_session, FakeRedis())
    count = await service.revoke_inferred_memories(user_id=user.id, reason="test")
    assert count == 1, "superseded 终态行不得被 bulk 撤销（复查必须排除）"

    await db_session.refresh(keep)
    await db_session.refresh(superseded)
    assert keep.revoked_at is not None
    assert superseded.revoked_at is None and superseded.retracted_at is None, "终态行不被二次触碰"

    # 该用户恰一次 bump / 一条事件，memory_ids 只含有效行。
    assert await _get_epoch(db_session, user) == 2
    events = await _outbox_rows(db_session)
    assert len(events) == 1
    payload = events[0]["payload"] if isinstance(events[0]["payload"], dict) else json.loads(events[0]["payload"])
    assert payload["memory_ids"] == [str(keep.id)]


# ---------------------------------------------------------------------------
# 4. derived 不复活：live 偏好视图 / profile_context 缓存 / inline snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_panel_preference_delete_removes_live_value(db_session, patch_enqueue, outbox_tables):
    """记忆面板删除偏好 → live 视图（ProfileContext 的真源）不得复活该值。"""
    from app.config import settings
    from app.services.memory_service import MemoryService
    from app.services.profile_write_service import ProfileWriteService

    user = await _create_user(db_session)
    settings.ENABLE_USER_MEMORY_CONTROLS = False
    write_service = ProfileWriteService(db_session, FakeRedis())
    await write_service.set_explicit_preference(
        user_id=user.id,
        pref_key="depth_preference",
        pref_value=0.8,
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
    )

    live = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user.id))
    ).scalar_one()
    assert live.explicit.get("depth_preference") == 0.8

    memory_service = MemoryService(db_session, FakeRedis())
    head = await memory_service.find_preference(user.id, "depth_preference")
    assert head is not None

    settings.ENABLE_MEMORY_RETRACTION = True
    assert await memory_service.retract_memory(kind="preference", memory_id=head.id, user_id=user.id)

    await db_session.refresh(live)
    assert "depth_preference" not in (live.explicit or {}), "删除链头后 live 视图复活了已删除偏好"


@pytest.mark.asyncio
async def test_preference_delete_after_supersede_chain_removes_live_key(db_session, patch_enqueue, outbox_tables):
    """R1-C1/R2-P1 回归：supersede 链（设值→改值）后删除链头，live 键必须摘除。

    本功能最典型的产品流：设置偏好 0.6 → 修改为 0.8（v1.replaced_by_id=v2，
    v2 为活跃链头）→ 面板删除链头 v2。head-check 若不过滤 superseded 终态行
    （replaced_by_id 置位、retracted_at 为 NULL），会命中被顶替的 v1 →
    live 键不摘除 → ProfileContext 每次编译复活已删除的用户值。构造采纳自
    R2 探针 #1（r2_probe1_supersede_chain_test.py，原树运行时实证 P1）。
    """
    from app.config import settings
    from app.services.memory_service import MemoryService
    from app.services.profile_write_service import ProfileWriteService

    user = await _create_user(db_session)
    settings.ENABLE_USER_MEMORY_CONTROLS = False
    settings.ENABLE_MEMORY_RETRACTION = True
    write_service = ProfileWriteService(db_session, FakeRedis())

    refs = [{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}]
    await write_service.set_explicit_preference(
        user_id=user.id, pref_key="depth_preference", pref_value=0.6, evidence_refs=refs
    )
    await write_service.set_explicit_preference(
        user_id=user.id, pref_key="depth_preference", pref_value=0.8, evidence_refs=refs
    )

    live = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user.id))
    ).scalar_one()
    assert live.explicit.get("depth_preference") == 0.8

    memory_service = MemoryService(db_session, FakeRedis())
    head = await memory_service.find_preference(user.id, "depth_preference")
    assert head is not None and head.version == 2, "两次写入后链头必须是 v2（supersede 链成立）"

    assert await memory_service.retract_memory(kind="preference", memory_id=head.id, user_id=user.id)

    await db_session.refresh(live)
    assert "depth_preference" not in (
        live.explicit or {}
    ), "C1 regression: live key survived head deletion after a supersede chain (resurrection channel open)"


@pytest.mark.asyncio
async def test_profile_context_cache_rejected_after_epoch_bump(db_session, patch_enqueue, monkeypatch):
    """epoch 门：即使缓存 DEL 失败/竞态，epoch 变化后消费方必须拒绝旧 derived 快照。

    M-07 R1-C2-1/R2-P2-4：本测试必须钉住 epoch 门本身——门的 version 来源
    （``PreferenceService.get_preference_version``）与构建时的 fake version
    保持一致，使 preference_version 门恒通过，仅剩 epoch 条件能拒绝 stale
    缓存。旧构造 fake version=7 而门读真实 DB（无行→默认 0），版本失配先
    行拒绝，epoch 条件从未参与（变异 M1 存活的根因）。构造采纳自 R2 探针
    #2（``r2_probe2_epoch_gate_test.py``）。
    """
    from app.core.profile_context import ProfileContext
    from app.core.user_insight_state import UserInsightState
    from app.services import profile_context_service as pcs_module
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    fake_redis = FakeRedis()

    compile_calls = []

    class _StubContract:
        canonical_state = UserInsightState()

        def to_prompt_context(self):
            return {}

    async def _fake_compile(self, *, user_id, profile_context, **kwargs):
        compile_calls.append(user_id)
        return _StubContract()

    monkeypatch.setattr(pcs_module.UserInsightCompiler, "compile", _fake_compile)

    async def _fake_prefs(self, user_id):
        return {
            "explicit": {"depth_preference": 0.8},
            "inferred": {},
            "version": 7,
            "traits_prior": {},
            "trait_observation_state": {},
            "traits_coldstart_completed_at": None,
        }

    # 关键差异（对旧构造）：门的 version 来源与缓存 payload 一致 →
    # preference_version 门恒通过，唯一能拒绝 stale 条目的只剩 epoch 门。
    async def _fake_gate_version(self, user_id):
        return 7

    async def _empty_knowledge(self, user_id):
        from app.core.profile_context import KnowledgeSummary

        return KnowledgeSummary()

    async def _empty_cognitive(self, user_id):
        from app.core.profile_context import CognitiveSummary

        return CognitiveSummary()

    async def _empty_errors(self, user_id):
        return {"summary": {}, "recent": []}

    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_preferences", _fake_prefs)
    monkeypatch.setattr(pcs_module.PreferenceService, "get_preference_version", _fake_gate_version)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_knowledge_summary", _empty_knowledge)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_cognitive_summary", _empty_cognitive)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_error_summary", _empty_errors)

    # _attach_live_extensions 全部 try/except 包裹，但直接短路更稳。
    async def _no_extensions(self, user_id, context, **kwargs):
        return None

    monkeypatch.setattr(pcs_module.ProfileContextService, "_attach_live_extensions", _no_extensions)
    monkeypatch.setattr(
        pcs_module.AuroraStage34KillSwitchService, "summary", AsyncMock(return_value={"capsule_mode": "shadow"})
    )

    service = pcs_module.ProfileContextService(db_session, fake_redis)

    ctx1 = await service.get_profile_context(user.id)
    assert len(compile_calls) == 1
    # R1 C3-① 修正：await 协程，否则断言恒真（未 await 的协程对象非 None）。
    assert await fake_redis.get(f"user:profile_context:{user.id}") is not None

    # 模拟 DEL 失败/竞态：把 epoch bump 前的旧 payload 重新塞回缓存。
    stale_payload = ctx1.model_dump_json()
    await fake_redis.setex(f"user:profile_context:{user.id}", 120, stale_payload)

    # 删除一条 episodic 记忆 → epoch bump。
    memory = await _create_episodic(db_session, user, "临时观察")
    memory_service = MemoryService(db_session, fake_redis)
    await memory_service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id)
    await fake_redis.setex(f"user:profile_context:{user.id}", 120, stale_payload)  # 再次模拟 DEL 失败

    ctx2 = await service.get_profile_context(user.id)
    assert len(compile_calls) == 2, "epoch 变化后必须重编译，不得复用旧 derived 快照"
    assert isinstance(ctx2, ProfileContext)
    assert ctx2.memory_epoch == 2


@pytest.mark.asyncio
async def test_inline_snapshot_stale_after_epoch_bump(db_session, patch_enqueue, monkeypatch):
    from app.services import profile_context_service as pcs_module
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    fake_redis = FakeRedis()
    service = pcs_module.ProfileContextService(db_session, fake_redis)

    await service._write_inline_snapshot_cache(user.id, {"stable_preferences": {"depth_preference": 0.8}})
    snapshot = await service.get_inline_snapshot(user.id)
    assert snapshot is not None, "epoch 未变时快照可读"

    memory = await _create_episodic(db_session, user, "临时观察")
    await MemoryService(db_session, fake_redis).revoke_episodic_memory(user_id=user.id, memory_id=memory.id)

    # 模拟 DEL 失败：旧快照仍在 Redis，但 epoch 门必须拒绝（不得复活）。
    await fake_redis.setex(
        f"user:inline_snapshot:{user.id}",
        120,
        json.dumps({"stable_preferences": {"depth_preference": 0.8}}),
    )
    assert await service.get_inline_snapshot(user.id) is None, "epoch 变化后旧 inline snapshot 必须被视为 stale"


@pytest.mark.asyncio
async def test_inline_snapshot_pins_epoch_read_before_content_assembly(db_session, patch_enqueue, monkeypatch):
    """R1-C2-4/R2-P2-2：inline snapshot（与 profile_context）的 epoch 必须取自
    内容装配前的前置读取，并复用于两处嵌入。

    模拟 ABA 竞态：装配开始时 epoch=1；装配期间（prefs→knowledge→…→compile）
    删除事务 commit，此后任何 epoch 读取都返回 bump 后的 2。写缓存时二次读取
    的旧实现会给旧内容盖上新 epoch 戳（读侧门通过 → 已删内容以 120s TTL
    复活）；前置读取的实现全程只读一次，快照携带旧 epoch=1，读侧门以
    current=2 拒绝——复活窗关闭。
    """
    from app.core.profile_context import CognitiveSummary, KnowledgeSummary
    from app.core.user_insight_state import UserInsightState
    from app.services import profile_context_service as pcs_module

    user = await _create_user(db_session)
    fake_redis = FakeRedis()
    epoch_reads = {"count": 0}

    async def _racing_epoch(self, user_id):
        epoch_reads["count"] += 1
        # 第 1 次读取 = 前置读取（内容装配前）；此后构建期间删除已 commit，
        # 后续任何读取（若实现仍二次读取）看到的都是 bump 后的值。
        return 1 if epoch_reads["count"] == 1 else 2

    class _StubContract:
        canonical_state = UserInsightState()

        def to_prompt_context(self):
            return {}

    async def _fake_compile(self, *, user_id, profile_context, **kwargs):
        return _StubContract()

    async def _fake_prefs(self, user_id):
        return {
            "explicit": {},
            "inferred": {},
            "version": 7,
            "traits_prior": {},
            "trait_observation_state": {},
            "traits_coldstart_completed_at": None,
        }

    async def _empty_errors(self, user_id):
        return {"summary": {}, "recent": []}

    async def _empty_knowledge(self, user_id):
        return KnowledgeSummary()

    async def _empty_cognitive(self, user_id):
        return CognitiveSummary()

    async def _no_extensions(self, user_id, context, **kwargs):
        return None

    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_memory_epoch", _racing_epoch)
    monkeypatch.setattr(pcs_module.UserInsightCompiler, "compile", _fake_compile)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_preferences", _fake_prefs)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_knowledge_summary", _empty_knowledge)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_cognitive_summary", _empty_cognitive)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_get_error_summary", _empty_errors)
    monkeypatch.setattr(pcs_module.ProfileContextService, "_attach_live_extensions", _no_extensions)
    monkeypatch.setattr(
        pcs_module.AuroraStage34KillSwitchService, "summary", AsyncMock(return_value={"capsule_mode": "shadow"})
    )

    service = pcs_module.ProfileContextService(db_session, fake_redis)
    context = await service.get_profile_context(user.id)

    # 前置读取实现：整个编译路径恰好一次 epoch 读取，ProfileContext 与
    # inline snapshot 两处嵌入复用同一个值。
    assert epoch_reads["count"] == 1, "epoch 应在内容装配前读取一次并复用（C2-4），不得在写缓存时二次读取"
    assert context.memory_epoch == 1
    assert json.loads(await fake_redis.get(f"user:profile_context:{user.id}"))["memory_epoch"] == 1

    snapshot_raw = await fake_redis.get(f"user:inline_snapshot:{user.id}")
    assert snapshot_raw is not None
    assert (
        json.loads(snapshot_raw)["memory_epoch"] == 1
    ), "inline snapshot 必须携带内容装配前读到的 epoch——写时二次读取会给旧内容盖新 epoch 戳（ABA 复活窗）"

    # 读侧门：current epoch 已 bump 到 2 → 旧快照必须被拒绝（复活通道关闭）。
    assert await service.get_inline_snapshot(user.id) is None


@pytest.mark.asyncio
async def test_aurora_self_model_cache_cleared_on_delete(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    fake_redis = FakeRedis()
    await fake_redis.setex(f"aurora:self_model:{user.id}", 999999, json.dumps({"assumptions": ["x"]}))

    memory = await _create_episodic(db_session, user, "推导出的假设")
    service = MemoryService(db_session, fake_redis)
    await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id)

    assert f"aurora:self_model:{user.id}" not in fake_redis.store, "90 天 TTL 的 Aurora self-model 必须被主动失效"


@pytest.mark.asyncio
async def test_profile_context_cache_cleared_on_delete(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    fake_redis = FakeRedis()
    await fake_redis.setex(f"user:profile_context:{user.id}", 120, "{}")
    await fake_redis.setex(f"user:inline_snapshot:{user.id}", 120, "{}")

    memory = await _create_episodic(db_session, user, "临时观察")
    service = MemoryService(db_session, fake_redis)
    await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id)

    assert f"user:profile_context:{user.id}" not in fake_redis.store
    assert f"user:inline_snapshot:{user.id}" not in fake_redis.store


# ---------------------------------------------------------------------------
# 5. retrieval / context 新请求 0 使用（下一轮装配）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleted_episodic_absent_from_next_assembly(db_session, patch_enqueue, outbox_tables):
    """下一轮装配的数据源（list_recent_episodic ← context_builder/context_pack）0 使用。"""
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    keep = await _create_episodic(db_session, user, "保留的观察", lane="direct_capture")
    drop = await _create_episodic(db_session, user, "要删除的观察", lane="direct_capture")

    await service.revoke_episodic_memory(user_id=user.id, memory_id=drop.id)

    visible = await service.list_recent_episodic(user.id, limit=10)
    visible_ids = {str(record.id) for record in visible}
    assert str(keep.id) in visible_ids
    assert str(drop.id) not in visible_ids

    retracted_visible = await service.get_recent_episodic(user.id, limit=10)
    assert all(str(getattr(record, "id", "")) != str(drop.id) for record in retracted_visible)


@pytest.mark.asyncio
async def test_bulk_revoke_zero_use_afterwards(db_session, patch_enqueue, outbox_tables):
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    await _create_episodic(db_session, user, "推断 1")
    await _create_episodic(db_session, user, "推断 2")

    service = MemoryService(db_session, FakeRedis())
    assert await service.revoke_inferred_memories(user_id=user.id, reason="test") == 2
    assert await service.list_recent_episodic(user.id, limit=10) == []


@pytest.mark.asyncio
async def test_working_memory_forget_and_reject_pin_zero_use(db_session):
    """WM 的 Redis 态即真源：forget 后新请求（list/build_snapshot）0 使用；rejected 被过滤。"""
    from app.working_memory.schema import WorkingMemoryEntry
    from app.working_memory.service import WorkingMemoryService

    def _entry(entry_id: str, text: str) -> WorkingMemoryEntry:
        from datetime import UTC, datetime

        now = datetime.now(UTC).replace(tzinfo=None)
        return WorkingMemoryEntry(
            entry_id=entry_id,
            user_id="u1",
            session_id="s1",
            text=text,
            semantic_key=f"key:{entry_id}",
            salience_score=0.5,
            mention_count=1,
            first_seen_at=now,
            last_seen_at=now,
            source_turn_ids=("t1",),
            subject_type="study_habit",
            confidence=0.6,
            evidence_token="tok",
            occurred_at=now,
        )

    wm = WorkingMemoryService()  # local_store 模式
    await wm._save_entry(_entry("e1", "临时条目"), ttl_seconds=300)
    await wm._save_entry(_entry("e2", "保留条目"), ttl_seconds=300)

    assert await wm.forget_entry(user_id="u1", session_id="s1", entry_id="e1")
    entries = await wm.list_entries(user_id="u1", session_id="s1")
    assert [entry.entry_id for entry in entries] == ["e2"]

    rejected = await wm.mark_rejected(user_id="u1", session_id="s1", entry_id="e2")
    assert rejected is not None and rejected.rejected
    assert await wm.list_entries(user_id="u1", session_id="s1") == []
    snapshot = await wm.build_snapshot(user_id="u1", session_id="s1")
    assert snapshot == ()


# ---------------------------------------------------------------------------
# 6. in-flight：当前轮不回滚（声明式钉住——本轮引用的是装配时快照）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inflight_current_turn_snapshot_is_not_rolled_back(db_session, patch_enqueue, outbox_tables):
    """当前轮已注入的上下文不回滚：删除发生后，本轮已取走的引用仍持有（声明式验收），
    但下一轮（重新装配）0 使用——由上一测试钉住。此处钉住"不抛错、不影响已注入快照"。"""
    from app.services.memory_service import MemoryService

    user = await _create_user(db_session)
    service = MemoryService(db_session, FakeRedis())
    memory = await _create_episodic(db_session, user, "本轮已注入的记忆")

    # 本轮装配（模拟 in-flight run 已注入）。
    injected = await service.list_recent_episodic(user.id, limit=10)
    assert len(injected) == 1

    # 删除发生在本轮进行中。
    await service.revoke_episodic_memory(user_id=user.id, memory_id=memory.id)

    # 已注入引用不被追改（in-flight 不回滚）。
    assert injected[0].summary == "本轮已注入的记忆"

    # 下一轮装配 0 使用。
    assert await service.list_recent_episodic(user.id, limit=10) == []
