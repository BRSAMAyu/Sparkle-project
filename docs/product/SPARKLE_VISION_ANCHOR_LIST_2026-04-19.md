# Sparkle 愿景锚定清单

> **文档性质**: MIMO 战略对齐工具
> **维护者**: MIMO
> **日期**: 2026-04-21
> **版本**: v29（Stage 29.5 closeout + Stage 30 in progress）
> **v2.2 锁定**: Stage 22-29.5 ✅ / Stage 30 🔶 / Stage 31-32 ❌
> **用途**: 锚定长期多阶段工作的方向，每次派卡前核对是否偏离
> **权威来源**: 本清单中的每一条均可追溯至以下已签字文档
> - `SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` — 产品核心共识
> - `SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md` — Stage 4 战略共识 v2
> - `SPARKLE_AURORA_STAGE5_DISPATCH_PLAN_2026-04-19.md` — Stage 5 派发计划
> - `SPARKLE_AURORA_STAGE5_HANDOFF_2026-04-19.md` — Stage 5 收尾 handoff
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md` — 用户模型五层架构
> - `SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md` — 成长系统路线图
> - `SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md` — 数据利用分析
> - `SPARKLE_AURORA_STAGE16_DISPATCH_PLAN_2026-04-20.md` — Stage 16 派发计划（WS-MWL-* 七个 Workstream + Rule Y）
> - `SPARKLE_AURORA_STAGE17_DISPATCH_PLAN_2026-04-20.md` — Stage 17 派发计划（WS-SOC-* 社交脑 MVP + Rule Z + Accountability + Router 只读）
> - `SPARKLE_AURORA_STAGE17_HANDOFF_2026-04-20.md` — Stage 17 工程收尾（8 WS accept + 144 baseline + 27 backend + 51 mobile）
> - `SPARKLE_AURORA_STAGE18_DISPATCH_PLAN_2026-04-20.md` — Stage 18 派发计划（State Aggregator + 确定性 push + Rule AB）
> - `SPARKLE_AURORA_STAGE18_HANDOFF_2026-04-20.md` — Stage 18 工程收尾（8 WS accept + 97 baseline + 42 backend）
> - `SPARKLE_AURORA_STAGE18_RULE_AB_DEFINITION_2026-04-20.md` — Rule AB 正式定义（push 治理：evidence/cap/quiet-hours/retraction）
> - `SPARKLE_AURORA_STAGE19_HANDOFF_2026-04-20.md` — Stage 19 工程收尾（7 WS accept + 30 tests + Working Memory Redis-only + LLM dry-run）
> - `SPARKLE_AURORA_STAGE19_RULE_AC_DEFINITION_2026-04-20.md` — Rule AC 正式定义（Working Memory 治理：Redis-only / 无 SQL/Alembic / consolidation 不触发 push）
> - `SPARKLE_AURORA_STAGE20_HANDOFF_2026-04-21.md` — Stage 20 工程收尾（7 WS accept + Sufficiency Judge + Conflict Resolver + Route History）
> - `SPARKLE_AURORA_STAGE20_RULE_AD_AE_DEFINITION_2026-04-21.md` — Rule AD/AE 正式定义
> - `SPARKLE_AURORA_STAGE21_HANDOFF_2026-04-21.md` — Stage 21 工程收尾（8 WS accept + Skill 蒸馏 + Rule AF）
> - `SPARKLE_AURORA_STAGE21_RULE_AF_DEFINITION_2026-04-21.md` — Rule AF 正式定义
> - `SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md` — 前沿理念融合分析（Stage 16/17 链路锚点）
> - `SPARKLE_AURORA_ROADMAP_v2_2_FINAL_LOCK_2026-04-21.md` — Aurora 路线图 v2.2 最终锁定（Stage 22-32）
> - `SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md` — Stage 22 派发计划（v2.1 修订版）
> - `SPARKLE_AURORA_GOVERNANCE_GRAY_WINDOW_CONTEXT_2026-04-20.md` — Gray Window 上下文化治理增补（PGW / SGW / Skipped）
> - `SPARKLE_AURORA_STAGE16_RULE_Y_DEFINITION_2026-04-20.md` — Rule Y 正式定义（推断式画像写入治理）
> - `SPARKLE_AURORA_STAGE16_READ_VERIFY_REPORT_2026-04-20.md` — Stage 16 读验证报告
> - `SPARKLE_AURORA_STAGE16_EXTRACT_DRY_RUN_REPORT_2026-04-20.md` — Stage 16 冷数据 dry-run precision 报告
> - `SPARKLE_AURORA_STAGE16_SGW_FRAMEWORK_2026-04-20.md` — Stage 16 Simulated Gray Window 框架（Pre-launch Gray substitute）
> - `SPARKLE_AURORA_STAGE16_HANDOFF_2026-04-20.md` — Stage 16 工程收尾与 Stage 17 约束锁定

---

## 一、核心使命

**一句话**：帮助用户跨越"理想中的自己"和"现实中的自己"之间鸿沟。

**产品定义**（产品共识 §2.1 最终定义）：

> Sparkle 是一个**AI 学习成长系统**。这一定义高于"助手"，也高于"教练"。
> - 它不是 AI 学习助手
> - 它不是 AI 教练产品
> - "教练"最多只是系统在某些场景下采用的交互角色
> - "助手"最多只是系统在某些任务上的局部能力表现

**产品定位**：
- 短期形态：AI 学习教练
- 长期形态：AI 成长操作系统
- 两者是同一条曲线，不是两个产品

---

## 一-A、三层模型（防止定义 / 架构 / 验证信号互相替代）

本清单严格区分三层。任何一层不能被另一层静默替换。如果需要修改第一层，必须走文档 amendment 流程。

### 第一层 · 系统是什么（签字定义，不走 amendment 不能改）

Sparkle = **AI 学习成长系统**

签字定义不变。任何 reframing（"社会体"、"队友"、"教练"、"OS"）都不能替代此定义。如果未来要改，必须走正式 amendment，有用户签字。

### 第二层 · 系统的本质（架构层，可随工程演进而精确化）

- **用户与 Sparkle 的关系**：**朋友**——一个真正、美好的友谊关系。不是教练-学员（等级关系），不是用户-工具（使用关系），不是队友（任务合作关系）。朋友意味着真诚、在乎、但不替代用户的判断。
- **Sparkle 的自我发展空间**：Sparkle 对自己的定义、对用户的理解、对这段关系的认识，可以有**在限制范围内的发展空间**。它不是静态的配置文件，而是一个能在交互中成长的动态存在。发展的边界由用户显式控制。
- **Aurora 的技术本质**：adaptive context engineering——在每次交互中动态组装真正匹配当下的 context。
- **整个系统的技术本质**：adaptive harness engineering——整套支撑结构围绕"让自适应能力在真实场景里稳定运行"来设计。

### 第三层 · 用户感受什么（验证信号，不是优化目标）

以下是系统做对了之后在用户端应该出现的**可观察结果**。我们不直接优化这些感受，我们优化第二层的架构本质，用第三层的信号验证第二层是否做对了：

| 信号 | 含义 | 可验证条件 |
|------|------|-----------|
| **A1 高匹配个性化** | 简单输入也能收获高度个性化的响应 | 用户显式肯定语言频率、连续对话深度、"这理解我"类表达 |
| **A2 低抵触率** | 干预建议触发好奇而非焦虑/羞耻 | 建议采纳率、拒绝后对话延续率、抵触语言频率 |
| **A3 真实采纳→行动→反馈闭环** | 用户采纳后真的去做、结果被系统感知 | 采纳率 × 行动率 × 反馈采集率 |
| **A4 长期目标进展** | 用户自述渴望在真实场景下有进展 | 目标-行动-结果 trace 完整性、周/月级复盘留存 |
| **A5 友谊姿态一致性** | 不同场景里是同一个朋友，不是人格碎片 | 跨会话画像一致性、发言风格稳定性、承诺-跟进率 |

**关键原则**：A1-A5 是**结果**，不是**目标**。我们优化 B/C/D/E 类的架构能力，用 A 类验证是否做对了。直接优化 A 类会导致指标漂移。

---

## 二、架构愿景

### 2.1 双核协作

| 核心 | 职责 | 关键约束 |
|------|------|----------|
| **执行核** | 目标澄清 → 充分性评估 → 阶段化 plan → 可执行任务 → 执行反馈 → 动态调整 | 必须与认知核协作 |
| **认知核** | 用户画像 → 记忆（长/短期）→ 认知棱镜 → 情绪/动机/状态理解 → 个性化支持 → 持续陪伴 | 必须与执行核协作 |

**硬约束**：两核必须协作，不能并行孤岛。协作通过 DualCoreRouter 实现，不是运行在平行隔离中。

### 2.2 Aurora 定位

Aurora 不是产品，是双核协作的**技术脊柱**——决定在任何一次对话中，认知核与执行核如何配合、用什么时间尺度响应、如何不互相覆盖。

**三时层模型**（Stage 4 核心架构）：

Aurora 是一个引擎在三种预算约束下的行为谱，对外统一、内部分层：

| 时层 | 预算 | 触发方式 | 典型产物 |
|------|------|---------|---------|
| **inline** | P95 < 100ms | 同步路径 | BackboneRoutingDecision（含 routing_mode） |
| **nearline** | P95 ≤ 30s, P99 ≤ 60s | 会话结束 / idle / 提交 | TDR、InsightClaim、ProbeOutcome、TaskGuidance |
| **long-horizon** | 小时~天级 | 批处理 / 定时 / 成长周期 | FocusContract 演进、IdentityEvidence 聚合 |

**关键设计决策**（已锁定，不重新辩论）：
- 三时层**不是**三个 Aurora，是**一个引擎在三种预算下的行为谱**
- 下游**不感知时层**（P2 外部一体）
- Presence 和 Time-tier 是**正交两轴**，不映射（Presence 决定可见度，Time-tier 决定预算）
- 通信只通过 primitives 或 prior_outputs（P1 红线）
- 三时层**禁止**共享内存、禁止共享 ORM session

### 2.3 用户模型五层架构（Rule K 写入纪律）

画像系统是 pipeline + projection cache，不是 source-of-truth store。SoT 在 L0 Infrastructure。

| 层 | 职责 | 写入边界 |
|----|------|----------|
| **L0 Infrastructure** | 收集 raw evidence，构建全软件闭环 | 只写 raw evidence events，不写 projection/inference |
| **L1 画像系统** | 清洗、标准化、投影、证据链、projection cache | 只写 projection cache，不改 L0 raw events |
| **L2 AI System** | 归因、压缩、裁判、预测、inference cache | 只写 inference cache，不改 L1 fact |
| **L3 Aurora** | 独立影子状态、参数调控、漂移检测 | 只写白名单参数（数值/策略），不写任何层 data |
| **用户纠偏** | 直达 raw/calibration，不经过 Aurora 代写 | 绕过 L2/L3，L1 下次编译周期吸收 |

**Aurora 白名单纪律**：调旋钮（权重、阈值、采样频率、输出策略、token 分配）不改电路（数据源、算法、证据链结构、纠偏记录）。

**Aurora 影子模型**：轻量状态摘要（朋友姿态锚、身份/审美、目标路由、执行评估、不确定性标记），用于漂移检测——Aurora 说的和画像系统说的不一致 = 需要问用户。

### 2.4 双交互模式

| 模式 | 体验 | Aurora 介入度 |
|------|------|--------------|
| **普通对话** | 日常问答、任务执行 | 低介入，交互模型主导 |
| **深度模式** | "走进内心世界"的感觉 | 高介入，Aurora 主导但通过交互模型呈现 |

**设计哲学**：用户需要知道何时在和什么交流。深度模式下，语气更直接、更系统内核感，但本质上仍是交互模型，只是 context policy 和 prompt 不同。

---

## 三、用户交互愿景

### 3.1 交互式校准

**核心思想**：用户通过对话让系统理解自己，系统在对话中更新画像，同时保持独立判断。

**关键场景**：
- 用户问"我最近学习状态怎么样？" → 系统基于画像回答 → 用户可以校准
- 系统判断"用户容易放弃"，但用户解释"家里出事了" → 系统理解背后原因 → 更新参数 + 调整交互策略
- 不是冰冷的参数调整，而是理解上下文的人情味

**技术实现**：
- 用户画像可读写（通过对话，不是设置界面）
- 系统保持独立判断，不完全听信用户
- 证据链可理解（不是看不懂的参数）

### 3.2 透明度与可控性

**三层展示**：
1. 可校正的（用户可以直接调整）
2. 不可直接校正的（系统建议，用户可讨论）
3. 敏感推断（系统谨慎处理）

### 3.3 干预语言原则

**抵触干预是产品第一位的风险**。干预方式必须满足（产品共识 §8.2）：

1. 不审判
2. 不羞辱
3. 不替用户做道德评价
4. 不先告诉用户"你又失败了"
5. 先建立同侧关系，再提出改动建议
6. 优先引发好奇和重新启动，而不是制造羞耻和焦虑

**最高约束**：
> Sparkle 不是指出你不行，而是帮助你重新变得能走。

---

## 四、任务系统愿景

### 4.1 对话分流（三路，非两路）

同一个 Aurora 引擎，根据请求复杂度选择不同产出形态（Stage 4 §4.2 共识）：

| 路径 | routing_mode | 说明 |
|------|-------------|------|
| **简单直接回答** | `direct` | inline 出 stay + ambient，orchestrator 走短 FSM |
| **复杂任务工作流** | `workflow` | inline 出 transition 意向 + nearline 补 TDR 全记录，走长 FSM |
| **任务助手** | `task_assistant` | 单核 + Aurora 一次性注入，走独立路径 |

**关键机制**：
- routing_mode 是 `BackboneRoutingDecision` 上的**字段**，不是独立服务
- 支持**会话中途升级**——对话从简单升为复杂时，Aurora 重新发 transition 意向
- 升级触发最小集：显式规划请求 / 连续 2+ 轮同话题 / 挫败信号

### 4.2 TaskGuidance 双版本产物

任务指南从"静态模板"升级为"Aurora 参与生成的双版本产物"（Stage 4 §4.3 共识）：

- **人类版**（default）：人话、情境化、低密度；创建任务卡时**默认生成**并推送
- **AI 版**（on-demand）：结构化、ref-rich、高密度；用户点"给 AI 用的版本"时**才生成**
- 两个版本从**同一个 TaskGuidance primitive** 派生，保证一致性
- 双版本**不预先全量生成**，避免成本叠加
- TaskGuidance 是 **Stage 4 候选 primitive**，尚未正式入宪 Gate 0

### 4.3 任务助手降级

**原则**：单核模式，但会话起点接收 Aurora 一次性注入（Stage 4 §4.4 共识）：

**5 项注入清单**：
1. 当前 `FocusContract` 摘要
2. 当前 `TaskGuidance` 的 AI 版本（若已生成，否则 fallback 为用户版摘要）
3. 最近一次 `TransitionDecisionRecord` 的 `UXIntent + AuroraPresenceLevel`
   - **冷启动 fallback**：`UXIntent.ROUTINE + AuroraPresenceLevel.AMBIENT`
4. projection-allowed 的活跃 `InsightClaim`
5. 最近 N 条相关 `ProbeOutcome`

**运行期间策略**：
- 注入后任务助手按单核正常跑
- Aurora **不**向该会话注入新的 context 或干预指令
- 但 Aurora 可以在 nearline 收集该会话的 outcome 用于**下一轮**注入
- 仅在强信号（crisis / emotional_block / capability ceiling）命中时才 refresh 注入

---

## 五、持续学习愿景

### 5.1 三层学习结构

| 层级 | 范围 | 说明 |
|------|------|------|
| **对话内学习** | 单次对话 | 即时反馈和调整 |
| **跨对话学习** | 用户整体 | 用户画像和偏好的长期积累 |
| **跨用户学习** | 全系统 | 从成功案例中蒸馏可复用知识 |

### 5.2 知识蒸馏管道

**流程**：用户成功案例 → 系统总结抽象浓缩 → 形成高信息密度的知识 → 放入 learning base

**关键设计**：
- 用户确认机制：展示学到的知识，用户选择私有或公开
- 质量过滤：系统层面评判和拦截不好的知识
- 种子库升级：从写死的变成活的、由系统主动蒸馏的

### 5.3 种子库定位

- 现状：人工写死的预设
- 目标：持续学习的 foundation
- 用户可以选择将蒸馏的知识加入个人 learning base 或公开可见

---

## 六、成长环与数据愿景

### 6.1 七阶段成长环

```
Sense → Clarify → Plan → Execute → Reflect → Reinforce → Adapt
```

任何模块必须能映射到其中一阶段，否则就是漂流物。

### 6.2 日常闭环（完整定义）

```
发现问题 → 以用户可接受的方式交付 → 用户愿意采纳 → 产生行动 → 验证有效 → 更新系统
```

**关键修正**（产品共识 §5.3）：
- 不是"发现问题"就算完成
- 不是"建议用户改变"就算闭环
- **最容易被忽略的两步**：① 以用户可接受的方式交付 ② 用户愿意采纳

### 6.3 闭环原则（P3 宪法级）

- Aurora 默认**不**把用户转给外部 AI；Sparkle 是用户的唯一成长终端
- **唯一例外**（capability ceiling）：请求进入 `CapabilityGate` 拒绝域（医疗诊断、法律咨询、紧急危机援助热线）时，明示转介，UX 必须告知用户"这是转介，不是 Sparkle 在回避"
- 除 capability ceiling 外，所有"我帮不了你，你去问 ChatGPT"式话术**禁用**

### 6.4 数据利用（四层泄漏）

| 层级 | 当前状态 | 目标 |
|------|----------|------|
| 采集 | 95% | 保持 |
| context dict | 75% | 提升 |
| prompt | 40-50% | 大幅提升 |
| AI 推理 | 20% | 大幅提升 |

**最高 ROI 修复**：`format_user_context()` 在 prompts.py 中采集了 `error_summary`、`recent_errors`、`recent_mastery_changes` 但从未渲染进 prompt（数据利用分析 §Priority 1）。

### 6.5 90 天计划（产品共识 §12.2）

未来 90 天唯一主题：跑通一个真实可验证的成长闭环。

| 阶段 | 天数 | 目标 | 成功标准 |
|------|------|------|----------|
| **第一阶段** | 0-20 天 | 接通核心数据与计划执行 | 错题分析回写知识节点掌握度；adaptive_replanner 真正写回计划；梳理干预语言体系 |
| **第二阶段** | 21-50 天 | 接通主动预警与行为干预 | plan health = critical 稳定转化为事件；推送支持行为触发；干预语言 A/B 测试 |
| **第三阶段** | 51-70 天 | 接通参数层与效果回流 | cognitive_adjustments 改变实际参数；建立干预后效果验证和回流机制 |
| **收尾阶段** | 71-90 天 | 打磨单一端到端主场景 | 完成一个稳定可演示、可验证、可复用的主链路闭环 |

**核心原则**：暂停大多数非核心新功能开发，所有资源优先服务于主链路。

### 6.6 六个产品断点（按优先级排列）

**第一梯队**（最关键）：
1. 干预交付方式和语言体系
2. `adaptive_replanner` → 计划执行（已产生调整但未写回计划）
3. 错题分析 → 知识节点掌握度（错误信号流向 profile 而非 mastery）

**第二梯队**：
4. 风险事件触发（plan health = critical 无事件）
5. 行为触发推送（推送只有 time-only）
6. 参数级调整（cognitive_adjustments 只是文本）

**第三梯队**：
7. 干预效果验证与回流（没有 verification 环节）

---

## 七、5-P 宪法与治理边界

### 7.1 Stage 4 新增宪法（与原有 Aurora 宪法并列）

| ID | 原则 | 可验证条件 |
|----|------|-----------|
| **P1** 时层纪律 | 三时层只通过 primitives 或 prior_outputs 通信 | 代码层禁止跨时层共享状态；CI 检测 |
| **P2** 外部一体 | 下游不感知 Aurora 时层 | 下游接口不出现 "inline/nearline" 字样 |
| **P3** 闭环原则 | 默认不转外部 AI，除 capability ceiling 窄窗 | CapabilityGate 拒绝域有白名单且 UX 明示 |
| **P4** 颗粒分流 | 简单/复杂路径共用 Aurora，不分叉引擎 | 只有一个 AuroraEngine 类；routing_mode 是字段不是服务 |
| **P5** 预算可观测 | 每时层有成本/延迟预算并上报 | 每次调用带 tier 标签 |

### 7.2 Stage 4 显式不做清单（硬红线）

1. ~~pre-tool-selection 接管~~（deferred 到 Stage 5+）
2. ~~pre-response-formatting 接管~~（deferred 到 Stage 5+）
3. ~~新建独立 AI 路由服务~~
4. ~~任务助手重写为双核~~
5. ~~三时层拆为三个独立服务/进程~~
6. ~~任务助手运行期间 Aurora 注入新 context~~（nearline 收集 outcome 用于下一轮可以）
7. ~~Stage 4 内铺 cohort 放量~~

任何新提议撞到这 7 条中任意一条，默认拒绝。

### 7.3 Rule K · 用户模型写入纪律（Stage 5 新增）

所有与用户模型相关的写入必须落入五条通道之一：

| 通道 | 可写 | 禁写 |
|------|------|------|
| L0 Infrastructure | raw evidence events | projection / inference |
| L1 画像系统 | projection cache | L0 raw events, L2 inference |
| L2 AI System | inference cache | L1 fact, L0 raw events |
| L3 Aurora | 白名单参数（数值/策略）+ 审计日志 | 任何层 data |
| 用户纠偏 | raw / calibration 条目 | 推断/控制层伪装为用户真相 |

**白名单纪律**：调旋钮不改电路。Aurora 可调权重、阈值、采样频率、输出策略、token 分配；不可改数据源、算法、证据链结构、纠偏记录。

### 7.4 构建顺序原则

**先建完整，再精简**：
- 精简版需要知道从什么精简
- 如果精简版先出，完整版可能永远不会建
- 成本/延迟预算只有在完整版跑起来后才能真实测量

---

## 八、设计哲学

### 8.1 权利分配

- 系统提供 foundation，具体发展由用户决定
- 必须往好的方向引导，但不是虚假的奉承
- 用户拥有控制权：硬约束参数可设置，Policy 可显式控制
- 系统保持独立判断，不完全听信用户

### 8.2 Adaptive Harness 核心优势

- 边界约束 + 自由度空间
- 确定性参数 + 自适应调整
- 人机协同的新范式

---

## 九、当前进度与愿景距离

### 9.1 Stage 4 完成（全部 WS accept）

| WS | 内容 | 状态 |
|----|------|------|
| WS-A.1 | Aurora 异步 substrate（三时层调度、Celery 入口、P1 修复） | ✅ accept |
| WS-B.1 | routing_mode seam | ✅ accept |
| WS-B.2 | Escalation Completion | ✅ accept |
| WS-C.1 | TaskGuidance sidecar skeleton + CRUD | ✅ accept |
| WS-C.2 | TaskGuidance 双版本 UI（Flutter） | ✅ accept |
| WS-D | Task Assistant Dormant Mode（重建） | ✅ accept |
| WS-E | Closed-Loop UX | ✅ accept |
| WS-F.1 | Benchmark harness + P1 guardrail | ✅ accept |

### 9.2 Stage 5 完成（5 WS accept，88 tests green）

| WS | 内容 | 状态 |
|----|------|------|
| WS-K1 | Learning-State Fragment（错题/mastery → 稳定片段） | ✅ accept |
| WS-R1 | Adaptive Replanner Closure（执行反馈 → 下一步 delta） | ✅ accept |
| WS-L1 | Intervention Language Contract（锚定 §3.3 介入语言） | ✅ accept |
| WS-G1 | Growth Signal Uplink（成就 → Aurora 单向信号） | ✅ accept |
| WS-S1 | Shadow Expansion（50 cases + hook metrics） | ✅ accept |

**Stage 5 关键成果**：
- 7 阶段环：1/7 → ≥3/7（Execute→Reflect, Reflect→Adapt 变强）
- 断点：#1 adaptive_replanner→执行、#2 error/mastery→profile、干预语言体系已推进
- 双核闭环：cognitive/error evidence → learning-state fragment → intervention contract → replanner delta → outcome feedback

### 9.3 用户模型架构已落地

| 组件 | 状态 | 说明 |
|------|------|------|
| 五层架构（L0-L3 + 用户纠偏） | ✅ 已落盘 | `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md` |
| Rule K 写入纪律 | ✅ 已定义 | 四档 + 用户纠偏独立通道 + 白名单 |
| Aurora 影子模型 | ✅ 已定义 | 轻量状态摘要 + diff 漂移检测 |
| L1 现状：UserInsightCompiler 四件套 | ✅ 70% 已实现 | compiler + state + calibration + transparency |

### 9.4 Stage 6 完成（6 WS accept）

| WS | 内容 | 状态 |
|----|------|------|
| WS-M1a | M1 源清点 + 数据质量评估 | ✅ accept |
| WS-M1b | M1 投影实现（编译已有源 + 补缺口） | ✅ accept |
| WS-RP1 | 渲染管线修复（format_user_context 优先消费 UserInsightState） | ✅ accept |
| WS-V1 | 用户纠偏后端环硬化（endpoint 级端到端测试） | ✅ accept |
| WS-E1 | profile-aware evaluation 骨架（只读 fixture + harness） | ✅ accept |
| WS-VR1 | 干预效果验证 → verification payload | ✅ accept |

**Stage 6 关键成果**：
- 渲染管线：prompt 路径现在消费 canonical UserInsightState（泄漏修复最后一公里）
- 用户纠偏：后端读写路径已验证，前端消费侧待 WS-V2
- 评估：有骨架，无真实 runner（待 WS-E2）
- 干预验证：verification payload 已落地

### 9.5 Stage 7 完成（4 WS accept，143 tests green）

| WS | 内容 | 状态 |
|----|------|------|
| WS-C1 | 双 compiler 归一（CompiledInsightState.from_user_insight_state() 委托模式） | ✅ accept |
| WS-M1c | M1 数据质量深化（source coverage / quality registry） | ✅ accept |
| WS-V2 | 透明度/纠错 Flutter 消费侧（kWs6ProfileSurfaceEnabled = true） | ✅ accept |
| WS-E2 | 真实 evaluation runner（只读 runner + baseline fixture） | ✅ accept |

**Stage 7 关键成果**：
- **系统第一次有了用户能在手机上感知的画像闭环**（WS-V2）
- compiler 边界清晰：UserInsightCompiler 仍是 fact owner，CompiledInsightState 通过委托消费
- eval runner 可执行，M1 数据质量可观测
- Rule G/H/I/J/K/L/M 零违规

**GLM P2 发现（已接受，Stage 8 处理）**：
| P2 | 内容 | Stage 8 处理 |
|----|------|-------------|
| P2-1 | WS-V2 fallback 链无日志 | 候选 telemetry 改进 |
| P2-2 | WS-E2 评分逻辑硬编码 | 已知限制，LLM-attached evaluator 是 Stage 8+ 方向 |
| P2-3 | 无 Rule K CI 静态检测 | **Stage 8 必须收口**：pre-commit hook |
| P2-4 | handoff 文件名日期不一致 | 纯 hygiene，不修 |

### 9.6 Stage 9 完成（4 WS accept，用户前门成立）

| WS | 内容 | 状态 |
|----|------|------|
| WS-MET1 | prompt / inference utilization 定义与采集基线 | ✅ accept |
| WS-IC1 | in-chat canonical profile front door（只读） | ✅ accept |
| WS-IC2 | in-chat profile correction（User Correction 独立通道） | ✅ accept |
| WS-EV2 | rubric evaluator + optional LLM-attached metadata | ✅ accept |

**Stage 9 关键成果**：
- 用户第一次能在聊天里直接问“你现在怎么看我”，并读到 canonical 画像前门
- 用户第一次能在聊天里纠正画像，而且写路径明确不经过 Aurora / L3 / strategy lane
- prompt / inference utilization 不再是口头判断，而是有正式 metric carrier
- evaluator 不再只是硬编码 fixture scorer，而是 rubric-driven、可诊断、仍保持 `evaluation_records_only`

### 9.7 Stage 10 完成（3 WS accept，信任链深化）

| WS | 内容 | 状态 |
|----|------|------|
| WS-EV3 | evaluator real LLM-judge 接线（Rule S，只写 evaluation_records） | ✅ accept |
| WS-EVD1 | in-chat profile front door evidence_resolution：`source_markers_only` → `l0_clickable_refs` | ✅ accept |
| WS-G2D | graph-as-diagnostic 用户诊断面（“我哪里弱” chat-native card） | ✅ accept |

**Stage 10 关键成果**：
- 用户第一次能从聊天里的画像 claim 直接点回允许暴露的 `L0` 依据引用，而不只是看来源标签
- evaluator 第一次有了真实 judge attachment 路径，并且 timeout / unavailable 时能优雅降级，不破坏 `evaluation_records_only`
- graph 系统第一次不只是基础设施或节点浏览器，而是能回答“我哪里弱”的诊断面

### 9.8 Stage 11 完成（4 WS accept，信任链收紧）

| WS | 内容 | 状态 |
|----|------|------|
| WS-EVD2 | EvidenceCard 二级导航闭环（概念 → 星图 / 错题 → 错题本 / 会话 → 历史） | ✅ accept |
| WS-EV4 | LLM-judge 工程化（70/30 配置化 + timeout/budget + prompt version） | ✅ accept |
| WS-MET2 | utilization metric → ai_ops dashboard / developer surface | ✅ accept |
| WS-CL0 | 持续学习五组件信号质量审计（audit-only，不接线） | ✅ accept |

**Stage 11 关键成果**：
- Stage 10 的 clickable evidence 不再停在单层 drawer，而是对当前安全类型真正可跳转
- evaluator 的 judge 路径不再依赖硬编码权重和预算，运行配置与降级语义都显式化
- prompt / inference utilization 第一次真正出现在运维 / 开发者可见面板里
- 系统第一次对白己的连续学习资产做出“哪些绝不能接到用户前门”的硬审计结论

### 9.9 Stage 12 完成（4 WS accept，learning substrate repair）

| WS | 内容 | 状态 |
|----|------|------|
| WS-CL2a | `PersistentBayesianLearner` Redis key / TTL / compatibility 对齐 | ✅ accept |
| WS-CL2b | `multi_dimensional_learner.save_state()` + Celery 调用链修复 | ✅ accept |
| WS-MOB1 | mobile 老欠账 9 项终局收口（fix / isolate / delete） | ✅ accept |
| WS-CL2c | `strategy_store` DB-backed durable L2 cache + migration | ✅ accept |

**Stage 12 关键成果**：
- Stage 11 CL0 找出的四个具体基座缺陷已经都被修掉，连续学习不再依赖明显坏掉或重启即丢的 seam
- `PersistentBayesianLearner` key 合同第一次一致化，`multi_dimensional_learner` 不再存在缺失 `save_state()` 的假闭环
- `strategy_store` 第一次成为真正 durable 的 L2 inference cache，而不是进程内 sidecar
- Stage 12 重跑 CL0 后，结论也更诚实了：基座更健康，但**仍没有组件达到可直接接前门的 `wire` 状态**

### 9.10 Stage 13 完成（4 WS accept，signal-quality gating）

| WS | 内容 | 状态 |
|----|------|------|
| WS-SQ-METHOD | `SQAM` 四维信号质量审计方法 + Rule W 落地 | ✅ accept |
| WS-SQ-MEASURE | 对 `PersistentBayesianLearner` 跑通 4 维基线测量 | ✅ accept |
| WS-SQ-FEED | 修复 top-1 短板：reward label fidelity collapse | ✅ accept |
| WS-EVD3-LITE | `practice_outcome` 证据类型 lite 落地（memory lane + safe route） | ✅ accept |

**Stage 13 关键成果**：
- 系统第一次对白己说清楚“continuous-learning signal 何时才算够格上前门”，不再靠感觉裁定
- `PersistentBayesianLearner` 在同一份 SQAM 方法下从 `repair-first` 升级为 `wire-ready`
- 这不是“持续学习已经接线”，而是“Stage 14 终于可以对单一组件提出 bounded `WS-CL1` 候选”
- 用户面只做了一个刻意收敛的小递进：review 后的 `practice_outcome` 证据能在现有 evidence drawer / error detail 路径里被看见和点击

### 9.11 Stage 14 完成（4 WS accept，wire-safe prep）

| WS | 内容 | 状态 |
|----|------|------|
| WS-CL1-INTEG | 修复 `RouterNode -> ToolPreferenceRouter` 的持久 learner 集成残缝 | ✅ accept |
| WS-CL1-SCALE | 用 `11` source states / `220` observations 的 frozen proxy fixture 重跑 SQAM | ✅ accept |
| WS-CL1-SS-AUDIT | 审计 `state_{tool_category}` 是否阻塞 Stage 15 wire-on | ✅ accept |
| WS-CL1-SHADOW | 落地零用户感知、L2 inference-cache-only 的 divergence shadow pipe | ✅ accept |

**Stage 14 关键成果**：
- `PersistentBayesianLearner` 不再只是 frozen fixture 下的 `wire-ready`，而是完成了 integration repair + scale rerun + shadow pipe 的 `wire-safe` 准备
- Stage 13 的小 fixture 通过并不是偶然：在更大的 frozen proxy fixture 下，`ID1 / ST1 / DP1 / SM1` 仍全部保持绿色
- 但 `state_{tool_category}` 压缩被明确审定为当前 Stage 15 wire-on 的 **blocking** 限制
- 因此 Stage 14 的真实结论不是“可以接前门了”，而是“Stage 15 fork 被锁为 `Path A-blocked`”

### 9.12 显式延后挂牌（Stage 14 收尾后）

| 项目 | 来源 | 状态 | 下一归属 |
|------|------|------|----------|
| RB1 tokenizer-aware inline budget | WS-RP1 精度尾债 | deferred | Stage 15+ candidate |
| continuous learning / distillation 用户面集成（WS-CL1） | Stage 14 锁 `Path A-blocked` | deferred | Stage 15 source-state redesign / narrowed-claim amendment |
| evidence type 扩展（WS-EVD3 full） | Stage 13 仅落了 `practice_outcome` lite | deferred | Stage 15+ candidate |
| graph diagnostic 从 chat card 深化为完整 Galaxy 诊断面 | WS-G2D 深化 | deferred | Stage 15+ candidate |
| dual interaction mode | 长期愿景 | deferred | Stage 15+ candidate |

### 9.13 愿景锚点 vs 当前覆盖

| 愿景锚点 | 覆盖度 | 说明 |
|----------|--------|------|
| Aurora 异步化 | ✅ Stage 4 | 三时层 substrate + 路由分流 |
| 对话分流 | ✅ Stage 4 | 三路 routing_mode + 会话中途升级 |
| TaskGuidance 双版本 | ✅ Stage 4 | sidecar + UI |
| 任务助手降级 | ✅ Stage 4 | 单核 + 5 项注入 + dormant |
| 5-P 宪法执行 | ✅ Stage 4-8 | P1-P5 全部绿色 |
| 用户模型五层架构 | ✅ Stage 6-10 | Rule K + 影子模型 + compiler 归一 + evaluator + CI guard + chat front door + judge/evidence deepen |
| 交互式校准 | ✅ Stage 7-10 | 后端环 + 前端消费 + fallback telemetry + in-chat query/correction + clickable evidence |
| 7 个产品断点 | ✅ Stage 8 | #1/#2/#3/#4/#5/#6 + 干预语言全部收口 |
| 数据泄漏修复 | 🔶 部分 | 渲染管线已修（WS-RP1）；utilization 已可观测，但 tokenizer-aware 精度尾债仍在 |
| 双核协作闭环 | 🔶 0.6/1 | Stage 5 建了一条通路，非完整双向 |
| graph-as-diagnostic | ✅ Stage 10 | chat-native “我哪里弱” 诊断面已落地；Galaxy 专页深化仍可继续 |
| 持续学习三层结构 | 🔶 已建立 SQAM + wire-safe prep，但 Stage 15 仍 blocked | Stage 14 证明单组件在 integration / scale / shadow 维度都更可信，但 source-state 压缩仍阻止 truthful wire-on |
| 双交互模式 | ❌ 未来 | Stage 8+ |

### 9.14 距离评估

**用"7 阶段成长环"做标尺**：
- Sense → Clarify → Plan：Stage 4 ✅
- Execute → Reflect：Stage 5 ✅
- Reflect → Adapt：Stage 5-9 ✅（Stage 7 用户可感知，Stage 8 日常环治理收口，Stage 9 聊天前门成立）
- Reinforce：仍弱 ❌
- 整体：4/7

**用"用户感知"做标尺**：
- Stage 7 WS-V2 是系统第一次用户能在手机上感知的画像闭环
- Stage 8 之后，用户昨天发生的摩擦更容易被系统接住：plan-health、behavior-trigger push、bounded steering 都已有闭环证据
- Stage 9 之后，用户不再只能去设置页看画像，而是能在聊天里直接问、直接纠，这是真正的“用户前门”
- Stage 10 之后，用户不仅能看到系统怎么想，还能点开依据、并直接问“我哪里弱”，信任链和诊断链都更具体了
- Stage 11 之后，系统对“可点击”“可跳转”“可学习”这些口头承诺变得更诚实了：已支持的路径能真走通，暂不可信的学习组件被明确挡在前门之外
- Stage 12 之后，系统虽然没有新增前门能力，但“成长被系统记住”这件事第一次拥有了可重审的工程地基；诚实结论是地基已修、前门仍不能贸然接线
- Stage 13 之后，系统第一次有了“continuous learning 何时才算够格上线”的正式标尺；用户面增量很小，但治理和可测性发生了质变
- Stage 14 之后，系统第一次把 `wire-ready` 和 `wire-safe` 分开验证：集成、规模、shadow 都已补齐，但也更诚实地承认 source-state 压缩仍阻止前门接线
- 从 Stage 4 "用户感知 Aurora 价值接近零" 到 Stage 9 "画像可见、可问、可纠，日常环能接住变化"，有实质跃迁

**用"断点收口"做标尺**：
- 7 个断点已全部收口
- Stage 9 不再存在"画像后端闭环但用户前门缺失"的主要产品断裂
- Stage 13 解决的是"continuous learning 什么时候才配接前门"的制度断裂，而不是再加一个新入口
- Stage 14 解决的是"wire-ready 是否足够可信到接线前"的工程断裂，同时把"还不能接线"的原因从模糊担忧收敛为 source-state 压缩这个明确问题

### 9.15 ✅ Stage 16 完成（能力轨转向 + Memory governed write lane）

**核心问题**：聊天流量 100% 不写 EpisodicMemory，使得 Reflect/Adapt 永远只能拿历史 review/error 等"被结构化过"的事实，无法看见用户当下"未结构化的生活线"。

**Stage 16 总目标**：打通 Memory 写入通道，但**不开放下游消费**（入水但不开闸：水管接通，闸门锁死，下游设施还没建）。

**7-Phase Growth Ring 映射**：

| Phase | Stage 16 后的状态变化 |
|-------|----------------------|
| Sense | 聊天流量首次成为 episodic 记忆来源（受治理） |
| Reflect | 拥有"用户在说什么 / 在意什么"的非结构化信号 |
| Adapt | 拥有"用户最近说了什么"作为决策上下文 |
| Clarify / Plan / Execute / Reinforce | 不变 |

**七个 Workstream（WS-MWL-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-MWL-RULE** | 正式定义 Rule Y（推断式画像写入治理） | confidence + evidence_token + decay_policy + source_lane 四要素；Rule K 子规则 |
| **WS-MWL-READ-VERIFY** | 修复"我以为读了"（MIMO 发现 orchestrator.py 中 Memory 读取仅在 USE_CONTEXT_PACK=True 时发生） | 读不通就不许写；必须新增集成测试 |
| **WS-MWL-EXTRACT** | 推断抽取器（从 chat turn 抽取 episodic 候选） | 不阻塞 streaming；dry-run 一周影子产出；precision ≥ 0.90 |
| **WS-MWL-CONFLICT** | 冲突与去重 | explicit_correction 优先；同语义近邻合并；decay 标记过期不物理删 |
| **WS-MWL-WRITE** | 真正的写入路径 | feature flag default OFF；写入失败静默降级；写入计数指标暴露 |
| **WS-MWL-KILL** | 杀闸 | 只能回滚 inferred_extraction；软删除 revoked_at；≤ 下一次 chat turn 生效 |
| **WS-MWL-MOBILE-DECL** | 移动端声明与撤销 | 画像 front door "AI 自动记忆"区段；全局关闭开关；Rule Q/U 合规 |

**Gate S16-FINAL 验收**：Rule Y 文档落盘 → READ-VERIFY 集成测试 green → EXTRACT dry-run precision ≥ 0.90 → WRITE default OFF 下 baseline 仍 green → KILL 回归测试 green → MOBILE-DECL widget-level 测试 green → 全代码库 grep 验证 inferred_extraction 不出现在任何下游消费路径。

**Path B / C 兜底**：Path B 仅打通 read-verify + kill switch，不开真写入；Path C 若 extract precision < 0.85 则锁死写入、退回 Path B。

**Stage 16 完成状态**：

| 维度 | 结果 |
|------|------|
| baseline | Gate S16-0 144 green + Rule V 8 + Rule K 35/0 |
| backend sweep | 16 green + Stage 13/14/15 carry-forward 24 green |
| mobile sweep | 8 green + Stage 13/15 carry-forward 53 green |
| Rule Y | 正式落盘，四要素 + 7 条硬违规守卫 |
| 下游隔离 | grep 验证 inferred_extraction 未进入 Router/Push/Skill/Accumability |
| 独立审计 | GLM-observer + GLM1 双审计对齐，final-accept 通过 |
| SGW | 以 Pre-launch 语境走 SGW 路径（44 persona + ≥360 session + ≥4000 turn） |

### 9.16 ✅ Stage 17 完成（社交脑 MVP + Accountability seed + Router 只读消费首次开口）

**Stage 17 入场条件（三重锁）**：Stage 16 以 `Pre-launch` 语境走 SGW 路径（≥12h wall-clock + 44 frozen persona + ≥360 会话 + ≥4000 turn + 5 worker cap）+ Rule Y `Hard violation = 0` 且 `Soft violation rate < 5%` + dispatch plan 已落盘并由用户显式宣告 SGW 通过。

**Stage 17 总目标**：把 Stage 16 接通的 Memory 写入车道，第一次连到下游**只读**消费端，并正式确立"用户社交圈在画像系统中的位置"这一被推迟多个 stage 的边界问题。

**7-Phase Growth Ring 映射**：

| Phase | 解锁内容 | 明确不做 |
|-------|---------|---------|
| Sense | 聊天中的人物 / 关系 / 承诺第一次被结构化捕获 | 不引入 LLM 抽取，仍是规则式 |
| Reflect | 承诺到期事实可被前门读到 | 不主动推送 |
| Adapt | Router 可读社交上下文 | Router **不得**以社交事实为决策依据 |

**八个 Workstream（WS-SOC-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-SOC-RULE-Z** | 正式定义 Rule Z（跨用户隐私边界） | HMAC-SHA256(mentioning_user_id‖mentioned_user_id_or_null, normalized_name)；禁止全局 person index；CI 守卫新增跨用户 join grep |
| **WS-SOC-NAMESPACE** | 社交上下文独立命名空间 | person_mention / relationship / commitment 严禁写入 `community_context`；`social_context` 专用 renderer；default OFF |
| **WS-SOC-EXTRACT** | 社交主语分类器 | 规则式分类：self / person_mention / relationship / commitment；不引入 LLM；分类失败不写入；带 async backpressure |
| **WS-SOC-COMMIT** | Commitment 元数据补全 | 必须解析出 due_at；无明确时间锚点不抽取；规则式时间解析 |
| **WS-ACCT-MVP** | Accountability 前门（只读不推送） | Step 0 先做 accountability 健康审计；新 API `GET /memory/accountability/pending`；commitment recall 单独观测 |
| **WS-SOC-ROUTER-READ** | Router 只读上下文窗口 | snapshot ≤ 200 token；仅作为 LLM prompt 上下文；必须跑 ≥30 组 prompt A/B 对照 |
| **WS-SOC-MOBILE** | 前门声明扩展 | "AI 自动记忆"区段增加 subject_type 过滤器；person_mention 标注 Rule Z caveat；4 个子开关 |
| **WS-SOC-KILL** | 子通道 kill switch | 按 subject_type 单独 revoke；≥ 3 条回归测试 |

**Rule 命名表**：

| Rule | 主题 | 引入 Stage | 状态 |
|------|------|------------|------|
| **Rule Y** | 推断式画像写入治理 | Stage 16 | locked |
| **Rule Z** | 跨用户隐私边界 | Stage 17 | locked |
| **Rule AA** | Skill 跨用户共享治理 | Stage 20 | reserved |

**Stage 17 不做清单**：主动推送 → Stage 18；Router 把社交事实作为决策分支 → Stage 19B+；LLM 抽取 → Stage 19A+；Skill 系统读 Memory → Stage 20；cross-user 数据流动 → 永不。

**Path A/B/C 兜底**：

| Path | 触发条件 | 必须保留 WS | 可延后到 Stage 18 |
|------|----------|-------------|-------------------|
| **A** | Stage 16 SGW 完成 + Rule Y `Hard violation = 0` + `Soft violation rate < 5%` | 全 8 WS | — |
| **B1** | scope 风险（任一 WS 在验收时未达标） | RULE-Z + NAMESPACE + EXTRACT + ACCT-MVP | COMMIT / ROUTER-READ / MOBILE / KILL |
| **B2** | SGW precision 跌至 < 0.85 | RULE-Z + NAMESPACE + EXTRACT(person_mention only) | COMMIT / ACCT-MVP / ROUTER-READ / MOBILE / KILL |
| **C** | Rule Y 破例 / Router 字段进决策分支 / Rule Z hash 设计被绕 | 立即停 Stage 17 | 全部 |

**Gate S17-FINAL 验收**：Rule Z 文档 + CI 守卫升级 → `WS-SOC-NAMESPACE` 先于 EXTRACT / ROUTER-READ green → Alembic migration apply → backend sweep ≥ 14 → mobile sweep ≥ 6 → Router A/B 报告落盘 → commitment recall 观测完成 → 全代码库 grep 验证 `subject_type` / `social_context` / `RouterContextReader` / `recent_person_mentions` 无越界消费。

**Stage 17 完成状态**：

| 维度 | 结果 |
|------|------|
| baseline | Gate S17-0 144 green + Rule V 8 + Rule K/Z 0 violation |
| backend sweep | 27 green（Rule Z guard / namespace isolation / subject_type extraction / commitment parser / accountability MVP / router context reader / social kill / inferred write lane） |
| mobile sweep | 51 green（memory features + home features） |
| carry-forward | Stage 13-16 backend 28 green |
| Rule Z | 正式落盘，HMAC-SHA256 边界 + CI 守卫 + 5 个禁止场景 |
| Social namespace | `social_context` 独立于 `community_context`，prompt 渲染 bounded + default OFF |
| Accountability | overdue commitments 前门可见 + resolved/dismiss 动作，无 push |
| Router seam | `SocialContextProvider → FrozenSocialSnapshot` 契约建立，Stage 18 可迁移 |
| 独立审计 | 8 WS 全部 accept，handoff 为 final 状态 |

### 9.17 ✅ Stage 18 完成（State Aggregator 单一状态源 + 确定性 push 环）

**Stage 18 入场条件（三重锁）**：Stage 17 全 8 WS green + 至少一周生产灰度 + Rule Z 无破例 + Accountability MVP 用户 resolve/dismiss 行为有真实数据样本（≥ 50 条事件）。

**Stage 18 总目标**：把 Stage 17 的社交与承诺只读 seam 转化为受治理的单一状态源层，并用该层驱动首个确定性主动触达环。State Aggregator 负责聚合多源信号生成 `user_state.v1`，确定性 push 基于状态变化触发有证据支撑的提醒。

**八个 Workstream（WS-SA-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-SA-RULE-AB** | 正式定义 Rule AB（push 治理） | evidence-backed + daily cap + quiet-hours + retraction |
| **WS-SA-CORE** | frozen `user_state.v1` + pull-only Aggregator 服务 | 无 write-back 到 L0/L1；protobuf mirror |
| **WS-SA-ROUTER-MIGRATE** | Router 从 Stage 17 直连迁移至 Aggregator-backed provider | 保持 `SocialContextProvider` 公共合约不变；20 组冷场景等价验证 |
| **WS-SA-PUSH-POLICY** | 确定性 push policy compiler | 模板冻结、日频上限、静默时段调度；无 LLM free-text |
| **WS-SA-PUSH-CHANNEL** | push 投递通道 + WebSocket channel | 投递记录、可撤回窗口、投递侧冗余守卫 |
| **WS-SA-MOBILE** | opt-in + 分类控制 + inbox | default OFF、分类开关、触发证据展示 |
| **WS-SA-KILL** | 三级 kill switch | 单策略 / 全局 / Aggregator 层级独立关停 |

**新增治理规则**：**Rule AB**（Stage 18 新建）：push 治理——每条 push 必须有触发证据、受日频上限约束、支持静默时段、可撤回。

**Stage 18 硬边界**：
1. Aggregator pull-only：无 write-back 到 L0/L1 源数据
2. Push 确定性：模板绑定，无 LLM free-text 生成
3. Opt-in default OFF：所有 Stage 18 push 需用户显式开启
4. 禁止类目：emotion / motivation / social pressure / new-goal proposal 不可触发

**Stage 18 完成状态**：

| 维度 | 结果 |
|------|------|
| baseline | Gate S18-0 97 green（Aurora baseline） |
| backend sweep | 42 green（schema / aggregator / router migrate / push policy / push delivery / kill switch / state-driven push / memory settings / memory admin） |
| mobile sweep | 2 direct + carry-forward（memory_settings_screen + unified_notification_push_card） |
| Stage 17 carry-forward | 4 green（Rule Z guard + namespace isolation） |
| Rule AB | 正式落盘 |
| Router 迁移 | `AggregatorBackedSocialContextProvider` 保持 Stage 17 公共合约，20 组冷场景等价 |
| 独立审计 | GLM1 审计结论：8 commits 原子拆分 + hard boundary 四条全过 + handoff final |

**Stage 19 义务锁定**：19A Working Memory 必须消费 Aggregator 的 `engagement_state` / `commitment_summary`，不得自建平行层；19B 扩展 Router 消费前需通过 sufficiency governance。

### 9.18 ✅ Stage 19 完成（Working Memory + LLM 抽取 dry-run pipeline + Rule AC）

**Stage 19 入场条件**：Stage 18 全部 WS green + Aggregator 在生产流量下有至少一周稳定运行 + Rule AB 无破例。

**Stage 19 总目标**：引入 Working Memory 作为对话级短期记忆层（Redis-only，无持久化），并落地 LLM 抽取 dry-run pipeline 作为规则式抽取的精度提升路径。Stage 19 采用"pipeline 协调"模式——`WorkingMemoryPipelineService` 统一协调规则式与 LLM 两条抽取路径，去重在 Working Memory 层完成。

**七个 Workstream（WS-WM-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-WM-RULE-AC** | 正式定义 Rule AC（Working Memory 治理） | Redis-only / 无 SQL / 无 Alembic / consolidation 不触发 push |
| **WS-WM-CORE** | Working Memory 核心服务 | 对话级上下文管理，TTL 生命周期 |
| **WS-WM-LLM-DRY-RUN** | LLM 抽取 dry-run pipeline | Rule Y 四要素对账；banned inferences 含 emotion/mood/personality；prompt 白名单守卫 |
| **WS-WM-CONSOLIDATE** | Working Memory consolidation 流程 | explicit confirmation 检测有时间邻近约束；不触发 push（grep guard 0 命中） |
| **WS-WM-AGGREGATOR-INTEGRATE** | Working Memory 接入 Aggregator schema | Aggregator v1.1 升级，新增 `working_memory_snapshot`；proto-gen clean + KL ≤ 0.03 |
| **WS-WM-MOBILE** | Working Memory 透明度 | 用户可查看 WM 快照内容，6 widget tests |
| **WS-WM-KILL** | 三级 kill switch | working_memory / llm_extractor / consolidation 独立可杀 |

**Stage 19 硬边界**：
1. Working Memory 仅 Redis 存储——grep guard 验证 models/alembic 零命中
2. LLM 抽取走 Rule Y 四要素——InferredEpisodicCandidate 对账 + dry-run
3. Consolidation 不触发 Push——grep guard 0 命中
4. Aggregator 只读——Rule AB guard passed

**Stage 19 完成状态**：

| 维度 | 结果 |
|------|------|
| commits | 8 原子提交，按 WS 边界拆分 |
| backend tests | 24 passed |
| mobile tests | 6 passed（widget） |
| Rule AC/AB/K 三重 guard | 全部 passed |
| Aggregator schema | v1.1 升级，向后兼容（KL ≤ 0.03） |
| proto-gen | clean |
| 独立审计 | GLM1 accept clean，无 carry-forward debt |

**Stage 20 义务锁定**：Gate S20-0 前置条件（Stage 19 final-accept）已满足，Stage 20 dispatch 可直接交付执行。

### 9.19 ✅ Stage 20 完成（Sufficiency Judge + Conflict Resolver + Route History + 治理层强化）

****Stage 20 入场条件**：Stage 19 全部 WS green + Working Memory 在生产流量下有至少一周稳定运行 + Rule AC 无破例。

**Stage 20 总目标**：建立路由决策的治理基础设施——Sufficiency Judge 判断信息是否足够支撑决策、Conflict Resolver 处理多源冲突的优先级仲裁、Route History 记录决策日志供后续审计。Stage 20 不涉及 Skill 蒸馏（原规划延后），而是为 Stage 21 Skill MVP 铺设决策治理地基。

**七个 Workstream**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-S1** | Sufficiency Judge 核心 | 纯规则式加权算术，零 LLM import；judge_version="v1" frozen |
| **WS-S2** | task/context split | Router 仅在 task_sufficiency 分支决策，context_sufficiency 仅输出不参与路由（Rule AD） |
| **WS-C1** | Conflict Resolver 优先级链 | frozen immutable：working_memory(1) < llm(2) < rule(3) < explicit(4) |
| **WS-C2** | Shadow mode | 并行比较非替换，record_shadow_comparison() 记录两路结果 |
| **WS-H1** | Route History 写入 | write-only 决策日志，零 read-for-routing 方法 |
| **WS-H2** | outcome backfill | mark_timeout() / record_follow_up_input() / record_explicit_feedback() 通过 decision_id 单行更新 |
| **WS-Audit** | Alembic + CI guard | 4 张审计表 + Rule AD/AE 两个 CI 守卫脚本 |

**新增治理规则**：
- **Rule AD**：task/context split 治理——Router 仅在 task_sufficiency 分支决策，context_sufficiency 不得参与路由分支
- **Rule AE**：conflict audit——每次 override 必须伴随 conflict_resolution_records 审计
- **Rule AF**（Stage 21 预留）：Skill 跨用户共享治理

**Stage 20 硬边界**：
1. Sufficiency Judge 纯规则式——CI guard 扫描零 LLM import
2. task/context split——Rule AD CI guard 扫描无 context_sufficiency 分支
3. Conflict Resolver 优先级链 frozen——immutable dict，无动态变更
4. Aggregator 只读不变——Rule AB guard maintained

**Stage 20 完成状态**：

| 维度 | 结果 |
|------|------|
| commits | 3 原子提交 |
| workstreams | 7 全部 PASS（WS-S1/S2/C1/C2/H1/H2/Audit） |
| governance | Rule AD/AE/AC/AB/Y 全部 enforced/preserved/extended |
| carry-forward | Stage 17 handoff 升级为 closeout baseline，Rule Z HMAC 升级注释补齐 |
| 独立审计 | GLM1 accept clean，无 carry-forward debt |

**Stage 21 义务锁定**：Sufficiency Judge + Conflict Resolver + Route History 全部落地，Stage 21 Skill MVP 前置条件已满足。Rule AF 锁定为 Skill 跨用户共享治理位。

### 9.20 ✅ Stage 21 完成（Skill 知识蒸馏管道 + Rule AF）

**Stage 21 入场条件**：Stage 20 全部 WS green + Route History 已积累足够可信样本。

**Stage 21 总目标**：从"持续学习"升级为"知识蒸馏"——从用户成功案例中提取可复用 Skill，并支持跨用户共享（需用户显式授权，受 Rule AF 治理）。

**八个 Workstream（WS-SK-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-SK-RULE-AF** | Rule AF 定义 | numbered-history + frozen prompts + trigger keyword + CI guards |
| **WS-SK-SCHEMA** | Skill V1 schema | user_skills / shared_skills + moderation queue + 50-item cap |
| **WS-SK-EXTRACT** | Skill 提取器 | explicit-trigger-only + keyword matcher + user-confirmed draft |
| **WS-SK-SELECTION** | Skill 选择器 | Aggregator 暴露 metadata + Router prompt-only injection |
| **WS-SK-SHARE** | 跨用户共享 | private-vs-shared 物理隔离 + PII check + anonymous publish |
| **WS-SK-MOBILE** | 移动端 UI | profile 入口 + "我的方式" manager + shared catalog |
| **WS-SK-KILL** | 杀闸 | Store / Selection / Share 三级独立可杀 |

**新增治理规则**：**Rule AF**（Stage 21 新建）：Skill 跨用户共享治理。

**Stage 21 完成状态**：

| 维度 | 结果 |
|------|------|
| commits | 8 原子提交 |
| backend sweep | 31 passed |
| mobile sweep | 6 passed |
| Rule AF | 正式落盘，四要素 + 5 条硬违规守卫 |
| Skill 物理隔离 | content 分离于 Aggregator state，summaries 进 `user_state.v1.3` |
| 共享机制 | opt-in per skill + anonymous + fork snapshot |
| 独立审计 | GLM1 accept clean |

### 9.21 ✅ Aurora 路线图 v2.2 锁定（Stage 22-32）

**v2.2 生效日期**：2026-04-21

**总览**：11 阶段 / 54 WS / 10 条规则（AG-AP）/ 4 条跨 Stage 基线（B1-B4）

| 阶段 | 主题 | WS 数 | 定性 | 关键规则 | 状态 |
|------|------|-------|------|----------|------|
| 22 | Baseline Repair | 6 | 修复 | AG | ✅ closeout |
| 23 | Bayesian Wire-On | 6 | 重构 | AH | ✅ closeout |
| 24 | Accountability Policy Compiler | 4 | 新增 | AI | ✅ closeout |
| 25 | Reflection Wire-On | 5 | 扩展 | AJ | ✅ closeout |
| 26 | Scene Consolidation | 5 | 新增 | AK | ✅ closeout |
| 27 | Foresight Engine | 5 | 扩展+新增 | AL | ✅ closeout |
| 28 | Traits 弱先验 | 5 | 扩展+新增 | AM | ✅ closeout |
| 29 | SRL 三阶段独立 Tracker | 6 | 重构+新增 | AN | ✅ closeout |
| 29.5 | Repo Hygiene | 6 | 卫生 | AQ | ✅ closeout |
| 30 | Metacognition 扩展 | 4 | 扩展 | AO | 🔶 in progress |
| 30 | Metacognition 扩展 | 4 | 扩展 | AO | ❌ pending |
| 31 | Idiographic Lite | 4 | 扩展+新增 | AP | ❌ pending |
| 32 | CL SQAM 扫尾 | 4 | 测量 | 复用 W | ❌ pending |

**规则锁定表**（Stage 22-32）：

```
AG  Baseline 前置       —— Stage 22 ✅
AH  source-state 维度登记 —— Stage 23 ✅ closeout
AI  Policy Compiler 纯规则 —— Stage 24 ✅ closeout
AJ  Reflection 消费隔离   —— Stage 25 ✅ closeout
AK  Scene 合并幂等 + 算法约束 —— Stage 26 ✅ closeout
AL  Foresight 非 Router 分支 —— Stage 27 ✅ closeout
AM  Traits 置信度 ≤0.3 + 冲突优先级 —— Stage 28 ✅ closeout
AN  SRL 解耦（EventBus + Aggregator）—— Stage 29 ✅ closeout
AQ  Proto/Python 同步    —— Stage 29.5 ✅ closeout
AO  Metacognition 禁诊断词 —— Stage 30 🔶 in progress
```
AJ  Reflection 消费隔离   —— Stage 25
AK  Scene 合并幂等 + 算法约束 —— Stage 26
AL  Foresight 非 Router 分支 —— Stage 27
AM  Traits 置信度 ≤0.3 + 冲突优先级 —— Stage 28
AN  SRL 解耦（EventBus + Aggregator）—— Stage 29
AO  Metacognition 禁诊断词 —— Stage 30
AP  Idiographic 仅关联不因果 —— Stage 31
```

