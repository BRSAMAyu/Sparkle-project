# Sparkle Aurora Stage 4 Vision Alignment (2026-04-19)

> **Status**: Draft **v2** · Claude 合并 Codex 拍板版 + GLM 条目审 · 待用户最终盖章
> **Supersedes**: v1（2026-04-19 当日）· 任何 "Stage 4 = pre-tool-selection 接管" 的隐含工程惯性
> **Scope**: 战略共识文件，不含代码；锁定后再拆 workstream / wave。

### Revision History

| 版本 | 变更要点 | 来源 |
| --- | --- | --- |
| v1 | 首稿：5 段骨架 + 5-P 宪法 + 8 决策点 + 不做清单 | Claude 起草 |
| v2 | Q1-Q5 采纳 Codex 拍板版 · §2.2/§7 去重 · §3.1 删 Presence 列 · §4.2 ComplexityRouter 降级为字段 · §4.4 加 fallback · §3.3 补 prior_outputs 衔接 · P5 nearline 调至 P95≤30s/P99≤60s · Gap2 正式录入（不映射） · TaskGuidance 降为 "Stage 4 候选 primitive" + 最小 schema 骨架 · 会话升级信号最小判据集补齐 | Codex + GLM |

---

## 0. 这份文件是干什么的

Stage 3 仓库侧已完成（79 tests green · 9/10 shadow routine agreement · WS-M Phase 1
cutover-ready · 3 caveats documented）。按原工程惯性，下一步会是
"pre-tool-selection 接管 → pre-response-formatting 接管"。

用户在 2026-04-18 主动叫停这条直线，要求回到**愿景层**重新对齐。这份文件把用户
提出的战略输入、GLM 的 pin/gap、Codex 的建议答案，以及我自己的 5-P 宪法补丁，
合并成一份**先锁共识、再谈工程**的 Stage 4 入口文件。

---

## 1. 为什么 Stage 4 需要战略回归

### 1.1 我们在 Stage 3 证明了什么

- Aurora 能以**同步、单体、仓库内**的姿态跑通 pre-node-routing 这一个面
- 用 shadow → projection → cohort gating 这套迁移套路可以零破坏落地
- 观测、回滚、凭证三件套可以在一个面上闭合

### 1.2 Stage 3 没有证明什么（三条 caveats）

- 当前 90% shadow 一致率是**"用户体验一致性"**，不是 Aurora 独立推理一致性
- 当前投影逻辑在 `migration.py:216-235` 偷看 legacy routing input，不是纯 Aurora
- 12 条 curated 语料不等于 ≥100 条 production-replay 语料

### 1.3 为什么不能继续按原计划冲 Stage 4

用户在 2026-04-18 明确给出的四条现实约束：

1. **成本**：一次请求触发 Aurora 全链路，在真实流量下成本不可接受
2. **延迟**：Aurora 同步接入，会让简单对话也等一次完整推理
3. **闭环**：目前的"转给外部 AI"式分流，违背"Sparkle 是用户唯一成长终端"的立意
4. **颗粒度**：当前架构对"简单直接回答"和"复杂任务工作流"一视同仁

这四条单独看是工程问题，合起来是**定位问题**——如果 Aurora 只是一个"更贵更慢
的路由器"，它就不该上线；如果它是"一套可以同时跑慢/快/即时三路的控制面"，那
当前形态就只是它的 inline 版本。

Stage 4 的正确提问不是"下一个 trigger point 接哪个"，而是**"Aurora 完全体长什么
样，当前 Stage 3 是它的哪一部分"**。

---

## 2. Stage 4 的新主线

### 2.1 一句话主线

> **先把 "Aurora 完全体" 定义清楚、跑起来；再按成本/延迟预算把它精简成 inline
> 快路径和即时反馈路径。不反过来。**

### 2.2 Stage 4 的四根支柱

