from __future__ import annotations
"""
Push Sender Service

Handles sending push notifications via Firebase Cloud Messaging (FCM).
Supports both FCM (Android) and APNs (iOS through FCM).

Features:
- Multi-device support (sends to all user's devices)
- Token cleanup for invalid/expired tokens
- Platform-specific configurations (Android/iOS)
- Deep link support for notification actions
"""
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase_config import get_firebase_app, initialize_firebase, is_firebase_available
from app.models.user import UserDevice


@dataclass
class PushResult:
    """Result of a push notification send operation"""

    success: bool
    success_count: int = 0
    failure_count: int = 0
    error: str | None = None
    invalid_tokens: list[str] | None = None


@dataclass
class PushPayload:
    """Push notification payload"""

    title: str
    body: str
    data: dict[str, Any] | None = None
    image: str | None = None
    deep_link: str | None = None
    notification_type: str = "system"


class PushSenderService:
    """
    Push notification sender using Firebase Cloud Messaging.

    Usage:
        async with AsyncSessionLocal() as db:
            service = PushSenderService(db)
            result = await service.send_to_user(
                user_id=user_id,
                title="New message",
                body="You have a new message",
                data={"type": "chat", "chat_id": "123"}
            )
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._initialized = False

    async def _ensure_initialized(self) -> bool:
        """Ensure Firebase is initialized"""
        if self._initialized:
            return is_firebase_available()

        self._initialized = True
        return initialize_firebase()

    async def send_to_user(
        self,
        user_id: UUID | str,
        payload: PushPayload | None = None,
        title: str | None = None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> PushResult:
        """
        Send push notification to all devices of a user.

        Args:
            user_id: Target user ID
            payload: PushPayload object (alternative to title/body)
            title: Notification title
            body: Notification body
            data: Additional data payload
            **kwargs: Additional arguments for PushPayload

        Returns:
            PushResult with success/failure details
        """
        # Ensure Firebase is available
        if not await self._ensure_initialized():
            return PushResult(
                success=False,
                error="Firebase not configured or unavailable",
            )

        # Build payload
        if payload is None:
            payload = PushPayload(
                title=title or "",
                body=body or "",
                data=data,
                **kwargs,
            )

        # Get user's device tokens
        tokens = await self._get_user_tokens(str(user_id))
        if not tokens:
            logger.debug(f"No device tokens found for user {user_id}")
            return PushResult(success=False, error="No device tokens")

        # Send via FCM
        return await self._send_fcm_multicast(str(user_id), tokens, payload)

    async def send_to_token(
        self,
        token: str,
        payload: PushPayload | None = None,
        title: str | None = None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> PushResult:
        """
        Send push notification to a specific device token.

        Args:
            token: Device FCM token
            payload: PushPayload object
            title: Notification title
            body: Notification body
            data: Additional data payload
            **kwargs: Additional arguments

        Returns:
            PushResult with success/failure details
        """
        if not await self._ensure_initialized():
            return PushResult(
                success=False,
                error="Firebase not configured or unavailable",
            )

        if payload is None:
            payload = PushPayload(
                title=title or "",
                body=body or "",
                data=data,
                **kwargs,
            )

        return await self._send_fcm_single(token, payload)

    async def _send_fcm_multicast(
        self,
        user_id: str,
        tokens: list[str],
        payload: PushPayload,
    ) -> PushResult:
        """Send FCM message to multiple tokens"""
        try:
            from firebase_admin import messaging

            app = get_firebase_app()
            if not app:
                return PushResult(success=False, error="Firebase app not available")

            # Build the message
            notification = messaging.Notification(
                title=payload.title,
                body=payload.body,
                image=payload.image,
            )

            # Prepare data payload (must be strings)
            data_payload = self._prepare_data_payload(payload)

            # Build Android config
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    title=payload.title,
                    body=payload.body,
                    image=payload.image,
                    channel_id="sparkle_smart_push",
                    priority="high",
                    click_action=payload.deep_link,
                ),
                priority="high",
                data=data_payload,
            )

            # Build APNs config
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=payload.title,
                            body=payload.body,
                        ),
                        sound="default",
                        badge=1,
                        mutable_content=1,
                    ),
                ),
            )

            # Create multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                data=data_payload,
                tokens=tokens,
                android=android_config,
                apns=apns_config,
            )

            # Send
            response = messaging.send_each_for_multicast(message, app=app)

            logger.info(
                f"FCM multicast sent to user {user_id}: "
                f"{response.success_count} success, {response.failure_count} failed"
            )

            # Collect invalid tokens
            invalid_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        error_code = resp.exception.code if resp.exception else "UNKNOWN"
                        # Check for invalid token errors
                        if error_code in [
                            "UNREGISTERED",
                            "INVALID_ARGUMENT",
                            "NOT_FOUND",
                        ]:
                            invalid_tokens.append(tokens[idx])
                            logger.warning(
                                f"Invalid token detected: {tokens[idx][:20]}... "
                                f"Error: {error_code}"
                            )

            # Clean up invalid tokens
            if invalid_tokens:
                await self._cleanup_invalid_tokens(invalid_tokens)

            return PushResult(
                success=response.success_count > 0,
                success_count=response.success_count,
                failure_count=response.failure_count,
                invalid_tokens=invalid_tokens,
            )

        except Exception as e:
            logger.error(f"Failed to send FCM multicast: {e}")
            return PushResult(success=False, error=str(e))

    async def _send_fcm_single(self, token: str, payload: PushPayload) -> PushResult:
        """Send FCM message to a single token"""
        try:
            from firebase_admin import messaging

            app = get_firebase_app()
            if not app:
                return PushResult(success=False, error="Firebase app not available")

            # Prepare data payload
            data_payload = self._prepare_data_payload(payload)

            # Build the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=payload.title,
                    body=payload.body,
                    image=payload.image,
                ),
                data=data_payload,
                token=token,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        title=payload.title,
                        body=payload.body,
                        image=payload.image,
                        channel_id="sparkle_smart_push",
                        priority="high",
                        click_action=payload.deep_link,
                    ),
                    priority="high",
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=payload.title,
                                body=payload.body,
                            ),
                            sound="default",
                            badge=1,
                            mutable_content=1,
                        ),
                    ),
                ),
            )

            # Send
            message_id = messaging.send(message, app=app)
            logger.debug(f"FCM message sent: {message_id}")

            return PushResult(success=True, success_count=1)

        except messaging.UnregisteredError:
            logger.warning(f"Token unregistered: {token[:20]}...")
            await self._cleanup_invalid_tokens([token])
            return PushResult(success=False, error="Token unregistered", invalid_tokens=[token])
        except Exception as e:
            logger.error(f"Failed to send FCM message: {e}")
            return PushResult(success=False, error=str(e))

    def _prepare_data_payload(self, payload: PushPayload) -> dict[str, str]:
        """Prepare data payload (all values must be strings for FCM)"""
        data = {}

        if payload.data:
            for key, value in payload.data.items():
                if value is not None:
                    data[key] = str(value)

        # Add deep link if provided
        if payload.deep_link:
            data["deep_link"] = payload.deep_link

        # Add notification type
        data["notification_type"] = payload.notification_type

        # Add timestamp
        data["sent_at"] = datetime.now(timezone.utc).isoformat()

        return data

    async def _get_user_tokens(self, user_id: str) -> list[str]:
        """Get all active device tokens for a user"""
        try:
            query = select(UserDevice.push_token).where(
                UserDevice.user_id == user_id,
                UserDevice.is_active == True,
            )
            result = await self.db.execute(query)
            tokens = [row[0] for row in result.all()]
            return tokens
        except Exception as e:
            logger.error(f"Failed to get user tokens: {e}")
            return []

    async def _cleanup_invalid_tokens(self, tokens: list[str]) -> None:
        """Mark invalid tokens as inactive"""
        if not tokens:
            return

        try:
            stmt = (
                update(UserDevice)
                .where(UserDevice.push_token.in_(tokens))
                .values(is_active=False)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Marked {len(tokens)} invalid tokens as inactive")
        except Exception as e:
            logger.error(f"Failed to cleanup invalid tokens: {e}")
            await self.db.rollback()

    async def register_device_token(
        self,
        user_id: UUID | str,
        device_id: str,
        push_token: str,
        platform: str,
        token_type: str = "fcm",
        device_name: str | None = None,
        app_version: str | None = None,
        os_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserDevice:
        """
        Register or update a device token for push notifications.

        Args:
            user_id: User ID
            device_id: Unique device identifier
            push_token: FCM/APNs push token
            platform: Platform (ios, android, web)
            token_type: Token type (fcm, apns)
            device_name: Device name
            app_version: App version
            os_version: OS version
            metadata: Additional metadata

        Returns:
            UserDevice instance
        """
        user_id_str = str(user_id)

        # Check if device already exists
        query = select(UserDevice).where(
            UserDevice.user_id == user_id_str,
            UserDevice.device_id == device_id,
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing device
            existing.push_token = push_token
            existing.token_type = token_type
            existing.is_active = True
            existing.last_used_at = datetime.now(timezone.utc)
            if device_name:
                existing.device_name = device_name
            if app_version:
                existing.app_version = app_version
            if os_version:
                existing.os_version = os_version
            if metadata:
                existing.device_metadata = metadata

            await self.db.commit()
            await self.db.refresh(existing)
            logger.info(f"Updated device token for user {user_id}, device {device_id}")
            return existing
        else:
            # Create new device
            device = UserDevice(
                user_id=user_id_str,
                device_id=device_id,
                push_token=push_token,
                platform=platform,
                token_type=token_type,
                device_name=device_name,
                app_version=app_version,
                os_version=os_version,
                device_metadata=metadata,
                is_active=True,
                last_used_at=datetime.now(timezone.utc),
            )
            self.db.add(device)
            await self.db.commit()
            await self.db.refresh(device)
            logger.info(f"Registered new device for user {user_id}, device {device_id}")
            return device

    async def unregister_device_token(
        self,
        user_id: UUID | str,
        device_id: str,
    ) -> bool:
        """
        Unregister a device token (mark as inactive).

        Args:
            user_id: User ID
            device_id: Device identifier

        Returns:
            True if device was found and deactivated
        """
        user_id_str = str(user_id)

        stmt = (
            update(UserDevice)
            .where(
                UserDevice.user_id == user_id_str,
                UserDevice.device_id == device_id,
            )
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Unregistered device {device_id} for user {user_id}")
            return True
        return False

    async def get_user_devices(
        self,
        user_id: UUID | str,
        active_only: bool = True,
    ) -> list[UserDevice]:
        """
        Get all devices for a user.

        Args:
            user_id: User ID
            active_only: Only return active devices

        Returns:
            List of UserDevice objects
        """
        user_id_str = str(user_id)

        query = select(UserDevice).where(UserDevice.user_id == user_id_str)

        if active_only:
            query = query.where(UserDevice.is_active == True)

        query = query.order_by(UserDevice.last_used_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())


# Factory function for dependency injection
def get_push_sender_service(db: AsyncSession) -> PushSenderService:
    """Get PushSenderService instance"""
    return PushSenderService(db)
