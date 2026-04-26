# Aurora MVP Engineering Scope — Exam Sprint Mode Phase 1

> **Status**: DRAFT — 工程范围收束稿  
> **Date**: 2026-04-25  
> **Scope**: Aurora / Exam Sprint Mode 第一阶段工程切片  
> **North Star**: 7 天内帮助一位基础薄弱的大学生通过《计算机网络》考试  
> **Depends On**: `SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md`, `backend/app/orchestration/exam_sprint_policy.py`

---

## §0 核心判断

Aurora 在第一阶段不应被实现为“更聪明的聊天人格”，而应被实现为 **Exam Sprint Mode 的控制平面**。

第一阶段的职责划分如下：

- **Aurora 控制平面**：维护状态、做唤醒判断、控制上下文装配、调节表达和教学策略、决定是否重规划、写入短期与冲刺期记忆
- **标准教学执行平面**：讲题、答疑、出题、批改、生成任务卡、推进每日计划
- **强模型介入条件**：状态冲突、策略失效、目标漂移、考前高风险、用户明确要求重校准

这一定义与 Aurora Runtime v1 的三层架构兼容：Aurora 继续做认知与控制，标准层继续负责可见交互。

---

## §1 MVP 边界

### 1.1 第一阶段必须做

第一阶段锁定为：

- 学科：**计算机网络**
- 模式：**7 天冲刺**
- 目标模式：**minimum_pass / 先过**
- 运行原则：**轻量 Aurora 每轮必跑，中等/完全态按需唤醒**

必须交付的能力：

1. 冷启动 intake + 资料接入
2. Diagnostic Quiz v1
3. Computer Networks Sprint Pack v1
4. AuroraControlSignal v1
5. State Store v1
6. Task Card Generator v1
7. Quiz / Grade / Mistake Analyzer v1
8. 错因驱动的局部重规划
9. 每日 checkpoint
10. 简版显性 Aurora 校准

### 1.2 第一阶段明确不做

- 多学科同时上线
- 长期人格式陪伴 Aurora
- 复杂关系模型 UI
- 每轮都运行强模型
- 跨学期长期成长档案
- 复杂多 agent 编排
- 自动化长期画像写入

### 1.3 为什么先做“计算机网络 + 7 天通过率模式”

- 高频题型清晰，ROI 易排序
- 既有概念题，也有流程题与计算题，适合验证控制层价值
- 最小通过路径可定义，不容易被“学得很全”误导
- 可较快验证 Aurora 是否真的提高任务完成率、错因修复率和通过概率

---

## §2 产品形态：控制平面 + 教学执行平面

### 2.1 一句话架构

`Aurora = State Store + Wake Policy + Context Router + Strategy Engine + Model-Write Pipeline + Visible Calibration UX`

### 2.2 双平面职责

| 平面 | 负责什么 | 不负责什么 |
|---|---|---|
| **Aurora 控制平面** | 状态判断、路径选择、教学参数控制、主动介入、重规划、状态写入 | 直接长篇讲题、每轮生成所有用户可见回复 |
| **教学执行平面** | 讲解、出题、批改、任务推进、任务卡展示 | 自行猜测用户画像、自己决定是否大重规划 |

### 2.3 总体数据流

```text
用户输入 / 任务反馈 / 小测结果 / 上传资料 / 时间事件
        ↓
Event Normalizer
        ↓
Silent State Updater
        ↓
Light Aurora Turn Router
        ↓
AuroraControlSignal v1
        ↓
Context Assembler + Strategy Engine
        ↓
Standard Teaching Layer
        ↓
Task Result / Quiz Result / Telemetry
        ↓
Model-Write Pipeline
        ↓
必要时触发 AuroraWakeRequest → Medium / Full Aurora
```

---

## §3 端到端用户闭环

### 3.1 冷启动

冷启动最多只问 6 个必要问题：

