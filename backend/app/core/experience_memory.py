"""M-06 · Experience Memory 契约 —— 情境→干预→结果经验的只读投影（纯函数层）。

MEMORY_V3 §5 Experience Memory 的核心 payload 在本层的映射：

    situation signature → ``SituationSignature``（D-05 投影四元组，直接复用）
    intervention        → ``signature.intervention_type``（A-01 目录，本层零新名）
    execution mode      → ``signature.execution_mode``（human/agent/hybrid）
    outcome             → ``observed_with_positive`` / ``observed_with_negative``
                          （「与何种方向的结果共同出现」——相关性计数，非效果断言）
    user feedback       → ``feedback``（D-05 摘要漏斗面 accepted/started 计数）
    evidence count      → ``evidence_count``（观察子集 n_positive + n_negative）
    context boundary    → ``context_boundary``（scope + 观察窗 + 生成时点）

**灵魂红线（卡面 + DATA_FLYWHEEL §5「把相关性写成因果」禁令）**：

1. **无 outcome 不标 effective**：方向判定谓词（``has_positive_association_evidence``
   等）只读观察子集的两个计数，删失/unknown/exposure 计数在任何路径上都
   进不了它们。censored 三态与 unknown 原样保留在记录里（观察完整性面），
   但绝不产生方向证据。变异守卫：``tests/contract/test_experience_memory_contract.py``
   把「删失计入正向证据」「censored 升档 strength」两类变异钉红。
2. **无因果断言字段**：序列化输出只含相关性语义字段
   （observed_with_* / evidence_count / evidence_strength / rate_interval /
   claim）。唯一允许的 caus 词形键是 ``causal_claim`` 且恒为 ``False``
   （D-05 谦抑措辞层镜像——机器可断言的否定，比缺省更强）。
   ``scan_output_for_causal_assertions`` 是该红线的机制化：对任意嵌套
   payload 扫描禁词字段名 + causal_claim 值 + claim 文本（D-05
   ``FORBIDDEN_CLAIM_TERMS`` 复用），任何违反返回非空清单。
3. **失败等价保留**：``observed_with_negative`` 与正向同权进入 evidence_count
   与档位（D-05 ``association_evidence_tier`` 只看观察数不看方向——本层不
   降级、不隐藏负向记录）；双向召回（``split_by_evidence_direction``）把
   正/负两个方向并列返回，无 outcome 记录进 ``no_outcome_evidence`` 桶
   （保留但无方向）。

**FIX-31 P2-1 消费面（D-05 摘要 cap 5000 ASC 丢最新 + 无 truncated 标记）**：
D-05 的 ``association_summary`` 按 ``occurred_at ASC`` 加载 ``_SUMMARY_EVENT_CAP``
（5000）行——事件集超界时静默丢弃**最新**历史。本层消费侧处理：
- 投影带 ``truncated`` 面（服务层用同谓词 count 探测：行数 > cap 即截断）；
- 截断时 ``completeness_adjusted_strength`` 把档位降一级（accumulated→
  repeated→single_observation→insufficient），``evidence_strength`` 保留 D-05
  原值（真源语义不被本层改写）；
- 检索结果的 ``degraded_confidence`` 面携带截断原因码
  ``d05_summary_cap_exceeded``，消费方（chat/orchestration context 装配）
  可据此降权或不注入。

**与既有管线的边界（不重建真源）**：
- outcome 事实 → D-02 outcome_ledger；生命周期事件与聚合语义 → D-05
  ``intervention_lifecycle``（本层只消费 ``AssociationSummary``/``SliceSummary``
  载体与纯函数，零写路径、零事件、零迁移）；
- M-06 的词表纪律：不向 D-05 冻结词表（39 名词表）添加任何成员；本层
  自有的封闭词表（召回桶名/截断原因码/禁词表）是 M-06 输出结构的一部分，
  由冻结测试钉死；
- ``ExperienceMemoryRecord`` 鸭子类型兼容 M-03 预筛候选契约
  （``id``/``user_id``/``summary``/``occurred_at``/``source_type``/
  ``source_lane``/``epistemic_class``），使真实 ``prefilter_candidates``
  无需修改即可守卫经验记录（M-03 的身份/状态/权限切在检索边界真实执行）。

变更流程：本模块任何词表/字段集/档位语义改动需 bump
``EXPERIENCE_MEMORY_SCHEMA_VERSION`` 并过 reviewer（C-01/D-05 同款纪律）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_ACCUMULATED,
    EVIDENCE_TIER_INSUFFICIENT,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_SINGLE,
    FORBIDDEN_CLAIM_TERMS,
    INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
    AssociationSummary,
    SituationSignature,
    SliceSummary,
)

EXPERIENCE_MEMORY_SCHEMA_VERSION = "experience_memory.m06.v1"

#: MEMORY_V3 §1 记录类型面（M-01 EpistemicClass.EXPERIENCE 的镜像字面）。
EXPERIENCE_RECORD_TYPE = "EXPERIENCE"

#: 投影记录的 source_type / source_lane（M-03 目的面权限可据此封禁；
#: 未注册 lane → classify_episodic_class 走 explicit_class="EXPERIENCE" 路径）。
EXPERIENCE_SOURCE_TYPE = "experience_projection"
EXPERIENCE_SOURCE_LANE = "experience_projection"

# ---------------------------------------------------------------------------
# 召回桶词表（冻结；双向召回 + 无证据保留桶）
# ---------------------------------------------------------------------------

#: 正向相关证据桶：观察到 ≥1 条 positive outcome 共同出现。
DIRECTION_POSITIVE = "observed_with_positive"
#: 负向相关证据桶：观察到 ≥1 条 negative outcome 共同出现（失败等价保留）。
DIRECTION_NEGATIVE = "observed_with_negative"
#: 无 outcome 证据桶：只有 exposure/删失/unknown，无方向（保留，不隐藏）。
BUCKET_NO_OUTCOME_EVIDENCE = "no_outcome_evidence"

EXPERIENCE_RECALL_BUCKETS: tuple[str, ...] = (DIRECTION_POSITIVE, DIRECTION_NEGATIVE, BUCKET_NO_OUTCOME_EVIDENCE)

# ---------------------------------------------------------------------------
# 截断语义（FIX-31 P2-1 消费面）
# ---------------------------------------------------------------------------

#: D-05 摘要 ASC+cap 丢最新历史的截断原因码（冻结）。
SUMMARY_TRUNCATION_REASON = "d05_summary_cap_exceeded"

#: 档位阶梯（降级用；顺序 = 证据强度单调不降）。
_TIER_LADDER: tuple[str, ...] = (
    EVIDENCE_TIER_INSUFFICIENT,
    EVIDENCE_TIER_SINGLE,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_ACCUMULATED,
)


def downgrade_evidence_tier(tier: str) -> str:
    """截断时的档位降一级（insufficient 保持 insufficient）。

    FIX-31 P2-1 消费面动作：读到被截断的摘要时投影降置信。D-05 原档位
    保留在 ``evidence_strength``（真源语义不改写），降级值只出现在
    ``completeness_adjusted_strength``。
    """
    value = str(tier)
    if value not in _TIER_LADDER:
        return EVIDENCE_TIER_INSUFFICIENT  # 未知档位保守降到底
    index = _TIER_LADDER.index(value)
    return _TIER_LADDER[max(0, index - 1)]


# ---------------------------------------------------------------------------
# 无因果断言守卫（验收 ③ 的机制化）
# ---------------------------------------------------------------------------

#: 序列化字段名禁词（effective/success/works/prove/guarantee 族 + D-05 claim
#: 禁词的字段名形态）。任何包含这些子串的输出键都是因果/效果断言字段。
FORBIDDEN_OUTPUT_FIELD_TERMS: tuple[str, ...] = (
    "effective",
    "success",
    "works",
    "prove",
    "guarante",
    "导致",
    "使得",
    "成功率",
    "有效率",
    "证明了",
)

#: 唯一允许的 caus 词形键：恒 False 的机器否定守卫（D-05 谦抑层镜像）。
CAUSAL_GUARD_KEY = "causal_claim"


def scan_output_for_causal_assertions(payload: Any) -> list[str]:
    """扫描任意嵌套 payload 的因果断言违反（空清单 = 干净）。

    三层检查：
    1. 任何 dict 键（递归）不得含 ``FORBIDDEN_OUTPUT_FIELD_TERMS`` 子串
       （``causal_claim`` 除外——它必须是 False 值的否定守卫）；
    2. ``causal_claim`` 键的值必须恒为 ``False``（True 即因果断言）；
    3. ``claim`` 键的字符串值不得命中 D-05 ``FORBIDDEN_CLAIM_TERMS``。
    """
    violations: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                key_str = str(key)
                child_path = f"{path}.{key_str}" if path else key_str
                if any(term in key_str for term in FORBIDDEN_OUTPUT_FIELD_TERMS):
                    violations.append(f"forbidden field name: {child_path}")
                if key_str == CAUSAL_GUARD_KEY and value is not False:
                    violations.append(f"causal_claim must be False: {child_path}={value!r}")
                if key_str == "claim" and isinstance(value, str):
                    for term in FORBIDDEN_CLAIM_TERMS:
                        if term in value:
                            violations.append(f"forbidden claim term {term!r} in {child_path}")
                _walk(value, child_path)
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(payload, "")
    return violations


# ---------------------------------------------------------------------------
# 数据模型（Work 1：situation signature / intervention / mode / outcome /
# feedback / evidence count 的投影载体）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperienceMemoryRecord:
    """一条经验记忆（一个情境切片的只读投影；不落库、不产事件）。

    鸭子类型兼容 M-03 预筛候选（``id``/``user_id``/``summary``/
    ``occurred_at``/``source_type``/``source_lane``/``epistemic_class``）：
    ``record_kind`` 判为 episodic、``derive_status`` 判为 active、
    ``derive_scope`` 判为 global、``classify_episodic_class`` 走显式
    EXPERIENCE——真实 ``prefilter_candidates`` 可直接守卫本记录。

    红线字段语义：
    - ``observed_with_positive`` / ``observed_with_negative``：白名单 outcome
      与该干预**共同出现**的方向分解（相关性计数；D-05 n_positive/n_negative
      原样投影）；
    - ``censored_*`` / ``n_unknown_status``：观察完整性面（保留但永不产生
      方向证据、不进 evidence_count）；
    - ``feedback``：D-05 摘要漏斗面（accepted/started；edit/reject 计数是
      D-05 载体的后续扩展面，本层不重聚合事件去补——不复制聚合真源）；
    - ``evidence_strength``：D-05 档位原值；``completeness_adjusted_strength``：
      截断时降一级（FIX-31 P2-1）。
    """

    record_id: str
    user_id: str | None
    signature: SituationSignature
    n_exposed: int
    n_accepted: int = 0
    n_started: int = 0
    observed_with_positive: int = 0
    observed_with_negative: int = 0
    censored_not_yet_due: int = 0
    censored_window_closed: int = 0
    censored_user_churned: int = 0
    n_unknown_status: int = 0
    positive_association_rate: float = 0.0
    rate_interval: tuple[float, float] = (0.0, 1.0)
    weighted_positive_rate: float = 0.0
    evidence_strength: str = EVIDENCE_TIER_INSUFFICIENT
    claim: str = ""
    scope: tuple[str, ...] = ()
    since: datetime | None = None
    until: datetime | None = None
    generated_at: datetime | None = None
    truncated: bool = False

    # -- MEMORY_V3 §5 payload 面 ------------------------------------------------

    @property
    def evidence_count(self) -> int:
        """重复证据计数 = 观察子集大小（正+负；失败等价计入）。"""
        return self.observed_with_positive + self.observed_with_negative

    @property
    def intervention(self) -> str:
        return self.signature.intervention_type

    @property
    def execution_mode(self) -> str:
        return self.signature.execution_mode

    @property
    def feedback(self) -> dict[str, int]:
        return {"accepted": self.n_accepted, "started": self.n_started}

    @property
    def outcome_face(self) -> dict[str, int]:
        return {
            "observed_with_positive": self.observed_with_positive,
            "observed_with_negative": self.observed_with_negative,
            "censored_not_yet_due": self.censored_not_yet_due,
            "censored_window_closed": self.censored_window_closed,
            "censored_user_churned": self.censored_user_churned,
            "unknown": self.n_unknown_status,
        }

    @property
    def context_boundary(self) -> dict[str, Any]:
        return {
            "scope": list(self.scope),
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

    @property
    def completeness_adjusted_strength(self) -> str:
        """FIX-31 P2-1：截断摘要的降置信档位（未截断 = D-05 原档位）。"""
        if self.truncated:
            return downgrade_evidence_tier(self.evidence_strength)
        return self.evidence_strength

    # -- 灵魂红线：方向判定谓词（只读观察子集）----------------------------------

    @property
    def has_outcome_evidence(self) -> bool:
        """有白名单 outcome 共同出现（= 有方向可谈）。删失/unknown/exposure 永不算。"""
        return self.evidence_count > 0

    @property
    def has_positive_association_evidence(self) -> bool:
        """观察到 ≥1 条 positive outcome 共同出现（相关性，非效果断言）。"""
        return self.observed_with_positive > 0

    @property
    def has_negative_association_evidence(self) -> bool:
        """观察到 ≥1 条 negative outcome 共同出现（失败等价保留）。"""
        return self.observed_with_negative > 0

    # -- M-03 预筛候选鸭子类型面 --------------------------------------------------

    @property
    def id(self) -> str:  # noqa: A003 — M-03 候选契约键名
        return self.record_id

    @property
    def summary(self) -> str:
        """自然语言面 = D-05 非因果 claim 文案（M-03 record_kind / token 估算消费）。"""
        return self.claim

    @property
    def occurred_at(self) -> datetime | None:
        return self.generated_at

    @property
    def source_type(self) -> str:
        return EXPERIENCE_SOURCE_TYPE

    @property
    def source_lane(self) -> str:
        return EXPERIENCE_SOURCE_LANE

    @property
    def epistemic_class(self) -> str:
        return EXPERIENCE_RECORD_TYPE

    # -- 序列化（唯一权威）--------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": EXPERIENCE_MEMORY_SCHEMA_VERSION,
            "record_id": self.record_id,
            "type": EXPERIENCE_RECORD_TYPE,
            "user_id": self.user_id,
            "situation_signature": self.signature.as_dict(),
            "intervention": self.intervention,
            "execution_mode": self.execution_mode,
            "n_exposed": self.n_exposed,
            "n_accepted": self.n_accepted,
            "n_started": self.n_started,
            "outcome": self.outcome_face,
            "feedback": self.feedback,
            "evidence_count": self.evidence_count,
            "positive_association_rate": round(self.positive_association_rate, 6),
            "rate_interval": [round(self.rate_interval[0], 6), round(self.rate_interval[1], 6)],
            "weighted_positive_rate": round(self.weighted_positive_rate, 6),
            "evidence_strength": self.evidence_strength,
            "completeness_adjusted_strength": self.completeness_adjusted_strength,
            "truncated": self.truncated,
            "claim": self.claim,
            "causal_claim": False,
            "context_boundary": self.context_boundary,
        }
        return payload


#: 记录 payload 顶层键集（冻结；``to_dict`` 恰好产出这些键）。
EXPERIENCE_RECORD_PAYLOAD_KEYS: tuple[str, ...] = (
    "schema_version",
    "record_id",
    "type",
    "user_id",
    "situation_signature",
    "intervention",
    "execution_mode",
    "n_exposed",
    "n_accepted",
    "n_started",
    "outcome",
    "feedback",
    "evidence_count",
    "positive_association_rate",
    "rate_interval",
    "weighted_positive_rate",
    "evidence_strength",
    "completeness_adjusted_strength",
    "truncated",
    "claim",
    "causal_claim",
    "context_boundary",
)

#: outcome 面键集（冻结）。
EXPERIENCE_OUTCOME_FACE_KEYS: tuple[str, ...] = (
    "observed_with_positive",
    "observed_with_negative",
    "censored_not_yet_due",
    "censored_window_closed",
    "censored_user_churned",
    "unknown",
)

#: feedback 面键集（冻结）。
EXPERIENCE_FEEDBACK_KEYS: tuple[str, ...] = ("accepted", "started")


@dataclass(frozen=True)
class ExperienceProjection:
    """一个 scope（user/global）的经验记忆投影（只读派生视图）。

    ``watermark`` 来自 D-05 摘要内水印（事件集内容印记；服务层另用公开
    ``watermark()`` 做缓存失效键——FIX-31 P3-1 已登记两者在 >1000 事件时
    构造性不等，缓存 TTL 是消费侧兜底）。
    """

    scope: tuple[str, ...]
    user_id: str | None
    generated_at: datetime
    since: datetime | None
    until: datetime | None
    watermark: str
    truncated: bool = False
    truncation_reason: str = ""
    records: tuple[ExperienceMemoryRecord, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXPERIENCE_MEMORY_SCHEMA_VERSION,
            "source_schema_version": INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
            "scope": list(self.scope),
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "watermark": self.watermark,
            "truncated": self.truncated,
            "truncation_reason": self.truncation_reason,
            "n_records": len(self.records),
            "records": [record.to_dict() for record in self.records],
        }


#: 投影 payload 顶层键集（冻结）。
EXPERIENCE_PROJECTION_PAYLOAD_KEYS: tuple[str, ...] = (
    "schema_version",
    "source_schema_version",
    "scope",
    "user_id",
    "generated_at",
    "since",
    "until",
    "watermark",
    "truncated",
    "truncation_reason",
    "n_records",
    "records",
)


# ---------------------------------------------------------------------------
# 投影纯函数（D-05 载体 → 经验记忆记录）
# ---------------------------------------------------------------------------


def derive_experience_record_id(
    *,
    scope: Sequence[str],
    signature: SituationSignature,
    since: datetime | None,
    until: datetime | None,
) -> str:
    """确定性记录 id（``expmem_<sha256[:16]>``，D-01/D-05 派生风格）。

    同一 (scope, signature, window) 恒产同 id：投影幂等，消费方可安全去重。
    """
    seed = json.dumps(
        {
            "schema": EXPERIENCE_MEMORY_SCHEMA_VERSION,
            "scope": [str(part) for part in scope],
            "signature": signature.as_dict(),
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "expmem_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def project_slice(
    slice_summary: SliceSummary,
    *,
    scope: Sequence[str],
    user_id: str | None,
    since: datetime | None,
    until: datetime | None,
    generated_at: datetime | None,
    truncated: bool,
) -> ExperienceMemoryRecord:
    """单个 D-05 切片摘要 → 一条经验记忆记录（字段一一对应，零语义改写）。

    红线：n_censored_* / n_unknown 只进 outcome 面的完整性计数，不进
    evidence_count / 方向谓词 / 档位（档位由 D-05 按 n_observed 判定，本层
    不重算——不复制聚合真源）。
    """
    signature = slice_summary.signature
    return ExperienceMemoryRecord(
        record_id=derive_experience_record_id(scope=scope, signature=signature, since=since, until=until),
        user_id=user_id,
        signature=signature,
        n_exposed=slice_summary.n_exposed,
        n_accepted=slice_summary.n_accepted,
        n_started=slice_summary.n_started,
        observed_with_positive=slice_summary.n_positive,
        observed_with_negative=slice_summary.n_negative,
        censored_not_yet_due=slice_summary.n_censored_not_yet_due,
        censored_window_closed=slice_summary.n_censored_window_closed,
        censored_user_churned=slice_summary.n_censored_user_churned,
        n_unknown_status=slice_summary.n_unknown,
        positive_association_rate=slice_summary.positive_association_rate,
        rate_interval=tuple(slice_summary.rate_interval),  # type: ignore[arg-type]
        weighted_positive_rate=slice_summary.weighted_positive_rate,
        evidence_strength=slice_summary.evidence_strength,
        claim=slice_summary.claim,
        scope=tuple(str(part) for part in scope),
        since=since,
        until=until,
        generated_at=generated_at,
        truncated=truncated,
    )


def project_summary(
    summary: AssociationSummary,
    *,
    truncated: bool = False,
) -> ExperienceProjection:
    """D-05 保守关联摘要 → 经验记忆投影（纯函数；截断标志由服务层探测传入）。"""
    user_id = summary.scope[1] if summary.scope[0] == "user" and len(summary.scope) > 1 else None
    generated_at = summary.generated_at
    records = tuple(
        project_slice(
            slice_summary,
            scope=summary.scope,
            user_id=user_id,
            since=summary.since,
            until=summary.until,
            generated_at=generated_at,
            truncated=truncated,
        )
        for slice_summary in summary.slices
    )
    return ExperienceProjection(
        scope=tuple(str(part) for part in summary.scope),
        user_id=user_id,
        generated_at=generated_at,
        since=summary.since,
        until=summary.until,
        watermark=summary.watermark,
        truncated=truncated,
        truncation_reason=SUMMARY_TRUNCATION_REASON if truncated else "",
        records=records,
    )


# ---------------------------------------------------------------------------
# 检索接口（Work 3：相似情境双向召回）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperienceContextQuery:
    """Context retrieval 查询（chat/orchestration 装配 context 时给出）。

    情境轴 = goal_type + friction_tag（+ execution_mode 可选）；intervention_type
    是回答轴（"何曾有效/无效"列出的是干预），也可约束为问某一干预。所有维度
    可选：未约束维度保守放行（M-03 unconstrained 纪律），已约束维度精确匹配
    （"unknown"/"unattributed" 不匹配任何显式约束——保守，不猜）。
    """

    user_id: str
    goal_type: str | None = None
    friction_tag: str | None = None
    execution_mode: str | None = None
    intervention_type: str | None = None
    purpose: str = "llm_context"  # M-03 RETRIEVAL_PURPOSES 词表（服务层校验）
    since: datetime | None = None
    until: datetime | None = None
    now: datetime | None = None
    user_last_active_at: datetime | None = None
    max_records_per_direction: int = 20

    def constraints(self) -> dict[str, str]:
        """已约束的签名维度（值非 None 才进约束）。"""
        return {
            key: str(value)
            for key, value in {
                "goal_type": self.goal_type,
                "friction_tag": self.friction_tag,
                "execution_mode": self.execution_mode,
                "intervention_type": self.intervention_type,
            }.items()
            if value is not None
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "goal_type": self.goal_type,
            "friction_tag": self.friction_tag,
            "execution_mode": self.execution_mode,
            "intervention_type": self.intervention_type,
            "purpose": self.purpose,
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
        }


def signature_matches_query(constraints: Mapping[str, str], signature: SituationSignature) -> bool:
    """确定性情境匹配：每个已约束维度精确相等才匹配（未约束维度放行）。"""
    signature_dict = signature.as_dict()
    return all(signature_dict.get(key) == value for key, value in constraints.items())


def rank_experience_records(
    records: Iterable[ExperienceMemoryRecord],
) -> list[ExperienceMemoryRecord]:
    """排序：证据计数降序，平手按签名元组升序（确定性输出）。"""
    return sorted(records, key=lambda record: (-record.evidence_count, record.signature.as_tuple()))


def split_by_evidence_direction(
    records: Sequence[ExperienceMemoryRecord],
) -> dict[str, tuple[ExperienceMemoryRecord, ...]]:
    """双向召回分桶（验收 ①）。

    - ``observed_with_positive``：n_positive > 0（有正向共同出现证据）；
    - ``observed_with_negative``：n_negative > 0（失败等价保留，同排序）；
    - ``no_outcome_evidence``：evidence_count == 0（删失/unknown-only——保留
      观察完整性，不隐藏；它们的 claim 恒为「尚无足够观察样本」族）。

    混合方向记录（正负皆有）同时进两个方向桶——计数承载细节，不删信息。
    """
    positive = tuple(record for record in records if record.has_positive_association_evidence)
    negative = tuple(record for record in records if record.has_negative_association_evidence)
    none = tuple(record for record in records if not record.has_outcome_evidence)
    return {DIRECTION_POSITIVE: positive, DIRECTION_NEGATIVE: negative, BUCKET_NO_OUTCOME_EVIDENCE: none}


@dataclass(frozen=True)
class ExperienceContextResult:
    """Context retrieval 结果：该用户相似情境下「何曾与正/负结果共同出现」。"""

    schema_version: str
    query: ExperienceContextQuery
    observed_with_positive: tuple[ExperienceMemoryRecord, ...] = ()
    observed_with_negative: tuple[ExperienceMemoryRecord, ...] = ()
    no_outcome_evidence: tuple[ExperienceMemoryRecord, ...] = ()
    watermark: str = ""
    truncated: bool = False
    truncation_reason: str = ""
    prefilter_payloads: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    @property
    def degraded_confidence(self) -> dict[str, Any]:
        """FIX-31 P2-1 消费面：截断时的降置信标记（消费方据此降权/不注入）。"""
        return {
            "truncated": self.truncated,
            "reason": self.truncation_reason,
            "note": (
                "D-05 summary cap exceeded (ASC load drops newest history); "
                "completeness_adjusted_strength is one tier lower than evidence_strength"
                if self.truncated
                else ""
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "query": self.query.to_dict(),
            DIRECTION_POSITIVE: [record.to_dict() for record in self.observed_with_positive],
            DIRECTION_NEGATIVE: [record.to_dict() for record in self.observed_with_negative],
            BUCKET_NO_OUTCOME_EVIDENCE: [record.to_dict() for record in self.no_outcome_evidence],
            "counts": {
                DIRECTION_POSITIVE: len(self.observed_with_positive),
                DIRECTION_NEGATIVE: len(self.observed_with_negative),
                BUCKET_NO_OUTCOME_EVIDENCE: len(self.no_outcome_evidence),
            },
            "watermark": self.watermark,
            "truncated": self.truncated,
            "degraded_confidence": self.degraded_confidence,
            "prefilter": {name: dict(payload) for name, payload in self.prefilter_payloads.items()},
        }


#: 检索结果 payload 顶层键集（冻结）。
EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS: tuple[str, ...] = (
    "schema_version",
    "query",
    DIRECTION_POSITIVE,
    DIRECTION_NEGATIVE,
    BUCKET_NO_OUTCOME_EVIDENCE,
    "counts",
    "watermark",
    "truncated",
    "degraded_confidence",
    "prefilter",
)


__all__ = [
    "EXPERIENCE_MEMORY_SCHEMA_VERSION",
    "EXPERIENCE_RECORD_TYPE",
    "EXPERIENCE_SOURCE_TYPE",
    "EXPERIENCE_SOURCE_LANE",
    "EXPERIENCE_RECALL_BUCKETS",
    "DIRECTION_POSITIVE",
    "DIRECTION_NEGATIVE",
    "BUCKET_NO_OUTCOME_EVIDENCE",
    "SUMMARY_TRUNCATION_REASON",
    "FORBIDDEN_OUTPUT_FIELD_TERMS",
    "CAUSAL_GUARD_KEY",
    "EXPERIENCE_RECORD_PAYLOAD_KEYS",
    "EXPERIENCE_OUTCOME_FACE_KEYS",
    "EXPERIENCE_FEEDBACK_KEYS",
    "EXPERIENCE_PROJECTION_PAYLOAD_KEYS",
    "EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS",
    "ExperienceMemoryRecord",
    "ExperienceProjection",
    "ExperienceContextQuery",
    "ExperienceContextResult",
    "downgrade_evidence_tier",
    "scan_output_for_causal_assertions",
    "derive_experience_record_id",
    "project_slice",
    "project_summary",
    "signature_matches_query",
    "rank_experience_records",
    "split_by_evidence_direction",
]
