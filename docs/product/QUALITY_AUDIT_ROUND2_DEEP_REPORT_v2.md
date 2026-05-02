# Sparkle 全系统第二轮深度质量审查报告 (修正版 v2)

**审查日期**: 2026-05-02
**修正日期**: 2026-05-02
**审查范围**: Go Gateway / Python Engine / Flutter Mobile / 安全 / 基础设施 / i18n
**基准分支**: `fix/quality-audit-deep-2026-05-02`

> **v2 修正说明**: 经 5 个并行 agent 逐条验证，修正了 1 处 P1 误报、1 处 P2 升级、2 处事实错误、1 处上下文缺失。详见附录 A。

---

## 总览

| 层 | P1 | P2 | P3 | 总计 |
|----|----|----|----|------|
| Go Gateway | 3 | 9 | 8 | 20 |
| Python Engine | 1 | 9 | 10 | 20 |
| Flutter | 3 | 6 | 7 | 16 |
| 安全 (跨切面) | 2 | 5 | 4 | 11 |
| 基础设施 | 0 | 4 | 6 | 10 |
| **合计** | **9** | **33** | **35** | **77** |

> v1→v2 变化: P1-Flutter-3 (isSending 竞态) 验证为误报，从 P1 移除；P2-Py-1 (`_utcnow` 252 处重复 + 不兼容返回类型) 升为 P1；原 P1-Flutter-3 移至 P3 (已防护的代码模式记录)。

---

## P1 级发现 (9 个 — 必须修复)

### [P1-Go-1] chat_orchestrator PII 明文日志泄露

- **文件**: `chat_orchestrator.go`, `chat_orchestrator_chatflow.go`, `chat_orchestrator_feedback.go`
- **问题**: **25 处** `log.Printf("... user: %s", userID)` 直接写入原始 userID。`websocket_proxy.go` 正确定义了 `hashUserIDForLog()` (line 562) 并在全部 15 个日志站使用，但 orchestrator 系列文件未对齐。
- **验证**: 逐文件确认 — orchestrator.go 3 处 (L307, L310, L682)、chatflow 12 处 (L315, L332, L360, L364, L375, L439, L467, L544, L684, L752 等)、feedback 10 处 (L214, L229, L237, L251, L264, L271, L282, L289, L588, L759, L860, L961)。
- **风险**: 日志收集到 Loki/ELK 时构成 PII 泄露，违反 GDPR/个人信息保护法。
- **修复**: 全量替换为 `zap.String("user_id_hash", hashUserIDForLog(userID))`，与 websocket_proxy.go 对齐。

### [P1-Go-2] ws_registry BroadcastToUser 数据竞争

- **文件**: `ws_registry.go:174-211`
- **问题**: `alive` 字段是 `bool`，`BroadcastToUser` 在 RUnlock (L193) 和 RLock (L200) 之间无锁读取 `*w.alive`，而 `Unregister` 在写锁下修改。Go 内存模型下构成数据竞争，`go test -race` 会报警。
- **验证**: 确认 `alive *bool` 指针模式存在但不足以消除 race。L193 `r.mu.RUnlock()` 到 L200 `r.mu.RLock()` 之间存在无锁窗口。
- **风险**: 低实际危害（alive 指针提供部分保护），但 race detector 必定报错。
- **修复**: `alive` 改为 `atomic.Bool`，读取用 `alive.Load()`，写入用 `alive.Store(false)`。

### [P1-Go-3] JWT audience 验证时序攻击

- **文件**: `auth.go:384-405`
- **问题**: `claimHasAudience` 在 L390、L393、L399 三处使用 `==` 比较 `aud` claim，可用时序侧信道逐字节猜测。同文件 L417 已正确使用 `subtle.ConstantTimeCompare` 进行 admin secret 验证，且已导入 `crypto/subtle` (L5)。
- **验证**: 确认三处 `==` 均可替换。
- **风险**: 低可利用性（HS256 签名保护了 claim 完整性），但不符合纵深防御原则。
- **修复**: 三处 `==` 替换为 `subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1`。

### [P1-Py-1] `_utcnow()` 252 处重复定义 + 3 种不兼容返回类型

- **文件**: `backend/app/` 下 252 个文件
- **问题**: 252 处独立定义 `_utcnow()`，存在三种不兼容返回类型：
  1. **tz-naive** (~250+ 文件): `datetime.now(UTC).replace(tzinfo=None)` — 例: `state_aggregator/service.py:77`
  2. **tz-aware** (至少 1 文件): `datetime.now(UTC)` — 例: `orchestrator.py:229`
  3. **ISO string** (~17 文件): `datetime.now(UTC).isoformat()` — 例: `signals/intervention_episode.py:28`
