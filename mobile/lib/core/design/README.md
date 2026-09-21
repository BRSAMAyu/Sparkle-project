# core/design — Sparkle Design System

组件/令牌唯一事实源。入口 barrel：`design_system.dart`（导出 `SparkleButton`、tokens、`AppThemes`、validation）。

## 目录

- `tokens_v2/` — 颜色/间距/动效/响应式 token 与 `ThemeManager`（唯一事实源，DS 数值层已冻结 @Deprecated）。
- `theme/` — `SparkleThemeExtension`、`SparkleContextExtension`（`context.colors/typo/space/radius/motion` 唯一 context 入口）。
- `components/atoms/` — `SparkleButton`、`SparkleCard`、`SemanticPill`、`TaskPill`、`AiStatusCapsule`、`SparklePressable`。
- `components/molecules|organisms/` — stepper、expandable section。
- `widgets/` — `GraphiteScaffold`/`GraphiteCardSurface`/`SparklePageScaffold`（页面骨架）、`EmptyState`/`CompactEmptyState`、`CustomErrorWidget`/`CompactErrorCard`、`LoadingIndicator`/`SparkleSkeleton`、`SparkleConfetti`、feedback/dialog 等。
- `utils/ai_status_mapper.dart` — AI 状态 → 语义/视觉唯一映射。
- `validation/` — `DesignSystemLinter`、`DesignValidator`。

## Step 0 收敛状态（U-01，2026-09-21）

- **tone 枚举**：`PillTone`（semantic_pill.dart）是唯一 tone 枚举 owner；原 `TaskPillTone`（值完全相同）已删除，`TaskPill.tone` 直接用 `PillTone`。两组件各自的 tone→色映射保持不变。
- **骨架屏**：`widgets/sparkle_skeleton.dart` 是骨架渲染唯一 owner（`SparkleSkeleton/SparkleCardSkeleton/SparkleListSkeleton/SparkleChatBubbleSkeleton` + 并入的遗留 shimmer 变体 `TaskCardSkeleton/ChatBubbleSkeleton/ProfileCardSkeleton/ListItemSkeleton`）。`LoadingIndicator` 只保留 circular/linear/fullScreen；重复的 `SkeletonVariant` 枚举与死代码 `async_state_builder.dart`（零引用）已删除。遗留 shimmer 变体待 Step 1-6 按 surface 迁移后删除。
- **按钮**：design 目录内部对 `custom_button.dart` 的依赖已清零（EmptyState/CompactEmptyState/CustomErrorWidget/NotFoundErrorPage 已直用 `SparkleButton`）。`custom_button.dart` 本体仍被 15 个 feature 文件 59 处调用点使用（视觉与 customGradient 能力差异，须逐 surface 迁移），**已判死、Step 1-6 迁完即删**，禁止新增调用。

## CONVENTION：新增 UI 必须用 design system（V3 冻结，2026-09-21）

> 依据 `v3/04_ux/DESIGN_DIRECTION.md`（Components 收敛）与 `v3/00_context/DECISIONS_V3.md` D21/D22。
> 适用范围：`mobile/lib/features/**` 中 V3 可达的 9 canonical surfaces（onboarding/home/chat/goal/task/memory/galaxy/profile/settings）**优先强制**；其余 feature 新代码同样适用，存量不追溯。

### 规则

1. **组件 owner 唯一**。下表 owner 之外的同类实现（含 feature 内私有 `_*Chip/_*Pill/_*Button/_*Empty/_*Error/_*Loading` 类）不得新增：

   | 需求 | 唯一 owner |
   |---|---|
   | 按钮 | `SparkleButton`（特殊页面骨架按钮可用主题化 Material 按钮，见例外 E3） |
   | 卡面/容器 | `SparkleCard`、`GraphiteCardSurface`；页面骨架 `SparklePageScaffold`/`GraphiteScaffold` |
   | 语义 pill/徽标/筛选 chip | `SemanticPill`（selected 态）或 `TaskPill` |
   | 空态 | `EmptyState` / `CompactEmptyState` |
   | 错误态 | `CustomErrorWidget` / `CompactErrorCard` |
   | 加载 | `LoadingIndicator` 或 `SparkleSkeleton`（禁新增裸 `CircularProgressIndicator` 于首屏主路径） |
   | AI 状态显示 | `AiStatusCapsule`（经 `AiStatusIndicator`），语义先登记 `ai_status_mapper` |
   | 按压反馈 | `SparklePressable`/`SparkleTappable`（禁裸 `GestureDetector`+`Container` 自造按压面用于可点卡片） |

2. **颜色只走 token**：`context.colors` / `DS.*`；禁止新增 `Color(0x…)` 字面量与 `Colors.*` 原生色（既有 ratchet：`scripts/guards/check_ui_design_tokens_ratchet.py`）。
3. **字体只走角色**：`context.typo.*` / Material TextTheme；禁止新增数值 `fontSize:` 字面量。
4. **装饰预算**（DESIGN_DIRECTION）：装饰对比度不得高于核心信息；同屏最多一个强视觉焦点；核心流程不加 gradient/particle/glow/confetti，动效必须过 `PerformanceTier` 与 reduce-motion 门控。galaxy 为独立视觉锤（dark cosmic 豁免），但其颜色须集中在 `sector_config`/painter 主题入口。
5. **扩展 owner 而不是另起炉灶**：owner 缺能力（如 pill 需要 selected 态）→ 在 `core/design` 扩 API，禁止在 feature 内并行造类。新 AI 语义状态必须先登记 `ai_status_mapper`。

### 例外清单（E1–E5，需在代码内 `// design-exception: EX-n 理由` 标注）

- **E1 galaxy 面视觉锤**：`features/galaxy/presentation/widgets/galaxy/` 的 `star_map_painter`/`sector_config`/`galaxy_mini_map` 等允许局部色字面量（dark-cosmic 专属调色），但不得外溢到 galaxy 之外的 import。
- **E2 数据可视化画笔**：CustomPainter 内的图表配色（heatmap/graph）允许派生色计算，须从 token 色出发（`Color.derive` 类），禁止无来源字面量。
- **E3 Material 语义控件**：`TextField`/`Switch`/`Slider`/`PopupMenu` 等走 `AppThemes` 主题化 Material 控件，不属重复实现；`IconButton` 允许（须用 token 色），但主 CTA 禁用。
- **E4 平台/DON 特例**：home 的天气/粒子装饰引擎（`features/home/presentation/widgets/layers/`）在完成 `PerformanceTier` 门控改造前为存量白名单；改造后按规则 4 管辖。
- **E5 单测/golden 固定色**：`test/` 下不受约束。

### 编码检查

- 新增违规阻断：`python3 scripts/guards/check_ux_component_convention.py`（ratchet 基线 `ux_component_convention_baseline.json`，只降不升；`--update-baseline` 在净删后刷新）。
- 颜色/字号存量 ratchet：`check_ui_design_tokens_ratchet.py`（已登记 rule guard）。
