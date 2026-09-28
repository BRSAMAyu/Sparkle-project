# U 线（UI 10 卡）深挖章节 —— V4 交接文档素材（wt775）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」U 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt775（2026-09-28，基线 main@ed072fd2）。方法：卡面（v3/07_tasks/cards/U-0*.md）+ wt759 三源核验报告逐卡 SHA → `git log -1` 全部 21 个交付 SHA 逐条重验在主干 → 关键代码开文件亲证（design tokens 守卫/state gate 注册表/notification card 四要素/proposal 分发）→ 测试逐文件计数 → v3-output receipt 抽读（WT671/WT673/WT686/WT689/WT694/U-09）。**未轻信任何台账/报告结论性文字。**

---

## U.0 线级概览

U 线是 V3 的「产品形态线」：把核心旅程从「功能可用」推向「产品化呈现」。10/10 全部 done（tasks.json + fleet done 名单 + wt759 逐卡 SHA 在案）。

执行形态的显著特点（V4 设计者需要知道）：

1. **两波交付结构**：第一波（wt310-wt363，09-22 前后）把卡面主体全部落地；第二波（wt671-wt698，09-25/26）是「双证判定不重做 + 定向续做」——每个续做会话先以 `git merge-base --is-ancestor` + 树内产物证判定前轮已完成的范围，只补真实缺口（典型：wt673 对 U-06、wt675 对 U-07、wt672 对 U-10、wt676 对 U-09）。这个「续做不重做」模式是 V3 后期多线并行的关键纪律。
2. **独立审查密度全线最高**：U-02/U-05 有 wt694 两轮联合独立审查（第二轮在 APPROVE 376 的同时新抓出 FIX-384 漏修面——审查发现新缺陷的实录）；U-04 有 wt689 独立审查 APPROVE（并核验出 FIX-379②③ 的诚实化处置）；U-01 有 wt671 集成 HEAD 复核。
3. **「headless/契约层可交付，真机段诚实转出」是全线常态**：无真机/浏览器权限的 worker 用 widget test + 契约测试 + golden 链承载验收，真机走查段显式转 HUMAN_INBOX 不伪造（U-09 45 张矩阵、U-06 simulator 段、G-05 同族）。**但中央 HUMAN_INBOX（09-27 才创建）未回填这些转出项**（→ 本次登记 V3-FIX-511，§U.5）。

**L2–L5 分层实际达到哪层（卡面编号体系的亲证结论）**：卡面只在标题层标注了 L2（U-05 三屏产品化）/L4（U-06 状态完备性）/L5（U-09 三端一致性 diff），全库无 L1/L3 层的 UI 卡定义（B-04 的「L2–L5 Review Harness」是审查轮次口径，见 v3/07_tasks/TASK_INDEX.md:14）。实际达到：
- **L2（单屏产品化）：达成的面=home/goal/chat 三屏（U-05，双审查 APPROVE）+ memory 控制面（U-03）+ proposal 交互组件（U-04）+ 文案终审（U-10）**；
- **L4（状态完备性）：闸门面达成、非全屏覆盖**——`core/state/` 四件套 22 相位代码化，闸门注册面覆盖率 1.0≥0.95 达标，但注册表仅 8 个 seam（§U.2-U-06），chat/galaxy 主屏未整面接闸（wt358/wt673 两轮如实登记）；
- **L5（三端一致性）：headless 契约层达成，真机 diff 层未发生**——11 契约用例+平台分支审计+允许差异登记表在主干，45 张真机截图矩阵是就绪的执行清单而非已采集证据（v3-output/U-09/SCREENSHOT_MATRIX.md，采集命令可复跑）。

---

## U.1 意图（卡面目标与验收）

十卡共性 Forbidden 条款（卡面原文，全线一致）：不得重建已存在的权威真源；不得用 mock/seed 冒充真实行为；不得只通过静态代码阅读宣称用户体验通过；不得弱化既有安全/幂等/隔离/审计守卫。Worker 只能提交 READY_FOR_REVIEW/PARTIAL/BLOCKED；Reviewer 必须独立执行关键验收。

