"""
GalaxyStreamingService - 知识星图实时推送服务

通过WebSocket向用户推送知识星图的实时更新
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.event_bus import EventBus
from app.core.websocket import ConnectionManager


class GalaxyStreamingService:
    """
    知识星图实时推送服务

    监听知识星图相关事件，并通过WebSocket推送给前端：
    1. 掌握度更新事件
    2. 知识拓展完成事件
    3. 节点解锁事件
    4. 升级事件
    """

    # WebSocket消息类型
    MSG_MASTERY_UPDATED = "galaxy.mastery_updated"
    MSG_NODE_EXPANDED = "galaxy.nodes_expanded"
    MSG_NODE_UNLOCKED = "galaxy.node_unlocked"
    MSG_LEVEL_UP = "galaxy.level_up"
    MSG_BATCH_UPDATE = "galaxy.batch_update"

    def __init__(
        self,
        websocket_manager: ConnectionManager,
        event_bus: EventBus
    ):
        self.ws_manager = websocket_manager
        self.event_bus = event_bus
        self._running = False
        self._consumer_started = False

    async def start(self):
        """启动事件监听和推送"""
        if self._consumer_started:
            logger.warning("GalaxyStreamingService already started")
            return

        await self.event_bus.connect()
        self._running = True

        try:
            # 订阅掌握度更新事件
            await self.event_bus.subscribe(
                stream="sparkle_events",
                group_name="galaxy_streamers",
                consumer_name=f"galaxy_streamer-{datetime.utcnow().timestamp()}",
                callback=self._on_event
            )

            self._consumer_started = True
            logger.info("GalaxyStreamingService started successfully")

        except Exception as e:
            logger.error(f"Failed to start GalaxyStreamingService: {e}")
            self._running = False

    async def _on_event(self, event_data: dict):
        """处理接收到的事件"""
        event_type = event_data.get("event_type")

        try:
            if event_type == "node_mastery_updated":
                await self._on_mastery_updated(event_data)

        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")

    async def _on_mastery_updated(self, event_data: dict):
        """处理掌握度更新事件"""
        try:
            user_id = UUID(event_data.get("user_id"))
            node_id = UUID(event_data.get("node_id"))
            old_mastery = int(event_data.get("old_mastery", 0))
            new_mastery = int(event_data.get("new_mastery", 0))
            reason = event_data.get("reason", "")

            # 检查是否有升级
            old_level = old_mastery // 10
            new_level = new_mastery // 10

            # 发送掌握度更新消息
            await self.broadcast_mastery_update(
                user_id=user_id,
                node_id=node_id,
                old_mastery=old_mastery,
                new_mastery=new_mastery,
                reason=reason
            )

            # 如果有升级，发送升级通知
            if new_level > old_level:
                await self.broadcast_level_up(
                    user_id=user_id,
                    node_id=node_id,
                    old_level=old_level,
                    new_level=new_level
                )

            # 如果是首次解锁，发送解锁通知
            if old_mastery == 0 and new_mastery > 0:
                node_name = await self._get_node_name(node_id)
                if node_name:
                    await self.broadcast_node_unlocked(
                        user_id=user_id,
                        node_id=node_id,
                        node_name=node_name
                    )

        except Exception as e:
            logger.error(f"Error in _on_mastery_updated: {e}")

    async def _get_node_name(self, node_id: UUID) -> str | None:
        """获取节点名称（用于推送通知）"""
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.galaxy import KnowledgeNode

            async with AsyncSessionLocal() as db:
                node = await db.get(KnowledgeNode, node_id)
                if node:
                    return node.name
        except Exception as e:
            logger.error(f"Error getting node name: {e}")
        return None

    async def broadcast_mastery_update(
        self,
        user_id: UUID,
        node_id: UUID,
        old_mastery: int,
        new_mastery: int,
        reason: str = ""
    ):
        """推送掌握度更新"""
        message = {
            "type": self.MSG_MASTERY_UPDATED,
            "data": {
                "node_id": str(node_id),
                "old_mastery": old_mastery,
                "new_mastery": new_mastery,
                "delta": new_mastery - old_mastery,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await self._send_to_user(user_id, message)
        logger.debug(f"Sent mastery update: user={user_id}, node={node_id}, {old_mastery}→{new_mastery}")

    async def broadcast_node_expanded(
        self,
        user_id: UUID,
        trigger_node_id: UUID,
        new_nodes: list[dict[str, Any]]
    ):
        """推送知识拓展结果"""
        message = {
            "type": self.MSG_NODE_EXPANDED,
            "data": {
                "trigger_node_id": str(trigger_node_id),
                "new_nodes": new_nodes,
                "count": len(new_nodes),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await self._send_to_user(user_id, message)
        logger.info(f"Sent node expansion: user={user_id}, count={len(new_nodes)}")

    async def broadcast_node_unlocked(
        self,
        user_id: UUID,
        node_id: UUID,
        node_name: str
    ):
        """推送节点解锁通知"""
        message = {
            "type": self.MSG_NODE_UNLOCKED,
            "data": {
                "node_id": str(node_id),
                "node_name": node_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await self._send_to_user(user_id, message)
        logger.info(f"Sent node unlock: user={user_id}, node={node_name}")

    async def broadcast_level_up(
        self,
        user_id: UUID,
        node_id: UUID,
        old_level: int,
        new_level: int
    ):
        """推送升级通知"""
        message = {
            "type": self.MSG_LEVEL_UP,
            "data": {
                "node_id": str(node_id),
                "old_level": old_level,
                "new_level": new_level,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await self._send_to_user(user_id, message)
        logger.info(f"Sent level up: user={user_id}, node={node_id}, level {old_level}→{new_level}")

    async def broadcast_batch_update(
        self,
        user_id: UUID,
        updates: list[dict[str, Any]]
    ):
        """批量推送多个节点更新"""
        message = {
            "type": self.MSG_BATCH_UPDATE,
            "data": {
                "updates": updates,
                "count": len(updates),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await self._send_to_user(user_id, message)
        logger.info(f"Sent batch update: user={user_id}, count={len(updates)}")

    async def _send_to_user(self, user_id: UUID, message: dict):
        """发送消息给指定用户"""
        try:
            # 使用 ConnectionManager 发送个人消息
            await self.ws_manager.send_personal_message(message, str(user_id))

        except Exception as e:
            logger.error(f"Failed to send galaxy update to user {user_id}: {e}")

    def stop(self):
        """停止服务"""
        self._running = False
        logger.info("GalaxyStreamingService stopped")


# 全局单例（延迟初始化）
_galaxy_streaming_service: GalaxyStreamingService | None = None


def get_galaxy_streaming_service() -> GalaxyStreamingService | None:
    """获取 GalaxyStreamingService 单例"""
    return _galaxy_streaming_service


async def init_galaxy_streaming_service(
    websocket_manager: ConnectionManager,
    event_bus: EventBus
) -> GalaxyStreamingService:
    """初始化 GalaxyStreamingService 单例"""
    global _galaxy_streaming_service

    if _galaxy_streaming_service is None:
        _galaxy_streaming_service = GalaxyStreamingService(
            websocket_manager=websocket_manager,
            event_bus=event_bus
        )
        await _galaxy_streaming_service.start()

    return _galaxy_streaming_service
