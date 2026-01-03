import asyncio
import json
import time
import uuid
from loguru import logger
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.orchestration.token_tracker import TokenTracker
from app.services.billing_worker import BillingWorker
from app.models.chat import TokenUsage
from app.models.user import User

async def test_token_metering_flow():
    logger.info("Starting Token Metering Integration Test...")
    
    # 1. 初始化
    redis_client = redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD)
    token_tracker = TokenTracker(redis_client)
    
    # 获取一个真实用户 ID
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    user_id = None
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()
        if user:
            user_id = str(user.id)
            logger.info(f"Using test user: {user_id}")
        else:
            logger.error("No user found in database. Please run seed data first.")
            return

    session_id = f"test_session_{int(time.time())}"
    request_id = f"test_req_{uuid.uuid4()}"
    
    # 2. 模拟记录 Token 使用
    logger.info("Recording simulated token usage...")
    prompt_tokens = 150
    completion_tokens = 350
    model = "gpt-4"
    cost = 0.0255
    
    await token_tracker.record_usage(
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model,
        cost=cost
    )
    
    # 3. 验证 Redis 中的即时数据
    daily_usage = await token_tracker.get_daily_usage(user_id)
    logger.info(f"Daily usage in Redis: {daily_usage} tokens")
    assert daily_usage >= (prompt_tokens + completion_tokens)
    
    # 4. 运行 BillingWorker 处理队列
    logger.info("Running BillingWorker to flush records to DB...")
    # 我们手动创建一个 worker 并只运行一轮刷新
    worker = BillingWorker(batch_size=1, flush_interval=0)
    
    # 由于 worker.start() 是死循环，我们手动模拟其逻辑
    result = await redis_client.blpop("queue:billing", timeout=2)
    if result:
        _, data = result
        worker._batch.append(json.loads(data))
        await worker._flush_to_db()
        logger.info("Flushed to DB successfully.")
    else:
        logger.error("No data found in queue:billing!")
        return

    # 5. 验证数据库中的记录
    async with async_session() as session:
        result = await session.execute(
            select(TokenUsage).where(TokenUsage.request_id == request_id)
        )
        db_record = result.scalars().first()
        
        if db_record:
            logger.info("✅ Database record found!")
            logger.info(f"DB Record: {db_record.total_tokens} tokens, cost: ${db_record.cost}")
            assert db_record.total_tokens == (prompt_tokens + completion_tokens)
            assert db_record.user_id == uuid.UUID(user_id)
        else:
            logger.error("❌ Database record NOT found!")

    await redis_client.close()
    await engine.dispose()
    logger.info("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_token_metering_flow())