| 卡 | Risk/Resource/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| U-01 设计表面 Inventory 与组件收敛 | medium/LIGHT/1 | 用真实 screenshot+widget tree 找出核心旅程组件/装饰债，制定迁移顺序 | 组件 owner 唯一；新增 UI 必须用 design system；输出 before screenshots+consolidation plan |
| U-02 Calm/Warm 设计语言与低刺激 | medium/HEAVY/1 | 「纸感书院+现代AI」变 token/policy，接活 low-stimulation dead code | 双模式核心截图过 contrast/hierarchy rubric；低刺激实际减少动效不只是 setting 值 |
| U-03 Aurora/Memory「对我的理解」 | high/HEAVY/2 | provenance/scope/correction 做成普通用户可懂的控制面 | 30 秒能解释知道什么/为什么/怎么改；纠正后界面与下次 decision 同步变化；A/B visual issues=0 |
| U-04 Proposal/Execution/Hybrid Handoff | high/HEAVY/2 | 统一 Action Proposal、diff、approval、turn ownership、run progress UI | GJ06/GJ07 无需读日志知道轮到谁；重复点击不产生重复 command；未知结果不显示成功 |
| U-05 首页/Goal/Chat 三屏 L2 | medium/HEAVY/1 | 三屏共享同一 Goal trajectory 心智模型 | 5 秒测试说出每屏主任务；核心 CTA 唯一；5 Persona screenshot A/B=0；功能不退化 |
| U-06 L4 状态完备性注入 | medium/HEAVY/1 | 系统化覆盖 State Matrix，不再每 feature 自造空/错/加载态 | 核心 surfaces state matrix ≥95% covered；错误全有下一步；>500ms 有 stage feedback；无 terminal spinner |
| U-07 长尾 Contextualization 与导航减负 | medium/HEAVY/1 | 长尾能力放回 Goal/Action context，清除超级App感 | 五 Tab 不增；CORE journey 无关入口不出现；HIDDEN 不可达；CONTEXTUAL 有自然 journey |
| U-08 Accessibility 全链升级 | medium/HEAVY/1 | 核心 Journey 对 screen reader/keyboard/large text/reduced motion 可用 | GJ01/GJ03/GJ08 辅助技术可完成；WCAG AA；不依赖颜色传达关键状态 |
| U-09 L5 三端视觉/交互一致性 Diff | medium/HEAVY/1 | Android/Web/macOS 同 canonical state 真实对比并修平台断裂 | 核心状态三端无 A/B issue；交互语义一致；产出 final screenshot matrix 与 diff report |
| U-10 全产品文案与术语终审 | medium/LIGHT/1 | 黑话/玄学分数/羞辱化鼓励全部收敛 | 核心 journey 无未解释术语/placeholder/raw key；Why/失败/不确定表达合规 |

---

## U.2 实际交付逐卡

### U-01 · 组件收敛与设计系统治理（V4 应把「守卫冻结」当作本卡真正的产物）

**交付（六步链 + 复核，全部有主干 SHA）**

| 步骤 | 主干 SHA | 内容 |
|---|---|---|
| Step 1/3/4/5 | `c99838d5`/`76847722`/`7cf1198c`/`4e406994` | chip/pill 收敛 rawChip 75→11；empty/error/loading 收敛 rawSpinner 79→8；button 收敛 rawButton 87→19（CustomButton 退役）；profile 色字面量 123→103 |
| Step 6+7 | `7590aa1a` | confetti 双挂载修复 + **守卫清单登记（chain complete）** |
| wt671 复核 | `938e1f34`+`e3e68667` | FIX-357/358（扫描根陈旧机械对齐+证据指针诚实化）+ Inventory 刷新：**头注亲证** scripts/guards/check_ux_component_convention.py:6-31 声明基线冻结于 U-01、10 个治理面（9 U-01 surfaces+sprint 第 10 面）、ratchet 只降不升 |

