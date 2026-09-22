# DS-GRADIENT：design_system.dart 渐变 API 守卫盲区封堵 — 收工报告

- 卡：DS-GRADIENT（micro）｜worktree：`wt134`｜基线：`b7956f1c`
- 日期：2026-09-22｜SPEC 依据：DL-R3 SPEC v1.0 §1.4.1/§1.4.2/§1.5/§5.3（A5.3 "gradient/屏 ≤2 处且非核心流程——ratchet 口径新维度"）

## 0. 结论一句话

`DS.accentGradient` 一族（13 个 DS 渐变 API）此前完全游离于守卫之外（`\bDS\.accent\b` 因词边界不命中 `DS.accentGradient`；`gradientLiteral` 只查裸 `LinearGradient(` 构造）。本次在 `check_dl_spec_ratchet.py` 新增两个 ratchet 维度封堵盲区，基线钉定 **60/1**，存量违规 1 处登记不强改，`accentGradient` 标 `@Deprecated` 与 `DS.accent` 先例对齐。

## 1. 现状审计表（①）

DS 渐变 API 暴露面（`design_system.dart` `// Gradients` 块 + 角色/任务助手，共 13 个符号）：`primaryGradient / secondaryGradient / secondaryGradientDark / accentGradient / infoGradient / warningGradient / successGradient / errorGradient / cardGradientNeutral / deepSpaceGradient / flameGradient / pageGradientForRole / getTaskGradient`。

全仓调用点 **23 文件 / 60 引用**（守卫扫描口径 = 去注释行；与 grep 一致）。合规判定按色值构成与 SPEC 条款：

| 判定 | API | 构成 | 调用点（文件=数） | 依据 |
|---|---|---|---|---|
| **违规** | `accentGradient` ×1 | `accent`(=brandSecondary) **满饱和** + 亮度偏移 | flame_indicator.dart=1（brightness 60–79 档的装饰进度环+火焰图标） | §1.4.1/§1.4.2：brandSecondary 退役，不得作第二交互色；装饰位。**登记钉基线，B2-3+ 迁移** |
| 合规（语义槽 §1.5） | `info/warning/success/errorGradient` ×25 | 语义槽色本体/降透明 | error_widget=3, action_card=11, content_review_card=3, plan_review_card=4, pattern_card=3, task_detail=3, chat_input=1（error 档） | 语义槽渐变，方向正确 |
| 合规（可点击控件 §1.4.1 允许场景） | `primaryGradient`（=surface 混 5–12% brandSecondary 的 ambient wash，**不含 brandPrimary**）部分点 | 选中态/发送键/CTA | community_chat_input=1, task_list=1（选中态）, goal_created_dialog=1, transparency_panel=1, preference_controller_2d=1, achievement_stats_panel=1, chat_input=1, chat_bubble=1, action_card=3, pattern_card=1, task_detail=2, flame_indicator=1, loading_indicator=1 | 控件/品牌场景允许；primaryGradient 实为表面环境光，非满饱和交互色 |
| 合规（装饰环境光/中性/背景） | `secondaryGradient`（surface 混 4–8% brandSecondary）×6、`cardGradientNeutral` ×3、`deepSpaceGradient` ×2、`pageGradientForRole` ×2 | 表面/中性层/背景 | chat_bubble=1(AI 侧), focus_action_card=1, candidate_action_sheet=1, focus_agent_sheet=1, curiosity_capsule_card=1, action_card=8, loading_indicator=1, background_layer=1, graphite_surfaces=1, dashboard_screen=1 | 非交互色双义；AI 侧用 brandSecondary 派生与 §1.4.2 "info 派生来源"方向一致 |
| 暴露面（0 调用） | `secondaryGradientDark`（secondaryBaseDark→brandPrimary 混合，存疑设计）、`flameGradient`、`getTaskGradient`（§1.5.1 任务色条款约束） | — | 无 | 纳入 ratchet，新增即拦 |

