#!/usr/bin/env dart
/// 检查中英文翻译覆盖率
/// 运行：dart scripts/i18n_coverage_check.dart (从项目根目录)

import 'dart:convert';
import 'dart:io';

void main() {
  // 获取项目根目录
  final scriptFile = File(Platform.script.toFilePath());
  final projectRoot = scriptFile.parent.parent;

  final zhFile = File('${projectRoot.path}/mobile/lib/l10n/app_zh.arb');
  final enFile = File('${projectRoot.path}/mobile/lib/l10n/app_en.arb');

  if (!zhFile.existsSync()) {
    stderr.writeln('错误: 找不到 app_zh.arb 文件 (${zhFile.path})');
    exit(1);
  }

  if (!enFile.existsSync()) {
    stderr.writeln('错误: 找不到 app_en.arb 文件 (${enFile.path})');
    exit(1);
  }

  final zhContent = jsonDecode(zhFile.readAsStringSync()) as Map;
  final enContent = jsonDecode(enFile.readAsStringSync()) as Map;

  final zhKeys = zhContent.keys.where((k) => !k.startsWith('@')).toSet();
  final enKeys = enContent.keys.where((k) => !k.startsWith('@')).toSet();

  final missingInEn = zhKeys.difference(enKeys);
  final missingInZh = enKeys.difference(zhKeys);

  print('=== 翻译覆盖率报告 ===');
  print('中文键数: ${zhKeys.length}');
  print('英文键数: ${enKeys.length}');
  print('');

  if (missingInEn.isNotEmpty) {
    print('英文缺失 (${missingInEn.length}):');
    missingInEn.take(10).forEach((k) => print('  - $k'));
    if (missingInEn.length > 10) {
      print('  ... 还有 ${missingInEn.length - 10} 个');
    }
    print('');
  }

  if (missingInZh.isNotEmpty) {
    print('中文缺失 (${missingInZh.length}):');
    missingInZh.take(10).forEach((k) => print('  - $k'));
    if (missingInZh.length > 10) {
      print('  ... 还有 ${missingInZh.length - 10} 个');
    }
    print('');
  }

  final coverage = (enKeys.length / zhKeys.length * 100).round();
  print('覆盖率: $coverage%');

  if (coverage < 95) {
    stderr.writeln('错误: 翻译覆盖率低于 95%');
    exit(1);
  }

  print('✅ 翻译覆盖率检查通过');
  exit(0);
}
