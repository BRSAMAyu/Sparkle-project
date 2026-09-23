# SPEC-FIX · 复审 R1/R3/R4/R5 修复（A 线复审闭环收官件）

> 卡：北极星全旅程战役 · A 纵队设计语言线 SPEC-FIX ｜ 2026-09-23 ｜ worktree **wt204**（base **e1a1d92c**）
> 修复依据：`v3-output/SPEC-REVIEW/REPORT.md` 的四项（按派卡编号 R1/R3/R4/R5 = 复审报告 §③ 的 R5/R3/R1/R4；复审 R2 基线收割已由主会话于 e1a1d92c 完成，R6-R8 低危不入本卡）。
> 回写源：`v3-output/A-SPEC-V1_1/REPORT.md` §4（N1-N8 增量条目原文）。
> 改动面：`exam_sprint_dashboard_card.dart` / `sprint_screen.dart` / `prism_card.dart` / `check_dl_spec_ratchet.py` + 基线 JSON / `DL-R3/SPEC.md` / arb+l10n 生成物 / 三个测试文件。全程未 commit / 未 push。

---

## ① 四项修法（对照复审验收）

### 1. 卡 R1（复审 R5）· S-G9 重复文案 + 日期手工拼接——卡间移交落空的清偿

**S-G9**：`exam_sprint_dashboard_card.dart` 宽布局下同一数字两种措辞并排（`_HeadlineBlock` 主位 `examTodayProgress`「今天已完成 x/y 项任务」 vs 弧旁 `examTodayCompleted`「今日 x/y 完成」）。**取舍：保留主位 `examTodayProgress`，删除弧旁 `examTodayCompleted` 文本块**（连同其前导 `SizedBox(6)`）。理由：①复审 R5 本就指定「删 :649-651、保留 `_HeadlineBlock` 主位」；②更准确的措辞是主位款——「今天已完成 x/y **项任务**」带单位与宾语，x/y 的分母语义（今日任务总数）就地可读，符合 §6.1「结论+带口径数字」；弧旁「今日 x/y 完成」语序含混（可误读为比例式「x of y」）；③弧旁区只剩 N6② 口径行，面积效率提升（§0.2）。**验收**：新增测试断言「今天已完成 2/3 项任务」`findsOneWidget`、`textContaining('今日 2/3')` / `'2/3 完成'` `findsNothing`；既有两处旧断言（`'今日 2/3 完成'` findsOneWidget）反转为 findsNothing。死 key `examTodayCompleted` 随之清偿。

**S-G10**：`:858` 手工拼接 `'${group.date!.month}/${group.date!.day}'` 改走 `formatSparkleDateOnly(group.date!, context.l10n)`（`date_formatting.dart` 唯一入口，SPEC-A 先例一行换）。zh 由「9/20」变为「9月20日」（en 保持「9/20」形态）——X3 防复发，双语各自地道。**验收**：新增测试断言展开未来任务组后 `'9月20日'` `findsOneWidget`、`'9/20'` `findsNothing`。

附带：死 key `planLoadSprintFailed`（复审 R5 点名、全仓消费者普查为零）一并从 zh/en arb 删除；`flutter gen-l10n` 重新生成，`check_l10n_regen_parity` PASS（11202 keys 一致）。

### 2. 卡 R3（复审 R3）· SPEC v1.1 双事实源回写 canonical

把 A-SPEC 报告 §4 的 N2（后半）/N3/N4/N5/N6/N7/N8 逐字回写 `v3-output/DL-R3/SPEC.md`，形制照 N1 已回写体例（blockquote + `【v1.1 N# 增补 @A-SPEC，落地 @…】` 标注），**只回写不改写**：

