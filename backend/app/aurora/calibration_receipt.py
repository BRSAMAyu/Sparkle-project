"""A-06 · Aurora Calibration Receipt —— "Why this?" 用户可纠偏回执（aurora_calibration_receipt.v1）。

产品目标（卡面）：让用户感知理解与可纠正性，而不是「AI 说自己懂」。

本模块是 AURORA_V3 §6 UI receipts 的**纯契约面**（零 IO、确定性、不 raise）：

1. **短 rationale summary + memory/knowledge refs + uncertainties**（卡面 Work 1）
   —— ``build_calibration_receipt`` 把「这条回复真的引用了哪些记忆/材料、哪些
   还不确定」装配成用户语言回执。rationale 是**回执组成事实的提炼摘要**
   （引用了几条记忆、几份材料、几处不确定），**不是也不可能是推理流**：
   - 本模块的输入只有已解析的记忆条目/材料名/计数，``annotations``、
     ``policy_why``、``joint_why`` 等内部 reason 码在结构上进不了本模块
     （调用方是 response_builder 的回执装配层，从不传决策环内部注释）；
   - 输出逐字段断言不含 ``policy_why`` / ``joint_why`` / 内部 reason 码形态
     （``test_a06_calibration_receipt.py`` 双钉）——hidden chain-of-thought
     守界是**结构性**的（数据流边界），不是提示词约定。
2. **四动作纠偏**（卡面 Work 2）：``not_relevant / wrong / change_scope / delete``
   封闭词表。每个动作**只委托既有权威真源**，零新写路径：
   - ``not_relevant``   → ``MemoryService.record_memory_reference_outcome(denied)``
     （引用层降置信 + 飞轮负样本——「这条与本轮无关，以后少引」）；
   - ``wrong``          → 带更正内容走 ``MemoryProvenanceService.update_item``
     （M-01 supersede 法则）；不带内容走 ``MemoryService.correct_memory
     (lower_confidence)``；
   - ``change_scope``   → ``MemoryProvenanceService.update_scope(pause)``
     （暂停召回、可恢复——「别再用这条建议我」）；
   - ``delete``         → ``MemoryProvenanceService.revoke_item``
     （M-07 撤销链：epoch bump + invalidation + 三面不可见）。
3. **触发有度**（卡面 Work 3）：``evaluate_receipt_surfacing`` 是确定性门——
   - 回复没有真实引用记忆 → 不出回执；
   - 引用全部高置信且用户已确认 → 降级 ``ambient``（回执仍在、四动作仍在——
     纠偏能力不弱化；只是不主动强调，避免每条回复都把历史顶到用户眼前）；
   - 存在不确定引用时升格 ``calibration`` 强调呈现，但受
     ``MAX_CALIBRATION_SURFACES_PER_DAY`` 日预算约束（超限降级 ambient）。
   门只影响**呈现强度**，永不吞掉回执本身与纠偏动作（不弱化既有纠偏面）。

冻结声明：``CALIBRATION_RECEIPT_ACTIONS`` / ``RECEIPT_SURFACE_DECISIONS`` /
``RECEIPT_UNCERTAINTY_LABELS`` / 阈值参数被
``backend/tests/unit/test_a06_calibration_receipt.py`` 精确集 + sha256 双钉；
扩展需 bump ``CALIBRATION_RECEIPT_VERSION`` 并过 reviewer。
"""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from app.core.aurora_decision import AURORA_UNCERTAINTY_KINDS

#: 回执契约版本（扩展任何冻结面需 bump 并过 reviewer）。
CALIBRATION_RECEIPT_VERSION = "aurora_calibration_receipt.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结）
# ---------------------------------------------------------------------------

#: 四动作（卡面 Work 2；AURORA_V3 §6「不相关 / 改一下 / 别再用这条」的完整化）。
CALIBRATION_RECEIPT_ACTIONS: frozenset[str] = frozenset(
    {
        "not_relevant",  # 这条与本轮无关（引用层降噪，不否定内容本身）
        "wrong",  # 内容不对（降置信；带更正文本时走 supersede）
        "change_scope",  # 收窄使用范围（暂停召回，可恢复）
        "delete",  # 删除这条记忆（M-07 撤销链）
    }
)

#: 动作 → 既有权威真源委托面（审计/响应负载用；本模块零写路径，只声明去处）。
RECEIPT_ACTION_AUTHORITIES: Mapping[str, str] = MappingProxyType(
    {
        "not_relevant": "memory.record_memory_reference_outcome(denied)",
        "wrong": "memory.correct_memory(lower_confidence) | provenance.update_item(supersede)",
        "change_scope": "provenance.update_scope(pause)",
        "delete": "provenance.revoke_item",
    }
)

#: 呈现门裁决（封闭三值）。
RECEIPT_SURFACE_DECISIONS: frozenset[str] = frozenset(
    {
        "surfaced",  # calibration 强调呈现（有不确定面值得校准）
        "ambient",  # 降级安静呈现（回执与动作仍在，不主动强调）
        "hidden",  # 无可回执内容（无引用记忆）
    }
)

