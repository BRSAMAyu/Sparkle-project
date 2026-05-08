# Sparkle 星火 — 上线前最终验收清单

> **Version**: 1.2 | **Date**: 2026-05-08 | **Author**: BRSAMA + AI Architect
> **Purpose**: 系统上线前最后一道门 — 确认每一个子系统、每一条链路、每一个用户可感知的功能都达到可上线标准
> **Reference**: 愿景验收清单 v1.0 | P2/P3/P4 裁定书 | Alignment 2026-04-25 | SGW Handoff | 12-agent 全系统深度探索报告
> **Change Log**: v1.2 — Aurora 12模块组件清单 + Self Model/Write Pipeline 新验收项; LLM 6 Provider/9+ Tier/Agent-Aware 路由; Memory 3-Lane 架构 + Evidence 评分 + 纠正机制; Plan Two-Tier Review + Auto-Approval + Alignment Scoring; GraphRAG Fastpath/Multi-Hop/HyDE 三模式; Gateway 16 Handler/14 Middleware/20+ Service/4 Saga 完整清单

---

# 0. 使用说明

## 0.1 验收等级定义

| 分数 | 含义 |
|------|------|
| **PASS** | 已验证通过，达到上线标准 |
| **PASS-W** | 通过但有已知小问题，不影响核心体验 |
| **CONDITIONAL** | 条件通过，需在指定时间前修复补充项 |
| **FAIL** | 不通过，阻塞上线 |
| **N/A** | 本版本不包含，Post-Launch |

## 0.2 分类体系

| 分类 | 含义 | 上线要求 |
|------|------|---------|
| **P0-Critical** | 一票否决项，任一失败即阻塞上线 | 全部 PASS |
| **P1-Core** | 核心链路，直接影响用户体验 | 95% PASS，其余 CONDITIONAL |
| **P2-Experience** | 体验优化，影响用户满意度 | 85% PASS，其余 PASS-W 或 CONDITIONAL |
| **P3-Operational** | 运维保障，影响长期稳定性 | 90% PASS |
| **P4-Vision** | 完全体愿景项，不阻塞首版上线 | N/A，记录进度 |

## 0.3 总通过线

```
P0-Critical:  100% PASS
P1-Core:      ≥95% PASS，0 FAIL
P2-Experience: ≥85% PASS，0 FAIL
P3-Operational: ≥90% PASS，0 FAIL
P4-Vision:    进度记录，不阻塞
```

## 0.4 一票否决项（Veto Items）

以下任一条件不满足，**不能上线**：

```
V1. 用户数据安全有漏洞（未加密传输、PII 泄露、SQL 注入等）
V2. 认证系统不可靠（JWT 可伪造、Token 无法撤销）
V3. AI 输出无安全护栏（能产生有害、歧视、医疗诊断内容）
V4. 数据库无备份恢复能力
V5. 核心用户链路断裂（注册→登录→创建目标→对话→获得计划→执行任务 任何环节不可用）
V6. 生产环境硬编码密钥或密码
V7. 移动端启动崩溃率 > 1%
```

---

# 1. 基础设施层验收 (Infrastructure)

## 1.1 PostgreSQL 数据库

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| INFRA-DB-001 | 连接池 | P0 | pgxpool 30 max / 5 min 连接正常，无泄漏 | `make env-check` + 监控 |
| INFRA-DB-002 | 迁移完整 | P0 | `alembic current` = `alembic heads`，132 迁移全部应用 | `alembic current` |
| INFRA-DB-003 | pgvector 扩展 | P1 | vector 扩展已加载，1024 维 embedding 列存在 | `\dx` in psql |
| INFRA-DB-004 | HNSW 索引 | P1 | knowledge_nodes.embedding 有 HNSW 索引（cosine），查询性能 < 100ms | `\di` + benchmark |
| INFRA-DB-005 | AGE 扩展 | P2 | age 扩展已加载，ag_catalog schema 存在 | `\dx` in psql |
| INFRA-DB-006 | 143 张表完整性 | P1 | schema.sql 与运行库一致，所有 enum/约束/索引就位 | `make sync-db` + diff |
| INFRA-DB-007 | 备份恢复 | P0 | pg_dump 可完整导出，restore 可恢复，恢复后数据校验通过 | `scripts/backup_prod_data.sh` |
| INFRA-DB-008 | 连接加密 | P0 | 生产环境 SSL/TLS 连接 | 配置检查 |
| INFRA-DB-009 | 数据库监控 | P3 | Prometheus pg_exporter 指标采集正常 | Grafana dashboard |
| INFRA-DB-010 | 定期清理 | P3 | events、trace、logs 有归档/清理策略，存储不无限增长 | Celery 任务验证 |

## 1.2 Redis

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| INFRA-RD-001 | 连接稳定 | P0 | Redis Stack 7.4 运行稳定，连接池 100 max / 10 min idle | `redis-cli ping` |
| INFRA-RD-002 | 内存控制 | P1 | maxmemory 512MB + volatile-lru 淘汰策略生效 | `redis-cli CONFIG GET maxmemory` |
| INFRA-RD-003 | Token 黑名单 | P0 | JTI/user/session 三级黑名单写入/查询正确 | Auth 中间件测试 |
| INFRA-RD-004 | Rate Limit | P0 | 分布式限流 (IP/user/endpoint) 生效，滑动窗口正确 | 压测验证 |
| INFRA-RD-005 | 事件流 | P1 | Redis Streams 消费组正常，消费者 lag 可监控 | XINFO + Prometheus |
| INFRA-RD-006 | 缓存一致性 | P1 | 热状态 Redis + 温状态 PG 分层清晰，TTL 合理 | 状态读写验证 |
| INFRA-RD-007 | Fail-Closed | P0 | Redis 不可达时，认证 fail-closed（拒绝请求）而非放行 | 断开 Redis 测试 |
| INFRA-RD-008 | FT.SEARCH | P2 | Redis Search 索引（文档/节点）创建和查询正常 | `FT.SEARCH` 命令 |

## 1.3 MinIO / 对象存储

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| INFRA-MN-001 | 文件上传 | P1 | 文件上传完整，元数据正确写入 DB | API 测试 |
| INFRA-MN-002 | 文件下载 | P1 | 权限校验后可下载，不越权 | API 测试 |
| INFRA-MN-003 | 存储加密 | P0 | 生产环境 SSL 连接 MinIO | 配置检查 |
| INFRA-MN-004 | 文件清理 | P3 | 孤儿文件 GC 机制生效 | FileGCService 测试 |
| INFRA-MN-005 | 大文件支持 | P2 | >10MB 文件分块上传正常 | 上传测试 |

## 1.4 Docker / 容器编排

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| INFRA-DK-001 | 完整栈启动 | P0 | 17 容器全部 healthy: db, redis, minio, api, agent, gateway, celery, monitoring | `docker compose ps` |
| INFRA-DK-002 | 健康检查 | P0 | 每个容器有 healthcheck，unhealthy 自动检测 | `docker compose ps` |
| INFRA-DK-003 | 资源限制 | P2 | 每个容器有 memory/CPU limits | docker-compose.yml 检查 |
| INFRA-DK-004 | 网络隔离 | P2 | 内部服务不暴露外部端口，只有 gateway(8080) 可达 | 端口扫描 |
| INFRA-DK-005 | 重启策略 | P1 | 容器异常退出后自动重启 | `docker kill` 测试 |
| INFRA-DK-006 | 蓝绿部署 | P3 | K8s blue-green 配置有效，切换可回滚 | `scripts/blue_green_switch.sh` |

---

# 2. Go Gateway 层验收

## 2.0 组件清单（深度审计确认）

Gateway 完整组件清单（Go 实现）：

