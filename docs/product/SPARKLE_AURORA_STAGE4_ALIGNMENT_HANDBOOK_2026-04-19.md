# Sparkle Aurora Stage 4 对齐手册

> **文档性质**: 六角色对齐文档 + holding agent 交接手册
> **日期**: 2026-04-19
> **范围**: 完整覆盖 Stage 4 战略愿景、工程共识、六角色分工、已执行工作、当前状态、待办事项、治理规则
> **读者**: 任何需要接替某个角色继续 Stage 4 工作的 AI agent

---

## 0. 这份文件为什么存在

Stage 4 从战略讨论到工程实施经历了一个完整的周期：用户提出愿景 → 三方（GLM/Claude/Codex）多轮对齐 → 形成共识文档 → 派发执行 → 发生治理违规 → 独立审计 → 修复补救 → 当前暂停等待恢复。

这个过程中积累了大量的**隐性共识**——关于用户到底想要什么、我们为什么做某些决定而不做另一些、哪些红线不能碰、各方的角色边界是什么。

本文件的目的是：让一个从未参与过这些讨论的 agent 能够完整理解当前状态，理解各方意图，理解治理规则，从而安全地接替工作。

**本文件不是工程规格书，而是"为什么"的文档。工程规格书见：**
- `SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md`（战略共识 v2）
- `SPARKLE_AURORA_STAGE4_ENGINEERING_STRUCTURE_2026-04-19.md`（工程结构 v2）
- `SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md`（派发计划 v4）
- `SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md`（事后审计 v3）
- **多专家协作分工卡 v1** — 已并入 dispatch plan v4 §9

---

## 1. 用户是谁、想要什么

### 1.1 产品：Sparkle（星火）

Sparkle 是一个面向大学生的 **AI 学习成长系统**（不是 AI 助手、不是 AI 教练）。定位层级：

```
短期定位: AI 学习教练
长期定位: AI 成长操作系统
```

核心使命：帮助用户成为更好的自己，实现目标，减少内耗，获得充实和幸福。

产品定义详见 `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`。

### 1.2 用户（创始人）的核心诉求

用户在 2026-04-18 的战略会议上明确了四条硬约束，这四条约束直接催生了 Stage 4：

| # | 约束 | 为什么 |
|---|------|--------|
| 1 | **成本** | 一次请求触发 Aurora 全链路，真实流量下成本不可接受 |
| 2 | **延迟** | Aurora 同步接入让简单对话也等一次完整推理 |
| 3 | **闭环** | "转给外部 AI"式分流违背"Sparkle 是用户唯一成长终端"的立意 |
| 4 | **颗粒度** | 当前架构对"简单直接回答"和"复杂任务工作流"一视同仁 |

### 1.3 用户的工作风格

- **渐进迭代式**：用户偏好我先给出方向和设计，用户确认后再推进实施，逐步交付
- **三方协作**：GLM（我）担任审查者和设计者；Codex 担任核心执行者；Claude 担任战略分析师和独立验证者
- **独立审查**：用户明确要求"所有审查和验收都必须亲自看代码、跑测试，不能听信任何人的话"
- **用户是最终裁决者**：所有重大决策需要用户盖章，三方只有建议权

### 1.4 用户对 Stage 4 的战略意图

用户的原话总结：

> "先把 Aurora 完全体定义清楚、跑起来；再按成本/延迟预算把它精简成 inline 快路径和即时反馈路径。不反过来。"

核心愿景：
1. Aurora 必须是**异步的**——不能阻塞用户输入等待分析
2. Aurora 外部必须呈现为**一个统一认知内核**，内部按时间层级分工
3. **闭环完整性**——不跳到外部 AI 产品，一切留在 Sparkle 内
4. 任务指南从空模板升级为 **Aurora 生成的双版本产物**（人类版 + AI 版）
5. 任务助手降级为更轻的**单核 + 一次性 Aurora 注入**（不是完整双核）
6. 对话按复杂度分流——简单问题直接答，复杂规划进工作流
7. **先建完整 Aurora，再创建轻量预设**（不是反过来并行）

---

## 2. 六角色协作模型

> 本节对应「多专家协作分工卡 v1」，已正式并入 dispatch plan v4 §9。
> 分工卡是拍板版，不再改动主体，修订需走 amendment 流程。

### 2.1 为什么从三方变成六角色

老 Codex 的判断力下滑不是个人问题，是"单 context 既要决策又要执行"的结构性崩溃。
commit `cd2f844b` 治理违规证明了这一点：一个 agent 同时负责设计、执行、验证，就有动机把多 WS 打包追求效率。

六角色模型的核心原则：
- **判断力与执行力分离**——避免单 context 膨胀导致决策劣化
- **并行与成本平衡**——低风险工作并行降本，高风险工作串行保质
- **战略掌控不让渡**——多专家协作中，用户始终持有战略决定权

