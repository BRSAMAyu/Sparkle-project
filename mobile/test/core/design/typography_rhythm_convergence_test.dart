import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';

/// TYPE-RHYTHM 卡验收测试（A-SPEC7 v1.7 N41 首案 / N44 首案）：
///
/// 1. N41 同名同值收敛——DS.titleMedium（deprecated shim）与
///    Theme textTheme.titleMedium 必须渲染同值。收敛前 shim 转发
///    titleLarge（19px），与 textTheme 的 16px 同名漂移。
/// 2. N44 长文段距显式令——SparkleMarkdown 非 chatBubble 角色的段间
///    空隙 = spacing12 档（半隙对称：每块上下 6）；chatBubble 角色豁免
///    为 0（聊天段距由 aurora 分组 spacing6 承担，禁双重叠加）。
void main() {
  group('N41 · DS.titleMedium 同名同值收敛', () {
    test('DS.titleMedium 与 textTheme.titleMedium 全属性恒等（明暗双主题）', () {
      for (final theme in <ThemeData>[AppThemes.lightTheme, AppThemes.darkTheme]) {
        final fromTextTheme = theme.textTheme.titleMedium!;
        expect(
          DS.titleMedium.fontSize,
          fromTextTheme.fontSize,
          reason: '同名漂移回归：DS.titleMedium 与 textTheme.titleMedium 字号必须相等',
        );
        expect(
          DS.titleMedium.fontWeight,
          fromTextTheme.fontWeight,
          reason: '字重必须同名同值',
        );
        expect(
          DS.titleMedium.height,
          fromTextTheme.height,
          reason: '行高必须同名同值',
        );
        expect(
          DS.titleMedium.letterSpacing,
          fromTextTheme.letterSpacing,
          reason: '字距必须同名同值',
        );
        expect(
          DS.titleMedium.fontFamilyFallback,
          fromTextTheme.fontFamilyFallback,
          reason: '字体回退链必须同名同值',
        );
      }
    });

    test('收敛档位符合 §3.1 角色表：titleMedium=16/w500，titleLarge=19（显式升档用）', () {
      expect(DS.titleMedium.fontSize, 16.0);
      expect(DS.titleMedium.fontWeight, FontWeight.w500);
      // 依赖 19px 视觉重量的调用点应显式改用 titleLarge，而非借道 titleMedium。
      expect(DS.titleLarge.fontSize, 19.0);
    });
  });

  group('N44 · SparkleMarkdown 长文段距显式', () {
    testWidgets('standard 角色：多段内容每段上下 6（相邻段合计空隙 12=spacing12 档）',
        (tester) async {
      await tester.pumpWidget(
        const _Harness(
          content: '第一段\n\n第二段',
          role: SparkleMarkdownRole.standard,
        ),
      );
      final halfGapPaddings = tester.widgetList<Padding>(
        find.byWidgetPredicate(
          (w) =>
              w is Padding &&
              w.padding == const EdgeInsets.symmetric(vertical: 6.0),
        ),
      );
      expect(
        halfGapPaddings.length,
        2,
        reason: '两个段落各包一层上下 6 的段距 Padding',
      );
    });

    testWidgets('standard 角色：h2 标题块距上下 9（0.75×段距，标题先于正文脱行）',
        (tester) async {
      await tester.pumpWidget(
        const _Harness(
          content: '## 二级标题\n\n正文段落',
          role: SparkleMarkdownRole.standard,
        ),
      );
      expect(
        tester.widgetList<Padding>(
          find.byWidgetPredicate(
            (w) =>
                w is Padding &&
                w.padding == const EdgeInsets.symmetric(vertical: 9.0),
          ),
        ),
        isNotEmpty,
        reason: 'h2 块距 0.75×段距=9（上下各 9 的对称半隙）',
      );
    });

    testWidgets('chatBubble 角色：段距豁免为 0，不与 aurora 分组 spacing6 双重叠加',
        (tester) async {
      await tester.pumpWidget(
        const _Harness(
          content: '第一段\n\n第二段',
          role: SparkleMarkdownRole.chatBubble,
        ),
      );
      final halfGapPaddings = tester.widgetList<Padding>(
        find.byWidgetPredicate(
          (w) =>
              w is Padding &&
              w.padding == const EdgeInsets.symmetric(vertical: 6.0),
        ),
      );
      expect(
        halfGapPaddings.length,
        0,
        reason: '聊天域段距由 aurora 分组承担（N44 豁免条款），段内块距必须为 0',
      );
      // 段落文本本身仍须完整渲染（豁免的是段距，不是内容）。
      expect(find.byType(RichText), findsNWidgets(2));
    });
  });
}

class _Harness extends StatelessWidget {
  const _Harness({
    required this.content,
    required this.role,
  });

  final String content;
  final SparkleMarkdownRole role;

  @override
  Widget build(BuildContext context) => MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: SparkleMarkdown(
            content: content,
            textColor: DS.textPrimary,
            codeBackgroundColor: DS.surfaceSecondary,
            linkColor: DS.brandPrimary,
            contentRole: role,
          ),
        ),
      );
}
