"""D-02 · Outcome Ledger 契约 —— 「完成 ≠ 点击」的真相分级与五源正规化。

冻结声明（v3 DATA stream, locks: outcome-ledger）：
- **不新建真源表**：账本是跨五源的**读模型**（服务层聚合，零 schema 变更）。
  五源 = tasks 完成行（X-01 completion_evidence）+ study_records + focus_sessions
  + quiz 反馈（expansion_feedback.meta_data.source ∈ {quiz_passed, quiz_failed}，
  live 0 行、代码路径在册）+ behavioral_outcomes（live 0 行，M-06 Experience 消费面）。
- **TruthClass 词表 = 卡面四值（actual/self_reported/estimated/unknown）+ B-02
  台账的 demo 档合成**，不是「与 B-02 完全对齐」的单一权威五值真源——B-02 台账
  inventory 另有 demo/mock/seed_namespace/pollution 等分类学，本词表只取其 demo
  概念。estimated/demo 保留给消费方标注模型估计与 demo cohort 的语义；确定性完成
  分级只会产 actual/self_reported/unknown。
- **evidence_kind 封闭枚举 = X-01 ``app.core.action_plan.EVIDENCE_KINDS``**（单一
  真源）；本模块做的是 kind → 信任档位（verifiable/user/system）→ 可解析 ref
  scheme → 五源物化路径的正规化映射（``EVIDENCE_TRUST_TIERS`` /
  ``EVIDENCE_KIND_REF_SCHEMES`` / ``EVIDENCE_KIND_SOURCE_MATERIALIZATION``）。
- **「无法证明时不伪装 actual」守卫**（ACTION_AND_INTERVENTION_ENGINE §4 +
  DATA_FLYWHEEL §5 禁止假象）：``classify_task_completion`` 是纯函数、确定性、
  无 LLM。可验证证据（artifact/file/code/quiz_result）必须**实际解析/物化**才能
  升 actual；声明本身不构成证明。user 档（user_confirmation/self_report）与未验证
  声明一律 self_reported。行损坏（无 completed_at）→ unknown。
  服务层解析约束（R2 返修）：kind↔scheme 白名单（``EVIDENCE_KIND_REF_SCHEMES``，
  v1 仅 artifact/file × document://）；code 在出现代码解析器前**恒不**经声明升
  actual；task://、subtask:// 指向的行本身也是用户主张——「声明不构成证明」在
  owner 内部同样成立，v1 不作为完成证据的可解析 scheme。
- **去重键**：outcome 身份 = (source, source_id)（``outcome_key`` 可读复合键，
  ``derive_outcome_id`` 产 ``outc_<sha256[:32]>`` 幂等 id）。**已知限制**：D-01
  ``CorrelationIds.__post_init__``（event_registry.py）强制 correlation 值为
  canonical UUID，``outc_<hash>`` 填入 ``correlation.outcome_id`` 会被
  ``EventContractError`` 拒收——与 D-01 自家 ``evt_`` 前缀同类限制；接线卡不得
  按此形态直填 correlation，需随 evt_ 同款 follow-up（UUID 化包装或放宽校验）解决。
  **同因合并规则**：``study_records.record_type ∈ ECHO_STUDY_RECORD_TYPES
  且 task_id 非空``的行是完成管线（spark_node）的自动回声——它们不是独立 outcome，
  只作为 task_completion outcome 的多源证据附着（验收：「同 task 的 completion+
  study_record 算一个 outcome 的多源证据，不是两个 outcome」）。独立源（focus/quiz/
  standalone study）保持自身 outcome 并以 correlation.task_id 互链，计数不重复。

分级的证据哲学（设计依据，勿漂移）：
- 自动回声 ≠ 独立证据：TaskService.complete 无条件触发 spark_node → study_record，
  因此 study_record(task_complete) 的存在只证明「完成事件被服务器处理过」，不证明
  「工作真的发生了」——把它当 independent 证据会使守卫失效（每个点击都变 actual）。
- 独立系统证据 = 与完成调用无自动因果、服务器记录的行为观察：focus 计时会话
  （FOCUS_COVERAGE 覆盖率规则）、quiz 结果反馈、可解析的 artifact/file/code ref。
- 行为观察的覆盖率规则：focus 覆盖分钟 ≥ max(FOCUS_COVERAGE_MIN_MINUTES,
  FOCUS_COVERAGE_RATIO × actual_minutes) 才升 actual——1 分钟 focus 不能把
  60 分钟任务伪装成 actual（DATA_FLYWHEEL「用更多聊天量当理解增长」同款反模式）。

消费方接入点（服务层 = ``app/services/outcome_ledger_service.py``）：
- **Aurora / Context Compiler（A-05）**：``query(truth_class=TruthClass.ACTUAL)``
  取「已证实」的近期 outcome 进决策上下文，self_reported 行不得当事实注入。
- **Experience Memory（M-06）**：``query(source=BEHAVIORAL)`` + correlation.intervention_id
  对 behavioral_outcomes 做策略学习输入；distilled_strategy_cache 的事实面。
- **Galaxy（G-01/G-02）**：``query(source=STUDY_RECORD/FOCUS_SESSION)`` +
  correlation.node_id 对齐星图掌握度链（GJ03：task→study_record→mastery_audit→outbox）。
- **North Star WVPL**：goal-linked outcome 判定用本账本的 actual 面，不用完成点击面。

X-08 扩展（2026-09，locks: outcome-ledger + task-core，V3-3）：
- **partial/failed outcome 保留（卡面 work 3「不得静默丢弃」）**：task 流
  standalone 谓词从「status=COMPLETED」扩为「status IN (COMPLETED, ABANDONED)」
  ——ABANDONED 行以 ``polarity=NEGATIVE`` 进入账本（``TruthClass.ACTUAL`` +
  NEGATIVE，与 quiz_failed「真实但负向的 outcome」同款先例），失败可查询、
  可审计、但**结构性不可点亮**：WVPL loop 谓词（D-06）独立要求
  ``status=COMPLETED``，NEGATIVE 条目在任何口径下都不产生 loop。
- **tool receipt 映射（卡面 work 1）**：X-05 AgentRun 终态 receipt
  （服务器记录的执行明细，agent_runs.task_id 关联）作为 task_completion
  outcome 的**独立证据**附着（``EvidenceRole.INDEPENDENT``、verified=True、
  ``agent_run://<run_id>`` ref）；SUCCEEDED receipt 物化存在 → 完成分级升
  ACTUAL（``classify_task_completion(run_receipt_materialized=True)``，与
  quiz 物化面同款先例）；PARTIAL/FAILED receipt **永不**升 actual
  （失败不点亮），只作证据保留。
- **为何不 bump ``OUTCOME_LEDGER_SCHEMA_VERSION``**：本次扩展不改 TruthClass
  词表、信任档位、五源封闭集与幂等键推导——``derive_outcome_id`` 的 seed
  （含版本串）保持逐字节稳定，D-06 golden fact JSON 钉住的既有 outcome id
  全部不受影响（读模型旧条目 id 不变的演进是最低侵入路径）。谓词语义扩展
  由持有 outcome-ledger 锁的本卡（X-08）声明，随两位 reviewer 流程裁决。

变更流程：词表/档位/覆盖率规则属冻结契约，改动需 bump ``OUTCOME_LEDGER_SCHEMA_VERSION``
并过两位 reviewer（C-01/D-01/X-01 同款纪律）。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping, Sequence
from uuid import UUID

from loguru import logger

from app.core.action_plan import EVIDENCE_KINDS

OUTCOME_LEDGER_SCHEMA_VERSION = "outcome.ledger.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本并过两位 reviewer）
# ---------------------------------------------------------------------------


class TruthClass(StrEnum):
    """真相分级（卡面四值 + B-02 demo 档合成词表；冻结，勿漂移）。"""

    ACTUAL = "actual"  # 独立可验证证据已解析/物化
    SELF_REPORTED = "self_reported"  # 用户自报（点击完成/确认/自述），无独立证明
    ESTIMATED = "estimated"  # 模型估计（消费方标注，确定性分级不产此值）
    DEMO = "demo"  # demo/seed cohort（消费方标注，确定性分级不产此值）
    UNKNOWN = "unknown"  # 行损坏/输入缺失，无法分级


class OutcomeSource(StrEnum):
    """账本聚合的五源（封闭；第六源加入需 bump 版本）。"""

    TASK_COMPLETION = "task_completion"  # tasks.status=COMPLETED（X-01 evidence 消费）
    STUDY_RECORD = "study_record"  # study_records（standalone：task_id IS NULL）
    FOCUS_SESSION = "focus_session"  # focus_sessions.status=COMPLETED
    QUIZ_FEEDBACK = "quiz_feedback"  # expansion_feedback meta source=quiz_passed/failed
    BEHAVIORAL = "behavioral"  # behavioral_outcomes（M-06 Experience 事实面）


class OutcomePolarity(StrEnum):
    """outcome 的方向（quiz_failed / success=False 是真实但负向的 outcome）。"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EvidenceRole(StrEnum):
    """附着证据与完成调用的因果关系（「自动回声 ≠ 独立证据」的机制化）。"""

    INDEPENDENT = "independent"  # 与完成调用无自动因果的可验证证据
    PIPELINE_ECHO = "pipeline_echo"  # 完成管线的自动副作用（只作多源佐证，永不升 actual）


