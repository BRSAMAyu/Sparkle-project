# V4-F06 — diff_or_evidence_only

## 结论一句话

无障碍与文本缩放基础能力按「V3 已满足面差量举证 + V4 新面最小增量补缺口」落地：像素族（V4-F02）补 reduce-motion 静态分支、星图补连接文本列表（ACCESSIBILITY_ASSETS「连接有文本列表」唯一缺口）与入场 reduce-motion 静态分支、chat 打字机动效统一到 MediaQuery 单一口径（A-SPEC6 N32/AX-G5）、app 壳无障碍组装律（N31 叠加律）抽为 settings 模块单一权威实现面；三条卡面验收全部有机器可失败断言背书（24 新测试，每验收面一正一反 + 控制组探针活性证明），`flutter analyze` 零 issue，四条设计棘轮守卫全 PASS，classic 零差量成立（A11y 增强属两侧同益面，pixel/classic 渲染差量声明不破）。

## 差量明细（相对 base fea3a4aa = 开卡时 main HEAD；main 随后推进到 92bf49f0 不含本卡面）

产品码（6 改 + 0 删；`app/routes.dart`、RF-06 冲突面三文件、`core/design/tokens_v2/`、`backend/`、`proto/`、迁移零触碰）：

- `mobile/lib/core/design/pixel/pixel_state.dart`（改，+46/−29）—
  `PixelSuccessBadge` 补 **reduce-motion 静态分支**（卡面工作项「reduceMotion
  静态分支」的像素族落点）：`_reduceMotion` 只认 MediaQuery 双源并集
  （`context.reduceMotion` = 系统 `disableAnimations` ∨ `accessibleNavigation`，
  与 SparkleMotion N33 同一口径，禁 `platformDispatcher` 直读）；减弱动效下
  不创建 ticker（`_rise == null` 直落静止终态：对勾全显、位移 0），设置中途
  开启则停并回收在航控制器。零 duration 崩溃面在分支前短路。
  非 reduce-motion 路径逐字节等价（同控制器/同 650ms milestoneMax/同曲线）。
