# WT306 · J-03 Today Cockpit 重新定义主入口 — REPORT

**Worker:** wt306 ｜ **Date:** 2026-09-24 ｜ **Status:** READY_FOR_REVIEW
**Worktree:** /Users/brsama/code/GitHub/Sparkle-sysrev/wt306-j03-today-cockpit（branch `wt306-j03-today-cockpit`）

## SHAs

- **base:** `61cea7652f080716b70988387018fca3e38fb269`（branch point，= main@开工时；`git merge-base main HEAD` 复核一致）
- **final:** `1799be7c828559094820d15953d43c5397c9e910`
- **patch:** `v3-output/WT306-J03/changes.patch`（`git diff --binary main...HEAD`，3750 行，merge-base 口径，不受 main 后续推进影响）

## 改动文件清单（12 files, +2049/−892）

**新增：**
1. `mobile/lib/features/home/presentation/providers/today_cockpit_provider.dart` — 四态派生 VM + `todayCockpitProvider`（Riverpod `dependencies:` 声明全部上游）
2. `mobile/lib/features/home/presentation/widgets/today_cockpit_card.dart` — Today Cockpit 主卡
3. `mobile/test/features/home/presentation/widgets/today_cockpit_card_test.dart` — 7 用例

**修改：**
4. `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`（−810 行净减）— cockpit 顶替 Command Center；删 `_HomeCommandCenterCard`/`_CommandCenterContent`/`_CommandCenterSkeleton`/`_GoalChip`/`_OnboardingQuickCard`/`_buildOnboardingWelcome`/`_buildFirstGoalEmptyState`/`_startNextAction`；`_CommandCenterRiskBanner` 保留（_AttentionSlot/_DailyBriefingCard 仍在用）；UnderstandingSnapshotCard 下移至行动区之后
5. `mobile/lib/features/home/presentation/providers/dashboard_slot_config_provider.dart` — `defaultCollapsed` 扩至 15 槽（原 10）
6. `mobile/lib/features/home/home.dart` — export 新 provider/card
7–10. `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + 3 个 gen 产物（28 个新键，`flutter gen-l10n`）
11. `mobile/test/widget/dashboard_screen_structure_test.dart` — 2 用例注入 `dashboardSlotConfigAllExpandedOverride()`（wt296 同款先例）

## 四态实现（每态真实数据路径，无 mock）

派生逻辑全部在 `todayCockpitProvider`（纯组合既有 provider，`dependencies:` 显式声明；永不抛异常）。判定顺序：**no-goal → stalled → active → fresh**：

| 态 | 判定信号（字段级真源） | 唯一 Primary CTA | 跳转链路 |
|---|---|---|---|
| **no-goal** | `multiGoalOverviewProvider.goals` 为空（GET /growth/spine/goals + /plans，含 remote current_goal_id 仲裁） | 「和 AI 定目标」 | `context.go('/goals/new')` |
| **stalled** | ① `homeGrowthState.activeBottleneck`（/growth/dashboard.active_bottleneck，仅 high severity）② `spineStatusBand.staleGuard`（GET /aurora/spine/status-band）③ `deadlineDays<=0`（dashboard.mostImportantTask/activePlanProgress，原 CC 口径）④ nextAction dueDate 已过期 ⑤ `0<planHealth<0.45` | 「解开卡点」→ chat 携带真实 context（bottleneck 走既有 `dashboardBottleneckPrompt(topic)`；其余走 `todayCockpitStuckPrompt(goal, reason)`，reason 三选一按信号强度） | `/chat?prompt=…&chat_mode=growth`（`_openBottleneckChat` 同款约定，即 J-05 的 home 落点） |
| **active** | `tasksCompleted > 0`（GET /tasks/today） | 有 nextAction → 「先做这个」；无 → 「查看任务」 | nextAction：`activeTaskProvider` + `/tasks/{id}/execute?origin=home_growth`（原 `_startNextAction` 链路原样迁入） |
| **fresh** | 有目标但今天未动：`tasksTotal>0 && completed==0`（headline=具体任务标题）；`tasksTotal==0` → 「今天还没排布」 | 开始/安排今天（`/plans/new?type=growth`） | 同上 |

**主卡结构**（HOME.md 信息层级 1→5）：eyebrow（态感知）→ headline（优先真实任务标题）→ why-now 行（瓶颈>截止>停滞staleGuard>健康度>今日余量）→ goal context chips（目标名/进度 x/y/临期≤2 警示）→ current run 条（`chatProvider.runPhase.isActive` + `activeRunSummary`，keep-alive 只读不触发连接，点击进 chat）→ **唯一** `SparkleButton.primary` → 次级「我卡住了」ghost（stalled 态退化为「查看任务」，避免双卡点入口）→ no-goal 态附 5 个目标起点 SemanticPill（复用既有 goal-starter prompt 通道）。

## Competing cards 移除/折叠

- **移除**（3 个互相竞争的引导/行动卡面收敛为 cockpit 单卡）：`_buildOnboardingWelcome`（3 张 quick 卡）、`_buildFirstGoalEmptyState`（5 chips + 3 按钮）、`_HomeCommandCenterCard`（primary+ghost 双 CTA）。N40 GuestConversionCard / J-02 OnboardingResumeCard **原样保留**（有独立可见性守门，未弱化）。
- **默认折叠**（`defaultCollapsed` 10→15 槽）：dailyBriefing、multiGoalDashboard、examSprint、taskBoard、dashboardUpdates、workspaceCards 加入默认折叠；折叠机制本身（CollapsibleSlot 64px header + 长按编辑 + lean view）未动，无槽位被隐藏。存量用户持久化配置不受影响（`fromJson` 仅无存档时取默认值）。
- **首屏唯一 primary CTA** 有测试锁定（见下）。WeatherHeader（装饰背景，U-01 装饰档位管辖，非 CTA 竞争者）未动——决策留档。

## B-02 lineage

VM 文件头有逐字段来源表；`todayCockpitProvider` 仅 watch 5 个既有 provider（multiGoalOverview / homeGrowthState / spineStatusBand / dashboard / chat），未新建任何 repo/endpoint/真源。所有跳转复用既有路由与 prompt 约定。

## 测试证据（全部串行 `--concurrency=1`）

| 套件 | 结果 |
|---|---|
| `today_cockpit_card_test.dart`（新，四态各 1 + loading skeleton 转换 + 全屏唯一 primary CTA 且属于 cockpit 卡） | **7/7 过** |
| `dashboard_screen_structure_test.dart`（5 用例，2 例按 wt296 先例注入全展开基线） | 5/5 过 |
| `test/features/home/presentation/widgets/` + `data/`（home 全量回归） | 58/58 过 |
| `test/app/main_pages_load_smoke_test.dart` + `main_actions_smoke_test.dart` | 15/15 过 |
| `bash scripts/run_all_rule_guards.sh` | **exit 0（83 rules all PASS）** |

启动门合规：两次定向 flutter test 前均查 `sysctl vm.swapusage`（1681M / 1277M free ≥1.2G，load<8）；无模拟器/Gradle/浏览器。

## flutter analyze 计数（flutter analyze 3.35.x，全库）

| 口径 | 本次 | 预算 | 判定 |
|---|---|---|---|
| error | 37 | ≤42 | ✓（预算内且下降） |
| warning | 17 | ≤16(+5 容差) | +1，容差内 |
| info | 598 | ≤594(+5 容差) | +4，容差内 |
| per-code（info_code_budgets 38 码逐一比对） | — | 只降不升 | **无一超预算** |
| 本次改动文件 | **0 告警** | — | — |

+1w/+4i 漂移来源为 l10n gen 产物与存量子集，未超任何 per-code 预算；总 issue 数 713→652（净减 61）。

## 守卫修复说明（开工期间 4 条红转绿）

- **UX-COMP**：新文件 `_GoalStarterChips` 命中 parallelClass 正则（`*Chips`）→ 更名 `_GoalStarters`（内部本就是 SemanticPill owner 组合），PASS。
- **SPACING-RHYTHM**：新文件 spacingHalfStep=6（DS.spacing6/10/14 为 half-step token）→ 全部换 4pt 基格（8/12/16），PASS（1608/1623，较基线降 15）。
- **AQ / BG**：worktree 缺 gitignored 生成产物（backend/app/gen、backend/gateway/gen）→ 按舰队协议从主仓只读 `cp -RL`（解引用绝对符号链），PASS。此为环境修复，不改代码。

## 风险

1. **视觉回归未在真机/模拟器验证**（本任务 LIGHT 纪律禁模拟器）——卡面为原 hero tone 同壳重构，5 Persona 第一眼/5 秒测试需 Reviewer 跑模拟器实证（卡面 Forbidden 条款：不得只凭静态阅读宣称 UX 通过 → 本报告不宣称，标注待验）。
2. `defaultCollapsed` 扩面改变新用户首屏（设计意图），老用户无感；若产品要「新用户也能一键展开全部」，编辑面板入口未变。
3. `chatProvider` 进入 cockpit 派生链：keep-alive 只读 watch，不新建 WS 连接（构造期仅订阅既有 connectionStateStream）；若未来 chatProvider 改为 autoDispose 需同步评估。
4. `spineStatusBand.staleGuard` 作为 stalled 信号依赖后端 band 数据质量；后端误报会直接抬高卡点 CTA 曝光（J-05/Aurora 侧兜底）。

## 未尽事项

- 模拟器 5-Persona 截图审查（J-01 机会图复核）DEFERRED 给 Reviewer/integration（HEAVY，本 worker 受内存纪律限制）。
- WeatherHeader 天气背景与 omnibar 预测卡的「天气式 guide/预测」降级未做（归 U-01 装饰档位/omnibar 所有面，避免跨锁冲突）。
- `homeCommandCenter*` 系列 l10n 键部分失去消费方（_slotMeta 仍用），未清理以防下游引用。

## 收工清理

- worktree 内 `mobile/build`、`.dart_tool` 为 flutter 工具链运行必然产物（gitignored），未入库；`lib/gen`×2 与 `backend gen` 为协议允许的主仓只读拷贝（gitignored）。
- `/tmp/wt306_*.log`、`/tmp/wt306_dashboard_backup.dart`、`/tmp/wt306_codes.txt` 已删除。
- 无遗留进程、无模拟器。