**跨 Stage 基线**（Stage 22 完成后、Stage 23 启动前必须建立）：

| 基线 | 来源 | 锁定内容 |
|------|------|----------|
| B1 Aggregator schema 漂移控制 | GLM1 风险 1 | 每次 schema bump 必走 proto-gen 三端传播 + backward compat 测试 |
| B2 EventBus 负载基线 | GLM1 风险 2 | 当前 120+ event types 基线测量；新增 event type 前须验证 consumer lag |
| B3 LLM 调用预算 | GLM1 风险 3 | 每请求 LLM 调用次数上限登记；p95 延迟与成本回归测试 |
| B4 跨 Stage 数据质量门 | GLM1 风险 4 | Stage 25/27/29 启动前须验证其上游 Stage 产出数据质量 |

**快速开发模式**：
- Codex 按 v2.2 执行
- GLM1 + GLM-observer 阶段性验收
- 首席架构师不参与每次 gate_final
- 仅以下情形触发人工介入：
  1. GLM1 与 GLM-observer 判断冲突
  2. 发现需新增或修改规则
  3. Stage 23 / Stage 29 任一 shadow 数据偏离预期 >20%
  4. 跨 Stage 基线 B1-B4 任一项回归失败

**Stage 22 义务锁定**：Skill 全链路落地，Stage 22 Bayesian Wire-On 前置条件已满足。