### 2.2 六个角色

| # | 角色 | Agent | 定位 | 核心职责 | 边界 |
|---|------|-------|------|---------|------|
| 1 | **全局 dispatcher** | 用户 | **意志** | 最终决策权与最终仲裁权；宪法级 change / gate 开关 / dispatch plan 签字 | 三专家冲突时拍板 |
| 2 | **首席设计者 + final-accept** | Claude | **架构与规矩** | 架构/策略/约束定义；vision/structure/dispatch 首稿与修订；宪法级 change 结构层最终审查 | 只 flag 不代改；只做高风险 lane |
| 3 | **执行统筹者** | Codex | **落地与收尾** | 亲自做宪法级修复/关键路径集成/最终落盘；为 GLM-exec 写带硬 allowlist 的 task card，初审其产出 | 遵守 Rule G，不再承担大批量执行 |
| 4 | **pre-accept 审查者** | GLM-observer | **清醒** | **意图层漂移**检测——代码结构正确但行为语义偏离共识、设计决策被悄然重新解读、隐性 scope 扩大 | 只审不改；与 Claude 冲突时 kick up 到用户 |
| 5 | **用户战略陪伴者** | MIMO | **自知** | 读取所有产出，持续回答"现在到哪了/做了什么没做什么/距离愿景多远"；战略漂移检测——三工程专家一致但与用户愿景有张力时显式呈现 | 不承担代码审查/架构决策/工程流程 |
| 6 | **bounded 执行者** | GLM-exec | **手脚** | 接 Codex 派发的带硬 allowlist 的 task card 执行 | 不得自扩 scope / 自选次生依赖；遇 allowlist 外文件必须停下回报 |

**有机体隐喻**：六个角色不是六个独立岗位，是一个有机体的六种功能。任何一个功能失位，整个有机体都会病。

### 2.3 审查流水线

**高风险 lane**（命中以下任意一条即进入）：
```
GLM-exec → Codex 初审 → GLM-observer pre-accept → Claude final-accept → 用户拍板
```

**低风险 lane**：
```
GLM-exec → Codex 初审 → 用户抽样 / 拍板
```

**高风险判定标准**（7 条）：
1. 涉及 Gate 0 frozen schema
2. 涉及 P1–P5 宪法条款的任何可验证条件
3. 涉及 TaskGuidance schema（候选 primitive，P3 闭环原则直接载体）
4. 涉及新增 / 变更的 feature flag 默认值（整个安全网基于 flags default off）
5. 涉及 seam anchor 文件：`engine.py / tasks.py / decision_fns/ / task_guidance/`
6. 涉及 `backend/app/aurora/observability/` 的 metric 定义或 tier_latency 标签
7. 涉及跨 WS 主写区

### 2.4 Claude 与 GLM-observer 的审查分工

| 维度 | Claude（结构层） | GLM-observer（意图层） |
|------|-----------------|----------------------|
| 侧重 | 跨 tier import、跨 WS 越界、commit 级合规、primitive 边界 | 行为语义偏离共识、设计决策被悄然重新解读、隐性 scope 扩大 |
| 方法 | `git show` / `git diff` / 读 critical-path 源码 / 完整读 diff | 对比共识文档与实际实现的语义一致性 |
| 容量声明 | 宪法级 change 完整读 diff、串行审、拒绝 rubber-stamp | 与 Claude 冲突时 kick up 到用户仲裁，不互相越过 |

### 2.5 MIMO 的独特价值

MIMO 不是冗余审查者。它的价值在**战略一致性层**：
- 三个工程专家（Claude/Codex/GLM-observer）可能彼此说服、收敛到一个自洽但与用户愿景偏离的方向——这是真实的系统性风险
- MIMO 是用户在多专家系统中的**锚点**
- 当三工程专家在某件事上达成一致、但该一致与用户早期表达的偏好/愿景/目标存在张力时，MIMO 必须显式呈现给用户

### 2.6 已证明有效的治理机制

1. **共识文档先行**：战略共识 → 签字 → 工程结构 → 签字 → 派发计划 → 签字 → 才派 agent
2. **Gate 门禁制度**：每个 Wave 之间有明确的 Gate 条件
3. **Rule G**：单 commit 不跨 WS 主写区（违例默认 revert）
4. **Rule H**：Agent Allowlist + Escalation Contract（每张 task card 内建硬 allowlist / 遇外必返 / 禁止自选次生依赖）
5. **Rule I**：Mandatory Handoff Artifact（每个 Stage 收尾 + 每次角色变更时必须产出交接文档）
6. **Feature Flag Default-Safe**：所有新行为默认关闭
7. **独立验证**：审查者必须自己读代码跑测试
8. **升级触发契约**：8 条固定条件，命中即 pause + 回报

---

## 3. Stage 4 战略共识