**DS.* 令牌体系的约束力（本次专项核验）**：约束力是**守卫冻结型**而非「全量迁移完成型」——
- `mobile/lib/core/design/` 权威层级 = `tokens_v2/`（唯一事实源）→ `theme/`（context.colors/typo/space/radius/motion 唯一 context 入口）→ `DS`（数值层已冻结 @Deprecated，存量过渡）（v3-output/U-09/WT676_CONSISTENCY_DIFF_MATRIX.md §2，主干文件亲证一致）。
- 使用规模：`DS.` 形态引用 22,129 处 / 577 文件 import design_system（本次 grep 实数）。
- 双 ratchet 守卫在册在跑：`check_ux_component_convention.py`（246 行，per-file 基线只降不升、新文件零违例、squad 域 ZERO/high-water WITNESS 条目）+ `check_ui_design_tokens_ratchet.py`（硬编码色/字号 repo 级棘轮，基线 JSON 在 scripts/guards/）。
- **未迁移面如实可见**（wt676 矩阵实测数）：chat fontSize 字面量 108 处+令牌形 120 处「双态撕裂」（V3-FIX-377 首批修后本次复测仍余 80 处字面量）；galaxy **零 context.typo 采用**（62 处字面量，E1 冻结豁免预算内——视觉锤面迁移需视觉 owner 裁决）；insights/goal/settings 零 context.typo 但面小。**DS 令牌是「新增受闸、存量分期」的治理态，不是「已全量统一」**。

**残差**：① 字面量存量迁移无承接卡（377 首批后再无批次，→ V3-FIX-510 台账行缺失放大了此盲区，§U.5）；② 守卫扫描根不含 galaxy 的 tokens 迁移裁决入口（E1 冻结豁免是预算登记非迁移计划）。

**一句话用户可见行为**：新 UI 不能再引入裸按钮/裸 spinner/裸 Chip/新色字面量（守卫提交闸）；核心屏装饰竞争下降（gradient/particle 统计面在 wt399 rubric 中复核）。

### U-02 · Calm/Warm 令牌与低刺激模式

**交付（四波，末波独立审查 APPROVE）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主体 | `22f99776`（wt353） | tokens_v2/state_tokens.dart（calm/celebrate/attentive 状态令牌）+ 低刺激接进真实 Theme/Animation 链（EmotionResponsiveConfig.lowStimulus → MediaQuery.disableAnimations → context.reduceMotion） |
| 验收收尾 | `acbeb450`（wt399） | 双档核心屏**真实渲染截图**（B-04 harness 同源）+ 可计算 contrast/hierarchy rubric 8/8 + 动效量化对照（45 行矩阵圈定 android 批） |
| F5 收口 | `fc4f4a43`（wt683，FIX-374） | 低刺激档零时长 AnimatedSize 框架断言根因修复（渲染树级回归锁） |
| 独立审查 | `61239f06`（wt694 第二轮） | **374 APPROVE（修法+回归锁经 reviewer 亲跑红绿复核）**；普查说法「部分不实」被纠正（19 处 AnimatedSize 实为 2 已修+1 漏修+2 折叠件+14 硬编码 const）→ 新登记 FIX-384 |
| 384 收口 | `329d8eb7`（wt698） | aurora_calibration_strip 禁动效档「不装壳」漏修面收口（374/384 同指针 FIXED@329d8eb7） |

**卡面验收的真实口径**：「低刺激模式实际减少动效，不只是 setting 值」以渲染树级断言兑现（`chat_bubble_reduced_motion_test.dart` 枚举渲染树零 Duration.zero RenderAnimatedSize，wt694 亲跑红绿）；「双档 rubric 8/8」以 wt399 真渲染截图承载。残差：**FIX-375 OPEN**（FirstActionCard 无标题层——journey 面 hierarchy rubric 两档 FAIL，棘轮 journeyFirstAction:hierarchy:no-heading 保持必红放行；登记为 U-02 验收残余双债之一，10/4 红线内不实施）。

