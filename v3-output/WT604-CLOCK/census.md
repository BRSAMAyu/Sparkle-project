# WT604 · 全库时钟约定普查（约定地图 + 错配清单 + 测试风险面）

- 工位：wt604（worktree `wt604-clock`，分支 `agent/node-b/wt604/clock`，基线 = main 头 `6f6cd08e`）
- 日期：2026-09-25
- 范围：`backend/app/`（产品读写面）+ `backend/tests/`（播种面）。**只修机械安全项，产品侧错配一律报告不修。**
- 关联在案：V3-FIX-314（plan.created_at 墙钟当 UTC 双重换算，归属 wt602 在飞 `agent/node-b/wt602/today`）、V3-FIX-315 族C（测试 UTC 日播种，wt590 收口 0b2273b3）、wt559 六测（V3-FIX-250 族）、wt582/wt602 取证。

---

## 0. 一句话结论

代码层约定是清晰的 **「naive 列 + UTC 值」**（`models/base.py` `_utcnow` + `core/time_utils.py`），但存在**两股系统性逆流**：(a) **客户端直存的墙上钟列**（FocusSession/CalendarEvent，V3-FIX-37 已定界）与其余 UTC 列在**同一批消费文件里混用**；(b) **plan/task.created_at 的写面（代码=UTC 默认）与生产实证（JOURNEY 实测=上海墙上钟）矛盾，且读面已经分裂成两种假设并存**——这是 V3-FIX-314 的根因面，本普查给出其完整消费面清单交 wt602。

## 1. 写面普查（存储约定地图）

### 1.1 全局基线

- `models/base.py:153-158/252-257`：`BaseModel`/`HardDeleteBaseModel` 的 `created_at/updated_at` = **naive `DateTime` 列 + `_utcnow` 默认**（`core/datetime_utils.py:13`，= 真 UTC 的 naive 形式，与宿主机时区无关）。
- `core/time_utils.py`：仓库唯一权威时间工具（`utcnow/local_date/local_midnight_as_utc_naive/local_midnight_wall/wall_clock_to_utc_naive(V3-FIX-297)/utc_naive_to_wall_clock(V3-FIX-300)`），文档明确两种 naive 存储钟并存。
- 列类型几乎全是 `TIMESTAMP WITHOUT TIME ZONE`（naive）；`DateTime(timezone=True)` 仅 `accountability.py:81-82`、`agent_stats.py:28-29`、`calendar_event.py:47-57` 三处（calendar 列虽带 tz 类型，实际存的是客户端发来的**无时区后缀本地 ISO**，读出为 naive——见 wt582/wt602 取证）。

### 1.2 分类统计（按列族）

| 分类 | 列族（代表） | 写点证据 | 数量级 |
|---|---|---|---|
| **A. UTC 存储**（naive 列 + 服务端 utcnow 写入） | `BaseModel.created_at/updated_at`（约 100+ 表继承）；`Task.completed_at/started_at/paused_at/confirmed_at`（`task_service.py:716`、`execution_service.py:3130`、`execution_ingestor.py:627` 全部 `_utcnow()`）；`StudyRecord.created_at`（time_utils.py:12 点名）；`ChatMessage.created_at`（`chat.py:70` default=utcnow，主键）；audit/security/idempotency/job/notification 全族（`audit_log.py` 10+ 列 default=datetime.utcnow）；`Plan.confirmed_at`（`plan_service.py:540` `_utcnow()`，注释明示 naive UTC） | ORM 默认 / service 层 `_utcnow()` | 绝对多数（models/ 33 文件含 server_default 或 default=utcnow） |
| **B. 墙上钟存储**（客户端本地 naive 直存） | `FocusSession.start_time/end_time`（`models/focus.py:38-39`；mobile 发本地 ISO 无时区后缀，V3-FIX-37 定界）；`CalendarEvent.start_time/end_time`（`api/v1/calendar.py:140-141` 直存 `event_in.start_time`，客户端本地钟） | 客户端 payload 直存 | 2 表 5 列 |
| **C. 混**（同一列/同一写面不止一种钟） | ① `Plan.created_at`/`Task.created_at`：**代码写点 = ORM 默认 UTC**（`plan_service.py:108`、`task_service.py:178` 均不显式赋 created_at；全库 DB 持久化 Plan 写点仅 plan_service 8 处 + guest_seed + 脚本，无一处显式本地钟），但 **JOURNEY 生产实证 = 上海墙上钟**（FIX-314：created 21:15:30 与 day0 run_id 20260922-211514 同钟）→ 环境级写钟与代码约定冲突，**在案 wt602**。② `guest_seed_service.py`：`created_at=datetime.utcnow()`（UTC）与 `target_date=date.today()`（宿主机本地日，:2006/:2042）**同一函数内混钟**。③ 北极星/活跃度消费面把 A、B 两类列放进同一表达式（见 §3）。 | 代码 vs 生产实证矛盾 + 同函数混钟 | 2 列在案 + 1 个种子面 |

