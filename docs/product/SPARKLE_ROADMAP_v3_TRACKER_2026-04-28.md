# Sparkle Roadmap v3 — 工作跟踪文档

> **创建日期**: 2026-04-28
> **最后更新**: 2026-04-29
> **对应 Roadmap**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **用途**: 记录所有已完成、进行中、待做的工作, 支持并行推进与阶段审查

---

## 当前状态: Phase 0 完成, Phase 1 完成, Phase 2 推进中
> **审查报告 R1**: [`SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md`](SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md) — 3 P0 + 4 P1 + 3 P2
> **审查报告 R2**: [`SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md`](SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md) — P0 复查: C-02 ✅ 已修, C-01/C-03 ❌ 仍待修
> **审查报告 R3**: [`SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md`](SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md) — 2 P1 + 3 P2 (数据利用+离线缺口)

---

## Phase 0: 生产基础设施硬化

### 0.1 TLS/HTTPS 终止
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.1.1 nginx.conf 添加 443 + SSL | ✅ 完成 | main | HTTP→HTTPS 重定向, TLSv1.2/1.3, HSTS |
| T0.1.2 docker-compose.prod.yml 挂载证书 | ✅ 完成 | main | SSL_CERT_DIR volume mount, 443 端口 |
| T0.1.3 SSL 证书生成脚本 | ✅ 完成 | main | scripts/ssl/generate_dev_certs.sh |
| T0.1.4 settings.py CORS HTTPS | ✅ 完成 | main | production 强制 PRODUCTION_URL=https, CORS 默认回填生产域名且仅允许 HTTPS |
| T0.1.5 Flutter 生产 API URL | ✅ 完成 | main | 已支持 String.fromEnvironment('API_BASE_URL'), release mode 警告 http |

### 0.2 崩溃报告 (Sentry)
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.2.1 backend/app/core/sentry.py | ✅ 完成 | main | FastAPI+Redis+Celery 集成 |
| T0.2.2 main.py startup init | ✅ 完成 | main | lifespan 中早期初始化 |
| T0.2.3 gRPC server sentry init | ✅ 完成 | main | grpc_server.py serve() |
| T0.2.4 .env.example Sentry DSN | ✅ 完成 | main | |
| T0.2.5 settings.py Sentry 字段 | ✅ 完成 | main | |
| T0.2.6 Flutter Sentry init | ✅ 完成 | main | main.dart 读取 SENTRY_DSN/SENTRY_ENVIRONMENT/SENTRY_RELEASE dart-define |

### 0.3 秘钥启动校验
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.3.1 settings.py production secret 校验 | ✅ 完成 | main | SECRET_KEY+POSTGRES+REDIS+MINIO+INTERNAL_API+LLM |
| T0.3.2 MinIO 默认值改为空 | ✅ 完成 | main | "minioadmin" → "" |
| T0.3.3 .env.example placeholder 注释 | ✅ 完成 | main | 头部警告 + REQUIRED 注释 |
| T0.3.4 check_production_secrets.py 脚本 | ✅ 完成 | main | 含引号去除, 开发跳过 |

### 0.4 基础设施安全加固
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.4.1 Grafana 密码必填 | ✅ 完成 | main | :? 语法, 未设则 docker compose 报错 |
| T0.4.2 JPush placeholder 移除 | ✅ 完成 | main | '' 默认 + jpushEffectiveEnabled guard |
| T0.4.3 MinIO credentials 从 env | ✅ 完成 | main | docker compose/gateway/init_minio_buckets 均要求显式 env, 不回退 minioadmin |
| T0.4.4 PRODUCTION_URL setting | ✅ 完成 | main | settings.py + .env.example |
| T0.4.5 Grafana 8 dashboard 预配置 | ✅ 完成 | main | provisioning 目录现有 8 个 dashboard JSON |

### 0.5 邮件服务配置
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.5.1 email 发送逻辑确认 | ✅ 完成 | main | 单测覆盖 disabled、缺 SMTP、STARTTLS 发送路径 |
| T0.5.2 SMTP 配置说明 | ✅ 完成 | main | docs/ops/smtp_configuration.md |
| T0.5.3 EMAIL_ENABLED 生产默认 | ✅ 完成 | main | 未显式设置时 dev=false, production=true |