### 9.22 ✅ Stage 22 完成（Baseline Repair）

**Stage 22 入场条件**：Stage 21 全部 WS green + Rule AF 无破例。

**Stage 22 总目标**：修复"AI 可见度"基线——将"AI 可见"从 3-4/10 拉到 ≥ 7/10，为后续 Bayesian / Reflection / Foresight / Traits / SRL 组件建立可信的数据供给管道。

**六个 Workstream（WS-BR-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-BR-PROMPT-VERIFY** | prompt 渲染覆盖率验证 | 检查achievement/calendar/intervention/error_replan 是否真正进入 prompt |
| **WS-BR-LOOP-CLOSURE** | 闭环断裂修复 | achievement/calendar → AI prompt 通道打通 |
| **WS-BR-ACHIEVEMENT-WIRE** | Achievement → AI | completion → milestone_achieved → prompt 注入 |
| **WS-BR-CALENDAR-WIRE** | Calendar → AI | calendar_event → upcoming_deadline → prompt 注入 |
| **WS-BR-INTERVENTION-Q** | Intervention 质量 | feedback collection → outcome backfill |
| **WS-BR-SEED-VERIFY** | 种子验证闭环 | seed 验证数据真实性 + backfill 策略 |

**新增治理规则**：**Rule AG**（Stage 22 新建）：Baseline 修复前禁止任何新消费者上线。