宿主机钟依赖写点（`datetime.now()`/`date.today()`，UTC 宿主上无害、+8 宿主上变墙钟）：`core/task_manager.py:123`（内存 TaskStats，非 DB）、`guest_seed_service.py:2006/2042/2098`（due_date/target_date）、`schemas/community.py:275`（deadline 校验）、`services/growth_dashboard_service.py:474`（见 §3 修前面）。`orchestration/*` 大量 `created_at=int(datetime.now().timestamp())` 是 gRPC/proto int64 纪元秒（`.timestamp()` 按宿主 TZ 解释 naive 值，绝对时刻正确），非 DB 列，不参与本地图谱。

## 2. 读面普查（消费模式 × 列）

消费模式四类：① `.date()` 直切（假设列值日期=语义日）；② `time_utils.local_date()`（UTC 列→用户本地日，正确口径）；③ `wall_clock` 助手族（墙上钟列专用，297/300 后引入）；④ 裸窗口比较（端点用 utcnow/date.today 构造，直接进 SQL WHERE）。

③ 的调用面（已按列定钟的修复面，25 文件）：`api/v1/statistics.py`、`api/v1/experience_readouts.py`、`api/v1/experience/dashboard_router.py`、`api/v1/accountability.py`、`api/v1/tasks.py`、`api/v1/plans.py`、`services/focus_service.py`、`services/growth_dashboard_service.py`、`services/struggle_signal_aggregator.py`、`services/predictive_service.py`、`services/achievement_engine.py`、`services/accountability_achievement_service.py`、`services/checkpoint_nudge_service.py`、`services/analytics/*`、`state_aggregator/service.py`、`orchestration/context_builder.py`、`orchestration/discovery_manager.py`、`orchestration/phase_sketch_service.py`、`orchestration/planning_strategy_compiler.py`、`services/daily_task_selection_service.py`（部分，见 §3.2）等。

「读面假设 vs 写面实际」逐列一致性：

| 列 | 写面实际 | 读面假设 | 一致？ |
|---|---|---|---|
| `Task.completed_at` | UTC（写点全 `_utcnow`，实测在案确认） | 多数 `local_date()`（statistics:265/278、growth_dashboard、daily_task_selection:68） | ✅ 一致 |
| `StudyRecord.created_at` | UTC | `local_date`（statistics:250）或 UTC 窗（predictive） | ✅ |
| `FocusSession.start_time/end_time` | **墙上钟**（客户端本地 naive） | 分裂：正确面用 `local_midnight_wall`（focus_service:480、statistics:65、growth_dashboard:658、struggle:278、predictive:938/1110、focus_signal_processor:62）；**错误面仍按 UTC/宿主钟构造端点**（§3.1 的 5 处 LIVE） | ⚠️ 分裂 |
| `CalendarEvent.start_time/end_time` | **墙上钟** | state_aggregator 已修（297/300 CLOSED）；`api/v1/calendar.py`、`smart_schedule_service`、`calendar_service` 仍按 UTC/宿主钟（§3.1 LIVE） | ⚠️ 分裂 |
| `Plan.created_at`/`Task.created_at` | 代码=UTC，实证=墙钟（在案 FIX-314） | **两种假设并存**：① `_as_local_date`（UTC 假设）daily_task_selection:68/115；② `.date()` 直切（墙钟假设）`api/v1/plans.py:502`、`aurora/runtime_v1/service.py:1961/2708-2710`；③ UTC 裸窗 predictive:703/710、perceptible_intelligence:1062、struggle:252/361/386、guest_seed:4000；④ 纯排序面（无钟语义，安全）task_service:285/1681/1734、context_builder:1274/1446、aurora service:424、exam_sprint_intake:275/316、sprint_task_ledger:69 等 | ❌ 读面自身分裂 |
| `UserStreakStats.last_activity_date` 等 streak 列 | UTC naive（297 docstring 定界） | achievement_engine 用户本地日（293 CLOSED）；`services/streak_quality.py:22/63/148/162` 仍是 **UTC 日口径**（`_utcnow().date()`，非用户本地日） | ⚠️ 与 293 契约不一致（产品侧，见 §3.3-6） |

