# WT320 · WSQ-6 有界压测基线卡

> 原 worker（wt320）因账号 5 小时额度上限阵亡于执行前夜；脚本遗产（ws_probe.py 18KB + ws_upgrade_loadtest.py 34KB）
> 由主会话抢救并完成执行。credit: wt320 起草（含 SwapWatchdog 自杀设计与 S1-S5 场景实现），主会话收尾跑数。

## 执行环境

- 专属网关实例：`/tmp/gw18080`（HEAD 构建），PORT=18080，`WS_TICKET_TTL_SECONDS=120`（覆盖 dev .env 旧值 3600——新代码对 TTL>300 启动 Fatal，见「事故与发现」）
- 共享栈零接触（8080/PG/Redis 只读连接）；SwapWatchdog 全程武装（<800M 自杀，未触发）

## 五场景结果

| 场景 | 结果 | 关键数据 |
|---|---|---|
| S1 未认证洪泛 | **PASS** | tier1 限流率实测 0.6869 vs 理论 0.6867；tier2 0.93=0.93；零升级穿透；渗透 RPS 31/35 |
| S2 单账号换票洪泛 | **RED FLAG** | 200 签发 309 次 > 票层理论预算 160（≈1.93×）；non-harm 3/3；见「真发现」 |
| S3 NAT 不误杀 | **PASS** | 50 慢速 NAT 用户 0×429/401 全连通；洪水被钳 341 |
| S4 重连风暴 | **PASS** | 0×429，全员 15s 内重连 |
| S5 滚动排空 | 未跑 | 需重启编排（--gateway-restart-cmd），留后续窗口 |

## 真发现（S2 RED FLAG）

单账号+单出口 IP 的换票洪泛下，签发层放行 309×200，为理论预算（160/窗口）的 1.93 倍。
可能性：实现按窗口边界重置计数、或预算口径（per-user vs per-IP）与设计模型不一致。
**产品风险**：票层是 WS 入口前最后一道预算，超发≈放大认证后的连接面。建议开 C 线卡对照 WSQ-2 设计逐条核对票层限流实现。

## 事故与发现（执行过程）

1. **僵尸网关陷阱**：wt320 阵亡时其 21:32 启动的 `./gateway_bin`（无 .env、默认密钥）仍占 18080；主会话三次启动均静默让位，所有探针打到僵尸上——一度伪装成「新代码 auth 全断」S1 级回归（实为僵尸用默认密钥验真票必 401）。教训：**端口探活必须核对监听进程 PID/启动时间，agent 阵亡清点必须含其拉起的后台进程**。
2. **dev .env TTL 隐雷**：`backend/gateway/.env` 的 `WS_TICKET_TTL_SECONDS=3600` 超新代码 `WS_TICKET_TTL_SECONDS_MAX=300` 上限——**当前 dev 栈一旦重启网关即 Fatal 死**（8080 现存活的是旧二制）。已就地把 .env 改为 120。生产/云端 bootstrap 的 env 装配必须同步此口径。
3. 8080 共享网关与本测 HEAD 二制的 token 链交叉验证：同票 8080/18080 双 200（含 users/me+ticket），主代码无回归。

## 基线数据与阈值提案

- `ws_upgrade_limited_total` 告警阈值提案：S1 口径下 tier1 限流占比稳定 ≈0.687、tier2 ≈0.93（实测=理论逐位吻合）。
  提案：**5 分钟窗口 limited_total > 8000（≈S1 tier1 洪泛强度的 80%）触发 warning，>16000 critical**；
  S3 场景 healthy 基线 = NAT 慢速用户零命中（limited_total≈0），误报余量充足。
- 本机有界基线（inflight≤30、场景串行）与生产 ECS 的换算局限：本机 loopback 无真实网络栈排队，
  绝对 RPS 不可平移；**限流命中率、误杀率、穿透率是结构指标可平移**。

## 复跑

```bash
WT320_JWT_SECRET=<secret> python3 scripts/loadtest/ws_upgrade_loadtest.py --scenario s1 --port 18080
# 前置：backend/gateway 目录起专属实例 PORT=18080 WS_TICKET_TTL_SECONDS=120
```
