"""GET /api/v1/insights/evidence-cards API 测试（D-07）。

红测先行：证明 base c8b445b5 上洞察面（a）没有证据驱动的 insight 产物，
（b）预测面渲染无定义分数/假精确预测。目标契约（fact→interpretation→
uncertainty→evidence→implication 五要素，三类洞察优先，定性词替代置信
百分比——M-10 口径）在本文件冻结：

- 每张卡恰有 fact / interpretation / uncertainty / evidence / implication
  五要素 + id/kind；
- 全响应无置信百分比/无定义分数族键（confidence/risk_score/score/rate/…）；
- evidence 深链指向应用内可达路由；纠正底层事实后再次读取，卡片随之更新
  （洞察是派生视图，不落陈旧快照）；
- 无数据不生成卡（更不生成人格结论）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.insights import router as insights_router
from app.models.goal import Goal
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


class _FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _build_app(session: AsyncSession, user_id) -> FastAPI:
    app = FastAPI()
    app.include_router(insights_router, prefix="/insights")

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser(user_id)
    return app


async def _make_user(db_session: AsyncSession) -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


_NOW = datetime(2026, 9, 25, 10, 0, 0)


async def _seed_lifecycle_event(
    db_session: AsyncSession,
    user_id,
    *,
    decision_id: str,
    event_type: str,
    friction_tag: str = "execution_friction",
    occurred_at: datetime | None = None,
    outcome_polarity: str | None = None,
    window_hours: int = 72,
) -> None:
    db_session.add(
        InterventionLifecycleEvent(
            user_id=user_id,
            decision_id=decision_id,
            event_type=event_type,
            intervention_type="rescope",
            execution_mode="hybrid",
            goal_type="exam",
            friction_tag=friction_tag,
            outcome_polarity=outcome_polarity,
            outcome_truth_class="actual" if outcome_polarity else None,
            detail={"window_hours": window_hours},
            dedupe_subkey="",
            occurred_at=occurred_at or (_NOW - timedelta(hours=2)),
        )
    )
    await db_session.commit()


async def _seed_goal_with_tasks(
    db_session: AsyncSession, user_id, *, completed: int = 0, total: int = 2
) -> Goal:
    goal = Goal(
        user_id=user_id,
        title="两周内完成线代一轮复习",
        goal_type="exam",
        status="active",
        is_primary=True,
        # 真源读数原样（可能因上游写入链停在 0，R2-A 跟踪中）——卡片必须
        # 如实上报两口径，不得修饰。
        progress=0.0,
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(user_id=user_id, goal_id=goal.id, name="线代复习冲刺", type=PlanType.SPRINT)
    db_session.add(plan)
    await db_session.flush()
    goal.plan_id = plan.id
    await db_session.flush()
    for i in range(total):
        db_session.add(
            Task(
                user_id=user_id,
                plan_id=plan.id,
                title=f"任务 {i}",
                type=TaskType.LEARNING,
                estimated_minutes=25,
                status=TaskStatus.COMPLETED if i < completed else TaskStatus.PENDING,
            )
        )
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


def _iter_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from _iter_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_keys(item)


_BANNED_KEYS = {
    # 置信百分比黑话（M-10 清除口径）与无定义能力分数/假精确预测族
    "confidence",
    "risk_score",
    "difficulty_score",
    "predicted_mastery",
    "mastery_score",
    "score",
    "percent",
    "percentage",
    "probability",
    "rate",
    "interval",
}


async def _get_cards(app: FastAPI) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/evidence-cards")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_three_kinds_with_five_element_structure(db_session):
    """三类洞察齐备，每张卡五要素结构完整且无假精确键。"""
    user = await _make_user(db_session)
    for _ in range(3):
        await _seed_lifecycle_event(
            db_session, user.id, decision_id=f"aurora_{uuid4().hex}", event_type="exposed"
        )
    await _seed_lifecycle_event(
        db_session,
        user.id,
        decision_id=await _first_decision(db_session, user.id),
        event_type="accepted",
    )
    # interventions_that_helped：一条 exposure + 观察到的正向 outcome（窗口内）
    helped_decision = f"aurora_{uuid4().hex}"
    await _seed_lifecycle_event(
        db_session,
        user.id,
        decision_id=helped_decision,
        event_type="exposed",
        friction_tag="recall_gap",
    )
    await _seed_lifecycle_event(
        db_session,
        user.id,
        decision_id=helped_decision,
        event_type="outcome_observed",
        friction_tag="recall_gap",
        outcome_polarity="positive",
    )
    await _seed_goal_with_tasks(db_session, user.id, completed=1, total=2)

    app = _build_app(db_session, user.id)
    body = await _get_cards(app)

    assert body["meta"]["schema_version"] == "insights.evidence_cards.v1"
    cards = body["data"]["cards"]
    kinds = {card["kind"] for card in cards}
    assert {"friction_pattern", "interventions_that_helped", "goal_progress"} <= kinds

    for card in cards:
        for element in ("fact", "interpretation", "uncertainty", "evidence", "implication"):
            assert element in card, f"{card['kind']} 缺五要素之一: {element}"
        assert card["fact"], "fact 不得为空"
        assert isinstance(card["evidence"], list) and card["evidence"], "每条洞察必须有证据深链"
        for entry in card["evidence"]:
            assert entry["deep_link"].startswith("/")
        # 假精确红线：全 payload 禁止置信百分比/无定义分数族键
        keys = set(_iter_keys(card))
        assert not (keys & _BANNED_KEYS), f"发现禁用键: {keys & _BANNED_KEYS}"

    friction_card = next(c for c in cards if c["kind"] == "friction_pattern")
    assert friction_card["fact"]["friction_tag"] == "execution_friction"
    assert friction_card["fact"]["exposures"] == 3
    assert friction_card["fact"]["accepted"] == 1

    helped_card = next(c for c in cards if c["kind"] == "interventions_that_helped")
    # 只给定性证据档 + 计数，不给 rate/区间
    assert helped_card["fact"]["n_observed"] == 1
    assert helped_card["fact"]["n_positive"] == 1
    assert helped_card["interpretation"]["evidence_strength"] in {
        "single_observation",
        "repeated",
        "accumulated",
    }
    assert "correlation_not_causation" in helped_card["uncertainty"]["qualifiers"]

    goal_card = next(c for c in cards if c["kind"] == "goal_progress")
    assert goal_card["fact"]["ledger"] == {"completed": 1, "total": 2}
    # 真源 progress 列读数原样上报（0.0），不修饰
    assert goal_card["fact"]["progress_column"] == 0.0
    assert goal_card["implication"]["deep_link"].endswith(str(goal_card["fact"]["goal_id"]))


async def _first_decision(db_session: AsyncSession, user_id) -> str:
    from sqlalchemy import select

    row = (
        await db_session.execute(
            select(InterventionLifecycleEvent.decision_id).where(
                InterventionLifecycleEvent.user_id == user_id,
                InterventionLifecycleEvent.event_type == "exposed",
            )
        )
    ).first()
    return row[0]


@pytest.mark.asyncio
async def test_no_data_returns_no_cards_and_no_persona(db_session):
    """无数据不生成卡：既无洞察更无人格结论。"""
    user = await _make_user(db_session)
    app = _build_app(db_session, user.id)
    body = await _get_cards(app)

    assert body["data"]["cards"] == []
    assert "no evidence" in body["meta"]["note"]


@pytest.mark.asyncio
async def test_helped_card_suppressed_when_evidence_insufficient(db_session):
    """无观察结果的 exposure 证据不足 → 不生成『有帮助』结论。"""
    user = await _make_user(db_session)
    await _seed_lifecycle_event(
        db_session, user.id, decision_id=f"aurora_{uuid4().hex}", event_type="exposed"
    )
    app = _build_app(db_session, user.id)
    body = await _get_cards(app)

    kinds = {card["kind"] for card in body["data"]["cards"]}
    assert "interventions_that_helped" not in kinds
    assert "friction_pattern" in kinds  # exposure 本身是真实事件，摩擦卡仍在


@pytest.mark.asyncio
async def test_correction_updates_subsequent_reads(db_session):
    """纠正/新事实落库后，后续读取如实更新（派生视图，无陈旧快照）。"""
    user = await _make_user(db_session)
    await _seed_goal_with_tasks(db_session, user.id, completed=0, total=2)
    decision_id = f"aurora_{uuid4().hex}"
    await _seed_lifecycle_event(
        db_session, user.id, decision_id=decision_id, event_type="exposed"
    )
    app = _build_app(db_session, user.id)

    first = await _get_cards(app)
    cards = {card["kind"]: card for card in first["data"]["cards"]}
    assert cards["goal_progress"]["fact"]["ledger"]["completed"] == 0
    assert cards["friction_pattern"]["fact"]["accepted"] == 0

    # 纠正面 1：完成任务（账本事实变化）
    from sqlalchemy import select

    task = (
        await db_session.execute(select(Task).where(Task.user_id == user.id))
    ).scalars().first()
    task.status = TaskStatus.COMPLETED
    await db_session.commit()
    # 纠正面 2：用户接受了干预（解释面事实变化）
    await _seed_lifecycle_event(
        db_session, user.id, decision_id=decision_id, event_type="accepted"
    )

    second = await _get_cards(app)
    updated = {card["kind"]: card for card in second["data"]["cards"]}
    assert updated["goal_progress"]["fact"]["ledger"]["completed"] == 1
    assert updated["friction_pattern"]["fact"]["accepted"] == 1


@pytest.mark.asyncio
async def test_user_isolation_and_window(db_session):
    """他人事件不泄漏；窗口外事件不计入。"""
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    await _seed_lifecycle_event(
        db_session, other.id, decision_id=f"aurora_{uuid4().hex}", event_type="exposed"
    )
    # 窗口外（>30 天）
    await _seed_lifecycle_event(
        db_session,
        user.id,
        decision_id=f"aurora_{uuid4().hex}",
        event_type="exposed",
        occurred_at=_NOW - timedelta(days=45),
    )

    app = _build_app(db_session, user.id)
    body = await _get_cards(app)
    cards = body["data"]["cards"]
    # 仅有窗口外的陈旧 exposure → 不出摩擦卡（30 天窗内零证据）
    assert not any(
        c["kind"] == "friction_pattern" and c["fact"]["exposures"] > 0 for c in cards
    )
