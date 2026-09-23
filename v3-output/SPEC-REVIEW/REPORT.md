# SPEC-REVIEW · A 线六卡统一复审（改造→复审闭环收官卡）

> 卡：北极星全旅程战役 · A 纵队设计语言线 SPEC-REVIEW ｜ 2026-09-23 ｜ worktree **wt201**（base **7a2849c6**）
> 性质：**纯审查，零代码改动、零测试执行**。全部代码引用为只读走查（Read/grep）实测；守卫结论 = 读账目（两份基线 JSON）+ 只读跑守卫脚本（无 `--update-baseline`，零写入）；未跑任何 flutter test / pytest。
> 复审对象：A-SPEC-V1_1（SPEC v1.1 提案卡）+ 五张改造卡 SPEC-A（#1/#3/#5，wt176）、SPEC-B（#2/#8/#9，wt177）、SPEC-C（#4/#6，wt178）、SPEC-GUARD（#7/N1，wt184）、SPEC-J（#10，wt195）——六卡在**合并后同一棵树**上的协同性。
> 审查基线说明：派卡时主仓 HEAD=24e64b7f（其 diff 相对 7a2849c6 仅 `v3/.sparkle_v3_fleet_state.json` 一行，**代码树逐字节同构**）；复审进行中主仓 HEAD 前移至 8fa0a3a2（LEADERBOARD-DEBT 删 1143 行死链 + wt199），已核其触碰面（leaderboard 三文件 + routes/endpoints/l10n 删键），与六卡文件**零交集**，不影响本报告任何结论。以下 file:line 均为 @7a2849c6（= 派卡时主仓 HEAD 代码树）实测。

---

## ① N1-N8 + top10 落地状态总表（红蓝裁决）

### 1.1 SPEC v1.1 八条增量（N1-N8）

