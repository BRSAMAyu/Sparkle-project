# 全系统审查·第二轮（R2）— 2 号复审员：引擎·规划与执行链

- 基线：main@ca86bda8（R1 修复已集成，F2 = c519bda4）；冻结 worktree `wt2`
- 切片：`backend/app/orchestration/` 规划族 + `backend/app/services/` 规划执行任务族（plan_* / task_* / execution_* / 调度）
- 方法：①逐项核对 F2 修复落地（diff + 现行代码 + 新测试红绿）；②P1-2 幂等修法在「参数真实演化」分支的专项深查（独立实证探针）；③规划→任务卡→执行→回报→重规划全链路内存集成探针（真实模型/真实服务，不打网络）；④全仓「回调式 JSONB 更新」扫描；⑤P2-6/P2-3 迁移方案设计（不实施）。
- 说明：任务书提到的 `round1/02-fixes.md` 不存在——F2 修复记录随 `c519bda4` 提交（该提交同时新建了 R1 报告文件），修复内容以提交 diff 与新增测试为准。

---

## 1. 修复验证结论（9/9 落地，核心目标达成；发现 1 个 P1 级同类残留 + P1-2 演化分支残留缺口）

| ID | 结论 | 证据 |
|---|---|---|
| P1-1 /complete 400 | ✅ 已落地（选最小方案：ValueError→400，FSM 未放开） | `app/api/v1/tasks.py:1264-1270` try/except ValueError→400 + 埋点；测试 `test_complete_pending_task_returns_400_not_500` 绿。残留：移动端首页一键完成 PENDING 任务仍直接调 /complete（`next_actions_card.dart:_completeTask` 未改），用户交互从 500 变 400，仍是错误路径（产品层"放开 PENDING→COMPLETED"建议未采纳，记 R3 候选） |
| P1-2 applier 幂等 | ✅ 核心目标达成：同参数重复轮不再复利（tag `adaptive_adjusted` + `adaptive_meta.last_applied_*` 比值增量）。⚠️ 演化分支有 4 条残留路径，见 §2 R2-P2-02 | `app/services/plan_adjustment_applier.py:152-156,165,184,208,217,243,383-387`；`test_repeated_same_multiplier_does_not_compound` 等 6 个新测试绿；本探针 Probe A-D |
| P2-1a JSONB summaries | ✅ 已落地（`list()` 拷贝再改） | `app/services/plan_state_service.py:353`；测试 2 个绿。但同类残留见 §2 R2-P1-01 |
| P2-1b JSONB feedback | ✅ 双侧修复（调用侧 deepcopy + `replace_feedback_log` 内 deepcopy） | `app/services/plan_feedback_service.py:335-341,359`；`app/services/plan_state_service.py:561`；测试 2 个绿 |
| P2-2 冷却后置 | ✅ 已落地（预写移除；落地成功后 fresh-read 深合并武装） | `app/orchestration/adaptive_replanner.py:1835-1838,1923-1940`；`test_noop_patch_does_not_arm_adjustment_cooldown` / `test_landed_patch_arms_adjustment_cooldown` 绿。副作用见 §2 R2-P3-06 |
| P2-3 HITL 条件占位 | ✅ 已落地（条件 UPDATE 占位，rowcount=1 才 apply；并发/顺序双确认测试绿） | `app/services/execution_ingestor.py:136-159,456-478`。残留崩溃窗口见 §2 R2-P3-04/05 |
| P2-4 reject 回滚 resync | ✅ 已落地（rebuild_task_index + PlanService.update_progress，异常降级 warning） | `app/services/execution_ingestor.py:215-220,638-655`；真实链路探针 [4] 通过 |
| P2-5 update 委托 | ✅ 已落地（端点委托 TaskService.update，卡投影/链接/focus 失效恢复） | `app/api/v1/tasks.py:839-841`；`test_update_task_goes_through_task_service_projection_sync` 绿 |
| P2-7 outcome 回归 | ✅ 已落地（first=0 且 later>0 → 0 分 + 回归 note） | `app/services/plan_outcome_evaluator.py:84-92,113-114`；4 个新测试绿 |
| P2-8 dispatch 认领 | ✅ 已落地（条件 UPDATE 认领，输家 ValueError→400；保留前置快检） | `app/services/execution_service.py:1015-1041,1074-1079`；`app/api/v1/executions.py` 各端点 ValueError→400/404 映射在位；2 个新测试绿 |

