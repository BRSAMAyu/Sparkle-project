# Sparkle 全系统第二轮深度质量审查报告

**审查日期**: 2026-05-02
**审查范围**: Go Gateway / Python Engine / Flutter Mobile / 安全 / 基础设施 / i18n
**审查方法**: 5 个并行 agent (3 opus + 2 haiku)，逐行代码审查 + 全局模式扫描
**基准分支**: `fix/quality-audit-deep-2026-05-02`

---

## 总览

| 层 | P1 | P2 | P3 | 总计 |
|----|----|----|----|----|
| Go Gateway | 3 | 9 | 8 | 20 |
| Python Engine | 0 | 10 | 10 | 20 |
| Flutter | 4 | 6 | 6 | 16 |
| 安全 (跨切面) | 2 | 5 | 4 | 11 |
| 基础设施 | 0 | 4 | 6 | 10 |
| **合计** | **9** | **34** | **34** | **77** |

---

## P1 级发现 (9 个 — 必须修复)

### [P1-Go-1] chat_orchestrator PII 明文日志泄露
- **文件**: `chat_orchestrator.go`, `chat_orchestrator_chatflow.go`, `chat_orchestrator_feedback.go`
- **问题**: 15+ 处 `log.Printf("... user: %s", userID)` 直接写入原始 userID。`websocket_proxy.go` 正确使用了 `hashUserIDForLog()`，但 orchestrator 系列文件未对齐。
- **风险**: 日志收集到 Loki/ELK 时构成 PII 泄露，违反 GDPR/个人信息保护法。

### [P1-Go-2] ws_registry BroadcastToUser 数据竞争
- **文件**: `ws_registry.go:174-211`
- **问题**: `alive` 字段是 `bool`，`BroadcastToUser` 在 RUnlock 和 RLock 之间无锁读取 `*w.alive`，而 `Unregister` 在写锁下修改。Go 内存模型下构成数据竞争。
- **修复**: 改为 `atomic.Bool`。

### [P1-Go-3] JWT audience 验证时序攻击
- **文件**: `auth.go:384-405`
- **问题**: `claimHasAudience` 使用 `==` 比较 `aud` claim，可用时序侧信道逐字节猜测。
- **修复**: 改用 `subtle.ConstantTimeCompare`。

### [P1-Flutter-1] WebSocket 消息静默丢失
- **文件**: `websocket_chat_service_v2.dart:1901-1907`
- **问题**: `_queueIncomingMessage` 的 `catchError` 仅打日志，异常消息被丢弃，UI 无感知。
- **修复**: 关键事件异常时向 UI 发送 ErrorEvent。

### [P1-Flutter-2] WebSocket 重连消息时序错乱
- **文件**: `websocket_chat_service_v2.dart:1669-1676`
- **问题**: `_restorePendingFromDb` 是 `unawaited` 异步，`_flushPendingMessages` 同步调用可能先于恢复完成，导致离线消息丢失或乱序。
- **修复**: `_flushPendingMessages` 移到 `_restorePendingFromDb` 的 `.then()` 回调中。

### [P1-Flutter-3] ChatNotifier isSending 状态双重重置竞态
- **文件**: `chat_provider.dart:1022-1134`
- **问题**: `finalizeRun` 和 `finally` 块都可能重置 `isSending`，导致状态闪烁。
- **修复**: finally 块增加 `!sawTerminalEvent` 守卫。

### [P1-Flutter-4] communityEventsStreamProvider 每次重建创建新 WebSocket
- **文件**: `community_provider.dart:32-65`
- **问题**: `WebSocketService()` 在 Provider 构建时创建，autoDispose 重建时旧连接依赖 GC 断开。
- **修复**: 将 WebSocketService 提升为单例 Provider。

### [P1-Sec-1] gRPC 通信默认无 TLS
- **文件**: `agent/client.go:96`
- **问题**: `insecure.NewCredentials()` 为默认配置，生产环境可能未启用 TLS。
- **修复**: 生产环境强制 `AGENT_TLS_ENABLED=true`，否则拒绝启动。

### [P1-Sec-2] 调试日志在生产环境泄露敏感信息
- **文件**: `ws_auth.go:36-71`
- **问题**: `log.Printf` 记录用户 ID 和请求细节，生产环境应使用结构化日志并禁用详细日志。
- **修复**: 替换为 Zap，生产环境降低日志级别。

