# UIUX Round 1 — L1 设计系统地基审查报告

> 审查员：Aurelia（设计系统/视觉方向）
> 日期：2026-09-18 ｜ 基线：wt3 @ ca86bda8（只读审查）
> 范围：`mobile/lib/core/design/` 全目录 + 组件/关键 screen 抽查 + 全库硬编码统计
> 方法：纯代码级审查（本波不跑 flutter）；对比度按 WCAG 2.x 相对亮度公式实算

---

## 0. 一句话总评

**有系统之形，无系统之治**：Sparkle 拥有超出参赛项目平均水平的令牌骨架（6 套调色板、暗色/高对比/色盲三机制、Material 组件主题映射齐全），但同一语义存在 2-4 个并行事实源（任务色、品牌色、字阶、动效、按钮各有多套），且核心可达性指标（浅色模式文字对比度）系统性不达标——系统没有被"当成法律"执行。

**设计系统成熟度：4.5 / 10**
（骨架 7 分：暗色机制、ThemeManager、组件主题映射、验证工具意识；治理 2 分：多事实源、守卫未接线、入口不唯一；可达性 3 分：机制在但数值失败。）

---

## 1. 统计口径声明（重要）

本报告独立统计（`mobile/lib` 排除 `core/design/` 与 `*/gen/`，grep 原始匹配）：

| 指标 | 本波实测 | 已钉棘轮基线 | 差异说明 |
| --- | --- | --- | --- |
| 硬编码 `Color(0x…)` | **718 处 / 49 文件** | 243 处 / 32 文件 | 棘轮口径更窄（疑似仅 `const Color(0xFF` 或仅 features/），**棘轮脚本在 wt3 不可发现**，口径不可复现——本身是治理缺陷，见 P1-8 |
| 硬编码 `fontSize: N` | **790 处**（含 core/design 则 1475） | 884 处 | 大体一致，差异来自正则细节 |
| 硬编码中文（features 等） | 343 文件量级（含注释） | 1712 行 / 163 文件 | 棘轮口径疑似仅 UI 字符串行 |

**行动建议**：令牌化迁移第一步不是改代码，而是把棘轮统计脚本固化入库（可复现的正则 + 排除清单），否则"只降不升"无法被门禁执行。

---

## 2. A1 令牌体系盘点

### 2.1 实际存在的六层结构（问题：层与层互相竞争）

| 层 | 文件 | 内容 | 状态 |
| --- | --- | --- | --- |
| 权威调色板 | `tokens_v2/theme_manager.dart` | SparkleColors 35 个语义色 × **6 套调色板**（light/dark × normal/highContrast/colorBlindFriendly）；SparkleTypography 8 角色；SparkleSpacing 7 档；SparkleAnimations；SparkleShadows ×2 | **健康，是全系统最好的资产** |
| 静态门面 | `design_system.dart` | `DS` 类 300+ getter：~80 个 alpha 变体色、假 Material shade（50-900）、圆角、间距数字别名、图标尺寸、第三套字阶、稀有度/连胜色 | 便利层已膨胀为第二事实源 |
| 上下文扩展 A | `design_system.dart:479-525` | `context.sparkleColors / .sparkleTypography / .sparkleSpacing / .sparkleTheme` | 与扩展 B 职责重叠 |
| 上下文扩展 B | `theme/sparkle_context_extension.dart` | `context.sparkle.colors/.typo/.space/.radius/.motion/.taskColors` + SparkleRadius（4/8/12/16/20/999）+ SparkleMotionTokens | 与 A 并存，两套词汇表指同物 |
| 领域色残留 | `color_extensions.dart` | SemanticColors：**~80 个硬编码 hex**（brandOrange/brandBlue、agent 9 色、intent 8 色、sector 14 色、achievement 4 色、template 4 色、chatMode 4 色…）+ 6 个全局 switch 函数 | 讽刺：文件自述"以替代硬编码颜色值"（`:3`），自身是设计系统内最大硬编码源（108 处） |
| 二号任务色源 | `tokens/task_colors.dart` | TaskColors 7 色（含 ocr），自述"Single source of truth… DO NOT define task colors elsewhere"（`:7-8`） | **与 SparkleColors.task* 直接冲突**（见 P0-2） |