**基线噪音确认**：R1 的 14 个 SQLite `Least` 错误已不再出现（`test_task_service.py` 16 passed，本波全部 7 个测试文件 0 error）。

---

## 2. 复审发现表

| ID | 严重度 | file:line | 场景 | 证据 | 建议 |
|---|---|---|---|---|---|
| R2-P1-01 | **P1** | `backend/app/services/plan_state_service.py:396-410`（on_task_completed）、`:210-232`（on_task_created） | 用户完成任务（正常完成/委派执行/一键完成，全频率最高路径）→ `PlanStateService.on_task_completed` 先**原地修改** ORM 加载的 `state.task_index` dict，再把同一 dict 作为 patch 传给 `upsert_plan_state` → upsert 内 deepcopy+deep-merge 的结果与「已被原地改过的基线」**值相等** → SQLAlchemy flush 时相等性判定"未变更"，UPDATE 不含该列 → `task_index.completed` 永不落库。创建侧 `on_task_created` 对 `total` 同理。由于 `get_or_create_plan_state` 建行时即写入非空默认 task_index（`:188`），"基线为 NULL"的唯一幸存分支在真实系统不存在 → 完成计数**永久冻结**（通常恒 0） | 探针实证（/tmp/ti_probe2.py）：patch 中 `completed:1` 明确传入，upsert 返回后与全新 session 读回均为 `{'total': 0, 'completed': 0, 'by_type': {}}`；SQL echo（/tmp/ti_probe3.py）：`UPDATE plan_states SET facts=?, version=?, updated_at=? WHERE ...` —— **不含 task_index**（version 照常 bump 掩盖写入失败）。下游：`plan_progress_service.py:79-82` 读冻结的 completed/avg_completion_rate 做健康评估（progress 信号失真）；`milestone_handler` 依赖的 completed 计数只能靠唯一 rebuild 路径（ingestor reject，P2-4 修复）或编排全量写刷新。R1 P2-1 类根因残留——修复波只修了 `append_task_summary`/`replace_feedback_log` 两处 | 双保险：①`upsert_plan_state` 对 5 个 JSONB 字段赋值后统一 `flag_modified(state, "task_index"/"facts"/...)`（一行根治整类问题，含未知存量调用点）；②调用侧改为 `task_index = copy.deepcopy(state.task_index or {...})` 后再改。补红测试：独立 session 断言完成前后 task_index 变化（现有 jsonb 测试未覆盖此路径）。注意 `sync_task_summaries`/`Plan.progress` 掩蔽了用户可见症状，需按"信号通路数据丢失"对待 |
| R2-P2-02 | P2 | `backend/app/services/plan_adjustment_applier.py:121-123`（补丁顺序）、`:165`（tag 判别）、`:167-171`（clamp×ratio）、`:400-470`（回滚不还原 last_applied） | P1-2 幂等修法在「参数真实演化」分支的残留缺口（探针 /tmp/p12_probe.py 实证）：**（a）同周期打标串扰**：`_patch_difficulty` 先于 `_patch_time_multiplier` 执行且共用同一 `adaptive_adjusted` 标——任何新任务在同一轮先吃到难度调整即被打标，随后 time 补丁把它当作"已按 last_applied 缩放过"只乘比值 `mult/last`；当乘数稳定时比值=1.0，新任务**完全错过时间放大**（实测：50min 新任务应为 65 实际 50；已缩放任务 39 不变——新任务此后永久比同侪低 1/1.3 倍，除非乘数再演化）。同理，下一轮新插入的复习卡（创建即带 tag）在乘数稳定期也永远拿不到时间缩放。**（b）clamp 边界基线损坏**：上轮 clamp 到 480 的任务（原 400，mult 1.5），乘数回落时按比值从 480 缩放：mult 1.2 → 384（理想 480）、mult 1.1 → 352（理想 440）；MIN 侧反向超调（6min、mult 0.5→clamp 5，mult 0.8→8，理想 5）。损坏不可自愈。**（c）回滚不同步**：`rollback_last_patch` 还原任务字段/标签但不还原 `adaptive_meta.last_applied_*` → 回滚后再应用同参数：比值 = new/last = 1.0 → no-op（实测回滚到 39 后 mult 1.5 再触发仍是 39，理想 45）。**（d）舍入漂移**：逐轮 `round()` 使演化收敛值 ±1min（实测 17min 基线 5 轮最大偏差 +1），自限可接受。**二次叠加检查：未发现**——telescoping 正确，`last_applied` 仅在 count>0 时刷新，重复同参数轮为精确 no-op（新测试已证） | a：交换补丁顺序（time 先、difficulty 后）即可消除主要路径；根治：per-task 记录 `last_time_multiplier`（或 tag 拆分为 `adaptive_time_scaled`/`adaptive_difficulty_scaled`）。b：在 task_state_snapshots 里已有原始 minutes，可改从快照基线计算目标值 `round(orig_minutes × current_multiplier)`。c：rollback 时从 `snapshot.patch_summary` 还原 `last_applied_*` |
| R2-P2-03 | P2 | `backend/app/services/feedback_adjustment_service.py:549-556` | 反馈驱动的 `delete_task` 动作（低评分/减少任务流）对 task_index 写 `{"total": {"$dec": N}}` —— **MongoDB 风格伪操作符**，`_deep_merge`/`upsert_plan_state` 无任何操作符支持 → `task_index["total"]` 被写字面 dict `{"$dec": 3}` → 类型损坏；`plan_progress_service.py:80-84` 读到 dict 后 `completed / total` 抛 TypeError（或 health 评估降级） | `grep -rn '\$dec' app/` 仅此一处；plan_state_service 无 `$dec/$inc` 解析 | 改为读-改-写（deepcopy 后减）或提供受支持的 `$dec` 语义；迁移期顺带清洗存量脏值 |
| R2-P3-04 | P3 | `backend/app/services/execution_ingestor.py:141-159` | HITL confirm 崩溃窗口（失败注入实证）：`_claim_waiting_approval` 先 commit（waiting_approval→succeeded），`_apply_execution_result` 在其后；若二者间进程崩溃，intent 恒为 SUCCEEDED 而任务未完成。重试 confirm：claim 条件不满足 → 走 loser 分支（只置 TRUSTED+发事件），**永不补做任务完成/计划记录**（探针 [5]：重试后 task 仍 IN_PROGRESS） | 探针 [5] 输出：`claim consumed=True → 崩溃 → retry confirm → task.status=IN_PROGRESS` | loser 分支检测"intent 已 SUCCEEDED 且任务未完成且 parsed.success"时幂等重放 `_apply_execution_result`（其内部以 record/现有状态为准，幂等可保证）；或将 claim 延迟到 apply 同一事务 |
| R2-P3-05 | P3 | `backend/app/services/execution_ingestor.py:168-173` | 并发双确认的 loser 分支仍调用 `handle_trusted_execution`（winner 在 `_apply_execution_result:551` 也调）→ 并发场景 learning 信号双计；loser 分支不发 `EXECUTION_QUALITY_RECORDED`、不 `record_outcome`，与 winner 不对称（无功能危害） | 代码对照 | loser 分支仅在"补做 apply"（见 R2-P3-04）路径内触发 learning；纯让位时不重复触发 |
| R2-P3-06 | P3 | `backend/app/orchestration/adaptive_replanner.py:1923-1940,1976-1992` | P2-2 修复副作用：零任务级变更轮不再武装 `last_adjustment_at` → 2h 调整冷却对"参数写了但没落地"的轮次永久失效；每个新健康信号都会重写 plan_state（bump_version + feedback_log 追加 + recent_adaptations/snapshots 追加）并向用户 enqueue 一条"本轮没有任务级调整"的 adaptation update，无节流 | `adaptive_replanner.py:1729` 唯一冷却闸门读 `last_adjustment_at`；零变更分支（1949-1953、1976-1992）不写它 | 零变更轮写独立的轻量 `last_noop_adjustment_at`（如 15-30min 内不再重评估），或在信号服务层按 signature 聚合；feedback_log 追加加窗口上限 |
| R2-P3-07 | P3 | `mobile/lib/features/home/presentation/widgets/next_actions_card.dart:581-588`（只读佐证） | P1-1 产品层残留：移动端一键完成未配合调整（未先 start、未处理 400 文案），PENDING 任务一键完成仍是错误交互 | `_completeTask` 直调 completeTask；后端现返回 400 | R3 候选：产品决策放开 PENDING→COMPLETED（R1 附件 diff 现成）或移动端先 start 再 complete |

