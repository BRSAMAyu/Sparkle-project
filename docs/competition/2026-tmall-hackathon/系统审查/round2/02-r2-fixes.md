# R2 修复波·Wave1 — G2 修复记录（规划执行链）

- 修复员：G2（切片：规划→任务卡→执行→回报→重规划链）
- 基线：worktree `wt2` @ ca86bda8（冻结，未 commit；完整 diff 见同目录 `02-r2-fixes.patch`）
- 对应复审报告：[02-r2-engine-planning.md](02-r2-engine-planning.md)
- 方法：红-绿证明（新测试先在冻结代码上跑红，修复后跑绿；P1-01 红测试必须真 PG）。逐项测试命令单独执行，pytest 只跑目标文件。

## 修复总览

| ID | 严重度 | 结论 | 红→绿 |
|---|---|---|---|
| R2-P1-01 | **P1** | ✅ 已修（upsert 统一 `flag_modified` 根治 + 调用侧 deepcopy 双保险） | 真 PG 上 3 failed → 3 passed |
| R2-P2-03 | P2 | ✅ 已修（`{"$dec": N}` 伪操作符改为读-改-写真实减法） | 2 passed（行为等价红由报告 §2 实证覆盖） |
| R2-P2-02 | P2 | ✅ 已修（拆专属标签+轮前快照判幂等 / 时间基线表 / 回滚还原 last_applied+baselines） | 冻结基线 5 failed → 修复后 35 passed（含 29 存量） |
| R2-P3-04 | P3 | ✅ 已修（confirm 输家分支检测"claim 已提交但 apply 未执行"幂等补做） | 冻结基线 1 failed → 修复后 7 passed |
| C2（stretch） | — | ✅ 已实施（迁移 A：`execution_intent_id` 部分唯一索引 + 服务层 IntegrityError 幂等；方案 B：`PlanService.create` 用户级 advisory xact lock；附带清理死缓存读） | scratch DB 全链 upgrade/downgrade/upgrade + 行为探针通过；服务层 3 passed |

## R2-P1-01（P1）：task_index/facts 写入静默丢失

**根因确认**：`sqlalchemy/orm/persistence.py::_collect_update_commands`（SQLAlchemy 2.0.48）对每个出现在 `committed_state` 的属性做 `impl.is_equal(当前值, 已提交值)` 判定，相等则该列不进 UPDATE。调用侧原地修改 ORM 加载的 dict 时，`committed_state` 持有的是同一对象引用（基线被一并改掉），upsert 内 deepcopy+deep-merge 的结果再与之等值 → 列被永久排除出 UPDATE，`version` 照常 bump 掩盖失败。该判定与后端方言无关，但按任务要求红测试在真 PG 上用**两个独立 session**验证落库真值。

**修法（双保险，报告 §3.1 建议全采纳）**：
1. `upsert_plan_state` 对 6 个 JSONB 字段（facts/milestones/task_index/task_summaries/feedback_log/constraints）赋值后统一 `flag_modified`——根治整类"回调式 JSONB 更新"丢失，含未知存量调用点与未来新增调用点（`plan_state_service.py`）。
2. `on_task_completed` / `on_task_created` 改为 `copy.deepcopy` 后再改，不再污染已提交基线。

**红测试**：`tests/integration/test_plan_state_jsonb_pg.py`（3 个用例：单次完成落库、双次完成计数=2、创建 total 落库；第二个独立 session 只信 DB 真值；PG 不可用时 skip 以保 SQLite 基座绿）。红：`{'total': 0, 'completed': 0, 'by_type': {}}` 恒定而 version 2→3——与复审探针一致；绿：3 passed。

## R2-P2-03：`{"$dec": N}` 伪操作符

`feedback_adjustment_service._apply_action`（delete_task）改为读-改-写：`get_or_create_plan_state` → deepcopy task_index → `total = max(0, total - len(target_task_ids))` → 按 `on_task_completed` 同一约定重算 `avg_completion_rate`。注意 deep-merge 语义下 patch 缺键删不掉列中旧值，total 归零时必须显式写 0 覆盖残留完成率（首版实现踩到此坑，已由测试钉住）。测试：`tests/unit/test_feedback_adjustment_delete_task.py`（2 passed：真实减法+类型、下限 0+完成率覆盖）。

## R2-P2-02：P1-2 幂等修法的演化分支残留（4 项全修）

实现于 `plan_adjustment_applier.py`：