- **风险**: `orchestrator.py` 传 tz-aware 结果给 state_aggregator (tz-naive)，比较时触发 `TypeError: can't compare offset-naive and offset-aware datetimes`。string 返回类型更会导致静默类型错误。
- **修复**:
  1. 在 `backend/app/core/time_utils.py` 定义统一 `utcnow() -> datetime` (tz-naive，与现有主流一致)
  2. 全量替换 252 处 import
  3. 对 ISO string 变体单独处理（改为调用方 `.isoformat()` 而非函数内部转换）

### [P1-Flutter-1] WebSocket 消息静默丢失

- **文件**: `websocket_chat_service_v2.dart:1901-1907`
- **问题**: `_queueIncomingMessage` 的 `catchError` 仅打日志，异常消息被丢弃。`_handleIncomingMessage` (L1910) 内部也有 try/catch (L1944) 仅日志。两层兜底都不通知 UI。
- **验证**: 确认消息链序列化模式本身正确，问题纯粹是 error handling gap。
- **风险**: 格式错误的服务端消息会导致用户永远看不到该消息内容，无任何 UI 提示。
- **修复**: `catchError` 中对关键事件类型（chat delta、plan review 等）向 UI 发送 ErrorEvent。

### [P1-Flutter-2] WebSocket 重连消息时序错乱

- **文件**: `websocket_chat_service_v2.dart:1672-1676`
- **问题**: `_restorePendingFromDb` 是 `unawaited` 异步，`_flushPendingMessages` 同步调用先于 DB 恢复完成。后果：
  1. 内存中的 pending 消息先发送
  2. DB 恢复的消息插入队列时 flush 已完成，这些消息被滞留直到下次 flush 触发
- **验证**: 确认 `_restorePendingFromDb` (L2376-2395) 是 async 函数，`_flushPendingMessages` (L2365-2373) 是同步调用。
- **修复**: `_flushPendingMessages` 移到 `_restorePendingFromDb().then()` 回调中，确保 DB 恢复完成后再 flush。

### [P1-Flutter-4] communityEventsStreamProvider 每次重建创建新 WebSocket

- **文件**: `community_provider.dart:32-65`
- **问题**: `WebSocketService()` 在 L40 于 Provider 体内直接实例化。autoDispose 重建时：
  1. 旧连接依赖 `ref.onDispose` 断开（非立即）
  2. 新连接立即创建
  3. 下游 `friendsProvider` (L92) 等看到新 stream，触发重新初始化级联
- **验证**: 确认 `WebSocketService()` 未注入，直接在 provider body 创建。
- **修复**: 将 `WebSocketService` 提升为独立的非 autoDispose 单例 Provider，communityEventsStreamProvider 引用该单例。

### [P1-Sec-1] gRPC 通信默认无 TLS

- **文件**: `agent/client.go:96`
- **问题**: `insecure.NewCredentials()` 为默认配置 (L96)，TLS 由 `AGENT_TLS_ENABLED` 控制 (默认 false)。生产环境存在两个防护层：
  1. `config.go:574` 拦截 `InsecureSkipVerify=true`（但**不拦截 TLS 未启用**）
  2. Docker Compose 部署中 Go/Python 通常共享网络，降低风险
- **验证**: 确认 L97-115 有 TLS opt-in 逻辑，但生产环境不强制启用。
- **风险**: 跨主机部署时 gRPC 流量明文传输。同主机 Docker 部署风险较低。
- **修复**: 生产环境 (`!IsDevelopment()`) 强制 `AGENT_TLS_ENABLED=true`，否则 `log.Fatal` 拒绝启动。

### [P1-Sec-2] 调试日志在生产环境泄露用户 ID

- **文件**: `ws_auth.go:36-71`
- **问题**: 6 处 `log.Printf` 无条件触发（不受 debug 模式控制），其中 L50 和 L71 明文记录 userID：
  ```
  [WsAuth] JWT header validation success for user: %s", userID
  [WsAuth] JWT query validation success for user: %s", userID
  ```
- **验证**: 确认全部 6 处均为标准 `log.Printf`，无日志级别控制。
- **风险**: 每次成功 WebSocket 认证都写明文 userID 到生产日志。
- **修复**: 替换为 Zap 结构化日志 + hashUserIDForLog，生产环境降为 Debug 级别。

