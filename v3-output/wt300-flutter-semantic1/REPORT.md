# wt300-flutter-semantic1 收工报告（A/D 线 · flutter analyze 语义类烧减一期）

日期：2026-09-22 ｜ 分支：`wt300-flutter-semantic1`（本地 commit `1a265d42`，未 push）｜ 交付：worktree 改动 + changes.patch

## 回执五要素

### ① 359 → 0（DISCARDED_FUTURES 清零）

- 基线（主仓拷 gen/ + pub get 后，基线克隆复核一致）：1014 issues = ERROR 42 / WARNING 16 / INFO 956
- 终态：652 issues = ERROR 42 / WARNING 16 / INFO 594
- 逐码 delta（基线克隆 vs 终态，全量精确比对）：
  - `DISCARDED_FUTURES` 359 → **0**
  - `CASCADE_INVOCATIONS` 309 → **306**（-3，级联拆分的副产收益）
  - `require_trailing_commas` 0 → 0（过程中曾 +83，已重排清零，见下）
  - 其余全部码目不变；ERROR/WARNING 零新增
- `dart analyze --format machine`（gate 口径）与 flutter analyze 计数一致：INFO=594

### ② 修法分类：359 = 343 包裹 + 16 级联拆分 + 0 补 await + 0 留

| 修法 | 数量 | 说明 |
|---|---|---|
| `unawaited(...)` 显式包裹 | 343 | StateNotifier 构造器初始加载、SensoryFeedbackService.emit、show*Dialog/Sheet、context.push、动画 repeat/forward/animateTo、subscription?.cancel、Future.microtask 延迟等——运行时 no-op 包装，明示 fire-and-forget 意图，零行为变化 |
| 级联拆分 + unawaited | 16 | `initState` 中 `x = AnimationController(..)..repeat()` 拆为赋值 + `unawaited(x.repeat())`（4 文件补 `import 'dart:async'`） |
| 补 await | 0 | **红线决策**：补 await 会改变执行顺序/错误传播路径，违反"不改行为"；全量按 fire-and-forget 显式化处理 |
| 留并记录 | 0 | 全部 359 处语义明确（均为既有 fire-and-forget），无拿不准的遗留 |

工具链：AST 级脚本（analyzer 14.4）定位 ExpressionStatement 精确包裹；`part of` 文件（chat_notifier_actions/reviews）依赖主库已导入的 dart:async，无需加 import。

### ③ 测试

- `community_provider_test`：3 PASS（改动最重文件，16 处）
- `community_provider_security_test`：4 PASS
- `sync_engine_test`：全跳过——**既有** IsarCore segfault 二进制问题（skip 注释在先，与本次无关）
- 均单文件单进程（`--concurrency=1`）、跑前查 swap ≥1.2G 门 + pgrep 错峰
- **未跑**：4 个改动到的 widget 测试文件（learning_path_task_path_navigation / h5_cross_system_chains / node_detail_sheet / galaxy_first_load_empty_state）——swap 被其他 worker 压到 0.9-1.0G（<1.2G HEAVY 门），按纪律不开跑；其改动与全量 343 处机械同构，结构正确性由 analyze gate（0 error）背书。**建议主会话合入窗口 swap 空闲时补跑。**
- gate：`scripts/check_flutter_analyze_gate.py` 从仓库根跑 PASS（exit 0）
- 守卫：`run_all_rule_guards.sh` **83/83 PASS**（exit 0）

### ④ 资源峰值

- swap 门测试时段：空闲 1.35G→0.87G（受舰队其他 worker 挤压，非本卡进程；本卡无 HEAVY 常驻，pgrep 全程无 flutter_tester/gradle/emulator 残留）
- load 峰值 ~7.2（<8 门）；本卡自身负载 = dart/analyzer 单进程 + 单文件 flutter test
- 磁盘：无 >1G 新增；构建产物未落仓

### ⑤ 二期建议（CASCADE_INVOCATIONS 306）

1. **形态**：306 条几乎全是 `..color=`/`..style=`/`..shader=` 绘画属性级联（paint 调制）与 controller 级联残留；真 `cascade_invocations` lint（要求链式化重复语句）占少数。
2. **建议路线**：先抽样 20 处分类——(a) paint 调制级联是地道的 Dart 惯用法且 lint 误伤面大，建议对 `paint` 局部变量模式做 lint 目标豁免或入 allowlist 永续预算；(b) 语句级 `a.b(); a.c();` 同接收者链才是真修点，可 AST 脚本化（同接收者连续 ExpressionStatement 合并为级联），预计可修 60-90 条。
3. **教训复用**：本次 reformat 因"外层语句包含内层被选语句"的区间重叠损坏过文件——二期任何 AST 改写脚本必须先做嵌套包含检测 + 纯插入优先（本卡已验证该模式）。
4. **排序建议**：二期顺序建议 `USE_BUILD_CONTEXT_SYNCHRONOUSLY`（86，需逐点语义判断 mounted/BuildContext 跨 async gap，不可脚本化）先于 CASCADE；CASCADE 的机械部分可三期脚本批修。

## 过程事故与处置（透明记录）

1. **reformat v1 嵌套区间重叠损伤 1 文件**（unified_settings_screen.dart 语言对话框：外层 show*Dialog 包裹语句 + 其 builder 内 2 条 setLocale 包裹语句同时被选，内层替换后外层旧区间覆盖位移文本）→ 发现后按纪律**单文件 git checkout 还原**，随后**全量 143 文件还原重做**（fix_discarded 纯插入流水线安全已证，reformat v2 外层改纯插入逗号、内层全替换，天然无重叠）。终态逐码 delta 与首跑一致且 0 error。
2. **主仓误触发 gate**：曾用相对路径跑守卫使主仓的 ignored 工件 `quality/flutter_analyze_report.json` 被刷新（.gitignore:234，可再生缓存，无 tracked 影响）；此后全部用绝对路径指向工作树。
3. **守卫环境修复**：AQ/BG 需 backend 生成码——从主仓 `cp -RL`（解引用，首次 `cp -R` 拷入的符号链接曾致 K/Z 路径逃逸失败，已修）拷入 `backend/app/gen`、`backend/gateway/gen`（均 gitignored，不入 commit）。

## 收工清理

- [x] `/tmp/wt300_pkg`（analyzer 脚手架）、`/tmp/wt300-base`（基线克隆）、locs/analyze 中间产物、损坏备份——删除
- [x] `mobile/build`、`.dart_tool`、独立端口进程——检查/清理
- [x] l10n：全流程未触发生成，`git status` 无 l10n 漂移，无需 checkout 还原
- [x] 主仓零 tracked 改动
