"""V4-D04 · 撤回读门接世代（D03 R2-C1 移交落地）+ 节点/列表/insight 同 version.

卡面验收：撤回证据后节点、列表、insight 同 version。
- R2-C3（读门接 epoch 为主）：同秒撤回不再依赖墙钟序（系统性漏检闭合）；
- R2-C1（commit 前重读为辅）：重算窗口内新撤回 ⇒ 提交前整体丢弃；
- 图面/建议面消费同一门：pending ⇒ 建议（insight）禁用 + 图面带同门出口。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user import User
from app.services.galaxy.mastery_evidence import MasteryEffectKind
from app.services.galaxy.outcome_absorption_service import _evidence_request_id
from app.services.retraction_recompute_service import (
    RECOMPUTE_TRACE_REASON,
    RetractionRecomputeService,
    _parse_pinned_epoch,
)

_T0 = datetime(2026, 9, 28, 10, 0, 0)

_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS mastery_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id CHAR(36) NOT NULL,
    user_id CHAR(36) NOT NULL,
    old_mastery INTEGER NOT NULL,
    new_mastery INTEGER NOT NULL,
    reason VARCHAR(100) NOT NULL,
    request_id VARCHAR(100),
    revision INTEGER DEFAULT 1,
    effect_kind VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS event_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id CHAR(36) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    sequence_number INTEGER NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
)
"""
_COUNTERS_DDL = """
CREATE TABLE IF NOT EXISTS event_sequence_counters (
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id CHAR(36) NOT NULL,
    next_sequence INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (aggregate_type, aggregate_id)
)
"""


async def _make_user(db_session) -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_node_with_status(db_session, user: User, *, mastery: float):
    node = KnowledgeNode(name=f"n{uuid4().hex[:8]}", importance_level=1)
    db_session.add(node)
    await db_session.flush()
    status = UserNodeStatus(user_id=user.id, node_id=node.id, mastery_score=mastery, revision=0)
    db_session.add(status)
    await db_session.flush()
    return node, status


async def _add_evidence_row(db_session, *, user: User, node, old: int, new: int, outcome_id: str, observed_at) -> None:
    request_id = _evidence_request_id(float(new), 0.9, outcome_id, None)
    await db_session.execute(
        text(
            "INSERT INTO mastery_audit_log "
            "(node_id, user_id, old_mastery, new_mastery, reason, request_id, revision, effect_kind, created_at) "
            "VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, 1, :effect_kind, :created_at)"
        ),
        {
            "node_id": str(node.id),
            "user_id": str(user.id),
            "old_mastery": old,
            "new_mastery": new,
            "reason": "evidence:task_outcome",
            "request_id": request_id,
            "effect_kind": "evidence",
            "created_at": observed_at,
        },
    )


@pytest.fixture()
async def gate_tables(db_session):
    await db_session.execute(text(_AUDIT_DDL))
    await db_session.execute(text(_OUTBOX_DDL))
    await db_session.execute(text(_COUNTERS_DDL))
    await db_session.commit()
    return True


# ---------------------------------------------------------------------------
# 钉世代（R2-C1/C-3 的机制基础）
# ---------------------------------------------------------------------------


def test_parse_pinned_epoch_shapes():
    assert _parse_pinned_epoch("epoch=7") == 7
    assert _parse_pinned_epoch("epoch=abc") is None
    assert _parse_pinned_epoch("obs=60;conf=0.8") is None
    assert _parse_pinned_epoch(None) is None


async def test_recompute_trace_row_pins_base_epoch(gate_tables, db_session):
    """正例：重算 trace 行把所钉世代写进 request_id 空位（``epoch=N``）。"""

    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    results = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch
    )
    assert results and results[0].outcome == "recomputed"

    row = (
        await db_session.execute(
            text(
                "SELECT request_id FROM mastery_audit_log "
                "WHERE user_id = :u AND node_id = :n AND reason = :r ORDER BY id DESC LIMIT 1"
            ),
            {"u": str(user.id), "n": str(node.id), "r": RECOMPUTE_TRACE_REASON},
        )
    ).first()
    assert row is not None and row[0] == f"epoch={registration.epoch}"

    # 同世代 ⇒ 读门新鲜（RECOMPUTED，非 stale）
    gate = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert gate.stale is False and gate.suggestions_allowed is True


# ---------------------------------------------------------------------------
# 同秒撤回（R2-C3 量化闭合）：墙钟漏检 ⇒ 世代门抓到
# ---------------------------------------------------------------------------


