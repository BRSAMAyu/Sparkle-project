# INTAKE-TEMPLATE —— 复用路径补 7 天冲刺模板（北极星 C 纵队）

> worktree: `Sparkle-sysrev/wt166`（基线 `4ea97156`）｜2026-09-23
> 交付物：本报告 + `changes.patch`（2 文件，+454/−16）｜零 commit、零凭据、主仓零写入

## 0. 缺陷一句话

用户经 goal 建计划后走 exam-sprint intake，命中 NBP-3b 的 goal 关联复用
（`Goal.goal_type.in_(("exam","academic"))`）即返回 goal 计划——而 goal 计划
只有里程碑梯任务（`goals.py create_goal` 只建 `goal_first_step`，无 `day:N`
标签），**7 天冲刺 Day1-Day7 脊柱在最常见路径缺位**：`daily_task_selection`
的 `_plan_current_day` + `_is_today_relevant` 依赖 day:N 标签推进旅程，无标签
则旅程无 Day 概念，CP-04 的 S1/S2 判定面退化（JOURNEY-DRIVER 实测 S2 不可观测）。

## ① 方案裁决论证（A：复用时补模板）

**裁决：方案 A（复用后补挂模板），并加 goal 闸。**

### 为什么不选 B（收紧复用条件）

B = 只有已具 sprint 模板形状的 goal 计划才复用，否则走完整生成。逐行证据表明
这**必然复发 NBP-3 双计划**：

- `goals.py:191`：`plan_type = PlanType.SPRINT if payload.goal_type in ("exam","academic")`
  —— goal 驱动计划恒为 active SPRINT、`target_date=goal.target_date`；
- `exam_sprint_intake_service.py` goal 关联兜底命中的计划 subject 恒为 NULL
  （goals.py 从不写 subject），**不在 `uq_plans_user_sprint_goal_active` 部分唯一
  索引谓词内**（INTAKE-IDX 迁移）；
- 若 B 放行完整生成：新计划 subject 非空，与 goal 计划（subject NULL）在索引上
  互不可见 → **静默双 active sprint 计划**，正是 NBP-3（LOOP2 实测根因）；
- 若先回填 subject 再生成：INSERT 撞 INTAKE-IDX → IntegrityError → 403 面暴露给
  goal 用户，intake 在真实链路上直接不可用。
- 结论：B 要么复发 NBP-3 静默双计划，要么制造新的 403 故障面。BP-7/INTAKE-IDX
  的幂等复用是 DB 级收敛语义，不应为旅程形状让路——**形状缺失应在复用计划内补齐**。

### A 的补挂幂等与并发安全（实现中钉死的三层闸）

1. **形状闸**：计划已有任何 `day:` 标签任务（`_plan_has_day_template_tasks`，逐行
   扫 tags，与 `_task_day_index` 消费口径同源）→ 跳过。只认 `day:` 标签、不认
   `order_index>=1000`——goal 里程碑任务恰好 order_index=1000，会被
   daily_task_selection 的 order_index 兜底当作 day1，但它没有脊柱，不能据此跳过。
2. **goal 闸**（并发契约，真并发测试逼出来的）：`plan.goal_id is None` → 不补。
   `PlanService.create` 内部先 `commit` 计划、任务随后逐任务提交——并发 intake 的
   复用查询可能命中"已提交但脊柱未落"的半成品计划，补挂 = 双模板 +
   `plan_states` get-or-create 竞态（实测 PendingRollbackError，见 ④）。
   缺陷本体只在 goal 计划（无生成方）；intake 生成计划由生成方负责补齐。
3. **PG 行锁**：`SELECT id FROM plans WHERE id=:id FOR UPDATE`（方言门控，仅
   postgresql）串行化"同 goal 计划并发补挂"——复查 + 首个任务提交在同一持锁窗口，
   后到者复查必见 day:N。只锁 id 列，避免实体重选冲掉 subject 回填。

## ② 实现清单

全部改动限于 `backend/app/services/exam_sprint_intake_service.py` 与
`backend/tests/unit/test_exam_sprint_intake_service.py`：