**GLM1 独立验收**：ACCEPT - CLEAN

| 验证项 | 结果 |
|--------|------|
| WS-BR-PROMPT-VERIFY | PASS（覆盖率 0.909，10/11 字段已渲染）|
| WS-BR-ACHIEVEMENT-WIRE | PASS（成就→AI 只读单向） |
| WS-BR-CALENDAR-WIRE | PASS（日历扩展 3 新字段） |
| WS-BR-LOOP-CLOSURE | PASS（触发器 6 种 + cooldown 24h + Celery） |
| WS-BR-INTERVENTION-Q | PASS（cohort_profile 补全） |
| WS-BR-SEED-VERIFY | PASS（adoption_id + 闭环 + 撤回） |
| Backend tests | 30+ passed |
| Mobile tests | 7+ passed |

### 9.23 ✅ Stage 23 完成（Bayesian Wire-On）

**Stage 23 入场条件**：Stage 22 全部 WS green + Rule AG 无破例。

**Stage 23 总目标**：将 Bayesian 推荐从 shadow 模式正式接入 Router——通过三层 rollout（off/shadow/live_canary）实现渐进式上线。

**六个 Workstream（WS-BY-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-BY-SOURCE-STATE-DESIGN** | 多维 source-state 设计 | 7 维 + Rule AH registry + 128 budget |
| **WS-BY-SOURCE-STATE-IMPL** | Learner 消费多维 state | backfill + SQAM 重跑 |
| **WS-BY-WIRE** | 三档 rollout | off/shadow/live_canary |
| **WS-BY-OUTCOME** | outcome 规范化 backfill | 6 canonical types |
| **WS-BY-KILL** | Redis kill-switch | fallback to off |
| **WS-BY-DATA-BOOTSTRAP** | 合成数据集 | 3 users × 150 pairs × 7 dims |

