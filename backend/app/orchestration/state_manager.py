"""
Session State Manager
基于 Redis 的分布式状态管理，支持 FSM 持久化和会话恢复

扩展功能:
- 活跃计划管理（P0: 任务→计划自动切换）
- 计划上下文跟踪
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger
from prometheus_client import Counter
from sqlalchemy import select

from app.core.metrics import get_or_create_metric

if TYPE_CHECKING:
    from app.services.plan_matching_service import PlanMatchingService

# FSM States (与 orchestrator.py 保持一致)
STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"


SESSION_LOCK_ACQUIRE_FAILURES_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_session_lock_acquire_failures_total",
    "Total session lock acquire failures caused by lock contention",
)


@dataclass
class FSMState:
    """FSM 状态数据结构"""
    session_id: str
    state: str
    details: str = ""
    request_id: str | None = None
    user_id: str | None = None
    timestamp: float = 0.0
    # 用于断点续传
    last_processed_message: str | None = None
    accumulated_response: str = ""
    tool_calls_in_progress: list = None

    def __post_init__(self):
        if self.tool_calls_in_progress is None:
            self.tool_calls_in_progress = []
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> FSMState:
        return cls(**json.loads(data))


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SessionStateManager:
    """
    会话状态管理器
    负责 FSM 状态的持久化、恢复和分布式锁管理
    """

    _DURABLE_RECOVERABLE_STATES = {STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_TOOL_CALLING, STATE_FAILED}

    def __init__(self, redis_client, ttl: int = 3600, db_session=None):
        """
        Args:
            redis_client: Redis 客户端实例
            ttl: 状态过期时间（秒），默认 1 小时
        """
        self.redis = redis_client
        self.ttl = ttl
        self.lock_ttl = 30  # 锁的过期时间（秒）
        self.db_session = db_session
        logger.info("SessionStateManager initialized")

    def _get_state_key(self, session_id: str) -> str:
        """生成状态键"""
        return f"session:{session_id}:state"

    def _get_lock_key(self, session_id: str) -> str:
        """生成锁键"""
        return f"session:{session_id}:lock"

    def _get_response_key(self, session_id: str, request_id: str) -> str:
        """生成缓存响应键"""
        return f"session:{session_id}:response:{request_id}"

    async def save_state(self, session_id: str, state: FSMState) -> bool:
        """
        保存 FSM 状态到 Redis

        Args:
            session_id: 会话 ID
            state: FSM 状态对象

        Returns:
            bool: 是否成功
        """
        try:
            if self.redis is None:
                return False
            key = self._get_state_key(session_id)
            await self.redis.setex(key, self.ttl, state.to_json())
            logger.debug(f"Saved state for session {session_id}: {state.state}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state for session {session_id}: {e}")
            return False

    async def load_state(self, session_id: str) -> FSMState | None:
        """
        从 Redis 恢复 FSM 状态

        Args:
            session_id: 会话 ID

        Returns:
            Optional[FSMState]: 恢复的状态，如果不存在则返回 None
        """
        try:
            if self.redis is None:
                return await self._load_durable_state(session_id)
            key = self._get_state_key(session_id)
            data = await self.redis.get(key)

            if not data:
                logger.debug(f"No saved state found for session {session_id}")
                durable = await self._load_durable_state(session_id)
                if durable is not None:
                    await self.save_state(session_id, durable)
                return durable

            state = FSMState.from_json(data)
            logger.info(f"Restored state for session {session_id}: {state.state}")
            return state
        except Exception as e:
            logger.error(f"Failed to restore state for session {session_id}: {e}")
            return None

    async def update_state(
        self,
        session_id: str,
        state: str,
        details: str = "",
        request_id: str | None = None,
        user_id: str | None = None,
        **kwargs
    ) -> bool:
        """
        更新 FSM 状态（原子操作）

        Args:
            session_id: 会话 ID
            state: 新状态
            details: 状态详情
            request_id: 请求 ID
            user_id: 用户 ID
            **kwargs: 其他要更新的字段

        Returns:
            bool: 是否成功
        """
        try:
            # 先加载现有状态
            existing = await self.load_state(session_id)

            if existing:
                # 更新现有状态
                existing.state = state
                existing.details = details
                existing.timestamp = datetime.now().timestamp()
                if request_id:
                    existing.request_id = request_id
                if user_id:
                    existing.user_id = user_id

                # 更新其他字段
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)

                new_state = existing
            else:
                # 创建新状态
                new_state = FSMState(
                    session_id=session_id,
                    state=state,
                    details=details,
                    request_id=request_id,
                    user_id=user_id,
                    timestamp=datetime.now().timestamp(),
                    **kwargs
                )

            # 保存到 Redis
            saved = await self.save_state(session_id, new_state)
            await self._persist_durable_state(new_state)
            return saved

        except Exception as e:
            logger.error(f"Failed to update state for session {session_id}: {e}")
            return False

    async def _persist_durable_state(self, state: FSMState) -> None:
        if self.db_session is None:
            return
        try:
            from app.aurora.runtime_v1.models import DurableSessionStateSnapshot

            now = _utcnow()
            recoverable = state.state in self._DURABLE_RECOVERABLE_STATES
            expires_at = now + timedelta(hours=6 if recoverable else 1)
            payload = asdict(state)
            result = await self.db_session.execute(
                select(DurableSessionStateSnapshot).where(
                    DurableSessionStateSnapshot.session_id == state.session_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = DurableSessionStateSnapshot(session_id=state.session_id)
                self.db_session.add(record)
            record.user_id = state.user_id
            record.request_id = state.request_id
            record.fsm_state = state.state
            record.details = state.details or ""
            record.payload = payload
            record.recoverable = recoverable
            record.last_seen_at = now
            record.expires_at = expires_at
            record.runtime_metadata = {"source": "SessionStateManager.update_state"}
            await self.db_session.flush()
        except Exception as exc:
            logger.debug(f"Failed to persist durable FSM state for {state.session_id}: {exc}")

    async def _load_durable_state(self, session_id: str) -> FSMState | None:
        if self.db_session is None:
            return None
        try:
            from app.aurora.runtime_v1.models import DurableSessionStateSnapshot

            now = _utcnow()
            result = await self.db_session.execute(
                select(DurableSessionStateSnapshot)
                .where(
                    DurableSessionStateSnapshot.session_id == session_id,
                    DurableSessionStateSnapshot.recoverable.is_(True),
                    DurableSessionStateSnapshot.expires_at > now,
                )
                .order_by(DurableSessionStateSnapshot.last_seen_at.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return None
            payload = dict(record.payload or {})
            if payload.get("state") == STATE_DONE:
                return None
            logger.info(f"Recovered durable FSM state for session {session_id}: {payload.get('state')}")
            return FSMState.from_json(json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.debug(f"Failed to load durable FSM state for {session_id}: {exc}")
            return None

    async def acquire_lock(self, session_id: str, request_id: str) -> bool:
        """
        获取分布式锁（防止并发请求冲突）

        Args:
            session_id: 会话 ID
            request_id: 请求 ID

        Returns:
            bool: 是否成功获取锁
        """
        try:
            lock_key = self._get_lock_key(session_id)
            # 使用 NX 选项：仅当 key 不存在时设置
            result = await self.redis.set(
                lock_key,
                request_id,
                nx=True,  # Only set if not exists
                ex=self.lock_ttl
            )

            if result:
                logger.debug(f"Lock acquired for session {session_id} by request {request_id}")
                return True
            else:
                # 检查是否是同一个请求（重试场景）
                existing = await self.redis.get(lock_key)
                if existing == request_id:
                    logger.debug(f"Lock already held by same request {request_id}")
                    return True
                SESSION_LOCK_ACQUIRE_FAILURES_TOTAL.inc()
                logger.warning(f"Failed to acquire lock for session {session_id}, already locked")
                return False

        except Exception as e:
            logger.error(f"Error acquiring lock for session {session_id}: {e}")
            return False

    async def release_lock(self, session_id: str, request_id: str) -> bool:
        """
        释放分布式锁（使用 Lua 脚本保证原子性）

        Args:
            session_id: 会话 ID
            request_id: 请求 ID

        Returns:
            bool: 是否成功释放
        """
        try:
            lock_key = self._get_lock_key(session_id)

            # Lua 脚本：原子性地检查并删除
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            result = await self.redis.eval(lua_script, 1, lock_key, request_id)

            if result:
                logger.debug(f"Lock released for session {session_id} by request {request_id}")
                return True
            else:
                logger.warning(f"Failed to release lock for session {session_id}, not owner")
                return False

        except Exception as e:
            logger.error(f"Error releasing lock for session {session_id}: {e}")
            return False

    async def renew_lock(self, session_id: str, request_id: str) -> bool:
        """
        续期锁（延长锁的 TTL）

        用于长时间运行的任务，防止锁在处理完成前过期。

        Args:
            session_id: 会话 ID
            request_id: 请求 ID

        Returns:
            bool: 是否成功续期
        """
        try:
            lock_key = self._get_lock_key(session_id)

            # Lua script: 仅当 lock owner 匹配时才续期
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """

            result = await self.redis.eval(lua_script, 1, lock_key, request_id, self.lock_ttl)

            if result:
                logger.debug(f"Lock renewed for session {session_id}")
                return True
            else:
                logger.warning(f"Failed to renew lock for session {session_id}, not owner or expired")
                return False

        except Exception as e:
            logger.error(f"Error renewing lock for session {session_id}: {e}")
            return False

    async def _lock_renewal_task(
        self,
        session_id: str,
        request_id: str,
        stop_event: asyncio.Event,
        interval: float = 10.0
    ):
        """
        后台锁续期任务

        Args:
            session_id: 会话 ID
            request_id: 请求 ID
            stop_event: 停止事件
            interval: 续期间隔（秒），默认 10 秒
        """
        try:
            while not stop_event.is_set():
                # 等待 interval 秒或直到收到停止信号
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                    break  # 收到停止信号，退出循环
                except TimeoutError:
                    # 超时，执行续期
                    pass

                success = await self.renew_lock(session_id, request_id)
                if not success:
                    logger.warning(f"Lock renewal failed for session {session_id}, stopping renewal")
                    break
        except asyncio.CancelledError:
            logger.debug(f"Lock renewal task cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Lock renewal task error for session {session_id}: {e}")

    async def start_lock_renewal(
        self,
        session_id: str,
        request_id: str,
        interval: float = 10.0
    ) -> tuple[asyncio.Task, asyncio.Event]:
        """
        启动锁续期后台任务

        Args:
            session_id: 会话 ID
            request_id: 请求 ID
            interval: 续期间隔（秒），默认 10 秒

        Returns:
            Tuple[asyncio.Task, asyncio.Event]: (续期任务, 停止事件)
        """
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._lock_renewal_task(session_id, request_id, stop_event, interval)
        )
        logger.debug(f"Started lock renewal task for session {session_id}")
        return task, stop_event

    async def stop_lock_renewal(self, task: asyncio.Task, stop_event: asyncio.Event):
        """
        停止锁续期后台任务

        Args:
            task: 续期任务
            stop_event: 停止事件
        """
        stop_event.set()
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (TimeoutError, asyncio.CancelledError):
            pass
        logger.debug("Stopped lock renewal task")

    async def cache_response(self, session_id: str, request_id: str, response: dict[str, Any], ttl: int = 300) -> bool:
        """
        缓存完整响应（用于幂等性和断点续传）

        Args:
            session_id: 会话 ID
            request_id: 请求 ID
            response: 响应数据
            ttl: 缓存过期时间（秒），默认 5 分钟

        Returns:
            bool: 是否成功
        """
        try:
            key = self._get_response_key(session_id, request_id)
            await self.redis.setex(key, ttl, json.dumps(response, ensure_ascii=False))
            logger.debug(f"Cached response for session {session_id}, request {request_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
            return False

    async def get_cached_response(self, session_id: str, request_id: str) -> dict[str, Any] | None:
        """
        获取缓存的响应（幂等性检查）

        Args:
            session_id: 会话 ID
            request_id: 请求 ID

        Returns:
            Optional[Dict]: 缓存的响应，如果不存在则返回 None
        """
        try:
            key = self._get_response_key(session_id, request_id)
            data = await self.redis.get(key)

            if data:
                logger.info(f"Hit cache for session {session_id}, request {request_id}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None

    async def is_duplicate_request(self, session_id: str, request_id: str) -> bool:
        """
        检查是否是重复请求

        Args:
            session_id: 会话 ID
            request_id: 请求 ID

        Returns:
            bool: 是否是重复请求
        """
        cached = await self.get_cached_response(session_id, request_id)
        return cached is not None

    async def cleanup_session(self, session_id: str) -> bool:
        """
        清理会话数据（用于测试或手动清理）

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否成功
        """
        try:
            state_key = self._get_state_key(session_id)
            lock_key = self._get_lock_key(session_id)

            # 删除状态和锁
            await self.redis.delete(state_key, lock_key)

            # 删除所有缓存的响应（使用模式匹配）
            pattern = f"session:{session_id}:response:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)

            logger.info(f"Cleaned up session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return False

    async def get_session_stats(self, session_id: str) -> dict[str, Any] | None:
        """
        获取会话统计信息

        Args:
            session_id: 会话 ID

        Returns:
            Optional[Dict]: 统计信息
        """
        try:
            state = await self.load_state(session_id)
            if not state:
                return None

            return {
                "session_id": session_id,
                "current_state": state.state,
                "last_update": datetime.fromtimestamp(state.timestamp).isoformat(),
                "details": state.details,
                "request_id": state.request_id,
                "user_id": state.user_id,
                "has_cached_response": True,  # 简化，实际可检查
                "ttl_remaining": await self.redis.ttl(self._get_state_key(session_id))
            }
        except Exception as e:
            logger.error(f"Failed to get stats for session {session_id}: {e}")
            return None

    # ========== Active Plan Management (P0: 任务→计划自动切换) ==========

    def _get_active_plan_key(self, session_id: str) -> str:
        """生成活跃计划键"""
        return f"session:{session_id}:active_plan"

    async def set_active_plan(
        self,
        session_id: str,
        plan_id: UUID,
        reason: str = "manual"
    ) -> bool:
        """
        设置会话的活跃计划

        Args:
            session_id: 会话 ID
            plan_id: 计划 ID
            reason: 切换原因 (manual, auto_match, task_context)

        Returns:
            bool: 是否成功
        """
        try:
            key = self._get_active_plan_key(session_id)
            data = {
                "plan_id": str(plan_id),
                "reason": reason,
                "switched_at": _utcnow().isoformat()
            }
            await self.redis.setex(key, self.ttl, json.dumps(data))
            logger.info(f"Active plan set to {plan_id} for session {session_id}, reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to set active plan for session {session_id}: {e}")
            return False

    async def get_active_plan(self, session_id: str) -> dict[str, Any] | None:
        """
        获取会话的活跃计划

        Args:
            session_id: 会话 ID

        Returns:
            Dict with plan_id, reason, switched_at or None
        """
        try:
            key = self._get_active_plan_key(session_id)
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get active plan for session {session_id}: {e}")
            return None

    async def get_active_plan_id(self, session_id: str) -> UUID | None:
        """
        获取会话的活跃计划 ID

        Args:
            session_id: 会话 ID

        Returns:
            计划 ID 或 None
        """
        data = await self.get_active_plan(session_id)
        if data and data.get("plan_id"):
            return UUID(data["plan_id"])
        return None

    async def auto_switch_plan(
        self,
        session_id: str,
        user_id: UUID,
        task_context: dict[str, Any],
        db_session=None,
        plan_matching_service: PlanMatchingService | None = None
    ) -> UUID | None:
        """
        根据任务上下文自动切换计划

        智能匹配逻辑:
        1. 提取任务关键词/主题
        2. 与用户活跃计划进行相似度匹配
        3. 如果找到更匹配的计划，自动切换

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            task_context: 任务上下文 {"content": str, "type": str, ...}
            db_session: 数据库会话（用于查询计划）
            plan_matching_service: 计划匹配服务

        Returns:
            切换后的计划 ID，如果未切换则返回当前计划 ID
        """
        try:
            current_plan_data = await self.get_active_plan(session_id)
            current_plan_id = UUID(current_plan_data["plan_id"]) if current_plan_data else None

            # 如果没有提供匹配服务，无法进行自动匹配
            if not plan_matching_service:
                logger.debug(f"No plan matching service provided, skipping auto-switch for session {session_id}")
                return current_plan_id

            # 使用匹配服务查找最佳计划
            matched_plan = await plan_matching_service.match_task_to_plan(
                user_id=user_id,
                task_content=task_context.get("content", ""),
                task_type=task_context.get("type", "chat"),
                current_plan_id=current_plan_id
            )

            if matched_plan and (not current_plan_id or matched_plan.id != current_plan_id):
                # 切换到新计划
                await self.set_active_plan(
                    session_id=session_id,
                    plan_id=matched_plan.id,
                    reason="auto_match"
                )
                logger.info(
                    f"Auto-switched plan from {current_plan_id} to {matched_plan.id} "
                    f"for session {session_id}"
                )
                return matched_plan.id

            return current_plan_id

        except Exception as e:
            logger.error(f"Failed to auto-switch plan for session {session_id}: {e}")
            return None

    async def clear_active_plan(self, session_id: str) -> bool:
        """
        清除会话的活跃计划

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否成功
        """
        try:
            key = self._get_active_plan_key(session_id)
            await self.redis.delete(key)
            logger.debug(f"Active plan cleared for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear active plan for session {session_id}: {e}")
            return False

    async def get_plan_switch_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        获取计划切换历史

        Args:
            session_id: 会话 ID
            limit: 返回数量限制

        Returns:
            切换历史列表
        """
        # 简化实现：当前只存储最新状态
        # 完整实现需要使用 Redis List 或单独的历史表
        current = await self.get_active_plan(session_id)
        if current:
            return [current]
        return []


# Backwards-compatible alias for benchmarks/tests
StateManager = SessionStateManager
