"""
WebSocket Monitoring API
Provides endpoints for monitoring WebSocket connection status and health.
Also includes device token management for push notifications.
"""
from __future__ import annotations
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.websocket import manager
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserDevice

router = APIRouter()


# ========== Device Token Schemas ==========

class DeviceRegisterRequest(BaseModel):
    """设备注册请求"""
    device_id: str
    push_token: str
    platform: str  # ios, android, web
    token_type: str = "fcm"  # fcm, apns, huawei
    device_name: str | None = None
    app_version: str | None = None
    os_version: str | None = None


class DeviceInfo(BaseModel):
    """设备信息"""
    id: str
    device_id: str
    platform: str
    token_type: str
    device_name: str | None
    app_version: str | None
    os_version: str | None
    is_active: bool
    last_used_at: str


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    devices: list[DeviceInfo]
    total: int


@router.get("/stats")
async def websocket_stats(current_user: User = Depends(get_current_user)):
    """
    Get WebSocket statistics.

    Returns connection counts and status information.
    Requires authentication (admin role recommended in production).
    """
    try:
        online_count = await manager.get_online_count()
        active_groups = len(manager.active_connections)
        active_users = len(manager.user_connections)
        total_connections = active_groups + active_users

        return {
            "status": "healthy",
            "stats": {
                "online_users": online_count,
                "active_group_connections": active_groups,
                "active_user_connections": active_users,
                "total_connections": total_connections,
            },
            "details": {
                "groups": list(manager.active_connections.keys()),
                "users": list(manager.user_connections.keys()),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/health")
async def websocket_health():
    """
    Simple health check endpoint for WebSocket service.

    Returns minimal status information without authentication.
    Useful for load balancers and monitoring systems.
    """
    try:
        active_connections = len(manager.active_connections) + len(manager.user_connections)
        redis_connected = manager.redis is not None

        return {
            "status": "healthy" if redis_connected else "degraded",
            "connections": active_connections,
            "redis_connected": redis_connected,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/online/{user_id}")
async def check_user_online(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a specific user is online.

    Can be used to implement presence indicators in the UI.
    """
    try:
        is_online = await manager.is_user_online(user_id)
        return {
            "user_id": user_id,
            "online": is_online,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check online status: {str(e)}")


@router.post("/ws/ack/{message_id}")
async def record_message_ack(
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Record ACK for a received message.

    Called by clients to confirm delivery of messages with msg_id.
    """
    try:
        await manager.record_ack(str(current_user.id), message_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record ACK: {str(e)}")


@router.get("/metrics")
async def websocket_metrics(current_user: User = Depends(get_current_user)):
    """
    Get detailed WebSocket metrics.

    Returns comprehensive metrics for monitoring and alerting.
    Consider adding admin role check in production.
    """
    try:
        return {
            "connections": {
                "active_groups": len(manager.active_connections),
                "active_users": len(manager.user_connections),
                "online_users": await manager.get_online_count(),
            },
            "friend_map_size": len(manager.friend_map),
            "redis_status": {
                "connected": manager.redis is not None,
                "pubsub_active": manager.pubsub is not None and manager.listener_task is not None,
            },
            "timestamp": manager.redis is not None  # Simple health indicator
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# ========== Device Token Management ==========

@router.post("/devices/register", response_model=DeviceInfo)
async def register_device(
    data: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """
    注册或更新用户设备推送令牌

    客户端应在以下情况调用此端点：
    - 应用首次启动
    - 推送令牌发生变化
    - 用户登录

    如果设备已存在（通过 user_id + device_id 判断），将更新令牌和信息。
    """
    try:
        async with AsyncSessionLocal() as db:
            # 查找现有设备
            result = await db.execute(
                select(UserDevice).where(
                    UserDevice.user_id == str(current_user.id),
                    UserDevice.device_id == data.device_id,
                )
            )
            device = result.scalar_one_or_none()

            from datetime import datetime
            now = datetime.now(timezone.utc)

            if device:
                # 更新现有设备
                device.push_token = data.push_token
                device.token_type = data.token_type
                device.platform = data.platform
                device.is_active = True
                device.last_used_at = now
                if data.device_name:
                    device.device_name = data.device_name
                if data.app_version:
                    device.app_version = data.app_version
                if data.os_version:
                    device.os_version = data.os_version
            else:
                # 创建新设备
                device = UserDevice(
                    user_id=str(current_user.id),
                    device_id=data.device_id,
                    push_token=data.push_token,
                    platform=data.platform,
                    token_type=data.token_type,
                    device_name=data.device_name,
                    app_version=data.app_version,
                    os_version=data.os_version,
                    is_active=True,
                    last_used_at=now,
                )
                db.add(device)

            await db.commit()
            await db.refresh(device)

            # 清除 Redis 缓存
            if manager.redis:
                cache_key = f"user:devices:{current_user.id}"
                await manager.redis.delete(cache_key)

            return DeviceInfo(
                id=str(device.id),
                device_id=device.device_id,
                platform=device.platform,
                token_type=device.token_type,
                device_name=device.device_name,
                app_version=device.app_version,
                os_version=device.os_version,
                is_active=device.is_active,
                last_used_at=device.last_used_at.isoformat() if device.last_used_at else "",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register device: {str(e)}")


@router.get("/devices", response_model=DeviceListResponse)
async def list_my_devices(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的所有设备

    返回用户已注册的设备列表，包括推送令牌状态。
    """
    try:
        async with AsyncSessionLocal() as db:
            query = select(UserDevice).where(
                UserDevice.user_id == str(current_user.id)
            )
            if active_only:
                query = query.where(UserDevice.is_active)

            query = query.order_by(UserDevice.last_used_at.desc())

            result = await db.execute(query)
            devices = result.scalars().all()

            device_infos = [
                DeviceInfo(
                    id=str(d.id),
                    device_id=d.device_id,
                    platform=d.platform,
                    token_type=d.token_type,
                    device_name=d.device_name,
                    app_version=d.app_version,
                    os_version=d.os_version,
                    is_active=d.is_active,
                    last_used_at=d.last_used_at.isoformat() if d.last_used_at else "",
                )
                for d in devices
            ]

            return DeviceListResponse(
                devices=device_infos,
                total=len(device_infos),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")


@router.delete("/devices/{device_id}")
async def unregister_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    停用设备推送令牌

    客户端应在以下情况调用此端点：
    - 用户登出
    - 用户卸载应用
    - 用户禁用推送通知

    停用后，该设备将不再收到推送通知。
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserDevice).where(
                    UserDevice.user_id == str(current_user.id),
                    UserDevice.device_id == device_id,
                )
            )
            device = result.scalar_one_or_none()

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            device.is_active = False
            await db.commit()

            # 清除 Redis 缓存
            if manager.redis:
                cache_key = f"user:devices:{current_user.id}"
                await manager.redis.delete(cache_key)

            return {"success": True, "message": "Device unregistered"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unregister device: {str(e)}")
