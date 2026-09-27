# WT753 mobile 缺陷猎缺 findings（审查波第一轮，2026-09-28）

- 猎缺 Agent：wt753（v3 航道，node-b）
- 基线：main@469ed006（mobile/ 与 a1ab24c9 全等，窗内无 mobile 新提交；本窗 mobile 改动=wt710/717/724/725/729/731 的 l10n 批 + share_poster 430 + GOV-015 删除 440）
- 方法纪律：CONFIRMED = analyze/grep/沙箱 regen/测试输出可复现；SUSPECTED = 推理。未跑真机/模拟器。产品码零改动（唯一写动作=本 findings + DYNAMIC_ISSUES 台账登记，均在 wt753 worktree 分支）。
- 结论速览：**CONFIRMED 缺陷 2（已占 V3-FIX-489/490）+ CONFIRMED 卫生项 2（未占号，建议随收割批）+ INFO 4；五焦点的"零发现"查证面一并列底。**

---

## CONFIRMED 缺陷（台账已登记）

### F1 [CONFIRMED][P3→台账 V3-FIX-489] WS6 透明画像屏 671 行全链不可达（GOV-015 同构孤儿屏，且观测遥测指向幻影路由）

**位置**：`mobile/lib/features/user/presentation/screens/profile_transparent_screen.dart`（671 行）

**证据链**（469ed006 实测）：
1. 零路由注册：`grep -rn "profile/transparent" mobile/lib` 仅 2 命中，均非路由——`user_repository.dart:71`（HTTP API 端点字符串）与 `ws6_profile_mirror_provider.dart:24`（遥测 metadata）。`user_routes.dart` 无此路径；`git log -S "profile/transparent" -- mobile/lib/features/user/user_routes.dart` 空 = **历史上从未注册过**。
2. 零实例化：类名全 lib 仅自身定义 2 行命中；唯一消费者是 `test/features/user/profile_transparent_screen_test.dart:84`（widget test 直接挂载，证明屏本身功能完好、只是无人可达）。`user.dart` barrel 亦不导出。
3. 零深链入口：`deep_link_service.dart` `_routeMapping` 10 键（achievement/milestone/insights/task/plan/capsule/node/prism/openclaw/openclaw-settings）无 transparent。
4. 数据链却是活的（与 GOV-015 死链不同，本屏是"活链死头"）：
   - `ws6_flags.dart:1` `kWs6ProfileSurfaceEnabled = true`（旗开）；
   - `ws6TransparentProfileViewProvider` 全部生产消费点都在该屏内部（mirror_provider 之外 grep 仅屏自身 4 命中）→ 屏不可达即 provider 生产零消费；
   - `ws6_profile_mirror_provider.dart:24` 遥测 `route: '/user/profile/transparent'` 指向路由表中不存在的路径 → 观测面板持续产出指向幻影路由的 binding 事件（观测污染）；
   - `userRepository.submitInsightControl`（POST `/profile/transparent`，user_repository.dart:71）唯一调用方是该屏。
5. 屏内承诺真实用户控制动作：`onMarkWrong`/`onExamModeOnly` → `submitInsightControl(action: 'wrong'|'exam_mode_only')`（screen :65-:83）——数据洞察的"标错/仅考试模式"控制 UI 不可达，与 GOV-015「承诺控制动作但无 handler」同构反转版：**有 handler、无入口**。

**复现**：`cd mobile && grep -rn "ProfileTransparentScreen" lib --include="*.dart"`（2 命中均为自身定义）；再跑 app 于任何版本，无任何导航路径到达透明画像视图。

**严重度建议**：P3。理由：比 GOV-015（P4）重——体量 3 倍（671 vs 207 行）、feature flag 常开、遥测持续污染观测面、POST API 面存在却零触达；且 day7 后移动端是产品展示面，"透明度/画像披露"叙事若在评审/答辩中被问及"透明画像视图在哪"，产品面无法给出。修法方向二选一：
- (a) 接线复活：注册 `/profile/transparent` 路由 + 从统一设置「画像透明度」卡（unified_settings_screen.dart:1947 起，l10n `enableTransparentMode`）加入口，遥测 route 同步改真路径；
- (b) 处置A 外科删除（同 wt729 GOV-015 判例）：screen 671 行 + ws6 provider/flags 链 + test，`/profile/transparent` API 端点与 `submitInsightControl` 是否保留由后端透明度 API 是否另有消费方裁决（删前需 grep backend/gateway）。

