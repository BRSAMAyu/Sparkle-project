"""
Core: infra
Phase: none
Stage: 40

D-06 · WVPL 北极星只读暴露端点（WT352 · 愿景差距 G7）。

差距背景（v3-output/WT347-VISION-GAP/REPORT.md G7）：WVPL（Weekly Valuable
Progress Loops，METRIC_TREE North Star）已有 frozen schema + golden 冻结 + 每日
worker（``app/core/north_star_wvpl.py`` / ``tests/golden`` /
``app/workers/cost_wvpl_worker.py``），但 api/v1 零暴露——评审无法查询
分母/loops/分工分布，「北极星必须可答」不可达。本模块补上只读查询面：

- **响应形状 = frozen schema**（``north_star.wvpl.fact.v1``）：handler 只做
  参数解析，直接返回 ``NorthStarWvplService.build_fact`` 的事实 JSON dict，
  不发明第二套 schema、不做任何后处理；
- **只读**：服务是确定性聚合查询层，无写路径；认证/权限沿同族 admin 端点
  惯例（superuser 依赖，``memory_admin``/``admin_dashboard`` 同款）；
- **诚实空态**：空库/未初始化时服务如实返回零计数 + None 比率（分母 0 不
  伪造比率是 frozen 口径的一部分），本端点不加默认值、不造假数据；
- **as_of 幂等锚点可选注入**：评审/审计可指定锚点复现逐字节事实 JSON
  （缺省 = 当前墙钟，生产语义）。

网关侧零改动：``proxy_routes.go`` 的 ``/admin`` catch-all 代理组已覆盖本路径
（authMiddleware + RequireAdmin → Python 引擎，引擎侧二次校验 superuser）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.services.north_star_wvpl_service import NorthStarWvplService

router = APIRouter(
    prefix="/admin/north-star",
    tags=["north-star-wvpl"],
    dependencies=[Depends(get_current_active_superuser)],
)


# route-tier: internal
@router.get(
    "/wvpl-fact", response_model=dict[str, Any], summary="WVPL 北极星事实 JSON（frozen schema north_star.wvpl.fact.v1）"
)
async def get_wvpl_fact(
    as_of: Annotated[
        datetime | None,
        Query(
            description=(
                "幂等锚点（ISO 8601，naive UTC 语义）：窗口为 [as_of-7d, as_of)。"
                "缺省取当前墙钟；同一 as_of + 同一库态 → 逐字节相同的事实 JSON。"
            ),
        ),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """产出 WVPL 北极星事实 JSON（只读；形状 = frozen schema，零后处理）。"""
    return await NorthStarWvplService(db).build_fact(as_of=as_of)
