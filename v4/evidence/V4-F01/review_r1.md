# V4-F01 独立审查 receipt（R1）

- 审查会话：wtF01R1（未参与 F01 实现）· 2026-09-28
- 审查对象：分支 `agent/v4/f01` @ `ecf60098`（基线 `4d26cdd1` = Sparkle-project main HEAD，实况 `git log` 核验一致）
- 审查方式：只读 diff 全量扫描 + 亲算 WCAG 对比度 + 亲跑测试/守卫 + 两轮受控变异（改后即 `git checkout` 还原，工作树零残留）
- **总裁决：PASS（一审通过）**——CHALLENGED 2 项均非阻断（引语归源、测试命名口径），不触及卡面任何验收项；1 项守护范围注记属审查增补发现。合并后照常走集成 SHA 复验。

## 1. 逐项核验记录（本审实跑命令与结果）

### 1.1 红线核验（最重）

| # | 声称 | 审核查证（命令/方法/结果） | 结果 |
|---|---|---|---|
| 1 | classic=off 时 41 颜色槽逐槽零差（浅/深两态断言在库） | `pixel_preview_theme_test.dart` `colorSignature()` 逐数 = **41 槽**（SparkleColors 构造器 42 参 − brightness），浅/深两态各一断言（对 `SparkleColors.light()/dark()` 全 map 等值）；`flutter test test/core/design/pixel_preview_theme_test.dart` 亲跑 **30/30 passed**（含该两断言） | **CONFIRMED**（守护范围见 §3 注记 N1） |
| 2 | 零差量断言可失败 | 受控变异一：`SparkleColors.light()` 工厂值 `F8F4EF→F8F4EE` → 断言仍过（两侧同源工厂，**tautology 实证**）；受控变异二：classic 路径注入 `brightness==light → pixelPreviewThemeData(paperDay)` 通道泄漏 → 断言**立即失败**（line 108，`+0 -1 Some tests failed`）。两轮变异后均 `git checkout` 还原，`git status` 干净 | **CONFIRMED**（断言真实可失败，守护对象是通道不是工厂值） |
| 3 | `setPixelPreviewProfile` 只影响 preview 通道 | 代码审：方法体只写 `_pixelPreviewProfile` + `_saveToPrefs` + notify，不触碰 mode/brand/skin/highContrast；`themeForBrightness` preview 分支置于头部，classic（默认 0 档）短路走既有路径（theme_manager.dart +45/−0 纯增）；测试：dusk→classic 往返回退逐槽复原（before/after 全 signature 等值）、持久化 + reset 归零断言在库且亲跑 | **CONFIRMED** |
| 4 | 五 Tab 路由/生成文件/经典主题路径零触碰 | `git diff --name-status 4d26cdd1..ecf60098` 全量 = 10 文件：4 个 mobile 设计核心文件 + tasks.json（状态字段 4 行）+ 5 个 evidence 文件；`grep -iE "rout|shell|gen/|\.g\.dart|l10n"` 零命中；theme_manager classic 段零删除（+45/−0）；design_system −14 行全部是本卡自己声明的替换点（onPrimary/onSecondary/onError ×3 行 + 两处 `_buildThemeData` brightness 实参） | **CONFIRMED** |
| 5 | preview 消费面收敛 | `grep -rn pixelPreview|PixelProfile mobile/lib` 仅命中 3 个设计核心文件（pixel_preview_theme.dart / theme_manager.dart / design_system.dart 导出与挂载点）；无任何 feature/路由旁路读取 | **CONFIRMED** |

### 1.2 无第二套令牌

| # | 声称 | 审核查证 | 结果 |
|---|---|---|---|
| 6 | 三 profile 经 SparkleColors/SparkleThemeData 唯一运行时真源 | `pixelPreviewColors()` 返回 `SparkleColors`、`pixelPreviewThemeData()` 返回 `SparkleThemeData`（typography=SparkleTypography.standard、spacing=SparkleSpacing、animations=SparkleAnimations 恒等复用）；测试断言 `theme isA<SparkleThemeData>` + typography 恒等 + DS 静态层与 pixelPreviewColors 同值，均在库且亲跑 | **CONFIRMED** |
| 7 | 仅 4 个点名新增字段走 ThemeExtension | `PixelProfileTheme` 字段恰为 `pixelStep`/`cornerCut`/`accentInk`/`stateMotion`（+profile 标识），与 `v4/02_design/DESIGN_SYSTEM.md` 头部「再增加极少数字段（pixelStep、cornerCut、accentInk、stateMotion）。不引入第三套品牌色/第二套字阶」逐字吻合；扩展仅 preview 开启时挂载（classic `extension<PixelProfileTheme>()` 为 null 有断言）；`spacing_dp`/`type_roles` 未动（spacing/typography 全复用既有类） | **CONFIRMED** |
| 8 | 色板转抄保真 | `v4/02_design/TOKENS.proposal.json`（status=PROPOSED_NOT_APPROVED）13 槽 × 3 档逐值比对 `_pd*`/`_dusk*`/`_quiet*` 常量：**39/39 全部精确**；`pixel_step_dp=2`、`corner_cut_dp=[4,8,12]`、`motion_ms=80/160/220/650` 与扩展默认值一致；派生槽（textDisabled/planning/ocr/中性阶梯/柔紫）逐一注明 lerp 公式 | **CONFIRMED** |
| 9 | PROPOSED 状态不因实现漂移 | TOKENS.proposal.json 未被本卡触碰（不在 diff）；文件头/注释全量标注 PROPOSED；limitations §3 明示色板批准归设计侧与 HUMAN_INBOX | **CONFIRMED** |