| 条 | 落点 | 标注 |
|---|---|---|
| N2 后半 | §9.4 增补第 **5** 条（跨面派生值：服务端下传值优先/禁新增本地推算 + A9.5 跨屏断言验收） | 落地注记：sprint 侧工程收敛 @SPEC-A/#1，旁路双算存量归 R6 |
| N3 | §2.6 末（呼吸禁令实现无关口径 + 等待窗豁免 + 守卫扩维条文） | 存量靶清偿 @SPEC-B/#8+@SPEC-C/#6，守卫扩维 @SPEC-FIX |
| N4 | §4.5 末（屏级错误三件套硬性 + Object 插值禁令例证） | 落地 @SPEC-A/#3 + @SPEC-C/#4 |
| N5 | §1.5 末（截止临近三档色阶） | 落地 @SPEC-B（exam 卡）/ @SPEC-FIX（sprint pill 收敛）；**附【v1.1 勘误 @SPEC-REVIEW】**：「≥7 天中性」与「≤7 天 warning」在 7 天处重叠 → 统一「**>7 天中性**」（7 天归 warning，实现与测试边界 @SPEC-B 已按此） |
| N6 | §6.3 末（模型预测数准入四件） | 落地 @SPEC-B/#2 |
| N7 | §4.1 末（指标瓦片非 pill + `*Pill` 后缀禁令） | tile 归位 @SPEC-A；exam 卡 `_MetricPill`/`_ModePill` 冻结未迁（parallelClass=2） |
| N8 | §10.5 台账（A-SPEC 九行台账表逐字回写 + 回写时点状态勘定注记） | 勘定注记逐行核对复审 §1.1/1.2 裁决：N1-N6 已落地、N7 半、0xE6101929 续挂、5-Tab 待批 3 |

**对照检查**：N3-N8 条目正文与 A-SPEC 报告逐字一致（diff 可验）；勘误/状态勘定均以独立标注行存在，未改写逐字原文。

### 3. 卡 R4（复审 R1）· N3 守卫扩维缺位——两只账外活体的处置

**prism_card.dart（活体一）**：2000ms `repeat(reverse: true)` 无门控呼吸（复审点名的 C-G2「home 同型」预言体）**退役为单次入场**——正典集 320ms `forward()` 一次，折射辉光 alpha 0.1→0.3 到位即静止定帧，不再占 home 屏 §2.6 持续动画源名额；`DecorationMode` 门控保留（SPEC-B #8 DayZero 同款范式：animated 档单次播、staticFrame/off 档 didChangeDependencies 钉静止位、防依赖重建重播）。**验收**：新增 `prism_card_test.dart` 三用例（SPEC-B/C 先例范式）——①入场终止性：320ms 到静止位 alpha=0.15，持续观察 2.5s（覆盖旧 2000ms 完整往返周期）alpha 恒定 + `transientCallbackCount==0`（旧 repeat 实现三项全挂）；②staticFrame 档首帧即钉静止位；③reduce-motion（high tier + disableAnimations）首帧即钉。附带收益：prism 的 `Duration(milliseconds: 2000)` 本是 offLadder 存量（基线账面 1 处），随本修清零——offLadder 182→181 为本卡挣得的合法 ratchet-down。

**_BlinkingCursor（活体二）· 白名单裁决（裁决链见 ④）**：裁决为**平台惯例流式光标，非违规呼吸——入白名单登记，代码不改**。

**守卫扩维（执法权落地）**：`check_dl_spec_ratchet.py` 新增 **`persistentRepeatLoop` 维**（A2.3/N3，features 域）——扫 `.repeat(reverse: true)`（任意周期，手写呼吸模式的实现无关口径）+ 裸 `.repeat()`（仅当文件声明 ≥2000ms 周期时长时计）；文件级门控豁免：引用 `DecorationMode`/`resolveDecorationMode`/`PerformanceTier` 的文件视为已过 N3①门控、计 0。**白名单登记制**（`PERSISTENT_REPEAT_WHITELIST`，path→registered reason，入册必须带理由）：首批两条——`chat_screen.dart`（_BlinkingCursor，理由见 ④）与 `chat_run_phase_indicator.dart`（N3 等待窗豁免：事件驱动等待期恰好 1 个持续源，700ms 非 reverse 且 <2s 本不在扫描口径内，登记以昭豁免依据）。自测新增 Case 5（reverse 计数/裸 repeat 需 ≥2s 才计/门控文件豁免/白名单文件豁免/ratchet 抬升拒绝），`--self-test` 全过。实树新维入账 **56 处/30 文件**（存量冻结、新文件零容忍），prism 修后已不在账面。

