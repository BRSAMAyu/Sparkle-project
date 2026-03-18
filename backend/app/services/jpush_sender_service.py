from __future__ import annotations
"""
JPush Sender Service

Handles sending push notifications via JPush (极光推送) REST API v3.
Provides an alternative push channel for Chinese domestic users where
Google services (FCM) are not available.

JPush REST API v3 Documentation: https://docs.jiguang.cn/jpush/server/push/rest_api_v3_push

Features:
- Support for Android and iOS platforms
- Token cleanup for invalid registrations
- Platform-specific configurations
- Deep link support
"""
import asyncio
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any, Literal
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jpush_config import get_jpush_settings, initialize_jpush, is_jpush_available
from app.models.user import UserDevice


@dataclass
class JPushResult:
    """Result of a JPush notification send operation"""

    success: bool
    msg_id: str | None = None
    success_count: int = 0
    failure_count: int = 0
    error: str | None = None
    invalid_registrations: list[str] | None = None


@dataclass
class JPushPayload:
    """JPush notification payload"""

    title: str
    body: str
    data: dict[str, Any] | None = None
    image: str | None = None
    deep_link: str | None = None
    notification_type: str = "system"
    # iOS specific
    badge: int | None = None
    sound: str = "default"
    # Android specific
    channel_id: str = "sparkle_smart_push"
    priority: int = 1  # 0-2, higher is more important


