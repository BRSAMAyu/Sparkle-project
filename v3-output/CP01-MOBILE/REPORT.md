# CP-01-MOBILE 收工报告：计划人工确认端点 mobile 接线

- Worker: CP-01-MOBILE ｜ worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt133` ｜ 基线 b7956f1c（含 B3-CHAT）
- 交付物: `v3-output/CP01-MOBILE/REPORT.md` + `changes.patch`（新文件 `git add -N` 出 `--- /dev/null` 头，出 patch 后 `git reset -q` 还原）
- 状态: **未 commit / 未 push**（纪律遵守）

---

## ① 落点裁决

**确认动作落在 `PlanDetailScreen`（`/plans/:id`）Overview Tab 的头卡内**（计划名/进度/目标日期所在 `GraphiteCardSurface`，目标日期行之后），仅 `PlanType.sprint` 渲染。

理由：
1. `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` 是 exam-sprint 计划的主呈现面（Overview/Progress 双 Tab，含 sprint pack 上下文卡、今日焦点、7 天完成探针），确认语义（"这份计划正式生效"）的对象就是"这一份计划"，详情页是唯一无歧义落点。
2. goal detail 屏的 `goalDetailConfirm` / minimum-bar 确认区（`minimum_criteria_card.dart`）是**最低达标线确认**，与本卡 plan 整体确认语义不同，未混淆、未触碰。
3. SPEC 面积纪律：动作收进既有头卡的**次级位置**——未确认态是一个 ghost 次级按钮（`SparkleButton variant: ghost`，accent 交由主题唯一承担），已确认态是一个 success 语义槽窄条（`DS.success` 10% 底 + verified 图标 + 「已确认 · <时间>」）。不新增卡片、不加弹窗，屏幕必达项（今日焦点/新增任务）不受影响。
4. growth 类型计划不渲染该动作（后端语义面向 exam-sprint 确认；growth 计划无此仪式）。

## ② 改动清单（8 改 + 3 新）

| 文件 | 改动 |
|---|---|
| `mobile/lib/core/network/api_endpoints.dart` | +1 行：`planConfirm(id) => '/plans/$id/confirm'` |
| `mobile/lib/features/plan/data/models/plan_confirm_result.dart` | **新**：确认摘要模型（`plan_id/confirmed_at/already_confirmed/message`），手写 fromJson（对齐 `PlanPhaseBundle` 手写风格，不进 build_runner） |
| `mobile/lib/features/plan/data/repositories/plan_repository.dart` | +23 行：`confirmPlan(id)`，照抄 house style（demo 分支 → post → `unwrapMap` → `_handleDioError`）；404/网络错按既有惯例抛 `Exception(detail)` |
| `mobile/lib/features/plan/presentation/providers/plan_confirmation_provider.dart` | **新**：family 化会话内确认状态（`inFlight/confirmed/confirmedAt/error` + `PlanConfirmOutcome` 三态） |
| `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` | +80 行：头卡内 `_PlanConfirmSection`（未确认=ghost 按钮 + inFlight 转圈；已确认=success 槽 + 时间）；三态反馈走 `AppFeedback.success/info/error`（既有错误面） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` | +19 行 ×2：`planConfirmAction/planConfirmAlready/planConfirmFailed(error)/planConfirmSuccess/planConfirmedAt(time)`，字母序插入、带 `@` placeholder 元数据 |
| `mobile/lib/l10n/app_localizations*.dart`（3 个生成文件） | `flutter gen-l10n` 再生成产物（含新键） |
| `mobile/test/features/plan/presentation/screens/plan_detail_confirm_test.dart` | **新**：5 个 widget 测试（见下） |

### 设计决策申报：确认态是会话级，不挂 `PlanModel`

后端 CP-01（308400d1）只新增了 confirm 端点，**未扩 GET /plans/{id} 的 Pydantic 响应契约**（schemas/plan.py 未动），客户端无法从拉取侧得知 `confirmed_at`。因此已确认态只能由 confirm 端点的幂等 200 摘要给出 → provider 会话内记录，不伪造、不持久化。重复进入详情页按钮重现是**诚实态**：再点一次由后端幂等兜底（200 + `already_confirmed:true` + 首次时间戳），客户端按成功处理并转已确认态。若后续后端扩 GET 契约，provider 可无痕升级为服务端事实源。

## ③ 三态测试结果（红线）

新测试 `plan_detail_confirm_test.dart`（串行 `--concurrency=1`）**5/5 全绿**：

1. **未确认态**：sprint 计划渲染 `plan-confirm-button`（「确认这份计划」），无已确认徽章，未发请求；
2. **growth 排除**：growth 计划不渲染确认动作；
3. **200 首次确认**：点击 → `confirmPlan` 恰调一次 → success 反馈（「计划已确认生效」）+ 转已确认徽章（「已确认 · <时间>」），按钮消失；
4. **already_confirmed 幂等**：mock 200+`already_confirmed:true` → **不当错误**（无错误反馈），转已确认态且呈现首次确认时间戳；
5. **404**：mock 抛 `Exception: Plan … not found` → 错误面反馈（「确认失败：…」），确认动作保留可重试，不转已确认态。

