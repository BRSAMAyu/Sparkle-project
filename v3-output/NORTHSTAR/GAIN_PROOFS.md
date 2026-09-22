# NORTHSTAR GAIN PROOFS · 四能力增益证明靶子清单

> 北极星宣称「星图/向量索引/记忆/画像**实际正向增益**（能跑≠有用）」。本文档是后续
> **C 线闭环测试的靶子清单**：每个能力给出「若有效 → 哪些指标改善」「若无效 → 什么表现」
> 「若有害 → 什么表现」，并给出可机检的观测键（与 runner 骨架 observation 键对齐）。
>
> 判定基线原则：**每个能力都必须有「有它 vs 没它」的差分**（paired arm / ablation），
> 单臂绝对值好看不构成证据。M-09 的 paired no-history 臂是本清单的方法论先例。

## 0. 靶子状态词表（冻结）

`UNTESTED`（未测）→ `PROVEN_POSITIVE` / `PROVEN_NULL`（无效）/ `PROVEN_HARMFUL`（有害）。
任何靶子只有 C 线真实差分数据才能离开 `UNTESTED`；runner 骨架推演结果不改变状态。

---

## 1. 星图（Galaxy 知识图谱 + mastery）

| 靶子 | 定义 |
|---|---|
| **GP-01 星图定向增益** | 若有效：计划按 exam_weight×薄弱度定向 → M4 加权覆盖率达标更快（前 3 天 C(A) ≥ C(B)+0.2）且 posttest「被定向节点」得分率 > 「未定向节点」（差 ≥ 0.15）。若无效：覆盖率上去了但 posttest 同节点得分率不动（**生长≠掌握**，C(A)−posttest 相关节点分相关 ≈ 0）。若有害：见 GP-03 |
| **GP-02 错题→节点回写闭环** | 若有效：错题落本 + mastery 同步后，该节点下次 quiz/复习重测正确率比首次 ≥ +0.3（错误被真正修复）。若无效：重测正确率与首测无差（错题本是死档案）。若有害：错因误判（归因到错误节点）→ 修复练习打偏 → 该节点 posttest 失分且重测仍错 |
| **GP-03 mastery 校准（星图不说谎）** | 若有效：M8 校准误差 ≤ 0.15——星图「已掌握」⇔ 模拟考该节点真会。若无效：校准误差 > 0.3（星图是装饰品，覆盖/掌握宣称全部失去证据资格）。若有害：**mastery 虚高**（星图显示掌握但实测不达线）→ 系统提前移出该节点 → posttest 结构性丢分且用户被误导——此表现直接证伪 P5「我信任它」 |

观测键：`mastery_calibration_error`、`targeted_vs_untargeted_score_gap`、`mistake_repair_uplift`、`galaxy_coverage_weighted`、`premature_node_exit_count`。

## 2. 向量检索（RAG / embedding）

| 靶子 | 定义 |
|---|---|
| **GP-04 检索信息增量（对照盲选）** | 判据：`citation_hit_rate_above_blind` =（给真料答对率 − 给随机无关料答对率）> 0。若无效：**引用材料答对率 = 盲选**（±0.05 内）——检索没有提供信息增量，答案质量与料无关，索引白建。若有害：给真料的答对率**低于**盲选（检索到的错误/过期内容误导作答） |
| **GP-05 引用忠实且命中** | 若有效：引用挂接的星图节点/文档块与提问章节一致率 ≥ 0.8，且无未检索文档的幻觉引用（Q-01 `_rag_citation_faithful` 同规）。若无效：引用随机挂接（一致率 ≈ 均匀分布期望）。若有害：引用了过期版本或跨用户文档（Q-01 rag checker 面）——这是安全事故不只是无效 |
| **GP-06 长料 JIT 有用性** | 若有效：长课件场景下带 JIT 截断的引用作答正确率 ≥ 全文塞入的 0.9 倍且 token 成本显著低。若无效：截断后正确率塌方（截断把关键块截掉 = 分块/排序策略失败） |

观测键：`blind_baseline_delta`、`citation_node_alignment`、`stale_or_crossuser_citation_count`、`jit_answer_ratio_vs_full_context`。

## 3. 记忆（memory：纠正/偏好/经验沉淀）

| 靶子 | 定义 |
|---|---|
| **GP-07 记忆 uplift（paired no-history）** | 同一学生状态双臂差分：有记忆臂 vs 无历史臂。若有效：uplift > 0——隔日提问正确复用昨日纠正（「我上次说看不懂证明，这次先给直觉」被遵守）、偏好跨 session 保持。若无效：uplift ≈ 0（每 session 都在失忆，P4「不用重复解释」证伪）。若有害：见 GP-08/09 |
| **GP-08 记忆污染反噬** | 若有害的表现：day 作用域约束被 globalize 到次日（「今天只有 1 小时」被记成长期约束）、superseded 旧值复活（M-09 已登记的 ContextPackBuilder 偏好冲突 bug 签名）→ **答错关联题 / 计划按过期约束生成**。机检：M-09 invalid-use 指标 > 0 或本 runner `stale_memory_surfaces` > 0 |
| **GP-09 过个性化（overpersonalization）** | 若有害：无关记忆 surfacing 进决策上下文（M-09 overpersonalization 指标）→ 无关标签影响推荐（「曾问过编程题」→ 给数学复习塞编程类比）→ quiz 分数/完成率被拖低。若无效：记忆只在显式追问时出现，平时零增益也零伤害（应判 NULL 而非 POSITIVE） |
| **GP-10 经验记忆（什么干预对此人有效）** | 若有效：同类 friction 二次出现时，干预采纳率比首次 ≥ +0.2 且修复耗时下降。若无效：每次都用同一套模板（采纳率不随历史变化）——Experience Memory 退化为摆设 |

