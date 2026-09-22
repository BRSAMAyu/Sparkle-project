# OVERLAY-SMALL 收工报告：chat 小屏（375×667）overlay 化提面积

- Worker：OVERLAY-SMALL（V3 舰队）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt139`（基线 a1572cfa，含 B3-CHAT 重划 + CP-01-MOBILE）
- 交付物：本报告 + `changes.patch`（7 文件，405 行）
- 纪律：未 commit / 未 push；主仓只读；交付物零凭据

---

## ① 面积构成实测 + 两处改动选择依据

### 改动前 375×667 构成（仪表化探针实测，2026-09-22）

| 块 | 高度 dp | 占 667 比 | 说明 |
|---|---|---|---|
| AppBar | 56.0 | 8.4% | 双行标题 + 收件箱/设置/历史/更多 |
| chatHeaderPanels | 0 | 0% | 无事件时零面积（S8 语义保持） |
| **消息视口** | **429.0** | **64.3%** | B3-CHAT 实测口径 |
| 模式条折叠行 ChatContextToggle + 间隙 | 38.0 + 4 | 6.3% | S8 折叠行，常驻 |
| 预测 dock（折叠态）+ 外边距 | 36.0 + 6 | 6.3% | C-11 单行 headline，常驻 |
| ChatInput | 90.0 | 13.5% | 最大单块，不动（砍功能红线） |
| 底部安全垫 | 8.0 | 1.2% | max(spacing8, padding.bottom) |
| 合计 chrome | 238 | 35.7% | 与 390×844 的 chrome 完全同高（844−606=238）——**小屏劣化纯粹是分母效应** |

列表底 padding `_calculateBottomPadding` compact 档已预留 **152dp**（输入 90 + 安全垫 8 + dock 42 + 信号/呼吸留量）——这就是 overlay 化的落点：悬浮胶囊可以叠进这段"纯留白"而不压消息。

### 选定的两处改动（SPEC「每 surface 必达项 ≤2」精神）

**改动 1：预测 dock 小屏悬浮胶囊化**（375×667 下 dock 42dp → 0dp 常驻）
- 实现：视口包 `Stack(clipBehavior: Clip.none)`，非空态时 dock 以 `Positioned(bottom: spacing4)` 叠于视口底部留白区；内联路径仅保留给大屏与空态（快捷建议页内容居中铺满，悬浮会压住入口 chips，故空态不悬浮）。
- 出退场动画（`SparkleExitTransition`）、C-11 chip 预算、填入式回调逐位共用（抽出 `_buildPredictionDock` 单点维护）。
- 前 42dp → 后 0dp；消息可滚出 dock 后方（152dp 留白 > 输入 90 + 安全垫 8 + dock 40）。

**改动 2：模式条折叠行小屏收进「更多」溢出菜单**（38+4dp → 0dp）
- 实现：`_isCompactShortMobileContext`（宽<430 且高<700 的紧凑竖屏）折叠态下隐藏 ChatContextToggle 行；AppBar 既有 PopupMenuButton 新增 `_ChatShortcutAction.contextControls` 菜单项（新 l10n 键 `chatContextControlsExpand` zh/en 双语）承接展开入口；展开态屏内折叠行**自动回归**并充当收起控制。
- 折叠/展开语义不变：默认收起、按需展开、展开后可收起；「推理·模式·计划」状态摘要入口位由菜单项文案承接。

### 小屏判别边界（防误伤）

`_isCompactShortMobileContext` = portrait && width<430 && height<700。390×844 canonical 面**不命中**——B3-CHAT 已验收面积行为逐位不变（见下）。

### 改动前后对比

| 表面 | 改动前 | 改动后 | 断言下限 |
|---|---|---|---|
| 390×844（canonical） | 606dp / **71.8%** | 606dp / **71.8%**（逐位不变） | ≥0.70 |
| 375×667（小屏） | 429dp / **64.3%** | **509dp / 76.3%**（+80dp，+11.9pp 实测 / 口径 +12.0pp 四舍五入） | **≥0.70（从 0.62 收紧）** |

目标达成：任务卡目标 ≥66%，冲 70% —— **70% 达成**，断言按 0.70 落地（留 6.3pp 余量防平台字体抖动）。

## ② 红线面（为何不破坏 B3-CHAT 语义 / 功能不减）

1. **五大件收容语义逐条核对**：
   - 内联信号：未触碰（`_hasInlineSignals` 分支原样）；
   - 收件箱入口：未触碰，且断言升级为 `ChatInboxEntryIcon findsOneWidget`（防回归锁）；
   - 折叠展开：语义保持"默认收起 / 按需展开 / 可收起"——小屏折叠行的收起控制=展开态回归的屏内原行，展开入口=溢出菜单项（可达性闭环）；大规模重排零涉及；
   - 预算函数：`_calculateBottomPadding` 与 0.20/0.60 双 cap 未动；悬浮 dock 的净空仍由既有 152dp 留白承担，未新增任何"吃掉预算"的常驻块；
   - V13/记忆面板：budget 测试中 `ChatWorkingMemoryPanel findsNothing` + `StatusAwarenessBar findsNothing` 断言原样保留并通过。
2. **功能不减**：dock 悬浮化≠移除（测试显式断言 `ChatPredictionDock findsOneWidget`）；空态快捷建议页保持 dock 内联（不受悬浮遮挡）；大屏（含 390×844）行为与基线逐位一致。
3. **proto/DB/分层边界**：纯 mobile widget 层改动，零 proto、零迁移、零网关。

## ③ 冲突面

触碰文件全集：`mobile/lib/features/chat/presentation/screens/chat_screen.dart`、`mobile/lib/l10n/app_{zh,en}.arb`、`mobile/lib/l10n/app_localizations{,_zh,_en}.dart`、`mobile/test/widget/chat_area_budget_test.dart`。与在途卡 wt137（backend 事件）、wt138（backend 迁移）、wt136（backend 测试）**零交集**（全 mobile，单 feature 目录 + l10n 工件 + 单测试文件）。

## ④ 诚实申报

- **实测最终值**：375×667 = **76.3%**（viewport 509dp），vs 70% 目标超额 6.3pp；vs 卡内保底 66% 超额 10.3pp。
- **预测偏差**：改动前推算 513dp/76.9%，实测 509dp/76.3%——差额 4dp 来自底区链路中原被 dock 外边距掩蔽的既有间隙（探针两轮实测均稳定复现），非回归、非裁剪，按实测值落地断言。
- **"overlay 化面积"口径如实说明**：76.3% 为 B3-CHAT 既有口径（视口组件高度/屏高）。悬浮 dock 40dp 叠在列表 152dp 底部留白区内，末条消息可完整滚出胶囊上方，实际可读面积同比增大；未发生"把 chrome 藏进视口数字"的口径游戏——dock 与模式条均有可达入口（菜单项/屏内折叠行）且有测试锁。
- **回归批次 4 个失败为 HEAD 既有**（已 stash 复现对照）：`chat_design_language_widgets_test` 的 Material 短捷扫描（指向 message_detail_view.dart / node_detail_sheet.dart，非本卡触碰文件）与其 dark golden 像素差（97.6%，环境字体渲染级）、`j5_frontend_closure_test` ×2 的 `SparkleThemeExtension not registered`（unified_omni_bar.dart 测试 harness 主题未注册）。与本卡改动无因果。
- **l10n 工件差异说明**：本机 gen-l10n 产物与仓内已提交工件存在大面积格式漂移（formatter 版本差异），为控补丁噪音，dart 工件改为**手工按既有格式**追加 `chatContextControlsExpand` getter（arb 双语正常新增）；后续卡片如需全量 regen 请单独立卡统一 formatter。

## ⑤ 回归矩阵

| 验证项 | 结果 |
|---|---|
| `chat_area_budget_test`（390×844 ≥0.70 + 375×667 ≥0.70 + 面板 findsNothing + 收件箱入口 + 小屏形态断言） | ✅ 2/2（71.8% / 76.3%） |
| V13 citation replay（`chat_message_model_citation_replay_test`） | ✅ |
| 记忆面板 findsNothing（budget 测试内 S8 断言） | ✅ |
| `chat_review_banner` / `chat_scroll` / `aurora_daily_startup_retry` / `modeling_chat_screen` / `chat_history_sheet_regression` | ✅ 全绿 |
| `chat_prediction_dock_c11`（C-11 预算+填入式）/ `working_memory_drawer` | ✅ 全绿 |
| `chat_golden_test`（含 375×667 mobile 档） | ✅ 10/10 |
| analyze 触碰文件 | ✅ 0 error（chat_screen 59 issues = 基线持平；budget test 8 < 基线 9） |
| 既有失败（基线复现，非本卡） | design_language ×2、j5 ×2（详见 ④） |

flutter test 全程串行 `--concurrency=1` 单批执行；期间 swap 空闲 1.15G–1.35G、load 4.5–5.0，未触发熔断。

## ⑥ 收工核查

- [x] 探针测试 `overlay_probe_tmp_test.dart` 已删除（测量数据已固化进本报告）
- [x] `mobile/build`、`mobile/.dart_tool` 已清理；worktree 内无残留构建产物
- [x] 从主仓拷入的 `mobile/lib/gen`（gitignored）已清除
- [x] 无模拟器/无遗留进程；`/tmp` 探针文件已清
- [x] 未 commit / 未 push；改动以 `v3-output/OVERLAY-SMALL/changes.patch` 交付
