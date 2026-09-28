# V4-FIX-547 receipt — sendMessage 续延 dispose 后活性守卫（P2 产品侧）

- 日期：2026-09-28
- 分支：`agent/v4/fix547`（worktree `../wtF547`，base main@b4fa8900，**未 push**）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-547 行（wt805 判「测试单侧修不彻底，建议产品侧独立卡」，本卡即该产品侧卡）
- 上游取证：`v3-output/WT805-FLAKEFIX/notes.md` §2.3；CI 29 job 108772804580 attempt 1 唯一红（chat_value_signal_test「failed after test completion」）

## 1. 复现（先红后修）

CI 29 真红链：`ChatNotifier.sendMessage` 续延在 `chat_provider.dart:1388` 读
`subscriptionsProvider` → 触发该 provider 构建（其 build 内 `unawaited(loadSubscriptions())`
网络写回）→ 容器在写回落定前 dispose → 写落在已 dispose 的 SubscriptionsNotifier 上 →
`Bad state: Tried to use SubscriptionsNotifier after dispose` 以未处理异步错误泄漏 →
「failed after test completion」。

新增回归钉 `mobile/test/features/chat/presentation/providers/chat_send_message_dispose_guard_test.dart`（3 测，真接线形制——ChatNotifier 经 `chatProvider` 由容器持有，`container.dispose()` 同时 dispose 两个 notifier，与生产 StateNotifierProvider 生命周期一致）：

| 测 | 形态 | 修复前（pre-fix 实录） | 修复后 |
|---|---|---|---|
| 控制组 | 容器存活：订阅正常写回、发送正常完成 | ✅ 绿 | ✅ 绿 |
| 钉 A（CI 29 形态） | 读簇触发订阅加载后容器 dispose，迟写回落定于 dispose 后 | ❌ 红：`Bad state: Tried to use SubscriptionsNotifier after dispose was called`（与 CI 29 签名逐字一致，runZonedGuarded 体内确定性断言） | ✅ 绿 |
| 钉 B（token 缺口形态） | sendMessage 挂在 token await 上时容器 dispose，续延恢复 | ❌ 红：`Bad state: Tried to use ChatNotifier after dispose`（栈：`chat_provider.dart:1345 finalizeRun ← 2264 catch 路径`，`await sendFuture` 抛出） | ✅ 绿 |

修复前实测（fix 落地前运行）：`+1 -2: Some tests failed`（控制组绿、双钉红，exit≠0）；
修复后 `+3: All tests passed`（exit=0）。「不写 state」由「已 dispose 的 StateNotifier 任何
state 写必抛 Bad state」互为充要：无泄漏错误 ⇔ 未写 state。

## 2. 修法（按仓内既有模式择优：取消传播 mounted/_isDisposed 门）

选择**取消传播（dispose→守卫门→续延退出）**，非 `ref.exists`/container 探测、非 `on StateError` 吞噬：

- `Ref.exists` 语义是「provider 是否已构建」而非「容器是否存活」，不能作活性探测；riverpod 2.6.1 `ProviderContainer._disposed` 为私有，无公开探测 API，任何探测式写法要么不可行要么依赖异常。
- `on StateError` 吞噬（api_interceptor.dart 先例）会把存活容器上的真 StateError bug 一并静默=改变正常路径行为；且 api_interceptor 需要它是因为拦截器对象不是 StateNotifier、没有 `mounted`——ChatNotifier/SubscriptionsNotifier 都有，故取更精确的门。

### `mobile/lib/features/chat/presentation/providers/chat_provider.dart`（+4 门）

1. `await guestService.getGuestId()` 续延恢复点（getGuestId 是平台通道异步缺口）：`if (_isDisposed) return;`
2. `await getAccessToken()` 续延恢复点（CI 29 红链的入口缺口，真实现走 secure storage/网络）：`if (_isDisposed) return;`
3. `await for` 事件循环顶：`if (_isDisposed || !isCurrentRequest())`（沿用本文件 `flushPending.applyPending` line ~1246 同款守卫）。
4. `finalizeRun` 入口：`if (_isDisposed || !isCurrentRequest() || sawTerminalEvent)`——sendMessage 全部收束路径的唯一写收口，与同函数 finally 块既有 `mounted &&` 门同语义。

### `mobile/lib/features/seed_library/presentation/providers/seed_library_provider.dart`（CI 29 抛点收口）

