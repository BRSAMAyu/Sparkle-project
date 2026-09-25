# WT355-HUNT-R2 — 猎缺第二轮（独立复核）报告

- **worker**: wt355 ｜ **日期**: 2026-09-25 ｜ **分支**: `wt355-hunt-r2`（基于 main@4cb23b53）
- **被复核对象**: `v3-output/WT348-HUNT-R1/REPORT.md` H1-H8（第一轮基于 main@b280d38a；本轮行号在当前 main 上重新标定）
- **模式**: LIGHT（只读分析 + 可跑 sqlite/单元探针 + 干净进程 import 探针；未连 PG/Redis；未跑 flutter/模拟器/浏览器）
- **独立性声明**: 全部行号、枚举值、调用链、schema 类型均在本 worktree 亲验（读原文/grep/实跑），未采信第一轮转述；探针测试为本轮独立编写（`backend/tests/unit/test_wt355_hunt_r2_review_probe.py`，4 用例全绿），第一轮探针也在本 worktree 独立复跑通过（2/2）。
- **红线遵守**: 零产品代码改动；唯一新增代码文件为上述复核探针测试。

---

## 一、裁定总表

| # | 第一轮定性 | **R2 裁定** | 一句话理由 |
|---|---|---|---|
| H1 | blocker | **确认（维持 blocker），机制描述精化** | 唯一写入方口径失配实锤；但生产 PG 上是「查询报错被吞、不写入」而非「数到 0 后写 0.0」——用户可见结局相同（进度恒 0.0） |
| H2 | major | **确认（维持 major）** | 软删链路亲验成立，且因果比第一轮更紧：**同一事件内**先软删后计数 |
| H3 | major | **确认（维持 major）** | 本 worktree 干净进程三入口循环 import 全炸（独立复现） |
| H4 | major | **确认（维持 major）** | 双侧链亲验成立；小勘误：chip 是 5 个小写 case 而非 6 个，且 paused/stuck 连小写 case 都没有 |
| H5 | minor | **确认（维持 minor，防御深度）** | 现行两条创建路径均新建 Plan（1:1），多 goal 不可达，不升级 |
| H6 | minor | **确认（维持 minor）** | goal_router:314（goal 优先）vs :608（plan 优先）原文亲读属实 |
| H7 | minor | **确认（维持 minor），补充窗口错位面** | 分母仅 due_date 过滤属实；分子分母还分属 completed_at / due_date 两个不同时间轴 |
| H8 | minor | **确认（维持 minor）** | event_bus.py:1081-1082 原文亲读属实；现网调用方每次新建 dict，危害未证实，不升级 |

**总计：8/8 确认，0 推翻、0 升级、0 降级；另补 1 条第一轮漏报（S1, minor）。**

---

## 二、逐条复核证据（与第一轮证据独立）

### H1 ｜ blocker ｜ 确认，机制精化

**亲验事实链（全部本 worktree 现场取证）：**

