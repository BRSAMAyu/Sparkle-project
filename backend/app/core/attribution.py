"""V4-D02 · goal/task/occurrence/run 同域关联、统一观察窗与缺失语义（unattributed 分母）。

设计真源：``v4/03_intelligence/DATA_AND_GRAPH.md``（本卡 specs 明文引用）：

- 「每个事件至少携带 user、decision_id、goal/task/run 可选真实外键、causation_id、
  dedupe_key、source_version、occurred_at/received_at。**不能把 task_occurrence_id
  当 Task.id；缺关联就 unattributed**。received_at 用于延迟与 watermark，不能覆盖
  真实事件时间。」
- 「关联完整率按具备合法同域键的 eligible 事件计算，**同时公开 unattributed 占全部
  比例；不能剔除难配对事件制造 100%**。」
- 「censored：观察窗结束但无可解释结果；包括未返场/退出/失去授权。**与 failed 分开**。」
- 「accepted/rejected/edited/started：按真实操作记录；既有枚举没有 edited 时走显式
  契约扩展，不填假 accepted。」

本模块是**统一层，不是第二权威**——四条既有权威原样复用、逐条 import 期断言钉死：

1. **观察窗语义**（超窗未回来 = 删失 censored，绝不计失败）：唯一权威 = D-05
   ``intervention_lifecycle.resolve_observation_status``（三删失 + unknown，读模型
   查询时点重算）。本模块只提供域无关门面 :func:`anchor_observation_status`，逐值
   委托权威函数；任何域不得自造窗口语义。窗口缺省/钳制同权威
   （72h 默认，[1h, 30d]）。
2. **用户响应词表**（accepted/rejected/started/edited）：唯一权威 = D-05
   ``LifecycleEventType`` / ``USER_RESPONSE_EVENT_TYPES``。``edited`` 已是显式成员
   （DATA_AND_GRAPH「不填假 accepted」在 V3 已满足——edit 走 edited、永不改写为
   accepted；事件身份 = (decision_id, event_type, dedupe_subkey)，两类事件身份
   不同、互不改写）。本模块 import 期断言四值齐备，不复制词表。
3. **outcome 身份**：唯一权威 = D-02 ``derive_outcome_id``（``outc_<sha256[:32]>``）。
   追踪链第三跳用其重算验证，不新造 outcome id。
4. **呈现事件身份**：唯一权威 = D01/B05 ``experience_event.v1``
   （``derive_dedupe_key``/``derive_experience_event_id`` + ``EXPERIENCE_RECEIPT_REF_SCHEMES``）。
   追踪链前两跳用其重算验证。

新增的最小事实面（此前全仓无）：

- **显式分域关联键** :class:`DomainKey`：``(domain, canonical UUID)`` 二元组。
  四域封闭词表 :class:`AttributionDomain`（goal/task/occurrence/run，卡面四域）。
  匹配只认**同域+同值**：跨域键即使 UUID 逐字节相同也不得串归因（domain_mismatch
  → unattributed，不硬塞）——「task_occurrence_id 当 Task.id」的机制化拒绝。
  裸值永远不参与匹配（值相等本身不构成关联）。
- **归因判定** :func:`attribute_outcome`：确定性全函数 →
  ``attributed``（同域键匹配且落在观察窗内）或 ``unattributed``（封闭理由词表：
  ``missing_key``/``domain_mismatch``/``no_same_domain_match``/``outside_window``；
  行损坏 → ``unjudgeable``）。unattributed **显式落分母**，不静默丢弃。
- **幂等样本身份** :func:`derive_attribution_sample_id`（``attr_<sha256[:32]>``，
  D-01/D-02 派生风格）：同一 (域, 锚点, outcome) 恒同 id——同一事件/回执重放
  恒同样本，消费方按 id 去重，样本量不虚增。
- **公开分母** :class:`AttributionDenominator`：eligible 全集计分母
  （含 unattributed/unknown，永不剔除难配对事件）；``unattributed_ratio`` 在
  eligible=0 时为 ``None``（不宣称 0% 也不 100%）。``to_dict()`` 为公开可查面
  （insights/evidence cards 消费）。
- **链路追踪验证** :func:`trace_receipt_to_outcome`：UI 交互（其重播抑制键即
  experience_event ``event_id``）→ receipt_ref → experience_event → outcome
  逐跳**重算**验证（每跳 id 从冻结权威重新派生比对，无存储信任）；任一跳断裂
  → 逐跳 ``TraceHop`` 显式报因，不静默。随机取样本可完整还原（验收 3）。

与 I01 的透传兼容：censored/unknown 复用 D-05 ``ObservationStatus`` 原词表；
本模块不产、不改 ``TruthClass``（真相关面唯一权威 = D-02 账本）——
``last_valid_outcome.truth_class``（全 5 值 1:1 透传，demo 含）语义不受影响。

变更流程：四域词表/unattributed 理由词表/分母语义属冻结契约，改动需 bump
``ATTRIBUTION_SCHEMA_VERSION`` 并过 reviewer（C-01/D-01/D-02/D-05 同款纪律）。
"""