| 项 | 内容 |
|---|---|
| `intake()` 复用分支 | 复用命中后调 `_supplement_sprint_template_tasks`，再 `_bundle_from_existing_plan`（launch 锚点直接反映补挂后的 day-1 包）；**IntegrityError 并发兜底分支刻意不补**——该计划的生成方正在补齐模板，败者只读 |
| `_create_sprint_template_tasks()` | 从 `_generate_plan_and_tasks` 原样抽出 phase→day_spec→Task 循环（day:N 标签、day*1000 order_index、guide_json/ai_prompt/success_criteria），两条路径共用，形状保证同构 |
| `_decorate_sprint_plan_metadata()` | 抽出 source_metadata 块（day_highlights/exam_sprint_intake/study_materials/post_exam_review）共用——复用计划由此升级为一等冲刺计划（dashboard 读 exam_sprint_intake、plan 详情/aurora 读 day_highlights、考后复盘读 post_exam_review） |
| `_plan_has_day_template_tasks()` | day: 标签存在性判定（幂等闸） |
| `_supplement_sprint_template_tasks()` | goal 闸 → PG 行锁 → 幂等复查 → 复用 strategy/session 走共享构造器补任务 → 元数据块 → commit |
| 测试（4 新 + 2 更新 + 1 夹具忠实化） | 见下方回归矩阵 |

### 新增回归（红线逐条）

- `test_intake_reuse_supplements_seven_day_template_for_goal_plan`：goal 建计划 →
  intake 复用 → 断言单计划、day 集合 == {1..days_left} 全脊柱、day*1000 band、
  phase: 标签、**里程碑任务不删**、source_metadata 三块齐全、launch 锚点含里程碑。
- `test_intake_reuse_supplement_is_idempotent_on_repeat`：重复 intake（第二次走
  BP-7 主键 + subject 回填路径）→ 同一 plan_id、任务零增长、脊柱完整。
- `test_intake_does_not_force_template_on_non_exam_goal_plan`：project 族不复用、
  补挂根本不触发、goal 计划无任何 day:N 任务被强加。
- `test_intake_supplement_skips_non_goal_plan_even_without_day_tags`：**goal 闸
  契约**——无 goal_id 的计划即使无 day 标签也不补（并发半成品计划保护）。

### 既有测试处理（诚实申报）

- NBP-3 / NBP-3b 两测试的 `first_day_task_ids == [milestone]` 断言更新为
  `milestone in first_day_task_ids` + day 标签存在断言——旧断言编码的正是本卡
  修复的缺陷行为；复用语义断言（`_generate_plan_and_tasks` 不被调、单计划、
  subject 回填自愈）原样保留且全绿。
- BP-7 测试夹具两任务补 `day:1/day:2` 标签（夹具忠实化：intake 真实生成的任务
  恒带 day:N，见服务 tags 构造）；断言未动。

## ③ 回归矩阵（对比法：/tmp 基线克隆 HEAD vs 本 worktree）

定向家族（intake 域 + day:N 消费方 + 元数据消费方，零新增面）：

```
test_exam_sprint_intake_service.py / test_exam_sprint_intake_concurrency.py
test_intakeidx_plans_sprint_goal_unique_migration_sqlite.py
test_exam_sprint_review_service.py / test_dailyflow_p2_today_filter.py（day:N 消费方）
test_exam_sprint_dashboard_service.py / test_north_star_metrics_service.py
test_exam_sprint_api.py / test_daily_startup_message.py / test_pack_quality_analysis_task.py
```

| 基座 | 结果 |
|---|---|
| 基线克隆（HEAD 4ea97156，无补丁） | **49 passed / 0 failed** |
| 本 worktree（+补丁，终版） | **53 passed / 0 failed**（= 49 基线 + 4 新增，零回归） |
| 真并发测试（关键单点，多次重复） | 补丁后 4/4 passed（基线同窗口 3/3 passed） |

lint：`ruff check` / `ruff format --check --line-length 120` 全过。
DATABASE_URL=sqlite+aiosqlite SECRET_KEY=test，主库只读。

## ④ 诚实申报

- **过程中引入过一版真回归，已修复并钉死**：初版补挂无 goal 闸，
  `test_concurrent_intake_same_goal_creates_exactly_one_plan` 从稳定绿变为
  3/4 失败（基线克隆同窗口 3/3 绿）。根因即 ①-2 所述 `PlanService.create`
  先 commit 计划的半成品窗口；修复（goal 闸）后 4/4 绿。此教训已写进方法
  docstring 与专用回归测试。
