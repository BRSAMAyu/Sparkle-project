from __future__ import annotations
"""
Arbitration Service - Phase 2g

核心功能：
1. 管理人工仲裁流程
2. 处理升级的申诉案件
3. 提供管理员仲裁界面的后端支持
4. 记录仲裁决策和反馈学习

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_system import (
    ArbitrationCase as ArbitrationCaseModel,
)
from app.models.review_system import (
    ArbitrationDecision as ArbitrationDecisionModel,
)
from app.services.review_appeal_service import AppealDecision
from app.services.review_history_service import (
    AppealStatus,
    get_review_history_service,
)

# ============================================
# 数据模型
# ============================================


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

class ArbitratorRole(StrEnum):
    """仲裁员角色"""
    AUTO = "auto"               # 自动仲裁
    REVIEWER = "reviewer"       # 审查员
    SENIOR = "senior"           # 高级审查员
    ADMIN = "admin"             # 管理员


class ArbitrationPriority(StrEnum):
    """仲裁优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EscalationReason(StrEnum):
    """升级原因"""
    SCORE_DISCREPANCY = "score_discrepancy"       # 一二次审查分数差异大
    LOW_CONFIDENCE = "low_confidence"             # 低置信度
    USER_ESCALATION = "user_escalation"           # 用户请求升级
    REPEAT_APPEAL = "repeat_appeal"               # 重复申诉
    SENSITIVE_CONTENT = "sensitive_content"       # 敏感内容
    POLICY_VIOLATION = "policy_violation"         # 政策违规
    SYSTEM_ERROR = "system_error"                 # 系统错误


@dataclass
class ArbitrationCase:
    """仲裁案件"""
    case_id: str
    appeal_id: str
    review_id: str
    user_id: str
    escalation_reason: EscalationReason
    priority: ArbitrationPriority = ArbitrationPriority.NORMAL
    created_at: str = ""

    # 案件状态
    status: str = "pending"  # pending, assigned, in_review, resolved
    assigned_to: str | None = None
    assigned_at: str | None = None

    # 审查信息
    original_review_score: float = 0.0
    secondary_review_score: float | None = None
    score_discrepancy: float = 0.0

    # 仲裁结果
    resolution: str | None = None
    final_decision: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None

    # 元数据
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _utcnow().isoformat()


@dataclass
class ArbitrationDecision:
    """仲裁决策"""
    case_id: str
    decision: AppealDecision
    explanation: str
    arbitrator_id: str
    arbitrator_role: ArbitratorRole
    confidence: float = 1.0
    feedback_for_model: str | None = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _utcnow().isoformat()


@dataclass
class ArbitrationQueueStats:
    """仲裁队列统计"""
    total_pending: int = 0
    total_assigned: int = 0
    total_in_review: int = 0
    total_resolved_today: int = 0
    avg_resolution_time_hours: float = 0.0
    by_priority: dict[str, int] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)


# ============================================
# Escalation Rules Engine
# ============================================

