# V4-G06 · 独立审查 receipt（R1，未参与实现）

- 审查对象：`b8f0119c`（代码）+ `56eb6051`（golden/证据头）；base `9369f0e5`；分支 `agent/v4/g06`，worktree `wtG06`
- 审查会话独立运行 analyze/测试/守卫/mutation；探针产物已还原，工作树结束干净

## VERDICT: PASS_WITH_CHALLENGES

十项靶全部打完。核心裁决（渐变墨色收敛）经独立复算成立；S04/Shop 红线零触碰（V4S04-ASSETS 守卫亲跑 PASS：ledger=49）；golden 86 张亲跑零漂移。但：**交付 SHA 上 DL-SPEC 治理守卫红（新增回归，交付未记录）**——合并门，须闭后推进集成 SHA；另有两项中等发现登记。

---

## 发现列表

### F-3 · HIGH（合并门）｜新增治理守卫回归未记录：DL-SPEC ratchet 在交付 SHA 上 FAIL
- **位置**：`mobile/lib/features/achievement/presentation/screens/achievement_contract_screen.dart:705,726,736,943`
- **复现**：`python3 scripts/guards/check_dl_spec_ratchet.py` → exit **1**：`achievement_contract_screen.dart: persistentRepeatLoop 4 > baseline 3 (+1)`
- **实证**：base 该文件 `.repeat(` 计数 3（=基线 3，绿）；交付后 4。G06 的 reduce-motion 等价改造把 `_glowController.repeat(reverse: true)` 启动点拆到 initState/_updateMotionPreference/didUpdateWidget 三处（+pulse 一处），守卫按调用点计数 → 3→4。该文件不在 `PERSISTENT_REPEAT_WHITELIST`。守卫在 `scripts/rule_guard_manifest.tsv:76`（DL-SPEC，提交前套件）。
- **结论**：运行时行为正确（全部循环已按 reduce-motion 启停），但这是本卡 diff 引入的新增守卫回归，`run_manifest.json` 命令清单无任何守卫运行、`limitations.md` 未登记。按 AGENTS.md 守卫纪律（"区分既有失败和新增回归"、"治理守卫（提交前）"）须闭账：收敛为单一启动点 helper，或按 N3 白名单登记理由，或合法降计数后 `--update-baseline`；不得无登记带红推进。
- **旁证**：全量守卫套件 `run_all_rule_guards.sh` exit 1，失败=AQ/BG/DL-SPEC 三项；AQ（`No module named 'app.gen'`）与 BG（生成 pb.go/pb2.py 缺失）为 `backend/app/gen/`（.gitignore:246）未生成的环境性既有失败，与本卡 diff 无关（本卡零 backend/生成物触碰），不计入本卡。

### F-1 · MEDIUM｜E- 控制组"classic-light 旧配对"用错调色板（结论侥幸成立，钉子钉错对象）
- **位置**：`mobile/test/widget/v4_g06_family_contrast_guard_test.dart:130-163`（配对常量）；`v4/evidence/V4-G06/limitations.md` 挑战①、`diff_or_evidence_only.md` B6（数字口径）
- **实证**（独立复算脚本，WCAG 2.x 同式）：
  - 钉住的三对：gold×`#8B4500`→2.949、purple×`#56B4E9`→4.498、coral×`#0072B2`→4.050。其中 `#8B4500` 是 **highContrast-light** 的 semanticWarning、`#56B4E9`/`#0072B2` 是 **colorBlindFriendly-light** 的 brandSecondary/semanticInfo——**无一来自默认 classic-light 调色板**（theme_manager.dart:576-582：`#7D5C26`/`#7A8BA6`/`#48678D`），而同守卫 `_allProfiles['classic-light'] = SparkleColors.light()` 自我声明即为默认板。证据数字 2.95/4.499 与合成对吻合；"4.02" 与任何一对都不精确吻合（其实际值 4.050）。
  - **真实 classic-light 旧配对**独立复算：3.431 / 4.498 / 3.600——同样全部 <4.5，"无公共墨色"结论对真实默认板**仍然成立**（epic 4.498 贴线但确实不达标）。
- **结论**：B6 裁决（收敛固定身份双端）在正确口径下成立，维持有效；但 E- 钉按现写法没有钉住它声称钉的旧运行时配对，证据数字需勘误。整改：E- 三对改用 `SparkleColors.light()` 默认值（或直接引用 `_allProfiles['classic-light']`），并登记修正后的 3.43/4.50/3.60。

