"""
WebSocket Connection Manager
"""
from typing import Dict, List, Set
from fastapi import WebSocket
from uuid import UUID
import json
from loguru import logger

class ConnectionManager:
    def __init__(self):
        # 存储活跃连接: group_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储用户连接: user_id -> WebSocket (用于私信或全局通知，暂时保留)
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, group_id: str, user_id: str):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to group {group_id}")

    def disconnect(self, websocket: WebSocket, group_id: str, user_id: str):
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
                self.active_connections[group_id].remove(websocket)
                if not self.active_connections[group_id]:
                    del self.active_connections[group_id]
        
        if user_id in self.user_connections:
            del self.user_connections[user_id]
            
        logger.info(f"User {user_id} disconnected from group {group_id}")

    async def broadcast(self, message: dict, group_id: str):
        if group_id in self.active_connections:
            # 序列化消息
            json_msg = json.dumps(message, default=str)
            for connection in self.active_connections[group_id]:
                try:
                    await connection.send_text(json_msg)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    # 可能需要在这里处理断开连接的逻辑

manager = ConnectionManager()