**16 Handlers**:
websocket_proxy / proxy_routes / auth_handler / apple_auth / user_handler / goal_handler / task_handler / galaxy_handler / community_handler / achievement_handler / errorbook_handler / document_handler / admin_handler / health_handler / notification_handler / file_handler

**14 Middleware**:
auth_middleware / cors_middleware / rate_limit / security_headers / error_sanitizer / request_logger / recovery / pii_logsanitizer / metrics_middleware / tracing_middleware / ws_origin_check / admin_auth / internal_auth / dedup

**20+ Services**:
user_service / goal_service / task_service / galaxy_service / community_service / achievement_service / document_service / errorbook_service / notification_service / file_service / cache_service / agent_client (gRPC) / event_publisher / cqrs_outbox / cqrs_relay / cqrs_projection / saga_coordinator / message_dedup / health_checker / file_gc / push_service

**4 Sagas**: TaskCreateSaga / SourceUploadSaga / ExperimentPromotionSaga / SkillPublishSaga

**22 CQRS Prometheus Metrics**: outbox_pending / outbox_relayed / projection_updated / saga_started / saga_completed / saga_compensated / event_published / event_consumed / dlq_size + 分项

## 2.1 认证与授权

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-AUTH-001 | JWT RS256 | P0 | 生产环境使用 RS256，PKCS8/PKCS1 密钥解析正确 | 配置检查 + 测试 |
| GW-AUTH-002 | Token 声明验证 | P0 | sub/type/exp/nbf/iss/aud 全部校验，无效 token 被拒绝 | 安全测试 |
| GW-AUTH-003 | Token 黑名单 | P0 | JTI 撤销 + user-level 撤销 + session 撤销三级生效 | `security_acceptance.py` |
| GW-AUTH-004 | Apple Sign-In | P1 | Apple JWT 验证链路完整 | `apple_auth.go` 测试 |
| GW-AUTH-005 | 时钟偏移 | P2 | 30 秒时钟偏移容忍 | 配置验证 |
| GW-AUTH-006 | WS Ticket | P1 | WebSocket 连接使用 ticket-based auth，非 query token | 生产配置检查 |

## 2.2 安全

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-SEC-001 | 安全头 | P0 | CSP/HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy/Permissions-Policy 全部注入 | curl -I 检查 |
| GW-SEC-002 | 错误脱敏 | P0 | 生产环境不暴露内部错误详情，所有错误经 error_sanitizer.go | 错误触发测试 |
| GW-SEC-003 | PII 日志脱敏 | P0 | logsafe.RedactText() 脱敏 email/phone/ID/card/bearer/api-key | 日志检查 |
| GW-SEC-004 | 输入校验 | P0 | UUID 路径参数校验（防路径穿越）、JSON 净化（bluemonday）、消息大小限制 | 渗透测试 |
| GW-SEC-005 | 生产守护 | P0 | 弱 SECRET_KEY 拒绝、DEBUG=True 拒绝、CORS * 拒绝、缺 internal API key 拒绝 | 配置加载测试 |
| GW-SEC-006 | Admin 路由 | P0 | admin 路由需 X-Admin-Secret（常量时间比较）+ JWT admin 角色 | 授权测试 |
| GW-SEC-007 | 内部路由 | P1 | internal 路由需 X-Internal-API-Key + IP CIDR 白名单 | 内部路由测试 |

## 2.3 WebSocket

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-WS-001 | 流式消息 | P0 | AI 聊天流式 delta 正确推送，CONTINUE→STOP 序列完整 | `ai_chat_multiturn_acceptance.py` |
| GW-WS-002 | 断线重连 | P1 | 客户端重连后消息不丢失、不重复（dedup） | 网络断开测试 |
| GW-WS-003 | 消息去重 | P1 | SHA-256 内容哈希去重，重复消息被过滤 | MessageDedupService 测试 |
| GW-WS-004 | Origin 校验 | P0 | WebSocket 连接校验 Origin 白名单 | curl 测试 |
| GW-WS-005 | 每用户连接限制 | P1 | 单用户 WebSocket 连接数限制生效 | 连接压测 |
| GW-WS-006 | 优雅关闭 | P2 | 服务关闭时 WebSocket 连接有序排干 | `ws_hardening.go` 验证 |
| GW-WS-007 | 心跳 | P1 | ping/pong 心跳 30s 间隔 + 60s 超时，断连自动清理 | 连接日志 |
| GW-WS-008 | 推送集成 | P2 | SignalPush/InterventionPush 正确推送到客户端 | 推送测试 |

## 2.4 gRPC 客户端

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-GRPC-001 | TLS/mTLS | P0 | 生产环境 gRPC 连接使用 TLS | 配置检查 |
| GW-GRPC-002 | 断路器 | P1 | StreamChatWithFallback 三态断路器 (Closed/Open/Half-Open) 生效 | 模拟后端宕机 |
| GW-GRPC-003 | 重试 | P1 | 4 次最大重试，指数退避，keepalive 20s | 配置检查 |
| GW-GRPC-004 | 16 RPC | P1 | StreamChat + feedback + review + arbitration + memory 等 16 RPC 全部可用 | `grpcurl list` |
| GW-GRPC-005 | OTel | P2 | gRPC 调用链路追踪正常 | Tempo 查看 |
| GW-GRPC-006 | 降级 | P1 | gRPC 不可达时 gateway 仍可返回健康状态 + 降级响应 | 断开 Python 测试 |

## 2.5 代理路由与 CQRS

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-PROXY-001 | REST 代理 | P1 | 60+ Python 后端 API 代理正确转发，路径映射无遗漏 | `proxy_routes_test.go` |
| GW-PROXY-002 | 文件服务 | P1 | 上传/下载/元数据代理正确 | 文件 API 测试 |
| GW-CQRS-001 | 事件总线 | P1 | Redis Streams 事件发布/消费正常，22 Prometheus 指标采集 | CQRS metrics |
| GW-CQRS-002 | Outbox | P1 | PostgreSQL 事务性发件箱确保写入与事件最终一致 | outbox_relay 测试 |
| GW-CQRS-003 | 投影 | P2 | community/task/galaxy 读模型投影更新正常 | 投影 worker 测试 |
| GW-CQRS-004 | 4 Saga 协调 | P2 | TaskCreateSaga/SourceUploadSaga/ExperimentPromotionSaga/SkillPublishSaga 协调正确，含补偿逻辑 | saga_test.go |
| GW-CQRS-005 | DLQ | P1 | 失败事件进入 DLQ，可重放，有 admin 管理 API | DLQ 测试 |
| GW-CQRS-006 | 幂等 | P1 | 重试不重复写入状态/任务/通知 | 幂等测试 |
| GW-HDL-001 | 16 Handler 注册 | P1 | websocket/proxy/auth/apple/user/goal/task/galaxy/community/achievement/errorbook/document/admin/health/notification/file 全部注册 | `grpcurl` + route 检查 |
| GW-MW-001 | 14 Middleware 链 | P1 | auth→cors→rate_limit→security_headers→error_sanitizer→request_logger→recovery→pii→metrics→tracing→ws_origin→admin→internal→dedup 链正确 | middleware 测试 |

## 2.6 健康检查

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GW-HEALTH-001 | /healthz /readyz | P0 | DB ping + Redis ping + gRPC health 全部反映真实状态 | curl 测试 |
| GW-HEALTH-002 | 降级模式 | P1 | gRPC 不健康时不阻塞 readiness（降级而非不可用） | 断开 Python 测试 |
| GW-HEALTH-003 | CQRS 健康 | P2 | /api/v1/health/cqrs 报告 outbox 待处理 + worker 状态 | admin API |

---

# 3. Python AI 引擎层验收