另有三套动效系统并存：`SparkleMotion`（motion.dart，5 时长 6 曲线）、`AnimationSystem`（animation_token.dart，9 时长）、`DS.motionDuration/SparkleMotionToken`（design_system.dart:1076-1117）。同名令牌数值冲突：`normal` 在 SparkleAnimations=180ms，在 AnimationSystem=250ms；`slow` 260ms vs 400ms。

### 2.2 缺失的令牌

| 类别 | 缺口 | 后果证据 |
| --- | --- | --- |
| **前景对（onXxx）** | 无静态 `onBrandPrimary / onSuccess / onWarning…`，全部运行时 `ThemeUtils.getContrastSafeText` 现算 | 设计稿不可对齐；pills 干脆放弃计算直接拿底色当文字色 → 对比度失败（§2.4） |
| **容器色三件套** | 无 `xxxContainer / onXxxContainer / xxxBorder`，各组件现场 `.withValues(alpha: 0.1/0.3)` | 魔法数 0.1/0.3 在 `task_pill.dart:40-68`、`semantic_pill.dart:25-75`、`design_system.dart:714-716` 三处重复 |
| **情绪/温度语义层** | 无 calm/celebrate/encourage 等情绪令牌；`adaptive/emotion_responsive_theme.dart`（低刺激模式：减动效、降温色、藏挑战徽章）**定义了但全库零消费（死代码）** | "有温度的学习伙伴"定位在令牌层无承载体； streak/rarity 色是硬编码 const 不随主题（design_system.dart:1214-1284） |
| **焦点/触摸态令牌** | focusColor 只在 ThemeData（alpha 0.18），无组件级 focus token；键盘导航可视性依赖 Flutter 默认 | 键盘/外接输入场景（web 端）焦点可见性不可控 |
| **阴影/模糊强度令牌** | SparkleShadows 有 3 档，但全库手写 `BoxShadow(` 208 处、`ImageFilter.blur` 15 处 | 高光溢出、暗色阴影过重无统一调节点 |
| **divider/border 可见性** | `borderDefault = neutral200`（浅色 #F4EFE9），画在 `surfaceSecondary`（#F1EBE4）上**近似隐形**（对比 ~1.02:1） | SparkleCard 边框失效 → 界面靠 208 个手写阴影补偿边界感（P1-4） |
| **TextTheme 完整映射** | `_buildTextTheme` 只映射 8 角色（design_system.dart:343-358），缺 displayMedium/Small、titleMedium/Small、bodySmall、labelMedium | 未映射处回落 Flutter 默认字阶 → 实际渲染混入第三种字体尺度 |

### 2.3 令牌质量

**命名一致性（差）**
- 同一含义 3 种拼写：`brandPrimary10` / `brandPrimary100` / `brandPrimary10Const`（design_system.dart:702-735）；且 `*Const` 后缀实为 getter 并非 const，命名撒谎。
- **假 shade 语义反直觉**：`brandPrimary50…900` 全是 alpha 伪装（`:719-728`），且 600-900 是"越号越透明"，与 Material shade 心智相反；`error900 == error`、`brandPrimary900 == brandPrimary`。迁移者按 Material 直觉用色必错。
- 别名泛滥：`surface == surfaceBase == surfaceHigh == surfaceSecondary`（`:673-677`）；`DS.md == DS.spacing16 == 16`（间距双命名并行，`:976-998`）。
- 陷阱命名：`neutral0` 在暗色返回浅米色 #F4F1EB（`:1178`）；`CustomButton` 拿 `DS.neutral0.withValues(alpha: 0)` 当"透明"用（custom_button.dart:280 等 5 处）。
- `textTertiary` 是派生值非真令牌（`textSecondary α0.6`，`:682-683`），浅色实对比 ~2.9:1，作 caption AA 失败。