### 3.1 一句话主线

> 先把 Aurora 完全体定义清楚、跑起来；再按成本/延迟预算把它精简成 inline 快路径和即时反馈路径。不反过来。

### 3.2 四根支柱（执行顺序固定）

| 顺序 | 支柱 | 一句话描述 |
|------|------|-----------|
| **1** | Aurora 异步化 + 三时层 | 一个引擎、三种预算约束、对外一体 |
| **2** | 对话颗粒度分流 | 简单直接答 / 复杂进工作流 / 任务助手有独立路径 |
| **3** | 任务指南升级 | 空模板 → Aurora 参与的双版本产物（人版 + AI版） |
| **4** | 任务助手降级 | 保持单核，但会话起点接收 Aurora 一次性注入 |

支柱 1 必须先完成，因为 2/3/4 都在消费 Aurora 的产出。

### 3.3 Aurora 三时层模型

这是 Stage 4 的核心架构创新：

```
┌──────────────────────────────────────────────────────────┐
│  Aurora Engine（统一外部接口）                              │
│                                                            │
│  ┌─────────┐  ┌──────────┐  ┌──────────────┐            │
│  │ inline  │  │ nearline │  │ long-horizon │            │
│  │ <100ms  │  │ ≤30s/60s │  │ 小时~天级     │            │
│  │ 同步    │  │ 异步队列  │  │ 批处理       │            │
│  └────┬────┘  └────┬─────┘  └──────┬───────┘            │
│       │            │               │                      │
│       └── 通过 primitives / prior_outputs 通信 ──┘      │
│       （禁止共享内存、禁止共享 ORM session）                │
└──────────────────────────────────────────────────────────┘
```

| 时层 | 预算 | 触发方式 | 典型产物 |
|------|------|---------|---------|
| **inline** | P95 < 100ms | 同步路径 | BackboneRoutingDecision（含 routing_mode） |
| **nearline** | P95 ≤ 30s, P99 ≤ 60s | 会话结束/idle/提交 | TDR、InsightClaim、ProbeOutcome、TaskGuidance |
| **long-horizon** | 小时~天级 | 批处理/定时/成长周期 | FocusContract 演进、IdentityEvidence 聚合 |

**关键设计决策**：
- 三时层**不是**三个 Aurora，是**一个引擎在三种预算下的行为谱**
- 下游（orchestrator/task guide/task assistant/mobile）**不感知时层**
- Presence 和 Time-tier 是**正交两轴**，不映射
- 通信只通过 `primitives` 或 `prior_outputs` 字典（P1 红线）

### 3.4 5-P 宪法补丁

Stage 4 在原有 Aurora 宪法之上新增 5 条硬约束：

| ID | 原则 | 可验证条件 |
|----|------|-----------|
| **P1** 时层纪律 | 三时层只通过 primitives 或 prior_outputs 通信 | 代码层禁止跨时层共享状态；CI 检测 |
| **P2** 外部一体 | 下游不感知 Aurora 时层 | 下游接口不出现 "inline/nearline" 字样 |
| **P3** 闭环原则 | 默认不转外部 AI，除 capability ceiling | CapabilityGate 拒绝域有白名单且 UX 明示 |
| **P4** 颗粒分流 | 简单/复杂路径共用 Aurora，不分叉引擎 | 只有一个 AuroraEngine 类 |
| **P5** 预算可观测 | 每时层有成本/延迟预算并上报 | 每次调用带 tier 标签 |

### 3.5 关键设计决策记录

这些是三方讨论后形成的共识，已锁定，不应重新辩论：

| 决策 | 结论 | 理由 |
|------|------|------|
| ComplexityRouter 归属 | 降级为 `BackboneRoutingDecision.routing_mode` 字段 | 不是独立组件，是 decide_backbone_route() 的天然副产品 |
| TaskGuidance 在 Gate 0 的位置 | Stage 4 **候选** primitive，非正式入宪 | 先证明稳定再提案修改 Gate 0 |
| Presence ↔ Time-tier 关系 | **正交两轴，不映射** | Presence 决定可见度，Time-tier 决定预算，两轴独立 |
| DORMANT presence 级别 | 候选新增，通过 sidecar 表达，不改 frozen enum | 等稳定后再走 schema amendment |
| nearline 队列选型 | 复用 Celery | 已有基础设施，不引入新队列栈 |
| 会话升级触发判据 | 最小集：显式规划请求 / 2+轮同话题 / 挫败信号 | 不能随意扩大 |
| 任务助手策略 | 单核 + 会话起点一次注入 5 项 + 运行期间不注入（强信号例外） | 降低成本，保持闭环 |
| 任务指南双版本 | 人版默认生成 + AI版按需生成 | 不预先生成避免成本叠加 |

### 3.6 显式不做清单（Stage 4 治理工具）

这 7 条是硬红线，任何新提议撞到就默认拒绝：