## 3.1 核心编排

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-ORB-001 | ChatOrchestrator | P0 | process_stream() 主链完整：上下文组装→路由→验证→执行→响应→持久化→观测 | `ai_chat_multiturn_acceptance.py` |
| AI-ORB-002 | DualCoreRouter | P1 | 认知/执行双核路由正确，goal_clarity/emotional_block/procrastination 评分生效 | 路由测试 |
| AI-ORB-003 | 意图识别 | P1 | BERT + 规则 + LLM 三层意图识别准确率 ≥ 85% | 意图分类测试 |
| AI-ORB-004 | 上下文窗口 | P1 | Token budget 管理 + ContextPruner 裁剪不截断关键信息 | 长对话测试 |
| AI-ORB-005 | UXEnvelope | P1 | 每次响应携带 PresentationProfile + StructuredAction + 适应性记录 | 响应检查 |
| AI-ORB-006 | 多 Agent | P2 | 6 专职 agent（deep analyst/error analyst/exam oracle/galaxy guide/study buddy/time tutor）可用 | 专家模式测试 |

## 3.2 LLM 服务（6 Provider / 9+ Tier / Agent-Aware 路由）

LLM Router 实现 9+ 级模型路由，按 cost/latency/capability/risk 选择模型：

| 级别 | 模型范围 | 典型场景 |
|------|---------|---------|
| FREE | 免费模型 | 低风险/简单问答 |
| LOW-COST | 轻量模型 | 日常对话/工具调用 |
| STANDARD | 标准模型 | 大部分聊天 |
| BALANCED | 均衡模型 | 复杂推理 |
| CAPABLE | 高能力模型 | 目标规划/深度分析 |
| PREMIUM | 旗舰模型 | 关键决策 |
| REASONING | 推理专精 | 多步推理/数学 |
| HIGH-RISK | 高风险场景 | 医疗/法律护栏 |
| TOP | 最强模型 | 极端复杂场景 |

6 个 Provider 全部注册：Xiaomi / DeepSeek / Zhipu / Hunyuan / DashScope / SiliconFlow

4 种调用模式：`chat` (单次) / `stream` (流式) / `reason` (推理增强) / `with_tools` (工具调用)

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-LLM-001 | 9+ Tier 路由 | P1 | complexity-based routing 正确选择 tier：简单→FREE，复杂→CAPABLE，极端→TOP | llm_service 单测 |
| AI-LLM-002 | 6 Provider 可用 | P1 | 每个provider至少1个模型可正常调用，不单点依赖 | provider_ping 测试 |
| AI-LLM-003 | Agent-Aware 路由 | P1 | 不同 agent (study_buddy/exam_oracle/deep_analyst) 路由到适合的模型 | agent 路由测试 |
| AI-LLM-004 | 降级 fallback | P0 | 主模型不可达时自动 fallback 到备用模型，不中断用户 | 模拟主模型宕机 |
| AI-LLM-005 | 成本追踪 | P2 | 每次调用记录 input/output tokens + 成本 | TokenTracker 验证 |
| AI-LLM-006 | 超时控制 | P1 | LLM 调用有超时限制，不无限等待 | 超时配置检查 |
| AI-LLM-007 | 安全输出 | P0 | LLM 输出不包含有害/歧视/医疗诊断内容 | 安全测试 |
| AI-LLM-008 | 流式响应 | P0 | gRPC server-streaming 正确推送 delta 到 Go Gateway | `StreamChat` 测试 |
| AI-LLM-009 | 工具调用模式 | P1 | with_tools 模式正确序列化工具定义 + 解析工具调用响应 | tool_call 测试 |
| AI-LLM-010 | Provider 故障隔离 | P1 | 单个 provider 故障不影响其他 provider 调用 | provider 故障模拟 |

## 3.3 工具系统

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-TOOL-001 | 工具注册 | P1 | 37 工具类全部注册到 DynamicToolRegistry | `get_all_tools()` |
| AI-TOOL-002 | 工具调用闭环 | P1 | AI 调用工具→客户端确认→结果回传→AI 继续回答 | `ai_chat_multiturn_acceptance.py` |
| AI-TOOL-003 | 权限控制 | P1 | 工具调用有权限检查，不越权 | 工具权限测试 |
| AI-TOOL-004 | 错误处理 | P2 | 工具调用超时/失败有 graceful fallback | 模拟工具失败 |

## 3.4 Memory 系统（3 Lanes / Evidence-Based / Versioned）

Memory 系统采用 3 通道写入架构：

| Lane | 方法 | 触发条件 |
|------|------|---------|
| **Direct Capture** | `upsert_preference()` | 用户明确表达的偏好/目标/设置 |
| **Inferred Extraction** | `create_episodic_memory()` | AI 从对话中推断，需遵守 Rule Y 7 条硬规则 |
| **User State** | 状态聚合器写入 | 行为信号/学习状态/情绪指标 |

每条记忆包含：`evidence`（证据来源）+ `confidence`（置信度 0-1）+ `scope`（作用域）+ `version`（版本号）

纠正机制：`apply_correction()` 用户纠正 → `retract_memory()` 用户撤回

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-MEM-001 | Direct Capture Lane | P1 | upsert_preference() 正确写入用户明确偏好，含 evidence + confidence + scope | `memory_acceptance.py` |
| AI-MEM-002 | Inferred Lane | P0 | create_episodic_memory() 遵守 Rule Y 7 条硬规则（SGW-H001~H007），每条推断有 evidence | `check_rule_y_inferred_extraction.py` |
| AI-MEM-003 | User State Lane | P1 | 状态聚合器写入行为/学习/情绪指标，不影响 long_term preference | Lane 隔离测试 |
| AI-MEM-004 | Evidence 评分 | P1 | 每条记忆有 evidence 引用来源，confidence ∈ [0,1]，无 evidence 的推断记忆被拒绝 | evidence 测试 |
| AI-MEM-005 | 版本管理 | P2 | 记忆变更有 version 递增，旧版本可追溯 | 版本测试 |
| AI-MEM-006 | 记忆检索 | P1 | 后续对话可命中已写入记忆，按 relevance + confidence 排序 | 记忆检索测试 |
| AI-MEM-007 | 作用域隔离 | P1 | turn/session/task/day/sprint/goal 作用域正确，不污染 long_term | Rule Y guard |
| AI-MEM-008 | 用户纠正 | P1 | apply_correction() 更新记忆 + retract_memory() 删除记忆，AI 后续行为反映纠正 | 纠正测试 |
| AI-MEM-009 | 用户控制 | P1 | 用户可查看/删除/关闭长期记忆 | Memory Settings API |
| AI-MEM-010 | PII 脱敏 | P0 | 记忆存储中 PII 已脱敏（sha256_token + HMAC），脱敏不可逆 | Privacy audit |
| AI-MEM-011 | 衰减 | P2 | 过期记忆自动衰减置信度，decay_rate 按时间/使用频率动态调整 | Celery 任务验证 |

## 3.5 RAG / 知识检索（GraphRAG + Multi-Hop + HyDE）

GraphRAG retrieve() 支持三种检索路径：

| 模式 | 触发条件 | 检索策略 |
|------|---------|---------|
| **Fastpath** | 单跳即可命中 | pgvector similarity → 直接返回 top-k |
| **Sequential** | 需要推理链 | pgvector → graph traversal → 逐跳展开 |
| **Multi-Hop** | 复杂跨域问题 | 向量搜索 + 图谱遍历交替，最多 3 跳，HyDE 增强 |

