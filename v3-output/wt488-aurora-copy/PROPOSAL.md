# wt488 · Aurora/galaxy 黑话重设计提案（纯分析+派卡，零产品码改动）

- 工号：wt488（对应组员主张⑦；上游核验 = wt479 §5-A「重灾区不在 Aurora 交互文案，在 galaxy/visual_elements 隐喻体系 + Aurora 名字从未被介绍」）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt488-aurora`（分支 `wt488-aurora`）
- base SHA：`aa6a9667`（含 V3-FIX-182+183：visual-elements 后端发布闸 `ENABLE_VISUAL_ELEMENTS` 默认 False、移动端 0 入边——本提案的爆炸半径判断以此为前提）
- 裁定口径：`v3/01_product/PRODUCT_LANGUAGE.md` + `v3/04_ux/COPY_TONE.md` + 既有白话基线（`auroraConfidenceLabel="把握 {percent}%"`、`auroraActionDisagree="不太对"`）
- 方法：`app_zh.arb`/`app_en.arb` 全量 11,559 键（zh=en）JSON 解析 → 隐喻词表（星图/知识星/星域/星云/星轨/银河/宇宙/引力/辉光/轨道/光子/点亮/装备/皮肤/Aurora 等）命中 266 键 → 逐键 `grep -rE 'l10n\.<key>\b' lib test --include=*.dart`（剔除 `lib/l10n/` 生成物）计引用文件数 → 零引用键再以大小写不敏感子串复核（防动态拼键误判）→ 按「无上下文 3 秒内理解」判据逐条裁决

---

## 0. 结论 TL;DR

1. **最大的黑话不是词，是名字**：产品在聊天空态自我介绍为「AI 导师」（`chatWelcomeTitle`，app_zh.arb:2141，消费点 chat_screen.dart:2910），随后全应用 **56 个活键**（30 个 `aurora*` + 26 个非 aurora 键）自称 **"Aurora"**——这个名字在 onboarding 4 屏（interactive_onboarding_screen.dart 全文）与全部引导链中 **0 次介绍**。修法是 1 次命名引入（值级改动即可），**不是**重写 167 个 `aurora*` 键。
2. **galaxy 隐喻要分层**：「星图」作为产品级专名（onboarding 第 3 屏已介绍）**保留**；隐喻体系内部派生的二级黑话（**知识星/知识星点/银河核心/星域/轨道/力场参数**）才是 3 秒测试不过的重灾区，共 **25 个高危活键**，全部可 arb 值级外科替换。
3. **「光子」不列高危**：上下文充足（"价格 {price} 光子"）且兑换入口自带解释行（`photonRedeemProSubtitle`="学习所得的光子，随时可兑换成 Pro 时长"）。列 P2 产品决策（保留+首次可见处 gloss，或改名「学习积分」），不阻塞本提案。
4. **visual_elements 文案零成本方案 = 不做**：aa6a9667 已把该 feature 闸在后端 403 + 移动端 0 入边之后，95 键族当前用户不可见。文案修复随「是否发布该 feature」的裁决卡一并走，现在不花一张卡。
5. 顺手扫出 3 个真缺陷（EN 四译并存、onboarding 架构屏开发术语、62 个死键），连同命名缺口登记 **V3-FIX-198~201**（190-193 见台账在案，194-197 grep 确认本仓快照未占、按卡面口径为在途，故自 198 起）。

---

## 1. 黑话全量盘点

### 1.0 盘点统计

| 指标 | 数值 | 口径 |
|---|---|---|
| 扫描池 | 11,559 键 ×2（zh/en） | `mobile/lib/l10n/app_{zh,en}.arb`，非 `@` 键 |
| 隐喻词命中候选 | 266 键 | §方法词表，值级命中 |
| 活键（有 l10n 引用） | 204 键 | 174 非 aurora* + 30 aurora* |
| 零引用死键（候选内） | 62 键 | `l10n.<key>` 零命中 + 大小写不敏感复核 |
| "Aurora" 自称活键 | **56 键** | 30 `aurora*` + 26 非 aurora*（settings/chat/通知/任务/周报面） |
| **高危（3 秒测试不过，必须替换）** | **25 键** | 全部 galaxy 隐喻二级派生 + 1 个 Aurora 复合词，§1.2 |
| 半透明（改/留两可，给建议词） | 15 键 | §1.3 |
| 光子族活键（决策项） | 25 键 | §1.4 |
| visual_elements 闸后键族 | 95 键族 | §1.5，随闸处置 |
| EN 侧同概念译名 | 99 键涉星光概念：galaxy 变体 86 / star map 8 / constellation 5 | §1.6，随替换卡统一 |

裁决图例：❌ 必须替换 ｜ ⚠️ 半透明（建议替换或配 gloss）｜ ✅ 保留（3 秒可懂/已是白话基线/专名已引入）｜ 💀 死键（用户不可见，随收割卡删除，不耗替换文案）

### 1.1 保留项（先说不动什么，防执行卡扩散）

| 词/键 | 现值（arb 行号） | 判据 | 裁决 |
|---|---|---|---|
| `auroraConfidenceLabel` / `auroraActionConfirm` / `auroraActionDisagree` | 把握 {percent}% / 看起来对 / 不太对（9886 邻域，wt479 已核） | 已是刻意白话基线 | ✅ 保留，作为全产品措辞标尺 |
| `galaxy` / `exploreGalaxy` / `quickReplyExploreGalaxyLabel` / `taskDetailAcceptIntoGalaxy` / `reportOpenGalaxy` / `theaterTopBarViewGalaxy` 等以「星图/知识星图」为专名的用法 | 星图（:11）/ 探索星图（:81）/ 纳入星图（:4544）/ 打开知识星图（:7941） | onboarding 第 3 屏 `onboardingGalaxyTitle/Description`（:1821-1822）已介绍；「星图」为常用词 | ✅ 保留专名（规范见 §4-1）；EN 侧统一写法见 §1.6 |
| 「点亮」族：`galaxyNotLit`、`galaxyContribFirstLight`、`knowledgeMasteryLevelUnlit`、`achievementStatsWaitingToLight` 等 20+ 键 | 尚未点亮 / 首次点亮 / 未点亮 | 「点亮」是常用词而非域内黑话，温度合规（COPY_TONE 反对的是无意义鼓励，不是意象） | ✅ 保留 |
| `galaxySectorCosmos` / `studyMaterialsSubjectCosmos` | 宇宙（:3974/:3754） | 这是**学科名**（天文/宇宙），不是隐喻黑话 | ✅ 保留（盘点词表假阳性，如实排除） |
| `galaxyA11yCanvasSummary` | 知识星图：{nodeCount} 个知识点，覆盖 {domainCount} 个领域（:3883） | 无障碍摘要已是「知识点/领域」白话 | ✅ 保留（可作 galaxy 族替换的目标语汇范本） |
| `galaxyErrorHuman*` 三键 | 星图出了点小状况…你的数据没有丢，稍后再试一次（:3940 邻域） | 事实陈述+数据安全+下一步，白话范本 | ✅ 保留（失败文案替换以它为模板） |
| `sensoryHapticSubtitle` / `guestConversionCardBody` | 成就、星图等触感反馈（:50）/ 星图进度（:2099） | 专名正常用法 | ✅ 保留 |
| `userAurora` | Aurora | 助手显示名键（1 处引用）——名字本身不是黑话，缺的是引入（→V3-FIX-198） | ✅ 保留键，配合 §2 引入方案 |

### 1.2 高危清单（25 键，❌ 必须替换；中英双语建议词已给，可直接抄进执行卡）

**A. 知识星族（12 键）——把知识拟物成"星星"再让它们"飞"，3 秒测试全灭**

| # | 键（zh 行号，引用文件数） | 现值 zh / en | 判 | 建议 zh / en |
|---|---|---|---|---|
| 1 | `galaxyDraftReviewPromptTitle`（:8252 邻域，2f） | 我们从 {documentName} 里找到了 {count} 颗知识星，要现在看看吗？/ We found {count} knowledge stars in your {documentName}! Review them? | ❌ | 我们在《{documentName}》里找到了 {count} 个知识点，要现在看看吗？/ We found {count} knowledge points in {documentName}. Review them now? |
| 2 | `galaxyDraftReviewPromptBody`（2f） | 你的星图该由你亲手确认。你可以逐个通过、跳过、合并，或者先改名再收下。/ You decide what belongs in your galaxy… | ⚠️前半句诗化，动词白话 | 你的星图由你确认：逐个通过、跳过、合并，或先改名再收下。/ Your map, your call. Approve, skip, merge, or rename each one. |
| 3 | `galaxyDraftReviewScreenTitle`（1f） | 审核知识星 / Review knowledge stars | ❌ | 审核知识点 / Review knowledge points |
| 4 | `galaxyDraftReviewEmptyTitle`（1f） | 现在没有待确认的知识星 / No pending stars right now | ❌ | 现在没有待确认的知识点 / Nothing waiting for review |
| 5 | `galaxyDraftReviewEmptyBody`（:8300，1f） | 等文档处理完成后，新的知识草稿会先落到这里，等你点头再进入星图。/ …draft knowledge stars will land here… | ⚠️「落到/点头」可留 | 文档处理完成后，新的知识草稿会先到这里，你确认后才会进入星图。/ When processing finishes, drafts land here for your approval before joining your map. |
| 6 | `galaxyDraftCompletionTitle`（1f） | 已确认 {accepted} / {total} 颗知识星 / {accepted} of {total} knowledge stars added | ❌ | 已确认 {accepted} / {total} 个知识点 / Added {accepted} of {total} knowledge points |
| 7 | `galaxyDraftCompletionSummary`（:8322，1f） | {accepted} / {total} 颗知识星已加入你的星图！/ …knowledge stars added to your galaxy! | ❌ | 已把 {accepted} / {total} 个知识点加入你的星图 / Added {accepted} of {total} knowledge points to your map |
| 8 | `galaxyDraftCompletionReady`（:8277，1f） | 准备把它们送进你的星图 / Ready to send them into your galaxy | ⚠️「送进」轻拟人 | 准备加入你的星图 / Ready to add to your map |
| 9 | `galaxyDraftCompletionBody`（:8313，1f） | {documentName} 里的这些知识星，已经准备好飞进你的星图。/ The stars you kept from {documentName} are ready to fly into your map. | ❌ | 《{documentName}》里的这些知识点已整理好，确认后就会进入你的星图。/ These knowledge points from {documentName} are ready — confirm to add them to your map. |
| 10 | `galaxyDraftEditTitle`（1f） | 调整这颗知识星 / Tune this knowledge star | ❌ | 编辑这个知识点 / Edit this knowledge point |
| 11 | `studyMaterialsAttachedNodesTitle`（1f） | 挂载的知识星点 / Attached knowledge stars | ❌「星点」生造 | 关联的知识点 / Linked knowledge points |
| 12 | `studyMaterialsKnowledgeStarsLabel`（1f） | 知识星点 / Knowledge stars | ❌ | 知识点 / Knowledge points |

**B. 上传/落图过程族（3 键）——"飞向/轨道/滑出去"：失败文案违反「失败诚实+具体」**

| # | 键（zh 行号，引用文件数） | 现值 zh / en | 判 | 建议 zh / en |
|---|---|---|---|---|
| 13 | `galaxyUploadTargetGalaxyCore`（:8365，1f） | 银河核心 / Galaxy core | ❌（上传目标选择器：全图 vs 选区） | 整个星图 / Entire map |
| 14 | `galaxyUploadTargetSelectedConstellation`（:8366，1f） | 这片星域 / this constellation | ❌（「星域」改用 app 既有词「领域」，见 `galaxyA11yCanvasSummary`） | 所选领域 / Selected domain |
| 15 | `galaxyUploadAlreadyInProgress`（:8367，1f） | 已经有一份学习资料正在飞向你的星图。/ A study material is already joining your constellation. | ❌ | 已经有一份资料在处理中，完成后会进入你的星图。/ A document is already being added to your map. |
| 16 | `galaxyUploadStatusQueued`（:8369，1f） | 上传完成，正在进入轨道... / Upload complete. Holding orbit... | ❌ | 上传完成，正在整理… / Uploaded — organizing… |
| 17 | `galaxyUploadFailedBody`（:8391，1f） | 文档在落入星图前滑了出去，准备好时再试一次就好。/ The document slipped out of the constellation… | ❌（失败原因不可知，诗意掩盖事实） | 这份资料没能进你的星图，你的数据没有丢，稍后再试一次。/ The document didn't make it to your map. Your data is safe — try again in a moment.（模板=`galaxyErrorHuman*`） |

**C. 星图视图设置族（3 键）——物理仿真参数直出**

| # | 键（zh 行号，引用文件数） | 现值 zh / en | 判 | 建议 zh / en |
|---|---|---|---|---|
| 18 | `galaxySimCenterGravity`（:3979 邻域，1f） | 中心吸引力 / Center Gravity | ❌（图布局参数） | 节点聚拢力度 / Node pull |
| 19 | `galaxySimLinkTension`（:11960 邻域，1f） | 连线牵引力 / Link Tension | ❌ | 连线松紧 / Line tension |
| 20 | `galaxySimSettingsDesc`（1f） | 调节显示密度、力场参数与回放节奏… / …force field parameters… | ❌「力场参数」 | 调节显示密度、节点间距和回放速度，让星图浏览更顺手。/ Adjust density, node spacing, and replay speed. |

**D. Onboarding 特性页（3 键，新用户第一屏级暴露面）**

| # | 键（zh 行号，引用文件数） | 现值 zh / en | 判 | 建议 zh / en |
|---|---|---|---|---|
| 21 | `onboardingGalaxyFeature1`（:1823，1f） | 6大知识星域：理性、造物、灵感、文明、生活、精神 / Six learning realms… | ❌「知识星域」 | 6 大学习领域：理性、造物、灵感、文明、生活、精神 / Six learning domains: … |
| 22 | `onboardingGalaxyFeature2`（:1824，1f） | 实时衰减预测：了解知识遗忘曲线 / Real-time decay prediction… | ❌「衰减预测」诊断腔 | 看到什么快忘了：需要复习的知识会变暗提醒你 / Knowledge you're likely to forget dims so you know when to review |
| 23 | `onboardingGalaxyFeature3`（1f） | 交互式时间机器：预测未来学习状态 / Interactive time machine… | ❌「时间机器」 | 回看学习轨迹：知识如何随时间生长 / Look back at how your knowledge grew over time |
| 24 | `onboardingGalaxyFeature4`（1f） | 智能推荐：基于知识图谱的学习路径 / …based on the knowledge graph… | ❌「知识图谱」内部术语 | 下一步学什么：根据你的星图给出建议 / What to learn next, suggested from your map |

**E. Aurora 复合黑话（1 键）**

| # | 键（zh 行号，引用文件数） | 现值 zh / en | 判 | 建议 zh / en |
|---|---|---|---|---|
| 25 | `sensoryAuroraLinkTitle`（:51，1f） | Aurora 感官联动 / Aurora Sensory Link | ❌「感官联动」 | 让 Aurora 调节音乐与触感 / Let Aurora adjust sound and haptics（subtitle `sensoryAuroraLinkSubtitle` 本身已是白话，✅ 不动） |

### 1.3 半透明项（⚠️ 15 键，给建议词，执行卡可裁）

| 键 | 现值 | 判 | 建议 |
|---|---|---|---|
| `communityGroupGalaxy` / `communityAddToGroupGalaxy` / `communityGalaxyIndexHint` | 群星图 / 加入群星图 / 群组知识星图索引 | 「群星图」可误读为「群星·图」 | 小组星图 / 加入小组星图 / 让这份资料也出现在小组星图索引里；en 统一 Group map |
| `chatAgentNavigator` / `chatRoundtableGalaxyNavigator` / `intentAgentGalaxyGuide` / `chatExpertGalaxyGuide` | 星图导航 / 星图向导 | 半透明，专名+功能词可懂 | 可保留；若随 agent 改名一并动，统一「星图助手」 |
| `achievementEquipAction` / `achievementEquipped` / `achievementUnlockToEquip` / `profileNoTitleEquipped` / `userTitleUnequippedOption` / `visualBundleEquipped` / `visualPrestigeEmpty` / `visualEquipFailed` | 装备 / 已装备 / 解锁后可装备 / 未装备称号 / … | 游戏化借词，称号/套装语境可懂但生硬 | 称号语境→「佩戴/未佩戴」；套装语境→「使用/已使用」。⚠️ 与闸后面 visualElementEquip 族（§1.5）用词需一次性统一，防两套词 |
| `achievementRewardSkin` | 星系皮肤 | 「星系」与「星图」混指同一概念（同 `achievementCardGalaxySkin`=星图皮肤） | 统一「星图皮肤」 |
| `taskDiagnosisMessage` | Aurora 已根据当前任务状态给出诊断。 | 「诊断」临床腔（COPY_TONE 禁诊断式语言） | Aurora 看了一下这个任务的情况。/ Aurora looked at where this task stands. |
| `taskExecutionAuroraDiagnosticUnavailable` | Aurora 诊断暂时不可用：{error} | ⚠️ `{error}` 原始串透传给用户（是否人话取决于上游），替换「诊断」时顺带评估 `{error}` 消毒（另案，本卡不动参数） | Aurora 暂时看不了这个任务：{error} |
| `onboardingWelcomeSubtitle` | 你的 AI 学习助手\n让知识点亮智慧之光 | 「点亮智慧之光」空诗句 | 你的 AI 学习助手\n先从一个今天能完成的小目标开始（或随 §2 命名方案一并改写） |

### 1.4 光子族（25 活键，P2 产品决策，不列高危）

- 现状：`photonRedeemPro*` 12 键（profile+独立屏，D-COMM-2 裁定的活面）、`pt*` 转账 5 键、`contract*` 押金 2 键、`shop*` 3 键（V3-FIX-05：目录空但入口在场 streak_details_screen.dart:427）、`streakShopSubtitle`、成就奖励 2 键。
- 判据：「价格 {price} 光子」3 秒可懂（语境自释货币）；`photonRedeemProSubtitle` 已是合格 gloss。
- **方案 A（推荐）**：保留「光子」专名，在两处首次可见点补一句 gloss——`shopTitle` 副标题或 `streakShopSubtitle` 改「光子是学习赚到的积分，可在商城使用」；成就奖励首见处已带 +N 光子，无需动。零结构改动。
- **方案 B（产品拍板才做）**：显示层全改「学习积分 / Points」，25 键 zh+en 值级替换；不动 `/photon` 路由、后端 ledger 与 D-COMM-2 语义（键名是内部符号，不在黑话范围）。风险：与 T36 release-scope 卡（V3-FIX-190/191）同期动同一批面，需排队。

### 1.5 visual_elements 闸后键族（95 键族：`visualElement*`/`visual*`/`photon` 商城 hint）——本提案不动

aa6a9667 已证：`ENABLE_VISUAL_ELEMENTS` 默认 False → 8 条路由全组 403；移动端 U-07 摘除后 0 入边、0 push 引用 ⇒ **该族当前对用户不可见，文案替换无用户价值**。族内高危词（装备/卸下/稀有度/皮肤/辉光/紫色星云/征服引力/静星轨迹）**登记为「随闸裁决卡」的附带清单**：若产品裁决发布该 feature，文案卡必须同步执行（装备→使用/佩戴、稀有度→等级、辉光→光效）；若裁决删除（wt479 §5-B B-1 圈层），文案随葬零成本。⚠️ 唯二例外已外溢到活面：`motionIntensityUltraDesc/MediumDesc` 的「辉光」（:4809/:4811，设置页活键）→「光效」，随 §3 卡-2 顺带；「装备」活面 8 键见 §1.3。

### 1.6 EN 侧译名不一致（99 键，随替换卡统一，不单独立卡）

同一「星图」概念 EN 现存 **galaxy 变体 86 键 / star map 8 键 / constellation 5 键**（含 `goalGraphToggleStarMap="Star Map"` vs `galaxy="Galaxy"` vs `galaxyUploadTargetSelectedConstellation="this constellation"`）。zh 侧同类：星图/星系/星域三词混指（§1.3 achievementRewardSkin 行）。统一规则写进 §4-2，执行卡照做即可。

### 1.7 死键（62 键，💀 不耗替换文案，登记 V3-FIX-200 随收割卡删除）

判定：`grep -rE 'l10n\.<key>\b' lib test`（剔除生成物）零命中 **且** 大小写不敏感子串复核零命中。清单（family 供收割卡分组）：

- aurora 旧状态带 31：`auroraStatusReady/Partial/Missing/Recalibrating`、`auroraBandCalibrated/CoolingDown/NeedsConfirm/RiskFound/Sensing`、`auroraObserving`、`auroraBackground`、`auroraStrategyRisk`、`chatAuroraRecalibratePrompt`、`chatMemoryAuroraUsedCount`、`chatMemoryReferenceReceiptLabel`、`chatReceiptAuroraAdjustedExperience/AuroraChangedNext/ExperienceChange`、`dashboardCommandCenterAskAurora`、`homeAskAurora`、`stuckHelpAuroraSteps`、`receiptCorrectionRecorded`、`dashboardCcNoUrgentAction`、`homeNoUrgentAction` 等
- galaxy 旧面 9：`knowledgeGalaxy`、`galaxyEmptyMessage`、`galaxyNodeNotExist`、`galaxyPreviewReLight`、`galaxySectorDarkMatter`（wt479 点名的暗物质——已是死键）、`galaxySimulationCenterGravity/Gravity`、`goalDetailOpenGalaxy`、`memGoGalaxy`、`homeOnboardingExploreGalaxy`
- 成就 demo/奖励 10：`achievementDemoExplore50/100/500Name`、`achievementDemoNodes100Name`、`achievementDemoSkinNebula*`、`achievementDemoTitleEarlyExplorer`、`achievementMilestoneBadgeGalaxy/HeadlineNodes/SubheadlineNodes`、`achievementUnlockPhotonReward10/25/50/100`
- visual 旧主题 10：`visualStarTrack`（wt479 点名的静星轨迹——死键）、`visualGravity`、`visualAuroraDesc/Shard`、`visualNebulaDesc`、`visualNightAurora/SilentNightAurora/SilentAuroraDesc`、`visualScholarDesc`、`visualGalaxyConquerorDesc`、`visualSlotStarMapEffect/Page`
- 杂项 2：`auto_photonbalance`、`taskDetailNodeExpansionDescription`

（wt479 §5-A 表引用的 4 个代表键 `auroraStatusReady`/`galaxySectorDarkMatter`/`visualStarTrack`/`galaxySimulationCenterGravity` 经复核**均为零引用死键**——重灾区比 wt479 报告的更小，活的 galaxy 高危集中在 §1.2 的 25 键。）

---

## 2. Onboarding 缺口方案（V3-FIX-198 修法）

**缺口事实链**（grep 证毕）：onboarding 4 屏 = 欢迎（`onboardingWelcomeTitle/Subtitle`）→ 系统架构（`onboardingArchitecture*`，另登记 V3-FIX-199）→ 星图（`onboardingGalaxy*`）→ AI 怎么帮你（`onboardingAiHelpTitle`+chat/tasks 特性行）；4 屏 + `features/onboarding/` 全目录 + chat 空态，**0 处出现"Aurora"**。而聊天空态自称「AI 导师」（`chatWelcomeTitle`，app_zh.arb:2141 / chat_screen.dart:2910 消费），首条状态芯片却是「Aurora · 轻量感知中」（`auroraSensing`）——用户被介绍了"AI 导师"，然后满屏遇见从未介绍的名字。

**屏 1（首进 chat；最小实现 = 改既有键值，零新键零新逻辑）**

- `chatWelcomeTitle`：zh「你好，我是 Aurora」 / en "Hi, I'm Aurora"
- `chatWelcomeSubtitle`：zh「你的学习伙伴。我会看着你的进展，有把握时提醒你，拿不准时先问你。」（29 字 ✓）/ en "I keep an eye on your learning — I'll speak up when I'm confident, and ask when I'm not."
- 触发时机：chat 空态（现键就在此渲染，天然一次性）；无需新触发逻辑。

**屏 2（首次 galaxy 可见；一次性 coach mark，覆盖跳过 onboarding/guest 直进路径）**

- 新键建议 `galaxyFirstVisitHint`：zh「这是你的星图：一个亮点是一个知识点，学得越勤它越亮。」（25 字 ✓）/ en "This is your map — each light is a knowledge point. The more you practice, the brighter it gets."
- 触发时机：`/galaxy` 首次可达后首帧底部浮层，SharedPreferences 一次性标记（`interactive_onboarding_screen.dart:17` `_kOnboardingPageKey` 同法先例）；onboarding 完整走完的用户在第 3 屏已获同义介绍，coach mark 照常显示一次不冲突。

**可选增强（同卡可选项，不做不阻塞）**：onboarding 第 4 屏（AI 怎么帮你）加一行 `onboardingAiHelpTitle` 下副标——「对话里的这位叫 Aurora——之后你会经常见到这个名字。」（26 字 ✓），把命名前移到 onboarding 内，chat 空态方案不变。

**红线**：不加新屏、不改 onboarding 页数与路由（`_totalPages` 硬编码）；60 字/屏上限按 zh 计，en 允许等效长度。

---

## 3. 替换爆炸半径与派卡排序

引用计数口径：`grep -rE 'l10n\.<key>\b' mobile/{lib,test} --include=*.dart`，剔除生成物，计**引用文件数**（每键 1-2 个文件，全部 ≤2；全族无一处 >2，因文案消费点单一屏/组件化良好）。键数统计含 zh+en 双 arb 与生成物 `app_localizations{,_zh,_en}.dart` 的机械同步（执行卡用 `mobile/lib/l10n/i18n_batch_replace.py` 既有工具+wt363 外科手法，`flutter gen-l10n` 仅作契约互证、产物弃用防全量重排噪声——wt363 判例）。

| 排序 | 卡 | 内容 | 键数（对） | 代码引用点 | 风险 | 依赖/耦合 |
|---|---|---|---|---|---|---|
| 1 | **copy-aurora-intro**（V3-FIX-198 主修） | §2 屏 1：`chatWelcomeTitle/Subtitle` 值级改写；可选 onboarding P4 副标新键 | 2（+1 可选） | chat_screen.dart:2910 一处（键不动则零代码改动） | **最低**：值级、活面单一、无逻辑 | 无 |
| 2 | **copy-galaxy-metaphor**（§1.2 A-D 24 键 + §1.3 活面 ⚠️ 项 + §1.6 EN 统一 + `motionIntensity*` 辉光 2 键） | arb 值级外科替换，zh+en 同步 | ~34 | 全部 ≤2 文件/键，约 40 个消费点，全为 Text 渲染无逻辑分支 | 低：无参数结构变化；`{documentName}` 等占位符原样保留 | 与死键收割同 arb 文件，**分卡分 commit**；避让 T36 release-flag 移动端卡（V3-FIX-191 同文件 routes 面不同区） |
| 3 | **copy-dead-key-harvest**（V3-FIX-200） | §1.7 62 死键删除（wt363 U-10 手法：arb×2+gen×3 外科删+零引用逐键复核） | 62 | 0（已证） | 低（纯删除，gen-l10n 契约互证） | 在卡 2 之后做，防行号漂移干扰审查 |
| 4 | **copy-aurora-gloss-settings**（§1.2-E + §1.3 尾 3 行 + 屏 2 coach mark） | `sensoryAuroraLinkTitle` 替换 + `galaxyFirstVisitHint` 新键 + 触发逻辑（新代码唯一处）+ `taskDiagnosis*` 措辞 | 3 改 1 新 | coach mark 触发 1 处（galaxy 首帧） | 中低：唯一含新逻辑的卡 | 无 |
| 5 | **copy-photon-gloss（决策项）**（§1.4） | 方案 A gloss 1-2 键；方案 B 25 键全改（产品拍板后另立细则） | 1-2（A）/25（B） | A：2 处副标题位；B：同 A 口径 | A 低 / B 中（与 D-COMM-2 措辞锚定冲突需拍板） | 排 T36 release-scope 卡之后 |

**不做**：visual_elements 95 键族（§1.5，随闸裁决卡）；`auroraFacet*` 状态词（wt479 已判「配一句副标题即可」，若后续派卡随 copy-aurora-gloss-settings 顺带，不单独立卡）；「把握 92%」基线族（保留标尺）；特效/动效删留（wt479 §5-B 另案，本提案零触碰）。

---

## 4. 措辞规范（与白话基线对齐，评审执行卡照此验收）

1. **名字先引入，后使用**：任何助手/功能专有名（Aurora、星图、光子）首次出现在用户面前时，必须已有一句"它是什么"的介绍（chat 空态自介 / onboarding 屏 / 入口副标题 gloss 三种形态）；介绍前不得进入按钮、状态芯片、通知文案。判例：V3-FIX-198。
2. **隐喻只留一层**：允许一个产品级隐喻专名（星图）；隐喻内部禁止派生二级黑话（知识星/星点/星域/银河核心/轨道/力场），二级概念一律用产品既有白话词（知识点/领域/整个星图/正在整理）——目标语汇范本 = `galaxyA11yCanvasSummary`。
3. **3 秒测试为验收判据**：替换后每条文案以「无上下文首见 3 秒内能说出这是什么/要做什么」自检；过不了的进替换表，过的（点亮/宇宙学科名/星图专名）不动，防执行卡扩散。
4. **只改显示层，不动符号**：替换仅限 arb 值（zh+en 同步+占位符原样），不改键名、路由、后端字段与生成物手改禁区（AGENTS 硬规则 1/2）；键名是内部符号，不属于黑话治理对象。
5. **失败/不确定文案以事实+数据安全+下一步为模板**：模板 = `galaxyErrorHuman*` 三键与「把握 {percent}%」；禁止诗意掩盖（"滑了出去"）、诊断腔（"给出诊断"）、空诺（"即将上线"）——延续 wt363 终审口径。
6. **一词一译**：同一概念全产品一个词（zh：星图≠星系≠星域；en：Galaxy 全称 Knowledge Galaxy，禁 Star Map/constellation 混用），新文案入 arb 前按本条自查（V3-FIX-201）。

---

## 5. 缺陷登记（V3-FIX-198~201，已同步 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`，一个 docs commit 双文件）

