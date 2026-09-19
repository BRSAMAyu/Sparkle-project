"""C-01 · DecisionContext —— Aurora / Router / Planner 共同消费的最小高信号决策上下文契约。

冻结声明（v3/07_tasks/cards/C-01.md，gate V3-2，locks context-contract）：
- ContextPack（app/core/context_pack.py）是唯一上下文契约；DecisionContext 是它在
  “决策面”上的扩展视图，挂在 ``ContextPack.decision_context``（可选字段，默认 None），
  **不是**平行的 UserContextV3 真源。
- 事实语义全部来自既有权威：
  - UserStateV1（app/state_aggregator/schema.py）仍是 UserWorldSnapshot 唯一权威，
    signal 只是对其 envelope 的投影 + ref 指针；
  - memory/preferences/goals/episodic 的真源仍是 memory DB 表；
  - TTL 唯一真源是 StateAggregatorService.FIELD_TTLS_SECONDS（builder 侧传入）。
- 每个字段携带 ref / type / scope / ttl_or_epoch / version / why_included。
- 契约快照 parity guard：backend/tests/contract/test_decision_context_contract.py
  冻结字段集、封闭词表与序列化面。任何变更都需要 bump DECISION_CONTEXT_SCHEMA_VERSION
  并过两位 reviewer。

消费方接入点：
- Router（orchestration/dual_core_router）：读 signals（engagement/emotion/srl）
  + intent/route_intent/focus_mode，替代从 ContextBuilderMixin 平行 dict 里二次取数；
- Aurora（app/aurora）：读 items manifest（ref/relevance/why_included 即 provenance，
  对应 AURORA_V3 的 relevant memories + provenance 与 memory_use_receipts）；
- Planner（orchestration/plan_review_service 等）：读 items_of_type("goal")/
  items_in_scope("plan") + plan ref， replan 时从 pack 直接取决策面。
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import UUID

from app.state_aggregator.schema import StateFieldEnvelope, UserStateFieldName

DECISION_CONTEXT_SCHEMA_VERSION = "decision_context.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本）
# ---------------------------------------------------------------------------

DECISION_SCOPES: frozenset[str] = frozenset({"user", "session", "plan", "task", "global"})

DECISION_REF_SCHEMES: frozenset[str] = frozenset({"memory", "user_state", "plan", "document", "profile"})

DECISION_INCLUDE_REASONS: frozenset[str] = frozenset(
    {
        "rank_policy",  # memory rank policy 打分选中
        "evidence_order",  # 未启用 rank policy 时按 evidence_score 排序选中
        "budget_carryover",  # 在预算裁剪中幸存（候选 > 注入）
        "semantic_gate",  # 通过语义门控阈值
        "focus_mode",  # focus mode 权重参与选择
        "plan_scope",  # plan 关联材料
        "state_signal",  # 决策关键 UserStateV1 信号
        "direct_request",  # 用户本轮显式要求（如上传材料）
        "diversity",  # section 多样性保位
        "fallback",  # 降级路径保底注入
    }
)

DECISION_ITEM_TYPES: frozenset[str] = frozenset(
    {
        "preference",
        "goal",
        "episodic_memory",
        "plan",
        "user_state_signal",
        "document_chunk",
    }
)

# 默认高信号 UserState 字段集（冻结）：Router/Aurora 的最小共同需要。
# task/context_sufficiency 依赖当轮 parse，待 Planner 链路传入 turn parse 后再加。
DEFAULT_DECISION_SIGNAL_FIELDS: tuple[UserStateFieldName, ...] = (
    "engagement_state",
    "emotion_hint",
    "srl_phase",
)


def memory_ref(kind: str, item_id: Any) -> str:
    """memory 真源指针，如 ``memory://episodic/<uuid>``（id 可解析回 DB 记录）。"""
    return f"memory://{kind}/{item_id}"


def user_state_ref(field_name: str) -> str:
    return f"user_state://{field_name}"


def plan_ref(plan_id: Any) -> str:
    return f"plan://{plan_id}"


