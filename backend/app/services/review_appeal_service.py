from __future__ import annotations

"""
Review Appeal Service - Phase 2e

核心功能：
1. 处理用户申诉请求
2. 触发二次审查
3. 管理申诉队列
4. 提供申诉状态追踪

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import TaskType
from app.models.chat import ChatMessage
from app.services.llm_service import get_llm_service_for_task
from app.services.review_history_service import (
    AppealEntry,
    AppealStatus,
    get_review_history_service,
)

# ============================================
# 数据模型
# ============================================


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

class AppealPriority(StrEnum):
    """申诉优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AppealDecision(StrEnum):
    """申诉决策"""
    APPROVED = "approved"           # 申诉通过，推翻原审查
    REJECTED = "rejected"           # 申诉拒绝，维持原审查
    PARTIALLY_APPROVED = "partially_approved"  # 部分通过
    ESCALATED = "escalated"         # 升级到人工处理


@dataclass
class AppealRequest:
    """申诉请求"""
    user_id: str
    review_id: str
    appeal_reason: str
    issues_with_review: list[str] = field(default_factory=list)
    evidence: dict[str, Any] | None = None
    priority: AppealPriority = AppealPriority.NORMAL


@dataclass
class AppealDecisionResult:
    """申诉决策结果"""
    appeal_id: str
    decision: AppealDecision
    explanation: str
    secondary_review_score: float | None = None
    confidence: float = 0.0
    reviewed_by: str = "system"
    reviewed_at: str = ""

    def __post_init__(self):
        if not self.reviewed_at:
            self.reviewed_at = _utcnow().isoformat()


# ============================================
# Appeal Review Service
# ============================================

