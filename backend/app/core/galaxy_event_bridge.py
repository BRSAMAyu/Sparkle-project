"""
Galaxy Event Bridge - 将 EventBus 事件转发到 SSE Manager
用于实现前端星图的实时更新动画
"""
from __future__ import annotations

import asyncio

from loguru import logger

from app.core.event_bus import event_bus
from app.core.sse import sse_manager

# 访客用户 ID（从 guest_seed_service 可见）
GUEST_USER_ID = "guest_sparkle_demo_visitor"


class GalaxyEventBridge:
    """
    将 EventBus 中的 Galaxy 相关事件转发到 SSE Manager

    订阅 Redis Stream "sparkle_events"，过滤出 galaxy 相关事件，
    然后通过 SSE 推送给前端。
    """

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """启动桥接器，订阅 EventBus"""
        if self._running:
            logger.warning("GalaxyEventBridge already running")
            return

        await event_bus.connect()
        self._running = True
        # subscribe 方法内部会创建后台任务并存储到 event_bus._consumer_tasks
        await event_bus.subscribe(
            stream="sparkle_events",
            group_name="galaxy_sse_bridge",
            consumer_name="bridge_1",
            callback=self._handle_event
        )
        logger.info("GalaxyEventBridge started")

    async def stop(self):
        """停止桥接器"""
        self._running = False
        # event_bus.close() 会在 grpc_server 的 GracefulShutdown 中统一调用
        # 这里只需要标记不再处理事件
        logger.info("GalaxyEventBridge stopped")

    async def _handle_event(self, payload: dict):
        """
        处理 EventBus 事件并转发到 SSE

        Args:
            payload: 事件载荷，包含 event_type, user_id 等字段
        """
        event_type = payload.get("event_type", "")
        user_id = payload.get("user_id")

        if not user_id:
            return

        # 只处理 galaxy 相关事件
        if event_type in ("galaxy.node.updated", "knowledge_node_updated", "node_mastery_updated"):
            await sse_manager.send_to_user(
                user_id=user_id,
                event_type="galaxy.node.updated",
                data={
                    "node_id": payload.get("node_id"),
                    "new_mastery": payload.get("new_mastery"),
                    "old_mastery": payload.get("old_mastery"),
                    "reason": payload.get("reason", "unknown"),
                }
            )
            logger.debug(
                f"Forwarded galaxy.node.updated to SSE: user={user_id} node={payload.get('node_id')}"
            )
        elif event_type == "error_created":
            await sse_manager.send_to_user(
                user_id=user_id,
                event_type="galaxy.error.created",
                data={
                    "error_id": payload.get("error_id"),
                    "linked_node_ids": payload.get("linked_node_ids", []),
                }
            )
            logger.debug(
                f"Forwarded galaxy.error.created to SSE: user={user_id} error={payload.get('error_id')}"
            )


# 全局实例
galaxy_event_bridge = GalaxyEventBridge()
