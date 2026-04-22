"""
Capsule Favorite Service

处理胶囊收藏功能
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.core.event_types import CAPSULE_FAVORITE_UPDATED
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
        note: str | None = None,
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
            await self._publish_favorite_event(
                user_id=user_id,
                capsule_id=capsule_id,
                action="updated",
            )
            return existing_favorite

        # 创建新收藏
        favorite = CapsuleFavorite(
            user_id=user_id,
            capsule_id=capsule_id,
            note=note,
        )
        db.add(favorite)

        await db.commit()
        await db.refresh(favorite)
        await self._publish_favorite_event(
            user_id=user_id,
            capsule_id=capsule_id,
            action="favorited",
        )

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

        await db.commit()
        await self._publish_favorite_event(
            user_id=user_id,
            capsule_id=capsule_id,
            action="unfavorited",
        )

        logger.info(f"[Favorite] User {user_id} unfavorited capsule {capsule_id}")
        return True

    async def get_user_favorites(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
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

    async def get_preferences(
        self,
        user_id: UUID,
        db: AsyncSession,
        *,
        limit: int = 50,
    ) -> dict[str, object]:
        result = await db.execute(
            select(CapsuleFavorite, CuriosityCapsule)
            .join(CuriosityCapsule, CuriosityCapsule.id == CapsuleFavorite.capsule_id)
            .where(
                CapsuleFavorite.user_id == user_id,
                CuriosityCapsule.deleted_at.is_(None),
                CuriosityCapsule.user_id == user_id,
            )
            .order_by(desc(CapsuleFavorite.created_at))
            .limit(limit)
        )
        rows = list(result.all())
        if not rows:
            return {
                "favorite_count": 0,
                "content_depth_preference": None,
                "subject_affinity": [],
                "recent_notes": [],
            }

        depth_counts: dict[str, int] = {}
        subject_counts: dict[str, int] = {}
        recent_notes: list[str] = []
        for favorite, capsule in rows:
            depth = str(getattr(capsule.depth_level, "value", capsule.depth_level) or "").strip()
            if depth:
                depth_counts[depth] = depth_counts.get(depth, 0) + 1
            subject = str(capsule.related_subject or "").strip()
            if subject:
                subject_counts[subject] = subject_counts.get(subject, 0) + 1
            note = str(favorite.note or "").strip()
            if note and note not in recent_notes:
                recent_notes.append(note)

        content_depth_preference = None
        if depth_counts:
            content_depth_preference = sorted(
                depth_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]

        subject_affinity = [
            subject
            for subject, _count in sorted(
                subject_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        return {
            "favorite_count": len(rows),
            "content_depth_preference": content_depth_preference,
            "subject_affinity": subject_affinity,
            "recent_notes": recent_notes[:3],
        }

    async def toggle_favorite(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        note: str | None = None,
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

    async def _publish_favorite_event(
        self,
        *,
        user_id: UUID,
        capsule_id: UUID,
        action: str,
    ) -> None:
        await event_bus.publish(
            CAPSULE_FAVORITE_UPDATED,
            {
                "event_type": CAPSULE_FAVORITE_UPDATED,
                "user_id": str(user_id),
                "capsule_id": str(capsule_id),
                "action": action,
            },
        )


# 全局单例
capsule_favorite_service = CapsuleFavoriteService()
