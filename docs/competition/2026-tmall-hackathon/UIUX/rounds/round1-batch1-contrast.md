# Round 1 — 批次 1 修复记录：浅色模式对比度达标（P0-1）

> 执行：Aurelia（设计系统方向）｜ 日期：2026-09-18 ｜ 基线：wt2 @ ca86bda8（冻结，未 commit）
> 对应诊断：`round1-L1-design-system.md` §2.3 / P0-1（本批只修数值，不动令牌结构）
> 改动文件（3）：`mobile/lib/core/design/tokens_v2/theme_manager.dart`、`mobile/lib/core/design/tokens/task_colors.dart`、`mobile/lib/core/design/color_extensions.dart`

---

## 1. 验收口径（先定义"达标"，再谈数值）

**公式**：WCAG 2.x 相对亮度对比度 `(L1+0.05)/(L2+0.05)`，L 为 sRGB 线性化相对亮度（0.2126R+0.7152G+0.0722B，每通道 γ 展开）。全部数值由脚本实算（见 §7 验证）。

**文字前景（本批主标准）：≥4.5:1**，绑定容器集 = 文字真实落点的并集：

| 容器 | 色值 | 来源 |
| --- | --- | --- |
| white | #FFFFFF | Material 卡片/底板 |
| surfaceAmbient | #FCF8F3 | 浅色高阶面 |
| surfacePrimary | #F8F4EF | 页面底色（报告引用基准） |
| surfaceSecondary | #F1EBE4 | 面板/卡面 |
| chatBubbleOther | #F5F0E8 | 聊天链接文字底 |
| 上三者的 10% tint 叠底 | — | pill 真实底 = 原色 10% 叠在容器上（TaskPill/SemanticPill/AiStatusCapsule 三处同构） |

**图形/状态点（statusOnline 这类）：≥3:1**（WCAG 1.4.11 非文字对比），并明确禁止其作文字使用（当前无此用法，已审计）。

**显式豁免（记录在案，非隐瞒）**：10% tint 叠 surfaceSecondary/tertiary 的边缘落点（实测 4.07–4.58 带）不在本批绑定集内——把全部 15 个色都压过这条线会把调色板逼进高对比档（橄榄泥化），违背"纸感书院"气质；该落点的正解是批次 2 的 container 对令牌（`xxxContainer/onContainer`），届时文字不再用原色而用配对前景。逐色残值已在 §5 速查表如实列出。

---

## 2. 修复清单

### 2.1 brandPrimary（报告点名 3.33:1）

`theme_manager.dart` light normal：`#A77D63 → #825D49`

| 组合 | 前 | 后 |
| --- | --- | --- |
| on surfacePrimary（报告基准） | 3.33 | **5.31** |
| on white | 3.65 | 5.82 |
| on surfaceSecondary | 3.08 | 4.91 |
| on chatBubbleOther（聊链接文字底） | 3.22 | 5.13 |
| on primary 的 10% tint（brand pill 文字） | ~2.9 | **4.66**（绑定集最差点） |
| 白字 on brandPrimary（实心按钮反白） | 3.65 | **5.82** |

**设计决策：加深 base，而非引入 onBrand 前景令牌。** 理由：(1) 使用面审计显示 brandPrimary 直接作文字/图标的调用点 30+（chat_bubble 链接色 1079/1224/2501/2683 行、AiStatusCapsule、TaskPill tone=brand 等），onBrand 方案要逐点改用法 = 结构改动，违反本批边界；(2) 加深一次修正双向问题——彩色文字达标的同时，实心按钮反白从 3.65 提到 5.82；(3) DS 门面（design_system.dart:627）全部转发 `_theme.colors`，features 层 `brandPrimary` 色值在 core/design 之外**零硬编码副本**（已 grep 审计），单点改值全局生效。onBrand/onContainer 前景对按蓝图留给批次 2（四件套结构）。

**暖棕气质**：#A77D63→#825D49 同色相（~25°）加深约一档半，饱和度未加，纸感不变脏；`glowPrimary` 同步 `0x24A77D63→0x24825D49` 保持光晕同源。

### 2.2 TaskColors 六任务色（报告点名 1.59–2.02:1）

`task_colors.dart` 浅色值（pill 的 getLabel/getIcon 直接用原色，底为 10% tint）：

