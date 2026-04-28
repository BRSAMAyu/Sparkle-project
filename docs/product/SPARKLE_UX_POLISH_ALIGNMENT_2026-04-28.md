# SPARKLE 全系统对齐文档 — UX深度打磨阶段交接

> **生成日期**: 2026-04-28  
> **分支**: `gpt_pro方案推进` (9 commits ahead of origin)  
> **状态**: 愿景实现 100/100 (代码+文档+运维)，待UX深度打磨  
> **接收人**: Claude Code (UX深度打磨优化阶段)  
> **生成人**: GLM-5.1 (本轮架构师)

---

## 一、项目定位

**Sparkle (星火)** = AI-native 目标实现操作系统。不是聊天/RAG/计划生成器，是把用户目标、资料、行动、失败、反馈和社群持续编译成更好下一步的系统。

**北极星**: 零基础学生用 Sparkle 7天通过考试。

---

## 二、当前架构总览

```
┌─ Flutter Mobile ──────────────────────────────────────────────────┐
│  39 feature modules | 1,064 .dart files | 207 test files          │
│  Riverpod + GoRouter + Multi-sensory UX                           │
├─ Go Gateway (:8080) ──────────────────────────────────────────────┤
│  16 middleware: Auth(JWT+黑名单), Rate Limit, CORS, Security      │
│  WebSocket hub + gRPC proxy                                       │
├─ Python Engine (:8000 REST, :50051 gRPC) ────────────────────────┤
│  Signal-to-Action Spine (8层59文件) | Aurora Adaptive Kernel      │
│  LangGraph FSM | FastAPI | 334 service files                     │
├─ Data Layer ──────────────────────────────────────────────────────┤
│  PostgreSQL 16 (143 tables, pgvector, Apache AGE)                 │
│  Redis Stack (cache, event bus, rate limit)                       │
│  MinIO (object storage)                                           │
├─ Monitoring ──────────────────────────────────────────────────────┤
│  Prometheus + Grafana + Loki + Tempo + Alertmanager               │
└───────────────────────────────────────────────────────────────────┘
```

---

## 三、Signal-to-Action Spine (8层架构) — 当前状态

### 架构定义
- **蓝图**: `docs/product/SPARKLE_CAUSAL_CONTROL_OS_FINAL_2026-04-27.md`
- **进度**: `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_PROGRESS_2026-04-27.md`
- **工作日志**: `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_WORK_LOG_2026-04-27.md`
- **P2/P3/P4简报**: `docs/product/SPARKLE_P2P3P4_ARCHITECT_BRIEF_2026-04-27.md`

### 8层实现文件

| 层 | 组件 | 文件 | 测试覆盖 |
|----|------|------|---------|
| L1 RawEvent | 入口方法 | `app/signals/spine_orchestrator.py:134` (on_task_completed), `:1485` (on_user_return) | ✅ |
| L2 ActionableSignal | 信号+8探测器 | `app/signals/types.py:31` + 6个detector文件 | ✅ |
| L3 SignalRanking | 10维评分 | `app/signals/signal_ranker.py` | `test_layers.py` |
| L4 StateRegister | Redis持久化 | `app/signals/state_register.py` | `test_layers.py` |
| L5 PolicyArbitration | 11个state_key | `app/signals/policy_engine.py` | `test_policy_engine.py` |
| L6 Directives | 9类Directive | `app/signals/types.py` (9个dataclass) | `test_layers.py` |
| L7 Actuation | 执行+审计 | `app/signals/directive_applier.py` | ✅ |
| L8 Outcome | 归因+自纠 | `app/signals/outcome_recorder.py` | `test_outcome_attribution.py` |