async def test_same_second_retraction_caught_by_epoch_gate(gate_tables, db_session):
    """反例：撤回事件与旧 trace 同墙钟秒（sqlite CURRENT_TIMESTAMP 秒粒度）
    ——旧墙钟比对判「新鲜」（created_at 相等不大于），世代比对判过期。"""
    from app.services.memory_service import MemoryService

    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id,
        kind="result_retracted",
        target_type="outcome",
        target_id=f"outc_{uuid4().hex}",
    )
    assert registration.epoch == 2

    # 模拟「重算发生在撤回前同一墙钟秒」：trace 行 created_at 与撤回事件
    # created_at 逐字节相同，钉的却是旧世代 epoch=1。
    event_created_at = (
        await db_session.execute(
            text(
                "SELECT created_at FROM event_outbox "
                "WHERE aggregate_type = :at AND aggregate_id = :aid AND event_type = :et "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"at": "user_retraction", "aid": str(user.id), "et": "retraction.registered"},
        )
    ).scalar_one()
    await db_session.execute(
        text(
            "INSERT INTO mastery_audit_log "
            "(node_id, user_id, old_mastery, new_mastery, reason, request_id, revision, effect_kind, created_at) "
            "VALUES (:node_id, :user_id, 40, 42, :reason, :request_id, 1, :effect_kind, :created_at)"
        ),
        {
            "node_id": str(node.id),
            "user_id": str(user.id),
            "reason": RECOMPUTE_TRACE_REASON,
            "request_id": "epoch=1",
            "effect_kind": MasteryEffectKind.PROJECTION.value,
            "created_at": event_created_at,
        },
    )
    await db_session.commit()

    # 墙钟面（D03 旧行为）：事件与 trace 同秒 ⇒ 漏检
    last_recompute_at = await service._last_recompute_at(user.id, node.id)
    last_retraction_at = await service._last_retraction_at(user.id)
    assert last_retraction_at is not None and last_recompute_at is not None
    assert not (last_retraction_at > last_recompute_at)  # 旧门在此漏检

    # 新门（世代为主）：钉 1 < 撤回 2 ⇒ pending（节点级 + 用户级同判）
    node_gate = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert node_gate.stale is True and node_gate.suggestions_allowed is False
    user_gate = await service.capability_user_read_state(user_id=user.id)
    assert user_gate.stale is True and user_gate.suggestions_allowed is False
    assert await MemoryService(db_session).get_memory_epoch(user.id) == 2


async def test_user_gate_fresh_when_no_retraction_despite_memory_epoch(gate_tables, db_session):
    """反例（不越权）：用户无撤回事件 ⇒ 用户级门恒新鲜——记忆域 epoch bump
    （M-01 删除/纠正）不得判星图过期。"""
    from app.services.memory_invalidation_pipeline import _bump_memory_epoch_in_txn
    from app.services.retraction_recompute_service import RecomputeStatus  # noqa: F401

    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=10.0)
    await _bump_memory_epoch_in_txn(db_session, user.id, reason="memory:delete")
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    gate = await service.capability_user_read_state(user_id=user.id)
    assert gate.stale is False and gate.suggestions_allowed is True
    assert gate.status == "fresh"
    assert node is not None


# ---------------------------------------------------------------------------
# commit 前重读（R2-C1 辅助防御）
# ---------------------------------------------------------------------------


async def test_commit_epoch_gate_discards_on_mid_window_advance(gate_tables, db_session):
    """反例（C-1 交错窗口）：重算窗口内 epoch 前进 ⇒ 提交门拒绝（不写回）；
    世代未动 ⇒ 放行（提交正常发生——D03 既有 happy path 同门）。"""
    from app.services.memory_service import MemoryService

    user = await _make_user(db_session)
    await _make_node_with_status(db_session, user, mastery=10.0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    epoch_at_start = await MemoryService(db_session).get_memory_epoch(user.id)
    allowed, current = await service._commit_epoch_gate(user.id, epoch_at_start)
    assert allowed is True and current == epoch_at_start

    # 窗口内：另一撤回落库（epoch 前进）——提交门拒绝
    await service.register_retraction(
        user_id=user.id,
        kind="result_retracted",
        target_type="outcome",
        target_id=f"outc_{uuid4().hex}",
    )
    epoch_after = await MemoryService(db_session).get_memory_epoch(user.id)
    assert epoch_after == epoch_at_start + 1
    allowed, current = await service._commit_epoch_gate(user.id, epoch_at_start)
    assert allowed is False and current == epoch_after
    # 不可证世代（None）fail-closed 拒绝（与发布栅栏同口径）
    allowed_none, _ = await service._commit_epoch_gate(user.id, None)
    assert allowed_none is False


async def test_recompute_with_stale_base_epoch_discards_per_node(gate_tables, db_session):
    """反例（栅栏回归面）：携旧 base_epoch 的重算 ⇒ 逐节点 discard_stale_epoch。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    # 重算后（世代收敛），再撤回另一 outcome（世代前进）——旧 base 的重算必须丢弃
    assert registration.epoch == 2
    await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch
    )
    second = await service.register_retraction(
        user_id=user.id,
        kind="result_retracted",
        target_type="outcome",
        target_id=f"outc_{uuid4().hex}",
    )
    results = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch  # 已过期
    )
    assert results
    assert results[0].outcome == "discard_stale_epoch"
    assert second.epoch == registration.epoch + 1


# ---------------------------------------------------------------------------
# 图面/建议面同门（节点、列表、insight 同 version）
# ---------------------------------------------------------------------------


async def test_predict_next_gated_by_pending_read_state(gate_tables, db_session):
    """反例（insight 面）：撤回 pending ⇒ predict-next 不给建议（同门出口）。"""
    from app.services.galaxy_service import GalaxyService
    from app.services.memory_service import MemoryService

    user = await _make_user(db_session)
    node, status = await _make_node_with_status(db_session, user, mastery=42.0)
    node.importance_level = 5  # 确保重算收敛后 fallback 推荐可命中
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )

    galaxy = GalaxyService(db_session)
    # 门在 pending：insight/建议面禁用（即便图上有可推荐节点）
    assert await galaxy.predict_next_node(user.id) is None

    # 重算收敛（携带当前世代过栅栏）⇒ 门转新鲜，建议恢复
    base_epoch = await MemoryService(db_session).get_memory_epoch(user.id)
    results = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=base_epoch
    )
    assert results and results[0].outcome == "recomputed"
    gate = await service.capability_user_read_state(user_id=user.id)
    assert gate.stale is False
    assert await galaxy.predict_next_node(user.id) is not None
    # 重算推进了投影版本（同 version 载体）
    await db_session.refresh(status)
    assert int(status.revision) >= 1
