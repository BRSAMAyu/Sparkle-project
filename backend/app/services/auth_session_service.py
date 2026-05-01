"""
Authentication session tracking service.
"""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.auth_security import UserSession

SESSION_REVOKED_PREFIX = "session_revoked:"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def extract_client_metadata(request: Request | None) -> dict[str, str | None]:
    if request is None:
        return {
            "device_id": None,
            "device_name": None,
            "device_type": None,
            "ip_address": None,
            "user_agent": None,
        }
    return {
        "device_id": request.headers.get("x-device-id"),
        "device_name": request.headers.get("x-device-name"),
        "device_type": request.headers.get("x-device-platform"),
        "ip_address": _client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }


class AuthSessionService:
    async def upsert_session(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
        refresh_token_jti: str | None = None,
        request: Request | None = None,
    ) -> UserSession:
        metadata = extract_client_metadata(request)
        now = _utcnow_naive()

        insert_stmt = pg_insert(UserSession).values(
            user_id=user_id,
            session_id=session_id,
            device_id=metadata["device_id"],
            device_name=metadata["device_name"],
            device_type=metadata["device_type"],
            ip_address=metadata["ip_address"],
            user_agent=metadata["user_agent"],
            refresh_token_jti=refresh_token_jti,
            is_active=True,
            revoked_at=None,
            last_active_at=now,
        )
        update_fields: dict[str, Any] = {
            "user_id": user_id,
            "device_id": metadata["device_id"],
            "device_name": metadata["device_name"],
            "device_type": metadata["device_type"],
            "ip_address": metadata["ip_address"],
            "user_agent": metadata["user_agent"],
            "last_active_at": now,
            "is_active": True,
            "revoked_at": None,
        }
        if refresh_token_jti:
            update_fields["refresh_token_jti"] = refresh_token_jti

        await db.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=[UserSession.session_id],
                set_=update_fields,
            ),
        )

        await cache_service.delete(f"{SESSION_REVOKED_PREFIX}{session_id}")
        await db.flush()
        result = await db.execute(select(UserSession).where(UserSession.session_id == session_id))
        session = result.scalar_one()
        return session

    async def touch_from_payload(
        self,
        db: AsyncSession,
        *,
        request: Request,
        user_id: str,
        payload: dict[str, Any],
    ) -> None:
        session_id = payload.get("sid")
        if not session_id:
            return
        await self.upsert_session(
            db,
            user_id=user_id,
            session_id=str(session_id),
            refresh_token_jti=payload.get("jti") if payload.get("type") == "refresh" else None,
            request=request,
        )

    async def list_sessions(self, db: AsyncSession, user_id: str) -> list[UserSession]:
        result = await db.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.last_active_at.desc(), UserSession.created_at.desc()),
        )
        return list(result.scalars().all())

    async def revoke_session(self, db: AsyncSession, session: UserSession, ttl_seconds: int) -> None:
        session.is_active = False
        session.revoked_at = _utcnow_naive()
        await cache_service.set(f"{SESSION_REVOKED_PREFIX}{session.session_id}", "1", ttl=ttl_seconds)
        await db.flush()

    async def revoke_session_by_id(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
        ttl_seconds: int,
    ) -> UserSession | None:
        result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.session_id == session_id),
        )
        session = result.scalar_one_or_none()
        if session is None:
            return None
        await self.revoke_session(db, session, ttl_seconds=ttl_seconds)
        return session

    async def revoke_all_other_sessions(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        current_session_id: str | None,
        ttl_seconds: int,
    ) -> int:
        result = await db.execute(select(UserSession).where(UserSession.user_id == user_id, UserSession.is_active.is_(True)))
        sessions = list(result.scalars().all())
        revoked = 0
        for session in sessions:
            if current_session_id and session.session_id == current_session_id:
                continue
            await self.revoke_session(db, session, ttl_seconds=ttl_seconds)
            revoked += 1
        return revoked

    async def revoke_all_sessions_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        ttl_seconds: int,
    ) -> int:
        result = await db.execute(select(UserSession).where(UserSession.user_id == user_id, UserSession.is_active.is_(True)))
        sessions = list(result.scalars().all())
        for session in sessions:
            await self.revoke_session(db, session, ttl_seconds=ttl_seconds)
        return len(sessions)

    async def is_session_revoked(self, session_id: str) -> bool:
        if not session_id:
            return False
        cached = await cache_service.get(f"{SESSION_REVOKED_PREFIX}{session_id}")
        return cached is not None


auth_session_service = AuthSessionService()
