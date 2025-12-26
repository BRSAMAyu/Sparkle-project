"""
WebSocket Connection Manager
"""
from typing import Dict, List, Optional
from fastapi import WebSocket
from uuid import UUID
import json
from loguru import logger

class ConnectionManager:
    def __init__(self):
        # 存储活跃群组连接: group_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储活跃用户全局连接: user_id -> WebSocket
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, group_id: str, user_id: str):
        """连接到群组 (Existing logic)"""
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
        # 注意：这里我们可能不需要把这个连接设为 user_connections，除非它是专门的
        # 但如果是 /groups/{id}/ws，它只负责群消息。
        # 如果我们有 /ws/me，那才是 user_connections
        logger.info(f"User {user_id} connected to group {group_id}")

    async def connect_user(self, websocket: WebSocket, user_id: str):
        """连接到用户个人通道 (New logic)"""
        await websocket.accept()
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to personal channel")

    def disconnect(self, websocket: WebSocket, group_id: str, user_id: str):
        """断开群组连接"""
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
                self.active_connections[group_id].remove(websocket)
                if not self.active_connections[group_id]:
                    del self.active_connections[group_id]
        logger.info(f"User {user_id} disconnected from group {group_id}")

    def disconnect_user(self, user_id: str):
        """断开用户个人通道"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"User {user_id} disconnected from personal channel")

    async def broadcast(self, message: dict, group_id: str):
        """广播消息到群组"""
        if group_id in self.active_connections:
            # 序列化消息
            json_msg = json.dumps(message, default=str)
            # 复制列表以避免在迭代时修改
            for connection in list(self.active_connections[group_id]):
                try:
                    await connection.send_text(json_msg)
                except Exception as e:
                    logger.error(f"Error sending message to group {group_id}: {e}")
                    # Remove broken connection? Or wait for disconnect?
                    pass

    async def send_personal_message(self, message: dict, user_id: str):
        """发送私信给特定用户"""
        if user_id in self.user_connections:
            try:
                json_msg = json.dumps(message, default=str)
                await self.user_connections[user_id].send_text(json_msg)
            except Exception as e:
                logger.error(f"Error sending personal message to {user_id}: {e}")
                # Remove if broken
                if user_id in self.user_connections:
                    del self.user_connections[user_id]

    async def notify_status_change(self, user_id: str, status: str, friend_ids: List[str]):
        """通知好友状态变更"""
        message = {
            "type": "status_update",
            "user_id": user_id,
            "status": status
        }
        json_msg = json.dumps(message, default=str)
        
        for fid in friend_ids:
            if fid in self.user_connections:
                try:
                    await self.user_connections[fid].send_text(json_msg)
                except Exception as e:
                    logger.error(f"Error sending status update to {fid}: {e}")

manager = ConnectionManager()