| 条 | 裁决 | 落地证据（@7a2849c6 实测） | 残留 |
|---|---|---|---|
| N1 sprint 第 10 治理面 | **过** | `scripts/guards/check_ux_component_convention.py:52-54` 扫描根 +`features/plan/presentation`（带 N1 依据注释）；`ux_component_convention_baseline.json` 登记 plan 域 14 文件（sprint_screen 登记为迁后值 rawSpinner=3、其余全零）；`v3-output/DL-R3/SPEC.md:27`（§0.2 定义段）、`:547`/`:565`（§8 标题+矩阵 sprint 行）、`:667-680`（新增 §8.10）四处入册；守卫在合并树实测 PASS（rawButton 31/31、rawChip 16/16 等，111 files，本复审只读复跑） | 无 |
| N2 跨面派生值单算 | **部分过** | sprint 侧已收敛：`sprint_screen.dart:230-232` 只认 `examSprintDashboardProvider` 服务端 `days_left`（planId 匹配门），全文件 `DateTime.now()`=0（grep 实测）；降级位展示目标日不走推算（:306-314）；跨屏同源断言测试在 `sprint_screen_test.dart`（#1 用例：故意矛盾桩 daysLeft=5 vs 本地推算 160 天，断言 5 出现、160 findsNothing） | ①§9.4 第 5 条（服务端下传值优先/禁新增本地推算）**未回写进 SPEC.md**（:710-716 §9.4 正文仍 4 条）；②同域旁路双算仍活：`plan_context_summary.dart:597`（`plan.targetDate!.difference(DateTime.now())`，plan 详情页倒计时——恰是 sprint 屏复盘钮 :319-327 push `/plans/{id}/review` 链路的邻近面）、`active_goal_provider.dart:414`（goal 域同型推导） |
| N3 呼吸禁令（实现无关口径） | **部分过** | 两个点名存量靶全灭：chat `_ReasoningBreathOverlay` 3s repeat(reverse)→320ms `forward()` 单次入场（`chat_screen.dart:3850-3854`，:3866-3868 reduce-motion 逐字保留）；exam DayZero 3000ms repeat(reverse)→单次入场+静止定帧（`exam_sprint_dashboard_card.dart:268-278`，DecorationMode 门控保留） | ①**守卫扩维未交付**：`check_dl_spec_ratchet.py` DIMENSIONS（:185-198）无「长周期 repeat 模式」维，`breathingController` 维仍只按命名匹配（=1/1，命中的是 `prism_card.dart:21` 的字段名）；②第三只活体同型未裁决：`prism_card.dart:27-31` features 域 2000ms `repeat(reverse: true)` 呼吸，无 DecorationMode 门控（initState 无条件启动）——正是 C-G2 预言的「home 同型」；③`chat_screen.dart:3794-3798` `_BlinkingCursor` 500ms repeat(reverse) 仅 reduce-motion 门控，按 N3 文义需白名单登记而白名单机制不存在 |
| N4 屏级错误三件套 + Object 插值禁令 | **过** | sprint：`sprint_screen.dart:208-215` `CustomErrorWidget.page`（人话标题+影响句+重试钮，`onRetry: ref.invalidate(planDetailProvider)`）；galaxy：存储收窄 `GalaxyError?`（`galaxy_screen.dart:163`）+ 三档人话映射 `_galaxyLoadErrorMessage`（:3784-3795）+ 面板只走映射（:3102-3105），`'$_loadError'` 插值代码位清零（唯一残留在 :161 注释里）；两侧验收测试均在（sprint test 错误态用例断言 `textContaining('boom')` findsNothing；galaxy test 断言 SocketException 文案 findsNothing） | N4 条文本身未回写 SPEC.md §4.5（见 N8/采纳缺口） |
| N5 截止临近色阶 | **过（附勘误）** | `_urgencyAccentColor`（`exam_sprint_dashboard_card.dart:1041-1045`）：≤1d error / ≤7d warning / 其余 brandPrimary，色源走 `context.colors`（CB-friendly 随主题切换）；翻转范围收敛至 header（:74→图标+模式 pill）+ 倒计时数字（:494）两处；任务组回归中性（:192）、计划名 chip 回归中性面（:508-528）；测试断言三档色值 + daysLeft=5 全树 `everyElement(isNot(semanticError))`（exam card test :222 组） | 勘误：N5 条文「≥7 天中性层 → ≤7 天 warning」在 7 天处自相重叠，实现（含测试边界 daysLeft=7→warning）取 ≤7 warning——建议在 SPEC 文本订正为「>7 中性」 |
| N6 预测数准入四件 | **过** | ②口径行 `examPassProbabilityEstimate` 就地可见（:657-663）；③低档兜底按最终值判定（:583-584 `probability < 0.4`）+ 动作文案（:664-674）；④色源 `context.colors.error/warning/success`（:686-690，禁静态 DS 直读有注释钉）；④动画 320ms 正典（:13 `_kCanonicalEntrance` + :556-558）；测试 4 条（exam card test :305 组，含 Okabe-Ito 色值 0xFFD55E00 断言） | 无 |
| N7 metric tile 非 pill + `*Pill` 后缀禁令 | **部分过** | 规则成立（sprint 侧旧 pill 已随重写消失，SPEC-GUARD 复核零定义零引用）；tile 语义归 GraphiteCardSurface 家族（sprint 成就卡 :408） | exam 卡 `_MetricPill`（:740）/_ModePill（:1006）仍在（parallelClass=2 冻结）——SPEC-B 深改该文件（669 行 patch）却未触发「随触碰迁移」，因 N7 未定义「触碰」粒度（文件级 or 类级），两卡各按宽义理解后无人迁移；条文亦未入 SPEC.md |
| N8 台账行回写 | **不过**（工程已落、账未回写） | 工程实质：top10 全落地（见 1.2），v1.0 台账 §10.5 存量行如实 | **§10.5（SPEC.md:763 起）一行 v1.1 行都没回写**——N1 入守卫根/N2 双算收敛/N3 呼吸/N4 错误态/N5 色阶/N6 弧/N7 更名/锤内规范 3 半句（覆盖件不遮节点）/0xE6101929 token 化/5-Tab 漂移备忘，10 行承诺全数缺席（v1.0 自立规矩「每张卡合入后回写」）；`0xE6101929` 字面量仍在 `galaxy_screen.dart:4080`（X-G6 撤件案被砍后「随触碰 token 化」，至今未触碰、亦无台账行认领） |

