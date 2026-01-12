from enum import Enum
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.galaxy import GalaxyUserPermission, CollaborativeGalaxy

class GalaxyPermission(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    CONTRIBUTOR = "contrib"

class GalaxyPermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_permission(self, galaxy_id: UUID, user_id: UUID) -> Optional[GalaxyPermission]:
        """获取用户在特定星图中的权限"""
        stmt = select(GalaxyUserPermission.permission_level).where(
            and_(
                GalaxyUserPermission.galaxy_id == galaxy_id,
                GalaxyUserPermission.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        level = result.scalar_one_or_none()
        if level:
            return GalaxyPermission(level)
        return None

    async def has_permission(self, galaxy_id: UUID, user_id: UUID, required_levels: List[GalaxyPermission]) -> bool:
        """检查用户是否具有所需权限级别之一"""
        permission = await self.get_user_permission(galaxy_id, user_id)
        if not permission:
            return False
        return permission in required_levels

    async def can_edit(self, galaxy_id: UUID, user_id: UUID) -> bool:
        """检查用户是否可以编辑（添加/更新节点）"""
        return await self.has_permission(
            galaxy_id, 
            user_id, 
            [GalaxyPermission.OWNER, GalaxyPermission.EDITOR, GalaxyPermission.CONTRIBUTOR]
        )

    async def can_manage(self, galaxy_id: UUID, user_id: UUID) -> bool:
        """检查用户是否可以管理（删除节点/修改权限）"""
        return await self.has_permission(
            galaxy_id, 
            user_id, 
            [GalaxyPermission.OWNER, GalaxyPermission.EDITOR]
        )
