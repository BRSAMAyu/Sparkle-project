from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from app.models.user import User, PushPreference
from app.models.notification import PushHistory
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService
from app.services.llm_service import llm_service
from app.services.curiosity_capsule_service import curiosity_capsule_service
from app.services.personalization import get_personalization_engine, PushPolicyProfile
from app.services.push_strategies import (
    SprintStrategy,
    MemoryStrategy,
    InactivityStrategy,
    CuriosityStrategy,
    EmptyCapsuleStrategy,
)

class PushService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def process_all_users(self):
        """
        Main entry point: Process push logic for all eligible users.
        """
        logger.info("Starting daily push processing...")
        
        # 1. Get all active users with push preferences
        # Note: In a real large-scale system, we would paginate or use a job queue.
        query = (
            select(User)
            .join(PushPreference, User.id == PushPreference.user_id)
            .where(User.is_active == True)
        )
        result = await self.db.execute(query)
        users = result.scalars().all()

        for user in users:
            try:
                await self.process_user_push(user)
            except Exception as e:
                logger.error(f"Error processing push for user {user.id}: {e}")

    async def process_user_push(self, user: User) -> bool:
        """
        Process push logic for a single user.
        Returns True if a push was sent.
        """
        engine = get_personalization_engine(self.db, self.redis)
        policy = await engine.get_push_policy_profile(user.id)
        prefs = await engine.pref_service.get_preferences(user.id)
        explicit_prefs = prefs.explicit or {}

        if policy.silent_during_focus:
            logger.info(f"User {user.id} is in focus mode, skipping push")
            return False

        if not self._is_active_time(policy):
            logger.debug(f"User {user.id} is not in active time slot.")
            return False

        if await self._check_frequency_cap(user, policy):
            logger.debug(f"User {user.id} reached frequency cap.")
            return False

        strategies = [
            SprintStrategy(self.db),
            MemoryStrategy(self.db),
            EmptyCapsuleStrategy(self.db),
            CuriosityStrategy(self.db),
            InactivityStrategy(self.db),
        ]

        trigger_strategy = None
        for strategy in strategies:
            if await strategy.should_trigger(user, policy):
                trigger_strategy = strategy
                break

        if not trigger_strategy:
            return False

        # 4. Generate Content
        # For curiosity, we might generate capsule inside get_context_data or separate
        trigger_type = trigger_strategy.trigger_type

        if trigger_type == "curiosity":
            # Generate capsule first
            capsule = await curiosity_capsule_service.generate_daily_capsule(user.id, self.db)
            if capsule:
                trigger_data = {"capsule_id": str(capsule.id), "title": capsule.title, "preview": capsule.content[:50]}
                content_dict = {
                    "title": f"✨ 好奇心胶囊: {capsule.title}",
                    "body": f"发现一个新知识点！{capsule.content[:30]}..."
                }
            else:
                return False
        else:
            trigger_data = await trigger_strategy.get_context_data(user)
            content_dict = await self._generate_push_content(
                user,
                explicit_prefs,
                trigger_type,
                trigger_data
            )
        
        if not content_dict:
            logger.warning("Failed to generate push content.")
            return False

        # 5. Send & Record
        await self._send_push(user, trigger_type, content_dict, trigger_data, policy)
        
        return True

    async def _check_frequency_cap(self, user: User, policy: PushPolicyProfile) -> bool:
        """
        Check if user reached daily cap or is in cooldown.
        Returns True if BLOCKED (capped), False if ALLOWED.
        """
        prefs = user.push_preference
        if not prefs:
            return False

        now = datetime.now(timezone.utc)

        # Cooldown check (e.g., at least 2 hours between pushes)
        if prefs and prefs.last_push_time:
            last_time = prefs.last_push_time
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            
            min_interval = timedelta(minutes=policy.min_interval_minutes)
            if (now - last_time) < min_interval:
                return True

        # Daily Cap Check
        # Convert now to user's local time to determine "today"
        try:
            tz = ZoneInfo(policy.timezone or "Asia/Shanghai")
            local_now = now.astimezone(tz)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
            local_now = now.astimezone(tz)
        
        # Start of local day in UTC
        local_start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_start_of_day = local_start_of_day.astimezone(timezone.utc)

        query = select(func.count()).select_from(PushHistory).where(
            and_(
                PushHistory.user_id == user.id,
                PushHistory.created_at >= utc_start_of_day
            )
        )
        result = await self.db.execute(query)
        daily_count = result.scalar() or 0
        
        return daily_count >= policy.daily_cap

    def _is_active_time(self, policy: PushPolicyProfile) -> bool:
        """
        Check if current time is within user's active slots.
        """
        try:
            tz = ZoneInfo(policy.timezone or "Asia/Shanghai")
        except ZoneInfoNotFoundError:
            logger.warning(f"Invalid timezone {policy.timezone}, defaulting to Asia/Shanghai")
            tz = ZoneInfo("Asia/Shanghai")

        now_local = datetime.now(tz)

        current_minutes = now_local.hour * 60 + now_local.minute

        if policy.active_hours:
            return current_minutes in policy.active_hours

        return 480 <= current_minutes <= 1320

    async def _generate_push_content(
        self,
        user: User,
        explicit_prefs: Dict[str, Any],
        trigger_type: str,
        data: Dict
    ) -> Dict[str, str]:
        """
        Generate push content using LLM based on persona and trigger data.
        Returns dict with 'title' and 'body'.
        """
        persona = explicit_prefs.get("persona_type", "coach")
        depth_preference = explicit_prefs.get("depth_preference", 0.5)
        curiosity_preference = explicit_prefs.get("curiosity_preference", 0.5)
        nickname = user.nickname or user.username or "同学"
        
        return await llm_service.generate_push_content(
            user_nickname=nickname,
            persona=persona,
            trigger_type=trigger_type,
            context_data=data,
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
        )

    async def _send_push(
        self,
        user: User,
        trigger_type: str,
        content: Dict[str, str],
        data: Dict,
        policy: PushPolicyProfile
    ):
        """
        Create Notification and History records.
        """
        title = content.get("title", "Sparkle 提醒")
        body = content.get("body", "你有一条新消息")

        # 1. Create Notification (User visible)
        notif_create = NotificationCreate(
            title=title,
            content=body,
            type=trigger_type,
            data=data
        )
        await NotificationService.create(self.db, user.id, notif_create)
        
        # 2. Create PushHistory (Analytics)
        import hashlib
        # Hash body content
        content_hash = hashlib.md5(body.encode('utf-8')).hexdigest()
        
        history = PushHistory(
            user_id=user.id,
            trigger_type=trigger_type,
            content_hash=content_hash,
            status="sent"
        )
        self.db.add(history)
        
        # 3. Update User Preferences (Last push time)
        user.push_preference.last_push_time = datetime.now(timezone.utc)
        
        await self.db.commit()
        logger.info(f"Push sent to user {user.id} [{trigger_type}]: {title} - {body}")

        try:
            from app.services.decision_record_service import DecisionRecordService

            decision_service = DecisionRecordService(self.db)
            await decision_service.record_decision(
                user_id=user.id,
                module="push",
                action=f"send_{trigger_type}",
                preference_version=policy.preference_version,
                preferences_snapshot={
                    "daily_cap": policy.daily_cap,
                    "persona_type": user.push_preference.persona_type if user.push_preference else "coach",
                    "curiosity_frequency": policy.curiosity_frequency,
                },
                outcome=f"Sent {trigger_type} push notification",
            )
        except Exception as e:
            logger.warning(f"Failed to record push decision: {e}")
