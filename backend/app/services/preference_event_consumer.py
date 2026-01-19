"""
偏好事件消费者 - 订阅 Go 发布的偏好变更事件，使 Python 端缓存失效
"""
import asyncio
import json
from uuid import UUID

from loguru import logger

from app.services.user_service import UserService


class PreferenceEventConsumer:
    """消费 user.preferences.updated 事件"""

    def __init__(self, redis_client, user_service: UserService):
        self.redis = redis_client
        self.user_service = user_service
        self.stream_key = "cqrs:stream:user"
        self.consumer_group = "python_preference_consumer"
        self.consumer_name = "worker-1"

    async def start(self):
        """启动事件消费循环"""
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create consumer group: {e}")

        logger.info(f"PreferenceEventConsumer started, listening on {self.stream_key}")

        while True:
            try:
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=10,
                    block=1000,
                )

                for _stream, entries in messages:
                    for entry_id, data in entries:
                        await self._handle_event(data)
                        await self.redis.xack(self.stream_key, self.consumer_group, entry_id)

            except Exception as e:
                logger.error(f"Error consuming events: {e}")
                await asyncio.sleep(1)

    async def _handle_event(self, data: dict):
        """处理单个事件"""
        event_type = self._get_value(data, "type")
        if event_type in ("user.preferences.updated", "user.preferences.inferred"):
            try:
                payload_str = self._get_value(data, "payload") or "{}"
                payload = json.loads(payload_str)
                inner_data = json.loads(payload.get("data", "{}"))

                user_id = UUID(inner_data["user_id"])
                version = inner_data.get("preference_version")

                logger.info(f"Received preferences update for user {user_id}, version={version}")
                await self.user_service.invalidate_user_cache(user_id)

            except Exception as e:
                logger.error(f"Failed to handle preferences update event: {e}")

    @staticmethod
    def _get_value(data: dict, key: str):
        if key in data:
            value = data[key]
            if isinstance(value, bytes):
                return value.decode()
            return value
        key_bytes = key.encode()
        if key_bytes in data:
            value = data[key_bytes]
            if isinstance(value, bytes):
                return value.decode()
            return value
        return ""
