# 07 R2 复审·移动端长尾功能面（35 features）

> 全系统审查·第二轮｜切片 7｜基线 main@ca86bda8（worktree wt7）
> R1 基线：90daac8a（见 `round1/07-mobile-features.md`）；本轮聚焦：R1 修复验证 + 运行时/集成视角复审 + R2 修复波排产。
> 范围：galaxy / plan / insights / error_book / memory / focus 六个深审模块 + 35 目录长尾面。

---

## 1. R1 修复验证结论

R1 修复波以提交 **b3ef16f5**（`fix(integration): F7 — …`）集成。**注：round1 目录下实际不存在 `07-fixes.md` 文件**（其余切片有 01/04/05/06-fixes.md），修复内容以提交信息与 diff 为准，建议补齐该档案以保持审计线索一致。

| 项 | 验证方式 | 结论 |
|----|----------|------|
| **F7-01** 错题本显式 Demo 分支 + 错误态 | diff 核对 `error_book_provider.dart` 4 处（errorList / todayReviewList / errorStats / remediablePatterns）：`catch(_)` 静默回退全部移除，改为 `if (DemoDataService.isDemoMode)` 前置短路 + 真实路径直抛 | ✅ 落地。配套新增 7 个红-绿测试（`_ThrowingErrorBookRepository` 模拟离线/5xx） |
| **F7-05** memory 面板全量错误态 | diff 核对 `memory_panel_screen.dart`：7 个请求逐项 `settled()` 包装，新增 `partialError` 字段，部分失败渲染成功分区 + 非阻塞 `AppFeedback.error(memoryPanelLoadFailed)`（arb 中英 key 均已登记） | ✅ 落地，partial-settle 实现优于建议方案 |
| **F7-10** galaxy_model name 硬转型 | diff 核对：`name: json['name']?.toString() ?? ''`，与 id 的 P1-13 修法对齐；配套 `galaxy_model_parsing_test.dart` 缺 name 用例 | ✅ 落地（测试绿） |
| **F7-13** focus_repository:195 硬转型 | diff 核对：`rawContent is String ? … : toString()`，两字段皆缺/空时抛带上下文 `FormatException`（`on DioException` 外层可兼容） | ✅ 落地 |
| **F7-14** growth_dashboard fire-and-forget | diff 核对：`unawaited(...catchError(debugPrint))` | ✅ 落地（最小可接受修法；"refresh on next load" 补偿仍是注释承诺，见 R2-03） |

**测试验证**：`flutter test --concurrency=4 test/features/error_book` → **+11 全绿**（跑两遍确认稳定）；`test/features/galaxy/unit/galaxy_model_parsing_test.dart` → +2 全绿（含 F7-10 用例）。

**★F7-01 抽查：真实用户误开 Demo 模式是否有出口** —— 结论：**有出口，出口充分，残留面极小**：
- `isDemoMode` 的唯二来源：① 编译期 `--dart-define=DEMO_MODE=true`（`main.dart:115`，发布二进制不可达，属有意演示构建）；② 本地偏好 `demo_guest_mode_enabled`。
- 当前代码**不存在任何把该偏好写为 true 的路径**（R1 提到的 `loginAsDemoAccount` 已不存在，`auth_provider.dart` 中 7 处写入全部为 `false`）。残留仅限"从旧版本 app 升级后遗留的 true 偏好"。
- 即使偏好残留为 true：`checkAuthStatus()`（`auth_provider.dart:119`）对**任何持真实 token 的已登录用户强制 `isDemoMode = false`**，登录/注册/登出流程也全部复位为 false——真实账号永远有出口。
- 残留缺口（P3）：未登录 + 遗留偏好 = 匿名用户静默处于 Demo 数据且**无任何 UI 横幅/设置项可见或清除**（settings 中无 demo 指示器）。鉴于该偏好已无置 true 路径，实际风险随旧版本用户消亡而归零；建议在 settings 加一行只读"演示模式"指示即可彻底闭环。

**五项修复全部通过复核，质量良好（优于/等于建议修法），error_book 数据真实性缺陷已闭环。**

---

## 2. R2 集成复审发现表

复审视角：provider→repository→API 错误逐层传播、Isar 离线同步、跨模块导航。R1 已登记项只登记现状（不重报）。

