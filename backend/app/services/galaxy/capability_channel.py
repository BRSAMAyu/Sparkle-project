"""V4-D04 · 星图能力通道分类 —— 「练习过」与「独立检验通过」的显式分离。

设计真源：``v4/03_intelligence/DATA_AND_GRAPH.md`` §星图权威：

    能力证据与活动轨迹分离。旧时间累计亮度可作为"参与足迹"，标签不能叫精通；
    独立测验/修正过的练习证据才能支撑相应能力描述。遗忘估计标模型估计，
    不把没登录等于能力下降。

卡 V4-D04（implementation · normal，锁 galaxy-evidence）：

- **在关系型主星图中接有效 outcome**：有效 = D-02 账本真相面（查询时点重算的
  ``TruthClass``）× D-03 撤回投影（被撤回行经账本墓碑结构性零贡献，本模块不
  重复判定）。星图吸收器不再按裸极性（positive）点亮，而是先过本通道分类。
- **不另立第二归因/第二真相**：``TruthClass`` 唯一权威 = D-02
  ``app.core.outcome_ledger``（全 5 值 1:1 消费，与 I01
  ``last_valid_outcome.truth_class`` 同一口径，demo 透传不排除——但 demo
  **不贡献人类能力**）；outcome 条目读取只走 D-02 公共读面
  ``OutcomeLedgerService.query``（I01 同款有界扫描），不复制分级逻辑。
- **Agent 产物不计人类能力**：``run_receipt`` 事件面 outcome（X-08 run 终态
  receipt）以及真相仅由 ``agent_run://`` receipt 支撑的 task 完成行，归
  :attr:`CapabilityChannel.NON_HUMAN` ——只留溯源，永不融合、永不解锁。
  X-08 的 receipt→ACTUAL 升格语义是账本「工作真的发生了」的真相面，不是
  「人类能力得到独立检验」的能力面；星图消费后者。

封闭词表（新增即 bump ``CAPABILITY_CHANNEL_SCHEMA_VERSION`` 并过 reviewer）：

- :attr:`CapabilityChannel.VERIFIED`「独立检验通过」：独立测验（quiz 物化）或
  已解析产物（artifact/file 声明经解析验证）支撑 ——唯一允许融合掌握度后验、
  唯一允许展示 BRILLIANT/MASTERED 能力标签的通道；
- :attr:`CapabilityChannel.PRACTICED`「练习过」：真实的人类参与（自报完成、
  focus 覆盖的行为观察）——可解锁（参与足迹可见）、可留溯源，**永不**推进
  掌握度后验（时长型行为观察 ≠ 能力检验）；
- :attr:`CapabilityChannel.NON_HUMAN`「Agent 产物」：Agent 执行的工作成果——
  只留溯源，不解锁、不融合；
- :attr:`CapabilityChannel.TRACE_ONLY`「仅活动痕迹」：demo/模型估计/行损坏
  与纯时长源（focus/study_record 独立流）——只留痕迹。

TruthClass → 通道映射（显式、全 5 值钉死；ACTUAL 需证据面细化）：

============ ===========
TruthClass   通道
============ ===========
ACTUAL       证据面细化（人类独立检验 → VERIFIED / 仅 Agent receipt → NON_HUMAN /
             仅 focus 覆盖 → PRACTICED / 无法判定 → TRACE_ONLY）
SELF_REPORTED PRACTICED
ESTIMATED    TRACE_ONLY（模型估计，标估计不标能力）
DEMO         TRACE_ONLY（demo cohort 不计个人能力；I01 口径透传展示，星图不贡献）
UNKNOWN      TRACE_ONLY（行损坏 fail-closed，宁缺勿造）
============ ===========

本模块纯函数、零 IO、零 LLM；DB 读取面在吸收器
（``outcome_absorption_service``）。
"""

from __future__ import annotations

from enum import StrEnum

from app.core.outcome_ledger import (
    EVIDENCE_TRUST_TIERS,
    EvidenceRole,
    EvidenceTrustTier,
    OutcomeEntry,
    OutcomeSource,
    TruthClass,
)
from app.services.galaxy.mastery_evidence import MasteryEvidenceType

CAPABILITY_CHANNEL_SCHEMA_VERSION = "capability.channel.v1"

#: run receipt 事件面来源标签（X-08 ``outcome_capture_service`` 同款常量语义；
#: 这里引用其单一出处，不复制字面）。
from app.services.outcome_capture_service import RUN_RECEIPT_EVENT_SOURCE  # noqa: E402