1. **Aurora 异步化 + 三时层**（§3）
2. **对话颗粒度分流**（§4.2）
3. **任务指南升级为双版本产物**（§4.3）
4. **任务助手降级为单核 + 初始 Aurora 注入**（§4.4）

支柱之间的顺序：1 先做完，2/3/4 才能稳——因为 2/3/4 都在消费 Aurora 的产出。

### 2.3 不做的事

"显式不做"清单是 Stage 4 的治理工具，**唯一权威列表放在 §7**。本节不重复，避免
两处维护同一类内容迟早不一致。

---

## 3. Aurora 完全体：三时层 + 对外一体

### 3.1 三时层（内部分层）

| 时层 | 预算 | 触发方式 | 典型产物 |
| --- | --- | --- | --- |
| **inline** | P95 < 100ms | 对话请求同步路径 | BackboneRoutingDecision（含 routing_mode） |
| **nearline** | P95 ≤ 30s · P99 ≤ 60s | 会话结束 / idle 触发 / 显式提交 | TransitionDecisionRecord、InsightClaim、ProbeOutcome、TaskGuidance |
| **long-horizon** | 小时级~天级 | 批处理 / 定时 / 成长周期 | FocusContract 版本演进、IdentityEvidence 聚合、WindowState 更新 |

三时层不是三个 Aurora，是**一个 Aurora 引擎在三种预算约束下的行为谱**。对外通过
同一套 primitives 表达结果。

> **注（GLM 审定）**：Presence 和 Time-tier 是正交两轴，本表**不再给出**
> "Presence 对应列"。Presence 决定用户可见度和交互模式；Time-tier 决定预算和
> 延迟。正式映射见 §6 Gap2 答案。

### 3.2 对外一体（外部抽象）

下游（orchestrator / task guide / task assistant / mobile）不感知时层：

- 下游只看到 `prior_outputs` 里是否有某类 primitive 可用
- 不要求"现在立刻算"；允许 miss → fallback
- 缺席不是错误，是**"此刻该时层尚无产物"**

这就是用户说的"外层一体，内层分层"：**外部统一 API，内部按预算分路**。

### 3.3 三时层的衔接通道

- **inline → nearline**：通过 `AuroraDecisionContext.prior_outputs` 字典传递
  （复用已有设计），inline 产出的 BackboneRoutingDecision / 轻量 snapshot
  hash 作为 nearline 消费入口
- **nearline → long-horizon**：通过 **primitives 持久化**传递（写入对应表），
  long-horizon 批处理只读 primitives，不读内存
- **nearline ↔ nearline / long-horizon ↔ long-horizon**：异步进程间不共享内存，
  只通过 primitives 表通信

**关键约束（P1 落实）**：三时层之间**只通过 primitives 或 prior_outputs 字典**
通信，不共享任何内存状态、不共享任何 ORM session。这条红线不能破。

### 3.4 三时层如何落位到当前代码

- **inline**：即现有 `AuroraEngine.safe_route()` 同步路径，继续走 trigger point
- **nearline**：新增 async queue（见 §6 Gap3 建议复用 Celery），消费 `SignalSnapshot`
  批次 → 写 `TransitionDecisionRecord` / `InsightClaim` / `TaskGuidance`
- **long-horizon**：复用 Celery beat 已有基础设施，做 FocusContract 版本演进 /
  IdentityEvidence 聚合 / WindowState drift 检测

---

## 4. 四条新共识

### 4.1 闭环（Closed-loop）共识

**原则（P3 强化版，采纳 GLM pin）**：

- Aurora 默认**不**把用户转给外部 AI；Sparkle 是用户的唯一成长终端
- **唯一例外**（capability ceiling escape）：当请求进入明确定义的 CapabilityGate
  拒绝域（例如：医疗诊断、法律咨询、紧急危机援助热线），Aurora 通过
  `CapabilityGate.enabled=false + route="external_referral"` 明示转介，且必须
  在 UX 层告知用户"这是转介，不是 Sparkle 在回避"
