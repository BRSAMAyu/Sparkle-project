# Sparkle 完全体深度审计 — 愿景差距 · 稳定性风险 · 极端条件

> **审计类型**: 架构级全面审计
> **日期**: 2026-04-27
> **审计范围**: v2.0 全部 P1-P4 实现 (484/484 tests, 28 modules, 46 exports)
> **审计结论**: 逻辑层完整度 ~90%，但用户可感知层完整度 ~35%

---

## 一、最关键的架构问题：Aurora ↔ Spine 双系统割裂

**严重程度**: P0 — 这是整个完全体愿景的最大瓶颈

### 现状

```
                    ┌─────────────────┐
  用户消息 ──→      │  Orchestrator    │
                    │  (FSM 主控)      │
                    └───┬─────────┬───┘
                        │         │
            ┌───────────┘         └───────────┐
            ▼                                 ▼
  ┌──────────────────┐              ┌──────────────────┐
  │  Aurora Runtime  │              │  Signal Spine    │
  │  v1 (决策循环)    │              │  (因果控制)       │
  │                  │              │                  │
  │  DashboardReadout│              │  ActionableSignal│
  │  AuroraDecision  │              │  PolicyDecision  │
  │  ChatAdapter     │              │  9 Directives    │
  └──────────────────┘              └──────────────────┘
        ↕ 0 连接 ↕                        ↕ 0 连接 ↕
  Aurora 不知道 Spine 存在        Spine 不知道 Aurora 存在
```

**验证**:
- `backend/app/aurora/runtime_v1/decision_loop.py` (1768 行): **零个** `from app.signals` 导入
- 主 Orchestrator 只有 2 个 Spine 调用点 (line 2348, 2364)，仅限 `on_first_message` 和 `on_user_return`
- Aurora 的 `DashboardReadout` 不消费 `ActionableStatePacket`
- Spine 的 `PolicyDecision` 不影响 Aurora 的决策循环

**影响**: 用户感受到的是两个独立系统在各自运转，而不是"AI-native 目标实现操作系统"。这是愿景中"所有功能接到同一条 Causal Control Spine"的根本违背。

---

## 二、6 个神性时刻的用户可感知状态

| # | 神性时刻 | 逻辑完整 | API 端点 | 前端可消费 | 综合评级 |
|---|---------|---------|---------|----------|---------|
| 1 | 看见坚持 | ✅ GrowthChronicle | ❌ 无 API | ❌ 无 UI | **STUB** |
| 2 | 承认误判 | ✅ handle_user_receipt_action | ✅ POST /spine/receipt/action | ⚠️ 部分 | **LIVE** |
| 3 | 知道不用资料 | ✅ build_source_receipt | ❌ 未接入 chat | ❌ 无 UI | **STUB** |
| 4 | 记得时间 | ✅ build_recovery_card | ❌ 无 API | ❌ 无 UI | **STUB** |
| 5 | 阻止低收益 | ✅ _apply_quality_cross_check | N/A (内部) | N/A (内部) | **LIVE** |
| 6 | 社群经验转策略 | ✅ build_cohort_mistake_hint | ❌ 未接入 chat | ❌ 无 UI | **STUB** |

**结论**: 6 个神性时刻中，只有 2 个 (33%) 用户真正能感受到。其余 4 个逻辑存在但无用户界面。

---

## 三、12 个孤立模块（有代码无接入）

以下模块存在完整的逻辑和测试，但 **SpineOrchestrator 没有实例化或调用它们**：

| # | 模块 | 功能 | 为什么没接入 |
|---|------|------|------------|
| 1 | `policy_analytics.py` | 策略效果分析 | 纯分析，无消费者调用 |
| 2 | `policy_experiments.py` | A/B 影子实验 | 需要定时任务触发，无调度器 |
| 3 | `research_grade.py` (3合1) | 反事实/模拟器/市场 | 研究级工具，无生产调用 |
| 4 | `growth_chronicle.py` | 成长叙事 | 无 API 端点，无前端消费 |
| 5 | `relationship_model.py` | 用户-AI 关系 | 无消费者，trust_level 写了但没人读 |
| 6 | `skill_extraction.py` | 策略提取 | SkillExtractionService 未被 SpineOrchestrator 调用 |
| 7 | `source_tray_integration.py` | 资料桥接 | build_source_receipt 未被任何 pipeline 调用 |
| 8 | `external_integration.py` | 日历/工具信号 | CalendarSignalBridge 无生产事件源 |
| 9 | `goal_type_adapter.py` | 目标类型适配 | adapt_mastery_mapping 未被 planning 调用 |
| 10 | `learning_base.py` | 贝叶斯学习 | StrategyBelief 写了但没被任何决策路径消费 |
| 11 | `material_signal.py` | 资料利用率信号 | 检测器存在但未被 pipeline 触发 |
| 12 | `timeline_card_renderer.py` | 时间线卡片 | API 返回了 card 字段，但前端未渲染 |