### F2 [CONFIRMED][P4→台账 V3-FIX-490] `/settings/learning-mode` 注册路由零入口，LearningModeScreen 166 行不可达

**位置**：`mobile/lib/features/user/user_routes.dart:304-316`（路由注册）+ `mobile/lib/features/user/presentation/screens/learning_mode_screen.dart`（166 行）

**证据**（469ed006 实测）：
1. `grep -rn "learning-mode" mobile/lib` 唯一命中 = 路由定义本身（user_routes.dart:304）；`name: 'learningMode'` 全库零 `pushNamed/goNamed` 消费。
2. `LearningModeScreen` 类名全 lib 消费仅 user.dart:5（barrel 导出）+ user_routes.dart:20/:312（import+挂载）——零导航、零深链（deep_link_service 无映射）、`route: '` 间接导航样式（expanded_toolbar/evidence_cards 模式）亦零命中、test/integration_test 零引用。
3. 入口史：`git log -S "settings/learning-mode" -- mobile/` 仅 initial commit（1722e6dc）——自仓库重置起该路由从未有过入口，等价设置面已由统一设置内联卡承担（learning mode 相关卡片在 unified_settings 内联，本屏为遗留平行实现）。
4. `flutter analyze` 对该屏零告警（死而未烂）。

**复现**：`grep -rn "learning-mode" mobile/lib`；或运行 app 检索任何到达学习模式设置屏的路径（无）。

**严重度建议**：P4（卫生+路由完整性，无用户危害）。修法方向：删路由+屏+barrel 导出（同 GOV-015 处置A 判例）；若产品仍要独立学习模式设置屏，则在统一设置补入口。

---

## CONFIRMED 卫生项（未占台账号，建议随既有收割家族处置）

### F3 [CONFIRMED][P4 卫生] 4 个零引用资产滞留仓内

**证据**（46 文件全量 vs lib+test+pubspec+json+md corpus basename 比对，零命中）：
- `mobile/assets/icons/Gemini_Generated_Image_yt8rz9yt8rz9yt8r.png`（AI 生图原始文件名残留，REPOSITORY_STANDARDS 卫生问题）
- `mobile/assets/audio/ui/button1.ogg`、`button2.ogg`、`off.ogg`（音频消费面 `sensory_feedback_service.dart` assetPath 全量枚举核对：tap/toggle/select/nav/sheet_open/dialog_open/confirm/success/error/... 无此三名；同目录 `on.ogg` 有引用，仅 off 死）

**修法方向**：直接删除（先例：V3-FIX-354 死集合退役）。音频文件如需保留作素材应移出 assets 声明目录（pubspec `assets/audio/ui/` 整目录声明会把死文件打进产物）。

### F4 [CONFIRMED][P4 卫生] design tokens 零外部引用 55 个（含 tokens_v2 退役 spacing 整类）

**证据**（lib+test 全 corpus 标识符计数，扣除定义点后外部引用=0）：
- `tokens_v2/spacing_token.dart`：`SpacingSystem` 整类 ~31 项（edgeXs..edgeXxxl/topSm..rightLg/horizontal*/vertical*/huge/grid）——类已标 `@Deprecated('Use DS/SparkleSpacing')`（:8-9），零外部引用 = 退役未执行；
- `design_system.dart`：fontSize4xl/5xl/6xl/fontSizeLG/fontSizeMD/fontSizeXL、radius6、breakpointDesktop/Standard/Tablet/Wide、opacityDisabled、streakExpert/Intermediate/Master、profileAccentVisualElements；
- `widgets/app_feedback.dart`：success/info/warning/errorDuration 4 项；
- 杂项：`semantic_pill.dart` defaultSize、`sparkle_button_v2.dart` defaultSize、`pulse_scope.dart` _maxActiveSlots、`sensory_modals.dart` _sheetCurve、`sparkle_skeleton.dart` _fullContentHeight、`global_particle_counter.dart` _defaultMaxParticles、`design_system.dart` _fontRatio（私有零引用 5 项）。

