"""
Session State Manager
基于 Redis 的分布式状态管理，支持 FSM 持久化和会话恢复
"""
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, asdict
from uuid import UUID

# FSM States (与 orchestrator.py 保持一致)
STATE_INIT = "INIT"
STATE_THINKING = "THINKING"
STATE_GENERATING = "GENERATING"
STATE_TOOL_CALLING = "TOOL_CALLING"
STATE_DONE = "DONE"
STATE_FAILED = "FAILED"


@dataclass
class FSMState:
    """FSM 状态数据结构"""
    session_id: str
    state: str
    details: str = ""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: float = 0.0
    # 用于断点续传
    last_processed_message: Optional[str] = None
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
    def from_json(cls, data: str) -> 'FSMState':
        return cls(**json.loads(data))


class SessionStateManager:
    """
    会话状态管理器
    负责 FSM 状态的持久化、恢复和分布式锁管理
    """
    
    def __init__(self, redis_client, ttl: int = 3600):
        """
        Args:
            redis_client: Redis 客户端实例
            ttl: 状态过期时间（秒），默认 1 小时
        """
        self.redis = redis_client
        self.ttl = ttl
        self.lock_ttl = 30  # 锁的过期时间（秒）
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
            key = self._get_state_key(session_id)
            await self.redis.setex(key, self.ttl, state.to_json())
            logger.debug(f"Saved state for session {session_id}: {state.state}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state for session {session_id}: {e}")
            return False

    async def load_state(self, session_id: str) -> Optional[FSMState]:
        """
        从 Redis 恢复 FSM 状态
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[FSMState]: 恢复的状态，如果不存在则返回 None
        """
        try:
            key = self._get_state_key(session_id)
            data = await self.redis.get(key)
            
            if not data:
                logger.debug(f"No saved state found for session {session_id}")
                return None
            
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
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
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
            return await self.save_state(session_id, new_state)
            
        except Exception as e:
            logger.error(f"Failed to update state for session {session_id}: {e}")
            return False

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

    async def cache_response(self, session_id: str, request_id: str, response: Dict[str, Any], ttl: int = 300) -> bool:
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

    async def get_cached_response(self, session_id: str, request_id: str) -> Optional[Dict[str, Any]]:
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

    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
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