# rule-bj: exempt V4-D02 冻结契约模块（同域关联/统一观察窗/缺失语义）；生产消费方按卡序接线（V4-D03 撤回派生影响按关联键找受影响面、V4-D05 洞察公开 unattributed 分母）——登记 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from app.core.event_registry import normalize_occurred_at
from app.core.experience_event import (
    EXPERIENCE_RECEIPT_REF_SCHEMES,
    derive_dedupe_key,
    derive_experience_event_id,
)
from app.core.intervention_lifecycle import (
    DEFAULT_OBSERVATION_WINDOW_HOURS,
    USER_RESPONSE_EVENT_TYPES,
    LifecycleEventType,
    ObservationStatus,
    clamp_observation_window_hours,
    outcome_links_exposure,
    resolve_observation_status,
)
from app.core.outcome_ledger import OUTCOME_LEDGER_SCHEMA_VERSION, OutcomeSource, derive_outcome_id

ATTRIBUTION_SCHEMA_VERSION = "attribution.domain.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本 + reviewer）
# ---------------------------------------------------------------------------


class AttributionDomain(StrEnum):
    """同域关联键的四域封闭词表（卡面 goal/task/occurrence/run；每域键独立命名空间）。

    域即身份的一半：匹配必须 (domain, value) 二元组相等。**不存在跨域值迁移**——
    ``task_occurrence_id`` 只属 occurrence 域（``DOMAIN_CORRELATION_KEYS`` 钉死），
    任何把它当 task 域键参与的归因都是伪归因。
    """

    GOAL = "goal"
    TASK = "task"
    OCCURRENCE = "occurrence"
    RUN = "run"


ATTRIBUTION_DOMAINS: frozenset[str] = frozenset(d.value for d in AttributionDomain)


class AttributionStatus(StrEnum):
    """归因判定二值（unattributed 是显式一等结论，不是错误、不是失败）。"""

    ATTRIBUTED = "attributed"
    UNATTRIBUTED = "unattributed"


class UnattributedReason(StrEnum):
    """unattributed 的封闭理由词表（公开分母按理由细分；每值可审计）。"""

    MISSING_KEY = "missing_key"  # 锚点或结果侧该域关联键缺失（缺关联就 unattributed，不硬塞）
    DOMAIN_MISMATCH = "domain_mismatch"  # 双方有键但域不同——值逐字节相同也不串（跨域形近拒绝）
    NO_SAME_DOMAIN_MATCH = "no_same_domain_match"  # 同域不同值（真实的非关联，保留事实）
    OUTSIDE_WINDOW = "outside_window"  # 同域键匹配但在观察窗外（时序倒置或超窗；锚点侧= censored）


class UnjudgeableReason(StrEnum):
    """行损坏/输入无法判定的显式面（对齐 D-05 ``ObservationStatus.UNKNOWN`` 语义）。

    与 unattributed 分开计数（n_unknown 面，同样永不进 rate 分母）：unattributed
    是「关联不上」，unjudgeable 是「输入坏到无从判定」。
    """

    BROKEN_ROW = "broken_row"


