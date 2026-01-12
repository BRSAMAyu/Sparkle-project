# Flutter 设计系统整合计划

**日期**: 2025-12-28
**优先级**: P2
**预计工作量**: 8 周
**状态**: 规划中

---

## 问题陈述

Sparkle Flutter 应用中存在 3 个竞争的设计系统，导致代码维护困难、颜色不一致、导入混乱：

| 系统 | 位置 | 状态 | 问题 |
|------|------|------|------|
| **System A: AppThemes** | `lib/app/theme.dart` | 🟢 活跃 | 依赖已弃用的 AppDesignTokens；代码冗长（547 行） |
| **System B: Design System 2.0** | `lib/core/design/design_system.dart` | 🟡 已安装但休眠 | 更现代的架构，但未被应用使用；NS 冲突 |
| **System C: SparkleTheme** | `lib/core/design/sparkle_theme.dart` | 🔴 已放弃 | 颜色冲突（0xFF6750A4 vs 0xFFFF6B35）；未导入 |

### 关键问题

1. **命名空间冲突**: 两个 `AppThemes` 类（`theme.dart` 和 `design_system.dart`）
2. **颜色不一致**:
   - System A: primaryBase = 0xFFFF6B35 (橙色)
   - System B: brandPrimary = 0xFFFF8C5A (浅橙色)
   - System C: brandPrimary = 0xFF6750A4 (紫色)
3. **弃用混乱**: AppDesignTokens 标记为 @Deprecated，但被 System A 广泛使用
4. **重复代码**:
   - System A: 整个 AppThemeExtension 实现（54-97 行）
   - System B: SparkleThemeData + SparkleColors + SparkleTypography 完整重新实现
   - System C: 极简实现，未同步
5. **维护成本**:
   - 任何颜色或字体变更需要修改 3 个地方
   - 新的语义化颜色系统（任务类型颜色）仅在 System A 中实现

---

## 解决方案概述

采用 **System B（Design System 2.0）** 作为标准，原因：

1. ✅ **现代化架构**: ThemeManager + SparkleThemeData + 语义化令牌
2. ✅ **响应式设计**: 内置 ResponsiveSystem 支持
3. ✅ **动画系统**: SparkleAnimations 和阴影系统
4. ✅ **可扩展性**: BrandPreset 支持多品牌主题
5. ✅ **单一来源**: 统一的主题管理和持久化

---

## 实现路线图

### 阶段 1: 准备和验证 (2 周)

**目标**: 验证 System B 的完整性，准备迁移基础设施

#### 任务 1.1: 审查 System B 的完整性
- [ ] 验证 `design_system.dart` 导出所有必需的类
- [ ] 检查 `tokens_v2/` 目录中的所有令牌文件
- [ ] 验证 `components/` 中的原子化组件
- [ ] 检查 `validation/` 工具

**文件**:
- `mobile/lib/core/design/design_system.dart`
- `mobile/lib/core/design/tokens_v2/`
- `mobile/lib/core/design/components/`
- `mobile/lib/core/design/validation/`

#### 任务 1.2: 创建迁移脚本
- [ ] 创建 `scripts/migrate_design_system.sh` 脚本
- [ ] 脚本自动化替换：
  - `import 'package:sparkle/app/theme.dart'` → `import 'package:sparkle/core/design/design_system.dart'`
  - `AppThemes.lightTheme` → `AppThemes.lightTheme`（保持相同）
  - `AppDesignTokens.*` → `DS.*`
  - `DS.brandPrimary` → 保持相同（兼容）

#### 任务 1.3: 扩展 System B 的语义化颜色
- [ ] 将 System A 的任务类型颜色复制到 System B 的 SparkleColors
- [ ] 新增字段：
  - taskLearning, taskTraining, taskErrorFix, taskReflection, taskSocial, taskPlanning
  - planSprint, planGrowth
  - 方法: `getTaskColor(String)`, `getPlanColor(String)`, `getTaskGradient(String)`

**修改文件**: `mobile/lib/core/design/tokens_v2/theme_manager.dart`