---

## Phase 1: 核心闭环关闭

### 1.1 Breakpoint #5: Behavior-driven Push
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.1.1 notification_service 增强 | ✅ 完成 | main | Spine NotificationDirective 集成 |
| T1.1.2 session_end RecallOpportunity | ✅ 完成 | main | StreamChat 结束后触发召回检测 |
| T1.1.3 push_scheduler.py 新建 | ✅ 完成 | main | PushScheduler + recall queue + scheduler 集成 |
| T1.1.4 JPush 内容增强 | ✅ 完成 | main | JPushPayload 支持 goal_context + suggested_action extras, 2 tests passed |
| T1.1.5 Flutter 推送跳转 | ✅ 完成 | main | PushNavigationService 解析 deep_link、goal_context、suggested_action、recall_type 并跳转 task/plan/chat/notification-center |
| T1.1.6 test_behavior_driven_push.py | ✅ 完成 | main | 13 tests passed, 含 invalid recall queue key 防崩溃覆盖 |

### 1.2 Breakpoint #6: Structured CognitiveAdjustments
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.2.1 CognitiveAdjustment dataclass | ✅ 完成 | main | dimension/value/reason/evidence/scope/ttl/user_visible |
| T1.2.2 router 生成 structured_adjustments | ✅ 完成 | main | prompt_instruction 渲染 + routing_engine 透传 |
| T1.2.3 ux_envelope 从调整生成 | ✅ 完成 | main | ux_turn 含 user_visible structured_adjustments |
| T1.2.4 response_builder 结构化参数 | ✅ 完成 | main | response_metadata 含 structured_cognitive_adjustments |
| T1.2.5 Flutter WebSocket 传递 | ✅ 完成 | main | WebSocket metadata 解码 structured_cognitive_adjustments, ChatMessageModel/UX envelope 保留结构化列表 |
| T1.2.6 test_structured_cognitive_adjustments.py | ✅ 完成 | main | 7 tests passed (含 prompt_instruction + overlay 测试) |

### 1.3 Breakpoint #7: Verification Loop
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.3.1 outcome_tracker.py | ✅ 完成 | main | register_expected + record_actual + verify_pending |
| T1.3.2 register_expected_outcome | ✅ 完成 | main | 含 Redis 索引 + TTL 窗口 |
| T1.3.3 record_actual_outcome | ✅ 完成 | main | 触发 OutcomeRecorder 归因 |
| T1.3.4 attribution.py | ✅ 完成 | main | 已有 OutcomeRecorder._attribute (4 规则) |
| T1.3.5 learning_guard.py | ✅ 完成 | main | should_learn/retract/verdict 三层守卫 |
| T1.3.6 test_verification_loop.py | ✅ 完成 | main | 21 tests passed, 含 pending verification、policy effect、learning guard 缺口覆盖 |

### 1.4 Outcome 回流闭环
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.4.1 9 类 directive outcome | ✅ 完成 | main | OutcomeRecorder 已支持 4 类归因规则 |
| T1.4.2 统一 outcome 写入 CausalTrace | ✅ 完成 | main | OutcomeTracker 链接 pending→trace→outcome |
| T1.4.3 Outcome Grafana dashboard | ✅ 完成 | main | monitoring/grafana-dashboards/sparkle-spine-outcome.json, provisioning 已挂载 |

### 1.5 Card Protocol 迁移
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T1.5.1 card_service.py 完善 | ✅ 完成 | main | CardService 补齐软删除/恢复、CardEdge 关系门面、CardSnapshot 创建与版本查询; 14 Card Protocol tests passed, ruff passed |
| T1.5.2 planning_workflow Card 写入 | ✅ 完成 | main | planning_workflow 经 PlanService/TaskService 双写 Card; 新增服务路径验收测试, phase1 5 tests passed |
| T1.5.3 TaskOccurrence 从 Card 生成 | ✅ 完成 | main | PhaseService/TemporalEngine 已从 Task Card 生成 Occurrence; phaseb 8 tests passed |
| T1.5.4 InterventionRecord 记录 | ✅ 完成 | main | InterventionService 自适应干预双写 InterventionRecord 并回填旧 request; 9 tests passed, ruff passed |
| T1.5.5 Flutter Card 模型适配 | ✅ 完成 | main | EntityCardPayload 支持 Card Protocol card_id/card_type/metadata, PlanCard/TaskModel 可消费; 6 tests passed, analyze clean |
| T1.5.6 双写一致性校验 | ✅ 完成 | main | scripts/check_card_protocol_dual_write_consistency.py + validator; 15 tests passed, ruff passed |

