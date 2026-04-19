# Sparkle 愿景锚定清单

> **文档性质**: MIMO 战略对齐工具
> **维护者**: MIMO
> **日期**: 2026-04-19
> **版本**: v4（Stage 5/6 完成 + 用户画像系统架构 + Stage 7 骨架）
> **用途**: 锚定长期多阶段工作的方向，每次派卡前核对是否偏离
> **权威来源**: 本清单中的每一条均可追溯至以下已签字文档
> - `SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` — 产品核心共识
> - `SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md` — Stage 4 战略共识 v2
> - `SPARKLE_AURORA_STAGE5_DISPATCH_PLAN_2026-04-19.md` — Stage 5 派发计划
> - `SPARKLE_AURORA_STAGE5_HANDOFF_2026-04-19.md` — Stage 5 收尾 handoff
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md` — 用户模型五层架构
> - `SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md` — 成长系统路线图
> - `SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md` — 数据利用分析

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

### 9.5 Stage 7 已定骨架（4 WS + 显式延后项）

**当前执行面（以 `SPARKLE_AURORA_STAGE7_DISPATCH_PLAN_2026-04-19.md` v0.1 为准）**：

| WS | 主题 | 说明 |
|----|------|------|
| WS-C1 | 双 compiler 归一 | 必须先完成调用链图与 owner 归属，再允许其余 WS 最终 accept |
| WS-M1c | M1 数据质量深化 | 在现有画像投影管线内补 source coverage / quality registry |
| WS-V2 | 透明度/纠错 Flutter 消费侧 | Stage 7 唯一直接面向用户的画像系统 WS |
| WS-E2 | 真实 evaluation runner | 在 `WS-E1` skeleton 上挂只读 runner |

**显式延后挂牌（不从世界中消失）**：

| 项目 | 来源 | 状态 | 下一归属 |
|------|------|------|----------|
| breakpoint #3 `plan health no event` | Stage 5 handoff §6 | deferred | Stage 8 必须收口或 amendment |
| breakpoint #4 `push time-only` | Stage 5 handoff §6 | deferred | Stage 8 必须收口或 amendment |
| breakpoint #5 `cognitive_adjustments text-only` | Stage 5 handoff §6 | deferred | Stage 8 必须收口或 amendment |
| RB1 tokenizer-aware inline budget | `WS-RP1` 精度尾债 | Stage 7 out-of-scope | Stage 8 candidate 或后续 amendment |

### 9.6 愿景锚点 vs 当前覆盖

| 愿景锚点 | 覆盖度 | 说明 |
|----------|--------|------|
| Aurora 异步化 | ✅ Stage 4 | 三时层 substrate + 路由分流 |
| 对话分流 | ✅ Stage 4 | 三路 routing_mode + 会话中途升级 |
| TaskGuidance 双版本 | ✅ Stage 4 | sidecar + UI |
| 任务助手降级 | ✅ Stage 4 | 单核 + 5 项注入 + dormant |
| 5-P 宪法执行 | ✅ Stage 4-6 | P1-P5 全部绿色 |
| 用户模型五层架构 | ✅ Stage 6 | Rule K + 影子模型 + 白名单 + 投影管线硬化 |
| 交互式校准 | 🔶 部分 | 后端环已通（WS-V1）；前端消费待 WS-V2 |
| 数据泄漏修复 | 🔶 部分 | 渲染管线已修（WS-RP1）；tokenizer-aware inline 精度仍是尾债，不在 Stage 7 执行面 |
| 6 个产品断点 | 🔶 部分 | #1/#2/#干预语言/#6 已推进；#3/#4/#5 显式挂牌到 Stage 8 |
| 双核协作闭环 | 🔶 0.6/1 | Stage 5 建了一条通路，非完整双向 |
| 持续学习三层结构 | ❌ 未来 | Stage 8+ |
| 双交互模式 | ❌ 未来 | Stage 8+ |

### 9.7 距离评估

**用"7 阶段成长环"做标尺**：
- Sense → Clarify → Plan：Stage 4 路由分流 ✅
- Execute → Reflect：Stage 5 WS-R1 replanner 闭环 ✅
- Reflect → Adapt：Stage 5 WS-G1 growth signal 变强 ✅
- Reinforce：仍弱 ❌
- 整体：≥3/7

**用"用户感知"做标尺**：
- Stage 6 WS-V1 后端纠错环已通，但前端不消费等于零用户价值
- Stage 7 WS-V2 是第一个用户能直接感知的画像系统闭环
- 数据利用：渲染管线已修（WS-RP1），tokenizer-aware inline 精度仍是跟踪中的尾债，但不阻塞 Stage 7 起跑

**用"数据利用"做标尺**：
- Stage 5 增加了 growth signal payload（从 0 到有），但 prompts.py 死数据修复（最高 ROI）未动
- WS-RP1 是修复泄漏的最后一公里

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
| v4 | 2026-04-19 | Stage 4/5/6 完成状态统一收口：Stage 5 完成（5 WS accept，88 tests green，7 阶段环 1/7→≥3/7）；Stage 6 完成（6 WS accept，渲染管线修复、用户纠偏后端环、eval 骨架、干预验证）；用户模型五层架构落盘（L0-L3 + 用户纠偏，Rule K + 影子模型 + 白名单）；Stage 7 骨架改为真实执行面（4 WS：C1/M1c/V2/E2）+ 显式延后项（#3/#4/#5 → Stage 8，RB1 out-of-scope）；愿景覆盖表与距离评估同步更新 |

---

## 十二、首席设计者工作约束

任何承担首席设计者角色的 agent（当前为 Claude）必须遵守以下硬约束：

1. **任何架构提案必须同时带可验证条件**。否则 kick back 重写。"让系统更温暖"这类表述本身就应该被 block。
2. **不修改签字定义**。如果觉得产品共识需要改，必须走 amendment 流程，不能在日常讨论里静默 reframe。
3. **每次提出新概念前，先问自己：这在实际工程里能分解成可执行的 task card 吗？如果不能，它就不是架构，是散文。** 散文可以在内部思考，但不放进产出。

---

*本清单由 MIMO 维护，每次用户愿景讨论后更新。修正需追溯至已签字共识文档。*
