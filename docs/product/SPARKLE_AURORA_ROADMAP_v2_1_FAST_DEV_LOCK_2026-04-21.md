# SPARKLE Aurora Roadmap v2.1 Fast-Dev Lock (2026-04-21)

> Status: locked execution table for Stages 23-32
> Companion docs:
> - [SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md)
> - [SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md)

## 1. Stage Lock Table

### Stage 23｜Bayesian wire-on + SS-AUDIT 解锁

- 性质：新能力
- 前置：Stage 22 Gate FINAL 绿；数据利用 `>= 7.0`；`routing_decision_log` 密度达门槛
- 核心 WS：
  - `WS-BY-SOURCE-STATE`
  - `WS-BY-SQAM`
  - `WS-BY-LEARNER`
  - `WS-BY-CONSUMER`
  - `WS-BY-SHADOW`
- Rule：复用 Rule `W`
- Gate：SQAM 四维门槛全过 + shadow `KL < 0.05` + Router A/B `KL <= 0.03`
- 对下一阶段义务：Stage 24 消费 Bayesian outcome 作为 accountability 合规反馈信号

### Stage 24｜Accountability Policy Compiler 完整版

- 性质：完成 Stage 17 MVP
- 前置：Stage 23 outcome 流稳定
- 核心 WS：
  - `WS-AP-COMPILER`
  - `WS-AP-SCHEDULER`
  - `WS-AP-AUDIT`
  - `WS-AP-UI`
- 新 Rule `AG`：Policy compiler 禁 LLM；承诺状态变更必留审计；到期通知禁情绪操控
- Gate：编译器 `0` LLM 调用；审计记录 `1:1`；UI 撤回路径 `<= 2 tap`
- 对下一阶段义务：Reflection 可消费 accountability 失败事件

### Stage 25｜Reflection Wire-On

- 性质：扩展既有 reflection 栈
- 前置：Stage 22 OutcomeVerifier Celery 化 + Stage 23 outcome 流
- 核心 WS：
  - `WS-RF-READ-API`
  - `WS-RF-INJECT`
  - `WS-RF-ANALYSIS`
  - `WS-RF-QUALITY`
- 新 Rule `AH`：AI 自生 reflection 内容禁直接进 next-turn few-shot；需用户确认或 `>= 7d` 冷却
- Gate：冷数据 `>= 30` 案例；reflection → next-action 采纳率 `>= 0.6`
- 对下一阶段义务：Stage 26 Scene 聚类消费 reflection 作为场景边界信号

### Stage 26｜Scene Consolidation

- 性质：新增能力
- 前置：Stage 25 reflection 语义密度达标
- 核心 WS：
  - `WS-SC-CELL`
  - `WS-SC-CLUSTER`
  - `WS-SC-SCENE`
  - `WS-SC-CONSOLIDATE`
  - `WS-SC-RETRIEVAL`
- 新 Rule `AI`：Scene 聚类幂等；必须带时序锚；禁止脱 `evidence_token`
- Gate：幂等测试通过；Scene 召回精度 `>= 0.75`
- 对下一阶段义务：Stage 27 Foresight 消费 Scene 历史模式

### Stage 27｜Foresight Engine

- 性质：新增能力
- 前置：Stage 26 Scene 上线 + Stage 23 Bayesian 数据充分
- 核心 WS：
  - `WS-FS-ATTRACTOR`
  - `WS-FS-FORESIGHT`
  - `WS-FS-JITAI`
  - `WS-FS-PUSH-INTEGRATE`
  - `WS-FS-KILL`
- 新 Rule `AJ`：foresight 禁作 Router 分支条件；进 prompt 必带 confidence；JITAI 需用户同意或默认静音
- Gate：预测对齐率 `>= 0.55`；接受率 `>= 0.4`；Router `0` 命中 foresight 分支
- 对下一阶段义务：Stage 28 Traits 可消费 foresight 预测历史

### Stage 28｜Traits 弱先验层

- 性质：新增能力
- 前置：Stage 27 行为观测充分
- 核心 WS：
  - `WS-TR-ONBOARD`
  - `WS-TR-NLP-OBSERVE`
  - `WS-TR-STORAGE`
  - `WS-TR-AGGREGATOR`
  - `WS-TR-OVERRIDE`
- 新 Rule `AK`：traits 置信度永不 `> 0.3`；禁在 UI 贴标签；Dynamic State 始终优先；禁入 Router 分支
- Gate：置信度越界 `0`；traits 标签外显 `0`；冲突解决契约 green
- 对下一阶段义务：Stage 29 可低置信参考 traits 倾向

### Stage 29｜SRL 三阶段扩展

