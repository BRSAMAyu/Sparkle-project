"""
PlanContextBuilder - 计划级上下文构建器

Builds plan-level context from PlanState for injection into ContextPack.
Implements the PlanScope layer as defined in docs/state/plan_state_spec.md.

Usage:
    from app.core.plan_context import PlanContextBuilder

    builder = PlanContextBuilder(db, redis)
    plan_context = await builder.build(user_id, plan_id)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plan_state_service import PlanStateService


# Default budget for plan_context section (tokens)
PLAN_CONTEXT_DEFAULT_BUDGET = 500


class PlanContextBuilder:
    """
    Builds plan-level context for injection into ContextPack.

    Design principles:
    1. Lightweight output: Only include essential fields
    2. Graceful degradation: Return empty dict if plan_id is None
    3. Cache-aware: Leverages PlanStateService's Redis caching
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
    ) -> None:
        self.db = db
        self.redis = redis
        self._plan_state_service = PlanStateService(db, redis)

    async def build(
        self,
        user_id: UUID,
        plan_id: Optional[UUID],
        include_task_index: bool = True,
        include_recent_tasks: bool = True,
        include_feedback_log: bool = False,
        max_milestones: int = 5,
        max_feedback_entries: int = 10,
        max_recent_tasks: int = 5,
    ) -> Dict[str, Any]:
        """
        Build plan context from PlanState.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID (None returns empty context)
            include_task_index: Whether to include task_index
            include_feedback_log: Whether to include feedback_log
            max_milestones: Maximum milestones to include
            max_feedback_entries: Maximum feedback entries to include

        Returns:
            Plan context dictionary for injection
        """
        # Graceful degradation: no plan_id means no plan context
        if plan_id is None:
            return {}

        try:
            state = await self._plan_state_service.get_plan_state(user_id, plan_id)
        except Exception as e:
            logger.warning(f"Failed to fetch plan state for plan_id={plan_id}: {e}")
            return {}

        if state is None:
            return {}

        # Build lightweight context
        context: Dict[str, Any] = {
            "plan_id": str(plan_id),
            "version": state.version,
            "status": state.status,
        }

        # Include facts (always included - core of plan context)
        if state.facts:
            context["facts"] = state.facts

        # Include constraints (runtime constraints)
        if state.constraints:
            context["constraints"] = state.constraints

        # Include milestones (truncated)
        if state.milestones:
            milestones = state.milestones[-max_milestones:]  # Most recent
            context["milestones"] = [
                {
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "achieved_at": m.get("achieved_at"),
                }
                for m in milestones
            ]

        # Include task_index (summary stats)
        if include_task_index and state.task_index:
            task_index = state.task_index
            context["task_summary"] = {
                "total": task_index.get("total", 0),
                "completed": task_index.get("completed", 0),
                "avg_completion_rate": task_index.get("avg_completion_rate"),
            }
            # Include by_type summary if present
            by_type = task_index.get("by_type", {})
            if by_type:
                context["task_summary"]["by_type"] = {
                    k: {"total": v.get("total", 0), "completed": v.get("completed", 0)}
                    for k, v in by_type.items()
                }

        # Include recent task summaries (lightweight)
        if include_recent_tasks and state.task_summaries:
            context["recent_tasks"] = (state.task_summaries or [])[:max_recent_tasks]

        # Include feedback_log (optional, truncated)
        if include_feedback_log and state.feedback_log:
            feedback_log = state.feedback_log[-max_feedback_entries:]
            context["recent_feedback"] = [
                {
                    "type": f.get("type"),
                    "content": f.get("content"),
                    "timestamp": f.get("timestamp"),
                }
                for f in feedback_log
            ]

        logger.debug(
            f"Built plan context: plan_id={plan_id}, "
            f"fields={list(context.keys())}"
        )
        return context

    async def build_for_prompt(
        self,
        user_id: UUID,
        plan_id: Optional[UUID],
    ) -> str:
        """
        Build plan context as formatted string for prompt injection.

        Args:
            user_id: Owner user ID
            plan_id: Plan ID

        Returns:
            Formatted string for prompt, or empty string if no context
        """
        context = await self.build(user_id, plan_id)

        if not context:
            return ""

        lines = ["## 当前计划上下文"]

        # Plan status
        lines.append(f"计划ID: {context.get('plan_id')}")
        lines.append(f"状态: {context.get('status')}")

        # Facts
        facts = context.get("facts", {})
        if facts:
            lines.append("\n### 计划事实")
            for key, value in facts.items():
                lines.append(f"- {key}: {value}")

        # Task summary
        task_summary = context.get("task_summary")
        if task_summary:
            total = task_summary.get("total", 0)
            completed = task_summary.get("completed", 0)
            rate = task_summary.get("avg_completion_rate")
            rate_str = f" ({rate:.0%})" if rate is not None else ""
            lines.append(f"\n### 任务进度: {completed}/{total}{rate_str}")

        # Milestones
        milestones = context.get("milestones", [])
        if milestones:
            lines.append("\n### 已达成里程碑")
            for m in milestones:
                lines.append(f"- {m.get('title')}")

        # Constraints
        constraints = context.get("constraints", {})
        if constraints:
            lines.append("\n### 运行时约束")
            for key, value in constraints.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)


def merge_plan_context(
    user_context: Dict[str, Any],
    plan_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge plan context into user context following priority rules.

    Priority: Runtime > Plan > User
    - Plan-level facts override user-level defaults
    - Explicit values override inferred values

    Args:
        user_context: User-level context
        plan_context: Plan-level context

    Returns:
        Merged context with plan context taking precedence
    """
    if not plan_context:
        return user_context

    merged = dict(user_context)

    # Inject plan_context as a separate section
    merged["plan_context"] = plan_context

    # Merge specific fields with priority
    plan_facts = plan_context.get("facts", {})

    # Override preferences with plan-level facts if they exist
    if "preferences" in merged and plan_facts:
        prefs = dict(merged["preferences"])
        # Plan-level preference overrides
        if "difficulty_preference" in plan_facts:
            prefs["difficulty_preference"] = plan_facts["difficulty_preference"]
        if "session_length_preference" in plan_facts:
            prefs["session_length_preference"] = plan_facts["session_length_preference"]
        merged["preferences"] = prefs

    return merged
