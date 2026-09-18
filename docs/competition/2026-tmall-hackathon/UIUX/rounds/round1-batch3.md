# Round 1 · 批次 3 — 入口统一 + 孤立色清零 + W-7 中文优先

> 上游：`round1-batch2-single-source.md` §6 移交表 + web 走查 W-7 发现。
> 本批边界：**双 `colors` 入口统一、`sparkleTypography` 收编、AppColors/SemanticColors ~76 色处置、
> container/decor 四件套收敛、W-7 三项（locale/品牌标/表单宽）**。
> 基线：main `6d0643e9`（批次 2 已落）。wt3 残留为批次 2 未清理的工作区副本（经 diff 比对与
> 6d0643e9 内容一致），已重置到 6d0643e9 后开工。
> 纪律：零构建；`flutter pub get` 仅依赖解析；定向 `flutter test` 仅限本批触及的可测逻辑
> （i18n 回退链 + 测试文件重定向批）；`lib/gen`（gitignore 产物）从主 checkout 复制以支持定向测试。

---

## 0. 结果速览

| 指标 | 值 |
| --- | --- |
| 改动 | 115 文件（含本记录文档），+771 / −1374（净 −603）；其中代码与 README 114 文件，+599 / −1374（净 −775） |
| 删除文件 | `app/theme.dart` 整文件（−561：AppColors + AppThemeExtension + 弃用 AppThemes） |
| 入口收敛 | `context.colors` **2 → 1**（SparkleColorAliases 门面退役）；`context.typo` 唯一入口（`sparkleTypography`/`sparkleSpacing`/`sparkleAnimations`/`sparkleShadows`/`sparkleColors` 五 getter + 重复 `reduceMotion` 全删） |
| 迁移调用点 | 入口统一 93 文件（typo 292 处/52 文件、colors 21 处、space 6 处、shadows 3 处、显式消歧 3 处、facade 方法转发消费 1 处补扫） |
| 孤立色清零 | SemanticColors **69 成员全删**（65 零消费实证 + 4 活消费迁单一源）；死函数 ×2 删；4 组领域调色板收编为单一拷贝；AppColors 25 getter（0 消费）随文件删除 |
| 四件套 | 边框 ×3 + 容器面 ×6 派生公式上收 SparkleColors（值恒等），DS 全部转转发；shadowPrimary 死令牌删 |
| W-7 | locale zh 默认/回退链落位；登录页字阶上令牌；表单 ≤480 约束（DS.contentMaxWidthForm） |
| 验证 | 全仓 `flutter analyze` **0 error / 0 warning**；旧符号 grep 零代码残留（仅出处注释）；UI-TOKENS 棘轮 **PASS（color=275/275, fontSize=727/727）**；定向测试：i18n 13/13 绿，重定向批 25 绿 + 3 失败经 stash 基线复核为**存量失败**（与本批无关） |

---

## 1. 裁决一：双 `colors` 入口统一（batch2 §6 撞线项）

**裁决：`SparkleContextExtension.colors`（theme/sparkle_context_extension.dart，真 palette）为唯一入口。`SparkleColorAliases` 门面退役，整类删除。**

依据：批次 2 在 task_pill/login_screen 实际撞出 `ambiguous_extension_member_access`，靠显式扩展调用临时消歧（`task_card.dart:775` 先例）——双入口不是理论问题，是已发生的编译冲突。门面 9 个成员全部是 palette 直转或已废弃的语义（`surfaceCard` 等三个别名槽是「卡片该用什么底色」的第二套词汇，正是 L1 §2 批评的别名熵）。

### 1.1 迁移表