class AppealReviewService:
    """
    申诉审查服务

    职责：
    1. 接收并验证申诉请求
    2. 触发二次审查（使用不同模型）
    3. 比较一次和二次审查结果
    4. 做出申诉决策
    5. 管理申诉队列
    """

    # 二次审查模型配置
    SECONDARY_REVIEWER_MODEL = "glm-4-plus"  # 使用不同模型进行二次审查

    # 自动仲裁阈值
    AUTO_APPROVE_SCORE_DIFF = 0.3  # 如果二次审查分数比一次高0.3，自动通过
    AUTO_REJECT_SCORE_DIFF = -0.1  # 如果二次审查分数更低，自动拒绝
    ESCALATION_CONFIDENCE_THRESHOLD = 0.6  # 低于此置信度升级人工

    def __init__(self, db_session: AsyncSession):
        self._db = db_session
        self._history_service = get_review_history_service(db_session)

    async def submit_appeal(
        self,
        request: AppealRequest,
    ) -> AppealEntry:
        """
        提交申诉

        Args:
            request: 申诉请求

        Returns:
            创建的申诉条目
        """
        logger.info(
            f"[AppealService] Submitting appeal for review {request.review_id} "
            f"by user {request.user_id}"
        )

        # 1. 验证原审查存在
        original_review = await self._history_service.get_review_by_id(request.review_id)
        if not original_review:
            raise ValueError(f"Review {request.review_id} not found")

        # 2. 检查是否已有申诉
        existing_appeals = await self._history_service.get_appeal_queue(
            status=None,
        )
        for appeal in existing_appeals:
            if appeal.review_id == request.review_id and appeal.status == AppealStatus.PENDING:
                raise ValueError(f"Appeal already pending for review {request.review_id}")

        # 3. 创建申诉记录
        appeal = await self._history_service.record_review_appeal(
            review_id=request.review_id,
            user_id=request.user_id,
            appeal_reason=request.appeal_reason,
            issues_with_review=request.issues_with_review,
        )

        logger.info(f"[AppealService] Appeal created: {appeal.appeal_id}")

        return appeal

    async def process_secondary_review(
        self,
        appeal_id: str,
        secondary_reviewer_model: str | None = None,
    ) -> AppealDecisionResult:
        """
        处理二次审查

        Args:
            appeal_id: 申诉ID
            secondary_reviewer_model: 二次审查使用的模型

        Returns:
            申诉决策结果
        """
        logger.info(f"[AppealService] Processing secondary review for appeal {appeal_id}")

        # 1. 获取申诉
        appeal = await self._history_service.get_appeal_by_id(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal {appeal_id} not found")

        # 2. 更新状态为审查中
        await self._history_service.update_appeal_status(
            appeal_id=appeal_id,
            status=AppealStatus.IN_REVIEW,
        )

        # 3. 获取原审查
        original_review = await self._history_service.get_review_by_id(appeal.review_id)
        if not original_review:
            raise ValueError(f"Original review {appeal.review_id} not found")

        # 4. 执行二次审查
        secondary_result = await self._execute_secondary_review(
            original_review=original_review,
            appeal=appeal,
            model=secondary_reviewer_model or self.SECONDARY_REVIEWER_MODEL,
        )

        # 5. 比较并做出决策
        decision_result = await self._make_appeal_decision(
            appeal=appeal,
            original_review=original_review,
            secondary_result=secondary_result,
        )

        # 6. 更新申诉状态
        final_status = self._map_decision_to_status(decision_result.decision)
        await self._history_service.update_appeal_status(
            appeal_id=appeal_id,
            status=final_status,
            resolution=decision_result.explanation,
            resolved_by=decision_result.reviewed_by,
            secondary_review_id=secondary_result.get("review_id"),
            secondary_decision=secondary_result.get("decision"),
            secondary_score=secondary_result.get("score"),
        )

        logger.info(
            f"[AppealService] Appeal {appeal_id} resolved: "
            f"decision={decision_result.decision.value}"
        )

        return decision_result

    async def _execute_secondary_review(
        self,
        original_review,
        appeal: AppealEntry,
        model: str,
    ) -> dict[str, Any]:
        """
        执行二次审查

        使用不同的模型重新审查内容
        """
        try:
            from app.agents.reviewer_agent import ReviewerAgent

            content, user_query = await self._get_review_content(original_review)
            if not content:
                raise ValueError("Original content not available for secondary review")

            reviewer_llm = get_llm_service_for_task(TaskType.REVIEW)
            if model:
                reviewer_llm.chat_model = model
                reviewer_llm.reason_model = model

            reviewer = ReviewerAgent(reviewer_llm=reviewer_llm)
            review_result = await reviewer.review_llm_response(
                user_query=user_query or "",
                llm_response=content,
                context={
                    "appeal_id": appeal.appeal_id,
                    "review_id": appeal.review_id,
                    "user_id": appeal.user_id,
                    "timestamp": _utcnow().isoformat(),
                },
            )

            return {
                "review_id": review_result.review_id,
                "model": reviewer.reviewer_model,
                "score": review_result.overall_score,
                "decision": review_result.decision,
                "issues": [i.to_dict() for i in review_result.issues],
                "executed_at": _utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"[AppealService] Secondary review failed: {e}")
            return {
                "review_id": None,
                "model": model,
                "score": None,
                "decision": None,
                "error": str(e),
            }

    async def _get_review_content(self, original_review) -> tuple[str | None, str | None]:
        if getattr(original_review, "content_snapshot", None):
            return original_review.content_snapshot, getattr(original_review, "user_query", None)

        if original_review.target_type != "llm_response":
            return None, getattr(original_review, "user_query", None)

        target_id = original_review.target_id
        if not target_id:
            return None, getattr(original_review, "user_query", None)

        try:
            message_uuid = uuid.UUID(str(target_id))
            result = await self._db.execute(
                select(ChatMessage).where(ChatMessage.id == message_uuid)
            )
            msg = result.scalar_one_or_none()
            if msg:
                return msg.content, getattr(original_review, "user_query", None)
        except ValueError:
            pass

        result = await self._db.execute(
            select(ChatMessage).where(ChatMessage.message_id == str(target_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            return msg.content, getattr(original_review, "user_query", None)

        return None, getattr(original_review, "user_query", None)

    async def _make_appeal_decision(
        self,
        appeal: AppealEntry,
        original_review,
        secondary_result: dict[str, Any],
    ) -> AppealDecisionResult:
        """
        根据一次和二次审查结果做出申诉决策
        """
        original_score = original_review.overall_score
        secondary_score = secondary_result.get("score")

        # 如果二次审查失败，升级到人工
        if secondary_score is None:
            return AppealDecisionResult(
                appeal_id=appeal.appeal_id,
                decision=AppealDecision.ESCALATED,
                explanation="二次审查执行失败，已升级到人工处理",
                confidence=0.0,
                reviewed_by="system",
            )

        score_diff = secondary_score - original_score

        # 自动仲裁规则
        if score_diff >= self.AUTO_APPROVE_SCORE_DIFF:
            # 二次审查分数明显更高，自动通过申诉
            return AppealDecisionResult(
                appeal_id=appeal.appeal_id,
                decision=AppealDecision.APPROVED,
                explanation=f"二次审查分数({secondary_score:.2f})显著高于一次审查({original_score:.2f})，申诉通过",
                secondary_review_score=secondary_score,
                confidence=0.9,
                reviewed_by="auto_arbitrator",
            )

        elif score_diff <= self.AUTO_REJECT_SCORE_DIFF:
            # 二次审查分数更低或相近，拒绝申诉
            return AppealDecisionResult(
                appeal_id=appeal.appeal_id,
                decision=AppealDecision.REJECTED,
                explanation=f"二次审查分数({secondary_score:.2f})未能支持申诉，维持原审查结果",
                secondary_review_score=secondary_score,
                confidence=0.85,
                reviewed_by="auto_arbitrator",
            )

        else:
            # 结果不明确，需要人工审查
            confidence = 0.5 + abs(score_diff) * 0.5
            if confidence < self.ESCALATION_CONFIDENCE_THRESHOLD:
                return AppealDecisionResult(
                    appeal_id=appeal.appeal_id,
                    decision=AppealDecision.ESCALATED,
                    explanation=f"一次({original_score:.2f})与二次({secondary_score:.2f})审查结果接近，需要人工裁决",
                    secondary_review_score=secondary_score,
                    confidence=confidence,
                    reviewed_by="system",
                )
            else:
                # 倾向于部分通过
                return AppealDecisionResult(
                    appeal_id=appeal.appeal_id,
                    decision=AppealDecision.PARTIALLY_APPROVED,
                    explanation=f"二次审查({secondary_score:.2f})略高于一次({original_score:.2f})，部分采纳申诉意见",
                    secondary_review_score=secondary_score,
                    confidence=confidence,
                    reviewed_by="auto_arbitrator",
                )

    def _map_decision_to_status(self, decision: AppealDecision) -> AppealStatus:
        """将申诉决策映射到状态"""
        mapping = {
            AppealDecision.APPROVED: AppealStatus.RESOLVED,
            AppealDecision.REJECTED: AppealStatus.REJECTED,
            AppealDecision.PARTIALLY_APPROVED: AppealStatus.RESOLVED,
            AppealDecision.ESCALATED: AppealStatus.ESCALATED,
        }
        return mapping.get(decision, AppealStatus.RESOLVED)

    async def get_appeal_status(self, appeal_id: str) -> dict[str, Any] | None:
        """
        获取申诉状态

        Args:
            appeal_id: 申诉ID

        Returns:
            申诉状态信息
        """
        appeal = await self._history_service.get_appeal_by_id(appeal_id)
        if not appeal:
            return None

        return {
            "appeal_id": appeal.appeal_id,
            "review_id": appeal.review_id,
            "status": appeal.status.value,
            "submitted_at": appeal.timestamp,
            "appeal_reason": appeal.appeal_reason,
            "resolution": appeal.resolution,
            "resolved_by": appeal.resolved_by,
            "resolved_at": appeal.resolved_at,
            "secondary_decision": appeal.secondary_decision,
            "secondary_score": appeal.secondary_score,
        }

    async def get_pending_appeals_count(self) -> int:
        """获取待处理申诉数量"""
        queue = await self._history_service.get_appeal_queue(
            status=AppealStatus.PENDING
        )
        return len(queue)

    async def get_appeal_statistics(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        获取申诉统计

        Args:
            days: 统计天数

        Returns:
            申诉统计数据
        """
        cutoff = _utcnow() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        all_appeals = await self._history_service.get_appeal_queue(status=None, limit=1000)

        # 筛选时间范围
        appeals = [a for a in all_appeals if a.timestamp >= cutoff_str]

        if not appeals:
            return {
                "total": 0,
                "by_status": {},
                "approval_rate": 0.0,
                "avg_resolution_time_hours": 0.0,
                "period_days": days,
            }

        # 按状态统计
        by_status = {}
        for a in appeals:
            s = a.status.value
            by_status[s] = by_status.get(s, 0) + 1

        # 计算通过率
        resolved = by_status.get(AppealStatus.RESOLVED.value, 0)
        rejected = by_status.get(AppealStatus.REJECTED.value, 0)
        total_decided = resolved + rejected
        approval_rate = resolved / total_decided if total_decided > 0 else 0.0

        # 计算平均解决时间
        resolution_times = []
        for a in appeals:
            if a.resolved_at:
                submitted = datetime.fromisoformat(a.timestamp)
                resolved = datetime.fromisoformat(a.resolved_at)
                diff = (resolved - submitted).total_seconds() / 3600
                resolution_times.append(diff)

        avg_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

        return {
            "total": len(appeals),
            "by_status": by_status,
            "approval_rate": approval_rate,
            "avg_resolution_time_hours": avg_time,
            "period_days": days,
        }


# ============================================
# 全局实例管理
# ============================================

_appeal_services: dict[int, AppealReviewService] = {}


def get_appeal_review_service(db_session: AsyncSession) -> AppealReviewService:
    """获取AppealReviewService实例"""
    session_id = id(db_session)
    if session_id not in _appeal_services:
        _appeal_services[session_id] = AppealReviewService(db_session)
    return _appeal_services[session_id]
