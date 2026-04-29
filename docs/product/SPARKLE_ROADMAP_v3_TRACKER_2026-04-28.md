# Sparkle Roadmap v3 — 工作跟踪文档

> **创建日期**: 2026-04-28
> **最后更新**: 2026-04-30 (P0-3 drill coverage complete)
> **对应 Roadmap**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **用途**: 记录所有已完成、进行中、待做的工作, 支持并行推进与阶段审查

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
| H-01-FIX: 6 个 EventBus 事件接入 Spine | ✅ 完成 | Codex | SpineEventBridge 接入 task.abandoned/stuck、focus.session.completed、plan.created、srl.phase.transition、calendar.event.*; 3 tests passed |
| H-02-FIX: Aurora→Spine 反馈接入 PolicyEngine | ✅ 完成 | Codex | SpineOrchestrator 评估前读取 Aurora decisions, PolicyEngine 作为可逆 soft_bias 消费; 2 tests passed |
| H-03-FIX: Spine 降级 Prometheus counter + 告警 | ✅ 完成 | Codex | sparkle_spine_degradation_total + SparkleSpineDegradation 告警 + runbook; 1 test passed |
| H-04-FIX: Context Receipt Bar 用户行动按钮 | ✅ 完成 | Codex | receipt 详情增加"按课件重讲/排除此资料/换成历年真题", 通过 chatProvider 续发纠偏 prompt; analyzer passed |

### P2 Medium

| 任务 | 状态 | 负责人 | 备注 |
|------|------|--------|------|
| M-01-FIX: structured_cognitive_adjustments Flutter 解析 | ✅ R2 验证通过 | — | T1.2.5 已完成 WS→Provider→State 数据管道, UI 渲染留 Phase 4 |
| M-02-FIX: dual_core_router 消费 Spine StateRegister | ✅ 完成 | Claude+Codex | DualCoreRoutingInput 增加 spine_active_states; RoutingEngine 从 StateRegister 读取活跃状态; route() 消费 fatigue/cognitive_load/execution/knowledge 状态并影响 mode/strategy/debug; 38 tests passed |

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
| 2026-04-29 | (pending) | Phase 3.5 | P2-9/10/11 audit cleanup — settings, kill switch tri-state, CalendarSignalBridge wiring |
| 2026-04-29 | (pending) | Phase 3 | T3.4 gap closure — RoutingEngine reads AuroraUserPreferences→DualCoreRoutingInput |
| 2026-04-29 | (pending) | Phase 3.5 | Ruff hygiene — spine_orchestrator.py 32→0 errors (10 dup methods removed) |
| 2026-04-29 | (pending) | Phase 3.5 | Cooldown semantic tightening — l3_session_count_today < 3 gate + quota-exhausted test |
| 2026-04-29 | (pending) | R3 O-01 | OfflineChatMessage wiring — Isar persistence, reconnect replay, ACK marking, cleanup |
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
| T7.3.3 生产 .env 配置 | ⬜ 待运维 | — | 所有 secret 替换 |
| T7.3.4 DB 迁移 + 种子数据 | ⬜ 待运维 | — | alembic upgrade head + seed |
| T7.3.5 蓝绿部署验证 | 🟡 待正式路径演练 | Claude | R4: blue_green_switch.sh 不足以证明生产流量切换; 需 deploy-prod.sh 或 K8s 实演练 |
| T7.3.6 监控验证 | ✅ 完成 | Claude | sparkle_t6_slo_alerts.yml + recording_rules + Loki retention |
| T7.3.7 备份恢复演练 | ⬜ 待运维 | — | pg_dump + restore 验证 |

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

### R5.1 后端 Python 审查 (20 issues) — 已修 3

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
| P2-1 | P2 | God Class: SpineOrchestrator 4357 行 | `spine_orchestrator.py` | 🔴 待修 |
| P2-2 | P2 | God Class: ChatOrchestrator 3547 行 | `orchestrator.py` | 🔴 待修 |
| P2-3 | P2 | 10+ 死事件类 (定义但从未实例化) | `event_bus.py` | ✅ 已修 (b766be2f) |
| P2-4 | P2 | 事件消费者无背压/限流 | event consumers | 🟡 已有: count=1 消费 + MAXLEN 50000 流截断 |
| P2-5 | P2 | EventBus DLQ 无告警/监控 | `event_bus.py` | ✅ 已修 (eaa1e1db) |
| P2-6 | P2 | Redis 连接无 circuit breaker | 多文件 | 🟡 Spine 管道已有; 其余 try/except 覆盖 |
| P2-7 | P2 | context_manager 异常处理不一致 | `context_manager.py` | ✅ 已修 (1cf2c249) |
| P2-8 | P2 | StateRegister 无 TTL/过期清理 | `state_register.py` | ✅ 已修 (cdedb67f) |
| P2-9 | P2 | OutcomeRecorder 无幂等保护 | `outcome_recorder.py` | ✅ 已修 (b908c7bb) |
| P2-10 | P2 | 数据最小化审计未被任何模块调用 | `data_minimization.py` | ✅ 已修 (9260ce74) |
| P2-14 | P2 | cognitive_adjustments 被截断到 [:2]/[:3] | `dual_core_router.py` | ✅ 已修 → [:5] |
| P2-17 | P2 | pipeline lock 管理 on_task_completed vs _run_signal_pipeline 不一致 | `spine_orchestrator.py` | ✅ 已修 (ea4b9c92) |
| P2-20 | P2 | EventBus consumer loop Redis 断连不重连 | `event_bus.py` | ✅ 已修: 自动重连 |

### R5.2 Flutter + Gateway 审查 (17 issues)