### 1.3 对比度声明亲算抽验（非只看测试绿）

本审独立实现 WCAG 2.x 相对亮度公式（sRGB 线性化 → 0.2126/0.7152/0.0722 → (L1+0.05)/(L2+0.05)），对**全部 3 档 × 10 文本角色 × 3 容器面 = 90 对**亲算（不止抽 2 角色）：

- 90/90 ≥ 4.5:1，最弱对 = paperDay textSecondary on tertiary = **4.80:1**（dusk 最弱 5.32，quiet 最弱 5.57）——与测试断言口径（同标准公式）一致；
- border 槽 ≥3:1（图形线）：paperDay **4.21**（neutral300=line `68766A` on canvas）、dusk **6.90**（neutral600=line `9DAF9F` on surface）、quiet **4.79**——全过，口径 = `SparkleColors.border` 派生 getter（dark→neutral600/light→neutral300），非新增槽；
- 抽验角色点算：paperDay textSecondary `58665C` on `E9E5D8` = 4.80、dusk semanticWarning `E2BF89` on `24322B` = 9.17、quiet taskReflection `64558A` on `ECECE5` = 5.52；
- 头部声明核对：柔紫 `#64558A` 全浅色容器面最弱 **5.19:1**、`#BCAED4` dusk 容器面最弱 **4.58:1**——与源码注释「≥5.19:1 / ≥4.58:1」逐字吻合；
- onPrimary/onError 实路径（AppThemes→colorScheme）断言在库且亲跑（30 用例内）。

### 1.4 顺手修的 2 缺陷——classic 恒等性

| # | 修复 | 审核查证 | 结果 |
|---|---|---|---|
| 10 | dusk 亮 accent `getContrastSafeText` 两侧 <4.5 | 亲算实证修复动机：`B9D5B5` vs white = **1.59:1**、vs ink `F5F0E3` = **1.39:1**，两侧均 <4.5，原公式必回退白字（1.59:1 不达 AA）——缺陷真实。classic 恒等性：`pixelAccentInk` 仅在 `pixelPreviewEnabled` 时非 null，classic 走 `?? ` 右侧原表达式（逐字保留），`ThemeUtils.getContrastSafeText` 本体零改动 | **CONFIRMED** |
| 11 | AppThemes brightness 取 `theme.colors.brightness` | classic 恒等性：`SparkleColors.light()/dark()` 六个工厂变体（normal/highContrast/CB-friendly × 浅深）全部显式设 `brightness: Brightness.light/dark`，与入口实参恒等；brand preset 与商城皮肤走 `copyWith` 保留 brightness。preview 收益：dusk 档两入口输出暗色（测试「dusk 下 light/dark 入口都出暮色」亲跑过） | **CONFIRMED** |

### 1.5 复跑（全部本审亲跑，数字与 run_manifest.json 逐项对表）

| 命令 | 本审结果 | manifest 声称 | 对表 |
|---|---|---|---|
| `flutter test test/core/design/pixel_preview_theme_test.dart` | **+30 All passed** | 30/30 | 一致 |
| `flutter test test/core/design test/unit` | **+408 ~1 All passed**（~1 = 既有 tearDownAll 残记） | +408 ~1 | 一致 |
| `flutter test test/app test/widget/chat_design_system_dark_mode_test.dart test/widget/a11y_semantic_labels_test.dart test/widget_test.dart` | **+47 ~1 All passed** | +47 ~1 | 一致 |
| `flutter analyze`（4 触碰文件） | No issues found | No issues found | 一致 |
| `check_ui_design_tokens_ratchet.py` | PASS color=225/275, fontSize=634/727 (184 files) | 同 | 逐字一致 |
| `check_dl_spec_ratchet.py` | PASS 15 维（coldColorLiteral=87/90 等） | 同 | 逐字一致 |
| `check_typography_rhythm_ratchet.py` | PASS sub12=232/234, w800=0/0, w900=6/6 | 同 | 逐字一致 |
| `check_spacing_rhythm_ratchet.py` | PASS spacingHalfStep=1591/1623 (321 files) | 同 | 一致 |
| toolchain | Flutter 3.41.3 stable rev 48c32af034 / darwin 25.6.0 arm64 | 同 | 一致 |

