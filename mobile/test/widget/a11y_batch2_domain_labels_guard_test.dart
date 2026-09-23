import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// A11Y-BATCH2/3/4（N32 续 · 无名钮下批）域内 ratchet 守卫。
///
/// 卡面验收「本批域内无名钮清零」：批 2 三域——friends 族 / sprint 族 /
/// user 设置族（features/user + features/settings presentation 全量），
/// 批 3 四域（A11Y-BATCH3 扩域）——群组族（group 相关屏 + 群组件 +
/// group_chat）/ galaxy 域 / insights 域 / plan_create 族，批 4 四域
/// （A11Y-BATCH4 扩域）——seed_library 域 / error_book 域 / chat 域
/// （presentation 全量 + data 层通知浮窗；群聊批 3 已清零）/
/// community 域（presentation 全量，群组批 3 已清零）——做静态扫描，
/// 任何 `SparkleIconButton` / `IconButton` 调用点（含 `.fabGeometry` 等
/// 命名构造，批 3 起入扫）必须可命名：
///
/// 1. `semanticLabel:`（首选，l10n）；
/// 2. `tooltip:`（material IconButton 并入语义名；SparkleIconButton 需
///    显式 semanticLabel，故两者都计为已命名——wrapper Tooltip 不计，
///    因其只挂 semantics.tooltip 不构成按钮名）；
/// 3. 反推：icon 为 `Icon(...)` 且自带 `semanticLabel:`（组件层反推链）。
///
/// 形制照 A11Y-ICONS（wt256）首批；ratchet 只降不升——本测试失败即批域
/// 出现新无名钮，按 N31 登记制当场补名。
void main() {
  final batchScopes = <String>[
    // friends 族
    'lib/features/community/presentation/screens/friends_screen.dart',
    'lib/features/community/presentation/screens/friend_profile_screen.dart',
    'lib/features/community/presentation/screens/user_search_screen.dart',
    'lib/features/community/presentation/screens/blocked_users_screen.dart',
    'lib/features/community/presentation/widgets/friends_hub_view.dart',
    // sprint 族
    'lib/features/plan/presentation/screens/sprint_screen.dart',
    'lib/features/plan/presentation/screens/sprint_history_screen.dart',
    'lib/features/plan/presentation/screens/sprint_completion_screen.dart',
    'lib/features/plan/presentation/screens/sprint_review_screen.dart',
    'lib/features/plan/presentation/screens/exam_sprint_setup_screen.dart',
    // user 设置族（presentation 全量：screens + widgets）
    'lib/features/user/presentation/screens',
    'lib/features/user/presentation/widgets',
    'lib/features/settings/presentation/screens',
    'lib/features/settings/presentation/widgets',
    // ── 批 3（A11Y-BATCH3）扩域 ────────────────────────────────────────
    // 群组族（group 相关屏 + 群组件 + 群聊）
    'lib/features/community/presentation/screens/group_list_screen.dart',
    'lib/features/community/presentation/screens/create_group_screen.dart',
    'lib/features/community/presentation/screens/group_detail_screen.dart',
    'lib/features/community/presentation/screens/group_members_screen.dart',
    'lib/features/community/presentation/screens/group_moderation_screen.dart',
    'lib/features/community/presentation/screens/group_tasks_screen.dart',
    'lib/features/community/presentation/screens/group_search_screen.dart',
    'lib/features/community/presentation/screens/group_discover_screen.dart',
    'lib/features/community/presentation/screens/group_files_screen.dart',
    'lib/features/community/presentation/screens/squad_list_screen.dart',
    'lib/features/community/presentation/widgets/groups_hub_view.dart',
    'lib/features/community/presentation/widgets/groups_tab.dart',
    'lib/features/community/presentation/widgets/group_knowledge_base_view.dart',
    'lib/features/community/presentation/widgets/group_recommendation_card.dart',
    'lib/features/community/presentation/widgets/group_chat_bubble.dart',
    'lib/features/chat/presentation/screens/group_chat_screen.dart',
    // galaxy 域（presentation 全量）
    'lib/features/galaxy/presentation',
    // insights 域（presentation 全量）
    'lib/features/insights/presentation',
    // plan_create 族（创建/编辑/详情同簇）
    'lib/features/plan/presentation/screens/plan_create_screen.dart',
    'lib/features/plan/presentation/screens/plan_edit_screen.dart',
    'lib/features/plan/presentation/screens/plan_detail_screen.dart',
    // ── 批 4（A11Y-BATCH4）扩域 ────────────────────────────────────────
    // seed_library 域（presentation 全量：screens + marketplace）
    'lib/features/seed_library/presentation',
    // error_book 域（presentation 全量）
    'lib/features/error_book/presentation',
    // chat 域（presentation 全量；group_chat 批 3 已清零）
    'lib/features/chat/presentation',
    // chat data 层通知浮窗（服务内嵌 UI，静态扫描同样入扫）
    'lib/features/chat/data/services/message_notification_service.dart',
    // community 域（presentation 全量；群组批 3 已清零）
    'lib/features/community/presentation',
  ];

  test('批域内图标按钮全部有语义名（N31 ratchet 只降不升）', () {
    final violations = <String>[];

    for (final scope in batchScopes) {
      for (final path in _dartFiles(scope)) {
        final findings = _scanUnnamedButtons(File(path).readAsStringSync());
        for (final line in findings) {
          violations.add('$path:$line');
        }
      }
    }

    expect(
      violations,
      isEmpty,
      reason: '批域出现无名图标钮（icon-only button without semanticLabel）'
          '——按 N31 登记制补 semanticLabel（l10n zh/en）或 tooltip：\n'
          '${violations.join('\n')}',
    );
  });
}

