# WT702-TOLFIX · V3-FIX-383 收口笔记（2026-09-27）

- 分支：`agent/node-b/wt702/tolfix`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt702-tolfix`，base = main tip e2c3fa5b）
- 修复 commit：`8120869d`；台账 commit：见本目录所在分支末笔
- 任务卡：V3-FIX-383（wt692 登记）——`B04TolerantGoldenComparator` 容差单位错位：`diffPercentTolerance = 0.5` 与 `ComparisonResult.diffPercent`（**分数**，pixelDiffCount/totalPixels ∈ [0,1]）直比 = 实际 50% 容差，注释意图 0.5% 落空，B-04 视觉回归门近乎失效

## 1. 修复 diff（commit 8120869d，4 文件 +210/−5）

| 文件 | 改动 |
|---|---|
| `mobile/test/goldens/b04_visual_baseline/b04_harness.dart` | 常量 `diffPercentTolerance` 0.5 → **0.005**（分数口径 0.5%）；类注释新增「单位口径（V3-FIX-383 钉死）」段：diffPercent 是分数、SDK _goldens_io.dart:254 实证、0.005=0.5%、带界含等号、对照 golden_family_drift_guard 先例；比较逻辑本体零改动 |
| `mobile/test/goldens/b04_visual_baseline/b04_tolerant_comparator_test.dart` | 新增带界单测 6 例（见 §2） |
| `mobile/test/goldens/golden_family_drift_guard.dart` | 注释同步：V3-FIX-383「已登记归 wt667 在航面处置」→「已由 wt702 修复（常量改 0.005，与本带同值）」 |
| `mobile/test/goldens/golden_family_drift_guard_test.dart` | 注释同步（同上） |

SDK 依据（本机 Flutter 3.41.3 实读 `/opt/homebrew/share/flutter/packages/flutter_test/lib/src/_goldens_io.dart`）：

```dart
253:  if (pixelDiffCount > 0) {
254:    final double diffPercent = pixelDiffCount / totalPixels;
```

失败消息为 `(diffPercent * 100).toStringAsFixed(2)%`（百分数口径），单测对失败消息的 `0.60%`/`49.00%` 断言钉死分数↔百分比换算。

## 2. 带界单测（b04_tolerant_comparator_test.dart，6/6 绿）

测法：纯图像构造——`PictureRecorder` 白底 200×150（=30000px 总面）+ 确定性摆放 N 个红像素 → PNG；golden 落 `Directory.systemTemp` 临时目录（测后即删），**不经、不触碰仓库内任何基线 PNG**。判挂路径在 `runAsync` 回调体内 try/catch 收集 `FlutterError`（本 SDK `runAsync` 吞错返 null 并 reportError，binding.dart:2719 实证）。

| 用例 | diff 像素 | diffPercent | 修后（0.005） | 旧常量（0.5）下 |
|---|---|---|---|---|
| 常量钉死：=0.005 且 ==kGoldenEnvDriftBand | — | — | 绿 | **红** |
| 0 差 → passed 直通 | 0 | 0.0 | 绿 | 绿 |
| 0.4% 带内 | 120 | 0.004 | 绿 | 绿 |
| 0.5% 带界含等号 | 150 | 0.005 | 绿 | 绿 |
| 0.6% 超带 | 180 | 0.006 | 挂（FlutterError，消息含 0.60%） | 绿（假） |
| 49% 布局崩坏量级 | 14700 | 0.49 | 挂（FlutterError，消息含 49.00%） | 绿（假） |

变异验红（临时把常量改回 0.5 跑同单测）：`00:00 +3 -3: Some tests failed`——恰为常量钉死 + 0.6% + 49% 三例红，证单测对回归真有门作用；随后恢复 0.005（git diff 复核仅预期 +12/−1）。

## 3. goldens 全量前后对比（`flutter test test/goldens/`）

| 时点 | 结果 |
|---|---|
| 修前（worktree 原样 = main 的 0.5 常量） | `00:16 +78 ~15: All tests passed!`（78 过 15 skip 0 红，复现 wt692 记录） |
| 修后（0.005 + 6 新单测） | `00:15 +84 ~15: All tests passed!`（84 过 15 skip 0 红；+6 新单测，**零新红**） |

默认跑 capture 门关（`B04_VISUAL_CAPTURE` 未设时 b04 只跑布局探针不比对 PNG；dashboard golden 走 dart-define 门 = 15 skip 之一部分），故比较器行为变化不触默认面——真实回归面见 §4 verify 模式。

`flutter analyze`：`No issues found!`（修前修后各跑一次，收口前复跑 6.0s 仍零 issue）。

## 4. 新红分诊（b04 verify 模式实测，唯一能触达比较器的面）

命令形制：`B04_VISUAL_CAPTURE=true flutter test --dart-define=B04_BUILD_SHA8=<sha8> test/goldens/b04_visual_baseline/b04_visual_baseline_capture_test.dart`（不写盘，纯比对；sha8 是 `String.fromEnvironment` 编译期常量，shell env 传不进，首次尝试用环境变量传入失败=27 张全 missing-file 挂，改 `--dart-define` 后正常）。

基线锚事实（亲点清单）：27 张中 26 张锚 `87b5f432`，唯 `android home__main` 锚 `e0777bd5`（= c69f55b7 单面重采，台账 FIX-376 行在案「macos 批 home 面仍锚 87b5f432 待下轮全量重采，本批只采 android 权威文字面」）。

| # | 面 | 修前 verify（0.5） | 修后 verify（0.005） | 分诊结论 |
|---|---|---|---|---|
| A | android home__main @87b5f432 | 挂（missing-file） | 挂（missing-file，**不变**） | 混锚清单缺陷，非渲染差：该张只存在于 e0777bd5 锚；缺失路径不经容差比较器，修前修后同挂。用 e0777bd5 单独跑 home 面（--plain-name）则 android home **过**（内容未漂移）。→ 混锚运行缺陷登记 **V3-FIX-395**；重采本体归 FIX-376 既定挂账，不重复登记 |
| B | macos 1280x800 home__main @87b5f432 | **过（假绿）** | 挂：`Pixel test failed, 15.24%, 624197px diff detected` | 真实布局/内容差 = home 首屏经 V3-FIX-376 重做（UnderstandingSnapshotCard demo 门控/回执卡改版），87b5f432 基线先于重做；15.24% 为带宽（0.5%）30 倍、本机环境漂移签名（0.18%）85 倍，非环境噪声；同 surface 在 800x600 批带内过、android 重采批过，指向 1280 宽视口可见的面变化。**处置：不在本卡硬修 UI、不动基线 PNG、不放宽容差；重采按 FIX-376 既定挂账（签发机下轮全量重采）执行**。此例即 383 真实影响的活证：修前 50% 容差把它吞成假绿 |

verify 模式总分：修前 `+26 -1` → 修后 `+25 -2`（唯一新红 = B）。其余 25 张（含 macos 800x600 全批、android 除 home 外全批）修后在 0.5% 带内全过，说明 B-04 基线集在本机除 home 面外健康。

## 5. 台账与合规

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-383 OPEN → **FIXED@8120869d**（全证据面入行）；新登 **V3-FIX-395**（B-04 verify 混锚运行缺陷，重采本体归 FIX-376）
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → `verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`（exit 0；293 行 V3-FIX 行，383/395 均 7 列）
- 铁律合规：基线 PNG 零触碰（修前修后 verify 跑后 `git status -- v3-output/B-04/` 恒空）；不放宽容差、不改比较逻辑迁就失败；未 push；gen 按 wt369/wt374/wt675 先例主仓 `cp -RL` 不入库；测试运行对 `mobile/lib/l10n/`（本机 gen-l10n 重排副作用）与 `v3-output/WT401-Q03-VISUAL/*_probe_*.json`（探针报告）的写面已 `git checkout --` 还原，不入库
