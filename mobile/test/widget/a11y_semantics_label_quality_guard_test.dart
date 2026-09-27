import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// A11Y-U08 续（wt674）· Semantics 标签质量守卫。
///
/// 卡面 U-08 验收「语义标签补齐」的 ratchet 钉子，两条禁入面：
///
/// 1. **占位标签禁入**：库存量 63 处 `Semantics(label: 'Chat xxx control N')`
///    硬编码开发者占位串——静态盘点曾把它们计作「已命名」，实为读屏不可懂的
///    开发黑话（不诚实面，V3-FIX-359），本轮全部清零（真实 l10n 名/内容合并
///    名/废除拆节点）。本测试钉死 `control <数字>` 占位模式不再回流。
///
/// 2. **无名图标钮禁入**：`InkWell`/`GestureDetector` 直接包裹裸 `Icon(` 且
///    子树与语义祖先均不提供名字（无 Text/Semantics/Tooltip、Icon 无
///    semanticLabel）= 读屏匿名可点节点。现存 7 文件存量已登记 V3-FIX-360
///    （补名需新增 l10n 键或参数化改签名，超本轮机械项边界），以 allowlist
///    钉存量——**只降不升**。
///
/// 形制照 a11y_batch2_domain_labels_guard（N31/N32 棘轮族）；ratchet 只降不升。
void main() {
  const scanRoots = <String>['lib'];
  const scanExemptions = <String>[
    // 组件库定义层（守卫族同款豁免）：类定义/包装器自身，非调用点。
    'lib/core/design/',
    'lib/l10n',
    // gen 产物
    '.g.dart',
    '.freezed.dart',
    '.gr.dart',
  ];

  /// V3-FIX-360 存量（file → 缘由）；只许减少，不许新增。
  const unnamedIconClickAllowlist = <String, String>{
    // 泛化 icon 参数钮：可访问名需调用方传参（改签名 + 全调用点补名）。
    'lib/features/home/presentation/widgets/calendar/compact_task_card.dart':
        '泛化 icon 参数钮，需调用方传 semanticLabel（V3-FIX-360）',
    // 成就视图切换（grid/list 两钮）：视图名需新增 l10n 键。
    'lib/features/achievement/presentation/screens/achievement_list_screen.dart':
        '视图切换钮名需新增 l10n 键（V3-FIX-360）',
    // 需新增 l10n 键对（收藏/取消收藏），arb 键面归文案卡管。
    'lib/features/translation/presentation/screens/translation_history_screen.dart':
        '收藏星钮两态名需新增 l10n 键（V3-FIX-360）',
    'lib/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart':
        '预览开/关两态名需新增 l10n 键（V3-FIX-360）',
    // 快捷排期图标钮语义名需新增 l10n 键。
    'lib/features/calendar/presentation/widgets/smart_schedule_chip.dart':
        '快捷排期钮需新增 l10n 键（V3-FIX-360）',
    // 色板选择器：色名键 + 32px 触控目标，属结构性改造面。
    'lib/features/calendar/presentation/screens/calendar_stats_screen.dart':
        '色板选择器需色名键+触控目标改造（V3-FIX-360）',
    // 2D 拖拽把手：slider 语义（adjustable + value），结构性改造面。
    'lib/features/user/presentation/widgets/preference_controller_2d.dart':
        '拖拽把手需 slider 语义（adjustable+value）（V3-FIX-360）',
  };

  test('占位语义标签（control N 模式）全库清零（V3-FIX-359 ratchet 只降不升）', () {
    final violations = <String>[];
    final pattern = RegExp(r'control \d');

    for (final path in _dartFiles(scanRoots, scanExemptions)) {
      final lines = File(path).readAsLinesSync();
      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        if (line.trim().startsWith('//')) continue; // 历史注记豁免
        if (line.contains("label: '") && pattern.hasMatch(line)) {
          violations.add('$path:${i + 1}: ${line.trim()}');
        }
      }
    }

    expect(
      violations,
      isEmpty,
      reason: '出现新的占位语义标签——读屏用户听到的是开发者黑话而非界面语言，'
          '按 N31 登记制补真实 l10n 名：\n${violations.join('\n')}',
    );
  });

  test('无名图标可点节点存量钉死（V3-FIX-360 allowlist 只降不升）', () {
    final violations = <String>[];

    for (final path in _dartFiles(scanRoots, scanExemptions)) {
      if (unnamedIconClickAllowlist.containsKey(path)) continue;
      final findings = _scanUnnamedIconClicks(File(path).readAsStringSync());
      for (final line in findings) {
        violations.add('$path:$line');
      }
    }

    expect(
      violations,
      isEmpty,
      reason: '出现新的无名图标可点节点（InkWell/GestureDetector 包裸 Icon 且'
              '无任何语义名）——按 N31 登记制补 semanticLabel 或入 V3-FIX-360 '
              'allowlist（只减不增）：\n${violations.join('\n')}',
    );
  });

  test('allowlist 条目仍真实存在（存量清走须同步摘行，防僵尸豁免）', () {
    for (final path in unnamedIconClickAllowlist.keys) {
      final file = File(path);
      if (!file.existsSync()) {
        fail('allowlist 文件已删除，请同步摘除豁免行：$path');
      }
      if (_scanUnnamedIconClicks(file.readAsStringSync()).isEmpty) {
        fail('allowlist 文件已无无名图标钮，请同步摘除豁免行：$path');
      }
    }
  });
}

