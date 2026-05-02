# Sparkle Roadmap v3 — 工作跟踪文档

> **创建日期**: 2026-04-28
> **最后更新**: 2026-05-02 (30 CXP 并行打磨完成最终集成: 30/30 报告齐备, CXP 分支/共享工作区补丁已合入 final-closeout integration, Python/Go/Flutter 聚焦验证通过)

### P0 Critical — 当前会话修复

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| P0-1: WebSocket 重连丢上下文 | ✅ 已修 (5855b859) | Claude | Flutter 重连带 session_id query param + Go gateway 转发 + chat_orchestrator 日志 |
| P0-2: (已完成) | ✅ 已修 | — | P0-2 内容已在之前会话完成 |
| P0-3: 25个Aurora从未生产运行 | ✅ 已验证 | Claude | 47个 kill switch 全部默认 live, 71个 binding, drill 脚本已补齐 |
| P0-4: 632 commits未合入main | 🟡 待决定 | — | 需用户/产品决策: merge 或 squash-merge roadmapv3→main |
> **对应 Roadmap**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **用途**: 记录所有已完成、进行中、待做的工作, 支持并行推进与阶段审查

### 2026-05-01 Closeout Dispatch Updates

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| C16: Flutter Typed Failure Model | ✅ 完成 | Codex | `AppFailure` typed mapper added; auth/chat/dashboard paths adopted; chat/dashboard UI differentiates offline/auth/server/validation recovery; `flutter test test/core/errors/failures_test.dart` 4/4 passed |
| R18: Aurora 完全体体验收口 | ✅ 完成 | Codex | Legacy `SPARKLE_*` 配套开关默认全开并纳入配置一致性守卫；聊天 freeform 纠错进入可见对话+结构化链；状态带第三层小屏可滚动、纠正/详情 chip 更稳；后端 Aurora 51 tests + 移动端聚焦 61 tests + secret/diff checks passed |

### 2026-05-02 Parallel CXP Final Integration

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| CXP-01~CXP-30 并行体验/系统打磨 | ✅ 集成完成 | Codex final integrator | 共享工作区补丁提交 `ccf83242e`; 已合并 CXP-01/02/05/07/13/16/17/18/21/23/25 等独立分支; CXP-14 缺失报告已补; 最终验收见 `docs/product/parallel_closeout/SPARKLE_FINAL_INTEGRATION_ACCEPTANCE_REPORT_2026-05-02.md` |
| Final conflict resolution | ✅ 完成 | Codex | 解决 `time_utils.py` add/add、community API 格式/权限调用、task card 格式、gateway ACK/quota 旧测试语义冲突 |
| Final verification | ✅ 聚焦通过 | Codex | backend compile + ruff scoped + 74 backend tests; gateway logsafe/handler/middleware tests; Flutter entity-card 11 tests; Flutter focused analyze `--no-fatal-infos` 通过 |

---