### F-2 · MEDIUM｜地图 B1–B3 修复无实现级回归保护（mutation 存活实证）
- **复现**（mutation M-B）：`achievement_map_screen.dart` 状态 chip 回退 `DS.textSecondary`→`Colors.white70` 后亲跑 `v4_g06_family_contrast_guard_test.dart + test/goldens/g06_four_style/ + test/features/achievement --concurrency=1` → **+28 All tests passed!**（全绿，mutation 存活）。
- **结论**：守卫为 token 数学复算（自算 textSecondary×面板模型），不泵产品屏；地图屏不在任何 golden（8 张=徽章/火堆/自我锚/弹窗）。B1（chip）/B2（lock+描边）/B3（虚线）以及同构造的 B9（streak 格墨）、A10（hub）、A11（光子横幅）的实现接线均无 mutation 敏感钉——产品侧回退将静默回归。守卫头注"钉住的都是本家族修过的真实缺陷配对"在**配对层**为真，**实现层**不成立，表述需收窄。整改建议：地图详情面板/锁定节点纳入一枚四风格 golden，或守卫改泵真实 widget 取色。

### 小项（不判罚，登记备查）
- N1：引用口径 "DESIGN_SYSTEM 1.3.1 禁透明度压文字" 在 `v4/02_design/DESIGN_SYSTEM.md` 无对应编号条目（实质规则由 ACCESSIBILITY_ASSETS ≥4.5:1 承载）——引用失准，三处清除本身已 diff 实证。
- N2：证据引 legendary "深墨 7.6/8.9"——实测 7.567 / 10.12（浅珊瑚端实际更优），第二值不精确，方向保守无害。
- N3：守卫地图面板模型未按其自述 G02 口径对 0.82 alpha 合成；按实际浅档画布合成后仍 ≥4.5（模型 4.90），方向安全。
- N4：A13 阴影 `0x22`（13.33%）→ `alpha: 0.13`，"等值"差 ~0.3pp，非实质。
- N5：弹窗内残余透明度文字：chip 区 0.88（墨按 chip 底实算，合成后 ≥4.5）、combo 横幅 `onBrandPrimary.withValues(alpha: 0.7)`（既有未动）——Q08/后续卡可一并裁决。

## 十靶核验记录（全部亲验）