#: 各域的关联键名（correlation dict 键 → 域；显式分域的反向拼写表）。
#: 「不能把 task_occurrence_id 当 Task.id」在此钉死：``task_occurrence_id`` 只投影
#: 到 occurrence 域；task 域永远不含它（import 期断言 + 契约测试字面冻结）。
DOMAIN_CORRELATION_KEYS: dict[AttributionDomain, tuple[str, ...]] = {
    AttributionDomain.GOAL: ("goal_id",),
    AttributionDomain.TASK: ("task_id",),
    AttributionDomain.OCCURRENCE: ("occurrence_id", "task_occurrence_id"),
    AttributionDomain.RUN: ("run_id",),
}

# import 期断言：域键名表互斥（一个键名只属一个域）+ 反伪归因红线。
_all_names = [name for names in DOMAIN_CORRELATION_KEYS.values() for name in names]
assert len(_all_names) == len(set(_all_names)), "a correlation key name must belong to exactly one attribution domain"
assert (
    "task_occurrence_id" not in DOMAIN_CORRELATION_KEYS[AttributionDomain.TASK]
), "task_occurrence_id must never project into the task domain (DATA_AND_GRAPH: 不能把 task_occurrence_id 当 Task.id)"
assert "goal_id" not in DOMAIN_CORRELATION_KEYS[AttributionDomain.TASK]


class AttributionKeyError(ValueError):
    """分域键构造失败（非 canonical UUID / 域词表外）——边界处 fail-loud，不降级串域。"""


# ---------------------------------------------------------------------------
# 显式分域关联键
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainKey:
    """``(domain, canonical UUID)`` 分域关联键（值语义只在同域内成立）。

    - 构造期 canonical UUID 校验（fail-loud :class:`AttributionKeyError`）：
      畸形值不得进关联面（对照 D-05 ``linkage_keys`` 的「无效值剔除」——本类用于
      **判定**而非**捕获**，捕获用 :func:`domain_keys_from_correlation`）。
    - ``key_string`` = ``<domain>:<uuid>``（D-02 ``outcome_key`` 同款形态；不是
      receipt_ref URI，不进 ``EXPERIENCE_RECEIPT_REF_SCHEMES`` 词表问题域）。
    """

    domain: AttributionDomain
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.domain, AttributionDomain):
            try:
                object.__setattr__(self, "domain", AttributionDomain(str(self.domain)))
            except ValueError as exc:
                raise AttributionKeyError(f"attribution domain {self.domain!r} outside closed vocabulary") from exc
        try:
            object.__setattr__(self, "value", str(UUID(str(self.value))))
        except (ValueError, TypeError, AttributeError) as exc:
            raise AttributionKeyError(f"attribution key value {self.value!r} is not a valid UUID") from exc

    @property
    def key_string(self) -> str:
        return f"{self.domain.value}:{self.value}"

    def links(self, other: DomainKey) -> bool:
        """同域关联判定：域相等**且** canonical 值相等。

        值相等但域不同 → False（跨域形近不串归因；这是本类的核心语义，红测钉死）。
        """
        if not isinstance(other, DomainKey):
            return False
        return self.domain is other.domain and self.value == other.value

    def to_dict(self) -> dict[str, str]:
        return {"domain": self.domain.value, "value": self.value}


def domain_keys_from_correlation(correlation: Mapping[str, Any] | None) -> tuple[DomainKey, ...]:
    """correlation dict（如 D-02 ``OutcomeEntry.correlation``）→ 分域键元组。

    - 只认 :data:`DOMAIN_CORRELATION_KEYS` 的键名→域投影（显式分域；未登记键名
      如 session_id/plan_id 不构成四域归因依据）；
    - 值 canonical 化失败 → 剔除不炸（捕获面与 D-05 ``linkage_keys`` 同纪律：
      脏值不匹配、不抛异常、留待 unattributed 分母显式承接）；
    - 同域多键并存时全部返回（判定由 :func:`attribute_outcome` 逐键短路）。
    """
    if not correlation:
        return ()
    keys: list[DomainKey] = []
    for domain, names in DOMAIN_CORRELATION_KEYS.items():
        for name in names:
            raw = correlation.get(name)
            if raw is None:
                continue
            try:
                keys.append(DomainKey(domain=domain, value=str(raw)))
            except AttributionKeyError:
                continue
    return tuple(keys)


