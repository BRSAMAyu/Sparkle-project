# U-02 验收收尾 · 双档核心屏截图 + contrast/hierarchy rubric 判定表

- Worker: wt399（卡 U-02 acceptance 剩余两项）
- base SHA: `c1efd8a6`
- final SHA: 见 git log（本文件所在提交）
- 执行环境: macOS arm64（宿主真实字体 Hiragino Sans GB/Arial/MaterialIcons
  经 `FontLoader` 灌入测试引擎；既有 golden 套件均为 Ahem 色块渲染，本卡
  首次实现 flutter test 内真实字形出图）

## 1. 截图范围（以 wt390 U-09 45 行矩阵为准圈定）

wt390 交付的 `SCREENSHOT_MATRIX.md`（v3-output/U-09/交接件）为 9 surface ×
5 平台档共 45 行。U-02 圈定其 **android 列（1080x2400@3.0）** 的核心屏，
另加矩阵宿主于 home 的 journey/first-action 卡单独成图：

| 矩阵行 | surface | 状态 | 本卡证据文件 |
|---|---|---|---|
| 6 | home | main | `home__demo_data__android__1080x2400@3.0__{standard,low}.png` |
| 11 | chat | history_citations | `chat__demo_data__android__1080x2400@3.0__{standard,low}.png` |
| —（宿主于 home） | journey/first-action | PENDING 提案 | `journeyFirstAction__demo_data__android__1080x2400@3.0__{standard,low}.png` |
| 41 | settings | main | `settings__demo_data__android__1080x2400@3.0__{standard,low}.png` |

8 张 PNG 全部由 `flutter test
test/goldens/u02_dual_mode_evidence_test.dart
--dart-define=U02_CAPTURE_EVIDENCE=true --update-goldens` 真实渲染产出
（门控默认 skip，不进常规 CI 比对）。屏代码零改动；数据面按存量 harness
口径 provider 覆写钉为确定性状态；渲染/主题/动效层全部真实。

低刺激档装配 = 真实 app 链路：`EmotionResponsiveAppWrapper(config:
lowStimulus)`（app.dart:146 同款）→ `EmotionResponsiveTheme.applyToTheme`
重主题化 + `ColorFiltered` 减色温层 + `MediaQuery.disableAnimations`。

## 2. rubric 定义（可计算，非目测）

**contrast**：WCAG 2.1 相对亮度 L = 0.2126R+0.7152G+0.0722B（线性化后），
比值 = (L亮+0.05)/(L暗+0.05)。两层判定：
- L1 token 对：`AppThemes.lightTheme`（真实主题管道）产出的 SparkleColors
  前景/背景对；低刺激档有效色 = token 经低刺激滤色矩阵
  （`_lightLowStimulusFilter` 镜像，r×0.94/g×0.96/b×1.02）后的实显色。
  阈值：正文对 ≥4.5（AA），辅助文字对 ≥3.0（AA-large），disabled 豁免。
- L2 屏上渲染色：真跑后从 RenderParagraph 提取全部实显 TextStyle，
  逐色对主题容器候选集（scaffold/surface 三级/primary/inverseSurface/
  双气泡）取最优比值；≥18px 或 ≥14px w700 按 3.0，其余 4.5；
  alpha<0.5 装饰字豁免。图标字形（MaterialIcons RichText）不属排版样本，剔除。

**hierarchy**：从同一渲染样本分三层——标题（w≥600 或 ≥18px）、正文
（w<600 且 13–18px）、辅助（<13px）。判定：① 标题层非空且 max(标题字号)
> max(正文字号)（同字号时标题字重须 ≥ 正文，复合不倒挂）；② max(辅助)
≤ max(正文)。两档分别判定。

**mode-diff（acceptance 第 2 项"不只是 setting 值"）**：同屏两档必须满足
① 实显主题 extension 档位真切换（lowStimulation 标志）；② 动效时长收缩、
弹性曲线撤除；③ splash 关闭（NoSplash）、卡片阴影下降；④ 渲染树含
ColorFiltered 减色温层（低档有、标准档无）；⑤ 消费主题文字主题的屏
（settings）实显字号整体 +1px（home/chat/journey 为显式 TextStyle，
字号判据豁免并如实登记，其两档差异由 ①–④ + 截图承担）。

测试真源：`mobile/test/core/design/u02_contrast_hierarchy_rubric_test.dart`
（8 用例全绿；发现棘轮：已登记缺陷不放红留证，未登记新违规必须红，
修复后清空对应键——不删断言换全绿）。完整运行输出：`rubric_test_output.log`。

## 3. 判定表（逐屏 × 逐档）

### 3.1 token 对 contrast（真实主题管道，两档）