## 3. 错配清单（读面假设 ≠ 写面实际）

状态标注：**CLOSED** = 已修不重报（293/297/300 及 37/197/211/221/233/250 修复面，见 §2）；**在案** = V3-FIX-314 已登记、归属 wt602；**LIVE** = 本次普查新发现，建议主会话编号派卡（全部产品侧，本工位不修）。

### 3.1 新发现 LIVE 错配（按影响排序 top5）

1. **`api/v1/calendar.py:74-80`（list_events 日期过滤）** — 端点把 `start_date/end_date` 构造成 **aware UTC 日界**（`datetime.combine(d, min/max).replace(tzinfo=UTC)`）与**墙上钟列** `CalendarEvent.start_time/end_time` 比较。方向：+8（列值被当 UTC，语义前移 8h）；触发窗口：每日 16:00-24:00Z（上海 00:00-08:00）最烈，全日均有 8h 平移；影响：按日列日历错窗/漏事件；另 aware-vs-naive 比较在 asyncpg 属未定义行为面。
2. **`api/v1/calendar.py:170-188`（/calendar/summary）** — `now=datetime.now(UTC)`，`today_start/end` = **UTC 日**，比墙上钟列。方向：日界差（上海 00:00-08:00 的事件计入「昨日」、16:00-24:00 计入「明日」窗）；影响：首页「今日事件数/未来 7 天」计数错。
3. **`services/user_activity_service.py:60-83`** — `last_activity_at = max(UTC last_message_at, UTC last_task_completion_at, 墙钟 last_focus_session_at)`：**跨钟 max**，与 V3-FIX-297 修掉的 state_aggregator 同款模式新址。方向：+8（墙钟值显得比真实新 8h）；影响：用户活跃快照偏移，凡消费 `get_last_real_activity_at` 的判定（唤醒/召回/降级）在傍晚学习后延迟约 8h 才算「不活跃」。
4. **`services/north_star_wvpl_service.py:350-357`** — `occurred = coalesce(墙钟 end_time, UTC created_at)` 对 **naive-UTC 窗口** `[start,end)`（:143-146 utcnow 推导）。方向：±8 错桶 + 同表达式两钟；影响：WVPL 窗口内专注事件计数按 UTC 日错分，北极星汇报分母/分子失真。
5. **`services/idiographic_association_service.py:448-470/507-521`** — 每日行为向量：窗口端点 `_day_start(UTC 日)` naive 零点，`focus_by_day` 按**墙钟日**键控（`end_time.date()`）、`task/study_by_day` 按 **UTC 日**键控（`completed_at/created_at.date()`）。方向：同一天向量里 focus 与 task/study 键差一日（16:00-24:00Z 事件）；影响：吸引子/行为序列日粒度错位。

其余 LIVE（同族次要）：

