"""
Capsule Favorite Service

处理胶囊收藏功能
"""
from __future__ import annotations

import re
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
                "method_preferences": [],
                "method_preference_summary": [],
            }

        depth_counts: dict[str, int] = {}
        subject_counts: dict[str, int] = {}
        recent_notes: list[str] = []
        method_counts: dict[str, dict[str, object]] = {}
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
            for method in self._extract_method_preferences(capsule, note=note):
                entry = method_counts.setdefault(
                    method["key"],
                    {
                        "key": method["key"],
                        "label": method["label"],
                        "count": 0,
                        "source_titles": [],
                    },
                )
                entry["count"] = int(entry["count"]) + 1
                source_titles = entry["source_titles"]
                if isinstance(source_titles, list) and method["source_title"] not in source_titles:
                    source_titles.append(method["source_title"])

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
        method_preferences = self._rank_method_preferences(method_counts, favorite_count=len(rows))
        return {
            "favorite_count": len(rows),
            "content_depth_preference": content_depth_preference,
            "subject_affinity": subject_affinity,
            "recent_notes": recent_notes[:3],
            "method_preferences": method_preferences,
            "method_preference_summary": [
                f"用户偏好{method['label']}" for method in method_preferences[:3]
            ],
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

    @staticmethod
    def _extract_method_preferences(capsule: CuriosityCapsule, *, note: str = "") -> list[dict[str, str]]:
        title = str(capsule.title or "").strip()
        content = str(capsule.content or "").strip()
        subject = str(capsule.related_subject or "").strip()
        haystack = "\n".join(part for part in (title, content[:500], subject, note) if part).lower()
        methods: list[dict[str, str]] = []

        if any(token in haystack for token in ("番茄钟", "pomodoro", "25/5", "25 分钟", "25分钟")):
            methods.append(
                {
                    "key": "pomodoro",
                    "label": "番茄钟方法",
                    "source_title": title or "未命名胶囊",
                }
            )

        title_method = CapsuleFavoriteService._method_label_from_title(title)
        if (
            title_method
            and not any(item["key"] == "pomodoro" for item in methods)
            and all(item["label"] != title_method for item in methods)
        ):
            methods.append(
                {
                    "key": CapsuleFavoriteService._method_key(title_method),
                    "label": title_method,
                    "source_title": title or "未命名胶囊",
                }
            )
        return methods[:3]

    @staticmethod
    def _method_label_from_title(title: str) -> str:
        normalized = str(title or "").strip()
        if not normalized:
            return ""
        if any(marker in normalized for marker in ("方法", "技巧", "法", "策略", "模型")):
            return normalized[:40]
        match = re.search(r"([\w\u4e00-\u9fff]{2,24}(?:方法|技巧|法|策略|模型))", normalized)
        return match.group(1) if match else ""

    @staticmethod
    def _method_key(label: str) -> str:
        slug = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "_", str(label or "").strip().lower()).strip("_")
        return slug[:48] or "capsule_method"

    @staticmethod
    def _rank_method_preferences(
        method_counts: dict[str, dict[str, object]],
        *,
        favorite_count: int,
    ) -> list[dict[str, object]]:
        ranked: list[dict[str, object]] = []
        for entry in sorted(
            method_counts.values(),
            key=lambda item: (-int(item.get("count") or 0), str(item.get("label") or "")),
        ):
            count = int(entry.get("count") or 0)
            confidence = min(0.86, 0.55 + (count / max(favorite_count, 1)) * 0.25)
            ranked.append(
                {
                    "key": str(entry.get("key") or ""),
                    "label": str(entry.get("label") or ""),
                    "count": count,
                    "confidence": round(confidence, 2),
                    "source_titles": [
                        str(title)
                        for title in list(entry.get("source_titles") or [])[:3]
                        if str(title).strip()
                    ],
                }
            )
        return ranked[:5]


# 全局单例
capsule_favorite_service = CapsuleFavoriteService()
