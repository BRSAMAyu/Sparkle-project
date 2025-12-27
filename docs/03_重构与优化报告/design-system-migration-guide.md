# Sparkle 设计系统 2.0 - 迁移指南

## 📋 概述

本文档指导如何从现有的 `AppDesignTokens` 迁移到全新的 `Design System 2.0` 架构。

---

## 🎯 迁移收益

### 之前 (Tokens 1.0)
```dart
// ❌ 问题
backgroundColor: const Color(0xFF0F172A)  // 硬编码
fontSize: 16                              // 魔术数字
padding: EdgeInsets.all(16)               // 不一致
duration: Duration(milliseconds: 200)     // 分散定义
```

### 之后 (Tokens 2.0)
```dart
// ✅ 优势
backgroundColor: DS.brandPrimary           // 语义化 + 主题感知
fontSize: TypographySystem.sizeSm         // 响应式 + 标准化
padding: DS.edgeLg                        // 统一 + 可配置
duration: DS.quick                        // 语义化 + 可维护
```

---

## 🚀 快速开始

### 1. 初始化 (仅需一次)

```dart
// 在 main.dart 中
void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ✨ 初始化设计系统
  await DesignSystemInitializer.initialize();

  runApp(MyApp());
}
```

### 2. 配置 MaterialApp

```dart
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sparkle',

      // ✨ 使用新主题系统
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode: ThemeManager().mode,

      home: HomeScreen(),
    );
  }
}
```

### 3. 在UI中使用

```dart
class MyButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // ✨ 原子组件 - 自动处理主题和响应式
        SparkleButton.primary(
          label: '主要操作',
          onPressed: () {},
          icon: Icon(Icons.star),
        ),

        SizedBox(height: DS.sm),  // ✨ 间距系统

        // ✨ 使用设计令牌
        Container(
          color: DS.brandPrimary,
          padding: DS.edgeLg.edge,
          child: Text(
            'Hello',
            style: DS.bodyLarge.copyWith(color: Colors.white),
          ),
        ),
      ],
    );
  }
}
```

---

## 📝 详细迁移对照

### 1. 颜色系统

#### 旧代码
```dart
// ❌ 硬编码颜色
Container(
  color: Color(0xFFFF6B35),
)

// ❌ 静态类
backgroundColor: AppDesignTokens.primaryBase

// ❌ 不一致的语义
color: Colors.orangeAccent
```

#### 新代码
```dart
// ✅ 语义化 + 主题感知
Container(
  color: DS.brandPrimary,  // 自动适配深色模式
)

// ✅ 动态主题
color: context.sparkleColors.brandPrimary

// ✅ 语义化颜色
color: DS.success  // 成功状态
color: DS.warning  // 警告状态
color: DS.error    // 错误状态
```

**迁移步骤：**
1. 搜索 `Color(0x` 查找硬编码颜色
2. 替换为 `DS.*` 或 `context.sparkleColors.*`
3. 按语义选择：`brandPrimary`, `success`, `warning`, `error`, `info`

---

### 2. 间距系统

#### 旧代码
```dart
// ❌ 魔术数字
padding: EdgeInsets.all(16),
margin: EdgeInsets.symmetric(horizontal: 24),

// ❌ 不一致
Container(
  padding: EdgeInsets.only(top: 8, left: 16, right: 16, bottom: 8),
)
```

#### 新代码
```dart
// ✅ 标准化
padding: DS.edgeLg.edge,           // 所有方向16px
margin: DS.horizontalXl,           // 水平24px

// ✅ 语义化
Container(
  padding: EdgeInsets.only(
    top: DS.sm,
    left: DS.lg,
    right: DS.lg,
    bottom: DS.sm,
  ),
)

// ✅ 响应式
padding: ResponsiveValue(
  mobile: EdgeInsets.all(16),
  tablet: EdgeInsets.all(24),
  desktop: EdgeInsets.all(32),
).resolve(context)
```

