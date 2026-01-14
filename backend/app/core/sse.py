"""
Server-Sent Events (SSE) Manager
用于实时推送事件到前端
"""
import asyncio
import json
import time
from typing import Dict, Set, Optional
from uuid import UUID
from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger
from app.core.cache import cache_service


class SSEManager:
    """
    SSE 连接管理器
    管理所有活跃的 SSE 连接，支持向特定用户推送事件
    支持断点续传 (Last-Event-ID) 和 Redis 缓冲
    """

    def __init__(self):
        # {user_id: Set[queue]}
        self.connections: Dict[str, Set[asyncio.Queue]] = {}

    async def connect(self, user_id: str, last_event_id: Optional[str] = None) -> asyncio.Queue:
        """
        创建新的 SSE 连接

        Args:
            user_id: 用户 ID
            last_event_id: 客户端上次收到的事件ID (Replay support)

        Returns:
            asyncio.Queue: 事件队列
        """
        queue = asyncio.Queue()

        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(queue)
        logger.info(f"SSE connection established for user {user_id}")

        # Replay logic
        if last_event_id and cache_service.redis:
            try:
                history_key = f"sse:history:{user_id}"
                # Get last N events (simple approach: get all and filter)
                # In production with large lists, use LRANGE carefully or Redis Stream
                events = await cache_service.redis.lrange(history_key, 0, -1)
                
                last_seq_int = int(last_event_id)
                replayed_count = 0
                
                # Events are stored in order. We need to find where last_seq is.
                # NOTE: lrange returns list, we assume appending order.
                for event_raw in events:
                    try:
                        event = json.loads(event_raw)
                        seq = event.get("seq", 0)
                        if seq > last_seq_int:
                            # This is a missed event
                            await queue.put(event)
                            replayed_count += 1
                    except Exception:
                        continue
                
                if replayed_count > 0:
                    logger.info(f"Replayed {replayed_count} events for user {user_id} since {last_event_id}")
            except Exception as e:
                logger.error(f"SSE Replay failed for user {user_id}: {e}")

        return queue

    async def disconnect(self, user_id: str, queue: asyncio.Queue):
        """
        断开 SSE 连接

        Args:
            user_id: 用户 ID
            queue: 事件队列
        """
        if user_id in self.connections:
            self.connections[user_id].discard(queue)

            if not self.connections[user_id]:
                del self.connections[user_id]

        logger.info(f"SSE connection closed for user {user_id}")

    async def send_to_user(self, user_id: str, event_type: str, data: dict):
        """
        向特定用户推送事件
        """
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        
        # Generate Sequence ID (Timestamp in ms for simplicity)
        seq = int(time.time() * 1000)
        
        event_data = {
            "type": event_type,
            "data": data,
            "seq": seq
        }
        
        # 1. Store in Redis for Replay (Buffer 60s or 100 items)
        if cache_service.redis:
            try:
                history_key = f"sse:history:{user_id_str}"
                raw = json.dumps(event_data, ensure_ascii=False)
                await cache_service.redis.rpush(history_key, raw)
                await cache_service.redis.ltrim(history_key, -100, -1) # Keep last 100
                await cache_service.redis.expire(history_key, 60) # TTL 60s
            except Exception as e:
                logger.error(f"Failed to buffer SSE event: {e}")

        if user_id_str not in self.connections:
            logger.debug(f"No active SSE connections for user {user_id_str}")
            return

        # 2. Push to active queues
        for queue in self.connections[user_id_str]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Error sending SSE event to user {user_id_str}: {e}")

        logger.debug(f"Sent SSE event '{event_type}' (seq={seq}) to user {user_id_str}")

    async def broadcast(self, event_type: str, data: dict):
        """
        向所有连接的用户广播事件
        (Broadcast typically doesn't support replay per user easily unless we duplicate, 
         skipping replay for broadcast for now or using a global channel)
        """
        event_data = {
            "type": event_type,
            "data": data,
            "seq": int(time.time() * 1000)
        }

        for user_id, queues in self.connections.items():
            for queue in queues:
                try:
                    await queue.put(event_data)
                except Exception as e:
                    logger.error(f"Error broadcasting SSE event to user {user_id}: {e}")

        logger.debug(f"Broadcasted SSE event '{event_type}' to all users")

    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return sum(len(queues) for queues in self.connections.values())


# 全局 SSE 管理器实例
sse_manager = SSEManager()


async def event_generator(queue: asyncio.Queue):
    """
    SSE 事件生成器

    Args:
        queue: 事件队列

    Yields:
        str: SSE 格式的事件数据
    """
    try:
        while True:
            # 等待事件
            event_data = await queue.get()

            # 格式化为 SSE 格式
            event_type = event_data.get("type", "message")
            data = event_data.get("data", {})
            seq = event_data.get("seq")

            # SSE Standard: id field for reconciliation
            if seq is not None:
                yield f"id: {seq}\n"
            
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    except asyncio.CancelledError:
        logger.debug("SSE event generator cancelled")
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
