"""
Device Registration API

Handles registration and management of user device tokens for push notifications.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User, UserDevice
from app.services.push_sender_service import PushSenderService

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegistrationRequest(BaseModel):
    """Request to register a device token"""

    device_id: str = Field(..., description="Unique device identifier")
    push_token: str = Field(..., description="FCM/APNs push token")
    platform: str = Field(..., description="Platform: ios, android, web")
    token_type: str = Field(default="fcm", description="Token type: fcm, apns")
    device_name: str | None = Field(default=None, description="Device name")
    app_version: str | None = Field(default=None, description="App version")
    os_version: str | None = Field(default=None, description="OS version")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class DeviceRegistrationResponse(BaseModel):
    """Response for device registration"""

    success: bool
    device_id: str
    message: str


class DeviceUnregisterRequest(BaseModel):
    """Request to unregister a device"""

    device_id: str = Field(..., description="Device identifier to unregister")


@router.post("/register", response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceRegistrationResponse:
    """
    Register or update a device token for push notifications.

    This endpoint:
    1. Registers a new device token
    2. Updates existing device token if device_id already exists
    3. Associates the device with the current user
    """
    try:
        push_service = PushSenderService(db)

        device = await push_service.register_device_token(
            user_id=current_user.id,
            device_id=request.device_id,
            push_token=request.push_token,
            platform=request.platform,
            token_type=request.token_type,
            device_name=request.device_name,
            app_version=request.app_version,
            os_version=request.os_version,
            metadata=request.metadata,
        )

        return DeviceRegistrationResponse(
            success=True,
            device_id=device.device_id,
            message="Device registered successfully",
        )

    except Exception as e:
        logger.error(f"Failed to register device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register device: {str(e)}",
        ) from e


@router.delete("/unregister", response_model=DeviceRegistrationResponse)
async def unregister_device(
    request: DeviceUnregisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceRegistrationResponse:
    """
    Unregister a device (mark as inactive).

    The device record is kept but marked as inactive to prevent
    further push notifications to this device.
    """
    try:
        push_service = PushSenderService(db)

        success = await push_service.unregister_device_token(
            user_id=current_user.id,
            device_id=request.device_id,
        )

        if success:
            return DeviceRegistrationResponse(
                success=True,
                device_id=request.device_id,
                message="Device unregistered successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister device: {str(e)}",
        ) from e


@router.get("/list")
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List all registered devices for the current user.
    """
    try:
        query = select(UserDevice).where(
            UserDevice.user_id == str(current_user.id),
            UserDevice.is_active,
        ).order_by(UserDevice.last_used_at.desc())

        result = await db.execute(query)
        devices = result.scalars().all()

        return [
            {
                "device_id": device.device_id,
                "platform": device.platform,
                "device_name": device.device_name,
                "app_version": device.app_version,
                "os_version": device.os_version,
                "last_used_at": device.last_used_at.isoformat() if device.last_used_at else None,
                "created_at": device.created_at.isoformat() if device.created_at else None,
            }
            for device in devices
        ]

    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list devices: {str(e)}",
        ) from e