/// 展开作用域为 dart 源文件清单（跳过生成物）。
List<String> _dartFiles(String scope) {
  final type = FileSystemEntity.typeSync(scope);
  if (type == FileSystemEntityType.file) {
    return [scope];
  }
  final dir = Directory(scope);
  if (!dir.existsSync()) {
    throw StateError('batch scope missing: $scope');
  }
  return dir
      .listSync(recursive: true)
      .whereType<File>()
      .map((f) => f.path.replaceAll(r'\', '/'))
      .where((p) => p.endsWith('.dart'))
      .where(
        (p) =>
            !p.endsWith('.g.dart') &&
            !p.endsWith('.freezed.dart') &&
            !p.endsWith('.gr.dart'),
      )
      .toList()
    ..sort();
}

// --- 静态扫描（与 A11Y-ICONS 批内盘点同口径） --------------------------

final _blockComment = RegExp(r'/\*.*?\*/', dotAll: true);

/// 行注释：`//` 前面不是 `:`（放行 'https://' 类 scheme 字面量）。
final _lineComment = RegExp(r'(?<!:)//[^\n]*');

final _buttonCall = RegExp(r'\b(SparkleIconButton|IconButton)(\.\w+)?\s*\(');
final _iconCall = RegExp(r'\bIcon\s*\(');

/// 返回未命名钮所在行号清单（基于注释剥离后的文本）。
List<int> _scanUnnamedButtons(String source) {
  final clean = source
      .replaceAll(_blockComment, '')
      .replaceAll(_lineComment, '');
  final lines = clean.split('\n');
  final findings = <int>[];

  for (final match in _buttonCall.allMatches(clean)) {
    final args = _balanced(clean, match.end - 1);
    final named = args.contains('semanticLabel:') ||
        args.contains('tooltip:') ||
        _iconSelfLabeled(args);
    if (!named) {
      findings.add(_lineOf(lines, match.start));
    }
  }
  return findings;
}

/// icon 自带 semanticLabel（组件反推链的事实源）。
bool _iconSelfLabeled(String args) {
  for (final match in _iconCall.allMatches(args)) {
    if (_balanced(args, match.end - 1).contains('semanticLabel:')) {
      return true;
    }
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
