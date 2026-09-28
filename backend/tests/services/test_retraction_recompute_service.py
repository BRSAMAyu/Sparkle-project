"""V4-D03 · 撤回派生影响与投影重算服务层守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项（卡 V4-D03，每条一正一反可失败）：
1. **并发旧job不能复活已删内容**：持久墓碑 + 发布栅栏（旧 epoch job 丢弃）；
2. **非线性状态按有效事件回放而非减旧分数**：重算结果 = G-01 权威回放值
   （精确相等钉死），合法其他来源保留；
3. **重算中UI与工具均标过期，不继续旧建议**：读门 pending ⇒ stale + 建议禁用
   （同一门两出口），重算完成转新鲜。

幂等面：登记重放零重复副作用；重算重放恒同结果。
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
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.retraction_recompute_service import (
    RECOMPUTE_TRACE_REASON,
    RETRACTION_AGGREGATE_TYPE,
    RETRACTION_REGISTERED_EVENT,
    RetractionRecomputeError,
    RetractionRecomputeService,
)

_T0 = datetime(2026, 9, 19, 10, 0, 0)

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


async def _make_node_with_status(db_session, user: User, *, mastery: float) -> tuple[KnowledgeNode, UserNodeStatus]:
    node = KnowledgeNode(name=f"n{uuid4().hex[:8]}", importance_level=1)
    db_session.add(node)
    await db_session.flush()
    status = UserNodeStatus(user_id=user.id, node_id=node.id, mastery_score=mastery, revision=0)
    db_session.add(status)
    await db_session.flush()
    return node, status


async def _add_evidence_row(
    db_session,
    *,
    user: User,
    node: KnowledgeNode,
    old: int,
    new: int,
    outcome_id: str,
    observed_at: datetime,
    effect_kind: str = "evidence",
    reason: str = "evidence:task_outcome",
) -> None:
    """按 G-02 吸收器同款编码写证据行（依赖边标记 = oc= 段）。"""
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
            "reason": reason,
            "request_id": request_id,
            "effect_kind": effect_kind,
            "created_at": observed_at,
        },
    )


async def _audit_rows(db_session, node_id) -> list[tuple]:
    result = await db_session.execute(
        text(
            "SELECT old_mastery, new_mastery, reason, request_id, effect_kind "
            "FROM mastery_audit_log WHERE node_id = :node_id ORDER BY id"
        ),
        {"node_id": str(node_id)},
    )
    return list(result.fetchall())


async def _stored_mastery(db_session, user, node) -> float:
    result = await db_session.execute(
        text("SELECT mastery_score FROM user_node_status " "WHERE user_id = :user_id AND node_id = :node_id"),
        {"user_id": str(user.id), "node_id": str(node.id)},
    )
    return float(result.scalar_one())


@pytest.fixture()
async def outbox_tables(db_session):
    await db_session.execute(text(_AUDIT_DDL))
    await db_session.execute(text(_OUTBOX_DDL))
    await db_session.execute(text(_COUNTERS_DDL))
    await db_session.commit()
    return True


# ---------------------------------------------------------------------------
# 验收①：并发旧job不能复活已删内容
# ---------------------------------------------------------------------------


async def test_register_retraction_tombstones_derived_rows(db_session, outbox_tables) -> None:
    """正例：结果撤回登记 ⇒ 依赖证据行持久墓碑 + epoch bump + 事件恰一条。"""
    from app.services.memory_service import MemoryService

    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    assert registration.duplicate is False
    assert registration.tombstoned_rows == 1
    assert registration.affected_node_ids == (str(node.id),)
    assert registration.epoch == 2  # 首次 bump：1 → 2（M-01 懒建语义）

    rows = await _audit_rows(db_session, node.id)
    assert rows[0][4] == "retracted"  # 持久墓碑：effect_kind 词表成员
    assert rows[0][3] is not None  # 行本体保留（audit-without-exposure，不物理删除）

    epoch_after = await MemoryService(db_session).get_memory_epoch(user.id)
    assert epoch_after == 2

    event_rows = (
        await db_session.execute(
            text("SELECT payload FROM event_outbox WHERE event_type = :et AND aggregate_type = :at"),
            {"et": RETRACTION_REGISTERED_EVENT, "at": RETRACTION_AGGREGATE_TYPE},
        )
    ).fetchall()
    assert len(event_rows) == 1
    assert f'"retraction_id":"{registration.retraction_id}"' in str(event_rows[0][0])


async def test_register_retraction_replay_is_idempotent(db_session, outbox_tables) -> None:
    """反例（重复撤回）：同 target 重放 ⇒ duplicate、零新副作用（不双 bump/双事件）。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    first = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    second = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    assert second.duplicate is True
    assert second.retraction_id == first.retraction_id
    assert second.epoch == first.epoch  # 不双 bump
    assert second.tombstoned_rows == 0  # 墓碑幂等（已是 retracted，条件更新零行）

    event_count = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM event_outbox WHERE event_type = :et"),
            {"et": RETRACTION_REGISTERED_EVENT},
        )
    ).scalar_one()
    assert event_count == 1