| 前景 token | 背景 token | standard | low(滤色后) | 阈值 | 判定 |
|---|---|---|---|---|---|
| textPrimary #171717 | surfacePrimary(scaffold) #F8F5F0 | 16.37:1 | 15.13:1 | 4.5 | PASS |
| textPrimary | surfaceSecondary #F0ECE5 | 15.15:1 | 14.00:1 | 4.5 | PASS |
| textPrimary | surfaceTertiary #E5DFD5 | 13.49:1 | — | 4.5 | PASS |
| textSecondary #555555 | surfacePrimary | 5.24:1 | 5.12:1 | 4.5 | PASS |
| textSecondary | surfaceSecondary | 4.85:1 | — | 4.5 | PASS |
| textTertiary #707070 | surfacePrimary | 4.59:1 | 4.50:1 | 3.0 | PASS |
| textTertiary | surfaceSecondary | 4.25:1 | — | 3.0 | PASS |
| chatBubbleOtherText #171717 | chatBubbleOther #F0ECE5 | 15.80:1 | 14.60:1 | 4.5 | PASS |
| chatBubbleUserText white | chatBubbleUser #0072B2 | 5.36:1 | 5.17:1 | 4.5 | PASS |
| onPrimary | brandPrimary #0072B2 | 5.82:1 | — | 4.5 | PASS |

（"—" = 该对在该轮样本未渲染，L2 层已覆盖）

### 3.2 屏上渲染 contrast + hierarchy（真跑渲染树，两档）

| surface | 档 | 层级（标题 max / 正文 max / 辅助 max） | 层级判定 | 屏上对比判定 |
|---|---|---|---|---|
| home | standard | 19px「先定下你的第一个目标」 / 16px「输入消息...」 / ≤12px | PASS | 全部 PASS（7 色，白字在深底 13.20:1） |
| home | low | 19px / 16px / ≤12px | PASS | 全部 PASS（7 色） |
| chat | standard | 16px「AI学习助手」 / 16px「输入消息...」* | PASS（同字号标题字重更高，复合不倒挂） | **1 项 FAIL（已登记 F1）**，其余 PASS |
| chat | low | 16px / 17px | PASS | 该轮样本为空态面板，全部 PASS（F5 致 history 态在 low 档泵帧期受框架断言干扰，见 F5） |
| journeyFirstAction | standard | 无标题层 / 16–18px | **FAIL（已登记 F2）** | 全部 PASS（4 色） |
| journeyFirstAction | low | 无标题层 | **FAIL（已登记 F2）** | 全部 PASS |
| settings | standard | 20px「胶囊生成」 / 16px「感官反馈」 / ≤12px | PASS | 全部 PASS（11 色） |
| settings | low | 20px / **17px**（+1px 实证） / ≤12px | PASS | 全部 PASS |

### 3.3 mode-diff（低刺激真实生效证据，acceptance 第 2 项）

四屏 × 四判据全 PASS：档位切换、动效收缩、splash/阴影减除、减色温层
（settings 另有 16→17px 渲染字号提升实证）。动效/装饰量化对照见 §4。

### 3.4 已登记发现（棘轮真源：`registeredU02Findings`，DEFERRED）

