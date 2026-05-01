from datetime import UTC, datetime
from typing import Any

import y_py as Y
from redis.asyncio import Redis
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import CRDTOperationLog, CRDTSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
            _utcnow().isoformat(),
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
            operation_count=0, # TRACKED(TD-008): implement operation count tracking
            updated_at=_utcnow()
        ).on_conflict_do_update(
            index_elements=['galaxy_id'],
            set_={
                'state_data': update_data,
                'updated_at': _utcnow()
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



# ═══════════════════════════════════════════════════════════════════════
# APP-005: CRDT Mastery Merge — offline/multi-device conflict resolution
# ═══════════════════════════════════════════════════════════════════════


class MasteryMergeCRDT:
    """CRDT merge strategy for node mastery scores across devices.

    Strategy: max-wins for mastery scores (learning progress is monotonic).
    For local task status: most-progressed wins.
    All merges are commutative, associative, and idempotent (CRDT properties).
    """

    @staticmethod
    def merge_mastery(local: float, remote: float) -> float:
        """Merge two mastery scores — max wins (learning is monotonic)."""
        return max(local, remote)

    @staticmethod
    def merge_task_status(local: str, remote: str) -> str:
        """Merge task status — most progressed wins."""
        order = {"pending": 0, "in_progress": 1, "completed": 2, "abandoned": 3}
        if order.get(local, 0) >= order.get(remote, 0):
            return local
        return remote

    @staticmethod
    def merge_node(
        local: dict[str, Any],
        remote: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge a full node from two devices.

        Rules:
        - mastery: max wins
        - status: most progressed wins
        - revision: max wins (LWW for metadata)
        - updated_at: latest wins
        """
        merged = dict(local)

        local_mastery = float(local.get("mastery_score", 0.0))
        remote_mastery = float(remote.get("mastery_score", 0.0))
        merged["mastery_score"] = max(local_mastery, remote_mastery)

        local_status = str(local.get("status", "pending"))
        remote_status = str(remote.get("status", "pending"))
        merged["status"] = MasteryMergeCRDT.merge_task_status(local_status, remote_status)

        local_rev = int(local.get("revision", 0))
        remote_rev = int(remote.get("revision", 0))
        merged["revision"] = max(local_rev, remote_rev) + 1

        return merged

    @staticmethod
    def merge_batch(
        local_nodes: dict[str, dict[str, Any]],
        remote_nodes: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge a batch of nodes from two devices.

        Returns list of merged node dicts (only nodes that changed).
        Nodes only in local or only in remote are included as-is.
        """
        all_ids = set(local_nodes.keys()) | set(remote_nodes.keys())
        merged = []
        for node_id in all_ids:
            loc = local_nodes.get(node_id)
            rem = remote_nodes.get(node_id)
            if loc and rem:
                merged.append(MasteryMergeCRDT.merge_node(loc, rem))
            else:
                merged.append(loc or rem)
        return merged
