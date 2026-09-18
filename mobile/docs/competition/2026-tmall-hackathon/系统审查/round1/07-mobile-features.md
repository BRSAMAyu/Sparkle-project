# 07 移动端·长尾功能面审查报告（35 个 features）

> 全系统审查·第一轮｜切片 7｜基线 main@90daac8a（worktree wt7）
> 范围：`mobile/lib/features/` 除核心 7 个（splash/onboarding/auth/home/chat/task/settings）外的全部 35 个目录，共 599 个 dart 文件。
> 深审目录：galaxy、plan、insights、error_book、memory、focus。

---

## 1. 总评

长尾功能面整体工程质量**中上**。核心状态机（galaxy_provider 1373 行）展现了成熟的水准：requestId 防竞态、`_noChange` sentinel 解决 copyWith 无法置 null 的经典问题、dispose 全量清理（Timer/StreamSubscription/Listener/StreamController）、SSE 断线重连；JSON 解析在 galaxy/plan repository 一线采用防御式风格（`as num?` + `??` 默认值）；错误展示统一走 `AppFeedback.error` + `UserFacingError`；路由参数做了类型检查与 null 兜底（带 P1-12/P1-13 修复痕迹）。

主要风险集中在三处：
1. **error_book 的"静默 demo 兜底"策略**——真实 API 失败时向用户展示假错题且无任何错误提示，是数据真实性缺陷；
2. **冻结基线上移动端测试基建不可执行**——gen/ 产物按 protobuf 6.1.0 生成而 pubspec 仅约束 `^6.0.0`（无 override），所有引用 gen/ 的测试 suite 编译失败（与"6.1.0 override 已修复"的已知问题记录不符，基线上没有该修复）；
3. **批量规范债务**——227 处硬编码颜色、884 处硬编码 fontSize、163 文件 1712 行中文硬编码（i18n 守卫只拦新文件、存量豁免），无治理守卫覆盖 UI 令牌违规。