| 旧入口/门面成员 | 处置 | 规模 |
| --- | --- | --- |
| `SparkleContext.colors`（门面 getter） | 删除；`context.colors` 从此唯一指向 SparkleColors | — |
| `SparkleColorAliases` 类（9 成员） | 整类删除 | −18 行 |
| `context.colors.surfaceCard` | → `context.colors.surfaceSecondary`（值恒等） | 3 处 |
| `context.colors.getPlanColor`（facade 方法转发） | 同名存在于 palette，补 extension import 即收敛 | 1 处（补扫捕获） |
| `context.colors.textPrimary/textSecondary/border` | 同名收敛于 palette（`border` 为案四新增 getter，值恒等） | 8 处 |
| `context.sparkleColors` | → `context.colors` | 17 处 / 7 文件 + 1 测试 |
| 显式消歧 `SparkleContextExtension(context).colors` | 简化为 `context.colors`（task_pill / login_screen / task_card） | 3 处 |
| design_system_linter 硬编码色豁免名单 | `sparkleColors` → `context.colors`（死豁免换新守卫位） | 2 处 |

### 1.2 重复 `reduceMotion` 一并收敛

design_system 与 sparkle_context_extension 两个扩展都定义了 `reduceMotion`——入口统一后所有文件将同时 import 两者，这是下一个必撞的歧义点，属同一案的本质（同名双入口）。删除 design_system 侧（实现逐字相同），10 个消费文件随 import 补齐落到扩展侧。

### 1.3 行为变化

无。门面所有消费点的值在 palette 上逐一同名/同值（`surfaceCard==surfaceSecondary` 等均为门面自身的直转定义）。task_pill/login_screen/task_card 的显式消歧代码删除后编译行为不变——这正是「入口已唯一」的可执行证明。

---

## 2. 裁决二：`context.sparkleTypography` 收编（batch2 §6 移交项）

**裁决：`SparkleTypography` 的唯一 context 入口是 `context.typo`。design_system 的 `sparkleTypography` getter 删除，全量迁移。**

依据：batch2 已把样式唯一事实源收敛到 `SparkleTypography`（DS 字阶全部 deprecated shim 转发），但 context 层仍留两个名字指向同一来源——入口双源是 batch2 未竟的另一半。batch2 移交表记「3 个 feature 文件在用」，实测为 **52 文件 292 处**（移交时口径为直接 import 者；经 design_system 门面间接消费的面大得多）——规模虽超 30 文件阈值，但迁移是**纯 getter 重命名**（同扩展同实现，零语义差），不属于需要 deprecated 转发桥的破坏面，直接全量迁移。

### 2.1 迁移与连带清理

| 符号 | 处置 | 规模 |
| --- | --- | --- |
| `context.sparkleTypography` | → `context.typo` | 292 处 / 52 文件 |
| `context.sparkleSpacing` | → `context.space` | 6 处 / 1 文件 |
| `context.sparkleShadows.small/medium` | → `DS.shadowSm`/`DS.shadowMd`（SparkleShadows 仍是唯一源，DS 为其转发层） | 3 处 / 3 文件 |
| `context.sparkleAnimations` | 零消费，getter 删除 | 0 处 |
| `SparkleContext.sparkleTheme` | **保留**（SparkleThemeData 根入口，core 组件 materials/sparkle_button_v2 在用；extension 未承载的 shadows 家族经此取用） | — |
| import 补齐 | 消费 extension 成员的文件统一补 `sparkle_context_extension.dart`（排序插入） | 88 文件 |

冻结数值层（`DS.fontSize*`/`fontWeight*`、DS 字阶 shim ~2300 调用点）**不在本批**，移交批次 4（见 §7）。

---

## 3. 裁决三：AppColors / SemanticColors ~76 色处置

**裁决：全局语义色唯一事实源 = SparkleColors（`context.colors`）。按批次 2 方法论逐色裁决：死令牌 grep 实证删除；活消费迁单一源；领域分类调色板（agent/intent/achievement/template）按「领域数据」单拷贝收编，不强行折入六套工厂。**

### 3.1 SemanticColors：69 成员全删

