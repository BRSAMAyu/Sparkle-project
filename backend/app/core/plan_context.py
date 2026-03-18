from __future__ import annotations
"""
PlanContextBuilder - 计划级上下文构建器

Builds plan-level context from PlanState for injection into ContextPack.
Implements the PlanScope layer as defined in docs/state/plan_state_spec.md.

Usage:
    from app.core.plan_context import PlanContextBuilder

    builder = PlanContextBuilder(db, redis)
    plan_context = await builder.build(user_id, plan_id)

    # With UserScope cognitive profile injection
    enriched_context = await builder.build_enriched(user_id, plan_id)
"""

from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.services.plan_state_service import PlanStateService

# Default budget for plan_context section (tokens)
PLAN_CONTEXT_DEFAULT_BUDGET = 500


def _utcnow() -> datetime:
    """Return a naive UTC datetime for compatibility with current DB column types."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        plan_id: UUID | None,
        include_task_index: bool = True,
        include_recent_tasks: bool = True,
        include_feedback_log: bool = False,
        max_milestones: int = 5,
        max_feedback_entries: int = 10,
        max_recent_tasks: int = 5,
    ) -> dict[str, Any]:
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
        context: dict[str, Any] = {
            "plan_id": str(plan_id),
            "version": state.version,
            "status": state.status,
        }

        # Include plan metadata for prompt readability
        try:
            plan_result = await self.db.execute(
                select(Plan).where(
                    Plan.id == plan_id,
                    Plan.user_id == user_id,
                    Plan.deleted_at.is_(None),
                )
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                context.update(
                    {
                        "plan_title": plan.name,
                        "plan_type": plan.type.value if plan.type else None,
                        "plan_stage": plan.plan_stage.value if plan.plan_stage else None,
                        "target_date": plan.target_date.isoformat() if plan.target_date else None,
                        "progress": plan.progress,
                        "is_active": plan.is_active,
                        "plan_description": plan.description,
                    }
                )
                if plan.description:
                    context["goal"] = plan.description
        except Exception as e:
            logger.warning(f"Failed to fetch plan metadata for plan_id={plan_id}: {e}")

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
            summaries = (state.task_summaries or [])[:max_recent_tasks]
            context["task_summaries"] = summaries
            context["recent_tasks"] = summaries

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
        plan_id: UUID | None,
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

    async def build_enriched(
        self,
        user_id: UUID,
        plan_id: UUID | None,
        include_cognitive_profile: bool = True,
        include_behavior_patterns: bool = True,
        max_behavior_patterns: int = 5,
    ) -> dict[str, Any]:
        """
        Build plan context enriched with UserScope cognitive insights.

        This implements the priority merge: PlanScope > UserScope
        - Plan-level facts take precedence
        - User cognitive patterns provide background context

        Args:
            user_id: Owner user ID
            plan_id: Plan ID (None returns empty context)
            include_cognitive_profile: Whether to include cognitive state snapshot
            include_behavior_patterns: Whether to include behavior patterns
            max_behavior_patterns: Maximum number of behavior patterns to include

        Returns:
            Enriched plan context with user_profile section
        """
        # Get base plan context
        base_context = await self.build(user_id, plan_id, include_feedback_log=True)

        if not include_cognitive_profile and not include_behavior_patterns:
            return base_context

        enriched = dict(base_context)
        user_profile: dict[str, Any] = {}

        # Fetch cognitive state snapshot
        if include_cognitive_profile:
            try:
                from app.models.user_state import UserStateSnapshot

                # Get the most recent snapshot from the last 24 hours
                cutoff = _utcnow() - timedelta(hours=24)
                result = await self.db.execute(
                    select(UserStateSnapshot)
                    .where(UserStateSnapshot.user_id == user_id)
                    .where(UserStateSnapshot.snapshot_at >= cutoff)
                    .order_by(desc(UserStateSnapshot.snapshot_at))
                    .limit(1)
                )
                snapshot = result.scalar_one_or_none()

                if snapshot:
                    user_profile["cognitive_state"] = {
                        "cognitive_load": snapshot.cognitive_load,
                        "interruptibility": snapshot.interruptibility,
                        "strain_index": snapshot.strain_index,
                        "focus_mode": snapshot.focus_mode,
                        "sprint_mode": snapshot.sprint_mode,
                        "snapshot_time": snapshot.snapshot_at.isoformat() if snapshot.snapshot_at else None,
                    }

                    # Include time context if available
                    if snapshot.time_context:
                        user_profile["time_context"] = snapshot.time_context

            except Exception as e:
                logger.warning(f"Failed to fetch cognitive state: {e}")

        # Fetch behavior patterns
        if include_behavior_patterns:
            try:
                from app.models.cognitive import BehaviorPattern

                # Get active (non-archived) behavior patterns with high confidence
                result = await self.db.execute(
                    select(BehaviorPattern)
                    .where(BehaviorPattern.user_id == user_id)
                    .where(not BehaviorPattern.is_archived)
                    .order_by(
                        desc(BehaviorPattern.confidence_score),
                        desc(BehaviorPattern.frequency)
                    )
                    .limit(max_behavior_patterns)
                )
                patterns = result.scalars().all()

                if patterns:
                    user_profile["behavior_patterns"] = [
                        {
                            "pattern_name": p.pattern_name,
                            "pattern_type": p.pattern_type,
                            "confidence": p.confidence_score,
                            "frequency": p.frequency,
                            "description": p.description[:150] if p.description else None,
                            "solution_hint": p.solution_text[:100] if p.solution_text else None,
                        }
                        for p in patterns
                    ]

                    # Derive learning style from patterns
                    user_profile["derived_insights"] = self._derive_insights_from_patterns(patterns)

            except Exception as e:
                logger.warning(f"Failed to fetch behavior patterns: {e}")

        # Fetch user preferences from preferences center
        try:
            from app.services.personalization.preference_service import PreferenceService

            pref_service = PreferenceService(self.db, self.redis)
            prefs = await pref_service.get_preferences(user_id)

            if prefs:
                # Merge explicit and inferred preferences
                explicit = prefs.explicit or {}
                inferred = prefs.inferred or {}
                user_profile["preferences_snapshot"] = {
                    "learning_style": explicit.get("learning_style", "balanced"),
                    "feedback_style": explicit.get("feedback_style", "balanced"),
                    "focus_duration_preference": explicit.get("focus_duration_preference", 25),
                    "ai_verbosity": explicit.get("ai_verbosity", "balanced"),
                    # Include inferred insights if available
                    "inferred_difficulty": inferred.get("difficulty_preference"),
                    "inferred_session_length": inferred.get("session_length_preference"),
                }
        except Exception as e:
            logger.debug(f"User preferences not available: {e}")

        # Add user_profile to enriched context
        if user_profile:
            enriched["user_profile"] = user_profile

        logger.debug(
            f"Built enriched plan context: plan_id={plan_id}, "
            f"has_cognitive_state={'cognitive_state' in user_profile}, "
            f"behavior_patterns_count={len(user_profile.get('behavior_patterns', []))}"
        )

        return enriched

    def _derive_insights_from_patterns(self, patterns: list) -> dict[str, Any]:
        """
        Derive learning insights from behavior patterns.

        Args:
            patterns: List of BehaviorPattern objects

        Returns:
            Derived insights dict
        """
        insights: dict[str, Any] = {}

        pattern_types = [p.pattern_type for p in patterns]
        pattern_names = [p.pattern_name.lower() for p in patterns]

        # Detect planning issues
        planning_patterns = [n for n in pattern_names if "plan" in n or "估" in n]
        if planning_patterns:
            insights["planning_tendency"] = "optimistic" if any("乐观" in n or "低估" in n for n in planning_patterns) else "conservative"

        # Detect focus issues
        focus_patterns = [n for n in pattern_names if "专注" in n or "分心" in n or "focus" in n]
        if focus_patterns:
            insights["focus_tendency"] = "easily_distracted" if any("分心" in n or "distract" in n for n in focus_patterns) else "focused"

        # Detect emotional patterns
        emotional_count = pattern_types.count("emotional")
        cognitive_count = pattern_types.count("cognitive")
        execution_count = pattern_types.count("execution")

        if emotional_count > cognitive_count and emotional_count > execution_count:
            insights["primary_challenge_area"] = "emotional"
        elif cognitive_count > execution_count:
            insights["primary_challenge_area"] = "cognitive"
        elif execution_count > 0:
            insights["primary_challenge_area"] = "execution"

        return insights


def merge_plan_context(
    user_context: dict[str, Any],
    plan_context: dict[str, Any],
) -> dict[str, Any]:
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
