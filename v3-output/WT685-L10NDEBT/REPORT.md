# WT685-L10NDEBT — V3-FIX-361/362 l10n 债修复批

- 工号：wt685（前卡 wt682 额度窗口阵亡零产出，本卡重发）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt685-l10ndebt`（分支 `agent/node-b/wt685/l10ndebt`）
- base SHA：`945e7132`（main HEAD）
- 交付：实施 commit（362+361 各一）+ 台账单 commit + 本 REPORT commit；一律不 push
- 交付状态：**READY_FOR_REVIEW**（worker 不自 DONE；Reviewer 须独立执行 §五关键项）

---

## 一、362 计数口径复核（wt677 异议收案）

wt677 verify4 对 362 登记 136 提出方法学异议（独立复算 217，更严变体 18~152）。本轮以可复现脚本收案：

**判定规则**（`scripts/devtools/count_en_placeholder_keys.py`，复现命令 `python3 scripts/devtools/count_en_placeholder_keys.py`）：

1. **活键集**：标识符集法——键名 token 出现在 mobile/lib 或 mobile/test 任意 .dart 中（剔 `lib/l10n`、`lib/gen` 产物目录）= 10031。
2. **EN-DRAFT（计量口径）**：en 值全部词首字母大写（Title-Case 词组）**且**以 9 个开发描述符词尾之一结尾（Title/Desc/Label/Subtitle/Hint/Message/Failed/Success/Error，大小写敏感）。
   - **多词子集 = 136，与 wt672 登记数精确复现**（计量 meter）；
   - 单词尾（裸 `Title`/`Failed`/`Error`/`Success`）= 19，为忠实短标签混合带，列留审不计 meter。
3. **EN-DRAFT-EXACT**（en 值 == splitCamel(键名)，503）**不作口径**：合法短标签（'Dark Mode'/'View Details' 等）同形，纯键名拆分判据过宽。
4. **ZH-VARIANT**：en 值含 CJK = 23（wt677 复现 22 后又有新 *Zh 键入库），全部 *Zh 后缀 deliberate 变体、非法外残留，非遗漏——wt677 该项结论维持。
5. **wt677 的 217 未能复现**（自然变体带 19~155，更宽并集至 303）；双方均未留脚本，217 定性为方法敏感约数，台账引用数以本脚本多词 meter（136）为准。

## 二、362 实施批（132 键翻译）

`scripts/devtools/apply_wt685_en_translations.py` 显式逐键人工映射（无机翻），zh 值为翻译源，仓内 en 风格对齐：house 术语（错题=error/Error Book、打卡=check-in、冲刺=Sprint、前瞻=foresight hint）、消息/提示/状态句 sentence case、短名词标签可 Title Case。

- **meter 前后：136 → 8**；其中 `planReviewConfidenceTitle` 随 361 收敛 → **终态 7**；单词尾 19 → 18。
- **无新增占位**（改动仅限命中集内）；死键零漂移（活键集 HEAD 10031 → 现在 10032，唯一新增 live 键 = 新键 confidenceWithBand）。

**留审清单（不硬译，共 25 键）**：

- 多词 adequate 残留 7（house 一致、语义无损，译同义反降质）：`ebAddError`/`errorBookAddError`='Add Error'、`ebEditError`='Edit Error'、`ebSaveError`='Save Error'（**人工复审判定项：en 有「保存失败」歧义**）、`errorBookAddFirst`='Add First Error'、`sendMessageLabel`='Send Message'、`communityTaskTitleField`='Task Title'（与 `taskTitleLabel`='Task title' 大小写不统一，人工裁决统一方向）。
- 单词忠实标签 18：`achievementRewardTitle`/`shopItemTypeTitle`='Title'（称号 house/gaming 译法）、`calTitle`/`calendarTitleHint`/`goalDetailEditTitle`/`memoryFieldTitle`/`seedLibraryDetailAddItemTitle`='Title'（字段标签，zh 亦仅「标题」）、`capsuleJobStatusFailed`/`chatAttachmentFailed`/`syncCenterStatusFailed`/`syncCenterTabFailed`/`taskMonitorFilterFailed`/`statusFailed`/`chatActionStatusFailed`='Failed'、`colorError`/`chatWorkflowStatusError`='Error'、`colorSuccess`='Success'、`chatLabelError`='Error'（错题 house 译法）。

## 三、361 实施批（8 键 6 面定性化）

PRODUCT_LANGUAGE「0.73 confidence」禁令 → 「定性档位词（百分比细节）」形态，如「我比较确定（73%）」/ "I'm fairly confident (73%)"。

- **档位词**：high=我比较确定 / medium=有一定把握 / low=我还不太确定（en: I'm fairly confident / I'm somewhat confident / I'm not quite sure yet）。**阈值与 backend `ux_envelope._confidence_band` 对齐**（high ≥0.8、medium ≥0.55），Dart 镜像 `mobile/lib/core/extensions/confidence_band.dart`（含 >1 视为已是百分数的归一化，与 source pill 既有约定一致）。
- **键名零改动**（49 冻结键未触碰；占位符 schema 演进属台账预告的「调用点传值逻辑」）：4 百分比键 `sourceExplanationConfidence`/`intentConfidenceLabel`/`personaConfidence`/`systemUpdatesConfidence` 值改 ICU select 形态（band+percent），gen-l10n 生成 selectLogic 分支。
- **逐面**：chat source pill、goal intent chip、persona metadata 行（原 "0.85" 裸串）、system updates pill、plan review（标题→「把握有多大/How confident I am」+同行 **Dart 内硬编码 `'..%'` 直出**改走新键 `confidenceWithBand`）、memory detail（`memoryConfidence`→「把握程度」、`memoryConfidenceValue` 值传定性串、kv 三处 `toStringAsFixed(2)` 裸值清零）。
- `memoryCorrectionLowerConfidence`（纠正动作按钮）值改「别太信这条 / Not so sure about this」——原「置信度较低」读作状态而非动作。
- **新键 1 个**：`confidenceWithBand`（arb×2+gen 重跑）。**并行卡避让**：wt683（U-02 令牌面）如需 arb 新键与本键同文件追加，merge 时按键名并集无冲突；本卡 arb 值面改动如与其冲突以其为准让渡并在其回报注明。

## 四、卡面验收对照

- [x] 362 占位计数下降无新增：meter 136→7（终态）、单词尾 19→18、死键零漂移、ZH-VARIANT 零非法形。
- [x] 361 百分比带档位词：6 面全部定性化，raw 0.xx 与 Dart 内硬编码 % 清零（8 键逐面见 §三）。
- [x] Forbidden：未动 49 冻结键/.env/tasks.json；未重建权威真源（arb 单源未移位）；未 mock 冒充；未 push；新发现未占号（chatConfidence{High,Medium,Cautious} 3 键 en 仍为键名拆分草稿 'Chat Confidence High' 等，属 464 EN-DRAFT-EXACT 带内残留，**移交下一批 l10n sweep，不占新号**）。

## 五、验证件套（本树实测）

| 门 | 结果 |
|---|---|
| base/final SHA | base `945e7132`；final 见分支 HEAD |
| gen-l10n | exit 0；select 语法生成 `intl.Intl.selectLogic` 分支正确（zh/en 子类抽验，en 撇号转义亲验）。**本机 SDK 复现 wt679 记录的跨 SDK formatter 漂移**（全量 regen 647 行噪声）→ 按 wt350/wt679 外科判例保留 HEAD 格式，仅对 9 键成员块+新键 getter 做 regen 对齐移植（gen diff 收敛到 173 行），L10N-PARITY 语义校验兜底复跑 OK；偏离 wt672「保留 regen 产物」判例的记录与 wt679 一致 |
| L10N-PARITY | OK: 10087 template keys == abstract members; zh/en subclasses complete |
| flutter analyze | No issues found（E0/W0/I0） |
| 定向 flutter test | **40 绿**：memory_correction + memory_explain_view + memory_panel_screen + plan_review_card + user_persona_screen 13；insights_frontend_smoke + learning_insights_navigation + evidence_insight_card 15；memory_settings + memory_auto_memory_panel 4；i18n_service + p2_07 i18n golden 8 |
| 守卫 | `run_all_rule_guards.sh --jobs 4` → **all rule guards passed (86 rules)**，FAIL=0（AQ/BG 环境件按协议自主仓补拷 backend app.gen + gateway gen，gitignored 不入库） |
| 台账 | `ledger_union_merge.py --verify` 通过（284 行 V3-FIX、零冲突残留、ID 无重号） |
| 死键/活键账 | 活键 10031→10032（+confidenceWithBand）；零死键漂移 |
| mypy / Python 行为 | 零 Python 产品代码改动（新增 3 个 devtools 测量/实施脚本纯 stdlib 只读或写 arb），棘轮不推高 |

## 六、并行卡避让与遗留

- 变更文件 = mobile l10n 五件（arb×2+gen×3）+ 6 个消费面 dart + `lib/core/extensions/confidence_band.dart` + 3 个 devtools 脚本 + devtools README + 台账 + 本 REPORT。与 wt683（令牌面，arb 值面独占约定不破——本卡即约定中的「你」）、wt684（docs）零产品文件交集。
- 遗留（不占号）：① EN-DRAFT-EXACT 带 464 中 155 之外的草稿形残留（如 chatConfidence* 3 键 'Chat Confidence High'、chatCompletion* 'Chat Completion Done' 等）——下一批 l10n sweep 的机械可译面；② `ebSaveError` 歧义与 `communityTaskTitleField`/`taskTitleLabel` 大小写统一，随留审清单人审。

## 七、收工清单

- [x] 口径复核先行（复现器入库后才动翻译）
- [x] 362 meter 136→7、留审 25 键逐键列明
- [x] 361 六面定性化、键名零改动、新键仅 1
- [x] analyze 零 issue / PARITY OK 10087 / 守卫 86 全绿 / 定向 test 40 绿 / 台账 --verify 通过
- [ ] Reviewer 独立验收（READY_FOR_REVIEW → 验收）