**新增治理规则**：**Rule AH**（Stage 23 新建）：source-state 维度登记。

**GLM1 独立验收**：ACCEPT - CLEAN

| 验证项 | 结果 |
|--------|------|
| WS-BY-SOURCE-STATE-DESIGN | PASS（7 维 + 128 budget）|
| WS-BY-SOURCE-STATE-IMPL | PASS（Learner 消费 + TTL 7d→30d）|
| WS-BY-WIRE | PASS（off/shadow/live_canary 三档）|
| WS-BY-OUTCOME | PASS（6 outcome types）|
| WS-BY-KILL | PASS（Redis override）|
| WS-BY-DATA-BOOTSTRAP | PASS（3×150×7）|
| Guards | 3/3 PASS |
| Tests | 49 passed |

**实现路径**：Path B（infrastructure wired, default off, shadow/canary controlled rollout）

**Stage 24 义务锁定**：Stage 23 Bayesian Wire-On 已落地，Stage 24 Accountability Policy Compiler 可启动。

### 9.24 ✅ Stage 24 完成（Accountability Policy Compiler）

**Stage 24 入场条件**：Stage 23 全部 WS green + Rule AH 无破例。

**Stage 24 总目标**：实现"关系→行为约束"编译——从 accountability_partnership 表读取承诺状态，编译为 intervention 触发条件（纯规则，无 LLM）。

