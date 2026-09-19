"""M-06 · ExperienceMemoryProjector 服务层守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项（卡 M-06，验收员独立复现用）：
- **双向召回**（验收 ①）：同一用户相似 context 下，正/负两个方向并列召回，
  失败干预与有效干预等价保留（同档位、同排序键）；
- **无 outcome 不标 effective**（验收 ②，灵魂红线）：只有删失/unknown 的
  干预 → evidence_count==0、方向谓词全 False、档位 insufficient、claim 为
  「尚无足够观察样本」族、只进 no_outcome_evidence 桶；
- **无因果断言**（验收 ③）：全链路（投影 + 检索）序列化输出过
  ``scan_output_for_causal_assertions`` 干净；
- **censored/unknown 语义正确流转**（验收 ④）：not_yet_due/window_closed/
  churned/unknown 计数原样保留在 outcome 面，永不进证据面；
- **FIX-31 P2-1 消费面**：摘要截断（ASC cap 丢最新）→ truncated 标记 +
  档位降一级 + degraded_confidence 面；
- D-05 消费面缓存（watermark 失效 + TTL 兜底）、M-07 删除链（软删事件 →
  投影消失）、M-03 真实预筛（user_memory_settings 权限真实生效）、
  M-05 selfcheck 接线、零写路径断言、用户隔离。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.aurora_decision import AuroraDecisionContract
from app.core.experience_memory import (
    DIRECTION_POSITIVE,
    SUMMARY_TRUNCATION_REASON,
    ExperienceContextQuery,
    scan_output_for_causal_assertions,
)
from app.core.intervention_lifecycle import EVIDENCE_TIER_INSUFFICIENT, EVIDENCE_TIER_REPEATED
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
from app.services import intervention_lifecycle_service as d05_module
from app.services.experience_memory_projector import (
    CACHE_TTL_SECONDS,
    ExperienceMemoryProjector,
    run_experience_use_selfcheck,
    to_selfcheck_candidates,
)
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.memory_use_selfcheck import SelfCheckContext

_T0 = datetime(2026, 9, 19, 10, 0, 0)
_NOW = _T0 + timedelta(hours=80)  # 默认观察时点：72h 窗已关


@pytest.fixture(autouse=True)
def _clean_projector_cache():
    ExperienceMemoryProjector.reset_cache()
    yield
    ExperienceMemoryProjector.reset_cache()


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
    task_ref: str | None = None,
    evidence=("signal://cognitive_load",),
    salt: str = "",
) -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=intervention_type,
        rationale_summary=f"m06 test decision {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=mode,
        governance_mode="live",
        evidence_refs=tuple(evidence),
        action_proposal_ref=task_ref,
    )


def _outcome(
    user_id,
    *,
    at: datetime,
    polarity: OutcomePolarity = OutcomePolarity.POSITIVE,
    truth: TruthClass = TruthClass.ACTUAL,
    correlation: dict | None = None,
    source: OutcomeSource = OutcomeSource.TASK_COMPLETION,
) -> OutcomeEntry:
    sid = uuid4().hex
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


async def _expose(
    db_session,
    user,
    *,
    intervention_type: str,
    task_id=None,
    goal="exam",
    evidence=("signal://cognitive_load",),
    at=_T0,
    salt="",
):
    """落一条 exposure，返回 (lifecycle 服务, decision_id)。"""
    svc = InterventionLifecycleService(db_session)
    task_ref = f"task://{task_id}" if task_id else None
    decision = _decision(
        user.id,
        intervention_type=intervention_type,
        task_ref=task_ref,
        evidence=evidence,
        salt=salt,
    )
    result = await svc.record_exposure(decision=decision, user_id=user.id, goal_type=goal, occurred_at=at)
    assert result.recorded
    return svc, result.decision_id


async def _link_outcome(db_session, user, decision_id, task_id, *, polarity, at):
    svc = InterventionLifecycleService(db_session)
    result = await svc.record_outcome_association(
        decision_id=decision_id,
        outcome=_outcome(
            user.id,
            at=at,
            polarity=polarity,
            correlation={"task_id": str(task_id)},
        ),
    )
    assert result.recorded


# ---------------------------------------------------------------------------
# 1. 双向召回（验收 ①）+ 失败等价保留
# ---------------------------------------------------------------------------


class TestBidirectionalRecall:
    async def test_similar_context_recalls_both_directions(self, db_session):
        """同一 situation（exam + cognitive_overload + hybrid）下：
        rescope 与 2 条 positive 共同出现、remind 与 2 条 negative 共同出现、
        practice 无 outcome——三路各归其桶。"""
        user = await _make_user(db_session)

        # rescope：2 条 positive
        task_a = uuid4()
        _, dec_a = await _expose(db_session, user, intervention_type="rescope", task_id=task_a, salt="a")
        await _link_outcome(
            db_session, user, dec_a, task_a, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1)
        )
        await _link_outcome(
            db_session, user, dec_a, task_a, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=2)
        )

        # remind：2 条 negative（quiz 挂科源）
        task_b = uuid4()
        _, dec_b = await _expose(db_session, user, intervention_type="remind", task_id=task_b, salt="b")
        await _link_outcome(
            db_session,
            user,
            dec_b,
            task_b,
            polarity=OutcomePolarity.NEGATIVE,
            at=_T0 + timedelta(hours=1),
        )
        await _link_outcome(
            db_session,
            user,
            dec_b,
            task_b,
            polarity=OutcomePolarity.NEGATIVE,
            at=_T0 + timedelta(hours=2),
        )

        # practice：无 outcome（观察时点在窗内 → censored_not_yet_due）
        _, _ = await _expose(db_session, user, intervention_type="practice", salt="c")

        projector = ExperienceMemoryProjector(db_session)
        query = ExperienceContextQuery(
            user_id=str(user.id),
            goal_type="exam",
            friction_tag="cognitive_overload",
            now=_T0 + timedelta(hours=3),  # 窗未关：practice 是 not_yet_due
        )
        result = await projector.retrieve_context(query)

        positive_types = [r.intervention for r in result.observed_with_positive]
        negative_types = [r.intervention for r in result.observed_with_negative]
        none_types = [r.intervention for r in result.no_outcome_evidence]

        assert positive_types == ["rescope"]
        assert negative_types == ["remind"]
        assert none_types == ["practice"]

    async def test_failure_retained_with_equal_strength(self, db_session):
        """失败等价保留：同观察数的负向记录与正向同档位、同 evidence_count。"""
        user = await _make_user(db_session)
        task_a, task_b = uuid4(), uuid4()
        _, dec_a = await _expose(db_session, user, intervention_type="rescope", task_id=task_a, salt="a")
        await _link_outcome(
            db_session, user, dec_a, task_a, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1)
        )
        await _link_outcome(
            db_session, user, dec_a, task_a, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=2)
        )
        _, dec_b = await _expose(db_session, user, intervention_type="remind", task_id=task_b, salt="b")
        await _link_outcome(
            db_session, user, dec_b, task_b, polarity=OutcomePolarity.NEGATIVE, at=_T0 + timedelta(hours=1)
        )
        await _link_outcome(
            db_session, user, dec_b, task_b, polarity=OutcomePolarity.NEGATIVE, at=_T0 + timedelta(hours=2)
        )

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        positive = result.observed_with_positive[0]
        negative = result.observed_with_negative[0]
        assert positive.evidence_count == negative.evidence_count == 2
        assert positive.evidence_strength == negative.evidence_strength == EVIDENCE_TIER_REPEATED

    async def test_dissimilar_situation_not_recalled(self, db_session):
        """相似性边界：不同 friction 的经验不进本次情境召回（保守精确匹配）。"""
        user = await _make_user(db_session)
        # deadline_pressure 情境（signal://goal_mode）下的经验
        await _expose(
            db_session,
            user,
            intervention_type="rescope",
            evidence=("signal://goal_mode",),
            salt="other-friction",
        )

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(
                user_id=str(user.id),
                goal_type="exam",
                friction_tag="cognitive_overload",
                now=_NOW,
            )
        )
        assert result.observed_with_positive == ()
        assert result.observed_with_negative == ()
        assert result.no_outcome_evidence == ()

    async def test_user_isolation(self, db_session):
        """用户隔离：A 的经验绝不进 B 的检索（身份维度无条件）。"""
        user_a = await _make_user(db_session)
        user_b = await _make_user(db_session)
        task_a = uuid4()
        _, dec_a = await _expose(db_session, user_a, intervention_type="rescope", task_id=task_a, salt="a")
        await _link_outcome(
            db_session, user_a, dec_a, task_a, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1)
        )

        projector = ExperienceMemoryProjector(db_session)
        result_b = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user_b.id), goal_type="exam", now=_NOW)
        )
        assert result_b.observed_with_positive == ()
        result_a = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user_a.id), goal_type="exam", now=_NOW)
        )
        assert [r.intervention for r in result_a.observed_with_positive] == ["rescope"]


# ---------------------------------------------------------------------------
# 2. 无 outcome 不标 effective（验收 ②，灵魂红线）
# ---------------------------------------------------------------------------


class TestNoOutcomeNeverEffective:
    async def test_censored_exposure_never_directional(self, db_session):
        """窗未关的 exposure：censored_not_yet_due=1，无任何方向证据。"""
        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p")

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_T0 + timedelta(hours=3))
        )
        assert len(result.no_outcome_evidence) == 1
        record = result.no_outcome_evidence[0]
        assert record.observed_with_positive == 0
        assert record.observed_with_negative == 0
        assert record.evidence_count == 0
        assert record.has_outcome_evidence is False
        assert record.has_positive_association_evidence is False
        assert record.has_negative_association_evidence is False
        assert record.evidence_strength == EVIDENCE_TIER_INSUFFICIENT
        assert "尚无足够的观察样本" in record.claim
        # 灵魂红线：不进任何方向桶
        assert record not in result.observed_with_positive
        assert record not in result.observed_with_negative

    async def test_window_closed_and_churned_stay_non_directional(self, db_session):
        """三种删失态 + 大量 exposure 计数都推不出方向证据。"""
        present = await _make_user(db_session)
        gone = await _make_user(db_session)
        await _expose(db_session, present, intervention_type="practice", salt="p1")
        await _expose(db_session, gone, intervention_type="practice", salt="p2")

        projector = ExperienceMemoryProjector(db_session)
        # present：窗末后仍活跃 → window_closed；gone：窗中已离开 → churned
        result_present = await projector.retrieve_context(
            ExperienceContextQuery(
                user_id=str(present.id),
                goal_type="exam",
                now=_NOW,
                user_last_active_at=_T0 + timedelta(hours=79),
            )
        )
        result_gone = await projector.retrieve_context(
            ExperienceContextQuery(
                user_id=str(gone.id),
                goal_type="exam",
                now=_NOW,
                user_last_active_at=_T0 + timedelta(hours=10),
            )
        )
        for result in (result_present, result_gone):
            record = result.no_outcome_evidence[0]
            assert record.evidence_count == 0
            assert record.has_outcome_evidence is False
            assert result.observed_with_positive == ()
            assert result.observed_with_negative == ()
        assert result_present.no_outcome_evidence[0].outcome_face["censored_window_closed"] == 1
        assert result_gone.no_outcome_evidence[0].outcome_face["censored_user_churned"] == 1

    async def test_accepted_feedback_alone_is_not_outcome_evidence(self, db_session):
        """用户接受/开始过干预（即时反馈）≠ 结果证据：方向谓词仍全 False。"""
        user = await _make_user(db_session)
        svc, decision_id = await _expose(db_session, user, intervention_type="practice", salt="fb")
        from app.core.intervention_lifecycle import LifecycleEventType

        assert (
            await svc.record_response(
                decision_id=decision_id,
                user_id=user.id,
                event_type=LifecycleEventType.ACCEPTED,
                occurred_at=_T0 + timedelta(minutes=5),
            )
        ).recorded
        assert (
            await svc.record_response(
                decision_id=decision_id,
                user_id=user.id,
                event_type=LifecycleEventType.STARTED,
                occurred_at=_T0 + timedelta(minutes=10),
            )
        ).recorded

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        record = result.no_outcome_evidence[0]
        assert record.feedback == {"accepted": 1, "started": 1}  # 反馈面保留
        assert record.evidence_count == 0  # 但不是结果证据
        assert record.has_outcome_evidence is False


# ---------------------------------------------------------------------------
# 3. 无因果断言（验收 ③，全链路）
# ---------------------------------------------------------------------------


class TestNoCausalAssertionEndToEnd:
    async def test_retrieval_payload_clean(self, db_session):
        user = await _make_user(db_session)
        task = uuid4()
        _, dec = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="a")
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1))
        await _expose(db_session, user, intervention_type="practice", salt="c")

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        assert scan_output_for_causal_assertions(result.to_dict()) == []
        for record in (*result.observed_with_positive, *result.no_outcome_evidence):
            assert record.to_dict()["causal_claim"] is False


# ---------------------------------------------------------------------------
# 4. censored/unknown 语义正确流转（验收 ④）
# ---------------------------------------------------------------------------


class TestCensoredSemanticsFlow:
    async def test_all_censored_states_preserved_verbatim(self, db_session):
        """D-05 三态删失 + 观察态在同一投影中共存，计数原样流转。"""
        user = await _make_user(db_session)
        # observed（1 正）
        task = uuid4()
        _, dec_obs = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="obs", at=_T0)
        await _link_outcome(
            db_session, user, dec_obs, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1)
        )
        # not_yet_due（新近 exposure，窗未关）
        await _expose(db_session, user, intervention_type="practice", salt="nyd", at=_NOW - timedelta(hours=2))
        # window_closed（窗关、用户在场）
        await _expose(db_session, user, intervention_type="remind", salt="wc", at=_T0)

        projector = ExperienceMemoryProjector(db_session)
        projection = await projector.project(user_id=user.id, now=_NOW, user_last_active_at=_NOW + timedelta(hours=1))
        faces = {r.intervention: r.outcome_face for r in projection.records}
        assert faces["rescope"]["observed_with_positive"] == 1
        assert faces["rescope"]["censored_not_yet_due"] == 0
        assert faces["practice"]["censored_not_yet_due"] == 1
        assert faces["remind"]["censored_window_closed"] == 1
        # unknown 面存在且默认 0（unknown 只来自损坏行，正常流恒 0——保留语义不丢）
        assert faces["rescope"]["unknown"] == 0

    async def test_deleted_events_excluded_and_cache_invalidated(self, db_session):
        """M-07 删除链：软删生命周期事件 → watermark 变化 → 缓存失效 → 记录消失。"""
        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p1")
        await _expose(db_session, user, intervention_type="remind", salt="p2")

        projector = ExperienceMemoryProjector(db_session)
        first = await projector.project(user_id=user.id, now=_NOW)
        assert {r.intervention for r in first.records} == {"practice", "remind"}

        # 软删 practice 的 exposure（M-07 口径：deleted_at）
        exposure = (
            (
                await db_session.execute(
                    InterventionLifecycleEvent.__table__.select().where(
                        InterventionLifecycleEvent.intervention_type == "practice"
                    )
                )
            ).fetchall()
        )[0]
        from datetime import datetime as _dt

        await db_session.execute(
            InterventionLifecycleEvent.__table__.update()
            .where(InterventionLifecycleEvent.id == exposure.id)
            .values(deleted_at=_dt.utcnow())
        )
        await db_session.commit()

        second = await projector.project(user_id=user.id, now=_NOW)
        assert {r.intervention for r in second.records} == {"remind"}  # 复活面不存在


# ---------------------------------------------------------------------------
# 5. FIX-31 P2-1 消费面：截断语义
# ---------------------------------------------------------------------------


class TestTruncationHandling:
    async def test_truncated_summary_marks_and_downgrades(self, db_session, monkeypatch):
        """行数 > cap → truncated=True + 档位降一级 + degraded_confidence。

        用 monkeypatch 把 D-05 的 _SUMMARY_EVENT_CAP 调小（5）：摘要 ASC
        加载最旧 5 行（真丢最新），探测 count=8 > 5 → 截断。M-06 的 cap
        引用是运行期模块属性读取，两侧一致。
        """
        user = await _make_user(db_session)
        # 布局 8 行：E1(t0) + out1(t0+1h) + out2(t0+2h) 为最旧 3 行（进 ASC
        # 前 5），E2(t0+3h)、E3(t0+4h) 也进；E4/E5/E6 最_new，被 cap 丢弃。
        task = uuid4()
        _, dec = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="a", at=_T0)
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1))
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=2))
        for i, hours in enumerate((3, 4, 5, 6, 7)):
            await _expose(
                db_session,
                user,
                intervention_type="practice",
                salt=f"e{i}",
                at=_T0 + timedelta(hours=hours),
            )

        monkeypatch.setattr(d05_module, "_SUMMARY_EVENT_CAP", 5, raising=False)

        projector = ExperienceMemoryProjector(db_session)
        projection = await projector.project(user_id=user.id, now=_NOW, use_cache=False)

        n_rows = (await db_session.execute(InterventionLifecycleEvent.__table__.select())).fetchall()
        assert len(n_rows) == 8  # 1 exposure+2 outcome+5 exposure = 8 行

        assert projection.truncated is True
        assert projection.truncation_reason == SUMMARY_TRUNCATION_REASON
        rescope = next(r for r in projection.records if r.intervention == "rescope")
        assert rescope.evidence_strength == EVIDENCE_TIER_REPEATED  # D-05 原档位保留
        assert rescope.completeness_adjusted_strength == "single_observation"  # 降一级
        assert rescope.to_dict()["truncated"] is True

        # 检索面：degraded_confidence
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        assert result.truncated is True
        assert result.to_dict()["degraded_confidence"]["reason"] == SUMMARY_TRUNCATION_REASON

    async def test_under_cap_summary_not_truncated(self, db_session):
        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p")

        projector = ExperienceMemoryProjector(db_session)
        projection = await projector.project(user_id=user.id, now=_NOW, use_cache=False)
        assert projection.truncated is False
        assert projection.records[0].completeness_adjusted_strength == projection.records[0].evidence_strength


# ---------------------------------------------------------------------------
# 6. D-05 消费面缓存（watermark 失效 + TTL 兜底）
# ---------------------------------------------------------------------------


class TestProjectionCache:
    async def test_watermark_hit_and_invalidation(self, db_session, monkeypatch):
        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p1")

        calls = {"n": 0}
        original = InterventionLifecycleService.association_summary

        async def counting_summary(self, **kwargs):
            calls["n"] += 1
            return await original(self, **kwargs)

        monkeypatch.setattr(InterventionLifecycleService, "association_summary", counting_summary)

        projector = ExperienceMemoryProjector(db_session)
        first = await projector.project(user_id=user.id, now=_NOW)
        second = await projector.project(user_id=user.id, now=_NOW)
        assert calls["n"] == 1  # 命中缓存：事件集未变
        assert second == first

        # 新事件 → watermark 变化 → 失效重投影
        await _expose(db_session, user, intervention_type="remind", salt="p2")
        third = await projector.project(user_id=user.id, now=_NOW)
        assert calls["n"] == 2
        assert {r.intervention for r in third.records} == {"practice", "remind"}

    async def test_cohort_flag_isolated_cache_entries(self, db_session):
        """R2 P2-1 回归钉：global scope 下 cohort 旗标必须分键缓存——
        先 include_demo_cohort=True 再 False（暖缓存背靠背）不得命中彼此
        条目，demo cohort 行不得泄入显式排除调用，双向皆然。"""
        guest = await _make_user(db_session, registration_source="guest")
        human = await _make_user(db_session)
        await _expose(db_session, guest, intervention_type="remind", salt="g1")
        await _expose(db_session, human, intervention_type="rescope", salt="h1")

        projector = ExperienceMemoryProjector(db_session)
        both = await projector.project(user_id=None, now=_NOW, include_demo_cohort=True)
        assert {r.intervention for r in both.records} == {"remind", "rescope"}

        excluded = await projector.project(user_id=None, now=_NOW, include_demo_cohort=False)
        assert {r.intervention for r in excluded.records} == {"rescope"}

        again = await projector.project(user_id=None, now=_NOW, include_demo_cohort=True)
        assert {r.intervention for r in again.records} == {"remind", "rescope"}

        # 两旗标各占独立缓存键（修复本体：键并入 |demo= 旗标）
        suffixes = {key.rsplit("|demo=", 1)[-1] for key in ExperienceMemoryProjector._cache}
        assert suffixes == {"0", "1"}

    async def test_ttl_bounds_staleness(self, db_session):
        """TTL 兜底：条目过期后即使 watermark 不变也重算（FIX-31 P3-1 盲区上界）。"""
        import time as _time

        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p")

        projector = ExperienceMemoryProjector(db_session)
        await projector.project(user_id=user.id, now=_NOW)

        cache_key = "{}|demo=0".format(
            InterventionLifecycleService.summary_cache_key(user_id=user.id, since=None, until=None)
        )
        assert cache_key in ExperienceMemoryProjector._cache
        watermark, projection, computed_at = ExperienceMemoryProjector._cache[cache_key]
        # 人工老化条目（TTL 边界）
        ExperienceMemoryProjector._cache[cache_key] = (
            watermark,
            projection,
            _time.monotonic() - CACHE_TTL_SECONDS - 1,
        )
        aged = projector._cache_get(cache_key, watermark)
        assert aged is None

    async def test_use_cache_false_bypasses_cache(self, db_session, monkeypatch):
        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p")

        calls = {"n": 0}
        original = InterventionLifecycleService.association_summary

        async def counting_summary(self, **kwargs):
            calls["n"] += 1
            return await original(self, **kwargs)

        monkeypatch.setattr(InterventionLifecycleService, "association_summary", counting_summary)
        projector = ExperienceMemoryProjector(db_session)
        await projector.project(user_id=user.id, now=_NOW, use_cache=False)
        await projector.project(user_id=user.id, now=_NOW, use_cache=False)
        assert calls["n"] == 2


# ---------------------------------------------------------------------------
# 7. M-03 真实预筛接线（权限面真实生效）
# ---------------------------------------------------------------------------


class TestPrefilterEnforcement:
    async def test_disable_episodic_cuts_all_experience_records(self, db_session):
        from app.models.user_memory_settings import UserMemorySettings

        user = await _make_user(db_session)
        task = uuid4()
        _, dec = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="a")
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1))

        db_session.add(UserMemorySettings(user_id=user.id, allow_episodic=False))
        await db_session.commit()

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        # 投影有记录，但 M-03 预筛在输出边界把它们全部砍除（真实权限生效）
        assert result.observed_with_positive == ()
        payload = result.prefilter_payloads[DIRECTION_POSITIVE]
        assert payload["input_count"] == 1
        assert payload["allowed_count"] == 0
        assert payload["reason_counts"].get("purpose:type_disabled") == 1

    async def test_default_settings_allow_records_with_prefilter_payload(self, db_session):
        user = await _make_user(db_session)
        task = uuid4()
        _, dec = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="a")
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1))

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        assert len(result.observed_with_positive) == 1
        payload = result.prefilter_payloads[DIRECTION_POSITIVE]
        assert payload["version"].startswith("memory-v3.m03")  # 真实 M-03 版本面
        assert payload["allowed_count"] == 1

    async def test_invalid_purpose_rejected(self, db_session):
        user = await _make_user(db_session)
        projector = ExperienceMemoryProjector(db_session)
        with pytest.raises(ValueError, match="unknown retrieval purpose"):
            await projector.retrieve_context(ExperienceContextQuery(user_id=str(user.id), purpose="not_a_purpose"))

    async def test_missing_user_id_rejected(self, db_session):
        projector = ExperienceMemoryProjector(db_session)
        with pytest.raises(ValueError, match="user_id is required"):
            await projector.retrieve_context(ExperienceContextQuery(user_id=""))


# ---------------------------------------------------------------------------
# 8. M-05 usage selfcheck 接线（输出面链路不弱化）
# ---------------------------------------------------------------------------


class TestSelfcheckWiring:
    async def test_records_flow_through_real_selfcheck(self, db_session):
        user = await _make_user(db_session)
        task = uuid4()
        _, dec = await _expose(db_session, user, intervention_type="rescope", task_id=task, salt="a")
        await _link_outcome(db_session, user, dec, task, polarity=OutcomePolarity.POSITIVE, at=_T0 + timedelta(hours=1))

        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW)
        )
        records = result.observed_with_positive + result.no_outcome_evidence

        candidates = to_selfcheck_candidates(records)
        assert all(c.section == "episodic" for c in candidates)
        assert all(c.item_id == r.record_id for c, r in zip(candidates, records, strict=True))

        gate = await run_experience_use_selfcheck(records, ctx=SelfCheckContext(user_message="这道题怎么复习"))
        assert gate.input_count == len(records)
        decisions = {d.candidate.item_id for d in gate.decisions}
        assert decisions == {r.record_id for r in records}  # 全部经真实 M-05 决策


# ---------------------------------------------------------------------------
# 9. 零写路径（投影层不产任何行/事件）
# ---------------------------------------------------------------------------


class TestZeroWritePath:
    async def test_projection_writes_nothing(self, db_session):
        from sqlalchemy import text

        user = await _make_user(db_session)
        await _expose(db_session, user, intervention_type="practice", salt="p")

        async def _count(table: str) -> int:
            return (await db_session.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()

        before = {
            "intervention_lifecycle_events": await _count("intervention_lifecycle_events"),
            "episodic_memories": await _count("episodic_memories"),
            "event_outbox": await _count("event_outbox") if await _table_exists(db_session, "event_outbox") else 0,
        }

        projector = ExperienceMemoryProjector(db_session)
        projection = await projector.project(user_id=user.id, now=_NOW)
        await projector.retrieve_context(ExperienceContextQuery(user_id=str(user.id), goal_type="exam", now=_NOW))
        assert len(projection.records) == 1

        after = {
            "intervention_lifecycle_events": await _count("intervention_lifecycle_events"),
            "episodic_memories": await _count("episodic_memories"),
            "event_outbox": await _count("event_outbox") if await _table_exists(db_session, "event_outbox") else 0,
        }
        assert before == after  # 只读投影：零新行、零事件


async def _table_exists(db_session, name: str) -> bool:
    from sqlalchemy import inspect

    def _check(sync_conn):
        return inspect(sync_conn).has_table(name)

    connection = await db_session.connection()
    return await connection.run_sync(_check)
