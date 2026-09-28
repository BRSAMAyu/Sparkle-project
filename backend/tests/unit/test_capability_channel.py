"""V4-D04 · 能力通道分类契约（纯函数；「练习过 vs 独立检验通过」显式映射）.

卡面验收：只学习计时不显示掌握；Agent产物不计人类能力。
每面一正一反可失败；TruthClass 全 5 值映射显式钉死（I01 口径对齐）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.core.outcome_ledger import (
    EvidenceRole,
    OutcomeEntry,
    OutcomeEvidence,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.services.galaxy.capability_channel import (
    TRUTH_CLASS_CHANNELS,
    CapabilityChannel,
    classify_outcome_channel,
    fusion_observation_params,
    node_capability_channel,
)
from app.services.galaxy.mastery_evidence import MasteryEvidenceType


def _entry(
    *,
    truth: TruthClass,
    evidence: tuple[OutcomeEvidence, ...] = (),
    source: OutcomeSource = OutcomeSource.TASK_COMPLETION,
) -> OutcomeEntry:
    task_id = uuid4()
    return OutcomeEntry(
        outcome_id=derive_outcome_id(source=source, source_id=task_id),
        source=source,
        source_id=str(task_id),
        user_id=str(uuid4()),
        occurred_at=datetime(2026, 9, 28, 10, 0, 0),
        truth_class=truth,
        polarity=OutcomePolarity.POSITIVE,
        source_ref=f"task://{task_id}",
        correlation={"task_id": str(task_id)},
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# TruthClass → 通道：全 5 值显式（I01 last_valid_outcome 口径对齐，demo 透传）
# ---------------------------------------------------------------------------


def test_truth_class_channel_map_covers_all_five_values():
    """正例：TruthClass 全 5 值在映射词表内显式可判（demo 含——透传但不贡献）。"""
    assert {t.value for t in TruthClass} == {"actual", "self_reported", "estimated", "demo", "unknown"}
    assert TRUTH_CLASS_CHANNELS[TruthClass.SELF_REPORTED] is CapabilityChannel.PRACTICED
    assert TRUTH_CLASS_CHANNELS[TruthClass.ESTIMATED] is CapabilityChannel.TRACE_ONLY
    assert TRUTH_CLASS_CHANNELS[TruthClass.DEMO] is CapabilityChannel.TRACE_ONLY
    assert TRUTH_CLASS_CHANNELS[TruthClass.UNKNOWN] is CapabilityChannel.TRACE_ONLY


def test_actual_not_in_static_map_requires_evidence_refinement():
    """反例：ACTUAL 不得有静态通道——必须按证据面细化（人检 vs Agent 产物）。"""
    assert TruthClass.ACTUAL not in TRUTH_CLASS_CHANNELS
    # 且细化不是摆设：同为 ACTUAL，证据面不同通道不同。
    quiz = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="quiz_feedback", ref="quiz_feedback://1", evidence_kind="quiz_result",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    receipt = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="agent_run_receipt", ref="agent_run://1", evidence_kind="system_event",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    assert classify_outcome_channel(source="task_completion", entry=quiz) is CapabilityChannel.VERIFIED
    assert classify_outcome_channel(source="task_completion", entry=receipt) is CapabilityChannel.NON_HUMAN


# ---------------------------------------------------------------------------
# 源级映射
# ---------------------------------------------------------------------------


def test_quiz_source_is_verified_and_time_sources_are_trace_only():
    """正例：独立测验 → VERIFIED；纯时长源（focus/study_record）→ 活动痕迹。"""
    assert classify_outcome_channel(source="quiz_feedback", entry=None) is CapabilityChannel.VERIFIED
    assert classify_outcome_channel(source="focus_session", entry=None) is CapabilityChannel.TRACE_ONLY
    assert classify_outcome_channel(source="study_record", entry=None) is CapabilityChannel.TRACE_ONLY


def test_unknown_source_fails_closed_to_trace_only():
    """反例：词表外来源 fail-closed 归活动痕迹（宁缺勿造能力）。"""
    assert classify_outcome_channel(source="mystery_stream", entry=None) is CapabilityChannel.TRACE_ONLY


def test_run_receipt_source_is_non_human_even_with_verified_entry():
    """正例（Agent 产物隔离）：run receipt 事件面 → 永远 NON_HUMAN。"""
    verified_entry = _entry(
        source=OutcomeSource.QUIZ_FEEDBACK,
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="quiz_feedback", ref="quiz_feedback://1", evidence_kind="quiz_result",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    assert (
        classify_outcome_channel(source="run_receipt", entry=verified_entry)
        is CapabilityChannel.NON_HUMAN
    )


# ---------------------------------------------------------------------------
# task_completion 细化
# ---------------------------------------------------------------------------


def test_task_without_ledger_entry_is_practiced():
    """正例：账本条目不可得（未命中）→ PRACTICED（参与可见、能力不声称）。"""
    assert classify_outcome_channel(source="task_completion", entry=None) is CapabilityChannel.PRACTICED


def test_task_self_reported_is_practiced():
    """正例：点击完成（self_reported）→ 练习过。"""
    entry = _entry(truth=TruthClass.SELF_REPORTED)
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.PRACTICED


def test_task_actual_with_quiz_is_verified():
    """正例：ACTUAL + quiz 物化 → 独立检验通过。"""
    entry = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="quiz_feedback", ref="quiz_feedback://1", evidence_kind="quiz_result",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.VERIFIED


def test_task_actual_with_resolved_artifact_is_verified():
    """正例：ACTUAL + 已解析 verifiable 产物（artifact/file）→ 独立检验通过。"""
    entry = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="declared_ref", ref="document://f1", evidence_kind="artifact",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.VERIFIED


def test_task_actual_with_focus_only_is_practiced_not_verified():
    """反例（时长不显示掌握）：ACTUAL 仅由 focus 覆盖支撑 → 练习过，不是检验通过。"""
    entry = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="focus_session", ref="focus_session://1", evidence_kind="system_event",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
        ),
    )
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.PRACTICED


def test_task_actual_receipt_only_is_non_human():
    """反例（Agent 产物不计人类能力）：X-08 receipt 升格的 ACTUAL → NON_HUMAN。"""
    entry = _entry(
        truth=TruthClass.ACTUAL,
        evidence=(
            OutcomeEvidence(
                source="agent_run_receipt", ref="agent_run://1", evidence_kind="system_event",
                role=EvidenceRole.INDEPENDENT, verified=True,
            ),
            # pipeline echo 不改变判定
            OutcomeEvidence(
                source="study_record", ref="study_record://1", evidence_kind="system_event",
                role=EvidenceRole.PIPELINE_ECHO, verified=False,
            ),
        ),
    )
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.NON_HUMAN


def test_task_actual_with_unreadable_evidence_fails_closed():
    """反例：ACTUAL 但证据面完全不可读 → TRACE_ONLY（fail-closed，不声称能力）。"""
    entry = _entry(truth=TruthClass.ACTUAL, evidence=())
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.TRACE_ONLY


def test_task_corrupt_truth_class_fails_closed():
    """反例：账本行 truth_class 损坏 → TRACE_ONLY。"""
    entry = _entry(truth=TruthClass.UNKNOWN)
    assert classify_outcome_channel(source="task_completion", entry=entry) is CapabilityChannel.TRACE_ONLY


# ---------------------------------------------------------------------------
# 融合参数：只有 VERIFIED 产观察，其余一律 None
# ---------------------------------------------------------------------------


def test_fusion_params_only_for_verified():
    """正例：VERIFIED×task → TASK_OUTCOME 观察值（60/0.8 既有常量）。"""
    params = fusion_observation_params(CapabilityChannel.VERIFIED, source="task_completion")
    assert params is not None
    assert params[0] is MasteryEvidenceType.TASK_OUTCOME
    assert params[1] == 60.0 and params[2] == 0.8
    quiz_params = fusion_observation_params(CapabilityChannel.VERIFIED, source="quiz_feedback")
    assert quiz_params is not None and quiz_params[0] is MasteryEvidenceType.QUIZ


def test_fusion_params_none_for_practiced_non_human_trace():
    """反例：练习/Agent 产物/痕迹通道永不产融合观察（零掌握度效果）。"""
    for channel in (CapabilityChannel.PRACTICED, CapabilityChannel.NON_HUMAN, CapabilityChannel.TRACE_ONLY):
        assert fusion_observation_params(channel, source="task_completion") is None


# ---------------------------------------------------------------------------
# 节点级通道标签
# ---------------------------------------------------------------------------


def test_node_channel_verified_requires_verification_grade_evidence():
    assert node_capability_channel(verified_evidence_count=2, unlocked=True) == "verified"


def test_node_channel_practiced_for_zero_or_unknown_counts():
    """反例：零检验证据（含 legacy 存量）与计数面不可得都标 practiced，不称检验。"""
    assert node_capability_channel(verified_evidence_count=0, unlocked=True) == "practiced"
    assert node_capability_channel(verified_evidence_count=None, unlocked=True) == "practiced"


def test_node_channel_none_for_locked_nodes():
    assert node_capability_channel(verified_evidence_count=5, unlocked=False) is None


@pytest.mark.parametrize(
    "channel", [CapabilityChannel.VERIFIED, CapabilityChannel.PRACTICED, CapabilityChannel.NON_HUMAN, CapabilityChannel.TRACE_ONLY]
)
def test_channel_vocabulary_closed(channel: CapabilityChannel):
    """词表封闭四值。"""
    assert channel.value in {"verified", "practiced", "non_human", "trace_only"}