`SubscriptionsNotifier.loadSubscriptions` 三个异步缺口写回点 + `toggleSubscription` 两个同构缺口加 `if (!mounted) return;`（照同仓库 `GuestConversionController.recordValueSignal` 既有形制）。钉 A 证明这是 CI 29 Bad state 的直接来源：sendMessage 在 dispose 前的合法读已触发写回在途，仅守 sendMessage 续延无法消除该形态，必须在写回端收口——这正是 wt805「测试单侧修不彻底」的落点。

正常路径零变化：全部守卫只在 `_isDisposed`/`!mounted`（即 notifier 已被容器 dispose）时短路；容器存活时每个门都是一次布尔读。

## 3. 变异实证（逐门击穿，记录全部真实结果）

| 变异 | 结果 | 结论 |
|---|---|---|
| M1：仅去 token await 门 | 3/3 绿 | 钉 B 的「不逃逸」由 finalizeRun 门+catch 吸收兜住；token 门承载的是卡面「不得再触碰 provider 读/写」的字面保证（无门时续延在 dispose 后仍触碰 state 读并抛内部 Bad state 靠 catch 吸收）——保留 |
| M2b：去 loadSubscriptions 全部三道 mounted 门 | **钉 A 红复发**（`Bad state: Tried to use SubscriptionsNotifier after dispose`，逐字 CI 29 签名），控制组/钉 B 绿 | **loadSubscriptions 写回门是 CI 29 红的直接载荷，必需** |
| M3：去 finalizeRun `_isDisposed` 门 | 3/3 绿 | 逃逸面由既有 catch 吸收 + `sawTerminalEvent` 二次进入短路 + finally `mounted` 三重防线覆盖；该门为 dispose 不写的直接表达（并避免异常吸收路径的无谓工作），保留 |

## 4. 验证（全部本次实测，exit code 为 shell 实录）

| 面 | 命令 | 结果 | exit |
|---|---|---|---|
| 回归钉 | `flutter test test/features/chat/presentation/providers/chat_send_message_dispose_guard_test.dart` | 3/3 绿 | 0 |
| CI 29 原红测试 | `flutter test test/features/chat/presentation/providers/chat_value_signal_test.dart` | 5/5 绿（V3 测侧覆写保持不动，双层防御） | 0 |
| features/chat + features/seed_library 全量 | `flutter test test/features/chat test/features/seed_library` | **257/257** | 0 |
| unit chat 族（10 文件） | chat_notifier_actions/attachments/first_event_guard/stream、chat_provider×2、chat_state、chat_draft_store、chat_repository_history_filter、chat_stream_parsing、websocket_chat_service_v2 | **86/86** | 0 |
| widget/邻接面（10 文件） | chat_area_budget、chat_bubble_reduced_motion、chat_history_sheet_regression、chat_long_suggestion_reparent、chat_review_banner、chat_scroll、chat_wait_pulse_source、core_provider_keep_alive、group_chat_index_shift_reparent、task_chat_dormant | **34/34** | 0 |
| 其余 ChatNotifier 引用面（5 文件） | u02_contrast_hierarchy_rubric、token_refresh_coordinator、web_session_restore、u02_dual_mode_evidence、community_agent_provider | 44 绿（~8 skipped 为文件内既有 skip） | 0 |
| 静态 | `flutter analyze`（全 mobile） | 基线 `No issues found` → 修复后 `No issues found`（零新增；期间修掉自建测试 1 处 `require_trailing_commas`） | 0 |
| 格式 | `dart format`（3 个改动文件） | 无内容变化 | 0 |

## 5. 影响面与未触碰项

- 改动文件：`chat_provider.dart`（+4 活性门）、`seed_library_provider.dart`（+5 mounted 门）、新增回归钉测试 1 文件、本 receipt、DYNAMIC_ISSUES.md 状态列。
- 未触碰：`.env`、RF-06 冲突面（dashboard_screen/compact_status_bar/task_execution_screen）、五 Tab 路由、`subscriptionsProvider` 的测试侧覆写（wt807 交付保持原样）、proto/生成物/DB。
- worktree `backend/app/gen`、`mobile/lib/gen` 为 gitignored 本地构建拷贝，未入库。
- 残余风险：同构「provider build 内 unawaited 写回 + 无 mounted 门」模式仓库他处可能仍存在（本卡只收 CI 29 实证面）；已按卡面范围不扩散。

## 6. 交付

- fix commit：`db0916f6`（`fix(chat): FIX-547 sendMessage 续延 dispose 后活性守卫`，分支 `agent/v4/fix547`），**未 push**。台账状态列更新与本 receipt 补记为后续独立 commit（sha 不可自指）。
- DYNAMIC_ISSUES.md V3-FIX-547 行（OPEN 行）状态列改 `FIXED@<sha>`。
