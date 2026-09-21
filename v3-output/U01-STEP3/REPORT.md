# U-01 Step 3 REPORT — Empty/Error/Loading 状态件统一（wt65, base=c99838d5）

Worker: U-01 Step 3（LIGHT：零模拟器/零浏览器/零构建）｜日期 2026-09-22
计划依据：主仓 commit 8c69c670 CONSOLIDATION_PLAN Step 3——9 surfaces 内裸 `CircularProgressIndicator/LinearProgressIndicator`、自绘空态/错误态收敛至 owner（`LoadingIndicator` / `EmptyState` / `CompactEmptyState` / `CustomErrorWidget` / `CompactErrorCard`）；galaxy 视觉锤豁免；Step 1 边界规则沿用（交互型/选中型不动，纯展示状态件才迁）。

## 总览

| 指标 | Before | After | 说明 |
|---|---|---|---|
| **rawSpinner（guard 口径）** | **79** | **8（-89.9%）** | 8 = galaxy 全部存量，按豁免条款保留；**非 galaxy 扫描根 71→0 清零** |
| parallelClass | 149 | 147（-2） | 删私有 `_LoadingState`/`_EmptyState`（causal_timeline_panel）；其余 15 个装饰卡面类按视觉等价原则**保留登记**（见下） |
| rawButton / rawChip / colorLiteral | 87 / 11 / 123 | 持平 | 本步不触碰 |

触及文件：owner 2 + features 57（chat 22 / home 13 / task 10 / goal 5 / settings 4 / memory 2 / user 1）+ test 4 + ratchet baseline JSON。

## 1. LoadingIndicator owner 最小扩展（规则 5）

迁移面所需能力逐项透传，**默认值全部保持历史行为**（既有 67 个调用方渲染零影响）：

| 参数 | 作用范围 | 默认 | 迁移需求来源 |
|---|---|---|---|
| `strokeWidth` | circular | null→3.0（历史硬编码） | 内联 10–22px spinner 用 1/1.5/1.6/2 |
| `value` | circular+linear | null→不确定态 | 确定性进度条/环（confidence/progress） |
| `backgroundColor` | circular+linear | null→linear 用 DS.neutral200 / circular 无 | 进度环底环、自定义轨道 |
| `liveRegion` | 全部 | true（历史行为） | 内联在已带语义标签控件内不播报 |
| `strokeCap` | circular | null→平台默认 | today_growth 进度环 round 帽 |
| `borderRadius` | linear | null→直角 | long_term_plan 圆角条 |
| `size`（linear 复用为 minHeight） | linear | null→主题默认 4.0 | 2/3/4/6/8px 厚度条（`LoadingIndicator.linear` 工厂此前零调用方，无兼容面） |

**附带稳健性修正（诚实申报 D）**：owner 的 Semantics label 原无条件求值 `context.l10n`（l10n 缺失即崩）。现改为 `loadingText ?? l10n?.commonLoading ?? 'Loading'`（与 error_widget.dart 的 null-l10n 惯例一致）。真实 app（l10n 恒存在）行为逐字不变；无本地化代理的宿主（部分测试 harness）从崩溃变为正常渲染。`context_l10n` 扩展 import 随之移除。

## 2. 迁移明细（非 galaxy 扫描根 71 处）

- **脚本批（29 处）**：`SizedBox(width:N,height:N, child: CircularProgressIndicator(...))` 单层包裹、无 `value:` 的机械模式。脚本提取 size/strokeWidth/color（`color:` 或 `valueColor: AlwaysStoppedAnimation(...)`），未显式给 strokeWidth 的补 `strokeWidth: 4`（裸 CPI 默认，owner 默认 3，须显式对齐）；无色的落 owner 默认 `DS.primaryBase`（= `colorScheme.primary` = `colors.brandPrimary`，已核实与裸 CPI 默认等价）。全部 `liveRegion: false`（见申报 C）。
- **手工批（42 处）**：determinate 进度条/环（plan_review/content_review/goal_arbitration/goal_bottleneck/journey/long_term/plan_view/sprint_view/execution_template/goal_detail×2/dashboard×2/predicted_intent/task_guide/today_growth）、bare linear（why_this/task_create/accessibility/unified_settings×3/goal_creation/goal_switcher/understanding/openclaw_hub/working_memory）、无 SizedBox 包裹裸 CPI（study_materials/intent_preview/causal/subtask/openclaw_node/task_preview/task_offline/voice_input/agent_workflow/agent_reasoning_v2/regeneration/chip 类）、chat_screen 头部 linear。