1. 哪门课，考试日期是什么
2. 目标是先过、保分还是冲高
3. 范围、老师重点、往年题是否可用
4. 当前基础与最怕章节
5. 每天真实可用时间
6. 是否存在不可学习时段

同时鼓励上传：

- 课件
- 复习提纲
- 作业题
- 往年卷
- 老师划重点
- 错题照片

### 3.2 初始诊断

诊断目标是 triage，不是做完整分班测试。

- 时长：10-25 分钟
- 题量：8-15 题
- 覆盖：高频概念、高频计算/流程、1-2 个综合题
- 每题附带信心自评

输出：

- `estimated_score_now`
- `pass_probability`
- `top_bottlenecks`
- `mistake_clusters`
- `recommended_path`

### 3.3 冲刺执行闭环

完整闭环如下：

1. 冷启动 intake
2. 资料解析与 exam scope 抽取
3. Sprint Pack 匹配
4. Diagnostic Quiz
5. 最小通过路径选择
6. 生成 Day 1 任务卡
7. 用户执行任务
8. 小测批改与错因分析
9. Aurora 控制层更新状态
10. 局部重规划或继续推进
11. 每日 checkpoint
12. 考前 24h 切换到 last-24h 策略

---

## §4 核心模块清单

| 模块 | 职责 | 第一阶段是否必须 | 备注 |
|---|---|---|---|
| `State Store v1` | 存用户、目标、情境、自我、知识、任务、错因状态 | 必须 | Phase 1 只保留冲刺期关键字段 |
| `Light Aurora Turn Router` | 每轮生成 `AuroraControlSignal` | 必须 | 低成本、同步 |
| `Context Assembler` | 决定加载什么，不加载什么 | 必须 | 只装配压缩态 |
| `Strategy Engine v1` | 决定先问/先答/先诊断、做题还是补概念 | 必须 | 对接 Sprint Pack |
| `Sprint Pack Adapter` | 提供学科路径、题型、错因、模板 | 必须 | Phase 1 仅计网 |
| `Diagnostic Quiz Generator` | 冷启动与 checkpoint 小测 | 必须 | 首版可规则化 |
| `Task Card Generator` | 把策略落成可执行任务卡 | 必须 | 输出结构化 JSON |
| `Mistake Analyzer` | 聚类错因、更新知识状态 | 必须 | 支持重复错因检测 |
| `Checkpoint Runtime` | 每日总结与第二天建议 | 必须 | 与 Proactivity 联动 |
| `AuroraWakeRequest` | 标准层申请中等/完全态介入 | 必须 | 结构化协议 |
| `Medium Aurora Replanner` | 做局部重规划 | 必须 | Phase 1 可规则 + 小模型 |
| `Visible Aurora Calibration UX` | 用户可见的简版重校准 | 必须 | 只支持少量显性场景 |
| `Model-Write Pipeline` | 观察、分类、置信度、持久化 | 必须 | 严控长期字段写入 |

---

## §5 AuroraControlSignal v1

### 5.1 设计原则

`AuroraControlSignal` 是 Aurora 控制平面与教学执行平面的正式契约。

要求：

- 每轮轻量 Aurora 必跑
- 标准层必须消费
- 任何“风格、上下文、策略、主动性、写入”都从该对象读取
- 中等态/完全态只改变其生成逻辑，不改变契约本身

### 5.2 v1 Schema