**代码示例**:
```dart
class SparkleColors {
  // ... existing fields ...

  // Task type colors
  final Color taskLearning;
  final Color taskTraining;
  // ... etc ...

  Color getTaskColor(String taskType) {
    switch (taskType.toLowerCase()) {
      case 'learning': return taskLearning;
      case 'training': return taskTraining;
      // ... etc ...
    }
  }
}
```

#### 任务 1.4: 验证 ThemeManager 持久化
- [ ] 测试 ThemeManager.initialize() 正确加载 SharedPreferences
- [ ] 验证 setAppThemeMode() 正确持久化
- [ ] 验证 setBrandPreset() 正确持久化
- [ ] 验证 toggleHighContrast() 正确持久化

**测试文件**: `mobile/test/core/design/theme_manager_test.dart`（需要创建）

---

### 阶段 2: 应用集成 (2 周)

**目标**: 在 MaterialApp 中集成 System B，更新主题提供者

#### 任务 2.1: 更新 app.dart
- [ ] 修改 `mobile/lib/app/app.dart`
- [ ] 替换导入:
  ```dart
  // 旧
  import 'package:sparkle/app/theme.dart';

  // 新
  import 'package:sparkle/core/design/design_system.dart';
  ```
- [ ] MaterialApp.router 配置保持不变（AppThemes.lightTheme 和 darkTheme 在两个系统中都存在）

**文件**: `mobile/lib/app/app.dart:1-40`

#### 任务 2.2: 更新 theme_provider.dart
- [ ] 修改 `mobile/lib/presentation/providers/theme_provider.dart`
- [ ] 集成 ThemeManager：
  ```dart
  final themeModeProvider = StateProvider<AppThemeMode>((ref) {
    return ThemeManager().mode;
  });

  final themeManagerProvider = Provider((ref) {
    return ThemeManager();
  });
  ```
- [ ] 添加品牌预设提供者：
  ```dart
  final brandPresetProvider = StateProvider<BrandPreset>((ref) {
    return ThemeManager().brandPreset;
  });
  ```
- [ ] 添加高对比度提供者：
  ```dart
  final highContrastProvider = StateProvider<bool>((ref) {
    return ThemeManager().highContrast;
  });
  ```

**文件**: `mobile/lib/presentation/providers/theme_provider.dart`

#### 任务 2.3: 创建主题设置屏幕
- [ ] 创建 `mobile/lib/presentation/screens/settings/theme_settings_screen.dart`
- [ ] 实现颜色预览
- [ ] 实现深色/浅色模式切换
- [ ] 实现品牌预设选择（Sparkle/Ocean/Forest）
- [ ] 实现高对比度模式切换
- [ ] 实现恢复默认值按钮

**示例代码**:
```dart
class ThemeSettingsScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeManager = ref.read(themeManagerProvider);
    final currentMode = ref.watch(themeModeProvider);
    final currentPreset = ref.watch(brandPresetProvider);
    final highContrast = ref.watch(highContrastProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('主题设置')),
      body: ListView(
        children: [
          // Theme Mode Selection
          ListTile(
            title: const Text('深色模式'),
            trailing: Switch(
              value: currentMode == AppThemeMode.dark,
              onChanged: (value) {
                themeManager.setAppThemeMode(
                  value ? AppThemeMode.dark : AppThemeMode.light,
                );
              },
            ),
          ),
          // Brand Preset Selection
          ListTile(
            title: const Text('品牌预设'),
            trailing: DropdownButton<BrandPreset>(
              value: currentPreset,
              items: BrandPreset.values.map((preset) {
                return DropdownMenuItem(
                  value: preset,
                  child: Text(preset.name),
                );
              }).toList(),
              onChanged: (preset) {
                if (preset != null) {
                  themeManager.setBrandPreset(preset);
                }
              },
            ),
          ),
          // High Contrast Toggle
          ListTile(
            title: const Text('高对比度模式'),
            trailing: Switch(
              value: highContrast,
              onChanged: (value) {
                themeManager.toggleHighContrast(value);
              },
            ),
          ),
        ],
      ),
    );
  }
}
```

---

### 阶段 3: 屏幕迁移 (2 周)

