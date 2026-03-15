"""
权限控制服务
Permission Service - 统一权限检查和管理

功能:
- 统一权限枚举定义
- 角色权限映射
- 权限检查装饰器
- 资源访问控制
"""
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import (
    Group,
    GroupMember,
    GroupRole,
)


class Permission(str, Enum):
    """权限枚举"""
    # 消息相关
    SEND_MESSAGE = "send_message"           # 发送消息
    EDIT_MESSAGE = "edit_message"           # 编辑消息
    DELETE_MESSAGE = "delete_message"       # 删除消息
    REVOKE_MESSAGE = "revoke_message"       # 撤回消息
    PIN_MESSAGE = "pin_message"             # 置顶消息

    # 群管理相关
    MANAGE_MEMBERS = "manage_members"       # 管理成员
    MUTE_MEMBERS = "mute_members"           # 禁言成员
    KICK_MEMBERS = "kick_members"           # 踢出成员
    BAN_MEMBERS = "ban_members"             # 封禁成员
    MANAGE_ANNOUNCEMENT = "manage_announcement"  # 管理公告
    MANAGE_SETTINGS = "manage_settings"     # 管理设置
    MANAGE_KEYWORDS = "manage_keywords"     # 管理敏感词

    # 群组相关
    INVITE_MEMBERS = "invite_members"       # 邀请成员
    APPROVE_MEMBERS = "approve_members"     # 审批成员
    EDIT_GROUP_INFO = "edit_group_info"     # 编辑群信息
    DISSOLVE_GROUP = "dissolve_group"       # 解散群组
    TRANSFER_OWNER = "transfer_owner"       # 转让群主

    # 文件相关
    UPLOAD_FILE = "upload_file"             # 上传文件
    DOWNLOAD_FILE = "download_file"         # 下载文件
    DELETE_FILE = "delete_file"             # 删除文件
    MANAGE_FILE_PERMISSIONS = "manage_file_permissions"  # 管理文件权限

    # 任务相关
    CREATE_TASK = "create_task"             # 创建任务
    EDIT_TASK = "edit_task"                 # 编辑任务
    DELETE_TASK = "delete_task"             # 删除任务
    ASSIGN_TASK = "assign_task"             # 分配任务

    # 打卡相关
    CHECKIN = "checkin"                     # 打卡
    VIEW_CHECKIN = "view_checkin"           # 查看打卡

    # 举报相关
    REPORT_MESSAGE = "report_message"       # 举报消息
    REVIEW_REPORT = "review_report"         # 审核举报


# 角色权限映射
ROLE_PERMISSIONS: dict[GroupRole, set[Permission]] = {
    GroupRole.OWNER: {
        # 群主拥有所有权限
        Permission.SEND_MESSAGE,
        Permission.EDIT_MESSAGE,
        Permission.DELETE_MESSAGE,
        Permission.REVOKE_MESSAGE,
        Permission.PIN_MESSAGE,
        Permission.MANAGE_MEMBERS,
        Permission.MUTE_MEMBERS,
        Permission.KICK_MEMBERS,
        Permission.BAN_MEMBERS,
        Permission.MANAGE_ANNOUNCEMENT,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_KEYWORDS,
        Permission.INVITE_MEMBERS,
        Permission.APPROVE_MEMBERS,
        Permission.EDIT_GROUP_INFO,
        Permission.DISSOLVE_GROUP,
        Permission.TRANSFER_OWNER,
        Permission.UPLOAD_FILE,
        Permission.DOWNLOAD_FILE,
        Permission.DELETE_FILE,
        Permission.MANAGE_FILE_PERMISSIONS,
        Permission.CREATE_TASK,
        Permission.EDIT_TASK,
        Permission.DELETE_TASK,
        Permission.ASSIGN_TASK,
        Permission.CHECKIN,
        Permission.VIEW_CHECKIN,
        Permission.REPORT_MESSAGE,
        Permission.REVIEW_REPORT,
    },
    GroupRole.ADMIN: {
        # 管理员权限
        Permission.SEND_MESSAGE,
        Permission.EDIT_MESSAGE,
        Permission.DELETE_MESSAGE,
        Permission.REVOKE_MESSAGE,
        Permission.PIN_MESSAGE,
        Permission.MANAGE_MEMBERS,
        Permission.MUTE_MEMBERS,
        Permission.KICK_MEMBERS,
        Permission.MANAGE_ANNOUNCEMENT,
        Permission.MANAGE_KEYWORDS,
        Permission.INVITE_MEMBERS,
        Permission.APPROVE_MEMBERS,
        Permission.UPLOAD_FILE,
        Permission.DOWNLOAD_FILE,
        Permission.DELETE_FILE,
        Permission.CREATE_TASK,
        Permission.EDIT_TASK,
        Permission.DELETE_TASK,
        Permission.ASSIGN_TASK,
        Permission.CHECKIN,
        Permission.VIEW_CHECKIN,
        Permission.REPORT_MESSAGE,
        Permission.REVIEW_REPORT,
    },
    GroupRole.MEMBER: {
        # 普通成员权限
        Permission.SEND_MESSAGE,
        Permission.EDIT_MESSAGE,
        Permission.DELETE_MESSAGE,
        Permission.UPLOAD_FILE,
        Permission.DOWNLOAD_FILE,
        Permission.CREATE_TASK,
        Permission.CHECKIN,
        Permission.VIEW_CHECKIN,
        Permission.REPORT_MESSAGE,
    },
}


