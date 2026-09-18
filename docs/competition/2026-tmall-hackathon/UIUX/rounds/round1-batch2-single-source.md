# Round 1 · 批次 2 — 双事实源收敛（Single Source of Truth）

> 上游：`round1-L1-design-system.md`（P0-2 双事实源 / P0-3 字阶三体系）· `round1-batch1-contrast.md`（数值已先校准，本批只删结构不改校准值）
> 本批边界：**删双源**。container 四件套（xxxContainer/onContainer）与 `context.sparkle` 入口统一留批次 3。
> 纪律：色值以树上现值为真相源（批次 1 对比度数值已在基线）；零构建、零 flutter test；dart analyze 定向。

---

## 0. 结果速览

| 指标 | 值 |
| --- | --- |
| 改动 | 10 文件，+168 / −622（净 −454 行） |
| 删除文件 | `tokens/task_colors.dart`（81 行）、`tokens_v2/typography_token.dart`（226 行） |
| 事实源收敛 | 任务色 **3 → 1**（TaskColors、SparkleTaskColors → SparkleColors.task*）；品牌色 **2 → 1**（SemanticColors.brand* → SparkleColors.brand*）；字阶 **3 → 1**（TypographySystem、DS 字阶 → SparkleTypography） |
| 迁移调用点 | 真实调用点全迁移（task_pill、login_screen、theme extension 接线）；超额面（116 文件字号 + 394 文件字重）按预设分支降级为冻结 deprecated shim |
| 验证 | 定向 dart analyze 8 文件 **0 error / 0 warning**；旧符号 lib+test 严格 grep **零代码残留** |

---

## 1. 裁决一：TaskColors vs SparkleColors.task*（L1 P0-2）

**裁决：SparkleColors.task*（tokens_v2/theme_manager.dart）为唯一事实源。**

依据：批次 1 已将浅色 task* 收敛到语义色值（`theme_manager.dart` 批次 1 注释原话 "so batch 2 inherits one value per hue"），本树现值即为此裁决准备的收敛目标；L1 §5.1 与 P0-2 修复方向均为"删 TaskColors"。

### 1.1 色值处置（以现值为准）

- 两侧共有槽位：**保留 SparkleColors 现值**，TaskColors 侧值随之消亡（浅色 learning `#175FB0` vs `#48678D` 的分叉终结——同一 hue 从此只有一个值）。
- TaskColors 独有的 **OCR 槽折入**：`taskOcr` 新增字段接进全部 6 套工厂（light/HC/CB × light/dark），值 = TaskColors 现值（light `#4F6572` / dark `#78909C`）；特殊档沿用同值——灰色天然色盲/高对比中性，零新发明字面量。
- `getTaskColor(String)` 补 `'ocr'` case；新增强类型 `Color taskColorFor(TaskType)` 作为 TaskType → 调色板的唯一映射。

### 1.2 删除与迁移

| 对象 | 处置 | 规模 |
| --- | --- | --- |
| `tokens/task_colors.dart` | 整文件删除（`TaskColors`、`_RawTaskColors` 14 值） | −81 行 |
| `SparkleTaskColors`（app/theme.dart 第三方源，存疑值 64B5F6/FF9800 系） | 类 + `SparkleTaskColorsExtension` + 2 处 ThemeData 注册全删（lib+test 零消费，本就 @Deprecated） | −223 行 |
| `task_pill.dart`（唯一真实消费者） | 4 个角色 getter 调用迁移为 `context.colors.taskColorFor(type)` 单点取色；import 改 `task_model.dart show TaskType` | 1 组件 |
| `SparkleThemeExtension` | 拆线：`taskColors` 字段、2 个 factory 注入、copyWith、lerp 全删（任务色本就随 `colors` 走 lerp） | 8 行 |
| `SparkleContextExtension` | `taskColors` getter 删除 | 1 getter |

### 1.3 行为变化（即修复本体）

