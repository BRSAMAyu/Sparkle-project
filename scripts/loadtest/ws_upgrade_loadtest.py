"""WS 升级链路压测 runner — WS-TICKET-DESIGN §6.2 S1-S5 五场景。

可重跑基线工具（落仓库的可复用脚本，非一次性探针）：

    python3 scripts/loadtest/ws_upgrade_loadtest.py --scenario s1 \
        --target 127.0.0.1 --port 18080 --jwt-secret "$WT320_JWT_SECRET" \
        --out /tmp/loadtest-results

有界执行纪律（16GB 本机，强制）：
- 并发 ≤ --inflight（默认 30），单场景加载时长 ≤ 60s，场景串行不叠加；
- 开跑前先探 target 健康（非 200 直接 BLOCKED）；
- SwapWatchdog 每 15s 自查 vm.swapusage，free < 800MB 立即中止并记录截断点；
- 打到的是「自己的」网关实例时才允许跑 S5（SIGTERM drain）——
  --gateway-pid 必须显式传入，缺省则 S5 跳过，防止误伤共享网关。

场景判定公式（§6.2）：token bucket 预算 = burst + rate_limit × 注入时长，
理论 429 率 = (注入总数 − 预算) / 注入总数；实测应 ≥ 理论值 × 95%。

预算参数口径（wt323 教训，WSQ-6 S2 红旗复盘）：预算必须按网关**运行时**桶参数算，
不能拍 viper 默认值——网关会加载 backend/gateway/.env（及仓库根 .env，优先级更高），
WS_TICKET_RATE_*/WS_UPGRADE_RATE_* 被覆盖时默认值口径即失真（曾把 10rps 桶
误判成 5rps 预算、得出 1.93×「超发」假红旗）。本脚本按网关 config.Load() 的
文件解析优先级自动取值（CLI 参数 > 根 .env > backend/gateway/.env > viper 默认）；
若网关再以**进程 env** 覆盖桶参数（压测侧不可见），必须用 --ticket-rate-rps 等
CLI 参数显式传入同一值，来源会记入各场景 JSON 的 judgments 供审计。
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ws_probe as wp  # noqa: E402

DEFAULT_INFLIGHT = 30
DEFAULT_SWAP_ABORT_MB = 800.0

# viper 默认值（backend/gateway/internal/config/config.go:650-651 及 WS_UPGRADE_* 默认）。
# 仅当 .env 链与 CLI 都未覆盖时使用。
TICKET_RATE_RPS_DEFAULT = 5.0
TICKET_RATE_BURST_DEFAULT = 10
UPGRADE_RATE_RPS_DEFAULT = 30.0
UPGRADE_RATE_BURST_DEFAULT = 60


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def resolve_limit_params(
    cli_rps: Optional[float],
    cli_burst: Optional[int],
    env_key_rps: str,
    env_key_burst: str,
    default_rps: float,
    default_burst: int,
    gateway_env_file: Optional[Path] = None,
) -> tuple[float, int, str]:
    """解析限流桶参数，镜像网关 config.Load() 的口径（config.go:732-754）。

    优先级：CLI 参数（须与网关进程 env 覆盖一致）> 仓库根 .env（网关 merge 时
    后读、优先生效）> backend/gateway/.env > viper 默认。
    返回 (rps, burst, source)；source 记入 JSON judgments 供审计。
    """
    if cli_rps is not None or cli_burst is not None:
        return (
            float(cli_rps if cli_rps is not None else default_rps),
            int(cli_burst if cli_burst is not None else default_burst),
            "cli-arg(网关进程env覆盖时必须显式传入)",
        )
    chain: list[Path] = []
    if gateway_env_file is not None:
        chain.append(gateway_env_file)
    else:
        repo_root = Path(__file__).resolve().parents[2]
        chain.append(repo_root / "backend" / "gateway" / ".env")  # 先读（低优先）
        chain.append(repo_root / ".env")  # 后读（高优先，镜像网关 merge 顺序）
    merged: dict[str, str] = {}
    for p in chain:
        merged.update(_parse_env_file(p))
    rps_raw = merged.get(env_key_rps)
    burst_raw = merged.get(env_key_burst)
    rps, burst = default_rps, default_burst
    if rps_raw is not None:
        rps = float(rps_raw)
    if burst_raw is not None:
        burst = int(burst_raw)
    source = "viper-defaults(config.go)"
    if rps_raw is not None or burst_raw is not None:
        source = "env-file(" + ",".join(str(p) for p in chain if p.exists()) + ")"
    return rps, burst, source

# 各场景 XFF 模拟源 IP（本机 lo0 无法绑多 IP；实例配置 TRUSTED_PROXIES=127.0.0.1
# 后 ClientIP 取 XFF，等价生产 LB 后语义。网段取 benchmark 保留段 198.18/15。）
XFF_S1 = "198.18.0.11"
XFF_S1_TIER2 = "198.18.0.12"
XFF_S2 = "198.18.0.21"
XFF_S3_NAT = "198.19.0.1"
XFF_S3_FLOOD = "198.19.0.2"
XFF_S4_POOL = [f"198.20.0.{i}" for i in range(1, 6)]
XFF_S5 = "198.21.0.1"


@dataclass
class ScenarioResult:
    name: str
    started_at: str
    params: dict
    totals: dict = field(default_factory=dict)
    status_dist: dict = field(default_factory=dict)
    metrics_delta: dict = field(default_factory=dict)
    metrics_note: str = ""
    latency: dict = field(default_factory=dict)
    judgments: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    truncated: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.host = args.target
        self.port = args.port
        self.inflight = args.inflight
        self.secret = args.jwt_secret
        self.issuer = args.jwt_issuer
        self.audience = args.jwt_audience
        self.out_dir = args.out
        os.makedirs(self.out_dir, exist_ok=True)
        self.wd = wp.SwapWatchdog(interval_s=15.0, abort_free_mb=args.swap_abort_mb)
        self.gw_pid = args.gateway_pid
        self.restart_cmd = args.gateway_restart_cmd
        gw_env = Path(args.gateway_env_file) if args.gateway_env_file else None
        self.ticket_rate_rps, self.ticket_rate_burst, self.ticket_rate_src = resolve_limit_params(
            args.ticket_rate_rps, args.ticket_rate_burst,
            "WS_TICKET_RATE_RPS", "WS_TICKET_RATE_BURST",
            TICKET_RATE_RPS_DEFAULT, TICKET_RATE_BURST_DEFAULT, gw_env,
        )
        self.upgrade_rate_rps, self.upgrade_rate_burst, self.upgrade_rate_src = resolve_limit_params(
            args.upgrade_rate_rps, args.upgrade_rate_burst,
            "WS_UPGRADE_RATE_RPS", "WS_UPGRADE_RATE_BURST",
            UPGRADE_RATE_RPS_DEFAULT, UPGRADE_RATE_BURST_DEFAULT, gw_env,
        )

    # ---------------- 基础设施 ----------------

    def preflight(self) -> bool:
        r = wp.ws_upgrade_probe(self.host, self.port, "/api/v1/health", timeout=5)
        ok = r.status == 200
        print(f"[preflight] GET /api/v1/health -> {r.status or r.error} ({'OK' if ok else 'BLOCKED'})")
        return ok

    def _metrics(self) -> dict:
        return wp.scrape_metrics(self.host, self.port)

    def _mint(self, sub: str, ttl: int = 600) -> str:
        return wp.mint_hs256_jwt(self.secret, sub, ttl_seconds=ttl, issuer=self.issuer, audience=self.audience)

    def _flood_tasks(
        self,
        count: int,
        rate: float,
        path_fn: Callable[[int], str],
        xff: str,
    ) -> tuple[list[Callable], list[float]]:
        """构造匀速节拍的升级探测任务组。"""
        tasks = []
        for i in range(count):
            path = path_fn(i)
            tasks.append(lambda p=path: wp.ws_upgrade_probe(self.host, self.port, p, xff=xff))
        deadlines = wp.paced_deadlines(rate, count)
        return tasks, deadlines

    @staticmethod
    def _summarize(name: str, results: list, params: dict, started_at: str) -> ScenarioResult:
        sr = ScenarioResult(name=name, started_at=started_at, params=params)
        dist: dict[str, int] = {}
        latencies = []
        for r in results:
            key = str(r.status) if r.status > 0 else ("err:" + r.error.split(":")[0] if r.error else "err")
            dist[key] = dist.get(key, 0) + 1
            if r.status > 0:
                latencies.append(r.elapsed_ms)
        sr.status_dist = {k: dist[k] for k in sorted(dist)}
        if latencies:
            latencies.sort()
            n = len(latencies)
            sr.latency = {
                "n": n,
                "p50_ms": round(latencies[int(n * 0.5)], 2),
                "p95_ms": round(latencies[min(int(n * 0.95), n - 1)], 2),
                "p99_ms": round(latencies[min(int(n * 0.99), n - 1)], 2),
                "mean_ms": round(statistics.fmean(latencies), 2),
            }
        sr.totals = {"dispatched": len(results)}
        return sr

    # ---------------- S1 未认证洪水（主验收） ----------------

    def s1(self) -> ScenarioResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        before = self._metrics()
        notes = []
        fake_sub = f"s1_fake_{int(time.time())}"

        def path_fn_t1(i: int, tier: str) -> tuple[str, str]:
            """返回 (path, payload_class)。"""
            mode = i % 3
            if mode == 0:
                return "/ws/chat", "no_cred"  # 无凭据
            if mode == 1:
                return "/ws/chat?token=" + wp.garbage_jwt(), "garbage_jwt"  # 垃圾 JWT
            return (
                "/ws/chat?token=" + self._mint(fake_sub + tier + str(i), ttl=120),
                "valid_signed_fake_jwt",  # 合法签名假用户（白盒凭据，见报告差异说明）
            )

        def run_tier(tier: str, rate: float, dur: float, xff: str) -> tuple[list, int, float]:
            count = int(rate * dur)
            paths: list[str] = []
            classes: list[str] = []
            for i in range(count):
                p, cls = path_fn_t1(i, tier)
                paths.append(p)
                classes.append(cls)
            tasks = [
                (lambda p=p: wp.ws_upgrade_probe(self.host, self.port, p, xff=xff))
                for p in paths
            ]
            deadlines = wp.paced_deadlines(rate, count)
            res, disp = wp.run_swarm(tasks, self.inflight, self.wd, deadlines)
            labeled = list(zip(classes, res))
            return labeled, disp, disp / rate

        # Tier-1：100 conn/s × 45s（时长≤60s 纪律）；Tier-2：500/s × 12s
        # （§6.2 的 1000×60 超本机时长纪律，全量口径留给生产 ECS）
        tier1, disp1, elapsed1 = run_tier("t1", 100.0, 45.0, XFF_S1)
        tier2, disp2, elapsed2 = ([], 0, 0.0)
        tier2_done = False
        if not self.wd.abort_event.is_set():
            tier2, disp2, elapsed2 = run_tier("t2", 500.0, 12.0, XFF_S1_TIER2)
            tier2_done = True
        if self.wd.abort_event.is_set():
            notes.append(self.wd.truncation_note)
        after = self._metrics()

        all_results = [r for _, r in tier1 + tier2]
        sr = self._summarize("S1_unauth_flood", all_results, {
            "tier1": f"100rps x 45s = {disp1}", "tier2": f"500rps x 12s = {disp2}",
            "tier2_done": tier2_done,
            "payloads": "no_cred/garbage_jwt/valid_signed_fake_jwt x 1/3",
            "xff": XFF_S1 + "/" + XFF_S1_TIER2,
        }, started_at)
        sr.totals["tier1_dispatched"] = disp1
        sr.totals["tier2_dispatched"] = disp2

        # 按载荷类别 × 档位 分桶（§6.2-S1 判定①只适用于未认证载荷类别）
        def dist_for(tier_data: list[tuple[str, wp.ProbeResult]], only: Optional[set] = None) -> dict:
            d: dict[str, int] = {}
            for cls, r in tier_data:
                if only and cls not in only:
                    continue
                k = str(r.status) if r.status > 0 else "err"
                d[k] = d.get(k, 0) + 1
            return {k: d[k] for k in sorted(d)}

        sr.totals["tier1_dist"] = dist_for(tier1)
        sr.totals["tier2_dist"] = dist_for(tier2)
        sr.totals["unauth_classes_dist"] = dist_for(
            tier1 + tier2, only={"no_cred", "garbage_jwt"}
        )
        sr.totals["valid_signed_class_dist"] = dist_for(
            tier1 + tier2, only={"valid_signed_fake_jwt"}
        )
        sr.metrics_delta = {
            "ws_upgrade_limited_total": wp.counter_delta(before, after, "ws_upgrade_limited_total"),
            "ws_connection_success_total": wp.counter_delta(before, after, "ws_connection_success_total"),
            "ws_connection_error_total": wp.counter_delta(before, after, "ws_connection_error_total"),
        }

        # 判定（按 §6.2 公式代入运行时参数；桶参数解析来源见 judgments）
        n429_t1 = dist_for(tier1).get("429", 0)
        n429_t2 = dist_for(tier2).get("429", 0)
        budget1 = self.upgrade_rate_burst + self.upgrade_rate_rps * elapsed1
        budget2 = self.upgrade_rate_burst + self.upgrade_rate_rps * elapsed2
        unauth = sr.totals["unauth_classes_dist"]
        n101_unauth = unauth.get("101", 0)
        sr.judgments = {
            "upgrade_success_unauth_classes": (
                "0 (101=0)" if n101_unauth == 0 else f"FAIL: 101={n101_unauth}"
            ),
            "tier1_429_rate": {
                "measured": round(n429_t1 / disp1, 4) if disp1 else None,
                "theoretical": round(max(0, disp1 - budget1) / disp1, 4) if disp1 else None,
                "dispatched": disp1, "limited": n429_t1,
            },
            "tier2_429_rate": {
                "measured": round(n429_t2 / disp2, 4) if disp2 else None,
                "theoretical": round(max(0, disp2 - budget2) / disp2, 4) if disp2 else None,
                "dispatched": disp2, "limited": n429_t2,
            },
            "penetration_rps_tier1": round((disp1 - n429_t1) / max(elapsed1, 0.001), 2),
            "penetration_rps_tier2": round((disp2 - n429_t2) / max(elapsed2, 0.001), 2),
            "upgrade_rate_rps": self.upgrade_rate_rps,
            "upgrade_rate_burst": self.upgrade_rate_burst,
            "upgrade_rate_param_source": self.upgrade_rate_src,
            "finding_auth_gap": (
                "valid_signed_fake_jwt 类别被网关放行 101（WsAuth 只验签名+黑名单，"
                "不查用户存在性）——§6.2-S1 判定①的『合法签名假 JWT 升级成功率 0%』"
                "在实现上不成立，需产品侧裁定（DB 存在性校验 vs 收紧判定口径）"
                if sr.totals["valid_signed_class_dist"].get("101", 0) > 0 else "none"
            ),
        }
        sr.notes = notes + [
            f"budget=burst{self.upgrade_rate_burst:g}+{self.upgrade_rate_rps:g}rps×注入时长（桶参数来源：{self.upgrade_rate_src}）",
            "渗透=未被429的请求（401/101），其中 401=被认证层拒绝、101=白盒凭据建连",
        ]
        return sr

    # ---------------- S2 单账号签发洪打 ----------------

    def s2(self) -> ScenarioResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        before = self._metrics()
        jwt = self._mint("s2_flood_user")
        rate, dur = 50.0, 30.0  # §6.2：1 账号 50 rps
        count = int(rate * dur)
        deadlines = wp.paced_deadlines(rate, count)
        tasks = [
            (lambda: wp.issue_ticket(self.host, self.port, jwt, xff=XFF_S2)) for _ in range(count)
        ]
        results, dispatched = wp.run_swarm(tasks, self.inflight, self.wd, deadlines)
        notes = []
        if self.wd.abort_event.is_set():
            notes.append(self.wd.truncation_note)

        # 非误伤检查：等 2s 回血后正常签 3 张票并全部建连成功
        normal_ok = None
        if not self.wd.abort_event.is_set():
            time.sleep(2)
            issued_ok = 0
            for _ in range(3):
                r = wp.issue_ticket(self.host, self.port, jwt, xff=XFF_S2 + "n")
                tk = wp.ticket_from_result(r)
                if r.status == 200 and tk:
                    conn = wp.ws_connect(self.host, self.port, wp.authed_ws_path(tk), xff=XFF_S2 + "n")
                    if conn.accepted:
                        issued_ok += 1
                        conn.close()
            normal_ok = f"{issued_ok}/3"

        after = self._metrics()
        sr = self._summarize("S2_single_account_issue_flood", results, {
            "user_rps": rate, "duration_s": dur, "xff": XFF_S2,
        }, started_at)
        sr.totals["dispatched"] = dispatched
        sr.totals["normal_traffic_not_harmed"] = normal_ok
        sr.metrics_delta = {
            "ws_ticket_issued_total": wp.counter_delta(before, after, "ws_ticket_issued_total"),
            "ws_upgrade_limited_total": wp.counter_delta(before, after, "ws_upgrade_limited_total"),
        }
        n200 = sr.status_dist.get("200", 0)
        n429 = sr.status_dist.get("429", 0)
        elapsed = dispatched / rate
        # 预算必须用网关运行时桶参数（.env 可能覆盖 viper 默认；wt323 复盘：
        # 曾因硬编码 5rps/burst10 而把 10rps 桶的正常收敛误判为 1.93× 超发红旗）
        budget = self.ticket_rate_burst + self.ticket_rate_rps * elapsed
        # 注意：api 组另有 15rps/burst30 限流先行计数，但其预算(480@30s)高于
        # ticket 层预算，429 应全部来自 ticket 层——若 200 数远超 ticket 层
        # 运行时预算则说明限流层 key 或顺序有问题，作为 RED FLAG 输出。
        sr.judgments = {
            "issued_200": n200,
            "rejected_429": n429,
            "ticket_layer_rate_rps": self.ticket_rate_rps,
            "ticket_layer_burst": self.ticket_rate_burst,
            "ticket_layer_param_source": self.ticket_rate_src,
            "ticket_layer_budget_theoretical": round(budget, 1),
            "issue_layer_breach": "RED FLAG: 200 数超过 ticket 层预算" if n200 > budget * 1.15 else "ok",
            "non_harm_check": normal_ok,
        }
        sr.notes = notes
        return sr

    # ---------------- S3 NAT 不误杀 ----------------

    def s3(self) -> ScenarioResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        before = self._metrics()
        notes = []
        n_users = 50  # §6.2：50 认证用户共享出口 IP，人均 2 conn/分钟
        nat_users = [f"s3_nat_user_{i}" for i in range(n_users)]
        nat_xff = XFF_S3_NAT

        # 阶段 A：50 用户各自以 2 conn/min 节奏的第一连（1 conn/user，50s 铺满）
        user_jwts = {u: self._mint(u) for u in nat_users}
        rate_a = n_users / 50.0  # ~1/s
        deadlines_a = wp.paced_deadlines(rate_a, n_users)

        def nat_task(i: int) -> Callable:
            def _t() -> wp.ProbeResult:
                jwt = user_jwts[nat_users[i]]
                r = wp.issue_ticket(self.host, self.port, jwt, xff=nat_xff)
                tk = wp.ticket_from_result(r)
                if r.status != 200 or not tk:
                    return wp.ProbeResult(status=r.status, error="ticket_issue_failed")
                return wp.ws_upgrade_probe(self.host, self.port, wp.authed_ws_path(tk), xff=nat_xff)
            return _t

        tasks_a = [nat_task(i) for i in range(n_users)]
        res_a, disp_a = wp.run_swarm(tasks_a, self.inflight, self.wd, deadlines_a)
        if self.wd.abort_event.is_set():
            notes.append(self.wd.truncation_note + " (phase A)")

        # 阶段 B：洪水从另一独立出口 IP（S1 口径：50/s×20s=1000，量级足以触发钳制）
        flood_res = []
        if not self.wd.abort_event.is_set():
            fr, fdur = 50.0, 20.0
            fc = int(fr * fdur)
            ftasks = [
                (lambda: wp.ws_upgrade_probe(self.host, self.port, "/ws/chat", xff=XFF_S3_FLOOD))
                for _ in range(fc)
            ]
            fdeadlines = wp.paced_deadlines(fr, fc)
            flood_res, _ = wp.run_swarm(ftasks, self.inflight, self.wd, fdeadlines)
            if self.wd.abort_event.is_set():
                notes.append(self.wd.truncation_note + " (phase B flood)")

        after = self._metrics()
        sr = self._summarize("S3_nat_no_false_kill", res_a, {
            "nat_users": n_users, "nat_xff": nat_xff, "flood_xff": XFF_S3_FLOOD,
            "flood_profile": "50rps x 20s (unauth, separate XFF IP)",
        }, started_at)
        sr.totals["nat_dispatched"] = disp_a
        flood_dist = {}
        for r in flood_res:
            k = str(r.status) if r.status > 0 else "err"
            flood_dist[k] = flood_dist.get(k, 0) + 1
        sr.totals["flood_dist"] = flood_dist
        sr.metrics_delta = {
            "ws_upgrade_limited_total": wp.counter_delta(before, after, "ws_upgrade_limited_total"),
            "ws_connection_success_total": wp.counter_delta(before, after, "ws_connection_success_total"),
        }
        nat_429 = sr.status_dist.get("429", 0)
        nat_401 = sr.status_dist.get("401", 0)
        nat_101 = sr.status_dist.get("101", 0)
        sr.judgments = {
            "nat_users_429_or_401": nat_429 + nat_401,
            "nat_users_connected": nat_101,
            "verdict": "PASS: NAT 用户 0 误杀" if (nat_429 + nat_401 == 0 and nat_101 == disp_a) else "CHECK",
            "flood_clamped": flood_dist.get("429", 0),
        }
        sr.notes = notes
        return sr

    # ---------------- S4 重连风暴 ----------------

    def s4(self) -> ScenarioResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        before = self._metrics()
        notes = []
        n_users = 100  # §6.2：100 认证客户端分布多 IP
        users = [f"s4_user_{i}" for i in range(n_users)]
        xff_of = {u: XFF_S4_POOL[i % len(XFF_S4_POOL)] for i, u in enumerate(users)}
        jwts = {u: self._mint(u) for u in users}

        def user_connect(u: str) -> wp.WSConn:
            r = wp.issue_ticket(self.host, self.port, jwts[u], xff=xff_of[u])
            tk = wp.ticket_from_result(r)
            if r.status != 200 or not tk:
                return wp.WSConn(accepted=False, status=r.status, error="ticket_issue_failed")
            return wp.ws_connect(self.host, self.port, wp.authed_ws_path(tk), xff=xff_of[u])

        # 阶段 A：全员建连（约 20/s 铺开，inflight≤30）
        conns: dict[str, wp.WSConn] = {}
        phase_a_tasks = [(lambda u=u: user_connect(u)) for u in users]
        deadline_a = wp.paced_deadlines(20.0, n_users)

        def phase_a() -> None:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.inflight) as pool:
                futs = [(u, pool.submit(user_connect, u)) for u in users]
                for idx, (u, fut) in enumerate(futs):
                    if deadline_a[idx] - (time.monotonic() - t0) > 0:
                        time.sleep(deadline_a[idx] - (time.monotonic() - t0))
                    try:
                        conns[u] = fut.result(timeout=60)
                    except Exception:  # noqa: BLE001
                        conns[u] = wp.WSConn(accepted=False, error="phase_a_failed")

        t0 = time.monotonic()
        phase_a()
        accepted_a = sum(1 for c in conns.values() if c.accepted)

        # 保持 3s 后全员断开（模拟断网），outage 10s（§6.2 为 30s，本机压缩并记录）
        time.sleep(3)
        for c in conns.values():
            c.close()
        outage_s = 10.0
        time.sleep(outage_s)

        # 阶段 B：6 连击退避重连（0.5s 步进指数退避，封顶 8s；§6.2 判定 15s 内）
        backoff_shots = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
        b429 = [0]  # 线程安全：仅在 pool 线程内 -1 号线程池串行计数不可靠，用列表累加
        reconnected = 0
        reconnect_times: list[float] = []
        shots_used: list[int] = []
        pending = list(users)

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.inflight) as pool:
            def reconnect(u: str) -> tuple[str, bool, float, int]:
                start = time.monotonic()
                for shot, delay in enumerate(backoff_shots):
                    if delay:
                        time.sleep(delay)
                    r = wp.issue_ticket(self.host, self.port, jwts[u], xff=xff_of[u])
                    if r.status == 429:
                        b429[0] += 1
                        continue
                    tk = wp.ticket_from_result(r)
                    if r.status != 200 or not tk:
                        continue
                    c = wp.ws_connect(self.host, self.port, wp.authed_ws_path(tk), xff=xff_of[u])
                    if c.accepted:
                        c.close()
                        return u, True, time.monotonic() - start, shot + 1
                    if c.status == 429:
                        b429[0] += 1
                return u, False, time.monotonic() - start, len(backoff_shots)

            futs = [pool.submit(reconnect, u) for u in pending]
            for fut in futs:
                u, ok, dur, shots = fut.result(timeout=120)
                if ok:
                    reconnected += 1
                    reconnect_times.append(dur)
                    shots_used.append(shots)

        after = self._metrics()
        sr = ScenarioResult(name="S4_reconnect_storm", started_at=started_at, params={
            "users": n_users, "xff_pool": XFF_S4_POOL,
            "phase_a_profile": "~20/s ticket+connect", "outage_s": outage_s,
            "backoff_shots": backoff_shots, "design_outage_s": 30,
        })
        sr.totals = {
            "phase_a_accepted": accepted_a,
            "reconnected": reconnected,
            "reconnect_429": b429[0],
            "mean_shots": round(statistics.fmean(shots_used), 2) if shots_used else None,
        }
        sr.latency = {
            "reconnect_p50_s": round(statistics.median(reconnect_times), 2) if reconnect_times else None,
            "reconnect_max_s": round(max(reconnect_times), 2) if reconnect_times else None,
        }
        sr.metrics_delta = {
            "ws_upgrade_limited_total": wp.counter_delta(before, after, "ws_upgrade_limited_total"),
            "ws_connection_success_total": wp.counter_delta(before, after, "ws_connection_success_total"),
            "ws_ticket_issued_total": wp.counter_delta(before, after, "ws_ticket_issued_total"),
        }
        sr.judgments = {
            "reconnect_429": b429[0],
            "all_within_15s": "PASS" if reconnect_times and max(reconnect_times) <= 15.0 else "CHECK",
            "verdict": (
                "PASS: 0×429 且全员重连"
                if b429[0] == 0 and reconnected == n_users
                else f"CHECK: reconnected={reconnected}/{n_users}, 429={b429[0]}"
            ),
        }
        sr.notes = notes + [
            f"outage 压缩为 {outage_s}s（设计 30s），重连判定口径不变",
        ]
        return sr

    # ---------------- S5 滚动发布 / drain ----------------

    def s5(self) -> ScenarioResult:
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        notes = []
        if not self.gw_pid:
            sr = ScenarioResult(name="S5_rolling_drain", started_at=started_at, params={})
            sr.notes = ["SKIPPED: 未提供 --gateway-pid（保护共享网关：只有自有实例才能 drain）"]
            sr.judgments = {"verdict": "SKIPPED"}
            return sr
        n_conns = self.inflight  # 并发纪律上限 30（§6.2 为 500 live conn，缩比记录）
        users = [f"s5_user_{i}" for i in range(n_conns)]
        jwts = {u: self._mint(u, ttl=900) for u in users}

        # 1) 两批票：connect_tickets 供建连（会被单次核销消费），reserve_tickets
        #    预签未用、专供重启后重连（§6.2-S5「发布窗口前签发的票跨重启可用」）
        def issue_batch(u: str) -> tuple[str, str]:
            r1 = wp.issue_ticket(self.host, self.port, jwts[u], xff=XFF_S5)
            r2 = wp.issue_ticket(self.host, self.port, jwts[u], xff=XFF_S5)
            return wp.ticket_from_result(r1), wp.ticket_from_result(r2)

        connect_tickets: dict[str, str] = {}
        reserve_tickets: dict[str, str] = {}
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.inflight) as pool:
            for u, fut in [(u, pool.submit(issue_batch, u)) for u in users]:
                try:
                    t1, t2 = fut.result(timeout=30)
                    if t1:
                        connect_tickets[u] = t1
                    if t2:
                        reserve_tickets[u] = t2
                except Exception:  # noqa: BLE001
                    continue
        notes.append(f"tickets: connect={len(connect_tickets)} reserve={len(reserve_tickets)}")

        # 2) 建立存活连接
        live: dict[str, wp.WSConn] = {}

        with ThreadPoolExecutor(max_workers=self.inflight) as pool:
            def connect(u: str) -> tuple[str, wp.WSConn]:
                return u, wp.ws_connect(
                    self.host, self.port, wp.authed_ws_path(connect_tickets[u]), xff=XFF_S5
                )
            for u, fut in [(u, pool.submit(connect, u)) for u in users if u in connect_tickets]:
                try:
                    _, c = fut.result(timeout=60)
                    if c.accepted:
                        live[u] = c
                except Exception:  # noqa: BLE001
                    continue
        notes.append(f"live conns: {len(live)}/{len(connect_tickets)}")

        # 3) SIGTERM 触发 drain（wt275 语义），客户端读 close 帧码
        drain_t0 = time.monotonic()
        try:
            os.kill(self.gw_pid, signal.SIGTERM)
        except ProcessLookupError:
            notes.append("gateway pid already gone before SIGTERM")
        close_codes: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=self.inflight) as pool:
            def read_close(u: str, c: wp.WSConn) -> tuple[str, Optional[int]]:
                frame = c.recv_frame(timeout=30)
                return u, (c.close_code if frame and frame[0] == 0x8 else None)

            futs = [(u, pool.submit(read_close, u, c)) for u, c in live.items()]
            for u, fut in futs:
                try:
                    _, code = fut.result(timeout=35)
                    close_codes[u] = code if code is not None else -1
                except Exception:  # noqa: BLE001
                    close_codes[u] = -1
        drain_close_s = time.monotonic() - drain_t0

        # 4) 等端口释放 → 重启（滚动发布语义：新进程顶上，Redis 态保留）
        def port_closed() -> bool:
            s = socket.socket()
            s.settimeout(1)
            try:
                s.connect((self.host, self.port))
                return False
            except OSError:
                return True
            finally:
                s.close()

        waited = 0.0
        while waited < 60 and not port_closed():
            time.sleep(1)
            waited += 1
        notes.append(f"port released after ~{waited}s")

        restarted = False
        if self.restart_cmd:
            subprocess.run(self.restart_cmd, shell=True, check=False)
            deadline = time.time() + 60
            while time.time() < deadline:
                r = wp.ws_upgrade_probe(self.host, self.port, "/api/v1/health", timeout=2)
                if r.status == 200:
                    restarted = True
                    break
                time.sleep(1)
        notes.append(f"restarted={restarted}")

        # 5) 用重启前签发、未消费的预签票重连（0 429 期望）+ 新票签发可用
        reconn_ok = 0
        reconn_429 = 0
        reconn_401 = 0
        if restarted:
            with ThreadPoolExecutor(max_workers=self.inflight) as pool:
                def reconnect(u: str) -> int:
                    if u not in reserve_tickets:
                        return 0
                    c = wp.ws_connect(
                        self.host, self.port, wp.authed_ws_path(reserve_tickets[u]), xff=XFF_S5
                    )
                    if c.accepted:
                        c.close()
                        return 1
                    if c.status == 429:
                        return 429
                    if c.status == 401:
                        return 401
                    return 0
                futs = [pool.submit(reconnect, u) for u in reserve_tickets]
                for fut in futs:
                    v = fut.result(timeout=60)
                    if v == 1:
                        reconn_ok += 1
                    elif v == 429:
                        reconn_429 += 1
                    elif v == 401:
                        reconn_401 += 1
            fresh = wp.issue_ticket(
                self.host, self.port, self._mint("s5_post_restart"), xff=XFF_S5
            )
            fresh_issue_ok = fresh.status == 200
        else:
            fresh_issue_ok = None

        code_dist: dict[str, int] = {}
        for code in close_codes.values():
            key = str(code)
            code_dist[key] = code_dist.get(key, 0) + 1
        sr = ScenarioResult(name="S5_rolling_drain", started_at=started_at, params={
            "live_conns": len(live), "design_live_conns": 500,
            "xff": XFF_S5, "gateway_pid": self.gw_pid,
            "note": "live conn 缩比到并发纪律上限 30；协议判定不变；"
                    "metrics 计数器随进程重启清零，S5 的 metrics_delta 不可跨重启比较",
        })
        sr.totals = {
            "reserve_tickets": len(reserve_tickets),
            "live_accepted": len(live),
            "close_code_dist": code_dist,
            "drain_close_wall_s": round(drain_close_s, 2),
            "post_restart_reconnect_ok": reconn_ok,
            "post_restart_reconnect_429": reconn_429,
            "post_restart_reconnect_401": reconn_401,
            "fresh_issue_ok": fresh_issue_ok,
        }
        sr.metrics_delta = {}
        sr.metrics_note = (
            "跨重启计数器清零（Prometheus 进程内计数），S5 不做 delta 判定；"
            "跨重启的 Redis 态由 reserve ticket 重连成功率直接证明"
        )
        dominant_close = max(code_dist, key=lambda k: code_dist[k]) if code_dist else None
        sr.judgments = {
            "close_frame_receipt": f"{len(close_codes)}/{len(live)}",
            "dominant_close_code": dominant_close,
            "close_code_semantics": (
                "1001=CloseGoingAway（live conn 的 drain 关闭路径，符合 §6.2-S5）；"
                "1013=CloseTryAgainLater 仅用于 draining 后拒绝新注册（不同语义路径）"
                if dominant_close == "1001" else f"CHECK: dominant={dominant_close}"
            ),
            "reconnect_429": reconn_429,
            "reconnect_401_reserved_unconsumed": reconn_401,
            "ticket_survives_restart": (
                "PASS" if restarted and reconn_ok == len(reserve_tickets)
                else ("CHECK" if restarted else "SKIPPED(restart failed)")
            ),
        }
        sr.notes = notes
        return sr

    # ---------------- 执行入口 ----------------

    def run(self, scenarios: list[str]) -> list[ScenarioResult]:
        if not self.preflight():
            print("BLOCKED: gateway preflight failed", file=sys.stderr)
            return []
        self.wd.start()
        out = []
        for name in scenarios:
            fn = getattr(self, name, None)
            if fn is None:
                continue
            print(f"[run] ===== {name} start =====", flush=True)
            sr = fn()
            print(f"[run] ===== {name} done: {json.dumps(sr.judgments, ensure_ascii=False)}", flush=True)
            out.append(sr)
            with open(os.path.join(self.out_dir, f"{sr.name}.json"), "w", encoding="utf-8") as f:
                f.write(sr.to_json())
            if self.wd.abort_event.is_set():
                print(f"[run] SWAP ABORT — 后续场景不跑: {self.wd.truncation_note}", file=sys.stderr)
                break
        swap_log = self.wd.stop()
        with open(os.path.join(self.out_dir, "swap_watchdog.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(swap_log) + ("\n" + self.wd.truncation_note if self.wd.truncation_note else ""))
        return out


SCENARIOS = {
    "s1": "S1_unauth_flood",
    "s2": "S2_single_account_issue_flood",
    "s3": "S3_nat_no_false_kill",
    "s4": "S4_reconnect_storm",
    "s5": "S5_rolling_drain",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=list(SCENARIOS) + ["all"], default="all")
    ap.add_argument("--target", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=18080)
    ap.add_argument("--inflight", type=int, default=DEFAULT_INFLIGHT)
    ap.add_argument("--jwt-secret", default=os.environ.get("WT320_JWT_SECRET", ""),
                    help="与目标网关一致的 JWT_SECRET（HS256 fallback 校验用）；勿写死进仓库")
    ap.add_argument("--jwt-issuer", default="sparkle-gateway")
    ap.add_argument("--jwt-audience", default="sparkle-app")
    ap.add_argument("--swap-abort-mb", type=float, default=DEFAULT_SWAP_ABORT_MB)
    ap.add_argument("--gateway-pid", type=int, default=None,
                    help="S5 专用：自有网关实例 PID（SIGTERM drain）；缺省跳过 S5")
    ap.add_argument("--gateway-restart-cmd", default=None, help="S5 专用：重启命令（shell）")
    ap.add_argument("--gateway-env-file", default=None,
                    help="网关 .env 路径（解析限流桶参数用）；缺省按仓库根 .env > backend/gateway/.env 链解析")
    ap.add_argument("--ticket-rate-rps", type=float, default=None,
                    help="签发口桶速率（WS_TICKET_RATE_RPS）。仅当网关以进程 env 覆盖该值时必须显式传入")
    ap.add_argument("--ticket-rate-burst", type=int, default=None,
                    help="签发口桶容量（WS_TICKET_RATE_BURST）。仅当网关以进程 env 覆盖该值时必须显式传入")
    ap.add_argument("--upgrade-rate-rps", type=float, default=None,
                    help="握手口桶速率（WS_UPGRADE_RATE_RPS）。仅当网关以进程 env 覆盖该值时必须显式传入")
    ap.add_argument("--upgrade-rate-burst", type=int, default=None,
                    help="握手口桶容量（WS_UPGRADE_RATE_BURST）。仅当网关以进程 env 覆盖该值时必须显式传入")
    ap.add_argument("--out", default="/tmp/ws_loadtest_results")
    args = ap.parse_args()

    if not args.jwt_secret:
        print("需要 --jwt-secret 或 WT320_JWT_SECRET（S1 假签名 JWT/S2-S5 认证流需要）", file=sys.stderr)
        return 2
    if args.inflight > 30:
        print("并发纪律上限 30（任务卡强制），拒绝更大的 --inflight", file=sys.stderr)
        return 2

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    runner = Runner(args)
    results = runner.run(names)
    ok = bool(results) and not runner.wd.abort_event.is_set()
    print("\n=== RESULTS DIR:", args.out, "===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