```json
{
  "schema_version": "aurora_control_signal.v1",
  "energy": {
    "current": "light",
    "candidate_upgrade": "none",
    "wake_score": 0.41,
    "cooldown_status": "available"
  },
  "intent": {
    "primary": "exam_task_execution",
    "secondary": ["concept_confusion", "time_pressure"],
    "confidence": 0.78
  },
  "expression": {
    "tone_warmth": 0.55,
    "directness": 0.78,
    "structure_density": 0.82,
    "brevity": 0.68,
    "friendliness": 0.45,
    "emotional_support": 0.35,
    "challenge_intensity": 0.62,
    "action_orientation": 0.90,
    "technical_depth": 0.72,
    "socratic_level": 0.25,
    "example_count": 1,
    "multimessage_allowed": false
  },
  "context": {
    "budget_tokens": 4200,
    "must_load": [
      "current_goal_summary",
      "current_task_card",
      "subject_sprint_pack_slice",
      "knowledge_nodes_relevant",
      "recent_mistake_clusters"
    ],
    "may_load": [
      "last_5_turns",
      "uploaded_slides_relevant_chunks"
    ],
    "do_not_load": [
      "full_long_term_profile",
      "relationship_model_raw"
    ],
    "recency_window_days": 7,
    "citation_required": true
  },
  "strategy": {
    "path_mode": "minimum_pass",
    "session_mode": "diagnose_then_drill",
    "pedagogy": {
      "concept_first": false,
      "problem_first": true,
      "worked_example_first": true,
      "retrieval_practice": true,
      "interleaving": false,
      "spaced_review": true,
      "error_analysis_required": true
    },
    "difficulty": {
      "target_zone": "slightly_below_exam",
      "reduce_if_fail_twice": true
    },
    "planning": {
      "continue_original_plan": false,
      "replan_scope": "today_only",
      "drop_low_roi_topics": true
    }
  },
  "proactivity": {
    "level": "checkpoint_nudge",
    "next_wake_at": "2026-01-04T21:30:00",
    "max_messages": 1,
    "requires_user_response": false,
    "allow_delay": true
  },
  "model_write_policy": {
    "ephemeral": [
      "current_confusion_tcp_congestion",
      "today_energy_medium_low"
    ],
    "sprint_memory": [
      "tcp_congestion_mastery_update",
      "task_overrun_observation"
    ],
    "long_term_candidate": [
      {
        "claim": "用户在考试压力下更适合短任务卡",
        "confidence": 0.58,
        "needs_confirmation": true
      }
    ],
    "forbidden_write": [
      "stable_personality_claim_without_confirmation"
    ]
  },
  "state_updates": {
    "knowledge_updates": [],
    "goal_updates": [],
    "self_model_updates": [
      {
        "field": "strategy_confidence",
        "delta": -0.08,
        "reason": "recent task overrun"
      }
    ]
  },
  "standard_layer_contract": {
    "response_type": "task_help",
    "must_include": [
      "one worked example",
      "three practice questions",
      "completion_check"
    ],
    "must_not_include": [
      "full_week_replan",
      "long motivational speech"
    ]
  }
}
```

### 5.3 v1 必填字段

- `energy`
- `intent`
- `strategy`
- `standard_layer_contract`

其余字段允许在实现中分阶段补齐，但接口位置必须预留。

---

## §6 状态模型与写入边界

第一阶段维护 7 类状态：

1. `UserModel`
2. `SparkleSelfModel`
3. `GoalModel`
4. `SituationModel`
5. `RelationalModel`
6. `KnowledgeState`
7. `TaskState`

### 6.1 UserModel

保留冲刺强相关字段：

- 学科基础
- 时间容量
- 执行模式
- 压力模式
- 干预偏好

### 6.2 SparkleSelfModel

这是第一阶段必须上线的差异化模块。

它记录：

- 当前采用的策略
- 策略置信度
- 系统对用户的关键假设
- 控制面是否命中
- 是否需要重校准

### 6.3 KnowledgeState

知识状态不是静态图，而是 **考试收益图**。每个节点至少包含：

- `mastery`
- `exam_weight`
- `frequency`
- `prerequisites`
- `mistake_tags`
- `last_practiced_at`
- `recommended_action`

### 6.4 写入边界

写入必须走统一管线：

`观察 → 分类 → 置信度 → 确认/试用 → 持久化/撤销`