后处理：`filter_retrieved_chunks()` 按相关性/噪声/重复过滤 + 重排序

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-RAG-001 | 混合搜索 | P1 | Redis FT.SEARCH → pgvector → keyword 三级 fallback 正常 | 搜索测试 |
| AI-RAG-002 | Embedding | P1 | DashScope/SiliconFlow embedding 生成正常，1024 维 | embedding_service 测试 |
| AI-RAG-003 | Fastpath 模式 | P1 | 单跳查询在 pgvector 直接命中，延迟 < 200ms | fastpath benchmark |
| AI-RAG-004 | Multi-Hop 推理 | P2 | 复杂问题最多 3 跳图遍历，每跳有相关性衰减 | multi-hop 测试 |
| AI-RAG-005 | HyDE 增强 | P2 | 假设文档嵌入(HyDE)提升低相关性查询的召回率 ≥ 15% | HyDE 对比测试 |
| AI-RAG-006 | 后处理过滤 | P1 | filter_retrieved_chunks() 过滤噪声/重复/低相关性资料，质量分数 > 阈值 | 过滤测试 |
| AI-RAG-007 | Token Budget | P1 | 每轮检索有 token 预算，不超限，超出时按相关性裁剪 | token_tracker |
| AI-RAG-008 | 引用追溯 | P2 | AI 回答可追溯到源资料片段，retrieval trace 包含 node_id + source + score | 引用测试 |
| AI-RAG-009 | 检索遥测 | P2 | 每次检索记录 mode/hops/chunks_filtered/latency 到 telemetry | telemetry 检查 |

## 3.6 Plan 系统（Two-Tier Review / Auto-Approval / Alignment Scoring）

计划审查采用两层架构：

```
Tier 1 — 快速规则检查 (quick_rule_check)
  → 检查：deadline 可行性 / 任务数量合理 / 无重复任务 / 知识覆盖
  → 结果：PASS → auto-approve / FAIL → 进入 Tier 2

Tier 2 — 深度 LLM 审查 (llm_review)
  → 检查：目标对齐度 / 策略合理性 / 资源匹配 / 风险评估
  → validate_feasibility() 综合评估

对齐评分：alignment_score = 目标匹配度 × 策略权重 × 资源覆盖率
```

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-PLAN-001 | 计划生成 | P1 | 基于目标/deadline/资料/掌握度/时间生成个性化计划 | `galaxy_plan_acceptance.py` |
| AI-PLAN-002 | Tier 1 规则检查 | P1 | quick_rule_check() 检查 deadline 可行性/任务数量/重复/知识覆盖，5 项规则全过 | review 单测 |
| AI-PLAN-003 | Tier 2 LLM 审查 | P1 | llm_review() 深度审查目标对齐/策略合理性/资源匹配/风险，产出详细审查报告 | review 单测 |
| AI-PLAN-004 | 可行性验证 | P1 | validate_feasibility() 综合评估计划可行性，不可行计划被拒绝并给出原因 | feasibility 测试 |
| AI-PLAN-005 | 自动批准 | P2 | Tier 1 PASS 的安全计划自动批准，不需人工介入 | auto-approve 测试 |
| AI-PLAN-006 | 对齐评分 | P2 | alignment_score = 目标匹配度 × 策略权重 × 资源覆盖率，分数量化可追溯 | alignment 测试 |
| AI-PLAN-007 | 拒绝追踪 | P2 | 被拒绝的计划有 rejection_reason + suggested_fixes，用户可看到改进建议 | rejection 测试 |
| AI-PLAN-008 | 适应性重规划 | P1 | 任务失败/错因重复/资料失效时局部重规划，不推翻全部计划 | `adaptive_replanner.py` |
| AI-PLAN-009 | 版本管理 | P2 | 计划变更有版本号 + 原因 + diff，可回溯到任意版本 | 计划版本测试 |
| AI-PLAN-010 | Exam Sprint | P1 | 7 天 survival / 14 天 build-and-retrieve / standard 三模式策略正确 | exam_sprint 测试 |
| AI-PLAN-011 | 计划与任务一致 | P1 | 任务卡可追溯计划节点，计划可查看任务完成反馈，双向链接完整 | 链路测试 |

## 3.7 gRPC 服务

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-GRPC-001 | AgentService | P0 | Chat/GetPlan/StreamReply/SubmitFeedback/HealthCheck 全部可用 | `grpcurl` |
| AI-GRPC-002 | GalaxyService | P1 | 9 RPC 方法全部实现 | `grpcurl` |
| AI-GRPC-003 | ErrorBookService | P1 | 6 CRUD + AnalyzeError 可用 | `grpcurl` |
| AI-GRPC-004 | STTService | P2 | TranscribeAudio/EnhanceTranscript 可用 | STT 测试 |
| AI-GRPC-005 | InferenceService | P2 | RunInference 统一 LLM 调度可用 | inference 测试 |

## 3.8 Celery 任务

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AI-CEL-001 | Worker 稳定 | P1 | celery worker 正常启动，70+ 任务注册 | `make celery-status` |
| AI-CEL-002 | 定时任务 | P1 | 15min/hourly/6h/daily/weekly 全部调度正确 | `celery_schedule.py` 检查 |
| AI-CEL-003 | L4 异步学习 | P2 | DailyGoalReflection/PolicyEffectCompaction/SkillCandidate/SourceEffectiveness/CommunityAggregation/StateDecay 6 个 L4 job 正常产出候选 | L4 输出验证 |
| AI-CEL-004 | 失败重试 | P1 | 任务失败有重试 + DLQ，不静默吞异常 | DLQ 检查 |

---

# 4. Aurora 认知核心验收

## 4.0 组件清单（深度审计确认）

Aurora 由 12 个核心模块组成（~20K 行实现），全部已落地：

| 模块 | 文件 | 行数 | 职责 |
|------|------|------|------|
| Decision Loop | `aurora/decision_loop.py` | 1,833 | 纯 LLM 推理决策，非用户文本直接输出 |
| Dashboard | `aurora/dashboard.py` | 1,756 | 覆盖度读数：covered/missing/recently_asked domains |
| Chat Adapter | `aurora/chat_adapter.py` | 843 | 决策意图→1-3 条用户消息，每条 ≤260 字 |
| State Aggregator | `state_aggregator/service.py` | 2,755 | 20+ 维度状态聚合，写入隔离 |
| Aurora State | `aurora/state.py` | 791 | L0-L4 能量级状态管理 |
| Planning | `aurora/planning.py` | 1,149 | 适应性规划/策略调整 |
| Checkpoint Runtime | `aurora/checkpoint_runtime.py` | 1,419 | 会话检查点/恢复 |
| Control Surface | `aurora/control_surface.py` | 339 | 5 参数读写 + 硬边界强制 |
| Wake Policy | `aurora/wake_policy.py` | 1,110 | 唤醒策略/时机控制 |
| Telemetry | `aurora/telemetry.py` | 1,144 | 遥测/审计日志 |
| Self Model | `aurora/self_model.py` | 883 | 自我认知建模 + 建模维度边界 |
| Write Pipeline | `aurora/write_pipeline.py` | 1,099 | 写入管道 + 纠正反馈 + PII 过滤 |

## 4.1 Aurora 三层架构

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AUR-001 | Decision Loop | P1 | AuroraDecisionLoop.decide() 纯 LLM 推理产出决策（非用户文本） | `aurora_v1_acceptance.py` |
| AUR-002 | Dashboard Readout | P1 | DashboardReadoutBuilder 产出覆盖 covered/missing/recently_asked domains | dashboard 测试 |
| AUR-003 | Chat Adapter | P1 | ChatLayerAdapter.render() 将决策意图转为 1-3 条用户消息，每条 ≤260 字 | chat_adapter 测试 |
| AUR-004 | L0 规则层 | P1 | L0 无需 LLM，处理时间/任务状态/deadline/DND/基础事件 | L0 测试 |
| AUR-005 | L1 轻量层 | P1 | L1 每轮参与路由/上下文/语气/策略参数/升级判断 | L1 测试 |
| AUR-006 | L2 中度层 | P2 | L2 在失败/错因重复/偏离/冲突时介入 | L2 测试 |
| AUR-007 | L3 全核心 | P2 | Full Aurora Core 限时交互式建模会话可用 | Aurora Core 测试 |
| AUR-008 | L4 异步 | P2 | L4 后台学习产出候选，不直接改 live state | L4 输出验证 |

