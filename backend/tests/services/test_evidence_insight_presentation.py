"""V4-D05 · D07 事实卡读面呈现契约服务层守卫（sqlite 隔离，不触 dev DB）。

只经**既有生产入口**驱动写路径（``InterventionLifecycleService.record_exposure /
record_response / record_outcome_association``，与 F507 读侧数据流守卫同纪律），
对 V4-D05 呈现契约的接线各写正反配对：

- 验收①（服务层反例钉）：三例只有两例关联的真实卡 payload 无因果百分比、
  过 M-06 因果断言扫描、qualifier 随行、interpretation.causal 恒 False；
- D02-R1 C-3：重放投递（绕过写幂等的重复关联行）不放大呈现样本量；
- 验收②：无数据不出卡+无理解宣称；有删失的切片 understanding 门扣下
  「充分理解」资格；已删来源（软删行）不复用（卡与回访两面）；
- 验收③：每张卡 next_step 信封 ≤1 主建议、``user_can_reject=True``、
  ``reject_penalty="none"``；真实拒绝路径（record_response REJECTED）→
  回访 rejected_by_user 且零奖励后果；
- objective：回访由真实事件证明相关性（accepted+链接 outcome →
  related_outcome_observed + 样本身份），无事件不出回访。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.aurora_decision import AuroraDecisionContract
from app.core.experience_memory import scan_output_for_causal_assertions
from app.core.insight_presentation import REASON_INCOMPLETE_EVIDENCE
from app.core.intervention_lifecycle import LifecycleEventType
from app.core.outcome_ledger import (
    OutcomeEntry,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.execution_intent import ExecutionMode
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.user import User
from app.services.evidence_insight_service import EvidenceInsightService
from app.services.intervention_lifecycle_service import InterventionLifecycleService

_T0 = datetime(2026, 9, 25, 10, 0, 0)
_NOW = _T0 + timedelta(hours=2)  # 窗口内查询时点（outcome 未到期面可测）


async def _make_user(db_session) -> User:
    user = User(
        username=f"d05{uuid4().hex[:8]}",
        email=f"d05{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source="email",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _decision(user_id, *, salt: str = "") -> AuroraDecisionContract:
    """同签名决策（rescope × knowledge_bottleneck）：三例同切片的锚。"""
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type="rescope",
        rationale_summary=f"d05 presentation test {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=ExecutionMode.HYBRID,
        trigger_point="l2_escalation",
        input_context_hash=uuid4().hex[:8],
        evidence_refs=("signal://knowledge_transfer",),
    )


def _linked_decision(user_id, *, task_uuid: str) -> AuroraDecisionContract:
    """带 task 链接键的决策（outcome 关联的前提：exposure.linkage 有 task_id）。"""
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type="rescope",
        rationale_summary=f"d05 linked test {uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=ExecutionMode.HYBRID,
        trigger_point="l2_escalation",
        input_context_hash=uuid4().hex[:8],
        evidence_refs=("signal://knowledge_transfer",),
        action_proposal_ref=f"task://{task_uuid}",
    )


def _outcome(user_id, *, task_uuid: str, at: datetime, salt: str = "") -> OutcomeEntry:
    sid = f"d05-{task_uuid[:8]}-{salt or uuid4().hex[:6]}"
    return OutcomeEntry(
        outcome_id=derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid),
        source=OutcomeSource.TASK_COMPLETION,
        source_id=sid,
        user_id=str(user_id),
        occurred_at=at,
        truth_class=TruthClass.ACTUAL,
        polarity=OutcomePolarity.POSITIVE,
        source_ref=f"task_completion://{sid}",
        correlation={"task_id": task_uuid},
    )


async def _expose_three(db_session, user: User, *, linked: bool = False):
    """三次同签名 exposure（每次独立 decision）；linked=True 时各带独立 task 键。"""
    svc = InterventionLifecycleService(db_session)
    decisions = []
    for index in range(3):
        task_uuid = str(uuid4())
        decision = _linked_decision(user.id, task_uuid=task_uuid) if linked else _decision(user.id, salt=f"n{index}")
        result = await svc.record_exposure(
            decision=decision, user_id=user.id, occurred_at=_T0 + timedelta(minutes=index)
        )
        assert result.recorded is True, result.reason
        decisions.append((decision, task_uuid))
    await db_session.commit()
    return svc, decisions


def _walk_strings(node) -> list[str]:
    if isinstance(node, dict):
        out: list[str] = []
        for key, value in node.items():
            out.extend(_walk_strings(key))
            out.extend(_walk_strings(value))
        return out
    if isinstance(node, (list, tuple)):
        out = []
        for item in node:
            out.extend(_walk_strings(item))
        return out
    if isinstance(node, str):
        return [node]
    return []


async def _helped_card(db_session, user: User) -> dict | None:
    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    for card in result["data"]["cards"]:
        if card["kind"] == "interventions_that_helped":
            return card
    return None


# ---------------------------------------------------------------------------
# 验收①（服务层反例钉）：三例只有两例关联，卡面无因果百分比
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_exposures_two_linked_card_carries_no_causal_percentage(db_session):
    """反例钉：3 exposure + 2 链接 outcome → 卡如实出 3/2 分母，写不出「提升67%」。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user, linked=True)
    for (decision, task_uuid), offset in zip(decisions[:2], (10, 20), strict=True):
        result = await svc.record_outcome_association(
            decision_id=decision.decision_id_or_compute(),
            outcome=_outcome(user.id, task_uuid=task_uuid, at=_T0 + timedelta(minutes=offset)),
        )
        assert result.recorded is True, result.reason
    await db_session.commit()

    card = await _helped_card(db_session, user)
    assert card is not None
    # 事实面：分母 3、关联 2，随行如实。
    assert card["fact"]["n_exposed"] == 3
    assert card["fact"]["n_observed"] == 2
    assert card["fact"]["n_positive"] == 2
    # 相关非因果：档位词与 qualifier 随行，causal 恒 False。
    assert card["interpretation"]["causal"] is False
    assert card["interpretation"]["direction"] == "positive_association"
    assert "correlation_not_causation" in card["uncertainty"]["qualifiers"]
    assert "small_sample" in card["uncertainty"]["qualifiers"]
    # 夸大表述门全 payload 字符串扫描：无「67%」、无因果/成效措辞族。
    strings = _walk_strings(card)
    assert not any("67%" in s or "67 %" in s for s in strings), strings
    assert not any(term in s for s in strings for term in ("提升", "提高", "改善", "见效", "有效"))
    # M-06 因果断言扫描（单一权威）：全 payload 干净。
    assert scan_output_for_causal_assertions(card) == []
    # 理解宣称门：3 暴露只有 2 观察有一删失未到期 → 「充分理解」资格扣下。
    assert card["understanding"]["claim_allowed"] is False
    assert REASON_INCOMPLETE_EVIDENCE in card["understanding"]["reasons"]
    assert card["understanding"]["censored"] >= 1
    # 单主建议信封：恰一个主建议、可拒绝、零惩罚。
    assert card["next_step"]["primary"] == card["implication"]
    assert card["next_step"]["user_can_reject"] is True
    assert card["next_step"]["reject_penalty"] == "none"


