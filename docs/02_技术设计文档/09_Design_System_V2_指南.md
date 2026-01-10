# Design System V2 指南 (Luminous Cognition)

## 1. 概述 (Overview)

**Sparkle Design System V2 (代号: Luminous Cognition)** 是专为移动端 AI 学习助手打造的下一代设计语言。它不仅仅是一套 UI 组件库，更是一个完整的视觉与交互系统，旨在通过"光"与"材质"的隐喻，营造出沉浸、智能且富有生命力的学习环境。

### 核心设计理念

1.  **光之隐喻 (Metaphor of Light)**: 使用光效 (Glow, Rim Light) 来引导注意力，表达 AI 的思考状态和知识的习得过程。
2.  **高级材质 (Advanced Materials)**: 引入 `NeoGlass` (新拟态玻璃)、`Obsidian` (黑曜石)、`Ceramic` (陶瓷) 等物理材质，通过 `SparkleMaterial` 系统统一渲染。
3.  **语义化令牌 (Semantic Tokens)**: 所有的颜色、间距、排版和动画都通过语义化 Token 管理，支持动态主题切换和响应式布局。
4.  **性能优先 (Performance First)**: 内置 `PerformanceService` 集成，根据设备性能动态降级视觉特效 (如模糊、噪点)。

---

## 2. 架构设计 (Architecture)

```mermaid
graph TD
    DS[Design System V2]
    
    subgraph Core [核心层]
        Theme[ThemeManager]
        Tokens[Design Tokens]
        Materials[Material System]
    end
    
    subgraph Components [组件层]
        Atoms[Atoms (Buttons, Icons)]
        Molecules[Molecules (Cards, Inputs)]
        Organisms[Organisms (Galaxy, Chat)]
    end
    
    subgraph Renderer [渲染层]
        Styler[MaterialStyler]
        Painters[Custom Painters]
        Shaders[Shaders]
    end
    
    DS --> Core
    Core --> Components
    Components --> Renderer
```

### 2.1 目录结构
```
mobile/lib/core/design/
├── design_system.dart       # 统一入口 (DS类)
├── materials.dart           # 材质定义与渲染器 (SparkleMaterial, MaterialStyler)
├── theme/                   # 主题数据定义
├── tokens_v2/               # 设计令牌
│   ├── color_token.dart     # 颜色系统
│   ├── typography_token.dart# 排版系统
│   ├── spacing_token.dart   # 间距系统
│   ├── animation_token.dart # 动画系统
│   └── theme_manager.dart   # 主题管理器
└── components/              # 原子组件
```

---

## 3. 材质系统 (Material System)

材质是 DS V2 的核心创新。我们将视觉属性（背景、模糊、噪点、边框、光效）封装为数据类 `SparkleMaterial`，并由 `MaterialStyler` 统一渲染。

### 3.1 核心材质

| 材质名称 | 描述 | 适用场景 | 视觉特征 |
| :--- | :--- | :--- | :--- |
| **NeoGlass** | 新拟态玻璃 | 核心容器 (FocusCard, OmniBar) | 磨砂玻璃感、微噪点、边缘光 (Rim Light) |
| **Obsidian** | 黑曜石 | 深色模式强调元素、主按钮 | 深邃光泽、强反射、内发光 (Glow) |
| **Ceramic** | 陶瓷 | 常规卡片、背景板 | 哑光、不透明、细腻触感 |

### 3.2 使用示例

```dart
// 使用预设材质
MaterialStyler(
  material: AppMaterials.neoGlass,
  borderRadius: BorderRadius.circular(20),
  child: Container(
    padding: EdgeInsets.all(20),
    child: Text("NeoGlass Card"),
  ),
);

// 自定义材质
MaterialStyler(
  material: SparkleMaterial(
    color: Colors.black.withOpacity(0.8),
    blurSigma: 20,
    rimLightColor: Colors.white.withOpacity(0.2),
    noiseOpacity: 0.05,
  ),
  child: ...,
);
```

