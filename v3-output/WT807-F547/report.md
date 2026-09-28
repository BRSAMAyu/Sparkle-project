# WT807 · V3-FIX-547 修复报告

- 分支：`agent/wt807/fix547`（worktree `/Users/brsama/code/GitHub/wt807`，base main@1f62b36c）
- 修复 commit：**45336b1b**（`45336b1ba3ca4c97a231f10b68daabb5bbeda9d2`，`fix(tests): wt807 V3-FIX-547 chat_value_signal dispose 竞态修复`）
- 台账登记 commit：见 git log 第二笔（台账 FIXED@45336b1b + 本报告）
- 红线遵守：不 push、不碰运行栈、零产品码改动（`mobile/lib/` 未动）、零断言删除/跳过

## 1. 根因

CI 29 job 108772804580 唯一红 = `chat_value_signal_test.dart`「failed after test completion」（wt805 notes §2.3 栈取证）。本次在 wt805 定位基础上补全了机制链：

1. `subscriptionsProvider`（`mobile/lib/features/seed_library/presentation/providers/seed_library_provider.dart:696`）构建体里 **`unawaited(notifier.loadSubscriptions())`** fire-and-forget 自动加载。
2. `ChatNotifier.sendMessage`（`chat_provider.dart:1388`）无条件 `_ref.read(subscriptionsProvider)`；测试经 `_ContainerForwardingRef` 落在真容器上，首次读取即实例化 provider 并触发该续延。
3. `loadSubscriptions` 的完成路径在测试环境是**真网络失败**：`seedLibraryRepositoryProvider` → `apiClientProvider = Provider<ApiClient>(ApiClient.new)` → 真 Dio（`baseUrl: ApiEndpoints.baseUrl`、connect/receive timeout 10s/30s），测试容器无 override。`getMySubscriptions` 的 DioException 到达时长是**秒级不受控墙钟**（DNS/连接错误回包，CI 负载下可拖到秒级）。
4. 测试体 `await sendFuture; await _settle();`（固定 80ms）结束时续延往往未落地；teardown（LIFO）先 `container.dispose()`，续延随后写 `SubscriptionsNotifier.state` → `Bad state: Tried to use SubscriptionsNotifier after dispose` → 未处理异步错误 → 用例已结束后报红。本地 Dio 失败回包快（毫秒级），续延总在窗口内落地——与「CI-only 间歇红」定性吻合。

排除面（同链路逐一核查、均非本红）：`PersistentNotifier` 构建期 `unawaited(_loadState())`（完成路径是 mock SharedPreferences 内存读，微任务级确定）；`guestConversionControllerProvider` 构建同步、`recordValueSignal` 有 `mounted` 守卫且 mock prefs 微任务级；`chatStreamWithFirstEventGuard` 守卫计时器与 `streamTimeout` 均在流 done 时 disarm/cancel；`sendFuture` 经 `await for` 覆盖全部流消费，onDone 无残留续延。

## 2. 修法（最小改动 + 根因消除；FIX-544 同族形制：消除竞态窗口，不靠等待时长覆盖）

仅改 `mobile/test/features/chat/presentation/providers/chat_value_signal_test.dart`（+49/−2）：

1. **竞态窗口按构造消除**：`_buildHarness` 增 `subscriptionsProvider.overrideWith((ref) => SubscriptionsNotifier(_EmptySubscriptionRepository()))`。`_EmptySubscriptionRepository extends SeedLibraryRepository` 同签名覆写 `getMySubscriptions` 返回空页（零网络 I/O）。语义等价论据：sendMessage 只读 `.subscriptions` 列表，本环境真实现恒因网络失败为空——覆写后观测量（extraContext 组装、全部断言）逐位不变，唯「不受控网络失败续延」这一噪声源被拆除。
2. **`_settle()` 韧性改造**：固定 80ms 墙钟睡眠 → 8 轮 `Future<void>.delayed(Duration.zero)` 事件循环 drain。微任务链在任何 timer 触发前排空，轮数只需覆盖事件循环跳数（当前链深 ≤3，8 轮余量充足），对 runner 负载免疫——FIX-544「等待成立即返回、消负载假阴性」先例的确定性版。

未采纳「测试单侧修不彻底」顾虑的展开：wt805 建议的两支中，产品侧 mounted/取消保护（改 `mobile/lib/`）越本卡红线；测试容器生命周期治理支即本修法，且非「延迟 dispose」式时序补丁——悬挂续延本体被消除，dispose 先后不再有可撞窗口。产品 fire-and-forget 构建模式在产品容器（长命）语义下合法，无需动产品。

## 3. 验证证据

| 项 | 结果 |
|---|---|
| `flutter analyze test/features/chat/presentation/providers/chat_value_signal_test.dart` | No issues found（零新增） |
| 目标测试 `flutter test test/features/chat/presentation/providers/chat_value_signal_test.dart` | 5 测全过；**连跑 5/5 次全绿**（每次 `00:00 +5: All tests passed!`） |
| blast radius：同目录全量 `flutter test test/features/chat/presentation/providers/` | `00:01 +80: All tests passed!` |
| 台账体检 `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` | **通过**：379 行 V3-FIX 行裸管分布 `{8: 379}` 零畸形、ID 无重号、状态枚举合法、deep 抽检 FIXED@45336b1b 可达（rot 0）；唯一 warning 为幻影号 473（历史 commit message 既有问题，非本行引入，工具明示不阻断） |
| 负载模拟 | 未做：本地红本就不可构造（CI-only 形态，同 wt805 FIX-544 结论），以「竞态源按构造消除」论证替代 |

环境注记：新 worktree 缺 gitignored `mobile/lib/gen/`（proto 生成物），按 wt805 先例自主 worktree 拷贝（不入库）；flutter 工具链本地重生成 `mobile/lib/l10n/*.dart`（纯空行差异），已 `git checkout --` 还原，未入 commit。

## 4. 交付物

- 修复 commit：`45336b1b`（仅测试文件）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` line 419 → `FIXED@45336b1b（wt807 2026-09-28…）`
- 本报告：`v3-output/WT807-F547/report.md`
- 未 push（push-lock 遵守）；worktree 保留待主会话整合