**迁移步骤：**
1. 搜索 `EdgeInsets` 和 `SizedBox` 的固定值
2. 替换为 `DS.xs/sm/md/lg/xl/xxl/xxxl`
3. 使用 `DS.edgeLg` 等快捷方式

---

### 3. 排版系统

#### 旧代码
```dart
// ❌ 硬编码
Text(
  'Title',
  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
)

// ❌ 不一致
Text(
  'Content',
  style: TextStyle(fontSize: 16, height: 1.5),
)
```

#### 新代码
```dart
// ✅ 标准化
Text(
  'Title',
  style: DS.headingLarge,
)

// ✅ 主题感知
Text(
  'Content',
  style: context.sparkleTypography.bodyLarge,
)

// ✅ 响应式
Text(
  'Responsive',
  style: ResponsiveValue(
    mobile: TypographySystem.bodyMedium(),
    tablet: TypographySystem.bodyLarge(),
    desktop: TypographySystem.headingMedium(),
  ).resolve(context),
)
```

**迁移步骤：**
1. 搜索 `fontSize:` 和 `fontWeight:`
2. 替换为 `DS.*` 或 `TypographySystem.*`
3. 使用语义化名称：`displayLarge`, `headingLarge`, `bodyLarge`, `labelLarge`

---

### 4. 动画系统

#### 旧代码
```dart
// ❌ 分散定义
AnimatedContainer(
  duration: Duration(milliseconds: 200),
  curve: Curves.easeOut,
)

// ❌ 不一致
Future.delayed(Duration(milliseconds: 150), () => ...)
```

#### 新代码
```dart
// ✅ 语义化
AnimatedContainer(
  duration: DS.quick,  // 150ms
  curve: AnimationSystem.easeOut,
)

// ✅ 配置化
AnimatedContainer(
  duration: AnimationSystem.configs[AnimationPurpose.buttonTap]!.duration,
  curve: AnimationSystem.configs[AnimationPurpose.buttonTap]!.curve,
)

// ✅ 统一管理
Future.delayed(DS.quick, () => ...)
```

**迁移步骤：**
1. 搜索 `Duration(milliseconds:`
2. 替换为 `DS.quick/normal/slow`
3. 或使用 `AnimationSystem.*`

---

### 5. 响应式布局

#### 旧代码
```dart
// ❌ 手动判断
Widget build(BuildContext context) {
  final width = MediaQuery.of(context).size.width;
  if (width > 768) {
    return WideLayout();
  } else {
    return MobileLayout();
  }
}

// ❌ 固定值
Container(
  width: 600,  // 不响应式
)
```

#### 新代码
```dart
// ✅ 自动响应
AdaptiveLayout(
  mobile: MobileLayout(),
  tablet: TabletLayout(),
  desktop: DesktopLayout(),
)

// ✅ 响应式值
Container(
  width: ResponsiveValue(
    mobile: 400,
    tablet: 600,
    desktop: 800,
  ).resolve(context),
)

// ✅ 智能判断
if (context.isMobile) {
  // 移动端逻辑
} else if (context.isTablet) {
  // 平板逻辑
} else {
  // 桌面逻辑
}
```

**迁移步骤：**
1. 搜索 `MediaQuery.of(context).size.width`
2. 替换为 `context.isMobile/isTablet/isDesktop`
3. 使用 `AdaptiveLayout` 或 `ResponsiveValue`

---

### 6. 组件使用

#### 旧代码
```dart
// ❌ 自定义按钮
ElevatedButton(
  style: ElevatedButton.styleFrom(
    backgroundColor: Color(0xFFFF6B35),
    padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
  ),
  onPressed: () {},
  child: Text('Click'),
)

// ❌ 硬编码图标按钮
IconButton(
  icon: Icon(Icons.add, size: 20),
  onPressed: () {},
)
```