## 4.2 Control Surface

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AUR-CS-001 | 5 参数 | P1 | proactive_intensity/next_wake_at/conversation_style/agenda_priority/task_density_hint 全部可读写 | control_surface 测试 |
| AUR-CS-002 | 硬边界 | P0 | DND 时段/隐私边界/禁用动作由系统强制，Aurora 不可覆盖 | 边界测试 |
| AUR-CS-003 | 建模边界 | P0 | 允许的维度 vs 禁止的维度（clinical/personality/social-identity）强制执行 | `check_rule_ao_no_diagnostic_labels.py` |

## 4.3 Kill Switch

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AUR-KS-001 | 三态协议 | P0 | off → shadow → live 三态切换正确，每个功能独立 | KillSwitchBinding 测试 |
| AUR-KS-002 | 24 服务 | P1 | Stage 18-40 + dual_core + doc_context 等 24 个 kill switch 服务全部注册 | `check_rule_av_kill_switch_mode_enum.py` |
| AUR-KS-003 | Prometheus | P1 | `sparkle_kill_switch_mode{stage,feature}` gauge 指标暴露 | metrics 端点检查 |

## 4.4 状态聚合

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AUR-SA-001 | 20+ 维度 | P1 | commitment/policies/reflections/social/scenes/foresight/engagement/emotion/learning/WM/task/calendar/traits/SRL/metacognition/idiographic 全部聚合 | StateAggregatorService 测试 |
| AUR-SA-002 | 写入隔离 | P0 | 各聚合器只写自己的维度，不越权 | `check_rule_k_write_paths.py` |

## 4.5 Self Model & Write Pipeline

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| AUR-SM-001 | 建模维度白名单 | P0 | self_model.py 只对允许的维度建模，clinical/personality/social-identity 硬拒绝 | `self_model_test.py` |
| AUR-SM-002 | 纠正反馈 | P1 | write_pipeline.py 支持 apply_correction() + retract_memory()，用户纠正写入模型 | correction 测试 |
| AUR-SM-003 | PII 过滤 | P0 | write_pipeline 写入前 PII 过滤（sha256_token + HMAC） | PII audit |
| AUR-SM-004 | 审计日志 | P1 | telemetry.py 每次决策写入审计日志，可追溯 | audit log 检查 |
| AUR-SM-005 | 唤醒策略 | P1 | wake_policy.py 基于用户状态/时间/优先级决定唤醒时机 | wake policy 测试 |

---

# 5. Flutter 移动端验收

## 5.1 核心 UI

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-UI-001 | 首页 | P1 | 首页围绕目标推进，不是功能宫格 | 人工回归 |
| FL-UI-002 | 聊天页 | P1 | 流式消息/状态带/Context Receipt/任务卡/预测选项统一呈现 | 人工回归 |
| FL-UI-003 | 星图页 | P1 | 力导向图谱渲染流畅，节点交互（点击/缩放/搜索）正常 | 人工回归 |
| FL-UI-004 | 任务页 | P1 | 任务卡展示完整执行协议，简洁模式+展开详情 | 人工回归 |
| FL-UI-005 | 社群页 | P1 | 社群围绕承诺/共性错因/资源质量，不是无关信息流 | 人工回归 |
| FL-UI-006 | 设置页 | P1 | 用户可管理记忆/社群/资料/提醒/关系偏好 | 人工回归 |
| FL-UI-007 | 35 功能模块 | P1 | 35 feature 模块（120+ screens）全部可导航，无死页 | navigation 测试 |
| FL-UI-008 | 31 路由模块 | P1 | GoRouter 31 个 feature route 全部注册，auth guard 正确 | `app/routes.dart` |

## 5.2 WebSocket 连接

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-WS-001 | 连接稳定 | P0 | WebSocket v2 连接建立、心跳、断连重连正常 | `websocket_chat_service_v2_test.dart` |
| FL-WS-002 | 指数退避 | P1 | 6 级退避 (800ms→12.2s+jitter)，重连不冲击服务端 | 退避测试 |
| FL-WS-003 | 401 自动恢复 | P1 | Token 过期自动刷新 + 重连，用户无感知 | Token 过期测试 |
| FL-WS-004 | 离线队列 | P1 | Isar 持久化离线消息，恢复后幂等同步 | 离线测试 |
| FL-WS-005 | 大帧优化 | P2 | >12KB 帧在 isolate 解析，不阻塞 UI | 性能测试 |
| FL-WS-006 | 消息去重 | P1 | 50 消息 pending 限制 + 去重机制 | 去重测试 |

## 5.3 离线能力

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-OFF-001 | Outbox 模式 | P1 | 离线操作存入 Outbox，恢复后批量同步 | `sync_engine_test.dart` |
| FL-OFF-002 | CRDT | P2 | 图谱掌握度/任务状态离线多端无冲突合并 | `crdt_sync_manager_test.dart` |
| FL-OFF-003 | 本地存储 | P1 | Isar 结构化数据 + Hive KV，数据持久化可靠 | 存储测试 |
| FL-OFF-004 | 连接监控 | P1 | NetworkMonitor 正确感知在线/离线状态 | `connectivity_provider_test.dart` |

## 5.4 国际化

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-I18N-001 | 双语覆盖 | P1 | app_en.arb (606 keys) + app_zh.arb (609 keys) 完整覆盖 | ARB key 对比 |
| FL-I18N-002 | 运行时切换 | P2 | 语言切换即时生效，无需重启 | 切换测试 |
| FL-I18N-003 | 无硬编码 | P1 | 用户可见文案 100% 来自 ARB，无硬编码中英文字符串 | `check_hardcoded_strings` |
| FL-I18N-004 | Agent Overlays | P2 | 6 个 persona ARB overlay 文件加载正确 | overlay 测试 |

## 5.5 可访问性

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-A11Y-001 | 字体缩放 | P2 | 0.85x-1.4x 字体缩放不破坏布局 | `a11y_touch_target_test.dart` |
| FL-A11Y-002 | 高对比度 | P2 | 高对比度模式颜色对比度达标 | `a11y_contrast_test.dart` |
| FL-A11Y-003 | 触控目标 | P2 | 最小 48dp 触控目标 | `a11y_touch_target_test.dart` |
| FL-A11Y-004 | Reduce Motion | P2 | 减弱动画模式生效 | 设计系统检查 |
| FL-A11Y-005 | 色盲友好 | P2 | Wong 2011 色盲友好调色板 | 设计系统检查 |
| FL-A11Y-006 | 语义标签 | P2 | 25+ semantic label strings in l10n | `a11y_semantic_labels_test.dart` |

## 5.6 推送通知

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-PUSH-001 | 双通道 | P1 | FCM (国际) + JPush (中国 Android) 正常推送 | 推送测试 |
| FL-PUSH-002 | 深度链接 | P1 | 推送点击导航到正确目标/任务/召回上下文 | `push_navigation_service_test.dart` |
| FL-PUSH-003 | 静默时间 | P1 | 尊重用户通知偏好和静默时段 | 通知设置测试 |
| FL-PUSH-004 | 徽章管理 | P2 | iOS badge 正确更新 | iOS 测试 |

## 5.7 设计系统

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-DS-001 | Design Tokens | P1 | 颜色/间距/排版/动画 Token 全部通过 DS 类访问 | `design_validator.dart` |
| FL-DS-002 | 暗色模式 | P1 | System/Light/Dark 三模式 + 3 品牌预设全部正确渲染 | Golden tests |
| FL-DS-003 | 组件库 | P2 | 6 Atom + 1 Molecule + 1 Organism + 30 设计组件可用 | 组件测试 |
| FL-DS-004 | 皮肤系统 | P2 | Shop 皮肤系统 equip/unequip 正常 | 皮肤测试 |

