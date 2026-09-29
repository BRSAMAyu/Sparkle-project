"""V4-U13 · 洞察卡撤回排除显式在册（sqlite 隔离，不触 dev DB）。

只经**既有生产入口**驱动写路径，对 V4-U13 呈现增量的服务层守卫各写正反配对：

- 验收②「撤回」呈现面：软删 exposure / 软删任务 → 卡仍可出（不连坐），
  ``uncertainty.withdrawn_refs_excluded`` 计数如实随行——撤回不静默消失；
- 无撤回 → 计数为 0（显式零，不缺键、不编造撤回）；
- 呈现引用恒洁净：候选引用过 D05 契约 ``exclude_withdrawn_refs`` 精确身份
  过滤（软删身份绝不进 refs）；
- 撤回计数不改任何 fact 分子/分母（真源口径零改动——D-05 账本权威不动）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.aurora_decision import AuroraDecisionContract
from app.core.intervention_lifecycle import LifecycleEventType
from app.models.execution_intent import ExecutionMode
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.user import User
from app.services.evidence_insight_service import EvidenceInsightService
from app.services.intervention_lifecycle_service import InterventionLifecycleService

_T0 = datetime(2026, 9, 25, 10, 0, 0)
_NOW = _T0 + timedelta(hours=2)


async def _make_user(db_session) -> User:
    user = User(
        username=f"u13{uuid4().hex[:8]}",
        email=f"u13{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source="email",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _decision(user_id, *, salt: str = "") -> AuroraDecisionContract:
    """同签名决策（rescope × knowledge_bottleneck）。"""
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type="rescope",
        rationale_summary=f"u13 withdrawn test {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=ExecutionMode.HYBRID,
        trigger_point="l2_escalation",
        input_context_hash=uuid4().hex[:8],
        evidence_refs=("signal://knowledge_transfer",),
    )


async def _expose_three(db_session, user: User):
    """三次同签名 exposure（每次独立 decision）——摩擦卡与关联卡的最小证据面。"""
    svc = InterventionLifecycleService(db_session)
    decisions = []
    for index in range(3):
        decision = _decision(user.id, salt=f"n{index}")
        result = await svc.record_exposure(
            decision=decision, user_id=user.id, occurred_at=_T0 + timedelta(minutes=index)
        )
        assert result.recorded is True, result.reason
        decisions.append(decision)
    await db_session.commit()
    return svc, decisions


async def _soft_delete_exposure(db_session, decision_id: str, *, at: datetime) -> None:
    row = (
        (
            await db_session.execute(
                select(InterventionLifecycleEvent).where(
                    InterventionLifecycleEvent.decision_id == decision_id,
                    InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                )
            )
        )
        .scalars()
        .one()
    )
    row.deleted_at = at


async def _friction_card(result: dict) -> dict | None:
    for card in result["data"]["cards"]:
        if card["kind"] == "friction_pattern":
            return card
    return None


# ---------------------------------------------------------------------------
# 验收②「撤回」呈现面：排除计数显式随行，不静默消失
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_withdrawal_reports_explicit_zero(db_session):
    """正例（零撤回基线）：无软删行 → withdrawn_refs_excluded 显式为 0，不缺键。"""
    user = await _make_user(db_session)
    await _expose_three(db_session, user)

    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    card = await _friction_card(result)
    assert card is not None
    assert card["uncertainty"]["withdrawn_refs_excluded"] == 0
    # 真源口径零改动：fact 分子分母不受撤回面影响。
    assert card["fact"]["exposures"] == 3


@pytest.mark.asyncio
async def test_soft_deleted_exposure_counted_as_withdrawn_not_silent(db_session):
    """撤回显式在册：软删 1 条 exposure → 计数 =1 如实随行；剩余 2 条仍出卡
    （合法其他来源不连坐），fact exposures=2 不复活已删行。"""
    user = await _make_user(db_session)
    _, decisions = await _expose_three(db_session, user)

    await _soft_delete_exposure(db_session, decisions[0].decision_id_or_compute(), at=_NOW)
    await db_session.commit()

    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    card = await _friction_card(result)
    assert card is not None
    # 已删行不进 fact（既有权威），但撤回不静默：排除计数显式在册。
    assert card["fact"]["exposures"] == 2
    assert card["uncertainty"]["withdrawn_refs_excluded"] == 1
    # 呈现引用恒洁净：软删身份绝不进 refs。
    did = decisions[0].decision_id_or_compute()
    assert did not in card["evidence"][0]["refs"]


@pytest.mark.asyncio
async def test_all_withdrawn_no_card_no_claim(db_session):
    """全部来源撤回 → 无卡（无数据），绝不复活已删内容造假分析。"""
    user = await _make_user(db_session)
    _, decisions = await _expose_three(db_session, user)
    for decision in decisions:
        await _soft_delete_exposure(db_session, decision.decision_id_or_compute(), at=_NOW)
    await db_session.commit()

    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    assert await _friction_card(result) is None
    assert result["data"]["cards"] == []
    assert "note" in result["meta"]  # 诚实空态在册