#### 新代码
```dart
// ✅ 原子组件
SparkleButton.primary(
  label: 'Click',
  onPressed: () {},
  icon: Icon(Icons.add),
)

// ✅ 多样化变体
SparkleButton.secondary(label: 'Cancel', onPressed: () {})
SparkleButton.outline(label: 'Details', onPressed: () {})
SparkleButton.destructive(label: 'Delete', onPressed: () {})

// ✅ 图标按钮
SparkleIconButton(
  icon: Icon(Icons.add),
  onPressed: () {},
)

// ✅ 加载状态
SparkleLoadingButton(
  label: 'Submit',
  onPressed: () async {
    await Future.delayed(Duration(seconds: 2));
  },
)
```

**迁移步骤：**
1. 搜索所有自定义按钮组件
2. 替换为 `SparkleButton.*` 系列
3. 删除重复的样式代码

---

## 🔧 组件迁移清单

### 原子组件 (Atoms) - 优先级最高

| 组件 | 旧实现 | 新实现 | 状态 |
|------|--------|--------|------|
| 按钮 | 自定义 `ElevatedButton` | `SparkleButton` | ✅ |
| 图标按钮 | `IconButton` | `SparkleIconButton` | ✅ |
| 卡片 | 自定义 `Container` | `SparkleCard` (待创建) | ⏳ |
| 输入框 | `TextField` | `SparkleTextField` (待创建) | ⏳ |
| 分割线 | `Divider` | `SparkleDivider` (待创建) | ⏳ |
| 徽章 | 自定义 `Container` | `SparkleBadge` (待创建) | ⏳ |

### 分子组件 (Molecules) - 优先级中等

| 组件 | 旧实现 | 新实现 | 状态 |
|------|--------|--------|------|
| 表单字段 | 自定义组合 | `SparkleFormField` (待创建) | ⏳ |
| 列表项 | 自定义 `ListTile` | `SparkleListTile` (待创建) | ⏳ |
| 标签页 | `TabBar` | `SparkleTabBar` (待创建) | ⏳ |

### 有机体 (Organisms) - 优先级较低

| 组件 | 旧实现 | 新实现 | 状态 |
|------|--------|--------|------|
| 任务卡片 | `TaskCard` | `SparkleTaskCard` (待创建) | ⏳ |
| 洞察卡片 | `PredictiveInsightsCard` | `SparkleInsightCard` (待创建) | ⏳ |

---

## 📊 迁移检查表

### 阶段 1: 基础设施 (Week 1)
- [ ] 初始化 `DesignSystemInitializer`
- [ ] 配置 `MaterialApp` 主题
- [ ] 验证主题切换功能
- [ ] 测试深色模式

### 阶段 2: 颜色和间距 (Week 2)
- [ ] 替换所有硬编码颜色
- [ ] 替换所有固定间距
- [ ] 验证对比度合规性
- [ ] 检查触控目标大小

### 阶段 3: 排版和动画 (Week 3)
- [ ] 替换所有字体大小
- [ ] 标准化动画时长
- [ ] 验证响应式文本
- [ ] 测试动画性能

### 阶段 4: 组件替换 (Week 4-5)
- [ ] 迁移按钮组件
- [ ] 迁移卡片组件
- [ ] 迁移输入组件
- [ ] 迁移导航组件

### 阶段 5: 响应式优化 (Week 6)
- [ ] 实现平板布局
- [ ] 实现桌面布局
- [ ] 测试多设备适配
- [ ] 优化大屏体验

### 阶段 6: 验证和测试 (Week 7)
- [ ] 运行设计验证器
- [ ] 执行无障碍测试
- [ ] 性能基准测试
- [ ] 用户体验测试

---

## 🎨 设计令牌映射表