- **(a) 同周期打标串扰**：补丁顺序改为时间先、难度后；更关键的是两补丁各自只依据**本轮开始前的标签快照**（`preexisting_tags`）判幂等，时间维度专属标 `adaptive_time_scaled`、难度维度专属标 `adaptive_difficulty_scaled`（存量 `adaptive_adjusted` 继续按"已缩放"保守对待，避免老数据二次复利）。实证数字回归：50min 新任务在乘数稳定期（1.3）同轮拿到 65 与完整难度步进（原实现 50，错过放大）。
- **(b) clamp 边界基线损坏**：新增 `adaptive_meta.time_baselines`（task_id → 首次缩放前真实分钟数，仅对未缩放任务记录——存量已缩放行的当前值并非真实基线，记入会虚高）。目标值 = `clamp(round(基线 × 当前乘数))`。实证回归：400@1.5→480 后乘数回落 1.2→480（原 384）、1.1→440（原 352）；MIN 侧 6@0.5→5 后 0.8→5（原 8）。
- **(c) 回滚不同步 last_applied**：快照新增 `adaptive_meta_before`（记录本轮开始前 applier 自有的 last_applied_time_multiplier / last_applied_difficulty_shift / time_baselines），`rollback_last_patch` 按其还原（原值为空则 pop；旧快照无该字段保持原行为不猜）。回归：回滚后重应用同参数 30→45（原为 no-op 停在 30）。
- **(d) 舍入漂移**：被 (b) 的基线重算吸收——每轮从整数基线取整而非从上一轮舍入结果继续比值缩放。回归：17min @1.2→20、@1.4→24（比值路径给 23）。
- 附带：前置复习卡创建不再携带 `adaptive_adjusted`（只留 `adaptive_prerequisite_review`），下一轮可正常吃到时间缩放（原实现创建即带标、乘数稳定期永久错过）。存量旧卡受 (a) 的保守兼容约束仍走比值路径，属可接受残留（无法区分"仅难度打标"与"已时间缩放"，保守侧防复利优先）。

**红-绿**：6 个新测试（`tests/unit/test_plan_adjustment_applier.py` 追加），冻结基线跑出 **5 failed**（同周期串扰/clamp 高低侧/漂移/回滚还原），修复后 **35 passed**（29 存量 + 6 新增全绿）。

## R2-P3-04：confirm 崩溃窗口重试永不补 apply

`execution_ingestor.confirm_result` 输家分支重构：输掉 claim 后先 `refresh(intent)`（claim 是条件 UPDATE 且 `synchronize_session=False`，会话内对象是陈旧的 waiting_approval——首版实现漏了这点，陈旧状态使补偿条件永不触发），再检测「intent=SUCCEEDED ∧ parsed.success ∧ 任务未完成」（新 `_needs_result_application` 用裸列 SELECT 绕过 identity map，防陈旧会话掩盖并发已提交状态）→ 幂等补做 `_apply_execution_result`（任务已完成则不进该分支：无双完成；PlanExecutionRecord 在任务完成提交之后才创建：无双写；事件与 learning 由 apply 内部统一发布，与 winner 路径对称）。副作用：让位分支的 `handle_trusted_execution` 双计（R2-P3-05）在补做路径中不再发生；纯让位路径行为未动（P3-05 非本波任务，保持现状）。

**红-绿**：新测试 `test_confirm_retries_apply_after_crash_between_claim_and_apply` 在冻结基线 **failed**（task 恒 IN_PROGRESS，即报告探针 [5] 场景），修复后随文件 **7 passed**。原 `test_confirm_lost_race_does_not_reapply_result` 的模拟"只 claim 不 apply"恰是崩溃窗口语义，已更新为真实双击竞态（winner 完成 claim+apply，断言 loser 不重复 apply），P2-3 不变量保持。

## C2（stretch）：迁移 A + 方案 B

**前置事实修正**：`alembic heads` 实测**单 head `0150e391736a`**（一个 merge revision）——复审报告 §3.2 "47 个 head" 的扫描结论有误，新迁移直接挂链，无需先出 merge。

**迁移 A**（`alembic/versions/sr8r2g2_20260918_plan_exec_records_intent_unique.py`，`sr8r2g2_c2_intent` → down `0150e391736a`）：
- `plan_execution_records.execution_intent_id`（PG UUID / SQLite CHAR(36) 方言守卫，nullable）+ FK `fk_plan_exec_records_intent` → `execution_intents.id` ondelete SET NULL；
- 部分唯一索引 `uq_plan_execution_records_intent … WHERE execution_intent_id IS NOT NULL`（SQLite 上退化为全列唯一索引，NULL 互异，语义等价，沿用仓内方言守卫模式防 R1 的 Least 型回退）；
- 存量回填：无归属信息保持 NULL（不猜）；downgrade 逆序回滚。

