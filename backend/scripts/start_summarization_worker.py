#!/usr/bin/env python3
"""
启动 SummarizationWorker 的便捷脚本

使用方式:
    python scripts/start_summarization_worker.py
    python scripts/start_summarization_worker.py --worker-id worker-1 --batch-size 10
"""

import asyncio
import argparse
from loguru import logger

from app.config import settings
from app.orchestration.summarization_worker import SummarizationWorker
import redis.asyncio as redis


async def main():
    parser = argparse.ArgumentParser(description="启动 SummarizationWorker")
    parser.add_argument(
        "--redis-url",
        default=settings.REDIS_URL,
        help=f"Redis URL (默认: {settings.REDIS_URL})"
    )
    parser.add_argument(
        "--worker-id",
        default="worker-main",
        help="Worker ID (用于日志和监控)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="批量处理的任务数"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="最大重试次数"
    )

    args = parser.parse_args()

    logger.info(f"Starting SummarizationWorker: {args.worker_id}")
    logger.info(f"Redis URL: {args.redis_url}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Max retries: {args.max_retries}")

    # 创建 Redis 客户端
    redis_client = redis.from_url(args.redis_url, decode_responses=False)

    # 验证连接
    try:
        await redis_client.ping()
        logger.info("✅ Redis 连接成功")
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        return

    # 创建 Worker
    worker = SummarizationWorker(
        redis_client=redis_client,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        worker_id=args.worker_id
    )

    # 启动 Worker
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        await redis_client.close()
        logger.info("Worker 已停止")


if __name__ == "__main__":
    asyncio.run(main())