关键色值事实：`primaryGradient`/`secondaryGradient` 并非饱和交互色渐变，而是 `_blend(surface, brandSecondary, 0.04–0.12)` 的环境光 wash——真正的盲区风险集中在 `accentGradient`（唯一满饱和直引）。同文件 `_getFlameColor()` 的色值孪生已被 B2-3a 以 `DS.brandSecondary` 等值直引处理（见 flame_indicator.dart:106 注释），渐变 API 是同族漏网之鱼。

## 2. 守卫维度说明（②实现）

`scripts/guards/check_dl_spec_ratchet.py` 新增两维（照既有写法：行扫描、去注释、per-file 基线、`--update-baseline` 显式重钉、拒绝抬升）：

| 维度 | 条款 | scope | 模式 | 语义 |
|---|---|---|---|---|
| `dsGradientApiCalls` | A5.3（SPEC §5.3 "ratchet 口径新维度"） | mobile-lib | `\bDS\.(13 个符号名枚举)\b`（长名在前防 `secondaryGradientDark` 误短配；**刻意名枚举**而非 `\w*Gradient`，未来新增 getter 必须有意识地登记） | DS 渐变 API 家族引用总数，基线=当前 60，只降不升；新文件 allowance 0 |
| `dsAccentGradientForbidden` | A1.5（§1.4.2 别名族） | mobile-lib | `\bDS\.accentGradient\b` | 满饱和第二交互色渐变禁令；存量 1 处钉死，其余任何文件出现即 FAIL（含新文件） |

配套改动：
- 定义处天然不命中（`static LinearGradient get accentGradient` 无 `DS.` 前缀）；`.g.dart/.freezed.dart` 沿用既有排除。
- `update_baseline` 拒绝信息增补"新维度首钉是唯一合法 `--allow-raise` 用途"指引；`--allow-raise` 放行时**打印所有上升维度明细**（本次输出：`dsGradientApiCalls: 0 -> 60, dsAccentGradientForbidden: 0 -> 1`），审计留痕。
- self-test 新增 Case 4（a：新文件任意 DS 渐变 API 即拒且不误伤 accent 禁令；b：新文件 `DS.accentGradient` 双维度齐发；c：钉定文件抬升拒；d：还原 PASS）。
- 登记面：manifest 无需新行——`scripts/rule_guard_manifest.tsv:75` 按脚本整行登记（`DL-SPEC`），新维度自动纳入；守卫脚本 docstring 维度表已更新。

## 3. 基线值（③钉定证据）

`dl_spec_ratchet_baseline.json` 重钉前后（既有维度**只降不升**）：

```
bannedCurve 24→24, breathingController 1→1, coldColorLiteral 90→90, colorsDotNative 1→1,
confettiPerFile 7→7, errorCopyOops 6→6, gradientLiteral 303→303, dsAccentAlias 0→0,
textHardcodedZh 0→0, particleBypass 77→77,
offLadderDuration 186→184  ← 非 DS-GRADIENT 所致：HEAD b7956f1c（B3-CHAT 合入）相对旧基线
                              （冻结于 d87d42ea）的既存债务下降，本次重钉顺带固化（合法方向）；
                              已核验我的 dart diff 无任何 Duration 行
dsGradientApiCalls 0→60（新维度首钉）, dsAccentGradientForbidden 0→1（新维度首钉）
```

首钉流程留痕：无 `--allow-raise` 先跑被拒（exit 1，拒绝信息含两个新维度明细），核对既有维度总量快照零移动后显式 `--allow-raise` 放行。

## 4. 全绿证明（④回归）

1. `check_dl_spec_ratchet.py --self-test` → **SELF-TEST PASS**（含新 Case 4：`DS gradient-API dims all behave`）
2. `check_dl_spec_ratchet.py` → **PASS**：`dsGradientApiCalls=60/60, dsAccentGradientForbidden=1/1`，其余 12 维全部 current≤baseline
3. `bash scripts/run_all_rule_guards.sh` → **design 守卫族全绿**（DL-SPEC / UI-TOKENS `color=239/275, fontSize=719/727` / UX-COMP 五维）+ 其余守卫绿；唯 **AQ/BG 失败 = 环境性**：本 worktree 未跑 `make proto-gen`，`app.gen`/`*.pb.go`/`*.pb.dart` 产物缺失（proto parity 检查不读本次任何改动文件，与卡无关）
4. `flutter analyze lib/core/design/design_system.dart` → **0 issues**；flame_indicator.dart 仅 4 条**既存** `discarded_futures` info（L76–87 `.repeat()`，非本次改动，未触碰）
5. 盲区现形证明：重钉基线**前**守卫即 FAIL 23 处（`NEW FILE flame_indicator: dsAccentGradientForbidden=1` 等）——新维度确有捕获力，非摆设

