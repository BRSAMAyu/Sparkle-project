# 批1-B · S2 机话与数据字面量直出清偿 — 施工报告（wt93）

> 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt93`（wt93-v3，基线 main@fe3bc1fd）
> 规格：`v3-output/DL-R3/SPEC.md` §6 ｜ 施工图：`v3-output/DL-R1-AUDIT/TRIAGE.md` §3 ｜ 证据：AUDIT S2
> 交付：`v3-output/B1-B/changes.patch`（24 文件，+1826/−59）+ 本报告。零 commit、零 push。

---

## 逐例清偿

### 例1 ｜「图论概念梳理完成 >= 1boolean」达标线机话

- **缺失点**：
  - 引擎拼接：`backend/app/api/v1/experience_readouts.py:186`（原 `_criterion_label` 的 `f"{title} >= {threshold}{unit}"`）；
  - mobile 无兜底：`mobile/lib/features/experience/data/experience_models.dart:261-274` `_readableLine` 命中 `label` key 原样返回。
- **修法**（SPEC §6.4：整句模板 + 结构化下传 + 端侧兜底）：
  - 引擎 `_criterion_label` 重写：`unit=boolean` 走整句模板「完成「{title}」即达标」；已知数值 unit 走中文单位词映射（count→次、days→天、percent→%）；**未知 unit 不再拼接英文枚举**（只保留 `{title} ≥ {threshold}`）。
  - `_criteria_payload` 同步下传 `threshold`/`unit`/`metric` 结构化原值（additive；gateway `models.go` 中该字段为 raw `[]byte` JSON，零破坏）。
  - mobile 新建 `criterion_lexicon.dart`：`humanizeCriterionLabel()` 用正则识别存量/缓存里的旧机器拼接（含 `07:00time` 时间型），按 arb 模板重建人话；非机器格式返回 null 保持原文。接线进 `_readableLine`（模式门控，graphNodes/claims 等普通文案不受影响）。
- **测试证据**：`backend/tests/unit/test_experience_readouts_criterion_label.py` 12 项（先红后绿，含 AUDIT 原始反例与「任何 label 不得含 >=」渲染契约）；mobile `lexicon_test.dart` 例1组 4 项。

### 例2 ｜「截止： 2026-09-20 15:00:00.000」毫秒时间戳

- **缺失点**：`mobile/lib/features/memory/presentation/widgets/pending_commitments_section.dart:55` `'截止: ${c.dueAt}'`——DateTime.toString() 直出 + 硬编码中文绕过 arb 双重违规。
- **修法**：新建 `date_formatting.dart` 唯一入口——相对优先（今天/明天/昨天/±7 天内），≥7 天落绝对，禁毫秒；X8 同点 Range 折叠为单点、同日只标一次日期。`formatSceneTime`（memory 面板场景时间 Range，X8 同类直出点）与承诺截止行一并接线，文案 `displayDueLabel` 入 arb。
- **测试证据**：`lexicon_test.dart` 例2组 5 项（禁毫秒/相对桶/绝对桶/X8 折叠/同日 Range）；widget `pending_commitments_format_test.dart` 断言渲染文本无 `.000` 且含 `15:00`。

### 例3 ｜goal 状态 chip 直出「active」「normal」

- **缺失点**：`mobile/lib/features/goal/presentation/screens/goal_detail_screen.dart:249/:253` `label: data.goal.status / data.goal.priority`（semanticsLabel 同样直出）。
- **修法**：新建 `goal_status_lexicon.dart`（值域取自引擎模型列注释：goal.status `draft|active|paused|completed|archived|cancelled`、goal.priority `critical|high|normal|low`），chip label 与 semanticsLabel 均经词典；未收录枚举回退原值（零视觉与行为变化）。
- **测试证据**：`lexicon_test.dart` 例3组 4 项（zh/en 双语 + 未收录回退 null）；`goal_detail_screen_a6_l10n_test.dart` 回归通过。

### 例4 ｜memory 面板「completed …」/Q 值/状态直出

- **缺失点**：`mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart:851`（`subtitle: item.status`）、`:825`（`'Q 0.82'` 机器指标 pill）、`:747`（前瞻置信度 `0.81` 两位小数）、`:863`（episodic summary 英文事件名直出）。
- **修法**：memory 记录状态入 `goal_status_lexicon.dart`（值域：derive_status 的 `active/superseded/retracted/archived/expired/resolved/revoked` + MemoryGoal 的 `completed/cancelled/paused`）；Q 值与前瞻置信度走 `lexicon.dart` `bandLabel` §6.3 三档人话（不出百分比/小数）；新建 `memory_event_lexicon.dart` 动词词典（completed/finished/reviewed/practiced/mastered →「已完成「X」」等，未命中原样返回，不碰用户内容）。
- **测试证据**：`lexicon_test.dart` 例4组 8 项；受影响的两个既有 widget 测试按新语义更新断言（`scene_recent_summary_test.dart`：`Q 0.82`→`高质量`；`foresight_hint_display_test.dart`：`节奏 0.81`→`节奏 · 比较有把握`、`计划跟随 0.74`→`计划跟随 · 还在确认，供你参考`）。

### 例5 ｜计划名「14-Day Exam Prep」英文默认模板

- **源头核查**：**内置默认模板而非 demo 数据**——`backend/app/scenario_packs/exam_prep_14d_v1_0.json:3` 经 `goals.py:398`/`scenario_packs.py:84` 应用到用户目标，`exam_sprint_intake_service.py:598` `pack_name=manifest.name` 直接成为用户可见名。
- **修法**：manifest `name`→「14 天考试冲刺」、`description` 中文化（**两行外科手术式修改，`pack_id` 等机器标识不动**）；同文件 `_select_pack` 的两个英文保底包名 `7-Day Survival Sprint`→「7 天保底冲刺」、`Standard Exam Sprint`→「标准考试冲刺」。
- **测试证据**：`backend/tests/unit/test_scenario_pack_names_zh.py` 3 项（含「id 必须不变」反悔保护）；`tests/api/test_exam_sprint_api.py` 13 项回归通过。

### 例6 ｜goal 域硬编码绕过 arb（子集迁移）

- **修法**：`goal_detail_l10n.dart` 与 arb 双重定义并存（TRIAGE 批次 A 项）。按任务卡迁「任务状态/时间/数值呈现」直接相关子集 **14 个 getter**（Progress/Mastery/MasteryPercent/TargetDate/NoTargetDate/Overdue/Due/Status/Priority/Estimated/Minutes/Partners/Commitments/Relevance）——其中 5 个 arb 已有同义 key（直接去重），9 个新增 key；扩展体改为 `_arb.<key>` 委托（显式接收者防扩展自解析），消费者零改动、文案逐字不变。
- **测试证据**：`flutter test test/features/goal test/features/memory` 77 项全绿（含 a6 l10n 测试）。

---

## 词典 schema 落点（SPEC §6.4）

```
mobile/lib/core/display/lexicon/
  lexicon.dart               # LexiconEntry{domain,raw,label(arb 间接引用)} + Lexicon.lookup 唯一入口 + §6.3 bandLabel 三档
  goal_status_lexicon.dart   # goal.status / goal.priority / memory.record 三域
  criterion_lexicon.dart     # 旧机话达标线正则兜底 + unit 词映射
  memory_event_lexicon.dart  # 事件动词 verbTemplate
  date_formatting.dart       # 时间格式化唯一入口（相对优先/禁毫秒/X8 折叠）
