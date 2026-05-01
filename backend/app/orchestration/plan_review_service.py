"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Plan Review Service - Phase 1: User Confirmation Loop

Implements intelligent plan review with:
- Quick rule-based auto-approval for safe plans
- LLM-based deep review for complex plans
- User confirmation workflow for high-risk plans
"""


from __future__ import annotations
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import UUID

from loguru import logger

from app.config import settings
from app.core.business_metrics import (
    PHASE4_OPERATION_DURATION_SECONDS,
    PLAN_REASONING_GENERATED_TOTAL,
    PLAN_REASONING_SOURCE_TOTAL,
)
from app.core.event_bus import event_bus
from app.core.pending_actions import pending_actions_store
from app.event_publishers.srl_events import publish_srl_event
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry
from app.orchestration.plan_quality_gate import PlanQualityGate
from app.orchestration.schemas import ExecutablePlan
from app.services.llm_service import llm_service
from app.services.self_evolution_service import StrategyCalibrationService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
    suggested_fix: str | None = None
    affected_tool_calls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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
    comments: list[ReviewComment]
    reviewed_at: str
    suggested_modifications: dict[str, Any] | None = None
    auto_approved: bool = False
    user_facing_reason: str | None = None
    reasoning_summary: str | None = None
    reasoning_details: list[dict[str, str]] | None = None
    reasoning_source: str | None = None
    persona_strategy_mapping: list[dict[str, Any]] | None = None
    alignment_score: float | None = None
    alignment_summary: str | None = None
    review_feedback_entry: dict[str, Any] | None = None
    quality_report: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
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
            "reasoning_summary": self.reasoning_summary,
            "reasoning_details": self.reasoning_details,
            "reasoning_source": self.reasoning_source,
            "persona_strategy_mapping": self.persona_strategy_mapping,
            "alignment_score": self.alignment_score,
            "alignment_summary": self.alignment_summary,
            "review_feedback_entry": self.review_feedback_entry,
            "quality_report": self.quality_report,
        }


class PlanReviewService:
    """
    Service for reviewing executable plans before execution.

    Implements a two-tier review system:
    1. Quick rule-based checks for auto-approval
    2. LLM-based deep review for complex plans

    Includes retry mechanism and graceful degradation when LLM review fails.
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

    # Maximum retry attempts for LLM review
    MAX_LLM_REVIEW_RETRIES = 2

    # Retry delay in seconds
    RETRY_DELAY = 0.5

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.quality_gate = PlanQualityGate()

    def set_redis(self, redis_client):
        """Configure Redis client"""
        self.redis = redis_client
        pending_actions_store.set_redis(redis_client)

    async def _get_langgraph_breaker(self) -> CircuitBreaker:
        breaker = circuit_breaker_registry.get("langgraph_planner")
        if breaker is not None:
            return breaker

        breaker = CircuitBreaker(
            name="langgraph_planner",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout_ms=60000,
                failure_rate_threshold=0.5,
            ),
            redis_client=self.redis,
        )
        await breaker.initialize()
        circuit_breaker_registry.register(breaker)
        return breaker

    async def review_plan(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: dict[str, Any],
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
        reviewed_at = _utcnow().isoformat()
        mode_strategy = self._extract_mode_strategy(user_context)
        quality_report = self.quality_gate.evaluate(
            plan=plan,
            user_message=user_message,
            user_context=user_context,
        )
        quality_payload = quality_report.to_dict()

        # Step 1: Quick rule-based check
        rule_result = await self._quick_rule_check(plan, user_context)
        if rule_result:
            if quality_report.decision != "approve":
                gated_decision = self._map_quality_gate_decision(quality_report.decision)
                gated_comments = self._build_quality_gate_comments(quality_report)
                return PlanReviewResult(
                    review_id=review_id,
                    plan_id=plan.plan_id,
                    decision=gated_decision,
                    confidence=min(plan.confidence, quality_report.overall_score),
                    comments=gated_comments,
                    reviewed_at=reviewed_at,
                    auto_approved=False,
                    user_facing_reason=self._get_quality_gate_reason(quality_report.decision),
                    quality_report=quality_payload,
                )
            logger.info(f"Plan {plan.plan_id} auto-approved by rules: {rule_result}")
            reasoning_summary, reasoning_details = self._build_reasoning_payload(
                plan=plan,
                user_context=user_context,
                decision=ReviewDecision.APPROVED.value,
                auto_approved=True,
                auto_approve_reason=rule_result,
            )
            calibration_service = StrategyCalibrationService(redis=self.redis)
            user_uuid = self._extract_user_id(user_context)
            persona_strategy_mapping = self._build_persona_strategy_mapping(user_context)
            persona_strategy_mapping, _ = await calibration_service.apply_rule_calibration(
                user_id=user_uuid,
                mappings=persona_strategy_mapping,
            )
            alignment_score, alignment_summary, matched_rule_keys = self._score_plan_alignment(
                plan=plan,
                mappings=persona_strategy_mapping,
            )
            if user_uuid:
                await calibration_service.record_mapping_alignment(
                    user_id=user_uuid,
                    mappings=persona_strategy_mapping,
                    matched_rule_keys=matched_rule_keys,
                )
                await calibration_service.record_alignment_score(user_id=user_uuid, score=alignment_score)
            comments: list[ReviewComment] = []
            if alignment_score is not None and alignment_score < 0.55:
                severity = SeverityLevel.WARNING.value
                decision = ReviewDecision.APPROVED.value
                if mode_strategy.get("require_alignment_check"):
                    severity = SeverityLevel.CRITICAL.value
                    decision = ReviewDecision.NEEDS_MODIFICATION.value
                comments.append(
                    ReviewComment(
                        category=ReviewCategory.ALIGNMENT.value,
                        severity=severity,
                        message=alignment_summary or "当前计划和你的近期执行画像存在一定偏差。",
                        suggested_fix="建议降低难度、缩短单次负载或把任务拆细后再执行。",
                    )
                )
            review_feedback_entry = self.build_review_feedback_entry(
                review_id=review_id,
                decision=(
                    decision
                    if alignment_score is not None
                    and alignment_score < 0.55
                    and mode_strategy.get("require_alignment_check")
                    else ReviewDecision.APPROVED.value
                ),
                comments=comments,
                alignment_score=alignment_score,
                alignment_summary=alignment_summary,
                mode_strategy=mode_strategy,
                quality_report=quality_payload,
            )
            if reasoning_summary:
                PLAN_REASONING_SOURCE_TOTAL.labels(source="rules_only").inc()
            final_decision = (
                decision
                if alignment_score is not None
                and alignment_score < 0.55
                and mode_strategy.get("require_alignment_check")
                else ReviewDecision.APPROVED.value
            )
            return PlanReviewResult(
                review_id=review_id,
                plan_id=plan.plan_id,
                decision=final_decision,
                confidence=1.0,
                comments=comments,
                reviewed_at=reviewed_at,
                auto_approved=final_decision == ReviewDecision.APPROVED.value,
                user_facing_reason=self._get_user_facing_reason(
                    decision=final_decision,
                    auto_approved=final_decision == ReviewDecision.APPROVED.value,
                    auto_approve_reason=rule_result,
                ),
                reasoning_summary=reasoning_summary,
                reasoning_details=reasoning_details,
                reasoning_source="rules_only",
                persona_strategy_mapping=persona_strategy_mapping,
                alignment_score=alignment_score,
                alignment_summary=alignment_summary,
                review_feedback_entry=review_feedback_entry,
                quality_report=quality_payload,
            )

        # Step 2: LLM-based deep review
        logger.info(f"Plan {plan.plan_id} requires LLM review")
        llm_result = await self._llm_review(plan, user_message, user_context)

        decision = llm_result.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value)
        reasoning_source = "llm_fallback" if llm_result.get("fallback_used") else "llm_review"
        calibration_service = StrategyCalibrationService(redis=self.redis)
        user_uuid = self._extract_user_id(user_context)
        persona_strategy_mapping = self._build_persona_strategy_mapping(user_context)
        persona_strategy_mapping, _ = await calibration_service.apply_rule_calibration(
            user_id=user_uuid,
            mappings=persona_strategy_mapping,
        )
        alignment_score, alignment_summary, matched_rule_keys = self._score_plan_alignment(
            plan=plan,
            mappings=persona_strategy_mapping,
        )
        if user_uuid:
            await calibration_service.record_mapping_alignment(
                user_id=user_uuid,
                mappings=persona_strategy_mapping,
                matched_rule_keys=matched_rule_keys,
            )
            await calibration_service.record_alignment_score(user_id=user_uuid, score=alignment_score)
        comments = [
            ReviewComment(
                category=c.get("category", ReviewCategory.SUGGESTION.value),
                severity=c.get("severity", SeverityLevel.INFO.value),
                message=c.get("message", ""),
                suggested_fix=c.get("suggested_fix"),
                affected_tool_calls=c.get("affected_tool_calls", []),
            )
            for c in llm_result.get("comments", [])
        ]
        if decision == ReviewDecision.APPROVED.value and alignment_score is not None and alignment_score < 0.55:
            severity = SeverityLevel.WARNING.value
            if mode_strategy.get("require_alignment_check"):
                decision = ReviewDecision.NEEDS_MODIFICATION.value
                severity = SeverityLevel.CRITICAL.value
            comments.append(
                ReviewComment(
                    category=ReviewCategory.ALIGNMENT.value,
                    severity=severity,
                    message=alignment_summary or "当前计划和你的近期执行画像存在一定偏差。",
                    suggested_fix="建议把任务颗粒度再拆细一点，或先降低本轮负载后再推进。",
                )
            )
        if quality_report.decision != "approve":
            if decision == ReviewDecision.APPROVED.value:
                decision = self._map_quality_gate_decision(quality_report.decision)
            comments.extend(self._build_quality_gate_comments(quality_report))
        reasoning_summary, reasoning_details = self._build_reasoning_payload(
            plan=plan,
            user_context=user_context,
            decision=decision,
            auto_approved=False,
        )

        review_feedback_entry = self.build_review_feedback_entry(
            review_id=review_id,
            decision=decision,
            comments=comments,
            alignment_score=alignment_score,
            alignment_summary=alignment_summary,
            mode_strategy=mode_strategy,
            quality_report=quality_payload,
        )
        if reasoning_summary:
            PLAN_REASONING_SOURCE_TOTAL.labels(source=reasoning_source).inc()
        return PlanReviewResult(
            review_id=review_id,
            plan_id=plan.plan_id,
            decision=decision,
            confidence=llm_result.get("confidence", 0.5),
            comments=comments,
            reviewed_at=reviewed_at,
            suggested_modifications=llm_result.get("suggested_modifications"),
            auto_approved=False,
            user_facing_reason=self._get_user_facing_reason(
                decision=decision,
                auto_approved=False,
            ),
            reasoning_summary=reasoning_summary,
            reasoning_details=reasoning_details,
            reasoning_source=reasoning_source,
            persona_strategy_mapping=persona_strategy_mapping,
            alignment_score=alignment_score,
            alignment_summary=alignment_summary,
            review_feedback_entry=review_feedback_entry,
            quality_report=quality_payload,
        )

    async def _quick_rule_check(self, plan: ExecutablePlan, user_context: dict[str, Any]) -> str | None:
        """
        Quick rule-based check for auto-approval.

        P0 Fix #1: Added feasibility validation and overcommitment detection.

        Args:
            plan: The executable plan to check
            user_context: User context including constraints and current commitments

        Returns:
            Reason string if auto-approved, None otherwise
        """
        mode_strategy = self._extract_mode_strategy(user_context)
        review_strictness = max(float(mode_strategy.get("review_strictness", 1.0) or 1.0), 0.5)
        auto_approve_confidence_threshold = min(
            0.99,
            self.AUTO_APPROVE_CONFIDENCE_THRESHOLD + max(review_strictness - 1.0, 0.0) * 0.08,
        )
        auto_approve_max_tools = max(2, int(round(self.AUTO_APPROVE_MAX_TOOLS / review_strictness)))

        # === P0 Fix #2: Check for overcommitment (user already has too many plans) ===
        active_plan_count = user_context.get("current_plan_count", 0)
        if active_plan_count >= 3:
            # Check if this plan creates another big plan
            for tc in plan.tool_calls:
                if tc.name in ["create_sprint_plan", "create_learning_plan", "create_plan"]:
                    logger.warning(
                        f"User already has {active_plan_count} active plans, "
                        f"rejecting auto-approval for new plan creation"
                    )
                    # Don't auto-approve, let LLM review handle the warning
                    return None

        # Check for high-risk tools
        for tool_call in plan.tool_calls:
            if tool_call.name in self.HIGH_RISK_TOOLS:
                logger.info(f"High-risk tool detected: {tool_call.name}")
                return None

        # Check plan confidence
        if plan.confidence < auto_approve_confidence_threshold:
            logger.info(f"Plan confidence {plan.confidence} below threshold")
            return None

        # Check number of tools
        if len(plan.tool_calls) > auto_approve_max_tools:
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

        # === P0 Fix #1: Validate feasibility before auto-approving high confidence plans ===
        if plan.confidence >= max(0.95, auto_approve_confidence_threshold + 0.05) and len(plan.tool_calls) <= 2:
            # Add feasibility validation for high confidence plans
            feasibility_ok = await self._validate_feasibility(plan, user_context)
            if not feasibility_ok:
                logger.info(
                    f"Plan rejected by feasibility check despite high confidence "
                    f"(confidence={plan.confidence}, tool_calls={len(plan.tool_calls)})"
                )
                return None  # Don't auto-approve, will go to LLM review with feasibility concerns

            return "high_confidence_simple_plan"

        return None

    @staticmethod
    def _extract_mode_strategy(user_context: dict[str, Any]) -> dict[str, Any]:
        strategy = (user_context or {}).get("mode_strategy")
        return strategy if isinstance(strategy, dict) else {}

    def build_review_feedback_entry(
        self,
        *,
        review_id: str,
        decision: str,
        comments: list[ReviewComment],
        alignment_score: float | None,
        alignment_summary: str | None,
        mode_strategy: dict[str, Any] | None = None,
        quality_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        dominant = comments[0] if comments else None
        category = str(dominant.category if dominant else decision)
        message = str(dominant.message if dominant else alignment_summary or decision)
        bias_constraint = ""
        lowered = message.lower()
        if category == ReviewCategory.ALIGNMENT.value and alignment_score is not None and alignment_score < 0.55:
            if "难度" in message or "difficulty" in lowered:
                bias_constraint = "task_difficulty"
            elif "颗粒度" in message or "granularity" in lowered:
                bias_constraint = "task_granularity"
            elif "并行" in message or "concurrency" in lowered:
                bias_constraint = "concurrency"

        return {
            "type": "plan_review",
            "source": "plan_review_service",
            "review_id": review_id,
            "decision": decision,
            "category": category,
            "message": message,
            "alignment_score": alignment_score,
            "alignment_summary": alignment_summary or "",
            "bias_constraint": bias_constraint,
            "review_strictness": float((mode_strategy or {}).get("review_strictness", 1.0) or 1.0),
            "require_alignment_check": bool((mode_strategy or {}).get("require_alignment_check", False)),
            "recorded_at": _utcnow().isoformat(),
            "quality_decision": str((quality_report or {}).get("decision") or ""),
            "quality_overall_score": (quality_report or {}).get("overall_score"),
        }

    @staticmethod
    def _map_quality_gate_decision(quality_decision: str) -> str:
        normalized = str(quality_decision or "").strip().lower()
        if normalized == "approve":
            return ReviewDecision.APPROVED.value
        if normalized in {"revise", "downgrade_to_provisional", "ask_more"}:
            return ReviewDecision.NEEDS_MODIFICATION.value
        return ReviewDecision.REQUIRES_CONFIRMATION.value

    @staticmethod
    def _get_quality_gate_reason(quality_decision: str) -> str:
        normalized = str(quality_decision or "").strip().lower()
        if normalized == "ask_more":
            return "我先不把这个计划当成强计划发出去，还需要先补一个关键信息。"
        if normalized == "downgrade_to_provisional":
            return "当前证据或可行性还不够强，这轮更适合先给一个带假设的暂定计划。"
        if normalized == "revise":
            return "这份计划还差关键部分，需要先修正后再执行。"
        return "计划质量审查完成。"

    def _build_quality_gate_comments(self, quality_report) -> list[ReviewComment]:
        comments: list[ReviewComment] = []
        for issue in quality_report.issues:
            severity = SeverityLevel.INFO.value
            if issue.severity == "critical":
                severity = SeverityLevel.CRITICAL.value
            elif issue.severity == "warning":
                severity = SeverityLevel.WARNING.value
            comments.append(
                ReviewComment(
                    category=ReviewCategory.QUALITY.value,
                    severity=severity,
                    message=issue.message,
                    suggested_fix=self._quality_fix_hint(issue.code),
                )
            )
        if not comments and quality_report.decision != "approve":
            comments.append(
                ReviewComment(
                    category=ReviewCategory.QUALITY.value,
                    severity=SeverityLevel.WARNING.value,
                    message=self._get_quality_gate_reason(quality_report.decision),
                )
            )
        return comments

    @staticmethod
    def _quality_fix_hint(issue_code: str) -> str | None:
        normalized = str(issue_code or "").strip()
        if normalized.startswith("missing_section:"):
            section = normalized.split(":", 1)[-1]
            return f"请把 {section} 明确写进这轮计划。"
        if normalized == "grounding_required_but_missing":
            return "先使用用户材料证据，或者明确降级为暂定计划。"
        if normalized == "phase_a_guardrail_breach":
            return "先补关键缺口，再继续完整规划。"
        if normalized == "no_next_action":
            return "请先给出一个未来 24 小时内可执行的下一步。"
        if normalized == "overload_too_many_steps":
            return "请减少并行步骤，先压成一个更轻的启动动作。"
        return None

    async def _validate_feasibility(
        self,
        plan: ExecutablePlan,
        user_context: dict[str, Any],
    ) -> bool:
        """
        P0 Fix #1: Validate plan feasibility against user constraints.

        Checks for impossible constraints like:
        - Expert-level goals with minimal time investment
        - Time conflicts with user's schedule
        - Skill mismatches

        Args:
            plan: The executable plan to validate
            user_context: User context with constraints and skill level

        Returns:
            True if plan appears feasible, False if clearly infeasible
        """
        # Extract user skill level (default to intermediate if unknown)
        user_context.get("skill_level", "intermediate").lower()
        user_background = user_context.get("user_background", "")

        # Check each tool call for feasibility issues
        for tc in plan.tool_calls:
            params = tc.params or {}

            # === Check 1: Time vs Difficulty constraints ===
            daily_hours = params.get("daily_hours")
            total_days = params.get("total_days", params.get("duration_days"))
            difficulty = params.get("difficulty", "").lower()
            params.get("type", "").lower()
            title = params.get("title", "").lower()

            # Normalize difficulty from title if not in params
            if not difficulty:
                if any(word in title for word in ["精通", "专家", "expert", "master"]):
                    difficulty = "expert"
                elif any(word in title for word in ["入门", "基础", "beginner", "basic"]):
                    difficulty = "beginner"

            # Rule: Expert/master level goals require minimum time investment
            if difficulty in ["expert", "master", "精通"]:
                if daily_hours and daily_hours < 2:
                    logger.warning(f"Feasibility check failed: {difficulty} level with only {daily_hours}h/day")
                    return False

                # Additional check: liberal arts background needs more time for technical goals
                if user_background == "liberal_arts" and daily_hours < 3:
                    logger.warning(
                        f"Feasibility check failed: liberal arts user attempting {difficulty} "
                        f"technical goal with only {daily_hours}h/day"
                    )
                    return False

            # Rule: Impossible to reach "expert" in 1 week with low hours
            if total_days and total_days <= 7:
                if difficulty in ["expert", "master", "精通"] and daily_hours and daily_hours < 4:
                    logger.warning(
                        f"Feasibility check failed: {difficulty} in {total_days} days "
                        f"with {daily_hours}h/day is unrealistic"
                    )
                    return False

                # Check total hours required
                if daily_hours and total_days:
                    total_hours = daily_hours * total_days
                    # Most skills need ~100 hours for proficiency, 1000+ for mastery
                    if difficulty in ["expert", "master", "精通"] and total_hours < 50:
                        logger.warning(
                            f"Feasibility check failed: {difficulty} requires more than " f"{total_hours} total hours"
                        )
                        return False

            # === Check 2: Liberal arts student attempting advanced technical goals ===
            if user_background == "liberal_arts" or "文科" in str(user_background):
                # If user indicated they don't know code, advanced programming goals need review
                if any(word in title for word in ["爬虫", "web开发", "全栈", "crawler"]):
                    # Check if plan includes setup/basics
                    plan_has_setup = any(
                        "环境" in str(tc.params.get("description", ""))
                        or "安装" in str(tc.params.get("description", ""))
                        or "基础" in str(tc.params.get("description", ""))
                        for tc in plan.tool_calls
                    )

                    if not plan_has_setup:
                        logger.warning(
                            "Feasibility check: liberal arts user attempting advanced "
                            "technical goal without setup steps"
                        )
                        # Don't block, but require LLM review to catch this
                        return False

        # All feasibility checks passed
        return True

    async def _llm_review(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Perform LLM-based deep review of the plan with retry mechanism.

        Implements a three-tier fallback strategy:
        1. Try LLM review with retries
        2. If LLM fails, use rule-based fallback
        3. If rule-based is inconclusive, use safe defaults

        Args:
            plan: The executable plan
            user_message: Original user message
            user_context: User context

        Returns:
            Dictionary with decision, confidence, comments
        """
        # Build review prompt
        prompt = self._build_review_prompt(plan, user_message, user_context)

        # Try LLM review with retries
        last_error = None
        for attempt in range(self.MAX_LLM_REVIEW_RETRIES):
            try:
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

                # Validate response
                if not result or not isinstance(result, dict):
                    raise ValueError(f"Invalid LLM response type: {type(result)}")

                # Validate decision field
                decision = result.get("decision", ReviewDecision.REQUIRES_CONFIRMATION.value)
                valid_decisions = {d.value for d in ReviewDecision}
                if decision not in valid_decisions:
                    result["decision"] = ReviewDecision.REQUIRES_CONFIRMATION.value

                # Success - log and return
                logger.info(
                    f"LLM review succeeded on attempt {attempt + 1}: "
                    f"decision={result.get('decision')}, "
                    f"confidence={result.get('confidence', 0.0)}"
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"LLM review attempt {attempt + 1}/{self.MAX_LLM_REVIEW_RETRIES} failed: {e}")
                if attempt < self.MAX_LLM_REVIEW_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

        # LLM review failed after all retries - use rule-based fallback
        logger.error(f"LLM review failed after {self.MAX_LLM_REVIEW_RETRIES} attempts: {last_error}")
        return await self._llm_review_fallback(plan, user_message, user_context)

    async def _llm_review_fallback(
        self,
        plan: ExecutablePlan,
        user_message: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Rule-based fallback when LLM review is unavailable.

        Implements intelligent degradation based on plan characteristics:
        - Safe/read-only plans: auto-approve
        - Mixed plans: require confirmation
        - High-risk plans: reject with warning

        Args:
            plan: The executable plan
            user_message: Original user message
            user_context: User context

        Returns:
            Dictionary with decision, confidence, comments
        """
        logger.info("Using rule-based fallback for plan review")

        # Analyze plan characteristics
        tool_names = [tc.name for tc in plan.tool_calls]

        # Handle empty plan first (edge case)
        if not plan.tool_calls or not tool_names:
            decision = ReviewDecision.APPROVED.value
            confidence = 1.0
            logger.info("Fallback: Empty plan auto-approved")
            return {
                "decision": decision,
                "confidence": confidence,
                "comments": [
                    {
                        "category": ReviewCategory.SAFETY.value,
                        "severity": SeverityLevel.INFO.value,
                        "message": "Empty plan (no tool calls). Auto-approved.",
                    }
                ],
                "fallback_used": True,
                "fallback_reason": "llm_review_unavailable",
            }

        has_high_risk = any(name in self.HIGH_RISK_TOOLS for name in tool_names)
        has_safe_only = all(any(safe in name.lower() for safe in self.SAFE_TOOL_CATEGORIES) for name in tool_names)
        has_mixed = not has_high_risk and not has_safe_only

        comments = []
        decision = ReviewDecision.REQUIRES_CONFIRMATION.value
        confidence = 0.5

        if has_safe_only and len(plan.tool_calls) <= self.AUTO_APPROVE_MAX_TOOLS:
            # Safe plan - auto-approve
            decision = ReviewDecision.APPROVED.value
            confidence = 0.9
            comments.append(
                {
                    "category": ReviewCategory.SAFETY.value,
                    "severity": SeverityLevel.INFO.value,
                    "message": "Plan contains only read-only operations. Auto-approved by rule.",
                }
            )
            logger.info(f"Fallback: Auto-approved safe plan with {len(plan.tool_calls)} read-only tools")

        elif has_high_risk:
            # High-risk plan - require confirmation with warning
            decision = ReviewDecision.REQUIRES_CONFIRMATION.value
            confidence = 0.3
            high_risk_tools = [name for name in tool_names if name in self.HIGH_RISK_TOOLS]
            comments.append(
                {
                    "category": ReviewCategory.SAFETY.value,
                    "severity": SeverityLevel.WARNING.value,
                    "message": f"Plan contains high-risk operations: {', '.join(high_risk_tools)}",
                    "suggested_fix": "Please review carefully before proceeding.",
                    "affected_tool_calls": high_risk_tools,
                }
            )
            logger.warning(f"Fallback: High-risk plan requires confirmation: {high_risk_tools}")

        elif has_mixed:
            # Mixed plan - require confirmation
            decision = ReviewDecision.REQUIRES_CONFIRMATION.value
            confidence = 0.6
            comments.append(
                {
                    "category": ReviewCategory.SAFETY.value,
                    "severity": SeverityLevel.INFO.value,
                    "message": "LLM review unavailable. Plan requires manual confirmation.",
                    "suggested_fix": "Review the tool calls below and confirm if you wish to proceed.",
                }
            )
            logger.info("Fallback: Mixed plan requires confirmation")

        return {
            "decision": decision,
            "confidence": confidence,
            "comments": comments,
            "fallback_used": True,
            "fallback_reason": "llm_review_unavailable",
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
        user_context: dict[str, Any],
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
                "reasoning_summary": review.reasoning_summary,
                "reasoning_details": review.reasoning_details,
                "reasoning_source": review.reasoning_source,
                "persona_strategy_mapping": review.persona_strategy_mapping,
                "alignment_score": review.alignment_score,
                "alignment_summary": review.alignment_summary,
            },
        )
        return action_id

    def _build_persona_strategy_mapping(
        self,
        user_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        normalized_context = user_context if isinstance(user_context, dict) else {}
        plan_context = normalized_context.get("plan_context")
        plan_context = plan_context if isinstance(plan_context, dict) else {}
        task_summary = plan_context.get("task_summary")
        task_summary = task_summary if isinstance(task_summary, dict) else {}
        facts = plan_context.get("facts")
        facts = facts if isinstance(facts, dict) else {}
        recent_feedback = plan_context.get("recent_feedback")
        recent_feedback = recent_feedback if isinstance(recent_feedback, list) else []

        mappings: list[dict[str, Any]] = []

        def add_mapping(
            *,
            signal_key: str,
            signal_label: str,
            evidence: str,
            recommended_constraint: str,
            recommended_value: str,
            confidence_tier: str,
        ) -> None:
            mappings.append(
                {
                    "rule_key": signal_key,
                    "signal_key": signal_key,
                    "signal_label": signal_label,
                    "evidence": evidence,
                    "recommended_constraint": recommended_constraint,
                    "recommended_value": recommended_value,
                    "confidence_tier": confidence_tier,
                }
            )

        completion_rate = task_summary.get("avg_completion_rate")
        try:
            completion_rate_value = float(completion_rate) if completion_rate is not None else None
        except Exception:
            completion_rate_value = None
        if completion_rate_value is not None and completion_rate_value < 0.6:
            add_mapping(
                signal_key="avg_completion_rate_low",
                signal_label="近期完成率偏低",
                evidence=f"当前计划平均完成率约 {completion_rate_value:.0%}。",
                recommended_constraint="task_difficulty",
                recommended_value="lower",
                confidence_tier="inferred",
            )

        avg_task_duration = facts.get("avg_task_duration_minutes")
        session_length_preference = facts.get("session_length_preference")
        try:
            avg_task_duration_value = float(avg_task_duration) if avg_task_duration is not None else None
        except Exception:
            avg_task_duration_value = None
        try:
            session_length_value = float(session_length_preference) if session_length_preference is not None else None
        except Exception:
            session_length_value = None
        if (
            avg_task_duration_value is not None
            and session_length_value is not None
            and session_length_value > 0
            and avg_task_duration_value > session_length_value * 1.5
        ):
            add_mapping(
                signal_key="avg_task_duration_overrun",
                signal_label="近期单次任务普遍拉长",
                evidence=(
                    f"最近平均有效执行时长约 {avg_task_duration_value:.0f} 分钟，"
                    f"明显高于偏好时长 {session_length_value:.0f} 分钟。"
                ),
                recommended_constraint="task_granularity",
                recommended_value="finer",
                confidence_tier="inferred",
            )

        hard_count = 0
        long_count = 0
        just_right_count = 0
        explicit_count = 0
        for item in recent_feedback:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category") or "").strip().lower()
            content = str(item.get("content") or "").strip().lower()
            if item.get("completion_quality") is not None or category:
                explicit_count += 1
            if category == "too_difficult" or "太难" in content:
                hard_count += 1
            if category == "too_long" or "太长" in content:
                long_count += 1
            if category == "just_right" or "刚好" in content:
                just_right_count += 1

        feedback_tier = "explicit" if explicit_count else "implicit"
        if hard_count >= 2:
            add_mapping(
                signal_key="feedback_too_hard",
                signal_label="近期多次反馈偏难",
                evidence=f"最近反馈中有 {hard_count} 次提到任务难度偏高。",
                recommended_constraint="task_difficulty",
                recommended_value="lower",
                confidence_tier=feedback_tier,
            )
        if long_count >= 2:
            add_mapping(
                signal_key="feedback_too_long",
                signal_label="近期多次反馈偏长",
                evidence=f"最近反馈中有 {long_count} 次提到节奏或时长偏长。",
                recommended_constraint="session_length",
                recommended_value="shorter",
                confidence_tier=feedback_tier,
            )

        active_plans = normalized_context.get("active_plans")
        if isinstance(active_plans, list) and len(active_plans) >= 3:
            add_mapping(
                signal_key="active_plan_load_high",
                signal_label="活跃计划负载偏高",
                evidence=f"当前同时存在 {len(active_plans)} 个活跃计划。",
                recommended_constraint="concurrency",
                recommended_value="lower",
                confidence_tier="inferred",
            )

        if just_right_count >= 2 and (completion_rate_value is None or completion_rate_value >= 0.7):
            add_mapping(
                signal_key="feedback_just_right",
                signal_label="近期节奏匹配度较高",
                evidence=f"最近反馈里已有 {just_right_count} 次明确表示节奏刚好。",
                recommended_constraint="load_shape",
                recommended_value="preserve",
                confidence_tier=feedback_tier,
            )

        return mappings[:5]

    def _score_plan_alignment(
        self,
        *,
        plan: ExecutablePlan,
        mappings: list[dict[str, Any]] | None,
    ) -> tuple[float | None, str | None, list[str]]:
        if not mappings:
            return None, None, []

        tool_count = len(plan.tool_calls or [])
        risk_count = len(plan.risk_flags or [])
        total_steps = int(plan.total_steps or tool_count)
        timeouts = [int(call.timeout_ms or 0) for call in (plan.tool_calls or []) if getattr(call, "timeout_ms", None)]
        avg_timeout = sum(timeouts) / len(timeouts) if timeouts else 0.0
        max_parallel = 1
        if plan.execution_order:
            max_parallel = max((len(layer) for layer in plan.execution_order if isinstance(layer, list)), default=1)
        low_scope = tool_count <= 5 and risk_count <= 1
        finer_granularity = total_steps >= 3 or tool_count >= 3
        shorter_session = avg_timeout > 0 and avg_timeout <= 15000
        lower_concurrency = plan.collaboration_mode != "parallel" and max_parallel <= 1
        preserve_load = low_scope and tool_count >= 1

        tier_weight = {
            "explicit": 1.0,
            "implicit": 0.8,
            "inferred": 0.6,
            "weak": 0.3,
        }
        achieved_weight = 0.0
        total_weight = 0.0
        matched_labels: list[str] = []
        matched_rule_keys: list[str] = []

        for item in mappings:
            constraint = str(item.get("recommended_constraint") or "").strip().lower()
            value = str(item.get("recommended_value") or "").strip().lower()
            tier = str(item.get("confidence_tier") or "inferred").strip().lower()
            weight = tier_weight.get(tier, 0.6)
            total_weight += weight
            satisfied = False
            if constraint == "task_difficulty" and value == "lower":
                satisfied = low_scope and risk_count <= 1
            elif constraint == "task_granularity" and value == "finer":
                satisfied = finer_granularity
            elif constraint == "session_length" and value == "shorter":
                satisfied = shorter_session or finer_granularity
            elif constraint == "concurrency" and value == "lower":
                satisfied = lower_concurrency
            elif constraint == "load_shape" and value == "preserve":
                satisfied = preserve_load and plan.confidence >= 0.6
            if satisfied:
                achieved_weight += weight
                matched_labels.append(str(item.get("signal_label") or item.get("signal_key") or ""))
                matched_rule_keys.append(str(item.get("rule_key") or item.get("signal_key") or ""))

        if total_weight <= 0:
            return None, None, []
        score = round(achieved_weight / total_weight, 2)
        if score >= 0.8:
            summary = "这次计划和你最近的执行画像基本一致，关键建议大多被实际吸收进了方案里。"
        elif score >= 0.55:
            summary = "这次计划和你的近期画像大体一致，但还有少量约束没有完全落到执行方案里。"
        else:
            summary = "这次计划和你的近期画像对齐度偏低，建议再检查难度、颗粒度或并行负载是否收得够紧。"
        if matched_labels:
            summary = f"{summary} 已命中的画像建议包括：{'、'.join(label for label in matched_labels if label)[:60]}。"
        return score, summary, matched_rule_keys

    @staticmethod
    def _extract_user_id(user_context: dict[str, Any]) -> UUID | None:
        candidates = [
            ((user_context or {}).get("user_context") or {}).get("user_id"),
            ((user_context or {}).get("profile") or {}).get("identity", {}).get("user_id"),
            (user_context or {}).get("user_id"),
        ]
        for candidate in candidates:
            try:
                if candidate:
                    return UUID(str(candidate))
            except Exception:
                continue
        return None

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
        auto_approve_reason: str | None = None,
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

    def _build_reasoning_payload(
        self,
        *,
        plan: ExecutablePlan,
        user_context: dict[str, Any],
        decision: str,
        auto_approved: bool,
        auto_approve_reason: str | None = None,
    ) -> tuple[str | None, list[dict[str, str]] | None]:
        started_at = time.perf_counter()
        if not settings.ENABLE_PLAN_REASONING_SUMMARY:
            return None, None
        if decision != ReviewDecision.APPROVED.value:
            return None, None

        normalized_context = user_context if isinstance(user_context, dict) else {}
        plan_context = normalized_context.get("plan_context")
        plan_context = plan_context if isinstance(plan_context, dict) else {}
        progress_snapshot = normalized_context.get("progress_snapshot")
        progress_snapshot = progress_snapshot if isinstance(progress_snapshot, dict) else {}
        llm_profile = normalized_context.get("llm_profile")
        llm_profile = llm_profile if isinstance(llm_profile, dict) else {}

        details: list[dict[str, str]] = []

        def append_detail(
            *,
            label: str,
            evidence: str,
            impact: str,
            confidence_tier: str,
        ) -> None:
            details.append(
                {
                    "label": label,
                    "evidence": evidence,
                    "impact": impact,
                    "confidence_tier": confidence_tier,
                }
            )

        task_summary = plan_context.get("task_summary")
        task_summary = task_summary if isinstance(task_summary, dict) else {}
        completed = int(task_summary.get("completed", 0) or 0)
        total = int(task_summary.get("total", 0) or 0)
        completion_rate = task_summary.get("avg_completion_rate")
        try:
            completion_rate_value = float(completion_rate) if completion_rate is not None else None
        except Exception:
            completion_rate_value = None
        if total > 0:
            append_detail(
                label="最近执行完成率",
                evidence=(
                    f"当前计划已完成 {completed}/{total} 个任务"
                    f"{f'，平均完成率约 {completion_rate_value:.0%}' if completion_rate_value is not None else ''}。"
                ),
                impact="这次方案会优先延续你已经能稳定推进的节奏，而不是突然加重负担。",
                confidence_tier="inferred",
            )

        facts = plan_context.get("facts")
        facts = facts if isinstance(facts, dict) else {}
        avg_task_duration = facts.get("avg_task_duration_minutes")
        session_length_preference = facts.get("session_length_preference")
        difficulty_preference = facts.get("difficulty_preference")
        fact_parts: list[str] = []
        if avg_task_duration:
            fact_parts.append(f"最近平均有效执行时长约 {avg_task_duration} 分钟")
        if session_length_preference:
            fact_parts.append(f"计划上下文记录的单次偏好时长约 {session_length_preference} 分钟")
        if difficulty_preference is not None:
            fact_parts.append(f"当前难度偏好约 {difficulty_preference}")
        if fact_parts:
            append_detail(
                label="近期执行时长与难度",
                evidence="；".join(fact_parts) + "。",
                impact="这让计划时长和任务颗粒度更贴近你最近真实能完成的强度。",
                confidence_tier="inferred",
            )

        recent_feedback = plan_context.get("recent_feedback")
        if isinstance(recent_feedback, list) and recent_feedback:
            detail_count = 0
            long_count = 0
            hard_count = 0
            explicit_count = 0
            for item in recent_feedback:
                if not isinstance(item, dict):
                    continue
                content = str(item.get("content") or "").lower()
                detail_count += 1
                if item.get("completion_quality") is not None or item.get("category"):
                    explicit_count += 1
                if "long" in content or "太长" in content:
                    long_count += 1
                if "difficult" in content or "太难" in content:
                    hard_count += 1
            feedback_fragments: list[str] = []
            if long_count:
                feedback_fragments.append(f"{long_count} 条反馈提到节奏偏长")
            if hard_count:
                feedback_fragments.append(f"{hard_count} 条反馈提到难度偏高")
            if feedback_fragments:
                append_detail(
                    label="最近反馈信号",
                    evidence=f"最近 {detail_count} 条计划反馈中，" + "，".join(feedback_fragments) + "。",
                    impact="通过后的方案会优先压住过长或过难的风险，避免重复踩到最近的阻力点。",
                    confidence_tier="explicit" if explicit_count else "implicit",
                )

        highlights = [str(item).strip() for item in (progress_snapshot.get("highlights") or []) if str(item).strip()]
        if highlights:
            append_detail(
                label="近期进度快照",
                evidence=highlights[0],
                impact="规划说明会优先沿着你最近真正有进展的方向继续推进。",
                confidence_tier="inferred",
            )

        active_plans = normalized_context.get("active_plans") if isinstance(normalized_context, dict) else None
        if isinstance(active_plans, list) and active_plans:
            append_detail(
                label="当前计划负载",
                evidence=f"你当前有 {len(active_plans)} 个活跃计划，系统优先保持这次方案足够轻量。",
                impact="这样能降低新计划和现有节奏互相挤占的风险。",
                confidence_tier="inferred",
            )

        if not details:
            tool_count = len(plan.tool_calls or [])
            append_detail(
                label="执行复杂度",
                evidence=f"本次计划包含 {tool_count} 个动作，风险标记 {len(plan.risk_flags or [])} 个。",
                impact="动作数量和风险都在可控范围内，适合直接推进。",
                confidence_tier="inferred",
            )

        verbosity = str(llm_profile.get("verbosity_target") or "").strip()
        tone = str(llm_profile.get("tone") or "").strip()
        if auto_approved and auto_approve_reason:
            append_detail(
                label="自动通过依据",
                evidence=self._get_auto_approve_reason(auto_approve_reason),
                impact="这说明计划满足了安全且低风险的快速通过条件。",
                confidence_tier="inferred",
            )

        summary_parts: list[str] = []
        if total > 0:
            if completion_rate_value is not None:
                summary_parts.append(f"这个计划被通过，是因为你当前计划的稳定完成率约为 {completion_rate_value:.0%}")
            else:
                summary_parts.append(f"这个计划被通过，是因为你当前计划已经稳定完成了 {completed}/{total} 个任务")
        elif avg_task_duration:
            summary_parts.append(f"这个计划被通过，是因为你最近的有效执行时长大约稳定在 {avg_task_duration} 分钟")
        else:
            tool_count = len(plan.tool_calls or [])
            confidence_pct = f"{float(plan.confidence or 0.0):.0%}"
            summary_parts.append(
                f"这个计划被通过，是因为当前执行复杂度可控（{tool_count} 个动作）且整体置信度约 {confidence_pct}"
            )
        if verbosity or tone:
            summary_parts.append(f"说明方式也会继续按你偏好的 {verbosity or 'balanced'} / {tone or '稳定'} 节奏呈现")
        if auto_approved and auto_approve_reason:
            summary_parts.append(f"并满足“{self._get_auto_approve_reason(auto_approve_reason)}”的快速通过条件")
        summary = "，".join(summary_parts) + "。"
        PLAN_REASONING_GENERATED_TOTAL.labels(decision=decision).inc()
        PHASE4_OPERATION_DURATION_SECONDS.labels(operation="build_reasoning_payload").observe(
            max(time.perf_counter() - started_at, 0.0)
        )
        return summary, details[:3]

    def _get_auto_approve_reason(self, reason_code: str | None) -> str:
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
        user_comment: str | None = None,
        modifications: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        # Atomically claim the action (get-and-delete) to prevent concurrent processing
        action = await pending_actions_store.claim(review_id, user_id)
        if not action:
            logger.warning(f"Review not found or expired: {review_id}")
            return {
                "status": "error",
                "message": "Review not found or expired",
            }

        preview_data = action.get("preview_data", {})
        plan_id = preview_data.get("plan_id")
        logger.info(f"User {user_decision} review {review_id} for plan {plan_id}")

        # Fix #3: 追踪拒绝次数，检测连续两次拒绝
        if user_decision == "reject" and plan_id:
            rejection_count = await self.track_rejection_count(plan_id, user_id)
            logger.info(f"Plan {plan_id} rejection count: {rejection_count}")

            # 两次拒绝，触发信息收集（回到对话澄清需求）
            if rejection_count >= 2:
                logger.warning(f"Plan {plan_id} rejected {rejection_count} times, " "triggering information collection")

                # 清理拒绝计数
                await self.reset_rejection_count(plan_id, user_id)

                # 触发信息收集（通过Redis pub/sub通知orchestrator）
                await self._trigger_information_collection(
                    plan_id=plan_id, user_id=user_id, feedback=user_comment or "用户连续两次否定方案"
                )

                return {
                    "status": "information_collection_triggered",
                    "message": "方案被连续否定，需要重新了解您的需求",
                    "rejection_count": rejection_count,
                }

        # 用户接受方案，重置拒绝计数
        if user_decision == "approve" and plan_id:
            await self.reset_rejection_count(plan_id, user_id)

        # === Phase 4: 时机2: Write user decision to feedback_log ===
        if db_session and plan_id:
            try:
                from uuid import UUID

                from app.services.plan_feedback_service import get_plan_feedback_service

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

        return {
            "status": "success",
            "user_decision": user_decision,
            "review_id": review_id,
            "plan_id": plan_id,
            "message": f"Review {user_decision} by user",
        }

    async def get_stored_plan(self, plan_id: str, user_id: str) -> dict[str, Any] | None:
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
        self,
        plan_id: str,
        user_id: str,
        db_session: Any | None = None,
        modifications: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Resume plan execution after user approval.

        This method is called when a user approves a plan review.
        It updates the plan state to indicate it should proceed with execution.
        Also triggers automatic task generation for the approved plan.

        Args:
            plan_id: Plan ID to resume
            user_id: User who approved
            db_session: Optional database session for task generation
            modifications: Optional UI metadata submitted with the approval

        Returns:
            Status dictionary
        """
        logger.info(f"Resuming plan {plan_id} after approval by user {user_id}")
        auto_delegate_tasks = self._should_auto_delegate_tasks(modifications)

        # Store the approval in pending_actions for the orchestrator to pick up
        action_id = await pending_actions_store.save(
            tool_name="__plan_approved__",
            arguments={
                "plan_id": plan_id,
                "user_id": user_id,
                "auto_delegate_tasks": auto_delegate_tasks,
                "review_modifications": modifications or {},
            },
            user_id=user_id,
            description=f"Plan {plan_id} approved by user",
            preview_data={
                "plan_id": plan_id,
                "user_id": user_id,
                "action": "resume",
                "auto_delegate_tasks": auto_delegate_tasks,
                "timestamp": _utcnow().isoformat(),
            },
        )

        # Trigger asynchronous task generation
        asyncio.create_task(
            self._generate_tasks_after_approval(
                plan_id=plan_id,
                user_id=user_id,
                action_id=action_id,
                auto_delegate_tasks=auto_delegate_tasks,
            )
        )
        asyncio.create_task(
            self._capture_plan_goal_memory(
                plan_id=plan_id,
                user_id=user_id,
                action_id=action_id,
            )
        )

        return {
            "status": "success",
            "action_id": action_id,
            "message": (
                "Plan approved and task generation initiated"
                if not auto_delegate_tasks
                else "Plan approved, task generation initiated, and eligible tasks will be auto-delegated"
            ),
            "task_generation_initiated": True,
            "auto_delegate_tasks": auto_delegate_tasks,
        }

    async def _capture_plan_goal_memory(
        self,
        *,
        plan_id: str,
        user_id: str,
        action_id: str,
    ) -> None:
        from sqlalchemy import select

        from app.database import get_db_session
        from app.models.memory import MemoryGoal
        from app.models.plan import Plan
        from app.services.memory_service import MemoryService

        try:
            plan_uuid = UUID(plan_id)
            user_uuid = UUID(user_id)
        except ValueError:
            logger.warning("Skipping plan goal memory capture for invalid ids plan_id={} user_id={}", plan_id, user_id)
            return

        try:
            async with get_db_session() as db:
                plan = await db.get(Plan, plan_uuid)
                if plan is None or plan.user_id != user_uuid:
                    return

                existing = await db.execute(
                    select(MemoryGoal).where(
                        MemoryGoal.user_id == user_uuid,
                        MemoryGoal.linked_plan_id == plan_uuid,
                        MemoryGoal.deleted_at.is_(None),
                        MemoryGoal.archived_at.is_(None),
                        MemoryGoal.retracted_at.is_(None),
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    return

                memory_service = MemoryService(db)
                await memory_service.create_goal(
                    user_id=user_uuid,
                    title=plan.name,
                    linked_plan_id=plan_uuid,
                    status="active",
                    evidence_refs=[{"type": "event", "id": action_id, "schema_version": "event.v1"}],
                    metadata={
                        "plan_type": str(plan.type.value) if getattr(plan.type, "value", None) else str(plan.type),
                        "subject": plan.subject,
                    },
                    source_type="event",
                )
        except Exception as exc:
            logger.warning("Plan approval goal memory capture failed for plan {}: {}", plan_id, exc)

    async def _generate_tasks_after_approval(
        self,
        plan_id: str,
        user_id: str,
        action_id: str,
        auto_delegate_tasks: bool = False,
    ) -> None:
        """
        Background task: Generate tasks automatically after plan approval.

        This method runs asynchronously after a plan is approved,
        generating concrete tasks based on the plan details.

        Args:
            plan_id: The approved plan ID
            user_id: User who owns the plan
            action_id: The approval action ID for tracking
            auto_delegate_tasks: Whether eligible tasks should be handed off automatically
        """
        from uuid import UUID

        from sqlalchemy import select

        from app.database import get_db_session
        from app.models.plan import Plan, PlanType
        from app.models.task import Task
        from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
        from app.tools.schemas import GenerateTasksForPlanParams

        try:
            # Get a fresh database session
            async with get_db_session() as db:
                # Fetch plan details
                plan = await db.get(Plan, UUID(plan_id))
                if not plan:
                    logger.warning(f"Plan {plan_id} not found for task generation")
                    return

                # Check if tasks already exist for this plan
                existing_tasks_result = await db.execute(select(Task).where(Task.plan_id == UUID(plan_id)))
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
                    f"Generating {task_count} tasks for plan {plan_id} " f"(difficulty={difficulty}, topic={topic})"
                )

                # Execute the tool
                params = GenerateTasksForPlanParams(
                    plan_id=plan_id, topic=topic, difficulty=difficulty, task_count=task_count
                )

                result = await tool.execute(params=params, user_id=user_id, db_session=db, tool_call_id=action_id)

                if result.success:
                    task_count_created = result.data.get("task_count", 0)
                    logger.info(
                        f"Successfully generated {task_count_created} tasks "
                        f"for plan {plan_id} (action_id={action_id})"
                    )
                    if auto_delegate_tasks:
                        await self._auto_delegate_generated_tasks(
                            db_session=db,
                            user_id=user_id,
                            plan_id=plan_id,
                            tasks=result.data.get("tasks") or [],
                        )
                else:
                    logger.error(f"Task generation failed for plan {plan_id}: " f"{result.error_message}")

        except Exception as e:
            logger.error(f"Error in _generate_tasks_after_approval: {e}", exc_info=True)

    async def notify_plan_rejected(self, plan_id: str, user_id: str, feedback: str) -> dict[str, Any]:
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
        logger.info(f"Plan {plan_id} rejected by user {user_id}. Feedback: {feedback[:100]}...")

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
                "timestamp": _utcnow().isoformat(),
            },
        )

        return {
            "status": "success",
            "action_id": action_id,
            "message": "Plan rejection recorded",
        }

    async def trigger_replanning(
        self,
        plan_id: str,
        user_id: str,
        feedback: str,
        modifications: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger replanning based on user feedback.

        This method is called when a user requests modifications to a plan.
        It stores the modification request and creates a new planning task.

        Args:
            plan_id: Original plan ID
            user_id: User requesting modifications
            feedback: User's modification request
            modifications: Optional UI metadata submitted with the request

        Returns:
            Status dictionary with new plan ID if created
        """
        logger.info(f"Triggering replan for {plan_id} by user {user_id}. Feedback: {feedback[:100]}...")

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
                "review_modifications": modifications or {},
            },
            user_id=user_id,
            description=f"Plan modification requested: {feedback[:100]}",
            preview_data={
                "original_plan_id": plan_id,
                "new_plan_id": new_plan_id,
                "user_id": user_id,
                "action": "replan",
                "feedback": feedback,
                "timestamp": _utcnow().isoformat(),
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
                "timestamp": _utcnow().isoformat(),
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
        await event_bus.publish(
            "plan.replanned",
            {
                "event_type": "plan.replanned",
                "user_id": user_id,
                "original_plan_id": plan_id,
                "plan_id": new_plan_id,
                "feedback": feedback,
            },
        )
        from app.core.event_bus import PlanCreatedEvent

        plan_created = PlanCreatedEvent(
            user_id=str(user_id),
            plan_id=str(new_plan_id),
            evidence_id=str(new_plan_id),
            source="plan_review_service",
            metadata={"original_plan_id": str(plan_id), "feedback": feedback},
        )
        await event_bus.publish("plan.created", plan_created.to_dict())
        await publish_srl_event(
            user_id=user_id,
            trigger_event_type="plan.created",
            evidence_id=str(new_plan_id),
            metadata={"plan_id": str(new_plan_id), "original_plan_id": str(plan_id)},
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

        from app.core.context_pack import ContextPackBuilder
        from app.core.sse import sse_manager
        from app.database import get_db_session
        from app.orchestration.executor import ToolExecutor
        from app.orchestration.lang_graph_planner import LangGraphPlanner
        from app.orchestration.state_snapshot import StateSnapshotManager

        try:
            async with get_db_session() as db:
                session_id = f"replan:{action_id}"
                snapshot_manager = StateSnapshotManager(self.redis)
                snapshot = await snapshot_manager.create_snapshot(
                    user_id=user_id,
                    session_id=session_id,
                    db_session=db,
                )

                replan_message = "用户请求修改当前计划。" f"原计划ID: {original_plan_id}。" f"反馈: {feedback}"

                planner = LangGraphPlanner(
                    self.redis,
                    circuit_breaker=await self._get_langgraph_breaker(),
                )
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
                        intent="planning",
                        query_text=replan_message,
                        focus_mode="plan_focus",
                        route_intent="plan",
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
                            runtime_context={
                                "plan_id": executable_plan.plan_id,
                            },
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
                        f"Replan review queued: action_id={review_action_id}, " f"plan={executable_plan.plan_id}"
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

    async def track_rejection_count(self, plan_id: str, user_id: str) -> int:
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

    async def reset_rejection_count(self, plan_id: str, user_id: str):
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

    async def _trigger_information_collection(self, plan_id: str, user_id: str, feedback: str):
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
                "timestamp": _utcnow().isoformat(),
            }
            try:
                await self.redis.publish(f"user:{user_id}:info_collection", json.dumps(notification))
                logger.info(f"Published information collection trigger for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to publish information collection trigger: {e}")

    @staticmethod
    def _should_auto_delegate_tasks(modifications: dict[str, Any] | None) -> bool:
        if not isinstance(modifications, dict):
            return False
        raw = (
            modifications.get("delegate_approved_tasks")
            or modifications.get("auto_delegate_approved_tasks")
            or modifications.get("delegate_to_agent")
            or modifications.get("execution_mode")
        )
        if isinstance(raw, bool):
            return raw
        normalized = str(raw or "").strip().lower()
        return normalized in {"true", "1", "yes", "agent", "auto"}

    async def _auto_delegate_generated_tasks(
        self,
        *,
        db_session: Any,
        user_id: str,
        plan_id: str,
        tasks: list[dict[str, Any]],
    ) -> None:
        from app.models.execution_intent import ExecutionMode
        from app.services.execution_service import ExecutionService

        execution_service = ExecutionService(db=db_session)
        user_uuid = UUID(user_id)
        eligible_task_ids: list[UUID] = []

        for task_payload in tasks:
            raw_task_id = str(task_payload.get("id") or "").strip()
            if not raw_task_id:
                continue
            try:
                task_uuid = UUID(raw_task_id)
            except Exception:
                logger.debug("Skipping auto-delegation for invalid task id payload: {}", raw_task_id)
                continue
            try:
                decision = await execution_service.classify_task(
                    task_id=task_uuid,
                    user_id=user_uuid,
                )
            except Exception as exc:
                logger.info(
                    "Skipping auto-delegation for task {} in plan {} because classification failed: {}",
                    task_uuid,
                    plan_id,
                    exc,
                )
                continue
            if decision.execution_mode == ExecutionMode.HUMAN:
                continue
            eligible_task_ids.append(task_uuid)

        if not eligible_task_ids:
            logger.info("Plan {} has no generated tasks eligible for auto-delegation", plan_id)
            return

        try:
            payload = await execution_service.handoff_tasks_batch(
                task_ids=eligible_task_ids,
                user_id=user_uuid,
                execution_strategy="auto",
            )
            logger.info(
                "Auto-delegated {} generated tasks for plan {} after approval (requested={})",
                len(payload.get("items") or []),
                plan_id,
                len(eligible_task_ids),
            )
        except Exception as exc:
            logger.warning(
                "Failed to auto-delegate generated tasks for plan {}: {}",
                plan_id,
                exc,
            )


# Global singleton
plan_review_service = PlanReviewService()
