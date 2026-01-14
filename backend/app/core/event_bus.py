from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
import json
import os
import asyncio
from datetime import datetime
from loguru import logger
import redis.asyncio as redis
from redis.exceptions import ResponseError
from app.config import settings
from app.core.redis_utils import resolve_redis_password, format_redis_url_for_log

class Event(ABC):
    """Event base class"""
    @abstractmethod
    def to_dict(self) -> dict:
        pass

class KnowledgeNodeUpdated(Event):
    def __init__(self, user_id: str, node_id: str, new_mastery: int):
        self.user_id = user_id
        self.node_id = node_id
        self.new_mastery = new_mastery
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "event_type": "knowledge_node_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "new_mastery": self.new_mastery,
            "timestamp": self.timestamp.isoformat()
        }

class NodeMasteryUpdatedEvent(Event):
    def __init__(self, user_id: str, node_id: str, old_mastery: int, new_mastery: int, reason: str):
        self.user_id = user_id
        self.node_id = node_id
        self.old_mastery = old_mastery
        self.new_mastery = new_mastery
        self.reason = reason
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "event_type": "node_mastery_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "old_mastery": self.old_mastery,
            "new_mastery": self.new_mastery,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

class ErrorCreated(Event):
    def __init__(self, user_id: str, error_id: str, linked_node_ids: List[str] = None):
        self.user_id = user_id
        self.error_id = error_id
        self.linked_node_ids = linked_node_ids or []
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "event_type": "error_created",
            "user_id": self.user_id,
            "error_id": self.error_id,
            "linked_node_ids": self.linked_node_ids,
            "timestamp": self.timestamp.isoformat()
        }

class EventBus:
    """
    Event Bus - Redis Streams Implementation
    Supports asynchronous publishing and consumer groups.
    """
    def __init__(self, redis_url: Optional[str] = None):
        # We delay connection until needed or explicitly initialized
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis: Optional[redis.Redis] = None
        self._consumers = []
        self._running = False

    async def connect(self):
        """Establish Redis connection"""
        if not self.redis:
            try:
                password, password_source = resolve_redis_password(self.redis_url, settings.REDIS_PASSWORD)
                kwargs = {
                    "encoding": "utf-8",
                    "decode_responses": True
                }
                if password:
                    kwargs["password"] = password

                self.redis = redis.from_url(
                    self.redis_url,
                    **kwargs
                )
                await self.redis.ping()
                logger.info(
                    "Successfully connected to Redis Event Bus: {}, Password={}, PasswordSource={}".format(
                        format_redis_url_for_log(self.redis_url),
                        "Yes" if password else "No",
                        password_source,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis = None

    async def close(self):
        """Close connection and stop consumers"""
        self._running = False
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Redis Event Bus connection closed")

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> Optional[str]:
        """
        Publish event to Redis Stream
        
        Args:
            event_type: Type of the event (used as key in payload usually, but here just for logging/logic)
            payload: Dictionary data to send
            stream: Redis Stream key name
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                logger.error("Cannot publish: Redis not connected")
                return None

        try:
            # Ensure payload implies event_type if not present, or wrap it
            message = payload.copy()
            if "event_type" not in message:
                message["event_type"] = event_type
            
            # Serialize complex types if necessary (Redis expects str->str dict for simpler usage)
            # We use json dumps for the whole payload or individual fields.
            # Here we dump the whole payload into a 'data' field to avoid field limitation issues,
            # or we flatten it. For simplicity and flexibility, let's put it in 'data'.
            # However, standard stream usage often puts fields directly. 
            # Let's stringify values.
            
            msg_body = {}
            for k, v in message.items():
                if isinstance(v, (dict, list)):
                    msg_body[k] = json.dumps(v)
                else:
                    msg_body[k] = str(v)

            # XADD
            msg_id = await self.redis.xadd(stream, msg_body)
            logger.debug(f"Published event {event_type} to {stream} with ID {msg_id}")
            return msg_id

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return None

    async def subscribe(self, stream: str, group_name: str, consumer_name: str, callback: Callable[[Dict], Any]):
        """
        Start a background consumer for a consumer group.
        
        Args:
            stream: Redis Stream key
            group_name: Consumer Group name
            consumer_name: Unique consumer name instance
            callback: Async function to handle message payload (dict)
        """
        if not self.redis:
            await self.connect()

        # 1. Create Consumer Group if not exists
        try:
            await self.redis.xgroup_create(stream, group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group {group_name} for stream {stream}")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {group_name} already exists")
            else:
                logger.error(f"Error creating consumer group: {e}")
                return

        # 2. Start Consumption Loop
        self._running = True
        asyncio.create_task(self._consume_loop(stream, group_name, consumer_name, callback))

    async def _consume_loop(self, stream: str, group_name: str, consumer_name: str, callback: Callable):
        logger.info(f"Starting consumer loop: {group_name}:{consumer_name} on {stream}")
        
        while self._running:
            try:
                if not self.redis:
                    await asyncio.sleep(1)
                    continue

                # Read from group
                # count=1 for processing one by one, block=5000ms
                entries = await self.redis.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream: ">"},
                    count=1,
                    block=2000
                )

                if not entries:
                    continue

                for stream_name, messages in entries:
                    for message_id, data in messages:
                        try:
                            # Parse data (handling json strings if we did that)
                            parsed_data = {}
                            for k, v in data.items():
                                try:
                                    parsed_data[k] = json.loads(v)
                                except (json.JSONDecodeError, TypeError):
                                    parsed_data[k] = v
                            
                            # Invoke callback
                            await callback(parsed_data)
                            
                            # ACK
                            await self.redis.xack(stream, group_name, message_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")
                            # TODO: Implement Dead Letter Queue or Retry logic here
                            
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1) # Backoff

# Global instance
event_bus = EventBus()