| ID | 严重度 | file:line | 发现 | 证据 | 建议修法 |
|----|--------|-----------|------|------|----------|
| R2-01 | **P1** | `memory/presentation/screens/memory_settings_screen.dart:63-81, 275, 278+` | **记忆设置读取失败静默回退默认值 → 保存即覆盖真实服务端设置**。`loadSettings` 对 `getMemorySettings()`/`getPushSettings()` 失败均 `catch(_)` 回退**默认配置**（enabled:true、全部允许、medium）；表单以默认值填充，用户任何一次"保存"会把默认值 `updateMemorySettings` 写回服务端，真实设置被静默清空——与 F7-01 同类的"假数据冒充用户数据"，且带写回放大效应 | `} catch (_) {`<br>`  settings = MemorySettingsModel(enabled: true, allowPreferences: true, …)` | load  失败时进分区/整页错误态 + 重试（复用本屏已有 error 字段），**禁止**用默认值填充表单；仅当服务端确认无配置（404）时才用默认值 |
| R2-02 | P2 | `focus/presentation/providers/focus_statistics_provider.dart:257,304,352` + focus/presentation（全 UI 层） | **`errorMessage` 只写不读**：today/week/month 三处 catch 写入 `errorMessage`，但 focus 全部 screen/widget 无一消费（grep 零命中）。API 与本地 Isar 双失败时用户看到的是 0 分钟且无任何提示 | `errorMessage: e.toString()` ×3；UI 层 `errorMessage` 引用 = 0 | stats 屏（focus_statistics_screen）按 `errorMessage != null` 渲染错误横幅/重试；或直接删字段改 `AsyncValue` 错误通道 |
| R2-03 | P2 | `focus/presentation/providers/focus_statistics_provider.dart:477` + `mindfulness_provider.dart:379,409-410` | **F7-03 / F7-04 现状确认：均未修**（不在本轮 5 项修复单内）。`if (_localRepo == null) return null;` 三义压缩仍在；落库失败仍 `_clearPersistedSession()` + `state = const MindfulnessState()` 销毁可恢复会话（`loggingError` 仍被 410 行覆盖） | 同 R1 F7-03/04 证据 | 见排产第 1 项（本轮给出可执行修法） |
| R2-04 | P2 | `focus/data/repositories/focus_statistics_repository.dart:380-417` | **Isar"冲突解决"实为无调用方的死代码，且含 3 处硬转型**：`mergeServerSessions`（`['id'] as String`、`['duration_minutes'] as int`、`['start_time'] as String`）在 focus 模块内 **0 个调用方**（grep 证实）——服务端→本地合并从未发生；本地→服务端上行 sync（`sync()` 逐条 markAsSynced/markSyncFailed）健壮（逐条隔离失败 ✅），但"多设备合并"能力实际不存在 | `grep mergeServerSessions focus/` 仅定义处 1 命中 | 二选一：删除死方法；或接线到 `sync()` 尾部并防御解析（`as String?` + tryParse）。若产品定位单设备，删掉并同步删除"conflict resolution"注释 |
| R2-05 | P3 | `focus/presentation/providers/mindfulness_provider.dart:144` | **F7-17 现状确认：未修**。构造函数 `unawaited(_restoreSession())` 与 start() 理论竞态仍在 | 同 R1 | start() 入口加 `if (state.isActive) skip restore` 标志位，5 行内 |
| R2-06 | P3 | `plan/presentation/providers/plan_provider.dart:151-155`（+9 处调用） | **F7-16 现状确认：未修**。refresh 仍为串行 `loadPlans → loadActivePlans → invalidate(dashboard)`，每次写操作全量扇出 | 同 R1 | `Future.wait([loadPlans(), loadActivePlans()])` 一行改并行；或按操作类型定向刷新 |
| R2-07 | P3 | `insights/presentation/providers/growth_dashboard_provider.dart:25-36` | F7-14 修复后的残留：catchError 仅 debugPrint，注释承诺的"下次 load 对齐"依赖既有 refresh 路径，无显式补偿。可接受（本地乐观态 + 服务端最终一致），登记备忘 | `catchError((Object e) { debugPrint(...); })` | 维持现状即可；若做离线队列再补回滚 |
| R2-08 | 良好 | （链路验证） | **跨模块导航 id 链类型安全实测通过**：galaxy→learning-path/errors/chat 用 query param 字符串（`Uri(queryParameters:)` 天然 string 化）；galaxy_routes 对 `extra` 做 `is GalaxyDraftReviewRouteArgs` 类型检查、path 参数 null 时渲染 `galaxyInvalidNodeId` 错误屏；plan/task 详情用 pattern 保证的 `pathParameters['id']`；plan_routes 的 `extraMap?['plan_id']?.toString() ?? ''` 空值兜底 + `sprint_completion_screen.dart:75` 对空 planId 有 `trim().isEmpty` guard。`learning_path_task_path_navigation_test` + `router_deep_link_test` 全绿 | — | 无需动作 |
| R2-09 | 良好 | （链路验证） | **错误传播分层抽检通过**：insights 4 个 repository 的 9 处 `catch (_)` 全部是"包装后 rethrow"（`_extractDioMessage` 提取 detail），非吞错；memory 写链路 notifier 回滚乐观态后 rethrow → screen catch → `AppFeedback.error`，三层完整；plan sprint 系 provider catch 后写 state.error 且 `sprint_history_screen:61` 有对应渲染；error_book 列表/统计 `AsyncValue.when(error:)` 渲染 `CompactErrorCard`/`_buildErrorState`。六模块 provider 层**未再发现静默吞错回退**（memory_settings 一处除外，见 R2-01） | — | — |
| R2-10 | P3（测试债） | `test/features/plan/presentation/screens/learning_portfolio_screen_test.dart:146` | "pull-to-refresh refreshes portfolio data" **确定性红**（单跑复现：`fetchCalls` 恒为 1）。protobuf 解锁后才首次真正运行（R1 时该 suite 编译失败被遮蔽）。屏幕实现（`SparkleRefreshIndicator`→标准 `RefreshIndicator` + `ref.refresh(.future)`）静态看正确，疑为 fling 手势在测试环境未产生足够 overscroll 的测试侧问题，但需真机下拉一次确认非产品缺陷 | `expect(fetchCalls, greaterThanOrEqualTo(2))` 实际 1 | 测试改 `tester.drag(list, const Offset(0, 300))` 分步拖拽；同时排入多平台实测清单人工验证下拉刷新 |

