"""
图数据库同步 Worker

消费 Redis Stream 中的同步事件，异步写入到 AGE
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from loguru import logger

from app.core.age_client import get_age_client
from app.core.background_tasks import spawn_tracked
from app.core.cache import cache_service
from app.models.graph_models import KnowledgeVertex


class GraphSyncWorker:
    """图同步 Worker"""

    # 兼容经 __new__ 构造的测试实例（未跑 __init__ 时 stop() 也安全）。
    _consume_task: asyncio.Task | None = None

    def __init__(self):
        self.age_client = get_age_client()
        # Allow tests to inject a mocked cache_service before instantiation.
        self.redis = cache_service.redis
        self.running = False
        self.stream_key = "stream:graph_sync"
        self.group_name = "graph_sync_group"
        self.consumer_name = "worker_1"
        # EVENT-ACK：pending 回收空闲阈值——失败/崩溃遗留的未 ack 消息（PEL）
        # 超过该空闲时长后被 XAUTOCLAIM 认领重处理（at-least-once）。
        self.pending_reclaim_idle_ms = 60_000
        self._consume_task = None

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
        # FF-CONVERGENCE（wt310）：裸 create_task 无引用 + stop() 只翻 flag 无法
        # cancel（wt294 P1-4 关停面裸奔）。改为持有引用的追踪任务，stop() 可
        # 立即 cancel 并等待落地。
        self._consume_task = spawn_tracked(self._consume(), name="graph_sync_worker.consume")

    async def stop(self):
        """停止 Worker"""
        logger.info("🛑 停止图同步 Worker...")
        self.running = False
        task = self._consume_task
        self._consume_task = None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _recover_pending(self):
        """回收 pending：崩溃/处理失败遗留的未确认消息（EVENT-ACK）。

        本 worker 失败时不 ack（消息留在 PEL），但此前没有任何回收面——
        pending 消息会永久卡死。用 XAUTOCLAIM 认领空闲超过
        ``pending_reclaim_idle_ms`` 的条目并按正常路径重处理。at-least-once
        语义：与 EventBus._claim_stale_messages 同款（node 写按 id 幂等，
        边写依赖下游容忍重放——重放窗口被 min_idle_time 限制在真实故障面）。
        """
        if not self.redis:
            return
        try:
            # redis-py 7.0+ 返回 (next_id, messages, deleted_ids)
            result = await self.redis.xautoclaim(
                self.stream_key,
                self.group_name,
                self.consumer_name,
                min_idle_time=self.pending_reclaim_idle_ms,
                start_id="0-0",
                count=10,
            )
            messages = list(result[1] or [])
        except Exception as e:
            logger.debug(f"graph sync pending reclaim skipped: {e}")
            return
        for msg_id, msg_data in messages:
            try:
                await self._process_message(msg_id, msg_data)
            except Exception as e:
                logger.warning(
                    "graph sync pending reclaim failed (message stays pending): id={} error={}",
                    msg_id,
                    e,
                )

    async def _consume(self):
        """消费消息"""
        logger.info("开始消费同步消息...")

        while self.running:
            try:
                # 先回收 stale pending（崩溃/失败遗留），再读新消息（与 EventBus 一致）
                await self._recover_pending()

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

                for _stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        try:
                            # 处理消息
                            await self._process_message(msg_id, msg_data)
                        except Exception as e:
                            # EVENT-ACK：失败不 ack（消息留在 PEL），由
                            # _recover_pending 的 XAUTOCLAIM 认领重试
                            # （at-least-once；不引入额外死信设施）。
                            logger.warning(f"处理消息失败（留 pending 待回收） {msg_id}: {e}")

            except asyncio.CancelledError:
                logger.info("Worker 被取消")
                break
            except Exception as e:
                logger.error(f"消费循环错误: {e}")
                await asyncio.sleep(1)  # 避免快速重试

    @staticmethod
    def _read_field(msg_data: dict[Any, Any], field: str) -> str:
        """Read Redis stream fields regardless of decode_responses mode."""
        value = msg_data.get(field)
        if value is None:
            value = msg_data.get(field.encode("utf-8"))
        if value is None:
            raise KeyError(field)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def _process_message(self, msg_id: bytes, msg_data: dict[Any, Any]):
        """处理单条消息"""
        # 解析消息
        msg_type = self._read_field(msg_data, "type")
        data = json.loads(self._read_field(msg_data, "data"))

        logger.debug(f"处理消息: {msg_type} - {data.get('id', 'N/A')}")

        try:
            if msg_type == "node_created":
                await self._handle_node_created(data)
            elif msg_type == "relation_created":
                await self._handle_relation_created(data)
            elif msg_type == "user_status_updated":
                await self._handle_user_status_updated(data)
            else:
                # EVENT-ACK：未知类型是显式良性 ack（schema 演进白名单外、
                # 重试无意义），warning 可见、不静默。
                logger.warning(f"未知消息类型: {msg_type}")

            # 确认消息已处理
            if self.redis:
                await self.redis.xack(self.stream_key, self.group_name, msg_id)
                logger.debug(f"消息已确认: {msg_id}")
            else:
                logger.warning("Redis 未初始化，跳过消息确认")

        except Exception as e:
            logger.error(f"处理消息 {msg_type} 失败: {e}")
            # 不确认消息，稍后重试
            raise

    async def _handle_node_created(self, data: dict[str, Any]):
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

    async def _handle_relation_created(self, data: dict[str, Any]):
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

    async def _handle_user_status_updated(self, data: dict[str, Any]):
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
_worker_instance: GraphSyncWorker | None = None


def get_graph_sync_worker() -> GraphSyncWorker:
    """获取 Worker 单例"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = GraphSyncWorker()
    return _worker_instance


async def start_sync_worker():
    """启动同步 Worker"""
    worker = get_graph_sync_worker()
    # FF-CONVERGENCE（wt310）：裸 spawn → 统一追踪（异常可见、不被 GC 回收）。
    spawn_tracked(worker.start(), name="graph_sync_worker.start")


async def stop_sync_worker():
    """停止同步 Worker"""
    worker = get_graph_sync_worker()
    await worker.stop()
