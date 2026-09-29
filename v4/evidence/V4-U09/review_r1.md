# V4-U09 独立审查 receipt（一审 R1）

- 审查者：wtU09R1（独立会话，未参与 U09 实现）
- 日期：2026-09-29
- 对象：agent/v4/u09 @ 75623a66（基线 4152266c，merge-base 与 main 核实一致）
- 工作树：审查开始与结束时均干净（M1 突变亲放后已字节级还原，`git status` 零残留）
- 卡标准：`v4/04_tasks/tasks.json` V4-U09（normal / 1 独立审查 / required_locks: ui-focus）

## 裁决：APPROVE_WITH_CONDITIONS

三条验收全部亲证成立、红线零触碰、删除完备；唯一条件级缺陷是 **run_manifest.json
对截图 PNG 的描述与像素事实不符**（F1，证据记录修正，不动代码、不阻验收）。

---

## 1. 独立复跑与亲验（可复现命令）

| 项 | 命令（cwd=wtU09/mobile 除注明外） | 结果 |
|---|---|---|
| focus 套件 | `flutter test test/features/focus/` | **+19 All tests passed**（亲跑） |
| M1 突变亲放 | 摘除 `mindfulness_provider.dart` stop() 开头 `isLoggingSession` 守卫（11 行）→ `flutter test test/features/focus/presentation/providers/u09_focus_settlement_test.dart --reporter expanded` | **+4 -1**，红面=「面2反钉：结算窗口内重入 stop()」，Actual 显示 `saveSession` 被调用 **2 次**（双结算实证）；还原后 +5 全绿，`git diff` 零残留 |
| 静态分析 | `flutter analyze --no-pub lib test` | No issues found!（亲跑） |
| l10n 守卫 | `python3 scripts/guards/check_l10n_regen_parity.py` / `check_i18n_coverage.py`（cwd=wtU09） | 10195 键 PARITY OK / i18n-coverage PASS（亲跑） |
| 抽批回归 | `flutter test test/core test/features/cognitive` | **+674 All tests passed**（亲跑；3087 全量为实现者报告，本次以抽批佐证） |
| 产物哈希 | `shasum -a 256 v4/evidence/V4-U09/screenshots/*`（cwd=wtU09） | 与 run_manifest.json `artifacts_sha256` 逐字节一致 |
| 合并落差 | `git merge-tree --write-tree 75623a66 main`（cwd=wtU09） | exit 0 无冲突；详见 §6 |

M2/M3 未亲放（按审查指令抽 M1）；二者靶点以代码读核：

- M2 靶：`mindfulness_provider.dart:299` `durationMinutes = (snapshot.elapsedSeconds / 60).floor()`
  ——唯一时长来源是实测；面1正测断言 `durationMinutes == 90 && != 25`（u09_focus_settlement_test.dart:229-234），估时顶替必红成立。
- M3 靶：`mindfulness_mode_screen.dart:210-217` `if (!result.savedLocally && result.masteryUpdates.isEmpty)` 失败分支——失败路径 error+pop+return，永不抵达成果面；砍掉该分支则 flow 测「失败不庆祝钉」（findsNothing 断言）必红成立。

## 2. 验收三条逐条裁决

**① 中断计时不假保存；估计和实际分开 — PASS**
- 中断/杀进程零写入：面1反钉（恢复会话→recordInterruption→dispose→断言 `statistics.calls` 空；重开恢复后仍零写入）亲跑绿。唯一结算入口是用户主动 `stop()`。
- 估计/实际分开：结算只收实测（:299）；用户可见面实测主行+估时注脚分列（focus_session_outcome_sheet.dart:163-173；flow 测断言「实际专注 6 分钟」+「计划 25 分钟」同屏）；成果溯源头也记实测（flow 测 3：content contains 实际 6 分钟）。