---

## Phase 1.6: 审查发现的接线缺口 (🔴 审查新增 — 2026-04-29)

> **来源**: [`SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md`](SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md)
> **性质**: 模块已实现但生产代码路径未接线，非代码质量问题

### P0 Critical — 必须立即修复

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| C-01-FIX: OutcomeTracker 接线到生产代码 | ✅ 完成 | Codex | SpineOrchestrator 注册预期, TaskEventConsumer 回填实际行为, SchedulerService 6h 过窗验证; 26 tests passed |
| C-02-FIX: structured_adjustments 注入 prompts.py | ✅ R2 验证通过 | — | prompt_instruction property 自动转为文本经 dual_core_instruction 参数注入, 机制正确 |
| C-03-FIX: multi_agent_adapter 传入 Spine context | ✅ 完成 | Codex | ExecutionEngine→multi_agent_adapter→prompt 两段链路均传入 spine_response_directive、chronicle、fatigue context; 4 tests passed |

### P1 High — 重要信号缺失

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| H-01-FIX: 6 个 EventBus 事件接入 Spine | 🟡 审查新增 | — | task.abandoned, task.stuck, focus.session.completed, plan.created, srl.phase.transition, calendar.event.* |
| H-02-FIX: Aurora→Spine 反馈接入 PolicyEngine | 🟡 审查新增 | — | feed_aurora_decision 写入 Redis 但无 Spine 策略评估读取 |
| H-03-FIX: Spine 降级 Prometheus counter + 告警 | ✅ 完成 | Codex | sparkle_spine_degradation_total + SparkleSpineDegradation 告警 + runbook; 1 test passed |
| H-04-FIX: Context Receipt Bar 用户行动按钮 | 🟡 审查新增 | — | receipt 显示正确但缺少"按课件重讲/排除资料"等行动 |

### P2 Medium

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| M-01-FIX: structured_cognitive_adjustments Flutter 解析 | ✅ R2 验证通过 | — | T1.2.5 已完成 WS→Provider→State 数据管道, UI 渲染留 Phase 4 |
| M-02-FIX: dual_core_router 消费 Spine StateRegister | 🔵 审查新增 | — | Phase 3 核心任务的前置准备 |

---

## Phase 2-7: 简要索引 (详细任务在对应阶段展开时填写)

| Phase | 状态 | 开始日期 | 完成日期 |
|-------|------|----------|----------|
| Phase 2: Spine 深化 | 🟡 进行中 | 2026-04-29 | — |
| Phase 3: Aurora↔Spine | ⬜ 未开始 | — | — |
| Phase 4: 活体验打磨 | ⬜ 未开始 | — | — |
| Phase 5: P4 平台 | ⬜ 未开始 | — | — |
| Phase 6: 稳定性与规模化 | ⬜ 未开始 | — | — |
| Phase 7: 验收上线 | ⬜ 未开始 | — | — |

### Phase 2 审查更新 (🔴 2026-04-29)

| Task | 原状态 | 更新 | 原因 |
|------|--------|------|------|
| T2.3.4 Spine Timeline API | ⬜ 未开始 | ✅ 已存在 | endpoint 已在 `aurora.py` line 447+, path: `/api/v1/aurora/spine/timeline` |
| T2.3.5 causal_timeline_panel.dart | ⬜ 未开始 | ✅ 已存在 | widget 已实现, 调用 API, 支持 corrections |
| T2.1.6 / H-03 Spine 降级监控 | ⬜ 未开始 | ✅ 完成 | chat_turn Spine 异常写入 Prometheus counter, 5m 告警接入 Alertmanager |