## 5.8 性能

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-PERF-001 | 首屏加载 | P1 | 冷启动到首屏 < 3s | `flutter_core_bench_test.dart` |
| FL-PERF-002 | 聊天流 | P1 | AI 响应流式渲染不卡顿 | 性能测试 |
| FL-PERF-003 | 星图渲染 | P2 | 力导向布局 500+ 节点不卡顿 | 性能测试 |
| FL-PERF-004 | 内存使用 | P2 | 长时间使用无内存泄漏 | 内存分析 |
| FL-PERF-005 | SmartCache | P2 | LRU + TTL 缓存命中率合理 | 缓存测试 |

## 5.9 错误处理

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-ERR-001 | Sealed Failure | P1 | 6 类 AppFailure 正确映射，bilingual userMessage 显示 | 错误测试 |
| FL-ERR-002 | 温和降级 | P1 | LLM/RAG/网络失败时 UI 显示温和错误页，非红屏 | `CustomErrorWidget` 测试 |
| FL-ERR-003 | 离线提示 | P2 | OfflineBanner 自动显示/隐藏 | 离线测试 |
| FL-ERR-004 | 全局捕获 | P1 | FlutterError.onError + PlatformDispatcher.onError 有 crash 上报 | `PerformanceMonitor.reportCrash` |

## 5.10 认证流程

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| FL-AUTH-001 | 完整流程 | P0 | 注册→登录→Token管理→登出→Token刷新全链路 | `auth_flow_test.dart` |
| FL-AUTH-002 | 社交登录 | P1 | Google/Apple/WeChat 登录可用 | 社交登录测试 |
| FL-AUTH-003 | 访客模式 | P2 | Guest 登录 + Guest→Full 升级流程正确 | 访客测试 |
| FL-AUTH-004 | 安全存储 | P0 | Token 存储使用 flutter_secure_storage | 安全检查 |

---

# 6. 知识星图 / Galaxy 系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| GAL-001 | 图谱 CRUD | P1 | 节点/边创建、查询、更新、删除正常 | `galaxy_plan_acceptance.py` |
| GAL-002 | 掌握度 | P1 | 完成学习动作后 mastery 增长，BKT 概率更新 | 掌握度测试 |
| GAL-003 | 语义搜索 | P1 | 语义向量搜索返回相关节点 + 相似度分数 | 搜索测试 |
| GAL-004 | 学习路径 | P2 | BFS 路径查找，从当前节点到目标节点生成学习路径 | 路径测试 |
| GAL-005 | 协作图谱 | P2 | CRDT 同步多用户协作编辑，冲突合并正确 | `collaborative_service.py` |
| GAL-006 | 节点扩展 | P2 | LLM 节点扩展生成候选新节点 | expansion 测试 |
| GAL-007 | 复习建议 | P1 | 按掌握度+遗忘曲线给出复习建议 | review 测试 |
| GAL-008 | 50+ API | P1 | 50+ Galaxy REST API 全部可用 | API 合同测试 |
| GAL-009 | 事件消费 | P1 | error_created/task.completed/node_mastery_updated 事件正确消费 | galaxy_event_consumer |
| GAL-010 | 资料挂载 | P1 | 资料可挂载到节点，显示覆盖/质量/缺口 | 资料挂载测试 |
| GAL-011 | Flutter 渲染 | P1 | WebGL shader 背景 + 力导向布局 + 预测性视口预加载 | 人工回归 |
| GAL-012 | 14 子服务 | P2 | 14 个 Galaxy 子服务（facade/retrieval/structure/stats/evolution/rag/ontology/collaborative/crdt/feedback/provenance/streaming/review_urgency）全部可用 | 服务测试 |

---

# 7. 任务卡 / Plan 系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| TASK-001 | 任务卡协议 | P1 | why_this_task / materials / steps / stuck / success / min_output / fallback 结构完整 | 任务卡检查 |
| TASK-002 | 状态流转 | P1 | PENDING → IN_PROGRESS → COMPLETED/ABANDONED + start/pause/resume/abandon/restore | `task_card_flow_test.dart` |
| TASK-003 | 卡住分流 | P1 | "我卡住了" 触发不同 ContextPlan（看不懂/不会做题/时间不够/状态不行） | 卡住测试 |
| TASK-004 | 时间恢复 | P2 | 用户离开后回来，识别时间流逝，提供恢复卡 | 时间恢复测试 |
| TASK-005 | 离线执行 | P2 | 离线执行任务后，恢复网络同步状态 | `task_offline_queue_p2_10_test.dart` |
| TASK-006 | 用户覆盖 | P1 | 用户可缩短/延后/替换/拒绝任务 | 覆盖测试 |
| TASK-007 | 完成更新 | P1 | 任务完成更新 knowledge/mastery/mistake/task_granularity | 更新验证 |
| TASK-008 | 失败归因 | P1 | 任务失败后系统归因（不直接责备），更新 task_granularity/knowledge_bottleneck | 失败测试 |

---

# 8. 社群 / Community 系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| COM-001 | 好友系统 | P1 | 好友请求/接受/删除/屏蔽/搜索全链路 | `community_acceptance.py` |
| COM-002 | 群组系统 | P1 | SQUAD/SPRINT/OFFICIAL 三类群组 CRUD + 成员管理 + 角色权限 | 群组测试 |
| COM-003 | 实时消息 | P1 | WebSocket 群聊/私聊正常，消息类型（TEXT/TASK_SHARE/PLAN_SHARE/FILE_SHARE/ACHIEVEMENT/CHECKIN）全部支持 | 消息测试 |
| COM-004 | 责任伙伴 | P1 | Accountability MVP：承诺创建/伙伴提醒/见证/观察候选 | `accountability_acceptance.py` |
| COM-005 | 伙伴隐私 | P0 | 伙伴解释类反馈 → candidate，用户确认前不写模型；用户拒绝后不再用于策略 | `check_rule_z_social_boundary.py` |
| COM-006 | 匿名聚合 | P1 | 社群共性错因匿名聚合，k-阈值保护 | 聚合测试 |
| COM-007 | 资源质量 | P2 | 共享资料基于使用效果评价，非单纯点赞 | 资源质量测试 |
| COM-008 | 信号桥接 | P1 | CommunitySignalBridge 将社群信号桥接到个人系统 | bridge 测试 |
| COM-009 | Opt-out | P1 | 用户可关闭社群智能或某类社群信号 | 设置测试 |
| COM-010 | 管理工具 | P2 | Moderation/Report/Broadcast 管理工具可用 | admin 测试 |

---

# 9. 成就 / 成长系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| ACH-001 | 成就引擎 | P1 | AchievementEngine 5 prestige lane + 成就解锁 + streak + combo + milestone | `achievement_visual_acceptance.py` |
| ACH-002 | 光子系统 | P1 | PhotonService 授予/扣除/转移/历史全部正常 | `photons API` |
| ACH-003 | Spark 契约 | P2 | SparkContract 学习承诺机制可用 | 契约测试 |
| ACH-004 | 事件驱动 | P1 | AchievementEventConsumer 处理 task completion/focus session/node update/community share | 消费者测试 |
| ACH-005 | 责任伙伴成就 | P2 | AccountabilityAchievementService streak/perfect month/mutual support | 伙伴成就测试 |
| ACH-006 | 成长信号 | P2 | 成就事件转为 GrowthSignal 候选，不单纯展示 badge | 信号测试 |
| ACH-007 | 成长叙事 | P2 | GrowthChronicle 长期洞察 pending/confirmed/edited/rejected 状态 | 叙事测试 |
| ACH-008 | 用户确认 | P1 | 长期洞察需用户确认，未确认不作为硬约束 | 确认测试 |

---