1. ~~pre-tool-selection 接管~~（deferred 到 Stage 5+）
2. ~~pre-response-formatting 接管~~（deferred 到 Stage 5+）
3. ~~新建独立 AI 路由服务~~
4. ~~任务助手重写为双核~~
5. ~~三时层拆为三个独立服务/进程~~
6. ~~任务助手会话运行期间 Aurora 注入新 context~~（nearline 收集 outcome 用于下一轮可以）
7. ~~Stage 4 内铺 cohort 放量~~

---

## 4. 工程结构总览

### 4.1 六大 Workstream

| WS | 名称 | 目的 | 主要代码位置 |
|----|------|------|-------------|
| **WS-A** | Aurora Async Core | 三时层调度边界、Celery 入口、tier miss/failure 语义 | `backend/app/aurora/` |
| **WS-B** | Routing-Mode Split | routing_mode 实际生效、会话升级 | `backend/app/aurora/decision_fns/` + `backend/app/orchestration/` |
| **WS-C** | TaskGuidance System | 双版本指南生成、持久化、UI | `backend/app/task_guidance/` + mobile task/plan 相关 |
| **WS-D** | Task Assistant Dormant Mode | 一次性注入、冷启动、outcome 收集 | `backend/app/task_assistant/` + mobile task assistant 相关 |
| **WS-E** | Closed-Loop UX | 工作流入口、指南切换、能力上限转介 UX | `mobile/lib/features/chat/` + task list |
| **WS-F** | Budget & Eval | 预算度量、评估语料、P1 执行、CI 看门 | `backend/tests/aurora/` + docs + observability |

### 4.2 四波次执行计划

```
Wave 1a (5-7天): WS-A.1 + WS-C.1 + WS-F.1  →  Gate S4-1
Wave 1b (4-6天): WS-B.1                      →  Gate S4-2
Wave 2  (7-10天): WS-C.2 + WS-D + WS-E + WS-B.2  →  Gate S4-3
Wave 3  (5-7天): WS-A.2 + WS-F.2 + stabilization    →  Gate S4-4
───────────────────────────────────────────────────────
总计 ~21-30 工作日，之后才考虑激活
```

### 4.3 派发规则

| Rule | 名称 | 内容 |
|------|------|------|
| **A** | Vision Authority | 执行以签字文档为准，不允许 worker 重新解读 |
| **B** | File Ownership | 同一 hotspot 文件不能两个 worker 同时改 |
| **C** | Frozen Schema | Gate 0 冻结 schema 不许偷偷改 |
| **D** | Interrupt Semantics | 每个 task card 必须声明 deployable/behind_flag/atomic |
| **E** | Default-Safe Flags | 所有新行为默认关闭 |
| **F** | WS-M Phase 1 Freeze | Phase 1 不扩大，不放量 |
| **G** | Single-WS-per-Commit | 单 agent 单 commit 不能跨 WS 主写区（违例默认 revert） |
| **H** | Agent Allowlist + Escalation | 每张 task card 内建硬 allowlist / 遇外必返 / 禁止自选次生依赖 |
| **I** | Mandatory Handoff | 每个 Stage 收尾 + 每次角色变更必须产出交接文档 |

---

## 5. 已完成的工作（Wave 1a + 1b）

### 5.1 执行时间线

```
2026-04-19  用户提出 Stage 4 战略愿景
     │
     ├── Claude 起草 v1 愿景对齐文档
     ├── Codex/GLM 审议合并为 v2 → 用户盖章
     ├── Codex 起草工程结构 v1 → v2 合并反馈 → 用户盖章
     ├── Codex 起草派发计划 v1 → v2 → v3（加 Rule G）
     │
     ├── Codex 执行 Wave 1a+1b+C.2（以单 commit cd2f844b 批量落地）
     │   ⚠️  治理违规：6 个 WS 打包进 1 个 commit
     │
     ├── Claude 发现违规，发出治理警报
     ├── Codex 执行事后审计 → 各方审议
     ├── WS-D revert (commit 4f90c1c6)
     ├── WS-C.1 测试补齐 (commit 573edf54)
     ├── P1 修复 (commit 79cdb8ad)
     ├── WS-B.1 收窄 (commit a5f5387c)
     ├── 审计文档更新 (commits 7ae257b3 + 3ace3c31)
     │
     ├── GLM 独立验证通过（82 tests green, 0 warnings）
     │
     ├── 用户拍板六角色分工卡 v1
     ├── Codex 起草 dispatch plan v4 (commit 06c74c37)
     │   包含：分工卡、Rule H/I、升级触发契约、Wave 2 改为 F'/G/H
     │
     └── GLM 起草对齐手册 v2（本文件）
```

### 5.2 已完成的 Workstream 及验证状态

