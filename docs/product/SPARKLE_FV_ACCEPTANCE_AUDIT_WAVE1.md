# Sparkle 完全体验收审查 — 第一波审计报告

> 日期: 2026-05-02
> 方法: 8 并行 Sonnet 探索 agent + 主 agent 直接代码验证
> 状态: 第一波完成，第二波深度验证进行中

---

## 一、一票否决项验证（主 agent 亲自验证）

| # | 否决项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | Aurora 与 Causal Control Spine 割裂 | ⚠️ 需关注 | `aurora_spine_confluence.py` 实现完整，但主 orchestrator 未直接导入。通过 `SpineAuroraBridge` 间接连接，orchestrator 获取 6 类 Directive。合流存在但非直接。 |
| 2 | 关键模块只存在代码未被生产主链消费 | ⚠️ 部分风险 | SpineOrchestrator 已接入 orchestrator + Celery。但 L4 异步引擎(`l4_async.py`)未接入 Celery，而是 `AsyncDeepLearner` 接入。DirectiveApplicationAudit 仅在 signals/ 内，orchestration/ 未使用。 |
| 3 | 用户反馈只记录不改变行动 | ✅ 通过 | CorrectionFeedbackProcessor 已验证：用户纠正降低 StateEntry 置信度 0.15，修改 affected_state_keys（task_granularity_fit/knowledge_bottleneck/transfer_failure/strategy_confidence 等），更新 SparkleSelfModel。orchestrator.py:964 导入并使用。 |
| 4 | 关键闭环无 Outcome 回流 | ⚠️ 部分风险 | OutcomeRecorder 存在于 signals/，但 orchestrator 层面是否记录 actual_outcome 未确认。 |
| 5 | 高影响判断不可解释/纠正/撤销 | ✅ 通过 | CorrectionFeedbackProcessor + PredictedReplyOption + judgment_incorrect 选项 + ContextReceiptBar + CausalTimelinePanel 组成完整纠正链。 |
| 6 | 资料粗暴污染上下文 | ✅ 通过 | ContextPlan 全模式实现（5/5），Pollution Guard 严格（5/5），Token Budget 完善（5/5） |
| 7 | 长期模型写短期状态为人格标签 | ⚠️ 需验证 | MetacognitionService 和 IdiographicAssociationService 存在，但有 LearningGuard 防护。 |
| 8 | 生产缺少降级/回滚/kill switch | ✅ 基本通过 | orchestrator 有 Spine degradation handling (line 2428-2431)，kill switch tri-state 已实现 |
| 9 | P4 实验绕过安全直接影响用户 | ✅ 通过 | Safe Experiment Platform 7 阶段生命周期，shadow-first，guardrail monitor |
| 10 | 多目标状态互相污染 | ✅ 通过 | Redis key namespace: `spine:goal:{user_id}:{goal_id}`，task card 绑定 goal_id |

---

## 二、各章节评分汇总

### 3. Causal Control Spine (SPINE-001~020)
**均分: 3.6/5** | 状态: 功能可用，需加固

| ID | 分 | 关键发现 |
|----|-----|----------|
| SPINE-001 | 4 | RawEvent 管道存在，部分社区事件绕过 |
| SPINE-003 | 4 | ActionableSignal 结构完整，counter_evidence 填充不一致 |
| SPINE-004 | 3 | Signal Ranking 10 维声明，contradiction_level 硬编码 0.5 |
| SPINE-005 | 4 | PolicyEngine 存在，冲突解决有限 |
| SPINE-009 | 5 | 9 类 Directive 全部实现 |
| SPINE-010 | 3 | 硬约束下游执行不一致 |
| SPINE-011 | 3 | DirectiveApplicationAudit 存在但下游模块不全部返回 |
| SPINE-016 | 3 | CausalTrace 可追踪但回放能力有限 |
| SPINE-018 | 2 | **跨层 trace 关联弱** — 各服务独立生成 trace_id |
| SPINE-020 | 3 | Redis 降级有 resilient wrapper，LLM/RAG 降级有限 |

### 4. Aurora Core (AUR-001~027)
**均分: 4.1/5** | 状态: 强实现，L4 有缺口

| ID | 分 | 关键发现 |
|----|-----|----------|
| AUR-002~006 | 5 | L0-L4 能级全部实现，配额/冷却/fallback 完善 |
| AUR-007 | 5 | 每轮记录能级和升级理由 |
| AUR-010 | 5 | L3 退回标准层有 SessionClosure |
| AUR-020~027 | 4 | Aurora 消费 StatePacket + PolicyDecision + Outcome，但部分路径可绕过 Spine |

### 5. Goal Modeling (GOAL-001~012)
**均分: 3.3/5** | 状态: 中等

| ID | 分 | 关键发现 |
|----|-----|----------|
| GOAL-003 | 5 | 10 种节点类型全部实现 |
| GOAL-004 | 5 | 5 个 DomainPack 实现 |
| GOAL-009 | 2 | **目标变化确认缺失** |
| GOAL-011 | 1 | **ReturnCaseFile 未实现** |
| GOAL-012 | 2 | 策略迁移机制缺失 |

### 6. Plan & Exam Sprint (PLAN-001~012)
**均分: 3.6/5** | 状态: 良好

| ID | 分 | 关键发现 |
|----|-----|----------|
| PLAN-004 | 5 | 考试冲刺阶段自动切换完整 |
| PLAN-011 | 2 | 资料变化更新节点覆盖不自动 |