---

## P2 级发现 (34 个 — 应修复)

### Go Gateway (9 个)

| ID | 文件 | 类别 | 问题摘要 |
|----|------|------|---------|
| P2-Go-1 | `distributed_rate_limiter.go` | 可观测性 | `rateLimiterTokensCurrent` GaugeVec label 含 clientID，Prometheus 基数爆炸 |
| P2-Go-2 | `client.go:325-335` | 错误处理 | gRPC 流重连后用已耗尽 timeout 的旧 context 重试 |
| P2-Go-3 | `chat_orchestrator_responder.go` | 错误处理 | protobufResponder 6+ 处 `json.Marshal` 错误被 `_` 忽略 |
| P2-Go-4 | `websocket_proxy.go:518` | 安全 | groupID 未验证直接拼接 URL，path traversal 风险 |
| P2-Go-5 | `rate_limit.go:301` | 资源管理 | `HybridRateLimitMiddlewareSimple` 创建的 RateLimiter goroutine 无 Stop |
| P2-Go-6 | `chat_orchestrator_chatflow.go:531` | 性能 | 热路径每次读取 `DAILY_QUOTA` / `STREAM_TOKEN_SEGMENT` 环境变量 |
| P2-Go-7 | `cors.go:11-14` | 安全 | Allow-Headers 缺少 `X-Request-ID` 等，无 Expose-Headers |
| P2-Go-8 | `chat_orchestrator.go:229` | 可观测性 | WS 升级失败用 `log.Printf` 而非 Zap，缺少关键诊断信息 |
| P2-Go-9 | `chat_orchestrator.go:259` | 资源管理 | drain/limit 场景下 defer 重复关闭已关闭的 WebSocket 连接 |

### Python Engine (10 个)

| ID | 文件 | 类别 | 问题摘要 |
|----|------|------|---------|
| P2-Py-1 | 多处 | 正确性 | `_utcnow()` 15+ 处重复定义，tz-aware/naive 混用可能 TypeError |
| P2-Py-2 | `llm_service.py:597-604` | LLM 可靠性 | fallback 路径伪对象 provider.value 指向 temperature 而非 provider 名称 |
| P2-Py-3 | `context_builder.py:659-1002` | 性能 | `_build_user_context()` 10+ 串行 DB 查询可用 `asyncio.gather()` 并行 |
| P2-Py-4 | `context_pruner.py:324-338` | 健壮性 | 全局单例持有固定 Redis 引用，断线重连后永久失效 |
| P2-Py-5 | `event_bus.py:839-883` | 事件总线 | 重试消息新 message_id 绕过 idempotency 检查，可能重复处理风暴 |
| P2-Py-6 | `memory_service.py:117-153` | 并发安全 | `max_version` 查询无 FOR UPDATE，并发写入可能版本冲突 |
| P2-Py-7 | `state_aggregator/service.py:114` | 内存 | `_cache` 纯 dict 无上限无主动淘汰，长时间运行内存泄漏 |
| P2-Py-8 | `dual_core_router.py:633,660,676` | 路由 | `cognitive_adjustments[:5]` 按追加顺序截断，高优先级信号可能丢失 |
| P2-Py-9 | `event_bus.py:1201-1210` | 健壮性 | 连接错误检测用字符串匹配 `"connection" in str(e)` 而非 isinstance |
| P2-Py-10 | `llm_secure_io.py:85-89` | 安全 | kill switch "off" 时安全过滤完全绕过，shadow 模式也不生效 |

### Flutter (6 个)

| ID | 文件 | 类别 | 问题摘要 |
|----|------|------|---------|
| P2-Fl-1 | 128+ 处 | i18n | 大量硬编码中文字符串未走 l10n (详见下表) |
| P2-Fl-2 | `capsule_share_card.dart:260` | i18n | switch pattern 混用中英文 key 匹配 |
| P2-Fl-3 | `routes.dart:70-124` | 导航 | guest 用户路由策略不完整，缺文档 |
| P2-Fl-4 | `shell_navigation.dart:215` | 性能 | `ref.watch(communityEventsStreamProvider)` 导致导航栏 rebuild 风暴 |
| P2-Fl-5 | 多文件 | 设计系统 | 7+ 文件硬编码颜色值，未走 design_system.dart |
| P2-Fl-6 | `seed_item_card.dart` 等 | 设计系统 | 10+ 处 `FontWeight.bold` 未用 DS.fontWeightBold token |