**一句话用户可见行为**：开启低刺激/OS 减动效后，核心屏动效真实关停且不再崩溃（374/384）；calm/celebrate/attentive 状态影响 Aurora 呈现档位。

### U-03 · 「Sparkle 对我的理解」控制面

**交付**：`295fd59a`（主卡）+ `8c6797fc`（five-action 完整：link_task action with task-picker）。
**主干面亲证**：`mobile/lib/features/memory/presentation/` 实存 screens 四屏（memory_panel/memory_detail/memory_settings/understanding）+ widgets 六件（**why_this_receipt_sheet.dart**、understanding_overview_view、evidence_cards/drawer、memory_evidence_badge、pending_commitments/unresolved_conflicts 段件）——四组理解视图+Why-this receipt+修正/删除/改 scope/暂时不用五动作面在树。后端对端=M 线 `/memory/provenance/*` 七路由（M-line 章已深挖，此处不重复）。
**验证**：M 线深挖章（v3-output/WT770-DOC-MX/M-line.md）已核 M-08 receipt 链与 U-03 读面互证；wt673 对 memory 面 6+6+1 处错误 sink 统一为 `uiErrorMessage(l10n, categorizeUiError(e))`（原始异常透传清零）。
**残差**：① 「30 秒解释」验收是 rubric 口径，无真机计时实测记录（组件级 widget 测试在库，三端实机走查未发生）；② A/B visual issues=0 以 B-04 golden 链口径成立（android 批），macOS 批有 ENV-1 字形伪影豁免（B-04 章）。

**一句话用户可见行为**：用户可在 Memory 面看每条理解的来源（why-this receipt）、纠正/删除/改 scope，且下一次 decision 同步变化（M-07 失效管线同事务保证）。

### U-04 · Proposal/Hybrid Handoff 交互组件

**交付（主卡 + 断链修复 + 独立审查 APPROVE）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主卡 | `f7607937` | 统一 ActionProposalCard（chat/task 页复用）+ awaiting user/partial/unknown/cancel/conflict 状态覆盖 |
| FIX-378 收口 | `f00c44d6`（wt687） | **chat 挂载命令分发断链修复**：ActionProposalCard 确认/拒绝/取消经 onWidgetAction 发出 `action_proposal_approve/reject/cancel` 但 chat_notifier_actions 不处理——本次主干亲证 mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart 与 action_card.dart 实存两 handler |
| 独立审查 | `e0cbd3b2`（wt689） | FIX-378 **APPROVE**（断链/幂等/测试三面独立复验）；FIX-379 三项核验属实且 ②③ 处置=纯文档诚实化（「UI 据此提示已确认过」的 docstring 时许诺撤下——HybridJourneyPayload 不解析 step_replay 且成功即卸载，新提示键在唯一活面永不可渲染=造新死面；跨模块幂等键恒等不变量测试留证） |

**残差**：FIX-379 行仍 **OPEN**（X-07 run-step 契约移动端消费面缺口 ②③——按 wt689 裁定挂载卡承接；docstring 已诚实化，无行为缺陷）；「重复点击不产生重复 command」验收以跨模块幂等键恒等不变量测试承载（confirm+cancel 双动作，变异实证）。

**一句话用户可见行为**：聊天页 proposal 卡的确认/拒绝/取消按钮真实生效（378 修后）；用户无需读日志即可分辨你做/Sparkle做/一起做。

### U-05 · 首页/Goal/Chat 三屏 L2 产品化