**② 切后台/重开不重置或重复结算 — PASS（持久层模拟级）**
- 不重置：面2正——SharedPreferences 快照恢复同一 `startTime` 到毫秒、elapsed 墙钟续算 600→≥600（亲跑绿）。
- 不重复结算：面2反钉并发双 stop 恰好 1 次保存（亲跑绿）+ **M1 亲放证明守卫是承重墙**（摘除→双写入→红）。
- 失败重试单结算：flow 测 4 完整生命周期（失败→快照保留→零成功写入→重开续结→重试→`successfulWrites == 1`）。
- 边界声明：杀进程=持久层模拟（SharedPreferences+新 notifier 实例），真机级归 Q07——limitations.md #1 已如实登记，采信。

**③ 无声音动效仍完整可用，失败不显示庆祝 — PASS**
- 失败零庆祝：flow 测 4 断言无成果面/无奖励摘要/error snackbar 如实/零假写入；M3 靶分支代码读核成立。
- 无声无动效完整可用：flow 测 5——系统减动效+提示音/背景声/场景全关（U14 偏好键），暂停/恢复/退出/结算/跳过全链路 + `transientCallbackCount == 0`；火苗 `context.reduceMotion` 静态支消除唯一无限循环（screen diff `_buildFlameAnimation`）。
- 接可选声音状态：`_syncAmbientOnPause` 只消费 `pauseAmbient/resumeAmbient/isAmbientEnabled` 既有 API，恢复受 U14 门控，零新音频机制（代码读核）。

**objective（成果或跳过、不强制长反思）— PASS**
- `reflection_dialog.dart` 整删（diff -214 行）；全库 grep `ReflectionDialog|reflection_dialog` 唯一残留在新 sheet 的**文档注释**（focus_session_outcome_sheet.dart:17），零代码引用；focus 域内 `barrierDismissible: false` 仅剩 exit_confirmation_dialog.dart:218（既有三重退出确认，带取消路径，非反思强制，不违卡）。
- 双一等路径：「跳过」「记录成果」同权重按钮 + barrier 可关（showSensoryDialog 默认 `barrierDismissible: true` 透传 showGeneralDialog，sensory_modals.dart:129-146）+ 留空点记录=跳过（flow 测 2 亲证零写入离开）；记录失败 sheet 保持打开、跳过恒可用（sheet 代码 104-136）。

## 3. 预登记挑战 CH-1~CH-6 逐项裁决

- **CH-1（中断 status 启发式）— 启发式对本卡充分，枚举扩展另卡**。`interruptionCount>3 → 'interrupted'` 只是**真实保存**上的状态标签（:300）；中断路径本身零写入已钉死，「中断计时不假保存」字面满足。显式终态枚举属 backend status 契约扩展（单一 owner），不在本卡范围——**建议登记新卡，非阻断**。
- **CH-2（失败即退出 vs 原地重试）— 采信保守侧**。失败 pop 避免服务端持续不可用时 PopScope 重触发 stop 的困陷 trap；快照保留+重开续结已由 flow 测 4 全周期覆盖。维持现状。
- **CH-3（顺序双会话幂等）— 现状可接受**。teardown 后 state 清空，再次 stop 必先经新 `start()`（新 startTime）→ 两条记录即两个合法会话；<1 分钟会话被 `durationMinutes > 0` 门天然不落账。entry 级 startTime 去重属 repository 可选加固，**不要求**。
- **CH-4（acted 回执时点后移）— 无移动端下游依赖，改动正确**。`reportAction` 为 fire-and-forget POST（intervention_action_service.dart:12-35，失败仅 log）；移动端 'acted' 消费面（notification_center 的 interactionState 过滤/漏斗）读的是 backend 状态，无任何代码依赖「失败也上报 acted」。与 F03 对齐属数据语义改善；backend 漏斗 `acted` 计数在失败场景将变少——**给 owner 的知会事项，非阻断**。
- **CH-5（saving 态跳过逃生门）— 逃生门已存在，无需改**。saving 态禁用的只是两个按钮（防双击重复提交）；`barrierDismissible: true` 且 sheet 无 PopScope——悬挂请求期间点空白即可离开（`?? false` 兜底=跳过语义）。裁决：维持现状。
- **CH-6（harness 强度）— 足以支撑三条验收（当前证据层级）**。u09_evidence_test 断言先于 dump（实测/估时/双按钮/结算恰一次=6 分钟），未被 harness 短路；交互闭环由 flow 测真实 tap 承载；生命周期场景 provider+widget 双层。截图问题见 F1。