**暗色模式（机制优，覆盖不全）**
- 机制完备：ThemeManager 持久化 + `didChangePlatformBrightness` + 6 套调色板，`app/app.dart:83-85` 正确接线 light/darkTheme。这是亮点。
- 但覆盖断层：SemanticColors 60+ 色、TaskColors.social、rarity 全系、streak 全系、agent/intent/sector/template 不随暗色（或仅 brightness 二分）；highContrast/colorBlindFriendly 只在 SparkleColors 圈内生效，color_extensions.dart 的 `isHighContrast` 标志仅影响 4 个 adaptive getter。

**可访问性基线（数值实算）**

浅色模式（#F8F4EF 底）大面积不达标：

| 色 | 用途 | 对比度 | WCAG |
| --- | --- | --- | --- |
| brandPrimary #A77D63 | 文字/图标（pill、按钮文字） | **3.33:1**（on surfaceSecondary 3.08） | 12-14px 文字 AA 需 4.5，**失败** |
| TaskColors.learning #64B5F6 | 任务标签文字 | **2.02:1** | 严重失败 |
| TaskColors.social #FFB703 | 任务标签文字 | **1.59:1**（近不可读） | 严重失败 |
| semanticWarning #C59A67 | 文字 | **2.34:1** | 失败 |
| statusOnline #2ECC71 | 文字 | 1.92:1 | 失败（作圆点可，作文字不可） |
| chatBubbleUser 白字 on #6B82A0 | 聊天气泡 14px | **3.94:1** | AA 失败 |
| textDisabled #A49B90 | 禁用文字 | 2.50:1 | 禁用态豁免，可接受 |

暗色模式整体健康（brandPrimary 5.24、textSecondary 8.16、success 5.60）——**问题是浅色模式，不是暗色**。

字号：最小正文字阶尚可（bodyMedium 14/1.62），但实际代码 `fontSize: 10`×106、`11`×126、`12`×205——**10/11px 共 232 处**，突破移动可读底线；pill 类组件 12px + 低对比色双重伤害（`ai_status_capsule.dart:67`、`compact_error_card.dart:28`）。

触控目标：`DS.touchTargetMinSize=48` 且 SparkleIconButton 接入 accessibility provider（sparkle_button_v2.dart:398-428）——合格。

### 2.4 组件一致性抽查（10 项）

