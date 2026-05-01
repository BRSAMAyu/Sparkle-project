"""
Core: execution
Phase: reinforce
Stage: Signal-to-Action Spine P1-4 Behavior-Driven Push Scheduler

行为驱动的推送调度器 — 将 RecallOpportunity + Spine NotificationDirective
连接到推送投递管道。

核心原则:
- 推送是温和的召回，不是催促
- 推送必须经过 Spine NotificationDirective（如果有）
- 推送受 push policy（频控 + 静默时段 + 疲劳保护）约束
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.user import User
from app.services.personalization import get_personalization_engine
from app.services.push_service import PushService
from app.signals.recall_notification import RecallNotificationBuilder
from app.signals.recall_opportunity import RecallOpportunityDetector

_RECALL_QUEUE_PREFIX = "push_scheduler:recall_queue:"
_MAX_QUEUE_SIZE = 10


class PushScheduler:
    """
    Behavior-driven push scheduler.

    Integrates RecallOpportunity detection with Spine NotificationDirective
    for intelligent push delivery within existing push policy constraints.
    """

    def __init__(self, db: AsyncSession, redis: Any | None = None):
        self.db = db
        self.redis = redis or (cache_service.redis if cache_service else None)
        self.detector = RecallOpportunityDetector()
        self.notif_builder = RecallNotificationBuilder()
        self.push_service = PushService(db)

    async def enqueue_session_end_recall(
        self,
        user_id: str,
        *,
        session_context: dict[str, Any] | None = None,
    ) -> int:
        """
        Called when a chat session ends. Checks for recall opportunities
        and enqueues them for the next push cycle.

        Returns the number of opportunities enqueued.
        """
        ctx = session_context or {}
        enqueued = 0

        trigger = self.detector.check_undigested_material(
            user_id=user_id,
            uploaded_files_count=ctx.get("uploaded_files_count", 0),
            diagnosed_files_count=ctx.get("diagnosed_files_count", 0),
            hours_since_upload=ctx.get("hours_since_upload", 1.0),
        )
        if trigger:
            await self._enqueue_trigger(trigger)
            enqueued += 1

        for task in ctx.get("pending_tasks") or []:
            trigger = self.detector.check_task_not_started(
                user_id=user_id,
                task_id=str(task.get("task_id", "")),
                hours_since_assignment=float(task.get("hours_since_assignment", 1.0)),
                has_started=bool(task.get("has_started", False)),
            )
            if trigger:
                await self._enqueue_trigger(trigger)
                enqueued += 1

        for task in ctx.get("overdue_tasks") or []:
            trigger = self.detector.check_task_missed(
                user_id=user_id,
                task_id=str(task.get("task_id", "")),
                deadline_hours=float(task.get("deadline_hours", 0)),
                is_completed=bool(task.get("is_completed", False)),
            )
            if trigger:
                await self._enqueue_trigger(trigger)
                enqueued += 1

        if ctx.get("exam_deadline_days") is not None:
            trigger = self.detector.check_pre_exam_silence(
                user_id=user_id,
                exam_deadline_days=float(ctx["exam_deadline_days"]),
                hours_since_last_activity=float(ctx.get("hours_since_last_activity", 3.0)),
            )
            if trigger:
                await self._enqueue_trigger(trigger)
                enqueued += 1

        if enqueued > 0:
            logger.info(f"Enqueued {enqueued} recall opportunities for user {user_id}")
        return enqueued

    async def process_recall_queue(self) -> dict[str, int]:
        """
        Process pending recall opportunities for all users with queued items.
        Called by the smart push cycle every 15 minutes.

        Returns stats: {"processed": N, "sent": N, "skipped_cooldown": N, "skipped_policy": N}
        """
        stats = {"processed": 0, "sent": 0, "skipped_cooldown": 0, "skipped_policy": 0}

        if not self.redis:
            return stats

        try:
            keys = []
            async for key in self.redis.scan_iter(match=f"{_RECALL_QUEUE_PREFIX}*"):
                keys.append(key)
        except Exception:
            return stats

        for key in keys:
            try:
                user_id = key.decode() if isinstance(key, bytes) else key
                user_id = user_id.replace(_RECALL_QUEUE_PREFIX, "")
                raw_triggers = await self.redis.lrange(key, 0, -1)
                if not raw_triggers:
                    continue

                try:
                    user = await self.db.get(User, uuid.UUID(user_id))
                except ValueError:
                    logger.warning(f"Skipping invalid user_id in recall queue: {user_id}")
                    await self.redis.delete(key)
                    continue
                if not user:
                    await self.redis.delete(key)
                    continue

                engine = get_personalization_engine(self.db, None)
                policy = await engine.get_push_policy_profile(user.id)

                for raw in raw_triggers:
                    stats["processed"] += 1
                    try:
                        trigger_data = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if await self.notif_builder.check_cooldown_async(
                        user_id=user_id,
                        trigger_type=trigger_data.get("trigger_type", ""),
                        redis_client=self.redis,
                    ):
                        stats["skipped_cooldown"] += 1
                        continue

                    spine_directive = await self._get_spine_directive(user_id)
                    message = self._build_push_message(trigger_data, spine_directive)

                    try:
                        await self.push_service._send_push(
                            user=user,
                            trigger_type=spine_directive.trigger if spine_directive else trigger_data.get("trigger_type", "recall"),
                            content={"title": message["title"], "body": message["body"]},
                            data={
                                "type": "recall",
                                "recall_type": trigger_data.get("trigger_type"),
                                "deep_link": message.get("deep_link", ""),
                                **({"spine_trigger": spine_directive.trigger} if spine_directive else {}),
                            },
                            policy=policy,
                        )
                        stats["sent"] += 1
                        await self.notif_builder.record_sent_async(
                            user_id=user_id,
                            trigger_type=trigger_data.get("trigger_type", ""),
                            redis_client=self.redis,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send recall push to {user_id}: {e}")
                        stats["skipped_policy"] += 1

                await self.redis.delete(key)
            except Exception as e:
                logger.error(f"Error processing recall queue for key {key}: {e}")

        return stats

    async def _enqueue_trigger(self, trigger: Any) -> None:
        key = f"{_RECALL_QUEUE_PREFIX}{trigger.user_id}"
        data = json.dumps(trigger.to_dict(), ensure_ascii=False)
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.lpush(key, data)
                pipe.ltrim(key, 0, _MAX_QUEUE_SIZE - 1)
                pipe.expire(key, 86400)  # 24h TTL
                await pipe.execute()
            except Exception as e:
                logger.warning(f"Failed to enqueue recall trigger: {e}")

    async def _get_spine_directive(self, user_id: str) -> Any:
        try:
            from app.signals.spine_orchestrator import SpineOrchestrator
            if self.redis:
                spine = SpineOrchestrator(self.redis)
                return await spine.get_notification_directive(user_id)
        except Exception:
            pass
        return None

    def _build_push_message(self, trigger_data: dict[str, Any], spine_directive: Any | None) -> dict[str, str]:
        if spine_directive:
            return {
                "title": "Sparkle",
                "body": trigger_data.get("message_template", "你有新的学习提醒"),
                "deep_link": spine_directive.deep_link if hasattr(spine_directive, "deep_link") else "",
            }
        return {
            "title": "Sparkle 提醒",
            "body": trigger_data.get("message_template", "你有新的学习提醒"),
            "deep_link": "",
        }