---

## P2 级发现 (33 个 — 应修复)

### Go Gateway (9 个)

| ID | 文件 | 类别 | 问题摘要 | 修复方向 |
|----|------|------|---------|---------|
| P2-Go-1 | `distributed_rate_limiter.go` | 可观测性 | `rateLimiterTokensCurrent` GaugeVec label 含 clientID，Prometheus 基数爆炸 | 移除 clientID label 或改为 bucket 聚合 |
| P2-Go-2 | `client.go:325-335` | 错误处理 | gRPC 流重连后用已耗尽 timeout 的旧 context 重试 | 重连时创建新 context + fresh timeout |
| P2-Go-3 | `chat_orchestrator_responder.go` | 错误处理 | protobufResponder 6+ 处 `json.Marshal` 错误被 `_` 忽略 | 返回错误或至少 log.Warn |
| P2-Go-4 | `websocket_proxy.go:107,518` | 安全 | groupID 从 URL 参数提取后零验证直接拼接，path traversal 风险 | 添加 UUID 格式验证 |
| P2-Go-5 | `rate_limit.go:301` | 资源管理 | `HybridRateLimitMiddlewareSimple` 创建的 RateLimiter goroutine 无 Stop | 添加 Stop/Close 方法 |
| P2-Go-6 | `chat_orchestrator_chatflow.go:531` | 性能 | 热路径每次读取 `DAILY_QUOTA` / `STREAM_TOKEN_SEGMENT` 环境变量 | 启动时读取一次，存为变量 |
| P2-Go-7 | `cors.go:11-14` | 安全 | Allow-Headers 缺少 `X-Request-ID` 等，无 Expose-Headers | 补全必要 headers |
| P2-Go-8 | `chat_orchestrator.go:229` | 可观测性 | WS 升级失败用 `log.Printf` 而非 Zap | 统一用 Zap |
| P2-Go-9 | `chat_orchestrator.go:259` | 资源管理 | drain/limit 场景下 defer 重复关闭已关闭的 WebSocket 连接 | 添加 `alive` 检查或 sync.Once |

### Python Engine (9 个)

| ID | 文件 | 类别 | 问题摘要 | 修复方向 |
|----|------|------|---------|---------|
| P2-Py-2 | `llm_service.py:597-604` | LLM 可靠性 | fallback 路径匿名对象 `provider` 属性中 `temperature` 放错嵌套层级，脆弱 | 构造正确的 ModelConfig 而非匿名对象 |
| P2-Py-3 | `context_builder.py:659-1002` | 性能 | `_build_user_context()` 10+ 串行 DB 查询可用 `asyncio.gather()` 并行 | 改为并行查询 |
| P2-Py-4 | `context_pruner.py:324-338` | 健壮性 | 全局单例持有固定 Redis 引用，断线重连后永久失效 | 改为懒获取 Redis 连接 |
| P2-Py-5 | `event_bus.py:839-883` | 事件总线 | 重试消息新 Redis message_id 绕过幂等检查（窗口窄：仅原处理部分成功时） | 用 `_original_message_id` 做幂等 key |
| P2-Py-6 | `memory_service.py:117-153` | 并发安全 | `max_version` 查询无 `FOR UPDATE`，并发写入可能版本冲突 | 加 `SELECT ... FOR UPDATE` |
| P2-Py-7 | `state_aggregator/service.py:114` | 内存 | `_cache` 纯 dict，过期条目仅跳过不删除，无上限 | 改用 `cachetools.TTLCache` + 定期清理 |
| P2-Py-8 | `dual_core_router.py:633,660,676` | 路由 | `cognitive_adjustments[:5]` 按追加顺序截断，高优先级信号可能丢失 | 按优先级排序后截断 |
| P2-Py-9 | `event_bus.py:1201-1210` | 健壮性 | 连接错误检测用 `"connection" in str(e)` 而非 isinstance | 改用异常类型判断 |
| P2-Py-10 | `llm_secure_io.py:85-89` | 安全 | kill switch "off" 时深度安全过滤完全绕过（基础 secret redaction 仍运行） | shadow 模式仍执行过滤（记录但不阻断）；off 模式至少保留输出过滤 |

### Flutter (6 个)

