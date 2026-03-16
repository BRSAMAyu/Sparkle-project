"""
Push Router Service

Intelligent push notification routing service that selects the optimal
push channel based on user region and device capabilities.

Routing Strategy:
- Chinese domestic users (region='cn') → JPush (more stable, no GFW issues)
- International users (region='international') → FCM
- Fallback: If primary channel fails, try secondary channel

Features:
- Automatic region detection based on device metadata
- Token type prioritization
- Channel failover support
- Unified interface for push notifications
"""
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase_config import is_firebase_available
from app.core.jpush_config import is_jpush_available
from app.models.user import UserDevice
from app.services.jpush_sender_service import (
    JPushPayload,
    JPushSenderService,
)
from app.services.push_sender_service import (
    PushPayload,
    PushResult,
    PushSenderService,
)


class PushChannel(str, Enum):
    """Available push channels"""
    FCM = "fcm"
    JPUSH = "jpush"
    APNS = "apns"
    UNKNOWN = "unknown"


@dataclass
class RoutedPushResult:
    """Result of a routed push notification"""
    success: bool
    primary_channel: PushChannel
    primary_result: PushResult | None = None
    fallback_channel: PushChannel | None = None
    fallback_result: PushResult | None = None
    error: str | None = None


@dataclass
class DevicePushInfo:
    """Device information for push routing"""
    device_id: str
    push_token: str
    token_type: str  # fcm, jpush, apns, huawei
    platform: str  # ios, android, web
    region: str | None = None
    is_active: bool = True