**交付（主体 + 增量 + 双轮独立审查）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主体 | `cb022dad`（wt315） | 三屏 L2 重构；**首页双渲染真缺陷当场揪出修掉**（REAL double-render defect found+fixed） |
| 增量 | `68c385f6`+`3ec111c4`（wt686） | FIX-376（demo 首屏理解快照错误裸露）+ FIX-377（chat 令牌双态撕裂首批） |
| 独立审查 | `61239f06`（wt694，与 U-02 联合） | 376 **APPROVE 但限定口径**：home provider 门控为真；**作为 B-04-L-01 的收口不成立**——golden 首屏回执卡消费的是 experience 孪生 provider（experience_provider.dart:5，无 demo 分支），wt696 补完（FIX-376 FIXED@bd576cd7 收口孪生） |

**卡面验收**：「5 秒测试」「CTA 唯一」无真机实测记录（headless 结构断言+golden 承载）；「功能不退化」以触达测试族承载（wt694 亲跑 37 绿邻域回归在案）。

**一句话用户可见行为**：首页只突出 Primary Action/Why/Stuck/Run；chat 长建议转 proposal/receipt 结构；demo 模式首屏不再裸露错误快照。

### U-06 · L4 状态完备性注入（「闸门面达标 ≠ 全屏覆盖」的样板卡）

**交付（主体 + 续做，两轮如实登记残余）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主体 | `f644de3a`（wt358） | `mobile/lib/core/state/` 四件套：surface_state.dart（STATE_MATRIX 22 相位 1:1 代码化+14 失败族）、surface_state_injection.dart（debug-only 注入探针）、surface_state_view.dart（统一渲染+死胡同守卫）、staged_loading.dart（>500ms 分阶升格）；三测件（本次逐文件计数：coverage 5+matrix 13+view 17 = 35 个 test 入口，wt358 报告口径 50 用例含循环展开） |
| 续做 | `04867998`+`74962798`（wt673） | cognitive 三面接 StagedSurfaceLoader（裸 spinner+手写双语字面量清零，含一个「英文用户也见中文」的 i18n 缺陷）；14 文件原始异常透传清零；REPORT+patch 入库（交付物必须 commit 硬条款） |

**闸门注册表现状（本次开文件亲证）**：surface_state_injection.dart 登记 seam 共 **8 个**：cognitive.capsules/capsuleJobs/capsuleDetail、community.feed、home.dashboard、plan.diagnosticQuiz、profile.context、shared.loadingState。**chat/galaxy 主屏未整面接闸**（wt358 登记→wt673 维持：chat 自有 ws 状态机已齐 reconnecting/error 分支，整面换闸=重构级，如实不实施）。覆盖率验收「≥95%」的口径=**注册闸门面的真实渲染覆盖率 1.0**（coverage 测试聚合断言恒成立），不是「全 app 95% surfaces 已接闸」。
**其余验收**：34 处残余 CircularProgressIndicator 逐一复核为有界/确定性/已带文案（wt673 §二C，`.when(` 括号平衡扫描 0 缺口）；「无 terminal spinner」同口径成立。simulator 段 DEFERRED（诚实登记）。

**一句话用户可见行为**：已接闸的 8 个 seam 面，加载 >500ms 出现阶段文案升格+可离开提示，错误必有下一步按钮；核心面不再有终结态裸转圈。

### U-07 · 长尾 Contextualization 与导航减负

**交付（主体 + 双证判本体完成续做）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主体 | `8ac6bad5`（wt356） | portfolio 分档执行：LABS 走 unlisted；routes.dart 路由真源零 diff；五 Tab 零改动；只摘 CORE journey 无关入口 |
| 续做 | `233c494a`（wt675） | 双证判本体已完成不重做；DEFERRED 定向六文件 swap 窗内补跑全绿；LABS 暴露边收口（commit 内明示「tasks.json U-07=TODO 脱节报请规格权威核正」——后经协调面核正） |