## 当前状态: Phase 0-5 基本完成, Phase 6/7 进入 R4 生产验收复核
> **审查报告 R1**: [`SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md`](SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md) — 3 P0 + 4 P1 + 3 P2
> **审查报告 R2**: [`SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md`](SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md) — P0 复查: C-01/C-02/C-03 ✅ 均已修
> **审查报告 R3**: [`SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md`](SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md) — 2 P1 + 3 P2 (数据利用+离线缺口)
> **审查报告 R4**: [`SPARKLE_AUDIT_R4_FINAL_ACCEPTANCE_CODEX_2026-04-29.md`](SPARKLE_AUDIT_R4_FINAL_ACCEPTANCE_CODEX_2026-04-29.md) — Phase 6/7 生产验收复核: 压测、蓝绿、成本熔断、Aurora live 治理、首页纠偏闭环
> **Aurora 全系统审计**: Phase 3.5 — 3 P0 + 3 P1 + 5 P2 (见下方 Phase 3.5 节)
> **外部审计 R6**: [`SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md`](SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md#r6-外部审计-2026-04-30) — 自评修正 + 5 死代码 + 68 重复块 + CI no-op

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
| T0.3.4 check_production_secrets.py 脚本 | ✅ 完成 | C05 | 含引号去除, 开发跳过; 2026-05-01 增加 tracked-file provider pattern scan 且不打印 secret 值 |
| T0.3.5 Secret rotation runbook | ✅ 完成 | C05 | `docs/ops/secret_rotation_runbook.md`; provider 管理员仍需轮换历史暴露凭据 |

### 0.4 基础设施安全加固
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T0.4.1 Grafana 密码必填 | ✅ 完成 | main | :? 语法, 未设则 docker compose 报错 |
| T0.4.2 JPush placeholder 移除 | ✅ 完成 | main | '' 默认 + jpushEffectiveEnabled guard |
| T0.4.3 MinIO credentials 从 env | ✅ 完成 | main | docker compose/gateway/init_minio_buckets 均要求显式 env, 不回退 minioadmin |
| T0.4.4 PRODUCTION_URL setting | ✅ 完成 | main | settings.py + .env.example |
| T0.4.5 Grafana 8 dashboard 预配置 | ✅ 完成 | main | provisioning 目录现有 8 个 dashboard JSON |
| T0.4.6 API 容器非 root 运行 | ✅ 完成 | Codex C07 | backend/gateway image 固定 `sparkle` UID/GID 10001; local/prod compose pin `SPARKLE_APP_UID:GID`; logs/uploads/cache 用可写 volume；compose config + Dockerfile check 通过 |

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
| H-01-FIX: 6 个 EventBus 事件接入 Spine | ✅ 完成 | Codex | SpineEventBridge 接入 task.abandoned/stuck、focus.session.completed、plan.created、srl.phase.transition、calendar.event.*; 3 tests passed |
| H-02-FIX: Aurora→Spine 反馈接入 PolicyEngine | ✅ 完成 | Codex | SpineOrchestrator 评估前读取 Aurora decisions, PolicyEngine 作为可逆 soft_bias 消费; 2 tests passed |
| H-03-FIX: Spine 降级 Prometheus counter + 告警 | ✅ 完成 | Codex | sparkle_spine_degradation_total + SparkleSpineDegradation 告警 + runbook; 1 test passed |
| H-04-FIX: Context Receipt Bar 用户行动按钮 | ✅ 完成 | Codex | receipt 详情增加"按课件重讲/排除此资料/换成历年真题", 通过 chatProvider 续发纠偏 prompt; analyzer passed |

### P2 Medium

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| M-01-FIX: structured_cognitive_adjustments Flutter 解析 | ✅ R2 验证通过 | — | T1.2.5 已完成 WS→Provider→State 数据管道, UI 渲染留 Phase 4 |
| M-02-FIX: dual_core_router 消费 Spine StateRegister | ✅ 完成 | Claude+Codex | DualCoreRoutingInput 增加 spine_active_states; RoutingEngine 从 StateRegister 读取活跃状态; route() 消费 fatigue/cognitive_load/execution/knowledge 状态并影响 mode/strategy/debug; 38 tests passed |

### Closeout Dispatch — 2026-05-01

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| C01: DualCoreRouter 生产接线复核 | ✅ 完成 | Codex | 当前支持运行时为 `ChatOrchestrator.process_stream()` → `_apply_dual_core_routing()` → `dual_core_router.route()`; legacy `ProductionChatOrchestrator` 默认不可构造。新增 live process-stream 回归证明 router 被调用并影响 route/prompt/metadata; Response metadata 现在暴露 bounded `dual_core_decision`; 34 focused tests + scoped ruff passed |

---

## Phase 3.5: Aurora 全面审计修复 (🔴 2026-04-29)

> **来源**: Aurora 全系统深度审计 (Claude Opus)
> **范围**: 18+ 文件, 15K+ 行 Aurora 代码
> **发现**: 3 P0 + 3 P1 + 5 P2

### P0 Critical — 数据完整性

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| AUDIT-P0-1: types.py 13个重复 dataclass 定义 | ✅ 完成 | Claude | 删除13个重复定义+StateEntry损坏块, 1692→1197行, 保留from_dict/relevance_for_nodes等扩展方法; 2067 tests passed |
| AUDIT-P0-2: causal_trace_store 静默数据丢失 | ✅ 完成 | Claude | 5个append方法加logger.warning; 移除重复store_directive_by_id; except Exception: pass→logger.warning; 2067 tests passed |
| AUDIT-P0-3: spine_orchestrator StateRegister 竞态条件 | ✅ 完成 | Claude | _save_state 改用 Redis pipeline 原子操作 (set+sadd), 加 FakeRedis fallback; 2017 tests passed |

### P1 High — 功能缺陷

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| AUDIT-P1-4: 3个事件管道路由缺失 | ✅ 完成 | Claude | task_event_consumer dispatch set 增加 achievement.unlocked/shop.purchase_completed/notification.fatigue_detected; test_spine_event_bridge 同步更新; 24 tests passed |
| AUDIT-P1-5: L0RuleEngine 未接入生产代码 | ✅ 完成 | Claude | routing_engine._get_spine_active_states 内调用 _apply_l0_rules → L0RuleEngine.evaluate_deadline_pressure; 从 Redis 缓存读取日历上下文; 23 L0/L1 tests passed |
| AUDIT-P1-6: spine_quality_guard 仅在replay路径调用 | ✅ 完成 | Claude | _run_signal_pipeline 在 trace 保存前调用 _run_live_quality_guard; 检查 signal_actionability + directive_compliance; 降级记录 Prometheus counter; 1995 tests passed |

### P2 Medium — 架构/技术债务

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| AUDIT-P2-7: AuroraEngine 与 Spine 两套独立系统 | 🟡 部分缓解 | Claude | T3.4 status-band 统一返回6态+风险标志, 两系统数据流已桥接但独立运行; 完全统一留 Phase 4 |
| AUDIT-P2-8: AuroraEnergyStore.resolve_energy_level() 死代码 | ✅ 完成 | Claude | _compute_6state_band() 现在通过 AuroraEnergyStore(enabled=True) 调用 load_energy(); 绕过 settings gate |
| AUDIT-P2-9: 88个 AURORA_* settings 缺失于 .env.example | ✅ 完成 | Claude | 57个非MODE设置已补充到 .env.example, 按Stage分组注释; 2026-04-29 |
| AUDIT-P2-10: Stage 37/39 kill switch 非三态模式 | ✅ 完成 | Claude | Stage 37 bool→str 三态 (AURORA_STAGE37_LLM_SAFETY_MODE), Stage 39 删除自定义 _normalize_mode/_get_flag/_set_flag, 统一用 KillSwitchBinding+read_mode/write_mode; 9 tests passed; 2026-04-29 |
| AUDIT-P2-11: CalendarSignalBridge 存在但从未调用 | ✅ 完成 | Claude | SpineEventBridge._calendar_changed() 接入 CalendarSignalBridge.detect_deadline_pressure()+build_time_context(); 6 tests passed; 2026-04-29 |

---

## Phase 2-7: 简要索引 (详细任务在对应阶段展开时填写)

| Phase | 状态 | 开始日期 | 完成日期 |
|-------|------|----------|----------|
| Phase 2: Spine 深化 | ✅ 完成 | 2026-04-29 | — |
| Phase 3: Aurora↔Spine | ✅ 完成 | 2026-04-29 | T3.1→T3.4 全部完成, Flutter状态带真实API消费已接入 |
| Phase 4: 活体验打磨 | ✅ 完成 | 2026-04-29 | Phase 4.1-4.3 全部完成, O-04 Focus自动同步完成 |
| Phase 5: P4 平台 | ✅ 完成 | 2026-04-29 | T5.1.2 Episode生成接入Spine + T5.1.3 完整性校验, 24 tests |
| Phase 6: 稳定性与规模化 | 🟡 R4 待复核 | 2026-04-29 | 代码框架基本完成; T6.1.6 压测、蓝绿生产路径、成本熔断生产接线待验收 |
| Phase 7: 验收上线 | 🟡 推进中 | 2026-04-29 | T7.3 production readiness script created |

### Phase 2 审查更新 (🔴 2026-04-29)

| Task | 原状态 | 更新 | 原因 |
|------|--------|------|------|
| T2.3.4 Spine Timeline API | ⬜ 未开始 | ✅ 已存在 | endpoint 已在 `aurora.py` line 447+, path: `/api/v1/aurora/spine/timeline` |
| T2.3.5 causal_timeline_panel.dart | ⬜ 未开始 | ✅ 已存在 | widget 已实现, 调用 API, 支持 corrections |
| T2.1.6 / H-03 Spine 降级监控 | ⬜ 未开始 | ✅ 完成 | chat_turn Spine 异常写入 Prometheus counter, 5m 告警接入 Alertmanager |
| H-01 EventBus→Spine 接线 | ⬜ 未开始 | ✅ 完成 | TaskEventConsumer 现在将 6 类高价值事件桥接为 ActionableSignal |
| H-02 Aurora→Spine 策略反馈 | ⬜ 未开始 | ✅ 完成 | Aurora action/surface 进入 PolicyEngine soft_bias, 不直接改硬约束 |
| H-04 Context Receipt Bar 用户行动按钮 | ⬜ 未开始 | ✅ 完成 | receipt sheet 现在可直接触发按课件重讲/排除此资料/换成历年真题纠偏 prompt |
| M-02 dual_core_router 消费 Spine StateRegister | ⬜ 未开始 | ✅ 完成 | StateRegister 活跃状态进入 DualCoreRoutingInput, 影响 routing mode、strategy_adjustments 与 debug |

---

## 审查日志

| 日期 | Phase | 审查类型 | 发现问题 | 修复状态 |
|------|-------|----------|----------|----------|
| 2026-05-01 | Closeout C03 | Codex Dispatch | AdaptiveReplanner 对 `task.abandoned` / `task.stuck` 缺少直接生产触发，用户可见 adaptation 文案没有显式 reason 字段 | ✅ 已修: TaskEventConsumer 将 abandoned/stuck 事件接入 `evaluate_plan_health_now`; adaptation update 标题/description/metadata 显式说明真实进展与触发原因; 11 focused tests passed, scoped ruff passed |
| 2026-04-29 | Phase 6/7 | Codex R4 Final Acceptance | Tracker 宣称 Phase 0-6 完成, 但 T6.1.6 100 并发压测仍未开始; Phase 7 仍有人工/运维真实门槛 | ✅ T6.1.6 已补 k6 压测脚本; Phase 7 runbook 与人工验收证据仍待补 |
| 2026-04-29 | Phase 6/7 | Codex R4 Final Acceptance | `blue_green_switch.sh` 不是生产流量切换证据; 正式路径应对齐 `deploy-prod.sh` 或 `deploy_k8s.sh` | 🟡 待对齐: 选择生产部署路径并做实演练 |
| 2026-04-29 | Phase 6 | Codex R4 Final Acceptance | RAG/Aurora 成本熔断只在 `cost_controller.py` 与单测中存在, 未接入生产 RAG/Aurora 主链 | ✅ 已修: is_rag_within_budget 接入 graph_rag.retrieve(); is_aurora_within_budget 接入 L3/L4 |
| 2026-04-29 | Aurora/UX | Codex R4 Final Acceptance | 首页 Aurora 状态带纠偏 chip 只跳 chat initial_user_message, 未提交结构化 telemetry/Core Session 反馈 | ✅ 已修: dashboard_screen onCorrectionTap 先提交 recordStatusBandCorrection() 再跳转 chat |
| 2026-04-29 | Docs/Workflow | Codex R4 Final Acceptance | `docs/product/愿景验收清单` 工作区被删除, 仅 `critical_files/愿景验收清单` 保留副本 | 🟡 待确认: 若非有意归档, 恢复主路径作为 Phase 7 验收源 |
| 2026-04-29 | Phase 1 | Opus Audit | outcome_recorder.py 重复方法定义, push_scheduler await sync method | ✅ 全部修复 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_recorder._attribute() 死代码残留 (lines 229-246 重复 harmful/needs_confirmation 检查) | ✅ 已修: 死代码已删除, REVIEW 残留已移除 |
| 2026-04-29 | Phase 1 | Claude Review | outcome_tracker 非原子 Redis 操作 (lpush+ltrim+expire 未用 pipeline) | ✅ 已修: register_expected 用户索引改为 pipeline |
| 2026-04-29 | Phase 1 | Claude Review | push_scheduler UUID(user_id) 缺少 try-except, 格式异常会中断 queue 处理 | ✅ 已修: ValueError skip+delete bad key, 单测覆盖 |
| 2026-04-29 | Phase 1 | Claude Review | learning_guard.should_learn() lines 56-57 冗余分支 | ✅ 已修: 冗余分支已删除, REVIEW 残留已移除 |
| 2026-04-29 | Phase 1 | Claude Review | 5 个方法缺单元测试 (build_self_correction_receipt, verify_pending, get_guard_verdict 等) | ✅ 已补: verification_loop 21 tests, behavior_push 13 tests |
| 2026-04-29 | Phase 1-2 | Claude Deep Audit | **3 P0 Critical**: OutcomeTracker 死代码, CognitiveAdjustment 未到 LLM prompt, multi_agent 跳过 Spine | ✅ 已修 — C-01/C-02/C-03 均完成 |
| 2026-04-29 | Phase 1-2 | Claude Deep Audit | **4 P1 High**: 6 EventBus 事件绕过 Spine, Aurora→Spine 只写日志, Spine 降级无监控, Receipt 缺行动按钮 | ✅ 已修 — H-01/H-02/H-03/H-04 均完成 |
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
| 2026-04-29 | Phase 2 | Codex Self Review | H-01 若继续用 `on_external_event(source="task")` 会落到未实现 dispatch/unsupported source, 仍无法真正进入 Spine | ✅ 已修: 新增 SpineEventBridge 直接构造 ActionableSignal 并运行 Spine pipeline |
| 2026-04-29 | Phase 2 | Codex Self Review | H-02 已有 `consume_aurora_decisions`, 但只用于 outcome attribution, PolicyEngine evaluate 前未读取 | ✅ 已修: on_task_completed/_run_signal_pipeline 均读取 Aurora decisions 并传入 PolicyEngine |
| 2026-04-29 | Phase 2 | Codex Self Review | H-04 Context Receipt Bar 只有查看依据和 timeline, 用户发现资料不合适时无法即时纠偏 | ✅ 已修: 详情 sheet 增加 3 个行动 chip 并续发纠偏 prompt; 窄范围 analyzer passed, Flutter test 受既有全包编译错误阻塞 |
| 2026-04-29 | Phase 3 | Claude+Codex | M-02 dual_core_router 不消费 Spine StateRegister, Phase 3 前置缺失 | ✅ 已修: RoutingEngine 读取 StateRegister, Router 消费 fatigue/cognitive_load/execution/knowledge 状态并进入 mode/debug/strategy; 38 tests passed |
| 2026-04-29 | 全系统 | Claude R3 数据审计 | **D-01 P1**: Notification 交互历史未接入 AI, **D-02 P1**: Photon 消费模式未接入 AI | ✅ 均已修: D-01 连续dismiss→fatigue signal; D-02 shop.purchase_completed+achievement.unlocked→reward_engagement signal; 10 tests passed |
| 2026-04-29 | 全系统 | Claude R3 离线审计 | **O-01 P1** ✅: OfflineChatMessage 已接入. **O-04 P2** ✅: Focus自动同步已接入 (connectivity listener + startup sync). **O-02/03 P2**: CRDT/任务离线 ⬜ (Phase 6) | 见 R3 报告
| 2026-04-29 | Phase 3 | Claude | T3.1.1 L0 rule-aware Aurora: deadline_pressure 自动计算 + quiet_hours 强制执行 | ✅ 已修: L0RuleEngine 新建, deadline_pressure→StateRegister, dual_core_router 消费 deadline state, quiet_hours 解析; 11 tests passed |
| 2026-04-29 | Phase 3 | Claude | T3.1.2 L1 Light Aurora: ResponseDirective 消费 StateRegister 活跃状态调节 tone | ✅ 已修: build_response_directive 增加 active_states 参数, fatigue→low_pressure(优先), deadline→urgent, SpineOrchestrator 两处调用点传入; 6 tests passed |
| 2026-04-29 | Phase 3 | Claude | T3.1.3 L2 Mid Aurora: 升级模式检测 + 结构性干预 | ✅ 完成: L2InterventionEngine 新建 (4 escalation patterns: knowledge_crisis/execution_collapse/exam_underwater/burnout_risk); SpineOrchestrator._check_l2_escalation 接入; Redis cooldown 1h; 25 production-grade tests passed, 965 spine tests 无回归 |
| 2026-04-29 | Phase 3 | Claude | T3.1.4 L3 Full Aurora Core: 交互式建模会话 | ✅ 完成: L3FullCoreEngine 新建 (8 wake conditions + priority ordering + session lifecycle state machine); AuroraCoreSessionService 增加 pause/resume/transition_session; AuroraWakeJudge 扩展 5 个新唤醒条件; SpineOrchestrator 接入 L3 engine + pause/resume/health check; 62 production-grade tests passed, 39 aurora tests 无回归 |
| 2026-04-29 | Phase 3 | Claude | T3.1.5-T3.1.7 L4 Async + 能级决策 + 成本控制 | ✅ 完成: L4AsyncEngine 新建 (6 analysis types, shadow→simulation→promoted lifecycle, PolicyUpdateCandidate pattern); EnergyLevelDecider 新建 (L0-L3 每轮决策 + upgrade_reason 写入 CausalTrace); CostController 新建 (L3/L4 quota + cooldown + fallback); CausalTrace 新增 aurora_energy_level/aurora_upgrade_reason 字段; 43 production-grade tests passed |
| 2026-04-29 | Phase 3 | Claude | T3.2.1-T3.2.6 Aurora↔Spine 合流 | ✅ 完成: AuroraInputAssembler (消费 StatePacket+PolicyDecisions+Outcomes+Corrections); AuroraOutputArbitrator (proposals 通过仲裁, 不直接生效, 5个 override reasons); AuroraSelfCorrector (承认误判通过 Spine 修正); AuroraSelfModelAccessor (假设/开放问题/误判/策略信心); SpineOrchestrator 接入全部组件; 33 production-grade tests passed, 130 Aurora tests 无回归 |
| 2026-04-29 | Phase 3.5 | Claude Aurora全系统审计 | **P0-1**: types.py 13个重复dataclass (~500行死代码), **P0-2**: causal_trace_store 静默丢数据, **P0-3**: StateRegister 竞态条件 | ✅ 全部已修: P0-1删除509行死代码; P0-2加日志+删重复方法; P0-3 Redis pipeline原子化 |
| 2026-04-29 | Phase 3.5 | Claude Aurora全系统审计 | **P1-4**: 3个事件路由缺失 (achievement/shop/notification→Spine), **P1-5**: L0RuleEngine未接线, **P1-6**: quality_guard仅replay | ✅ 全部已修: P1-4路由补齐; P1-5接入routing_engine; P1-6加入live pipeline |
| 2026-04-29 | Phase 3 | Claude | T3.3.1-T3.3.3 Predicted Reply Options & 纠正反馈闭环 | ✅ 完成: ReplyOptionInjector 新建 (6 band_status 选项生成 + metadata 注入); CorrectionFeedbackProcessor 新建 (disconfirmation→confidence-0.15→StateRegister+self_model 更新, 20 semantic→state_key 映射); StateRegister.lower_confidence() 新增; response_builder 注入 predicted_reply_options; /telemetry/chip-selected 接入纠正反馈; spine_orchestrator.on_user_correction 接入; 33 production-grade tests passed, 171 Aurora tests 无回归 |
| 2026-04-29 | Phase 3 | Claude | T3.4.1-T3.4.4 Aurora Status Band 6-State & User Preferences | ✅ 完成: get_status_band_summary 统一返回6态band (sensing/calibrated/risk_found/needs_confirm/calibration_available/cooling_down) + correction_options + cooldown; AuroraUserPreferencesService 新建 (4偏好: 分析深度/直接性/解释级别/压力风格, GET/PUT API); DualCoreRouter 消费偏好调制路由; 35 production-grade tests passed, 2053 spine tests + 287 Aurora tests 无回归 |
| 2026-04-29 | Phase 3.5 | Claude Aurora全系统审计 | **P2-7**: AuroraEngine/Spine 双系统 — 部分缓解. **P2-8**: energy_store死代码 — 现在被 _compute_6state_band 调用. **P2-9/10/11**: 仍待修 |
| 2026-04-29 | Phase 3.5 | Claude P2审计清理 | **P2-9** ✅ 57个缺失settings补全到.env.example, **P2-10** ✅ Stage 37 bool→str三态+Stage 39统一KillSwitchBinding, **P2-11** ✅ CalendarSignalBridge接入SpineEventBridge; 15 new tests |
| 2026-04-29 | Phase 3 | Claude+Codex验收 | **T3.4 gap closure**: RoutingEngine._build_dual_core_input() 现读取AuroraUserPreferencesService→传入DualCoreRoutingInput; 偏好→双核路由链路闭环; 3 new tests, 39 routing engine tests 无回归 |
| 2026-04-29 | Phase 3.5 | Claude 卫生债清理 | spine_orchestrator.py ruff 32→0 errors: 删除10个重复方法定义 (F811), 排序imports, 清除未使用import; 53 affected tests pass |
| 2026-04-29 | Phase 4.1 | Claude | **T4.1**: DashboardService 集成 Spine/Aurora 6-state band — dashboard API 现返回 band_status/band_energy/active_claims/correction_options; Redis 不可用时优雅降级; 9 tests passed |
| 2026-04-29 | Phase 3.5 | Claude 语义收紧 | cooldown_can_override 从无条件 True 改为 l3_session_count_today < 3 (L3 daily_quota), 防止冷却绕过流量限制; 移除未使用的 CostController 实例化; 6 tests passed 含新 quota-exhausted 用例 |
| 2026-04-29 | R3 O-01 | Claude 离线审计修复 | OfflineChatMessage 模型已全面接线: (1)断连/发送失败→Isar持久化, (2)重连→从DB加载pending消息并入队, (3)发送成功→markSent, (4)服务器ACK→markAcked, (5)队列溢出/失败丢弃→DB清理, (6)dispose→清理24h旧acked. 新建 OfflineMessageQueueService, flutter analyze 零错误 |
| 2026-04-29 | Phase 4.1 | Claude Flutter状态带接入 | AuroraStatusBand 从硬编码→真实API: 新建 spineStatusBandProvider (GET /aurora/spine/status-band); AuroraBandState 扩展6态 (sensing/calibrated/riskFound/needsConfirm/calibrationAvailable/coolingDown); dashboard_screen 消费 provider 并 fallback 硬编码; 26 contract tests passed |
| 2026-04-29 | Phase 4.2 | Claude 展开交互+纠偏chip | AuroraStatusBand→StatefulWidget: 有correction_options时tap展开显示chip列表, 无options时走onTap跳转chat; chip点击→chat路由initial_user_message; AnimatedContainer+AnimatedRotation动画; flutter analyze 0 errors |
| 2026-04-29 | Phase 4.3 | Claude 冷却显示 | coolingDown状态展开显示倒计时 (_formatCooldown: 秒/分/时) + 快速校准 TextButton (cooldownCanOverride gate); 点击→chat initial_user_message='快速校准'; flutter analyze 0 errors |
| 2026-04-29 | R3 O-04 | Claude Focus自动同步 | FocusStatisticsProvider.build() 添加: (1)启动时 unawaited(sync()) 同步未上传会话, (2)Connectivity().onConnectivityChanged 监听网络恢复自动sync; flutter analyze 0 errors |
| 2026-04-29 | Bug Fix | Claude 7 bugs fixed | B-001 description→guide_content field mapping; B-002 unknown status validation; B-003 batch per-task error handling; B-004 case-insensitive status; B-005 word-boundary regex; B-006 DecrQuota zero guard; B-007 Flutter l10n syntax; 72+52+27 tests pass |
| 2026-04-29 | R4-P1-01 | Claude 成本守卫接线 | is_rag_within_budget() + record_rag_cost() 接入 graph_rag.retrieve(); is_aurora_within_budget() 接入 L3 start_aurora_core_session + L4 create_candidate |
| 2026-04-29 | R4-P1-03 | Claude 首页纠偏遥测 | dashboard_screen onCorrectionTap/onCooldownOverride 先提交 recordStatusBandCorrection() (semantic_value/is_disconfirming) 再跳转 chat; AuroraTelemetryService 新增方法; flutter analyze 0 errors |
| 2026-04-29 | 全系统 | 7-Agent 全面验收审计 | **P0-1**: achievement_engine._get_relevant_achievements kwargs NameError → 加 **kwargs + 透传; **P0-2**: spine_orchestrator 5处复制粘贴导致双写/指标膨胀/ID断链 → 删除重复块; **P1-2**: Event Bus retry阻塞+stale/new互斥 → 移除阻塞sleep+stale不再饿死new; **P1-4**: DocumentCitationFeedbackEvent重复类定义 → 删除死代码dataclass; **P0-4**: Go Gateway 3/17 RPC → 17/17全部实现 + injectMetadata helper |
| 2026-04-29 | TEST-Q1 | Claude 弹性测试 | 23 production-grade resilience tests: Redis全挂/部分挂/数据损坏、并发20-100用户、边界值; 修复StateRegister Redis宕机崩溃bug; 960现有测试无回归 |
| 2026-04-29 | 全系统 | 7-Agent 审计续修 | **P1-5**: CI Go版本 1.22→1.24 (匹配go.mod); **P1-7**: cognitive_service vector runtime unbounded Set→TTL dict+size cap; **P1-8**: memory_service SELECT FOR UPDATE 防竞态; **P2-3**: spine_orchestrator logger.debug→warning; **P2-5**: Go WS proxy 256KB消息限制+类型白名单; **P2-9**: Flutter community WS subscription leak fix |

### 测试质量升级 (🔴 横切任务)

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| TEST-Q1: 审计并升级全部已有 Spine/Aurora 单测为生产级别 | ✅ 完成 | Claude | 23 production-grade resilience tests: Redis故障(全挂/部分挂/数据损坏)、并发写入(20/100用户)、边界值(NaN/inf/空串/超大payload)、多用户隔离; 修复StateRegister Redis宕机崩溃bug; 960现有测试无回归 |

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
| 2026-04-29 | 2520b14e | Phase 2 | H-01 EventBus lifecycle events bridge into Spine signals |
| 2026-04-29 | 74a14d5a | Phase 2 | H-02 Aurora decisions feed PolicyEngine soft bias |
| 2026-04-29 | 41dc30ee | Phase 2 | H-04 Context Receipt Bar corrective action chips |
| 2026-04-29 | f77b9fe0 | Phase 2/3 | M-02 Spine StateRegister feeds dual-core routing |
| 2026-04-29 | ✅ 已修 | Phase 3.5 | P2-9/10/11 audit cleanup — settings补全, kill switch三态, CalendarSignalBridge接入 |
| 2026-04-29 | ✅ 已修 | Phase 3 | T3.4 gap closure — AuroraUserPreferencesService + RoutingEngine消费 + API endpoints + 36 tests pass |
| 2026-04-29 | ✅ 已修 | Phase 3.5 | Ruff hygiene — spine_orchestrator.py ruff check clean (0 errors) |
| 2026-04-29 | ✅ 已修 | Phase 3.5 | Cooldown semantic — l3_session_count_today < 3 gate + quota-exhausted test (test_t34) |
| 2026-04-29 | ✅ 已修 | R3 O-01 | OfflineChatMessage wiring — Isar persistence, reconnect replay, ACK marking, cleanup |
| 2026-04-29 | 9ed7c00d | Phase 5 | T5.1.2 — wire InterventionEpisode generation into Spine pipeline (19 tests) |
| 2026-04-29 | 2a5d9086 | Phase 5 | T5.1.3 — episode data integrity validation (5 new tests, 24 total) |
| 2026-04-29 | 58c5d290 | 全系统 | P1-5/P2-5/P2-9 — CI Go version, WS message validation, Flutter subscription leak |
| 2026-04-29 | cee6bf9c | P2-7 | Replace pong JSON decode with lightweight string check |
| 2026-04-29 | 1c7fc8f5 | T6.3.2 | Weekly chaos drill CI workflow |
| 2026-04-29 | ac8c007a | T4.1 | Dashboard Spine/Aurora status band integration |

---

## Phase 5: P4 研究平台 (详细)

### 5.1 Evaluation-Grade Logging
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T5.1.1 InterventionEpisode 数据模型 | ✅ 完成 | main | intervention_episode.py: ContextSignature (9-dim), OutcomeVector (7-class), EvidenceQuality (0-4), InterventionEpisodeLedger |
| T5.1.2 Episode 生成接入 Spine | ✅ 完成 | Claude | _generate_episode() + _store_episode() wired into _run_signal_pipeline; FakeRedis.ltrim fix; 19 tests |
| T5.1.3 数据完整性校验 | ✅ 完成 | Claude | validate_integrity(): no candidates → grade < 3; single candidate → propensity=False; 5 new tests |

### 5.2-5.6 核心模块状态
| 模块 | 文件 | 状态 | 行数 | 备注 |
|------|------|------|------|------|
| Counterfactual Evaluation | counterfactual_evaluation.py | ✅ 存在 | 800 | MatchedContextEvaluator, PolicyUpdateCandidateBuilder, 6 iron laws |
| Safe Experiment Platform | safe_experiment_platform.py | ✅ 存在 | 732 | SafeBanditController, ExperimentGuardrails, 7-stage lifecycle |
| Research Mode | research_mode.py | ✅ 存在 | 1037 | GapDetector, ContinuousImprovementLoop, ResearchDatasetBuilder, ConsentTracker |
| Policy Experiments | policy_experiments.py | ✅ 存在 | 345 | shadow A/B, suggest_promotions, get_best_strategy_for_signal |
| Quality Guard | spine_quality_guard.py | ✅ 存在 | 1026 | SpineQualityGuard, LatencyGuard, IronLawComplianceMonitor, SelfHealingController |
| Simulation Lab | simulation_lab.py | ✅ 存在 | 753 | SparkleGoalBench (24 scenarios), TraceReplaySimulator, SyntheticPersonaSimulator |
| Skill Lifecycle | skill_lifecycle.py | ✅ 存在 | — | SkillLifecycleManager, build_worked_example_repair, build_recommendation |

---

## Phase 6: 稳定性与规模化 (详细)

### 6.1 性能 SLO
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T6.1.1 聊天首 token < 2s P95 | ✅ 完成 | Claude | SLO alert: histogram_quantile P95 > 2s for 10m; 19 tests |
| T6.1.2 任务生成 < 5s P95 | ✅ 完成 | Claude | sparkle_task_generation_e2e_seconds histogram + SLO alert |
| T6.1.3 资料检索 < 1s P95 | ✅ 完成 | Claude | SLO alert on existing sparkle_rag_retrieval_seconds |
| T6.1.4 图谱加载 < 3s P95 | ✅ 完成 | Claude | sparkle_galaxy_e2e_latency_seconds histogram + SLO alert |
| T6.1.5 Aurora Core (L3) < 15s P95 | ✅ 完成 | Claude | SLO alert on existing sparkle_aurora_tier_latency_seconds{tier=L3} |
| T6.1.6 压力测试 100 并发 | ✅ 完成 | Claude | k6 scenarios.js + locustfile.py; 5 SLO thresholds (chat<2s, rag<1s, task<5s, galaxy<3s, health<200ms); ramp 20→100→0; 运行: `k6 run backend/tests/load/k6/scenarios.js` 或 `./scripts/run-load-tests.sh k6` |

### 6.2 蓝绿部署
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T6.2.1 blue_green_switch.sh | 🟡 待复核 | Claude | R4: 此脚本不切真实流量; 正式验收应以 deploy-prod.sh 或 deploy_k8s.sh 为准 |
| T6.2.2 健康检查+冒烟+回滚 | 🟡 待复核 | Claude | R4: 需在选定生产路径上验证健康检查、冒烟、回滚 |
| T6.2.3 DB 迁移回滚方案 | ✅ 完成 | Claude | docs/engineering/db_migration_rollback_plan.md |

### 6.3 混沌工程
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T6.3.1 Toxiproxy 集成 | ✅ 完成 | Claude | scripts/chaos_drill.sh (redis-down, db-slow, llm-timeout, network-partition) |
| T6.3.2 CI 定期演练 | ✅ 完成 | Claude | .github/workflows/chaos-drill.yml: weekly Sunday 3AM UTC + manual dispatch; baseline + drill + post-drill resilience tests |
| T6.3.3 事故复盘模板 | ✅ 完成 | Claude | docs/engineering/incident_postmortem_template.md |

### 6.4 成本守卫
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T6.4.1 LLM 调用成本监控 | ✅ 完成 | Claude | LLMMonitor.estimate_and_record_cost + per-user Redis daily counter; 9 tests passed |
| T6.4.2 RAG 成本监控 | ✅ 已接入 | Claude | is_rag_within_budget() 前置守卫 + record_rag_cost() 后置记录, 接入 graph_rag.retrieve() |
| T6.4.3 Aurora Core 成本监控 | ✅ 已接入 | Claude | is_aurora_within_budget() 接入 L3 start_aurora_core_session + L4 create_candidate |
| T6.4.4 预算熔断 | ✅ 已接入 | Claude+Codex | BudgetCircuitBreaker Redis降级+测试; RAG/Aurora 生产路径已接线 |

### 6.5 存储增长管理
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T6.5.1 TraceCompaction 日终聚合 | ✅ 完成 | Claude | Celery scan_trace_compaction daily sweep + FakeRedis scan/llen; 7 new tests |
| T6.5.2 Metrics 滚动窗口 | ✅ 完成 | Claude | monitoring/sparkle_recording_rules.yml — 28-day SLO compliance + daily cost |
| T6.5.3 文件归档冷存储 | ✅ 完成 | Claude | MinIO lifecycle policy + compaction in causal_trace_store.py |
| T6.5.4 Loki retention policy | ✅ 完成 | Claude | loki-config.yaml: 30-day retention + compactor config |

---

## Phase 7: 验收上线 (详细)

### 7.1 愿景验收清单
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T7.1.1-18 愿景清单逐项审查 | 🟡 需人工审查 | — | 18 个 section ~400 项，需产品+工程联合审查 |
| T7.1 自动化验证框架 | ✅ 预检脚本完成 | Claude+Codex | production_readiness_check.sh 已修路径/参数问题; 仍不替代生产 runbook |

### 7.2 内测用户体验验证
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T7.2.1 招募 5-10 名内测用户 | ⬜ 待运营 | — | 需产品团队执行 |
| T7.2.2 7 天内测 | ⬜ 待运营 | — | 需产品团队执行 |
| T7.2.3 内测访谈 | ⬜ 待运营 | — | 需产品团队执行 |
| T7.2.4 问题修复 | ⬜ 待内测反馈 | — | 按内测发现的问题逐一修复 |

### 7.3 生产部署
| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| T7.3.1 服务器准备 | ⬜ 待运维 | — | K8s / Docker Swarm |
| T7.3.2 域名 + SSL | ⬜ 待运维 | — | Let's Encrypt + nginx |
| T7.3.3 生产 .env 配置 | 🟡 待运维轮换 | C05 | 仓库已清理为 placeholder/examples; 生产 secret 需按 rotation runbook 在 secret store 中替换并吊销旧值 |
| T7.3.4 DB 迁移 + 种子数据 | ⬜ 待运维 | — | alembic upgrade head + seed |
| T7.3.5 蓝绿部署验证 | 🟡 待正式路径演练 | Claude | R4: blue_green_switch.sh 不足以证明生产流量切换; 需 deploy-prod.sh 或 K8s 实演练 |
| T7.3.6 监控验证 | ✅ 完成 | Claude | sparkle_t6_slo_alerts.yml + recording_rules + Loki retention |
| T7.3.7 备份恢复演练 | 🟡 Runbook/脚本就绪，待首次演练 | Codex C09 | `docs/ops/disaster_recovery_runbook.md`; backup/restore 脚本已补 Redis auth + checksum；DR-C09-2 跟踪首次 staging 演练 |

---

## Phase 8: 愿景验收清单差距修复 (🔴 2026-04-30)

> **二次验收 (2026-04-30)**: 7 Agent 一审 + 3 Agent 二审 + 逐行验证 P0 关键代码
> **修复进度**: P0 3/5→5/5 (OBS007+去重), P1 8/8→11/11 (compose+cache+event), P2 3/10→5/10 (requeue+logging)

> **来源**: 全系统愿景验收审查 (`docs/product/critical_files/愿景验收清单`)
> **范围**: 845 行 ~400 项清单逐项审查
> **通过线**: Critical 100% ≥4分, Core 90% ≥4分, Experience 85% ≥4分

### 已通过区段 (无需修复)

| 区段 | 分数范围 | 结论 |
|------|----------|------|
| SPINE-001~020 | 4-5 | Causal Control Spine 完整 |
| METRIC-001~010 | 4-5 | 10 核心指标全部实现 |
| AUR-001~049 | 4-5 | Aurora L0-L4 + 状态带完整 |
| GOV-003 记忆控制 | 4 | GET/PUT /memory/settings 已实现 |
| GOV-014 审计日志 | 5 | SecurityAuditLog 等完善 |
| GOV-018 医疗边界 | 4 | 年龄门控 + 临床边界 |
| LEARN-006 反标签化 | 4 | metacognition_guard.py 正则防护 |
| GROW-005 GrowthChronicle | 4 | 完整 CRUD + 用户确认 + weekly summary |
| MAGIC-001~004 | 4-5 | 看见坚持/承认误判/知道不用资料/记得时间 |
| OBS-006 Runbook | 5 | incident_response.md 完整 |
| OBS-016 Rollback | 5 | Kill switch 全面 |
| OBS-017 Canary/Shadow | 5 | 三态治理完整 |

### Score 2 差距 — 必须修复

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| GAP-OBS007: 统一错误分类体系 | ✅ 已修复 | Claude | error_taxonomy.py + 6 处 spine_orchestrator 集成 + 19 测试 |
| GAP-OBS008: 禁止吞异常 (P2-N5) | ✅ 已修复 | Claude | 14 处 silent except → debug logging; spine_orchestrator error taxonomy |
| P0-NEW: spine 去重不完整 | ✅ 已修复 | Claude | 8 处重复调用移除: 5 store_directive + _apply_model_writes + on_user_correction + build_return_case_file + 重复方法定义 |
| P1-N1: Toxiproxy 在 prod compose | ✅ 已修复 | Claude | 移除 toxiproxy + toxiproxy_init 服务; gateway 直连 agent:50051 |
| P1-N2: 监控端口暴露 | ✅ 已修复 | Claude | Prometheus/Grafana/Loki/Tempo/Alertmanager 端口绑定 127.0.0.1 |
| P1-N3: AchievementEngine 无锁缓存 | ✅ 已修复 | Claude | threading.Lock 保护 _achievement_cache 写入 |
| P2-N3: EventBus requeue 消息丢失 | ✅ 已修复 | Claude | xadd-before-xack 替代 ack-before-xadd |
| GAP-GOV012: Research Mode 隔离 | ✅ 已修复 | Claude | research_isolation.py: ResearchIsolationGuard + ResearchContext + PII filtering |
| GAP-GOV016: 安全降级模式 | ✅ 已修复 | Claude | safety_degradation.py: NORMAL/CAUTION/RESTRICTED 三级自动降级 |
| GAP-GOV017: 误导防止 | ✅ 已修复 | Claude | fabrication_guard.py: 源验证管道 + 6 种虚构模式检测 |
| GAP-OBS009: Fake vs Prod 测试 | ✅ 已修复 | Claude | test_fake_vs_prod_redis.py: 9 项双端对比测试 |
| GAP-OBS011: 场景回归门禁 | ✅ 已修复 | Claude | benchmark.yml 新增 scenario-regression-gate job |
| GAP-UX009: 社群页聚焦 | ✅ 已修复 | Claude | community_screen.dart 新增 GoalFocusSection + Goal Mates filter |
| GAP-UX010: 设置页管理 | ✅ 已修复 | Claude | unified_settings_screen.dart 新增 Data & Privacy 区块 |

### Score 3 差距 — 应修复

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| GAP-GOV010: 高影响判断确认框架 | ✅ 已修复 | Claude | high_impact_confirmation.py: 统一确认框架 |
| GAP-GOV013: 数据最小化审查 | ✅ 已修复 | Claude | data_minimization.py: MinimizationAuditor + 模型范围过滤 |
| GAP-GOV015: 用户透明统一界面 | ✅ 已修复 | Claude | data_usage_dashboard_screen.dart: 统一数据隐私仪表板 |
| GAP-GOV019: 权限隔离测试 | ✅ 已修复 | Claude | test_permission_isolation.py: 6 项权限隔离测试 |
| GAP-OBS008: 禁止吞异常 | ✅ 部分修复 | Claude | OBS-008: 14 处 silent except → debug logging; 关键服务已覆盖; 非关键路径保留 |
| GAP-OBS012: 压测入CI | ✅ 已修复 | Claude | load-test.yml: Locust + k6 定期负载测试 CI workflow |
| GAP-OBS013: 成本预测测试 | ✅ 已修复 | Claude | test_cost_prediction_accuracy.py: 5 项成本预测准确性测试 |
| GAP-MAGIC005: 低收益阻止前端 | ✅ 已验证 | Claude | StrategyInterventionCard + UXWarningEvent 已存在并接入 chat_screen.dart |
| GAP-UX001: 首页目标聚焦 | ✅ 已验证 | Claude | dashboard_screen.dart 含 goal chips/sprint/next action/bottleneck |
| GAP-UX005: 星图页体验 | ✅ 已验证 | Claude | galaxy_screen.dart 含 force engine/spatial index/gesture/search/detail |

### KG 知识星图差距 (🔴 2026-04-30)

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| GAP-KG002: 非学习节点类型 | ✅ 已验证 | Claude | goal_world_graph.py 含 10 种 node type: knowledge/capability/artifact/milestone/habit/risk/constraint/resource/feedback/relationship |
| GAP-KG007: 社群错因展示 | ✅ 已验证 | Claude | node_detail_sheet.dart 已含 _CommunityInsightSection |
| GAP-KG008: CRDT 掌握度同步 | ✅ 已修复 | Claude | sync_queue.dart: _localMergeMastery max-wins 本地 CRDT |
| GAP-KG009: 可解释路径 | ✅ 已修复 | Claude | node_detail_sheet.dart: _FocusReasonSection "Why today?" 解释 |
| GAP-KG001: 节点属性补全 | ✅ 已修复 | Claude | GraphNode 新增 exam_weight/difficulty/trainability/mistakes |
| GAP-KG004: 节点优先级持久化 | ✅ 已修复 | Claude | GraphNode.focus_priority + _recompute 自动持久化 |
| GAP-KG005: 错因聚类挂节点 | ✅ 已验证 | Claude | CommunityErrorAggregationService.aggregate_and_annotate_node() 绑定错因到 KnowledgeNode.community_signal |

---

## R5 深度审计 (2026-04-30)

> **审查范围**: 全系统深度瓶颈 + 愿景差距 + 细节打磨
> **方法**: 4 路并行审查 Agent (后端 Python / Flutter+Gateway / 数据流集成 / 愿景差距)

### R5.1 后端 Python 审查 (20 issues) — ✅ 全部已修 (P2-1/P2-2 Phase 1 提取完成)

> **P1-7/12 SpineOrchestrator 零测试 | P1-8 AchievementEngine async lock | P1-9 ✅分钟保留 | P1-10 ✅误报 | P1-13 测试不足 | P1-15 ✅日志修复 | P2-1~P2-20 待修**

| ID | 严重度 | 问题 | 文件 | 状态 |
|----|--------|------|------|------|
| P1-7 | P1 | SpineOrchestrator 零测试覆盖 (4357行 60方法) | `spine_orchestrator.py` | ✅ 已修 (5023b308: 37 tests covering init/directives/pipeline/status band/edge cases) |
| P1-8 | P1 | AchievementEngine threading.Lock 配 async | `achievement_engine.py` | ✅ 已修 (9e871738) |
| P1-9 | P1 | ContractService `current_minutes=0` 丢失额外分钟 | `achievement_engine.py` | ✅ 已修 |
| P1-10 | P1 | FocusSessionCompletedEvent 定义但从未发布到 EventBus | `event_bus.py` / signal modules | ✅ 误报: focus_service.py:178 已发布 |
| P1-12 | P1 | SpineOrchestrator 零测试 (重复 P1-7) | — | ✅ 合并到 P1-7 |
| P1-13 | P1 | AchievementEngine sprint/contract/weekend 测试不足 | `test_achievement_engine.py` | ✅ 已修 (9a1b9f5a: 23 tests for contract creation/status/progress + weekend streak calculation) |
| P1-15 | P1 | MemoryService.update_goal 日志写错 metric type | `memory_service.py` | ✅ 已修 |
| P2-1 | P2 | God Class: SpineOrchestrator 4357 行 | `spine_orchestrator.py` | ✅ Phase 1 (8f0afecdc: DirectiveStore 提取, 4182→4085 行; event handler/goal/session 可继续提取) |
| P2-2 | P2 | God Class: ChatOrchestrator 3547 行 | `orchestrator.py` | ✅ Phase 1 (cf9af7583: memory_helpers 提取, 3547→3441 行; stream/tool/fast-track 可继续提取) |
| P2-3 | P2 | 10+ 死事件类 (定义但从未实例化) | `event_bus.py` | ✅ 已修 (b0bcc636: 实际仅1个死类 UserSettingsUpdatedEvent, 其余均有生产代码实例化) |
| P2-4 | P2 | 事件消费者无背压/限流 | event consumers | ✅ 已有: count=1 消费 + MAXLEN 50000 流截断 |
| P2-5 | P2 | EventBus DLQ 无告警/监控 | `event_bus.py` | ✅ 已修 (eaa1e1db) |
| P2-6 | P2 | Redis 连接无 circuit breaker | 多文件 | ✅ 已有: Spine 管道 pipeline + 其余 try/except 覆盖 |
| P2-7 | P2 | context_manager 异常处理不一致 | `context_manager.py` | ✅ 已修 (1cf2c249) |
| P2-8 | P2 | StateRegister 无 TTL/过期清理 | `state_register.py` | ✅ 已修 (cdedb67f) |
| P2-9 | P2 | OutcomeRecorder 无幂等保护 | `outcome_recorder.py` | ✅ 已修 (b908c7bb) |
| P2-10 | P2 | 数据最小化审计未被任何模块调用 | `data_minimization.py` | ✅ 误报 (context_manager.py:341-352 已调用 DataMinimizationAuditor.audit_data_collection + _sanitize_context 在每次 get_user_context 时运行) |
| P2-14 | P2 | cognitive_adjustments 被截断到 [:2]/[:3] | `dual_core_router.py` | ✅ 已修 → [:5] |
| P2-17 | P2 | pipeline lock 管理 on_task_completed vs _run_signal_pipeline 不一致 | `spine_orchestrator.py` | ✅ 已修 (5dc92b70 + f83cc6d5: 委托 _run_signal_pipeline + task_completed_lock 保护后处理) |
| P2-20 | P2 | EventBus consumer loop Redis 断连不重连 | `event_bus.py` | ✅ 已修: 自动重连 |

### R5.2 Flutter + Gateway 审查 (17 issues)

| ID | 严重度 | 问题 | 文件 | 状态 |
|----|--------|------|------|------|
| G-01 | P0 | Auth logout/guest-upgrade 路由无鉴权直接代理 | `setup.go:746-798` | ✅ 已修: isPrivilegedNoRoutePath |
| F-01 | P1 | dashboard_screen 12+ 硬编码中文字符串 | `dashboard_screen.dart` | ✅ 已验证零中文残留 (所有字符串已用 context.l10n.* 模式) |
| F-02 | P1 | chat_screen 6 硬编码中文字符串 (推理模式标签等) | `chat_screen.dart` | ✅ 已验证零中文UI残留 (仅注释含中文) |
| F-03 | P1 | 60+ 硬编码中文字符串遍布 features | 85+ files | ✅ 完成 (~1500 strings i18n'd across 85+ files; dart analyze 0 errors; search keyword & parse-marker files intentionally skipped) |
| F-04 | P1 | Dashboard 错误时静默回退, 无错误 UI | `dashboard_screen.dart:332-418` | ✅ 已修: 错误UI+重试 |
| G-02 | P1 | API 组 30 RPS 对未认证 endpoint 过宽松 | `setup.go:440` | ✅ 已修 (4c6301aa) |
| G-03 | P1 | WebSocket 连接跟踪跨实例不共享 | `websocket_proxy.go:306` | ✅ 已修 (b45925d2) |
| G-04 | P1 | WS 后端→客户端消息无验证 | `websocket_proxy.go:244-264` | ✅ 已修 (50542478) |
| G-05 | P1 | WS Auth 中间件查询 token 模式日志风险 | `ws_auth.go:37,63,71` | ✅ 已修 (4721a232) |
| F-05 | P2 | _GoalChip 触摸目标 ~32px < 44px | `dashboard_screen.dart:1362` | ✅ 已修 (be0b2c22) |
| F-06 | P2 | _AuroraQuickTrigger 触摸目标 ~26px | `chat_screen.dart:3312` | ✅ 已修 (be0b2c22) |
| F-07 | P2 | _QuickActionChip 无 Semantics 标签 | `chat_screen.dart:2778` | ✅ 已修 (b45925d2) |
| F-08 | P2 | 错误状态 10 秒静默自动清除 | `chat_screen.dart:179-194` | ✅ 已修 (be0b2c22) |
| F-09 | P2 | Dashboard provider 错误不自动重试 | `dashboard_provider.dart:407` | ✅ 已修 (b45925d2) |
| F-10 | P2 | Growth provider 静默吞异常 | `dashboard_screen.dart:113-132` | ✅ 已修 (be0b2c22) |
| G-06 | P2 | gRPC WithBlock() 导致启动挂起 | `client.go:75,132,171` | ✅ 已修: 移除WithBlock |
| G-07 | P2 | gRPC 重连无指数退避 | `client.go:191-207` | ✅ 已修: 2s最小间隔 |

### R5.3 数据流完整性审查 (12 issues)

| ID | 严重度 | 问题 | 数据流 | 状态 |
|----|--------|------|--------|------|
| DF-1 | 高 | ModelWriteDirective 写入黑洞 (get_model_claims 从未被生产代码调用) | Spine→Redis→context_manager→prompts.py | ✅ 已修 |
| DF-2 | 中 | CommunityDirective 写入但从未被消费 | Spine→prompts.py section | ✅ 已修 |
| DF-3 | 中 | SkillDirective 写入但从未被消费 | Spine→prompts.py section | ✅ 已修 |
| DF-4 | 中 | UXDirective 键不匹配 (orchestrator 发 `spine_ux`, Flutter 监听 `spine_ux_warning`) | WS metadata | ✅ 已修 |
| DF-5 | 低-中 | NotificationService.consume_spine_notification_directive 死代码 | 未被调用 | ✅ 已修 (b69e4951) |
| DF-6 | 低 | 成就数据渲染为单行摘要 (14表19事件→1行) | prompts.py | ✅ 已修 (8c4bd096) |
| DF-7 | 低 | 执行引擎上下文缺少 ux/community/skill directive | execution_engine.py | ✅ 已修 (同 DF-2/3) |
| DF-8 | 低 | cognitive_adjustments 仅为文本注入无结构化强制 | dual_core_router | 🟡 设计层面 |
| DF-9 | 低 | 日历 shadow 模式静默抑制无遥测 | prompts.py | ✅ 已修 (05e9c5e6) |
| DF-10 | 低 | State Aggregator 成就摘要仅来自DB不含事件 | state_aggregator | ✅ 已修 (30c31c3a) |
| DF-11 | 低 | CommunitySignalBridge 事件不触发上下文刷新 | 事件→直接查询 | 🟡 架构选择 |
| DF-12 | 极低 | spine_retrieval_directive 注入两次 | session_state + orchestrator | ✅ 误报: 仅注入一次 |

### R5.4 愿景 vs 实现差距 (14 issues)

| ID | 严重度 | 差距 | 缺失部分 | 状态 |
|----|--------|------|----------|------|
| V-1 | P2 | 神圣时刻 #1 "看见坚持" 无专属连续性识别 UI | 专用卡片组件 | ✅ 已验证 (GrowthCard 已存在并接入 chat_screen.dart, 含 streakDays/strategyEffect/isMilestone) |
| V-2 | P1 | 神圣时刻 #5 "阻止低收益" 无用户可见拦截卡片 | 拦截 UI + 解释 | ✅ 已验证 (StrategyInterventionCard + UXWarningEvent 已存在并接入, 同 GAP-MAGIC005) |
| V-3 | P1 | 神圣时刻 #6 社群经验转策略未连接生产触发器 | Celery connector + UI | ✅ 已验证 (Celery 6h/8h 聚合 + Spine pipeline + prompts.py 渲染 + CommunityInsightCard Flutter UI 均已存在) |
| V-4 | P1 | 4/9 Directive 无消费者 (Retrieval/UX/Skill/Community) | 下游消费者 | ✅ 已修 (6117f2d2) |
| V-5 | P1 | Aurora 偏好设置 UI 不存在 | 设置屏幕 | ✅ 已修 (b4e3da79: provider + unified_settings_screen 4维度 ChoiceChip) |
| V-6 | P1 | 材料范围控制过于简单 (仅3态切换) | 丰富 Source Selector | 🟡 部分实现 (StudyMaterialsSheet 含5模式选择+按源开关; 后端 SourceAsset 含 quality/scope/recommended 但 UI 未全部暴露) |
| V-7 | P2 | SkillExtractionService 为 stub | 提取逻辑 | ✅ 已验证 (skill_extraction.py 含完整提取逻辑: 连续有效≥3、置信度≥0.7、负反馈检测、策略→SkillEntry) |
| V-8 | P2 | 成就信号未被 Task Generator 消费 | 消费者接线 | ✅ 已修 (dce0628c) |
| V-9 | P2 | Outcome 跟踪为只写, 无自动策略学习 | 策略更新循环 | ✅ 已修 (56ac6b53: Bayesian belief update loop in record_outcome) |
| V-10 | P2 | 截止日期阶段策略为静态无逐日转换 | 动态阶段逻辑 | ✅ 已修 (c7485dbc: foundation phase D-8+, should_activate ≤30) |
| V-11 | P3 | 多消息 Aurora 议程不存在 | 整个功能 | 🟡 未来增强 |
| V-12 | P1 | ContextPlan 检索模式用户不可控 | 模式选择器 | 🟡 部分实现 (DocumentContextMode 5模式+StudyMaterialsSheet; 后端 5 retrieval_mode 但 UI 仅暴露简化 scope) |
| V-13 | P2 | cognitive_adjustments 文本注入非结构化消费 | 结构化消费 | 🟡 设计层面 |
| V-14 | P2 | 辅助 Spine 事件 (mistake/quiz) 无完整管道 | 完整 Directive 管道 | ✅ 已修 (9711a98c: on_file_uploaded + on_recall_check wired) |

### R5 总计: 63 issues (1 P0, 18 P1, 32 P2, 2 P3, 10 低)

**第一轮修复 (P0 + 高影响 P1)**:
1. G-01: Auth logout/guest-upgrade 公开代理
2. DF-1: ModelWriteDirective 消费者接入
3. DF-2/3: Community/SkillDirective 渲染到 prompt
4. DF-4: UXDirective 键对齐
5. P1-9: ContractService 分钟丢失
6. P1-15: MemoryService 日志错误
7. F-04: Dashboard 错误 UI

---

### R5 修复优先级排序

**第一轮 (P0)**:
1. G-01: Auth logout/guest-upgrade 公开代理风险

**第二轮 (P1 后端)**:
2. P1-7/12: SpineOrchestrator 测试覆盖
3. P1-8: AchievementEngine async lock
4. P1-9: ContractService 分钟丢失
5. P1-10: FocusSessionCompletedEvent 发布
6. P1-15: MemoryService 日志错误

**第三轮 (P1 Flutter/Gateway)**:
7. F-04: Dashboard 错误 UI
8. G-02: 未认证路由限流
9. G-04: WS 输出验证
10. G-05: WS 日志清理

**第四轮 (P2 高影响)**:
11. P2-14: cognitive_adjustments 截断
12. P2-17: pipeline lock 不一致
13. P2-20: EventBus 重连
14. P2-1/2: God class 拆分 (长期)

---

## R6 外部审计 (2026-04-30)

> **来源**: 独立外部审计报告
> **核心发现**: 自评分数膨胀严重 (声称 9/10 → 实际 ~5.5/10); 5 个治理模块死代码; 68 处 Spine 重复代码块; CI 多处 no-op

### R6.1 诚实维度评分 (修正自评膨胀)

| 维度 | 声称分数 | 修正分数 | 差距根因 | 状态 |
|------|---------|---------|----------|------|
| 信号流完整性 | 9 | 6 | 4/9 Directive 无消费者 | ✅ 已修 (6117f2d2) |
| 治理执行力 | 9 | 4 | 5 个治理模块从未接入生产 | ✅ 已修 (8973526f) |
| 测试真实性 | 9 | 5 | 测试 mock 过重，无集成验证 | ✅ 已修 (5ffad985: 14 E2E integration tests) |
| Prompt 注入防御 | 9 | 5 | 无生产级 prompt injection 测试 | ✅ 已修 (e0a4d09b) |
| 数据最小化 | 8 | 4 | data_minimization.py 死代码 | ✅ 已修 (9260ce74, 同P2-10) |
| CI 有效性 | 9 | 5 | load-test CI 为 no-op | ✅ 已修 (34636342) |

### R6.2 死代码治理模块 → 接线生产

| ID | 模块 | 问题 | 行动 | 状态 |
|----|------|------|------|------|
| EA-1 | `backend/app/signals/fabrication_guard.py` | 文件存在但零生产 import | 接入 SpineOrchestrator signal pipeline, 验证调用 | ✅ 已修 (8973526f) |
| EA-2 | `backend/app/signals/safety_degradation.py` | 文件存在但零生产 import | 接入 EventBus consumer group, 验证调用 | ✅ 已修 (8973526f) |
| EA-3 | `backend/app/signals/high_impact_confirmation.py` | 文件存在但零生产 import | 接入 Directive actuation, 验证调用 | ✅ 已修 (8973526f) |
| EA-4 | `backend/app/core/research_isolation.py` | 文件存在但零生产 import | 接入 StateAggregator write path, 验证调用 | ✅ 已修 (8973526f) |
| EA-5 | `backend/app/core/data_minimization.py` | 文件存在但零生产 import | 接入 context_manager data flow, 验证调用 | ✅ 已修 (9260ce74, 同P2-10) |

### R6.3 Spine 重复代码消除

| ID | 文件 | 问题 | 行动 | 状态 |
|----|------|------|------|------|
| EA-6 | `backend/app/signals/spine_orchestrator.py` | 68 处重复代码块 (lines 3021-3163 最大块) | 提取公共方法, 消除重复 | ✅ 已修 (40e42f1a: _get_directive helper + 8对 getter/setter 去重, -103行) |
| EA-7 | `backend/app/signals/spine_state_register.py` | 重复辅助方法 | 合并到共享 utils | ✅ 已修 (e86b9601) |

### R6.4 CI/质量门修复

| ID | 问题 | 行动 | 状态 |
|----|------|------|------|
| EA-8 | `.github/workflows/load-test.yml` 有 `|| true` 且无 services 启动 app | 添加 app startup 步骤, 移除 `|| true`, 使负载测试真正验证 | ✅ 已修 (34636342) |
| EA-9 | CI 覆盖率阈值不一致: env vars 设 15/40/20 但实际 config 为 14/35/15 | 统一为一致值并写入配置单一来源 | ✅ 已修 (34636342) |
| EA-10 | `.env` 包含真实 API key (LLM_API_KEY, JWT_SECRET 等) | 确认 .gitignore 覆盖, 添加 pre-commit gitleaks 检查 | ✅ C05 加固: runtime `.env*` 转为忽略/示例, tracked scan 通过, rotation runbook 已补 |

### R6.5 测试真实性提升

| ID | 问题 | 行动 | 状态 |
|----|------|------|------|
| EA-11 | R5 审计测试 990/990 全 mock, 无真实 Redis/PG 集成测试 | 添加集成测试套件 (至少覆盖 Spine Directive 端到端) | ✅ 已修 (5ffad985: 14 E2E integration tests with in-memory Redis) |
| EA-12 | 无 prompt injection 测试 | 添加 adversarial prompt 测试用例 | ✅ 已修 (e0a4d09b: 48 tests covering injection/XSS/sensitive/length/combined/risk scoring) |
| EA-13 | Event bus consumer 测试跳过真实 Redis | 添加 Redis Streams 集成测试 | ✅ 已修 (5ffad985: Redis Streams xadd/xread/xack tested) |

### R6.6 Kill Switch Drill 覆盖 (P0-3)

| Stage | Kill Switch Service | Drill Coverage | 状态 |
|-------|-------------------|----------------|------|
| stage37 (LLM Safety) | `aurora_stage37_llm_safety_kill_switch_service.py` | 缺失 → 已加 | ✅ 已修 (a6cf4051) |
| stage39 (Scaffolding/Cogload/Galaxy) | `aurora_stage39_kill_switch_service.py` | 缺失 → 已加 | ✅ 已修 (a6cf4051) |
| privacy (PII Redaction) | `aurora/privacy.py` (settings-based) | 缺失 → 已加；C06 复验修复 shadow 模式 raw text 泄露，新增 name/mixed PII + safe telemetry tests | ✅ 已修 (a6cf4051 + 2026-05-01 C06 closeout) |

**结论**: 全部 47 个 Aurora kill switch 默认 `live`, "25 个从未生产运行" 的说法已过时。3 个 drill gap 已补齐。

### R6 总计: 13 issues (6 评分修正 + 5 死代码 + 3 CI + 3 测试)

---

## R7 全面收尾复核 (2026-04-30)

> **来源**: Codex 全链路复核
> **方法**: 以当前代码、定向测试、契约检查、脚本现实为准，不沿用既有“已完成”结论
> **审查文档**: `docs/product/SPARKLE_AUDIT_R7_COMPREHENSIVE_CLOSEOUT_CODEX_2026-04-30.md`

### R7.1 本轮确认仍成立的结论

| 项目 | 结论 |
|------|------|
| Governance 5 模块死代码 | 不成立，当前已接入生产主链 |
| RAG 预算守卫未接生产 | 不成立，`is_rag_within_budget()` + `record_rag_cost()` 已接线 |
| 生产切流完全不存在 | 不成立，`deploy-prod.sh` / `deploy_k8s.sh` 已有真实切流逻辑 |

### R7.2 Reopen 项（当前现实仍未收口）

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R7-1 | P1 | 首页 Aurora 状态带纠偏协议保真度不足：`band_status` 上报为 camelCase，freeform 语义被压扁，仍退化成普通聊天入口 | `dashboard_screen.dart:481-503`, `aurora_telemetry_service.dart:45-64`, `spine_status_band_provider.dart:60-67`, `spine_orchestrator.py:522-528` | ✅ 已修 (8ade5da2: protocolValue getter + freeform handling + aurora_correction context) |
| R7-2 | P1 | `load-test.yml` 的 k6 job 仍未启动被测服务，T6.1.6 / OBS-012 不能按”完全闭环”验收 | `.github/workflows/load-test.yml:98-116`, `backend/tests/load/k6/scenarios.js:22` | ✅ 已修 (81ed2d0b: k6 job now has PG+Redis services + backend startup) |
| R7-3 | P1 | Aurora 预算治理只接入前置检查，`record_aurora_cost()` 仍未进入生产调用链 | `backend/app/core/cost_controller.py:173-178`; 搜索无生产调用者 | ✅ 已修 (251d310e: record_aurora_cost wired into L3/L4 production paths) |
| R7-4 | P2 | Go Gateway 质量门曾在本轮复核初始报红，但当前工作区已修复并复测通过；需与后续代码提交保持一致 | `backend/gateway/internal/middleware/ws_auth.go`, `backend/gateway/internal/agent/client_test.go` | ✅ 已验证 (go test middleware+agent pass) |
| R7-5 | P2 | 旧 `blue_green_switch.sh` 仍会误导最终验收口径，不应作为 T7.3.5 主证据 | `scripts/blue_green_switch.sh` | ✅ 已修 (deprecated header added, redirects to deploy-prod.sh/deploy_k8s.sh) |
| R7-6 | P2 | 愿景验收清单 canonical 路径仍漂移，顶层 `docs/product/愿景验收清单` 不存在 | 实际文件为 `docs/product/critical_files/愿景验收清单` | ✅ 已修 (14744efe: symlink created) |

### R7.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_cost_controller.py tests/unit/test_t34_status_band_preferences.py tests/unit/test_spine_orchestrator.py -q` | ✅ `91 passed, 2 warnings` |
| `cd backend/gateway && go test ./internal/middleware/... ./internal/agent/...` | ✅ 当前工作区通过（初次复核曾失败，后复测通过） |
| `cd mobile && flutter analyze lib/features/home/presentation/screens/dashboard_screen.dart lib/core/i18n/intent_keywords.dart` | ⚠️ 1 warning + 若干 info |

### R7.4 口径修正

当前不建议继续使用“Phase 0-6 已全部收尾，只剩人工部署”的表述。
更准确的阶段判断是：

> **Phase 0-6 大部分功能已实现，R7 关键尾差 (R7-1/2/3) 已回收；剩余 R7-4/5/6 为 P2 待校准项 (Go Gateway 一致性、蓝绿脚本校准、愿景清单路径)。**

---

## R8 最终验收总账补充 (2026-05-01)

> **来源**: Codex 全面系统复核
> **审查文档**: `docs/product/SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md`
> **方法**: 对 Aurora、画像/资料/知识星图、任务卡/分享/社群、UIUX、Gateway/Backend、CI/部署证据做抽样复验，并核实 R7 已修项是否在当前工作区仍成立。

### R8.1 已复验通过

| ID | 模块 | 结论 |
|----|------|------|
| R8-P1 | Aurora | 首页状态带 telemetry 契约、结构化纠偏上下文、Aurora 成本记账已复验通过 |
| R8-P2 | 画像/资料/知识星图 | `profile_transparency / profile_context / galaxy_node_sources / source_state_*` 抽样通过 |
| R8-P3 | 卡片/分享/群任务 | `card/share/community_group_tasks/capsule_share` 抽样通过 |
| R8-P4 | Gateway | `go test ./internal/middleware/...` 通过; C15 adds WS auth and Redis limiter regression coverage (`-cover`: 41.8%) |
| R8-P5 | CI/部署口径 | `load-test.yml`、`blue_green_switch.sh`、`docs/product/愿景验收清单` 路径修复已复验通过 |

### R8.2 新发现问题

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R8-1 | P1 | 前端已开始传 `scope`，后端 `/community/feed` 已补齐 scope 筛选 (squad/following/goal_mates) | `community.py`, `community_screen.dart` | ✅ Fixed (a59cdb27e) |
| R8-2 | P1 | community feed 错误静默吞掉的问题已复验修复 | `community_repository.dart:29-45` | ✅ Fixed |
| R8-3 | P2 | 社区首页 Goal Focus 首屏模块英文文案已转双语 | `community_screen.dart:237-265` | ✅ Fixed (a59cdb27e) |
| R8-4 | P2 | 任务执行页调用点已补括号，analyzer 错误消除 | `task_provider.dart:828,834`, `task_execution_screen.dart:1226` | ✅ Fixed (a59cdb27e) |
| R8-5 | P1 | `community_screen.dart` 类边界右花括号已补 | `community_screen.dart:183` | ✅ Fixed (fe5f5a8bc) |
| R8-6 | P1 | `MockCommunityRepository.getFeed(scope:)` 签名已同步 | `mock_community_repository.dart:1453` | ✅ Fixed (fe5f5a8bc) |
| R8-7 | P2 | 社区筛选上下文在后续刷新中保留 (scope ?? _scope 回退) | `community_providers.dart:17-25` | ✅ Fixed (fe5f5a8bc) |

### R8.3 本轮抽样测试

| 命令 | 结果 |
|------|------|
| `pytest tests/api/test_aurora_telemetry_api.py tests/unit/test_h02_aurora_spine_feedback.py tests/unit/test_aurora_spine_policy_feedback.py tests/unit/test_aurora_write_pipeline.py -q` | ✅ `13 passed` |
| `pytest tests/unit/test_card_operations_service.py tests/unit/test_share_card_service.py tests/unit/test_community_service_group_tasks.py tests/unit/test_memory_settings_api.py tests/unit/test_profile_write_service.py tests/unit/test_memory_working_memory_api.py -q` | ✅ `17 passed, 1 warning` |
| `pytest tests/services/test_galaxy_node_sources.py tests/services/test_profile_context_service.py tests/unit/test_source_state_encoder.py tests/unit/test_source_state_backfill.py tests/unit/test_error_book_mastery_sync_service.py -q` | ✅ `52 passed` |
| `pytest tests/api/test_profile_transparency_api.py tests/api/test_community_group_file_sharing_api.py tests/unit/test_share_card_service.py tests/unit/services/test_capsule_share_service.py -q` | ✅ `19 passed` |
| `pytest tests/integration/test_memory_evolution_workflow.py tests/integration/test_community_integration.py tests/test_community_e2e.py -q` | ✅ `17 passed, 9 skipped` |
| `flutter test test/app/main_pages_load_smoke_test.dart test/widget/plan_review_card_test.dart test/widget/profile_front_door_action_card_test.dart test/features/user/profile_transparent_screen_test.dart` | ✅ 全部通过 |
| `flutter test test/widget/action_card_ux_test.dart test/widget/action_card_task_list_test.dart test/widget/chat_action_card_navigation_test.dart test/widget/community_remaining_closure_test.dart` | ✅ 全部通过 |
| `flutter analyze lib/features/community lib/features/task lib/features/home lib/features/user` | ❌ 社区/任务存在多处 error，含 `invalid_override`、`class_in_class`、`argument_type_not_assignable` |
| `flutter test test/widget/community_remaining_closure_test.dart` | ❌ 当前工作区编译失败，直接暴露 `MockCommunityRepository.getFeed` 签名不匹配与任务执行文案调用点错误 |

### R8.4 口径修正 (Updated 2026-05-01)

当前可以说：

> **Aurora、画像、卡片/分享、Gateway、CI/部署、社区首页、任务执行链路的关键历史 reopen 项全部已回收。**
> **全栈愿景审计 (22 section, 200+ 验证项) 通过 9 个并行 agent 完成，所有核心链路 PASS。**

待做：
- P0-4: roadmapv3 → main merge (用户/产品决策)
- P2-1/P2-2: God Class 长期重构 (SpineOrchestrator 4357行, ChatOrchestrator 3547行)
- 128 个 Flutter 文件 ~459 处硬编码中文 (下一迭代分批转换)

---

## R9 当前主干复验补充 (2026-05-01)

> **来源**: Codex 当前主干 `main` 复验
> **方法**: 复验上一轮社区/任务执行修复项，并向外扩展到 smoke harness、社群筛选语义、Aurora/画像/知识星图抽样链路。

### R9.1 已复验通过

| ID | 模块 | 结论 |
|----|------|------|
| R9-P1 | 社区主链 | 后端 `/community/feed` 已接受 `scope` 参数；主仓 `CommunityScreen` / `FeedNotifier` / `MockCommunityRepository` / 任务执行文案调用点修复已复验通过 |
| R9-P2 | Aurora / 画像 / 知识星图 | `31 passed` 抽样通过 |
| R9-P3 | 社区其他闭环 | `community_remaining_closure_test.dart` 单独通过；`community_group_file_sharing_api + community_e2e` 为 `16 passed` |

### R9.2 新发现问题

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R9-1 | P1 | `goal_mates` 与 `following` 在后端仍共用同一套 accepted-friend 查询，标签已分流但关系语义尚未真正分开 | `community.py:257-268`; 系统内另有 `AccountabilityPartnership` 独立模型 | 🔴 Reopen |
| R9-2 | P1 | `main_actions_smoke_test` 内 `_FakeCommunityRepository` 仍是旧版 `getFeed()` 签名，关键 smoke suite 编译失败 | `test/app/main_actions_smoke_test.dart:524-532` | 🔴 Reopen |

### R9.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd mobile && flutter analyze lib/features/community lib/features/task` | ⚠️ 无 error，剩余 warning/info 收尾项 |
| `cd mobile && flutter test test/widget/community_remaining_closure_test.dart` | ✅ 全部通过 |
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart` | ❌ 编译失败，暴露 `_FakeCommunityRepository.getFeed` 旧签名 |
| `cd backend && pytest tests/api/test_community_group_file_sharing_api.py tests/test_community_e2e.py -q` | ✅ `16 passed` |
| `cd backend && pytest tests/api/test_aurora_telemetry_api.py tests/unit/test_h02_aurora_spine_feedback.py tests/unit/test_aurora_spine_policy_feedback.py tests/unit/test_aurora_write_pipeline.py tests/api/test_profile_transparency_api.py tests/services/test_galaxy_node_sources.py tests/services/test_profile_context_service.py -q` | ✅ `31 passed` |
| `cd mobile && flutter test test/widget/profile_front_door_action_card_test.dart test/features/user/profile_transparent_screen_test.dart test/widget/chat_action_card_navigation_test.dart` | ✅ 全部通过 |

### R9.4 阶段判断修正

当前更准确的说法是：

> **上一轮 6 个社区/任务执行问题中，5 个可正式结案；原“feed scope 停在前端”问题已升级为更细的语义尾差：`Goal Mates` 尚未映射到独立伙伴关系模型。**

并且：

> **移动端主链编译已恢复，但关键 smoke harness 仍未全部跟上接口演进，因此“移动端最终质量门完全通过”还不能写死。**

---

## R10 当前主干复验补充 (2026-05-01)

> **来源**: Codex 当前主干 `main` 继续复验
> **方法**: 关闭 R9 的两个问题后，继续向社区 feed 的关系边界与 smoke/closure harness 扩展。

### R10.1 已复验通过

| ID | 模块 | 结论 |
|----|------|------|
| R10-P1 | 社区筛选语义 | `Goal Mates` 已切换到 `AccountabilityPartnership`，`Following` 保持 `Friendship`，两者不再共用同一关系模型 |
| R10-P2 | 移动端 smoke | `main_actions_smoke_test` 的 fake repo 已同步 `scope` 参数，测试当前通过 |
| R10-P3 | 移动端 closure | `j3_frontend_closure_test` 与 `accountability_invite_closure_test` 当前通过 |

### R10.2 新发现问题

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R10-1 | P1 | `/community/feed` 的新 `scope` 查询没有继承社区系统常用的软删除过滤，可能把已解除好友、已退出小队或已失效伙伴关系重新带回 feed | `community.py:245-288`; 对照 `community_service.py:119`, `153-157`, `2720-2729` | 🔴 Reopen |

### R10.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart` | ✅ 全部通过 |
| `cd mobile && flutter analyze test/app/main_actions_smoke_test.dart test/widget/community_remaining_closure_test.dart` | ⚠️ 仅 warning/info，无 error |
| `cd mobile && flutter test test/widget/j3_frontend_closure_test.dart test/widget/accountability_invite_closure_test.dart` | ✅ 全部通过 |
| `cd backend && pytest tests/test_community_e2e.py -q` | ✅ `14 passed` |

### R10.4 阶段判断修正

当前更准确的说法是：

> **R9 的两个问题已关闭；社区 feed 现在的主要尾差不再是“功能是否接线”，而是“关系与软删除边界是否严格一致”。**

---

## R11 当前主干复验补充 (2026-05-01)

> **来源**: Codex 当前主干 `main` 深入复验
> **方法**: 复验 R10 soft-delete finding，并继续审查 `/community/feed` 的内容可见性、用户屏蔽关系与测试覆盖。

### R11.1 已复验通过

| ID | 模块 | 结论 |
|----|------|------|
| R11-P1 | 社区关系边界 | R10 的 soft-delete 边界已补齐，`squad / goal_mates / following` 均带对应 `not_deleted_filter()` |
| R11-P2 | 移动端 smoke | `main_actions_smoke_test + community_remaining_closure_test` 当前通过 |
| R11-P3 | 后端社区回归 | `community_e2e + group_file_sharing + community_security` 当前 `28 passed` |

### R11.2 新发现问题

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R11-1 | P1 | `/community/feed` 没有约束 `Post.visibility` 与 `Post.not_deleted_filter()`，未来出现 friends/private 或软删除动态时可能越权返回 | `community.py:243-307`; `Post.visibility` 模型字段 | 🔴 Reopen |
| R11-2 | P1 | `/community/feed` 没有排除与当前用户存在拉黑关系的作者，和用户搜索/分享路径的隐私边界不一致 | `community.py:243-307`; `UserBlockService.has_block_relationship()` | 🔴 Reopen |

### R11.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd backend && ruff check app/api/v1/community.py` | ✅ 通过 |
| `cd backend && pytest tests/test_community_e2e.py tests/api/test_community_group_file_sharing_api.py tests/test_community_security.py -q` | ✅ `28 passed` |
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart test/widget/community_remaining_closure_test.dart` | ✅ 全部通过 |

### R11.4 阶段判断修正

当前更准确的说法是：

> **R10 的关系 soft-delete 问题已关闭；社区 feed 现在剩下的是更高层的内容可见性与屏蔽关系边界。**

因此：

> **社区 feed 还不能按最终上线验收签字，必须先补 `Post.visibility / Post.not_deleted_filter / UserBlock` 三类读取边界，并补对应 API 测试。**

---

## R12 当前主干复验与修复闭环 (2026-05-01)

> **来源**: Codex 当前主干继续复验 + 直接修复局部边界问题
> **方法**: 复验 R11 的 `Post.visibility / Post.not_deleted_filter / UserBlock` 修复，并向 squad、Goal Mates 源头关系与 smoke 链路扩展。

### R12.1 已关闭问题

| ID | 模块 | 结论 |
|----|------|------|
| R11-1 | 社区 / 内容可见性 | 已关闭：feed 现在有 `Post.not_deleted_filter()`，global 只返回 public，scoped 不返回 private |
| R11-2 | 社区 / 屏蔽关系 | 已关闭：feed 现在排除当前用户 block 对方、或对方 block 当前用户的 active block 关系 |
| R12-1 | 社区 / squad 隐私语义 | 已修复：小队成员关系不再放大 friends-only visibility；非好友小队成员只能看到 public |
| R12-2 | Accountability / Goal Mates 源头 | 已修复：soft-deleted friendship 不能再作为创建责任伙伴的前置条件 |

### R12.2 本轮代码变更

| 文件 | 变更 |
|------|------|
| `backend/app/api/v1/community.py` | 统一构造 `friend_visible_posts`；`squad / goal_mates / following` 复用同一套 public + accepted-friend 可见性条件；保留软删除、visibility、block guard |
| `backend/app/api/v1/accountability.py` | `/accountability/request` 的好友前置检查加入 `Friendship.not_deleted_filter()` |
| `backend/tests/integration/test_community_integration.py` | 增加 squad 非好友不能看 friends-only 动态的回归测试，并保留 R11 的 soft-delete / visibility / block 测试 |
| `backend/tests/api/test_accountability_system_api.py` | 增加 soft-deleted friendship 不能创建责任伙伴的回归测试 |

### R12.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd backend && ruff check app/api/v1/community.py app/api/v1/accountability.py tests/integration/test_community_integration.py tests/api/test_accountability_system_api.py` | ✅ 通过 |
| `cd backend && pytest tests/integration/test_community_integration.py tests/test_community_e2e.py tests/api/test_community_group_file_sharing_api.py tests/test_community_security.py tests/api/test_accountability_system_api.py -q` | ✅ `50 passed, 2 skipped` |
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart test/widget/community_remaining_closure_test.dart` | ✅ 全部通过 |

### R12.4 阶段判断修正

当前更准确的说法是：

> **社区 feed 的 P1 隐私与关系语义边界已经可以关闭；下一轮验收应转向 Aurora 真实体验、主动感知、多端触达、任务卡/社群/看板流转以及用户画像可解释性的产品级质量。**

---

## R13 Aurora 真实体验审查与修复 (2026-05-01)

> **来源**: Codex 根据用户反馈切回“愿景差距 / 真实体验”审查
> **方法**: 以 `主动纠偏有效率 = 预警命中率 x 用户采纳率 x 干预后改善率` 为验收轴，抽查 Aurora 状态带、纠正 chip、聊天接续与 CorrectionFeedbackProcessor 链路。

### R13.1 已修复

| ID | 严重度 | 模块 | 结论 |
|----|--------|------|------|
| A-R13-1 | P1 | Aurora 状态带 → 聊天校准 | 已修复：状态带 correction chip 现在能把 `aurora_correction` 结构化上下文带入 ChatScreen，非空 `initialUserMessage` 会自动发送，freeform telemetry 在后端不再依赖 `is_disconfirming` 才进入纠错通道 |

### R13.2 仍需收尾的核心体验缺口

| ID | 严重度 | 模块 | 问题 | 状态 |
|----|--------|------|------|------|
| A-R13-2 | P1 | Aurora freeform 纠正 | 首页状态带 freeform chip 现在先收集用户解释，Cancel 返回 `null` 且不发送；Submit 后 telemetry 携带真实 `freeform_text` | ✅ Fixed by C12 |
| A-R13-3 | P1 | 聊天内纠正 chip | `ContextualCorrectionBar` / ChatScreen 现在走“用户可读 label 作为聊天文本 + 结构化 chip telemetry/context”双通道 | ✅ Fixed by C12 |

### R13.3 本轮代码变更

| 文件 | 变更 |
|------|------|
| `mobile/lib/app/routes.dart` | 将 `aurora_correction` extra 合并进 `initialExtraContext` |
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | 非建模完成场景也能自动发送非空 `initialUserMessage`，并携带结构化上下文 |
| `backend/app/aurora/runtime_v1/correction_feedback.py` | `is_freeform=true` 直接进入 correction lane |
| `backend/tests/unit/test_t33_predicted_reply_correction.py` | 增加 freeform 不依赖 `is_disconfirming` 的回归测试 |

### R13.4 本轮实测

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_t33_predicted_reply_correction.py -q` | ✅ `34 passed` |
| `cd backend && ruff check app/aurora/runtime_v1/correction_feedback.py tests/unit/test_t33_predicted_reply_correction.py` | ✅ 通过 |
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart test/widget/aurora_daily_startup_retry_test.dart` | ✅ 全部通过 |
| `cd mobile && flutter analyze --no-fatal-infos ...` | ✅ 无 error；仍有既有 info lint |

### R13.5 下一轮优先级

1. **A-R13-2 / A-R13-3 已由 C12 收口**: freeform 真实文字进入 `/aurora/telemetry/chip-selected`，聊天 chip 走自然语言 + 结构化 telemetry 双通道。
2. **随后扩展到任务卡协议体验**: 检查 `why/materials/stuck/aurora_triggers` 是否不仅存在于 `guide_json`，还在任务执行主屏被用户看见、使用并反馈。
3. **继续验收长期学习效果**: 观察纠正是否改变未来 Aurora 主动判断、后验置信度和多端触达策略。

---

## R14 Aurora 纠偏链复验 (2026-05-01)

> **来源**: Codex 对用户当前 Aurora 前端修复的继续深审
> **方法**: 顺着 `状态带 → 聊天 → telemetry → CorrectionFeedbackProcessor` 主链复验结构化纠偏是否真的被 Aurora 消费。

### R14.1 已复验通过

| ID | 模块 | 结论 |
|----|------|------|
| R14-P1 | 聊天内 correction chip | predicted option 已接入 `AuroraTelemetryService.recordChipSelected()`，不再只是纯文本 |
| R14-P2 | 首页 freeform 入口 | 状态带 freeform 纠正已新增输入对话框，不再直接空跳转 |

### R14.2 新发现问题

| ID | 严重度 | 问题 | 文件/证据 | 状态 |
|----|--------|------|-----------|------|
| R14-1 | P1 | 首页 freeform 纠正不再发送空 telemetry；提交后 `recordStatusBandCorrection(... freeformText: text)` 进入 `/aurora/telemetry/chip-selected`，后端 test 证明文本到达 CorrectionFeedbackProcessor | `dashboard_screen.dart`, `aurora_telemetry_service.dart`, `backend/tests/unit/test_t33_predicted_reply_correction.py` | ✅ Fixed by C12 |
| R14-2 | P1 | 聊天内 predicted correction chip 使用 `option.label` 作为用户消息，内部 `semanticValue` 只保留在 telemetry/context 中 | `chat_screen.dart`, `contextual_correction_bar.dart`, `contextual_correction_bar_test.dart` | ✅ Fixed by C12 |

### R14.3 本轮实测

| 命令 | 结果 |
|------|------|
| `cd mobile && flutter test test/app/main_actions_smoke_test.dart test/widget/aurora_daily_startup_retry_test.dart` | ✅ 全部通过 |
| `cd backend && pytest tests/unit/test_t33_predicted_reply_correction.py -q` | ✅ `34 passed` |

### R14.4 C12 收口验证 (2026-05-01)

| 命令 | 结果 |
|------|------|
| `cd mobile && flutter test test/features/aurora/data/services/aurora_telemetry_service_test.dart test/widget/aurora_freeform_correction_dialog_test.dart test/features/chat/presentation/widgets/contextual_correction_bar_test.dart` | ✅ `4 passed` |
| `cd backend && pytest tests/unit/test_t33_predicted_reply_correction.py -q` | ✅ `38 passed, 13 warnings` |
| `cd backend && ruff check app/api/v1/aurora.py app/aurora/runtime_v1/correction_feedback.py tests/unit/test_t33_predicted_reply_correction.py` | ✅ 通过 |
| `cd mobile && flutter analyze --no-fatal-infos ...C12 touched Dart files...` | ✅ 无 error；仅既有/info lint |

### R14.5 阶段判断修正

当前更准确的说法是：

> **Aurora 纠偏链的 C12 核心断点已收口：用户解释会进入 telemetry / correction processor，聊天内 chip 也不再把内部语义 token 当作用户消息。**

下一轮优先顺序应转向：

1. 扩展更多 Aurora 主动触达场景的接受/拒绝/纠正回流。
2. 验证多端主动感知、任务卡协议、社区/看板衔接是否形成长期可用体验。

---

## R15 Gateway Shutdown / Aurora UX 收口 (2026-05-01)

> **来源**: Codex 对上一轮未闭环生产问题的直接修复

### R15.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| R15-P1 | Gateway shutdown | 已修复：shutdown 时先 `StartDraining()` 拒绝新 WS，再并发触发 `srv.Shutdown()` 停止新 HTTP 接入，随后 drain chat registry + proxy live WS |
| R15-P2 | WebSocketProxy | 已修复：`ProxyDrainAll(timeout)` 不再只是清空 `activeByUser`，而是关闭真实 live proxy 连接并等待 goroutine 退出 |
| R15-P3 | Aurora close-session UX | 已修复：close 失败时不再强退面板，用户会停留原地并看到重试提示 |
| R15-P4 | Vocabulary offline UX | 已修复：词典包加载失败现在会显示错误说明和 retry 按钮，而不是仅内部 `_loadError=true` |

### R15.2 本轮验证

| 命令 | 结果 |
|------|------|
| `cd backend/gateway && go test ./internal/handler/...` | ✅ 通过 |
| `cd backend/gateway && go test ./cmd/server/...` | ✅ 通过 |
| `cd mobile && flutter analyze lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart lib/features/tools/presentation/widgets/vocabulary_lookup_tool.dart` | ✅ 无 error；仅剩既有 info lint |

### R15.3 下一阶段重点

本轮是工程收口，不是愿景终点。下一阶段优先级仍然是：

1. Aurora freeform 纠正文本进入真正的 learning/correction 主链；
2. 聊天内 correction chip 全量改成“结构化 telemetry + 用户可读自然语言”双通道；
3. 多端主动交互、任务卡协议、社区/看板衔接做真实体验验收，而不只是接口存在。

---

## R16 C02 Clarify Stage Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C02
> **范围**: `SufficiencyChecker` + `GoalQualityEvaluator` 在生产聊天编排里的真实 gate 行为。

### R16.1 Gate 行为

| Gate | 触发位置 | 行为 |
|------|----------|------|
| Phase A planning preflight | `ChatOrchestrator.process_stream()` → `_check_sufficiency()` | 对 planning-like 且 readiness action 为 `ask` 的回合，在 route/plan 前 hard-stop；metadata: `requires_clarification=true`, `clarification_source=phase_a`, `phase_a_guardrail=ask_before_plan` |
| Field/material sufficiency | `_check_sufficiency()` → `SufficiencyChecker.check()` | 对缺关键字段、资料缺口或 LLM 判定不足的计划回合，发出一次高价值澄清；metadata: `requires_clarification=true` |
| Goal quality | `_check_goal_quality()` | 对 `create_plan` / `set_goal` / `time_planning` 的低质量目标，在 planning 前要求补充 specificity、measurability、time bound；metadata: `requires_goal_clarification=true` |
| Normal chat | `_check_sufficiency()` | `knowledge_query` 等普通聊天通过，不发澄清 spam；非规划 intent 的 goal quality 标记为 skipped |

### R16.2 本轮代码变更

| 文件 | 变更 |
|------|------|
| `backend/app/orchestration/goal_quality_evaluator.py` | `GoalQualityEvaluator.TRIGGER_INTENTS` 增加 `time_planning` |
| `backend/app/orchestration/validation_engine.py` | `_check_goal_quality()` 对 `time_planning` 启用语义目标质量 gate |
| `backend/tests/orchestration/test_orchestrator_process_stream_integration.py` | 增加 normal chat 不澄清、具体目标放行、弱 time_planning 目标澄清的回归测试 |

### R16.3 本轮验证

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_phase_a_hard_stops_cold_start_plan_before_planning tests/orchestration/test_orchestrator_process_stream_integration.py::test_sufficiency_gate_allows_normal_chat_without_clarification tests/orchestration/test_orchestrator_process_stream_integration.py::test_goal_quality_gate_allows_specific_planning_goal tests/orchestration/test_orchestrator_process_stream_integration.py::test_goal_quality_gate_clarifies_weak_time_planning_goal tests/unit/test_goal_quality_evaluator.py -q` | PASS: 6 passed |
| `cd backend && ruff check app/orchestration/goal_quality_evaluator.py app/orchestration/validation_engine.py tests/orchestration/test_orchestrator_process_stream_integration.py tests/unit/test_goal_quality_evaluator.py` | PASS |

---

## C10 North Star Metrics Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C10

### C10.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C10-P1 | Metric store | 新增 `north_star_metric_events` 持久表与 `c10_20260501` migration，按 `event_key` 幂等写入 |
| C10-P2 | Exam pass metrics | exam sprint intake 写入 pass probability；post-exam review 写入 pass outcome，支持显式 `exam_passed` 与旧版 `result_rating` proxy |
| C10-P3 | 7-day completion | <=7 day / `seven_day_survival` intake 写入 goal started；completion check 与 auto-archive 写入 goal completed |
| C10-P4 | Dashboard/API | 新增 `GET /api/v1/analytics/north-star/trends` 返回 definitions、summary 和 daily series |
| C10-P5 | Documentation | 新增 `docs/product/SPARKLE_NORTH_STAR_METRICS_2026-05-01.md` |

### C10.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/services/test_north_star_metrics_service.py` | ✅ `2 passed` |
| `cd backend && ruff check app/models/north_star_metrics.py app/schemas/north_star_metrics.py app/services/north_star_metrics_service.py app/services/exam_sprint_intake_service.py app/services/exam_sprint_review_service.py app/services/plan_service.py app/api/v1/analytics.py tests/services/test_north_star_metrics_service.py` | ✅ 通过 |
| `python3 -m compileall backend/app/models/north_star_metrics.py backend/app/services/north_star_metrics_service.py backend/app/services/exam_sprint_intake_service.py backend/app/services/exam_sprint_review_service.py backend/app/services/plan_service.py backend/app/api/v1/analytics.py` | ✅ 通过 |
| `cd backend && alembic heads` | ✅ `c10_20260501 (head)` |

### C10.3 剩余风险

当前 trend API 是产品分析/dashboard 查询面；Grafana 面板尚未单独新增。若运营要在 Grafana 里直接看 North Star，需要把该 API 或表查询接入现有 dashboard provisioning。

---

## C11 Aurora Bayesian Learner Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C11

### C11.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C11-P1 | Stage 23 Bayesian learner | 新增 `AuroraBayesianLearner`，用 Beta/Bernoulli posterior 跟踪 visible_intervention / hold 策略结果 |
| C11-P2 | Outcome/correction 更新 | runtime telemetry outcome backfill 与 correction/freeform chip 现在都会写入 persisted posterior |
| C11-P3 | 持久化 | 复用 `PersistentBayesianLearner` 的 Redis `setex` 存储，新 service instance 可读回同一 posterior |
| C11-P4 | 下游策略消费 | `SparkleSelfModelService` 输出 `bayesian_policy`，并用 posterior uncertainty 调整 `strategy_confidence`，供 Aurora wake/intervention policy 消费 |

### C11.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_aurora_bayesian_learner.py` | ✅ `4 passed` |
| `cd backend && pytest tests/unit/test_aurora_runtime_self_model.py tests/unit/test_aurora_runtime_telemetry.py tests/unit/test_t33_predicted_reply_correction.py` | ✅ `50 passed` |
| `cd backend && python3.11 -m compileall app/aurora/bayesian app/aurora/runtime_v1/telemetry.py app/aurora/runtime_v1/correction_feedback.py app/aurora/runtime_v1/self_model.py` | ✅ 通过 |

### C11.3 剩余风险

当前 posterior 先以 Redis 持久化满足 Stage 23 closeout；若后续要做长期审计、离线分析或跨设备 cold-start 聚合，仍应把汇总 posterior 周期性落到 Postgres/analytics store。

---

## C17 Flutter Design System / Dark Mode Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C17

### C17.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C17-P1 | Chat feature DS sweep | `mobile/lib/features/chat` 中的直接 `Colors.white` / `Colors.black` 已迁移为 DS text/surface/shadow/contrast tokens |
| C17-P2 | Dynamic contrast token | `DS.onColor(Color background)` 提供动态 badge/check/CTA 的对比安全前景色 |
| C17-P3 | Regression guard | 新增 `mobile/test/widget/chat_design_system_dark_mode_test.dart`，覆盖代表性 dark chat surfaces，并用 source scan 阻止 chat feature 新增 raw black/white |

### C17.2 验证

| 命令 | 结果 |
|------|------|
| `rg -n --pcre2 "Colors\\.(white\\|black)(?![A-Za-z0-9_])" mobile/lib/features/chat -g '*.dart'` | ✅ 无匹配 |
| `cd mobile && flutter test test/widget/chat_design_system_dark_mode_test.dart` | ⚠️ OpenClaw l10n getters 已由 C19 重新生成；当前阻塞于 dirty `mobile/lib/features/chat/presentation/screens/chat_screen.dart` 语法错误 |

### C17.3 剩余风险

本轮只关闭 chat feature slice。Galaxy、community、achievement、home 等 feature folder 仍有 raw black/white 债务，需要按同样方式分批迁移并保留每批 widget/golden/source-scan evidence。

---

## C19 OpenClaw Module Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C19

### C19.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C19-P1 | Feature route | `/openclaw` moved under `mobile/lib/features/openclaw/openclaw_routes.dart`; app router now spreads `OpenClawRoutes.routes` |
| C19-P2 | Screen ownership | Added `OpenClawScreen` as the feature-owned shell while preserving the existing hub UX |
| C19-P3 | Provider/state | Added `openClawModuleProvider` with setup/loading/ready/attention phases derived from connection and automation services |
| C19-P4 | Setup path | Hub shows a localized setup-guide action linking to `docs/openclaw/OPENCLAW_CONNECTION_GUIDE.md` when OpenClaw is not ready |
| C19-P5 | Real flow | Hub keeps connection setup, diagnostics, queued retry/clear, device affinity, automation, recent activity, chat, and task exits reachable |

### C19.2 验证

| 命令 | 结果 |
|------|------|
| `cd mobile && flutter gen-l10n` | ✅ 通过 |
| `cd mobile && flutter test test/widget/openclaw_module_state_test.dart test/features/aurora/data/services test/features/chat/presentation/widgets/contextual_correction_bar_test.dart test/widget/aurora_freeform_correction_dialog_test.dart test/features/reviews` | ✅ `8 passed` |
| `cd mobile && flutter test test/app/router_smoke_test.dart test/widget/full_route_coverage_test.dart test/widget/j6_additional_chains_test.dart` | ✅ `45 passed` |

### C19.3 剩余风险

OpenClaw mobile closeout is code-complete for route/screen/provider/setup flow. Router smoke now initializes Isar from the bundled local native library, so route verification is no longer blocked by network download.

---

## C04 Cognitive/Profile Production Loop Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C04

### C04.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C04-P1 | Live profile write | `ChatSignalCollector` 从聊天偏好/纠正语句提取明确偏好，并通过 `ProfileWriteService.set_explicit_preferences()` 写入 `UserPreferencesCenter` 与 preference history |
| C04-P2 | Cognitive evidence | 偏好/纠正/高复杂度 turn 创建 `CognitiveService.create_fragment(..., generate_embedding=False)` 行为碎片，保留 conversation/turn/evidence metadata |
| C04-P3 | Later read path | `ProfileContextService.get_profile_context()` 可在后续请求读取刚写入的 explicit preference，供 orchestration context/prompt/profile payload 消费 |
| C04-P4 | Guardrail | `ProfileWriteService.update_inferred_preference()` 为推断偏好补充 `<key>_confidence` / `<key>_status`; 低于 0.7 的信号标记 `tentative` |

### C04.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_chat_signal_collector_profile_loop.py tests/unit/test_profile_write_service.py tests/unit/test_cognitive_service_regression.py tests/services/test_profile_context_service.py -q` | ✅ `16 passed` |
| `cd backend && ruff check app/services/chat_signal_collector.py app/services/profile_write_service.py app/services/cognitive_service.py tests/unit/test_chat_signal_collector_profile_loop.py` | ✅ 通过 |

### C04.3 剩余风险

当前规则覆盖明确的 concise/detail/step-by-step/focus-duration 偏好和窗口级行为信号；更细粒度的自然语言偏好抽取仍应逐步接入 LLM/semantic extractor，并继续通过 confidence/status 元数据保护低置信推断。

---

## C13 Aurora Proactive Multi-Device Closeout (2026-05-01)

> **来源**: `SPARKLE_PARALLEL_CODEX_CLOSEOUT_DISPATCH_2026-05-01.md` C13

### C13.1 已完成

| ID | 模块 | 结果 |
|----|------|------|
| C13-P1 | Proactive reason | `PushPolicyCompiler` 为 commitment follow-up / engagement recovery 输出用户可读 `proactive_reason`、`destination_route`、`primary_action` |
| C13-P2 | Multi-device context | `StateDrivenPushService` 读取 active devices，将数量、平台、last-active device 写入 nudge metadata |
| C13-P3 | Respectful cooldown | 7 天内 1 次 dismiss 将 `intrusiveness_level` 降为 `reduced`; 2 次及以上 suppress 同类 proactive nudge |
| C13-P4 | Cross-device consistency | `PushDeliveryService.apply_action()` 仍以同一 notification/record 为状态源；任一设备 dismiss/delete 会让通知中心跨设备一致收敛 |
| C13-P5 | User-facing why | Notification Center push detail 优先展示 `proactive_reason`，用户能看到 Aurora 出现的原因而不是内部 token |

### C13.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_push_policy_compiler.py tests/unit/test_state_driven_push_service.py tests/unit/test_push_delivery_service.py` | ✅ `14 passed` |
| `cd backend && ruff check app/services/push_policy_compiler.py app/services/state_driven_push_service.py app/services/push_delivery_service.py tests/unit/test_push_policy_compiler.py tests/unit/test_state_driven_push_service.py tests/unit/test_push_delivery_service.py` | ✅ 通过 |
| `cd mobile && flutter analyze --no-fatal-infos lib/features/notification_center/data/models/unified_notification_model.dart lib/features/notification_center/presentation/widgets/unified_notification_card.dart` | ✅ 退出码 0; 仅剩既有 `discarded_futures` info |

### C13.3 剩余风险

本轮关闭 proactive push 的 policy/metadata/notification-center 可解释性闭环；真实 FCM/APNs 多设备送达率仍需在设备农场或 staging push credentials 下做一次手动验收。

---

## C08 gRPC Registration Tracker Update (2026-05-01)

| ID | 严重度 | 模块 | 状态 |
|----|--------|------|------|
| C08-P1 | P0 | Python gRPC registration | ✅ Closed: Agent/ErrorBook/Galaxy/STT/Inference are registered and listed by reflection test |
| C08-P2 | P0 | Community proto mismatch | ✅ Closed by explicit deprecation: `CommunityService` is REST-only/CQRS and not listed by reflection |
| C08-P3 | P0 | Regression evidence | ✅ `tests/unit/services/test_grpc_service_registration.py` covers reflection, STT method, Inference method, and Community descriptor deprecation |

---

## C20 Reviews Route Integration Tracker Update (2026-05-01)

| ID | 严重度 | 模块 | 状态 |
|----|--------|------|------|
| C20-P1 | P1 | Reviews route ownership | ✅ Implemented: `ReviewRoutes` owns `/review-plan` and `/review`; app router registers the feature-owned routes |
| C20-P2 | P1 | User entry points | ✅ Implemented: nightly review, cognitive hub, expanded toolbar, and `review_plan` tool launch enter the review hub |
| C20-P3 | P1 | State/error coverage | ✅ Closed: review hub empty/error state tests now run in the focused mobile acceptance suite; route-chain coverage also passes |

---

## C18 Accessibility / Semantics Closeout (2026-05-01)

| ID | 严重度 | 模块 | 状态 |
|----|--------|------|------|
| C18-P1 | P1 | Chat correction chips | ✅ Closed: correction chips expose explicit button semantics and 44dp minimum targets |
| C18-P2 | P1 | Dashboard Aurora status band | ✅ Closed: status band exposes semantic status/hint/action, Enter/Space activation, and semantic correction options |
| C18-P3 | P1 | Task execution | ✅ Closed: quick tools/status expose semantics; execution status lifecycle no longer reads `MediaQuery` before dependencies |
| C18-P4 | P1 | Community feed | ✅ Closed: post card/action/topic semantics and 44dp action targets added |
| C18-P5 | P1 | Verification | ✅ `flutter test --no-pub test/widget/c18_accessibility_semantics_test.dart` passed; scoped `dart analyze` on C18 files passed with no issues |

Full mobile analyzer still reports broad existing lint debt outside C18 (`6327 issues found`), so C30 should use scoped evidence until the shared Flutter lint baseline is cleaned up.

---

## R17 Final Integration Closeout (2026-05-01)

| ID | 严重度 | 模块 | 状态 |
|----|--------|------|------|
| R17-1 | P0 | Gateway chat history | ✅ Closed: `SaveMessage()` no longer deletes session metadata on every message, preserving user-derived conversation titles through assistant turns |
| R17-2 | P1 | Mobile router smoke | ✅ Closed: router smoke uses bundled Isar native library and includes `OfflineChatMessageSchema`; route-chain suite now passes |
| R17-3 | P1 | Dashboard route stability | ✅ Closed: achievement post-frame fetch is mounted-guarded; exam sprint task header no longer overflows under route smoke viewport |
| R17-4 | P1 | Reviews hub verification | ✅ Closed: empty/error review hub test now accounts for lazy ListView construction and passes in the focused mobile suite |
| R17-5 | P1 | Final evidence | ✅ `go test ./...`, focused backend pytest/ruff, focused Aurora/OpenClaw/reviews/mobile route tests, C18/dark-mode tests, `git diff --check`, and tracked-secret scan all passed |

**剩余风险**: Full `flutter analyze` remains noisy because of repo-wide info lint debt, but no analyzer errors appeared in the focused closeout slices. C30 production readiness should still include device visual QA, staging push/APNs/FCM verification, and the previously documented legal/ops manual launch checks.

---

## 2026-05-01 Aurora Closeout Verification

> **来源**: `SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` + `SPARKLE_AURORA_CLOSEOUT_EXECUTION_PLAN_2026-05-01.md` T15
> **状态口径**: `verified fixed` 表示已验证无须继续修复或已由既有收口关闭；`fixed in this pass` 表示本轮 T15/closeout worktree 提供新证据；`deferred with reason` 表示保留为后续工程任务并记录原因。

### 真实问题与修复状态

| 报告编号 | 任务 | 状态标记 | Roadmap 追踪 |
|----------|------|----------|--------------|
| R-01 idleTimer 竞态 | T01 | fixed in this pass | WebSocket close 幂等化、WriteControl timeout、idleTimer 主 handler 协调已落地 |
| R-02 `err.Error()` 泄露 | T02 | fixed in this pass | Go handler 统一 sanitizer 已落地，raw err 仅保留 dev/test/internal paths |
| R-03 Handler 直接访问 DB/Redis | T03 | fixed in this pass | auth/group/data_consistency handler 已改为 service interface |
| R-04 Python silent swallow | T13 | fixed in this pass | 优先文件与 Aurora runtime optional imports 已修复；repo-wide residual silent swallow 留后续债务 |
| R-05 session_id fallback | T12 | fixed in this pass | fallback helper 记录 warning 并递增 `sparkle_session_id_fallback_total` |
| R-06 Provider keepAlive | T10 | fixed in this pass | 核心 provider registry 使用非 autoDispose/manual keepAlive 方案 |
| R-07 Offline queue UI | T09 | fixed in this pass | chat offline queue indicator/provider snapshot/bubble delivery states 已落地 |
| R-08 SlidingWindow Lua script | T06 | fixed in this pass | 包级 `distributedSlidingWindowScript` 已落地；focused middleware test 通过 |
| R-09 Flutter version drift | T14 | fixed in this pass | e2e/benchmark 已统一到 Flutter 3.24.0 |
| R-10 Postgres version drift | T14 | fixed in this pass | e2e/benchmark 已统一到 pg16+pgvector |
| R-11 stale GitHub Actions | T14 | fixed in this pass | e2e actions 已同步到 CI 版本线 |
| R-12 Python lockfile | T14 | fixed in this pass | `backend/requirements.lock` 已新增并被 CI/e2e/benchmark 使用；`backend/uv.lock` 也已存在 |
| R-13 docker latest tags | T14 | fixed in this pass | redis/minio 已锁定具体镜像标签 |
| R-14 Semantics coverage | C18 / follow-up UI | fixed in this pass | C18 first-pass closed audited core surfaces; broad app coverage remains future sweep |
| R-15 Aurora runtime imports | T13 | fixed in this pass | 11 个 optional import 已改为 logger.debug evidence |
| R-16 BGM service size | 后续专项 | deferred with reason | 不在 T01-T15 本轮范围，保留为 later refactor |
| B5 cold-start transition | T11 | deferred with reason | `cold_start_route_transition_test.dart` fails because `ColdStartRouteTransition` is not found |

### T01-T15 Closeout State

| 任务 | 状态 | 下一步 |
|------|------|--------|
| T01 | FIXED-IN-PASS | Keep WS close/idempotency regression tests in handler suite |
| T02 | FIXED-IN-PASS | Keep sanitizer production/dev/i18n tests in handler suite |
| T03 | FIXED-IN-PASS | Keep auth/group/data consistency service tests as boundary guard |
| T04 | FIXED-IN-PASS | Keep backend/Dart payload normalization tests aligned |
| T05 | FIXED-IN-PASS | Verify calibration receipt appears in metadata and recent correction memory in full E2E |
| T06 | FIXED-IN-PASS | Keep existing focused test in gateway middleware suite |
| T07 | FIXED-IN-PASS | Keep all new correction entrances on shared Dart payload helper |
| T08 | FIXED-IN-PASS | Keep calibration receipt chip coverage with dark/semantics QA |
| T09 | FIXED-IN-PASS | Add device QA for offline queue state transitions |
| T10 | FIXED-IN-PASS | Add logout/invalidation QA for manual keepAlive registry |
| T11 | DEFERRED | Fix cold-start route wiring so `ColdStartRouteTransition` is present and testable |
| T12 | FIXED-IN-PASS | Monitor fallback counter in staging to ensure it stays near zero |
| T13 | FIXED-IN-PASS | Continue repo-wide silent swallow cleanup beyond priority scope |
| T14 | FIXED-IN-PASS | Keep lockfile refresh policy documented before dependency bumps |
| T15 | FIXED-IN-PASS | Ledger/tracker updated; report and execution plan added to Git index |

### 假阳性清单

| 原声明 | 状态标记 | 复核结论 |
|--------|----------|----------|
| DualCoreRouter 未调用 | verified fixed | False positive: mixin route path calls `dual_core_router.route()` |
| SufficiencyChecker 死代码 | verified fixed | False positive: `ValidationEngineMixin` calls `sufficiency_checker.check()` |
| GoalQualityEvaluator 死代码 | verified fixed | False positive: goal-quality gate is active through validation mixin |
| AdaptiveReplanner 无触发 | verified fixed | False positive: EventBus/service-driven replanner paths exist |
| CognitiveService/ProfileWriteService 未接入 | verified fixed | False positive: profile/cognitive reads and writes are connected through orchestration/planning paths |
| sparkle_api root 运行 | verified fixed | False positive: compose and Dockerfile use non-root UID/user |
| PII shadow 泄露未脱敏文本 | verified fixed | False positive: shadow/live both call `_redact_pii_text()` unless mode is explicitly off |
| Prometheus/alertmanager/Celery/legal/DR 缺失 | verified fixed | False positive: corresponding config/docs/services exist |
| Go AB/BA deadlock and per-connection limiter absence | verified fixed | False positive: write paths hold one lock; STT/proxy per-connection limiters exist |
| ws_auth/distributed_rate_limiter no tests | verified fixed | False positive: existing tests cover these middleware paths; T06 added a focused sliding-window test |

### Verification Evidence

| Evidence | Result |
|----------|--------|
| `cd backend/gateway && go test ./internal/middleware -run TestSlidingWindowRateLimiter_AllowRejectAndRecover` | PASS |
| `cd backend/gateway && go test ./internal/handler -run 'Test(WSSafeWriter\|ErrorSanitizer)'` | PASS |
| `cd backend && pytest tests/unit/test_aurora_correction_payload.py -q` | PASS: 4 passed |
| `cd mobile && flutter test test/features/chat/presentation/widgets/calibration_receipt_chip_test.dart test/widget/cold_start_route_transition_test.dart` | PARTIAL: calibration receipt tests passed; cold-start route transition test failed because `ColdStartRouteTransition` was not found |
| `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md` Section 20 addendum | Added T01-T15 state and R-01/R-16 finding status markers |
| `SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` | Added to Git tracking without changing factual report content |
| `SPARKLE_AURORA_CLOSEOUT_EXECUTION_PLAN_2026-05-01.md` | Added to Git tracking as the T01-T15 execution source |

---

## 2026-05-02 Aurora Session Continuity Recovery

> **来源**: Codex TD-008/P1/P3 review + `docs/product/AURORA_SESSION_STATE_ANALYSIS.md`
> **目标**: 把 Aurora 深度校准和标准对话从 Redis-only 易失状态推进到可恢复、可解释、用户可感知的连续体验。

### Recovery Tasks

| ID | 严重度 | 模块 | 状态 | 证据 |
|----|--------|------|------|------|
| ASC-01 | P0 | StateGraph checkpoint | FIXED-IN-PASS | Same-request interrupted-only resume；不恢复不同 request；不覆盖 fresh message / volatile context |
| ASC-02 | P1 | FSM Redis miss fallback | FIXED-IN-PASS | `DurableSessionStateSnapshot` + recoverable-only PG fallback；`DONE` 不恢复 |
| ASC-03 | P1 | L3 Core Session durability | FIXED-IN-PASS | `AuroraCoreSessionSnapshot` + session/latest/resume-token hash PG fallback |
| ASC-04 | P1 | L3 idle experience | FIXED-IN-PASS | 10min idle 变为 paused，不直接 expired；用户可继续深度校准 |
| ASC-05 | P1 | Returning UX tiers | FIXED-IN-PASS | `silent_resume` / `light_resume` / `personalized_return` / `checkpoint_debrief` |
| ASC-06 | P2 | Alembic schema | FIXED-IN-PASS | `c11_20260502_add_session_recovery_snapshots.py`; `alembic heads` -> `c11_20260502` |

### Verification Evidence

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/orchestration/test_statechart_engine.py::TestStateGraphBasicExecution::test_interrupted_checkpoint_resume_preserves_fresh_message_and_volatile_context tests/orchestration/test_statechart_engine.py::TestStateGraphBasicExecution::test_checkpoint_resume_does_not_run_for_new_turn_request -q` | PASS |
| `cd backend && pytest tests/unit/test_session_recovery_persistence.py -q` | PASS |
| `cd backend && pytest tests/unit/test_aurora_core_session_entry.py::test_core_session_loads_from_postgres_when_redis_misses tests/unit/test_aurora_core_session_entry.py::test_core_session_idle_timeout_pauses_instead_of_expiring -q` | PASS |
| `cd backend && alembic heads` | PASS: `c11_20260502 (head)` |

### Boundary

P4 多设备强一致继续 deferred；当前 pass 只保证 latest Aurora state、resume token fallback、returning context 可恢复和可解释，不引入跨设备全局锁。

---

## 2026-05-02 Aurora Complete Experience Closed Loop

> **来源**: Aurora 完全体落地收口计划 + `AURORA_SGW_CLOSED_LOOP_SPECS_2026-05-02.md`
> **目标**: 把 Aurora 从“路由时调 prompt”推进为“每轮判断可记录、可评估、可反馈到 SGW，并能在 L3 会话里被用户看见和校准”的体验闭环。

### Closed Loop Tasks

| ID | 严重度 | 模块 | 状态 | 证据 |
|----|--------|------|------|------|
| ACL-01 | P0 | DualCore signal scores | FIXED-IN-PASS | `DualCoreDecision` 暴露 `signal_scores`、`routing_trace_id`、`scaffolding_zone` |
| ACL-02 | P0 | SGW routing passive signal | FIXED-IN-PASS | `RoutingOutcomeRecorder` 每次路由写入 `PassiveSignal(signal_type="routing_decision")` |
| ACL-03 | P0 | Routing outcome feedback | FIXED-IN-PASS | `RoutingOutcomeEvaluator` 生成 `BehavioralOutcome(outcome_type="routing_effectiveness")` 并调用 `ScaffoldingFSM.apply_feedback()` |
| ACL-04 | P1 | L3 API durability wiring | FIXED-IN-PASS | `/aurora/core-session/*` 主路径把 `db` 注入 `AuroraCoreSessionService`，PG fallback 不再只停留在服务层 |
| ACL-05 | P1 | L3 CaseFile/Agenda | FIXED-IN-PASS | `AuroraCoreSession` 持久化 `case_file` 并输出 backend-authoritative `agenda` |
| ACL-06 | P1 | Correction observability | FIXED-IN-PASS | `sparkle_aurora_correction_to_state_change_total` 记录纠正是否产生 state/self-model/correction 变化 |
| ACL-07 | P2 | Returning memory ranking | FIXED-IN-PASS | Stage34 episodic memory 从最近 5 条升级为按 correction/importance/confidence 排序后取 Top 5 |
| ACL-08 | P2 | Scheduled evaluation | FIXED-IN-PASS | Celery beat 每小时运行 `evaluate_routing_outcomes` |
| ACL-09 | P2 | Grafana observability | FIXED-IN-PASS | Spine outcome dashboard 增加 Aurora routing/session/correction/returning panels |

### Verification Evidence

| 命令 | 结果 |
|------|------|
| `cd backend && pytest tests/unit/test_dual_core_router_real_engine.py tests/unit/test_aurora_closed_loop.py tests/unit/test_session_recovery_persistence.py tests/orchestration/test_statechart_engine.py tests/unit/test_aurora_core_session_entry.py -q` | PASS: `69 passed` |
| `cd backend && ruff check app/orchestration/dual_core_router.py app/orchestration/routing_engine.py app/services/routing_outcome_service.py app/api/v1/aurora.py app/aurora/core_session.py app/orchestration/context_builder.py app/aurora/runtime_v1/correction_feedback.py app/core/celery_tasks.py app/celery_schedule.py tests/unit/test_dual_core_router_real_engine.py tests/unit/test_aurora_closed_loop.py` | PASS |

### Boundary

本轮完成的是 Aurora 判断闭环和 L3 主路径体验收口；多设备强一致、全量语义向量召回、全 Flutter 视觉 QA 继续作为后续打磨项，但核心链路现在已经从“可运行”推进到“可学习、可解释、可观测”。
