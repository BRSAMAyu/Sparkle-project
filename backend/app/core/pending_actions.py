"""
待确认操作管理
用于存储需要用户二次确认的高风险操作
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    """Return naive UTC datetime for compatibility with existing DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class PendingActionsStore:
    """
    待确认操作存储
    使用内存字典存储，支持过期清理
    """

    ACTION_KEY_PREFIX = "pending_action:"
    USER_INDEX_PREFIX = "pending_action_user:"

    def __init__(self, expire_minutes: int = 5, redis_client=None):
        """
        初始化存储

        Args:
            expire_minutes: 操作过期时间（分钟），默认 5 分钟
        """
        self._store: dict[str, dict[str, Any]] = {}
        self._expire_minutes = expire_minutes
        self._cleanup_task: asyncio.Task | None = None
        self.redis = redis_client

    def set_redis(self, redis_client) -> None:
        """Configure Redis client for persistent storage."""
        self.redis = redis_client

    async def save(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        description: str = "",
        preview_data: dict[str, Any] | None = None
    ) -> str:
        """
        保存待确认的操作

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            user_id: 用户 ID
            description: 操作描述
            preview_data: 预览数据

        Returns:
            str: 操作 ID (action_id)
        """
        action_id = str(uuid4())

        payload = {
            "action_id": action_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "user_id": user_id,
            "description": description,
            "preview_data": preview_data or {},
            "created_at": _utcnow(),
            "expires_at": _utcnow() + timedelta(minutes=self._expire_minutes),
        }

        if self.redis:
            key = f"{self.ACTION_KEY_PREFIX}{action_id}"
            ttl_seconds = int(self._expire_minutes * 60)
            await self.redis.setex(key, ttl_seconds, json.dumps(_serialize_payload(payload)))
            user_index_key = f"{self.USER_INDEX_PREFIX}{user_id}"
            await self.redis.sadd(user_index_key, action_id)
            await self.redis.expire(user_index_key, ttl_seconds)
        else:
            self._store[action_id] = payload
            # 启动清理任务（如果尚未启动）
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())

        return action_id

    # Lua script for atomic get-and-delete in Redis
    _CLAIM_LUA = """
    local data = redis.call('GET', KEYS[1])
    if not data then
        return nil
    end
    local parsed = cjson.decode(data)
    if parsed.user_id ~= ARGV[1] then
        return nil
    end
    redis.call('DEL', KEYS[1])
    redis.call('SREM', KEYS[2], ARGV[2])
    return data
    """

    async def claim(self, action_id: str, user_id: str) -> dict[str, Any] | None:
        """
        Atomically get and delete a pending action.

        Prevents concurrent claims of the same action (get-then-delete race).
        Use this instead of separate get() + delete() when processing an action.

        Args:
            action_id: Action ID
            user_id: User ID (ensures only the owner can claim)

        Returns:
            The action data if claimed, None if not found / already claimed / wrong user
        """
        if self.redis:
            key = f"{self.ACTION_KEY_PREFIX}{action_id}"
            user_index_key = f"{self.USER_INDEX_PREFIX}{user_id}"
            raw = await self.redis.eval(
                self._CLAIM_LUA, 2, key, user_index_key, user_id, action_id
            )
            if not raw:
                return None
            try:
                return json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                return None
        else:
            action = self._store.pop(action_id, None)
            if not action:
                return None
            if action["expires_at"] < _utcnow():
                return None
            if action.get("user_id") != user_id:
                # Put it back if wrong user
                self._store[action_id] = action
                return None
            return action

    async def get(self, action_id: str, user_id: str) -> dict[str, Any] | None:
        """
        获取待确认的操作

        Args:
            action_id: 操作 ID
            user_id: 用户 ID（确保用户只能访问自己的操作）

        Returns:
            Optional[Dict]: 操作数据，如果不存在或已过期返回 None
        """
        if self.redis:
            key = f"{self.ACTION_KEY_PREFIX}{action_id}"
            raw = await self.redis.get(key)
            if not raw:
                await self.redis.srem(f"{self.USER_INDEX_PREFIX}{user_id}", action_id)
                return None
            try:
                action = json.loads(raw)
            except Exception:
                return None
        else:
            action = self._store.get(action_id)
            if not action:
                return None

            # 检查是否过期
            if action["expires_at"] < _utcnow():
                del self._store[action_id]
                return None

        # 检查用户权限
        if action.get("user_id") != user_id:
            return None

        return action

    async def delete(self, action_id: str, user_id: str) -> bool:
        """
        删除待确认的操作

        Args:
            action_id: 操作 ID
            user_id: 用户 ID

        Returns:
            bool: 是否成功删除
        """
        if self.redis:
            key = f"{self.ACTION_KEY_PREFIX}{action_id}"
            raw = await self.redis.get(key)
            if not raw:
                await self.redis.srem(f"{self.USER_INDEX_PREFIX}{user_id}", action_id)
                return False
            try:
                action = json.loads(raw)
            except Exception:
                return False
            if action.get("user_id") != user_id:
                return False
            await self.redis.delete(key)
            await self.redis.srem(f"{self.USER_INDEX_PREFIX}{user_id}", action_id)
            return True

        action = self._store.get(action_id)
        if not action:
            return False
        # 检查用户权限
        if action["user_id"] != user_id:
            return False
        del self._store[action_id]
        return True

    async def _cleanup_expired(self):
        """
        清理过期的操作
        每分钟运行一次
        """
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次

                now = _utcnow()
                expired_keys = [
                    key
                    for key, value in self._store.items()
                    if value["expires_at"] < now
                ]

                for key in expired_keys:
                    del self._store[key]

            except asyncio.CancelledError:
                break
            except Exception as e:
                # 记录错误但不中断清理任务
                print(f"清理过期操作时出错: {e}")

    async def get_all_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """
        获取用户的所有待确认操作（用于测试和调试）

        Args:
            user_id: 用户 ID

        Returns:
            list: 操作列表
        """
        if self.redis:
            return await self._get_all_by_user_redis(user_id)
        return [
            action
            for action in self._store.values()
            if action["user_id"] == user_id and action["expires_at"] > _utcnow()
        ]

    async def _get_all_by_user_redis(self, user_id: str) -> list[dict[str, Any]]:
        user_index_key = f"{self.USER_INDEX_PREFIX}{user_id}"
        action_ids = await self.redis.smembers(user_index_key) if self.redis else []
        if not action_ids:
            return []

        actions = []
        now = _utcnow()
        for action_id in action_ids:
            key = f"{self.ACTION_KEY_PREFIX}{action_id}"
            raw = await self.redis.get(key)
            if not raw:
                await self.redis.srem(user_index_key, action_id)
                continue
            try:
                action = json.loads(raw)
            except Exception:
                await self.redis.srem(user_index_key, action_id)
                continue
            expires_at = action.get("expires_at")
            if expires_at and _parse_datetime(expires_at) < now:
                await self.redis.delete(key)
                await self.redis.srem(user_index_key, action_id)
                continue
            actions.append(action)
        return actions

    async def clear_all(self):
        """
        清空所有待确认操作（用于测试）
        """
        if self.redis:
            await self._clear_all_redis()
            return
        self._store.clear()

    async def _clear_all_redis(self) -> None:
        async for key in self.redis.scan_iter(match=f"{self.ACTION_KEY_PREFIX}*"):
            await self.redis.delete(key)
        async for key in self.redis.scan_iter(match=f"{self.USER_INDEX_PREFIX}*"):
            await self.redis.delete(key)


def _serialize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "created_at": payload["created_at"].isoformat(),
        "expires_at": payload["expires_at"].isoformat()
    }


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return _utcnow()


# 全局单例
pending_actions_store = PendingActionsStore()
