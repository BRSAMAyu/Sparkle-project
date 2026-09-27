# WT694-REVIEW2 · U-02/U-05 增量联合独立审查（wt694 第二轮）

- 审查会话：wt694（独立审查轮，未参与任一被审修复的实现）
- 日期：2026-09-25 ｜ 审查基线：main@d56a1071（worktree 分支 `agent/node-b/wt694/review2`，未 push）
- 审查对象：U-02 增量 fc4f4a43（V3-FIX-374）；U-05 增量 68c385f6（V3-FIX-376）+ 3ec111c4（V3-FIX-377）
- 方法：diff hunk 亲读 + lib 全域渲染树枚举路径亲查 + 回归锁真测（修前文件检出跑红）+ ratchet 前后双跑。产品代码零改动（红测用临时检出、随即还原；台账零改动，新发现登记 **V3-FIX-384**）。

---

## 裁决一 · V3-FIX-374（U-02 低刺激档零时长 AnimatedSize 框架断言）：**APPROVE（修法与回归锁成立）**，普查说法**部分不实**，存在 1 处漏修面（登记 V3-FIX-384）

### 修法本体复核（APPROVE 依据）

1. **chat_bubble.dart:1240-1257**：禁动效档（`context.reduceMotion`）直接挂载 `messageContent`，standard 档 AnimatedSize 壳（`DS.motionDuration(SparkleMotionToken.micro)` + `Curves.easeOutCubic` + `Alignment.topLeft`）逐参不变——与「语义等价替换、standard 档零变化」声明一致。原 Duration.zero 三元已从该文件移除（`chat_bubble.dart:922` 的 `reduceMotion ? Duration.zero` 属 AnimatedScale，绘制层不参与布局，保留正确）。
2. **sparkle_motion_primitives.dart:450-456（SparkleExitTransition）**：`maintainSize:false && context.reduceMotion` 提前返回 `visible ? animatedChild : SizedBox.shrink()`，不再装 AnimatedSize 壳；standard 档走原 AnimatedSize 路径不变。消费点实测 5 处调用（chat_screen.dart:2351/2638/2661/3441 四 dock 点 + task_guide_panel.dart:154），与提交声明「四消费点 + task_guide_panel」吻合。AnimatedOpacity/AnimatedRotation/AnimatedScale 零时长仅绘制不参与布局的保留口径成立。
3. **回归锁真测（亲跑，非采信）**：worktree 检出 fc4f4a43^ 的两个被修 lib 文件后跑 `test/widget/chat_bubble_reduced_motion_test.dart` → **红**，实录复现精确断言 `A RenderAnimatedSize was mutated in its own performLayout`（RenderAnimatedSize._layoutStable → performLayout 栈帧在案）；还原修复后 **2/2 绿**（low 档零断言 + 渲染树枚举零 `Duration.zero` RenderAnimatedSize；standard 档 AnimatedSize 外壳仍在）。渲染树级断言使该锁不可被「仅改测试」绕过。

### 「19 处普查余量为折叠件硬编码」说法核验：**部分成立——总数对、归因不全**

lib 全域 `AnimatedSize(` 调用点精确普查（grep 枚举，逐点读 duration 表达式）＝ **19 处**，与普查总数一致。分类：

| 类别 | 处数 | 明细 |
|---|---|---|
| 消费 reduceMotion·已修（V3-FIX-374） | 2 | chat_bubble.dart:1245、sparkle_motion_primitives.dart:460 |
| **消费 reduceMotion·未修未登记（漏修面，V3-FIX-384）** | **1** | **aurora_calibration_strip.dart:178** —— `AnimatedSize(duration: DS.motionDuration(SparkleMotionToken.standard, reduceMotion: context.reduceMotion))`，reduceMotion 下即 Duration.zero |
| 折叠件·硬编码·**不消费 reduceMotion**（说法成立） | 2 | collapsible_widget_wrapper.dart:77（`_animationDuration = Duration(milliseconds: 200)` 常量，:56 定义处）、collapsible_slot.dart:70（`DS.motionDuration(SparkleMotionToken.responsive)` 不带 reduceMotion 实参 → 恒 AnimationSystem.responsive 正值） |
| 硬编码 const / const 派生·永不归零 | 14 | dashboard_screen.dart:1445/1965/2480（DS.quick=150ms const）、exam_sprint_dashboard_card.dart:204（400ms）、unified_omni_bar.dart:141、task_board_card.dart:67（DS.quick）、chat_screen.dart:3965（220ms）、calibration_receipt_chip.dart:82（180ms）、inline_translation_block.dart:151（300ms）、plan_context_summary.dart:229（AnimationSystem.normal=250ms）、node_detail_sheet.dart:798（220ms）、statistics_card.dart:100（250ms）、group_chat_bubble.dart:1105、feed_post_card.dart:334（各 200ms） |