### 1.2 top10 改造清单

| # | 改造 | 裁决 | 合并树证据（实测） | 备注 |
|---|---|---|---|---|
| 1 | 冲刺倒计时与进度口径归一 | **过**（子项 S-G9 **不过**） | :230-232 服务端 days_left；:286-291 `sprintProgressScope` 口径行；daysLeft==0→`examDay`、<0→`sprintEnded`（:298-302）；跨屏同源测试在 | **S-G9 重复文案未删**：同一张 exam 卡宽布局下 `_HeadlineBlock`「今日进度 x/y」（:485-486/:500-506）与弧旁「今日已完成 x/y」（:649-651）同数字两种措辞仍并排——SPEC-A 按文件所有权移交 wt177，SPEC-B 未接（卡内零申报），**移交无显式签收人，落空** |
| 2 | 通过率弧规范化 | **过** | 见 N6 四件 + 测试 | 无 |
| 3 | sprint 屏三态补齐 | **过**（子项日期拼接**部分**） | 错误态三件套（:208-215）；任务空态 EmptyState 三要素+单 CTA（:180-191，旧 key `sprintNoTasks` 已从 arb 删除，实测 None）；骨架三段贴真实布局（:683-818：header 卡/40×40 圆环成就行/整宽任务卡行，80×80 方块清零）；三态测试各 1 | 「骨架→内容 golden 前后帧」以结构断言替代（SPEC-A 诚实申报，仓库无 golden 基建，成立）；`'${group.date!.month}/${group.date!.day}'` 手工拼接仍在 exam 卡 :858——同 S-G9，移交落空 |
| 4 | galaxy 错误态人话 | **过** | 见 N4 | 无 |
| 5 | sprint 进度位诚实编码 | **过** | `gradient: LinearGradient` 在 sprint_screen 清零（grep=0，横幅改 accentWash 单色+稀有度描边 :505-513）；进度条 valueColor 唯一映射 `_progressValueColor`＝中性/success（:471-472，两处消费 :561-563/:651-655）；稀有度色只留图标环/描边身份位；`_getRarityColor` 两份合一为文件级 `_rarityColor`（:456-467，grep 清零）；测试遍历全屏进度条断言色值 ∈ {neutral500, success} | 无 |
| 6 | chat 等待期持续源裁 1 | **过** | breath overlay 320ms forward 单次（:3850-3854）；等待窗唯一 repeat 源＝阶段胶囊 700ms（`chat_run_phase_indicator.dart:80-83`，reduce-motion 下 pulse=null :249-256）；验收测试 `chat_wait_pulse_source_test.dart` 在（入场终止性+静止定帧+hasScheduledFrame 三断言，SPEC-C 报告判别性说明成立） | `_BlinkingCursor`（:3794-3798）属流式态、与等待窗错峰，SPEC-C 声明不触碰——但它是 N3 文义下的未登记持续源（归 N3 残留，不减本条裁决） |
| 7 | sprint surface 入守卫 | **过** | 扫描根 :52-54；基线 14 文件现值登记；负向探针（临时裸件文件→FAIL→删）见 SPEC-GUARD 报告 §5；合并树守卫只读复跑 PASS | rawButton 正则不匹配 `.icon` 变体的盲点如实申报未扩（`check_ux_component_convention.py:62`，exam 卡 :161/:823 两处 `TextButton.icon` 账面隐身）——修法已留卡池 |
| 8 | DayZero 浮动降级 | **过** | :268-278 单次 forward+双门防重播+DecorationMode 分支钉静止；测试含 2.5s 观察窗断言偏移恒 0 | offLadder 基线 -2 未收割（见 ③-R2） |
| 9 | urgency 色阶迁移 | **过** | 见 N5 | 同 N5 勘误 |
| 10 | galaxy 工作视图最小切片 | **过** | 锚点只信服务端 `isReviewRecommended`+`reviewUrgencyScore` 最高（:582-601，无推荐→null 诚实降级 :634-637）；250ms 梯内轮询等入场编排落地（:607-630）；视野档位取「投影+48px 容差计数 ≤20」最宽档（:643-683，档表 :224）；聚焦与 `_focusOnNode` 分离保证 ≤20 语义（:688-716，500ms 梯内 :712）；布局优化后未接管则重定焦（:720-742，320ms）；唯一 chip＝SemanticPill bottom:92（:3428-3454，`_workViewChipNode` getter 构建期诚实隐藏 :747-756）；点击走既有 `_startReviewForNode` 理由链（:760-765）；验收测试 4 例（galaxy_work_view_test.dart） | 超密图兜底/refresh 不重算/chip 无 dismiss 均为申报过的有意收敛（D5 大卡范畴） |