- 除 capability ceiling 外，所有"我帮不了你，你去问 ChatGPT"式话术**禁用**

### 4.2 对话颗粒度分流共识

**原则**：同一个 Aurora 引擎，根据请求复杂度选择不同产出形态。

- **简单直接回答路径**：inline 出 BackboneRoutingDecision（stay + ambient）+
  orchestrator 走短 FSM
- **复杂任务工作流路径**：inline 出 transition 意向 + nearline 补 TDR 全记录 +
  orchestrator 走长 FSM（含 plan / tool / review）
- **升级点**：支持**会话中途升级**——一段对话从简单升为复杂时，Aurora 重新发
  transition 意向，orchestrator 无缝切到长 FSM

**组件归属（GLM 审定：降级为字段，零新增组件）**：

- 不新建 `ConversationComplexityRouter` 类/服务
- 在 `BackboneRoutingDecision` 上新增字段 `routing_mode: RoutingMode`
  - `RoutingMode ∈ {direct, workflow, task_assistant}`
- 复杂度判断是 `decide_backbone_route()` 的**天然副产品**，通过该方法内部
  的 signal 权重扩展输出，不是独立 decision function

**会话中途升级触发判据（最小集）**：

1. 用户显式请求规划 / 拆分任务 / 制定计划
2. 连续 2+ 轮追问同一结构性话题（signal 衰减但未切换）
3. 挫败表达检测命中（emotional_block / repeated_failure 信号）

首判 direct 后命中以上任一条，下次 safe_route 返回 `routing_mode=workflow` +
transition 意向，orchestrator 切 FSM。

### 4.3 任务指南升级共识

**原则**：任务指南从"静态模板"升级为"Aurora 参与生成的双版本产物"。

- **用户版本**（default）：人话、情境化、低密度；创建任务卡时**默认生成**并推送
- **AI 版本**（on-demand）：结构化、ref-rich、高密度；**用户点"给 AI 用的版本"时
  才生成**，供下游 task assistant 消费
- 两个版本从**同一个 TaskGuidance primitive** 派生，保证一致性
- 双版本**不预先全量生成**，避免成本叠加（回应 Codex 拍板 Q3）

**治理措辞（采纳 Codex 建议）**：

> `TaskGuidance` 是 **Stage 4 候选 primitive**，本文档只提议其存在与最小 schema；
> 是否正式入宪 Gate 0 由 Codex 按 schema impact 审后定（见 §6 Gap1）。

**TaskGuidance 最小 schema 骨架（候选，非 frozen）**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | primitive 主键 |
| `task_card_ref` | UUID | 所绑任务卡 ID |
| `audience` | `GuideAudience` enum | `human` / `ai` |
| `content` | str | 指南正文（按 audience 渲染） |
| `generated_by` | `DecisionMechanism` | 已有枚举复用（deterministic / llm / hybrid） |
| `policy_version` | str | 生成时锚定的 aurora_policy 版本 |

### 4.4 任务助手降级共识

**原则**：任务助手保持单核（不引入双核），但**会话起点**接收 Aurora 的初始注入。

Aurora 在会话建立时（或任务分派时）**一次性注入**以下 5 项：

1. 当前 `FocusContract` 摘要
2. 当前 `TaskGuidance` 的 AI 版本（若已生成，否则该条 fallback 为用户版摘要）
3. 最近一次 `TransitionDecisionRecord` 的 `UXIntent + AuroraPresenceLevel`
   - **若不存在历史 TDR**（新用户 / 冷启动），fallback 为
     `UXIntent.ROUTINE + AuroraPresenceLevel.AMBIENT`
4. projection-allowed 的活跃 `InsightClaim`
5. 最近 N 条相关 `ProbeOutcome`（N 初值建议 3，可调）

**中途策略**：