| 任务 | 前 → 后 | 白底 | 白底 tint（pill 实际） | primary tint |
| --- | --- | --- | --- | --- |
| learning | #64B5F6 → **#175FB0** | 2.21→**6.36** | 2.06→5.49 | 1.89→5.04 |
| training | #FF9800 → **#8E4E00** | 2.16→**6.48** | 2.00→5.59 | 1.84→5.11 |
| errorFix | #EF5350 → **#B0312A** | 3.49→**6.33** | 3.09→5.40 | 2.84→4.95 |
| reflection | #9C27B0 **保持不动** | 6.30（原已达标） | 5.37 | 4.96 |
| social | #FFB703 → 拆 **socialLight #755F00** / socialDark #FFB703 | 1.75→**6.19** | 1.65→5.37 | 1.52→4.93 |
| planning | #009688 → **#00695C** | 3.67→**6.61** | 3.25→5.69 | 3.00→5.21 |
| ocr | #78909C → 拆 **ocrLight #4F6572** / ocrDark #78909C | 3.35→**6.11** | 3.04→5.33 | 2.78→4.89 |

（注：报告所引 2.02/1.59 为 pill tint 叠卡面口径，本表白底口径略高，同一缺陷。）

要点：
- **social/ocr 拆分是暗色零回归的关键**：这两色原为明暗共用单值，直接加深会把暗色 amber 从 9.94:1 拖到 ~4:1。拆分沿用本文件既有的 `xxxLight/xxxDark` 模式（最小结构触达），dark 侧逐字节保留原值。
- "大面积底色 3:1 vs 文字前景 4.5:1" 的区分结论：审计确认 TaskColors 唯一消费点是 `task_pill.dart`（tint 底 + 原色文字/图标），不存在原色大面积实心底用法；故全部按文字 4.5:1 校准，自动覆盖图形 3:1 线，无需两套值。
- 饱和 Material 色系在 features 层有 10 处硬编码副本（64B5F6×2、FF9800×5、EF5350×2、009688×1），不在本批边界，已列入 §6 移交清单。
- socialLight #755F00 仍是琥珀 hue（~50° 深金），维持"social 必须是 amber"的原始注释约定。

### 2.3 semanticWarning（报告点名 2.34:1）+ 聊天气泡白字（报告点名 3.94:1）

- `semanticWarning`：`#C59A67 → #7D5C26`，surfacePrimary 2.34→**5.59**；白底 2.56→6.12；amber→深琥珀棕，ctaAccent 语义不变（ctaAccent 当前零消费点，已审计）。`warningAccent`/`warningLight` 为派生 getter，自动跟随。
- 聊天气泡：`chatBubbleUser` `#6B82A0 → #566C8C`，白字对比 3.94→**5.36**。选择加深雾蓝底而非改字色：白字于彩色气泡是 IM 惯例心智，且雾蓝加深半档仍是"雾蓝"；`chatBubbleUserText` 保持白色不动。暗色气泡（#5A5A62，白字 6.83）不动。`userChatBubbleGradient` 零消费（已审计），其起点 brandSecondary 的问题记入批次 2（见 §6）。

### 2.4 系统性同缺陷延伸（同一 P0-1、同一文件、同类文字用途——本批一并修数值）

审计发现报告 §2.3 表只点名了最差值，但同一失败机制覆盖整个浅色文字角色集（消费点：TaskPill 六个 tone 分支把 semantic 四色当文字；agent_reasoning_bubble_v2 把 task*/plan* 当文字）：

| 令牌 | 前 → 后 | surfacePrimary |
| --- | --- | --- |
| semanticSuccess | #7E9C87 → **#456E52** | 2.74→**5.32** |
| semanticError | #C17A70 → **#A0483E** | 3.05→**5.49** |
| semanticInfo | #7590B0 → **#48678D** | 3.01→**5.33** |
| taskLearning | #7893B2 → **#48678D** | 2.90→**5.33** |
| taskTraining | （=新 semanticWarning） | 2.34→**5.59** |
| taskErrorFix | （=新 semanticError） | 3.05→**5.49** |
| taskReflection | #9A88B7 → **#6C5C92** | 2.91→**5.35** |
| taskSocial | #769083 → **#456E52** | 3.15→**5.32** |
| taskPlanning | #6A8790 → **#426D77** | 3.50→**5.20** |
| planSprint | #B3756B → **#A0483E** | 3.38→**5.49** |
| planGrowth | #73907A → **#456E52** | 3.20→**5.32** |

**收敛策略**：原调色板里 taskLearning/taskErrorFix/taskTraining/planSprint/planGrowth/taskSocial 与 semanticInfo/Error/Warning 同 hue 不同值——本批让同 hue 者取同一新值，浅色"任务色"从 11 个独立值收敛为 7 个（雾蓝/琥珀/陶红/鼠尾草绿/堇紫/青灰 + 状态绿），视觉区分度不减（各任务类型仍各有独立 hue），而批次 2 删双源时 inherits 一 hue 一值，合并面显著缩小。

