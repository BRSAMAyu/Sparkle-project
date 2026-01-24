"""
PlanFeedbackService - 计划反馈管理服务 (Phase 4)

Responsibilities:
1. 将审查意见写入 PlanState.feedback_log
2. 将用户反馈写入 PlanState.feedback_log
3. 更新反馈的 priority 和 decision
4. 获取待处理的反馈列表

This service provides the feedback loop for the plan review system.
"""
from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.schemas import PlanFeedback
from app.services.plan_state_service import PlanStateService

if TYPE_CHECKING:
    from app.orchestration.plan_review_service import PlanReviewResult


# Cache configuration
PLAN_STATE_CACHE_TTL = 3600  # 1 hour
PLAN_STATE_CACHE_PREFIX = "state:plan:"


class PlanFeedbackService:
    """计划反馈管理服务 (Phase 4)

    管理计划反馈的写入和查询，支持：
    - 审查意见写入
    - 用户反馈写入
    - 待处理反馈查询
    """

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self._plan_state_service = PlanStateService(db, redis)

    async def append_review_feedback(
        self,
        user_id: UUID,
        plan_id: UUID,
        review_result: PlanReviewResult,
        user_decision: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        将审查意见写入 feedback_log

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID
            review_result: 审查结果
            user_decision: 用户决策 (approve/reject/modify)

        Returns:
            更新后的 PlanState
        """
        # 创建反馈条目
        feedback = PlanFeedback.from_review_result(review_result)

        # 如果用户有决策，更新反馈
        if user_decision:
            feedback.decision = user_decision
            if user_decision == "reject":
                feedback.priority = "high"
                feedback.feedback_type = "plan_disagree"
            feedback.source = "user"

        # 转换为 feedback_log 格式 (keep review comments/details)
        feedback_entry = feedback.to_dict()
        feedback_entry["applied_adjustment"] = {
            "decision": feedback.decision,
            "priority": feedback.priority,
            "review_id": feedback.review_id,
            "review_decision": feedback.review_decision,
        }

        # 写入 PlanState (append full entry)
        state = await self._plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"feedback_log": feedback_entry},
            bump_version=True,
        )

        logger.info(
            f"Review feedback appended: plan_id={plan_id}, "
            f"review_id={review_result.review_id}, decision={feedback.decision}"
        )

        return state.to_dict() if state else None

    async def append_user_feedback(
        self,
        user_id: UUID,
        plan_id: UUID,
        content: str,
        decision: str = "supplement",
        priority: str = "normal",
        related_task_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        将用户反馈写入 feedback_log

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID
            content: 反馈内容
            decision: 决策类型
            priority: 优先级
            related_task_id: 关联任务 ID

        Returns:
            更新后的 PlanState
        """
        feedback = PlanFeedback(
            feedback_type="user_feedback",
            content=content,
            decision=decision,
            priority=priority,
            source="user",
            related_plan_id=str(plan_id),
            related_task_id=str(related_task_id) if related_task_id else None,
        )

        # 写入 PlanState
        state = await self._plan_state_service.append_feedback(
            user_id=user_id,
            plan_id=plan_id,
            feedback_type=feedback.feedback_type,
            content=feedback.content,
            task_id=related_task_id,
            applied_adjustment={
                "decision": feedback.decision,
                "priority": feedback.priority,
            }
        )

        logger.info(
            f"User feedback appended: plan_id={plan_id}, decision={decision}"
        )

        return state.to_dict() if state else None

    async def track_rejection(
        self,
        user_id: UUID,
        plan_id: UUID,
        is_rejection: bool,
    ) -> tuple[int, bool]:
        """
        P0-2: Track consecutive rejections. Returns (count, should_rollback).

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID
            is_rejection: True if this is a rejection, False to reset counter

        Returns:
            tuple[int, bool]: (current count, should trigger rollback)
        """
        state = await self._plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            return (0, False)

        # Calculate new count: increment on rejection, reset on approval
        current_count = state.consecutive_rejection_count or 0
        new_count = current_count + 1 if is_rejection else 0

        # Update the count
        await self._plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"consecutive_rejection_count": new_count},
            bump_version=False,  # Don't bump version for rejection tracking
        )

        # Check if rollback should be triggered (>= 2 consecutive rejections)
        should_rollback = new_count >= 2
        if should_rollback:
            # Set rollback flag in constraints
            await self._plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"constraints": {"require_phase_rollback": True}},
                bump_version=False,
            )
            logger.info(
                f"Phase rollback triggered: plan_id={plan_id}, rejection_count={new_count}"
            )

        return (new_count, should_rollback)

    async def get_pending_feedback(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        获取待处理的反馈（高优先级或需要补充的）

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID

        Returns:
            待处理反馈列表
        """
        state = await self._plan_state_service.get_plan_state(user_id, plan_id)
        if not state or not state.feedback_log:
            return []

        pending = []
        for entry in state.feedback_log:
            adj = entry.get("applied_adjustment", {})
            if adj.get("priority") == "high" or adj.get("decision") in ["reject", "supplement"]:
                pending.append(entry)

        return pending

    async def update_feedback_decision(
        self,
        user_id: UUID,
        plan_id: UUID,
        review_id: str,
        user_decision: str,
        user_comment: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        更新现有反馈的决策（用户确认后调用）

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID
            review_id: 审查 ID
            user_decision: 用户决策 (approve/reject/modify)
            user_comment: 用户评论

        Returns:
            更新后的 PlanState
        """
        state = await self._plan_state_service.get_plan_state(user_id, plan_id)
        if not state or not state.feedback_log:
            logger.warning(f"No feedback_log found for plan_id={plan_id}")
            return None

        # 找到对应的 review 反馈并更新
        updated = False
        for entry in reversed(state.feedback_log):
            if entry.get("applied_adjustment", {}).get("review_id") == review_id:
                entry["applied_adjustment"]["decision"] = user_decision
                if user_decision == "reject":
                    entry["applied_adjustment"]["priority"] = "high"
                entry["source"] = "user"
                entry["decision"] = user_decision
                if user_decision == "reject":
                    entry["priority"] = "high"
                if user_comment:
                    entry["user_comment"] = user_comment
                updated = True
                break

        if updated:
            # 保存更新 (use service to bump version and cache)
            state = await self._plan_state_service.replace_feedback_log(
                user_id=user_id,
                plan_id=plan_id,
                feedback_log=state.feedback_log,
                bump_version=True,
            )

            logger.info(
                f"Updated feedback decision: plan_id={plan_id}, review_id={review_id}, decision={user_decision}"
            )

            return state.to_dict() if state else None

        return None

    async def _set_cache(self, state) -> None:
        """Set plan state in cache."""
        if not self.redis:
            return

        import json

        cache_key = f"{PLAN_STATE_CACHE_PREFIX}{state.plan_id}"
        try:
            data = json.dumps(state.to_dict(), ensure_ascii=False, default=str)
            await self.redis.setex(cache_key, PLAN_STATE_CACHE_TTL, data)
            logger.debug(
                f"Set plan state cache: plan_id={state.plan_id}, ttl={PLAN_STATE_CACHE_TTL}"
            )
        except Exception as e:
            logger.warning(f"Failed to set plan state cache: {e}")


# Global singleton
_plan_feedback_service = None


def get_plan_feedback_service(db: AsyncSession, redis=None) -> PlanFeedbackService:
    """获取 PlanFeedbackService 实例"""
    global _plan_feedback_service
    if _plan_feedback_service is None or _plan_feedback_service.db != db:
        _plan_feedback_service = PlanFeedbackService(db, redis)
    return _plan_feedback_service