**复审通过项（B 任务，无新发现）**：
- **周切换边界**：`execution_schedule_service._next_cron_datetime`（0=Sunday 换算 `(weekday()+1)%7`）四个边界实测全对：周六 23:30→次日 09:00、周日 09:01→下周、周日 09:00 整不重Fire、周一 08:00→本周日。
- **双用户隔离**：真实 ORM 链路下，A 的 adjust/reject 全程不影响 B 的任务、plan_state、facts（探针 [3]）；所有写入均带 user_id+plan_id 过滤。
- **失败注入-reject 路径**：reject→回滚→resync→再完成，计数回归一致（探针 [4] 前半段；后半段的发散恰由 R2-P1-01 造成，非 P2-4 修复缺陷）。
- **P1-2 二次叠加**：无（见 R2-P2-02 结论 d）。

---

## 3. 专项清单

### 3.1 C1：全仓「回调式 JSONB 更新」未走拷贝写调用点清单

扫描方法：`upsert_plan_state` 全部 33 处调用点逐一核对 + PlanState 五个 JSONB 字段（facts/task_index/milestones/task_summaries/feedback_log）与其他模型 JSONB 列（tags/policy/trigger_config 等）的原地变更模式 grep + 真实 ORM 写入探针。

| # | 调用点 | 模式 | 后果 | 判定 |
|---|---|---|---|---|
| 1 | `plan_state_service.on_task_completed`（~L396-410） | 原地改 `state.task_index`/`state.facts` 后作为 patch 传回 → 合并结果==被改基线 → 列被排除出 UPDATE（SQL echo 实证） | completed/by_type/last_completed_task_id/avg_task_duration 不落库，计数永久冻结 | **损坏（R2-P1-01）** |
| 2 | `plan_state_service.on_task_created`（~L210-232） | 同上（task_index.total） | total 增量不落库 | **损坏（同根）** |
| 3 | `feedback_adjustment_service.py:549-556` | `{"$dec": N}` 伪操作符，`_deep_merge` 不支持 | total 被写字面 dict，下游除法 TypeError | **损坏（R2-P2-03）** |
| 4 | `plan_state_service.append_task_summary`（L353） | `list()` 拷贝后改 | — | ✅ 已修（P2-1a） |
| 5 | `plan_state_service.replace_feedback_log`（L561） | `copy.deepcopy` | — | ✅ 已修（P2-1b） |
| 6 | `plan_feedback_service.update_feedback_decision`（L335-341） | deepcopy 后改 | — | ✅ 已修（P2-1b） |
| 7 | `plan_outcome_service.py:352-360`、`self_revision_service.py:114`、`adaptive_replanner` 全部 meta 写点（879/1151/1520/1596/1638/1697/1884/1933/2187/2199/2226/2593/2619/2681/2850）、`execution_engine.py:2422-2440`、`execution_service.py:2366,2400`、`validation_engine.py:643`、`plan_feedback_service.py:92,234-250`、`plans.py:1308,1455`、`plan_service.py:277` | 均为 dict()/list 拷贝或全新值 | — | ✅ 安全 |

