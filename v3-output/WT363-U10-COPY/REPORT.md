# WT363-U10 — 全产品文案与术语终审 + 死键收割（U-10）

- 工号：wt363（wt356 卡 U-07 done 解锁）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt363-u10-copy`（分支 `wt363-u10-copy`）
- base SHA：`4451bb1a`（分支点 main，含 wt359 搜索定位修复）
- final SHA：见分支 HEAD（交付 commit message）
- 卡面：`v3/07_tasks/cards/U-10.md`（权威）；Must read `01_product/PRODUCT_LANGUAGE.md`、`04_ux/COPY_TONE.md` 已读并作为裁定口径
- 协作约束遵守：未动 wt358（U-06 状态面）在改的任何文件（其 worktree 变更清单已核对：state* 新键/profile_screen 等，与本卡 6 文件零交集）

---

## 一、死键收割（42 键，wt356 登记批）

### 零引用确认方法
对 wt356 REPORT §五.1 登记的各族键逐一展开为 42 个具体键名，`grep -rE '\b<key>\b' lib test --include=*.dart`（排除 `lib/l10n/` 生成物）逐键全零命中后删除。`chatSettingsSeedLibrary` 经查仍有 1 处真实引用（chat_settings_screen 种子增强开关）→ **保留未删**（诚实裁定，不硬凑数字）。

### 删除清单（42 键）
- insightHub 族 13：`insightHubSimulation/Theater/CompactSimulation/CompactTheater/RecommendedSeeds/RecommendedSeedsCount/SeedsToExplore/ContinueLastSimulation/ContinueLastTheater/NoRecentTheater/StartSimulation/ContinueSession/ContinueTopic`
- ins 族 7：`insSimLabel/insTheaterLabel/insOpenSim/insTheaterFallback/insSimFallback/insStartSimulation/insFocusedTheater`（后 3 键为同族旁支，同法零引用确认）
- chatPrompt 族 4：`chatPromptRefinePath/RefinePathMessage/SimulateRound/SimulateRoundMessage`
- report 行动卡 2：`reportActionExploreNode/EnterSimulation`
- chat_bubble 预览 6：`chatViewTheaterDetails/SimulationDetails`、`chatSimulationTitle/Desc`、`chatTheaterTitle/Desc`
- chatSettings seed 计数族 7：`chatSettingsCurrentSeeds/SeedsEnabledCount/SeedsEnabledNone/SeedDisableHint/SeedEnableHint/SyncingSeeds/SeedsDefaultOff`
- insights overview 2：`lioNoTheaterYet/lioRecommendedSeeds`
- profile 1：`profileSubtitleVisualElements`

### 外科同步与卫生验证（wt350 判例形制）
- arb ×2 删 42 键 + 7 个含 placeholder 的 `@meta` 块；gen ×3 外科删成员（abstract doc 块+声明行 / impl `@override`+成员块）。
- diff 全量自查：**+0 / -738，纯删除零插入**；非键名行均为 placeholder @meta 块内部行（属键变更本体）。
- `flutter gen-l10n` 实跑 exit 0（arb 与生成器契约无断裂）；实跑产物与本机 3.41.3 全量格式重排噪声确认与 wt339/wt350 发现一致 → **弃用其产物，保留外科态**（gen-l10n 仅作契约互证）。
- arb JSON 合法性 python 校验通过（各 11370 键）。

## 二、文案红线修复（终审口径：不捏造、不诊断、不空诺；双语一致）

全部为 **arb 值级外科替换 + gen 值同步**，零业务逻辑改动、零新键（Forbidden 合规）：

| # | 键 | 面 | 修复 |
|---|---|---|---|
| 1 | `memoryMergeComingSoon` | 记忆详情合并 snackbar | zh「合并功能即将上线→**暂未开放**」/ en "coming soon→**isn't available yet**"（去空诺，改当下事实陈述） |
| 2 | `communityCommentsComingSoon` | 社群 Feed 评论 snackbar | 同上口径：zh「暂未开放」/ en "aren't available yet" |
| 3 | `memoryExplanationInferredEpisodic` | 记忆详情 why-this | 删内部黑话「证据 **token**、置信度与撤销路径」→「保留了依据，也支持撤销」；en 同步去 "evidence tokens, confidence"（USER_LANGUAGE：说用户可感知的事，不说系统内部对象；依据与撤销均为真实存在能力，无捏造） |
| 4 | `notificationRecallScore` | 通知中心详情行 | 「召回评分→**记忆保持预估**」/ "Recall score→**Estimated retention**"（去 RAG 味「召回」黑话；「预估」如实标注为估计值，配合既有「标记不准」可纠正入口） |
| 5 | `chatMemoryNotRightPrompt` | 聊天记忆回执纠正 | 「请降低置信度（机器口吻）→**之后请少参考这条，不要直接引用**」；en 同步去 "lower confidence" |
| 6 | `group_members_screen.dart:83` | 社群成员页邀请按钮 | **硬编码英文空诺** `'Invite feature coming soon'`（绕过 l10n，zh 用户看英文）→ 复用既有键 `toolCurrentlyUnavailable(groupMembersInvite)`＝zh「邀请成员暂不可用」/ en "Invite members is currently unavailable"（1 行展示层修复，复用键不引新键） |

过程修正（自查发现并修复）：en 生成 dart 串内撇号未转义曾致 analyze E30，已转义修复（`isn\'t` 等 3 处）；zh gen 4 值曾因脚本早退未落盘，已补齐并做 arb↔gen 逐键一致终验（5 键 en/zh 全 OK）。