观测键：`memory_uplift_vs_no_history`、`stale_memory_surfaces`、`day_scope_globalize_count`、`overpersonalization_rate`、`intervention_repeat_adoption_delta`。

## 4. 画像（profile：水平/节奏/偏好建模）

| 靶子 | 定义 |
|---|---|
| **GP-11 难度分层增益（ablation）** | 画像开 vs 关双臂。若有效：画像臂卡壳率（quiz 首答错误且 30s 内放弃）更低、任务完成率更高（差 ≥ 0.15）。若无效：开关无差（画像字段没进决策，或进了但被 LLM 无视）。若有害：见 GP-12 |
| **GP-12 标签锁死（一次失误定终身）** | 若有害：单次 quiz 失败 → 画像降档 → 后续材料永久降难度 → posttest 高难题全丢（提分上限被画像压死）。机检：画像难度轨迹与实测 mastery 的相关性为负，或 `difficulty_ceiling_lock_count` > 0。若有效：画像随每日 quiz 单调校准，难度带上沿跟随实测上升 |
| **GP-13 节奏画像与计划完成率** | 若有效：按个人节奏（早晚/块时长）排的计划，完成率 ≥ 随机排期 + 0.15。若无效：完成率与排期方式无关（画像没被 planner 消费）。观测链路：画像字段 → planning_workflow 输入 → 计划卡 → 完成事件，任一环断裂即 NULL |

观测键：`profile_ab_completion_delta`、`stuck_rate_by_difficulty_band`、`difficulty_ceiling_lock_count`、`profile_mastery_trace_correlation`、`plan_completion_rate_by_pacing`。

---

## 5. 汇总矩阵（C 线执行核对单）

| 靶子 | 能力 | 有效信号 | 无效信号 | 有害信号 | 差分方法 | 状态 |
|---|---|---|---|---|---|---|
| GP-01 | 星图 | 定向节点 posttest 分差 ≥ 0.15 | 覆盖↑分数不动 | （由 GP-03 判） | 定向/未定向节点内对照 | UNTESTED |
| GP-02 | 星图 | 错题重测 +0.3 | 重测无改善 | 错因归因打偏 | 首测/重测 paired | UNTESTED |
| GP-03 | 星图 | 校准误差 ≤ 0.15 | 误差 > 0.3 | mastery 虚高→提前移出 | 星图 vs 模拟考逐节点 | UNTESTED |
| GP-04 | 向量 | 真料−盲选 > 0 | 真料=盲选 | 真料<盲选 | 真料/盲选料双臂 | UNTESTED |
| GP-05 | 向量 | 引用对齐 ≥ 0.8 | 随机挂接 | 过期/跨用户引用 | 引用审计 | UNTESTED |
| GP-06 | 向量 | JIT ≥ 全文×0.9 且省 token | 截断塌方 | — | JIT/全文 paired | UNTESTED |
| GP-07 | 记忆 | uplift > 0 | uplift ≈ 0 | （GP-08/09） | paired no-history（M-09 法） | UNTESTED |
| GP-08 | 记忆 | — | — | 过期约束 globalize→答错关联题 | M-09 invalid use + 本 runner | UNTESTED |
| GP-09 | 记忆 | — | — | 无关记忆 surfacing 拖低表现 | M-09 overpersonalization | UNTESTED |
| GP-10 | 记忆 | 二次干预采纳 +0.2 | 模板无变化 | — | 首次/二次 paired | UNTESTED |
| GP-11 | 画像 | 开臂完成率 +0.15 | 开关无差 | （GP-12） | ablation 开/关 | UNTESTED |
| GP-12 | 画像 | 难度随实测上移 | 无关 | 失误→永久降档→压死上限 | 难度轨迹 vs mastery | UNTESTED |
| GP-13 | 画像 | 节奏排期完成率 +0.15 | 与排期无关 | — | 节奏/随机排期 paired | UNTESTED |

**北极星级一票否决项**：GP-03（星图说谎）、GP-04（检索零增量）、GP-07（记忆失忆）、GP-11（画像无效）任一判 `PROVEN_NULL` 或 `PROVEN_HARMFUL`，对应的产品宣称必须从北极星材料中撤下——这比「全绿」更重要，是本清单存在的意义。