# 10. 错题本系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| ERR-001 | 错题 CRUD | P1 | 文本/图片错题录入，字段完整，落库成功 | `notes_errorbook_acceptance.py` |
| ERR-002 | AI 诊断 | P1 | 错因类型/根因/建议知识点 AI 分析正常 | `AnalyzeError` RPC |
| ERR-003 | 复习调度 | P1 | SM-2 间隔重复调度，next_review_at 正确变化 | 调度测试 |
| ERR-004 | 语义关联 | P2 | 错题关联知识图谱节点，影响节点状态 | 关联测试 |
| ERR-005 | 社群聚合 | P2 | 社群错因聚合统计，匿名化处理 | 聚合测试 |

---

# 11. 事件系统验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| EVT-001 | EventBus | P1 | Redis Streams 发布/消费/消费组/重试正常 | `event_bus_health` API |
| EVT-002 | 18 事件类型 | P1 | KnowledgeNodeUpdated/TaskCompleted/ErrorCreated/ProfileUpdated 等 18+ 事件类型全部定义 | event_types.py |
| EVT-003 | 16 消费者 | P1 | Achievement/Capsule/Cognitive/Document/Execution/Galaxy/GroupFile/Intervention/MainChain/Nudge/PlanHealth/Preference/Profile/SocialSignal/Task 消费者全部运行 | 消费者状态 |
| EVT-004 | DLQ | P1 | 死信队列有人工/自动处理路径 | DLQ admin API |
| EVT-005 | 跨层 trace | P1 | 事件携带 trace_id/user_id/goal_id/event_id，Flutter→Go→Python 可关联 | trace 检查 |
| EVT-006 | 幂等 | P1 | 事件重放幂等，不重复写状态 | 重放测试 |
| EVT-007 | 背压 | P2 | 消费堆积有告警和限流 | 消费 lag 监控 |

---

# 12. 安全与隐私验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| SEC-001 | 无硬编码密钥 | P0 | 代码中无 hardcoded secrets/tokens/passwords | `check_rule_bi_hardcoded_secrets.py` |
| SEC-002 | .env 管理 | P0 | 所有密钥通过 .env 文件管理，.env 在 .gitignore | gitignore 检查 |
| SEC-003 | SQL 注入防护 | P0 | 所有 SQL 查询使用参数化语句 | 代码审计 |
| SEC-004 | XSS 防护 | P0 | WebSocket 消息经 bluemonday 净化 | 安全测试 |
| SEC-005 | Rate Limit | P0 | IP(10/s) + Auth(5/s) + WS(5/min) + Distributed(Redis) 限流生效 | 压测 |
| SEC-006 | PII 脱敏 | P0 | 日志/研究集/LLM 输入 PII 按策略脱敏 | logsafe 测试 |
| SEC-007 | 建模边界 | P0 | 禁止 clinical/personality/social-identity 越界建模，系统强制拦截 | `check_rule_ao_no_diagnostic_labels.py` |
| SEC-008 | Kill Switch | P0 | Aurora/RAG/实验/Skill/社群/召回/P4 全部有 off/shadow/live | KillSwitch 测试 |
| SEC-009 | 数据主权 | P1 | 用户能查看/导出/删除关键数据 | data_export API |
| SEC-010 | 合规 | P1 | 年龄门控/删除协议/加密擦除/法律保留可用 | compliance 测试 |
| SEC-011 | 审计日志 | P2 | 管理员操作/策略发布/实验晋升/数据导出有审计 | audit_log 测试 |
| SEC-012 | 年龄门控 | P1 | `age_gate.py` + `deletion_protocol.py` + `crypto_erase.py` 可用 | compliance 测试 |
| SEC-013 | 金融原子性 | P0 | 光子授予/扣除原子操作，幂等键保护 | `check_rule_bb_financial_atomicity.py` |

---

# 13. 监控与可观测性验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| OBS-001 | Prometheus | P1 | Gateway(:8080) + Backend(:8000) 指标采集正常 | Prometheus targets |
| OBS-002 | Grafana | P1 | 15+ dashboards (AI Agent/API Health/Community/Data/Gateway/Mobile/Product/Production/Spine) 全部可查看 | Grafana UI |
| OBS-003 | Alerting | P1 | 20+ alert rules (P1: GatewayDown/BackendDown, P2: 5xx/Latency/Lag, P3: Context/Feed/Loop) | Alertmanager |
| OBS-004 | Loki | P2 | 日志聚合 + Promtail 采集正常 | Loki query |
| OBS-005 | Tempo | P2 | 分布式追踪 (OTLP) 正常 | Tempo query |
| OBS-006 | SLO | P1 | Gateway ≥99.9% | Backend ≥99.9% | 5xx ≤2% | P95 ≤1.5s | Lag ≤120s | SLO dashboard |
| OBS-007 | Runbook | P2 | 每类告警有运行手册 | `monitoring/runbooks/` |
| OBS-008 | 业务指标 | P2 | Spine/Aurora/RAG/Learning/Community 指标入 Prometheus | 业务 dashboard |

---

# 14. 测试与质量门验收

## 14.1 测试覆盖

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| QA-001 | Python 测试 | P1 | 905 test files / ~7,619 test cases，覆盖率 ≥50% | `pytest --cov` |
| QA-002 | Go 测试 | P1 | 77 test files / ~557 test cases，覆盖率 ≥30% | `go test -cover` |
| QA-003 | Flutter 测试 | P1 | 287 test files，覆盖率 ≥25% | `flutter test --coverage` |
| QA-004 | E2E 测试 | P1 | chat/galaxy/plan/offline/integration 等 E2E 场景测试通过 | E2E suite |
| QA-005 | 集成测试 | P2 | 10 Flutter integration tests (app_launch/auth_flow/checkin_feedback/goal_creation 等) 通过 | `flutter test integration_test` |
| QA-006 | Golden 测试 | P2 | 7 golden tests (dashboard/chat/accessibility/notification/emotion/i18n) 通过 | golden test |
| QA-007 | 性能测试 | P2 | Benchmark + Load test 有基线 | benchmark suite |

## 14.2 治理规则

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| QA-GOV-001 | Rule Guards | P0 | 69 条治理规则全部 PASS | `bash scripts/run_all_rule_guards.sh` |
| QA-GOV-002 | Tech Debt | P1 | 5 项 tech debt budget 不超标 | `python scripts/check_tech_debt_budget.py` |
| QA-GOV-003 | Coverage Thresholds | P1 | Python 50% / Go 30% / Flutter 25% 全局阈值达标 | `check_coverage_thresholds.py` |
| QA-GOV-004 | Proto Parity | P1 | Python/Go proto 生成代码一致 | `check_rule_bg_proto_cross_language_parity.py` |
| QA-GOV-005 | 安全扫描 | P0 | Trivy + Gitleaks 无高危发现 | CI security-scan |
| QA-GOV-006 | Lint 全过 | P1 | golangci-lint (22 linters) + ruff + mypy + flutter analyze 零错误 | CI lint |

## 14.3 验收脚本

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| QA-SCRIPT-001 | 21 验收脚本 | P1 | ai_chat_multiturn / accountability / galaxy_plan / achievement / seed_library / insights / cognitive / community / focus / calendar / memory / errorbook / translation / document_stt / long_term_plan / celery / security / api_contract / community_admin / ai_expert / aurora_v1 全部通过 | `backend/scripts/*_acceptance.py` |
| QA-SCRIPT-002 | Journey Smoke | P2 | `scripts/journey_smoke.sh all` 通过 | journey smoke |
| QA-SCRIPT-003 | Local Signoff | P1 | `make local-final-signoff` 全部通过 | signoff suite |

---