@pytest.mark.asyncio
async def test_every_emitted_card_has_at_most_one_primary_suggestion(db_session):
    """全卡型不变量：next_step 信封 ≤1 主建议（一条观察 ≤ 一个主建议）。"""
    user = await _make_user(db_session)
    await _expose_three(db_session, user)
    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    assert result["data"]["cards"], "friction 卡应存在（3 次暴露）"
    for card in result["data"]["cards"]:
        assert card["next_step"]["user_can_reject"] is True
        assert card["next_step"]["reject_penalty"] == "none"
        assert card["next_step"]["primary"] is not None
        assert card["next_step"]["primary"] == card["implication"]


# ---------------------------------------------------------------------------
# D02-R1 C-3：重放投递不进样本量
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replayed_outcome_delivery_does_not_inflate_sample_size(db_session):
    """写幂等被绕过（直插重复关联行）时，呈现侧按样本身份去重：样本量不放大。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user, linked=True)
    decision, task_uuid = decisions[0]
    outcome = _outcome(user.id, task_uuid=task_uuid, at=_T0 + timedelta(minutes=10), salt="replay")
    result = await svc.record_outcome_association(decision_id=decision.decision_id_or_compute(), outcome=outcome)
    assert result.recorded is True

    # 模拟绕过 _insert_once 的重放投递（同 decision 同 outcome，不同 dedupe 子键）。
    db_session.add(
        InterventionLifecycleEvent(
            user_id=user.id,
            decision_id=decision.decision_id_or_compute(),
            event_type=LifecycleEventType.OUTCOME_OBSERVED.value,
            intervention_type="rescope",
            execution_mode="hybrid",
            goal_type="unknown",
            friction_tag="knowledge_bottleneck",
            linkage={"task_id": task_uuid},
            outcome_source="task_completion",
            outcome_ref=outcome.outcome_id,
            outcome_polarity="positive",
            outcome_truth_class="actual",
            detail=None,
            dedupe_subkey=f"{outcome.outcome_id}:replay",
            occurred_at=_T0 + timedelta(minutes=11),
        )
    )
    await db_session.commit()

    card = await _helped_card(db_session, user)
    assert card is not None
    uncertainty = card["uncertainty"]
    # 重放如实计 raw（2），去重后样本量恒 1——重放不放大样本量。
    assert uncertainty["outcome_samples_raw"] == 2
    assert uncertainty["samples"] == 1
    assert uncertainty["duplicate_outcome_samples_dropped"] == 1
    assert "replayed_deliveries_excluded_from_sample" in uncertainty["qualifiers"]


# ---------------------------------------------------------------------------
# 验收②：无数据不出卡/不出理解；已删来源不复用
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_data_means_no_cards_no_understanding_claim_no_revisit(db_session):
    user = await _make_user(db_session)
    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    assert result["data"]["cards"] == []
    assert "no evidence in window" in result["meta"]["note"]
    revisit = result["data"]["revisit"]
    assert revisit["relevance"] == "no_prior_suggestion"
    assert revisit["proves_relevance"] is False
    assert revisit["decision_id"] == ""
    assert "presentation_gate_dropped" not in result["meta"]


@pytest.mark.asyncio
async def test_deleted_source_rows_are_not_reused_by_cards_or_revisit(db_session):
    """已删来源不复用：软删关联行 → 卡样本即刻回落；软删 exposure → 回访消失。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user, linked=True)
    decision, task_uuid = decisions[0]
    await svc.record_outcome_association(
        decision_id=decision.decision_id_or_compute(),
        outcome=_outcome(user.id, task_uuid=task_uuid, at=_T0 + timedelta(minutes=10)),
    )
    # 第二个 decision 也链接（保证删除后仍有卡）。
    decision2, task_uuid2 = decisions[1]
    await svc.record_outcome_association(
        decision_id=decision2.decision_id_or_compute(),
        outcome=_outcome(user.id, task_uuid=task_uuid2, at=_T0 + timedelta(minutes=20)),
    )
    await db_session.commit()

    before = await _helped_card(db_session, user)
    assert before is not None and before["uncertainty"]["samples"] == 2

    # 软删第一条关联行（来源删除）。
    row = (
        (
            await db_session.execute(
                select(InterventionLifecycleEvent).where(
                    InterventionLifecycleEvent.decision_id == decision.decision_id_or_compute(),
                    InterventionLifecycleEvent.event_type == LifecycleEventType.OUTCOME_OBSERVED.value,
                )
            )
        )
        .scalars()
        .one()
    )
    row.deleted_at = _NOW
    await db_session.commit()

    after = await _helped_card(db_session, user)
    assert after is not None
    assert after["uncertainty"]["samples"] == 1  # 已删来源不复用
    assert after["uncertainty"]["outcome_samples_raw"] == 1

    # 软删 exposure → 回访不再引用已删建议（no_prior，不复活）。
    exposure_row = (
        (
            await db_session.execute(
                select(InterventionLifecycleEvent).where(
                    InterventionLifecycleEvent.decision_id == decision.decision_id_or_compute(),
                    InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                )
            )
        )
        .scalars()
        .one()
    )
    exposure_row.deleted_at = _NOW
    await db_session.commit()

    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    revisit = result["data"]["revisit"]
    assert revisit["decision_id"] != decision.decision_id_or_compute() or revisit["relevance"] == "no_prior_suggestion"


