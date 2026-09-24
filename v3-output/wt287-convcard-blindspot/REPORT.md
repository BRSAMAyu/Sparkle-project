# wt287-convcard-blindspot 卡报告（A 线·转化卡挂载盲区修复）

日期：2026-09-22 ｜ 分支：wt287-convcard-blindspot（本地 commit，未 push）｜ 基点：d6e64a8b

## ① 挂载链结论与修法

**盲区链条（修复前）**：

- `dashboard_screen.dart` 首屏列表二选一：`hasNoGoals`（`multiGoalOverviewProvider` data 且 `goals.isEmpty`，:1107）为真 → 只渲染 `_buildOnboardingWelcome() + dashboardSections`；为假 → `growthSections + dashboardSections + AuroraCalibrationStrip`（:1474-1483）。
- GuestConversionCard 原挂 `growthSections`（N40 注释位，原 :1130-1133）→ **hasNoGoals 时整体不渲染**。
- 而转化卡主受众恰是「没有目标的新访客」（无目标=无进行中任务=守门④天然过）——主受众永远看不到卡。wt282 的 OnboardingResumeCard 已挂 dashboardSections 避开同坑，本卡为同型盲区补漏。

**修法**：GuestConversionCard 移入 `dashboardSections`，置于 OnboardingResumeCard **紧邻上方**（同段注释合并、cascade 一次 add 两卡，满足 `cascade_invocations` lint）。dashboardSections 两分支均渲染 → 主受众（无目标访客）与有目标访客都可见。副作用检查：dashboardState error/loading 分支不渲染本卡（与 resume 卡一致，可接受）；有目标访客的卡位从首屏第 2 段下移到 growthSections 之后（次要受众位次换主受众可见性，权衡成立）。

改动文件：

- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`（growthSections 摘除 + dashboardSections 挂入，N40/J-02 注释合并改写）
- `mobile/test/features/home/dashboard_test_harness.dart`（新增 `extraOverrides` 追加式参数；riverpod 2.6.1 同 provider 后写胜出，已对源码确认 container.dart:124）
- `mobile/test/widget/dashboard_conversion_cards_visibility_test.dart`（新增，3 用例）

## ② 互斥语义结论

**天然互斥，无需额外避让**（卡内自守门，轴不同）：

- GuestConversionCard：`guestConversionVisibleProvider` 四守门，①即 `isGuestUser(currentUser)`（`registrationSource == 'guest'`，与 routes.dart redirect 同源）→ **注册用户恒 SizedBox.shrink**。
- OnboardingResumeCard：`isAuthenticated && user != null && !isGuestUser && onboardingCompleted == false` → **guest 恒不可见**（其 doc comment 明言「guest 恒 completed，走 N40 转化卡，互斥」）。

两卡相邻挂载，同屏至多见其一。测试用例 1 特意把 onboardingCompleted 钉为 false + guest：即使 resume 卡自身条件（completed==false）成立，guest 轴仍将其钉死隐藏——互斥的强证明。

## ③ 测试结果（定向单文件单进程，--concurrency=1）

| 套件 | 结果 | 说明 |
|---|---|---|
| `test/widget/dashboard_conversion_cards_visibility_test.dart`（新增） | **3/3 pass** | ①盲区修复本体：guest+信号+无目标→转化卡可见+resume 卡不可见；②互斥反向：已认证未引导（且有信号）→resume 卡可见+转化卡不可见；③迁移回归：guest+信号+有目标→转化卡仍可见 |
| `test/widget/dashboard_screen_structure_test.dart` | +2 -3 | 与 baseline 克隆（HEAD 干净树）**逐用例全同**：同 3 败（updates 展开/固定纵向序/en locale），败因 streak-quality 400 逃逸为存量环境性失败（wt282 交接已注明 baseline-verified env failures），**非本卡回归** |
| `guest_conversion_card_test.dart` | 5/5 pass | 卡行为未动，回归绿 |
| `onboarding_resume_card_test.dart` | 4/4 pass | 含「guest 不可见」互斥用例，绿 |

**analyze 对比法**：改动两文件 issue 集与 baseline 克隆全同（dashboard_screen 7 infos / harness 5 infos，仅行号平移），新测试文件 0 issue——零新增。

**守卫**：`run_all_rule_guards.sh` **exit=0，83 规则全绿**。注：克隆场景 AQ/BG 因 gen 缺失先报 fail（baseline 同败），按 mobile gen 同例从主仓 `cp -RL` backend/app/gen 与 backend/gateway/gen 后转绿（-L 解引用，直拷符号链接会令 K/Z 崩——主仓 gen 内含指回主仓的 symlink）；两 gen 目录均 gitignored。

## ④ 资源峰值

- HEAVY 门合规：开工 swap 空闲仅 775-900M，**持门等待**至 1269M（≥1.2G）才起 flutter test；期间只做 LIGHT（pub get/gen 拷贝/analyze/守卫/baseline 克隆）。
- 测试全程 swap 未再触发熔断线（结束后 1417M 空闲）；每轮测试前 `pgrep flutter_tester` 错峰确认无残留；收工确认无 tester 进程。
- analyze ≈7s/次、定向 test ≈1-2s 纯跑（编译另计）；无模拟器/浏览器/Gradle。

## ⑤ 交接建议

1. **合入管线**：`git diff d6e64a8b..wt287-convcard-blindspot` 三处改动（2 改 1 增）；合并窗口若在本 worktree 重跑定向测试，gen 目录拷贝仍在（gitignored），pub get 后即可跑。
2. **存量环境败**：`dashboard_screen_structure_test.dart` 3 用例在克隆环境因 streak-quality 400 逃逸必败（HEAD 同败），建议后续卡排查 harness 未 override 的真实 notifier 网络逃逸（与本卡无关）。
3. **l10n 还原说明**：本机 Flutter 工具链 pub get 会重生成 l10n 三文件（纯 dartfmt 换行差异，-385/+129 行噪音），按纪律 checkout 还原；后续 worker 遇同状可直接还原。
4. **产品向**：转化卡在有目标访客面位次下移（growthSections 之后）——若数据侧后续发现「有目标访客」转化率显著掉，可考虑守门式双挂载（guest+有目标时保留 growthSections 位）；当前以主受众可见性优先，不动。
5. worktree 内 `mobile/lib/gen`、`backend/app/gen`、`backend/gateway/gen` 为验证用拷贝（gitignored），合入后删 worktree 即回收。