**总裁决：top10 全部落地（10/10 过，其中 2 条带未签收的移交子项）；N1/N4/N5/N6 过，N2/N3/N7 部分过，N8 不过（工程实、账本虚）。单卡验证结论全部与合并树相符，无虚假申报；问题集中在卡间移交与共享账本层——正是复审要抓的面。**

---

## ② 协同检查四项结论

### a. sprint 面（SPEC-A 三态+口径）× exam 卡（SPEC-B urgency 三档+通过率弧）——**协同成立，一处跨卡语义分叉**

「同一屏」的实际形态：exam 卡挂 home 仪表盘两处（`dashboard_screen.dart:685/:1213`），sprint 屏是独立路由——用户在一条旅程里先后看同一组冲刺事实（N1 把两文件定义为**一个** surface）。

- **令牌/间距**：两侧全走 DS 令牌梯（sprint `DS.lg/md` + GraphiteCardSurface；exam `spacing16/18/20` + DashboardSectionShell hero），无裸色冲突、无栅格打架。progress 编码两侧一致收敛（sprint 中性/success；exam 弧走 N6 语义槽）。
- **协同增量（合并才可见的好结果）**：sprint 屏倒计时现在与 home 卡同源（`examSprintDashboardProvider` 单 provider 双消费，跨屏测试钉死）——两屏数字不可能再打架，这是单卡验证覆盖不到的面，合并后成立。
- **分叉点（不过项）**：同一倒计时数字两侧色语义不一致——exam 卡按 N5 三档（≤7d warning 染倒计时数字+header），sprint 屏 pill 恒 `PillTone.brand`（`sprint_screen.dart:297-305`，SPEC-GUARD 注释明言「不引入 N5（防双 owner）」）。用户在 daysLeft=3 时 home 见橙色、进冲刺屏见 brand 色同值。两卡注释互相知情、属**有记录的让位**而非事故，但 N1 既然并成一格 surface， urgency 语义就该一格统一。`PillTone` 枚举现成有 `warning/danger`（`semantic_pill.dart:7`），收敛成本 S。

### b. galaxy 工作视图（SPEC-J）× galaxy 错误面（SPEC-C）——**协同成立，结构上互斥，无死角**

