"""Memory V3 user-facing Provenance/Scope service (task M-08).

Assembly + ownership layer for the U-03 "Sparkle 对我的理解" face. This module
owns NO new truth: it projects and mutates the existing authorities —

    storage / mutations     M-02 gate + ``MemoryService`` write paths
    epistemic classes       M-01 ``memory_epistemic_contract``
    selfcheck receipts      M-05 ``memory_use_selfcheck`` (closed vocabularies)
    invalidation / epoch    M-07 ``MemoryInvalidationPipeline``
    decision provenance     C-01 ``DecisionContext`` ref scheme (memory://<kind>/<id>)

What this module OWNS is the user-language projection (buckets / source labels
/ confidence tiers / why-this translations) and the strict user-scope gate:
every query filters ``user_id``; cross-user lookups are indistinguishable from
missing ones (``None`` → API 404, runs.py ownership pattern).

Privacy口径 (card work 2): provenance metadata carries WHEN / WHENCE /
CONFIDENCE-TIER only — never raw model parameters, prompt fragments or other
users' data. Where the source is genuinely absent the answer is an honest
``source_known=False``（"来源不明"）, never a guess and never a silent empty
string (acceptance ②).

Receipt contract (card work 3): ``lookup_why_this`` consumes the M-05 receipt
structure (``memory_selfcheck`` payload + ``memory://`` ref + optional pack
linkage) that already flows in ``ContextPack.metadata``; reasons outside the
frozen ``SELF_CHECK_REASONS`` / ``FAST_MODEL_REASONS`` / C-01
``DECISION_INCLUDE_REASONS`` vocabularies are reported as ``known=False``
instead of being invented.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision_context import DECISION_INCLUDE_REASONS, memory_ref
from app.models.context_pack import ContextPackRun
from app.models.memory import (
    EpisodicMemory,
    MemoryCorrection,
    MemoryGoal,
    MemoryPreference,
)
from app.services.memory_epistemic_contract import (
    EpistemicClass,
    MemoryRecordStatus,
    classify_episodic_class,
    derive_scope,
    derive_status,
    preference_write_provenance,
)
from app.services.memory_invalidation_pipeline import (
    MemoryInvalidationPipeline,
    MemoryMutationAction,
)
from app.services.memory_use_selfcheck import (
    FAST_MODEL_REASONS,
    SELF_CHECK_REASONS,
    SELF_CHECK_VERSION,
)

PROVENANCE_SERVICE_VERSION = "memory-v3.m08.v1"

# ---------------------------------------------------------------------------
# Closed vocabularies of the user-language face (frozen; extension is a
# deliberate product decision — mirrors the M-05 vocabulary discipline)
# ---------------------------------------------------------------------------

#: U-03 four groups (MEMORY_AURORA_UI.md) mapped onto M-01 epistemic classes.
PROVENANCE_BUCKETS: frozenset[str] = frozenset({"told", "observed", "uncertain", "effective"})

BUCKET_LABELS: dict[str, str] = {
    "told": "你告诉我的",
    "observed": "我从你的行动中观察到的",
    "uncertain": "我还不确定的",
    "effective": "对你有效过的方法",
}

#: Epistemic class → bucket (EXPERIENCE rows only exist after M-06 projection;
#: the mapping is live so merged M-06 rows land in the right group).
_EPISODIC_CLASS_TO_BUCKET: dict[str, str] = {
    EpistemicClass.FACT.value: "told",
    EpistemicClass.OBSERVATION.value: "observed",
    EpistemicClass.HYPOTHESIS.value: "uncertain",
    EpistemicClass.EXPERIENCE.value: "effective",
}

#: Confidence tiers (card work 2: 置信层级，不复述内部模型参数 — tier only,
#: the raw float is intentionally NOT exposed on this face).
CONFIDENCE_TIERS: dict[str, str] = {
    "confirmed": "已确认",
    "likely": "较有把握",
    "tentative": "初步推断",
}

#: M-05 selfcheck reason → user language (closed-vocabulary translation; the
#: frozen vocabularies are imported, not restated, so drift turns tests red).
SELFCHECK_REASON_LABELS: dict[str, str] = {
    "selfcheck:irrelevant_to_query": "与当轮话题无关，未直接说出来",
    "selfcheck:phatic_query": "当轮只是问候或确认，不需要引用记忆",
    "selfcheck:echoed_in_query": "内容你当轮刚说过，无需重复",
    "selfcheck:recently_surfaced": "最近一次回复已经说过，避免重复",
    "selfcheck:duplicate_in_pack": "与另一条更相关的记忆重复，只保留一份",
    "selfcheck:agreement_bias_risk": "为避免一味附和，这条偏好没有参与表达",
    "selfcheck:fm_semantic_irrelevant": "语义检查判断与当轮话题无关",
    "selfcheck:fm_agreement_bias": "语义检查判断存在迎合风险，未参与表达",
}

#: C-01 why_included reason → user language.
WHY_INCLUDED_LABELS: dict[str, str] = {
    "rank_policy": "按与当轮内容的相关度排序选中",
    "evidence_order": "按证据强度排序选中",
    "budget_carryover": "在上下文容量内保留",
    "semantic_gate": "通过语义相关度检查",
    "focus_mode": "受当前专注模式加权",
    "plan_scope": "与当前学习计划关联",
    "state_signal": "命中你的关键学习状态",
    "direct_request": "你在本轮明确要求使用",
    "diversity": "为覆盖不同类型信息保留",
    "fallback": "上下文不足时的保底信息",
}

#: Source lanes/types that mark a record as user-stated (M-01 explicit tier).
#: Mirrors EXPLICIT_SOURCE_LANES / USER_STATEMENT_SOURCE_TYPES semantics for
#: the label projection without redefining them.
_SOURCE_LABEL_USER_STATED = "你告诉我的"
_SOURCE_LABEL_INFERRED = "系统从你的对话与行为中推断"
_SOURCE_LABEL_OBSERVED = "系统从你的学习行动中记录"
_SOURCE_LABEL_EXPERIENCED = "从对你的帮助效果中总结"
_SOURCE_LABEL_SYSTEM = "系统写入"
_SOURCE_LABEL_UNKNOWN = "来源不明"

#: Goal-domain source types whose write IS the user's own statement (M-08 R2
#: P2-2: create_goal now persists source_type; system captures like
#: plan-approval "event" goals must never land in the told/confirmed bucket).
_GOAL_USER_STATED_SOURCE_TYPES = frozenset({"user_state", "user_created", "user_registered", "chat_preference"})

#: Episodic source_type → user-language whence (extends the existing
#: EPISODIC_SOURCE_LABELS convention in app.api.v1.memory; kept as its own
#: closed map so this service never imports from an API module).
_EPISODIC_SOURCE_TYPE_LABELS: dict[str, str] = {
    "chat": "来自对话记录",
    "text": "来自对话记录",
    "analysis": "来自 AI 分析",
    "user_state": "来自你的设置",
    "user_created": "你手动创建",
    "user_registered": "你注册时填写",
    "behavior_auto": "来自行为记录",
    "behavior": "来自行为记录",
    "document_import": "来自文档导入",
    "document": "来自文档导入",
    "error_book": "来自错题本",
    "plan": "来自学习计划",
    "system": "系统写入",
    "tool_history": "来自工具使用记录",
    "seed_library": "来自种子库",
    "seed_item": "来自种子条目",
    "translation": "来自翻译",
}

# 值为异构 SQLAlchemy 模型类，列访问（id/user_id/deleted_at/updated_at）走
# 动态映射——显式 type[Any] 承接该既有松散性（同文件 record 形参同为 Any）。
_SUPPORTED_KINDS: dict[str, type[Any]] = {
    "episodic": EpisodicMemory,
    "preference": MemoryPreference,
    "goal": MemoryGoal,
}

#: Per-kind scan bound for the list face (see ``list_items``).
_LIST_SCAN_CAP = 1000

# Startup-time vocabulary guards (M-05 同款纪律): the user-language label maps
# must cover EXACTLY the frozen upstream vocabularies — an upstream reason
# addition/rename turns this red at import time instead of silently surfacing
# honest-unknown labels for live reasons.
assert set(WHY_INCLUDED_LABELS) == set(DECISION_INCLUDE_REASONS), (
    "M-08 WHY_INCLUDED_LABELS drifted from C-01 DECISION_INCLUDE_REASONS: "
    f"{set(WHY_INCLUDED_LABELS) ^ set(DECISION_INCLUDE_REASONS)}"
)
assert set(SELFCHECK_REASON_LABELS) == set(SELF_CHECK_REASONS | FAST_MODEL_REASONS), (
    "M-08 SELFCHECK_REASON_LABELS drifted from M-05 selfcheck vocabularies: "
    f"{set(SELFCHECK_REASON_LABELS) ^ set(SELF_CHECK_REASONS | FAST_MODEL_REASONS)}"
)
assert set(_EPISODIC_CLASS_TO_BUCKET) == {
    EpistemicClass.FACT.value,
    EpistemicClass.OBSERVATION.value,
    EpistemicClass.HYPOTHESIS.value,
    EpistemicClass.EXPERIENCE.value,
}, "M-08 bucket mapping drifted from the M-01 episodic epistemic classes"

# MemoryCorrection actions that are user-visible governance events (read-side
# filter for the source history; write side stays owned by MemoryService).
# M-08 R2 P3-6: user_update (goal field edit) and scope_update (goal linkage)
# are written by this very service's audit legs — omitting them hid M-08's own
# governance events from the history it renders.
_USER_GOVERNANCE_ACTIONS: frozenset[str] = frozenset(
    {
        "retract",
        "delete",
        "reject",
        "no_longer_applicable",
        "user_edit",
        "user_edit_supersede",
        "user_update",
        "scope_pause",
        "scope_resume",
        "scope_update",
        "confirm",
        "memory_reference_accepted",
        "memory_reference_corrected",
        "memory_reference_ignored",
        "memory_reference_denied",
    }
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def parse_memory_ref(ref: str) -> tuple[str, UUID]:
    """Parse a ``memory://<kind>/<uuid>`` receipt ref (C-01 scheme member).

    Raises ``ValueError`` on malformed refs, unknown schemes or unsupported
    kinds — the API maps that to 422 (never a silent default).
    """
    text = str(ref or "").strip()
    scheme, _, rest = text.partition("://")
    if scheme != "memory" or not rest:
        raise ValueError(f"memory_ref must use the memory://<kind>/<id> scheme: {text!r}")
    kind, _, raw_id = rest.partition("/")
    if not raw_id or kind not in _SUPPORTED_KINDS:
        raise ValueError(f"memory_ref has unsupported kind {kind!r}")
    return kind, UUID(raw_id)  # ValueError on bad uuid propagates to caller


class MemoryProvenanceNotFoundError(Exception):
    """Uniform not-found for cross-user AND missing records (no existence leak)."""


class MemoryProvenanceConflictError(Exception):
    """Downstream truth source declined the mutation (honest failure)."""


class MemoryProvenanceService:
    def __init__(self, db: AsyncSession, redis_client: Any | None = None):
        self.db = db
        self.redis = redis_client

    # ------------------------------------------------------------------
    # Ownership-scoped record access (the isolation gate)
    # ------------------------------------------------------------------

    async def _get_record(self, user_id: UUID, kind: str, memory_id: UUID, *, for_update: bool = False):
        model = _SUPPORTED_KINDS.get(kind)
        if model is None:
            raise ValueError(f"Unsupported memory kind: {kind}")
        stmt = select(model).where(
            model.id == memory_id,
            model.user_id == user_id,  # isolation: cross-user == missing
            model.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise MemoryProvenanceNotFoundError(f"{kind} memory {memory_id} not found")
        return record

    # ------------------------------------------------------------------
    # User-language projections
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_tier(record: Any, *, explicit: bool) -> tuple[str, str]:
        """Tier + label from provenance and confidence bands (no raw params).

        Explicit user statements are 已确认 by definition; inferred records are
        较有把握 (>=0.6) or 初步推断 — an inferred record never reports 已确认
        regardless of its internal score.
        """
        if explicit:
            return "confirmed", CONFIDENCE_TIERS["confirmed"]
        confidence = getattr(record, "confidence", None)
        if confidence is None:
            confidence = getattr(record, "evidence_score", None)
        try:
            value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            value = None
        if value is not None and value >= 0.6:
            return "likely", CONFIDENCE_TIERS["likely"]
        return "tentative", CONFIDENCE_TIERS["tentative"]

    @classmethod
    def _bucket_for_record(cls, kind: str, record: Any) -> str:
        if kind == "episodic":
            epistemic_class = classify_episodic_class(
                getattr(record, "source_lane", None),
                explicit_class=getattr(record, "epistemic_class", None),
                source_type=getattr(record, "source_type", None),
            )
            return _EPISODIC_CLASS_TO_BUCKET.get(epistemic_class, "uncertain")
        # preference domain: inferred writes are hypothesis-tier beliefs the
        # user has not confirmed; explicit writes are user-stated.
        if kind == "preference":
            provenance = preference_write_provenance(
                source_type=getattr(record, "source_type", None),
                evidence_refs=getattr(record, "evidence_refs", None),
            )
            if provenance == "inferred":
                return "uncertain"
            return "told"
        # goal domain (M-08 R2 P2-2): a persisted system capture source
        # (plan-approval "event", behavior, ...) is an observed write, never a
        # user statement — it must not land in told/已确认.
        goal_source = str(getattr(record, "source_type", "") or "").strip().lower()
        if goal_source and goal_source not in _GOAL_USER_STATED_SOURCE_TYPES:
            return "observed"
        # NULL / user-stated source: the create action itself is the statement.
        return "told"

    @staticmethod
    def _content_of(kind: str, record: Any) -> str:
        if kind == "episodic":
            return str(getattr(record, "summary", "") or "")
        if kind == "preference":
            value = getattr(record, "pref_value", None)
            if isinstance(value, dict) and "value" in value:
                value = value.get("value")
            return "" if value is None else str(value)
        return str(getattr(record, "title", "") or "")

    @classmethod
    def _source_projection(cls, kind: str, record: Any) -> dict[str, Any]:
        """User-language whence projection with the honest-unknown contract."""
        lane = str(getattr(record, "source_lane", "") or "").strip().lower()
        source_type = str(getattr(record, "source_type", "") or "").strip().lower()
        epistemic_class = (
            classify_episodic_class(
                lane, explicit_class=getattr(record, "epistemic_class", None), source_type=source_type
            )
            if kind == "episodic"
            else EpistemicClass.CONFIRMED_PREFERENCE.value
        )

        if kind == "episodic":
            # Lane (the writer) owns the primary framing: an inferred-lane
            # record is "系统推断" regardless of which material (chat /
            # behavior / ...) it was inferred from; a direct-capture record
            # names the module that observed it.
            if epistemic_class == EpistemicClass.EXPERIENCE.value:
                label, known = _SOURCE_LABEL_EXPERIENCED, True
            elif lane == "user_confirmed":
                label, known = _SOURCE_LABEL_USER_STATED, True
            elif lane == "direct_capture":
                if source_type == "user_registered":
                    label, known = _SOURCE_LABEL_USER_STATED, True
                elif source_type in _EPISODIC_SOURCE_TYPE_LABELS:
                    label, known = _EPISODIC_SOURCE_TYPE_LABELS[source_type], True
                else:
                    label, known = _SOURCE_LABEL_OBSERVED, True
            elif lane:
                label, known = _SOURCE_LABEL_INFERRED, True
            else:
                label, known = _SOURCE_LABEL_UNKNOWN, False
        elif kind == "preference":
            provenance = preference_write_provenance(
                source_type=source_type, evidence_refs=getattr(record, "evidence_refs", None)
            )
            if provenance == "inferred":
                label, known = _SOURCE_LABEL_INFERRED, True
            elif source_type in {"user_state", "chat_preference", "user_registered"}:
                label, known = _SOURCE_LABEL_USER_STATED, True
            elif source_type:
                label, known = _EPISODIC_SOURCE_TYPE_LABELS.get(source_type, "系统写入"), True
            else:
                label, known = _SOURCE_LABEL_UNKNOWN, False
        else:  # goal
            if source_type in _GOAL_USER_STATED_SOURCE_TYPES:
                label, known = _SOURCE_LABEL_USER_STATED, True
            elif source_type in _EPISODIC_SOURCE_TYPE_LABELS:
                label, known = _EPISODIC_SOURCE_TYPE_LABELS[source_type], True
            elif source_type:
                # M-08 R2 P2-2：系统捕获来源（如计划审批的 "event"）如实标
                # 「系统写入」——绝不伪装成用户陈述。
                label, known = _SOURCE_LABEL_SYSTEM, True
            else:
                # Goals created through the public create path carry no
                # source_type value — the create action itself is the
                # user statement.
                label, known = _SOURCE_LABEL_USER_STATED, True
        return {"source_label": label, "source_known": known, "provenance_class": epistemic_class}

    def _item_payload(self, kind: str, record: Any) -> dict[str, Any]:
        bucket = self._bucket_for_record(kind, record)
        explicit = bucket == "told"
        tier, tier_label = self._confidence_tier(record, explicit=explicit)
        status = derive_status(record, now=_utcnow())
        source = self._source_projection(kind, record)
        payload: dict[str, Any] = {
            "kind": kind,
            "id": str(record.id),
            "ref": memory_ref(kind, record.id),
            "bucket": bucket,
            "bucket_label": BUCKET_LABELS[bucket],
            "content": self._content_of(kind, record),
            "status": status,
            "scope": derive_scope(record),
            "updated_at": getattr(record, "updated_at", None),
            "created_at": getattr(record, "created_at", None),
            "correction_count": getattr(record, "correction_count", 0),
            "evidence_missing": bool(getattr(record, "evidence_missing", False)),
            "confidence_tier": tier,
            "confidence_tier_label": tier_label,
            "source_label": source["source_label"],
            "source_known": source["source_known"],
            "epistemic_class": source["provenance_class"],
            "actions": self._available_actions(kind, status),
        }
        if kind == "episodic":
            payload["occurred_at"] = getattr(record, "occurred_at", None)
        if kind == "preference":
            payload["pref_key"] = getattr(record, "pref_key", None)
            payload["version"] = getattr(record, "version", None)
        if kind == "goal":
            payload["title"] = getattr(record, "title", None)
        return payload

    @staticmethod
    def _available_actions(kind: str, status: str) -> list[str]:
        """Actions the current state honestly supports (U-03 action bar)."""
        if status == MemoryRecordStatus.ARCHIVED.value:
            # Paused records support a REAL revoke (P1-1: delete intent wins
            # over pause — the revoke leg un-archives first, resume can never
            # resurrect a deleted record).
            return ["view_source", "resume", "revoke"]
        if status != MemoryRecordStatus.ACTIVE.value:
            return ["view_source"]
        actions = ["update", "revoke", "view_source", "pause"]
        if kind == "goal":
            actions.append("set_scope")
        return actions

    # ------------------------------------------------------------------
    # Work 1: list / detail
    # ------------------------------------------------------------------

    async def list_items(
        self,
        user_id: UUID,
        *,
        bucket: str | None = None,
        kind: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        """List the user's memory items grouped by the U-03 four buckets.

        Scan bound: each kind contributes at most ``_LIST_SCAN_CAP`` most
        recently updated rows (bucket classification is a Python-side
        provenance derivation and cannot be grouped in SQL). The response
        reports ``scan_capped`` honestly when the cap is hit instead of
        silently truncating.
        """
        if bucket is not None and bucket not in PROVENANCE_BUCKETS:
            raise ValueError(f"Unknown bucket: {bucket}")
        if kind is not None and kind not in _SUPPORTED_KINDS:
            raise ValueError(f"Unsupported memory kind: {kind}")
        safe_limit = max(1, min(int(limit or 50), 200))
        safe_offset = max(0, int(offset or 0))

        items: list[dict[str, Any]] = []
        bucket_counts = dict.fromkeys(PROVENANCE_BUCKETS, 0)
        scan_capped = False

        for kind_name, model in _SUPPORTED_KINDS.items():
            if kind is not None and kind_name != kind:
                continue
            stmt = (
                select(model)
                .where(
                    model.user_id == user_id,
                    model.deleted_at.is_(None),
                )
                .order_by(model.updated_at.desc())
                .limit(_LIST_SCAN_CAP)
            )
            result = await self.db.execute(stmt)
            rows = list(result.scalars().all())
            if len(rows) >= _LIST_SCAN_CAP:
                scan_capped = True
            for record in rows:
                payload = self._item_payload(kind_name, record)
                if payload["status"] != MemoryRecordStatus.ACTIVE.value and not include_inactive:
                    continue
                bucket_counts[payload["bucket"]] = bucket_counts.get(payload["bucket"], 0) + 1
                if bucket is not None and payload["bucket"] != bucket:
                    continue
                items.append(payload)

        items.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        total_in_scope = len(items)
        window = items[safe_offset : safe_offset + safe_limit]
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "items": window,
            "bucket_counts": bucket_counts,
            "total": total_in_scope,
            "offset": safe_offset,
            "limit": safe_limit,
            "has_more": safe_offset + len(window) < total_in_scope,
            "scan_capped": scan_capped,
        }

    async def get_item(self, user_id: UUID, kind: str, memory_id: UUID) -> dict[str, Any]:
        record = await self._get_record(user_id, kind, memory_id)
        return self._item_payload(kind, record)

    # ------------------------------------------------------------------
    # Work 2: source (user-language provenance metadata)
    # ------------------------------------------------------------------

    async def get_source(self, user_id: UUID, kind: str, memory_id: UUID) -> dict[str, Any]:
        record = await self._get_record(user_id, kind, memory_id)
        source = self._source_projection(kind, record)
        refs = getattr(record, "evidence_refs", None) or []
        if isinstance(refs, dict):
            refs = refs.get("refs") or []
        evidence_refs = [ref for ref in refs if isinstance(ref, dict)]

        correction_rows = await self.db.execute(
            select(MemoryCorrection)
            .where(
                MemoryCorrection.user_id == user_id,
                MemoryCorrection.memory_id == memory_id,
                MemoryCorrection.memory_type == kind,
                MemoryCorrection.action.in_(list(_USER_GOVERNANCE_ACTIONS)),
            )
            .order_by(MemoryCorrection.created_at.desc())
            .limit(20)
        )
        history = [
            {
                "action": row.action,
                "at": row.created_at,
                "has_reason": bool((row.reason or "").strip()),
            }
            for row in correction_rows.scalars().all()
        ]

        item = self._item_payload(kind, record)
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "kind": kind,
            "id": str(record.id),
            "ref": memory_ref(kind, record.id),
            # 何时
            "written_at": getattr(record, "created_at", None),
            "occurred_at": getattr(record, "occurred_at", None),
            "updated_at": getattr(record, "updated_at", None),
            "last_used_at": getattr(record, "last_consumed_at", None),
            # 何源（honest unknown contract）
            "source_known": source["source_known"],
            "source_label": source["source_label"],
            "source_lane_hint": self._lane_hint(kind, record),
            # 置信层级（tier only — no raw model parameters）
            "confidence_tier": item["confidence_tier"],
            "confidence_tier_label": item["confidence_tier_label"],
            # 证据概况（count + health flag，不落内容明文）
            "evidence_count": len(evidence_refs),
            "evidence_missing": bool(getattr(record, "evidence_missing", False)),
            "evidence_checked_at": getattr(record, "evidence_checked_at", None),
            "correction_count": getattr(record, "correction_count", 0),
            "governance_history": history,
        }

    @staticmethod
    def _lane_hint(kind: str, record: Any) -> str | None:
        """Coarse user-safe lane hint (never the raw internal lane string)."""
        lane = str(getattr(record, "source_lane", "") or "").strip().lower()
        if not lane:
            return None
        if lane in {"direct_capture", "user_confirmed"}:
            return "user_stated"
        if lane == "inferred_extraction":
            return "inferred"
        return "system"

    # ------------------------------------------------------------------
    # Work 1 (scope): read + pause/resume/goal-linkage
    # ------------------------------------------------------------------

    async def get_scope(self, user_id: UUID, kind: str, memory_id: UUID) -> dict[str, Any]:
        record = await self._get_record(user_id, kind, memory_id)
        scope = derive_scope(record)
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "kind": kind,
            "id": str(record.id),
            "scope": scope,
            "paused": getattr(record, "archived_at", None) is not None,
            "paused_at": getattr(record, "archived_at", None),
            "editable": derive_status(record, now=_utcnow()) == MemoryRecordStatus.ACTIVE.value,
            "supported_updates": self._scope_support(kind),
        }

    @staticmethod
    def _scope_support(kind: str) -> list[str]:
        supports = ["pause", "resume"]
        if kind == "goal":
            supports.extend(["link_plan", "link_task"])
        return supports

    async def _assert_owned_goal_ref(self, user_id: UUID, ref_kind: str, ref_id: UUID) -> None:
        """Ownership gate for goal linkage targets (M-08 R2 P2-3).

        link_plan/link_task write FK columns (plans.id / tasks.id). Without
        this gate a cross-user id is accepted verbatim (unvalidated external
        reference) and a non-existent id reaches PostgreSQL as an FK
        IntegrityError → 500 (sqlite tests don't enforce FKs, so the suite
        can't catch it). Missing AND cross-user are indistinguishable — 404,
        the same law as every other face of this service.
        """
        from app.models.plan import Plan
        from app.models.task import Task

        model = Plan if ref_kind == "plan" else Task
        result = await self.db.execute(
            select(model).where(
                model.id == ref_id,
                model.user_id == user_id,  # cross-user target == not found
                model.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise MemoryProvenanceNotFoundError(f"{ref_kind} {ref_id} not found")

    async def update_scope(
        self,
        user_id: UUID,
        kind: str,
        memory_id: UUID,
        *,
        action: str,
        plan_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Scope mutations on existing columns only (no new storage):

        - ``pause`` / ``resume``: archived_at toggle — pause removes the record
          from recall (list_recent_episodic / pack pulls exclude archived)
          while keeping it recoverable; resume restores it.
        - ``link_plan`` / ``link_task`` (goal only): the honest "仅此 Goal"
          narrowing — a goal's scope binds to its plan/task linkage columns.
          Targets are ownership-validated first (P2-3): cross-user or missing
          ids → 404; a PG FK race at commit is caught and reported as 404 too
          (never a 500 from an unvalidated external reference).
        """
        if action not in {"pause", "resume", "link_plan", "link_task"}:
            raise ValueError(f"Unsupported scope action: {action}")
        record = await self._get_record(user_id, kind, memory_id, for_update=True)
        status = derive_status(record, now=_utcnow())
        if action in {"pause", "resume"}:
            # pause/resume must stay available on archived records (that is
            # exactly what resume undoes); only genuinely terminal states
            # (revoked/retracted/superseded/...) are locked.
            if status not in {MemoryRecordStatus.ACTIVE.value, MemoryRecordStatus.ARCHIVED.value}:
                raise MemoryProvenanceConflictError(f"memory is {status}; scope is not editable")
        elif status != MemoryRecordStatus.ACTIVE.value:
            raise MemoryProvenanceConflictError(f"memory is {status}; scope is not editable")

        now = _utcnow()
        if action in {"pause", "resume"}:
            already = getattr(record, "archived_at", None) is not None
            effective = (action == "pause") != already
            if not effective:
                return self._scope_result(kind, record, changed=False, epoch=None)
            record.archived_at = now if action == "pause" else None
            record.updated_at = now
            audit_action = "scope_pause" if action == "pause" else "scope_resume"
        else:
            if kind != "goal":
                raise ValueError(f"scope action {action} is only supported for goals")
            if action == "link_plan":
                if plan_id is None:
                    raise ValueError("plan_id is required for link_plan")
                await self._assert_owned_goal_ref(user_id, "plan", plan_id)
                record.linked_plan_id = plan_id
            else:
                if task_id is None:
                    raise ValueError("task_id is required for link_task")
                await self._assert_owned_goal_ref(user_id, "task", task_id)
                record.linked_task_id = task_id
            record.updated_at = now
            audit_action = "scope_update"

        record.correction_count = (record.correction_count or 0) + 1
        self.db.add(
            MemoryCorrection(
                user_id=user_id,
                memory_type=kind,
                memory_id=record.id,
                action=audit_action,
                reason=(reason or audit_action)[:500],
            )
        )
        pipeline = MemoryInvalidationPipeline(self.db, self.redis)
        invalidation = await pipeline.apply_in_txn(
            user_id=user_id,
            action=MemoryMutationAction.USER_UPDATE,
            kind=kind,
            memory_ids=[record.id],
            reason_code=audit_action,
        )
        try:
            await self.db.commit()
        except IntegrityError as exc:
            # P2-3（PG-only race）：目标 plan/task 在归属校验后、commit 前被并发
            # 删除 → FK 违反。整个 scope 变更（含 epoch/事件）回滚，按同款
            # 404 法则报告——绝不向客户端泄漏 500。
            await self.db.rollback()
            raise MemoryProvenanceNotFoundError(f"scope target for {kind} memory {record.id} not found") from exc
        await pipeline.invalidate_derived_caches(user_id=user_id, kinds={kind})
        await self.db.refresh(record)
        return self._scope_result(kind, record, changed=True, epoch=invalidation.epoch)

    def _scope_result(self, kind: str, record: Any, *, changed: bool, epoch: int | None) -> dict[str, Any]:
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "kind": kind,
            "id": str(record.id),
            "scope": derive_scope(record),
            "paused": getattr(record, "archived_at", None) is not None,
            "paused_at": getattr(record, "archived_at", None),
            "changed": changed,
            "memory_epoch": epoch,
        }

    # ------------------------------------------------------------------
    # Work 1 (update): user edits via the existing mutation authorities
    # ------------------------------------------------------------------

    async def _nonterminal_edit_siblings(self, user_id: UUID, old: Any, *, exclude_id: UUID) -> list[Any]:
        """Prior user-edit replacements of ``old`` that are not yet terminal.

        The user-edit supersede flow anchors EVERY replacement with both
        ``source_type="user_created" + source_id=<old id>`` and the evidence
        ref ``user_state:user_edit:<old id>``. Rows matching the anchor that
        are still non-terminal (not superseded/revoked/retracted/deleted —
        a paused row counts: resume would otherwise resurrect the fork) are:

        - crash-window orphans — the create leg committed, the supersede leg
          did not (R2 PROBE7), or
        - the rival that won a concurrent double-edit race.

        Both must converge onto the newest replacement (P2-4: after any
        successful edit exactly ONE anchored record may stay active).
        """
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.source_type == "user_created",
                EpisodicMemory.source_id == str(old.id),
                EpisodicMemory.id != exclude_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.superseded_by_id.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
            )
            .with_for_update()
        )
        anchor = f"user_edit:{old.id}"
        siblings = []
        for row in result.scalars().all():
            refs = row.evidence_refs or []
            if any(
                isinstance(ref, dict) and ref.get("id") == anchor and ref.get("type") == "user_state" for ref in refs
            ):
                siblings.append(row)
        return siblings

    async def update_item(
        self,
        user_id: UUID,
        kind: str,
        memory_id: UUID,
        *,
        content: str | None = None,
        pref_value: dict[str, Any] | None = None,
        title: str | None = None,
        status: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """User-sovereignty edit. Per M-01 law (correction produces supersede,
        never destructive overwrite):

        - preference → ``MemoryService.update_preference`` (version-chain
          advance + explicit source; SUPERSEDE invalidation wired since M-07);
        - goal → ``MemoryService.update_goal`` (field whitelist; USER_UPDATE
          invalidation wired by M-08);
        - episodic → supersede flow: a corrected user-confirmed record is
          written through the M-02 storage gate, then the old record is
          superseded (``superseded_by_id``) with the SUPERSEDE invalidation.
        """
        record = await self._get_record(user_id, kind, memory_id)
        current_status = derive_status(record, now=_utcnow())
        if current_status != MemoryRecordStatus.ACTIVE.value:
            raise MemoryProvenanceConflictError(f"memory is {current_status}; it can no longer be edited")

        if kind == "preference":
            from app.services.memory_service import MemoryService

            if pref_value is None and content is not None:
                pref_value = {"value": content}
            if pref_value is None:
                raise ValueError("pref_value (or content) is required for preference update")
            updated = await MemoryService(self.db, self.redis).update_preference(
                user_id=user_id,
                preference_id=memory_id,
                pref_value=pref_value,
            )
            if updated is None:
                raise MemoryProvenanceConflictError("preference update was declined")
            refreshed = await self._get_record(user_id, "preference", updated.id)
            return self._update_result("preference", refreshed, superseded_id=memory_id, epoch=None)

        if kind == "goal":
            from app.services.memory_service import MemoryService

            updates: dict[str, Any] = {}
            if title is not None:
                updates["title"] = title
            if status is not None:
                updates["status"] = status
            if content is not None and title is None:
                updates["title"] = content
            if not updates:
                raise ValueError("goal update requires title/status")
            updated = await MemoryService(self.db, self.redis).update_goal(
                user_id,
                memory_id,
                **updates,
            )
            if updated is None:
                raise MemoryProvenanceNotFoundError(f"goal memory {memory_id} not found")
            refreshed = await self._get_record(user_id, "goal", updated.id)
            return self._update_result("goal", refreshed, superseded_id=None, epoch=None)

        # episodic supersede flow
        new_summary = content if content is not None else title
        if new_summary is None or not str(new_summary).strip():
            raise ValueError("episodic update requires the corrected content")
        from app.services.memory_service import MemoryService

        memory_service = MemoryService(self.db, self.redis)
        old = await self._get_record(user_id, "episodic", memory_id, for_update=True)
        replacement = await memory_service.create_episodic_memory(
            user_id=user_id,
            summary=str(new_summary).strip(),
            source_type="user_created",
            source_id=str(old.id),
            occurred_at=getattr(old, "occurred_at", None) or _utcnow(),
            importance_score=getattr(old, "importance_score", None),
            tags=[str(tag) for tag in (getattr(old, "tags", None) or []) if str(tag)] or None,
            evidence_refs=[
                # user_state: the closed evidence vocabulary's type for
                # user-driven writes (same convention as update_preference);
                # id anchors the superseded record.
                {"type": "user_state", "id": f"user_edit:{old.id}"},
            ],
            confidence=None,
            decay_policy=getattr(old, "decay_policy", None),
            semantic_key=getattr(old, "semantic_key", None),
            subject_type=getattr(old, "subject_type", "self"),
            due_at=getattr(old, "due_at", None),
            source_lane="user_confirmed",
            epistemic_class=EpistemicClass.FACT.value,
            emit_system_update=False,
        )
        if replacement is None:
            # The M-02 storage gate declined the corrected content — honest
            # failure, never a silent no-op.
            raise MemoryProvenanceConflictError("corrected content was declined by the memory storage gate")

        old = await self._get_record(user_id, "episodic", memory_id, for_update=True)
        old_status = derive_status(old, now=_utcnow())
        # P2-4 fork convergence: every prior anchored replacement of this
        # record that is still non-terminal (crash-window orphans from the
        # two-commit create/supersede window, or the rival that won a
        # concurrent double-edit) is superseded onto the fresh replacement in
        # the SAME transaction — a retry converges instead of forking, and two
        # active user_confirmed records for one edit are impossible.
        siblings = await self._nonterminal_edit_siblings(user_id, old, exclude_id=replacement.id)
        now_ts = _utcnow()
        superseded_rows: list[Any] = []
        if old_status == MemoryRecordStatus.ACTIVE.value:
            old.superseded_by_id = replacement.id
            old.updated_at = now_ts
            old.correction_count = (old.correction_count or 0) + 1
            self.db.add(
                MemoryCorrection(
                    user_id=user_id,
                    memory_type="episodic",
                    memory_id=old.id,
                    action="user_edit_supersede",
                    reason=(reason or "user_edit")[:500],
                )
            )
            superseded_rows.append(old)
        for row in siblings:
            row.superseded_by_id = replacement.id
            row.updated_at = now_ts
            row.correction_count = (row.correction_count or 0) + 1
            self.db.add(
                MemoryCorrection(
                    user_id=user_id,
                    memory_type="episodic",
                    memory_id=row.id,
                    action="user_edit_supersede",
                    reason=f"fork_converge:{(reason or 'user_edit')[:500]}",
                )
            )
            superseded_rows.append(row)

        if superseded_rows:
            pipeline = MemoryInvalidationPipeline(self.db, self.redis)
            invalidation = await pipeline.apply_in_txn(
                user_id=user_id,
                action=MemoryMutationAction.SUPERSEDE,
                kind="episodic",
                memory_ids=[row.id for row in superseded_rows],
                reason_code="user_edit",
            )
            await self.db.commit()
            await pipeline.invalidate_derived_caches(user_id=user_id, kinds={"episodic"})
            epoch = invalidation.epoch
        else:
            # Concurrent terminal mutation (e.g. delete on another device) and
            # no orphaned siblings: the replacement record stands on its own;
            # nothing to supersede.
            epoch = None
        await self.db.refresh(old)
        refreshed = await self._get_record(user_id, "episodic", replacement.id)
        return self._update_result("episodic", refreshed, superseded_id=old.id, epoch=epoch)

    def _update_result(
        self,
        kind: str,
        record: Any,
        *,
        superseded_id: UUID | None,
        epoch: int | None,
    ) -> dict[str, Any]:
        return {
            **self._item_payload(kind, record),
            "superseded_id": str(superseded_id) if superseded_id else None,
            "memory_epoch": epoch,
        }

    # ------------------------------------------------------------------
    # Work 1 (revoke): uniform delete face over existing authorities
    # ------------------------------------------------------------------

    async def revoke_item(
        self,
        user_id: UUID,
        kind: str,
        memory_id: UUID,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Revoke = the user-facing delete. Delegates to the storage-owned
        mutation paths (revoke_episodic_memory / retract_memory) which already
        guarantee the M-07 chain: epoch bump + ``memory.invalidated`` event +
        derived-cache DEL, atomically with the soft-delete itself.

        M-08 R2 P1-1: the delegated primitives' M-07 idempotency guards treat
        EVERY non-ACTIVE status as "already terminal" — revoking a PAUSED
        (archived) record would silently no-op while this API reported
        ``revoked=true``, and a later resume would resurrect the "deleted"
        record. Delete intent wins over pause: an ARCHIVED row is first
        un-archived (same transaction, row-locked) so the primitive sees
        ACTIVE and executes the full revoke chain.

        Three-face invisibility after revoke: (a) retrieval excludes the row
        (revoked/retracted filters in list_recent_episodic / pack pulls);
        (b) projections rebuild under the bumped epoch (consumer-side epoch
        gates reject stale entries; the Redis DEL accelerates); (c) this API
        hides non-active records unless ``include_inactive`` is explicit.
        """
        from app.services.memory_service import MemoryService

        record = await self._get_record(user_id, kind, memory_id, for_update=True)
        if derive_status(record, now=_utcnow()) == MemoryRecordStatus.ARCHIVED.value:
            record.archived_at = None
            record.updated_at = _utcnow()
            # Same-transaction flush: the delegated primitive's SELECT ... FOR
            # UPDATE + derive_status recheck then observes ACTIVE and the
            # revoke runs for real (one commit, no resurrectable window).
            await self.db.flush()

        service = MemoryService(self.db, self.redis)
        if kind == "episodic":
            record = await service.revoke_episodic_memory(
                user_id=user_id,
                memory_id=memory_id,
                reason=reason or "user_revoked",
                reason_code="user_revoke",
            )
        else:
            success = await service.retract_memory(
                kind=kind,
                memory_id=memory_id,
                user_id=user_id,
                reason=reason or "user_revoked",
                reason_code="user_revoke",
            )
            if not success:
                raise MemoryProvenanceNotFoundError(f"{kind} memory {memory_id} not found")
            record = await self._get_record(user_id, kind, memory_id)
        if record is None:
            raise MemoryProvenanceNotFoundError(f"{kind} memory {memory_id} not found")
        status_after = derive_status(record, now=_utcnow())
        # API 只报真实状态（P1-1）：只有真正处于撤销/撤回终态才说 revoked=true；
        # 委托原语的理论 no-op 逃逸路径在这里被诚实降级，不再谎报成功。
        revoked = status_after in {
            MemoryRecordStatus.REVOKED.value,
            MemoryRecordStatus.RETRACTED.value,
        }
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "kind": kind,
            "id": str(record.id),
            "status": status_after,
            "revoked": revoked,
        }

    # ------------------------------------------------------------------
    # Work 3: Why-this lookup by memory_use_receipt
    # ------------------------------------------------------------------

    async def lookup_why_this(self, user_id: UUID, receipt: Mapping[str, Any]) -> dict[str, Any]:
        """Assemble "why was this memory used" for a memory-use receipt.

        The receipt is the M-05/C-01 structure that already rides in
        ``ContextPack.metadata["memory_selfcheck"]`` and the decision-context
        item manifest: ``memory_ref`` (memory://<kind>/<id>), optional
        ``pack_id`` linkage, ``why_included`` closed-vocab reasons and the
        selfcheck ``internal_only`` entries. This endpoint VALIDATES and
        TRANSLATES it against the user's own records — nothing is invented:

        - refs / pack ids belonging to another user resolve to 404 (no
          existence leak — same law as every other face of this service);
        - reason codes outside the frozen vocabularies come back as
          ``known=False`` (honest unknown, never a guessed label);
        - a receipt version that is not the current ``SELF_CHECK_VERSION`` is
          flagged ``receipt_stale`` instead of being silently re-interpreted.
        """
        raw_ref = receipt.get("memory_ref") or receipt.get("ref")
        if not raw_ref:
            raise ValueError("receipt must carry memory_ref (memory://<kind>/<id>)")
        kind, memory_id = parse_memory_ref(str(raw_ref))
        record = await self._get_record(user_id, kind, memory_id)

        run_payload: dict[str, Any] | None = None
        raw_pack_id = receipt.get("pack_id") or receipt.get("context_pack_id") or receipt.get("run_id")
        if raw_pack_id:
            try:
                pack_uuid = UUID(str(raw_pack_id))
            except ValueError as exc:
                raise ValueError("receipt pack_id is not a valid id") from exc
            run_result = await self.db.execute(
                select(ContextPackRun).where(
                    ContextPackRun.id == pack_uuid,
                    ContextPackRun.user_id == user_id,  # cross-user pack → not found
                    ContextPackRun.deleted_at.is_(None),
                )
            )
            run = run_result.scalar_one_or_none()
            if run is None:
                raise MemoryProvenanceNotFoundError(f"context pack {pack_uuid} not found")
            run_payload = {
                "pack_id": str(run.id),
                "intent": run.intent,
                "created_at": run.created_at,
                "trace_id": run.trace_id,
            }

        receipt_version = receipt.get("version")
        version_known = receipt_version is None or str(receipt_version) == SELF_CHECK_VERSION

        why_included = self._translate_reasons(receipt.get("why_included") or (), WHY_INCLUDED_LABELS)
        internal_entries = []
        for entry in receipt.get("internal_only") or []:
            if not isinstance(entry, Mapping):
                continue
            translated = self._translate_reasons([entry.get("reason")], SELFCHECK_REASON_LABELS)
            internal_entries.append(
                {
                    "id": entry.get("id"),
                    "section": entry.get("section"),
                    "reason": entry.get("reason"),
                    "reason_known": bool(translated) and translated[0]["known"],
                    "reason_label": translated[0]["label"] if translated else None,
                }
            )

        reference_history = await self._recent_reference_traces(user_id, kind, memory_id)
        item = self._item_payload(kind, record)
        source = await self.get_source(user_id, kind, memory_id)
        still_active = item["status"] == MemoryRecordStatus.ACTIVE.value
        # P3-7：对 superseded 旧 id 的回执带替代记录指针（行上就有
        # superseded_by_id）——用户从「为什么当时用这条」直达现行版本。
        superseded_by = getattr(record, "superseded_by_id", None)
        return {
            "schema_version": PROVENANCE_SERVICE_VERSION,
            "memory": {
                "kind": kind,
                "id": str(record.id),
                "ref": memory_ref(kind, record.id),
                "content": item["content"],
                "status_now": item["status"],
                "bucket": item["bucket"],
                "still_in_use": still_active,
                "paused": getattr(record, "archived_at", None) is not None,
                "replaced_by_ref": memory_ref(kind, superseded_by) if superseded_by else None,
            },
            "used_at": getattr(record, "last_consumed_at", None) or (run_payload or {}).get("created_at"),
            "run": run_payload,
            "why_included": why_included,
            "usage_decision": {
                "internal_only": internal_entries,
                "receipt_version": receipt_version,
                "receipt_version_known": version_known,
            },
            "recent_uses": reference_history,
            "source": source,
            # U-03 correction loop: from any Why-this receipt the user can
            # directly say "这不对" — point at the real mutation endpoints.
            "correction": {
                "update": f"/api/v1/memory/provenance/items/{kind}/{record.id}/update",
                "revoke": f"/api/v1/memory/provenance/items/{kind}/{record.id}/revoke",
                "scope": f"/api/v1/memory/provenance/items/{kind}/{record.id}/scope",
            },
        }

    @staticmethod
    def _translate_reasons(reasons: Iterable[Any], labels: Mapping[str, str]) -> list[dict[str, Any]]:
        translated: list[dict[str, Any]] = []
        for reason in reasons:
            code = str(reason or "").strip()
            if not code:
                continue
            known = code in labels
            translated.append(
                {
                    "reason": code,
                    "known": known,
                    "label": labels.get(code),  # None + known=False = honest unknown
                }
            )
        return translated

    async def _recent_reference_traces(
        self, user_id: UUID, kind: str, memory_id: UUID, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        rows = await self.db.execute(
            select(MemoryCorrection)
            .where(
                MemoryCorrection.user_id == user_id,
                MemoryCorrection.memory_id == memory_id,
                MemoryCorrection.memory_type == kind,
                MemoryCorrection.action.like("memory_reference_%"),
            )
            .order_by(MemoryCorrection.created_at.desc())
            .limit(limit)
        )
        return [{"action": row.action, "at": row.created_at} for row in rows.scalars().all()]
