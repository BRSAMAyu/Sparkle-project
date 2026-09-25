# WT348-HUNT-R1 — 猎缺第一轮（双轮审查·找问题轮）报告

- **worker**: wt348 ｜ **日期**: 2026-09-25 ｜ **分支**: `wt348-hunt-r1`（基于 main@b280d38a）
- **模式**: LIGHT（代码审查/静态分析/定向 sqlite pytest；未连本地 PG/Redis；未跑 flutter/浏览器/模拟器）
- **狩猎面**: ①近期合并面（dashboard/goal/task 族、mobile home/chat）②并发/一致性热点（event_bus、task_event_consumer、celery tasks）③诚实性红线（mock/demo/硬编码）④在册债定向核查
- **红线遵守**: 零产品代码改动；唯一新增文件为定向探针测试（证据件，见 D1）
- **定性**: 8 条发现（1 blocker / 3 major / 4 minor），全部经定向验证或双侧源码链取证，无「可能」态断言；另附台账验尸 4 项（2 CLOSED WITH EVIDENCE / 2 仍开放）

---

## 一、发现清单

### H1 ｜ blocker ｜ Goal.progress 唯一写入方用小写 `"completed"` 过滤，进度被恒写 0.0

- **位置**: `backend/app/services/task_event_consumer.py:262` 与 `:323`（计数条件）、`:265` 与 `:326`（写回）
- **证据**:
  - `TaskStatus` 为 StrEnum 且值全大写（`backend/app/models/task.py:47-54`，`COMPLETED = "COMPLETED"`）；列定义为 `Enum(TaskStatus)`（`models/task.py:121`），`task_service` 全部以枚举成员写入（`:198/:342/:414/:518/:715/:1047/:1237`），全仓无小写写入方（已 grep 排除，命中的 `status="completed"` 均为其它模型的字段）。
  - task_event_consumer 是 **Goal.progress 的唯一写入方**（全仓 `goal.progress =` 仅 `:265/:326` 两处），而 `Task.status == "completed"` 在大小写敏感比较下匹配不到任何行 → `completed=0` → `goal.progress = 0.0`，即每次 `task.completed`/`task.abandoned` 事件都把进度改写为 0。
  - **定向测试（可跑，已通过 2/2）**: `backend/tests/unit/test_wt348_goal_progress_caliber_probe.py::test_judgement_1_lowercase_literal_counts_zero_completed` — 同一批种子数据，枚举口径数到 1 个已完成、小写字面量口径数到 0。
  - 消费面:`backend/app/api/v1/experience/goal_router.py:287` `progress=_safe_ratio(goal.progress)` 直读 → 目标详情进度恒 0；`:314` `overall = (goal.progress …) or (plan.progress …) or 0` 被 falsy-or 掩蔽成 plan 进度（掩蔽本身另立 H6）。
  - 同文件对照组：`plan_service.py:214-216` 用 `TaskStatus.COMPLETED`（正确口径）、`api/v1/statistics.py:54/65` 用大写字面量 `"COMPLETED"`（碰巧正确）——唯 task_event_consumer 用小写。
- **建议修法**: 两处条件改 `Task.status == TaskStatus.COMPLETED`（与 plan_progress_service/goal_today_view 同口径）；修后评估是否需要一次性重算存量 Goal.progress（建议另立卡）。
- **复核要点（可证伪）**: 在任意含大写状态任务的库上跑 `select count(*) from tasks where status='completed'` → 0 而枚举口径 >0；或直接跑探针测试文件（2 用例，sqlite 内存库，~1s）。若 `lowercase_completed != 0` 则本条不成立。

### H2 ｜ major ｜ 同两处 Goal.progress 计数不过滤软删，与 10+ 读面口径冲突（家族=wt329 口径打架）

- **位置**: `backend/app/services/task_event_consumer.py:253-264、:313-325`（分子分母均无 `Task.deleted_at.is_(None)`）
- **证据**:
  - 软删在生产可达：`backend/app/orchestration/adaptive_replanner.py:885-887` 对计划内未保留、非完成任务执行 `task.soft_delete()`，而 task_event_consumer 自身即调用 AdaptiveReplanner（`:226-238`）——同一事件管线先软删任务、后续事件再把软删任务计入进度分母。
  - 读面口径对照（全部显式过滤）：`goal_today_view.py:42`、`api/v1/experience_readouts.py:274`、`api/v1/tasks.py:321`、`api/v1/experience/dashboard_router.py:168`、`api/v1/experience/goal_router.py:546`、`tools/task_query_tool.py:78/717/780`、`core/celery_tasks.py:1388/2412`、`aurora/runtime_v1/service.py:440`。
  - **定向测试（已通过）**: 探针 `test_judgement_2_soft_deleted_counted_in_numerator_and_denominator` — 软删后无过滤口径 (1,2) vs 过滤口径 (0,1)。