**修法方向**：Deprecated 整类直接删（退役声明即授权）；其余逐键复核后删，或并入下一个 design-token 清理批（U-05/U-09 家族）。逐键清单见本文件附录 A。

---

## INFO（记录不占号）

### I1 arb 元数据占位符声明瑕疵 2 键（gen-l10n 沙箱实跑 exit 0，不阻塞）
- `chaosQueueWaterLevel`（app_en.arb:14662-14669）：值 `Queue Level: {current} / {threshold}` 用 2 占位符，`@placeholders` 只声明 `current`；gen×3 手改同步均已带 `threshold` 参数（app_localizations.dart:57037 等三处一致），运行时正确。下次真跑 gen-l10n 时该键由值面重推断，产出可能翻 `Object`（现 gen 同为 Object，无漂移）。
- `intentPredictionContinue`：声明 `title` 占位符但值不用（en "Continue"/zh "继续"）；gen 三件签名带未用参数，无害。
- `galaxyA11yCanvasSummary`：en 无 `@` 元数据，zh 模板声明 `int`——沙箱 `flutter gen-l10n` 实跑输出 1 条兼容性警告（en 侧推断 Object vs 模板 int）；入库 gen 以模板为准 `int` 正确。建议给 en 补 `@` 元数据消除警告噪声（PARITY 守卫不拦元数据缺失）。

### I2 hardcoded CJK 字符串基线（既有债，本窗零新增）
- 非 presentation 目录 1273 处 + presentation 324 处 CJK 字符串字面量（I18N 守卫只验"import 了 i18n 基建"，不验穷尽，learning_forecast_screen.dart:474 `'周一'..'周日'` 等在守卫 PASS 下共存）。
- 本窗 diff 实证：`git diff 4ecf5d71^..469ed006 -- mobile/` 新增 CJK 行 93 行，全部分布在 `.arb`（应有）与 `app_localizations_zh.dart` gen 文件 getter（应为）；产品面新增硬编码 = **0**。wt710/717/724/725/731 批次为纯清理方向。
- 同族已在台账：V3-FIX-362/411/430 campaign；1464 死键 V3-FIX-210 在册。本窗不重复登记。

### I3 l10n 键健康全绿（查证面）
- en/zh 键集 10061=10061 双向缺失 0（`dart scripts/i18n_coverage_check.dart` PASS 100%）；
- 占位符 en↔zh 逐键比对零不一致（初扫 5 键 confidence* 系 ICU select 嵌套语法误报，`other{Confidence}` 是 fallback 文案非占位符）；
- gen×3（abstract/en/zh）对 arb 10061 键逐一验证签名零缺失；
- 沙箱 `flutter gen-l10n`（复制 arb+l10n.yaml+pubspec 到 /tmp 实跑）exit 0，仅 I1 所述 1 警告——arb 处于可再生状态。

### I4 本窗 mobile 提交面复核
- GOV-015 删除（8e837e8a/V3-FIX-440）余波：`dataUsage|DataUsageDashboardScreen|data_usage_dashboard` 于 lib+test+integration_test+l10n 五件套 **0 残留**；docs 引用清零；analyze 零 undefined——删除干净，无余波缺陷。
- transparentMode 死键删除（8d12ba54/V3-FIX-437）：`transparentModeProvider`（Dart provider，非 l10n 键）仍被 unified_settings_screen.dart:515/:1949/:1955 正常消费，属同名不同物，非残留。`enableTransparentMode` l10n 键活跃（unified_settings_screen.dart:1947）。

---

## 五焦点查证面清单（零发现部分）