lib+test 逐成员 grep 实证（豁免出处注释）：**65 成员零消费**——adaptiveTextSecondary/adaptiveBackground、statusOnlineColor/Offline/Invisible、wechatGreen/goldenAccent/amberGold、galaxy ×8、chatMode ×3、agent ×9、intent ×8、template ×4、achievement ×4、sector ×14、panel ×3、背景/统计渐变 ×4。整类删除，连带：`lightHighContrast`/`darkHighContrast` 工厂与 `colorExtensionsHighContrast` getter（零消费；P1-9 高对比贯通时在 SparkleColors 六套工厂内实现）、顶层死函数 `getSectorColor`/`getChatModeColor`（零消费）。

**4 个活消费迁移**（值恒等或收敛）：

| 消费点 | 旧 | 新 | 值 |
| --- | --- | --- | --- |
| multi_agent_bar / chat_mode_selector_pill | `adaptiveTextPrimary` | `context.colors.textPrimary` | 恒等（light 171717 / dark F4F1EB 与 palette 字面相同） |
| galaxy_search_panel | `adaptiveForeground` | `context.colors.textPrimary` | light 111827→171717（未登记的近似墨色收敛到校准锚） |
| chat_mode_selector_sheet | `chatModeIndigo` | `getIntentColor('chat')` | 恒等（5C6BC0；chatModeIndigo 本就是 intentIndigo 的重复字面量） |
| galaxy_search_panel（暗支） | `panelDarkOverlayLighter` | `galaxyPanelOverlayDark`（core/design 顶层常量，E6151D30 原值迁移；features 层不落硬编码色以守 UI-TOKENS 棘轮） | 恒等；galaxy 模块横扫时重校 |

`SparkleColorExtensions` 扩展保留但瘦身为 `isDarkMode`（23 消费）——它只是 Theme 亮度助手，与已删类无关。

### 3.2 领域调色板的边界裁决（为什么不折入 SparkleColors）

四组活函数（getAgentColor ×9 值 / getIntentColor ×8 / getAchievementColor ×4 / getTemplateColor ×4）是**领域身份色**：Agent 角色、意图分类、成就稀有度、分享模板。强行折入六套工厂需要 +25 字段×(ctor/copyWith/lerp) 且发明 5×25 个新值（违反零新增纪律）；映射到现有语义槽则重写产品身份语义（mentor 紫 ≠ brandSecondary）。处置：**保持领域调色板，与已死成员副本一并清理后每个 hex 全仓单拷贝**，文件头声明四组调色板的单一源地位与「不随亮度/HC/CB 变化，跨档校准归 P1-9」的边界。这与批次 2 对 features 层名字键调色板的豁免裁决同一逻辑。

### 3.3 app/theme.dart 整文件删除

`AppColors`（25 getter，**0 消费**）、`AppThemeExtension`/`appExtension`（0 消费）、弃用 `AppThemes`（0 消费——app.dart 实际使用 design_system 的 AppThemes）、`ThemeExtensionHelper` 全部死亡，整文件 −561 行。

**连带修复（测试保真度）**：5 个测试文件（router_deep_link / skill_management_route / router_smoke / main_actions_smoke / recommendation_feedback_widgets）import 的是**弃用旧 AppThemes**——它们一直在用一个生产端根本不运行的主题下跑冒烟。重定向到 design_system 的 AppThemes 后，测试与生产主题一致（analysis_options 的 linter 同步摘除对该文件的豁免）。

---

## 4. 裁决四：container/decor 四件套收敛（batch1→2→3 移交兑现）

**裁决：颜色值的唯一事实源 = SparkleColors 本体 + 其派生 getter。边框与容器面的派生公式从 DS 静态层上收（值恒等），DS 同名符号全部转转发；阴影唯一源 = SparkleShadows（已满足，补删死令牌）；圆角唯一源 = SparkleRadius（context 侧）+ DS 常量档（数值一致，TD-010 继续跟踪）。**