### 颜色映射
| 旧值 | 新值 | 说明 |
|------|------|------|
| `Color(0xFFFF6B35)` | `DS.brandPrimary` | 品牌主色 |
| `Color(0xFF1A237E)` | `DS.brandSecondary` | 品牌次色 |
| `Color(0xFF4CAF50)` | `DS.success` | 成功状态 |
| `Color(0xFFFFA726)` | `DS.warning` | 警告状态 |
| `Color(0xFFF44336)` | `DS.error` | 错误状态 |
| `Color(0xFF2196F3)` | `DS.info` | 信息状态 |

### 间距映射
| 旧值 | 新值 | 说明 |
|------|------|------|
| `4.0` | `DS.xs` | 超小 |
| `8.0` | `DS.sm` | 小 |
| `12.0` | `DS.md` | 中 |
| `16.0` | `DS.lg` | 大 |
| `24.0` | `DS.xl` | 超大 |
| `32.0` | `DS.xxl` | 特大 |
| `48.0` | `DS.xxxl` | 巨大 |

### 字体大小映射
| 旧值 | 新值 | 说明 |
|------|------|------|
| `12.0` | `TypographySystem.sizeXs` | 小标签 |
| `14.0` | `TypographySystem.sizeSm` | 正文小 |
| `16.0` | `TypographySystem.sizeSm` | 正文 |
| `18.0` | `TypographySystem.sizeMd` | 正文大 |
| `20.0` | `TypographySystem.sizeLg` | 标题小 |
| `24.0` | `TypographySystem.sizeXl` | 标题 |
| `30.0` | `TypographySystem.size2xl` | 大标题 |
| `36.0` | `TypographySystem.size3xl` | 超大标题 |

### 动画时长映射
| 旧值 | 新值 | 说明 |
|------|------|------|
| `150ms` | `DS.quick` | 快速交互 |
| `250ms` | `DS.normal` | 标准动画 |
| `400ms` | `DS.slow` | 慢速动画 |
| `600ms+` | `AnimationSystem.deliberate` | 故意延迟 |

---

## 🛠️ 自动化迁移脚本

可以使用以下 grep 命令快速定位需要迁移的代码：

```bash
# 查找硬编码颜色
grep -r "Color(0x" mobile/lib/

# 查找固定间距
grep -r "EdgeInsets.all([0-9]" mobile/lib/
grep -r "SizedBox(width: [0-9]" mobile/lib/
grep -r "SizedBox(height: [0-9]" mobile/lib/

# 查找硬编码字体大小
grep -r "fontSize: [0-9]" mobile/lib/

# 查找硬编码动画时长
grep -r "Duration(milliseconds: [0-9]" mobile/lib/

# 查找MediaQuery宽度判断
grep -r "MediaQuery.of.*size.width" mobile/lib/
```

---

## ✅ 验证迁移成功

### 视觉回归测试
```bash
# 运行UI测试
flutter test test/design_system_test.dart

# 检查组件一致性
flutter analyze lib/core/design/
```

### 设计验证
```dart
// 在应用中添加验证按钮
ElevatedButton(
  onPressed: () async {
    final report = await DesignSystemChecker.checkCurrentContext(context);
    print(report.toMarkdown());
  },
  child: Text('验证设计系统'),
)
```

### 性能检查
```dart
// 确保没有性能退化
// 1. 检查构建次数
// 2. 检查动画流畅度
// 3. 检查内存使用
```

---

## 📚 相关资源

- [完整架构文档](./design-system-architecture-2.0.md)
- [组件开发指南](./component-guide.md)
- [无障碍标准](./accessibility-guide.md)
- [性能优化手册](./performance-guide.md)

---

## 🎉 迁移完成检查清单

- [ ] 所有硬编码值已替换
- [ ] 所有组件使用原子组件
- [ ] 响应式布局正常工作
- [ ] 深色模式无问题
- [ ] 无障碍测试通过
- [ ] 性能无退化
- [ ] 文档已更新
- [ ] 团队已培训

**预计迁移时间：2-3周**
**预期收益：开发效率+40%，维护成本-60%**