- `mobile/lib/features/galaxy/data/services/galaxy_accessibility_service.dart`
  （改，+24/−1）— `getNodeSemanticLabel` 增加可选
  `connectedNames`（默认空 = V3 既有标签逐字节不变），非空时尾追加
  `galaxyA11yNodeConnections`（新 l10n 键「，连接：A、B」）；
  `GalaxyNodeSemantics` 透传 `connectedNames`。announce 链路不传连接子句
  （键盘焦点播报保持既有口径）。
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`（改，
  +57/−6）— 两处：① `_buildNodeSemanticsOverlay` 复用既有
  `_buildAdjacency`（物理引擎同源，不造第二权威）按图序展开节点名传入
  清单（连接文本列表；计算随 overlay 按图缓存，不进每帧热路径；未知名
  端点跳过不造占位名）；② `_startEntranceAnimationIfNeeded` 补
  **reduce-motion 静态分支**：减弱动效下相机直落概览（跳过 1400ms 推近）、
  `_entranceController.value = 1.0` 直落终态（模糊 sigma=0、不透明度 1），
  回放启动 Timer 与装载流程不受影响；构建回放 Timer 的 140ms/30ms 字面量
  收敛为类级常量 `_replayStartupDelay`/`_replayPreRoll`（两分支共用，
  DL-SPEC A2.1 离阶时长计数不增）。
- `mobile/lib/features/chat/widgets/typing_text.dart`（改，+58/−19）—
  `TypingText`/`TypingRichText`/`_BlinkingCursor` 的 reduce-motion 判定从
  `platformDispatcher.accessibilityFeatures.disableAnimations` 直读（N32/AX-G5
  明令禁止的双源分裂形态：只认系统、漏 in-app 半边）统一为 MediaQuery
  双源并集；判定点移到 `didChangeDependencies`（initState 不能依赖
  inherited；Timer 首跳在 charDelay 之后，首帧前命中减弱即停并直落全文，
  不露帧）。注意：本文件当前在 lib/ 内 **0 消费点**（仅 golden 资产引用），
  属口径对齐的既有维护面，无行为调用点风险。
- `mobile/lib/features/settings/presentation/providers/accessibility_provider.dart`
  （改，+35/−0）— 新增 app 壳无障碍组装律单一权威实现面：
  `composeDisableAnimations` / `composeAccessibleNavigation`（系统 ∨ in-app）
  与 `composeAppTextScaler`（系统字阶夹窗 [0.85, 1.35] × app 内 fontScale）。
- `mobile/lib/app/app.dart`（改，+9/−10）— MaterialApp builder 的 MediaQuery
  组装委托到上述权威函数（行为逐字节等价重构：同夹窗、同乘式、同 OR 律；
  未装载分支保持既有 clamp 原样）。
- l10n（`app_zh.arb`/`app_en.arb` 各 +1 键 `galaxyA11yNodeConnections`；
  `app_localizations.dart`/`_zh.dart`/`_en.dart` 按 wt729 判例手改同步×3，
  不跑 gen-l10n 全量再生成——实跑会引发全量 formatter 风格翻搅）。

测试（5 新文件，24 用例；每验收面一正一反，控制组证明探针判别力）：

- `test/core/design/pixel/pixel_a11y_f06_test.dart`（11）— A± 200% 零异常
  + 溢出探针活性；B±/B2 reduce-motion 零 ticker + 常规分支在航探针 +
  accessibleNavigation 同享；C± 48dp 语义命中面 + 32dp 控制组判负；
  D± 语义标签逐字相等（无同义拼接）+ 拼接控制组判负；E± 15 对正文组合
  ≥4.5:1（classic 深/浅 + 3 像素档 + 星图画布 + 聊天气泡）+ 禁用灰控制组判负。
- `test/core/widgets/app_feedback_a11y_focus_test.dart`（2）— F+ toast
  （AppFeedback→floating SnackBar）在屏时输入框保持 primary focus +
  liveRegion 语义（差量举证：现行为已满足，测试钉死防回退）；F- 模态
  对话框控制组被同一探针判负。
- `test/features/galaxy/widget/galaxy_edge_list_a11y_test.dart`（5）—
  G± 带边图连接子句在场/无边图不造子句（V3 标签逐字相等）；H± 减弱动效
  入场直落终态（progress==1.0）/常规路径在航（探针活性）；I+ 200%+减弱
  动效整屏零异常且摘要/节点语义存活。生产时序 harness（首帧布局后图到达，
  入场在真实 viewport 下执行）。
- `test/features/settings/presentation/providers/accessibility_composition_test.dart`
  （4）— I+ 双源并集全真值表 + 字阶组合五点（1.0/1.56/0.85 托底/1.35 夹顶/
  1.89 叠加上限）；I- AND 组合与替换组合被同一探针判负。
- `test/core/design/pixel/pixel_a11y_evidence_test.dart`（2）— 证据采集
  （环境变量门控落盘，常规跑零副作用）：故事页 200%+减弱动效 与 100% 基线
  两变体真实渲染断言。

## 验收逐条自证（卡面原文 → 机器证据）

1. **「关键目标≥48dp项目标准；正文contrast≥4.5:1」** — C+：PixelPrimaryAction
   语义命中面 ≥48×48dp（`tester.getSemantics().rect`）；C- 控制组 32dp 被判负
   （探针有判别力）。族级既有面差量举证：`DS.touchTargetMinSize == 48.0`
   （常量即 48）、`SparkleButtonV2` 消费 settings `minimumTouchTargetSize`
   （48/56/64 三档）、V3 `a11y_touch_target_test` 既有套件全绿。E+：15 对
   正文组合 ≥4.5:1 逐对断言（含经典深/浅、像素三档、星图画布 neutral0/
   #101929 = 17.60:1、聊天气泡四对）；E- 禁用灰控制组（≈2.85:1）被判负。
2. **「screenreader无同义重复朗读；toast不抢持续输入」** — D+：五态徽章
   语义标签逐字相等（`Semantics(container,label)+ExcludeSemantics` 单一
   来源，F02 失败史形态不再现）；D- 拼接控制组被判负。G+：连接文本列表
   经节点条目线性可读（「，连接：Node 1」「连接：Node 0、Node 2」按图序
   去重）；G- 无边图零子句（V3 字节不变）。F+：SnackBar 在屏时输入框
   primary focus 不变（元素链探针）+ liveRegion 旗标（播报不抢焦）；
   F- 模态对话框控制组夺走焦点被判负。
3. **「200%和reduced-motion无零duration崩溃」** — A+：故事页全族 200%
   `takeException` 为 null、五态语义在场；H+：减弱动效下星图入场直落终态
   （620ms 控制器 value==1.0，模糊/缩放/渐变运动全无）；B+：成功徽章
   减弱动效零 ticker（`transientCallbackCount==0`）；I+：200%+减弱动效
   星图整屏零异常、摘要与节点语义存活。反方向：A-/B-/H- 探针活性控制组
   证明这些零值断言不是恒真。

## 红线自证（diff 逐面）

- **RF-06 冲突面零触碰**：`git diff fea3a4aa --name-only` 全量 15 文件 =
  6 产品码（pixel 族/settings provider/chat widget/galaxy 服务与屏/app 壳）+
  5 l10n + 4 测试（新增）；dashboard_screen / compact_status_bar /
  task_execution_screen 零命中；`backend/`、`proto/`、迁移、`*/gen/` 零命中。
- **五 Tab 路由合同零触碰**：`app/routes.dart` 不在 diff；`test/widget/
  nav_decontextualization_contract_test.dart`（U-07 五 Tab 铁律钉计数恒 5）
  全绿（+73 app+a11y 批内）。
- **classic 零差量（N2 注记随调用点重新举证）**：本卡**零新增像素组件
  产品调用点**（`grep -rn "Pixel" lib/` 调用面不扩）；像素族改动仅
  `PixelSuccessBadge` 动效分支——classic 与像素档共用同一组件同一分支，
  reduce-motion 静态化属**两侧同益面**（a11y 增强，非 pixel 特色改写），
  非 reduce-motion 路径逐字节等价（同 650ms/同曲线/同 forward）；
  theme 通道（design_system 挂载面/tokens_v2）零触碰；
  `test/core/design/pixel/` 全部 F02 既有断言（含 classic 降级 22/18dp、
  stairSteps=0、无渗漏）原样全绿（design 域 214/214）。
- **生成文件零手改红线澄清**：`mobile/lib/l10n/app_localizations*.dart` 是
  git 追踪的 l10n 生成物——按 wt729/4a7c34f1 判例「弃 gen-l10n 重生成
  （实跑 614+/494- 全量 formatter 翻搅）、arb 单键新增 + gen×3 手改同步」
  落地；`mobile/lib/gen/`（协议生成）与 SQLC 产物零触碰。L10N-PARITY 守卫
  PASS（10034 模板键 == 抽象成员；zh/en 子类完整）、I18N 覆盖守卫 PASS。

## 复跑清单（全绿实录见 run_manifest.json / test_results.json）

`flutter analyze --no-pub`（全库 No issues）；`flutter test test/core/design/`
214/214、`test/core/navigation/` 36/36、`test/core/widgets/` 28/28、
`test/features/galaxy/` 159/159+~1 既有 skip、`test/features/settings/`
11/11+~1 既有 skip、app+a11y 批 73/73；四棘轮守卫 PASS。AQ/BG 守卫在
worktree 因 gitignored 生成目录缺位不可跑（`app.gen` / proto 生成物），
已核验主检出同脚本 PASS（环境性，非回归，与 F02 gen_note 同类）。