def hash_query_text(text: str | None) -> str | None:
    """查询文本的短哈希（cache key 组件 / 观测关联用；不落原文，PII 最小化）。"""
    normalized = str(text or "").strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# 契约 dataclass（字段集被 tests/contract/test_decision_context_contract.py 冻结）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextItemDescriptor:
    """pack 内单个被注入 item 的来源/语义描述（provenance manifest 条目）。"""

    ref: str
    type: str
    scope: str
    why_included: tuple[str, ...]
    ttl_seconds: int | None = None
    epoch: str | None = None
    relevance: float | None = None
    version: str = DECISION_CONTEXT_SCHEMA_VERSION

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        scheme = self.ref.split("://", 1)[0] if "://" in self.ref else ""
        if scheme not in DECISION_REF_SCHEMES:
            violations.append(f"item {self.ref}: unknown ref scheme {scheme!r}")
        if self.type not in DECISION_ITEM_TYPES:
            violations.append(f"item {self.ref}: unknown type {self.type!r}")
        if self.scope not in DECISION_SCOPES:
            violations.append(f"item {self.ref}: unknown scope {self.scope!r}")
        if not self.why_included or not set(self.why_included) <= DECISION_INCLUDE_REASONS:
            violations.append(f"item {self.ref}: why_included empty or out of vocabulary")
        if self.ttl_seconds is None and self.epoch is None:
            violations.append(f"item {self.ref}: ttl_seconds and epoch both missing (ttl_or_epoch rule)")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "type": self.type,
            "scope": self.scope,
            "why_included": list(self.why_included),
            "ttl_seconds": self.ttl_seconds,
            "epoch": self.epoch,
            "relevance": self.relevance,
            "version": self.version,
        }


@dataclass(frozen=True)
class DecisionStateSignal:
    """UserStateV1 单字段的最小高信号投影（真源仍是 state_aggregator）。"""

    name: str
    ref: str
    value: dict[str, Any]
    why_included: tuple[str, ...] = ("state_signal",)
    ttl_seconds: int | None = None
    epoch: str | None = None
    computed_at: datetime | str | None = None
    freshness_seconds: int | None = None
    source_snapshot_ids: tuple[str, ...] = ()
    version: str = DECISION_CONTEXT_SCHEMA_VERSION

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.ref != user_state_ref(self.name):
            violations.append(f"signal {self.name}: ref must be {user_state_ref(self.name)!r}")
        if self.ttl_seconds is None and self.epoch is None:
            violations.append(f"signal {self.name}: ttl_seconds and epoch both missing (ttl_or_epoch rule)")
        if not isinstance(self.value, dict):
            violations.append(f"signal {self.name}: value must be a dict projection")
        if not self.why_included or not set(self.why_included) <= DECISION_INCLUDE_REASONS:
            violations.append(f"signal {self.name}: why_included empty or out of vocabulary")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ref": self.ref,
            "value": self.value,
            "why_included": list(self.why_included),
            "ttl_seconds": self.ttl_seconds,
            "epoch": self.epoch,
            "computed_at": _iso(self.computed_at),
            "freshness_seconds": self.freshness_seconds,
            "source_snapshot_ids": list(self.source_snapshot_ids),
            "version": self.version,
        }


