# P1-4 · sprint 仪表盘与任务账本对账 · 施工报告（wt110）

> 交付物：`v3-output/P1-4-DASHBOARD/changes.patch`（4 文件，+约 380/−约 30）+ 本报告。
> 基线：wt110，基于 main@5d1df370。零 commit / 零 push / 零模拟器 / 零构建产物落仓。
> 卡面：LOOP1 断点 BP-4（NORTHSTAR-LOOP1 REPORT §2），S7「AI 叙事失去地基」族在 sprint 面的实例；DL-R4 P1-8 裁决「跨账本对账无矛盾」的第一批施工应用。
> 模式：复用 B1-A 单一事实源模式（`goal_today_view.py`：SQL 条件 + 取数 + 纯判定镜像三件套，消费面委托引用）。

---

## 1. 三处根因（回执①）

红证复现（红测试在实现落地前跑出的数字与 E1 证据逐字一致）：
`SprintTaskStats(total=4, completed=0, completion_rate=0.0)`、`SprintScoreStats(current_score=0.0, delta=-42.0, baseline_source='intake')`。

| # | 现象 | 根因（一句话） | 位置 |
|---|---|---|---|
| 1a | **total=4**（账本实际 20） | sprint-summary 按单条 plan 名下任务计数（`Task.plan_id == plan.id`），而 `get_sprint_summary` 无 plan_id 时取**最新创建**的 sprint plan——NS-001 里那是 goal 面计划（228093d7），名下只挂了 4 张 goal_milestone 卡，intake 计划（46ef9462）的 day 卡与手动任务全部不在域内 | `exam_sprint_review_service.py` `_resolve_target_plan` + `_load_plan_tasks`（旧 `_build_summary`） |
| 1b | **完成 0**（账本 COMPLETED=2） | 同一 plan 域收窄的另一半：2 个完成事件一个挂在 intake 计划名下（`5a83a029`「Day 1 · 诊断分诊」）、一个是无 plan_id 的手动任务（`312347aa`「Day1 数理逻辑 I」，C1b fallback 建）——都落在 4 张未完成里程碑卡的计数域之外 | 同上 |
| 2 | **current_score=0.0 → delta=-42** | 无诊断快照时 current_score 回退 `_current_average_mastery`：用户星图只有「解锁未学习」节点（mastery_score 列**非空默认 0**），全 0 平均可=0.0——存储层 0 与「无测量」不可区分，旧实现把 0 当真实分数与 intake 基线 42 做差，产出虚假退步叙事 | `exam_sprint_review_service.py` 旧 `_current_average_mastery` + `_build_mastery_summary` |

同族连带（E1 证据里同样在说谎，一并修）：`daily_study_trend` 全 0 分钟——回退统计也按 `plan_id` 收窄 + 期间起点锚定单条 plan 的 `created_at`，跨计划/更早的完成事件进不了窗口。

## 2. 统一到哪个权威源（回执②）

**新引擎模块 `backend/app/services/sprint_task_ledger.py`（sprint 任务账本单一事实源）**，模式同 B1-A：

- 口径 = **任务账本视图**（GET `/api/v1/tasks`，`app/api/v1/tasks.py list_tasks`）同一取数域：**该用户全部未删除任务**——不按 plan 收窄、不按状态预过滤。理由：sprint 执行期任务可能挂在并行 sprint 计划下（BP-7 形态）或根本无 plan_id（plan→task 链缺口），按 plan 收窄必然造成账本-仪表盘两套事实；
- 导出四件套：`sprint_ledger_condition`（SQL 条件唯一定义点）、`fetch_sprint_ledger_tasks`（唯一取数入口）、`is_completed_task`/`count_completed`（纯判定镜像，与 SQL 同源防漂移）、`build_ledger_task_stats`（total/completed/completion_rate 唯一构造点）；
- **消费面**：`ExamSprintReviewService._build_summary` 改为委托引用（sprint-summary / 考后复盘 / 七日完成 northstar 上报的 task_stats 全部经此）；
- **边界（刻意不统一）**：计划结构性判定——七日完成检测（`_has_completed_seven_day_sprint`）、自动归档（`auto_archive_if_complete`，统计改名 `_build_plan_task_stats` 以正名分）——仍按 plan 域任务。它们判定的是「这份计划做完了吗」，不是「这个用户的执行账本」，两类口径混用会让无关任务阻塞/误触发归档。`_load_plan_tasks` 保留并加 docstring 声明此边界。

**current_score「暂无数据」语义**：新 `_current_measured_score`——只有存在 **mastery_score > 0** 的测量行才构成数据（`SELECT avg(...) WHERE mastery_score > 0`）；无测量信号返回 `None`，`delta` 相应 `None`（schema 两字段本就 `float | None`，形状零变化，前端呈现「暂无数据」）。0/空不再是合法「当前分」。存在真实测量时照常计算（对照测试：65.0 → delta +23.0）。