---

## 审查日志

| 日期 | Phase | 审查类型 | 发现问题 | 修复状态 |
|------|-------|----------|----------|----------|
| 2026-04-29 | Phase 1 | Opus Audit | outcome_recorder.py 重复方法定义, push_scheduler await sync method | ✅ 全部修复 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_recorder._attribute() 死代码残留 (lines 229-246 重复 harmful/needs_confirmation 检查) | ✅ 已修: 死代码已删除, REVIEW 残留已移除 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_tracker 非原子 Redis 操作 (lpush+ltrim+expire 未用 pipeline) | ✅ 已修: register_expected 用户索引改为 pipeline |
| 2026-04-29 | Phase 1 | Claude Review | push_scheduler UUID(user_id) 缺少 try-except, 格式异常会中断 queue 处理 | ✅ 已修: ValueError skip+delete bad key, 单测覆盖 |
| 2026-04-29 | Phase 1 | Claude Review | learning_guard.should_learn() lines 56-57 冗余分支 | ✅ 已修: 冗余分支已删除, REVIEW 残留已移除 |
| 2026-04-29 | Phase 1 | Claude Review | 5 个方法缺单元测试 (build_self_correction_receipt, verify_pending, get_guard_verdict 等) | ✅ 已补: verification_loop 21 tests, behavior_push 13 tests |
| 2026-04-29 | Phase 1-2 | Claude Deep Audit | **3 P0 Critical**: OutcomeTracker 死代码, CognitiveAdjustment 未到 LLM prompt, multi_agent 跳过 Spine | ⬜ 待修 — 见审查报告 |
| 2026-04-29 | Phase 1-2 | Claude Deep Audit | **4 P1 High**: 6 EventBus 事件绕过 Spine, Aurora→Spine 只写日志, Spine 降级无监控, Receipt 缺行动按钮 | ⬜ 待修 — 见审查报告 |
| 2026-04-29 | Phase 2 | Claude Deep Audit | **T2.3.4/T2.3.5 已完成**: Spine Timeline API + Flutter Panel 均已存在, 无需新建 | ✅ 确认 |
| 2026-04-29 | Phase 1 | Claude R2 验收 | C-02 ✅ 已修 (prompt_instruction property 机制), M-01 ✅ (T1.2.5 Flutter 管道) | ✅ 验收通过 |
| 2026-04-29 | Phase 1 | Claude R2 验收 | C-01 ❌ OutcomeTracker 仍未接线, C-03 ❌ multi_agent_adapter 仍未传 Spine | ✅ 已修: C-01/C-03 均完成 |
| 2026-04-29 | Phase 1.5 | Codex Self Review | T1.5.1 CardService 需成为 Card CRUD/Edge/Snapshot 稳定入口, 避免上层直接拼多服务 | ✅ 已修: 增加薄门面与版本查询, 14 Card Protocol tests + ruff 通过 |
| 2026-04-29 | Phase 1.5 | Codex Self Review | T1.5.2/T1.5.3 不应重复写 Card 逻辑, 应验收 planning_workflow 使用的 PlanService/TaskService 双写路径 | ✅ 已证实: 新增服务路径测试 + phaseb TaskOccurrence 测试通过 |
| 2026-04-29 | Phase 1.5 | Codex Self Review | T1.5.4 旧 InterventionService 自适应干预未直接写 Card Protocol InterventionRecord | ✅ 已修: 双写记录、旧 request 回填 record_id、投递成功后标记 DELIVERED |
| 2026-04-29 | Phase 1.5 | Codex Self Review | T1.5.5 Flutter 统一实体卡只识别 legacy/entity_card, 不识别 /cards/search 的 Card Protocol payload | ✅ 已修: CardProtocolRef + PLAN/TASK metadata 兼容解析 |
| 2026-04-29 | Phase 1.6 | Codex Self Review | C-01 初版会在同一个 task.completed 事件里先注册再立刻解析当前 pending, 且 verify_pending 未等待验证窗口 | ✅ 已修: 行为回填改为解析旧 pending, pending 过窗才 timeout, 统一 OutcomeTracker API |
| 2026-04-29 | Phase 1.6 | Codex Self Review | C-03 需要覆盖 multi-agent synthesis 与 fallback 两条 prompt 构造路径, 不能只改一处 | ✅ 已修: 两处 build_system_prompt 均透传 Spine context, 新增 2 条回归测试 |
| 2026-04-29 | Phase 1.6 | Codex Self Review | C-03 adapter 已消费 Spine context, 但 ExecutionEngine 入口若不传字段仍会断链 | ✅ 已修: multi_agent_context 从 state.context_data 透传 Spine + dual-core prompt instruction |
| 2026-04-29 | Phase 1.5 | Codex Self Review | T1.5.6 双写迁移缺少可重复运行的一致性检查入口 | ✅ 已修: 后端 validator + CLI, 覆盖缺失投影/重复/孤儿/缺 Edge |
| 2026-04-29 | Phase 2 | Codex Self Review | Spine 降级只写 `spine_degraded` metadata, 没有生产监控与告警 | ✅ 已修: Prometheus counter + SLO alert + runbook |
| 2026-04-29 | 全系统 | Claude R3 数据审计 | **D-01 P1**: Notification 交互历史未接入 AI, **D-02 P1**: Photon 消费模式未接入 AI | ⬜ 待修 — 见 R3 报告 |
| 2026-04-29 | 全系统 | Claude R3 离线审计 | **O-01 P1**: OfflineChatMessage 模型存在但未使用, **O-02/03/04 P2**: CRDT/任务/Focus 离线缺失 | ⬜ 待修 — 见 R3 报告 |

