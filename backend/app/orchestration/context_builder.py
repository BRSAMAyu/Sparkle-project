"""Context-building mixin for ChatOrchestrator.

Extracts all ``_build_*_context``, ``_merge_*``, ``_get_*`` helpers that
assemble the rich user / conversation / plan context dict consumed by the
prompt builder and LLM calls.

This is a *mixin* -- it relies on attributes that live on the concrete
``ChatOrchestrator`` instance (``self.redis``, ``self.context_pruner``,
``self.state_manager``, etc.).
"""

from __future__ import annotations

import contextlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from google.protobuf.json_format import MessageToDict
from loguru import logger
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.cognitive import CognitiveFragment
from app.models.plan import Plan
from app.models.task import Task
from app.models.task import TaskStatus as ModelTaskStatus
from app.models.task_feedback import TaskFeedback
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.services.focus_service import focus_service
from app.services.self_evolution_service import UnderstandingDepthService
from app.services.perceptible_intelligence_service import (
    PerceptibleInsightService,
)
from app.services.user_service import UserService


# ---------------------------------------------------------------------------
# Helpers (duplicated from orchestrator to avoid circular imports)
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class ContextBuilderMixin:
    """Mixin providing context building methods for ChatOrchestrator."""

    # ------------------------------------------------------------------
    # _build_profile_payload
    # ------------------------------------------------------------------

    def _build_profile_payload(
        self,
        user_context_data: dict[str, Any] | None,
        preferences: dict[str, Any] | None,
        llm_profile_data: dict[str, Any] | None,
        preference_version: int,
        experiment_cohort: str | None,
    ) -> dict[str, Any]:
        identity: dict[str, Any] = {}
        if isinstance(user_context_data, dict):
            flame_level = None
            prefs = user_context_data.get("preferences")
            if isinstance(prefs, dict):
                flame_level = prefs.get("flame_level")
            identity = {
                "nickname": user_context_data.get("nickname", "未知"),
                "timezone": user_context_data.get("timezone", "Asia/Shanghai"),
                "language": user_context_data.get("language", "zh-CN"),
                "is_pro": user_context_data.get("is_pro", False),
                "persona_type": user_context_data.get("persona_type"),
                "flame_level": flame_level,
            }

        prefs = preferences
        if not isinstance(prefs, dict) and isinstance(user_context_data, dict):
            prefs = user_context_data.get("preferences")
        if not isinstance(prefs, dict):
            prefs = {}

        llm_profile = llm_profile_data if isinstance(llm_profile_data, dict) else {}

        return {
            "identity": identity,
            "preferences": prefs,
            "llm_profile": llm_profile,
            "preference_version": preference_version,
            "experiment_cohort": experiment_cohort,
        }

    # ------------------------------------------------------------------
    # _merge_user_contexts
    # ------------------------------------------------------------------

    def _merge_user_contexts(self, local_context: dict[str, Any], grpc_context: dict[str, Any]) -> dict[str, Any]:
        """
        P0: Merge user context from Go Gateway (gRPC) with local context (Python).
        Prioritizes gRPC context as it's more recent (fetched at request time).

        Returns:
            Merged context dict with both sources
        """
        if not grpc_context:
            return local_context

        merged = {}

        # Start with local context as base
        merged.update(local_context)

        # Override with gRPC context (prioritized as more recent)
        if "pending_tasks" in grpc_context:
            merged["next_actions"] = grpc_context["pending_tasks"]  # Normalize field name
        if "active_plans" in grpc_context:
            merged["active_plans"] = grpc_context["active_plans"]
        if "focus_stats" in grpc_context:
            merged["focus_stats"] = grpc_context["focus_stats"]
        if "recent_progress" in grpc_context:
            merged["recent_progress"] = grpc_context["recent_progress"]

        logger.debug(f"Merged context keys: {list(merged.keys())}")
        return merged

    # ------------------------------------------------------------------
    # _get_task_status_summary
    # ------------------------------------------------------------------

    async def _get_task_status_summary(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """Get summary of all tasks for user across all plans."""
        try:
            # Pending count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status == ModelTaskStatus.PENDING
                )
            )
            pending = result.scalar() or 0

            # In progress count
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status == ModelTaskStatus.IN_PROGRESS
                )
            )
            in_progress = result.scalar() or 0

            # Overdue count (pending/in_progress and due_date < now)
            result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date < _utcnow()
                )
            )
            overdue = result.scalar() or 0

            return {
                "pending": pending,
                "in_progress": in_progress,
                "overdue": overdue
            }
        except Exception as e:
            logger.warning(f"Failed to get task status summary: {e}")
            return {"pending": 0, "in_progress": 0, "overdue": 0}

    # ------------------------------------------------------------------
    # _get_cognitive_insights
    # ------------------------------------------------------------------

    async def _get_cognitive_insights(self, user_id: str, db_session: AsyncSession) -> dict[str, Any]:
        """获取认知模式摘要，注入 LLM 上下文

        当用户有已识别的行为模式时，LLM 可以在合适时机主动展示认知棱镜。
        """
        try:
            from uuid import UUID

            from app.services.cognitive_service import CognitiveService

            cognitive = CognitiveService(db_session)
            patterns = await cognitive.get_user_patterns(UUID(user_id), min_confidence=0.6)

            if patterns:
                # 按类型分组
                by_type = {"cognitive": [], "emotional": [], "execution": []}
                for p in patterns:
                    by_type.setdefault(p.pattern_type, []).append(p.pattern_name)

                # Map ORM BehaviorPattern → policy_signals via the canonical map
                from app.services.profile_context_service import ProfileContextService
                policy_map = ProfileContextService.PATTERN_POLICY_MAP
                policy_signals = []
                for p in patterns:
                    normalized = str(p.pattern_name or "").strip().lower()
                    policy_signals.extend(policy_map.get(normalized, []))

                return {
                    "has_cognitive_patterns": True,
                    "pattern_count": len(patterns),
                    "recent_patterns": [p.pattern_name for p in patterns[:3]],
                    "patterns_by_type": {k: len(v) for k, v in by_type.items()},
                    "policy_signals": list(set(policy_signals))
                }
        except Exception as e:
            logger.warning(f"Failed to get cognitive insights for {user_id}: {e}")

        return {"has_cognitive_patterns": False}

    # ------------------------------------------------------------------
    # _get_recent_sentiment_distribution
    # ------------------------------------------------------------------

    async def _get_recent_sentiment_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(CognitiveFragment.sentiment)
                .where(CognitiveFragment.user_id == uuid.UUID(user_id))
                .where(CognitiveFragment.sentiment.isnot(None))
                .order_by(desc(CognitiveFragment.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                sentiment = str(raw or "").strip().lower()
                if not sentiment:
                    continue
                distribution[sentiment] = distribution.get(sentiment, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent sentiment distribution: {e}")
            return {}

    # ------------------------------------------------------------------
    # _get_recent_task_feedback_distribution
    # ------------------------------------------------------------------

    async def _get_recent_task_feedback_distribution(
        self,
        user_id: str,
        db_session: AsyncSession | None,
        window: int = 8,
    ) -> dict[str, int]:
        if not db_session:
            return {}
        try:
            result = await db_session.execute(
                select(TaskFeedback.category)
                .where(TaskFeedback.user_id == uuid.UUID(user_id))
                .where(TaskFeedback.category.isnot(None))
                .order_by(desc(TaskFeedback.created_at))
                .limit(window)
            )
            rows = result.scalars().all()
            distribution: dict[str, int] = {}
            for raw in rows:
                category = str(raw or "").strip().lower()
                if not category:
                    continue
                distribution[category] = distribution.get(category, 0) + 1
            return distribution
        except Exception as e:
            logger.warning(f"Failed to load recent task feedback distribution: {e}")
            return {}

    # ------------------------------------------------------------------
    # _build_user_context
    # ------------------------------------------------------------------

    async def _build_user_context(self, user_id: str, db_session: AsyncSession, session_id: str | None = None) -> dict[str, Any]:
        """
        Build comprehensive user context from UserService

        Returns:
            Dict containing user context and analytics
        """
        try:
            # Pass redis_client to UserService for caching
            user_service = UserService(db_session, self.redis)
            base_user_context = await user_service.get_context(uuid.UUID(user_id))
            base_user_context_data = base_user_context.model_dump() if base_user_context else None
            experiment_cohort = self._experiment_cohort_for_user(user_id)
            returning_context = await self._build_returning_context(
                user_id=user_id,
                session_id=session_id,
                db_session=db_session,
            )
            understanding_depth = None
            if settings.ENABLE_PERCEPTIBLE_INTELLIGENCE:
                with contextlib.suppress(Exception):
                    depth_service = UnderstandingDepthService(db_session, self.redis)
                    understanding_depth = (await depth_service.evaluate(user_id=uuid.UUID(user_id))).__dict__

            # P1: Task Status Summary
            task_status_summary = await self._get_task_status_summary(user_id, db_session)

            llm_profile_data = None
            preference_version = 0
            try:
                from app.services.personalization import get_personalization_engine

                engine = get_personalization_engine(db_session, self.redis)
                llm_profile = await engine.get_llm_profile(uuid.UUID(user_id))
                prefs = await engine.pref_service.get_preferences(uuid.UUID(user_id))
                preference_version = prefs.version
                llm_profile_data = {
                    "system_prompt_additions": llm_profile.system_prompt_additions,
                    "verbosity_target": llm_profile.verbosity_target,
                    "temperature": llm_profile.temperature,
                    "should_ask_clarifying": llm_profile.should_ask_clarifying,
                    "should_provide_examples": llm_profile.should_provide_examples,
                    "exploration_level": llm_profile.exploration_level,
                    "tone": llm_profile.tone,
                }
            except Exception as e:
                logger.warning(f"Failed to build LLM profile: {e}")

            # --- Use ContextOrchestrator (P4) ---
            from app.core.context_manager import ContextOrchestrator

            context_orchestrator = ContextOrchestrator(db_session, self.redis)
            # Fetch aggregated context (cached)
            cognitive_context = await context_orchestrator.get_user_context(user_id)

            profile_context_payload = None

            # Map CognitiveContext to legacy dict format for backward compatibility
            # In future, we should use CognitiveContext object directly in prompt builder

            user_context_data = None
            if cognitive_context:
                # Use data from new orchestrator
                user_context_data = base_user_context_data or {
                    "user_id": user_id,
                    "nickname": "同学",
                }

                # Fetch active plans manually if not in cognitive context yet
                # Active plans (latest 3)
                plans_stmt = (
                    select(Plan)
                    .where(
                        and_(
                            Plan.user_id == uuid.UUID(user_id),
                            Plan.is_active
                        )
                    )
                    .order_by(desc(Plan.created_at))
                    .limit(3)
                )
                plans_result = await db_session.execute(plans_stmt)
                plans = plans_result.scalars().all()
                active_plans = [
                    {
                        "id": str(plan.id),
                        "title": plan.name,
                        "type": plan.type.value,
                        "target_date": plan.target_date.isoformat() if plan.target_date else None,
                        "progress": plan.progress or 0
                    }
                    for plan in plans
                ]

                # P0: 认知棱镜上下文注入
                cognitive_insights = await self._get_cognitive_insights(user_id, db_session)

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=cognitive_context.preferences,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )

                if getattr(cognitive_context, "profile_context", None):
                    profile_context_payload = cognitive_context.profile_context

                return {
                    "user_context": user_context_data, # Legacy field
                    "analytics_summary": cognitive_context.engagement_metrics or {},
                    "preferences": (
                        profile_context_payload.get("preferences")
                        if isinstance(profile_context_payload, dict)
                        else cognitive_context.preferences
                    ),
                    "next_actions": cognitive_context.active_tasks,
                    "active_plans": active_plans,
                    "focus_stats": cognitive_context.focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "experiment_cohort": experiment_cohort,
                    "task_status_summary": task_status_summary,
                    "returning_context": returning_context,
                    "understanding_depth": understanding_depth,
                    "profile": profile_payload,
                    "profile_context": profile_context_payload,

                    # New field for full context injection
                    "cognitive_context": cognitive_context.model_dump(exclude={'user_id', 'timestamp'}),

                    # 认知棱镜数据
                    "cognitive_insights": cognitive_insights
                }

            # Fallback to legacy logic if new orchestrator returns None (shouldn't happen)
            logger.warning(f"ContextOrchestrator returned None for {user_id}, falling back to legacy")

            # ... Legacy Logic ...
            user_context = base_user_context
            analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

            if user_context:
                user_context_data = user_context.model_dump()

            # Next actions (top pending tasks)
            tasks_stmt = (
                select(Task)
                .where(
                    and_(
                        Task.user_id == uuid.UUID(user_id),
                        Task.status == ModelTaskStatus.PENDING
                    )
                )
                .order_by(desc(Task.priority), asc(Task.due_date), desc(Task.created_at))
                .limit(3)
            )
            tasks_result = await db_session.execute(tasks_stmt)
            tasks = tasks_result.scalars().all()
            next_actions = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority
                }
                for task in tasks
            ]

            # Active plans (latest 3)
            plans_stmt = (
                select(Plan)
                .where(
                    and_(
                        Plan.user_id == uuid.UUID(user_id),
                        Plan.is_active
                    )
                )
                .order_by(desc(Plan.created_at))
                .limit(3)
            )
            plans_result = await db_session.execute(plans_stmt)
            plans = plans_result.scalars().all()
            active_plans = [
                {
                    "id": str(plan.id),
                    "title": plan.name,
                    "type": plan.type.value,
                    "target_date": plan.target_date.isoformat() if plan.target_date else None,
                    "progress": plan.progress or 0
                }
                for plan in plans
            ]

            # Focus stats (today)
            focus_stats = await focus_service.get_today_stats(db_session, uuid.UUID(user_id))

            if user_context_data:
                # Handle preferences: could be dict (from cognitive_context) or object (from base_user_context)
                preferences_dict = {}
                if "preferences" in user_context_data:
                    prefs = user_context_data["preferences"]
                    if isinstance(prefs, dict):
                        preferences_dict = prefs
                    elif hasattr(prefs, 'model_dump'):
                        preferences_dict = prefs.model_dump()
                    else:
                        logger.warning(f"Unexpected preferences type: {type(prefs)}")
                elif "user_context" in user_context_data and hasattr(user_context_data["user_context"], "preferences"):
                    # Old structure: preferences is on user_context object
                    prefs = user_context_data["user_context"].preferences
                    if hasattr(prefs, "model_dump"):
                        preferences_dict = prefs.model_dump()
                    else:
                        preferences_dict = {"depth_preference": 0.5, "curiosity_preference": 0.5}

                profile_payload = self._build_profile_payload(
                    user_context_data=user_context_data,
                    preferences=preferences_dict,
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )

                return {
                    "user_context": user_context_data,
                    "analytics_summary": analytics,
                    "preferences": {
                        "depth_preference": preferences_dict.get("depth_preference", 0.5),
                        "curiosity_preference": preferences_dict.get("curiosity_preference", 0.5),
                    },
                    "next_actions": next_actions,
                    "active_plans": active_plans,
                    "focus_stats": focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "experiment_cohort": experiment_cohort,
                    "task_status_summary": task_status_summary,
                    "returning_context": returning_context,
                    "understanding_depth": understanding_depth,
                    "profile": profile_payload,
                }
            else:
                # Fallback to basic context
                logger.warning(f"User {user_id} not found, using fallback context")
                profile_payload = self._build_profile_payload(
                    user_context_data=None,
                    preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                    llm_profile_data=llm_profile_data,
                    preference_version=preference_version,
                    experiment_cohort=experiment_cohort,
                )
                return {
                    "user_context": None,
                    "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                    "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                    "next_actions": next_actions,
                    "active_plans": active_plans,
                    "focus_stats": focus_stats,
                    "preference_version": preference_version,
                    "llm_profile": llm_profile_data,
                    "experiment_cohort": experiment_cohort,
                    "task_status_summary": task_status_summary,
                    "returning_context": returning_context,
                    "understanding_depth": understanding_depth,
                    "profile": profile_payload,
                }

        except Exception as e:
            logger.error(f"Failed to build user context: {e}")
            # Fallback
            return {
                "user_context": None,
                "analytics_summary": {"is_active": True, "engagement_level": "medium"},
                "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
                "preference_version": 0,
                "llm_profile": None,
                "returning_context": None,
                "understanding_depth": None,
                "profile": self._build_profile_payload(
                    user_context_data=None,
                    preferences={"depth_preference": 0.5, "curiosity_preference": 0.5},
                    llm_profile_data=None,
                    preference_version=0,
                    experiment_cohort=self._experiment_cohort_for_user(user_id),
                ),
                "experiment_cohort": self._experiment_cohort_for_user(user_id),
            }

    # ------------------------------------------------------------------
    # _build_returning_context
    # ------------------------------------------------------------------

    async def _build_returning_context(
        self,
        *,
        user_id: str,
        session_id: str | None,
        db_session: AsyncSession,
    ) -> dict[str, Any] | None:
        if not session_id or not self.redis:
            return None
        try:
            redis_key = f"returning-context:{session_id}"
            if await self.redis.exists(redis_key):
                return None

            user_uuid = uuid.UUID(user_id)
            result = await db_session.execute(
                select(ChatSession.last_message_at)
                .where(ChatSession.user_id == user_uuid, ChatSession.last_message_at.is_not(None))
                .order_by(ChatSession.last_message_at.desc())
                .limit(1)
            )
            last_message_at = result.scalar_one_or_none()
            if last_message_at is None:
                return None

            silence_gap = _utcnow() - last_message_at
            if silence_gap < timedelta(days=3):
                return None

            task_result = await db_session.execute(
                select(Task.title, Task.completed_at)
                .where(
                    Task.user_id == user_uuid,
                    Task.status == ModelTaskStatus.COMPLETED,
                    Task.completed_at.is_not(None),
                    Task.completed_at <= last_message_at,
                )
                .order_by(Task.completed_at.desc())
                .limit(1)
            )
            latest_completed = task_result.first()

            overdue_result = await db_session.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == user_uuid,
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date.is_not(None),
                    Task.due_date >= last_message_at.date(),
                    Task.due_date <= _utcnow().date(),
                )
            )
            overdue_count = int(overdue_result.scalar() or 0)

            upcoming_result = await db_session.execute(
                select(Task.title, Task.due_date)
                .where(
                    Task.user_id == user_uuid,
                    Task.status.in_([ModelTaskStatus.PENDING, ModelTaskStatus.IN_PROGRESS]),
                    Task.due_date.is_not(None),
                )
                .order_by(Task.due_date.asc())
                .limit(1)
            )
            next_due = upcoming_result.first()

            progress_text = "你上次离开前还没有留下明确的完成记录。"
            if latest_completed:
                progress_text = f"你上次推进到「{str(latest_completed[0])}」这一步。"
            due_text = f"离开期间有 {overdue_count} 个任务进入截止窗口。"
            if next_due:
                due_text = f"离开期间有 {overdue_count} 个任务进入截止窗口，最近的是「{str(next_due[0])}」。"

            payload = {
                "days_away": max(int(silence_gap.days), 3),
                "last_active_at": last_message_at.isoformat(),
                "last_progress": progress_text,
                "overdue_task_count": overdue_count,
                "next_due_task_title": str(next_due[0]) if next_due else "",
                "welcome_back_message": f"{progress_text}{due_text} 欢迎回来，我们可以从这里继续。",
                "briefing_text": f"{progress_text}{due_text}",
            }
            await self.redis.setex(redis_key, 24 * 60 * 60, "1")
            return payload
        except Exception as exc:
            logger.warning(f"Failed to build returning context: {exc}")
            return None

    # ------------------------------------------------------------------
    # _build_conversation_context
    # ------------------------------------------------------------------

    async def _build_conversation_context(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Build conversation context with ContextPruner

        Returns:
            Dict containing pruned history and summary
        """
        if not self.context_pruner:
            logger.warning("ContextPruner not initialized, returning empty context")
            return {"messages": [], "summary": None}

        try:
            pruned_result = await self.context_pruner.get_pruned_history(
                session_id=session_id,
                user_id=user_id
            )

            logger.debug(
                f"Conversation context for session {session_id}: "
                f"{pruned_result['original_count']} -> {pruned_result['pruned_count']} messages, "
                f"summary_used={pruned_result['summary_used']}"
            )

            return pruned_result

        except Exception as e:
            logger.error(f"Failed to prune conversation history: {e}")
            return {"messages": [], "summary": None}

    # ------------------------------------------------------------------
    # _log_context_injection
    # ------------------------------------------------------------------

    def _log_context_injection(self, user_id: str, context: dict[str, Any] | None) -> None:
        """Log context injection details for observability."""
        if not context or not isinstance(context, dict):
            logger.info("Context injection for user {}: empty", user_id)
            return

        next_actions = context.get("next_actions") or context.get("pending_tasks") or []
        active_plans = context.get("active_plans") or []

        tasks_count = len(next_actions) if isinstance(next_actions, list) else 0
        plans_count = len(active_plans) if isinstance(active_plans, list) else 0

        last_activity = None
        user_ctx = context.get("user_context")
        if isinstance(user_ctx, dict):
            last_activity = user_ctx.get("last_activity_time") or user_ctx.get("last_login")

        if not last_activity and isinstance(context.get("analytics_summary"), dict):
            last_activity = context["analytics_summary"].get("last_login") or context["analytics_summary"].get("last_activity_time")

        logger.info(
            "Context injection for user {}: {} tasks, {} plans, last_activity={}",
            user_id,
            tasks_count,
            plans_count,
            last_activity
        )

    # ------------------------------------------------------------------
    # _build_full_context
    # ------------------------------------------------------------------

    async def _build_full_context(
        self,
        *,
        request: agent_service_pb2.ChatRequest,
        active_db: AsyncSession | None,
        user_id: str,
        session_id: str,
        user_message: str,
        request_id: str,
        tracer,
    ) -> tuple[dict[str, Any], uuid.UUID | None, bool, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        grpc_context = {}
        if request.user_profile and request.user_profile.extra_context:
            try:
                grpc_context = json.loads(request.user_profile.extra_context)
                logger.debug(f"Parsed extra_context from gRPC: {list(grpc_context.keys())}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extra_context JSON: {e}")

        request_context = {}
        if request.HasField("extra_context"):
            try:
                request_context = MessageToDict(request.extra_context)
                if request_context:
                    logger.debug(f"Parsed request extra_context: {list(request_context.keys())}")
            except Exception as e:
                logger.warning(f"Failed to parse request extra_context: {e}")

        if request_context:
            grpc_context = {**grpc_context, **request_context}

        plan_id = None
        if grpc_context and "plan_id" in grpc_context:
            with contextlib.suppress(ValueError, AttributeError):
                plan_id = uuid.UUID(grpc_context["plan_id"])

        plan_switched = False
        if not plan_id and user_message and active_db:
            with tracer.start_as_current_span("orchestrator.auto_switch_plan"):
                try:
                    from app.services.plan_matching_service import PlanMatchingService
                    plan_matching = PlanMatchingService(active_db)
                    matched_plan_id = await self.state_manager.auto_switch_plan(
                        session_id=session_id,
                        user_id=uuid.UUID(user_id),
                        task_context={
                            "content": user_message,
                            "type": grpc_context.get("task_type", "chat"),
                        },
                        db_session=active_db,
                        plan_matching_service=plan_matching,
                    )
                    if matched_plan_id:
                        plan_id = matched_plan_id
                        plan_switched = True
                        logger.info(f"Auto-switched to plan {plan_id} based on message content")
                except Exception as e:
                    logger.warning(f"Auto-switch plan failed: {e}")

        overlay_versions = {}
        if grpc_context:
            versions = grpc_context.get("realtime_versions")
            if isinstance(versions, dict):
                overlay_versions = {str(k): str(v) for k, v in versions.items()}
        if overlay_versions:
            await self._self_heal_versions(user_id, overlay_versions, active_db)

        if grpc_context and ("realtime_versions" in grpc_context or "overlay_generated_at" in grpc_context):
            grpc_context = dict(grpc_context)
            grpc_context.pop("realtime_versions", None)
            grpc_context.pop("overlay_generated_at", None)

        user_context_payload = None
        conversation_context = None
        plan_context = None
        with tracer.start_as_current_span("db.build_context"):
            if active_db and user_id:
                local_context = await self._build_user_context(user_id, active_db, session_id=session_id)
                user_context_payload = self._merge_user_contexts(local_context, grpc_context)
                logger.info(f"Merged user context: {user_context_payload is not None}")

                if plan_id:
                    try:
                        from app.core.plan_context import PlanContextBuilder
                        from app.services.plan_state_service import PlanStateService

                        plan_builder = PlanContextBuilder(active_db, self.redis)
                        plan_context = await plan_builder.build_enriched(uuid.UUID(user_id), plan_id)
                        if plan_context:
                            logger.info(f"Built plan_context for plan_id={plan_id}")
                            if user_context_payload is None:
                                user_context_payload = {}
                            user_context_payload["plan_context"] = plan_context

                            try:
                                plan_state_svc = PlanStateService(active_db, self.redis)
                                plan_state = await plan_state_svc.get_plan_state(
                                    uuid.UUID(user_id), uuid.UUID(plan_id)
                                )
                                if plan_state and plan_state.constraints.get("require_phase_rollback"):
                                    logger.info(f"Phase rollback triggered for plan_id={plan_id}")
                                    await plan_state_svc.upsert_plan_state(
                                        user_id=uuid.UUID(user_id),
                                        plan_id=uuid.UUID(plan_id),
                                        patch={"constraints": {"require_phase_rollback": False}},
                                        bump_version=False,
                                    )
                                    plan_context["mode"] = "phase_rollback"
                                    plan_context["rollback_reason"] = "2次连续拒绝，需重新收集信息"
                                    if plan_state.feedback_log:
                                        plan_context["previous_feedback"] = plan_state.feedback_log[-2:]
                            except Exception as e:
                                logger.warning(f"Failed to check phase rollback: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to build plan context: {e}")

                try:
                    user_uuid = uuid.UUID(user_id)
                    router = ToolPreferenceRouter(active_db, user_uuid, self.redis)
                    preferred_tools = await router.get_preferred_tools(limit=3)
                    if preferred_tools:
                        if user_context_payload is not None:
                            user_context_payload["preferred_tools"] = preferred_tools
                        logger.info(f"Injected tool preferences for user {user_id}: {preferred_tools}")
                except Exception as e:
                    logger.warning(f"Failed to get tool preferences (non-fatal): {e}")
                    if active_db:
                        await active_db.rollback()
            elif grpc_context:
                user_context_payload = grpc_context
                logger.info("Using gRPC context without local DB context")

        self._log_context_injection(user_id, user_context_payload)
        if self.context_pruner:
            with tracer.start_as_current_span("db.build_conversation_context"):
                conversation_context = await self._build_conversation_context(session_id, user_id)

        if active_db and user_message:
            try:
                user_msg = ChatMessage(
                    user_id=uuid.UUID(str(user_id)),
                    session_id=self._coerce_session_uuid(session_id),
                    role=MessageRole.USER,
                    content=user_message,
                    message_id=request_id,
                )
                active_db.add(user_msg)
                await active_db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist user chat message: {e}")
                with contextlib.suppress(Exception):
                    await active_db.rollback()

        return grpc_context, plan_id, plan_switched, user_context_payload, conversation_context, plan_context