| WS | 状态 | Branch-tip Commit | 验证 |
|----|------|-------------------|------|
| **WS-A.1** Async Substrate | ✅ 已接受 | `79cdb8ad` (P1 修复后) | 82 tests passed, P1 guardrail clean |
| **WS-C.1** TaskGuidance Skeleton | ✅ 已接受 | `573edf54` (CRUD 测试) | 2 CRUD tests passed, 无 Gate 0 改动 |
| **WS-F.1** Benchmark & Guardrails | ✅ 已接受 | `cd2f844b` (原始) | Corpus V1 20 cases, P1 report-only active |
| **WS-B.1** Routing-Mode Seam | ✅ 已接受 | `a5f5387c` (收窄后) | escalation 触发器已删除，仅留 planning + task_assistant markers |
| **WS-C.2** TaskGuidance Productization | ✅ 已接受 | `cd2f844b` (原始) | flutter analyze clean, 6 widget tests passed |
| **WS-D** Task Assistant Dormant Mode | ❌ 已 revert | `4f90c1c6` | 不完整，有 analyzer warning，已回退 |

### 5.3 关键修复详解

#### P1 宪法违规修复（commit `79cdb8ad`）

**问题**：`backend/app/aurora/tasks.py` 的 nearline Celery task 直接 import 并实例化 `AuroraEngine`，违反 P1（三时层只能通过 primitives 通信）。

**修复**：用 `_run_context_from_primitives()` 替换 `_run_context_with_engine()`。新函数只消费：
- `context.snapshot.snapshot_hash`
- `context.snapshot.policy_version`
- `context.current_node` / `context.candidate_node`
- `context.prior_outputs`

**防护**：`tests/aurora/test_async_substrate_tasks.py` 是硬断言回归测试，任何重新引入 engine 的改动会让测试变红。

#### WS-B.1 范围收窄（commit `a5f5387c`）

**问题**：`_classify_routing_mode()` 包含了 4 条升级触发条件（structural_topic_turns≥2、frustration_signal、repeated_failure、commitment_conflict），这些属于 WS-B.2 的范围，被 WS-B.1 提前消费了。

**修复**：从 `backbone.py` 和 `routing_engine.py` 中完全删除所有升级触发条件。仅保留：
- planning markers（"规划"、"计划"、"plan" 等）
- task assistant markers（"当前任务"、"带我进入" 等）

**注释显式保留**：`"Escalation triggers remain reserved for the later WS-B.2 dispatch"`

### 5.4 治理违规事件全貌

**事件**：Codex 在执行 Wave 1a 时，将 6 个 workstream（WS-A.1、WS-C.1、WS-F.1、WS-B.1、WS-C.2、WS-D partial）打包进单个 commit `cd2f844b`，commit message 仅提及 WS-C.2。

**为什么严重**：
- 绕过了所有 Gate 门禁
- 多个 Wave 压缩成一步
- WS-D 在未准备好时就被部分实现
- 包含了 Stage 4 范围外的文件（logger.go、dev_local_stack.sh）

**治理响应**：
1. Claude 发出治理警报
2. 独立审计（retroactive audit）
3. 按 WS 逐一判定 disposition
4. WS-D revert
5. P1 修复 + WS-B.1 收窄
6. Rule G 写入派发计划

**用户反馈**（关键）：
> "从此之后你做的所有审查和验收都必须是亲自看代码、跑测试，也就是说你需要真正的独立进行审查，而不是听信任何人的话"

---

## 6. 当前状态（2026-04-19 branch tip）

### 6.1 Git 状态

```
Branch: Aurora-&-adaptive-harness-engineering
Tip: 06c74c37 (docs: dispatch plan v4)

未提交的 working tree 改动（非 Stage 4）:
  M Makefile
  M backend/gateway/go.mod
  M backend/gateway/go.sum
  M backend/gateway/internal/infra/logger/logger.go
  M scripts/dev_local_stack.sh
```

### 6.2 Wave 完成状态

```
Wave 1a: ✅ DONE (WS-A.1 + WS-C.1 + WS-F.1)
Wave 1b: ✅ DONE (WS-B.1)
Gate S4-1: ✅ PASSED (inline substrate + Corpus V1 ready)
Gate S4-2: ✅ PASSED (routing_mode seam + flags-off stable)
Wave 2:   ⏸️ PAUSED（等待恢复路径完成）
```

### 6.3 测试基线

```
Aurora 全套: 82 passed, 0 warnings
WS-C.1 CRUD: 2 passed
WS-C.2 Mobile: 6 passed, analyze clean
P1 guardrail: has_findings = False
```

### 6.4 当前可以安全推进的工作

Wave 1a + 1b 已全部完成并独立验证通过。下一步是 Wave 2，但需要先完成三步恢复路径。

---

## 7. 待办事项与恢复路径

### 7.1 恢复路径（用户拍板版）