| # | 组件 | 发现 | 证据 |
| --- | --- | --- | --- |
| 1 | **按钮** | **3 套并行**：SparkleButton v2（270 处使用，radius 8、InkWell、Semantics、14px）；CustomButton（59 处，radius 12、渐变、**GestureDetector 无 ripple 无语义**、字号 16-25px）；裸 Material Button（196 处）。`enum ButtonVariant` 在两个文件定义两次且枚举值不同 | sparkle_button_v2.dart:267-269 / custom_button.dart:204,241-250,8-13 / grep 计数 |
| 2 | **pill/chip** | TaskPill 与 SemanticPill 逻辑 90% 重复（两个 6 值 tone 枚举 TaskPillTone/PillTone 互不相认）；AiStatusCapsule 又是第三种形态（radius 8 非 pill、裸 fontSize、裸 padding）；**features 层另有 439 个本地 Button/Pill/Chip/Card/Tag 类** | task_pill.dart:8 / semantic_pill.dart:11 / ai_status_capsule.dart:43,67 |
| 3 | **卡片** | SparkleCard（borderDefault 隐形边框 + radius 12）vs CardTheme（surfaceTertiary@0.85 可见边框 + radius 22）：同为"卡片"两种边界、两种圆角 | sparkle_card.dart:29-32 / design_system.dart:360-371 |
| 4 | **对话框** | DialogTheme radius 24 vs confirmation_dialog radius 8 vs chat 内手写 28：同语义三种圆角 | design_system.dart:174-184 / confirmation_dialog.dart:41 / chat_bubble.dart:676 |
| 5 | **输入框** | InputDecorationTheme 完整（radius 18、focus 2px 品牌色）——但登录页 `border: const OutlineInputBorder()` 局部覆盖把圆角打回默认 4px，**第一印象表单与全 app 不一致** | design_system.dart:404-455 / login_screen.dart:141,156 |
| 6 | **Loading** | SparkleLoadingIndicator 存在，`CircularProgressIndicator` 裸用 85 处 | grep 计数 |
| 7 | **空状态** | EmptyState 组件存在，但 dashboard 就地造 4 种私有空态（_buildFirstGoalEmptyState/_buildSlotEmptyCta/_buildEmptyDashboardCta/_HomeEmptyInline） | dashboard_screen.dart:395,873,937,1902 |
| 8 | **错误呈现** | 4 套：error_widget（大卡+2xl 图标）/ compact_error_card（12px 裸字号）/ AppFeedback.error（snackbar）/ _HomeErrorCard（dashboard 私有） | error_widget.dart:260 / compact_error_card.dart:28 / dashboard_screen.dart:1840 |
| 9 | **聊天气泡** | chat_bubble.dart **3666 行单文件巨石**；整体走 DS 令牌（好），但混入 fontSize:10 时间戳、brandPrimary 作气泡文字（3.33:1） | chat_bubble.dart:1394,1079 |
| 10 | **底部导航** | NavigationBarTheme 集中配置（72 高、指示器、双态字重）——集中管理良好（正面样本）；但 6 处 features 自绘导航变体待 L3 核验 | design_system.dart:285-308 |

**组件层结论**：`core/design/components/` 与 `core/design/widgets/` 两个组件目录并存本身就是历史断层（atoms v2 vs legacy widgets），组件不是缺，是**同一语义多胎生育且无人收编**。

---

## 3. B 视觉气质评估（Design Director 视角）

目标气质：精致、有温度的学习伙伴。现有令牌的"底色审美"其实是好的——暖米色纸感 surface + 低饱和学术色板，方向对。伤气质的是以下 5 点（按伤害排序）：

### 3.1 品牌人格分裂：用户看到的第一屏品牌不在令牌系统里
SparkleColors 的品牌是 #A77D63 暖棕 + #7A8BA6 雾蓝（温暖学术）；而登录页品牌标用 SemanticColors 里孤立的 #D9773A 亮橙 + #4C78B2 促销蓝渐变。**用户认识产品的第一个 3 秒，看到的不是产品真正的品牌色**。两种人格：纸感书院 vs 应用商店促销页。
证据：`login_screen.dart:24-27,317-351,377-381`；`theme_manager.dart:507-508`；`color_extensions.dart:123-132`。

### 3.2 主色无力：精致被做成了"没有主张"
brandPrimary 3.33:1 的对比度决定了它撑不起任何关键行动点。CustomButton 的 primary 是"近乎背景色的微渐变 + 棕字"（custom_button.dart:266-297），视觉重量反而低于满屏的装饰卡。与之相对的是全库 345 处 LinearGradient、208 处 BoxShadow、52 处 Confetti、459 处 particle、416 处 glow——**装饰的对比度远高于信息的对比度**。温度感来自克制的强调，不是来自特效总量。

### 3.3 微观字号泛滥：温度变成吃力
10/11/12px 共 536 处。给大学生的产品把时间戳做到 10px（chat_bubble.dart:1394）、把成就说明做到 11px——"有温度"的前提是不让用户眯眼。小字号 + 低对比（§2.3）是双重扣分。