class EvidenceTrustTier(StrEnum):
    """evidence_kind → 信任档位（正规化映射的值域）。"""

    VERIFIABLE = "verifiable"  # 必须实际解析/物化才能升 actual
    USER = "user"  # 用户断言（user_confirmation/self_report），永不升 actual
    SYSTEM = "system"  # 系统行为观察（需独立物化 + 覆盖率规则）


#: X-01 evidence_kind 封闭枚举 → 信任档位（五源正规化映射之一，冻结）。
EVIDENCE_TRUST_TIERS: dict[str, EvidenceTrustTier] = {
    "artifact": EvidenceTrustTier.VERIFIABLE,
    "file": EvidenceTrustTier.VERIFIABLE,
    "code": EvidenceTrustTier.VERIFIABLE,
    "quiz_result": EvidenceTrustTier.VERIFIABLE,
    "system_event": EvidenceTrustTier.SYSTEM,
    "user_confirmation": EvidenceTrustTier.USER,
    "self_report": EvidenceTrustTier.USER,
}

#: evidence_kind → 五源物化路径（声明如何被证明；空 = 点击内断言、无可物化面）。
#: 这是「evidence 正规化」的第二张映射表：plan 侧声明 vs 账本侧物化互为对偶。
EVIDENCE_KIND_SOURCE_MATERIALIZATION: dict[str, tuple[str, ...]] = {
    "artifact": ("stored_files via ref resolution (document://…)",),
    "file": ("stored_files via ref resolution (document://…)",),
    "code": ("no dedicated table yet — v1 unverifiable, never actual alone",),
    "quiz_result": ("quiz_feedback (expansion_feedback meta source=quiz_*)",),
    "system_event": ("focus_session", "study_record"),
    "user_confirmation": (),
    "self_report": (),
}