### 测试文件 (19个, 1024 tests)
```
tests/unit/spine/
├── conftest.py                      ← FakeRedis + shared fixtures
├── test_types_and_detectors.py
├── test_p0_features.py
├── test_p1_features.py
├── test_policy_engine.py
├── test_pipeline_integration.py
├── test_layers.py
├── test_metrics.py
├── test_production_wiring.py
├── test_notification.py
├── test_v2_v3_features.py
├── test_production_directives.py
├── test_advanced_features.py
├── test_research_and_bridge.py
├── test_specialized_features.py
├── test_vision_gap_and_audit.py
├── test_audit_and_vision.py
├── test_spine_metrics.py
└── test_e2e_pipeline.py            ← 12 E2E集成测试
```

---

## 四、6个神性时刻 — 完整实现状态

### 定义
- **愿景**: `docs/product/SPARKLE_FULL_VISION_v1_2026-04-27.md`
- **10铁律**: `docs/product/SPARKLE_CAUSAL_CONTROL_OS_FINAL_2026-04-27.md`

### 每个时刻的完整文件映射

#### 1. 看见坚持 (Seeing Persistence)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端信号 | `app/signals/achievement_reinforcement.py` | 198行 |
| 后端增长卡片事件 | `mobile/.../chat_stream_events.dart:1777` | GrowthCardEvent |
| Flutter卡片 | `mobile/.../widgets/growth_card.dart` | chat_screen.dart:1376 |
| Flutter庆祝 | `mobile/.../widgets/sparkle_confetti.dart` | 163行 |
| Chat集成 | `chat_screen.dart:1376-1401` | GrowthCard widget |
| 状态管理 | `chat_state.dart:232` | pendingGrowthCard |
| Dismiss | `chat_notifier_actions.dart` | dismissGrowthCard() |
| **UX问题** | ⚠️ P1: 庆祝动画不感知专注模式 | 需查FocusSession状态 |

#### 2. 承认误判 (Admitting Misjudgment)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端归因 | `app/signals/outcome_recorder.py:66-76` | harmful/needs_confirmation |
| 后端receipt构建 | `app/signals/outcome_recorder.py:439-497` | build_self_correction_receipt |
| 后端自纠逻辑 | `app/signals/spine_orchestrator.py:3100+` | on_user_receipt_correction |
| SpineReceipt事件 | `mobile/.../chat_stream_events.dart:1752` | SpineReceiptEvent |
| Flutter卡片 | `mobile/.../widgets/spine_receipt_card.dart` | 233行 |
| Chat集成 | `chat_screen.dart:1288-1306` | SpineReceiptCard |
| CausalTimeline | `mobile/.../widgets/causal_timeline_panel.dart` | 617行 |
| 状态管理 | `chat_state.dart:222` | pendingSpineReceipt |
| **已修复UX** | ✅ 语气改为"抱歉，我之前判断有误" | 原为"Aurora 调整了判断" |
| **已修复UX** | ✅ 修正按钮tap target 44pt | 原vertical padding 7→14 |
| **UX问题** | ⚠️ P1: 用户无法自由输入修正原因 | 只有预定义选项 |

#### 3. 知道不用资料 (Knowing Unused Data)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端源信任 | `app/signals/source_tray_integration.py` | 476行 |
| 后端receipt构建 | `source_tray_integration.py:139-193` | build_source_receipt |
| 后端用户纠正 | `source_tray_integration.py:414-450` | record_user_correction |
| 后端阻断列表 | `source_tray_integration.py:452-461` | is_source_blocked/get_blocked_sources |
| Flutter receipt bar | `mobile/.../widgets/context_receipt_bar.dart` | 325行 |
| Chat集成 | `chat_bubble.dart:1132-1137` | ContextReceiptBar |
| **UX问题** | ⚠️ P2: receipt chip alpha 0.6 可能不够醒目 | 需增大到0.85 |
| **UX问题** | ⚠️ P2: 排除资料无解释原因 | 需添加reason字段 |

