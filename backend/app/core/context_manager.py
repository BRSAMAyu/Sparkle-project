from __future__ import annotations
import asyncio
import json
from collections import defaultdict
from datetime import date, timedelta, timezone, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import Integer, cast, func, select
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.achievement import Achievement, AchievementRarity, UserAchievement
from app.models.calendar_event import CalendarEvent
from app.models.community import Group, GroupMember, GroupTaskClaim
from app.schemas.error_book import ErrorQueryParams
from app.schemas.task import TaskListQuery, TaskStatus
from app.services.error_book_service import ErrorBookService
from app.services.focus_service import focus_service
from app.services.galaxy_service import GalaxyService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService
from app.services.task_service import TaskService
from app.services.user_service import UserService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CognitiveContext(BaseModel):
    """
    User's aggregated cognitive context for LLM injection.
    Reflects the 'Learning Profile' of the user.
    """
    user_id: str
    timestamp: datetime

    # Knowledge State (Galaxy)
    knowledge_stats: dict[str, Any] = Field(default_factory=dict, description="Overall mastery and stats")
    recent_mastery_changes: list[dict[str, Any]] = Field(default_factory=list, description="Recently mastered nodes")

    # Problem Areas (Error Book)
    error_summary: dict[str, Any] = Field(default_factory=dict, description="Review stats and weak subjects")
    recent_errors: list[dict[str, Any]] = Field(default_factory=list, description="Recent error records for context")

    # Task & Goals (Task/Plan)
    active_tasks: list[dict[str, Any]] = Field(default_factory=list, description="Current pending tasks")
    focus_stats: dict[str, Any] = Field(default_factory=dict, description="Today's focus performance")

    # User Profile (User)
    preferences: dict[str, Any] = Field(default_factory=dict, description="Learning preferences")
    engagement_metrics: dict[str, Any] = Field(default_factory=dict, description="Engagement level and patterns")
    community_context: dict[str, Any] = Field(default_factory=dict, description="Active community participation snapshot")
    social_context: dict[str, Any] = Field(default_factory=dict, description="Stage 17 isolated social context namespace")
    profile_context: dict[str, Any] | None = Field(default=None, description="Unified profile context payload")
    achievement_summary: dict[str, Any] = Field(default_factory=dict, description="Read-only achievement summary")
    calendar_context: dict[str, Any] = Field(default_factory=dict, description="Read-only calendar constraints")

    # Preference Version (for cache invalidation)
    preference_version: int = Field(default=0, description="Preference version for cache validation")

    def to_llm_system_prompt_context(self) -> str:
        """Convert to a string representation suitable for System Prompt injection"""
        # Compact representation
        return json.dumps(self.model_dump(mode='json', exclude={'user_id', 'timestamp'}), ensure_ascii=False)


