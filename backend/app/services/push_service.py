import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from loguru import logger

from app.models.user import User, PushPreference
from app.models.notification import PushHistory
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService
from app.services.llm_service import llm_service
from app.services.curiosity_capsule_service import curiosity_capsule_service
from app.services.push_strategies import (
    SprintStrategy,
    MemoryStrategy,
    InactivityStrategy,
    CuriosityStrategy
)

class PushService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sprint_strategy = SprintStrategy()
        self.memory_strategy = MemoryStrategy()
        self.inactivity_strategy = InactivityStrategy()
        self.curiosity_strategy = CuriosityStrategy()

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
        # Ensure user has preferences loaded
        if not user.push_preference:
            # Should be loaded by join, but double check
            return False

        prefs: PushPreference = user.push_preference

        # 1. Check Timezone & Active Slots
        if not self._is_active_time(prefs):
            logger.debug(f"User {user.id} is not in active time slot.")
            return False

        # 2. Check Frequency Caps
        if await self._check_frequency_cap(user, prefs):
            logger.debug(f"User {user.id} reached frequency cap.")
            return False

        # 3. Strategy Evaluation (Priority: Sprint > Curiosity > Memory > Inactivity)
        trigger_strategy = None
        trigger_data = {}
        trigger_type = ""

        # Check Sprint Strategy
        if await self.sprint_strategy.should_trigger(user, self.db):
            trigger_strategy = self.sprint_strategy
            trigger_type = "sprint"
        
        # Check Curiosity Strategy
        elif prefs.enable_curiosity and await self.curiosity_strategy.should_trigger(user, self.db):
            trigger_strategy = self.curiosity_strategy
            trigger_type = "curiosity"

        # Check Memory Strategy
        elif await self.memory_strategy.should_trigger(user, self.db):
            trigger_strategy = self.memory_strategy
            trigger_type = "memory"
            
        # Check Inactivity Strategy
        elif await self.inactivity_strategy.should_trigger(user, self.db):
            trigger_strategy = self.inactivity_strategy
            trigger_type = "inactivity"

        if not trigger_strategy:
            return False

        # 4. Generate Content
        # For curiosity, we might generate capsule inside get_trigger_data or separate
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
            trigger_data = await trigger_strategy.get_trigger_data(user, self.db)
            content_dict = await self._generate_push_content(user, prefs, trigger_type, trigger_data)
        
        if not content_dict:
            logger.warning("Failed to generate push content.")
            return False

        # 5. Send & Record
        await self._send_push(user, trigger_type, content_dict, trigger_data)
        
        return True

    async def _check_frequency_cap(self, user: User, prefs: PushPreference) -> bool:
        """
        Check if user reached daily cap or is in cooldown.
        Returns True if BLOCKED (capped), False if ALLOWED.
        """
        now = datetime.now(timezone.utc)

        # Cooldown check (e.g., at least 2 hours between pushes)
        if prefs.last_push_time:
            last_time = prefs.last_push_time
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            
            if (now - last_time) < timedelta(hours=2):
                return True

        # Daily Cap Check
        # Convert now to user's local time to determine "today"
        try:
            tz = ZoneInfo(prefs.timezone or "Asia/Shanghai")
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
        
        return daily_count >= prefs.daily_cap

    def _is_active_time(self, prefs: PushPreference) -> bool:
        """
        Check if current time is within user's active slots and outside silence window (23-07).
        """
        try:
            tz = ZoneInfo(prefs.timezone or "Asia/Shanghai")
        except ZoneInfoNotFoundError:
            logger.warning(f"Invalid timezone {prefs.timezone}, defaulting to Asia/Shanghai")
            tz = ZoneInfo("Asia/Shanghai")

        now_local = datetime.now(tz)
        
        # 1. Hard Rule: Silence Window (23:00 - 07:00)
        # TODO: Add override flag check if user forced enable?
        if now_local.hour >= 23 or now_local.hour < 7:
            return False
            
        # 2. Check minute alignment (Optional optimization: only run on :00 and :30)
        # Assuming scheduler handles the trigger time, but we can double check logic if needed.
        # Strict checking here might miss if job runs at 00:01. Let's be lenient on minutes here
        # and assume the caller (Scheduler) controls frequency.

        # 3. Active Slots Check
        if not prefs.active_slots:
            return True # If not defined, default to allowed (within 07-23)
            
        # prefs.active_slots structure: [{"start": "08:00", "end": "09:00"}]
        # Check if current time falls into any slot
        current_time_str = now_local.strftime("%H:%M")
        current_minutes = now_local.hour * 60 + now_local.minute
        
        is_in_slot = False
        try:
            # Support both list of strings or list of objects
            # Assuming objects as per previous context: [{"start": "...", "end": "..."}]
            slots = prefs.active_slots
            if isinstance(slots, list):
                for slot in slots:
                    if isinstance(slot, dict) and "start" in slot and "end" in slot:
                        start_h, start_m = map(int, slot["start"].split(":"))
                        end_h, end_m = map(int, slot["end"].split(":"))
                        
                        start_mins = start_h * 60 + start_m
                        end_mins = end_h * 60 + end_m
                        
                        if start_mins <= current_minutes <= end_mins:
                            is_in_slot = True
                            break
        except Exception as e:
            logger.error(f"Error parsing active slots: {e}")
            return True # Fail open to avoid blocking valid pushes on config error
            
        return is_in_slot

    async def _generate_push_content(self, user: User, prefs: PushPreference, trigger_type: str, data: Dict) -> Dict[str, str]:
        """
        Generate push content using LLM based on persona and trigger data.
        Returns dict with 'title' and 'body'.
        """
        persona = prefs.persona_type or "coach"
        nickname = user.nickname or user.username or "同学"
        
        return await llm_service.generate_push_content(
            user_nickname=nickname,
            persona=persona,
            trigger_type=trigger_type,
            context_data=data
        )

    async def _send_push(self, user: User, trigger_type: str, content: Dict[str, str], data: Dict):
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