6. `services/calendar_service.py:72-76` — `anchor = start_date or datetime.utcnow().date()`（UTC 日）构造 naive 零点窗比墙列；上海 00:00-08:00（=前日 16:00-24:00Z）时 7 天忙闲规划窗起点落在本地昨日。
7. `services/smart_schedule_service.py:49` — `target_date = request.preferred_date or date.today()`（宿主机钟，V3-FIX-233 族残留）；:135-136/:153-154/:271-272 naive 零点窗与墙列同钟自洽，仅日源错。
8. `services/streak_quality.py:22-272` — streak 质量面「今日」= `_utcnow().date()`（UTC 日），与 `achievement_engine` V3-FIX-293 已定的「连胜今日=用户本地日」契约不一致（同一 streak 语义两种日界，上海 00:00-08:00 两面各说各话）。
9. `services/guest_seed_service.py:2006/2042 vs :151` — 种子内混钟：`target_date=date.today()`（宿主日）+ `created_at=utcnow()`（UTC）；UTC 宿主 16:00-24:00Z 时种子冲刺计划的目标日与本地日网格错一天。
10. `aurora/runtime_v1/service.py:1961/2708-2710` 与 `api/v1/plans.py:502` — `plan.created_at.date()` 直切，与 daily_task_selection 的 `_as_local_date`（UTC 假设）**对同一列用两种假设**；孰对取决于 FIX-314 裁决的存储约定，随 wt602 一并收口。

### 3.2 在案（归属 wt602 / V3-FIX-314，不重报，附本次补全的消费面）

- `services/daily_task_selection_service.py:115`（`_plan_current_day` 对 plan.created_at 取 UTC 假设 local_date）与 `:68`（task.created_at 同款）——FIX-314 主修点。
- 本次补全的同列消费面（wt602 收口时需一并裁决 UTC/墙钟口径）：§3.1-10 两处 `.date()` 直切；§3.2-③ 四处 UTC 裸窗（predictive:703/710、perceptible:1062、struggle:252/361/386、guest_seed:4000——若最终裁定 created_at=墙钟存储，这些窗全错；若裁定 UTC 存储，则 `.date()` 直切两处错）。

### 3.3 CLOSED（核实过修复注记，不重报）

- V3-FIX-293：`achievement_engine.py:2034/2065`（连胜日界=用户本地日，显式 activity_date 优先）。
- V3-FIX-297：`state_aggregator/service.py:546/973` + `time_utils.wall_clock_to_utc_naive`（今日窗口同钟）。
- V3-FIX-300：`state_aggregator/service.py:518/983` + `time_utils.utc_naive_to_wall_clock`（周窗端点换墙钟）。
- V3-FIX-37/197/211/221/233/250 修复面：`api/v1/statistics.py`（37/197）、`services/struggle_signal_aggregator.py:180-182`、`services/predictive_service.py:911/1091`、`services/focus_signal_processor.py:50`、`services/growth_dashboard_service.py:508-516/664-670`、`api/v1/tasks.py:250-256/1020-1027`、`api/v1/plans.py`（233 族）、`services/exam_sprint_dashboard_service.py:58-64`、`services/task_priority_service.py:105-111`（均带注记，抽查通过）。

## 4. 测试面普查（宿主钟/UTC 日播种 = wt590 族C 同款风险面）

扫描：`backend/tests` 全量 grep `date.today()`（44 文件）∪ `utcnow().date()`（24 文件），共 **68 文件**。交叉 `monkeypatch.*utcnow / FROZEN / PushPreference / _freeze_clocks / freeze_time` 加固标记：