### 安全 (5 个)

| ID | 文件 | 问题摘要 |
|----|------|---------|
| P2-Sec-1 | `config.go:564` | 弱密钥检测只在运行时，CI 中无密钥强度检查 |
| P2-Sec-2 | 测试文件 | 硬编码密码和 API key 散落在多个测试文件 |
| P2-Sec-3 | `settings.py:997` | CORS 配置依赖运行时验证，无 CI 级检查 |
| P2-Sec-4 | `setup.go:468-502` | health/internal 端点缺少独立速率限制 |
| P2-Sec-5 | `docker-compose.yml` | 部分服务未指定 user，可能以 root 运行 |

### 基础设施 (4 个)

| ID | 文件 | 问题摘要 |
|----|------|---------|
| P2-Inf-1 | `docker-compose.yml` | MinIO 无健康检查 |
| P2-Inf-2 | `sparkle_slo_alerts.yml` | 缺少 DB 连接池/磁盘/内存告警 |
| P2-Inf-3 | `ci.yml` | 缺少性能基准测试 |
| P2-Inf-4 | `proto/*.proto` | 中文注释 20+ 处，缺 protoc-gen-validate |

---

## P3 级发现 (34 个 — 建议修复)

<details>
<summary>Go Gateway P3 (8 个)</summary>

| ID | 问题 |
|----|------|
| P3-Go-1 | `stringBuilderPool` 大对象(100KB+) 回 pool 后长期占内存 |
| P3-Go-2 | `health_checker.go` onStateChange goroutine 未被 wg 跟踪 |
| P3-Go-3 | `chat_history.go` retryWorker goroutine 无 Stop 调用 |
| P3-Go-4 | `chat_orchestrator.go:304` `_ = authToken` 死代码 |
| P3-Go-5 | `distributed_rate_limiter.go:264` 直接类型断言 `.(int64)` 可能 panic |
| P3-Go-6 | `chat_orchestrator_chatflow.go:781` 每条消息调 Redis LLEN，热路径瓶颈 |
| P3-Go-7 | `chat_history.go:276-313` Pipeline 部分失败不透明 |
| P3-Go-8 | `health_checker.go:302` `circuitBreakerStateGauge.Reset()` 在锁内调用 |

</details>

<details>
<summary>Python Engine P3 (10 个)</summary>

| ID | 问题 |
|----|------|
| P3-Py-1 | `privacy.py` 银行卡正则误报率过高（匹配所有 12-19 位数字） |
| P3-Py-2 | `write_pipeline.py` SHA-1 截断 96bit 用于 claim 去重，碰撞风险 |
| P3-Py-3 | `context_builder.py:832` fallback 路径调用 `get_analytics_summary` 但结果未使用 |
| P3-Py-4 | `llm_service.py:1560` `get_db().__anext__()` 获取的 session 从不关闭 |
| P3-Py-5 | `write_pipeline.py:386` Redis SETEX read-merge-write 无原子性 |
| P3-Py-6 | `context_pruner.py:217` `len(content) <= 12` 低信号阈值过激进，中文 12 字可含完整信息 |
| P3-Py-7 | `agent_grpc_service.py:329` 双重 commit 模式，事务语义不清 |
| P3-Py-8 | `state_aggregator/service.py:726` achievement 全表扫描计算 total_score |
| P3-Py-9 | `dual_core_router.py:52` frozen dataclass 含可变 list |
| P3-Py-10 | `llm_service.py:820` sanitize_llm_output 双重调用 |

</details>

<details>
<summary>Flutter P3 (6 个)</summary>

| ID | 问题 |
|----|------|
| P3-Fl-1 | `vocabulary_provider.dart:78` 错误消息泄露内部异常 |
| P3-Fl-2 | `sector_config.dart:146` 知识域关键词全中文，后端英文标签匹配失效 |
| P3-Fl-3 | `thought_capsule_dialog.dart` 绕过 AppFeedback 直接调 ScaffoldMessenger |
| P3-Fl-4 | `chat_provider.dart:80` `_Debouncer` 跨 part 文件定义，降低可发现性 |
| P3-Fl-5 | `mindfulness_provider.dart` Timer.periodic 可能未在 dispose 清理 |
| P3-Fl-6 | 全局仅 ~30 处 semanticLabel，700+ 文件大量交互元素缺少无障碍标注 |

