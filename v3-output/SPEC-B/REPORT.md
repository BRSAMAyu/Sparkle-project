# SPEC-B · 考试冲刺卡 #2 + #8 + #9 三件（同文件捆绑）· 收工报告

> 卡：北极星全旅程战役 · A 纵队设计语言线 ｜ 2026-09-22 ｜ worktree **wt177**（base **703d5629**）
> 规范依据：`v3-output/A-SPEC-V1_1/REPORT.md` §4 N3/N5/N6 + §5 改造清单 #2/#8/#9
> 性质：产品代码改造卡。改动全部落在 `exam_sprint_dashboard_card.dart` 及其测试/文案域（详见 §2 冲突面）。
> 交付物 = 本报告 + `changes.patch`（669 行）｜ 未 commit / 未 push ｜ 零凭据。

---

## 1. 三件实现清单（逐条对照验收自证）

### #2 通过率弧规范化（N6 预测数准入四件）— 改造清单 #2

| N6 子条款 | 落点（file:line @ wt177 工作树） | 实现 |
|---|---|---|
| ② 口径一行就地可见 | `exam_sprint_dashboard_card.dart:657-663`（弧右侧信息列第三行） | 新增 `context.l10n.examPassProbabilityEstimate`＝zh「按当前进度估算」/ en "Estimated from your current progress"，bodySmall/textSecondary，与既有 daysLeft/今日进度行同列就地可见 |
| ③ 低档分档文案兜底 | `:582-584`（`showLowTierAction = !isNull && probability < 0.4`，按**最终预测值**判定，非动画中间值）+ `:665-674` | <0.4 时追加 `examPassProbabilityLowAction`＝zh「还来得及，先攻高频考点」/ en "Still time — focus on high-yield topics first"；≥0.4 与 null 档不渲染 |
| ④ 编码色走 theme CB-safe 变体 | `:683-689` `_probabilityColor(SparkleColors, value)` 改读 `context.colors.error/warning/success`（原为静态 `DS.*` 直读） | 语义槽经 `SparkleThemeExtension` 注入主题取色；`colorBlindFriendly: true` 时自动切换 Okabe-Ito 变体（error=朱红 0xFFD55E00 / success=蓝绿 0xFF009E73 / warning=橙 0xFFE69F00），红绿单通道依赖消除 |
| ④ 入场动画 ≤M3（320ms） | `:13` `_kCanonicalEntrance = Duration(milliseconds: 320)`（A2.1 阶梯白名单 320∈正典集）+ `:556-558` 弧控制器引用 | 原 `1200ms` offLadder 退役；档内归梯 |
| arb 双语 + gen-l10n | `app_zh.arb:9348-9349`、`app_en.arb:9546-9547` 新 key；`flutter gen-l10n` 重生成 `app_localizations{,_zh,_en}.dart` | `check_l10n_regen_parity` PASS（11204 键对齐）；`check_i18n_coverage` PASS |

**验收测试**（`exam_sprint_dashboard_card_test.dart` group `SPEC-B #2`，4 条全绿）：
- ② 口径文案存在：`find.text('按当前进度估算')` findsOneWidget；
- ③ 低档文案触发：0.35 → 动作文案出现；0.72 → findsNothing；
- ④ 时长∈正典集：t=0 显示 0% → t=160ms 未到位（在途，非瞬时）→ **t=320ms 到位**（同时排掉旧 1200ms 档）；
- ④ CB 变体无红绿依赖：以 `SparkleColors.light(colorBlindFriendly: true)` 注入 ThemeData，0.35 弧色断言 = **0xFFD55E00**（Okabe-Ito 朱红）且 ≠ 标准主题 error（0xFFA0483E ⇒ 证明色源确走 theme 注入）；0.72 弧色 = **0xFF009E73**（蓝绿），与朱红构成蓝/红双通道对比。

### #8 DayZero 浮动降级（N3 呼吸禁令，实现无关口径）— 改造清单 #8

落点 `exam_sprint_dashboard_card.dart:246-303`：