class CapabilityChannel(StrEnum):
    """星图能力通道（封闭四值；语义见模块 docstring）。"""

    VERIFIED = "verified"  # 独立检验通过（独立测验 / 已解析产物）
    PRACTICED = "practiced"  # 练习过（真实人类参与，未独立检验）
    NON_HUMAN = "non_human"  # Agent 产物（不计人类能力）
    TRACE_ONLY = "trace_only"  # 仅活动痕迹（纯时长 / demo / 估计 / 行损坏）


#: TruthClass 静态映射（ACTUAL 除外——需证据面细化，见 :func:`classify_outcome_channel`）。
TRUTH_CLASS_CHANNELS: dict[TruthClass, CapabilityChannel] = {
    TruthClass.SELF_REPORTED: CapabilityChannel.PRACTICED,
    TruthClass.ESTIMATED: CapabilityChannel.TRACE_ONLY,
    TruthClass.DEMO: CapabilityChannel.TRACE_ONLY,
    TruthClass.UNKNOWN: CapabilityChannel.TRACE_ONLY,
}

#: 非任务源的静态通道（D-02 ``FIVE_SOURCE_MAP`` 封闭五源；未列来源 fail-closed
#: 归 TRACE_ONLY）：
#: - ``quiz_feedback``：独立测验 —— 独立检验的原型；
#: - ``behavioral``：M-06 服务器记录的行为结果（非时长型）——独立观察面；
#: - ``focus_session`` / ``study_record``（独立流）：纯时长/参与日志 —— 活动痕迹，
#:   「只学习计时不显示掌握」在此钉死。
NON_TASK_SOURCE_CHANNELS: dict[str, CapabilityChannel] = {
    OutcomeSource.QUIZ_FEEDBACK.value: CapabilityChannel.VERIFIED,
    OutcomeSource.BEHAVIORAL.value: CapabilityChannel.VERIFIED,
    OutcomeSource.FOCUS_SESSION.value: CapabilityChannel.TRACE_ONLY,
    OutcomeSource.STUDY_RECORD.value: CapabilityChannel.TRACE_ONLY,
}

#: task 完成条目上构成「人类独立检验」的附着证据源（D-02 ``OutcomeEvidence.source``
#: 词表）：quiz 物化行 + 已解析的声明产物。focus 覆盖**不在内**——它是时长型
#: 行为观察（练习证明），不是能力检验。
_HUMAN_VERIFICATION_EVIDENCE_SOURCES: frozenset[str] = frozenset({"quiz_feedback"})

#: Agent receipt 附着证据源（X-08 run receipt → ``agent_run://`` 引用）。
_AGENT_RECEIPT_EVIDENCE_SOURCE = "agent_run_receipt"


def _has_verified_declared_ref(entry: OutcomeEntry) -> bool:
    """条目是否携带已解析的 verifiable 档声明产物（artifact/file ref 已解析）。"""
    for item in entry.evidence:
        if item.source != "declared_ref" or not item.verified or item.role is not EvidenceRole.INDEPENDENT:
            continue
        kind = item.evidence_kind
        if kind is not None and EVIDENCE_TRUST_TIERS.get(kind) is EvidenceTrustTier.VERIFIABLE:
            return True
    return False


def classify_outcome_channel(*, source: str, entry: OutcomeEntry | None) -> CapabilityChannel:
    """一次 outcome 的星图能力通道判定（确定性全函数；未知输入 fail-closed）。

    判定顺序（逐条短路）：
    1. ``source`` 为 run receipt 事件面 → NON_HUMAN（Agent 产物不计人类能力，
       无需查账本——receipt 不是账本源，其真相面只是 task 条目上的附着证据）；
    2. 非任务源查 :data:`NON_TASK_SOURCE_CHANNELS`（缺员 fail-closed →
       TRACE_ONLY）；
    3. 任务源（task_completion）：
       - 无账本条目（D-02 公共读面有界扫描未命中：任务已删/超出扫描窗）→
         PRACTICED——参与可见、能力不声称（宁练习勿伪造检验）；
       - ``truth_class != ACTUAL`` → :data:`TRUTH_CLASS_CHANNELS` 静态映射；
       - ``ACTUAL``：按附着证据细化——存在人类独立检验（quiz 物化 / 已解析
         verifiable 产物）→ VERIFIED；仅有 Agent receipt（X-08 receipt 升格）
         → NON_HUMAN；仅 focus 覆盖 → PRACTICED（时长型行为观察）；证据面
         完全不可读 → TRACE_ONLY。
    """
    source_value = str(source or "")
    if source_value == RUN_RECEIPT_EVENT_SOURCE:
        return CapabilityChannel.NON_HUMAN
    if source_value != OutcomeSource.TASK_COMPLETION.value:
        return NON_TASK_SOURCE_CHANNELS.get(source_value, CapabilityChannel.TRACE_ONLY)

    if entry is None:
        # 账本条目不可得：参与主张仍成立（完成行曾存在并被捕获），能力主张不可证。
        return CapabilityChannel.PRACTICED
    try:
        truth = TruthClass(entry.truth_class)
    except ValueError:
        return CapabilityChannel.TRACE_ONLY
    if truth is not TruthClass.ACTUAL:
        return TRUTH_CLASS_CHANNELS[truth]

    has_human_verification = any(item.source in _HUMAN_VERIFICATION_EVIDENCE_SOURCES for item in entry.evidence)
    if not has_human_verification:
        has_human_verification = _has_verified_declared_ref(entry)
    if has_human_verification:
        return CapabilityChannel.VERIFIED

    has_agent_receipt = any(
        item.source == _AGENT_RECEIPT_EVIDENCE_SOURCE and item.role is EvidenceRole.INDEPENDENT
        for item in entry.evidence
    )
    has_focus = any(item.source == OutcomeSource.FOCUS_SESSION.value for item in entry.evidence)
    if has_agent_receipt:
        return CapabilityChannel.NON_HUMAN
    if has_focus:
        return CapabilityChannel.PRACTICED
    # ACTUAL 但证据面完全不可读（理论上不可达）：fail-closed，不声称任何能力。
    return CapabilityChannel.TRACE_ONLY