| ID | Sev | 缺陷 | 证据（grep/行号） | 修法卡 |
|---|---|---|---|---|
| V3-FIX-198 | P2 | "Aurora" 名未引入即自称：chat 空态自介「AI 导师」，全应用 56 活键自称 Aurora，onboarding/引导链 0 介绍 | app_zh.arb:2141 `chatWelcomeTitle`；chat_screen.dart:2910；interactive_onboarding_screen.dart 全文 0 命中；56 键清单见本提案 §1.0 | copy-aurora-intro（§3 卡 1） |
| V3-FIX-199 | P3 | onboarding 系统架构屏以开发栈术语直出新用户（Flutter/Go Gateway/Python Agent Engine/WebSocket/PostgreSQL+pgvector 五步动画） | `onboardingArchitectureStep1-5Desc`（app_zh.arb onboardingArchitecture 区段）+ ArchitectureAnimation；违反 PRODUCT_LANGUAGE 原则 1 | 独立小卡：改用户能力视角一句话或裁删该屏 |
| V3-FIX-200 | P3 | 隐喻/皮肤族 62 个零引用死键滞留 arb（含 wt479 点名的暗物质/静星轨迹/中心引力——均死键） | 判定与清单见 §1.7；gen 全量重排噪声源 | copy-dead-key-harvest（§3 卡 3） |
| V3-FIX-201 | P3 | 星图概念译名分裂：EN galaxy 86/star map 8/constellation 5 三译并存，zh 星图/星系/星域混指 | §1.6 计数脚本口径；样例 `goalGraphToggleStarMap` vs `galaxy` vs `galaxyUploadTargetSelectedConstellation` | 随 copy-galaxy-metaphor 统一（§3 卡 2），不单独立卡 |

