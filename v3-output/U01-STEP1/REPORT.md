# U-01 Step 1 REPORT — Chip/Pill 统一（wt64, base=7729f5a1）

Worker: U-01 Step 1（LIGHT：零模拟器/零浏览器/零 gradle）｜日期 2026-09-21
计划依据：U-01 CONSOLIDATION_PLAN Step 1（Chip/Pill 统一）。基线含 Step 0（PillTone 单 owner）/Step 2。
约束执行：只迁 V3 可达 9 surfaces；galaxy 面豁免零改动；超界文件未碰（seed_library/plan/community 等的 chip 不在扫描根，全部未动）。

## 总览

| 项 | 结果 |
|---|---|
| 迁移处数 | **67**（chat 18 / task 9 / memory 8 / home 6 / goal 6 / settings 4 / user 16） |
| 保留处数 | **7**（动态身份色，逐条理由见下）+ galaxy 1 处豁免 |
| owner 扩展 | `SemanticPill` 新增 `selected` / `onDeleted`（README 规则 5「扩展 owner 而不是另起炉灶」），默认参数不变、既有调用点渲染零影响 |
| ratchet | **rawChip 75→8（-89%）**；colorLiteral 124→123（本步 -1：删除 goal_detail 的 `Color(0xFFE6A817)`）；rawButton=87、parallelClass=149 持平 |
| flutter analyze | HEAD 基线（/tmp 干净克隆对照）6827 → 6817（**-10，零新增**）；触及的 39 文件 0 issue |
| widget test | **已写未执行**（内存门禁，见「诚实申报」1）；新增 2 个测试文件 + 扩展 1 个既有测试，触及文件 analyze 0 issue |

## owner 扩展（mobile/lib/core/design/components/atoms/semantic_pill.dart）

- `selected: bool`（默认 false）：bg/border alpha 0.1/0.3 → 0.18/0.5，无自定义 `icon` 时前置 `Icons.check`（对齐 M3 ChoiceChip/FilterChip 选中 checkmark 语义）。
- `onDeleted: VoidCallback?`：尾部独立 `GestureDetector`+`Icons.close` 删除钮（`Semantics(button, '删除')`），命中区独立于 pill 本体 `onTap`。

## 迁移明细（file · before → after · tone 映射 · 偏差）

### chat 面（18 迁 / 7 留）

| file:line | before → after | tone 映射 | 视觉偏差登记 |
|---|---|---|---|
| chat_screen 2183 | Chip → SemanticPill | neutral | bg surfacePanel(近实底)→tint α0.1；textTertiary→textSecondary |
| chat_screen 2299 | InputChip → SemanticPill(onDeleted) | 按 status：processed→success / uploading→warning / failed→danger / 默认 neutral（原 `_attachmentStatusColor` 色值一一对应改 `_attachmentStatusTone`） | bg info-α0.04 混合底→tone tint；border→tone α0.3 |
| agent_team_sheet 295 | ActionChip → SemanticPill(icon) | neutral | 默认 M3 皮→neutral tint |
| agent_team_sheet 326 | ChoiceChip → SemanticPill(selected) | brand | selectedColor α0.16→0.18 |
| group_chat 777 / private_chat 263 | FilterChip(_agentMode) → SemanticPill(selected,icon) | brand | icon 双态色（brand/neutral500）→selected 切换表达 |
| group_chat 987 / private_chat 746 | _AgentQuickChip/_PrivateAgentQuickChip → SemanticPill | brand | bg brand-α0.1 与文字 brand **完全等值**；字号 fontSizeSm→labelSmall（全局申报 G1） |
| assistant_message_metadata_tray 551 | ActionChip → SemanticPill(icon,onTap?) | neutral | 默认 M3→tint；onPressed 可空语义保留（onTap null=禁用） |
| review_rating_dialog 614 | Chip(onDeleted) → SemanticPill(onDeleted) | neutral | bodySmall→labelSmall；deleteIcon Icons.close 与 owner 删除钮**同 glyph** |
| review_rating_dialog 657 | FilterChip(tags) → SemanticPill(selected) | neutral | 手写 selection 触感→SparklePressable 默认 tap（全局申报 G4） |
| regeneration_prompt 512 | ChoiceChip(type,可反选) → SemanticPill(selected,icon) | neutral | 反选语义保留（onTap 闭包内置空） |
| regeneration_prompt 545 | FilterChip(hints) → SemanticPill(selected) | neutral | — |
| divine_moment_card 180 | ActionChip → SemanticPill(dense) | 按 type 新增 `_toneOf`（与 `_visuals` 一一对应）：brand/warning/info/danger；dismiss→neutral | bg/border α0.1/0.3 原本就等值 |
| growth_card 179 | ActionChip → SemanticPill(dense) | success / dismiss→neutral | bg/border/labelSmall **完全等值** |
| chat_bubble 3431 | ActionChip → SemanticPill(dense,icon) | neutral | 外层 Tooltip+长按 GestureDetector 原样保留 |
| collaboration_timeline 116 | Chip → SemanticPill(dense) | success | shade100/700→token tint α0.1 |
| action_card 3450 | ChoiceChip → SemanticPill(selected) | neutral | — |