@dataclass(frozen=True)
class DecisionContext:
    """决策面契约：本次 pack 构建服务于哪个决策、装入了什么、为何装入、降级了什么。"""

    user_id: UUID
    intent: str
    schema_version: str = DECISION_CONTEXT_SCHEMA_VERSION
    route_intent: str | None = None
    focus_mode: str | None = None
    plan_id: UUID | None = None
    query_text_hash: str | None = None
    signals: tuple[DecisionStateSignal, ...] = ()
    items: tuple[ContextItemDescriptor, ...] = ()
    omitted_counts: Mapping[str, int] = field(default_factory=dict)
    degraded_fields: tuple[str, ...] = ()
    built_at: datetime | None = None

    def __post_init__(self) -> None:
        # 冻结对象：omitted_counts 固化为只读视图，防下游静默篡改观测面。
        object.__setattr__(self, "omitted_counts", MappingProxyType(dict(self.omitted_counts)))

    # -- 消费便捷接口 -------------------------------------------------------

    def signal(self, name: str) -> DecisionStateSignal | None:
        for entry in self.signals:
            if entry.name == name:
                return entry
        return None

    def items_in_scope(self, scope: str) -> tuple[ContextItemDescriptor, ...]:
        return tuple(item for item in self.items if item.scope == scope)

    def items_of_type(self, item_type: str) -> tuple[ContextItemDescriptor, ...]:
        return tuple(item for item in self.items if item.type == item_type)

    def refs(self) -> tuple[str, ...]:
        return tuple(item.ref for item in self.items) + tuple(entry.ref for entry in self.signals)

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.schema_version != DECISION_CONTEXT_SCHEMA_VERSION:
            violations.append(f"schema_version mismatch: {self.schema_version!r}")
        if not self.intent:
            violations.append("intent must be non-empty")
        for item in self.items:
            violations.extend(item.validate())
        for entry in self.signals:
            violations.extend(entry.validate())
        return tuple(violations)

    def cache_key_components(self) -> dict[str, Any]:
        """V3 Context Compiler cache key 组件（CONTEXT_COMPILER_V3.md §7）。

        决定性组件：user/decision-type/object refs/source epochs/query hash。
        写操作与纠偏请求必须携带新的 query_text_hash，不得用旧 cache 冒充新推理。
        """
        epochs = {entry.epoch for entry in self.signals if entry.epoch}
        epochs.update(item.epoch for item in self.items if item.epoch)
        return {
            "user_id": str(self.user_id),
            "intent": self.intent,
            "route_intent": self.route_intent,
            "focus_mode": self.focus_mode,
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "query_text_hash": self.query_text_hash,
            "schema_version": self.schema_version,
            "item_refs": sorted(item.ref for item in self.items),
            "epochs": sorted(epochs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "user_id": str(self.user_id),
            "intent": self.intent,
            "route_intent": self.route_intent,
            "focus_mode": self.focus_mode,
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "query_text_hash": self.query_text_hash,
            "signals": [entry.to_dict() for entry in self.signals],
            "items": [item.to_dict() for item in self.items],
            "omitted_counts": dict(self.omitted_counts),
            "degraded_fields": list(self.degraded_fields),
            "built_at": _iso(self.built_at),
        }


# ---------------------------------------------------------------------------
# signal 投影（每字段的最小高信号 value 形状，冻结）
# ---------------------------------------------------------------------------

SIGNAL_VALUE_PROJECTIONS: Mapping[str, Callable[[Any], dict[str, Any]]] = {
    "engagement_state": lambda v: {
        "last_active_at": _iso(v.last_active_at),
        "session_count_7d": int(v.session_count_7d or 0),
        "streak": int(v.streak or 0),
    },
    "emotion_hint": lambda v: {
        "dominant_sentiment": v.dominant_sentiment,
        "sentiment_distribution": dict(v.sentiment_distribution or {}),
        "emotional_block_detected": bool(v.emotional_block_detected),
    },
    "srl_phase": lambda v: {
        "current_phase": v.current_phase,
        "phase_started_at": _iso(v.phase_started_at),
        "confidence": v.confidence,
        "source": v.source,
    },
}


def _default_signal_projection(value: Any) -> dict[str, Any]:
    """未显式登记投影的字段：递归投影为 JSON 安全 dict（日期转 ISO）。"""

    def _convert(item: Any) -> Any:
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, dict):
            return {key: _convert(entry) for key, entry in item.items()}
        if isinstance(item, (list, tuple)):
            return [_convert(entry) for entry in item]
        if dataclasses.is_dataclass(item) and not isinstance(item, type):
            return {f.name: _convert(getattr(item, f.name)) for f in dataclasses.fields(item)}
        return item

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _convert(value)
    return {"value": _convert(value)}


def state_signal_from_envelope(
    field_name: UserStateFieldName,
    envelope: StateFieldEnvelope[Any],
    *,
    ttl_map: Mapping[str, int],
    epoch: str,
) -> DecisionStateSignal:
    """从 UserStateV1 envelope 构造 DecisionStateSignal（投影 + 权威 TTL + ref）。"""
    projection = SIGNAL_VALUE_PROJECTIONS.get(field_name, _default_signal_projection)
    return DecisionStateSignal(
        name=field_name,
        ref=user_state_ref(field_name),
        value=projection(envelope.value),
        why_included=("state_signal",),
        ttl_seconds=int(ttl_map[field_name]),
        epoch=epoch,
        computed_at=envelope.computed_at,
        freshness_seconds=envelope.freshness_seconds,
        source_snapshot_ids=tuple(envelope.source_snapshot_ids or ()),
    )


# 供消费方做字段集自检的便捷导出（契约真源是 dataclass 本身）
CONTEXT_ITEM_DESCRIPTOR_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(ContextItemDescriptor))
DECISION_STATE_SIGNAL_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(DecisionStateSignal))
DECISION_CONTEXT_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(DecisionContext))
