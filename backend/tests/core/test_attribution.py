"""V4-D02 · 同域关联/统一观察窗/缺失语义/链路追踪 契约守卫（纯函数，无 DB、无模型）。

卡 V4-D02 验收（必须可失败——每条验收至少一个红转绿反例）：
1. 不同 ID 域不能拼接伪归因；unattributed 公开分母；
2. 超窗未回来不记失败（censored）；重复回放不加样本（幂等）；
3. UI→receipt→event→outcome 随机追踪可还原。

词表冻结纪律与 test_experience_event.py 同款：封闭集精确字面断言，新增成员不改
本测试 → 红。语义唯一真源断言：窗口=D-05、outcome 身份=D-02、事件身份=D01/B05。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.attribution import (
    ATTRIBUTION_DOMAINS,
    ATTRIBUTION_SCHEMA_VERSION,
    DOMAIN_CORRELATION_KEYS,
    AttributionDenominator,
    AttributionDomain,
    AttributionKeyError,
    AttributionStatus,
    DomainKey,
    UnattributedReason,
    UnjudgeableReason,
    anchor_observation_status,
    attribute_outcome,
    attribute_outcome_entry,
    domain_keys_from_correlation,
    trace_receipt_to_outcome,
)
from app.core.experience_event import (
    ExperienceCommitState,
    ExperienceEvent,
    ExperienceEventKind,
    ExperiencePresentation,
    ExperienceSubject,
)
from app.core.intervention_lifecycle import (
    DEFAULT_OBSERVATION_WINDOW_HOURS,
    USER_RESPONSE_EVENT_TYPES,
    LifecycleEventType,
    ObservationStatus,
    derive_lifecycle_event_id,
    resolve_observation_status,
)
from app.core.outcome_ledger import OutcomeSource, derive_outcome_id

_T0 = datetime(2026, 9, 28, 10, 0, 0)  # naive UTC 锚点时刻


def _key(domain: AttributionDomain) -> DomainKey:
    return DomainKey(domain=domain, value=str(uuid4()))


def _outcome_payload(
    *,
    outcome_id: str,
    source: OutcomeSource = OutcomeSource.STUDY_RECORD,
    source_id: str | None = None,
    correlation: dict | None = None,
    occurred_at: datetime = _T0 + timedelta(hours=2),
) -> dict:
    sid = source_id or uuid4().hex
    return {
        "outcome_id": outcome_id,
        "source": source.value,
        "source_id": sid,
        "correlation": correlation or {},
        "occurred_at": occurred_at,
    }


def _verdict(**overrides):
    values = {
        "anchor": _key(AttributionDomain.TASK),
        "outcome_key": None,
        "outcome_id": "outc_" + uuid4().hex[:16],
        "anchor_at": _T0,
        "outcome_at": _T0 + timedelta(hours=2),
        "now": _T0 + timedelta(hours=3),
    }
    values["outcome_key"] = values["anchor"]
    values.update(overrides)
    return attribute_outcome(**values)


# ---------------------------------------------------------------------------
# 封闭词表（精确字面冻结）
# ---------------------------------------------------------------------------


class TestFrozenVocabularies:
    def test_domain_vocabulary_is_the_card_four(self):
        assert frozenset({"goal", "task", "occurrence", "run"}) == ATTRIBUTION_DOMAINS

    def test_unattributed_reason_vocabulary_is_closed_four(self):
        assert {r.value for r in UnattributedReason} == {
            "missing_key",
            "domain_mismatch",
            "no_same_domain_match",
            "outside_window",
        }

    def test_unjudgeable_reason_is_single_value(self):
        assert {r.value for r in UnjudgeableReason} == {"broken_row"}

    def test_domain_correlation_keys_literal_freeze(self):
        assert {d.value: list(names) for d, names in DOMAIN_CORRELATION_KEYS.items()} == {
            "goal": ["goal_id"],
            "task": ["task_id"],
            "occurrence": ["occurrence_id", "task_occurrence_id"],
            "run": ["run_id"],
        }

    def test_task_occurrence_id_never_in_task_domain(self):
        # DATA_AND_GRAPH 红线：「不能把 task_occurrence_id 当 Task.id」的表级钉死。
        assert "task_occurrence_id" not in DOMAIN_CORRELATION_KEYS[AttributionDomain.TASK]

    def test_response_vocabulary_is_d05_authority_with_explicit_edited(self):
        # DATA_AND_GRAPH「不填假 accepted」：edited 是显式成员，非 accepted 的伪装。
        assert frozenset({"accepted", "edited", "rejected", "started"}) == USER_RESPONSE_EVENT_TYPES
        assert LifecycleEventType.EDITED.value == "edited"

    def test_schema_version_pinned(self):
        assert ATTRIBUTION_SCHEMA_VERSION == "attribution.domain.v1"
        assert DEFAULT_OBSERVATION_WINDOW_HOURS == 72


# ---------------------------------------------------------------------------
# 验收 1 · 不同 ID 域不能拼接伪归因
# ---------------------------------------------------------------------------


class TestCrossDomainSpliceRejection:
    def test_identical_uuid_across_domains_never_links(self):
        """红转绿反例：同一 UUID 落在 task 与 occurrence 两域——形近不串归因。"""
        shared = str(uuid4())
        task_key = DomainKey(domain=AttributionDomain.TASK, value=shared)
        occ_key = DomainKey(domain=AttributionDomain.OCCURRENCE, value=shared)
        assert task_key.links(occ_key) is False
        assert occ_key.links(task_key) is False

    def test_cross_domain_verdict_is_unattributed_domain_mismatch(self):
        shared = str(uuid4())
        verdict = _verdict(
            anchor=DomainKey(domain=AttributionDomain.TASK, value=shared),
            outcome_key=DomainKey(domain=AttributionDomain.OCCURRENCE, value=shared),
        )
        assert verdict.status is AttributionStatus.UNATTRIBUTED
        assert verdict.reason == UnattributedReason.DOMAIN_MISMATCH.value
        assert verdict.matched_key is None and verdict.sample_id == ""

    def test_task_occurrence_id_only_projects_to_occurrence_domain(self):
        task_id = str(uuid4())
        occ_id = str(uuid4())
        keys = domain_keys_from_correlation({"task_id": task_id, "task_occurrence_id": occ_id})
        by_domain = {k.domain: k.value for k in keys}
        assert by_domain[AttributionDomain.TASK] == task_id
        assert by_domain[AttributionDomain.OCCURRENCE] == occ_id
        # occurrence id 永不伪装成 task 域键：
        assert all(k.value != occ_id for k in keys if k.domain is AttributionDomain.TASK)

    def test_bare_value_equality_alone_is_not_association(self):
        k1 = _key(AttributionDomain.RUN)
        k2 = DomainKey(domain=AttributionDomain.RUN, value=str(uuid4()))
        assert k1.links(k2) is False  # 同域不同值
        assert k1.links("not-a-key") is False  # 非键对象不链接

    def test_malformed_key_fails_loud_at_boundary(self):
        with pytest.raises(AttributionKeyError):
            DomainKey(domain=AttributionDomain.TASK, value="task_occurrence-9-not-uuid")
        with pytest.raises(AttributionKeyError):
            DomainKey(domain="galaxy", value=str(uuid4()))  # 词表外域

    def test_malformed_correlation_value_dropped_not_crash(self):
        keys = domain_keys_from_correlation({"task_id": "not-a-uuid", "run_id": str(uuid4())})
        assert [k.domain for k in keys] == [AttributionDomain.RUN]


class TestUnattributedPublicDenominator:
    def test_missing_key_is_unattributed_not_forced_not_dropped(self):
        verdict = _verdict(outcome_key=None)
        assert verdict.status is AttributionStatus.UNATTRIBUTED
        assert verdict.reason == UnattributedReason.MISSING_KEY.value

    def test_denominator_counts_every_eligible_event(self):
        """关联完整率分母 = 全体 eligible（含难配对事件），不可剔除制造 100%。"""
        anchor = _key(AttributionDomain.TASK)
        attributed = attribute_outcome(
            anchor=anchor,
            outcome_key=anchor,
            outcome_id="outc_hit",
            anchor_at=_T0,
            outcome_at=_T0 + timedelta(hours=1),
            now=_T0 + timedelta(hours=2),
        )
        missing = attribute_outcome(
            anchor=anchor,
            outcome_key=None,
            outcome_id="outc_nokey",
            anchor_at=_T0,
            outcome_at=_T0 + timedelta(hours=1),
            now=_T0 + timedelta(hours=2),
        )
        shared = str(uuid4())
        mismatch = attribute_outcome(
            anchor=anchor,
            outcome_key=DomainKey(domain=AttributionDomain.OCCURRENCE, value=shared),
            outcome_id="outc_splice",
            anchor_at=_T0,
            outcome_at=_T0 + timedelta(hours=1),
            now=_T0 + timedelta(hours=2),
        )
        denom = AttributionDenominator.from_verdicts([attributed, missing, mismatch])
        assert denom.n_eligible == 3
        assert denom.n_attributed == 1
        assert denom.n_unattributed == 2
        assert denom.unattributed_ratio == pytest.approx(2 / 3)
        assert denom.by_reason == {"missing_key": 1, "domain_mismatch": 1}
        payload = denom.to_dict()
        assert payload["unattributed_ratio"] == pytest.approx(2 / 3)
        assert payload["n_eligible"] == 3  # 公开面：全集可见

    def test_zero_eligible_ratio_is_none_no_zero_or_full_claim(self):
        denom = AttributionDenominator.from_verdicts([])
        assert denom.n_eligible == 0
        assert denom.unattributed_ratio is None
        assert denom.to_dict()["unattributed_ratio"] is None

    def test_broken_row_counts_as_unknown_face(self):
        verdict = _verdict(anchor_at=None)
        assert verdict.reason == UnjudgeableReason.BROKEN_ROW.value
        denom = AttributionDenominator.from_verdicts([verdict])
        assert denom.n_unknown == 1
        assert denom.by_reason["broken_row"] == 1

    def test_entry_level_uses_only_anchor_domain_key(self):
        anchor = _key(AttributionDomain.GOAL)
        goal_id = anchor.value
        outcome = _outcome_payload(
            outcome_id="outc_g",
            correlation={"goal_id": goal_id, "task_id": str(uuid4())},
        )
        verdict = attribute_outcome_entry(anchor=anchor, outcome=outcome, anchor_at=_T0, now=_T0 + timedelta(hours=1))
        assert verdict.status is AttributionStatus.ATTRIBUTED
        # goal 域锚点对纯 task 关联的 outcome 不归因（不同域不硬塞）：
        verdict2 = attribute_outcome_entry(
            anchor=anchor,
            outcome=_outcome_payload(outcome_id="outc_t", correlation={"task_id": str(uuid4())}),
            anchor_at=_T0,
            now=_T0 + timedelta(hours=1),
        )
        assert verdict2.status is AttributionStatus.UNATTRIBUTED
        assert verdict2.reason == UnattributedReason.MISSING_KEY.value


# ---------------------------------------------------------------------------
# 验收 2 · 超窗 censored（绝不记失败）+ 延迟 outcome + 重放幂等
# ---------------------------------------------------------------------------


class TestObservationWindowCensored:
    def test_outcome_beyond_window_is_outside_window_and_anchor_censored(self):
        """红转绿反例：超窗 outcome 既不归因、锚点也绝不记失败（censored）。"""
        anchor = _key(AttributionDomain.TASK)
        verdict = attribute_outcome(
            anchor=anchor,
            outcome_key=anchor,
            outcome_id="outc_late",
            anchor_at=_T0,
            outcome_at=_T0 + timedelta(hours=73),  # 72h 窗外 1h
            now=_T0 + timedelta(hours=80),
            user_last_active_at=_T0 + timedelta(hours=79),  # 用户在场而未行动
        )
        assert verdict.status is AttributionStatus.UNATTRIBUTED
        assert verdict.reason == UnattributedReason.OUTSIDE_WINDOW.value
        assert verdict.observation_status is ObservationStatus.CENSORED_WINDOW_CLOSED
        # 删失 ≠ 失败：判定结果里不存在任何 negative/failed 语义位
        assert verdict.status.value != "failed"

    def test_window_not_yet_due_is_censored_not_failure(self):
        status = anchor_observation_status(
            domain=AttributionDomain.OCCURRENCE,
            anchor_id=str(uuid4()),
            anchor_at=_T0,
            window_hours=72,
            outcome_times=(),
            now=_T0 + timedelta(hours=1),
        )
        assert status is ObservationStatus.CENSORED_NOT_YET_DUE

    def test_churned_user_after_window_is_censored_churned(self):
        status = anchor_observation_status(
            domain=AttributionDomain.GOAL,
            anchor_id=str(uuid4()),
            anchor_at=_T0,
            window_hours=72,
            outcome_times=(),
            now=_T0 + timedelta(hours=80),
            user_last_active_at=_T0 + timedelta(hours=10),  # 窗内即流失
        )
        assert status is ObservationStatus.CENSORED_USER_CHURNED

    def test_delayed_outcome_within_window_is_attributed(self):
        """延迟 outcome：真实事件时间在窗内即归因（received 延迟不改写事实时间）。"""
        anchor = _key(AttributionDomain.RUN)
        verdict = attribute_outcome(
            anchor=anchor,
            outcome_key=anchor,
            outcome_id="outc_delayed",
            anchor_at=_T0,
            outcome_at=_T0 + timedelta(hours=71),
            now=_T0 + timedelta(hours=100),  # 很晚才收到
        )
        assert verdict.status is AttributionStatus.ATTRIBUTED
        assert verdict.observation_status is ObservationStatus.OBSERVED

    def test_outcome_before_anchor_never_retro_attributed(self):
        anchor = _key(AttributionDomain.TASK)
        verdict = attribute_outcome(
            anchor=anchor,
            outcome_key=anchor,
            outcome_id="outc_pre",
            anchor_at=_T0,
            outcome_at=_T0 - timedelta(hours=1),  # 早于锚点：时序倒置
            now=_T0 + timedelta(hours=2),
        )
        assert verdict.status is AttributionStatus.UNATTRIBUTED
        assert verdict.reason == UnattributedReason.OUTSIDE_WINDOW.value

    def test_unified_window_matches_d05_authority_for_all_four_domains(self):
        """统一观察窗 = D-05 权威逐值委托（反第二权威）：四域同输入恒同输出。"""
        for domain in AttributionDomain:
            args = {
                "domain": domain,
                "anchor_id": str(uuid4()),
                "anchor_at": _T0,
                "window_hours": 72,
                "outcome_times": (_T0 + timedelta(hours=5),),
                "now": _T0 + timedelta(hours=6),
            }
            assert anchor_observation_status(**args) == resolve_observation_status(
                exposed_at=args["anchor_at"],
                window_hours=72,
                outcome_times=args["outcome_times"],
                now=args["now"],
            )

    def test_window_facade_rejects_out_of_vocabulary_domain(self):
        with pytest.raises(AttributionKeyError):
            anchor_observation_status(domain="galaxy", anchor_id=str(uuid4()), anchor_at=_T0, window_hours=72, now=_T0)

    def test_broken_anchor_row_is_unknown(self):
        status = anchor_observation_status(
            domain=AttributionDomain.TASK,
            anchor_id=str(uuid4()),
            anchor_at=None,
            window_hours=72,
            now=_T0,
            anchor_valid=False,
        )
        assert status is ObservationStatus.UNKNOWN


class TestReplayIdempotency:
    def test_replay_produces_identical_verdict_and_sample_id(self):
        """同一事件/回执重放（now 不同）恒同 verdict、恒同样本 id——样本不虚增。"""
        anchor = _key(AttributionDomain.TASK)
        kwargs = {
            "anchor": anchor,
            "outcome_key": anchor,
            "outcome_id": "outc_once",
            "anchor_at": _T0,
            "outcome_at": _T0 + timedelta(hours=2),
        }
        first = attribute_outcome(now=_T0 + timedelta(hours=3), **kwargs)
        replay = attribute_outcome(now=_T0 + timedelta(hours=50), **kwargs)  # 很久后重放
        assert first.sample_id == replay.sample_id
        assert first.to_dict() == replay.to_dict()

    def test_consumer_dedup_by_sample_id_counts_once(self):
        anchor = _key(AttributionDomain.OCCURRENCE)
        kwargs = {
            "anchor": anchor,
            "outcome_key": anchor,
            "outcome_id": "outc_dedupe",
            "anchor_at": _T0,
            "outcome_at": _T0 + timedelta(hours=2),
            "now": _T0 + timedelta(hours=3),
        }
        deliveries = [attribute_outcome(**kwargs) for _ in range(5)]  # at-least-once 重放 5 次
        unique_samples = {v.sample_id for v in deliveries}
        assert len(unique_samples) == 1
        denom = AttributionDenominator.from_verdicts(deliveries)
        assert denom.n_eligible == 5  # 投递次数如实入分母（观测面）
        assert len(unique_samples) == 1  # 样本身份去重后恰 1 个（归因面不虚增）

    def test_different_outcomes_have_distinct_sample_ids(self):
        anchor = _key(AttributionDomain.TASK)
        ids = {
            attribute_outcome(
                anchor=anchor,
                outcome_key=anchor,
                outcome_id=f"outc_{i}",
                anchor_at=_T0,
                outcome_at=_T0 + timedelta(hours=1),
                now=_T0 + timedelta(hours=2),
            ).sample_id
            for i in range(3)
        }
        assert len(ids) == 3

    def test_edited_and_accepted_are_distinct_event_identities(self):
        """「明确 edited 迁移」：edited 事件与 accepted 事件身份不同、互不改写。"""
        decision_id = "aurora_" + "ab" * 16
        edited_id = derive_lifecycle_event_id(decision_id=decision_id, event_type="edited")
        accepted_id = derive_lifecycle_event_id(decision_id=decision_id, event_type="accepted")
        assert edited_id != accepted_id
        # 幂等面：同 (decision, event_type) 重放恒同 id。
        assert derive_lifecycle_event_id(decision_id=decision_id, event_type="edited") == edited_id


# ---------------------------------------------------------------------------
# 验收 3 · UI→receipt→event→outcome 随机追踪可还原
# ---------------------------------------------------------------------------


def _projected_event(*, receipt_ref: str | None, subject_id: str, version_token: str = "cv1") -> ExperienceEvent:
    return ExperienceEvent.project(
        kind=ExperienceEventKind.STATE_CONFIRMED.value,
        commit_state=ExperienceCommitState.COMMITTED.value,
        receipt_ref=receipt_ref,
        subject=ExperienceSubject(type="task", id=subject_id, version_token=version_token),
        presentation=ExperiencePresentation(modalities=("visual",), copy_key="outcome.confirmed"),
        issued_at=_T0,
        expires_at=None,
    )


class TestTraceReceiptToOutcome:
    def test_random_sample_full_chain_restore(self):
        """随机取样本（uuid4）：UI(event_id) → receipt_ref → event → outcome 全链还原。"""
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=sid)
        receipt_ref = f"outcome://{outcome_id}"
        task_id = str(uuid4())
        event = _projected_event(receipt_ref=receipt_ref, subject_id=task_id)
        outcome = _outcome_payload(outcome_id=outcome_id, source_id=sid)

        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=outcome)
        assert report.traceable is True
        assert [hop.hop for hop in report.hops] == [
            "receipt_ref_scheme",
            "event_identity",
            "outcome_identity",
            "outcome_link",
        ]
        assert all(hop.ok for hop in report.hops)
        # 确定性：同链路重放 trace 恒同（随机样本可复现还原）。
        again = trace_receipt_to_outcome(event=event.to_dict(), outcome=outcome)
        assert again.to_dict() == report.to_dict()

    def test_mutated_event_breaks_chain_loudly(self):
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=sid)
        event = _projected_event(receipt_ref=f"outcome://{outcome_id}", subject_id=str(uuid4()))
        payload = dict(event.to_dict())
        payload["event_id"] = "eev_forged" + "0" * 28  # 存储行被篡改
        report = trace_receipt_to_outcome(event=payload, outcome=_outcome_payload(outcome_id=outcome_id, source_id=sid))
        assert report.traceable is False
        identity_hop = next(h for h in report.hops if h.hop == "event_identity")
        assert identity_hop.ok is False
        assert "does not match recomputed" in identity_hop.detail

    def test_event_without_receipt_ref_reports_broken_first_hop(self):
        event = ExperienceEvent.project(
            kind=ExperienceEventKind.STATE_SYNCING.value,
            commit_state=ExperienceCommitState.COMMITTED.value,
            receipt_ref=None,
            subject=ExperienceSubject(type="task", id=str(uuid4()), version_token="cv1"),
            presentation=ExperiencePresentation(modalities=(), copy_key="task.syncing"),
            issued_at=_T0,
            expires_at=None,
        )
        report = trace_receipt_to_outcome(event=event.to_dict())
        assert report.traceable is False
        first = report.hops[0]
        assert first.hop == "receipt_ref_scheme" and first.ok is False
        assert "no receipt_ref" in first.detail

    def test_missing_outcome_is_explicit_incomplete_chain(self):
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid)
        event = _projected_event(receipt_ref=f"outcome://{outcome_id}", subject_id=str(uuid4()))
        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=None)
        assert report.traceable is False
        assert report.hops[-1].detail == "no outcome provided (chain incomplete)"

    def test_stored_outcome_id_mismatch_fails_outcome_identity(self):
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid)
        event = _projected_event(receipt_ref=f"outcome://{outcome_id}", subject_id=str(uuid4()))
        wrong = _outcome_payload(outcome_id="outc_" + "f" * 32, source_id=sid)
        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=wrong)
        assert report.traceable is False
        outcome_hop = next(h for h in report.hops if h.hop == "outcome_identity")
        assert outcome_hop.ok is False

    def test_same_domain_anchor_link_restores_chain(self):
        """receipt_ref 非 outcome 面（intervention_lifecycle）时，经同域键还原 outcome。"""
        decision_id = "aurora_" + "cd" * 16
        task_id = str(uuid4())
        event = _projected_event(receipt_ref=f"intervention_lifecycle://{decision_id}", subject_id=task_id)
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid)
        outcome = _outcome_payload(
            outcome_id=outcome_id, source=OutcomeSource.TASK_COMPLETION, source_id=sid, correlation={"task_id": task_id}
        )
        anchor = DomainKey(domain=AttributionDomain.TASK, value=task_id)
        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=outcome, anchor=anchor)
        assert report.traceable is True
        link_hop = report.hops[-1]
        assert link_hop.ok is True and "same-domain" in link_hop.detail
        # 跨域锚点（occurrence 域）即使持同值 UUID 也不得完成链路：
        splice_anchor = DomainKey(domain=AttributionDomain.OCCURRENCE, value=task_id)
        splice_report = trace_receipt_to_outcome(event=event.to_dict(), outcome=outcome, anchor=splice_anchor)
        assert splice_report.traceable is False

    def test_exposure_linkage_path_uses_d05_authority(self):
        decision_id = "aurora_" + "ee" * 16
        event = _projected_event(receipt_ref=f"intervention_lifecycle://{decision_id}", subject_id=str(uuid4()))
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.FOCUS_SESSION, source_id=sid)
        linkage = {"task_id": str(uuid4())}
        outcome = _outcome_payload(
            outcome_id=outcome_id,
            source=OutcomeSource.FOCUS_SESSION,
            source_id=sid,
            correlation={"task_id": linkage["task_id"]},
        )
        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=outcome, exposure_linkage=linkage)
        assert report.traceable is True
        assert report.hops[-1].ok is True and "D-05" in report.hops[-1].detail

    def test_receipt_pointing_at_other_outcome_fails_link(self):
        sid = uuid4().hex
        outcome_id = derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=sid)
        event = _projected_event(receipt_ref=f"outcome://{outcome_id}", subject_id=str(uuid4()))
        other_sid = uuid4().hex
        other_id = derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=other_sid)
        other = _outcome_payload(outcome_id=other_id, source_id=other_sid)
        report = trace_receipt_to_outcome(event=event.to_dict(), outcome=other)
        assert report.traceable is False
        link_hop = report.hops[-1]
        assert link_hop.ok is False and "points at" in link_hop.detail