- `_floatController.repeat(reverse: true)`（原 3000ms 常驻循环）→ `_entranceController.forward()` **单次入场**（320ms 正典档，`easeOutCubic` 自下方 6px 浮入，1.0＝静止位）；依赖重建不重播（`isAnimating || isCompleted` 双门）。
- **DecorationMode 门控保留**：`resolveDecorationMode` 分支不动——非 animated 档 `stop() + value=1.0` 钉静止定帧（原 0.5 相位改为入场完成位，语义更准）。
- 入场映射 `Offset(0, (1-entrance)*6)`：value=1 恒 0 偏移，无往返分量。

**验收测试**（group `SPEC-B #8`，2 条全绿）：
- 单次入场（强制 high 档走 animated 分支）：首帧偏移 >0（入场中）→ 320ms 到静止位 → **再持续观察 2.5s（覆盖旧 3000ms repeat 完整周期）偏移恒 0** ⇒ 无循环 controller；
- reduce-motion（high 档 + disableAnimations，排除 tier 降档干扰）：首帧即静止位。

**守卫自证**：文件内 `repeat(` 调用清零（仅注释提及历史）；`Duration(milliseconds:)` 字面量全文件仅剩 320 一处（梯内）。

### #9 urgency 色阶迁移（N5 三档）— 改造清单 #9

落点 `exam_sprint_dashboard_card.dart:44-49` + `:1038-1044` `_urgencyAccentColor`：

| 档 | 条件 | 色源（theme 语义槽） |
|---|---|---|
| 中性层 | daysLeft ≥ 8 | `colors.brandPrimary` |
| warning | 2 ≤ daysLeft ≤ 7 | `colors.warning` |
| error | daysLeft ≤ 1（考日 daysLeft=0 走横幅，不染此色） | `colors.error` |

原 `daysLeft <= 3 ? DS.error : DS.brandPrimary` 双档整卡翻转退役。

**翻转范围收敛至两处**（其余位去 urgency 翻色）：
1. **header**（`_CardHeader`：火箭图标容器 + 模式 pill，`:74`）；
2. **倒计时数字**（`_HeadlineBlock` countdown 文本 `:494`，原恒 textPrimary）。

同步去翻转：计划名 chip 回归中性面（`DS.surfaceSecondary` + textSecondary 12% 描边，`:508-518`）；今日任务组回归中性 brandPrimary（`:191-192`）；`_PassProbabilityArc` 的死参数 `accentColor`（从未被弧消费）删除——弧的编码色唯一来源是 N6 的 `_probabilityColor`。

**验收测试**（group `SPEC-B #9`，4 条全绿）：
- 三档色值断言：daysLeft=10/8 → header 图标与倒计时数字均 = `brandPrimary`；daysLeft=7/2（边界）→ = `semanticWarning`（0xFF7D5C26）；daysLeft=1 → = `semanticError`（0xFFA0483E）；
- error 槽在 ≤7d 档不出现：daysLeft=5 全树扫描所有 `Text.style.color` 与 `Icon.color`，`everyElement(isNot(semanticError))`。

---

## 2. 冲突面声明

- **wt176**（同日改 sprint_screen.dart + provider）：本卡全部改动在 `features/home/presentation/widgets/exam_sprint_dashboard_card.dart` + `features/home` 测试 + `lib/l10n` 文案/生成物；wt176 落 `features/plan/presentation/screens/sprint_screen.dart` + `exam_sprint_dashboard_provider.dart`。**双方文件面零重叠**（同属冲刺域但树内不同文件；SPEC-B 未触碰 provider 与 sprint_screen），互已声明。
- **wt170 / wt172 / wt174**：全 backend，无交集。
- **wt175**：纯研究卡，无交集。
- arb 文件插入点为 exam 键块尾部（`examPlanSubject` 之后），与既有 openclaw 键块无位移冲突。

## 3. 诚实申报（风险与边界）