**与 B-01/wt639 的互证**：B-01 波 2 审计（wt639，690 ALIVE/12 DEAD/2 ORPHAN）在 U-07 之后仍抓出 onboarding 4 屏（FIX-342）、learning-mode（FIX-490）、WS6（FIX-489）等孤儿面——说明 U-07 的「HIDDEN 用户不可达」是**导航层成立**（路由/Tab/搜索/深链不暴露），不是「仓库里没有死屏」；死屏清理走 GOV-015/孤儿面族（wt729/wt762 共 ~3,958 行纯删，见 §U.4）。

**一句话用户可见行为**：五 Tab 不增；Calendar/Focus/ErrorBook 等长尾经 context CTA 到达并返回原 Goal；leaderboard/shop/photon 保持 HIDDEN。

### U-08 · Accessibility 全链升级

**交付（返工重验 + 续做清零）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主体+返工 | `3f8299eb`+`f6357fae`（wt365） | U-06 渲染面补 liveRegion（失败族/横幅/分阶等待：状态突变自动播报）；返工后 6/6 真跑全绿（断言手法按 Flutter 语义装配实证校准——debugSemantics 同源，防「改测试凑绿」）+ wt358 30/30 = **36/36** |
| 续做 | `01585b78`（wt674，FIX-359） | 58 处占位语义标签全清 + 21 处无名图标可点节点补名 + 标签质量守卫（防回潮） |

**残差**：① 「GJ01/GJ03/GJ08 辅助技术可完成」以 widget/semantics 层测试承载；真机 TalkBack/VoiceOver 走查未发生（无设备，同 U 线共性）；② WCAG AA 的 contrast 面由 U-02 rubric 承载（可计算口径 8/8），全量 WCAG 审计未做。

**一句话用户可见行为**：状态突变有 liveRegion 播报；图标按钮有名字；触达目标/动效尊重系统设置。

### U-09 · L5 三端一致性 Diff（本线最需要 V4 读清楚的一张卡）

**证据形态（卡面「三端真实对比」的实际承载，三层）**：
1. **headless 契约层（主干，可复跑）**：`60366592`（wt390）——mobile/lib 全量平台分支审计表（kIsWeb/条件导入/Platform 门控三分类逐文件判定）；2 处真修（responsive_utils 平台判定接缝 dart:io→defaultTargetPlatform，红测先行；B-04 naming 注册表补 macos 段）；`mobile/test/widget/u09_platform_render_contract_test.dart` **11 契约用例**（C1 状态管线三端渲染指纹逐字一致×11 相位、C2 URL/网端、C3 平台判定同源、C4 session 双后端等价、C5 keyboard 偏好非平台分支、C6 三端 viewport 零 overflow、C7 允许差异登记表机器可读）；canonical fixture 与 B-04 states.py 同源。
2. **盘点矩阵+机械统一（主干）**：`774a048b`+`c817e64e`（wt676）——跨表面一致性矩阵（typography/spacing 消费盘点表，本节 U-01 引用的数据源）+ home/insights/settings 三面 92 处圆角字面量指认既有 DS 令牌（33 文件）。
3. **真机 diff 层（未发生，诚实转出）**：45 张三端截图矩阵=**就绪的执行清单**（9 surfaces×3 平台×viewport，逐行采集入口+断言点+命名模板，`visual_baseline.py matrix` 命令可复跑）+ DIFF_REPORT 模板；wt390/wt676 两轮均明示无浏览器/模拟器权限不伪造，「真机段转 HUMAN_INBOX+主会话」——**中央 HUMAN_INBOX 未收编此交接**（→ V3-FIX-511）。

**卡面验收口径对照**：「核心状态三端无 A/B visual issue」=契约层成立（渲染指纹逐字一致）+真机层未验证；「生成 final screenshot matrix 与 diff report」=**模板与清单已生成，final 数据未产生**。允许差异登记表在 `v3/04_ux/MULTIPLATFORM.md`（5 类：转场/触觉音频/网端别名/token 存储后端/IME 视觉，逐条 reason）——「对允许差异写 reason 而非强行像素一致」验收以文档+机器可读 fixture 双承载兑现。