1. **写入方唯一性（全仓 grep）**：`goal.progress =` 全仓仅 `task_event_consumer.py:265` 与 `:326` 两处；无 `update(Goal)` 原生写入口。`Goal.progress` 列默认 `0.0`（`models/goal.py:49`）。两条 Goal 创建路径均不设 progress（`api/v1/goals.py` 向导 :198-210 只建 Plan 并挂接；`goal_decomposition_service.py:158` 的 `Goal(...)` 无 progress 参数）；`community_feedback_service.py:8/:206` 注释明示永不改 Goal.progress。**→ 不存在任何可补救的其他写入口径。**
2. **枚举与列类型**：`TaskStatus(enum.StrEnum)` 成员名与值全大写（`models/task.py:46-54`）；`status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), ...)`（:121）——原生 `Enum(TaskStatus)`（同文件 :89-93 的 `_string_enum`/`native_enum=False` 辅助只用于其他列）。**生产 schema 快照实锤**：`backend/gateway/internal/db/schema.sql:528-536` `CREATE TYPE taskstatus AS ENUM ('PENDING','IN_PROGRESS','COMPLETED','ABANDONED','STUCK','PAUSED','RESTORE')`，`tasks.status` 列类型 `taskstatus`（:5951 附近）。持久化值=大写成员名（本仓 SQLAlchemy 2.0.48 `Enum._valid_lookup` 实测：`TaskStatus.COMPLETED → 'COMPLETED'`）。
3. **消费者口径**：`:262` 与 `:323` `Task.status == "completed"`（小写字面量）亲读属实。
4. **机制精化（R2 增量，有探针固化）**：SQLAlchemy 2.0.48 对**未知小写串**的 bind 处理是原样透传到 SQL 层、不报客户端错（探针 `test_r2_e1_lowercase_unknown_string_is_passed_through_and_persisted_value_is_uppercase` 实测 `_db_value_for_elem("completed") == "completed"`）。因此：
   - **生产 PG**：生成 `WHERE status = 'completed'`，原生枚举 `taskstatus` 无此标签 → PG 抛 `22P02 invalid input value for enum taskstatus: "completed"` → 计数查询抛错 → 被 `:270`/`:335` 的 `except Exception` 吞成 warning → **整个写入不发生**。叠加列默认 0.0 + 唯一写入方失效 → 生产结局 = **进度冻结于 0.0**。可证伪预测：生产日志应能检索到 `Failed to update goal progress`（含 invalid input value for enum taskstatus）。
   - **sqlite/测试环境**：VARCHAR 比较返回 0 行 → `completed=0` → 字面写 0.0（探针 `test_r2_e2_consumer_shaped_query_writes_zero_progress`：消费者形状查询 (0,2) → progress=0.0）。
   - **第一轮「恒写 0.0」的用户可见结论正确**，机制描述在 PG 上需按上述精化（对修复验收有影响：修后 PG 上该 warning 应消失，而不是看进度值变化）。
5. **用户实际看到的数字（掩蔽条件标定）**：
   - `goal_router.py:287` `progress=_safe_ratio(goal.progress)`：goal 详情恒 **0.0**。
   - `goal_router.py:314` `overall = _clamp_unit((goal.progress if goal else None) or (plan.progress if plan else None) or 0)`：`goal.progress=0.0` 为 falsy → **overall 显示 plan.progress**（`plan_service.py:218-219` 用枚举成员口径、数值正确且通常非零）；`:608` 同理。→ **只要 plan.progress 非零，用户在 overall/plan_health 看到的是 plan 进度（掩蔽）；goal 详情看 0（暴露）；两处数字不一致。** 仅当 plan.progress 也为 0/None 时整体显示 0。
6. **修法方向**：确认正确——两处条件改 `Task.status == TaskStatus.COMPLETED`（与 `plan_service.py:218`、`plan_progress_service.py:295` 同口径，成员 bind 到 'COMPLETED' 标签，PG/sqlite 双端正确）；存量重算另立卡（当前存量全是 0.0，修后首个事件即自愈当前 plan，历史 plan 需一次性重算或接受惰性收敛）。

### H2 ｜ major ｜ 确认

- 消费者两处 count（`:256-264`/`:318-325`）无 `Task.deleted_at.is_(None)` 亲读属实。
- **因果比第一轮更紧（R2 增量）**：`_handle_task_completed` 在 **同一事件内**先调 AdaptiveReplanner（`:228-238`，其内 `adaptive_replanner.py:885-887` `task.soft_delete()` 后 commit），随后 `:241` 起独立 session 做无过滤计数——不需要「后续事件」，单事件即先删后数。生产入口实锤：`task_service.py:864/:1310` 发布 `task.completed`/`task.abandoned`。
- SSOT 对照亲读：`goal_today_view.py:38-44` 显式 `Task.deleted_at.is_(None)`。
- 探针（第一轮判据二）在本 worktree 复跑通过；我的 `test_r2_e2_fixed_caliber_yields_correct_progress` 独立给出修复口径 (1,2)→0.5。
- 修法（补软删过滤，与 H1 同卡）正确。

### H3 ｜ major ｜ 确认

- 本 worktree（干净 checkout）实跑：`import app.core.plan_context` / `import app.orchestration.prompts` / `import app.core.context_pack` 三个干净进程**全部**循环 import 炸（`prompts.py:44 from app.core.plan_context import merge_plan_context` → partially initialized module）；`import app.models` 预载后 OK。与台账 C-01 判定一致，证据独立复现。
- 修法方向正确：打断环或延迟导入，作为接线卡前置项独立成卡，不再滞留台账。