- **建议修法**: 两处 count 查询补 `Task.deleted_at.is_(None)`；与 H1 同卡修复成本最低。
- **复核要点**: 软删一个已完成任务后触发 `task.completed` 事件，对比 `Goal.progress` 与 goal_today_view 口径的任务集；或跑探针第二用例。若两口径相等则本条不成立。

### H3 ｜ major ｜ 台账 C-01 循环 import 仍开放：`plan_context`/`prompts`/`context_pack` 三个直接 import 入口在干净 worktree 全部炸

- **位置**: 环 = `app/core/plan_context.py` ↔ `app/orchestration/prompts.py` ↔ `app/core/context_pack.py`（台账 2026-09-19 R2-F5 登记）
- **证据**: 本 worktree（干净 checkout）实跑三条命令（SECRET_KEY 已设）：
  - `import app.core.plan_context` → `ImportError: cannot import name 'merge_plan_context' from partially initialized module`
  - `import app.orchestration.prompts` → 同型循环炸
  - `import app.core.context_pack` → 同型循环炸
  - `import app.models` 后再 `import app.core.context_pack` → OK（顺序依赖，与台账描述一致：正常入口先载 models 不触发，新脚本/Celery 入口/健康检查首 import 即炸的概率随 C-01 把 context_pack 变契约模块而上升）。
- **建议修法**: 按台账处置——打断 prompts→models 的传递依赖或延迟导入；建议作为接线卡前置项独立成卡，不应继续滞留台账。
- **复核要点**: 在干净 worktree（无预 import app.models）跑 `python -c "import app.core.context_pack"`；若 import 成功则本条不成立。

### H4 ｜ major ｜ 移动端聊天 task_list 状态 chip 大小写失配：全部状态落 default，原始英文枚举直接上屏

- **位置**: `mobile/lib/features/task/presentation/widgets/task_list_widget.dart:290-311`（`case 'pending'/'in_progress'/'completed'/…` 全小写）vs `backend/app/tools/task_query_tool.py:141-143`（`"type": task.type.value, "status": task.status.value` 全大写）
- **证据**（双侧源码链，确定性）:
  - 后端：`TaskStatus.COMPLETED.value == "COMPLETED"`（models/task.py:53），QueryPlanTasksTool 以 `widget_type="task_list"` 发射（task_query_tool.py:164-176），payload 内 status 为 `.value` 大写。
  - 移动端：`agent_message_renderer.dart:248-254` `case 'task_list'` 把 payload maps 直传 `TaskListWidget`；`task_list_widget.dart:191` `taskData['status'] as String? ?? 'pending'` 无归一化；`_buildStatusChip` 六个小写 case 全部匹配失败 → `default: label = status` → chip 显示未本地化的 `"PENDING"/"COMPLETED"/"IN_PROGRESS"…` 且颜色一律 brandPrimary；`_buildTaskIcon` 同根因（`case 'learning'` vs `"LEARNING"`）落 default 图标。
  - 对照组（非缺陷）：`plan_tools.py:316-328` 创建型 payload 不含 status 键 → 移动端 `?? 'pending'` 命中小写 case，恰好正常——这也解释了该失配为何未在主路径被肉眼发现。
- **建议修法**: 移动端 `_buildStatusChip`/`_buildTaskIcon` 入口统一 `toLowerCase()`（或改用 `TaskStatus`/`TaskType` enum + JsonValue 反序列化）；后端不改（枚举序列化规范是大写真源）。
- **复核要点**: 在 Dart 侧构造 `{'status': 'COMPLETED'}` 调 `_buildStatusChip`，断言命中 `case 'completed'`；若命中则本条不成立。或真机发一次「查询任务」工具调用看 chip 文案。

### H5 ｜ minor ｜ Goal 选择用 `scalar_one_or_none()` 但 `Goal.plan_id` 无唯一约束，多 goal 挂同一 plan 时进度静默冻结

