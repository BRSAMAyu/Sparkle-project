from datetime import datetime
import json
from typing import Optional, List
import y_py as Y
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.models.galaxy import CRDTSnapshot, CollaborativeGalaxy, CRDTOperationLog
from loguru import logger

class CRDTPersistenceManager:
    """
    CRDT 状态持久化管理器: 内存 -> Redis -> PostgreSQL
    CRDT Persistence Manager: Memory -> Redis -> PostgreSQL
    """

    def __init__(self, redis_client: Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session
        self._batch_buffer = []

    async def persist_snapshot(self, galaxy_id: str, ydoc: Y.YDoc):
        """
        1. 内存 -> Redis (高频写入)
        Memory -> Redis (High-frequency write)
        """
        # 序列化 Yjs 文档
        update_data = Y.encode_state_as_update(ydoc)

        # Redis 持久化 (TTL 24h)
        # 注意: 如果 redis_client 设置了 decode_responses=True, 
        # 这里存储 bytes 可能会有问题。
        # 建议使用独立的 redis 实例或确保可以处理 bytes。
        key = f"crdt:snapshot:{galaxy_id}"
        await self.redis.set(key, update_data, ex=86400)

        # 记录最后同步时间
        await self.redis.set(
            f"crdt:timestamp:{galaxy_id}",
            datetime.utcnow().isoformat(),
            ex=86400
        )

    async def persist_to_db(self, galaxy_id: str, ydoc: Y.YDoc):
        """
        2. Redis -> PostgreSQL (低频, 定时任务)
        Redis -> PostgreSQL (Low-frequency, scheduled task)
        """
        update_data = Y.encode_state_as_update(ydoc)
        
        # Upsert 到数据库
        stmt = insert(CRDTSnapshot).values(
            galaxy_id=galaxy_id,
            state_data=update_data,
            operation_count=0, # TODO: implement operation count tracking
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=['galaxy_id'],
            set_={
                'state_data': update_data,
                'updated_at': datetime.utcnow()
            }
        )
        
        await self.db.execute(stmt)
        await self.db.commit()

    async def restore(self, galaxy_id: str) -> Y.YDoc:
        """
        3. 恢复: PostgreSQL -> Redis -> 内存
        Restore: PostgreSQL -> Redis -> Memory
        """
        # 优先从 Redis 恢复 (最新)
        key = f"crdt:snapshot:{galaxy_id}"
        redis_data = await self.redis.get(key)
        
        ydoc = Y.YDoc()
        if redis_data:
            # 如果 redis_client 设置了 decode_responses=True, 
            # redis_data 可能是 string, 需要转回 bytes
            if isinstance(redis_data, str):
                redis_data = redis_data.encode('latin-1') # Or appropriate encoding
            
            Y.apply_update(ydoc, redis_data)
            return ydoc

        # Redis 无数据, 从 PostgreSQL 恢复
        result = await self.db.execute(
            select(CRDTSnapshot.state_data).where(CRDTSnapshot.galaxy_id == galaxy_id)
        )
        row = result.scalar_one_or_none()

        if row:
            Y.apply_update(ydoc, row)
            # 回填到 Redis
            await self.persist_snapshot(galaxy_id, ydoc)
            return ydoc

        # 无历史数据, 返回空文档
        return ydoc

    async def log_operation(self, galaxy_id: str, user_id: str, op_type: str, op_data: dict):
        """
        记录操作日志
        Log collaborative operation
        """
        log_entry = CRDTOperationLog(
            galaxy_id=galaxy_id,
            user_id=user_id,
            operation_type=op_type,
            operation_data=op_data
        )
        self.db.add(log_entry)
        await self.db.commit()