# ---------------------------------------------------------------------------
# 幂等样本身份（重放不虚增样本）
# ---------------------------------------------------------------------------


def derive_attribution_sample_id(*, domain: AttributionDomain | str, anchor_id: str, outcome_id: str) -> str:
    """确定性归因样本 id（``attr_<sha256[:32]>``，D-01 ``eev_``/D-02 ``outc_`` 派生风格）。

    同一 (域, 锚点 id, outcome id) 恒产同 id：同一事件/回执重放（at-least-once
    投递、6h 扫描 beat 重跑、丢样本重算）恒得同样本身份——消费方按 id 去重即
    实现「重复回放不加样本」。时间字段不进派生（重放时点不同不改样本身份）。
    """
    seed = json.dumps(
        {
            "schema": ATTRIBUTION_SCHEMA_VERSION,
            "domain": AttributionDomain(str(domain)).value,
            "anchor_id": str(anchor_id),
            "outcome_id": str(outcome_id),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "attr_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# 归因判定（确定性全函数；unattributed 显式落分母）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributionVerdict:
    """一次 (锚点键, outcome) 的同域归因判定（不可变、可重放复核）。

    - ``status=attributed``：``sample_id`` 恒定（重放幂等）、``matched_key`` 为
      匹配的分域键、``observation_status=observed``（窗口内）；
    - ``status=unattributed``：``reason`` 为封闭理由词表成员（显式分母，不静默
      丢弃）；``outside_window`` 时 ``observation_status`` 同步给出锚点侧读模型值
      （超窗未回来 = censored_*，绝不 negative/failed）；
    - ``status=unattributed`` + ``reason=unjudgeable``：输入行损坏（n_unknown 面）。
    """

    status: AttributionStatus
    domain: AttributionDomain | None = None
    matched_key: DomainKey | None = None
    reason: str | None = None
    sample_id: str = ""
    observation_status: ObservationStatus | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ATTRIBUTION_SCHEMA_VERSION,
            "status": self.status.value,
            "domain": self.domain.value if self.domain is not None else None,
            "matched_key": self.matched_key.to_dict() if self.matched_key is not None else None,
            "reason": self.reason,
            "sample_id": self.sample_id,
            "observation_status": self.observation_status.value if self.observation_status is not None else None,
        }


def attribute_outcome(
    *,
    anchor: DomainKey | None,
    outcome_key: DomainKey | None,
    outcome_id: str,
    anchor_at: datetime | None,
    outcome_at: datetime | None,
    now: datetime,
    window_hours: int | None = None,
    user_last_active_at: datetime | None = None,
) -> AttributionVerdict:
    """同域归因判定（纯函数、确定性、无 IO/LLM；判定顺序逐条短路）。

    ``outcome_id``（D-02 ``outc_<hash>``）是样本身份的必要分量：attributed 判定的
    ``sample_id`` 由 (域, 锚点值, outcome_id) 内容寻址——重放恒同 id，消费方按 id
    去重即「重复回放不加样本」。

    1. 任一侧该域关联键缺失 → ``unattributed/missing_key``（缺关联就 unattributed，
       **不硬塞**、不静默丢弃——公开分母承接）；
    2. 域不同 → ``unattributed/domain_mismatch``（值逐字节相同也拒绝——跨域形近
       不串归因）；
    3. 同域不同值 → ``unattributed/no_same_domain_match``；
    4. 同域键匹配但 ``anchor_at``/``outcome_at`` 缺失 → ``unattributed/unjudgeable``
       （行损坏显式面，n_unknown，不伪装成关联或失败）；
    5. 同域键匹配且时序齐备：
       - ``anchor_at ≤ outcome_at ≤ anchor_at + window`` → ``attributed``
         （样本 id 幂等；延迟 outcome 在窗内照常归因——received_at 延迟不改变
         outcome 真实时间语义）；
       - 早于锚点（时序倒置）或晚于窗末 → ``unattributed/outside_window``，且
         ``observation_status`` 按锚点侧统一观察窗给出（超窗未回来 = censored_*，
         绝不计失败；超窗才回来的 outcome 保留事实、不归此锚点）。

    窗口语义唯一真源 = D-05（缺省 72h、钳制 [1h, 30d]）；本函数只消费其常量。
    """
    window = clamp_observation_window_hours(window_hours)

    if anchor is None or outcome_key is None:
        known = anchor if anchor is not None else outcome_key
        return AttributionVerdict(
            status=AttributionStatus.UNATTRIBUTED,
            domain=known.domain if known is not None else None,
            reason=UnattributedReason.MISSING_KEY.value,
        )

    if anchor.domain is not outcome_key.domain:
        return AttributionVerdict(
            status=AttributionStatus.UNATTRIBUTED,
            domain=anchor.domain,
            reason=UnattributedReason.DOMAIN_MISMATCH.value,
        )

    if anchor.value != outcome_key.value:
        return AttributionVerdict(
            status=AttributionStatus.UNATTRIBUTED,
            domain=anchor.domain,
            reason=UnattributedReason.NO_SAME_DOMAIN_MATCH.value,
        )

    if anchor_at is None or outcome_at is None:
        return AttributionVerdict(
            status=AttributionStatus.UNATTRIBUTED,
            domain=anchor.domain,
            reason=UnjudgeableReason.BROKEN_ROW.value,
        )

    anchor_ts = normalize_occurred_at(anchor_at)
    outcome_ts = normalize_occurred_at(outcome_at)
    window_end_ts = anchor_ts.timestamp() + window * 3600
    in_window = anchor_ts.timestamp() <= outcome_ts.timestamp() <= window_end_ts

    if not in_window:
        # 锚点侧读模型状态同步复算（唯一权威 = D-05 resolve_observation_status）：
        # 超窗/未到期/在场所未行动/流失四态，绝不产生 negative/failed 语义。
        observation = resolve_observation_status(
            exposed_at=anchor_ts,
            window_hours=window,
            outcome_times=(outcome_ts,),
            now=now,
            user_last_active_at=user_last_active_at,
            exposure_valid=True,
        )
        return AttributionVerdict(
            status=AttributionStatus.UNATTRIBUTED,
            domain=anchor.domain,
            reason=UnattributedReason.OUTSIDE_WINDOW.value,
            observation_status=observation,
        )

    return AttributionVerdict(
        status=AttributionStatus.ATTRIBUTED,
        domain=anchor.domain,
        matched_key=anchor,
        sample_id=derive_attribution_sample_id(domain=anchor.domain, anchor_id=anchor.value, outcome_id=outcome_id),
        observation_status=ObservationStatus.OBSERVED,
    )


def attribute_outcome_entry(
    *,
    anchor: DomainKey,
    outcome: Mapping[str, Any],
    anchor_at: datetime | None,
    now: datetime,
    window_hours: int | None = None,
    user_last_active_at: datetime | None = None,
) -> AttributionVerdict:
    """:func:`attribute_outcome` 的账本行入口（D-02 ``OutcomeEntry`` dict 形态）。

    outcome 侧键从 ``correlation`` 按 :data:`DOMAIN_CORRELATION_KEYS` 显式分域投影；
    锚点域在 outcome correlation 中无任何键 → ``missing_key``（缺关联就
    unattributed）。``occurred_at`` 取 outcome 真实事件时间（不是 received_at）。
    """
    outcome_keys = domain_keys_from_correlation(outcome.get("correlation"))
    same_domain = next((k for k in outcome_keys if k.domain is anchor.domain), None)
    occurred_at = outcome.get("occurred_at")
    return attribute_outcome(
        anchor=anchor,
        outcome_key=same_domain,
        outcome_id=str(outcome.get("outcome_id") or ""),
        anchor_at=anchor_at,
        outcome_at=occurred_at if isinstance(occurred_at, datetime) else None,
        now=now,
        window_hours=window_hours,
        user_last_active_at=user_last_active_at,
    )


# ---------------------------------------------------------------------------
# 公开分母（unattributed 显式占比；不剔除难配对事件）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributionDenominator:
    """一批归因判定的公开分母（DATA_AND_GRAPH「关联完整率」的机制面）。

    - ``n_eligible`` = 全体判定数（**含** unattributed/unjudgeable——不剔除难配对
      事件制造 100%）；
    - ``unattributed_ratio`` = n_unattributed / n_eligible；eligible=0 → ``None``
      （不宣称 0% 也不 100%——D-05 Wilson n=0 同款谦抑）；
    - ``by_reason``：unattributed 按封闭理由细分（可审计「为什么关联不上」）；
    - ``n_unknown``：行损坏面单列（同样永不进 attributed 率分子）。
    ``to_dict()`` 即公开可查面（insights/evidence cards 消费）。
    """

    n_eligible: int
    n_attributed: int
    n_unattributed: int
    n_unknown: int
    by_reason: dict[str, int]

    @classmethod
    def from_verdicts(cls, verdicts: Iterable[AttributionVerdict]) -> AttributionDenominator:
        n_eligible = n_attributed = n_unattributed = n_unknown = 0
        by_reason: dict[str, int] = {}
        for verdict in verdicts:
            n_eligible += 1
            if verdict.status is AttributionStatus.ATTRIBUTED:
                n_attributed += 1
                continue
            n_unattributed += 1
            reason = verdict.reason or "unspecified"
            if reason == UnjudgeableReason.BROKEN_ROW.value:
                n_unknown += 1
            by_reason[reason] = by_reason.get(reason, 0) + 1
        return cls(
            n_eligible=n_eligible,
            n_attributed=n_attributed,
            n_unattributed=n_unattributed,
            n_unknown=n_unknown,
            by_reason=by_reason,
        )

    @property
    def unattributed_ratio(self) -> float | None:
        if self.n_eligible <= 0:
            return None
        return self.n_unattributed / self.n_eligible

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ATTRIBUTION_SCHEMA_VERSION,
            "n_eligible": self.n_eligible,
            "n_attributed": self.n_attributed,
            "n_unattributed": self.n_unattributed,
            "n_unknown": self.n_unknown,
            "unattributed_by_reason": dict(sorted(self.by_reason.items())),
            "unattributed_ratio": (round(self.unattributed_ratio, 6) if self.unattributed_ratio is not None else None),
        }