- **已加固（双冻结钟/钉时区族，25 文件）**：`unit/test_weekly_stats_behavior_clock_local.py`、`test_today_view_local_date_boundary.py`、`test_today_focus_task_local_day.py`、`test_task_snooze_due_date_local_day.py`、`test_task_priority_reasoning_local_today.py`、`test_struggle_today_window_local.py`、`test_streak_engine_local_day_freeze_max.py`、`test_state_aggregator_local_clock.py`、`test_planning_deadline_days_local.py`、`test_plan_replan_local_today.py`、`test_plan_day_cursor_local_today.py`、`test_plan_archive_days_ahead_local_day.py`、`test_plan_adjustment_lookahead_local.py`、`test_plan_adjustment_applier.py`、`test_phase_sketch_cursor_local_today.py`、`test_orchestrator_evolution_context.py`、`test_growth_streak_local_clock.py`、`test_exam_sprint_days_left_local.py`、`test_due_soon_days_left_local_day.py`、`test_discovery_target_date_local_today.py`、`test_dailyflow_p2_today_filter.py`、`test_daily_task_selection_local_today.py`、`api/test_task_quick_actions_api.py`、`api/test_plans_api.py`（wt559 判例区）、＋本次顺手修的 `unit/test_task_priority_service.py`。
- **残留播种面（43 文件）**，按风险分层（标注「已核」= 本工位逐点读过）：

| 文件 | 播种形状 | 一句修法 |
|---|---|---|
| `unit/test_exam_sprint_intake_service.py`（已核） | `exam_date/target_date=date.today()+7/14`（:40/:101/:186），intake 是 day 数学重灾区（FIX-314 同族读面） | 冻结 `exam_sprint_intake_service` 的 utcnow 到上海本地同日上午 + 播种按冻结日常数推导 |
| `unit/test_exam_sprint_review_service.py` | 同上族 | 同上 |
| `unit/test_exam_sprint_intake_concurrency.py` | 同上族（并发竞态窗叠加时钟） | 同上 |
| `unit/test_error_mastery_loop.py`（已核） | `target_date/due_date=utcnow().date()+N`（:156/:197）+ UTC 语义错题日 | 冻结服务钟 + 常数日播种（沿双冻结钟族） |
| `unit/test_memory_daily_summary_job.py` | `utcnow().date()` 播种汇总窗 | 冻结 job 模块钟，端点取「上海同日上午」常数 |
| `unit/test_planning_strategy_compiler.py` | `date.today()` 推导 deadline | 同双冻结钟族 |
| `unit/test_memory_conflict_resolver.py`（已核） | `target_date=date.today()`（:58/:68） | 冻结消费面钟；播种改常数 |
| `unit/test_cost_prediction_accuracy.py` | 宿主日窗 | 冻结钟 + 常数 |
| `unit/test_error_replan_bridge.py` / `_stage34.py` | `utcnow().date()` 播种 replan 窗 | 双冻结钟族 |
| `unit/consumers/test_stage34_journey_consumers.py` | 同上 | 同上 |
| `unit/test_phase_e_planning_loop.py` / `test_mirofish_wiring_finish.py` / `test_theater_seed_and_accuracy.py` / `test_card_protocol_phase4.py` / `test_card_protocol_phaseb.py` / `test_context_pack_conflicts.py` / `test_evidence_resolve.py` | `date.today()`/裸 `datetime(...)` 播种（部分经 mock 面自洽，需逐文件核） | 统一按双冻结钟族收口；自洽面（显式传参/同表达式断言）可标豁免 |
| `api/test_exam_sprint_api.py`、`api/test_task_priority_reasoning_api.py`、`api/test_task_complete_and_update_api.py`、`api/test_task_complete_galaxy_outbox.py` | API 层 `date.today()` 播种 due/target | 沿 `api/test_plans_api.py` wt559 判例（FROZEN_UTC_NOW=20:00Z + PushPreference 钉 Asia/Shanghai + 期望按 09-26 手工推导） |
| `api/test_leaderboard_self_anchor_api.py`、`api/test_insights_understanding_depth_api.py`、`api/test_insights_understanding_dimensions_api.py` | `utcnow().date()` 播种 | 同上 |
| `test_community_e2e.py`（已核） | `due_date=date.today()+N`（:541/:699/:954），断言不比日期 | 低危；顺手常数化即可 |
| `orchestration/test_planning_workflow.py`、`orchestration/test_round1_p2_fixes.py`（已核） | mock 日历/字符串日 | 低危；常数化 |
| `services/test_guest_seed_example_marker.py`、`services/test_north_star_metrics_service.py`（已核） | `date.today()` 仅作未消费种子/固定 `datetime(2026,5,1)` 断言 | 良性，豁免 |
| `services/test_exam_sprint_dashboard_service.py`（已核） | `date.today()+5` 喂给 mocked `_days_left` | 良性，豁免 |
| `aurora/test_daily_startup_message.py`（已核） | `session_day=date.today()` 显式传参自洽 | 良性，豁免 |
| `aurora/test_h6_dialogue_quality_audit.py`、`test_llm_parser.py`、`unit/test_understanding_depth_metric_service.py`、`integration/test_ltm_e2e.py`、`integration/test_phase5_orchestrator_north_star_acceptance.py`、`integration/test_stage35_error_journey_smoke.py`、`integration/test_thermodynamics_demo_scenario.py`、`northstar_eval/feature_tour.py`、`northstar_eval/real_drive.py`、`test_db_partitioning.py`/`test_context_manager.py`（裸 datetime 常数） | 播种/评估脚本面 | 逐文件复核：断言若含「同表达式重算」即自洽豁免；否则按双冻结钟族 |

