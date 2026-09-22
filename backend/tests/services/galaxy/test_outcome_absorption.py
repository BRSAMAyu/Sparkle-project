"""G-02 · Outcome → Galaxy 吸收验收（真实 DB，零 LLM，零 mock 业务行为）.

卡面 acceptance 逐条红测：
- **GJ05**（Human action → evidence → Galaxy）：任务完成 outcome 真实吸收进
  图谱节点（G-01 证据融合点亮，非 legacy 时长），且不与完成管线回声双计
  （study_count 不动、同因 receipt 不二次融合）；
- **GJ08**（Correction → memory scope → adaptation 同款可解释性要求 / 卡面
  「图谱变化可解释且可追 source」）：每次图谱变化在
  ``learning_path_snapshot.graph_event_sources`` 留行，reference_id = outcome
  id（与 X-08 账本 ``derive_outcome_id`` 同源），payload 携带 source_ref /
  outcome_key，可追到账本条目；
- **不重复点亮（幂等）**：同 outcome 重放、同因 receipt 重放，mastery 不变、
  evidence 行唯一（append-only mastery_audit_log 标记门）；
- **失败/撤销正确处理**：NEGATIVE 永不点亮（零 evidence 行）+ 弱点标记；
  NEUTRAL 只留溯源；同 id 极性翻转（结构上不可达，防御性）记录纠正、不降级。

传输层说明：Redis 总线为外部设施，消费者路由测试用真实 DB + 真实吸收逻辑，
仅 session_factory 为薄包装（被测行为 = 路由与吸收，全部真实）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.services.galaxy.outcome_absorption_service import (
    ABSORBED_OUTCOMES_SNAPSHOT_KEY,
    OUTCOME_EVIDENCE_AUDIT_REASON,
    GalaxyOutcomeAbsorber,
    OutcomeAbsorptionConsumer,
    _evidence_request_id,
)
from app.services.outcome_capture_service import (
    build_outcome_recorded_payload,
    build_run_receipt_outcome,
    build_task_outcome_capture,
)
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures（与 test_galaxy_contribution_stats 同款 SQLite DDL）
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
async def absorber_env(db_session):
    await _ensure_mastery_audit_log(db_session)
    user = await _make_user(db_session)
    node = KnowledgeNode(name="贝叶斯定理", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return db_session, user, node


async def _make_task(db, user, node=None, *, status=TaskStatus.COMPLETED, title="G-02 任务"):
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import TaskType

    task = Task(
        id=uuid4(),
        user_id=user.id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=status,
        completed_at=_naive_now() if status == TaskStatus.COMPLETED else None,
        knowledge_node_id=node.id if node is not None else None,
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


def _naive_now():
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(tzinfo=None)


def _task_payload(task) -> dict:
    """Real X-08 producer: terminal task → content-free outcome.recorded payload."""
    capture = build_task_outcome_capture(task)
    return build_outcome_recorded_payload(capture)


def _receipt_payload(run_status: str, task) -> dict:
    """Real X-08 producer: terminal run receipt → payload (NEUTRAL/POSITIVE/NEGATIVE)."""
    run = SimpleNamespace(
        id=uuid4(),
        task_id=task.id,
        user_id=task.user_id,
        status=run_status,
        completed_at=_naive_now(),
        created_at=_naive_now(),
    )
    return build_outcome_recorded_payload(build_run_receipt_outcome(run))


async def _audit_rows(db, user_id, node_id, reason=OUTCOME_EVIDENCE_AUDIT_REASON):
    result = await db.execute(
        text(
            "SELECT reason, request_id FROM mastery_audit_log "
            "WHERE user_id = :user_id AND node_id = :node_id AND reason = :reason"
        ),
        {"user_id": str(user_id), "node_id": str(node_id), "reason": reason},
    )
    return list(result.fetchall())


async def _status(db, user_id, node_id) -> UserNodeStatus:
    return await db.get(UserNodeStatus, (user_id, node_id))


def _provenance_entries(status_row) -> list[dict]:
    snapshot = status_row.learning_path_snapshot or {}
    return [e for e in snapshot.get("graph_event_sources") or [] if e.get("event_type") == "outcome.recorded"]


# ---------------------------------------------------------------------------
# GJ05：完成 outcome 真实点亮（证据融合）且不双计
# ---------------------------------------------------------------------------


async def test_gj05_positive_outcome_lights_node_via_evidence_fusion(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    payload = _task_payload(task)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(payload)

    assert result is not None and result.action == "lit"
    status = await _status(db, user.id, node.id)
    # 证据融合数值钉死：fresh prior(0, var=.25) + task_outcome(60, conf=.8, w=.6)
    # → gain=0.5 → posterior=30.0。legacy 时长路径给 0，30 即证明走的是证据面。
    assert status.mastery_score == pytest.approx(30.0)
    assert status.is_unlocked is True
    # 不双计：吸收不是学习会话（完成管线的 study_record 回声由 spark_node 负责）
    assert status.study_count == 0
    # evidence 行 = 点亮硬门（reason 可回放为 task_outcome 证据；标记可逆解析）
    rows = await _audit_rows(db, user.id, node.id)
    assert len(rows) == 1
    expected_marker = _evidence_request_id(60.0, 0.8, payload["outcome_id"], str(task.id))
    assert rows[0][1] == expected_marker, "request_id 必须内嵌 outcome 幂等标记"
    assert len(expected_marker) <= 100, "VARCHAR(100) 列宽约束"


async def test_gj08_graph_change_traceable_to_outcome_source(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    payload = _task_payload(task)

    await GalaxyOutcomeAbsorber(db).absorb_outcome(payload)

    status = await _status(db, user.id, node.id)
    entries = _provenance_entries(status)
    assert entries, "图谱变化必须留下可解释溯源行"
    entry = entries[0]
    assert entry["reference_id"] == payload["outcome_id"], "溯源必须追到账本同源 outcome id"
    assert entry["source_type"] == "outcome_ledger"
    assert entry["label"] == "positive"
    assert entry["payload"]["source_ref"] == f"task://{task.id}"
    assert entry["payload"]["outcome_key"] == payload["outcome_key"]
    # 吸收标记同链可对账
    markers = status.learning_path_snapshot[ABSORBED_OUTCOMES_SNAPSHOT_KEY]
    assert payload["outcome_id"] in markers


# ---------------------------------------------------------------------------
# 幂等：同 outcome 重放 / 同因 receipt 不重复点亮
# ---------------------------------------------------------------------------


async def test_replay_same_outcome_does_not_double_light(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    payload = _task_payload(task)
    absorber = GalaxyOutcomeAbsorber(db)

    first = await absorber.absorb_outcome(dict(payload))
    mastery_after_first = (await _status(db, user.id, node.id)).mastery_score
    second = await absorber.absorb_outcome(dict(payload))
    status = await _status(db, user.id, node.id)

    assert first.action == "lit" and second.action == "duplicate"
    assert status.mastery_score == pytest.approx(mastery_after_first), "重放不得二次点亮"
    assert len(await _audit_rows(db, user.id, node.id)) == 1, "evidence 行必须唯一"
    assert len(_provenance_entries(status)) == 1, "溯源条目去重"


async def test_same_task_receipt_outcome_does_not_double_fuse(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    absorber = GalaxyOutcomeAbsorber(db)

    await absorber.absorb_outcome(_task_payload(task))
    mastery_after_task = (await _status(db, user.id, node.id)).mastery_score

    # 同一任务的 SUCCEEDED run receipt：另一 outcome id、同 correlation_task_id
    receipt = _receipt_payload("SUCCEEDED", task)
    assert receipt["outcome_id"] != _task_payload(task)["outcome_id"]
    result = await absorber.absorb_outcome(receipt)
    status = await _status(db, user.id, node.id)

    assert result.action == "duplicate", "同因 receipt 只补溯源，不二次融合"
    assert status.mastery_score == pytest.approx(mastery_after_task), "同因合并不双计"
    assert len(await _audit_rows(db, user.id, node.id)) == 1
    refs = {e["reference_id"] for e in _provenance_entries(status)}
    assert receipt["outcome_id"] in refs, "receipt 面仍可追溯"


async def test_distinct_task_outcomes_each_fuse(absorber_env):
    db, user, node = absorber_env
    task_a = await _make_task(db, user, node, title="任务A")
    task_b = await _make_task(db, user, node, title="任务B")
    absorber = GalaxyOutcomeAbsorber(db)

    await absorber.absorb_outcome(_task_payload(task_a))
    mastery_a = (await _status(db, user.id, node.id)).mastery_score
    await absorber.absorb_outcome(_task_payload(task_b))
    mastery_b = (await _status(db, user.id, node.id)).mastery_score

    assert mastery_b > mastery_a, "不同任务的真实成果各自计一次（第二次融合必增）"
    assert len(await _audit_rows(db, user.id, node.id)) == 2


# ---------------------------------------------------------------------------
# 失败/撤销：NEGATIVE 永不点亮、NEUTRAL 只记录、极性翻转防御
# ---------------------------------------------------------------------------


async def test_negative_outcome_never_lights_and_flags_weak(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node, status=TaskStatus.ABANDONED)
    payload = _task_payload(task)
    assert payload["polarity"] == "negative"
    absorber = GalaxyOutcomeAbsorber(db)

    result = await absorber.absorb_outcome(payload)
    status = await _status(db, user.id, node.id)

    assert result.action == "flagged"
    assert status.mastery_score == 0.0, "失败 outcome 不得点亮"
    assert await _audit_rows(db, user.id, node.id) == [], "失败不得写掌握度证据行"
    assert "signal:weak_at" in (node.keywords or []), "失败必须标记弱点供 review"
    assert len(_provenance_entries(status)) == 1, "失败保留为可查询溯源（不静默丢弃）"

    # 重放幂等：仍不点亮、不重复标记
    await absorber.absorb_outcome(dict(payload))
    assert (await _status(db, user.id, node.id)).mastery_score == 0.0
    assert len(_provenance_entries(await _status(db, user.id, node.id))) == 1


async def test_neutral_outcome_recorded_only(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    payload = _receipt_payload("PARTIAL", task)
    assert payload["polarity"] == "neutral"

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(payload)
    status = await _status(db, user.id, node.id)

    assert result.action == "recorded_only"
    assert status.mastery_score == 0.0, "partial receipt 不点亮（消费侧 P2：结构性不进任何点亮面）"
    assert await _audit_rows(db, user.id, node.id) == []
    assert "signal:weak_at" not in (node.keywords or []), "neutral 不标弱点"
    assert len(_provenance_entries(status)) == 1, "partial 保留可查询、可审计"


async def test_negative_after_positive_flips_never_demote_never_relight(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    absorber = GalaxyOutcomeAbsorber(db)

    await absorber.absorb_outcome(_task_payload(task))
    mastery_lit = (await _status(db, user.id, node.id)).mastery_score
    assert mastery_lit > 0

    # 同 outcome id 翻转为 NEGATIVE（FSM 吸收态下结构不可达；消费侧防御）
    payload = _task_payload(task)
    flipped = {**payload, "polarity": "negative"}
    result = await absorber.absorb_outcome(flipped)
    status = await _status(db, user.id, node.id)

    assert result.action == "corrected"
    assert status.mastery_score == pytest.approx(mastery_lit), "翻转不得降级已吸收证据"
    assert len(await _audit_rows(db, user.id, node.id)) == 1, "翻转不得二次写证据行"


# ---------------------------------------------------------------------------
# 节点解析：确定性链 + 无目标防御
# ---------------------------------------------------------------------------


async def test_node_resolution_falls_back_to_task_link(absorber_env):
    db, user, node = absorber_env
    from app.models.task_resources import TaskKnowledgeLink

    task = await _make_task(db, user, node=None)  # 任务无直接节点
    db.add(TaskKnowledgeLink(task_id=task.id, knowledge_node_id=node.id, relation_type="prerequisite"))
    await db.commit()

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))

    assert result.action == "lit"
    assert result.node_ids == [str(node.id)]
    status = await _status(db, user.id, node.id)
    assert status.mastery_score == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# P1-5：DF-5 标题锚第 4 环——无显式关联的完成任务也必须点亮同一颗星
# ---------------------------------------------------------------------------


async def test_task_without_links_lights_exact_title_matched_star(absorber_env):
    """无 knowledge_node_id / 无 TaskKnowledgeLink 时，标题精确命中既有节点.

    生产断环复现：northstar 完成任务 outcome.recorded 只有 correlation_task_id，
    旧解析链拿不到节点 → no_target → mastery 恒 0。第 4 环 = DF-5 同源标题锚：
    完成管线 spark 与 outcome 吸收必须落在**同一颗星**（exact-title 命中）。
    """
    db, user, node = absorber_env
    task = await _make_task(db, user, node=None, title="贝叶斯定理")  # 与既有节点同名

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))

    assert result.action == "lit", "无显式关联的完成任务必须经标题锚点亮，不得 no_target"
    assert result.node_ids == [str(node.id)], "必须命中既有同名节点，而非复制新节点"
    status = await _status(db, user.id, node.id)
    assert status.mastery_score == pytest.approx(30.0), "证据融合数值（fresh prior + task_outcome）"
    assert status.is_unlocked is True
    assert len(await _audit_rows(db, user.id, node.id)) == 1


async def test_task_without_links_ignites_deterministic_task_star(absorber_env):
    """标题无命中时物化 uuid5 确定性任务星并点亮（与 ensure_task_node 同一 id）.

    与完成管线 daily-flow DF-5 同源：GalaxyService.task_node_uuid(normalized
    title) ——同一任务重放/多事件面（完成 outcome + receipt）锚定同一颗星。
    """
    db, user, node = absorber_env
    title = "离子交换色谱入门 P1-5"
    task = await _make_task(db, user, node=None, title=title)
    from app.services.galaxy_service import GalaxyService

    expected_anchor = GalaxyService.task_node_uuid(title)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))

    assert result.action == "lit"
    assert result.node_ids == [str(expected_anchor)], "必须落在确定性 uuid5 任务星上"
    anchor = await db.get(KnowledgeNode, expected_anchor)
    assert anchor is not None and anchor.source_task_id == task.id
    status = await _status(db, user.id, expected_anchor)
    assert status.mastery_score == pytest.approx(30.0)
    assert status.is_unlocked is True

    # 同任务 receipt 面重放：同因合并，不二次融合（tk= 标记语义跨第 4 环成立）
    receipt = _receipt_payload("SUCCEEDED", task)
    second = await GalaxyOutcomeAbsorber(db).absorb_outcome(receipt)
    assert second.action == "duplicate"
    assert (await _status(db, user.id, expected_anchor)).mastery_score == pytest.approx(30.0)


async def test_no_correlation_means_no_target(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node=None)

    payload = _task_payload(task)
    stripped = {k: v for k, v in payload.items() if k != "correlation_node_id"}
    # build_task_outcome_capture 会带 correlation_task_id；去掉它即无任何解析链
    stripped.pop("correlation_task_id", None)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(stripped)

    assert result.action == "no_target"
    statuses = (await db.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user.id))).scalars().all()
    assert statuses == [], "无目标时不得凭空创建节点状态"


async def test_stale_node_reference_is_skipped(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    payload = _task_payload(task)
    payload["correlation_node_id"] = str(uuid4())  # 不存在的节点引用

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(payload)

    assert result.action == "no_target"
    assert await _status(db, user.id, node.id) is None, "悬挂引用不得点亮其他节点"


# ---------------------------------------------------------------------------
# 消费者路由（传输层薄包装；吸收行为走真实 DB）
# ---------------------------------------------------------------------------


class _SessionFactory:
    """把 db_session 包成 async context manager 的薄工厂（仅传输层包装）。"""

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return _SessionCtx(self._session)


class _SessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


async def test_consumer_routes_only_outcome_recorded_events(absorber_env):
    db, user, node = absorber_env
    task = await _make_task(db, user, node)
    consumer = OutcomeAbsorptionConsumer(session_factory=_SessionFactory(db), event_bus=None)

    # 非 outcome 事件：忽略（不建 status、不动节点）
    await consumer._on_event({"event_type": "task.completed", "task_id": str(task.id)})
    assert await _status(db, user.id, node.id) is None

    # outcome.recorded：真实吸收
    await consumer._on_event(_task_payload(task))
    status = await _status(db, user.id, node.id)
    assert status is not None
    assert status.mastery_score == pytest.approx(30.0)