# ---------------------------------------------------------------------------
# 统一观察窗（域无关门面；语义唯一真源 = D-05）
# ---------------------------------------------------------------------------


def anchor_observation_status(
    *,
    domain: AttributionDomain | str,
    anchor_id: str,
    anchor_at: datetime | None,
    window_hours: int | None,
    outcome_times: Sequence[datetime] = (),
    now: datetime,
    user_last_active_at: datetime | None = None,
    anchor_valid: bool = True,
) -> ObservationStatus:
    """四域统一观察窗读模型值（goal/task/occurrence/run 逐值委托 D-05 权威函数）。

    - 「超窗未回来」= ``censored_window_closed`` / ``censored_user_churned``（删失），
      「窗未到期」= ``censored_not_yet_due``——**永不产生 failed/negative**（验收 2）；
    - 窗内见到 outcome（含延迟到达）= ``observed``；
    - 行损坏（anchor_valid=False / anchor_at 缺失）= ``unknown``；
    - ``domain``/``anchor_id`` 只作可审计入参校验（域词表外 fail-loud），不参与
      判定——窗口语义四域同权，这正是「统一观察窗」的含义。
    """
    if str(domain) not in ATTRIBUTION_DOMAINS:
        raise AttributionKeyError(f"attribution domain {domain!r} outside closed vocabulary")
    if not str(anchor_id or "").strip():
        raise AttributionKeyError("anchor_id must be a non-empty string")
    return resolve_observation_status(
        exposed_at=anchor_at,
        window_hours=window_hours,
        outcome_times=outcome_times,
        now=now,
        user_last_active_at=user_last_active_at,
        exposure_valid=anchor_valid,
    )


