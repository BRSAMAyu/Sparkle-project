"""G-04 · Galaxy 对 Correction/Delete/Version 的一致性 —— 派生视图不留残影.

真源链（与 70eb9b68/NBP-4 同一读面）：
``ErrorRecord.is_deleted`` tombstone / 任务硬删 / 草稿节点删除 →
``GalaxyConsistencyService``（溯源剪除 + 弱点标记重算）→
``invalidate_galaxy_graph_view_cache``（Redis 视图键 + shield）→
``get_galaxy_graph`` 立即新值。

红测面（修复前全部留残影）：
1. **溯源残影**：错题删除后 node detail 的 ``graph_event_sources`` 仍引用
   已删错题（reference 悬空）——必须剪除，且不误伤其他溯源面；
2. **WEAK 状态残影**：错题删除后 ``signal:weak_at`` 标记复活 WEAK 学习
   状态——无存活错题证据时必须摘除；
3. **缓存残影**：删除后读面 ttl=600 旧快照仍展示旧 error_count——必须
   即时失效，重读零 sleep 得新值；
4. **幂等门完整性**：溯源剪除不得破坏吸收幂等门（append-only audit 行
   才是硬门）——重放仍 duplicate，不复活点亮；
5. **草稿节点删除**：被删节点不得在读面活过缓存 TTL。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.cache import cache_service
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.error_book_service import ErrorBookService
from app.services.galaxy.consistency_service import GalaxyConsistencyService
from app.services.galaxy.outcome_absorption_service import GalaxyOutcomeAbsorber
from app.services.galaxy.provenance import append_graph_event_source
from app.services.galaxy_service import GalaxyService
from app.services.knowledge_integration_service import KnowledgeIntegrationService
from app.services.outcome_capture_service import (
    build_outcome_recorded_payload,
    build_task_outcome_capture,
)
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures（与 test_outcome_read_model_visibility 同款 SQLite DDL + 真实服务）
# ---------------------------------------------------------------------------


async def _ensure_mastery_audit_log(db_session) -> None:
    """吸收幂等硬门的物理表（raw SQL 写面，不在 Base.metadata）。"""
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


def _naive_now():
    return datetime.now(UTC).replace(tzinfo=None)


def _view(graph, node_id):
    for view in graph.nodes:
        if view.id == node_id:
            return view
    raise AssertionError(f"node {node_id} missing from galaxy graph response")


def _local_view_keys(user_id) -> list[str]:
    prefix = f"Sparkle:view:get_galaxy_graph:{user_id}:"
    return [k for k in cache_service._local_cache if k.startswith(prefix)]


async def _make_error(db, user_id, node_id: object, *, deleted: bool = False) -> ErrorRecord:
    error = ErrorRecord(
        user_id=user_id,
        subject_code="math",
        chapter="函数与方程",
        question_text="G-04 一致性错题",
        linked_knowledge_node_ids=[node_id],
        is_deleted=deleted,
    )
    db.add(error)
    await db.commit()
    await db.refresh(error)
    return error


async def _single_live_error(db, user_id) -> ErrorRecord:
    return (
        await db.execute(
            select(ErrorRecord).where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
        )
    ).scalars().one()


@pytest_asyncio.fixture()
async def consistency_env(db_session):
    user = await _make_user(db_session)
    node = KnowledgeNode(name="G-04 一致性节点", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    status = UserNodeStatus(user_id=user.id, node_id=node.id, mastery_score=20.0, is_unlocked=True)
    db_session.add(status)
    await db_session.commit()
    return db_session, user, node


# ---------------------------------------------------------------------------
# 1. 溯源残影：错题删除 → node detail 不再引用已删错题，其他溯源面保留
# ---------------------------------------------------------------------------


async def test_error_delete_prunes_only_error_provenance(consistency_env):
    db, user, node = consistency_env
    error = await _make_error(db, user.id, node.id)
    status = await db.get(UserNodeStatus, (user.id, node.id))
    append_graph_event_source(
        status,
        event_type="error.created",
        source_type="error_book",
        reference_id=error.id,
        label="knowledge_gap",
        payload={"error_type": "knowledge_gap"},
    )
    append_graph_event_source(
        status,
        event_type="translation.saved",
        source_type="translation",
        reference_id="doc-1",
        label="residues-free decoy",
        payload={},
    )
    await db.commit()

    assert await ErrorBookService(db).delete_error(error.id, user.id) is True

    await db.refresh(status)
    sources = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    by_type = {str(item.get("source_type")) for item in sources if isinstance(item, dict)}
    assert "error_book" not in by_type, "已删错题的溯源行必须被剪除（node detail 残影）"
    assert "translation" in by_type, "无关溯源面（translation）不得被误伤"


async def test_error_delete_keeps_live_error_provenance_on_other_errors(consistency_env):
    """多错题同节点：只删其一 → 存活错题的溯源行必须保留（按 reference 定界）."""
    db, user, node = consistency_env
    survivor = await _make_error(db, user.id, node.id)
    victim = await _make_error(db, user.id, node.id)
    status = await db.get(UserNodeStatus, (user.id, node.id))
    for err in (survivor, victim):
        append_graph_event_source(
            status,
            event_type="error.created",
            source_type="error_book",
            reference_id=err.id,
            label="error",
            payload={},
        )
    await db.commit()

    assert await ErrorBookService(db).delete_error(victim.id, user.id) is True

    await db.refresh(status)
    sources = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    refs = {str(item.get("reference_id")) for item in sources if isinstance(item, dict)}
    assert str(victim.id) not in refs, "被删错题的溯源必须剪除"
    assert str(survivor.id) in refs, "存活错题的溯源必须保留（Correction ≠ Delete）"


# ---------------------------------------------------------------------------
# 2. WEAK 状态残影：最后一个错题删除 → 弱点标记摘除；仍有存活错题 → 保留
# ---------------------------------------------------------------------------


async def test_error_delete_clears_weak_tag_when_last_error_gone(consistency_env):
    db, user, node = consistency_env
    await _make_error(db, user.id, node.id)
    node.keywords = ["signal:weak_at", "math"]
    await db.commit()

    error = await _single_live_error(db, user.id)
    assert await ErrorBookService(db).delete_error(error.id, user.id) is True

    await db.refresh(node)
    assert "signal:weak_at" not in (node.keywords or []), "无存活错题证据时弱点标记必须摘除（WEAK 残影）"
    assert "math" in (node.keywords or []), "无关关键词不得被误伤"


async def test_weak_tag_survives_when_other_live_errors_remain(consistency_env):
    db, user, node = consistency_env
    await _make_error(db, user.id, node.id)
    survivor = await _make_error(db, user.id, node.id)
    node.keywords = ["signal:weak_at"]
    await db.commit()

    victim = (
        await db.execute(
            select(ErrorRecord).where(
                ErrorRecord.user_id == user.id,
                ErrorRecord.is_deleted.is_(False),
                ErrorRecord.id != survivor.id,
            )
        )
    ).scalars().one()
    assert await ErrorBookService(db).delete_error(victim.id, user.id) is True

    await db.refresh(node)
    assert "signal:weak_at" in (node.keywords or []), "仍有存活错题时弱点标记必须保留"


# ---------------------------------------------------------------------------
# 3. 缓存残影：删除后读面即时新值（零 sleep）
# ---------------------------------------------------------------------------


async def test_error_delete_refreshes_read_model_immediately(consistency_env):
    db, user, node = consistency_env
    error = await _make_error(db, user.id, node.id)
    node.keywords = ["signal:weak_at"]
    await db.commit()

    service = GalaxyService(db)
    before = await service.get_galaxy_graph(user.id)
    view_before = _view(before, node.id)
    assert view_before.user_status is not None, "前置：节点已有个人状态"
    assert view_before.user_status.recent_error_count == 1, "前置：删除前读面必须看到 1 条近错"
    assert _local_view_keys(user.id), "前置：读面缓存必须已建立（本地兜底模式）"

    assert await ErrorBookService(db).delete_error(error.id, user.id) is True

    assert _local_view_keys(user.id) == [], "删除后视图缓存键必须被失效"
    after = await service.get_galaxy_graph(user.id)
    view_after = _view(after, node.id)
    assert view_after.user_status.recent_error_count == 0, "删除后重读必须零 sleep 得新值（缓存残影红线）"
    assert "signal:weak_at" not in (node.keywords or [])


# ---------------------------------------------------------------------------
# 4. 幂等门完整性：溯源剪除不破坏吸收幂等（事件重放不复活点亮）
# ---------------------------------------------------------------------------


async def test_provenance_prune_cannot_resurrect_absorbed_light(consistency_env):
    """剪除 outcome 溯源后重放同一 outcome：硬门（audit 行）在 → duplicate。

    红线：若幂等门误挂在溯源行上，剪除溯源会让重放二次点亮（Version 复活）。
    """
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import Task, TaskStatus, TaskType

    db, user, node = consistency_env
    await _ensure_mastery_audit_log(db)
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="G-04 重放任务",
        type=TaskType.LEARNING,
        estimated_minutes=10,
        status=TaskStatus.COMPLETED,
        completed_at=_naive_now(),
        knowledge_node_id=node.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="完成",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    payload = build_outcome_recorded_payload(build_task_outcome_capture(task))

    absorber = GalaxyOutcomeAbsorber(db)
    first = await absorber.absorb_outcome(dict(payload))
    assert first.action == "lit", "前置：首次吸收必须点亮"
    lit_mastery = float((await db.get(UserNodeStatus, (user.id, node.id))).mastery_score)

    # 全量剪除该 outcome 的溯源行（比删除更狠的残影清理）
    pruned = await GalaxyConsistencyService(db).prune_provenance(
        user_id=user.id, source_type="outcome_ledger", reference_id=first.outcome_id
    )
    status = await db.get(UserNodeStatus, (user.id, node.id))
    sources = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    assert pruned >= 1 and not sources, "前置：该 outcome 的溯源必须已被剪空"

    replay = await absorber.absorb_outcome(dict(payload))
    assert replay.action == "duplicate", "剪除溯源后重放必须仍走 audit 幂等门（duplicate）"
    status_after = await db.get(UserNodeStatus, (user.id, node.id))
    assert float(status_after.mastery_score) == pytest.approx(lit_mastery), "重放不得二次点亮（Version 不复活）"


# ---------------------------------------------------------------------------
# 5. 草稿节点删除：读面不得活过缓存 TTL
# ---------------------------------------------------------------------------


async def test_draft_node_delete_disappears_from_read_model_immediately(db_session):
    user = await _make_user(db_session)
    service = KnowledgeIntegrationService(db_session)
    node = await service.create_vocabulary_node(
        user_id=user.id,
        source_text="resonance",
        translation="共振",
        context="physics reading",
    )
    assert node.status == "draft", "前置：词汇节点是草稿"

    graph = await GalaxyService(db_session).get_galaxy_graph(user.id)
    _view(graph, node.id)
    assert _local_view_keys(user.id), "前置：读面缓存已建立"

    await service.delete_draft_node(node.id, user.id)

    assert _local_view_keys(user.id) == [], "删除后视图缓存必须被失效"
    after = await GalaxyService(db_session).get_galaxy_graph(user.id)
    with pytest.raises(AssertionError):
        _view(after, node.id)


# ---------------------------------------------------------------------------
# 6. 任务硬删：读面缓存失效（目标关联残影）
# ---------------------------------------------------------------------------


async def test_task_delete_invalidates_read_model(consistency_env):
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import Task, TaskStatus, TaskType
    from app.services.task_service import TaskService

    db, user, node = consistency_env
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="G-04 目标关联任务",
        type=TaskType.LEARNING,
        estimated_minutes=15,
        status=TaskStatus.IN_PROGRESS,
        knowledge_node_id=node.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="进行中",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    graph = await GalaxyService(db).get_galaxy_graph(user.id)
    _view(graph, node.id)
    assert _local_view_keys(user.id), "前置：读面缓存已建立"

    await TaskService.delete(db, task)

    assert _local_view_keys(user.id) == [], "任务删除后星图读面必须立即失效（goal-connected 残影）"


# ---------------------------------------------------------------------------
# 7. 重放/幂等：consistency 清理自身可重放（零剪除零放大）
# ---------------------------------------------------------------------------


async def test_consistency_cleanup_is_replay_safe(consistency_env):
    db, user, node = consistency_env
    error = await _make_error(db, user.id, node.id)
    result = await GalaxyConsistencyService(db).handle_error_deleted(
        user_id=user.id, error_id=error.id, node_ids=[node.id]
    )
    assert result["pruned_statuses"] >= 0

    replay = await GalaxyConsistencyService(db).handle_error_deleted(
        user_id=user.id, error_id=error.id, node_ids=[node.id]
    )
    assert replay["pruned_statuses"] == 0, "重放清理必须零剪除（幂等，无残影也无写放大）"