| 信息类型 | 写入位置 | 是否需确认 | TTL / 生命周期 |
|---|---|---|---|
| 今天很累 | 临时状态 | 否 | 24h |
| 本次考试目标 60 分 | GoalModel | 是 | 到考试结束 |
| TCP 拥塞控制薄弱 | KnowledgeState | 否，但要有证据 | 冲刺期 |
| 更适合 30-45 分钟短任务 | 长期候选字段 | 是 | 考后 +14d 过期 |
| 系统高估了可用时间 | SparkleSelfModel | 否 | 直到被修正 |

### 6.5 Phase 1 写入禁令

- 不写入稳定人格标签
- 不写入未经确认的长期偏好
- 不把单次情绪状态写成长期特征
- 不把关系模型对用户可视化为精确数值人格

---

## §7 分级唤醒机制

### 7.1 四个能级

| 能级 | 运行方式 | 成本 | 用户是否感知 | 输出 |
|---|---|---|---|---|
| 静默态 | 规则、状态机、缓存更新 | 低 | 否 | 状态更新 |
| 轻量态 | 每轮 router | 低-中 | 通常否 | `AuroraControlSignal` |
| 中等态 | 诊断与局部重规划 | 中 | 弱感知 | 诊断、重路由 |
| 完全态 | 强模型 + 多消息校准 | 高 | 是 | 状态 / 策略 / Harness 重校准 |

### 7.2 唤醒评分

```text
wake_score =
  0.25 * exam_urgency
+ 0.20 * plan_drift
+ 0.20 * learning_failure_signal
+ 0.15 * state_conflict
+ 0.10 * user_distress
+ 0.10 * standard_layer_uncertainty
```

### 7.3 触发阈值

| 条件 | 行动 |
|---|---|
| 每轮对话 | 轻量态必跑 |
| `wake_score < 0.45` | 维持轻量态 |
| `0.45 <= wake_score < 0.72` | 中等态诊断 |
| `wake_score >= 0.72` | 完全态候选 |
| 用户明确说“你理解错我了 / 重新校准 / 深度模式” | 直接进入候选完全态 |
| 考前 24h 且计划严重落后 | 可绕过普通冷却 |

### 7.4 标准层唤醒协议

```json
{
  "type": "AuroraWakeRequest",
  "source": "standard_tutor",
  "reason_codes": [
    "goal_conflict",
    "strategy_failure",
    "user_says_misunderstood"
  ],
  "evidence": [
    "过去 3 张任务卡完成率 33%",
    "小测正确率从 62% 降到 41%"
  ],
  "local_uncertainty": 0.82,
  "suggested_energy": "medium_or_full",
  "deadline_context": {
    "days_left": 5,
    "risk": "high"
  }
}
```

### 7.5 冷却策略

| 场景 | 完全态冷却 | 日上限 | 例外 |
|---|---|---|---|
| 普通非考试期 | 6h | 1 | 重大用户纠错 |
| 14 天冲刺 | 4h | 2 | 小测崩盘、资料变更 |
| 7 天冲刺 | 2h | 3 | 计划失败、目标冲突 |
| 考前 48h | 90m | 4 | 高风险重规划 |
| 考前 24h | 45m | 4 | 每次更短 |

冷却期内默认降级成中等态，而不是硬拒绝。

---

## §8 Strategy Engine v1

### 8.1 核心任务

Strategy Engine 负责把“用户现在该学什么、该怎么学、该不该继续当前路径”变成具体控制参数。

### 8.2 第一阶段必须支持的控制项

- `path_mode`: `minimum_pass | score_max | hybrid`
- `first_move`: `answer | ask | diagnose | plan | stabilize`
- `teaching_order`: `concept_first | problem_first | worked_example_first`
- `practice_mode`: `blocked | mixed | spaced_review | mock_exam`
- `difficulty_policy`: `lower | maintain | raise`
- `replan_scope`: `task | today | sprint`
- `drop_low_roi_topics`: `true | false`
- `task_granularity`: `fine | normal`