#### 4. 记得时间 (Remembering Time)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端阈值 | `app/signals/stale_state_guard.py:28` | _STALE_THRESHOLD_MIN=60 |
| 后端TimeContext | `stale_state_guard.py:33-43` | TimeContext dataclass |
| 后端RecoveryCard | `stale_state_guard.py:195-248` | build_recovery_card |
| Flutter卡片 | `mobile/.../widgets/stale_recovery_card.dart` | 213行 |
| Chat集成 | `chat_screen.dart:1268-1286` | StaleRecoveryCard |
| 状态管理 | `chat_state.dart:219` | pendingStaleCard |
| **已修复UX** | ✅ 天级别时间显示 | ≥1440分钟显示"X天Y小时" |
| **UX问题** | ⚠️ P0: 缺少"我先休息一下"选项 | 需产品确认后添加 |
| **UX问题** | ⚠️ P1: 60分钟阈值可能太长 | 短任务场景20分钟更适合 |

#### 5. 阻止低收益 (Blocking Low Value)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端疲劳检测 | `app/services/notification_service.py:189-204` | fatigue protection |
| 后端疲劳状态 | `app/signals/spine_orchestrator.py:3571-3626` | check_fatigue() |
| UXWarning事件 | `mobile/.../chat_stream_events.dart:1700` | UXWarningEvent |
| Flutter卡片 | `mobile/.../widgets/strategy_intervention_card.dart` | 230行 |
| Chat集成 | `chat_screen.dart:1331-1350` | StrategyInterventionCard |
| 状态管理 | `chat_state.dart:228` | pendingUXWarning |
| **已修复UX** | ✅ "暂时忽略"替代"知道了" | 减少用户忽略倾向 |
| **UX问题** | ⚠️ P0: 无"30分钟后再提醒"延迟选项 | 需后端snooze支持 |
| **UX问题** | ⚠️ P1: 无undo（dismiss后不可恢复） | 需snackbar undo |

#### 6. 社群经验→策略 (Community → Strategy)
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端社群桥 | `app/services/community_signal_bridge.py` | 229行 |
| CommunityDirective | `app/signals/types.py:697-723` | CommunityDirective |
| CommunityHint事件 | `mobile/.../chat_stream_events.dart:1726` | CommunityHintEvent |
| Flutter卡片 | `mobile/.../widgets/community_insight_card.dart` | 247行 |
| Chat集成 | `chat_screen.dart:1307-1330` | CommunityInsightCard |
| **已修复UX** | ✅ 长摘要截断 maxLines:3 | 防止卡片撑满屏幕 |
| **UX问题** | ⚠️ P1: "参考这个建议"action不明确 | 需添加副标题说明 |
| **UX问题** | ⚠️ P1: 匿名保证不够透明 | 需添加隐私说明 |

### Spine降级指示器
| 维度 | 文件 | 位置 |
|------|------|------|
| 后端事件 | `mobile/.../chat_stream_events.dart:1844` | SpineDegradedEvent |
| 状态管理 | `chat_provider.dart:1764` | spineDegraded=true |
| Flutter UI | `chat_screen.dart:1352-1374` | Chip "智能调节暂不可用" |
| **状态**: ✅ 已实现 | 非侵入式Chip | 不需要修复 |

---

## 五、Aurora 自适应内核 — 当前状态

