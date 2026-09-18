# P3 清扫报告 · 网关批（GW-P2-4 落地 + GW-P3 族 + GW 移交 + R2-08 网关侧）

- 清扫员：P3 清扫员·网关批（恢复重派）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt2`（main@47db4816，未 commit）
- 日期：2026-09-18
- 补丁：[p3-sweep-gateway.patch](p3-sweep-gateway.patch)（`git add -A && git diff --cached` 产物，gen/ 无改动）
- 验证协议：`CGO_ENABLED=0 go vet ./...` 零输出；`SECRET_KEY=x JWT_SECRET=test-secret-0123456789abcdef CGO_ENABLED=0 go test <pkg> -count=1` 逐包（一次一个进程）；-race 仍因 CGO_ENABLED=0 铁律不可用

---

## 0. 总览

| 批次 | 项数 | 结果 |
|---|---|---|
| ★GW-P2-4 产品决策落地 | 1 | ✅ 有界降级全量落地（红-绿双证） |
| GW-P3-1..7（round1/05-fixes.md 剩余） | 7 | ✅ 5 代码修复 + 2 注释契约（按报告判词） |
| GW-3/6/7/9（round2/05-r2-fixes.md 移交） | 4 | ✅ 全部修复（GW-3 含同型 Run 热旋修复） |
| R2-08 网关侧 P3（08-r2-fixes.md §5） | 17 条死路由 + 守卫 | ✅ 16 删 + 1 改方法 + BM 守卫红-绿 |
| **合计** | **29 项处置** | 全部闭环，守卫套件全绿（含新 BM） |

未做（超出授权/跨仓，移交清单见 §6）。

---

## 1. ★GW-P2-4 配额 Redis 故障「有界降级」（最高优先，产品决策 2026-09-18）

决策依据：`系统审查/漏洞台账.md` 末节 + 漏洞台账「2026-09-18 产品决策落定」。旧形态：Redis 加载日用量失败 → `dailyUsageStart=0` 且 `RecordUsageSegment` 同样失败 → 中流配额闸口恒不触发 = 无界 fail-open。

**实现**（三件套）：
1. `internal/service/quota_fallback.go`（新增）：`QuotaLocalFallback`——**实例级**近似日计数硬上限，默认 **50/实例/日**；单字 `atomic.Int64` CAS（高 32 位=UTC 日、低 32 位=当日计数）实现「atomic + 当日重置」；达限后计数器饱和（拒绝不再自增，杜绝 32 位回绕）；env `QUOTA_LOCAL_FALLBACK_DAILY_LIMIT` 可覆盖（构造时读取，非法值回退默认）。
2. `internal/metrics/ws_metrics.go`：新增 `sparkle_quota_local_fallback_active` gauge（1=降级中/0=Redis 健康）；保留 `sparkle_quota_daily_usage_load_errors_total`（帮助文案同步改为降级语义）。
3. `internal/handler/chat_orchestrator_chatflow.go`（配额加载分支）：加载失败 → 打点 + gauge=1 + `quotaFallback.Allow()`；**未获准（第 51 次）在流开始前拒绝**，envelope/protobuf 走 `resource_exhausted`，legacy 走 `message_nack`，`error_code=quota_exceeded`（客户端既有配额 UX 复用），message 明示 `service degraded: per-instance fallback limit reached`；Redis 恢复后任一成功加载把 gauge 归零（自愈 disarm）。

**红-绿**（`quota_fallback_test.go`，51 次真实 WS 连接）：
- RED（接线前）：Redis 故障注入（关停 miniredis）下第 51 次仍被放行（`service_unavailable` 而非 `quota_exceeded`），gauge 恒 0 —— FAIL（73s 旧形态跑证）。
- GREEN：第 1..50 次放行、第 51 次 `error_code=quota_exceeded` —— PASS（8.4s）；gauge 1→0 转换测试 PASS（0.5s）。
- 服务单测 4 项（限额/当日重置/并发恰 50 次准入/env 覆盖）全绿。

**语义边界（记录在案）**：N 实例部署时有效上限为 N×50（实例级近似的固有属性，靠 `sparkle_quota_local_fallback_active` 告警缓解）；降级期按「次」计而非 token（Redis 不可用时 token 计量本身不可用）；免费模型跨层降级为协调者 follow-up（决策原文）。

---

## 2. GW-P3-1..7（round1/05-fixes.md §3 剩余清单）

| ID | 处置 | 证据 |
|---|---|---|
| GW-P3-1 限流键可污染 | `rate_limit.go` `normalizeRateLimitRoutePath` 重写：wildcard=模板+截断段数（cap 8）；NoRoute=固定前 3 段+段数——不可信后缀不再造桶，同深度后缀同桶，`/settings` 与 `/settings/ai-usage` 段数不同仍分桶 | RED：新测 suffix A/B 同桶断言在旧实现 FAIL；GREEN：`rate_limit_bucket_test.go` 5 断言全绿；旧用例 `uses_concrete_request_path...` 按新契约改写 |
| GW-P3-2 内网白名单缺省静默跳过 | `internal_ip_whitelist.go`：构造时（生产且空表）`[SECURITY][WARN]` 启动告警一次；运行时放行语义不变（静态 key 仍是闸门） | RED：日志捕获测试旧实现 FAIL（无告警）；GREEN：`internal_ip_whitelist_gap_test.go` 3 断言（prod 告警/dev 静默/配置后静默）+ 放行行为钉死 |
| GW-P3-3 gRPC 4xx 透传契约 | `grpcStreamErrorDetails` 加契约注释：4xx 类引擎 message 视为可对外（仅截断），引擎侧必须保持人读校验消息无内部细节；5xx/unknown 仍掩蔽 | 注释即修复（报告判词「维持，加注释」） |
| GW-P3-4 dedup 无超时 | `websocket_proxy.go`：`context.WithTimeout(200ms)`（`wsDedupCheckTimeout`）；超时/出错照常转发（dedup 是优化不是正确性闸门） | 行为红-绿：`websocket_proxy_dedup_test.go` 用 ctx-aware redis hook 制造 2s 停顿——旧实现（Background ctx）回声 1.5s 内不到 FAIL；新实现 203ms 转发 PASS |
| GW-P3-5 重连限流非原子 | `checkReconnectAllowed`+`recordReconnectAttempt` 合并为单锁 `checkAndRecordReconnect`（检查+记账+封禁一步），调用点/旧测试同步迁移 | 确定性 RED：旧对在最后一个配额槽位上双观察者互锁复现（双 true + 计数溢出 11>10，`zz_red` 临时测试证红后删除）；GREEN：32 并发恰 10 次准入 + 窗口重开语义 PASS |
| GW-P3-6 tokens gauge 无语义 | `distributed_rate_limiter.go`：`rate_limiter_tokens_current` gauge → `rate_limiter_tokens_remaining` histogram（0..1000 桶），per-request remaining 全键混采=容量压力信号，不再伪称 per-key 状态 | `distributed_rate_limiter_tokens_test.go`：限流器 3 次请求后直方图样本数增长 PASS（旧 gauge 形态无此观测面，编译级红） |
| GW-P3-7 outbox 非事务 | 按报告判词「无需改动」：`outbox/publisher.go` 加 at-least-once 交付契约注释（publish→mark 崩溃窗口重放；SKIP LOCKED 多实例安全）；消费端 `projection/handlers.go` 包注释加幂等要求（LastProcessedPosition 限制重放窗但不豁免幂等） | 注释即修复 |

## 3. GW-3/6/7/9（round2/05-r2-fixes.md §3 移交清单）

### GW-3（R2-GW-3，P2）file 订阅者 recover 后活性丢失 — ✅
- `file_event_subscriber.go`：新增 `RunWithRestart(ctx)`——panic（`runOnce` recover 转普通错误）与终态错误统一走「计数 → 指数退避 250ms→5s 封顶 → 重启」；健康运行 >1min 重置退避；ctx 取消即退出（非故障）。
- 指标：`sparkle_file_event_subscriber_restarts_total`（每次重启 +1，降级窗口可观测可告警）。
- `setup.go` goroutine 改走 `RunWithRestart`（GW-P0-1 recover 语义升级为「recover 即重启」）。
- **同型缺陷一并修**：旧 `Run` 对 `ReceiveMessage` 错误是 warn+continue——Redis 关停时拨号立即失败 = 热旋刷日志；现改为把终态错误交还重启循环（重试策略单点化）。
- **shutdown 缺陷一并修（新发现 #2）**：go-redis `ReceiveMessage` 建连后不响应 ctx 取消——`Run` 内 watcher 监听 ctx → `pubsub.Close()` 解堵（watchDone 防泄漏）；修复前 `cancel()` 后 goroutine 永不退出（调试测试实证 >3s），修复后 58µs 退出。
- 红绿：`file_event_subscriber_restart_test.go`——Redis 关停期重启计数增长（旧实现计数恒 0，红态在第一轮真实跑出）→ `mr.Restart()` 后自动恢复投递、`cancel` 干净退出，全绿。

### GW-6 双 drain 各拿满额 deadline — ✅
- `cmd/server/main.go`：提取 `drainWebSocketPhases`——两 drain 共享一个绝对 deadline，第二阶段只拿剩余预算（`remainingDrainBudget` 负值归零）；合计等待 ≤ T/3（旧最坏 2T/3）。
- 注意点：`Registry()` 返回具体指针，先判 typed-nil 再入接口（interface 装箱后 nil 检查失效）。
- `main_drain_test.go`：两阶段授予单调不增、总量受 400ms 预算约束、负预算归零，PASS。

### GW-7 fire-and-forget 扇出无上限 — ✅（两处族全修）
- `chat_history.go`：backfill 走 `startBackfill`——信号量 cap 4 + `backfillWg`；满载丢弃（纯缓存预热，下次读自愈）；`Stop()` 现在 `backfillWg.Wait()`（不再遗弃在飞 backfill）。覆盖 :475 消息回填与 :727 会话回填两个点。
- `ab_test_middleware.go`：`recordMetricBounded`——cap 8 信号量，满载丢弃（best-effort 遥测）；覆盖 latency 与 success 两个打点（原每请求 2 goroutine）。
- 测试：`chat_history_backfill_test.go`（有槽即跑/满载丢弃/Stop 等待）+ `ab_test_bounded_test.go`（占槽阻塞/满载丢弃/释放后再准入），全绿。红态为静态结论（报告 §4 无背压判定），新测试钉死有界契约。

### GW-9 密钥失败不进限流计数 — ✅
- 指标：`sparkle_key_auth_failures_total{mechanism=admin_secret|internal_api_key, reason=not_configured|missing|invalid}`；接线 `AdminAuthMiddleware`（auth.go）与 `InternalAPIKeyMiddleware`（internal_api.go）的全部 401 分支。
- 有效密钥不计数（测试钉死）；这些请求先于限流器被拒，计数器即爆破探测的唯一非日志信号。
- `key_auth_failures_test.go`：missing/invalid 分别计数、有效密钥零计数，PASS。

## 4. R2-08 网关侧 P3 处置（08-r2-fixes.md §5 分类清单）

§5 各行的归属甄别：/health、/ws、achievements 副本、exam-sprint 功能面、marketplace/seed-libraries admin、galaxy/community 长尾、单条散布——均为**引擎侧**去重/产品确认项，非网关代码；R2-08-12 迁移守卫为 scripts 侧。网关侧可执行项 = 「死网关路由 17 条」行，本批全量处置：

| # | 路由 | 处置 | 依据 |
|---|---|---|---|
| 4,5 | GET/POST `/cards`（bare） | 删 | 引擎无 bare 面 |
| 6,7 | PATCH/PUT `/cards/*` | 删 | 引擎 /cards 无 PATCH/PUT |
| 10 | POST `/exam-sprint/completion` | **改方法 → GET** | 引擎仅 GET /completion（plan_id query）；mobile `examSprintCompletion` 常量经查是 go_router 应用内导航 URI 而非 HTTP 调用，无双注册风险 |
| 11 | POST `/tasks/:id/reopen` | 删 | 引擎全仓无 reopen |
| 12 | GET `/tasks/suggestions` | 删（POST 兄弟存活） | 引擎仅 POST |
| 13 | PATCH `/goals/:id` | 删（PUT 兄弟存活） | 引擎仅 PUT {goal_id} |
| 14 | GET `/cqrs/dlq/stats` | 删（整组） | 引擎无 /api/v1/cqrs/*；真身在 /dlq/* 与 /admin |
| 15-17 | POST/GET/DELETE `/community/messages/private*` | 删 ×3 | 引擎无私信面（DM=/friends/{id}/messages） |
| 18 | PATCH `/community/posts/:post_id` | 删 | 引擎无 post 编辑 |
| 19 | DELETE `/community/groups/:id/leave` | 删（POST 兄弟存活） | 引擎仅 POST leave |
| 20 | DELETE `/community/groups/:id/messages/:msg_id` | 删（PATCH+revoke 存活） | 引擎无 DELETE |
| 21 | POST `/community/share/:share_id/adopt` | 删（新别名存活） | 引擎用 /shared-resources/{id}/adopt |
| 22 | GET `/galaxy/nodes` | 删（POST 兄弟存活） | 引擎仅 POST /galaxy/nodes |

- 删除前逐条核过 mobile `api_endpoints.dart`/feature 消费者（cards 常量无 HTTP 消费者；taskSuggestions 走 POST；其余报告已实证 404/405 无成功消费者）——客户端结果不变（引擎 404/405 → 网关路由 404），面收敛。
- 回归钉死：`proxy_routes_r208_test.go` 三测——17 键逐一断言未注册（方法为键）、GET completion 在/POST completion 不在、11 条存活兄弟路由防过剪。全绿。
- **守卫化（BM 守卫）**：`scripts/guards/check_rule_bm_r208_dead_routes.py`——16 片段 + exam-sprint 方法面双向断言，`rule-bm: ignore <reason>` 豁免注记；已登记 `rule_guard_manifest.tsv`（68→69 守卫）。红-绿：临时回插 `cards.PUT` → FAIL（exit 1，指向精确行）→ 还原 → OK。
- 报告 §5 建议「网关↔引擎前缀自动比对扩进 BA guard」：**移交**（跨语言全量 parity 守卫是独立工程，现状 92 条不可达引擎路由需产品/引擎侧先清；BM 守卫是本批处置面的防回归钉子）。

## 5. 测试记录

```
$ CGO_ENABLED=0 go vet ./...                                   → 零输出
$ export SECRET_KEY=x JWT_SECRET=test-secret-0123456789abcdef CGO_ENABLED=0
逐包 -count=1（一次一个 go test 进程）：
  ok  cmd/server           0.8s    ok  internal/agent     0.9s
  ok  internal/config      0.5s    ok  internal/logsafe   0.5s
  ok  internal/middleware  5.7s    ok  internal/service   9.4s
  ok  internal/cqrs        2.7s    ok  internal/cqrs/event 0.5s
  ok  internal/db          0.6s    ok  internal/handler  27.2s
  internal/metrics — 无测试文件（新增 gauge/counter 值读取 helper 供跨包测试）
  gen/* 为生成代码；outbox/projection/worker/galaxy/logger/i18n 无测试文件
守卫：bash scripts/run_all_rule_guards.sh 全绿（含新 [Rule BM]）；BM 守卫独立红验 exit 1 → 还原 → exit 0
```

过程产物（patch 外）：无遗留临时文件（zz_red/debug 测试均已删除）；`docs/product/stage22_prompt_coverage_baseline.md` 的 audited_at 时间戳为守卫套件运行副作用，已 `git checkout` 还原。

## 6. 新发现记档与移交清单

**新发现（本批已顺手修或已防护）**：
1. `ChatHistoryService.Run` 热旋：pubsub 接收错误 warn+continue，Redis 关停时拨号即败 = 无间隔重试刷屏（GW-3 修复中一并改为错误上交重启循环）。
2. go-redis pubsub 取消盲区：`ReceiveMessage` 建连后 ctx 取消不解除阻塞，进程无法干净停机（GW-3 修复中加 pubsub.Close watcher）。
3. typed-nil 接口装箱陷阱：`Registry()` 具体指针入接口后 nil 检查失效（GW-6 调用点已显式防护，此处记档防扩散）。
4. miniredis v2.35 无 `SetSlowdown`：GW-P3-4 测试用 ctx-aware redis `AddHook` 模式替代（模式可复用，见 `websocket_proxy_dedup_test.go`）。

**移交（未做，超出本批授权）**：
1. 「网关↔引擎前缀自动比对」全量 parity 守卫（BA guard 扩展）——需引擎侧先清 §5 长尾，BM 守卫为过渡钉子。
2. §5 引擎侧行（health/achievements 双前缀去重、exam-sprint dashboard/sprint-summary/diagnose 补注册、marketplace/seed-libraries admin 面、galaxy/community 长尾、单条散布 9 条）——引擎代码 + 产品确认，非网关。
3. 免费模型配额跨层降级（GW-P2-4 决策原文中的 follow-up）。
4. 配额 Lua reserve/refund/decr 死代码族删除（R2-05 报告选项 1，需另行决策）。
5. CI 补跑 `-race`（本机 CGO_ENABLED=0 铁律不可用；并发正确性以行为性并发测试+静态论证覆盖：fallback CAS、reconnect 单锁、backfill/metric 信号量、subscriber watcher）。

---

*处置方法：可行为红的项全部红-绿（GW-P2-4/P3-1/P3-2/P3-4/P3-5/GW-3/BM 守卫）；纯观测/契约项（P3-3/P3-6/P3-7/GW-7/GW-9）以「报告判词 + 新观测面钉死」处置。git 操作仅 add/diff/reset，未 commit。*