### H4 ｜ major ｜ 确认（附小勘误）

- 后端：`task_query_tool.py:141-143` `"type": task.type.value, "status": task.status.value` 大写、`widget_type="task_list"`（:164-176）亲读；**生产可达实锤**：`agents/standard_workflow.py:2848` 注册 `query_plan_tasks`，`orchestration/prompts.py:438-445` 将「我还有什么任务」等真实用户问题路由到该工具。
- 移动端：`agent_message_renderer.dart:248` `case 'task_list'` 直传 payload maps；`task_list_widget.dart:191-192` `taskData['status'] as String? ?? 'pending'` 无归一化；`_buildStatusChip`（:289-311）case 全小写 → 大写串全部落 `default: label = status`（原始枚举上屏、颜色一律 brandPrimary）；`_buildTaskIcon`（:260-286）同根因落 default 图标。
- **小勘误（不影响结论）**：status chip 实为 **5 个**小写 case（pending/in_progress/completed/abandoned/restore），非 6 个；且 `TaskStatus` 7 成员中 **PAUSED/STUCK 连小写 case 都没有**——即使只修大小写，这两态仍落 default。修卡应一并补齐。
- 对照组亲读属实：`plan_tools.py:316-328` 创建型 payload 无 status 键 → `?? 'pending'` 命中小写 case，恰好正常（解释为何主路径未肉眼发现）。
- 修法方向正确：移动端入口归一化（或 enum 反序列化）；后端 `.value` 大写是既定线上格式，不改。

### H5 ｜ minor ｜ 确认（维持防御深度，不升级）

- `:250`/`:311` `scalar_one_or_none()`、`:270`/`:335` 宽 `except` 吞成 warning、`models/goal.py:64` `plan_id` 无 unique 均亲验属实。
- **可达性核查（R2 增量）**：两条 Goal 创建路径均**新建 Plan** 配对（`goals.py:198-210`；`goal_decomposition_service.py:158` 一带），现行 1 goal : 1 plan 成立，多 goal 挂同一 plan 经现有 API 不可达 → 维持 minor 防御深度定性。
- 修法（`.limit(1)` + `scalars().first()` 或 DB 部分唯一索引 + 定向测试）合理。

### H6 ｜ minor ｜ 确认

- `goal_router.py:314`（goal 优先）vs `:608`（plan 优先）两行原文亲读；`or` 吞合法 `0.0` 实锤（与 H1 联动：H1 存续期间 overall=plan 进度、goal 详情=0，同屏两数）。
- 修法（收敛单一投影函数、显式 None 判空）正确。

### H7 ｜ minor ｜ 确认（补充窗口错位面）

- `statistics.py` 亲读：分子 `tasks_completed`（:51-56，`status == "COMPLETED"` + `completed_at >= today_start`）、分母 `total_tasks_today`（:71-77，仅 `due_date == today_start.date()`，无 status、无 deleted_at）——第一轮事实全部成立；对照组 `goal_today_view.py:38-44` SSOT 双过滤齐备。
- **R2 增量**：分子分母还分属 **completed_at / due_date 两条时间轴**——今日完成但逾期到期的任务计入分子不计入分母；今日到期、明日完成的任务在完成前长期占分母。修法除补软删过滤外，应显式声明口径（含不含已放弃/逾期），否则「完成率」仍不可解释。维持 minor。

### H8 ｜ minor ｜ 确认

- `event_bus.py:1081-1082` 原文亲读：`if "schema_version" not in payload: payload["schema_version"] = "1.0"` 原地写调用方 dict。
- 危害评估：现网主要调用方（如 `task_service.py:864/:1310` `event.to_dict()`）每次构造新 dict，共享/复用同一 payload 发布多流的实害未证实 → **维持 minor，不升级**。修法（`{"schema_version": "1.0", **payload}`）正确，成本低可随重构收口。

---

## 三、补充发现（第一轮漏报，≤2 条，取 1 条）

### S1 ｜ minor ｜ `PlanService.update_progress` 兜底路径分子分母均不过滤软删（H2 家族、另一写方）

