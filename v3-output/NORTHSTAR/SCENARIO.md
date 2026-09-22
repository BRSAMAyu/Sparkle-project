# NORTHSTAR SCENARIO · 7 天期末冲刺 Spec Case（可反复执行）

> 北极星：**「用户只剩一周准备期末考试，用 Sparkle 的学习效果就是最好的、能拿的分就是最高的」**。
> 本文档把这句宣称落成一个可反复执行的 spec case：每步有用户动作、系统行为、可测量检查点。
> 检查点词表（CP-00..CP-98）与 `backend/tests/northstar_eval/` runner 骨架一一对应（见 `journey_schema.py` 冻结词表）。

## 0. 真实性声明（先读）

- 本剧本是**评估规格**，不是已完成事实。所有目标数字是「及格线 / 最小可检效应（MDE）」假设，
  由 EVAL_FRAMEWORK.md 的对照协议判定，任何一项未达成都构成对北极星宣称的反例。
- 剧本中 Sparkle 侧每个「系统行为」都锚定到仓库真实服务面（见 §4 锚点表）；
  runner 骨架以 contract-simulation 方式推演本剧本（确定性、真实 LLM 0 次），
  真实增益证明由后续 C 线闭环测试（真实服务层 + 真人/真卷）闭合。

## 1. 人物与约束（冻结）

| 项 | 值 |
|---|---|
| Persona | 大二学生「林晓」（persona_library 已有 persona 体系的同构扩展；演示账号走 `LOCAL_SMOKE_USERNAME` 体系） |
| 科目 | 离散数学（期末闭卷，100 分卷） |
| 距考试 | 7 天 |
| 起点 | 摸底卷 A **42 分**（前测，同卷机制见 EVAL_FRAMEWORK §M1） |
| 未掌握章 | 6 章：CH1 数理逻辑 / CH2 集合与关系 / CH3 函数与基数 / CH4 图论 / CH5 组合数学 / CH6 代数系统 |
| 每日预算 | 2–3 小时（冻结为 165 min/天 ± 15，含系统交互时间——交互时间计入学习成本，不许白嫖） |
| 考纲节点 | 24 个（6 章 × 4 节点，字段对齐 sprint pack `KnowledgeNode`：`exam_weight/difficulty/time_cost/trainability`，样例库 `backend/app/sprint_packs/mathematics_v1.json` 同构） |
| 试卷 | 卷 A（摸底=post 基线卷）、卷 B（Day7 模拟考，同构异题）、卷 A′（3 天后重测，A 的等价复本） |

## 2. 与 exam_prep_14d 主干的映射

7 天是 14 天主干（`exam_prep_14d@v1.0`，`backend/app/scenario_packs/exam_prep_14d_v1_0.json`）的压缩变体：

| 本剧本 | 14d 主干节点 | 说明 |
|---|---|---|
| Day0 | `day1_orientation` + `day2_prerequisite_map` | 摸底 + 考纲→星图映射合并执行 |
| Day1–2 | `day4_deep_analysis` | 首攻最大权重章（数理逻辑） |
| Day3–6 | `day5_error_repair` + `day6_targeted_drill` + `day7_timed_practice` + `day8_review_cycle` | 逐章推进 + 错题修复 + 复习循环 |
| Day7 | `day13_final_simulation` | 全真模拟考（跳过 `day14_final_reset`，考试日即 reset） |

## 3. 逐日旅程

### Day0 · 摸底诊断 + 首计划（预算 165 min）