**四个 Workstream（WS-AP-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-AP-IR** | 承诺数据提取 | partnership 表读取 + 状态解析 |
| **WS-AP-COMPILER** | 规则编译器 | 纯规则，无 LLM |
| **WS-AP-SCHEDULER** | 触发调度 | Celery beat 可执行 |
| **WS-AP-GUARD** | 治理守卫 | 强制串行 |

**新增治理规则**：**Rule AI**（Stage 24 新建）：Policy Compiler 纯规则，禁 LLM。

**GLM1 独立验收**：ACCEPT - CLEAN

**实现路径**：Path A（full implementation, default off）

**Stage 25 义务锁定**：Stage 24 Accountability Policy Compiler 已落地，Stage 25 Reflection Wire-On 可启动。

### 9.25 ✅ Stage 25 完成（Reflection Wire-On）

**Stage 25 入场条件**：Stage 24 全部 WS green + Rule AI 无破例。

**Stage 25 总目标**：将 route_history 从"纯写"变为"写+读"，消费 route_history 做反思触发。

**五个 Workstream（WS-RF-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-RF-READ-API** | route_history 读 API | user_id 强隔离 |
| **WS-RF-USER-CONTEXT** | ReflectionAgent user_id 签名 | assertion guard |
| **WS-RF-INJECT** | route_history 证据注入 | token budget ≤800 |
| **WS-RF-TRIGGER** | 6 类触发 | 新增 3 类 |
| **WS-RF-QUALITY** | Rule Y 验证 + 降级 | 3 连 <95% → shadow |

**新增治理规则**：**Rule AJ**（Stage 25 新建）：Reflection 消费隔离。

**GLM1 独立验收**：ACCEPT - CLEAN

| 验证项 | 结果 |
|--------|------|
| WS-RF-READ-API | PASS（user_id 隔离）|
| WS-RF-USER-CONTEXT | PASS（assertion guard）|
| WS-RF-INJECT | PASS（token budget）|
| WS-RF-TRIGGER | PASS（6 类）|
| WS-RF-QUALITY | PASS（自动降级）|
| Aggregator v1.6 | PASS |
| Tests | 50 backend + 3 mobile |

**实现路径**：Path A（full implementation, default off）

**Stage 26 义务锁定**：Stage 25 Reflection Wire-On 已落地，Stage 26 Scene Consolidation 可启动。

### 9.26 ✅ Stage 26 完成（Scene Consolidation）

**Stage 26 入场条件**：Stage 25 全部 WS green + Rule AJ 无破例。

**Stage 26 总目标**：将零散的 EpisodicMemory 聚合为 Scene——提供时间维度的高层次抽象。

**五个 Workstream（WS-SC-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-SC-MODEL** | Scene 模型 | scene_id + member_memory_ids + time |
| **WS-SC-CLUSTER** | 聚类算法 | cosine + 时间窗口，禁 K-means |
| **WS-SC-QUALITY** | 质量评分 | 0.35×member + 0.45×cohesion + 0.20×time |
| **WS-SC-AGGREGATOR** | Aggregator v1.7 | recent_scenes |
| **WS-SC-KILL** | 杀闸 | off/shadow/live + 自动降级 |

**新增治理规则**：**Rule AK**（Stage 26 新建）：Scene 合并幂等 + 算法约束。

**GLM1 独立验收**：ACCEPT - CLEAN

| 验证项 | 结果 |
|--------|------|
| WS-SC-MODEL | PASS（Alembic migration）|
| WS-SC-CLUSTER | PASS（cosine + time window）|
| WS-SC-QUALITY | PASS（公式 + 幂等）|
| WS-SC-AGGREGATOR | PASS（v1.7 + proto）|
| WS-SC-KILL | PASS（自动降级）|
| Tests | 46 backend + 3 mobile |

**Carry-forward**：Scene 缺 evidence_token（可选补）——member_memory_ids 已实现治理意图

**Stage 27 义务锁定**：Stage 26 Scene Consolidation 已落地，Stage 27 Foresight Engine 可启动。

### 9.27 ✅ Stage 27 完成（Foresight Engine）

**Stage 27 入场条件**：Stage 26 全部 WS green + Rule AK 无破例。

**Stage 27 总目标**：利用已存在的 PredictiveService 扩展 Foresight Engine——PersDyn attractor + deviation detection + JITAI trigger。

**五个 Workstream（WS-FS-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-FS-EXTEND** | PredictiveService 扩展 | build_foresight_snapshot() |
| **WS-FS-ATTRACTOR** | PersDyn attractor | baseline/variability/recovery |
| **WS-FS-DEVIATION** | 行为偏离预测 | 阈值检测 |
| **WS-FS-JITAI** | JITAI 触发 | 模板 + rate counter |
| **WS-FS-GUARD** | 治理守卫 | Rule AL 零 Router 分支 |

**新增治理规则**：**Rule AL**（Stage 27 新建）：Foresight 输出仅供提示，不得进入 Router 分支。

**GLM1 验收**：ACCEPT - CLEAN（Path A 全量实现）

| 验证项 | 结果 |
|--------|------|
| WS-FS-EXTEND | PASS（build_foresight_snapshot）|
| WS-FS-ATTRACTOR | PASS（PersDyn）|
| WS-FS-DEVIATION | PASS（偏离检测）|
| WS-FS-JITAI | PASS（模板 + auto-downgrade）|
| WS-FS-GUARD | PASS（零 Router 分支）|
| Backend tests | 56 passed |
| Mobile tests | 3 passed |
| Proto sync | PASS |
| Bug fix | JITAI rate counter → RATE_RETENTION_DAYS=4 |

**实现路径**：Path A（full implementation, default off）

**Stage 28 义务锁定**：Stage 27 Foresight Engine 已落地，Stage 28 Traits 弱先验可启动。

### 9.28 ✅ Stage 28 完成（Traits 弱先验）

**Stage 28 入场条件**：Stage 27 全部 WS green + Rule AL 无破例。

**Stage 28 总目标**：在已有 UserInsightState 基础上新增 Big Five 层 Traits——置信度上限 0.3。

**五个 Workstream（WS-TR-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-TR-MODEL** | Traits 模型 | Big Five + 置信度 ≤0.3 |
| **WS-TR-NLP-OBSERVE** | NLP 观察 | 跨文化基线校准 |
| **WS-TR-COLDSTART** | 冷启动 3 问 | 用户主动提供 |
| **WS-TR-AGGREGATOR** | Aggregator v1.9 | traits_summary |
| **WS-TR-GUARD** | 治理守卫 | 置信度 + 冲突优先级 |

**新增治理规则**：**Rule AM**（Stage 28 新建）：Traits 置信度 ≤0.3 + 冲突时 Dynamic States 优先。

**GLM1 验收**：ACCEPT - CLEAN（Path A 全量实现）

**Stage 29 义务锁定**：Stage 28 Traits 弱先验已落地，Stage 29 SRL Tracker 可启动。

### 9.29 ✅ Stage 29 完成（SRL 三阶段独立 Tracker）

**Stage 29 入场条件**：Stage 28 全部 WS green + Rule AM 无破例。

**Stage 29 总目标**：将 SRL（Self-Regulated Learning）阶段追踪从耦合转为独立服务——通过 EventBus 解耦。