async def test_stale_job_with_old_epoch_cannot_publish(db_session, outbox_tables) -> None:
    """验收①红转绿：撤回后 epoch 前进，携旧 base_epoch 的 job ⇒ 丢弃，分数不动。"""
    user = await _make_user(db_session)
    node, status_row = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )

    # 并发旧 job：它开始时看到的世代是 1（撤回 bump 之前的世界）。
    results = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch - 1
    )
    assert len(results) == 1
    assert results[0].outcome == "discard_stale_epoch"
    assert await _stored_mastery(db_session, user, node) == 42.0  # 旧结果没有写回
    assert status_row.revision == 0  # 逻辑时钟未动


async def test_replay_after_tombstone_excludes_retracted_evidence(db_session, outbox_tables) -> None:
    """持久墓碑防御纵深：直呼 G-01 重放（完全不知晓撤回的旧路径）也拿不回效果。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    stats = GalaxyStatsService(db_session)
    before = await stats._load_prior_belief(user.id, node.id, 42.0)
    assert before.mean > 20.0  # 撤回前：证据有效

    service = RetractionRecomputeService(db_session)
    await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    after = await stats._load_prior_belief(user.id, node.id, 42.0)
    assert after.mean == 20.0  # 回落到冻结基线，不是 42（不复活）


async def test_invalid_kind_target_combination_rejected(db_session, outbox_tables) -> None:
    """反例：材料删除/推断撤回不是本服务执行体；结果撤回只收 outcome 目标。"""
    user = await _make_user(db_session)
    service = RetractionRecomputeService(db_session)
    with pytest.raises(RetractionRecomputeError):
        await service.register_retraction(
            user_id=user.id, kind="material_deleted", target_type="outcome", target_id="outc_x"
        )
    with pytest.raises(RetractionRecomputeError):
        await service.register_retraction(
            user_id=user.id, kind="result_retracted", target_type="memory_record", target_id=str(uuid4())
        )


# ---------------------------------------------------------------------------
# 验收②：非线性状态按有效事件回放而非减旧分数
# ---------------------------------------------------------------------------


async def test_recompute_equals_authoritative_replay_of_valid_events(db_session, outbox_tables) -> None:
    """正例：撤回 E1 后重算 = G-01 权威对仍有效事件的回放值（精确相等）。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=55.0)
    outcome_a = f"outc_{uuid4().hex}"
    outcome_b = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=40, outcome_id=outcome_a, observed_at=_T0)
    await _add_evidence_row(
        db_session, user=user, node=node, old=40, new=55, outcome_id=outcome_b, observed_at=_T0.replace(day=20)
    )
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_a
    )
    results = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_a], base_epoch=registration.epoch
    )
    assert results[0].outcome == "recomputed"

    # 权威回放值：仍有效事件（E2）从冻结锚（被撤回行的 old_mastery=20）前向融合。
    from app.services.galaxy.mastery_evidence import (
        EvidenceHistoryEntry,
        MasteryEvidenceType,
        recompute_evidence_state,
    )

    expected = recompute_evidence_state(
        20.0,
        [
            EvidenceHistoryEntry(
                evidence_type=MasteryEvidenceType.TASK_OUTCOME,
                value=55.0,
                confidence=0.9,
                observed_at=_T0.replace(day=20),
            )
        ],
    )
    stored = await _stored_mastery(db_session, user, node)
    assert stored == pytest.approx(expected.mean)
    assert stored != 55.0  # 不等于「没撤回的样子」
    # 不是「存储值减旧行分差」：55 - (55-40) = 40 ≠ 回放值
    assert stored != 40.0

    # trace 行：projection（重放跳过，重算动作本身不是证据）
    rows = await _audit_rows(db_session, node.id)
    assert rows[-1][2] == RECOMPUTE_TRACE_REASON
    assert rows[-1][4] == MasteryEffectKind.PROJECTION.value