**期间锚点同族修**：新 `_sprint_period_start`——与目标计划时间窗重叠的所有 sprint 计划的最早创建时刻（无重叠退回本计划创建时刻）；error_recovery 与 daily_study_trend 的窗口起点统一用它。趋势回退统计改为用户域 + 窗口过滤（deleted 过滤补上）。

## 3. 红→绿统计（回执③）

| 阶段 | 结果 |
|---|---|
| 红（实现落地前） | **9 failed**（5 SSOT 契约 + 4 BP-4 对账），失败数字逐字复现证据（total=4/completed=0/0.0/-42.0/trend 0min）；同文件既有 11 测试全过（未伤基线） |
| 绿（实现落地后） | `test_sprint_task_ledger.py` 5 passed + `test_exam_sprint_review_service.py` 15 passed = **20 passed** |
| exam_sprint 全家回归（红线面） | diagnose_api / diagnostic_service / intake_service / policy / review_service / daily_sprint_reminder / sprint_galaxy_mastery / pack_loader / pack_registry / non_exam_crisis_mode + api/test_exam_sprint_api + goal_today_view = **121 passed，零回退** |
| 北极星驱动器单测 | `tests/northstar_eval/test_real_drive_unit.py` **19 passed**（summary 解析/对账逻辑不受影响） |
| lint/format | ruff + black(120) 对 4 个变更文件全绿 |

新增测试清单：
- `backend/tests/unit/test_sprint_task_ledger.py`（5）：契约导出、SQL 条件镜像（用户全域+非软删、断言**不得**含 plan_id/status 收窄）、纯判定与统计语义（含原生字符串状态）、端到端取数（跨 plan + 无 plan 全可见、软删/他人不可见）；
- `backend/tests/unit/test_exam_sprint_review_service.py` 增 4：`_seed_ns001_shape` 复刻 NS-001 账本形态（goal 计划 4 里程碑卡 + intake 计划 day 卡 + 手动无 plan 任务）后——①task_stats 与账本逐项对账（total/completed/rate/ headline/narrative 文案）；②无测量时 current_score=None、delta=None（红住 -42）；③对照：有测量 65.0 → delta +23.0；④趋势计入跨计划完成时长（45+55）。

## 4. 红线面核对

- **exam_sprint 套件零回退**：见上表，INTAKE/P0-1 刚合入的 33+38+51 基线所涉文件全部绿；
- **mobile 消费形状不变**：`SprintTaskStats`/`SprintScoreStats` schema 未动（current_score/delta 本就 nullable），纯引擎侧数值修正；mobile 无 sprint-summary 直连消费点（grep 证）；
- **北极星 upsert 不破坏**：`record_seven_day_goal_completed` / `record_exam_outcome` 机制未动；`_has_completed_seven_day_sprint` 门控仍按 plan 域任务（计划结构判定边界），仅 payload 里的 task 统计数字变为账本真值；`score_delta` 可为 None（payload dict 序列化兼容）；
- **冲突面**：wt109 LOOP2 只读活栈未触碰；未碰 intake 建计划路径（wt111 面不同文件）；
- 本卡只修 sprint-summary 叙事面。`ExamSprintDashboardService`（/dashboard 的今日分组卡）的 score 处理（无数据时 current=baseline，无假差值）与 plan-day 分组展示属另一语义面，本卡不动、已记录。

## 5. 遗留与建议（不阻塞收工）

1. **plan→task 链缺口**（C1b fallback 的上游）：手动任务无 plan_id 才需要账本口径兜底；根治应让 sprint 执行任务落 plan_id（或计划页显式挂靠），属产品决策，建议开卡；
2. `_sprint_period_start` 用「窗口重叠」圈定并行计划，若未来出现同科目错峰多计划，可再收敛科目维度；
3. DL-R4 P1-8 的「注册可达性测试」要件：本卡未新增/迁移端点（形状不变），以 SSOT 契约测试替代；若 §9.4 门禁要求引擎模块一律带注册面断言，可补 `/sprint-summary` 形状键集断言（半小时工作量）。

## 6. 收工核查（回执④）

- [x] 变更仅在 wt110 worktree 内：`backend/app/services/sprint_task_ledger.py`、`backend/app/services/exam_sprint_review_service.py`、`backend/tests/unit/test_sprint_task_ledger.py`、`backend/tests/unit/test_exam_sprint_review_service.py` + `v3-output/P1-4-DASHBOARD/{changes.patch,REPORT.md}`；
- [x] 零 commit / 零 push / 零 stash / 零 reset（仅 `git add -N` 生成 patch 后已 `git reset` 还原索引）；`git status` 干净对齐上清单；
- [x] `backend/app/gen/`（生成代码，gitignored 构建产物）为跑测试自主仓只读复制入 worktree，不入 patch、不入库；
- [x] 无独立端口进程、无模拟器、无 /tmp 遗留、无构建产物（未起 Gradle/Flutter）；
- [x] pytest 全程绝对路径解释器 `/opt/homebrew/bin/pytest`，串行 LIGHT，无内存尖峰。