**目标**: 将所有屏幕从 System A 迁移到 System B

#### 任务 3.1: 扫描所有屏幕文件
- [ ] 列出所有使用 AppThemes 或 AppDesignTokens 的屏幕
- [ ] 优先级排序（影响范围）

**命令**:
```bash
find mobile/lib/presentation/screens -name "*.dart" | xargs grep -l "AppThemes\|AppDesignTokens" | wc -l
```

#### 任务 3.2: 批量替换
- [ ] 执行迁移脚本进行自动替换：
  ```bash
  # 替换所有 AppDesignTokens -> DS
  find mobile/lib -name "*.dart" -type f -exec sed -i 's/AppDesignTokens\./DS./g' {} \;

  # 替换所有导入
  find mobile/lib -name "*.dart" -type f -exec sed -i 's|package:sparkle/app/theme|package:sparkle/core/design/design_system|g' {} \;

  # 替换所有 @Deprecated 警告的使用
  find mobile/lib -name "*.dart" -type f -exec sed -i 's/import.*sparkle_theme/import package:sparkle\/core\/design\/design_system/g' {} \;
  ```

#### 任务 3.3: 修复编译错误
- [ ] 运行 `flutter analyze` 检查错误
- [ ] 修复所有迁移相关的编译错误：
  - DS 的 const 版本变体（DS.brandPrimaryConst 等）
  - 缺失的颜色字段（需要添加到 DS 或 context.sparkleColors）
  - 不兼容的 API（如 AppThemeExtension 的替代品）

#### 任务 3.4: 验证 UI 外观
- [ ] 运行 `flutter run` 并检查每个屏幕
- [ ] 对比颜色、间距、字体是否一致
- [ ] 检查深色/浅色模式是否正确
- [ ] 验证所有梯度都渲染正确

---

### 阶段 4: 清理和删除旧系统 (1 周)

**目标**: 删除 System A 和 System C，完全迁移到 System B

#### 任务 4.1: 删除 System A 文件
- [ ] 删除 `mobile/lib/app/theme.dart`
- [ ] 验证没有其他文件导入此文件

**命令**:
```bash
grep -r "from 'package:sparkle/app/theme" mobile/lib
```

#### 任务 4.2: 删除 System C 文件
- [ ] 删除 `mobile/lib/core/design/sparkle_theme.dart`
- [ ] 验证没有其他文件导入此文件

**命令**:
```bash
grep -r "from 'package:sparkle/core/design/sparkle_theme" mobile/lib
```

#### 任务 4.3: 删除已弃用的 AppDesignTokens
- [ ] 删除 `mobile/lib/core/design/design_tokens.dart`
- [ ] 验证没有其他文件直接导入此文件（应该已通过 DS 或 context.sparkleColors 迁移）

**命令**:
```bash
grep -r "design_tokens\|AppDesignTokens" mobile/lib --include="*.dart"
```

#### 任务 4.4: 清理导出
- [ ] 更新 `mobile/lib/core/design/design_system.dart` 中的导出列表
- [ ] 确保所有必需的类都被正确导出

---

### 阶段 5: 测试和验证 (1 周)

**目标**: 完整的测试覆盖和 QA 验证

#### 任务 5.1: 单元测试
- [ ] 创建 `mobile/test/core/design/design_system_test.dart`
- [ ] 测试 ThemeManager 的所有方法
- [ ] 测试 SparkleColors 的所有工厂方法
- [ ] 测试品牌预设应用

#### 任务 5.2: widget 测试
- [ ] 创建 `mobile/test/widgets/theme_settings_screen_test.dart`
- [ ] 测试主题设置屏幕的所有交互
- [ ] 验证主题更改后 UI 正确更新

#### 任务 5.3: 集成测试
- [ ] 测试应用启动时的主题加载
- [ ] 测试深色/浅色模式切换
- [ ] 测试品牌预设应用
- [ ] 测试高对比度模式

#### 任务 5.4: 视觉回归测试
- [ ] 在 iOS 和 Android 上测试所有屏幕
- [ ] 验证所有颜色、间距、字体一致
- [ ] 拍摄参考屏幕截图

