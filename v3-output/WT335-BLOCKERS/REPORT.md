# WT335 · 后端 blocker 簇 F-7 / F-6 / F-5 — REPORT（wt324 实测三 major 原卡面重派）

> 2026-09-25 · 分支 `wt335-backend-blockers`（自 main 24f2a245）· LIGHT（backend 代码 + 定向 pytest）
> 缺陷证据源：v3-output/WT324-SIMEVIDENCE/REPORT.md §四

---

## 一、F-7（major·阻断验收）：多目标看板→目标详情 404

### 根因（两端合谋，非单点）

**写侧（错数据来源）**：mobile `multi_goal_dashboard_provider`（active_goal_provider.dart）
的 multi-goal 概览在 spine 目标缺失/未同步时走 plan 回退快照，
`ActiveGoalSnapshot.fromPlan` 用 **plan.id 冒充 goal id**（fromPlan 构造 `id: plan.id`），
`resolvedSelectedGoalId` 兜底 `goals.first.id`（回退态=plan.id），经
`selectGoal → PUT /users/me {current_goal_id}` 把 plan_id 写进 settings。
后端写入口（users.py / user_settings.py → `UserSettingsService.update_settings`）
对 current_goal_id **零校验**，plan_id 原样落库——与 wt324 logcat 证据吻合
（settings 返回 current_goal_id: ef026203-… 即 plan_id，请求
/experience/goal-detail/ef026203-… 即 404）。

**读侧（404 触发面）**：`_resolve_goal`（goal_router.py）解析 UUID 后精确查 Goal，
查无 → 404；app 错误页「目标详情加载失败」重试不复权（id 本身错，重试必然再 404）。

### 修法（按卡面两分支都做，均在 Python 侧）

1. **激活链存真正的 goal_id（写侧纠偏）**：`UserSettingsService.update_settings`
   对 `current_goal_id` 统一过新方法 `resolve_goal_space_id`：命中本人 Goal → 原样；
   命中本人 Plan → 纠偏为该 plan 的 goal_id（plan 未挂 goal → None，诚实空态优于
   必然 404 的 id）；其余原样透传（不吞悬空值——可能来自写读竞态，纠偏职责止于
   「plan→goal」这一确证形态）。**单一收口点**：users.py PUT /me 与 user_settings.py
   POST/PUT settings 都经 service.update_settings，一处修全链生效。
2. **存量错数据读取侧修复路径（二选一之「读取时校验纠偏」，不改库）**：
   `resolve_goal_space_id` 同函数用于读侧投影——GET /users/me（`_build_user_profile`
   改 async 并注入 db 做纠偏，5 个调用点统一）、GET/POST/PUT /user/settings 响应。
   **选读取纠偏而非迁移脚本的理由**：a) 不写库=零迁移风险、可回退（撤代码即回原状）；
   b) 错误形态可确证（id 命中本人 Plan 表），误纠概率趋零；c) 迁移脚本对「纠偏后
   app 本地缓存（PersistentNotifier active_goal 命名空间）」无能为力——app 下一次
   fetchUserSettings 即被读侧自愈纠正并经 hydrateFromRemote 收敛本地态，迁移脚本做不到。

**app 侧 404 文案分支（卡面标注可选）**：不做。理由：读侧自愈已根治 404 源头；
该文案文件属 wt336 mobile 战区，避免抢地盘，记为可选遗留。

### 红测→绿

`backend/tests/api/test_current_goal_id_goal_space.py` 9 例（写侧纠偏×2、真 goal 不动、
清空 None、读侧自愈+不回写库断言、me 读纠偏、goal id/悬空值透传、
goal-detail 200 端到端、plan_id 直连仍 404（404 语义不放宽））。
修复前跑：写侧 2 例红（plan_id 原样落库复现）；修复后 9/9 绿。

---

## 二、F-6（major）：chat_mode=growth 全链静默死

### 裁决（卡面要求先答）：growth **不是**后端引擎真实支持的 mode

- `backend/app/orchestration/chat_modes.py`：`SUPPORTED_CHAT_MODES = {standard,
  deep_analysis, study_plan, error_diagnosis, expert_auto}` + `expert::`/`team::` 前缀；
  `normalize_chat_mode('growth')` → standard（"Unknown modes fallback for compatibility"）。
- `mode_workflow_config.py` mode 策略表无 growth 条目；gateway 无 growth mode 处理。

→ 按卡面走「调用侧改用语义最近的既有 mode，删死字符串」分支。

### 语义选择及理由：deep_analysis

调用场景=「我卡住了」/瓶颈对话（cockpit stalled 与 dashboard bottleneck CTA），
prompt 语义是"我在 X 上卡住了/帮我突破"。逐候选取舍：standard=即 wt324 实测的缺陷
落地形态（"均衡·标准对话"，形同虚设），排除；study_plan 偏"制定新计划"，而卡住用户
要的是突破当前障碍非另起计划；expert_auto 触发专家自动路由，行为面变更过大；
error_diagnosis 限错题诊断。**deep_analysis（深度分析+langgraph 执行偏置）与
"诊断并分析当前瓶颈、怎么破"语义距离最近**。

### 改动（最小，两处单行+注释）

- `today_cockpit_card.dart` `_openStuckChat`：'growth' → 'deep_analysis'
- `dashboard_screen.dart` `_openBottleneckChat`：'growth' → 'deep_analysis'
- routes.dart:348 透传**不改**（透传任意值本身无错，后端静默回落是兜底契约）；
  chat_mode.dart:71 orElse 静默回落**不改**（与后端 normalize_chat_mode 兼容回落
  双向一致——测试固化该契约，防一侧单方面改抛错）。