## 5. 净化决策（⑤申报）

**存量违规 1 处（flame_indicator.dart:126）不改色，登记钉基线**。理由（红线：不破坏视觉既有行为）：`accentGradient` 是主题相关的 brandSecondary 满饱和渐变（默认浅色主题下 brandSecondary=primaryColor 暖棕），改成语义槽 `infoGradient`（slate 蓝槽）是肉眼可见的换色，属视觉决策，超出 micro 卡授权；且 B2-3a 对同文件色值孪生的既有裁决就是"等值直引保留"。迁移留给 B2-3+（报告即登记）。零改动方案下守卫 teeth 不减：该文件已被钉死，任何新增（含其他文件）立即 FAIL。

配套零视觉影响动作：`accentGradient` 标 `@Deprecated`（doc 注释指向语义槽/表面渐变替代与守卫名），与 SPEC §1.4.2 对 `DS.accent` 的处理完全同构。**申报**：项目 `analysis_options.yaml` 只配了 `deprecated_member_use: warning`（跨包才触发），同包引用提示需 `deprecated_member_use_from_same_package`（未启用，启用会全仓扩面，不属本卡）；故 @Deprecated 的强制力同样落在 ratchet 守卫上，IDE 侧有删除线信号，与 DS.accent 先例待遇一致。

## Worker 五要素

**① 现状审计表**：见 §1（23 文件/60 引用，违规 1，语义槽 25，环境光/控件 34）。
**② 红线面**：守卫纯只读扫描，永不写源码与基线；基线仅 `--update-baseline` 显式重钉且拒绝抬升（本次首钉走显式 `--allow-raise` 并打印明细，非 S22 式读时自写）；拒绝信息已增补新维度首钉指引。
**③ 冲突面**：在途卡全在 backend/galaxy/mobile-features，与无重叠。我改了 `scripts/guards/check_dl_spec_ratchet.py`、`scripts/guards/dl_spec_ratchet_baseline.json`、`mobile/lib/core/design/design_system.dart`（仅加注释+@Deprecated，无行为变更）。**未触碰任何 B3-CHAT chat 面文件**——审计含 chat 8 文件但全部只读；@Deprecated 在当前 lint 配置下不产生同包告警，对 chat 面在途工作零噪音。
**④ 诚实申报**：(a) offLadderDuration 186→184 是 HEAD 既存下降的顺带固化，非本卡工作；(b) AQ/BG 红是本 worktree 缺 proto 产物的环境问题；(c) accentGradient 违规未净化（§5 理由）；(d) 同包 deprecation 提示不触发（lint 未启 `from_same_package`）；(e) `secondaryGradientDark` 设计存疑（混合交互色）但 0 调用，仅纳入守卫面。
**⑤ 收工核查**：未 commit/push；交付物 = 本报告 + `changes.patch`；无临时产物残留（仅 `/tmp/ds-gradient-totals-before.txt` 快照，随收工清理）；未起任何重进程；主仓只读未触碰。

## 附：改动文件清单

| 文件 | 变更 |
|---|---|
| `scripts/guards/check_dl_spec_ratchet.py` | +2 维度、+2 模式、docstring 表、update_baseline 透明度、self-test Case 4 |
| `scripts/guards/dl_spec_ratchet_baseline.json` | 重钉（新维度 60/1；offLadderDuration 186→184 固化既存下降） |
| `mobile/lib/core/design/design_system.dart` | `accentGradient` + doc 注释 + `@Deprecated`（零行为变更） |
| `v3-output/DS-GRADIENT/REPORT.md` | 本报告 |
