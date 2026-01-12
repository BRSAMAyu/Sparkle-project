import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio
import redis.asyncio as redis
from typing import Dict, List

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.config import settings

app = FastAPI(title="Sparkle Visualization Service", version="1.0.0")

class VisualizationManager:
    def __init__(self):
        # session_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis = None
        self.pubsub = None
        self.listener_task = None

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]

    async def init_redis(self):
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.psubscribe("visualize:*")
        self.listener_task = asyncio.create_task(self._redis_listener())

    async def _redis_listener(self):
        try:
            while True:
                if self.pubsub:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        await self._handle_redis_message(message)
                else:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def _handle_redis_message(self, message: dict):
        channel = message['channel']
        data = message['data']
        
        if channel.startswith("visualize:"):
            session_id = channel.split(":")[1]
            if session_id in self.active_connections:
                # Broadcast
                for connection in list(self.active_connections[session_id]):
                    try:
                        await connection.send_text(data)
                    except Exception:
                        pass # Handle disconnects gracefully

manager = VisualizationManager()

@app.on_event("startup")
async def startup_event():
    await manager.init_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "visualization"}

@app.websocket("/ws/visualize/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
