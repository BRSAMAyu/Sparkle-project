"""
用户设备服务
User Device Service - 管理用户设备和推送令牌
"""
from __future__ import annotations
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.models.user import UserDevice


def _utcnow_naive() -> datetime:
    """Return a naive UTC timestamp for legacy DateTime columns."""
    return datetime.utcnow()


class DeviceService:
    """用户设备令牌管理服务"""

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis = redis_client

    async def register_device(
        self,
        db: AsyncSession,
        user_id: str,
        device_id: str,
        push_token: str,
        platform: str,
        token_type: str = "fcm",
        device_name: str | None = None,
        app_version: str | None = None,
        os_version: str | None = None,
        device_metadata: dict | None = None,
    ) -> UserDevice:
        """
        注册或更新用户设备

        如果设备已存在（通过 user_id + device_id 判断），则更新令牌和信息
        如果设备不存在，则创建新记录
        """
        # 查找现有设备
        result = await db.execute(
            select(UserDevice).where(
                UserDevice.user_id == user_id,
                UserDevice.device_id == device_id,
            )
        )
        device = result.scalar_one_or_none()

        now = _utcnow_naive()

        if device:
            # 更新现有设备
            device.push_token = push_token
            device.token_type = token_type
            device.platform = platform
            device.is_active = True
            device.last_used_at = now
            if device_name:
                device.device_name = device_name
            if app_version:
                device.app_version = app_version
            if os_version:
                device.os_version = os_version
            if device_metadata:
                device.device_metadata = device_metadata
        else:
            # 创建新设备
            device = UserDevice(
                user_id=user_id,
                device_id=device_id,
                push_token=push_token,
                platform=platform,
                token_type=token_type,
                device_name=device_name,
                app_version=app_version,
                os_version=os_version,
                device_metadata=device_metadata,
                is_active=True,
                last_used_at=now,
            )
            db.add(device)

        await db.commit()
        await db.refresh(device)

        # 缓存到 Redis（用于快速查询）
        if self.redis:
            cache_key = f"user:devices:{user_id}"
            await self._cache_device_tokens(db, user_id, cache_key)

        return device

    async def get_user_devices(
        self,
        db: AsyncSession,
        user_id: str,
        active_only: bool = True,
    ) -> list[UserDevice]:
        """
        获取用户的所有设备
        """
        query = select(UserDevice).where(UserDevice.user_id == user_id)
        if active_only:
            query = query.where(UserDevice.is_active)

        result = await db.execute(query.order_by(UserDevice.last_used_at.desc()))
        return list(result.scalars().all())

    async def deactivate_device(
        self,
        db: AsyncSession,
        user_id: str,
        device_id: str,
    ) -> bool:
        """
        停用设备令牌（用户登出或设备卸载应用时调用）
        """
        result = await db.execute(
            select(UserDevice).where(
                UserDevice.user_id == user_id,
                UserDevice.device_id == device_id,
            )
        )
        device = result.scalar_one_or_none()

        if device:
            device.is_active = False
            await db.commit()

            # 清除 Redis 缓存
            if self.redis:
                cache_key = f"user:devices:{user_id}"
                await self.redis.delete(cache_key)

            return True
        return False

    async def get_user_device_tokens(
        self,
        db: AsyncSession,
        user_id: str,
        active_only: bool = True,
    ) -> list[str]:
        """
        获取用户的所有活跃设备推送令牌

        这是 ConnectionManager._get_user_device_tokens 的实现
        """
        # 先尝试从 Redis 缓存读取
        if self.redis:
            cache_key = f"user:devices:{user_id}"
            cached = await self.redis.get(cache_key)
            if cached:
                import json
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    pass  # 缓存损坏，继续查询数据库

        # 查询数据库
        query = select(UserDevice.push_token).where(UserDevice.user_id == user_id)
        if active_only:
            query = query.where(UserDevice.is_active)

        result = await db.execute(query)
        tokens = [row[0] for row in result.all()]

        # 写入缓存（5分钟 TTL）
        if self.redis and tokens:
            cache_key = f"user:devices:{user_id}"
            import json
            await self.redis.setex(
                cache_key,
                300,  # 5分钟
                json.dumps(tokens)
            )

        return tokens

    async def _cache_device_tokens(
        self,
        db: AsyncSession,
        user_id: str,
        cache_key: str,
    ):
        """辅助方法：缓存用户设备令牌到 Redis"""
        import json
        tokens = await self.get_user_device_tokens(db, user_id, active_only=True)
        await self.redis.setex(cache_key, 300, json.dumps(tokens))

    async def cleanup_inactive_devices(
        self,
        db: AsyncSession,
        days_threshold: int = 30,
    ) -> int:
        """
        清理长时间未使用的设备标记

        默认清理30天未使用的设备
        返回清理的设备数量
        """
        from datetime import timedelta

        threshold_date = _utcnow_naive() - timedelta(days=days_threshold)

        result = await db.execute(
            select(UserDevice).where(
                UserDevice.last_used_at < threshold_date,
                UserDevice.is_active,
            )
        )
        devices = result.scalars().all()

        count = 0
        for device in devices:
            device.is_active = False
            count += 1

        await db.commit()
        return count


# 全局设备服务实例（延迟初始化）
_device_service: DeviceService | None = None


def get_device_service() -> DeviceService:
    """获取设备服务单例"""
    global _device_service
    if _device_service is None:
        # 使用 websocket manager 的 redis 实例
        _device_service = DeviceService(redis_client=manager.redis)
    return _device_service