### 3.4 任务色板精神分裂：同一"学习任务"两副面孔
muted 学术系（SparkleColors.taskLearning #7893B2）与饱和 Material 系（TaskColors.learningLight #64B5F6）描述同一个概念。首页用一套、任务 pill 用另一套时，产品的色彩语言失去口音一致性；且后者当文字色 1.59-2.02:1 近乎不可读。
证据：`theme_manager.dart:524-531` vs `task_colors.dart:55-74`；消费点 `task_pill.dart:72-78`。

### 3.5 "低刺激学习伴侣"的产品意图存在于代码却从未出生
`emotion_responsive_theme.dart` 精确定义了 lowStimulus 模式（减动效、降色温、藏挑战徽章）——这正是"有温度"该有的机制，但全库零消费。同时治理工具 `design_system_linter.dart` / `design_validator.dart` 也零消费。**产品里最有个性的两个系统都是孤儿**。气质问题本质是治理问题。

---

## 4. C 令牌化迁移蓝图

### 4.1 目标令牌清单（v3 增量，建在 SparkleColors/SparkleThemeExtension 上）

**色彩（每语义色四件套：base / container / onContainer / border）**
```
brand:      brandPrimary, brandContainer(≈现 alpha 0.1), onBrand, brandBorder(≈0.3), brandSecondary 同构
semantic:   success/warning/error/info × 四件套（替代全部现场 .withValues(alpha:…)）
text:       textPrimary/Secondary/Tertiary(静态化)/Disabled + onSurfaceVariant
surface:    现有四级 + surfaceHover/Pressed + divider(独立可见性校准) + scrim
focus:      focusRing(宽+色)
reward 领域层: rarity*/streak*/achievement* 收编进 palette（补 dark/light 变体，消灭 const 硬编码）
galaxy 领域层: galaxy*/sector* 集中到 tokens/galaxy_palette.dart（保留领域色但唯一出处 + 主题感知）
```

**字阶（单一事实源）**：SparkleTypography 扩到 15 角色补齐 TextTheme 映射；TypographySystem 废弃（或降为 ratio 实现细节）；`DS.fontSize*` 全部 @Deprecated；硬下限：正文 ≥14，元数据 ≥12（10/11px 全部归并 12），label 类一律 labelSmall + onSurfaceVariant。

**间距**：7 档为准；新增 `gapSm=12` 第 8 档（承认 12pt 现实，替代"sm+xs 组合"教条）；废弃 spacing2..spacing64 数字别名与 SpacingSystem。

**圆角**：收敛 4/8/12/16/20 + full 六档；19 种实测值就近映射（7→8、10→12、14→12 或 16、18→16、22/24→20 或组件级 dialog 常量、2/3/4→4、99→999）。dialog 24 / bottomSheet 28 作为组件级常量留在主题内。

**动效**：三合一到 SparkleMotionTokens 门面：时长 5 档（120/180/250/400/600）+ 曲线 4 档（standard/enter/exit/overshoot）+ reduceMotion 全局短路（现 `context.reduceMotion` 已有两份重复实现，合并为一）。

**入口纪律**：唯一入口 `context.sparkle.*`；`DS` 保留为 deprecated 兼容 shim（内部转发，不再新增）；`SparkleContext`(design_system) / `SemanticColors` / `TaskColors` / `AppColors`(app/theme.dart) 排期删除。

### 4.2 映射规则（硬编码值 → 目标令牌的归类法）

1. **语义匹配**：色相落入 success/warning/error/info 扇区 → 映射对应 container/onContainer 对（如 0x33 + 绿系 → successContainer）。
2. **中性灰阶**：按 HSL 亮度 + 所在主题分 neutral/surface/text 层级。
3. **品牌渐变对**：成对出现的 brand 渐变 → 固定为 `brandGradient` 组合令牌，禁止逐色引用。
4. **领域专属色**（galaxy/sector/agent/intent/rarity）：不强行语义化，集中到领域 palette 文件 + 补齐暗色变体，先"唯一出处"后"语义化"。
5. **fontSize**：`≤12→12（labelSmall）/ 13,14→14 / 15,16→16 / 18,20→18 / 22-28→24 / ≥32→30+`，codemod 脚本 + `flutter analyze` 门禁双保险。
6. 生成一份脚本产出的「hex→token 映射表」入库（HSL 最近邻 + 人工白名单复核），作为各批 PR 的查表依据，同时就是棘轮守卫的 ban-list。