**这 12 个模块占总模块数的 43%，代表约 3000+ 行"存在但未激活"的代码。**

---

## 四、长期稳定性风险（1 年以上使用）

### HIGH 风险

| # | 风险 | 模块 | 影响 |
|---|------|------|------|
| H1 | **SpineMetrics 计数器无限增长** | `spine_metrics.py` | Redis INCR 无上限，1 年后单用户计数器可达百万级。虽然数字大小不影响 Redis，但 `snapshot()` 的除法精度下降 |
| H2 | **growth_chronicle 全量加载** | `growth_chronicle.py` | `add_entry()` 每次加载用户全部 100 条记录再写回。高并发下内存和延迟问题 |
| H3 | **Orchestrator trace 内存累积** | `spine_orchestrator.py` | CausalTrace 对象的 list 字段通过 `.append()` 无限增长。单次 pipeline 中 trace 有 5+ 个 list 字段 |

### MEDIUM 风险

| # | 风险 | 模块 | 影响 |
|---|------|------|------|
| M1 | **关系模型计数器无重置** | `relationship_model.py` | `total_interactions` 永远递增，30 天 TTL 后重建但无历史衰减机制 |
| M2 | **Skill effective_count 无上限** | `skill_lifecycle.py` | 长期有效策略的 effective_count 会持续增长，threshold 检查不变但数值漂移 |
| M3 | **策略实验累积** | `policy_experiments.py` | 每用户最多 20 个实验，auto-conclude 后不删除，只标记状态 |
| M4 | **StateRegister 全量加载** | `state_register.py` | `get_active_states()` 一次性加载用户全部活跃状态到内存 |

### 长期退化场景

**场景 1: 老用户回归**
- 使用 6 个月后中断 3 个月 → 回归时 Redis TTL 已过期（30 天），所有 spine 状态丢失
- GrowthChronicle 丢失，用户看不到历史
- RelationshipModel 重置为默认，系统"忘记"了用户偏好
- **影响**: 用户体验断崖，从"懂我的 AI"变成"全新的 AI"

**场景 2: 高频用户**
- 每天完成 20 个任务，持续 1 年 → 7300 个 CausalTrace
- `_MAX_USER_TRACES=50` 只保留最近 50 个，历史因果链不可查
- PolicyEffectEntry 在 `_MAX_POLICY_EFFECTS=20` 下被截断
- **影响**: 策略学习窗口太短，长期模式无法被检测

**场景 3: 多目标用户**
- 同时准备考试 + 找工作 + 健身 → 3 个 goal_type 交叉
- 目前的 `goal_type_adapter.py` 只做单目标适配
- StateRegister 的 `state_key` 没有多目标命名空间
- **影响**: 策略互相干扰，考试策略应用到健身上

---

## 五、极端使用条件分析

### 极端场景 1: 考试前 24 小时高频使用

**用户行为**: 每 30 分钟一次交互，连续 20 小时
**系统影响**:
- 40+ 个 CausalTrace 产生 → `_MAX_USER_TRACES=50` 接近满
- RecallOpportunity 的 `pre_exam_silence` 检测失效（用户不沉默）
- AchievementMomentum 持续 momentum_high → 系统可能过度鼓励
- fatigue_rate 在 UserSimulator 中有建模，但生产系统无疲劳检测

**缺失**: 没有生产级的用户疲劳检测和强制休息机制

### 极端场景 2: 完全零基础 + 考试倒计时 3 天

**用户行为**: 第一次使用，完全不会，3 天后考试
**系统影响**:
- ExamRescueDetector 能检测意图 → ✅
- 但 goal_type_adapter 只定义了 5 种 mastery 映射 → 对 "完全不会" 场景可能不够
- ExamSprintPolicy D-3 策略是 `light_recall` → 对零基础太轻量
- 资料闭环依赖用户上传资料 → 零基础用户可能没有资料

