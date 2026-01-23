"""
Capsule Favorite Service

处理胶囊收藏功能
"""
from typing import List, Optional
from uuid import UUID
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from app.models.capsule_favorite import CapsuleFavorite
from app.models.curiosity_capsule import CuriosityCapsule


class CapsuleFavoriteService:
    """
    胶囊收藏服务

    核心功能：
    - 添加收藏
    - 取消收藏
    - 获取收藏列表
    - 检查收藏状态
    """

    async def add_favorite(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        note: Optional[str] = None,
    ) -> CapsuleFavorite:
        """
        收藏胶囊

        Args:
            user_id: 用户ID
            capsule_id: 胶囊ID
            db: 数据库会话
            note: 收藏备注

        Returns:
            收藏对象
        """
        # 检查胶囊是否存在
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if not capsule:
            raise ValueError(f"Capsule {capsule_id} not found")

        if capsule.user_id != user_id:
            raise ValueError("User can only favorite their own capsules")

        # 检查是否已收藏
        existing = await db.execute(
            select(CapsuleFavorite).where(
                CapsuleFavorite.user_id == user_id,
                CapsuleFavorite.capsule_id == capsule_id,
            )
        )
        existing_favorite = existing.scalar_one_or_none()

        if existing_favorite:
            # 更新备注
            if note is not None:
                existing_favorite.note = note
            await db.commit()
            await db.refresh(existing_favorite)
            return existing_favorite

        # 创建新收藏
        favorite = CapsuleFavorite(
            user_id=user_id,
            capsule_id=capsule_id,
            note=note,
        )
        db.add(favorite)

        # 更新胶囊分享计数（用于统计受欢迎程度）
        capsule.share_count += 1

        await db.commit()
        await db.refresh(favorite)

        logger.info(f"[Favorite] User {user_id} favorited capsule {capsule_id}")
        return favorite

    async def remove_favorite(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        取消收藏

        Returns:
            是否成功取消
        """
        # 查找收藏记录
        result = await db.execute(
            select(CapsuleFavorite).where(
                CapsuleFavorite.user_id == user_id,
                CapsuleFavorite.capsule_id == capsule_id,
            )
        )
        favorite = result.scalar_one_or_none()

        if not favorite:
            return False

        # 删除收藏
        await db.delete(favorite)

        # 更新胶囊计数
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if capsule and capsule.share_count > 0:
            capsule.share_count -= 1

        await db.commit()

        logger.info(f"[Favorite] User {user_id} unfavorited capsule {capsule_id}")
        return True

    async def get_user_favorites(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """
        获取用户的收藏列表

        Returns:
            [
                {
                    "id": str,
                    "capsule_id": str,
                    "note": str,
                    "created_at": datetime,
                    "capsule": CuriosityCapsule,
                }
            ]
        """
        result = await db.execute(
            select(CapsuleFavorite)
            .where(CapsuleFavorite.user_id == user_id)
            .order_by(desc(CapsuleFavorite.created_at))
            .limit(limit)
            .offset(offset)
        )
        favorites = result.scalars().all()

        # 加载关联的胶囊
        result = [
            {
                "id": str(f.id),
                "capsule_id": str(f.capsule_id),
                "note": f.note,
                "created_at": f.created_at,
                "capsule": await db.get(CuriosityCapsule, f.capsule_id),
            }
            for f in favorites
        ]

        return result

    async def is_favorited(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        检查胶囊是否已收藏

        Returns:
            是否已收藏
        """
        result = await db.execute(
            select(CapsuleFavorite).where(
                CapsuleFavorite.user_id == user_id,
                CapsuleFavorite.capsule_id == capsule_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def toggle_favorite(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        note: Optional[str] = None,
    ) -> dict:
        """
        切换收藏状态

        Returns:
            {
                "is_favorited": bool,
                "favorite": Optional[CapsuleFavorite],
            }
        """
        is_fav = await self.is_favorited(user_id, capsule_id, db)

        if is_fav:
            await self.remove_favorite(user_id, capsule_id, db)
            return {"is_favorited": False, "favorite": None}
        else:
            favorite = await self.add_favorite(user_id, capsule_id, db, note)
            return {"is_favorited": True, "favorite": favorite}


# 全局单例
capsule_favorite_service = CapsuleFavoriteService()