### 4.3 分批策略：按「模块 × 全令牌类型」纵切，不按令牌类型横切

- **理由**：同一模块被色/字/距三轮改三次，review 与回归成本三倍；纵切一次到位，且棘轮按模块清零直观。
- **批次 0（地基，1 个 PR）**：固化棘轮脚本入库（可复现口径）+ v3 令牌增量落地 + 守卫接 CI。不动任何业务代码。
- **批次 1（P0 修复，2-3 个 PR）**：浅色调色板对比度修复（brandPrimary 调深至 ≥4.5 或引入 onBrand 深棕；TaskColors 对齐 SparkleColors 并加 dark 变体）+ pill/气泡文字色改 onContainer。**先修数值后删代码，风险最低。**
- **批次 2（收编双源）**：删 TaskColors/SemanticColors/AppColors，调用点机械替换。
- **批次 3-6（模块横扫，每批 ≤15 文件 / ≤400 diff 行）**：auth/home/chat/task → plan/calendar/insights → settings/user/community → 长尾 + galaxy 领域收编。core/design 自身（1475 处 fontSize 的大头在本目录）单独立一批。
- **每批验收**：棘轮计数不升（目标：该模块三项计数归零）+ `flutter analyze` + 该模块关键屏截图目检（可延至平台实测波统一做）。

### 4.4 与 i18n 批次的编排

l10n 基建已存在且部分落地（`l10n.yaml` + `lib/l10n/app_zh.arb` 约 16.6k 行，94 个 feature 文件已用 AppLocalizations）。建议：

1. **先 i18n，后令牌化**（同模块内先后脚、两个独立 PR）：i18n 是纯字符串机械抽取、不动布局、可脚本辅助、风险低——先做可让中文棘轮先钉住；令牌化涉及视觉回归，若先做，i18n 抽取会造成截图基线二次失效。
2. 同一模块「i18n PR 合入 → 令牌化 PR 立即跟进」，上下文连续，避免跨模块切换成本。
3. 抽词时优先复用 generic key（emptyState.generic、action.retry 等），防止 arb key 爆炸；`check_hardcoded_strings.sh` 现有正则 `\u4e00-\u9fa5` 在 grep 中不生效（POSIX grep 不认 \u 转义），守卫本身需要修复——并入批次 0。

---

## 5. D 分级发现汇总

### P0（系统性缺陷，阻塞气质与可达性底线）

| # | 发现 | 证据 | 修复建议 |
| --- | --- | --- | --- |
| P0-1 | **浅色模式文字对比度系统性不达标**：brandPrimary 3.33、任务色 1.59-2.02、warning 2.34、气泡白字 3.94 | §2.3 表；task_pill.dart:77；chat_bubble.dart:1079 | 浅色 brandPrimary 调深（如 #8A6248 一档）或所有彩色文字改 onContainer 静态令牌；TaskColors 浅色系全部重校 ≥4.5 |
| P0-2 | **双事实源**：TaskColors vs SparkleColors.task*（色值相悖、类型数不同）；SemanticColors.brandOrange/Blue vs SparkleColors.brand*（登录页品牌分裂） | task_colors.dart:7,55-74；theme_manager.dart:524-531；login_screen.dart:24-27 | 删 TaskColors；登录页品牌标改用 SparkleColors.brand*；SemanticColors 并入 SparkleColors 或降级为 galaxy 域 palette |
| P0-3 | **字阶三体系冲突**：SparkleTypography（14 body）vs TypographySystem（16 body，DS.displayLarge 实为 48.8px）vs DS.fontSize*（fontSizeSm 14→16 冲突已致 deprecated）；TextTheme 只映射 8 角色 | design_system.dart:1049-1052,343-358；typography_token.dart:13-21 | 单一源 + 补齐映射 + DS 字阶全 deprecated（§4.1） |

