"""V3-FIX-347 处置守卫（wt655）：头像审核台结构性零进料撤面.

原状（wt652 深查亲证）：/audit/avatars(+/{user_id}/approve|reject) 三端点
真实可达（superuser 门+网关代理+avatar_moderation 审计分类），但全仓
（backend Python+gateway Go 两侧）无任何写入方将 avatar_status 置
PENDING——用户头像更新（users.py update_profile）直设 APPROVED 绕过审核。
队列结构性恒空：get_pending_avatars 恒 []，approve/reject 实践恒 404。
内容安全治理姿态（审核端点+审计分类+pending_avatar_url 全套语义）建立
在零进料队列上，若被审计方当真即为合规虚报。

裁决=撤面如实化（FIX-339/341 先例）：比赛期产品语义为头像免审直通
（无 admin 审核工作流/mobile 审核 UI），补 PENDING 进料只会让用户头像
永久滞留待审（无审核者）。三端点+AuditService 已删；users.py 直通路径
如实注释留档；DB 列 avatar_status/pending_avatar_url 保留（RC 期不做
迁移，值恒 APPROVED/None）。若未来引入真实内容审核工作流，须三件齐上
（进料置 PENDING+审核工作流+admin UI）并更新本守卫。本守卫断言：
  - AuditService 模块不可 import（不留孤儿服务）；
  - /audit 路由组不再注册任何 /avatars 路由；
  - 全仓 backend/app 无代码路径写入 AvatarStatus.PENDING（零进料即零
    审核语义，防止端点复活后仍是空转假面）。
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

from app.api.v1.router import api_router  # noqa: E402


def test_audit_service_module_is_gone() -> None:
    assert importlib.util.find_spec("app.services.audit_service") is None, (
        "app.services.audit_service 已随 V3-FIX-347 撤面删除；重建须头像"
        "进料置 PENDING+审核工作流+admin UI 三件齐上并更新本守卫"
    )


def test_audit_router_has_no_avatar_moderation_routes() -> None:
    """/audit 组不得再注册头像审核端点（空转假面不复活）。"""
    audit_routes = [
        getattr(route, "path", "")
        for route in api_router.routes
        if getattr(route, "path", "").startswith("/audit")
    ]
    leaked = [p for p in audit_routes if "avatar" in p]
    assert not leaked, f"/audit 组出现已撤面的头像审核路由 {leaked}"


def test_no_pending_avatar_writer_exists() -> None:
    """全仓 backend/app 零 AvatarStatus.PENDING 写入方（结构性零进料如实化）.

    PENDING 值保留在枚举中仅因 DB Enum 列类型稳定（RC 期不迁移）；
    任何生产代码再次写入 PENDING 即重建了空转审核面，必须连同端点+
    工作流一起重建。
    """
    result = subprocess.run(
        ["grep", "-rn", "AvatarStatus.PENDING", str(BACKEND_ROOT / "app")],
        capture_output=True,
        text=True,
    )
    hits = []
    for line in (result.stdout or "").splitlines():
        if not line or "__pycache__" in line:
            continue
        _path, _lineno, *rest = line.split(":", 2)
        code = (rest[0] if rest else "").split("#", 1)[0]  # 去注释后扫代码面
        if "AvatarStatus.PENDING" in code:
            hits.append(line)
    assert not hits, f"发现 AvatarStatus.PENDING 代码写入/读取方，空转审核面复活：{hits}"