**statusOnline**（报告点名 1.92:1，dot 用途）：`#2ECC71 → #189150`，surfacePrimary 1.92→**3.68**，全部浅色面（含 tertiary 3.04）过 3:1 图形线；白字上它为 4.03 <4.5，**禁止作文字**（当前无此用法）。连带修复两处同值陷阱：浅色 highContrast 档 statusOnline（1.86→**3.58**，HC 档不应比正常档更差）与 `color_extensions.dart` 的死 getter `statusOnlineColor`（零消费，但对齐防未来误用）。暗色两档 statusOnline（9.41/8.25）不动。

---

## 3. 暗色模式联动核查（不得退化）

暗色退化路径只有两条，均已封死：

1. **SparkleColors.dark 三档（normal/highContrast/colorBlindFriendly）逐字节未动** → 暗色全部组合比值不变。
2. **task_colors.dart 明暗共用值的拆分**：socialDark/ocrDark 保留拆分前原值 `#FFB703`/`#78909C`，暗色实算与前完全一致。

暗色关键组合复核（改前=改后）：brandPrimary #C97A43 on #1A1A1E **5.24**｜chatBubbleUser #5A5A62 白字 **6.83**｜warning #D2A56D **7.72**｜success **5.60**｜info **6.88**｜error **5.66**｜taskReflection **5.64**｜taskPlanning **5.80**｜planSprint **5.82**｜planGrowth **5.53**｜learningDark **9.02**｜trainingDark **10.02**｜errorFixDark **6.25**｜reflectionDark **4.88**｜planningDark **7.11**｜social **9.94**｜ocr **5.18**｜statusOnline **8.25**。暗色全数 ≥4.5，无退化。

浅色联动正向收益：DS 派生色（`primaryDark`、`warningLight` 等 shift 派生）自动跟随；`ThemeUtils.getContrastSafeText(brandPrimary)`（DS.textOnPrimary）从"fallback 分支"变为确定性白字。

---

## 4. 设计决策存档

1. **加深 base 优先于 onBrand 令牌**（本批）：使用面审计 + 单点传导 + 双向修复（见 §2.1）。onBrand/onContainer 前景对是批次 2 结构件，届时 pill 文字改用配对前景，可同时消化 §1 的 tint 边缘豁免。
2. **绑定容器集口径**：按"文字真实落点"而非"一切可想象底色"校准。tertiary-tint 落点（4.07–4.58）记录为批次 2 container 对的验收项，而非本批的隐藏失败。
3. **hue 保全优先**：每个新值都在原 hue 上加深（雾蓝仍雾蓝、琥珀仍琥珀），移动 ≤1.5 档明度；暗色侧一律原值保留。
4. **收敛优于独特**：同 hue 双源值统一，服务批次 2 的删源合并（结构不动，数值先行铺路）。

---

## 5. 改后对比度速查表（验收用）

### 5.1 浅色 normal——文字角色（加粗为绑定集最差点，全部 ≥4.5）

| 令牌（新值） | white | ambient | primary | secondary | bubbleOther | 白/ambient/primary tint（最差） | secTint* | terTint* | 白字on它 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brandPrimary #825D49 | 5.82 | 5.50 | 5.31 | 4.91 | 5.13 | **4.66** | 4.34 | 3.88 | 5.82 |
| semanticSuccess #456E52 | 5.82 | 5.51 | 5.32 | 4.92 | 5.13 | **4.68** | 4.32 | 3.89 | 5.82 |
| semanticWarning #7D5C26 | 6.12 | 5.79 | 5.59 | 5.17 | 5.40 | **4.90** | 4.55 | 4.07 | 6.12 |
| semanticError #A0483E | 6.02 | 5.69 | 5.49 | 5.08 | 5.30 | **4.78** | 4.45 | 3.98 | 6.02 |
| semanticInfo #48678D | 5.83 | 5.52 | 5.33 | 4.93 | 5.14 | **4.67** | 4.34 | 3.89 | 5.83 |
| taskLearning =info | 5.83 | 5.52 | 5.33 | 4.93 | 5.14 | **4.67** | 4.34 | 3.89 | 5.83 |
| taskTraining =warning | 6.12 | 5.79 | 5.59 | 5.17 | 5.40 | **4.90** | 4.55 | 4.07 | 6.12 |
| taskErrorFix =error | 6.02 | 5.69 | 5.49 | 5.08 | 5.30 | **4.78** | 4.45 | 3.98 | 6.02 |
| taskReflection #6C5C92 | 5.86 | 5.54 | 5.35 | 4.95 | 5.17 | **4.70** | 4.37 | 3.91 | 5.86 |
| taskSocial =success | 5.82 | 5.51 | 5.32 | 4.92 | 5.13 | **4.68** | 4.32 | 3.89 | 5.82 |
| taskPlanning #426D77 | 5.70 | 5.39 | 5.20 | 4.81 | 5.02 | **4.56** | 4.24 | 3.81 | 5.70 |
| planSprint =error / planGrowth =success | 同 semanticError/Success 行 | — | — | — | — | — | — | — | — |