**缺失**: 零基础 + 极短时间场景没有专门的应急策略

### 极端场景 3: 弱网 / 离线后恢复

**系统设计**:
- Redis 依赖严重 — 所有 Spine 状态在 Redis
- Redis 宕机 → Spine 完全失效（所有方法都有 try/except 兜底）
- 恢复后 → 所有状态从零开始（TTL 已过）
- **缺失**: 无 Redis 持久化备份策略，无状态恢复机制

---

## 六、代码质量风险

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| Q1 | `import json` 在 25 个方法体内重复 | spine_orchestrator.py | 性能 + 可读性 |
| Q2 | `except Exception` 吞错误 | spine_orchestrator.py:362 | 可能隐藏关键故障 |
| Q3 | 12 个孤立模块无消费者 | 详见第三节 | 维护负担 + 测试幻觉 |
| Q4 | FakeRedis 测试与生产 Redis 行为差异 | test_signal_spine.py | 测试可能通过但生产行为不同 |

---

## 七、优先修复建议

### P0 — 架构级修复（不修就不能叫"完全体"）

| # | 任务 | 估计 | 影响 |
|---|------|------|------|
| P0-1 | **Aurora ↔ Spine 桥接** — Aurora decision_loop 消费 ActionableStatePacket，Spine 消费 Aurora 的 decision 输出 | 5 天 | 消除双系统割裂 |
| P0-2 | **接入 12 个孤立模块** — 把它们接入 SpineOrchestrator pipeline | 3 天 | 激活 43% 沉睡代码 |

### P1 — 神性时刻补全

| # | 任务 | 估计 | 影响 |
|---|------|------|------|
| P1-1 | Growth Chronicle API + 前端卡片 | 2 天 | 神性时刻 1 激活 |
| P1-2 | Source Receipt 接入 chat 响应层 | 1 天 | 神性时刻 3 激活 |
| P1-3 | Recovery Card 接入用户返回流 | 1 天 | 神性时刻 4 激活 |
| P1-4 | Community Hint 接入 ResponseDirective | 1 天 | 神性时刻 6 激活 |

### P2 — 稳定性加固

| # | 任务 | 估计 | 影响 |
|---|------|------|------|
| P2-1 | SpineMetrics 定期重置 + 精度保护 | 0.5 天 | 消除 H1 |
| P2-2 | Growth Chronicle 分页加载 | 0.5 天 | 消除 H2 |
| P2-3 | 老用户回归状态恢复机制 | 2 天 | 消除退化场景 1 |
| P2-4 | 长期策略记忆（超 50 trace 限制） | 1 天 | 消除退化场景 2 |
| P2-5 | 多目标命名空间隔离 | 1 天 | 消除退化场景 3 |

### P3 — 极端条件保障

| # | 任务 | 估计 | 影响 |
|---|------|------|------|
| P3-1 | 用户疲劳检测 + 强制休息机制 | 1 天 | 极端场景 1 |
| P3-2 | 零基础 + 极短时间应急策略 | 1 天 | 极端场景 2 |
| P3-3 | Redis 持久化 + 状态快照恢复 | 2 天 | 极端场景 3 |

---

## 八、总结评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **逻辑完整性** | 9/10 | 28 个模块覆盖了愿景的所有功能域 |
| **测试覆盖** | 8.5/10 | 484 测试，但都是单元测试，缺 E2E |
| **用户可感知** | 3.5/10 | 43% 代码处于孤立状态，4/6 神性时刻不可感知 |
| **架构一致性** | 4/10 | Aurora 和 Spine 割裂，不是 "同一根 Spine" |
| **长期稳定性** | 5/10 | 有 TTL 和修剪但缺恢复机制和疲劳保护 |
| **极端条件** | 4/10 | 弱网和极限场景保护不足 |
| **综合** | **5.5/10** | 基础设施优秀，但"最后一英里"未走完 |

**核心结论**: Sparkle 的 Spine 已经建成了完整的"骨架+器官"，但神经没有完全接通——12 个模块处于"存在但未激活"状态，Aurora 和 Spine 各自为政。要让用户真正感受到完全体，需要一次系统性的"接线"工作，而非更多新功能开发。