- **折叠件子说法核验通过**：两个折叠件文件全文 grep `reduceMotion` 零命中（exit 1）——确实不消费 reduceMotion，故**不可能产生零时长 AnimatedSize**（无崩溃面）；它们在低刺激档照常 200ms 动画属行为差，与 V3-FIX-375「不崩溃，纯行为差」登记一致。
- **普查漏项**：`DS.motionDuration` 返回 Duration.zero 的唯一条件是显式传 `reduceMotion: true`（design_system.dart:1087-1090）；全域 25 处 motionDuration 调用中带该实参且喂给 **AnimatedSize** 的除两处已修外即 aurora_calibration_strip.dart:178 一处（graphite_surfaces 三处喂 AnimatedContainer/TweenAnimationBuilder，:362 另有 reduceMotion 提前返回，均不涉 AnimatedSize）。DYNAMIC_ISSUES V3-FIX-374/375 证据栏「19 处中仅上述两处+已修三处消费 reduceMotion」表述与实况不符（实为 2 已修 + 1 漏修；折叠件两处不消费）。
- **风险定性**：该漏修点挂 home 首屏 dashboard（dashboard_screen.dart:1298），与 chat 回归锁的渲染树不同树，故现锁不覆盖；`reduceMotion = MediaQuery.disableAnimations || accessibleNavigation`（sparkle_context_extension.dart:39-44），低刺激档与 OS 减动效用户展开/收起校准条时走同一零时长 performLayout 自脏机制，崩溃机制同源（本轮未做全栈复现实测，定性为「同机制未收口」而非「实测必崩」）。**建议：V3-FIX-384 按 SparkleExitTransition 同款「禁动效不装壳」收口该处，并考虑将渲染树枚举断言从 chat host 推广到 dashboard low 档 host。**

### 漏修面清单

1. aurora_calibration_strip.dart:178 —— 低刺激/OS 减动效下 Duration.zero AnimatedSize 未收口未登记（本轮新发现，**V3-FIX-384**，grep 复核该 ID 全仓零占用）。

---

## 裁决二 · V3-FIX-376（demo 首屏理解快照错误裸露）：**APPROVE（限定口径：home provider 门控实现为真）；作为 B-04-L-01 的收口不成立——golden 首屏回执卡消费的是 experience 孪生 provider，未修**

### 门控分支真实性核验（实现层面成立）

1. **两入口均可达空态（成立）**：`main.dart:151-154` 在 `runApp` 之前统一置 `DemoDataService.isDemoMode = bool.fromEnvironment('DEMO_MODE') || prefs.getBool('demo_guest_mode_enabled')`——dart-define 入口与持久化偏好入口**汇入同一静态旗标**，provider 不可能在旗标置位前构建；`_fetch` 顶部对该旗标门控（understanding_snapshot_provider.dart:183-196），故两入口下 provider 均返回内建空快照。旗标是入口无关的单一闸门，此口径下「两入口都能进空态」成立。
2. **空快照形态良构**：显式构造 `UnderstandingSnapshot(claims: [], recentlyCorrected: [], memoryDeclarations: [], envelopeStyle: EnvelopeStyleSnapshot.empty(), lastUpdateTime: null, totalClaims: 0, highConfidenceRatio: 0)`，全部 required 字段齐备，`isEmpty` getter（provider 文件:168-172）四条件全真。消费面空态承载亲核：understanding_panel.dart:79/92-94 `empty → _EmptyUnderstandingState` + 空态 subtitle（既有 UI，零新文案属实）；understanding_drawer 同源 watch。
3. **非 demo 路径零改动（成立）**：commit diff 为纯插入（17+/0-），门控块以下的 api.get/解析路径逐行未动；仅 2 文件（provider + 新测试）。
4. **pin 测试亲跑 2/2 绿**（`test/features/home/presentation/providers/understanding_snapshot_demo_placeholder_test.dart`）；case 1（demo 下 provider.future 解析为空快照）为真行为锚。修前红声明未独立复跑（本轮以静态核读 + 修后绿为准）。

### 作为 B-04-L-01 收口的成立性：**不成立（独立复核 + 与 wt693 补记相互印证）**

