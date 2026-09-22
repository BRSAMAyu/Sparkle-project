"""NBP-4 · 任务完成 → 星图读模型可见延迟消除（写后即时投影验收）.

LOOP3 北极星实测：任务完成后星图节点掌握度分钟级才可见。归因：吸收链
（outcome.recorded → GalaxyOutcomeAbsorber → UserNodeStatus）秒级落库，
但读面 ``GalaxyService.get_galaxy_graph`` 挂 ``@cached(ttl=600)`` 视图缓存，
吸收路径从不失效 → 「学完 → 看到星图长大」被吞最长 10 分钟。

本文件红测（真实 DB + 真实缓存面，零 sleep）：
1. **读面即时可见**：预热图缓存（mastery=0 快照）→ 吸收 POSITIVE outcome →
   立即重读星图，掌握度/解锁状态必须已是融合后值（30.0）；
2. **失效面精确性**：只有可见动作（lit/flagged）触发失效，duplicate 重放
   不产生失效流量；
3. **缓存兜底面**：无 Redis（本地缓存兜底）时 ``delete_pattern`` 必须真的
   剔除匹配键——否则整个失效面在兜底模式下形同虚设（回归坑）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskStatus
from app.services.galaxy.outcome_absorption_service import (
    GalaxyOutcomeAbsorber,
    invalidate_galaxy_graph_view_cache,
)
from app.services.galaxy_service import GalaxyService
from app.services.outcome_capture_service import (
    build_outcome_recorded_payload,
    build_task_outcome_capture,
)
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures（与 test_outcome_absorption 同款 SQLite DDL + 真实吸收逻辑）
# ---------------------------------------------------------------------------


async def _ensure_mastery_audit_log(db_session) -> None:
    await db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mastery_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                old_mastery INTEGER NOT NULL,
                new_mastery INTEGER NOT NULL,
                reason TEXT,
                request_id TEXT,
                revision INTEGER DEFAULT 1,
                created_at DATETIME NOT NULL
            )
        """))
    await db_session.commit()


@pytest_asyncio.fixture()
async def readmodel_env(db_session):
    await _ensure_mastery_audit_log(db_session)
    user = await _make_user(db_session)
    node = KnowledgeNode(name="星图读面可见性节点", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return db_session, user, node


def _naive_now():
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(tzinfo=None)


async def _make_completed_task(db, user, node) -> Task:
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import TaskType

    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="NBP-4 读面即时性任务",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=TaskStatus.COMPLETED,
        completed_at=_naive_now(),
        knowledge_node_id=node.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="完成并留下证据",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


def _task_payload(task) -> dict:
    """Real X-08 producer: terminal task → content-free outcome.recorded payload."""
    return build_outcome_recorded_payload(build_task_outcome_capture(task))


def _node_view(graph, node_id):
    for view in graph.nodes:
        if view.id == node_id:
            return view
    raise AssertionError(f"node {node_id} missing from galaxy graph response")


# ---------------------------------------------------------------------------
# 1. 学完 → 立即看到星图长大（无 sleep、无 TTL 依赖）
# ---------------------------------------------------------------------------


async def test_absorbed_outcome_visible_on_galaxy_graph_immediately(readmodel_env):
    """预热读面缓存 → 吸收 → 立即重读：掌握度必须是融合后值，而非缓存旧值.

    红线：修复前该测试失败——第二次 get_galaxy_graph 命中 ttl=600 旧缓存，
    user_status 仍是预热时的 None（mastery 0 快照），星图分钟级不生长。
    """
    db, user, node = readmodel_env

    # 预热读面缓存：吸收前快照（节点尚无 UserNodeStatus）
    before = await GalaxyService(db).get_galaxy_graph(user.id)
    view_before = _node_view(before, node.id)
    assert view_before.user_status is None, "前置：吸收前节点无个人状态"

    task = await _make_completed_task(db, user, node)
    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "lit"

    # 立即重读（零 sleep）：读面必须反映吸收后的掌握度
    after = await GalaxyService(db).get_galaxy_graph(user.id)
    view_after = _node_view(after, node.id)
    assert view_after.user_status is not None, "吸收后读面必须出现个人状态（不得被旧缓存吞掉）"
    assert view_after.user_status.mastery_score == pytest.approx(30.0)


async def test_read_model_cache_really_invalidated_between_reads(readmodel_env):
    """失效面直证：同 user 连读两次命中缓存，吸收后第三次必须换新值.

    用「缓存命中计数」区分真失效 vs 巧合：预热后连读一次（必命中），
    吸收（lit）后重读——若失效面失灵，返回的仍是预热快照。
    """
    db, user, node = readmodel_env

    first = await GalaxyService(db).get_galaxy_graph(user.id)
    assert _node_view(first, node.id).user_status is None
    # 确认缓存确实存在（第二次读命中，不重算）——观察 local cache 键
    prefix = f"Sparkle:view:get_galaxy_graph:{user.id}:"
    cached_keys = [k for k in cache_service._local_cache if k.startswith(prefix)] if not cache_service.redis else []
    assert cached_keys, "前置：读面缓存必须已建立（本测试环境为本地兜底缓存）"

    task = await _make_completed_task(db, user, node)
    await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))

    # 失效后：旧键必须已从缓存面消失
    remaining = [k for k in cache_service._local_cache if k.startswith(prefix)] if not cache_service.redis else []
    assert remaining == [], "lit 吸收后视图缓存键必须被失效"

    after = await GalaxyService(db).get_galaxy_graph(user.id)
    assert _node_view(after, node.id).user_status.mastery_score == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# 2. 失效面精确性：可见动作才失效，重放零流量
