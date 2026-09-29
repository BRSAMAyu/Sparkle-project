# FIX-566 独立审查 receipt（R1）

- 审查人：R1（独立会话，未参与实现）
- 日期：2026-09-29
- 被审对象：fix commit `ea55abb7`（base `dd4de05a`，分支头 `a6f12d1a`），分支 `fix/v4/f566-retry-scroll-jump-latest`，worktree wtF566
- 审查环境：flutter 3.41.3 stable homebrew（48c32af034，与 manifest 记载同机同装）、dart/flutter analyze、本机 gen-l10n 同格式器

## VERDICT: PASS

八靶全打，无 P0/P1/P2 阻断项；L1 限制由本审查正验升格（行级零漂移成立）；4 项 info 级发现，均不阻塞。修复真实、完整、可复验，mutation 三向有牙（M-① 亲复现 + R1 自做 2 个）。

## 逐靶结论

1. **①裁决复核（补 force vs 豁免）**：U07 一审原文核实（`v4/evidence/V4-U07/review_r1.md`：C-2 登记 reuse 重试不 force、R-1 裁回底入口出卡立微卡；R-2 已给「screen 侧对同轮重发补 force」同方向建议）。豁免前提否决有据：错误横幅为滚动 Stack 之外的 Column 兄弟件（`chat_screen.dart:2441` 起 `SparkleExitTransition` 全宽容器），任意滚动位常驻可点；语义注释在案（`chat_screen.dart:249-251`「发送/重试/快捷动作=显式用户动作」）。「重试均触发 force」对 reuse 路径成立依赖本修复，裁决成立。
2. **①实现核验**：全仓 grep `retryLastMessage`——UI 侧 provider 调用仅 `chat_screen.dart:992`（收拢于 `_retryLastMessage()`），按钮唯一产品调用点 ：2535，其余为测试直驱。force 先序正确：`_scrollToBottom(force: true)` 同步先翻锚（`forceFollow()`）再 `animateTo(0)`（:3081-3095），使后续助手应答到达时的到达性滚动（非 force、门控于 `shouldFollow`）必然跟随——force 后置则依赖 provider 微任务序，先序是唯一确定性选择。复用既有 force 机制零第二权威：`ChatScrollAnchor` 与 providers 目录 diff 为空（亲验）。provider 零 diff：`ea55abb7` 8 文件不含 `chat_provider.dart`，`git diff dd4de05a..a6f12d1a -- mobile/lib/features/chat/presentation/providers/` 零输出。
3. **M-① 亲复现**：删 ：991 force 行（sed 行级替换）→ 仅「F566① 正」红，失败形态 `Expected: <0.0> Actual: <580.0>`（恰 U07 C-2 原缺陷形态：视口滞留阅读位 580 不回底），unit+①反+②×2 共 4 测保持绿；`git checkout --` 还原后 5/5 绿。
4. **②胶囊行为**：可见性为锚的帧级镜像（`_handleScroll` :1340-1345 先 `updateFromPosition` 再翻转帧 setState，单一事实源，无需节流——setState 仅翻转帧触发）；240px 窗两沿断言（贴底隐藏/上滑浮现/滑回隐藏）与点击回底由本审查亲跑 5/5 绿；空态零面积为结构性双保险（`!inQuickActionsState` 条件 + 空列表 `maxScrollExtent<=0` 锚恒跟随）；OVERLAY-SMALL 让位几何核验（dock 全宽单行 `bottom: DS.spacing4` :2382-2384，胶囊 `bottom: DS.spacing64` 右侧，静偏移合理，视觉终审归 L3/Q05 已登记）；DS 令牌：新增行硬编码样式扫描零命中、14 处 `DS.*`，UI-TOKENS 棘轮亲跑 PASS（color=225/275、fontSize=632/727）。
5. **R1 自做 mutation ×2**：
   - **R1-A** 胶囊显隐条件常显化（:1343 `!_scrollAnchor.shouldFollow`→`true`）→ **3 红**（①正 ：358 findsNothing、②三态贴底隐藏、②点击回底隐藏，均 `Expected: no matching candidates / Found 1 widget`），①反绿（其仅断言在场）→ 还原 4/4 绿；
   - **R1-B** 胶囊 onTap 去 force（:2410 `_scrollToBottom(force: true)`→`_scrollToBottom()`）→ **仅②点击红** `Expected: <0.0> Actual: <600.0>`（非 force 早退，视口滞留）→ 还原 4/4 绿。胶囊 force 语义与显隐布线双向有牙。
