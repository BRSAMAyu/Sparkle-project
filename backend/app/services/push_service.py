from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import PushHistory
from app.models.user import PushPreference, User
from app.schemas.notification import NotificationCreate
from app.services.curiosity_capsule_service import curiosity_capsule_service
from app.services.llm_service import llm_service
from app.services.notification_service import NotificationService
from app.services.personalization import PushPolicyProfile, get_personalization_engine
from app.services.push_strategies import (
    CuriosityStrategy,
    EmptyCapsuleStrategy,
    InactivityStrategy,
    MemoryStrategy,
    SprintStrategy,
)

PUSH_TRIGGER_TYPES = {
    "MEMORY": "memory",
    "SPRINT": "sprint",
    "INACTIVITY": "inactivity",
    "CURIOSITY": "curiosity",
    "EMPTY_CAPSULE": "empty_capsule",
    "STRUGGLE_DETECTED": "struggle_detected",
}
STRUGGLE_DETECTED = PUSH_TRIGGER_TYPES["STRUGGLE_DETECTED"]
NON_JUDGMENTAL_BLOCKLIST = ("失败", "没做到", "你又")


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PushService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def process_all_users(self, *, delivery_mode: str = "live") -> dict[str, int | str]:
        """
        Main entry point: Process push logic for all eligible users.
        """
        normalized_mode = str(delivery_mode or "live").strip().lower()
        logger.info("Starting push policy processing in {} mode...", normalized_mode)

        # 1. Get all active users with push preferences
        # Note: In a real large-scale system, we would paginate or use a job queue.
        query = select(User).join(PushPreference, User.id == PushPreference.user_id).where(User.is_active)
        result = await self.db.execute(query)
        users = result.scalars().all()

        summary = {
            "mode": normalized_mode,
            "evaluated_users": len(users),
            "triggered": 0,
            "sent": 0,
            "shadowed": 0,
            "errors": 0,
        }
        for user in users:
            try:
                outcome = await self.process_user_push(user, delivery_mode=normalized_mode)
                if outcome["triggered"]:
                    summary["triggered"] += 1
                if outcome["sent"]:
                    summary["sent"] += 1
                if outcome["shadowed"]:
                    summary["shadowed"] += 1
            except Exception as e:
                summary["errors"] += 1
                logger.error(f"Error processing push for user {user.id}: {e}")
        return summary

    async def process_user_push(self, user: User, *, delivery_mode: str = "live") -> dict[str, bool | str]:
        """
        Process push logic for a single user.
        Returns trigger outcome metadata.
        """
        normalized_mode = str(delivery_mode or "live").strip().lower()
        engine = get_personalization_engine(self.db, self.redis)
        policy = await engine.get_push_policy_profile(user.id)
        prefs = await engine.pref_service.get_preferences(user.id)
        explicit_prefs = prefs.explicit or {}

        if policy.silent_during_focus:
            logger.info(f"User {user.id} is in focus mode, skipping push")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": ""}

        if not self._is_active_time(policy):
            logger.debug(f"User {user.id} is not in active time slot.")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": ""}

        if await self._check_frequency_cap(user, policy):
            logger.debug(f"User {user.id} reached frequency cap.")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": ""}

        if await self._check_schedule_and_quiet_hours(user.id):
            logger.info(f"User {user.id} is in schedule DND or quiet hours, skipping push")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": ""}

        strategies = [
            SprintStrategy(self.db),
            MemoryStrategy(self.db),
            EmptyCapsuleStrategy(self.db),
            CuriosityStrategy(self.db),
            InactivityStrategy(self.db),
        ]

        trigger_strategy = None
        trigger_type = ""
        for strategy in strategies:
            if await strategy.should_trigger(user, policy):
                trigger_strategy = strategy
                trigger_type = strategy.trigger_type
                break

        if not trigger_strategy:
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": ""}

        if await self._check_notification_type_disabled(user.id, trigger_type):
            logger.info(f"User {user.id} disabled notification type {trigger_type}, skipping push")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": trigger_type}

        # 4. Generate Content
        # For curiosity, we might generate capsule inside get_context_data or separate

        if trigger_type == "curiosity":
            # Generate capsule first
            capsule = await curiosity_capsule_service.generate_daily_capsule(user.id, self.db)
            if capsule:
                trigger_data = {"capsule_id": str(capsule.id), "title": capsule.title, "preview": capsule.content[:50]}
                content_dict = {
                    "title": f"✨ 好奇心胶囊: {capsule.title}",
                    "body": f"发现一个新知识点！{capsule.content[:30]}...",
                }
            else:
                return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": trigger_type}
        else:
            trigger_data = await trigger_strategy.get_context_data(user)
            content_dict = await self._generate_push_content(user, explicit_prefs, trigger_type, trigger_data)

        if not content_dict:
            logger.warning("Failed to generate push content.")
            return {"triggered": False, "sent": False, "shadowed": False, "trigger_type": trigger_type}

        if normalized_mode == "shadow":
            logger.info("Push policy shadow evaluation for user {} trigger={}", user.id, trigger_type)
            return {"triggered": True, "sent": False, "shadowed": True, "trigger_type": trigger_type}

        # 5. Send & Record
        await self._send_push(user, trigger_type, content_dict, trigger_data, policy)

        return {"triggered": True, "sent": True, "shadowed": False, "trigger_type": trigger_type}

    async def send_struggle_nudge(
        self,
        *,
        user_id: str,
        message_hint: str,
        struggle_context: dict,
    ) -> bool:
        """
        发送挣扎关怀推送。

        关键约束：
        1. 检查 DND 时间段（从 ControlSurface 读取）
        2. 最大推送频率：每8小时1次
        3. 语言必须非审判性
        """
        if any(token in str(message_hint or "") for token in NON_JUDGMENTAL_BLOCKLIST):
            logger.warning("Blocked judgmental struggle nudge for user {}", user_id)
            return False

        user_uuid = _coerce_uuid(user_id)
        result = await self.db.execute(select(User).where(User.id == user_uuid, User.is_active.is_(True)))
        user = result.scalar_one_or_none()
        if user is None:
            return False

        if await self._is_in_control_surface_dnd(user_uuid):
            logger.info("User {} is in Aurora DND window, skipping struggle nudge", user_uuid)
            return False

        if await self._recent_struggle_nudge_sent(user_uuid):
            logger.debug("User {} reached struggle nudge 8h cooldown", user_uuid)
            return False

        engine = get_personalization_engine(self.db, self.redis)
        policy = await engine.get_push_policy_profile(user_uuid)
        if policy.silent_during_focus:
            logger.info("User {} is in focus mode, skipping struggle nudge", user_uuid)
            return False

        if user.push_preference is None:
            user.push_preference = PushPreference(user_id=user_uuid)
            self.db.add(user.push_preference)
            await self.db.flush()

        data = {
            "trigger_type": STRUGGLE_DETECTED,
            "struggle_score": struggle_context.get("struggle_score"),
            "primary_signal": struggle_context.get("primary_signal"),
            "struggle_context": struggle_context,
        }
        content = {
            "title": "Aurora 想和你一起看一下节奏",
            "body": str(message_hint or "").strip() or "你最近的学习节奏可能有些阻力，我们一起看一下怎么调轻一点。",
        }
        await self._send_push(user, STRUGGLE_DETECTED, content, data, policy)
        return True

    async def _is_in_control_surface_dnd(self, user_id: UUID) -> bool:
        try:
            from app.aurora.runtime_v1.control_surface import ControlSurfaceService

            reading = await ControlSurfaceService(self.db, self.redis).read_control_surface(user_id)
            hard_bounds = reading.hard_bounds
            return hard_bounds.is_action_disabled("proactive_follow_up") or hard_bounds.is_within_dnd(
                datetime.now(UTC)
            )
        except Exception as exc:
            logger.warning("Failed to read Aurora control surface for struggle nudge: {}", exc)
            return False

    async def _check_schedule_and_quiet_hours(self, user_id: UUID) -> bool:
        """Check if push should be suppressed due to schedule or quiet hours.
        Returns True if push should be BLOCKED."""
        try:
            from app.services.preference_consumption_service import PreferenceConsumptionService

            consumption = PreferenceConsumptionService(self.db, self.redis)
            return await consumption.should_suppress_push(user_id)
        except Exception as exc:
            logger.warning(f"Failed to check schedule/quiet hours for {user_id}: {exc}")
            return False

    async def _check_notification_type_disabled(self, user_id: UUID, trigger_type: str) -> bool:
        """Check if the specific notification type is disabled by user preference.
        Returns True if BLOCKED."""
        try:
            from app.services.preference_consumption_service import PreferenceConsumptionService

            consumption = PreferenceConsumptionService(self.db, self.redis)
            notif_config = await consumption.get_notification_config(user_id)
            disabled_types = set(notif_config.get("disabled_types", []))
            notification_level = notif_config.get("notification_level", "standard")

            if notification_level == "minimal":
                return True

            if trigger_type in disabled_types:
                return True

            if not notif_config.get("enable_system", True) and trigger_type in (
                "memory", "sprint", "inactivity"
            ):
                return True

            if not notif_config.get("enable_interventions", True) and trigger_type in (
                "curiosity", "empty_capsule", "struggle_detected"
            ):
                return True

            return False
        except Exception as exc:
            logger.warning(f"Failed to check notification type disabled for {user_id}: {exc}")
            return False

    async def _recent_struggle_nudge_sent(self, user_id: UUID) -> bool:
        since = _utcnow() - timedelta(hours=8)
        result = await self.db.execute(
            select(func.count(PushHistory.id)).where(
                PushHistory.user_id == user_id,
                PushHistory.trigger_type == STRUGGLE_DETECTED,
                PushHistory.created_at >= since,
            )
        )
        return int(result.scalar() or 0) > 0

    async def _check_frequency_cap(self, user: User, policy: PushPolicyProfile) -> bool:
        """
        Check if user reached daily cap or is in cooldown.
        Returns True if BLOCKED (capped), False if ALLOWED.
        """
        prefs = user.push_preference
        if not prefs:
            return False

        now = datetime.now(UTC)

        # Cooldown check (e.g., at least 2 hours between pushes)
        if prefs and prefs.last_push_time:
            last_time = prefs.last_push_time
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=UTC)

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
        utc_start_of_day = local_start_of_day.astimezone(UTC)

        query = (
            select(func.count())
            .select_from(PushHistory)
            .where(and_(PushHistory.user_id == user.id, PushHistory.created_at >= utc_start_of_day))
        )
        result = await self.db.execute(query)
        daily_count = result.scalar() or 0

        return daily_count >= policy.daily_cap

    def _is_active_time(self, policy: PushPolicyProfile) -> bool:
        """
        Check if current time is within user's active slots.
        Respects weekly schedule preferences for busy/relax/fragmented slots.
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
        self, user: User, explicit_prefs: dict[str, Any], trigger_type: str, data: dict
    ) -> dict[str, str]:
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
        self, user: User, trigger_type: str, content: dict[str, str], data: dict, policy: PushPolicyProfile
    ):
        """
        Create Notification and History records.
        """
        title = content.get("title", "Sparkle 提醒")
        body = content.get("body", "你有一条新消息")

        # 1. Create Notification (User visible)
        notif_create = NotificationCreate(title=title, content=body, type=trigger_type, data=data)
        await NotificationService.create(self.db, user.id, notif_create)

        # 2. Create PushHistory (Analytics)
        import hashlib

        # Hash body content
        content_hash = hashlib.md5(body.encode("utf-8")).hexdigest()

        history = PushHistory(user_id=user.id, trigger_type=trigger_type, content_hash=content_hash, status="sent")
        self.db.add(history)

        # 3. Update User Preferences (Last push time)
        user.push_preference.last_push_time = datetime.now(UTC)

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