# ---------------------------------------------------------------------------
# 链路追踪验证（UI→receipt→event→outcome 逐跳重算还原）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceHop:
    """追踪链单跳验证结果（ok=False 时 detail 给显式断因，不静默）。"""

    hop: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"hop": self.hop, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class TraceReport:
    """``receipt_ref → experience_event → outcome`` 链路还原报告（可审计溯源）。"""

    traceable: bool
    hops: tuple[TraceHop, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ATTRIBUTION_SCHEMA_VERSION,
            "traceable": self.traceable,
            "hops": [hop.to_dict() for hop in self.hops],
        }


def _receipt_ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


def trace_receipt_to_outcome(
    *,
    event: Mapping[str, Any],
    outcome: Mapping[str, Any] | None = None,
    anchor: DomainKey | None = None,
    exposure_linkage: Mapping[str, str] | None = None,
) -> TraceReport:
    """从一条 UI 交互（experience_event）还原完整结果链（纯函数、逐跳重算）。

    每跳验证都是**从冻结权威重新派生并比对**（无存储信任——存储行被篡改即断链
    显式报因），随机取任一样本可完整还原（验收 3）：

    1. ``receipt_ref_scheme``：事件携带 receipt_ref 且 scheme ∈ B05 封闭六元集
       （无 receipt_ref 的事件无法向权威回执溯源 → 断链显式报因）；
    2. ``event_identity``：``dedupe_key = derive_dedupe_key(receipt_ref, kind,
       subject.version_token)``、``event_id = derive_experience_event_id(dedupe_key)``
       重算比对（D01 权威）——UI 侧重播抑制键可独立复算；
    3. ``outcome_identity``（提供 outcome 时）：``outcome_id = derive_outcome_id(
       source, source_id)`` 重算比对（D-02 权威）；
    4. ``outcome_link``：事件→outcome 的链必须有其一成立——
       (a) receipt_ref scheme = ``outcome`` 且 ref 指向该 outcome_id（直连回执）；
       (b) ``anchor`` 提供且 outcome correlation 与锚点同域键匹配（同域关联）；
       (c) ``exposure_linkage`` 提供且与 outcome correlation 有共同键
       （D-05 ``outcome_links_exposure`` 权威判定，intervention_lifecycle 面）。
       全不成立 → 断链显式报因。

    outcome 缺失 → ``traceable=False``（链条不完整是显式结论，不是静默通过）。
    """
    hops: list[TraceHop] = []

    # Hop 1: receipt_ref scheme（B05 E4 词表）
    receipt_ref = event.get("receipt_ref")
    receipt_ref = str(receipt_ref).strip() if receipt_ref is not None else ""
    if not receipt_ref:
        hops.append(TraceHop(hop="receipt_ref_scheme", ok=False, detail="event carries no receipt_ref"))
    else:
        scheme = _receipt_ref_scheme(receipt_ref)
        if scheme in EXPERIENCE_RECEIPT_REF_SCHEMES:
            hops.append(TraceHop(hop="receipt_ref_scheme", ok=True, detail=f"scheme={scheme}"))
        else:
            hops.append(
                TraceHop(
                    hop="receipt_ref_scheme",
                    ok=False,
                    detail=f"scheme {scheme!r} outside EXPERIENCE_RECEIPT_REF_SCHEMES",
                )
            )

    # Hop 2: event 身份重算（D01 权威）
    raw_subject = event.get("subject")
    subject: Mapping[str, Any] = raw_subject if isinstance(raw_subject, Mapping) else {}
    kind = str(event.get("kind") or "")
    version_token = str(subject.get("version_token") or "")
    recomputed_dedupe = derive_dedupe_key(receipt_ref=receipt_ref or None, kind=kind, version_token=version_token)
    recomputed_event_id = derive_experience_event_id(recomputed_dedupe)
    stored_event_id = str(event.get("event_id") or "")
    stored_dedupe = str(event.get("dedupe_key") or "")
    if (
        stored_event_id
        and stored_event_id == recomputed_event_id
        and (not stored_dedupe or stored_dedupe == recomputed_dedupe)
    ):
        hops.append(TraceHop(hop="event_identity", ok=True, detail=f"event_id={recomputed_event_id} recomputed"))
    else:
        hops.append(
            TraceHop(
                hop="event_identity",
                ok=False,
                detail=f"stored event_id={stored_event_id!r} does not match recomputed {recomputed_event_id!r}",
            )
        )

    if outcome is None:
        hops.append(TraceHop(hop="outcome_identity", ok=False, detail="no outcome provided (chain incomplete)"))
        return TraceReport(traceable=False, hops=tuple(hops))

    # Hop 3: outcome 身份重算（D-02 权威）
    outcome_source = str(outcome.get("source") or "")
    outcome_source_id = str(outcome.get("source_id") or "")
    stored_outcome_id = str(outcome.get("outcome_id") or "")
    try:
        source_enum = OutcomeSource(outcome_source)
        recomputed_outcome_id = derive_outcome_id(source=source_enum, source_id=outcome_source_id)
        outcome_hop_ok = bool(stored_outcome_id) and stored_outcome_id == recomputed_outcome_id
        outcome_detail = f"outcome_id={recomputed_outcome_id} recomputed ({OUTCOME_LEDGER_SCHEMA_VERSION})"
    except (ValueError, TypeError):
        outcome_hop_ok = False
        recomputed_outcome_id = ""
        outcome_detail = f"source {outcome_source!r} outside OutcomeSource vocabulary"
    hops.append(TraceHop(hop="outcome_identity", ok=outcome_hop_ok, detail=outcome_detail))

    # Hop 4: 事件→outcome 链接语义（三选一，全部走冻结权威）
    link_ok = False
    link_detail = "no link established"
    if receipt_ref and _receipt_ref_scheme(receipt_ref) == "outcome" and recomputed_outcome_id:
        ref_tail = receipt_ref.split("://", 1)[1]
        link_ok = ref_tail == stored_outcome_id
        link_detail = (
            "receipt_ref outcome:// direct link"
            if link_ok
            else (f"receipt_ref points at {ref_tail!r} but outcome_id is {stored_outcome_id!r}")
        )
    if not link_ok and anchor is not None:
        same_domain = [k for k in domain_keys_from_correlation(outcome.get("correlation")) if k.domain is anchor.domain]
        link_ok = any(anchor.links(key) for key in same_domain)
        link_detail = (
            f"same-domain key match ({anchor.domain.value})" if link_ok else "no same-domain key match with anchor"
        )
    if not link_ok and exposure_linkage is not None:
        raw_correlation = outcome.get("correlation")
        correlation: Mapping[str, Any] = raw_correlation if isinstance(raw_correlation, Mapping) else {}
        link_ok = outcome_links_exposure(exposure_linkage, correlation)
        link_detail = "exposure linkage match (D-05)" if link_ok else "no exposure linkage match"
    hops.append(TraceHop(hop="outcome_link", ok=link_ok, detail=link_detail))

    return TraceReport(traceable=all(hop.ok for hop in hops), hops=tuple(hops))