**保留（7，理由：per-entity 动态身份色，6-tone 固定色相无法等价映射，强迁即破坏视觉等价）**：
- agent_team_sheet 258 / 352 / 373：`_agentColor(id)` 每个 agent 独立身份色（selected 色块/删除钮着色随 agent 变化）。
- agent_reasoning_bubble 99：`widget.agentColor` 动态传入。
- agent_reasoning_bubble 468：`DS.prismPurple`（=brandSecondary，非 PillTone 色相）。
- agent_reasoning_bubble_v2 752：`DS.taskReflection`（非 PillTone 色相）。
- capability_ceiling_card 160：`mode.color` 动态模式色（兼有既有测试断言 ActionChip 类型，见 capability_ceiling_card_test）。

### task 面（9 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| task_create 423 | ActionChip(tooltip) → Tooltip+SemanticPill(icon) | isNew→success / else brand | bg α0.1 等值；tooltip 经包裹保留 |
| task_detail 414 | Chip(type) → SemanticPill(neutral,dense,icon) | neutral | bg surfaceOverlay α0.92 近实底→tint |
| task_detail 428 | Chip(status) → SemanticPill(selected,dense) | 新增 `_getStatusTone`（pending→warning / inProgress·paused·restore·stuck→info / completed→success / abandoned→neutral；与原 `_getStatusColor` 一一对应） | bg α0.2→0.18(selected)；bold→常规（G1） |
| task_detail 441 | Chip(protocol kind, ValueKey) → SemanticPill(neutral,dense,icon) | neutral | ValueKey `task-protocol-kind-chip` 原样保留 |
| task_detail 1215 | Chip(keypoints) → SemanticPill(neutral,dense) | neutral | surfaceSecondary→tint |
| task_execution 2262 | ChoiceChip(reasons) → SemanticPill(selected) | neutral | — |
| task_protocol_panel 123 / 181 | Chip(evidence/updates) → SemanticPill(dense) | brand / success | α0.06→0.1；fontSize10→labelSmall |
| stuck_help_sheet 322 | Chip → SemanticPill(dense) | brand | α0.08/0.18→0.1/0.3 |

### memory 面（8 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| memory_panel 870 | Chip(confidences) → SemanticPill(dense) | neutral | — |
| memory_panel 948 | Chip(Q score) → SemanticPill(dense) | success | α0.12→0.1 |
| memory_panel 1021 | Chip(tags) → SemanticPill(dense) | neutral | surfaceTertiary→tint |
| memory_panel 1870 | `_CorrectionBadge` 内 Chip → SemanticPill(dense) | warning | radius 10→full；α0.12/0.4→0.1/0.3（类保留，调用点零改） |
| memory_panel 1892 | `_FilterChip` 内 FilterChip → SemanticPill(selected) | neutral | 触感 selection→tap（G4） |
| memory_settings 1010 | `_MemoryChoiceChip` → SemanticPill(selected) | brand（primaryBase≡brandPrimary，色相等值） | disabled 变暗丢失（G3） |
| memory_settings 1042 | `_MemoryFilterChip` → SemanticPill(selected) | brand | 同上 |
| memory_evidence_badge 44 | Chip → SemanticPill(dense) | ok→success / redacted→warning / missing→danger | count 并入 label 文本；点击/长按仍由外层 GestureDetector 承担（pill 本体非交互，与原等价） |

### home 面（6 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| task_monitor 238 | FilterChip → SemanticPill(selected) | brand | 未选中 bg brand-α0.1 等值；选中 α0.3→0.18 |
| dashboard 1716 | ActionChip(nudge) → SemanticPill(icon) | brand | **实底 primaryContainer→tint α0.1**（最显性偏差，语义/可点性不变） |
| understanding_panel 577 | ChoiceChip → SemanticPill(selected) | neutral | 外层 `Semantics(button,selected)` 原样保留 |
| aurora_status_band 232 | ActionChip → SemanticPill(dense) | isDisconfirming→warning / else neutral | disconfirming 仅边框警示→整 pill warning tint（语义增强） |
| curiosity_capsule_card 150 | Chip(relatedSubject) → SemanticPill(dense) | neutral | — |
| interactive_task_card 177 | Chip(tags) → SemanticPill(dense) | brand | bg α0.1 等值；无边框→tone 边框 |

