from __future__ import annotations
"""
Version Conflict Detection Service - Phase 3 (P1)

Handles version conflict detection and resolution for plans:
1. Pre-execution version validation
2. Auto-replan mechanism
3. HITL escalation for low confidence replans
4. Rate limiting for replans

P1 Priority: 版本冲突检测增强
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Literal
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis

from app.orchestration.schemas import (
    MAX_REPLAN_ATTEMPTS,
    REPLAN_MAX_PER_WINDOW,
    REPLAN_RATE_LIMIT_WINDOW,
    VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD,
    VERSION_CONFLICT_HITL_THRESHOLD,
    ExecutablePlan,
    StateSnapshot,
)


@dataclass
class VersionConflictResult:
    """Version conflict detection result"""
    has_conflict: bool = False
    conflict_type: Literal["none", "plan_version", "context_version", "both"] = "none"
    expected_version: int = 0
    current_version: int = 0
    changed_fields: list[str] = field(default_factory=list)
    recommendation: Literal["proceed", "replan", "hitl", "discard"] = "proceed"
    replan_confidence: float = 1.0
    conflicted_domains: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_conflict": self.has_conflict,
            "conflict_type": self.conflict_type,
            "expected_version": self.expected_version,
            "current_version": self.current_version,
            "changed_fields": self.changed_fields,
            "recommendation": self.recommendation,
            "replan_confidence": self.replan_confidence,
            "conflicted_domains": self.conflicted_domains,
            "affected_domains": self.affected_domains,
            "details": self.details,
        }


@dataclass
class ReplanResult:
    """Replan operation result"""
    success: bool
    new_plan: ExecutablePlan | None = None
    reason: str = ""
    attempt_count: int = 0
    requires_hitl: bool = False
    hitl_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "new_plan_id": self.new_plan.plan_id if self.new_plan else None,
            "reason": self.reason,
            "attempt_count": self.attempt_count,
            "requires_hitl": self.requires_hitl,
            "hitl_reason": self.hitl_reason,
        }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class VersionConflictService:
    """
    Version Conflict Detection and Resolution Service

    Responsibilities:
    1. Detect version conflicts before plan execution
    2. Determine appropriate resolution strategy
    3. Manage auto-replan with rate limiting
    4. Escalate to HITL when necessary
    """

    # Redis key prefixes
    REPLAN_COUNT_PREFIX = "replan_count:"
    CONFLICT_HISTORY_PREFIX = "conflict_history:"

    def __init__(
        self,
        redis: Redis | None = None,
        plan_state_service=None,
        planner=None,
    ):
        self.redis = redis
        self.plan_state_service = plan_state_service
        self.planner = planner

    async def check_version_conflict(
        self,
        plan: ExecutablePlan,
        user_id: UUID,
        current_snapshot: StateSnapshot | None = None,
    ) -> VersionConflictResult:
        """
        Check for version conflicts before plan execution

        Args:
            plan: The executable plan to validate
            user_id: User ID for state lookup
            current_snapshot: Current state snapshot (optional, will fetch if not provided)

        Returns:
            VersionConflictResult with conflict details and recommendation
        """
        result = VersionConflictResult()

        if not self.plan_state_service:
            logger.warning("No plan_state_service configured, skipping version check")
            return result

        try:
            # Get plan_id from context if available
            plan_id_str = plan.context_version.split(":")[0] if ":" in plan.context_version else None

            if not plan_id_str:
                # No plan_id in context, skip version check
                logger.debug("No plan_id in context, skipping version conflict check")
                return result

            plan_id = UUID(plan_id_str)

            # Get current PlanState version
            plan_state = await self.plan_state_service.get_plan_state(user_id, plan_id)

            if not plan_state:
                logger.debug(f"No PlanState found for plan {plan_id}, skipping version check")
                return result

            current_version = plan_state.version
            expected_version = plan.plan_version

            # Check for version mismatch
            if current_version != expected_version:
                result.has_conflict = True
                result.conflict_type = "plan_version"
                result.expected_version = expected_version
                result.current_version = current_version

                # Analyze what changed
                result.changed_fields = self._detect_changed_fields(plan, plan_state)

                # Determine recommendation based on change severity
                result.replan_confidence = self._calculate_replan_confidence(
                    expected_version, current_version, result.changed_fields
                )

                if result.replan_confidence >= VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD:
                    result.recommendation = "replan"
                elif result.replan_confidence >= VERSION_CONFLICT_HITL_THRESHOLD:
                    result.recommendation = "hitl"
                else:
                    result.recommendation = "proceed"  # Minor change, can proceed

                logger.info(
                    f"Version conflict detected for plan {plan_id}: "
                    f"expected={expected_version}, current={current_version}, "
                    f"recommendation={result.recommendation}, "
                    f"confidence={result.replan_confidence:.2f}"
                )

        except Exception as e:
            logger.error(f"Version conflict check failed: {e}")
            # On error, default to proceeding but log the issue
            result.details["error"] = str(e)

        return result

    def _check_context_versions(
        self,
        snapshot: StateSnapshot,
        current_context_versions: dict[str, str],
    ) -> VersionConflictResult:
        result = VersionConflictResult()
        if not snapshot:
            return result

        snapshot_versions = snapshot.context_versions or {}
        conflicted_domains = []
        for domain, snapshot_version in snapshot_versions.items():
            current_version = current_context_versions.get(domain)
            if current_version and current_version != snapshot_version:
                conflicted_domains.append(domain)

        if conflicted_domains:
            result.has_conflict = True
            result.conflict_type = "context_version"
            result.changed_fields = conflicted_domains
            result.conflicted_domains = conflicted_domains
            result.details["snapshot_versions"] = snapshot_versions
            result.details["current_versions"] = current_context_versions

        return result

    def _infer_domain_for_tool(self, tool_name: str) -> str | None:
        tool_lower = tool_name.lower()
        if "task" in tool_lower:
            return "tasks"
        if "plan" in tool_lower or "sprint" in tool_lower:
            return "plans"
        if "focus" in tool_lower or "pomodoro" in tool_lower:
            return "focus"
        if "friend" in tool_lower or "group" in tool_lower or "community" in tool_lower:
            return "community"
        if "knowledge" in tool_lower or "graph" in tool_lower or "galaxy" in tool_lower:
            return "knowledge"
        return None

    def _get_plan_affected_domains(self, plan: ExecutablePlan) -> list[str]:
        domains = set()
        for tool_call in plan.tool_calls:
            domain = self._infer_domain_for_tool(tool_call.name)
            if domain:
                domains.add(domain)
        return sorted(domains)

    def _merge_conflicts(
        self,
        *,
        context_check: VersionConflictResult,
        plan_check: VersionConflictResult,
        plan: ExecutablePlan,
    ) -> VersionConflictResult:
        merged = VersionConflictResult()
        merged.affected_domains = self._get_plan_affected_domains(plan)

        if not context_check.has_conflict and not plan_check.has_conflict:
            return merged

        if context_check.has_conflict and plan_check.has_conflict:
            merged.conflict_type = "both"
        elif context_check.has_conflict:
            merged.conflict_type = "context_version"
        else:
            merged.conflict_type = "plan_version"

        merged.has_conflict = True
        merged.expected_version = plan_check.expected_version
        merged.current_version = plan_check.current_version
        merged.changed_fields = sorted(set(context_check.changed_fields + plan_check.changed_fields))
        merged.conflicted_domains = sorted(set(context_check.conflicted_domains))
        merged.replan_confidence = min(context_check.replan_confidence, plan_check.replan_confidence)
        if merged.replan_confidence <= 0:
            merged.replan_confidence = plan_check.replan_confidence or 0.8

        # Decision tree (align orchestrator behavior)
        conflict_domains = set(merged.conflicted_domains)
        affected_domains = set(merged.affected_domains)
        if conflict_domains and affected_domains and conflict_domains.isdisjoint(affected_domains):
            merged.recommendation = "proceed"
        elif plan.fallback_strategy.get("on_version_conflict") == "replan":
            if plan.confidence < 0.7:
                merged.recommendation = "discard"
            elif merged.replan_confidence >= VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD:
                merged.recommendation = "replan"
            else:
                merged.recommendation = "hitl"
        else:
            merged.recommendation = "hitl"

        merged.details = {
            "context_conflict": context_check.to_dict(),
            "plan_conflict": plan_check.to_dict(),
        }
        return merged

    async def check_all_conflicts(
        self,
        plan: ExecutablePlan,
        snapshot: StateSnapshot,
        current_context_versions: dict[str, str],
        user_id: UUID,
    ) -> VersionConflictResult:
        context_check = self._check_context_versions(snapshot, current_context_versions)
        plan_check = await self.check_version_conflict(plan, user_id)
        return self._merge_conflicts(
            context_check=context_check,
            plan_check=plan_check,
            plan=plan,
        )

    def _detect_changed_fields(self, plan: ExecutablePlan, plan_state) -> list[str]:
        """Detect which fields changed between planning and current state"""
        changed_fields = []

        # Compare key state fields
        if hasattr(plan_state, "current_phase") and plan_state.current_phase:
            changed_fields.append("current_phase")

        if hasattr(plan_state, "completed_milestones") and plan_state.completed_milestones:
            changed_fields.append("milestones")

        if hasattr(plan_state, "active_task_count") and plan_state.active_task_count > 0:
            changed_fields.append("active_tasks")

        if hasattr(plan_state, "feedback_log") and len(plan_state.feedback_log or []) > 0:
            changed_fields.append("feedback")

        if hasattr(plan_state, "constraints") and plan_state.constraints:
            changed_fields.append("constraints")

        return changed_fields

    def _calculate_replan_confidence(
        self,
        expected_version: int,
        current_version: int,
        changed_fields: list[str],
    ) -> float:
        """
        Calculate confidence score for auto-replan

        Higher confidence = more likely that replan will succeed
        Lower confidence = more complex changes that may need human review
        """
        version_delta = abs(current_version - expected_version)

        # Base confidence decreases with version delta
        if version_delta == 1:
            base_confidence = 0.9
        elif version_delta <= 3:
            base_confidence = 0.7
        elif version_delta <= 5:
            base_confidence = 0.5
        else:
            base_confidence = 0.3

        # Adjust based on changed fields
        critical_fields = {"constraints", "current_phase"}
        moderate_fields = {"milestones", "active_tasks"}
        minor_fields = {"feedback"}

        for field in changed_fields:
            if field in critical_fields:
                base_confidence -= 0.2
            elif field in moderate_fields:
                base_confidence -= 0.1
            elif field in minor_fields:
                base_confidence -= 0.05

        return max(0.1, min(1.0, base_confidence))

    async def can_replan(self, user_id: UUID, plan_id: UUID) -> tuple:
        """
        Check if replan is allowed (rate limiting)

        Returns:
            (can_replan: bool, reason: str, attempt_count: int)
        """
        if not self.redis:
            return (True, "No rate limiting configured", 0)

        key = f"{self.REPLAN_COUNT_PREFIX}{user_id}:{plan_id}"

        try:
            count_data = await self.redis.get(key)

            if not count_data:
                return (True, "First replan attempt", 0)

            count = int(count_data)

            if count >= MAX_REPLAN_ATTEMPTS:
                return (
                    False,
                    f"Max replan attempts ({MAX_REPLAN_ATTEMPTS}) reached",
                    count,
                )

            # Check rate limit window
            ttl = await self.redis.ttl(key)
            if ttl > 0 and count >= REPLAN_MAX_PER_WINDOW:
                return (
                    False,
                    f"Rate limit ({REPLAN_MAX_PER_WINDOW}/{REPLAN_RATE_LIMIT_WINDOW}s) exceeded",
                    count,
                )

            return (True, "Replan allowed", count)

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return (True, "Rate limit check failed, allowing replan", 0)

    async def record_replan_attempt(self, user_id: UUID, plan_id: UUID):
        """Record a replan attempt for rate limiting"""
        if not self.redis:
            return

        key = f"{self.REPLAN_COUNT_PREFIX}{user_id}:{plan_id}"

        try:
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, REPLAN_RATE_LIMIT_WINDOW)
            await pipe.execute()
        except Exception as e:
            logger.error(f"Failed to record replan attempt: {e}")

    async def resolve_conflict(
        self,
        conflict_result: VersionConflictResult,
        original_plan: ExecutablePlan,
        user_id: UUID,
        session_id: str,
        user_message: str,
        *,
        plan_id: UUID | None = None,
        replan_callback=None,
    ) -> ReplanResult:
        """
        Resolve a version conflict based on the recommendation

        Args:
            conflict_result: The detected conflict
            original_plan: The original plan that has conflict
            user_id: User ID
            session_id: Session ID
            user_message: Original user message for replanning

        Returns:
            ReplanResult with new plan or HITL requirements
        """
        if not conflict_result.has_conflict:
            return ReplanResult(success=True, new_plan=original_plan, reason="No conflict")

        if conflict_result.recommendation == "proceed":
            return ReplanResult(
                success=True,
                new_plan=original_plan,
                reason="Conflict outside affected domains, proceeding with original plan",
            )

        if conflict_result.recommendation == "discard":
            return ReplanResult(
                success=False,
                reason="Low confidence conflict; discarding current plan",
            )

        if conflict_result.recommendation == "hitl":
            return ReplanResult(
                success=False,
                requires_hitl=True,
                hitl_reason=(
                    f"Version conflict with low replan confidence "
                    f"({conflict_result.replan_confidence:.2f}). "
                    f"Changed fields: {conflict_result.changed_fields}"
                ),
            )

        if not plan_id:
            return ReplanResult(
                success=False,
                requires_hitl=True,
                reason="Missing plan_id for conflict resolution",
                hitl_reason="缺少计划ID，无法自动重规划",
            )

        # Auto-replan
        can_replan, reason, attempt_count = await self.can_replan(user_id, plan_id)
        if not can_replan:
            return ReplanResult(
                success=False,
                reason=reason,
                attempt_count=attempt_count,
                requires_hitl=True,
                hitl_reason=f"Replan rate limit reached: {reason}",
            )

        await self.record_replan_attempt(user_id, plan_id)

        if replan_callback:
            try:
                logger.info(f"Attempting auto-replan for plan {plan_id} (attempt {attempt_count + 1})")
                new_plan = await replan_callback()

                return ReplanResult(
                    success=True,
                    new_plan=new_plan,
                    reason="Auto-replanned due to version conflict",
                    attempt_count=attempt_count + 1,
                )

            except Exception as e:
                logger.error(f"Auto-replan failed: {e}")
                return ReplanResult(
                    success=False,
                    reason=f"Replan failed: {str(e)}",
                    attempt_count=attempt_count + 1,
                    requires_hitl=True,
                    hitl_reason=f"Auto-replan failed: {str(e)}",
                )

        return ReplanResult(
            success=False,
            reason="No replanning callback configured",
            requires_hitl=True,
            hitl_reason="Auto-replan not available",
        )

    async def record_conflict_history(
        self,
        user_id: UUID,
        plan_id: UUID,
        conflict_result: VersionConflictResult,
        resolution: ReplanResult,
    ):
        """Record conflict history for analytics and learning"""
        if not self.redis:
            return

        key = f"{self.CONFLICT_HISTORY_PREFIX}{user_id}"

        history_entry = {
            "timestamp": _utcnow().isoformat(),
            "plan_id": str(plan_id),
            "conflict_type": conflict_result.conflict_type,
            "version_delta": abs(
                conflict_result.current_version - conflict_result.expected_version
            ),
            "recommendation": conflict_result.recommendation,
            "resolution_success": resolution.success,
            "required_hitl": resolution.requires_hitl,
        }

        try:
            import json

            await self.redis.lpush(key, json.dumps(history_entry))
            await self.redis.ltrim(key, 0, 99)  # Keep last 100 entries
            await self.redis.expire(key, 86400 * 30)  # 30 days TTL
        except Exception as e:
            logger.error(f"Failed to record conflict history: {e}")


# Singleton instance
version_conflict_service: VersionConflictService | None = None


def get_version_conflict_service(
    redis: Redis | None = None,
    plan_state_service=None,
    planner=None,
) -> VersionConflictService:
    """Get or create the version conflict service singleton"""
    global version_conflict_service

    if version_conflict_service is None:
        version_conflict_service = VersionConflictService(
            redis=redis,
            plan_state_service=plan_state_service,
            planner=planner,
        )

    return version_conflict_service
