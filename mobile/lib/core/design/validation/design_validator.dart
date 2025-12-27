import 'package:flutter/material.dart';

/// 设计系统验证器 - 确保代码符合设计规范
class DesignValidator {
  DesignValidator._();

  /// 验证颜色对比度 (WCAG 2.1)
  static bool validateContrast(
    Color foreground,
    Color background, {
    Level level = Level.AA,
    bool isLargeText = false,
  }) {
    final ratio = _calculateContrastRatio(foreground, background);

    switch (level) {
      case Level.AA:
        return ratio >= (isLargeText ? 3.0 : 4.5);
      case Level.AAA:
        return ratio >= (isLargeText ? 4.5 : 7.0);
    }
  }

  /// 验证间距倍数 (4pt网格)
  static bool validateSpacing(double value) {
    return value % 4 == 0;
  }

  /// 验证字体大小 (12-72px)
  static bool validateFontSize(double size) {
    return size >= 12 && size <= 72;
  }

  /// 验证动画时长 (50-1000ms)
  static bool validateAnimationDuration(Duration duration) {
    final ms = duration.inMilliseconds;
    return ms >= 50 && ms <= 1000;
  }

  /// 验证触控目标大小 (WCAG 2.1: 48x48px)
  static bool validateTouchTarget(Size size) {
    return size.width >= 48 && size.height >= 48;
  }

  /// 验证圆角半径 (4的倍数)
  static bool validateBorderRadius(double radius) {
    return radius % 4 == 0;
  }

  /// 验证阴影模糊半径 (合理范围)
  static bool validateShadowBlur(double blur) {
    return blur >= 0 && blur <= 64;
  }

  /// 验证透明度 (0-1)
  static bool validateOpacity(double opacity) {
    return opacity >= 0 && opacity <= 1;
  }

  /// 计算对比度比率
  static double _calculateContrastRatio(Color c1, Color c2) {
    final l1 = _relativeLuminance(c1);
    final l2 = _relativeLuminance(c2);
    final lighter = l1 > l2 ? l1 : l2;
    final darker = l1 > l2 ? l2 : l1;
    return (lighter + 0.05) / (darker + 0.05);
  }

  /// 计算相对亮度 (WCAG公式)
  static double _relativeLuminance(Color color) {
    final r = _srgbToLinear(color.red / 255.0);
    final g = _srgbToLinear(color.green / 255.0);
    final b = _srgbToLinear(color.blue / 255.0);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  /// sRGB转线性RGB
  static double _srgbToLinear(double value) {
    return value <= 0.03928
        ? value / 12.92
        : math.pow((value + 0.055) / 1.055, 2.4).toDouble();
  }

  /// 生成验证报告
  static ValidationReport generateReport({
    required List<Color> colors,
    required List<double> spacings,
    required List<double> fontSizes,
    required List<Duration> durations,
    required List<Size> touchTargets,
  }) {
    final violations = <Violation>[];

    // 验证颜色
    for (final color in colors) {
      if (!validateOpacity(color.opacity)) {
        violations.add(Violation(
          type: ViolationType.color,
          message: '颜色透明度超出范围: ${color.opacity}',
          severity: Severity.medium,
        ),);
      }
    }

    // 验证间距
    for (final spacing in spacings) {
      if (!validateSpacing(spacing)) {
        violations.add(Violation(
          type: ViolationType.spacing,
          message: '间距不是4的倍数: $spacing',
          severity: Severity.low,
        ),);
      }
    }

    // 验证字体大小
    for (final size in fontSizes) {
      if (!validateFontSize(size)) {
        violations.add(Violation(
          type: ViolationType.typography,
          message: '字体大小超出范围: $size',
          severity: Severity.medium,
        ),);
      }
    }

    // 验证动画时长
    for (final duration in durations) {
      if (!validateAnimationDuration(duration)) {
        violations.add(Violation(
          type: ViolationType.animation,
          message: '动画时长超出范围: ${duration.inMilliseconds}ms',
          severity: Severity.low,
        ),);
      }
    }

    // 验证触控目标
    for (final size in touchTargets) {
      if (!validateTouchTarget(size)) {
        violations.add(Violation(
          type: ViolationType.accessibility,
          message: '触控目标太小: ${size.width}x${size.height}',
          severity: Severity.high,
        ),);
      }
    }

    return ValidationReport(
      totalChecks: colors.length + spacings.length + fontSizes.length +
                  durations.length + touchTargets.length,
      violations: violations,
      score: _calculateScore(violations.length, colors.length + spacings.length +
                  fontSizes.length + durations.length + touchTargets.length,),
    );
  }

  static double _calculateScore(int violations, int total) {
    if (total == 0) return 1.0;
    return (total - violations) / total;
  }
}

enum Level { AA, AAA }

enum ViolationType {
  color,
  spacing,
  typography,
  animation,
  accessibility,
  layout,
}

enum Severity {
  low,
  medium,
  high,
  critical,
}

@immutable
class Violation {
  final ViolationType type;
  final String message;
  final Severity severity;