# ---------------------------------------------------------------------------


async def test_invalidation_fires_on_visible_actions_only(readmodel_env, monkeypatch):
    """lit 触发失效；duplicate 重放不触发（重放是幂等面，读面零变化）。"""
    db, user, node = readmodel_env
    task = await _make_completed_task(db, user, node)
    payload = _task_payload(task)

    calls: list[object] = []

    async def _spy(target_user_id):
        calls.append(target_user_id)
        return await invalidate_galaxy_graph_view_cache(target_user_id)

    monkeypatch.setattr(
        "app.services.galaxy.outcome_absorption_service.invalidate_galaxy_graph_view_cache", _spy
    )
    absorber = GalaxyOutcomeAbsorber(db)

    await absorber.absorb_outcome(dict(payload))
    assert len(calls) == 1, "lit 必须触发一次读面失效"

    await absorber.absorb_outcome(dict(payload))  # 重放 → duplicate
    assert len(calls) == 1, "duplicate 重放不得产生失效流量（读面零变化）"


async def test_negative_flag_invalidates_read_face(readmodel_env, monkeypatch):
    """NEGATIVE flagged 也改变读面（弱点标记 → review_signal），必须失效."""
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import TaskType

    db, user, node = readmodel_env
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="NBP-4 负向任务",
        type=TaskType.LEARNING,
        estimated_minutes=10,
        status=TaskStatus.ABANDONED,
        knowledge_node_id=node.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="记录放弃",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    calls: list[object] = []

    async def _spy(target_user_id):
        calls.append(target_user_id)
        return await invalidate_galaxy_graph_view_cache(target_user_id)

    monkeypatch.setattr(
        "app.services.galaxy.outcome_absorption_service.invalidate_galaxy_graph_view_cache", _spy
    )
    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "flagged"
    assert len(calls) == 1, "flagged（弱点标记入图）必须触发读面失效"


# ---------------------------------------------------------------------------
# 3. 缓存兜底面：无 Redis 时 delete_pattern 必须真的剔除本地键
# ---------------------------------------------------------------------------


async def test_delete_pattern_evicts_local_cache_fallback(monkeypatch):
    """本地兜底模式下失效语义与 Redis 模式一致（NBP-4 回归坑直证）。

    修复前 delete_pattern 在 redis=None 时是 no-op：cached 写进 _local_cache
    的键删不掉，写后即时投影在兜底模式下形同虚设。
    """
    monkeypatch.setattr(cache_service, "redis", None)
    marker = uuid4().hex
    own_prefix = f"Sparkle:view:get_galaxy_graph:nbp4-local-{marker}:"
    own_keys = [f"{own_prefix}None:True:False", f"{own_prefix}exam:True:True"]
    decoy = f"Sparkle:view:get_galaxy_graph:nbp4-other-{marker}:{uuid4().hex}:None:True:False"
    for key in [*own_keys, decoy]:
        await cache_service.set(key, {"probe": key})
        assert await cache_service.get(key) is not None

    deleted = await cache_service.delete_pattern(f"Sparkle:view:get_galaxy_graph:nbp4-local-{marker}:*")

    assert deleted == len(own_keys), "必须剔除前缀匹配的全部本地键"
    for key in own_keys:
        assert await cache_service.get(key) is None, f"{key} 必须已被剔除"
    assert await cache_service.get(decoy) is not None, "无关用户键必须保留"
