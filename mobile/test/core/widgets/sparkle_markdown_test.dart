import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';

void main() {
  group('normalizeRichText', () {
    test('normalizes CRLF to LF', () {
      expect(
        normalizeRichText('line1\r\nline2'),
        'line1\nline2',
      );
    });

    test('removes zero-width characters', () {
      expect(
        normalizeRichText('hello\u200Bworld'), // ZWSP
        'helloworld',
      );
      expect(
        normalizeRichText('hello\u200Cworld'), // ZWNJ
        'helloworld',
      );
      expect(
        normalizeRichText('hello\uFEFFworld'), // BOM
        'helloworld',
      );
    });

    test('removes replacement character', () {
      expect(
        normalizeRichText('hello\uFFFDworld'),
        'helloworld',
      );
    });

    test('normalizes Unicode bullets to standard dash', () {
      expect(
        normalizeRichText('• item1\n• item2'),
        '- item1\n- item2',
      );
      expect(
        normalizeRichText('● item1\n● item2'),
        '- item1\n- item2',
      );
      expect(
        normalizeRichText('◦ item1\n◦ item2'),
        '- item1\n- item2',
      );
      expect(
        normalizeRichText('‣ item1\n‣ item2'),
        '- item1\n- item2',
      );
    });

    test('normalizes ambiguous question mark bullets', () {
      expect(
        normalizeRichText('? **标题**\n？ 其他条目'),
        '- **标题**\n- 其他条目',
      );
    });

    test('normalizes dash bullets', () {
      expect(
        normalizeRichText('— item1\n– item2'),
        '- item1\n- item2',
      );
      expect(
        normalizeRichText('－ item1'),
        '- item1',
      );
    });

    test('normalizes Chinese numbered lists', () {
      expect(
        normalizeRichText('1、第一项\n2、第二项'),
        '1. 第一项\n2. 第二项',
      );
    });

    test('normalizes parenthesized numbers (half-width only)', () {
      expect(
        normalizeRichText('(1) 第一项'),
        '1. 第一项',
      );
    });

    test('ensures space after list markers', () {
      expect(
        normalizeRichText('-item1\n*item2'),
        '- item1\n* item2',
      );
      expect(
        normalizeRichText('1.item1\n2.item2'),
        '1. item1\n2. item2',
      );
    });

    test('ensures space after heading markers', () {
      expect(
        normalizeRichText('#Heading\n##Subheading'),
        '# Heading\n## Subheading',
      );
    });

    test('ensures space after blockquote marker', () {
      expect(
        normalizeRichText('>Quote'),
        '> Quote',
      );
    });

    test('fixes dash-bold without space', () {
      expect(
        normalizeRichText('-**Bold item**'),
        '- **Bold item**',
      );
    });

    test('preserves legitimate question marks', () {
      expect(
        normalizeRichText('What is this?'),
        'What is this?',
      );
      expect(
        normalizeRichText('这是一个问题？'),
        '这是一个问题？',
      );
    });

    test('preserves emoji joined by ZWJ', () {
      expect(
        normalizeRichText('👨‍💻 developer'),
        '👨‍💻 developer',
      );
    });

    test('preserves color emoji variation selector', () {
      expect(
        normalizeRichText('❤️ heart'),
        '❤️ heart',
      );
    });

    test('handles complex mixed input', () {
      final input = '''
• **标题1** - 描述
? **标题2**
— 普通条目
1、数字条目
(1) 括号数字
''';
      final result = normalizeRichText(input);
      expect(result, contains('- **标题1**'));
      expect(result, contains('- **标题2**'));
      expect(result, contains('- 普通条目'));
      expect(result, contains('1. 数字条目'));
      expect(result, contains('1. 括号数字'));
    });

    test('does not convert question marks in middle of text', () {
      expect(
        normalizeRichText('Hello? World'),
        'Hello? World',
      );
    });

    test('handles empty input', () {
      expect(normalizeRichText(''), '');
    });

    test('handles whitespace-only input', () {
      expect(normalizeRichText('   \n\n   '), '   \n\n   ');
    });
  });

  group('SparkleMarkdown widget', () {
    testWidgets('renders without crashing', (tester) async {
      await tester.pumpWidget(
        const _TestWidget(
          content: 'Hello **world**',
        ),
      );
      expect(find.text('Hello world', findRichText: true), findsOneWidget);
    });

    testWidgets('renders list with safe bullet dots', (tester) async {
      await tester.pumpWidget(
        const _TestWidget(
          content: '- Item 1\n- Item 2\n- Item 3',
        ),
      );
      expect(find.text('Item 1', findRichText: true), findsOneWidget);
      expect(find.text('Item 2', findRichText: true), findsOneWidget);
      expect(find.text('Item 3', findRichText: true), findsOneWidget);
    });

    testWidgets('renders ordered list correctly', (tester) async {
      await tester.pumpWidget(
        const _TestWidget(
          content: '1. First\n2. Second\n3. Third',
        ),
      );
      expect(find.text('First', findRichText: true), findsOneWidget);
      expect(find.text('Second', findRichText: true), findsOneWidget);
      expect(find.text('Third', findRichText: true), findsOneWidget);
    });
  });
}

class _TestWidget extends StatelessWidget {
  const _TestWidget({
    required this.content,
  });

  final String content;

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: Scaffold(
          body: SparkleMarkdown(
            content: content,
            textColor: DS.textPrimary,
            codeBackgroundColor: DS.surfaceSecondary,
            linkColor: DS.brandPrimary,
          ),
        ),
      );
}
