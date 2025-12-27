"""
BillingWorker - 异步计费任务处理器

从 Redis 队列消费 Token 使用记录，持久化到数据库，
并提供计费统计和报表功能。
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.chat import ChatMessage
try:
    from app.models.chat import TokenUsage
except ImportError:
    # 如果 TokenUsage 还未添加，创建一个临时的占位符
    # 实际使用时应该已经添加到模型中
    TokenUsage = None


class BillingWorker:
    """
    异步计费任务处理器

    功能:
    1. 从队列消费 Token 使用记录
    2. 聚合多条记录减少数据库写入
    3. 持久化到数据库
    4. 提供统计查询
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        db_session_factory,
        batch_size: int = 50,
        flush_interval: int = 5,
        worker_id: str = None
    ):
        """
        初始化 BillingWorker

        Args:
            redis_client: Redis 客户端
            db_session_factory: 数据库 Session 工厂
            batch_size: 批量写入的记录数
            flush_interval: 自动刷新间隔（秒）
            worker_id: 工作器 ID
        """
        self.redis = redis_client
        self.db_factory = db_session_factory
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.worker_id = worker_id or f"billing-worker-{id(self)}"

        self.running = False
        self.buffer: List[Dict[str, Any]] = []
        self.processed_count = 0
        self.failed_count = 0

        logger.info(f"BillingWorker {self.worker_id} initialized")

    async def start(self):
        """启动工作器"""
        if self.running:
            logger.warning(f"BillingWorker {self.worker_id} is already running")
            return

        self.running = True
        logger.info(f"BillingWorker {self.worker_id} started")

        # 启动两个任务：消费队列 + 定时刷新
        consumer_task = asyncio.create_task(self._consume_queue())
        flusher_task = asyncio.create_task(self._auto_flush())

        try:
            await asyncio.gather(consumer_task, flusher_task)
        except asyncio.CancelledError:
            logger.info(f"BillingWorker {self.worker_id} cancelled")
        except Exception as e:
            logger.error(f"BillingWorker {self.worker_id} crashed: {e}", exc_info=True)
        finally:
            self.running = False
            # 刷新剩余数据
            if self.buffer:
                await self._flush_buffer()
            logger.info(f"BillingWorker {self.worker_id} stopped")

    async def stop(self):
        """停止工作器"""
        self.running = False
        logger.info(f"Stopping BillingWorker {self.worker_id}...")

    async def _consume_queue(self):
        """从队列消费记录"""
        queue_key = "queue:billing"

        while self.running:
            try:
                # 批量获取
                for _ in range(self.batch_size):
                    task_data = await self.redis.blpop(queue_key, timeout=0.1)
                    if task_data is None:
                        break

                    record = json.loads(task_data[1])
                    self.buffer.append(record)

                # 如果缓冲区已满，立即刷新
                if len(self.buffer) >= self.batch_size:
                    await self._flush_buffer()

            except Exception as e:
                logger.error(f"Failed to consume from queue: {e}")
                await asyncio.sleep(1)

    async def _auto_flush(self):
        """定时刷新缓冲区"""
        while self.running:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.buffer:
                    await self._flush_buffer()
            except Exception as e:
                logger.error(f"Auto flush error: {e}")
                await asyncio.sleep(1)

    async def _flush_buffer(self):
        """刷新缓冲区到数据库"""
        if not self.buffer:
            return

        records = self.buffer.copy()
        self.buffer = []

        try:
            async with self.db_factory() as db:
                # 批量插入
                for record in records:
                    try:
                        # 创建 TokenUsage 记录
                        if TokenUsage:
                            import uuid
                            timestamp = datetime.fromtimestamp(record["timestamp"])
                            usage = TokenUsage(
                                id=uuid.uuid4(),
                                user_id=record["user_id"],
                                session_id=record["session_id"],
                                request_id=record["request_id"],
                                prompt_tokens=record["prompt_tokens"],
                                completion_tokens=record["completion_tokens"],
                                total_tokens=record["total_tokens"],
                                model=record.get("model", "gpt-4"),
                                cost=record.get("cost"),
                                created_at=timestamp,
                                updated_at=timestamp
                            )
                            db.add(usage)

                        # 更新 ChatMessage（如果存在）
                        if record.get("session_id"):
                            result = await db.execute(
                                select(ChatMessage)
                                .where(ChatMessage.session_id == record["session_id"])
                                .order_by(ChatMessage.created_at.desc())
                                .limit(1)
                            )
                            chat_msg = result.scalar_one_or_none()
                            if chat_msg:
                                chat_msg.tokens_used = record["total_tokens"]
                                chat_msg.model_name = record.get("model", "gpt-4")

                    except Exception as e:
                        logger.error(f"Failed to process record {record.get('request_id')}: {e}")
                        self.failed_count += 1

                await db.commit()
                self.processed_count += len(records)

                logger.info(
                    f"Flushed {len(records)} records to DB. "
                    f"Total processed: {self.processed_count}, failed: {self.failed_count}"
                )

        except Exception as e:
            logger.error(f"Failed to flush buffer: {e}")
            # 将记录放回缓冲区，等待下次重试
            self.buffer.extend(records)
            await asyncio.sleep(5)  # 等待后重试

    async def get_stats(self) -> Dict[str, Any]:
        """获取工作器统计"""
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "buffer_size": len(self.buffer),
            "processed": self.processed_count,
            "failed": self.failed_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0
                else 0
            )
        }

    async def get_daily_revenue(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取每日营收统计

        Args:
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            统计信息
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        async with self.db_factory() as db:
            # 总成本
            result = await db.execute(
                select(
                    func.sum(TokenUsage.cost).label("total_cost"),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.count(TokenUsage.id).label("request_count")
                )
                .where(TokenUsage.created_at >= f"{date} 00:00:00")
                .where(TokenUsage.created_at <= f"{date} 23:59:59")
            )
            row = result.first()

            # 按用户分组
            result2 = await db.execute(
                select(
                    TokenUsage.user_id,
                    func.sum(TokenUsage.cost).label("user_cost"),
                    func.sum(TokenUsage.total_tokens).label("user_tokens"),
                    func.count(TokenUsage.id).label("user_requests")
                )
                .where(TokenUsage.created_at >= f"{date} 00:00:00")
                .where(TokenUsage.created_at <= f"{date} 23:59:59")
                .group_by(TokenUsage.user_id)
                .order_by(func.sum(TokenUsage.cost).desc())
                .limit(10)
            )
            top_users = [
                {
                    "user_id": r.user_id,
                    "cost": float(r.user_cost or 0),
                    "tokens": r.user_tokens or 0,
                    "requests": r.user_requests
                }
                for r in result2.fetchall()
            ]

            return {
                "date": date,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": row.total_tokens or 0,
                "request_count": row.request_count or 0,
                "top_users": top_users
            }

    async def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户计费统计

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            用户统计信息
        """
        start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        if not TokenUsage:
            return {"error": "TokenUsage model not available"}

        async with self.db_factory() as db:
            result = await db.execute(
                select(
                    func.date(TokenUsage.created_at).label("date"),
                    func.sum(TokenUsage.total_tokens).label("tokens"),
                    func.sum(TokenUsage.cost).label("cost"),
                    func.count(TokenUsage.id).label("requests")
                )
                .where(TokenUsage.user_id == user_id)
                .where(TokenUsage.created_at >= f"{start_date} 00:00:00")
                .group_by(func.date(TokenUsage.created_at))
                .order_by(func.date(TokenUsage.created_at))
            )

            daily_stats = []
            total_tokens = 0
            total_cost = 0
            total_requests = 0

            for row in result.fetchall():
                daily_stats.append({
                    "date": str(row.date),
                    "tokens": row.tokens or 0,
                    "cost": float(row.cost or 0),
                    "requests": row.requests
                })
                total_tokens += row.tokens or 0
                total_cost += float(row.cost or 0)
                total_requests += row.requests

            return {
                "user_id": user_id,
                "period_days": days,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 6),
                "total_requests": total_requests,
                "daily_average": {
                    "tokens": total_tokens / days if days > 0 else 0,
                    "cost": round(total_cost / days, 6) if days > 0 else 0,
                    "requests": total_requests / days if days > 0 else 0
                },
                "daily_stats": daily_stats
            }


# 工厂函数
def create_billing_worker(
    redis_url: str,
    db_session_factory,
    worker_id: str = None,
    **kwargs
) -> BillingWorker:
    """
    创建 BillingWorker 实例

    Args:
        redis_url: Redis 连接 URL
        db_session_factory: 数据库 Session 工厂
        worker_id: 工作器 ID
        **kwargs: 其他配置参数

    Returns:
        BillingWorker 实例
    """
    import redis.asyncio as redis

    redis_client = redis.from_url(redis_url, decode_responses=False)
    return BillingWorker(redis_client, db_session_factory, worker_id=worker_id, **kwargs)


# 独立的运行脚本入口
async def run_worker():
    """
    作为独立进程运行工作器的入口函数

    使用方式:
    python -m app.services.billing_worker
    """
    from app.config import settings
    from app.database import get_async_session_factory

    worker = create_billing_worker(
        redis_url=settings.REDIS_URL,
        db_session_factory=get_async_session_factory(),
        worker_id="main-billing-worker"
    )

    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_worker())