```

- 词条文案全部经 **arb key 间接引用**（新增 52 key × zh/en，含 `@` placeholders 元数据），词典内零散落硬编码；`flutter gen-l10n` 已重跑，产物（git 跟踪）入 patch。
- 引擎与端侧模板对齐：引擎整句「完成「{title}」即达标」= arb `displayCriterionCompleteTemplate`。

## 测试统计

| 侧 | 文件 | 结果 |
|---|---|---|
| 引擎（新增） | test_experience_readouts_criterion_label（12）+ test_scenario_pack_names_zh（3） | 15 绿（先红后绿） |
| 引擎（回归） | test_b2_criteria_status_endpoint、test_exam_sprint_api、test_goal_strategy_services、test_memory_epistemic_contract | 26 绿 |
| mobile（新增） | lexicon_test（19）+ pending_commitments_format_test（1） | 20 绿 |
| mobile（更新） | scene_recent_summary / foresight_hint_display 断言随人话化更新 | 6 绿 |
| mobile（回归） | test/features/goal + test/features/memory 77；test/core/models + experience_repository + understanding_panel 16 | 93 绿 |

- 全量 `test/widget/` 有 33 失败 → 其中 2 个为本卡改动目标（已修），其余 31 个经 **/tmp 干净基线克隆对照**（同 fe3bc1fd + 同生成产物）确认为存量失败，与本卡无关；基线克隆已清理。
- 环境：worktree 内 `backend/.venv`（随 worktree 回收）；测试 env 进程内哑值 `SECRET_KEY`，无 .env 落盘；`mobile/lib/gen`（gitignored proto 产物）按需生成，不入 patch。

## 触达文件数

**24**（引擎 3 改 + 2 新增测试；mobile 代码 5 改 + 5 新增词典 + 测试 4 文件（2 新增 lexicon/pending_commitments + 2 更新 scene/foresight）+ arb/生成 5）。代码文件（去测试与生成产物）12 个。

## 与 wt90（S7）错开声明

未触碰任何 `taskBoard*` key（app_zh.arb:8996+ 区段）及其消费者（task_board_provider、dashboard_screen、task_board/* 等文件零改动）；arb 新增 key 均为全新命名（goalStatus*/goalPriority*/memoryRecordStatus*/display*/memoryEvent*/goalDetail* 子集），与 wt90 双 key 治理面零交集。

## 未覆盖剩余量估算（80+ 硬编码）

- `goal_detail_l10n.dart` 余 **38 条**硬编码三目 getter（本卡迁 14 条），均为交互文案（按钮/空态/snack），与状态/时间/数值呈现无关，建议下一 copy 批整体迁 arb；
- features/goal 其余硬编码中文仅 1 处（goal_detail_screen.dart:497「查看计划」）；
- `I18nService.isChinese ?` 三目模式全 app 另有 5 文件（insights/theater/tools/focus/knowledge），unresolved_conflicts/pending_commitments 同类「卡内硬编码」已顺手清 1 处；
- memory episodic `subjectType`（`:864` 副标题）与 tags（`:886-898`）本卡未动：tags 为自由文本（过滤有误伤用户内容风险），建议随 memory 域下一卡连同引擎写入侧一起词典化。

## 收工核查声明

- 删：/tmp 基线克隆已清；无 /tmp 探针残留；无模拟器/浏览器/Gradle 进程（本卡全程 LIGHT：无模拟器、无 flutter build）。
- 留：worktree 内 `backend/.venv`（随 worktree 生命周期回收）；`v3-output/B1-B/` 报告+patch（持久产物）。
- 主仓与主仓进程只读未动；无跨 worktree 树变更操作（无 stash/reset/clean）；patch 前 `git status` 已与清单比对。