#: kind ↔ 可解析 ref scheme 白名单（R2 P2-1 返修新增，冻结）：声明 kind 只有
#: 配对 scheme 的 ref 才可能被解析验证。v1 仅 artifact/file × document://；
#: code 无解析器（恒不单独升 actual）；quiz_result 经 quiz_feedback 物化面而非
#: 声明 ref；task://、subtask:// 行本身是用户主张，不作为完成证据可解析 scheme。
EVIDENCE_KIND_REF_SCHEMES: dict[str, frozenset[str]] = {
    "artifact": frozenset({"document"}),
    "file": frozenset({"document"}),
    "code": frozenset(),
    "quiz_result": frozenset(),
    "system_event": frozenset(),
    "user_confirmation": frozenset(),
    "self_report": frozenset(),
}

# 完整性守卫（import 期）：X-01 词表演进时映射缺项即刻暴露，而非运行期静默漏分级。
assert set(EVIDENCE_TRUST_TIERS) == set(EVIDENCE_KINDS), "EVIDENCE_TRUST_TIERS must cover the X-01 vocabulary"
assert set(EVIDENCE_KIND_SOURCE_MATERIALIZATION) == set(
    EVIDENCE_KINDS
), "EVIDENCE_KIND_SOURCE_MATERIALIZATION must cover the X-01 vocabulary"
assert set(EVIDENCE_KIND_REF_SCHEMES) == set(EVIDENCE_KINDS), "EVIDENCE_KIND_REF_SCHEMES must cover the X-01 vocabulary"

#: 同因合并规则：这些 record_type 的 study_records(task_id 非空) 是完成管线自动回声。
ECHO_STUDY_RECORD_TYPES: frozenset[str] = frozenset({"task_complete"})

#: quiz 反馈的 meta_data.source 判别值（GalaxyFeedbackService.FeedbackType 词表子集）。
QUIZ_FEEDBACK_SOURCES: frozenset[str] = frozenset({"quiz_passed", "quiz_failed"})

#: focus 覆盖率规则（升 actual 的行为观察门槛）。
FOCUS_COVERAGE_MIN_MINUTES = 10
FOCUS_COVERAGE_RATIO = 0.5