无 tone 的 `TaskPill` 由 TaskColors 饱和 Material 值（浅色 learning `#175FB0` 等，L1 §2.3 点名的"首页一套、pill 另一套"）切换为调色板 task* 值（浅色 learning `#48678D` = semanticInfo），暗色同步走调色板暗档——pill 与全局色彩语言归一口音。

---

## 2. 裁决二：SemanticColors.brandOrange/brandBlue vs SparkleColors.brand*（L1 P0-2）

**裁决：SparkleColors.brand* 为唯一事实源；登录页品牌标改用产品真实品牌对。**

依据：L1 §2.4——用户认识产品的第一个 3 秒看到的不是产品品牌色（纸感书院 #825D49 暖棕 vs 登录页孤立 #D9773A 促销橙）。

### 2.1 色值处置（以现值为准）

- 锚值全保留：`brandPrimary`/`brandSecondary` 六套工厂现值一字不动。
- Deep 渐变端角色（原孤立值 `#BA5923`/`#2F588E`）改为**派生 getter**：`brandPrimaryDeep` / `brandSecondaryDeep` = `Color.lerp(anchor, black, 0.16)`。单一公式、零新增 hex 字面量、与锚值永不漂移、六套调色板自动成立（CB 档同 hue 变深仍 CB-safe）。

### 2.2 删除与迁移

| 对象 | 处置 |
| --- | --- |
| `SemanticColors.brandOrange/brandOrangeDeep/brandBlue/brandBlueDeep` | 4 个 getter（4 个孤立字面量）删除，原址留收敛注释 |
| `login_screen.dart`（唯一消费者） | 4 个私有 getter 改指 `SparkleColors`；`_BrandMark`/`_BrandWordmark` 参数正名 `orange/orangeDeep/blue/blueDeep` → `primary/primaryDeep/secondary/secondaryDeep`（8 处重命名），消除"登录页是橙色品牌"的命名误导 |

### 2.3 行为变化（即修复本体）

登录页品牌标从促销橙蓝渐变切换为产品品牌对：浅色 `#825D49 → 深化16%` / `#7A8BA6 → 深化16%`，暗色 `#C97A43` / `#7E8FAE`——L1 P0-2"登录页品牌分裂"的修复本体。视觉终验随 L2/L3 截图波。

---

## 3. 裁决三：字阶三体系单一真相源（L1 P0-3）

**裁决：SparkleTypography（theme_manager.dart）为唯一样式真相源。**
**分支触发：DS 数值面 116 文件（字号 ~633 调用点）+ 394 文件（字重 ~1659 调用点）远超 30 文件阈值 → 按任务预设降级 shim 方案**：样式 shim 转发到唯一源，数值 shim 冻结。

### 3.1 删除

`tokens_v2/typography_token.dart` 整文件（−226 行）：`TypographySystem` 样式工厂 ×9、`TypographyToken`、`TypographyTokenVariant`、`TextKey`、`TypographyThemeExtension`（后四者 lib+test 零消费，其中 ThemeExtension 版 sparkleTypography 映射本身就是第四个微型事实源）；`design_system.dart` 的 import/export 同步摘除。

### 3.2 样式 shim（转发，值收敛）

`DS` 9 个 TextStyle getter 重指向 `SparkleTypography.standard()` 并全部 `@Deprecated('Use context.typo.* instead.')`。存量 ~744 调用点不动，渲染值按 L1 P0-3 指认的冲突归一：

| DS 符号（shim） | 旧值（TypographySystem） | 新值（SparkleTypography） | 调用点 |
| --- | --- | --- | --- |
| displayLarge | 48.8 w800 | 46 w700 | 1 |
| headingLarge | 39 w700 | 30 w700 | 3 |
| titleLarge | 25 w600 | 19 w500 | 35 |
| titleMedium | 20 w600 | 19 w500（暂转发 titleLarge，待 15 角色扩展） | 34 |
| bodyLarge | 20 w400 | 16 w400 | 18 |
| bodyMedium | 16 w400 | 14 w400 | 125 |
| bodySmall | 12.8 w500 | 12 w400（bodySmall 别名） | 348 |
| labelLarge | 16 w500 | 14 w500 | 23 |
| labelSmall | 12.8 w500 | 12 w500 | 157 |

