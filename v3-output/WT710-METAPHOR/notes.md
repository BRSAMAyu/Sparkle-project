# WT710-METAPHOR · V3-FIX-403 处置实录（copy-galaxy-metaphor zh 主体 19 键白话化收口）

- 工号：wt710（2026-09-27，任务来源=台账 V3-FIX-403 行，wt706 登记的卡2 zh 主体重开）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt710-metaphor`（分支 `agent/node-b/wt710/metaphor`）
- base SHA：`f48451b3`（main，含 wt706 登记的 403 行）；代码 commit：`bf8b3742`
- 触达面：`mobile/lib/l10n/app_zh.arb` + `app_en.arb` + `app_localizations{,_zh,_en}.dart`（89 行改 89 行）+ `mobile/test/features/galaxy/widget/galaxy_draft_review_screen_test.dart`（1 钉值 + 2 提法）+ 台账 + 本 notes

## 1. 结论 TL;DR

1. 403 的 19 键（❌16 + ⚠️3）全部按 wt488 PROPOSAL §1.2 建议词值级替换落地；⚠️ 三键执行卡裁**替换**（§1.2 原判各有具体建议词，照抄）。
2. zh∪en 并集口径：en 侧只动 16/19——galaxyUploadTargetGalaxyCore（en="Entire map"）、galaxyDraftReviewPromptBody（en 已是白话动词句）、galaxyUploadAlreadyInProgress（en 已是 "joining your map"）三键 en 原值非黑话不动。
3. 键名/键数/占位符（{documentName}/{count}/{accepted}/{total}）零改动；arb×2+gen×3 恰 89 行改动，L10N-REGEN-PARITY（10087 键）作契约互证。
4. 49 冻结键（V3-FIX-182 拍板挂起：aurora*19+visual*30 死键，清单见 W565_L10N_CLOSEOUT §3.4）与 19 键**零重叠零触碰**（前缀即可判定，19 键全为 galaxy*/studyMaterials* 活键）。
5. 连带新发现：范围外残留真黑话 2 键（studyMaterialsHeroSubtitle「知识星点」、galaxyUploadHeadingTo「正飞向 {target}」），新登 **V3-FIX-411**，本卡不扩面不触碰。

## 2. 19 键逐键 before/after（zh / en）

消费面=改前 `l10n.<key>` 词边界 grep（`mobile/lib`+`mobile/test` 剔 `lib/l10n/` 生成物；POSIX `[[:>:]]` 口径）实录，全为 Text/label 渲染无逻辑分支；改后键名未动故消费面零变化。

### A. 知识星族（12 键）

| # | 键 | 消费面（改前 grep 实录） | zh before → after | en before → after |
|---|---|---|---|---|
| 1 | galaxyDraftReviewPromptTitle | galaxy_draft_review_screen.dart:119; galaxy_screen.dart:4083 | 我们从 {documentName} 里找到了 {count} 颗知识星，要现在看看吗？ → 我们在《{documentName}》里找到了 {count} 个知识点，要现在看看吗？ | We found {count} knowledge stars in your {documentName}! Review them? → We found {count} knowledge points in {documentName}. Review them now? |
| 2 | galaxyDraftReviewScreenTitle | galaxy_draft_review_screen.dart:80 | 审核知识星 → 审核知识点 | Review knowledge stars → Review knowledge points |
| 3 | galaxyDraftReviewEmptyTitle | galaxy_draft_review_screen.dart:92,101 | 现在没有待确认的知识星 → 现在没有待确认的知识点 | No pending stars right now → Nothing waiting for review |
| 4 | galaxyDraftCompletionTitle | galaxy_draft_review_screen.dart:318 | 已确认 {accepted} / {total} 颗知识星 → 已确认 {accepted} / {total} 个知识点 | {accepted} of {total} knowledge stars added → Added {accepted} of {total} knowledge points |
| 5 | galaxyDraftCompletionSummary | galaxy_screen.dart:3316 | {accepted} / {total} 颗知识星已加入你的星图！ → 已把 {accepted} / {total} 个知识点加入你的星图 | {accepted} of {total} knowledge stars added to your map! → Added {accepted} of {total} knowledge points to your map |
| 6 | galaxyDraftCompletionBody | galaxy_draft_review_screen.dart:329 | {documentName} 里的这些知识星，已经准备好飞进你的星图。 → 《{documentName}》里的这些知识点已整理好，确认后就会进入你的星图。 | The stars you kept from {documentName} are ready to fly into your map. → These knowledge points from {documentName} are ready — confirm to add them to your map. |
| 7 | galaxyDraftEditTitle | galaxy_draft_review_screen.dart:396 | 调整这颗知识星 → 编辑这个知识点 | Tune this knowledge star → Edit this knowledge point |
| 8 | studyMaterialsAttachedNodesTitle | document_library_screen.dart:1164 | 挂载的知识星点 → 关联的知识点 | Attached knowledge stars → Linked knowledge points |
| 9 | studyMaterialsKnowledgeStarsLabel | document_library_screen.dart:1226 | 知识星点 → 知识点 | Knowledge stars → Knowledge points |
| 10 | ⚠️ galaxyDraftReviewPromptBody | galaxy_draft_review_screen.dart:132; galaxy_screen.dart:4095 | 你的星图该由你亲手确认。你可以逐个通过、跳过、合并，或者先改名再收下。 → 你的星图由你确认：逐个通过、跳过、合并，或先改名再收下。 | 不动（原值已白话：star map 为 §1.1 保留专名，动词句 plain） |
| 11 | ⚠️ galaxyDraftReviewEmptyBody | galaxy_draft_review_screen.dart:102 | 等文档处理完成后，新的知识草稿会先落到这里，等你点头再进入星图。 → 文档处理完成后，新的知识草稿会先到这里，你确认后才会进入星图。 | When document processing finishes, draft knowledge stars will land here for your approval. → When document processing finishes, drafts land here for your approval before joining your map. |
| 12 | ⚠️ galaxyDraftCompletionReady | galaxy_draft_review_screen.dart:143 | 准备把它们送进你的星图 → 准备加入你的星图 | Ready to send them into your map → Ready to add to your map |

### B. 上传/仿真/设置族（7 键）

| # | 键 | 消费面 | zh before → after | en before → after |
|---|---|---|---|---|
| 13 | galaxyUploadTargetGalaxyCore | galaxy_screen.dart:2060 | 银河核心 → 整个星图 | 不动（"Entire map" 原值已白话） |
| 14 | galaxyUploadStatusQueued | galaxy_document_upload_overlay.dart:154,362 | 上传完成，正在进入轨道... → 上传完成，正在整理... | Upload complete. Holding orbit... → Upload complete. Organizing... |
| 15 | galaxyUploadFailedBody | galaxy_document_upload_overlay.dart:301,384 | 文档在落入星图前滑了出去，准备好时再试一次就好。 → 这份资料没能进你的星图，你的数据没有丢，稍后再试一次。（模板=galaxyErrorHuman*「你的数据没有丢，稍后再试一次」，arb:15320-15325 实证） | The document slipped out of the star map before it could settle. Try again when you're ready. → This document didn't make it to your map. Your data is safe — try again in a moment. |
| 16 | galaxyUploadAlreadyInProgress | galaxy_screen.dart:2072,2097 | 已经有一份学习资料正在飞向你的星图。 → 已经有一份资料在处理中，完成后会进入你的星图。 | 不动（"already joining your map" 原值已白话） |
| 17 | galaxySimCenterGravity | galaxy_simulation_settings_sheet.dart:147 | 中心吸引力 → 节点聚拢力度 | Center Gravity → Node pull |
| 18 | galaxySimLinkTension | galaxy_simulation_settings_sheet.dart:165 | 连线牵引力 → 连线松紧 | Link Tension → Line tension |
| 19 | galaxySimSettingsDesc | galaxy_simulation_settings_sheet.dart:117 | 调节显示密度、力场参数与回放节奏，让星图浏览更顺手、更直观。 → 调节显示密度、节点间距和回放速度，让星图浏览更顺手。 | Adjust display density, force field parameters, and replay speed for a smoother star map browsing experience. → Adjust display density, node spacing, and replay speed for a smoother star map browsing experience. |

## 3. grep 归零证据与 gen 同步

- **改前实录**：19 键 `l10n.<key>[[:>:]]` 消费面逐键在档（§2 表第三列），全活。
- **改后归零**：19 键改后值 × 各自原黑话词表（知识星/知识星点/银河核心/轨道/滑了出去/飞向/中心吸引力/连线牵引力/力场参数/knowledge stars/pending stars/Center Gravity/Link Tension/force field/slipped out/fly into/送进/Holding orbit 等）逐键校验 **19/19 CLEAN**（arb 双侧值 + gen zh/en/doc 三文件同步态）。
- **gen 同步手法**：`flutter gen-l10n` 重生成实测产生全量重排噪声（app_localizations_en.dart 562 行、_zh 296 行、abstract 237 行——intl.selectLogic 块新格式化风格，与 19 键无关），按 wt363/380b31b1 判例**弃用重生成产物**（git checkout 回 HEAD 后）外科手改 gen×3（doc 19 行 + zh 19 值 + en 16 值，占位符 `$x` 无花括形与既有 emitter 规则一致，撇号 `\'` 转义对齐），`check_l10n_regen_parity.py` 以 10087 键全量过作逐字节语义互证。
- **范围外残留（如实记录，不属本卡）**：19 键之外全仓 arb 黑话扫尾=「知识星图」专名 25 键（§1.1 拍板保留，galaxyA11yCanvasSummary 等自不必动）+ 真黑话 2 键（→V3-FIX-411）；en 侧范围外零残留（orbit/Galaxy core/knowledge star/slipped/fly into/force field 全查零命中）。