### 4. 卡 R5（复审 R4）· urgency 色语义分叉收敛

`sprint_screen.dart` 倒计时 pill 恒 `PillTone.brand` → 新增文件级 `_sprintCountdownTone(daysLeft)`，与 exam 卡 `_urgencyAccentColor` **同款三档**：≤1d（含考日 daysLeft=0 与已结束 <0）→ `PillTone.danger`（→ error 槽「不可挽回节点临近」扩展语义）、≤7d → `PillTone.warning`、其余 → `PillTone.brand`（中性 brandPrimary）。N1 既把 sprint 屏与 exam 卡定义为**一个** surface，同一倒计时数字在 daysLeft=3 时不再「home 橙 / sprint 屏 brand」两副面孔；原 SPEC-GUARD「不引入 N5（防双 owner）」注释更新为收敛后口径（owner 仍为 exam 卡 `_urgencyAccentColor`，sprint 侧为同款映射消费）。**验收**：sprint_screen_test 新增 4 用例——三档 tone 断言（brand/warning/danger）+ **三档色值断言**（pill 文字色 == `DS.brandPrimary` / `DS.warning` / `DS.error`，含 7/8 档位边界与考日 0 的 danger），复用 exam card test :222 组的跨档位范式。

---

## ② 实现清单

**代码（mobile/lib）**
- `features/home/presentation/widgets/exam_sprint_dashboard_card.dart`：删弧旁 `examTodayCompleted` 文本块（S-G9，含取舍注释）；日期拼接改 `formatSparkleDateOnly`（S-G10，+import）；N5 注释三处对齐「>7d 中性」勘误。
- `features/plan/presentation/screens/sprint_screen.dart`：倒计时 pill tone 改 `_sprintCountdownTone(serverDaysLeft)` 三档映射（新文件级 helper + 注释）。
- `features/home/presentation/widgets/prism_card.dart`：`_breathingController`(2000ms repeat reverse) → `_entranceController`(320ms 单次 forward) + `DecorationMode` 门控（didChangeDependencies 钉静止/防重播），辉光消费改 `_glowOpacity`。
- `lib/l10n/app_zh.arb` / `app_en.arb`：删 `examTodayCompleted`、`planLoadSprintFailed` 两死 key（均无 @-metadata；消费者普查为零）；`flutter gen-l10n` 重新生成三个 dart 生成物。

**守卫（scripts/guards）**
- `check_dl_spec_ratchet.py`：新增 `persistentRepeatLoop` 维（docstring 表 + 正则组 + `_count_persistent_repeat` + Dimension 注册）+ `PERSISTENT_REPEAT_WHITELIST` 登记制白名单（2 条带理由）+ self-test Case 5（6 断言）。
- `dl_spec_ratchet_baseline.json`：经 `--update-baseline --allow-raise` 入账（脚本注明的 new-dimension sanctioned 路径）。**diff 审计**：既有 14 维总量零抬升；`offLadderDuration` 182→181（prism 2000ms 清零的合法下降）；`gradientLiteral` 302 不动；新增 `persistentRepeatLoop: 56`/30 文件纯增量。约束「182/302 不许超」满足（181/302）。

**规范文档（v3-output/DL-R3/SPEC.md）**：§1.5/§2.6/§4.1/§4.5/§6.3/§9.4(第5条)/§10.5 七处回写（+42 行），N3-N8 逐字、N2 后半照条文、N5 附勘误行、N8 附状态勘定行。

