# Sparkle Aurora 深度质量审计 — 综合验收报告

**日期**: 2026-05-02
**审计范围**: Aurora 体验质量 / 成长环路 / 跨会话状态 / 生产稳定性 / Flutter UX
**方法**: 5 个 Opus Agent 并行审查 → 架构师定向验证 → 综合判断
**详细报告**: `docs/product/quality_audit_agents/` 目录下 5 份完整报告

---

## 总体评级矩阵

| 维度 | 报告 | 评级 | 一句话 |
|------|------|------|--------|
| Aurora 体验质量 | [01_aurora_experience_quality.md](quality_audit_agents/01_aurora_experience_quality.md) | **GOOD** | 语言原则 EXCELLENT，校准收据自然，但模板变化度偏低 |
| 成长环路 + 双核路由 | [02_growth_loop_dual_core.md](quality_audit_agents/02_growth_loop_dual_core.md) | **EXCELLENT** | 感知层 19 维度 + 指数衰减，路由多信号评分有实际意义 |
| 跨会话状态 | [03_cross_session_state.md](quality_audit_agents/03_cross_session_state.md) | **GOOD** | 回归体验 EXCELLENT，但 Aurora 状态仅 Redis 无持久化备份 |
| 生产稳定性 | [04_production_stability.md](quality_audit_agents/04_production_stability.md) | **GOOD** | 7 项全部 GOOD，gRPC 重试 + 熔断器 + 三级上下文裁剪 |
| Flutter UX | [05_flutter_ux.md](quality_audit_agents/05_flutter_ux.md) | **GOOD→EXCELLENT** | Chat 屏幕状态覆盖极好，可访问性和设计系统合规是短板 |

**系统整体: GOOD+** — 功能完整度和工程健壮性远超同类产品基线，但在无障碍访问和监控精细度上有明确改进空间。

---

## 已验证的真实发现（按优先级排列）

### P1 — 发布前应修复

**1. 可访问性 live regions 严重不足** ⚠️
- **验证**: 整个 chat feature 仅 2 处 `liveRegion: true`（offline_queue_indicator + daily_startup_banner）
- **影响**: Aurora 状态从 sensing→risk_found 转变时，屏幕阅读器用户**完全无感知**
- **位置**: `status_awareness_bar.dart`, `calibration_receipt_chip.dart`, `comeback_banner.dart`, error bar
- **建议**: 在 6 个关键状态变化点添加 `liveRegion: true`

**2. 监控缺失：校准环路 + 熔断器无告警** ⚠️
- **验证**: 全部 monitoring YAML 文件中无 `aurora_correction`、`calibration_receipt`、`circuit_breaker` 相关规则
- **现有**: 11 条 SLO 告警覆盖基础设施，但 Aurora 特有的用户侧故障（校准失败、状态卡死）无监控
- **建议**: 添加 `SparkleAuroraCorrectionLoopStuck`（连续失败 >5 次/10min）和 `SparkleCircuitBreakerOpen` 告警

### P2 — 近期应修复

**3. CalibrationReceiptChip 关闭状态不持久**
- `_dismissed` 是本地 state，widget 重建后收据重新出现
- 位置: `calibration_receipt_chip.dart`
- 建议: 用 provider 或 SharedPreferences 持久化关闭状态

**4. Status bar chip minHeight 32dp**
- `_StatusCorrectionChip` 和 `_PredictedOptionChip` 在 `status_awareness_bar.dart` 中 minHeight 为 32dp
- 同文件的 `_CorrectionChip`（contextual_correction_bar.dart）已正确使用 44dp
- 应统一为 44dp 满足 Apple HIG

**5. AuroraReceiptChip 无关闭机制**
- 与 CalibrationReceiptChip 不一致，用户无法关闭 aurora 收据
- 位置: `aurora_receipt_chip.dart`

**6. Home 模块 23 处 Colors.white 硬编码**
- **验证**: 25 处跨 9 文件（含粒子/天气效果中合理使用的）
- 核心违规: `exam_sprint_dashboard_card.dart`（9 处）、`openclaw_automation_panel.dart`（2 处）
- Chat 模块已 100% 合规

**7. 限流器 Redis 不可用时硬拒绝**
- `DistributedRateLimiter` Redis 失败时返回 `(false, 0, err)`，无本地降级
- 基础设施存在 `HybridRateLimitMiddlewareSimple`，但主路径未接入

**8. Aurora 状态仅 Redis 持久化**
- 核心会话状态 30min TTL，Redis 宕机 = 状态丢失
- 无磁盘备份，无 PostgreSQL fallback