### 路线图文档
- **v2.1修正**: `docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md`
- **v2.2锁定**: `docs/product/SPARKLE_AURORA_ROADMAP_v2_2_FINAL_LOCK_2026-04-21.md`
- **对齐**: `docs/product/SPARKLE_AURORA_ALIGNMENT_2026-04-26.md`
- **Phase I Exit**: `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- **Runtime V1 Spec**: `docs/product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md`
- **用户模型**: `docs/product/SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`

### Stage完成状态

| Stage | 状态 | 关键文件 | Handoff文档 |
|-------|------|---------|------------|
| 4-8 双核路由 | ✅ | `dual_core_router.py` (713行) | `STAGE4-8_HANDOFF` |
| 9-10 Chat Profile | ✅ | Rubric + LLM Judge | `STAGE9-10_HANDOFF` |
| 11 Evidence | ✅ | Judge config | `STAGE11_HANDOFF` |
| 12 Foundation | ✅ | Bayesian + strategy_store | `STAGE12_HANDOFF` |
| 16-17 Memory/Social | ✅ | Memory write + Social bridge | `STAGE16-17_HANDOFF` |
| 18-19 State Aggregator | ✅ | 19个 `_build_*` 方法 | `STAGE18-19_HANDOFF` |
| 20-21 Skill System | ✅ | skill_lifecycle.py | `STAGE20-21_HANDOFF` |
| 22 Baseline Repair | ✅ | 18 telemetry fields | `STAGE22_HANDOFF` |
| 33-40 (Stage33+) | ✅ | Social/SRL/WM gates | `STAGE33-40_HANDOFF` |

### Aurora关键服务

| 服务 | 文件 | 功能 |
|------|------|------|
| State Aggregator | `app/state_aggregator/service.py` (1058行) | 19个_build_*方法填充21字段UserStateV1 |
| Context Builder | `app/orchestration/context_builder.py` | cognitive_context.model_dump()含全部字段 |
| Prompt Assembly | `app/orchestration/prompts.py` | 18 tracked_fields, feature-gated rendering |
| Dual Core Router | `app/orchestration/dual_core_router.py` (713行) | Execution vs Cognitive routing |
| Kill Switch | `app/core/kill_switch.py` | tri-state (off/shadow/live) |
| Privacy | `app/aurora/privacy.py` | PII redaction |

---

## 六、P0审计修复 — 当前状态

| ID | 问题 | 修复文件 | 状态 |
|----|------|---------|------|
| GOV-012 | memory controls未强制执行 | `app/api/v1/memory_settings.py:17-20` | ✅ commit 61fd6186 |
| GOV-016 | force_receipt缺失 | `app/signals/policy_engine.py` | ✅ commit 61fd6186 |
| STAB-006 | interaction counter | `app/signals/spine_orchestrator.py:1222-1229` | ✅ commit 85bfc1fc |
| STAB-004 | ReturnCaseFile | `app/signals/spine_orchestrator.py` | ✅ commit 85bfc1fc |
| STAB-012 | Spine degraded indicator | `chat_screen.dart:1352-1374` | ✅ 已实现 |
| SRC-014 | Source trust correction | `source_tray_integration.py:414-461` | ✅ commit 4eb95e40 |
| GOV-006 | Data deletion + age gate | `compliance/age_gate.py` | ✅ commit f135dffa |
| APP-005 | CRDT mastery merge | `galaxy/crdt_persistence.py` | ✅ commit f135dffa |
| P4-RES-005 | Consent tracking | `research_mode.py` | ✅ commit 4eb95e40 |
| NUDGE-007 | Backoff logic | notification_service | ✅ commit b56fb619 |

---

## 七、数据利用链路 — 当前状态

### 修正后评估 (原报告过时)

| 层 | 原报告 | 实际 | 证据 |
|----|--------|------|------|
| 采集 | 95% | 100% | StateAggregator 19个_build_*方法 |
| 聚合→Context | 75% | ~90% | `context_builder.py:747` model_dump() |
| Context→Prompt | 40-50% | ~60% | prompts.py 18 tracked_fields |
| Prompt→AI | 20% | ~40% | section_weights可关闭但默认开 |

### 关键链路验证
- **Memory Write**: `_write_turn_end_episodic_memory` 4个调用点 (orchestrator:1225,1444,3400,3476)
- **Achievement→AI**: achievement_summary在prompts.py:3296渲染
- **Calendar→AI**: calendar_context在prompts.py:3412渲染为【时间约束】
- **Error→Replan**: ErrorReplanBridge 13种触发类型 (error_replan_bridge.py:83-97)

---

## 八、UX审查发现 — 待深度打磨项

### UX审查来源
3个独立agent并行审查，覆盖：Chat交互轨迹、边缘情况韧性、神性时刻体验质量

### P0 — 必须修复 (5项)

| # | 问题 | 文件 | 描述 |
|---|------|------|------|
| UX-P0-1 | 缺少"我先休息"选项 | `stale_recovery_card.dart` | 恢复卡片只有4个选项，缺少"休息" |
| UX-P0-2 | 策略干预无延迟提醒 | `strategy_intervention_card.dart` | 只有"调整"和"忽略"，无"稍后提醒" |
| UX-P0-3 | 修正按钮无反馈 | `spine_receipt_card.dart` | 点击修正chip后无immediate feedback |
| UX-P0-4 | 长消息无展开 | `chat_bubble.dart:1044` | >500字截断无"展开全文" |
| UX-P0-5 | 发送失败无重试 | `chat_screen.dart:2074` | 发送失败消息消失无inline retry |

### P1 — 应当修复 (10项)

| # | 问题 | 文件 | 描述 |
|---|------|------|------|
| UX-P1-1 | 庆祝不感知专注模式 | `sparkle_confetti.dart` | 专注模式中庆祝不恰当 |
| UX-P1-2 | 自修正receipt时机太早 | `outcome_recorder.py` | attribution出现立即发receipt |
| UX-P1-3 | 60分钟stale阈值太刚性 | `stale_state_guard.py:28` | 短任务场景不适用 |
| UX-P1-4 | WebSocket连接无加载指示 | `websocket_chat_service_v2.dart` | 用户不知连接中 |
| UX-P1-5 | 社群洞察action不明确 | `community_insight_card.dart` | "参考这个建议"不够具体 |
| UX-P1-6 | 策略干预dismiss无undo | `chat_screen.dart:1347` | dismiss后不可恢复 |
| UX-P1-7 | 社群洞察匿名不透明 | `community_insight_card.dart` | 无隐私说明 |
| UX-P1-8 | 部分响应丢失 | `websocket_chat_service_v2.dart` | WebSocket断连时进行中响应丢失 |
| UX-P1-9 | 发送时TextField仍可编辑 | `chat_input.dart:180` | 发送中应禁用 |
| UX-P1-10 | receipt打字时被遮挡 | `chat_screen.dart:1288` | receipt在键盘后面用户看不到 |

### P2 — 可选修复 (8项)

| # | 问题 | 文件 | 描述 |
|---|------|------|------|
| UX-P2-1 | receipt chip不够醒目 | `context_receipt_bar.dart:84` | alpha 0.6太低 |
| UX-P2-2 | 粒子数不一致 | `sparkle_confetti.dart` | 卡片与对话框粒子数不匹配 |
| UX-P2-3 | 卡片动画太短 | 所有card widgets | 340-380ms偏快 |
| UX-P2-4 | 排除资料无原因 | `context_receipt_bar.dart` | 只显示名字不显示reason |
| UX-P2-5 | 社群洞察dismiss无反馈 | `community_insight_card.dart` | 无改进算法反馈 |
| UX-P2-6 | 空状态缺原因 | `empty_state.dart` | 不解释为什么空 |
| UX-P2-7 | 权限dialog无"以后再说" | `app_permission_dialog.dart` | 只有取消和设置 |
| UX-P2-8 | 分享卡片fallback太简 | `universal_share_bottom_sheet.dart` | 失败时预览太简单 |

---

## 九、Flutter卡片集成模式 (给UX打磨agent参考)

### 事件→状态→UI完整链路

```
1. Backend发送metadata (response_metadata['spine_stale_card'])
2. WebSocket解析 → StaleRecoveryEvent (chat_stream_events.dart:1666)
3. Provider处理 → state.copyWith(pendingStaleCard: event) (chat_provider.dart:1740)
4. Chat Screen渲染 → if (chatState.pendingStaleCard != null) → StaleRecoveryCard (chat_screen.dart:1268)
5. 用户交互 → onOptionSelected → dismissStaleCard() + sendMessage(option)
```

### 所有已集成卡片一览

| 卡片Widget | 事件类 | 状态字段 | chat_screen行 | Dismiss方法 |
|-----------|--------|---------|-------------|------------|
| StaleRecoveryCard | StaleRecoveryEvent | pendingStaleCard | 1268-1286 | dismissStaleCard |
| SpineReceiptCard | SpineReceiptEvent | pendingSpineReceipt | 1288-1306 | dismissSpineReceipt |
| CommunityInsightCard | CommunityHintEvent | pendingCommunityHint | 1307-1330 | dismissCommunityHint |
| StrategyInterventionCard | UXWarningEvent | pendingUXWarning | 1331-1350 | dismissUXWarning |
| GrowthCard | GrowthCardEvent | pendingGrowthCard | 1376-1401 | dismissGrowthCard |
| Chip (degraded) | SpineDegradedEvent | spineDegraded | 1352-1374 | 自动恢复 |
| CausalTimelinePanel | (独立按钮触发) | - | 独立panel | 关闭面板 |

### 动画模式 (所有卡片一致)
```dart
AnimationController(duration: Duration(milliseconds: 340-380))
_fadeAnim = CurvedAnimation(curve: Curves.easeOut)
_slideAnim = Tween<Offset>(begin: Offset(0, 0.06), end: Offset.zero)
  .animate(CurvedAnimation(curve: Curves.easeOutCubic))
