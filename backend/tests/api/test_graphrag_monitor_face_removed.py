"""V3-FIX-341 处置守卫（wt646）：GraphRAG monitor 假开关撤面。

原状：router.py 以 ENABLE_GRAPHRAG_MONITOR_API 门注册 graph_monitor
(/monitor/graph) 与 graphrag_trace(/graphrag)，但旗默认 False 且网关
proxy_routes.go 无 /monitor、/graphrag 代理组——翻旗客户端仍 404
（假开关：旗宣称的能力无到达路径）。

裁决=撤面（WONTFIX 不接线）：消费面（mobile GraphRAGVisualizer 从未被
喂数）与被监控体（ENABLE_GRAPHRAG_FASTPATH 默认 False）双双缺位，补网关
代理组只会给休眠诊断面开外露通道。两 router 模块已删；trace 落存侧
（cache_trace）保留。本守卫断言：
  - 两模块不可 import（撤面后不得留孤儿模块）；
  - 无论旗值如何，api_router 不再注册 /monitor/graph、/graphrag 路由
    （假开关的"翻旗可达"承诺永久失效，直到三件套重建）。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.api.v1.router import api_router  # noqa: E402

REMOVED_MODULES = ("app.api.v1.graph_monitor", "app.api.v1.graphrag_trace")
REMOVED_ROUTE_PREFIXES = ("/monitor/graph", "/graphrag")


def _registered_paths() -> set[str]:
    return {getattr(route, "path", "") for route in api_router.routes}


def test_removed_router_modules_are_gone() -> None:
    for module in REMOVED_MODULES:
        assert importlib.util.find_spec(module) is None, (
            f"{module} 已随 V3-FIX-341 撤面删除；重建须网关代理组+router+"
            "mobile 喂数三件齐上并更新本守卫"
        )


def test_graphrag_routes_unreachable_even_with_flag_flipped(monkeypatch) -> None:
    """撤面后翻旗也不得出现 graphrag 路由（原假开关承诺已作废）。"""
    monkeypatch.setattr(settings, "ENABLE_GRAPHRAG_MONITOR_API", True)
    paths = _registered_paths()
    for prefix in REMOVED_ROUTE_PREFIXES:
        leaked = [p for p in paths if p.startswith(prefix)]
        assert not leaked, (
            f"ENABLE_GRAPHRAG_MONITOR_API=True 时出现已撤面路由 {leaked}；"
            "graphrag monitor 面已随 V3-FIX-341 删除"
        )