未发现 P0（崩溃/白屏/功能完全不可用）级问题。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| F7-01 | **P1** | `mobile/lib/features/error_book/data/providers/error_book_provider.dart:117-146, 189-215, 233-253` | 用户离线/后端 5xx/网关超时打开错题本：列表、今日复习、统计三个 provider 均 `catch (_)` 后静默返回演示数据，UI 无任何错误态。用户会把 demo 错题当作自己录入的真实错题（复习打卡、掌握度统计全部失真） | `} catch (_) {`<br>`  final items = _demoErrorRecords().where((item) {...`<br>`} catch (_) {`<br>`  ... id: 'demo_review_1', ...`<br>`} catch (_) {`<br>`  final items = _demoErrorRecords();` | 仅在 `DemoDataService.isDemoMode` 为真时走 demo 分支（与 focus_repository 的写法对齐）；真实请求失败时抛出让 UI 渲染错误态/重试。涉及 4 处：errorList(117)、todayReviewList(189)、errorStats(233)、remediablePatterns(36，回退空列表尚可接受但同样吞掉了错误) |
| F7-02 | **P1** | `mobile/pubspec.yaml:91` + `mobile/lib/gen/*`（生成产物） | 冻结基线 main@90daac8a 上运行 `flutter test`：所有 import `package:sparkle/gen/*.pb*.dart` 的测试 suite 编译失败。gen/ 由 proto 工具链按 protobuf **6.1.0** 运行时生成（`$_createMessage` 新签名），而 pubspec 仅 `protobuf: ^6.0.0` 且 `dependency_overrides` **无 protobuf 条目**，lock 解析 6.0.0。6 个深审目录合计 **24 个 suite loading failed / 17 通过**。注：已知问题清单中"protobuf 6.1.0 override 已修复"与基线不符（主仓库 mobile/pubspec.yaml 同样无 override、lock 同样 6.0.0，主仓库跑测试应同样失败——属基线级漂移，非本 worktree 环境问题） | `pubspec.yaml`：<br>`  protobuf: ^6.0.0`<br>`pubspec.lock`：<br>`    version: "6.0.0"`<br>编译错误：<br>`The argument type 'GeneratedMessage Function()' can't be assigned to the parameter type 'MemoryItem Function()'` | ```diff<br>--- a/mobile/pubspec.yaml<br>+++ b/mobile/pubspec.yaml<br>@@ dependency_overrides @@<br>+  protobuf: 6.1.0<br>```<br>或将 proto 工具链生成所用的 protobuf 运行时版本锁回 6.0.0，使 gen 产物与约束一致；修复后需 CI 守护"生成器运行时版本 ≤ app 约束版本" |
| F7-03 | P2 | `mobile/lib/features/focus/presentation/providers/focus_statistics_provider.dart:469` + `mindfulness_provider.dart:313-378` | `saveSession` 返回 null 有三种含义被压成两种：`_localRepo == null` 时**什么都没保存**就返回 null；同步失败时本地已保存返回 null。调用方 `MindfulnessNotifier.stop()` 把 null 一律解读为"离线已保存"（`S.focusOfflineSaved`）并展示给用户。当 Isar 本地库初始化失败（`localDatabaseProvider` 抛错导致 build 中 `_localRepo` 未赋值）时，用户专注数小时的时长数据静默丢失且被告知"已离线保存" | `if (_localRepo == null) return null;`<br>…<br>`savedLocally = response != null;`<br>`resultMessage = S.focusOfflineSaved;` | `saveSession` 返回类型改为 sealed result（`Saved{synced}` / `OfflineSaved` / `NotSaved(reason)`），或在 `_localRepo == null` 分支抛异常走调用方 catch 的 `S.focusSaveFailed` 提示 |
| F7-04 | P2 | `mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart:379-410` | 专注结束、`saveSession` 抛异常（本地落库失败）时：catch 设置 `loggingError` 后，代码继续执行 `_clearPersistedSession()`（销毁 SharedPreferences 中的会话快照）并把 `state` 重置为空——会话数据彻底不可恢复，且 380 行设置的 `loggingError` 立即被 410 行 `state = const MindfulnessState()` 覆盖（死代码） | `} catch (e) {`<br>`  state = state.copyWith(loggingError: e.toString());`<br>`  resultMessage = S.focusSaveFailed(e.toString());`<br>`}`<br>`…`<br>`await _clearPersistedSession();`<br>`state = const MindfulnessState();` | 落库失败时保留持久化会话（不调用 `_clearPersistedSession`），下次启动由 `_restoreSession` 恢复后重试提交；`state` 重置延后到成功路径 |
| F7-05 | P2 | `mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart:99-128` | 记忆面板 `loadAll` 用 `Future.wait` 并发 7 个请求（preferences/goals/episodic/scenes/foresight/commitments/conflicts），**任一失败整个面板进入全量 error 态**，已成功的 6 类数据不渲染；弱网下面板可用性差 | `final results = await Future.wait([`<br>`  _service.getPreferences(),`<br>`  … 7 个 …`<br>`]);`<br>`} catch (e) {`<br>`  state = state.copyWith(isLoading: false, error: '$e');` | 改用 `Future.wait(..., eagerError: false)` 或逐项 `AsyncValue.guard`，state 按分区记录成功/失败，分区级错误态+重试 |
| F7-06 | P2（组） | 全 35 目录，227 处 / 32 文件 | 硬编码 `Color(0x…)` 绕过 `core/design` 令牌体系。Top：`visual_elements/…/visual_element_palette.dart`(44)、`user/…/profile_screen.dart`(20)、`galaxy/…/star_map_painter.dart`(19)、`user/…/avatar_selection_dialog.dart`(16)、`plan/…/learning_portfolio_screen.dart`(15，整个文件自带 15 个 `_portfolioXxx` 私有色常量) | `const _portfolioMint = Color(0xFFE7F4EA);`<br>`const _portfolioCream = Color(0xFFF7EFE3); …` | painter/palette 类（CustomPainter 调色板）可保留但应集中登记为设计资产；screen/widget 级硬编码迁入 `core/design/tokens(_v2)`；`scripts/rule_guard_manifest.tsv` 目前**无** UI 令牌守卫（已有 I18N 守卫），建议新增 `check_ui_design_tokens` |
| F7-07 | P2（组） | 全 35 目录，884 处 `fontSize:` | 硬编码字号绕过排版令牌。Top：`visual_elements_screen.dart`(35)、`achievement_detail_screen.dart`(25)、`group_chat_bubble.dart`(21)、`achievement_list_screen.dart`(21)、`calendar_stats_screen.dart`(20) | `style: DS.bodyMedium.copyWith(fontSize: 13)` 类混用随处可见 | 同 F7-06，随令牌守卫一并治理；优先收敛到 `DSTextStyle` 家族 |
| F7-08 | P2（组） | 全 35 目录，163 文件 / 1712 行含中文字面量 | 中文硬编码存量。`scripts/guards/check_i18n_coverage.py` 策略为"只拦含中文但未 import i18n 的**新**文件，EXEMPT_FILES 豁免存量"——守卫通过≠已 i18n，1712 行存量被策略性放过（arb 机制 app_zh/app_en 完备，具备治理条件） | 守卫逻辑注释：`trusting that files already wired to the i18n system handle their strings properly` | 按 feature 分批抽取进 `.arb`（`lib/l10n/i18n_batch_replace.py` 已有批量工具）；将 EXEMPT_FILES 清零后把守卫升级为全量强校验 |
| F7-09 | P2（组） | features 内 35 条 analyze warning | `flutter analyze`：33 处 `unused_import`（多为 `app_localizations.dart`/`i18n_service.dart` 残留，分布 tools(11)/seed_library(4)/translation(2)/calendar(2)/insights(2)/memory(2)/photon(1)/cognitive(1)/mirofish(1)/theater(1)/community(1)）+ 1 处 `unused_element_parameter`（`community/presentation/widgets/feed_post_card.dart:265`）+ 2 处 deprecated Radio API（`user/presentation/widgets/traits_coldstart_questionnaire.dart:114-115`，Flutter 3.32+ `groupValue/onChanged` 已废弃，应迁移 `RadioGroup`） | `warning • Unused import: 'package:sparkle/l10n/app_localizations.dart' • lib/features/tools/presentation/widgets/breathing_tool.dart:17:8` | 批量删除 unused_import；Radio 迁移 RadioGroup（deprecated API 在后续 Flutter 版本会移除，届时编译失败） |
| F7-10 | P3 | `galaxy_model.dart:195`（`shared/entities/`，galaxy 深审连带） | `GalaxyNodeModel.fromJson` 中 `name: json['name'] as String` 为硬转型；id 同类问题已有 `// P1-13 fix: null-safety for id field` 修复而 name 未修。后端 DB `name nullable=False` + Pydantic `name: str` 必填，契约内安全，但经网关缓存/旧版本响应时缺字段会抛 TypeError 且无上下文 | `name: json['name'] as String,` | `json['name']?.toString() ?? ''` 或带字段名抛 `FormatException` |
| F7-11 | P3（组） | `calendar/…/daily_detail_screen.dart:753`、`community/…/friends_screen.dart:896`、`community/…/group_tasks_screen.dart:293`、`community/…/checkin_interaction.dart:263`、`goal/…/goal_detail_page.dart:827`、`seed_library/…/seed_library_detail_screen.dart:1019` | ConsumerWidget（Stateless 系）方法体内局部创建 `TextEditingController` 用于 bottom-sheet/对话框，从不 dispose。低危（ChangeNotifier 随树 GC），但违反 flutter_lints 最佳实践 | `final titleController = TextEditingController(text: event.title);`（方法内局部变量） | 迁移 StatefulWidget 持有并在 dispose 释放，或用后 `controller.dispose()` |
| F7-12 | P3（组） | `insights/presentation/pages/learning_dashboard_page.dart`、`growth_chronicle_page.dart`、`goal/presentation/pages/goal_detail_page.dart`、`user/presentation/screens/profile_transparent.dart` | screen 命名规范偏离：前三个为路由挂载的 screen 级组件（`insights_routes.dart:75,91`、`goal_routes.dart:49` 已挂载）但用 `pages/ + _page.dart` 后缀；`profile_transparent.dart` 类名为 `ProfileTransparentScreen` 却无 `_screen.dart` 后缀 | `child: const LearningDashboardPage(),` | 统一为 `presentation/screens/xxx_screen.dart` |
| F7-13 | P3 | `focus/data/repositories/focus_repository.dart:195` + 全仓无调用 | `(payload['content'] ?? payload['guidance']) as String` 对真实 API 响应字段硬转型（两 key 皆缺时抛 TypeError，且外层 `on DioException` 捕不住）；且 `getLLMGuidance` **无任何调用方**（死代码） | `return (payload['content'] ?? payload['guidance']) as String;` | 删除死方法或加防御解析（`as String?` + 兜底文案） |
| F7-14 | P3 | `insights/presentation/providers/growth_dashboard_provider.dart:29` | `updateEntryStatus` 中 `ref.read(...).updateChronicleEntryStatus(...)` fire-and-forget，Future 未 catch，失败时产生 unhandled exception（注释声称"refresh on next load if it fails"但未实现补偿逻辑） | `// Persist to backend (fire-and-forget; refresh on next load if it fails)`<br>`ref.read(growthDashboardRepositoryProvider).updateChronicleEntryStatus(entryId, status);` | `unawaited(...catch(...))` + 失败时回滚本地状态或触发 refresh |
| F7-15 | P3（组） | 11 处 `catch (_) {}` 空体 | 空吞异常：`aurora_core_session_sheet.dart:138,179`、`aurora_telemetry_service.dart:76`、`mock_community_repository.dart:807`、`accountability_invite_flow.dart:61`、`translator_tool.dart:269`、`knowledge_integration_service.dart:103`、`translation_history_provider.dart:82`、`modeling_chat_screen.dart:808`、`visual_element_card.dart:429,1014` | `} catch (_) {}` | 至少 `debugPrint` 或加注释说明为何可安全忽略 |
| F7-16 | P3 | `plan/presentation/providers/plan_provider.dart:80-155` | 每个写操作（create/update/delete/activate/deactivate/setPrimary/archive/restore）成功后都 `refresh()` = `loadPlans + loadActivePlans + invalidate(dashboard)`，即**单次用户操作触发 2 个列表请求 + dashboard 失效链**；构造函数还额外立即发 `loadPlans + loadActivePlans` | `Future<void> refresh() async {`<br>`  await loadPlans();`<br>`  await loadActivePlans();` | refresh 合并为单方法内并行 `Future.wait`，或按操作类型定向刷新 |
| F7-17 | P3 | `focus/presentation/providers/mindfulness_provider.dart:144,467` | 构造函数 `unawaited(_restoreSession())` 异步恢复 state，与 UI 立即调用 `start()` 存在理论竞态（恢复完成覆盖新会话）；窗口极小，现实风险低 | `MindfulnessNotifier(...) { unawaited(_restoreSession()); }` | start() 内若已 active 则跳过恢复写入，或用标志位互斥 |

