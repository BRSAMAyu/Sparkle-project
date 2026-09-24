import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/structured_suggestion_body.dart';

/// U-05 Chat 屏 L2：长建议结构化呈现（proposal 式条目）的确定性探测与
/// 渲染回归锚点。结构探测是纯静态规则（列表语法 ≥2 条、无围栏代码块），
/// 不涉及任何语义判定；无结构/含代码块内容必须回退原 markdown 渲染。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('StructuredSuggestionBody.hasListStructure', () {
    test('numbered list with intro prose is structured', () {
      const content = '针对你的瓶颈，我建议按下面三步走：\n\n'
          '1. 先把第二章的错题按错因归类；\n'
          '2. 每类只重做最典型的 3 道；\n'
          '3. 周末做一次 30 分钟限时小测。\n';
      expect(StructuredSuggestionBody.hasListStructure(content), isTrue);
    });

    test('bullet list is structured', () {
      const content = '可以这样拆解：\n\n- 每天固定 25 分钟\n- 只刷一类题型\n';
      expect(StructuredSuggestionBody.hasListStructure(content), isTrue);
    });

    test('plain prose without list markers is not structured', () {
      final content = List.filled(
        8,
        '这是一个很长的纯文本建议，没有任何列表结构，'
        '所以应当保持原有 markdown 渲染路径，不做结构化拆分。',
      ).join();
      expect(StructuredSuggestionBody.hasListStructure(content), isFalse);
    });

    test('fenced code blocks disable structuring (fallback to markdown)', () {
      const content = '建议如下：\n\n- 第一点\n- 第二点\n\n'
          '```python\nprint("hello")\n```\n';
      expect(StructuredSuggestionBody.hasListStructure(content), isFalse);
    });
  });

  group('StructuredSuggestionBody rendering', () {
    Future<void> pumpBody(WidgetTester tester, String content) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: StructuredSuggestionBody(
                content: content,
                textColor: const Color(0xFF111111),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('renders numbered items as proposal rows with badges',
        (tester) async {
      await pumpBody(
        tester,
        '先给你一个整体判断：现在的路线没问题。\n\n'
        '1. 把错题按错因归类；\n'
        '2. 每类只重做最典型的三道；\n',
      );
      // prose 段保留原文渲染。
      expect(find.textContaining('整体判断'), findsOneWidget);
      // 条目内容按 proposal 行渲染。
      expect(find.textContaining('错因归类'), findsOneWidget);
      expect(find.textContaining('最典型的三道'), findsOneWidget);
    });

    testWidgets('single item list falls back to plain markdown rendering',
        (tester) async {
      const content = '只有一条：把今天的任务做完。';
      expect(StructuredSuggestionBody.hasListStructure(content), isFalse);
      await pumpBody(tester, content);
      expect(find.textContaining('把今天的任务做完'), findsOneWidget);
    });
  });
}
