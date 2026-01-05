"""
图数据库同步 Worker

消费 Redis Stream 中的同步事件，异步写入到 AGE
"""

import asyncio
import json
from typing import Dict, Any, Optional
from loguru import logger

from app.core.age_client import get_age_client, init_age
from app.core.cache import cache_service
from app.models.graph_models import KnowledgeVertex


class GraphSyncWorker:
    """图同步 Worker"""

    def __init__(self):
        self.age_client = get_age_client()
        self.redis = None
        self.running = False
        self.stream_key = "stream:graph_sync"
        self.group_name = "graph_sync_group"
        self.consumer_name = "worker_1"

    async def start(self):
        """启动 Worker"""
        logger.info("🚀 启动图同步 Worker...")

        # 初始化 Redis
        self.redis = cache_service.redis
        if not self.redis:
            logger.error("Redis 未初始化")
            return

        # 初始化 AGE
        await self.age_client.init_pool()

        # 创建消费组（如果不存在）
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                self.group_name,
                mkstream=True
            )
            logger.info(f"创建消费组: {self.group_name}")
        except Exception:
            logger.info(f"消费组 {self.group_name} 已存在")

        self.running = True

        # 开始消费
        await self._consume()

    async def stop(self):
        """停止 Worker"""
        logger.info("🛑 停止图同步 Worker...")
        self.running = False

    async def _consume(self):
        """消费消息"""
        logger.info("开始消费同步消息...")

        while self.running:
            try:
                # 读取消息（阻塞 5 秒）
                messages = await self.redis.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {self.stream_key: ">"},  # 从未确认的消息开始
                    count=10,
                    block=5000
                )

                if not messages:
                    continue

                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        try:
                            # 处理消息
                            await self._process_message(msg_id, msg_data)
                        except Exception as e:
                            logger.error(f"处理消息失败 {msg_id}: {e}")
                            # 可以选择重试或移到死信队列

            except asyncio.CancelledError:
                logger.info("Worker 被取消")
                break
            except Exception as e:
                logger.error(f"消费循环错误: {e}")
                await asyncio.sleep(1)  # 避免快速重试

    async def _process_message(self, msg_id: bytes, msg_data: Dict[bytes, bytes]):
        """处理单条消息"""
        # 解析消息
        msg_type = msg_data[b"type"].decode('utf-8')
        data = json.loads(msg_data[b"data"].decode('utf-8'))

        logger.debug(f"处理消息: {msg_type} - {data.get('id', 'N/A')}")

        try:
            if msg_type == "node_created":
                await self._handle_node_created(data)
            elif msg_type == "relation_created":
                await self._handle_relation_created(data)
            elif msg_type == "user_status_updated":
                await self._handle_user_status_updated(data)
            else:
                logger.warning(f"未知消息类型: {msg_type}")

            # 确认消息已处理
            await self.redis.xack(self.stream_key, self.group_name, msg_id)
            logger.debug(f"消息已确认: {msg_id}")

        except Exception as e:
            logger.error(f"处理消息 {msg_type} 失败: {e}")
            # 不确认消息，稍后重试
            raise

    async def _handle_node_created(self, data: Dict[str, Any]):
        """处理节点创建"""
        vertex = KnowledgeVertex(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            importance=int(data['importance']),
            sector=data['sector'],
            keywords=data['keywords'].split(',') if data['keywords'] else [],
            source_type=data['source_type']
        )

        await self.age_client.add_vertex("KnowledgeNode", vertex.to_dict())
        logger.debug(f"节点已同步到 AGE: {vertex.name}")

    async def _handle_relation_created(self, data: Dict[str, Any]):
        """处理关系创建"""
        await self.age_client.add_edge(
            from_label="KnowledgeNode",
            from_props={"id": data['source']},
            to_label="KnowledgeNode",
            to_props={"id": data['target']},
            edge_label=data['type'].upper(),
            edge_props={
                "strength": str(data['strength']),
                "created_by": data.get('created_by', 'seed')
            }
        )
        logger.debug(f"关系已同步到 AGE: {data['source']} → {data['target']}")

    async def _handle_user_status_updated(self, data: Dict[str, Any]):
        """处理用户状态更新"""
        user_id = data['user_id']
        node_id = data['node_id']
        study_minutes = data.get('study_minutes', 0)
        is_favorite = data.get('is_favorite', False)
        mastery_delta = data.get('mastery_delta', 0.0)

        # 创建用户兴趣边
        if is_favorite or study_minutes > 0:
            await self.age_client.add_edge(
                from_label="User",
                from_props={"id": user_id},
                to_label="KnowledgeNode",
                to_props={"id": node_id},
                edge_label="INTERESTED_IN",
                edge_props={
                    "strength": str(mastery_delta / 100 if mastery_delta > 0 else 0.5),
                    "last_accessed": data.get('timestamp', '')
                }
            )

        # 创建学习记录边
        if study_minutes > 0:
            await self.age_client.add_edge(
                from_label="User",
                from_props={"id": user_id},
                to_label="KnowledgeNode",
                to_props={"id": node_id},
                edge_label="STUDIED",
                edge_props={
                    "study_minutes": str(study_minutes),
                    "mastery_delta": str(mastery_delta),
                    "last_study": data.get('timestamp', '')
                }
            )

        # 已掌握
        if mastery_delta >= 80:
            await self.age_client.add_edge(
                from_label="User",
                from_props={"id": user_id},
                to_label="KnowledgeNode",
                to_props={"id": node_id},
                edge_label="MASTERED"
            )

        logger.debug(f"用户状态已同步: user={user_id}, node={node_id}")


# Worker 实例
_worker_instance: Optional[GraphSyncWorker] = None


def get_graph_sync_worker() -> GraphSyncWorker:
    """获取 Worker 单例"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = GraphSyncWorker()
    return _worker_instance


async def start_sync_worker():
    """启动同步 Worker"""
    worker = get_graph_sync_worker()
    await worker.start()


async def stop_sync_worker():
    """停止同步 Worker"""
    worker = get_graph_sync_worker()
    await worker.stop()
