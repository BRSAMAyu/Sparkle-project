# V4-F01 — diff_or_evidence_only

## 结论一句话

纸昼/暮色/低刺激三个像素候选 profile 已并入唯一令牌体系（tokens_v2 → SparkleThemeData，无第二套颜色/字阶/间距类），preview 通道默认 classic=off、发布主题逐槽零差量、classic 随时可回退；PROPOSED 色板按 `v4/02_design/TOKENS.proposal.json` 提案值逐槽转抄并通过 WCAG ≥4.5:1 自动测（3 profile × 核心文案角色 × 三容器面 + onPrimary/onError 实路径）；四个设计棘轮守卫全过，analyze/受影响测试全绿。

## 差量明细（相对 base 4d26cdd1 = main HEAD）

新增 2 文件（全部在 mobile/）：

- `mobile/lib/core/design/tokens_v2/pixel_preview_theme.dart`（新增，~430 行）——
  `PixelPreviewProfile` 枚举（classic/paperDay/dusk/quiet）、PROPOSED 色板锚值
  （13 提案槽逐值转抄 + 派生槽注明公式）、`pixelPreviewColors()`/
  `pixelPreviewThemeData()`（产出既有 `SparkleColors`/`SparkleThemeData`）、
  `PixelStateMotion`（proposal motion_ms：press 80/state 160/enter 220/
  milestoneMax 650）、`PixelProfileTheme` ThemeExtension
  （DESIGN_SYSTEM.md 允许的四个新增字段：pixelStep=2dp、cornerCut=[4,8,12]、
  accentInk=on_accent、stateMotion）。文件头标注 PROPOSED_NOT_APPROVED 与
  权限源（v4/README_START_HERE.md 权限节：参考图是提案非批准，pixel.preview
  只在开发预览开放）。
- `mobile/test/core/design/pixel_preview_theme_test.dart`（新增，30 用例）——
  见 test_results.json。

修改 2 文件（最小增量，+80/−14，全部删除行为本卡自己的替换点）：

- `mobile/lib/core/design/tokens_v2/theme_manager.dart`（+45/−0）——preview
  通道状态：`pixelPreviewProfile`（默认 classic）、`pixelPreviewEnabled`、
  `setPixelPreviewProfile()`、持久化键 `pixel_preview_profile`（initialize
  越界回落 classic）、`themeForBrightness()` 头部 preview 分支（classic 不进
  分支，既有路径逐字节保持）、`reset()` 归零。切换 UI 不在本卡（F05 铺路）。
- `mobile/lib/core/design/design_system.dart`（+35/−14）——导出
  pixel_preview_theme.dart；`AppThemes.lightTheme/darkTheme` 的 brightness
  改取 `theme.colors.brightness`（classic 恒等，preview dusk 钉死暗色）；`_buildThemeData`
  在 preview 开启时 onPrimary/onSecondary/onError 取 proposal on_accent
  （accentInk）——classic 保持 `getContrastSafeText` 原公式零差量（dusk 档
  亮 accent 下原公式白/文本色二选一均 <4.5:1，属候选档实装缺陷，本卡修）；
  extensions 列表仅 preview 开启时挂 `PixelProfileTheme`（classic 不携带）。

## 设计同源（RF-06 线，只读参考）

- 设计语言方向对齐 sparkle-cosmos `agent/rf06-full-ui` 交接视觉合同
  （v4/evidence/V4-B01/diff_or_evidence_only.md §3 盘点 + 
  《前端设计与迭代交接》§3.1）：奶油纸底承托 + 深墨正文；鼠尾草绿（accent）、
  灰蓝（info）、陶土（warning/error 族）为功能强调；柔紫作为角色强调落在
  taskReflection（PROPOSED 字面量 #64558A 浅档 / #BCAED4 dusk，非 proposal
  槽位，标注来源与对比度依据 ≥4.58:1）；像素概念网格 2dp、角切 4/8/12。
- 该分支属不同根仓库（无 merge-base），未做任何 merge/补丁移植；本卡只复用
  其公开交接文档描述的方向，全部色值真源是本仓 `v4/02_design/TOKENS.proposal.json`。

## 验收对照

| 卡面验收 | 结果 |
|---|---|
| 最终颜色对比度自动测；3 profile 核心文案可读 | 满足：pixel_preview_theme_test.dart「自动对比度测量」组——3 profile × 10 文本角色 × 3 容器面 ≥4.5:1、border 槽 ≥3:1 图形线、聊天气泡 ≥4.5:1、onPrimary/onError 走 AppThemes 实路径 ≥4.5:1；基线=底3浅/深容器与全部文本槽（20 对 × 3 档 + 实路径 6 对），全部通过 |
| 200% 字阶无主 CTA 截断，系统字号可继承 | 满足：真实 ThemeData 渲染 FilledButton，TextScaler.linear(2.0) 下无异常、标签渲染尺寸随字阶放大（17→33px）、标签盒完整落入按钮盒、按钮 ≥48dp；字阶复用 SparkleTypography.standard（断言 fontSize 恒等） |
| runtime 只有一个 token 源 | 满足：候选档产出既有 SparkleThemeData/SparkleColors（同类型断言）；AppThemes/DS 静态层与 pixelPreviewColors 同值断言；无第二套颜色/字阶/间距类（新增类型只承载 4 个 DESIGN_SYSTEM.md 点名的像素扩展字段） |
| preview 默认 off | 满足：默认 classic、发布主题 41 颜色槽逐槽零差量（浅/深两态）、classic 往返回退逐槽复原、持久化 + reset 归零有断言 |

## 保持不动（红线核验）

- 默认发布主题：classic 路径 41 颜色槽逐槽零差量（浅/深），PixelProfileTheme
  扩展 classic 不挂载（断言覆盖）。
- 五 Tab 路由：零触碰（diff 不含 routes/shell 文件）。
- 生成文件：零触碰（mobile/lib/gen 由 make proto-gen 本地重建，未入库；
  l10n 生成文件曾被 flutter 工具误触再生成，已 git checkout 还原，不在 diff 中）。
- 既有经典主题/品牌预设/商城皮肤/高对比/色盲友好逻辑：未改（preview 分支
  置于 themeForBrightness 头部，classic 短路）。
