"""
BillingWorker - 异步计费任务处理器

负责从 Redis 队列中消费 Token 使用记录，并批量持久化到数据库中。
"""

import json
import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
import redis.asyncio as redis
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.chat import TokenUsage
from app.config import settings

class BillingWorker:
    """
    异步计费工作器
    
    采用批量写入策略减少数据库压力，支持异常重试。
    """
    
    def __init__(
        self, 
        redis_url: str = settings.REDIS_URL,
        redis_password: str = settings.REDIS_PASSWORD,
        db_url: str = settings.DATABASE_URL,
        batch_size: int = 10,
        flush_interval: int = 5
    ):
        self.redis_url = redis_url
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # 初始化 Redis
        self.redis = redis.from_url(redis_url, password=redis_password)
        
        # 初始化数据库引擎和会话工厂
        self.engine = create_async_engine(db_url)
        self.async_session_factory = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        
        self.is_running = False
        self._batch: List[Dict[str, Any]] = []
        self._last_flush_time = time.time()
        
    async def start(self):
        """启动工作器"""
        logger.info(f"BillingWorker starting... (batch_size={self.batch_size}, flush_interval={self.flush_interval})")
        self.is_running = True
        
        try:
            while self.is_running:
                # 尝试从队列获取任务，超时 1 秒
                result = await self.redis.blpop("queue:billing", timeout=1)
                
                if result:
                    _, data = result
                    try:
                        record = json.loads(data)
                        self._batch.append(record)
                        logger.debug(f"Added record to batch. Current size: {len(self._batch)}")
                    except Exception as e:
                        logger.error(f"Failed to parse billing record: {e}")
                
                # 检查是否需要刷新到数据库
                if self._should_flush():
                    await self._flush_to_db()
                    
        except asyncio.CancelledError:
            logger.info("BillingWorker stopping (cancelled)...")
        except Exception as e:
            logger.error(f"BillingWorker encountered critical error: {e}")
            raise
        finally:
            self.is_running = False
            # 停止前尝试刷新最后一批
            if self._batch:
                await self._flush_to_db()
            await self.redis.close()
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
        if time.time() - self._last_flush_time >= self.flush_interval:
            return True
            
        return False

    async def _flush_to_db(self):
        """将批处理中的记录持久化到数据库"""
        if not self._batch:
            return
            
        logger.info(f"Flushing {len(self._batch)} records to database...")
        start_time = time.time()
        
        try:
            async with self.async_session_factory() as session:
                async with session.begin():
                    # 转换记录格式以匹配模型，并处理可能的 UUID 转换或时间格式转换
                    stmt_data = []
                    for r in self._batch:
                        stmt_data.append({
                            "user_id": r["user_id"],
                            "session_id": r["session_id"],
                            "request_id": r["request_id"],
                            "model": r["model"],
                            "prompt_tokens": r["prompt_tokens"],
                            "completion_tokens": r["completion_tokens"],
                            "total_tokens": r["total_tokens"],
                            "cost": r.get("cost", 0.0),
                            "timestamp": datetime.fromtimestamp(r["timestamp"]) if "timestamp" in r else datetime.utcnow()
                        })
                    
                    # 批量插入
                    await session.execute(insert(TokenUsage), stmt_data)
                
                await session.commit()
                
            logger.info(f"Successfully persisted {len(self._batch)} records in {time.time() - start_time:.3f}s")
            self._batch = []
            self._last_flush_time = time.time()
            
        except Exception as e:
            logger.error(f"Failed to persist billing records: {e}")
            # 如果是唯一约束冲突（可能是重复请求），尝试逐条插入或记录错误
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.warning("Duplicate key detected, retrying individual records...")
                await self._retry_individually()
            else:
                # 其他错误则保留在批中待下次重试（需谨慎处理，防止死循环）
                logger.error("Keeping records in batch for retry...")

    async def _retry_individually(self):
        """逐条重试插入，跳过已存在的记录"""
        async with self.async_session_factory() as session:
            for r in self._batch:
                try:
                    async with session.begin_nested():
                        stmt_data = {
                            "user_id": r["user_id"],
                            "session_id": r["session_id"],
                            "request_id": r["request_id"],
                            "model": r["model"],
                            "prompt_tokens": r["prompt_tokens"],
                            "completion_tokens": r["completion_tokens"],
                            "total_tokens": r["total_tokens"],
                            "cost": r.get("cost", 0.0),
                            "timestamp": datetime.fromtimestamp(r["timestamp"]) if "timestamp" in r else datetime.utcnow()
                        }
                        await session.execute(insert(TokenUsage), stmt_data)
                    await session.commit()
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                        logger.debug(f"Skipping duplicate request_id: {r['request_id']}")
                    else:
                        logger.error(f"Failed to persist individual record {r['request_id']}: {e}")
            
            await session.commit()
            
        self._batch = []
        self._last_flush_time = time.time()

    def stop(self):
        """停止工作器"""
        self.is_running = False

if __name__ == "__main__":
    # 简单的本地运行逻辑
    worker = BillingWorker()
    asyncio.run(worker.start())