# 15. CI/CD 与部署验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| CICD-001 | Main CI | P0 | lint + backend-test + flutter-test + security-scan 全部绿色 | GitHub Actions |
| CICD-002 | E2E Smoke | P1 | E2E smoke workflow 通过 | e2e-smoke workflow |
| CICD-003 | Quality Baseline | P1 | Quality baseline workflow 通过 | quality-baseline workflow |
| CICD-004 | Deploy Prod | P3 | deploy-prod workflow 可用（首版可手动触发） | workflow 检查 |
| CICD-005 | K8s 配置 | P3 | base/gateway.yaml + base/backend.yaml + prod blue/green 配置有效 | K8s 检查 |
| CICD-006 | 数据库迁移 | P1 | `alembic upgrade head` 可在空库执行，不报错 | 空库迁移测试 |
| CICD-007 | Proto 生成 | P1 | `make proto-gen` 后 Go/Python/Flutter 生成代码一致 | proto-gen 检查 |

---

# 16. SGW (Simulated Gray Window) 验收

| ID | 项 | 分类 | 验收标准 | 验证方法 |
|----|-----|------|---------|---------|
| SGW-001 | 墙钟时长 | P1 | ≥12 小时不中断运行 | SGW 报告 |
| SGW-002 | Persona 覆盖 | P1 | ≥44 个 persona 覆盖 | persona_library.json |
| SGW-003 | Sessions | P1 | ≥360 完成会话 | checkpoint |
| SGW-004 | Turns | P1 | ≥4,000 累计对话轮次 | checkpoint |
| SGW-005 | 硬违规 | P0 | =0 硬违规（7 条规则全部通过） | hard_violation_rules.py |
| SGW-006 | 软违规率 | P1 | <5% 软违规率（审计采样） | metrics_collector |

---

# 17. 端到端核心旅程验收

以下每个旅程必须人工或脚本完整走通。

## 17.1 新用户首次体验

| ID | 旅程 | 分类 | 验收标准 |
|----|------|------|---------|
| JOURNEY-001 | 注册→登录→首屏 | P0 | 30 秒内完成，首屏显示目标推进而非功能宫格 |
| JOURNEY-002 | 输入目标"7天考试先过" | P1 | 60 秒内识别 exam_rescue 模式，给出场景判断 |
| JOURNEY-003 | 上传课件 | P1 | 文件上传成功，生成知识节点，挂载到图谱 |
| JOURNEY-004 | 获得计划 | P1 | 基于目标+资料+deadline 生成个性化计划 |
| JOURNEY-005 | 执行任务卡 | P1 | 任务卡有 why/materials/steps/stuck/success，可开始执行 |
| JOURNEY-006 | 完成任务 | P1 | 任务完成→知识节点掌握度变化→计划进度更新 |
| JOURNEY-007 | 卡住恢复 | P1 | "我卡住了"→区分卡点类型→改变策略 |

## 17.2 长期用户旅程

| ID | 旅程 | 分类 | 验收标准 |
|----|------|------|---------|
| JOURNEY-008 | 老用户回归 | P2 | 回归时系统加载历史，不从头开始 |
| JOURNEY-009 | 多目标 | P2 | 可同时存在多个目标，状态不互相污染 |
| JOURNEY-010 | 计划调整 | P1 | 任务失败后系统归因+调整，不直接责备 |
| JOURNEY-011 | 社群互动 | P2 | 好友/群组/承诺/见证全部可用 |
| JOURNEY-012 | 离线→在线 | P1 | 离线执行任务后恢复网络，状态正确同步 |

## 17.3 体验"神性时刻"

| ID | 时刻 | 分类 | 验收标准 |
|----|------|------|---------|
| MAGIC-001 | 看见坚持 | P2 | 七连胜后系统解释如何改变提醒/挑战/语气，允许用户说"我很累" |
| MAGIC-002 | 承认误判 | P2 | 系统判断错误后承认→解释→改判→改变任务，写入 timeline |
| MAGIC-003 | 知道不用资料 | P2 | 本轮未用课件时说明为什么，并提供"按课件重讲" |
| MAGIC-004 | 记得时间 | P1 | 用户离开后回来，系统识别时间流逝，提供恢复卡 |
| MAGIC-005 | 阻止低收益 | P1 | 高压 deadline 做低收益事时温和阻止，保留 override |
| MAGIC-006 | 社群转策略 | P2 | 匿名共性错因影响任务模板，用户可见"同目标用户也常错" |

---

# 18. P4 愿景项（不阻塞首版上线，记录进度）

以下为完全体愿景项，首版上线不要求完成，但记录当前进度：

| ID | 愿景项 | 当前状态 |
|----|--------|---------|
| P4-V-001 | Counterfactual Policy Evaluation | 候选代码存在 |
| P4-V-002 | User / Goal Simulator | simulation 模块存在 |
| P4-V-003 | Research-grade Experiment Platform | safe_experiments 存在 |
| P4-V-004 | Skill / DomainPack Marketplace | marketplace API 存在 |
| P4-V-005 | Privacy-preserving Community Intelligence | community_aggregates 存在 |
| P4-V-006 | Autonomous Product Quality Guard | 部分 metrics 存在 |
| P4-V-007 | GoalWorldGraph (非学习节点) | 架构预留 |
| P4-V-008 | DomainPack 系统 | 架构预留 |
| P4-V-009 | MultiGoal Arbitration | 架构预留 |
| P4-V-010 | Growth Chronicle 用户确认流 | 部分实现 |

---

# 19. 已知问题与技术债

| ID | 问题 | 严重度 | 影响 | 备注 |
|----|------|--------|------|------|
| KNOWN-001 | IsarCore download failure (Flutter) | P2 | 集成测试 3 个 Flutter 测试失败 | Pre-existing，非 P2 引入 |
| KNOWN-002 | _FakeRedis.set() missing nx | P2 | 单元测试 mock 差异 | Pre-existing |
| KNOWN-003 | Accessibility schema drift | P2 | 部分无障碍测试可能失败 | Pre-existing |
| KNOWN-004 | Error Book Flutter UI | P2 | 后端完整，Flutter 前端未找到 | 需确认 |
| KNOWN-005 | HNSW index missing | P1 | Galaxy 语义搜索性能 | 需创建索引 |
| KNOWN-006 | Apache AGE 未实际使用 | P2 | 图查询仍用 SQLAlchemy | 预留但不阻塞 |
| KNOWN-007 | TRACKED(TD-003) 通知 API 未实现 | P2 | 通知 snooze/dismiss | Post-launch |
| KNOWN-008 | 单实例 WS 连接追踪 | P2 | 多实例部署需 Redis-backed 计数器 | 文档记录 |

---

# 20. 验收签字表

| 角色 | 签字 | 日期 | 备注 |
|------|------|------|------|
| Chief Architect (BRSAMA) | | | |
| 后端负责人 | | | |
| 移动端负责人 | | | |
| 安全审计 | | | |
| QA | | | |

---

# 21. 最终判断

**上线标准**：本清单所有 P0 项 PASS，P1 项 ≥95% PASS（0 FAIL），P2 项 ≥85% PASS（0 FAIL），P3 项 ≥90% PASS。

**上线前必须完成的动作**：
1. 全量规则守卫通过：`bash scripts/run_all_rule_guards.sh`
2. 本地签收通过：`make local-final-signoff`
3. 21 验收脚本通过：`backend/scripts/*_acceptance.py`
4. Flutter 全量测试通过：`flutter test`
5. Go 全量测试通过：`go test ./...`
6. 安全扫描通过：Trivy + Gitleaks
7. SGW 通过（或 CONDITIONAL）

**如果本清单全部通过**：

> Sparkle 不是一个功能堆叠的学习 App，而是一个 AI-native 的目标实现操作系统。
> 每一次 AI 介入都可解释、可纠正、可回流。
> 每一条链路都有观测、降级和回滚。
> 用户把目标交给 Sparkle 后，Sparkle 能持续编译出更好的下一步。