- 代码结构描述（截图级）：加载失败时 build 在 `galaxy_screen.dart:3093-3109` **提前 return** 全屏 `_StatusPanel`（人话标题+三档人话正文+重试钮）——此刻画布 Stack（含聚焦视野与 chip）根本不构建，`_workViewChipNode` 无消费点。两态物理互斥，不存在「聚焦态下错误面被 chip 挡住」或反向遮盖。
- 重试闭环：`onAction: _loadGraph`（:3107）默认 `preserveCamera=false` → :525-529 清 `_loadError` 置 loading → 数据落地 `_applyGraphData` 非 preserve 路径重新挂 `_scheduleWorkViewFocus`（:883-887）——**错误恢复后工作视野自动重新武装**，chip/聚焦不会因一次出错而永久消失。
- 计时器安全：聚焦轮询 Timer 在错误窗口触发时 `_resolveWorkViewAnchorNode` 读 null graph 直接返回（:583-586），无误聚焦。
- 布局共存：chip 在 bottom:92（FAB bottom:18 上方 :3455-3473），「还没有掌握记录」横幅在 top:56（:4080 一带，X-G6 砍单保留件）——纵向三段互不重叠。

### c. chat 等待单源（SPEC-C）× sprint 骨架（SPEC-A 重拼）——**动效节奏协同成立，正典集统一，但 N3 缺「执法权」**

- **320ms 正典集在合并树上实现了统一**：全部六个新/改入场动效收敛到 320——chat 呼吸单次入场（chat_screen :3852）、DayZero 入场（exam :13 共享常量）、通过率弧入场（exam :558）、galaxy 重定焦（galaxy :739）；等待期唯一持续源＝胶囊 700ms（N3 等待窗豁免的恰 1 个）；galaxy 聚焦 500ms / 轮询 250ms 均在梯内（SPEC-J 曾被守卫抓到 520/240 并已改梯内，守卫闭环有效）。
- sprint 骨架用 owner 件 `SparkleSkeleton`（1200ms repeat 微光，`core/design` 域，N3 scope 是 features 域故不违条）——架构正确：加载循环属 loading 态语义、入场属一次性语义，两类不同册；骨架重拼后跳变消除。
- **缺口**：N3 的守卫扩维（长周期 repeat 扫描+白名单）六卡无一人交付，导致节奏统一目前靠**卡内自觉**而非机检——`prism_card.dart:27-31`（2000ms 呼吸，features 域，无门控）与 `_BlinkingCursor`（500ms，仅 reduce-motion）在合并树上仍是账外件。见 ③-R1。

### d. 守卫（SPEC-GUARD 入册）× SPEC-J 新代码——**相容，账目干净**

- 只读复跑两守卫：UX-COMP **PASS**（rawButton 31/31、rawSpinner 22/22、rawChip 16/16、parallelClass 159/159、colorLiteral 121/121，111 files）；DL-SPEC ratchet **PASS**（offLadder 182/184、gradientLiteral 302/303 等 14 维）。
- SPEC-J 的 chip 走 `SemanticPill`（非 raw Chip）→ galaxy_screen rawChip 账面保持 1（存量 header `ActionChip`，:3056），零新增；聚焦/轮询时长全部梯内（守卫曾实抓实改，见 c）。
- 账目核对：`ux_component_convention_baseline.json` plan 域 14 条与 SPEC-GUARD 报告 §1.3 表逐条一致；chat_screen stale 条目坠落成立（现值全零→NEW FILE 零容忍语义，严格更强）。
- **未收割的 ratchet-down（合并窗口债）**：`dl_spec_ratchet_baseline.json` 仍冻结旧值——exam 卡 `offLadderDuration: 2`（实况 0：1200/3000ms 已退役）、sprint_screen `gradientLiteral: 1`（实况 0）、chat 呼吸 3s 亦在其中。守卫语义是「现值 > 基线才 FAIL」：这两格 slack 意味着**已退役的 1200/3000ms 若回潮仍不报警**——六卡挣下的 ratchet-down 没入账，防护被稀释。SPEC-A/B/GUARD 三卡都不约而同申报「基线由合并窗口刷新」，主会话窗口未执行。见 ③-R2。

---

## ③ 修复建议清单（按价值排序，供下轮卡池；本卡零代码不修）