---

## 详细修改指南

### 修改 1: theme_manager.dart - 添加任务类型颜色

**文件**: `mobile/lib/core/design/tokens_v2/theme_manager.dart`

**位置**: SparkleColors 类（第 197-334 行）

**添加内容**:
```dart
@immutable
class SparkleColors {
  const SparkleColors({
    required this.brandPrimary,
    required this.brandSecondary,
    // ... existing ...
    required this.taskLearning,      // NEW
    required this.taskTraining,      // NEW
    required this.taskErrorFix,      // NEW
    required this.taskReflection,    // NEW
    required this.taskSocial,        // NEW
    required this.taskPlanning,      // NEW
    required this.planSprint,        // NEW
    required this.planGrowth,        // NEW
  });

  // ... existing fields ...

  // NEW: Task type colors
  final Color taskLearning;
  final Color taskTraining;
  final Color taskErrorFix;
  final Color taskReflection;
  final Color taskSocial;
  final Color taskPlanning;
  final Color planSprint;
  final Color planGrowth;

  factory SparkleColors.light({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        // ... existing ...
        taskLearning: Color(0xFF64B5F6),
        taskTraining: Color(0xFFFF9800),
        taskErrorFix: Color(0xFFEF5350),
        taskReflection: Color(0xFF9C27B0),
        taskSocial: Color(0xFF81C784),
        taskPlanning: Color(0xFF009688),
        planSprint: Color(0xFFE53935),
        planGrowth: Color(0xFF43A047),
      );
    }
    return const SparkleColors(
      // ... existing ...
      taskLearning: Color(0xFF64B5F6),
      taskTraining: Color(0xFFFF9800),
      taskErrorFix: Color(0xFFEF5350),
      taskReflection: Color(0xFF9C27B0),
      taskSocial: Color(0xFF81C784),
      taskPlanning: Color(0xFF009688),
      planSprint: Color(0xFFE53935),
      planGrowth: Color(0xFF43A047),
    );
  }

  factory SparkleColors.dark({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        // ... existing ...
        taskLearning: Color(0xFF64B5F6),
        taskTraining: Color(0xFFFFB74D),
        taskErrorFix: Color(0xFFEF5350),
        taskReflection: Color(0xFFBA68C8),
        taskSocial: Color(0xFF81C784),
        taskPlanning: Color(0xFF4DB6AC),
        planSprint: Color(0xFFFF5252),
        planGrowth: Color(0xFF66BB6A),
      );
    }
    return const SparkleColors(
      // ... existing ...
      taskLearning: Color(0xFF64B5F6),
      taskTraining: Color(0xFFFFB74D),
      taskErrorFix: Color(0xFFEF5350),
      taskReflection: Color(0xFFBA68C8),
      taskSocial: Color(0xFF81C784),
      taskPlanning: Color(0xFF4DB6AC),
      planSprint: Color(0xFFFF5252),
      planGrowth: Color(0xFF66BB6A),
    );
  }

  // NEW: Helper methods for task colors
  Color getTaskColor(String taskType) {
    switch (taskType.toLowerCase()) {
      case 'learning': return taskLearning;
      case 'training': return taskTraining;
      case 'error_fix': return taskErrorFix;
      case 'reflection': return taskReflection;
      case 'social': return taskSocial;
      case 'planning': return taskPlanning;
      default: return taskLearning;
    }
  }

  Color getPlanColor(String planType) {
    switch (planType.toLowerCase()) {
      case 'sprint': return planSprint;
      case 'growth': return planGrowth;
      default: return planSprint;
    }
  }

  LinearGradient getTaskGradient(String taskType) {
    final color = getTaskColor(taskType);
    return LinearGradient(
      colors: [color, color.withValues(alpha: 0.7)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }
}
```

### 修改 2: design_system.dart - 更新 DS 快捷访问

**文件**: `mobile/lib/core/design/design_system.dart`

**位置**: DS 类（第 185-292 行）