---

## 3. 模式扫描统计总表

| 扫描项 | 命中规模 | 分布/典型 | 定级 |
|---|---|---|---|
| 硬编码 `Color(0x` | 227 处 / 32 文件 | top: visual_element_palette(44)、profile_screen(20)、star_map_painter(19) | P2 组（F7-06） |
| 硬编码 `fontSize:` | 884 处 | top: visual_elements_screen(35)、achievement_detail(25) | P2 组（F7-07） |
| Text() 内中文硬编码 | 163 文件 / 1712 行含中文字面量 | i18n 守卫存量豁免策略性放过 | P2 组（F7-08） |
| `catch (e) {}` 空体 | 0 处 | — | 良好 |
| `catch (_) {}` 空体 | 11 处 | aurora/community/tools/translation/user/visual_elements | P3 组（F7-15） |
| catch(_) 静默 demo 兜底 | error_book 4 处 provider | 数据真实性混淆 | **P1**（F7-01） |
| `!`/`as String` 硬转型（真实 API 路径） | 少量：galaxy_model name、focus_repository:195；demo 数据路径若干 | 契约内风险低 | P3（F7-10/13） |
| Timer.periodic 无 cancel | 0 处 | 全部有 cancel/dispose | 良好 |
| TextEditingController 无 dispose | 6 文件（ConsumerWidget 局部创建） | calendar/community/goal/seed_library | P3 组（F7-11） |
| async gap 后无 mounted 检查 | analyze 未报 use_build_context_synchronously；抽查 review_screen/memory/galaxy 均有 `if (!mounted) return;` | — | 良好 |
| screen 命名偏离 `_screen.dart` | 4 文件 | insights×2、goal×1、user×1 | P3 组（F7-12） |
| TODO/FIXME/HACK | 仅 2 处 | community_repository.dart:1435、group_chat_bubble.dart:193 | 良好 |
| analyze warning（features 内） | 35 条（33 unused_import + 2 deprecated） | tools 最多（11） | P2 组（F7-09） |

