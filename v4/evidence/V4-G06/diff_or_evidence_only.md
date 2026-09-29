# V4-G06 · diff 叙证（小队/自我锚/光子/成就——四风格商业化完备）

断点续跑：前任 agent 阵亡于宿主机强制重启，worktree dirty=14 项盘点后续跑零丢弃。

## 缺陷清单（含前任已修标注）

### A. 前任已修（dirty 恢复并纳入本卡；部分由本会话补完编译/lint）

| # | 文件 | 缺陷 → 修法 | 状态 |
|---|---|---|---|
| A1 | achievement_contract_screen | 庆祝勾徽白字对 dusk success 仅 1.59:1、文案裸压 40% 黑纱浅档 3.1:1 → getContrastSafeText 实算 + surfacePrimary 卡垫；金色脉冲 reduce-motion 静态化；倍率徽章 off-token 琥珀（白字 1.63:1）→ 实算墨 | 前任已修 |
| A2 | milestone_celebration_screen | 彩带 reduce-motion 不发射；stat chip 固定 150 宽 200% 截断 → min/max 约束；固定美术底豁免注释 + coldColorLiteral ratchet 登记（基线 6 只降不升） | 前任已修 |
| A3 | achievement_unlock_dialog | 光晕/粒子/旋转持续动效 reduce-motion 统一启停（didChangeDependencies 解析，哨兵初值防丢启动）；legendary 彩条/光环去 0xFFFFE082 等硬编码 → 令牌族 | 前任已修 |
| A4 | achievement_detail_screen | 解锁辉光微缩放/粒子环 reduce-motion 停表（0.5 中点静态近似） | 前任已修 |
| A5 | achievement_list_screen | 接近解锁徽章呼吸 reduce-motion 停表全不透明（提示语义由静态承载） | 前任已修 |
| A6 | streak_indicator | 火苗缩放停表中点/环形脉冲停表原尺寸/进度环一次性入场 | 前任已修 |
| A7 | streak_details_screen | 今日格呼吸 reduce-motion 停表高亮峰值 | 前任已修 |
| A8 | bonfire_widget | reduce-motion/性能降档等价（low=off / medium|reduceMotion=staticFrame / 其余全量，home DecorationMode 同口径）；等级徽标火色文字 1.0–1.7:1 → 按徽标底实算 | 前任已修 |
| A9 | community_widgets | 输入中三点动画 reduce-motion 停表静态梯度 | 前任已修 |
| A10 | groups_hub_view | 渐变图标 neutral0 压渐变最难端 2.70:1（classic-dark）→ 按最难端实算 | 前任已修 |
| A11 | photon_transfer_screen | 访客横幅 warning 压 warningLight 1.1–1.6:1 → 按底实算；余额卡 neutral0 压 accent 面浅档 1.2–1.4:1 → 按面实算 | 前任已修 |
| A12 | achievement_share_bottom_sheet | 微信 0xFF07C160 品牌通道色 identity 豁免登记（非主题色） | 前任已修 |
| A13 | achievement_map_screen | 阴影裸 ARGB 0x22000000 → 等值令牌写法 | 前任已修 |
| A14 | 5 文件 | 前任遗留 `context.reduceMotion` 未导入扩展 → 8 处编译错误（undefined_getter）| 本会话补完（补 sparkle_context_extension 导入）|
| A15 | 6 文件 | 前任遗留 11 处 lint（require_trailing_commas 等）→ dart fix | 本会话补完 |

### B. 本会话新修（走查新增缺陷，全部风格面、零行为语义变更）