| R# | 建议 | 文件/改法 | 量 |
|---|---|---|---|
| R1 | **N3 守卫扩维 + 白名单登记**（防已修的面回潮、了结两只账外活体） | `check_dl_spec_ratchet.py` 新增维：扫 features 域 `repeat(reverse: true)` 与 ≥2s `repeat()`，无 DecorationMode/PerformanceTier 门控即计；白名单首批登记：胶囊 700ms（等待窗豁免）、`_BlinkingCursor`（或顺手加门控）；`prism_card.dart` 2000ms 呼吸迁移单次入场或加门控（SPEC-C #6 同款改法有现成范式） | M |
| R2 | **合并窗口基线收割**（一行命令，价值/成本比全场最高） | 主会话在无并发卡窗口跑 `python3 scripts/guards/check_dl_spec_ratchet.py --update-baseline`（脚本自带 refuse-to-raise 保护）：offLadder 184→182、gradientLiteral 303→302 入账，退役时长回潮即报警；UX-COMP 侧基线已 current，无需动 | S |
| R3 | **SPEC v1.1 回写 canonical 文本**（消灭规范层双事实源） | 一张纯文档卡：把 N2 第 5 条补进 `DL-R3/SPEC.md` §9.4、N3 口径补进 §2.5/2.6、N4 三件套补进 §4.5、N5 色阶补进 §1.5（顺手勘误「≥7/≤7」重叠为「>7 中性」）、N6 四件补进 §6.3、N7 tile 条补进 §4.1、§10.5 补 N8 十行台账（含 0xE6101929 与「覆盖件不遮节点」半句、5-Tab 备忘） | S-M |
| R4 | **倒计时 urgency 统一到 sprint pill**（关闭 N1 单 surface 内的色语义分叉） | `sprint_screen.dart:297-305` pill tone 按 `_urgencyAccentColor` 同款三档映射 `PillTone.warning/danger`（枚举现成）；顺带把 exam 卡 N5 勘误一起做；测试复用 exam card test :222 组范式 | S |
| R5 | **S-G9 + 日期拼接清偿**（两张卡间的无人签收移交，S 级纯文本） | exam 卡删 ：649-651 `examTodayCompleted` 文本块（保留 `_HeadlineBlock` 主位）；:858 手工拼接改 `formatSparkleDateOnly`/`displayDateOnly`（SPEC-A 已备好唯一入口，一行换）；同时清死 key `planLoadSprintFailed` | S |
| R6 | **N2 旁路双算收敛**（plan 详情页倒计时仍客户端自算，sprint 复盘链路一步可达） | `plan_context_summary.dart:597` 改读 exam payload/服务端 `days_left`（同 SPEC-A 范式）；`active_goal_provider.dart:414` 归入同一清偿或登记台账 | S-M |
| R7 | **rawButton `.icon` 盲点扩正则** | `check_ux_component_convention.py:62` pattern 增 `(?:ElevatedButton|FilledButton|OutlinedButton|TextButton)\.icon\(`，全基线随 R2 窗口一并刷新（SPEC-GUARD 已预警会多面上涨） | S-M |
| R8 | l10n 微调（随下个 copy 批，不独立立卡）：`sprintProgressScope` zh「口径：服务端按冲刺任务完成比结算」——「口径」是舰队内部 jargon，宜改用户语言（如「按你完成的任务计算」级，对齐 `examPassProbabilityEstimate` 的语域）；`galaxyWorkViewNextTouch` zh「下一个建议碰」的「碰」字同为内部黑话（en "Next up" 自然），可酌改「下一个建议复习」 | `app_zh.arb` 两 key + gen-l10n | S |

---

## ④ l10n 双语抽查结论（六卡新增 14 key 全量过目）