## 4. 条件（conditions，合并前/集成时完成）

- **C1（F1 修正）**：run_manifest.json `screenshots_note` 声称「截图为结束面叠于专注页之上的最上层实际画面（非栈底 RepaintBoundary 复用）」。**像素复核不符**：
  - 证据：库内 PNG（SHA 90a39edc…）背景专注页完全明亮无 barrier 压暗、翻页钟「00:00」/火苗/退出按钮完整可见无遮挡；语义 dump 中 sheet 元素坐标（专注结束 y≈254-280、按钮 y≈474-491）处无对应像素。
  - 复现：`U09_EVIDENCE_DIR=<tmp> flutter test test/features/focus/presentation/screens/u09_evidence_test.dart`（探针复采与库内 PNG 同构，探针目录已删）。
  - sheet 本体的存在性由语义 dump（RenderParagraph rect）+ flow 测真实点击充分证明，**验收不受影响**；但按证据诚实规则，记录必须与现实一致：**随集成的 gen-l10n 再生补一道修正**——要么改用能含 root navigator overlay 的截图方法重采，要么把 screenshots_note 改为「PNG 为结算后底层页帧；结束面以同测 dump+flow 测为准」。
- **C2（集成复验，沿卡登记）**：合并后在集成 SHA 复跑 focus 套件（+19）+ analyze + L10N-REGEN-PARITY/i18n-coverage 守卫 + 双侧 gen-l10n 再生（本卡与 main 侧 arb 为同文件纯增量键，merge-tree 已证可自动合并、合并树含双侧键，生成 dart 需再生保证派生一致）。

## 5. 次要发现（不要求动作）

- F2：u09_focus_settlement_test.dart 面2补用例名含「重试恰好结算一次」，但函数体只断言到快照保留（:326-343）；实际重试单结算闭环由 flow 测 4 覆盖。命名精度问题，覆盖无缺口。
- F3：3087 全量为实现者报告，本次以 focus(19)+core/cognitive(674) 抽批+analyze 佐证，未全量亲跑——风险低（触碰面仅 focus+l10n 纯增量）。

## 6. 合并落差核（main 已推进至 e2c2372c，任务书所指 4d6ba401 之后又 2 个 fleet state commit）

- `git merge-tree --write-tree 75623a66 main` → exit 0，无冲突。
- 分支∩main 变更文件交集 = 5 个 l10n 文件（arb×2 + 生成 dart×3）+ tasks.json；**focus 族与 main 侧零交集**（main 侧 focus 目录零 diff）。
- 合并树上键共存验证：`git show <merged-tree>:mobile/lib/l10n/app_localizations_zh.dart | grep -c focusOutcome` = 6，main 侧新键（squadSharedError*/leaderboardSelfAnchor* 等）同在——arb 纯增量自动可并，生成文件再生归 C2。

## 7. 红线与整洁

- 触碰面核实：lib 仅 focus 三文件+reflection_dialog 删除+l10n；backend/proto/迁移/路由/RF-06 三冲突面零 diff（`git diff --name-only 4152266c..75623a66` 全量过目）。
- 无第二权威：结算走既有 focusStatisticsProvider 单链、成果走既有 cognitiveProvider.createFragment、ambient 走既有 SensoryFeedbackService。
- tasks.json 仅改 implementation_state/evidence_summary（状态权威字段按 fleet 流程留给协调侧，status 仍 PENDING，正确）。
- 审查过程零 push、零实现改动（M1 已还原，`git status` 干净）。

—— wtU09R1，2026-09-29