**测试（mobile/test）**
- 新增 `features/home/presentation/widgets/prism_card_test.dart`（3 用例：入场终止性/静态档/reduce-motion）。
- `exam_sprint_dashboard_card_test.dart`：2 处旧断言反转 + 新增 SPEC-FIX R5 组 2 用例（S-G9 文案断言、S-G10 日期令牌断言）；N5 组标题补勘误标注。
- `sprint_screen_test.dart`：新增 SPEC-FIX R4 组 4 用例（三档 tone + 三档色值 + 7/8 边界 + 考日 0）；`host()` 增可选 `scopeKey`（同 tester 二次 pumpWidget 换 provider 档位必须换 key——Riverpod ProviderScope 元素原位复用、overrides 不重建）。

**测试结果（对比法）**：直接面 3 文件 **33/33 全绿**（exam 卡 20 含新增 2、sprint 屏 10 含新增 4、prism 3 全新）；间接消费面 **12/12 全绿**（router_smoke / chat_review_banner / chat_scroll / aurora_daily_startup_retry）；`chat_wait_pulse_source_test`（SPEC-C 先例，验证 _BlinkingCursor 所在屏未被本卡波及）**2/2 绿**。改动面测试**零新增失败**——所有失败均为本卡新断言在旧实现语义下的必失败项（TDD 红转绿），无一条预存用例由绿转红。三守卫终态全绿（见上）。

---

## ③ 冲突面声明（对同轮三张在航卡逐个核对）

| 卡 | 面 | 与本卡交集核查 |
|---|---|---|
| wt198 | northstar_eval（评测） | 无交集。本卡不触 backend/、scripts/devtools/、proto/；wt198 若触 exam payload 服务端形状，本卡 sprint/exam 消费侧只读该字段未改形状（`days_left` 原样）。 |
| wt200 | mobile 实测（只读） | 无代码交集；其截图/实测基线若含 prism 呼吸动效或 sprint pill brand 色，属**预期视觉变化**（本卡正是改这两处），验收时以本报告 §①3/§①4 为准。 |
| wt203 | 纯编纂 | **唯一需要主会话留意的面**：若 wt203 触碰 `v3-output/DL-R3/SPEC.md`（编纂候选高概率文件），合入窗口需与本卡 42 行回写做 3-way。本卡对 SPEC.md 为纯增量 blockquote/条目（七处锚点：§1.5 末、§2.6 末、§4.1 末、§4.5 末、§6.3 末、§9.4 第 4/5 条间、§10.5 表后），未改写任何 v1.0 原文，冲突面天然窄。 |

本卡触碰文件全集（13 改 + 1 新）：见 `git status` 与 `changes.patch`；与三卡申报面零文件重叠（SPEC.md 为潜在文本级冲突，已如上声明）。

---

## ④ 诚实申报

**_BlinkingCursor 裁决链（必写项）**：
1. **语义定位**：该组件是 chat 流式应答时消息尾部的输入光标（caret），500ms `repeat(reverse: true)` 闪烁表达「正在书写」——与全平台文本输入的 caret 闪烁惯例（WebTerminal/EditText/UITextfield 约 500-530ms 周期）同构，属**状态信号**而非装饰性呼吸；它没有「活着感」的氛围语义（那是 D-1 删除对象的核心特征）。
2. **N3 文义核对**：N3 口径下 500ms `repeat(reverse: true)` 确实计为持续动画源，须①门控②占名额。现状门控为**渲染层** reduce-motion（build 内 `context.reduceMotion` 分支返回静态 Container）；事件窗口绑定（仅流式光标位挂载，流结束随消息落位卸载），等待窗豁免的名额逻辑同样适配（流式期它就是该窗口的持续源）。
3. **裁决**：平台惯例 + 事件窗口绑定 + reduce-motion 渲染门控三者齐备 → **白名单登记**（`PERSISTENT_REPEAT_WHITELIST` 首条，理由已入册），代码不改——复审 R1 本就给出「白名单**或**顺手加门控」两可，加门控（如 reduce-motion 下 stop controller）属锦上添花，不重复动刀。
4. **申报残余**：reduce-motion 下其 AnimationController **仍在跑**（门控在渲染层不在 controller 层）——ticker 未省、仅画面静止。这是旧代码形态，复审已知情（「仅 reduce-motion 门控」），本卡未扩大触碰面；若后续要收，S 级一行（reduce-motion 分支 stop），登记于此供下轮卡池取用。