**根治建议（F2 移交项首选）**：在 `upsert_plan_state` 内对每个 JSONB 字段赋值后统一 `sqlalchemy.orm.attributes.flag_modified(state, <field>)`——消除"调用侧原地改→相等基线"整类问题（含未来新增调用点），成本 5 行；配合 R2-P1-01 的红测试。备选：模型层换 `MutableDict/MutableList`（影响面大，不推荐本阶段做）。

### 3.2 C2：Alembic 迁移设计（方案，不实施）

前置事实：`plan_execution_records` 现无 `execution_intent_id` 列（`app/models/plan_execution_record.py:40-90`）；迁移链当前为**多 head**（python 扫描得 47 个 head，如 `stage_c5_aurora_decision_telemetry`、`oc004e5f6a7b8`、`c66d70d3967a` 等）——新迁移须先 `alembic heads` 确认并选择挂载点（建议与 execution 域同链，或先出 merge revision）；`gateway schema.sql` 是自动导出快照，不手改（硬规则 2）。

**迁移 A（P2-3 配套）：`plan_execution_records` 意图级唯一约束**
```
revision: r2_oc01_intent_unique（down_revision=<execution 域 head，实施时以 alembic heads 为准>）

upgrade:
1) op.add_column('plan_execution_records',
     sa.Column('execution_intent_id', GUID(), nullable=True))          # 新列
2) op.create_foreign_key('fk_plan_exec_records_intent',
     'plan_execution_records', 'execution_intents',
     ['execution_intent_id'], ['id'], ondelete='SET NULL')
3) 存量回填：无 intent 归属信息，保持 NULL（不猜）
4) op.create_index(
     'uq_plan_execution_records_intent',      # 部分唯一索引（PG 方言）
     'plan_execution_records', ['execution_intent_id'],
     unique=True,
     postgresql_where=sa.text('execution_intent_id IS NOT NULL'))
   # SQLite 分支：建普通唯一索引即可（现有测试基座为 SQLite；索引 DDL 需沿用仓内 PG 方言守卫模式，防止 R1 的 Least 型回退）
downgrade: drop index → drop FK → drop column

代码配套（随迁移同波）:
- `execution_ingestor._create_plan_execution_record` 写入 execution_intent_id=intent.id
- 捕获 IntegrityError → 回查现有记录直接返回（与 P2-3 条件占位构成双层防线）
```

