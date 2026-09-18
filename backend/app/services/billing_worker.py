"""
BillingWorker - 异步计费任务处理器

负责从 Redis 队列中消费 Token 使用记录，并批量持久化到数据库中。
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from loguru import logger
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.db.url import to_async_database_url
from app.models.chat import TokenUsage


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BillingWorker:
    """
    异步计费工作器

    采用批量写入策略减少数据库压力，支持异常重试。
    落库失败时记录回退 Redis 重试或转死信队列，worker 进程不因 flush 失败退出。
    """

    RETRY_METADATA_KEY = "_billing_attempts"
    MAX_RECORD_ATTEMPTS = 3
    RETRY_BACKOFF_SECONDS = 1.0
    BILLING_QUEUE = "queue:billing"

    def __init__(
        self,
        redis_url: str = settings.REDIS_URL,
        redis_password: str | None = settings.REDIS_PASSWORD,
        db_url: str = settings.DATABASE_URL,
        batch_size: int = 10,
        flush_interval: int = 5,
    ):
        self.redis_url = redis_url
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # 初始化 Redis
        resolved_password, _ = resolve_redis_password(redis_url, redis_password)
        self.redis = redis.from_url(redis_url, password=resolved_password)

        # 初始化数据库引擎和会话工厂
        self.engine = create_async_engine(to_async_database_url(db_url))
        self.async_session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        self.is_running = False
        self._batch: list[dict[str, Any]] = []
        self._last_flush_time = time.time()
        self._dead_letter_queue = "queue:billing:dead_letter"
        # flush 失败后的重试退避（测试可置 0 加速）
        self._flush_retry_backoff = self.RETRY_BACKOFF_SECONDS

    async def start(self):
        """启动工作器"""
        logger.info(f"BillingWorker starting... (batch_size={self.batch_size}, flush_interval={self.flush_interval})")
        self.is_running = True

        try:
            while self.is_running:
                # 尝试从队列获取任务，超时 1 秒
                result = await self.redis.blpop(self.BILLING_QUEUE, timeout=1)

                if result:
                    _, data = result
                    try:
                        record = json.loads(data)
                        self._batch.append(record)
                        logger.debug(f"Added record to batch. Current size: {len(self._batch)}")
                    except Exception as e:
                        logger.error(f"Failed to parse billing record: {e}")

                # 检查是否需要刷新到数据库（失败不退出进程，走恢复路径）
                if self._should_flush():
                    try:
                        await self._flush_to_db()
                    except Exception as exc:
                        await self._recover_failed_batch(exc)

        except asyncio.CancelledError:
            logger.info("BillingWorker stopping (cancelled)...")
        except Exception as e:
            logger.error(f"BillingWorker encountered critical error: {e}")
            raise
        finally:
            self.is_running = False
            # 停止前尝试刷新最后一批（失败则回退重试/死信，避免静默丢失）
            if self._batch:
                try:
                    await self._flush_to_db()
                except Exception as exc:
                    await self._recover_failed_batch(exc)
            await self.redis.aclose()
            await self.engine.dispose()
            logger.info("BillingWorker stopped.")

    def _should_flush(self) -> bool:
        """判断是否应该刷新批处理"""
        if not self._batch:
            return False

        # 达到批大小
        if len(self._batch) >= self.batch_size:
            return True

        # 超过刷新时间间隔
        return time.time() - self._last_flush_time >= self.flush_interval

    async def _flush_to_db(self):
        """将批处理中的记录持久化到数据库"""
        if not self._batch:
            return

        logger.info(f"Flushing {len(self._batch)} records to database...")
        start_time = time.time()

        try:
            async with self.async_session_factory() as session:
                async with session.begin():
                    # 转换记录格式以匹配模型（时间戳统一按 UTC 换算，见 _to_stmt_data）
                    stmt_data = [self._to_stmt_data(r) for r in self._batch]

                    # 批量插入
                    await session.execute(insert(TokenUsage), stmt_data)

                await session.commit()

            logger.info(f"Successfully persisted {len(self._batch)} records in {time.time() - start_time:.3f}s")
            self._batch = []
            self._last_flush_time = time.time()

        except Exception as e:
            logger.error(f"Failed to persist billing records: {e}")
            logger.warning("Batch flush failed, retrying records individually...")
            await self._retry_individually()

    async def _retry_individually(self):
        """逐条重试插入，坏记录转入死信队列，避免阻塞后续合法记录。"""
        async with self.async_session_factory() as session:
            for r in self._batch:
                try:
                    async with session.begin_nested():
                        stmt_data = self._to_stmt_data(r)
                        await session.execute(insert(TokenUsage), stmt_data)
                    await session.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                        logger.debug(f"Skipping duplicate request_id: {r['request_id']}")
                    else:
                        logger.error(f"Failed to persist individual record {r.get('request_id')}: {e}")
                        await self._move_to_dead_letter(r, str(e))

            await session.commit()

        self._batch = []
        self._last_flush_time = time.time()

    def _to_stmt_data(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": record["user_id"],
            "session_id": record["session_id"],
            "request_id": record["request_id"],
            "model": record["model"],
            "model_tier": record.get("model_tier"),
            "ai_reasoning_mode": record.get("reasoning_mode", "balanced"),
            "prompt_tokens": record["prompt_tokens"],
            "completion_tokens": record["completion_tokens"],
            "total_tokens": record["total_tokens"],
            "cost": record.get("cost", 0.0),
            # B1: epoch → naive UTC，与 _utcnow() 对齐，避免本地时区漂移
            "timestamp": (
                datetime.fromtimestamp(record["timestamp"], tz=UTC).replace(tzinfo=None)
                if "timestamp" in record
                else _utcnow()
            ),
        }

    async def _recover_failed_batch(self, exc: Exception) -> None:
        """批量 flush 与逐条重试均失败后的兜底：未超限记录回退 Redis 重试，超限转死信。

        本方法绝不抛异常，保证 worker 进程不因落库故障退出（B2）。
        """
        logger.error(f"Billing flush failed, recovering {len(self._batch)} records: {exc}")
        retry_batch: list[dict[str, Any]] = []
        for record in self._batch:
            attempts = int(record.get(self.RETRY_METADATA_KEY, 0)) + 1
            if attempts >= self.MAX_RECORD_ATTEMPTS:
                try:
                    await self._move_to_dead_letter(record, str(exc))
                except Exception as dl_exc:
                    logger.error(
                        "Failed to enqueue dead letter for request_id=%s: %s",
                        record.get("request_id"),
                        dl_exc,
                    )
            else:
                record[self.RETRY_METADATA_KEY] = attempts
                retry_batch.append(record)

        self._batch = []
        self._last_flush_time = time.time()

        if retry_batch:
            if self._flush_retry_backoff > 0:
                # 退避，避免 DB 故障期间热循环重试
                await asyncio.sleep(self._flush_retry_backoff)
            # blpop 从队头弹出，lpush 逆序回推以保持原顺序
            for record in reversed(retry_batch):
                try:
                    await self.redis.lpush(self.BILLING_QUEUE, json.dumps(record, ensure_ascii=False))
                except Exception as push_exc:
                    logger.error(
                        "Failed to requeue billing record request_id=%s: %s",
                        record.get("request_id"),
                        push_exc,
                    )
                    try:
                        await self._move_to_dead_letter(record, f"requeue failed: {push_exc}")
                    except Exception as dl_exc:
                        logger.error(
                            "Failed to enqueue dead letter for request_id=%s: %s",
                            record.get("request_id"),
                            dl_exc,
                        )
            if retry_batch:
                logger.warning(f"Requeued {len(retry_batch)} billing records for retry")

    async def _move_to_dead_letter(self, record: dict[str, Any], error: str) -> None:
        payload = {
            "record": record,
            "error": error,
            "failed_at": _utcnow().isoformat(),
        }
        await self.redis.rpush(self._dead_letter_queue, json.dumps(payload, ensure_ascii=False))
        logger.warning(
            "Moved billing record to dead letter queue: request_id=%s queue=%s",
            record.get("request_id"),
            self._dead_letter_queue,
        )

    def stop(self):
        """停止工作器"""
        self.is_running = False


if __name__ == "__main__":
    # 简单的本地运行逻辑
    worker = BillingWorker()
    asyncio.run(worker.start())