### 8.3 7 天 minimum-pass 默认策略

优先级锁定为：

`高频题型 > 高权重章节 > 先修瓶颈 > 易拿分计算题 > 低频拓展`

满足以下条件时进入 `minimum_pass`：

- `days_left <= 7`
- `estimated_score_now < pass_score - 10`
- `daily_available_minutes < 120`
- `pass_probability < 0.55`
- 用户明确说“先过”

### 8.4 失败保护

- 连续两次任务超时 > 40%：降低任务颗粒度
- 连续三次同类错因：停止推新章节，插入专项任务卡
- 考前 48h 高权重节点 `mastery < 0.45`：主动建议放弃低收益内容

---

## §9 Subject Sprint Pack v1

### 9.1 定义

`Subject Sprint Pack` 不是 prompt，而是 Aurora、规划器、任务卡、小测和错因分析共用的结构化学科资产。

### 9.2 第一阶段范围

Pack 只做：

- `计算机网络`
- `undergraduate`
- `7d minimum_pass`

### 9.3 Pack 至少包含

- `knowledge_graph_template`
- `priority_matrix`
- `question_archetypes`
- `mistake_taxonomy`
- `paths.minimum_pass`
- `task_card_templates`
- `checkpoint_templates`
- `last_24h_strategy`
- `aurora_rules`

### 9.4 计网 Pack 的最小通过路径

第一阶段默认路径：

1. 分层模型与协议栈
2. IP / 子网划分
3. 路由基础
4. TCP 可靠传输
5. TCP 拥塞控制
6. HTTP / DNS
7. 链路层基础

可放弃候选：

- 高耗时低频扩展内容
- 罕见协议细节
- 长证明式开放题

### 9.5 高频题型与错因

高频题型：

- 子网划分
- TCP 序号 / ACK / 窗口
- 拥塞控制
- 路由表更新
- DNS / HTTP 流程

典型错因：

- 层次混淆
- bit / byte / 速率 / 时延单位混淆
- 状态转移错误
- 累积 ACK 误读
- 变量与窗口含义混淆

---

## §10 任务卡、Quiz 与错因重规划闭环

### 10.1 任务卡原则

任务卡不是 todo list，而是最小学习协议。

必须包含：

- `why`
- `duration_min`
- `goal`
- `materials`
- `steps`
- `done_criteria`
- `fallback_if_stuck`
- `aurora_triggers`

### 10.2 示例：TCP 拥塞控制 45 分钟任务卡

```json
{
  "task_id": "cn_tcp_congestion_45min_v1",
  "title": "45 分钟修复 TCP 拥塞控制题型",
  "why": "这是高频考点，且你最近 3 次错在状态变化和窗口变量。",
  "duration_min": 45,
  "goal": "能独立判断慢启动、拥塞避免、快重传后的窗口变化",
  "materials": [
    "课件第 4 章相关页",
    "SprintPack: tcp_congestion_worked_example"
  ],
  "steps": [
    {
      "name": "5 分钟概念压缩",
      "output": "写出 cwnd / ssthresh 的变化规则"
    },
    {
      "name": "10 分钟 worked example",
      "output": "跟做 1 题"
    },
    {
      "name": "20 分钟 3 道变式题",
      "output": "每题写出状态变化"
    },
    {
      "name": "10 分钟小测",
      "output": "提交答案与信心"
    }
  ],
  "done_criteria": [
    "3 道题至少 2 道正确",
    "能解释错题原因",
    "下一步建议自动生成"
  ],
  "fallback_if_stuck": "先看半成品解题框架，不直接看完整答案",
  "aurora_triggers": [
    "accuracy_below_0.5",
    "time_overrun_above_0.4",
    "same_mistake_repeated"
  ]
}
```

### 10.3 错因驱动重规划

闭环如下：

