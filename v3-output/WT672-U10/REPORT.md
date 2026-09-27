# WT672-U10 — 全产品文案与术语终审（增量轮）

- 工号：wt672（卡池 U-10；U-10 上一轮 wt363 READY_FOR_REVIEW，tasks.json 仍 TODO、无 review receipt，故本轮为增量终审非重做）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt672-u10`（分支 `agent/node-b/wt672/u10`）
- base SHA：`41aee60c`（main HEAD，含 wt669 D-08 复证）
- 交付 commit：见分支 HEAD（实施项 commit + 台账 commit + 本 REPORT commit）
- 卡面：`v3/07_tasks/cards/U-10.md`（权威）；Must read `01_product/PRODUCT_LANGUAGE.md`、`04_ux/COPY_TONE.md` 已读并作为裁定口径
- 交付状态：**READY_FOR_REVIEW**（worker 不自 DONE；Reviewer 须独立执行 §五验证件套关键项）

---

## 一、wt363 首轮双证判定（增量基线，不重做）

双证 = 历史 commit + 树内产物核验，逐项吻合：

| 首轮交付项 | commit 证 | 树内核验 |
|---|---|---|
| 死键收割 42 键（arb×2+gen×3 纯删除） | d85e9a9a | 现存活键集 10029 + 死键集恰=49（aurora*19+visual*30 冻结键，FIX-182 拍板范围），与 FIX-200/210 收割链账目吻合 |
| 红线 5 键值修复（空诺×2/黑话×2/机器口吻×1） | d85e9a9a | memoryMergeComingSoon/communityCommentsComingSoon/memoryExplanationInferredEpisodic/notificationRecallScore/chatMemoryNotRightPrompt 六处 zh+en 值逐键比对全部为修后文本 |
| group_members 硬编码英文空诺改复用键 | d85e9a9a | group_members_screen.dart:86 `toolCurrentlyUnavailable(groupMembersInvite)` 在场 |

**判定：wt363 首轮落地双证成立，本轮在其上增量。** 后续收割链（FIX-200/210 wt523/wt565/wt607）已把死键池收干净，冻结 49 键（aurora*19+visual*30）挂 FIX-182 用户拍板——本卡未触碰。

## 二、扫描方法与覆盖面

1. **活键集**：identifier-set 法（任何静态引用形态必含键名 token），lib+test 全 dart 剔 l10n/gen 产物 → 10078 键中 10029 活 / 49 死（=冻结键，零误差闭环）。
2. **红线规则扫**（活键 zh+en 值）：空诺（即将上线/coming soon/敬请期待…）、内部黑话（置信度/召回/token/向量/RAG/知识图谱）、诊断式语言、placeholder/debug、无来源精确数字（%/100/分数）、模板化鼓励/羞辱、「我理解你」无依据、「已完成」无 receipt。
3. **硬编码英文面扫**：`Text('英文')`、`Text("英文")`、`_buildKeyValue('英文',…)` 全 features。
4. **术语一致性抽查**：星图译名统一（FIX-201）、连续/streak 族、掌握度/mastery 族、backend zh message ↔ mobile ErrorMessages 模式匹配（auth/404/网络/限流/权限高频面）。
5. **文案-实现一致抽证**：天气图鉴 5 规则 vs `dashboard_service._calculate_weather`、资料归档「退出学习参考」vs sources 生命周期+retrieval invalidation、a11y 200% 缩放声明 vs 无钳制的 textScaler 透传、社群 fallback 调用链。

## 三、清单统计与处置

### 一致（抽查通过，不动）
- **天气图鉴 5 条规则逐条对上实现**：`days_left<3 且 progress<0.5→风雨`、`progress<0.2 且 days_left<7→薄雾`、`2 天无完成任务→薄雾`、`焦虑>0.5→风雨（覆盖）`、`progress>0.8→流星` 与 `dashboard_service.py:347-383` 全等；文案还自带「更容易/倾向/参考规则」恰当对冲，且「预览不会改动真实天气」如实。
- **星图术语统一保持**：活键 zh 值「星图」84 处，「星座/星系」零残留（FIX-201 wt498 收口未回潮）。
- **backend zh message ↔ mobile 映射一致**：「没有找到/不存在/登录令牌无效，请重新登录/太频繁/权限」等高频 detail 均被 ErrorMessages 六族模式覆盖并转本地化文案。
- 「连续/streak」「掌握度/mastery」族用词跨面一致；`proposalUnknownHint`（"先别当成已完成"）等反冒充文案在场；空诺扫描活键零命中（除 R3 兜底模板内用户口吻 "soon" 非产品承诺）；诊断式 33 命中全部为错题/连接诊断等真实功能语义，非心理诊断。

### 超实现/欠一致（本卡实施 ≤10 项，全部纯文案：改真话不改行为）

| # | 面 | 修复 |
|---|---|---|
| 1 | `studyMaterialsArchiveSuccess` zh/en | 去「RAG 上下文」黑话，承诺不变（归档→retrieval invalidation 实证为真）：zh「资料已归档，之后的学习参考不会再用到它。」/ en "Material archived — it won't be used as a study reference anymore." |
| 2 | `memoryEvidenceToken` zh/en | 值为 id/token 字符串（correction_id 等），标签去英文黑话：zh「证据 Token→依据编号」/ en "Evidence Token→Evidence ID" |
| 3 | memory_detail_screen 13 处硬编码英文标签（英中混杂，COPY_TONE 明令项） | preference 分支 'Key'→memoryFieldName「名称」、'Value'→memoryFieldContent「内容」、'Confidence'→memoryConfidence「置信度」、'Updated'→memoryLastUpdated「最后更新」、'Retracted'→memoryRetractedAt「撤回时间」；三分支 'Evidence'（分值行）→新键 memoryEvidenceScoreLabel「证据强度」×3、'Corrections'→新键 memoryCorrectionCountLabel「纠错次数」×3。展示层零行为改动；复用键 5 个 + 新键 2 个（arb×2+gen-l10n 重跑） |

新键抉择说明：'Evidence' 行展示的是 evidence_score 分值而非计数，既有 `memoryEvidenceCount`「证据数」语义不符不可误用；'Corrections' 无裸标签键（`memoryPanelCorrectionCount` 值含 {count} 会与 kv 值重复渲染"纠错 3 : 3"），故各新 1 键。

### 只登记不动（行为相关，V3-FIX-357~360，台账 commit 在场）

- **R1 = V3-FIX-357（P3）**：置信度百分比族 8 活键 6 面（sourceExplanation/intentConfidence/planReviewConfidenceTitle/personaConfidence/systemUpdatesConfidence/memoryConfidence+memoryConfidenceValue+memoryCorrectionLowerConfidence），raw 0.xx 直出违 PRODUCT_LANGUAGE；改定性词需动调用点传值逻辑。继承 wt363 登记（原 12 键，wt369 D-07 已清 lfcConfidence 等面）并精确化。
- **R2 = V3-FIX-358（P3）**：EN 侧占位翻译债精确清点 **136 活键**（wt363 估 ~110）；另 22 键 en 值含 CJK 全为 *Zh 后缀 deliberate 变体（代码分支选键，en locale 不渲染）非遗漏。
- **R3 = V3-FIX-359（P2）**：社群 Agent 兜底模板无披露——group 预设流空输出时本地模板带 `kAgentMetadataKey:true` 以 agent 身份直接发进群（ErrorEvent 路径不顶替，仅空输出路径）；private 预设落草稿较轻；模板仅复述近期消息无事实捏造，缺披露属行为/UX 决策。
- **R4 = V3-FIX-360（P4）**：ErrorMessages.getLocalizedMessage 默认分支直出 technicalMessage（未命中模式时后端英文原文可直达 zh UI）；藏真话 vs 直出属行为取舍。
- 报告级备注（不占 FIX 号）：mock community 帖子含编造见证（"同类错误减少了60%"），但 `DemoDataService.isDemoMode` 恒 false 且全仓无置 true 点——生产不可达，demo-mode-by-design，随 R3 社群面后续一并裁决即可；memory_detail 面原始内部量（importance/decay_policy/evidenceToken 原始 id 值）直出并入 R1 同卡收敛；`taskExecutionAiPartial` 等 lib 零引用仅 test 引用的"test-only 活键"现象移交收割链下一轮核减。

## 四、卡面验收对照

- [x] **核心 journey 无未解释内部术语/placeholder/raw l10n key**：活键值级六类规则扫描零 raw-key 渲染（l10n.x 值内引用零命中）；zh 面黑话「RAG 上下文」「证据 Token」已修（实施 #1/#2）；记忆详情面 13 处英文硬编码标签清零（实施 #3）；剩余「Token 统计」族集中在 AI Ops/执行预算等技术表面（PRODUCT_LANGUAGE 允许必要技术表面）；placeholder 类活键 16 个全为品牌/专有名词（Sparkle/Google/OpenClaw/Tailscale/OCR 等）合规。
- [x] **Why/失败/不确定表达符合 PRODUCT_LANGUAGE**：`receiptUncertainLine`「{count} 条我还不确定，你可以直接纠正」、memory why-this（wt363 修后文本）、纠正提示、失败文案（失败诚实+可纠正入口）逐面抽查合规；天气/掌握度等推断面均带「预估/参考/更容易」观察性措辞；无「我理解你」式无依据断言（零命中）。
- [x] 英文仅在专有名词/必要技术表面：硬编码英文面扫剩余命中全为插值/专有名词（HTTP/WebSocket chips、模型名等）；zh 默认体验英文标签残留已清（实施 #3）。
- Forbidden 遵守：未重建权威真源（arb 单源未移位）；无 mock 冒充；未弱化守卫（86 规则全绿）；未动冻结 49 键、.env、tasks.json；未 push。

## 五、验证件套（本树实测）

| 门 | 结果 |
|---|---|
| base/final SHA | base `41aee60c`；final 见分支 HEAD |
| analyze A/B | 变更前后各跑一次，双双 "No issues found"（E0/W0/I0 零漂移；含 gen-l10n 产物态复跑） |
| gen-l10n 契约 | exit 0；**本卡保留 gen 产物**（偏离 wt350 保留外科态判例：本次实测其唯一"噪声"是清除历次外科收割遗留的空行串与键位规范化，净减 cruft 且可复现，`git diff` 逐 hunk 核过） |
| L10N-PARITY | `check_l10n_regen_parity.py` → OK: 10080 template keys == abstract members; zh/en subclasses complete |
| 全量守卫 | `run_all_rule_guards.sh --jobs 4` → **all rule guards passed (86 rules)**，FAIL=0（AQ/BG 环境件按协议自主仓补拷 backend app.gen + gateway gen） |
| 定向 flutter test | **29/29 绿**：memory_correction + memory_explain_view + memory_panel_screen（直接渲染 MemoryDetailScreen 三件）6 绿；wt363 首轮 DEFERRED 钉测试补跑 nav_decontextualization_contract + insights_frontend_smoke + learning_insights_navigation + i18n_service 23 绿（swap 窗口 19.5G 已开，首轮欠账一并清） |
| mypy | 零 Python 改动（diff 全 .dart/.arb/台账/REPORT），棘轮天然不推高 |
| simulator/integration | DEFERRED 如实声明（LIGHT 纪律；动态 journey 截图证据缺口沿用 wt363 登记，移交主会话 HEAVY 窗口）；部分代偿：三份 MemoryDetail widget 测试真实渲染改动面并断言通过 |

## 六、并行卡避让

变更文件 = mobile l10n 六件 + memory_detail_screen.dart + 台账 + 本 REPORT。与 wt666（backend insights）、wt667（mobile golden）、wt670（backend mypy）、wt671（mobile 设计表面盘点）零产品文件交集（主仓工作区 wt667 的 golden 未提交改动不在本树；台账按惯例各会话追加行集成）。

## 七、收工清单

- [x] analyze A/B 零漂移（含 gen 产物态复跑）
- [x] gen-l10n exit 0，产物保留（理由见 §五）
- [x] L10N-PARITY OK 10080
- [x] 守卫 86 全绿
- [x] 定向 test 29/29（含首轮 DEFERRED 补跑）
- [x] 台账 V3-FIX-357/358/359/360 登记（grep 占号实证 357 起可用，最高 356）
- [x] 实施项 commit + 台账 commit + REPORT commit
- [ ] Reviewer 独立验收（READY_FOR_REVIEW → 验收）