| ID | 文件 | 类别 | 问题摘要 | 修复方向 |
|----|------|------|---------|---------|
| P2-Fl-1 | 128+ 处 | i18n | 大量硬编码中文字符串未走 l10n | 按模块分批转换 |
| P2-Fl-2 | `capsule_share_card.dart:260` | i18n | switch pattern 混用中英文 key 匹配 | 统一用 l10n key |
| P2-Fl-3 | `routes.dart:70-124` | 导航 | guest 用户路由策略不完整 | 补全 guest 路由策略 + 文档 |
| P2-Fl-4 | `shell_navigation.dart:215` | 性能 | `ref.watch(communityEventsStreamProvider)` 导致导航栏 rebuild 风暴 | 改为 `ref.listen` 或 select 子状态 |
| P2-Fl-5 | 多文件 | 设计系统 | 7+ 文件硬编码颜色值 | 统一到 design_system.dart |
| P2-Fl-6 | `seed_item_card.dart` 等 | 设计系统 | 10+ 处 `FontWeight.bold` 未用 DS token | 替换为 DS.fontWeightBold |

### 安全 (5 个)

| ID | 文件 | 问题摘要 | 修复方向 |
|----|------|---------|---------|
| P2-Sec-1 | `config.go:564` | 弱密钥检测只在运行时，CI 中无密钥强度检查 | 添加 CI 阶段的密钥强度 lint |
| P2-Sec-2 | 测试文件 | 硬编码密码和 API key 散落在多个测试文件 | 提取到 test fixture 或 env |
| P2-Sec-3 | `settings.py:997` | CORS 配置依赖运行时验证，无 CI 级检查 | 添加 CI 检查脚本 |
| P2-Sec-4 | `setup.go:468-502` | health/internal 端点缺少独立速率限制 | 添加专用 rate limiter |
| P2-Sec-5 | `docker-compose.yml` | 部分服务未指定 user，可能以 root 运行 | 添加 `user: "1000:1000"` |

### 基础设施 (4 个)

| ID | 文件 | 问题摘要 | 修复方向 |
|----|------|---------|---------|
| P2-Inf-1 | `docker-compose.yml` | MinIO 无健康检查 | 添加 healthcheck |
| P2-Inf-2 | `sparkle_slo_alerts.yml` | 缺少 DB 连接池/磁盘/内存告警 | 补充基础资源告警 |
| P2-Inf-3 | `ci.yml` | 缺少性能基准测试 | 添加 benchmark job |
| P2-Inf-4 | `proto/*.proto` | 中文注释 20+ 处，缺 protoc-gen-validate | 逐步迁移注释 + 添加 validate |

---

## P3 级发现 (35 个 — 建议修复)

<details>
<summary>Go Gateway P3 (8 个)</summary>

| ID | 问题 | 修复方向 |
|----|------|---------|
| P3-Go-1 | `stringBuilderPool` 大对象 (100KB+) 回 pool 后长期占内存 | 添加大小检查，过大的不回收 |
| P3-Go-2 | `health_checker.go` onStateChange goroutine 未被 wg 跟踪 | 添加到 WaitGroup |
| P3-Go-3 | `chat_history.go` retryWorker goroutine 无 Stop 调用 | 添加 context 取消 + Stop |
| P3-Go-4 | `chat_orchestrator.go:304` `_ = authToken` 死代码 | 移除 |
| P3-Go-5 | `distributed_rate_limiter.go:264` 直接类型断言 `.(int64)` 可能 panic | 改为 comma-ok 模式 |
| P3-Go-6 | `chat_orchestrator_chatflow.go:781` 每条消息调 Redis LLEN，热路径瓶颈 | 改为定期批量检查 |
| P3-Go-7 | `chat_history.go:276-313` Pipeline 部分失败不透明 | 改进错误报告 |
| P3-Go-8 | `health_checker.go:302` `circuitBreakerStateGauge.Reset()` 在锁内调用 | 移到锁外 |

</details>

<details>
<summary>Python Engine P3 (10 个)</summary>