- **位置**: `backend/app/services/task_event_consumer.py:250、:311`；schema 侧 `backend/app/models/goal.py:64`（`plan_id` 无 unique）
- **证据**: `select(Goal).where(Goal.plan_id==plan_uuid, Goal.user_id==user_id)` + `scalar_one_or_none()`——若同一 plan 出现 2+ 条 Goal（schema 允许；当前两条创建路径各建独立 plan 故未触发，但约束不在 DB 层），SQLAlchemy 抛 `MultipleResultsFound`，被 `:269/:382` 宽 `except Exception` 吞成 warning，进度静默停更。属防御深度缺口而非现行缺陷。
- **建议修法**: 改 `.limit(1)` + `scalars().first()`（或 DB 层补部分唯一索引），并对 goal 进度更新路径补一条定向测试。
- **复核要点**: 手工插入同 plan 双 Goal 后触发事件，观察日志 `Failed to update goal progress`；若进度仍更新则本条不成立。

### H6 ｜ minor ｜ goal_router 内部对「同一进度事实」存在两套相反优先级的 falsy-or 派生

- **位置**: `backend/app/api/v1/experience/goal_router.py:314`（goal 优先）vs `:608`（plan 优先）；`:314` 的 `or` 还会把合法的 `goal.progress == 0.0` 吞成 plan 进度
- **证据**: 两行原文（见上文引用）：`overall = (goal.progress …) or (plan.progress …) or 0` 与 `progress = (plan.progress …) or (goal.progress …)`。同一 payload 内 overall 与 plan_health.progress 在 `0 < plan.progress` 且 `goal.progress==0` 时会给出两个不同数字；且 `0.0` 作为合法值被 `or` 吞——goal 尚未开动（真实 0 进度）时 overall 虚高为 plan 进度。与 H1 互为掩蔽/放大关系，也是「同一事实多处派生」家族的现行实例。
- **建议修法**: 收敛为单一投影函数（显式 `None` 判空代替 `or`），两处调用点同源。
- **复核要点**: 构造 goal.progress=0.0、plan.progress=0.5 的响应，断言 `overall != plan_health.progress`（现行为）即可复现；若两值恒一致则本条不成立。

### H7 ｜ minor ｜ `statistics.py` 今日总分母无状态/软删过滤（H2 家族第二实例）

- **位置**: `backend/app/api/v1/statistics.py:71-77`（`total_tasks_today`：仅 `due_date == today`，无 status、无 deleted_at 过滤）
- **证据**: 同端点分子 `tasks_completed`（:51-56）按 `status == "COMPLETED"` 计数，分母却包含已完成/已放弃/被 replanner 软删（adaptive_replanner.py:887）的任务 → 完成率口径被稀释；对照 `goal_today_view.todays_task_condition`（SSOT，:38-44）与 `dashboard_router._efficiency_metrics`（:163-169，双过滤齐备）。
- **建议修法**: 分母补 `Task.deleted_at.is_(None)` 并明确业务口径（是否含已放弃），与 SSOT 对齐或注释声明差异理由。
- **复核要点**: 同日 1 完成 + 1 已放弃 + 1 软删，现口径 total=3、建议口径 total≤2；若 total 相等则本条不成立。

### H8 ｜ minor ｜ `event_bus.publish()` 原地变异调用方 payload（注入 `schema_version`）

- **位置**: `backend/app/core/event_bus.py:1081-1083`
- **证据**: `if "schema_version" not in payload: payload["schema_version"] = "1.0"` 直接写调用方传入的 dict。发布侧 `_serialize_stream_body` 随后有拷贝，但调用方共享/复用同一 dict（如多流发布、重试装配）时会携带被注入的键；属纯度缺口，现网无已证危害，列 minor 供第二轮裁量是否随 重构收口。
- **建议修法**: `message = {"schema_version": "1.0", **payload}` 后续全部用 `message`。
- **复核要点**: 单测：对同一 payload 连续 publish 两个不同 stream 后 `assert "schema_version" not in caller_payload`；现行为断言失败。

---

## 二、台账验尸（KNOWN_CODE_DEBT_LEDGER.md 定向核查）

