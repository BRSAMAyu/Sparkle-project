# GOAL-ROUTER：路由遮蔽死代码裁决与修复（S7 另一条结构性根因）

- Worker：GOAL-ROUTER（wt99-v3，base main@1c2aced1）
- 日期：2026-09-22
- 产物：`v3-output/GOAL-ROUTER/changes.patch`（5 文件，已验证可对 HEAD 干净套用）+ 本报告
- 红线声明：未 commit/push；未触碰 gateway 路由注册与守卫 ledger；未触碰 U-01/U-03 相关面；mobile goal 域回归全绿

---

## 1. 遮蔽机制（一句话）

`backend/app/api/v1/router.py` 的 `_include_experience_routers()`（经 `_include_router_if_new()`，router.py:87-93/96-110）对 `experience/*_router.py` 逐个做 **(path, methods) 键集合不重叠才整体挂载** 的去重：先注册的 `experience_readouts`（`api_router.include_router(experience.router)` 在 `_include_experience_routers()` 之前）持有 `GET /experience/goal-detail/{goal_id}`，与 `experience/goal_router.py` 的同路径 GET 存在一键重叠 → **goal_router 被整体拒绝注册**，其两个端点（GET goal-detail、PUT criteria-status）全部成为死代码。

注意去重的粒度是「router 级」：一条路由冲突即全 router 连坐——连 mobile 正在调用、且毫无重叠的 `PUT /experience/goal-detail/{goal_id}/criteria-status` 也一并被遮蔽，线上该 PUT 实际返回 405。

## 2. 消费链（裁决依据，实测代码而非推测）

```
mobile goal 详情屏 (goal_detail_provider.dart)
  GET  /experience/goal-detail/{真实goalId}   ─┐
  PUT  /experience/goal-detail/{id}/criteria-status（确认/撤销达标线）─┤→ gateway 通配代理
                                                │   (proxy_routes.go:1000-1005,
mobile home 仪表盘卡 (experience_repository.getGoalDetail('current')        /experience/*path)
  → dashboard_screen.dart GoalDetailSnapshotCard)             ─┘
                                                ↓
                          引擎 /api/v1/experience/goal-detail/{goal_id}
```

- 线上 GET 一直由 **experience_readouts** 提供（快照形状）；PUT **无任何 handler**（405，mobile 确认达标线按钮长期报错）。
- engine 内部无其它代码消费 readouts 的 `get_goal_detail`；mobile 侧该路径只有上述两个解析器。
- gateway 侧是 `registerREST(experience, "/*path")` 通配转发，引擎端点增删对 gateway 透明。

## 3. 形状对照表

| 字段 | 死端点形状（goal_router GoalDetailPayload） | 生效端点形状（readouts 快照 dict） | goal 详情屏解析器期望 | home 卡解析器期望 |
|---|---|---|---|---|
| goal | GoalSummaryPayload（id/title/goal_type/status/target_date/mastery/progress/priority） | Goal.to_dict() 全量 | GoalSummary 键集＝死端点形状 | 只读 id/title/progress |
| minimum_acceptance_criteria | dict{description,status,thresholds[]} | list[{label,status,source}] | dict{description,status,thresholds}（PUT 翻转 status） | list→可读行（_readableLine） |
| plan_health / current_phase / todays_minimal_next_step / knowledge_bottlenecks / accountability_status / related_sources / strategy_belief | 有 | **无** | 必需（缺失→常驻空态） | 不读 |
| active / plan / progress / next_task / goal_graph / why_this_matters / updated_at | **无** | 有 | 不读 | 必需 |
| `goal_id='current'` 别名 | 不支持（UUID Path → 422） | 支持（_active_goal 主目标解析） | 不用 | **依赖** |

结论：mobile 两个解析器各按一种形状编写、共用同一路径——**单选任一形状都会打碎另一个消费方**。goal 详情屏自上线起只有 goal 头部（goal.to_dict() 键恰好兼容）能渲染，达标线/今日一步/瓶颈/问责/资料/策略信念全部常驻空态，PUT 405；这就是 S7「home 说有/goal 说空」在 goal 详情屏一侧的完整成因（批1-A 修的 SSOT 取数在两侧都已落地，但 goal_router 侧从未生效）。

## 4. 裁决：方案 (a)——goal_router 生效为唯一所有者，GET 升级为超集形状

**理由**：
1. 消费链证明 goal 详情屏契约（含 PUT criteria-status）只有 goal_router 形状能承载；方案 (b) 要么永久砍掉 related_sources/strategy_belief/accountability_status/plan_health 等真实 UI 区块，要么把瓶颈排序、计划健康度等引擎公式搬进 Dart 并组合多个端点——功能回退+逻辑重复。
2. readouts 形状的消费方只有 home 卡一处，兼容成本低：把 readouts 快照字段**原样并入**超集即可，home 卡解析器仅需 criteria 行的一处小适配（见 §6）。
3. 「今日任务」口径继续由 `goal_today_view.py` 单一事实源导出：一次 `fetch_todays_next_task` 取数，同时投影 `todays_minimal_next_step`（goal 屏）与 `next_task`（home 卡），不产生第三套口径。

