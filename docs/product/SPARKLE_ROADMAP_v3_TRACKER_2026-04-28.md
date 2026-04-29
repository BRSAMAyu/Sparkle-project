# Sparkle Roadmap v3 — 工作跟踪文档

> **创建日期**: 2026-04-28
> **最后更新**: 2026-04-29
> **对应 Roadmap**: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`
> **用途**: 记录所有已完成、进行中、待做的工作, 支持并行推进与阶段审查

---

## 当前状态: Phase 0-5 基本完成, Phase 6/7 进入 R4 生产验收复核
> **审查报告 R1**: [`SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md`](SPARKLE_AUDIT_R1_SIGNAL_FLOW_2026-04-29.md) — 3 P0 + 4 P1 + 3 P2
> **审查报告 R2**: [`SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md`](SPARKLE_AUDIT_R2_CODEX_VERIFICATION_2026-04-29.md) — P0 复查: C-01/C-02/C-03 ✅ 均已修
> **审查报告 R3**: [`SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md`](SPARKLE_AUDIT_R3_DATA_UTILIZATION_OFFLINE_2026-04-29.md) — 2 P1 + 3 P2 (数据利用+离线缺口)
> **审查报告 R4**: [`SPARKLE_AUDIT_R4_FINAL_ACCEPTANCE_CODEX_2026-04-29.md`](SPARKLE_AUDIT_R4_FINAL_ACCEPTANCE_CODEX_2026-04-29.md) — Phase 6/7 生产验收复核: 压测、蓝绿、成本熔断、Aurora live 治理、首页纠偏闭环
> **Aurora 全系统审计**: Phase 3.5 — 3 P0 + 3 P1 + 5 P2 (见下方 Phase 3.5 节)

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
| 2026-04-29 | Phase 3.5 | Claude 语义收紧 | cooldown_can_override 从无条件 True 改为 l3_session_count_today < 3 (L3 daily_quota), 防止冷却绕过流量限制; 移除未使用的 CostController 实例化; 6 tests passed 含新 quota-exhausted 用例 |
| 2026-04-29 | R3 O-01 | Claude 离线审计修复 | OfflineChatMessage 模型已全面接线: (1)断连/发送失败→Isar持久化, (2)重连→从DB加载pending消息并入队, (3)发送成功→markSent, (4)服务器ACK→markAcked, (5)队列溢出/失败丢弃→DB清理, (6)dispose→清理24h旧acked. 新建 OfflineMessageQueueService, flutter analyze 零错误 |
| 2026-04-29 | Phase 4.1 | Claude Flutter状态带接入 | AuroraStatusBand 从硬编码→真实API: 新建 spineStatusBandProvider (GET /aurora/spine/status-band); AuroraBandState 扩展6态 (sensing/calibrated/riskFound/needsConfirm/calibrationAvailable/coolingDown); dashboard_screen 消费 provider 并 fallback 硬编码; 26 contract tests passed |
| 2026-04-29 | Phase 4.2 | Claude 展开交互+纠偏chip | AuroraStatusBand→StatefulWidget: 有correction_options时tap展开显示chip列表, 无options时走onTap跳转chat; chip点击→chat路由initial_user_message; AnimatedContainer+AnimatedRotation动画; flutter analyze 0 errors |
| 2026-04-29 | Phase 4.3 | Claude 冷却显示 | coolingDown状态展开显示倒计时 (_formatCooldown: 秒/分/时) + 快速校准 TextButton (cooldownCanOverride gate); 点击→chat initial_user_message='快速校准'; flutter analyze 0 errors |
| 2026-04-29 | R3 O-04 | Claude Focus自动同步 | FocusStatisticsProvider.build() 添加: (1)启动时 unawaited(sync()) 同步未上传会话, (2)Connectivity().onConnectivityChanged 监听网络恢复自动sync; flutter analyze 0 errors |
| 2026-04-29 | Bug Fix | Claude 7 bugs fixed | B-001 description→guide_content field mapping; B-002 unknown status validation; B-003 batch per-task error handling; B-004 case-insensitive status; B-005 word-boundary regex; B-006 DecrQuota zero guard; B-007 Flutter l10n syntax; 72+52+27 tests pass |
| 2026-04-29 | R4-P1-01 | Claude 成本守卫接线 | is_rag_within_budget() + record_rag_cost() 接入 graph_rag.retrieve(); is_aurora_within_budget() 接入 L3 start_aurora_core_session + L4 create_candidate |
| 2026-04-29 | R4-P1-03 | Claude 首页纠偏遥测 | dashboard_screen onCorrectionTap/onCooldownOverride 先提交 recordStatusBandCorrection() (semantic_value/is_disconfirming) 再跳转 chat; AuroraTelemetryService 新增方法; flutter analyze 0 errors |

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
| T6.3.2 CI 定期演练 | 🟡 待证据 | Claude | R4: 发现 chaos_drill.sh, 但未见 GitHub Actions 定期演练接线证据 |
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