### 既有测试定向回归（全部串行，逐批）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | `plan_repository_test` + `plan_detail_screen_test`（既有） | 7/7 绿 |
| 2 | `plan_provider_test` + `plan_provider_f7_16_refresh_parallel_test` | 5/5 绿 |
| 3 | `exam_sprint_closed_loop_test`（H7 闭环，渲染详情屏+任务卡） | 5/5 绿 |
| 4 | `core_provider_keep_alive_test` + `exam_sprint_flow_test` | 4/4 绿 |
| 5 | `h5_cross_system_chains` + `h9_ui_sync` | 全绿 |
| 6 | `j2_frontend_closure_test` | 5/6：1 挂为**存量**（见下） |

**j2 存量失败申报**：`tool shell sheet stays bottom aligned with close affordance` 在**干净基线 b7956f1c 克隆（/tmp，用后即删）上同样失败**——B3-CHAT 面积的存量问题，与本卡无关；同文件内 `daily detail active plan card routes to plan detail`（plan 域路由）在我的改动下通过。其余引用 `planRepositoryProvider` 的测试（chat_review_banner/chat_scroll/poster_studio/review_plan_hub/dashboard harness）仅用它作 override 点，本次未改 provider 装配，未跑（避免逼近 HEAVY 全库测试）。

### analyze

触碰文件全量 `flutter analyze`：**0 error / 0 warning**。余 17 条 info 全部核验为存量：
- `plan_detail_screen.dart` 15 条（14 条 require_trailing_commas + 1 条 unnecessary_import，`git blame` 全部指向 1722e6dc 等历史提交，不在我新增行上）；
- `plan_repository.dart:12` directives_ordering（HEAD 基线同样存在）；
- 我新增的 81 行屏幕代码、29 行模型、新测试文件：**零 lint**（新测试文件单独 analyze = No issues found）。

## ④ 红线面（触碰文件为何不破坏既有行为）

- **B3-CHAT chat 面（零接触）**：本卡未 import/chat 目录任何文件、未动 proto/gRPC、未动路由表。chat 相关测试 `chat_review_banner/chat_scroll` 依赖的只是 `planRepositoryProvider` override 点（签名未变）。
- `plan_detail_screen.dart`（+80 行纯增量）：改动=1 条 import、头卡内 5 行条件渲染、1 个新私有 widget 类；`_maybeOpenSprintCompletion`、双 Tab 结构、归档/恢复、错误恢复面均未动——H7 闭环与既有 `plan_detail_screen_test` 5 case 全绿佐证。
- `plan_repository.dart`（+23 行纯增量）：只新增方法，既有方法一字未动——`plan_repository_test` 2 case 绿。
- `api_endpoints.dart`（+1 行）：纯新增常量函数。
- 生成 l10n（申报）：`flutter gen-l10n` 再生成带 ~130 行**纯格式漂移**（参数单行→多行）。已在 /tmp 干净 HEAD 克隆复现：**同工具链对 HEAD 再生成产生同样漂移**，即 HEAD 生成物是旧工具链产出，漂移是当前工具链的确定性输出、内容无损（含 B3-CHAT 键在内全部存量键原样）。未手改任何生成文件。

## ⑤ 冲突面

在途卡 wt129（error 吸收）/wt131（orchestration）/wt132（galaxy）——本卡改动全部在 `mobile/lib/features/plan/`、`mobile/lib/core/network/api_endpoints.dart`、`mobile/lib/l10n/` 与 `mobile/test/features/plan/`。**与三卡零交集**（error 吸收在 error_book/task 面，orchestration 在 Python 引擎，galaxy 在 galaxy 面）。arb 文件为多卡共写热区，本卡插入位在 `planC*` 字母序段，冲突概率低；若与他卡 arb 撞车，按字母序重排即可。

## ⑥ 环境障碍与处置（申报）

worktree 缺 `mobile/lib/gen/`（**gitignored 生成物**，`make proto-gen` 产物；主仓有、worktree 无）→ 任何 flutter test 在编译期即炸（`review_grpc_service.dart` 找不到 proto 类，**既有测试同样失败**，非本卡回归）。处置：从主仓只读拷贝 `gen/`（1.3M，27 文件）进 worktree 供编译，属 ignored 产物、**不进 patch、不进 git**。后续 mobile worker 在新 worktree 会遇到同样问题，建议主会话固化此步骤。

## ⑦ 收工核查

- [x] `mobile/build`、`.dart_tool`：flutter test 产物已清（worktree 内）
- [x] `/tmp` 探针克隆（wt133-baseline、wt133-l10nprobe）已删
- [x] 无模拟器、无残留进程（全部 flutter test/analyze 已结束）
- [x] `git status`：8 modified + 3 untracked 新文件 + `v3-output/`（交付物容器，untracked），**无 commit 无 push**，index 干净（`git reset -q` 已执行）
- [x] swap 监控：全程串行 `--concurrency=1`、按文件分批，swap free 全程 ~950M-1.4G，未触发熔断线
