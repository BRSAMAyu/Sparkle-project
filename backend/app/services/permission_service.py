"""角色权限映射常量（原「权限控制服务」死 enforcement 面已退役）。

V3-FIX-346 如实化裁决（wt655，FIX-339 退役删除先例）：

本模块的可达消费面只有「角色→权限清单」映射——auth.py 注册流程取
MEMBER 清单写入审计元数据与 user.registered 事件（write-only 遥测）。

原宣称「统一权限检查和管理」的 enforcement 机械（check_permission/
check_permissions/get_member_role/is_admin/is_owner/can_mute_user/
can_kick_user + require_permission/require_admin/require_owner 三装饰器）
经 wt652 深查为全仓零调用方的死平行实现，且装饰器取参
``kwargs.get('current_user', {}).get('id')`` 对 ORM User 对象必
AttributeError（latent bug，因从不被调用而从未暴露），已全部删除。

真实的群管权限 enforcement 在 community_service.GroupService.
_can_manage_member（operator/target 角色判禁言/踢人，单一实现，
tests/unit/test_v3_fix346_permission_surface_truth.py 钉死其语义）。
未来如需统一权限装饰器，须带 ORM 取参修复+调用方+测试重建，
不得从本模块历史版本复活死代码。
"""
from __future__ import annotations

from enum import StrEnum

from app.models.community import GroupRole


class Permission(StrEnum):
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
    """角色权限映射查询（唯一消费方：auth.py 注册审计遥测）"""

    @staticmethod
    def get_role_permissions(role: GroupRole) -> set[Permission]:
        """获取角色的所有权限"""
        return ROLE_PERMISSIONS.get(role, set())
