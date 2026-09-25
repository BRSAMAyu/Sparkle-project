"""卡 S-04 · Community Artifact Feedback → Outcome/Evidence —— headless 验收测试.

承接 S-03 已合入的第 4 入径（share → peer feedback → 主人 adopt →
Goal.community_evidence 回执），本卡在其上加两块**结构化**（不重建真源）：

1. **outcome evidence 结构化**：采纳不再只写 Goal.metadata JSON 回执 +
   best-effort Redis 信念面（无 Redis 时结构性降级为 0 —— 断头路），而是
   落一张可查询的结构化证据表 ``community_outcome_evidence``（学习飞轮
   数据面），goal_id/feedback_id/shared_resource_id 全真实外键。
2. **flywheel 事件**：采纳产生 ``community.feedback_adopted`` 事件写入
   ``event_outbox``（D-01 V3 envelope，参照 D-05 lifecycle 事件形状），
   下游可消费；事件词表按 D-01 扩词表流程登记（S-04 扩展，hash 显式重冻结）。

卡魂负向测试（与 wt377 S-03 同型，不得弱化）：
- feedback / adopt **永不**自动改 Goal.mastery / Goal.progress；
- 未采纳零影响：无证据行、无 outbox 行、Goal 轨迹无 community_evidence 键。
- 撤回传播到结构化证据行（status=retracted，派生引用更新不静默消失）。

现状定性（诚实标注）：
- 分享关联 Goal/Action（真实外键而非自由文本）、反馈不自动成为 mastery、
  显式采纳端点、S-03 回执链 —— **S-03/S-01 已建齐，基线即绿（契约锁）**；
- 结构化证据表 + flywheel outbox 事件 —— **本卡真红面**（base 上
  ImportError/缺表失败，修后绿）。

DATABASE_URL 口径：sqlite+aiosqlite:///:memory:（conftest 统一注入）。
event_outbox / event_sequence_counters 无 ORM 模型（真源在迁移 5f2b9b3c0e6f），
测试内按 M-07 先例建最小 sqlite 表（列对齐该迁移）。
"""

from __future__ import annotations

import json
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.community import SharedResource, SharedResourceFeedback
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.schemas.community import FeedbackVerdict

COMMUNITY_PREFIX = "/api/v1/community"
SQUAD_PREFIX = f"{COMMUNITY_PREFIX}/squads"

FLYWHEEL_EVENT = "community.feedback_adopted"


