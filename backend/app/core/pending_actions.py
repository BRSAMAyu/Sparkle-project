"""
待确认操作管理
用于存储需要用户二次确认的高风险操作

MVP 阶段使用内存存储，生产环境可升级为 Redis
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from uuid import uuid4


class PendingActionsStore:
    """
    待确认操作存储
    使用内存字典存储，支持过期清理
    """

    def __init__(self, expire_minutes: int = 5):
        """
        初始化存储

        Args:
            expire_minutes: 操作过期时间（分钟），默认 5 分钟
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._expire_minutes = expire_minutes
        self._cleanup_task: Optional[asyncio.Task] = None

    async def save(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        description: str = "",
        preview_data: Optional[Dict[str, Any]] = None
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

        self._store[action_id] = {
            "action_id": action_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "user_id": user_id,
            "description": description,
            "preview_data": preview_data or {},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=self._expire_minutes),
        }

        # 启动清理任务（如果尚未启动）
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())

        return action_id

    async def get(self, action_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取待确认的操作

        Args:
            action_id: 操作 ID
            user_id: 用户 ID（确保用户只能访问自己的操作）

        Returns:
            Optional[Dict]: 操作数据，如果不存在或已过期返回 None
        """
        action = self._store.get(action_id)

        if not action:
            return None

        # 检查是否过期
        if action["expires_at"] < datetime.utcnow():
            del self._store[action_id]
            return None

        # 检查用户权限
        if action["user_id"] != user_id:
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

                now = datetime.utcnow()
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

    def get_all_by_user(self, user_id: str) -> list[Dict[str, Any]]:
        """
        获取用户的所有待确认操作（用于测试和调试）

        Args:
            user_id: 用户 ID

        Returns:
            list: 操作列表
        """
        return [
            action
            for action in self._store.values()
            if action["user_id"] == user_id and action["expires_at"] > datetime.utcnow()
        ]

    def clear_all(self):
        """
        清空所有待确认操作（用于测试）
        """
        self._store.clear()


# 全局单例
pending_actions_store = PendingActionsStore()