### 3.3 性能分级

`AppMaterials` 会根据 `PerformanceService` 的当前分级自动调整材质复杂度：

- **Ultra**: 开启所有特效 (高斯模糊 + 动态噪点 + 复杂光照)。
- **High**: 关闭动态噪点。
- **Medium**: 降低模糊半径，简化光照。
- **Low**: 关闭模糊 (回退到半透明纯色)，关闭所有昂贵特效。

---

## 4. 设计令牌 (Design Tokens)

通过 `DS` 静态类提供便捷访问。

### 4.1 颜色 (Colors)

支持浅色/深色模式自动切换，以及高对比度模式。

```dart
// 语义化颜色
color: DS.brandPrimary      // 品牌主色
color: DS.surfacePrimary    // 一级背景
color: DS.textSecondary     // 次级文本
color: DS.semanticError     // 错误状态

// 任务类型颜色
color: DS.taskLearning      // 学习任务
color: DS.planSprint        // 冲刺计划
```

### 4.2 排版 (Typography)

基于模块化比例 (1.25) 构建。

```dart
Text("标题", style: DS.headingLarge)
Text("正文", style: DS.bodyMedium)
Text("标签", style: DS.labelSmall)
```

### 4.3 间距 (Spacing)

基于 8pt 网格系统。

```dart
Padding(
  padding: EdgeInsets.all(DS.md), // 16.0
  child: SizedBox(height: DS.sm), // 8.0
)
```

### 4.4 动画 (Animations)

定义了标准的时长和曲线。

```dart
AnimatedContainer(
  duration: DS.normal, // 250ms
  curve: DS.curveEaseOut,
  ...
)

// 扩展方法
widget.fadeIn()
widget.slideUp()
widget.scaleIn()
```

---

## 5. 组件开发规范 (Component Guidelines)

### 5.1 原子化组件

优先使用 `mobile/lib/core/design/components/` 下的原子组件，而非直接使用 Flutter 原生组件。

- **SparkleButton**: 支持多种变体 (Primary, Secondary, Ghost) 和尺寸。
- **SparkleIcon**: 统一图标尺寸和颜色处理。
- **SparkleInput**: 集成验证状态和聚焦动效。

### 5.2 响应式设计

使用 `SparkleContext` 扩展或 `ResponsiveSystem` 处理多端适配。

```dart
// 在 BuildContext 中
if (context.isMobile) {
  // 移动端布局
} else {
  // 桌面端布局
}

// 响应式值
final width = ResponsiveValue<double>(
  context,
  mobile: 300,
  tablet: 500,
  desktop: 800,
).value;
```

---

## 6. 主题定制 (Theming)

### 6.1 初始化

在 `main.dart` 中初始化：

```dart
void main() async {
  await ThemeManager().initialize();
  runApp(MyApp());
}
```

### 6.2 动态切换

```dart
// 切换模式
ThemeManager().setAppThemeMode(AppThemeMode.dark);

// 切换品牌色
ThemeManager().setBrandPreset(BrandPreset.ocean);
```

---

## 7. 最佳实践 (Best Practices)

1.  **避免硬编码颜色**: 永远不要使用 `Colors.blue`，使用 `DS.brandPrimary` 或 `context.colors.brandPrimary`。
2.  **使用 MaterialStyler**: 对于任何通过背景容器，优先考虑使用 `AppMaterials` 预设。
3.  **遵循间距常量**: 所有的 Padding 和 Margin 必须使用 `DS.space` 系列常量。
4.  **文本样式继承**: 使用 `Theme.of(context).textTheme` 或 `DS.typography`，避免手动设置 `fontSize`。
5.  **性能意识**: 在列表或高频刷新区域，谨慎使用 `BackdropFilter` (即 `blurSigma > 0`)。

---

*文档维护者: Design System Team*
*最后更新: 2026-01-10*
