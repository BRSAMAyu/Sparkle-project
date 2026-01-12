"""
Server-Sent Events (SSE) Manager
用于实时推送事件到前端
"""
import asyncio
import json
from typing import Dict, Set
from uuid import UUID
from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger


class SSEManager:
    """
    SSE 连接管理器
    管理所有活跃的 SSE 连接，支持向特定用户推送事件
    """

    def __init__(self):
        # {user_id: Set[queue]}
        self.connections: Dict[str, Set[asyncio.Queue]] = {}

    async def connect(self, user_id: str) -> asyncio.Queue:
        """
        创建新的 SSE 连接

        Args:
            user_id: 用户 ID

        Returns:
            asyncio.Queue: 事件队列
        """
        queue = asyncio.Queue()

        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(queue)
        logger.info(f"SSE connection established for user {user_id}")

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

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            data: 事件数据
        """
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id

        if user_id_str not in self.connections:
            logger.debug(f"No active SSE connections for user {user_id_str}")
            return

        event_data = {
            "type": event_type,
            "data": data
        }

        # 向该用户的所有连接推送
        for queue in self.connections[user_id_str]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Error sending SSE event to user {user_id_str}: {e}")

        logger.debug(f"Sent SSE event '{event_type}' to user {user_id_str}")

    async def broadcast(self, event_type: str, data: dict):
        """
        向所有连接的用户广播事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event_data = {
            "type": event_type,
            "data": data
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

            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    except asyncio.CancelledError:
        logger.debug("SSE event generator cancelled")
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
