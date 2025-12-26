"""
WebSocket Connection Manager
"""
from typing import Dict, List, Optional
from fastapi import WebSocket
from uuid import UUID
import json
import asyncio
from loguru import logger
import redis.asyncio as redis
from app.config import settings

class ConnectionManager:
    def __init__(self):
        # 存储活跃群组连接: group_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储活跃用户全局连接: user_id -> WebSocket
        self.user_connections: Dict[str, WebSocket] = {}
        
        # Redis Pub/Sub
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.listener_task: Optional[asyncio.Task] = None

    async def init_redis(self):
        """Initialize Redis connection for Pub/Sub"""
        try:
            self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            self.pubsub = self.redis.pubsub()
            self.listener_task = asyncio.create_task(self._redis_listener())
            logger.info("WebSocket Redis Pub/Sub initialized")
        except Exception as e:
            logger.error(f"Failed to init WebSocket Redis: {e}")

    async def close_redis(self):
        """Close Redis connection"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()

    async def _redis_listener(self):
        """Listen for messages from Redis and dispatch locally"""
        try:
            # Initial subscription to catch all relevant patterns if needed, 
            # or we rely on dynamic subscription.
            # For simplicity in this architecture, we might subscribe to a global channel 
            # and filter, OR maintain dynamic subscriptions.
            # Dynamic is better for scale but complex.
            # Let's use a simple pattern: instance subscribes to channels it cares about?
            # Actually, `psubscribe` is easier if we have a consistent naming convention.
            # But we only want to receive messages for users/groups WE have locally.
            
            # Hybrid approach: 
            # When a local connection is added, we subscribe to that channel on Redis.
            # When removed, we unsubscribe.
            
            # Since self.pubsub is shared, we just need to ensure the loop runs.
            while True:
                if self.pubsub:
                    try:
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
        """Handle incoming Redis message"""
        channel = message['channel']
        raw_data = message['data']
        
        try:
            data = json.loads(raw_data)
            # Channel format: "group:{id}" or "user:{id}"
            if channel.startswith("group:"):
                group_id = channel.split(":")[1]
                # Special handling for control messages
                if isinstance(data, dict) and data.get("type") == "kick_group":
                    await self._kick_local(group_id, data["user_id"], data.get("reason", ""))
                else:
                    await self._broadcast_local(data, group_id)
            elif channel.startswith("user:"):
                user_id = channel.split(":")[1]
                await self._send_personal_local(data, user_id)
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _subscribe(self, channel: str):
        if self.pubsub:
            await self.pubsub.subscribe(channel)

    async def _unsubscribe(self, channel: str):
        if self.pubsub:
            await self.pubsub.unsubscribe(channel)

    async def connect(self, websocket: WebSocket, group_id: str, user_id: str):
        """连接到群组 (Existing logic)"""
        await websocket.accept()
        # Tag user_id for easier management
        websocket.user_id = user_id 
        
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
            # Subscribe to Redis channel for this group
            await self._subscribe(f"group:{group_id}")
            
        self.active_connections[group_id].append(websocket)
        logger.info(f"User {user_id} connected to group {group_id}")

    async def connect_user(self, websocket: WebSocket, user_id: str):
        """连接到用户个人通道 (New logic)"""
        await websocket.accept()
        websocket.user_id = user_id
        self.user_connections[user_id] = websocket
        # Subscribe to Redis channel for this user
        await self._subscribe(f"user:{user_id}")
        logger.info(f"User {user_id} connected to personal channel")

    async def disconnect(self, websocket: WebSocket, group_id: str, user_id: str):
        """断开群组连接"""
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
                self.active_connections[group_id].remove(websocket)
                if not self.active_connections[group_id]:
                    del self.active_connections[group_id]
                    # Unsubscribe if no local listeners
                    await self._unsubscribe(f"group:{group_id}")
        logger.info(f"User {user_id} disconnected from group {group_id}")

        async def disconnect_user(self, user_id: str):

            """断开用户个人通道"""

            if user_id in self.user_connections:

                del self.user_connections[user_id]

                # Unsubscribe

                await self._unsubscribe(f"user:{user_id}")

            logger.info(f"User {user_id} disconnected from personal channel")

    

        async def kick_user_from_group(self, group_id: str, user_id: str, reason: str = "kicked"):

            """强制断开用户在特定群组的连接 (Distributed via Redis)"""

            if self.redis:

                kick_msg = {

                    "type": "kick_group",

                    "group_id": group_id,

                    "user_id": user_id,

                    "reason": reason

                }

                await self.redis.publish(f"group:{group_id}", json.dumps(kick_msg))

            else:

                await self._kick_local(group_id, user_id, reason)

    

        async def _kick_local(self, group_id: str, user_id: str, reason: str):

            if group_id in self.active_connections:

                for ws in list(self.active_connections[group_id]):

                    if hasattr(ws, 'user_id') and ws.user_id == user_id:

                        try:

                            await ws.send_json({"type": "error", "message": f"You were removed from group: {reason}"})

                            await ws.close(code=4001)

                        except:

                            pass

    

        async def broadcast(self, message: dict, group_id: str):

            """广播消息到群组 (Via Redis)"""

            # Publish to Redis

            if self.redis:

                await self.redis.publish(f"group:{group_id}", json.dumps(message, default=str))

            else:

                # Fallback to local only if Redis not available (e.g. testing)

                await self._broadcast_local(message, group_id)

    

        async def _broadcast_local(self, message: dict, group_id: str):

            """广播到本地连接"""

            if group_id in self.active_connections:

                json_msg = json.dumps(message, default=str)

                connections_to_remove = []

                for connection in self.active_connections[group_id]:

                    try:

                        await connection.send_text(json_msg)

                    except Exception as e:

                        logger.error(f"Error sending message to group {group_id}: {e}")

                        connections_to_remove.append(connection)

                

                for connection in connections_to_remove:

                    if connection in self.active_connections[group_id]:

                        self.active_connections[group_id].remove(connection)

                

                if not self.active_connections[group_id]:

                    del self.active_connections[group_id]

                    await self._unsubscribe(f"group:{group_id}")

    

        async def send_personal_message(self, message: dict, user_id: str):

            """发送私信给特定用户 (Via Redis)"""

            if self.redis:

                await self.redis.publish(f"user:{user_id}", json.dumps(message, default=str))

            else:

                await self._send_personal_local(message, user_id)

    

        async def _send_personal_local(self, message: dict, user_id: str):

            """发送私信到本地用户连接"""

            if user_id in self.user_connections:

                try:

                    json_msg = json.dumps(message, default=str)

                    await self.user_connections[user_id].send_text(json_msg)

                except Exception as e:

                    logger.error(f"Error sending personal message to {user_id}: {e}")

                    if user_id in self.user_connections:

                        del self.user_connections[user_id]

                        await self._unsubscribe(f"user:{user_id}")

    

        async def notify_status_change(self, user_id: str, status: str, friend_ids: List[str]):

            """通知好友状态变更"""

            message = {

                "type": "status_update",

                "user_id": user_id,

                "status": status

            }

            # Publish to each friend's channel

            if self.redis:

                json_msg = json.dumps(message, default=str)

                for fid in friend_ids:

                    await self.redis.publish(f"user:{fid}", json_msg)

            else:

                # Local fallback

                for fid in friend_ids:

                    await self._send_personal_local(message, fid)

    

    manager = ConnectionManager()

    