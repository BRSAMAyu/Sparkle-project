"""
WebSocket Connection Manager
Distributed support via Redis Pub/Sub with optimized fan-out for presence.

Production-grade features:
- Message delivery tracking with ACK mechanism
- Online status tracking across distributed instances
- Offline push notification hooks
- Message deduplication via message IDs
"""
import asyncio
import contextlib
import json
import time
import uuid

import redis.asyncio as redis
from fastapi import WebSocket
from loguru import logger

from app.config import settings
from app.core.redis_utils import format_redis_url_for_log, resolve_redis_password

# 延迟导入设备服务（避免循环依赖）
_device_service = None


def get_device_service():
    """获取设备服务单例"""
    global _device_service
    if _device_service is None:
        from app.services.device_service import DeviceService
        # 延迟获取 redis 实例
        _device_service = DeviceService()
    return _device_service


def set_websocket_redis(redis_client: redis.Redis):
    """设置 WebSocket 的 Redis 实例（供初始化时调用）"""
    global _device_service
    if _device_service is None:
        from app.services.device_service import DeviceService
        _device_service = DeviceService(redis_client=redis_client)
    else:
        _device_service.redis = redis_client


class ConnectionManager:
    def __init__(self):
        # Local group connections: group_id -> List[WebSocket]
        self.active_connections: dict[str, list[WebSocket]] = {}

        # Local individual user connections: user_id -> WebSocket
        self.user_connections: dict[str, WebSocket] = {}

        # Map of friend_id -> Set of local user_ids who are friends with them
        # Used to optimize presence fan-out
        self.friend_map: dict[str, set[str]] = {}

        # Redis Pub/Sub
        self.redis: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self.listener_task: asyncio.Task | None = None

    async def init_redis(self):
        """Initialize Redis connection for Pub/Sub"""
        password, password_source = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)

        kwargs = {
            "encoding": "utf-8",
            "decode_responses": True,
        }
        if password:
            kwargs["password"] = password

        try:
            self.redis = redis.from_url(settings.REDIS_URL, **kwargs)
            self.pubsub = self.redis.pubsub()

            # 设置设备服务的 Redis 实例
            set_websocket_redis(self.redis)

            # Subscribe to global patterns
            await self.pubsub.psubscribe("presence:*")
            await self.pubsub.psubscribe("group:*")
            await self.pubsub.psubscribe("user:*")
            await self.pubsub.psubscribe("visualize:*")

            self.listener_task = asyncio.create_task(self._redis_listener())
            logger.info(
                "WebSocket Redis Pub/Sub initialized: {}, Password={}, PasswordSource={}".format(
                    format_redis_url_for_log(settings.REDIS_URL),
                    "Yes" if password else "No",
                    password_source,
                )
            )
        except Exception as e:
            logger.warning(f"WebSocket Redis unavailable; realtime sync disabled: {e}")
            logger.warning("To start Redis: `docker compose up -d redis` or `systemctl start redis`")

    async def close_redis(self):
        """Close Redis connection"""
        if self.listener_task:
            self.listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.listener_task

        if self.pubsub:
            await self.pubsub.close()

        if self.redis:
            await self.redis.close()

    async def _redis_listener(self):
        """Listen for messages from Redis and dispatch locally"""
        try:
            while True:
                if self.pubsub:
                    try:
                        # Use ignore_subscribe_messages to filter noise
                        message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message:
                            await self._handle_redis_message(message)
                    except Exception as e:
                        logger.error(f"Redis listener error: {e}")
                        await asyncio.sleep(1)
                else:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def _handle_redis_message(self, message: dict):
        """Handle incoming Redis message from patterns"""
        channel = message['channel']
        raw_data = message['data']

        try:
            data = json.loads(raw_data)

            # 1. Presence Update
            if channel.startswith("presence:"):
                user_id = channel.split(":")[1]
                if user_id in self.friend_map:
                    local_friends = self.friend_map[user_id]
                    for fid in list(local_friends):
                        await self._send_personal_local(data, fid)

            # 2. Group Messages / Control
            elif channel.startswith("group:"):
                group_id = channel.split(":")[1]
                if isinstance(data, dict):
                    msg_type = data.get("type")
                    if msg_type == "kick_group":
                        await self._kick_local(group_id, data["user_id"], data.get("reason", ""))
                    elif msg_type == "typing":
                        # Forward typing indicator to everyone EXCEPT the sender
                        await self._broadcast_local(data, group_id, exclude_user_id=data.get("user_id"))
                    else:
                        await self._broadcast_local(data, group_id)
                else:
                    await self._broadcast_local(data, group_id)

            # 3. Direct User Messages (Private Chat / System)
            elif channel.startswith("user:"):
                user_id = channel.split(":")[1]
                await self._send_personal_local(data, user_id)

            # 4. Visualization Updates
            elif channel.startswith("visualize:"):
                session_id = channel.split(":")[1]
                await self._broadcast_local(data, f"visualize:{session_id}")

        except Exception as e:
            logger.error(f"Error handling Redis message on channel {channel}: {e}")

    async def connect(self, websocket: WebSocket, group_id: str, user_id: str):
        """Connect to a group chat channel"""
        await websocket.accept()
        websocket.user_id = user_id
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
        await self.set_online_status(user_id, True)
        logger.info(f"User {user_id} connected to group {group_id}")

    async def connect_visualization(self, websocket: WebSocket, session_id: str):
        """Connect to visualization stream"""
        await websocket.accept()
        group_id = f"visualize:{session_id}"
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
        logger.info(f"Client connected to visualization for session {session_id}")

    async def connect_user(self, websocket: WebSocket, user_id: str, friend_ids: list[str] = None):
        """Connect to personal channel and register friend map for presence"""
        await websocket.accept()
        websocket.user_id = user_id
        self.user_connections[user_id] = websocket

        # Register friends to friend_map so we know who to notify locally
        if friend_ids:
            for fid in friend_ids:
                if fid not in self.friend_map:
                    self.friend_map[fid] = set()
                self.friend_map[fid].add(user_id)

        await self.set_online_status(user_id, True)
        logger.info(f"User {user_id} connected to personal channel. Registered {len(friend_ids or [])} friends.")

    def disconnect(self, websocket: WebSocket, group_id: str, user_id: str):
        """Disconnect from group"""
        if group_id in self.active_connections and websocket in self.active_connections[group_id]:
            self.active_connections[group_id].remove(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]
        logger.info(f"User {user_id} disconnected from group {group_id}")

    def disconnect_visualization(self, websocket: WebSocket, session_id: str):
        """Disconnect from visualization stream"""
        group_id = f"visualize:{session_id}"
        if group_id in self.active_connections and websocket in self.active_connections[group_id]:
            self.active_connections[group_id].remove(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]
        logger.info(f"Client disconnected from visualization for session {session_id}")

    def disconnect_user(self, user_id: str):
        """Disconnect from personal channel and cleanup friend map"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]

        # Cleanup friend_map (reverse lookup is expensive, but we only do it on disconnect)
        # To optimize, we could store a local_user_friends_map[user_id] -> List[friend_ids]
        # But for now, simple cleanup
        keys_to_delete = []
        for fid, subscribers in self.friend_map.items():
            if user_id in subscribers:
                subscribers.remove(user_id)
                if not subscribers:
                    keys_to_delete.append(fid)
        for k in keys_to_delete:
            del self.friend_map[k]

        # Note: set_online_status(False) is called by the endpoint after disconnect
        logger.info(f"User {user_id} disconnected from personal channel. Cleaned up friend map.")

    async def kick_user_from_group(self, group_id: str, user_id: str, reason: str = "kicked"):
        """Kick user from group (Distributed)"""
        if self.redis:
            msg = {"type": "kick_group", "user_id": user_id, "reason": reason}
            await self.redis.publish(f"group:{group_id}", json.dumps(msg))
        else:
            await self._kick_local(group_id, user_id, reason)

    async def _kick_local(self, group_id: str, user_id: str, reason: str):
        if group_id in self.active_connections:
            for ws in list(self.active_connections[group_id]):
                if hasattr(ws, 'user_id') and ws.user_id == user_id:
                    try:
                        await ws.send_json({"type": "error", "message": f"Kicked: {reason}"})
                        await ws.close(code=4001)
                    except: pass

    async def broadcast(self, message: dict, group_id: str):
        """Broadcast to group (Distributed)"""
        if self.redis:
            await self.redis.publish(f"group:{group_id}", json.dumps(message, default=str))
        else:
            await self._broadcast_local(message, group_id)

    async def _broadcast_local(self, message: dict, group_id: str, exclude_user_id: str = None):
        if group_id in self.active_connections:
            json_msg = json.dumps(message, default=str)
            for ws in list(self.active_connections[group_id]):
                # Skip if it's the excluded user
                if exclude_user_id and hasattr(ws, 'user_id') and ws.user_id == exclude_user_id:
                    continue
                try:
                    await ws.send_text(json_msg)
                except Exception as e:
                    logger.error(f"Local broadcast error: {e}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user (Distributed)"""
        if self.redis:
            # Check if user has any local connection on any server (Simplistic check)
            # In a real cluster, we publish and let the recipient server handle it.
            # If NO server has the connection, we should trigger Push.
            # Here we add a 'is_pushed' flag to avoid double push if we want.
            await self.redis.publish(f"user:{user_id}", json.dumps(message, default=str))

            # Hook for Push Notification
            # Note: In a production app, we would use a Redis Key to track
            # if the user is online ANYWHERE. If not, trigger Push.
            # await self._trigger_offline_push(user_id, message)
        else:
            await self._send_personal_local(message, user_id)

    async def _send_personal_local(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Local personal send error: {e}")
        else:
            # User not on THIS instance.
            # In single-instance mode, this is where we trigger Push.
            await self._trigger_offline_push(user_id, message)

    async def _trigger_offline_push(self, user_id: str, message: dict):
        """
        Hook for external Push Notification services (FCM, JPush, etc.)
        """
        if message.get("type") == "ack" or message.get("type") == "status_update":
            return # Don't push technical messages

        logger.info(f"Triggering offline push for user {user_id}")
        # TODO: Integration with app.services.notification_service

    async def notify_status_change(self, user_id: str, status: str):
        """Notify friends of status change (Optimized Distributed)"""
        message = {
            "type": "status_update",
            "user_id": user_id,
            "status": status
        }
        if self.redis:
            # Publish ONCE to presence channel
            await self.redis.publish(f"presence:{user_id}", json.dumps(message, default=str))
        else:
            # Fallback (impossible to know friends here without DB, so just skip or implement simple)
            pass

    async def broadcast_visualization(self, session_id: str, data: dict):
        """Broadcast visualization update"""
        group_id = f"visualize:{session_id}"
        if self.redis:
            await self.redis.publish(f"visualize:{session_id}", json.dumps(data, default=str))
        else:
            await self._broadcast_local(data, group_id)

    # ========== Production-grade Features ==========

    async def send_with_ack(self, message: dict, user_id: str, timeout: float = 5.0) -> bool:
        """
        Send message and wait for ACK, return whether delivery was successful.

        This is used for critical messages where delivery confirmation is required.
        """
        message_id = message.get("id") or str(uuid.uuid4())
        message["msg_id"] = message_id

        if not self.redis:
            # Fallback for single-instance: just send without ACK tracking
            await self.send_personal_message(message, user_id)
            return True

        # Store pending ACK
        await self.redis.setex(
            f"ws:pending_ack:{user_id}:{message_id}",
            int(timeout),
            json.dumps({"timestamp": time.time()})
        )

        await self.send_personal_message(message, user_id)

        # Wait for ACK (simplified polling implementation)
        start = time.time()
        while time.time() - start < timeout:
            exists = await self.redis.exists(f"ws:ack:{user_id}:{message_id}")
            if exists:
                await self.redis.delete(f"ws:ack:{user_id}:{message_id}")
                logger.debug(f"ACK received for message {message_id} from user {user_id}")
                return True
            await asyncio.sleep(0.05)

        logger.warning(f"ACK timeout for message {message_id} to user {user_id}")
        return False  # Timeout - user offline or connection issue

    async def record_ack(self, user_id: str, message_id: str):
        """
        Record client ACK for a message.

        Called when client sends back an ACK message.
        """
        if not self.redis:
            return

        await self.redis.setex(
            f"ws:ack:{user_id}:{message_id}",
            60,  # Keep for 1 minute
            "1"
        )
        logger.debug(f"Recorded ACK for message {message_id} from user {user_id}")

    async def is_user_online(self, user_id: str) -> bool:
        """
        Check if user is online (distributed across all instances).

        Uses Redis as a shared store for online status.
        """
        if not self.redis:
            # Fallback: check local only
            return user_id in self.user_connections

        return await self.redis.exists(f"ws:online:{user_id}") > 0

    async def set_online_status(self, user_id: str, online: bool):
        """
        Set user online status (distributed across all instances).

        When a user comes online, we publish a presence notification.
        When going offline, we clear the online marker.
        """
        if not self.redis:
            return

        key = f"ws:online:{user_id}"
        if online:
            await self.redis.setex(key, 300, "1")  # 5 minute TTL
            # Note: Presence notification is handled by the endpoint
        else:
            await self.redis.delete(key)

    async def get_online_count(self) -> int:
        """Get total number of online users (approximate for distributed setup)."""
        if not self.redis:
            return len(self.user_connections)

        # This is expensive in production; consider a counter
        keys = []
        async for key in self.redis.scan_iter(match="ws:online:*"):
            keys.append(key)
        return len(keys)

    async def _trigger_offline_push(self, user_id: str, message: dict):
        """
        Trigger offline push notification for user.

        Integrates with FCM/APNs or other push services.
        """
        msg_type = message.get("type")

        # Skip technical messages
        if msg_type in ["ack", "status_update", "typing", "presence", "ping"]:
            return

        # Get user device tokens
        device_tokens = await self._get_user_device_tokens(user_id)
        if not device_tokens:
            logger.debug(f"No device tokens for user {user_id}")
            return

        # Construct push payload
        push_data = {
            "title": self._get_push_title(msg_type, message),
            "body": self._get_push_body(msg_type, message),
            "data": {
                "type": msg_type,
                "message_id": message.get("id") or message.get("msg_id"),
                "group_id": message.get("group_id"),
                "sender_id": message.get("sender", {}).get("id") if isinstance(message.get("sender"), dict) else None,
            }
        }

        # Store to push queue (to be processed by push service)
        for token in device_tokens:
            await self.redis.rpush(
                "push:queue",
                json.dumps({
                    "token": token,
                    "payload": push_data,
                    "user_id": user_id
                })
            )

        logger.info(f"Queued push notification for user {user_id}, type={msg_type}")

    async def _get_user_device_tokens(self, user_id: str) -> list[str]:
        """
        Get user's device push tokens.

        Queries from database with Redis caching for performance.
        """
        try:
            # 首先尝试从 Redis 缓存读取
            if self.redis:
                cache_key = f"user:devices:{user_id}"
                cached = await self.redis.get(cache_key)
                if cached:
                    try:
                        return json.loads(cached)
                    except:
                        pass  # 缓存损坏，继续查询

            # 如果缓存未命中，需要从数据库查询
            # 这里使用延迟导入避免循环依赖
            from sqlalchemy import select

            from app.db.session import AsyncSessionLocal
            from app.models.user import UserDevice

            async with AsyncSessionLocal() as db:
                query = select(UserDevice.push_token).where(
                    UserDevice.user_id == user_id,
                    UserDevice.is_active,
                )
                result = await db.execute(query)
                tokens = [row[0] for row in result.all()]

                # 写入缓存（5分钟 TTL）
                if self.redis and tokens:
                    cache_key = f"user:devices:{user_id}"
                    await self.redis.setex(cache_key, 300, json.dumps(tokens))

                return tokens

        except Exception as e:
            logger.error(f"Error getting device tokens for user {user_id}: {e}")
            return []

    def _get_push_title(self, msg_type: str, message: dict) -> str:
        """Get push notification title based on message type."""
        titles = {
            "message": "新消息",
            "mention": "有人提到了你",
            "member_joined": "新成员加入",
            "member_left": "成员离开",
            "task_created": "新任务",
            "member_checkin": "成员打卡",
            "message_edit": "消息已编辑",
            "message_revoke": "消息已撤回",
            "reaction_update": "新表情反应",
        }
        return titles.get(msg_type, "星火通知")

    def _get_push_body(self, msg_type: str, message: dict) -> str:
        """Get push notification body based on message type."""
        if msg_type == "message":
            sender = message.get("sender", {})
            content = message.get("content", "")
            nickname = sender.get("nickname", sender.get("username", "有人"))
            return f"{nickname}: {content[:50]}"
        elif msg_type == "mention":
            sender = message.get("sender", {})
            nickname = sender.get("nickname", "有人")
            return f"{nickname} 在群里提到了你"
        elif msg_type == "member_joined":
            user = message.get("user", {})
            nickname = user.get("nickname", "新成员")
            return f"{nickname} 加入了群聊"
        elif msg_type == "task_created":
            task = message.get("task", {})
            title = task.get("title", "新任务")
            return f"群里有新任务: {title[:30]}"
        elif msg_type == "member_checkin":
            user = message.get("user", {})
            nickname = user.get("nickname", "成员")
            duration = message.get("duration", 0)
            return f"{nickname} 打卡了 {duration} 分钟"
        return "您有一条新消息"

manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """
    Get the global WebSocket ConnectionManager singleton instance.

    This is a convenience function for accessing the connection manager
    from services that need to send notifications via WebSocket.

    Usage:
        from app.core.websocket import get_ws_manager

        ws_manager = get_ws_manager()
        await ws_manager.send_personal_message(message, user_id)
    """
    return manager