class PushRouterService:
    """
    Intelligent push notification router.

    Routes notifications to the optimal push channel based on:
    1. Device token type (jpush, fcm, apns)
    2. Device region (cn, international)
    3. Channel availability

    Usage:
        async with AsyncSessionLocal() as db:
            router = PushRouterService(db)
            result = await router.send_to_user(
                user_id=user_id,
                title="New message",
                body="You have a new message",
            )
    """

    # Region priorities for channel selection
    CN_CHANNELS = [PushChannel.JPUSH, PushChannel.FCM]  # JPush first for China
    INTL_CHANNELS = [PushChannel.FCM, PushChannel.JPUSH]  # FCM first for international

    def __init__(self, db: AsyncSession):
        self.db = db
        self._fcm_service = PushSenderService(db)
        self._jpush_service = JPushSenderService(db)

    async def send_to_user(
        self,
        user_id: UUID | str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        deep_link: str | None = None,
        notification_type: str = "system",
        image: str | None = None,
        prefer_channel: PushChannel | None = None,
        enable_fallback: bool = True,
    ) -> RoutedPushResult:
        """
        Send push notification to all devices of a user.

        Args:
            user_id: Target user ID
            title: Notification title
            body: Notification body
            data: Additional data payload
            deep_link: Deep link URL
            notification_type: Type of notification
            image: Image URL
            prefer_channel: Preferred channel override
            enable_fallback: Enable fallback to secondary channel

        Returns:
            RoutedPushResult with details
        """
        user_id_str = str(user_id)

        # Get user's devices
        devices = await self._get_user_devices(user_id_str)
        if not devices:
            logger.debug(f"No active devices found for user {user_id}")
            return RoutedPushResult(
                success=False,
                primary_channel=PushChannel.UNKNOWN,
                error="No active devices",
            )

        # Group devices by preferred channel
        devices_by_channel = self._group_devices_by_channel(
            devices, prefer_channel
        )

        # Try to send via each channel
        results: list[tuple[PushChannel, PushResult | None, bool]] = []

        for channel, channel_devices in devices_by_channel.items():
            if not channel_devices:
                continue

            result = await self._send_via_channel(
                channel=channel,
                devices=channel_devices,
                title=title,
                body=body,
                data=data,
                deep_link=deep_link,
                notification_type=notification_type,
                image=image,
            )

            success = result.success if result else False
            results.append((channel, result, success))

            # If successful and no fallback needed, break
            if success and not enable_fallback:
                break

            # If failed and fallback enabled, continue to next channel
            if not success and enable_fallback:
                logger.info(
                    f"Push via {channel.value} failed, trying fallback..."
                )
                continue

        # Determine final result
        primary_channel, primary_result, primary_success = results[0] if results else (PushChannel.UNKNOWN, None, False)

        # Check if any channel succeeded
        any_success = any(success for _, _, success in results)

        return RoutedPushResult(
            success=any_success,
            primary_channel=primary_channel,
            primary_result=primary_result,
            fallback_channel=results[1][0] if len(results) > 1 and not primary_success else None,
            fallback_result=results[1][1] if len(results) > 1 and not primary_success else None,
            error=None if any_success else "All push channels failed",
        )

    async def send_to_device(
        self,
        device: DevicePushInfo,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        deep_link: str | None = None,
        notification_type: str = "system",
        image: str | None = None,
        enable_fallback: bool = True,
    ) -> RoutedPushResult:
        """
        Send push notification to a specific device.

        Args:
            device: DevicePushInfo object
            title: Notification title
            body: Notification body
            data: Additional data payload
            deep_link: Deep link URL
            notification_type: Type of notification
            image: Image URL
            enable_fallback: Enable fallback to secondary channel

        Returns:
            RoutedPushResult with details
        """
        # Determine primary channel based on device info
        primary_channel = self._determine_channel(device)
        fallback_channel = self._get_fallback_channel(primary_channel)

        # Try primary channel
        primary_result = await self._send_via_channel(
            channel=primary_channel,
            devices=[device],
            title=title,
            body=body,
            data=data,
            deep_link=deep_link,
            notification_type=notification_type,
            image=image,
        )

        primary_success = primary_result.success if primary_result else False

        # If primary failed and fallback enabled, try fallback
        fallback_result = None
        if not primary_success and enable_fallback and fallback_channel:
            logger.info(
                f"Push via {primary_channel.value} failed, "
                f"trying fallback via {fallback_channel.value}"
            )
            fallback_result = await self._send_via_channel(
                channel=fallback_channel,
                devices=[device],
                title=title,
                body=body,
                data=data,
                deep_link=deep_link,
                notification_type=notification_type,
                image=image,
            )

        any_success = (
            primary_success or
            (fallback_result.success if fallback_result else False)
        )

        return RoutedPushResult(
            success=any_success,
            primary_channel=primary_channel,
            primary_result=primary_result,
            fallback_channel=fallback_channel if not primary_success else None,
            fallback_result=fallback_result,
            error=None if any_success else "All push channels failed",
        )

    def _determine_channel(self, device: DevicePushInfo) -> PushChannel:
        """
        Determine the optimal push channel for a device.

        Priority:
        1. Token type (if jpush token exists, use JPush)
        2. Region (cn -> JPush, international -> FCM)
        3. Platform (iOS -> APNs through FCM, Android -> FCM)
        """
        # Check token type first
        token_type = device.token_type.lower()
        if token_type == "jpush":
            if is_jpush_available():
                return PushChannel.JPUSH
        elif token_type in ["fcm", "apns"]:
            if is_firebase_available():
                return PushChannel.FCM

        # Check region
        region = device.region or self._infer_region_from_token(device.push_token)

        if region == "cn" and is_jpush_available():
            return PushChannel.JPUSH

        # Default to FCM for international users
        if is_firebase_available():
            return PushChannel.FCM

        # Fallback to available channel
        if is_jpush_available():
            return PushChannel.JPUSH

        return PushChannel.UNKNOWN

    def _get_fallback_channel(self, primary: PushChannel) -> PushChannel | None:
        """Get the fallback channel for a primary channel"""
        fallback_map = {
            PushChannel.JPUSH: PushChannel.FCM if is_firebase_available() else None,
            PushChannel.FCM: PushChannel.JPUSH if is_jpush_available() else None,
            PushChannel.APNS: None,  # APNs through FCM, no fallback
            PushChannel.UNKNOWN: None,
        }
        return fallback_map.get(primary)

    def _group_devices_by_channel(
        self,
        devices: list[DevicePushInfo],
        prefer_channel: PushChannel | None = None,
    ) -> dict[PushChannel, list[DevicePushInfo]]:
        """Group devices by their optimal push channel"""
        grouped: dict[PushChannel, list[DevicePushInfo]] = {}

        for device in devices:
            if prefer_channel:
                channel = prefer_channel
            else:
                channel = self._determine_channel(device)

            if channel not in grouped:
                grouped[channel] = []
            grouped[channel].append(device)

        # Sort channels by priority
        # CN users: JPush first, FCM second
        # INTL users: FCM first, JPush second
        sorted_channels = {}

        # Check if majority of devices are from CN
        cn_count = sum(1 for d in devices if d.region == "cn")
        if cn_count > len(devices) // 2:
            priority_order = [PushChannel.JPUSH, PushChannel.FCM]
        else:
            priority_order = [PushChannel.FCM, PushChannel.JPUSH]

        for channel in priority_order:
            if channel in grouped:
                sorted_channels[channel] = grouped[channel]

        # Add remaining channels
        for channel, device_list in grouped.items():
            if channel not in sorted_channels:
                sorted_channels[channel] = device_list

        return sorted_channels

    async def _send_via_channel(
        self,
        channel: PushChannel,
        devices: list[DevicePushInfo],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        deep_link: str | None = None,
        notification_type: str = "system",
        image: str | None = None,
    ) -> PushResult | None:
        """Send notification via a specific channel"""
        if channel == PushChannel.FCM:
            return await self._send_via_fcm(
                devices=devices,
                title=title,
                body=body,
                data=data,
                deep_link=deep_link,
                notification_type=notification_type,
                image=image,
            )
        elif channel == PushChannel.JPUSH:
            return await self._send_via_jpush(
                devices=devices,
                title=title,
                body=body,
                data=data,
                deep_link=deep_link,
                notification_type=notification_type,
                image=image,
            )
        else:
            logger.warning(f"Unsupported push channel: {channel}")
            return None

    async def _send_via_fcm(
        self,
        devices: list[DevicePushInfo],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        deep_link: str | None = None,
        notification_type: str = "system",
        image: str | None = None,
    ) -> PushResult | None:
        """Send notification via FCM"""
        if not is_firebase_available():
            logger.warning("FCM not available")
            return PushResult(success=False, error="FCM not available")

        # Filter devices with FCM/APNs tokens
        fcm_devices = [
            d for d in devices
            if d.token_type.lower() in ["fcm", "apns"]
        ]

        if not fcm_devices:
            return PushResult(success=False, error="No FCM devices")

        tokens = [d.push_token for d in fcm_devices]

        payload = PushPayload(
            title=title,
            body=body,
            data=data,
            deep_link=deep_link,
            notification_type=notification_type,
            image=image,
        )

        # Use multicast send
        return await self._fcm_service._send_fcm_multicast(
            user_id="routed",
            tokens=tokens,
            payload=payload,
        )

    async def _send_via_jpush(
        self,
        devices: list[DevicePushInfo],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        deep_link: str | None = None,
        notification_type: str = "system",
        image: str | None = None,
    ) -> PushResult | None:
        """Send notification via JPush"""
        if not is_jpush_available():
            logger.warning("JPush not available")
            return PushResult(success=False, error="JPush not available")

        # Filter devices with JPush tokens
        jpush_devices = [
            d for d in devices
            if d.token_type.lower() == "jpush"
        ]

        if not jpush_devices:
            return PushResult(success=False, error="No JPush devices")

        registration_ids = [d.push_token for d in jpush_devices]

        payload = JPushPayload(
            title=title,
            body=body,
            data=data,
            deep_link=deep_link,
            notification_type=notification_type,
            image=image,
        )

        # Send via JPush
        jpush_result = await self._jpush_service.send_to_registrations(
            registration_ids=registration_ids,
            payload=payload,
        )

        # Convert to PushResult
        return PushResult(
            success=jpush_result.success,
            success_count=jpush_result.success_count,
            failure_count=jpush_result.failure_count,
            error=jpush_result.error,
            invalid_tokens=jpush_result.invalid_registrations,
        )

    async def _get_user_devices(self, user_id: str) -> list[DevicePushInfo]:
        """Get all active devices for a user"""
        try:
            query = select(UserDevice).where(
                UserDevice.user_id == user_id,
                UserDevice.is_active == True,
            )
            result = await self.db.execute(query)
            devices = result.scalars().all()

            return [
                DevicePushInfo(
                    device_id=d.device_id,
                    push_token=d.push_token,
                    token_type=d.token_type,
                    platform=d.platform,
                    region=d.device_metadata.get("region") if d.device_metadata else None,
                    is_active=d.is_active,
                )
                for d in devices
            ]
        except Exception as e:
            logger.error(f"Failed to get user devices: {e}")
            return []

    def _infer_region_from_token(self, token: str) -> str | None:
        """
        Infer user region from token format.

        JPush registration IDs have a specific format.
        FCM tokens are typically longer.
        """
        if not token:
            return None

        # JPush registration IDs are typically 19-20 characters
        # and start with specific prefixes based on region
        if len(token) <= 25 and token.isalnum():
            # Likely a JPush token, assume CN
            return "cn"

        # FCM tokens are typically longer (140+ characters)
        if len(token) > 100:
            return "international"

        return None

    async def close(self):
        """Clean up resources"""
        await self._jpush_service.close()


# Factory function for dependency injection
def get_push_router_service(db: AsyncSession) -> PushRouterService:
    """Get PushRouterService instance"""
    return PushRouterService(db)
