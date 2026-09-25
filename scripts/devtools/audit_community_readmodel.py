#!/usr/bin/env python3
"""S-01 段一：Community Realtime/Read-model 真相审计（可重复报告）。

一条命令产出结构化 report：每个读模投影一行
（名称 | 来源 | 新鲜度机制 | 一致性风险 | live 可测性），
外加可选的 live 探测面。诚实性红线：

- live 探测失败/不可达 = 如实记录 ``unreachable/error``，绝不合成
  「假 realtime」成功样（卡面 Forbidden）；
- 默认**不连任何 PostgreSQL**（应用库社区表可能有真数据）；只有显式
  传 ``--pg-dsn``（指向自建独立库时）才做 outbox 计数探测；
- Redis 探测只读（SCAN/XLEN/XINFO/EXISTS），零写入；
- 静态事实段由本脚本内登记的审计结论 + 代码锚点（path#symbol）构成，
  锚点可用 ``--verify-anchors`` 用 grep 复核（同一 commit 下可重复）。

用法：
    python3 audit_community_readmodel.py                       # 静态审计（零网络）
    python3 audit_community_readmodel.py --format json         # 结构化输出
    python3 audit_community_readmodel.py --live                # + 只读 live 探测
    python3 audit_community_readmodel.py --live --strict-live  # live 失败→exit 2
    python3 audit_community_readmodel.py --verify-anchors      # 复核代码锚点

产出（段一审计基线，commit 级可重复）：
    C1 community CQRS 投影链（post:view:* / feed:global / post:likes:*）
       = 双向死链：event_outbox 无生产者（gateway internal/cqrs/outbox/
       repository.go#Insert 零非测试调用方）→ cqrs:stream:community 饥饿 →
       投影永为空；同时无任何 HTTP handler 读这些键（读侧亦空）。
       admin /cqrs/projections 会显示 status=active（注册时 upsert），
       属观测面误导，不代表有事件流过。
    C2 帖子/点赞/评论写路径不发布任何事件（无 outbox、无 event_bus、
       无 WS 推送）——feed 是纯拉取面，POST 后靠客户端刷新。
    C3 群聊 realtime = 真 WS：mobile → gateway :8080
       /api/v1/community/groups/{id}/ws（票+JWT、升级限流）→ 引擎 FastAPI
       WS → 进程内 ConnectionManager + Redis pub/sub group:{id} 扇出。
       Redis 不可用时 broadcast 回落**本进程**广播（多 worker 部署会静默
       丢跨进程推送）——回落被如实限定，不冒充分布式送达。
    C4 feed/消息读路径 = PG 直读（SQLAlchemy），无缓存层参与，
       read-your-writes；mobile 断网回落 ListReadCache 本地快照且 UI 强制
       挂 fromCache/asOf 时点标记（诚实回落，非假实时）。
    C5 seed/demo 数据标记：V3-FIX-08 cohort 帖对真实用户按不存在处理
       （feed/like 双面一致）；mobile Mock 仓储仅在 DemoDataService.
       isDemoMode（静态默认 False）下启用。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

REPO_DEFAULT = "."
GATEWAY_DEFAULT = "http://127.0.0.1:8080"
ENGINE_DEFAULT = "http://127.0.0.1:8000"
REDIS_DEFAULT = "redis://127.0.0.1:6379/0"


# ---------------------------------------------------------------- 静态审计


@dataclass
class ProjectionRow:
    """一行读模投影审计结论（卡面验收字段口径）。"""

    name: str
    source: str
    freshness: str
    consistency_risk: str
    live_testability: str
    status: str
    anchors: list[str] = field(default_factory=list)


STATIC_ROWS: list[ProjectionRow] = [
    ProjectionRow(
        name="community.post_view_projection (gateway Redis)",
        source="event_outbox → Redis stream cqrs:stream:community → "
        "CommunitySyncWorker / CommunityProjectionHandler → 键 "
        "post:view:*、feed:global、post:likes:*",
        freshness="事件驱动最终一致（设计值）；实际=永为空（写侧无生产者，见 status）",
        consistency_risk="致死死链（双向）：outbox Insert 零非测试调用方→流饥饿；"
        "无任何 HTTP handler 读这些键→投影即使有值也无人消费。"
        "admin /cqrs/projections 显示 status=active 属注册期 upsert，不代表有事件流过",
        live_testability="Redis 只读探测（XLEN cqrs:stream:community / SCAN post:view:*）"
        "+ GET /admin/cqrs/projections（需 admin JWT）",
        status="DEAD_CHAIN（登记不修——卡面 Forbidden 不重建读模）",
        anchors=[
            "backend/gateway/internal/cqrs/outbox/repository.go#Insert",
            "backend/gateway/internal/worker/community_sync.go#CommunitySyncWorker",
            "backend/gateway/internal/cqrs/projection/handlers.go#CommunityProjectionHandler",
            "backend/gateway/cmd/server/setup.go#initCQRS",
        ],
    ),
    ProjectionRow(
        name="community.feed / posts / comments / messages (engine PG 直读)",
        source="PostgreSQL 直读（SQLAlchemy）：Post+PostLike+GroupMessage 等，"
        "visibility/cohort/block/软删过滤全部在 SQL 谓词内",
        freshness="read-your-writes（无缓存层参与，写后立即可读）",
        consistency_risk="深分页 offset 语义（并发写导致翻页漂移）；"
        "无投影参与故无投影不一致问题",
        live_testability="GET /api/v1/community/feed?page=1&limit=1（需 JWT，API 级可测）",
        status="ACTIVE_TRUTH_SOURCE",
        anchors=[
            "backend/app/api/v1/community.py#get_feed",
            "backend/app/api/v1/community.py#_cohort_visible_post_clause",
        ],
    ),
    ProjectionRow(
        name="community.post_write_event_face（帖子写路径事件面）",
        source="无——create_post / toggle_like / delete_post 不发布任何事件"
        "（无 outbox、无 event_bus、无 WS 推送）",
        freshness="纯拉取面：写后靠客户端主动刷新",
        consistency_risk="多端视图靠轮询/重拉收敛，无推送即有陈旧窗口（如实现状）",
        live_testability="API 级：POST /posts 后 GET /feed 比对（需双 JWT，段二双账号面）",
        status="NO_EVENT_SOURCE（如实登记，不 mock 补齐）",
        anchors=[
            "backend/app/api/v1/community.py#create_post",
            "backend/app/api/v1/community.py#toggle_like_post",
        ],
    ),
    ProjectionRow(
        name="community.group_realtime (群聊 WS)",
        source="mobile → gateway :8080 /api/v1/community/groups/{id}/ws"
        "（票+JWT、升级限流、双向代理）→ 引擎 FastAPI WS → 进程内 "
        "ConnectionManager + Redis pub/sub group:{id} 扇出",
        freshness="推送即时（同一引擎进程内/经 pub/sub 跨进程）",
        consistency_risk="Redis 不可用时 broadcast 回落本进程广播——多 worker 部署"
        "静默丢跨进程推送（回落被限定为降级而非假送达）；"
        "send_personal_message 在 Redis 开启且接收方全实例不在线时不触发离线推送"
        "（触发点仅在本进程未命中分支）",
        live_testability="段二双账号 live 证据（DEFERRED）：join→chat→reconnect；"
        "段一仅可验证升级握手被鉴权面拒绝/放行",
        status="ACTIVE_REALTIME",
        anchors=[
            "backend/app/api/v1/community.py#websocket_endpoint",
            "backend/app/core/websocket.py#ConnectionManager",
            "backend/gateway/internal/handler/websocket_proxy.go#HandleCommunityWS",
        ],
    ),
    ProjectionRow(
        name="community.checkin (打卡)",
        source="PG（squad service 结算）+ manager.broadcast 推送群 WS + "
        "event_bus 'community.checkin_recorded'（无订阅者时为纯事件流记录，"
        "不产生副作用——代码注释如实声明）",
        freshness="广播即时；无投影落地",
        consistency_risk="依赖群 WS 在线面，离线成员靠重连后 HTTP 读收敛",
        live_testability="段二双账号（DEFERRED）：A 打卡 B 在群 WS 收推送",
        status="ACTIVE_REALTIME",
        anchors=["backend/app/api/v1/community.py#checkin_event_publish"],
    ),
    ProjectionRow(
        name="task_projection / galaxy_projection (gateway Redis)",
        source="与 C1 同一 event_outbox → cqrs:stream:* 死链模式",
        freshness="同上：永为空",
        consistency_risk="同 C1；task 事件族属 wt360 在修战区（task_event_consumer），"
        "本卡只登记不触碰",
        live_testability="同 C1（XLEN cqrs:stream:task / galaxy）",
        status="DEAD_CHAIN（登记不修）",
        anchors=[
            "backend/gateway/internal/worker/community_sync.go#CommunityStreamKey",
            "backend/gateway/cmd/server/setup.go#startCQRSWorkers",
        ],
    ),
    ProjectionRow(
        name="mobile.community_read_cache (断网回落)",
        source="ListReadCache 本地快照（getFeedCached：成功落快照，"
        "连接类失败回读）",
        freshness="回读=陈旧快照，UI 强制挂 fromCache/asOf「截至 X」时点标记",
        consistency_risk="快照与服务器态之间的窗口由时点标记如实暴露（诚实回落，"
        "非假 realtime——符合卡面验收）",
        live_testability="定向 flutter test（本段 LIGHT 不执行，DEFERRED 登记命令）",
        status="ACTIVE_HONEST_FALLBACK",
        anchors=[
            "mobile/lib/features/community/data/repositories/community_repository.dart#getFeedCached",
            "mobile/lib/features/community/data/repositories/community_repository.dart#communityRepositoryProvider",
        ],
    ),
    ProjectionRow(
        name="seed/demo 数据标记面",
        source="V3-FIX-08：cohort（guest/seed）作者帖在公开 feed 与 like 面对真实用户"
        "按不存在处理（本人帖除外）；关系面 scope 不做 cohort 过滤",
        freshness="随每次查询实时判定",
        consistency_risk="feed 与 like 双面已对齐（同一谓词函数）；"
        "若未来新增写/读面漏用该谓词会出现可见性漂移",
        live_testability="API 级：guest cohort 种子帖对真实账号 404/不可见（段二双账号）",
        status="ACTIVE_SEED_MARKING",
        anchors=[
            "backend/app/api/v1/community.py#_cohort_visible_post_clause",
            "mobile/lib/core/services/demo_data_service.dart#isDemoMode",
        ],
    ),
]

ANCHOR_SEARCHES: dict[str, str] = {
    "backend/gateway/internal/cqrs/outbox/repository.go#Insert": "func (r *PostgresRepository) Insert",
    "backend/gateway/internal/worker/community_sync.go#CommunitySyncWorker": "type CommunitySyncWorker struct",
    "backend/gateway/internal/worker/community_sync.go#CommunityStreamKey": "cqrs:stream:community",
    "backend/gateway/internal/cqrs/projection/handlers.go#CommunityProjectionHandler": "type CommunityProjectionHandler struct",
    "backend/gateway/cmd/server/setup.go#initCQRS": "func initCQRS",
    "backend/gateway/cmd/server/setup.go#startCQRSWorkers": "func startCQRSWorkers",
    "backend/gateway/internal/handler/websocket_proxy.go#HandleCommunityWS": "func (p *WebSocketProxy) HandleCommunityWS",
    "backend/app/api/v1/community.py#get_feed": "async def get_feed",
    "backend/app/api/v1/community.py#_cohort_visible_post_clause": "def _cohort_visible_post_clause",
    "backend/app/api/v1/community.py#create_post": "async def create_post",
    "backend/app/api/v1/community.py#toggle_like_post": "async def toggle_like_post",
    "backend/app/api/v1/community.py#websocket_endpoint": "async def websocket_endpoint",
    "backend/app/api/v1/community.py#checkin_event_publish": "community.checkin_recorded",
    "backend/app/core/websocket.py#ConnectionManager": "class ConnectionManager",
    "mobile/lib/features/community/data/repositories/community_repository.dart#getFeedCached": "getFeedCached",
    "mobile/lib/features/community/data/repositories/community_repository.dart#communityRepositoryProvider": "communityRepositoryProvider",
    "mobile/lib/core/services/demo_data_service.dart#isDemoMode": "isDemoMode = false",
}


def verify_anchors(repo: str) -> list[dict[str, Any]]:
    """grep 复核每个锚点在当前树内可命中（同一 commit 下可重复）。"""
    results = []
    for anchor, pattern in ANCHOR_SEARCHES.items():
        path = anchor.split("#")[0]
        proc = subprocess.run(
            ["grep", "-lF", pattern, f"{repo}/{path}"],
            capture_output=True,
            text=True,
        )
        results.append({"anchor": anchor, "present": proc.returncode == 0})
    return results


# ---------------------------------------------------------------- live 探测


def probe_http(name: str, url: str) -> dict[str, Any]:
    """只读 HTTP GET 探测；失败如实记录，绝不合成成功。"""
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=4) as resp:
            body = resp.read(2048).decode("utf-8", "replace")
            return {"probe": name, "url": url, "status": "ok", "http": resp.status, "body_head": body[:200]}
    except Exception as exc:  # noqa: BLE001 —— 探测面把一切失败如实带出
        return {"probe": name, "url": url, "status": "unreachable", "error": f"{type(exc).__name__}: {exc}"}


def probe_redis_readonly(url: str) -> dict[str, Any]:
    """Redis 只读探测（SCAN/XLEN/XINFO/EXISTS）；零写入。"""
    try:
        import redis  # 延迟导入：无 redis-py 时静态审计不受影响
    except ImportError:
        return {"probe": "redis", "status": "skipped", "error": "redis-py 未安装（pip install redis）"}

    out: dict[str, Any] = {"probe": "redis", "status": "ok", "readonly": True, "facts": {}}
    try:
        client = redis.from_url(url, socket_connect_timeout=4, socket_timeout=4, decode_responses=True)
        facts: dict[str, Any] = {}
        facts["stream_len"] = {
            "cqrs:stream:community": client.xlen("cqrs:stream:community"),
            "cqrs:stream:task": client.xlen("cqrs:stream:task"),
            "cqrs:stream:galaxy": client.xlen("cqrs:stream:galaxy"),
        }
        groups: dict[str, Any] = {}
        for stream in ("cqrs:stream:community", "cqrs:stream:task", "cqrs:stream:galaxy"):
            try:
                groups[stream] = client.xinfo_groups(stream)
            except Exception as exc:  # noqa: BLE001
                groups[stream] = f"no-group/error: {type(exc).__name__}"
        facts["consumer_groups"] = groups
        projection_keys: dict[str, int] = {}
        for pattern in ("post:view:*", "task:view:*", "galaxy:node:*"):
            count = 0
            cursor: int | str = 0
            while True:
                cursor, batch = client.scan(cursor=cursor, match=pattern, count=200)
                count += len(batch)
                if cursor in (0, "0"):
                    break
            projection_keys[pattern] = count
        facts["projection_key_counts"] = projection_keys
        facts["feed_global_exists"] = bool(client.exists("feed:global"))
        facts["feed_global_members"] = client.zcard("feed:global") if facts["feed_global_exists"] else 0
        client.close()
        out["facts"] = facts
        out["interpretation"] = (
            "stream_len=0 且 projection_key_counts=0 即实证 C1 死链（流饥饿、投影为空）；"
            "非零则记录实际值供段二比对——两种结果都是如实报告"
        )
    except Exception as exc:  # noqa: BLE001
        out["status"] = "unreachable"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def probe_admin_projections(gateway: str, admin_token: str | None) -> dict[str, Any]:
    """admin 投影元数据面（需 admin JWT；未提供则如实记 skipped）。"""
    if not admin_token:
        return {
            "probe": "admin_cqrs_projections",
            "status": "skipped",
            "note": "需 --admin-token（admin JWT）；该面读 PG projection_metadata，"
            "属网关自身运行元数据，不触应用业务库",
        }
    import urllib.error
    import urllib.request

    url = f"{gateway}/admin/cqrs/projections"
    try:
        req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {admin_token}"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            return {"probe": "admin_cqrs_projections", "status": "ok", "http": resp.status, "body_head": resp.read(1024).decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001
        return {"probe": "admin_cqrs_projections", "url": url, "status": "unreachable", "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------- 主流程


def main() -> int:
    parser = argparse.ArgumentParser(description="S-01 社区读模真相审计（可重复）")
    parser.add_argument("--repo", default=REPO_DEFAULT, help="仓库根（锚点复核基准）")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--live", action="store_true", help="追加只读 live 探测（gateway/engine/Redis）")
    parser.add_argument("--gateway", default=GATEWAY_DEFAULT)
    parser.add_argument("--engine", default=ENGINE_DEFAULT)
    parser.add_argument("--redis-url", default=REDIS_DEFAULT)
    parser.add_argument("--admin-token", default=None, help="admin JWT（可选）")
    parser.add_argument("--strict-live", action="store_true", help="任一 live 探测失败 → exit 2")
    parser.add_argument("--verify-anchors", action="store_true", help="grep 复核代码锚点")
    parser.add_argument("--out", default=None, help="同时写 JSON 到该路径")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "card": "S-01 segment-1 (community realtime/read-model truth audit)",
        "honesty_contract": "live 失败/不可达一律如实记录，不合成假 realtime；默认零 PG 连接",
        "projections": [asdict(r) for r in STATIC_ROWS],
    }

    if args.verify_anchors:
        report["anchor_verification"] = verify_anchors(args.repo)

    live_failed = False
    if args.live:
        live = [
            probe_http("gateway_health", f"{args.gateway}/api/v1/health"),
            probe_http("engine_health", f"{args.engine}/health"),
            probe_redis_readonly(args.redis_url),
            probe_admin_projections(args.gateway, args.admin_token),
        ]
        report["live_probes"] = live
        live_failed = any(p.get("status") not in ("ok", "skipped") for p in live)
        report["live_verdict"] = (
            "部分探测不可达——按卡面口径如实记录，不 fallback 假 realtime"
            if live_failed
            else "全部可达探测完成（只读）"
        )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 100)
        print("S-01 段一 · Community Read-model 真相审计（每投影一行）")
        print("=" * 100)
        for r in STATIC_ROWS:
            print(f"\n◆ {r.name}   [{r.status}]")
            print(f"  来源      : {r.source}")
            print(f"  新鲜度    : {r.freshness}")
            print(f"  一致性风险: {r.consistency_risk}")
            print(f"  live可测性: {r.live_testability}")
            print(f"  锚点      : {'; '.join(r.anchors)}")
        if "anchor_verification" in report:
            missing = [a["anchor"] for a in report["anchor_verification"] if not a["present"]]
            print("\n锚点复核: " + (f"{len(report['anchor_verification'])} 个全部命中" if not missing else f"缺失 {missing}"))
        if "live_probes" in report:
            print("\nLive 探测（只读）:")
            for p in report["live_probes"]:
                brief = p.get("error") or p.get("body_head") or (str(p.get("facts"))[:220] if p.get("facts") else "")
                print(f"  - {p['probe']}: {p['status']} {brief}")
            print(f"  判定: {report['live_verdict']}")
        print()

    if args.strict_live and live_failed:
        print("STRICT-LIVE: 存在不可达探测面 → exit 2", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
