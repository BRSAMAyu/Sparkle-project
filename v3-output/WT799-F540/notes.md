# WT799 · V3-FIX-540 实录（快车道 skip 后 FirstActionCard 间歇缺失）

- 分支 `agent/node-b/wt799/f540`（基于 main @ ae001069，V3-FIX-507 闭账）；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt799-f540`。
- 面内约束遵守：无 flutter run 真机/模拟器；未触运行栈/ns001；未 push；未改台账。

## 根因（代码亲证，5 个失效面叠加，非单点）

1. **进程级缓存（主根因）**：`firstActionStateProvider`（`mobile/lib/features/journey/data/repositories/first_action_repository.dart`）是非 autoDispose 的 FutureProvider——首次 fetch 后整个进程生命周期缓存。注册落地 soft-wall dashboard（A2a 5/5）在 goal 落库**前**挂载 FirstActionCard 并 fetch（goal=null 被缓存，包括失败态 AsyncError）；此后任何重挂载都读旧缓存。
2. **写链不失效**：快车道 `_handleFastPathSubmit`（goal 落库点）只 invalidate 4 个 profile 面 provider；modeling `_finish`（skip 后路由点）只 invalidate `profileContextProvider`——均不含 first-action 投影。
3. **N-4 注册表缺席**：`sessionBoundProvidersProvider`（`session_refresh_service.dart`，完整性约束「用户态数据 provider 必须登记」）不含 `firstActionStateProvider`——用户 goal 面跨登出/换号存活。
4. **dashboard 刷新集缺席**：`_refreshHomeGrowthState`（下拉刷新）失效清单不含该 provider，手动恢复路径也无。
5. **守门吞噬 staleness**：卡内 `state?.goal == null → SizedBox.shrink` 把以上一切 stale 态静默渲染为「卡片不存在」——这正是「goal 已落库但卡片缺失」的 UI 表现形式。

**间歇性归因（4/6 miss 而非 6/6，与落点方差耦合）**：register 直落 soft-wall dashboard → pre-goal fetch 被缓存 → 必 miss（PX1/PX2/PX4/px5_full）；auto-login 复活流程落「我的」tab（V3-FIX-541 落点分歧实测 ×3）→ dashboard 未 pre-goal 挂载 → 首次 fetch 发生在落库后 → hit（PX3 重跑/PX5）。R7 双态（skip 落 /chat 或 /home）两态在 go() 后 shell 均重建，任何一态都救不回已被缓存的旧值——与实测两态皆 miss 的一致面吻合。引擎「打盹」503（PX2 log）是 miss 第二形态的注入源（AsyncError 同样被缓存），已在 T2 覆盖。

**拓扑亲证**：`/home` 在 `StatefulShellRoute.indexedStack` 分支 0；`/onboarding/persona`、`/onboarding/modeling-chat` 是 `UserRoutes.routes` 挂的 shell 外顶层路由（`app/routes.dart:425`）——go() 过程 dashboard 子树整体卸载，goal 写链全部发生在卡片不在场窗口。

## 修法（5 触点，最小改动）

1. `first_action_repository.dart`：provider 改 `FutureProvider.autoDispose`——每次 dashboard 挂载重查服务端真源（核心修，消灭 stale-null/stale-error 缓存类）；「重开 App 持久化回放」语义不变（真源在服务端，投影只读）。
2. `persona_onboarding_screen.dart` `_handleFastPathSubmit`：goal 落库后 `..invalidate(firstActionStateProvider)`——覆盖 `user_persona_screen` 经 `context.push` 进入（dashboard 分支下层存活、卡片仍 listen、autoDispose 不释放）的拓扑。
3. `persona_onboarding_screen.dart` `_handleContinue`（全量提交）：同一写链纪律，同步 invalidate（全量提交同样落 learning_goal）。
4. `modeling_chat_screen.dart` `_finish`：skip/完成即 journey 终点，invalidate first-action 投影后再路由。
5. `session_refresh_service.dart`：`firstActionStateProvider` 登记 N-4 session 失效清单；`dashboard_screen.dart` `_refreshHomeGrowthState`：下拉刷新集纳入（同屏写路径后可手动恢复）。

## 红绿（widget 测试 fake 时序，无真机）

- 新测 `mobile/test/features/journey/first_action_card_reentry_test.dart`：
  - **T1 快车道竞态**：同一 ProviderContainer（= 同一进程）先以无 goal 态挂载（soft-wall 面）→ 卸载 → 脚本翻转服务端态（goal 落库等价面）→ 重挂载断言 goal 标题上卡 + fetchCount==2。红（修复前 0 widget 浮现，实测 4/6 miss 的复现面）→ 绿。
  - **T2 引擎节流毒化**：首查抛错（「503 打盹」）→ 卸载 → 服务恢复+已落库 → 重挂载必须浮现。红 → 绿。
  - **T3 N-4 注册表**：`sessionBoundProvidersProvider` contains `firstActionStateProvider`。红 → 绿。
- 红的可信度：修复代码 `git stash` 后 3/3 红（T1/T2 失败面即「goal 落库但 0 widget」），恢复后 3/3 绿——非骨架假红。
- 测试骨架注记（有价值的过程实录）：autoDispose 的卸载经 riverpod scheduler `vsync`（`_UncontrolledProviderScopeElement.build` 下一帧执行）。测试若把整个 `UncontrolledProviderScope` 换掉，scope element unmount 时已调度的 dispose 任务被丢弃（`_mounted=false` → markNeedsBuild 跳过）——dispose 永不执行，呈现假性「缓存仍在」。故测试骨架复刻生产拓扑：根 scope 常驻（app.dart 单根 scope），只替换 dashboard 子树。生产不受此影响（根 scope 永不卸载）。

## 验证

- `flutter test`：新测 3/3 + 既有 `first_action_card_test.dart` 8/8 + `persona_onboarding_*` 3 文件 + `modeling_chat_screen_test` + `dashboard_screen_structure_test` + `core_provider_keep_alive_test` + journey/ 全量 + `auth/presentation/providers/`（含 N-4 隔离回归）= **全绿（62+ pass，两批合计 44+18）**。
- `flutter analyze`：No issues found。
- worktree 内 `make proto-gen`：dockerized 拉取失败回落 host toolchain 成功（wt792 同款路径；mobile/lib/gen 为 gitignore 产物，未入库）。

## 残留（不阻塞本卡，如实登记）

- **同屏 goal 写面的失效纪律**：onboarding 之外的 goal 写路径（如 cockpit「先定下你的第一个目标」CTA 链）是否写 first-action 投影真源未核；本修后该面已有两道恢复（autoDispose 重挂载重查 + 下拉刷新显式失效），若复测发现同屏写后卡片仍 stale，按 V3-FIX-542 起 grep 复核登记（542 当前空闲，541=落点分歧已登记）。
- V3-FIX-539/540 修复后的 J-02 残留复测（纯 UI 注册路径 ≤3min）仍属登记在案的 J-02 残留工作；本卡未改 V3-FIX-538（注册 tap 弹回，OPEN）。
- 台账 540 行销账判定留给集成会话：修法面已闭环（红绿+回归+analyze 净），实测复测需真机/驱动通道（本卡约束禁 flutter run），未自勾验收。

## 变更清单

- `mobile/lib/features/journey/data/repositories/first_action_repository.dart`（autoDispose+注释）
- `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`（快车道+全量两处 invalidate+import）
- `mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart`（_finish invalidate+import）
- `mobile/lib/core/services/session_refresh_service.dart`（N-4 注册表+import）
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`（刷新集+import）
- `mobile/test/features/journey/first_action_card_reentry_test.dart`（新增红绿测试）
- `v3-output/WT799-F540/notes.md`（本实录）
