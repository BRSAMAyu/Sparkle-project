# wt274-fix-accinvite 卡报告（测试基线修复）

日期：2026-09-22 ｜ 分支：wt274-fix-accinvite（本地 2 commits，未 push）｜ 基点：b9a7da3d

## ① 根因（theme 注册现状 + 分叉结论）

**分叉 a：仅测试 harness 缺注册，生产侧无 bug。**

- 生产 `mobile/lib/core/design/design_system.dart:334-337`：`_buildThemeData` 已同时注册私有 `_SparkleThemeExtension` 与公开 `SparkleThemeExtension`（注释"🔧 修复：注册公开的 SparkleThemeExtension"）。
- 公开 extension 的读取入口 `theme/sparkle_context_extension.dart:9-12`（`context.colors` 家族）未注册即 assert 炸；`context.sparkleTheme`（design_system.dart:501-504）有 fallback 不炸。
- 共享 helper `test/shared/i18n_test_helper.dart` 的 `testMaterialApp` 已注册（U-03 修复）；但 `accountability_invite_closure_test.dart` 用的是裸 `MaterialApp.router`（无 theme）。
- 失败链：拒绝邀请 → partnerships 转空 → `CompactEmptyState`（accountability_screen.dart:66）→ `context.colors` → assert。

**前置阻塞（卡面症状之外的第一层）**：worktree 缺 gitignored 的 `mobile/lib/gen/`（proto 生成产物），先编译败。已用 host 工具链定向生成：`PATH=~/.pub-cache/bin:$PATH buf generate --template buf.gen.dart.yaml`（未动 Go/Python 产物，proto 与主仓 diff 确认一致）。

**原始报错（修复前）**：

```
══╡ EXCEPTION CAUGHT BY WIDGETS LIBRARY ╞═══
The following assertion was thrown building CompactEmptyState(...):
SparkleThemeExtension is not registered on ThemeData.
'package:sparkle/core/design/theme/sparkle_context_extension.dart':
Failed assertion: line 11 pos 7: 'extension != null'
The relevant error-causing widget was:
  CompactEmptyState  accountability_screen.dart:66:22
00:01 +10 -1: Some tests failed.
```

## ② 改动清单（+8 行，全在 test/，零生产代码改动）

1. `mobile/test/widget/accountability_invite_closure_test.dart`（e3dc8776）：`_pumpHarness` 的 `MaterialApp.router` 挂 `theme: ThemeData(extensions: [SparkleThemeExtension.light()])` + import（与 testMaterialApp 同款模式）。
2. `mobile/test/widget/commitment_detail_screen_policy_test.dart`（9b854eba）：同根因扩修同款修复（详情屏 `SparkleRefreshIndicator` 构建即读 `context.colors`）。

交付物：`v3-output/wt274-fix-accinvite/REPORT.md` + `changes.patch`（`git format-patch -2 --stdout`）。

## ③ 测试结果（原样）

卡面三文件（终验，修复后）：

```
00:01 +11: All tests passed!
```

（修复前同三文件：`00:01 +10 -1: Some tests failed.`）

commitment_detail（扩修后 2/3 绿）：

```
00:00 +0 -1: detail screen shows pending policy summary count and next trigger [E]
00:00 +2 -1: Some tests failed.
```

余 1 败为**另一确证生产 bug，非 theme，本卡按红线未越界修**：`DateFormat.yMMMd([String? locale])` 被传入 `Locale` 对象（`accountability_detail_screen.dart:956→964`，`Localizations.localeOf(context)` 返回 Locale），运行时必抛 `type 'Locale' is not a subtype of type 'String?'`。同文件同错共 4 处：**964 / 1017 / 1093 / 1261**——生产环境渲染待办策略/活动记录/打卡行即崩。仓内正确风格参照 `formatters.dart`（收 String 参）与 `paused_task_status_panel.dart`（`context.locale.toLanguageTag()`）。建议开卡修（改动≈4 行：`locale.toString()` 或改传 `context.l10n.localeName`）。

## 涟漪对照（基线还原法确证）

- 单文件粒度还原我的修复 → 跑 3 个失败邻居 → 败相逐条复现 → 恢复修复。证明以下均为**基线既有败**，与本卡零涟漪：
  - `commitment_detail_screen_policy_test`：theme 根因（已扩修）+ Locale 生产 bug（交接）。
  - `chat_action_card_navigation_test`："task list prefers task and plan detail routes"布局断言败（非 theme，未动）。
  - `action_card_task_list_test`：`Bad state: No ProviderScope found`（TaskCard @ action_card.dart:1621 harness 缺 ProviderScope，非 theme，未动）。
- 邻近绿证：`exam_sprint_dashboard_card_test` 21 过 0 败；`accountability_signal_notification_test`（testMaterialApp 系）3/3 绿。

## ④ 资源峰值

- `vm.swapusage` 全程 988M↔961M free（跑前后同值或微降，无尖峰）：开工 1280.75M free / load 13.18（等回落）；首跑前 1312M / load 7.04（过门）；终验前 961M、后 887M。全程与 wt270/wt273 错峰（ps 确认无并发 flutter/dart/gradle/模拟器），单进程定向测试，无宽扫描。
- 磁盘：收工 `df -h /` = 14Gi 可用。

## ⑤ 交接建议

1. **合入**：两 commit 均纯 test harness，对比法验证完，可按管线合入；commitment_detail 若嫌越界可只取 e3dc8776。
2. **新卡 A（高优）**：accountability_detail_screen.dart 的 4 处 `DateFormat.yMMMd(locale)` Locale/String 类型错误——真生产崩溃，不是测试问题。
3. **新卡 B（低优）**：`action_card_task_list_test` 缺 ProviderScope、`chat_action_card_navigation_test` 布局断言——两个存量 harness/组件问题，与 theme 无关。
4. **环境备忘**：每个新 worktree 需 `buf generate --template buf.gen.dart.yaml`（PATH 加 `~/.pub-cache/bin`）否则 mobile 测试全编译败；本树 lib/gen 已生成（gitignored）。
5. **副作用备忘**：本地 Flutter 的 gen-l10n 会重排 `lib/l10n/app_localizations*.dart` 格式（纯格式 diff，已 `git checkout --` 还原）；后续 worker 跑测试还会遇到，勿误当真实改动提交。

## 收工清理

mobile/build、.dart_tool 已删；/tmp 备份已删；无遗留进程；树净（git status 0）；未 push、未动 main、无 stash/reset/clean（基线对照用单文件粒度 `git checkout -- <file>` 还原法）。