### P3 — 持续改进

**9.** Flutter Provider 无 bg→fg 刷新 — 从后台切回时状态可能过期
**10.** 记忆系统无矛盾自动检测 — 长期使用后可能出现自相矛盾的记忆条目
**11.** Router `user_visible` 标志从未设为 True — 可能是死代码或有意设计
**12.** Chat screen error bar 可能闪烁 — dismiss 后底层错误仍在会立即重现
**13.** 限流器会话锁获取失败直接拒绝 — 无队列/重试，用户需手动重发
**14.** Aurora core session sheet 3 处 Colors.white — 应使用 `DS.textOnPrimary`

---

## 误报纠正（Agent 发现经我验证后修正）

| Agent 发现 | 我的验证 | 修正 |
|-----------|---------|------|
| "Correction chip minHeight 32dp" | `contextual_correction_bar.dart` 的 `_CorrectionChip` 实际是 **44dp** | 仅 `status_awareness_bar.dart` 的 chip 是 32dp，影响范围缩小 |
| "Semantics 覆盖率仅 8%" | chat 模块有 **39 处** `Semantics()` 调用，核心 widget 覆盖完整 | 原始计算方法有误（分子分母不对等），实际核心组件覆盖 GOOD |
| "Router prompt impact 用户不可见" | `user_visible` 标志确实未启用，但可能是故意的 MVP 设计 | 不一定是 bug，标记为待确认 |

---

## 亮点（值得保持的设计决策）

1. **三级上下文裁剪**（≤10 全量 / ≤30 规则 / >30 LLM 摘要）— 优雅地解决了长会话内存问题
2. **回归体验四档位**（silent_resume / light_resume / personalized_return / checkpoint_debrief）— 远超竞品
3. **LLM 多层 fallback**（3 次尝试 + 指数退避 + 跨模型降级）— 生产级容错
4. **分布式会话锁**（Redis lock + 10s 续期）— 正确防止并发状态损坏
5. **Chat screen 状态覆盖**（离线队列 / 回归 banner / 校正入口 / 错误栏）— 几乎没有状态遗漏
6. **语言原则系统** — 7 条原则 + 5 条禁语 + prompt + 测试双重强制执行

---

## 行动项总结

| # | 优先级 | 工作量 | 行动 | 关键文件 |
|---|--------|--------|------|---------|
| 1 | P1 | S | 添加 6 处 `liveRegion: true` | `status_awareness_bar.dart`, `calibration_receipt_chip.dart`, `comeback_banner.dart`, `chat_screen.dart` |
| 2 | P1 | S | 添加 2 条 Prometheus 告警规则 | `monitoring/sparkle_slo_alerts.yml` 或新建 `sparkle_aurora_alerts.yml` |
| 3 | P2 | S | 持久化 CalibrationReceiptChip 关闭状态 | `calibration_receipt_chip.dart` |
| 4 | P2 | XS | chip minHeight 32→44dp（2 处） | `status_awareness_bar.dart` |
| 5 | P2 | S | AuroraReceiptChip 添加关闭按钮 | `aurora_receipt_chip.dart` |
| 6 | P2 | M | Home 模块 Colors.white → DS tokens | `exam_sprint_dashboard_card.dart`, `openclaw_automation_panel.dart` 等 7 文件 |
| 7 | P2 | M | 限流器接入本地降级路径 | `distributed_rate_limiter.go` |
| 8 | P2 | L | Aurora 状态 PostgreSQL 双写 | 新建 persistence 层 |
| 9-14 | P3 | — | 持续改进 backlog | — |

**P1 项预估总工作量: ~2-3 小时**
**P2 项预估总工作量: ~1-2 天**

---

## 详细报告索引

| 文件 | 内容 |
|------|------|
| [01_aurora_experience_quality.md](quality_audit_agents/01_aurora_experience_quality.md) | 记忆自然性、校准收据、校正闭环、语言原则、校正 chip UX |
| [02_growth_loop_dual_core.md](quality_audit_agents/02_growth_loop_dual_core.md) | 7 阶段成长环路、双核路由评分、路由→prompt 传播 |
| [03_cross_session_state.md](quality_audit_agents/03_cross_session_state.md) | 跨会话连续性、回归体验、Provider 状态、记忆质量 |
| [04_production_stability.md](quality_audit_agents/04_production_stability.md) | WS 重连、gRPC 容错、Redis 不可用、goroutine 泄漏、监控 |
| [05_flutter_ux.md](quality_audit_agents/05_flutter_ux.md) | 状态栏质量、收据系统、Chat 屏幕、可访问性、设计系统 |