1. **两处中性档视觉变化**（N5 收敛的必然结果，非隐藏）：≥7d 档倒计时数字从 textPrimary 变 brandPrimary（与 header 同源的 hero 强调）；计划名 chip 从 brand 淡染变中性灰面。≤7d/≤1d 档 header 与倒计时颜色语义更准（warning/error 不再越槽整卡翻转）。
2. **测试强制了 PerformanceTier**：测试宿主（60Hz + dpr 3.0）默认解析为 medium 档 → staticFrame，会跳过 animated 分支；`SPEC-B #8` 组内 `forceHighTier()` 显式钉 high 并 `addTearDown` 还原 `defaultPerformanceTier()`，不污染其它用例。生产行为不受影响。
3. **worktree 缺 gitignored 产物**：`mobile/lib/gen/`（proto 生成物，`.gitignore:240`）在本 worktree 不存在导致编译失败；经 diff 确认 `proto/` 与主仓逐字节一致后，从主仓**只读复制**进本 worktree（等价 `make proto-gen` 产物，未写主仓任何字节）。该目录不入 git、不进 patch。
4. **predicted_intent_card_test 2 例失败为存量**：本批相邻域回归发现的 2 例失败（`predicted_intent_card_test.dart` "Recent same-category signal" 相关），已在 HEAD 克隆基线复现同样 2 例——与本卡零关系，未越界修复（防冲突面扩张），留卡池处理。
5. **`_PassProbabilityArc.isChinese` 参数为存量未用字段**（HEAD 即如此），未动（不属本卡三件，避免 diff 扩张）。
6. 口径行/低档文案挂在弧右侧信息列（非弧内环形文字）：N6 要求「就地可见」，与既有 daysLeft/今日完成行同列即视为就地；若验收期望弧下方独立行，属一行级调整。

## 4. 回归对比数据（对比法）

| 批次 | HEAD 基线（/tmp 克隆 @703d5629） | wt177 本卡 |
|---|---|---|
| `exam_sprint_dashboard_card_test.dart` | 8 pass / 0 fail（存量 F14×5 + F15×3） | **18 pass / 0 fail**（存量 8 全保持 + 新增 SPEC-B×10 全绿） |
| 相邻域批（closed_loop + `test/features/home/` 全量） | 41 pass / 2 fail（predicted_intent 存量×2） | **51 pass / 2 fail**（同 2 例存量；+10 = 本卡新测试） |
| `flutter analyze`（卡文件） | — | 0 error / 0 warning（仅存量 info 级：trailing comma、discarded_futures 等，与 HEAD 同型）；本轮修复自生 lint 2 处（unnecessary `!`、冗余 import） |

**守卫触碰面（全部 PASS）**：
- `check_dl_spec_ratchet.py`：`offLadderDuration` 总量 **184 → 182（-2）**——正是本文件 1200ms（#2）与 3000ms（#8）双双退役；基线未动（合并窗口刷新纪律），ratchet 只降不升达成；
- `check_ux_component_convention.py` PASS（rawButton 19/19 等，无新增裸件）；
- `check_l10n_regen_parity.py` PASS（11204 键）、`check_i18n_coverage.py` PASS。

## 5. 收工核查

- [x] 交付物仅 `v3-output/SPEC-B/REPORT.md` + `changes.patch`；未 commit / 未 push
- [x] 改动全部在专属 worktree（wt177）内；主仓只读（仅 gen 复制读源）；零凭据
- [x] 令牌纪律：色源全走 `context.colors` 语义槽 / 既有 DS 令牌，零新增裸色；时长 320 ∈ A2.1 正典集；l10n 新 key 双语 + gen-l10n 落地
- [x] HEAVY 纪律：flutter test 跑前进程门（`ps | grep flutter_tester|flutter_tools` = 0）每次通过；串行 `--concurrency=1`；共 4 个定向小批，无宽扫描；swap <1.2G 期间先做守卫/报告轻任务错峰
- [x] 收工清理：`/tmp/speccb-baseline`（HEAD 对照克隆）、`mobile/build/`、`.dart_tool/` 全部删除；无 /tmp 驻留、无遗留进程
- [x] 基线 JSON 未动（offLadder -2 留待合并窗口按共享态纪律刷新）