| # | 用户动作 | 系统行为 | 检查点 |
|---|---|---|---|
| 0.1 | 输入目标「7 天后期末考，离散数学，想及格冲 70+」 | exam_sprint intake：目标建模、生成 7 天 backbone（考试日倒排） | 目标/截止日/范围三要素显式落账 |
| 0.2 | 做 30 min 摸底卷 A（24 题对应 24 考纲节点，每节点 1 题） | 判卷 → **42 分**；逐题映射到考纲节点 → 生成 24 节点 mastery 初值 | **CP-00** 摸底分入账且考纲→星图节点映射 24/24 |
| 0.3 | 上传课件 PDF（6 章，~120 页） | 解析 → 分块 → 向量索引（embedding 入库）；按章节挂到星图节点 | 索引完成，每节点 ≥1 个材料块挂载 |
| 0.4 | 审阅 AI 生成的 7 天计划草案 | 计划按 `exam_weight × (1−mastery)` 定向排序；数理逻辑（权重最高）排 Day1–2；每天含「新学/复习/自测」三段；标注 Human/Agent/Hybrid 所有权 | **CP-01** 计划定向正确且经人工确认（草案→用户改 1 处→确认生效） |
| 0.5 | 确认计划 | 计划冻结为 Day1 执行版；NorthStarMetrics 记录 `exam_pass_probability` 基线 | 事件账本可查 |

### Day1–Day6 · 每日循环（预算 165 min/天）

每日循环五段（以 Day1 数理逻辑 I 为例）：

| 段 | 时长 | 用户动作 | 系统行为 | 检查点（每日采集） |
|---|---|---|---|---|
| 1 计划 | 10 min | 打开 Today Cockpit，看 3 张 task card | 按昨日结果**自适应**生成当日卡（见段 5）；已掌握节点降权/移出 | **CP-04** 次日计划依据前日结果自适应（每日计 1 次，6 次中 ≥5 次有真实变更） |
| 2 新学 | 2×45 min | 学指定小节；上传/引用材料提问 | RAG 引用作答（引用必须挂星图节点+文档块）；苏格拉底式追问不直接喂答案（认知所有权：此段 ownership=human+coach） | 引用命中率入账（GAIN_PROOFS GP-05）；答完 1 道引导题 |
| 3 自测 | 15 min | 做 5 题形成性 quiz（当日内容 70% + 历史抽样 30%） | 确定性判卷 → 标准化分；错题逐题归因（mistake_types 词表） | **CP-02** quiz 分数轨迹非降（3 日滑动窗） |
| 4 错题沉淀 | 10 min | 逐题看错因卡片 | 错题 → 错题本；触发 `error_book_mastery_sync` → 星图对应节点 mastery 下修 + 生长事件 | **CP-03** 错题 100% 落错题本且触发 mastery 同步（6 天合计漏记 = 0） |
| 5 复习+复盘 | 40 min | 重测遗忘曲线到期题（昨日+前日错题）；确认明日计划草案 | 遗忘曲线调度（间隔重复）；Aurora 生成当日报告（学了什么/为什么这么排/明日改什么）；草案按当日 quiz/复习结果重排 | **CP-05** 复习命中率 ≥ 0.7（重测首答对率，按日计） |

逐日主攻与形成性测验目标分（标准化：当日 70% + 历史抽样 30%，满分 100）：

| 日 | 主攻章（24 节点中的新学节点） | 复习抽样 | quiz 目标带 | 达标判据 |
|---|---|---|---|---|
| Day1 | CH1 数理逻辑 I（命题逻辑，4 节点） | — | 40–55 | 轨迹基线 |
| Day2 | CH1 II（谓词+推理理论，4 节点） | D1 错题 | 48–62 | 轨迹非降 |
| Day3 | CH2 集合与关系 + CH3 函数（4+2 节点） | D1–D2 抽 4 题 | 55–70 | 轨迹非降 |
| Day4 | CH4 图论（4 节点） | D1–D3 抽 4 题 | 62–78 | 轨迹非降；加权覆盖 ≥ 0.5 |
| Day5 | CH5 组合数学（4 节点） | D1–D4 抽 4 题 | 68–84 | 轨迹非降 |
| Day6 | CH6 代数系统（2 节点）+ 全量薄弱重修 | 全量到期题 | 74–90 | 轨迹非降；加权覆盖 ≥ 0.8（**CP-06**） |

### Day7 · 全真模拟考（预算 120 min 考试 + 30 min 复盘）