| 家族 | 处置 | 值 |
| --- | --- | --- |
| 边框 `border`/`borderStrong`/`borderSubtle` | DS 的 `_isDark ? neutral600 : neutral300` 等三条并行派生公式上收为 SparkleColors getter，DS 转发（84/7/315 个消费点零改动） | 恒等 |
| 容器面 `surfacePanel`/`surfaceOverlay`/`surfaceCanvas`/`surfacePrimaryElevated`/`glassBackground`/`glassBorder` | 派生公式上收 SparkleColors，DS 转发（62/67/15/38/1/1 消费点零改动） | 恒等 |
| 阴影 | `DS.shadowPrimary` 零消费删除；`shadowXl`（2 消费，brandPrimary 派生）保留并注明 | — |
| 圆角 | `DS.radius6` 静态零消费但 `borderRadius6` 有 5 消费 → **整档保留**（batch1「死档」猜测被 grep 推翻）；SparkleRadius 与 DS 档数值一致性核验通过 | — |
| 容器对令牌（xxxContainer/onContainer） | batch1 预留的**新令牌**不落——批内核验发现 surfaceSecondary/Tertiary + textPrimary/Secondary 已是批次 1 对比度校准的声明锚（theme_manager 注释原文），新增别名层等于造第二套容器词汇；改为在 SparkleColors 四件套注释块中把校准锚关系写死，别名层反而净减（§1 门面删除） | — |

---

## 5. 裁决五（W-7）：中文优先 locale + 登录页打磨

### 5.1 locale：zh 为默认与回退（不改 en 翻译）

**裁决：竞赛产品中文优先——无偏好或不可匹配一律 zh；en 仅经设置显式选择（持久化后照常命中）。** 系统跟随时"en 设备→英文界面"的旧策略是走查翻车根因（web 走查环境全英文）。

| 层 | 改动 |
| --- | --- |
| `I18nService.resolveSupportedLocale` | 无偏好不再窥探 `PlatformDispatcher`，直接 zh；显式偏好按语言码匹配，不可匹配回退 zh |
| `I18nService._buildFallbackLocalizations` | default 分支 en→zh（未知码落中文） |
| 生成物 `app_localizations.dart` | `supportedLocales` 手工重排 zh-first + 批注（regen 会恢复字母序——`app.dart` 的 resolutionCallback 是不依赖生成物顺序的保底层） |
| `MaterialApp.localeResolutionCallback` | 新增：语言码匹配否则 zh（兜住一切绕过 provider 的路径） |
| 测试 | 3 处「falls back to en」期望翻转为 zh（旧断言编码的是被推翻的产品决策）；**定向 13/13 绿** |

### 5.2 登录页品牌标：走查结论部分过期，落地为字阶令牌修复

现树登录页**已有**品牌标（`_BrandMark` 渐变圆 + 火焰图标 + `_BrandWordmark` 全量 appTitle「Sparkle 星火」，batch2 已切品牌对色）——「无品牌标识」的发现对旧构建成立、对当前树不成立。真正残留的缺陷在**字阶**：字标用的 `textTheme.headlineSmall` 与协议行 `textTheme.bodySmall` 都是 `_buildTextTheme` **未映射**的角色，实际渲染落到 M3 默认字阶而非设计系统。修复：字标 → `context.typo.headingMedium`（24/w600 基，叠加既有 w800/字距/行高 copyWith），协议行 → `context.typo.bodySmall`（12/w400，含 CJK fallback）。未新建任何二进制资产、未硬编码样式值。

### 5.3 登录表单宽屏约束

`ContentConstraint` 桌面档放行到 1200px——登录表单在 web/桌面被拉成 1200px 通栏，正是走查缺陷。新增 `DS.contentMaxWidthForm = 480.0`（布局令牌，与 tablet/desktop 上限同族），表单用 `Center + ConstrainedBox` 收窄居中，无新依赖。

---

## 6. 验证

