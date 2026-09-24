# WT323 · WSQ-6 S2 红旗复核：换票层限流预算「超发」实为压测脚本口径错位

> 2026-09-24。C 线真缺陷核对卡（无正式卡面，任务卡即卡面）。
> 结论先行：**网关限流实现零缺陷**；WSQ-6 压测基线的 S2「1.93× 超发」是
> **脚本用 viper 默认值（5rps/burst10）推算理论预算、而网关运行时被
> `backend/gateway/.env` 覆盖为 10rps** 导致的测量口径错位。已修脚本并对复跑收敛闭环。

## 一、base / final SHA

- base：`1c5f2d8d56af5645a3a9718b0d6894e49befc90f`（main，worktree 分支起点）
- 代码+证据提交：`41c3d19c0c5a61f535a9c490e6fc7b9104c97903`
  （changes.patch 即该点的 `git diff --binary main...HEAD` 归档）
- final：本分支 `wt323-s2-ticket-budget` HEAD（含本报告与 changes.patch 归档提交）

## 二、根因（file:line）

**超发判定的理论模型错位，而非限流实现欠执行。** 证据链：

1. **判空模型硬编码默认值**：`scripts/loadtest/ws_upgrade_loadtest.py` 修前 L301
   `budget = 10 + 5 * elapsed  # ticket 层默认 5rps/burst10`——取的是 viper 默认
   （`backend/gateway/internal/config/config.go:650-651`）。
2. **运行时被 .env 覆盖**：主仓 `backend/gateway/.env`（gitignored 运行时配置）含
   `WS_TICKET_RATE_RPS=10`。网关 `config.Load()`（config.go:732-754）从 cwd 解析
   .env 并让文件值覆盖 viper 默认 → WT320 专属实例的实际桶参数是 **10rps/burst10**。
3. **运行时预算 = burst10 + 10rps×30s = 310**，实测签发 309 = 预算的 **99.7%**——
   是完全收敛的 token bucket，根本不存在 1.93× 超发。160 的「理论预算」从未是
   该实例的预算。
4. **机制级逐位复现（最小 Go 测试）**：
   `backend/gateway/internal/middleware/s2_ticket_budget_repro_test.go`
   （miniredis + 虚拟时钟 + 与 S2 相同的到达过程 1500×20ms）：
   - rate=10/burst10 → 确定性产出 **309**（与压测实测逐位一致）；
   - rate=5/burst10 → 产出 159-160（设计默认模型成立）。
   同一套 `distributedTokenBucketScript`（distributed_rate_limiter.go:47-82），
   参数唯一决定预算——排除「窗口边界重置 / per-user vs per-IP 口径错位 /
   refill 算法差异 / 并发竞态」全部候选（S1 场景 tier1/tier2 实测=理论逐位吻合
   也早已证明该实现无算法性泄漏）。

旁证：per-user 键口径正确（setup.go:585-589 authMiddleware 之后挂
`HybridRateLimitMiddlewareSimple(5.0/10.0 默认)`，键=`user_id:POST:/api/v1/ws/ticket`，
rate_limit.go:276-284）；api 组 15rps/burst30 前置限流预算 480@30s，不构成约束。

## 三、修法

按任务卡分支裁定：**实现合理、测量模型错 → 修测量侧并论证，产品代码零改动**。

- `scripts/loadtest/ws_upgrade_loadtest.py`：
  - 新增 `resolve_limit_params()`：镜像网关 config.Load() 的解析优先级
    （CLI 参数 > 仓库根 .env > backend/gateway/.env > viper 默认），
    S1（WS_UPGRADE_RATE_*）与 S2（WS_TICKET_RATE_*）预算一律用解析后的运行时参数；
  - 新增 CLI `--ticket-rate-rps/--ticket-rate-burst/--upgrade-rate-rps/--upgrade-rate-burst/
    --gateway-env-file`：网关以**进程 env** 覆盖桶参数时压测侧不可见，必须显式传入同一值；
  - 判定 JSON 落审计字段：`ticket_layer_rate_rps / ticket_layer_burst /
    ticket_layer_param_source`（S1 同理），红旗判定公式与 1.15 松紧不变。