**添加内容**:
```dart
class DS {
  // ... existing code ...

  // NEW: Task type colors via context
  static Color getTaskColor(String taskType) => _theme.colors.getTaskColor(taskType);
  static Color getPlanColor(String planType) => _theme.colors.getPlanColor(planType);
  static LinearGradient getTaskGradient(String taskType) => _theme.colors.getTaskGradient(taskType);

  // Convenience shortcuts for common task colors
  static Color get taskLearning => _theme.colors.taskLearning;
  static Color get taskTraining => _theme.colors.taskTraining;
  static Color get taskErrorFix => _theme.colors.taskErrorFix;
  static Color get taskReflection => _theme.colors.taskReflection;
  static Color get taskSocial => _theme.colors.taskSocial;
  static Color get taskPlanning => _theme.colors.taskPlanning;
  static Color get planSprint => _theme.colors.planSprint;
  static Color get planGrowth => _theme.colors.planGrowth;
}
```

### 修改 3: app.dart - 更新导入

**文件**: `mobile/lib/app/app.dart`

**修改**:
```dart
// 旧
import 'package:sparkle/app/theme.dart';

// 新
import 'package:sparkle/core/design/design_system.dart';
```

其他代码保持不变（AppThemes 在两个系统中都存在）

### 修改 4: theme_provider.dart - 集成 ThemeManager

**文件**: `mobile/lib/presentation/providers/theme_provider.dart`

**完全替换**:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// Provider for theme manager singleton
final themeManagerProvider = Provider((ref) {
  return ThemeManager();
});

/// Provider to manage the application's ThemeMode (Light, Dark, System)
final themeModeProvider = StateProvider<AppThemeMode>((ref) {
  return ThemeManager().mode;
});

/// Provider to manage brand preset
final brandPresetProvider = StateProvider<BrandPreset>((ref) {
  return ThemeManager().brandPreset;
});

/// Provider to manage high contrast mode
final highContrastProvider = StateProvider<bool>((ref) {
  return ThemeManager().highContrast;
});

/// Helper to convert AppThemeMode to ThemeMode
ThemeMode appThemeModeToThemeMode(AppThemeMode mode) {
  switch (mode) {
    case AppThemeMode.light:
      return ThemeMode.light;
    case AppThemeMode.dark:
      return ThemeMode.dark;
    case AppThemeMode.system:
      return ThemeMode.system;
  }
}

/// Helper to convert ThemeMode to AppThemeMode
AppThemeMode themeModeToAppThemeMode(ThemeMode mode) {
  switch (mode) {
    case ThemeMode.light:
      return AppThemeMode.light;
    case ThemeMode.dark:
      return AppThemeMode.dark;
    case ThemeMode.system:
      return AppThemeMode.system;
  }
}
```

---

## 验收标准

### 完成标准

- [ ] 所有屏幕使用 System B 的 AppThemes（通过 `flutter analyze` 验证）
- [ ] 所有颜色令牌通过 DS 或 context.sparkleColors 访问（无 AppDesignTokens）
- [ ] 删除了 System A 和 System C 的所有文件
- [ ] `flutter run` 无警告和错误
- [ ] 所有屏幕的深色/浅色模式正常工作
- [ ] 主题设置屏幕工作正常（所有 4 个选项可用）
- [ ] 应用启动时主题设置被正确加载和持久化

### 性能标准

- [ ] 主题切换时间 < 100ms
- [ ] 应用启动时间增加 < 50ms（由于 ThemeManager 初始化）
- [ ] 内存使用增加 < 500KB

### 兼容性标准


- [ ] 支持 iOS 12.0+
- [ ] 支持 Android API 21+
- [ ] 屏幕方向切换时主题正确保持
- [ ] 与现有 Riverpod 提供者兼容

---

## 风险评估

| 风险 | 影响 | 概率 | 缓解策略 |
|------|------|------|---------|
| 颜色不匹配 | 中 | 中 | 在虚拟设备和真机上逐个屏幕验证 |
| 破坏深色模式 | 高 | 低 | 每个阶段完成后测试深色/浅色切换 |
| 性能下降 | 中 | 低 | 性能基准测试，检查过度重新渲染 |
| 旧系统遗留代码 | 低 | 中 | 脚本化搜索检查剩余的导入和使用 |
| 第三方库冲突 | 低 | 低 | 运行完整的 `flutter pub get` 和 `flutter clean` |

---

## 迁移脚本

创建 `scripts/migrate_design_system.sh`:

```bash
#!/bin/bash

