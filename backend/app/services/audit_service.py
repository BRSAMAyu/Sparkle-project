from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, AvatarStatus
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate

class AuditService:
    @staticmethod
    async def get_pending_avatars(db: AsyncSession) -> List[User]:
        """获取所有待审核头像的用户列表"""
        stmt = select(User).where(User.avatar_status == AvatarStatus.PENDING)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def approve_avatar(db: AsyncSession, user_id: UUID) -> Optional[User]:
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
                title="头像审核通过",
                content="您的新头像已经审核通过，现在大家都可以看到啦！",
                type="system",
                data={"status": "approved"}
            )
        )
        
        return user

    @staticmethod
    async def reject_avatar(db: AsyncSession, user_id: UUID, reason: str = "头像内容不符合规范") -> Optional[User]:
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
                title="头像审核未通过",
                content=f"很抱歉，您的头像审核未通过。原因：{reason}",
                type="system",
                data={"status": "rejected", "reason": reason}
            )
        )
        
        return user