| 焦点 | 查证动作 | 结果 |
|---|---|---|
| 1 GOV-015 余波 | 四向 grep（类名/路由串/l10n 键/测试字面量）×lib+test+integration_test+l10n 五件套 | 0 残留 |
| 2 l10n 键健康 | en/zh 双向 diff、占位符双向比对、gen×3 签名对账、沙箱 regen、PARITY 守卫 | 全绿（I1 瑕疵 3 处不阻塞） |
| 3 路由完整性 | 139 注册 pattern（常量递归解析+双参数语法）×452 导航调用（push/go/replace/named/route: 间接/深链映射/deep_link 直通）双向对账 | 导航→注册 0 缺口；注册→无入口 2 缺口（F1/F2）+5 候选人工排除（chat legacy 4 别名=刻意 redirect chat_routes.dart:103-149；milestone=deep_link_service.dart:16 有入口；/errors/:id/edit=error_detail_screen.dart:955 多行 push 有入口；/seed-libraries/:id=SeedLibraryRoutes.detail() 常量方法有入口） |
| 4 死资源 | assets 46 文件 basename 全 corpus 比对；core/design 55 项标识符计数 | F3/F4 |
| 5 编译面 | `flutter analyze`（No issues found! 7.1s）、I18N 守卫 PASS、i18n_coverage 100%、`flutter test` 全量（结果见下） | 见下 |

## 编译面与测试实录

- `flutter analyze`：**No issues found!**（ran in 7.1s）——零既有零新增。
- `python3 scripts/guards/check_i18n_coverage.py`：PASS。
- `dart scripts/i18n_coverage_check.dart`：100%（10061/10061）。
- `flutter test` 全量（2659 用例，本机 darwin/arm64，同一 469ed006 树三跑）：
  - 跑1（compact，管道输出）：+2471 ~23 **-165**；
  - 跑2（compact，文件输出）：+2635 ~23 **-1**（失败发生于 00:20 并发窗口，候选 6 文件 chat_provider/chat_stream_parsing/active_goal_provider/community_provider_security/compact_knowledge_node/wt422_l10n_harvest_smoke 隔离重跑 37/37 全绿——并发负载敏感 flake，非确定性失败）；
  - 跑3（`--reporter json`）：**2659 pass / 0 fail**（done success=true，527s）。
  - 定性：全量套件在本机存在**并发负载敏感的 flaky**（同树三跑 -165/-1/0），与窗内改动无涉——mobile/ 树在 a1ab24c9→469ed006 零提交、窗内各卡定向套件绿（wt729 22 用例、wt731 31 用例等 commit 记录）、analyze 零告警。**无新回归证据**；如实记录：本机未做窗前基线 A/B 全量跑（成本原因），flaky 全集定性留集成侧裁决。
- `flutter gen-l10n` 沙箱实跑：exit 0（I1 警告 1 条）。

---
### 附录 A：F4 零引用 design token 逐项清单

- tokens_v2/spacing_token.dart：**`SpacingSystem` 类整体零引用**（类名+文件名于 lib/test/integration_test 自身文件外 0 命中，@Deprecated 未退役）——含 grid/xs/sm/md/lg/xl/xxl/xxxl/huge、edgeXs..edgeXxxl、horizontalSm..horizontalXl、verticalSm..verticalXl、topSm..topLg、bottomSm..bottomLg、leftSm..leftLg、rightSm..rightLg 全部成员（短名成员未逐项扫描，以类级零引用为准）
- design_system.dart：fontSize4xl, fontSize5xl, fontSize6xl, fontSizeLG, fontSizeMD, fontSizeXL, radius6, breakpointDesktop, breakpointStandard, breakpointTablet, breakpointWide, opacityDisabled, streakExpert, streakIntermediate, streakMaster, profileAccentVisualElements, _fontRatio
- tokens_v2/animation_token.dart：configs（static Map，:27）
- widgets/app_feedback.dart：successDuration, infoDuration, warningDuration, errorDuration
- widgets/pulse_scope.dart：_maxActiveSlots；widgets/sensory_modals.dart：_sheetCurve；widgets/sparkle_skeleton.dart：_fullContentHeight；widgets/global_particle_counter.dart：_defaultMaxParticles；components/atoms/sparkle_button_v2.dart：defaultSize
- 复核提示：短名（xs/sm/md/lg/xl）与经 import alias 的消费形态未逐项排除，收割批落地前按 V3-FIX-200 判例做大小写不敏感子串复核