class ContextOrchestrator:
    """
    Orchestrates the gathering of user context from multiple services.
    Uses Redis for caching snapshots to ensure low latency for Chat API.
    """

    CACHE_TTL_SECONDS = 300  # 5 minutes cache
    COMMUNITY_CONTEXT_ALLOWED_FIELDS = frozenset(
        {
            "active_group_count",
            "active_group_types",
            "sprint_progress",
            "recent_interaction",
            "has_pending_group_tasks",
            "pending_group_task_count",
            "summary_lines",
        }
    )

    def __init__(self, db_session: AsyncSession, redis_client):
        self.db = db_session
        self.redis = redis_client

        # Initialize Services
        self.galaxy_service = GalaxyService(db_session)
        self.error_book_service = ErrorBookService(db_session)
        # TaskService is static, but we can wrap if needed. Using static methods directly in _get_task_profile
        # UserService needs instance
        self.user_service = UserService(db_session, redis_client)
        self.preference_service = PreferenceService(db_session, redis_client)
        self.profile_context_service = ProfileContextService(db_session, redis_client)

    def _get_error_book_service(self, db_session: AsyncSession | None = None) -> ErrorBookService:
        db = db_session or self.db
        if db is self.db:
            return self.error_book_service
        return ErrorBookService(db)

    def _get_user_service(self, db_session: AsyncSession | None = None) -> UserService:
        db = db_session or self.db
        if db is self.db:
            return self.user_service
        return UserService(db, self.redis)

    def _get_preference_service(self, db_session: AsyncSession | None = None) -> PreferenceService:
        db = db_session or self.db
        if db is self.db:
            return self.preference_service
        return PreferenceService(db, self.redis)

    def _get_profile_context_service(self, db_session: AsyncSession | None = None) -> ProfileContextService:
        db = db_session or self.db
        if db is self.db:
            return self.profile_context_service
        return ProfileContextService(db, self.redis)

    async def get_user_context(self, user_id: str, force_refresh: bool = False) -> CognitiveContext:
        """
        Get aggregated user context.
        Tries cache first, then gathers from services in parallel.

        Version-aware caching: if preference version has changed, force refresh.
        """
        if not force_refresh:
            cached = await self._get_cached_context(user_id)
            if cached:
                # 验证偏好版本是否一致
                current_version = await self._get_preference_version(user_id)
                if cached.preference_version == current_version:
                    return cached
                # 版本不一致，需要刷新
                logger.info(f"Preference version changed for user {user_id}: "
                           f"cached={cached.preference_version}, current={current_version}, refreshing context")

        uid = UUID(user_id)

        # ✅ Fix C3: Create independent DB sessions for each parallel task
        # This prevents shared session issues when tasks run concurrently
        async def _with_session(coro):
            """Execute coroutine in an independent DB session."""
            # Create a new session factory using the same bind
            session_factory = async_sessionmaker(bind=self.db.bind, expire_on_commit=False)
            async with session_factory() as session:
                return await coro(session)

        # Parallel Execution of independent context gathering
        # We protect against individual service failures to return at least partial context
        results = await asyncio.gather(
            _with_session(lambda db: self._get_profile_context(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_error_profile(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_task_profile(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_user_metrics(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_community_profile(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_achievement_context(uid, db)),  # type: ignore[misc]
            _with_session(lambda db: self._get_calendar_context(uid, db)),  # type: ignore[misc]
            return_exceptions=True
        )

        # Unpack results
        profile_context = self._handle_result(results[0], "profile_context", None)
        error_data = self._handle_result(results[1], "error", {})
        task_data = self._handle_result(results[2], "task", {})
        metrics_data = self._handle_result(results[3], "metrics", {})
        community_data = self._handle_result(results[4], "community", {})
        achievement_data = self._handle_result(results[5], "achievement", {})
        calendar_data = self._handle_result(results[6], "calendar", {})

        knowledge_summary = {}
        preference_version = 0
        preferences = {}
        profile_context_payload = None
        if profile_context is not None:
            profile_context_payload = profile_context.to_prompt_context()
            preferences = profile_context.preferences or {}
            preference_version = profile_context.preference_version or 0
            knowledge_summary = (profile_context.knowledge_summary.model_dump(mode="json")
                                 if profile_context.knowledge_summary else {})

        # Construct Context Object
        context = CognitiveContext(
            user_id=user_id,
            timestamp=_utcnow(),

            knowledge_stats={
                "overall_mastery": knowledge_summary.get("overall_mastery", 0.0),
                "active_learning_subjects": knowledge_summary.get("active_learning_subjects", []),
                "weak_spots": knowledge_summary.get("weak_spots", []),
            },
            recent_mastery_changes=knowledge_summary.get("recent_mastery_changes", []),

            error_summary=error_data.get("summary", {}),
            recent_errors=error_data.get("recent", []),

            active_tasks=task_data.get("tasks", []),
            focus_stats=task_data.get("focus", {}),

            preferences=preferences,
            engagement_metrics=metrics_data or {},
            community_context=self._assert_allowed_community_context(community_data or {}),
            social_context={},
            profile_context=profile_context_payload,
            achievement_summary=achievement_data or {},
            calendar_context=calendar_data or {},

            # 记录偏好版本用于缓存验证
            preference_version=preference_version,
        )

        context = self._sanitize_context(context)

        # Cache the result
        await self._cache_context(user_id, context)

        return context

    def _sanitize_context(self, context: CognitiveContext) -> CognitiveContext:
        sensitive_keys = {"email", "phone", "device_id", "ip_address", "raw_content", "sensitive_tags"}
        def _clean(data: dict[str, Any]) -> dict[str, Any]:
            return {k: v for k, v in data.items() if k not in sensitive_keys}

        context.preferences = _clean(context.preferences)
        context.engagement_metrics = _clean(context.engagement_metrics)
        context.achievement_summary = _clean(context.achievement_summary)
        context.calendar_context = _clean(context.calendar_context)
        return context

    def _assert_allowed_community_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        unexpected = sorted(set(payload.keys()) - set(self.COMMUNITY_CONTEXT_ALLOWED_FIELDS))
        if unexpected:
            raise ValueError(f"community_context field whitelist violated: {unexpected}")
        return payload

    def _handle_result(self, result, name: str, default: Any) -> Any:
        if isinstance(result, Exception):
            logger.error(f"Failed to gather {name} context: {result}")
            return default
        return result

    async def _get_cached_context(self, user_id: str) -> CognitiveContext | None:
        if not self.redis:
            return None
        try:
            key = f"user:context:snapshot:{user_id}"
            data = await self.redis.get(key)
            if data:
                json_data = json.loads(data)
                return CognitiveContext(**json_data)
        except Exception as e:
            logger.warning(f"Cache get failed for user context: {e}")
        return None

    async def _cache_context(self, user_id: str, context: CognitiveContext):
        if not self.redis:
            return
        try:
            key = f"user:context:snapshot:{user_id}"
            data = context.model_dump_json()
            await self.redis.setex(key, self.CACHE_TTL_SECONDS, data)
        except Exception as e:
            logger.warning(f"Cache set failed for user context: {e}")

    # --- Sub-fetchers ---

    async def _get_knowledge_profile(self, user_id: UUID) -> dict[str, Any]:
        """Fetch Galaxy stats and recent mastery"""
        # 1. Stats
        stats_model = await self.galaxy_service.stats.calculate_user_stats(user_id)
        stats = stats_model.dict() if stats_model else {}

        # 2. Recent Mastery (This might require a specialized query in GalaxyService or StatsService)
        # For now, we can infer or leave empty if not easily available without custom query.
        # Assuming we might want to add a method to GalaxyService later for "recent updates".
        recent = []

        return {
            "stats": stats,
            "recent": recent
        }

    async def _get_error_profile(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        """Fetch Error Book stats and recent errors"""
        service = self._get_error_book_service(db_session)
        # 1. Stats
        stats = await service.get_review_stats(user_id)

        # 2. Recent Errors (Top 5 pending review or just created)
        # We want "Recent High Frequency Errors" or just "Recent Errors"
        errors, _ = await service.list_errors(
            user_id,
            ErrorQueryParams(page=1, page_size=5, need_review=False) # Just latest
        )

        recent_errors_data = []
        for e in errors:
            recent_errors_data.append({
                "id": str(e.id),
                "question_preview": e.question_text[:50] if e.question_text else "Image Question",
                "subject": e.subject_code,
                "error_type": e.latest_analysis.get("error_type_label") if e.latest_analysis else "Unknown",
                "mastery": e.mastery_level
            })

        return {
            "summary": stats,
            "recent": recent_errors_data
        }

    async def _get_task_profile(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        """Fetch Active Tasks and Focus Stats"""
        # Use provided session or fall back to self.db
        db = db_session if db_session is not None else self.db
        # 1. Active Tasks
        tasks, _ = await TaskService.get_multi(
            db,
            user_id,
            TaskListQuery(page=1, page_size=5, status=TaskStatus.PENDING)
        )

        active_tasks_data = []
        for t in tasks:
            active_tasks_data.append({
                "id": str(t.id),
                "title": t.title,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "type": t.type.value
            })

        # 2. Focus Stats
        focus = await focus_service.get_today_stats(db, user_id)

        return {
            "tasks": active_tasks_data,
            "focus": focus
        }

    async def _get_user_profile(self, user_id: UUID) -> dict[str, Any]:
        """Fetch User Context and Analytics"""
        service = self._get_user_service()
        # 1. Context
        user_ctx = await service.get_context(user_id)
        preferences = {}
        if user_ctx and user_ctx.preferences:
            preferences = user_ctx.preferences

        # 2. Analytics
        analytics = await service.get_analytics_summary(user_id)

        return {
            "preferences": preferences,
            "metrics": analytics
        }

    async def _get_user_metrics(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        """Fetch analytics metrics only."""
        return await self._get_user_service(db_session).get_analytics_summary(user_id)

    async def _get_profile_context(self, user_id: UUID, db_session: AsyncSession | None = None):
        return await self._get_profile_context_service(db_session).get_profile_context(user_id)

    async def _get_achievement_context(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        db = db_session if db_session is not None else self.db
        recent_cutoff = _utcnow() - timedelta(days=14)

        recent_result = await db.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, Achievement.id == UserAchievement.achievement_id)
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.is_not(None),
                UserAchievement.unlocked_at >= recent_cutoff,
            )
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(5)
        )

        progress_result = await db.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, Achievement.id == UserAchievement.achievement_id)
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.is_(None),
                UserAchievement.progress > 0.5,
            )
            .order_by(UserAchievement.progress.desc(), UserAchievement.last_progress_update.desc().nullslast())
            .limit(5)
        )

        score_result = await db.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, Achievement.id == UserAchievement.achievement_id)
            .where(UserAchievement.user_id == user_id)
        )

        recent_unlocks = [
            {
                "achievement_id": achievement.id,
                "name": achievement.name,
                "rarity": (
                    achievement.rarity.value
                    if hasattr(achievement.rarity, "value")
                    else str(achievement.rarity or "common")
                ),
                "unlocked_at": user_achievement.unlocked_at.isoformat() if user_achievement.unlocked_at else None,
            }
            for user_achievement, achievement in recent_result.all()
        ]
        in_progress = [
            {
                "achievement_id": achievement.id,
                "name": achievement.name,
                "progress": round(float(user_achievement.progress or 0.0), 3),
                "progress_value": int(user_achievement.progress_value or 0),
                "progress_target": int(user_achievement.progress_target or 0),
            }
            for user_achievement, achievement in progress_result.all()
        ]

        rarity_weights = {
            AchievementRarity.COMMON.value: 1.0,
            AchievementRarity.RARE.value: 2.0,
            AchievementRarity.EPIC.value: 3.0,
            AchievementRarity.LEGENDARY.value: 4.0,
        }
        total_score = 0.0
        for user_achievement, achievement in score_result.all():
            rarity = achievement.rarity.value if hasattr(achievement.rarity, "value") else str(achievement.rarity or "common")
            weight = rarity_weights.get(rarity, 1.0)
            progress = float(user_achievement.progress or 0.0)
            total_score += weight if user_achievement.unlocked_at else (progress * weight)

        if not recent_unlocks and not in_progress and total_score <= 0:
            return {}

        return {
            "recent_unlocks": recent_unlocks,
            "in_progress_achievements": in_progress,
            "total_achievement_score": round(total_score, 2),
        }

    async def _get_calendar_context(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        db = db_session if db_session is not None else self.db
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = now + timedelta(days=7)

        today_result = await db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time < today_end,
                CalendarEvent.end_time > today_start,
            )
            .order_by(CalendarEvent.start_time)
        )
        week_result = await db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time >= now,
                CalendarEvent.start_time <= week_end,
            )
            .order_by(CalendarEvent.start_time)
        )

        today_events = list(today_result.scalars().all())
        week_events = list(week_result.scalars().all())
        preferences = await self._get_preference_service(db).get_preferences(user_id)
        merged_prefs: dict[str, Any] = {}
        if preferences:
            merged_prefs.update(dict(preferences.inferred or {}))
            merged_prefs.update(dict(preferences.explicit or {}))
        exam_urgency = merged_prefs.get("exam_urgency") if isinstance(merged_prefs.get("exam_urgency"), dict) else {}

        upcoming_deadlines = []
        for event in week_events[:6]:
            if event.task_id is None and event.plan_id is None:
                continue
            upcoming_deadlines.append(
                {
                    "title": event.title,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "source": "task" if event.task_id else "plan",
                }
            )

        time_blocks_today = self._derive_available_time_blocks(today_events, reference_day=today_start.date())
        workload_density = self._derive_workload_density(week_events)

        if not upcoming_deadlines and not time_blocks_today and not workload_density and not exam_urgency:
            return {}

        return {
            "upcoming_deadlines": upcoming_deadlines,
            "time_blocks_today": time_blocks_today,
            "workload_density": workload_density,
            "exam_urgency": exam_urgency or {},
        }

    async def _get_preference_version(self, user_id: str) -> int:
        """
        获取用户偏好的当前版本号。
        用于验证缓存是否过期（偏好修改后会递增版本号）。
        """
        try:
            prefs = await self._get_preference_service().get_preferences(UUID(user_id))
            return prefs.version or 0
        except Exception as e:
            logger.warning(f"Failed to get preference version for {user_id}: {e}")
            return 0

    async def _get_community_profile(self, user_id: UUID, db_session: AsyncSession | None = None) -> dict[str, Any]:
        # Use provided session or fall back to self.db
        db = db_session if db_session is not None else self.db
        membership_result = await db.execute(
            select(GroupMember, Group)
            .join(Group, Group.id == GroupMember.group_id)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.deleted_at.is_(None),
                Group.deleted_at.is_(None),
            )
        )
        rows = membership_result.all()
        if not rows:
            return {}

        active_groups = []
        sprint_summaries: list[str] = []
        type_counts = {"sprint": 0, "squad": 0, "official": 0}
        latest_active_at: datetime | None = None

        for member, group in rows:
            active_groups.append(group)
            group_type = str(group.type.value if hasattr(group.type, "value") else group.type).lower()
            type_counts[group_type] = type_counts.get(group_type, 0) + 1
            if member.last_active_at and (latest_active_at is None or member.last_active_at > latest_active_at):
                latest_active_at = member.last_active_at
            if group_type == "sprint":
                claim_counts = await self.db.execute(
                    select(
                        func.count(GroupTaskClaim.id),
                        func.sum(cast(GroupTaskClaim.is_completed, Integer)),
                    )
                    .join(GroupMember, GroupMember.user_id == GroupTaskClaim.user_id)
                    .join(Group, Group.id == GroupMember.group_id)
                    .where(
                        GroupMember.user_id == user_id,
                        Group.id == group.id,
                        GroupTaskClaim.deleted_at.is_(None),
                    )
                )
                total_claims, completed_claims = claim_counts.one()
                total_claims = int(total_claims or 0)
                completed_claims = int(completed_claims or 0)
                progress = round((completed_claims / total_claims) * 100) if total_claims else 0
                sprint_summaries.append(
                    f"\"{group.name}\" 群组进度 {progress}%，你的贡献 {completed_claims}/{max(total_claims, 1)} 任务"
                )

        unfinished_claims = await self.db.execute(
            select(func.count(GroupTaskClaim.id))
            .join(GroupMember, GroupMember.user_id == GroupTaskClaim.user_id)
            .join(Group, Group.id == GroupMember.group_id)
            .where(
                GroupMember.user_id == user_id,
                GroupTaskClaim.is_completed.is_(False),
                GroupTaskClaim.deleted_at.is_(None),
                GroupMember.deleted_at.is_(None),
                Group.deleted_at.is_(None),
            )
        )
        pending_group_tasks = int(unfinished_claims.scalar_one() or 0)
        recent_interaction = None
        if latest_active_at:
            delta_days = max(0, (_utcnow() - latest_active_at).days)
            recent_interaction = f"{delta_days}天前" if delta_days > 0 else "今天"

        summary_lines = [
            f"活跃群组: {len(active_groups)}个（{type_counts.get('sprint', 0)}个冲刺群、{type_counts.get('squad', 0)}个学习小队）",
        ]
        if sprint_summaries:
            summary_lines.append(f"冲刺进度: {sprint_summaries[0]}")
        if recent_interaction:
            summary_lines.append(f"最近互动: {recent_interaction}")
        if pending_group_tasks:
            summary_lines.append(f"未完成群组任务: {pending_group_tasks}个")

        return {
            "active_group_count": len(active_groups),
            "active_group_types": {k: v for k, v in type_counts.items() if v},
            "sprint_progress": sprint_summaries[:1],
            "recent_interaction": recent_interaction,
            "has_pending_group_tasks": pending_group_tasks > 0,
            "pending_group_task_count": pending_group_tasks,
            "summary_lines": summary_lines,
        }

    @staticmethod
    def _derive_available_time_blocks(events: list[CalendarEvent], *, reference_day: date) -> list[dict[str, str]]:
        day_start = datetime.combine(reference_day, datetime.min.time()).replace(hour=7)
        day_end = datetime.combine(reference_day, datetime.min.time()).replace(hour=22)
        blocks: list[tuple[datetime, datetime]] = []
        for event in events:
            start = event.start_time.replace(tzinfo=None) if event.start_time.tzinfo else event.start_time
            end = event.end_time.replace(tzinfo=None) if event.end_time.tzinfo else event.end_time
            start = max(start, day_start)
            end = min(end, day_end)
            if start >= end:
                continue
            blocks.append((start, end))

        free_blocks: list[dict[str, str]] = []
        cursor = day_start
        for start, end in sorted(blocks, key=lambda item: item[0]):
            if start > cursor:
                free_blocks.append(
                    {
                        "start": cursor.strftime("%H:%M"),
                        "end": start.strftime("%H:%M"),
                    }
                )
            cursor = max(cursor, end)
        if cursor < day_end:
            free_blocks.append({"start": cursor.strftime("%H:%M"), "end": day_end.strftime("%H:%M")})
        return free_blocks[:4]

    @staticmethod
    def _derive_workload_density(events: list[CalendarEvent]) -> str:
        if not events:
            return "low"
        by_day: defaultdict[date, int] = defaultdict(int)
        total_minutes = 0
        for event in events:
            event_day = event.start_time.date()
            by_day[event_day] += 1
            total_minutes += max(0, int((event.end_time - event.start_time).total_seconds() / 60))
        active_days = max(len(by_day), 1)
        avg_events = sum(by_day.values()) / active_days
        avg_minutes = total_minutes / active_days
        if avg_events >= 4 or avg_minutes >= 240:
            return "high"
        if avg_events >= 2 or avg_minutes >= 120:
            return "medium"
        return "low"