- **同名双胞胎 provider**：`understanding_snapshot_card.dart:20` watch 的是 `features/experience/presentation/providers/experience_provider.dart:5` 的 `understandingSnapshotProvider`（FutureProvider.autoDispose → `experienceRepository.getUnderstandingSnapshot()`），**无任何 demo 分支**（repo 与 ApiClient 层均无 isDemoMode 拦截，grep 实证）。该卡正是 demo 首屏 dashboard_screen.dart:1007「Aurora understanding receipt」——主叙事句正下的 B-04-L-01 实拍面。修的是 home provider（消费面 = understanding_panel + chat understanding_drawer，前者在 dashboard:1450 折叠槽内默认折叠、后者在 chat），**均不入 golden home 首屏**。
- **pin 测试 case 2 定向失准**：该 case pump 的恰是 experience 卡（错误 provider），断言「树内无 CompactErrorCard」在本轮测试环境 1 秒内通过的原因是网络 future 未及完成、断言落在 loading 骨架窗口（测试打印 API Base URL 后即刻通过，无 DioException 断言路径）——属时序性通过，不构成 demo 契约锚。CompactErrorCard（「ⓘ 加载失败 轻触重试」本体）仍可由 experience 卡在真实 demo 运行中渲染。
- **台账状态核对**：`v3-output/B-04/VISUAL_ISSUES_LEDGER.md` L-01 已由 wt693 重采批补记（commit bb84e122，HEAD 在册）判明同一点并**保持开放**，待修面 = experience 孪生 provider 或其 repo demo 分支。本轮在未读该补记前独立循码得出同一归因（dashboard:1007 导入 experience_provider 而非 home provider），与其相互印证——**非新发现，不占 V3-FIX-384**；376 台账行若按「L-01 收口」口径解读应视 L-01 开放为准。
- 附带核实：`demo_guest_mode_enabled` 当前 lib 内仅剩读与清 false 的写点（auth_provider 7 处 setBool(false)），无置 true 代码路径——入口 2 实际由历史置位/手工置位可达；不影响上述门控逻辑结论。

**裁决口径**：376 作为「understandingSnapshotProvider（home）demo 门控内建空态」的实现按声明成立 → APPROVE；但 B-04-L-01 不因本修收口（ledger 已如此记载），后续需 experience 面同款门控。

---

## 裁决三 · V3-FIX-377（chat fontSize 28 处字面量→同值令牌）：**APPROVE**

1. **替换全景**：diff 计数 `+DS.fontSizeXs` = 26、`+DS.fontSizeBase` = 2，共 28 处 10 文件，与声明一致；`import` 行增量为 **0**（10 文件原均有 design_system 导入，声明属实）。
2. **同值抽查（≥6 处亲核）**：agent_reasoning_bubble.dart 3 处（labelStyle TextStyle 12→DS.fontSizeXs、role 标签 12→Xs、prismPurple 标签 12→Xs）、message_detail_view.dart 时间戳 12→Xs、collaboration_timeline.dart 标题 16→DS.fontSizeBase、intent_preview_dialog.dart 12→Xs——全部为 `TextStyle(fontSize:)` 具位替换，无默认参/级联误伤；`DS.fontSizeXs = 12.0`（design_system.dart:1046）、`DS.fontSizeBase = 16.0`（:1050），**字面量与令牌常量数值相等、类型同 double、const 语义同**。`fontSizeBase` 仅 2 处（collaboration_timeline、agent_workflow_panel），与映射表吻合。
3. **UI-TOKENS ratchet 前后双跑（亲跑）**：pre-377（3ec111c4^ 检出态）`fontSize=669/727（190 files）` → post（HEAD 态）`fontSize=641/727（189 files）`，**Δ=-28 恰等替换数、只降不升**，color 面 237/275 零漂移；641/727 与提交信息所报完全一致。基线 JSON 未动（无 --update-baseline 痕迹，ratchet 余量留出属实）。
4. 族外值（10/11/11.5/12.5/13/14/18）未动只登记的口径与 diff 相符（除 12/16 外无其他字面量被触碰）。

---

## 总裁决与移交

| 项 | 裁决 | 摘要 |
|---|---|---|
| V3-FIX-374（fc4f4a43） | **APPROVE** | 修法正确、回归锁真红真绿（亲测）；普查说法部分不实 |
| V3-FIX-376（68c385f6） | **APPROVE（限 home provider 口径）** | 门控/空态/非demo零改动均真；B-04-L-01 未收口（与 wt693 补记互证，L-01 保持开放） |
| V3-FIX-377（3ec111c4） | **APPROVE** | 28 处同值替换、零 import 增量、ratchet 669→641 只降（亲跑双态） |

**新发现（V3-FIX-384，预分配 ID 已 grep 复核零占用）**：aurora_calibration_strip.dart:178 reduceMotion 下 Duration.zero AnimatedSize（dashboard 面，机制同 374 根因，未被 374/375 登记覆盖）。

**移交建议**：① V3-FIX-384 按 374 同款模式收口 aurora_calibration_strip 并考虑渲染树断言推广至 dashboard low 档；② 376 的 experience 孪生 provider 门控随 L-01 开放项承接；③ 374 普查口径如后续引用，以本轮 19 处三分表为准。

*证据可复跑路径：worktree `agent/node-b/wt694/review2`（/Users/brsama/code/GitHub/Sparkle-sysrev/wt694-review2）；红测 = 检出 `fc4f4a43^ -- <两 lib 文件>` 后 `flutter test test/widget/chat_bubble_reduced_motion_test.dart`；ratchet = `python3 scripts/guards/check_ui_design_tokens_ratchet.py`。*