- 注入后任务助手按单核正常跑
- 会话运行期间，**Aurora 不向该会话注入新的 context 或干预指令**
- 但 Aurora 可以在 nearline 收集该会话的 outcome 用于**下一轮**注入
- 仅在强信号（crisis / emotional_block / capability ceiling）命中时才 refresh 注入

**5 条注入项是最小集**（Codex 建议 + GLM fallback 补齐），后续按实际消费情况扩。

---

## 5. 5-P 宪法补丁（Constitutional Additions）

在原 Aurora 宪法（可治理优于更聪明、side-effect 一致、fallback 完备）之上，Stage 4
新增 5 条：

| ID | 原则 | 可验证条件 |
| --- | --- | --- |
| **P1** 时层纪律 | 三时层只通过 primitives 或 prior_outputs 通信 | 代码层禁止跨时层共享状态；CI 检测 |
| **P2** 外部一体 | 下游不感知 Aurora 时层 | 下游接口不出现 "inline/nearline" 字样 |
| **P3** 闭环原则 | 默认不转外部 AI，除 capability ceiling | CapabilityGate 拒绝域有白名单且 UX 明示 |
| **P4** 颗粒分流 | 简单/复杂路径共用 Aurora，不分叉引擎 | 只有一个 `AuroraEngine` 类；ComplexityRouter 是字段不是服务 |
| **P5** 预算可观测 | 每时层有成本/延迟预算并上报 | 每次调用带 tier 标签；仪表盘 P50/P95/P99 达标 |

**GLM pin 已吸收**：P3 的 ceiling escape、P5 的可观测可验证。

**P5 初始预算（Codex/GLM 待最终校准，已吸收 GLM 第一轮修正）**：

- inline：**P95 ≤ 100ms** · 每次请求 Aurora 贡献成本 ≤ 0.1 × LLM 基线
- nearline：**P95 ≤ 30s · P99 ≤ 60s** · 单位 session 成本 ≤ 1 × LLM 基线
- long-horizon：延迟不敏感 · 批量成本 ≤ 0.5 × LLM 基线 / active user / day
  （**标注**：该阈值为初始锚点，上线后按实际用户量校准）

---

## 6. 8 个待决策条目（5 Q + 3 Gap）—— v2 状态

| # | 条目 | v2 状态 | 答案 / 建议 |
| --- | --- | --- | --- |
| **Q1** | Aurora 异步的时层模型 | ✅ Codex 拍板版接受 | inline / nearline / long-horizon 三层（§3.1） |
| **Q2** | ComplexityRouter 归属 | ✅ Codex 拍板 + GLM 降级为字段 | `BackboneRoutingDecision.routing_mode` 字段 · 支持会话中途升级（§4.2） |
| **Q3** | 任务指南双版本发布策略 | ✅ Codex 拍板版接受 | 用户版默认生成 · AI 版 on-demand（§4.3） |
| **Q4** | 任务助手初始注入最小集 | ✅ Codex 拍板版接受 + GLM fallback 补齐 | 5 项 · 会话起点注入 · 冷启动 fallback 已定义（§4.4） |
| **Q5** | 闭环严格度 | ✅ Codex 拍板版接受 | 默认闭环 + capability ceiling 窄口例外（§4.1 / P3） |
| **Gap1** | TaskGuidance 在 Gate 0 的位置 | 🟡 已给最小 schema 骨架（§4.3） | 是否正式入宪待 Codex schema-impact 审 |
| **Gap2** | Presence ↔ 成本时层映射 | ✅ GLM 正式回答：**不映射**（两轴正交） | 见下方正交表 |
| **Gap3** | nearline 队列选型 | 🟡 建议复用 Celery（已有基础设施） | 待 Codex 最终确认 |

### Gap2 正交矩阵（GLM 提供）