```

### 设计系统引用
- 颜色: `DS.surfaceHigh`, `DS.warning`, `DS.info`, `DS.error`, `DS.success`, `DS.textPrimary/Secondary/Tertiary`
- 字体: `DS.labelSmall`, `DS.bodySmall`
- 圆角: `BorderRadius.circular(14)`
- 间距: `EdgeInsets.symmetric(horizontal: 12, vertical: 6)`

---

## 十、全部关键文档索引

### 产品愿景与蓝图
| 文档 | 路径 | 描述 |
|------|------|------|
| 愿景 v1 | `docs/product/SPARKLE_FULL_VISION_v1_2026-04-27.md` | 终局定义+6神性时刻+长期扩展 |
| 因果控制OS | `docs/product/SPARKLE_CAUSAL_CONTROL_OS_FINAL_2026-04-27.md` | 8层+9Directive+10铁律+P0任务书 |
| 产品共识 | `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` | 短期AI教练→长期成长OS |
| 对齐文档 | `docs/product/SPARKLE_ALIGNMENT_2026-04-25.md` | 北极星+Milestone A-D+4个gap |
| 深度审计 | `docs/product/SPARKLE_DEEP_AUDIT_2026-04-27.md` | 200+项全面审查 |
| 项目交接 | `docs/product/SPARKLE_PROJECT_ALIGNMENT_HANDOFF_2026-04-24.md` | 多agent交接 |

### Aurora路线图 (Stages 4-40)
| 文档 | 路径 |
|------|------|
| v2.1修正 | `docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md` |
| v2.2最终锁定 | `docs/product/SPARKLE_AURORA_ROADMAP_v2_2_FINAL_LOCK_2026-04-21.md` |
| Aurora对齐 | `docs/product/SPARKLE_AURORA_ALIGNMENT_2026-04-26.md` |
| Phase I Exit | `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md` |
| Runtime V1 | `docs/product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md` |
| Stage 4-40 Handoff | `docs/product/SPARKLE_AURORA_STAGE{N}_HANDOFF_*.md` (每个Stage一个) |

### Signal Spine
| 文档 | 路径 |
|------|------|
| Spine设计 | `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_2026-04-27.md` |
| Spine进度 | `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_PROGRESS_2026-04-27.md` |
| P2/P3/P4简报 | `docs/product/SPARKLE_P2P3P4_ARCHITECT_BRIEF_2026-04-27.md` |
| Codex Dispatch | `docs/product/SPARKLE_CODEX_DISPATCH_MASTER_2026-04-27.md` |

### 数据利用与闭环
| 文档 | 路径 |
|------|------|
| 数据利用分析 | `docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md` |
| 高级概念集成 | `docs/product/SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md` |
| 闭环计划 | `docs/product/SPARKLE_CLOSED_LOOPS_PLAN_v1.1_2026-04-27.md` |
| 增长系统路线图 | `docs/product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md` |
| v2.1统一因果运行时 | `docs/product/SPARKLE_V2_1_UNIFIED_CAUSAL_RUNTIME_2026-04-27.md` |
| v2体验路线图 | `docs/product/SPARKLE_V2_LIVING_EXPERIENCE_ROADMAP_2026-04-27.md` |

### 工程标准
| 文档 | 路径 |
|------|------|
| 测试方法论 | `docs/engineering/test_methodology.md` |
| 质量护栏 | `docs/engineering/quality_guardrails.md` |
| Flutter质量门 | `docs/engineering/flutter_quality_gate.md` |
| 移动架构治理 | `docs/engineering/MOBILE_ARCHITECTURE_GOVERNANCE.md` |
| 完成定义 | `docs/engineering/definition_of_done_industrial.md` |
| i18n指南 | `docs/engineering/i18n_guidelines.md` |
| Proto规范 | `docs/engineering/proto_change_adr_template.md` |

### 部署与运维
| 文档 | 路径 |
|------|------|
| 生产部署指南 | `docs/05_部署与运维/production_deployment_guide.md` |
| 阿里云部署 | `backend/docs/ALIYUN_DEPLOYMENT_GUIDE.md` |
| 环境配置 | `backend/EXECUTION_GUIDE.md` |
| Docker修复 | (memory) `docker_infrastructure_fixes.md` |
| 事件跑书 | `monitoring/runbooks/incident_response.md` |

### 质量基线
| 文件 | 路径 |
|------|------|
| 性能基线 | `quality/performance_baselines.json` |
| 技术债预算 | `quality/tech_debt_budget.json` |
| 覆盖率阈值 | `quality/coverage_thresholds.json` |
| 基线快照 | `quality/baseline_snapshot.json` |

### 治理规则
| 文件 | 路径 |
|------|------|
| 规则清单 | `scripts/rule_guard_manifest.tsv` (61条) |
| Guard脚本 | `scripts/guards/check_rule_*.py` (17个) |
| 全量运行 | `scripts/run_all_rule_guards.sh` |

---

## 十一、Memory文件索引

位置: `.claude/projects/-Users-brsama-code-GitHub-Sparkle-project/memory/`

### 核心记忆
- `MEMORY.md` — 总索引 (232行)
- `vision_audit_corrected_2026-04-28.md` — 本次修正后的审计结果
- `vision_audit_2026-04-27.md` — 上次审计 (含veto C1-C10)

### 产品路线
- `roadmap.md` — 原始路线图
- `roadmap_v2_stage16_23.md` — Aurora Stage 16-23
- `advanced_concepts_roadmap.md` — 高级概念集成
- `codex_dispatch_v2.md` — 并行Codex dispatch

### 反馈规则 (11个)
- `feedback_code_modifications.md` — 主agent亲自写代码
- `feedback_role_boundary.md` — 架构师不实现
- `feedback_work_delegation.md` — 小scope直接编辑
- `feedback_i18n_strategy.md` — 双语策略
- `feedback_self_review_protocol.md` — 5步自审
- `feedback_independent_audit.md` — 独立验证
- `feedback_audit_process.md` — 审计流程
- `feedback_dual_review.md` — 双重审查
- `feedback_role_division.md` — GLM审查/Codex执行
- `feedback_no_lock_files.md` — 不碰锁文件
- `workflow_engineering_rules.md` — 多agent工程规则

---

## 十二、Git提交历史 (本次session)

```
79672d74 fix(ux): P0 divine moment UX quality improvements
ae34663c docs: test methodology, production deployment guide, performance baselines
32a5c7d2 feat(spine): telemetry expansion, error bridge expansion, E2E integration tests
c489d7ae fix(spine): remove replay-induced duplicated code in SpineOrchestrator
f135dffa feat(spine): DataDeletionService, MasteryMergeCRDT, fatigue protection, plan revision
4eb95e40 feat(spine): P0-P4 feature implementations
85bfc1fc fix(spine): STAB-006 + STAB-004
61fd6186 fix(spine): GOV-012 + GOV-016 P0 audit fixes
b6c4d47f refactor(spine): split test_signal_spine.py into 18 modular files
```

加上之前的40+ commits (P0-P12实现, v2.1-v3.1特性等)，总计约90+ commits on branch。

---

## 十三、UX深度打磨阶段 — 工作范围

### 目标
从"功能完整"(100/100愿景) 推进到"体验完美"(每个交互细节打磨)。

### 工作原则
1. **每阶段提交** — 改一个文件就commit
2. **自我审查** — 改完运行测试确认无回归
3. **独立验证** — 派agent审查每个改动
4. **不碰后端** — 本阶段仅打磨Flutter UX，后端已100%完成
5. **25分钟提醒** — 每轮检查工作流

### 优先级排序
1. P0 (5项) — 必须修复
2. P1 (10项) — 应当修复
3. P2 (8项) — 可选优化
4. 交互动画打磨 — 所有卡片animation统一到500ms
5. 触觉反馈统一 — SensoryFeedbackEvent映射审查
6. 无障碍审查 — Semantics, tap target 44pt, color contrast

### 需产品确认的决策
1. StaleRecoveryCard是否添加"我先休息一下"选项？
2. StrategyInterventionCard是否添加"30分钟后再提醒"？(需后端snooze)
3. 庆祝动画在专注模式是否静音？
4. 自修正receipt延迟30秒出现是否合适？

---

## 十四、关键代码文件快速参考

### Flutter Widgets (UX打磨核心目标)
```
mobile/lib/features/chat/presentation/widgets/
├── spine_receipt_card.dart          # 神性时刻#2 承认误判
├── strategy_intervention_card.dart  # 神性时刻#5 阻止低收益
├── community_insight_card.dart      # 神性时刻#6 社群洞察
├── stale_recovery_card.dart         # 神性时刻#4 记得时间
├── context_receipt_bar.dart         # 神性时刻#3 知道不用资料
├── causal_timeline_panel.dart       # 因果时间线
├── growth_card.dart                 # 神性时刻#1 看见坚持 (卡片)
├── chat_bubble.dart                 # 消息气泡
├── chat_input.dart                  # 消息输入
└── sparkle_confetti.dart            # 庆祝动画