- **残余窗口（明知未堵）**：同一 goal 计划上两路 intake *同时* 走复用分支、
  且都在对方首任务提交前通过形状复查 → 理论双模板。PG 上被行锁串行化
  （生产基座）；sqlite 测试基座无锁但无此并发面（测试不构造双复用并发）。
  TaskService.create 逐任务提交的架构使长持锁不可行，属既有架构约束。
- **补挂的模板保真度**：strategy/session 来自本次 intake 表单（与全量生成完全
  同源），非从旧数据重建——保真度等同首次生成。
- **备份计划单测超时风险**：单测试文件 4 分钟量级（TaskService.create 副作用
  链路 focus_context/card 投影所致，既有特性，非本卡引入）。
- worktree 内 `backend/app/gen` 为测试期只读拷贝自主仓（proto 逐字节一致已核，
  NBP23 同例），不入 patch，收工已删。

## ⑤ 迁移裁决：存量回填 = **不做脚本，首触补（本卡语义自带）**

- 存量面：NBP-3b 上线后已发生过 goal 复用的用户，其计划无 day:N 脊柱。
- 回填脚本不可行/不值：模板生成需要 strategy + PlanningSession.collected
  （subject/每日时长/掌握度/弱章），session 在 Redis 有 TTL，存量用户早已蒸发；
  从 plan 裸数据重建 strategy 是有损猜测，违背诚实性红线。
- **首触补**：用户下次任一点击 intake（BP-7 明文设计：断线重连/重复提交是常态）
  即命中复用 → 补挂 → 自愈，且保真度等同首次生成。单计划不变量零风险。
- 诊断 SQL（主会话如需摸底，只读）：
  ```sql
  SELECT p.id, p.user_id, p.created_at FROM plans p
  WHERE p.type='sprint' AND p.is_active AND p.deleted_at IS NULL
    AND p.goal_id IS NOT NULL AND p.target_date IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.plan_id=p.id
                    AND t.deleted_at IS NULL AND t.tags::text LIKE '%"day:%');
  ```

## ⑥ 冲突面声明

- 改动仅 `exam_sprint_intake_service.py` + 其单测，无 schema/迁移、无 proto、
  无网关。
- **wt162（tour）**：其旅程断言可能受益——goal→intake 链路复用后计划将含
  day:N 脊柱，若 wt162 有对"复用计划任务数/day 标签"的断言需按新形状复核
  （本卡单测已示范口径）。除此之外零交集。
- wt164/wt165：零交集（未动 daily_task_selection/dashboard/review 代码，
  仅被其消费）。

## ⑦ 活栈验证交接（留主会话）

合入 + 重启后：用 `/tmp/ns001_journey_demo_state.json` 锚点续跑 JOURNEY-DRIVER
day2。预期：demo 用户对既有 goal 计划重跑 intake（或任意同 subject+exam_date
intake 重入）→ 复用即补挂 → 计划出现 day:1..N 脊柱 → **S1（次日计划适应）可
观测**、S2 判定面恢复。注意锚点用户若其计划 subject 已回填，重入走 BP-7 主键
+ goal 闸（goal_id 非空）同样补挂，两条复用路径均已覆盖测试。

## ⑧ 收工核查

- [x] 无 commit / 无 push（`git status`：2 modified + v3-output/INTAKE-TEMPLATE/ 未跟踪）
- [x] 主仓零写入；活栈零触碰；无 .env 读写
- [x] /tmp 清理：基线克隆 `/tmp/wt166-baseline`（含 gen 拷贝）、探针日志
      `/tmp/wt166_*.log` 已删；`/tmp/ns001_journey_demo_state.json` 非本卡产物未动
- [x] pytest tmp：全程 `-p no:cacheprovider`；并发测试 sqlite 文件走 pytest
      tmp_path（KB 级，pytest 自动轮转 3 代）
- [x] worktree 内 `backend/app/gen` 拷贝已删；worktree 内无进程残留（纯 pytest，已退）
- [x] 交付物：本报告 + `changes.patch`（558 行 diff，2 文件）