---

## 提交日志

| 日期 | Commit | Phase | 范围 |
|------|--------|-------|------|
| 2026-04-29 | 276bce8b | Phase 0 | Complete production hardening — CORS HTTPS, Flutter Sentry, MinIO env, Grafana dashboards, SMTP |
| 2026-04-29 | a9ec2ac3 | Phase 1 | Breakpoints #5/#6/#7 — structured adjustments, behavior-driven push, verification loop |
| 2026-04-29 | e1812b92 | Phase 1 | Prometheus outcome metrics + Grafana outcome dashboard |
| 2026-04-29 | 93b72fd4 | Phase 1 | Audit fixes — dedup outcome_recorder, async record_sent |
| 2026-04-29 | cec517ac | Phase 1 | Claude Review handoff + code quality annotations |
| 2026-04-29 | 2428d022 | Phase 1 | Review follow-ups — Redis pipeline, REVIEW cleanup, missing tests |
| 2026-04-29 | 8817a4b9 | Phase 1 | T1.1.4 JPush behavior context payload — goal_context + suggested_action |
| 2026-04-29 | b0a0cb95 | Phase 1 | T1.1.5 Flutter push open routing — task/goal/recall contexts |
| 2026-04-29 | 6a8f8f3d | Phase 1 | T1.2.5 Flutter WebSocket structured cognitive adjustments |
| 2026-04-29 | d329c3b2 | Phase 1.5 | T1.5.1 CardService facade — CRUD delete/restore, edge facade, snapshot versions |
| 2026-04-29 | cba418cd | Phase 1.5 | T1.5.2-T1.5.3 planning/task card projection verification |
| 2026-04-29 | 02dd8b13 | Phase 1.5 | T1.5.4 InterventionService dual-writes Card Protocol InterventionRecord |
| 2026-04-29 | 3f126de5 | Phase 1.5 | T1.5.5 Flutter Card Protocol payload adaptation + R3 audit report |
| 2026-04-29 | 93e1420f | Phase 1.5 | T1.5.6 Card Protocol dual-write consistency validator |
| 2026-04-29 | b60299d4 | Phase 1.6 | C-01 OutcomeTracker production wiring |
| 2026-04-29 | 65750e69 | Phase 1.6 | C-03 Multi-agent Spine context prompt wiring |
| 2026-04-29 | 2b69f4c7 | Phase 1.6 | C-03 ExecutionEngine carries Spine context into multi-agent adapter |
| 2026-04-29 | d6afea15 | Phase 2 | H-03/T2.1.6 Spine degradation Prometheus counter + alert |
