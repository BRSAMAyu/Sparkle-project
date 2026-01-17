"""
WebSocket Connection Manager
Distributed support via Redis Pub/Sub with optimized fan-out for presence.
"""
from typing import Dict, List, Optional, Set
from fastapi import WebSocket
import json
import asyncio
from loguru import logger
import redis.asyncio as redis
from app.config import settings
from app.core.redis_utils import resolve_redis_password, format_redis_url_for_log

class ConnectionManager:
    def __init__(self):
        # Local group connections: group_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Local individual user connections: user_id -> WebSocket
        self.user_connections: Dict[str, WebSocket] = {}
        
        # Map of friend_id -> Set of local user_ids who are friends with them
        # Used to optimize presence fan-out
        self.friend_map: Dict[str, Set[str]] = {}

        # Redis Pub/Sub
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.listener_task: Optional[asyncio.Task] = None

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
        logger.info(f"User {user_id} connected to group {group_id}")

    async def connect_visualization(self, websocket: WebSocket, session_id: str):
        """Connect to visualization stream"""
        await websocket.accept()
        group_id = f"visualize:{session_id}"
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
        logger.info(f"Client connected to visualization for session {session_id}")

    async def connect_user(self, websocket: WebSocket, user_id: str, friend_ids: List[str] = None):
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
                
        logger.info(f"User {user_id} connected to personal channel. Registered {len(friend_ids or [])} friends.")

    def disconnect(self, websocket: WebSocket, group_id: str, user_id: str):
        """Disconnect from group"""
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
                self.active_connections[group_id].remove(websocket)
                if not self.active_connections[group_id]:
                    del self.active_connections[group_id]
        logger.info(f"User {user_id} disconnected from group {group_id}")

    def disconnect_visualization(self, websocket: WebSocket, session_id: str):
        """Disconnect from visualization stream"""
        group_id = f"visualize:{session_id}"
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
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

manager = ConnectionManager()
