import 'dart:io';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:path/path.dart' as path;

/// 设计系统合规检查工具
///
/// 用于检查代码中的设计系统违规，包括：
/// 1. 硬编码颜色值
/// 2. 硬编码间距值
/// 3. 未使用设计系统组件
class DesignSystemLinter {
  final String projectRoot;
  final List<String> _violations = [];

  DesignSystemLinter(this.projectRoot);

  /// 运行所有检查
  Future<List<String>> runAllChecks() async {
    _violations.clear();

    await _checkHardcodedColors();
    await _checkHardcodedSpacing();
    await _checkMaterialButtonUsage();

    return _violations;
  }

  /// 检查硬编码颜色值
  Future<void> _checkHardcodedColors() async {
    final dartFiles = await _findDartFiles();

    for (final file in dartFiles) {
      final content = await File(file).readAsString();
      final lines = content.split('\n');

      for (int i = 0; i < lines.length; i++) {
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

      for (int i = 0; i < lines.length; i++) {
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

      for (int i = 0; i < lines.length; i++) {
        final line = lines[i];

        // 检查Material按钮使用
        if (_containsMaterialButton(line)) {
          _violations.add('$file:${i + 1}: 使用Material按钮 - $line');
        }
      }
    }
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
            !relativePath.contains('generated')) {
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
      RegExp(r'Color\(0x[0-9A-F]{8}\)'), // Color(0xFF6B35)
      RegExp(r'Colors\.\w+'),           // DS.brandPrimary, DS.brandPrimary
      RegExp(r'const Color\.\w+'),      // const Color.white
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
    final spacingPattern = RegExp(r'(EdgeInsets|SizedBox|padding|margin).*[^DS\.\s](4|8|12|16|24|32|48|64)');
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
      'ElevatedButton(',
      'TextButton(',
      'IconButton(',
      'OutlinedButton(',
      'FloatingActionButton(',
    ];

    for (final pattern in buttonPatterns) {
      if (line.contains(pattern)) {
        // 排除设计系统文件
        if (line.contains('design_system_linter.dart')) {
          return false;
        }
        return true;
      }
    }

    return false;
  }

  /// 生成检查报告
  String generateReport(List<String> violations) {
    final buffer = StringBuffer();

    buffer.writeln('=' * 80);
    buffer.writeln('设计系统合规检查报告');
    buffer.writeln('=' * 80);
    buffer.writeln('检查时间: ${DateTime.now()}');
    buffer.writeln('项目根目录: $projectRoot');
    buffer.writeln('违规数量: ${violations.length}');
    buffer.writeln();

    if (violations.isEmpty) {
      buffer.writeln('✅ 恭喜！未发现设计系统违规。');
    } else {
      buffer.writeln('⚠️ 发现以下设计系统违规：');
      buffer.writeln();

      // 按违规类型分组
      final colorViolations = violations.where((v) => v.contains('硬编码颜色')).toList();
      final spacingViolations = violations.where((v) => v.contains('硬编码间距')).toList();
      final buttonViolations = violations.where((v) => v.contains('使用Material按钮')).toList();

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

      buffer.writeln('💡 修复建议：');
      buffer.writeln('  1. 硬编码颜色 → 使用 DS.brandPrimary, DS.success 等');
      buffer.writeln('  2. 硬编码间距 → 使用 DS.lg, DS.xl 等');
      buffer.writeln('  3. Material按钮 → 使用 SparkleButton.primary() 等');
    }

    buffer.writeln('=' * 80);

    return buffer.toString();
  }

  /// 运行检查并打印报告
  static Future<void> runAndPrint(String projectRoot) async {
    final linter = DesignSystemLinter(projectRoot);
    final violations = await linter.runAllChecks();
    final report = linter.generateReport(violations);

    print(report);

    // 保存报告到文件
    final reportFile = File(path.join(projectRoot, 'design_system_report.txt'));
    await reportFile.writeAsString(report);
    print('报告已保存到: ${reportFile.path}');
  }
}

/// 命令行入口
void main(List<String> args) async {
  final projectRoot = args.isNotEmpty ? args[0] : Directory.current.path;

  print('开始设计系统合规检查...');
  print('项目目录: $projectRoot');
  print('');

  await DesignSystemLinter.runAndPrint(projectRoot);
}