风险窗统一表述：**UTC 宿主机每日 16:00-24:00Z（上海本地次日 00:00-08:00）**，播种日（宿主/UTC 日）与产品「今日」（用户本地日，缺省 Asia/Shanghai）错位一天；+8 宿主机则在 00:00-08:00 反向错位。修法判例：`tests/unit/test_dailyflow_p2_today_filter.py:84-122` 与 `api/test_plans_api.py` wt559 区（`FROZEN_UTC_NOW=2026-09-25 20:00` + 钉 Asia/Shanghai + 期望按 09-26 手工推导）。

## 5. 顺手修（机械安全项，纯测试侧）

1. `backend/tests/unit/test_task_priority_service.py` — 族C 冻结钟改造：新增 `FROZEN_NOW=2026-09-25 10:00 naive UTC`（上海同日 18:00，日界未跨）/`FROZEN_TODAY` 常数；`low_energy_aurora` fixture 内冻结 `app.services.task_priority_service.utcnow`；5 处宿主钟播种（`date.today()+3d/+5d`、`datetime.utcnow()-2h/+5min`、`due_date=date.today()`）改按冻结常数推导。语义不变（due-today/复习到期仍=「今日」），宿主机时钟/时区无关化。验证：`pytest tests/unit/test_task_priority_service.py` **6 passed**（SECRET_KEY/REDIS_URL 测试环境变量下）。

（其余候选逐一核查后判定：良性/自洽面不動，真风险面如 exam_sprint_intake 族涉及断言语义重推导，超出「机械安全」边界，留报告。）

## 6. 交主会话的派卡建议（产品侧，全部未修）

1. **calendar API 双面**（§3.1-1/2，同文件同根因，一张卡）：utcnow→用户本地日 + 端点换 `local_midnight_wall`（沿 297/300 纪律）。
2. **user_activity 跨钟 max**（§3.1-3）：`wall_clock_to_utc_naive(focus.end_time, tz)` 后再 max（297 同款，一个文件三处）。
3. **north_star_wvpl coalesce 分钟**（§3.1-4）：端点换墙钟或列值换 UTC，二选一同钟。
4. **idiographic 每日向量键控统一**（§3.1-5）：全列统一 UTC 日或墙钟日（与 statistics 的 day_key 口径对齐）。
5. **streak_quality「今日」切用户本地日**（§3.1-8）：对齐 V3-FIX-293 契约。
6. **smart_schedule/calendar_service 的宿主/UTC 日源**（§3.1-6/7）：`date.today()/utcnow().date()` → `local_date(utcnow(), tz)`（233 族收尾）。
7. **plan/task.created_at 消费面随 wt602 裁决一并收口**（§3.2）：两种读假设二归一，并修 guest_seed 混钟（§3.1-9）。

## 7. 本工位产出物

- 本报告：`v3-output/WT604-CLOCK/census.md`
- 顺手修：`backend/tests/unit/test_task_priority_service.py`（6/6 绿）
- 未动：产品代码零改动；未推远端；未编辑共享台账。
