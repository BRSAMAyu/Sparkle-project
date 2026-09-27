# WT731-ENL10N — V3-FIX-445 l10n EN 占位残余清零（诚实化运动尾巴）

- 工号：wt731
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt731-enl10n`
- 分支：`agent/node-b/wt731/enl10n`（base = main `6cc37d31`）；一律不 push
- 卡面：l10n EN 占位残余收尾——V3-FIX-362 campaign（136→wt685 终态 7）的清零批
- 交付：实施 commit（l10n 两件）+ docs commit（本 notes + 台账 445 行）

---

## 一、余量盘点（grep 现状，非沿用历史口径）

复现命令：`python3 scripts/devtools/count_en_placeholder_keys.py`（wt685 判例口径，本树实测）：

| 口径 | base（6cc37d31） | 终态 |
|---|---|---|
| **EN-DRAFT 多词（THE meter=136）** | **7** | **0** |
| EN-DRAFT 单词尾（留审尾） | 18 | 18（不动，见 §三） |
| EN-DRAFT-EXACT（==splitCamel(键名)） | 383 | 383（非 meter，wt685 裁定不作口径） |
| ZH-VARIANT（en 值含 CJK） | 23 | 23（全部 *Zh 后缀 deliberate 变体，非法形 0） |
| 活键集 | 9999 | 9999（零增删键） |

meter 余量恰为 7，与协调方预期一致，全部为 wt685 REPORT §二「留审清单」多词 adequate 残留 + 其标注的两项人审判定项（`ebSaveError` 歧义、`communityTaskTitleField`/`taskTitleLabel` 大小写统一）。

## 二、逐键 before/after（7 键，值面 surgical，键名/zh/占位符 schema 零改动）

| 键 | before (en) | after (en) | zh（权威，未动） | 消费点与理由 |
|---|---|---|---|---|
| `ebAddError` | Add Error | **Add error** | 添加错题 | add_error_screen.dart:377/:440 AppBar 标题；句式对齐仓内既有同域 CTA `errorBookRecordFirstError`='Record first error' |
| `ebEditError` | Edit Error | **Edit error** | 编辑错题 | add_error_screen.dart:376/:410/:439 AppBar 标题；与上行平行 |
| `ebSaveError` | Save Error | **Save this error** | 保存错题 | add_error_screen.dart:571 FilledButton 提交钮；**wt685 标注的「保存失败」歧义判定项就此收口**——Title-Case 裸 'Save Error' 与状态句形（同域 `ebAddFailed`='Add failed: {e}'）同形易误读，改后为明确动宾且邻位 `ebSaveChanges`/`ebSavingPleaseWait` 语义连贯 |
| `errorBookAddError` | Add Error | **Add error** | 添加错题 | error_list_screen.dart:178 FAB label；对齐同屏空态提示 `errorBookNoErrorsHint`='Tap the + button to add an error' 的 add an error 措辞 |
| `errorBookAddFirst` | Add First Error | **Add first error** | 添加第一道错题 | error_list_screen.dart:516 EmptyState actionText；与 review tab 同位按钮 `errorBookRecordFirstError`='Record first error' 大小写统一（原两键同屏异形） |
| `sendMessageLabel` | Send Message | **Send message** | 发送消息 | user_search_screen.dart:94 ListTile（私聊入口） |
| `communityTaskTitleField` | Task Title | **Task title** | 任务标题 | group_tasks_screen.dart:324 TextField labelText；**wt685 标注的大小写统一判定项就此收口**——向 `taskTitleLabel`='Task title' 对齐（该键本就不在 meter，统一方向取改 1 键而非改 2 键） |

统一方向说明：句首大写句式（sentence case）为该域既有权威形态（`errorBookRecordFirstError`='Record first error' 在先），非为躲 meter 正则而生造；这 7 键正因「忠实翻译与开发草稿形状碰撞」才留在 meter 里，收零只能迁移出该形状，迁移方向取仓内既有先例。

## 三、不动清单与理由（「多则只做真占位不改已译」）

- **单词尾 18 键**（'Title'/'Failed'/'Error'/'Success'）：zh 亦仅「标题/失败/错误/成功」的忠实短标签，wt685 列留审不计 meter，非占位；不动。
- **ZH-VARIANT 23 键**：全部 *Zh 后缀 deliberate 变体（代码 `zh?xZh:xEn` 分支选键，en locale 不渲染），wt677/wt685 双轮确认非遗漏；不动。
- **EN-DRAFT-EXACT 带**：wt685 明确「不作口径」（'Dark Mode'/'View Details' 等合法短标签同形）。其中已知的**真草稿形残留 8 键**：`chatConfidenceHigh/Medium/Cautious`（'Chat Confidence High' 等，zh 高/中/谨慎）与 `chatCompletionDone/NeedsInput/Partial/Processing/Blocked`——wt685 遗留①「移交下一批 l10n sweep，不占新号」，本卡按 meter 口径收尾不扩面，如实留档由协调方裁后续（机械可译面，估 <30 分钟工作量）。

## 四、gen-l10n 同步方式（外科判例，本次再度验证必要）

- 值面改动只触达 `app_localizations_en.dart` 的 7 个 getter 字面量；abstract 类与 zh 子类无字面量、零改动（wt729「gen×3」因删键需动 3 件，本批值面仅需 1 件）。
- **事故记录**：本机 `flutter pub get`（generate:true 隐式 gen-l10n）将 gen 件全量重排（en 子类 323 行 diff 噪声），与 wt685 记录的「全量 regen 647 行噪声」同源——按 wt363/wt685/wt729 外科判例 `git checkout` 还原 3 件 gen 至 HEAD 后重施 7 行值面手改；还原后全量验证重跑（analyze/PARITY/定向测试均以最终树为准）。
- 最终 diff 收敛：`app_en.arb` 7 行改 7 行 + `app_localizations_en.dart` 7 行改 7 行，共 2 文件 14 行改 14 行。

## 五、验证件套（本树实测，最终树）

| 门 | 结果 |
|---|---|
| flutter analyze | **No issues found**（还原 gen 重排后重跑确认） |
| L10N-REGEN-PARITY | **OK: 10054 template keys == abstract members; zh/en subclasses complete** |
| i18n-coverage 守卫 | **PASS** |
| meter 复跑 | 多词 **7→0**；单词尾 18、EXACT 383、ZH-VARIANT 23（*Zh 全 合法形）零漂移 |
| 定向测试 | **31 绿全过**：error_book presentation 5 件（error_list_screen / error_state / search_empty / add_error_validation_timing / error_detail_mastery）+ community create_group_guard + groups_hub_view + wt422_l10n_harvest_smoke + i18n_service + p2_07 i18n switch golden |
| 钉值测试 | 先行 find/grep：mobile/test 与 integration_test 对 7 键名及 7 个旧 EN 字面量（'Add Error' 等）**零钉值零引用** |
| 键数对称 | arb JSON 合法，en=zh=10054 键；键名零改动、49 冻结键不在本批触碰面 |
| 台账 | `ledger_union_merge.py --verify` 零 FAIL（7 列 8 裸管） |

## 六、遗留与交接

- EXACT 带真草稿形 8 键（§三）未占号留档，请协调方裁决是否开机械翻译批。
- `sendMessageLabel` 改句式后与同 sheet 邻位 `communitySendFriendRequest`='Send Friend Request'（Title Case）存在形态差异；后者不在 meter、属已译键，按「不改已译」不动，留档备查。
- 改动文件：`mobile/lib/l10n/app_en.arb`、`mobile/lib/l10n/app_localizations_en.dart`（实施 commit）+ 本 notes + `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 445 行（docs commit）。零产品 Dart 改动、零行为变更面（纯 en 文案）、不 push。