**六个 Workstream（WS-SR-*)**：

| WS | 目的 | 关键约束 |
|----|------|----------|
| **WS-SR-MODEL** | SRL 阶段状态机 | forethought/performance/reflection |
| **WS-SR-TRACKER** | 独立 SRLPhaseTracker | 订阅 EventBus |
| **WS-SR-EVENT-BRIDGE** | EventBus 集成 | SRLPhaseTransitionEvent |
| **WS-SR-SCAFFOLDING-EXTEND** | Scaffolding FSM | 消费阶段调整 support_level |
| **WS-SR-AGGREGATOR** | Aggregator v1.10 | srl_phase_summary |
| **WS-SR-GUARD** | 治理守卫 | Rule AN/AL 零冲突 |

**新增治理规则**：**Rule AN**（Stage 29 新建）：SRL 阶段状态经 EventBus + Aggregator 解耦。

**GLM1 验收**：ACCEPT - CLEAN（Path A 全量实现）

| 验证项 | 结果 |
|--------|------|
| Backend tests | 73 passed |
| Mobile tests | 6 passed |
| EventBus throughput | 24693.97 events/min |
| Lag p95 | 0.17s |
| Proto sync | PASS |

**实现路径**：Path A（full implementation）

**Note**：目标环境上线前需应用 Stage 28/29 migration 到目标库。

### 9.29.5 ✅ Stage 29.5 完成（Repo Hygiene）

**Stage 29.5 入场条件**：Stage 29 全部 WS green。

**Stage 29.5 总目标**：基础设施卫生检查——Proto 同步 + CI guards + Alembic 链完整。

**六项并行验证**：

| WS | 目的 | 结果 |
|----|------|------|
| **WS-HG-PROTO-SYNC** | 3 proto 字段 + 11 消息类型 | ✅ PASS |
| **WS-HG-CI-GUARDS** | 17 条规则 + manifest + CI 集成 | ✅ PASS |
| **WS-HG-RULE-Y-AG-GUARDS** | AST 级别 guard | ✅ PASS |
| **WS-HG-AB-EXEMPTION** | Rule AB 白名单强制 | ✅ PASS |
| **WS-HG-MIGRATION-FILL** | Alembic 链完整 | ✅ PASS |
| 测试计数 | 78 backend 精确匹配 | ✅ PASS |

**GLM1 验收**：ACCEPT - CLEAN

**移交事项**：⚠️ 未提交更改——必须在进入 Stage 30 之前提交
- Proto 扩展 + 生成的 pb2 文件
- 17 个 guard 脚本 + manifest + runner
- 2 个无操作迁移 + 1 个合并迁移
- CI yml 集成
- 78+ 新测试文件

**Stage 30 义务锁定**：Stage 29.5 repo hygiene 已验证 + 更改已提交，Stage 30 Metacognition 扩展可启动。

### 9.30 依赖链（v2.2 锁定，不可打乱顺序）

```
Memory Write (Stage 16 ✅)
    ↓
Social Brain + Accountability + Router Read-Only (Stage 17 ✅)
    ↓
State Aggregator + State-Driven Push (Stage 18 ✅)
    ↓
LLM Extraction + Working Memory (Stage 19 ✅)
    ↓
Sufficiency Governance + Conflict Resolution + Route History (Stage 20 ✅)
    ↓
Skill Distillation + Rule AF (Stage 21 ✅)
    ↓
Baseline Repair (Stage 22 ✅) ← 已 closeout
    ↓
Bayesian Wire-On (Stage 23 ✅) ← 已 closeout
    ↓
Accountability Policy Compiler (Stage 24 ✅) ← 已 closeout
    ↓
Reflection Wire-On (Stage 25 ✅) ← 已 closeout
    ↓
Scene Consolidation (Stage 26 ✅) ← 已 closeout
    ↓
Foresight Engine (Stage 27 ✅) ← 已 closeout
    ↓
Traits 弱先验 (Stage 28 ✅) ← 已 closeout
    ↓
SRL 三阶段独立 Tracker (Stage 29 ✅) ← 已 closeout
    ↓
Metacognition 扩展 (Stage 30 🔶) ← 当前执行
    ↓
Metacognition 扩展 (Stage 30)
    ↓
Idiographic Lite (Stage 31)
    ↓
CL SQAM 扫尾 (Stage 32)
```

**硬约束**：任何 Stage 试图跳跃依赖链上游未完成的 Stage，默认拒绝。

### 9.25 显式延后挂牌更新（v2.2 锁定后）

| 项目 | 来源 | 状态 | 下一归属 |
|------|------|------|----------|
| RB1 tokenizer-aware inline budget | WS-RP1 精度尾债 | deferred | Stage 22+ candidate |
| evidence type 扩展（WS-EVD3 full） | Stage 13 仅落了 `practice_outcome` lite | deferred | Stage 22+ candidate |
| graph diagnostic 从 chat card 深化为完整 Galaxy 诊断面 | WS-G2D 深化 | deferred | Stage 22+ candidate |
| APNs / FCM 真实设备推送 | Stage 18 仅 WebSocket channel | deferred | 真实用户上线阶段 |
| Aggregator event-driven fan-out | Stage 18 仅 pull-only | deferred | Stage 22+ candidate |
| LLM 抽取正式接线（从 dry-run 升级为 live） | Stage 19 仅 dry-run | deferred | Stage 22+ candidate |
| Router 扩展消费（sufficiency governance） | Stage 17/18/19 仅读不决策 | deferred | Stage 22+ |
| Skill 跨用户共享 | 长期愿景 | deferred | ✅ Stage 21 已落盘 |
| AI 可见度基线修复 | v2.2 | 🔶 Stage 22 执行中 | Stage 23 |
| Bayesian Wire-On | v2.2 | ❌ Stage 23 | Stage 24 |
| 双交互模式 | 长期愿景 | deferred | Stage 23+ |
| 成长操作系统 | 长期愿景 | deferred | Stage 32+ |

### 9.24 愿景锚点 vs 当前覆盖更新（v2.2 锁定后）

| 愿景锚点 | 覆盖度 | 说明 |
|----------|--------|------|
| Aurora 异步化 | ✅ Stage 4 | 三时层 substrate + 路由分流 |
| 对话分流 | ✅ Stage 4 | 三路 routing_mode + 会话中途升级 |
| TaskGuidance 双版本 | ✅ Stage 4 | sidecar + UI |
| 任务助手降级 | ✅ Stage 4 | 单核 + 5 项注入 + dormant |
| 5-P 宪法执行 | ✅ Stage 4-8 | P1-P5 全部绿色 |
| 用户模型五层架构 | ✅ Stage 6-10 | Rule K + 影子模型 + compiler 归一 + evaluator + CI guard + chat front door + judge/evidence deepen |
| 交互式校准 | ✅ Stage 7-10 | 后端环 + 前端消费 + fallback telemetry + in-chat query/correction + clickable evidence |
| 7 个产品断点 | ✅ Stage 8 | #1/#2/#3/#4/#5/#6 + 干预语言全部收口 |
| 数据泄漏修复 | 🔶 部分 | 渲染管线已修（WS-RP1）；utilization 已可观测，但 tokenizer-aware 精度尾债仍在 |
| 双核协作闭环 | 🔶 0.6/1 | Stage 5 建了一条通路，非完整双向 |
| graph-as-diagnostic | ✅ Stage 10 | chat-native "我哪里弱" 诊断面已落地；Galaxy 专页深化仍可继续 |
| 持续学习三层结构 | ✅ Stage 16 | Memory governed write lane 打通；Rule Y 落盘 |
| 社交脑 | ✅ Stage 17 | Rule Z 落盘；social_context namespace 独立 |
| 主动推送 | ✅ Stage 18 | State Aggregator + State-Driven Push |
| LLM 辅助抽取 | ✅ Stage 19 | Working Memory + dry-run pipeline |
| Sufficiency + Conflict + History | ✅ Stage 20 | Rule AD/AE 落盘 |
| 知识蒸馏 | ✅ Stage 21 | Rule AF + Skill Store |
| AI 可见度基线修复 | ✅ Stage 22 | closeout（prompt 覆盖率 0.909） |
| Bayesian Wire-On | ✅ Stage 23 | closeout（6 WS + Path B 三档 rollout） |
| Accountability Policy Compiler | ✅ Stage 24 | closeout（纯规则） |
| Reflection Wire-On | ✅ Stage 25 | closeout（6 类 trigger） |
| Scene Consolidation | ✅ Stage 26 | closeout（cosine + time window） |
| Foresight Engine | ✅ Stage 27 | closeout（PersDyn + JITAI） |
| Traits 弱先验 | ✅ Stage 28 | closeout（Big Five + 置信度 ≤0.3） |
| SRL Tracker | ✅ Stage 29 | closeout（EventBus 解耦） |
| Metacognition 扩展 | 🔶 Stage 30 | 当前执行 |
| SRL Tracker | ❌→Stage 29 | 路线图已锁定 |
| Metacognition 扩展 | ❌→Stage 30 | 路线图已锁定 |
| Idiographic Lite | ❌→Stage 31 | 路线图已锁定 |
| CL SQAM 扫尾 | ❌→Stage 32 | 路线图已锁定 |

---

## 十、核对机制

### 10.1 派卡前核对

每次派发新卡之前，检查：
1. 这张卡在为哪个愿景锚点铺路？
2. 如果和所有锚点都对不上，是否有明确理由？
3. 是否在推进 7 阶段成长环中的某个阶段？
4. 是否违反 §7.2 不做清单中的任何一条？
5. 是否违反 5-P 宪法中的任何一条？

### 10.2 阶段验收核对

每个 Stage 收尾时，检查：
1. 用户在 7 阶段环里被推进了几步？
2. 数据利用的四层比例是否提升？
3. 6 个断点中有几个被修复？
4. 双核协作是否有新的闭合实例？
5. P1-P5 宪法的可验证条件是否全部满足？
6. 所有 Wave 的测试基线是否绿色？

### 10.3 战略漂移检测

当三个工程专家（Claude / Codex / GLM-observer）在某件事上达成一致，但与本清单中的愿景锚点存在张力时，MIMO 必须把张力显式呈现给用户。

特别关注：
- 三方一致认为"应该简化/砍掉"某个功能——但用户的原始愿景明确需要它
- 三方一致认为"可以先放一放"某个断点——但它是第一梯队的
- 工程效率优先于用户价值的信号
- 任何 agent 试图静默替换第一层签字定义（如把"AI 学习成长系统"替换为"社会体/教练/OS/队友"）
- 把第三层验证信号当作优化目标直接追逐（如直接优化"温暖感"而不优化架构能力）

---

