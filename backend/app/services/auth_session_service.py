"""
Authentication session tracking service.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.auth_security import UserSession

SESSION_REVOKED_PREFIX = "session_revoked:"

# engine-restore-storm: 会话 touch 最小间隔。恢复风暴下同一 session 在 ~1s 内
# 并发拉取 20+ 端点；last_active_at 在该窗口内的重复 touch 直接跳过，
# 消除 user_sessions 行锁排队与写放大（会话活跃度精度 5s 足够）。
SESSION_TOUCH_MIN_INTERVAL = 5  # seconds

logger = logging.getLogger(__name__)


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

    async def touch_session(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
        refresh_token_jti: str | None = None,
        request: Request | None = None,
        metadata: dict[str, str | None] | None = None,
    ) -> None:
        """在途请求的会话元数据更新（touch）。

        仅更新 last_active_at / 设备元数据 / refresh jti：
        - 不复位 is_active / revoked_at（撤销状态只能由登录/刷新的 upsert 显式重置）
        - 不删除 Redis 撤销标记
        避免「登出其他设备」与目标设备在途请求并发时，已撤销会话被 touch 复活（A1）。
        """
        if metadata is None:
            metadata = extract_client_metadata(request)
        now = _utcnow_naive()

        # freshness-skip（engine-restore-storm）：窗口内已活跃的会话跳过重复 touch，
        # 避免同一 session 并发请求在 user_sessions 行锁上排队（写放大）。
        # 跳过路径不写库，不可能复活已撤销会话（A1 语义保持）。
        if not refresh_token_jti:
            recent = await db.execute(
                select(UserSession.last_active_at).where(UserSession.session_id == session_id)
            )
            row = recent.first()
            if (
                row is not None
                and row[0] is not None
                and now - row[0] < timedelta(seconds=SESSION_TOUCH_MIN_INTERVAL)
            ):
                return

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
        }
        if refresh_token_jti:
            update_fields["refresh_token_jti"] = refresh_token_jti

        await db.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=[UserSession.session_id],
                set_=update_fields,
            ),
        )
        await db.flush()

    async def touch_from_payload_detached(
        self,
        *,
        user_id: str,
        payload: dict[str, Any],
        request: Request | None = None,
    ) -> None:
        """独立短事务的会话 touch（engine-restore-storm 修复）。

        旧路径在请求事务里 upsert user_sessions，行锁要持有到请求结束才释放；
        会话恢复风暴下同一 session 的 ~20 个并发请求在该行锁上排队串行化，
        轻端点（user/settings、aurora、telemetry）全部超时。

        现改为独立 AsyncSession + 立即 commit（锁持有 ~ms），失败仅记日志、
        不影响请求。配合 touch_session 的 freshness-skip 消除写放大。
        注意：metadata 在调度前同步提取，不持有 Request 对象跨生命周期。
        """
        from app.db.session import AsyncSessionLocal

        session_id = payload.get("sid")
        if not session_id:
            return
        metadata = extract_client_metadata(request)
        refresh_token_jti = payload.get("jti") if payload.get("type") == "refresh" else None
        try:
            async with AsyncSessionLocal() as db:
                await self.touch_session(
                    db,
                    user_id=user_id,
                    session_id=str(session_id),
                    refresh_token_jti=refresh_token_jti,
                    metadata=metadata,
                )
                await db.commit()
        except Exception as exc:  # noqa: BLE001 — touch 是元数据卫生，绝不阻塞/弄挂请求
            logger.warning("detached session touch failed for user {}: {}", user_id, exc)

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
        await self.touch_session(
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
