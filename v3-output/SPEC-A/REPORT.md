# SPEC-A · 冲刺仪表盘 #1+#3+#5 三件改造（同文件捆绑）交付报告

> 卡：北极星全旅程战役 · A 纵队设计语言线 SPEC-A ｜ 2026-09-22 ｜ worktree **wt176**（base **703d5629**）
> 规范依据：`v3-output/A-SPEC-V1_1/REPORT.md`（SPEC v1.1，已采纳）§4 N1-N8 + §5 改造清单 #1/#3/#5
> 触碰面：`mobile/lib/features/plan/presentation/screens/sprint_screen.dart` + `mobile/lib/core/display/lexicon/date_formatting.dart` + `mobile/lib/l10n/app_{zh,en}.arb`（+ gen-l10n 产物）+ 新增验收测试 1 文件。**未触碰** `exam_sprint_dashboard_card.dart`（wt177 今日所有，见②）。
> 交付物：本文件 + `changes.patch`（8 个 diff，含新增测试）。零凭据；未 commit / 未 push。

---

## ① 三件实现清单（逐条对照验收标准自证）

### #1 倒计时与进度口径归一（N2 派生值单算）——`sprint_screen.dart` `_SprintHeader`

| 改什么 | 落点 | 实现 |
|---|---|---|
| daysLeft 客户端自算 → 服务端真值 | 原 :216 `plan.targetDate.difference(DateTime.now())` | `_SprintHeader` 改 ConsumerWidget，`ref.watch(examSprintDashboardProvider).valueOrNull`，**planId 匹配时直接采用 payload `days_left`**（与 home 内嵌 exam 卡共用同一 provider = 单一数据源） |
| 降级路径不再自算 | 同上 | payload 缺失 / planId 不匹配 → 不再推算天数，Chip 改展示目标日 `sprintEndsOn(formatSparkleDateOnly(targetDate))`（走 date_formatting 唯一入口，新增 `formatSparkleDateOnly`）；targetDate 也为 null → **不渲染倒计时位**（诚实空缺，不造默认值；顺带修掉原「targetDate=null 显示冲刺已结束」的假态） |
| days_left==0 语义修正 | Chip 分支 | 0 天显示 `examDay`（今天考试），<0 才显示 `sprintEnded`——对齐 backend celery `days_left<=0` 即考日的口径 |
| `plan.progress` 口径来源标注 | 进度条下方新增一行 | `sprintProgressScope`（「口径：服务端按冲刺任务完成比结算」）——文案实测自 backend `plan_service.update_progress`（`new_progress = completed_tasks / total_tasks`），与 exam 卡 `today_progress.completion_rate` 口径区分 |
| 删 S-G9 重复文案 | exam 卡 :469-470 vs :628-631 | **未执行**——落点在 `exam_sprint_dashboard_card.dart`（wt177 今日所有），见③ |

**验收自证**：
- ✅ 跨屏断言两处剩余天数同源同值：`sprint_screen_test.dart` 两个用例——①sprint 屏在 `targetDate=2027-03-02`（本地推算 ≈160 天）与 `days_left=5` 故意矛盾的桩下，断言显示「剩余 5 天」且 `textContaining('160')` findsNothing、无「冲刺已结束」；②同一 `ExamSprintDashboardData` 喂给 `ExamSprintDashboardCard`，断言「还有 5 天」「距考试还有 5 天」。两屏同值=同源自 examSprintDashboardProvider。
- ✅ 客户端无 DateTime.now() 推算派生值：`grep -c "DateTime.now()" sprint_screen.dart` = **0**（改造前 1）。

### #3 sprint 屏三态补齐（N4 错误态三件套硬性）——`sprint_screen.dart` `_ActiveSprintView` + `_SprintSkeleton`

| 改什么 | 落点 | 实现 |
|---|---|---|
| 错误态 → CustomErrorWidget 三件套 | 原 :195-205 Icon+裸文案 | `CustomErrorWidget.page`：人话标题 `sprintLoadErrorTitle`（冲刺面板加载失败）+ 影响一句 `sprintLoadErrorImpact`（任务和进度暂时看不到；你的数据没有丢…）+ **重试钮**（owner SparkleButton，onRetry=`ref.invalidate(planDetailProvider(plan.id))`）；错误对象不直出（err 参数弃用） |
| 任务空态 → EmptyState | 原 :175-178 `sprintNoTasks` 裸文本 | `EmptyState(title: 还没排任务, description: 为何空+影响, actionText: 去排任务, onAction: → /plans/{id})` 单一 CTA；旧 key `sprintNoTasks` 从 arb 移除（全库零引用） |
| 骨架按真实布局重拼 | 原 :681-689 3×80×80 方块 | 三段同构：①header 卡（标题/概述/进度行/进度条/口径行/倒计时位/全宽复盘钮）②成就卡（图标+标题行 + 2 条 40×40 圆环成就行 `_SkeletonAchievementRow`）③任务区（标题 + 3 条 `_SkeletonTaskRow` 整宽圆角卡） |
| 日期拼接走 date_formatting | — | 本卡触碰面内无 `'${…date!.month` 手工拼接（见③申报）；反向贡献：`date_formatting.dart` 新增 `formatSparkleDateOnly` 唯一入口，供倒计时降级位与后续卡复用 |