---

## 6. 执行卡清单（每张可直接派卡）

- [ ] **copy-aurora-intro**：`chatWelcomeTitle/Subtitle` 值级改写（§2 屏 1 文案现成）＋可选 P4 副标。验收：首装→chat 空态 3 秒内能答出"助手叫什么/它做什么"；zh≤60 字。
- [ ] **copy-galaxy-metaphor**：§1.2 24 键 + §1.3 活面 ⚠️ 项 + §1.6 EN 统一 + `motionIntensity*` 2 键，arb 值级替换，zh+en 同 commit，占位符零变化。验收：`grep` 全表键无旧词残留（知识星/星域/银河核心/轨道/力场/星系）；`flutter analyze` 过；受影响屏 golden/组件测试零回退。
- [ ] **copy-dead-key-harvest**：§1.7 62 键删除（wt363 手法）。验收：逐键零引用复核记录 + gen-l10n 契约互证 + diff 纯删除。
- [ ] **copy-aurora-gloss-settings**：`sensoryAuroraLinkTitle` + `galaxyFirstVisitHint` coach mark + `taskDiagnosis*`。验收：galaxy 首进一次性提示可关闭、重启不复现。
- [ ] **copy-photon-gloss（决策项）**：产品拍板 A/B 后执行，排在 T36 release-scope 卡之后。

---

*盘点产物中间数据：/tmp/wt488_inventory.json、/tmp/wt488_counts_precise.json（本机临时文件，不入库——AGENTS 硬规则 5）。本提案零产品码改动、零测试环境需求；所有行号以 base `aa6a9667` 为准。*