- **全仓 `flutter analyze`：0 error / 0 warning**（全仓口径而非仅改动文件——`plan_card.dart` 经 facade 方法转发的消费点在改动文件清单外，定向口径会漏检，故升级为全仓）。
- **旧符号 grep**（lib+test，豁免出处注释）：`sparkleTypography`/`sparkleColors`/`sparkleSpacing`/`sparkleShadows`/`sparkleAnimations`/`SparkleColorAliases`/`SemanticColors`/`colorExtensionsHighContrast`/`surfaceCard`/`surfaceElevated`/`surfaceGlass`/`shadowPrimary`/`AppColors`/`app/theme.dart` → **零代码残留**（仅 6 条出处注释）。
- **UI-TOKENS 棘轮**（wt3 树上执行 `scripts/run_all_rule_guards.sh --rule UI-TOKENS`，PYTHON_BIN=/opt/homebrew/bin/python3.11）：**PASS — color=275/275, fontSize=727/727**。过程抓到并当场修复 1 例：galaxy 面板常量最初落 features 层触发 +1 违规，改落 core/design（color_extensions.dart 领域装饰色，与其他领域调色板同址）后归零。本批零新增字面量，全部值恒等迁移。
- **定向测试**：i18n 双文件 13/13 绿；主题重定向批（6 文件）25 绿 / 3 失败——`git stash` 基线复核 3 失败在 6d0643e9 干净树上**逐字复现**（`create group`/`create post` finder 落空 + `router_smoke` 渲染异常），为存量失败，与本批无关。
- 纪律：零构建；`flutter pub get` 仅解析；`lib/gen` 为 gitignore 会话产物（从主 checkout 复制以支撑定向测试，不入库不入 patch）。
- 视觉终验（随 L2/L3 截图波）：登录页字标字阶、表单 480 居中、en 设备首启中文界面、边框/容器面转发层抽点比对。

---

## 7. 残留与移交（批次 4 边界）

| 项 | 现状 | 去向 |
| --- | --- | --- |
| SparkleTypography 15 角色扩展 + TextTheme 补齐映射（L1 §4.1） | `titleMedium` shim 仍转发 titleLarge；`_buildTextTheme` 仍缺 headlineSmall/titleSmall/bodySmall/labelMedium 映射（本批登录页已绕行直接用 `context.typo`） | 批次 4 |
| DS 冻结数值层（`fontSize*`/`fontWeight*`/字阶 shim，~2300 调用点） | 冻结 deprecated，未逐屏迁移 | 批次 4 逐屏横扫 |
| 领域调色板跨档校准（agent/intent/achievement/template 25 值不随亮度/HC/CB） | 单拷贝已收编，色值未调 | L1 P1-9 高对比贯通 |
| galaxy 模块 decor 横扫 | `galaxyPanelOverlayDark` 常量（core/design）+ 内联 DS.alpha 值群 | 批次 4 模块横扫 |
| features 层名字键调色板（calendar/avatar/candidate_action 3 处） | batch2 §4 原样 | 批次 3+ 模块横扫（未及，原样移交） |
| `textTertiary` 派生值静态化校准（~2.9:1，213 消费） | batch1 §6 原样 | 批次 4（静态化时按校准表定值） |
| CB 浅色档重校 / tint 边缘带 container 对验收 | batch1 §6 原样 | 批次 4（调色板结构工作） |
| DS.surfaceHigh/surface/surfaceBase 纯别名（80 消费）→ surfaceSecondary 改名横扫 | 转发层保留 | 批次 4 顺手项 |
| deepSpace*/avatarFallback* 派生仍在 DS 静态层 | 值源已是 palette 锚，位置迁移属可选 | 批次 4+ |
| 生成物顺序回退风险 | `flutter gen-l10n` 会把 supportedLocales 恢复字母序（zh-first 为手工重排）——文件内已批注；`localeResolutionCallback` 是顺序无关保底 | 登记：regen 后需复查顺序 |
| 定向测试存量失败 3 例（main_actions ×2 / router_smoke ×1） | 与本批无关，基线复现 | 独立修复单 |
