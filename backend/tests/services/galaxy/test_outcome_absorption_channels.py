"""V4-D04 · 吸收器能力通道分流（真实 DB；「星图只接有效 outcome」）.

卡面验收逐条红测：
- **只学习计时不显示掌握**：self_reported 完成（纯点击）→ 练习过：解锁+溯源，
  掌握度零变化、零证据行；focus 覆盖支撑的 ACTUAL 完成同为练习通道（时长型
  行为观察 ≠ 能力检验）；独立测验（quiz 物化）→ 独立检验通过：真实融合点亮。
- **Agent产物不计人类能力**：run receipt（SUCCEEDED）单独到达 → 只留溯源，
  不解锁不融合；纯 receipt 升格的 ACTUAL 完成同理 NON_HUMAN。
- 幂等：练习通道重放 → duplicate 零重复溯源。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.services.galaxy.outcome_absorption_service import (
    OUTCOME_EVIDENCE_AUDIT_REASON,
    GalaxyOutcomeAbsorber,
)
from app.services.outcome_capture_service import (
    build_outcome_recorded_payload,
    build_run_receipt_outcome,
    build_task_outcome_capture,
)
from tests.golden.north_star_wvpl_fixture import make_user as _make_user

pytestmark = pytest.mark.asyncio


async def _ensure_mastery_audit_log(db_session) -> None:
    await db_session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS mastery_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                old_mastery INTEGER NOT NULL,
                new_mastery INTEGER NOT NULL,
                reason TEXT,
                request_id TEXT,
                revision INTEGER DEFAULT 1,
                created_at DATETIME NOT NULL,
                effect_kind TEXT
            )
        """
        )
    )
    await db_session.commit()


@pytest_asyncio.fixture()
async def absorber_env(db_session):
    await _ensure_mastery_audit_log(db_session)
    user = await _make_user(db_session)
    node = KnowledgeNode(name=f"通道测试{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return db_session, user, node


def _naive_now():
    return datetime.now(UTC).replace(tzinfo=None)


async def _make_completed_task(db, user, node, *, title: str) -> Task:
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
    from app.models.task import TaskType

    task = Task(
        id=uuid4(),
        user_id=user.id,
        title=title,
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


async def _add_focus_cover(db, user, task, *, minutes: int = 20) -> None:
    """完成前开始的 COMPLETED focus 会话（账本覆盖证据的时间方向约束）。"""
    started = _naive_now() - timedelta(minutes=minutes + 10)
    db.add(
        FocusSession(
            user_id=user.id,
            task_id=task.id,
            start_time=started,
            end_time=started + timedelta(minutes=minutes),
            duration_minutes=minutes,
            status=FocusStatus.COMPLETED,
        )
    )
    await db.commit()


def _task_payload(task) -> dict:
    return build_outcome_recorded_payload(build_task_outcome_capture(task))


def _receipt_payload(run_status: str, task) -> dict:
    run = SimpleNamespace(
        id=uuid4(),
        task_id=task.id,
        user_id=task.user_id,
        status=run_status,
        completed_at=_naive_now(),
        created_at=_naive_now(),
    )
    return build_outcome_recorded_payload(build_run_receipt_outcome(run))


async def _audit_rows(db, user_id, node_id):
    result = await db.execute(
        text(
            "SELECT reason, request_id, effect_kind FROM mastery_audit_log "
            "WHERE user_id = :user_id AND node_id = :node_id"
        ),
        {"user_id": str(user_id), "node_id": str(node_id)},
    )
    return list(result.fetchall())


async def _status(db, user_id, node_id) -> UserNodeStatus | None:
    return await db.get(UserNodeStatus, (user_id, node_id))


# ---------------------------------------------------------------------------
# 独立检验通过（VERIFIED）：quiz 物化 → 真实融合点亮
# ---------------------------------------------------------------------------


async def _add_quiz_pass(db, user, node, task) -> None:
    """独立测验物化面（D-02 quiz_feedback 源：meta source=quiz_passed）。"""
    from app.models.galaxy import ExpansionFeedback

    db.add(
        ExpansionFeedback(
            user_id=user.id,
            trigger_node_id=node.id,
            meta_data={"source": "quiz_passed", "task_id": str(task.id)},
        )
    )
    await db.commit()


async def test_quiz_verified_completion_fuses_and_lights(absorber_env):
    """正例（独立检验通过）：quiz 物化支撑的 ACTUAL 完成 → VERIFIED 融合点亮，
    mastery 真实推进 + 证据账本行（G-02 幂等门标记）落库。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="检验通过的完成")
    await _add_quiz_pass(db, user, node, task)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "lit"
    assert result.capability_channel == "verified"
    status = await _status(db, user.id, node.id)
    assert status.is_unlocked is True
    assert float(status.mastery_score) > 0.0
    rows = await _audit_rows(db, user.id, node.id)
    assert len(rows) == 1
    reason, request_id, effect_kind = rows[0]
    assert reason == OUTCOME_EVIDENCE_AUDIT_REASON
    assert effect_kind == "evidence"
    assert f"oc={result.outcome_id[len('outc_'):]}" in str(request_id).split(";")


async def test_quiz_verified_replay_does_not_double_light(absorber_env):
    """反例（幂等回归）：VERIFIED 点亮后重放 → duplicate，mastery/证据行不翻倍。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="重放的检验完成")
    await _add_quiz_pass(db, user, node, task)

    absorber = GalaxyOutcomeAbsorber(db)
    first = await absorber.absorb_outcome(_task_payload(task))
    assert first.action == "lit"
    mastery_after_first = float((await _status(db, user.id, node.id)).mastery_score)
    second = await absorber.absorb_outcome(_task_payload(task))
    assert second.action == "duplicate"
    status = await _status(db, user.id, node.id)
    assert float(status.mastery_score) == mastery_after_first
    assert len(await _audit_rows(db, user.id, node.id)) == 1


# ---------------------------------------------------------------------------
# 练习过（PRACTICED）：解锁可见、零掌握度效果
# ---------------------------------------------------------------------------


async def test_focus_covered_completion_is_practiced_never_lights(absorber_env):
    """正例+反例（只学习计时不显示掌握）：focus 覆盖把完成升到 ACTUAL（账本
    真相面），但时长型行为观察不是独立检验——通道=练习过：解锁可见、溯源在，
    掌握度零变化、零证据行。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="练习完成（focus 覆盖）")
    await _add_focus_cover(db, user, task, minutes=20)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "practiced"
    assert result.capability_channel == "practiced"
    status = await _status(db, user.id, node.id)
    assert status is not None and status.is_unlocked is True
    assert float(status.mastery_score) == 0.0
    assert await _audit_rows(db, user.id, node.id) == []  # 零证据行


async def test_self_reported_click_completion_is_practiced_never_lights(absorber_env):
    """正例：纯点击完成（无任何验证，self_reported）→ 练习过：解锁+溯源，掌握度零变化。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="点击完成")

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "practiced"
    status = await _status(db, user.id, node.id)
    assert status.is_unlocked is True
    assert float(status.mastery_score) == 0.0
    assert await _audit_rows(db, user.id, node.id) == []
    provenance = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    assert any(e.get("reference_id") == result.outcome_id for e in provenance)


