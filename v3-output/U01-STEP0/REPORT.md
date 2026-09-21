# U-01 Step 0 REPORT — 设计系统内部统一（wt62, base=3b5a99bc）

Worker: U-01 Step 0（LIGHT：零模拟器/零浏览器/零 gradle）｜日期 2026-09-21
计划依据：主仓 commit 8c69c670（U-01 INVENTORY/CONSOLIDATION_PLAN）Step 0：design 目录内部三处 owner 不唯一。
约束执行：只动 design 内部与直接调用点；galaxy 面零改动；ratchet 守卫全程 PASS 且不增。

## 总览

| 项 | 结果 | 调用点迁移 | ratchet |
|---|---|---|---|
| 1. PillTone ≡ TaskPillTone 合并 | 完成（双枚举→PillTone 单 owner） | 2 文件（task_pill.dart 自身 + task_card.dart 16 处引用） | parallelClass 149/149 持平 |
| 2. 双 skeleton 家族统一 | 完成（sparkle_skeleton.dart 单 owner + 删死文件） | 2 文件（plan_detail_screen 免改——既有 import 解析；测试 1 处迁移） | 持平 |
| 3. CustomButton design 内残留清理 | design 内部依赖清零；**实现删除顺延**（见申报 3） | design 内 4 处（empty_state 2 + error_widget 2）+ 1 个测试 | 持平（custom_button 不在扫描根） |

## 1. PillTone ≡ TaskPillTone 双枚举合并

**Before**：`enum PillTone {info,success,warning,danger,neutral,brand}`（semantic_pill.dart）与 `enum TaskPillTone {...}`（task_pill.dart）值完全相同，两套 owner。
**After**：仅 `PillTone`（semantic_pill.dart）存在；`TaskPill.tone` 参数与内部 switch 改用 `PillTone`；task_pill.dart 内两套 tone→token 色映射**逐字保留**（TaskPill.neutral 仍走 surfaceTertiary/border，SemanticPill.neutral 走 textSecondary alpha——二者本就不同，枚举合并不影响）。
**迁移点**：`features/task/presentation/widgets/task_card.dart`（直接调用点）`_typeTone/_statusTone` 16 处 `TaskPillTone.*` → `PillTone.*` + import。全仓（lib+test）已无 `TaskPillTone` 残留。
**视觉**：零变化（值相同、映射未动；text_layout_regression_test 通过）。

## 2. 双 skeleton 家族统一

**Before**：design 内两套骨架实现——A) `sparkle_skeleton.dart`（token 色+自研 shader 呼吸动画，README 规约 owner）；B) `loading_indicator.dart` 内 shimmer 包家族（TaskCardSkeleton/ChatBubbleSkeleton/ProfileCardSkeleton/ListItemSkeleton + 私有 _ShimmerWrapper/_SkeletonBox），且 `SkeletonVariant` 枚举定义两次（loading_indicator 与 async_state_builder 各一，值集还不同）。
**After**：
- shimmer 家族四类+私有 helper **逐字迁入** sparkle_skeleton.dart（唯一 owner 文件，标注“遗留 shimmer 变体，Step 1-6 按 surface 迁移后删”）；渲染代码零改动（reduce-motion/暗色/尺寸/色值不变）。
- `LoadingIndicator` 剥离骨架职责：删 `LoadingType.skeleton`、`SkeletonVariant` 枚举、`LoadingIndicator.skeleton` 工厂、`skeletonVariant/skeletonCount` 字段、`_buildSkeletonLoading`（全仓 lib 零调用，仅 1 个测试用例使用→已迁移）；只保留 circular/linear/fullScreen（features 22 处调用全部是 `LoadingIndicator.circular()`，不受影响）。
- 删除 `widgets/async_state_builder.dart`（SparkleAsyncBuilder/SparkleAsyncListBuilder + 第二个 `SkeletonVariant`）：**lib+test 全仓零引用的死代码**。
- 调用点：plan_detail_screen.dart 的 TaskCardSkeleton 由其既有 sparkle_skeleton.dart import 解析，无需改动；`shared_state_widgets_test.dart` 的 reduce-motion 用例改为直接泵入 owner 处 `ListItemSkeleton`（断言不变：2 个骨架+无 Shimmer）。
**视觉**：零变化（同代码搬家）。

## 3. CustomButton 残留清理