**验收自证**：
- ✅ 三态 widget test 各 1（共 3 用例）：错误态断言 `CustomErrorWidget` 存在、标题/影响文案存在、`textContaining('boom')` findsNothing（裸异常零直出）、点「重试」后 provider 重建计数 1→2；空态断言 `EmptyState` 存在 + 标题/hint/CTA 三文案 + 旧裸文案 findsNothing；骨架断言 80×80 方块清零 + 全宽 44 高复盘钮位 / 40×40 圆环位 / 全宽文本行位均在（贴真实布局特征件）。
- ⚠️ 「骨架→内容无布局跳变（golden 前后帧）」：**未做 golden**——仓库无该区域 golden 基建，本卡以骨架特征件结构断言替代；golden 建议随 sprint surface 入守卫卡（改造#7）一并立。
- `'${group.date!' 模式：触碰面内 0；全 lib 余 1 处在 exam 卡（见③）。

### #5 sprint 进度位诚实编码（B-02 进度/奖励分离）——`_CloseToUnlockBanner` + `_SprintAchievementTile`

| 改什么 | 落点 | 实现 |
|---|---|---|
| 进度条 valueColor 回归中性/success | 原 :503-510、:602-610 | 新增唯一映射 `_progressValueColor({required bool completed})`：未满=中性层 `DS.neutral500`、已满/已解锁=`DS.success` 语义槽；横幅与 tile 两处进度条全部改走该映射 |
| 稀有度色只留图标身份位 | 图标环 + 横幅描边 | 40×40 圆环的底/边/图标保留 `_rarityColor`（§8.7-3 合法域）；横幅 low-alpha 稀有度描边保留；进度读数 % 文本稀有度色 → `DS.textSecondary`（tile 已解锁态「已完成！」→ `DS.success` 语义槽） |
| 渐变横幅降级为 S2 色阶+描边 | 原 :447-460 `LinearGradient` | 删渐变，改单色 `accentWash`（surface 系低浓度稀有度 wash，保留身份感）+ 既有稀有度描边；容器挂 `ValueKey('sprint-close-unlock-banner')` 供测试定位 |
| 两份 `_getRarityColor` 合一 | 原 :538-549、:630-641 | 收敛为文件级唯一 `_rarityColor(AchievementRarity)`，两处私有 helper 全删 |

**验收自证**：
- ✅ 进度位色值断言：widget test 遍历屏上全部 `LinearProgressIndicator`——凡显式 `valueColor` 者色值必须 ∈ {`DS.neutral500`, `DS.success`}（且断言显式 valueColor 的条非空），并断言任何进度条 valueColor 不得等于 rare/epic/legendary 稀有度色。
- ✅ gradient 基线 -1：`grep -c "gradient: LinearGradient" sprint_screen.dart` = 0（改造前 1）；守卫实测 `gradientLiteral=302/303`（基线 303，现值 302，ratchet 只降已兑现，基线 JSON 由合并窗口刷新）。
- ✅ 重复 helper 清零：`grep -c "_getRarityColor"` = 0。

## l10n 与共享件变更

- 新 key（zh/en 双语，gen-l10n 已跑，`check_l10n_regen_parity` PASS）：`sprintNoTasksTitle/Hint/Cta`、`sprintLoadErrorTitle/Impact`、`sprintEndsOn({date})`、`sprintProgressScope`、`displayDateOnly({month},{day})`；删 key：`sprintNoTasks`。
- `date_formatting.dart`：新增 `formatSparkleDateOnly`（纯日期绝对格式，复用 displayDateOnly），不改动既有三个函数。

## 环境备注（合入窗口需知）

基线 worktree 缺 `mobile/lib/gen/`（gitignored 生成物，考卡原生测试连 exam 卡旧测试都编译不过）。已用本仓 `buf generate --template buf.gen.dart.yaml`（host protoc-gen-dart，等价 `make proto-gen` 的 dart 段）在本 worktree 内补齐；产物不入库、不进 patch。**合入后跑定向 mobile 测试前需确保 gen 已生成**。

---

## ② 冲突面声明（逐个）

| 会话 | 改动面 | 与本卡关系 | 结论 |
|---|---|---|---|
| **wt177** | 同日改 `exam_sprint_dashboard_card.dart` | 本卡触碰文件为 sprint_screen.dart / date_formatting.dart / l10n arb / 新测试文件，**不含 exam 卡**——本卡 #1 的 S-G9 删除与 #3 的 `'${group.date!'` 清零因该文件所有权**主动未触碰**（见③） | **不同文件，零重叠** ✅ |
| **wt170 / wt172 / wt174** | 全 backend | 本卡零 backend 改动（backend 仅只读走查 plan_service 以核实 progress 口径） | **零重叠** ✅ |
| **wt175** | 纯研究 | 本卡为产品代码卡，无共同产出物 | **零重叠** ✅ |

---

## ③ 诚实申报（做不满的验收条目）

1. **S-G9 重复文案未删**（#1 验收子项）：两处落点（exam 卡 `_HeadlineBlock` :469-470 与 `_PassProbabilityArc` :628-631）均在 `exam_sprint_dashboard_card.dart` = wt177 今日所有。为守「零重叠」红线主动放弃；卡面「全部落 sprint_screen.dart 及其 provider」与此子项冲突，按纪律取文件所有权优先。**移交 wt177 或下一张 exam 卡顺带删除（S 级，删一处 `examTodayCompleted` 文本块即可）。**
2. **`'${group.date!'` 模式全 lib 未清零**（#3 验收子项）：现存 1 处在 exam 卡 :816，同上归属 wt177。本卡触碰面内该模式为 0（且新增的日期展示全部走 date_formatting）。
3. **golden 前后帧未做**（#3 验收「骨架→内容无布局跳变」）：无存量 golden 基建，以骨架特征件结构断言替代；如需 golden 建议随改造#7（sprint surface 入守卫）立基建。
4. **既有分析器 info 残留 2 条**（非本卡引入，触碰行外）：`prefer_expression_function_bodies`（`_NoActiveSprintView.build`）与 `discarded_futures`（复盘钮 onPressed 内 `SensoryFeedbackService.emit`）——`git diff` 证实两行未被触碰，基线不劣化；顺手修复了基线既有的 3 条 `directives_ordering`（import 块本就在触碰面内）。
5. **`planLoadSprintFailed` 成为死 key**：被三件套文案替代后全库零 dart 引用；保守起见未从 arb 删除（防他处动态引用），建议下个 copy 批清理。

---

## ④ 回归对比数据（对比法：先基线、后改后；同机同串行 `--concurrency=1`）

| 测试文件 | 基线（改动前） | 改后 | 结论 |
|---|---|---|---|
| `test/features/plan/presentation/screens/sprint_screen_test.dart`（新增，验收 6 用例：#1×2、#3×3、#5×1） | 不存在 | **6/6 pass**（基线 0 新增到既有文件） | ✅ |
| `test/features/home/presentation/widgets/exam_sprint_dashboard_card_test.dart` | **8/8 pass** | **8/8 pass** | ✅ 零回归 |
| `test/app/router_smoke_test.dart`（含 `/sprint → SprintScreen` 路由注册） | **8/8 pass** | **8/8 pass** | ✅ 零回归 |
| `flutter analyze` 触碰文件（sprint_screen.dart / date_formatting.dart / 新测试） | 4 info（3 ordering + 2 旧 info） | **2 info**（均为未触碰的基线既有项） | ✅ 不劣化 |
| 守卫 `check_dl_spec_ratchet.py` | PASS | **PASS**（gradientLiteral 302/303，本卡净 -1） | ✅ |
| 守卫 `check_ux_component_convention.py` | PASS | **PASS** | ✅ |
| 守卫 `check_i18n_coverage.py` / `check_l10n_regen_parity.py` | PASS | **PASS**（11209 keys 双语完整） | ✅ |

---

## ⑤ 收工核查

- [x] 交付物仅 `v3-output/SPEC-A/REPORT.md` + `changes.patch`（8 diff：7 修改 + 1 新增测试）；无commit/无 push/零凭据
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean/切分支类树操作
- [x] flutter test 前进程门检查（`flutter_tester|flutter_tools` = 0）×3 次；全程 `--concurrency=1` 串行定向，未宽扫描；swap 门观察（最低 1.15G 时仅执行 LIGHT 分析/生成命令）
- [x] 收工清理：`mobile/build`（129M）、`mobile/.dart_tool`（132K）已删；`mobile/lib/gen`（1.4M，gitignored 生成物，随 worktree 回收）保留供测试复跑；/tmp 无驻留；无模拟器/浏览器实例
- [x] 令牌全走 `mobile/lib/core/design/`（DS.*），无新增裸色/字面量；l10n 新 key 全部双语 + gen-l10n
- [x] 未触碰 exam_sprint_dashboard_card.dart、backend、scripts/guards