---

## 4. 验证良好清单

- **galaxy_provider.dart**（1373 行）：`_layoutRequestId` 递增号防过期响应竞态；`_noChange` sentinel 让 copyWith 支持可空字段置 null；dispose 中 Timer×3/StreamSubscription/ValueListener/StreamController 全量清理；SSE 断线 5s 重连（`_scheduleEventsReconnect`）；`loadGalaxy` 区分阻塞/后台刷新两种错误策略（后台失败不打断已有图渲染）。
- **galaxy 路由与导航**：`galaxy_routes.dart` 对 `state.extra` 做类型检查、path 参数 null 兜底（P1-12/P1-13 修复痕迹）；`galaxy_screen.dart` 有空态面板、错误面板、首帧 loading 防闪烁 guard。
- **galaxy/plan repository JSON 解析**：统一 `as num?`/`as String?` + `??` 默认值防御式风格，无裸强转。
- **plan 错误处理**：screens 统一 `AppFeedback.error(context, UserFacingError.from(e))`；`planDetailProvider` 的 30s keepAlive timer 正确 `ref.onDispose(timer.cancel)`。
- **insights/learning_path_repository.dart**：demo 分支、`ApiResponseParser` 包装解析、`_extractDioMessage` 提取后端 detail/message、`selected_related_node_ids` 以 query 数组传递与后端 FastAPI `Query(default_factory=list)` 契约兼容（Dio 默认 ListFormat.multi）。
- **error_book 写链路**：`ErrorOperations` notifier 每次 create/update/delete/submitReview 后 invalidate 列表/统计/galaxy 并递增 `galaxyRefreshTriggerProvider`；`review_screen._handleReview` mounted/context.mounted 检查完整、失败有 `ebReviewFailed` 反馈；`_basePath='/errors'` 与后端 `error_book.py` 前缀一致。
- **focus 离线优先**：`FocusStatisticsRepository`（Isar）本地落库 → 即时同步 → 失败留待 `Connectivity.onConnectivityChanged` 触发 `sync()` 重传；`MindfulnessNotifier` 会话持久化/崩溃恢复（`_persistSession`/`_restoreSession`）字段级 tryParse 防御完整。
- **memory 面板**：provider 创建即 `unawaited(loadAll())` 一次、RefreshIndicator/重试按钮复用同一入口，无重复请求；notifier 各写操作均有 `if (!mounted) return;` 守卫。

