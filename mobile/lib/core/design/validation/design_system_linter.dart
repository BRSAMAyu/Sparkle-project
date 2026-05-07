// ignore_for_file: cascade_invocations

import 'dart:io';

import 'package:path/path.dart' as path;

/// 设计系统合规检查工具
///
/// 用于检查代码中的设计系统违规，包括：
/// 1. 硬编码颜色值
/// 2. 硬编码间距值
/// 3. 未使用设计系统组件
class DesignSystemLinter {
  DesignSystemLinter(this.projectRoot);
  final String projectRoot;
  final List<String> _violations = [];

  /// 运行所有检查
  Future<List<String>> runAllChecks() async {
    _violations.clear();

    await _checkHardcodedColors();
    await _checkHardcodedSpacing();
    await _checkHardcodedGradientsAndShadows();
    await _checkMaterialButtonUsage();
    await _checkHardcodedFontSize();
    await _checkHardcodedBorderRadius();

    return _violations;
  }

  /// 检查硬编码颜色值
  Future<void> _checkHardcodedColors() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];

        // 检查硬编码颜色模式
        if (_containsHardcodedColor(line)) {
          _violations.add('$file:${i + 1}: 硬编码颜色 - $line');
        }
      }
    }
  }

  /// 检查硬编码间距值
  Future<void> _checkHardcodedSpacing() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];

        // 检查硬编码间距模式
        if (_containsHardcodedSpacing(line)) {
          _violations.add('$file:${i + 1}: 硬编码间距 - $line');
        }
      }
    }
  }

  /// 检查Material按钮使用
  Future<void> _checkMaterialButtonUsage() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];

        // 检查Material按钮使用
        if (_containsMaterialButton(line)) {
          _violations.add('$file:${i + 1}: 使用Material按钮 - $line');
        }
      }
    }
  }

  /// 检查硬编码渐变、阴影和半透明黑白
  Future<void> _checkHardcodedGradientsAndShadows() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        if (_containsHardcodedGradientOrShadow(line)) {
          _violations.add('$file:${i + 1}: 硬编码渐变/阴影 - $line');
        }
      }
    }
  }

  /// 检查硬编码 fontSize
  Future<void> _checkHardcodedFontSize() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        if (_containsHardcodedFontSize(line)) {
          _violations.add('$file:${i + 1}: 硬编码字号 - $line');
        }
      }
    }
  }

  /// 检查硬编码 BorderRadius
  Future<void> _checkHardcodedBorderRadius() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        if (_containsHardcodedBorderRadius(line)) {
          _violations.add('$file:${i + 1}: 硬编码圆角 - $line');
        }
      }
    }
  }

  bool _containsHardcodedFontSize(String line) {
    if (line.trim().startsWith('//')) return false;
    final pattern = RegExp(r'fontSize:\s*\d+');
    if (!pattern.hasMatch(line)) return false;
    if (line.contains('DS.') ||
        line.contains('AppDesignTokens') ||
        line.contains('design_system_linter.dart')) {
      return false;
    }
    return true;
  }

  bool _containsHardcodedBorderRadius(String line) {
    if (line.trim().startsWith('//')) return false;
    final pattern = RegExp(r'BorderRadius\.circular\(\d+');
    if (!pattern.hasMatch(line)) return false;
    if (line.contains('DS.') ||
        line.contains('AppDesignTokens') ||
        line.contains('design_system_linter.dart')) {
      return false;
    }
    return true;
  }

  /// 查找所有Dart文件
  Future<List<String>> _findDartFiles() async {
    final dartFiles = <String>[];
    final directory = Directory(projectRoot);

    await for (final entity in directory.list(recursive: true)) {
      if (entity is File && entity.path.endsWith('.dart')) {
        // 排除测试文件和生成的文件
        final relativePath = path.relative(entity.path, from: projectRoot);
        if (!relativePath.contains('.g.') &&
            !relativePath.contains('test') &&
            !relativePath.contains('generated') &&
            !relativePath.contains('.dart_tool/') &&
            !relativePath.contains('linux/flutter/ephemeral/') &&
            !relativePath.contains('.plugin_symlinks/') &&
            !relativePath.contains('build/') &&
            !relativePath.contains('core/design/validation/') &&
            !relativePath.contains('core/design/tokens/') &&
            !relativePath.contains('core/design/tokens_v2/') &&
            !relativePath.contains('/domain/') &&
            !relativePath.contains('/data/') &&
            relativePath != 'core/design/design_system.dart' &&
            relativePath != 'core/design/materials.dart' &&
            relativePath != 'core/utils/theme_utils.dart' &&
            relativePath != 'app/theme.dart') {
          dartFiles.add(entity.path);
        }
      }
    }

    return dartFiles;
  }

  /// 检查是否包含硬编码颜色
  bool _containsHardcodedColor(String line) {
    // 排除注释行
    if (line.trim().startsWith('//')) return false;

    // 检查常见的硬编码颜色模式
    final patterns = [
      RegExp(r'Color\(0x[0-9a-fA-F]{8}\)'), // Color(0xFF6B35)
      // Require a word boundary to avoid false positives like `sparkleColors` or `primaryColor`.
      RegExp(r'\bColors\.\w+'), // Colors.white
    ];

    for (final pattern in patterns) {
      if (pattern.hasMatch(line)) {
        // 排除设计系统文件本身
        if (line.contains('AppDesignTokens') ||
            line.contains('DS.') ||
            line.contains('sparkleColors') ||
            line.contains('sparkleTheme')) {
          return false;
        }
        return true;
      }
    }

    return false;
  }

  /// 检查是否包含硬编码间距
  bool _containsHardcodedSpacing(String line) {
    // 排除注释行
    if (line.trim().startsWith('//')) return false;

    // 检查硬编码间距数值
    final spacingPattern = RegExp(
      r'(EdgeInsets|SizedBox|padding|margin).*[^DS\.\s](4|8|12|16|24|32|48|64)',
    );
    if (spacingPattern.hasMatch(line)) {
      // 排除设计系统使用
      if (line.contains('DS.') ||
          line.contains('AppDesignTokens') ||
          line.contains('sparkleSpacing')) {
        return false;
      }
      return true;
    }

    return false;
  }

  /// 检查是否使用Material按钮
  bool _containsMaterialButton(String line) {
    // 排除注释行
    if (line.trim().startsWith('//')) return false;

    // 检查Material按钮组件
    final buttonPatterns = [
      RegExp(r'\bElevatedButton\('),
      RegExp(r'\bTextButton\('),
      RegExp(r'\bIconButton\('),
      RegExp(r'\bOutlinedButton\('),
      RegExp(r'\bFloatingActionButton\('),
    ];

    for (final pattern in buttonPatterns) {
      if (pattern.hasMatch(line)) {
        // 排除设计系统文件
        if (line.contains('design_system_linter.dart')) {
          return false;
        }
        return true;
      }
    }

    return false;
  }

  bool _containsHardcodedGradientOrShadow(String line) {
    if (line.trim().startsWith('//')) return false;

    final patterns = [
      RegExp(r'\bLinearGradient\('),
      RegExp(r'\bRadialGradient\('),
      RegExp(r'\bSweepGradient\('),
      RegExp(r'\bBoxShadow\('),
      RegExp(r'Colors\.(black|white)\.with(?:Opacity|Values)\('),
      RegExp(r'Color\(0x[0-9a-fA-F]{8}\)\.with(?:Opacity|Values)\('),
    ];

    for (final pattern in patterns) {
      if (!pattern.hasMatch(line)) {
        continue;
      }
      if (line.contains('DS.') ||
          line.contains('sparkleTheme') ||
          line.contains('AppThemes') ||
          line.contains('theme_manager.dart') ||
          line.contains('design_system.dart') ||
          line.contains('graphite_surfaces.dart')) {
        return false;
      }
      return true;
    }

    return false;
  }

  /// 生成检查报告
  String generateReport(List<String> violations) {
    final buffer = StringBuffer();

    buffer
      ..writeln('=' * 80)
      ..writeln('设计系统合规检查报告')
      ..writeln('=' * 80)
      ..writeln('检查时间: ${DateTime.now()}')
      ..writeln('项目根目录: $projectRoot')
      ..writeln('违规数量: ${violations.length}')
      ..writeln();

    if (violations.isEmpty) {
      buffer.writeln('✅ 恭喜！未发现设计系统违规。');
    } else {
      buffer
        ..writeln('⚠️ 发现以下设计系统违规：')
        ..writeln();

      // 按违规类型分组
      final colorViolations =
          violations.where((v) => v.contains('硬编码颜色')).toList();
      final spacingViolations =
          violations.where((v) => v.contains('硬编码间距')).toList();
      final gradientViolations =
          violations.where((v) => v.contains('硬编码渐变/阴影')).toList();
      final buttonViolations =
          violations.where((v) => v.contains('使用Material按钮')).toList();
      final fontSizeViolations =
          violations.where((v) => v.contains('硬编码字号')).toList();
      final borderRadiusViolations =
          violations.where((v) => v.contains('硬编码圆角')).toList();

      if (colorViolations.isNotEmpty) {
        buffer.writeln('🔴 硬编码颜色违规 (${colorViolations.length}处):');
        for (final violation in colorViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (colorViolations.length > 10) {
          buffer.writeln('  • ... 还有${colorViolations.length - 10}处');
        }
        buffer.writeln();
      }

      if (spacingViolations.isNotEmpty) {
        buffer.writeln('🟡 硬编码间距违规 (${spacingViolations.length}处):');
        for (final violation in spacingViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (spacingViolations.length > 10) {
          buffer.writeln('  • ... 还有${spacingViolations.length - 10}处');
        }
        buffer.writeln();
      }

      if (gradientViolations.isNotEmpty) {
        buffer.writeln('🟣 硬编码渐变/阴影违规 (${gradientViolations.length}处):');
        for (final violation in gradientViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (gradientViolations.length > 10) {
          buffer.writeln('  • ... 还有${gradientViolations.length - 10}处');
        }
        buffer.writeln();
      }

      if (buttonViolations.isNotEmpty) {
        buffer.writeln('🔵 Material按钮使用 (${buttonViolations.length}处):');
        for (final violation in buttonViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (buttonViolations.length > 10) {
          buffer.writeln('  • ... 还有${buttonViolations.length - 10}处');
        }
        buffer.writeln();
      }

      if (fontSizeViolations.isNotEmpty) {
        buffer.writeln('🟠 硬编码字号 (${fontSizeViolations.length}处):');
        for (final violation in fontSizeViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (fontSizeViolations.length > 10) {
          buffer.writeln('  • ... 还有${fontSizeViolations.length - 10}处');
        }
        buffer.writeln();
      }

      if (borderRadiusViolations.isNotEmpty) {
        buffer.writeln('🟢 硬编码圆角 (${borderRadiusViolations.length}处):');
        for (final violation in borderRadiusViolations.take(10)) {
          buffer.writeln('  • $violation');
        }
        if (borderRadiusViolations.length > 10) {
          buffer.writeln('  • ... 还有${borderRadiusViolations.length - 10}处');
        }
        buffer.writeln();
      }

      buffer
        ..writeln('💡 修复建议：')
        ..writeln('  1. 硬编码颜色 → 使用 DS.brandPrimary, DS.success 等')
        ..writeln('  2. 硬编码间距 → 使用 DS.lg, DS.xl 等')
        ..writeln('  3. 硬编码渐变/阴影 → 使用 DS.*Gradient / DS.shadow* / Graphite 容器')
        ..writeln('  4. Material按钮 → 使用 SparkleButton.primary() 等')
        ..writeln('  5. 硬编码字号 → 使用 DS.fontSizeSm, DS.fontSizeBase, DS.fontSizeLg 等')
        ..writeln('  6. 硬编码圆角 → 使用 DS.radiusSm, DS.radiusMd, DS.radiusLg 等');
    }

    buffer.writeln('=' * 80);

    return buffer.toString();
  }

  /// 运行检查并打印报告
  static Future<void> runAndPrint(String projectRoot) async {
    final linter = DesignSystemLinter(projectRoot);
    final violations = await linter.runAllChecks();
    final report = linter.generateReport(violations);

    stdout.writeln(report);

    // 保存报告到文件
    final reportFile = File(path.join(projectRoot, 'design_system_report.txt'));
    await reportFile.writeAsString(report);
    stdout.writeln('报告已保存到: ${reportFile.path}');
  }
}

/// 命令行入口
void main(List<String> args) async {
  final projectRoot = args.isNotEmpty ? args[0] : Directory.current.path;

  stdout.writeln('开始设计系统合规检查...');
  stdout.writeln('项目目录: $projectRoot');
  stdout.writeln();

  await DesignSystemLinter.runAndPrint(projectRoot);
}