### 1.6 NOT_RUN 如实性与 HEAVY 划界

| # | 项 | 审核查证 | 结果 |
|---|---|---|---|
| 12 | 截图/设备面 NOT_RUN | limitations §1 明记 flutter_tester `toImage/toByteData` 软渲染挂起三试（每用例 ~10 分钟人工终止、flags 在案、临时采集文件未入库）；evidence 目录无 PNG 冒充、`git status` 无未 track 残留；diff_or_evidence_only.md 与验收对照表无一处「视觉已验证」表述（可读性全部落在「自动测/组件级 widget 测试」口径）；review_receipt.json=PENDING + honest_note 不自称完成 | **CONFIRMED**（引语归源勘误见 C1） |
| 13 | HEAVY 面归 F05 划界 | V4-F05 卡实测：HEAVY=True、五面（首页/卡住 sheet/记忆/长回答/星图）+ 三 profile 切换 + 同一状态流、锁 style-preview——与 F01 limitations §1/§4 的让渡表述逐项吻合，无越权代跑 | **CONFIRMED** |

### 1.7 RF-06 同源性

| # | 项 | 审核查证 | 结果 |
|---|---|---|---|
| 14 | 只读交接文档方向、未 merge 不同根分支 | `git log --merges 4d26cdd1..ecf60098` = **0**；`git rev-list --max-parents=0 ecf60098` = 唯一根 `1722e6dc`（本仓单根）；分支形态 = 基线 + 恰 1 个 feat 提交。RF-06 仅以 `agent/rf06-full-ui` 公开交接文档为方向参考（V4-B01 盘点在案：该分支远端 only、本机无对象、未做任何 merge/补丁移植）；色值真源落在本仓 TOKENS.proposal.json，与 diff_or_evidence_only.md §设计同源声明一致 | **CONFIRMED** |

## 2. CHALLENGED（2 项，均非阻断）+ 注记（1 项）

- **C1｜「卡面」引语非原文**：limitations.md §1「按卡面『模拟器不在本机 HEAVY 空窗内则不硬跑』授权跳过」——该句在 V4-F01 卡面与本仓全部文档中均**无原文**（`grep 不硬跑` 零命中）。实义授权真实且独立成立：v4/MASTER_DESIGN.md「最多一个 HEAVY 构建/模拟器/大测试运行」单槽纪律 + V4-F05（HEAVY=True、锁 style-preview、五面截图）归属 + B04 先例（模拟器不可用降级取证）。结论不受影响；后续引用请改为「按 v4/MASTER_DESIGN HEAVY 单槽纪律与 F05 卡面归属」。
- **C2｜越界回落测试覆盖口径**：用例「initialize 越界索引回落 classic（preview off）」实际只断言枚举边界常量（classic=0、4 档），未经 `initialize()` 构造越界持久值走守卫（`setPixelPreviewProfile` 无法构造越界，属诚实注明）。`initialize()` 内 bounds 守卫代码真实存在（越界时保持字段默认 classic），但该守卫**无直接可失败测试**。用例名略宽于实测覆盖，建议后续补一条直接注入 prefs 的用例或收窄命名。
- **N1（守护范围注记，非勘误）**：41 槽零差量断言两侧同源 `SparkleColors.light()/dark()` 工厂——本审变异实证其对**工厂值自身变更不敏感**（tautology），对 **preview 通道泄漏敏感**（立即失败）。即：该断言守护的是「classic 通道无注入/无泄漏」，classic 值冻结由本审 diff 全量扫描（classic 工厂零触碰、theme_manager +45/−0 纯增）+ 408/47 回归共同背书。实现侧 evidence 用语（「与既有发布主题逐槽比对」）与实测行为一致，不构成虚报；后续卡不应把该测试当「值冻结守卫」引用。

## 3. 裁决与后续

- **V4-F01 判 PASS**：一审通过，允许按舰队流程进入集成 SHA 复验；`review_receipt.json` 维持 PENDING 不由本审改写（本 receipt 即一审记录）。
- 合并前无附加条件；C1/C2 随本 receipt 在案（C1 为引用措辞勘误、C2 为测试覆盖口径登记），不阻塞任何卡面验收项。
- 集成复验提醒：集成 SHA 上重跑本 receipt §1.5 全表（约 2 分钟）+ §1.1 表 1 之 30 用例即可覆盖全部卡面验收的机器可验面；真实设备/五面截图等 HEAVY 面按 F05 卡走。

—— wtF01R1，2026-09-28（本文件即独立审查凭证；审查会话未参与 ecf60098 实现）