---

## 5. 测试执行记录

1. **环境准备**：`flutter pub get` 成功（172 packages 版本约束提示为常规噪音）。
2. **flutter analyze**（全仓）：6818 issues，绝大多数为 `third_party_plugins/`（vendored fork）与 `tool/` 的 info 级；**features 范围内 35 条 warning + 2 条 error**。2 条 error 为 `chat/data/services/{plan_review,review}_grpc_service.dart` 的 `uri_does_not_exist`（gen 产物漂移，归 6 号切片，本切片不展开定性）。
3. **flutter test（6 个深审目录）**：`flutter test test/features/galaxy test/features/plan test/features/insights test/features/error_book test/features/memory test/features/focus` → **+17 通过 / -24 失败**。24 个失败全部为 **loading failed（编译失败）**，根因 F7-02：gen/ 产物按 protobuf 6.1.0 生成 vs lock 解析 6.0.0。不引用 gen/ 的 suite（+17）全部通过。
4. **环境事件（如实记录，非代码改动）**：为解除测试阻塞尝试 `make proto-gen`——因本机 Xcode license 未接受 + docker 镜像 `sparkle/proto-toolchain:latest` 不存在，两次失败；第二次 host fallback 运行将 git-ignored 的 `mobile/lib/gen/` 清空且未成功重建。已从主仓库 `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/gen/`（同一基线 commit，27 个产物文件，`GetArbitrationQueueRequest` 等新 RPC 齐备）原样拷贝恢复。恢复后测试结论即上述第 3 条（protobuf 运行时漂移依旧，证明其为基线真实状态而非本 worktree 环境问题）。
5. **前后端契约抽查**：galaxy `knowledge_nodes.name`（DB nullable=False + Pydantic 必填）、learning-paths `selected_related_node_ids`（FastAPI Query 数组）、error-book 路由前缀 `/errors` 与 `/error-book`——均一致，未发现字段对齐缺陷。

---

*审查员：07｜切片：移动端·长尾功能面｜日期：2026-09-18*