|  | AMBIENT | ACTIVE | META_SURFACE | DORMANT（候选新增） |
| --- | --- | --- | --- | --- |
| **inline** | 默认直答场景 | workflow 入口帧 | meta-reflection 触发 | 任务助手首帧注入 |
| **nearline** | 常规静默优化 | 主动策略调整 | 深度反思归档 | 收集 outcome |
| **long-horizon** | 模型漂移检测 | pack 策略演化 | 用户画像版本升级 | — |

> Presence 决定用户可见度和交互模式；Time-tier 决定预算和延迟。两轴独立。
> DORMANT 为本轮候选新增 presence 级别，待 Gate 0 schema 审定。

---

## 7. Stage 4 不做的事（唯一权威清单）

为防止工程惯性跑偏，Stage 4 **显式不做**以下 7 条：

1. pre-tool-selection 接管（deferred 到 Stage 5 或更后）
2. pre-response-formatting 接管（deferred 到 Stage 5 或更后）
3. 新独立 AI 路由服务（继续扩 Aurora 内部）
4. 任务助手重写为双核（保持单核 + 初始注入）
5. 把三时层拆成三个独立服务/进程（保持单引擎，内部分路）
6. **任务助手会话运行期间，Aurora 不向该会话注入新的 context 或干预指令**；
   但 Aurora **可以**在 nearline 收集该会话的 outcome 用于**下一轮**注入
   （精确化措辞，采纳 GLM 审意见）
7. 在 Stage 4 内同时铺 cohort 放量（Phase 1 只做 allowlist，放量留给 Stage 4 末）

这份 "不做" 列表本身是 Stage 4 的**治理工具**——任何新提议的 workstream 如果撞到
这 7 条里任意一条，默认拒绝；要通过必须走宪法修订。

---

## 8. Stage 4 上线前门禁（Stage 3 遗留）

从 Stage 3 checkpoint 继承的三个前置条件：

1. **3 条 caveats 文档化**（✅ 已在 WS-M runbook §Known Limits 完成）
2. **Shadow corpus ≥ 100 条 production-replay，routine ≥ 80%**（⏳ 未完成 · 需生产流量回放权限）
3. **WS-M 始终标注 Phase 1**（✅ 已在 runbook 明示 · 持续遵守）

Stage 4 主线工作可以和 #2 并行推进，但**cohort 放量**必须等 #2 达标。

---

## 9. 下一步（流程，非工程）

v1 → v2 已完成三方意见合并。剩余步骤：

1. **用户盖章 v2**（或对任何条目发起修订）
2. **Codex 正式回** Gap1（TaskGuidance 是否入宪 + schema 审）与 Gap3（Celery 复用确认）
3. **盖章后**开 Stage 4 工程结构文档（workstream 重组、wave 规划）
4. **工程结构盖章后**才派第一个 Stage 4 agent

**本文档在 §1-§7 所有内容被用户盖章前，不进入工程阶段。**

---

## 附录 A · 与既有文件的关系

- 本文档**不替代** `SPARKLE_AURORA_ORCHESTRATOR_INTEGRATION.md`（Gate 0 schema / 6 returns / 5 ledger primitives 仍有效）
- 本文档**提议扩展** Gate 0：TaskGuidance 为 Stage 4 候选 primitive，待 Gap1 决议
- 本文档**不替代** `SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md`（WS-M Phase 1 定义不变）
- 本文档**下游化** Stage 3 Dispatch Plan v1.1 的剩余 workstream：任何未关闭项重新归到 Stage 4 四支柱下评估

## 附录 B · 产品愿景对齐点

- 与 `SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` 的 "发现问题 → 可接受交付 → 采纳 →
  行动 → 验证 → 更新" 主闭环**完全一致**
- 本文档的闭环原则（P3）即产品共识 "Sparkle 是用户唯一成长终端" 的工程投影
- 任务指南双版本（§4.3）直接服务产品共识的 "可接受交付" 断点
- 任务助手单核 + 初始注入（§4.4）直接服务产品共识的 "采纳 → 行动" 断点