#: 不确定性类型 → 用户语言（AURORA_V3 §1 uncertainties 的用户面）。
#: 完整性 import 期断言：只翻译既有封闭词表成员，且必须全覆盖——A-01 词表
#: 演进即刻在此处 fail-fast，绝不静默漏翻。
RECEIPT_UNCERTAINTY_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "insufficient_context": "这次可参考的上下文还不够",
        "stale_signal": "依据的状态信息可能已经过时",
        "conflicting_evidence": "有几条信息互相矛盾",
        "unverified_inference": "这条理解我还不确定，没有向你确认过",
        "user_model_conflict": "你最近的反馈和我的判断不一致",
        "policy_gap": "这种情况还没有明确的规则，我按保守方式处理了",
    }
)
assert set(RECEIPT_UNCERTAINTY_LABELS) == set(
    AURORA_UNCERTAINTY_KINDS
), "RECEIPT_UNCERTAINTY_LABELS drifted from AURORA_UNCERTAINTY_KINDS"

# ---------------------------------------------------------------------------
# 阈值/预算（冻结；门参数）
# ---------------------------------------------------------------------------

#: 不确定引用判定线：置信低于此值，或未被用户确认，都算「不确定引用」。
#: 0.6 与 M-08 ``_confidence_tier`` 的 likely 带下限对齐（同一口径，不另造档）。
UNCERTAIN_REFERENCE_CONFIDENCE = 0.6

#: calibration 呈现日预算（触发有度）：一天最多 N 次强调呈现，超限降级 ambient。
MAX_CALIBRATION_SURFACES_PER_DAY = 3

#: 回执携带的引用条目上限（既有 memory_reference_receipt 的 5 条面，不扩）。
MAX_REFERENCED_REFS = 5

_INTERNAL_REASON_MARKERS = ("policy_why", "joint_why", "allocation_why", ".sufficient", ".exhausted", "R0.", "R1.")


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return _strip(value).lower() in {"true", "1", "yes"}


def is_uncertain_reference(item: Mapping[str, Any]) -> bool:
    """单条引用是否构成「不确定引用」（真实条目事实的确定性投影）。

    判据（对齐 M-08 置信带语义，不发明第二口径）：显式 ``uncertain`` 标记 >
    置信 < ``UNCERTAIN_REFERENCE_CONFIDENCE`` > 未被用户确认（inferred 面）。
    """
    if "uncertain" in item:
        return _as_bool(item.get("uncertain"))
    confidence = _as_float(item.get("confidence"), 0.0)
    if confidence > 0 and confidence < UNCERTAIN_REFERENCE_CONFIDENCE:
        return True
    return not _as_bool(item.get("user_confirmed"))


def evaluate_receipt_surfacing(
    *,
    referenced_total: int,
    uncertain_total: int,
    calibration_shown_today: int,
) -> tuple[str, str]:
    """呈现门（纯函数；触发有度的机制面）。

    返回 ``(decision, reason)``：
    - ``hidden``：没有真实引用记忆——无可解释内容，绝不硬造回执；
    - ``ambient``：全部引用高置信且已确认（不打扰；回执仍在）或 calibration
      日预算耗尽（超限降级，不是吞掉）；
    - ``surfaced``：存在不确定引用且预算内——值得请用户校准。
    门只决定呈现强度，四个纠偏动作在 surfaced/ambient 两档下完全一致。
    """
    if referenced_total <= 0:
        return "hidden", "no_referenced_memory"
    if uncertain_total > 0 and calibration_shown_today < MAX_CALIBRATION_SURFACES_PER_DAY:
        return "surfaced", "uncertain_reference_within_budget"
    if uncertain_total > 0:
        return "ambient", "calibration_daily_budget_reached"
    return "ambient", "all_confident_no_uncertainty"