- **位置**: `backend/app/services/plan_service.py:215-219`（`total_query = select(func.count(Task.id)).where(Task.plan_id == plan_id)` 与 `completed_query` 均无 `deleted_at` 过滤，:236 写回 `plan.progress`）
- **可达性**: `execution_ingestor.py:639/:711`、`execution_service.py:3142` 生产调用。主路径 `PhaseService.sync_legacy_plan_progress`（:187-193）走 card_protocol 生命周期口径；仅当其异常回退（:199 warning "Weighted phase progress fallback ... failed"）才落到此 count——故为条件路径，定性 minor。
- **可证伪**: 构造含软删任务的 plan 强制走兜底分支，比对 progress 与过滤口径；若相等则不成立。
- **修法**: 兜底两查询补 `Task.deleted_at.is_(None)`，与 H2 同口径。

---

## 四、可派发卡面（按复核结论组合）

> 通用 Forbidden（全部卡适用）：不改 proto/生成代码与 SQLC 产物；DB 变更只走 Alembic；不删既有断言换全绿；不动认证授权；Mock 不冒充真实结果。

### 卡 R2-A（major·blocker 收口）｜ task_event_consumer Goal 进度口径修复（H1+H2 同文件并卡）

- **路径种子**: `backend/app/services/task_event_consumer.py:256-264、:265、:318-326`；对照 `app/services/plan_service.py:218`、`app/services/plan_progress_service.py:295`、`app/services/goal_today_view.py:38-44`
- **改动**: ① `:262`/`:323` 改 `Task.status == TaskStatus.COMPLETED`；② 两处 count 补 `Task.deleted_at.is_(None)`；③ Goal 查找（`:250`/`:311`）改 `.limit(1)` + `scalars().first()`（顺带消 H5 的 MultipleResultsFound 面，不强制 DB 索引）
- **红测要求**: 扩展 `backend/tests/unit/test_wt355_goal_progress_caliber_probe.py` 或新建：同一批种子（1 COMPLETED + 1 PENDING + 1 软删 COMPLETED）下，修复口径 (1,2)→progress 0.5；小写串形状用例保留为回归证明
- **验收**: a) 新红测绿；b) `pytest backend/tests/unit -q` 相关面无回归；c) PG 语义注记：修后生产日志不再出现 `Failed to update goal progress: ... invalid input value for enum taskstatus`（发布说明中列为人肉验证项）；d) 一次性重算存量 Goal.progress 另立卡（当前存量恒 0.0 的证据见 R2 报告 H1 节）
- **Forbidden**: 不改 `models/task.py` 枚举定义；不改 schema.sql（快照）；不动事件契约字段

### 卡 R2-B（major）｜ 打断 plan_context↔prompts↔context_pack 循环 import（台账 C-01 升格，H3）

- **路径种子**: `backend/app/core/plan_context.py`、`backend/app/orchestration/prompts.py:44`、`backend/app/core/context_pack.py`（环拓扑见台账 2026-09-19 R2-F5）
- **改动**: 延迟导入或下沉共享函数打断 prompts→plan_context 环；不改变任何函数行为
- **红测要求**: 新增 import 冒烟测试（`pytest` 收集一个 test 模块，在测试进程内 `import app.core.context_pack` 必须成功——测试进程未预载 app.models 时等效干净入口；若 conftest 已预载 models，则用 `subprocess` 干净进程跑 `python -c "import app.core.context_pack"` 断言 exit 0）
- **验收**: 三个入口在干净进程 import 成功（对照本报告 H3 节复现命令）；台账 C-01 置 CLOSED WITH EVIDENCE
- **Forbidden**: 不用 try/except 包 ImportError 掩盖；不移动公开 API 签名

### 卡 R2-C（major）｜ mobile task_list 状态/类型 chip 归一化（H4）

- **路径种子**: `mobile/lib/features/task/presentation/widgets/task_list_widget.dart:191-192、:260-286、:289-311`；后端格式真源 `backend/app/tools/task_query_tool.py:141-143`
- **改动**: chip/icon 入口统一 `toLowerCase()` 归一化；**补齐 PAUSED/STUCK 两态文案与颜色**（现即使小写也无 case）；文案走 l10n
- **红测要求**: flutter test（在允许跑 flutter 的机器执行）：构造 `{'status': 'COMPLETED', 'type': 'LEARNING'}` 渲染 TaskListWidget，断言命中 completed 样式（success 色 + l10n 文案）而非 default；paused/stuck 各一例
- **验收**: 真机/模拟器发一次「我还有什么任务」工具调用，chip 显示本地化文案（放 HUMAN_INBOX 验证项）
- **Forbidden**: 不改后端 `.value` 大写线上格式；不改 `agent_message_renderer.dart` 分发协议