**代码配套**：模型列+`__table_args__` 索引+to_dict；`PlanExecutionRecordService.create_record` 写入 `execution_intent_id`，捕 IntegrityError → rollback → 按 intent 回查现有记录幂等返回；`execution_ingestor._create_plan_execution_record` 传入 `intent.id`。与 P2-3 条件占位构成双层防线。

**方案 B**：`PlanService.create` 在配额检查与 insert 同一事务内先 `SELECT pg_advisory_xact_lock(hashtextextended(:user_id::text, 0))`（仅 PG 分支，SQLite 基座跳过；同用户创建串行化、跨用户零影响、事务结束自动释放）。附带清理：删除 `plan_quota_service._get_user_quota` 对 `plan_quota:{user_id}` 的死缓存读（全仓无写入方）。

**scratch DB 全链验证**（`sr8r2_g2_c2`，验证后已删除）：
1. fresh 库 `alembic upgrade head`（全 137 个迁移）通过；
2. 结构验证：列 uuid/nullable ✓、FK confdeltype='n'(SET NULL) ✓、索引 `CREATE UNIQUE INDEX … WHERE (execution_intent_id IS NOT NULL)` ✓、version=`sr8r2g2_c2_intent` ✓；
3. `downgrade -1` 干净（列/索引归零、版本回 `0150e391736a`），再 `upgrade head` 可逆 ✓；
4. 行为探针：同 intent 第二条记录被拒（IntegrityError）✓、NULL 归属记录共存 ✓。
5. 服务层幂等测试（SQLite）：`tests/unit/test_plan_execution_record_intent_unique.py` 3 passed。

**遗留**：`gateway schema.sql` 是 `make sync-db` 自动导出快照（硬规则 2），本波不含 docker 环境未重新导出，下次 `make sync-db` 会带上新列/索引，不手改。

## 测试执行记录（逐文件，单命令）

| # | 目标 | 结果 |
|---|---|---|
| 1 | `tests/integration/test_plan_state_jsonb_pg.py`（P1-01，真 PG，冻结代码） | **3 failed**（红） |
| 2 | 同上（修复后，真 PG） | **3 passed** |
| 3 | `tests/unit/test_plan_state_service_jsonb.py`（P2-1a/1b 回归） | 4 passed |
| 4 | `tests/unit/test_feedback_adjustment_delete_task.py`（P2-03） | **2 passed** |
| 5 | `tests/unit/test_plan_adjustment_applier.py`（P2-02，冻结代码） | **5 failed**（红）+ 30 passed |
| 6 | 同上（修复后） | **35 passed** |
| 7 | `tests/unit/test_execution_ingestor_confirm_reject.py`（P3-04 新用例，冻结 ingestor） | **1 failed**（红） |
| 8 | 同上（修复后） | **7 passed** |
| 9 | `tests/unit/test_plan_execution_record_intent_unique.py`（C2 服务层） | **3 passed** |
| 10 | `tests/test_plan_task_service_production.py`（回归） | 50 passed / 5 failed（与冻结基线完全一致，基线固有） |
| 11 | `tests/test_plan_task_tools_production.py`（回归） | 66 passed / 6 failed（与冻结基线完全一致，基线固有） |
| 12 | `test_adaptive_replanner_stage34.py` + `test_plan_outcome_evaluator.py` + `test_task_complete_and_update_api.py`（回归） | **15 passed** |
| 13 | 全部新/改测试文件合并跑（含真 PG） | **50 passed** |

## 剩余清单 / 移交

- **R2-P3-05/06/07**（P3）：非本波任务书范围，未动。P3-05 的双计问题在 P3-04 补做路径已部分消除；纯让位路径仍保留原 learning 触发（防 chat_control 场景 learning 丢失）。
- **R2-P1-01 产品层残留**（P3-07 / 移动端 `_completeTask`）：归 06/07 切片。
- **存量 `adaptive_adjusted`-only 行**：继续走保守比值路径（防复利优先），随任务被重新触碰逐步迁移到专属标。
- **快照无界增长**（`task_patch_snapshots`/`time_baselines` 只增不减，旧债）：建议后续加窗口上限。
- **基线固有失败**：`test_plan_task_service_production.py` 5 个、`test_plan_task_tools_production.py` 6 个在冻结 ca86bda8 上同样失败，与本波无关（复审报告"v1 基线失败与本切片无关"一致），建议单独立项。
- **复审报告勘误**：迁移链为单 head（`0150e391736a`），非 47 head；SQLite 其实能复现 P1-01 的 flush 语义（等值判定与方言无关），但红测试按要求落在真 PG。