# ---------------------------------------------------------------------------
# 工具（与 S-03 验收文件同构的最小造数/夹具）
# ---------------------------------------------------------------------------
async def _make_user(db: AsyncSession, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{prefix}_{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


def _squad_payload(name: str) -> dict:
    return {
        "name": name,
        "deadline": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
        "max_members": 4,
        "sprint_goal": "期末周冲完计网",
    }


async def _owner_goal_plan_task(db: AsyncSession, owner: User) -> tuple[Goal, Plan, Task]:
    """真源造数：Goal → Plan（双向外链）→ Task（plan_id 挂链）。"""
    goal = Goal(user_id=owner.id, title="S-04 目标：完成作品集", status="active", mastery=0.2, progress=0.1)
    db.add(goal)
    await db.flush()
    plan = Plan(user_id=owner.id, goal_id=goal.id, name="作品集计划", type=PlanType.SPRINT)
    db.add(plan)
    await db.flush()
    goal.plan_id = plan.id
    db.add(goal)
    await db.flush()
    task = Task(
        user_id=owner.id,
        plan_id=plan.id,
        title="作品集第一章",
        type=TaskType.LEARNING,
        estimated_minutes=45,
        status=TaskStatus.COMPLETED,
    )
    db.add(task)
    await db.flush()
    return goal, plan, task


# event_outbox / event_sequence_counters 最小 sqlite 表（对齐 5f2b9b3c0e6f 迁移列；
# M-07 先例——生产 PG 由迁移建表，测试 sqlite 由本夹具补齐）。
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


@pytest.fixture(name="flywheel_app")
async def flywheel_app_fixture(db_session: AsyncSession):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()

    from app.api.v1.community import router as community_router
    from app.api.v1.community_squad import router as squad_router

    app = FastAPI()
    app.include_router(community_router, prefix=COMMUNITY_PREFIX)
    app.include_router(squad_router, prefix=COMMUNITY_PREFIX)

    current = {"user": None}

    async def _override_get_db():
        yield db_session

    async def _override_get_current_user():
        return current["user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    import app.api.v1.community as community_api

    async def _no_op_streak(_user_id: UUID) -> None:
        return None

    community_api._refresh_streak_signals = _no_op_streak  # type: ignore[method-assign]

    yield app, current

    app.dependency_overrides.clear()


async def _walk_to_feedback(db: AsyncSession, app: FastAPI, current: dict) -> tuple[User, User, Goal, str, str]:
    """走链：小队 + Goal/Plan/Task 真源 + share + peer 反馈；返回句柄。"""
    owner = await _make_user(db, "s04_owner")
    mate = await _make_user(db, "s04_mate")
    goal, _plan, _task = await _owner_goal_plan_task(db, owner)
    await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        current["user"] = owner
        squad = await ac.post(SQUAD_PREFIX, json=_squad_payload("S-04 飞轮小队"))
        assert squad.status_code == 201, squad.text
        squad_id = squad.json()["id"]

        current["user"] = mate
        assert (await ac.post(f"{SQUAD_PREFIX}/{squad_id}/join")).status_code == 200

        current["user"] = owner
        task_row = (
            await db.execute(select(Task).where(Task.user_id == owner.id, Task.title == "作品集第一章"))
        ).scalar_one()
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task_row.id),
                "target_group_id": squad_id,
                "permission": "view",
                "comment": "求伙伴看看这个产出",
            },
        )
        assert share.status_code == 200, share.text
        shared_resource_id = share.json()["id"]

        current["user"] = mate
        fb = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value, "comment": "第一章结构很清楚"},
        )
        assert fb.status_code == 201, fb.text
        feedback_id = fb.json()["id"]

    return owner, mate, goal, shared_resource_id, feedback_id


async def _outbox_rows(db: AsyncSession, event_type: str) -> list[dict]:
    result = await db.execute(
        text(
            "SELECT aggregate_type, aggregate_id, event_type, sequence_number, payload, metadata "
            "FROM event_outbox WHERE event_type = :t"
        ),
        {"t": event_type},
    )
    return [dict(row._mapping) for row in result.all()]