\* secTint/terTint = 10% tint 叠 surfaceSecondary/tertiary：批次 2 container 对的验收线，本批豁免口径见 §1。

### 5.2 浅色 normal——TaskColors pill（label on 10% tint）

| 任务 | 白 tint | ambient tint | primary tint | secTint* |
| --- | --- | --- | --- | --- |
| learning #175FB0 | 5.49 | 5.21 | 5.04 | 4.67 |
| training #8E4E00 | 5.59 | 5.32 | 5.11 | 4.76 |
| errorFix #B0312A | 5.40 | 5.13 | 4.95 | 4.59 |
| reflection #9C27B0 | 5.37 | 5.11 | 4.96 | 4.57 |
| social #755F00 | 5.37 | 5.11 | 4.93 | 4.58 |
| planning #00695C | 5.69 | 5.42 | 5.21 | 4.84 |
| ocr #4F6572 | 5.33 | 5.07 | 4.89 | 4.55 |

### 5.3 聊天 / 状态 / 文字基线

| 组合 | 比值 | 标准 |
| --- | --- | --- |
| 白字 on chatBubbleUser #566C8C（浅） | **5.36** | 4.5 ✓ |
| chatBubbleOtherText #171717 on #F5F0E8 | 15.80 | 4.5 ✓ |
| 白字 on 暗色气泡 #5A5A62 | 6.83 | 4.5 ✓ |
| statusOnline #189150 作圆点（浅，全表面含 tertiary） | 3.04–4.03 | 3:1 ✓（禁作文字） |
| statusOffline #95A5A6 圆点 on white | 2.56 | 图形线边缘，批次 2 记录 |
| textSecondary #6C655D on primary | 5.24 | 4.5 ✓ |
| textDisabled #A49B90 | 2.50 | 禁用豁免 |
| brandPrimary on neutral200 | 5.09 | 4.5 ✓ |

### 5.4 暗色 normal（未改动，复核记录）

textPrimary 15.39｜textSecondary 8.16｜brandPrimary 5.24｜brandSecondary 5.31｜success 5.60｜warning 7.72｜error 5.66｜info 6.88｜task* 4.88–10.02｜plan* 5.53/5.82｜气泡 6.83/12.68｜statusOnline 8.25——全部 ≥4.5。

---

## 6. 残留与移交（不在本批边界）

| 项 | 现状 | 去向 |
| --- | --- | --- |
| brandSecondary #7A8BA6（浅） | white 3.46 / primary 3.16 / secondary 2.92：装饰/渐变用途为主，作图形在 secondary 上未过 3:1 | 批次 2：随 onBrand/四件套校准（未在本批点名清单内，不动） |
| tint 叠 secondary/tertiary 边缘带（4.07–4.58） | §5 表逐色列出 | 批次 2 container 对令牌验收项 |
| 浅色 colorBlindFriendly 档 | warning 2.06 / taskPlanning 2.11 / taskReflection 2.80 / taskSocial 3.12（brandPrimary 4.74 ✓） | 批次 2：CB 档整套重校（Wong palette 需换深变体，属调色板结构工作） |
| textTertiary 派生值（~2.9:1） | `textSecondary α0.6` 派生，非静态令牌 | 批次 2 静态化时校准 |
| TaskColors 饱和值 features 层硬编码副本 10 处 | 64B5F6×2、FF9800×5、EF5350×2、009688×1 | 批次 3+ 模块横扫（随删源收编） |
| `userChatBubbleGradient` 起点 brandSecondary | 零消费死令牌 | 批次 2 删除或重定义 |
| statusOffline 圆点 2.56 | 图形线边缘 | 批次 2 状态色族校准一并处理 |

## 7. 验证

- 对比度：Python 脚本实算（本文全部数值同一脚本产出；与 Flutter `computeLuminance` 同公式口径）。
- `flutter analyze` 全量一次（6800 条均为库存量 info，集中于 third_party_plugins vendored 目录）；三个改动文件定向 `dart analyze` → **No issues found**。
- 未跑 flutter test（资源纪律）；视觉终验随 L2/L3 截图波做 pill/气泡实机目检（round1-L1 §6 交接项已列）。