**一句话用户可见行为**：无直接新增行为；「android 目标在 macOS 宿主被判非移动端」类宿主相关判定缺陷已修；三端 canonical 状态语义由契约测试锁住。

### U-10 · 全产品文案与术语终审

**交付（主卡双证成立 + 增量终审）**

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| 主卡 | `d85e9a9a`（wt363） | 死键收割 42 键（零引用逐键 grep 实证，arb+gen 三件套外科纯删除 **+0/−738**；gen 手改同步——wt363 判例：gen-l10n 重生成含全量 formatter 翻搅，弃重生成） |
| 增量 | `633fdacd`+`d87ea8fd`（wt672） | 文案红线 2 键值去黑话 + 记忆详情 13 处硬编码英文标签清零（改真话不改行为，零业务逻辑）；REPORT 双证 wt363 首轮成立（死键账目 10029 活/49 冻结闭环） |
| 集成 | `fda4f975` | 187 轮四卡集成（含 U-10），三批 renumber |

**残差**：① EXACT 带 8 草稿键（chatConfidence×3/chatCompletion×5）+ l10n 49 冻结键仍在（H-005 等用户文案裁决）；② wt685 L10N 债与 en/zh 10061 键双向零缺失是后续守卫面（非 U-10 卡内）。

**一句话用户可见行为**：核心 journey 无 raw key/占位符；记忆详情不再出现硬编码英文标签；「0 memories/5 correctable claims/75%」类黑话主呈现已被 U-03 的理解视图替换。

---

## U.3 设计决定与取舍（从提交/审查考古）

1. **「续做不重做」双证判据**：每个续做会话先证前轮交付在主干祖先链+树内产物齐备，只补真实缺口（wt673/675/672/676 四连）。代价是每张卡的交付分散在 2-4 个 commit 波次，V4 读账必须逐波读；收益是 10/4 红线内零重做浪费。
2. **守卫冻结优于一次性迁移**：U-01 的真正产物是「只降不升」的 ratchet 基线+新文件零违例闸，而非把 22k 处 DS 引用一次性清完。存量撕裂面（chat 80 字面量、galaxy 零 typo 采用）以矩阵盘点显式留档，迁移裁决权留给视觉 owner（E1 冻结豁免）。
3. **低刺激的验证钉在渲染树而非设置页**：U-02/374/384 三轮把「reduceMotion 下不得出现零时长 AnimatedSize 壳」做成渲染树枚举断言+「禁动效不装壳」修法范式——reviewer（wt694）亲跑红绿复核并纠正普查归因，这是「独立审查抓出真缺陷」的正面样本。
4. **诚实化优于死键**：U-04/379②③ 的裁定——提示文案在唯一活面永不可渲染时，撤 docstring 许诺+留幂等不变量测试，而不是造新 l10n 死面。「不虚占键位」与 U-10 死键收割同律。
5. **允许差异显式登记**：U-09 把「平台差异是资产不是缺陷」写成机器可读 fixture（platformDivergences 逐条 point/platforms/reason）+文档双承载，C7 契约测试保证登记表非空且形合规——为 V4 的多端策略提供了现成的裁决框架。
6. **真机段不伪造**：全线以「headless 承载+转出清单就绪」收束真机验收；但转出登记链断裂（508），V4 若接手三端走查，执行清单都在（U-09 §5、B-04 harness、G-05 HUMAN_INBOX_G05_VISUAL.md），缺的只是统一入口登记与采集执行。

---

## U.4 残差与 V4 注意点（汇总）

