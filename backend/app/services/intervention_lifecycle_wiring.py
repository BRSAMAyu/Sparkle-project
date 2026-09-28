"""V3-FIX-507 · D-05 intervention lifecycle 生产接线（写面，韧性壳）。

修的问题（台账 V3-FIX-507）：D-05 ``InterventionLifecycleService`` 的四个写方法
全仓生产面零调用——读侧三消费方（D-07 洞察卡 / M-06 经验投影 / North Star
intervention 面）全部已接线但恒空，数据飞轮中段断链被测试全绿掩盖。

设计纪律（台账 T-d05-lifecycle-production-wiring）：
- **只在既有事件流的真实节点挂调用，不造新事件、不造轮询**：
  1. 交付面：``InterventionRecordService.mark_delivered``（消费者交付与反馈路径
     CREATED→DELIVERED 的唯一收敛点）→ ``record_exposure``；
     ``mark_accepted`` / ``mark_dismissed`` / ``mark_acted`` →
     ``record_response``（accepted / rejected / started——D-05 封闭词表的
     既有语义；snoozed/seen 无词表成员，不接线、不造语义）。
  2. Aurora decision 执行点：``SpineOrchestrator`` 管线 directive 定稿下发处 →
     ``record_exposure``（契约构造参照 A-01 L2 ``_build_decision_contract`` 先例，
     intervention_type 经 A-02 ``SPINE_STRATEGY_TO_INTERVENTION`` 冻结投影）。
  3. D-02 ledger 增量扫描定时任务（app/core/celery_tasks.py）→
     ``associate_pending_outcomes``。
- **韧性壳（FIX-530 判例）**：接线失败只 ``logger.warning``，永不拖垮宿主链路
  （交付转场 / spine 管线 / 定时扫描）。D-05 服务自身的 refused（inert/shadow/
  无 exposure/畸形 id）是可观测降级而非异常，原样留痕。
- **不伪造锚点**：交付面无 spine 信号锚 → friction 留 ``unattributed``（不算
  分析失败，D-05 词表既有档）；spine 面无 plans/tasks UUID 锚 → linkage 留空。
  交付面唯一合法关联桥是 plan_card → ``legacy_plan_id``（与 D-02 task 完成
  ``correlation.plan_id`` 同 plans.id 域）。
- **decision_id 全部经** ``AuroraDecisionContract.decision_id_or_compute()``
  内容寻址产出（``aurora_<32hex>``），不手搓前缀。

投影映射（ InterventionTriggerType → A-01 目录，L2_INTERVENTION_TO_CATALOG
同款冻结纪律；语义判据逐条对齐 A-02 ``SPINE_STRATEGY_TO_INTERVENTION`` 既有
判例，新增 trigger 必须登记，wiring 测试强制全员覆盖）：
- PLAN_RISK    → rescope（adjust_plan→rescope：计划路径软重排）
- CONCEPT_GAP  → practice（repair_knowledge_bottleneck→practice：知识缺口修复）
- STALL_PATTERN→ split（insert_easy_win→split：微小重启/易赢步骤）
- OVERLOAD     → pause（reduce_next_48h_load→pause：负荷下调）
- MISALIGNMENT → explain（insert_reassurance→explain：安抚性解释/自我效能恢复）
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aurora_decision import AuroraDecisionContract
from app.core.intervention_lifecycle import LifecycleEventType

# 会话工厂（模块级符号，测试换装点；生产为 app.db.session.AsyncSessionLocal）。
from app.db.session import AsyncSessionLocal  # noqa: F401
from app.models.card_protocol import (
    Card,
    InterventionAcceptanceStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.services.intervention_lifecycle_service import (
    InterventionLifecycleService,
    LifecycleRecordResult,
)

__all__ = [
    "TRIGGER_TO_CATALOG_INTERVENTION",
    "ACCEPTANCE_TO_LIFECYCLE_EVENT",
    "build_directive_decision_contract",
    "build_record_decision_contract",
    "record_delivery_exposure",
    "record_directive_exposure_for_user",
    "record_record_response",
]


# ---------------------------------------------------------------------------
# 冻结投影映射（见模块 docstring 语义判据）
# ---------------------------------------------------------------------------

TRIGGER_TO_CATALOG_INTERVENTION: dict[InterventionTriggerType, str] = {
    InterventionTriggerType.PLAN_RISK: "rescope",
    InterventionTriggerType.CONCEPT_GAP: "practice",
    InterventionTriggerType.STALL_PATTERN: "split",
    InterventionTriggerType.OVERLOAD: "pause",
    InterventionTriggerType.MISALIGNMENT: "explain",
}

#: 交付面接受状态 → D-05 封闭词表响应事件（seen/snoozed 无词表成员，不映射）。
ACCEPTANCE_TO_LIFECYCLE_EVENT: dict[InterventionAcceptanceStatus, LifecycleEventType] = {
    InterventionAcceptanceStatus.ACCEPTED: LifecycleEventType.ACCEPTED,
    InterventionAcceptanceStatus.DISMISSED: LifecycleEventType.REJECTED,
    InterventionAcceptanceStatus.ACTED: LifecycleEventType.STARTED,
}

_DELIVERY_COGNITION_TIER = "l0_rules"  # 交付选择是确定性规则（taxonomy + 桥）
_SPINE_COGNITION_TIER = "l1_light"  # spine 管线规则评估（无 LLM）

# V4-D01 · delivered/rendered 语义区分（增量；不改本面既有接线语义）：
# 交付面 lifecycle exposed 行的 detail 显式携带 exposure_basis="delivered"——
# 它是**交付回执**（服务端确实下发了），不等于「用户真的看到」；「用户实际
# 可见面」由 experience_event.v1 rendered 增量承载
# （app/services/experience_event_service.py，唯一入口 mark_seen 真实转场）。
EXPOSURE_BASIS_DETAIL_KEY = "exposure_basis"
DELIVERY_EXPOSURE_BASIS = "delivered"


# ---------------------------------------------------------------------------
# 契约构造（交付面 / spine 面）
# ---------------------------------------------------------------------------


def build_record_decision_contract(record: InterventionRecord) -> AuroraDecisionContract | None:
    """把一次 InterventionRecord 投影为 aurora_decision.v1 契约（交付面）。

    - intervention_type：TRIGGER_TO_CATALOG_INTERVENTION 投影；未登记 trigger
      → None（宁可无 lifecycle 记录也不产词表外干预）；
    - decision_id 内容寻址输入含 record 身份（每次交付是独立决策实例；
      重放/重复标记恒同 id → D-05 幂等去重）；
    - execution_mode 镜像 A-02 目录 nominal_execution_mode（无分配事实时的
      契约标称值，A-02 权威语义）。
    """
    from app.aurora.intervention_catalog import INTERVENTION_CATALOG
    from app.core.aurora_decision import _INERT_INTERVENTIONS
    from app.models.execution_intent import ExecutionMode

    trigger = record.trigger_type
    catalog_type = TRIGGER_TO_CATALOG_INTERVENTION.get(trigger)
    if catalog_type is None or catalog_type in _INERT_INTERVENTIONS:
        return None
    item = INTERVENTION_CATALOG[catalog_type]
    if item.nominal_execution_mode is None:
        return None

    diagnosis = dict(record.diagnosis_payload or {})
    reasons = [str(r) for r in (diagnosis.get("reasons") or []) if str(r).strip()]
    pattern = str(diagnosis.get("pattern_name") or "").strip()
    rationale = pattern or (reasons[0] if reasons else "")
    if not rationale.strip():
        rationale = f"{trigger.value} intervention via {record.delivery_strategy.value}"

    return AuroraDecisionContract(
        user_id=record.user_id,
        intervention_type=catalog_type,
        rationale_summary=rationale,
        cognition_tier=_DELIVERY_COGNITION_TIER,
        execution_mode=ExecutionMode(item.nominal_execution_mode),
        governance_mode="live",
        trigger_point="card_protocol_delivery",
        input_context_hash=hashlib.sha256(f"intervention_record:{record.id}".encode()).hexdigest()[:32],
        annotations={
            "intervention_record_id": str(record.id),
            "trigger_type": trigger.value,
            "delivery_channel": record.delivery_channel.value,
            "delivery_strategy": record.delivery_strategy.value,
        },
    )


def build_directive_decision_contract(
    *,
    user_id: UUID,
    signal: Any,
    decision: Any,
    directive: Any,
) -> AuroraDecisionContract | None:
    """把 spine 管线一次 directive 下发投影为 aurora_decision.v1 契约。

    参照 A-01 L2 ``_build_decision_contract`` 先例：strategy 经
    ``SPINE_STRATEGY_TO_INTERVENTION`` 投影，inert/未映射 → None（不行动没有
    用户可见载体；record_exposure 对 inert 亦拒绝——先在此短路省一次 IO）。
    evidence_refs 携 ``signal://<state_key>``（friction_tag 真实归因的来源）。
    """
    from app.aurora.intervention_catalog import INTERVENTION_CATALOG, SPINE_STRATEGY_TO_INTERVENTION
    from app.core.aurora_decision import _INERT_INTERVENTIONS
    from app.models.execution_intent import ExecutionMode

    strategy = str(getattr(decision, "primary_strategy", "") or "").strip()
    catalog_type = SPINE_STRATEGY_TO_INTERVENTION.get(strategy)
    if catalog_type is None or catalog_type in _INERT_INTERVENTIONS:
        return None
    item = INTERVENTION_CATALOG[catalog_type]
    if item.nominal_execution_mode is None:
        return None

    state_key = str(getattr(signal, "state_key", "") or "").strip()
    reasoning = (
        str(getattr(decision, "reasoning_summary", "") or getattr(signal, "evidence_summary", "") or "").strip()
        or f"spine strategy {strategy}"
    )
    directive_id = str(getattr(directive, "directive_id", "") or "")

    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=catalog_type,
        rationale_summary=reasoning,
        cognition_tier=_SPINE_COGNITION_TIER,
        execution_mode=ExecutionMode(item.nominal_execution_mode),
        governance_mode="live",
        trigger_point="spine_pipeline_directive",
        input_context_hash=hashlib.sha256(f"directive:{directive_id}".encode()).hexdigest()[:32],
        evidence_refs=(f"signal://{state_key}",) if state_key else (),
        annotations={
            "directive_id": directive_id,
            "policy_decision_id": str(getattr(decision, "policy_decision_id", "") or ""),
            "primary_strategy": strategy,
        },
    )


# ---------------------------------------------------------------------------
# 写面 1：交付面（显式 db；调用方 = InterventionRecordService）
# ---------------------------------------------------------------------------


async def _delivery_plan_linkage(db: AsyncSession, record: InterventionRecord) -> dict[str, str]:
    """plan_card → legacy_plan_id 关联键（plans.id 域；无效值剔除不炸）。"""
    if not record.plan_card_id:
        return {}
    try:
        card = await db.get(Card, record.plan_card_id)
    except Exception:  # noqa: BLE001 — 卡读取失败不留空关联之外的影响
        return {}
    if card is None or not card.metadata_:
        return {}
    legacy = card.metadata_.get("legacy_plan_id")
    if not legacy:
        return {}
    try:
        return {"plan_id": str(UUID(str(legacy)))}
    except (ValueError, TypeError, AttributeError):
        return {}


async def record_delivery_exposure(db: AsyncSession, record: InterventionRecord) -> LifecycleRecordResult | None:
    """交付即暴露（写面 1a）：mark_delivered 的 lifecycle 挂点。韧性壳。"""
    try:
        contract = build_record_decision_contract(record)
        if contract is None:
            return None
        linkage = await _delivery_plan_linkage(db, record)
        return await InterventionLifecycleService(db).record_exposure(
            decision=contract,
            user_id=record.user_id,
            plan_id=linkage.get("plan_id"),
            window_hours=int(record.outcome_window_days) * 24,
            detail={
                "intervention_record_id": str(record.id),
                "trigger_type": record.trigger_type.value,
                "delivery_channel": record.delivery_channel.value,
                "delivery_strategy": record.delivery_strategy.value,
                # V4-D01：显式标记交付回执语义（delivered ≠ rendered/seen）。
                EXPOSURE_BASIS_DETAIL_KEY: DELIVERY_EXPOSURE_BASIS,
            },
        )
    except Exception as exc:  # noqa: BLE001 — 韧性壳：交付链路永不被 lifecycle 拖垮
        logger.warning(
            "D-05 lifecycle delivery exposure recording failed (record={}): {}",
            getattr(record, "id", "-"),
            exc,
        )
        return None


async def record_record_response(
    db: AsyncSession,
    record: InterventionRecord,
    event_type: LifecycleEventType,
) -> LifecycleRecordResult | None:
    """用户响应（写面 1b）：accepted/rejected/started 转场的 lifecycle 挂点。

    无 exposure 的响应被 D-05 漏斗完整性门拒收（refused，可观测降级）——
    本函数不吞 refused，只吞异常（refused 是 D-05 既有语义，调用方可观测）。
    """
    try:
        contract = build_record_decision_contract(record)
        if contract is None:
            return None
        return await InterventionLifecycleService(db).record_response(
            decision_id=contract.decision_id_or_compute(),
            user_id=record.user_id,
            event_type=event_type,
            detail={"intervention_record_id": str(record.id)},
        )
    except Exception as exc:  # noqa: BLE001 — 韧性壳
        logger.warning(
            "D-05 lifecycle response recording failed (record={}, event={}): {}",
            getattr(record, "id", "-"),
            event_type.value,
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# 写面 2：Aurora decision 执行点（自开 session；调用方 = SpineOrchestrator）
# ---------------------------------------------------------------------------


async def record_directive_exposure_for_user(
    *,
    user_id: str,
    signal: Any,
    decision: Any,
    directive: Any,
) -> str | None:
    """spine 管线 directive 下发 → 自持短会话记录 exposure（韧性壳）。

    返回记录成功时的 decision_id（aurora_<32hex>）；跳过/拒绝/失败一律 None。
    user_id 不可解析为 UUID 时跳过（L2 引擎同款纪律）。
    """
    try:
        parsed = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        return None
    try:
        contract = build_directive_decision_contract(
            user_id=parsed, signal=signal, decision=decision, directive=directive
        )
        if contract is None:
            return None
        state_key = str(getattr(signal, "state_key", "") or "").strip()
        goal_type = getattr(signal, "goal_type", None)
        async with AsyncSessionLocal() as db:
            result = await InterventionLifecycleService(db).record_exposure(
                decision=contract,
                user_id=parsed,
                friction_state_key=state_key or None,
                goal_type=str(goal_type) if goal_type else None,
                detail={
                    "directive_id": str(getattr(directive, "directive_id", "") or ""),
                    "policy_decision_id": str(getattr(decision, "policy_decision_id", "") or ""),
                    "primary_strategy": str(getattr(decision, "primary_strategy", "") or ""),
                },
            )
        if result.recorded:
            return contract.decision_id_or_compute()
        logger.debug(
            "D-05 spine exposure not recorded (reason={}, decision={})",
            result.reason,
            result.decision_id,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — 韧性壳：spine 管线永不被 lifecycle 拖垮
        logger.warning("D-05 spine directive exposure recording failed (user={}): {}", user_id, exc)
        return None