class JPushSenderService:
    """
    Push notification sender using JPush REST API v3.

    Usage:
        async with AsyncSessionLocal() as db:
            service = JPushSenderService(db)
            result = await service.send_to_registration(
                registration_id="registration_id",
                title="New message",
                body="You have a new message",
                data={"type": "chat", "chat_id": "123"}
            )
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._initialized = False
        self._settings = None
        self._client: httpx.AsyncClient | None = None

    async def _ensure_initialized(self) -> bool:
        """Ensure JPush is initialized and HTTP client is ready"""
        if self._initialized:
            return is_jpush_available()

        self._initialized = True

        if not initialize_jpush():
            return False

        self._settings = get_jpush_settings()

        # Create HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        return True

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_to_registration(
        self,
        registration_id: str,
        payload: JPushPayload | None = None,
        title: str | None = None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> JPushResult:
        """
        Send push notification to a specific JPush registration ID.

        Args:
            registration_id: JPush registration ID
            payload: JPushPayload object
            title: Notification title
            body: Notification body
            data: Additional data payload
            **kwargs: Additional arguments

        Returns:
            JPushResult with success/failure details
        """
        if not await self._ensure_initialized():
            return JPushResult(
                success=False,
                error="JPush not configured or unavailable",
            )

        if payload is None:
            payload = JPushPayload(
                title=title or "",
                body=body or "",
                data=data,
                **kwargs,
            )

        return await self._send_push(
            registration_ids=[registration_id],
            payload=payload,
        )

    async def send_to_registrations(
        self,
        registration_ids: list[str],
        payload: JPushPayload | None = None,
        title: str | None = None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> JPushResult:
        """
        Send push notification to multiple JPush registration IDs.

        Args:
            registration_ids: List of JPush registration IDs (max 1000)
            payload: JPushPayload object
            title: Notification title
            body: Notification body
            data: Additional data payload
            **kwargs: Additional arguments

        Returns:
            JPushResult with success/failure details
        """
        if not await self._ensure_initialized():
            return JPushResult(
                success=False,
                error="JPush not configured or unavailable",
            )

        if payload is None:
            payload = JPushPayload(
                title=title or "",
                body=body or "",
                data=data,
                **kwargs,
            )

        # JPush limits to 1000 registrations per request
        if len(registration_ids) > 1000:
            logger.warning(
                f"JPush registration list exceeds 1000, truncating. "
                f"Got {len(registration_ids)}"
            )
            registration_ids = registration_ids[:1000]

        return await self._send_push(
            registration_ids=registration_ids,
            payload=payload,
        )

    async def send_to_alias(
        self,
        alias: str,
        payload: JPushPayload | None = None,
        title: str | None = None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> JPushResult:
        """
        Send push notification to an alias (typically user ID).

        Args:
            alias: User alias
            payload: JPushPayload object
            title: Notification title
            body: Notification body
            data: Additional data payload
            **kwargs: Additional arguments

        Returns:
            JPushResult with success/failure details
        """
        if not await self._ensure_initialized():
            return JPushResult(
                success=False,
                error="JPush not configured or unavailable",
            )

        if payload is None:
            payload = JPushPayload(
                title=title or "",
                body=body or "",
                data=data,
                **kwargs,
            )

        return await self._send_push(
            alias=alias,
            payload=payload,
        )

    async def _send_push(
        self,
        payload: JPushPayload,
        registration_ids: list[str] | None = None,
        alias: str | None = None,
    ) -> JPushResult:
        """
        Send push notification via JPush REST API.

        Args:
            payload: JPushPayload object
            registration_ids: List of registration IDs
            alias: User alias

        Returns:
            JPushResult with details
        """
        if not self._client or not self._settings:
            return JPushResult(success=False, error="JPush not initialized")

        # Build JPush API request body
        request_body = self._build_request_body(
            payload=payload,
            registration_ids=registration_ids,
            alias=alias,
        )

        # Get auth header
        auth_string = self._settings.get_auth_string()
        if not auth_string:
            return JPushResult(success=False, error="JPush credentials not configured")

        try:
            # Send request
            api_url = f"{self._settings.get_api_url()}/push"
            response = await self._client.post(
                api_url,
                json=request_body,
                headers={"Authorization": f"Basic {auth_string}"},
            )

            # Parse response
            response_data = response.json()

            if response.status_code == 200:
                msg_id = response_data.get("msg_id", "")
                sendno = response_data.get("sendno", "")

                logger.info(
                    f"JPush sent successfully. msg_id: {msg_id}, sendno: {sendno}"
                )

                return JPushResult(
                    success=True,
                    msg_id=str(msg_id),
                    success_count=1,  # JPush doesn't return detailed counts in push response
                )
            else:
                error_code = response_data.get("error", {}).get("code", "UNKNOWN")
                error_msg = response_data.get("error", {}).get("message", "Unknown error")

                logger.error(
                    f"JPush failed. Status: {response.status_code}, "
                    f"Error: {error_code} - {error_msg}"
                )

                # Check for invalid registration errors
                invalid_registrations = []
                if error_code in [1011, 1012, 1013, 1014]:  # Invalid registration errors
                    if registration_ids:
                        invalid_registrations = registration_ids
                    elif alias:
                        # Need to look up registration ID for this alias
                        pass

                return JPushResult(
                    success=False,
                    error=f"{error_code}: {error_msg}",
                    invalid_registrations=invalid_registrations,
                )

        except httpx.TimeoutException:
            logger.error("JPush request timed out")
            return JPushResult(success=False, error="Request timed out")
        except httpx.RequestError as e:
            logger.error(f"JPush request error: {e}")
            return JPushResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Failed to send JPush notification: {e}")
            return JPushResult(success=False, error=str(e))

    def _build_request_body(
        self,
        payload: JPushPayload,
        registration_ids: list[str] | None = None,
        alias: str | None = None,
    ) -> dict[str, Any]:
        """
        Build JPush REST API v3 request body.

        Documentation: https://docs.jiguang.cn/jpush/server/push/rest_api_v3_push
        """
        body: dict[str, Any] = {
            "platform": "all",  # Send to both Android and iOS
            "audience": {},
            "notification": self._build_notification(payload),
            "options": {
                "time_to_live": 86400,  # 24 hours
                "apns_production": True,  # Use APNs production environment
            },
        }

        # Set audience
        if registration_ids:
            body["audience"]["registration_id"] = registration_ids
        elif alias:
            body["audience"]["alias"] = [alias]
        else:
            # Broadcast to all (use with caution)
            body["audience"] = "all"

        # Add message (custom data)
        if payload.data:
            body["message"] = {
                "msg_content": payload.body,
                "title": payload.title,
                "extras": self._prepare_extras(payload),
            }

        return body

    def _build_notification(self, payload: JPushPayload) -> dict[str, Any]:
        """Build notification object for JPush"""
        notification: dict[str, Any] = {
            "alert": payload.body,  # Default alert
        }

        # Android notification
        notification["android"] = {
            "alert": payload.body,
            "title": payload.title,
            "builder_id": 1,
            "channel_id": payload.channel_id,
            "priority": payload.priority,
            "extras": self._prepare_extras(payload),
        }

        # Add large icon or big picture if image provided
        if payload.image:
            notification["android"]["large_icon"] = payload.image
            notification["android"]["big_pic_path"] = payload.image

        # Add deep link / intent
        if payload.deep_link:
            notification["android"]["intent"] = {
                "url": payload.deep_link,
            }

        # iOS notification
        notification["ios"] = {
            "alert": {
                "title": payload.title,
                "body": payload.body,
            },
            "sound": payload.sound,
            "badge": payload.badge if payload.badge is not None else "+1",
            "extras": self._prepare_extras(payload),
        }

        # Add mutable-content for rich notifications
        if payload.image:
            notification["ios"]["mutable-content"] = True

        return notification

    def _prepare_extras(self, payload: JPushPayload) -> dict[str, Any]:
        """Prepare extras (custom data) for JPush notification"""
        extras: dict[str, Any] = {}

        if payload.data:
            for key, value in payload.data.items():
                if value is not None:
                    extras[key] = value

        # Add deep link if provided
        if payload.deep_link:
            extras["deep_link"] = payload.deep_link

        # Add notification type
        extras["notification_type"] = payload.notification_type

        # Add timestamp
        extras["sent_at"] = datetime.now(timezone.utc).isoformat()

        return extras

    async def _cleanup_invalid_registrations(
        self, registration_ids: list[str]
    ) -> None:
        """Mark invalid registration IDs as inactive"""
        if not registration_ids:
            return

        try:
            stmt = (
                update(UserDevice)
                .where(UserDevice.push_token.in_(registration_ids))
                .values(is_active=False)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(
                f"Marked {len(registration_ids)} invalid JPush registrations as inactive"
            )
        except Exception as e:
            logger.error(f"Failed to cleanup invalid registrations: {e}")
            await self.db.rollback()

    async def check_device_status(
        self, registration_id: str
    ) -> Literal["valid", "invalid", "unknown"]:
        """
        Check if a JPush registration ID is still valid.

        Uses JPush's device API to check registration status.

        Args:
            registration_id: JPush registration ID

        Returns:
            "valid", "invalid", or "unknown"
        """
        if not await self._ensure_initialized():
            return "unknown"

        if not self._client or not self._settings:
            return "unknown"

        auth_string = self._settings.get_auth_string()
        if not auth_string:
            return "unknown"

        try:
            api_url = f"{self._settings.get_api_url()}/devices/{registration_id}"
            response = await self._client.get(
                api_url,
                headers={"Authorization": f"Basic {auth_string}"},
            )

            if response.status_code == 200:
                data = response.json()
                # Check if device is active
                tags = data.get("tags", [])
                return "valid"
            elif response.status_code == 404:
                return "invalid"
            else:
                return "unknown"

        except Exception as e:
            logger.error(f"Failed to check device status: {e}")
            return "unknown"


# Factory function for dependency injection
def get_jpush_sender_service(db: AsyncSession) -> JPushSenderService:
    """Get JPushSenderService instance"""
    return JPushSenderService(db)