**方案 B（P2-6 配套）：计划配额 TOCTOU**
- **推荐：advisory lock（无 schema 变更）**——`PlanService.create` 在 check_quota_available 与 insert 的**同一事务**内先执行：
  `SELECT pg_advisory_xact_lock(hashtextextended(:user_id::text, 0))`
  同用户并发创建串行化、跨用户零影响、会话结束自动释放；死锁风险低（单锁事务）。代码改动 2 处（quota check 入口 + create 事务）。
- 备选（如需纯 DB 约束）：新表 `user_plan_quota_counters(user_id PK, active_count int NOT NULL DEFAULT 0, updated_at)`，创建/归档/删除事务内 `SELECT ... FOR UPDATE` 维护计数——缺点是计数漂移需要巡检任务对账，不建议首选。
- 部分唯一索引无法表达"≤3 个活跃"语义，不适用。
- 附带清理：删除 `plan_quota_service._get_user_quota` 对 `plan_quota:{user_id}` 的死缓存读（或补写入方）——防未来无声改配额。
- 可选 DB 兜底（可与迁移 A 同波）：`execution_intents` 上部分唯一索引 `(task_id) WHERE status IN ('draft','ready','queued','dispatched','running','waiting_approval')`，把 `_ensure_no_active_intent` 升级为 DB 级保证（需先核对存量无违例行）。

---

## 4. 测试执行记录

环境：worktree `wt2`（ca86bda8），`/opt/homebrew/bin/pytest`（py3.11），SECRET_KEY/JWT_SECRET/REDIS_URL 按规注入；逐文件运行（内存纪律）。环境处置：worktree 缺 `app/gen` → 从主仓复制 `sparkle/` 与 pb2 产物（gitignored 脚手架）；本机 Data 卷 100% 满（一次 ENOSPC）→ 清理 wt2 内可再生 `__pycache__` 并以 `-p no:cacheprovider + PYTHONDONTWRITEBYTECODE` 运行后恢复。

| # | 目标 | 结果 |
|---|---|---|
| 1 | `tests/api/test_task_complete_and_update_api.py`（P1-1/P2-5） | **4 passed** in 6.16s |
| 2 | `tests/unit/test_execution_ingestor_confirm_reject.py`（P2-3/P2-4/P2-8） | **6 passed** in 14.98s |
| 3 | `tests/unit/test_plan_state_service_jsonb.py`（P2-1a/1b） | **4 passed** in 0.38s |
| 4 | `tests/unit/test_plan_adjustment_applier.py`（P1-2） | **29 passed** in 0.43s |
| 5 | `tests/unit/test_adaptive_replanner_stage34.py`（P2-2） | **7 passed** in 2.54s |
| 6 | `tests/integration/test_plan_outcome_evaluator.py`（P2-7） | **4 passed** in 0.06s |
| 7 | `tests/unit/test_task_service.py`（基线噪音确认） | **16 passed** in 1.77s，无 `Least` 错误 |
| 8 | 独立探针（/tmp，不入仓，python3.11 直跑） | `p12_probe.py`：P1-2 演化分支 5 场景（A 同周期打标串扰 / B clamp 穿越 / C 舍入漂移 / D 回滚失同步 / E cap 自愈）；`r2_chain_probe.py`：全链路 7 节（完成同步 / 幂等 / 双用户 / reject resync / 崩溃注入 / 周界 / 时区）；`ti_probe2.py`+`ti_probe3.py`：task_index 写入 patch 断言 + SQL echo 实证 UPDATE 不含 task_index |

范围与噪音：R1 P3-1..P3-8 未在 F2 修复波内（保持原状，不重报）；P3-2 的 `date.today()` 混用经代码确认仍在（applier `_fetch_upcoming_tasks:564`、occurrence、scheduler cron 无 timezone），探针 [7] 因运行时刻未落在 0:00-8:00(CN) 窗口未复现实际偏一天，机制性结论沿用 R1。v1 基线失败与本切片无关。