`用户做题 → 批改 → MistakeCluster 更新 → KnowledgeState 更新 → Aurora 判断策略是否失效 → 插入专项任务卡或局部重规划`

触发重规划的最小规则：

- 连续 3 次同类错因
- 任务超时 > 40%
- 高权重节点 `mastery < 0.5`
- checkpoint 正确率 < 55%

---

## §11 7 天工作流

| 天数 | 目标 | Aurora 重点 | 教学执行层重点 |
|---|---|---|---|
| D0 | 冷启动、资料、诊断、路径选择 | 校准目标与风险 | 问卷、资料解析、诊断题 |
| D1 | 建高收益地图，修 1-2 个瓶颈 | 控制上下文与路径 | 高频例题 + 第一天任务卡 |
| D2-D4 | 高频题型攻坚 | checkpoint + 错因聚类 | worked example、变式题、短测 |
| D5 | 半套或整套模拟 | 中等态重规划 | 限时模拟 + 批改 |
| D6 | 修复最影响通过率的错因 | 放弃低 ROI 内容 | 错因专项任务卡 |
| D7 | 考前 24h 稳定输出 | 切换 `last_24h_strategy` | 公式、流程、错题、短测 |

7 天默认时间配比：

- 概念压缩：20%
- worked example：25%
- 题型训练：35%
- 错题复盘：15%
- 情绪 / 执行校准：5%

---

## §12 简版显性 Aurora UX

### 12.1 第一阶段只支持三类显性介入

1. 重新校准备考策略
2. 修正可用时间假设
3. 考前高风险时切换保底路径

### 12.2 状态条文案

默认收拢态：

- `Aurora · 已校准`
- `Aurora · 观察中`
- `Aurora · 需要你确认一个判断`
- `Aurora · 策略风险升高`

展开后不显示人格分数，只显示：

- 我的判断
- 证据
- 影响
- 建议动作

### 12.3 介入语言模板

遵循：

`观察 → 不确定性 → 影响 → 建议 → 用户选择`

示例：

> 我可能需要重新校准一下。我之前按每天 2 小时给你排，但最近两次任务都明显超时。继续这样排会让你每天都失败，反而降低通过率。建议把今晚改成一个 45 分钟高收益任务。你确认今晚真实可用时间是 45、60 还是 90 分钟？

### 12.4 第一阶段不做

- 复杂多消息朋友式展开
- 长篇自我揭示风格交互
- 关系模型可视化仪表盘

---

## §13 API 与工程接口建议

Phase 1 推荐接口切片：

| 接口 | 用途 | MVP |
|---|---|---|
| `POST /aurora/event` | 用户输入 / 任务反馈事件入口 | 必须 |
| `POST /aurora/turn-control` | 生成 `AuroraControlSignal` | 必须 |
| `POST /aurora/wake-request` | 标准层申请升级 | 必须 |
| `POST /exam-sprint/intake` | 冷启动 intake | 必须 |
| `POST /exam-sprint/diagnose` | 诊断 quiz 生成与评分 | 必须 |
| `POST /sprint-pack/match` | 匹配 Pack 与路径 | 必须 |
| `POST /planner/generate-task-cards` | 任务卡生成 | 必须 |
| `POST /quiz/generate` | 小测生成 | 必须 |
| `POST /quiz/grade` | 小测批改 | 必须 |
| `POST /mistake/analyze` | 错因聚类 | 必须 |
| `POST /state/update` | 状态写入 | 必须 |
| `POST /checkpoint/run` | 每日 checkpoint | 必须 |

### 13.1 与当前代码边界的关系

当前仓库中已有：

- `backend/app/orchestration/exam_sprint_policy.py`
- `backend/app/scenario_packs/exam_prep_14d_v1_0.json`
- 规划与 Aurora runtime 相关测试

本规格的作用不是替换这些脚手架，而是定义下一层更具体的 **Exam Sprint 控制契约**：

