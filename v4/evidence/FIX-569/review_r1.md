# FIX-569 独立审查 receipt（R1）

- 审查人：R1（独立会话，未参与 FIX-569 实现）
- 日期：2026-09-28
- 对象：worktree `wtF569`，分支 `fix/v4/f569-implicit-motion-wiring`；被审实现头 `92dc478c`，证据头 `b5543af7`（审查起点两者即位，工作树干净）
- 基线：`8b03350b`；证据：`v4/evidence/FIX-569/`（四件套）
- 审查方式：只审不改、不 push；mutation 与探针验后逐字节还原（`git checkout --` / 删除临时测试文件），审查结束时工作树干净、HEAD 仍为 `b5543af7`（亲验 `git status` 空 + `git rev-parse HEAD` 复核）

## 总裁决：**PASS_WITH_CHALLENGES**

三接线位、门语义、reduce-motion 等价、回归与棘轮全部亲证成立；实现方证据四件套与亲跑结果一致、边界登记如实（review_r1 空位、coordination 远端缺位 diff 自证、receipt_id≠event_id 归 F03）。1 项挑战级发现 **F-1**（接线注释/证据对「纠正换载荷重播一次」的语义断言与实测行为不符——实测不重播）须随闭账登记并修正措辞；F-1 不推翻修复：接线本身满足移交令与组件契约，且实测行为（纠正不重播）是保守侧。

## A. 三接线位裁决复核（靶1）：成立

1. **SparkleProposalEnter × `stuck_journey_sheet.dart:210`**：包裹点在 `_ReadyPane` 的 `if (data.mainIntervention != null)` 分支内——abstain（`main_intervention: null`）路径组件结构性缺席，非装饰位；且 P- 反例测试以 `findsNothing` 钉死（`semantic_motion_wiring_f569_test.dart:405-411`）。挂载时机：loading→ready 经 `AnimatedSwitcher` 换代（子 key `ValueKey('stuck-journey-ready')`）→ 提案卡首挂载即播一次（P+ 亲证 80ms 在航、落定 opacity==1）；一次性 TweenAnimationBuilder、无完成回调、sheet 关闭即卸载——与组件契约吻合。
2. **SparkleReceiptSwap × `recovery_calibration_section.dart:120`（key helper :77）**：`git diff 8b03350b..92dc478c -- <该文件>` 仅三段——import、`_receiptSwapKey()`、build 内一层壳包裹 `..._phaseBody(...)`；**八个相体 widget（_inputBody/_scopeChoiceBody/_adjustingBody/_diffReviewBody/_committedBody/_conflictBody/_unknownBody/_preferenceBody）逐字节未动**（diff 无其他 hunk，亲核）。committed 相 `:426` 是全文件唯一 `PixelStateBadge(state: PixelRunState.success)`；conflict/unknown 相各用自家 conflict/unknown 徽章。key 语义亲读：回执仅在 provider 投影解析门放行后在场（`recovery_calibration_provider.dart:563` COMMITTED 无回执一律 unknown）→ confirming/conflict/unknown 相 key 恒为空串哨兵 → tick 不推进 → 零徽章零动画；首挂载 tick==0 直落终态；同 key 重投不重播（`didUpdateWidget` 仅 key 变化推进）。
3. **SparkleEvidenceStamp × `evidence_insight_card.dart:43`**：kind 印章行包裹，`_kindTitle`（:145）封闭词表（friction/helped/goal，词表外回落 unknown 标签，零原文透传上屏）。**U05 排除理由属实**：`node_detail_sheet.dart:1427` `_CapabilityEvidenceSection` doc 明文「不开特效仍理解全部信息：纯静态文本+图标，无动效承载」——挂动效即放松既有门，排除有据非偷懒。滚动不重播主张核实：总览屏为 `SingleChildScrollView`（`learning_insights_overview_screen.dart:70`）+ `for` 循环非懒构建（`evidence_insight_section.dart:64`）→ 卡随 feed 就绪常驻挂载，滚动不重挂；区隐藏（契约不支持/加载/出错 `SizedBox.shrink`）= 卡卸载即取消。✓

## B. 门语义不放松（靶2）：成立，无缺条

实现方 10 例逐条对应亲核（`semantic_motion_wiring_f569_test.dart`）：