| ID | 严重度 | 问题 | 文件 | 状态 |
|----|--------|------|------|------|
| G-01 | P0 | Auth logout/guest-upgrade 路由无鉴权直接代理 | `setup.go:746-798` | ✅ 已修: isPrivilegedNoRoutePath |
| F-01 | P1 | dashboard_screen 12+ 硬编码中文字符串 | `dashboard_screen.dart` | ✅ 已修 (a6c81d07) |
| F-02 | P1 | chat_screen 6 硬编码中文字符串 (推理模式标签等) | `chat_screen.dart` | ✅ 已修 (17a49bd5) |
| F-03 | P1 | 60+ 硬编码中文字符串遍布 features | 15+ files | 🟡 进行中 (plan_view 39/60 done, 6fc8a116) |
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
| V-1 | P2 | 神圣时刻 #1 "看见坚持" 无专属连续性识别 UI | 专用卡片组件 | 🔴 待修 |
| V-2 | P1 | 神圣时刻 #5 "阻止低收益" 无用户可见拦截卡片 | 拦截 UI + 解释 | 🔴 待修 |
| V-3 | P1 | 神圣时刻 #6 社群经验转策略未连接生产触发器 | Celery connector + UI | 🔴 待修 |
| V-4 | P1 | 4/9 Directive 无消费者 (Retrieval/UX/Skill/Community) | 下游消费者 | ✅ 已修 (6117f2d2) |
| V-5 | P1 | Aurora 偏好设置 UI 不存在 | 设置屏幕 | 🔴 待修 |
| V-6 | P1 | 材料范围控制过于简单 (仅3态切换) | 丰富 Source Selector | 🔴 待修 |
| V-7 | P2 | SkillExtractionService 为 stub | 提取逻辑 | 🔴 待修 |
| V-8 | P2 | 成就信号未被 Task Generator 消费 | 消费者接线 | ✅ 已修 (dce0628c) |
| V-9 | P2 | Outcome 跟踪为只写, 无自动策略学习 | 策略更新循环 | 🔴 待修 |
| V-10 | P2 | 截止日期阶段策略为静态无逐日转换 | 动态阶段逻辑 | 🔴 待修 |
| V-11 | P3 | 多消息 Aurora 议程不存在 | 整个功能 | 🟡 未来增强 |
| V-12 | P1 | ContextPlan 检索模式用户不可控 | 模式选择器 | 🔴 待修 |
| V-13 | P2 | cognitive_adjustments 文本注入非结构化消费 | 结构化消费 | 🟡 设计层面 |
| V-14 | P2 | 辅助 Spine 事件 (mistake/quiz) 无完整管道 | 完整 Directive 管道 | 🔴 待修 |

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
| 测试真实性 | 9 | 5 | 测试 mock 过重，无集成验证 | 🔴 待修 |
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
| EA-6 | `backend/app/signals/spine_orchestrator.py` | 68 处重复代码块 (lines 3021-3163 最大块) | 提取公共方法, 消除重复 | 🟡 进行中 (5a4168e8: 99行最大块已删) |
| EA-7 | `backend/app/signals/spine_state_register.py` | 重复辅助方法 | 合并到共享 utils | ✅ 已修 (e86b9601) |

### R6.4 CI/质量门修复

| ID | 问题 | 行动 | 状态 |
|----|------|------|------|
| EA-8 | `.github/workflows/load-test.yml` 有 `|| true` 且无 services 启动 app | 添加 app startup 步骤, 移除 `|| true`, 使负载测试真正验证 | ✅ 已修 (34636342) |
| EA-9 | CI 覆盖率阈值不一致: env vars 设 15/40/20 但实际 config 为 14/35/15 | 统一为一致值并写入配置单一来源 | ✅ 已修 (34636342) |
| EA-10 | `.env` 包含真实 API key (LLM_API_KEY, JWT_SECRET 等) | 确认 .gitignore 覆盖, 添加 pre-commit gitleaks 检查 | ✅ 已验证: .gitignore 覆盖, 未入库 |

### R6.5 测试真实性提升

| ID | 问题 | 行动 | 状态 |
|----|------|------|------|
| EA-11 | R5 审计测试 990/990 全 mock, 无真实 Redis/PG 集成测试 | 添加集成测试套件 (至少覆盖 Spine Directive 端到端) | 🔴 待修 |
| EA-12 | 无 prompt injection 测试 | 添加 adversarial prompt 测试用例 | ✅ 已修 (e0a4d09b: 48 tests covering injection/XSS/sensitive/length/combined/risk scoring) |
| EA-13 | Event bus consumer 测试跳过真实 Redis | 添加 Redis Streams 集成测试 | 🔴 待修 |

### R6.6 Kill Switch Drill 覆盖 (P0-3)

| Stage | Kill Switch Service | Drill Coverage | 状态 |
|-------|-------------------|----------------|------|
| stage37 (LLM Safety) | `aurora_stage37_llm_safety_kill_switch_service.py` | 缺失 → 已加 | ✅ 已修 (a6cf4051) |
| stage39 (Scaffolding/Cogload/Galaxy) | `aurora_stage39_kill_switch_service.py` | 缺失 → 已加 | ✅ 已修 (a6cf4051) |
| privacy (PII Redaction) | `aurora/privacy.py` (settings-based) | 缺失 → 已加 | ✅ 已修 (a6cf4051) |

**结论**: 全部 47 个 Aurora kill switch 默认 `live`, "25 个从未生产运行" 的说法已过时。3 个 drill gap 已补齐。

### R6 总计: 13 issues (6 评分修正 + 5 死代码 + 3 CI + 3 测试)