**离线/弱网行为总结**：上行同步（focus `sync()`）健壮——逐条隔离失败、`Connectivity` 触发重试（R1 已验证）；下行合并不存在（R2-04）；memory 面板弱网可用性已由 F7-05 partial-settle 修复改善（实测部分分区失败仅非阻塞提示）；Isar 库初始化失败时 focus 仍依赖 R2-03 的修复消除"假已保存"。

---

## 3. ★R2 修复波排产建议（UI/UX 阶段与修复波直接输入）

### 3.1 输入清单与现状核对（R1 剩余 11 项 + 新增 4 项）

R1 共 17 项：已修 5（F7-01/05/10/13/14）+ 1 项由独立提交闭环（F7-02 protobuf 锁 6.1.0，`9332592a` + `3b339db8` 根因闭环）→ **剩 11 项未修**（任务书按 10 项计，差异为 F7-06/07/08 三项批量债务与其他项的口径并集）。R2 新增：R2-01（P1）、R2-02、R2-04、R2-10。模式扫描债务规模复核（R1 同口径 35 目录）：硬编码颜色 **243 处/32 文件**（R1 记 227，微增 16，同 32 文件）、fontSize **884 处**（持平）、中文硬编码 **163 文件/1712 行**（R1 口径）、空 `catch (_) {}` **11 处**（持平）。

### 3.2 排产总表（按 用户可见收益 × 修复成本 排序）

| 排序 | 项 | 用户可见收益 | 成本 | 批次建议 |
|------|-----|-------------|------|----------|
| 1 | **R2-03（=F7-03+F7-04）专注数据假保存/丢失** | 高：数小时专注时长静默丢失且被告知"已离线保存"，直接伤害核心卖点 | 小（2 文件 ~40 行 + 2 测试） | R2 修复波·P0 |
| 2 | **R2-01 记忆设置默认值覆盖真实设置** | 高：用户隐私授权设置被静默重置，合规敏感 | 小（1 文件 ~30 行 + 1 测试） | R2 修复波·P0 |
| 3 | **F7-09 33 unused_import + 2 deprecated Radio + 2 unused** | 中：Radio deprecated API 在 Flutter 升级后**变编译错误**（定时炸弹）；清零后可收紧 analyze 门槛 | 极小（纯机械，1 个 PR） | R2 修复波·P0（搭车批） |
| 4 | R2-02 focus errorMessage 死端 | 中：统计失败至少可见 | 小 | R2 修复波·P1 |
| 5 | R2-10 portfolio 下拉刷新红测试 | 中：解锁 plan 测试全绿基线 | 小（测试文件 1 处手势改写） | R2 修复波·P1 |
| 6 | F7-15 11 处空 catch | 低-中：可观测性 | 极小 | P1 机械批（与 3 同 PR 系） |
| 7 | F7-16 plan 写操作刷新扇出 | 中：每次写操作 2 串行请求 + invalidate 链 → 卡顿感 | 极小 | P1 |
| 8 | F7-11 6 处 ConsumerWidget 局部 TextEditingController | 低 | 极小 | P1 机械批 |
| 9 | R2-04 mergeServerSessions 死代码+硬转型 | 低（删） / 中（接线） | 极小（删）/ 中（接线+防御解析） | P1（建议先删，需要多设备时再实现） |
| 10 | F7-12 4 文件命名偏离 | 低（纯规范） | 小（动 imports/路由引用） | P2 机械批 |
| 11 | F7-17 restore 竞态 | 低（窗口极小） | 极小 | P2 |
| 12 | R2-07 growth_dashboard 补偿日志 | 低 | 零（维持现状） | 记账不排产 |
| 13 | Demo 模式只读指示器 | 低 | 极小 | P2（与 UI/UX 阶段合并） |
| 14 | 批量债务 243 色 / 884 字号 / 1712 行中文 | 中（品牌一致性、国际化） | 大 | 见 3.4 分批策略（UI/UX 阶段主线） |

