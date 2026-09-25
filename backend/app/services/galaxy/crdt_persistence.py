from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any, cast

import y_py as Y
from redis.asyncio import Redis
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import CRDTOperationLog, CRDTSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# G-05（wt395）: 共享 cache_service 客户端是 ``decode_responses=True``——Yjs 二进制
# 快照在 redis-py **响应解析层**就会 UnicodeDecodeError，restore() 里的 ``str`` 兜底
# （encode('latin-1')）根本执行不到。表现为：引擎重启/会话 TTL 驱逐后，第一台
# 重连设备走 ``SyncCollaborativeGalaxy → restore()`` 必失败（servicer 捕获后
# success=False，多端恢复面断）。快照读写必须走二进制安全客户端。
_binary_redis_client: Redis | None = None
_binary_redis_init_failed = False


async def _get_binary_redis(fallback: Redis | None) -> Redis | None:
    """惰性构建/复用 ``decode_responses=False`` 的 Redis 客户端（连接口径同
    cache_service.init_redis：同 URL、resolve_redis_password 解析口令）。

    构建失败时回退到调用方传入的共享客户端（维持既有行为可观测，不静默升级）。
    """
    global _binary_redis_client, _binary_redis_init_failed
    if _binary_redis_client is not None:
        return _binary_redis_client
    if _binary_redis_init_failed:
        return fallback
    try:
        from app.config import settings
        from app.core.redis_utils import resolve_redis_password

        password, _password_source = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
        kwargs: dict[str, Any] = {"decode_responses": False}
        if password:
            kwargs["password"] = password
        client = Redis.from_url(settings.REDIS_URL, **kwargs)
        # redis-py ping 重载返回 Awaitable[bool] | bool —— 显式 cast 供类型检查
        await cast("Awaitable[bool]", client.ping())
        _binary_redis_client = client
        return _binary_redis_client
    except Exception:
        # Redis 不可达等：回退共享客户端，让上层既有错误路径如实暴露
        _binary_redis_init_failed = True
        return fallback


class CRDTPersistenceManager:
    """
    CRDT 状态持久化管理器: 内存 -> Redis -> PostgreSQL
    CRDT Persistence Manager: Memory -> Redis -> PostgreSQL
    """

    def __init__(self, redis_client: Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session
        self._batch_buffer: list[Any] = []

    async def persist_snapshot(self, galaxy_id: str, ydoc: Y.YDoc):
        """
        1. 内存 -> Redis (高频写入)
        Memory -> Redis (High-frequency write)
        """
        # 序列化 Yjs 文档
        update_data = Y.encode_state_as_update(ydoc)

        # Redis 持久化 (TTL 24h)
        # G-05（wt395）: 必须走 decode_responses=False 的二进制安全客户端——
        # 二进制写入本身在共享客户端上可行，但对应 get 会在响应解析层炸掉，
        # 写读两端必须同一客户端形态（详见模块头 _get_binary_redis 注释）。
        client = await _get_binary_redis(self.redis)
        if client is None:
            raise RuntimeError("CRDTPersistenceManager: no redis client available for snapshot persist")

        key = f"crdt:snapshot:{galaxy_id}"
        await client.set(key, update_data, ex=86400)

        # 记录最后同步时间
        await client.set(f"crdt:timestamp:{galaxy_id}", _utcnow().isoformat(), ex=86400)

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
        # G-05（wt395）: 二进制安全客户端读取（共享 decode_responses=True 客户端
        # 在这里直接 UnicodeDecodeError，多端恢复面断裂——见模块头注释）。
        client = await _get_binary_redis(self.redis)
        if client is None:
            raise RuntimeError("CRDTPersistenceManager: no redis client available for snapshot restore")
        key = f"crdt:snapshot:{galaxy_id}"
        redis_data = await client.get(key)

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
