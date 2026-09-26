"""Release scope flags 薄视图（wt483 PLAN 卡 A；v3-output/wt483-t36-align/PLAN.md §2.1/§3）。

单一权威在 app/config/settings.py 的 Settings 类（唯一 BaseSettings、唯一 env 管道，
RELEASE_ENABLE_* 分节、默认全 False）。本模块只是对 settings 单例的只读视图 +
FastAPI 依赖工厂——禁止在此再实例化/继承 BaseSettings（V3-FIX-21 同族禁令：
治理面与行为面分叉的双权威脑裂）。

消费时序（PLAN §4）：卡 A 只落权威 + 工厂 + 契约端点（零行为变化，无路由挂旗）；
卡 B 挂 leaderboards/community/transfer，卡 C 挂 visual_elements/shop/inventory。
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, status

from app.config import settings

# 五旗权威字段名（键序即 PLAN §3 统一形制；与 settings.py RELEASE_* 分节一一对应）
RELEASE_FLAG_FIELDS: tuple[str, ...] = (
    "RELEASE_ENABLE_SHOP",
    "RELEASE_ENABLE_PHOTON_TRANSFER",
    "RELEASE_ENABLE_PUBLIC_LEADERBOARDS",
    "RELEASE_ENABLE_PUBLIC_COMMUNITY",
    "RELEASE_ENABLE_VISUAL_ELEMENTS",
)

_CONTRACT_PREFIX = "RELEASE_ENABLE_"


def release_flags() -> dict[str, bool]:
    """从 settings 单例读当前五旗值（权威字段名 → bool）。"""
    return {name: bool(getattr(settings, name, False)) for name in RELEASE_FLAG_FIELDS}


def release_flags_response() -> dict[str, bool]:
    """/release-flags 契约响应构造（PLAN §2.8.1 单一形）。

    键集 = 去 ``RELEASE_ENABLE_`` 前缀的小写 snake_case（shop / photon_transfer /
    public_leaderboards / public_community / visual_elements），是移动端 provider
    的解码面——键集冻结，增删必须同步契约快照与移动端。
    """
    return {name[len(_CONTRACT_PREFIX) :].lower(): bool(getattr(settings, name, False)) for name in RELEASE_FLAG_FIELDS}


def require_release_flag(
    flag_name: str,
    status_code: int = status.HTTP_403_FORBIDDEN,
) -> Callable[[], None]:
    """FastAPI 依赖工厂：旗关时拒绝（默认 403 FEATURE_DISABLED，T36 语义保留）。

    未知旗名 fail-closed（视同关闭）。当前无任何路由消费本工厂——挂旗在卡 B/C；
    本卡带工厂是为了让挂旗动作零新增机制。
    """

    def dependency() -> None:
        if not bool(getattr(settings, flag_name, False)):
            raise HTTPException(
                status_code=status_code,
                detail="FEATURE_DISABLED",
            )

    return dependency