### 3.3 前 3 项可直接执行的修法（文件级）

**① R2-03：专注会话假保存/数据丢失（P0，~半天）**
- `mobile/lib/features/focus/presentation/providers/focus_statistics_provider.dart:477`
  - `if (_localRepo == null) return null;` → 改为抛出：`throw StateException('local focus repository unavailable');`；返回类型 `Future<LoggedFocusSession?>` 保持，让 `MindfulnessNotifier` 的既有 catch（`mindfulness_provider.dart:400` `resultMessage = S.focusSaveFailed`）接管，杜绝"未保存却提示已离线保存"。更优：引入 sealed result `FocusSaveResult{synced, offlineSaved, failed(reason)}`，`MindfulnessStopResult` 按变体映射文案。
- `mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart:379-410`
  - 379 行 catch 块内：**不执行**后续 `_clearPersistedSession()`——把 405-410 行的 `_timer?.cancel()…_clearPersistedSession(); state = const MindfulnessState();` 整段移入 try 成功路径（或 catch 后 `return MindfulnessStopResult(savedLocally: false, …)` 提前退出），保留 SharedPreferences 快照供下次启动 `_restoreSession()` 恢复重试；删除死代码 `loggingError` 赋值或改为成功后清理。
  - 验证：新增 widget test——mock 本地落库抛错 → 断言 prefs 快照仍在 + 文案为 `focusSaveFailed`；重启 notifier 断言 `_restoreSession` 恢复。

**② R2-01：记忆设置默认值覆盖（P0，~2 小时）**
- `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart:63-81`
  - 删除两处 `catch (_) { settings = MemorySettingsModel(…) }` 回退，改为失败时 `state = state.copyWith(isLoading: false, error: '$e')`（本屏已有 error 通道，228 行的 GoRouter 兜底 catch 不受影响）；build 中已有 error 渲染路径时补"重试"按钮复用 `loadAll` 入口。**默认值仅在 API 返回 404（无配置）时使用**：给 `MemoryApiService.getMemorySettings` 加 `DioException.status == 404` 判定传入。
  - 验证：`test/features/memory` 新增用例——getMemorySettings 抛错 → 断言渲染错误态且 `_saveSettings` 入口禁用（或保存前 `state.settings == null` guard 生效，见 272 行已有 guard，只需保证 settings 不再被默认值填充）。

**③ F7-09 + F7-15 机械清零批（P0 搭车，~1 小时）**
- 33 处 unused_import：按 `flutter analyze` 输出逐条删除（tools 11 / seed_library 4 / translation 2 / calendar 2 / insights 2 / memory 2 / photon/cognitive/mirofish/theater/community 各 1），多数为 `app_localizations.dart`/`i18n_service.dart` 残留。
- `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart:114-115`：Radio 迁移 `RadioGroup`（Flutter 3.32+ 废弃 API，升级即编译错误）。
- 11 处 `catch (_) {}`：逐处加 `debugPrint('… ignored: $e')` + 一行注释说明为何安全（清单见 R1 F7-15）。
- 验证：`flutter analyze lib/features` warning 从 37 → ≤4（预期仅剩 chat 一条 unused_element 归 6 号切片 + feed_post_card 参数项）；`flutter test --concurrency=4` 抽跑受影响 feature。

### 3.4 令牌化批量债务分批策略（243 色 / 884 字号 / 1712 行中文）