### 红测（执行 DEFERRED，代码照常完成）

`mobile/test/features/chat/data/models/chat_mode_contract_test.dart` 4 例：
mobile 枚举与后端 SUPPORTED_CHAT_MODES 逐值对齐、home 源码死字符串守卫
（修复前必红）、deep_analysis 精确解析、未知值回落 standard 契约文档化。
**DEFERRED 证据**：`sysctl vm.swapusage` = free 931.69M < 1.2G 门禁（两次实测同值），
按 HANDOVER §4.3 跳过执行；修复对 backend 侧另加的间接验证：backend modes
契约由后端测试天然覆盖，且 mobile 侧后补跑仅需 `flutter test
test/features/chat/data/models/chat_mode_contract_test.dart --concurrency=1`。

---

## 三、F-5（major）：瓶颈误报——刚完成任务立即成为卡点

### 根因

`GrowthDashboardService._get_weakest_area` 仅按 `UserNodeStatus.mastery_score`
升序取最低知识节点，**无任何 completed 态/时间维度排除**。任务「Readiness check」
完成后其关联节点（`Task.knowledge_node_id`）掌握度仍低即被指认为 weakest area →
`_build_active_bottleneck` 立即产出 `topic="Readiness check"` 的
active_bottleneck（severity=high）→ mobile
`/growth/dashboard.active_bottleneck → homeGrowthStateProvider.activeBottleneck →
cockpit bottleneckTopic` 转 stalled，掩盖刚产出的 active 完成态（wt306 风险4 成真）。

### 修法（时间窗判定）及与现有推导一致性的理由

`_get_weakest_area` 排除「`BOTTLENECK_RECENT_COMPLETION_WINDOW_HOURS`（24h）
窗口内有关联 Task（status=COMPLETED）完成」的知识节点。**选时间窗而非永久排除
completed 态的理由**：a) 任务完成后掌握度未必抬升，节点可能仍是真瓶颈——永久排除
会让瓶颈发现能力永久失明；时间窗只抑制「刚完成就指认」这一确证误报形态，到期自然
复权，无需迁移；b) 同文件已有 LOOKBACK_DAYS=7 / TTL 秒数式窗口推导先例，时间窗
与其同风格。窗口全部覆盖所有节点时返回 None（诚实空态优于指认刚处理过的节点，
cockpit 不会 stalled）。daily context line 的 bottleneck（同函数第二消费点）一并受益。

### 红测→绿

`backend/tests/unit/test_growth_bottleneck_recent_completion.py` 5 例：
刚完成即不指认（修复前红：复现 'Readiness check' 被指认）、未完成节点照常指认、
窗口外完成复权、全窗口覆盖→诚实 None、pending/进行中任务不触发排除。
修复后 5/5 绿。

---

## 四、验收清单（逐项）

| 项 | 结果 |
|---|---|
| F-7 红测→绿 | 9/9（修复前 2 红复现） |
| F-6 红测 | 文件交付；执行 DEFERRED（swap 931.69M<1.2G，两次实测） |
| F-5 红测→绿 | 5/5（修复前 2 红复现） |
| 受影响 service 定向 pytest | 34 passed（growth dashboard/growth api/context line/ai_ops/equipment）+ 19 passed（guest ttl/f821）+ 43 passed（goal today view/experience 系，其中 1 例既有失败见下） |
| 既有失败（非本卡引入） | `test_goal_today_view.py::test_surface_queries_both_filter_by_ssot_condition` 在主仓 main 同样复现（日期敏感：期望 TODAY 得 09-24），本卡未触碰 goal_today_view 链路 |
| ruff 被碰文件 | 6 文件（4 app + 2 test）All checks passed |
| 冷缓存 mypy | `rm -rf .mypy_cache` 后 1449 = quality/mypy_baseline.txt 基线，零推高 |
| 治理守卫 | `bash scripts/run_all_rule_guards.sh` exit 0（83 rules，补拷 gateway/mobile gen 后） |
| gen 三件套 | app/gateway/mobile 均 `cp -RL` 自主仓（-L 解引用） |

## 五、改动面（6 改 + 3 新，全部最小化）

- `backend/app/services/user_settings_service.py`：update_settings 写侧纠偏 + 新增 `resolve_goal_space_id`
- `backend/app/api/v1/users.py`：`_build_user_profile` 改 async 注入纠偏（5 调用点）
- `backend/app/api/v1/user_settings.py`：GET/POST/PUT settings 读侧投影纠偏
- `backend/app/services/growth_dashboard_service.py`：`_get_weakest_area` 时间窗排除 + 常量
- `mobile/.../today_cockpit_card.dart`、`dashboard_screen.dart`：'growth'→'deep_analysis'
- 新增测试 3 文件（见上）

## 六、交接 / 遗留

1. F-6 mobile 契约测试待跑（合并后任一 mobile 会话补跑即可，命令见 §二）。
2. F-7 app 侧 404 文案分支（可选）未做，留 wt336/mobile owner。
3. 存量错数据以读侧自愈方式兜底，无迁移脚本；如未来要落库清洗，可按
   `resolve_goal_space_id` 同判据出一次性脚本进 `scripts/devtools/`。
4. `test_goal_today_view` 既有失败建议另立小卡（日期冻结或真 bug 待判）。