| # | 用户动作 | 系统行为 | 检查点 |
|---|---|---|---|
| 7.1 | 120 min 限时做卷 B（同构异题，覆盖 24 节点） | 计时、禁材料；交卷后确定性判卷 | **CP-99** 全真墙钟 ≤ 120 min（真实墙钟属性，API 级推演 honest-unsupported） |
| 7.2 | 看成绩与归因 | 目标：**posttest ≥ 57**（42+15，MDE 定标见 EVAL_FRAMEWORK；目标带 62–70）；逐节点得分 vs 星图 mastery 预测做校准分析 | **CP-07** 提分 ≥ +15 且逐节点校准误差 ≤ 0.15 |
| 7.3 | — | NorthStarMetrics 记录 `exam_outcome`；闭环数据回写（本次冲刺的 intervention→outcome 进入 Experience Memory） | outcome 账本可查，来源标记 `northstar_eval` |

### Day10 · 遗忘率重测（+3 天，预算 30 min）

| # | 用户动作 | 系统行为 | 检查点 |
|---|---|---|---|
| 10.1 | 做卷 A′（卷 A 等价复本，30 min） | 判卷 → retest 分 | **CP-08** 遗忘率 F = (post − retest)/post ≤ 0.2；逐节点衰减 vs 复习调度记录交叉验证 |
| 10.2 | — | 北极星闭环收官：三臂同流程采齐后进入 EVAL_FRAMEWORK 判定 | 三臂指标对齐入 comparison 账本 |

### 认知负担与遗漏点（贯穿，非每日）

- **CP-98** 认知负担：每日收工 5 题 7 分量表（心理要求/时间压力/掌控感/清晰度/付出），日 均 ≤ 4.5 且不逐日攀升（真人量表，API 级推演 honest-unsupported）。
- **遗漏点账本**：考纲 24 节点中，凡「从未出现在任何计划卡/quiz/复习」的节点记遗漏 1 次；三臂对比遗漏点率（GAIN_PROOFS GP-11）。

## 4. 系统行为 → 仓库真实服务锚点表

| 剧本系统行为 | 仓库锚点（真实代码面） |
|---|---|
| 考试冲刺 intake / 7 天 backbone | `backend/app/services/exam_sprint_intake_service.py`（ExamSprintIntakeRequest → Plan/Task） |
| 摸底诊断卷生成/判卷/节点映射 | `backend/app/services/exam_sprint_diagnostic_service.py`（DiagnosticGenerate/Grade，topic→galaxy node 解析） |
| 星图节点与 mastery 生长 | `backend/app/services/galaxy_service.py`、`app/models/galaxy.py`（KnowledgeNode/UserNodeStatus）、`app/services/error_book_mastery_sync_service.py` |
| 材料 RAG 引用问答 | `backend/app/services/knowledge_service.py` + `app/services/embedding_service.py` + `app/services/galaxy/rag_router.py` |
| 记忆（纠正/偏好/经验沉淀与次日复用） | `backend/app/services/memory_*`（M-02..M-07 链路） |
| 画像（难度分层/节奏） | `backend/app/services/profile_write_service.py`、`profile_context_service.py` |
| 北极星指标事件 | `backend/app/services/north_star_metrics_service.py`（exam_pass_probability / exam_outcome） |
| 每日 task card 与所有权标注 | Today Cockpit 卡面（P3 Human/Agent/Hybrid，V3 NORTH_STAR.md §3） |
| 计划生成（AI 草案+人工确认） | `app/orchestration/planning_workflow.py`（经 exam_sprint_intake 调用） |

## 5. 可反复执行性

- 试卷 A/B/A′ 题库冻结（24+24+24 题及答案键），判卷确定性（无 LLM 判分）；
- persona 冻结（起点分、可用时间、材料集不变）；
- 每次执行的检查点数据落 `northstar_eval` 证据目录（runner 骨架 JSON schema 稳定）；
- 洗脱与轮换见 EVAL_FRAMEWORK §对照协议——同一真人重复执行时按 ABBA 顺序换臂换卷，避免练习效应污染。