**核心原则：先立守卫与基线棘轮（ratchet），后批量燃烧；每批必须有机械可验证的完成判据。**

**第 0 批（守卫先行，1 个 PR）**：在 `scripts/rule_guard_manifest.tsv` 新增 `check_ui_design_tokens` 守卫——扫描 `lib/features/**` 的 `Color(0x`、`fontSize:`，对照**冻结基线清单**（当前 32 文件/243 处、884 处），只拦**新增**违规（棘轮模式，允许只减不增）；i18n 守卫同口径把 EXEMPT_FILES 冻结。无守卫的燃烧批次会被新代码回灌（R1→R2 期间颜色已从 227 涨到 243，即为实证）。

**第 1-N 批（燃烧），按"用户触点频次 × 文件内密度"切批**：
- 切批维度：**按 feature 为批次单位、每批 4-6 个文件、单批 ≤60 处替换**（经验上单批 review 时间 <1h，冲突面 <1 天）；同 feature 内先 screen 级文件、后 widget/painter 级。
- 批次顺序：① 六深审模块（insights→error_book→memory→plan→focus→galaxy，用户高频）；② 高密度 Top 文件（`visual_element_palette.dart` 44 处、`profile_screen.dart` 20、`star_map_painter.dart` 19、`learning_portfolio_screen.dart` 15——painter/palette 类**不迁移**，改为集中登记为设计资产常量文件并 import `core/design` 语义别名）；③ 其余长尾 feature；④ 中文 1712 行按 feature 分批走 `lib/l10n/i18n_batch_replace.py`，EXEMPT_FILES 清零后将 `check_i18n_coverage.py` 从"只拦新文件"升级为全量强校验。
- 字号批（884 处）放在颜色批之后单独跑：`DS.bodyMedium.copyWith(fontSize:13)` 类混用需要按语义归档到 `DSTextStyle` 家族，机械替换率低、需目检比例高，每批缩到 4 文件。

**每批验证判据（DoD）**：
1. `check_ui_design_tokens` 计数严格下降且无新增（守卫绿）；
2. `flutter test --concurrency=4 test/features/<该feature>` 全绿；
3. `flutter analyze` 该 feature 无新增 warning；
4. 屏幕截图前后对照（UI/UX 审查框架的 5 层模型走查，可并入多平台实测轮）——这是唯一能拦住"令牌语义选错"（如 brandPrimary 误替换语义色）的手段，机械工具验证不了视觉正确性。

**排期口径**：颜色 243 处 ≈ 6-8 批；字号 884 处 ≈ 10-12 批；中文 1712 行 ≈ 8-10 批；合计 25-30 个小 PR，按每工作日 2-3 批推进约 2-3 周净投入，可与 UI/UX 视觉审查长期迭代并行流水化。

---

## 4. 测试执行记录

环境：worktree wt7 @ ca86bda8，`flutter pub get` 成功（protobuf ^6.1.0 override 已在 `9332592a` 落库，gen/ 产物兼容）。全部命令 `--concurrency=4`，一次一个命令（内存纪律遵守）。

| 套件 | 结果 |
|------|------|
| `test/features/error_book` | **+11 全绿**（跑 2 遍稳定；含 F7-01 新增 7 个红-绿用例） |
| `test/features/galaxy/unit/galaxy_model_parsing_test.dart` | +2 全绿（含 F7-10 缺 name 用例） |
| `test/features/galaxy`（全套） | **+93 全绿** |
| `test/features/memory` | **+48 全绿** |
| `test/features/focus` | +3 全绿 |
| `test/features/plan` | +21 / -1（唯一失败 `learning_portfolio_screen_test` 下拉刷新，单跑复现 → R2-10） |
| `test/features/insights` | +1 / -1（失败为 `insights overview …` **R1 已登记基线红**，未重报） |
| `test/widget/learning_path_task_path_navigation_test.dart` + `test/app/router_deep_link_test.dart` | +3 全绿（导航链验证） |
| `flutter analyze --no-pub lib/features` | 37 warnings（33 unused_import + 1 unused_element(chat,属切片6) + 1 unused_element_parameter + 2 deprecated Radio）→ F7-09 现状未修 |
| 模式复扫（R1 同口径 35 目录） | 颜色 243/32 文件（R1:227，+16 回灌）、fontSize 884、空 catch 11、F7-11/12 文件均原样存在 |

---

*复审员：07｜切片：移动端·长尾功能面｜日期：2026-09-18｜基线 ca86bda8*