</details>

<details>
<summary>安全 P3 (4 个)</summary>

| ID | 问题 |
|----|------|
| P3-Sec-1 | 迁移脚本用 f-string 拼接 SQL 表名（运维脚本，非用户输入） |
| P3-Sec-2 | Redis 密码通过环境变量传递，docker inspect 可见 |
| P3-Sec-3 | 测试中 `service.api_key = "zhipu-key"` 占位符密钥 |
| P3-Sec-4 | WebSocket 支持 query 参数传递 token，URL 中 token 可能被日志记录 |

</details>

<details>
<summary>基础设施 P3 (6 个)</summary>

| ID | 问题 |
|----|------|
| P3-Inf-1 | 开发环境缺少网络隔离 |
| P3-Inf-2 | 监控服务开发环境无资源限制 |
| P3-Inf-3 | 缺少数据库备份策略 |
| P3-Inf-4 | 日志卷无大小限制 |
| P3-Inf-5 | 告警命名不一致 |
| P3-Inf-6 | Go/Flutter 覆盖率阈值偏低 |

</details>

---

## i18n 现状

| 指标 | 数值 |
|------|------|
| 含硬编码中文的文件数 | ~527 个 |
| 硬编码中文字符串总数 | ~2,176 个 |
| 其中 UI 显示文本（非注释） | ~128+ 处需优先处理 |
| i18n 转换进度 | ~48.9% |

**按模块分布 (UI 硬编码)**:

| 模块 | 文件数 | 优先级 |
|------|--------|--------|
| chat | 90 | P0 |
| home | 74 | P0 |
| community | 52 | P1 |
| user | 50 | P1 |
| task | 27 | P1 |
| galaxy | 26 | P2 |
| plan | 25 | P1 |
| 其他 | ~183 | P2-P3 |

---

## 正面发现

第二轮审查确认以下方面质量良好：

1. **JWT 黑名单机制** — JTI + 用户级别撤销 + Fail-Closed
2. **时序攻击防护** — `internal_api.go` 使用 `subtle.ConstantTimeCompare`
3. **多层速率限制** — IP/Auth/WebSocket/端点四级 + Redis 分布式 + 本地降级
4. **安全 HTTP 头** — CSP + HSTS + X-Frame-Options + Permissions-Policy
5. **错误消息清理** — 生产环境不泄露内部错误详情
6. **Docker 生产配置** — 蓝绿部署、资源限制、网络隔离、端口绑定
7. **CI 安全扫描** — Trivy + Gitleaks + Safety 三重扫描
8. **Proto 管理** — Buf 工具链 + breaking change 检测 + CI 强制

---

## 修复优先级建议

### 立即 (P1 — 本周)

1. **[P1-Go-1]** chat_orchestrator 全量替换明文 userID → `hashUserIDForLog()`
2. **[P1-Go-2]** ws_registry `alive` 改 `atomic.Bool`
3. **[P1-Go-3]** JWT aud 改 `subtle.ConstantTimeCompare`
4. **[P1-Flutter-1]** WebSocket 消息失败时发送 ErrorEvent
5. **[P1-Flutter-2]** `_flushPendingMessages` 移入 `_restorePendingFromDb().then()`
6. **[P1-Flutter-4]** communityEventsStreamProvider 改单例

### 下一迭代 (P2 — 2 周内)

7. **[P2-Go-1]** 移除或聚合 rateLimiterTokensCurrent label
8. **[P2-Go-4]** groupID 添加格式验证
9. **[P2-Py-2]** LLM fallback 路径修复伪对象 provider 赋值
10. **[P2-Py-5]** EventBus 重试消息使用 `_original_message_id` 做 idempotency
11. **[P2-Py-7]** StateAggregator cache 改用 `cachetools.TTLCache`
12. **[P2-Py-10]** shadow 模式下仍执行安全过滤（记录但不阻断）
13. **[P2-Fl-4]** communityEventsStream 改 `ref.listen`

### 计划中 (P3 — 1-2 月)

14. i18n 第二批转换（128+ UI 硬编码字符串）
15. 设计系统颜色/字体 token 合规
16. 无障碍标注补全
17. 覆盖率阈值提升

---

**报告生成时间**: 2026-05-02
**审查 Agent**: 3x Opus (Go/Python/Flutter) + 2x Haiku (Security/Infra)