class EscalationRulesEngine:
    """
    升级规则引擎

    决定何时将案件升级到人工仲裁
    """

    # 阈值配置
    SCORE_DISCREPANCY_THRESHOLD = 0.25  # 分数差异阈值
    LOW_CONFIDENCE_THRESHOLD = 0.6      # 低置信度阈值
    REPEAT_APPEAL_THRESHOLD = 2         # 重复申诉次数阈值

    @classmethod
    def should_escalate(
        cls,
        original_score: float,
        secondary_score: float | None,
        confidence: float,
        appeal_count: int = 1,
        is_sensitive: bool = False,
    ) -> tuple[bool, EscalationReason | None]:
        """
        判断是否需要升级到人工仲裁

        Returns:
            (should_escalate, reason)
        """
        # 敏感内容总是升级
        if is_sensitive:
            return True, EscalationReason.SENSITIVE_CONTENT

        # 重复申诉升级
        if appeal_count >= cls.REPEAT_APPEAL_THRESHOLD:
            return True, EscalationReason.REPEAT_APPEAL

        # 低置信度升级
        if confidence < cls.LOW_CONFIDENCE_THRESHOLD:
            return True, EscalationReason.LOW_CONFIDENCE

        # 分数差异大升级
        if secondary_score is not None:
            discrepancy = abs(secondary_score - original_score)
            if discrepancy >= cls.SCORE_DISCREPANCY_THRESHOLD:
                return True, EscalationReason.SCORE_DISCREPANCY

        return False, None

    @classmethod
    def calculate_priority(
        cls,
        escalation_reason: EscalationReason,
        user_tier: str = "free",
        waiting_hours: float = 0.0,
    ) -> ArbitrationPriority:
        """
        计算仲裁优先级

        Args:
            escalation_reason: 升级原因
            user_tier: 用户等级 (free, pro, enterprise)
            waiting_hours: 等待时间（小时）

        Returns:
            仲裁优先级
        """
        base_priority = ArbitrationPriority.NORMAL

        # 敏感内容和政策违规为紧急
        if escalation_reason in (
            EscalationReason.SENSITIVE_CONTENT,
            EscalationReason.POLICY_VIOLATION,
        ):
            base_priority = ArbitrationPriority.URGENT

        # 系统错误为高优先级
        elif escalation_reason == EscalationReason.SYSTEM_ERROR:
            base_priority = ArbitrationPriority.HIGH

        # 付费用户提升优先级
        if user_tier in ("pro", "enterprise"):
            priority_map = {
                ArbitrationPriority.LOW: ArbitrationPriority.NORMAL,
                ArbitrationPriority.NORMAL: ArbitrationPriority.HIGH,
                ArbitrationPriority.HIGH: ArbitrationPriority.URGENT,
                ArbitrationPriority.URGENT: ArbitrationPriority.URGENT,
            }
            base_priority = priority_map[base_priority]

        # 长时间等待提升优先级
        if waiting_hours > 24:
            priority_map = {
                ArbitrationPriority.LOW: ArbitrationPriority.NORMAL,
                ArbitrationPriority.NORMAL: ArbitrationPriority.HIGH,
                ArbitrationPriority.HIGH: ArbitrationPriority.URGENT,
                ArbitrationPriority.URGENT: ArbitrationPriority.URGENT,
            }
            base_priority = priority_map[base_priority]

        return base_priority


# ============================================
# Arbitration Service
# ============================================