### P1（重大，伤害一致性与可维护性）

| # | 发现 | 证据 | 修复建议 |
| --- | --- | --- | --- |
| P1-4 | 浅色卡片边框隐形（borderDefault=neutral200 on surfaceSecondary ≈1.02:1），界面被迫靠 208 处手写阴影撑边界 | sparkle_card.dart:32；theme_manager.dart:746 | 引入独立 border/divider 令牌并按可见性校准（≥1.15:1） |
| P1-5 | 组件多胎生育：按钮 3 套（196 处裸 Material 按钮）、pill/Chip features 层 439 个本地类、错误呈现 4 套、空状态就地造 | §2.4 #1/2/7/8 | 收编目录（components/atoms 为唯一出产地）；按使用频次先收按钮与 pill；196 处裸按钮逐步换 SparkleButton |
| P1-6 | 圆角 19 种实测值；间距双命名；DS 别名泛滥（surface/surfaceBase/surfaceHigh 同值） | §2.2/§2.3；grep 圆角分布 | §4.1 收敛表 + codemod |
| P1-7 | 假 shade（alpha 冒充 50-900，600-900 方向反直觉）+ `*Const` 命名撒谎 | design_system.dart:702-747 | 删除假 shade 层，改 container 对；文档明示 |
| P1-8 | 治理工具全部孤儿：design_system_linter / design_validator / emotion_responsive_theme 零消费；棘轮脚本在库内不可发现 | grep 证据 §3.5 | 批次 0 接线：守卫进 `run_all_rule_guards.sh`，口径固化 |
| P1-9 | 无障碍机制不贯通：SemanticColors/TaskColors/rarity/streak 不响应 highContrast/colorBlindFriendly | color_extensions.dart:44-69 | 域色并入 palette 六套体系，或明确豁免并文档化 |

### P2（打磨项）

| # | 发现 | 证据 | 修复建议 |
| --- | --- | --- | --- |
| P2-10 | 登录表单局部覆盖 InputDecorationTheme，圆角 4 打破 18 的全 app 语言 | login_screen.dart:141,156 | 删除局部 border，吃主题默认 |
| P2-11 | 10/11px 共 232 处；AiStatusCapsule 裸样式（12px 彩字 3.10:1）；CustomButton large 25px 文字、无 ripple 无 Semantics | chat_bubble.dart:1394；ai_status_capsule.dart:67；custom_button.dart:241-250 | 随模块横扫归并；AiStatusCapsule 改走 pill 体系 |
| P2-12 | chat_bubble.dart 3666 行巨石（可维护性 + 视觉回归粒度过粗） | wc -l | 拆气泡/操作条/长按菜单三个子组件，随 chat 批次 |
| P2-13 | core/design 无 README，权威入口（context.sparkle）不可发现，两套 context 扩展并存 | 目录清单 | 补 design/README.md：入口、令牌清单、禁用清单 |

---

## 6. 为后续波铺路的交接项

- **L2/L3 截图波重点核验**：浅色模式下任务 pill 可读性（P0-1 的实机表现）、登录页品牌观感（P0-2）、卡片边界感（P1-4）、10/11px 实机阅读体验。
- **棘轮基线换算**：本波口径（§1）建议作为新棘轮基线（718/790/1712），旧 243/884 基线口径需在批次 0 重新钉死并入库脚本。
- **正面资产**（后续波不要破坏）：6 套调色板机制、NavigationBarTheme 集中配置、SparklePressable 触控目标自适应、login/i18n 部分落地、85 处 CircularProgressIndicator 背后的 loading 意识（收编而非抹除）。
