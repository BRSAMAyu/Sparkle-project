# WT350 质量尾账三件 — 交付报告

- 分支：`wt350-quality-tail`（base = main @ b280d38a）
- 代码 commit：`c066a4cb`（16 files, +12/-70）
- 结论：**READY_FOR_REVIEW**（定向 flutter test 按内存门 DEFERRED，无回归面，详见 §5）

## 1. l10n 旧键收割（wt329 遗留）

- 键：`taskBoardTodaySummary`、`taskBoardNoTasksToday`（wt329 修 F-9 时弃用、暂留回滚余地）。
- 零引用确认：grep `mobile/lib/` 与 `mobile/test/` 全树，除 arb 文件与 l10n 生成文件外零命中。
- 动作：`app_en.arb` / `app_zh.arb` 各删 2 键 + `@taskBoardTodaySummary` 元数据块（含 placeholders），两文件 JSON 合法性 python 校验通过；随后 `flutter gen-l10n` 实跑 exit 0 验证 arb 与生成器契约无断裂。

## 2. 生成文件同步与卫生检查（wt339 坑复盘）

- 实跑 `flutter gen-l10n` 后 diff 发现：本机 Flutter 3.41.3 的生成产物相对提交态存在**全量格式重排噪声**（参数列表折叠、构造器缩进等，~430 行）——即 wt339 发现的坑，提交态基线（wt329 落库）是另一种格式。
- 处置：生成文件回退到 HEAD，按卡面卫生条款做**外科手术式编辑**——三个生成文件（`app_localizations.dart` / `_en.dart` / `_zh.dart`）只删除两键对应成员，格式忠于提交态基线。
- 卫生验证：`git diff` 全量人工核读，生成文件 diff **只含两键变更**（52 行纯删除，恰为 wt329 同一文件 +52 纯插入的镜像）；`flutter analyze` E=0 证明编辑后类编译完整（漏删/错删必产生编译错）。
- 无 CI 冲突面：CI（FLUTTER_VERSION=3.41.3）不跑 gen-l10n diff 守卫，rule_guard_manifest.tsv 亦无 l10n 一致性守卫；arb 是单一事实源，语义一致性已由 gen-l10n 实跑互证。

## 3. analyze INFO 烧减：598 → 587（烧减 11，预算 ≤594）

门禁：`python3 scripts/check_flutter_analyze_gate.py` → **ERROR=0 / WARNING=15 / INFO=587**（修复前基线实测 E0/W15/I598），E/W 零上升，gate passed。info_code_budgets 全部 ≤ 预算（未动 allowlist 文件，避免挤压其他在航 worker 的 598 基线树）。

### 已修（11 条，逐条记录）

| # | lint | 文件 | 修法 |
|---|------|------|------|
| 1-4 | EOL_AT_END_OF_FILE | community: group_files_screen / group_list_screen / group_search_screen / partners_tab | 文件无末行换行，补 1 个 `\n` |
| 5 | EOL_AT_END_OF_FILE | memory/memory_panel_screen | 去末尾空行 |
| 6-7 | EOL_AT_END_OF_FILE | shop: consumable_provider / skin_provider | 去末尾空行 |
| 8 | EOL_AT_END_OF_FILE | vocabulary/local_vocabulary_provider | 去末尾 2 空行 |
| 9 | EOL_AT_END_OF_FILE | shared/models/api_response_model | 补末行换行 |
| 10 | EOL_AT_END_OF_FILE | test/widget/memory_panel_screen_test | 去末尾空行 |
| 11 | DANGLING_LIBRARY_DOC_COMMENTS | test/interactive_intent_test.dart | shebang 后 `///` 块悬空（不附着任何声明），转 `//` 普通注释 |

**实证发现（探针验证）**：本版 analyzer 的 `EOL_AT_END_OF_FILE` 对「缺末行换行」与「末尾多空行」（`\n\n` 结尾）都报 lint——包内探针 `}\n`→不报、`}\n\n`→报。修复脚本按 `s/\n*\z/\n/` 归一。

### 放弃项（拿不准/受限，逐条记录）

- `PREFER_CONST_LITERALS_TO_CREATE_IMMUTABLES`（action_proposal_dual_mount_test.dart:53）：代码有先行 worker 注释「非 const：proposalPayload 已含 'status'，const 下重复键为编译错误」，const 化会破坏编译，语义受限放弃。
- `EOL_AT_END_OF_FILE`×2 与 `REQUIRE_TRAILING_COMMAS`×1（chat 路径：memory_reference_receipt / audio_recording_service）：卡面 Forbidden chat 业务路径，不碰。
- `NO_LEADING_UNDERSCORES_FOR_LOCAL_IDENTIFIERS`（chat_area_budget_test.dart）：chat 命名测试避嫌不碰。
- `USE_BUILD_CONTEXT_SYNCHRONOUSLY`（86 处）：每处需语义判断 async gap，非纯机械，单批风险收益比差，本轮不动。

## 4. 收工验证

| 项 | 结果 |
|---|---|
| 规则守卫 | `bash scripts/run_all_rule_guards.sh` → all 83 rules passed，exit 0 |
| flutter analyze | E0 / W15 / I587 ≤ 594（容差 5），gate passed |
| mypy 棘轮 | backend 零改动（`git status backend/` 空），冷 mypy 按构造=基线 1278，不推高（quality/mypy_baseline.txt = 1278） |
| 定向 flutter test | **DEFERRED**：swap free 647M < 1.2G 门（开工/收工两次实测 615M/647M）。l10n 两键在 lib/ 与 test/ 均零引用，无测试回归面；analyze E0 证明编译完整 |

## 5. Forbidden 遵守

- l10n 只删死键，零键值内容改动（diff 全为删除行）。
- 未碰 chat/galaxy/home 业务逻辑（16 个变更文件逐一核对，均非三特性产品代码）。
- 零新增依赖（pubspec.yaml 未动）。

## 6. 变更清单（16 files, +12/-70）

arb ×2（删键）、l10n 生成 ×3（外科手术同步）、EOL 归一 ×10、doc comment ×1。patch 见同目录 `changes.patch`（264 行）。