- `exam_sprint_policy.py` 继续承担策略基线与硬边界
- `AuroraControlSignal` 承担单回合控制契约
- `Sprint Pack v1` 承担学科执行资产
- `Medium Aurora Replanner` 承担失败后的局部重规划

---

## §14 Ticket 拆分与验收

### 14.1 P0

1. `AuroraControlSignal v1`
2. `Light Aurora Turn Router`
3. `Context Assembler`
4. `Exam Sprint Intake`
5. `Diagnostic Quiz Generator / Grader`
6. `Task Card Generator v1`
7. `KnowledgeState Updater`
8. `MistakeCluster Analyzer`
9. `Checkpoint Runtime`
10. `Medium Aurora Replanner`
11. `Simple Visible Aurora Calibration`
12. `Model-Write Pipeline v1`
13. `Telemetry / Evaluation Logger`
14. `Computer Networks Sprint Pack v1`

### 14.2 P1

- Pack authoring / validation
- 冷却策略调参与观测
- 用户主动 Aurora 入口 UI
- 多消息完全态
- 多学科扩展

### 14.3 Phase 1 验收指标

结果指标：

- `estimated_score_delta_7d`
- `pass_probability_delta`
- 模拟测验得分提升

过程指标：

- 任务完成率
- 按时完成率
- 小测正确率提升
- 高权重节点 mastery 提升
- 错因复发率下降
- 重规划后任务完成率

体验指标：

- “Sparkle 比 ChatGPT 更懂我”
- “计划可执行”
- “Aurora 主动介入有帮助”
- “任务卡让我知道下一步做什么”

系统指标：

- Light Aurora 延迟
- 完全态调用频率
- 平均 token 成本
- 上下文命中率
- 错误升级率 / 漏升级率

建议的最小成功门槛：

- 关键任务完成率 ≥ 80%
- 小测正确率提升 ≥ 20%
- 错因复发率下降 ≥ 50%

---

## §15 风险、反模式与最终交付物

### 15.1 反模式

| 风险 | 反模式 | 规避方式 |
|---|---|---|
| Aurora 退化成第二聊天窗口 | Aurora 自己长篇输出教学内容 | 强制经由控制信号影响标准层 |
| 成本失控 | 每轮全量强模型 | 轻量态必跑，升级态受唤醒与冷却控制 |
| Sprint Pack 退化成 prompt stuffing | 用长 prompt 描述学科 | 用结构化 schema 管理学科资产 |
| 任务卡退化成待办清单 | 只有标题，没有 done criteria | 任务卡必须是可检查学习协议 |
| 上下文噪声过载 | 一股脑塞入全量画像 | 必须走 context mask / budget |
| 错误长期建模 | 单次状态写成长久人格 | 采用 candidate + confirmation 写入 |
| 过早多学科化 | 同时做 4 门课 | 先跑通计网 7 天通过闭环 |

### 15.2 第一阶段最终交付物

1. `AuroraControlSignal v1`
2. `State Store v1`
3. `Light Aurora Router`
4. `Context Assembler`
5. `Strategy Engine v1`
6. `Computer Networks Sprint Pack v1`
7. `Diagnostic Quiz v1`
8. `Task Card Generator v1`
9. `Mistake Analyzer v1`
10. `Medium Aurora Replanner`
11. `Simple Aurora Calibration UX`
12. `Model-Write Pipeline v1`
13. `Telemetry / Evaluation Logger`

### 15.3 完成定义

Phase 1 完成的标志不是“看起来像 Aurora 了”，而是：

- 能从冷启动进入 7 天计网冲刺
- 能跑出结构化诊断
- 能生成与执行任务卡
- 能识别错因并触发重规划
- 能在高风险节点做简版显性校准
- 能采集指标，验证 Aurora 控制层是否真的提高通过概率

第一阶段的唯一目标是把 Aurora 从愿景收束成一个 **真正产生提分效果的认知控制系统**。