**总体质量：好，无机翻腔。** 三组人话错误模板（galaxy 三档 + sprint 错误态）共用「你的数据没有丢 / Your data is safe」安抚句式，跨卡口径统一；zh/en 非逐字直译而是各自地道（「还来得及，先攻高频考点」/ "Still time — focus on high-yield topics first" 是范本级）；`sprintNoTasksHint` 把「为何空+影响」一句话讲清；角色后缀规则基本遵守（Title/Hint/Cta/Impact）。两处语域问题见 ③-R8（「口径」「碰」内部黑话入 UI）；另 `galaxyErrorHuman*`/`sprintEndsOn`/`sprintProgressScope`/`displayDateOnly`/`examPassProbability*` 等 8 key 未带 3.2.4 角色后缀，守卫侧无机检（A3.4 未实现），登记为低危漂移风险。死 key `planLoadSprintFailed` 留存（SPEC-A 已申报，归 R5）。

---

## ⑤ A 线整体战报（供参赛材料引用）

A 线设计语言用三步走完了「规范→改造→复审」的完整闭环：**v1.0**（DL-R3）定稿九面治理地图与组件/motion/copy 三册正典；随后北极星三面（聊天/冲刺/星图）对标研究自审出 18 条差距，红蓝辩论砍到 10 条改造 + 8 条增量规范（N1-N8），形成 **SPEC v1.1**——最大发现是结构性的：期末周主场景冲刺仪表盘整域不在任何组件守卫扫描根内，「系统性失控重现」的前兆被立项堵住。**五张改造卡**（SPEC-A/B/C/GUARD/J，五个独立 worktree 并行、文件所有权零重叠）把 top10 全部落地：冲刺屏三态补齐、倒计时口径收敛到服务端单源、通过率弧按「口径行+低档兜底+CB-safe 色源+正典时长」四件准入、urgency 三档色阶终结整卡翻红、chat 等待期双动画源裁到单源、galaxy 裸异常换成人话三模板、星图默认进入「推荐锚点工作视野+唯一下一步 chip」、第 10 治理面带 14 文件基线入守卫。**统一复审**（本卡）在合并树上逐条核验：10/10 改造落地与单卡申报相符、四项跨卡协同全部成立（两屏倒计时同源互锁、星图错误面与工作视野结构互斥且重试后自动重武装、320ms 正典集六处统一、守卫账目对 SPEC-J 新代码零新增违规），同时抓到六卡各自验证覆盖不到的交汇问题——两张卡间的移交子项无人签收（S-G9/日期拼接）、ratchet-down 未入账导致退役时长防护被稀释、SPEC v1.1 八条只回写了不到两条形成规范层双事实源、N3 守卫扩维缺位留下两只账外呼吸活体——全部折价成 8 条修复建议（R1-R8）进入下轮卡池，其中两条是 S 级一行命令/一行换码量级。A 线现状：**10 治理面、双守卫 14+5 维全绿（111 文件在册）、正典集与语义槽五槽制贯穿六张新卡**；设计语言从「文档规范」变成了「有账本、有执法、有复审闭环的治理系统」。

---

## ⑥ 收工核查

- [x] 交付物仅本文件（`wt201/v3-output/SPEC-REVIEW/REPORT.md`）；零代码改动、零 patch（复审卡免 patch）
- [x] 主仓全程只读（仅 Read/grep/git 只读命令）；无 stash/reset/clean 类树操作
- [x] 零测试执行（未跑 flutter test/pytest）；只读复跑了 2 个守卫脚本（无 --update-baseline，零写入），已并入证据
- [x] /tmp 无驻留（全程未写 /tmp）；无进程/模拟器遗留；worktree 内无构建产物
- [x] 顺带溯源：/tmp 发现三份他卡遗留备份 `wt176-SPEC-A-backup`/`wt177-SPEC-B-backup`/`wt178-SPEC-C-backup`（共 144K，2026-09-23 07:2x-08:4x 合入窗口产物，内容已合入并经本复审验讫）——非本卡文件未动，报请主会话确认后可删
- [x] 引用均为 @7a2849c6 实测 file:line / JSON 键值 / 测试文件与用例名；未执行过的验证（golden、测试运行结果）一律标注来源为对应卡报告申报，未冒充实测