1. **GOV-015/WS6 两大删除后的 UI 面健康度（专项结论）**：wt729（FIX-440，data_usage_dashboard 655 行纯删）+ wt762（FIX-489 WS6 透明画像孤儿屏 2636 行纯删 + FIX-490 learning-mode 667 行纯删，共 ~3,958 行 0 增）删除的全部是**从未接线的孤儿面**——WS6 的 wire-or-purge 裁决证据链亲证「路由两代仓库从未注册、stage7 只翻 flag 未触 routes；设计意图已由已接线 UserPersonaScreen /profile/persona 承担（读/纠正/回滚/偏好更新四面齐备）」。删除后：analyze E0、full_route_coverage 116 路由全绿、a11y 守卫 allowlist 同步摘行（防僵尸豁免）、独占 l10n 键逐键亲证零外部消费者后删除、i18n 100%。**UI 面健康度未受伤害，反而消除了「不可达承诺面」**；重做路径原子留档在 commit message（git 恢复+注册路由+补入口三步）。V4 教训：删面前先证「设计意图是否已由他面承担」，且删除必须是屏+provider+flags+tests+l10n 全链原子。
2. **U-06 闸门覆盖是 8 个 seam 不是全部核心屏**：chat（自有 ws 状态机）与 galaxy（视觉锤）的整面接入是 V4 的显式决策点，不是「已完成只需要维护」。
3. **令牌存量迁移无主**：chat 80 处 fontSize 字面量+galaxy 零 context.typo（E1 豁免）在 FIX-377 首批后无承接计划；台账 377 行缺失（507）使这个尾更不可见。
4. **真机面欠账集中**：U-06 simulator、U-08 三端辅助技术、U-09 45 张矩阵、U-02/05 的 5 秒测试 rubric——全部只有 headless 承载。执行清单与 harness 齐备，V4 初期应安排一次集中采集批次（成本主要在设备/浏览器权限而非代码）。
5. **FIX-375 OPEN**（FirstActionCard 无标题层，journey 面 rubric FAIL 保持必红放行）与 FIX-379②③ OPEN——两个 U 线挂账都是「需要产品/视觉裁决」而非机械修。
6. **验收语义的口径差异要带进 V4**：「≥95% covered」=注册面覆盖率 1.0；「A/B issue=0」=golden android 批口径+macOS ENV-1 豁免；「三端一致」=契约指纹一致。V4 验收设计应显式写清口径，避免把 headless 口径误读为真机结论。

---

## U.5 本次审查登记

- **V3-FIX-510**（本次新登记，台账行已入本 worktree commit）：台账 V3-FIX-377 行缺失——370-376/378/379 在册而 377 跳号零行；修复本体在主干（分支 commit 3d00aec9，集成 3ec111c4「V3-FIX-377 chat 令牌双态撕裂机械收口首批」，WT686 REPORT §「→ FIXED@3d00aec9」、wt694 review 引用一致）。与 504 同向的台账低估漂移；且行缺失使「首批」后的令牌迁移尾（本次复测 chat 仍有 80 处 fontSize 字面量）失去依附面。
- **V3-FIX-511**（本次新登记）：真机段交接承诺未入中央 HUMAN_INBOX——U-09 45 张三端截图矩阵、G-05 真机截图/FPS 批（自带 v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md）、U-08 三端辅助技术走查、B-04 L2-L5 走查等「转 HUMAN_INBOX」承诺均早于中央收件箱创建（09-27 wt695），从未回填；现行 H-001~008 无一覆盖。V4 从中央收件箱出发会系统性漏看这批未完成面。
- 复核过但**不构成新发现**的两项：chat/galaxy 未接状态闸（wt358/wt673 两轮如实登记，属已知设计态）；demo 首屏孪生 provider 面（wt694 抓出且 wt696 已补完收口 bd576cd7）。
- 号占用核验：500-504 已占用（wt765/wt770/wt769）；505 grep 全仓零命中但仍空置——按派单纪律自 506 起用，本登记取 507/508（506 预留给并行的 wt775 S/G 章内先发现项，见 S-line.md §S.5）。