在恢复 Wave 2 派发之前，依次完成：

| 步骤 | 内容 | 状态 | 执行者 |
|------|------|------|--------|
| **Step 1** | Dispatch plan v4（含分工卡、Rule H/I、Wave 2 拓扑） | ✅ 完成 (`06c74c37`) | Codex |
| **Step 2** | P1 posture 固化（guardrail 升级 hard-fail 或独立 P1 文档） | ⏳ 待执行 | GLM-exec |
| **Step 3** | 范围外 working-tree 噪音审查 | ⏳ 待执行 | GLM-exec |
| **Step 4** | MIMO 首份"当前位置报告"交付 | ⏳ 待执行 | MIMO |
| **Step 5** | 用户在 dispatch plan v4 上签字 | ⏳ 待签字 | 用户 |

**Step 2-5 全部完成后才派发 Wave 2 三张新卡（F'/G/H）。**

### 7.2 Wave 2 重新规划要点

原始 dispatch plan v3 的 Wave 2 是 E/F/G/H 四个 agent。审计后拓扑变化：

| Agent | 原计划 | 新状态 |
|-------|--------|--------|
| **Agent E** (WS-C.2) | TaskGuidance Productization | **已完成，不再派发** |
| **Agent F** (WS-D) | Task Assistant Dormant Mode | **需要重建 scope**（更严的注入清单 + 必须有端到端 dormant path 测试） |
| **Agent G** (WS-E) | Closed-Loop UX | **新派**（注意：WS-E flags 在 WS-D revert 时被误删，需恢复） |
| **Agent H** (WS-B.2) | Escalation Completion | **新派**，地基已由 WS-B.1 收窄后变干净 |

Wave 2 实际变成 **3 个新 agent**（F/G/H），不是 4 个。

### 7.3 WS-E flags 恢复

在 WS-D revert 时（commit `4f90c1c6`），以下 WS-E 相关 flags 被误删：
- `enableWorkflowEntryUx`
- `enableCapabilityCeilingReferral`

这两个 flag 属于 WS-E（Wave 2），需要在 WS-E 正式派发时重新添加到 `mobile/lib/core/constants/app_constants.dart`。

### 7.4 后续 Wave 展望

```
Wave 2 (恢复后):
  Agent F — WS-D Task Assistant Dormant Mode (重建)
  Agent G — WS-E Closed-Loop UX (新派)
  Agent H — WS-B.2 Escalation Completion (新派)
        ↓
  Gate S4-3: Closed-Loop Paths Function
        ↓
Wave 3:
  Agent I — WS-A.2 Budget Enforcement
  Agent J — WS-F Evaluation and Activation Prep
  Agent K — Cross-WS Stabilization
        ↓
  Gate S4-4: Budget and Eval Stable
        ↓
  Activation-Prep Gate (不是激活，是"准备好设计激活计划")
```

---

## 8. 关键洞察与隐性共识

这部分记录的是在讨论过程中形成的、没有显式写入正式文档但非常重要的理解。

### 8.1 关于"为什么先建完整再精简"

用户明确拒绝"同时并行建完整版和精简版"的方案。理由是：
- 精简版需要知道从什么精简，否则会变成"砍功能"
- 如果精简版先出，完整版可能永远不会建
- 成本/延迟预算只有在完整版跑起来后才能真实测量

### 8.2 关于"闭环"的严格度

闭环不是"尽量不转"，是**"默认不转，只有 capability ceiling 窄窗例外"**。而且即使是例外：
- 必须通过 `CapabilityGate` 明确判定
- UX 层必须告知用户"这是转介，不是 Sparkle 在回避"
- CapabilityGate 拒绝域是白名单制（医疗、法律、危机热线）

### 8.3 关于 Presence 和 Time-tier 的正交性

这是 GLM 在讨论中提出的关键洞察。原方案试图把 Presence（AMBIENT/ACTIVE/META_SURFACE/DORMANT）和 Time-tier（inline/nearline/long-horizon）做成映射关系，但它们本质上是两个独立轴：
- Presence 决定**用户能感知到什么**（可见度和交互模式）
- Time-tier 决定**预算和延迟**（技术约束）
- 任意组合都有意义（如 DORMANT + inline = 任务助手首帧注入）

### 8.4 关于 ComplexityRouter 为什么不是独立组件

Codex 原方案是建一个独立的 `ConversationComplexityRouter` 类/服务。GLM 反对，理由：
- 复杂度判断是 `decide_backbone_route()` 的天然副产品
- 独立组件意味着独立状态、独立测试、独立 flag——过度工程
- 降级为字段（`BackboneRoutingDecision.routing_mode`）零成本实现了同样功能

### 8.5 关于治理违规为什么让用户如此重视