set -e

FLUTTER_APP_DIR="${1:-.}"

echo "🎨 开始设计系统迁移..."
echo "📂 目标目录: $FLUTTER_APP_DIR"

# 1. 替换导入
echo "📦 替换导入语句..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/app/theme.dart'|import 'package:sparkle/core/design/design_system.dart'|g" {} \;

find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/core/design/sparkle_theme.dart'|import 'package:sparkle/core/design/design_system.dart'|g" {} \;

find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/core/design/design_tokens.dart'|import 'package:sparkle/core/design/design_system.dart'|g" {} \;

# 2. 替换 AppDesignTokens -> DS
echo "🎯 替换 AppDesignTokens 为 DS..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  's/AppDesignTokens\./DS\./g' {} \;

# 3. 检查剩余的旧系统引用
echo "🔍 扫描剩余的旧系统引用..."
OLD_REFS=$(find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f | xargs grep -l "AppThemes\|AppDesignTokens\|SparkleTheme" || true)

if [ -n "$OLD_REFS" ]; then
  echo "⚠️  找到旧系统引用在:"
  echo "$OLD_REFS"
  echo ""
  echo "请手动检查并更新这些文件"
else
  echo "✅ 没有找到旧系统引用"
fi

echo ""
echo "✨ 迁移完成！"
echo ""
echo "后续步骤:"
echo "1. cd $FLUTTER_APP_DIR && flutter clean"
echo "2. flutter pub get"
echo "3. flutter analyze"
echo "4. flutter run"
```

使用方式:
```bash
chmod +x scripts/migrate_design_system.sh
./scripts/migrate_design_system.sh mobile
```

---

## 参考资源

- **System B 文档**: `mobile/lib/core/design/design_system.dart` (第 1-31 行)
- **ThemeManager 源码**: `mobile/lib/core/design/tokens_v2/theme_manager.dart`
- **响应式系统**: `mobile/lib/core/design/tokens_v2/responsive_system.dart`
- **设计令牌**: `mobile/lib/core/design/tokens_v2/`

---

## 附录：旧系统颜色映射

### System A → System B 的颜色映射

| System A | System B | 描述 |
|----------|----------|------|
| AppDesignTokens.primaryBase (0xFFFF6B35) | DS.brandPrimary | 主品牌色（orangy） |
| AppDesignTokens.primaryLight | DS.brandPrimary.withOpacity(0.7) | 亮色变体 |
| AppDesignTokens.secondaryBase | DS.brandSecondary | 次要品牌色（深蓝） |
| AppDesignTokens.neutral* | DS.textSecondary.withOpacity(...) | 中立灰色 |
| AppDesignTokens.success | DS.success (0xFF81C784) | 成功/绿色 |
| AppDesignTokens.warning | DS.warning (0xFFFFB74D) | 警告/橙色 |
| AppDesignTokens.error | DS.error (0xFFEF5350) | 错误/红色 |
| AppDesignTokens.info | DS.info (0xFF64B5F6) | 信息/蓝色 |

### 任务类型颜色（System A → System B）

| 任务类型 | System A 值 | System B 值 | RGB |
|---------|-----------|-----------|-----|
| Learning | 0xFF64B5F6 | DS.taskLearning | 蓝色 |
| Training | 0xFFFF9800 | DS.taskTraining | 橙色 |
| Error Fix | 0xFFEF5350 | DS.taskErrorFix | 红色 |
| Reflection | 0xFF9C27B0 | DS.taskReflection | 紫色 |
| Social | 0xFF81C784 | DS.taskSocial | 绿色 |
| Planning | 0xFF009688 | DS.taskPlanning | 青色 |

---

**总结**: 通过系统化的 5 阶段迁移计划，将 Sparkle 应用的设计系统从三个竞争的系统整合为单一的、可维护的 System B 实现，同时保留所有现有功能并改进开发体验。