class PermissionService:
    """权限服务"""

    @staticmethod
    def get_role_permissions(role: GroupRole) -> set[Permission]:
        """获取角色的所有权限"""
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    async def check_permission(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID,
        permission: Permission
    ) -> bool:
        """
        检查用户是否拥有指定权限

        Args:
            db: 数据库会话
            user_id: 用户ID
            group_id: 群组ID
            permission: 需要检查的权限

        Returns:
            是否拥有权限
        """
        # 获取用户在群组中的角色
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return False

        # 检查角色权限
        role_permissions = PermissionService.get_role_permissions(member.role)
        return permission in role_permissions

    @staticmethod
    async def check_permissions(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID,
        permissions: set[Permission],
        require_all: bool = True
    ) -> bool:
        """
        检查用户是否拥有多个权限

        Args:
            db: 数据库会话
            user_id: 用户ID
            group_id: 群组ID
            permissions: 需要检查的权限集合
            require_all: 是否需要全部权限

        Returns:
            是否拥有权限
        """
        # 获取用户在群组中的角色
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return False

        # 检查角色权限
        role_permissions = PermissionService.get_role_permissions(member.role)

        if require_all:
            return permissions.issubset(role_permissions)
        else:
            return bool(permissions & role_permissions)

    @staticmethod
    async def get_member_role(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID
    ) -> GroupRole | None:
        """获取用户在群组中的角色"""
        result = await db.execute(
            select(GroupMember.role).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def is_admin(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID
    ) -> bool:
        """检查用户是否是管理员或群主"""
        role = await PermissionService.get_member_role(db, user_id, group_id)
        return role in (GroupRole.OWNER, GroupRole.ADMIN)

    @staticmethod
    async def is_owner(
        db: AsyncSession,
        user_id: UUID,
        group_id: UUID
    ) -> bool:
        """检查用户是否是群主"""
        role = await PermissionService.get_member_role(db, user_id, group_id)
        return role == GroupRole.OWNER

    @staticmethod
    async def can_mute_user(
        db: AsyncSession,
        operator_id: UUID,
        target_id: UUID,
        group_id: UUID
    ) -> bool:
        """检查是否可以禁言目标用户"""
        # 获取操作者角色
        operator_role = await PermissionService.get_member_role(db, operator_id, group_id)
        if not operator_role:
            return False

        # 获取目标用户角色
        target_role = await PermissionService.get_member_role(db, target_id, group_id)
        if not target_role:
            return False

        # 不能禁言群主
        if target_role == GroupRole.OWNER:
            return False

        # 管理员不能禁言管理员
        if operator_role == GroupRole.ADMIN and target_role == GroupRole.ADMIN:
            return False

        # 群主可以禁言任何人，管理员可以禁言普通成员
        return operator_role in (GroupRole.OWNER, GroupRole.ADMIN)

    @staticmethod
    async def can_kick_user(
        db: AsyncSession,
        operator_id: UUID,
        target_id: UUID,
        group_id: UUID
    ) -> bool:
        """检查是否可以踢出目标用户"""
        # 与禁言逻辑相同
        return await PermissionService.can_mute_user(db, operator_id, target_id, group_id)


# 装饰器类型
F = TypeVar('F', bound=Callable[..., Any])


def require_permission(permission: Permission):
    """
    权限检查装饰器

    用法:
        @require_permission(Permission.MANAGE_MEMBERS)
        async def some_endpoint(...):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中提取db, user_id, group_id
            # 这需要根据实际的endpoint参数命名调整
            db = kwargs.get('db')
            user_id = kwargs.get('current_user', {}).get('id')
            group_id = kwargs.get('group_id')

            if not all([db, user_id, group_id]):
                raise HTTPException(
                    status_code=500,
                    detail="Permission check failed: missing required parameters"
                )

            has_permission = await PermissionService.check_permission(
                db, user_id, group_id, permission
            )

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission.value}"
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_admin():
    """
    管理员权限检查装饰器
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db = kwargs.get('db')
            user_id = kwargs.get('current_user', {}).get('id')
            group_id = kwargs.get('group_id')

            if not all([db, user_id, group_id]):
                raise HTTPException(
                    status_code=500,
                    detail="Permission check failed: missing required parameters"
                )

            is_admin = await PermissionService.is_admin(db, user_id, group_id)

            if not is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Admin permission required"
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_owner():
    """
    群主权限检查装饰器
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db = kwargs.get('db')
            user_id = kwargs.get('current_user', {}).get('id')
            group_id = kwargs.get('group_id')

            if not all([db, user_id, group_id]):
                raise HTTPException(
                    status_code=500,
                    detail="Permission check failed: missing required parameters"
                )

            is_owner = await PermissionService.is_owner(db, user_id, group_id)

            if not is_owner:
                raise HTTPException(
                    status_code=403,
                    detail="Owner permission required"
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