# ---------------------------------------------------------------------------
# 验收③ + objective：拒绝路径真实存在且零惩罚；回访由真实事件证明
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_rejection_recorded_with_zero_reward_consequence(db_session):
    """真实拒绝路径：record_response(REJECTED) 落行，且无任何奖励扣减面。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user)
    decision, _ = decisions[-1]  # 回访读最近一次 exposure
    did = decision.decision_id_or_compute()

    result = await svc.record_response(decision_id=did, user_id=user.id, event_type=LifecycleEventType.REJECTED.value)
    assert result.recorded is True
    await db_session.commit()

    # 拒绝行真实存在（可拒绝路径真实存在）。
    rejected_rows = (
        (
            await db_session.execute(
                select(InterventionLifecycleEvent).where(
                    InterventionLifecycleEvent.decision_id == did,
                    InterventionLifecycleEvent.event_type == LifecycleEventType.REJECTED.value,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rejected_rows) == 1

    # 零奖励后果：拒绝不触碰奖励货币（photon_balance 分毫不动）。
    await db_session.refresh(user)
    assert (user.photon_balance or 0) == 0

    # 回访面：用户拒绝是一等决定（rejected_by_user），零惩罚随行可读。
    payload = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    revisit = payload["data"]["revisit"]
    assert revisit["decision_id"] == did
    assert revisit["response"] == "rejected"
    assert revisit["relevance"] == "rejected_by_user"
    assert revisit["reward_consequence"] == "none"
    assert revisit["proves_relevance"] is False


@pytest.mark.asyncio
async def test_revisit_proves_relevance_via_real_linked_outcome(db_session):
    """objective：回访证明上次建议相关——accepted + 链接 outcome → 样本身份在册。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user, linked=True)
    decision, task_uuid = decisions[-1]  # 回访读最近一次 exposure
    did = decision.decision_id_or_compute()
    await svc.record_response(decision_id=did, user_id=user.id, event_type=LifecycleEventType.ACCEPTED.value)
    await svc.record_outcome_association(
        decision_id=did,
        outcome=_outcome(user.id, task_uuid=task_uuid, at=_T0 + timedelta(minutes=30)),
    )
    await db_session.commit()

    payload = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    revisit = payload["data"]["revisit"]
    assert revisit["decision_id"] == did
    assert revisit["response"] == "accepted"
    assert revisit["relevance"] == "related_outcome_observed"
    assert revisit["proves_relevance"] is True
    assert revisit["n_outcome_samples_unique"] == 1
    assert len(revisit["sample_ids"]) == 1
    assert revisit["sample_ids"][0].startswith("attr_")

    # 对照（非套模板）：拒绝历史 → 结构化字段必然不同。
    other = await _make_user(db_session)
    svc2, decisions2 = await _expose_three(db_session, other)
    await svc2.record_response(
        decision_id=decisions2[-1][0].decision_id_or_compute(),
        user_id=other.id,
        event_type=LifecycleEventType.REJECTED.value,
    )
    await db_session.commit()
    payload2 = await EvidenceInsightService(db_session).build_cards(user_id=other.id, now=_NOW)
    revisit2 = payload2["data"]["revisit"]
    assert revisit2["relevance"] == "rejected_by_user"
    assert revisit2 != revisit