## 三、验收对照（卡面 Acceptance）

- [x] **核心 journey 无未解释内部术语/placeholder/raw l10n key**：zh 全量 11370 键规则扫描（黑话/诊断/空诺/placeholder/raw-key/玄学分数六类）+ gen-l10n 契约实跑；raw-key 零命中；zh 默认体验的黑话/空诺可达面已修（上表 6 处）。残余见 §四登记。
- [x] **Why/失败/不确定表达符合 PRODUCT_LANGUAGE**：memory why-this（#3）、纠正提示（#5）、不可用提示（#1/2/6）均改为事实陈述+可纠正路径，无诊断式语言、无空诺；`personaLearningStyle`（用户自选 chip 的步骤标题，非 AI 断言）与 `communityMatchReasonStyleDiff`（匹配理由中性解释）裁定合规不动。
- 交付状态：**READY_FOR_REVIEW**（worker 不自 DONE；Reviewer 独立执行 arb↔gen 一致性抽查与 diff 自查）。

## 四、发现登记（不阻塞交付，移交后续卡）

1. **en 占位翻译批量债（~110 键）**：en arb 值为开发草稿占位（如 "Plan Archive Title"、"Sprint Info Title"、"Password Set Hint"），zh（模板/默认体验）完好。逐键清点见本卡扫描产物特征：值以 Title/Desc/Label/Subtitle/Hint/Message 结尾或与键名雷同，全部 USED。修复需按 Aurora tone 逐键人工翻译（LIGHT 卡不宜机翻批量改），建议独立 i18n 卡承接。
2. **置信度百分比族（12 键 USED）**：`personaConfidence/systemUpdatesConfidence/memoryConfidence(Value)/memoryCorrectionLowerConfidence/planReviewConfidenceTitle/intentConfidenceLabel/sourceExplanationConfidence/lfcConfidence/goalIntentConfidence/memoryPanelConfidenceValue(dead)/chatMemoryNotRightPrompt(已修口吻)`——PRODUCT_LANGUAGE 明令禁「0.73 confidence」式表达，定性词改写需动调用点逻辑（M-10 先例只清了 2 面），本卡 Forbidden 禁业务逻辑 → 整族移交逻辑卡。
3. **死键积压二批（5 键零引用已确认未删）**：`stayTuned/errorBookEditInProgress/errorBookReviewInProgress`（值含空诺）、`dataUsageAiCardDesc/dataUsageTagLearningStyle`（值含诊断式表述）——不在 wt356 登记范围，按卡边界只登记不删，可并入下轮收割。
4. U-07 遗留「金测试 env 门差异」未属本卡，维持其 REPORT 登记。

## 五、测试与证据

- **base/final SHA**：base `4451bb1a`；final 见分支 HEAD 交付 commit。
- **analyze 门**：`python3 scripts/check_flutter_analyze_gate.py` → **ERROR=0 / WARNING=16 / INFO=588**，与开工基线（本树实测同值，容差内）**逐位零漂移**；E0 同时证明 gen 外科编辑后类编译完整（漏删/错删必爆编译错）。
- **守卫**：`bash scripts/run_all_rule_guards.sh` exit 0（**84 rules**，worktree 内实测；AQ/BG 环境红已按 §4 协议补拷 backend/gateway/mobile gen 三件套后转绿）。
- **mypy**：零 Python 改动（diff 全 .dart/.arb），棘轮天然不推高。
- **定向 flutter test：DEFERRED** —— 开工/收工两次实测 swap free 1136M/925M < 1.2G 硬门，按内存纪律不执行。变更回归面分析：42 删键 + 5 改值 + 1 展示层修复在 `test/` **零引用**（逐键 grep 实证），analyze E0 背书编译完整。补跑命令（swap≥1.2G 窗口，串行）：
  ```bash
  cd mobile && flutter test --concurrency=1 \
    test/widget/nav_decontextualization_contract_test.dart \
    test/widget/insights_frontend_smoke_test.dart \
    test/widget/learning_insights_navigation_test.dart
  ```
- **simulator/integration 证据：DEFERRED**（LIGHT 纪律禁模拟器）。卡面 Forbidden「不得只通过静态代码阅读宣称用户体验通过」——如实声明：本交付动态证据 = analyze E0 + 守卫 84 + 上述补跑钉测试（swap 窗口执行），真机 journey 截图证据缺口移交主会话 HEAVY 窗口。
- **gen-l10n 契约**：实跑 exit 0（后按 wt350 判例弃用其格式噪声产物，保留外科态）。

## 六、Forbidden 遵守

- 未重建既有权威真源（arb 单一事实源未移位；routes/portfolio 等未触碰）。
- 无 mock/seed 冒充；未只凭静态阅读宣称体验通过（DEFERRED 如实标注）。
- 未弱化安全/幂等/隔离/审计守卫；守卫 84 全绿通过。
- 零新 l10n 键；唯一代码改动为 1 行展示层字符串源替换（硬编码→既有键），非业务逻辑。
- 未动 wt358 在改文件（逐文件核对零交集）。

## 七、收工清单

- [x] 守卫 84 exit 0（commit 前置门已过）
- [x] analyze E0/W16/I588 零漂移
- [x] mypy 天然满足（零 py 改动）
- [x] 交付物（本 REPORT + changes.patch）commit 进分支
- [x] `git diff --binary main...HEAD` 生成 changes.patch（--binary）
- [x] 定向 flutter test：DEFERRED（swap 925M<1.2G，补跑命令见 §五）
- [ ] mobile/build、.dart_tool、/tmp 自产物清理（收尾执行）