| 门 | 断言锚 | 判定 |
|---|---|---|
| 首挂载不播 | R+ :426-434（输入相挂载时 swap 壳下 `TweenAnimationBuilder` findsNothing） | ✓ |
| 同 key 重投不重播 | R- :469-505（同容器原地重建，40ms 零在航 + 文本状态仍在场）；组件级另有 S01 套件 D+ 钉 | ✓ |
| 取消零回执 | R- :536-556（零成功徽章、零 committed 文案、零回执号、输入相原样在场） | ✓ |
| conflict·unknown·在途零徽章零动画 | 在途：R- 门拒 :507-534（approve 挂起零徽章零在航，回执到场才有）；conflict/unknown：既有 U02 套件钉（recovery+insights 67/67 亲跑全绿，含 `_conflictBody/_unknownBody` 零成功徽章） | ✓ |

既有门零删改：`git diff 8b03350b..92dc478c` 对既有测试文件零触碰（唯一测试变更为新增文件）。无缺条需补测。

## C. reduce-motion 等价（靶3）：成立

三格（P- :380 / R- :558 / E- :631）均为「静态分支语义等价」断言而非「不抛异常」：内容完整在场（P-：提案文本 findsOneWidget；R-：成功徽章+回执号在场；E-：类型印章「阻力模式」在场）+ 零动画壳（`TweenAnimationBuilder` findsNothing）+ 零在航透明度。落定终态 vs 静态渲染等价，符合 S01 判例。✓

## D. 独立 mutation（靶4）：3/3 必红，探针判别力成立

| 编号 | mutation（单点，验后还原） | 命令 | 结果 |
|---|---|---|---|
| M-R1a | `_receiptSwapKey` 改为每次 build 返回 `Object()`（每次重建=换代） | `flutter test ...wiring_f569_test.dart --name 'R 回执替换接线'` | **2 failed**：R- 同 key 重投不重播（目标门）+ R- 门拒在航钉 |
| M-R1b | `_receiptSwapKey` 改为恒定串 `'mutant-constant'`（永不换代） | 同上 | **1 failed**：R+（替换在航 + 160ms 壳包裹徽章断言） |
| M-E1 | `_kindTitle` 注入「已掌握」认证措辞 | `--name 'E 证据印章接线'` | **2 failed**：E+（`已掌握 findsNothing` 钉 + 标题精确匹配）+ E-（标题匹配） |

全部 `git checkout --` 逐字节还原，还原后复跑 10/10 绿。实现方 mutation ×3（摘除接线）与本次互补：接线存在性、播放语义、key 语义、词表钉四面均可失败。

## E. 探针 A——纠正换载荷重播主张 → **F-1**

**发现 F-1（severity: MEDIUM，文档/证据失实，非门失守）**：三处断言「纠正换载荷经 AnimatedSwitcher 换代 = 新提案播一次」——`stuck_journey_sheet.dart:207-208`（接线注释）、`run_manifest.json` `wiring_sites[0].semantics_kept`、`diff_or_evidence_only.md` §1；`limitations.md` #6 承认 P 组未单独钉该行为、但仍按事实口径复述。

**复现（探针临时测试，验后已删）**：仓库 startJourney 返回 practice 载荷、correct() 返回**不同** intervention（explain）载荷 → pump sheet settle → `notifier.correct(...)` → `pumpAndSettle` → 新文案「先补一补这部分概念」在场（新载荷确已渲染）→ `pump(40ms)` 采样：**Opacity = [1.0]（零在航），TweenAnimationBuilder 壳为初挂载旧实例**。根因（读码）：`stuck_journey_provider.dart:108-123` correct() 全程 `status: ready`，`AnimatedSwitcher` 子 key 恒 `ValueKey('stuck-journey-ready')` → 同 key 同型 = 原地更新、无换代；TweenAnimationBuilder tween end 不变 → 不重播。**实测：纠正后新提案不播入场动画。**

**结论**：接线满足裁决（组件有主、挂载播一次、取消即卸载、abstain 缺席、门零放松）；「纠正重播一次」是注释/证据对行为的过度声明。实际行为（纠正不重播）偏保守、不构成乐谱行失格。处置建议（闭账时择一）：① 修正三处措辞为「纠正换载荷原地更新、不重播（同 tween 契约）」并在 limitations 如实登记；② 若 leader 裁决纠正应重播，需按组件契约「内容刷新由调用方换 key/新实例承担」补换代机制+测试（新小卡）。审查不要求本卡返工代码。

## F. 回归重跑（靶5）：全部复现

| 套件 | 实现方声称 | R1 亲跑 |
|---|---|---|
| `test/core/design/semantic_motion_wiring_f569_test.dart` | 10/10 | **10/10 passed** |
| `test/core/design/`（全目录，含 S01 既有套件） | 271/271 | **271/271 passed** |
| `test/features/recovery/ + test/features/insights/` | 67/67 | **67/67 passed** |
| `test/widget/u15_longtail_closure_guard_test.dart` | 14/14 | **14/14 passed**（实录 `U15 repeat 复跑数 = 48（基线 49）`） |
| `flutter analyze --no-pub` | 零 issue | **No issues found!** |