class ArbitrationService:
    """
    人工仲裁服务

    职责：
    1. 创建和管理仲裁案件
    2. 分配案件给仲裁员
    3. 记录仲裁决策
    4. 提供仲裁队列统计
    5. 反馈学习整合
    """

    def __init__(self, db_session: AsyncSession):
        self._db = db_session
        self._history_service = get_review_history_service(db_session)

    @staticmethod
    def _parse_uuid(value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return None

    def _to_case_entry(self, model: ArbitrationCaseModel) -> ArbitrationCase:
        return ArbitrationCase(
            case_id=model.case_id,
            appeal_id=model.appeal_id,
            review_id=model.review_id,
            user_id=str(model.user_id) if model.user_id else "",
            escalation_reason=EscalationReason(model.escalation_reason),
            priority=ArbitrationPriority(model.priority),
            created_at=model.created_at.isoformat(),
            status=model.status,
            assigned_to=model.assigned_to,
            assigned_at=model.assigned_at.isoformat() if model.assigned_at else None,
            original_review_score=model.original_review_score or 0.0,
            secondary_review_score=model.secondary_review_score,
            score_discrepancy=model.score_discrepancy or 0.0,
            resolution=model.resolution,
            final_decision=model.final_decision,
            resolved_at=model.resolved_at.isoformat() if model.resolved_at else None,
            resolved_by=model.resolved_by,
            notes=model.notes or [],
            evidence=model.evidence or {},
        )

    def _to_decision_entry(self, model: ArbitrationDecisionModel) -> ArbitrationDecision:
        return ArbitrationDecision(
            case_id=model.case_id,
            decision=AppealDecision(model.decision),
            explanation=model.explanation,
            arbitrator_id=model.arbitrator_id,
            arbitrator_role=ArbitratorRole(model.arbitrator_role),
            confidence=model.confidence or 1.0,
            feedback_for_model=model.feedback_for_model,
            created_at=model.decided_at.isoformat() if model.decided_at else "",
        )

    async def create_case(
        self,
        appeal_id: str,
        escalation_reason: EscalationReason,
        original_score: float,
        secondary_score: float | None = None,
        user_tier: str = "free",
    ) -> ArbitrationCase:
        """
        创建仲裁案件

        Args:
            appeal_id: 申诉ID
            escalation_reason: 升级原因
            original_score: 原审查分数
            secondary_score: 二次审查分数
            user_tier: 用户等级

        Returns:
            创建的仲裁案件
        """
        logger.info(
            f"[ArbitrationService] Creating case for appeal {appeal_id}, "
            f"reason={escalation_reason.value}"
        )

        # 获取申诉信息
        appeal = await self._history_service.get_appeal_by_id(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal {appeal_id} not found")

        # 计算优先级
        priority = EscalationRulesEngine.calculate_priority(
            escalation_reason=escalation_reason,
            user_tier=user_tier,
        )

        # 创建案件
        case = ArbitrationCase(
            case_id=f"arb_{uuid.uuid4().hex[:12]}",
            appeal_id=appeal_id,
            review_id=appeal.review_id,
            user_id=appeal.user_id,
            escalation_reason=escalation_reason,
            priority=priority,
            original_review_score=original_score,
            secondary_review_score=secondary_score,
            score_discrepancy=abs(secondary_score - original_score) if secondary_score else 0.0,
        )

        case_model = ArbitrationCaseModel(
            case_id=case.case_id,
            appeal_id=case.appeal_id,
            review_id=case.review_id,
            user_id=self._parse_uuid(case.user_id),
            escalation_reason=case.escalation_reason.value,
            priority=case.priority.value,
            status=case.status,
            assigned_to=case.assigned_to,
            assigned_at=datetime.fromisoformat(case.assigned_at) if case.assigned_at else None,
            original_review_score=case.original_review_score,
            secondary_review_score=case.secondary_review_score,
            score_discrepancy=case.score_discrepancy,
            resolution=case.resolution,
            final_decision=case.final_decision,
            resolved_at=datetime.fromisoformat(case.resolved_at) if case.resolved_at else None,
            resolved_by=case.resolved_by,
            notes=case.notes,
            evidence=case.evidence,
        )

        self._db.add(case_model)
        await self._db.flush()
        case = self._to_case_entry(case_model)

        # 更新申诉状态为已升级
        await self._history_service.update_appeal_status(
            appeal_id=appeal_id,
            status=AppealStatus.ESCALATED,
        )

        logger.info(
            f"[ArbitrationService] Case created: {case.case_id}, "
            f"priority={priority.value}"
        )

        return case

    async def assign_case(
        self,
        case_id: str,
        arbitrator_id: str,
        arbitrator_role: ArbitratorRole = ArbitratorRole.REVIEWER,
    ) -> ArbitrationCase:
        """
        分配案件给仲裁员

        Args:
            case_id: 案件ID
            arbitrator_id: 仲裁员ID
            arbitrator_role: 仲裁员角色

        Returns:
            更新后的案件
        """
        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Case {case_id} not found")
        case = self._to_case_entry(model)

        case.status = "assigned"
        case.assigned_to = arbitrator_id
        case.assigned_at = _utcnow().isoformat()

        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = "assigned"
            model.assigned_to = arbitrator_id
            model.assigned_at = _utcnow()
            await self._db.flush()

        logger.info(
            f"[ArbitrationService] Case {case_id} assigned to {arbitrator_id}"
        )

        return case

    async def submit_decision(
        self,
        case_id: str,
        decision: AppealDecision,
        explanation: str,
        arbitrator_id: str,
        arbitrator_role: ArbitratorRole,
        feedback_for_model: str | None = None,
    ) -> ArbitrationDecision:
        """
        提交仲裁决策

        Args:
            case_id: 案件ID
            decision: 决策
            explanation: 解释
            arbitrator_id: 仲裁员ID
            arbitrator_role: 仲裁员角色
            feedback_for_model: 给模型的反馈（用于学习）

        Returns:
            仲裁决策
        """
        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Case {case_id} not found")
        case = self._to_case_entry(model)

        logger.info(
            f"[ArbitrationService] Decision submitted for case {case_id}: "
            f"{decision.value}"
        )

        # 创建决策记录
        arb_decision = ArbitrationDecision(
            case_id=case_id,
            decision=decision,
            explanation=explanation,
            arbitrator_id=arbitrator_id,
            arbitrator_role=arbitrator_role,
            feedback_for_model=feedback_for_model,
        )

        decision_model = ArbitrationDecisionModel(
            case_id=case_id,
            decision=decision.value,
            explanation=explanation,
            arbitrator_id=arbitrator_id,
            arbitrator_role=arbitrator_role.value,
            confidence=arb_decision.confidence,
            feedback_for_model=feedback_for_model,
            decided_at=_utcnow(),
        )
        self._db.add(decision_model)
        await self._db.flush()

        # 更新案件状态
        case.status = "resolved"
        case.resolution = explanation
        case.final_decision = decision.value
        case.resolved_at = _utcnow().isoformat()
        case.resolved_by = arbitrator_id

        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = "resolved"
            model.resolution = explanation
            model.final_decision = decision.value
            model.resolved_at = _utcnow()
            model.resolved_by = arbitrator_id
            await self._db.flush()

        # 更新申诉状态
        final_appeal_status = (
            AppealStatus.RESOLVED if decision in (
                AppealDecision.APPROVED,
                AppealDecision.PARTIALLY_APPROVED,
            )
            else AppealStatus.REJECTED
        )

        await self._history_service.update_appeal_status(
            appeal_id=case.appeal_id,
            status=final_appeal_status,
            resolution=explanation,
            resolved_by=arbitrator_id,
        )

        # 如果有模型反馈，记录用于学习
        if feedback_for_model:
            await self._record_model_feedback(
                case=case,
                decision=arb_decision,
            )

        logger.info(
            f"[ArbitrationService] Case {case_id} resolved: "
            f"decision={decision.value}"
        )

        return arb_decision

    async def _record_model_feedback(
        self,
        case: ArbitrationCase,
        decision: ArbitrationDecision,
    ) -> None:
        """记录模型反馈用于学习"""
        # 这里可以集成到反馈学习系统
        logger.info(
            f"[ArbitrationService] Recording model feedback for case {case.case_id}: "
            f"{decision.feedback_for_model}"
        )
        # TRACKED(TD-008): 集成到 FeedbackDrivenGenerationService 或其他学习服务

    async def get_case(self, case_id: str) -> ArbitrationCase | None:
        """获取案件详情"""
        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_case_entry(model)

    async def get_pending_queue(
        self,
        limit: int = 50,
        priority: ArbitrationPriority | None = None,
    ) -> list[ArbitrationCase]:
        """
        获取待处理队列

        Args:
            limit: 限制数量
            priority: 筛选优先级

        Returns:
            待处理案件列表
        """
        query = select(ArbitrationCaseModel).where(ArbitrationCaseModel.status == "pending")
        if priority:
            query = query.where(ArbitrationCaseModel.priority == priority.value)

        result = await self._db.execute(query)
        models = result.scalars().all()

        priority_order = {
            ArbitrationPriority.URGENT: 0,
            ArbitrationPriority.HIGH: 1,
            ArbitrationPriority.NORMAL: 2,
            ArbitrationPriority.LOW: 3,
        }
        cases = [self._to_case_entry(model) for model in models]
        cases.sort(key=lambda c: (priority_order[c.priority], c.created_at))
        return cases[:limit]

    async def get_assigned_cases(
        self,
        arbitrator_id: str,
    ) -> list[ArbitrationCase]:
        """获取分配给特定仲裁员的案件"""
        result = await self._db.execute(
            select(ArbitrationCaseModel).where(
                ArbitrationCaseModel.assigned_to == arbitrator_id,
                ArbitrationCaseModel.status.in_(["assigned", "in_review"]),
            )
        )
        return [self._to_case_entry(model) for model in result.scalars().all()]

    async def get_queue_stats(self) -> ArbitrationQueueStats:
        """获取队列统计"""
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self._db.execute(select(ArbitrationCaseModel))
        all_cases = [self._to_case_entry(model) for model in result.scalars().all()]

        # 计算各状态数量
        pending = [c for c in all_cases if c.status == "pending"]
        assigned = [c for c in all_cases if c.status == "assigned"]
        in_review = [c for c in all_cases if c.status == "in_review"]
        resolved_today = [
            c for c in all_cases
            if c.status == "resolved"
            and c.resolved_at
            and datetime.fromisoformat(c.resolved_at) >= today_start
        ]

        # 按优先级统计
        by_priority = {}
        for p in ArbitrationPriority:
            by_priority[p.value] = len([
                c for c in pending if c.priority == p
            ])

        # 按原因统计
        by_reason = {}
        for r in EscalationReason:
            by_reason[r.value] = len([
                c for c in pending if c.escalation_reason == r
            ])

        # 计算平均解决时间
        resolved_with_time = [
            c for c in all_cases
            if c.status == "resolved" and c.resolved_at
        ]

        resolution_times = []
        for c in resolved_with_time:
            created = datetime.fromisoformat(c.created_at)
            resolved = datetime.fromisoformat(c.resolved_at)
            diff = (resolved - created).total_seconds() / 3600
            resolution_times.append(diff)

        avg_time = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0.0
        )

        return ArbitrationQueueStats(
            total_pending=len(pending),
            total_assigned=len(assigned),
            total_in_review=len(in_review),
            total_resolved_today=len(resolved_today),
            avg_resolution_time_hours=avg_time,
            by_priority=by_priority,
            by_reason=by_reason,
        )

    async def add_case_note(
        self,
        case_id: str,
        note: str,
        author_id: str,
    ) -> None:
        """添加案件备注"""
        result = await self._db.execute(
            select(ArbitrationCaseModel).where(ArbitrationCaseModel.case_id == case_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Case {case_id} not found")

        timestamp = _utcnow().isoformat()
        formatted_note = f"[{timestamp}] {author_id}: {note}"
        existing_notes = model.notes or []
        existing_notes.append(formatted_note)
        model.notes = existing_notes
        await self._db.flush()

        logger.info(f"[ArbitrationService] Note added to case {case_id}")

    async def bulk_assign(
        self,
        case_ids: list[str],
        arbitrator_id: str,
        arbitrator_role: ArbitratorRole = ArbitratorRole.REVIEWER,
    ) -> int:
        """
        批量分配案件

        Returns:
            成功分配的数量
        """
        assigned_count = 0
        for case_id in case_ids:
            try:
                await self.assign_case(
                    case_id=case_id,
                    arbitrator_id=arbitrator_id,
                    arbitrator_role=arbitrator_role,
                )
                assigned_count += 1
            except ValueError as e:
                logger.warning(f"[ArbitrationService] Failed to assign {case_id}: {e}")

        return assigned_count


# ============================================
# 全局实例管理
# ============================================

_arbitration_services: dict[int, ArbitrationService] = {}


def get_arbitration_service(db_session: AsyncSession) -> ArbitrationService:
    """获取ArbitrationService实例"""
    session_id = id(db_session)
    if session_id not in _arbitration_services:
        _arbitration_services[session_id] = ArbitrationService(db_session)
    return _arbitration_services[session_id]