## 十一、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1 | 2026-04-19 | MIMO 初版，基于用户愿景讨论整理 |
| v2 | 2026-04-19 | GLM-observer 审校修正：补齐 5-P 宪法、不做清单、三路分流、TaskGuidance 精确描述、干预语言 6 条原则、闭环完整定义、6 断点优先级、注入清单 5 项、数据泄漏最高 ROI 修复、Stage 4 进度精确化、核对机制增强、90 天计划三梯次 |
| v3 | 2026-04-19 | 用户裁定关系模型为"朋友"（非队友/非教练/非工具）+ Sparkle 自我发展空间；引入三层模型（签字定义 / 架构本质 / 验证信号）防止层间替代；A 类改为可验证信号（配 CI 条件）；Claude "社会体"漂移事件记录为反面案例；首席设计者三条硬约束写入；漂移检测增加定义替换和信号当目标的检测项 |
| v4 | 2026-04-19 | Stage 4/5/6 完成状态统一收口：Stage 5 完成（5 WS accept，88 tests green，7 阶段环 1/7→≥3/7）；Stage 6 完成（6 WS accept，渲染管线修复、用户纠偏后端环、eval 骨架、干预验证）；用户模型五层架构落盘（L0-L3 + 用户纠偏，Rule K + 影子模型 + 白名单）；Stage 7 骨架纳入（4 WS + 显式延后项）；愿景覆盖表与距离评估同步更新 |
| v5 | 2026-04-19 | Stage 7 final-accept 通过（4 WS accept，143 tests green，Rule G/H/I/J/K/L/M 零违规）；系统第一次有用户能在手机上感知的画像闭环（WS-V2）；compiler 边界清晰（WS-C1 委托模式）；eval runner 可执行（WS-E2）；GLM 4 项 P2 发现纳入 Stage 8 处理；Stage 8 入口条件定义（#3/#4/#5 最后一次 deferral + Rule K CI 检测必收）；愿景覆盖表更新：交互式校准从🔶升为✅ |
| v6 | 2026-04-20 | Stage 8 完成（5 WS accept，144 baseline tests green，Stage 8 sweep 50 green，mobile user surface 13 tests green）；Rule K 第一次进入本地/CI 硬护栏；Stage 5 遗留断点 #3/#4/#5 全部收口；dual-core bounded steering 落地到受治理的 session strategy lane；透明度 fallback telemetry 可观测；愿景覆盖表更新：7 个产品断点从🔶升为✅ |
| v7 | 2026-04-20 | Stage 9 完成（4 WS accept，Stage 8 baseline 144 green，Stage 9 backend sweep 27 green，mobile Stage 9 sweep 15 green）；用户前门成立：canonical 画像可在聊天里直接查询与纠正；User Correction lane 明确与 Aurora / L3 / strategy lane 分离；prompt / inference utilization 有正式度量载体；evaluator 从硬编码 scorer 升级为 rubric-driven，支持 optional LLM-attached 元数据 |
| v8 | 2026-04-20 | Stage 10 完成（3 WS accept，Stage 9 frozen baseline 144 green，Stage 10 backend sweep 31 green，mobile Stage 10 sweep 17 green，Rule K guard 35 files / 0 violation）；画像前门从 source markers 升级为 clickable L0 evidence refs；evaluator 接上 real LLM-judge attachment path 并具备 graceful fallback；graph-as-diagnostic 首次成为用户可见的“我哪里弱”诊断面 |
| v9 | 2026-04-20 | Stage 11 完成（4 WS accept，Stage 10 frozen baseline 144 green，Stage 11 backend sweep 14 green，Stage 11 mobile sweep 51 green，Rule K guard 35 files / 0 violation）；evidence 二级导航闭环落地；judge 权重 / timeout / budget / prompt version 工程化；utilization metrics 进入 ai_ops / developer 可见面；CL0 审计明确持续学习五组件当前均不得直接接入用户前门 |
| v10 | 2026-04-20 | Stage 12 完成（4 WS accept，Stage 11 frozen baseline 144 green，Stage 11 backend sweep 14 green，Stage 11 mobile sweep 51 green，Stage 12 backend sweep 20 green，Stage 12 mobile sweep 26 passed + 3 skipped，Rule K guard 35 files / 0 violation）；修复连续学习四个具体基座缺陷：Bayesian key 对齐、multi-dimensional save_state / Celery seam、strategy_store durable L2 cache、mobile 9 项老欠账终局收口；CL0 rerun 结论更新为“基座已修，但仍无组件达到可直接接前门的 wire 状态”，Stage 13 锁 Path C |
| v11 | 2026-04-20 | Stage 13 完成（Gate S13-0 baseline 144 green + Rule V 8 green + Rule K 35/0，Stage 13 backend sweep 23 green，Stage 13 mobile sweep 50 green）；落地 `SQAM` + Rule W，将 continuous-learning 上线资格从主观判断改为四维量化门；`PersistentBayesianLearner` 在同一 frozen method 下从 `repair-first` 升级为 `wire-ready`；`WS-SQ-FEED` 修掉 reward-label fidelity collapse；`WS-EVD3-LITE` 以 memory lane 方式落地 `practice_outcome` 安全证据类型；Stage 14 入口从 Stage 12 Path C 升级为“可对单一组件提出 bounded `WS-CL1` 候选”的 Path A |
| v12 | 2026-04-20 | Stage 14 完成（Gate S14-0 baseline replay 144 green + Rule V 8 green + Rule K 35/0 + Stage 13 backend sweep 23 green + Stage 13 mobile sweep 50 green；Stage 14 targeted backend sweep 23 green）；修复 `RouterNode` 的持久 learner 集成残缝；在 frozen `11` state / `220` observation proxy fixture 下重跑 SQAM，`PersistentBayesianLearner` 继续保持 `ID1 / ST1 / DP1 / SM1` 全绿；落地零用户感知、L2 inference-cache-only 的 shadow divergence pipe；但 `state_{tool_category}` 压缩被 Stage 14 审定为当前 wire-on 的 blocking 限制，因此 Stage 15 fork 被锁为 `Path A-blocked` |
| v13 | 2026-04-20 | Stage 15 完成（within-category bounded wire-on，Path A-on narrowed claim only）；Stage 16-23 战略路线图 v2.0 锁定（四方审查通过，11 项调整合并）；Memory 写路径（Stage 16）确认为整个能力链路最大隐性瓶颈——聊天流量 100% 不写 EpisodicMemory，使得 Reflect/Adapt 永远只能拿历史 review/error 等"被结构化过"的事实；MIMO 独立发现 Memory 读路径也可能断裂（orchestrator.py 中 AgentMemoryService import 标记 noqa: F401）；依赖链 Memory → Proactive → Skill → Wire-On → Social 确认 |
| v14 | 2026-04-20 | 多阶段战略路线图 v2.0 完整纳入愿景锚定清单；Stage 16 dispatch plan 落盘（WS-MWL-* 七个 Workstream + Rule Y + Path B/C 兜底）；Stage 16-23 各阶段战略目标、入场条件、关键 WS、验收门纳入 §9.15-§9.21；Stage 16 入场条件锁定（Gate S16-0 baseline + Codex §0.5 自答）；愿景覆盖表更新：持续学习三层结构从🔶升级为🔶→Stage 16 后预计✅ |
| v15 | 2026-04-20 | Stage 16 engineering closeout 完成（Gate S16-0 baseline 144 green + Rule V 8 green + Rule K 35/0 + Stage 13/14/15 backend carry-forward 24 green + Stage 13/15 mobile carry-forward 53 green；Stage 16 targeted backend sweep 16 green；Stage 16 targeted mobile sweep 8 green）；Rule Y 正式落盘，chat -> EpisodicMemory `inferred_extraction` governed write lane 打通，并同时满足 read / declare / revoke / kill；`inferred_extraction` 经 grep 证明未进入 Router / Push / Skill / Accountability 下游消费路径；愿景覆盖表更新：持续学习三层结构升级为✅，但 Stage 17 仍受“一周生产灰度 + Rule Y 无破例”运营门约束 |
| v16 | 2026-04-20 | Stage 16 final-accept 通过（GLM-observer + GLM1 双独立审计对齐）；Stage 17 dispatch plan 初版落盘（WS-SOC-* 七个 Workstream + Rule Z 跨用户隐私 + Accountability MVP + Router 只读上下文）；依赖链重排：Memory → Social → State Aggregator → LLM Extract → Skill → Wire-On → Dual Mode → Growth OS；Rule 编号顺延确认：Stage 16 Rule Y（推断式写入治理）→ Stage 17 Rule Z（跨用户隐私）→ Stage 20 Rule AA（Skill 跨用户共享）；Stage 17 入场三重锁：≥7 天生产灰度 + Rule Y 无破例 + dispatch plan 落盘；愿景覆盖表更新：社交脑从❌→🔶（dispatch 落盘待开工），Router 决策消费 Memory 延后至 Stage 19B+ |
| v17 | 2026-04-20 | Stage 17 dispatch plan 根据最终裁决合并 Addenda A-G：Rule 命名表正式锁定；`WS-SOC-RULE-Z` 升格 P0 并要求 HMAC-SHA256 边界；新增 `WS-SOC-NAMESPACE` 阻断 `community_context` 隐式注入；Path 矩阵改为 A / B1 / B2 / C；`WS-SOC-ROUTER-READ` 增加 ≥30 组 A/B prompt 对照；`WS-SOC-EXTRACT` 增加 backpressure 约束；`WS-ACCT-MVP` 增加健康审计前置与 commitment recall 观测；Stage 18 明确承担 `RouterContextReader -> State Aggregator` 重构义务 |
| v18 | 2026-04-20 | Aurora Gray Window 上下文化治理升版：新增 `PGW / SGW / Skipped` 三段式门控，Sparkle 当前 `Pre-launch` 语境改走 SGW；新增 `SPARKLE_AURORA_GOVERNANCE_GRAY_WINDOW_CONTEXT_2026-04-20.md` 与 `SPARKLE_AURORA_STAGE16_SGW_FRAMEWORK_2026-04-20.md`；Stage 17 入场条件从物理上不可满足的 7 天生产灰度改为 SGW（≥12h wall-clock + ≥20 persona + ≥200 会话 + ≥4000 turn + `Hard violation = 0` + `Soft violation rate < 5%`）；同时保留真实用户接受度为延后验证项 |
| v19 | 2026-04-20 | SGW v1.0 工程化定稿：并发收敛为 5 个 Claude worker，运行改为可 checkpoint / resume 的确定性 orchestrator；persona 覆盖冻结为 44 条（36 矩阵 + 8 特殊），总会话阈值升级为 ≥360；治理 addendum 升格为 `SPARKLE_AURORA_GOVERNANCE_GRAY_WINDOW_CONTEXT_2026-04-20.md`；Stage 17 dispatch 明确 `SocialContextProvider -> FrozenSocialSnapshot` 前瞻兼容契约，Stage 18 必须以 Aggregator provider 实现兑现该契约 |
| v20 | 2026-04-20 | Stage 17 + 18 engineering closeout 完成；Stage 17：8 WS accept（Rule Z 落盘 + 社交主语分类器 + commitment parser + Accountability MVP + Router 只读 seam + per-type kill switch），27 backend + 51 mobile green；Stage 18：8 WS accept（`user_state.v1` frozen schema + pull-only Aggregator + 确定性 push policy + WebSocket channel + Rule AB + 三级 kill switch + mobile opt-in），42 backend green + GLM1 独立审计通过；Aggregator-backed Router 迁移保持 Stage 17 公共合约不变；愿景覆盖表更新：社交脑从🔶→✅，主动推送从❌→✅，状态聚合从❌→✅；7 阶段成长环 5/7（Reinforce 仍弱，Stage 19 预计首次触达）；治理规则达 19 条（G-Z + Y + Z + AB） |
| v21 | 2026-04-20 | Stage 19 engineering closeout 完成（GLM1 accept clean，无 carry-forward debt）；7 WS accept：Working Memory Redis-only 核心服务 + LLM 抽取 dry-run pipeline（Rule Y 四要素对账 + banned inferences emotion/mood/personality）+ pipeline 协调模式（WorkingMemoryPipelineService 统一规则式与 LLM 两条路径）+ consolidation 流程（不触发 push）+ Aggregator v1.1 升级（新增 working_memory_snapshot，proto-gen clean + KL ≤ 0.03）+ mobile 透明度 + 三级 kill switch（working_memory / llm_extractor / consolidation 独立可杀）；Rule AC 落盘；24 backend + 6 mobile tests green；7 阶段成长环 6/7（Reinforce 从🔶升为✅）；治理规则达 20 条（+ Rule AC） |
| v22 | 2026-04-20 | Stage 20 engineering closeout 完成（GLM1 accept clean，无 carry-forward debt）；7 WS accept：Sufficiency Judge（纯规则式，judge_version="v1" frozen）+ task/context split（Rule AD）+ Conflict Resolver（frozen 优先级链 working_memory < llm < rule < explicit）+ shadow mode 并行比较 + Route History write-only 决策日志 + outcome backfill + 4 张 Alembic 审计表 + 2 个 CI 守卫；Rule AD/AE 落盘；Stage 17 carry-forward 债务清零（handoff 升级为 closeout baseline + Rule Z HMAC 升级注释补齐）；路线图调整：原 Stage 20 Skill 蒸馏延后至 Stage 21，Stage 20 改为 Sufficiency 治理层；Stage 21-24 顺延；治理规则达 22 条（+ Rule AD/AE），Rule AF 锁定为 Stage 21 Skill 跨用户共享 |

---

## 十二、首席设计者工作约束

任何承担首席设计者角色的 agent（当前为 Claude）必须遵守以下硬约束：

1. **任何架构提案必须同时带可验证条件**。否则 kick back 重写。"让系统更温暖"这类表述本身就应该被 block。
2. **不修改签字定义**。如果觉得产品共识需要改，必须走 amendment 流程，不能在日常讨论里静默 reframe。
3. **每次提出新概念前，先问自己：这在实际工程里能分解成可执行的 task card 吗？如果不能，它就不是架构，是散文。** 散文可以在内部思考，但不放进产出。

---

*本清单由 MIMO 维护，每次用户愿景讨论后更新。修正需追溯至已签字共识文档。*