mobile/lib/features/chat/presentation/screens/
└── chat_screen.dart                 # 主聊天屏幕 (所有卡片集成处)

mobile/lib/features/chat/presentation/providers/
├── chat_provider.dart               # 事件分发
├── chat_state.dart                  # 状态定义
└── chat_notifier_actions.dart       # dismiss方法

mobile/lib/features/chat/data/models/
└── chat_stream_events.dart          # 所有事件类定义

mobile/lib/core/design/
└── design_system.dart               # DS tokens

mobile/lib/core/services/
└── sensory_feedback_service.dart    # 触觉反馈

mobile/lib/core/design/widgets/
├── error_widget.dart                # 错误展示
├── loading_indicator.dart           # 加载状态
├── empty_state.dart                 # 空状态
├── app_permission_dialog.dart       # 权限弹窗
└── universal_share_bottom_sheet.dart # 分享
```

### 后端 (只读参考，不修改)
```
app/signals/spine_orchestrator.py    # 主编排器
app/signals/policy_engine.py         # 策略引擎
app/signals/outcome_recorder.py      # 归因+自纠
app/signals/stale_state_guard.py     # 时间守卫
app/signals/source_tray_integration.py # 源信任
app/signals/achievement_reinforcement.py # 成就强化
app/signals/research_mode.py         # 同意追踪
app/services/notification_service.py # 疲劳保护
app/services/community_signal_bridge.py # 社群桥
app/services/compliance/age_gate.py  # 数据删除
app/services/galaxy/crdt_persistence.py # CRDT
```

---

**文档结束。接手agent请先读CLAUDE.md，再读本对齐文档，然后开始UX打磨。**