- 新增回归钉 `s2_ticket_budget_repro_test.go`（虚拟时钟确定性测试，0.2s）：
  两种参数口径下预算=burst+rate×窗口，防止未来有人把「参数-预算」关系改坏。

## 四、红测 → 绿测 + 复跑数据对比

**红（复现实测行为）**：Go 虚拟时钟测试 rate=10/burst10 → **309** 逐位复现
WT320 实测；对照 legacy 160-模型线 184，超线正是 WT320 报的红旗形态——但同测
rate=5/burst10 → 159-160 证明实现无泄漏，309 完全由参数解释。

**绿（复跑收敛，专属网关 18080，与 WT320 同构：cwd 加载同一 .env，CLI 只覆盖
PORT/TTL；Redis/PG/MinIO 连共享栈只读业务写入）**：

| 复跑 | 网关运行时桶参数 | dispatched | issued 200 | 429 | 理论预算（修后脚本） | 判定 |
|---|---|---|---|---|---|---|
| WT320 原始 | .env 10rps/burst10（未识别） | 1500 | 309 | 1191 | ~~160（错）~~ | ~~RED FLAG~~ |
| **Run A**（复现 as-was） | .env 10rps/burst10 | 1500 | **309** | **1191** | 310（env-file 来源） | **ok** |
| **Run B**（设计默认） | CLI 覆盖 5rps/burst10 | 1500 | **159** | 1341 | 160（cli-arg 来源） | **ok** |

- Run A 与 WT320 原始数据**逐位一致**（309/1191/issued_total Δ312），根因实证闭合；
- Run B 证明设计默认口径（§3.1 的 5rps/burst10）下同样收敛（159 ≤ 160），
  viper CLI env > .env 优先级亦经此验证；
- non-harm 检查两轮均 3/3；SwapWatchdog 全程武装（free 919-991MB，未触发 800M 熔断）。
- 证据：`S2_runA_env10rps_issued309.json`、`S2_runB_cli5rps_issued159.json`、
  `swap_watchdog.log`；Go 测试：`go test ./internal/middleware/` 全绿（8.4s）。

## 五、遗留与风险

1. **dev .env 与设计默认漂移（未修，主仓只读）**：`backend/gateway/.env` 的
   `WS_TICKET_RATE_RPS=10` 高于设计默认 5（WS-TICKET-DESIGN §3.1）。对生产无影响
   （gitignored 本机文件），但**任何以该 .env 起实例的压测/联调都必须知道实际桶速是 10**。
   建议主会话裁定：改回 5，或接受「dev 提速」并在 .env.example 注释标注差异。
   修后脚本无论哪种口径都会正确判定。
2. **压测结果可平移性不变**：本机 loopback 的绝对 RPS 不可平移生产（WT320 报告
   已述），本次修复改变的是判定模型的正确性，不影响该局限。
3. **脚本 CLI 覆盖参数可能被误用**：若操作者传入与网关实际值不符的
   --ticket-rate-rps，判定会错——help 文本与 JSON `param_source` 已显式提示
   「须与网关实际值一致」，判定时先看 source 字段。
4. **小观察（不阻塞）**：S2 non-harm 探针的 `XFF_S2+"n"`（"198.18.0.21n"）并非
   合法 IP，依赖网关 XFF 解析的容错行为，建议后续卡改用独立合法 IP（如 198.18.0.22）。
5. **产品代码零改动**：S1/S3/S4 基线数据与其网关行为完全不受影响（无产品 diff；
   S1 预算注释行的参数来源字段为增量，公式不变）。

## 六、收工清单

- [x] 专属网关进程杀净（Run A PID 36175 / Run B PID 36579，18080 已释放，无残留）
- [x] /tmp/wt323-gw18080 自清
- [x] rule guards exit 0（见提交前执行记录）
- [x] 未动主仓任何文件（.env/Redis/PG/MinIO 只读或用 /tmp 副本）
