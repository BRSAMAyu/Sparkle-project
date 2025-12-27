# Sparkle 设计系统 2.0 - 快速参考卡

## 🚀 5分钟快速开始

### 1. 初始化 (main.dart)
```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DesignSystemInitializer.initialize(); // ✨ 一行代码
  runApp(MyApp());
}
```

### 2. 配置主题
```dart
MaterialApp(
  theme: AppThemes.lightTheme,
  darkTheme: AppThemes.darkTheme,
  home: YourApp(),
)
```

### 3. 开始使用
```dart
// ✅ 按钮
SparkleButton.primary(label: '点击', onPressed: () {})

// ✅ 间距
SizedBox(height: DS.sm)

// ✅ 颜色
Container(color: DS.brandPrimary)

// ✅ 文本
Text('Hello', style: DS.bodyLarge)

// ✅ 响应式
if (context.isMobile) { /* 移动端 */ }
```

---

## 🎨 设计令牌速查

### 颜色 (Colors)
```dart
DS.brandPrimary    // 品牌主色
DS.brandSecondary  // 品牌次色
DS.success         // 成功
DS.warning         // 警告
DS.error           // 错误
DS.info            // 信息
```

### 间距 (Spacing)
```dart
DS.xs   // 4px
DS.sm   // 8px
DS.md   // 12px
DS.lg   // 16px
DS.xl   // 24px
DS.xxl  // 32px
DS.xxxl // 48px

// 边距快捷方式
DS.edgeLg.edge     // EdgeInsets.all(16)
DS.horizontalXl    // EdgeInsets.symmetric(horizontal: 24)
```

### 排版 (Typography)
```dart
DS.displayLarge    // 48.8px, Bold
DS.headingLarge    // 31.25px, Bold
DS.headingMedium   // 25px, Semibold
DS.titleLarge      // 20px, Semibold
DS.bodyLarge       // 16px, Regular
DS.bodyMedium      // 14px, Regular
DS.labelLarge      // 14px, Medium
DS.labelSmall      // 12.8px, Medium
```

### 动画 (Animation)
```dart
DS.quick    // 150ms
DS.normal   // 250ms
DS.slow     // 400ms
```

---

## 🔧 常用组件

### 按钮系列
```dart
// 主要按钮
SparkleButton.primary(label: '提交', onPressed: () {})

// 次要按钮
SparkleButton.secondary(label: '取消', onPressed: () {})

// 轮廓按钮
SparkleButton.outline(label: '详情', onPressed: () {})

// 幽灵按钮
SparkleButton.ghost(label: '设置', onPressed: () {})

// 危险按钮
SparkleButton.destructive(label: '删除', onPressed: () {})

// 加载按钮
SparkleLoadingButton(
  label: '提交',
  onPressed: () async {
    await Future.delayed(Duration(seconds: 2));
  },
)

// 图标按钮
SparkleIconButton(
  icon: Icon(Icons.add),
  onPressed: () {},
)
```

### 响应式布局
```dart
// 自动适配布局
AdaptiveLayout(
  mobile: MobileLayout(),
  tablet: TabletLayout(),
  desktop: DesktopLayout(),
)

// 响应式值
ResponsiveValue(
  mobile: 16.0,
  tablet: 24.0,
  desktop: 32.0,
).resolve(context)

// 响应式网格
GridView.builder(
  gridDelegate: ResponsiveGridSystem.delegate(context),
  // ...
)
```

---

## 📱 上下文扩展

### 设备信息
```dart
context.isMobile      // 是否手机
context.isTablet      // 是否平板
context.isDesktop     // 是否桌面
context.isLandscape   // 是否横屏
context.breakpointInfo // 完整断点信息
```

### 主题访问
```dart
context.sparkleColors.brandPrimary
context.sparkleTypography.bodyLarge
context.sparkleSpacing.lg
context.sparkleAnimations.quick
context.sparkleShadows.medium
```

---

## 🎯 迁移速查

### 颜色替换
| 旧代码 | 新代码 |
|--------|--------|
| `Color(0xFFFF6B35)` | `DS.brandPrimary` |
| `Color(0xFF4CAF50)` | `DS.success` |
| `Colors.orangeAccent` | `DS.warning` |

### 间距替换
| 旧代码 | 新代码 |
|--------|--------|
| `EdgeInsets.all(16)` | `DS.edgeLg.edge` |
| `SizedBox(width: 8)` | `SizedBox(width: DS.sm)` |
| `padding: EdgeInsets.all(24)` | `padding: DS.edgeXl.edge` |

### 字体替换
| 旧代码 | 新代码 |
|--------|--------|
| `fontSize: 16` | `DS.bodyLarge` |
| `fontSize: 24, fontWeight: bold` | `DS.headingMedium` |
| `fontSize: 14, fontWeight: medium` | `DS.labelLarge` |

### 按钮替换
| 旧代码 | 新代码 |
|--------|--------|
| 自定义 `ElevatedButton` | `SparkleButton.primary` |
| `IconButton` | `SparkleIconButton` |
| 加载状态手动处理 | `SparkleLoadingButton` |

---

## ✅ 验证清单

### 使用前检查
- [ ] 已调用 `DesignSystemInitializer.initialize()`
- [ ] MaterialApp 使用了 `AppThemes.lightTheme`
- [ ] 导入了 `design_system.dart`

### 代码审查
- [ ] 没有硬编码颜色 `Color(0x`
- [ ] 没有硬编码间距 `EdgeInsets.all(`
- [ ] 没有硬编码字体 `fontSize: `
- [ ] 使用了原子组件 `SparkleButton.*`

### 测试检查
- [ ] 深色模式正常
- [ ] 平板/桌面布局正常
- [ ] 无障碍测试通过
- [ ] 视觉回归测试通过

---

## 🔍 常见问题

**Q: 如何切换主题？**
```dart
await ThemeManager().toggleDarkMode();
```

**Q: 如何添加新品牌预设？**
```dart
// 在 theme_manager.dart 中添加
enum BrandPreset { sparkle, ocean, forest, custom }
```

**Q: 如何验证设计合规？**
```dart
final report = await DesignSystemChecker.checkCurrentContext(context);
print(report.toMarkdown());
```

**Q: 如何自定义组件？**
```dart
// 继承原子组件或创建新的
class MyCustomButton extends StatelessWidget {
  // 使用设计令牌
}
```

---

## 📚 完整文档

- **架构设计**: `docs/03_重构与优化报告/design-system-architecture-2.0.md`
- **迁移指南**: `docs/03_重构与优化报告/design-system-migration-guide.md`
- **使用示例**: `docs/03_重构与优化报告/design-system-examples.dart`
- **实施总结**: `docs/03_重构与优化报告/design-system-implementation-summary.md`

---

**版本**: Design System 2.0
**更新时间**: 2025-12-27
**状态**: ✅ 生产就绪