| # | 文件 | 缺陷（实测）→ 修法 |
|---|---|---|
| B1 | achievement_map_screen | 状态 meta chip `Colors.white70` 在浅档近白详情面板上不可读 → `DS.textSecondary`（B2-3a 定标 ≥4.5:1 on S0/S1） |
| B2 | achievement_map_screen | 锁定节点 lock 图标白 35%、描边白 10% 浅档不可见（锁定=关键状态，非文字 ≥3:1）→ `DS.textTertiary` 实心 + `DS.borderSubtle` |
| B3 | achievement_map_screen | 锁定连接虚线白 12% 浅档画布不可见（路径上下文丢失）→ painter 增 `lockedLineColor` 入参，调用方传随档 `DS.border` |
| B4 | achievement_unlock_dialog | epic/legendary 内圆图标 `onBrandPrimary`（浅档解析为白）压 neutral0 恒浅内圆不可见；rare identity 金 #B8860B 对暗档 #F4F1EB 仅 2.89:1（<3:1 非文字阈值）→ `DS.onColor(DS.neutral0)` 恒深墨 |
| B5 | achievement_unlock_dialog | 卡面标题墨三重缺陷：rare #B8860B 对金端 2.3:1 全档失败；epic/legendary `onBrandPrimary` 白墨压浅端 2.31/2.78:1 → 双端实算墨（`ThemeUtils.getContrastSafeTextOnGradient`，白/黑双端 ≥4.5:1 者胜） |
| B6 | achievement_unlock_dialog | 渐变第二端用随档语义色（warning/brandSecondary/info）在 classic-light 与固定 identity 端明度相撞：三稀有度全部落入无公共墨色区间（双端下界 2.95/4.499/4.02:1，E- 控制组钉死）→ 收敛为稀有度身份色系固定双端（rare 金→深金 -25%；epic 紫→深紫 -35%（白墨 4.67/8.7）；legendary 珊瑚→浅珊瑚 +30%（深墨 7.6/8.9））。**[Q08 预登记]**：身份端点深浅属发布面美术维度，本卡按可读性下限就地收敛待裁 |
| B7 | achievement_unlock_dialog | 三处透明度压文字（0.8/0.6/0.8）违反 DESIGN_SYSTEM 1.3.1 禁则且使实算墨失守 → 去除压暗，全 opacity 实算墨 |
| B8 | achievement_unlock_dialog | reward/evidence/glory/surface 四个 neutral0 浮 chip 区沿用卡面墨（暗档=白墨压恒浅 chip 不可见）→ `DS.onColor(colors.background)` 按 chip 底实算 |
| B9 | streak_details_screen | 日历格数字墨 `textOnPrimary` 按 brandPrimary 实算而格底是 success/weak 中间色/warning → `DS.onColor(baseColor)` 按实际格底实算 |
| B10 | core/utils/theme_utils | 新增 `getContrastSafeTextOnGradient` + `minContrastOnGradient`（双端墨公共口径，公式与守卫钉同源；纯新增不改既有签名） |

## 新钉（本卡新增 CI 可失败守卫）

1. `mobile/test/widget/v4_g06_family_contrast_guard_test.dart` — 11 测试（8 正 + 3 组 E- 控制组：禁用灰/旧渐变配对/旧火堆徽标配对/旧 rare 图标配对判负，防测试自证），四档 = classic-light/classic-dark/paperDay/dusk/quiet 逐对复算。
2. `mobile/test/goldens/g06_four_style/g06_four_style_golden_test.dart` — 2 面 × 4 档确定性 golden（8 张，B04 容差比较器常态比对无 skip 门）+ 同源语义钉（徽章语义标签非空/火堆徽标在位/账本数字直出/庆祝可关按钮语义可达）；泵制带 `disableAnimations=true` 同时钉 reduce-motion 等价形态；BGM shutdown 门（`BgmService.dispose()`）+ q03 平台静音桩防 MissingPluginException 假失败与周期计时器泄漏。

## 回归计数

analyze 0 ｜ family(achievement+community+photon) 159 绿 ｜ widget 502 绿(4 skip 既有) ｜ goldens 86 绿(15 skip 既有采集门控) ｜ core/design+utils 314 绿 ｜ 全程 `--concurrency=1`，分批错峰，build 用后即清（128M 已删）。

## 交叉核对结论

- **像素网格同一（L19）**：家族三模块 lib 零位图资产引用（全 icon font + CustomPaint + 令牌色）——「不照搬第三方游戏素材」由构造满足；成就身份唯一真源 = DS.rarity* 令牌徽章，小队视觉 = BonfireWidget CustomPaint（2dp 概念网格，无文字画布整数缩放），四风格共用同一组件真源，无 per-style 分叉资产。golden 四档形态已钉。
- **S04 资产账本零改动红线**：本卡 diff（前任+本会话）只动 .dart 与测试基线（golden PNG 为测试夹具非应用资产），`mobile/assets` 零触碰，不触发 S04 台账任何字段 → 无需登记 Q05/S04 交叉项。
- **Shop HIDDEN 不开（L19）**：`features/shop` 零触碰、零新增深链/皮肤展示路径；streak_details Shop CTA 维持 V3-FIX-05 移除态（后端 RELEASE_ENABLE_SHOP 旗兜底）；与 V4-U12（自我锚与光子最新商业决定，done）一致。
