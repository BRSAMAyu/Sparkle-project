# WT792 J-02 Simulator 实测证据 · 执行实录（notes）

- worker：wt792 ｜ 分支 `agent/node-b/wt792/j02exec` ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt792-j02exec`
- base：main@`7de5e46e`（含 9d72463d「chore(ledger): V3-FIX-498 闭账」，任务书确认相符）
- 执行窗口：2026-09-28 08:23 起（day7 终门 08:19 PASS 之后，设备窗口已开）
- 依据：`v3-output/WT784-J02PREP/runbook.md`（主通道=macOS 集成测试通道）+ `checklist.md` + 驱动 `mobile/integration_test/j02_fastpath_journey_test.dart`（wt789 交付，flutter analyze 净——本会话 08:26 复验 No issues found）
- 通道：macOS desktop（darwin-arm64，Flutter 3.41.3，J-01 wt398 同款主通道）；fresh install 语义 = 每 persona 独立 dart 驱动进程 + 进程起点 `wipeLocalState()`（secure storage + prefs，runbook §2.1 macOS 行）
- 运行栈：只使用不重启。08:23 preflight——gateway :8080 healthy（uptime 48m）、engine :8000 healthy、gRPC :50051 open、sparkle_db/redis/minio 三容器 up 23h healthy

## 关键 setup 决策

1. **xcconfig shims 必需（更正）**：runbook §1.2 的 `mobile/macos/Flutter/Flutter-Debug.xcconfig` shims 是必需的——引用链在 `macos/Runner/Configs/Debug.xcconfig:1`（`#include "../../Flutter/Flutter-Debug.xcconfig"`），不在 pbxproj。首次构建因此失败一次（`run_macos_px1.log` 留证，不删）；补建 shims（gitignored）后重跑。主仓 Flutter/ 下无 shims 是因 ephemeral 外的 include 文件恰在其构建目录里被生成/存在差异——教训：Configs/*.xcconfig 也是引用点。
2. `make proto-gen` 在 worktree 执行成功（dockerized toolchain 拉取失败后自动回落 host toolchain，13 stubs + 4 re-exports）。
3. DB 探针列名已对活库校准（runbook §5.2 预留动作）：`memory_goals.user_id`、`episodic_memories.user_id`、`users.username`、`users.registration_source` 全部存在，模板 SQL 可直接用。

## 执行矩阵（含降级口径）

- Process 1：`J02_PASS=0 J02_LEGS=R,G,U`——PX1 真·冷启 + Leg G + Leg U（单进程三腿全）
- Process 2-5：`J02_PASS=1..4 J02_LEGS=R`——PX2-PX5 各自独立进程真·冷启
- 覆盖度 = runbook 允许降级矩阵：Leg R ×5（全真冷启）+ Leg G ×1 + Leg U ×1；如实标注
- run_id：`j02sim_macos_20260928_082714_36a0`

## 时间线（终）

- 08:27:14 run_id 生成，evidence 目录建
- 08:28 Process 1（PX1 R+G+U）启动——首次构建失败（缺 shims，log 留证 `run_macos_px1.buildfail.log`）
- 08:29:32 Process 1 重跑（shims 补后）→ 08:34:28 结束。PX1：R0-R7 全达（r6/r7 见缺陷注记），R8 前受阻；G 腿落「我的」tab（session 稳定但非 DashboardScreen）；U 腿降级路径+O3 受阻
- 08:40:48 Process 2（PX2, Leg R）→ 08:44 结束。同模式：O3 bounce→fallback ok→r7 FirstActionCard 缺口复现
- 08:40 前后：G4 DB 探针（guest_09788ed34e71）双 0 行 + source=guest ✓；PX1 goal 落库确认（memory_goals=1）
- 08:41 API 级升级探针（instrumented）：新 guest `guest_01710f43`（uid 866e3203）→ `/auth/upgrade-guest`（guest token 直调）→ 同 uid 翻转 src=email、username=j02up0928084114 ✓（A2c 后端语义活栈证据；UI 面受 O3 阻塞如实记录）
- 08:47 Process 3（PX3 首跑）→ **中止于 R0**：wipe 泄漏 auto-login（PX2 会话复活）+ logout tap 无效（V3-FIX-538 家族）。留证不删
- 08:50 两处披露式 harness 修复（R0 走 ensureAtLogin；G1 超时后真人路径恢复，分歧仍记 FAIL）→ analyze 净
- 08:52 PX3 重跑 → **全链打通：t_action_ready=121,754ms ≤ 180s**；R9 UI 确认面未捕获（后端 approve ok + COMMITTED + DB tasks=1）
- 09:05 PX4 → R8 受阻（539）。09:12 PX5 → **t_action_ready=114,583ms ≤ 180s**；DB tasks=1
- 09:33-09:45 G,U 专用进程 ×3 全部 `open returned 1` 启动失败（环境，留证 gu/gu_rerun/gu_rerun2）
- 09:15 全腿进程 px5_full（R,G,U）→ R 腿 539 miss（累计 4/6）；**G 腿完整采证**（g1 分歧 FAIL→恢复→g2 种子扫描 + g3 真实 lane 聊天轮，新 guest `guest_d2f70de3b47c`）；U 腿 O3 受阻 ×2 一致
- 09:20 A1b 最强探针：聊天后 guest 的 episodic=2 行经核验**全部归属其自身 uid**（真实聊天 lane 写自身 namespace，非种子泄漏非跨 namespace）；未聊天 guest 严格 0/0
- 09:25 收官：verdict.json / j02_timings.json（10 进程汇总）/ run_manifest 终态 / REPORT.md