async def test_run_receipt_outcome_alone_never_lights_never_unlocks(absorber_env):
    """反例（Agent产物不计人类能力）：SUCCEEDED receipt 单独到达 → 只留溯源。
    同因 receipt 亦不得借 task 完成行点亮——receipt 事件自身无账本条目、
    无人类独立检验，通道恒 NON_HUMAN。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="Agent 代跑任务")

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_receipt_payload("SUCCEEDED", task))
    assert result.action == "non_human"
    assert result.capability_channel == "non_human"
    status = await _status(db, user.id, node.id)
    assert status is not None
    assert status.is_unlocked is False  # 不解锁
    assert float(status.mastery_score) == 0.0  # 不融合
    assert await _audit_rows(db, user.id, node.id) == []  # 零证据行
    provenance = (status.learning_path_snapshot or {}).get("graph_event_sources") or []
    assert any(e.get("reference_id") == result.outcome_id for e in provenance)  # 溯源在


async def test_practiced_replay_is_duplicate_without_double_provenance(absorber_env):
    """反例（幂等）：练习通道重放 → duplicate，溯源不翻倍。"""
    db, user, node = absorber_env
    task = await _make_completed_task(db, user, node, title="重放的练习")

    absorber = GalaxyOutcomeAbsorber(db)
    first = await absorber.absorb_outcome(_task_payload(task))
    assert first.action == "practiced"
    second = await absorber.absorb_outcome(_task_payload(task))
    assert second.action == "duplicate"

    status = await _status(db, user.id, node.id)
    provenance = list((status.learning_path_snapshot or {}).get("graph_event_sources") or [])
    refs = [e.get("reference_id") for e in provenance]
    assert refs.count(first.outcome_id) == 1
    assert float(status.mastery_score) == 0.0


async def test_negative_outcome_still_flags_weak_and_never_lights(absorber_env):
    """回归面：NEGATIVE 语义不受 D04 影响（弱点标记、零点亮）。"""
    from app.models.task import TaskStatus as _TS

    db, user, node = absorber_env
    from app.models.task import TaskType

    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="放弃的任务",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=_TS.ABANDONED,
        knowledge_node_id=node.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    result = await GalaxyOutcomeAbsorber(db).absorb_outcome(_task_payload(task))
    assert result.action == "flagged"
    status = await _status(db, user.id, node.id)
    assert float(status.mastery_score) == 0.0
    assert await _audit_rows(db, user.id, node.id) == []