__all__ = [
    "ATTRIBUTION_DOMAINS",
    "ATTRIBUTION_SCHEMA_VERSION",
    "AttributionDomain",
    "AttributionKeyError",
    "AttributionStatus",
    "AttributionVerdict",
    "AttributionDenominator",
    "DomainKey",
    "DOMAIN_CORRELATION_KEYS",
    "TraceHop",
    "TraceReport",
    "anchor_observation_status",
    "attribute_outcome",
    "attribute_outcome_entry",
    "derive_attribution_sample_id",
    "domain_keys_from_correlation",
    "trace_receipt_to_outcome",
]

# import 期断言：用户响应词表唯一权威 = D-05（accepted/rejected/started + 显式 edited）。
# DATA_AND_GRAPH：「既有枚举没有 edited 时走显式契约扩展，不填假 accepted」——
# D-05 LifecycleEventType 已含显式 EDITED 成员；事件身份 (decision_id, event_type,
# dedupe_subkey) 保证 edited 与 accepted 是不同身份、互不改写。
assert (
    frozenset(
        {
            LifecycleEventType.ACCEPTED.value,
            LifecycleEventType.EDITED.value,
            LifecycleEventType.REJECTED.value,
            LifecycleEventType.STARTED.value,
        }
    )
    == USER_RESPONSE_EVENT_TYPES
), "USER_RESPONSE_EVENT_TYPES must remain the D-05 four-value closed set (accepted/edited/rejected/started)"
assert DEFAULT_OBSERVATION_WINDOW_HOURS == 72
