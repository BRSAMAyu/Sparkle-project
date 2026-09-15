import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/capability_ceiling_card.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('CapabilityCeilingCard', () {
    Widget buildWidget(Map<String, dynamic> ceilingData) => MaterialApp(
          home: Scaffold(
            body: ProviderScope(
              child: CapabilityCeilingCard(ceilingData: ceilingData),
            ),
          ),
        );

    testWidgets('renders reason text', (tester) async {
      await tester.pumpWidget(
        buildWidget({'reason': 'Cannot solve advanced calculus'}),
      );

      expect(find.text('Cannot solve advanced calculus'), findsOneWidget);
    });

    testWidgets('renders suggested mode chips', (tester) async {
      await tester.pumpWidget(
        buildWidget({
          'reason': 'Need deeper analysis',
          'suggested_modes': ['deep_analysis', 'expert_auto'],
        }),
      );

      expect(find.byType(ActionChip), findsNWidgets(2));
    });

    testWidgets('dismisses on close tap', (tester) async {
      await tester.pumpWidget(
        buildWidget({'reason': 'Test reason'}),
      );

      expect(find.text('Test reason'), findsOneWidget);

      await tester.tap(find.byIcon(Icons.close_rounded));
      await tester.pumpAndSettle();

      expect(find.text('Test reason'), findsNothing);
    });

    testWidgets('continue button dismisses card', (tester) async {
      await tester.pumpWidget(
        buildWidget({'reason': 'Test reason'}),
      );

      expect(find.text('Test reason'), findsOneWidget);

      // Find the continue button by its underline text style
      final continueFinders = find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            widget.style?.decoration == TextDecoration.underline,
      );
      expect(continueFinders, findsOneWidget);
      await tester.tap(continueFinders);
      await tester.pumpAndSettle();

      expect(find.text('Test reason'), findsNothing);
    });

    testWidgets('handles empty suggested_modes gracefully', (tester) async {
      await tester.pumpWidget(
        buildWidget({
          'reason': 'Some reason',
          'suggested_modes': <String>[],
        }),
      );

      expect(find.text('Some reason'), findsOneWidget);
      expect(find.byType(ActionChip), findsNothing);
    });

    testWidgets('handles missing reason with default text', (tester) async {
      await tester.pumpWidget(
        buildWidget(<String, dynamic>{}),
      );

      expect(find.byType(CapabilityCeilingCard), findsOneWidget);
    });
  });
}