硬下限核验：正文 ≥14 ✓（14/16），元数据 ≥12 ✓（12）；TypographySystem 的 12.8/48.8 非整倍率值全部消失。

### 3.3 数值 shim（冻结，值恒等）

`DS.fontSize*/fontWeight*/lineHeightNormal/fontSizeSM|MD|LG|XL` 约 20 个符号：**数值原样冻结**（含 fontSizeSm=16、captionStyle=16 等历史怪值，注释明示"冻结待逐屏迁移"），全部 `@Deprecated`；TypographySystem 引用改为恒等字面量。统计模块 4 个兼容样式（textStyle/headlineStyle/bodyStyle/captionStyle）内联冻结值以消除自弃用。**这层是冻结兼容层，不是第三事实源**：不再演化、不再新增，唯一演化方向是逐屏迁往 `context.typo`。

---

## 4. 批次 1 移交项处置

| 移交项（batch1 §6） | 本批处置 |
| --- | --- |
| `userChatBubbleGradient` 零消费死令牌（"批次 2 删除或重定义"） | **已删除**（SparkleColors getter，零消费经 lib+test 复核） |
| features 层旧 TaskColors 值硬编码副本（"批次 3+ 模块横扫"） | 现存 3 处（calendar/avatar/candidate_action）经核对实为**名字键通用调色板**（`'orange'` 等），非 TaskType 语义 → 维持批次 3+ 模块横扫，不属本批对 |

---

## 5. 验证

- **dart analyze 定向**（8 个改动/接线文件）：**0 error / 0 warning**。过程中抓到并当场修复：`ambiguous_extension_member_access` ×5（见 §6）、EOF 换行 ×1。
- **旧符号 grep**（lib+test，仅豁免整行注释）：`TaskColors` / `SparkleTaskColors` / `TypographySystem` / `TypographyToken` / `TextKey` / `brandOrange` / `brandBlue` / `taskColors` / `task_colors` / `typography_token` → **零代码残留**（仅 2 条出处注释 + 1 条冻结值注释）。
- **消费面复核**：`SparkleColors(` 外部构造零（新增必填字段无破坏面）；两扩展并存下裸用 `context.colors` 的其他文件扫描零命中。
- 纪律：零构建、零 flutter test；`pub get` 仅依赖解析（.dart_tool，gitignore 内）。
- 视觉终验（随 L2/L3 截图波）：登录页品牌标、无 tone 的 TaskPill、DS 字阶 shim 涉及屏（titleMedium/bodySmall 高频屏优先）。

---

## 6. 残留与移交（批次 3 边界）

| 项 | 现状 | 去向 |
| --- | --- | --- |
| **双 `colors` 入口碰撞** | `SparkleContext`(design_system).colors（aliases 门面）vs `SparkleContextExtension`.colors（真 palette）——本批在 task_pill/login_screen 实际撞线（ambiguous error），已用显式扩展调用临时消歧（`task_card.dart:775` 既有先例） | **批次 3 入口统一的第一案**：aliases 门面退役或改名 |
| `context.sparkleTypography` 第二排版入口 | design_system.dart:488，3 个 feature 文件在用 | 批次 3 入口统一 |
| AppColors(app/theme.dart)、SemanticColors 其余 ~76 色（galaxy/agent/intent/sector/achievement/template） | 域 palette 并入或豁免（L1 P1-9 高对比贯通） | 批次 3+ |
| container 四件套（xxxContainer/onContainer）、tint 边缘带、textTertiary 静态化、CB 浅色档重校 | batch1 §6 移交表原样 | 批次 3 |
| features 层名字键调色板字面量（3 处） | 非任务色语义 | 批次 3+ 模块横扫 |
| SparkleTypography 15 角色扩展 + TextTheme 补齐映射（L1 §4.1） | titleMedium shim 暂转发 titleLarge | 批次 3 |