## 4. 连带新发现：V3-FIX-411（已登记）

- `studyMaterialsHeroSubtitle`（zh）「…查看它们落到哪些**知识星点**…」——生造词，同族两键已随本卡改「知识点」；消费 document_library_screen.dart:593（1f，活）。
- `galaxyUploadHeadingTo`（zh）「正**飞向** {target}」——上传 overlay 进行态隐喻；消费 galaxy_document_upload_overlay.dart:386（1f，活）。
- 两键均不在 wt488 §1.2 24 键与 §1.3 清单内（wt488 盘点遗漏面），en 侧均白话；台账双键名 grep 零在挂 → 新登 V3-FIX-411（OPEN，zh 单边值级替换，备用 412 未动）。

## 5. 验证记录（真实运行）

- **flutter analyze**：`No issues found! (ran in 25.8s)`，零 issue。
- **守卫**：`check_l10n_regen_parity.py` → `L10N-REGEN-PARITY OK: 10087 template keys == abstract members; zh/en subclasses complete.`；`check_i18n_coverage.py` → `PASS — all presentation files with Chinese strings import i18n infrastructure`。
- **红先行/钉值**：galaxy 全族首跑 1 红——`galaxy_draft_review_screen_test.dart V25: full review flow` `Expected: exactly one matching candidate / Actual: Found 0 widgets with text "准备把它们送进你的星图"`（该测试钉 galaxyDraftCompletionReady 旧值，本卡改前 grep 词表漏「送进」所致，380b31b1 先例同款钉值连带）；钉值同步 `'准备把它们送进你的星图'→'准备加入你的星图'` 后单文件 3/3 绿、galaxy 全族复跑 **154 绿 1 skip 0 红**。
- **golden 漂移面**：b04_visual_baseline_capture + q03_visual_qa_longtail + golden_family_drift_guard 共 **50 绿**——golden 基线零漂移（b04 galaxy/tree_expanded 面在捕获前主动关掉「知识星确认」对话卡（capture_test:161-167「稍后再看」），19 键文案不入镜；q03 面为 auth/tasks/calendar/sprint 等屏不含 19 键消费点）；**无需重采，wt708 重采卡无本卡挂账**。附注：q03 运行会覆写 `v3-output/WT401-Q03-VISUAL/` 两个探针 JSON（测试副作用），已 `git checkout --` 还原不入库。
- **router smoke**：8/8 绿。
- **台账守卫**：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → `verify：297 行 V3-FIX 行，裸管分布 {8: 297}，多数形态 8 / verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`，exit=0（首跑 411 行 7 裸管 FAIL 已当场修列）。

## 6. 边界与自查

- 不新增键（19+2 键全为既有键改值）；arb 键名零改；`git diff --stat`=arb×2+gen×3 89 行 + test 3 行，无双数据库/后端/认证面触达。
- 49 冻结键零重叠：冻结池=aurora*19+visual*30 死键（W565 §3.1），19 键均 galaxy*/studyMaterials* 活键，前缀不相交。
- 「第 {current} / {total} 颗」（galaxyDraftReviewProgress）、「这颗星里装着什么」（galaxyDraftExcerpts）、「这颗星还没落稳」（galaxyUploadFailedTitle）、「{batchCount} 份待审核 · {draftCount} 颗星」（galaxyDraftPendingIndicator）等轻拟物键不在 403 清单，未动（如需治理应随 §1.3 半透明卡另议，不在本卡扩面）。
