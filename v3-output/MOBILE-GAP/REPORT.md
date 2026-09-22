# MOBILE-GAP 收工报告：六新面入口盘点 + Top1（自我锚）补齐

- Worker: MOBILE-GAP ｜ worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt163` ｜ 基线 `b6a68ae3`
- 交付物: `v3-output/MOBILE-GAP/REPORT.md` + `changes.patch`（14 文件，其中 6 新文件带 `--- /dev/null` 头；出 patch 后已 `git reset -q`）
- 状态: **未 commit / 未 push**（纪律遵守）｜ 零凭据

---

## ① 缺口盘点表（只读扫描 mobile/lib 全量）

| # | 后端新面 | 网关路由 | mobile 入口状态 | 证据 | 建议落点屏 | 价值排序 |
|---|---|---|---|---|---|---|
| 1 | 计划确认 `POST /plans/{id}/confirm` | ✓ | **已接线**（CP-01-MOBILE） | `plan_repository.confirmPlan` + `plan_detail_screen._PlanConfirmSection` | PlanDetail 头卡（已落） | — |
| 2 | 自我锚 `GET /leaderboards/self-anchor`（D-COMM-1） | ✓ wildcard 代理 | **缺口（零消费）** | 全库无 `self-anchor/selfAnchor` 命中；排行榜域仅消费 `/leaderboards` 五个旧端点 | Sprint 仪表盘次级入口 → 独立屏 | **Top1（本卡已补）** |
| 3 | 冲刺小队 `/community/squads*`（D-COMM-3） | ✓ 6 条 | **缺口** | `api_endpoints.dart` 无 squads 端点；既有 "squad" 命中均为 l10n 文案/群组旧域，非该 API | 社区 Tab 内小队列表+详情 | 3 |
| 4 | 小队榜 `/community/squads/{id}/leaderboard`（D-COMM-4） | ✓ | **缺口** | 同上，零命中；且 `<3` 人降级 `self_view_only` 无消费方 | 小队详情内 Tab（复用 D-COMM-1 自我锚为降级视图） | 4 |
| 5 | 自习室 `/community/squads/{id}/study-room/*`（D-COMM-4） | ✓ enter/exit/heartbeat/presence | **缺口（零命中）** | 全库无 `study-room/studyRoom` 命中 | 小队详情头部进出按钮 + 在场列表 | 5 |
| 6 | 光子兑换 `POST /photons/redeem-pro`（D-COMM-2） | ✓（`/billing/redeem` 同风格映射在引擎侧） | **缺口** | `api_endpoints.dart` photon 域仅 balance/transactions/transfer | 光子钱包/商店页兑换卡（可兑换基数来自响应，诚实呈现不足/月顶） | 2 |

另注：既有 `LeaderboardScreen`（全站榜）在路由层**无任何注册与入口**——这正是 D-COMM-1/D17「全站榜保持隐藏」裁决的正确现状，本卡未给其新增入口，遵守不翻案。

### 排序论证（北极星场景 = 期末一周的用户价值 × 实现成本）

1. **自我锚（已补）**：期末周学生每天最关心「我是否在跟上自己的计划」——自我锚以 sprint 账本唯一口径直接回答，且是 D-COMM-1 裁决后排行榜域**唯一被允许路由的产品面**；D-COMM-4 小队榜 `<3` 人时 `self_view_only:true` 的降级目标就是自我锚 → 先落它，后续小队卡可直接复用，是组合件里的地基。成本最低：1 只读端点、1 屏、不依赖任何其他面（小队/自习室依赖 ≥3 人小队才非空，单人旅程测试下全是空壳）。
2. **光子兑换**：商业价值高但北极星备考场景内低频（月顶 1 次的一次性兑换），且涉及变现语义需产品侧谨慎，留独立卡。
3-5. **小队→小队榜→自习室**：冷启动依赖真实多人；自习室 heartbeat 还需后台定时器策略（移动端功耗/退监听），一卡吃不下，建议后续「小队组合卡」按 D-COMM-3→4 顺序两屏内收敛。

## ② Top1 实现清单（自我锚 · 8 改 + 6 新）

| 文件 | 改动 |
|---|---|
| `mobile/lib/core/network/api_endpoints.dart` | +2 行：`leaderboardsSelfAnchor = '/leaderboards/self-anchor'` |
| `mobile/lib/features/leaderboard/data/models/self_anchor_model.dart` | **新**：`SelfAnchorView`/`SelfAnchorDayPoint`，手写 fromJson（对齐 `PlanConfirmResult` 手写风格，不进 build_runner）；字段/语义逐一对应 `SelfAnchorViewResponse`（`has_any_data` 诚实空态标记） |
| `mobile/lib/features/leaderboard/data/repositories/self_anchor_repository.dart` | **新**：只读单端点仓库；demo 分支同走诚实空态（真零 7 日窗，不造假曲线）；`unwrapMap` + data 缺失抛 `Exception`，照 house style |
| `mobile/lib/features/leaderboard/presentation/providers/self_anchor_provider.dart` | **新**：`autoDispose AsyncNotifier`（照 `learningPortfolioProvider` 现行风格）+ repository provider |
| `mobile/lib/features/leaderboard/presentation/screens/self_anchor_screen.dart` | **新**：`self_anchor_screen.dart` 命名合规。SPEC v1.0：**必达项 2**——①窗口合计摘要卡（完成 N 项 + 掌握度增量）②每日完成 7 柱序列卡（旧→新，零值日如实不画数值）；**唯一 accent**（`context.colors.brandPrimary`），今日列仅字重区分不作第二色；颜色/字号/间距/圆角全部走 `context.colors/typo/space/radius` 令牌，零 `Color(0x…)`/`Colors.*`/`fontSize:` 字面量；组件全部消费 owner（`SparklePageScaffold`/`GraphiteCardSurface`/`EmptyState`/`CustomErrorWidget`+`SparkleButton` 重试/`SparkleCardSkeleton`/`SparkleRefreshIndicator`/`ContentConstraint`），禁用项零触碰 |
| `mobile/lib/features/leaderboard/leaderboard_routes.dart` | **新**：`LeaderboardRoutes.selfAnchor = '/leaderboards/self-anchor'`（文件头注明 D17 隐藏裁决，不建全站榜路由） |
| `mobile/lib/app/routes.dart` | +2 行：import + `...LeaderboardRoutes.routes` 聚合 |
| `mobile/lib/features/plan/presentation/screens/sprint_screen.dart` | +9 行：AppBar 动作区追加「查看自我锚」ghost 图标按钮（Tooltip 语义），次级位置不占内容主面积；空数据无冲刺时按钮仍在（路由可达性不依赖状态） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` | +19 行 ×2：`leaderboardSelfAnchor*` 12 键（标题/副题/空态引导三件套/加载失败/重试/合计/单位/增量/入口标签），字母序插入、带 `@` placeholder 元数据 |
| `mobile/lib/l10n/app_localizations*.dart`（3 个生成文件） | `flutter gen-l10n` 产物（格式基线已重置，diff 仅含新键，干净） |
| `mobile/test/features/leaderboard/presentation/screens/self_anchor_screen_test.dart` | **新**：4 个 widget 测试（见下） |

### 设计决策申报

1. **空态诚实**：`has_any_data:false` 渲染 `EmptyState`（引导语 + 「去看我的冲刺」按钮跳 `/sprint`），**不渲染摘要卡与假零柱状图**——与 FLEET-BRIEF §四.4 诚实性红线一致；demo 模式同口径。
2. **窗口合计数字不四舍五入口径**：`total_mastery_delta` 仅展示层 `toStringAsFixed(1)`；完成数原样直显，不自算（唯一事实源 = 引擎账本聚合）。
3. **provider 生命周期**：autoDispose——自我锚是「看一眼」型快照面，离开即释放，重进重取，无需缓存失效协议。
4. **今日列用字重不用第二色**：SPEC 唯一交互色 accent 纪律；color 盲安全（Wong 色板下的 brandPrimary 也不受影响）。

## ③ 回归结果

### 新测试 `self_anchor_screen_test.dart`（串行 `--concurrency=1`）**4/4 全绿**

1. **数据态**：摘要卡（15/冲刺任务/掌握度 +2.4）+ 7 柱序列卡 + 非零日数值标签逐一可见 + 零值日无假标签（诚实零）+ 今日日期列 + 无「排行榜」社交比较元素残留（D-COMM-1 语义断言）；
2. **空数据态**：`EmptyState` 引导 + 无摘要卡/无序列卡（不造假图表）；
3. **错误态→重试**：诚实错误文案 + 点重试按钮翻转回数据态（repo 调用计数 2）；
4. **路由可达**：`/leaderboards/self-anchor` 经 `LeaderboardRoutes.routes` 注册进 GoRouter 可直达渲染。

### 既有测试定向回归（全部串行，逐批，批后清 build/.dart_tool）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | `app/router_smoke_test` + `app/router_deep_link_test`（全量路由装配，含新路由） | **12/12 绿** |
| 2 | `plan_detail_confirm_test` + `plan_detail_screen_test`（同 feature 撞屏面） | **10/10 绿** |
| 3 | `sprint_completion_screen_test` + `diagnostic_quiz_screen_test`（sprint 入口改动所在屏的相邻屏） | **5/5 绿** |

### analyze 与守卫

- 触碰文件 `flutter analyze`（leaderboard 全目录 + sprint_screen + routes.dart + api_endpoints.dart + 新测试）：**0 error / 0 warning**；余 11 条 info 全部为存量（逐条与 `git diff -U0` 行号比对，均在我改动行之外）。
- `check_ux_component_convention.py`：**PASS**（rawButton 19/19、rawChip 11/11、colorLiteral 100/100 ratchet holds——新代码零新增违规）。
- `check_ui_design_tokens_ratchet.py`：**PASS**（color 239/275、fontSize 719/727）。

### 环境修复申报（非代码改动）

worktree 缺少未入库的 `mobile/lib/gen/` 产物（27 个 `*.pb*.dart`），首跑测试全库编译失败。经 `buf generate --template buf.gen.dart.yaml`（本机 protoc-gen-dart@pub-cache）补齐，产物在 `.gitignore` 内不入 patch。

## ④ 冲突面申报

- **wt160**（aurora 收件箱域，批4）：本卡文件面 = `features/leaderboard/**`（全新）+ `plan/sprint_screen.dart` AppBar + `app/routes.dart` 聚合行 + l10n 新键 + `core/network/api_endpoints.dart` +1 常量——与其 aurora 收件箱文件面**零交集**；l10n 两文件若双方同轮追加键，合入时按字母序插入各自区段，冲突 trivial（`git apply --3way` 可解）。
- **wt161/162**（backend 域）：无交集。
- `v3-output/MOBILE-GAP/` 为本卡专属输出目录，无他卡使用。

## ⑤ 诚实申报

1. 排行榜域既有 `LeaderboardRepository`/`leaderboard_provider.dart` 未复用（其模型绑死旧五端点 + StateNotifier 旧风格），自我锚独立成套、零改动既有文件——避免顺手动存量引入回归面。
2. 日期标签为 UTC 日界直显（`M/d`），未做本地时区日界换算——引擎契约明确「本地化日界属展示层职责」，本卡按最小必达未实现时区换算，登记为后续打磨项（若产品要求本地日界，改 `_DailySeriesCard` 单点即可）。
3. 未新增 `CustomErrorWidget` 的 `onRetry` 依赖（其 inline 型不渲染重试钮），重试为屏内显式 `SparkleButton`——组件行为经源码确认后落位，非假设。
4. 测试对今日列的断言使用真实机器时钟（UTC 2026-09-22 验证通过）；若跨日跑 CI 理论上「今日高亮」断言仍稳定（fixture windowEnd 即当页最后一天，与「哪天」无关），唯 `9/22` 文案断言绑定 fixture 日期而非 now——已设计为时钟无关。
5. 未跑全库测试（资源纪律：定向回归 + 路由装配冒烟已覆盖改动可达面）。

## ⑥ 其余缺口卡建议（登记回执）

- **D-COMM-2 兑换入口**（排序 2）：photon 钱包/商店页加「光子兑 Pro」卡；仓库层处理 4 个业务终态（400 余额不足 / 409 基数不足 / 409 月顶 / 200 成功+到期时间），响应里的可兑换基数直接呈现；一屏 + 一次确认弹窗。
- **D-COMM-3+4 小队组合卡**（排序 3-5，收敛 2 屏）：小队列表屏（`GET /community/squads` 我的队 + join/leave）→ 小队详情屏头部挂「自习室进出（enter/exit + presence 在场列表）」+ 榜 Tab（`<3` 人时按 `self_view_only` 切自我锚——本卡屏可直接复用/嵌入）。heartbeat 建议屏内 Timer + 退屏 exit，功耗决策留卡内论证。

## ⑦ 收工核查

- [x] `mobile/build`、`mobile/.dart_tool`：每批测试/analyze 后即删，最终已清
- [x] `/tmp` 本卡产物（`wt163_selfanchor_test.log`、`wt163_retry.log`、`debug_dump_test.dart`、`wt163_changes.patch` 副本）：清理（patch 已入库至交付目录）
- [x] 无模拟器/Gradle/浏览器 HEAVY 操作；flutter test 全程 `--concurrency=1`
- [x] 零 commit / 零 push / 零凭据；主仓只读未触碰
- [x] 新 UI 全令牌消费，双守卫 ratchet PASS