def fusion_observation_params(
    channel: CapabilityChannel, *, source: str
) -> tuple[MasteryEvidenceType, float, float] | None:
    """通道 → G-01 融合观察参数 ``(evidence_type, value, confidence)``；None = 不融合。

    - VERIFIED × task_completion：沿用 G-02 既有 TASK_OUTCOME 观察值
      （60 / 0.8——真实完成的完成质量证据，值为 ``outcome_absorption_service``
      常量的单一出处，不在此复制）；
    - VERIFIED × quiz_feedback：QUIZ 档观察（权重 1.0；值/置信与任务完成同档，
      quiz 事件当前无 ``outcome.recorded`` 生产者，映射为封闭词表的完备面）;
    - 其余一切通道 → None：练习/Agent 产物/痕迹永不推进掌握度后验。
    """
    if channel is not CapabilityChannel.VERIFIED:
        return None
    from app.services.galaxy.outcome_absorption_service import (
        TASK_OUTCOME_EVIDENCE_CONFIDENCE,
        TASK_OUTCOME_EVIDENCE_VALUE,
    )

    source_value = str(source or "")
    if source_value == OutcomeSource.QUIZ_FEEDBACK.value:
        return MasteryEvidenceType.QUIZ, TASK_OUTCOME_EVIDENCE_VALUE, TASK_OUTCOME_EVIDENCE_CONFIDENCE
    if source_value == OutcomeSource.TASK_COMPLETION.value:
        return MasteryEvidenceType.TASK_OUTCOME, TASK_OUTCOME_EVIDENCE_VALUE, TASK_OUTCOME_EVIDENCE_CONFIDENCE
    return None


#: 节点级能力通道展示词表（读面 ``MasteryEvidenceInfo.capability_channel`` 用）：
#: 节点有任一「独立检验」级证据行（quiz / task_outcome 账本行）→ verified，
#: 否则 practiced（含 legacy 时间存量——参与足迹，不声称检验）。
NODE_VERIFIED_EVIDENCE_REASONS: frozenset[str] = frozenset(
    {
        "evidence:quiz",
        "evidence:task_outcome",
        "exam_sprint_diagnostic",
        "post_exam_review_weak_node",
        "error_diagnosis",
        "error_review",
        "correct_answer",
    }
)


def node_capability_channel(*, verified_evidence_count: int | None, unlocked: bool) -> str | None:
    """节点级通道标签（数据面区分；None = 节点无用户状态）。"""
    if not unlocked:
        return None
    if verified_evidence_count is None:
        # 计数面不可得（未装配证据查询的展示兼容路径）：保守标练习，不声称检验。
        return CapabilityChannel.PRACTICED.value
    if verified_evidence_count > 0:
        return CapabilityChannel.VERIFIED.value
    return CapabilityChannel.PRACTICED.value


__all__ = [
    "CAPABILITY_CHANNEL_SCHEMA_VERSION",
    "CapabilityChannel",
    "NODE_VERIFIED_EVIDENCE_REASONS",
    "NON_TASK_SOURCE_CHANNELS",
    "TRUTH_CLASS_CHANNELS",
    "classify_outcome_channel",
    "fusion_observation_params",
    "node_capability_channel",
]