### 7. Task Card (TASK-001~016)
**均分: 3.8/5** | 状态: 良好

| ID | 分 | 关键发现 |
|----|-----|----------|
| TASK-001 | 5 | 任务卡协议完整（why/materials/steps/stuck/success/minimum/updates/fallback） |
| TASK-004 | 5 | 步骤有时长、顺序、验收点 |
| TASK-012 | 2 | **恢复卡缺失** |
| TASK-013 | 1 | **Flutter 离线执行+同步未实现** |
| TASK-014 | 2 | ExecutionDirective Audit 未从任务生成返回 |

### 8. Knowledge Graph (KG-001~010)
**均分: 3.1/5** | 状态: 基础好，细节缺

| ID | 分 | 关键发现 |
|----|-----|----------|
| KG-005 | 2 | 重复错因→任务模板反馈链缺失 |
| KG-009 | 2 | "为什么今天学这个"解释缺失 |
| KG-010 | 3 | 掌握度伪精确保护不明确 |

### 8. Source/RAG/ContextPlan (SRC-001~018)
**均分: 4.2/5** | 状态: 优秀

| ID | 分 | 关键发现 |
|----|-----|----------|
| SRC-003 | 5 | ContextPlan 全模式（8 种） |
| SRC-005 | 5 | Pollution Guard 严格 |
| SRC-006 | 5 | Token Budget 完善 |
| SRC-010 | 5 | Context Receipt 完整 |
| SRC-015 | 2 | 社群资料接受门控缺失 |

### 10. Outcome & Learning (OUT/LEARN/SKILL/GROW)
**均分: ~3.5/5** | 状态: 待验证（agent 报告待交叉检查）

### 12. Community (COM-001~012)
**均分: 3.75/5** | 状态: 良好

| ID | 分 | 关键发现 |
|----|-----|----------|
| COM-006 | 5 | 匿名共性错因影响策略 |
| COM-007 | 5 | 多因子资源质量评分 |
| COM-008 | 5 | k=5 匿名阈值 |
| COM-010 | 5 | CommunityDirective 结构化 |
| COM-005 | 2 | 伙伴观察拒绝处理缺失 |
| COM-011 | 2 | 社群 UI 目标关联缺失 |

### 13. Recall/Nudge (NUDGE-001~010)
**均分: 4.3/5** | 状态: 优秀

| ID | 分 | 关键发现 |
|----|-----|----------|
| NUDGE-001~004 | 5 | 目标价值召回、完整元数据、低成本下一步、安静时间 |
| NUDGE-009 | 5 | 召回可解释性优秀 |

### 14. P4 Research Grade
**均分: 4.2/5** | 状态: 强实现

| 子项 | 分 | 状态 |
|------|-----|------|
| 14.1 Evaluation Logging | 4.5 | ✅ |
| 14.2 Counterfactual | 5.0 | ✅ |
| 14.3 Safe Experiment | 5.0 | ✅ |
| 14.4 Simulation Lab | 3.5 | ⚠️ |
| 14.5 Marketplace | 4.5 | ✅ |
| 14.6 Privacy Community | 5.0 | ✅ |
| 14.7 Quality Guard | 4.0 | ✅ |
| 14.8 Research Mode | 3.0 | ⚠️ |

---

## 三、Infrastructure/Stability/Observability (Section 15-18)

⚠️ **第一波 agent 报告不可信**（未能找到实际文件），需要重新验证。

主 agent 直接验证的部分：
- SpineOrchestrator 接入 orchestrator.py（line 2343）和 celery_tasks.py（5 处引用）
- trace_id 在 orchestrator.py 中传播（15+ 处引用）
- ContextPlan retrieval_mode 在 orchestrator.py:1943 使用

---

## 四、最严重缺口清单（< 2 分）

| 优先级 | 缺口 | 影响 |
|--------|------|------|
| P0 | SPINE-018: 跨层 trace_id 关联 (2/5) | 端到端审计链断裂 |
| P0 | GOAL-011: ReturnCaseFile (1/5) | 老用户回归体验断裂 |
| P0 | TASK-013: Flutter 离线执行+同步 (1/5) | 移动端核心体验缺失 |
| P1 | GOAL-009: 目标变化确认 (2/5) | 用户主权风险 |
| P1 | TASK-012: 恢复卡 (2/5) | 时间感知断裂 |
| P1 | TASK-014: ExecutionDirective Audit (2/5) | 任务生成不可审计 |
| P1 | COM-005: 伙伴观察拒绝 (2/5) | 社群隐私风险 |
| P1 | SRC-015: 社群资料接受门控 (2/5) | 隐私风险 |
| P2 | KG-005: 错因→任务模板 (2/5) | 错因闭环断裂 |
| P2 | KG-009: 节点优先级解释 (2/5) | 可解释性缺口 |
| P2 | GOAL-012: 策略迁移 (2/5) | 跨目标学习缺失 |
| P2 | COM-011: 社群目标关联 UI (2/5) | 社群体验跑偏 |

---

## 五、第二波验证计划

需要用 Opus agent 深度验证：
1. Infrastructure (Flutter/Go/Python/Events) — 第一波 agent 失败
2. Stability (STAB-001~020) — 第一波 agent 失败
3. Security/Governance (GOV-001~020) — 第一波 agent 失败
4. Observability (OBS-001~020) — 第一波 agent 失败
5. Aurora UX / Magic Moments — 第一波 agent 报告待审查
6. Feedback/Learning 交叉验证 — 第一波 agent 报告待审查