| # | 发现 | 数值证据 | 来源 | 处置 |
|---|---|---|---|---|
| F1 | chat 消息时间戳用 `neutral500`(#958A80) 10px w400，对比不足 | 最优背景 3.91:1 < AA 4.5:1 | 渲染树测量（chat/standard，见 log） | DEFERRED：neutral500 多消费点共用，改值波及面超出"纯 token 修正"；建议该消费点改用 textTertiary(#707070，4.59:1) |
| F2 | FirstActionCard 无标题层（全部渲染文本为正文/辅助级样式） | headingMax=N/A | 渲染树测量（journey 两档） | DEFERRED：目标标题应升 heading 级样式，涉及卡视觉改版 |
| F3 | FirstActionCard `Row`(first_action_card.dart:367) 在 360 逻辑宽溢出 | 21px（截图黄黑条纹可见，第三个按钮「编辑」被裁） | 渲染异常收集（capture 两档复现） | DEFERRED：需布局结构调整（Expanded/flex），非 token 值 |
| F4 | ChatScreen `chat_accessory_pill.dart:63` Row 同视口溢出 | 48–118px（随字体度量浮动；capture PNG 右缘条纹可见） | 渲染异常收集 | DEFERRED：同上，布局结构修正 |
| F5 | 低刺激档 `MediaQuery.disableAnimations` × `AnimatedSize` 触发框架断言 | `RenderAnimatedSize was mutated in its own performLayout`（chat low 档捕获） | 渲染异常收集 | DEFERRED：消费点对 zero-duration 动画需 LayoutBuilder 化；框架层交互，非本卡 token 面 |

## 4. 动效/装饰量化对照表（acceptance 第 2 项）

来源：`resolveSparkleMotionTokens` / `SparkleStateTokens.forMood`
（测试程序化输出，见 `rubric_test_output.log`）。

### 4.1 SparkleMotionTokens standard vs low

| 字段 | standard | low | 差值/变化 |
|---|---|---|---|
| fast | 150ms | 80ms | −70ms |
| normal | 250ms | 150ms | −100ms |
| slow | 400ms | 200ms | −200ms |
| slower | 600ms | 240ms | −360ms |
| standardCurve | Cubic(0.65,0.04,0.35,1.00) | 同左 | 不变 |
| enterCurve | Cubic(0.00,0.00,0.58,1.00) | 同左 | 不变 |
| exitCurve | Cubic(0.42,0.00,1.00,1.00) | 同左 | 不变 |
| bounceCurve | ElasticOutCurve(0.4) | easeOut | **弹性撤除** |
| overshootCurve | Cubic(0.17,0.89,0.32,1.27)（过冲） | easeOut | **过冲撤除** |

### 4.2 SparkleStateTokens（calm/celebrate/attention × 两档）

| mood | 字段 | standard | low | 低刺激减法 |
|---|---|---|---|---|
| calm | glowOpacity / emphasis / motion / particle / bounce | 0.05 / 1.0 / 1.0 / 0 / false | 同左 | 平静态本征低装饰，两档一致 |
| celebrate | glowOpacity | 0.16 | 0.08 | 发光减半 |
| celebrate | emphasisScale | 1.02 | 1.0 | 庆祝放大撤除 |
| celebrate | motionScale | 1.0 | 0.6 | 时长 ×0.6 |
| celebrate | particleScale | 1.0 | **0** | **庆祝粒子归零** |
| celebrate | allowBounce | true | **false** | **弹性撤除** |
| attention | glowOpacity | 0.10 | 0.06 | 发光收紧（保留可见性>0） |
| attention | motionScale | 1.0 | 0.6 | 时长 ×0.6 |
| attention | particleScale | 0 | 0 | 本就归零 |
| attention | allowBounce | false | false | 本就禁用 |

### 4.3 Theme/交互层实际生效清单（渲染级证据）

| 生效点 | standard | low | 证据 |
|---|---|---|---|
| context.motion.normal（消费点实测） | 250ms | 150ms | calm_low_stimulation_test.dart（22 用例既有绿） |
| 庆祝粒子（SparkleConfetti 挂载） | ConfettiWidget 挂载、粒子计数 20 | 不挂载、计数 0 | 同上（play 触发对比用例） |
| splash 反馈 | InkRipple | **NoSplash** | 渲染树实显主题断言（四屏） |
| 卡片阴影 | 默认 | elevation 0 + 描边 | 同上 |
| 页面转场 | 系统转场 | **NoTransitionsBuilder**（全平台） | applyToTheme 源 + 断言 |
| 色温层 | 无 ColorFiltered | ColorFiltered（浅色 r×0.94/g×0.96/b×1.02） | 渲染树断言（四屏）+ PNG 两档色差可见 |
| MediaQuery | 原样 | disableAnimations=true + accessibleNavigation=true | wrapper 装配（app.dart 同款） |
| Material 文字主题 | 基准 | 全系 +1px | settings 实测 body 16→17px |

## 5. 结论（worker 自评，非 DONE）

- acceptance 第 1 项：home/settings 两档全 PASS；chat 有 F1 一项 AA 不足
  （时间戳 3.91:1），journey 层级有 F2（无标题层）——两屏**未达"全部通过"**，
  按"发现优先"如实登记并给出修复建议，待修后重跑 rubric 即可闭环。
- acceptance 第 2 项：PASS。低刺激在 token（时长/曲线/粒子/发光）、Theme
  （splash/阴影/转场/文字主题/色温层）、渲染（+1px、ColorFiltered）三层
  均有量化差，非空设置值。
- F3/F4 两处 360 宽溢出为 U-09 视觉面发现，已按 matrix 断言点
  （"canonical home 零 overflow"同口径）登记，建议并入 U-09 修复清单。

## 6. 复跑方式

```bash
# rubric（8 用例，日常可跑）
cd mobile && flutter test test/core/design/u02_contrast_hierarchy_rubric_test.dart

# 证据截图（门控，需显式开启）
flutter test test/goldens/u02_dual_mode_evidence_test.dart \
  --dart-define=U02_CAPTURE_EVIDENCE=true --update-goldens
```

工件清单：8×PNG（本目录）、`RUBRIC_VERDICT.md`（本文件）、
`rubric_test_output.log`（全量数值输出）。
