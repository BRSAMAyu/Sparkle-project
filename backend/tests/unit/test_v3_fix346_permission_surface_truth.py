"""V3-FIX-346 · permission_service 死 enforcement 面退役契约测试.

背景（wt652 深查亲证，台账 V3-FIX-346）：
- 模块宣称「统一权限检查和管理」：enforcement 机械（check_permission/
  check_permissions/get_member_role/is_admin/is_owner/can_mute_user/
  can_kick_user + require_permission/require_admin/require_owner 三装饰器）
  全仓零调用方——装饰器唯一出现处是其自身 docstring 示例。
- 装饰器 :332 `kwargs.get('current_user', {}).get('id')` 对 ORM User 对象
  必 AttributeError（latent bug，因从不被调用而从未暴露）。
- 唯一可达消费 = auth.py 注册时取 MEMBER 权限清单写审计元数据与
  user.registered 事件（write-only 遥测，非授权）。
- 真实群管 enforcement 单一实现在 community_service.GroupService.
  _can_manage_member（operator/target 角色判禁言/踢人）。

裁决（wt655）：下线死面（FIX-339 先例）——删全部死 enforcement 机械
（含带 latent bug 的装饰器），保留角色权限映射常量（真实消费面），
docstring 如实标注 enforcement 去向；不接线（改写 live 群管路径在 RC 期
是零收益回归风险）。若未来需要统一装饰器，须带 ORM 取参修复+测试重建。
"""

from __future__ import annotations

import app.services.permission_service as ps
from app.models.community import GroupRole
from app.services.permission_service import Permission
from app.services.permission_service import PermissionService as PS

# 退役面：模块顶层名 + PermissionService 方法（全部零调用方）
DEAD_MODULE_NAMES = (
    "require_permission",
    "require_admin",
    "require_owner",
)
DEAD_SERVICE_METHODS = (
    "check_permission",
    "check_permissions",
    "get_member_role",
    "is_admin",
    "is_owner",
    "can_mute_user",
    "can_kick_user",
)


def test_dead_enforcement_surface_removed() -> None:
    """死 enforcement 面已退役：装饰器与死检查方法不可再 import/调用."""
    for name in DEAD_MODULE_NAMES:
        assert not hasattr(ps, name), f"死装饰器 {name} 应已删除"
    for method in DEAD_SERVICE_METHODS:
        assert not hasattr(PS, method), f"死方法 {method} 应已删除"


def test_docstring_no_longer_claims_unified_permission() -> None:
    """宣称面如实：活宣称面（类 docstring）不得再宣称「统一权限检查」；
    模块 docstring 的裁决历史记载属如实文档，不计."""
    assert "统一权限" not in (PS.__doc__ or "")
    assert "统一权限" not in (Permission.__doc__ or "")


def test_role_permission_constants_retained() -> None:
    """保留面（真实消费）：角色权限映射常量与查询方法完好."""
    member = PS.get_role_permissions(GroupRole.MEMBER)
    assert Permission.SEND_MESSAGE in member
    assert Permission.MUTE_MEMBERS not in member
    assert Permission.DISSOLVE_GROUP not in member
    owner = PS.get_role_permissions(GroupRole.OWNER)
    assert owner == set(Permission)
    # 三角色映射无空集（常量面完整）
    for role in GroupRole:
        assert PS.get_role_permissions(role), f"{role} 映射为空"


def test_auth_telemetry_consumer_still_works() -> None:
    """唯一真实消费面（注册审计遥测）不回退：MEMBER 清单排序输出."""
    expected = sorted(p.value for p in PS.get_role_permissions(GroupRole.MEMBER))
    assert len(expected) == 9
    assert "send_message" in expected


def test_real_enforcement_single_sourced_in_community_service() -> None:
    """真实群管 enforcement 单一实现钉死：community_service._can_manage_member 语义.

    OWNER 可管 ADMIN/MEMBER、不可管 OWNER；ADMIN 仅可管 MEMBER；
    MEMBER 不可管任何人。删除 permission_service 死平行实现后，
    该函数是群管授权唯一判据。
    """
    from app.services.community_service import GroupService

    can = GroupService._can_manage_member
    assert can(GroupRole.OWNER, GroupRole.ADMIN) is True
    assert can(GroupRole.OWNER, GroupRole.MEMBER) is True
    assert can(GroupRole.OWNER, GroupRole.OWNER) is False
    assert can(GroupRole.ADMIN, GroupRole.MEMBER) is True
    assert can(GroupRole.ADMIN, GroupRole.ADMIN) is False
    assert can(GroupRole.ADMIN, GroupRole.OWNER) is False
    assert can(GroupRole.MEMBER, GroupRole.MEMBER) is False
    assert can(GroupRole.MEMBER, GroupRole.ADMIN) is False
    assert can(GroupRole.MEMBER, GroupRole.OWNER) is False