def build_calibration_receipt(
    *,
    response_id: str,
    referenced_memories: Sequence[Mapping[str, Any]],
    knowledge_refs: list[str] | None = None,
    calibration_shown_today: int = 0,
) -> dict[str, Any] | None:
    """装配 Why-this 回执（纯函数；输入即真实上下文解析结果，本模块不查库）。

    ``referenced_memories``：response_builder 已从真实上下文解析并经「自然被
    引用」检验的记忆条目（id/type/content/time_ago/source/confidence/
    user_confirmed）——回执与真实 Context 一致的锚点在调用方，本模块逐条透传
    并补充四动作面。

    rationale 守界（产品红线）：``rationale_summary`` 只由回执自身的组成计数
    模板化生成（几条记忆/几份材料/几处不确定），是 provenance 摘要而非推理
    过程；``annotations``/reason 码在数据流上进不了本模块（见模块 docstring）。
    """
    refs = [dict(item) for item in referenced_memories if isinstance(item, Mapping) and _strip(item.get("id"))]
    refs = refs[:MAX_REFERENCED_REFS]
    if not refs:
        return None

    knowledge = [_strip(name) for name in (knowledge_refs or []) if _strip(name)][:MAX_REFERENCED_REFS]
    uncertain_flags = [is_uncertain_reference(item) for item in refs]
    uncertain_count = sum(1 for flag in uncertain_flags if flag)

    surface_decision, surface_reason = evaluate_receipt_surfacing(
        referenced_total=len(refs),
        uncertain_total=uncertain_count,
        calibration_shown_today=max(0, int(calibration_shown_today or 0)),
    )

    uncertainties: list[dict[str, Any]] = []
    if uncertain_count > 0:
        uncertainties.append(
            {
                "kind": "unverified_inference",
                "label": RECEIPT_UNCERTAINTY_LABELS["unverified_inference"],
                "count": uncertain_count,
            }
        )

    material_part = f"和 {len(knowledge)} 份参考材料" if knowledge else ""
    if uncertain_count > 0:
        rationale = (
            f"这次回应参考了 {len(refs)} 条你的记忆{('，' + material_part) if material_part else ''}；"
            f"其中 {uncertain_count} 条我还不太确定，你可以直接纠正。"
        )
    else:
        rationale = f"这次回应参考了 {len(refs)} 条你的记忆{('，' + material_part) if material_part else ''}。"

    receipt_id = _receipt_id(response_id=response_id, memory_ids=[_strip(item.get("id")) for item in refs])
    receipt: dict[str, Any] = {
        "receipt_type": "memory_reference_receipt",
        "schema_version": CALIBRATION_RECEIPT_VERSION,
        "receipt_id": receipt_id,
        "response_id": _strip(response_id),
        # summary/decision_reason 与 rationale_summary 同源同文（移动端既有
        # 消费键的兼容面；三者都是组成摘要，不是推理过程）。
        "summary": rationale,
        "decision_reason": rationale,
        "rationale_summary": rationale,
        "used_count": len(refs),
        "referenced_memories": [
            {
                **item,
                "uncertain": flag,
                "actions": sorted(CALIBRATION_RECEIPT_ACTIONS),
            }
            for item, flag in zip(refs, uncertain_flags, strict=True)
        ],
        "knowledge_refs": knowledge,
        "uncertainties": uncertainties,
        "surface": {
            "decision": surface_decision,
            "reason": surface_reason,
            "presentation": "calibration" if surface_decision == "surfaced" else "ambient",
        },
        "memory_reference_outcome": "pending",
        "supported_outcomes": ["accepted", "corrected", "ignored", "denied"],
    }
    return receipt


def receipt_action_plan(
    *,
    action: str,
    corrected_content: str | None = None,
) -> dict[str, Any]:
    """动作 → 权威委托计划（路由层把计划执行掉；本函数零 IO）。

    脏动作名返回空 dict（调用方 422）——绝不静默改成别的动作。
    ``wrong`` 的双路语义：带更正内容走 supersede（M-01 法则），不带走降置信。
    """
    normalized = _strip(action).lower()
    if normalized not in CALIBRATION_RECEIPT_ACTIONS:
        return {}
    plan: dict[str, Any] = {"action": normalized, "authority": RECEIPT_ACTION_AUTHORITIES[normalized]}
    if normalized == "wrong":
        plan["mode"] = "supersede" if _strip(corrected_content) else "lower_confidence"
    return plan


def calibration_receipt_fingerprint() -> str:
    """冻结面指纹（契约测试双钉用）。"""
    payload = {
        "version": CALIBRATION_RECEIPT_VERSION,
        "actions": sorted(CALIBRATION_RECEIPT_ACTIONS),
        "authorities": dict(sorted(RECEIPT_ACTION_AUTHORITIES.items())),
        "surface_decisions": sorted(RECEIPT_SURFACE_DECISIONS),
        "uncertainty_labels": dict(sorted(RECEIPT_UNCERTAINTY_LABELS.items())),
        "uncertain_confidence": UNCERTAIN_REFERENCE_CONFIDENCE,
        "max_calibration_per_day": MAX_CALIBRATION_SURFACES_PER_DAY,
        "max_referenced_refs": MAX_REFERENCED_REFS,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _receipt_id(*, response_id: str, memory_ids: list[str]) -> str:
    seed = json.dumps(
        {"response_id": _strip(response_id), "refs": memory_ids},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "calreceipt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "CALIBRATION_RECEIPT_ACTIONS",
    "CALIBRATION_RECEIPT_VERSION",
    "MAX_CALIBRATION_SURFACES_PER_DAY",
    "MAX_REFERENCED_REFS",
    "RECEIPT_ACTION_AUTHORITIES",
    "RECEIPT_SURFACE_DECISIONS",
    "RECEIPT_UNCERTAINTY_LABELS",
    "UNCERTAIN_REFERENCE_CONFIDENCE",
    "build_calibration_receipt",
    "calibration_receipt_fingerprint",
    "evaluate_receipt_surfacing",
    "is_uncertain_reference",
    "receipt_action_plan",
]