### 卡 R2-D（minor）｜ goal_router 进度投影单一化（H6）

- **路径种子**: `backend/app/api/v1/experience/goal_router.py:314、:608`
- **改动**: 抽单一投影函数（显式 `is not None` 判空代替 `or`），两处同源；明确 goal/plan 优先级并注释依据
- **红测要求**: 单测：goal.progress=0.0、plan.progress=0.5 时 overall 与 plan_health.phase_health 同源一致；goal.progress=None 回退 plan
- **验收**: 相关 endpoint 测试绿；无响应形状变更（值语义变化需在卡内记录 before/after）
- **Forbidden**: 不改 payload schema 字段名

### 卡 R2-E（minor）｜ statistics 今日完成口径对齐（H7，含窗口声明）

- **路径种子**: `backend/app/api/v1/statistics.py:49-77`；SSOT `backend/app/services/goal_today_view.py:38-44`
- **改动**: 分母补 `Task.deleted_at.is_(None)`；显式声明是否含已放弃/逾期（若对齐 SSOT 活跃态口径需一并过滤 status，二选一写注释）；分子分母时间轴统一或注释声明差异理由
- **红测要求**: 单测：同日 1 完成 + 1 已放弃 + 1 软删 + 1 逾期完成，断言分母按声明口径计数
- **验收**: 端点测试绿；口径决策在卡内留痕（若需产品决策先过澄清）
- **Forbidden**: 不改响应字段

### 卡 R2-F（low，可并入 R2-A/E 顺手做）｜ event_bus publish 纯度 + update_progress 兜底软删过滤（H8 + S1）

- **路径种子**: `backend/app/core/event_bus.py:1081-1082`；`backend/app/services/plan_service.py:215-219`
- **改动**: `message = {"schema_version": "1.0", **payload}` 后续用 `message`；plan_service 兜底两查询补 `deleted_at.is_(None)`
- **红测要求**: H8——同 payload 连发两个 stream 后断言调用方 dict 无 `schema_version`；S1——软删任务不计入兜底分子分母
- **验收**: 相关单测绿
- **Forbidden**: 不改事件 wire 格式（schema_version 值仍 "1.0"）

---

## 五、交付物与复现命令

| 件 | 路径 |
|---|---|
| 本报告 | `v3-output/WT355-HUNT-R2/REPORT.md` |
| R2 复核探针（4 用例全绿） | `backend/tests/unit/test_wt355_hunt_r2_review_probe.py` |
| 全量 diff | `v3-output/WT355-HUNT-R2/changes.patch` |
| 探针复跑 | `cd backend && SECRET_KEY=… pytest tests/unit/test_wt355_hunt_r2_review_probe.py tests/unit/test_wt348_goal_progress_caliber_probe.py -q`（6 passed） |
| H3 复现 | `cd backend && SECRET_KEY=… python -c "import app.core.context_pack"`（干净进程，预期 ImportError） |

## 六、诚实边界

- 未连 PG/Redis：H1 的 PG 22P02 行为由「schema 快照列类型 + SQLAlchemy 2.0.48 bind 透传实测 + PG 枚举输入解析语义」三段链推证，未在真 PG 上执行（红线禁止）；发布验证项已列入卡 R2-A 验收 c)。
- H4 未做真机复现（红线禁 flutter/模拟器），双侧源码链 + 工具注册面取证。
- 第一轮台账验尸 4 项（P1-#1/#2/#3、B-06、card_protocol）本轮未重复核查——其证据为文件级事实，第一轮已给位置，风险低；C-01 已通过 H3 独立复现覆盖。
- 行号以 main@4cb23b53 为准；第一轮报告的 goal_router:314/:608、:287 在当前 main 上逐一核对无漂移，consumer 的吞异常行号 :270/:335（第一轮写 :269/:382，:382 疑为笔误，无实质影响）。