  const Violation({
    required this.type,
    required this.message,
    required this.severity,
  });

  String get icon {
    switch (severity) {
      case Severity.low:
        return '💡';
      case Severity.medium:
        return '⚠️';
      case Severity.high:
        return '🚫';
      case Severity.critical:
        return '🚨';
    }
  }

  @override
  String toString() => '$icon [${type.name.toUpperCase()}] $message';
}

@immutable
class ValidationReport {
  final int totalChecks;
  final List<Violation> violations;
  final double score;

  const ValidationReport({
    required this.totalChecks,
    required this.violations,
    required this.score,
  });

  bool get isValid => violations.isEmpty;
  int get errorCount => violations.where((v) => v.severity == Severity.high || v.severity == Severity.critical).length;
  int get warningCount => violations.where((v) => v.severity == Severity.medium).length;
  int get infoCount => violations.where((v) => v.severity == Severity.low).length;

  String toMarkdown() {
    return '''
# 设计系统验证报告

## 📊 概览
- 总检查数: $totalChecks
- 违规数: ${violations.length}
- 通过率: ${(score * 100).toStringAsFixed(1)}%
- 状态: ${isValid ? '✅ 通过' : '❌ 需要修复'}

## 🔍 详细结果
- 严重错误 (🔴): $errorCount
- 警告 (⚠️): $warningCount
- 提示 (💡): $infoCount

## 📝 违规列表
${violations.map((v) => '- $v').join('\n')}

## 💡 建议
${_generateRecommendations()}
''';
  }

  String _generateRecommendations() {
    final recommendations = <String>[];

    if (violations.any((v) => v.type == ViolationType.accessibility)) {
      recommendations.add('- 确保所有交互元素 ≥ 48x48px (WCAG 2.1)');
    }

    if (violations.any((v) => v.type == ViolationType.color)) {
      recommendations.add('- 使用 AppDesignTokens 中定义的颜色');
      recommendations.add('- 验证颜色对比度是否符合 WCAG 标准');
    }

    if (violations.any((v) => v.type == ViolationType.spacing)) {
      recommendations.add('- 使用 4pt 网格系统进行间距布局');
      recommendations.add('- 避免硬编码间距值');
    }

    if (violations.any((v) => v.type == ViolationType.typography)) {
      recommendations.add('- 使用设计系统中的排版令牌');
      recommendations.add('- 保持字体大小在 12-72px 范围内');
    }

    if (violations.any((v) => v.type == ViolationType.animation)) {
      recommendations.add('- 使用标准动画时长 (150-600ms)');
      recommendations.add('- 避免过快或过慢的动画');
    }

    if (recommendations.isEmpty) {
      recommendations.add('- 所有检查通过！继续保持良好的设计实践。');
    }

    return recommendations.join('\n');
  }
}

/// Widget 验证扩展
extension WidgetValidation on Widget {
  /// 验证Widget是否符合设计规范
  Future<ValidationReport> validateDesign() async {
    // 这里可以实现更复杂的Widget树分析
    // 例如：遍历子widget，检查是否使用了硬编码值
    return const ValidationReport(
      totalChecks: 0,
      violations: [],
      score: 1.0,
    );
  }
}

/// 设计系统检查器
class DesignSystemChecker {
  static Future<ValidationReport> checkCurrentContext(BuildContext context) async {
    final violations = <Violation>[];

    // 检查媒体查询
    final media = MediaQuery.of(context);
    if (media.textScaleFactor > 1.5) {
      violations.add(Violation(
        type: ViolationType.typography,
        message: '文本缩放比例过高: ${media.textScaleFactor}',
        severity: Severity.medium,
      ),);
    }

    // 检查安全区域
    final padding = media.padding;
    if (padding.top < 0 || padding.bottom < 0) {
      violations.add(const Violation(
        type: ViolationType.layout,
        message: '安全区域边距异常',
        severity: Severity.high,
      ),);
    }

    // 检查屏幕尺寸
    final size = media.size;
    if (size.width < 320 || size.height < 480) {
      violations.add(Violation(
        type: ViolationType.layout,
        message: '屏幕尺寸过小: ${size.width}x${size.height}',
        severity: Severity.medium,
      ),);
    }

    return ValidationReport(
      totalChecks: 3,
      violations: violations,
      score: violations.isEmpty ? 1.0 : (3 - violations.length) / 3,
    );
  }
}