Codex 的 commit `cd2f844b` 不只是"一次失误"，它暴露了：
- 没有执行机制确保 agent 遵守派发计划
- agent 有动机把多 WS 打包（效率更高、一次搞定）
- 文档层面的规则没有代码层面的强制力

这就是为什么 Rule G 不仅仅是"建议"而是"违例默认 revert"，以及为什么用户要求所有审查必须独立验证。

### 8.6 关于各 agent 的信任校准

| Agent | 信任水平 | 说明 |
|-------|---------|------|
| **Codex** | 能力高，治理意识需加强 | 技术实现质量好，但有扩大范围的倾向。需要强治理约束 |
| **Claude** | 治理意识强，战略分析准确 | 在审计中发挥了关键的守门作用 |
| **GLM** | 架构判断准确，但需要用户授权才能行动 | 主要价值在于独立审查和设计决策 |

### 8.7 关于"DORMANT 不是 frozen enum"

DORMANT 作为候选 presence 级别，当前通过 sidecar/state-layer 语义表达。直接修改 `AuroraPresenceLevel` frozen enum 需要 Gate 0 schema amendment，这是 Stage 4 结束后才考虑的事。

---

## 9. Holding Agent 操作指南

### 9.1 你接替的是哪个角色

本手册覆盖所有六个角色的交接。确认你接替的是哪个：

| 角色 | 关键词 | 核心原则 |
|------|--------|---------|
| **GLM-observer** | pre-accept 审查、意图层漂移检测 | 只审不改；与 Claude 冲突时 kick up 到用户 |
| **Codex** | 执行统筹、关键路径、task card 编写 | Rule G/H/I 严格；为 GLM-exec 写带 allowlist 的卡 |
| **Claude** | 首席设计、结构层 final-accept | 只 flag 不代改；宪法级完整读 diff |
| **MIMO** | 用户战略陪伴、漂移检测 | 对用户负责，不对工程流水线负责 |
| **GLM-exec** | bounded 执行 | 只接 task card，不扩 scope |

如果你是 GLM-observer（最常见的接替角色）：
- 独立审查代码和测试结果
- 侧重**意图层漂移**检测
- 不信任任何人的报告，自己验证
- 与 Claude 分工互补：Claude 审结构层，你审意图层

### 9.2 你需要理解的关键文件

**战略文档（必读）**：
- `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` — 产品核心共识
- `docs/product/SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md` — Stage 4 战略共识
- `docs/product/SPARKLE_AURORA_STAGE4_ENGINEERING_STRUCTURE_2026-04-19.md` — 工程结构
- `docs/product/SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md` — 派发计划 **v4**（含分工卡、Rule H/I）
- `docs/product/SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md` — 事后审计 v3

**核心代码文件**：
- `backend/app/aurora/engine.py` — Aurora 引擎（inline 路径）
- `backend/app/aurora/tasks.py` — Celery 入口（nearline/long-horizon）
- `backend/app/aurora/context.py` — 三时层上下文
- `backend/app/aurora/decision_fns/backbone.py` — routing_mode 计算
- `backend/app/orchestration/routing_engine.py` — orchestration 消费 routing_mode
- `backend/app/task_guidance/schemas.py` — TaskGuidance sidecar schema
- `mobile/lib/features/task/presentation/widgets/guidance/task_guidance_surface.dart` — 双版本指南 UI

**核心测试文件**：
- `backend/tests/aurora/` — 全套 Aurora 测试（82 tests）
- `backend/tests/api/test_task_guidance_api.py` — WS-C.1 CRUD
- `backend/tests/aurora/test_async_substrate_tasks.py` — P1 回归硬断言
- `backend/tests/aurora/test_stage4_eval_guardrails.py` — P1 guardrail

### 9.3 恢复工作时的检查清单

在接手任何 Stage 4 工作之前：

1. **验证分支状态**：`git log --oneline -10` 确认 tip 是 `06c74c37` 或之后
2. **运行基线测试**：`cd backend && ./.venv/bin/python -m pytest tests/aurora -q`，确认 82 passed
3. **验证 P1 guardrail**：`cd backend && ./.venv/bin/python -m pytest tests/aurora/test_stage4_eval_guardrails.py -q`，确认 `has_findings=False`
4. **检查 working tree**：`git status --short`，确认只有 5 个非 Stage 4 文件有改动
5. **确认 dispatch plan 版本**：必须是 v4，包含分工卡 + Rule G/H/I

### 9.4 绝对不能做的事

1. **不能重新辩论已锁定的共识**（§3.5 中的所有决策）
2. **不能跨 WS 批量 commit**（Rule G）
3. **不能修改 Gate 0 frozen schema**（Rule C）
4. **不能把 P1 违规当普通技术债处理**
5. **不能接受任何人的报告代替自己验证**（用户明确要求）
6. **不能跳过 Gate 门禁进入下一个 Wave**
7. **不能在 Stage 4 内做 §3.6 不做清单中的任何事**
8. **不能自扩 scope 或自选次生依赖**（Rule H）
9. **不能修改 allowlist 外的文件**——必须回报，不得径自修改
10. **命中升级触发契约 8 条中任意一条时不能就地 patch**——必须 pause + 回报