**Before**：design 目录内部残留 5 处 grep 命中（4 个调用点）：empty_state.dart:233（primary）/304（text+small）、error_widget.dart:287（primary+customGradient）/469（primary+warningGradient），design 两文件均 import custom_button.dart。
**After**：4 个调用点全部直用 `SparkleButton`（规约 owner），两文件 import custom_button 已删：
- EmptyState 主行动 → `SparkleButton(label/onPressed/icon)`（onAction 可空传参保语义）；
- CompactEmptyState 文字动作 → `SparkleButton.ghost + ButtonSize.small`（ghost≈原 text 变体）；
- CustomErrorWidget 重试 → `SparkleButton`，severity 经 variant 投影（error→destructive=semanticError token，warning/info→primary）；
- NotFoundErrorPage 返回 → `SparkleButton.primary`。
design_system.dart barrel 已导出 SparkleButton/ButtonVariant/ButtonSize，两文件零新增 import。

### 诚实申报

1. **“删残留实现”未在本步完成（有意顺延）**：计划口径“CustomButton 残留 5 处”与仓库实况不符——custom_button.dart 实际被 **15 个 feature 文件、59 处调用点**使用（task_execution_screen 15 处、action_card 7 处、plan_review_card 7 处等）。直接删除实现会打断 features 编译；一次性迁移属“features 大面积重构”（任务明令禁止，属 Step 1-6）。故本步交付：design 内部依赖清零 + README 将 custom_button.dart **登记为已判死**（禁新增，Step 1-6 迁完即删）。
2. **按钮视觉非逐像素等价（任务以“按钮样式由 token 保证”背书）**：迁移的 4 处按钮由 CustomButton 渐变风换为 SparkleButton token 实心风（radius 12→8 等），且 error_widget 两处丢失 severity 渐变（以 destructive/primary variant 投影 severity 语义）。影响面=EmptyState/CompactEmptyState/CustomErrorWidget/NotFoundErrorPage 的默认按钮，全部有 widget test 行为对照（tap→回调、标签渲染、主题联动）。
3. **预存失败 1 例（与本步无关）**：`shared_state_widgets_test.dart` "CustomErrorWidget retry action remains functional" 在 base=3b5a99bc 基线即失败（`find.text('重试')` 0 命中，l10n 文案落空），改动前后失败点完全一致，未修复（超 Step 0 范围）。
4. galaxy 面文件零改动（视觉锤豁免）；features 仅动 2 个直接调用点文件（task_card.dart、plan_detail_screen_test.dart），无业务逻辑改动。

## Ratchet 守卫（scripts/guards/check_ux_component_convention.py）

- Before：`PASS — rawButton=87/87, rawSpinner=80/80, rawChip=75/75, parallelClass=149/149, colorLiteral=136/136 (146 files)`
- After：**逐字相同**（PASS，五项全持平；本步不触碰扫描根内平行类，无新增债务）。

## 测试统计（flutter test，串行 --concurrency=1，≤2 文件/批）

| 用例组 | Before | After |
|---|---|---|
| test/core/design 全目录（4 文件） | 14 过 / 1 失败（预存） | 14 过 / 1 失败（同一预存） |
| test/widget/text_layout_regression_test.dart + test/shared/.../awaiting_step_resume_card_test.dart | 9 过 | 9 过 |
| test/features/plan/.../plan_detail_screen_test.dart（TaskCardSkeleton+重试按钮路径） | 5 过 | 5 过（CustomButton→SparkleButton 类型断言随迁移更新） |
| **合计** | **28 过 / 1 预存失败** | **28 过 / 1 预存失败** |

## flutter analyze

- Before（/tmp 干净克隆 base=3b5a99bc）：6829 issues；触及文件相关 6 条（sparkle_skeleton discarded_futures、task_card directives_ordering、shared_state test 4 条 info）。
- After：**6829 issues（持平）**；触及文件相关 6 条同类型同数（无 error、无新 lint）。

## 变更清单

- M mobile/lib/core/design/components/atoms/task_pill.dart（枚举合并）
- M mobile/lib/core/design/widgets/loading_indicator.dart（剥离骨架职责，552→205 行）
- M mobile/lib/core/design/widgets/sparkle_skeleton.dart（+遗留 shimmer 家族，单 owner）
- M mobile/lib/core/design/widgets/empty_state.dart、error_widget.dart（4 调用点→SparkleButton）
- M mobile/lib/core/design/README.md（Step 0 收敛状态登记）
- M mobile/lib/features/task/presentation/widgets/task_card.dart（16 处→PillTone）
- M mobile/test/core/design/shared_state_widgets_test.dart（骨架用例迁 owner API）
- M mobile/test/features/plan/presentation/screens/plan_detail_screen_test.dart（按钮类型断言随迁移）
- D mobile/lib/core/design/widgets/async_state_builder.dart（死代码，零引用）