视觉等价保障：尺寸/线宽/颜色/轨道/线帽/圆角逐参数对应；`SizedBox` 包裹层仅在owner 已内建等价尺寸时移除（如 36px 裸 CPI 的显式 `size: 36 + strokeWidth: 4`）；色值未做任何"顺手收敛"。

## 3. 自绘空态/错误态

**迁移（1 个文件、删 2 个私有类、parallelClass -2）**：
- `causal_timeline_panel.dart`：`_LoadingState` → `LoadingIndicator.circular(36, sw4)`（裸 CPI 等价）；`_EmptyState` → `CompactEmptyState` + 扩展参数。

**CompactEmptyState 最小扩展**：新增 `description`（次要提示文案，labelSmall/textMuted）与 `iconSize`（默认 64 不变）——两段文案的紧凑内联空态迁移所需，默认参数下渲染与扩展前逐字一致（有测试固定）。

**保留登记（15 个私有类，galaxy 不计）**——均为"装饰卡面型"定制状态件，强迁即视觉不等价或含交互控件，按 Step 1 保留先例登记：

| 类 | 文件 | 保留原因 |
|---|---|---|
| `_HomeErrorCard`/`_HomeEmptyInline` | dashboard_screen | DashboardSectionShell 卡面骨架内嵌，结构不对应 owner |
| `_EmptyDashboardCardSection` | dashboard_card_section | 带边框/透明度卡面纯文案，非图标+文案空态 |
| `_HeatmapEmptyState` | learning_heatmap_widget | 圆形图标徽章+双文案的 decorated 卡面 |
| `_DiagnosticsErrorState` | openclaw_connection_diagnostics_sheet | GraphiteCardSurface + FilledButton（交互控件，Step 1 边界） |
| `_EmptyPlanSlot` | plan_view | 含 FilledButton.icon 的可操作空槽（交互边界） |
| `_EmptyUnderstandingState` | understanding_panel | 纯文案容器（无图标），非空态语义 |
| `ChatHistoryInlineError` | chat_design_language_widgets | 内联行式错误 + 交互，owner inline 无对应结构 |
| `_EmptyState`(544) | plan_selector_pill | pill 选择器内嵌态，强迁破坏 pill 交互语义 |
| `_ErrorBanner` | goal_creation_wizard | 页内 banner 私有样式 |
| `_ErrorState` | goal_detail_screen | 列式 icon+文案+TextButton，owner inline/page 均不等价 |
| `_EmptyBottleneckMessage` | goal_bottleneck_strip | surfaceContainerHighest 卡面纯文案 |
| `_GuidanceEmptyState` | task_guidance_surface | 含生成按钮（交互边界）+ 受众分支 |
| `_MemoryPanelLoadingSkeleton` / `_MemorySettingsLoadingSkeleton` | memory 两屏 | 私有骨架屏；surface 级骨架迁移属 Step 4-6 范围（Step 0 已登记删除时序） |

## 4. Ratchet（check_ux_component_convention.py）

- Before：`PASS — rawButton=87/87, rawSpinner=79/79, rawChip=11/11, parallelClass=149/149, colorLiteral=123/123 (134 files)`
- After：`PASS — rawButton=87/87, rawSpinner=8/8, rawChip=11/11, parallelClass=147/147, colorLiteral=123/123 (111 files)`
- 基线已 `--update-baseline` 刷新（只降不升：rawSpinner 79→8、parallelClass 149→147、其余持平）。

## 5. 测试统计（flutter test，串行 --concurrency=1，≤2 文件/批，批间查 swap）

| 用例组 | 结果 |
|---|---|
| test/core/design/loading_indicator_test.dart（**新增**，owner 参数：默认行为固定×2、透传×3、l10n label 契约） | **6/6 过** |
| test/core/design/shared_state_widgets_test.dart（+新增 CompactEmptyState 扩展 3 例） | 6 过 / 1 失败（**预存**，见申报 F） |
| offline_queue_indicator_test + compact_test（迁移面：sending spinner 断言强化为 owner+内部 CPI） | **5/5 过** |
| chat_screen_basic_test + unified_settings_bgm_test（迁移面回归，含 "Loading indicator appears"） | **26/26 过** |
| test_growth_dashboard（TodayGrowthStatusCard 断言随 key 迁移更新：owner 上查找+下钻 CPI，新增 strokeWidth/strokeCap/颜色断言） | 9 过 / 2 失败（**预存**，与基线克隆逐条一致） |
| why_this_today_panel_test | 0 过 / 1 失败（**预存**，与基线克隆一致） |