**实施**（全部在引擎 + mobile，gateway 零改动）：
- `experience_readouts.py`：删除 GET goal-detail（留防再遮蔽注释）及随之失去消费者的 `_criteria_payload`(list)/`_criterion_label`/`_draft_acceptance_criteria`（后者迁入 goal_router）/`_value`/`_iso`；`_next_task`、`_active_goal`、`_active_plan`、`_task_counts`、`_goal_graph_summary` 保留（被 goal_router 复用 + growth-dashboard 继续使用）。
- `experience/goal_router.py`：GET 升级为超集；`goal_id` 改 str——具体 UUID 走精确加载（查无 404，goal 屏语义），`current`/`active` 别名走主目标解析（home 卡语义，查无回退活跃计划给 `active=false` 空态）；无达标线时回退草案达标线（保持 home 卡行不退化）；PUT criteria-status 原样保留（随 router 生效）；`_todays_next_task`/`_next_step_payload`/`_todays_step_exists` 原样保留（test_goal_today_view.py 契约不破坏）。
- 复用声明：goal_router 以 `from app.api.v1 import experience_readouts as _readouts` 引用其 `_active_goal/_active_plan/_task_counts/_goal_graph_summary/_clamp_unit/_utcnow`——刻意引用而非复制，防止第三套口径漂移。

## 5. 红→绿统计

新守卫测试 `backend/tests/unit/test_goal_detail_route_shadowing.py`（9 用例：注册面 4 + 形状面 2 + 功能面 3）：

| 阶段 | 结果 |
|---|---|
| 修复前（红） | **8 failed / 1 passed**——PUT 未注册、GET 由 readouts 提供、readouts 仍注册 goal-detail、goal_router 未完整注册、response_model 缺两个契约键集、超集组装×2 失败（404 用例旧实现即满足） |
| 修复后（绿） | **9/9 passed** |

回归面：
- 引擎：`test_goal_detail_route_shadowing + test_goal_today_view + test_b2_criteria_status_endpoint` **27 passed**；experience 相关（actuator/workflow_experience/memory_provenance）57 中 56 过（1 失败为存量，见 §8）；`test_startup_smoke` 12 passed。
- mobile：`test/features/goal + test/features/experience` **20/20 passed**（--concurrency=1，含 A-6 l10n 回归与新增 3 个形状解析用例）。
- 规则守卫：`run_all_rule_guards.sh` 失败集＝基线克隆同跑失败集（AS/BI/GOV-DATA-MIN/BJ/BA-ROUTES 均为 base@1c2aced1 存量；BA-ROUTES 失败项为 insights.py 与 tasks.py reopen/rescope，不在本卡文件），**零新增失败**；BG 在基线克隆额外失败纯因克隆缺 gitignored 生成物，与本改动无关。

## 6. mobile 侧唯一改动（home 卡兼容）

`experience_models.dart` GoalDetailSnapshot：criteria 行改为 `_criteriaLines()`——新形状读 `minimum_acceptance_criteria.thresholds[]`（拼 `label >= threshold unit`，与旧引擎 `_criterion_label` 输出同形），**保留旧 list 形状回退**（滚动兼容旧引擎）。goal 详情屏解析器（goal_detail_provider.dart）零改动——它要的形状现在真的返回了。

## 7. 与 wt95（BA-ROUTES 守卫债卡）的联动

- 本卡不碰 gateway 注册与 `KNOWN_DIFFS` ledger：gateway 的 `/experience` 组是 `/*path` 通配覆盖，BA-ROUTES 守卫对引擎 `/experience` 下增删路由天然中性（catch-all 计前缀覆盖；PUT 属「已 ledger 路径上的方法级新增」也不触发路径漂移）。实测守卫失败集与基线完全一致。
- 守卫现状失败项（insights/understanding-dimensions、tasks reopen/rescope 等）属 wt95 债卡范围，本卡未代修。

## 8. 诚实申报

- **存量失败（基线复现，非本卡引入）**：`test_experience_actuator.py::...material_grounding`（file_resolution_failed）与 mobile `predicted_intent_card_test`×2（"Recent same-category signal" 文案断言）均在 /tmp 基线克隆（HEAD@1c2aced1）复现失败；前者疑依赖 MinIO/文件 fixture 环境，后者疑与 l10n 帮手有关。建议另立小卡。
- **并发树变更窗口（重要， wt8 条款场景）**：本卡施工期间，wt99 内出现一段非本 Worker 发起的批量暂存变更窗口（index 出现 lexicon/memory_panel/arb/goal_detail_l10n.dart UU 冲突等约 23 项，随后自行消散；HEAD 未移动）。本 Worker 全程遵守红线未执行 stash/reset/clean，交付物经逐文件内容核验无损失，且已提前备份至 /tmp。**请主会话核查是否有并发会话被派入 wt99**；合入本 patch 前建议再次 `git status --short` 比对（当前应为且仅为本卡 5 文件）。
- `docs/product/stage22_prompt_coverage_baseline.md` 曾被守卫跑分改写 `audited_at` 时间戳，已单文件还原，不在 patch 内。

## 9. 修复后行为对照（摘要）

| 场景 | 修复前 | 修复后 |
|---|---|---|
| goal 详情屏各区块 | 达标线/今日一步/瓶颈/问责/资料/策略信念常驻空态 | 真实数据（goal_router 契约生效） |
| 确认/撤销达标线（PUT） | 405 | 200（原 handler 生效） |
| home 仪表盘目标卡 | 正常（readouts 形状） | 正常（超集同字段；criteria 行新形状等价渲染） |
| 「今日一步」口径 | 两解析器读同一 GET，goal 屏恒空 | 同一次 SSOT 取数双投影，S7 全链路闭合 |
| 显式 UUID 查无 | 404（readouts 会静默回退到活跃目标） | 404（语义修正：精确 id 不静默换目标） |