| ID | 问题 | 修复方向 |
|----|------|---------|
| P3-Py-1 | `privacy.py` 银行卡正则匹配所有 12-19 位数字，误报率高 | 收紧正则 + Luhn 校验 |
| P3-Py-2 | `aurora/runtime_v1/write_pipeline.py:136` SHA-1 截断 96bit 用于 claim 去重 | 低风险，可换 SHA-256 |
| P3-Py-3 | `context_builder.py:832` fallback 路径调用 `get_analytics_summary` 但结果未使用 | 移除无用调用 |
| P3-Py-4 | `llm_service.py:1560-1562, 1619-1621` 两处 `get_db().__anext__()` session 从不关闭 | 改为 `async with` 或正确驱动 generator |
| P3-Py-5 | `write_pipeline.py:386` Redis SETEX read-merge-write 无原子性 | 改为 Lua script |
| P3-Py-6 | `context_pruner.py:217` `len(content) <= 12` 阈值过激进 | 提高到 20-30 或按语言调整 |
| P3-Py-7 | `agent_grpc_service.py:329` 双重 commit 模式，事务语义不清 | 统一为一个 commit 点 |
| P3-Py-8 | `state_aggregator/service.py:726` achievement 全表扫描计算 total_score | 添加索引或缓存 |
| P3-Py-9 | `dual_core_router.py:52` frozen dataclass 含可变 list | 改为 tuple |
| P3-Py-10 | `llm_service.py:820` sanitize_llm_output 双重调用 | 移除多余调用 |

</details>

<details>
<summary>Flutter P3 (7 个)</summary>

| ID | 问题 | 修复方向 |
|----|------|---------|
| P3-Fl-1 | `vocabulary_provider.dart:78` 错误消息泄露内部异常 | 清理错误消息 |
| P3-Fl-2 | `sector_config.dart:146` 知识域关键词全中文，后端英文标签匹配失效 | 同步关键词 |
| P3-Fl-3 | `thought_capsule_dialog.dart` 绕过 AppFeedback 直接调 ScaffoldMessenger | 统一走 AppFeedback |
| P3-Fl-4 | `chat_provider.dart:80` `_Debouncer` 跨 part 文件定义 | 移到独立文件 |
| P3-Fl-5 | `mindfulness_provider.dart` Timer.periodic 可能未在 dispose 清理 | 添加 cancel |
| P3-Fl-6 | 全局仅 ~30 处 semanticLabel，700+ 文件大量交互元素缺少无障碍标注 | 分批补充 |
| P3-Fl-7 | `chat_provider.dart:1022-1134` isSending 已有 `shouldResetSending` + `sawTerminalEvent` 双重守卫，v1 误报为竞态 | 记录为已验证安全的模式，无需修复 |

</details>

<details>
<summary>安全 P3 (4 个)</summary>

| ID | 问题 | 修复方向 |
|----|------|---------|
| P3-Sec-1 | 迁移脚本用 f-string 拼接 SQL 表名（运维脚本，非用户输入） | 低风险，添加注释说明 |
| P3-Sec-2 | Redis 密码通过环境变量传递，docker inspect 可见 | 改用 Docker secrets |
| P3-Sec-3 | 测试中 `service.api_key = "zolid-key"` 占位符密钥 | 统一为 fixture mock |
| P3-Sec-4 | WebSocket 支持 query 参数传递 token，URL 中 token 可能被日志记录 | 生产环境禁用 query token 或在日志中脱敏 |

</details>

<details>
<summary>基础设施 P3 (6 个)</summary>

| ID | 问题 | 修复方向 |
|----|------|---------|
| P3-Inf-1 | 开发环境缺少网络隔离 | 添加 Docker network 隔离 |
| P3-Inf-2 | 监控服务开发环境无资源限制 | 添加 deploy.resources.limits |
| P3-Inf-3 | 缺少数据库备份策略 | 添加 pg_dump cron |
| P3-Inf-4 | 日志卷无大小限制 | 添加 max-size + max-file |
| P3-Inf-5 | 告警命名不一致 | 统一为 SparkleXxxYyy 命名规范 |
| P3-Inf-6 | Go/Flutter 覆盖率阈值偏低 | 逐步提升 |

</details>

---

## i18n 现状

| 指标 | 数值 | 备注 |
|------|------|------|
| 含硬编码中文的文件数 | ~527 个 | 含注释，非全部需转换 |
| 硬编码中文字符串总数 | ~2,176 个 | 含注释/调试文本 |
| 其中 UI 显示文本（非注释） | ~128+ 处需优先处理 | 与 Final Acceptance 口径一致 |
| i18n 转换进度 | ~48.9% | |

**按模块分布 (UI 硬编码优先级)**:

| 模块 | 文件数 | 优先级 |
|------|--------|--------|
| chat | 90 | P0 |
| home | 74 | P0 |
| community | 52 | P1 |
| user | 50 | P1 |
| task | 27 | P1 |
| plan | 25 | P1 |
| galaxy | 26 | P2 |
| 其他 | ~183 | P2-P3 |

---

## 正面发现