- 性质：重构 + 新增
- 前置：Stage 28 traits 初值可用
- 核心 WS：
  - `WS-SR-TRACKER`
  - `WS-SR-PHASE-DETECT`
  - `WS-SR-SCAFFOLD-EXTEND`
  - `WS-SR-SDT-POLICY`
  - `WS-SR-EFFICACY-REPAIR`
- 新 Rule `AL`：SDT 话术禁命令式；连续共情回复 `<= 2` 轮，第 3 轮必须转向客观镜像 / 行动选项 / 认知重构
- Gate：SDT 话术 CI `0` 命令式；第 3 轮转向率 `>= 0.9`；三阶段转移事件 `>= 20`
- 对下一阶段义务：Stage 30 Metacognition 消费 SRL Reflection 阶段窗口

### Stage 30｜Metacognition 三维偏差扩展

- 性质：扩展
- 前置：Stage 29 Reflection 阶段结构化入口可用
- 核心 WS：
  - `WS-MC-TIME-BIAS`
  - `WS-MC-DIFFICULTY-BIAS`
  - `WS-MC-CONFIDENCE-BIAS`
  - `WS-MC-MIRROR`
- 新 Rule `AM`：禁临床诊断词；输出必须客观数据镜像，禁人格归因
- Gate：三维偏差稳定采样 `>= 50`；临床词黑名单 `0`；dashboard UI 审计ผ่าน
- 对下一阶段义务：Stage 31 以三维偏差为节点输入

### Stage 31｜Idiographic Lite

- 性质：新增能力弱化版
- 前置：Stage 23 wire-on 完成 + 每用户 `>= 150` 次完整 decision→outcome 对，覆盖 `>= 5` 个行为变量
- 核心 WS：
  - `WS-ID-NODE`
  - `WS-ID-ASSOCIATION`
  - `WS-ID-HUB`
  - `WS-ID-INTERVENTION`
- 新 Rule `AN`：禁声称因果；禁跨用户迁移；置信度低于阈值不得进入提示
- Gate：密度门槛通过；因果声明扫描 `0`；采纳率 `>= 0.3`
- 对下一阶段义务：Stage 32 决定 Idiographic 是否纳入 CL SQAM

### Stage 32｜Track B CL SQAM 扫尾

- 性质：CL Track B 收尾
- 前置：Stage 22-31 全绿；期间 CL baseline regression 无报警
- 核心 WS：
  - `WS-SQ-PROMPT-BANDIT`
  - `WS-SQ-DISTILLER`
  - `WS-SQ-MULTI-DIM`
  - `WS-SQ-STRATEGY-STORE`
- Rule：复用 Rule `W`
- Gate：4 组件各自产出 SQAM 报告，并给出 `green / conditional / blocked` 判定

## 2. Fast-Dev 协议

### 2.1 角色分工

| 角色 | 职责 |
| --- | --- |
| 用户 | 阶段性汇报 + 调度 Codex + 拍板架构升级类决策 |
| Codex | 按锁定表执行 Stage 22 → 32 |
| GLM-observer | Rule 合规 / 边界 / 前债治理审查 |
| GLM1 | 代码事实核查 / WS claim 对照 |
| 架构师 | 仅在升级类冲突、Path C、Rule 立法、阶段重排、跨 stage 架构冲突时介入 |

### 2.2 架构师介入触发条件

1. GLM1 / observer 结论冲突
2. 任一 Path `C` 触发
3. 发现新 Rule 需求（超出 `AG-AN`）
4. Stage N 入场义务无法满足
5. 跨 stage 架构冲突
6. 路线图范围外战略转向

### 2.3 架构师不介入的情形

1. 单个 WS 实现细节
2. 单次测试红 / 绿
3. commit 规约合规性
4. 日常 carry-forward 清理
5. Stage N+1 dispatch 文书本身

### 2.4 阶段性汇报模板

```text
Stage N closeout report
- commit chain: <hash1> <hash2> <hash3>
- run_stageN.sh: PASS/FAIL
- gate_final.sh: PASS/FAIL
- targeted sweep: N passed
- GLM-observer verdict: ACCEPT CLEAN / CONDITIONAL / REJECT
- GLM1 verdict: ACCEPT CLEAN / CONDITIONAL / REJECT
- carry-forward: [list] or CLEAN
- architect intervention needed: YES/NO
```

### 2.5 应急协议

1. 超过 2 个 stage 未收尾：触发 health check
2. 同时命中 `>= 2` 条 Rule：Codex 立即停
3. 出现战略转向：由 v2.2+ amendment 重排

## 3. 路线外候选项

以下候选保持观察，不进入 Stage 22-32 fast-dev 主线：

1. Reflexion-style verbal reflection buffer 独立化
2. EverMemOS Profile & Foresight 二期
3. 多 Agent subagent 架构
4. Skill marketplace
5. Voyager 式代码执行 skill