6. **回归与 l10n**：新测 5（widget 4+unit 1）亲跑全绿；回归面（test/features/chat + test/unit + test/core/widgets + 4 相邻 widget 文件）**606 passed +1 skipped** 与声称分母一致；`flutter analyze --no-pub` No issues found；arb 消息键集合（排除 `@` 元数据）**中英 10267=10267 相等**，diff 纯增量仅 `chatJumpToLatest`（zh=回到最新/en=Back to latest）；gen 产物三文件 diff **+6/+3/+3 纯增量零删行**。
7. **L1 正验升格（挑战解除）**：本机实跑 `flutter gen-l10n`（l10n.yaml 无 output-dir，产物即 `lib/l10n/` 三文件）两轮，mtime 均更新（12:32:23→12:33:23）而 `git status` 恒零输出——**入库 gen 产物与本机格式器全量再生 byte-identical，行级零漂移正验成立**，强于实现者「键级已验、行级不可判」的登记（其 144+/50− 对照系对 main c1f4f007 裸跑，与 dd4de05a 基线 gen 产物状态不同源，不构成对本头缺陷）。
8. **L2 判定（接受）**：provider 侧 reuse 真语义由 unit 测试走**真实 send 全链**钉住（真 `ChatNotifier.sendMessage`→`ErrorEvent`→`retryLastMessage`→断言用户消息恰 1 条+新 run isSending+错误清除），非播种；widget 侧播种仅提供横幅前置态，被钉差量「点重试→force 滚动」是 screen 侧事实，与错误态来源无关（按钮 onPressed→`_retryLastMessage` 两路径共用）。残余风险（播种态与真实失败态的横幅渲染等价性）实现者已登记，且横幅渲染非本卡改动面（`SparkleExitTransition` 零 diff）。覆盖差可接受，无附加要求。
9. **零削弱**：`git diff dd4de05a..ea55abb7 -- mobile/test/` **+766/−0**（两测试文件全新增，零既有测试修改、零断言删除）；screen 侧唯一 −7 为横幅内联 provider 调用收拢为 `_retryLastMessage()` 单行（纯等价替换）；到达性门控表达式（initState 监听 ：248-268）不在 diff 内逐字未动；`ChatScrollAnchor` 零改动。

## 编号发现

- **F1（info）** `chat_screen.dart:990-993`：`_retryLastMessage()` 无条件先 force 滚动，退化态（`_retryableRequest==null` 且连接健康，`retryLastMessage` 走 reconnect 空转）也会回底而无实际重发。横幅仅错误态在场、可重试错误均源自失败 send（已设 `_retryableRequest`），触发面趋近于零；登记备查即可，不建议改动。
- **F2（info）** 空态零面积无专属 widget 断言，由结构双保险保证（条件隐藏 + 空列表不可滚动锚恒跟随）；如 Q05 视觉终审改造入口，可顺手补一枚空态断言。
- **F3（info）** manifest 的 M-全量（stash 产品 diff 4 widget 全红）未由 R1 独立重做；已由 M-① + R1-A/R1-B 三向独立 mutation 补偿，牙齿证据充分。
- **F4（info）** 原始 arb 层中英键集合不等（en 11426/zh 11380）系既有 `@` 元数据键分布差异（`@auto_*` 等描述键），非本卡引入；gen-l10n 口径（消息键）10267=10267 相等，与 manifest 声称口径一致。

## 探针还原

三次 mutation（M-①/R1-A/R1-B）均 `git checkout --` 还原；两轮 `flutter gen-l10n` 产物 byte-identical 不污树；审查终点 `git status` 干净、HEAD `a6f12d1a` 未变。

## 命令与 exit code

| # | 命令（wtF566/mobile 下除注明外） | exit | 结果 |
|---|---|---|---|
| 1 | `flutter test test/unit/chat_f566_retry_reuse_path_test.dart test/widget/chat_f566_retry_force_scroll_jump_latest_test.dart --concurrency=1` | 0 | +5 All tests passed |
| 2 | M-①（sed 删 ：991 force 行）后重跑命令 1 | 1 | +4 −1，仅①正红 `Expected <0.0> Actual <580.0>` |
| 3 | `git checkout -- lib/.../chat_screen.dart` 后重跑命令 1 | 0 | +5 All tests passed |
| 4 | R1-A（:1343 常显化）后 `flutter test test/widget/chat_f566_retry_force_scroll_jump_latest_test.dart --concurrency=1` | 1 | +1 −3（①正/②三态/②点击红） |
| 5 | 还原后 R1-B（:2410 去 force）后同上 | 1 | +3 −1（仅②点击红 `0.0≠600.0`） |
| 6 | 还原后 `bash scripts/run_all_rule_guards.sh --rule UI-TOKENS`（仓库根） | 0 | PASS color=225/275 fontSize=632/727 |
| 7 | python3 arb 键集合比对 + gen diff 行数统计 | 0 | 消息键 10267=10267；gen +6/+3/+3 零删行 |
| 8 | `flutter gen-l10n` ×2 + `git status --short` | 0 | 零输出（byte-identical，L1 正验） |
| 9 | `flutter test test/features/chat test/unit test/core/widgets test/widget/chat_scroll_test.dart test/widget/chat_review_banner_test.dart test/widget/chat_long_suggestion_reparent_test.dart test/widget/chat_area_budget_test.dart --concurrency=4` | 0 | +606 ~1 All tests passed |
| 10 | `flutter analyze --no-pub` | 0 | No issues found! |
| 11 | `git diff dd4de05a..ea55abb7 -- mobile/test/` 增删行统计 | 0 | +766/−0 |

## receipt SHA

`<由提交产生，见最终报告>`