## G. repeat 棘轮（靶6）：48 亲验

`grep -rln '\.repeat(' mobile/lib --include='*.dart' | wc -l` = **48**（≤ 冻结基线 49；FIX-565 摘 typing_text 后合法清理值）；U15 守卫 B+ 实录同数；三个接线文件均不在 repeat 清单。✓

## H. 零越权（靶8）：成立

- `git diff 8b03350b..b5543af7 -- mobile/lib/core/design/semantic_motion.dart` = 0 行；`-- proto/` 同为 0 行——预算表、proto/WS 面零触碰。✓
- `u15_longtail_closure_guard_test.dart` 在 base..evidence 头 diff = 0 行——U15 冻结集（含 `kRepeatBaseline49`）未被本卡触碰。✓
- 变更面仅：3 个产品文件（各一层包裹壳）+ 1 个新测试文件 + 证据四件套。✓

## I. 边界诚实（靶7）：成立

`limitations.md` 六条逐一核实：review_r1 空位如实登记（本 receipt 即补位）；coordination 远端缺位 diff 自证（U15 判例口径）属实；receipt_id（直调面）≠ 适配器 event_id（F03 契约面）的区分与后续登记属实；U05 排除、widget 测试时钟口径、worktree 环境缺口均如实。发现 F-1 是唯一与实测不符的陈述（见 §E）。

## 编号发现汇总

- **F-1（MEDIUM）**：接线注释与证据三处对「纠正换载荷经 AnimatedSwitcher 换代 = 新提案播一次」的断言与实测不符（实测不重播）。位置：`mobile/lib/features/recovery/presentation/widgets/stuck_journey_sheet.dart:207-208`；`v4/evidence/FIX-569/run_manifest.json`（wiring_sites[0].semantics_kept）；`v4/evidence/FIX-569/diff_or_evidence_only.md` §1；`v4/evidence/FIX-569/limitations.md` #6。复现见 §E。处置：闭账登记 + 措辞修正（或 leader 裁决补换代机制另立小卡）。
- **O-1（LOW，记录性）**：审查任务书建议的 mutation 预期「ReceiptSwap key helper 改用固定串 → 同 key 重投不重播断言应红」不精确——恒定串杀的是 R+（永不播放），重播门由逐 build 换 identity（M-R1a）杀红。两面均被本套件覆盖，测试面无需动作。
- **O-2（LOW，存量、非本卡）**：`mobile/test/widget/u15_longtail_closure_guard_test.dart:300` 注释「本次运行实录应 = 49」在 FIX-565 清理后过时（实测 48）。该文件本卡零 diff，不判本卡；建议后续 bookkeeping 顺手修正。

## 命令与 exit code 清单（R1 会话实录）

| # | 命令 | 结果 / exit |
|---|---|---|
| 1 | `flutter test test/core/design/semantic_motion_wiring_f569_test.dart` | All tests passed（10/10）/ 0 |
| 2 | `flutter test test/core/design/` | All tests passed（271/271）/ 0 |
| 3 | `flutter test test/features/recovery/ test/features/insights/` | All tests passed（67/67）/ 0 |
| 4 | `flutter test test/widget/u15_longtail_closure_guard_test.dart` | All tests passed（14/14，复跑数 48）/ 0 |
| 5 | `flutter analyze --no-pub` | No issues found! / 0 |
| 6 | M-R1a 后 `flutter test ... --name 'R 回执替换接线'` | Some tests failed（+3 −2）/ 1 → 还原后复绿 |
| 7 | M-R1b 后同上 | Some tests failed（+4 −1）/ 1 → 还原后复绿 |
| 8 | M-E1 后 `flutter test ... --name 'E 证据印章接线'` | Some tests failed（+0 −2）/ 1 → 还原后复绿 |
| 9 | 探针 A（临时测试，运行后删除） | 实录 `opacities 40ms after correct: [1.0]`（不重播）；文件已删 |
| 10 | `git diff` 核对（semantic_motion / proto / u15 guard / 八相体） | 均 0 触碰 / 0 |
| 11 | 收尾 `git status` + `git rev-parse HEAD` | 工作树干净、HEAD=b5543af7 / 0 |

receipt 提交：本文件为该提交唯一内容（SHA 见分支 log，不回写本文）。
