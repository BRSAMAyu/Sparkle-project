# wt283-dedup-section-titles 卡报告（A 线·同屏双标题模式统一）

日期：2026-09-22 ｜ 分支：wt283-dedup-section-titles（本地 1 commit，未 push）｜ 基点：e4d795e1

## ① 摸排结果：全库 1 屏 3 对

**ExpandableSection（N17 披露件 owner）全库使用面 = 3 文件**：

| 文件 | 用法 | 双标题？ |
|---|---|---|
| `core/design/components/organisms/expandable_section.dart` | 组件定义 | — |
| `features/chat/presentation/widgets/transparency_panel.dart` | 4 处（工具/Token/Control Tower/步骤） | 无——子内容均为列表行/时间线，不重复标题 |
| `features/community/presentation/screens/accountability_detail_screen.dart` | 5 处 | **3 对同串双现** |

**3 对双标题（均在 accountability_detail_screen.dart）**：

| 段落标题（ExpandableSection，保留） | 卡内标题（私有卡 Row[icon+Text]，移除） |
|---|---|
| :333 `accountabilityPendingPolicies`（待执行策略） | :975（`_PendingPoliciesCard`） |
| :342 `accountabilityRecentReflections`（近期反思） | :1028（`_RecentReflectionsCard`） |
| :354 `accountabilityForesightHint`（前瞻提示） | :1105（`_ForesightHintCard`） |

三个卡均为**文件私有类且仅在该 ExpandableSection 内实例化**——「卡可独立复用于无段落标题上下文」例外**不成立**，无例外屏。

**同类分区组件延伸摸排**（启发式：同文件同 l10n key 既作 `title:` 又再现）：
- `_SectionCard`/`_GoalPanel`（同文件）：子内容（`_GrowthSummary`/heatmap/checkin 列表）不重复标题，干净。
- `PendingCommitmentsSection`：section label + 内容卡，无标题双现。
- `accountability_hub_screen`：`cahMyCommitments` 双现 = header `_MetricTile`（数值瓦片）+ `_Section` 标题，**不同 UI 角色**，非卡内标题双现；`partners_tab.dart` 独立面自身无双现。
- 相邻但不同模式（不动）：`skill_management` 「我的方式」×2 = AppBar 标题 + Tab 标签；`error_detail` 「还在学」×2 = 元数据徽章 + 统计卡值位（test 注释已注明语义）。

## ② 裁决与落地

**段落标题保留、卡内标题移除**（分区件单源播报；移动端红线遵守：零交互行为变化，纯视觉收敛）：

- `_PendingPoliciesCard` / `_RecentReflectionsCard`：标题行只剩图标 → 按裁决「收敛为内容对齐」，图标并入首行内容（条数 headline 行）；
- `_ForesightHintCard`：图标并入提示正文行（多行文本 `CrossAxisAlignment.start` + `Expanded`）。

测试随动 + 顺手修复（wt274 同族漏网）：
- `commitment_detail_screen_policy_test.dart`：`findsNWidgets(2)` → `findsOneWidget`，注释更新（基线 pass→pass，断言语义随裁决）。
- `reflection_recent_summary_test.dart`：**改动前基线即 0/3 全挂**（DateFormat 解锁渲染后暴露的既有债务——harness 缺 `SparkleThemeExtension`，与 wt274 修 commitment 同根因）；补主题注册后随去重 3/3 绿（其 `findsOneWidget` 断言在去重后语义正确）。

## ③ 防回归守卫（已实现并登记）

`scripts/guards/check_section_title_duplication_ratchet.py`（新，TYPO-RHYTHM 家族同款结构）：

- 维度 `dualTitle`：同文件内 l10n key 作 `title: context.l10n.<key>` 注册后又出现 ≥2 次（注释行剔除；`*.g.dart`/`*.freezed.dart` 除外）。已知边界：本地变量别名 `l10n.x` 风格不扫（S 卡接受，反模式复发面是直引风格）。
- ratchet only-down：`section_title_duplication_baseline.json` 冻结去重后存量 **32/23 文件**（多为 title+dialog/Semantics 合法复用，一并冻结）；新文件带双标题或存量上升即 fail；`--update-baseline` 拒绝升。
- self-test 4 例全过（clean PASS / 双标题 NEW FAIL / ratchet 平=PASS / 超=FAIL）。
- 已登记 `scripts/rule_guard_manifest.tsv` → `UX-DUPTITLE`；runner 实跑 exit=0。
- accountability_detail_screen.dart 去重后已完全出清存量。

## ④ 验证（对比法）

- 环境：`flutter pub get` + `PATH=~/.pub-cache/bin:$PATH buf generate --template buf.gen.dart.yaml`（gen/ 为 gitignored，不入 commit）。
- 定向测试（单文件单进程 `--concurrency=1`，swap≥1.2G 门错峰）：
  - `commitment_detail_screen_policy_test.dart`：基线 3/3 pass → 改后 **3/3 pass**；
  - `reflection_recent_summary_test.dart`：基线 **0/3 fail**（既有债）→ 改后 **3/3 pass**。
- `flutter analyze` 三改动 dart 文件 vs HEAD 基线克隆（`git clone` 至 /tmp，纪律允许法）：59 vs 59 条，按「消息+规则」配对 **零新增零消失**（59 条全为既有 info 级风格债）。
- l10n 三文件被工具链再生成纯格式扰动 → 已按纪律 `git checkout -- mobile/lib/l10n/` 还原。

## ⑤ 资源峰值与清理

- HEAVY 门遵守：flutter test 前轮询至 swap 空闲 1312M（≥1.2G）、load 4.28 才起跑；单进程并发 1。
- 峰值观测：等待期 swap 空闲最低 437M（他卡负载），本卡进程未致熔断；无模拟器/浏览器/Gradle。
- 收工已清：`/tmp/wt283-baseline`（基线克隆）、`/tmp/wt283-issues-*.txt`、`mobile/build`、`.dart_tool`。

## ⑥ 交接建议

1. `reflection_recent_summary_test` 的修复与 wt274 同族，若 wt274 已合入主仓，本卡 patch apply 时该文件可能冲突——以本卡版本为准（含去重后语义）。
2. 守卫基线含 23 文件合法/存量复用（32 key），后续 A 线若做「title+dialog 复用」清理，`--update-baseline` 只降不升即可逐批出清。
3. `skill_management`（AppBar+Tab）与 `error_detail`（徽章+值位）的双现属不同模式，A 线若立新卡可从这两处盘起。