# ---------------------------------------------------------------------------
# 1. 采纳 → 结构化 outcome evidence 落库 + flywheel 事件（本卡真红面）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_adopt_writes_structured_outcome_evidence_and_flywheel_event(db_session: AsyncSession, flywheel_app):
    from app.core.event_registry import EVENT_REGISTRY, EventStage, read_event_metadata
    from app.models.community import CommunityOutcomeEvidence

    app, current = flywheel_app
    owner, _mate, goal, shared_resource_id, feedback_id = await _walk_to_feedback(db_session, app, current)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        current["user"] = owner
        adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert adopt.status_code == 200, adopt.text
        assert adopt.json()["success"] is True
        await db_session.commit()

    # ── 结构化证据行：全真实外键、可查询、状态机字段齐 ──
    evidence_rows = (
        (
            await db_session.execute(
                select(CommunityOutcomeEvidence).where(CommunityOutcomeEvidence.feedback_id == UUID(feedback_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(evidence_rows) == 1, f"expected 1 structured evidence row, got {len(evidence_rows)}"
    ev = evidence_rows[0]
    assert str(ev.goal_id) == str(goal.id)
    assert str(ev.shared_resource_id) == str(shared_resource_id)
    assert str(ev.owner_id) == str(owner.id)
    assert ev.verdict == FeedbackVerdict.HELPFUL.value
    assert ev.status == "adopted"
    assert ev.adopted_at is not None
    assert ev.retracted_at is None

    # goal 行真实存在（证据落库挂的是真 Goal，不是自由文本）
    assert await db_session.get(Goal, ev.goal_id) is not None

    # ── S-03 回执链不弱化：Goal.community_evidence 回执仍在 ──
    await db_session.refresh(goal)
    receipts = (goal.metadata_payload or {}).get("community_evidence") or []
    assert any(
        r.get("feedback_id") == str(feedback_id) and r.get("verdict") == "helpful" for r in receipts
    ), f"goal receipt missing: {goal.metadata_payload}"

    # ── flywheel 事件：event_outbox 一行、D-01 V3 envelope、下游可消费 ──
    rows = await _outbox_rows(db_session, FLYWHEEL_EVENT)
    assert len(rows) == 1, f"expected exactly 1 {FLYWHEEL_EVENT} outbox row, got {len(rows)}"
    row = rows[0]
    assert row["aggregate_type"] == "community_outcome_evidence"
    assert row["aggregate_id"] == str(ev.id)

    envelope = read_event_metadata(row["metadata"])
    assert envelope.is_v3_envelope, f"not a V3 envelope: {row['metadata']}"
    assert envelope.schema_version == "event.v1"
    assert envelope.user_id == str(owner.id)
    assert envelope.source == "server_service"
    assert envelope.service == "community_feedback_service"
    assert envelope.occurred_at is not None
    assert (envelope.event_id or "").startswith("evt_")

    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    assert payload["feedback_id"] == str(feedback_id)
    assert payload["goal_id"] == str(goal.id)
    assert payload["shared_resource_id"] == str(shared_resource_id)
    assert payload["evidence_id"] == str(ev.id)
    assert payload["verdict"] == FeedbackVerdict.HELPFUL.value
    # 内容纪律（M-07 同款）：payload 只含 ids/词表值，不落反馈评论与用户内容
    assert "comment" not in payload
    assert "第一章结构很清楚" not in json.dumps(payload, ensure_ascii=False)

    # ── 词表：S-04 扩展按 D-01 流程登记为 live ──
    entry = EVENT_REGISTRY[FLYWHEEL_EVENT]
    assert entry.status == "live"
    assert entry.stage is EventStage.OUTCOME
    assert entry.producers == ("app/services/community_feedback_service.py",)

    # ── 卡魂负向钉死：采纳不改 mastery/progress ──
    await db_session.refresh(goal)
    assert goal.mastery == 0.2
    assert goal.progress == 0.1

    # ── 幂等：重复采纳不重复落证据行/事件行 ──
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        current["user"] = owner
        re_adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert re_adopt.status_code == 200
        assert re_adopt.json()["success"] is True
    await db_session.commit()
    evidence_count = (
        (
            await db_session.execute(
                select(CommunityOutcomeEvidence).where(CommunityOutcomeEvidence.feedback_id == UUID(feedback_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(evidence_count) == 1
    assert len(await _outbox_rows(db_session, FLYWHEEL_EVENT)) == 1


# ---------------------------------------------------------------------------
# 2. 未采纳零影响（负向，双向断言的另一半）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unadopted_feedback_has_zero_structured_impact(db_session: AsyncSession, flywheel_app):
    from app.models.community import CommunityOutcomeEvidence

    app, current = flywheel_app
    owner, _mate, goal, shared_resource_id, feedback_id = await _walk_to_feedback(db_session, app, current)

    # 反馈已存在、采纳未发生
    feedback = (
        await db_session.execute(select(SharedResourceFeedback).where(SharedResourceFeedback.id == UUID(feedback_id)))
    ).scalar_one()
    assert feedback.adopted_at is None
    assert feedback.adopted_into_goal_id is None

    assert (
        (await db_session.execute(select(CommunityOutcomeEvidence))).scalars().all()
    ) == [], "未采纳不得产生结构化证据行"
    assert await _outbox_rows(db_session, FLYWHEEL_EVENT) == [], "未采纳不得产生 flywheel 事件"

    await db_session.refresh(goal)
    assert (goal.metadata_payload or {}).get("community_evidence") is None, "未采纳不得写 Goal 轨迹回执"
    # 卡魂：反馈本身零 mastery 影响
    assert goal.mastery == 0.2
    assert goal.progress == 0.1


# ---------------------------------------------------------------------------
# 3. 撤回传播到结构化证据（派生引用更新，不静默消失）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retract_propagates_to_structured_evidence_and_receipt(db_session: AsyncSession, flywheel_app):
    from app.models.community import CommunityOutcomeEvidence

    app, current = flywheel_app
    owner, _mate, goal, shared_resource_id, feedback_id = await _walk_to_feedback(db_session, app, current)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        current["user"] = owner
        adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert adopt.status_code == 200, adopt.text

        retract = await ac.post(f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/retract")
        assert retract.status_code == 200, retract.text
        await db_session.commit()

    ev = (
        await db_session.execute(
            select(CommunityOutcomeEvidence).where(CommunityOutcomeEvidence.feedback_id == UUID(feedback_id))
        )
    ).scalar_one()
    assert ev.status == "retracted"
    assert ev.retracted_at is not None
    # 行保留（审计），不是物理抹除
    assert ev.goal_id is not None

    await db_session.refresh(goal)
    receipts = (goal.metadata_payload or {}).get("community_evidence") or []
    assert any(
        r.get("feedback_id") == str(feedback_id) and r.get("status") == "retracted" for r in receipts
    ), f"receipt retraction missing: {goal.metadata_payload}"

    feedback = (
        await db_session.execute(select(SharedResourceFeedback).where(SharedResourceFeedback.id == UUID(feedback_id)))
    ).scalar_one()
    assert feedback.retracted_at is not None

    # 撤回传播也不触碰 mastery/progress
    assert goal.mastery == 0.2
    assert goal.progress == 0.1


# ---------------------------------------------------------------------------
# 4. 契约锁（S-03/S-01 已建齐，基线即绿——如实标注）：
#    分享关联真实行而非自由文本；不可解析目标时采纳显式 400
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_share_links_real_rows_and_adopt_without_goal_is_rejected(db_session: AsyncSession, flywheel_app):
    app, current = flywheel_app
    owner = await _make_user(db_session, "s04_lock_owner")
    await db_session.commit()
    current["user"] = owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        squad = await ac.post(SQUAD_PREFIX, json=_squad_payload("S-04 关联锁小队"))
        squad_id = squad.json()["id"]

        # 分享：真实 Task 外键（不是自由文本），落库行可回查
        task = Task(user_id=owner.id, title="无计划任务", type=TaskType.LEARNING, estimated_minutes=10)
        db_session.add(task)
        await db_session.flush()
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task.id),
                "target_group_id": squad_id,
                "permission": "view",
            },
        )
        assert share.status_code == 200, share.text
        shared_resource_id = share.json()["id"]
        await db_session.commit()

        shared_row = await db_session.get(SharedResource, UUID(shared_resource_id))
        assert shared_row is not None and shared_row.task_id == task.id
        assert await db_session.get(Task, shared_row.task_id) is not None

        # 采纳：任务无 plan/goal 链、未显式指定 goal_id → 400（不自由文本造 Goal）

        mate = await _make_user(db_session, "s04_lock_mate")
        current["user"] = mate
        assert (await ac.post(f"{SQUAD_PREFIX}/{squad_id}/join")).status_code == 200
        fb = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value},
        )
        assert fb.status_code == 201
        feedback_id = fb.json()["id"]

        current["user"] = owner
        adopt = await ac.post(f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt")
        assert adopt.status_code == 400, adopt.text
        assert "目标" in adopt.json()["detail"]

        # 显式指定他人 goal → 403/400（归属校验，不跨用户挂证据）
        other_goal = Goal(user_id=mate.id, title="别人的目标", status="active")
        db_session.add(other_goal)
        await db_session.commit()
        adopt2 = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(other_goal.id)},
        )
        assert adopt2.status_code == 400, adopt2.text

        # GJ16 锚点锁：check-in 携带 goal_id 回链真实 Goal 行
        goal = Goal(user_id=owner.id, title="S-04 GJ16 目标", status="active", mastery=0.1, progress=0.0)
        db_session.add(goal)
        await db_session.commit()
        checkin = await ac.post(
            f"{COMMUNITY_PREFIX}/checkin",
            json={
                "group_id": squad_id,
                "today_duration_minutes": 20,
                "message": "打卡",
                "goal_id": str(goal.id),
            },
        )
        assert checkin.status_code == 200, checkin.text
        assert checkin.json()["goal_id"] == str(goal.id)
        assert await db_session.get(Goal, UUID(checkin.json()["goal_id"])) is not None