# ---------------------------------------------------------------------------
# X-08 · run receipt → outcome 映射（工具回执的极性词表；封闭，勿漂移）
# ---------------------------------------------------------------------------

#: 视为「工作已物化」的 run 终态：SUCCEEDED receipt 存在 → 完成分级可升 ACTUAL。
#: **仅此一个**——PARTIAL（部分完成）不是成功，FAILED/TIMED_OUT/BUDGET_EXCEEDED/
#: UNKNOWN_OUTCOME/CANCELLED 都不是：receipt 保留为证据但永不升 actual、
#: 永不点亮成果（X-08「失败不点亮成果」红线的机制化）。
RUN_RECEIPT_WORK_MATERIALIZED_STATUSES: frozenset[str] = frozenset({"SUCCEEDED"})

#: run 终态 → outcome 极性（封闭映射；capture 事件与账本共用同一词表）。
#: PARTIAL → NEUTRAL：部分完成是**真实但未完成**的 outcome——保留、可查询，
#: 但既非 positive（不点亮）也非 negative（不是失败），卡面「partial 保留」。
RUN_RECEIPT_OUTCOME_POLARITY: dict[str, OutcomePolarity] = {
    "SUCCEEDED": OutcomePolarity.POSITIVE,
    "PARTIAL": OutcomePolarity.NEUTRAL,
    "CANCELLED": OutcomePolarity.NEUTRAL,
    "FAILED": OutcomePolarity.NEGATIVE,
    "TIMED_OUT": OutcomePolarity.NEGATIVE,
    "BUDGET_EXCEEDED": OutcomePolarity.NEGATIVE,
    "UNKNOWN_OUTCOME": OutcomePolarity.NEGATIVE,
}


@dataclass(frozen=True)
class SourceSpec:
    """五源映射表的一行：源 → 物理表 + 真相语义 + 去重谓词。"""

    table: str
    truth_is_classified: bool  # True = 逐条分级（task_completion）；False = 服务器记录默认 actual
    default_truth_class: TruthClass
    occurred_at_field: str
    standalone_predicate: str  # 进入独立 outcome 流的谓词（文档化；服务层落实）


#: 五源映射表（冻结；服务层聚合的单一权威描述）。
FIVE_SOURCE_MAP: dict[str, SourceSpec] = {
    "task_completion": SourceSpec(
        table="tasks",
        truth_is_classified=True,
        default_truth_class=TruthClass.SELF_REPORTED,
        occurred_at_field="completed_at",
        standalone_predicate="status IN (COMPLETED, ABANDONED) AND deleted_at IS NULL"
        " (X-08 扩展：ABANDONED 以 polarity=NEGATIVE 保留——失败 outcome 不静默丢弃，"
        "亦不可点亮：WVPL loop 谓词独立要求 status=COMPLETED)",
    ),
    "study_record": SourceSpec(
        table="study_records",
        truth_is_classified=False,
        default_truth_class=TruthClass.ACTUAL,
        occurred_at_field="created_at",
        standalone_predicate="NOT (record_type IN ('task_complete') AND task_id IS NOT NULL)"
        " (echo 行并入 task_completion 作证据；task_complete 且无 task_id 的行保持独立)",
    ),
    "focus_session": SourceSpec(
        table="focus_sessions",
        truth_is_classified=False,
        default_truth_class=TruthClass.ACTUAL,
        occurred_at_field="end_time",
        standalone_predicate="status=COMPLETED",
    ),
    "quiz_feedback": SourceSpec(
        table="expansion_feedback",
        truth_is_classified=False,
        default_truth_class=TruthClass.ACTUAL,
        occurred_at_field="created_at",
        standalone_predicate="meta_data->>'source' IN ('quiz_passed','quiz_failed')",
    ),
    "behavioral": SourceSpec(
        table="behavioral_outcomes",
        truth_is_classified=False,
        default_truth_class=TruthClass.ACTUAL,
        occurred_at_field="timestamp",
        standalone_predicate="(全表；live 0 行，M-06 消费面)",
    ),
}