**未跑清单**：galaxy 套件（本步零改动豁免面）、goldens（chat_golden 的 CPI 为测试自建 fixture，不受影响；未跑）、全量套件（LIGHT 纪律禁止）。

## 6. flutter analyze

- 工作树全量 **6817** 条 = HEAD 基线克隆（/tmp/u01s3_baseline，base=c99838d5）**6817** 条；按 (rule, file) 聚合逐项对比 **净差异为零**（改动中的行号漂移除外）。触及文件无任何 error/warning。

## 7. 诚实申报

1. **过程中事故（已恢复，无净影响）**：脚本首跑后为消除 dart format 噪音执行 `git checkout -- mobile/lib` 回退，误将 owner 扩展与 2 处手工迁移一并回滚；analyze 报参数未定义后暴露，随即重放（扩展+手工迁移+缩进改进版脚本）。首跑脚本还因"末位参数无尾逗号"漏提过 `color: DS.warning`（aurora_receipt_chip/memory_reference_receipt）并产生过 `strokeWidth: None` 字面量——均在本轮回滚范围内，最终 diff 已逐 hunk 人工复核。
2. **首版 diff 曾引入 ~1100 行格式噪音**：仓库非 dart-format-clean，整文件 format 超范围，已整体回退并以"按落点缩进精准发射"重做；最终 patch 639+/581-（含 baseline JSON 与测试）。
3. **liveRegion:false 策略**：迁移落点统一传 `liveRegion: false`，语义与裸 ProgressIndicator 一致（不主动播报）；label 仍挂 `加载中`（l10n）。owner 默认 true 不变，既有 67 个调用方不受影响。
4. **owner l10n 容错**（见第 1 节）：真实 app 零变化；l10n 缺失宿主由崩溃变为兜底 'Loading' 标签。
5. **3 处 const 弱化**：plan_view/unified_omni_bar/task_chat_panel 的外层 `const Padding/SizedBox` 因工厂构造非 const 去掉 const（padding 参数保持 const），无运行时影响。
6. **预存失败 4 例**（基线克隆逐条核实为 HEAD 已存在，与本步无关，未修）：`CustomErrorWidget retry`（Step 0 已登记）、`DailyContextLine has a non-empty fallback`、`ActiveBottleneckAlert uses non-judgmental language`、`renders expanded priority reasoning...`——后三者根因均为测试 harness 缺 l10n delegates 而被测组件直接 `context.l10n`。
7. **gen 缺失处置**：worktree 缺 gitignored 的 `mobile/lib/gen/`（proto 产物），已按纪律从主仓**只读复制**（未改主仓）。
8. **today_growth key 位置**：`today-growth-progress` ValueKey 随迁移挂到 owner 包装上，既有测试改为 owner 上查找+下钻内部 CPI（顺带新增 strokeWidth/strokeCap 断言）。
9. **linear `size` 语义复用**为厚度（minHeight），已写注释；该工厂此前面向外部零调用方，无兼容风险。

## 8. 变更清单（摘要）

- M mobile/lib/core/design/widgets/loading_indicator.dart（7 参数扩展 + l10n 容错）
- M mobile/lib/core/design/widgets/empty_state.dart（CompactEmptyState +description/iconSize）
- M mobile/lib/features/**（57 文件 71 处 spinner 迁移 + causal 空态迁移）
- A mobile/test/core/design/loading_indicator_test.dart（owner 参数 6 例）
- M mobile/test/core/design/shared_state_widgets_test.dart（+3 例）
- M mobile/test/features/chat/.../offline_queue_indicator_test.dart、test/widget/home/test_growth_dashboard.dart（断言随 owner 迁移更新）
- M scripts/guards/ux_component_convention_baseline.json（ratchet 刷新）
- A v3-output/U01-STEP3/{REPORT.md, changes.patch}