第二轮审查确认以下方面质量良好：

1. **JWT 黑名单机制** — JTI + 用户级别撤销 + Fail-Closed
2. **时序攻击防护** — `internal_api.go` 使用 `subtle.ConstantTimeCompare`（`auth.go` 仅 audience 部分遗漏）
3. **多层速率限制** — IP/Auth/WebSocket/端点四级 + Redis 分布式 + 本地降级
4. **安全 HTTP 头** — CSP + HSTS + X-Frame-Options + Permissions-Policy
5. **错误消息清理** — 生产环境不泄露内部错误详情
6. **Docker 生产配置** — 蓝绿部署、资源限制、网络隔离、端口绑定
7. **CI 安全扫描** — Trivy + Gitleaks + Safety 三重扫描
8. **Proto 管理** — Buf 工具链 + breaking change 检测 + CI 强制

---

## 修复优先级建议

### 第一批: P1 安全 (本周内)

| # | ID | 工作量 | 修复要点 |
|---|-----|--------|---------|
| 1 | P1-Go-1 | M | 25 处 `log.Printf` → `zap` + `hashUserIDForLog()` |
| 2 | P1-Go-2 | S | `alive bool` → `atomic.Bool` |
| 3 | P1-Go-3 | S | 3 处 `==` → `subtle.ConstantTimeCompare` |
| 4 | P1-Sec-1 | S | 生产环境强制 `AGENT_TLS_ENABLED=true` |
| 5 | P1-Sec-2 | S | 6 处 `log.Printf` → Zap + hash + Debug level |

### 第二批: P1 功能 (本周内)

| # | ID | 工作量 | 修复要点 |
|---|-----|--------|---------|
| 6 | P1-Py-1 | L | 创建统一 `utcnow()` → 替换 252 处 (可分批) |
| 7 | P1-Flutter-1 | S | `catchError` 中添加 ErrorEvent 回调 |
| 8 | P1-Flutter-2 | S | `_flushPendingMessages` 移入 `_restorePendingFromDb().then()` |
| 9 | P1-Flutter-4 | M | `WebSocketService` 提升为单例 Provider |

### 第三批: P2 高影响 (2 周内)

| # | ID | 修复要点 |
|---|-----|---------|
| 10 | P2-Go-4 | groupID UUID 验证 |
| 11 | P2-Py-2 | LLM fallback 匿名对象 → 正确 ModelConfig |
| 12 | P2-Py-5 | EventBus 重试用 `_original_message_id` 做幂等 |
| 13 | P2-Py-7 | StateAggregator cache → `cachetools.TTLCache` |
| 14 | P2-Py-10 | kill switch off 模式仍保留输出过滤 |
| 15 | P2-Fl-4 | communityEventsStream 改 `ref.listen` |
| 16 | P2-Go-1 | 移除/聚合 Prometheus clientID label |

### 第四批: P3 + i18n (1-2 月)

17. i18n 第二批转换（128+ UI 硬编码字符串）
18. 设计系统颜色/字体 token 合规
19. 无障碍标注补全
20. P3-Py-4 session 泄漏修复
21. 覆盖率阈值提升

---

## 附录 A: v1 → v2 修正记录

| 修正项 | v1 内容 | v2 修正 | 验证方法 |
|--------|---------|---------|---------|
| P1-Flutter-3 | isSending 双重重置竞态 | **移除 P1** → P3-Fl-7 (已有 `shouldResetSending` + `sawTerminalEvent` 双重守卫，L917, L1029-1033, L1867-1882) | 逐行代码审查 |
| P2-Py-1 | `_utcnow()` 15+ 处重复 | **升为 P1-Py-1** (实际 252 处，3 种不兼容返回类型，tz-aware/naive 混用可致 TypeError) | grep + 逐文件验证 |
| P1-Sec-1 | gRPC 默认无 TLS | **补充上下文**: `config.go:574` 已拦截 `InsecureSkipVerify`，但未强制 TLS 启用 | 代码审查 |
| P3-Py-2 | 文件路径 `backend/app/pipeline/write_pipeline.py` | **修正路径**: `backend/app/aurora/runtime_v1/write_pipeline.py` | 文件存在性验证 |

---

**报告生成时间**: 2026-05-02
**修正时间**: 2026-05-02
**审查 Agent**: 3x Opus (Go/Python/Flutter) + 2x Haiku (Security/Infra)
**验证 Agent**: 5x parallel verification (4 general-purpose + 1 Go specialist)