async def test_recompute_replay_is_idempotent(db_session, outbox_tables) -> None:
    """重算重放：第二次跑同结果（账本纯函数），revision 不再推进。"""
    user = await _make_user(db_session)
    node, status_row = await _make_node_with_status(db_session, user, mastery=55.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=55, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    first = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch
    )
    second = await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch
    )
    assert first[0].new_mastery == second[0].new_mastery
    assert status_row.revision == 1  # 第一次 +1，重放不再推进


async def test_legitimate_other_source_is_preserved(db_session, outbox_tables) -> None:
    """反例（连坐）：吸收了其他合法 outcome 的节点/行不受撤回波及。"""
    user = await _make_user(db_session)
    node_a, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    node_b, _ = await _make_node_with_status(db_session, user, mastery=50.0)
    retracted_outcome = f"outc_{uuid4().hex}"
    other_outcome = f"outc_{uuid4().hex}"
    await _add_evidence_row(
        db_session, user=user, node=node_a, old=20, new=42, outcome_id=retracted_outcome, observed_at=_T0
    )
    await _add_evidence_row(
        db_session, user=user, node=node_b, old=30, new=50, outcome_id=other_outcome, observed_at=_T0
    )
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=retracted_outcome
    )
    assert registration.affected_node_ids == (str(node_a.id),)  # 依赖索引只命中 node_a

    await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[retracted_outcome], base_epoch=registration.epoch
    )
    rows_b = await _audit_rows(db_session, node_b.id)
    assert rows_b[0][4] == "evidence"  # 合法其他来源的行不被墓碑
    assert await _stored_mastery(db_session, user, node_b) == 50.0  # 不被动


# ---------------------------------------------------------------------------
# 验收③：重算中UI与工具均标过期，不继续旧建议
# ---------------------------------------------------------------------------


async def test_read_state_pending_marks_stale_and_blocks_suggestions(db_session, outbox_tables) -> None:
    """验收③红转绿：登记后未重算 ⇒ stale + suggestions_allowed=False（同门两出口）。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    before = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert before.stale is False and before.suggestions_allowed is True  # 撤回前新鲜

    await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    pending = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert pending.stale is True
    assert pending.suggestions_allowed is False  # 工具不继续旧建议
    assert pending.ui_marker == "stale_recomputing"  # UI 标过期


async def test_read_state_after_recompute_serves_fresh(db_session, outbox_tables) -> None:
    """重算完成 ⇒ 读门转新鲜（过期标记解除，建议恢复）。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=55.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=55, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    await service.recompute_capability_nodes(user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch)
    fresh = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert fresh.stale is False
    assert fresh.suggestions_allowed is True
    assert fresh.ui_marker is None


async def test_discarded_gate_keeps_pending_stale_state(db_session, outbox_tables) -> None:
    """栅栏丢弃后重算未发生 ⇒ 过期状态保持（不静默恢复新鲜）。"""
    user = await _make_user(db_session)
    node, _ = await _make_node_with_status(db_session, user, mastery=42.0)
    outcome_id = f"outc_{uuid4().hex}"
    await _add_evidence_row(db_session, user=user, node=node, old=20, new=42, outcome_id=outcome_id, observed_at=_T0)
    await db_session.commit()

    service = RetractionRecomputeService(db_session)
    registration = await service.register_retraction(
        user_id=user.id, kind="result_retracted", target_type="outcome", target_id=outcome_id
    )
    await service.recompute_capability_nodes(
        user_id=user.id, outcome_ids=[outcome_id], base_epoch=registration.epoch - 1
    )  # 旧 epoch job：丢弃
    still_pending = await service.capability_node_read_state(user_id=user.id, node_id=node.id)
    assert still_pending.stale is True and still_pending.suggestions_allowed is False
    assert await _stored_mastery(db_session, user, node) == 42.0
