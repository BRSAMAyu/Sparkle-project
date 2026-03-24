"""
Authentication audit service.
"""
from __future__ import annotations

import asyncio
from datetime import timezone, datetime, timedelta
from typing import Any

from fastapi import Request
from loguru import logger
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.auth_security import AuthAuditAction, AuthAuditLog


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class AuthAuditService:
    """Writes auth audit events using an isolated DB session."""

    async def log_event(
        self,
        action: str | AuthAuditAction,
        user_id: str | None = None,
        request: Request | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            async with AsyncSessionLocal() as db:
                entry = AuthAuditLog(
                    user_id=user_id,
                    action=str(action),
                    ip_address=_client_ip(request),
                    user_agent=request.headers.get("user-agent") if request else None,
                    metadata=metadata or {},
                    occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                db.add(entry)
                await db.commit()
        except Exception as exc:
            logger.warning(f"Auth audit log write failed: {exc}")

    def schedule_log(
        self,
        action: str | AuthAuditAction,
        user_id: str | None = None,
        request: Request | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            asyncio.create_task(
                self.log_event(action=action, user_id=user_id, request=request, metadata=metadata),
            )
        except Exception as exc:
            logger.warning(f"Failed to schedule auth audit log: {exc}")

    async def get_recent_events(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100,
    ) -> list[AuthAuditLog]:
        async with AsyncSessionLocal() as db:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            result = await db.execute(
                select(AuthAuditLog)
                .where(AuthAuditLog.user_id == user_id, AuthAuditLog.occurred_at >= since)
                .order_by(AuthAuditLog.occurred_at.desc())
                .limit(limit),
            )
            return list(result.scalars().all())


auth_audit_service = AuthAuditService()