### goal 面（6 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| goal_creation_wizard 548 | ChoiceChip(icon) → SemanticPill(selected,icon) | neutral | — |
| goal_creation_wizard 789/790 | Chip×2 → SemanticPill(dense)×2 | neutral | — |
| goal_detail 296 | Chip(overdue) → SemanticPill(warning,dense,icon) | warning（amber 字面量 `Color(0xFFE6A817)` **删除**，收敛到 warning token） | α0.12/0.5→0.1/0.3 |
| goal_detail 707 | `_InfoChip` 内 Chip → SemanticPill(selected?) | neutral 默认；step.type/estimated 两调用点 → brand+emphasized（原 brand-α0.18 底 → selected α0.18） | labelMedium→labelSmall |
| intent_confirmation_card 84 | ActionChip → SemanticPill(dense) | neutral | — |

### settings 面（4 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| openclaw_execution_preferences 112 | ChoiceChip → SemanticPill(selected) | neutral | — |
| openclaw_connection_panel 781/791 | ChoiceChip×2 → SemanticPill(selected)×2 | neutral | — |
| accessibility_settings 250 | ChoiceChip → SemanticPill(selected) | neutral | — |

### user 面（16 迁）

| file:line | before → after | tone 映射 | 偏差 |
|---|---|---|---|
| persona_onboarding 238/249/260 | ChoiceChip×3（`_styleChip/_goalTypeChip/_levelChip`，返回类型 ChoiceChip→Widget） | neutral | 手写 selection 触感→SparklePressable tap（G4） |
| unified_settings 633/860/943/1132/1143/1154/1240/2629/2638/2647/2707/3037/3063 | ChoiceChip×13 → SemanticPill(selected)×13 | neutral（primaryBase 类选中→brand 色相等值） | disabled（_sensoryReady/_bgmReady=false）时 onTap=null 保留禁用语义；变暗丢失（G3）；943 的预览 IconButton 布局原样保留 |

### 全局偏差申报（G1–G5，均已在代码注释或本表登记）

- **G1 字号归一**：pill label 统一 owner 的 `labelSmall`，原 10–14px 混用收敛（dense 承接 compact 场景）。
- **G2 色面归一**：默认 M3 灰底 chip → neutral tint；各处 α0.06–0.3 → 0.1/selected 0.18；radius 10 → full。
- **G3 disabled 变暗丢失**：原 disabledColor/textDisabled 的弱化渲染未进 owner（enabled=false 仅去涟漪+语义置禁）；选中态强调仍在。
- **G4 触感事件**：手写 `SensoryFeedbackEvent.selection` 的 3 处改由 SparklePressable 默认 `tap` 反馈承接（仍有一次触感，事件类型不同）。
- **G5 checkmark**：M3 选中 checkmark（checkmarkColor）→ selected 前置 check 图标，颜色随 tone。

## Ratchet 守卫（scripts/guards/check_ux_component_convention.py）

- Before（开工时实测）：`PASS — rawButton=87/87, rawSpinner=79/80, rawChip=75/75, parallelClass=149/149, colorLiteral=124/136 (142 files)`
- After（迁移后）：`PASS — rawButton=87/87, rawSpinner=79/80, rawChip=8/75, parallelClass=149/149, colorLiteral=123/136 (134 files)`
- **本步贡献：rawChip -67（75→8），colorLiteral -1（amber 字面量）**；rawSpinner -1、colorLiteral 其余 -11 为 Step 0/2 已落地但未入账的存量下降，本次 `--update-baseline` 一并锁定。
- 基线已刷新并落盘：`scripts/guards/ux_component_convention_baseline.json`（`--update-baseline` 后复跑 PASS：8/8 锁定）。

## flutter analyze（对照法：`git clone` worktree → HEAD 干净基线，未用 stash/reset）

- HEAD（7729f5a1）基线：**6827 issues**（补 gen 后全依赖跑两次同值）
- 本步工作树：**6817 issues（-10，零新增）**；触及的 39 文件（34 lib + 3 test + baseline JSON）0 issue、0 warning。
- 第三方 `third_party_plugins/` 既有 error 为存量，不在触及范围。
- `mobile/lib/gen/` 缺失 → 按纪律从主仓只读复制（git-ignored 构建产物，不入 patch）。

## 测试统计

**状态：已编写、未执行**（见诚实申报 1）。交付测试文件：