## 实测数字（截至 PX3，fallback 口径见 report）

| pass | 首屏 | 注册完(t_registered) | persona步1 | goal CTA现 | fastpath提交 | skip落点 | R8 action_ready | R9 |
|---|---|---|---|---|---|---|---|---|
| PX1 | 7426ms | 47336ms(bounce→API fallback) | 54072ms | 61857ms | 66121ms | /chat | 未达（无卡） | 未达 |
| PX2 | 4372ms | 43952ms(bounce→API fallback) | 57076ms | 64890ms | 69675ms | /chat | 未达（无卡） | 未达 |
| PX3(重跑) | 2095ms | 78454ms(auto-login 登出_walk+bounce→fallback) | 91704ms | 99510ms | 104094ms | /chat | **121754ms ≤ 180000ms ✓** | UI 确认面文案未捕获（60s 超时）；**后端 approve ok + proposal COMMITTED + DB tasks=1 实锤** |

- PX3 附加实证：`loading_feedback_observed=true`（F5）｜`fast_path_cta_absent_when_goal_empty=true`（wt764 负门控活栈复现）｜`fast_path_hint_appeared=true`｜proposal 三字段已捕获（proposals.json，PX3 内容与 PX1 目标强差异化）
- V3-FIX-539 复现率修正：PX1/PX2 miss、PX3 hit——**间歇性**（2/3 miss），非 100% 系统性；PX3 差异点=auto-login→登出→注册的更长会话周期（provider 刷新时间更充裕），或 PX1/PX2 时段引擎「打盹」节流。根因仍不归因，如实记 2/3。

## 新缺陷登记（只写本文件，编辑权归集成会话；号段经 grep 复核：537 已用，538 起空闲）

- **V3-FIX-538（O3 家族实机复现）**：macOS desktop 注册提交 tap 系统性无效且零反馈——PX1/PX2 各 2 次 tap 后表单原样（TEXTDUMP n=13 无错误词），fallback API 注册 200 后 UI 登录可用（同屏 登录 按钮tap有效）。J-01 7 runs × 3 策略先例的再次复现，至今无 FIX 号。证据：`run_macos_px1.log` / `run_macos_px2.log` J02_FINDING 行 + `04b` TEXTDUMP。影响 Leg R 主判据口径（runbook §6-2 fallback 降级）与 Leg U UI 面。
- **V3-FIX-539（J-02 快车道 skip 后 FirstActionCard 缺失）**：modeling skip 后落 /chat（FIX-536 已知分歧，驱动双态兼容走 home tab），dashboard 的 resume 卡正确消失（onboardingCompleted=true 生效），但 FirstActionCard 生成入口 30s+ 不出现，TodayCockpitCard 呈「先定下你的第一个目标」no-goal 面——而 DB `memory_goals` 已有该用户目标（PX1 j02px15382337 00:30:34 UTC 落库，标题与输入一致）。goals/firstAction provider 链在 skip 后未刷新（或被引擎「打盹」503 节流拦截，PX2 log `服务器正在打盹` 观测到 task load 失败）——根因不在本卡归因。复现：PX1+PX2 共 2/2。直接后果：R8 生成→R9 确认 UI 链不可达，≤3min useful action 的 UI 秒表核无法完成（诚实记录，不粉饰）。
- **V3-FIX-540（guest/auto-login 落点为「我的」tab）**：Leg G guest tap 后 session 建立稳定（60s 观察无 persona 循环——A2b 稳定性面成立），但落点是 profile tab 面（访客体验4e71/Lv.15/初始画像…，截图 `9x-g1_guest_home-timeout.png`），非 J-01 实测的 dashboard 2-3s 落点；路由 redirect 逻辑（`app/routes.dart`）guest 应落 /home，落点分歧根因未归因。驱动断言 DashboardScreen 不在树 → g1 超时，G2/G3 未跑（G4 探针由 orchestrator 补齐，双 0 行 ✓）。同型观测：PX3 auto-login 后同样落「我的」tab——两例同型，加重此 finding。
- **harness 注记（F1 口径 + 两处披露式修复）**：
  - **wipe 泄漏 1/3**：PX1→PX2 无 auto-login（wipe 有效），PX2→PX3 auto-login 为 PX2 用户（secure storage+prefs wipe 后 token 仍活，产品与驱动两侧 `useDataProtectionKeyChain:false` 选项一致，根因未归因；PX3 log `J02_FINDING` 行留证）。F1「fresh install」在本通道口径降级为「wipe 后状态，含 1/3 会话泄漏率」。
  - **修复①（R0 路径）**：auto-login 后的登出_walk 由裸 `productLogout` 改 `ensureAtLogin`（含披露式 provider-logout fallback，J-01 同款披露；PX3 首跑中止于此——logout tap 无效属 V3-FIX-538 家族）。产品代码零改动；PX1/PX2 跑不受影响（未走此路径）。
  - **修复②（G1 恢复路径）**：g1 断言超时后新增「走驾驶舱 tab 真人路径」恢复，g1 落点分歧仍如实记 FAIL（不抹除 V3-FIX-540），使 G2/G3 采证可继续。
  - 两处修复后 `flutter analyze` 净；修复时点在 PX3 首跑留证之后（不删失败 run），PX3 重跑以 `run_macos_px3_rerun.log` 存档。
- 观察项（不算缺陷）：r6_deferred_semantics 记 FAIL——ModelingChatScreen 打开时 PersonaOnboardingScreen 仍在 widget 树（route 栈保留语义，wt764 语义「其余四问未问」本身成立：persona 步 2-5 从未渲染提问）。report 按「语义达成、树残留为测量注记」口径记录。