**守卫启发式的已知局限**（ratchet 语义下只影响「冻什么」，不影响「不涨」）：①门控判定是文件级文本匹配（引用 DecorationMode/PerformanceTier 即豁免）——`unified_omni_bar.dart` 实际受 decoration_policy 管辖但本文件未引用该符号，被计入账面 1 处；门控在父层/组件外的情况会被误冻，后续可经白名单登记或门控符号显式化清偿。②裸 `repeat()` 的 ≥2s 判定是文件级时长共现，非逐 controller 关联——可能把「文件内有 2s 一次性动画 + 文件内有 <2s 裸 repeat」误计，冻进基线同样只冻不涨。③靜态扫描不含 PulseScope/painter 重绘类持续源（N3 全口径需运行时计数，超出本卡）。

**其他申报**：
- 基线 JSON 是共享态：§9.1 规定「持卡编辑 mobile/lib 的卡禁止刷基线」——本卡对其触碰**仅为新维度 onboarding + 本卡自身挣得的 offLadder -1**，走脚本内置的 sanctioned `--allow-raise` 路径（脚本注释：onboarding new dimension 是唯一合法用途），且 diff 审计证明既有维度零抬升。若主会话认为仍须由合并窗口重刷，重跑 `--update-baseline` 结果应与本卡版本一致（树未再变）。
- 本机测试环境两个与本卡无关的既有现象，如实记录：①同批多文件时偶发 `dart:isolate` 编译 shard 加载失败（单独重跑即绿，三个直接面文件最终合跑 33/33 过）；②`dart analyze` 对 prism 测试 host 函数签名报一条 `require_trailing_commas` info（参数表尾逗号已加仍报，疑似 lint 对 `=>` 体函数签名的误报）；两个直接面 lib 文件无任何本卡新增 info（其余 info 均为触碰文件预存，未顺手扩改）。
- 复审报告引用的 file:line 均为 @7a2849c6 时点，本卡行号已漂移；报告内引用以符号名为准（§11.1 纪律）。

---

## ⑤ 收工核查

- [x] 交付物：本文件 + `v3-output/SPEC-FIX/changes.patch`（2328 行，14 diff = 13 改 + 1 新文件，含 untracked 的 prism 测试）；零凭据
- [x] 未 commit / 未 push；主仓全程只读；无 stash/reset/clean 类树操作
- [x] 验收测试：直接面 33/33 + 间接面 12/12 + SPEC-C 先例 2/2 全绿；改动面预存用例零转红（对比法）
- [x] 守卫：dl-spec ratchet PASS（**offLadder 181≤182、gradientLiteral 302 不超**，新维 56/56 入账）、UX-COMP PASS（31/31、22/22、16/16、159/159、121/121，111 files）、l10n regen parity OK（11202 keys）
- [x] HEAVY 纪律：测试分三小批错峰，每批前 `ps` 查 flutter_tester=0、查 swap（批间 1.12G-1.34G ≥1G）；收工 flutter_tester=0、无模拟器、无遗留进程
- [x] 清理：worktree 内 `mobile/build`（123M）、`.dart_tool`（132K）已删；`/tmp` 本卡产物（baseline 前照、临时 patch、临时探针测试文件）已删/已归位
- [x] `mobile/lib/gen/` 为 gitignored 生成物（新 worktree 缺失致首次编译失败），经 `make proto-gen`（host 工具链回退）在本 worktree 重建——非交付物，不入 patch
- [x] 引用均为本 worktree 树实测（file:line 为收工时点）；未执行的验证不冒充实测
