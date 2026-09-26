"""
Server-Sent Events (SSE) Manager
用于实时推送事件到前端
支持断点续传和事件重放
"""
from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

from loguru import logger

from app.config.phase5_config import phase5_config
from app.core.cache import cache_service
from app.core.redis_utils import ensure_awaitable


class SSEManager:
    """
    SSE 连接管理器
    管理所有活跃的 SSE 连接，支持向特定用户推送事件
    支持断点续传 (Last-Event-ID) 和 Redis 缓冲
    """

    def __init__(self):
        # {user_id: Set[queue]}
        self.connections: dict[str, set[asyncio.Queue]] = {}
        # {user_key: last_seq} per-user 严格单调 seq（wt299-p1-pair P1-2）
        self._last_seq: dict[str, int] = {}

    def _next_seq(self, user_key: str) -> int:
        """生成严格单调递增的事件序号。

        毫秒时间戳为主体；同一毫秒内（或时钟回拨时）取 last+1 兜底，
        保证 connect() 的 `seq > last_event_id` 重放过滤不丢同毫秒事件
        （修前同毫秒事件 seq 相同，重放按严格大于过滤会静默丢弃）。
        纯同步段（首个 await 之前完成），事件循环内天然原子。
        """
        now_ms = int(time.time() * 1000)
        last = self._last_seq.get(user_key, 0)
        seq = now_ms if now_ms > last else last + 1
        self._last_seq[user_key] = seq
        return seq

    async def connect(self, user_id: str, last_event_id: str | None = None) -> asyncio.Queue:
        """
        创建新的 SSE 连接

        Args:
            user_id: 用户 ID
            last_event_id: 客户端上次收到的事件ID (Replay support)

        Returns:
            asyncio.Queue: 事件队列
        """
        queue: asyncio.Queue = asyncio.Queue()

        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(queue)
        user_prefix = str(user_id)[:8]
        logger.info(f"SSE connection established for user {user_prefix}***")

        # Replay logic
        if last_event_id and cache_service.redis:
            try:
                history_key = f"sse:history:{user_id}"
                # Get last N events (simple approach: get all and filter)
                # In production with large lists, use LRANGE carefully or Redis Stream
                events = await ensure_awaitable(cache_service.redis.lrange(history_key, 0, -1))

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
                            # 限制重放数量，防止过大的重放
                            if replayed_count >= phase5_config.SSE_REPLAY_MAX_EVENTS:
                                logger.warning(
                                    f"Replay limit reached ({phase5_config.SSE_REPLAY_MAX_EVENTS}) "
                                    f"for user {str(user_id)[:8]}***"
                                )
                                break
                    except Exception:
                        continue

                if replayed_count > 0:
                    logger.info(f"Replayed {replayed_count} events for user {str(user_id)[:8]}*** since {last_event_id}")
            except Exception as e:
                logger.error(f"SSE Replay failed for user {str(user_id)[:8]}***: {e}")

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

        logger.info(f"SSE connection closed for user {str(user_id)[:8]}***")

    async def send_to_user(self, user_id: str, event_type: str, data: dict, trace_id: str | None = None, is_done: bool = False):
        """
        向特定用户推送事件
        """
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id

        # Generate Sequence ID（per-user 严格单调，同毫秒自增）
        seq = self._next_seq(user_id_str)

        event_data = {
            "type": event_type,
            "data": data,
            "seq": seq,
            "trace_id": trace_id,
            "done": is_done
        }

        # 1. Store in Redis for Replay (使用配置的缓冲区大小和 TTL)
        if cache_service.redis:
            try:
                history_key = f"sse:history:{user_id_str}"
                raw = json.dumps(event_data, ensure_ascii=False)
                await ensure_awaitable(cache_service.redis.rpush(history_key, raw))
                # 保留最近 N 条事件
                await ensure_awaitable(cache_service.redis.ltrim(
                    history_key,
                    -phase5_config.SSE_BUFFER_SIZE,
                    -1
                ))
                # 设置 TTL
                await cache_service.redis.expire(history_key, phase5_config.SSE_BUFFER_TTL)
            except Exception as e:
                logger.error(f"Failed to buffer SSE event: {e}")

        if user_id_str not in self.connections:
            logger.debug(f"No active SSE connections for user {str(user_id_str)[:8]}***")
            return

        # 2. Push to active queues
        for queue in self.connections[user_id_str]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Error sending SSE event to user {str(user_id_str)[:8]}***: {e}")

        logger.debug(f"Sent SSE event '{event_type}' (seq={seq}, done={is_done}) to user {str(user_id_str)[:8]}***")

    async def broadcast(self, event_type: str, data: dict):
        """
        向所有连接的用户广播事件
        (Broadcast typically doesn't support replay per user easily unless we duplicate,
         skipping replay for broadcast for now or using a global channel)
        """
        event_data = {
            "type": event_type,
            "data": data,
            "seq": self._next_seq("__broadcast__")
        }

        for user_id, queues in self.connections.items():
            for queue in queues:
                try:
                    await queue.put(event_data)
                except Exception as e:
                    logger.error(f"Error broadcasting SSE event to user {str(user_id)[:8]}***: {e}")

        logger.debug(f"Broadcasted SSE event '{event_type}' to all users")

    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return sum(len(queues) for queues in self.connections.values())


# 全局 SSE 管理器实例
sse_manager = SSEManager()


async def event_generator(queue: asyncio.Queue):
    """
    SSE 事件生成器

    队列空闲期每隔 phase5_config.SSE_HEARTBEAT_INTERVAL 秒产出一条 SSE 注释帧
    ``: heartbeat\n\n``，保持链路（engine → gateway ReverseProxy → 客户端）字节
    流动，防止中间层因读空闲掐断连接。注释帧不携带 event:/data: 字段，网关逐字节
    透传，客户端解析器（如 mobile _parseSSE）会静默忽略，不触发任何事件处理。

    Args:
        queue: 事件队列

    Yields:
        str: SSE 格式的事件数据
    """
    try:
        while True:
            # 等待事件；超时则发心跳注释帧（SSE-HB）
            try:
                event_data = await asyncio.wait_for(
                    queue.get(),
                    timeout=phase5_config.SSE_HEARTBEAT_INTERVAL,
                )
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue

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
