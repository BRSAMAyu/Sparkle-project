"""D-05 · InterventionLifecycleService 服务层守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项（卡 D-05）：
- **同一 intervention 不双计**：exposure/response 幂等（重放第二写 recorded=False，
  存储恰一行）；outcome 关联按 (decision_id, outcome_id) 恰一次；
- **outcome 白名单红线**：behavioral / chat 类源拒收；窗口外/无关联键拒收；
- **censored/unknown 语义**：not_yet_due / window_closed / churned 三态分解，
  删失永不进 rate 分母；
- **per-user / per-scope 历史结果摘要**（验收 ②）：切片分组、用户隔离、
  global scope 的 demo cohort 排除、非因果 claim、Wilson 区间；
- 关联扫描（associate_pending_outcomes）幂等可重跑：真实 Task 完成源 →
  关联行恰一条，重跑零新增；
- watermark / cache key 的增量缓存语义（M-06 消费面）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.aurora_decision import AuroraDecisionContract
from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_SINGLE,
    LifecycleEventType,
)
from app.core.outcome_ledger import (
    OutcomeEntry,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.execution_intent import ExecutionMode
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.intervention_lifecycle_service import InterventionLifecycleService

_T0 = datetime(2026, 9, 19, 10, 0, 0)


async def _make_user(db_session, *, registration_source: str = "email") -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source=registration_source,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _decision(
    user_id,
    *,
    intervention_type: str = "rescope",
    mode: ExecutionMode | None = ExecutionMode.HYBRID,
    governance: str = "live",
    task_ref: str | None = None,
    evidence=("signal://knowledge_transfer",),
    salt: str = "",
) -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=intervention_type,
        rationale_summary=f"d05 test decision {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=mode,
        governance_mode=governance,
        evidence_refs=tuple(evidence),
        action_proposal_ref=task_ref,
    )


def _no_action_decision(user_id) -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type="no_action",
        rationale_summary="signal below materiality",
        cognition_tier="l0_rules",
        execution_mode=None,
        no_action_reason="materiality_below_threshold",
    )


def _outcome(
    user_id,
    *,
    source: OutcomeSource = OutcomeSource.TASK_COMPLETION,
    at: datetime,
    polarity: OutcomePolarity = OutcomePolarity.POSITIVE,
    truth: TruthClass = TruthClass.ACTUAL,
    correlation: dict | None = None,
    source_id: str | None = None,
) -> OutcomeEntry:
    sid = source_id or uuid4().hex
    return OutcomeEntry(
        outcome_id=derive_outcome_id(source=source, source_id=sid),
        source=source,
        source_id=sid,
        user_id=str(user_id),
        occurred_at=at,
        truth_class=truth,
        polarity=polarity,
        source_ref=f"{source.value}://{sid}",
        correlation=correlation or {},
    )


# ---------------------------------------------------------------------------
# 1. 生命周期记录幂等（验收 ①：不双计）
# ---------------------------------------------------------------------------


class TestExposureRecording:
    async def test_exposure_recorded_once_replay_refused(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, task_ref=f"task://{uuid4()}")

        first = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert first.recorded is True and first.reason == ""

        second = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0 + timedelta(hours=1))
        assert second.recorded is False
        assert second.reason == "duplicate_event"
        assert second.event_id == first.event_id  # 同幂等键同 id

        from app.models.intervention_lifecycle import InterventionLifecycleEvent

        rows = (
            (
                await db_session.execute(
                    InterventionLifecycleEvent.__table__.select().where(
                        InterventionLifecycleEvent.decision_id == first.decision_id
                    )
                )
            ).fetchall()
        )
        assert len(rows) == 1  # 存储恰一行——不双计

    async def test_inert_intervention_exposure_refused(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        result = await svc.record_exposure(decision=_no_action_decision(user.id), user_id=user.id)
        assert result.recorded is False
        assert "inert" in result.reason

    async def test_shadow_governance_exposure_refused(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        result = await svc.record_exposure(
            decision=_decision(user.id, governance="shadow"), user_id=user.id
        )
        assert result.recorded is False
        assert "shadow" in result.reason

    async def test_broken_payload_refused_without_row(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        result = await svc.record_exposure(decision={"garbage": True}, user_id=user.id)
        assert result.recorded is False
        assert result.reason == "decision_payload_invalid"

    async def test_slices_captured_at_exposure_time(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, evidence=("signal://cognitive_load",))
        result = await svc.record_exposure(
            decision=decision, user_id=user.id, goal_type="exam", occurred_at=_T0
        )
        assert result.recorded
        exposure = await svc._get_exposure(decision_id=result.decision_id)
        assert exposure.goal_type == "exam"
        assert exposure.friction_tag == "cognitive_overload"  # signal://cognitive_load 派生
        assert exposure.execution_mode == "hybrid"


class TestResponseRecording:
    async def test_response_funnel_idempotent(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id)
        exposed = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert exposed.recorded

        accepted = await svc.record_response(
            decision_id=exposed.decision_id,
            user_id=user.id,
            event_type=LifecycleEventType.ACCEPTED,
            occurred_at=_T0 + timedelta(minutes=5),
        )
        assert accepted.recorded

        replay = await svc.record_response(
            decision_id=exposed.decision_id,
            user_id=user.id,
            event_type=LifecycleEventType.ACCEPTED,
            occurred_at=_T0 + timedelta(minutes=6),
        )
        assert replay.recorded is False and replay.reason == "duplicate_event"

        started = await svc.record_response(
            decision_id=exposed.decision_id,
            user_id=user.id,
            event_type=LifecycleEventType.STARTED,
            occurred_at=_T0 + timedelta(minutes=10),
        )
        assert started.recorded

    async def test_orphan_response_refused(self, db_session):
        """无 exposure 的响应是孤儿事件——拒收（无锚点计数=双计风险源）。"""
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        result = await svc.record_response(
            decision_id="aurora_" + "c" * 32,
            user_id=user.id,
            event_type=LifecycleEventType.ACCEPTED,
        )
        assert result.recorded is False
        assert result.reason == "no_exposure"

    async def test_response_of_other_user_refused(self, db_session):
        user_a = await _make_user(db_session)
        user_b = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user_a.id)
        exposed = await svc.record_exposure(decision=decision, user_id=user_a.id, occurred_at=_T0)
        result = await svc.record_response(
            decision_id=exposed.decision_id,
            user_id=user_b.id,  # 非暴露对象的响应
            event_type=LifecycleEventType.ACCEPTED,
        )
        assert result.recorded is False

    async def test_outcome_event_type_rejected_by_record_response(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        with pytest.raises(ValueError):
            await svc.record_response(
                decision_id="aurora_" + "d" * 32,
                user_id=user.id,
                event_type=LifecycleEventType.OUTCOME_OBSERVED,
            )


# ---------------------------------------------------------------------------
# 2. outcome 关联（灵魂红线 + 幂等）
# ---------------------------------------------------------------------------


class TestOutcomeAssociation:
    async def _expose(self, db_session, user, *, task_id=None):
        svc = InterventionLifecycleService(db_session)
        task_ref = f"task://{task_id}" if task_id else None
        decision = _decision(user.id, task_ref=task_ref, salt="assoc")
        result = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert result.recorded
        return svc, result.decision_id

    async def test_whitelisted_linked_in_window_outcome_associated_once(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user, task_id=task_id)
        outcome = _outcome(
            user.id,
            at=_T0 + timedelta(hours=2),
            correlation={"task_id": str(task_id)},
        )

        first = await svc.record_outcome_association(decision_id=decision_id, outcome=outcome)
        assert first.recorded and first.reason == ""

        replay = await svc.record_outcome_association(decision_id=decision_id, outcome=outcome)
        assert replay.recorded is False and replay.reason == "duplicate_event"

    async def test_second_distinct_outcome_gets_its_own_row(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user, task_id=task_id)
        link = {"task_id": str(task_id)}
        first = await svc.record_outcome_association(
            decision_id=decision_id, outcome=_outcome(user.id, at=_T0 + timedelta(hours=1), correlation=link)
        )
        second = await svc.record_outcome_association(
            decision_id=decision_id, outcome=_outcome(user.id, at=_T0 + timedelta(hours=2), correlation=link)
        )
        assert first.recorded and second.recorded  # 不同 outcome 各自成行

    async def test_behavioral_source_rejected(self, db_session):
        """红线：behavioral（chat 信号分数判定族）不是关联白名单源。"""
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user, task_id=task_id)
        result = await svc.record_outcome_association(
            decision_id=decision_id,
            outcome=_outcome(
                user.id,
                source=OutcomeSource.BEHAVIORAL,
                at=_T0 + timedelta(hours=1),
                correlation={"task_id": str(task_id)},
            ),
        )
        assert result.recorded is False
        assert result.reason == "outcome_source_not_whitelisted"

    async def test_out_of_window_outcome_rejected(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user, task_id=task_id)
        result = await svc.record_outcome_association(
            decision_id=decision_id,
            outcome=_outcome(user.id, at=_T0 + timedelta(hours=200), correlation={"task_id": str(task_id)}),
        )
        assert result.recorded is False
        assert result.reason == "outcome_out_of_window"

    async def test_unlinked_outcome_rejected(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user, task_id=task_id)
        result = await svc.record_outcome_association(
            decision_id=decision_id,
            outcome=_outcome(user.id, at=_T0 + timedelta(hours=1), correlation={"task_id": str(uuid4())}),
        )
        assert result.recorded is False
        assert result.reason == "outcome_not_linked_to_intervention"

    async def test_association_without_exposure_rejected(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        result = await svc.record_outcome_association(
            decision_id="aurora_" + "e" * 32,
            outcome=_outcome(user.id, at=_T0 + timedelta(hours=1)),
        )
        assert result.recorded is False
        assert result.reason == "no_exposure"


class TestAssociationScan:
    """增量关联扫描：真实 Task 完成源 → 关联行；重跑零新增。"""

    async def test_scan_links_real_task_completion_once(self, db_session):
        from app.services.outcome_ledger_service import OutcomeLedgerService

        user = await _make_user(db_session)
        task = Task(
            user_id=user.id,
            title="复习线性代数",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.COMPLETED,
            completed_at=_T0 + timedelta(hours=2),
            actual_minutes=25,
        )
        db_session.add(task)
        await db_session.commit()

        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, task_ref=f"task://{task.id}")
        exposed = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert exposed.recorded

        new_links = await svc.associate_pending_outcomes(user_id=user.id, now=_T0 + timedelta(hours=3))
        assert new_links == 1

        # 重跑幂等：不双计
        again = await svc.associate_pending_outcomes(user_id=user.id, now=_T0 + timedelta(hours=4))
        assert again == 0

        # ledger 侧也能看到该 outcome（D-02 真源可对账）
        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        assert page.source_counts.get(OutcomeSource.TASK_COMPLETION, 0) == 1


# ---------------------------------------------------------------------------
# 3. 保守关联摘要（验收 ②；删失语义 + 切片 + 隔离 + cohort 边界）
# ---------------------------------------------------------------------------


class TestAssociationSummary:
    async def _expose(self, db_session, user, *, goal="exam", evidence=("signal://knowledge_transfer",), at=_T0):
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, evidence=evidence, salt=uuid4().hex[:6])
        result = await svc.record_exposure(decision=decision, user_id=user.id, goal_type=goal, occurred_at=at)
        assert result.recorded
        return svc, result.decision_id

    async def test_observed_exposure_produces_single_observation_slice(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        svc, decision_id = await self._expose(db_session, user)
        # 直接落一条白名单关联（linkage 为空 → 用 exposure 侧 plan/node 也无；
        # 改用带 task_ref 的 exposure）
        decision2 = _decision(user.id, task_ref=f"task://{task_id}", salt="obs")
        exposed2 = await svc.record_exposure(decision=decision2, user_id=user.id, goal_type="exam", occurred_at=_T0)
        assert exposed2.recorded
        linked = await svc.record_outcome_association(
            decision_id=exposed2.decision_id,
            outcome=_outcome(user.id, at=_T0 + timedelta(hours=2), correlation={"task_id": str(task_id)}),
        )
        assert linked.recorded

        summary = await svc.association_summary(user_id=user.id, now=_T0 + timedelta(hours=10))
        payload = summary.to_dict()
        assert payload["scope"][0] == "user"
        assert payload["n_exposures_total"] == 2
        observed_slice = next(s for s in payload["slices"] if s["n_observed"] > 0)
        assert observed_slice["n_positive"] == 1
        assert observed_slice["n_observed"] == 1
        assert observed_slice["evidence_strength"] == EVIDENCE_TIER_SINGLE
        assert observed_slice["causal_claim"] is False
        assert observed_slice["rate_interval"][1] >= observed_slice["positive_association_rate"]

    async def test_censored_not_yet_due_never_counts_negative(self, db_session):
        user = await _make_user(db_session)
        svc, _ = await self._expose(db_session, user, at=_T0)
        summary = await svc.association_summary(
            user_id=user.id, now=_T0 + timedelta(hours=10)  # 窗口未关
        )
        assert len(summary.slices) == 1
        slice_ = summary.slices[0]
        assert slice_.n_censored_not_yet_due == 1
        assert slice_.n_observed == 0  # 删失不进观察分母
        assert slice_.evidence_strength == "insufficient"

    async def test_window_closed_vs_churned_disambiguated(self, db_session):
        """在场而未行动（window_closed）≠ 无从观察（churned）。"""
        user_present = await _make_user(db_session)
        user_gone = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)

        for user in (user_present, user_gone):
            decision = _decision(user.id, salt=uuid4().hex[:6])
            result = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
            assert result.recorded

        now = _T0 + timedelta(hours=100)  # 72h 窗已关
        present = await svc.association_summary(
            user_id=user_present.id,
            now=now,
            user_last_active_at=_T0 + timedelta(hours=90),  # 窗末后仍活跃
        )
        gone = await svc.association_summary(
            user_id=user_gone.id,
            now=now,
            user_last_active_at=_T0 + timedelta(hours=30),  # 窗中已离开
        )
        assert present.slices[0].n_censored_window_closed == 1
        assert gone.slices[0].n_censored_user_churned == 1

    async def test_per_user_isolation_and_slice_grouping(self, db_session):
        user = await _make_user(db_session)
        other = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)

        # 同切片两条 exposure（不同 decision）
        for salt in ("g1", "g2"):
            decision = _decision(user.id, evidence=("signal://cognitive_load",), salt=salt)
            result = await svc.record_exposure(
                decision=decision, user_id=user.id, goal_type="exam", occurred_at=_T0
            )
            assert result.recorded
        # 不同 friction → 独立切片
        decision = _decision(user.id, evidence=("signal://goal_mode",), salt="g3")
        result = await svc.record_exposure(
            decision=decision, user_id=user.id, goal_type="exam", occurred_at=_T0
        )
        assert result.recorded
        # 其他用户的 exposure（不得进入 user 摘要）
        other_decision = _decision(other.id, salt="other")
        assert (
            await svc.record_exposure(decision=other_decision, user_id=other.id, occurred_at=_T0)
        ).recorded

        summary = await svc.association_summary(user_id=user.id, now=_T0 + timedelta(hours=1))
        assert summary.n_exposures_total == 3  # 不含 other 的 1 条
        friction_tags = {s.signature.friction_tag for s in summary.slices}
        assert friction_tags == {"cognitive_overload", "deadline_pressure"}
        grouped = [s for s in summary.slices if s.signature.friction_tag == "cognitive_overload"]
        assert grouped[0].n_exposed == 2

    async def test_no_double_count_after_replayed_exposure(self, db_session):
        """验收 ① 的摘要面：同一 decision 重放 exposure 不增 n_exposed。"""
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, salt="dbl")
        assert (await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)).recorded
        replay = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert replay.recorded is False

        summary = await svc.association_summary(user_id=user.id, now=_T0 + timedelta(hours=1))
        assert summary.n_exposures_total == 1

    async def test_global_scope_excludes_demo_cohort(self, db_session):
        real = await _make_user(db_session)
        seed = await _make_user(db_session, registration_source="seed")
        svc = InterventionLifecycleService(db_session)
        for user in (real, seed):
            decision = _decision(user.id, salt=f"g-{user.id}")
            assert (
                await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
            ).recorded

        global_summary = await svc.association_summary(now=_T0 + timedelta(hours=1))
        assert global_summary.scope == ("global",)
        assert global_summary.n_exposures_total == 1  # seed 行被排除

        explicit = await svc.association_summary(
            now=_T0 + timedelta(hours=1), include_demo_cohort=True
        )
        assert explicit.n_exposures_total == 2

    async def test_negative_outcomes_counted_not_hidden(self, db_session):
        """失败保留（DATA_FLYWHEEL §5）：负向 outcome 进 n_negative，不进删失面。"""
        user = await _make_user(db_session)
        task_id = uuid4()
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, task_ref=f"task://{task_id}", salt="neg")
        exposed = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert exposed.recorded
        assert (
            await svc.record_outcome_association(
                decision_id=exposed.decision_id,
                outcome=_outcome(
                    user.id,
                    source=OutcomeSource.QUIZ_FEEDBACK,
                    at=_T0 + timedelta(hours=1),
                    polarity=OutcomePolarity.NEGATIVE,
                    correlation={"task_id": str(task_id)},
                ),
            )
        ).recorded

        summary = await svc.association_summary(user_id=user.id, now=_T0 + timedelta(hours=3))
        slice_ = summary.slices[0]
        assert slice_.n_negative == 1
        assert slice_.n_positive == 0
        assert slice_.positive_association_rate == 0.0

    async def test_truth_class_weighting_applied(self, db_session):
        user = await _make_user(db_session)
        task_id = uuid4()
        link = {"task_id": str(task_id)}
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, task_ref=f"task://{task_id}", salt="w")
        exposed = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert exposed.recorded
        assert (
            await svc.record_outcome_association(
                decision_id=exposed.decision_id,
                outcome=_outcome(user.id, at=_T0 + timedelta(hours=1), truth=TruthClass.ACTUAL, correlation=link),
            )
        ).recorded
        assert (
            await svc.record_outcome_association(
                decision_id=exposed.decision_id,
                outcome=_outcome(
                    user.id,
                    at=_T0 + timedelta(hours=2),
                    truth=TruthClass.SELF_REPORTED,
                    correlation=link,
                ),
            )
        ).recorded

        summary = await svc.association_summary(user_id=user.id, now=_T0 + timedelta(hours=3))
        slice_ = summary.slices[0]
        assert slice_.n_positive == 2
        assert slice_.weighted_positive == pytest.approx(1.5)  # 1.0 + 0.5
        assert slice_.weighted_total == pytest.approx(1.5)

    async def test_slice_filters_push_down(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        exam = _decision(user.id, evidence=("signal://cognitive_load",), salt="f1")
        project = _decision(user.id, evidence=("signal://cognitive_load",), salt="f2")
        assert (
            await svc.record_exposure(decision=exam, user_id=user.id, goal_type="exam", occurred_at=_T0)
        ).recorded
        assert (
            await svc.record_exposure(decision=project, user_id=user.id, goal_type="project", occurred_at=_T0)
        ).recorded

        only_exam = await svc.association_summary(
            user_id=user.id, goal_type="exam", now=_T0 + timedelta(hours=1)
        )
        assert only_exam.n_exposures_total == 1
        assert only_exam.slices[0].signature.goal_type == "exam"

        only_friction = await svc.association_summary(
            user_id=user.id, friction_tag="cognitive_overload", now=_T0 + timedelta(hours=1)
        )
        assert only_friction.n_exposures_total == 2


# ---------------------------------------------------------------------------
# 4. 增量缓存钩（M-06 消费面）
# ---------------------------------------------------------------------------


class TestWatermarkAndCacheKey:
    async def test_watermark_stable_then_moves(self, db_session):
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        empty = await svc.watermark(user_id=user.id)
        assert empty == "empty"

        decision = _decision(user.id, salt="w1")
        assert (
            await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        ).recorded
        wm1 = await svc.watermark(user_id=user.id)

        wm1_again = await svc.watermark(user_id=user.id)
        assert wm1 == wm1_again  # 事件集不变 → 印记不变（可缓存）

        decision2 = _decision(user.id, salt="w2")
        assert (
            await svc.record_exposure(decision=decision2, user_id=user.id, occurred_at=_T0)
        ).recorded
        wm2 = await svc.watermark(user_id=user.id)
        assert wm2 != wm1

    async def test_cache_key_deterministic_and_filter_sensitive(self, db_session):
        base = InterventionLifecycleService.summary_cache_key(user_id=None, goal_type="exam")
        same = InterventionLifecycleService.summary_cache_key(user_id=None, goal_type="exam")
        other = InterventionLifecycleService.summary_cache_key(user_id=None, goal_type="project")
        user_scoped = InterventionLifecycleService.summary_cache_key(
            user_id="0f0e0d0c-0b0a-4909-8807-060504030201", goal_type="exam"
        )
        assert base == same
        assert base != other
        assert base != user_scoped
        assert base.startswith("d05:assoc_summary:")


# ---------------------------------------------------------------------------
# 5. outbox 集成通知（守卫写；分析真源在表，不在 outbox）
# ---------------------------------------------------------------------------


class TestOutboxEmission:
    """event_outbox 无 ORM 模型（仅 alembic 建表）——测试内按迁移 DDL 造表，
    验证 _emit_outbox_event 的原生 SQL 与已注册事件名真实可用。"""

    async def _create_outbox_tables(self, db_session):
        from sqlalchemy import text

        await db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS event_outbox (
                id TEXT PRIMARY KEY,
                aggregate_type VARCHAR(100) NOT NULL,
                aggregate_id TEXT NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                event_version INTEGER NOT NULL DEFAULT 1,
                payload TEXT NOT NULL,
                metadata TEXT,
                sequence_number INTEGER NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                published_at DATETIME
            )
        """))
        await db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS event_sequence_counters (
                aggregate_type VARCHAR(100) NOT NULL,
                aggregate_id TEXT NOT NULL,
                next_sequence INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (aggregate_type, aggregate_id)
            )
        """))
        await db_session.commit()

    async def test_exposure_emits_registered_outbox_event(self, db_session):
        import json as _json

        from sqlalchemy import text

        await self._create_outbox_tables(db_session)
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, salt="outbox")
        result = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert result.recorded

        rows = (
            await db_session.execute(
                text("SELECT event_type, sequence_number, payload FROM event_outbox")
            )
        ).fetchall()
        assert len(rows) == 1
        event_type, sequence_number, payload = rows[0]
        assert event_type == "intervention.exposed"
        assert sequence_number == 1
        payload = _json.loads(payload)
        assert payload["decision_id"] == result.decision_id
        assert payload["lifecycle_event_type"] == "exposed"

        # 重复 exposure（幂等拒收）不再发第二条 outbox 通知
        replay = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert replay.recorded is False
        count = (
            await db_session.execute(text("SELECT COUNT(*) FROM event_outbox"))
        ).scalar_one()
        assert count == 1

    async def test_response_events_do_not_emit_outbox(self, db_session):
        """accept/edit/reject 不发 outbox（reserved 名 intervention.feedback_recorded
        归 intervention_request aggregate 族，桥接是 A-04 接线卡的事）。"""
        from sqlalchemy import text

        await self._create_outbox_tables(db_session)
        user = await _make_user(db_session)
        svc = InterventionLifecycleService(db_session)
        decision = _decision(user.id, salt="noemit")
        exposed = await svc.record_exposure(decision=decision, user_id=user.id, occurred_at=_T0)
        assert exposed.recorded

        accepted = await svc.record_response(
            decision_id=exposed.decision_id,
            user_id=user.id,
            event_type=LifecycleEventType.ACCEPTED,
            occurred_at=_T0 + timedelta(minutes=1),
        )
        assert accepted.recorded
        rows = (
            await db_session.execute(text("SELECT event_type FROM event_outbox"))
        ).fetchall()
        assert [r[0] for r in rows] == ["intervention.exposed"]  # 仅 exposure 一条
