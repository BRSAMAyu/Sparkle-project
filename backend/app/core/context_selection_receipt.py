"""V4-I06 · ``context_selection_receipt.v1`` —— 上下文选择回执契约（B05 合同实现）。

权威规格：``v4/evidence/V4-B05/contract_receipt_min.md`` §2（合同 DESIGN_PROPOSAL
双审 APPROVE；本模块是其**实现**，实现卡 V4-I06）。

语义（合同原文落实）：一次上下文选择（chat 装配 / 提案依据 / 接续视图 / 干预定向）
完成后，记录「读了哪些权威的哪些版本、候选了什么、用了什么、拒了什么、为什么、
在哪生效」。回执 = 服务器对"确实发生了什么"的权威记录；呈现 = 回执的投影。

三条继承不变量（contract_receipt_min.md 头部）：
- I1 授权无关：回执不授予任何权限、不构成任何业务事实（C3：只读，只证明"读与选"）；
- I2 成功必须可溯源：本回执不是 committed receipt，不得驱动任何成功呈现；
- I3 跨对象拒绝：候选 ref 必须落在封闭 scheme（``ACTION_SOURCE_REF_SCHEMES``）
  且属于同一授权用户——来源验证（service 层 join 真实存储）双重校验，不可悬空。

产生时机（合同 §2）：Context Compiler（+记忆效用门+可用性过滤）完成选择时、在
proposal 发出 / resume view 返回**之前**。同一轮一个 receipt；无选择发生（L0 确定
性应答）不产生。当前接线点 = ``ContextPackBuilder.build``（chat/plan_review/context_
focus 共用的唯一上下文契约装配点；context_builder stage34 面经 metadata 只读消费）。

封闭词表纪律（合同纪律节）：词表扩展 = 契约变更，需 bump 版本过 reviewer；
本模块所有 frozenset 由 tests/contract/test_context_selection_receipt_contract.py
钉死。M-03 预筛 reason → 本合同 reason_code 的映射表同样是冻结面（PREFILTER_
REASON_CODE_MAP），改动须同步合同与测试。

与 V4-I02 的接口（卡要点 3）：效用门（``memory_utility_gate``，分支未合时默认
关闭）开启时，其 ``UtilityGateResult.to_metric_payload()`` 形状 metadata 经
``apply_utility_gate_metadata`` 进回执——门拒候选 reason_code=``utility_gate_
rejected``（note=门 reasons 摘要，debug-only）；门关时回执照常产生，原因码 =
prefilter 面既有语义（本模块映射表）。本分支不含 I02 代码，接口按其 to_metric_
payload 冻结形状消费，鸭子类型、无硬 import——门合入后零改动接线。

开关：``settings.CONTEXT_SELECTION_RECEIPT_MODE``（off/shadow/live，默认 shadow，
B05 §8「shadow 写先行、默认读关闭」）：
- ``off``：不产生、不落库（V3 路径零变化）；
- ``shadow``：产生 + 落库 + 进程内挂 ContextPack（metadata 面可观测），读 API 不暴露；
- ``live``：读面（/experience/context-receipts/latest）可消费。
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES

#: 契约版本（冻结；扩展纪律见 contract_receipt_min.md §8）。
CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION = "context_selection_receipt.v1"

#: receipt_id 前缀（合同 §2：``csr_<ulid>``）。
RECEIPT_ID_PREFIX = "csr_"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展 = bump 契约版本并过 reviewer）
# ---------------------------------------------------------------------------

#: 合同 §2 ``selection_role``：这次选择在哪生效。
SELECTION_ROLES: frozenset[str] = frozenset(
    {
        "chat_context",  # chat 装配
        "proposal_basis",  # 提案依据
        "resume_view",  # 接续视图
        "intervention_targeting",  # 干预定向
    }
)

#: 合同 §2 ``candidates[].status``。
CANDIDATE_STATUSES: frozenset[str] = frozenset({"selected", "rejected", "unavailable"})

#: 合同 §2 ``candidates[].reason_code``（status≠selected 时必选的类型化出口）。
#: 新增值 = bump ``v1.x`` + 测试冻结断言同步（合同 C2）。
REJECTION_REASON_CODES: frozenset[str] = frozenset(
    {
        "out_of_scope_memory",  # scope 不匹配（M-03 scope 维度）
        "stale_epoch",  # 删除/纠正/被取代/权限收紧后的失效家族（epoch 语义）
        "utility_gate_rejected",  # 效用门拒用（I02 门 / M-05 selfcheck 降档）
        "conflicts_confirmed_preference",  # 与已确认偏好冲突（M-04/冲突裁决出口）
        "permission_denied",  # user_memory_settings 权限 / sensitivity 天花板 / 身份
        "budget_exhausted",  # 预算/排名截断（合法但未进面）
        "duplicate",  # 包内近重复（M-05 dedup）
        "expired",  # TTL / 状态机 expired 家族
    }
)

#: ``unavailable``（候选存在但本轮不可读，如权限拒绝/解析失败）专用码集合。
UNAVAILABLE_REASON_CODES: frozenset[str] = frozenset({"permission_denied"})

#: 合同 §4 why-now confidence band（审慎标签，R1-C2 口径对齐：
#: DecisionUncertainty / M-08 _confidence_tier 同一封闭档位，不另造档）。
WHY_NOW_CONFIDENCE_BANDS: frozenset[str] = frozenset({"high", "medium", "low", "unknown"})

#: 合同 §4：why-now statement 长度上限（用户可读一句话）。
WHY_NOW_STATEMENT_MAX_LEN = 200

#: 合同 §2：candidate note 上限（debug-only，不得进用户正文）。
CANDIDATE_NOTE_MAX_LEN = 140

#: selector 实现版本（当前唯一生产者：ContextPackBuilder）。
SELECTOR_VERSION_CONTEXT_PACK = "context_pack.v4-i06.v1"

# ---------------------------------------------------------------------------
# M-03 预筛 reason → 合同 reason_code 冻结映射（词表转换唯一权威）
# ---------------------------------------------------------------------------

#: M-01 status 机非 ACTIVE 值家族 → ``stale_epoch``（删除/纠正/被取代/归档）；
#: ``expired`` 单列 → ``expired``。映射键 = M-03 ``Rejection.reason`` 的**前缀**
#: （``<dimension>:<detail>`` 维度前缀），首个命中生效；表序即判定序。
PREFILTER_REASON_CODE_MAP: tuple[tuple[str, str], ...] = (
    ("user:", "permission_denied"),  # 身份不符 = 权限家族（不泄漏跨用户存在性）
    ("status:expired", "expired"),
    ("status:", "stale_epoch"),  # revoked/superseded/retracted/archived/resolved
    ("ttl:", "expired"),  # not_yet_valid / expired / today_only_expired
    ("scope:", "out_of_scope_memory"),  # mismatch / unknown_level
    ("purpose:", "permission_denied"),  # user_memory_settings 权限层
    ("sensitivity:", "permission_denied"),  # 敏感度天花板 = 权限家族
)

#: 未命中映射表的兜底码（保守归类为"不适用本轮上下文"；词表无 other，
#: 合同未定义未知 reason 投影，实现卡钉死为 out_of_scope_memory 并在此声明）。
PREFILTER_REASON_CODE_FALLBACK = "out_of_scope_memory"

#: M-05 selfcheck 降档 reason → 合同 reason_code。
#: ``selfcheck:duplicate_in_pack`` 是真重复；其余 selfcheck 降档（不该说出口家族，
#: 含 fast-model 钩子 ``selfcheck:fm_*``）是记忆效用门的类型化出口 →
#: ``utility_gate_rejected``。表序即判定序：精确项在前，前缀项在后。
SELFCHECK_REASON_CODE_MAP: tuple[tuple[str, str], ...] = (
    ("selfcheck:duplicate_in_pack", "duplicate"),
    ("selfcheck:", "utility_gate_rejected"),
)

#: C-08 漏斗面（context_funnel）reason → 合同 reason_code（metadata 只读消费面）。
FUNNEL_REASON_CODE_MAP: tuple[tuple[str, str], ...] = (
    ("rank_cutoff", "budget_exhausted"),
    ("budget_truncated", "budget_exhausted"),
    ("empty_content", "out_of_scope_memory"),
    ("selfcheck_internal", "utility_gate_rejected"),
)


def rejection_reason_code(raw_reason: str) -> str:
    """开放 reason（M-03 / M-05 / C-08 面）→ 封闭 reason_code。

    判定序：先精确命中 selfcheck/funnel 表，再按 prefilter 维度前缀表，
    未命中走 fallback（``out_of_scope_memory``，模块 docstring 声明的实现卡
    钉死项）。返回值保证 ∈ ``REJECTION_REASON_CODES``（函数即守卫，不信任输入）。
    """
    text = str(raw_reason or "").strip()
    for table in (SELFCHECK_REASON_CODE_MAP, FUNNEL_REASON_CODE_MAP, PREFILTER_REASON_CODE_MAP):
        for prefix, code in table:
            if text == prefix or text.startswith(prefix):
                return code if code in REJECTION_REASON_CODES else PREFILTER_REASON_CODE_FALLBACK
    return PREFILTER_REASON_CODE_FALLBACK


# ---------------------------------------------------------------------------
# ref 构造 / 解析（scheme ∈ ACTION_SOURCE_REF_SCHEMES，封闭集复用不复制）
# ---------------------------------------------------------------------------


def memory_ref(kind: str, item_id: Any) -> str:
    """memory 真源指针（``memory://episodic/<uuid>`` 等；kind=episodic/preference/
    goal/experience——scheme 封闭集只约束 ``memory``，path 自由但可解析回 DB 行）。"""
    return f"memory://{str(kind or '').strip()}/{str(item_id or '').strip()}"


def parse_ref_scheme(ref: str) -> str | None:
    """``scheme://path`` → scheme；非 ``://`` 形态或空 scheme → None。

    合同 C1/反例 ``fabricated_ref_scheme``：scheme 不在封闭集 = 契约违约，
    构造侧拒绝；读侧（来源验证）对 None/集合外 scheme 一律判 unknown。
    """
    text = str(ref or "").strip()
    scheme, sep, _path = text.partition("://")
    if not sep or not scheme:
        return None
    return scheme


def ref_in_closed_schemes(ref: str) -> bool:
    """C1/I3 机器判定：ref scheme ∈ ACTION_SOURCE_REF_SCHEMES。"""
    scheme = parse_ref_scheme(ref)
    return scheme is not None and scheme in ACTION_SOURCE_REF_SCHEMES


def new_receipt_id() -> str:
    """``csr_<ulid>``——48bit 毫秒时间 + 80bit 随机的 Crockford Base32 ULID
    （合同 §2 形态；无外部依赖的确定性编码，单调性不作承诺——幂等键由调用方
    按「同一轮可重算不重复计数」语义自持）。"""
    from uuid import uuid4

    _ENCODE = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    ts_part = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_part = uuid4().int >> 64  # 64bit 随机（128bit 的高半段）
    value = (ts_part << 80) | (rand_part & ((1 << 80) - 1))
    chars: list[str] = []
    while value:
        chars.append(_ENCODE[value & 0x1F])
        value >>= 5
    padded = "".join(reversed(chars)).rjust(26, "0")
    return f"{RECEIPT_ID_PREFIX}{padded}"


# ---------------------------------------------------------------------------
# 契约模型（pydantic；字段 = contract_receipt_min.md §2 表逐行）
# ---------------------------------------------------------------------------


class ReceiptInputVersions(BaseModel):
    """input_versions——各键 null = 该权威未读取；不得以 0/"" 冒充已读（合同表）."""

    memory_epoch: int | None = Field(default=None, ge=0)
    goal_version: str | None = None
    task_version: str | None = None
    policy_version: str | None = None
    selector_version: str

    @field_validator("selector_version")
    @classmethod
    def _selector_version_not_blank(cls, value: str) -> str:
        """selector_version 必选且非空白——空串即"冒充已读"，构造层拒绝。"""
        text = str(value or "").strip()
        if not text:
            raise ValueError("selector_version must be a non-empty version string")
        return text


class ReceiptCandidate(BaseModel):
    """候选条目：selected 时 reason_code 必须 null；rejected/unavailable 时必选."""

    ref: str
    status: str
    reason_code: str | None = None
    note: str | None = Field(default=None, max_length=CANDIDATE_NOTE_MAX_LEN)


class ReceiptBudget(BaseModel):
    """预算面（对齐澄清预算 ≤1 轮与扫描上限，合同 §2 budget 行）。"""

    candidate_scan_limit: int = Field(ge=0)
    selected_max: int = Field(ge=0)
    clarifications_used: int = Field(default=0, ge=0)


class ReceiptWhyNow(BaseModel):
    """why-now（X-01 缺口补位；词表/纪律 = 合同 §4，不新造第二语义）。

    - statement ≤200 用户可读；
    - basis_refs ≥1 当 statement 非空（无依据的 why-now = 伪依据，契约层拒）；
    - expires_at null = 无时效语义；过期后呈现层显示"当时的原因"；
    - confidence_band ∈ WHY_NOW_CONFIDENCE_BANDS（审慎标签，非精度百分比）。
    """

    statement: str = Field(max_length=WHY_NOW_STATEMENT_MAX_LEN)
    basis_refs: list[str] = Field(default_factory=list)
    expires_at: str | None = None
    confidence_band: str = "unknown"


class ContextSelectionReceipt(BaseModel):
    """``context_selection_receipt.v1`` 全结构（合同 §2 字段表）。"""

    schema_version: str = CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION
    receipt_id: str
    selection_role: str
    decision_id: str | None = None
    input_versions: ReceiptInputVersions
    candidates: list[ReceiptCandidate] = Field(default_factory=list)
    budget: ReceiptBudget
    why_now: ReceiptWhyNow | None = None

    # ------------------------------------------------------------------
    # 契约校验（返回违例列表；空 = 合法。不抛异常——读侧对脏数据降级不炸）
    # ------------------------------------------------------------------
    def validate_contract(self) -> list[str]:
        violations: list[str] = []
        if self.schema_version != CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION:
            violations.append(
                f"schema_version={self.schema_version!r} not {CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION!r}"
            )
        if not self.receipt_id.startswith(RECEIPT_ID_PREFIX):
            violations.append(f"receipt_id={self.receipt_id!r} missing {RECEIPT_ID_PREFIX!r} prefix")
        if self.selection_role not in SELECTION_ROLES:
            violations.append(f"selection_role={self.selection_role!r} not in closed vocabulary")
        if not self.input_versions.selector_version:
            violations.append("input_versions.selector_version is required")
        seen_refs: set[str] = set()
        for index, candidate in enumerate(self.candidates):
            label = f"candidates[{index}]"
            if candidate.status not in CANDIDATE_STATUSES:
                violations.append(f"{label}.status={candidate.status!r} not in closed vocabulary")
            if not ref_in_closed_schemes(candidate.ref):
                # C1 / 反例 fabricated_ref_scheme：scheme 封闭集外即违约。
                violations.append(f"{label}.ref={candidate.ref!r} scheme not in ACTION_SOURCE_REF_SCHEMES")
            if candidate.ref in seen_refs:
                violations.append(f"{label}.ref={candidate.ref!r} duplicated")
            seen_refs.add(candidate.ref)
            if candidate.status == "selected":
                if candidate.reason_code is not None:
                    violations.append(f"{label}: selected must carry reason_code=null")
            else:
                if candidate.reason_code is None:
                    violations.append(f"{label}: status={candidate.status!r} requires reason_code")
                elif candidate.reason_code not in REJECTION_REASON_CODES:
                    violations.append(f"{label}.reason_code={candidate.reason_code!r} not in closed vocabulary")
        if self.why_now is not None:
            why = self.why_now
            if not why.statement.strip():
                violations.append("why_now.statement is empty")
            if why.statement.strip() and not why.basis_refs:
                # 反例 why_now_without_basis：statement 非空 ⇒ basis_refs ≥1。
                violations.append("why_now.statement non-empty requires >=1 basis_refs (伪依据)")
            for ref in why.basis_refs:
                if not ref_in_closed_schemes(ref):
                    violations.append(f"why_now.basis_refs ref={ref!r} scheme not in ACTION_SOURCE_REF_SCHEMES")
                elif ref not in seen_refs:
                    # C1 投影：why-now 依据必须真进本轮依据面（selected 集合）。
                    violations.append(f"why_now.basis_refs ref={ref!r} not among selected candidates")
            if why.confidence_band not in WHY_NOW_CONFIDENCE_BANDS:
                violations.append(f"why_now.confidence_band={why.confidence_band!r} not in closed vocabulary")
        return violations

    @property
    def selected_refs(self) -> list[str]:
        return [candidate.ref for candidate in self.candidates if candidate.status == "selected"]

    def to_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        return payload

    def to_log_line(self) -> str:
        """metadata-only 一行摘要（debug 日志面；不含 note 正文与被拒内容）。"""
        counts: dict[str, int] = {}
        for candidate in self.candidates:
            counts[candidate.status] = counts.get(candidate.status, 0) + 1
        return (
            f"receipt={self.receipt_id} role={self.selection_role} "
            f"candidates={counts} epoch={self.input_versions.memory_epoch} "
            f"selector={self.input_versions.selector_version}" + (" why_now=True" if self.why_now is not None else "")
        )


def context_selection_receipt_from_payload(payload: Any) -> tuple[ContextSelectionReceipt | None, list[str]]:
    """读侧门：payload → (receipt, violations)。

    版本门（fail-closed 对齐 action_plan 投影纪律）：schema_version 非当前版本
    → (None, violations)（调用方记 WARN）。结构损坏（非 dict / 必填缺失）→
    (None, violations)。字段级脏值尽力解析，残缺面进 violations 供遥测；
    **candidates 缺失 = 旧生产者** → 读侧按 unknown 处理（合法空集，不计违例，
    合同 §2 candidates unknown 语义：不得渲染为"无依据可用"或"有依据"任一）。
    """
    if not isinstance(payload, dict):
        return None, ["payload is not an object"]
    version = payload.get("schema_version")
    if version != CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION:
        return None, [f"schema_version={version!r} unsupported (known: {CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION!r})"]
    violations: list[str] = []
    try:
        input_versions_raw = payload.get("input_versions")
        input_versions = ReceiptInputVersions(**input_versions_raw) if isinstance(input_versions_raw, dict) else None
        if input_versions is None:
            return None, ["input_versions missing or not an object"]
        budget_raw = payload.get("budget")
        budget = ReceiptBudget(**budget_raw) if isinstance(budget_raw, dict) else None
        if budget is None:
            return None, ["budget missing or not an object"]
        candidates_raw = payload.get("candidates")
        candidates: list[ReceiptCandidate] = []
        if candidates_raw is None:
            violations.append("candidates missing (legacy producer) -> read as unknown")
        elif isinstance(candidates_raw, list):
            for index, entry in enumerate(candidates_raw):
                if not isinstance(entry, dict):
                    violations.append(f"candidates[{index}] is not an object")
                    continue
                if not str(entry.get("ref") or "").strip() or not str(entry.get("status") or "").strip():
                    violations.append(f"candidates[{index}] missing ref/status")
                    continue
                candidates.append(
                    ReceiptCandidate(
                        ref=str(entry.get("ref")),
                        status=str(entry.get("status")),
                        reason_code=entry.get("reason_code"),
                        note=entry.get("note"),
                    )
                )
        else:
            violations.append("candidates is not an array")
        why_now: ReceiptWhyNow | None = None
        why_raw = payload.get("why_now")
        if why_raw is not None:
            if isinstance(why_raw, dict):
                try:
                    why_now = ReceiptWhyNow(
                        statement=str(why_raw.get("statement") or ""),
                        basis_refs=[str(ref) for ref in (why_raw.get("basis_refs") or [])],
                        expires_at=why_raw.get("expires_at"),
                        confidence_band=str(why_raw.get("confidence_band") or "unknown"),
                    )
                except Exception as exc:  # noqa: BLE001 - 字段级降级，不炸读面
                    violations.append(f"why_now malformed: {exc}")
            else:
                violations.append("why_now is not an object")
        receipt_id = str(payload.get("receipt_id") or "").strip()
        selection_role = str(payload.get("selection_role") or "").strip()
        if not receipt_id:
            return None, ["receipt_id missing"] + violations
        if not selection_role:
            return None, ["selection_role missing"] + violations
        receipt = ContextSelectionReceipt(
            schema_version=str(version),
            receipt_id=receipt_id,
            selection_role=selection_role,
            decision_id=payload.get("decision_id"),
            input_versions=input_versions,
            candidates=candidates,
            budget=budget,
            why_now=why_now,
        )
        violations.extend(receipt.validate_contract())
        return receipt, violations
    except Exception as exc:  # noqa: BLE001 - 读侧永不因脏数据炸
        return None, violations + [f"malformed payload: {exc}"]


# ---------------------------------------------------------------------------
# 构造辅助：装配面观测 → 回执（纯函数；context_pack 接线消费）
# ---------------------------------------------------------------------------


def build_candidate(
    *,
    ref: str,
    status: str,
    reason: str | None = None,
    note: str | None = None,
) -> ReceiptCandidate:
    """单候选构造（reason_code 经封闭映射；selected 时强制 null）。"""
    if status == "selected":
        return ReceiptCandidate(ref=ref, status="selected", reason_code=None, note=_clip_note(note))
    code = rejection_reason_code(reason or "")
    return ReceiptCandidate(ref=ref, status=status, reason_code=code, note=_clip_note(note))


def _clip_note(note: str | None) -> str | None:
    text = str(note or "").strip()
    if not text:
        return None
    return text[:CANDIDATE_NOTE_MAX_LEN]


def apply_utility_gate_metadata(
    *,
    candidates: list[ReceiptCandidate],
    gate_payload: dict[str, Any] | None,
) -> list[ReceiptCandidate]:
    """V4-I02 接口点：效用门开启时把其 metadata（选/拒原因）并入回执。

    ``gate_payload`` 消费 ``UtilityGateResult.to_metric_payload()`` 冻结形状：
    ``{"decisions": [{"item_id", "selected", "score", "reasons"}, ...], ...}``。
    门结果覆盖同 id 候选的先前状态：
    - 门选中 → selected（reason_code 清 null；门选中的候选已过 M-03，合法性继承）；
    - 门拒 → rejected / reason_code=``utility_gate_rejected``（note=门 reasons 摘要）。
    门元数据缺失/形状不符 = 门关语义 → 原候选原样返回（卡要点 3：门关时回执仍
    产生，原因码 = prefilter 面既有语义）。鸭子类型消费——本分支无 I02 代码，
    门合入后零改动。
    """
    if not isinstance(gate_payload, dict):
        return candidates
    decisions = gate_payload.get("decisions")
    if not isinstance(decisions, list):
        return candidates
    by_ref: dict[str, ReceiptCandidate] = {}
    for candidate in candidates:
        item_id = candidate.ref.rsplit("/", 1)[-1]
        by_ref[item_id] = candidate
    merged: list[ReceiptCandidate] = []
    consumed: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        item_id = str(decision.get("item_id") or "").strip()
        if not item_id or item_id not in by_ref:
            continue  # 门只裁决 M-03 allowed 面；未知 id 不构造悬空 ref（I3）
        consumed.add(item_id)
        original = by_ref[item_id]
        if bool(decision.get("selected")):
            merged.append(ReceiptCandidate(ref=original.ref, status="selected", reason_code=None, note=original.note))
        else:
            reasons = [str(r) for r in (decision.get("reasons") or []) if str(r or "").strip()]
            note = "gate:" + ",".join(reasons[:3]) if reasons else None
            merged.append(
                ReceiptCandidate(
                    ref=original.ref,
                    status="rejected",
                    reason_code="utility_gate_rejected",
                    note=_clip_note(note),
                )
            )
    # 门未裁决的候选保持原状（门只作用于 optional history 面）。
    for candidate in candidates:
        if candidate.ref.rsplit("/", 1)[-1] not in consumed:
            merged.append(candidate)
    return merged


def build_why_now(
    *,
    statement: str,
    basis_refs: list[str],
    selected_refs: list[str],
    expires_at: str | None = None,
    confidence_band: str = "unknown",
) -> ReceiptWhyNow | None:
    """why-now 构造（契约层拒伪依据：statement 非空但无 selected 依据 → None+WARN，
    反例 ``why_now_without_basis``）。"""
    text = str(statement or "").strip()
    if not text:
        return None
    allowed = set(selected_refs)
    refs = [ref for ref in basis_refs if ref in allowed]
    if not refs:
        logger.warning(
            "I06 why_now rejected: no basis_refs among selected candidates (statement_len={})",
            len(text),
        )
        return None
    band = confidence_band if confidence_band in WHY_NOW_CONFIDENCE_BANDS else "unknown"
    return ReceiptWhyNow(
        statement=text[:WHY_NOW_STATEMENT_MAX_LEN],
        basis_refs=refs,
        expires_at=expires_at,
        confidence_band=band,
    )


__all__ = [
    "CANDIDATE_NOTE_MAX_LEN",
    "CANDIDATE_STATUSES",
    "CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION",
    "FUNNEL_REASON_CODE_MAP",
    "PREFILTER_REASON_CODE_FALLBACK",
    "PREFILTER_REASON_CODE_MAP",
    "RECEIPT_ID_PREFIX",
    "REJECTION_REASON_CODES",
    "SELFCHECK_REASON_CODE_MAP",
    "SELECTION_ROLES",
    "SELECTOR_VERSION_CONTEXT_PACK",
    "UNAVAILABLE_REASON_CODES",
    "WHY_NOW_CONFIDENCE_BANDS",
    "WHY_NOW_STATEMENT_MAX_LEN",
    "ContextSelectionReceipt",
    "ReceiptBudget",
    "ReceiptCandidate",
    "ReceiptInputVersions",
    "ReceiptWhyNow",
    "apply_utility_gate_metadata",
    "build_candidate",
    "build_why_now",
    "context_selection_receipt_from_payload",
    "memory_ref",
    "new_receipt_id",
    "parse_ref_scheme",
    "ref_in_closed_schemes",
    "rejection_reason_code",
]
