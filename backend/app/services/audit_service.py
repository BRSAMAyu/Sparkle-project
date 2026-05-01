from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import I18n
from app.models.user import AvatarStatus, User
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService


class AuditService:
    @staticmethod
    async def get_pending_avatars(db: AsyncSession) -> list[User]:
        """获取所有待审核头像的用户列表"""
        stmt = select(User).where(User.avatar_status == AvatarStatus.PENDING)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def approve_avatar(db: AsyncSession, user_id: UUID) -> User | None:
        """审核通过头像"""
        user = await db.get(User, user_id)
        if not user or user.avatar_status != AvatarStatus.PENDING:
            return None

        # 将待审核头像正式应用
        user.avatar_url = user.pending_avatar_url
        user.pending_avatar_url = None
        user.avatar_status = AvatarStatus.APPROVED

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 发送通知
        await NotificationService.create(
            db,
            user_id,
            NotificationCreate(
                title=I18n.t("audit.avatar_approved_title", locale="zh"),
                content=I18n.t("audit.avatar_approved_content", locale="zh"),
                type="system",
                data={"status": "approved"}
            )
        )

        return user

    @staticmethod
    async def reject_avatar(db: AsyncSession, user_id: UUID, reason: str | None = None) -> User | None:
        """审核驳回头像"""
        user = await db.get(User, user_id)
        if not user or user.avatar_status != AvatarStatus.PENDING:
            return None

        # 清理待审核信息
        user.pending_avatar_url = None
        user.avatar_status = AvatarStatus.REJECTED

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 发送通知
        await NotificationService.create(
            db,
            user_id,
            NotificationCreate(
                title=I18n.t("audit.avatar_rejected_title", locale="zh"),
                content=I18n.t("audit.avatar_rejected_content", locale="zh", reason=reason or I18n.t("audit.avatar_rejected_default_reason", locale="zh")),
                type="system",
                data={"status": "rejected", "reason": reason}
            )
        )

        return user