__all__ = [
    "OUTCOME_LEDGER_SCHEMA_VERSION",
    "ECHO_STUDY_RECORD_TYPES",
    "EVIDENCE_KIND_SOURCE_MATERIALIZATION",
    "EVIDENCE_KIND_REF_SCHEMES",
    "EVIDENCE_TRUST_TIERS",
    "FIVE_SOURCE_MAP",
    "FOCUS_COVERAGE_MIN_MINUTES",
    "FOCUS_COVERAGE_RATIO",
    "EvidenceRole",
    "EvidenceTrustTier",
    "OutcomeEntry",
    "OutcomeEvidence",
    "OutcomePolarity",
    "OutcomeSource",
    "QUIZ_FEEDBACK_SOURCES",
    "RUN_RECEIPT_OUTCOME_POLARITY",
    "RUN_RECEIPT_WORK_MATERIALIZED_STATUSES",
    "SourceSpec",
    "TruthClass",
    "classify_task_completion",
    "decode_cursor",
    "derive_outcome_id",
    "encode_cursor",
    "outcome_key",
    "parse_declared_evidence",
    "required_focus_minutes",
]


# ---------------------------------------------------------------------------
# 幂等键与去重键
# ---------------------------------------------------------------------------


def derive_outcome_id(*, source: OutcomeSource, source_id: UUID | str) -> str:
    """确定性 outcome 幂等 id（``outc_<sha256[:32]>``，event_registry 派生风格）。

    同一 (source, source_id) 恒产同 id：账本是读模型，重放查询（幂等再聚合）
    对消费方呈现稳定 id，可安全作为下游去重键。与 ``derive_event_id`` 同理：
    它覆盖「同一行重投递」，不覆盖「同一因果重执行产生新行」。

    已知限制（勿按字面接线）：D-01 ``CorrelationIds`` 强制 correlation 值为
    canonical UUID，``outc_<hash>`` 直接填 ``correlation.outcome_id`` 会被
    ``EventContractError`` 拒收——与 ``evt_`` 前缀同类，需 follow-up 卡解决值域门。
    """
    seed = json.dumps(
        {"schema": OUTCOME_LEDGER_SCHEMA_VERSION, "source": OutcomeSource(source).value, "source_id": str(source_id)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "outc_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def outcome_key(source: OutcomeSource, source_id: UUID | str) -> str:
    """可读去重键 ``<source>:<source_id>``（分页排序键的第二分量）。"""
    return f"{OutcomeSource(source).value}:{source_id}"


def encode_cursor(occurred_at: datetime, key: str) -> str:
    """keyset 游标：base64url(JSON{t,k})。opaque 对消费方。"""
    payload = json.dumps({"t": occurred_at.isoformat(), "k": key}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    """解码游标；畸形输入返回 None（调用方退化为无游标查询，不 crash）。"""
    if not cursor:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))
        if not isinstance(payload, Mapping):
            return None
        return datetime.fromisoformat(str(payload["t"])), str(payload["k"])
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
        return None


# ---------------------------------------------------------------------------
# 守卫：完成真相分级（纯函数，无 IO，无 LLM）
# ---------------------------------------------------------------------------


def required_focus_minutes(actual_minutes: int | float | None) -> int:
    """升 actual 所需的独立 focus 覆盖分钟（覆盖率规则）。

    threshold = max(FOCUS_COVERAGE_MIN_MINUTES, FOCUS_COVERAGE_RATIO × actual_minutes)；
    actual_minutes 缺失/0 → 绝对下限（10 分钟）。对 actual_minutes 单调不减。
    """
    if not actual_minutes or actual_minutes <= 0:
        return FOCUS_COVERAGE_MIN_MINUTES
    return max(FOCUS_COVERAGE_MIN_MINUTES, int(FOCUS_COVERAGE_RATIO * float(actual_minutes)))


def parse_declared_evidence(raw: Any) -> tuple[dict[str, Any], ...]:
    """防御性解析 tasks.completion_evidence 列（JSONB）为规范化 dict 元组。

    - 非 list / list 内非 dict → ()（脏行降级，不伪装）；
    - 不经 X-01 ``action_plan_projection`` 的行（例如手工 SQL 检视）由此兜底：
      词表外 kind 保留原样（分级时按未验证处理），不抛异常。
    """
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    parsed = []
    for entry in raw:
        if isinstance(entry, Mapping):
            parsed.append(
                {
                    "evidence_kind": entry.get("evidence_kind"),
                    "ref": entry.get("ref"),
                    "description": entry.get("description"),
                }
            )
    return tuple(parsed)


def classify_task_completion(
    *,
    completed_at: datetime | None,
    declared_evidence: Sequence[Mapping[str, Any]] | None,
    focus_minutes_covered: int | float,
    quiz_materialized: bool,
    verified_evidence_kinds: frozenset[str] | set[str],
    actual_minutes: int | float | None,
    run_receipt_materialized: bool = False,
) -> TruthClass:
    """「无法证明时不伪装 actual」守卫（验收项 ②，红测钉死）。

    判定顺序（确定性，逐条短路）：
    1. ``completed_at`` 缺失 → UNKNOWN（行损坏，无法分级）；
    2. 任一 verifiable 档 kind（artifact/file/code/quiz_result）**已验证**
       （ref 解析 / quiz 物化）→ ACTUAL；
    3. quiz 结果物化（独立五源行存在）→ ACTUAL；
    4. SUCCEEDED run receipt 物化（X-05 终态行存在，``agent_runs.task_id``
       关联；PARTIAL/FAILED receipt 不算）→ ACTUAL——服务器记录的执行明细
       是与点击无自动因果的独立工作证明（X-08 tool receipt 映射）；
    5. 独立 focus 计时覆盖 ≥ ``required_focus_minutes(actual_minutes)`` → ACTUAL
       （服务器记录的行为观察，覆盖率门槛防「1 分钟 focus 伪装 60 分钟完成」）；
    6. 其余一切（无声明 / user 档声明 / 未解析的 verifiable 声明 / 覆盖不足）→
       SELF_REPORTED——完成点击及其自动回声只是用户的自报。

    注意：本函数永不出 ESTIMATED/DEMO（那是消费方对模型估计与 demo cohort 的
    标注语义，不属于确定性完成分级）。truth 是**查询时点重算**的读模型值：
    服务层只计入完成时刻之前开始的 focus 会话（时间方向约束），新发现的
    完成前证据只会升不会降；文件证据的生命周期撤销（revoked/erased）可使
    actual 回落 self_reported——单调性语义详见 REPORT。
    """
    if completed_at is None:
        return TruthClass.UNKNOWN

    verified = {str(kind) for kind in verified_evidence_kinds}
    if verified & {k for k, tier in EVIDENCE_TRUST_TIERS.items() if tier is EvidenceTrustTier.VERIFIABLE}:
        return TruthClass.ACTUAL
    if quiz_materialized:
        return TruthClass.ACTUAL
    if run_receipt_materialized:
        return TruthClass.ACTUAL

    threshold = required_focus_minutes(actual_minutes)
    try:
        covered = float(focus_minutes_covered or 0)
    except (TypeError, ValueError):
        covered = 0.0
    if covered >= threshold:
        return TruthClass.ACTUAL

    # 声明存在但全部未验证（含词表外 kind）——降级为 self_reported 时留痕（可观测）。
    if declared_evidence is not None and len(tuple(declared_evidence)) > 0:
        kinds = [entry.get("evidence_kind") if isinstance(entry, Mapping) else None for entry in declared_evidence]
        unverified = [k for k in kinds if k is not None and k not in verified]
        if unverified:
            logger.debug(
                "OutcomeLedger: completion evidence declared but unverified (kinds={}) → self_reported",
                unverified,
            )
    return TruthClass.SELF_REPORTED


# ---------------------------------------------------------------------------
# 读模型条目（服务层聚合的载体；dataclass 而非 ORM —— 账本无表）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutcomeEvidence:
    """附着在 outcome 上的单条证据（多源证据的正规化形态）。"""

    source: str  # 物化源：study_record / focus_session / quiz_feedback / declared_ref
    ref: str | None  # 指向源行的 URI（task://…、focus_session://… 等）
    evidence_kind: str | None  # X-01 词表（declared 面）或物化源推断 kind
    role: EvidenceRole  # independent | pipeline_echo
    verified: bool = False  # ref 是否实际解析/物化


@dataclass(frozen=True)
class OutcomeEntry:
    """账本条目：一个去重后的 outcome（跨模块查询/计数的原子单位）。"""

    outcome_id: str  # outc_<sha256[:32]>（幂等）
    source: OutcomeSource
    source_id: str
    user_id: str
    occurred_at: datetime  # naive UTC（naive-UTC 规范）
    truth_class: TruthClass
    polarity: OutcomePolarity
    source_ref: str  # <source_table>://<id>（X-01 封闭 scheme 之外的账本扩展，见 REPORT）
    correlation: dict[str, str]  # {task_id, plan_id, node_id, intervention_id}（canonical UUID str）
    minutes: float | None = None  # focus.duration / study.study_minutes / task.actual_minutes
    mastery_delta: float | None = None
    score: float | None = None  # quiz score / behavioral success（1.0/0.0）
    evidence: tuple[OutcomeEvidence, ...] = ()

    @property
    def key(self) -> str:
        return outcome_key(self.source, self.source_id)