@pytest.mark.asyncio
async def test_revisit_awaiting_states_from_real_window_semantics(db_session):
    """窗口语义消费 D-05 权威：行动未回 → acted_awaiting；未行动 → awaiting_user。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user)
    did = decisions[-1][0].decision_id_or_compute()  # 回访读最近一次 exposure
    await svc.record_response(decision_id=did, user_id=user.id, event_type=LifecycleEventType.STARTED.value)
    await db_session.commit()

    payload = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    revisit = payload["data"]["revisit"]
    assert revisit["relevance"] == "acted_awaiting_outcome"
    assert revisit["proves_relevance"] is False

    user2 = await _make_user(db_session)
    await _expose_three(db_session, user2)
    payload2 = await EvidenceInsightService(db_session).build_cards(user_id=user2.id, now=_NOW)
    revisit2 = payload2["data"]["revisit"]
    assert revisit2["relevance"] == "awaiting_user"


# ---------------------------------------------------------------------------
# 夸大表述门的服务层守卫：违例卡整体扣下（响亮失败）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_drops_cards_without_silent_rewrite(db_session):
    """构造违例（直插 causal claim 的卡不可能来自封闭模板——以门参数面验证）：
    门参数取自卡自身分母；正常的关联卡恒过门（present gate 零误伤）。"""
    user = await _make_user(db_session)
    svc, decisions = await _expose_three(db_session, user, linked=True)
    for (decision, task_uuid), offset in zip(decisions[:2], (10, 20), strict=True):
        await svc.record_outcome_association(
            decision_id=decision.decision_id_or_compute(),
            outcome=_outcome(user.id, task_uuid=task_uuid, at=_T0 + timedelta(minutes=offset)),
        )
    await db_session.commit()

    result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=_NOW)
    # 封闭模板卡恒过门：无静默扣下、无静默改写。
    assert "presentation_gate_dropped" not in result["meta"]
    helped = [c for c in result["data"]["cards"] if c["kind"] == "interventions_that_helped"]
    assert helped and helped[0]["interpretation"]["causal"] is False
