"""
Plan Review Service - Phase 1: User Confirmation Loop

Implements intelligent plan review with:
- Quick rule-based auto-approval for safe plans
- LLM-based deep review for complex plans
- User confirmation workflow for high-risk plans
"""
import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger

from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.services.llm_service import llm_service
from app.core.pending_actions import pending_actions_store


class ReviewDecision(Enum):
    """Plan review decision types"""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MODIFICATION = "needs_modification"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class ReviewCategory(Enum):
    """Review comment categories"""
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    ALIGNMENT = "alignment"
    QUALITY = "quality"
    SUGGESTION = "suggestion"


class SeverityLevel(Enum):
    """Comment severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewComment:
    """Individual review comment"""
    category: str
    severity: str
    message: str
    suggested_fix: Optional[str] = None
    affected_tool_calls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "affected_tool_calls": self.affected_tool_calls,
        }


@dataclass
class PlanReviewResult:
    """Result of plan review"""
    review_id: str
    plan_id: str
    decision: str
    confidence: float
    comments: List[ReviewComment]
    reviewed_at: str
    suggested_modifications: Optional[Dict[str, Any]] = None
    auto_approved: bool = False
    user_facing_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "plan_id": self.plan_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "comments": [c.to_dict() for c in self.comments],
            "reviewed_at": self.reviewed_at,
            "suggested_modifications": self.suggested_modifications,
            "auto_approved": self.auto_approved,
            "user_facing_reason": self.user_facing_reason,
        }


class PlanReviewService:
    """
    Service for reviewing executable plans before execution.

    Implements a two-tier review system:
    1. Quick rule-based checks for auto-approval
    2. LLM-based deep review for complex plans
    """

    # High-risk tools that always require confirmation
    HIGH_RISK_TOOLS = {
        "delete_task",
        "delete_focus",
        "batch_delete",
        "delete_knowledge",
        "reset_progress",
        "clear_history",
    }

    # Safe tool categories that can be auto-approved
    SAFE_TOOL_CATEGORIES = {
        "query",
        "search",
        "retrieve",
        "get",
        "list",
        "fetch",
        "read",
    }

    # Maximum confidence for auto-approval without review
    AUTO_APPROVE_CONFIDENCE_THRESHOLD = 0.85

    # Maximum number of tool calls for auto-approval
    AUTO_APPROVE_MAX_TOOLS = 5

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def set_redis(self, redis_client):
        """Configure Redis client"""
        self.redis = redis_client
        pending_actions_store.set_redis(redis_client)

    async def review_plan(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: Dict[str, Any],
    ) -> PlanReviewResult:
        """
        Review an executable plan before execution.

        Args:
            plan: The executable plan to review
            user_message: Original user message
            user_context: User context and preferences

        Returns:
            PlanReviewResult with decision and comments
        """
        review_id = str(uuid.uuid4())
        reviewed_at = datetime.utcnow().isoformat()

        # Step 1: Quick rule-based check
        rule_result = await self._quick_rule_check(plan)
        if rule_result:
            logger.info(f"Plan {plan.plan_id} auto-approved by rules: {rule_result}")
            return PlanReviewResult(
                review_id=review_id,
                plan_id=plan.plan_id,
                decision=ReviewDecision.APPROVED.value,
                confidence=1.0,
                comments=[],
                reviewed_at=reviewed_at,
                auto_approved=True,
                user_facing_reason=self._get_user_facing_reason(
                    decision=ReviewDecision.APPROVED.value,
                    auto_approved=True,
                    auto_approve_reason=rule_result,
                ),
            )

        # Step 2: LLM-based deep review
        logger.info(f"Plan {plan.plan_id} requires LLM review")
        llm_result = await self._llm_review(plan, user_message, user_context)

        decision = llm_result.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value)

        return PlanReviewResult(
            review_id=review_id,
            plan_id=plan.plan_id,
            decision=decision,
            confidence=llm_result.get("confidence", 0.5),
            comments=[
                ReviewComment(
                    category=c.get("category", ReviewCategory.SUGGESTION.value),
                    severity=c.get("severity", SeverityLevel.INFO.value),
                    message=c.get("message", ""),
                    suggested_fix=c.get("suggested_fix"),
                    affected_tool_calls=c.get("affected_tool_calls", []),
                )
                for c in llm_result.get("comments", [])
            ],
            reviewed_at=reviewed_at,
            suggested_modifications=llm_result.get("suggested_modifications"),
            auto_approved=False,
            user_facing_reason=self._get_user_facing_reason(
                decision=decision,
                auto_approved=False,
            ),
        )

    async def _quick_rule_check(self, plan: ExecutablePlan) -> Optional[str]:
        """
        Quick rule-based check for auto-approval.

        Returns:
            Reason string if auto-approved, None otherwise
        """
        # Check for high-risk tools
        for tool_call in plan.tool_calls:
            if tool_call.name in self.HIGH_RISK_TOOLS:
                logger.info(f"High-risk tool detected: {tool_call.name}")
                return None

        # Check plan confidence
        if plan.confidence < self.AUTO_APPROVE_CONFIDENCE_THRESHOLD:
            logger.info(f"Plan confidence {plan.confidence} below threshold")
            return None

        # Check number of tools
        if len(plan.tool_calls) > self.AUTO_APPROVE_MAX_TOOLS:
            logger.info(f"Too many tools: {len(plan.tool_calls)}")
            return None

        # Check if all tools are safe (read-only)
        all_safe = True
        for tool_call in plan.tool_calls:
            tool_lower = tool_call.name.lower()
            if not any(safe in tool_lower for safe in self.SAFE_TOOL_CATEGORIES):
                all_safe = False
                break

        if all_safe and plan.tool_calls:
            return "all_tools_are_read_only"

        # Check for risk flags
        if plan.risk_flags:
            logger.info(f"Risk flags present: {plan.risk_flags}")
            return None

        # High confidence, low complexity plan
        if plan.confidence >= 0.95 and len(plan.tool_calls) <= 2:
            return "high_confidence_simple_plan"

        return None

    async def _llm_review(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Perform LLM-based deep review of the plan.

        Args:
            plan: The executable plan
            user_message: Original user message
            user_context: User context

        Returns:
            Dictionary with decision, confidence, comments
        """
        # Build review prompt
        prompt = self._build_review_prompt(plan, user_message, user_context)

        try:
            # 使用 reason_json 方法获取 JSON 格式的推理结果
            messages = [
                {
                    "role": "system",
                    "content": self._get_review_system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
            result = await llm_service.reason_json(
                messages=messages,
                temperature=0.2,
            )

            # reason_json 已返回解析后的对象，无需再解析
            if not result or not isinstance(result, dict):
                raise ValueError(f"Invalid LLM response type: {type(result)}")

            # 验证 decision 字段
            decision = result.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value)
            valid_decisions = {d.value for d in ReviewDecision}
            if decision not in valid_decisions:
                result["decision"] = ReviewDecision.REQUIRES_CONFIRMATION.value

            return result

        except Exception as e:
            logger.error(f"LLM review failed: {e}")
            # Default to requiring confirmation on error
            return {
                "decision": ReviewDecision.REQUIRES_CONFIRMATION.value,
                "confidence": 0.0,
                "comments": [
                    {
                        "category": ReviewCategory.SAFETY.value,
                        "severity": SeverityLevel.WARNING.value,
                        "message": "Unable to verify plan safety. Please review before proceeding.",
                    }
                ],
            }

    def _get_review_system_prompt(self) -> str:
        """Get system prompt for plan review"""
        return """You are a Plan Review Agent for an AI learning assistant. Your job is to review executable plans before they are executed.

Review criteria:
1. **Safety**: Ensure no harmful or destructive actions
2. **Alignment**: Verify the plan aligns with the user's intent
3. **Completeness**: Check if the plan has all necessary steps
4. **Quality**: Assess if the approach is sound

Decision types:
- approved: Safe, aligned, complete - proceed with execution
- rejected: Unsafe, completely misaligned, or impossible - do not execute
- needs_modification: Mostly good but requires changes before execution
- requires_confirmation: Needs user approval before proceeding

Respond in JSON format:
{
  "decision": "approved|rejected|needs_modification|requires_confirmation",
  "confidence": 0.0-1.0,
  "comments": [
    {
      "category": "safety|completeness|alignment|quality|suggestion",
      "severity": "critical|warning|info",
      "message": "Description of the issue or suggestion",
      "suggested_fix": "Optional: how to fix the issue",
      "affected_tool_calls": ["tool_id_1", "tool_id_2"]
    }
  ],
  "suggested_modifications": {
    "tool_changes": {...},
    "additional_steps": [...]
  }
}"""

    def _build_review_prompt(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: Dict[str, Any],
    ) -> str:
        """Build prompt for LLM review"""
        tool_summary = []
        for tc in plan.tool_calls:
            tool_summary.append(f"- {tc.name}: {json.dumps(tc.params, ensure_ascii=False)}")

        return f"""Review the following executable plan:

**User Request:**
{user_message}

**Plan Summary:**
{plan.rationale}

**Confidence:** {plan.confidence}
**Risk Flags:** {plan.risk_flags if plan.risk_flags else "None"}

**Tool Calls ({len(plan.tool_calls)}):**
{chr(10).join(tool_summary)}

**User Context:**
- Focus Active: {user_context.get('active_focus_id', 'None')}
- Pending Tasks: {user_context.get('pending_tasks_count', 0)}

Please review this plan and provide your assessment."""

    async def store_review_result(
        self,
        review: PlanReviewResult,
        user_id: str,
    ) -> str:
        """
        Store review result in pending actions store.

        Args:
            review: The review result to store
            user_id: User ID for authorization

        Returns:
            Action ID for user feedback
        """
        action_id = await pending_actions_store.save(
            tool_name="__plan_review__",
            arguments={
                "review_id": review.review_id,
                "plan_id": review.plan_id,
                "decision": review.decision,
            },
            user_id=user_id,
            description=self._get_review_description(review),
            preview_data={
                "review_id": review.review_id,
                "plan_id": review.plan_id,
                "decision": review.decision,
                "confidence": review.confidence,
                "comments": [c.to_dict() for c in review.comments],
                "suggested_modifications": review.suggested_modifications,
            },
        )
        return action_id

    def _get_review_description(self, review: PlanReviewResult) -> str:
        """Get user-friendly description of review"""
        if review.user_facing_reason:
            return review.user_facing_reason
        return self._get_user_facing_reason(
            decision=review.decision,
            auto_approved=review.auto_approved,
        )

    def _get_user_facing_reason(
        self,
        decision: str,
        auto_approved: bool = False,
        auto_approve_reason: Optional[str] = None,
    ) -> str:
        """
        Get user-facing explanation for the review decision.

        Args:
            decision: The review decision
            auto_approved: Whether the plan was auto-approved
            auto_approve_reason: The reason for auto-approval (if applicable)

        Returns:
            User-facing explanation string
        """
        if decision == ReviewDecision.APPROVED.value:
            if auto_approved:
                reason = self._get_auto_approve_reason(auto_approve_reason)
                return f"✓ 计划已自动批准：{reason}"
            return "✓ 计划已通过审查：经LLM深度审查，计划安全且符合您的意图"
        elif decision == ReviewDecision.REJECTED.value:
            return "✗ 计划未通过：存在严重问题，请查看下方详细说明"
        elif decision == ReviewDecision.NEEDS_MODIFICATION.value:
            return "⚠ 计划需要修改：部分调整后即可执行"
        elif decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            return "🔍 请确认计划：需要您确认后再执行"
        return "计划审查完成"

    def _get_auto_approve_reason(self, reason_code: Optional[str]) -> str:
        """
        Get user-friendly explanation for auto-approval reason.

        Args:
            reason_code: The internal reason code for auto-approval

        Returns:
            User-facing explanation string
        """
        reason_map = {
            "all_tools_are_read_only": "所有操作均为只读查询，无数据修改风险",
            "high_confidence_simple_plan": "高置信度简单计划，执行路径清晰明确",
        }
        return reason_map.get(reason_code, "计划符合安全标准，已自动通过审查")

    async def handle_review_feedback(
        self,
        review_id: str,
        user_decision: str,
        user_id: str,
        db_session: Any,  # P1 Fix #10: Now required for feedback writing
        user_comment: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle user feedback on a plan review.

        P1 Fix #10: db_session is now required for feedback writing.

        Args:
            review_id: Review ID
            user_decision: User's decision (approve, reject, modify)
            user_id: User ID
            db_session: Database session for feedback writing (required)
            user_comment: Optional user comment
            modifications: Optional user-provided modifications

        Returns:
            Status dictionary
        """
        # Get the stored action/review
        action = await pending_actions_store.get(review_id, user_id)
        if not action:
            logger.warning(f"Review not found or expired: {review_id}")
            return {
                "status": "error",
                "message": "Review not found or expired",
            }

        preview_data = action.get("preview_data", {})
        plan_id = preview_data.get("plan_id")
        logger.info(
            f"User {user_decision} review {review_id} for plan {plan_id}"
        )

        # Fix #3: 追踪拒绝次数，检测连续两次拒绝
        if user_decision == "reject" and plan_id:
            rejection_count = await self.track_rejection_count(plan_id, user_id)
            logger.info(f"Plan {plan_id} rejection count: {rejection_count}")

            # 两次拒绝，触发信息收集（回到对话澄清需求）
            if rejection_count >= 2:
                logger.warning(
                    f"Plan {plan_id} rejected {rejection_count} times, "
                    "triggering information collection"
                )

                # 清理拒绝计数
                await self.reset_rejection_count(plan_id, user_id)

                # 触发信息收集（通过Redis pub/sub通知orchestrator）
                await self._trigger_information_collection(
                    plan_id=plan_id,
                    user_id=user_id,
                    feedback=user_comment or "用户连续两次否定方案"
                )

                # 清理存储的action
                await pending_actions_store.delete(review_id, user_id)

                return {
                    "status": "information_collection_triggered",
                    "message": "方案被连续否定，需要重新了解您的需求",
                    "rejection_count": rejection_count
                }

        # 用户接受方案，重置拒绝计数
        if user_decision == "approve" and plan_id:
            await self.reset_rejection_count(plan_id, user_id)

        # === Phase 4: 时机2: Write user decision to feedback_log ===
        if db_session and plan_id:
            try:
                from app.services.plan_feedback_service import get_plan_feedback_service
                from uuid import UUID

                feedback_service = get_plan_feedback_service(db_session, self.redis)

                # Try to update the existing review feedback entry first
                updated = await feedback_service.update_feedback_decision(
                    user_id=UUID(user_id),
                    plan_id=UUID(plan_id),
                    review_id=review_id,
                    user_decision=user_decision,
                    user_comment=user_comment,
                )

                if updated:
                    logger.info(f"User decision feedback updated for plan {plan_id}")
                else:
                    # No existing review entry found, append a new user_feedback entry
                    await feedback_service.append_user_feedback(
                        user_id=UUID(user_id),
                        plan_id=UUID(plan_id),
                        content=user_comment or f"User decision: {user_decision}",
                        decision=user_decision,
                        priority="high" if user_decision == "reject" else "normal",
                    )
                    logger.info(f"User decision feedback appended (new entry) for plan {plan_id}")
            except Exception as e:
                logger.warning(f"Failed to write user decision feedback: {e}")

        # Clean up the stored action
        await pending_actions_store.delete(review_id, user_id)

        return {
            "status": "success",
            "user_decision": user_decision,
            "review_id": review_id,
            "plan_id": plan_id,
            "message": f"Review {user_decision} by user",
        }

    async def get_stored_plan(self, plan_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a stored plan for execution after approval.

        Args:
            plan_id: Plan ID
            user_id: User ID

        Returns:
            Plan data or None
        """
        # This would integrate with a plan storage system
        # For now, plans are stored in orchestrator state
        logger.info(f"Retrieving stored plan {plan_id} for user {user_id}")
        return None

    async def resume_plan_after_approval(
        self, plan_id: str, user_id: str, db_session: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Resume plan execution after user approval.

        This method is called when a user approves a plan review.
        It updates the plan state to indicate it should proceed with execution.
        Also triggers automatic task generation for the approved plan.

        Args:
            plan_id: Plan ID to resume
            user_id: User who approved
            db_session: Optional database session for task generation

        Returns:
            Status dictionary
        """
        logger.info(f"Resuming plan {plan_id} after approval by user {user_id}")

        # Store the approval in pending_actions for the orchestrator to pick up
        action_id = await pending_actions_store.save(
            tool_name="__plan_approved__",
            arguments={
                "plan_id": plan_id,
                "user_id": user_id,
            },
            user_id=user_id,
            description=f"Plan {plan_id} approved by user",
            preview_data={
                "plan_id": plan_id,
                "user_id": user_id,
                "action": "resume",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Trigger asynchronous task generation
        asyncio.create_task(
            self._generate_tasks_after_approval(
                plan_id=plan_id,
                user_id=user_id,
                action_id=action_id
            )
        )

        return {
            "status": "success",
            "action_id": action_id,
            "message": "Plan approved and task generation initiated",
            "task_generation_initiated": True,
        }

    async def _generate_tasks_after_approval(
        self, plan_id: str, user_id: str, action_id: str
    ) -> None:
        """
        Background task: Generate tasks automatically after plan approval.

        This method runs asynchronously after a plan is approved,
        generating concrete tasks based on the plan details.

        Args:
            plan_id: The approved plan ID
            user_id: User who owns the plan
            action_id: The approval action ID for tracking
        """
        from uuid import UUID
        from sqlalchemy import select
        from app.database import get_db_session
        from app.services.plan_service import PlanService
        from app.models.plan import Plan, PlanType
        from app.models.task import Task
        from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
        from app.tools.schemas import GenerateTasksForPlanParams

        try:
            # Get a fresh database session
            async with get_db_session() as db:
                # Fetch plan details
                plan = await PlanService.get_by_id(db, UUID(plan_id))
                if not plan:
                    logger.warning(f"Plan {plan_id} not found for task generation")
                    return

                # Check if tasks already exist for this plan
                existing_tasks_result = await db.execute(
                    select(Task).where(Task.plan_id == UUID(plan_id))
                )
                existing_tasks = existing_tasks_result.scalars().all()
                if existing_tasks:
                    logger.info(f"Plan {plan_id} already has {len(existing_tasks)} tasks, skipping generation")
                    return

                # Get the task generation tool
                tool = dynamic_tool_registry.get_tool("generate_tasks_for_plan")
                if not tool:
                    logger.error("GenerateTasksForPlanTool not registered")
                    return

                # Infer difficulty from plan type
                difficulty = "hard" if plan.type == PlanType.SPRINT else "medium"

                # Calculate task count based on estimated hours
                total_hours = plan.total_estimated_hours or 10
                task_count = max(3, min(8, int(total_hours / 2)))

                # Determine topic from plan subject or name
                topic = plan.subject or plan.name or "General learning"

                logger.info(
                    f"Generating {task_count} tasks for plan {plan_id} "
                    f"(difficulty={difficulty}, topic={topic})"
                )

                # Execute the tool
                params = GenerateTasksForPlanParams(
                    plan_id=plan_id,
                    topic=topic,
                    difficulty=difficulty,
                    task_count=task_count
                )

                result = await tool.execute(
                    params=params,
                    user_id=user_id,
                    db_session=db,
                    tool_call_id=action_id
                )

                if result.success:
                    task_count_created = result.data.get("task_count", 0)
                    logger.info(
                        f"Successfully generated {task_count_created} tasks "
                        f"for plan {plan_id} (action_id={action_id})"
                    )
                else:
                    logger.error(
                        f"Task generation failed for plan {plan_id}: "
                        f"{result.error_message}"
                    )

        except Exception as e:
            logger.error(f"Error in _generate_tasks_after_approval: {e}", exc_info=True)

    async def notify_plan_rejected(
        self, plan_id: str, user_id: str, feedback: str
    ) -> Dict[str, Any]:
        """
        Handle plan rejection by user.

        This method is called when a user rejects a plan review.
        It stores the rejection feedback and notifies relevant systems.

        Args:
            plan_id: Plan ID that was rejected
            user_id: User who rejected
            feedback: User's feedback/reason for rejection

        Returns:
            Status dictionary
        """
        logger.info(
            f"Plan {plan_id} rejected by user {user_id}. Feedback: {feedback[:100]}..."
        )

        # Store rejection for analytics and learning
        action_id = await pending_actions_store.save(
            tool_name="__plan_rejected__",
            arguments={
                "plan_id": plan_id,
                "user_id": user_id,
                "feedback": feedback,
            },
            user_id=user_id,
            description=f"Plan {plan_id} rejected",
            preview_data={
                "plan_id": plan_id,
                "user_id": user_id,
                "action": "rejected",
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        return {
            "status": "success",
            "action_id": action_id,
            "message": "Plan rejection recorded",
        }

    async def trigger_replanning(
        self, plan_id: str, user_id: str, feedback: str
    ) -> Dict[str, Any]:
        """
        Trigger replanning based on user feedback.

        This method is called when a user requests modifications to a plan.
        It stores the modification request and creates a new planning task.

        Args:
            plan_id: Original plan ID
            user_id: User requesting modifications
            feedback: User's modification request

        Returns:
            Status dictionary with new plan ID if created
        """
        logger.info(
            f"Triggering replan for {plan_id} by user {user_id}. Feedback: {feedback[:100]}..."
        )

        # Generate a new plan ID for the modified plan
        new_plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        # Store replanning request for the orchestrator to pick up
        action_id = await pending_actions_store.save(
            tool_name="__plan_replan__",
            arguments={
                "original_plan_id": plan_id,
                "new_plan_id": new_plan_id,
                "user_id": user_id,
                "feedback": feedback,
            },
            user_id=user_id,
            description=f"Plan modification requested: {feedback[:100]}",
            preview_data={
                "original_plan_id": plan_id,
                "new_plan_id": new_plan_id,
                "user_id": user_id,
                "action": "replan",
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # P1 Fix #9: Notify orchestrator via Redis pub/sub
        if self.redis:
            notification = {
                "type": "replan_requested",
                "original_plan_id": plan_id,
                "new_plan_id": new_plan_id,
                "user_id": user_id,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            }
            try:
                await self.redis.publish(f"user:{user_id}:replan", json.dumps(notification))
                logger.info(f"Published replan notification for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to publish replan notification: {e}")

        # Auto-execute replanning in background to avoid queued actions
        asyncio.create_task(
            self._execute_replan_action(
                action_id=action_id,
                user_id=user_id,
                original_plan_id=plan_id,
                new_plan_id=new_plan_id,
                feedback=feedback,
            )
        )

        return {
            "status": "success",
            "action_id": action_id,
            "new_plan_id": new_plan_id,
            "message": "Replanning request accepted (auto execution started)",
        }

    async def _execute_replan_action(
        self,
        action_id: str,
        user_id: str,
        original_plan_id: str,
        new_plan_id: str,
        feedback: str,
    ) -> None:
        """
        Execute replanning asynchronously and either auto-run or queue review.
        """
        from uuid import UUID
        from app.database import get_db_session
        from app.core.context_pack import ContextPackBuilder
        from app.orchestration.lang_graph_planner import LangGraphPlanner
        from app.orchestration.state_snapshot import StateSnapshotManager
        from app.core.sse import sse_manager
        from app.orchestration.executor import ToolExecutor

        try:
            async with get_db_session() as db:
                session_id = f"replan:{action_id}"
                snapshot_manager = StateSnapshotManager(self.redis)
                snapshot = await snapshot_manager.create_snapshot(
                    user_id=user_id,
                    session_id=session_id,
                    db_session=db,
                )

                replan_message = (
                    "用户请求修改当前计划。"
                    f"原计划ID: {original_plan_id}。"
                    f"反馈: {feedback}"
                )

                planner = LangGraphPlanner(self.redis)
                executable_plan = await planner.plan(
                    message=replan_message,
                    snapshot=snapshot,
                    user_id=user_id,
                    session_id=session_id,
                )

                user_context = {}
                try:
                    context_builder = ContextPackBuilder(db, redis=self.redis)
                    context_pack = await context_builder.build(
                        user_id=UUID(user_id),
                        intent="chat",
                    )
                    user_context = context_pack.to_prompt_context()
                except Exception as e:
                    logger.warning(f"Failed to build context pack for replan: {e}")

                review_result = await self.review_plan(
                    plan=executable_plan,
                    user_message=replan_message,
                    user_context=user_context,
                )

                if review_result.decision == ReviewDecision.APPROVED.value and review_result.auto_approved:
                    executor = ToolExecutor()
                    results = []
                    for tool_call in executable_plan.tool_calls:
                        result = await executor.execute_tool_call(
                            tool_name=tool_call.name,
                            arguments=tool_call.params or {},
                            user_id=user_id,
                            db_session=db,
                            tool_call_id=tool_call.id,
                            compensation_call=tool_call.compensation_call,
                        )
                        results.append(result)
                        if not result.success:
                            break
                    logger.info(
                        f"Auto-replan executed for user {user_id}, "
                        f"plan={executable_plan.plan_id}, "
                        f"tools={len(executable_plan.tool_calls)}"
                    )
                    await sse_manager.send_to_user(
                        user_id,
                        "plan_replan_completed",
                        {
                            "action_id": action_id,
                            "original_plan_id": original_plan_id,
                            "new_plan_id": new_plan_id,
                            "generated_plan_id": executable_plan.plan_id,
                            "auto_executed": True,
                            "tool_count": len(executable_plan.tool_calls),
                        },
                    )
                else:
                    review_action_id = await self.store_review_result(
                        review=review_result,
                        user_id=user_id,
                    )
                    logger.info(
                        f"Replan review queued: action_id={review_action_id}, "
                        f"plan={executable_plan.plan_id}"
                    )
                    await sse_manager.send_to_user(
                        user_id,
                        "plan_replan_review_required",
                        {
                            "action_id": action_id,
                            "review_action_id": review_action_id,
                            "review_id": review_result.review_id,
                            "original_plan_id": original_plan_id,
                            "new_plan_id": new_plan_id,
                            "generated_plan_id": executable_plan.plan_id,
                            "decision": review_result.decision,
                        },
                    )

                await pending_actions_store.delete(action_id, user_id)

        except Exception as e:
            logger.error(f"Failed to auto execute replan action {action_id}: {e}", exc_info=True)
            try:
                await sse_manager.send_to_user(
                    user_id,
                    "plan_replan_failed",
                    {
                        "action_id": action_id,
                        "original_plan_id": original_plan_id,
                        "new_plan_id": new_plan_id,
                        "error": str(e),
                    },
                )
            except Exception as notify_error:
                logger.warning(f"Failed to notify replan failure: {notify_error}")

    # Fix #3: 拒绝计数追踪和信息收集触发方法

    async def track_rejection_count(
        self,
        plan_id: str,
        user_id: str
    ) -> int:
        """
        追踪用户连续拒绝方案的次数

        Args:
            plan_id: 计划ID
            user_id: 用户ID

        Returns:
            当前连续拒绝次数
        """
        key = f"plan_rejection_count:{plan_id}:{user_id}"

        try:
            count = await self.redis.incr(key)
            await self.redis.expire(key, 3600)  # 1小时过期
            return count
        except Exception as e:
            logger.warning(f"Failed to track rejection count: {e}")
            return 1

    async def reset_rejection_count(
        self,
        plan_id: str,
        user_id: str
    ):
        """
        重置拒绝计数（用户接受方案或触发信息收集后调用）

        Args:
            plan_id: 计划ID
            user_id: 用户ID
        """
        key = f"plan_rejection_count:{plan_id}:{user_id}"
        try:
            await self.redis.delete(key)
            logger.info(f"Reset rejection count for plan {plan_id}")
        except Exception as e:
            logger.warning(f"Failed to reset rejection count: {e}")

    async def _trigger_information_collection(
        self,
        plan_id: str,
        user_id: str,
        feedback: str
    ):
        """
        触发信息收集（通过Redis pub/sub通知orchestrator）

        Args:
            plan_id: 计划ID
            user_id: 用户ID
            feedback: 用户反馈
        """
        if self.redis:
            notification = {
                "type": "information_collection_required",
                "plan_id": plan_id,
                "user_id": user_id,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            }
            try:
                await self.redis.publish(
                    f"user:{user_id}:info_collection",
                    json.dumps(notification)
                )
                logger.info(f"Published information collection trigger for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to publish information collection trigger: {e}")


# Global singleton
plan_review_service = PlanReviewService()