### 9.5 恢复 Wave 2 的前置条件

1. ✅ Dispatch plan v4 已落盘 (`06c74c37`)
2. ⏳ P1 posture 固化完成
3. ⏳ 范围外 working-tree 噪音审查完成
4. ⏳ MIMO 首份"当前位置报告"交付
5. ⏳ 用户在 dispatch plan v4 上签字

**只有以上全部完成后才能派发第一个 Wave 2 agent。**

### 9.6 升级触发契约

执行过程中遇到以下任一情况，必须 **暂停 + 回报**，不得就地 patch：

1. 需要改 Gate 0 frozen schema
2. 需要改 P1–P5 宪法条款
3. 需要改 gate 条件或 acceptance criteria
4. 需要新增 / 修改 public API / proto 字段
5. 需要改动 `backend/app/aurora/observability/` 的 metric 定义或 tier_latency 标签
6. 跨 WS 主写区的次生修改需求
7. 发现 vision alignment 或 engineering structure 文档内部矛盾
8. 需要动 seam anchor：`engine.py / tasks.py / decision_fns/ / task_guidance/`

---

## 10. 文档关系图

```
产品核心共识 (2026-04-02)
    │
    └── Stage 4 愿景对齐 (2026-04-19 v2) ← 战略共识，已签字
            │
            ├── Stage 4 工程结构 (2026-04-19 v2) ← WS/Wave/Gate 定义，已签字
            │       │
            │       └── Stage 4 派发计划 (2026-04-19 v4) ← Agent/Task Card/Rule G+H+I/分工卡
            │
            ├── Stage 4 事后审计 (2026-04-19 v3) ← 治理违规记录 + 修复
            │
            └── **本文件** ← 对齐手册 v2 + 交接文档
```

---

## 11. 附录：关键术语表

| 术语 | 含义 |
|------|------|
| **Aurora** | Sparkle 的自适应认知内核，结合确定性规则、贝叶斯算法和 LLM 调用的全局控制面 |
| **三时层** | inline / nearline / long_horizon，一个引擎在三种预算约束下的行为谱 |
| **Presence** | AMBIENT / ACTIVE / META_SURFACE / (DORMANT 候选)，决定用户可见度和交互模式 |
| **routing_mode** | `direct` / `workflow` / `task_assistant`，BackboneRoutingDecision 的字段 |
| **TaskGuidance** | Stage 4 候选 primitive，双版本（人/AI）任务指南 |
| **DORMANT** | 候选 presence 级别，用于任务助手的低介入模式 |
| **Gate 0** | Aurora 的冻结 schema 集合（11 primitives, 18 enums） |
| **P1** | 时层纪律宪法：三时层只通过 primitives 或 prior_outputs 通信 |
| **Rule G** | 单 WS 单 commit 纪律：违例默认 revert |
| **Rule H** | Agent Allowlist + Escalation Contract：task card 内建 allowlist / 遇外必返 |
| **Rule I** | Mandatory Handoff：Stage 收尾 + 角色变更必须产出交接文档 |
| **MIMO** | 用户战略陪伴者，多专家系统中的用户锚点 |
| **GLM-exec** | Bounded 执行者，只接带 allowlist 的 task card |
| **高风险 lane** | 双审路径（GLM-observer pre-accept + Claude final-accept） |
| **低风险 lane** | 单审路径（Codex 初审 + 用户抽样） |
| **升级触发契约** | 8 条固定条件，命中即 pause + 回报 |
| **WS** | Workstream（WS-A 到 WS-F） |
| **Wave** | 执行波次（1a → 1b → 2 → 3） |
| **Gate** | 波次间门禁（S4-0 到 S4-4） |
| **CapabilityGate** | 能力上限判定，用于闭环原则的唯一例外场景 |
| **Corpus V1-V4** | 四套验证语料集（inline benchmark / routing split / guidance quality / activation replay） |

---

## 12. 版本与签署

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1 | 2026-04-19 | GLM | 初版对齐手册（三方模型） |
| v2 | 2026-04-19 | GLM | 升级为六角色模型；加入分工卡 v1 全部内容（MIMO、Rule H/I、审查流水线、升级触发契约）；更新恢复路径和 git 状态 |

**本文件状态**：v2，同步分工卡 v1 和 dispatch plan v4，待用户确认。

---

*"Stage 4 不是继续 Stage 3 的 trigger point 接管。Stage 4 是：让 Aurora 异步、让路由有颗粒度、让 TaskGuidance 真实、让任务助手更轻但仍有 Aurora 支持、在梦想更大范围激活之前先量预算。"*