| 文件 | 覆盖类别 | 断言 |
|---|---|---|
| `mobile/test/core/design/semantic_pill_test.dart`（新） | owner 扩展 | selected→check 图标；未选中无 check；icon 优先于 check；onDeleted 独立命中不触发 onTap；点 label 触发 onTap 不触发 onDeleted；onTap=null 禁用而 onDeleted 仍可用 |
| `mobile/test/features/chat/presentation/widgets/growth_card_action_pill_test.dart`（新） | chat 面 · action pill | 2 个行动 pill 的 tone 映射（继续→success / 我累了→neutral）+ 点击回调保持 |
| `mobile/test/widget/accessibility_settings_screen_test.dart`（扩展 1 例） | settings 面 · selectable pill | 3 个 TouchTargetSize pill；默认恰一个 selected；点击切换 provider 状态；无原生 ChoiceChip 残留 |

回归清单（基线即存在的相关测试，均为最小批次建议）：
1. `test/core/design/semantic_pill_test.dart` + `test/widget/text_layout_regression_test.dart`（Step 0 的 SemanticPill 既有断言）
2. `test/widget/accessibility_settings_screen_test.dart` + `test/features/settings/presentation/screens/accessibility_settings_screen_test.dart`
3. `test/features/chat/presentation/widgets/growth_card_action_pill_test.dart` + `test/features/chat/presentation/widgets/capability_ceiling_card_test.dart`（保留项的 ActionChip 断言应仍绿）
4. `test/widget/memory_settings_screen_test.dart` + `test/widget/memory_panel_v2_test.dart`
5. `test/features/goal/goal_detail_screen_a6_l10n_test.dart` + `test/widget/unified_settings_bgm_test.dart`

既有测试与本步的兼容性核对：全 test/ 目录中直接断言 chip 类型的仅 4 文件——capability_ceiling_card_test（保留项，兼容）、calibration_receipt_chip_test / chat_design_language_widgets_test（未触及类）、overflow_regression_test（notification_center，未触及）；goldens 均为 env 门禁 skip。迁移面测试无 `find.byType(ChoiceChip/FilterChip/…)` 依赖。

## 诚实申报

1. **测试未执行（内存门禁）**：任务纪律「批间查 swap（<1G 停下落盘申报）」——落盘时 `vm.swapusage free=828M`（两次采样稳定 <1G，load≈3.5），HEAVY（flutter test）启动门关闭，故所有测试（新增 + 回归清单）**均未运行**。已做替代验证：触及文件 flutter analyze 0 issue（类型/语法层面可信）；测试运行期断言（finder/provider 交互）未验证。主会话内存回笼后请按上表 5 批串行执行（`--concurrency=1`），任一失败均为本步质量责任。
2. **视觉等价为“语义 tone 映射对齐”而非逐像素**：按任务验收口径执行；逐处偏差已在上表登记，最显性三处 = dashboard nudge 实底→tint、task_detail 状态/类型/协议 chip 近实底→tint、G1 字号归一。
3. **保留 7 处 + galaxy 1 处**：理由如上表（动态身份色无对应色相；视觉锤豁免）。若后续要求清零，正确路径是给 owner 增加“自定义色相须从 token 出发”的受控扩展，而非保留裸 Chip。
4. **守卫存量入账**：`--update-baseline` 把 Step 0/2 遗留未入账的 rawSpinner -1、colorLiteral -11 一并锁定（均为存量真实下降，非本步产生）。
5. **触达面**：34 个 lib 文件（1 design owner + 33 features 调用点）、3 个测试文件、1 个守卫基线 JSON、design README 登记；无业务逻辑改动，无超界文件（B-04 九 surfaces 划界外零改动，seed_library/plan/community 等处的 chip 未碰）。
6. **预存失败申报**：Step 0 报告的 `shared_state_widgets_test.dart` 预存失败与本步无关，未触碰该文件。

## 变更清单

- M mobile/lib/core/design/components/atoms/semantic_pill.dart（selected/onDeleted 扩展）
- M mobile/lib/core/design/README.md（Step 1 收敛状态登记）
- M mobile/lib/features/{chat×12, goal×3, home×6, memory×3, settings×3, task×5, user×2} 共 33 文件（67 处迁移）
- A mobile/test/core/design/semantic_pill_test.dart
- A mobile/test/features/chat/presentation/widgets/growth_card_action_pill_test.dart
- M mobile/test/widget/accessibility_settings_screen_test.dart（+1 例）
- M scripts/guards/ux_component_convention_baseline.json（ratchet 锁定：rawChip 75→8 等）