| 台账条目 | 结论 | 证据 |
|---|---|---|
| P1-#1/#2 统计三仓 mock + mock 入 Isar 暖缓存 | **CLOSED WITH EVIDENCE** | `agent_statistics_provider.dart:96-115` 已接真实 `GET /agent-stats/user/overview`（注释明示 D-04：无客户端兜底、降级聚合抛 `StatisticsSourceUnavailableException`）；`hybrid_statistics_repository.dart:135` 有一次性 legacy mock 暖缓存清洗；三 provider 文件 grep `mock/0.95/fake` 零命中 |
| P1-#3 leaderboard | 台账已自记销账（D-COMM-4），本轮未重查（有 COMM-LB 守卫固化，低风险） | — |
| B-06（2026-09-19 补登记）is_pro=flame_level>=3 双路派生 | **CLOSED WITH EVIDENCE** | `user_service.py:206-212` 已改 `entitlement_effective_grants_pro`（注释 V3-FIX-02/D17/O-04）；网关 `user_context.go:69` 注释「entitlement 是唯一权益判据」+ `chat_orchestrator_helpers_test.go:318-334` 反证测试（flame_level=15 无 entitlement → is_pro=false） |
| C-01（2026-09-19 补登记）plan_context↔prompts 循环 import | **仍开放，升格为 H3** | 干净 worktree 三入口实跑全炸（证据见 H3）；台账预定的 import 拓扑整理未执行 |
| P2-#4 card_protocol mid-flight | **仍开放** | `card_protocol/consistency_validator.py` 仍不存在（CARD-DUAL-WRITE 规则维持停用）；`legacy_adapter.py` 36 处 / `card_operations_service.py` 35 处 legacy 标记与登记密度相当 |

## 三、诚实性红线扫描结论（面 ③）

- `kDebugMode` 全部命中为日志/超时/资源类门控，无 wt328 同族 mock 数据回落（F-1 切除后无复发；`api_constants.dart` 等均为合理 debug-only 行为）。
- `DemoDataService.isDemoMode` 默认 false（`demo_data_service.dart:135`），唯一赋值入口为编译期常量 `bool.fromEnvironment('DEMO_MODE')`（`main.dart:127-128`）+ demo 会话恢复路径，home/dashboard/chat 各 repository 的 demo 分支均有门控——**无未门控 mock 可达生产路径**。
- 未发现硬编码文案冒充真实指标的新实例；`dashboard_service._calculate_weather` 的中文 condition 为既有后端文案设计（insight_copy 同族），未列缺陷。

## 四、并发/一致性热点结论（面 ②）

- `event_bus.py`：connect 吞错→显式 RuntimeError（wt333 修法在场）；消费循环防御/自动重启/DLQ 先落库后 ack/幂等键 (stream,group,effective_id) 均闭环；`_requeue_for_retry` 的 backoff 旋钮未接线是代码内自述已知项（:706-714 R2-EI-15），不重复列缺陷。唯一新增=H8。
- `task_event_consumer.py`：fan-out 隔离（_safe_run + gather return_exceptions）与外层 raise→总线重试契约成立；发现即 H1/H2/H5。
- `backend/app/tasks/*`（10 个 celery beat 任务）：错误路径均 logger+返回 error 状态，无 wt333 同族吞错形态（`accountability_tasks._user_timezone_name` 的 Asia/Shanghai 静默默认为产品级缺省，有 ZoneInfo 校验，未列缺陷）。

## 五、近期合并面结论（面 ①）

- mobile home：wt329 F-9 账本口径落地后，`tasksTotal/tasksCompleted` 旧口径仅存于 experience 快照消费面（`growth_quality_card.dart:98`，日窗 streak 语义，非账本打架）；未发现新残影。
- backend goal 族：goal_today_view SSOT 判定唯一（除 H7 statistics 分母与 H6 goal_router 投影外，无各自再写判定的第四处）。
- wt335 F-7：写侧 resolve_goal_space_id 单收口 + 读侧 users.py 投影自愈在位；mobile `active_goal_provider.dart:117` 的 plan 伪 goal 选择仍会上送 plan id，由后端纠偏吸收（防御在位，未列缺陷）。

## 六、交付物

| 件 | 路径 |
|---|---|
| 本报告 | `v3-output/WT348-HUNT-R1/REPORT.md` |
| 定向探针测试（证据件，2 用例全绿） | `backend/tests/unit/test_wt348_goal_progress_caliber_probe.py` |
| 全量 diff | `v3-output/WT348-HUNT-R1/changes.patch` |
| 复跑命令 | `cd backend && SECRET_KEY=… pytest tests/unit/test_wt348_goal_progress_caliber_probe.py -q` ｜ `python -c "import app.core.context_pack"`（干净进程，预期炸） |

## 七、未覆盖面声明（诚实边界）

- 未运行 flutter test/模拟器/浏览器；H4 为双侧源码链取证，未做真机复现。
- 未连接本地 PG/Redis；H1/H2 的 SQL 层行为以 sqlite 探针证实（列类型 Enum 持久化值与 PG 一致，均为枚举成员名=值 "COMPLETED"）。
- 台账 P3 gateway lint 基线、P2-#5/#6 全仓 legacy 密度图未逐条重查（超出本轮定向范围）。
- mobile group_chat_screen（wt339 新改）仅做静态抽检，其 remap 逻辑有新配测试覆盖，未深审。
