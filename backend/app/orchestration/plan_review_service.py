"""
Plan Review Service - Phase 1: User Confirmation Loop

Implements intelligent plan review with:
- Quick rule-based auto-approval for safe plans
- LLM-based deep review for complex plans
- User confirmation workflow for high-risk plans
"""
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
            )

        # Step 2: LLM-based deep review
        logger.info(f"Plan {plan.plan_id} requires LLM review")
        llm_result = await self._llm_review(plan, user_message, user_context)

        return PlanReviewResult(
            review_id=review_id,
            plan_id=plan.plan_id,
            decision=llm_result.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value),
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
            response = await llm_service.get_completion(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_review_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            # Parse LLM response
            result = self._parse_review_response(response)
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

    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM review response"""
        try:
            data = json.loads(response)

            # Validate decision
            decision = data.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value)
            valid_decisions = {d.value for d in ReviewDecision}
            if decision not in valid_decisions:
                decision = ReviewDecision.REQUIRES_CONFIRMATION.value

            return {
                "decision": decision,
                "confidence": float(data.get("confidence", 0.5)),
                "comments": data.get("comments", []),
                "suggested_modifications": data.get("suggested_modifications"),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review response: {e}")
            return {
                "decision": ReviewDecision.REQUIRES_CONFIRMATION.value,
                "confidence": 0.0,
                "comments": [
                    {
                        "category": ReviewCategory.QUALITY.value,
                        "severity": SeverityLevel.WARNING.value,
                        "message": "Review response could not be parsed. Manual review required.",
                    }
                ],
            }

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
        if review.decision == ReviewDecision.REJECTED.value:
            return "Plan rejected. Please review the issues and try again."
        elif review.decision == ReviewDecision.NEEDS_MODIFICATION.value:
            return "Plan requires modifications before execution."
        elif review.decision == ReviewDecision.REQUIRES_CONFIRMATION.value:
            return "Please review and confirm this plan before execution."
        return "Plan review complete."

    async def handle_review_feedback(
        self,
        review_id: str,
        user_decision: str,
        user_id: str,
        user_comment: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle user feedback on a plan review.

        Args:
            review_id: Review ID
            user_decision: User's decision (approve, reject, modify)
            user_id: User ID
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
        logger.info(
            f"User {user_decision} review {review_id} for plan {preview_data.get('plan_id')}"
        )

        # Clean up the stored action
        await pending_actions_store.delete(review_id, user_id)

        return {
            "status": "success",
            "user_decision": user_decision,
            "review_id": review_id,
            "plan_id": preview_data.get("plan_id"),
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


# Global singleton
plan_review_service = PlanReviewService()