/// 展开扫描根为 dart 源文件清单（守卫族同款：跳过生成物与豁免目录）。
List<String> _dartFiles(List<String> roots, List<String> exemptions) {
  final out = <String>[];
  for (final root in roots) {
    final dir = Directory(root);
    if (!dir.existsSync()) throw StateError('scan root missing: $root');
    for (final f in dir.listSync(recursive: true).whereType<File>()) {
      final p = f.path.replaceAll(r'\', '/');
      if (!p.endsWith('.dart')) continue;
      if (exemptions.any(p.contains)) continue;
      out.add(p);
    }
  }
  return out..sort();
}

final _blockComment = RegExp(r'/\*.*?\*/', dotAll: true);
/// `//` 前面不是 `:`（放行 'https://' 类 scheme 字面量）。
final _lineComment = RegExp(r'(?<!:)//[^\n]*');
final _clickCall = RegExp(r'\b(InkWell|GestureDetector)\s*\(');
final _iconCall = RegExp(r'\bIcon\s*\(');
final _nameProvider =
    RegExp(r'\b(Text\s*\(|Semantics\s*\(|Tooltip\s*\(|semanticLabel:|label:)');

/// 返回无名图标可点节点所在行号（基于注释剥离后的文本）。
///
/// 判名来源（任一即有名）：子树含 Text/Semantics/Tooltip/label 参数、
/// Icon 自带 semanticLabel、任一祖先 Semantics(label:) 或 Tooltip(message:)。
List<int> _scanUnnamedIconClicks(String source) {
  final clean = source
      .replaceAll(_blockComment, '')
      .replaceAll(_lineComment, '');
  final lines = clean.split('\n');
  final findings = <int>[];

  for (final m in _clickCall.allMatches(clean)) {
    final args = _balanced(clean, m.end - 1);
    if (_nameProvider.hasMatch(args)) continue;
    final im = _iconCall.firstMatch(args);
    if (im == null) continue;
    final iconArgs = _balanced(args, im.end - 1);
    if (iconArgs.contains('semanticLabel:')) continue;
    if (_namedByAncestor(clean, m.start)) continue;
    findings.add(_lineOf(lines, m.start));
  }
  return findings;
}

/// 向上找括号配平的祖先调用：Semantics(label:) / Tooltip(message:) 即有名。
bool _namedByAncestor(String clean, int pos) {
  var depth = 0;
  var ancestors = 0;
  var i = pos;
  while (i >= 0 && ancestors < 12) {
    final c = clean[i];
    if (c == ')') depth++;
    if (c == '(') {
      if (depth == 0) {
        ancestors++;
        final headStart = (i - 40).clamp(0, i);
        final nm =
            RegExp(r'\b(Semantics|Tooltip)\s*$').firstMatch(clean.substring(headStart, i));
        if (nm != null) {
          final aargs = _balanced(clean, i);
          final named =
              nm.group(1) == 'Tooltip' || aargs.contains('label:');
          if (named) return true;
        }
      } else {
        depth--;
      }
    }
    i--;
  }
  return false;
}

/// 从 `(` 起取括号配平的参数区文本。
String _balanced(String text, int openParenIndex) {
  var depth = 0;
  for (var i = openParenIndex; i < text.length; i++) {
    final ch = text[i];
    if (ch == '(') depth++;
    if (ch == ')') {
      depth--;
      if (depth == 0) return text.substring(openParenIndex + 1, i);
    }
  }
  return text.substring(openParenIndex + 1);
}

int _lineOf(List<String> lines, int offset) {
  var consumed = 0;
  for (var i = 0; i < lines.length; i++) {
    consumed += lines[i].length + 1;
    if (consumed > offset) return i + 1;
  }
  return lines.length;
}