1. **续跑完整性**：A1–A13 diff 在位（抽查 A1/A2/A3/A8/A12/A13 逐处）；10 个用 `context.reduceMotion` 文件均含 `sparkle_context_extension` 导入（A14 补完）；`flutter analyze --no-pub` 亲跑 **No issues found!（20.2s）**；theme_utils B10 纯新增不改既有签名。
2. **渐变墨色裁决（最重）**：亲复算（/tmp 独立 Dart 脚本，已删）：钉住对 2.949/4.498/4.050；真实默认板旧配对 3.431/4.498/3.600（同样无公共墨色）；新固定双端 **8.313/4.669/7.567 全部 ≥4.5**（epic 4.669=白墨、rare 8.313/legendary 7.567=深墨，与代码注释一致）。**裁决正确**：失败是同档内渐变两端跨墨色 crossover，"随档双墨"数学上不可救（每档内部即无单墨解）；"描边补偿"属美术方向改动应归 Q08；身份色为 `static const` 档不变量，固定双端跨四档成立。Q08 预登记（美术终裁）正当——本卡只按可读性下限收敛，未擅定美术。E- 钉错色问题见 F-1。
3. **地图 4 处固定白**：chip→`DS.textSecondary`、lock→`DS.textTertiary` 实心、描边→`DS.borderSubtle`、虚线→painter 新增 `lockedLineColor` 入参且两处调用点均传 `DS.border`——单一绘制权威，无第二实现。
4. **守卫真实性**：11/11 亲跑通过（exit 0），3 组 E- 判负在位；抽算 5 对：rare 旧图标 `#B8860B`×`#F4F1EB`=**2.887**（与"2.89"吻合）→修后 `onColor(neutral0)` 深墨 18.6；渐变三对见靶 2；streak weak 格（success×warning 中间色）白墨 **6.11**、active 5.83、frozen 6.12；地图 chip 4.90。
5. **透明度×3**：解锁文本 0.8、解锁时间 0.6、里程碑描述 0.8 三处 `withValues` 均除、留注——diff 逐处确认（引用编号失准见 N1）。
6. **S04/Shop 红线**：`git diff 9369f0e5..56eb6051 --name-status` 全 30 文件，`mobile/assets` 0、`mobile/lib/features/shop` 0、backend 0；diff 内 shop/asset 命中均为注释/证据文本；V4S04-ASSETS 守卫亲跑 **PASS（ledger=49 approved=38 proposed=11）**；streak_details:107-108 Shop CTA 维持 V3-FIX-05 移除态+RELEASE_ENABLE_SHOP 兜底注释未动。
7. **mutation**：M-A（legendary 第二端回退 `DS.info`）→ g06 golden **红**（`+1 -1: Some tests failed`，探针有效）；M-B 见 F-2（存活=发现）。mutation 数 2，其中 1 个暴露保护缺口。
8. **golden**：`test/goldens` 亲跑 **+86 ~15 All tests passed!（exit 0）** 零漂移（含 8 张新 golden，SHA 清单 10/10 逐字节的合）；B04 比较器 0.005 分数带界实证（b04_harness.dart:143）；tofu 口径成立：golden 钉布局/色彩形态，可读性由同源语义钉（徽章标签非空/账本数字直出/按钮语义可达）+对比度守卫承载，`disableAnimations=true` 泵制同时钉 reduce-motion 等价形态。
9. **回归抽半**：`test/features/community + test/features/photon + test/core/design` **+415 绿**；touched-family widget 7 文件 **+45 绿**（含 h9/u12/u15）；U15 棘轮绿。family 另一半（achievement）在 M-B 探针中 +15 绿。全绿口径与 test_results.json 一致。
10. **挑战② milestone 6 枚冷相**：`scripts/guards/dl_spec_ratchet_baseline.json` 实证 `coldColorLiteral: 6`（only-lower，注释明令 never raise）；里程碑屏豁免注释+`play: !context.reduceMotion`+stat chip `minWidth:150/maxWidth:320` 在位。**但同一守卫在 contract 屏 persistentRepeatLoop 维度红（F-3）**——豁免口径本身核实无误，守卫套件整体状态不绿。

## 命令与 exit code 清单（审查会话亲跑）

| 命令 | exit | 结果 |
|---|---|---|
| `flutter analyze --no-pub` | 0 | No issues found! (20.2s) |
| `flutter test test/widget/v4_g06_family_contrast_guard_test.dart --concurrency=1` | 0 | +11 全绿 |
| `flutter test test/goldens --concurrency=1` | 0 | +86 ~15 全绿（零漂移） |
| `flutter test test/features/community test/features/photon test/core/design --concurrency=1` | 0 | +415 全绿 |
| touched-family widget 7 文件 `--concurrency=1` | 0 | +45 全绿 |
| `flutter test test/widget/u15_longtail_closure_guard_test.dart --concurrency=1` | 0 | +14 全绿（48 基线棘轮在位） |
| mutation M-A 后 `flutter test test/goldens/g06_four_style/ --concurrency=1` | 红（输出 +1 -1 Some tests failed） | 探针有效 |
| mutation M-B 后（guard+goldens+achievement `--concurrency=1`） | 0 | +28 全绿 → **F-2 存活实证** |
| `python3 scripts/guards/check_dl_spec_ratchet.py` | **1** | **FAIL contract 屏 4>3 → F-3** |
| `bash scripts/run_all_rule_guards.sh` | 1 | AQ/BG/DL-SPEC 失败（AQ/BG 环境性既有；DL-SPEC 新增→F-3）；V4S04-ASSETS PASS |
| 独立对比度复算脚本（纯 Dart WCAG） | 0 | 数值见靶 2/4 |
| `shasum -a 256` artifacts_sha256.txt 对账 | 0 | 10/10 一致 |

资源纪律：全部 `--concurrency=1`；磁盘 32G available（>15G 红线）；mutation 产物已 `git checkout --` 还原，守卫探针产物（v3-output/WT401-Q03-VISUAL ×4）已还原，结束树干净。

## receipt
- 审查会话：R1（未参与 G06 实现）；本文件为唯一追加提交内容。
- 整改归属：F-3 由 G06 责任会话闭账（守卫绿或白名单登记后重签证据头）；F-1/F-2 可随闭账一并修正或开后续小卡。
